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

#OTROS
from unidecode import unidecode
from utils.filtros_genericos import filtro_persona, filtro_persona_principal

#SGA
from sga.commonviews import adduserdata
from sga.funciones import generar_nombre, log, variable_valor, MiPaginador
from sga.tasks import send_html_mail
from sga.models import Persona

#SAGEST
from sagest.models import Departamento
from sagest.funciones import encrypt_id, departamentos_vigentes, get_departamento, filter_departamentos, slugs_rectorado_vicerrectorados
from core.choices.models.sagest import ESTADO_INCIDENCIA, ETAPA_INCIDENCIA

#DIRECTIVO
from directivo.models import IncidenciaSancion, MotivoSancion, PersonaSancion, PuntoControl, EvidenciaPersonaSancion, RequisitoMotivoSancion, FaltaDisciplinaria
from directivo.forms import IncidenciaSancionForm
from directivo.utils.funciones import (generar_codigo_incidencia, permisos_sanciones, recover_file_temp,
                                       notify_persona_sancion, notificar_personas_sancion,
                                       secciones_etapa_audiencia, secciones_etapa_analisis,
                                       firmar_documento_etapa, obtener_tiempo_restante_seg)
from directivo.utils.actions_sanciones import (post_remitir_descargo, get_cargar_marcadas,generar_reporte_marcada,
                                               get_cargar_meses_marcadas, get_detalleaudiencia, get_revisar_audiencia, get_render_marcadas,
                                               get_historialfirmas, get_generar_accionpersonal, post_generar_accionpersonal)
from directivo.utils.strings import Strings, get_text_campo_objeto

