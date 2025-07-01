# -*- coding: UTF-8 -*-
import json
from django.contrib.auth.decorators import login_required
from django.forms import model_to_dict
from django.template.loader import get_template
from feria.forms import CronogramaForm
from feria.models import CronogramaFeria
from sga.commonviews import adduserdata
from sga.funciones import puede_realizar_accion, log
from decorators import secure_module, last_access
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from sga.models import Carrera
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'loadDataTable':
            try:
                txt_filter = request.POST['sSearch'] if request.POST['sSearch'] else ''
                limit = int(request.POST['iDisplayLength']) if request.POST['iDisplayLength'] else 25
                offset = int(request.POST['iDisplayStart']) if request.POST['iDisplayStart'] else 0
                tCount = 0
                cronogramas = CronogramaFeria.objects.filter()
                if txt_filter:
                    search = txt_filter.strip()
                    cronogramas = cronogramas.filter(Q(objetivo__icontains=search))
                tCount = cronogramas.count()
                if offset == 0:
                    rows = cronogramas[offset:limit]
                else:
                    rows = cronogramas[offset:offset + limit]
                aaData = []
                for row in rows:
                    aaCarreras = [
                        {
                           "id": aCarrera.id,
                           "name": aCarrera.nombre,
                           "code": aCarrera.codigo,
                        }
                        for aCarrera in row.carreras.filter(status=True)
                    ]

                    aaData.append([#row.id,
                                   row.objetivo,
                                   aaCarreras,
                                   {"id": row.id,
                                    "id_enc": encrypt(row.id),
                                    "name": row.objetivo,
                                    "fechainicio": row.fechainicio,
                                    "fechafin": row.fechafin,
                                    "fechainicioinscripcion": row.fechainicioinscripcion,
                                    "fechafininscripcion": row.fechafininscripcion,
                                    "numero_solicitudes": row.numero_solicitudes()
                                    },
                                   ])
                return JsonResponse({"result": "ok", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__(), "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        if action == 'saveCronograma':
            try:
                id = int(encrypt(request.POST['id'])) if 'id' in request.POST and request.POST['id'] and int(encrypt(request.POST['id'])) != 0 else None
                typeForm = 'edit' if id else 'new'
                f = CronogramaForm(request.POST)
                if not f.is_valid():
                    raise NameError(u"Debe ingresar la información en todos los campos")
                if typeForm == 'new':
                    # puede_realizar_accion(request, 'bd.puede_agregar_grupo')
                    # if Crono.objects.filter(name=f.cleaned_data['name']).exists():
                    #     raise NameError(u"Nombre debe ser único")
                    eCronograma = CronogramaFeria(
                        objetivo=f.cleaned_data['objetivo'],
                        fechainicio=f.cleaned_data['fechainicio'],
                        fechafin=f.cleaned_data['fechafin'],
                        fechainicioinscripcion=f.cleaned_data['fechainicioinscripcion'],
                        fechafininscripcion=f.cleaned_data['fechafininscripcion'],
                        minparticipantes=f.cleaned_data['minparticipantes'],
                        maxparticipantes=f.cleaned_data['maxparticipantes'],
                                            )
                    eCronograma.save(request)
                    log(u'Aciciono cronograma: %s' % eCronograma, request, "add")
                    if 'carreras' in request.POST:
                        carreras = json.loads(request.POST['carreras'])
                        for carrera in carreras:
                            eCronograma.carreras.add(carrera)
                            log(u'Adiciono carrera: %s' % carrera, request, "add")
                else:
                    # puede_realizar_accion(request, 'bd.puede_modificar_grupo')
                    if not CronogramaFeria.objects.filter(pk=id).exists():
                        raise NameError(u"No existe formulario a editar")
                    # if Group.objects.filter(name=f.cleaned_data['name']).exclude(pk=id).exists():
                    #     raise NameError(u"Nombre debe ser único")
                    eCronograma = CronogramaFeria.objects.get(pk=id)
                    eCronograma.objetivo = f.cleaned_data['objetivo']
                    eCronograma.fechainicio = f.cleaned_data['fechainicio']
                    eCronograma.fechafin = f.cleaned_data['fechafin']
                    eCronograma.fechainicioinscripcion = f.cleaned_data['fechainicioinscripcion']
                    eCronograma.fechafininscripcion = f.cleaned_data['fechafininscripcion']
                    eCronograma.minparticipantes = f.cleaned_data['minparticipantes']
                    eCronograma.maxparticipantes = f.cleaned_data['maxparticipantes']
                    eCronograma.save(request)
                    log(u'Edito cronograma: %s' % eCronograma, request, "edit")
                    if 'carreras' in request.POST:
                        carreras = json.loads(request.POST['carreras'])
                        carrera_aux = eCronograma.carreras.all()
                        for c in carrera_aux:
                            if not c.id in carreras:
                                eCronograma.carreras.remove(c)
                        for c in Carrera.objects.filter(pk__in=carreras):
                            eCronograma.carreras.add(c)
                            log(u'Adiciono carrera cronograma: %s carrera: %s' % (eCronograma, c), request, "edit")
                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente el cronograma"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar el cronograma. %s" % ex.__str__()})

        if action == 'deleteCronograma':
            try:
                #puede_realizar_accion(request, 'bd.puede_eliminar_grupo')
                if not 'id' in request.POST or not request.POST['id']:
                    raise NameError(u"No se encontro registro a eliminar")
                object_id = int(request.POST['id'])
                if not CronogramaFeria.objects.filter(pk=object_id).exists():
                    raise NameError(u"No se encontro registro a eliminar")
                eCronograma = CronogramaFeria.objects.get(pk=object_id)
                eCronograma.status = True
                eCronograma.save(request)
                log(u'Elimino cronograma: %s' % eCronograma, request, "del")
                return JsonResponse({"result": "ok", "mensaje": u"Se elimino correctamente el grupo"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el grupo. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'loadFormCronograma':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['new', 'edit', 'view'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    f = CronogramaForm()
                    eCronograma = None
                    id = 0
                    if typeForm in ['edit', 'view']:
                        id = int(encrypt(request.GET['id'])) if 'id' in request.GET and encrypt(request.GET['id']) and int(encrypt(request.GET['id'])) != 0 else None
                        if not CronogramaFeria.objects.filter(pk=id).exists():
                            raise NameError(u"No existe formulario a editar")
                        eCronograma = CronogramaFeria.objects.get(pk=id)
                        f.initial = model_to_dict(eCronograma)
                        if typeForm == 'view':
                            f.view()
                        if typeForm == 'edit':
                            puede_realizar_accion(request, 'feria.puede_modificar_cronogramaferia')
                        data['eCarreras'] = eCronograma.carreras.all()
                        data['eCronograma'] = eCronograma
                    else:
                        pass
                        puede_realizar_accion(request, 'feria.puede_agregar_cronogramaferia')
                    data['form'] = f
                    data['frmName'] = "frmCronograma"
                    data['typeForm'] = typeForm
                    data['id'] = encrypt(id)
                    template = get_template("adm_feria/cronograma/frm.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'loadCarreras':
                try:
                    eCarreras = Carrera.objects.filter(coordinacion__id__in=[1, 2, 3, 4, 5], status=True)
                    if 'carreras' in request.GET:
                        carreras = json.loads(request.GET['carreras'])
                        eCarreras = eCarreras.exclude(pk__in=carreras)
                    data['carreras'] = eCarreras
                    template = get_template("adm_feria/cronograma/carreras.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
        else:
            try:
                data['title'] = u'Administración de Ferias'
                return render(request, "adm_feria/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect("/")