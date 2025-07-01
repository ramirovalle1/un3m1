# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import ComplexivoAsignaturaForm
from sga.funciones import log, MiPaginador
from sga.models import ComplexivoAsignatura

@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@secure_module
@last_access

def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addasignatura' or action == 'editasignatura':
            try:
                f = ComplexivoAsignaturaForm(request.POST)
                if f.is_valid():
                    #validacion
                    if action == 'addasignatura':
                        if ComplexivoAsignatura.objects.filter(status=True,nombre=f.cleaned_data['nombre'].upper()).exists():
                            return JsonResponse({"result":"bad", "mensaje":u"Esta materia ya esta registrada"})
                        asignatura = ComplexivoAsignatura()
                    else:
                        if ComplexivoAsignatura.objects.filter(status=True,nombre=f.cleaned_data['nombre'].upper()).exclude(pk=request.POST['id']).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Esta materia ya esta registrada"})
                        asignatura = ComplexivoAsignatura.objects.get(pk=request.POST['id'])
                    asignatura.nombre = f.cleaned_data['nombre']
                    asignatura.codigo = f.cleaned_data['codigo']
                    asignatura.save(request)
                    if action == 'addasignatura':
                        log(u"Adiciono asignatura: %s" % asignatura, request, "add")
                    else:
                        log(u"Edito asignatura: %s" % asignatura, request, "edit")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deleteasignatura':
            try:
                asignatura = ComplexivoAsignatura.objects.get(pk=request.POST['id'])
                asignatura.status = False
                asignatura.save(request)
                log(u"Elimino asignatura: %s" % asignatura, request, "delete")
                return JsonResponse({"result": "ok", "id": asignatura.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'addasignatura':
                try:
                    data['title']= "Añadir asignatura"
                    data['form'] = ComplexivoAsignaturaForm()
                    return render(request, 'adm_complexivoasignatura/addasignatura.html', data)
                except Exception as ex:
                    pass
            if action == 'editasignatura':
                try:
                    data['title']= "Editar asignatura"
                    asignatura = ComplexivoAsignatura.objects.get(pk=request.GET['id'])
                    data['asignatura'] = asignatura.id
                    data['form'] = ComplexivoAsignaturaForm(initial={
                        'nombre': asignatura.nombre,
                        'codigo': asignatura.codigo,
                    })
                    return render(request, 'adm_complexivoasignatura/editasignatura.html', data)
                except Exception as ex:
                    pass

            if action == 'deleteasignatura':
                try:
                    data['title'] = u'Eliminar materia'
                    asignatura = ComplexivoAsignatura.objects.get(pk=request.GET['id'])
                    data['asignatura'] = asignatura
                    return render(request, "adm_complexivoasignatura/deleteasignatura.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            data['title'] = u'Asignaturas Complexivo'
            if 's' in request.GET:
                search = request.GET['s']
                asignaturas = ComplexivoAsignatura.objects.filter(nombre__icontains=search, status=True).distinct().order_by('-nombre')
            elif 'id' in request.GET:
                ids = request.GET['id']
                asignaturas = ComplexivoAsignatura.objects.filter(id=ids,status=True)
            else:
                asignaturas = ComplexivoAsignatura.objects.filter(status=True).order_by('-nombre')
            paging = MiPaginador(asignaturas, 20)
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
            return render(request, "adm_complexivoasignatura/view.html", data)