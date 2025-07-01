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
from settings import MEDIA_URL
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
import sys
from django.template.loader import get_template
from sga.funciones import log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery, convertir_fecha, \
    resetear_clave, MiPaginador, generar_nombre
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
    #     puede_realizar_accion(request, 'bd.puede_acceder_config_carnet')
    # except Exception as ex:
    #     return HttpResponseRedirect(f"/?info={ex.__str__()}")
    adduserdata(request, data)
    persona = request.session['persona']

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                puede_realizar_accion(request, 'bd.puede_agregar_config_carnet')
                f = ConfiguracionCarnetForm(request.POST, request.FILES)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                base_anverso = None
                base_reverso = None
                if f.cleaned_data['tipo_validacion'] == 1:
                    if 'base_anverso' in request.FILES:
                        base_anverso = request.FILES['base_anverso']
                        if base_anverso:
                            if base_anverso.size > 10485760:
                                raise NameError(u"Archivo mayor a 10 Mb.")
                            base_anversod = base_anverso._name
                            ext = base_anversod[base_anversod.rfind("."):]
                            if not ext in ['.jpg', '.jpeg', '.png']:
                                raise NameError(u"Solo archivo con extensión. pdf, jpg, jpeg.")
                            base_anverso._name = generar_nombre("anverso", base_anverso._name)
                elif f.cleaned_data['tipo_validacion'] == 2:
                    if 'base_reverso' in request.FILES:
                        base_reverso = request.FILES['base_reverso']
                        if base_reverso:
                            if base_reverso.size > 10485760:
                                raise NameError(u"Archivo mayor a 10 Mb.")
                            base_reversod = base_reverso._name
                            ext = base_reversod[base_reversod.rfind("."):]
                            if not ext in ['.jpg', '.jpeg', '.png']:
                                raise NameError(u"Solo archivo con extensión. pdf, jpg, jpeg.")
                            base_reverso._name = generar_nombre("anverso", base_reverso._name)
                else:
                    if 'base_anverso' in request.FILES:
                        base_anverso = request.FILES['base_anverso']
                        if base_anverso:
                            if base_anverso.size > 10485760:
                                raise NameError(u"Archivo mayor a 10 Mb.")
                            base_anversod = base_anverso._name
                            ext = base_anversod[base_anversod.rfind("."):]
                            if not ext in ['.jpg', '.jpeg', '.png']:
                                raise NameError(u"Solo archivo con extensión. pdf, jpg, jpeg.")
                            base_anverso._name = generar_nombre("anverso", base_anverso._name)
                    if 'base_reverso' in request.FILES:
                        base_reverso = request.FILES['base_reverso']
                        if base_reverso:
                            if base_reverso.size > 10485760:
                                raise NameError(u"Archivo mayor a 10 Mb.")
                            base_reversod = base_reverso._name
                            ext = base_reversod[base_reversod.rfind("."):]
                            if not ext in ['.jpg', '.jpeg', '.png']:
                                raise NameError(u"Solo archivo con extensión. pdf, jpg, jpeg.")
                            base_reverso._name = generar_nombre("anverso", base_reverso._name)

                eConfiguracionCarnet = ConfiguracionCarnet(version=f.cleaned_data['version'],
                                                           nombre=f.cleaned_data['nombre'],
                                                           tipo=f.cleaned_data['tipo'],
                                                           tipo_perfil=f.cleaned_data['tipo_perfil'],
                                                           tipo_validacion=f.cleaned_data['tipo_validacion'],
                                                           reporte=f.cleaned_data['reporte'],
                                                           base_anverso=base_anverso,
                                                           base_reverso=base_reverso,
                                                           activo=f.cleaned_data['activo'],
                                                           puede_cargar_foto=f.cleaned_data['puede_cargar_foto'],
                                                           puede_eliminar_carne=f.cleaned_data['puede_eliminar_carne'],
                                                           puede_subir_foto=f.cleaned_data['puede_subir_foto'],
                                                           )
                eConfiguracionCarnet.save(request)
                log(u'Adiciono configuración de carné: %s' % eConfiguracionCarnet, request, "add")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'edit':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_config_carnet')
                f = ConfiguracionCarnetForm(request.POST, request.FILES)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if not ConfiguracionCarnet.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Configuración de carné a editar no encontrado")
                eConfiguracionCarnet = ConfiguracionCarnet.objects.get(pk=request.POST['id'])
                eConfiguracionCarnet.version = f.cleaned_data['version']
                eConfiguracionCarnet.nombre = f.cleaned_data['nombre']
                eConfiguracionCarnet.activo = f.cleaned_data['activo']
                eConfiguracionCarnet.tipo = f.cleaned_data['tipo']
                eConfiguracionCarnet.tipo_perfil = f.cleaned_data['tipo_perfil']
                eConfiguracionCarnet.tipo_validacion = f.cleaned_data['tipo_validacion']
                eConfiguracionCarnet.reporte = f.cleaned_data['reporte']
                eConfiguracionCarnet.puede_cargar_foto = f.cleaned_data['puede_cargar_foto']
                eConfiguracionCarnet.puede_eliminar_carne = f.cleaned_data['puede_eliminar_carne']
                eConfiguracionCarnet.puede_subir_foto = f.cleaned_data['puede_subir_foto']
                if f.cleaned_data['tipo_validacion'] == 1:
                    if 'base_anverso' in request.FILES:
                        base_anverso = request.FILES['base_anverso']
                        if base_anverso:
                            if base_anverso.size > 10485760:
                                raise NameError(u"Archivo mayor a 10 Mb.")
                            base_anversod = base_anverso._name
                            ext = base_anversod[base_anversod.rfind("."):]
                            if not ext in ['.jpg', '.jpeg', '.png']:
                                raise NameError(u"Solo archivo con extensión. pdf, jpg, jpeg.")
                            base_anverso._name = generar_nombre("anverso", base_anverso._name)
                            eConfiguracionCarnet.base_anverso = base_anverso
                elif f.cleaned_data['tipo_validacion'] == 2:
                    if 'base_reverso' in request.FILES:
                        base_reverso = request.FILES['base_reverso']
                        if base_reverso:
                            if base_reverso.size > 10485760:
                                raise NameError(u"Archivo mayor a 10 Mb.")
                            base_reversod = base_reverso._name
                            ext = base_reversod[base_reversod.rfind("."):]
                            if not ext in ['.jpg', '.jpeg', '.png']:
                                raise NameError(u"Solo archivo con extensión. pdf, jpg, jpeg.")
                            base_reverso._name = generar_nombre("reverso", base_reverso._name)
                            eConfiguracionCarnet.base_reverso = base_reverso
                else:
                    if 'base_anverso' in request.FILES:
                        base_anverso = request.FILES['base_anverso']
                        if base_anverso:
                            if base_anverso.size > 10485760:
                                raise NameError(u"Archivo mayor a 10 Mb.")
                            base_anversod = base_anverso._name
                            ext = base_anversod[base_anversod.rfind("."):]
                            if not ext in ['.jpg', '.jpeg', '.png']:
                                raise NameError(u"Solo archivo con extensión. pdf, jpg, jpeg.")
                            base_anverso._name = generar_nombre("anverso", base_anverso._name)
                            eConfiguracionCarnet.base_anverso = base_anverso
                    if 'base_reverso' in request.FILES:
                        base_reverso = request.FILES['base_reverso']
                        if base_reverso:
                            if base_reverso.size > 10485760:
                                raise NameError(u"Archivo mayor a 10 Mb.")
                            base_reversod = base_reverso._name
                            ext = base_reversod[base_reversod.rfind("."):]
                            if not ext in ['.jpg', '.jpeg', '.png']:
                                raise NameError(u"Solo archivo con extensión. pdf, jpg, jpeg.")
                            base_reverso._name = generar_nombre("reverso", base_reverso._name)
                            eConfiguracionCarnet.base_reverso = base_reverso
                eConfiguracionCarnet.save(request)
                log(u'Edito configuración de carné: %s' % eConfiguracionCarnet, request, "edit")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'delete':
            try:
                puede_realizar_accion(request, 'bd.puede_eliminar_config_carnet')
                if not ConfiguracionCarnet.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Configuración de carné a editar no encontrado")
                eDelete = eConfiguracionCarnet = ConfiguracionCarnet.objects.get(pk=request.POST['id'])
                if eConfiguracionCarnet.en_uso():
                    raise NameError(u"Configuración de carné en uso")
                eConfiguracionCarnet.delete()
                log(u'Elimino configuración de carné: %s' % eDelete, request, "del")
                messages.add_message(request, messages.SUCCESS, f'Se elimino correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el registro. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    puede_realizar_accion(request, 'bd.puede_agregar_config_carnet')
                    data['title'] = u'Adicionar configuración de carné'
                    f = ConfiguracionCarnetForm()
                    data['form'] = f
                    return render(request, "adm_sistemas/config_carnet/add.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'edit':
                try:
                    puede_realizar_accion(request, 'bd.puede_modificar_config_carnet')
                    data['title'] = u'Editar configuración de carné'
                    if not ConfiguracionCarnet.objects.filter(pk=request.GET['id']).exists():
                        raise NameError(u"Configuración de carné a editar no encontrado")
                    data['eConfiguracionCarnet'] = eConfiguracionCarnet = ConfiguracionCarnet.objects.get(pk=request.GET['id'])
                    f = ConfiguracionCarnetForm()
                    f.set_initial(eConfiguracionCarnet)
                    data['form'] = f
                    return render(request, "adm_sistemas/config_carnet/edit.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Admininistración de la configuración de carné'
                search = None
                ids = None
                configuraciones = ConfiguracionCarnet.objects.filter(status=True)
                if 'id' in request.GET:
                    ids = request.GET['id']
                    configuraciones = configuraciones.filter(id=int(ids))
                if 's' in request.GET:
                    search = request.GET['s']
                    configuraciones = configuraciones.filter(Q(nombre__icontains=search)).distinct()
                paging = MiPaginador(configuraciones, 25)
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
                data['configuraciones'] = page.object_list
                data['media_url'] = MEDIA_URL
                return render(request, "adm_sistemas/config_carnet/view.html", data)
            except Exception as ex:
                pass
