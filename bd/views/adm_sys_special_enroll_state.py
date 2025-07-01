# -*- coding: UTF-8 -*-
from django.contrib import messages
from django.contrib.admin.models import LogEntry, ADDITION, DELETION
from django.contrib.admin.utils import unquote
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction, router
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils.encoding import force_str

from bd.models import LogQuery, get_deleted_objects, LogEntryLogin
from decorators import secure_module
from bd.forms import *
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
import sys
from django.template.loader import get_template
from sga.funciones import log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery, convertir_fecha, \
    resetear_clave, MiPaginador
from sga.models import Persona, LogEntryBackup, LogEntryBackupdos, AgregacionEliminacionMaterias, Inscripcion, Modulo, \
    ModuloGrupo
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    try:
        puede_realizar_accion(request, 'bd.puede_acceder_estado_matricula_especial')
    except Exception as ex:
        return HttpResponseRedirect(f"/?info={ex.__str__()}")
    adduserdata(request, data)
    persona = request.session['persona']

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                puede_realizar_accion(request, 'bd.puede_agregar_estado_matricula_especial')
                f = EstadoMatriculaEspecialForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                eEstadoMatriculaEspecial = EstadoMatriculaEspecial(nombre=f.cleaned_data['nombre'],
                                                                   editable=f.cleaned_data['editable'],
                                                                   color=f.cleaned_data['color'],
                                                                   accion=f.cleaned_data['accion'],
                                                                   )
                eEstadoMatriculaEspecial.save(request)
                log(u'Adiciono estado de matricula especial: %s' % eEstadoMatriculaEspecial, request, "add")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'edit':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_estado_matricula_especial')
                f = EstadoMatriculaEspecialForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if not EstadoMatriculaEspecial.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Estado a editar no encontrado")
                eEstadoMatriculaEspecial = EstadoMatriculaEspecial.objects.get(pk=request.POST['id'])
                eEstadoMatriculaEspecial.nombre = f.cleaned_data['nombre']
                eEstadoMatriculaEspecial.editable = f.cleaned_data['editable']
                eEstadoMatriculaEspecial.color = f.cleaned_data['color']
                eEstadoMatriculaEspecial.accion = f.cleaned_data['accion']
                eEstadoMatriculaEspecial.save(request)
                log(u'Edito estado de matricula especial: %s' % eEstadoMatriculaEspecial, request, "edit")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'del':
            try:
                puede_realizar_accion(request, 'bd.puede_eliminar_estado_matricula_especial')
                if not EstadoMatriculaEspecial.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Estado a eliminar no encontrado")
                eDelete = eEstadoMatriculaEspecial = EstadoMatriculaEspecial.objects.get(pk=request.POST['id'])
                if eEstadoMatriculaEspecial.en_uso():
                    raise NameError(u"Motivo en uso")
                eEstadoMatriculaEspecial.delete()
                log(u'Elimino estado de matrícula especial: %s' % eDelete, request, "del")
                messages.add_message(request, messages.SUCCESS, f'Se elimino correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el registro."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    puede_realizar_accion(request, 'bd.puede_agregar_estado_matricula_especial')
                    data['title'] = u'Adicionar estado de matrícula especial'
                    f = EstadoMatriculaEspecialForm()
                    data['form'] = f
                    return render(request, "adm_sistemas/especial_enroll_state/add.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'edit':
                try:
                    puede_realizar_accion(request, 'bd.puede_modificar_estado_matricula_especial')
                    data['title'] = u'Editar estado de matrícula especial'
                    if not EstadoMatriculaEspecial.objects.filter(pk=request.GET['id']).exists():
                        raise NameError(u"Estado a editar no encontrado")
                    data['eEstadoMatriculaEspecial'] = eEstadoMatriculaEspecial = EstadoMatriculaEspecial.objects.get(pk=request.GET['id'])
                    f = EstadoMatriculaEspecialForm()
                    f.set_initial(eEstadoMatriculaEspecial)
                    data['form'] = f
                    return render(request, "adm_sistemas/especial_enroll_state/edit.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Admininistración de Estados de Matrícula Especial'
                search = None
                ids = None
                estados = EstadoMatriculaEspecial.objects.filter(status=True)
                if 'id' in request.GET:
                    ids = request.GET['id']
                    estados = estados.filter(id=int(ids))
                if 's' in request.GET:
                    search = request.GET['s']
                    estados = estados.filter(Q(nombre__icontains=search)).distinct()
                paging = MiPaginador(estados, 25)
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
                data['estados'] = page.object_list
                return render(request, "adm_sistemas/especial_enroll_state/view.html", data)
            except Exception as ex:
                pass
