# -*- coding: UTF-8 -*-
from django.contrib import messages
from django.contrib.admin.models import LogEntry, ADDITION, DELETION
from django.contrib.admin.utils import unquote
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Permission
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
    #     puede_realizar_accion(request, 'bd.puede_acceder_grupo')
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
                tCount = 0
                grupos = Group.objects.filter().order_by('name')
                if txt_filter:
                    search = txt_filter.strip()
                    grupos = grupos.filter(Q(name__icontains=search))
                tCount = grupos.count()
                if offset == 0:
                    rows = grupos[offset:limit]
                else:
                    rows = grupos[offset:offset + limit]
                aaData = []
                for row in rows:
                    modulosgrupos = []
                    if ModuloGrupo.objects.filter(grupos__in=Group.objects.filter(pk=row.id)).exists():
                        modulos = []
                        for mg in ModuloGrupo.objects.filter(grupos__in=Group.objects.filter(pk=row.id)):
                            for m in mg.modulos.all():
                                modulos.append({"id": m.id,
                                                "nombre": m.nombre,
                                                "activo": m.activo,
                                                "sga": m.sga,
                                                "sagest": m.sagest,
                                                "posgrado": m.posgrado})

                            modulosgrupos.append({"id": mg.id,
                                                  "nombre": mg.nombre,
                                                  "modulos": modulos
                                                  })
                    aaData.append([row.id,
                                   row.name,
                                   modulosgrupos,
                                   {"id": row.id,
                                    "name": row.name,
                                    },
                                   ])
                return JsonResponse({"result": "ok", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__(), "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        if action == 'saveGroup':
            try:
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] and int(request.POST['id']) != 0 else None
                typeForm = 'edit' if id else 'new'
                f = GrupoForm(request.POST)
                if not f.is_valid():
                    raise NameError(u"Debe ingresar la información en todos los campos")
                if typeForm == 'new':
                    puede_realizar_accion(request, 'bd.puede_agregar_grupo')
                    if Group.objects.filter(name=f.cleaned_data['name']).exists():
                        raise NameError(u"Nombre debe ser único")
                    grupo = Group(name=f.cleaned_data['name'])
                    grupo.save()
                    log(u'Aciciono grupo: %s' % grupo, request, "add")
                    if 'permissions' in request.POST:
                        permissions = json.loads(request.POST['permissions'])
                        for permiso in permissions:
                            grupo.permissions.add(permiso)
                            log(u'Aciciono permisos a grupo: %s' % permiso, request, "add")
                else:
                    puede_realizar_accion(request, 'bd.puede_modificar_grupo')
                    if not Group.objects.filter(pk=id).exists():
                        raise NameError(u"No existe formulario a editar")
                    if Group.objects.filter(name=f.cleaned_data['name']).exclude(pk=id).exists():
                        raise NameError(u"Nombre debe ser único")
                    grupo = Group.objects.filter(pk=id).update(name=f.cleaned_data['name'])

                    log(u'Edito grupo: %s' % grupo, request, "edit")
                    eGroup = Group.objects.get(pk=id)
                    if 'permissions' in request.POST:
                        permissions = json.loads(request.POST['permissions'])
                        permissions_aux = eGroup.permissions.all()
                        for p in permissions_aux:
                            if not p.id in permissions:
                                eGroup.permissions.remove(p)
                                p.save()
                        for p in Permission.objects.filter(pk__in=permissions):
                            eGroup.permissions.add(p)


                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente el grupo"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar el grupo. %s" % ex.__str__()})

        if action == 'deleteGroup':
            try:
                puede_realizar_accion(request, 'bd.puede_eliminar_grupo')
                if not 'id' in request.POST or not request.POST['id']:
                    raise NameError(u"No se encontro registro a eliminar")
                object_id = int(request.POST['id'])
                if not Group.objects.filter(pk=object_id).exists():
                    raise NameError(u"No se encontro registro a eliminar")
                eGroup = Group.objects.get(pk=object_id)
                log(u'Elimino grupo: %s' % eGroup, request, "del")
                eGroup.delete()
                return JsonResponse({"result": "ok", "mensaje": u"Se elimino correctamente el grupo"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el grupo. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'loadFormGroup':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['new', 'edit', 'view'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    f = GrupoForm()
                    eGrupo = None
                    id = 0
                    if typeForm in ['edit', 'view']:
                        id = int(request.GET['id']) if 'id' in request.GET and request.GET['id'] and int(request.GET['id']) != 0 else None
                        if not Group.objects.filter(pk=id).exists():
                            raise NameError(u"No existe formulario a editar")
                        eGrupo = Group.objects.get(pk=id)
                        f.initial = model_to_dict(eGrupo)
                        if typeForm == 'view':
                            f.view()
                        if typeForm == 'edit':
                            puede_realizar_accion(request, 'bd.puede_modificar_grupo')
                        data['ePermissions'] = eGrupo.permissions.all()
                        data['eGrupo'] = eGrupo
                    else:
                        puede_realizar_accion(request, 'bd.puede_agregar_grupo')
                    data['form'] = f
                    data['frmName'] = "frmGrupo"
                    data['typeForm'] = typeForm
                    data['id'] = id
                    template = get_template("adm_sistemas/groups/frm.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'loadPermissions':
                try:
                    if 'permissions' in request.GET:
                        permissions = json.loads(request.GET['permissions'])
                        data['permissions'] = Permission.objects.filter().exclude(pk__in=permissions)
                    else:
                        data['permissions'] = Permission.objects.filter()
                    template = get_template("adm_sistemas/users/permissions.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Administración de Grupos del Sistema'
                # users = User.objects.filter().order_by('username')
                return render(request, "adm_sistemas/groups/view.html", data)
            except Exception as ex:
                pass