@login_required(redirect_field_name='ret', login_url='/loginsagest')
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['hoy'] = hoy = datetime.now()
    usuario = request.user
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    data['permisos'] = permisos = permisos_sanciones(persona)
    data['mi_departamento'] = mi_departamento = persona.mi_departamento()
    if not mi_departamento and not permisos['revisor']:
        return HttpResponseRedirect('/?info=No tiene departamento asignado')

    if request.method == 'POST':
        action = request.POST['action']
        if action == 'addincidencia':
            try:
                form = IncidenciaSancionForm(request.POST)
                if not form.is_valid():
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                listado = json.loads(request.POST['lista_items1'])
                if not listado:
                    raise NameError('No se ha seleccionado ningun usuario.')
                estado = request.POST.get('estadoincidencia', '2')
                # etapa = 2 if estado == '2' else 1
                codigo, numero = generar_codigo_incidencia(persona, mi_departamento)
                incidencia = IncidenciaSancion(codigo=codigo,
                                                numero=numero,
                                                etapa=1,
                                                estado=estado,
                                                persona=persona,
                                                departamento=mi_departamento,
                                                falta=form.cleaned_data['falta'],
                                                motivo=form.cleaned_data['motivo'],
                                                observacion=form.cleaned_data['observacion']
                                            )
                incidencia.save(request)
                log(f'Agrego una incidencia de indiciplina {incidencia}', request, "add")
                for item in listado:
                    persona = Persona.objects.get(pk=item['id_persona'])
                    persona_sancion = PersonaSancion(incidencia=incidencia, persona=persona)
                    persona_sancion.save(request)
                    for evidencia in item['evidencias']:
                        requisito_motivo = RequisitoMotivoSancion.objects.get(pk=evidencia['id_requisito'])
                        name_file, url, archivo='', '', ''
                        if evidencia['tipo'] == 'file':
                            name_file = evidencia['evidencia']
                            size = evidencia['size']
                            if not name_file in request.FILES and requisito_motivo.obligatorio:
                                raise NameError(f'{requisito_motivo.requisito} es obligatorio, por favor registre lo solicitado.')
                            if name_file in request.FILES:
                                archivo = request.FILES[name_file]
                                tamano = 4 # 4 MB
                                max_tamano = tamano * 1024 * 1024  # 4 MB
                                name_ = archivo._name
                                ext = name_[name_.rfind("."):]
                                formatos = requisito_motivo.requisito.formatos_permitidos()
                                if not ext.lower() in formatos:
                                    str_formatos = ', '.join(formatos)
                                    raise NameError(f'Solo se permite formato {str_formatos}')

                                if size > max_tamano:
                                    raise NameError(f'Archivo supera los {tamano} megas permitidos')
                                # Asignar un nombre personalizado al archivo
                                archivo.name = unidecode(generar_nombre(f"{name_file}_", archivo._name))
                        elif evidencia['tipo'] == 'url_file':
                            url_file_temp = evidencia['evidencia']
                            name_evidencia = evidencia['name_evidencia']
                            name_file = unidecode(generar_nombre(f"{name_evidencia}_", 'default.pdf'))
                            archivo = recover_file_temp(url_file_temp, name_file)
                        else:
                            url = evidencia['evidencia']

                        evidencia = EvidenciaPersonaSancion(persona_sancion=persona_sancion,
                                                            requisito_motivo=requisito_motivo,
                                                            archivo=archivo,
                                                            url=url)
                        evidencia.save(request)

                url_ = f'/adm_directivos?action=incidencias'
                return JsonResponse({"result": False, "to": url_})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"{ex}"})

        elif action == 'editincidencia':
            #Tener en cuenta que en el edit no esta contemplado el de generar evidencia
            try:
                form = IncidenciaSancionForm(request.POST)
                if not form.is_valid():
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                listado = json.loads(request.POST['lista_items1'])
                if not listado:
                    raise NameError('No se ha seleccionado ningun usuario.')
                estado = request.POST.get('estadoincidencia', '2')
                etapa = 2 if estado == '2' else 1

                incidencia = IncidenciaSancion.objects.get(pk=encrypt_id(request.POST['id']))
                incidencia.falta = form.cleaned_data['falta']
                incidencia.motivo = form.cleaned_data['motivo']
                incidencia.observacion = form.cleaned_data['observacion']
                incidencia.estado = estado
                incidencia.etapa = etapa
                incidencia.save(request)
                log(f'Agrego una incidencia de indiciplina {incidencia}', request, "add")
                ids_pers_exclude = [int(item['persona_sancion']) for item in listado if item['persona_sancion']]
                for item in listado:
                    if item['persona_sancion']:
                        persona_sancion = PersonaSancion.objects.get(pk=item['persona_sancion'])
                    else:
                        pers = Persona.objects.get(pk=item['id_persona'])
                        persona_sancion = PersonaSancion(incidencia=incidencia, persona=pers)
                        persona_sancion.save(request)
                        ids_pers_exclude.append(persona_sancion.id)
                    for evidencia in item['evidencias']:
                        requisito_motivo = RequisitoMotivoSancion.objects.get(pk=evidencia['id_requisito'])
                        id_evidencia = int(evidencia['evidencia_id']) if evidencia['evidencia_id'] else 0
                        obj_evidencia = EvidenciaPersonaSancion.objects.filter(pk=id_evidencia).first()
                        if not obj_evidencia:
                            obj_evidencia = EvidenciaPersonaSancion(persona_sancion=persona_sancion, requisito_motivo=requisito_motivo)
                        name_file, url, archivo='', '', ''
                        if evidencia['tipo'] == 'file':
                            name_file = evidencia['evidencia']
                            size = evidencia['size']
                            if not obj_evidencia.archivo and not name_file and requisito_motivo.obligatorio:
                                raise NameError(f'{requisito_motivo.requisito} es obligatorio, por favor registre lo solicitado.')
                            # if not name_file in request.FILES and requisito_motivo.obligatorio and not evidencia.archivo:
                            #     raise NameError(f'{requisito_motivo.requisito} es obligatorio, por favor registre lo solicitado.')
                            if name_file in request.FILES:
                                archivo = request.FILES[name_file]
                                tamano = 4 # 4 MB
                                max_tamano = tamano * 1024 * 1024  # 4 MB
                                name_ = archivo._name
                                ext = name_[name_.rfind("."):]
                                formatos = requisito_motivo.requisito.formatos_permitidos()
                                if not ext.lower() in formatos:
                                    str_formatos = ', '.join(formatos)
                                    raise NameError(f'Solo se permite formato {str_formatos}')

                                if size > max_tamano:
                                    raise NameError(f'Archivo supera los {tamano} megas permitidos')
                                # Asignar un nombre personalizado al archivo
                                archivo.name = unidecode(generar_nombre(f"{name_file}_", archivo._name))
                                obj_evidencia.archivo = archivo
                        else:
                            url = evidencia['evidencia']
                            obj_evidencia.url = url

                        obj_evidencia.save(request)
                incidencia.personas_sancion().exclude(id__in=ids_pers_exclude).update(status=False)
                url_ = f'/adm_directivos?action=incidencias'
                return JsonResponse({"result": False, "to": url_})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"{ex}"})

        elif action == 'delincidencia':
            try:
                instancia = IncidenciaSancion.objects.get(pk=encrypt_id(request.POST['id']))
                instancia.status=False
                instancia.save(request)
                log(f'Elimino incidencia: {instancia}', request, 'del')
                return JsonResponse({'error': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'error': True, 'mensaje': str(ex)})

        elif action == 'remitiranalisis':
            try:
                instancia = IncidenciaSancion.objects.get(pk=encrypt_id(request.POST['id']))
                instancia.etapa=2
                instancia.estado=2
                instancia.save(request)
                log(f'Se delega analisis del caso receptado: {instancia}', request, 'edit')
                return JsonResponse({'result': 'ok','showSwal':True,'titulo':'Disposición ejecutada' ,'mensaje': 'Se ejecuto con exito la disposición.'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': str(ex)})

        elif action == 'remitirdescargo':
            try:
                context = post_remitir_descargo(data, request)
                return JsonResponse(context)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': str(ex)})

        elif action == 'firmardocumento':
            try:
                context={'lx':395,'ly_menos':25}
                firmar_documento_etapa(request, persona, context)
                return JsonResponse({"result": False, "mensaje": "Guardado con exito", }, safe=False)
            except Exception as ex:
                textoerror = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s" % textoerror})

        elif action == 'finalizaretapa':
            try:
                incidencia = IncidenciaSancion.objects.get(pk=encrypt_id(request.POST['id']))
                incidencia.etapa = 3
                incidencia.estado = 6
                incidencia.save(request)
                log(f'Finalizo etapa analisis y paso a etapa de audiencia: {incidencia}', request, 'edit')
                return JsonResponse({'result': 'ok', 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": f"Error inesperado: {ex}"})

        elif action == 'generaraccionpersonal':
            try:
                context = post_generar_accionpersonal(data, request)
                return JsonResponse(context)
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        search, filtro, url_vars  = request.GET.get('s', ''), Q(status=True), ''
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            url_vars = f'&action={action}'
            # PERMISOS
            if action == 'incidencias':
                try:
                    data['title'] = 'Incidencias de sanciones'
                    data['subtitle'] = 'Listado de incidencias'
                    if permisos['revisor'] or permisos['director_th']:
                        ids_departamentos = IncidenciaSancion.objects.filter(status=True).values_list('departamento_id', flat=True).order_by('departamento_id').distinct()
                        data['departamentos'] = departamentos_vigentes(ids_departamentos)
                    else:
                        filtro &= Q(departamento=mi_departamento)

                    estado, departamento = request.GET.get('estado', ''), request.GET.get('departamento', '')
                    if estado:
                        data['estado'] = estado = int(estado)
                        filtro &= Q(estado=estado)
                        url_vars += f'&estado={estado}'
                    if departamento:
                        data['departamento'] = departamento = int(departamento)
                        filtro &= Q(departamento_id=departamento)
                        url_vars += f'&departamento={departamento}'
                    if search:
                        filtro_ex = Q(status=True,incidencia__departamento=mi_departamento)
                        filtro_ex = filtro_persona(search, filtro_ex)
                        ids_insidencias = PersonaSancion.objects.filter(filtro_ex).values_list('incidencia_id', flat=True).order_by('incidencia_id').distinct()
                        filtro &= (Q(codigo__unaccent__icontains=search) | Q(id__in=ids_insidencias))
                        data['s'] = search
                        url_vars += f'&s={search}'
                    listado = IncidenciaSancion.objects.filter(filtro).exclude(persona_id=1)
                    paginator = MiPaginador(listado, 20)
                    page = int(request.GET.get('page', 1))
                    paginator.rangos_paginado(page)
                    data['paging'] = paging = paginator.get_page(page)
                    data['listado'] = paging.object_list
                    data['url_vars'] = url_vars
                    data['estados'] = ESTADO_INCIDENCIA
                    data['viewactivo'] = {'grupo': 'sanciones', 'action': action}
                    return render(request, 'adm_directivos/incidencias.html', data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'addincidencia':
                try:
                    data['title'] = 'Adicionar incidencia disciplinaria'
                    form = IncidenciaSancionForm()
                    form.fields['motivo'].queryset = MotivoSancion.objects.none()
                    form.fields['motivoprincipal'].queryset = MotivoSancion.objects.none()
                    data['form'] = form
                    data['codigo'], numero = generar_codigo_incidencia(persona, mi_departamento)
                    data['fecha'] = hoy
                    data['integrantes'] = mi_departamento.mis_integrantes().exclude(id=persona.id)
                    data['url_atras'] = f'{request.path}?action=incidencias'
                    return render(request, 'adm_directivos/forms/formincidencia.html', data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'editincidencia':
                try:
                    data['title'] = 'Editar incidencia disciplinaria registrada'
                    data['id'] = id = encrypt_id(request.GET['id'])
                    incidencia = IncidenciaSancion.objects.get(id=id)
                    form = IncidenciaSancionForm(initial={'falta': incidencia.falta,
                                                          'motivo': incidencia.motivo,
                                                          'motivoprincipal': incidencia.motivo.motivoref,
                                                          'observacion': incidencia.observacion
                                                          })
                    form.fields['motivoprincipal'].queryset = incidencia.motivos_principales()
                    form.fields['motivo'].queryset = MotivoSancion.objects.filter(principal=False, status=True, motivoref_id=incidencia.motivo.motivoref.id)
                    data['form'] = form
                    data['codigo'] = incidencia.codigo
                    data['fecha'] = incidencia.fecha_creacion
                    data['incidencia'] = incidencia
                    data['integrantes'] = mi_departamento.mis_integrantes()
                    return render(request, 'adm_directivos/forms/formincidencia.html', data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'cargarmotivos':
                try:
                    tipo = request.GET['args']
                    if tipo == 'principal':
                        falta = FaltaDisciplinaria.objects.get(id=int(request.GET['id']))
                        motivos = falta.motivos_principales()
                    else:
                        motivo = MotivoSancion.objects.get(id=int(request.GET['id']))
                        motivos = motivo.sub_motivos()
                    motivos = [{'value': m.id, 'text': m.nombre} for m in motivos]
                    return JsonResponse({'result': True, 'data': motivos})
                except Exception as e:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'cargarfuncionario':
                try:
                    data, lista = {}, []
                    persona = Persona.objects.get(pk=int(request.GET['value']))
                    data['persona'] = {'id': persona.id, 'nombre': persona.nombre_completo_minus(), 'foto': persona.get_foto()}
                    motivo = MotivoSancion.objects.get(pk=int(request.GET['args']))
                    requisitos = motivo.requisitos().filter(status=True, activo=True)
                    for r in requisitos:
                        context = model_to_dict(r)
                        context['requisito'] = model_to_dict(r.requisito)
                        context['accept'] = r.requisito.formatos_permitidos()
                        context['icono'] = r.requisito.icono()
                        context['type_input'] = r.requisito.type_input()
                        context['punto_control'] = r.punto_control
                        context['punto_control_display'] = r.get_punto_control_display()
                        context['required'] = 'required' if r.obligatorio else ''
                        lista.append(context)
                    data['listado'] = lista
                    return JsonResponse({'result': True, 'data': data})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'mipersonal':
                try:
                    data['title'] = 'Mi personal administrativo'
                    data['subtitle'] = 'Listado de funcionarios a cargo'
                    if search:
                        filtro = filtro_persona_principal(search, filtro)
                        data['s'] = search
                        url_vars += f'&s={search}'
                    listado = mi_departamento.mis_integrantes().filter(filtro).order_by('nombres')
                    paginator = MiPaginador(listado, 20)
                    page = int(request.GET.get('page', 1))
                    paginator.rangos_paginado(page)
                    data['paging'] = paging = paginator.get_page(page)
                    data['listado'] = paging.object_list
                    data['url_vars'] = url_vars
                    data['viewactivo'] = {'grupo': 'general', 'action': action}
                    return render(request, 'adm_directivos/mi_personal.html', data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'receptadas':
                try:
                    data['title'] = 'Casos de sanción registrados'
                    data['subtitle'] = 'Listado de casos de sanción registrados'
                    estado, departamento = request.GET.get('estado', ''), request.GET.get('departamento', '')
                    if estado:
                        data['estado'] = estado = int(estado)
                        filtro &= Q(estado=estado)
                        url_vars += f'&estado={estado}'
                    if departamento:
                        data['departamento'] = departamento = int(departamento)
                        filtro &= Q(departamento_id=departamento)
                        url_vars += f'&departamento={departamento}'
                    if search:
                        filtro_ = filtro_persona(search, filtro)
                        ids_insidencias = PersonaSancion.objects.filter(filtro_).values_list('incidencia_id', flat=True).order_by('incidencia_id').distinct()
                        filtro &= (Q(codigo__unaccent__icontains=search) | Q(id__in=ids_insidencias))
                        data['s'] = search
                        url_vars += f'&s={search}'
                    listado = IncidenciaSancion.objects.filter(filtro).order_by('-fecha_creacion', '-estado')
                    paginator = MiPaginador(listado, 20)
                    page = int(request.GET.get('page', 1))
                    paginator.rangos_paginado(page)
                    data['paging'] = paging = paginator.get_page(page)
                    data['listado'] = paging.object_list
                    data['url_vars'] = url_vars
                    data['estados'] = ESTADO_INCIDENCIA
                    ids_departamentos = IncidenciaSancion.objects.filter(status=True).values_list('departamento_id', flat=True).order_by('departamento_id').distinct()
                    data['departamentos'] = departamentos_vigentes(ids_departamentos)
                    data['viewactivo'] = {'grupo': 'sanciones', 'action': action}
                    return render(request, 'adm_directivos/incidenciasreceptadas.html', data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'revisarincidencia':
                try:
                    template, data = get_revisar_audiencia(data, request)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'firmardocumento':
                try:
                    data['id'] = encrypt_id(request.GET['id'])
                    template = get_template("formfirmaelectronicamasiva.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': f'Error: {ex}'})

            elif action == 'detalleaudiencia':
                try:
                    template, data = get_detalleaudiencia(data, request)
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'historialfirmas':
                try:
                    template, data = get_historialfirmas(data, request)
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'generaraccionpersonal':
                try:
                    template, data = get_generar_accionpersonal(data, request)
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'marcadaspersona':
                try:
                    data['funcionario'] = Persona.objects.get(id=encrypt_id(request.GET['id']))
                    data = get_render_marcadas(data, request)
                    data['viewactivo'] = {'grupo': 'general', 'action': 'mipersonal'}
                    return render(request, "adm_directivos/marcadaspersona.html", data)
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'cargarmesesmarcadas':
                try:
                    context = get_cargar_meses_marcadas(data, request)
                    return JsonResponse(context)
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'cargarmarcadas':
                try:
                    context = get_cargar_marcadas(data, request)
                    return JsonResponse(context)
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'generarevidencia':
                try:
                    id_persona = int(request.GET['args[id_persona]'])
                    id_requisito = int(request.GET['args[id_requisito]'])
                    punto_control = int(request.GET['args[punto_control]'])
                    template = get_template('components/group_button.html')
                    data = generar_reporte_marcada(data, request)
                    data['motivorequisito'] = motivorequisito = RequisitoMotivoSancion.objects.get(pk=id_requisito)
                    return JsonResponse({'result': True, 'data': template.render(data), 'punto_control':punto_control, 'id_persona': id_persona, 'id_requisito': id_requisito, 'mensaje': 'Evidencia generada con éxito'})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Mi personal a cargo'
                data['subtitle'] = 'Listado de funcionarios a cargo'
                if search:
                    filtro = filtro_persona_principal(search, filtro)
                    data['s'] = search
                    url_vars += f'&s={search}'
                if mi_departamento:
                    listado = mi_departamento.mis_integrantes().filter(filtro).exclude(id=persona.id).order_by('nombres')
                    paginator = MiPaginador(listado, 20)
                    page = int(request.GET.get('page', 1))
                    paginator.rangos_paginado(page)
                    data['paging'] = paging = paginator.get_page(page)
                    data['listado'] = paging.object_list
                data['url_vars'] = url_vars
                data['viewactivo'] = {'grupo': 'general', 'action': 'mipersonal'}
                return render(request, 'adm_directivos/mi_personal.html', data)
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                pass




