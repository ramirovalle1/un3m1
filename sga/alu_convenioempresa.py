# -*- coding: latin-1 -*-
from datetime import datetime, timedelta

import xlwt
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from xlwt import *
import random
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.template import Context
from xlwt import easyxf, XFStyle

from decorators import secure_module, last_access
from sagest.models import DistributivoPersona
from settings import DEFAULT_PASSWORD, SEXO_MASCULINO, EMPLEADORES_GRUPO_ID, MODELO_EVALUACION, EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.forms import ConvenioEmpresaForm, TipoConvenioForm, TipoArchivoConvenioForm, ArchivoConvenioForm, EmpleadorForm, EmpresaForm
from sga.funciones import log, MiPaginador, generar_nombre, resetear_clave_empresa
from django.db.models import Q
from sga.models import ConvenioEmpresa, TipoConvenio, TipoArchivoConvenio, ArchivoConvenio, EmpresaEmpleadora, Persona, \
    Empleador, miinstitucion, ConvenioCarrera, Carrera
from sga.tasks import send_html_mail


@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        pass
    else:
        persona = request.session['persona']
        # if not DistributivoPersona.objects.filter(persona=persona):
        #     return HttpResponseRedirect('/?info=Ud. no tiene asignado un cargo.')
        data['title'] = u'Convenios institucionales'
        search = None
        ids = None
        #alu
        fecha_actual=datetime.now().date()
        if 's' in request.GET:
            search = request.GET['s'].strip()
            ss = search.split(' ')
            if len(ss) == 1:
                convenio = ConvenioEmpresa.objects.filter(Q(empresaempleadora__nombre__icontains=search), Q(status=True), fechafinalizacion__gte=fecha_actual).distinct()
            elif len(ss) == 2:
                convenio = ConvenioEmpresa.objects.filter(Q(empresaempleadora__nombre__icontains=ss[0]), Q(empresaempleadora__nombre__icontains=ss[1]), Q(status=True), fechafinalizacion__gte=fecha_actual).distinct()
            elif len(ss) == 3:
                convenio = ConvenioEmpresa.objects.filter(Q(empresaempleadora__nombre__icontains=ss[0]), Q(empresaempleadora__nombre__icontains=ss[1]), Q(status=True), fechafinalizacion__gte=fecha_actual).distinct()
            elif len(ss) == 4:
                convenio = ConvenioEmpresa.objects.filter(Q(empresaempleadora__nombre__icontains=ss[0]), Q(empresaempleadora__nombre__icontains=ss[1]), Q(empresaempleadora__nombre__icontains=ss[3]),Q(status=True), fechafinalizacion__gte=fecha_actual).distinct()
            else:
                convenio = ConvenioEmpresa.objects.filter(Q(empresaempleadora__nombre__icontains=ss[0]), Q(empresaempleadora__nombre__icontains=ss[1]), Q(empresaempleadora__nombre__icontains=ss[3]), Q(empresaempleadora__nombre__icontains=ss[4]), Q(status=True), fechafinalizacion__gte=fecha_actual).distinct()
        else:
            convenio = ConvenioEmpresa.objects.filter(status=True, fechafinalizacion__gte=fecha_actual)

        paging = MiPaginador(convenio, 20)
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
        data['convenioempresas'] = page.object_list

        return render(request, "adm_convenioempresa/view.html", data)