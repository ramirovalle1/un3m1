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
from sagest.models import Departamento, SeccionDepartamento, OpcionSistema
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.templatetags.sga_extras import encrypt
from .forms import PerfilPuestoDipForm, RequisitoPagoDipForm, ProcesoPagoForm, PasoProcesoPagoForm
from sga.funciones import MiPaginador, log, generar_nombre, remover_caracteres_especiales_unicode
from sga.models import Administrativo, Persona
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

        if action == 'addperfil':
            try:
                with transaction.atomic():
                    if PerfilPuestoDip.objects.filter(nombre=request.POST['nombre'], status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'Perfil Puesto ya existe.'}, safe=False)
                    form = PerfilPuestoDipForm(request.POST)
                    if form.is_valid():
                        instance = PerfilPuestoDip(nombre=form.cleaned_data['nombre'])
                        instance.save(request)
                        log(u'Adiciono Perfil Puesto: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'editperfil':
            try:
                with transaction.atomic():
                    filtro = PerfilPuestoDip.objects.get(pk=request.POST['id'])
                    f = PerfilPuestoDipForm(request.POST)
                    if f.is_valid():
                        filtro.nombre = f.cleaned_data['nombre']
                        filtro.save(request)
                        log(u'Edito Perfil Puesto DIP: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'deleteperfil':
            try:
                with transaction.atomic():
                    instancia = PerfilPuestoDip.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Perfil Puesto DIP: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'addrequisito':
            try:
                with transaction.atomic():
                    if RequisitoPagoDip.objects.filter(nombre=request.POST['nombre'], status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'Requisito ya existe.'}, safe=False)
                    form = RequisitoPagoDipForm(request.POST)
                    if form.is_valid():
                        instance = RequisitoPagoDip(nombre=form.cleaned_data['nombre'],
                                                    leyenda=form.cleaned_data['leyenda'])
                        instance.save(request)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre(instance.nombre_input(), newfile._name)
                            instance.archivo = newfile
                        instance.save(request)
                        log(u'Adiciono Requisito Pago DIP: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'editrequisito':
            try:
                with transaction.atomic():
                    filtro = RequisitoPagoDip.objects.get(pk=request.POST['id'])
                    f = RequisitoPagoDipForm(request.POST)
                    if f.is_valid():
                        filtro.nombre = f.cleaned_data['nombre']
                        filtro.leyenda = f.cleaned_data['leyenda']
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre(filtro.nombre_input(), newfile._name)
                            filtro.archivo = newfile
                        filtro.save(request)
                        log(u'Edito Requisito Pago DIP: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'deleterequisito':
            try:
                with transaction.atomic():
                    instancia = RequisitoPagoDip.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Requisito Pago DIP: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'addproceso':
            try:
                with transaction.atomic():
                    if ProcesoPago.objects.filter(nombre=request.POST['nombre'],version=request.POST['version'], status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'Proceso ya existe.'}, safe=False)
                    form = ProcesoPagoForm(request.POST)
                    if form.is_valid():
                        instance = ProcesoPago(
                            version=form.cleaned_data['version'],
                            perfil=form.cleaned_data['perfil'],
                            nombre=form.cleaned_data['nombre'],
                            descripcion=form.cleaned_data['descripcion'],
                            mostrar=form.cleaned_data['mostrar'],
                                               )
                        instance.save(request)
                        log(u'Adicionó Proceso para Pago DIP: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'editproceso':
            try:
                with transaction.atomic():
                    registro = ProcesoPago.objects.get(pk=request.POST['id'])
                    f = ProcesoPagoForm(request.POST)
                    if f.is_valid():
                        registro.version = f.cleaned_data['version']
                        registro.nombre = f.cleaned_data['nombre']
                        registro.perfil = f.cleaned_data['perfil']
                        registro.descripcion = f.cleaned_data['descripcion']
                        registro.mostrar = f.cleaned_data['mostrar']
                        registro.save(request)
                        log(u'Editó proceso de Pago DIP: %s' % registro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'delproceso':
            try:
                with transaction.atomic():
                    registro = ProcesoPago.objects.get(pk=int(request.POST['id']))
                    registro.status = False
                    registro.save(request)
                    log(u'Eliminó proceso Pago DIP: %s' % registro, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'mostrarproceso':
            try:
                registro = ProcesoPago.objects.get(pk=request.POST['id'])
                registro.mostrar = True if request.POST['val'] == 'y' else  False
                registro.save(request)
                log(u'Visualiza Proceso DIP : %s (%s)' % (registro, registro.mostrar),
                    request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        if action == 'addpaso':
            try:
                with transaction.atomic():
                    proceso = ProcesoPago.objects.get(pk=request.POST['id'])
                    if PasoProcesoPago.objects.filter(numeropaso=request.POST['numeropaso'], status=True, proceso=proceso).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'Numero de Paso ya existe.'}, safe=False)
                    form = PasoProcesoPagoForm(request.POST)
                    if form.is_valid():
                        instance = PasoProcesoPago(pasoanterior = form.cleaned_data['pasoanterior'])
                        instance.numeropaso = form.cleaned_data['numeropaso']
                        instance.proceso = proceso
                        instance.genera_informe = form.cleaned_data['genera_informe']
                        instance.finaliza = form.cleaned_data['finaliza']
                        instance.beneficiario = form.cleaned_data['beneficiario']
                        instance.descripcion = form.cleaned_data['descripcion']
                        instance.estadovalida = form.cleaned_data['estadovalida']
                        instance.estadorechazado = form.cleaned_data['estadorechazado']
                        instance.valida = form.cleaned_data['valida']
                        instance.carga = form.cleaned_data['carga']
                        instance.tiempoalerta_carga = form.cleaned_data['tiempoalerta_carga']
                        instance.tiempoalerta_validacion = form.cleaned_data['tiempoalerta_validacion']
                        instance.carga_archivo = form.cleaned_data['carga_archivo']
                        instance.valida_archivo = form.cleaned_data['valida_archivo']
                        instance.leyenda = form.cleaned_data['leyenda']
                        instance.save(request)
                        requisitos = form.cleaned_data['requisitos']
                        for req in requisitos:
                            requisito = RequisitoPasoPago(paso=instance, requisito=req)
                            requisito.save(request)
                        log(u'Adicionó Paso para Pago DIP: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'editpaso':
            try:
                with transaction.atomic():
                    filtro = PasoProcesoPago.objects.get(pk=request.POST['id'])
                    f = PasoProcesoPagoForm(request.POST)
                    if f.is_valid():
                        filtro.pasoanterior = f.cleaned_data['pasoanterior']
                        filtro.numeropaso = f.cleaned_data['numeropaso']
                        filtro.finaliza = f.cleaned_data['finaliza']
                        filtro.beneficiario = f.cleaned_data['beneficiario']
                        filtro.genera_informe = f.cleaned_data['genera_informe']
                        filtro.descripcion = f.cleaned_data['descripcion']
                        filtro.estadovalida = f.cleaned_data['estadovalida']
                        filtro.estadorechazado = f.cleaned_data['estadorechazado']
                        filtro.valida = f.cleaned_data['valida']
                        filtro.carga = f.cleaned_data['carga']
                        filtro.tiempoalerta_carga = f.cleaned_data['tiempoalerta_carga']
                        filtro.tiempoalerta_validacion = f.cleaned_data['tiempoalerta_validacion']
                        filtro.leyenda = f.cleaned_data['leyenda']
                        filtro.carga_archivo = f.cleaned_data['carga_archivo']
                        filtro.valida_archivo = f.cleaned_data['valida_archivo']
                        filtro.save(request)
                        requisitos = f.cleaned_data['requisitos']
                        for req in RequisitoPasoPago.objects.filter(status=True, paso=filtro).exclude(requisito__in=requisitos.values_list('pk', flat=True)):
                            req.status = False
                            req.save(request)
                        for req in requisitos:
                            if not RequisitoPasoPago.objects.filter(status=True, paso=filtro, requisito__id=req.pk).exists():
                                requisito = RequisitoPasoPago(paso=filtro, requisito=req)
                                requisito.save(request)
                        log(u'Edito Requisito Pago DIP: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'deletepaso':
            try:
                with transaction.atomic():
                    instancia = PasoProcesoPago.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Paso Pago DIP: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'configuraciones':
                try:
                    data['title'] = u'Configuraciones'
                    data['perfiles'] = PerfilPuestoDip.objects.filter(status=True).order_by('nombre')
                    data['requisitos'] = RequisitoPagoDip.objects.filter(status=True).order_by('nombre')
                    return render(request, "adm_configuracionproceso/configuraciones.html", data)
                except Exception as ex:
                    pass

            if action == 'pasos':
                try:
                    data['proceso'] = proceso = ProcesoPago.objects.get(pk=int(request.GET['id']))
                    data['title'] = u'PASOS DE %s' % (proceso.nombre)
                    data['listado'] = listado = proceso.pasoprocesopago_set.filter(status=True).order_by('numeropaso')
                    return render(request, "adm_configuracionproceso/pasos.html", data)
                except Exception as ex:
                    pass

            if action == 'verrequisitos':
                try:
                    data['proceso'] = proceso = PasoProcesoPago.objects.get(pk=request.GET['id'])
                    template = get_template("adm_configuracionproceso/modal/verrequisitos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addpaso':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = proceso = ProcesoPago.objects.get(pk=request.GET['id'])
                    form = PasoProcesoPagoForm()
                    form.fields['pasoanterior'].queryset = PasoProcesoPago.objects.filter(status=True, proceso=proceso).order_by('numeropaso')
                    data['form2'] = form
                    template = get_template("adm_configuracionproceso/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editpaso':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = PasoProcesoPago.objects.get(pk=request.GET['id'])
                    form = PasoProcesoPagoForm(initial=model_to_dict(filtro))
                    form.fields['requisitos'].initial = RequisitoPagoDip.objects.filter(status=True, pk__in=filtro.requisitos().values_list('requisito__id', flat=True)).order_by('nombre')
                    form.fields['pasoanterior'].queryset = PasoProcesoPago.objects.filter(status=True, proceso=filtro.proceso).exclude(pk=filtro.pk).order_by('numeropaso')
                    data['form2'] = form
                    template = get_template("adm_configuracionproceso/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            if action == 'addperfil':
                try:
                    form = PerfilPuestoDipForm()
                    data['form2'] = form
                    template = get_template("adm_configuracionproceso/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editperfil':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = PerfilPuestoDip.objects.get(pk=request.GET['id'])
                    form = PerfilPuestoDipForm(initial=model_to_dict(filtro))
                    data['form2'] = form
                    template = get_template("adm_configuracionproceso/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addrequisito':
                try:
                    data['form2'] = form= RequisitoPagoDipForm()
                    template = get_template("adm_configuracionproceso/modal/formrequisitos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editrequisito':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = RequisitoPagoDip.objects.get(pk=request.GET['id'])
                    form = RequisitoPagoDipForm(initial=model_to_dict(filtro))
                    data['form2'] = form
                    template = get_template("adm_configuracionproceso/modal/formrequisitos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addproceso':
                try:
                    form = ProcesoPagoForm()
                    data['form2'] = form
                    template = get_template("adm_configuracionproceso/modal/formmodalp.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            if action == 'editproceso':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ProcesoPago.objects.get(pk=request.GET['id'])
                    form = ProcesoPagoForm(initial=model_to_dict(filtro))
                    data['form2'] = form
                    template = get_template("adm_configuracionproceso/modal/formmodalp.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'buscardenominacion':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    query = DenominacionPuesto.objects.filter(status=True)
                    if len(s) == 1:
                        per = query.filter((Q(nombre__icontains=q))).distinct()[:15]
                    elif len(s) == 2:
                        per = query.filter((Q(nombre__icontains=s[0]) & Q(nombre__icontains=s[1])) ).distinct()[:15]

                    data = {"result": "ok",
                            "results": [{"id": x.id, "name": str(x.nombre)}
                                        for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass



        else:
            data['title'] = u'Configuración del Proceso Pago'
            search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
            if search:
                filtro = filtro & Q(nombre__icontains=search)
                url_vars += '&s=' + search
                data['search'] = search
            listado = ProcesoPago.objects.filter(filtro).order_by('-id')
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
            return render(request, 'adm_configuracionproceso/view.html', data)
