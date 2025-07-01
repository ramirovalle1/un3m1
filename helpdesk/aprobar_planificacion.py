# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from itertools import chain
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template
from decorators import secure_module
from helpdesk.models import HdAprobarSolicitud, HdPlanAprobacion, ESTADO_APROBACION
from sagest.models import Departamento
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log
from datetime import datetime


# @login_required(redirect_field_name='ret', login_url='/loginsagest')
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    if not Departamento.objects.filter(responsable=persona).exists():
        return HttpResponseRedirect('/?info=Usted no es reponsable de un departamento.')
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addaprobacion':
            try:
                permiso = HdPlanAprobacion.objects.get(pk=request.POST['id'])
                aprobar = HdAprobarSolicitud(plan=permiso,
                                            fechaaprobacion=datetime.now().date(),
                                            observacion=request.POST['obse'],
                                            aprueba=persona,
                                            estadosolicitud=int(request.POST['esta']))
                aprobar.save(request)
                permiso.estadoaprobacion=int(request.POST['esta'])
                permiso.save()
                # aprobar.mail_notificar_jefe_departamento(request.session['nombresistema'])
                log(u'Aprobar solicitud(Director): %s' % aprobar, request, "add")
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
                    detalle = HdPlanAprobacion.objects.get(pk=int(request.GET['id']))
                    data['solicitud'] = detalle
                    data['detallesolicitud'] = detalle.hdaprobarsolicitud_set.all()
                    data['aprobadores'] = detalle.hdaprobarsolicitud_set.all()
                    template = get_template("helpdesk_solicitud/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'detalle':
                try:
                    data = {}
                    detalle = HdPlanAprobacion.objects.get(pk=int(request.GET['id']))
                    data['solicitud'] = detalle
                    data['detallesolicitud'] = detalle.hdaprobarsolicitud_set.all()
                    data['aprobador'] = persona
                    data['fecha'] = datetime.now().date()
                    data['aprobadores'] = detalle.hdaprobarsolicitud_set.all()
                    template = get_template("helpdesk_solicitud/detalle_aprobar.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Aprobar Planificación(Director).'
            search = None
            ids = None
            if Departamento.objects.filter(responsable=persona, permisogeneral=True, integrantes__isnull=False).exists():
                departamento = Departamento.objects.all()
            else:
                departamento = Departamento.objects.filter(responsable=persona, integrantes__isnull=False)
            plantillas = HdPlanAprobacion.objects.filter(status=True).exclude(solicita=persona).order_by('-fecharegistro')
            if 's' in request.GET:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                if len(ss) == 1:
                    plantillas = plantillas.filter(Q(solicita__nombres__icontains=search) |
                                                   Q(solicita__apellido1__icontains=search) |
                                                   Q(solicita__apellido2__icontains=search) |
                                                   Q(solicita__cedula__icontains=search) |
                                                   Q(solicita__pasaporte__icontains=search)).distinct().order_by('-fecharegistro')
                else:
                    plantillas = plantillas.filter(Q(solicita__apellido1__icontains=ss[0]) & Q(solicita__apellido2__icontains=ss[1])).distinct().order_by('-fecharegistro')
            if 'ids' in request.GET:
                ids = int(request.GET['ids'])
                if ids > 0:
                    plantillas = plantillas.filter(estadoaprobacion=ids).distinct().order_by('-fechasolicitud')
            # plantillas = list(chain(plantillas.filter(estadosolicitud__in=[1, 5]).order_by('-estadosolicitud'), plantillas.exclude(estadosolicitud__in=[1, 5]).order_by('-estadosolicitud')))
            paging = MiPaginador(plantillas, 20)
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
            data['solicitud'] = page.object_list
            data['email_domain'] = EMAIL_DOMAIN
            data['solicitudes'] = ESTADO_APROBACION

            return render(request, 'helpdesk_solicitud/aprobar_director.html', data)