# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from sagest.forms import ProveedorForm, ModuloForm, PrioridadForm, ReqHistoriaForm, ReqHistoriaActividadForm, ResponsableForm
from sagest.models import Proveedor, ReqHistoria, ReqActividad, ReqPrioridad, \
    DistributivoPersona, ReqHistoriaActividad
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, puede_realizar_accion, generar_nombre, convertir_fecha
from django.forms import model_to_dict
from datetime import datetime
from django.template.loader import get_template
from django.template import Context

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    persona = request.session['persona']
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addhistoria':
            try:
                form = ReqHistoriaForm(request.POST, request.FILES)
                newfile=None
                if form.is_valid():
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("historiarequerimiento_", newfile._name)
                    distributivo = DistributivoPersona.objects.filter(status=True, persona=persona)[0]
                    historia = ReqHistoria(sistema=form.cleaned_data['sistema'],
                                           solicita=distributivo.persona,
                                           fecha=datetime.now().date(),
                                           denominacionpuesto=distributivo.denominacionpuesto if distributivo.denominacionpuesto else None,
                                           departamento=distributivo.unidadorganica if distributivo.unidadorganica else None,
                                           asunto=form.cleaned_data['asunto'],
                                           cuerpo=form.cleaned_data['cuerpo'],
                                           estado=1,
                                           archivo=newfile)
                    historia.save(request)
                    for x in ReqActividad.objects.filter(status=True, vigente=True):
                        historiaactividad = ReqHistoriaActividad(historia=historia,
                                                                 actividad=x,
                                                                 )
                        historiaactividad.save()
                    log(u'Agrego una nueva historia: %s' % historia, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edithistoria':
            try:
                form = ReqHistoriaForm(request.POST, request.FILES)
                newfile=None
                if form.is_valid():
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("historiarequerimiento_", newfile._name)
                    historia = ReqHistoria.objects.get(id=request.POST['id'])
                    historia.sistema=form.cleaned_data['sistema']
                    historia.asunto=form.cleaned_data['asunto']
                    historia.cuerpo=form.cleaned_data['cuerpo']
                    historia.archivo=newfile
                    historia.save(request)
                    log(u'edito historia: %s' % historia, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'adddetalle':
            try:
                distributivo=None
                actividad=None
                historia = ReqHistoria.objects.get(id=int(request.POST['idd']))
                if request.POST['id_responsable']:
                    distributivo = DistributivoPersona.objects.get(id=int(request.POST['id_responsable']))
                if request.POST['id_actividad']:
                    actividad=ReqActividad.objects.get(id=int(request.POST['id_actividad']))
                actividaddet = ReqHistoriaActividad(
                    historia=historia,
                    descripcion = request.POST['id_descripcion'] if request.POST['id_descripcion'] else None,
                    actividad =  actividad,
                    fechainicio =convertir_fecha(request.POST['id_fechainicio']) if request.POST['id_fechainicio'] else None,
                    fechafin = convertir_fecha(request.POST['id_fechafin']) if request.POST['id_fechafin'] else None,
                    responsable = distributivo.persona,
                    estado = int(request.POST['id_estado']) if request.POST['id_estado'] else None
                )
                actividaddet.save(request)
                log(u'agrego actividad  %s %s' % (actividaddet, persona), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al editar los datos."})

        elif action == 'editardetalle':
            try:
                actividaddet = ReqHistoriaActividad.objects.get(id=int(request.POST['idd']))
                if request.POST['id_responsable']:
                    distributivo = DistributivoPersona.objects.get(id=int(request.POST['id_responsable']))
                    actividaddet.responsable=distributivo.persona
                actividaddet.estado=int(request.POST['id_estado']) if request.POST['id_estado'] else actividaddet.estado
                actividaddet.fechainicio=convertir_fecha(request.POST['id_fechainicio']) if request.POST['id_fechainicio'] else actividaddet.fechainicio
                actividaddet.fechafin=convertir_fecha(request.POST['id_fechafin']) if request.POST['id_fechafin'] else actividaddet.fechafin
                actividaddet.descripcion=request.POST['id_descripcion'] if request.POST['id_descripcion'] else actividaddet.descripcion
                actividaddet.save(request)
                log(u'edito actividad  %s %s' % (actividaddet, persona), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al editar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addhistoria':
                try:
                    data['title'] = u'Adicionar historia'
                    form= ReqHistoriaForm()
                    form.adicionarexperto()
                    data['form'] = form
                    return render(request, "experto_requerimiento/addhistoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'edithistoria':
                try:
                    data['title'] = u'Editar historia'
                    data['historia'] = historia = ReqHistoria.objects.get(pk=request.GET['id'])
                    distributivo = historia.solicita.distributivopersona_set.filter(status=True)[0]
                    form = ReqHistoriaForm(initial={'sistema':historia.sistema, 'asunto' :historia.asunto, 'cuerpo':historia.cuerpo, 'prioridad': historia.prioridad})
                    form.adicionarexperto()
                    data['form'] = form
                    return render(request, "experto_requerimiento/edithistoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletehistoria':
                try:
                    data['title'] = u'Eliminar historia'
                    data['historia'] = ReqHistoria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_proveedores/../templates/adm_requerimiento/inactivatehistoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'editardetalle':
                try:
                    id = int(request.GET['idd'])
                    actividaddet = ReqHistoriaActividad.objects.get(id=id)
                    data = {"result": "ok",
                            "responsable": actividaddet.responsable.id if actividaddet.responsable else None,
                            "actividad": actividaddet.actividad.id if actividaddet.actividad else None,
                            "estado": actividaddet.estado if actividaddet.estado else None,
                            "fechainicio": actividaddet.fechainicio.date() if actividaddet.fechainicio else None,
                            "fechafin": actividaddet.fechafin.date() if actividaddet.fechafin else None,
                            "descripcion": actividaddet.descripcion if actividaddet.descripcion else None}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'detalle':
                try:
                    data = {}
                    data['historia'] =historia = ReqHistoria.objects.get(pk=int(request.GET['id']))
                    data['actividades'] = ReqHistoriaActividad.objects.filter(status=True, historia=historia).order_by('actividad')
                    template = get_template("experto_requerimiento/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u'Requerimientos Solicitados'
            search = None
            ids = None
            historias = ReqHistoria.objects.filter(status=True, solicita=persona)
            if 's' in request.GET:
                search = request.GET['s']
                search = request.GET['s']
                ss = search.split(' ')
                while '' in ss:
                    ss.remove('')
                if len(ss) == 1:
                    historias = historias.filter(Q(responsable__nombres__icontains=search) |
                                                 Q(responsable__apellido1__icontains=search) |
                                                 Q(responsable__apellido2__icontains=search) |
                                                 Q(responsable__cedula__icontains=search) |
                                                 Q(responsable__pasaporte__icontains=search) |
                                                 Q(solicita__nombres__icontains=search) |
                                                 Q(solicita__apellido1__icontains=search) |
                                                 Q(solicita__apellido2__icontains=search) |
                                                 Q(solicita__cedula__icontains=search) |
                                                 Q(solicita__pasaporte__icontains=search) |
                                                 Q(asunto__icontains=search))
                else:
                    historias = historias.filter(Q(responsable__apellido1__icontains=ss[0]) |
                                                 Q(responsable__apellido2__icontains=ss[1]) |
                                                 Q(responsable__cedula__icontains=ss[0]) |
                                                 Q(responsable__cedula__icontains=ss[1]) |
                                                 Q(responsable__pasaporte__icontains=ss[0]) |
                                                 Q(responsable__pasaporte__icontains=ss[1]) |
                                                 Q(solicita__apellido1__icontains=ss[0]) |
                                                 Q(solicita__apellido2__icontains=ss[1]) |
                                                 Q(solicita__cedula__icontains=ss[0]) |
                                                 Q(solicita__cedula__icontains=ss[1]) |
                                                 Q(solicita__pasaporte__icontains=ss[0]) |
                                                 Q(solicita__pasaporte__icontains=ss[1]) |
                                                 Q(asunto__icontains=ss[0]) |
                                                 Q(asunto__icontains=ss[1]))
            elif 'id' in request.GET:
                ids = request.GET['id']
                historias = historias.filter(id=ids, solicita=persona)
            paging = MiPaginador(historias, 20)
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
            data['historias'] = page.object_list
            data['form2'] = ResponsableForm()
            return render(request, "experto_requerimiento/view.html", data)
