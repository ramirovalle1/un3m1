# -*- coding: UTF-8 -*-
import random

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
from sga.models import Persona, LogEntryBackup, LogEntryBackupdos, AgregacionEliminacionMaterias, Inscripcion, Externo, \
    PerfilUsuario, PerfilAccesoUsuario
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    #
    # try:
    #     puede_realizar_accion(request, 'bd.puede_acceder_perfil_acceso_usuario')
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
                perfiles = PerfilAccesoUsuario.objects.all().order_by('grupo__id', 'coordinacion__id').distinct('grupo__id', 'coordinacion__id')
                if not persona.usuario.is_staff:
                    perfiles = perfiles.filter(status=True)
                if txt_filter:
                    search = txt_filter.strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        perfiles = perfiles.filter(Q(grupo__name__icontains=search) | Q(coordinacion__nombre__icontains=search))
                    else:
                        perfiles = perfiles.filter((Q(grupo__name__icontains=ss[0]) & Q(grupo__name__icontains=ss[1])) | (Q(coordinacion__nombre__icontains=ss[0]) & Q(coordinacion__nombre__icontains=ss[1])))

                tCount = perfiles.count()
                if offset == 0:
                    rows = perfiles[offset:limit]
                else:
                    rows = perfiles[offset:offset + limit]
                aaData = []
                for row in rows:
                    carreras = []
                    for pu in row.grupos_perfil_acceso_usuario():
                        carreras.append({"id": pu.carrera.id,
                                         "nombre": pu.carrera.__str__(),
                                         "is_related": pu.carrera.coordinacion_carrera().id == row.coordinacion.id if pu.carrera.tiene_coordinaciones() else False
                                         })

                    aaData.append([row.grupo.name,
                                   row.coordinacion.__str__(),
                                   carreras,
                                   {"id": row.id,
                                    "nombre_completo": f"{row.grupo.name} - {row.coordinacion.__str__()}",
                                    },
                                   ])
                return JsonResponse({"result": "ok", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__(), "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        if action == 'saveUserAccessProfile':
            try:
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] and int(request.POST['id']) != 0 else None
                typeForm = 'edit' if id else 'new'
                f = PerfilAccesoUsuarioForm(request.POST)
                if not f.is_valid():
                    raise NameError(u"Debe ingresar la información en todos los campos")
                if typeForm == 'new':
                    puede_realizar_accion(request, 'bd.puede_agregar_perfil_acceso_usuario')
                    for carrera in f.cleaned_data['carrera']:
                        if not PerfilAccesoUsuario.objects.values('id').filter(grupo=f.cleaned_data['grupo'], coordinacion=f.cleaned_data['coordinacion'], carrera=carrera).exists():
                            ePerfilAccesoUsuario = PerfilAccesoUsuario(grupo=f.cleaned_data['grupo'], coordinacion=f.cleaned_data['coordinacion'], carrera=carrera)
                            ePerfilAccesoUsuario.save(request)
                            log(u'Adiciono perfil acceso usuario: %s - %s - %s - [%s]' % (ePerfilAccesoUsuario.grupo, ePerfilAccesoUsuario.coordinacion, ePerfilAccesoUsuario.carrera, ePerfilAccesoUsuario.id), request, "add")

                else:
                    puede_realizar_accion(request, 'bd.puede_modificar_perfil_acceso_usuario')
                    if not PerfilAccesoUsuario.objects.filter(pk=id).exists():
                        raise NameError(u"No existe formulario a editar")
                    ePerfilAccesoUsuario = PerfilAccesoUsuario.objects.get(pk=id)
                    adicionarcarreras = Carrera.objects.filter(pk__in=f.cleaned_data['carrera']).exclude(pk__in=ePerfilAccesoUsuario.carreras_grupos_perfil_acceso_usuario().values_list('id', flat=True)).distinct()
                    for carrera in adicionarcarreras:
                        pa = PerfilAccesoUsuario(grupo=ePerfilAccesoUsuario.grupo, coordinacion=ePerfilAccesoUsuario.coordinacion, carrera=carrera)
                        pa.save(request)
                        log(u'Adiciono perfil acceso usuario: %s - %s - %s - [%s]' % (pa.grupo, pa.coordinacion, pa.carrera, pa.id), request, "add")
                    eliminar_perfiles = ePerfilAccesoUsuario.grupos_perfil_acceso_usuario().exclude(carrera__in=f.cleaned_data['carrera'])
                    for eliminar_perfil in eliminar_perfiles:
                        log(u'Elimino perfil acceso usuario: %s - %s - %s - [%s]' % (eliminar_perfil.grupo, eliminar_perfil.coordinacion, eliminar_perfil.carrera, eliminar_perfil.id), request, "del")
                        eliminar_perfil.delete()
                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar. %s" % ex.__str__()})

        if action == 'deleteUserAccessProfile':
            try:
                puede_realizar_accion(request, 'bd.puede_eliminar_persona')
                if not 'id' in request.POST or not request.POST['id']:
                    raise NameError(u"No se encontro registro a eliminar")
                object_id = int(request.POST['id'])
                if not PerfilAccesoUsuario.objects.filter(pk=object_id).exists():
                    raise NameError(u"No se encontro registro a eliminar")
                ePerfilAccesoUsuario = PerfilAccesoUsuario.objects.get(pk=object_id)
                eliminar_perfiles = ePerfilAccesoUsuario.grupos_perfil_acceso_usuario()
                for eliminar_perfil in eliminar_perfiles:
                    log(u'Elimino perfil acceso usuario: %s - %s - %s - [%s]' % (eliminar_perfil.grupo, eliminar_perfil.coordinacion, eliminar_perfil.carrera, eliminar_perfil.id), request, "del")
                    eliminar_perfil.delete()
                ePerfilAccesoUsuario.delete()
                return JsonResponse({"result": "ok", "mensaje": u"Se elimino correctamente el registro"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el registro. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'loadForm':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['new', 'edit', 'view'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    f = PerfilAccesoUsuarioForm()
                    ePerfilUser = None
                    id = 0
                    if typeForm in ['edit', 'view']:
                        id = int(request.GET['id']) if 'id' in request.GET and request.GET['id'] and int(request.GET['id']) != 0 else None
                        if not PerfilAccesoUsuario.objects.filter(pk=id).exists():
                            raise NameError(u"No existe formulario a editar")
                        ePerfilUser = PerfilAccesoUsuario.objects.get(pk=id)
                        f.set_init(ePerfilUser)
                        f.loadCarrera(ePerfilUser)
                        if typeForm == 'view':
                            f.view()
                        if typeForm == 'edit':
                            puede_realizar_accion(request, 'bd.puede_modificar_perfil_acceso_usuario')
                        data['ePerfilUser'] = ePerfilUser
                    else:
                        puede_realizar_accion(request, 'bd.puede_agregar_perfil_acceso_usuario')
                    data['form'] = f
                    data['frmName'] = "frmPerfil"
                    data['id'] = id
                    template = get_template("adm_sistemas/user_access_profile/frm.html")
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
                    template = get_template('adm_sistemas/persons/auditoria.html')
                    json_contenido = template.render(data)
                    return JsonResponse({"result": "ok", "contenido": json_contenido})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Administración de Perfiles de Acceso Usuario'
                # users = User.objects.filter().order_by('username')
                return render(request, "adm_sistemas/user_access_profile/view.html", data)
            except Exception as ex:
                pass
