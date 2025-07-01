# -*- coding: latin-1 -*-
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from decorators import last_access, secure_module
from inno.funciones import enviar_notificacion_aceptar_rechazar_solicitud_asistencia_pro
from settings import SOLICITUD_PREPROYECTO_ESTADO_APROBADO_ID, \
    SOLICITUD_PREPROYECTO_ESTADO_RECHAZADO_ID
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log
from sga.models import SolicitudAperturaClase, Carrera, Profesor, ESTADOS_PREPROYECTO


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    miscarreras = persona.mis_carreras()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'aprobarrechazar':
            try:
                value = int(request.POST['value'])
                solicitud = SolicitudAperturaClase.objects.get(pk=request.POST['id'])
                solicitud.estado = SOLICITUD_PREPROYECTO_ESTADO_APROBADO_ID if value == 1 else SOLICITUD_PREPROYECTO_ESTADO_RECHAZADO_ID
                solicitud.fecharespuesta = datetime.now().date()
                solicitud.save(request)
                log(u'Aprobo o rechazo en apertura de clase: %s - %s [%s]' % (solicitud,solicitud.estado, solicitud.id), request, "edit")
                enviar_notificacion_aceptar_rechazar_solicitud_asistencia_pro(solicitud)
                return JsonResponse({"result": "ok", "mensaje": f"{'Se aprobo correctamente la solicitud' if value == 1 else 'Se rechazo correctamente la solicitud'}"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error al aprobar o rechazara la solicitud. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'aprobarrechazar':
                try:
                    tipo = int(request.GET['t'])
                    data['solicitud'] = SolicitudAperturaClase.objects.get(pk=request.GET['id'])
                    if tipo == 1:
                        data['title'] = u'Aprobar solicitud de apertura de clase'
                    else:
                        data['title'] = u'Rechazar solicitud de apertura de clase'
                    data['tipo'] = tipo
                    return render(request, "adm_aperturaclase/aprobarrechazar.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Solicitudes de apertura de clases'
            search = None
            ids = None
            solicitudes = SolicitudAperturaClase.objects.filter(materia__nivel__periodo=periodo, materia__cerrado=False).distinct().order_by('estado')
            carreras = Carrera.objects.filter(pk__in=solicitudes.values_list('materia__asignaturamalla__malla__carrera_id', flat=True).distinct()).distinct()
            profesores = Profesor.objects.filter(pk__in=solicitudes.values_list('profesor_id', flat=True).distinct()).distinct()
            p_id = 0
            c_id = 0
            e_id = 0
            if not persona.usuario.is_superuser:
                solicitudes = solicitudes.filter(Q(materia__asignaturamalla__malla__carrera__in=miscarreras)).distinct().order_by('estado')

            if 'c_id' in request.GET:
                if int(request.GET['c_id']) > 0:
                    c_id = int(request.GET['c_id'])
                    solicitudes = solicitudes.filter(Q(materia__asignaturamalla__malla__carrera__id=c_id))
                    profesores = Profesor.objects.filter(pk__in=solicitudes.values_list('profesor_id', flat=True).filter(Q(materia__asignaturamalla__malla__carrera__id=c_id)).distinct()).distinct()

            if 'p_id' in request.GET:
                if int(request.GET['p_id']) > 0:
                    p_id = int(request.GET['p_id'])
                    solicitudes = solicitudes.filter(profesor_id=p_id).distinct()

            if 'e_id' in request.GET:
                if int(request.GET['e_id']) > 0:
                    e_id = int(request.GET['e_id'])
                    solicitudes = solicitudes.filter(estado=e_id).distinct()

            if 's' in request.GET:
                search = request.GET['s']
                ss = search.split(' ')
                if len(ss) == 1:
                    solicitudes = solicitudes.filter(Q(profesor__persona__nombres__icontains=search) |
                                                     Q(profesor__persona__apellido1__icontains=search) |
                                                     Q(profesor__persona__apellido2__icontains=search) |
                                                     Q(profesor__persona__cedula__icontains=search)).distinct().order_by('estado')
                else:
                    solicitudes = solicitudes.filter(Q(profesor__persona__apellido1__icontains=ss[0]) &
                                                     Q(profesor__persona__apellido2__icontains=ss[1])).distinct().order_by('estado')
            if 'id' in request.GET:
                ids = request.GET['id']
                solicitudes = solicitudes.filter(id=ids).distinct().order_by('estado')

            paging = MiPaginador(solicitudes, 25)
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
            data['solicitudes'] = page.object_list
            data['p_id'] = p_id
            data['c_id'] = c_id
            data['e_id'] = e_id
            data['carreras'] = carreras
            data['profesores'] = profesores
            data['estados'] = ESTADOS_PREPROYECTO
            data['total_registros'] = solicitudes.count()
            data['total_pendientes'] = solicitudes.filter(estado=1).count()
            data['total_aprobados'] = solicitudes.filter(estado=2).count()
            data['total_rechazados'] = solicitudes.filter(estado=3).count()
            return render(request, "adm_aperturaclase/view.html", data)
