# -*- coding: latin-1 -*-
from django.template import Context
from django.template.loader import get_template
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from posgrado.forms import AdmiPeriodoForm
from settings import MATRICULACION_LIBRE, VERIFICAR_CONFLICTO_DOCENTE
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import ClaseForm, AulaForm, ClaseTodosturnosForm, ClaseHorarioForm
from sga.funciones import log, variable_valor
from sga.models import Sede, Carrera, Nivel, Turno, Clase, Materia, NivelMalla, Malla, Aula, Profesor, ProfesorMateria, \
    ClaseAsincronica, DIAS_CHOICES, Bloque, Sesion, HorarioExamenDetalle
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    periodo = request.session['periodo']
    hoy=datetime.now().date()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'loadDataEvent':
            try:
                aData = {}
                print(request.POST)
                desde = request.POST['desde']
                hasta = request.POST['hasta']
                aula_id = int(encrypt(request.POST['aula_id']))
                eHorariosDetalles = HorarioExamenDetalle.objects.filter(aula_id=aula_id, horarioexamen__fecha__range=[desde, hasta])
                events = [{
                    'id': eHorariosDetalle.id,
                    'date_exam': eHorariosDetalle.horarioexamen.fecha.strftime('%Y-%m-%d'),
                    'materia': eHorariosDetalle.horarioexamen.materia.asignaturamalla.asignatura.nombre,
                    'teacher': eHorariosDetalle.profesormateria.profesor.__str__(),
                    'model_eval': eHorariosDetalle.horarioexamen.detallemodelo.nombre,
                    'type_teacher': eHorariosDetalle.profesormateria.tipoprofesor.__str__(),
                    "title": eHorariosDetalle.horarioexamen.__str__(),
                    "datestart": f'{eHorariosDetalle.horarioexamen.fecha.strftime("%Y-%m-%d")}T{eHorariosDetalle.horainicio.strftime("%H:%M:%S")}',
                    "start": f'{eHorariosDetalle.horarioexamen.fecha.strftime("%Y-%m-%d")}T{eHorariosDetalle.horainicio.strftime("%H:%M:%S")}',
                    "end": f'{eHorariosDetalle.horarioexamen.fecha.strftime("%Y-%m-%d")}T{eHorariosDetalle.horafin.strftime("%H:%M:%S")}',
                    "dateend": f'{eHorariosDetalle.horarioexamen.fecha.strftime("%Y-%m-%d")}T{eHorariosDetalle.horafin.strftime("%H:%M:%S")}',
                }for eHorariosDetalle in eHorariosDetalles]
                print(events)
                aData['events'] = events
                aData['desde'] = desde
                aData['hasta'] = hasta
                return JsonResponse({"result": "ok", "aData": aData, 'desde': desde, 'hasta': hasta})
            except Exception as e:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'mostrar':
                try:
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            return HttpResponseRedirect(request.path)
        else:

            try:
                data['title'] = u'Administración de horarios de clases del periodo'
                data['bloques'] = bloques = Bloque.objects.filter(status=True, tipo=1).order_by('pk')
                data['aulas_sin_bloques'] = aulas = Aula.objects.filter(status=True, bloque_id__isnull=True ).order_by('pk')

                return render(request, "adm_horarios/examenes_bloques/view.html", data)

            except Exception as ex:
                data['msg_error'] = ex.__str__()
                return render(request, "adm_horarios/error.html", data)

