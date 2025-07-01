# -*- coding: UTF-8 -*-
import random

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
import xlwt
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from xlwt import *
from django.shortcuts import render
from decorators import secure_module, last_access
from sagest.models import ArchivoDescarga
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    usuario = request.user
    perfilprincipal = request.session['perfilprincipal']
    if request.method == 'POST':
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Lista de enlaces a programas'
        url_vars = ''
        filtro = Q(status=True)
        search = None
        ids = None

        if 's' in request.GET:
            if request.GET['s'] != '':
                search = request.GET['s']

        if search:
            filtro = filtro & (Q(nombreprograma__icontains=search))
            url_vars += '&s=' + search

        if perfilprincipal.es_estudiante():
            procesos = ArchivoDescarga.objects.filter(filtro & Q(estado=True) & Q(estadoacceso=2)).order_by('id')
        else:
            procesos = ArchivoDescarga.objects.filter(filtro & Q(estado=True)).order_by('id')
        paging = MiPaginador(procesos, 20)
        p = 1
        try:
            paginasesion = 1
            if 'paginador' in request.session:
                paginasesion = int(request.session['paginador'])
            if 'page' in request.GET:
                p = int(request.GET['page'])
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
        data["url_vars"] = url_vars
        data['ids'] = ids if ids else ""
        data['proceso'] = page.object_list
        data['email_domain'] = EMAIL_DOMAIN
        return render(request, 'adm_verarchivodescarga/view.html', data)