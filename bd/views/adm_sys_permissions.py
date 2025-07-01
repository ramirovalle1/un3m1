from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from bd.forms import GestionPermisosForm
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template.loader import get_template
from sga.funciones import generar_nombre, log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery, convertir_fecha, resetear_clave, MiPaginador
from django.db.models.query_utils import Q
from bd.models import GestionPermisos
from django.forms import model_to_dict
from sga.templatetags.sga_extras import encrypt
from django.contrib.auth.models import Group, User, Permission
from sga.models import Modulo


@login_required(redirect_field_name='ret', login_url='/loginsga')
#@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = data['action'] = request.POST['action']
        if action == 'add':
            try:
                if not 'permiso' in request.POST or not 'modulo' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Seleccione un modulo o permiso valido."})

                form = GestionPermisosForm(request.POST, request.FILES)
                form.edit(request.POST['modulo'], request.POST['permiso'])
                file = None
                valid_ext = [".jpg", ".JPG", ".jpeg", ".JPEG", ".png", ".PNG"]
                if 'foto' in request.FILES:
                    file = request.FILES['foto']
                    if file:
                        if file.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo es mayor a 4 Mb."})
                        else:
                            newfilesd = file._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext in valid_ext:
                                file._name = generar_nombre("ubicacion_permiso", file._name)
                            else:
                                return JsonResponse({"result": "bad", "mensaje": f"Error, Solo archivos con extención .jpg .jpeg, .png"})
                if form.is_valid():
                    gp = GestionPermisos(descripcion=form.cleaned_data['descripcion'], modulo=form.cleaned_data['modulo'], permiso=form.cleaned_data['permiso'])
                    gp.foto = file if file else None
                    gp.save(request)
                    log(u'Adiciono nueva permiso: %s' % gp, request, "add")
                else:
                    print([{k: v[0]} for k, v in form.errors.items()])
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})

                return JsonResponse({"result": 'ok'}, safe=False)
            except Exception as ex:
                transaction.rollback()
                pass

        if action == 'edit':
            try:
                form = GestionPermisosForm(request.POST, request.FILES)
                gp = GestionPermisos.objects.filter(pk=int(encrypt(request.POST['id']))).first()
                form.edit(gp.modulo.id, gp.permiso.id)
                file = None
                valid_ext = [".jpg", ".JPG", ".jpeg", ".JPEG", ".png", ".PNG"]
                if 'foto' in request.FILES:
                    file = request.FILES['foto']
                    if file:
                        if file.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo es mayor a 4 Mb."})
                        else:
                            newfilesd = file._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext in valid_ext:
                                file._name = generar_nombre("ubicacion_permiso", file._name)
                            else:
                                return JsonResponse({"result": "bad", "mensaje": f"Error, Solo archivos con extención .jpg .jpeg, .png"})
                if form.is_valid():
                    if gp:
                        gp.descripcion, gp.modulo, gp.permiso = form.cleaned_data['descripcion'], form.cleaned_data['modulo'], form.cleaned_data['permiso']
                        gp.foto = file if file else gp.foto
                        gp.save(request)
                        log(u'Edito permiso: %s' % gp, request, "edit")
                return JsonResponse({"result": 'ok'}, safe=False)
            except Exception as ex:
                transaction.rollback()
                pass

        if action == 'delete':
            try:
                with transaction.atomic():
                    instancia = GestionPermisos.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó permiso: %s' % instancia, request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                transaction.rollback()
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)


        HttpResponseRedirect("/niveles?info=Solicitud incorrecta.")
    else:
        if 'action' in request.GET:
            action = data['action'] = request.GET['action']

            if action == 'buscarpermiso':
                try:
                    q = request.GET['q'].upper().strip()
                    per = Permission.objects.filter((Q(name__icontains=q) | Q(codename__icontains=q) | Q(content_type__app_label__icontains=q))).distinct().order_by('id')[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} | {} ({})".format(x.content_type, x.name, x.codename)} for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'buscarmodulo':
                try:
                    q = request.GET['q'].upper().strip()
                    modulo = Modulo.objects.filter((Q(nombre__icontains=q) | Q(url__icontains=q) | Q(descripcion__icontains=q))).distinct().order_by('id')[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} ({})".format(x.nombre, x.url)} for x in modulo]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'add':
                try:
                    form = GestionPermisosForm()
                    data['title'] = u"Adicionar permiso"
                    data['form'] = form
                    return render(request, "adm_sistemas/permissions/crud/add.html", data)
                except Exception as ex:
                    pass

            if action == 'listadogrupos':
                try:
                    data['title'] = u"Grupos"
                    if GestionPermisos.objects.values('id').filter(pk=int(request.GET['id'])).exists():
                        gp = GestionPermisos.objects.filter(pk=int(request.GET['id'])).first()
                        data['subtitle'] = u"%s" % gp.permiso.name
                        data['listado'] = gp.permiso.group_set.values_list('id', 'name').order_by('id')
                        data['th'] = ['#','Grupo']
                        template = get_template("adm_sistemas/permissions/crud/listado.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'html': json_content})
                    else:
                        return JsonResponse({"result": "false", 'message': 'Permiso no asignado.'})
                except Exception as ex:
                    pass

            if action == 'listadousuarios':
                try:
                    data['title'] = u"Usuarios"
                    if GestionPermisos.objects.values('id').filter(pk=int(request.GET['id'])).exists():
                        gp = GestionPermisos.objects.filter(pk=int(request.GET['id'])).first()
                        listado = []
                        contador = 0
                        data['subtitle'] = u"%s" % gp.permiso.name
                        for user in gp.permiso.user_set.all():
                            contador += 1
                            listado.append([contador, '%s' % user.persona_set.first().nombre_completo_inverso()])

                        data['top'] = contador
                        for group in gp.permiso.group_set.all():
                            for user in group.user_set.all():
                                contador += 1
                                listado.append([contador, '%s' % user.persona_set.first()])

                        data['listado'] = listado
                        data['th'] = ['#','Usuario']
                        data['color'] = 'rgba(49, 198, 212, 0.1)'
                        template = get_template("adm_sistemas/permissions/crud/listado.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'html': json_content})
                    else:
                        return JsonResponse({"result": "false", 'message': 'Permiso no asignado.'})
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    gp = GestionPermisos.objects.filter(pk=int(encrypt(request.GET['id']))).first()
                    form = GestionPermisosForm(initial=model_to_dict(gp))
                    form.edit(gp.modulo.id, gp.permiso.id)
                    data['title'] = u"Editar permiso"
                    data['form'] = form
                    data['id'] = gp.id
                    data['backend_foto'] = u"%s" % gp.foto.url if gp.foto else ''
                    return render(request, "adm_sistemas/permissions/crud/add.html", data)
                except Exception as ex:
                    pass

            HttpResponseRedirect("/adm_sistemas?info=Solicitud incorrecta.")
        else:
            try:
                data['title'] = 'Administración de permisos del sistema'
                filtros, s, m, url_vars = Q(status=True, modulo__status=True), request.GET.get('s', ''), request.GET.get('m', '0'), ''
                data['count'] = GestionPermisos.objects.filter(filtros).values('id').count()

                if s:
                    filtros = filtros & (Q(permiso__name__icontains=s) | Q(permiso__codename__icontains=s) | Q(descripcion__icontains=s))
                    data['s'] = f"{s}"
                    url_vars += f"&s={s}"

                if int(m):
                    filtros = filtros & (Q(modulo_id=m))
                    data['m'] = f"{m}"
                    url_vars += f"&m={m}"

                paging = MiPaginador(GestionPermisos.objects.filter(filtros).order_by('-id'), 10)
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
                data['permissions'] = page.object_list
                data['url_vars'] = url_vars
                data['modulos'] = GestionPermisos.objects.values_list('modulo_id', 'modulo__nombre', 'modulo__url').filter(status=True).distinct()
                return render(request, "adm_sistemas/permissions/view.html", data)

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})