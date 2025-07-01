# -*- coding: UTF-8 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.template.context import Context
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from django.db.models import Q
from sga.funciones import log, variable_valor, MiPaginador
from sga.models import SolicitudGrupoInvestigacion, SolicitudTematicaGrupoInvestigacion, SolicitudDetalleGrupoInvestigacion


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    persona = request.session['persona']
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addaprobacion':
            try:
                cabecera=SolicitudGrupoInvestigacion.objects.get(pk=int(request.POST['id']))
                cabecera.estado=variable_valor('APROBADO_GRUPO_INVESTIGACION') if int(request.POST['estado'])==variable_valor('APROBADO_GRUPO_INVESTIGACION') else variable_valor('RECHAZADO_GRUPO_INVESTIGACION')
                cabecera.save(request)
                detalle = SolicitudDetalleGrupoInvestigacion(cabecera=cabecera,
                                                            fechaaprobacion=datetime.now(),
                                                            observacion=request.POST['observacion'],
                                                            aprueba=persona,
                                                            estado= 2 if int(request.POST['estado'])==variable_valor('APROBADO_GRUPO_INVESTIGACION') else 3)
                detalle.save(request)
                # detalle.mail_notificar_jefe_departamento(request.session['nombresistema'],True)
                log(u'Aprobar solicitud de grupo investigacion(Investigacion): %s - [%s]' % (detalle,detalle.id), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return HttpResponseRedirect(request.path)

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'detallegrupo':
                try:
                    data['grupo'] = grupo = SolicitudGrupoInvestigacion.objects.get(pk=int(request.GET['id']))
                    data['participantes'] = grupo.solicitudparticipantegrupoinvestigacion_set.filter(status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres','apellido', 'nombre')
                    data['tematicas'] = SolicitudTematicaGrupoInvestigacion.objects.filter(grupo_id=int(request.GET['id']), status=True)
                    data['creado'] = variable_valor('CREADO_GRUPO_INVESTIGACION')
                    data['pendiente'] = variable_valor('PENDIENTE_GRUPO_INVESTIGACION')
                    data['solicitado'] = variable_valor('SOLICITADO_GRUPO_INVESTIGACION')
                    data['aprobado'] = variable_valor('APROBADO_GRUPO_INVESTIGACION')
                    if 's' in request.GET:
                        data['search'] = request.GET['s']
                    if 'page' in request.GET:
                        data['pagenumber'] = request.GET['page']
                    data['url_regresar'] = 'adm_solaprobar_inv'
                    return render(request, "adm_solicitudaprobacioninvestigacion/detallegrupo.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'detalle':
                try:
                    data = {}
                    cabecera = SolicitudGrupoInvestigacion.objects.get(pk=int(request.GET['id']))
                    data['cabecerasolicitud'] = cabecera
                    data['detallesolicitud'] = cabecera.solicituddetallegrupoinvestigacion_set.all()
                    data['aprobador'] = persona
                    data['fecha'] = datetime.now()
                    data['creado'] = variable_valor('CREADO_GRUPO_INVESTIGACION')
                    data['pendiente'] = variable_valor('PENDIENTE_GRUPO_INVESTIGACION')
                    data['solicitado'] = variable_valor('SOLICITADO_GRUPO_INVESTIGACION')
                    data['aprobado'] = variable_valor('APROBADO_GRUPO_INVESTIGACION')
                    template = get_template("adm_solicitudaprobacioninvestigacion/detalle_aprobar.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'detalleavance':
                try:
                    data = {}
                    cabecera = SolicitudGrupoInvestigacion.objects.get(pk=int(request.GET['id']))
                    data['cabecerasolicitud'] = cabecera
                    data['detallesolicitud'] = cabecera.solicituddetallegrupoinvestigacion_set.all()
                    data['creado'] = variable_valor('CREADO_GRUPO_INVESTIGACION')
                    data['pendiente'] = variable_valor('PENDIENTE_GRUPO_INVESTIGACION')
                    data['solicitado'] = variable_valor('SOLICITADO_GRUPO_INVESTIGACION')
                    data['aprobado'] = variable_valor('APROBADO_GRUPO_INVESTIGACION')
                    template = get_template("adm_solicitudaprobacioninvestigacion/detalleavance.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Aprobar solicitud de grupo investigación(Investigación).'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                if len(ss) == 1:
                    grupos = SolicitudGrupoInvestigacion.objects.filter((Q(codirector__persona__nombres__icontains=search) |
                                                                         Q(codirector__persona__apellido1__icontains=search) |
                                                                         Q(codirector__persona__apellido2__icontains=search) |
                                                                         Q(codirector__persona__cedula__icontains=search) |
                                                                         Q(codirector__persona__pasaporte__icontains=search) |
                                                                         Q(director__persona__nombres__icontains=search) |
                                                                         Q(director__persona__apellido1__icontains=search) |
                                                                         Q(director__persona__apellido2__icontains=search) |
                                                                         Q(director__persona__cedula__icontains=search) |
                                                                         Q(director__persona__pasaporte__icontains=search) |
                                                                         Q(nombre__icontains=search)) & Q(status=True) &
                                                                        (Q(estado=variable_valor('SOLICITADO_GRUPO_INVESTIGACION')) | Q(estado=variable_valor('APROBADO_GRUPO_INVESTIGACION')) |
                                                                         Q(estado=variable_valor('PENDIENTE_GRUPO_INVESTIGACION')) | Q(estado=variable_valor('RECHAZADO_GRUPO_INVESTIGACION')))).distinct(). \
                                                                         order_by('nombre', 'director__persona__apellido1', 'director__persona__apellido2','director__persona__nombres')
                else:
                    grupos = SolicitudGrupoInvestigacion.objects.filter(Q(nombre__icontains=ss[0]) & Q(nombre__icontains=ss[1]) & Q(status=True) &
                                                                        (Q(estado=variable_valor('SOLICITADO_GRUPO_INVESTIGACION')) | Q(estado=variable_valor('APROBADO_GRUPO_INVESTIGACION'))|
                                                                         Q(estado=variable_valor('RECHAZADO_GRUPO_INVESTIGACION')) | Q(estado=variable_valor('PENDIENTE_GRUPO_INVESTIGACION')))).distinct().order_by('nombre')
            else:
                grupos = SolicitudGrupoInvestigacion.objects.filter(Q(status=True),(Q(estado=variable_valor('SOLICITADO_GRUPO_INVESTIGACION'))|Q(estado=variable_valor('APROBADO_GRUPO_INVESTIGACION'))|
                                                                    Q(estado=variable_valor('RECHAZADO_GRUPO_INVESTIGACION')) | Q(estado=variable_valor('PENDIENTE_GRUPO_INVESTIGACION')))).distinct().order_by('estado','-fecha_creacion')
            paging = MiPaginador(grupos, 20)
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
            data['cabeceras'] = page.object_list
            data['creado'] = variable_valor('CREADO_GRUPO_INVESTIGACION')
            data['pendiente'] = variable_valor('PENDIENTE_GRUPO_INVESTIGACION')
            data['solicitado'] = variable_valor('SOLICITADO_GRUPO_INVESTIGACION')
            data['aprobado'] = variable_valor('APROBADO_GRUPO_INVESTIGACION')
            return render(request, 'adm_solicitudaprobacioninvestigacion/aprobar_inv.html', data)
