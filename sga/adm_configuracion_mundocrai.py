# -*- coding: latin-1 -*-
import os
import random
import pyqrcode
from datetime import datetime, date, timedelta
import xlwt
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from requests import request
from xlwt import *
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from googletrans import Translator

from decorators import secure_module, last_access
from settings import SITE_STORAGE, DEBUG
from sga.commonviews import adduserdata
from sga.forms import ActividadesMundoCraiForm, NoticiasMundoCraiForm, SalasMundoCraiForm, CapacitacionMundoCraiForm, \
    ReservasCraiSolicitarAutoridadForm, ReservasCraiSolicitarDetalleForm, FirmaMundoCraiForm, EncuestaMundoCraiForm, \
    PreguntaEncuestaMundoCraiForm, NivelEncuestaMundoCraiForm, DocenteCapacitacionForm, InscripcionCapacitacionForm, \
    OrganigramaForm, ReservaCubiculoCraiForm, TerminarReservaCubiculoCraiForm, SeccionClubesForm, \
    PaeActividadesPeriodoAreasForm, ClubesForm, InscripcionclubesForm
from sga.funciones import log, MiPaginador, generar_nombre, convertir_fecha, convertir_hora, tituloinstitucion, \
    restar_hora,suma_dias_habiles
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsaveqrcertificado
from sga.models import ActividadesMundoCrai, ActividadesMundoCraiDetalle, NoticiasMundoCrai, SalaCrai, \
    CapacitacionesCrai, InscripcionCapacitacionesCrai, ReservasCrai, CUENTAS_CORREOS, SolicitudOtrasCapacitacionesCrai, \
    MESES_CHOICES, FirmasCapacitacionesCrai, EncuestaCapacitacionesCrai, PreguntasEncuestaCapacitacionesCrai, \
    NivelSatisfacionEncuestaCapacitacionesCrai, Organigrama, ReservasCubiculosCrai, Persona, Profesor, SeccionClub, \
    Club, InscripcionClub
from sga.tasks import conectar_cuenta, send_html_mail


