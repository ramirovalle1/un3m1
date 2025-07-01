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
    convertir_fecha_hora_invertida, notificacion
from inno.models import HorarioTutoriaAcademica, SolicitudTutoriaIndividual, SolicitudTutoriaIndividualTema, \
    ESTADO_SOLICITUD_TUTORIA, RegistroClaseTutoriaDocente, DetalleSolicitudHorarioTutoria
from sga.models import SolicitudRecursosComunicacionInstitucional, RecursosComunicacionInstitucional, MultimediaRecursosComunicacionInstitucional, \
    MultimediaSolicitudRecursosComunicacionInstitucional, RecorridoRegistroSolicitud
from sga.forms import SolicitudRecursosComunicacionInstitucionalForm
from inno.forms import TutoriaManualForm, ProgramarTutoriasForm, ConvocarTutoriaManualForm
from django.db.models import Q, Sum
from datetime import datetime, timedelta, date
from django.template.loader import get_template
from settings import SITE_STORAGE
from sga.templatetags.sga_extras import encrypt
import json
from django.template import Context
from sga.tasks import send_html_mail, conectar_cuenta
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
                if f.is_valid():
                    if 'tipo' in request.POST:
                        tipo = int(request.POST['tipo'])
                        if tipo == 1:
                            solicitud = SolicitudRecursosComunicacionInstitucional(solicitante=persona,
                                                                                   descripcion=request.POST['descripcion'],
                                                                                   objetivo=request.POST['objetivo'],
                                                                                   fechasolicitud=datetime.now().date())
                        else:
                            files = request.FILES.getlist('archivorecurso')
                            nombrecont = 0
                            nombrearchivos = []
                            archivosolicitudproductoinst = None
                            if len(files) > 1:
                                solicitud = SolicitudRecursosComunicacionInstitucional(solicitante=persona,
                                                                                       nombre=request.POST['nombre'],
                                                                                       descripcion=request.POST['descripcion'],
                                                                                       objetivo=request.POST['objetivo'],
                                                                                       tipo=2,
                                                                                       fechasolicitud=datetime.now().date(),
                                                                                       tienemultimedia=1)
                                solicitud.save(request)
                                for file in files:
                                    nombrearchivos.append(file._name)
                                    request.FILES['archivorecurso'] = file
                                    arch = file
                                    extension = arch._name.split('.')
                                    tam = len(extension)
                                    exte = extension[tam - 1]
                                    if arch.size > 50485760:
                                        return JsonResponse(
                                            {"result": "bad", "mensaje": u"Error, el tamaño del archivo" + str(file) + "es mayor a 50 Mb."})
                                    if not exte.lower() == 'pdf' and not exte.lower() == 'png' and not exte.lower() == 'jpg' and not exte.lower() == 'zip' and not exte.lower() == 'rar':
                                        return JsonResponse(
                                            {"result": "bad", "mensaje": u"El archivo tiene que ser archivo pdf, png, jpg, zip o rar"})
                                    archivosolicitudproductoinst = request.FILES['archivorecurso']
                                    archivosolicitudproductoinst._name = generar_nombre("solicitudproducto", archivosolicitudproductoinst._name)
                                    multimediasolicitudrecurso = MultimediaSolicitudRecursosComunicacionInstitucional(solicitud_id=solicitud.id,
                                                                                                    nombre=nombrearchivos[nombrecont],
                                                                                                    archivo=archivosolicitudproductoinst)
                                    multimediasolicitudrecurso.save(request)
                                    nombrecont = nombrecont + 1
                            else:
                                if 'archivorecurso' in request.FILES:
                                    arch = request.FILES['archivorecurso']
                                    extension = arch._name.split('.')
                                    tam = len(extension)
                                    exte = extension[tam - 1]
                                    if arch.size > 4194304:
                                        return JsonResponse(
                                            {"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                                    if not exte.lower() == 'pdf' and not exte.lower() == 'png' and not exte.lower() == 'jpg' and not exte.lower() == 'zip' and not exte.lower() == 'rar':
                                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf o .png"})
                                    newfile = request.FILES['archivorecurso']
                                    newfile._name = generar_nombre("recurso", newfile._name)
                                directory = os.path.join(SITE_STORAGE, 'media', 'recursoscomunicacioninstitucional')
                                try:
                                    os.stat(directory)
                                except:
                                    os.mkdir(directory)
                                solicitud = SolicitudRecursosComunicacionInstitucional(solicitante=persona,
                                                                                       nombre=request.POST['nombre'],
                                                                                       descripcion=request.POST['descripcion'],
                                                                                       objetivo=request.POST['objetivo'],
                                                                                       archivo=newfile,
                                                                                       tipo=2,
                                                                                       fechasolicitud=datetime.now().date())
                        solicitud.save(request)
                        recorridosolicitud = RecorridoRegistroSolicitud(solicitud=solicitud,
                                                                        fecha=datetime.now().date(),
                                                                        persona=persona,
                                                                        observacion='SOLICITUD ENVIADA',
                                                                        estadosolicitud=1)
                        recorridosolicitud.save()
                        log(u'Generó una solicitud: %s' % solicitud, request, "add")
                        return JsonResponse({'result': 'ok'})
            except Exception as ex:
                pass


        elif action == 'aceptarsolicitud':
            try:
                f = SolicitudRecursosComunicacionInstitucionalForm(request.POST)
                if f.is_valid():
                    solicitud = SolicitudRecursosComunicacionInstitucional.objects.get(status=True, pk=int(request.POST['idsolicitud']))
                    recurso = RecursosComunicacionInstitucional(solicitud_id=solicitud.id,
                                                                nombre=f.cleaned_data['nombre'],
                                                                descripcion=f.cleaned_data['descripcion'],
                                                                objetivo=f.cleaned_data['objetivo'],
                                                                archivo=solicitud.archivo)
                    # solicitud.aceptasolicitud = persona
                    solicitud.estado = 2
                    recurso.save(request)
                    solicitud.save(request)
                    log(u'Adicionó un recurso: %s' % recurso, request, "add")
                    return JsonResponse({"result":False}, safe=False)
            except Exception as ex:
                pass

        elif action == 'cancelarsolicitudrecurso':
            try:
                if 'id' in request.POST:
                    solicitud = SolicitudRecursosComunicacionInstitucional.objects.get(status=True, pk=int(request.POST['id']))
                    solicitud.estado = 4
                    solicitud.save(request)
                    recorridosolicitud = RecorridoRegistroSolicitud(solicitud=solicitud,
                                                                    fecha=datetime.now().date(),
                                                                    persona=persona,
                                                                    observacion='SOLICITUD CANCELADA',
                                                                    estadosolicitud=5)
                    recorridosolicitud.save()
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



    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'solicitudrecursos':
                try:
                    data['title'] = u'Solicitudes de recursos'
                    data['pendientes'] = SolicitudRecursosComunicacionInstitucional.objects.filter(status=True, estado=1)
                    data['aceptados'] = SolicitudRecursosComunicacionInstitucional.objects.filter(status=True, estado=2)
                    data['rechazados'] = SolicitudRecursosComunicacionInstitucional.objects.filter(status=True, estado=3)
                    return render(request, "comunicacion_institucional/visualizarsolicitudes.html", data)
                except Exception as ex:
                    pass

            elif action == 'missolicitudes':
                try:
                    data['title'] = u'Mis solicitudes'
                    search = None
                    ids = None
                    s = None
                    perfil = None
                    filtro = Q(status=True, solicitante=persona)
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
                    solicitud = SolicitudRecursosComunicacionInstitucional.objects.filter(filtro).distinct().order_by('estado')
                    paging = MiPaginador(solicitud, 25)
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
                    data['solicitudes'] = page.object_list
                    return render(request, "comunicacion_institucional/missolicitudes.html", data)
                except Exception as ex:
                    pass

            elif action == 'solicitudrecurso':
                try:
                    data['title'] = u'Nueva solicitud'
                    form = SolicitudRecursosComunicacionInstitucionalForm()
                    form.ocultarmanual()
                    data['form_2'] = form
                    return render(request, "comunicacion_institucional/solicitudrecursoinstitucional.html", data)
                except Exception as ex:
                    pass

            elif action == 'verificarsolicitudes':
                try:
                    solicitud = SolicitudRecursosComunicacionInstitucional.objects.filter(status=True, solicitante=persona, estado=3)
                    if not solicitud:
                        return JsonResponse({"result":"ok"})
                    return JsonResponse({"result": "bad", "mensaje": u"No puede generar una nueva solicitud mientras mantenga una rechazada"})
                except Exception as ex:
                    pass

            elif action == 'visualizarsolicitud':
                try:
                    data['solicitud'] = solicitud = SolicitudRecursosComunicacionInstitucional.objects.get(status=True, pk=int(request.GET['id']))
                    data['idsolicitud'] = int(request.GET['id'])
                    form = SolicitudRecursosComunicacionInstitucionalForm()
                    form.ocultartipo()
                    if solicitud.tipo == 2 :
                        form.tipocreacion()
                        form.ocultarproducto()
                    else:
                        form.validar()
                    data['form2'] = form
                    template = get_template('comunicacion_institucional/modal/visualizarsolicitud.html')
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
                    data['form2'] = form
                    template = get_template('comunicacion_institucional/modal/visualizarsolicitud.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'cancelarsolicitudrecurso':
                try:
                    data['title'] = u'Confirmar cancelación'
                    data['solicitud'] = int(request.GET['id'])
                    data['action'] = 'cancelarsolicitudrecurso'
                    data['mensaje'] = u'Está seguro(a) que desea confirmar la cancelación de esta solicitud?.'
                    return render(request, "comunicacion_institucional/cancelarsolicitudrecurso.html", data)
                except:
                    pass

            elif action == 'rechazarsolicitudrecurso':
                try:
                    data['title'] = u'Confirmar rechazo de la solicitud'
                    data['solicitud'] = int(request.GET['id'])
                    data['action'] = 'rechazarsolicitudrecurso'
                    data['mensaje'] = u'Está seguro(a) que desea confirmar el rechazo de esta solicitud?.'
                    return render(request, "comunicacion_institucional/cancelarsolicitudrecurso.html", data)
                except:
                    pass

            elif action == 'catalogoproductos':
                try:
                    data['title'] = u'Catálogo de productos'
                    data['recursos'] = RecursosComunicacionInstitucional.objects.filter(status=True)
                    return render(request, "comunicacion_institucional/catalogoproductos.html", data)
                except:
                    pass

            elif action == 'ocultarproducto':
                try:
                    data['title'] = u'Confirmar acción'
                    data['recurso'] = int(request.GET['id'])
                    data['action'] = 'ocultarproducto'
                    data['mensaje'] = u'Está seguro(a) que desea ocultar este producto?.'
                    return render(request, "comunicacion_institucional/ocultarproducto.html", data)
                except:
                    pass

            elif action == 'mostrarproducto':
                try:
                    data['title'] = u'Confirmar acción'
                    data['recurso'] = int(request.GET['id'])
                    data['action'] = 'mostrarproducto'
                    data['mensaje'] = u'Está seguro(a) que desea mostrar este producto?.'
                    return render(request, "comunicacion_institucional/ocultarproducto.html", data)
                except:
                    pass

            elif action == 'mostrarmultimediaproductos':
                try:
                    data['recursos'] = MultimediaRecursosComunicacionInstitucional.objects.filter(status=True, recurso_id=int(request.GET['id']), estado=1)
                    template = template = get_template('comunicacion_institucional/modal/mostrarmultimediaproductos.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'multimediasolicitudproductoscomunicacionales':
                try:
                    data['title'] = u'Archivos enviados'
                    search = None
                    ids = None
                    s = None
                    perfil = None
                    filtro = (Q(status=True) & Q(solicitud_id=int(request.GET['id'])))
                    data['id'] = int(request.GET['id'])
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
                    recurso = MultimediaSolicitudRecursosComunicacionInstitucional.objects.filter(filtro).distinct().order_by('-id')
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
                    data['multimediasolicitudrecursos'] = page.object_list
                    return render(request, "comunicacion_institucional/multimediasolicitudproductoscomunicacionales.html", data)
                except:
                    pass

            elif action == 'mostrarrecorrido':
                try:
                    data['title'] = u'Recorrido de la solicitud'
                    recorridosolicitud = RecorridoRegistroSolicitud.objects.filter(solicitud_id=int(request.GET['id']))
                    solicitud = SolicitudRecursosComunicacionInstitucional.objects.get(id=int(request.GET['id']))
                    data['solicitud'] = solicitud
                    data['recorrido'] = recorridosolicitud
                    template = get_template("comunicacion_institucional/recorridosolicitud.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        else:
            try:
                search = None
                ids = None
                s = None
                perfil = None
                data['title'] = u'Productos de la institución'
                # data['recursos'] = RecursosComunicacionInstitucional.objects.filter(status=True, estado=1)
                filtro = Q(status=True, estado=1)
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
                return render(request, "comunicacion_institucional/view.html", data)
            except Exception as ex:
                pass