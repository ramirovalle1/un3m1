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
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.templatetags.sga_extras import encrypt
from .forms import CertificacionPresupuestariaDipForm
from sga.funciones import MiPaginador, log, generar_nombre, remover_caracteres_especiales_unicode
from sga.models import Administrativo, Persona, ProfesorMateria
from .models import *
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

        if action == 'addcertificacion':
            try:
                f = CertificacionPresupuestariaDipForm(request.POST)
                if f.is_valid():
                    filtro = CertificacionPresupuestariaDip(partida=f.cleaned_data['partida'],
                                     descripcion=f.cleaned_data['descripcion'],
                                     codigo=f.cleaned_data['codigo'],
                                     valor=f.cleaned_data['valor'],
                                     fecha=f.cleaned_data['fecha'],
                                     saldo=f.cleaned_data['valor'])
                    filtro.save(request)

                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        extension = newfile._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if newfile.size > 100194304:
                            transaction.set_rollback(True)
                            return JsonResponse(
                                {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                        if not exte in ['png','pdf','jpg','jpeg','j']:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .doc, docx"})
                        newfile._name = generar_nombre("certificacionepunemi", newfile._name)
                        filtro.archivo = newfile
                        filtro.save(request)
                    log(u'Adicionó certificacion dip: %s' % filtro, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Datos erróneos, intente nuevamente."}, safe=False)

        if action == 'editcertificacion':
            try:
                f = CertificacionPresupuestariaDipForm(request.POST)
                if f.is_valid():
                    filtro = CertificacionPresupuestariaDip.objects.get(pk=int(request.POST['id']))
                    filtro.valor= f.cleaned_data['valor']
                    filtro.descripcion= f.cleaned_data['descripcion']
                    filtro.fecha= f.cleaned_data['fecha']
                    filtro.partida= f.cleaned_data['partida']
                    filtro.codigo= f.cleaned_data['codigo']
                    if 'archivo' in request.FILES:
                        filtro.archivo.delete()
                        newfile = request.FILES['archivo']
                        extension = newfile._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if newfile.size > 100194304:
                            transaction.set_rollback(True)
                            return JsonResponse(
                                {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                        if not exte in ['doc','docx']:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .doc, docx"})
                        newfile._name = generar_nombre("certificacionepunemi", newfile._name)
                        filtro.archivo=newfile
                    filtro.save(request)
                    log(u'Editó certificacion de contrato dip: %s' % filtro, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Datos erróneos, intente nuevamente."}, safe=False)
        if action == 'deletecertificacion':
            try:
                id = request.POST['id']
                filtro = CertificacionPresupuestariaDip.objects.get(pk=int(id))
                if not filtro.esta_en_contrato():
                    filtro.status = False
                    filtro.save(request)
                    log(u'Eliminó certificacion de contrato dip: %s' % filtro, request, "del")
                    return JsonResponse({"result": False, "mensaje": u"Certificacion eliminada correctamnete!"})
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error, esta certificaion esta en un contrato"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Datos erróneos, intente nuevamente."}, safe=False)



        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addcertificacion':
                try:
                    data['form2'] = CertificacionPresupuestariaDipForm()
                    template = get_template("adm_certificacion/modal/formcertificacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editcertificacion':
                try:
                    data['filtro'] = filtro =  CertificacionPresupuestariaDip.objects.get(pk=int(request.GET['id']))
                    data['form2'] = CertificacionPresupuestariaDipForm(initial=model_to_dict(filtro))
                    template = get_template("adm_certificacion/modal/formcertificacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'detallecertificacion':
                data['detalle'] = detalle = CertificacionPresupuestariaDip.objects.get(pk=int(request.GET['id'])).detalles_certificacion()
                template = get_template("adm_certificacion/modal/detallecertificacion.html")
                return JsonResponse({"result": True, 'data': template.render(data)})



            if action == 'buscarpersonas':
                try:
                    id = request.GET['id']
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    querybase = Persona.objects.filter(status=True)
                    if len(s) == 1:
                        per = querybase.filter((Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(cedula__icontains=q) |  Q(apellido2__icontains=q) | Q(cedula__contains=q)), Q(status=True)).distinct()[:15]
                    elif len(s) == 2:
                        per = querybase.filter((Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) |
                                                       (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1])) |
                                                       (Q(nombres__icontains=s[0]) & Q(apellido1__contains=s[1]))).filter(status=True).distinct()[:15]
                    else:
                        per = querybase.filter((Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(apellido2__contains=s[2])) |
                                                       (Q(nombres__contains=s[0]) & Q(nombres__contains=s[1]) & Q(apellido1__contains=s[2]))).filter(status=True).distinct()[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {}".format(x.cedula, x.nombre_completo())} for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

        else:
            data['title'] = u'CERTIFICACIÓN PRESUPUESTARIA EPUNEMI'
            search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
            if search:
                filtro = filtro & Q(descripcion__icontains=search) | Q(codigo__icontains=search) | Q(partida__icontains=search)
                url_vars += '&s=' + search
                data['search'] = search
            listado = CertificacionPresupuestariaDip.objects.filter(filtro).order_by('-id')
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
            return render(request, 'adm_certificacion/view.html', data)