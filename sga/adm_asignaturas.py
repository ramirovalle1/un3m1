# -*- coding: latin-1 -*-
from googletrans import Translator
from django.contrib.auth.decorators import login_required
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.db import transaction
from django.shortcuts import render
from requests import request

from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import AsignaturaForm, UnificarAsignaturaForm, EjeformativoForm
from sga.funciones import log, puede_realizar_accion, MiPaginador
from sga.models import Asignatura, HistoricoRecordAcademico, AsignaturaMalla, Materia, RecordAcademico, \
    MateriaCursoEscuelaComplementaria, AgregacionEliminacionMaterias, HomologacionInscripcion, \
    ModuloMalla, EjeFormativo
from sga.templatetags.sga_extras import encrypt


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

        if action == 'add':
            try:
                f = AsignaturaForm(request.POST)
                if f.is_valid():
                    if Asignatura.objects.filter(status=True, nombre=f.cleaned_data['nombre']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La asignatura ya existe."})
                    asignatura = Asignatura(nombre=f.cleaned_data['nombre'],
                                            # codigo=f.cleaned_data['codigo'],
                                            modulo=f.cleaned_data['modulo'],
                                            creditos=f.cleaned_data['creditos'])
                    asignatura.save(request)
                    #asignatura.precedencia = f.cleaned_data['precedencia']
                    asignatura.precedencia.clear()
                    for r in f.cleaned_data['precedencia']:
                        asignatura.precedencia.add(r)
                    log(u'Adiciono asignatura: %s' % asignatura, request, "add")
                    return JsonResponse({"result": "ok", "id": asignatura.id})
                else:
                     raise NameError(f.errors)
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                asignatura = Asignatura.objects.get(pk=request.POST['id'])
                f = AsignaturaForm(request.POST)
                if f.is_valid():
                    if Asignatura.objects.filter(status=True, nombre=f.cleaned_data['nombre']).exclude(pk=asignatura.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La asignatura ya existe."})
                    asignatura.nombre = f.cleaned_data['nombre']
                    # asignatura.codigo = f.cleaned_data['codigo']
                    asignatura.creditos = f.cleaned_data['creditos']
                    asignatura.modulo = f.cleaned_data['modulo']
                    asignatura.save(request)
                    #asignatura.precedencia = f.cleaned_data['precedencia']
                    asignatura.precedencia.clear()
                    for r in f.cleaned_data['precedencia']:
                        asignatura.precedencia.add(r)
                    log(u'Modifico asignatura: %s' % asignatura, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        elif action == 'unificar':
            try:
                asignatura = Asignatura.objects.get(pk=request.POST['id'])
                f = UnificarAsignaturaForm(request.POST)
                if f.is_valid():
                    nuevaasignatura = f.cleaned_data['asignatura']
                    log(u'Unifico asignatura: %s con %s' % (asignatura, nuevaasignatura), request, "del")
                    AgregacionEliminacionMaterias.objects.filter(asignatura=asignatura).update(asignatura=nuevaasignatura)
                    AsignaturaMalla.objects.filter(asignatura=asignatura).update(asignatura=nuevaasignatura)
                    HistoricoRecordAcademico.objects.filter(asignatura=asignatura).update(asignatura=nuevaasignatura)
                    HomologacionInscripcion.objects.filter(asignatura=asignatura).update(asignatura=nuevaasignatura)
                    Materia.objects.filter(asignatura=asignatura).update(asignatura=nuevaasignatura)
                    MateriaCursoEscuelaComplementaria.objects.filter(asignatura=asignatura).update(asignatura=nuevaasignatura)
                    ModuloMalla.objects.filter(asignatura=asignatura).update(asignatura=nuevaasignatura)
                    RecordAcademico.objects.filter(asignatura=asignatura).update(asignatura=nuevaasignatura)
                    asignatura.delete()
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        elif action == 'delete':
            try:
                asignatura = Asignatura.objects.get(pk=request.POST['id'])
                if asignatura.enuso():
                    return JsonResponse({"result": "bad", "mensaje": u"Asignatura en uso."})
                log(u'Elimino asignatura: %s' % asignatura, request, "del")
                asignatura.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al eliminar los datos."})

        elif action == 'info':
            try:
                a = Asignatura.objects.get(pk=request.POST['aid'])
                return JsonResponse({'result': 'ok', 'creditos': a.creditos, 'codigo': a.codigo, 'horas': a.horas()})
            except Exception as ex:
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al obtener los datos."})

        elif action == 'addejeformativo':
            try:
                f = EjeformativoForm(request.POST)
                if f.is_valid():
                    eje = EjeFormativo(nombre=f.cleaned_data['nombre'])
                    eje.save(request)
                    log(u'Adicionó eje formativo: %s' % eje, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editejeformativo':
            try:
                f = EjeformativoForm(request.POST)
                if f.is_valid():
                    eje = EjeFormativo.objects.get(pk=request.POST['id'])
                    eje.nombre = f.cleaned_data['nombre']
                    eje.save(request)
                    log(u'Adicionó eje formativo: %s' % eje, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al editar los datos."})

        elif action == 'delejeformativo':
            try:
                eje = EjeFormativo.objects.get(pk=request.POST['id'])
                if not eje.asignaturamalla_set.all().exists():
                    log(u'Adicionó eje formativo: %s' % eje, request, "del")
                    eje.delete()
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"El eje formativo ya se encuentra en uso."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Listado de asignaturas'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_asignaturas')
                    data['title'] = u'Adicionar asignatura'
                    data['form'] = AsignaturaForm(initial={'creditos': 0})
                    return render(request, "adm_asignaturas/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_asignaturas')
                    data['title'] = u'Editar asignaturas'
                    asignatura = Asignatura.objects.get(pk=int(encrypt(request.GET['id'])))
                    f = AsignaturaForm(initial={'nombre': asignatura.nombre,
                                                'codigo': asignatura.codigo,
                                                'creditos': asignatura.creditos,
                                                'modulo': asignatura.modulo,
                                                'precedencia': asignatura.precedencia.all()})
                    f.fields['nombre'].widget.attrs['readonly'] = True
                    f.fields['nombre'].widget.required = False
                    #f.fields['nombre'].widget.required = True
                    f.sin_misma(asignatura)
                    data['form'] = f
                    data['asignatura'] = asignatura
                    return render(request, "adm_asignaturas/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'unificar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_asignaturas')
                    data['title'] = u'Unificar asignaturas'
                    asignatura = Asignatura.objects.get(pk=request.GET['id'])
                    f = UnificarAsignaturaForm(initial={'origen': asignatura})
                    f.for_id(asignatura.id)
                    data['form'] = f
                    data['asignatura'] = asignatura
                    return render(request, "adm_asignaturas/unificar.html", data)
                except Exception as ex:
                    pass

            elif action == 'delete':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_asignaturas')
                    data['title'] = u'Eliminar asignatura'
                    data['asignatura'] = Asignatura.objects.get(pk=request.GET['id'])
                    return render(request, "adm_asignaturas/delete.html", data)
                except Exception as ex:
                    pass

            elif action == 'ejeformativo':
                try:
                    data['title'] = u'Listado de ejes formativos'
                    search = None
                    ids = None
                    ejeformativos = EjeFormativo.objects.filter(status=True).order_by('id')
                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        if len(ss) == 1:
                            ejeformativos = ejeformativos.filter(Q(nombre__icontains=search))
                        else:
                            ejeformativos = ejeformativos.filter(Q(nombre__icontains=ss[0]), Q(nombre__icontains=ss[1]))
                    paging = MiPaginador(ejeformativos, 20)
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
                    data['ejeformativos'] = page.object_list
                    return render(request, "adm_asignaturas/ejeformativo.html", data)
                except Exception as ex:
                    pass

            elif action == 'addejeformativo':
                try:
                    data['title'] = u'Adicionar ejes formativos'
                    data['form'] = EjeformativoForm()
                    return render(request, "adm_asignaturas/addejeformativo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editejeformativo':
                try:
                    data['title'] = u'Editar ejes formativos'
                    data['eje'] = eje = EjeFormativo.objects.get(status=True, pk=request.GET['id'])
                    data['form'] = EjeformativoForm({'nombre':eje.nombre})
                    return render(request, "adm_asignaturas/editejeformativo.html", data)
                except Exception as ex:
                    pass

            elif action == 'delejeformativo':
                try:
                    data['title'] = u'Eliminar eje formativo'
                    data['eje'] = eje = EjeFormativo.objects.get(status=True, pk=request.GET['id'])
                    return render(request, "adm_asignaturas/delejeformativo.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                ss = search.split(' ')
                if len(ss) == 2:
                    asignaturas = Asignatura.objects.filter(Q(nombre__icontains=ss[0]) & Q(nombre__icontains=ss[1])).order_by('nombre')
                if len(ss) == 3:
                    asignaturas = Asignatura.objects.filter(Q(nombre__icontains=ss[0]) & Q(nombre__icontains=ss[1]) & Q(nombre__icontains=ss[2])).order_by('nombre')
                if len(ss) == 4:
                    asignaturas = Asignatura.objects.filter(Q(nombre__icontains=ss[0]) & Q(nombre__icontains=ss[1]) & Q(nombre__icontains=ss[2]) & Q(nombre__icontains=ss[3])).order_by('nombre')
                else:
                    asignaturas = Asignatura.objects.filter(Q(nombre__icontains=search) | Q(codigo__icontains=search) | Q(pk__icontains=search)).order_by('nombre')
            elif 'id' in request.GET:
                ids = request.GET['id']
                asignaturas = Asignatura.objects.filter(id=ids)
            else:
                asignaturas = Asignatura.objects.all().order_by('nombre')
            paging = MiPaginador(asignaturas, 25)
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
            data['asignaturas'] = page.object_list
            return render(request, "adm_asignaturas/view.html", data)
