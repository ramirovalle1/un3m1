# -*- coding: latin-1 -*-
import json
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import TipoTitulacionForm, CombinarTipoTitulacionForm
from sga.funciones import log
from sga.models import TipoTitulaciones, CombinarTipoTitulaciones, Carrera


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'add':
            try:
                form = TipoTitulacionForm(request.POST)
                if form.is_valid():
                    nombres=form.cleaned_data['nombre']
                    if not TipoTitulaciones.objects.values('id').filter(nombre=nombres, status=True).exists():
                        tipo=TipoTitulaciones(nombre=form.cleaned_data['nombre'],
                                              codigo=form.cleaned_data['codigo'],
                                              caracteristica=form.cleaned_data['caracteristica'],
                                              tipo=int(form.cleaned_data['tipo'])
                                              )
                        tipo.save(request)
                        log(u'Agrego Tipo de Titulación: %s' % tipo, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editar':
            try:
                tipo = TipoTitulaciones.objects.get(pk=int(request.POST['id']))
                form = TipoTitulacionForm(request.POST)
                if form.is_valid():
                    tipo.nombre = form.cleaned_data['nombre']
                    tipo.codigo = form.cleaned_data['codigo']
                    tipo.caracteristica = form.cleaned_data['caracteristica']
                    if not tipo.tiene_alternativa_activas():
                        tipo.tipo = int(form.cleaned_data['tipo'])
                    tipo.save(request)
                    log(u'Editar Tipo de Titulación: %s' % tipo, request, "editar")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action=='eliminar':
            try:
                tipo = TipoTitulaciones.objects.get(pk=int(request.POST['id']))
                if not tipo.tiene_alternativa_activas():
                    tipo.status= False
                    tipo.save(request)
                    log(u'Eliminó Tipo de Titulación: %s' % tipo, request, "del")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar Tipo de Titulación, tiene Alternativas de Titulacion en proceso."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})
        if action == 'combinar':
            try:
                form = CombinarTipoTitulacionForm(request.POST)
                if form.is_valid():
                    carreras = form.cleaned_data['carreras']
                    tipo = TipoTitulaciones.objects.get(pk=int(request.POST['id']))
                    for carrera in carreras:
                        if not CombinarTipoTitulaciones.objects.values('id').filter(tipotitulacion=tipo,carrera=carrera, status=True).exists():
                            combinartipo = CombinarTipoTitulaciones(tipotitulacion=tipo,carrera=carrera)
                            combinartipo.save(request)
                            log(u'Combinar Tipo de Titulación: %s' % combinartipo, request, "add")
                    combina =CombinarTipoTitulaciones.objects.filter(tipotitulacion=tipo, status=True).exclude(carrera__in=carreras)
                    for comb in combina:
                        comb.status=False
                        comb.save(request)
                        log(u'Combinar Tipo de Titulación: %s' % comb, request, "del")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos a Guardar."})
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(
                    json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}),content_type="application/json")
        return HttpResponseRedirect(request.path)

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'add':
                try:
                    data['title'] = u'Adicionar Tipo Titulación'
                    data['form'] = TipoTitulacionForm()
                    return render(request, "adm_tipotitulacion/add.html", data)
                except Exception as ex:
                    pass

            if action=='eliminar':
                try:
                    data['title'] = u'Eliminar Tipo Titulación'
                    data['tipo'] = TipoTitulaciones.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_tipotitulacion/eliminar.html", data)
                except Exception as ex:
                    pass
            if action == 'editar':
                try:
                    data['title'] = u'Editar Tipo de Titulación'
                    data['tipo'] = tipo=TipoTitulaciones.objects.get(pk=int(request.GET['id']))
                    form = TipoTitulacionForm(initial={'nombre':tipo.nombre,
                                                       'codigo':tipo.codigo,
                                                       'caracteristica':tipo.caracteristica,
                                                       'tipo':tipo.tipo})
                    if tipo.tiene_alternativa_activas():
                        form.editar()
                    data['form']= form
                    return render(request, "adm_tipotitulacion/editar.html", data)
                except Exception as ex:
                    pass
            if action == 'combinar':
                try:
                    data['title'] = u'Combinar Tipo de Titulación'
                    data['tipo'] = tipo = TipoTitulaciones.objects.get(pk=int(request.GET['id']))
                    if CombinarTipoTitulaciones.objects.values('id').filter(tipotitulacion=tipo,status=True).exists():
                        combinar=CombinarTipoTitulaciones.objects.filter(tipotitulacion=tipo,status=True)
                        form = CombinarTipoTitulacionForm(initial={'tipo': tipo.nombre, 'carreras':Carrera.objects.filter(pk__in=[c.carrera.id for c in combinar])})
                        data['lista_carreras']=combinar
                    else:
                        form = CombinarTipoTitulacionForm(initial={'tipo': tipo.nombre})
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_tipotitulacion/combinar.html", data)
                except Exception as ex:
                    pass
            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Tipo de Titulación'
            data['tipo'] = TipoTitulaciones.objects.filter(status=True)
            return render(request, "adm_tipotitulacion/view.html", data)
