# -*- coding: UTF-8 -*-
import os
from django.contrib.auth.decorators import login_required
from django.db import transaction
# from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from decorators import secure_module
from sga.commonviews import adduserdata
from sga.funciones import generar_nombre, MiPaginador, log, variable_valor, convertir_fecha_hora, convertir_fecha, convertir_hora, \
    convertir_fecha_hora_invertida, notificacion, remover_caracteres_especiales_unicode
from inno.models import HorarioTutoriaAcademica, SolicitudTutoriaIndividual, SolicitudTutoriaIndividualTema, \
    ESTADO_SOLICITUD_TUTORIA, RegistroClaseTutoriaDocente, DetalleSolicitudHorarioTutoria
from sga.models import SolicitudRecursosComunicacionInstitucional, RecursosComunicacionInstitucional, DetalleAprobacionSolicitud, \
    CUENTAS_CORREOS, MultimediaRecursosComunicacionInstitucional, MultimediaSolicitudRecursosComunicacionInstitucional, TIPO_PRODUCTOCOMUNICACIONAL, \
    ESTADO_SOLICITUDRECURSO, RecorridoRegistroSolicitud
from sga.forms import SolicitudRecursosComunicacionInstitucionalForm, ProductoComunicacionInstitucional, MultimediaProductoComunicacionalForm, \
    ReportePorProductoComunicacionalForm, ActualizarProductoComunicacional
from inno.forms import TutoriaManualForm, ProgramarTutoriasForm, ConvocarTutoriaManualForm
from django.db.models import Q, Sum
from datetime import datetime, timedelta, date
from django.template.loader import get_template
from settings import SITE_STORAGE
from sga.templatetags.sga_extras import encrypt
import json
from django.template import Context
from sga.tasks import send_html_mail, conectar_cuenta
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from django.db.models.aggregates import Count
from django.db.models import Max
from django.db import models, connection, connections
import io
import xlsxwriter
from typing import Any, Hashable, Iterable, Optional


