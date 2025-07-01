# -*- coding: UTF-8 -*-
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils.encoding import force_str

from bd.models import LogQuery, get_deleted_objects, LogEntryLogin
from decorators import secure_module
from bd.forms import *
from sga.commonviews import adduserdata
from django.db import connection, transaction
from sga.funciones import log, puede_realizar_accion, MiPaginador


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    try:
        puede_realizar_accion(request, 'bd.puede_acceder_motivo_matricula_especial')
    except Exception as ex:
        return HttpResponseRedirect(f"/?info={ex.__str__()}")
    adduserdata(request, data)
    persona = request.session['persona']

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addmotivo':
            try:
                puede_realizar_accion(request, 'bd.puede_agregar_motivo_matricula_especial')
                f = MotivoMatriculaEspecialForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                eMotivoMatriculaEspecial = MotivoMatriculaEspecial(nombre=f.cleaned_data['nombre'],
                                                                   activo=f.cleaned_data['activo'],
                                                                   detalle=f.cleaned_data['detalle'],
                                                                   tipo=f.cleaned_data['tipo'],
                                                                   )
                eMotivoMatriculaEspecial.save(request)
                log(u'Adiciono motivo de matricula especial: %s' % eMotivoMatriculaEspecial, request, "add")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'editmotivo':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_motivo_matricula_especial')
                f = MotivoMatriculaEspecialForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if not MotivoMatriculaEspecial.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Motivo a editar no encontrado")
                eMotivoMatriculaEspecial = MotivoMatriculaEspecial.objects.get(pk=request.POST['id'])
                eMotivoMatriculaEspecial.nombre = f.cleaned_data['nombre']
                eMotivoMatriculaEspecial.activo = f.cleaned_data['activo']
                eMotivoMatriculaEspecial.tipo = f.cleaned_data['tipo']
                eMotivoMatriculaEspecial.detalle = f.cleaned_data['detalle']
                eMotivoMatriculaEspecial.save(request)
                log(u'Edito motivo de matricula especial: %s' % eMotivoMatriculaEspecial, request, "edit")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'delmotivo':
            try:
                puede_realizar_accion(request, 'bd.puede_eliminar_motivo_matricula_especial')
                if not MotivoMatriculaEspecial.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Proceso a editar no encontrado")
                eDelete = eMotivoMatriculaEspecial = MotivoMatriculaEspecial.objects.get(pk=request.POST['id'])
                if eMotivoMatriculaEspecial.en_uso():
                    raise NameError(u"Motivo en uso")
                eMotivoMatriculaEspecial.delete()
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
                    puede_realizar_accion(request, 'bd.puede_agregar_motivo_matricula_especial')
                    data['title'] = u'Adicionar motivo de matrícula especial'
                    f = MotivoMatriculaEspecialForm()
                    data['form'] = f
                    return render(request, "adm_sistemas/especial_enroll_reason/addmotivo.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'editmotivo':
                try:
                    puede_realizar_accion(request, 'bd.puede_modificar_motivo_matricula_especial')
                    data['title'] = u'Editar motivo de matrícula especial'
                    if not MotivoMatriculaEspecial.objects.filter(pk=request.GET['id']).exists():
                        raise NameError(u"Motivo a editar no encontrado")
                    data['eMotivoMatriculaEspecial'] = eMotivoMatriculaEspecial = MotivoMatriculaEspecial.objects.get(pk=request.GET['id'])
                    f = MotivoMatriculaEspecialForm()
                    f.set_initial(eMotivoMatriculaEspecial)
                    data['form'] = f
                    return render(request, "adm_sistemas/especial_enroll_reason/editmotivo.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Admininistración de Motivos de Matrícula Especial'
                search = None
                ids = None
                motivos = MotivoMatriculaEspecial.objects.filter(status=True)
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
                return render(request, "adm_sistemas/especial_enroll_reason/view.html", data)
            except Exception as ex:
                pass
