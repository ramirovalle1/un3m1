# -*- coding: UTF-8 -*-
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from bd.forms import *
from sga.commonviews import adduserdata
from django.db import connection, transaction
from sga.funciones import log, puede_realizar_accion, MiPaginador
from matricula.models import MotivoRetiroMatricula


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    try:
        puede_realizar_accion(request, 'bd.puede_acceder_motivo_retiro_matricula')
    except Exception as ex:
        return HttpResponseRedirect(f"/?info={ex.__str__()}")
    adduserdata(request, data)
    persona = request.session['persona']

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addmotivo':
            try:
                puede_realizar_accion(request, 'bd.puede_agregar_motivo_retiro_matricula')
                f = MotivoRetiroMatriculaForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                eMotivoRetiroMatricula = MotivoRetiroMatricula(nombre=f.cleaned_data['nombre'],
                                                               activo=f.cleaned_data['activo'],
                                                               detalle=f.cleaned_data['detalle'],
                                                               tipo=f.cleaned_data['tipo'],
                                                               )
                eMotivoRetiroMatricula.save(request)
                log(u'Adiciono motivo de retiro de matricula: %s' % eMotivoRetiroMatricula, request, "add")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'editmotivo':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_motivo_retiro_matricula')
                f = MotivoRetiroMatriculaForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if not MotivoRetiroMatricula.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Motivo a editar no encontrado")
                eMotivoRetiroMatricula = MotivoRetiroMatricula.objects.get(pk=request.POST['id'])
                eMotivoRetiroMatricula.nombre = f.cleaned_data['nombre']
                eMotivoRetiroMatricula.activo = f.cleaned_data['activo']
                eMotivoRetiroMatricula.tipo = f.cleaned_data['tipo']
                eMotivoRetiroMatricula.detalle = f.cleaned_data['detalle']
                eMotivoRetiroMatricula.save(request)
                log(u'Edito motivo de retiro de matricula: %s' % eMotivoRetiroMatricula, request, "edit")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'delmotivo':
            try:
                puede_realizar_accion(request, 'bd.puede_eliminar_motivo_retiro_matricula')
                if not MotivoRetiroMatricula.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Proceso a editar no encontrado")
                eDelete = eMotivoRetiroMatricula = MotivoRetiroMatricula.objects.get(pk=request.POST['id'])
                if eMotivoRetiroMatricula.en_uso():
                    raise NameError(u"Motivo en uso")
                eMotivoRetiroMatricula.delete()
                log(u'Elimino motivo de matrícula especial: %s' % eDelete, request, "del")
                messages.add_message(request, messages.SUCCESS, f'Se elimino correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el registro."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addmotivo':
                try:
                    puede_realizar_accion(request, 'bd.puede_agregar_motivo_retiro_matricula')
                    data['title'] = u'Adicionar motivo de matrícula especial'
                    f = MotivoRetiroMatriculaForm()
                    data['form'] = f
                    return render(request, "adm_sistemas/remove_enroll_reason/addmotivo.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'editmotivo':
                try:
                    puede_realizar_accion(request, 'bd.puede_modificar_motivo_retiro_matricula')
                    data['title'] = u'Editar motivo de matrícula especial'
                    if not MotivoRetiroMatricula.objects.filter(pk=request.GET['id']).exists():
                        raise NameError(u"Motivo a editar no encontrado")
                    data['eMotivoRetiroMatricula'] = eMotivoRetiroMatricula = MotivoRetiroMatricula.objects.get(pk=request.GET['id'])
                    f = MotivoRetiroMatriculaForm()
                    f.set_initial(eMotivoRetiroMatricula)
                    data['form'] = f
                    return render(request, "adm_sistemas/remove_enroll_reason/editmotivo.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Admininistración de Motivos de Retiro de Asignatura o Matrícula'
                search = None
                ids = None
                motivos = MotivoRetiroMatricula.objects.filter(status=True)
                if 'id' in request.GET:
                    ids = request.GET['id']
                    motivos = motivos.filter(id=int(ids))
                if 's' in request.GET:
                    search = request.GET['s']
                    motivos = motivos.filter(Q(nombre__icontains=search)).distinct()
                paging = MiPaginador(motivos, 25)
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
                data['motivos'] = page.object_list
                return render(request, "adm_sistemas/remove_enroll_reason/view.html", data)
            except Exception as ex:
                pass
