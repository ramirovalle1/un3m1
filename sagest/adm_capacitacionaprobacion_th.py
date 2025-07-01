# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template
from decorators import secure_module
from sagest.models import CapCabeceraSolicitud, CapDetalleSolicitud, CapEventoPeriodo
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, variable_valor
from datetime import datetime


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addaprobacion':
            try:
                cabecera=CapCabeceraSolicitud.objects.get(pk=int(request.POST['id']))
                if not cabecera.capeventoperiodo.hay_cupo_inscribir() and variable_valor('APROBADO_CAPACITACION')==int(request.POST['estado']):
                    return JsonResponse({"result": "bad", "mensaje": u"No hay cupo disponible."})
                cabecera.estadosolicitud=int(request.POST['estado'])
                cabecera.fechaultimaestadosolicitud=datetime.now()
                cabecera.save(request)
                detalle = CapDetalleSolicitud(cabecera=cabecera,
                                                fechaaprobacion=datetime.now().date(),
                                                observacion=request.POST['observacion'],
                                                aprueba=persona,
                                                estado= 2 if int(request.POST['estado'])==variable_valor('APROBADO_CAPACITACION') else 3)
                detalle.save(request)
                detalle.mail_notificar_talento_humano(request.session['nombresistema'],True)
                log(u'Aprobar solicitud(Director): %s' % detalle, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'verdetalle':
                try:
                    data = {}
                    cabecera = CapCabeceraSolicitud.objects.get(pk=int(request.GET['id']))
                    data['cabecerasolicitud'] = cabecera
                    data['detallesolicitud'] = cabecera.capdetallesolicitud_set.all()
                    data['solicitud_capacitacion'] = variable_valor('SOLICITUD_CAPACITACION')
                    data['pendiente_capacitacion'] = variable_valor('PENDIENTE_CAPACITACION')
                    data['aprobado_capacitacion'] = variable_valor('APROBADO_CAPACITACION')
                    template = get_template("adm_capacitacionaprobacion/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'detalle':
                try:
                    data = {}
                    cabecera = CapCabeceraSolicitud.objects.get(pk=int(request.GET['id']))
                    data['cabecerasolicitud'] = cabecera
                    data['detallesolicitud'] = cabecera.capdetallesolicitud_set.all()
                    data['aprobador'] = persona
                    data['solicitud_capacitacion'] = variable_valor('SOLICITUD_CAPACITACION')
                    data['pendiente_capacitacion'] = variable_valor('PENDIENTE_CAPACITACION')
                    data['aprobado_capacitacion'] = variable_valor('APROBADO_CAPACITACION')
                    data['rechazado_capacitacion'] =variable_valor('RECHAZADO_CAPACITACION')
                    data['fecha'] = datetime.now().date()
                    template = get_template("adm_capacitacionaprobacion/detalle_aprobar.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'detalleevento':
                try:
                    data['evento'] = evento = CapEventoPeriodo.objects.get(pk=int(request.GET['id']))
                    template = get_template("adm_capacitacionaprobacion/detalleevento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u'Aprobacion de Evento.'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                if len(ss) == 1:
                    cabecera = CapCabeceraSolicitud.objects.filter(Q(solicita__nombres__icontains=search) |
                                                                   Q(solicita__apellido1__icontains=search) |
                                                                   Q(solicita__apellido2__icontains=search) |
                                                                   Q(solicita__cedula__icontains=search) |
                                                                   Q(solicita__pasaporte__icontains=search) |
                                                                   Q(capeventoperiodo__capevento__nombre__icontains=search)).distinct().order_by('solicita__apellido1','solicita__apellido2','solicita__nombres','solicita__cedula')
                elif len(ss) == 2:
                    cabecera = CapCabeceraSolicitud.objects.filter((Q(solicita__apellido1__icontains=ss[0]) &
                                                                    Q(solicita__apellido2__icontains=ss[1])) |
                                                                   (Q(capeventoperiodo__capevento__nombre__icontains=ss[0]) &
                                                                    Q(capeventoperiodo__capevento__nombre__icontains=ss[1]))).distinct().order_by('solicita__apellido1', 'solicita__apellido2','solicita__nombres')
                elif len(ss) == 3:
                    cabecera = CapCabeceraSolicitud.objects.filter((Q(solicita__apellido1__icontains=ss[0]) &
                                                                   Q(solicita__apellido2__icontains=ss[1]) &
                                                                   Q(solicita__nombres__icontains=ss[2])) |
                                                                   (Q(capeventoperiodo__capevento__nombre__icontains=ss[0]) &
                                                                    Q(capeventoperiodo__capevento__nombre__icontains=ss[1]) &
                                                                    Q(capeventoperiodo__capevento__nombre__icontains=ss[2]))).distinct().order_by('solicita__apellido1', 'solicita__apellido2','solicita__nombres')
                else:
                    cabecera = CapCabeceraSolicitud.objects.filter((Q(solicita__apellido1__icontains=ss[0]) &
                                                                   Q(solicita__apellido2__icontains=ss[1]) &
                                                                   Q(solicita__nombres__icontains=ss[2]) &
                                                                   Q(solicita__nombres__icontains=ss[3])) |
                                                                   (Q(capeventoperiodo__capevento__nombre__icontains=ss[0]) &
                                                                    Q(capeventoperiodo__capevento__nombre__icontains=ss[1]) &
                                                                    Q(capeventoperiodo__capevento__nombre__icontains=ss[2]) &
                                                                    Q(capeventoperiodo__capevento__nombre__icontains=ss[3]))).distinct().order_by('solicita__apellido1', 'solicita__apellido2','solicita__nombres')
            else:
                cabecera = CapCabeceraSolicitud.objects.filter(status=True).distinct().order_by('estadosolicitud', '-fechasolicitud')
            paging = MiPaginador(cabecera, 20)
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
            data['solicitud_capacitacion'] = variable_valor('SOLICITUD_CAPACITACION')
            data['pendiente_capacitacion'] = variable_valor('PENDIENTE_CAPACITACION')
            data['aprobado_capacitacion'] = variable_valor('APROBADO_CAPACITACION')
            data['cabecera'] = page.object_list
            # data['email_domain'] = EMAIL_DOMAIN
            return render(request, 'adm_capacitacionaprobacion/aprobar_th.html', data)