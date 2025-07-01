# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from settings import SOLICITUD_NUMERO_AUTOMATICO, PERMITE_ALUMNO_REGISTRAR, SECRETARIA_GROUP_ID
from sga.commonviews import adduserdata
from sga.forms import SolicitudSecretariaDocenteForm, RespuestaSolicitudSecretariaDocenteForm
from sga.funciones import generar_nombre, MiPaginador, log
from sga.models import SolicitudSecretariaDocente, TipoSolicitudSecretariaDocente, HistorialSolicitud, Persona


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'solicitar':
                try:
                    form = SolicitudSecretariaDocenteForm(request.POST, request.FILES)
                    if form.is_valid():
                        if inscripcion.adeuda_a_la_fecha():
                            return JsonResponse({"result": "bad", "mensaje": u"Tiene valores pendientes de pago,los cuales debe cancelar primero."})
                        newfile = None
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("documentosolicitud_", newfile._name)
                        responsable = None
                        if Persona.objects.filter(usuario__groups__in=Group.objects.filter(id=SECRETARIA_GROUP_ID), usuario__is_active=True).exists():
                            responsable = Persona.objects.filter(usuario__groups__in=Group.objects.filter(id=SECRETARIA_GROUP_ID), usuario__is_active=True)[0]
                        solicitud = SolicitudSecretariaDocente(fecha=datetime.now().date(),
                                                               hora=datetime.now().time(),
                                                               persona=persona,
                                                               tipo=form.cleaned_data['tipo'],
                                                               descripcion=form.cleaned_data['descripcion'],
                                                               cerrada=False,
                                                               responsable=responsable,
                                                               archivo=newfile)
                        solicitud.save(request)
                        historial = HistorialSolicitud(solicitud=solicitud,
                                                       fecha=datetime.now(),
                                                       persona=solicitud.responsable)
                        historial.save(request)
                        if SOLICITUD_NUMERO_AUTOMATICO:
                            if SolicitudSecretariaDocente.objects.filter(numero_tramite__gt=0).exists():
                                ultima = SolicitudSecretariaDocente.objects.filter(numero_tramite__gt=0).order_by('-id')[0]
                                solicitud.numero_tramite = ultima.numero_tramite + 1
                            else:
                                solicitud.numero_tramite = 1
                            solicitud.save(request)
                        log(u'Alumno solicito: %s [%s]' % (solicitud, solicitud.id), request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'valorsolicitud':
                try:
                    tipo = TipoSolicitudSecretariaDocente.objects.get(pk=request.POST['id'])
                    return JsonResponse({"result": "ok", "valor": tipo.valor, "informacion": tipo.descripcion, 'costo_base': tipo.costo_base, 'costo_unico': tipo.costo_unico})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'solicitar':
                try:
                    data['title'] = u'Nueva solicitud'
                    form = SolicitudSecretariaDocenteForm(initial={'cantidad': 1})
                    form.editar()
                    data['form'] = form
                    return render(request, "alu_solicitudes/solicitar.html", data)
                except Exception as ex:
                    pass

            if action == 'consulta':
                try:
                    data['title'] = u'Consultar solicitud'
                    solicitud = SolicitudSecretariaDocente.objects.get(pk=request.GET['id'])
                    form = RespuestaSolicitudSecretariaDocenteForm(initial={'solicitud': solicitud.descripcion,
                                                                            'descripcion': solicitud.respuesta})
                    data['form'] = form
                    data['permite_modificar'] = False
                    return render(request, "alu_solicitudes/consulta.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Solicitudes'
            solicitudes = SolicitudSecretariaDocente.objects.filter(persona=persona)
            paging = MiPaginador(solicitudes, 30)
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
            data['permite_alumno_registrar'] = PERMITE_ALUMNO_REGISTRAR
            return render(request, "alu_solicitudes/view.html", data)