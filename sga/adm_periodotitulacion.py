# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import PeriodoGrupoTitulacionForm, ArchivosTitulacionForm
from sga.funciones import log, generar_nombre
from sga.models import PeriodoGrupoTitulacion, ArchivoTitulacion


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'addarchivo' or action == 'editarchivo':
            try:
                f = ArchivosTitulacionForm(request.POST, request.FILES)
                if f.is_valid():
                    if action == 'addarchivo':
                        archivo = ArchivoTitulacion()
                    else:
                        archivo = ArchivoTitulacion.objects.get(pk=request.POST['id'])
                    archivo.nombre = f.cleaned_data['nombre']
                    archivo.tipotitulacion = f.cleaned_data['tipotitulacion']
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivotitulacion_", newfile._name)
                        archivo.archivo = newfile
                    archivo.save(request)
                    if action == 'addarchivo':
                        log(u'Agrego Archivo Titulación: %s' % archivo, request, "addarchivo")
                    else:
                        log(u'Edito Archivo Titulación: %s' % archivo, request, "editarchivo")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action =='deletearchivo':
            try:
                archivo = ArchivoTitulacion.objects.get(pk=request.POST['id'])
                if archivo.vigente:
                    return JsonResponse({"result": "bad", "mensaje": u"El archivo se encuentra vigente."})
                archivo.status=False
                archivo.save(request)
                log(u'Elimino Archivo Titulación: %s' % archivo, request, "deletearchivo")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        if action == 'add':
            try:
                form = PeriodoGrupoTitulacionForm(request.POST)
                if form.is_valid():
                    nombres=form.cleaned_data['nombre']
                    if form.cleaned_data['fechainicio']< form.cleaned_data['fechafin']:
                        if not PeriodoGrupoTitulacion.objects.filter(nombre=nombres, status=True).exists():
                            periodo=PeriodoGrupoTitulacion(nombre=form.cleaned_data['nombre'],
                                                           descripcion=form.cleaned_data['descripcion'],
                                                           fechainicio=form.cleaned_data['fechainicio'],
                                                           fechafin=form.cleaned_data['fechafin'],
                                                           porcentajeurkund=form.cleaned_data['plagio'],
                                                           nrevision=form.cleaned_data['nrevision'],
                                                           )

                            periodo.save(request)
                            log(u'Agrego Periodo Titulación: %s' % periodo, request, "add")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"La Fecha esta mal ingresados."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action=='editar':
            try:
                periodo = PeriodoGrupoTitulacion.objects.get(pk=int(request.POST['id']))
                form = PeriodoGrupoTitulacionForm(request.POST)
                if form.is_valid():
                    if periodo.tiene_grupo_activo():
                        periodo.descripcion = form.cleaned_data['descripcion']
                        periodo.porcentajeurkund = form.cleaned_data['plagio']
                        periodo.nrevision = form.cleaned_data['nrevision']
                        periodo.save(request)
                        log(u'Editar Periodo de Titulación: %s' % periodo, request, "editar")
                        return JsonResponse({"result": "ok"})
                    else:
                        if form.cleaned_data['fechainicio'] < form.cleaned_data['fechafin']:
                            periodo.nombre=form.cleaned_data['nombre']
                            periodo.descripcion=form.cleaned_data['descripcion']
                            periodo.fechainicio = form.cleaned_data['fechainicio']
                            periodo.fechafin = form.cleaned_data['fechafin']
                            periodo.porcentajeurkund = form.cleaned_data['plagio']
                            periodo.nrevision = form.cleaned_data['nrevision']
                            periodo.save(request)
                            log(u'Editar Periodo de Titulación: %s' % periodo, request, "editar")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"La Fecha esta mal ingresados."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action=='eliminar':
            try:
                periodo = PeriodoGrupoTitulacion.objects.get(pk=int(request.POST['id']))
                if not periodo.no_puede_eliminar():
                    periodo.status= False
                    periodo.save(request)
                    log(u'Elimino Periodo titulacion: %s' % periodo, request, "del")
                else:
                    return JsonResponse({"result": "bad","mensaje": u"No se puede Eliminar el Periodo de Titulacion, tiene Grupos de Titulacion Activas.."})
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return HttpResponseRedirect(request.path)

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'add':
                try:
                    data['title'] = u'Adicionar Periodo de Titulación'
                    data['form'] = PeriodoGrupoTitulacionForm()
                    return render(request, "adm_periodotitulacion/add.html", data)
                except Exception as ex:
                    pass

            if action=='eliminar':
                try:
                    data['title'] = u'Eliminar Periodo de Titulación'
                    data['periodo'] = PeriodoGrupoTitulacion.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_periodotitulacion/eliminar.html", data)
                except Exception as ex:
                    pass

            if action == 'editar':
                try:
                    data['title'] = u'Editar Periodo de Titulación'
                    data['periodo'] = periodo=PeriodoGrupoTitulacion.objects.get(pk=int(request.GET['id']))
                    form = PeriodoGrupoTitulacionForm(initial={'nombre':periodo.nombre,'descripcion':periodo.descripcion,'fechainicio':periodo.fechainicio,'fechafin':periodo.fechafin,'plagio':periodo.porcentajeurkund, 'nrevision':periodo.nrevision})
                    if periodo.tiene_grupo_activo():
                        form.editar_grupo()
                    data['form'] = form
                    return render(request, "adm_periodotitulacion/editar.html", data)
                except Exception as ex:
                    pass
            if action =='archivos':
                try:
                    data['title'] = u'Archivos de Titulación'
                    data['archivos'] = ArchivoTitulacion.objects.filter(status=True)
                    return render(request, "adm_periodotitulacion/viewarchivos.html", data)
                except Exception as ex:
                    pass
            if action =='addarchivo':
                try:
                    data['title'] = u'Adicionar Archivo de Titulación'
                    data['form'] = ArchivosTitulacionForm()
                    return render(request, "adm_periodotitulacion/addarchivo.html", data)
                except Exception as ex:
                    pass
            if action =='editarchivo':
                try:
                    data['archivo']=archivo=ArchivoTitulacion.objects.get(pk=request.GET['id'])
                    data['title'] = u'Editar Archivo de Titulación'
                    data['form'] = ArchivosTitulacionForm(initial={
                        'nombre': archivo.nombre,
                        'tipotitulacion' : archivo.tipotitulacion
                    })
                    return render(request, "adm_periodotitulacion/editarchivo.html", data)
                except Exception as ex:
                    pass
            if action=='deletearchivo':
                try:
                    data['title'] = u'Eliminar Archivo de Titulación'
                    data['archivo'] = ArchivoTitulacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_periodotitulacion/deletearchivo.html", data)
                except Exception as ex:
                    pass
            if action == 'vigente':
                try:
                    archivo = ArchivoTitulacion.objects.get(pk=request.GET['id'])
                    archivo.vigente = True
                    archivo.save(request)
                    log(u"cambio vigente archivo titulacion: %s" % archivo, request, "edit")
                    return HttpResponseRedirect('/adm_periodotitulacion?action=archivos')
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass
            if action == 'novigente':
                try:
                    archivo = ArchivoTitulacion.objects.get(pk=request.GET['id'])
                    archivo.vigente = False
                    archivo.save(request)
                    log(u"cambio no vigente archivo titulacion: %s" % archivo, request, "edit")
                    return HttpResponseRedirect('/adm_periodotitulacion?action=archivos')
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u'Periodo de Titulación'
            data['periodo'] = PeriodoGrupoTitulacion.objects.filter(status=True)
            return render(request, "adm_periodotitulacion/view.html", data)
