# -*- coding: UTF-8 -*-
import json

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
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
import sys
from django.template.loader import get_template
from sga.funciones import log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery, convertir_fecha, \
    resetear_clave
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
    #     puede_realizar_accion(request, 'bd.puede_acceder_grupos_modulos')
    # except Exception as ex:
    #     return HttpResponseRedirect(f"/?info={ex.__str__()}")
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'loadDataTable':
            try:
                txt_filter = request.POST['sSearch'] if request.POST['sSearch'] else ''
                limit = int(request.POST['iDisplayLength']) if request.POST['iDisplayLength'] else 25
                offset = int(request.POST['iDisplayStart']) if request.POST['iDisplayStart'] else 0
                aaData = []
                tCount = 0
                gruposmodulos = ModuloGrupo.objects.filter().order_by('nombre')
                if not persona.usuario.is_staff:
                    gruposmodulos = gruposmodulos.filter(status=True)
                if txt_filter:
                    search = txt_filter.strip()
                    gruposmodulos = gruposmodulos.filter(Q(nombre__icontains=search) | Q(descripcion__icontains=search))
                tCount = gruposmodulos.count()
                if offset == 0:
                    rows = gruposmodulos[offset:limit]
                else:
                    rows = gruposmodulos[offset:offset + limit]
                aaData = []
                for row in rows:
                    grupos = []
                    for g in row.groups():
                        grupos.append({"id": g.id,
                                       "nombre": g.name,
                                       })
                    modulos = []
                    for m in row.modules():
                        modulos.append({"id": m.id,
                                        "nombre": m.nombre,
                                        "activo": m.activo,
                                        })
                    aaData.append([row.id,
                                   {"nombre": row.nombre,
                                    "descripcion": row.descripcion,
                                    },
                                   {"id": row.id,
                                    "total": len(grupos),
                                    "grupos": grupos,
                                    },
                                   {"id": row.id,
                                    "total": len(modulos),
                                    "modulos": modulos,
                                    },
                                   {"id": row.id,
                                    "nombre": row.nombre,
                                    },
                                   ])
                return JsonResponse({"result": "ok", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__(), "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        if action == 'saveModuleGrupo':
            try:
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] and int(request.POST['id']) != 0 else None
                typeForm = 'edit' if id else 'new'
                f = ModuloGrupoForm(request.POST)
                f.deleteFields()
                if not f.is_valid():
                    # f.addErrors(f.errors.get_json_data(escape_html=True))
                    raise NameError(u"Debe ingresar la información en todos los campos")
                if typeForm == 'new':
                    puede_realizar_accion(request, 'bd.puede_agregar_grupos_modulos')
                    if ModuloGrupo.objects.filter(nombre=f.cleaned_data['nombre']).exists():
                        raise NameError(u"Nombre debe ser único")

                    mg = ModuloGrupo(nombre=f.cleaned_data['nombre'],
                                     descripcion=f.cleaned_data['descripcion'],
                                     prioridad=0
                                     )
                    mg.save(request)
                    if 'moduloss' in request.POST:
                        moduloss = json.loads(request.POST['moduloss'])
                        modulos = Modulo.objects.filter(pk__in=moduloss)
                        for modulo in modulos:
                            mg.modulos.add(modulo)
                    if 'gruposs' in request.POST:
                        gruposs = json.loads(request.POST['gruposs'])
                        grupos = Group.objects.filter(pk__in=gruposs)
                        for grupo in grupos:
                            mg.grupos.add(grupo)

                    log(u'Aciciono grupo de modulo: %s' % mg, request, "add")
                else:
                    puede_realizar_accion(request, 'bd.puede_modificar_grupos_modulos')
                    if not ModuloGrupo.objects.filter(pk=id).exists():
                        raise NameError(u"No existe formulario a editar")
                    if ModuloGrupo.objects.filter(nombre=f.cleaned_data['nombre']).exclude(pk=id).exists():
                        raise NameError(u"Nombre debe ser única")
                    mg = ModuloGrupo.objects.get(pk=id)
                    mg.nombre = f.cleaned_data['nombre']
                    mg.descripcion = f.cleaned_data['descripcion']
                    mg.save(request)
                    if 'moduloss' in request.POST:
                        moduloss = json.loads(request.POST['moduloss'])
                        moduloss = [int(x) for x in moduloss]
                        moduloss_aux = mg.modulos.all()
                        for m in moduloss_aux:
                            if not m.id in moduloss:
                                mg.modulos.remove(m)
                                m.save()
                        for modulo in Modulo.objects.filter(pk__in=moduloss):
                            mg.modulos.add(modulo)
                    if 'gruposs' in request.POST:
                        gruposs = json.loads(request.POST['gruposs'])
                        gruposs = [int(x) for x in gruposs]
                        gruposs_aux = mg.grupos.all()
                        for g in gruposs_aux:
                            if not g.id in gruposs:
                                mg.grupos.remove(g)
                                g.save()
                        for grupo in Group.objects.filter(pk__in=gruposs):
                            mg.grupos.add(grupo)
                    log(u'Edito grupo de modulo: %s' % mg, request, "edit")
                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente el grupo de modulo"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar el grupo de modulo. %s" % ex.__str__()})

        if action == 'deleteModuleGrupo':
            try:
                puede_realizar_accion(request, 'bd.puede_eliminar_grupos_modulos')
                if not 'id' in request.POST or not request.POST['id']:
                    raise NameError(u"No se encontro registro a eliminar")
                object_id = int(request.POST['id'])
                if not ModuloGrupo.objects.filter(pk=object_id).exists():
                    raise NameError(u"No se encontro registro a eliminar")
                eModuloGrupo = ModuloGrupo.objects.get(pk=object_id)
                log(u'Elimino grupo de modulo: %s' % eModuloGrupo, request, "del")
                eModuloGrupo.delete()
                return JsonResponse({"result": "ok", "mensaje": u"Se elimino correctamente el grupo de modulo"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el grupo de modulo. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'loadForm':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['new', 'edit', 'view'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    f = ModuloGrupoForm()
                    eModuloGrupo = None
                    id = 0
                    if typeForm in ['edit', 'view']:
                        id = int(request.GET['id']) if 'id' in request.GET and request.GET['id'] and int(request.GET['id']) != 0 else None
                        if not ModuloGrupo.objects.filter(pk=id).exists():
                            raise NameError(u"No existe formulario a editar")
                        eModuloGrupo = ModuloGrupo.objects.get(pk=id)
                        f.initial = model_to_dict(eModuloGrupo)
                        if typeForm == 'view':
                            f.view()
                        if typeForm == 'edit':
                            puede_realizar_accion(request, 'bd.puede_modificar_grupos_modulos')
                        data['eModuloGrupo'] = eModuloGrupo
                    else:
                        puede_realizar_accion(request, 'bd.puede_agregar_grupos_modulos')
                    data['form'] = f
                    data['frmName'] = "frmModuloGrupo"
                    data['id'] = id
                    template = get_template("adm_sistemas/groups_modules/frm.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Administración de Grupos de Modulos del Sistema'
                # users = User.objects.filter().order_by('username')
                return render(request, "adm_sistemas/groups_modules/view.html", data)
            except Exception as ex:
                pass
