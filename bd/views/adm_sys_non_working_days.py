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

from bd.models import LogQuery, get_deleted_objects, LogEntryLogin, TemplateBaseSetting
from decorators import secure_module
from bd.forms import *
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
import sys
from django.template.loader import get_template
from sga.funciones import log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery, convertir_fecha, \
    resetear_clave, MiPaginador
from sga.models import Persona, LogEntryBackup, LogEntryBackupdos, AgregacionEliminacionMaterias, Inscripcion, Modulo, \
    ModuloGrupo, DiasNoLaborable, TYPE_DAYS_NO_WORKING, DiasNoLaborableCoordinacion, DiasNoLaborableCoordinacionCarrera
from soap.models import Setting
from sga.templatetags.sga_extras import encrypt
from soap.consumer import banco_pacifico


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    #
    # try:
    #     puede_realizar_accion(request, 'bd.puede_acceder_dia_no_laborable')
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
                idp = int(request.POST['idp']) if request.POST['idp'] else 0
                idcc = int(request.POST['idcc']) if request.POST['idcc'] else 0
                idc = int(request.POST['idc']) if request.POST['idc'] else 0
                idnm = int(request.POST['idnm']) if request.POST['idnm'] else 0
                motivo = int(request.POST['type']) if request.POST['type'] else 0
                aaData = []
                tCount = 0
                days = DiasNoLaborable.objects.filter()
                if txt_filter:
                    search = txt_filter.strip()
                    days = days.filter(Q(observaciones__icontains=search)).distinct()
                if idp > 0:
                    days = days.filter(periodo_id=idp)
                if idcc > 0:
                    days = days.filter(coordinacion_id=idcc)
                if idc > 0:
                    days = days.filter(carrera_id=idc)
                if idnm > 0:
                    days = days.filter(nivelmalla_id=idnm)
                if motivo > 0:
                    days = days.filter(motivo=motivo)
                tCount = days.count()
                if offset == 0:
                    rows = days[offset:limit]
                else:
                    rows = days[offset:offset + limit]
                aaData = []
                for row in rows:
                    coordinacion = 'N/A'
                    if row.version == 1:
                        if row.coordinacion:
                            coordinacion = row.coordinacion.__str__()
                        else:
                            coordinacion = 'TODAS'

                    aaData.append([row.id,
                                   f"{row.fecha.strftime('%Y-%m-%d')} desde {row.desde.strftime('%H:%m')} hasta {row.hasta.strftime('%H:%m')}",
                                   row.get_tipo_accion(),
                                   row.periodo.__str__() if row.periodo else 'N/A',
                                   coordinacion,
                                   # row.carrera.__str__() if row.carrera else 'TODAS',
                                   # row.nivelmalla.__str__() if row.nivelmalla else 'TODAS',
                                   dict(TYPE_DAYS_NO_WORKING)[row.motivo] if row.motivo else '-',
                                   row.observaciones,
                                   {
                                       "id": row.id,
                                       "nombre": row.__str__(),
                                       "v_c": 1 if row.valida_coordinacion else 0
                                   },
                                   ])
                return JsonResponse({"result": "ok", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__(), "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        elif action == 'saveDayNoWorking':
            try:
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] and int(request.POST['id']) != 0 else None
                typeForm = 'edit' if id else 'new'
                f = DiasNoLaborableForm(request.POST)
                if not f.is_valid():
                    # [(k, v[0]) for k, v in f.errors.items()]
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if typeForm == 'new':
                    puede_realizar_accion(request, 'bd.puede_agregar_dia_no_laborable')
                    if DiasNoLaborable.objects.filter(periodo=f.cleaned_data['periodo'], coordinacion=f.cleaned_data['coordinacion'], carrera=f.cleaned_data['carrera'], nivelmalla=f.cleaned_data['nivelmalla'], fecha=f.cleaned_data['fecha']).exists():
                        raise NameError(u"Registro debe ser único")

                    eDiasNoLaborable = DiasNoLaborable(tipo_accion=f.cleaned_data['tipo_accion'],
                                                       periodo=f.cleaned_data['periodo'],
                                                       coordinacion=None,
                                                       carrera=None,
                                                       nivelmalla=None,
                                                       fecha=f.cleaned_data['fecha'],
                                                       desde=f.cleaned_data['desde'],
                                                       hasta=f.cleaned_data['hasta'],
                                                       motivo=f.cleaned_data['motivo'],
                                                       observaciones=f.cleaned_data['observaciones'],
                                                       valida_coordinacion=f.cleaned_data['valida_coordinacion'],
                                                       activo=f.cleaned_data['activo'],
                                                       version=2,
                                                       )
                    eDiasNoLaborable.save(request)
                    log(u'Adicionado día no laborable: %s' % eDiasNoLaborable, request, "add")
                else:
                    puede_realizar_accion(request, 'bd.puede_modificar_dia_no_laborable')
                    if not DiasNoLaborable.objects.filter(pk=id).exists():
                        raise NameError(u"No existe formulario a editar")
                    if DiasNoLaborable.objects.filter(periodo=f.cleaned_data['periodo'], coordinacion=f.cleaned_data['coordinacion'], carrera=f.cleaned_data['carrera'], nivelmalla=f.cleaned_data['nivelmalla'], fecha=f.cleaned_data['fecha']).exclude(pk=id).exists():
                        raise NameError(u"Registro debe ser única")
                    eDiasNoLaborable = DiasNoLaborable.objects.get(pk=id)
                    eDiasNoLaborable.tipo_accion = f.cleaned_data['tipo_accion']
                    eDiasNoLaborable.valida_coordinacion = f.cleaned_data['valida_coordinacion']
                    eDiasNoLaborable.activo = f.cleaned_data['activo']
                    eDiasNoLaborable.periodo = f.cleaned_data['periodo']
                    eDiasNoLaborable.coordinacion = f.cleaned_data['coordinacion']
                    eDiasNoLaborable.carrera = f.cleaned_data['carrera']
                    eDiasNoLaborable.nivelmalla = f.cleaned_data['nivelmalla']
                    eDiasNoLaborable.fecha = f.cleaned_data['fecha']
                    eDiasNoLaborable.desde = f.cleaned_data['desde']
                    eDiasNoLaborable.hasta = f.cleaned_data['hasta']
                    eDiasNoLaborable.motivo = f.cleaned_data['motivo']
                    eDiasNoLaborable.observaciones = f.cleaned_data['observaciones']
                    eDiasNoLaborable.save(request)
                    log(u'Edito día no laborable: %s' % eDiasNoLaborable, request, "edit")
                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente día no laborable"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar día no laborable. %s" % ex.__str__()})

        elif action == 'deleteDayNoWorking':
            try:
                puede_realizar_accion(request, 'bd.puede_eliminar_dia_no_laborable')
                if not 'id' in request.POST or not request.POST['id']:
                    raise NameError(u"No se encontro registro a eliminar")
                object_id = int(request.POST['id'])
                if not DiasNoLaborable.objects.filter(pk=object_id).exists():
                    raise NameError(u"No se encontro registro a eliminar")
                objectDelete = eDiasNoLaborable = DiasNoLaborable.objects.get(pk=object_id)
                objectDelete.delete()
                log(u'Elimino día no laborable: %s' % eDiasNoLaborable, request, "del")
                return JsonResponse({"result": "ok", "mensaje": u"Se elimino correctamente día no laborable"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar día no laborable. %s" % ex.__str__()})

        elif action == 'addCoordinacion':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_dia_no_laborable')
                f = DiasNoLaborableCoordinacionForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if not 'id' in request.POST:
                    raise NameError(u"Parametro no encontrado")
                id = request.POST['id']
                if not DiasNoLaborable.objects.values("id").filter(pk=id).exists():
                    raise NameError(u"Día no laborable no encontrado")
                eDiasNoLaborable = DiasNoLaborable.objects.get(pk=id)
                eDiasNoLaborableCoordinacion = DiasNoLaborableCoordinacion(dianolaborable=eDiasNoLaborable,
                                                                           coordinacion=f.cleaned_data['coordinacion'],
                                                                           activo=f.cleaned_data['activo'],
                                                                           valida_carrera=f.cleaned_data['valida_carrera']
                                                                           )
                eDiasNoLaborableCoordinacion.save(request)
                log(u'Adiciono coordinacion a día no laborable: %s' % eDiasNoLaborableCoordinacion, request, "add")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'editCoordinacion':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_dia_no_laborable')
                f = DiasNoLaborableCoordinacionForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if not DiasNoLaborableCoordinacion.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Coordinación del día no laborable no encontrado")
                eDiasNoLaborableCoordinacion = DiasNoLaborableCoordinacion.objects.get(pk=request.POST['id'])
                eDiasNoLaborableCoordinacion.coordinacion = f.cleaned_data['coordinacion']
                eDiasNoLaborableCoordinacion.activo = f.cleaned_data['activo']
                eDiasNoLaborableCoordinacion.valida_carrera = f.cleaned_data['valida_carrera']
                eDiasNoLaborableCoordinacion.save(request)
                log(u'Edito coordinacion %s del día no laborable: %s' % (eDiasNoLaborableCoordinacion.coordinacion, eDiasNoLaborableCoordinacion.dianolaborable), request, "edit")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'addCarrera':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_dia_no_laborable')
                f = DiasNoLaborableCoordinacionCarreraForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if not 'id' in request.POST:
                    raise NameError(u"Parametro no encontrado")
                id = request.POST['id']
                if not DiasNoLaborableCoordinacion.objects.values("id").filter(pk=id).exists():
                    raise NameError(u"Día no laborable no encontrado")
                eDiasNoLaborableCoordinacion = DiasNoLaborableCoordinacion.objects.get(pk=id)
                eDiasNoLaborableCoordinacionCarrera = DiasNoLaborableCoordinacionCarrera(coordinacion=eDiasNoLaborableCoordinacion,
                                                                                         carrera=f.cleaned_data['carrera'],
                                                                                         activo=f.cleaned_data['activo'],
                                                                                         valida_nivel=f.cleaned_data['valida_nivel'],
                                                                                         )
                eDiasNoLaborableCoordinacionCarrera.save(request)
                if eDiasNoLaborableCoordinacionCarrera.valida_nivel:
                    for nivel in f.cleaned_data['niveles']:
                        eDiasNoLaborableCoordinacionCarrera.nivel.add(nivel)
                log(u'Adiciono carrera %s a la coordinacion %s del día no laborable: %s' % (eDiasNoLaborableCoordinacionCarrera.carrera, eDiasNoLaborableCoordinacionCarrera.coordinacion, eDiasNoLaborableCoordinacionCarrera.coordinacion.dianolaborable), request, "add")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'editCarrera':
            try:
                puede_realizar_accion(request, 'bd.puede_modificar_dia_no_laborable')
                f = DiasNoLaborableCoordinacionCarreraForm(request.POST)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                if not 'id' in request.POST:
                    raise NameError(u"Parametro no encontrado")
                id = request.POST['id']
                if not DiasNoLaborableCoordinacionCarrera.objects.values("id").filter(pk=id).exists():
                    raise NameError(u"Coordinación de día no laborable no encontrado")
                eDiasNoLaborableCoordinacionCarrera = DiasNoLaborableCoordinacionCarrera.objects.get(pk=id)
                eDiasNoLaborableCoordinacionCarrera.carrera = f.cleaned_data['carrera']
                eDiasNoLaborableCoordinacionCarrera.activo = f.cleaned_data['activo']
                eDiasNoLaborableCoordinacionCarrera.valida_nivel = f.cleaned_data['valida_nivel']

                eDiasNoLaborableCoordinacionCarrera.nivel.clear()
                for nivel in f.cleaned_data['niveles']:
                    eDiasNoLaborableCoordinacionCarrera.nivel.add(nivel)
                eDiasNoLaborableCoordinacionCarrera.save(request)
                log(u'Edito carrera %s a la coordinacion %s del día no laborable: %s' % (eDiasNoLaborableCoordinacionCarrera.carrera, eDiasNoLaborableCoordinacionCarrera.coordinacion, eDiasNoLaborableCoordinacionCarrera.coordinacion.dianolaborable), request, "edit")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. <br> %s" % ex.__str__()})

        elif action == 'deleteDetail':
            try:
                puede_realizar_accion(request, 'bd.puede_eliminar_dia_no_laborable')
                if not 'model' in request.POST:
                    raise NameError(u"Parametro de modelo no encontrado")
                if not 'id' in request.POST:
                    raise NameError(u"Parametro de consulta no encontrado")
                m = request.POST['model']
                object_id = request.POST['id']
                model = eval(m)
                if not model.objects.filter(pk=object_id).exists():
                    raise NameError(u"No se encontro registro a eliminar")
                eModel = objectDelete = model.objects.get(pk=object_id)
                objectDelete.delete()
                log(u'Elimino %s del día no laborable: %s' % (u'carrera de la coordinación' if m == 'carrera' else 'coordinación', eModel), request, "del")
                return JsonResponse({"result": "ok", "mensaje": u"Se elimino corractamente el registro"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos. <br> %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'loadForm':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['new', 'edit', 'view'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    f = DiasNoLaborableForm()
                    eDiasNoLaborable = None
                    id = 0
                    if typeForm in ['edit', 'view']:
                        id = int(request.GET['id']) if 'id' in request.GET and request.GET['id'] and int(request.GET['id']) != 0 else None
                        if not DiasNoLaborable.objects.filter(pk=id).exists():
                            raise NameError(u"No existe formulario a editar")
                        eDiasNoLaborable = DiasNoLaborable.objects.get(pk=id)
                        f.set_initial(eDiasNoLaborable)
                        if typeForm == 'view':
                            f.view()
                        if typeForm == 'edit':
                            puede_realizar_accion(request, 'bd.puede_modificar_dia_no_laborable')
                        data['eDiasNoLaborable'] = eDiasNoLaborable
                        f.set_version(eDiasNoLaborable.version)
                    else:
                        puede_realizar_accion(request, 'bd.puede_agregar_dia_no_laborable')
                        data['eDiasNoLaborable'] = eDiasNoLaborable
                        f.set_version(2)
                    data['form'] = f
                    data['frmName'] = "frmDiasNoLaborable"
                    data['id'] = id
                    template = get_template("adm_sistemas/non_working_day/frm.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'loadDataDayNoWorkingDetail':
                try:
                    if not 'id' in request.GET:
                        raise NameError(u"Parametro no encontrado")
                    id = request.GET['id']
                    if not DiasNoLaborable.objects.values("id").filter(pk=id).exists():
                        raise NameError(u"Día no laborable no encontrado")
                    eDiasNoLaborable = DiasNoLaborable.objects.get(pk=id)
                    data['eDiasNoLaborable'] = eDiasNoLaborable
                    return render(request, "adm_sistemas/non_working_day/detail.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/adm_sistemas/non_working_days?info={ex.__str__()}")

            elif action == 'addCoordinacion':
                try:
                    puede_realizar_accion(request, 'bd.puede_modificar_dia_no_laborable')
                    if not 'id' in request.GET:
                        raise NameError(u"Parametro no encontrado")
                    id = request.GET['id']
                    if not DiasNoLaborable.objects.values("id").filter(pk=id).exists():
                        raise NameError(u"Día no laborable no encontrado")
                    eDiasNoLaborable = DiasNoLaborable.objects.get(pk=id)
                    data['eDiasNoLaborable'] = eDiasNoLaborable
                    data['title'] = u'Adicionar coordinación al día no laborable %s' % eDiasNoLaborable.fecha.strftime("%d-%m-%Y")
                    f = DiasNoLaborableCoordinacionForm()
                    data['form'] = f
                    return render(request, "adm_sistemas/non_working_day/addcoordinacion.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/adm_sistemas/non_working_days?action=loadDataDayNoWorkingDetail&info={ex.__str__()}")

            elif action == 'editCoordinacion':
                try:
                    puede_realizar_accion(request, 'bd.puede_modificar_dia_no_laborable')
                    if not 'id' in request.GET:
                        raise NameError(u"Parametro no encontrado")
                    id = request.GET['id']
                    if not DiasNoLaborableCoordinacion.objects.values("id").filter(pk=id).exists():
                        raise NameError(u"Coordinación del día no laborable no encontrado")
                    data['eDiasNoLaborableCoordinacion'] = eDiasNoLaborableCoordinacion = DiasNoLaborableCoordinacion.objects.get(pk=id)
                    data['title'] = u'Edito coordinación %s del día no laborable %s' % (eDiasNoLaborableCoordinacion.coordinacion, eDiasNoLaborableCoordinacion.dianolaborable.fecha.strftime("%d-%m-%Y"))
                    f = DiasNoLaborableCoordinacionForm()
                    f.set_initial(eDiasNoLaborableCoordinacion)
                    data['form'] = f
                    return render(request, "adm_sistemas/non_working_day/editcoordinacion.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/adm_sistemas/non_working_days?action=loadDataDayNoWorkingDetail&info={ex.__str__()}")

            elif action == 'addCarrera':
                try:
                    puede_realizar_accion(request, 'bd.puede_modificar_dia_no_laborable')
                    if not 'id' in request.GET:
                        raise NameError(u"Parametro no encontrado")
                    id = request.GET['id']
                    if not DiasNoLaborableCoordinacion.objects.values("id").filter(pk=id).exists():
                        raise NameError(u"Coordinación del día no laborable no encontrado")
                    data['eDiasNoLaborableCoordinacion'] = eDiasNoLaborableCoordinacion = DiasNoLaborableCoordinacion.objects.get(pk=id)
                    data['title'] = u'Adicionar carrera de la coordinación %s al día no laborable %s' % (eDiasNoLaborableCoordinacion.coordinacion, eDiasNoLaborableCoordinacion.dianolaborable.fecha.strftime("%d-%m-%Y"))
                    f = DiasNoLaborableCoordinacionCarreraForm()
                    f.set_carrera(eDiasNoLaborableCoordinacion.coordinacion)
                    data['form'] = f
                    return render(request, "adm_sistemas/non_working_day/addcarrera.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/adm_sistemas/non_working_days?action=loadDataDayNoWorkingDetail&info={ex.__str__()}")

            elif action == 'editCarrera':
                try:
                    puede_realizar_accion(request, 'bd.puede_modificar_dia_no_laborable')
                    if not 'id' in request.GET:
                        raise NameError(u"Parametro no encontrado")
                    id = request.GET['id']
                    if not DiasNoLaborableCoordinacionCarrera.objects.values("id").filter(pk=id).exists():
                        raise NameError(u"Carrera del día no laborable no encontrado")
                    data['eDiasNoLaborableCoordinacionCarrera'] = eDiasNoLaborableCoordinacionCarrera = DiasNoLaborableCoordinacionCarrera.objects.get(pk=id)
                    data['title'] = u'Editar carrera %s de la coordinación %s al día no laborable %s' % (eDiasNoLaborableCoordinacionCarrera.carrera.nombre, eDiasNoLaborableCoordinacionCarrera.coordinacion.coordinacion.nombre, eDiasNoLaborableCoordinacionCarrera.coordinacion.dianolaborable.fecha.strftime("%d-%m-%Y"))
                    f = DiasNoLaborableCoordinacionCarreraForm()
                    f.set_initial(eDiasNoLaborableCoordinacionCarrera)
                    f.set_carrera(eDiasNoLaborableCoordinacionCarrera.coordinacion.coordinacion)
                    data['form'] = f
                    return render(request, "adm_sistemas/non_working_day/editcarrera.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/adm_sistemas/non_working_days?action=loadDataDayNoWorkingDetail&info={ex.__str__()}")

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Administración de días no laborables'
                data['ePeriodos'] = Periodo.objects.filter(status=True)
                data['eCoordinaciones'] = Coordinacion.objects.filter(status=True)
                data['eCarreras'] = Carrera.objects.filter(status=True)
                data['eNivelesMalla'] = NivelMalla.objects.filter(status=True)
                data['eTipos'] = TYPE_DAYS_NO_WORKING
                idp = 0
                if 'idp' in request.GET:
                    idp = int(request.GET['idp'])
                data['idp'] = idp
                return render(request, "adm_sistemas/non_working_day/view.html", data)
            except Exception as ex:
                pass
