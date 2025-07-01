# -*- coding: UTF-8 -*-

import json
from datetime import datetime
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from decorators import secure_module, last_access
from sagest.models import Producto, OrdenPedido, Departamento, DetalleOrdenPedido, InventarioReal, HdIncidente, \
    OrdenTrabajo, DistributivoPersona, ESTADO_ORDEN_PEDIDO
from sga.models import Notificacion, Modulo
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import log, MiPaginador, puede_realizar_accion, null_to_decimal, generar_codigo
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, add_tabla_reportlab, generar_pdf_reportlab, \
    add_titulo_reportlab, add_graficos_barras_reportlab, add_graficos_circular_reporlab
from sagest.commonviews import secuencia_ordentrabajo


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'ViewedNotification':
            try:
                id = request.POST['id'] if 'id' in request.POST and request.POST['id'] else 0
                notificacion = Notificacion.objects.get(pk=id)
                if not notificacion:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos"})

                notificacion.leido = True
                notificacion.visible = False
                notificacion.fecha_hora_leido = datetime.now()
                notificacion.save(request)
                log(u'Leo el mensaje: %s' % notificacion, request, "edit")
                return JsonResponse({"result": "ok", 'mensaje': u'Notificación vista'})
            except Exception as ex:
                return JsonResponse({"result": "bad","mensaje": u"Error al cargar los datos %s"  % ex.__str__()})

        if action == 'ViewedNotificationModule':
            try:
                idp = request.POST['idp'] if 'idp' in request.POST and request.POST['idp'] else 0
                idm = request.POST['idm'] if 'idm' in request.POST and request.POST['idm'] else 0
                if not Modulo.objects.values("id").filter(pk=idm).exists():
                    return 0
                eModulo = Modulo.objects.get(pk=idm)
                notificaciones = Notificacion.objects.filter(modulo=eModulo, destinatario_id=persona.id, perfil_id=idp, leido=False, visible=True, fecha_hora_visible__gte=datetime.now())
                for notificacion in notificaciones:
                    notificacion.leido = True
                    notificacion.visible = False
                    notificacion.fecha_hora_leido = datetime.now()
                    notificacion.save(request)
                    log(u'Leo el mensaje: %s' % notificacion, request, "edit")
                return JsonResponse({"result": "ok", 'mensaje': u'Notificación vista'})
            except Exception as ex:
                return JsonResponse({"result": "bad","mensaje": u"Error al cargar los datos %s"  % ex.__str__()})

        if action == 'delnotificacion':
            try:
                with transaction.atomic():
                    instancia = Notificacion.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino notificación: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            return HttpResponseRedirect(request.path)
        else:
            try:
                search = None
                ids = None
                tipoentrada = request.session['tiposistema'] if 'tiposistema' in request.session else None
                notificaciones = Notificacion.objects.filter(destinatario=persona,status=True).order_by('leido', 'prioridad')
                if tipoentrada and tipoentrada in ['empresa', 'empleo']:
                    notificaciones = notificaciones.filter(app_label__icontains=tipoentrada)
                if 's' in request.GET:
                    search = request.GET['s']
                    if search:
                        notificaciones = notificaciones.filter((Q(titulo__icontains=search) |
                                                               Q(cuerpo__icontains=search)),status=True)
                if 'id' in request.GET:
                    ids = request.GET['id']
                    if ids:
                        notificaciones = notificaciones.filter(id=ids)
                visible = 0
                if 'visible' in request.GET and int(request.GET['visible']) > 0:
                    visible = int(request.GET['visible'])
                    notificaciones = notificaciones.filter(leido=int(request.GET['visible']) == 1,status=True)
                prioridad = 0
                if 'prioridad' in request.GET and int(request.GET['prioridad']) > 0:
                    prioridad = int(request.GET['prioridad'])
                    notificaciones = notificaciones.filter(prioridad=prioridad,status=True)
                paging = MiPaginador(notificaciones.order_by('-id'), 25)
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
                data['obj_notificaciones'] = page.object_list
                data['visible'] = visible
                data['prioridad'] = prioridad
                data['title'] = u'Notificaciones'
                if tipoentrada and tipoentrada in ['empresa', 'empleo']:
                    return render(request, "notificacion/notificacion_empleo.html", data)
                return render(request, "notificacion/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect("/")
