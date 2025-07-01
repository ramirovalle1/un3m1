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
    #     puede_realizar_accion(request, 'bd.puede_acceder_modulo')
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
                activo = int(request.POST['activo']) if request.POST['activo'] else 0
                app_sga = int(request.POST['app_sga']) if request.POST['app_sga'] else 0
                app_sagest = int(request.POST['app_sagest']) if request.POST['app_sagest'] else 0
                app_posgrado = int(request.POST['app_posgrado']) if request.POST['app_posgrado'] else 0
                app_api = int(request.POST['app_api']) if request.POST['app_api'] else 0
                aaData = []
                tCount = 0
                modulos = Modulo.objects.filter().order_by('nombre')
                if not persona.usuario.is_staff:
                    modulos = modulos.filter(status=True)
                if txt_filter:
                    search = txt_filter.strip()
                    modulos = modulos.filter(Q(url__icontains=search) | Q(nombre__icontains=search) | Q(descripcion__icontains=search) | Q(api_key__icontains=search))
                if app_sga > 0:
                    modulos = modulos.filter(sga=(app_sga == 1))
                if app_sagest > 0:
                    modulos = modulos.filter(sagest=(app_sagest == 1))
                if app_posgrado > 0:
                    modulos = modulos.filter(posgrado=(app_posgrado == 1))
                if app_api > 0:
                    modulos = modulos.filter(api=(app_api == 1))
                if activo > 0:
                    modulos = modulos.filter(activo=(activo == 1))
                tCount = modulos.count()
                if offset == 0:
                    rows = modulos[offset:limit]
                else:
                    rows = modulos[offset:offset + limit]
                aaData = []
                for row in rows:
                    modulosgrupos = []
                    categorias = []
                    if ModuloGrupo.objects.filter(modulos__in=Modulo.objects.filter(pk=row.id)).exists():
                        grupos = []
                        for mg in ModuloGrupo.objects.filter(modulos__in=Modulo.objects.filter(pk=row.id)):
                            for g in mg.grupos.all():
                                grupos.append({"id": g.id,
                                               "nombre": g.name,
                                               })

                            modulosgrupos.append({"id": mg.id,
                                                  "nombre": mg.nombre,
                                                  "grupos": grupos
                                                  })
                    aaData.append([row.id,
                                   row.icono,
                                   {"nombre": row.nombre,
                                    "url": row.url,
                                    "descripcion": row.descripcion,
                                    "api_key": row.api_key if row.api and row.api_key else '',
                                    "categorias": list(row.categorias.all().values_list('nombre', flat=True))
                                    },
                                   modulosgrupos,
                                   row.activo,
                                   row.sga,
                                   row.sagest,
                                   row.posgrado,
                                   row.api,
                                   {"id": row.id,
                                    "nombre": row.nombre,
                                    "activo": row.activo,
                                    "sga": row.sga,
                                    "sagest": row.sagest,
                                    "posgrado": row.posgrado,
                                    "api": row.api,
                                    },
                                   ])
                return JsonResponse({"result": "ok", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__(), "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        if action == 'saveModule':
            try:
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] and int(request.POST['id']) != 0 else None
                typeForm = 'edit' if id else 'new'
                f = ModuloForm(request.POST)
                if not f.is_valid():
                    # f.addErrors(f.errors.get_json_data(escape_html=True))
                    raise NameError(u"Debe ingresar la información en todos los campos")
                rolesaux = json.loads(request.POST['rolesaux'])
                categoriasaux = json.loads(request.POST['categoriasaux'])
                if not categoriasaux:
                    categoriasaux = []
                if typeForm == 'new':
                    puede_realizar_accion(request, 'bd.puede_agregar_modulo')
                    if Modulo.objects.filter(url=f.cleaned_data['url']).exists():
                        raise NameError(u"URL debe ser única")
                    # if Modulo.objects.filter(nombre=f.cleaned_data['nombre']).exists():
                    #     raise NameError(u"Nombre debe ser único")

                    modulo = Modulo(url=f.cleaned_data['url'],
                                    nombre=f.cleaned_data['nombre'],
                                    icono=f.cleaned_data['icono'],
                                    descripcion=f.cleaned_data['descripcion'],
                                    roles=','.join(rolesaux) if rolesaux else '',
                                    activo=f.cleaned_data['activo'],
                                    sga=f.cleaned_data['sga'],
                                    sagest=f.cleaned_data['sagest'],
                                    posgrado=f.cleaned_data['posgrado'],
                                    api=f.cleaned_data['api'],
                                    api_key=f.cleaned_data['api_key'])
                    modulo.save(request)
                    modulo.categorias.set(categoriasaux)
                    modulo.save(request)
                    log(u'Aciciono modulo: %s' % modulo, request, "add")
                else:
                    puede_realizar_accion(request, 'bd.puede_modificar_modulo')
                    if not Modulo.objects.filter(pk=id).exists():
                        raise NameError(u"No existe formulario a editar")
                    if Modulo.objects.filter(url=f.cleaned_data['url']).exclude(pk=id).exists():
                        raise NameError(u"URL debe ser única")
                    # if Modulo.objects.filter(nombre=f.cleaned_data['nombre']).exclude(pk=id).exists():
                    #     raise NameError(u"Nombre debe ser única")
                    modulo = Modulo.objects.get(pk=id)
                    modulo.url = f.cleaned_data['url']
                    modulo.nombre = f.cleaned_data['nombre']
                    modulo.icono = f.cleaned_data['icono']
                    modulo.roles = ','.join(rolesaux) if rolesaux else None
                    modulo.categorias.set(categoriasaux)
                    modulo.descripcion = f.cleaned_data['descripcion']
                    modulo.activo = f.cleaned_data['activo']
                    modulo.sga = f.cleaned_data['sga']
                    modulo.sagest = f.cleaned_data['sagest']
                    modulo.posgrado = f.cleaned_data['posgrado']
                    modulo.api = f.cleaned_data['api']
                    modulo.api_key = f.cleaned_data['api_key']
                    modulo.save(request)
                    log(u'Edito modulo: %s' % modulo, request, "edit")
                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente el modulo"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar el modulo. %s" % ex.__str__()})

        if action == 'deleteModule':
            try:
                puede_realizar_accion(request, 'bd.puede_eliminar_modulo')
                if not 'id' in request.POST or not request.POST['id']:
                    raise NameError(u"No se encontro registro a eliminar")
                object_id = int(request.POST['id'])
                if not Modulo.objects.filter(pk=object_id).exists():
                    raise NameError(u"No se encontro registro a eliminar")
                eModulo = Modulo.objects.get(pk=object_id)
                log(u'Elimino modulo: %s' % eModulo, request, "del")
                eModulo.delete()
                return JsonResponse({"result": "ok", "mensaje": u"Se elimino correctamente el modulo"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el modulo. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'loadFormModule':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['new', 'edit', 'view'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    f = ModuloForm()
                    eModulo = None
                    id = 0
                    if typeForm in ['edit', 'view']:
                        id = int(request.GET['id']) if 'id' in request.GET and request.GET['id'] and int(request.GET['id']) != 0 else None
                        if not Modulo.objects.filter(pk=id).exists():
                            raise NameError(u"No existe formulario a editar")
                        eModulo = Modulo.objects.get(pk=id)
                        f.initial = model_to_dict(eModulo)
                        if eModulo.roles:
                            listroles = []
                            for rol in ROLES_MODULO_SISTEMA:
                                if rol[0] in eModulo.roles:
                                    listroles.append(int(rol[0]))
                            f['roles'].initial = listroles
                        if typeForm == 'view':
                            f.view()
                        if typeForm == 'edit':
                            puede_realizar_accion(request, 'bd.puede_modificar_modulo')
                        data['eModulo'] = eModulo
                    else:
                        puede_realizar_accion(request, 'bd.puede_agregar_modulo')
                    data['form'] = f
                    data['frmName'] = "frmModulo"
                    data['id'] = id
                    template = get_template("adm_sistemas/modules/frm.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Administración de Modulos del Sistema'
                # users = User.objects.filter().order_by('username')
                return render(request, "adm_sistemas/modules/view.html", data)
            except Exception as ex:
                pass
