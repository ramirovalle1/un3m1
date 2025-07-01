# -*- coding: UTF-8 -*-
import random
import sys

import openpyxl
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
import xlwt
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import Context
from django.template.loader import get_template
from xlwt import *
from django.shortcuts import render, redirect
from decorators import secure_module
from sagest.forms import DepartamentoForm, IntegranteDepartamentoForm, ResponsableDepartamentoForm, \
    SeccionDepartamentoForm
from sagest.models import Departamento, SeccionDepartamento, OpcionSistema
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.templatetags.sga_extras import encrypt
from sga.funciones import MiPaginador, log, generar_nombre, remover_caracteres_especiales_unicode
from sga.models import Administrativo, Persona
from .models import *
from .forms import *
from django.db.models import Sum, Q, F, FloatField
from django.db.models.functions import Coalesce


@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    usuario = request.user
    if request.method == 'POST':
        res_json = []
        action = request.POST['action']

        if action == 'addperiodo':
            try:
                with transaction.atomic():
                    form = PeriodoPromocionDocenteForm(request.POST)
                    if form.is_valid():
                        filtro = PeriodoPromocionDocente(nombre=form.cleaned_data['nombre'],
                                                         fechainicio=form.cleaned_data['fechainicio'],
                                                         fechafin=form.cleaned_data['fechafin'])
                        filtro.save(request)
                        log(u'Adiciono Periodo de Promoción Docente: %s' % filtro, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'editperiodo':
            try:
                with transaction.atomic():
                    idcab = int(request.POST['id'])
                    filtro = PeriodoPromocionDocente.objects.get(pk=idcab)
                    form = PeriodoPromocionDocenteForm(request.POST)
                    if form.is_valid():
                        filtro.nombre = form.cleaned_data['nombre']
                        filtro.fechainicio = form.cleaned_data['fechainicio']
                        filtro.fechafin = form.cleaned_data['fechafin']
                        filtro.save(request)
                        log(u'Edito Periodo de Promoción Docente: %s' % filtro, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'deleteperiodo':
            try:
                with transaction.atomic():
                    instancia = PeriodoPromocionDocente.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Periodo de Promoción Docente: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addperiodo':
                try:
                    form = PeriodoPromocionDocenteForm(initial={'fechainicio': datetime.now().date(), 'fechafin': datetime.now().date()})
                    data['form2'] = form
                    template = get_template("adm_promociondocente/modal/formperiodo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editperiodo':
                try:
                    data['filtro'] = filtro = PeriodoPromocionDocente.objects.get(pk=int(request.GET['id']))
                    form = PeriodoPromocionDocenteForm(initial=model_to_dict(filtro))
                    data['form2'] = form
                    template = get_template("adm_promociondocente/modal/formperiodo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'configuraciones':
                try:
                    data['title'] = u'Configuraciones'
                    return render(request, "adm_promociondocente/configuraciones.html", data)
                except Exception as ex:
                    pass

        else:
            data['title'] = u'Promoción de Profesores'
            search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
            if search:
                filtro = filtro & Q(nombre__icontains=search)
                url_vars += '&s=' + search
                data['search'] = search
            listado = PeriodoPromocionDocente.objects.filter(filtro).order_by('-id')
            paging = MiPaginador(listado, 20)
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
            data["url_vars"] = url_vars
            data['listado'] = page.object_list
            data['totcount'] = listado.count()
            data['email_domain'] = EMAIL_DOMAIN
            data['existepromocion'] = PeriodoPromocionDocente.objects.filter(status=True, fechafin__gte=datetime.now().date()).exists()
            return render(request, 'adm_promociondocente/view.html', data)