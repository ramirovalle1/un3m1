# -*- coding: UTF-8 -*-
#PYTHON
import sys
import json
from decorators import secure_module

#DJANGO
from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template.loader import get_template
from django.shortcuts import render, redirect
from django.db.models import Q
from django import forms

#OTROS
from unidecode import unidecode
from utils.filtros_genericos import filtro_persona, filtro_persona_principal

#SGA
from sga.commonviews import adduserdata
from sga.funciones import generar_nombre, log, variable_valor, MiPaginador, notificacion, validar_archivo
from sga.tasks import send_html_mail
from sga.models import Persona, CUENTAS_CORREOS
from sga.templatetags.sga_extras import encrypt

#SAGEST
from sagest.models import Departamento,RegimenLaboral, MotivoAccionPersonalDetalle, SeccionDepartamento

from sagest.funciones import encrypt_id, departamentos_vigentes, get_departamento, filter_departamentos
from core.choices.models.sagest import ESTADO_INCIDENCIA
from faceid.models import PersonaMarcada, HistorialCambioEstado
from faceid.utils.funciones import funcionarios_importar
from faceid.forms import ImportarFuncionariosForm, PersonaMarcadaForm

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['hoy'] = hoy = datetime.now()
    usuario = request.user
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    data['mi_departamento'] = mi_departamento = persona.mi_departamento()
    if request.method == 'POST':
        action = request.POST['action']
        # SANCIONES
        if action == 'importarfuncionarios':
            try:
                form = ImportarFuncionariosForm(request.POST)
                if not form.is_valid():
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                departamento = form.cleaned_data['departamento']
                regimen = form.cleaned_data['regimen']
                cargos = form.cleaned_data['cargos']
                filtro = Q(status=True)
                if departamento:
                    filtro &= Q(unidadorganica=departamento)
                if regimen:
                    filtro &= Q(regimenlaboral=regimen)
                if cargos:
                    filtro &= Q(denominacionpuesto__in=cargos)

                funcionarios = funcionarios_importar().filter(filtro)
                for f in funcionarios:
                    persona = PersonaMarcada(persona=f.persona, departamento=f.unidadorganica, cargo=f.denominacionpuesto)
                    persona.save(request)
                log(f'Importación masiva de funcionrios al sistema de marcaje: {len(funcionarios)} funcipnarios masiva', request, 'add')
                messages.success(request, f'Se importo {len(funcionarios)} funcionarios al sistema de marcaje')
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'cambiarestado':
            try:
                per_marcada = PersonaMarcada.objects.get(pk=encrypt_id(request.POST['id']))
                val = eval(request.POST['val'].capitalize())
                tipo = request.POST['args'] if 'args' in request.POST else request.POST['args[val]']
                onservacion = ''
                if tipo == 'activo':
                    tipo = 1
                    observacion = 'Se cambio el estado de activo'
                    per_marcada.activo = val
                elif tipo == 'externo':
                    tipo = 2
                    observacion = request.POST['args[text]']
                    per_marcada.externo = val
                elif tipo == 'solo_pc':
                    tipo = 3
                    observacion = request.POST['args[text]']
                    per_marcada.solo_pc = val
                per_marcada.save(request)

                historial = HistorialCambioEstado(persona_marcada=per_marcada,
                                                  persona=persona, tipo=tipo,
                                                  estado=val, motivo=observacion)
                historial.save(request)
                log(u"Actualizo permiso de marcaje: %s" % per_marcada, request, "edit")
                return JsonResponse({'result': True, 'mensaje': 'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': False, 'mensaje': f'{ex}'})

        elif action == 'addpersonamarcada':
            try:
                form = PersonaMarcadaForm(request.POST)
                if not form.is_valid():
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                departamento, cargo, pers = None, None, form.cleaned_data['persona']
                distributivo = funcionarios_importar().filter(persona=form.cleaned_data['persona']).last()
                if distributivo:
                    departamento = distributivo.unidadorganica
                    cargo = distributivo.denominacionpuesto
                elif not pers.usuario.is_superuser:
                    raise NameError('El usuario seleccionado no es parte de la plantilla de talento humano')


                persona_marcada = PersonaMarcada(persona = pers,
                                                departamento = departamento,
                                                cargo = cargo,
                                                activo = form.cleaned_data['activo'],
                                                externo = form.cleaned_data['externo'],
                                                solo_pc = form.cleaned_data['solo_pc'])
                persona_marcada.save(request)
                log(f'Add persona marcada: {persona_marcada}', request, 'add')
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'editpersonamarcada':
            try:
                id = encrypt_id(request.POST['id'])
                persona_marcada = PersonaMarcada.objects.get(id=id)
                form = PersonaMarcadaForm(request.POST, instancia=persona_marcada)
                if not form.is_valid():
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})

                departamento, cargo, pers = None, None, form.cleaned_data['persona']
                distributivo = funcionarios_importar().filter(persona=form.cleaned_data['persona']).last()
                if distributivo:
                    departamento = distributivo.unidadorganica
                    cargo = distributivo.denominacionpuesto
                elif not pers.usuario.is_superuser:
                    raise NameError('El usuario seleccionado no es parte de la plantilla de talento humano')

                persona_marcada.persona = pers
                persona_marcada.departamento = departamento
                persona_marcada.cargo = cargo
                persona_marcada.activo = form.cleaned_data['activo']
                persona_marcada.externo = form.cleaned_data['externo']
                persona_marcada.solo_pc = form.cleaned_data['solo_pc']
                persona_marcada.save(request)
                log(f'Edito persona marcada: {persona_marcada}', request, 'edit')
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'delpersonamarcada':
            try:
                id = encrypt_id(request.POST['id'])
                persona_marcada = PersonaMarcada.objects.get(id=id)
                persona_marcada.status = False
                persona_marcada.save(request)
                log(f'Elimino persona marcada: {persona_marcada}', request, 'del')
                return JsonResponse({'error': False})
            except Exception as ex:
                return JsonResponse({'error': True, 'mensaje': f'Error: {ex}'})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        search, filtro, url_vars  = request.GET.get('s', ''), Q(status=True), ''
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            url_vars = f'&action={action}'

            if action == 'importarfuncionarios':
                try:
                    data['total'] = len(funcionarios_importar())
                    form = ImportarFuncionariosForm()
                    form.fields['departamento'].queryset = departamentos_vigentes()
                    data['form'] = form
                    data['seccionado'] = True
                    template = get_template('adm_gestion_marcadas/forms/importarfuncionarios.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'cantidadfuncionarios':
                try:
                    departamento = request.GET['value[departamento]']
                    regimen = request.GET['value[regimen]']
                    cargos = request.GET.getlist('value[cargos][]','')
                    filtro = Q(status=True)
                    if departamento:
                        filtro &= Q(unidadorganica_id=int(departamento))
                    if regimen:
                        filtro &= Q(regimenlaboral_id=int(regimen))
                    if cargos:
                        filtro &= Q(denominacionpuesto_id__in=cargos)
                    cantidad = len(funcionarios_importar().filter(filtro))
                    return JsonResponse({'result': True, 'cantidad': cantidad})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})


            elif action == 'addpersonamarcada':
                try:
                    form =  PersonaMarcadaForm()
                    form.fields['persona'].queryset = Persona.objects.none()
                    # form.fields['departamento'].queryset = departamentos_vigentes()
                    data['form'] = form
                    data['switchery'] = True
                    template = get_template('adm_gestion_marcadas/forms/formpersonamarcada.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'editpersonamarcada':
                try:
                    persona_marcada = PersonaMarcada.objects.get(id=encrypt_id(request.GET['id']))
                    form = PersonaMarcadaForm(initial=model_to_dict(persona_marcada))
                    form.fields['persona'].queryset = Persona.objects.filter(id=persona_marcada.persona.id)
                    # form.fields['departamento'].queryset = departamentos_vigentes([persona_marcada.departamento.id,])
                    data['id'] = persona_marcada.id
                    data['form'] = form
                    data['switchery'] = True
                    template = get_template('adm_gestion_marcadas/forms/formpersonamarcada.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'historialestado':
                try:
                    data['persona_marcada'] = persona_marcada = PersonaMarcada.objects.get(id=encrypt_id(request.GET['id']))
                    data['historial'] = HistorialCambioEstado.objects.filter(persona_marcada=persona_marcada).order_by('-fecha_creacion')
                    template = get_template('adm_gestion_marcadas/forms/historialestados.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})



            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Gestor de marcaje institucional'
                estado, departamento, search = (request.GET.get('estado', ''),
                                                request.GET.get('departamento', ''),
                                                request.GET.get('s', ''))
                if estado:
                    data['estado'] = estado = int(estado)
                    filtro &= Q(estado=estado)
                    url_vars += f'&estado={estado}'
                if departamento:
                    data['departamento'] = departamento = int(departamento)
                    filtro &= Q(departamento_id=departamento)
                    url_vars += f'&departamento={departamento}'
                if search:
                    filtro = filtro_persona(search, filtro)
                    data['s'] = search
                    url_vars += f'&s={search}'
                listado = PersonaMarcada.objects.filter(filtro).order_by('departamento__nombre')
                paginator = MiPaginador(listado, 20)
                page = int(request.GET.get('page', 1))
                paginator.rangos_paginado(page)
                data['paging'] = paging = paginator.get_page(page)
                data['listado'] = paging.object_list
                data['url_vars'] = url_vars
                return render(request, 'adm_gestion_marcadas/view.html', data)
            except Exception as ex:
                return HttpResponseRedirect(f'/?info=Error inesperado {ex}')


