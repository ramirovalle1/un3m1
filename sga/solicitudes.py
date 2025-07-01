# -*- coding: latin-1 -*-
from datetime import datetime
import json
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import RequestContext
from decorators import secure_module, last_access
from settings import SOLICITUD_NUMERO_AUTOMATICO, SECRETARIA_GROUP_ID
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import RespuestaSolicitudSecretariaDocenteForm, SolicitudSecretariaForm, NumeroTramiteForm, \
    ReasignarSolicitudResponsableForm, ArchivoSolicitudSecretariaForm
from sga.funciones import MiPaginador, log, generar_nombre
from sga.models import SolicitudSecretariaDocente, TipoSolicitudSecretariaDocente, Inscripcion, Persona, HistorialSolicitud

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'editar':
                try:
                    f = RespuestaSolicitudSecretariaDocenteForm(request.POST)
                    if f.is_valid():
                        solicitud = SolicitudSecretariaDocente.objects.get(pk=request.POST['id'])
                        solicitud.descripcion = f.cleaned_data['solicitud']
                        solicitud.save(request)
                        log(u'Editar respuesta solucitud: %s' % solicitud, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'comentar':
                try:
                    f = RespuestaSolicitudSecretariaDocenteForm(request.POST)
                    if f.is_valid():
                        solicitud = SolicitudSecretariaDocente.objects.get(pk=request.POST['id'])
                        solicitud.respuesta = f.cleaned_data['descripcion']
                        solicitud.save(request)
                        log(u'Comentar solicitud: %s' % solicitud, request, "edit")
                        solicitud.mail_subject_comentar(request.session['nombresistema'])
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'valorsolicitud':
                try:
                    tipo = TipoSolicitudSecretariaDocente.objects.get(pk=request.POST['id'])
                    return JsonResponse({"result": "ok", "valor": tipo.valor, "informacion": tipo.descripcion, "costo_base": tipo.costo_base, 'costo_unico': tipo.costo_unico})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

            elif action == 'adicionar':
                try:
                    form = SolicitudSecretariaForm(request.POST, request.FILES)
                    if form.is_valid():
                        if SolicitudSecretariaDocente.objects.values('id').filter(numero_tramite=form.cleaned_data['numero_tramite']).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"El numero de tramite ya existe"})
                        inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                        newfile = None
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("documentosolicitud_", newfile._name)
                        responsable = None
                        if Persona.objects.values('id').filter(usuario__groups__in=Group.objects.filter(id=SECRETARIA_GROUP_ID), usuario__is_active=True).exists():
                            responsable = Persona.objects.filter(usuario__groups__in=Group.objects.filter(id=SECRETARIA_GROUP_ID), usuario__is_active=True)[0]
                        solicitud = SolicitudSecretariaDocente(tipo=form.cleaned_data['tipo'],
                                                               fecha=datetime.now().date(),
                                                               hora=datetime.now().time(),
                                                               numero_tramite=0,
                                                               archivado=form.cleaned_data['archivado'],
                                                               persona=inscripcion.persona,
                                                               responsable=responsable,
                                                               descripcion=form.cleaned_data['descripcion'],
                                                               archivo=newfile)
                        solicitud.save(request)
                        historial = HistorialSolicitud(solicitud=solicitud,
                                                       fecha=datetime.now(),
                                                       persona=solicitud.responsable)
                        historial.save(request)
                        if SOLICITUD_NUMERO_AUTOMATICO:
                            if SolicitudSecretariaDocente.objects.values('id').filter(numero_tramite__gt=0).exists():
                                ultima = SolicitudSecretariaDocente.objects.filter(numero_tramite__gt=0).order_by('-id')[0]
                                solicitud.numero_tramite = ultima.numero_tramite + 1
                            else:
                                solicitud.numero_tramite = 1
                        else:
                            solicitud.numero_tramite = form.cleaned_data['numero_tramite']
                        solicitud.save(request)
                        solicitud.mail_subject_nuevo(request.session['nombresistema'])
                        log(u'Adiciono solicitud a secretaria: %s' % solicitud, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'subirarchivo':
                try:
                    form = ArchivoSolicitudSecretariaForm(request.POST, request.FILES)
                    if form.is_valid():
                        solicitud = SolicitudSecretariaDocente.objects.get(pk=request.POST['id'])
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("documentosolicitud_", newfile._name)
                        solicitud.archivo = newfile
                        solicitud.save(request)
                        log(u'Subir archivo de solicitud: %s' % solicitud, request, "edit")
                        return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'adicionartramite':
                try:
                    solicitud = SolicitudSecretariaDocente.objects.get(pk=request.POST['id'])
                    form = NumeroTramiteForm(request.POST)
                    if form.is_valid():
                        if SolicitudSecretariaDocente.objects.values('id').filter(numero_tramite=form.cleaned_data['numero_tramite']).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"El numero de tramite ya existe"})
                        solicitud.fecha = form.cleaned_data['fecha']
                        solicitud.numero_tramite = form.cleaned_data['numero_tramite']
                        solicitud.save(request)
                        log(u'Adicionar tramite de solicitud: %s' % solicitud, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'reasignar':
                try:
                    form = ReasignarSolicitudResponsableForm(request.POST)
                    if form.is_valid():
                        solicitud = SolicitudSecretariaDocente.objects.get(pk=request.POST['id'])
                        solicitud.responsable = form.cleaned_data['responsable']
                        solicitud.save(request)
                        historial = HistorialSolicitud(solicitud=solicitud,
                                                       fecha=datetime.now(),
                                                       persona=solicitud.responsable)
                        historial.save(request)
                        log(u'Reasignar solicitud responsable: %s' % solicitud, request, "edit")
                        solicitud.mail_reenvio(request.session['nombresistema'])
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'cerrar':
                try:
                    solicitud = SolicitudSecretariaDocente.objects.get(pk=request.POST['id'])
                    solicitud.fechacierre = datetime.now().date()
                    solicitud.cerrada = True
                    solicitud.save(request)
                    log(u'Cerrar solicitud: %s' % solicitud, request, "del")
                    solicitud.mail_subject_cierre(request.session['nombresistema'])
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'eliminar':
                try:
                    solicitud = SolicitudSecretariaDocente.objects.get(pk=request.POST['id'])
                    rubro = solicitud.rubro()
                    if rubro:
                        rubro.solicitud = None
                        rubro.save(request)
                    log(u'Elimino solicitud a secretaria: %s' % solicitud, request, "del")
                    solicitud.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'cerrar':
                try:
                    data['title'] = u'Cerrar solicitud'
                    data['solicitud'] = SolicitudSecretariaDocente.objects.get(pk=request.GET['id'])
                    return render(request, "solicitudes/cerrar.html", data)
                except Exception as ex:
                    pass

            if action == 'eliminar':
                try:
                    data['title'] = u'Eliminar solicitud'
                    data['solicitud'] = SolicitudSecretariaDocente.objects.get(pk=request.GET['id'])
                    return render(request, "solicitudes/eliminar.html", data)
                except Exception as ex:
                    pass

            elif action == 'comentar':
                try:
                    data['title'] = u'Responder solicitud'
                    data['solicitud'] = solicitud = SolicitudSecretariaDocente.objects.get(pk=request.GET['id'])
                    form = RespuestaSolicitudSecretariaDocenteForm(initial={'solicitud': solicitud.descripcion,
                                                                            'descripcion': solicitud.respuesta})
                    form.respuesta()
                    data['form'] = form
                    return render(request, "solicitudes/comentar.html", data)
                except Exception as ex:
                    pass

            elif action == 'editar':
                try:
                    data['title'] = u'Editar solicitud'
                    data['solicitud'] = solicitud = SolicitudSecretariaDocente.objects.get(pk=request.GET['id'])
                    form = RespuestaSolicitudSecretariaDocenteForm(initial={'solicitud': solicitud.descripcion,
                                                                            'descripcion': solicitud.respuesta})
                    form.editar(solicitud)
                    data['form'] = form
                    return render(request, "solicitudes/editar.html", data)
                except Exception as ex:
                    pass

            elif action == 'adicionar':
                try:
                    data['title'] = u'Adicionar nueva solicitud'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    form = SolicitudSecretariaForm(initial={'cantidad': 1})
                    if SOLICITUD_NUMERO_AUTOMATICO:
                        form.tramite_automatico()
                    form.editar()
                    data['form'] = form
                    return render(request, "solicitudes/adicionar.html", data)
                except Exception as ex:
                    pass

            elif action == 'adicionartramite':
                try:
                    data['title'] = u'Adicionar Nº de tramite'
                    data['solicitud'] = SolicitudSecretariaDocente.objects.get(pk=request.GET['id'])
                    data['form'] = NumeroTramiteForm(initial={'fecha': datetime.now().date(),
                                                              'numero_tramite': 0})
                    return render(request, "solicitudes/adicionartramite.html", data)
                except Exception as ex:
                    pass

            elif action == 'reasignar':
                try:
                    data['title'] = u'Reasignar responsable'
                    data['solicitud'] = SolicitudSecretariaDocente.objects.get(pk=request.GET['id'])
                    form = ReasignarSolicitudResponsableForm()
                    lista = Persona.objects.filter(Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)).distinct()
                    form.responsables(lista)
                    data['form'] = form
                    return render(request, "solicitudes/reasignar.html", data)
                except Exception as ex:
                    pass

            elif action == 'historialreasignacion':
                try:
                    data['title'] = u'Historial de Reasignaciones '
                    solicitud = SolicitudSecretariaDocente.objects.get(pk=request.GET['id'])
                    data['solicitudes'] = solicitud.historialsolicitud_set.all()
                    return render(request, "solicitudes/historialreasignacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'subirarchivo':
                try:
                    data['title'] = u'Subir Archivo'
                    data['solicitud'] = SolicitudSecretariaDocente.objects.get(pk=request.GET['id'])
                    data['form'] = ArchivoSolicitudSecretariaForm()
                    return render(request, "solicitudes/subirarchivo.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Solicitudes de estudiantes'
            ids = None
            search = None
            persona = request.session['persona']
            if persona.grupo_secretaria() or persona.es_administrador():
                if 's' in request.GET:
                    search = request.GET['s']
                    ss = search.split(' ')
                    while '' in ss:
                        ss.remove('')
                    if len(ss) == 1:
                        solicitudes = SolicitudSecretariaDocente.objects.filter(Q(descripcion__icontains=search) | Q(respuesta__icontains=search) | Q(persona__apellido1__icontains=search) | Q(persona__apellido2__icontains=search) | Q(persona__nombres__icontains=search) | Q(numero_tramite__icontains=search))
                    else:
                        solicitudes = SolicitudSecretariaDocente.objects.filter(Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1]))
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    solicitudes = SolicitudSecretariaDocente.objects.filter(id=ids)
                else:
                    solicitudes = SolicitudSecretariaDocente.objects.all()
            else:
                if 's' in request.GET:
                    search = request.GET['s']
                    ss = search.split(' ')
                    while '' in ss:
                        ss.remove('')
                    if len(ss) == 1:
                        solicitudes = SolicitudSecretariaDocente.objects.filter(Q(descripcion__icontains=search) | Q(respuesta__icontains=search) | Q(persona__apellido1__icontains=search) | Q(persona__apellido2__icontains=search) | Q(persona__nombres__icontains=search) | Q(numero_tramite__icontains=search), responsable=persona)
                    else:
                        solicitudes = SolicitudSecretariaDocente.objects.filter(Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1]), responsable=persona)

                elif 'id' in request.GET:
                    ids = request.GET['id']
                    solicitudes = SolicitudSecretariaDocente.objects.filter(responsable=persona, id=ids)
                else:
                    solicitudes = SolicitudSecretariaDocente.objects.filter(responsable=persona)
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
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['solicitudes'] = page.object_list
            data['reporte_0'] = obtener_reporte('solicitudes_secretaria')
            data['solicitud_numero_automatico'] = SOLICITUD_NUMERO_AUTOMATICO
            return render(request, "solicitudes/view.html", data)