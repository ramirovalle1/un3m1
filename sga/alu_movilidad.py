# -*- coding: latin-1 -*-
import os
from datetime import datetime, timedelta

import xlwt
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from xlwt import *
import random
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import get_template
from django.template import Context
from xlwt import easyxf, XFStyle

from decorators import secure_module, last_access
from sagest.models import DistributivoPersona, Aseguradora
from settings import DEFAULT_PASSWORD, SEXO_MASCULINO, EMPLEADORES_GRUPO_ID, MODELO_EVALUACION, EMAIL_DOMAIN, BASE_DIR
from sga.commonviews import adduserdata
from sga.forms import ConvenioEmpresaForm, TipoConvenioForm, TipoArchivoConvenioForm, ArchivoConvenioForm, \
    EmpleadorForm, EmpresaForm, MovilidadSolicitudForm, TiposSegurosForm, SeguroForm, AseguradoraForm
from sga.funciones import log, MiPaginador, generar_nombre, resetear_clave_empresa
from django.db.models import Q
from sga.models import ConvenioEmpresa, TipoConvenio, TipoArchivoConvenio, ArchivoConvenio, EmpresaEmpleadora, Persona, \
    Empleador, miinstitucion, ConvenioCarrera, Carrera, CUENTAS_CORREOS, MovilidadTipoSolicitud, MovilidadBaseLegal, \
    MovilidadTipoEstancia, Seguro, SeguroTipo
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt_alu
from django.forms import  model_to_dict

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']
        # *******************************  SEGURO ***********************************

        if action == 'addseguro':
            try:
                form = SeguroForm(request.POST, request.FILES)

                if form.is_valid():
                    if form.cleaned_data['fechainicio'] > form.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio es menor a fecha de fin."})

                    add = Seguro(asegurado=data['persona'],
                                 aseguradora=form.cleaned_data['aseguradora'],
                                 tipo=form.cleaned_data['tipo'],
                                 descripcion=form.cleaned_data['descripcion'],
                                 prima=form.cleaned_data['prima'],
                                 fechainicio=form.cleaned_data['fechainicio'],
                                 fechafin=form.cleaned_data['fechafin'])
                    add.save(request)

                    log(u'Adiciono un seguro: %s' % (add), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editseguro':
            try:
                form = SeguroForm(request.POST, request.FILES)

                if form.is_valid():
                    edit = Seguro.objects.get(pk=int(encrypt_alu(request.POST['id'])))

                    if form.cleaned_data['fechainicio'] > form.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio es menor a fecha de fin."})
                    # if form.cleaned_data['prima'] <= Decimal(0):

                    edit.aseguradora = form.cleaned_data['aseguradora']
                    edit.tipo = form.cleaned_data['tipo']
                    edit.descripcion = form.cleaned_data['descripcion']
                    edit.prima = form.cleaned_data['prima']
                    edit.fechainicio = form.cleaned_data['fechainicio']
                    edit.fechafin = form.cleaned_data['fechafin']

                    edit.save(request)

                    log(u'Edito seguro: %s' % (edit), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteseguro':
            try:
                delete_d = Seguro.objects.get(pk=int(encrypt_alu(request.POST['id'])))
                log(u'Eliminó un seguro: %s' % delete_d, request, "del")
                delete_d.status = False
                delete_d.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        # *******************************  TIPO  SEGURO ***********************************

        elif action == 'addtiposeguro':
            try:
                descripcion = (request.POST['descripcion'])
                add = SeguroTipo(nombre=descripcion)
                add.save(request)

                log(u'Adiciono un tipo de seguro: %s' % (add), request, "add")
                return JsonResponse({"result": "ok"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edittiposeguro':
            try:

                descripcion = (request.POST['descripcion'])
                edit = SeguroTipo.objects.get(pk=int(encrypt_alu(request.POST['id'])))
                edit.nombre = descripcion
                edit.save(request)

                log(u'Edito un tipo de seguro: %s' % (edit), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletetiposeguro':
            try:
                delete_d = SeguroTipo.objects.get(pk=int(encrypt_alu(request.POST['id'])))
                if Seguro.objects.filter(status=True,tipo_id=delete_d.id).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"El registro esta siendo utlizado, no podra eliminar."})
                log(u'Eliminó un tipo de seguro: %s' % delete_d, request, "del")
                delete_d.status = False
                delete_d.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        # *******************************  ASEGURADORA ***********************************

        elif action == 'addaseguradora':
            try:
                form = AseguradoraForm(request.POST, request.FILES)

                if form.is_valid():
                    add = Aseguradora(nombre=form.cleaned_data['nombre'])
                    add.save(request)

                    log(u'Adiciono una aseguradora: %s' % (add), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editaseguradora':
            try:
                form = AseguradoraForm(request.POST, request.FILES)

                if form.is_valid():
                    edit = Aseguradora.objects.get(pk=int(encrypt_alu(request.POST['id'])))
                    edit.nombre = form.cleaned_data['nombre']
                    edit.save(request)

                    log(u'Edito una aseguradora: %s' % (edit), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteaseguradora':
            try:
                delete_d = Aseguradora.objects.get(pk=int(encrypt_alu(request.POST['id'])))
                if Seguro.objects.filter(status=True,aseguradora_id=delete_d.id).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"El registro esta siendo utlizado, no podra eliminar."})
                log(u'Eliminó una aseguradora: %s' % delete_d, request, "del")
                delete_d.status = False
                delete_d.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return HttpResponseRedirect(request.path)

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            # *******************************  SEGURO ***********************************

            if action == 'seguros':
                try:
                    data['title'] = u'Listados De Seguros'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        seguro = Seguro.objects.filter(Q(status=True) & (Q(aseguradora__nombre__icontains=search) | Q(tipo__nombre__icontains=search) | Q(descripcion__icontains=search)))
                    elif 'ide' in request.GET:
                        ids = request.GET['ide']
                        seguro = Seguro.objects.filter(id=ids)
                    else:
                        seguro = Seguro.objects.filter(status=True).order_by('id')
                    paging = MiPaginador(seguro, 25)
                    p = 1
                    try:
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        page = paging.page(p)
                    except Exception as ex:
                        page = paging.page(p)
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['seguros'] = page.object_list
                    # data['clave'] = DEFAULT_PASSWORD
                    return render(request, "alu_movilidad/viewseguros.html", data)
                except Exception as ex:
                    pass

            elif action == 'addseguro':
                try:
                    data['title'] = u'Adicionar Seguro'
                    data['form'] = SeguroForm()
                    return render(request, "alu_movilidad/addseguro.html", data)
                except Exception as ex:
                    pass

            elif action == 'editseguro':
                try:
                    data['title'] = u'Editar Seguro'
                    data['seguro'] = seguro = Seguro.objects.get(id=int(encrypt_alu(request.GET['id'])))
                    data['form'] = SeguroForm(model_to_dict(seguro))
                    return render(request, "alu_movilidad/editseguro.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteseguro':
                try:
                    data['title'] = u'Eliminar Inquietud de Practica'
                    data['campo'] = Seguro.objects.get(pk=int(encrypt_alu(request.GET['id'])))
                    return render(request, "alu_movilidad/deleteseguro.html", data)
                except Exception as ex:
                    pass


            # ******************************* TIPO  SEGURO ***********************************

            elif action == 'tiposeguros':
                try:
                    data['title'] = u'Listados Tipos De Seguros'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        seguro = SeguroTipo.objects.filter(Q(status=True) & Q(nombre__icontains=search))
                    elif 'ide' in request.GET:
                        ids = request.GET['ide']
                        seguro = SeguroTipo.objects.filter(id=ids)
                    else:
                        seguro = SeguroTipo.objects.filter(status=True).order_by('id')
                    paging = MiPaginador(seguro, 25)
                    p = 1
                    try:
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        page = paging.page(p)
                    except Exception as ex:
                        page = paging.page(p)
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['tiposeguros'] = page.object_list
                    # data['clave'] = DEFAULT_PASSWORD
                    return render(request, "alu_movilidad/viewtiposeguros.html", data)
                except Exception as ex:
                    pass


            elif action == 'edittiposeguro':
                try:
                    data['title'] = u'Editar Tipo Seguro'
                    base = SeguroTipo.objects.get(id=int(encrypt_alu(request.GET['id'])))
                    data['nombre'] = base.nombre
                    return JsonResponse(
                        {"result": "ok", 'title': data['title'], 'nombre': data['nombre']})
                except Exception as ex:
                    pass

            elif action == 'deletetiposeguro':
                try:
                    data['title'] = u'Eliminar Inquietud de Practica'
                    data['campo'] = SeguroTipo.objects.get(pk=int(encrypt_alu(request.GET['id'])))
                    return render(request, "alu_movilidad/deletetiposeguro.html", data)
                except Exception as ex:
                    pass

            # ******************************* ASEGURADORAS ***********************************

            elif action == 'aseguradoras':
                try:
                    data['title'] = u'Listados De Aseguradoras'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        aseguradoras = Aseguradora.objects.filter(Q(status=True) & (Q(nombre__icontains=search)))
                    elif 'ide' in request.GET:
                        ids = request.GET['ide']
                        aseguradoras = Aseguradora.objects.filter(id=ids)
                    else:
                        aseguradoras = Aseguradora.objects.filter(status=True).order_by('id')
                    paging = MiPaginador(aseguradoras, 25)
                    p = 1
                    try:
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        page = paging.page(p)
                    except Exception as ex:
                        page = paging.page(p)
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['aseguradoras'] = page.object_list
                    # data['clave'] = DEFAULT_PASSWORD
                    return render(request, "alu_movilidad/viewaseguradoras.html", data)
                except Exception as ex:
                    pass

            elif action == 'addaseguradora':
                try:
                    data['title'] = u'Adicionar Aseguradora'
                    data['form'] = AseguradoraForm()
                    return render(request, "alu_movilidad/addaseguradora.html", data)
                except Exception as ex:
                    pass

            elif action == 'editaseguradora':
                try:
                    data['title'] = u'Editar Aseguradora'
                    data['aseguradora'] = aseguradora = Aseguradora.objects.get(id=int(encrypt_alu(request.GET['id'])))
                    data['form'] = AseguradoraForm(model_to_dict(aseguradora))
                    return render(request, "alu_movilidad/editaseguradora.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteaseguradora':
                try:
                    data['title'] = u'Eliminar Aseguradora'
                    data['campo'] = Aseguradora.objects.get(pk=int(encrypt_alu(request.GET['id'])))
                    return render(request, "alu_movilidad/deleteaseguradora.html", data)
                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u'Convenios institucionales'
            search = None
            ids = None
            fecha_actual = datetime.now().date()
            if 's' in request.GET:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                if 'buscar_por' in request.GET:
                    data['buscar_por']=buscar_por=request.GET['buscar_por']
                    if buscar_por == 'nombre_empresa':
                        convenio = ConvenioEmpresa.objects.filter(Q(empresaempleadora__nombre__icontains=search),Q(status=True),solicitud=True,fechafinalizacion__gt=fecha_actual)
                    elif buscar_por == 'otrotipodebusqueda':
                        pass
                elif len(ss) == 1:
                    convenio = ConvenioEmpresa.objects.filter(Q(empresaempleadora__nombre__icontains=search,solicitud=True), Q(status=True),fechafinalizacion__gt=fecha_actual).distinct()
                elif len(ss) == 2:
                    convenio = ConvenioEmpresa.objects.filter(Q(empresaempleadora__nombre__icontains=ss[0]), Q(empresaempleadora__nombre__icontains=ss[1]), Q(status=True),solicitud=True,fechafinalizacion__gt=fecha_actual).distinct()
                elif len(ss) == 3:
                    convenio = ConvenioEmpresa.objects.filter(Q(empresaempleadora__nombre__icontains=ss[0]), Q(empresaempleadora__nombre__icontains=ss[1]), Q(status=True),solicitud=True,fechafinalizacion__gt=fecha_actual).distinct()
                elif len(ss) == 4:
                    convenio = ConvenioEmpresa.objects.filter(Q(empresaempleadora__nombre__icontains=ss[0]), Q(empresaempleadora__nombre__icontains=ss[1]), Q(empresaempleadora__nombre__icontains=ss[3]),Q(status=True),solicitud=True,fechafinalizacion__gt=fecha_actual).distinct()
                else:
                    convenio = ConvenioEmpresa.objects.filter(Q(empresaempleadora__nombre__icontains=ss[0]), Q(empresaempleadora__nombre__icontains=ss[1]), Q(empresaempleadora__nombre__icontains=ss[3]), Q(empresaempleadora__nombre__icontains=ss[4]), Q(status=True),solicitud=True,fechafinalizacion__gt=fecha_actual).distinct()
            convenio = ConvenioEmpresa.objects.filter(status=True,solicitud=True,fechafinalizacion__gt=fecha_actual)
            filtro_vigencia = ""
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
            return render(request, "alu_movilidad/view.html", data)
