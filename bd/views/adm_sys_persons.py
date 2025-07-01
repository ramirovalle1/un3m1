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
    PerfilUsuario
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    #
    # try:
    #     puede_realizar_accion(request, 'bd.puede_acceder_persona')
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
                tipopersona = int(request.POST['tipopersona']) if request.POST['tipopersona'] else 0
                perfil = int(request.POST['perfil']) if request.POST['perfil'] else 0
                perfil_estado = int(request.POST['perfil_estado']) if request.POST['perfil_estado'] else 0
                aaData = []
                tCount = 0
                personas = Persona.objects.filter().order_by('apellido1', 'apellido2', 'nombres').distinct()
                if not persona.usuario.is_staff:
                    personas = personas.filter(status=True).distinct()
                if txt_filter:
                    search = txt_filter.strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        personas = personas.filter(Q(cedula__icontains=search) |
                                                   Q(pasaporte__icontains=search) |
                                                   Q(ruc__icontains=search) |
                                                   Q(nombres__icontains=search) |
                                                   Q(apellido1__icontains=search) |
                                                   Q(apellido2__icontains=search) |
                                                   Q(usuario__user_permissions__codename__icontains=search) |
                                                   Q(usuario__user_permissions__name__icontains=search) |
                                                   Q(usuario__groups__name__icontains=search)
                                                   )
                    else:
                        personas = personas.filter(Q(nombres__icontains=search) |
                                                   Q(apellido1__icontains=ss[0]) &
                                                   Q(apellido2__icontains=ss[1]))
                if tipopersona > 0:
                    personas = personas.filter(tipopersona=tipopersona).distinct()
                if perfil > 0:
                    if perfil == 1:
                        personas = personas.filter(administrativo__isnull=False).distinct()
                        if perfil_estado > 0:
                            personas = personas.filter(administrativo__isnull=False, administrativo__activo=perfil_estado == 1).distinct()
                    elif perfil == 2:
                        personas = personas.filter(profesor__isnull=False).distinct()
                        if perfil_estado > 0:
                            personas = personas.filter(profesor__isnull=False, profesor__activo=perfil_estado == 1).distinct()
                    elif perfil == 3:
                        personas = personas.filter(inscripcion__isnull=False).distinct()
                        if perfil_estado > 0:
                            personas = personas.filter(inscripcion__isnull=False, inscripcion__activo=perfil_estado == 1).distinct()

                tCount = personas.count()
                if offset == 0:
                    rows = personas[offset:limit]
                else:
                    rows = personas[offset:offset + limit]
                aaData = []
                ru = 0
                for row in rows:
                    documento = '-'
                    tipodocumento = '-'
                    if row.cedula:
                        documento = row.cedula
                        tipodocumento = "CEDULA"
                    elif row.pasaporte:
                        documento = row.pasaporte
                        tipodocumento = "PASAPORTE"
                    elif row.ruc:
                        documento = row.ruc
                        tipodocumento = "RUC"
                    perfiles = []
                    perfiles_sga = []
                    perfiles_sagest = []
                    perfiles_posgrado = []
                    x1 = row.mis_perfilesusuarios_app('sga')
                    for perfil in x1:
                        principal = row.perfilusuario_principal(x1, 'sga')
                        isPrincipal = False
                        if principal and principal.id == perfil.id:
                            isPrincipal = True
                        perfiles_sga.append({"id": perfil.id,
                                             "perfil": perfil.tipo(),
                                             "visible": perfil.visible,
                                             "principal": isPrincipal
                                             })
                    x2 = row.mis_perfilesusuarios_app('sagest')
                    for perfil in x2:
                        principal = row.perfilusuario_principal(x2, 'sagest')
                        isPrincipal = False
                        if principal and principal.id == perfil.id:
                            isPrincipal = True
                        perfiles_sagest.append({"id": perfil.id,
                                                "perfil": perfil.tipo(),
                                                "visible": perfil.visible,
                                                "principal": isPrincipal
                                                })
                    x3 = row.mis_perfilesusuarios_app('posgrado')
                    for perfil in x3:
                        principal = row.perfilusuario_principal(x3, 'posgrado')
                        isPrincipal = False
                        if principal and principal.id == perfil.id:
                            isPrincipal = True
                        perfiles_posgrado.append({"id": perfil.id,
                                                  "perfil": perfil.tipo(),
                                                  "visible": perfil.visible,
                                                  "principal": isPrincipal
                                                  })
                    perfiles.append({"id": random.random(),
                                     "nombre": "SGA",
                                     "perfiles": perfiles_sga})
                    perfiles.append({"id": random.random(),
                                     "nombre": "SAGEST",
                                     "perfiles": perfiles_sagest})
                    perfiles.append({"id": random.random(),
                                     "nombre": "POSGRADO",
                                     "perfiles": perfiles_posgrado})

                    grupos = []
                    if row.usuario:
                        for g in row.grupos():
                            grupos.append({"id": g.id,
                                           "name": g.name,
                                           })
                    permissions = []
                    if row.usuario:
                        for p in row.usuario.user_permissions.all():
                            permissions.append({"id": p.id,
                                                "codename": p.codename,
                                                "name": p.name})
                    aaData.append([row.id,
                                   {"tipo_persona": row.tipopersona if row.tipopersona else 1,
                                    "type_document": tipodocumento,
                                    "document": documento,
                                    "nombre_completo": row.nombre_completo(),
                                    "sexo": row.sexo.nombre if row.sexo else '-',
                                    "telefono": row.telefono if row.telefono else '-',
                                    "email": row.email if row.email else '-',
                                    "emailinst": row.emailinst if row.emailinst else '-'
                                    },
                                   grupos,
                                   perfiles,
                                   {"usuario": row.usuario.username if row.usuario else '-',
                                    "activo": row.usuario.is_active if row.usuario else False,
                                    "permissions": permissions,
                                   },
                                   {"id": row.id,
                                    "tipo_persona": row.tipopersona if row.tipopersona else 1,
                                    "nombre_completo": row.nombre_completo(),
                                    "is_superuser": row.usuario.is_superuser if row.usuario else False,
                                    "id_user": row.usuario.id if row.usuario else 0,
                                    },
                                   ])
                return JsonResponse({"result": "ok", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__(), "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        if action == 'savePerson':
            try:
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] and int(request.POST['id']) != 0 else None
                typePerson = int(request.POST['typePerson']) if 'typePerson' in request.POST and request.POST['typePerson'] and int(request.POST['typePerson']) in [1, 2] else None
                typeForm = 'edit' if id else 'new'
                f = PersonSystemForm(request.POST)
                f.tipo_persona(typePerson)
                if not f.is_valid():
                    raise NameError(u"Debe ingresar la información en todos los campos")
                if typeForm == 'new':
                    puede_realizar_accion(request, 'bd.puede_agregar_persona')
                    if f.cleaned_data['tipo_documento'] == 1 and Persona.objects.filter(cedula=f.cleaned_data['documento']).exists():
                        raise NameError(f"Persona existente con numero de cedula {f.cleaned_data['documento']}.")
                    elif f.cleaned_data['tipo_documento'] == 2 and Persona.objects.filter(pasaporte=f.cleaned_data['documento']).exists():
                        raise NameError(f"Persona existente con numero de pasaporte {f.cleaned_data['documento']}.")
                    elif f.cleaned_data['tipo_documento'] == 3 and Persona.objects.filter(ruc=f.cleaned_data['documento']).exists():
                        raise NameError(f"Empresa existente con numero de RUC {f.cleaned_data['documento']}.")
                    if typePerson == 1:
                        person = Persona(cedula=f.cleaned_data['documento'] if int(f.cleaned_data['tipo_documento']) == 1 else '',
                                         pasaporte=f.cleaned_data['documento'] if int(f.cleaned_data['tipo_documento']) == 2 else '',
                                         nombres=f.cleaned_data['nombres'] if f.cleaned_data['nombres'] else '',
                                         apellido1=f.cleaned_data['apellido1'] if f.cleaned_data['apellido1'] else '',
                                         apellido2=f.cleaned_data['apellido2'] if f.cleaned_data['apellido2'] else '',
                                         sexo=f.cleaned_data['sexo'],
                                         nacimiento=f.cleaned_data['nacimiento'],
                                         paisnacimiento=f.cleaned_data['paisnacimiento'],
                                         provincianacimiento=f.cleaned_data['provincianacimiento'],
                                         cantonnacimiento=f.cleaned_data['cantonnacimiento'],
                                         parroquianacimiento=f.cleaned_data['parroquianacimiento'],
                                         ciudad=f.cleaned_data['ciudad'],
                                         sector=f.cleaned_data['sector'],
                                         direccion=f.cleaned_data['direccion'],
                                         direccion2=f.cleaned_data['direccion2'],
                                         num_direccion=f.cleaned_data['num_direccion'],
                                         pais=f.cleaned_data['pais'],
                                         provincia=f.cleaned_data['provincia'],
                                         canton=f.cleaned_data['canton'],
                                         parroquia=f.cleaned_data['parroquia'],
                                         telefono=f.cleaned_data['telefono'],
                                         telefono_conv=f.cleaned_data['telefono_conv'],
                                         email=f.cleaned_data['email'],
                                         tipopersona=1,
                                         )
                        person.save(request)
                        person.mi_perfil()
                        log(u'Adiciono persona natural: %s' % person, request, "add")
                    else:
                        person = Persona(ruc=f.cleaned_data['documento'],
                                         nombres=f.cleaned_data['nombreempresa'],
                                         apellido1='',
                                         apellido2='',
                                         contribuyenteespecial=f.cleaned_data['contribuyenteespecial'],
                                         nacimiento=f.cleaned_data['nacimiento'],
                                         ciudad=f.cleaned_data['ciudad'],
                                         sector=f.cleaned_data['sector'],
                                         direccion=f.cleaned_data['direccion'],
                                         direccion2=f.cleaned_data['direccion2'],
                                         num_direccion=f.cleaned_data['num_direccion'],
                                         pais=f.cleaned_data['pais'],
                                         provincia=f.cleaned_data['provincia'],
                                         canton=f.cleaned_data['canton'],
                                         parroquia=f.cleaned_data['parroquia'],
                                         telefono=f.cleaned_data['telefono'],
                                         telefono_conv=f.cleaned_data['telefono_conv'],
                                         email=f.cleaned_data['email'],
                                         tipopersona=2,
                                         )
                        person.save(request)
                        log(u'Adiciono persona juridica: %s' % person, request, "add")
                        externo = Externo(persona=person,
                                          nombrecomercial=f.cleaned_data['nombrecomercial'],
                                          nombrecontacto=f.cleaned_data['nombrecontacto'],
                                          telefonocontacto=f.cleaned_data['telefonocontacto'],
                                          )
                        externo.save(request)
                        log(u'Adiciono cliente externo: %s' % externo, request, "add")
                        person.crear_perfil(externo=externo)
                        person.mi_perfil()
                else:
                    puede_realizar_accion(request, 'bd.puede_modificar_persona')
                    if not Persona.objects.filter(pk=id).exists():
                        raise NameError(u"No existe formulario a editar")
                    if f.cleaned_data['tipo_documento'] == 1 and Persona.objects.filter(cedula=f.cleaned_data['documento']).exclude(pk=id).exists():
                        raise NameError(f"Persona existente con numero de cedula {f.cleaned_data['documento']}.")
                    elif f.cleaned_data['tipo_documento'] == 2 and Persona.objects.filter(pasaporte=f.cleaned_data['documento']).exclude(pk=id).exists():
                        raise NameError(f"Persona existente con numero de pasaporte {f.cleaned_data['documento']}.")
                    elif f.cleaned_data['tipo_documento'] == 3 and Persona.objects.filter(ruc=f.cleaned_data['documento']).exclude(pk=id).exists():
                        raise NameError(f"Empresa existente con numero de RUC {f.cleaned_data['documento']}.")
                    person = Persona.objects.get(pk=id)
                    if typePerson == 1:
                        person.cedula = f.cleaned_data['documento'] if int(f.cleaned_data['tipo_documento']) == 1 else ''
                        person.pasaporte = f.cleaned_data['documento'] if int(f.cleaned_data['tipo_documento']) == 2 else ''
                        person.nombres = f.cleaned_data['nombres'] if f.cleaned_data['nombres'] else ''
                        person.apellido1 = f.cleaned_data['apellido1'] if f.cleaned_data['apellido1'] else ''
                        person.apellido2 = f.cleaned_data['apellido2'] if f.cleaned_data['apellido2'] else ''
                        person.sexo = f.cleaned_data['sexo']
                        person.nacimiento = f.cleaned_data['nacimiento']
                        person.paisnacimiento = f.cleaned_data['paisnacimiento']
                        person.provincianacimiento = f.cleaned_data['provincianacimiento']
                        person.cantonnacimiento = f.cleaned_data['cantonnacimiento']
                        person.parroquianacimiento = f.cleaned_data['parroquianacimiento']
                        person.ciudad = f.cleaned_data['ciudad']
                        person.sector = f.cleaned_data['sector']
                        person.direccion = f.cleaned_data['direccion']
                        person.direccion2 = f.cleaned_data['direccion2']
                        person.num_direccion = f.cleaned_data['num_direccion']
                        person.pais = f.cleaned_data['pais']
                        person.provincia = f.cleaned_data['provincia']
                        person.canton = f.cleaned_data['canton']
                        person.parroquia = f.cleaned_data['parroquia']
                        person.telefono = f.cleaned_data['telefono']
                        person.telefono_conv = f.cleaned_data['telefono_conv']
                        person.email = f.cleaned_data['email']
                        person.save(request)
                        log(u'Edito persona natural: %s' % person, request, "edit")
                    else:
                        person.ruc = f.cleaned_data['documento']
                        person.nombres = f.cleaned_data['nombreempresa']
                        person.nacimiento = f.cleaned_data['nacimiento']
                        person.ciudad = f.cleaned_data['ciudad']
                        person.sector = f.cleaned_data['sector']
                        person.direccion = f.cleaned_data['direccion']
                        person.direccion2 = f.cleaned_data['direccion2']
                        person.num_direccion = f.cleaned_data['num_direccion']
                        person.pais = f.cleaned_data['pais']
                        person.provincia = f.cleaned_data['provincia']
                        person.canton = f.cleaned_data['canton']
                        person.parroquia = f.cleaned_data['parroquia']
                        person.telefono = f.cleaned_data['telefono']
                        person.telefono_conv = f.cleaned_data['telefono_conv']
                        person.email = f.cleaned_data['email']
                        person.save(request)
                        log(u'Edito persona juridica: %s' % person, request, "edit")
                        if not Externo.objects.filter(persona=person).exists():
                            externo = Externo(persona=person,
                                              nombrecomercial=f.cleaned_data['nombrecomercial'],
                                              nombrecontacto=f.cleaned_data['nombrecontacto'],
                                              telefonocontacto=f.cleaned_data['telefonocontacto'],
                                              )
                            externo.save(request)
                            log(u'Adiciono cliente externo: %s' % externo, request, "add")
                            person.crear_perfil(externo=externo)
                            person.mi_perfil()
                        else:
                            externo = Externo.objects.get(persona=person)
                            externo.nombrecomercial = f.cleaned_data['nombrecomercial']
                            externo.nombrecontacto = f.cleaned_data['nombrecontacto']
                            externo.telefonocontacto = f.cleaned_data['telefonocontacto']
                            externo.save(request)
                            log(u'Edito cliente externo: %s' % externo, request, "edit")
                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar. %s" % ex.__str__()})

        if action == 'deletePerson':
            try:
                puede_realizar_accion(request, 'bd.puede_eliminar_persona')
                if not 'id' in request.POST or not request.POST['id']:
                    raise NameError(u"No se encontro registro a eliminar")
                object_id = int(request.POST['id'])
                if not Persona.objects.filter(pk=object_id).exists():
                    raise NameError(u"No se encontro registro a eliminar")
                ePersona = Persona.objects.get(pk=object_id)
                log(u'Elimino persona: %s' % Persona, request, "del")
                Persona.delete()
                return JsonResponse({"result": "ok", "mensaje": u"Se elimino correctamente el registro"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el registro. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'loadFormPerson':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['new', 'edit', 'view'] else None
                    typePerson = int(request.GET['typePerson']) if 'typePerson' in request.GET and request.GET['typePerson'] and int(request.GET['typePerson']) in [1, 2] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    if typePerson is None:
                        raise NameError(u"No se encontro el tipo de persona")
                    f = PersonSystemForm()
                    f.tipo_persona(typePerson)
                    ePersona = None
                    id = 0
                    if typeForm in ['edit', 'view']:
                        id = int(request.GET['id']) if 'id' in request.GET and request.GET['id'] and int(request.GET['id']) != 0 else None
                        if not Persona.objects.filter(pk=id).exists():
                            raise NameError(u"No existe formulario a editar")
                        ePersona = Persona.objects.get(pk=id)
                        f.set_initial(ePersona)
                        if typeForm == 'view':
                            f.view()
                        if typeForm == 'edit':
                            puede_realizar_accion(request, 'bd.puede_modificar_persona')
                        data['ePersona'] = ePersona
                    else:
                        puede_realizar_accion(request, 'bd.puede_agregar_persona')
                    data['form'] = f
                    data['frmName'] = "frmPerson"
                    data['typePerson'] = typePerson
                    data['id'] = id
                    template = get_template("adm_sistemas/persons/frm.html")
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
                data['title'] = 'Administración de Personas/Empresas del Sistema'
                # users = User.objects.filter().order_by('username')
                return render(request, "adm_sistemas/persons/view.html", data)
            except Exception as ex:
                pass
