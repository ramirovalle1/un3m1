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
from matricula.models import ConfigProcesoRetiroMatricula, ConfigProcesoRetiroMatriculaAsistente, ProcesoRetiroMatricula
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
    #     puede_realizar_accion(request, 'bd.puede_acceder_proceso_retiro_matricula')
    # except Exception as ex:
    #     return HttpResponseRedirect(f"/?info={ex.__str__()}")
    adduserdata(request, data)
    persona = request.session['persona']

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addproceso':
            try:
                f = ProcesoRetiroMatriculaForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                eProcesoRetiroMatricula = ProcesoRetiroMatricula(version=f.cleaned_data['version'],
                                                                 sufijo=f.cleaned_data['sufijo'],
                                                                 nombre=f.cleaned_data['nombre'],
                                                                 activo=f.cleaned_data['activo'],
                                                                 )
                eProcesoRetiroMatricula.save(request)
                motivos = f.cleaned_data['motivos']
                for motivo in motivos:
                    eProcesoRetiroMatricula.motivo.add(motivo)
                log(u'Adiciono proceso de retiro matricula: %s' % eProcesoRetiroMatricula, request, "add")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'editproceso':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_proceso_retiro_matricula')
                f = ProcesoRetiroMatriculaForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if not ProcesoRetiroMatricula.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Proceso a editar no encontrado")
                eProcesoRetiroMatricula = ProcesoRetiroMatricula.objects.get(pk=request.POST['id'])
                eProcesoRetiroMatricula.version = f.cleaned_data['version']
                eProcesoRetiroMatricula.sufijo = f.cleaned_data['sufijo']
                eProcesoRetiroMatricula.nombre = f.cleaned_data['nombre']
                eProcesoRetiroMatricula.activo = f.cleaned_data['activo']
                eProcesoRetiroMatricula.save(request)
                motivos = f.cleaned_data['motivos']
                motivos_ids = []
                for motivo in motivos:
                    motivos_ids.append(motivo.id)
                    eProcesoRetiroMatricula.motivo.add(motivo)
                for motivo in eProcesoRetiroMatricula.motivos():
                    if not motivo.id in motivos_ids:
                        eProcesoRetiroMatricula.motivo.remove(motivo.id)
                for motivo in motivos:
                    eProcesoRetiroMatricula.motivo.add(motivo)
                log(u'Edito proceso de retiro matricula: %s' % eProcesoRetiroMatricula, request, "edit")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'delproceso':
            try:
                puede_realizar_accion(request, 'bd.puede_eliminar_proceso_retiro_matricula')
                if not ProcesoRetiroMatricula.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Proceso a editar no encontrado")
                eDelete = eProcesoRetiroMatricula = ProcesoRetiroMatricula.objects.get(pk=request.POST['id'])
                if eProcesoRetiroMatricula.en_uso():
                    raise NameError(u"Proceso en uso")
                eProcesoRetiroMatricula.delete()
                log(u'Elimino de proceso de retiro matrícula: %s' % eDelete, request, "del")
                messages.add_message(request, messages.SUCCESS, f'Se elimino correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el registro. %s" % ex.__str__()})

        elif action == 'loadDataConfig':
            try:
                if not ProcesoRetiroMatricula.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Proceso no encontrado")
                eProcesoRetiroMatricula = ProcesoRetiroMatricula.objects.get(pk=request.POST['id'])
                aData = []
                for config in ConfigProcesoRetiroMatricula.objects.filter(proceso=eProcesoRetiroMatricula):
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
                puede_realizar_accion(request, 'bd.puede_agregar_config_proceso_retiro_matricula')
                f = ConfigProcesoRetiroMatriculaForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if not ProcesoRetiroMatricula.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Proceso de configuración no encontrado")
                eProcesoRetiroMatricula = ProcesoRetiroMatricula.objects.get(pk=request.POST['id'])
                eConfigProcesoRetiroMatricula = ConfigProcesoRetiroMatricula(proceso=eProcesoRetiroMatricula,
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
                                                                             tiempo_atencion=f.cleaned_data['tiempo_atencion'],
                                                                             tipo_tiempo_atencion=f.cleaned_data['tipo_tiempo_atencion'],
                                                                             )
                eConfigProcesoRetiroMatricula.save(request)
                log(u'Adiciono configuración del proceso de retiro matricula: %s' % eConfigProcesoRetiroMatricula, request, "add")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'editconfig':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_config_proceso_retiro_matricula')
                f = ConfigProcesoRetiroMatriculaForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if not ConfigProcesoRetiroMatricula.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Proceso a editar no encontrado")
                eConfigProcesoRetiroMatricula = ConfigProcesoRetiroMatricula.objects.get(pk=request.POST['id'])
                eConfigProcesoRetiroMatricula.orden = f.cleaned_data['orden']
                eConfigProcesoRetiroMatricula.nombre = f.cleaned_data['nombre']
                eConfigProcesoRetiroMatricula.tipo_entidad = f.cleaned_data['tipo_entidad']
                eConfigProcesoRetiroMatricula.tipo_validacion = f.cleaned_data['tipo_validacion']
                eConfigProcesoRetiroMatricula.obligar_archivo = f.cleaned_data['obligar_archivo']
                eConfigProcesoRetiroMatricula.obligar_observacion = f.cleaned_data['obligar_observacion']
                eConfigProcesoRetiroMatricula.estado_ok = f.cleaned_data['estado_ok']
                eConfigProcesoRetiroMatricula.estado_nok = f.cleaned_data['estado_nok']
                eConfigProcesoRetiroMatricula.accion_ok = f.cleaned_data['accion_ok']
                eConfigProcesoRetiroMatricula.accion_nok = f.cleaned_data['accion_nok']
                eConfigProcesoRetiroMatricula.boton_ok_verbose = f.cleaned_data['boton_ok_verbose']
                eConfigProcesoRetiroMatricula.boton_nok_verbose = f.cleaned_data['boton_nok_verbose']
                eConfigProcesoRetiroMatricula.boton_ok_label = f.cleaned_data['boton_ok_label']
                eConfigProcesoRetiroMatricula.boton_nok_label = f.cleaned_data['boton_nok_label']
                eConfigProcesoRetiroMatricula.tiempo_atencion = f.cleaned_data['tiempo_atencion']
                eConfigProcesoRetiroMatricula.tipo_tiempo_atencion = f.cleaned_data['tipo_tiempo_atencion']
                eConfigProcesoRetiroMatricula.save(request)

                log(u'Edito configuración del proceso de retiro matricula: %s' % eConfigProcesoRetiroMatricula, request, "edit")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'delconfig':
            try:
                puede_realizar_accion(request, 'bd.puede_eliminar_config_proceso_retiro_matricula')
                if not ConfigProcesoRetiroMatricula.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Configuración del proceso no encontrado")
                eDelete = eConfigProcesoRetiroMatricula = ConfigProcesoRetiroMatricula.objects.get(pk=request.POST['id'])
                if eConfigProcesoRetiroMatricula.en_uso():
                    raise NameError(u"Configuración en uso")
                eConfigProcesoRetiroMatricula.delete()
                log(u'Elimino configuración del proceso de retiro matricula: %s' % eDelete, request, "del")
                return JsonResponse({"result": "ok", "mensaje": "Se elimino correctamente el registro"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el registro. %s" % ex.__str__()})

        elif action == 'addresponsable':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_config_proceso_retiro_matricula')
                f = ConfigProcesoRetiroMatriculaAsistenteForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if not ConfigProcesoRetiroMatricula.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Configuración del proceso no encontrado")
                eConfigProcesoRetiroMatricula = ConfigProcesoRetiroMatricula.objects.get(pk=request.POST['id'])
                eConfigProcesoRetiroMatriculaAsistente = ConfigProcesoRetiroMatriculaAsistente(configuracion=eConfigProcesoRetiroMatricula,
                                                                                                   departamento=f.cleaned_data['departamento'] if eConfigProcesoRetiroMatricula.tipo_entidad == 1 else None,
                                                                                                   coordinacion=f.cleaned_data['coordinacion'] if eConfigProcesoRetiroMatricula.tipo_entidad == 2 else None,
                                                                                                   responsable=f.cleaned_data['responsable'])
                eConfigProcesoRetiroMatriculaAsistente.save(request)
                carreras = f.cleaned_data['carrera']
                for carrera in carreras:
                    eConfigProcesoRetiroMatriculaAsistente.carrera.add(carrera.id)
                log(u'Adiciono responsable configuración del proceso de retiro matricula: %s' % eConfigProcesoRetiroMatriculaAsistente, request, "add")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'editresponsable':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_config_proceso_retiro_matricula')
                f = ConfigProcesoRetiroMatriculaAsistenteForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if not ConfigProcesoRetiroMatriculaAsistente.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Configuración del proceso no encontrado")
                eConfigProcesoRetiroMatriculaAsistente = ConfigProcesoRetiroMatriculaAsistente.objects.get(pk=request.POST['id'])
                eConfigProcesoRetiroMatricula = eConfigProcesoRetiroMatriculaAsistente.configuracion
                eConfigProcesoRetiroMatriculaAsistente.departamento = f.cleaned_data['departamento'] if eConfigProcesoRetiroMatricula.tipo_entidad == 1 else None
                eConfigProcesoRetiroMatriculaAsistente.coordinacion = f.cleaned_data['coordinacion'] if eConfigProcesoRetiroMatricula.tipo_entidad == 2 else None
                eConfigProcesoRetiroMatriculaAsistente.responsable = f.cleaned_data['responsable']
                eConfigProcesoRetiroMatriculaAsistente.save(request)
                carreras = f.cleaned_data['carrera']
                carrera_ids = []
                for carrera in carreras:
                    carrera_ids.append(carrera.id)
                for carrera in eConfigProcesoRetiroMatriculaAsistente.carreras():
                    if not carrera.id in carrera_ids:
                        eConfigProcesoRetiroMatriculaAsistente.carrera.remove(carrera.id)
                for carrera in carreras:
                    eConfigProcesoRetiroMatriculaAsistente.carrera.add(carrera.id)
                log(u'Edito responsable configuración del proceso de retiro matricula: %s' % eConfigProcesoRetiroMatriculaAsistente, request, "edit")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'delresponsable':
            try:
                puede_realizar_accion(request, 'bd.puede_eliminar_config_proceso_retiro_matricula')
                if not ConfigProcesoRetiroMatriculaAsistente.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Configuración del proceso no encontrado")
                eDelete = eConfigProcesoRetiroMatriculaAsistente = ConfigProcesoRetiroMatriculaAsistente.objects.get(pk=request.POST['id'])
                if eConfigProcesoRetiroMatriculaAsistente.en_uso():
                    raise NameError(u"Configuración en uso")
                eConfigProcesoRetiroMatriculaAsistente.delete()
                log(u'Elimino responsable de configuración del proceso de retiro matricula: %s' % eDelete, request, "del")
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
                puede_realizar_accion(request, 'bd.puede_modificar_config_proceso_retiro_matricula')
                if not ConfigProcesoRetiroMatriculaAsistente.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Configuración del proceso no encontrado")
                eConfigProcesoRetiroMatriculaAsistente = ConfigProcesoRetiroMatriculaAsistente.objects.get(pk=request.POST['id'])
                if not Carrera.objects.filter(pk=request.POST['idc']).exists():
                    raise NameError(u"Carrera no encontrada")
                eCarrera = Carrera.objects.get(pk=request.POST['idc'])
                # if not eConfigProcesoRetiroMatriculaAsistente.carreras().filter(carrera__id__in=[eCarrera.id]).exists():
                #     raise NameError(u"Carrera no encontrada")
                eConfigProcesoRetiroMatriculaAsistente.carrera.remove(eCarrera.id)
                return JsonResponse({"result": "ok", "mensaje": f'Se removio carrera correctamente'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'activeResponsable':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_config_proceso_retiro_matricula')
                if not 'id' in request.POST:
                    raise NameError(u"Parametro de responsable no encontrado")
                if not 'activo' in request.POST:
                    raise NameError(u"Parametro de estado no encontrado")
                estado = True if int(request.POST['activo']) == 1 else False
                if not ConfigProcesoRetiroMatriculaAsistente.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Configuración del proceso no encontrado")
                eConfigProcesoRetiroMatriculaAsistente = ConfigProcesoRetiroMatriculaAsistente.objects.get(pk=request.POST['id'])
                eConfigProcesoRetiroMatriculaAsistente.activo = estado
                eConfigProcesoRetiroMatriculaAsistente.save(request)
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
                    puede_realizar_accion(request, 'bd.puede_agregar_proceso_retiro_matricula')
                    data['title'] = u'Adicionar proceso de retiro matricula'
                    f = ProcesoRetiroMatriculaForm()
                    data['form'] = f
                    return render(request, "adm_sistemas/remove_enroll_process/addproceso.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'editproceso':
                try:
                    puede_realizar_accion(request, 'bd.puede_modificar_proceso_retiro_matricula')
                    data['title'] = u'Editar proceso de retiro matricula'
                    if not ProcesoRetiroMatricula.objects.filter(pk=request.GET['id']).exists():
                        raise NameError(u"Proceso a editar no encontrado")
                    data['eProcesoRetiroMatricula'] = eProcesoRetiroMatricula = ProcesoRetiroMatricula.objects.get(pk=request.GET['id'])
                    f = ProcesoRetiroMatriculaForm()
                    f.set_initial(eProcesoRetiroMatricula)
                    data['form'] = f
                    return render(request, "adm_sistemas/remove_enroll_process/editproceso.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'configproceso':
                try:
                    puede_realizar_accion(request, 'bd.puede_acceder_config_proceso_retiro_matricula')
                    data['title'] = u'Configuración del proceso de retiro matricula'
                    if not ProcesoRetiroMatricula.objects.filter(pk=request.GET['id']).exists():
                        raise NameError(u"Proceso a configurar no encontrado")
                    data['eProcesoRetiroMatricula'] = eProcesoRetiroMatricula = ProcesoRetiroMatricula.objects.get(pk=request.GET['id'])
                    return render(request, "adm_sistemas/remove_enroll_config/view.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'addconfig':
                try:
                    puede_realizar_accion(request, 'bd.puede_agregar_config_proceso_retiro_matricula')
                    data['title'] = u'Adicionar configuración del proceso de retiro matricula'
                    if not ProcesoRetiroMatricula.objects.filter(pk=request.GET['id']).exists():
                        raise NameError(u"Proceso de configuración no encontrado")
                    data['eProcesoRetiroMatricula'] = eProcesoRetiroMatricula = ProcesoRetiroMatricula.objects.get(pk=request.GET['id'])
                    f = ConfigProcesoRetiroMatriculaForm()
                    data['form'] = f
                    return render(request, "adm_sistemas/remove_enroll_config/addconfig.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'editconfig':
                try:
                    puede_realizar_accion(request, 'bd.puede_modificar_config_proceso_retiro_matricula')
                    data['title'] = u'Editar configuración del proceso de retiro matricula'
                    if not ConfigProcesoRetiroMatricula.objects.filter(pk=request.GET['id']).exists():
                        raise NameError(u"Configuración del proceso no encontrado")
                    data['eConfigProcesoRetiroMatricula'] = eConfigProcesoRetiroMatricula = ConfigProcesoRetiroMatricula.objects.get(pk=request.GET['id'])
                    f = ConfigProcesoRetiroMatriculaForm()
                    f.set_initial(eConfigProcesoRetiroMatricula)
                    data['form'] = f
                    return render(request, "adm_sistemas/remove_enroll_config/editconfig.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'addresponsable':
                try:
                    puede_realizar_accion(request, 'bd.puede_modificar_config_proceso_retiro_matricula')
                    data['title'] = u'Adicionar responsable a configuración del proceso de retiro matricula'
                    if not ConfigProcesoRetiroMatricula.objects.filter(pk=request.GET['id']).exists():
                        raise NameError(u"Configuración del proceso no encontrado")
                    data['eConfigProcesoRetiroMatricula'] = eConfigProcesoRetiroMatricula = ConfigProcesoRetiroMatricula.objects.get(pk=request.GET['id'])
                    f = ConfigProcesoRetiroMatriculaAsistenteForm()
                    f.tipo(eConfigProcesoRetiroMatricula.tipo_entidad)
                    data['form'] = f
                    return render(request, "adm_sistemas/remove_enroll_config/addresponsable.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'editresponsable':
                try:
                    puede_realizar_accion(request, 'bd.puede_modificar_config_proceso_retiro_matricula')
                    data['title'] = u'Editar responsable de configuración del proceso de retiro matricula'
                    if not ConfigProcesoRetiroMatriculaAsistente.objects.filter(pk=request.GET['id']).exists():
                        raise NameError(u"Configuración del proceso no encontrado")
                    data['eConfigProcesoRetiroMatriculaAsistente'] = eConfigProcesoRetiroMatriculaAsistente = ConfigProcesoRetiroMatriculaAsistente.objects.get(pk=request.GET['id'])
                    f = ConfigProcesoRetiroMatriculaAsistenteForm()
                    f.set_initial(eConfigProcesoRetiroMatriculaAsistente)
                    data['form'] = f
                    return render(request, "adm_sistemas/remove_enroll_config/editresponsable.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Admininistración de Procesos de Retiro de una asignatura o Matrícula'
                search = None
                ids = None
                procesos = ProcesoRetiroMatricula.objects.filter(status=True)
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
                return render(request, "adm_sistemas/remove_enroll_process/view.html", data)
            except Exception as ex:
                pass
