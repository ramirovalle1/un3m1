# -*- coding: UTF-8 -*-
import io
import json
import sys
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template.loader import get_template
from django.shortcuts import render

from core.firmar_documentos import firmar
from postulate.forms import ConvocatoriaTerminosForm
from sagest.models import SeccionDepartamento, Departamento, DistributivoPersona
from sga.formmodel import CustomDateInput
from .form import SolicitudFirmaDocumentoForm, FirmarDocumentoForm, DepartamentoArchivosForm, DepartamentoGestionArchivosForm, DocuPlantillaForm, PlantillaProcesoForm, RequisitoPlantillaProcesoForm, CatPlantillaForm, AperturaProcesoForm, ValidarAperturaProcesoForm, ValidarAperturaProcesoEstructuradoForm
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre, remover_caracteres_especiales_unicode, \
    remover_caracteres_tildes_unicode, puede_realizar_accion
from gdocumental.models import Persona, DepartamentoArchivos, DepartamentoArchivosGestiones, PlantillaProcesos, DocumentosPlantillas, RequisitosPlantillaProcesos, CategoriaPlantillas, SolicitudProcesoDocumental, DepartamentoArchivoCarpeta, PersonasCompartidasCarpetas, DepartamentoArchivoDocumentos
from django.db.models import Q
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
# @last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'adddepartamento':
            try:
                form = DepartamentoArchivosForm(request.POST)
                if form.is_valid():
                    if DepartamentoArchivos.objects.filter(status=True, departamento=form.cleaned_data['departamento']).exists():
                        return JsonResponse({'result': True, 'mensaje': u'Departamento ya existe en Gestión Departamental'})
                    if DepartamentoArchivos.objects.filter(nomslug=form.cleaned_data['nomslug']).exists():
                        return JsonResponse({'result': True, 'mensaje': u'Ya existe un departamento con esta nomenclatura'})
                    filtro = DepartamentoArchivos(departamento=form.cleaned_data['departamento'],
                                                  responsable=form.cleaned_data['responsable'],
                                                  filesize=form.cleaned_data['filesize'],
                                                  storagesizegb=form.cleaned_data['storagesizegb'],
                                                  nomslug=form.cleaned_data['nomslug'])
                    sizemb = form.cleaned_data['storagesizegb'] * 1024
                    filtro.storagesizemb = sizemb
                    filtro.save(request)
                    log(u'Adicion Departamento Gestión Documental: %s' % filtro, request, action)
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        if action == 'editdepartamento':
            try:
                form = DepartamentoArchivosForm(request.POST)
                filtro = DepartamentoArchivos.objects.get(id=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    filtro.responsable = form.cleaned_data['responsable']
                    filtro.filesize = form.cleaned_data['filesize']
                    filtro.storagesizegb = form.cleaned_data['storagesizegb']
                    sizemb = form.cleaned_data['storagesizegb'] * 1024
                    filtro.storagesizemb = sizemb
                    filtro.save(request)
                    log(u'Edito Departamento Gestión Documental: %s' % filtro, request, action)
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        if action == 'deldepartamento':
            try:
                with transaction.atomic():
                    instancia = DepartamentoArchivos.objects.get(pk=int(encrypt(request.POST['id'])))
                    if instancia.enuso():
                        return JsonResponse({'error': True, "message": "Departamento ya tiene gestiones asignadas."}, safe=False)
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Departamento, Gestión Documental: %s' % instancia, request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'addgestion':
            try:
                filtro = DepartamentoArchivos.objects.get(id=int(encrypt(request.POST['id'])))
                gestion = SeccionDepartamento.objects.get(id=int(encrypt(request.POST['idgestion'])))
                form = DepartamentoGestionArchivosForm(request.POST)
                if form.is_valid():
                    if DepartamentoArchivosGestiones.objects.filter(status=True, departamento=filtro, gestion=gestion).exists():
                        return JsonResponse({'result': True, 'mensaje': u'Gestión ya tiene acceso a Gestión Departamental'})
                    if DepartamentoArchivosGestiones.objects.filter(nomslug=form.cleaned_data['nomslug']).exists():
                        return JsonResponse({'result': True, 'mensaje': u'Ya existe un departamento con esta nomenclatura'})
                    filtro = DepartamentoArchivosGestiones(departamento=filtro, gestion=gestion,
                                                           responsable=form.cleaned_data['responsable'],
                                                           nomslug=form.cleaned_data['nomslug'])
                    filtro.save(request)
                    log(u'Adiciono Gestión Departamental a Gestión Documental: %s' % filtro, request, "add")
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        if action == 'editgestion':
            try:
                form = DepartamentoGestionArchivosForm(request.POST)
                filtro = DepartamentoArchivosGestiones.objects.get(id=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    filtro.responsable = form.cleaned_data['responsable']
                    filtro.save(request)
                    log(u'Edito Responsable de Gestión, Gestión Documental: %s' % filtro, request, action)
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        if action == 'delgestion':
            try:
                with transaction.atomic():
                    instancia = DepartamentoArchivosGestiones.objects.get(pk=int(encrypt(request.POST['id'])))
                    if instancia.enuso():
                        return JsonResponse({'error': True, "message": "Gestión ya esta haciendo uso de documentos."}, safe=False)
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Gestión de Departamento, Gestión Documental: %s' % instancia, request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'adddocplantilla':
            try:
                form = DocuPlantillaForm(request.POST)
                if form.is_valid():
                    if DocumentosPlantillas.objects.filter(status=True, descripcion=form.cleaned_data['descripcion']).exists():
                        return JsonResponse({'result': True, 'mensaje': f'{form.cleaned_data["descripcion"]} ya existe'})
                    filtro = DocumentosPlantillas(descripcion=form.cleaned_data['descripcion'])
                    filtro.save(request)
                    log(u'Adicion Documento para Plantilla de Procesos: %s' % filtro, request, 'add')
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        if action == 'editdocplantilla':
            try:
                form = DocuPlantillaForm(request.POST)
                filtro = DocumentosPlantillas.objects.get(id=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    filtro.descripcion = form.cleaned_data['descripcion']
                    filtro.save(request)
                    log(u'Edito Documento para Plantilla de Procesos: %s' % filtro, request, 'edit')
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        if action == 'deldocplantilla':
            try:
                with transaction.atomic():
                    instancia = DocumentosPlantillas.objects.get(pk=int(encrypt(request.POST['id'])))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Documento para Plantilla de Procesos: %s' % instancia, request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'addcatplantilla':
            try:
                form = CatPlantillaForm(request.POST)
                if form.is_valid():
                    if CategoriaPlantillas.objects.filter(status=True, descripcion=form.cleaned_data['descripcion']).exists():
                        return JsonResponse({'result': True, 'mensaje': f'{form.cleaned_data["descripcion"]} ya existe'})
                    filtro = CategoriaPlantillas(descripcion=form.cleaned_data['descripcion'])
                    filtro.save(request)
                    log(u'Adicion Categoría para Plantilla de Procesos: %s' % filtro, request, 'add')
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        if action == 'editcatplantilla':
            try:
                form = CatPlantillaForm(request.POST)
                filtro = CategoriaPlantillas.objects.get(id=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    filtro.descripcion = form.cleaned_data['descripcion']
                    filtro.save(request)
                    log(u'Edito Categoría para Plantilla de Procesos: %s' % filtro, request, 'edit')
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        if action == 'delcatplantilla':
            try:
                with transaction.atomic():
                    instancia = CategoriaPlantillas.objects.get(pk=int(encrypt(request.POST['id'])))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Categoría para Plantilla de Procesos: %s' % instancia, request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'addplantilla':
            try:
                form = PlantillaProcesoForm(request.POST)
                if form.is_valid():
                    if PlantillaProcesos.objects.filter(status=True, descripcion=form.cleaned_data['descripcion'], version=form.cleaned_data['version']).exists():
                        return JsonResponse({'result': True, 'mensaje': f'{form.cleaned_data["descripcion"]} - {form.cleaned_data["version"]} ya existe'})
                    filtro = PlantillaProcesos(nomenclatura=form.cleaned_data['nomenclatura'], categoria=form.cleaned_data['categoria'], version=form.cleaned_data['version'], descripcion=form.cleaned_data['descripcion'], vigente=form.cleaned_data['vigente'])
                    filtro.save(request)
                    log(u'Adicion Plantilla de Procesos: %s' % filtro, request, 'add')
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        if action == 'editplantilla':
            try:
                form = PlantillaProcesoForm(request.POST)
                filtro = PlantillaProcesos.objects.get(id=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    filtro.categoria = form.cleaned_data['categoria']
                    filtro.nomenclatura = form.cleaned_data['nomenclatura']
                    filtro.version = form.cleaned_data['version']
                    filtro.descripcion = form.cleaned_data['descripcion']
                    filtro.vigente = form.cleaned_data['vigente']
                    filtro.save(request)
                    log(u'Edito Plantilla de Procesos: %s' % filtro, request, 'edit')
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        if action == 'delplantilla':
            try:
                with transaction.atomic():
                    instancia = PlantillaProcesos.objects.get(pk=int(encrypt(request.POST['id'])))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Plantilla de Procesos: %s' % instancia, request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'addreqplantilla':
            try:
                cab_ = PlantillaProcesos.objects.get(id=int(encrypt(request.POST['id'])))
                form = RequisitoPlantillaProcesoForm(request.POST)
                if form.is_valid():
                    if RequisitosPlantillaProcesos.objects.filter(cab=cab_, status=True, orden=form.cleaned_data['orden'], documento=form.cleaned_data['documento']).exists():
                        return JsonResponse({'result': True, 'mensaje': f'{form.cleaned_data["orden"]} - {form.cleaned_data["documento"]} ya existe'})
                    filtro = RequisitosPlantillaProcesos(cab=cab_, ref=form.cleaned_data['ref'], orden=form.cleaned_data['orden'], documento=form.cleaned_data['documento'],
                                                         responsable=form.cleaned_data['responsable'],
                                                         horas=form.cleaned_data['horas'], obligatorio=form.cleaned_data['obligatorio'],
                                                         departamentoreponsable=form.cleaned_data['departamentoreponsable'])
                    filtro.save(request)
                    log(u'Adicion Requisito Plantilla de Procesos: %s' % filtro, request, 'add')
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        if action == 'editreqplantilla':
            try:
                form = RequisitoPlantillaProcesoForm(request.POST)
                filtro = RequisitosPlantillaProcesos.objects.get(id=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    filtro.ref = form.cleaned_data['ref']
                    filtro.orden = form.cleaned_data['orden']
                    filtro.documento = form.cleaned_data['documento']
                    filtro.responsable = form.cleaned_data['responsable']
                    filtro.horas = form.cleaned_data['horas']
                    filtro.obligatorio = form.cleaned_data['obligatorio']
                    filtro.departamentoreponsable = form.cleaned_data['departamentoreponsable']
                    filtro.save(request)
                    log(u'Edito Requisito Plantilla de Procesos: %s' % filtro, request, 'edit')
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        if action == 'delreqplantilla':
            try:
                with transaction.atomic():
                    instancia = RequisitosPlantillaProcesos.objects.get(pk=int(encrypt(request.POST['id'])))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Requisito Plantilla de Procesos: %s' % instancia, request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'validarsolicitud':
            try:
                filtro_ = SolicitudProcesoDocumental.objects.get(id=int(encrypt(request.POST['id'])))
                if not filtro_.estado == 1:
                    txtestado_ = 'aprobada' if filtro_.estado == 2 else 'rechazada'
                    return JsonResponse({'result': True, 'mensaje': f'Solicitud ya fue {txtestado_}'})
                if filtro_.tipo == 1:
                    form = ValidarAperturaProcesoEstructuradoForm(request.POST, request.FILES)
                else:
                    form = ValidarAperturaProcesoForm(request.POST, request.FILES)
                if int(request.POST['estado']) == 3:
                    form.desactivar()
                if form.is_valid():
                    filtro_.estado = form.cleaned_data['estado']
                    filtro_.nombre = form.cleaned_data['nombre']
                    filtro_.observacion_validacion = form.cleaned_data['observacion_validacion']

                    if not int(filtro_.estado) == 3:
                        if form.cleaned_data['finicio'] < filtro_.fecha_creacion.date():
                            return JsonResponse({'result': True, 'mensaje': f'La fecha de inicio del proceso debe ser mayor o igual a la fecha actual.'})
                        if filtro_.tipo == 1:
                            if not RequisitosPlantillaProcesos.objects.values('id').filter(status=True, cab=form.cleaned_data['plantilla']).exists():
                                return JsonResponse({'result': True, 'mensaje': f'Plantilla no tiene configurado requisitos'})
                        if filtro_.tipo == 1:
                            filtro_.categoria = form.cleaned_data['categoria']
                            filtro_.plantilla = form.cleaned_data['plantilla']
                        filtro_.finicio = form.cleaned_data['finicio']

                    filtro_.save(request)
                    if filtro_.estado == '2':
                        folder_ = DepartamentoArchivoCarpeta(solicitud=filtro_, gestion=filtro_.gestion, nombre=form.cleaned_data['nombre'],
                                                             parent=0, propietario=filtro_.persona, cerrada=False)
                        folder_.save(request)
                        compartido_ = PersonasCompartidasCarpetas(carpeta=folder_, rol=1, persona=filtro_.persona)
                        compartido_.save(request)
                        if filtro_.tipo == 1:
                            requisitos = RequisitosPlantillaProcesos.objects.filter(status=True, cab=form.cleaned_data['plantilla']).order_by('orden')
                            for requisito in requisitos:
                                file_ = DepartamentoArchivoDocumentos(carpeta=folder_, requisito=requisito,  nombre=requisito.documento.descripcion, estado=1,
                                                                      orden=requisito.orden, responsable=requisito.responsable,  horas=requisito.horas,
                                                                      obligatorio=requisito.obligatorio, departamentoreponsable=requisito.departamentoreponsable)
                                qsdistributivo = DistributivoPersona.objects.filter(status=True, denominacionpuesto=requisito.responsable)
                                if qsdistributivo.exists():
                                    file_.propietario = qsdistributivo.first().persona
                                file_.save(request)
                    log(f'Valido Solicitud de Apertura Proceso: {filtro_} | {filtro_.get_estado_display()}', request, 'add')
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
                else:
                    return JsonResponse({'result': True, 'mensaje': f'Complete los datos: {form.errors}'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'adddepartamento':
                try:
                    data['title'] = u'Adicionar Departamento'
                    iddepartamento = int(encrypt(request.GET['id']))
                    depa_ = Departamento.objects.get(pk=iddepartamento)
                    form = DepartamentoArchivosForm()
                    if depa_.responsable:
                        form.fields['responsable'].queryset = Persona.objects.filter(id=depa_.responsable.id)
                        form.fields['responsable'].initial = depa_.responsable.id
                    else:
                        form.fields['responsable'].queryset = Persona.objects.none()
                    form.fields['departamento'].queryset = Departamento.objects.filter(status=True, id=iddepartamento).distinct().order_by('nombre')
                    form.fields['departamento'].initial = depa_
                    data['form'] = form
                    template = get_template("adm_gestiondocumental/modal/formdepartamento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'editdepartamento':
                try:
                    data['title'] = u'Editar Departamento'
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = DepartamentoArchivos.objects.get(id=id)
                    initial = model_to_dict(filtro)
                    form = DepartamentoArchivosForm(initial=initial)
                    if filtro.responsable:
                        form.fields['responsable'].queryset = Persona.objects.filter(id=filtro.responsable.id)
                    else:
                        form.fields['responsable'].queryset = Persona.objects.none()
                    form.fields['nomslug'].widget.attrs['readonly'] = True
                    form.fields['departamento'].widget.attrs['readonly'] = True
                    form.fields['departamento'].widget.attrs['class'] = 'noselect2'
                    form.fields['departamento'].widget.attrs['required'] = False
                    data['form'] = form
                    template = get_template("adm_gestiondocumental/modal/formdepartamento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'buscarpersonas':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    querybase = Persona.objects.filter(status=True, distributivopersona__isnull=False, administrativo__isnull=False).order_by('apellido1')
                    if len(s) == 1:
                        per = querybase.filter((Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(cedula__icontains=q) |  Q(apellido2__icontains=q) | Q(cedula__contains=q)), Q(status=True)).distinct()[:15]
                    elif len(s) == 2:
                        per = querybase.filter((Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) |
                                                       (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1])) |
                                                       (Q(nombres__icontains=s[0]) & Q(apellido1__contains=s[1]))).filter(status=True).distinct()[:15]
                    else:
                        per = querybase.filter((Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(apellido2__contains=s[2])) |
                                                       (Q(nombres__contains=s[0]) & Q(nombres__contains=s[1]) & Q(apellido1__contains=s[2]))).filter(status=True).distinct()[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {}".format(x.cedula, x.nombre_completo())} for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'viewarbol':
                try:
                    data['url_'] = request.path
                    data['id'] = id = encrypt(request.GET['id'])
                    data['filtro'] = filtro = DepartamentoArchivos.objects.get(pk=id)
                    data['title'] = f'ESTRUCTURA DE ARCHIVOS DE {filtro.departamento}'
                    data['listado'] = listado = DepartamentoArchivosGestiones.objects.filter(status=True, departamento=filtro).order_by('gestion__descripcion')
                    return render(request, 'adm_gestiondocumental/viewarbol.html', data)
                except Exception as ex:
                    pass

            if action == 'gestiones':
                try:
                    data['id'] = id = encrypt(request.GET['id'])
                    data['filtro'] = filtro = DepartamentoArchivos.objects.get(pk=id)
                    data['title'] = f'GESTIONES DE {filtro.departamento}'
                    data['listado'] = listado = DepartamentoArchivosGestiones.objects.filter(status=True, departamento=filtro).order_by('gestion__descripcion')
                    data['listgestion'] = listgestion = filtro.departamento.secciondepartamento_set.filter(status=True).exclude(id__in=listado.values_list('gestion__id', flat=True)).order_by('descripcion')
                    return render(request, 'adm_gestiondocumental/viewgestiones.html', data)
                except Exception as ex:
                    pass

            if action == 'addgestion':
                try:
                    data['title'] = u'Dar Acceso a Gestión'
                    data['id'] = iddepartamento = int(encrypt(request.GET['iddepartamento']))
                    data['idgestion'] = idgestion = int(encrypt(request.GET['idgestion']))
                    filtro = DepartamentoArchivos.objects.get(pk=iddepartamento)
                    gestion = SeccionDepartamento.objects.get(pk=idgestion)
                    form = DepartamentoGestionArchivosForm()
                    if gestion.responsable:
                        form.fields['responsable'].queryset = Persona.objects.filter(id=gestion.responsable.id)
                        form.fields['responsable'].initial = gestion.responsable.id
                    else:
                        form.fields['responsable'].queryset = Persona.objects.none()
                    data['form'] = form
                    template = get_template("adm_gestiondocumental/modal/formgestion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editgestion':
                try:
                    data['title'] = u'Editar Gestión'
                    data['id'] = id = int(encrypt(request.GET['id']))
                    filtro = DepartamentoArchivosGestiones.objects.get(pk=id)
                    initial = model_to_dict(filtro)
                    form = DepartamentoGestionArchivosForm(initial=initial)
                    form.fields['nomslug'].widget.attrs['readonly'] = True
                    if filtro.responsable:
                        form.fields['responsable'].queryset = Persona.objects.filter(id=filtro.responsable.id)
                        form.fields['responsable'].initial = filtro.responsable.id
                    else:
                        form.fields['responsable'].queryset = Persona.objects.none()
                    data['form'] = form
                    template = get_template("adm_gestiondocumental/modal/formgestion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'vercarpetas':
                try:
                    data['id'] = id = encrypt(request.GET['id'])
                    data['listado'] = listado = DepartamentoArchivosGestiones.objects.filter(pk=id)
                    data['filtro'] = filtro = listado.first()
                    data['url_'] = f'{request.path}?action=gestiones&id={encrypt(filtro.departamento.id)}'
                    data['title'] = u'ARBOL DE {}'.format(filtro.gestion.descripcion)
                    return render(request, 'adm_gestiondocumental/viewarbol.html', data)
                except Exception as ex:
                    pass

            if action == 'listdocplantillas':
                try:
                    data['title'] = u'Documentos para plantilla de procesos'

                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), f'&action={action}'

                    if search:
                        data['s'] = search
                        filtro = filtro & (Q(descripcion__unaccent__icontains=search))
                        url_vars += '&s=' + search

                    listado = DocumentosPlantillas.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(listado, 25)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, "adm_gestiondocumental/viewdocumentosplantilla.html", data)
                except Exception as ex:
                    print('Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, ex))

            if action == 'adddocplantilla':
                try:
                    data['title'] = u'Adicionar Documento para Plantilla'
                    form = DocuPlantillaForm()
                    data['form'] = form
                    template = get_template("adm_gestiondocumental/modal/formdocuplantilla.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'editdocplantilla':
                try:
                    data['title'] = u'Editar Documento para Plantilla'
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = DocumentosPlantillas.objects.get(id=id)
                    form = DocuPlantillaForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("adm_gestiondocumental/modal/formdocuplantilla.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'listcatplantillas':
                try:
                    data['title'] = u'Categoría para plantilla de procesos'

                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), f'&action={action}'

                    if search:
                        data['s'] = search
                        filtro = filtro & (Q(descripcion__unaccent__icontains=search))
                        url_vars += '&s=' + search

                    listado = CategoriaPlantillas.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(listado, 25)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, "adm_gestiondocumental/viewcategoriaplantilla.html", data)
                except Exception as ex:
                    print('Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, ex))

            if action == 'addcatplantilla':
                try:
                    data['title'] = u'Adicionar Categoría para Plantilla'
                    form = CatPlantillaForm()
                    data['form'] = form
                    template = get_template("adm_gestiondocumental/modal/formcatplantilla.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'editcatplantilla':
                try:
                    data['title'] = u'Editar Categoría para Plantilla'
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = CategoriaPlantillas.objects.get(id=id)
                    form = CatPlantillaForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("adm_gestiondocumental/modal/formcatplantilla.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'listplantillas':
                try:
                    data['title'] = u'Plantilla de Procesos'

                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), f'&action={action}'

                    if search:
                        data['s'] = search
                        filtro = filtro & (Q(descripcion__unaccent__icontains=search))
                        url_vars += '&s=' + search

                    listado = PlantillaProcesos.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(listado, 25)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, "adm_gestiondocumental/viewplantillaprocesos.html", data)
                except Exception as ex:
                    print('Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, ex))

            if action == 'addplantilla':
                try:
                    data['title'] = u'Adicionar Plantilla'
                    form = PlantillaProcesoForm()
                    data['form'] = form
                    template = get_template("adm_gestiondocumental/modal/formplantilla.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'editplantilla':
                try:
                    data['title'] = u'Editar Plantilla'
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = PlantillaProcesos.objects.get(id=id)
                    form = PlantillaProcesoForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("adm_gestiondocumental/modal/formplantilla.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'plantillarequisitos':
                try:
                    data['title'] = u'Requisitos de Plantilla'
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = PlantillaProcesos.objects.get(id=id)
                    data['listado'] = listado = RequisitosPlantillaProcesos.objects.filter(status=True, cab=filtro).order_by('orden')
                    return render(request, "adm_gestiondocumental/viewplantillarequisitos.html", data)
                except Exception as ex:
                    pass

            if action == 'addreqplantilla':
                try:
                    data['title'] = u'Adicionar Requisito Plantilla'
                    data['id'] = id = int(encrypt(request.GET['id']))
                    filtro = RequisitosPlantillaProcesos.objects.values('orden').filter(cab__id=id).order_by('orden')
                    orden_ = 1 if not filtro.exists() else filtro.last()['orden'] + 1
                    form = RequisitoPlantillaProcesoForm()
                    form.fields['orden'].initial = orden_
                    data['form'] = form
                    template = get_template("adm_gestiondocumental/modal/formrequisito.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'editreqplantilla':
                try:
                    data['title'] = u'Editar Requisito Plantilla'
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = RequisitosPlantillaProcesos.objects.get(id=id)
                    form = RequisitoPlantillaProcesoForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("adm_gestiondocumental/modal/formrequisito.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'solprocesos':
                try:
                    data['title'] = u'Solicitudes de procesos'

                    criterio, desde, hasta, departamento, filtro, url_vars = request.GET.get('criterio', ''), request.GET.get('desde', ''), request.GET.get('hasta', ''), request.GET.get('departamento', ''), Q(status=True), f'&action={action}'

                    if criterio:
                        data['criterio'] = criterio
                        s = criterio.split(' ')
                        if len(s) == 1:
                            filtro = filtro & (Q(persona__cedula__icontains=criterio) |
                                               Q(persona__nombres__unaccent__icontains=criterio))
                        if len(s) >= 2:
                            filtro = filtro & ((Q(persona__apellido1__icontains=s[0]) & Q(persona__apellido2__icontains=s[1])) |
                                               Q(persona__nombres__unaccent__icontains=criterio))
                        url_vars += '&criterio=' + criterio

                    if desde:
                        data['desde'] = desde
                        filtro = filtro & (Q(fecha_creacion__gte=desde))
                        url_vars += '&desde=' + desde

                    if hasta:
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha_creacion__lte=hasta)
                        url_vars += "&hasta={}".format(hasta)

                    if departamento:
                        data['departamento'] = int(departamento)
                        filtro = filtro & Q(gestion__departamento__id=departamento)
                        url_vars += "&departamento{}".format(departamento)

                    listado = SolicitudProcesoDocumental.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(listado, 15)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    data['departamentolist'] = departamentolist = DepartamentoArchivos.objects.values('departamento__nombre', 'id').filter(status=True).order_by('departamento__nombre')
                    return render(request, "adm_gestiondocumental/viewsoliprocesos.html", data)
                except Exception as ex:
                    print('Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, ex))

            if action == 'validarsolicitud':
                try:
                    data['title'] = u'Validar Solicitud'
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = SolicitudProcesoDocumental.objects.get(id=id)
                    if filtro.tipo == 1:
                        form = ValidarAperturaProcesoEstructuradoForm(initial=model_to_dict(filtro))
                        form.fields['plantilla'].queryset = PlantillaProcesos.objects.none()
                    else:
                        form = ValidarAperturaProcesoForm(initial=model_to_dict(filtro))
                    form.fields['nombre'].initial = ''
                    data['form'] = form
                    template = get_template("adm_gestiondocumental/modal/formvalidarproceso.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'buscarplantilla':
                id = request.GET['id']
                filtro = CategoriaPlantillas.objects.get(pk=id)
                listado = PlantillaProcesos.objects.filter(categoria=filtro, status=True, vigente=True)
                if 'search' in request.GET:
                    search = request.GET['search']
                    listado = listado.filter(Q(nomenclatura__icontains=search) | Q(descripcion__icontains=search))
                resp = [{'id': x.pk, 'text': f'{x.descripcion} - {x.version}'} for x in listado.order_by('nomenclatura')]
                return HttpResponse(json.dumps({'state': True, 'result': resp}))

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Gestión Documental'

            search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''

            if search:
                filtro = filtro & (Q(departamento__nombre__unaccent__icontains=search))
                url_vars += '&s=' + search
                data['s'] = search

            listado = DepartamentoArchivos.objects.filter(filtro).order_by('-id')
            paging = MiPaginador(listado, 25)
            p = 1
            try:
                paginasesion = 1
                if 'paginador' in request.session:
                    paginasesion = int(request.session['paginador'])
                if 'page' in request.GET:
                    p = int(request.GET['page'])
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
            data["url_vars"] = url_vars
            data['listado'] = page.object_list
            data['email_domain'] = EMAIL_DOMAIN
            data['listcount'] = len(listado)
            data['notisolicitud'] = SolicitudProcesoDocumental.objects.values('id').filter(status=True, estado=1).count()
            data['listDepartamentos'] = Departamento.objects.filter(tipo=1, status=True, integrantes__isnull=False, departamentoarchivos__isnull=True).distinct().order_by('nombre')
            return render(request, 'adm_gestiondocumental/view.html', data)
