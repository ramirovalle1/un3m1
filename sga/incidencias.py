# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from settings import RECTORADO_GROUP_ID, SISTEMAS_GROUP_ID
from sga.commonviews import adduserdata
from sga.forms import TipoIncidenciaForm, ResponderIncidenciaForm
from sga.funciones import MiPaginador
from sga.models import Incidencia, TipoIncidencia


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'reenviar':
            try:
                incidencia = Incidencia.objects.get(pk=request.POST['id'])
                f = TipoIncidenciaForm(request.POST)
                if f.is_valid():
                    incidencia.tipo = f.cleaned_data['tipo']
                    incidencia.save(request)
                    incidencia.mail_nuevo(request.session['nombresistema'])
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'responder':
            try:
                incidencia = Incidencia.objects.get(pk=request.POST['id'])
                f = ResponderIncidenciaForm(request.POST)
                if f.is_valid():
                    incidencia.solucion += (" / " if incidencia.solucion else '') + " " + f.cleaned_data['solucion'] + " / RESPUESTA POR: " + persona.nombre_completo() + " " + datetime.now().replace(microsecond=0).__str__()
                    incidencia.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'reenviar':
                try:
                    data['title'] = u'Reasignar incidencia'
                    incidencia = Incidencia.objects.get(pk=request.GET['id'])
                    data['incidencia'] = incidencia
                    data['form'] = TipoIncidenciaForm()
                    return render(request, "incidencias/reenviar.html", data)
                except Exception as ex:
                    pass

            elif action == 'responder':
                try:
                    data['title'] = u'Responder incidencia'
                    incidencia = Incidencia.objects.get(pk=request.GET['id'])
                    data['incidencia'] = incidencia
                    data['form'] = ResponderIncidenciaForm()
                    return render(request, "incidencias/responder.html", data)
                except Exception as ex:
                    pass

            elif action == 'cerrar':
                try:
                    incidencia = Incidencia.objects.get(pk=request.GET['id'])
                    incidencia.cerrada = True
                    incidencia.mail_respuesta(request.session['nombresistema'])
                    incidencia.save(request)
                    return HttpResponseRedirect("/incidencias?id=" + request.GET['id'])
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Listado de incidencias en clases'
            search = None
            ids = None
            data['tipoid'] = None
            if persona.en_grupo(RECTORADO_GROUP_ID) or persona.en_grupo(SISTEMAS_GROUP_ID):
                if 'id' in request.GET:
                    ids = int(request.GET['id'])
                    incidencias = Incidencia.objects.filter(id=ids)
                elif 's' in request.GET:
                    search = request.GET['s']
                    incidencias = Incidencia.objects.filter(Q(contenido__icontains=search) |
                                                            Q(lecciongrupo__profesor__persona__apellido1__icontains=search) |
                                                            Q(lecciongrupo__profesor__persona__apellido1__icontains=search) |
                                                            Q(lecciongrupo__profesor__persona__apellido2__icontains=search) |
                                                            Q(tipo__nombre__icontains=search)).distinct()
                else:
                    incidencias = Incidencia.objects.all()
            else:
                if 'id' in request.GET:
                    ids = int(request.GET['id'])
                    incidencias = Incidencia.objects.filter(id=ids, tipo__responsable=persona)
                elif 's' in request.GET:
                    search = request.GET['s']
                    incidencias = Incidencia.objects.filter(Q(tipo__responsable=persona),
                                                            Q(contenido__icontains=search) |
                                                            Q(lecciongrupo__profesor__persona__nombres__icontains=search) |
                                                            Q(lecciongrupo__profesor__persona__apellido1__icontains=search) |
                                                            Q(lecciongrupo__profesor__persona__apellido2__icontains=search) |
                                                            Q(tipo__nombre__icontains=search)).distinct()
                else:
                    incidencias = Incidencia.objects.filter(tipo__responsable=persona)
            if 'tipoid' in request.GET:
                incidencias = incidencias.filter(tipo__id=request.GET['tipoid'])
                data['tipoid'] = int(request.GET['tipoid'])
            paging = MiPaginador(incidencias, 25)
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
            data['incidencias'] = page.object_list
            data['tiposincidencias'] = TipoIncidencia.objects.all()
            return render(request, "incidencias/view.html", data)
