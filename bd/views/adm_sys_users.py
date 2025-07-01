# -*- coding: UTF-8 -*-
import json
from unicodedata import name

from django.contrib import messages
from django.contrib.admin.models import LogEntry, ADDITION, DELETION
from django.contrib.admin.utils import unquote
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Permission, PermissionsMixin
from django.db import transaction, router
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils.encoding import force_str

from bd.models import LogQuery, get_deleted_objects, LogEntryLogin
from decorators import secure_module
from bd.forms import *
from moodle.models import UserAuth
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
import sys
from django.template.loader import get_template
from sga.funciones import log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery, convertir_fecha, \
    resetear_clave
from sga.models import Persona, LogEntryBackup, LogEntryBackupdos, AgregacionEliminacionMaterias, Inscripcion
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    #
    # try:
    #     puede_realizar_accion(request, 'bd.puede_acceder_usuario')
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
                personal = int(request.POST['personal']) if request.POST['personal'] else 0
                superuser = int(request.POST['superuser']) if request.POST['superuser'] else 0
                activo = int(request.POST['activo']) if request.POST['activo'] else 0
                aaData = []
                tCount = 0
                users = User.objects.filter().order_by('username')
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
                                             Q(persona__apellido2__icontains=search))
                    else:
                        users = users.filter(Q(persona__nombres__icontains=search) |
                                             Q(persona__apellido1__icontains=ss[0]) &
                                             Q(persona__apellido2__icontains=ss[1]))
                if personal > 0:
                    users = users.filter(is_staff=(personal == 1))
                if superuser > 0:
                    users = users.filter(is_superuser=(superuser == 1))
                if activo > 0:
                    users = users.filter(is_active=(activo == 1))
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
                    aaData.append([row.id,
                                   {
                                    "username": row.username,
                                    "persona": persona.__str__() if persona else 'SIN PERSONA',
                                    "tipo_documento": tipo_documento if tipo_documento else 'SIN PERSONA',
                                    "documento": documento if documento else 'SIN PERSONA',
                                    "tipo_persona": tipo_persona if tipo_persona else 'SIN PERSONA',
                                    "email": email if email else 'SIN EMAIL',
                                    "password": row.password[1:len(row.password)-50] if row.password else 'SIN CONTRASEÑA',
                                    },
                                   row.is_staff,
                                   row.is_superuser,
                                   row.is_active,
                                   row.last_login.strftime('%Y/%m/%d %H:%M:%S') if row.last_login else "SIN REGISTRO",
                                   row.date_joined.strftime('%Y/%m/%d %H:%M:%S') if row.date_joined else "SIN REGISTRO",
                                   {"id": row.id,
                                    "username": row.username,
                                    "is_superuser": row.is_superuser,
                                    "is_staff": row.is_staff,
                                    "is_active": row.is_active,
                                    },
                                   ])
                return JsonResponse({"result": "ok", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__(), "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        elif action == 'saveUser':
            try:
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] and int(request.POST['id']) != 0 else None
                typeForm = 'edit' if id else 'new'
                f = UserSystemForm(request.POST)
                if not f.is_valid():
                    raise NameError(u"Debe ingresar la información en todos los campos")
                if typeForm == 'new':
                    raise NameError(u"No se permite crear nuevo usuario")
                else:
                    if not User.objects.filter(pk=id).exists():
                        raise NameError(u"No existe formulario a editar")
                    email = f.cleaned_data['email'] if f.cleaned_data['email'] else ''
                    first_name = f.cleaned_data['first_name'] if f.cleaned_data['first_name'] else ''
                    last_name = f.cleaned_data['last_name'] if f.cleaned_data['last_name'] else ''
                    User.objects.filter(pk=id).update(email=email,
                                                      first_name=first_name,
                                                      last_name=last_name,
                                                      is_staff=f.cleaned_data['is_staff'],
                                                      is_active=f.cleaned_data['is_active'],
                                                      )
                    eUser = User.objects.get(pk=id)
                    log(u'Edito usuario: %s' % eUser, request, "edit")
                    if 'permissions' in request.POST:
                        permissions = json.loads(request.POST['permissions'])
                        permissions = [int(x) for x in permissions]
                        permissions_aux = eUser.user_permissions.all()
                        for p in permissions_aux:
                            if not p.id in permissions:
                                eUser.user_permissions.remove(p)
                                p.save()
                        for p in Permission.objects.filter(pk__in=permissions):
                            eUser.user_permissions.add(p)

                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente el usuario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar el usuario. %s" % ex.__str__()})

        elif action == 'resetKeyUser':
            try:
                puede_realizar_accion(request, 'bd.puede_resetear_clave_usuario')
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] and int(request.POST['id']) != 0 else None
                if not User.objects.filter(pk=id).exists():
                    raise NameError(u"No existe usuario a resetear la clave")
                eUser = User.objects.filter(pk=id)
                if not Persona.objects.filter(usuario=eUser).exists():
                    raise NameError(u"No existe persona asociada al usuario")
                ePersona = Persona.objects.filter(usuario=eUser).first()
                resetear_clave(ePersona)
                log(u'Reseteo clave de usuario: %s de la persona: %s' % (eUser, ePersona), request, "edit")
                return JsonResponse({"result": "ok", "mensaje": u"Se reseteo correctamente la clave del usuario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al resetear la clave. %s" % ex.__str__()})

        elif action == 'deleteUser':
            try:
                puede_realizar_accion(request, 'bd.puede_eliminar_usuario')
                if not 'id' in request.POST or not request.POST['id']:
                    raise NameError(u"No se encontro registro a eliminar")
                object_id = int(request.POST['id'])
                if not User.objects.filter(pk=object_id).exists():
                    raise NameError(u"No se encontro registro a eliminar")
                eUser = User.objects.get(pk=object_id)
                log(u'Elimino usuario: %s' % eUser, request, "del")
                eUser.delete()
                return JsonResponse({"result": "ok", "mensaje": u"Se elimino correctamente el usuario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el usuario. %s" % ex.__str__()})

        elif action == 'saveUserPassword':
            try:
                puede_realizar_accion(request, 'bd.puede_resetear_clave_usuario')
                if not 'id' in request.POST or not request.POST['id']:
                    raise NameError(u"No se encontro registro")
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] and int(request.POST['id']) != 0 else None
                if not User.objects.filter(pk=id).exists():
                    raise NameError(u"No se encontro registro")
                f = UserPasswordForm(request.POST)
                if not f.is_valid():
                    raise NameError(u"Debe ingresar la nueva contraseña")
                if f.cleaned_data['password'] != f.cleaned_data['password2']:
                    raise NameError(u"La contraseña no coinciden")
                # User.objects.filter(pk=id).update(password=f.cleaned_data['password'])
                eUser = User.objects.get(pk=id)
                eUser.set_password(f.cleaned_data['password'])
                eUser.save()
                if (eUserAuth := UserAuth.objects.filter(usuario=eUser).first()) is not None:
                    if not eUserAuth.check_password(request.POST['pass']) or eUserAuth.check_data():
                        if not eUserAuth.check_password(request.POST['pass']):
                            eUserAuth.set_password(request.POST['pass'])
                        eUserAuth.save()
                else:
                    eUserAuth = UserAuth(usuario=eUser)
                    eUserAuth.set_data()
                    eUserAuth.set_password(request.POST['pass'])
                    eUserAuth.save()

                log(u'Cambio contraseña de usuario: %s' % eUser.username, request, "edit")
                return JsonResponse({"result": "ok", "mensaje": f"Se cambio contraseña correctamente del usuario {eUser.username}"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al cambiar contraseña del usuario. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'loadFormUser':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['new', 'edit', 'view'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    f = UserSystemForm()
                    eUser = None
                    id = 0
                    if typeForm in ['edit', 'view']:
                        id = int(request.GET['id']) if 'id' in request.GET and request.GET['id'] and int(request.GET['id']) != 0 else None
                        if not User.objects.filter(pk=id).exists():
                            raise NameError(u"No existe formulario a editar")
                        eUser = User.objects.get(pk=id)
                        f.set_initial(eUser)
                        if typeForm == 'view':
                            f.view()
                        if typeForm == 'edit':
                            puede_realizar_accion(request, 'bd.puede_modificar_usuario')
                            f.edit()
                        data['ePermissions'] = eUser.user_permissions.all()
                        data['eUser'] = eUser
                    data['form'] = f
                    data['frmName'] = "frmUser"
                    data['typeForm'] = typeForm
                    data['id'] = id
                    template = get_template("adm_sistemas/users/frm.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'loadFormPassword':
                try:
                    f = UserPasswordForm()
                    id = int(request.GET.get('id', '0'))
                    if not User.objects.filter(pk=id).exists():
                        raise NameError(u"No existe usuario")
                    eUser = User.objects.get(pk=id)
                    if eUser.is_superuser:
                        raise NameError(u"No se puede cambiar contraseña de super usuario")
                    puede_realizar_accion(request, 'bd.puede_resetear_clave_usuario')
                    data['eUser'] = eUser
                    data['form'] = f
                    data['frmName'] = "frmUserPassword"
                    data['id'] = id
                    template = get_template("adm_sistemas/users/frmPassword.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'loadAuditoria':
                try:
                    baseDate = datetime.today()
                    year = request.GET['year'] if 'year' in request.GET and request.GET['year'] else baseDate.year
                    month = request.GET['month'] if 'month' in request.GET and request.GET['month'] else baseDate.month
                    data['id'] = request.GET['id']
                    data['user'] = user = User.objects.get(pk=int(request.GET['id']))
                    person = None
                    if Persona.objects.filter(usuario=user).exists():
                        person = Persona.objects.get(usuario=user)
                        logs = LogEntry.objects.filter(Q(change_message__icontains=person.__str__()) | Q(user=user), action_time__year=year).exclude(user__is_superuser=True)
                        logs1 = LogEntryBackup.objects.filter(Q(change_message__icontains=person.__str__()) | Q(user=user), action_time__year=year).exclude(user__is_superuser=True)
                        logs2 = LogEntryBackupdos.objects.filter(Q(change_message__icontains=person.__str__()) | Q(user=user), action_time__year=year).exclude(user__is_superuser=True)
                        logs3 = LogEntryLogin.objects.filter(user=user, action_time__year=year).exclude(user__is_superuser=True)
                    else:
                        logs = LogEntry.objects.filter(Q(user=user), action_time__year=year).exclude(user__is_superuser=True)
                        logs1 = LogEntryBackup.objects.filter(Q(user=user), action_time__year=year).exclude(user__is_superuser=True)
                        logs2 = LogEntryBackupdos.objects.filter(Q(user=user), action_time__year=year).exclude(user__is_superuser=True)
                        logs3 = LogEntryLogin.objects.filter(user=user, action_time__year=year).exclude(user__is_superuser=True)

                    addmaterias = None
                    if Inscripcion.objects.filter(persona=person).exists():
                        addmaterias = AgregacionEliminacionMaterias.objects.filter(matricula__inscripcion__in=Inscripcion.objects.filter(persona=person), fecha__year=year).order_by('-fecha')

                    if int(month):
                        logs = logs.filter(action_time__month=month)
                        logs1 = logs1.filter(action_time__month=month)
                        logs2 = logs2.filter(action_time__month=month)
                        logs3 = logs3.filter(action_time__month=month)
                    if addmaterias:
                        addmaterias = addmaterias.filter(fecha__month=month)

                    logslist0 = list(logs.values_list("action_time", "action_flag", "change_message", "user__username"))
                    logslist1 = list(logs1.values_list("action_time", "action_flag", "change_message", "user__username"))
                    logslist2 = list(logs2.values_list("action_time", "action_flag", "change_message", "user__username"))
                    logslist = logslist0 + logslist1 + logslist2
                    aLogList = []
                    for xItem in logslist:
                        # print(xItem)
                        if xItem[1] == 1:
                            action_flag = '<label class="label label-success">AGREGAR</label>'
                        elif xItem[1] == 2:
                            action_flag = '<label class="label label-info">EDITAR</label>'
                        elif xItem[1] == 3:
                            action_flag = '<label class="label label-important">ELIMINAR</label>'
                        else:
                            action_flag = '<label class="label label-warning">OTRO</label>'
                        aLogList.append({"action_time": xItem[0],
                                         "action_flag": action_flag,
                                         "change_message": xItem[2],
                                         "username": xItem[3]})
                    for xItem in list(logs3.values_list("action_time", "action_flag", "change_message", "user__username", "id")):
                        l = LogEntryLogin.objects.get(pk=xItem[4])
                        if xItem[1] == 1:
                            action_flag = '<label class="label label-success">EXITOSO</label>'
                        elif xItem[1] == 2:
                            action_flag = '<label class="label label-warning">FALLIDO</label>'
                        else:
                            action_flag = '<label class="label label-important">DESCONOCIDO</label>'
                        aLogList.append({"action_time": xItem[0],
                                         "action_flag": action_flag,
                                         "change_message": l.get_data_message(),
                                         "username": xItem[3]
                                         })
                    if addmaterias:
                        addmateriaslist = list(addmaterias.values_list("fecha", "agregacion", "asignatura__nombre", "responsable__usuario__username"))
                        aLogAddMateriaslist = []
                        my_time = datetime.min.time()
                        for xItem in addmateriaslist:
                            # print(xItem)
                            aLogAddMateriaslist.append({"action_time": datetime.combine(xItem[0], my_time),
                                                        "action_flag": ADDITION if xItem[1] else DELETION,
                                                        "change_message": u"%s la asignatura %s" % (("Agrego" if xItem[1] else "Elimino"), xItem[2]),
                                                        "username": xItem[3]})
                        datalogs = aLogList + aLogAddMateriaslist
                    else:
                        datalogs = aLogList
                    data['logs'] = sorted(datalogs, key=lambda x: x['action_time'], reverse=True)
                    numYear = 6
                    dateListYear = []
                    for x in range(0, numYear):
                        dateListYear.append((baseDate.year) - x)
                    data['list_years'] = dateListYear
                    data['year_now'] = int(year)
                    data['month_now'] = int(month)
                    template = get_template('adm_sistemas/users/auditoria.html')
                    json_contenido = template.render(data)
                    return JsonResponse({"result": "ok", "contenido": json_contenido})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

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
                data['title'] = 'Administración de Usuarios del Sistema'
                # users = User.objects.filter().order_by('username')
                return render(request, "adm_sistemas/users/view.html", data)
            except Exception as ex:
                pass
