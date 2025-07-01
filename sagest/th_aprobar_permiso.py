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
from sagest.models import PermisoInstitucional, PermisoAprobacion, Departamento, ESTADO_PERMISOS, TipoPermiso, SolicitudJustificacionMarcada,\
    DetalleSolicitudJustificacionMarcada, HistorialSolicitudJustificacionMarcada,LogMarcada
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, notificacion
from datetime import datetime
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
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
                permiso = PermisoInstitucional.objects.get(pk=request.POST['id'])
                aprobar = PermisoAprobacion(permisoinstitucional=permiso,
                                            fechaaprobacion=datetime.now().date(),
                                            observacion=request.POST['obse'],
                                            aprueba=persona,
                                            estadosolicitud=int(request.POST['esta']))
                aprobar.save(request)
                permiso.actulizar_estado(request)
                aprobar.mail_notificar_jefe_departamento(request.session['nombresistema'])
                log(u'Aprobar solicitud(Director): %s' % aprobar, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'aprorechsolicitud':
            try:
                id = int(encrypt(request.POST['id']))
                estado = int(request.POST['estado'])
                if not SolicitudJustificacionMarcada.objects.filter(status=True,pk = id).exists():
                    JsonResponse({'error':True,'mensaje':u'No existe solicitud'})
                soli = SolicitudJustificacionMarcada.objects.get(status=True, pk=encrypt(request.POST['id']))
                soli.estado = estado
                soli.save(request)
                estado = 3 if estado == 2 else estado
                log('Edito el estado de la solicitud %s a estado %s'%(soli.__str__(),soli.estado),request,'edit')
                historial = HistorialSolicitudJustificacionMarcada(
                    solicitud=soli,
                    observacion=request.POST['observacion'],
                    persona=persona,
                    estado=estado,
                    fecha=datetime.now()
                )
                historial.save(request)
                log(u'Agrego historial de solicitud de justificacion de marcadas %s' % (historial.__str__()), request, 'add')
                return JsonResponse({'error':False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "mensaje": u"Solicitud Incorrecta."})
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'verdetalle':
                try:
                    data = {}
                    detalle = PermisoInstitucional.objects.get(pk=int(request.GET['id']))
                    data['permiso'] = detalle
                    data['detallepermiso'] = detalle.permisoinstitucionaldetalle_set.all()
                    data['aprobadores'] = detalle.permisoaprobacion_set.all()
                    template = get_template("th_permiso_institucional/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'detalle':
                try:
                    data = {}
                    detalle = PermisoInstitucional.objects.get(pk=int(request.GET['id']))
                    data['permiso'] = detalle
                    data['detallepermiso'] = detalle.permisoinstitucionaldetalle_set.all()
                    data['aprobador'] = persona
                    data['fecha'] = datetime.now().date()
                    data['aprobadores'] = detalle.permisoaprobacion_set.all()
                    template = get_template("th_permiso_institucional/detalle_aprobar.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action =='justifiacionmarcadas':
                try:
                    url_vars = ''
                    if Departamento.objects.filter(responsable=persona, permisogeneral=True, integrantes__isnull=False).exists():
                        departamento = Departamento.objects.all()
                    else:
                        departamento = Departamento.objects.filter(responsable=persona, integrantes__isnull=False)
                    data['title'] = u'Solicitud de justificación de marcadas'
                    solicitud =SolicitudJustificacionMarcada.objects.filter(status=True,solicita__in=departamento[0].integrantes.values_list('pk',flat=True))
                    if 's' in request.GET:
                        data['s'] = search = request.GET['s']
                        ss = search.split(' ')
                        if len(ss) >1:
                            solicitud = solicitud.filter(Q(solicita__apellido1__icontains = ss[0])&Q(solicita__apellido2__icontains = ss[1]))
                        else:
                            solicitud = solicitud.filter(Q(id__icontains=search) | Q(solicita__apellido1__icontains=search) | Q(solicita__cedula__icontains = search)).distinct()
                        url_vars += f"&s={search}"
                    if 'estado' in request.GET:
                        data['estado'] = estado = int(request.GET['estado'])
                        solicitud = solicitud.filter(estado=estado)
                        url_vars +=f"&estado={estado}"
                    paging = MiPaginador(solicitud, 25)
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
                    data['solicitudes'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request,"th_permiso_institucional/solicitudmarcadas.html",data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Aprobar Permiso Institucional(Director).'
                search = None
                ids = None
                # excluir = [x.id for x in TipoPermiso.objects.filter(status=True, quienaprueba=2)]

                if Departamento.objects.filter(responsable=persona, permisogeneral=True, integrantes__isnull=False).exists():
                    departamento = Departamento.objects.all()
                else:
                    departamento = Departamento.objects.filter(responsable=persona, integrantes__isnull=False)
                plantillas = PermisoInstitucional.objects.filter(status=True,unidadorganica__in=departamento).exclude(Q(solicita=persona)).order_by('-fechasolicitud')
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        plantillas = plantillas.filter(Q(solicita__nombres__icontains=search) |
                                                       Q(solicita__apellido1__icontains=search) |
                                                       Q(solicita__apellido2__icontains=search) |
                                                       Q(solicita__cedula__icontains=search) |
                                                       Q(solicita__pasaporte__icontains=search)).distinct().order_by('-fechasolicitud')
                    else:
                        plantillas = plantillas.filter(Q(solicita__apellido1__icontains=ss[0]) & Q(solicita__apellido2__icontains=ss[1])).distinct().order_by('-fechasolicitud')
                if 'ids' in request.GET:
                    ids = int(request.GET['ids'])
                    if ids > 0:
                        plantillas = plantillas.filter(estadosolicitud=ids).distinct().order_by('-fechasolicitud')
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
                data['permisos'] = page.object_list
                data['email_domain'] = EMAIL_DOMAIN
                data['solicitudes'] = ESTADO_PERMISOS
                return render(request, 'th_permiso_institucional/aprobar_director.html', data)
            except Exception as ex:
                pass