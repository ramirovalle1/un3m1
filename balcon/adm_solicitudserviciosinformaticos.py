# -*- coding: UTF-8 -*-
import json
import random
import sys
from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
import xlwt
from django.views.decorators.csrf import csrf_exempt
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import Context
from django.template.loader import get_template
from xlwt import *
from django.shortcuts import render, redirect

from balcon.forms import SolicitudInformacionServicioForm, SolicitudObservacionServiciosForm
from decorators import secure_module, last_access
from sagest.models import Departamento, Producto, DistributivoPersona
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre, puede_realizar_accion, null_to_decimal, \
    puede_realizar_accion_afirmativo, generar_codigo
from sga.models import Administrativo, Persona
from .models import SolucitudServiciosInformaticos, ESTADOS_SOLICITUD_INFORMATICOS, \
    SolicitudObservacionesServiciosInformaticos

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    PREFIX = 'FRM'
    SUFFIX = 'DSERINF'
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    departamentopersona = persona.departamento_set.all().first() if persona.departamento_set.all().exists() else None
    data['puede_administrar'] = puede_administrar = puede_realizar_accion_afirmativo(request,'sagest.puede_administrar_solicitudes_servicios')
    data['title'] = u'Solicitud de Productos'
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addsolicitud':
            try:
                with transaction.atomic():
                    f = SolicitudInformacionServicioForm(request.POST, request.FILES)
                    if f.is_valid():
                        newfile = None

                        numsolicitud = SolucitudServiciosInformaticos.objects.filter(departamento=f.cleaned_data['departamento'], fechaoperacion__year=datetime.now().year).count() + 1
                        codsolicitud = generar_codigo(numsolicitud, PREFIX, SUFFIX)
                        responsable = f.cleaned_data['responsable']
                        distributivo = DistributivoPersona.objects.filter(status=True, persona=responsable)[0]
                        denominaciondirector = DistributivoPersona.objects.filter(status=True, persona=distributivo.unidadorganica.responsable,unidadorganica=distributivo.unidadorganica)[0].denominacionpuesto.descripcion

                        soliserv = SolucitudServiciosInformaticos(numerodocumento=numsolicitud,
                                                                  codigodocumento=codsolicitud,
                                                                  fechaoperacion=datetime.now().date(),
                                                                  departamento=f.cleaned_data['departamento'],
                                                                  responsable=f.cleaned_data['responsable'],
                                                                  denominacionpuesto=distributivo.denominacionpuesto.descripcion,
                                                                  director=distributivo.unidadorganica.responsable,
                                                                  directordenominacionpuesto=denominaciondirector,
                                                                  descripcion=f.cleaned_data['descripcion'])
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            extension = newfile._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if newfile.size > 4194304:
                                return JsonResponse({"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                            if exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                                newfile._name = generar_nombre("solicitudservinf_", newfile._name)
                            else:
                                return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                            soliserv.archivo = newfile
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "FALTA SUBIR SOLICITUD"}, safe=False)
                        soliserv.save(request)
                        obser = SolicitudObservacionesServiciosInformaticos(solicitud=soliserv, estados=1, observacion=f.cleaned_data['descripcion'])
                        obser.save(request)
                        log(u'Adiciono Solicitud Servicios Informaticos: %s' % soliserv, request, "add")
                        return JsonResponse({"result": False, 'to': request.path}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'delsolicitud':
            try:
                solicitud = SolucitudServiciosInformaticos.objects.get(pk=request.POST['id'])
                log(u'Eliminó solicitud de Servicios Informaticos: %s' % (solicitud), request, "del")
                solicitud.status = False
                solicitud.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos. Detalle: %s" % (msg)})

        elif action == 'addobservacion':
            try:
                with transaction.atomic():
                    filtro = SolucitudServiciosInformaticos.objects.get(pk=int(request.POST['id']))
                    form = SolicitudObservacionServiciosForm(request.POST)
                    if form.is_valid():
                        filtro.estados = form.cleaned_data['estados']
                        filtro.save()
                        soli = SolicitudObservacionesServiciosInformaticos(solicitud=filtro,
                                                                    observacion=form.cleaned_data['descripcion'].upper(),
                                                                    estados=form.cleaned_data['estados'])
                        soli.save(request)
                        log(u'Adiciono Observación Solicitud Servicios Informaticos: %s' % soli, request, "add")
                        # return JsonResponse({"result": False,'to':'/nuevaurl'}, safe=False) SI DESEAS REDIRECCIONAR ADICIONARLE TO A LA RESPUESTA
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'buscarresponsable':
            try:
                departamento = Departamento.objects.get(pk=int(request.POST['id']))
                lista = []
                for integrante in departamento.integrantes.filter(administrativo__isnull=False):
                    lista.append([integrante.id, integrante.nombre_completo_inverso()])
                return JsonResponse({"result": "ok", "lista": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addsolicitud':
                try:
                    numsolicitud = SolucitudServiciosInformaticos.objects.filter(departamento=departamentopersona, fechaoperacion__year=datetime.now().year).count() + 1
                    ultimo = generar_codigo(numsolicitud, PREFIX, SUFFIX, 9, True)
                    form = SolicitudInformacionServicioForm(initial={'codigodocumento': ultimo,
                                                          'fechaoperacion': datetime.now().date()})
                    form.adicionar()
                    if not puede_administrar:
                        form.fields['departamento'].queryset = Departamento.objects.filter(pk=departamentopersona.pk)
                    data['form2'] = form
                    template = get_template("adm_solicitudserviciosinformaticos/modal/formsolicitud.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'delsolicitud':
                try:
                    data['title'] = u'Eliminar Solicitud'
                    data['solicitud'] = solicitud = SolucitudServiciosInformaticos.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_solicitudserviciosinformaticos/deletesolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'addobservacion':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = SolucitudServiciosInformaticos.objects.get(pk=request.GET['id'])
                    form = SolicitudObservacionServiciosForm()
                    ESTADOS_SOLICITUD_PRODUCTOS_OBS = (
                        (2, u'FINALIZADO'),
                        (3, u'RECHAZADO'),
                    )
                    form.fields['estados'].choices = ESTADOS_SOLICITUD_PRODUCTOS_OBS
                    data['form2'] = form
                    template = get_template("adm_solicitudserviciosinformaticos/modal/formobservacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'verobservaciones':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = SolucitudServiciosInformaticos.objects.get(pk=request.GET['id'])
                    data['detalle'] = detalle = filtro.solicitudobservacionesserviciosinformaticos_set.all().order_by('pk')
                    template = get_template("adm_solicitudserviciosinformaticos/modal/detalleobs.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Solicitud de Permisos a los Sistemas de Información'
            url_vars = ''
            filtro = Q(status=True)
            search = None
            ids = None
            tipo = request.GET.get('tipo', '')
            departamento = request.GET.get('departamento', '')

            if 's' in request.GET:
                if request.GET['s'] != '':
                    search = request.GET['s']

            if search:
                filtro = filtro & (Q(codigodocumento__icontains=search)) | Q(responsable__cedula__icontains=search) | Q(responsable__apellido1__icontains=search) | Q(departamento__nombre__icontains=search)
                url_vars += '&s=' + search

            if tipo:
                data['tipo'] = int(tipo)
                filtro = filtro & (Q(estados=int(tipo)))
                url_vars += '&tipo=' + tipo

            if departamento:
                data['departamento'] = int(departamento)
                filtro = filtro & (Q(departamento_id=int(departamento)))
                url_vars += '&departamento=' + departamento

            if not puede_administrar:
                if departamentopersona:
                    procesos = SolucitudServiciosInformaticos.objects.filter(filtro).filter(
                        departamento=departamentopersona).order_by('-fecha_creacion')
                else:
                    messages.error(request, 'Usted no pertenece a ningun departamento')
                    return redirect('/')
            else:
                procesos = SolucitudServiciosInformaticos.objects.filter(filtro).order_by('-fecha_creacion')
            data['totalcount'] = procesos.count()
            data['totalpendientes'] = procesos.filter(estados=1).count()
            data['totalfinalizadas'] = procesos.filter(estados=2).count()
            data['totalrechazados'] = procesos.filter(estados=3).count()

            paging = MiPaginador(procesos, 25)
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
            data['estados_solicitud'] = ESTADOS_SOLICITUD_INFORMATICOS
            if puede_administrar:
                data['departamentos'] = Departamento.objects.filter(integrantes__isnull=False, status=True).distinct()
            return render(request, 'adm_solicitudserviciosinformaticos/view.html', data)
