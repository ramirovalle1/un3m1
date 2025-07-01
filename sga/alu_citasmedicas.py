# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.shortcuts import render
from decorators import secure_module, last_access
from med.models import ProximaCita
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['title'] = u'Mis Citas Medicas'
    search = None
    ids = None
    persona = data['persona']
    if 's' in request.GET:
        search = request.GET['s']
        ss = search.split(' ')
        while '' in ss:
            ss.remove('')
        if len(ss) == 1:
            proxima_cita = ProximaCita.objects.filter(Q(tipoconsulta__icontains=search) |
                                                      Q(persona__nombres__icontains=search) |
                                                      Q(persona__apellido1__icontains=search) |
                                                      Q(persona__apellido2__icontains=search) |
                                                      Q(persona__cedula__icontains=search), medico=persona).distinct()
        else:
            proxima_cita = ProximaCita.objects.filter(Q(persona__apellido1__icontains=ss[0]) &
                                                      Q(persona__apellido2__icontains=ss[1]), medico=persona).distinct()
    elif 'id' in request.GET:
        ids = request.GET['id']
        proxima_cita = ProximaCita.objects.filter(id=ids, medico=persona)
    else:
        proxima_cita = ProximaCita.objects.filter(persona=persona)
    paging = MiPaginador(proxima_cita, 25)
    p = 1
    try:
        if 'page' in request.GET:
            p = int(request.GET['page'])
        page = paging.page(p)
    except Exception as ex:
        p = 1
        page = paging.page(p)
    data['paging'] = paging
    data['rangospaging'] = paging.rangos_paginado(p)
    data['page'] = page
    data['search'] = search if search else ""
    data['ids'] = ids if ids else ""
    data['proxima_cita'] = page.object_list
    return render(request, "alu_citasmedicas/view.html", data)