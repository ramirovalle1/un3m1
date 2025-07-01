# -*- coding: latin-1 -*-
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador
from sga.models import Periodo


def rango_anios():
    if Periodo.objects.exists():
        inicio = datetime.now().year
        fin = Periodo.objects.order_by('inicio')[0].inicio.year
        return range(inicio, fin - 1, -1)
    return [datetime.now().date().year]

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    if request.method == 'POST':
        action = request.POST['action']


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data = {}
        adduserdata(request, data)
        if 'action' in request.GET:
            action = request.GET['action']

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Periodos lectivos de la institución'

            data['anios'] = anios = rango_anios()
            if 'anio' in request.GET:
                request.session['anio'] = int(request.GET['anio'])
            else:
                request.session['anio'] = anios[0]
            data['anioselect'] = anioselect = request.session['anio']

            # search = None
            # ids = None
            # if 's' in request.GET:
            #     search = request.GET['s']
            #     periodos = Periodo.objects.filter(Q(nombre__icontains=search) |
            #                                       Q(tipo__nombre__icontains=search)).distinct().order_by("-inicio")
            # elif 'id' in request.GET:
            #     ids = request.GET['id']
            #     periodos = Periodo.objects.filter(id=ids).order_by("-inicio")
            # else:
            #     periodos = Periodo.objects.all().order_by("-inicio")
            periodos = Periodo.objects.filter(inicio__year=anioselect).order_by("-inicio")
            paging = MiPaginador(periodos, 25)
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
            # data['search'] = search if search else ""
            # data['ids'] = ids if ids else ""
            data['periodos'] = page.object_list
            return render(request, "adm_periodos_rubros/view.html", data)