def controlar_horas(fecha, horadesde, horahasta, salacrai):
    if ReservasCrai.objects.filter(fecha=fecha, salacrai=salacrai, horadesde__lte=horadesde, horahasta__gte=horadesde, status=True).exclude(estado=3).exists():
        return True
    if ReservasCrai.objects.filter(fecha=fecha, salacrai=salacrai, horadesde__gte=horadesde, horahasta__gte=horadesde, horadesde__lte=horahasta, horahasta__lte=horahasta, status=True).exclude(estado=3).exists():
        return True
    return False


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    borders = Borders()
    borders.left = 1
    borders.right = 1
    borders.top = 1
    borders.bottom = 1
    adduserdata(request, data)
    persona = request.session['persona']
    tipo_mundo = 0
    if request.user.has_perm('sagest.es_biblioteca'):
        tipo_mundo = 1
    if request.user.has_perm('sagest.es_docencia'):
        tipo_mundo = 2
    if request.user.has_perm('sagest.es_investigacion'):
        tipo_mundo = 3
    if request.user.has_perm('sagest.es_cultural'):
        tipo_mundo = 4
    url_path = 'http://127.0.0.1:8000'
    if not DEBUG:
        url_path = 'https://sga.unemi.edu.ec'
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'add':
            try:
                f = ActividadesMundoCraiForm(request.POST, request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        if newfile.size > 50485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 50 Mb."})
                        if newfile:
                            newfile._name = generar_nombre("actividad_crai_", newfile._name)
                newfileicono = None
                if 'icono' in request.FILES:
                    newfileicono = request.FILES['icono']
                    if newfileicono:
                        newfileiconod = newfileicono._name
                        ext = newfileiconod[newfileiconod.rfind("."):]
                        if not ext == '.png':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .png."})
                        if newfileicono.size > 2097152:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 2 Mb."})
                        if newfileicono:
                            newfileicono._name = generar_nombre("icono_crai_", newfileicono._name)
                if f.is_valid():
                    if ActividadesMundoCrai.objects.filter(status=True, descripcion=f.cleaned_data['descripcion'], tipomundocrai=f.cleaned_data['tipomundocrai']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La actividad ya existe."})
                    actividadesmundocrai = ActividadesMundoCrai(descripcion=f.cleaned_data['descripcion'],
                                                                concepto=f.cleaned_data['concepto'],
                                                                tipomundocrai=f.cleaned_data['tipomundocrai'],
                                                                tipoactividad=f.cleaned_data['tipoactividad'],
                                                                orden=f.cleaned_data['orden'],
                                                                enlace=f.cleaned_data['enlace'],
                                                                video=f.cleaned_data['video'],
                                                                estado=f.cleaned_data['estado'],
                                                                principal=f.cleaned_data['principal'],
                                                                icono = newfileicono,
                                                                archivo = newfile)
                    actividadesmundocrai.save(request)
                    if f.cleaned_data['actividadesmundocrai']:
                        actividadesmundocraidetalle = ActividadesMundoCraiDetalle(actividadesmundocraiprincipal=f.cleaned_data['actividadesmundocrai'],
                                                                                  actividadesmundocraidetalle=actividadesmundocrai)
                        actividadesmundocraidetalle.save(request)
                    log(u'Adiciono actividad CRAI: %s' % actividadesmundocrai, request, "add")
                    return JsonResponse({"result": "ok", "id": actividadesmundocrai.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        if action == 'addnoticia':
            try:
                f = NoticiasMundoCraiForm(request.POST, request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        if newfile.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                        if newfile:
                            newfile._name = generar_nombre("noticia_crai_", newfile._name)
                if f.is_valid():
                    if NoticiasMundoCrai.objects.filter(status=True, descripcion=f.cleaned_data['descripcion'], titulo=f.cleaned_data['titulo']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La noticia ya existe."})
                    noticiasmundocrai = NoticiasMundoCrai(descripcion=f.cleaned_data['descripcion'],
                                                          titulo=f.cleaned_data['titulo'],
                                                          enlace=f.cleaned_data['enlace'],
                                                          estado=f.cleaned_data['estado'],
                                                          archivo = newfile)
                    noticiasmundocrai.save(request)
                    log(u'Adiciono noticia CRAI: %s' % noticiasmundocrai, request, "add")
                    return JsonResponse({"result": "ok", "id": noticiasmundocrai.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        if action == 'addreservacubiculo':
            try:
                f = ReservaCubiculoCraiForm(request.POST)
                if f.is_valid():
                    if ReservasCubiculosCrai.objects.filter(status=True, profesor_id=f.cleaned_data['profesor'], cubiculo_id=request.POST['ids'], terminar=False).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Registro Repetido."})
                    if ReservasCubiculosCrai.objects.filter(status=True, profesor_id=f.cleaned_data['profesor'], terminar=False).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Profesor ya tiene cubículo."})
                    reservascubiculoscrai = ReservasCubiculosCrai(profesor_id=f.cleaned_data['profesor'],
                                                                  cubiculo_id=request.POST['ids'],
                                                                  fechadesde=f.cleaned_data['fechadesde'],
                                                                  terminar=False)
                    reservascubiculoscrai.save(request)
                    log(u'Adiciono Reserva cubículo CRAI: %s' % reservascubiculoscrai, request, "add")
                    return JsonResponse({"result": "ok", "id": reservascubiculoscrai.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        if action == 'addorganigrama':
            try:
                f = OrganigramaForm(request.POST)
                if f.is_valid():
                    if Organigrama.objects.filter(status=True, seccion=f.cleaned_data['seccion'], persona=f.cleaned_data['persona']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe."})
                    organigrama = Organigrama(seccion=f.cleaned_data['seccion'],
                                              nivel_puesto=f.cleaned_data['nivel_puesto'],
                                              persona_id=f.cleaned_data['persona'])
                    organigrama.save(request)
                    log(u'Adiciono Organigrama CRAI: %s' % organigrama, request, "add")
                    return JsonResponse({"result": "ok", "id": organigrama.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        if action == 'addfirma':
            try:
                f = FirmaMundoCraiForm(request.POST, request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext != '.jpg' and ext != '.jpeg' and ext != '.png':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .jpg, .jpeg, .png"})
                        if newfile.size > 2621440:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 2 Mb."})
                        if newfile:
                            newfile._name = generar_nombre("firma_crai_", newfile._name)
                if f.is_valid():
                    if FirmasCapacitacionesCrai.objects.filter(status=True, persona_id=f.cleaned_data['persona'], tipofirma=f.cleaned_data['tipofirma']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La Firma ya existe."})
                    if f.cleaned_data['tipofirma'] == '3':
                        if FirmasCapacitacionesCrai.objects.filter(status=True, tipofirma=3).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe la firma de Director."})
                    if f.cleaned_data['tipofirma'] == '2':
                        firmascapacitacionescrai = FirmasCapacitacionesCrai(persona_id=f.cleaned_data['persona'],
                                                                            tipofirma=f.cleaned_data['tipofirma'],
                                                                            tipomundocrai=f.cleaned_data['tipomundocrai'],
                                                                            archivo = newfile)
                    else:
                        firmascapacitacionescrai = FirmasCapacitacionesCrai(persona_id=f.cleaned_data['persona'],
                                                                            tipofirma=f.cleaned_data['tipofirma'],
                                                                            archivo = newfile)
                    firmascapacitacionescrai.save(request)
                    log(u'Adiciono firma CRAI: %s' % firmascapacitacionescrai, request, "add")
                    return JsonResponse({"result": "ok", "id": firmascapacitacionescrai.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        if action == 'addencuesta':
            try:
                f = EncuestaMundoCraiForm(request.POST)
                if f.is_valid():
                    if EncuestaCapacitacionesCrai.objects.filter(status=True, descripcion=f.cleaned_data['descripcion']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La Encuesta ya existe."})
                    encuestacapacitacionescrai = EncuestaCapacitacionesCrai(descripcion=f.cleaned_data['descripcion'],
                                                                            estado=f.cleaned_data['estado'])
                    encuestacapacitacionescrai.save(request)
                    log(u'Adiciono firma CRAI: %s' % encuestacapacitacionescrai, request, "add")
                    return JsonResponse({"result": "ok", "id": encuestacapacitacionescrai.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        if action == 'addpregunta':
            try:
                f = PreguntaEncuestaMundoCraiForm(request.POST)
                if f.is_valid():
                    if PreguntasEncuestaCapacitacionesCrai.objects.filter(encuesta__id=int(request.POST['idencuesta']) , status=True, pregunta=f.cleaned_data['pregunta']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La Pregunta ya existe en la Encuesta."})
                    preguntasencuestacapacitacionescrai = PreguntasEncuestaCapacitacionesCrai(encuesta_id=int(request.POST['idencuesta']),
                                                                                              pregunta=f.cleaned_data['pregunta'])
                    preguntasencuestacapacitacionescrai.save(request)
                    log(u'Adiciono Pregunta CRAI: %s' % preguntasencuestacapacitacionescrai, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        if action == 'adddocente':
            try:
                f = DocenteCapacitacionForm(request.POST)
                if f.is_valid():
                    if InscripcionCapacitacionesCrai.objects.filter(profesor__id=int(request.POST['persona']) , status=True, capacitacionescrai__id=int(request.POST['id'])).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El docente ya tiene la capacitación."})
                    inscripcioncapacitacionescrai = InscripcionCapacitacionesCrai(capacitacionescrai_id=int(request.POST['id']),
                                                                                  fecha=datetime.now().today(),
                                                                                  profesor_id=f.cleaned_data['persona'])
                    inscripcioncapacitacionescrai.save(request)
                    log(u'Adiciono Docente a capacitacion CRAI: %s' % inscripcioncapacitacionescrai, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        if action == 'addinscripcion':
            try:
                f = InscripcionCapacitacionForm(request.POST)
                if f.is_valid():
                    if InscripcionCapacitacionesCrai.objects.filter(inscripcion__id=int(request.POST['persona']) , status=True, capacitacionescrai__id=int(request.POST['id'])).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El estudiante ya tiene la capacitación."})
                    inscripcioncapacitacionescrai = InscripcionCapacitacionesCrai(capacitacionescrai_id=int(request.POST['id']),
                                                                                  fecha=datetime.now().today(),
                                                                                  inscripcion_id=f.cleaned_data['persona'])
                    inscripcioncapacitacionescrai.save(request)
                    log(u'Adiciono estudiante a capacitacion CRAI: %s' % inscripcioncapacitacionescrai, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        elif action == 'addinscripcionclub':
            try:
                f = InscripcionclubesForm(request.POST)
                if f.is_valid():
                    club = Club.objects.get(pk=request.POST['id'],status=True)
                    if not club.inscripcionclub_set.values("id").filter(status=True).exists():
                        totalinscritos = club.inscripcionclub_set.values("id").filter(status=True).count()
                        if totalinscritos >= club.cupo:
                            return JsonResponse({"result": "bad", "mensaje": u"Lo sentimos, no hay cupo disponible."})
                        inscripcionclub = InscripcionClub(inscripcion_id=f.cleaned_data['inscripcion'],
                                                          club=club)
                        inscripcionclub.save(request)
                        log(u'Adiciono Inscripción Club: %s' % inscripcionclub, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Lo sentimos, ya esta inscrito en este club."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        if action == 'addnivel':
            try:
                f = NivelEncuestaMundoCraiForm(request.POST)
                if f.is_valid():
                    if NivelSatisfacionEncuestaCapacitacionesCrai.objects.filter(encuesta__id=int(request.POST['idencuesta']) , status=True, nivel=f.cleaned_data['nivel']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El nivel ya existe en la Encuesta."})
                    nivelsatisfacionencuestacapacitacionescrai = NivelSatisfacionEncuestaCapacitacionesCrai(encuesta_id=int(request.POST['idencuesta']),
                                                                                              nivel=f.cleaned_data['nivel'],
                                                                                              orden=f.cleaned_data['orden'],
                                                                                              puntaje=f.cleaned_data['puntaje'])
                    nivelsatisfacionencuestacapacitacionescrai.save(request)
                    log(u'Adiciono Nivel CRAI: %s' % nivelsatisfacionencuestacapacitacionescrai, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        if action == 'addsala':
            try:
                f = SalasMundoCraiForm(request.POST)
                if f.is_valid():
                    if SalaCrai.objects.filter(status=True, nombre=f.cleaned_data['nombre'], ubicacion=f.cleaned_data['ubicacion']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La sala ya existe."})
                    salacrai = SalaCrai(nombre=f.cleaned_data['nombre'],
                                        capacidad=f.cleaned_data['capacidad'],
                                        ubicacion=f.cleaned_data['ubicacion'],
                                        tipo=f.cleaned_data['tipo'])
                    salacrai.save(request)
                    log(u'Adiciono Sala CRAI: %s' % salacrai, request, "add")
                    return JsonResponse({"result": "ok", "id": salacrai.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        if action == 'addcapacitacion':
            try:
                f = CapacitacionMundoCraiForm(request.POST)
                if not f.is_valid():
                    raise NameError('Error')
                    # if CapacitacionesCrai.objects.filter(status=True, tema=f.cleaned_data['tema'], salacrai=f.cleaned_data['salacrai']).exists():
                        # return JsonResponse({"result": "bad", "mensaje": u"La capacitación ya existe."})
                capacitacionescrai = CapacitacionesCrai(tema=f.cleaned_data['tema'],
                                                        contenido=f.cleaned_data['contenido'],
                                                        salacrai=f.cleaned_data['salacrai'],
                                                        fechadesde=f.cleaned_data['fechadesde'],
                                                        fechahasta=f.cleaned_data['fechahasta'],
                                                        horadesde=f.cleaned_data['horadesde'],
                                                        horahasta=f.cleaned_data['horahasta'],
                                                        capacitador_id=f.cleaned_data['capacitador'] if f.cleaned_data['capacitador'] else None,
                                                        tipo=f.cleaned_data['tipo'],
                                                        tipomundocrai=f.cleaned_data['tipomundocrai'],
                                                        encuesta=f.cleaned_data['encuesta'],
                                                        cupo=f.cleaned_data['cupo'],
                                                        horas=f.cleaned_data['horastotal'])
                capacitacionescrai.save(request)
                log(u'Adiciono Capacitación CRAI: %s' % capacitacionescrai, request, "add")
                return JsonResponse({"result": "ok", "id": capacitacionescrai.id})
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(), 'es').text, "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                actividadesmundocrai = ActividadesMundoCrai.objects.get(pk=request.POST['id'])
                f = ActividadesMundoCraiForm(request.POST, request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        if newfile.size > 50485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 50 Mb."})
                        if newfile:
                            newfile._name = generar_nombre("actividad_crai_", newfile._name)
                newfileicono = None
                if 'icono' in request.FILES:
                    newfileicono = request.FILES['icono']
                    if newfileicono:
                        newfileiconod = newfileicono._name
                        ext = newfileiconod[newfileiconod.rfind("."):]
                        if not ext == '.png':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .png."})
                        if newfileicono.size > 2097152:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 2 Mb."})
                        if newfileicono:
                            newfileicono._name = generar_nombre("icono_crai_", newfileicono._name)
                if f.is_valid():
                    if ActividadesMundoCrai.objects.filter(status=True, descripcion=f.cleaned_data['descripcion'], tipomundocrai=f.cleaned_data['tipomundocrai']).exclude(pk=actividadesmundocrai.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La actividad ya existe."})
                    ActividadesMundoCraiDetalle.objects.filter(actividadesmundocraidetalle=actividadesmundocrai).delete()
                    actividadesmundocrai.descripcion = f.cleaned_data['descripcion']
                    actividadesmundocrai.concepto = f.cleaned_data['concepto']
                    actividadesmundocrai.tipomundocrai = f.cleaned_data['tipomundocrai']
                    actividadesmundocrai.tipoactividad = f.cleaned_data['tipoactividad']
                    actividadesmundocrai.orden = f.cleaned_data['orden']
                    actividadesmundocrai.enlace = f.cleaned_data['enlace']
                    actividadesmundocrai.video = f.cleaned_data['video']
                    actividadesmundocrai.principal = f.cleaned_data['principal']
                    actividadesmundocrai.estado = f.cleaned_data['estado']
                    actividadesmundocrai.save(request)
                    if newfile:
                        actividadesmundocrai.archivo = newfile
                    if newfileicono:
                        actividadesmundocrai.icono = newfileicono
                    actividadesmundocrai.save(request)
                    if f.cleaned_data['actividadesmundocrai']:
                        actividadesmundocraidetalle = ActividadesMundoCraiDetalle(actividadesmundocraiprincipal=f.cleaned_data['actividadesmundocrai'],
                                                                                  actividadesmundocraidetalle=actividadesmundocrai)
                        actividadesmundocraidetalle.save(request)

                    log(u'Modifico actividad CRAI: %s' % actividadesmundocrai, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        elif action == 'editnoticia':
            try:
                noticiasmundocrai = NoticiasMundoCrai.objects.get(pk=request.POST['id'])
                f = NoticiasMundoCraiForm(request.POST, request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        if newfile.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                        if newfile:
                            newfile._name = generar_nombre("noticia_crai_", newfile._name)
                if f.is_valid():
                    if NoticiasMundoCrai.objects.filter(status=True, descripcion=f.cleaned_data['descripcion'], titulo=f.cleaned_data['titulo']).exclude(pk=noticiasmundocrai.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La noticia ya existe."})
                    noticiasmundocrai.descripcion = f.cleaned_data['descripcion']
                    noticiasmundocrai.titulo = f.cleaned_data['titulo']
                    noticiasmundocrai.enlace = f.cleaned_data['enlace']
                    noticiasmundocrai.estado = f.cleaned_data['estado']
                    if newfile:
                        noticiasmundocrai.archivo = newfile
                    noticiasmundocrai.save(request)
                    log(u'Modifico noticia CRAI: %s' % noticiasmundocrai, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        elif action == 'terminarreserva_cubiculo':
            try:
                reserva = ReservasCubiculosCrai.objects.get(pk=request.POST['id'])
                f = TerminarReservaCubiculoCraiForm(request.POST, request.FILES)
                if f.cleaned_data['fechahasta'] <= reserva.fechadesde:
                    return JsonResponse({"result": "bad", "mensaje": u"La fecha hasta debe ser mayor que la fecha desde %s." % reserva.fechadesde})
                if f.is_valid():
                    reserva.terminar = True
                    reserva.fechahasta = f.cleaned_data['fechahasta']
                    reserva.save(request)
                    log(u'Termino Reserva Cubículo CRAI: %s' % reserva, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        elif action == 'editorganigrama':
            try:
                organigrama = Organigrama.objects.get(pk=request.POST['id'])
                f = OrganigramaForm(request.POST)
                if f.is_valid():
                    if Organigrama.objects.filter(status=True, seccion=f.cleaned_data['seccion'], nivel_puesto=f.cleaned_data['nivel_puesto']).exclude(pk=organigrama.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe."})
                    organigrama.seccion = f.cleaned_data['seccion']
                    organigrama.nivel_puesto = f.cleaned_data['nivel_puesto']
                    organigrama.save(request)
                    log(u'Modifico Organigrama CRAI: %s' % organigrama, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        elif action == 'editfirma':
            try:
                firma = FirmasCapacitacionesCrai.objects.get(pk=request.POST['id'])
                f = FirmaMundoCraiForm(request.POST, request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext != '.jpg' and ext != '.jpeg' and ext != '.png':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .jpg, .jpeg, .png"})
                        if newfile.size > 2621440:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 2 Mb."})
                        if newfile:
                            newfile._name = generar_nombre("firma_crai_", newfile._name)
                if f.is_valid():
                    if FirmasCapacitacionesCrai.objects.filter(status=True, persona_id=f.cleaned_data['persona'], tipofirma=f.cleaned_data['tipofirma']).exclude(pk=firma.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La Firma ya existe."})
                    if f.cleaned_data['tipofirma'] == '3':
                        if FirmasCapacitacionesCrai.objects.filter(status=True, tipofirma=3).exclude(pk=firma.id).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe la firma de Director."})
                    firma.tipofirma = f.cleaned_data['tipofirma']
                    firma.tipomundocrai = None
                    if f.cleaned_data['tipofirma'] == '2':
                        firma.tipomundocrai = f.cleaned_data['tipomundocrai']
                    if newfile:
                        firma.archivo = newfile
                    firma.save(request)
                    log(u'Modifico Firma CRAI: %s' % firma, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        elif action == 'editencuesta':
            try:
                encuestacapacitacionescrai = EncuestaCapacitacionesCrai.objects.get(pk=request.POST['id'])
                f = EncuestaMundoCraiForm(request.POST)
                if f.is_valid():
                    if EncuestaCapacitacionesCrai.objects.filter(status=True, descripcion=f.cleaned_data['descripcion']).exclude(pk=encuestacapacitacionescrai.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La Encuesta ya existe."})
                    encuestacapacitacionescrai.descripcion = f.cleaned_data['descripcion']
                    encuestacapacitacionescrai.estado = f.cleaned_data['estado']
                    encuestacapacitacionescrai.save(request)
                    log(u'Modifico Encuesta CRAI: %s' % encuestacapacitacionescrai, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        elif action == 'editpregunta':
            try:
                preguntasencuestacapacitacionescrai = PreguntasEncuestaCapacitacionesCrai.objects.get(pk=request.POST['id'])
                f = PreguntaEncuestaMundoCraiForm(request.POST)
                if f.is_valid():
                    if PreguntasEncuestaCapacitacionesCrai.objects.filter(encuesta__id=int(request.POST['idencuesta']), status=True, pregunta=f.cleaned_data['pregunta']).exclude(pk=preguntasencuestacapacitacionescrai.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La Pregunta ya existe en la Encuesta."})
                    preguntasencuestacapacitacionescrai.pregunta = f.cleaned_data['pregunta']
                    preguntasencuestacapacitacionescrai.save(request)
                    log(u'Modifico Encuesta CRAI: %s' % preguntasencuestacapacitacionescrai, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        elif action == 'editnivel':
            try:
                nivelsatisfacionencuestacapacitacionescrai = NivelSatisfacionEncuestaCapacitacionesCrai.objects.get(pk=request.POST['id'])
                f = NivelEncuestaMundoCraiForm(request.POST)
                if f.is_valid():
                    if NivelSatisfacionEncuestaCapacitacionesCrai.objects.filter(encuesta__id=int(request.POST['idencuesta']), status=True, nivel=f.cleaned_data['nivel']).exclude(pk=nivelsatisfacionencuestacapacitacionescrai.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El Nivel ya existe en la Encuesta."})
                    nivelsatisfacionencuestacapacitacionescrai.nivel = f.cleaned_data['nivel']
                    nivelsatisfacionencuestacapacitacionescrai.orden = f.cleaned_data['orden']
                    nivelsatisfacionencuestacapacitacionescrai.puntaje = f.cleaned_data['puntaje']
                    nivelsatisfacionencuestacapacitacionescrai.save(request)
                    log(u'Modifico Encuesta CRAI: %s' % nivelsatisfacionencuestacapacitacionescrai, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        elif action == 'editsala':
            try:
                salacrai = SalaCrai.objects.get(pk=request.POST['id'])
                f = SalasMundoCraiForm(request.POST)
                if f.is_valid():
                    if SalaCrai.objects.filter(status=True, nombre=f.cleaned_data['nombre'], ubicacion=f.cleaned_data['ubicacion']).exclude(pk=salacrai.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La Sala ya existe."})
                    salacrai.nombre = f.cleaned_data['nombre']
                    salacrai.capacidad = f.cleaned_data['capacidad']
                    salacrai.ubicacion = f.cleaned_data['ubicacion']
                    salacrai.tipo = f.cleaned_data['tipo']
                    salacrai.save(request)
                    log(u'Modifico Sala CRAI: %s' % salacrai, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        elif action == 'editcapacitacion':
            try:
                capacitacionescrai = CapacitacionesCrai.objects.get(pk=request.POST['id'])
                f = CapacitacionMundoCraiForm(request.POST)
                if not f.is_valid():
                    raise NameError('Error')
                    # if CapacitacionesCrai.objects.filter(status=True, tema=f.cleaned_data['tema'], salacrai=f.cleaned_data['salacrai']).exclude(pk=capacitacionescrai.id).exists():
                    #     return JsonResponse({"result": "bad", "mensaje": u"La Capacitación ya existe."})
                capacitacionescrai.tema = f.cleaned_data['tema']
                capacitacionescrai.contenido = f.cleaned_data['contenido']
                capacitacionescrai.salacrai = f.cleaned_data['salacrai']
                capacitacionescrai.fechadesde = f.cleaned_data['fechadesde']
                capacitacionescrai.fechahasta = f.cleaned_data['fechahasta']
                capacitacionescrai.horadesde = f.cleaned_data['horadesde']
                capacitacionescrai.horahasta = f.cleaned_data['horahasta']
                capacitacionescrai.cupo = f.cleaned_data['cupo']
                capacitacionescrai.tipomundocrai = f.cleaned_data['tipomundocrai']
                capacitacionescrai.encuesta = f.cleaned_data['encuesta']
                capacitacionescrai.horas = f.cleaned_data['horastotal']
                capacitacionescrai.capacitador_id = f.cleaned_data['capacitador'] if f.cleaned_data['capacitador'] else None
                capacitacionescrai.save(request)
                log(u'Modifico Capacitación CRAI: %s' % capacitacionescrai, request, "edit")
                return JsonResponse({"result": "ok"})

            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        elif action == 'delete':
            try:
                actividadesmundocrai = ActividadesMundoCrai.objects.get(pk=request.POST['id'])
                if actividadesmundocrai.enuso():
                    return JsonResponse({"result": "bad", "mensaje": u"Actividad en uso."})
                log(u'Elimino actividad CRAI: %s' % actividadesmundocrai, request, "del")
                actividadesmundocrai.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al eliminar los datos."})

        elif action == 'deletenoticia':
            try:
                noticiasmundocrai = NoticiasMundoCrai.objects.get(pk=request.POST['id'])
                log(u'Elimino noticia CRAI: %s' % noticiasmundocrai, request, "del")
                noticiasmundocrai.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al eliminar los datos."})

        elif action == 'delreserva_cubiculo':
            try:
                reserva = ReservasCubiculosCrai.objects.get(pk=request.POST['id'])
                log(u'Elimino reserva cubiculo CRAI: %s' % reserva, request, "del")
                reserva.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al eliminar los datos."})

        elif action == 'deleteorganigrama':
            try:
                organigrama = Organigrama.objects.get(pk=request.POST['id'])
                log(u'Elimino Organigrama CRAI: %s' % organigrama, request, "del")
                organigrama.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al eliminar los datos."})

        elif action == 'deletefirma':
            try:
                firma = FirmasCapacitacionesCrai.objects.get(pk=request.POST['id'])
                log(u'Elimino firma CRAI: %s' % firma, request, "del")
                firma.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al eliminar los datos."})

        elif action == 'deleteencuesta':
            try:
                encuestacapacitacionescrai = EncuestaCapacitacionesCrai.objects.get(pk=request.POST['id'])
                log(u'Elimino Encuesta CRAI: %s' % encuestacapacitacionescrai, request, "del")
                encuestacapacitacionescrai.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al eliminar los datos."})

        elif action == 'deletepregunta':
            try:
                preguntasencuestacapacitacionescrai = PreguntasEncuestaCapacitacionesCrai.objects.get(pk=request.POST['id'])
                log(u'Elimino Pregunta CRAI: %s' % preguntasencuestacapacitacionescrai, request, "del")
                preguntasencuestacapacitacionescrai.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al eliminar los datos."})

        elif action == 'deletenivel':
            try:
                nivelsatisfacionencuestacapacitacionescrai = NivelSatisfacionEncuestaCapacitacionesCrai.objects.get(pk=request.POST['id'])
                log(u'Elimino Nivel CRAI: %s' % nivelsatisfacionencuestacapacitacionescrai, request, "del")
                nivelsatisfacionencuestacapacitacionescrai.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al eliminar los datos."})

        elif action == 'deletesala':
            try:
                salacrai = SalaCrai.objects.get(pk=request.POST['id'])
                log(u'Elimino Sala CRAI: %s' % salacrai, request, "del")
                salacrai.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al eliminar los datos."})

        elif action == 'deletecapacitacion':
            try:
                capacitacionescrai = CapacitacionesCrai.objects.get(pk=request.POST['id'])
                log(u'Elimino Capacitación CRAI: %s' % capacitacionescrai, request, "del")
                capacitacionescrai.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al eliminar los datos."})

        elif action == 'aprobarsala':
            try:
                reservascrai = ReservasCrai.objects.get(pk=request.POST['id'], status=True)
                reservascrai.observacion = request.POST['observacion']
                reservascrai.estado = 2
                reservascrai.save(request)
                lista = reservascrai.email_solicitante()
                send_html_mail("Aprobacion Reserva Sala CRAI (DOCENTE)", "emails/aprobacionsalacrai.html", {'sistema': request.session['nombresistema'], 'solicitante': reservascrai.solicitante(), 'descripcion': reservascrai.descripcion, 'observacion': reservascrai.observacion, 'estado': reservascrai.get_estado_display()}, lista, [], cuenta=CUENTAS_CORREOS[4][1])
                log(u'Aprobo reservación sala: %s' % reservascrai, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar los datos."})

        elif action == 'rechazarsala':
            try:
                reservascrai = ReservasCrai.objects.get(pk=request.POST['id'], status=True)
                reservascrai.observacion = request.POST['observacion']
                reservascrai.estado = 3
                reservascrai.save(request)
                lista = reservascrai.email_solicitante()
                send_html_mail("Rechazo Reserva Sala CRAI (DOCENTE)", "emails/aprobacionsalacrai.html", {'sistema': request.session['nombresistema'], 'solicitante': reservascrai.solicitante(),'descripcion': reservascrai.descripcion, 'observacion': reservascrai.observacion, 'estado': reservascrai.get_estado_display()}, lista, [], cuenta=CUENTAS_CORREOS[4][1])
                log(u'Rechazo reservación sala: %s' % reservascrai, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar los datos."})

        if action == 'listar':
            try:
                fecha = convertir_fecha(request.POST['idfecha'])
                data['reservascrais'] = reservascrai = ReservasCrai.objects.filter(status=True,fecha=fecha).order_by('horadesde')
                data['form2'] = ReservasCraiSolicitarDetalleForm()
                template = get_template("adm_configuracion_mundocrai/listar.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'adddetalle':
            try:
                horadesde = convertir_hora(request.POST['horadesde'])
                horahasta = convertir_hora(request.POST['horahasta'])
                fecha = convertir_fecha(request.POST['idfecha'])
                solicitanteprofesor = request.POST['solicitante']
                descripcion = request.POST['descripcion']
                salacrai = request.POST['salacrai']
                cantidad = request.POST['cantidad']
                if not horadesde <= horahasta:
                    return JsonResponse({"result": "bad", "mensaje": u"La hora desde debe ser mayor que la hora hasta"})
                if not controlar_horas(fecha, horadesde, horahasta, salacrai):
                    reservascrai = ReservasCrai(solicitanteprofesor_id=int(solicitanteprofesor),
                                                descripcion=descripcion,
                                                salacrai_id=salacrai,
                                                cantidad=cantidad,
                                                fecha=fecha,
                                                horadesde=horadesde,
                                                horahasta=horahasta,
                                                lunes=True if fecha.isoweekday() == 1 else False,
                                                martes=True if fecha.isoweekday() == 2 else False,
                                                miercoles=True if fecha.isoweekday() == 3 else False,
                                                jueves=True if fecha.isoweekday() == 4 else False,
                                                viernes=True if fecha.isoweekday() == 5 else False,
                                                sabado=True if fecha.isoweekday() == 6 else False,
                                                domingo=True if fecha.isoweekday() == 7 else False)
                    reservascrai.save(request)
                    lista = ['rparedesh@unemi.edu.ec',	'iburgosv@unemi.edu.ec']
                    send_html_mail("Reserva Sala CRAI (DOCENTE)", "emails/reservasalacrai.html", {'sistema': request.session['nombresistema'], 'participante': solicitanteprofesor, 'descripcion': descripcion, 'salacrai': salacrai, 't': tituloinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[4][1])
                    log(u'Adiciono nueva solicitud reserva sala CRAI autoridad, sola: %s' % reservascrai, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Ya tiene registrado un registro en esas horas."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editdetalle':
            try:
                horadesde = convertir_hora(request.POST['horadesde'])
                horahasta = convertir_hora(request.POST['horahasta'])
                cantidad = convertir_hora(request.POST['cantidad'])
                salacrai = convertir_hora(request.POST['salacrai'])
                if not horadesde <= horahasta:
                    return JsonResponse({"result": "bad", "mensaje": u"La hora desde debe ser mayor que la hora hasta"})
                reservascrai = ReservasCrai.objects.get(pk=int(request.POST['id']))
                reservascrai.horadesde = horadesde
                reservascrai.horahasta = horahasta
                reservascrai.cantidad = cantidad
                reservascrai.salacrai_id = salacrai
                reservascrai.save(request)
                log(u'Edito solicitud reserva sala CRAI autoridad: %s - [%s %s]' % (reservascrai, horadesde, horahasta), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deletedetalle':
            try:
                reservascrai = ReservasCrai.objects.get(pk=int(request.POST['id']))
                lista = ['rparedesh@unemi.edu.ec',	'iburgosv@unemi.edu.ec']
                send_html_mail("Eliminación Reserva Sala CRAI (DOCENTE)", "emails/eliminacionreservasalacrai.html", {'sistema': request.session['nombresistema'], 'participante': reservascrai.solicitanteprofesor, 'descripcion': reservascrai.descripcion, 'salacrai': reservascrai.salacrai, 't': tituloinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[4][1])
                log(u'Elimino reserva sala CRAI autoridad: %s' % (reservascrai), request, "add")
                reservascrai.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'aprobarinscripcion':
            try:
                inscripcion = InscripcionCapacitacionesCrai.objects.get(pk=request.POST['id'])
                inscripcion.aprobado = True
                inscripcion.save(request)
                # generacion de certificado
                data['evento'] = evento = inscripcion.capacitacionescrai
                # validacion de director, coordinador y docente si tiene firma
                director = FirmasCapacitacionesCrai.objects.filter(status=True, tipofirma=3)
                if director:
                    data['director'] = director[0].persona.nombre_completo_inverso_titulo()
                    data['fdirector'] = director[0].archivo.url
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Falta configurar firma del Director."})
                coordinador = FirmasCapacitacionesCrai.objects.filter(status=True, tipofirma=2, tipomundocrai=evento.tipomundocrai)
                if coordinador:
                    data['coordinador'] = coordinador[0].persona.nombre_completo_inverso_titulo()
                    data['fcoordinador'] = coordinador[0].archivo.url
                    if evento.tipomundocrai==1:
                        data['cargo']='COORDINADOR(A) GESTION DE BIBLIOTECA'
                    if evento.tipomundocrai==2:
                        data['cargo']='COORDINADOR(A) GESTION DE SOPORTE A LA DOCENCIA'
                    if evento.tipomundocrai==3:
                        data['cargo']='COORDINADOR(A) GESTION DE SOPORTE A LA INVESTIGACIÓN'
                    if evento.tipomundocrai==4:
                        data['cargo']='COORDINADOR(A) GESTIÓN CULTURAL'
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Falta configurar firma del Coordinador."})
                docenteclase = FirmasCapacitacionesCrai.objects.filter(status=True, tipofirma=1, persona=evento.capacitador)
                if docenteclase:
                    data['docenteclase'] = docenteclase[0].persona.nombre_completo_inverso_titulo()
                    data['fdocenteclase'] = docenteclase[0].archivo.url
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Falta configurar firma del Docente."})
                mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
                fechainicio = evento.fechadesde
                fechafin = evento.fechahasta
                fechacertificado = suma_dias_habiles(fechafin, 7)
                data['fecha'] = u"Milagro, %s de %s del %s" % (fechacertificado.day, str(mes[fechacertificado.month - 1]), fechacertificado.year)
                if fechainicio == fechafin:
                    fechascapacitacion = "el %s de %s del %s" % (fechainicio.day, str(mes[fechainicio.month - 1]), fechainicio.year)
                elif fechainicio.month != fechafin.month:
                    if fechainicio.year == fechafin.year:
                        fechascapacitacion = "del %s de %s al %s de %s del %s" % (fechainicio.day, str(mes[fechainicio.month - 1]), fechafin.day, str(mes[fechafin.month - 1]), fechafin.year)
                    else:
                        fechascapacitacion = "del %s de %s del %s al %s de %s del %s" % (fechainicio.day, str(mes[fechainicio.month - 1]), fechainicio.year, fechafin.day, str(mes[fechafin.month - 1]), fechafin.year)
                else:
                    fechascapacitacion = "del %s al %s de %s del %s" % (fechainicio.day, fechafin.day, str(mes[fechainicio.month - 1]), fechainicio.year)
                data['fechascapacitacion'] = fechascapacitacion
                data['fecha'] = u"Milagro, %s de %s del %s" % (datetime.now().day, str(mes[datetime.now().month - 1]), datetime.now().year)
                data['inscrito'] = inscripcion.inscrito()
                data['inscripcion'] = inscripcion
                # data['listado_contenido'] = listado = evento.contenido.split("\n") if evento.contenido else []
                qrname = 'qr_certificado_CRAI_' + str(inscripcion.id)
                # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
                # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
                rutapdf = folder + qrname + '.pdf'
                rutaimg = folder + qrname + '.png'
                if os.path.isfile(rutapdf):
                    os.remove(rutaimg)
                    os.remove(rutapdf)
                url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/certificados/' + qrname + '.pdf')
                # url = pyqrcode.create('http://127.0.0.1:8000//media/qrcode/certificados/' + qrname + '.pdf')
                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                data['qrname'] = 'qr' + qrname
                valida = conviert_html_to_pdfsaveqrcertificado(
                    'adm_configuracion_mundocrai/certificado_pdf.html',
                    {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                )
                if valida:
                    os.remove(rutaimg)
                    inscripcion.rutapdf = 'qrcode/certificados/' + qrname + '.pdf'
                    # inscrito.emailnotificado = True
                    # inscrito.fecha_emailnotifica = datetime.now().date()
                    # inscrito.persona_emailnotifica = persona
                    inscripcion.save(request)
                    # asunto = u"CERTIFICADO - " + inscrito.capeventoperiodo.capevento.nombre
                    # useremail = Persona.objects.get(cedula='0923363030')
                    # send_html_mail(asunto, "emails/notificar_certificado.html",
                    #                {'sistema': request.session['nombresistema'], 'inscrito': inscrito},
                    #                inscrito.participante.emailpersonal(), [], [inscrito.rutapdf],
                    #                # useremail.emailpersonal(), [], [inscrito.rutapdf],
                    #                cuenta=CUENTAS_CORREOS[0][1])
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte."})
                log(u'Aprobo solicitud: %s' % inscripcion, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar los datos."})

        if action == 'generarcertificado':
            try:
                inscripcion = InscripcionCapacitacionesCrai.objects.get(pk=request.POST['id'])
                # generacion de certificado
                data['evento'] = evento = inscripcion.capacitacionescrai
                # validacion de director, coordinador y docente si tiene firma
                director = FirmasCapacitacionesCrai.objects.filter(status=True, tipofirma=3)
                if director:
                    data['director'] = director[0].persona.nombre_completo_inverso_titulo()
                    data['fdirector'] = director[0].archivo.url
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Falta configurar firma del Director."})
                coordinador = FirmasCapacitacionesCrai.objects.filter(status=True, tipofirma=2, tipomundocrai=evento.tipomundocrai)
                if coordinador:
                    data['coordinador'] = coordinador[0].persona.nombre_completo_inverso_titulo()
                    data['fcoordinador'] = coordinador[0].archivo.url
                    if evento.tipomundocrai==1:
                        data['cargo']='COORDINADOR(A) GESTION DE BIBLIOTECA'
                    if evento.tipomundocrai==2:
                        data['cargo']='COORDINADOR(A) GESTION DE SOPORTE A LA DOCENCIA'
                    if evento.tipomundocrai==3:
                        data['cargo']='COORDINADOR(A) GESTION DE SOPORTE A LA INVESTIGACIÓN'
                    if evento.tipomundocrai==4:
                        data['cargo']='COORDINADOR(A) GESTIÓN CULTURAL'
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Falta configurar firma del Coordinador."})
                docenteclase = FirmasCapacitacionesCrai.objects.filter(status=True, tipofirma=1, persona=evento.capacitador)
                if docenteclase:
                    data['docenteclase'] = docenteclase[0].persona.nombre_completo_inverso_titulo()
                    data['fdocenteclase'] = docenteclase[0].archivo.url
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Falta configurar firma del Docente."})
                mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
                fechainicio = evento.fechadesde
                fechafin = evento.fechahasta
                fechacertificado = suma_dias_habiles(fechafin, 7)
                data['fecha'] = u"Milagro, %s de %s del %s" % (fechacertificado.day, str(mes[fechacertificado.month - 1]), fechacertificado.year)
                if fechainicio == fechafin:
                    fechascapacitacion = "el %s de %s del %s" % (fechainicio.day, str(mes[fechainicio.month - 1]), fechainicio.year)
                elif fechainicio.month != fechafin.month:
                    if fechainicio.year == fechafin.year:
                        fechascapacitacion = "del %s de %s al %s de %s del %s" % (fechainicio.day, str(mes[fechainicio.month - 1]), fechafin.day, str(mes[fechafin.month - 1]), fechafin.year)
                    else:
                        fechascapacitacion = "del %s de %s del %s al %s de %s del %s" % (fechainicio.day, str(mes[fechainicio.month - 1]), fechainicio.year, fechafin.day, str(mes[fechafin.month - 1]), fechafin.year)
                else:
                    fechascapacitacion = "del %s al %s de %s del %s" % (fechainicio.day, fechafin.day, str(mes[fechainicio.month - 1]), fechainicio.year)

                data['url_path'] = url_path
                data['fechascapacitacion'] = fechascapacitacion
                data['inscrito'] = inscripcion.inscrito()
                data['inscripcion'] = inscripcion
                mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
                       "octubre", "noviembre", "diciembre"]
                data['fecha'] = u"Milagro, %s de %s del %s" % (datetime.now().day, str(mes[datetime.now().month - 1]), datetime.now().year)
                # data['listado_contenido'] = listado = evento.contenido.split("\n") if evento.contenido else []
                qrname = 'qr_certificado_CRAI_' + str(inscripcion.id)
                # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
                # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
                rutapdf = folder + qrname + '.pdf'
                rutaimg = folder + qrname + '.png'
                if os.path.isfile(rutapdf):
                    os.remove(rutaimg)
                    os.remove(rutapdf)
                url = pyqrcode.create(f'{url_path}//media/qrcode/certificados/' + qrname + '.pdf')
                # url = pyqrcode.create('http://127.0.0.1:8000//media/qrcode/certificados/' + qrname + '.pdf')
                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                data['qrname'] = 'qr' + qrname
                valida = conviert_html_to_pdfsaveqrcertificado(
                    'adm_configuracion_mundocrai/certificado_v2.html',
                    {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                )
                if valida:
                    os.remove(rutaimg)
                    inscripcion.rutapdf = 'qrcode/certificados/' + qrname + '.pdf'
                    # inscrito.emailnotificado = True
                    # inscrito.fecha_emailnotifica = datetime.now().date()
                    # inscrito.persona_emailnotifica = persona
                    inscripcion.save(request)
                    # asunto = u"CERTIFICADO - " + inscrito.capeventoperiodo.capevento.nombre
                    # useremail = Persona.objects.get(cedula='0923363030')
                    # send_html_mail(asunto, "emails/notificar_certificado.html",
                    #                {'sistema': request.session['nombresistema'], 'inscrito': inscrito},
                    #                inscrito.participante.emailpersonal(), [], [inscrito.rutapdf],
                    #                # useremail.emailpersonal(), [], [inscrito.rutapdf],
                    #                cuenta=CUENTAS_CORREOS[0][1])
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte."})
                log(u'Aprobo solicitud: %s' % inscripcion, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar los datos."})

        if action == 'generarcertificadoclub':
            try:
                inscripcion = InscripcionClub.objects.get(pk=request.POST['id'])
                # generacion de certificado
                data['club'] = club = inscripcion.club
                # validacion de director, coordinador y docente si tiene firma
                director = FirmasCapacitacionesCrai.objects.filter(status=True, tipofirma=3)
                if director:
                    data['director'] = director[0].persona.nombre_completo_inverso_titulo()
                    data['fdirector'] = director[0].archivo.url
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Falta configurar firma del Director."})
                coordinador = FirmasCapacitacionesCrai.objects.filter(status=True, tipofirma=2, tipomundocrai=4)
                if coordinador:
                    data['coordinador'] = coordinador[0].persona.nombre_completo_inverso_titulo()
                    data['fcoordinador'] = coordinador[0].archivo.url
                    data['cargo']='COORDINADOR(A) GESTIÓN CULTURAL'
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Falta configurar firma del Coordinador."})
                docenteclase = FirmasCapacitacionesCrai.objects.filter(status=True, tipofirma=1, persona=club.tutorprincipal.persona)
                if docenteclase:
                    data['docenteclase'] = docenteclase[0].persona.nombre_completo_inverso_titulo()
                    data['fdocenteclase'] = docenteclase[0].archivo.url
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Falta configurar firma del Docente."})

                data['inscrito'] = inscripcion.inscripcion.persona.nombre_completo()
                data['inscripcion'] = inscripcion
                mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
                data['fecha'] = u"Milagro, %s de %s del %s" % (datetime.now().day, str(mes[datetime.now().month - 1]), datetime.now().year)
                # data['listado_contenido'] = listado = evento.contenido.split("\n") if evento.contenido else []
                qrname = 'qr_certificado_CLUB_CRAI_' + str(inscripcion.id)
                # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
                # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
                rutapdf = folder + qrname + '.pdf'
                rutaimg = folder + qrname + '.png'
                if os.path.isfile(rutapdf):
                    os.remove(rutaimg)
                    os.remove(rutapdf)
                url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/certificados/' + qrname + '.pdf')
                # url = pyqrcode.create('http://127.0.0.1:8000//media/qrcode/certificados/' + qrname + '.pdf')
                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                data['qrname'] = 'qr' + qrname
                valida = conviert_html_to_pdfsaveqrcertificado(
                    'adm_configuracion_mundocrai/certificado_club_pdf.html',
                    {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                )
                if valida:
                    os.remove(rutaimg)
                    inscripcion.archivo = 'qrcode/certificados/' + qrname + '.pdf'
                    inscripcion.save(request)
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte."})
                log(u'Genero certificado club: %s' % inscripcion, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar los datos."})

        if action == 'segmento_aux':
            try:
                data['id'] = int(request.POST['id'])
                fecha = request.POST['fecha']
                fecha_hasta = request.POST['fecha_hasta']
                fechadatetime = datetime.strptime(fecha, '%d-%m-%Y').date()
                fecha_hastadatetime = datetime.strptime(fecha_hasta, '%d-%m-%Y').date()
                cursor = connection.cursor()
                data['fecha'] = fecha
                data['fecha_hasta'] = fecha_hasta
                data['title'] = u'Gráficas Acceso al Mundo CRAI, fecha desde: ' + fecha + ' fecha hasta: ' + fecha_hasta
                colores = [u"FF3333", u"8AFF33", u"3370FF", u"D733FF", u"FF33A8", u"FF335B", u"33FFA4", u"#b87333",u"silver", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF", u"FF33A8",u"FF335B", u"33FFA4", u"#b87333", u"silver", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33",u"3370FF", u"D733FF", u"FF33A8", u"FF335B", u"33FFA4", u"#b87333", u"silver", u"gold",u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF", u"FF33A8", u"FF335B", u"33FFA4",u"#b87333", u"silver", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF",u"FF33A8", u"FF335B", u"33FFA4", u"#b87333", u"silver", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF", u"FF33A8", u"FF335B", u"33FFA4", u"#b87333",u"silver", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF", u"FF33A8",u"FF335B", u"33FFA4", u"#b87333", u"silver", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33",u"3370FF", u"D733FF", u"FF33A8", u"FF335B", u"33FFA4", u"#b87333", u"silver", u"gold",u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF", u"FF33A8", u"FF335B", u"33FFA4",u"#b87333", u"silver", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF",u"FF33A8", u"FF335B", u"33FFA4", u"#b87333", u"silver", u"gold", u"#e5e4e2"]
                # atras = 0
                # atras = int(request.POST['atras'])
                resultadosgeneral = []
                total = 0
                if fecha != '' and fecha_hasta != '':
                    if int(request.POST['id']) > 0:
                        if int(request.POST['id']) >= 1 and  int(request.POST['id']) <=4 :
                            sql= "select tabla.tipomundocrai, tabla.descripcion, count(tabla.id),tabla.tipo  from " \
                                 "(SELECT (CASE am.tipomundocrai WHEN 1 THEN 'BIBLIOTECA' WHEN 2 THEN 'DOCENCIA' WHEN 3 THEN 'INVESTIGACION' ELSE 'CULTURAL' END) " \
                                 " tipomundocrai, am.descripcion,am.id,(CASE ca.tipoingreso WHEN 1 THEN 'docente' WHEN 2 THEN 'estudiante' ELSE 'administrativo' END) AS tipo " \
                                 " FROM sga_contadoractividadesmundocrai ca, sga_actividadesmundocrai am " \
                                 " WHERE ca.status= TRUE AND ca.actividadesmundocraiprincipal_id=am.id AND am.status= TRUE AND am.tipomundocrai="+ request.POST['id']  +" " \
                                                                                                                                                                        " AND ca.fecha BETWEEN '"+ str(fechadatetime) +"' and '"+ str(fecha_hastadatetime) +"') as tabla " \
                                                                                                                                                                                                                                  " GROUP by tabla.tipomundocrai,tabla.descripcion ,tabla.tipo order by tabla.tipo,tabla.tipomundocrai, tabla.descripcion"
                            cursor.execute(sql)
                            results = cursor.fetchall()
                            resultadosgeneraldocente = []
                            totaldocente = 0
                            i = 0
                            for r in results:
                                if r[3] == 'docente':
                                    resultadosgeneraldocente.append([r[1][:20], r[2], u'%s' % colores[i]])
                                    i += 1
                                    totaldocente = totaldocente + int(r[2])

                            resultadosgeneralestudiante = []
                            totalestudiante = 0
                            i = 0
                            for r in results:
                                if r[3] == 'estudiante':
                                    resultadosgeneralestudiante.append([r[1][:20], r[2], u'%s' % colores[i]])
                                    i += 1
                                    totalestudiante = totalestudiante + int(r[2])

                            resultadosgeneraladministrativo = []
                            totaladministrativo = 0
                            i = 0
                            for r in results:
                                if r[3] == 'administrativo':
                                    resultadosgeneraladministrativo.append([r[1][:20], r[2], u'%s' % colores[i]])
                                    i += 1
                                    totaladministrativo = totaladministrativo + int(r[2])

                            sql_aux = "select " \
                                      " (select count(distinct per1.id) from sga_contadoractividadesmundocrai ca1, sga_actividadesmundocrai am1, auth_user u1, sga_persona per1  where " \
                                      " ca1.status= TRUE AND ca1.actividadesmundocraiprincipal_id=am1.id AND am1.status= TRUE AND am1.tipomundocrai="+ request.POST['id'] +" and  " \
                                                                                                                                                                           " ca1.usuario_creacion_id=u1.id AND per1.usuario_id=u1.id AND per1.status=TRUE  " \
                                                                                                                                                                           " AND ca1.fecha BETWEEN '"+ str(fechadatetime) +"' and '"+ str(fecha_hastadatetime) +"') as total, " \
                                                                                                                                                                                                                                      " (select count(distinct ca1.usuario_creacion_id) from sga_contadoractividadesmundocrai ca1, sga_actividadesmundocrai am1 " \
                                                                                                                                                                                                                                      " where ca1.status= TRUE AND ca1.actividadesmundocraiprincipal_id=am1.id AND am1.status=TRUE and ca1.tipoingreso=1 AND am1.tipomundocrai="+ request.POST['id'] +" and " \
                                                                                                                                                                                                                                                                                                                                                                                                      " ca1.fecha BETWEEN '"+ str(fechadatetime) +"' and '"+ str(fecha_hastadatetime) +"') as docente, " \
                                                                                                                                                                                                                                                                                                                                                                                                                                                             " (select count(distinct ca1.usuario_creacion_id) from sga_contadoractividadesmundocrai ca1, sga_actividadesmundocrai am1 " \
                                                                                                                                                                                                                                                                                                                                                                                                                                                             " where ca1.status= TRUE AND ca1.actividadesmundocraiprincipal_id=am1.id AND am1.status=TRUE and ca1.tipoingreso=2 AND am1.tipomundocrai="+ request.POST['id'] +" and " \
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             " ca1.fecha BETWEEN '"+ str(fechadatetime) +"' and '"+ str(fecha_hastadatetime) +"') as estudiante,  " \
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    " (select count(distinct ca1.usuario_creacion_id) from sga_contadoractividadesmundocrai ca1, sga_actividadesmundocrai am1 " \
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    " where ca1.status= TRUE AND ca1.actividadesmundocraiprincipal_id=am1.id AND am1.status=TRUE and ca1.tipoingreso=3 AND am1.tipomundocrai="+ request.POST['id'] +" and " \
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    " ca1.fecha BETWEEN '"+ str(fechadatetime) +"' and '"+ str(fecha_hastadatetime) +"') as administrativo;"
                            cursor.execute(sql_aux)
                            results_aux = cursor.fetchall()
                            totaldocenteindividual = 0
                            totalestudianteindividual = 0
                            totaladministrativoindividual = 0
                            for aux in results_aux:
                                totaldocenteindividual = aux[1]
                                totalestudianteindividual = aux[2]
                                totaladministrativoindividual = aux[3]

                            data['totaldocente'] = totaldocente
                            data['totaldocenteindividual'] = totaldocenteindividual
                            data['totalestudiante'] = totalestudiante
                            data['totalestudianteindividual'] = totalestudianteindividual
                            data['totaladministrativo'] = totaladministrativo
                            data['totaladministrativoindividual'] = totaladministrativoindividual
                            data['resultadosgeneraldocente'] = resultadosgeneraldocente
                            data['resultadosgeneralestudiante'] = resultadosgeneralestudiante
                            data['resultadosgeneraladministrativo'] = resultadosgeneraladministrativo
                            template = get_template("adm_configuracion_mundocrai/segmento_aux.html")
                        if int(request.POST['id']) == 5:
                            fecha = convertir_fecha(request.POST['fecha'])
                            fecha_hasta = convertir_fecha(request.POST['fecha_hasta'])
                            capacitacionescrais = CapacitacionesCrai.objects.filter(status=True,fechadesde__range=(fecha, fecha_hasta)).order_by('id')
                            data['capacitacionescrais'] = capacitacionescrais
                            template = get_template("adm_configuracion_mundocrai/segmento_aux_capacitacion.html")
                        if int(request.POST['id']) == 6:
                            fecha = convertir_fecha(request.POST['fecha'])
                            fecha_hasta = convertir_fecha(request.POST['fecha_hasta'])
                            reservascrais = ReservasCrai.objects.filter(status=True,fecha__range=(fecha, fecha_hasta)).order_by('id')
                            data['reservascrais'] = reservascrais
                            template = get_template("adm_configuracion_mundocrai/segmento_aux_reserva.html")


                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Seleccione bien las fechas"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'reservapdf':
            try:
                salas = SalaCrai.objects.filter(status=True, tipo=5).order_by('id')
                data['salacrais'] = salas
                return conviert_html_to_pdf(
                    'adm_configuracion_mundocrai/reservapdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        if action == 'estadistica1':
            try:
                data['id'] = int(request.POST['id'])
                capacitacion = CapacitacionesCrai.objects.get(pk=int(request.POST['id']))
                cursor = connection.cursor()
                data['title'] = u'Gráficas resultado encuesta satisfacción'
                colores = [u"FF3333", u"8AFF33", u"3370FF", u"D733FF", u"FF33A8", u"FF335B", u"33FFA4", u"#b87333",u"silver", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF", u"FF33A8",u"FF335B", u"33FFA4", u"#b87333", u"silver", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33",u"3370FF", u"D733FF", u"FF33A8", u"FF335B", u"33FFA4", u"#b87333", u"silver", u"gold",u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF", u"FF33A8", u"FF335B", u"33FFA4",u"#b87333", u"silver", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF",u"FF33A8", u"FF335B", u"33FFA4", u"#b87333", u"silver", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF", u"FF33A8", u"FF335B", u"33FFA4", u"#b87333",u"silver", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF", u"FF33A8",u"FF335B", u"33FFA4", u"#b87333", u"silver", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33",u"3370FF", u"D733FF", u"FF33A8", u"FF335B", u"33FFA4", u"#b87333", u"silver", u"gold",u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF", u"FF33A8", u"FF335B", u"33FFA4",u"#b87333", u"silver", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF",u"FF33A8", u"FF335B", u"33FFA4", u"#b87333", u"silver", u"gold", u"#e5e4e2"]
                r = []
                resultadosgeneral1 = []
                bandera1=False
                pregunta1=''
                resultadosgeneral2 = []
                bandera2 = False
                pregunta2 = ''
                resultadosgeneral3 = []
                bandera3 = False
                pregunta3 = ''
                resultadosgeneral4 = []
                bandera4 = False
                pregunta4 = ''
                resultadosgeneral5 = []
                bandera5 = False
                pregunta5 = ''
                resultadosgeneral6 = []
                bandera6 = False
                pregunta6 = ''
                resultadosgeneral7 = []
                bandera7 = False
                pregunta7 = ''
                resultadosgeneral8 = []
                bandera8 = False
                pregunta8 = ''
                resultadosgeneral9 = []
                bandera9 = False
                pregunta9 = ''
                resultadosgeneral10 = []
                bandera10 = False
                pregunta10 = ''
                if int(request.POST['id']) > 0:
                    sql="SELECT ns.id, ns.orden, ns.nivel FROM sga_nivelsatisfacionencuestacapacitacionescrai ns WHERE ns.encuesta_id="+ str(capacitacion.encuesta_id)  +" AND ns.status= true order by ns.orden"
                    cursor.execute(sql)
                    resultsnivel = cursor.fetchall()
                    sql2= "select pe.pregunta "
                    for r in resultsnivel:
                        sql2= sql2 + ",(select count(rc.id) from sga_respuestaencuestainscripcioncapacitacionescrai rc, sga_encuestainscripcioncapacitacionescrai ei, sga_inscripcioncapacitacionescrai i " \
                                    " where rc.encuestainscripcion_id=ei.id AND rc.status= TRUE AND ei.status= TRUE AND ei.encuesta_id=e.id and ei.inscripcion_id=i.id and i.status=true AND rc.pregunta_id=pe.id and i.capacitacionescrai_id=ca.id AND rc.nivel_id="+ str(r[0]) +") as a "

                    sql2 = sql2 + " from sga_capacitacionescrai ca, sga_encuestacapacitacionescrai e, sga_preguntasencuestacapacitacionescrai pe " \
                                  " where ca.id="+ request.POST['id'] +" and ca.status=true and ca.encuesta_id=e.id and e.status=true and pe.encuesta_id=e.id and pe.status=true"

                    cursor.execute(sql2)
                    results = cursor.fetchall()
                    i = 0
                    # , u'%s' % colores[i]
                    for r in results:
                        if resultadosgeneral1==[]:
                            j=1
                            pregunta1=r[0]
                            for rn in resultsnivel:
                                resultadosgeneral1.append([r[0], rn[2] , r[j], u'%s' % colores[j]])
                                j += 1
                                bandera1 = True
                        else:
                            if resultadosgeneral2==[]:
                                j = 1
                                pregunta2 = r[0]
                                for rn in resultsnivel:
                                    resultadosgeneral2.append([r[0], rn[2], r[j], u'%s' % colores[j]])
                                    j += 1
                                    bandera2 = True
                            else:
                                if resultadosgeneral3==[]:
                                    j = 1
                                    pregunta3 = r[0]
                                    for rn in resultsnivel:
                                        resultadosgeneral3.append([r[0], rn[2], r[j], u'%s' % colores[j]])
                                        j += 1
                                        bandera3 = True
                                else:
                                    if resultadosgeneral4==[]:
                                        j = 1
                                        pregunta4 = r[0]
                                        for rn in resultsnivel:
                                            resultadosgeneral4.append([r[0], rn[2], r[j], u'%s' % colores[j]])
                                            j += 1
                                            bandera4 = True
                                    else:
                                        if resultadosgeneral5==[]:
                                            j = 1
                                            pregunta5 = r[0]
                                            for rn in resultsnivel:
                                                resultadosgeneral5.append([r[0], rn[2], r[j], u'%s' % colores[j]])
                                                j += 1
                                                bandera5 = True
                                        else:
                                            if resultadosgeneral6==[]:
                                                j = 1
                                                pregunta6 = r[0]
                                                for rn in resultsnivel:
                                                    resultadosgeneral6.append([r[0], rn[2], r[j], u'%s' % colores[j]])
                                                    j += 1
                                                    bandera6 = True
                                            else:
                                                if resultadosgeneral7==[]:
                                                    j = 1
                                                    pregunta7 = r[0]
                                                    for rn in resultsnivel:
                                                        resultadosgeneral7.append([r[0], rn[2], r[j], u'%s' % colores[j]])
                                                        j += 1
                                                        bandera7 = True
                                                else:
                                                    if resultadosgeneral8==[]:
                                                        j = 1
                                                        pregunta8 = r[0]
                                                        for rn in resultsnivel:
                                                            resultadosgeneral8.append([r[0], rn[2], r[j], u'%s' % colores[j]])
                                                            j += 1
                                                            bandera8 = True
                                                    else:
                                                        if resultadosgeneral9==[]:
                                                            j = 1
                                                            pregunta9 = r[0]
                                                            for rn in resultsnivel:
                                                                resultadosgeneral9.append([r[0], rn[2], r[j], u'%s' % colores[j]])
                                                                j += 1
                                                                bandera9 = True
                                                        else:
                                                            if resultadosgeneral10==[]:
                                                                j = 1
                                                                pregunta10 = r[0]
                                                                for rn in resultsnivel:
                                                                    resultadosgeneral10.append([r[0], rn[2], r[j], u'%s' % colores[j]])
                                                                    j += 1
                                                                    bandera10 = True

                        i += 1
                    data['resultadosgeneral1'] = resultadosgeneral1
                    data['bandera1'] = bandera1
                    data['pregunta1'] = pregunta1
                    data['resultadosgeneral2'] = resultadosgeneral2
                    data['bandera2'] = bandera2
                    data['pregunta2'] = pregunta2
                    data['resultadosgeneral3'] = resultadosgeneral3
                    data['bandera3'] = bandera3
                    data['pregunta3'] = pregunta3
                    data['resultadosgeneral4'] = resultadosgeneral4
                    data['bandera4'] = bandera4
                    data['pregunta4'] = pregunta4
                    data['resultadosgeneral5'] = resultadosgeneral5
                    data['bandera5'] = bandera5
                    data['pregunta5'] = pregunta5
                    data['resultadosgeneral6'] = resultadosgeneral6
                    data['bandera6'] = bandera6
                    data['pregunta6'] = pregunta6
                    data['resultadosgeneral7'] = resultadosgeneral7
                    data['bandera7'] = bandera7
                    data['pregunta7'] = pregunta7
                    data['resultadosgeneral8'] = resultadosgeneral8
                    data['bandera8'] = bandera8
                    data['pregunta8'] = pregunta8
                    data['resultadosgeneral9'] = resultadosgeneral9
                    data['bandera9'] = bandera9
                    data['pregunta9'] = pregunta9
                    data['resultadosgeneral10'] = resultadosgeneral10
                    data['bandera10'] = bandera10
                    data['pregunta10'] = pregunta10
                    template = get_template("adm_configuracion_mundocrai/estadistica1.html")

                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'addseccion':
            try:
                f = SeccionClubesForm(request.POST, request.FILES)
                d = request.FILES['icono']
                if d.size > 2097152:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 2 Mb."})
                newfiles = request.FILES['icono']
                newfilesd = newfiles._name
                ext = newfilesd[newfilesd.rfind("."):]
                if ext != '.jpg' and ext != '.png':
                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .jpg,.png"})

                if f.is_valid():
                    newfile = None
                    if 'icono' in request.FILES:
                        newfile = request.FILES['icono']
                    if not SeccionClub.objects.filter(nombre=f.cleaned_data['nombre'] ,status=True).exists():
                        seccion = SeccionClub(nombre=f.cleaned_data['nombre'],
                                              icono=newfile)
                        seccion.save(request)
                        log(u'añade sección club: %s' % seccion, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"La sección ya se encuentra registrada."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editseccion':
            try:
                f = SeccionClubesForm(request.POST, request.FILES)
                seccionclub = SeccionClub.objects.get(pk=request.POST['id'])
                if 'icono' in request.FILES:
                    d = request.FILES['icono']
                    if d.size > 2097152:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 2 Mb."})
                    newfiles = request.FILES['icono']
                    newfilesd = newfiles._name
                    ext = newfilesd[newfilesd.rfind("."):]
                    if ext != '.jpg' and ext != '.png':
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .jpg,.png"})

                if f.is_valid():
                    seccionclub.nombre = f.cleaned_data['nombre']
                    if 'icono' in request.FILES:
                        seccionclub.icono = newfiles
                    seccionclub.save(request)
                    log(u'edito seccion club: %s' % seccionclub, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteseccion':
            try:
                seccionclub = SeccionClub.objects.get(pk=request.POST['id'])
                log(u'elimino area de periodo: %s' % seccionclub, request, "del")
                seccionclub.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addclub':
            try:
                f = ClubesForm(request.POST, request.FILES)
                d = request.FILES['icono']
                if d.size > 2097152:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 2 Mb."})
                newfiles = request.FILES['icono']
                newfilesd = newfiles._name
                ext = newfilesd[newfilesd.rfind("."):]
                if ext != '.jpg' and ext != '.png':
                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .jpg,.png"})
                if f.is_valid():
                    club = Club(seccionclub_id=request.POST['id'],
                                coordinacion=f.cleaned_data['coordinacion'],
                                carrera=f.cleaned_data['carrera'],
                                nombre=f.cleaned_data['nombre'],
                                descripcion=f.cleaned_data['descripcion'],
                                fechainicio=f.cleaned_data['fechainicio'],
                                fechafin=f.cleaned_data['fechafin'],
                                fechainicioinscripcion=f.cleaned_data['fechainicioinscripcion'],
                                fechafininscripcion=f.cleaned_data['fechafininscripcion'],
                                cupo=f.cleaned_data['cupo'],
                                tutorprincipal_id=f.cleaned_data['tutorprincipal'],
                                icono=newfiles)
                    club.save(request)
                    log(u'Adiciono club: %s %s %s' % (club.id, club, club.cupo), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editclub':
            try:
                f = ClubesForm(request.POST, request.FILES)
                if 'icono' in request.FILES:
                    d = request.FILES['icono']
                    if d.size > 2097152:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 2 Mb."})
                    newfiles = request.FILES['icono']
                    newfilesd = newfiles._name
                    ext = newfilesd[newfilesd.rfind("."):]
                    if ext != '.jpg' and ext != '.png':
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .jpg,.png"})

                club = Club.objects.get(pk=request.POST['id'])
                totalinscritos = InscripcionClub.objects.filter(club=club, status=True).count()
                if f.is_valid():
                    if f.cleaned_data['cupo'] < totalinscritos:
                        return JsonResponse({"result": "bad","mensaje": u"Lo sentimos, ya existe un número mayor de estudiantes inscritos en la actividad."})
                    club.nombre = f.cleaned_data['nombre']
                    club.coordinacion = f.cleaned_data['coordinacion']
                    club.descripcion = f.cleaned_data['descripcion']
                    club.fechainicio = f.cleaned_data['fechainicio']
                    club.fechafin = f.cleaned_data['fechafin']
                    club.fechainicioinscripcion = f.cleaned_data['fechainicioinscripcion']
                    club.fechafininscripcion = f.cleaned_data['fechafininscripcion']
                    club.cupo = f.cleaned_data['cupo']
                    club.tutorprincipal_id = f.cleaned_data['tutorprincipal']
                    club.carrera = f.cleaned_data['carrera']
                    if 'icono' in request.FILES:
                        club.icono=newfiles
                    club.save(request)
                    log(u'Edito club: %s %s %s %s Fecha ini: %s Fecha fin: %s' % (club.id, club, club.cupo, club.coordinacion, club.fechainicio, club.fechafin), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        elif action == 'deleteclub':
            try:
                club = Club.objects.get(pk=request.POST['id'])
                log(u'elimino actividad: %s' % club, request, "del")
                club.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'enviareliminacion':
            try:
                if InscripcionClub.objects.get(status=True,pk=request.POST['id']):
                    inscripcion=InscripcionClub.objects.get(status=True,pk=request.POST['id'])
                    inscripcion.aprobacion=int(request.POST['estado'])
                    inscripcion.save(request)
                    log(u'Cambio %s estado de solicitud elimimacion club: %s' % ( persona,inscripcion), request, "edit")

                    if int(request.POST['estado']) == 3:
                        # generacion de certificado
                        data['club'] = club = inscripcion.club
                        # validacion de director, coordinador y docente si tiene firma
                        director = FirmasCapacitacionesCrai.objects.filter(status=True, tipofirma=3)
                        if director:
                            data['director'] = director[0].persona.nombre_completo_inverso_titulo()
                            data['fdirector'] = director[0].archivo.url
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Falta configurar firma del Director."})
                        coordinador = FirmasCapacitacionesCrai.objects.filter(status=True, tipofirma=2, tipomundocrai=4)
                        if coordinador:
                            data['coordinador'] = coordinador[0].persona.nombre_completo_inverso_titulo()
                            data['fcoordinador'] = coordinador[0].archivo.url
                            data['cargo'] = 'COORDINADOR(A) GESTIÓN CULTURAL'
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Falta configurar firma del Coordinador."})
                        docenteclase = FirmasCapacitacionesCrai.objects.filter(status=True, tipofirma=1,
                                                                               persona=club.tutorprincipal.persona)
                        if docenteclase:
                            data['docenteclase'] = docenteclase[0].persona.nombre_completo_inverso_titulo()
                            data['fdocenteclase'] = docenteclase[0].archivo.url
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Falta configurar firma del Docente."})

                        data['inscrito'] = inscripcion.inscripcion.persona.nombre_completo()
                        data['inscripcion'] = inscripcion
                        mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
                               "octubre", "noviembre", "diciembre"]
                        data['fecha'] = u"Milagro, %s de %s del %s" % (
                        datetime.now().day, str(mes[datetime.now().month - 1]), datetime.now().year)
                        # data['listado_contenido'] = listado = evento.contenido.split("\n") if evento.contenido else []
                        qrname = 'qr_certificado_CLUB_CRAI_' + str(inscripcion.id)
                        folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
                        rutapdf = folder + qrname + '.pdf'
                        rutaimg = folder + qrname + '.png'
                        if os.path.isfile(rutapdf):
                            os.remove(rutaimg)
                            os.remove(rutapdf)
                        url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/certificados/' + qrname + '.pdf')
                        # url = pyqrcode.create('http://127.0.0.1:8000//media/qrcode/certificados/' + qrname + '.pdf')
                        imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                        data['qrname'] = 'qr' + qrname
                        valida = conviert_html_to_pdfsaveqrcertificado(
                            'adm_configuracion_mundocrai/certificado_club_pdf.html',
                            {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                        )
                        if valida:
                            os.remove(rutaimg)
                            inscripcion.archivo = 'qrcode/certificados/' + qrname + '.pdf'
                            inscripcion.save(request)
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte."})
                        log(u'Genero certificado club: %s' % inscripcion, request, "edit")

                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Ya envió solicitud."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'pdflistainscritos':
            try:
                club = Club.objects.get(pk=request.POST['idclub'])
                return conviert_html_to_pdf(
                    'adm_configuracion_mundocrai/inscritosclub_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': club.listado_inscritos_reporte(),
                    }
                )
            except Exception as ex:
                return JsonResponse(  {"result": "bad", "mensaje": u"Problemas al ejecutar el reporte. %s" % ex})

        elif action == 'deleteparticipante':
            try:
                inscrito = InscripcionClub.objects.get(pk=request.POST['id'])
                log(u'Eliminó participante club CRAI: %s' % inscrito, request, "del")
                inscrito.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'notificarpersonalizada':
            try:
                id = int(request.POST['id'])
                instancia = CapacitacionesCrai.objects.get(id=id)
                estados = request.POST.getlist('estado')
                if not estados:
                    raise NameError('Seleccione como minimo un estado')
                titulo = request.POST['titulo']
                cabecera = request.POST['cabecera']
                mensaje = request.POST['mensaje_at']
                filtro = Q(status=True)
                for estado in estados:
                    if int(estado)==1:
                        filtro = filtro & Q(aprobado=True)
                    else:
                        filtro = filtro & Q(aprobado=False)

                inscritos = instancia.inscripcioncapacitacionescrai_set.filter(filtro)

                if not inscritos:
                    raise NameError('No existen inscritos con el estado seleccionado')

                for i in inscritos:
                    pers = i.inscripcion.persona if i.inscripcion else i.profesor.persona
                    lista_email = pers.lista_emails()
                    # lista_email = ['jguachuns@unemi.edu.ec', ]
                    datos_email = {'sistema': request.session['nombresistema'],
                                   'fecha': datetime.now().date(),
                                   'hora': datetime.now().time(),
                                   # 'evento': evento,
                                   'titulo': titulo,
                                   'cabecera': cabecera,
                                   'persona': pers,
                                   'mensaje': mensaje}
                    template = "emails/notificacionpersonalizada_at.html"
                    send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])
                log(u'Notifico mensaje a personas consideradas en cronograma: %s' % instancia, request, "edit")
                return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Listado de Actividades Mundo-Crai'
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar Actividad Mundo-Crai'
                    data['form'] = ActividadesMundoCraiForm()
                    return render(request, "adm_configuracion_mundocrai/add.html", data)
                except Exception as ex:
                    pass

            if action == 'adddocente':
                try:
                    capacitacion = CapacitacionesCrai.objects.get(pk=int(request.GET['id']))
                    data['title'] = u'Adicionar Docente a Capacitacion - %s' % capacitacion.tema
                    data['id'] = request.GET['id']
                    data['form'] = DocenteCapacitacionForm()
                    return render(request, "adm_configuracion_mundocrai/adddocente.html", data)
                except Exception as ex:
                    pass

            if action == 'addinscripcion':
                try:
                    capacitacion = CapacitacionesCrai.objects.get(pk=int(request.GET['id']))
                    data['title'] = u'Adicionar Estudiante a Capacitacion - %s' % capacitacion.tema
                    data['id'] = request.GET['id']
                    data['form'] = InscripcionCapacitacionForm()
                    return render(request, "adm_configuracion_mundocrai/addinscripcion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addinscripcionclub':
                try:
                    data['club'] = club = Club.objects.get(pk=request.GET['id'])
                    data['title'] = u'Inscribir ' + str(club.nombre)
                    form = InscripcionclubesForm()
                    data['form'] = form
                    return render(request, "adm_configuracion_mundocrai/addinscripcionclub.html", data)
                except Exception as ex:
                    pass

            if action == 'addnoticia':
                try:
                    data['title'] = u'Adicionar Noticia Mundo-Crai'
                    data['form'] = NoticiasMundoCraiForm()
                    return render(request, "adm_configuracion_mundocrai/addnoticia.html", data)
                except Exception as ex:
                    pass

            if action == 'addreservacubiculo':
                try:
                    data['title'] = u'Adicionar Reserva Cubículo CRAI'
                    data['cubiculoid'] = request.GET['ids']
                    data['form'] = ReservaCubiculoCraiForm(initial={'fechadesde': date.today()})
                    return render(request, "adm_configuracion_mundocrai/addreservacubiculo.html", data)
                except Exception as ex:
                    pass

            if action == 'addorganigrama':
                try:
                    crai = persona.mi_departamento()
                    data['title'] = u'Adicionar Organigrama Crai'
                    form = OrganigramaForm()
                    form.adicionar(crai)
                    data['form'] = form
                    return render(request, "adm_configuracion_mundocrai/addorganigrama.html", data)
                except Exception as ex:
                    pass

            if action == 'addfirma':
                try:
                    data['title'] = u'Adicionar Firma Mundo-Crai'
                    data['form'] = FirmaMundoCraiForm()
                    return render(request, "adm_configuracion_mundocrai/addfirma.html", data)
                except Exception as ex:
                    pass

            if action == 'addencuesta':
                try:
                    data['title'] = u'Adicionar Encuesta Mundo-Crai'
                    data['form'] = EncuestaMundoCraiForm()
                    return render(request, "adm_configuracion_mundocrai/addencuesta.html", data)
                except Exception as ex:
                    pass

            if action == 'addpregunta':
                try:
                    data['title'] = u'Adicionar Pregunta Encuesta Mundo-Crai'
                    data['id'] = request.GET['id']
                    data['form'] = PreguntaEncuestaMundoCraiForm()
                    return render(request, "adm_configuracion_mundocrai/addpregunta.html", data)
                except Exception as ex:
                    pass

            if action == 'addnivel':
                try:
                    data['title'] = u'Adicionar Nivel Encuesta Mundo-Crai'
                    data['id'] = request.GET['id']
                    data['form'] = NivelEncuestaMundoCraiForm()
                    return render(request, "adm_configuracion_mundocrai/addnivel.html", data)
                except Exception as ex:
                    pass

            if action == 'addsala':
                try:
                    data['title'] = u'Adicionar Sala Mundo-Crai'
                    data['form'] = SalasMundoCraiForm()
                    return render(request, "adm_configuracion_mundocrai/addsala.html", data)
                except Exception as ex:
                    pass

            if action == 'addnoticia':
                try:
                    data['title'] = u'Adicionar Noticia Mundo-Crai'
                    data['form'] = NoticiasMundoCraiForm()
                    return render(request, "adm_configuracion_mundocrai/addnoticia.html", data)
                except Exception as ex:
                    pass

            if action == 'addcapacitacion':
                try:
                    data['title'] = u'Adicionar Capacitación Mundo-Crai'
                    data['form'] = CapacitacionMundoCraiForm()
                    return render(request, "adm_configuracion_mundocrai/addcapacitacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Editar Actividad Mundo-Crai'
                    actividadesmundocrai1 = ActividadesMundoCrai.objects.get(pk=request.GET['id'])
                    detalle1 = None
                    detalle = ActividadesMundoCraiDetalle.objects.filter(status=True,actividadesmundocraidetalle=actividadesmundocrai1)
                    if detalle:
                        detalle1 = detalle[0].actividadesmundocraiprincipal
                    f = ActividadesMundoCraiForm(initial={'descripcion': actividadesmundocrai1.descripcion,
                                                          'concepto': actividadesmundocrai1.concepto,
                                                          'tipomundocrai': actividadesmundocrai1.tipomundocrai,
                                                          'tipoactividad': actividadesmundocrai1.tipoactividad,
                                                          'orden': actividadesmundocrai1.orden,
                                                          'principal': actividadesmundocrai1.principal,
                                                          'enlace': actividadesmundocrai1.enlace,
                                                          'video': actividadesmundocrai1.video,
                                                          'estado': actividadesmundocrai1.estado,
                                                          'actividadesmundocrai': detalle1})
                    f.editar(actividadesmundocrai1)
                    data['form'] = f
                    data['actividadesmundocrai1'] = actividadesmundocrai1
                    return render(request, "adm_configuracion_mundocrai/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'editnoticia':
                try:
                    data['title'] = u'Editar Noticias Mundo-Crai'
                    noticia = NoticiasMundoCrai.objects.get(pk=request.GET['id'])
                    f = NoticiasMundoCraiForm(initial={'descripcion': noticia.descripcion,
                                                       'titulo': noticia.titulo,
                                                       'enlace': noticia.enlace,
                                                       'estado': noticia.estado})
                    data['form'] = f
                    data['noticia'] = noticia
                    return render(request, "adm_configuracion_mundocrai/editnoticia.html", data)
                except Exception as ex:
                    pass

            elif action == 'terminarreserva_cubiculo':
                try:
                    data['title'] = u'Terminar Reserva Cubículo Crai'
                    reserva = ReservasCubiculosCrai.objects.get(pk=request.GET['id'])
                    f = TerminarReservaCubiculoCraiForm(initial={'profesor': reserva.profesor.persona,
                                                                 'fechahasta': date.today()})
                    f.editar()
                    data['form'] = f
                    data['reserva'] = reserva
                    return render(request, "adm_configuracion_mundocrai/terminarreserva_cubiculo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editorganigrama':
                try:
                    data['title'] = u'Editar Organigrama Crai'
                    organigrama = Organigrama.objects.get(pk=request.GET['id'])
                    f = OrganigramaForm(initial={'seccion': organigrama.seccion,
                                                 'nivel_puesto': organigrama.nivel_puesto})
                    f.editar(organigrama)
                    data['form'] = f
                    data['organigrama'] = organigrama
                    return render(request, "adm_configuracion_mundocrai/editorganigrama.html", data)
                except Exception as ex:
                    pass

            elif action == 'editfirma':
                try:
                    data['title'] = u'Editar Firma Mundo-Crai'
                    firma = FirmasCapacitacionesCrai.objects.get(pk=request.GET['id'])
                    f = FirmaMundoCraiForm(initial={'tipofirma': firma.tipofirma,
                                                    'tipomundocrai': firma.tipomundocrai})
                    f.editar(firma)
                    data['form'] = f
                    data['firma'] = firma
                    return render(request, "adm_configuracion_mundocrai/editfirma.html", data)
                except Exception as ex:
                    pass

            elif action == 'editencuesta':
                try:
                    data['title'] = u'Editar Encuesta Mundo-Crai'
                    encuestacapacitacionescrai = EncuestaCapacitacionesCrai.objects.get(pk=request.GET['id'])
                    f = EncuestaMundoCraiForm(initial={'descripcion': encuestacapacitacionescrai.descripcion,
                                                       'estado': encuestacapacitacionescrai.estado})
                    data['form'] = f
                    data['encuestacapacitacionescrai'] = encuestacapacitacionescrai
                    return render(request, "adm_configuracion_mundocrai/editencuesta.html", data)
                except Exception as ex:
                    pass

            elif action == 'editpregunta':
                try:
                    data['title'] = u'Editar Pregunta Mundo-Crai'
                    preguntasencuestacapacitacionescrai = PreguntasEncuestaCapacitacionesCrai.objects.get(pk=request.GET['id'])
                    f = PreguntaEncuestaMundoCraiForm(initial={'pregunta': preguntasencuestacapacitacionescrai.pregunta})
                    data['form'] = f
                    data['preguntasencuestacapacitacionescrai'] = preguntasencuestacapacitacionescrai
                    data['id'] = preguntasencuestacapacitacionescrai.encuesta_id
                    return render(request, "adm_configuracion_mundocrai/editpregunta.html", data)
                except Exception as ex:
                    pass

            elif action == 'editnivel':
                try:
                    data['title'] = u'Editar Nivel Mundo-Crai'
                    nivelsatisfacionencuestacapacitacionescrai = NivelSatisfacionEncuestaCapacitacionesCrai.objects.get(pk=request.GET['id'])
                    f = NivelEncuestaMundoCraiForm(initial={'nivel': nivelsatisfacionencuestacapacitacionescrai.nivel,
                                                            'orden': nivelsatisfacionencuestacapacitacionescrai.orden,
                                                            'puntaje': nivelsatisfacionencuestacapacitacionescrai.puntaje})
                    data['form'] = f
                    data['nivelsatisfacionencuestacapacitacionescrai'] = nivelsatisfacionencuestacapacitacionescrai
                    data['id'] = nivelsatisfacionencuestacapacitacionescrai.encuesta_id
                    return render(request, "adm_configuracion_mundocrai/editnivel.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcapacitacion':
                try:
                    data['title'] = u'Editar Capacitación Mundo-Crai'
                    capacitacionescrai = CapacitacionesCrai.objects.get(pk=request.GET['id'])
                    f = CapacitacionMundoCraiForm(initial={'tema': capacitacionescrai.tema,
                                                           'contenido': capacitacionescrai.contenido,
                                                           'salacrai': capacitacionescrai.salacrai,
                                                           'fechadesde': capacitacionescrai.fechadesde,
                                                           'fechahasta': capacitacionescrai.fechahasta,
                                                           'horadesde': capacitacionescrai.horadesde,
                                                           'horahasta': capacitacionescrai.horahasta,
                                                           'tipo': capacitacionescrai.tipo,
                                                           'encuesta': capacitacionescrai.encuesta,
                                                           'tipomundocrai': capacitacionescrai.tipomundocrai,
                                                           'cupo': capacitacionescrai.cupo,
                                                           'horastotal':capacitacionescrai.horas})
                    f.editar(capacitacionescrai)
                    data['form'] = f
                    data['capacitacionescrai'] = capacitacionescrai
                    return render(request, "adm_configuracion_mundocrai/editcapacitacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'editsala':
                try:
                    data['title'] = u'Editar Sala Mundo-Crai'
                    salacrai = SalaCrai.objects.get(pk=request.GET['id'])
                    f = SalasMundoCraiForm(initial={'nombre': salacrai.nombre,
                                                    'capacidad': salacrai.capacidad,
                                                    'ubicacion': salacrai.ubicacion,
                                                    'tipo': salacrai.tipo})
                    data['form'] = f
                    data['salacrai'] = salacrai
                    return render(request, "adm_configuracion_mundocrai/editsala.html", data)
                except Exception as ex:
                    pass

            elif action == 'delete':
                try:
                    data['title'] = u'Eliminar Actividad Mundo-Crai'
                    data['actividadesmundocrai'] = ActividadesMundoCrai.objects.get(pk=request.GET['id'])
                    return render(request, "adm_configuracion_mundocrai/delete.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletenoticia':
                try:
                    data['title'] = u'Eliminar Noticia Mundo-Crai'
                    data['noticia'] = NoticiasMundoCrai.objects.get(pk=request.GET['id'])
                    return render(request, "adm_configuracion_mundocrai/deletenoticia.html", data)
                except Exception as ex:
                    pass

            elif action == 'delreserva_cubiculo':
                try:
                    data['title'] = u'Eliminar Reserva Cubículo Crai'
                    data['reserva'] = ReservasCubiculosCrai.objects.get(pk=request.GET['id'])
                    return render(request, "adm_configuracion_mundocrai/delreserva_cubiculo.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteorganigrama':
                try:
                    data['title'] = u'Eliminar Organigrama Crai'
                    data['organigrama'] = Organigrama.objects.get(pk=request.GET['id'])
                    return render(request, "adm_configuracion_mundocrai/deleteorganigrama.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletefirma':
                try:
                    data['title'] = u'Eliminar Firma Mundo-Crai'
                    data['firma'] = FirmasCapacitacionesCrai.objects.get(pk=request.GET['id'])
                    return render(request, "adm_configuracion_mundocrai/deletefirma.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteencuesta':
                try:
                    data['title'] = u'Eliminar Encuesta Mundo-Crai'
                    data['encuestacapacitacionescrai'] = EncuestaCapacitacionesCrai.objects.get(pk=request.GET['id'])
                    return render(request, "adm_configuracion_mundocrai/deleteencuesta.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletepregunta':
                try:
                    data['title'] = u'Eliminar Pregunta Mundo-Crai'
                    data['preguntasencuestacapacitacionescrai'] = preguntasencuestacapacitacionescrai = PreguntasEncuestaCapacitacionesCrai.objects.get(pk=request.GET['id'])
                    data['id'] = preguntasencuestacapacitacionescrai.encuesta_id
                    return render(request, "adm_configuracion_mundocrai/deletepregunta.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletenivel':
                try:
                    data['title'] = u'Eliminar Encuesta Mundo-Crai'
                    data['nivelsatisfacionencuestacapacitacionescrai'] = nivelsatisfacionencuestacapacitacionescrai = NivelSatisfacionEncuestaCapacitacionesCrai.objects.get(pk=request.GET['id'])
                    data['id'] = nivelsatisfacionencuestacapacitacionescrai.encuesta_id
                    return render(request, "adm_configuracion_mundocrai/deletenivel.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletecapacitacion':
                try:
                    data['title'] = u'Eliminar Capacitación Mundo-Crai'
                    data['capacitacionescrai'] = CapacitacionesCrai.objects.get(pk=request.GET['id'])
                    return render(request, "adm_configuracion_mundocrai/deletecapacitacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletesala':
                try:
                    data['title'] = u'Eliminar Sala Mundo-Crai'
                    data['salacrai'] = SalaCrai.objects.get(pk=request.GET['id'])
                    return render(request, "adm_configuracion_mundocrai/deletesala.html", data)
                except Exception as ex:
                    pass

            elif action == 'salas':
                try:
                    data['title'] = u'Salas Mundo-Crai'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            salacrai = SalaCrai.objects.filter(nombre__icontains=search, status=True).order_by('id')
                        else:
                            salacrai = SalaCrai.objects.filter((Q(nombre__icontains=ss[0]) | Q(nombre__icontains=ss[1])), status=True).order_by('id')
                    else:
                        salacrai = SalaCrai.objects.filter(status=True).order_by('id')
                    paging = MiPaginador(salacrai, 15)
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
                    data['salacrais'] = page.object_list
                    return render(request, "adm_configuracion_mundocrai/salas.html", data)
                except Exception as ex:
                    pass

            elif action == 'seccionclubes':
                try:
                    data['title'] = u'Secciones Clubes Mundo-Crai'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            seccionclubes = SeccionClub.objects.filter(nombre__icontains=search, status=True).order_by('id')
                        else:
                            seccionclubes = SeccionClub.objects.filter((Q(nombre__icontains=ss[0]) | Q(nombre__icontains=ss[1])), status=True).order_by('id')
                    else:
                        seccionclubes = SeccionClub.objects.filter(status=True).order_by('id')
                    paging = MiPaginador(seccionclubes, 15)
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
                    data['seccionclubes'] = page.object_list
                    return render(request, "adm_configuracion_mundocrai/seccionclubes.html", data)
                except Exception as ex:
                    pass

            elif action == 'reservacubiculo':
                try:
                    data['title'] = u'Reserva Cubículos Crai'
                    salas = SalaCrai.objects.filter(status=True, tipo=5).order_by('id')
                    data['salacrais'] = salas
                    return render(request, "adm_configuracion_mundocrai/reservacubiculo.html", data)
                except Exception as ex:
                    pass

            if action == 'verdetalle':
                try:
                    data = {}
                    cubiculo = SalaCrai.objects.get(pk=int(request.GET['id']))
                    reservas = ReservasCubiculosCrai.objects.filter(cubiculo=cubiculo, terminar=True).order_by('fechadesde')
                    data['cubiculo'] = cubiculo
                    data['reservas'] = reservas
                    template = get_template("adm_configuracion_mundocrai/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'capacitacion':
                try:
                    data['title'] = u'Capacitaciones Mundo-Crai'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            capacitacionescrai = CapacitacionesCrai.objects.filter(tema__icontains=search, status=True).order_by('-id') # , tipomundocrai=tipo_mundo
                        else:
                            capacitacionescrai = CapacitacionesCrai.objects.filter((Q(tema__icontains=ss[0]) | Q(tema__icontains=ss[1])), status=True).order_by('-id') #, tipomundocrai=tipo_mundo
                    else:
                        capacitacionescrai = CapacitacionesCrai.objects.filter(status=True).order_by('-id') #, tipomundocrai=tipo_mundo
                    data['tc'] = tc = int(request.GET['tc']) if 'tc' in request.GET and request.GET['tc'] else 0
                    data['cc'] = cc = int(request.GET['cc']) if 'cc' in request.GET and request.GET['cc'] else 0
                    if cc!=0:
                        capacitacionescrai = capacitacionescrai.filter(tipomundocrai=cc)
                    if tc != 0:
                        capacitacionescrai = capacitacionescrai.filter(tipo=tc)
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['capacitacionescrais'] = capacitacionescrai
                    data['firmascapacitacionescrais'] = FirmasCapacitacionesCrai.objects.filter(status=True).order_by('-tipofirma')
                    data['solicitudotrascapacitacionescrais'] = SolicitudOtrasCapacitacionesCrai.objects.filter(status=True)
                    data['encuestacapacitacionescrais'] = EncuestaCapacitacionesCrai.objects.filter(status=True).order_by('-id')
                    return render(request, "adm_configuracion_mundocrai/capacitacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'estadistica':
                try:
                    data['title'] = u'Estadistica Ingreso opciones CRAI'
                    return render(request, "adm_configuracion_mundocrai/estadistica.html", data)
                except Exception as ex:
                    pass

            elif action == 'reservasala':
                try:
                    data['title'] = u'Reservas Sala Crai'
                    fecha = datetime.now().date()
                    hoy = datetime.now().date()
                    pdia = fecha.day
                    panio = fecha.year
                    pmes = fecha.month
                    if 'mover' in request.GET:
                        mover = request.GET['mover']

                        if mover == 'anterior':
                            mes = int(request.GET['mes'])
                            anio = int(request.GET['anio'])
                            pmes = mes - 1
                            if pmes == 0:
                                pmes = 12
                                panio = anio - 1
                            else:
                                panio = anio

                        elif mover == 'proximo':
                            mes = int(request.GET['mes'])
                            anio = int(request.GET['anio'])
                            pmes = mes + 1
                            if pmes == 13:
                                pmes = 1
                                panio = anio + 1
                            else:
                                panio = anio

                    s_anio = panio
                    s_mes = pmes
                    s_dia = 1
                    data['mes'] = MESES_CHOICES[s_mes - 1]
                    data['ws'] = [0, 7, 14, 21, 28, 35]
                    lista = {}
                    listaactividades = {}
                    for i in range(1, 43, 1):
                        dia = {i: 'no'}
                        actividaddia = {i: None}
                        lista.update(dia)
                        listaactividades.update(actividaddia)
                    comienzo = False
                    fin = False
                    for i in lista.items():
                        try:
                            fecha = date(s_anio, s_mes, s_dia)
                            if fecha.isoweekday() == i[0] and fin is False and comienzo is False:
                                comienzo = True
                        except Exception as ex:
                            pass
                        if comienzo:
                            try:
                                fecha = date(s_anio, s_mes, s_dia)
                            except Exception as ex:
                                fin = True
                        if comienzo and fin is False:
                            dia = {i[0]: s_dia}
                            s_dia += 1
                            lista.update(dia)
                            actividaddias = ReservasCrai.objects.filter(status=True, fecha=fecha)
                            diaact = []
                            if actividaddias.exists():
                                valor = ""
                                for actividaddia in actividaddias:
                                    # &#13;
                                    cadena = u"Hora: %s a %s, Motivo: %s; " % (
                                    str(actividaddia.horadesde), str(actividaddia.horahasta), str(actividaddia.descripcion))
                                    valor = valor + cadena
                            else:
                                valor = ""
                            act = [valor, (fecha < datetime.now().date() and valor == ""), 1,
                                   fecha.strftime('%d-%m-%Y')]
                            diaact.append(act)
                            listaactividades.update({i[0]: diaact})
                    data['dias_mes'] = lista
                    data['dwnm'] = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
                    data['dwn'] = [1, 2, 3, 4, 5, 6, 7]
                    data['daymonth'] = 1
                    data['s_anio'] = s_anio
                    data['s_mes'] = s_mes
                    data['lista'] = lista
                    data['listaactividades'] = listaactividades
                    data['archivo'] = None

                    persona = request.session['persona']
                    data['check_session'] = False
                    data['fechainicio'] = date(datetime.now().year, 1, 1)
                    data['fechafin'] = datetime.now().date()
                    data['form3'] = ReservasCraiSolicitarAutoridadForm()
                    data['hoy'] = hoy
                    return render(request, "adm_configuracion_mundocrai/reservas.html", data)
                except:
                    pass

            elif action == 'noticias':
                try:
                    data['title'] = u'Noticias Mundo-Crai'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            noticias = NoticiasMundoCrai.objects.filter((Q(titulo__icontains=search) |
                                                               Q(descripcion__icontains=search)), status=True).order_by('id')
                        else:
                            noticias = NoticiasMundoCrai.objects.filter((Q(titulo__icontains=ss[0]) & Q(descripcion__icontains=ss[1]) |
                                                               Q(titulo__icontains=ss[1]) & Q(descripcion__icontains=ss[0])), status=True).order_by('id')
                    else:
                        noticias = NoticiasMundoCrai.objects.filter(status=True).order_by('id')
                    paging = MiPaginador(noticias, 15)
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
                    data['noticias'] = page.object_list
                    return render(request, "adm_configuracion_mundocrai/noticias.html", data)
                except Exception as ex:
                    pass

            elif action == 'organigrama':
                try:
                    data['title'] = u'Organigrama Crai'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            organigramas = Organigrama.objects.filter((Q(persona__nombres__icontains=search) |
                                                                       Q(persona__apellido1__icontains=search)), status=True).order_by('id')
                        else:
                            organigramas = Organigrama.objects.filter((Q(persona__nombres__icontains=ss[0]) & Q(persona__apellido1__icontains=ss[1]) |
                                                               Q(persona__nombres__icontains=ss[1]) & Q(persona__apellido1__icontains=ss[0])), status=True).order_by('id')
                    else:
                        organigramas = Organigrama.objects.filter(status=True).order_by('id')
                    paging = MiPaginador(organigramas, 15)
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
                    data['organigramas'] = page.object_list
                    return render(request, "adm_configuracion_mundocrai/organigrama.html", data)
                except Exception as ex:
                    pass

            if action == 'verinscritoscapacitacioncrai':
                try:
                    capacitacion = CapacitacionesCrai.objects.get(pk=int(request.GET['id']))
                    data['title'] = u'Inscritos en Capacitaciones CRAI - %s' % capacitacion.tema
                    filtro, estado, search = Q(status=True, capacitacionescrai__id=capacitacion.id),\
                                             request.GET.get('estado',''), \
                                             request.GET.get('s','')
                    if estado:
                        data['estado'] = estado =int(estado)
                        if estado == 1:
                            filtro= filtro & Q(aprobado=True)
                        else:
                            filtro = filtro & Q(aprobado=False)
                    if search:
                        data['s'] = search
                        filtro = filtro & ((Q(inscripcion__persona__nombres__icontains=search) |
                                           Q(inscripcion__persona__apellido1__icontains=search) |
                                           Q(inscripcion__persona__apellido2__icontains=search)) |
                                           (Q(profesor__persona__nombres__icontains=search) |
                                            Q(profesor__persona__apellido1__icontains=search) |
                                            Q(profesor__persona__apellido2__icontains=search)))

                    solicitudes = InscripcionCapacitacionesCrai.objects.filter(filtro).order_by("profesor__persona__nombres","inscripcion__persona__nombres")
                    # paging = MiPaginador(solicitudes, 25)
                    # p = 1
                    # try:
                    #     paginasesion = 1
                    #     if 'paginador' in request.session:
                    #         paginasesion = int(request.session['paginador'])
                    #     if 'page' in request.GET:
                    #         p = int(request.GET['page'])
                    #     else:
                    #         p = paginasesion
                    #     try:
                    #         page = paging.page(p)
                    #     except:
                    #         p = 1
                    #     page = paging.page(p)
                    # except:
                    #     page = paging.page(p)
                    # request.session['paginador'] = p
                    # data['paging'] = paging
                    # data['rangospaging'] = paging.rangos_paginado(p)
                    # data['page'] = page
                    data['solicitudes'] = solicitudes
                    data['id'] = capacitacion.id
                    return render(request, "adm_configuracion_mundocrai/verinscritoscapacitacioncrai.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/adm_configuracion_mundocrai?info=%s" % ex.__str__())

            if action == 'notificarinscritoscapacitacioncrai':
                try:
                    capacitacion = CapacitacionesCrai.objects.get(pk=int(request.GET['id']))
                    solicitudes = InscripcionCapacitacionesCrai.objects.filter(status=True,capacitacionescrai__id=request.GET['id']).order_by("profesor__persona__nombres", "inscripcion__persona__nombres")
                    asunto = u"CAPACITACIÓN CRAI"
                    for solicitud in solicitudes:
                        if(solicitud.profesor):
                            correo = solicitud.profesor.persona.lista_emails_envio()
                            datos = {'sistema': request.session['nombresistema'], 'solicitud': solicitud, 'capacitacion': capacitacion}
                            send_html_mail(asunto, "emails/notificacion_capacitacion.html", datos,
                                           correo, [], [],
                                           cuenta=CUENTAS_CORREOS[0][1])
                        else:
                            correo = solicitud.inscripcion.persona.lista_emails_envio()
                            datos = {'sistema': request.session['nombresistema']}
                            send_html_mail(asunto, "emails/notificacion_capacitacion.html", datos,
                                           correo, [], [],
                                           cuenta=CUENTAS_CORREOS[0][1])
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'reportecapacitaciones':


                try:
                    capacitacion = CapacitacionesCrai.objects.get(pk=int(request.GET['id']))
                    data['title'] = u'Inscritos en Capacitaciones CRAI - %s' % capacitacion.tema
                    search = None
                    tipo = None
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        solicitudes = InscripcionCapacitacionesCrai.objects.select_related().filter((Q(inscripcion__persona__nombres__icontains=search) |
                                                                                   Q(inscripcion__persona__apellido1__icontains=search) |
                                                                                   Q(inscripcion__persona__apellido2__icontains=search)) |
                                                                                   (Q(profesor__persona__nombres__icontains=search) |
                                                                                    Q(profesor__persona__apellido1__icontains=search) |
                                                                                    Q(profesor__persona__apellido2__icontains=search)), status=True, capacitacionescrai__id=request.GET['id']).order_by("profesor__persona__apellido1","inscripcion__persona__apellido1")
                    else:
                        solicitudes = InscripcionCapacitacionesCrai.objects.select_related().filter(status=True, capacitacionescrai__id=request.GET['id']).order_by("profesor__persona__apellido1","inscripcion__persona__apellido1")



                    borders = Borders()
                    borders.left = 1
                    borders.right = 1
                    borders.top = 1
                    borders.bottom = 1
                    __author__ = 'Unemi'
                    title = easyxf('font: name Arial, bold on , height 240; alignment: horiz centre')
                    normal = easyxf('font: name Arial , height 150; alignment: horiz left')
                    encabesado_tabla = easyxf('font: name Arial , bold on , height 150; alignment: horiz left')
                    normalc = easyxf('font: name Arial , height 150; alignment: horiz center')
                    subtema = easyxf('font: name Arial, bold on , height 180; alignment: horiz left')
                    normalsub = easyxf('font: name Arial , height 180; alignment: horiz left')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    normal.borders = borders
                    normalc.borders = borders
                    normalsub.borders = borders
                    subtema.borders = borders
                    encabesado_tabla.borders = borders
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')

                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Inscritos_Capacitaciones_CRAI' + random.randint(
                        1, 10000).__str__() + '.xls'


                    ws.col(0).width = 10000
                    ws.col(1).width = 8000
                    ws.col(2).width = 8000
                    ws.col(3).width = 8000

                    row_num = 0
                    ws.write(row_num, 0, 'PARTICIPANTES', encabesado_tabla)
                    ws.write(row_num, 1, 'CORREO PERSONAL', encabesado_tabla)
                    ws.write(row_num, 2, 'CORREO INSTITUCIONAL', encabesado_tabla)
                    ws.write(row_num, 3, 'NUMEROS DE CONTACTO', encabesado_tabla)
                    ws.write(row_num, 4, 'ESTADO', encabesado_tabla)
                    i = 0
                    row_num = 1
                    campo1 = ''

                    for soli in solicitudes:
                        i += 1
                        if soli.profesor:
                          campo1 = str(soli.profesor)
                          campo2 = str(soli.profesor.persona.email)
                          campo3 = str(soli.profesor.persona.emailinst)
                          campo4 = ' - '.join(soli.profesor.persona.lista_telefonos())
                          campo5 = "Aprobado" if soli.aprobado else "Reprobado"
                        else:
                          campo1 = str(soli.inscripcion)
                          campo2 = str(soli.inscripcion.persona.email)
                          campo3 = str(soli.inscripcion.persona.emailinst)
                          campo4 = ' - '.join(soli.inscripcion.persona.lista_telefonos())
                          campo5 = "Aprobado" if soli.aprobado else "Reprobado"
                        ws.write(row_num, 0, campo1, normal)
                        ws.write(row_num, 1, campo2, normal)
                        ws.write(row_num, 2, campo3, normal)
                        ws.write(row_num, 3, campo4, normal)
                        ws.write(row_num, 4, campo5, normal)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass


            if action == 'reportetotal':
                try:
                    fechadesde = convertir_fecha(request.GET['fecha_desde'])
                    fechahasta = convertir_fecha(request.GET['fecha_hasta'])
                    cood = request.GET['id']
                    tipo = request.GET['tip']

                    filtrofechas = Q(fecha__range=(fechadesde, fechahasta))

                    solicitudes = InscripcionCapacitacionesCrai.objects.filter(filtrofechas, status=True, capacitacionescrai__tipomundocrai= cood,capacitacionescrai__tipo = tipo ).order_by("profesor__persona__apellido1", "profesor__persona__apellido2","profesor__persona__nombres","inscripcion__persona__apellido1","inscripcion__persona__apellido2","inscripcion__persona__nombres").distinct("profesor__persona__apellido1", "profesor__persona__apellido2","profesor__persona__nombres","inscripcion__persona__apellido1","inscripcion__persona__apellido2","inscripcion__persona__nombres")

                    borders = Borders()
                    borders.left = 1
                    borders.right = 1
                    borders.top = 1
                    borders.bottom = 1
                    __author__ = 'Unemi'
                    title = easyxf('font: name Arial, bold on , height 240; alignment: horiz centre')
                    normal = easyxf('font: name Arial , height 150; alignment: horiz left')
                    encabesado_tabla = easyxf('font: name Arial , bold on , height 150; alignment: horiz left')
                    normalc = easyxf('font: name Arial , height 150; alignment: horiz center')
                    subtema = easyxf('font: name Arial, bold on , height 180; alignment: horiz left')
                    normalsub = easyxf('font: name Arial , height 180; alignment: horiz left')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    normal.borders = borders
                    normalc.borders = borders
                    normalsub.borders = borders
                    subtema.borders = borders
                    encabesado_tabla.borders = borders
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')

                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Inscritos_capacitaciones' + random.randint(
                        1, 10000).__str__() + '.xls'


                    ws.col(0).width = 10000

                    row_num = 0
                    ws.write(row_num, 0, 'PARTICIPANTES', encabesado_tabla)
                    i = 0
                    row_num = 1
                    campo1 = ''

                    for soli in solicitudes:
                        i += 1
                        if soli.profesor:
                          campo1 = str(soli.profesor)
                        else:
                          campo1 = str(soli.inscripcion)
                        ws.write(row_num, 0, campo1, normal)

                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'preguntas':
                try:
                    data['title'] = u'Preguntas Encuesta Mundo-CRAI'
                    search = None
                    tipo = None
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        preguntasencuestacapacitacionescrais = PreguntasEncuestaCapacitacionesCrai.objects.filter(descripcion__icontains=search, status=True, encuesta__id=request.GET['id']).order_by('id')
                    else:
                        preguntasencuestacapacitacionescrais = PreguntasEncuestaCapacitacionesCrai.objects.filter(status=True, encuesta__id=request.GET['id']).order_by('id')
                    data['search'] = search if search else ""
                    data['preguntasencuestacapacitacionescrais'] = preguntasencuestacapacitacionescrais
                    data['id'] = request.GET['id']
                    return render(request, "adm_configuracion_mundocrai/preguntas.html", data)
                except Exception as ex:
                    pass

            if action == 'niveles':
                try:
                    data['title'] = u'Niveles Encuesta Mundo-CRAI'
                    search = None
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        nivelsatisfacionencuestacapacitacionescrais = NivelSatisfacionEncuestaCapacitacionesCrai.objects.filter(nivel__icontains=search, status=True, encuesta__id=request.GET['id']).order_by('orden')
                    else:
                        nivelsatisfacionencuestacapacitacionescrais = NivelSatisfacionEncuestaCapacitacionesCrai.objects.filter(status=True, encuesta__id=request.GET['id']).order_by('orden')
                    data['search'] = search if search else ""
                    data['nivelsatisfacionencuestacapacitacionescrais'] = nivelsatisfacionencuestacapacitacionescrais
                    data['id'] = request.GET['id']
                    return render(request, "adm_configuracion_mundocrai/niveles.html", data)
                except Exception as ex:
                    pass

            if action == 'aprobarsala':
                try:
                    data['title'] = u'Aprobar Reserva Sala - CRAI'
                    data['reservascrai'] = ReservasCrai.objects.get(pk=request.GET['id'])
                    return render(request, "adm_configuracion_mundocrai/aprobarsala.html", data)
                except Exception as ex:
                    pass

            if action == 'rechazarsala':
                try:
                    data['title'] = u'Rechazar Reserva Sala - CRAI'
                    data['reservascrai'] = ReservasCrai.objects.get(pk=request.GET['id'])
                    return render(request, "adm_configuracion_mundocrai/rechazarsala.html", data)
                except Exception as ex:
                    pass

            if action == 'aprobarinscripcion':
                try:
                    data['title'] = u'Aprobar Incripción'
                    data['inscripcion'] = InscripcionCapacitacionesCrai.objects.get(pk=request.GET['id'])
                    return render(request, "adm_configuracion_mundocrai/aprobarinscripcion.html", data)
                except Exception as ex:
                    pass

            if action == 'generarcertificado':
                try:
                    data['title'] = u'Generar Certificado'
                    data['inscripcion'] = InscripcionCapacitacionesCrai.objects.get(pk=request.GET['id'])
                    return render(request, "adm_configuracion_mundocrai/generarcertificado.html", data)
                except Exception as ex:
                    pass

            if action == 'generarcertificadoclub':
                try:
                    data['title'] = u'Generar Certificado Club'
                    data['inscripcion'] = InscripcionClub.objects.get(inscripcion_id=request.GET['idinscripcion'])
                    return render(request, "adm_configuracion_mundocrai/generarcertificadoclub.html", data)
                except Exception as ex:
                    pass

            if action == 'descargardocente':
                try:
                    fecha = convertir_fecha(request.GET['fecha'])
                    fecha_hasta = convertir_fecha(request.GET['fecha_hasta'])
                    cursor = connection.cursor()
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=marcadas.xls'
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('Sheetname')
                    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    ws.write_merge(0, 0, 0, 3, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
                    ws.write_merge(1, 1, 0, 3, 'LISTADO DE DOCENTE ACCESO A SISTEMA CRAI', estilo)
                    ws.col(0).width = 10000
                    ws.write(4, 0, 'DOCENTE')
                    ws.write(4, 1, 'FACULTAD')
                    a = 4
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'

                    sql = ""

                    sql = "select (per1.apellido1||' '||per1.apellido2||' '||per1.nombres) as docente, pro.id " \
                          " from sga_persona per1, sga_profesor pro " \
                          " where pro.persona_id=per1.id and per1.id in (select tabla.idpersona  from (SELECT per.id as idpersona " \
                          " FROM sga_contadoractividadesmundocrai ca, sga_actividadesmundocrai am, auth_user u, " \
                          " sga_persona per WHERE ca.status= TRUE AND ca.actividadesmundocraiprincipal_id=am.id AND ca.tipoingreso=1 and " \
                          " am.status= TRUE AND am.tipomundocrai="+ request.GET['idt']  +" AND ca.usuario_creacion_id=u.id " \
                          " AND per.usuario_id=u.id AND per.status=TRUE AND ca.fecha BETWEEN '"+ str(fecha) +"' and '"+ str(fecha_hasta) +"') as tabla ) order by per1.apellido1, per1.apellido2"
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    for per in results:
                        a += 1
                        coordinacion = Profesor.objects.get(pk=int(per[1])).coordinacion.nombre
                        ws.write(a, 0, per[0])
                        ws.write(a, 1, coordinacion)
                    # ws.write(a+2, 0, 'Fecha:')
                    # ws.write(a+2, 1, datetime.today(),date_format)
                    ws.write_merge(a + 2, a + 2, 0, 1, datetime.today(), date_format)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'descargardocente2':
                try:
                    fecha = convertir_fecha(request.GET['fecha'])
                    fecha_hasta = convertir_fecha(request.GET['fecha_hasta'])
                    idt = request.GET['idt']
                    cursor = connection.cursor()
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=marcadas.xls'
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('Sheetname')
                    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    ws.write_merge(0, 0, 0, 3, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
                    ws.write_merge(1, 1, 0, 3, 'LISTADO DE DOCENTE ACCESO A SISTEMA CRAI', estilo)
                    ws.col(0).width = 10000
                    ws.write(4, 0, 'DOCENTE')
                    ws.write(4, 1, 'FACULTAD')
                    a = 4
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'

                    sql = ""

                    sql = "select (per1.apellido1||' '||per1.apellido2||' '||per1.nombres) as docente, pro.id " \
                          " from sga_persona per1, sga_profesor pro " \
                          " where pro.persona_id=per1.id and per1.id in (select tabla.idpersona  from (SELECT per.id as idpersona " \
                          " FROM sga_contadoractividadesmundocrai ca, sga_actividadesmundocrai am, auth_user u, " \
                          " sga_persona per WHERE ca.status= TRUE AND ca.actividadesmundocraiprincipal_id=am.id AND ca.tipoingreso=1 and " \
                          " am.status= TRUE AND am.tipomundocrai="+ request.GET['idt']  +" AND ca.usuario_creacion_id=u.id " \
                          " AND per.usuario_id=u.id AND per.status=TRUE AND ca.fecha BETWEEN '"+ str(fecha) +"' and '"+ fecha_hasta.strftime('%Y-%m-%d') +"') as tabla ) order by per1.apellido1, per1.apellido2"
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    for per in results:
                        a += 1
                        coordinacion = Profesor.objects.get(pk=int(per[1])).coordinacion.nombre
                        ws.write(a, 0, per[0])
                        ws.write(a, 1, coordinacion)
                    # ws.write(a+2, 0, 'Fecha:')
                    # ws.write(a+2, 1, datetime.today(),date_format)
                    ws.write_merge(a + 2, a + 2, 0, 1, datetime.today(), date_format)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'addseccion':
                try:
                    data['title'] = u'Adicionar Sección Club'
                    form = SeccionClubesForm()
                    data['form'] = form
                    return render(request, "adm_configuracion_mundocrai/addseccion.html", data)
                except Exception as ex:
                    pass

            if action == 'editseccion':
                try:
                    data['title'] = u'Editar Sección Club'
                    data['seccionclub'] = seccionclub = SeccionClub.objects.get(pk=request.GET['id'])
                    form = SeccionClubesForm(initial={'nombre': seccionclub.nombre})
                    data['form'] = form
                    return render(request, "adm_configuracion_mundocrai/editseccion.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteseccion':
                try:
                    data['title'] = u'Eliminar Sección'
                    data['seccionclub'] = SeccionClub.objects.get(pk=request.GET['idseccion'])
                    return render(request, "adm_configuracion_mundocrai/deleteseccion.html", data)
                except Exception as ex:
                    pass

            if action == 'listaclubes':
                try:
                    data['title'] = u'Clubes'
                    search = None
                    ids = None
                    data['seccionclub'] = seccionclub = SeccionClub.objects.get(pk=request.GET['idseccion'])
                    clubes = Club.objects.filter(seccionclub=seccionclub, status=True).order_by('id')
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            clubes = clubes.filter(Q(nombre__icontains=search))
                        else:
                            clubes = clubes.filter((Q(nombre__icontains=ss[0]) | Q(nombre__icontains=ss[1])))
                    paging = MiPaginador(clubes, 20)
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
                    data['clubes'] = page.object_list
                    return render(request, "adm_configuracion_mundocrai/listaclubes.html", data)
                except Exception as ex:
                    pass

            elif action == 'addclub':
                try:
                    data['title'] = u'Adicionar Club'
                    data['seccionclub'] = SeccionClub.objects.get(pk=request.GET['idseccion'])
                    form = ClubesForm()
                    data['form'] = form
                    return render(request, "adm_configuracion_mundocrai/addclub.html", data)
                except Exception as ex:
                    pass

            elif action == 'editclub':
                try:
                    data['title'] = u'Editar Actividad'
                    data['club'] = club = Club.objects.get(pk=request.GET['id'])
                    form = ClubesForm(initial={'nombre': club.nombre,
                                               'coordinacion': club.coordinacion,
                                               'descripcion': club.descripcion,
                                               'fechainicio': club.fechainicio,
                                               'fechafin': club.fechafin,
                                               'fechainicioinscripcion': club.fechainicioinscripcion,
                                               'fechafininscripcion': club.fechafininscripcion,
                                               'cupo': club.cupo,
                                               'carrera': club.carrera
                                               })
                    form.editar(club.coordinacion, club.tutorprincipal)
                    data['form'] = form
                    return render(request, "adm_configuracion_mundocrai/editclub.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteclub':
                try:
                    data['title'] = u'Eliminar Club'
                    data['club'] = Club.objects.get(pk=request.GET['idclub'])
                    return render(request, "adm_configuracion_mundocrai/deleteclub.html", data)
                except Exception as ex:
                    pass

            elif action == 'listainscritos':
                try:
                    data['title'] = u'Listado de Inscritos'
                    search = None
                    ids = None
                    data['club'] = club = Club.objects.get(pk=request.GET['idclub'], status=True)
                    if 's' in request.GET:
                        search = request.GET['s']
                        if ' ' in search:
                            s = search.split(" ")
                            listadoinscritos = InscripcionClub.objects.filter(((Q(inscripcion__persona__apellido1__contains=s[0]) &
                                                                                Q(inscripcion__persona__apellido2__contains=s[1]))),
                                                                                club=club,status=True).order_by('inscripcion__persona__apellido1','inscripcion__persona__apellido2')
                        else:
                            listadoinscritos = InscripcionClub.objects.filter(
                                (Q(inscripcion__persona__nombres__contains=search) |
                                 Q(inscripcion__persona__apellido1__contains=search) |
                                 Q(inscripcion__persona__apellido2__contains=search)),
                                club=club, status=True).order_by('inscripcion__persona__apellido1','inscripcion__persona__apellido2')
                    else:
                        listadoinscritos = InscripcionClub.objects.filter(club=club, status=True).order_by('inscripcion__persona__apellido1','inscripcion__persona__apellido2')
                    paging = MiPaginador(listadoinscritos, 25)
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
                    data['listadoinscritos'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_configuracion_mundocrai/listadoinscritos.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteparticipante':
                try:
                    data['title'] = u'Eliminar Participante al Club'
                    data['inscrito'] = InscripcionClub.objects.get(pk=request.GET['idlista'])
                    return render(request, "adm_configuracion_mundocrai/deleteparticipante.html", data)
                except Exception as ex:
                    pass



            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            tipomundocrai = int(request.GET['tipomundocrai']) if 'tipomundocrai' in request.GET and request.GET['tipomundocrai'] else 0
            actividadesmundocrais = ActividadesMundoCrai.objects.filter(status=True).order_by('tipomundocrai', 'orden', 'descripcion')
            if tipomundocrai != 0:
                actividadesmundocrais = actividadesmundocrais.filter(tipomundocrai=tipomundocrai).order_by('tipomundocrai', 'orden', 'descripcion')

            if 's' in request.GET:
                search = request.GET['s']
                actividadesmundocrais = actividadesmundocrais.filter((Q(descripcion__icontains=search)), status=True).order_by('tipomundocrai', 'orden', 'descripcion')

            elif 'id' in request.GET:
                ids = request.GET['id']
                actividadesmundocrais = actividadesmundocrais.filter(id=ids).order_by('tipomundocrai', 'orden', 'descripcion')

            paging = MiPaginador(actividadesmundocrais, 25)
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
            data['tipomundocrai'] = tipomundocrai
            data['rangospaging'] = paging.rangos_paginado(p)
            data['page'] = page
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['actividadesmundocrais'] = page.object_list
            return render(request, "adm_configuracion_mundocrai/view.html", data)
