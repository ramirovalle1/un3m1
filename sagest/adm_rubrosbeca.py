# -*- coding: UTF-8 -*-
import json
import os
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from sagest.forms import CampoContratoForm, ContratosForm, ArchivoContratoForm, ContratoPersonaForm, \
    CategoriaRubroBecaForm, RubroBecaForm
from sagest.models import CamposContratos, Contratos, ContratosCamposSeleccion, CategoriaRubroBeca, RubroBeca
from sagest.models import ContratoPersona, ContratoPersonaDetalle
from settings import SITE_ROOT
from sga.commonviews import adduserdata
from sga.funciones import log
from docx import Document

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addcategoriarubrobeca':
            try:
                form = CategoriaRubroBecaForm(request.POST)
                if form.is_valid():
                    registro = CategoriaRubroBeca(nombre=form.cleaned_data['nombre'])
                    registro.save(request)
                    log(u'Registro nuevo de Categoria Rubro Beca: %s' % registro, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'addrubrobeca':
            try:
                form = RubroBecaForm(request.POST, request.FILES)
                if form.is_valid():
                    registro = RubroBeca(categoriarubrobeca=form.cleaned_data['categoriarubrobeca'],
                                         nombre=form.cleaned_data['nombre'])
                    registro.save(request)
                    log(u'Registro nuevo Rubro Beca: %s' % registro, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'editrubrobeca':
            try:
                form = RubroBecaForm(request.POST)
                if form.is_valid():
                    rubrobeca = RubroBeca.objects.get(pk=request.POST['id'], status=True)
                    rubrobeca.categoriarubrobeca = form.cleaned_data['categoriarubrobeca']
                    rubrobeca.nombre = form.cleaned_data['nombre']
                    rubrobeca.save(request)
                    log(u'Registro modificado Rubro Beca: %s' % rubrobeca, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'editcategoriarubrobeca':
            try:
                form = CategoriaRubroBecaForm(request.POST)
                if form.is_valid():
                    registro = CategoriaRubroBeca.objects.get(pk=request.POST['id'], status=True)
                    registro.nombre = form.cleaned_data['nombre']
                    registro.save(request)
                    log(u'Registro modificado Categoria Rubro Beca: %s' % registro, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al editar los datos."})

        if action == 'deleterubrobeca':
            try:
                campo = RubroBeca.objects.get(pk=request.POST['id'], status=True)
                if campo.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": "El Rubro-Beca se encuentra en uso."})
                campo.status=False
                campo.save(request)
                log(u'Elimino Rubro Beca: %s' % campo, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'deletecategoriarubrobeca':
            try:
                registro = CategoriaRubroBeca.objects.get(pk=request.POST['id'], status=True)
                registro.status = False
                registro.save(request)
                log(u'Elimino Categoria Rubro Beca: %s' % registro, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addcategoriarubrobeca':
                try:
                    data['title'] = u'Nuevo categoria rubro-beca'
                    data['form'] = CategoriaRubroBecaForm()
                    return render(request, "adm_rubrosbeca/addcategoriarubrobeca.html", data)
                except Exception as ex:
                    pass

            if action == 'addrubrobeca':
                try:
                    data['title'] = u'Nuevo Rubro-Beca'
                    data['form'] = RubroBecaForm()
                    return render(request, "adm_rubrosbeca/addrubrobeca.html", data)
                except Exception as ex:
                    pass

            if action == 'editcategoriarubrobeca':
                try:
                    # puede_realizar_accion(request, 'sagest.puede_modificar_periodo')
                    data['title'] = u'Modificación categoria rubro-beca'
                    data['actividad'] = categoriarubrobeca = CategoriaRubroBeca.objects.get(pk=request.GET['id'], status=True)
                    form = CategoriaRubroBecaForm(initial={'nombre': categoriarubrobeca.nombre})
                    data['form'] = form
                    return render(request, "adm_rubrosbeca/editcategoriarubrobeca.html", data)
                except Exception as ex:
                    pass

            if action == 'editrubrobeca':
                try:
                    # puede_realizar_accion(request, 'sagest.puede_modificar_periodo')
                    data['title'] = u'Modificación de Rubro-Beca'
                    data['rubrobeca'] = rubrobeca = RubroBeca.objects.get(pk=request.GET['id'], status=True)
                    form = RubroBecaForm(initial={'categoriarubrobeca': rubrobeca.categoriarubrobeca,
                                                  'nombre': rubrobeca.nombre})
                    data['form'] = form
                    return render(request, "adm_rubrosbeca/editrubrobeca.html", data)
                except Exception as ex:
                    pass

            if action == 'deleterubrobeca':
                try:
                    data['title'] = u'Eliminar Rubro-Beca'
                    data['rubrobeca'] = RubroBeca.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_rubrosbeca/deleterubrobeca.html", data)
                except:
                    pass

            if action == 'deletecategoriarubrobeca':
                try:
                    data['title'] = u'Eliminar Contrato Plantilla'
                    data['categoriarubrobeca'] = CategoriaRubroBeca.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_rubrosbeca/deletecategoriarubrobeca.html", data)
                except:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Rubros-Becas'
            data['rubrobecas'] = RubroBeca.objects.filter(status=True).order_by('categoriarubrobeca','nombre')
            data['categoriarubrobecas'] = CategoriaRubroBeca.objects.filter(status=True).order_by('nombre')
            return render(request, 'adm_rubrosbeca/view.html', data)