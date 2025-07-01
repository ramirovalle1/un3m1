# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils.encoding import force_str

from bd.models import TemplateBaseSetting
from decorators import secure_module
from bd.forms import *
from settings import ALUMNOS_GROUP_ID
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template.loader import get_template
from sga.funciones import log, puede_realizar_accion
from django.core.cache import cache


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    #
    # try:
    #     puede_realizar_accion(request, 'bd.puede_acceder_ajuste_plantilla')
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
                settings = TemplateBaseSetting.objects.filter()
                if txt_filter:
                    search = txt_filter.strip()
                    settings = settings.filter(Q(name_system__icontains=search)).distinct()

                tCount = settings.count()
                if offset == 0:
                    rows = settings[offset:limit]
                else:
                    rows = settings[offset:offset + limit]
                aaData = []
                ru = 0
                for row in rows:
                    aaData.append([row.id,
                                   row.name_system,
                                   row.get_app_display(),
                                   {
                                       "use_menu_favorite_module": row.use_menu_favorite_module,
                                       "use_menu_notification": row.use_menu_notification,
                                       "use_menu_user_manual": row.use_menu_user_manual,
                                       "use_api": row.use_api
                                   },
                                   {
                                       "id": row.id,
                                       "nombre": row.__str__()
                                   },
                                   ])
                return JsonResponse({"result": "ok", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__(), "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        elif action == 'saveSetting':
            try:
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] and int(request.POST['id']) != 0 else None
                typeForm = 'edit' if id else 'new'
                f = TemplateBaseSettingForm(request.POST)
                if not f.is_valid():
                    # [(k, v[0]) for k, v in f.errors.items()]
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if typeForm == 'new':
                    puede_realizar_accion(request, 'bd.puede_agregar_ajuste_plantilla')
                    if TemplateBaseSetting.objects.filter(name_system=f.cleaned_data['name_system'], app=f.cleaned_data['app']).exists():
                        raise NameError(u"Nombre debe ser único")

                    eTemplateBaseSetting = TemplateBaseSetting(name_system=f.cleaned_data['name_system'],
                                                               app=f.cleaned_data['app'],
                                                               use_menu_favorite_module=f.cleaned_data['use_menu_favorite_module'],
                                                               use_menu_user_manual=f.cleaned_data['use_menu_user_manual'],
                                                               use_menu_notification=f.cleaned_data['use_menu_notification'],
                                                               use_api=f.cleaned_data['use_api'],
                                                               )
                    eTemplateBaseSetting.save(request)
                    eModulosEnCache = cache.has_key(f"modulos__api__sie__{ALUMNOS_GROUP_ID}_v1")
                    if eModulosEnCache:
                        cache.delete(f"modulos__api__sie__{ALUMNOS_GROUP_ID}_v1")
                    log(u'Adicionado ajuste de plnatilla: %s' % eTemplateBaseSetting, request, "add")
                else:
                    puede_realizar_accion(request, 'bd.puede_modificar_ajuste_plantilla')
                    if not TemplateBaseSetting.objects.filter(pk=id).exists():
                        raise NameError(u"No existe formulario a editar")
                    if TemplateBaseSetting.objects.filter(name_system=f.cleaned_data['name_system'], app=f.cleaned_data['app']).exclude(pk=id).exists():
                        raise NameError(u"Nombre debe ser única")
                    eTemplateBaseSetting = TemplateBaseSetting.objects.get(pk=id)
                    eTemplateBaseSetting.name_system = f.cleaned_data['name_system']
                    eTemplateBaseSetting.app = f.cleaned_data['app']
                    eTemplateBaseSetting.use_menu_favorite_module = f.cleaned_data['use_menu_favorite_module']
                    eTemplateBaseSetting.use_menu_user_manual = f.cleaned_data['use_menu_user_manual']
                    eTemplateBaseSetting.use_menu_notification = f.cleaned_data['use_menu_notification']
                    eTemplateBaseSetting.use_api = f.cleaned_data['use_api']
                    eTemplateBaseSetting.save(request)
                    eModulosEnCache = cache.has_key(f"modulos__api__sie__{ALUMNOS_GROUP_ID}_v1")
                    if eModulosEnCache:
                        cache.delete(f"modulos__api__sie__{ALUMNOS_GROUP_ID}_v1")
                    log(u'Edito ajuste de plnatilla: %s' % eTemplateBaseSetting, request, "edit")
                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente los ajuste de plantilla"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los ajuste de plantilla. %s" % ex.__str__()})

        elif action == 'deleteSetting':
            try:
                puede_realizar_accion(request, 'bd.puede_eliminar_ajuste_plantilla')
                if not 'id' in request.POST or not request.POST['id']:
                    raise NameError(u"No se encontro registro a eliminar")
                object_id = int(request.POST['id'])
                if not TemplateBaseSetting.objects.filter(pk=object_id).exists():
                    raise NameError(u"No se encontro registro a eliminar")
                objectDelete = eTemplateBaseSetting = TemplateBaseSetting.objects.get(pk=object_id)
                objectDelete.delete()
                log(u'Elimino ajustes de plnatilla: %s' % eTemplateBaseSetting, request, "del")
                return JsonResponse({"result": "ok", "mensaje": u"Se elimino correctamente los ajustes de plnatilla"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los ajustes de plnatilla. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'loadForm':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['new', 'edit', 'view'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    f = TemplateBaseSettingForm()
                    eTemplateBaseSetting = None
                    id = 0
                    if typeForm in ['edit', 'view']:
                        id = int(request.GET['id']) if 'id' in request.GET and request.GET['id'] and int(request.GET['id']) != 0 else None
                        if not TemplateBaseSetting.objects.filter(pk=id).exists():
                            raise NameError(u"No existe formulario a editar")
                        eTemplateBaseSetting = TemplateBaseSetting.objects.get(pk=id)
                        f.set_initial(eTemplateBaseSetting)
                        if typeForm == 'view':
                            f.view()
                        if typeForm == 'edit':
                            puede_realizar_accion(request, 'bd.puede_modificar_ajuste_plantilla')
                        data['eTemplateBaseSetting'] = eTemplateBaseSetting
                    else:
                        puede_realizar_accion(request, 'bd.puede_agregar_ajuste_plantilla')
                        data['eTemplateBaseSetting'] = eTemplateBaseSetting
                    data['form'] = f
                    data['frmName'] = "frmSettingTemplate"
                    data['id'] = id
                    template = get_template("adm_sistemas/setting_template/frm.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Administración de ajustes de plantillas'
                return render(request, "adm_sistemas/setting_template/view.html", data)
            except Exception as ex:
                pass
