# -*- coding: UTF-8 -*-
from django.contrib import messages
from django.contrib.admin.models import LogEntry, ADDITION, DELETION
from django.contrib.admin.utils import unquote
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction, router
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils.encoding import force_str

from bd.models import LogQuery, get_deleted_objects, LogEntryLogin
from decorators import secure_module
from bd.forms import *
from matricula.models import ProcesoMatriculaEspecial, ConfigProcesoMatriculaEspecial, \
    ConfigProcesoMatriculaEspecialAsistente
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
import sys
from django.template.loader import get_template
from sga.funciones import log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery, convertir_fecha, \
    resetear_clave, MiPaginador
from sga.models import Persona, LogEntryBackup, LogEntryBackupdos, AgregacionEliminacionMaterias, Inscripcion, Modulo, \
    ModuloGrupo
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    #
    # try:
    #     puede_realizar_accion(request, 'bd.puede_acceder_proceso_matricula_especial')
    # except Exception as ex:
    #     return HttpResponseRedirect(f"/?info={ex.__str__()}")
    adduserdata(request, data)
    persona = request.session['persona']

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addproceso':
            try:
                f = ProcesoMatriculaEspecialForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                eProcesoMatriculaEspecial = ProcesoMatriculaEspecial(version=f.cleaned_data['version'],
                                                                     sufijo=f.cleaned_data['sufijo'],
                                                                     nombre=f.cleaned_data['nombre'],
                                                                     activo=f.cleaned_data['activo'],
                                                                     )
                eProcesoMatriculaEspecial.save(request)
                motivos = f.cleaned_data['motivos']
                for motivo in motivos:
                    eProcesoMatriculaEspecial.motivo.add(motivo)
                log(u'Adiciono proceso de matricula especial: %s' % eProcesoMatriculaEspecial, request, "add")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'editproceso':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_proceso_matricula_especial')
                f = ProcesoMatriculaEspecialForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if not ProcesoMatriculaEspecial.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Proceso a editar no encontrado")
                eProcesoMatriculaEspecial = ProcesoMatriculaEspecial.objects.get(pk=request.POST['id'])
                eProcesoMatriculaEspecial.version = f.cleaned_data['version']
                eProcesoMatriculaEspecial.sufijo = f.cleaned_data['sufijo']
                eProcesoMatriculaEspecial.nombre = f.cleaned_data['nombre']
                eProcesoMatriculaEspecial.activo = f.cleaned_data['activo']
                eProcesoMatriculaEspecial.save(request)
                motivos = f.cleaned_data['motivos']
                motivos_ids = []
                for motivo in motivos:
                    motivos_ids.append(motivo.id)
                    eProcesoMatriculaEspecial.motivo.add(motivo)
                for motivo in eProcesoMatriculaEspecial.motivos():
                    if not motivo.id in motivos_ids:
                        eProcesoMatriculaEspecial.motivo.remove(motivo.id)
                for motivo in motivos:
                    eProcesoMatriculaEspecial.motivo.add(motivo)
                log(u'Edito proceso de matricula especial: %s' % eProcesoMatriculaEspecial, request, "edit")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'delproceso':
            try:
                puede_realizar_accion(request, 'bd.puede_eliminar_proceso_matricula_especial')
                if not ProcesoMatriculaEspecial.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Proceso a editar no encontrado")
                eDelete = eProcesoMatriculaEspecial = ProcesoMatriculaEspecial.objects.get(pk=request.POST['id'])
                if eProcesoMatriculaEspecial.en_uso():
                    raise NameError(u"Proceso en uso")
                eProcesoMatriculaEspecial.delete()
                log(u'Elimino de proceso de matrícula especial: %s' % eDelete, request, "del")
                messages.add_message(request, messages.SUCCESS, f'Se elimino correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el registro. %s" % ex.__str__()})

        elif action == 'loadDataConfig':
            try:
                if not ProcesoMatriculaEspecial.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Proceso no encontrado")
                eProcesoMatriculaEspecial = ProcesoMatriculaEspecial.objects.get(pk=request.POST['id'])
                aData = []
                for config in ConfigProcesoMatriculaEspecial.objects.filter(proceso=eProcesoMatriculaEspecial):
                    aResponsables = []
                    if config.tiene_responsables():
                        for asistente in config.responsables():
                            aCarreras = []
                            if asistente.tiene_carreras():
                                for carrera in asistente.carreras():
                                    aCarreras.append({"id": carrera.id,
                                                      "carrera": carrera.__str__()})
                            aResponsables.append({"id": asistente.id,
                                                  "departamento": asistente.departamento.__str__() if config.tipo_entidad == 1 else None,
                                                  "departamento_id": asistente.departamento.id if config.tipo_entidad == 1 else None,
                                                  "coordinacion": asistente.coordinacion.__str__() if config.tipo_entidad == 2 else None,
                                                  "coordinacion_id": asistente.coordinacion.id if config.tipo_entidad == 2 else None,
                                                  "responsable": asistente.responsable.__str__(),
                                                  "responsable_id": asistente.responsable.id,
                                                  "carreras": aCarreras,
                                                  "activo": asistente.activo,
                                                  })

                    aData.append({"id": config.id,
                                  "orden": config.orden,
                                  "nombre": config.nombre,
                                  "tipo_validacion": config.tipo_validacion,
                                  "tipo_validacion_verbose": config.get_tipo_validacion_display(),
                                  "tipo_entidad": config.tipo_entidad,
                                  "tipo_entidad_verbose": config.get_tipo_entidad_display(),
                                  "responsables": aResponsables,
                                  "en_uso": config.en_uso(),
                                  })
                return JsonResponse({"result": "ok", "aData": aData})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__()})

        elif action == 'addconfig':
            try:
                puede_realizar_accion(request, 'bd.puede_agregar_config_proceso_matricula_especial')
                f = ConfigProcesoMatriculaEspecialForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if not ProcesoMatriculaEspecial.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Proceso de configuración no encontrado")
                eProcesoMatriculaEspecial = ProcesoMatriculaEspecial.objects.get(pk=request.POST['id'])
                eConfigProcesoMatriculaEspecial = ConfigProcesoMatriculaEspecial(proceso=eProcesoMatriculaEspecial,
                                                                                 orden=f.cleaned_data['orden'],
                                                                                 nombre=f.cleaned_data['nombre'],
                                                                                 tipo_entidad=int(f.cleaned_data['tipo_entidad']),
                                                                                 tipo_validacion=int(f.cleaned_data['tipo_validacion']),
                                                                                 obligar_archivo=f.cleaned_data['obligar_archivo'],
                                                                                 obligar_observacion=f.cleaned_data['obligar_observacion'],
                                                                                 estado_ok=f.cleaned_data['estado_ok'],
                                                                                 estado_nok=f.cleaned_data['estado_nok'],
                                                                                 accion_ok=f.cleaned_data['accion_ok'],
                                                                                 accion_nok=f.cleaned_data['accion_nok'],
                                                                                 boton_ok_verbose=f.cleaned_data['boton_ok_verbose'],
                                                                                 boton_nok_verbose=f.cleaned_data['boton_nok_verbose'],
                                                                                 boton_ok_label=f.cleaned_data['boton_ok_label'],
                                                                                 boton_nok_label=f.cleaned_data['boton_nok_label'],
                                                                                 )
                eConfigProcesoMatriculaEspecial.save(request)
                log(u'Adiciono configuración del proceso de matricula especial: %s' % eConfigProcesoMatriculaEspecial, request, "add")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'editconfig':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_config_proceso_matricula_especial')
                f = ConfigProcesoMatriculaEspecialForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if not ConfigProcesoMatriculaEspecial.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Proceso a editar no encontrado")
                eConfigProcesoMatriculaEspecial = ConfigProcesoMatriculaEspecial.objects.get(pk=request.POST['id'])
                eConfigProcesoMatriculaEspecial.orden = f.cleaned_data['orden']
                eConfigProcesoMatriculaEspecial.nombre = f.cleaned_data['nombre']
                eConfigProcesoMatriculaEspecial.tipo_entidad = f.cleaned_data['tipo_entidad']
                eConfigProcesoMatriculaEspecial.tipo_validacion = f.cleaned_data['tipo_validacion']
                eConfigProcesoMatriculaEspecial.obligar_archivo = f.cleaned_data['obligar_archivo']
                eConfigProcesoMatriculaEspecial.obligar_observacion = f.cleaned_data['obligar_observacion']
                eConfigProcesoMatriculaEspecial.estado_ok = f.cleaned_data['estado_ok']
                eConfigProcesoMatriculaEspecial.estado_nok = f.cleaned_data['estado_nok']
                eConfigProcesoMatriculaEspecial.accion_ok = f.cleaned_data['accion_ok']
                eConfigProcesoMatriculaEspecial.accion_nok = f.cleaned_data['accion_nok']
                eConfigProcesoMatriculaEspecial.boton_ok_verbose = f.cleaned_data['boton_ok_verbose']
                eConfigProcesoMatriculaEspecial.boton_nok_verbose = f.cleaned_data['boton_nok_verbose']
                eConfigProcesoMatriculaEspecial.boton_ok_label = f.cleaned_data['boton_ok_label']
                eConfigProcesoMatriculaEspecial.boton_nok_label = f.cleaned_data['boton_nok_label']
                eConfigProcesoMatriculaEspecial.save(request)

                log(u'Edito configuración del proceso de matricula especial: %s' % eConfigProcesoMatriculaEspecial, request, "edit")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'delconfig':
            try:
                puede_realizar_accion(request, 'bd.puede_eliminar_config_proceso_matricula_especial')
                if not ConfigProcesoMatriculaEspecial.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Configuración del proceso no encontrado")
                eDelete = eConfigProcesoMatriculaEspecial = ConfigProcesoMatriculaEspecial.objects.get(pk=request.POST['id'])
                if eConfigProcesoMatriculaEspecial.en_uso():
                    raise NameError(u"Configuración en uso")
                eConfigProcesoMatriculaEspecial.delete()
                log(u'Elimino configuración del proceso de matrícula especial: %s' % eDelete, request, "del")
                return JsonResponse({"result": "ok", "mensaje": "Se elimino correctamente el registro"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el registro. %s" % ex.__str__()})

        elif action == 'addresponsable':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_config_proceso_matricula_especial')
                f = ConfigProcesoMatriculaEspecialAsistenteForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if not ConfigProcesoMatriculaEspecial.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Configuración del proceso no encontrado")
                eConfigProcesoMatriculaEspecial = ConfigProcesoMatriculaEspecial.objects.get(pk=request.POST['id'])
                eConfigProcesoMatriculaEspecialAsistente = ConfigProcesoMatriculaEspecialAsistente(configuracion=eConfigProcesoMatriculaEspecial,
                                                                                                   departamento=f.cleaned_data['departamento'] if eConfigProcesoMatriculaEspecial.tipo_entidad == 1 else None,
                                                                                                   coordinacion=f.cleaned_data['coordinacion'] if eConfigProcesoMatriculaEspecial.tipo_entidad == 2 else None,
                                                                                                   responsable=f.cleaned_data['responsable'])
                eConfigProcesoMatriculaEspecialAsistente.save(request)
                carreras = f.cleaned_data['carrera']
                for carrera in carreras:
                    eConfigProcesoMatriculaEspecialAsistente.carrera.add(carrera.id)
                log(u'Adiciono responsable configuración del proceso de matricula especial: %s' % eConfigProcesoMatriculaEspecialAsistente, request, "add")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'editresponsable':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_config_proceso_matricula_especial')
                f = ConfigProcesoMatriculaEspecialAsistenteForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if not ConfigProcesoMatriculaEspecialAsistente.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Configuración del proceso no encontrado")
                eConfigProcesoMatriculaEspecialAsistente = ConfigProcesoMatriculaEspecialAsistente.objects.get(pk=request.POST['id'])
                eConfigProcesoMatriculaEspecial = eConfigProcesoMatriculaEspecialAsistente.configuracion
                eConfigProcesoMatriculaEspecialAsistente.departamento = f.cleaned_data['departamento'] if eConfigProcesoMatriculaEspecial.tipo_entidad == 1 else None
                eConfigProcesoMatriculaEspecialAsistente.coordinacion = f.cleaned_data['coordinacion'] if eConfigProcesoMatriculaEspecial.tipo_entidad == 2 else None
                eConfigProcesoMatriculaEspecialAsistente.responsable = f.cleaned_data['responsable']
                eConfigProcesoMatriculaEspecialAsistente.save(request)
                carreras = f.cleaned_data['carrera']
                carrera_ids = []
                for carrera in carreras:
                    carrera_ids.append(carrera.id)
                for carrera in eConfigProcesoMatriculaEspecialAsistente.carreras():
                    if not carrera.id in carrera_ids:
                        eConfigProcesoMatriculaEspecialAsistente.carrera.remove(carrera.id)
                for carrera in carreras:
                    eConfigProcesoMatriculaEspecialAsistente.carrera.add(carrera.id)
                log(u'Edito responsable configuración del proceso de matricula especial: %s' % eConfigProcesoMatriculaEspecialAsistente, request, "edit")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'delresponsable':
            try:
                puede_realizar_accion(request, 'bd.puede_eliminar_config_proceso_matricula_especial')
                if not ConfigProcesoMatriculaEspecialAsistente.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Configuración del proceso no encontrado")
                eDelete = eConfigProcesoMatriculaEspecialAsistente = ConfigProcesoMatriculaEspecialAsistente.objects.get(pk=request.POST['id'])
                if eConfigProcesoMatriculaEspecialAsistente.en_uso():
                    raise NameError(u"Configuración en uso")
                eConfigProcesoMatriculaEspecialAsistente.delete()
                log(u'Elimino responsable de configuración del proceso de matrícula especial: %s' % eDelete, request, "del")
                return JsonResponse({"result": "ok", "mensaje": "Se elimino correctamente el registro"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el registro. %s" % ex.__str__()})

        elif action == 'loadCarreras':
            try:
                if not Coordinacion.objects.values("id").filter(pk=request.POST['id']).exists():
                    raise NameError(u"Coordinación no encontrada")
                eCoordinacion = Coordinacion.objects.get(pk=request.POST['id'])
                aData = []
                for carrera in eCoordinacion.carreras():
                    aData.append({"id": carrera.id,
                                  "nombre": carrera.__str__()})
                return JsonResponse({"result": "ok", "aData": aData})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

        elif action == 'removeCarrera':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_config_proceso_matricula_especial')
                if not ConfigProcesoMatriculaEspecialAsistente.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Configuración del proceso no encontrado")
                eConfigProcesoMatriculaEspecialAsistente = ConfigProcesoMatriculaEspecialAsistente.objects.get(pk=request.POST['id'])
                if not Carrera.objects.filter(pk=request.POST['idc']).exists():
                    raise NameError(u"Carrera no encontrada")
                eCarrera = Carrera.objects.get(pk=request.POST['idc'])
                # if not eConfigProcesoMatriculaEspecialAsistente.carreras().filter(carrera__id__in=[eCarrera.id]).exists():
                #     raise NameError(u"Carrera no encontrada")
                eConfigProcesoMatriculaEspecialAsistente.carrera.remove(eCarrera.id)
                return JsonResponse({"result": "ok", "mensaje": f'Se removio carrera correctamente'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'activeResponsable':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_config_proceso_matricula_especial')
                if not 'id' in request.POST:
                    raise NameError(u"Parametro de responsable no encontrado")
                if not 'activo' in request.POST:
                    raise NameError(u"Parametro de estado no encontrado")
                estado = True if int(request.POST['activo']) == 1 else False
                if not ConfigProcesoMatriculaEspecialAsistente.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Configuración del proceso no encontrado")
                eConfigProcesoMatriculaEspecialAsistente = ConfigProcesoMatriculaEspecialAsistente.objects.get(pk=request.POST['id'])
                eConfigProcesoMatriculaEspecialAsistente.activo = estado
                eConfigProcesoMatriculaEspecialAsistente.save(request)
                return JsonResponse({"result": "ok", "mensaje": f'Se guardo correctamente'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addproceso':
                try:
                    puede_realizar_accion(request, 'bd.puede_agregar_proceso_matricula_especial')
                    data['title'] = u'Adicionar proceso de matrícula especial'
                    f = ProcesoMatriculaEspecialForm()
                    data['form'] = f
                    return render(request, "adm_sistemas/especial_enroll_process/addproceso.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'editproceso':
                try:
                    puede_realizar_accion(request, 'bd.puede_modificar_proceso_matricula_especial')
                    data['title'] = u'Editar proceso de matrícula especial'
                    if not ProcesoMatriculaEspecial.objects.filter(pk=request.GET['id']).exists():
                        raise NameError(u"Proceso a editar no encontrado")
                    data['eProcesoMatriculaEspecial'] = eProcesoMatriculaEspecial = ProcesoMatriculaEspecial.objects.get(pk=request.GET['id'])
                    f = ProcesoMatriculaEspecialForm()
                    f.set_initial(eProcesoMatriculaEspecial)
                    data['form'] = f
                    return render(request, "adm_sistemas/especial_enroll_process/editproceso.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'configproceso':
                try:
                    puede_realizar_accion(request, 'bd.puede_acceder_config_proceso_matricula_especial')
                    data['title'] = u'Configuración del proceso de matrícula especial'
                    if not ProcesoMatriculaEspecial.objects.filter(pk=request.GET['id']).exists():
                        raise NameError(u"Proceso a configurar no encontrado")
                    data['eProcesoMatriculaEspecial'] = eProcesoMatriculaEspecial = ProcesoMatriculaEspecial.objects.get(pk=request.GET['id'])
                    return render(request, "adm_sistemas/especial_enroll_config/view.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'addconfig':
                try:
                    puede_realizar_accion(request, 'bd.puede_agregar_config_proceso_matricula_especial')
                    data['title'] = u'Adicionar configuración del proceso de matrícula especial'
                    if not ProcesoMatriculaEspecial.objects.filter(pk=request.GET['id']).exists():
                        raise NameError(u"Proceso de configuración no encontrado")
                    data['eProcesoMatriculaEspecial'] = eProcesoMatriculaEspecial = ProcesoMatriculaEspecial.objects.get(pk=request.GET['id'])
                    f = ConfigProcesoMatriculaEspecialForm()
                    data['form'] = f
                    return render(request, "adm_sistemas/especial_enroll_config/addconfig.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'editconfig':
                try:
                    puede_realizar_accion(request, 'bd.puede_modificar_config_proceso_matricula_especial')
                    data['title'] = u'Editar configuración del proceso de matrícula especial'
                    if not ConfigProcesoMatriculaEspecial.objects.filter(pk=request.GET['id']).exists():
                        raise NameError(u"Configuración del proceso no encontrado")
                    data['eConfigProcesoMatriculaEspecial'] = eConfigProcesoMatriculaEspecial = ConfigProcesoMatriculaEspecial.objects.get(pk=request.GET['id'])
                    f = ConfigProcesoMatriculaEspecialForm()
                    f.set_initial(eConfigProcesoMatriculaEspecial)
                    data['form'] = f
                    return render(request, "adm_sistemas/especial_enroll_config/editconfig.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'addresponsable':
                try:
                    puede_realizar_accion(request, 'bd.puede_modificar_config_proceso_matricula_especial')
                    data['title'] = u'Adicionar responsable a configuración del proceso de matrícula especial'
                    if not ConfigProcesoMatriculaEspecial.objects.filter(pk=request.GET['id']).exists():
                        raise NameError(u"Configuración del proceso no encontrado")
                    data['eConfigProcesoMatriculaEspecial'] = eConfigProcesoMatriculaEspecial = ConfigProcesoMatriculaEspecial.objects.get(pk=request.GET['id'])
                    f = ConfigProcesoMatriculaEspecialAsistenteForm()
                    f.tipo(eConfigProcesoMatriculaEspecial.tipo_entidad)
                    data['form'] = f
                    return render(request, "adm_sistemas/especial_enroll_config/addresponsable.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'editresponsable':
                try:
                    puede_realizar_accion(request, 'bd.puede_modificar_config_proceso_matricula_especial')
                    data['title'] = u'Editar responsable de configuración del proceso de matrícula especial'
                    if not ConfigProcesoMatriculaEspecialAsistente.objects.filter(pk=request.GET['id']).exists():
                        raise NameError(u"Configuración del proceso no encontrado")
                    data['eConfigProcesoMatriculaEspecialAsistente'] = eConfigProcesoMatriculaEspecialAsistente = ConfigProcesoMatriculaEspecialAsistente.objects.get(pk=request.GET['id'])
                    f = ConfigProcesoMatriculaEspecialAsistenteForm()
                    f.set_initial(eConfigProcesoMatriculaEspecialAsistente)
                    data['form'] = f
                    return render(request, "adm_sistemas/especial_enroll_config/editresponsable.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Admininistración de Procesos de Matrícula Especial'
                search = None
                ids = None
                procesos = ProcesoMatriculaEspecial.objects.filter(status=True)
                if 'id' in request.GET:
                    ids = request.GET['id']
                    procesos = procesos.filter(id=int(ids))
                if 's' in request.GET:
                    search = request.GET['s']
                    procesos = procesos.filter(Q(nombre__icontains=search)).distinct()
                paging = MiPaginador(procesos, 25)
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
                data['procesos'] = page.object_list
                return render(request, "adm_sistemas/especial_enroll_process/view.html", data)
            except Exception as ex:
                pass
