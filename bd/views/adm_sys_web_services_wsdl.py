# -*- coding: UTF-8 -*-
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from bd.forms import *
from moodle.models import UserAuth
from sga.commonviews import adduserdata
from django.db import connection, transaction
from sga.funciones import log, puede_realizar_accion, MiPaginador
from sga.models import Persona
from soap.models import Setting
from soap.consumer import banco_pacifico


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    try:
        puede_realizar_accion(request, 'bd.puede_acceder_web_services_wsdl')
    except Exception as ex:
        return HttpResponseRedirect(f"/?info={ex.__str__()}")
    adduserdata(request, data)
    persona = request.session['persona']

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                puede_realizar_accion(request, 'bd.puede_agregar_web_services_wsdl')
                f = SettingWSDLForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                eSetting = Setting(nombre=f.cleaned_data['nombre'],
                                   cuenta=f.cleaned_data['cuenta'],
                                   tipo=f.cleaned_data['tipo'],
                                   activo=f.cleaned_data['activo'],
                                   tipo_ambiente=f.cleaned_data['tipo_ambiente'],
                                   )
                eSetting.save(request)
                lista_items1 = json.loads(request.POST['lista_items1'])
                if lista_items1:
                    for lista in lista_items1:
                        if not User.objects.values("id").filter(pk=lista['id']).exists():
                            raise NameError(u"Usuario no encontrado")

                        eSetting.usuarios.add(lista['id'])
                log(u'Adiciono servicio web - WSDL: %s' % eSetting, request, "add")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'edit':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_web_services_wsdl')
                f = SettingWSDLForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if not Setting.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Servicio web a editar no encontrado")
                eSetting = Setting.objects.get(pk=request.POST['id'])
                eSetting.nombre = f.cleaned_data['nombre']
                eSetting.cuenta = f.cleaned_data['cuenta']
                eSetting.tipo = f.cleaned_data['tipo']
                eSetting.activo = f.cleaned_data['activo']
                eSetting.tipo_ambiente = f.cleaned_data['tipo_ambiente']
                eSetting.save(request)
                lista_items1 = json.loads(request.POST['lista_items1'])
                aux_usuarios = []
                if lista_items1:
                    for lista in lista_items1:
                        if not User.objects.values("id").filter(pk=lista['id']).exists():
                            raise NameError(u"Usuario no encontrado")
                        aux_usuarios.append(lista['id'])

                for usu in eSetting.get_usuarios():
                    if not usu.id in aux_usuarios:
                        eSetting.usuarios.remove(usu.id)

                if lista_items1:
                    for lista in lista_items1:
                        if not User.objects.values("id").filter(pk=lista['id']).exists():
                            raise NameError(u"Usuario no encontrado")
                        eSetting.usuarios.add(lista['id'])
                log(u'Edito servicio web - WSDL: %s' % eSetting, request, "edit")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'del':
            try:
                puede_realizar_accion(request, 'bd.puede_eliminar_web_services_wsdl')
                if not Setting.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Servicio a eliminar no encontrado")
                eDelete = eSetting = Setting.objects.get(pk=request.POST['id'])
                if eSetting.en_uso():
                    raise NameError(u"Servicio web en uso")
                eSetting.delete()
                log(u'Elimino servicio web - WSDL: %s' % eDelete, request, "del")
                messages.add_message(request, messages.SUCCESS, f'Se elimino correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el registro."})

        elif action == 'deleteUser':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_web_services_wsdl')
                if not Setting.objects.filter(pk=request.POST['ids']).exists():
                    raise NameError(u"Servicio no encontrado")
                eSetting = Setting.objects.get(pk=request.POST['ids'])
                if not User.objects.filter(pk=request.POST['idu']).exists():
                    raise NameError(u"Usuario del servicio no encontrado")
                eUser = User.objects.get(pk=request.POST['idu'])
                eSetting.usuarios.remove(eUser.id)
                log(u'Edito servicio web - WSDL: %s, se quito usuario: %s' % (eSetting, eUser.username), request, "edit")
                messages.add_message(request, messages.SUCCESS, f'Se elimino correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el registro."})

        elif action == 'loadDataTable':
            try:
                txt_filter = request.POST['sSearch'] if request.POST['sSearch'] else ''
                limit = int(request.POST['iDisplayLength']) if request.POST['iDisplayLength'] else 25
                offset = int(request.POST['iDisplayStart']) if request.POST['iDisplayStart'] else 0
                personal = int(request.POST['personal']) if request.POST['personal'] else 0
                superuser = int(request.POST['superuser']) if request.POST['superuser'] else 0
                activo = int(request.POST['activo']) if request.POST['activo'] else 0
                aaData = []
                tCount = 0
                users = User.objects.filter().order_by('username').distinct()
                if txt_filter:
                    search = txt_filter.strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        users = users.filter(Q(username__icontains=search) |
                                             Q(user_permissions__codename__icontains=search) |
                                             Q(user_permissions__name__icontains=search) |
                                             Q(persona__cedula__icontains=search) |
                                             Q(persona__pasaporte__icontains=search) |
                                             Q(persona__nombres__icontains=search) |
                                             Q(persona__apellido1__icontains=search) |
                                             Q(persona__apellido2__icontains=search)).distinct()
                    else:
                        users = users.filter(Q(persona__nombres__icontains=search) |
                                             Q(persona__apellido1__icontains=ss[0]) &
                                             Q(persona__apellido2__icontains=ss[1])).distinct()
                if personal > 0:
                    users = users.filter(is_staff=(personal == 1)).distinct()
                if superuser > 0:
                    users = users.filter(is_superuser=(superuser == 1)).distinct()
                if activo > 0:
                    users = users.filter(is_active=(activo == 1)).distinct()
                tCount = users.count()
                if offset == 0:
                    rows = users[offset:limit]
                else:
                    rows = users[offset:offset + limit]
                aaData = []
                ru = 0
                for row in rows:
                    ru += 1
                    persona = None
                    tipo_documento = None
                    tipo_persona = None
                    email = None
                    documento = None
                    if Persona.objects.filter(usuario=row).exists():
                        persona = Persona.objects.filter(usuario=row).first()
                        if persona.tipopersona == 1:
                            if persona.cedula:
                                tipo_documento = 'CEDULA'
                                documento = persona.cedula
                            else:
                                tipo_documento = 'PASAPORTE'
                                documento = persona.pasaporte
                        else:
                            tipo_documento = 'RUC'
                            documento = persona.ruc
                        tipo_persona = persona.get_tipopersona_display()
                        email = persona.emailinst
                    aaData.append([{"id": row.id,
                                    "username": row.username,
                                    "is_superuser": row.is_superuser,
                                    "is_staff": row.is_staff,
                                    "is_active": row.is_active,
                                    },
                                   row.id,
                                   {
                                       "username": row.username,
                                       "persona": persona.__str__() if persona else 'SIN PERSONA',
                                       "tipo_documento": tipo_documento if tipo_documento else 'SIN PERSONA',
                                       "documento": documento if documento else 'SIN PERSONA',
                                       "tipo_persona": tipo_persona if tipo_persona else 'SIN PERSONA',
                                       "email": email if email else 'SIN EMAIL',
                                       "password": row.password[1:len(row.password)-250] if row.password else 'SIN CONTRASEÑA',
                                   },
                                   row.is_active,
                                   row.is_superuser,
                                   row.is_staff,
                                   ])
                return JsonResponse({"result": "ok", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__(), "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        elif action == 'testConnection':
            try:
                if not 'idws' in request.POST:
                    raise NameError(u'No se encontro parametro de configuración')
                if not 'user' in request.POST:
                    raise NameError(u'No se encontro parametro de usuario')
                if not 'password' in request.POST:
                    raise NameError(u'No se encontro parametro de contraseña')
                password = request.POST['password']
                if not User.objects.values("id").filter(username=request.POST['user']).exists():
                    raise NameError(u"Usuario no encontrado")
                user = User.objects.filter(username=request.POST['user'])[0]
                if not Setting.objects.values("id").filter(pk=request.POST['idws']).exists():
                    raise NameError(u"No se encontro configruación")
                eSetting = Setting.objects.filter(pk=request.POST['idws'])[0]
                if not user.id in eSetting.get_usuarios().values_list("id", flat=True):
                    raise NameError(u'Usuario no encontrado en la configuración')
                aData = banco_pacifico.TestConnection(user, password)
                return JsonResponse({"result": "ok", "aData": aData})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error de conección. %s" % ex.__str__()})

        elif action == 'resetPassword':
            try:
                if not 'ids' in request.POST:
                    raise NameError(u'No se encontro parametro del servicio')
                if not 'idu' in request.POST:
                    raise NameError(u'No se encontro parametro de usuario')
                if not 'password' in request.POST:
                    raise NameError(u'No se encontro parametro de contraseña')
                password = request.POST['password']
                espacio = mayuscula = minuscula = numeros = False
                long = len(password)  # Calcula la longitud de la contraseña
                # y = password.isalnum()  # si es alfanumérica retona True
                for carac in password:
                    espacio = True if carac.isspace() else espacio  # si encuentra un espacio se cambia el valor user
                    mayuscula = True if carac.isupper() else mayuscula  # acumulador o contador de mayusculas
                    minuscula = True if carac.islower() == True else minuscula  # acumulador o contador de minúsculas
                    numeros = True if carac.isdigit() == True else numeros  # acumulador o contador de numeros

                if espacio == True:  # hay espacios en blanco
                    raise NameError(u"La clave no puede contener espacios.")
                if not mayuscula or not minuscula or not numeros or long < 8:
                    raise NameError(u"La clave elegida no es segura: debe contener letras minúsculas, mayúsculas, números y al menos 8 carácter.")

                if not User.objects.values("id").filter(pk=request.POST['idu']).exists():
                    raise NameError(u"Usuario no encontrado")
                user = User.objects.filter(pk=request.POST['idu'])[0]
                if not Setting.objects.values("id").filter(pk=request.POST['ids']).exists():
                    raise NameError(u"No se encontro servicio")
                eSetting = Setting.objects.filter(pk=request.POST['ids'])[0]
                if not user.id in eSetting.get_usuarios().values_list("id", flat=True):
                    raise NameError(u'Usuario no encontrado en el servicio')
                user.set_password(password)
                user.save()
                if (eUserAuth := UserAuth.objects.filter(usuario=user).first()) is not None:
                    if not eUserAuth.check_password(request.POST['pass']) or eUserAuth.check_data():
                        if not eUserAuth.check_password(request.POST['pass']):
                            eUserAuth.set_password(request.POST['pass'])
                        eUserAuth.save()
                else:
                    eUserAuth = UserAuth(usuario=user)
                    eUserAuth.set_data()
                    eUserAuth.set_password(request.POST['pass'])
                    eUserAuth.save()
                return JsonResponse({"result": "ok", "mensaje": u"Clave cambiada correctamente"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cambiar contraseña. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    puede_realizar_accion(request, 'bd.puede_agregar_web_services_wsdl')
                    data['title'] = u'Adicionar servicio web - WSDL'
                    f = SettingWSDLForm()
                    data['form'] = f
                    return render(request, "adm_sistemas/web_services/wsdl/add.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'edit':
                try:
                    puede_realizar_accion(request, 'bd.puede_modificar_web_services_wsdl')
                    data['title'] = u'Editar servicio web - WSDL'
                    if not Setting.objects.filter(pk=request.GET['id']).exists():
                        raise NameError(u"Servicio a editar no encontrado")
                    data['eSetting'] = eSetting = Setting.objects.get(pk=request.GET['id'])
                    f = SettingWSDLForm()
                    f.set_initial(eSetting)
                    data['form'] = f
                    return render(request, "adm_sistemas/web_services/wsdl/edit.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Admininistración de Servicio Web - WSDL'
                search = None
                ids = None
                settings = Setting.objects.filter(status=True)
                if 'id' in request.GET:
                    ids = request.GET['id']
                    settings = settings.filter(id=int(ids))
                if 's' in request.GET:
                    search = request.GET['s']
                    settings = settings.filter(Q(cuenta__banco__nombre__icontains=search) | Q(cuenta__numero=search) | Q(cuenta__tipocuenta__nombre__icontains=search)).distinct()
                paging = MiPaginador(settings, 25)
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
                data['settings'] = page.object_list
                return render(request, "adm_sistemas/web_services/wsdl/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect("/adm_sistemas/web_services?info=%s" % ex.__str__())
