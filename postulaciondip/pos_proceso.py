# -*- coding: UTF-8 -*-
import datetime
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
from docutils.nodes import status
from xlwt import *
from django.shortcuts import render, redirect

from .models import Proceso
from decorators import secure_module
from pdip.models import PerfilPuestoDip
from sagest.models import Departamento, SeccionDepartamento, OpcionSistema, DenominacionPuesto
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.templatetags.sga_extras import encrypt
from sga.funciones import MiPaginador, log, generar_nombre, remover_caracteres_especiales_unicode
from .forms import ProcesoForm, PasosProcesoForm, MantenimientoNombreForm, RequisitoForm, RequisitoProcesoForm, ClasificacionACForm
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
                    form = MantenimientoNombreForm(request.POST)
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

        if action == 'addtipo':
            try:
                with transaction.atomic():
                    if TipoProceso.objects.filter(nombre=request.POST['nombre'], status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'Tipo de proceso ya existe.'}, safe=False)
                    form = MantenimientoNombreForm(request.POST)
                    if form.is_valid():
                        instance = TipoProceso(nombre=form.cleaned_data['nombre'])
                        instance.save(request)
                        log(u'Adiciono tipo de proceso: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'addrequisito':
            try:
                form = RequisitoForm(request.POST)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        if newfile.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf' or ext == '.PDF':
                                newfile._name = generar_nombre("archivopdip_", newfile._name)
                            else:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, Solo archivo con extención. pdf."})
                if form.is_valid():
                    requisito = Requisito(nombre=form.cleaned_data['nombre'],
                                          observacion=form.cleaned_data['observacion'],
                                          archivo=newfile,
                                          tipoarchivo=form.cleaned_data['tipoarchivo'])
                    if newfile:
                        requisito.archivo = newfile
                    requisito.save(request)
                    log(u'Adiciono nuevo requisito: %s' % requisito, request, "addrequisito")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addactividadeconomica':
            try:
                with transaction.atomic():
                    form = ClasificacionACForm(request.POST)
                    if form.is_valid():
                        clasificacion = ClasificacionAC(codigo=form.cleaned_data['codigo'],
                                                        descripcion=form.cleaned_data['descripcion'],
                                                        nivel=form.cleaned_data['nivel'],
                                                        activo=form.cleaned_data['activo'])

                        clasificacion.save(request)
                        log(u'Adiciono nuevo ClasificacionAC DIP: %s' % clasificacion, request, "addactividadeconomica")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        if action == 'addprocesorequisito':
            try:
                with transaction.atomic():
                    pr = RequisitosProceso.objects.filter(requisito_id=request.POST['nombre'], status=False)
                    if pr.exists():
                        pr.update(status=True)
                        log(u'Editó tipo de proceso: %s' % pr, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    form = RequisitoProcesoForm(request.POST)
                    if form.is_valid():
                        instance = RequisitosProceso(status=True, fecha_creacion=datetime.date, proceso_id=request.POST['id'], usuario_creacion_id=usuario.id, requisito_id=request.POST['nombre'])
                        instance.save(request)
                        log(u'Adiciono tipo de proceso: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'procesorequisito':

            try:
                with transaction.atomic():
                    if Requisito.objects.filter(id__in=request.POST.getlist('requisito'), status=True).exists():

                        instance = RequisitosProceso(status=True, fecha_creacion=datetime.date, proceso_id=request.POST['id'], usuario_creacion_id=usuario.id)
                        for r in request.POST.getlist('requisito'):
                            RequisitosProceso.objects.create(status=True, fecha_creacion=datetime.date, proceso_id=request.POST['id'], usuario_creacion_id=usuario.id, requisito_id=r)
                        # instance.save(request)
                        log(u'Adiciono tipo de proceso: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'editrequisito':
            try:
                with transaction.atomic():
                    filtro = Requisito.objects.get(pk=request.POST['id'])
                    f = RequisitoForm(request.POST, request.FILES)
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            if newfile.size > 10485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext == '.pdf' or ext == '.PDF':
                                    newfile._name = generar_nombre("archivopdip_", newfile._name)
                                else:
                                    return JsonResponse(
                                        {"result": "bad", "mensaje": u"Error, Solo archivo con extención. pdf."})
                    if f.is_valid():
                        filtro.nombre = f.cleaned_data['nombre']
                        filtro.observacion = f.cleaned_data['observacion']
                        filtro.tipoarchivo = f.cleaned_data['tipoarchivo']
                        if 'archivo' in request.FILES:
                            archivo = request.FILES['archivo']
                            filtro.archivo = archivo
                        filtro.save(request)

                        log(u'Edito requisito DIP: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'editactividadeconomica':
            try:
                with transaction.atomic():
                    filtro = ClasificacionAC.objects.get(pk=request.POST['id'])
                    f = ClasificacionACForm(request.POST)
                    if f.is_valid():
                        filtro.codigo = f.cleaned_data['codigo']
                        filtro.descripcion = f.cleaned_data['descripcion']
                        filtro.nivel = f.cleaned_data['nivel']
                        filtro.activo = f.cleaned_data['activo']
                        filtro.save(request)

                        log(u'Edito ClasificacionAC DIP: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'editperfil':
            try:
                with transaction.atomic():
                    filtro = PerfilPuestoDip.objects.get(pk=request.POST['id'])
                    f = MantenimientoNombreForm(request.POST)
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

        if action == 'edittipo':
            try:
                with transaction.atomic():
                    filtro = TipoProceso.objects.get(pk=request.POST['id'])
                    f = MantenimientoNombreForm(request.POST)
                    if f.is_valid():
                        filtro.nombre = f.cleaned_data['nombre']
                        filtro.save(request)
                        log(u'Edito Tipo proceso DIP: %s' % filtro, request, "edit")
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

        if action == 'deleterequisito':
            try:
                with transaction.atomic():
                    instancia = Requisito.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Requisito DIP: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'deleteactividadeconomica':
            try:
                with transaction.atomic():
                    instancia = ClasificacionAC.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino ClasificacionAC DIP: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'deleteprocesorequisito':
            try:
                with transaction.atomic():
                    instancia = RequisitosProceso.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Requisito DIP: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'deletetipo':
            try:
                with transaction.atomic():
                    instancia = TipoProceso.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó tipo proceso DIP: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'addproceso':
            try:
                with transaction.atomic():
                    if Proceso.objects.filter(nombre=request.POST['nombre'],version=request.POST['version'], status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'Proceso ya existe.'}, safe=False)
                    form = ProcesoForm(request.POST)
                    if form.is_valid():
                        instance = Proceso(
                            tipo=form.cleaned_data['tipo'],
                            version=form.cleaned_data['version'],
                            perfil=form.cleaned_data['perfil'],
                            nombre=form.cleaned_data['nombre'],
                            activo=form.cleaned_data['activo']
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
                    registro = Proceso.objects.get(pk=request.POST['id'])
                    f = ProcesoForm(request.POST)
                    if f.is_valid():
                        registro.version = f.cleaned_data['version']
                        registro.nombre = f.cleaned_data['nombre']
                        registro.perfil = f.cleaned_data['perfil']
                        registro.activo = f.cleaned_data['activo']
                        registro.tipo = f.cleaned_data['tipo']
                        registro.save(request)
                        log(u'Editó proceso DIP: %s' % registro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'delproceso':
            try:
                with transaction.atomic():
                    registro = Proceso.objects.get(pk=int(request.POST['id']))
                    registro.status = False
                    registro.save(request)
                    log(u'Eliminó proceso Pago DIP: %s' % registro, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'activoparapostu':
            try:
                with transaction.atomic():
                    registro = ClasificacionAC.objects.get(pk=int(encrypt(request.POST['id'])))
                    if registro.activo:
                        registro.activo = False
                    else:
                        registro.activo = True
                    registro.save(request)
                    log(u'Editó Clasificacion - Activo DIP: %s' % registro, request, "edit")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)


        if action == 'mostrarproceso':
            try:
                registro = Proceso.objects.get(pk=request.POST['id'])
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
                    proceso = Proceso.objects.get(pk=request.POST['id'])
                    if PasosProceso.objects.filter(numeropaso=request.POST['numeropaso'], status=True, proceso=proceso).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'Numero de Paso ya existe.'}, safe=False)
                    form = PasosProcesoForm(request.POST)
                    if form.is_valid():
                        instance = PasosProceso(pasoanterior = form.cleaned_data['pasoanterior'])
                        instance.numeropaso = form.cleaned_data['numeropaso']
                        instance.tiporevisor = form.cleaned_data['tiporevisor']
                        instance.proceso = proceso
                        instance.habilitacontrato = form.cleaned_data['habilitacontrato']
                        instance.genera_informe = form.cleaned_data['genera_informe']
                        instance.finaliza = form.cleaned_data['finaliza']
                        instance.beneficiario = form.cleaned_data['beneficiario']
                        instance.nombre = form.cleaned_data['nombre']
                        instance.estadovalida = form.cleaned_data['estadovalida']
                        instance.estadorechazado = form.cleaned_data['estadorechazado']
                        instance.valida = form.cleaned_data['valida']
                        instance.carga = form.cleaned_data['carga']
                        instance.tiempoalerta_carga = form.cleaned_data['tiempoalerta_carga']
                        instance.tiempoalerta_validacion = form.cleaned_data['tiempoalerta_validacion']
                        instance.carga_archivo = form.cleaned_data['carga_archivo']
                        instance.valida_archivo = form.cleaned_data['valida_archivo']
                        instance.leyenda = form.cleaned_data['leyenda']
                        instance.activo = form.cleaned_data['activo']
                        instance.save(request)

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
                    filtro = PasosProceso.objects.get(pk=request.POST['id'])
                    f = PasosProcesoForm(request.POST)
                    if f.is_valid():
                        filtro.nombre = f.cleaned_data['nombre']
                        filtro.activo = f.cleaned_data['activo']
                        # filtro.secuencia = f.cleaned_data['secuencia']
                        filtro.tiporevisor = f.cleaned_data['tiporevisor']
                        filtro.valida = f.cleaned_data['valida']
                        filtro.pasoanterior = f.cleaned_data['pasoanterior']
                        filtro.numeropaso = f.cleaned_data['numeropaso']
                        filtro.carga = f.cleaned_data['carga']
                        filtro.estadovalida = f.cleaned_data['estadovalida']
                        filtro.estadorechazado = f.cleaned_data['estadorechazado']
                        filtro.finaliza = f.cleaned_data['finaliza']
                        filtro.habilitacontrato = f.cleaned_data['habilitacontrato']
                        filtro.beneficiario = f.cleaned_data['beneficiario']
                        filtro.genera_informe = f.cleaned_data['genera_informe']
                        filtro.carga_archivo = f.cleaned_data['carga_archivo']
                        filtro.valida_archivo = f.cleaned_data['valida_archivo']
                        filtro.leyenda = f.cleaned_data['leyenda']
                        filtro.tiempoalerta_carga = f.cleaned_data['tiempoalerta_carga']
                        filtro.tiempoalerta_validacion = f.cleaned_data['tiempoalerta_validacion']
                        filtro.habilitacontrato = f.cleaned_data['habilitacontrato']
                        filtro.save(request)

                        log(u'Edito paso Pago DIP: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'deletepaso':
            try:
                with transaction.atomic():
                    instancia = PasosProceso.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Paso DIP: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:

        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'requisitosporproceso':
                try:
                    if Proceso.objects.filter(pk=int(encrypt(request.GET['id']))).values('id').exists():

                        search, url_vars = request.GET.get('s', ''), ''
                        # # if search:
                        # #     url_vars += '&s=' + search
                        # #     data['search'] = search
                        data['proceso'] = id_proceso = Proceso.objects.get(pk=int(encrypt(request.GET['id'])))
                        data['title'] = u'REQUISITOS DE %s' % (id_proceso.nombre)
                        filtro = Q(proceso_id=id_proceso, status=True, requisito__status=True)

                        if search:
                            search = request.GET['s']
                            filtro = filtro & (Q(requisito__nombre__icontains=search))
                            url_vars += "&s={}".format(search)


                        # data['requisitos'] = listado = RequisitosProceso.objects.select_related('requisito') \
                        #     .values('id', 'requisito__id', 'requisito__nombre') \
                        #     .filter(filtro) \
                        #     .order_by('requisito__nombre', '-id')

                        listado = RequisitosProceso.objects.filter(filtro).order_by('-id', 'requisito__nombre')
                        paging = MiPaginador(listado, 5)
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
                        data['page'] = page
                        data['url_vars'] = url_vars
                        data['rangospaging'] = paging.rangos_paginado(p)
                        # data['listado'] = page.object_list
                        # data['totcount'] = listado.count()
                        data['requisitos'] = page.object_list
                        data['search'] = search if search else ''

                        # data['email_domain'] = EMAIL_DOMAIN
                        return render(request, "adm_configuracionproceso/requisito.html", data)
                except Exception as ex:
                    return redirect('/pos_proceso')
                    # pass

            if action == 'configuraciones':
                try:
                    data['title'] = u'Configuraciones'
                    data['perfiles'] = PerfilPuestoDip.objects.filter(status=True).order_by('nombre')
                    data['tipos'] = TipoProceso.objects.filter(status=True).order_by('nombre')
                    data['listarequisito'] = Requisito.objects.filter(status=True).order_by('nombre')  #Especificar filtro
                    data['clasificacionac'] = ClasificacionAC.objects.filter(status=True).order_by('-id', 'codigo')
                    return render(request, "adm_configuracionproceso/configuraciones.html", data)
                except Exception as ex:
                    pass

            if action == 'pasos':
                try:
                    data['proceso'] = proceso = Proceso.objects.get(pk=int(request.GET['id']))
                    data['title'] = u'PASOS DE %s' % (proceso.nombre)
                    data['listado'] = listado = proceso.pasosproceso_set.filter(status=True).order_by('numeropaso')
                    return render(request, "adm_configuracionproceso/pasos.html", data)
                except Exception as ex:
                    pass

            if action == 'addpaso':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = proceso = Proceso.objects.get(pk=request.GET['id'])
                    form = PasosProcesoForm()
                    form.fields['pasoanterior'].queryset = PasosProceso.objects.filter(status=True, proceso=proceso).order_by('numeropaso')
                    data['form2'] = form
                    template = get_template("adm_configuracionproceso/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editpaso':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = PasosProceso.objects.get(pk=request.GET['id'])
                    form = PasosProcesoForm(initial=model_to_dict(filtro))
                    form.fields['pasoanterior'].queryset = PasosProceso.objects.filter(status=True, proceso=filtro.proceso).exclude(pk=filtro.pk).order_by('numeropaso')
                    data['form2'] = form
                    template = get_template("adm_configuracionproceso/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addperfil':
                try:
                    form = MantenimientoNombreForm()
                    data['form2'] = form
                    template = get_template("adm_configuracionproceso/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addtipo':
                try:
                    form = MantenimientoNombreForm()
                    data['form2'] = form
                    template = get_template("adm_configuracionproceso/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addrequisito':
                try:
                    form = RequisitoForm()
                    data['form2'] = form
                    template = get_template("adm_configuracionproceso/modal/formrequisitos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addactividadeconomica':
                try:
                    form = ClasificacionACForm()
                    data['form2'] = form
                    template = get_template("adm_configuracionproceso/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addprocesorequisito':
                try:
                    form = RequisitoProcesoForm()
                    if RequisitosProceso.objects.filter(status=True, proceso_id=request.GET['id'], requisito__status=True).exists():
                        filterList = RequisitosProceso.objects.filter(status=True, proceso_id=request.GET['id'], requisito__status=True).values_list('requisito_id')
                        form.fields['nombre'].queryset = Requisito.objects.filter(status=True).exclude(pk__in=filterList).order_by('nombre')
                    data['form2'] = form
                    data['filtro'] = Proceso.objects.get(status=True, pk=int(request.GET['id']))
                    template = get_template("adm_configuracionproceso/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editrequisito':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = Requisito.objects.get(status=True, pk=int(encrypt(request.GET['id'])))
                    form = RequisitoForm(initial=model_to_dict(filtro))
                    data['form2'] = form
                    template = get_template("adm_configuracionproceso/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editactividadeconomica':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ClasificacionAC.objects.get(status=True, pk=int(encrypt(request.GET['id'])))
                    form = ClasificacionACForm(initial=model_to_dict(filtro))
                    data['form2'] = form
                    template = get_template("adm_configuracionproceso/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editperfil':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = PerfilPuestoDip.objects.get(pk=request.GET['id'])
                    form = MantenimientoNombreForm(initial=model_to_dict(filtro))
                    data['form2'] = form
                    template = get_template("adm_configuracionproceso/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'edittipo':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = TipoProceso.objects.get(pk=request.GET['id'])
                    form = MantenimientoNombreForm(initial=model_to_dict(filtro))
                    data['form2'] = form
                    template = get_template("adm_configuracionproceso/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addproceso':
                try:
                    form = ProcesoForm()
                    data['form2'] = form
                    template = get_template("adm_configuracionproceso/modal/formmodalp.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editproceso':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = Proceso.objects.get(pk=request.GET['id'])
                    form = ProcesoForm(initial=model_to_dict(filtro))
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
            data['title'] = u'Configuración del Proceso'
            search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
            if search:
                filtro = filtro & Q(nombre__icontains=search)
                url_vars += '&s=' + search
                data['search'] = search
            listado = Proceso.objects.filter(filtro).order_by('-id')
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
            data['listado'] = page.object_list
            data['totcount'] = listado.count()
            data['email_domain'] = EMAIL_DOMAIN
            return render(request, 'adm_configuracionproceso/view.html', data)