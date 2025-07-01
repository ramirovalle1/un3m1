# -*- coding: UTF-8 -*-
import json
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template
from decorators import secure_module, last_access
from sagest.forms import CapSolicitudForm
from sagest.models import Departamento, CapCabeceraSolicitud, CapDetalleSolicitud, CapEventoPeriodo, DistributivoPersona
from settings import PUESTO_ACTIVO_ID
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, variable_valor
from datetime import datetime



@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
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
        if action == 'add':
            try:
                f = CapSolicitudForm(request.POST)
                if f.is_valid():
                    if not request.POST['lista_items1']:
                        return JsonResponse({"result": "bad", "mensaje": u"No a elegido un evento programado"})
                    distributivo = DistributivoPersona.objects.filter(pk=f.cleaned_data['participante'], status=True,estadopuesto=PUESTO_ACTIVO_ID)[0]
                    listadoeventos = CapEventoPeriodo.objects.filter(id__in=[int(datos['idevento']) for datos in json.loads(request.POST['lista_items1'])]) if request.POST['lista_items1'] else []
                    for evento in listadoeventos:
                            cabecera = CapCabeceraSolicitud(capeventoperiodo=evento,
                                                             solicita=persona,
                                                             fechasolicitud=datetime.now().date(),
                                                             estadosolicitud=variable_valor('PENDIENTE_CAPACITACION'),
                                                             participante=distributivo.persona)
                            cabecera.save(request)
                            log(u'Ingreso Cabecera Solicitud de Evento : %s' % cabecera, request, "add")
                            detalle = CapDetalleSolicitud(cabecera=cabecera,
                                                          aprueba=persona,
                                                          observacion=f.cleaned_data['observacion'],
                                                          fechaaprobacion=datetime.now().date(),
                                                          estado=2)
                            detalle.save(request)
                            detalle.mail_notificar_talento_humano(request.session['nombresistema'], False)
                            log(u'Ingreso Detalle Solicitud de Evento : %s' % detalle, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Llene todos los campos"})

        if action == 'addaprobacion':
            try:
                cabecera=CapCabeceraSolicitud.objects.get(pk=int(request.POST['id']))
                cabecera.estadosolicitud=variable_valor('PENDIENTE_CAPACITACION') if int(request.POST['estado'])==variable_valor('APROBADO_CAPACITACION') else variable_valor('RECHAZADO_CAPACITACION')
                cabecera.save(request)
                detalle = CapDetalleSolicitud(cabecera=cabecera,
                                            fechaaprobacion=datetime.now().date(),
                                            observacion=request.POST['observacion'],
                                            aprueba=persona,
                                            estado= 2 if int(request.POST['estado'])==variable_valor('APROBADO_CAPACITACION') else 3)
                detalle.save(request)
                detalle.mail_notificar_jefe_departamento(request.session['nombresistema'],True)
                log(u'Aprobar solicitud(Director): %s' % detalle, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'busqueda':
                try:
                    director= DistributivoPersona.objects.filter(persona=persona,estadopuesto__id=PUESTO_ACTIVO_ID,status=True)[0]
                    q = request.GET['q'].upper().strip()
                    if ' ' in q:
                        s = q.split(" ")
                        distributivo=DistributivoPersona.objects.filter(Q(persona__apellido1__contains=s[0]) & Q(persona__apellido2__contains=s[1])&Q(unidadorganica=director.unidadorganica),estadopuesto__id=PUESTO_ACTIVO_ID,status=True).distinct()[:20]
                    distributivo=DistributivoPersona.objects.filter(Q(persona__nombres__contains=q) | Q(persona__apellido1__contains=q) | Q(persona__apellido2__contains=q) | Q(persona__cedula__contains=q)).filter(unidadorganica=director.unidadorganica,estadopuesto__id=PUESTO_ACTIVO_ID,status=True)[:20]
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_repr()}for x in distributivo]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'busquedaregistro':
                try:
                    eventoperiodo= CapEventoPeriodo.objects.get(pk=int(request.GET['id']))
                    data = {"result": "ok", "results": [{"id": eventoperiodo.id,"horas":str(eventoperiodo.horas),"evento":str(eventoperiodo.capevento), "inicio":str(eventoperiodo.fechainicio.strftime('%d-%m-%Y')),"fin":str(eventoperiodo.fechafin.strftime('%d-%m-%Y')),"enfoque":str(eventoperiodo.enfoque)}if eventoperiodo else ""]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'listadoinscripcion':
                try:
                    participante= DistributivoPersona.objects.get(pk=int(request.GET['idp']))
                    tieneeventos = CapCabeceraSolicitud.objects.values_list("capeventoperiodo_id").filter(participante=participante.persona)
                    excluir = CapEventoPeriodo.objects.values_list("id").filter(capevento__nombre__in=[datos['evento'] for datos in json.loads(request.GET['listado'])]) if request.GET['listado'] else []
                    eventoperiodolista =CapEventoPeriodo.objects.filter((Q(fechainicio__lte=datetime.now().date())&Q(fechafin__gte=datetime.now().date()))&Q(status=True)&Q(visualizar=True)&Q(regimenlaboral=participante.regimenlaboral)).exclude(Q(pk__in=excluir)|Q(pk__in=tieneeventos))
                    if eventoperiodolista:
                        data = {"result": "ok", "results": [{"id": str(eventoperiodo.id),"horas":str(eventoperiodo.horas),"evento":str(eventoperiodo.capevento),"inicio":str(eventoperiodo.fechainicio.strftime('%d-%m-%Y')),"fin":str(eventoperiodo.fechafin.strftime('%d-%m-%Y')),"enfoque":str(eventoperiodo.enfoque),"inscrito":str(eventoperiodo.contar_inscripcion_evento_periodo()),"modalidad":str(eventoperiodo.get_modalidad_display())}for eventoperiodo in eventoperiodolista]}
                    else:
                        data = {"result": "no"}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'add':
                try:
                    data['title'] = u'Solicitar Evento'
                    form = CapSolicitudForm(initial={'fechasolicitud': datetime.now().date(),'solicito':persona})
                    form.adicionar()
                    data['form'] = form
                    data['eventos'] = eventos=CapEventoPeriodo.objects.filter((Q(fechainicio__lte=datetime.now().date()) & Q(fechafin__gte=datetime.now().date())) & Q(status=True) & Q(visualizar=True))
                    data['regimenlaboral']=eventos[0].regimenlaboral
                    return render(request, "adm_capacitacionaprobacion/add.html", data)
                except Exception as ex:
                    pass

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
                    data['fecha'] = datetime.now().date()
                    data['solicitud_capacitacion'] = variable_valor('SOLICITUD_CAPACITACION')
                    data['pendiente_capacitacion'] = variable_valor('PENDIENTE_CAPACITACION')
                    data['aprobado_capacitacion'] = variable_valor('APROBADO_CAPACITACION')
                    data['rechazado_capacitacion'] = variable_valor('RECHAZADO_CAPACITACION')
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
            data['title'] = u'Aprobar Incripción de Evento(Director).'
            search = None
            ids = None
            # if Departamento.objects.values('id').filter(responsable=persona, permisogeneral=True,integrantes__isnull=False,status=True).exists():
            #     departamento = Departamento.objects.all()
            # else:
            departamento = Departamento.objects.filter(responsable=persona,integrantes__isnull=False,status=True)
            persona_jefe=DistributivoPersona.objects.values_list('regimenlaboral_id').filter(persona=persona, unidadorganica__in=departamento, estadopuesto_id=PUESTO_ACTIVO_ID)
            if 's' in request.GET:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                if len(ss) == 1:
                    eventos = CapCabeceraSolicitud.objects.filter((Q(participante__nombres__icontains=search) |
                                                   Q(participante__apellido1__icontains=search) |
                                                   Q(participante__apellido2__icontains=search) |
                                                   Q(participante__cedula__icontains=search) |
                                                   Q(participante__pasaporte__icontains=search))&
                                                   Q(participante__distributivopersona__unidadorganica__in=departamento)).distinct().order_by('estadosolicitud','-fechasolicitud')
                else:
                    eventos = CapCabeceraSolicitud.objects.filter(Q(participante__apellido1__icontains=ss[0]) & Q(solicita__apellido2__icontains=ss[1])&
                                                   Q(participante__distributivopersona__unidadorganica__in=departamento)).distinct().order_by('estadosolicitud','-fechasolicitud')
            else:
                eventos = CapCabeceraSolicitud.objects.filter(Q(participante__distributivopersona__unidadorganica__in=departamento)).distinct().order_by('estadosolicitud','-fechasolicitud')
            cambiar = CapDetalleSolicitud.objects.filter(aprueba=persona).exclude(Q(cabecera__participante__distributivopersona__unidadorganica__in=departamento)).distinct()
            paging = MiPaginador(eventos, 20)
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
            data['cabecera'] = page.object_list
            data['solicitud_capacitacion'] = variable_valor('SOLICITUD_CAPACITACION')
            data['pendiente_capacitacion'] = variable_valor('PENDIENTE_CAPACITACION')
            data['aprobado_capacitacion'] = variable_valor('APROBADO_CAPACITACION')
            data['existeevento'] = CapEventoPeriodo.objects.filter((Q(fechainicio__lte=datetime.now().date()) & Q(fechafin__gte=datetime.now().date())) & Q(status=True) & Q(visualizar=True)).exists()
            return render(request, 'adm_capacitacionaprobacion/aprobar_director.html', data)