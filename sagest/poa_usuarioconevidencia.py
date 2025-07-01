# -*- coding: UTF-8 -*-
import json
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import get_template

from decorators import secure_module
from sagest.forms import UsuarioEvidenciaForm, UsuarioConsultaEvidenciaForm
from sagest.models import UsuarioEvidencia, UsuarioConsultaEvidencia
from sga.commonviews import adduserdata
from sga.models import Persona
from sga.funciones import log, MiPaginador

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    data = {'title': u'Permiso Consultar POA'}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'add':
            f = UsuarioConsultaEvidenciaForm(request.POST)
            if f.is_valid():
                try:
                    if UsuarioConsultaEvidencia.objects.filter(status=True, userpermiso_id=int(request.POST['userpermiso']), unidadorganica=f.cleaned_data['unidadorganica']).exists():
                        usua = UsuarioConsultaEvidencia.objects.get(status=True, userpermiso_id=int(request.POST['id']), unidadorganica=f.cleaned_data['unidadorganica'])
                        return JsonResponse({"result": "bad", "mensaje": "Error: Usuario se encuentra registrado en: " + usua.unidadorganica.__str__()})
                    usuarioevidencia = UsuarioConsultaEvidencia(userpermiso_id=int(request.POST['userpermiso']),
                                                        unidadorganica=f.cleaned_data['unidadorganica'],
                                                        tipousuario=1)
                    usuarioevidencia.save(request)
                    log(u'añadio  usuario con evidencia poa: %s' % usuarioevidencia.id, request, "add")
                    return JsonResponse({"result": False})

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})
            else:
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'edit':
            usuarioevidencia = UsuarioEvidencia.objects.get(pk=request.POST['id'])
            f = UsuarioEvidenciaForm(request.POST)
            if f.is_valid():
                try:
                    if UsuarioEvidencia.objects.filter(unidadorganica=f.cleaned_data['unidadorganica']).exists():
                        if int(f.cleaned_data['tipousuario']) == 2:
                            UsuarioEvidencia.objects.filter(unidadorganica=f.cleaned_data['unidadorganica']).update(tipousuario=1)
                    usuarioevidencia.unidadorganica = f.cleaned_data['unidadorganica']
                    usuarioevidencia.tipousuario = f.cleaned_data['tipousuario']
                    usuarioevidencia.save(request)
                    log(u'edito usuario con evidencia poa: %s' % usuarioevidencia.id, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})
            else:
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'delete':
            try:
                usuarioevidencia = UsuarioConsultaEvidencia.objects.get(pk=request.POST['id'])
                usuarioevidencia.status = False
                usuarioevidencia.save(request)
                log(u'cambio estado usuario con evidencia: %s' % usuarioevidencia.id, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'add':
                try:
                    data['title'] = u'Adicionar Usuario'
                    data['action'] = 'add'
                    form = UsuarioConsultaEvidenciaForm()
                    form.fields['userpermiso'].queryset = Persona.objects.none()
                    data['form'] = form
                    template = get_template('poa_usuarioconevidencia/add.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'buscar_usuario':
                try:
                    if 'q' in request.GET:
                        search = request.GET['q'].upper().strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            query = Persona.objects.filter(administrativo__isnull=False).filter(Q(nombres__icontains=search) |
                                                                                                Q(apellido1__icontains=search) |
                                                                                                Q(apellido2__icontains=search) |
                                                                                                Q(cedula__icontains=search) |
                                                                                                Q(pasaporte__icontains=search)).distinct()
                        elif len(ss) == 2:
                            query = Persona.objects.filter(Q(apellido1__icontains=ss[0]) | Q(apellido2__icontains=ss[1])).distinct()
                        elif len(ss) == 3:
                            query = Persona.objects.filter(Q(apellido1__icontains=ss[0]) | Q(apellido2__icontains=ss[1]) | Q(apellido2__icontains=ss[2])).distinct()
                        elif len(ss) == 4:
                            query = Persona.objects.filter(Q(apellido1__icontains=ss[0]) | Q(apellido2__icontains=ss[1]) | Q(apellido2__icontains=ss[2]) | Q(apellido2__icontains=ss[3])).distinct()
                    else:
                        query = Persona.objects.filter(Q(administrativo__isnull=False) | Q(profesor__isnull=False)).distinct()
                    data = {"results": [{"id": x.usuario_id, "name": x.nombre_completo_inverso()} for x in query]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": 'Error al obtener los datos.'})

            elif action == 'edit':
                try:
                    data['title'] = u'Modificar Usuario'
                    data['usuarioevidencia'] = usuarioevidencia = UsuarioEvidencia.objects.get(pk=request.GET['id'])
                    form = UsuarioEvidenciaForm(initial={'userpermiso': usuarioevidencia.userpermiso.persona_set.get().nombre_completo_inverso(),
                                                         'unidadorganica': usuarioevidencia.unidadorganica,
                                                         'tipousuario': usuarioevidencia.tipousuario})
                    form.editar()
                    data['form'] = form
                    return render(request, 'poa_usuarioevidencia/edit.html', data)
                except Exception as ex:
                    pass

            elif action == 'delete':
                try:
                    data['title'] = u'Eliminar Permiso'
                    data['usuarioevidencia'] = UsuarioConsultaEvidencia.objects.get(pk=request.GET['id'])
                    return render(request, 'poa_usuarioconevidencia/delete.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            search, url_vars = request.GET.get('s', ''), ''
            if 's' in request.GET:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                url_vars += "&s={}".format(search)
                if len(ss) == 1:
                    usuarioevidencia = UsuarioConsultaEvidencia.objects.filter(
                        Q(userpermiso__persona__nombres__icontains=search) |
                        Q(userpermiso__persona__apellido1__icontains=search) |
                        Q(userpermiso__persona__apellido2__icontains=search), status=True).order_by('unidadorganica')
                else:
                    usuarioevidencia = UsuarioConsultaEvidencia.objects.filter(
                        Q(userpermiso__persona__apellido1__icontains=ss[0]) &
                        Q(userpermiso__persona__apellido2__icontains=ss[1]), status=True).order_by('unidadorganica')
            else:
                usuarioevidencia = UsuarioConsultaEvidencia.objects.filter(status=True).order_by('unidadorganica')
                data['usuarioevidencia'] = usuarioevidencia
            paging = MiPaginador(usuarioevidencia, 25)
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
            data['usuarioevidencia'] = page.object_list
            data['url_vars'] = url_vars

            return render(request, "poa_usuarioconevidencia/view.html", data)
