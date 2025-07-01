# -*- coding: UTF-8 -*-
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from bd.forms import *
from matricula.models import EstadoRetiroMatricula
from sga.commonviews import adduserdata
from django.db import connection, transaction
from sga.funciones import log, puede_realizar_accion, MiPaginador


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    try:
        puede_realizar_accion(request, 'bd.puede_acceder_estado_retiro_matricula')
    except Exception as ex:
        return HttpResponseRedirect(f"/?info={ex.__str__()}")
    adduserdata(request, data)
    persona = request.session['persona']

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                puede_realizar_accion(request, 'bd.puede_agregar_estado_retiro_matricula')
                f = EstadoRetiroMatriculaForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                eEstadoRetiroMatricula = EstadoRetiroMatricula(nombre=f.cleaned_data['nombre'],
                                                               editable=f.cleaned_data['editable'],
                                                               color=f.cleaned_data['color'],
                                                               accion=f.cleaned_data['accion'],
                                                               )
                eEstadoRetiroMatricula.save(request)
                log(u'Adiciono estado de retiro matricula: %s' % eEstadoRetiroMatricula, request, "add")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'edit':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_estado_retiro_matricula')
                f = EstadoRetiroMatriculaForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if not EstadoRetiroMatricula.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Estado a editar no encontrado")
                eEstadoRetiroMatricula = EstadoRetiroMatricula.objects.get(pk=request.POST['id'])
                eEstadoRetiroMatricula.nombre = f.cleaned_data['nombre']
                eEstadoRetiroMatricula.editable = f.cleaned_data['editable']
                eEstadoRetiroMatricula.color = f.cleaned_data['color']
                eEstadoRetiroMatricula.accion = f.cleaned_data['accion']
                eEstadoRetiroMatricula.save(request)
                log(u'Edito estado de retiro matricula: %s' % eEstadoRetiroMatricula, request, "edit")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'del':
            try:
                puede_realizar_accion(request, 'bd.puede_eliminar_estado_retiro_matricula')
                if not EstadoRetiroMatricula.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Estado a eliminar no encontrado")
                eDelete = eEstadoRetiroMatricula = EstadoRetiroMatricula.objects.get(pk=request.POST['id'])
                if eEstadoRetiroMatricula.en_uso():
                    raise NameError(u"Motivo en uso")
                eEstadoRetiroMatricula.delete()
                log(u'Elimino estado de retiro matricula: %s' % eDelete, request, "del")
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
                    puede_realizar_accion(request, 'bd.puede_agregar_estado_retiro_matricula')
                    data['title'] = u'Adicionar estado de retiro matricula'
                    f = EstadoRetiroMatriculaForm()
                    data['form'] = f
                    return render(request, "adm_sistemas/remove_enroll_state/add.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'edit':
                try:
                    puede_realizar_accion(request, 'bd.puede_modificar_estado_retiro_matricula')
                    data['title'] = u'Editar estado de retiro matricula'
                    if not EstadoRetiroMatricula.objects.filter(pk=request.GET['id']).exists():
                        raise NameError(u"Estado a editar no encontrado")
                    data['eEstadoRetiroMatricula'] = eEstadoRetiroMatricula = EstadoRetiroMatricula.objects.get(pk=request.GET['id'])
                    f = EstadoRetiroMatriculaForm()
                    f.set_initial(eEstadoRetiroMatricula)
                    data['form'] = f
                    return render(request, "adm_sistemas/remove_enroll_state/edit.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Admininistración de Estados de Retiro de Matrícula'
                search = None
                ids = None
                estados = EstadoRetiroMatricula.objects.filter(status=True)
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
                return render(request, "adm_sistemas/remove_enroll_state/view.html", data)
            except Exception as ex:
                pass
