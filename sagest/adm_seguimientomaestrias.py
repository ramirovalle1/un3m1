# -*- coding: UTF-8 -*-
import json
import random
import sys
from datetime import datetime
from decimal import Decimal

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

from balcon.forms import SolicitudBalconEditForm
from decorators import secure_module, last_access
from sagest.forms import DepartamentoForm, IntegranteDepartamentoForm, ResponsableDepartamentoForm, \
    SeccionDepartamentoForm, SeguimientoHistorialForm, SeguimientoInscripcionForm
from sagest.models import Departamento, SeccionDepartamento, TipoOtroRubro, ESTADOS_SOLICITUD_PRODUCTOS, Producto, \
    InventarioReal, DistributivoPersona, SolicitudObservacionesProductos, SalidaProducto, DetalleSalidaProducto
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from .commonviews import secuencia_bodega
from .forms import SolicitudProductoForm
from sga.funciones import MiPaginador, log, generar_nombre, puede_realizar_accion, null_to_decimal, \
    puede_realizar_accion_afirmativo, generar_codigo
from sga.models import Administrativo, Persona
from .models import SolicitudProductos, SolicitudDetalleProductos
from posgrado.models import InteresadoProgramaMaestria, HistorialInteresadoProgramaMaestria, HISTORIAL_CHOICES, \
    MaestriasAdmision


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']

    data['title'] = u'Seguimiento Interesados Maestria'
    if request.method == 'POST':

        action = request.POST['action']

        if action == 'cargarExcelInteresados':
            try:
                with transaction.atomic():
                    count = 0
                    counter = 0
                    linea = 1
                    excel = request.FILES['excel']
                    wb = openpyxl.load_workbook(excel)
                    worksheet = wb.worksheets[0]
                    for row in worksheet.iter_rows():
                        currentValues = [str(cell.value) for cell in row]
                        programa = None
                        if linea >= 2:
                            if currentValues[2] == 'None':
                                messages.error(request, 'REVISAR LINEA [{}],  FORMATO FILAS SIN NOMBRE DE ALUMNO, VERIFIQUE QUE EL ARCHIVO NO TENGA COLUMNAS VACIAS AL FINAL.'.format(linea))
                                transaction.set_rollback(True)
                                return redirect(request.path)
                            if currentValues[6] == 'None':
                                messages.error(request, 'REVISAR LINEA [{}],  FORMATO FILAS SIN CODIGO DE PROGRAMA, VERIFIQUE QUE EL ARCHIVO NO TENGA COLUMNAS VACIAS AL FINAL.'.format(linea))
                                transaction.set_rollback(True)
                                return redirect(request.path)
                            else:
                                if MaestriasAdmision.objects.filter(pk=int(currentValues[6])).exists():
                                    programa = MaestriasAdmision.objects.filter(pk=int(currentValues[6])).first()
                                else:
                                    messages.error(request, 'REVISAR LINEA [{}],  CODIGO DE PROGRAMA NO EXISTE.'.format(linea))
                                    transaction.set_rollback(True)
                                    return redirect(request.path)
                            if InteresadoProgramaMaestria.objects.filter(status=True, nombres__icontains=currentValues[2], programa_id=int(currentValues[6])).exists():
                                count += 1
                                car = InteresadoProgramaMaestria.objects.filter(status=True, nombres__icontains=currentValues[2], programa_id=int(currentValues[6])).first()
                                car.correo = currentValues[3] if currentValues[3] else ''
                                car.telefono = currentValues[4] if currentValues[4] else ''
                                car.telefono_adicional = currentValues[5] if currentValues[5] else ''
                                car.observacion = currentValues[0] if currentValues[0] else ''
                                car.save(request)
                                log(u'Edito Seguimiento Graduado: %s' % car, request, "change")
                            else:
                                cedula = currentValues[1] if currentValues[1] else ''
                                nombres = currentValues[2] if currentValues[2] else ''
                                email = currentValues[3] if currentValues[3] else ''
                                telefono = currentValues[4] if currentValues[4] else ''
                                telefono_adicional = currentValues[5] if currentValues[5] else ''
                                observacion = currentValues[0] if currentValues[0] else ''
                                car = InteresadoProgramaMaestria(nombres=nombres,
                                                                 correo=email,
                                                                 telefono=telefono,
                                                                 telefono_adicional=telefono_adicional,
                                                                 cedula=cedula,
                                                                 observacion=observacion,
                                                                 programa=programa)
                                car.save(request)
                                log(u'Adiciono Seguimiento Graduado: %s' % car, request, "add")
                                counter += 1
                        linea += 1
                    if count > 0:
                        messages.info(request, 'Se actualizaron {} registros ya existentes.'.format(str(count)))
                    if counter > 0:
                        messages.success(request, 'Se agregaron {} universidades'.format(counter))
            except Exception as ex:
                transaction.set_rollback(True)
                print(ex)
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                messages.error(request, ex)
                messages.error(request, 'Acaba de ocurrir un error al intertar cargar la linea {}, Acción fue cancelada.'.format(linea))
            return redirect('{}'.format(request.path))

        if action == 'addobservacion':
            try:
                with transaction.atomic():
                    filtro = InteresadoProgramaMaestria.objects.get(pk=int(request.POST['id']))
                    form = SeguimientoHistorialForm(request.POST)
                    if form.is_valid():
                        filtro.accion = form.cleaned_data['accion']
                        filtro.save()
                        soli = HistorialInteresadoProgramaMaestria(cab=filtro,
                                                                   detalle=form.cleaned_data['detalle'].upper(),
                                                                   accion=form.cleaned_data['accion'])
                        soli.save(request)
                        log(u'Adiciono Observación en Seguimiento Interesados Maestrías: %s' % soli, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'addinteres':
            try:
                with transaction.atomic():
                    form = SeguimientoInscripcionForm(request.POST)
                    if form.is_valid():
                        filtro = InteresadoProgramaMaestria(nombres=form.cleaned_data['nombres'].upper(),
                                              cedula=form.cleaned_data['cedula'],
                                              telefono=form.cleaned_data['telefono'],
                                              telefono_adicional=form.cleaned_data['telefono_adicional'],
                                              correo=form.cleaned_data['correo'].lower(),
                                              observacion=form.cleaned_data['observacion'],
                                              programa=form.cleaned_data['programa'])
                        filtro.save(request)
                        log(u'Adiciono interesado maestria: %s' % filtro, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addinteres':
                try:
                    data['form2'] = SeguimientoInscripcionForm()
                    template = get_template("adm_seguimientointeresados/modal/form.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'verobservaciones':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = InteresadoProgramaMaestria.objects.get(pk=request.GET['id'])
                    data['detalle'] = detalle = filtro.historialinteresadoprogramamaestria_set.all().order_by('pk')
                    template = get_template("adm_seguimientointeresados/modal/detalleobs.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addobservacion':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = InteresadoProgramaMaestria.objects.get(pk=request.GET['id'])
                    data['detalle'] = detalle = filtro.historialinteresadoprogramamaestria_set.all().order_by('pk')
                    form = SeguimientoHistorialForm()
                    HISTORIAL_CHOICES_OBSER = (
                        (2, "EL ESTUDIANTE CONTESTÓ"),
                        (3, "EL ESTUDIANTE NO CONTESTÓ"),
                        (4, "EL ESTUDIANTE NO ESTÁ INTERESADO"),
                        (5, "EL ESTUDIANTE CONFIRMO SU PARTICIPACIÓN"),
                    )
                    form.fields['accion'].choices = HISTORIAL_CHOICES_OBSER
                    data['form2'] = form
                    template = get_template("adm_seguimientointeresados/modal/formobservacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Seguimiento Interesados Maestrias'
            url_vars = ''
            filtro = Q(status=True)
            search = None
            ids = None
            programa = request.GET.get('programa', '')
            accion = request.GET.get('accion', '')
            desde = request.GET.get('desde', '')
            hasta = request.GET.get('hasta', '')
            orderby = request.GET.get('orderby', '4')

            if 's' in request.GET:
                if request.GET['s'] != '':
                    search = request.GET['s']

            if search:
                filtro = filtro & (Q(cedula__icontains=search)) | Q(nombres__icontains=search) | Q(observacion__icontains=search)
                url_vars += '&s=' + search

            if desde:
                data['desde'] = desde
                url_vars += "&desde={}".format(desde)
                filtro = filtro & Q(fecha_creacion__gte=desde)

            if hasta:
                data['hasta'] = hasta
                url_vars += "&hasta={}".format(hasta)
                filtro = filtro & Q(fecha_creacion__lte=hasta)

            if accion:
                data['accion'] = int(accion)
                filtro = filtro & (Q(accion=int(accion)))
                url_vars += '&accion=' + accion

            if programa:
                data['programa'] = int(programa)
                filtro = filtro & (Q(programa_id=int(programa)))
                url_vars += '&programa=' + programa

            ordering = '-pk'
            if orderby:
                data['orderby'] = orderby
                url_vars += "&orderby={}".format(orderby)
                if orderby == '0':
                    ordering = 'nombres'
                if orderby == '1':
                    ordering = 'programa__descripcion'
                if orderby == '2':
                    ordering = 'observacion'
                if orderby == '3':
                    ordering = 'fecha_creacion'
                if orderby == '4':
                    ordering = '-fecha_creacion'
                if orderby == '5':
                    ordering = 'accion'

            listamaestrias = InteresadoProgramaMaestria.objects.filter(status=True).distinct('programa').values_list('programa_id',flat=True)
            data['programas_lista'] = programa_lista = MaestriasAdmision.objects.filter(id__in=listamaestrias)

            listado = InteresadoProgramaMaestria.objects.filter(filtro).order_by(ordering)
            data['totalcount'] =  InteresadoProgramaMaestria.objects.filter(status=True).count()
            data['totalpendiente'] =  InteresadoProgramaMaestria.objects.filter(status=True, accion=1).count()
            data['totalcontestaron'] =  InteresadoProgramaMaestria.objects.filter(status=True, accion=2).count()
            data['totalnocontestaron'] =  InteresadoProgramaMaestria.objects.filter(status=True, accion=3).count()
            data['totalnointeresados'] =  InteresadoProgramaMaestria.objects.filter(status=True, accion=4).count()
            data['totalconfirmaron'] =  InteresadoProgramaMaestria.objects.filter(status=True, accion=5).count()
            paging = MiPaginador(listado, 25)
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
            data['listado'] = page.object_list
            data['email_domain'] = EMAIL_DOMAIN
            data['estados_solicitud'] = HISTORIAL_CHOICES
            return render(request, 'adm_seguimientointeresados/view.html', data)
