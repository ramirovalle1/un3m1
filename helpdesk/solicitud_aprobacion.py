# -*- coding: UTF-8 -*-
import json
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max
from django.db.models import Q
from django.template.context import Context
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from decorators import secure_module
from helpdesk.forms import HdPlanAprobacionForm, HdPlanificacionArchivoForm
from helpdesk.models import HdPlanAprobacion
from sagest.models import AnioEjercicio
from settings import EMAIL_DOMAIN, PUESTO_ACTIVO_ID
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, convertir_fecha, generar_nombre, convertir_fecha_invertida, variable_valor
from sga.models import miinstitucion, CUENTAS_CORREOS
from sga.tasks import send_html_mail, conectar_cuenta


# @login_required(redirect_field_name='ret', login_url='/loginsagest')
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addsolicitud':
            try:
                f = HdPlanAprobacionForm(request.POST, request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext == '.pdf':
                            if not ext == '.PDF':
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        if newfile.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                        if newfile:
                            newfile._name = generar_nombre("Planificacion", newfile._name)
                else:

                    return JsonResponse({"result": "bad", "mensaje": u"Error, debe subir un archivo."})

                if f.is_valid():
                    permiso = HdPlanAprobacion(
                        periodo_id=int(request.POST['periodo']),
                        solicita=persona,
                        fecharegistro=f.cleaned_data['fecharegistro'],
                        estadoaprobacion=1,
                        solicitarevision=f.cleaned_data['solicitarevision'],
                        observacion=f.cleaned_data['observacion'],
                        )

                    permiso.save(request)
                    if newfile:
                        permiso.archivo = newfile
                        permiso.save(request)
                    # send_html_mail("Solicitud de Revisión de Planificación[%s]" % permiso.solicita, "emails/permisosolicita.html", {'sistema': request.session['nombresistema'], 'codificacion': permiso.codificacion(), 'responsable': permiso.unidadorganica.responsable, 'solicita': permiso.solicita, 't': miinstitucion()}, permiso.unidadorganica.responsable.lista_emails_interno(), [], cuenta=CUENTAS_CORREOS[1][1])
                    log(u'Adiciono nueva Solicitud de Revisión de Planificación: %s' % permiso, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editsolicitud':
            try:
                f = HdPlanAprobacionForm(request.POST, request.FILES)
                newfile = None
                permiso = HdPlanAprobacion.objects.get(pk=int(request.POST['id']))
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext == '.pdf':
                            if not ext == '.PDF':
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        if newfile.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                        if newfile:
                            newfile._name = generar_nombre("Planificacion", newfile._name)
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, debe subir un archivo."})

                if f.is_valid():
                    permiso.periodo_id = int(request.POST['periodo'])
                    permiso.solicita = persona
                    permiso.fecharegistro = f.cleaned_data['fecharegistro']
                    permiso.estadoaprobacion = f.cleaned_data['estadoaprobacion']
                    permiso.solicitarevision = f.cleaned_data['solicitarevision']
                    permiso.observacion = f.cleaned_data['observacion']
                    permiso.save(request)
                    if newfile:
                        permiso.archivo = newfile
                        permiso.save(request)
                    log(u'Modifico Solicitud de Revisión de Planificación: %s' % permiso, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delsolicitud':
            try:
                permiso = HdPlanAprobacion.objects.get(pk=request.POST['id'])
                permiso.status = False
                permiso.save()
                log(u'Elimino Solicitud de Revisión de Planificación: %s' % permiso, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al elminar los datos."})




        elif action == 'addarchivo':
            try:
                f = HdPlanAprobacionForm(request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext == '.pdf':
                            if not ext == '.PDF':
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        if newfile.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                        if newfile:
                            newfile._name = generar_nombre("Solicitud", newfile._name)
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, debe subir un archivo."})

                if f.is_valid():
                    permiso = HdPlanAprobacion.objects.get(pk=int(request.POST['id']))
                    permiso.archivo = newfile
                    permiso.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addsolicitud':
                try:
                    data['title'] = u'Solicitar  Revisión de Planificación'
                    form = HdPlanAprobacionForm(initial={'fechasolicitud': datetime.now().date()})
                    data['form'] = form
                    return render(request, "helpdesk_solicitud/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'editsolicitud':
                try:
                    data['title'] = u'Solicita Revisión de Planificación'
                    data['solicitud'] = permiso = HdPlanAprobacion.objects.get(pk=int(request.GET['id']))
                    form = HdPlanAprobacionForm(initial={'fecharegistro': permiso.fecharegistro,
                                                             'estadoaprobacion': permiso.estadoaprobacion,
                                                             # 'solicitarevision': permiso.solicitarevision,
                                                             'periodo': permiso.periodo_id,
                                                             'observacion': permiso.observacion,
                                                             })
                    form.editar(permiso.periodo)
                    data['form'] = form
                    return render(request, "helpdesk_solicitud/editsolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'delsolicitud':
                try:
                    data['title'] = u'Eliminar   Solicitud Revisión de Planificación'
                    data['solicitud'] = HdPlanAprobacion.objects.get(pk=int(request.GET['id']))
                    return render(request, "helpdesk_solicitud/delsolicitud.html", data)
                except:
                    pass
            elif action == 'buscarperiodo':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if s.__len__() == 1:
                        # activo = ActivoFijo.objects.filter(Q(codigogobierno__icontains=q) | Q(codigointerno__icontains=s[0]) | Q(serie__icontains=q),status=True, catalogo__equipoelectronico=True if tipo == 2 else False).distinct()[:20]
                        anio = AnioEjercicio.objects.filter(
                            Q(anioejercicio__icontains=s[0]), status=True).distinct()[:20]
                    else:
                        anio = AnioEjercicio.objects.filter(
                            Q(anioejercicio__icontains=s[1])).filter(
                            status=True).distinct()[:20]

                    data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_repr()} for x in anio]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass
            elif action == 'detalle':
                try:
                    data = {}
                    detalle = HdPlanAprobacion.objects.get(pk=int(request.GET['id']))
                    data['solicitud'] = detalle
                    data['aprobadores'] = detalle.hdaprobarsolicitud_set.all()
                    template = get_template("helpdesk_solicitud/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})



            return HttpResponseRedirect(request.path)
        else:
            # if not DistributivoPersona.objects.filter(persona=persona):
            #     return HttpResponseRedirect('/?info=Ud. no tiene asignado un cargo.')
            data['title'] = u'Solicitud Revisión de Planificación'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
            if search:
                plantillas = HdPlanAprobacion.objects.select_related().filter(status=True, solicita=persona).filter(
                    Q() |
                    Q(solicita__cedula__icontains=search) |
                    Q(solicita__pasaporte__icontains=search)).distinct().order_by('-fecharegistro')
            elif 'id' in request.GET:
                ids = request.GET['id']
                plantillas = HdPlanAprobacion.objects.select_related().filter(id=ids, solicita=persona)
            else:
                plantillas = HdPlanAprobacion.objects.select_related().filter(status=True,
                                                                                  solicita=persona).order_by(
                    '-fecharegistro')
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
            data['form2'] = HdPlanificacionArchivoForm()
            return render(request, 'helpdesk_solicitud/view.html', data)