def buscar_dicc(it: Iterable[dict], clave: Hashable, valor: Any) -> Optional[dict]:
    for dicc in it:
        if dicc[clave] == valor:
            return dicc
    return None


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + datetime.timedelta(days=n)


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['periodo'] = periodo = request.session['periodo']
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addsolicitudrecurso':
            try:
                f = SolicitudRecursosComunicacionInstitucionalForm(request.POST, request.FILES)
                if 'tipo' in request.POST:
                    tipo = int(request.POST['tipo'])
                    if tipo == 1:
                        solicitud = SolicitudRecursosComunicacionInstitucional(solicitante=persona,
                                                                               descripcion=request.POST['descripcion'],
                                                                               objetivo=request.POST['objetivo'],
                                                                               fechasolicitud=datetime.now().date())
                    else:
                        if 'archivorecurso' in request.FILES:
                            arch = request.FILES['archivorecurso']
                            extension = arch._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if arch.size > 4194304:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                            if not exte.lower() == 'pdf' and not exte.lower() == 'png':
                                return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf o .png"})
                            newfile = request.FILES['archivorecurso']
                            newfile._name = generar_nombre("recurso", newfile._name)
                        solicitud = SolicitudRecursosComunicacionInstitucional(solicitante=persona,
                                                                               nombre=request.POST['nombre'],
                                                                               descripcion=request.POST['descripcion'],
                                                                               objetivo=request.POST['objetivo'],
                                                                               archivo=newfile,
                                                                               tipo=2,
                                                                               fechasolicitud=datetime.now().date())
                    solicitud.save(request)
                    log(u'Generó una solicitud: %s' % solicitud, request, "add")
                    return JsonResponse({'result': 'ok'})
            except Exception as ex:
                pass



        elif action == 'aceptarsolicitud':
            try:
                f = SolicitudRecursosComunicacionInstitucionalForm(request.POST, request.FILES)
                manualfile = None
                anadirrecurso = None
                correonotificacion = []
                if f.is_valid():
                    solicitud = SolicitudRecursosComunicacionInstitucional.objects.get(status=True, pk=int(request.POST['idsolicitud']))
                    correonotificacion.append(solicitud.solicitante.emailinst)
                    if 'manual' in request.FILES:
                        arch = request.FILES['manual']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 4194304:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Error, el tamaño del manual es mayor a 4 Mb."})
                        if not exte.lower() == 'pdf':
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"El manual tiene que ser archivo pdf"})
                        manualfile = request.FILES['manual']
                        manualfile._name = generar_nombre("manual", manualfile._name)
                        directory = os.path.join(SITE_STORAGE, 'media', 'manual')
                        try:
                            os.stat(directory)
                        except:
                            os.mkdir(directory)
                    if solicitud.tipo == 1:
                        if 'archivorecurso' in request.FILES:
                            arch = request.FILES['archivorecurso']
                            extension = arch._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if arch.size > 4194304:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                            if not exte.lower() == 'pdf' and not exte.lower() == 'png':
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Solo se permiten archivos .pdf o .png"})
                            newfile = request.FILES['archivorecurso']
                            newfile._name = generar_nombre("recurso", newfile._name)
                            recurso = RecursosComunicacionInstitucional(solicitud_id=solicitud.id,
                                                                        nombre=f.cleaned_data['nombre'],
                                                                        descripcion=f.cleaned_data['descripcion'],
                                                                        objetivo=f.cleaned_data['objetivo'],
                                                                        archivo=newfile, manual=manualfile)
                    else:
                        if solicitud.tienemultimedia == 1:
                            recurso = RecursosComunicacionInstitucional(solicitud_id=solicitud.id,
                                                                        nombre=f.cleaned_data['nombre'],
                                                                        descripcion=f.cleaned_data['descripcion'],
                                                                        objetivo=f.cleaned_data['objetivo'],
                                                                        tienemultimedia=1, manual=manualfile)
                            recurso.save(request)
                            multimediasolicitud = MultimediaSolicitudRecursosComunicacionInstitucional.objects.filter(
                                status=True,
                                solicitud_id=solicitud.id)
                            for multimediasoli in multimediasolicitud:
                                multimediarecurso = MultimediaRecursosComunicacionInstitucional(recurso_id=recurso.id,
                                                                                                nombre=multimediasoli.nombre,
                                                                                                archivo=multimediasoli.archivo)
                                multimediarecurso.save(request)
                        else:
                            recurso = RecursosComunicacionInstitucional(solicitud_id=solicitud.id,
                                                                        nombre=f.cleaned_data['nombre'],
                                                                        descripcion=f.cleaned_data['descripcion'],
                                                                        objetivo=f.cleaned_data['objetivo'],
                                                                        archivo=solicitud.archivo, manual=manualfile)
                    detalle = DetalleAprobacionSolicitud(solicitud_id=solicitud.id, fecha=datetime.now().date(),
                                                         estado=2)
                    asunto = u"SOLICITUD DE PRODUCTO INSTITUCIONAL APROBADA "
                    send_html_mail(asunto, "emails/notificarsolicitudaprobada.html",
                                   {'sistema': request.session['nombresistema'], 'solicitante': solicitud.solicitante,
                                    'descripcion': solicitud.descripcion, 'objetivo': solicitud.objetivo},
                                   ['jidrovoc@unemi.edu.ec'], [],
                                   cuenta=CUENTAS_CORREOS[1][1])
                    solicitud.estado = 2
                    recurso.save(request)
                    solicitud.save(request)
                    detalle.save(request)
                    recorridosolicitud = RecorridoRegistroSolicitud(solicitud=solicitud,
                                                                    fecha=datetime.now().date(),
                                                                    persona=persona,
                                                                    observacion='SOLICITUD ACEPTADA',
                                                                    estadosolicitud=3)
                    recorridosolicitud.save()
                    log(u'Adicionó un recurso: %s' % recurso, request, "add")
                    log(u'Aceptó solicitud: %s' % solicitud, request, "act")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
            except Exception as ex:
                pass

        elif action == 'cancelarsolicitudrecurso':
            try:
                if 'id' in request.POST:
                    solicitud = SolicitudRecursosComunicacionInstitucional.objects.get(status=True, pk=int(request.POST['id']))
                    solicitud.estado = 4
                    solicitud.save(request)
                    log(u'Cancela solicitud: %s' % solicitud, request, "act")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                pass


        elif action == 'rechazarsolicitudrecurso':
            try:
                if 'id' in request.POST:
                    solicitud = SolicitudRecursosComunicacionInstitucional.objects.get(status=True, pk=int(request.POST['id']))
                    solicitud.estado = 3
                    solicitud.save(request)
                    log(u'Rechaza solicitud: %s' % solicitud, request, "act")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                pass

        elif action == 'ocultarproducto':
            try:
                if 'id' in request.POST:
                    recurso = RecursosComunicacionInstitucional.objects.get(status=True, pk=int(request.POST['id']))
                    recurso.estado = 2
                    recurso.save(request)
                    log(u'Oculta recurso: %s' % recurso, request, "act")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                pass

        elif action == 'mostrarproducto':
            try:
                if 'id' in request.POST:
                    recurso = RecursosComunicacionInstitucional.objects.get(status=True, pk=int(request.POST['id']))
                    recurso.estado = 1
                    recurso.save(request)
                    log(u'Hace visible el recurso: %s' % recurso, request, "act")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                pass

        elif action == 'rechazarsolicitud':
            try:
                data['solicitud'] = solicitud = SolicitudRecursosComunicacionInstitucional.objects.get(status=True, pk=int(request.POST['id']))
                solicitud.estado = 3
                correonotificacion = []
                correonotificacion.append(solicitud.solicitante.emailinst)
                detalle = DetalleAprobacionSolicitud(solicitud_id=solicitud.id, fecha=datetime.now().date(), estado=3,
                                                     observacion=request.POST['observacion'])
                detalle.save(request)
                solicitud.save(request)
                asunto = u"SOLICITUD DE PRODUCTO INSTITUCIONAL RECHAZADA "
                send_html_mail(asunto, "emails/notificarsolicitudrechazada.html",
                               {'sistema': request.session['nombresistema'], 'solicitante': solicitud.solicitante,
                                'descripcion': solicitud.descripcion, 'objetivo': solicitud.objetivo, 'observacion': request.POST['observacion'],
                                'solicitud' : data},
                               correonotificacion, [],
                               cuenta=CUENTAS_CORREOS[1][1])
                recorridosolicitud = RecorridoRegistroSolicitud(solicitud=solicitud,
                                                                fecha=datetime.now().date(),
                                                                persona=persona,
                                                                observacion='SOLICITUD RECHAZADA',
                                                                estadosolicitud=4)
                recorridosolicitud.save()
                log(u'Rechazó una solicitud: %s' % solicitud, request, "act")
                return JsonResponse({'result': False})
            except Exception as ex:
                pass

        elif action == 'adicionarmanual':
            try:
                f = ProductoComunicacionInstitucional(request.POST, request.FILES)
                if f.is_valid():
                    if 'manual' in request.FILES:
                        arch = request.FILES['manual']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 4194304:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Error, el tamaño del manual es mayor a 4 Mb."})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"El manual tiene que ser archivo pdf"})
                        manualfile = request.FILES['manual']
                        manualfile._name = generar_nombre("manual", manualfile._name)
                    recurso = RecursosComunicacionInstitucional.objects.get(status=True, id=int(request.POST['id']))
                    recurso.manual = manualfile
                    recurso.save(request)
                    log(u'Adicionó manual a recurso: %s' % recurso, request, "act")
                    return JsonResponse({"result":False}, safe=False)
            except Exception as ex:
                pass

        elif action == 'adicionarproductoinstitucional':
            try:
                # request.FILES['manual']._name= remover_caracteres_especiales_unicode(request.FILES['manual']._name)
                # request.FILES['manual']._name= request.FILES['manual']._name.replace(" ", "")
                f = SolicitudRecursosComunicacionInstitucionalForm(request.POST, request.FILES)
                nombrecont = 0
                manualfile = None
                archivoproductoinst = None
                if f.is_valid():
                    if 'manual' in request.FILES:
                        arch = request.FILES['manual']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 4194304:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Error, el tamaño del manual es mayor a 4 Mb."})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"El manual tiene que ser archivo pdf"})
                        manualfile = request.FILES['manual']
                        manualfile._name = generar_nombre("manual", manualfile._name)
                    files = request.FILES.getlist('archivorecurso')
                    nombrearchivos = []
                    if len(files) > 1:
                        recurso = RecursosComunicacionInstitucional(nombre=f.cleaned_data['nombre'],
                                                                    descripcion=f.cleaned_data['descripcion'],
                                                                    objetivo=f.cleaned_data['objetivo'],
                                                                    tienemultimedia=1,
                                                                    manual=manualfile)
                        recurso.save(request)
                        for file in files:
                            nombrearchivos.append(file._name)
                            # if 'archivorecurso' in request.FILES:
                            request.FILES['archivorecurso'] = file
                            arch = file
                            extension = arch._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if arch.size > 50485760:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, el tamaño del manual es mayor a 4 Mb."})
                            if not exte.lower() == 'pdf' and not exte.lower() == 'png':
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"El manual tiene que ser archivo pdf o png"})
                            archivoproductoinst = request.FILES['archivorecurso']
                            archivoproductoinst._name = generar_nombre("producto", archivoproductoinst._name)
                            multimediarecurso = MultimediaRecursosComunicacionInstitucional(recurso_id=recurso.id,
                                                                                            nombre=nombrearchivos[nombrecont],
                                                                                            archivo=archivoproductoinst)
                            multimediarecurso.save(request)
                            nombrecont = nombrecont + 1
                    else:
                        if 'archivorecurso' in request.FILES:
                            arch = request.FILES['archivorecurso']
                            extension = arch._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if arch.size > 50485760:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, el tamaño del manual es mayor a 4 Mb."})
                            if not exte.lower() == 'pdf' and not exte.lower() == 'png':
                                return JsonResponse({"result": "bad", "mensaje": u"El manual tiene que ser archivo pdf o png"})
                            archivoproductoinst = request.FILES['archivorecurso']
                            archivoproductoinst._name = generar_nombre("producto", archivoproductoinst._name)
                        recurso = RecursosComunicacionInstitucional(nombre=f.cleaned_data['nombre'],
                                                                    descripcion=f.cleaned_data['descripcion'],
                                                                    objetivo=f.cleaned_data['objetivo'],
                                                                    archivo=archivoproductoinst,
                                                                    manual=manualfile)
                        recurso.save(request)
                        log(u'Adicionó producto: %s' % recurso, request, "act")
                    return JsonResponse({"result":False}, safe=False)
            except Exception as ex:
                pass

        elif action == 'ocultararchivomul':
            try:
                if 'id' in request.POST:
                    multimediarecurso = MultimediaRecursosComunicacionInstitucional.objects.get(status=True, id=int(request.POST['id']))
                    multimediarecurso.estado = 2
                    multimediarecurso.save(request)
                    log(u'Oculta multimedia: %s' % multimediarecurso, request, "act")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                pass

        elif action == 'mostrararchivomul':
            try:
                if 'id' in request.POST:
                    multimediarecurso = MultimediaRecursosComunicacionInstitucional.objects.get(status=True, id=int(request.POST['id']))
                    multimediarecurso.estado = 1
                    multimediarecurso.save(request)
                    log(u'Visualiza multimedia: %s' % multimediarecurso, request, "act")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                pass

        elif action == 'eliminararchivomul':
            try:
                if 'id' in request.POST:
                    multimediarecurso = MultimediaRecursosComunicacionInstitucional.objects.get(status=True, id=int(request.POST['id']))
                    multimediarecurso.status = False
                    multimediarecurso.save(request)
                    log(u'Elimina multimedia: %s' % multimediarecurso, request, "del")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                pass

        elif action == 'adicionararchivomul':
            try:
                f = MultimediaProductoComunicacionalForm(request.POST, request.FILES)
                files = request.FILES.getlist('archivorecurso')
                idrecursocom = int(request.GET['id'])
                nombrecont = 0
                nombrearchivos = []
                archivosolicitudproductoinst = None
                if len(files) > 0:
                    for file in files:
                        nombrearchivos.append(file._name)
                        request.FILES['archivorecurso'] = file
                        arch = file
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 50485760:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Error, el tamaño del manual es mayor a 4 Mb."})
                        if not exte.lower() == 'pdf' and not exte.lower() == 'png' and not exte.lower() == 'jpg' and not exte.lower() == 'zip' and not exte.lower() == 'rar':
                            return JsonResponse(
                                {"result": "bad",
                                 "mensaje": u"El archivo tiene que ser archivo pdf, png, jpg, zip o rar"})
                        archivosolicitudproductoinst = request.FILES['archivorecurso']
                        archivosolicitudproductoinst._name = generar_nombre("producto",
                                                                            archivosolicitudproductoinst._name)
                        multimediarecurso = MultimediaRecursosComunicacionInstitucional(recurso_id=idrecursocom, nombre=nombrearchivos[nombrecont],
                                                                                        archivo=archivosolicitudproductoinst)
                        multimediarecurso.save(request)
                        nombrecont = nombrecont +1
                        log(u'Adición archivo multimedia: %s' % multimediarecurso, request, "add")
                    return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                pass

        elif action == 'actualizarproductocomunicacional':
            try:
                f = ActualizarProductoComunicacional(request.POST, request.FILES)
                if f.is_valid():
                    if 'actualizarproducto' in request.FILES:
                        arch = request.FILES['actualizarproducto']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 50485760:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Error, el tamaño del producto es mayor a 50 Mb."})
                        if not exte.lower() == 'pdf' and not exte.lower() == 'png' and not exte.lower() == 'jpg' and not exte.lower() == 'jpeg' and not exte.lower() == 'zip':
                            return JsonResponse({"result": "bad", "mensaje": u"El producto tiene que ser archivo pdf, png, jpg, jpeg o zip"})
                        actualizarproducto = request.FILES['actualizarproducto']
                        actualizarproducto._name = generar_nombre("producto", actualizarproducto._name)
                    recurso = RecursosComunicacionInstitucional.objects.get(status=True, id=int(request.POST['id']))
                    recurso.archivo = actualizarproducto
                    recurso.save(request)
                    log(u'Actualizó archivo a recurso: %s' % recurso, request, "act")
                    return JsonResponse({"result":False}, safe=False)
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
            except Exception as ex:
                pass



    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'solicitudrecursos':
                try:
                    data['title'] = u'Solicitudes de recursos'
                    data['pendientes'] = SolicitudRecursosComunicacionInstitucional.objects.filter(status=True, estado=1)
                    data['aceptados'] = SolicitudRecursosComunicacionInstitucional.objects.filter(status=True, estado=2)
                    data['rechazados'] = SolicitudRecursosComunicacionInstitucional.objects.filter(status=True, estado=3)
                    return render(request, "solicitud_productos/visualizarsolicitudes.html", data)
                except Exception as ex:
                    pass

            elif action == 'missolicitudes':
                try:
                    data['title'] = u'Mis solicitudes'
                    data['solicitudes'] = SolicitudRecursosComunicacionInstitucional.objects.filter(status=True, solicitante=persona)
                    return render(request, "solicitud_productos/missolicitudes.html", data)
                except Exception as ex:
                    pass

            elif action == 'solicitudrecurso':
                try:
                    data['title'] = u'Nueva solicitud'
                    form = SolicitudRecursosComunicacionInstitucionalForm()
                    form.ocultarmanual()
                    data['form_2'] = form
                    return render(request, "solicitud_productos/solicitudrecursoinstitucional.html", data)
                except Exception as ex:
                    pass

            elif action == 'visualizarsolicitud':
                try:
                    data['solicitud'] = solicitud = SolicitudRecursosComunicacionInstitucional.objects.get(status=True, pk=int(request.GET['id']))
                    data['idsolicitud'] = int(request.GET['id'])
                    data['variosarchivos'] = False
                    form = SolicitudRecursosComunicacionInstitucionalForm()
                    form.ocultartipo()
                    if solicitud.tienemultimedia == 2:
                        template = template = get_template('solicitud_productos/modal/visualizarsolicitud.html')
                    else:
                        data['solicitudarchivosproductoszip'] = solicitudarchivoszip = MultimediaSolicitudRecursosComunicacionInstitucional.objects.filter(Q(status=True), Q(solicitud_id=solicitud.id), (Q(nombre__contains='.zip') | Q(nombre__contains='.rar')))
                        data['solicitudarchivosproductos'] = solicitudarchivos = MultimediaSolicitudRecursosComunicacionInstitucional.objects.filter(status=True, solicitud_id=solicitud.id).exclude(id__in=solicitudarchivoszip)
                        data['primerdocumento'] = solicitudarchivos[0]
                        template = template = get_template('solicitud_productos/modal/visualizarsolicitudvariosarchivos.html')
                    if solicitud.tipo == 2 :
                        form.tipocreacion()
                        if solicitud.tienemultimedia == 1:
                            form.norequeridoarchivo()
                        else:
                            form.ocultarproducto()
                    else:
                        template = get_template('solicitud_productos/modal/visualizarsolicitudcreacion.html')
                        form.validar()
                        form.validarproducto()
                    data['form2'] = form

                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'vistapreviasolicitud':
                try:
                    data['visible'] = True
                    data['solicitud'] = solicitud = SolicitudRecursosComunicacionInstitucional.objects.get(status=True, pk=int(request.GET['id']))
                    data['recurso'] = recurso = RecursosComunicacionInstitucional.objects.get(status=True, solicitud_id=solicitud.id)
                    data['idsolicitud'] = int(request.GET['id'])
                    form = SolicitudRecursosComunicacionInstitucionalForm()
                    form.sololectura()
                    form.fields['nombre'].initial = recurso.nombre
                    form.fields['descripcion'].initial = recurso.descripcion
                    form.fields['objetivo'].initial = recurso.objetivo
                    form.fields['tipo'].initial = solicitud.tipo
                    data['form2'] = form
                    if solicitud.tienemultimedia == 1:
                        data['bloqueoproducto'] = True
                        data['solicitudarchivosproductoszip'] = solicitudarchivoszip = MultimediaSolicitudRecursosComunicacionInstitucional.objects.filter(Q(status=True), Q(solicitud_id=solicitud.id),
                                                                                                                                                          (Q(nombre__contains='.zip') | Q(nombre__contains='.rar')))
                        data['solicitudarchivosproductos'] = solicitudarchivos = MultimediaSolicitudRecursosComunicacionInstitucional.objects.filter(status=True, solicitud_id=solicitud.id).exclude(id__in=solicitudarchivoszip)
                        data['primerdocumento'] = solicitudarchivos[0]
                        template = template = get_template(
                            'solicitud_productos/modal/visualizarsolicitudvariosarchivos.html')
                    else:
                        template = get_template('solicitud_productos/modal/visualizarsolicitud.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'visualizarrechazado':
                try:
                    # data['visible'] = visible = True
                    data['solicitud'] = solicitud = SolicitudRecursosComunicacionInstitucional.objects.get(status=True, pk=int(request.GET['id']))
                    data['idsolicitud'] = int(request.GET['id'])
                    form = SolicitudRecursosComunicacionInstitucionalForm()
                    form.ocultartipo()
                    if solicitud.tienemultimedia == 2:
                        template = template = get_template('solicitud_productos/modal/visualizarsolicitud.html')
                    else:
                        data['solicitudarchivosproductoszip'] = solicitudarchivoszip = MultimediaSolicitudRecursosComunicacionInstitucional.objects.filter(Q(status=True), Q(solicitud_id=solicitud.id),
                                                                                                                                                          (Q(nombre__contains='.zip') | Q(nombre__contains='.rar')))
                        data['solicitudarchivosproductos'] = solicitudarchivos = MultimediaSolicitudRecursosComunicacionInstitucional.objects.filter(status=True, solicitud_id=solicitud.id).exclude(id__in=solicitudarchivoszip)
                        data['primerdocumento'] = solicitudarchivos[0]
                        template = template = get_template('solicitud_productos/modal/visualizarsolicitudvariosarchivos.html')
                    if solicitud.tipo == 2:
                        form.tipocreacion()
                        # form.ocultarproducto()
                        if solicitud.tienemultimedia == 1:
                            form.norequeridoarchivo()
                        else:
                            form.ocultarproducto()
                    else:
                        template = get_template('solicitud_productos/modal/visualizarsolicitudcreacion.html')
                        form.validar()
                        form.validarproducto()
                    data['form2'] = form
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'cancelarsolicitudrecurso':
                try:
                    data['title'] = u'Confirmar cancelación'
                    data['solicitud'] = int(request.GET['id'])
                    data['action'] = 'cancelarsolicitudrecurso'
                    data['mensaje'] = u'Está seguro(a) que desea confirmar la cancelación de esta solicitud?.'
                    return render(request, "solicitud_productos/cancelarsolicitudrecurso.html", data)
                except:
                    pass

            elif action == 'rechazarsolicitudrecurso':
                try:
                    data['title'] = u'Confirmar rechazo de la solicitud'
                    data['solicitud'] = int(request.GET['id'])
                    data['action'] = 'rechazarsolicitudrecurso'
                    data['mensaje'] = u'Está seguro(a) que desea confirmar el rechazo de esta solicitud?.'
                    return render(request, "solicitud_productos/cancelarsolicitudrecurso.html", data)
                except:
                    pass

            elif action == 'catalogoproductos':
                try:
                    data['title'] = u'Catálogo de productos'
                    # data['recursos'] = RecursosComunicacionInstitucional.objects.filter(status=True)
                    search = None
                    ids = None
                    s = None
                    perfil = None
                    # data['recursos'] = RecursosComunicacionInstitucional.objects.filter(status=True, estado=1)
                    filtro = Q(status=True)
                    if 's' in request.GET:
                        s = request.GET['s']
                        data['s'] = s

                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(nombre__icontains=search) |
                                               Q(descripcion__icontains=search) |
                                               Q(objetivo__icontains=search))
                        else:
                            filtro = filtro & ((Q(nombre__icontains=ss[0]) &
                                                Q(nombre__icontains=ss[1])) |
                                               (Q(descripcion__icontains=ss[0]) &
                                                Q(descripcion__icontains=ss[1])) |
                                               (Q(objetivo__icontains=ss[0]) &
                                                Q(objetivo__icontains=ss[1])))
                    recurso = RecursosComunicacionInstitucional.objects.filter(filtro).distinct().order_by('-id')
                    data['totalproductoinstitucional'] = recurso.count()
                    paging = MiPaginador(recurso, 25)
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
                    data['perfil'] = perfil if perfil else ""
                    data['recursos'] = page.object_list
                    return render(request, "solicitud_productos/catalogoproductos.html", data)
                except:
                    pass

            elif action == 'ocultarproducto':
                try:
                    data['title'] = u'Confirmar acción'
                    data['recurso'] = int(request.GET['id'])
                    data['action'] = 'ocultarproducto'
                    data['mensaje'] = u'Está seguro(a) que desea ocultar este producto?.'
                    return render(request, "solicitud_productos/ocultarproducto.html", data)
                except:
                    pass

            elif action == 'mostrarproducto':
                try:
                    data['title'] = u'Confirmar acción'
                    data['recurso'] = int(request.GET['id'])
                    data['action'] = 'mostrarproducto'
                    data['mensaje'] = u'Está seguro(a) que desea mostrar este producto?.'
                    return render(request, "solicitud_productos/ocultarproducto.html", data)
                except:
                    pass

            elif action == 'rechazarsolicitud':
                try:
                    data['solicitud'] = solicitud = SolicitudRecursosComunicacionInstitucional.objects.get(status=True, pk=int(request.GET['id']))
                    template = template = get_template('solicitud_productos/modal/notificarrechazosolicitud.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'adicionarmanual':
                try:
                    data['producto'] = producto = RecursosComunicacionInstitucional.objects.get(status=True, pk=int(request.GET['idproducto']))
                    form = ProductoComunicacionInstitucional()
                    form.sololectura()
                    form.fields['nombre'].initial = producto.nombre
                    form.fields['descripcion'].initial = producto.descripcion
                    form.fields['objetivo'].initial = producto.objetivo
                    data['form2'] = form
                    data['action'] = 'adicionarmanual'
                    template = get_template('solicitud_productos/modal/formadicionarmanual.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'adicionarproductoinstitucional':
                try:
                    form = SolicitudRecursosComunicacionInstitucionalForm()
                    form.validar()
                    form.ocultartipo()
                    form.validarproducto()
                    form.fields['tipo'].initial = 1
                    template = template = get_template('solicitud_productos/modal/formadicionarproductoinstitucional.html')
                    data['form2'] = form
                    data['action'] = 'adicionarproductoinstitucional'
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'multimediaproductoscomunicacionales':
                try:
                    data['title'] = u'Multimedia de producto'
                    search = None
                    ids = None
                    s = None
                    perfil = None
                    filtro = (Q(status=True) & Q(recurso_id=int(request.GET['id'])))
                    data['idarchivomul'] = int(request.GET['id'])
                    if 's' in request.GET:
                        s = request.GET['s']
                        data['s'] = s

                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(nombre__icontains=search))
                        else:
                            filtro = filtro & ((Q(nombre__icontains=ss[0]) &
                                                Q(nombre__icontains=ss[1])))
                    recurso = MultimediaRecursosComunicacionInstitucional.objects.filter(filtro).distinct().order_by('-id')
                    data['totalproductoinstitucional'] = recurso.count()
                    paging = MiPaginador(recurso, 25)
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
                    data['perfil'] = perfil if perfil else ""
                    data['multimediarecursos'] = page.object_list
                    return render(request, "solicitud_productos/multimediaproductoscomunicacionales.html", data)
                except:
                    pass

            elif action == 'ocultararchivomul':
                try:
                    data['title'] = u'Confirmar acción'
                    data['archivomul'] = int(request.GET['id'])
                    data['idproductocom'] = int(request.GET['idarchivomul'])
                    data['action'] = 'ocultararchivomul'
                    data['mensaje'] = u'Está seguro(a) que desea ocultar este archivo?.'
                    return render(request, "solicitud_productos/mostrarocultararchivomul.html", data)
                except:
                    pass

            elif action == 'mostrararchivomul':
                try:
                    data['title'] = u'Confirmar acción'
                    data['archivomul'] = int(request.GET['id'])
                    data['idproductocom'] = int(request.GET['idarchivomul'])
                    data['action'] = 'mostrararchivomul'
                    data['mensaje'] = u'Está seguro(a) que desea mostrar este archivo?.'
                    return render(request, "solicitud_productos/mostrarocultararchivomul.html", data)
                except:
                    pass

            elif action == 'eliminararchivomul':
                try:
                    data['title'] = u'Confirmar acción'
                    data['archivomul'] = int(request.GET['id'])
                    data['idproductocom'] = int(request.GET['idarchivomul'])
                    data['action'] = 'eliminararchivomul'
                    data['mensaje'] = u'Está seguro(a) que desea confirmar la eliminación de este archivo?.'
                    return render(request, "solicitud_productos/mostrarocultararchivomul.html", data)
                except:
                    pass

            elif action == 'adicionararchivomul':
                try:
                    form = MultimediaProductoComunicacionalForm()
                    template = template = get_template('solicitud_productos/modal/formadicionararchivomul.html')
                    data['adicionararchivomul'] = int(request.GET['id'])
                    data['form2'] = form
                    data['action'] = 'adicionararchivomul'
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'reportedeproductoscomu':
                try:
                    totalconstatacion = None
                    data['listadorecursoscomunicacion'] = recursoscomunicacion = RecursosComunicacionInstitucional.objects.filter(status=True, estado=1)
                    totalproductoscomunicacion = recursoscomunicacion.count()
                    data['totalproductoscomunicacion'] = totalproductoscomunicacion
                    data['fecha'] = datetime.now().date()
                    return conviert_html_to_pdf('solicitud_productos/reporteproductoscomunicacion.html',
                                                {'pagesize': 'A4', 'data': data})
                except Exception as ex:
                    pass

            elif action == 'reportesolicitudesproductos':
                try:
                    tiposolicitud = int(request.GET['idtipo'])
                    estadosolicitud = int(request.GET['estadosolicitud'])
                    if estadosolicitud == 4:
                        if tiposolicitud == 3:
                            productosolicitud = SolicitudRecursosComunicacionInstitucional.objects.filter(status=True)
                        else:
                            productosolicitud = SolicitudRecursosComunicacionInstitucional.objects.filter(status=True, tipo=tiposolicitud)
                    else:
                        if tiposolicitud == 3:
                            productosolicitud = SolicitudRecursosComunicacionInstitucional.objects.filter(status=True,
                                                                                                          estado=estadosolicitud)
                        else:
                            productosolicitud = SolicitudRecursosComunicacionInstitucional.objects.filter(status=True,
                                                                                                          tipo=tiposolicitud,
                                                                                                          estado=estadosolicitud)
                    data['listadosolicitudesproductos'] = productosolicitud
                    data['totalsolicitudesproductos'] = totalsolicitudesproductos = productosolicitud.count()
                    data['fecha'] = datetime.now().date()
                    # return JsonResponse({"result": False}, safe=False)
                    return conviert_html_to_pdf('solicitud_productos/reportesolicitudesproductos.html',
                                                {'pagesize': 'A4', 'data': data})
                except Exception as ex:
                    pass

            elif action == 'cargarcombo_tiposolicitud':
                try:
                    lista = []
                    for tiposolicitud in TIPO_PRODUCTOCOMUNICACIONAL:
                        lista.append([tiposolicitud[0], tiposolicitud[1].__str__()])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cargarcombo_estadosolicitud':
                try:
                    lista = []
                    idestadosolicitud = 4
                    opcionestadosolicitud = 'GENERAL'
                    for estadosolicitud in ESTADO_SOLICITUDRECURSO:
                        if not estadosolicitud[0] == 4:
                            lista.append([estadosolicitud[0], estadosolicitud[1].__str__()])
                    lista.append([idestadosolicitud, opcionestadosolicitud.__str__()])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'actualizarproductocomunicacional':
                try:
                    form = ActualizarProductoComunicacional()
                    data['producto'] = producto = RecursosComunicacionInstitucional.objects.get(status=True, pk=int(request.GET['idproducto']))
                    form.camposnorequeridos()
                    form.fields['nombre'].initial = producto.nombre
                    form.fields['descripcion'].initial = producto.descripcion
                    form.fields['objetivo'].initial = producto.objetivo
                    data['form2'] = form
                    data['action'] = 'actualizarproductocomunicacional'
                    template = get_template('solicitud_productos/modal/formactualizarproductocomunicacional.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

        else:
            try:
                data['title'] = u'Solicitudes de productos'
                search2 = None
                search3 = None
                solicitudes = SolicitudRecursosComunicacionInstitucional.objects.filter(status=True)
                solicitudes_estado2 = solicitudes.filter(estado=2)
                solicitudes_estado3 = solicitudes.filter(estado=3)
                data['pendientes'] = SolicitudRecursosComunicacionInstitucional.objects.filter(status=True, estado=1).order_by('-id')


                data['aceptados'] = SolicitudRecursosComunicacionInstitucional.objects.filter(status=True, estado=2)
                if 's2' in request.GET:
                    search2 = request.GET['s2'].strip()
                    ss = search2.split(' ')
                    if len(ss) == 1:
                        solicitudes_estado2 = solicitudes_estado2.filter(Q(nombre__icontains=search2) |
                                                                         Q(descripcion__icontains=search2) |
                                                                         Q(objetivo__icontains=search2)).order_by('-id')
                    else:
                        solicitudes_estado2 = solicitudes_estado2.filter((Q(nombre__icontains=ss[0]) &
                                                                         Q(nombre__icontains=ss[1])) |
                                                                        (Q(descripcion__icontains=ss[0]) &
                                                                         Q(descripcion__icontains=ss[1])) |
                                                                        (Q(objetivo__icontains=ss[0]) &
                                                                         Q(objetivo__icontains=ss[1]))).order_by('-id')
                paging_estado2 = MiPaginador(solicitudes_estado2, 25)
                p2 = 1
                try:
                    paginasesion2 = 1
                    if 'paginador2' in request.session:
                        paginasesion2 = int(request.session['paginador2'])
                    else:
                        p2 = paginasesion2
                    if 'page_estado2' in request.GET:
                        p2 = int(request.GET['page_estado2'])
                    else:
                        p2 = paginasesion2
                    try:
                        page2 = paging_estado2.page(p2)
                    except:
                        p2 = 1
                    page2 = paging_estado2.page(p2)
                except:
                    page2 = paging_estado2.page(p2)
                request.session['paginador2'] = p2
                data['paging_estado2'] = paging_estado2
                data['rangospaging'] = paging_estado2.rangos_paginado(p2)
                data['page_estado2'] = page2
                data['search2'] = search2 if search2 else ""
                data['aceptados'] = page2.object_list

                if 's3' in request.GET:
                    search3 = request.GET['s3'].strip()
                    ss3 = search3.split(' ')
                    if len(ss3) == 1:
                        solicitudes_estado3 = solicitudes_estado3.filter(Q(nombre__icontains=search3) |
                                                                         Q(descripcion__icontains=search3) |
                                                                         Q(objetivo__icontains=search3)).order_by('-id')
                    else:
                        solicitudes_estado3 = solicitudes_estado3.filter((Q(nombre__icontains=ss3[0]) &
                                                                         Q(nombre__icontains=ss3[1])) |
                                                                        (Q(descripcion__icontains=ss3[0]) &
                                                                         Q(descripcion__icontains=ss3[1])) |
                                                                        (Q(objetivo__icontains=ss3[0]) &
                                                                         Q(objetivo__icontains=ss3[1]))).order_by('-id')
                paging_estado3 = MiPaginador(solicitudes_estado3, 25)
                p3 = 1
                try:
                    paginasesion3 = 1
                    if 'paginador3' in request.session:
                        paginasesion3 = int(request.session['paginador3'])
                    else:
                        p3 = paginasesion3
                    if 'page_estado3' in request.GET:
                        p3 = int(request.GET['page_estado3'])
                    else:
                        p3 = paginasesion3
                    try:
                        page3 = paging_estado3.page(p3)
                    except:
                        p3 = 1
                    page3 = paging_estado3.page(p3)
                except:
                    page3 = paging_estado3.page(p3)
                request.session['paginador3'] = p3
                data['paging_estado3'] = paging_estado3
                data['rangospaging'] = paging_estado3.rangos_paginado(p3)
                data['page_estado3'] = page3
                data['search3'] = search3 if search3 else ""
                data['rechazados'] = page3.object_list


                # data['rechazados'] = SolicitudRecursosComunicacionInstitucional.objects.filter(status=True, estado=3)
                return render(request, "solicitud_productos/view.html", data)
            except Exception as ex:
                pass