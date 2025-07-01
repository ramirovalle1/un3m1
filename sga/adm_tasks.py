from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template.loader import get_template
from django.template.context import Context
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import SolRetMatRevisionesForm, ReporteEstudiantesRetiradosForm
from sga.funciones import MiPaginador, generar_nombre, puede_realizar_accion, log
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import SolicitudRetiroMatricula, SolicitudRetiroMatriculaRevision, Matricula, Nivel, Carrera, \
    SolicitudMateriaRetirada, MateriaAsignada
from sga.templatetags.sga_extras import encrypt
from django.core.paginator import Paginator
from clrncelery.models import BatchTasks


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    usuario = request.user
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'LoadTask':
                try:
                    data['batch_task'] = batch_task = BatchTasks.objects.get(pk=request.POST['id'])
                    template = get_template("adm_tasks/progress.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': batch_task.title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos" + ex})

        return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'load_task':
                try:
                    data['batch_task'] = batch_task = BatchTasks.objects.get(pk=request.GET['id'])
                    return render(request, "adm_tasks/progress.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(request.path)

            return HttpResponseRedirect(request.path)
        else:

            try:
                search = None
                ids = None
                tareas = BatchTasks.objects.filter(person=persona).order_by('-fecha_creacion')
                if 's' in request.GET:
                    search = request.GET['s']
                    if search:
                        tareas = tareas.filter(Q(task_name__contains=search) | Q(task_id__icontains=search))
                if 'id' in request.GET:
                    ids = request.GET['id']
                    if ids:
                        tareas = tareas.filter(id=ids)

                paging = MiPaginador(tareas, 25)
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
                data['tareas'] = page.object_list
                #data['title'] = u'Ordenes de Pedidos'
                return render(request, "adm_tasks/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect("/")



