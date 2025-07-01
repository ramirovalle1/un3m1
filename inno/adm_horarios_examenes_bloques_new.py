# -*- coding: latin-1 -*-
import json

from django.forms import model_to_dict
from django.forms.models import model_to_dict
from django.template import Context
from django.template.loader import get_template
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, F, Sum
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from inno.forms import HorarioExamenForm
from posgrado.forms import AdmiPeriodoForm
from settings import MATRICULACION_LIBRE, VERIFICAR_CONFLICTO_DOCENTE
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import ClaseForm, AulaForm, ClaseTodosturnosForm, ClaseHorarioForm
from sga.funciones import log, variable_valor, null_to_numeric, puede_realizar_accion, convertir_fecha_invertida
from sga.models import Sede, Carrera, Nivel, Turno, Clase, Materia, NivelMalla, Malla, Aula, Profesor, ProfesorMateria, \
    ClaseAsincronica, DIAS_CHOICES, Bloque, Sesion, HorarioExamenDetalle, MateriaAsignada, Coordinacion, Paralelo, Administrativo, DetalleModeloEvaluativo, HorarioExamen, HorarioExamenDetalleAlumno
from sga.templatetags.sga_extras import encrypt
from inno.serializers.HorarioExamenBloque import BloqueSerializer, AulaSerializer, HorarioExamenDetalleSerializer, \
    SesionSerializer, MallaSerializer, NivelMallaSerializer, ParaleloSerializer, MateriaSerializer, \
    ProfesorMateriaSerializer, ProfesorSerializer, AdministrativoSerializer, MateriaFilterSerializer


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
                    "title": eHorariosDetalle.horarioexamen.__str__(),
                    "start": f'{eHorariosDetalle.horarioexamen.fecha.strftime("%Y-%m-%d")}T{eHorariosDetalle.horainicio.strftime("%H:%S:%M")}',
                    "end": f'{eHorariosDetalle.horarioexamen.fecha.strftime("%Y-%m-%d")}T{eHorariosDetalle.horafin.strftime("%H:%S:%M")}',
                }for eHorariosDetalle in eHorariosDetalles]
                aData['events'] = events
                aData['desde'] = desde
                aData['hasta'] = hasta
                return JsonResponse({"result": "ok", "aData": aData, 'desde': desde, 'hasta': hasta})
            except Exception as e:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'loadDataClassroomSchedule':
            try:
                aData = {}
                print(request.POST)
                if not 'bloque_id' in request.POST:
                    raise NameError('No se envio el parametro fecha')
                desde = datetime.strptime(request.POST['desde'], '%Y-%m-%d')
                hasta = datetime.strptime(request.POST['hasta'], '%Y-%m-%d')

                if desde.isocalendar().week != hasta.isocalendar().week:
                    raise NameError('Debe ingresar fecha  de la misma semana')

                aDates = []
                tFrom  = desde
                while(tFrom <= hasta):
                    aDates.append(tFrom)
                    tFrom = tFrom + timedelta(days=1)

                aula_id = int(encrypt(request.POST['aula_id'])) if request.POST['aula_id'] != 'all' else 0
                #aula_id = request.POST['aula_id']
                bloque_id = int(encrypt(request.POST['bloque_id']))

                eBlock = Bloque.objects.filter(pk=bloque_id).first()
                if eBlock is None:
                    raise NameError('No existe el bloque')
                if aula_id:
                    eClassrooms = Aula.objects.filter(pk=aula_id)
                else:
                    eClassrooms = eBlock.aulas()
                eTurns = []
                eWeekDays = [
                    {'id': 1, 'name': 'LUNES'},
                    {'id': 2, 'name': 'MARTES'},
                    {'id': 3, 'name': 'MIERCOLES'},
                    {'id': 4, 'name': 'JUEVES'},
                    {'id': 5, 'name': 'VIERNES'},
                    {'id': 6, 'name': 'SABADO'},
                    {'id': 7, 'name': 'DOMINGO'},
                ]
                for i, eDay in enumerate(eWeekDays):
                    for aDate in aDates:
                        if aDate.isoweekday() == eDay['id']:
                            eDay['date'] = aDate.strftime('%Y-%m-%d')
                            eWeekDays[i] = eDay
                            aDates.remove(aDate)
                            break
                horainicio = datetime(2022, 7, 29, 7, 0, 0)
                for ind in range(10):
                    horafin = horainicio + timedelta(minutes=89)
                    eTurns.append(
                        {
                            'id': ind,
                            'start': horainicio.strftime('%H:%M:%S %p'),
                            'end': horafin.strftime('%H:%M:%S %p'),
                        }
                    )
                    horainicio = horafin + timedelta(minutes=1)
                print(eTurns)

                eClassroomSchedules = []
                for eClassroom in eClassrooms:
                    eSchedules = HorarioExamenDetalle.objects.filter(aula_id=eClassroom.id, horarioexamen__fecha__range=[desde, hasta])
                    dClassroom = {
                        'id': eClassroom.id,
                        'name': eClassroom.nombre,
                        'type_classroom': eClassroom.tipo.__str__(),
                        'capacity': eClassroom.capacidad,
                        'eSchedules': {}
                    }
                    for eTurn in eTurns:
                        for eWeekDay in eWeekDays:
                            eSchedulesDetails = eSchedules.filter(horainicio=datetime.strptime(eTurn['start'], '%H:%M:%S %p'),
                                                                  horafin=datetime.strptime(eTurn['end'], '%H:%M:%S %p')
                                                                  ).annotate(dia_semana=F('horarioexamen__fecha__iso_week_day')).order_by('dia_semana').filter(dia_semana=eWeekDay['id'])
                            #dClassroom['eSchedules'][f"turn{eTurn['id']}_weekday{eWeekDay['id']}"] = HorarioExamenDetalleSerializer(eSchedulesDetails, many=True).data if eSchedulesDetails.values('id').exists() else []
                            dClassroom['eSchedules'][f"turn{eTurn['id']}_weekday{eWeekDay['id']}"] = {}

                            dClassroom['eSchedules'][f"turn{eTurn['id']}_weekday{eWeekDay['id']}"]["data"] = [
                            {
                                'id': eScheduleDetail.id,
                                'date': eScheduleDetail.horarioexamen.fecha.strftime('%Y-%m-%d'),
                                'teacher': eScheduleDetail.profesormateria.profesor.__str__() if eScheduleDetail.profesormateria is not None else 'Sin Profesor',
                                'model_eval': eScheduleDetail.horarioexamen.detallemodelo.nombre,
                                'type_teacher': eScheduleDetail.profesormateria.tipoprofesor.__str__(),
                                'university_career': eScheduleDetail.horarioexamen.materia.asignaturamalla.malla.carrera.__str__(),
                                'mesh_level': eScheduleDetail.horarioexamen.materia.asignaturamalla.nivelmalla.__str__(),
                                'parallel': eScheduleDetail.horarioexamen.materia.paralelomateria.__str__(),
                                'number_students': null_to_numeric(len(MateriaAsignada.objects.filter(status=True, materia=eScheduleDetail.horarioexamen.materia))),
                                'number_students_examen': eScheduleDetail.cantalumnos,
                                'name': f"{eScheduleDetail.horarioexamen.materia.asignaturamalla.asignatura.nombre}",
                            }for eScheduleDetail in eSchedulesDetails]
                            dClassroom['eSchedules'][f"turn{eTurn['id']}_weekday{eWeekDay['id']}"]['info'] = {
                                'id': eSchedulesDetails.first().id if eSchedulesDetails.first() is not None else '',
                                'classroom_id': eClassroom.id,
                                'classroom_name': eClassroom.nombre,
                                'weekday': eWeekDay,
                                'turn': eTurn,
                            }
                    eClassroomSchedules.append(dClassroom)
                print(eClassroomSchedules)
                aData['eClassroomSchedules'] = eClassroomSchedules
                aData['eWeekDays'] = eWeekDays
                aData['eTurns'] = eTurns
                aData['desde'] = request.POST['desde']
                aData['hasta'] = request.POST['hasta']
                return JsonResponse({"result": "ok", "aData": aData})
            except Exception as e:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error. %s" % str(e)})

        if action == 'loadDataClassrooms':
            try:
                aData = {}
                print(request.POST)
                bloque_id = int(encrypt(request.POST['bloque_id']))
                eBlock = Bloque.objects.filter(pk=bloque_id).first()
                aData['eClassroms'] = []
                if eBlock is not None:
                    eClassrooms = eBlock.aulas()
                    aData['eClassroms'] = AulaSerializer(eClassrooms, many=True).data if eClassrooms.values('id').exists() else []
                return JsonResponse({"result": "ok", "aData": aData})
            except Exception as e:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'loadListcoordinationSesions':
           try:
               if not 'idc' in request.POST:
                   raise NameError('Coordinación no encontrada')
               aData = {}
               eCoordinacion = Coordinacion.objects.get(pk=request.POST['idc'])
               eSesiones = eCoordinacion.secciones_por_periodo(periodo).distinct()
               aData['eSesiones'] = []
               if eSesiones.values('id').exists():
                   aData['eSesiones'] = SesionSerializer(eSesiones, many=True).data
               return JsonResponse({"result": "ok", "aData": aData})
           except Exception as ex:
               return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})


        if action == 'loadListSesionCareers':
           try:
               if not 'id' in request.POST:
                   raise NameError('Sesion no encontrada')
               aData = {}
               eSesion = Sesion.objects.get(pk=request.POST['id'])
               eNiveles = Nivel.objects.filter(status=True, periodo=periodo, sesion_id=eSesion.id,  nivellibrecoordinacion__coordinacion_id=request.POST['idc'])
               eMaterias = Materia.objects.filter(nivel_id__in=eNiveles.values_list('pk', flat=True).distinct(), status=True)
               eMallas = Malla.objects.filter(pk__in=eMaterias.values_list('asignaturamalla__malla_id').distinct()).distinct()
               aData['eMallas'] = []
               if eMallas.values('id').exists():
                   data_json = {
                       'periodo_id': periodo.id,
                       'sesion_id': request.POST['id'],
                       'coordinacion_id': request.POST['idc'],
                   }
                   aData['eMallas'] = MallaSerializer(eMallas, context=data_json, many=True).data
               return JsonResponse({"result": "ok", "aData": aData})
           except Exception as ex:
               return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        if action == 'loadListCareerLebels':
           try:
               if not 'id' in request.POST:
                   raise NameError('Carrera no encontrada')
               aData = {}
               eMalla = Malla.objects.get(pk=request.POST['id'])
               eMaterias = Materia.objects.filter(asignaturamalla__malla_id=eMalla.id, status=True)
               eNivelesMallas = NivelMalla.objects.filter(pk__in=eMaterias.values_list('asignaturamalla__nivelmalla_id').distinct()).distinct()
               aData['eNivelesMallas'] = []
               if eNivelesMallas.values('id').exists():
                   data_json = {
                       'periodo_id': periodo.id,
                       'malla_id': eMalla.id,
                       'sesion_id': request.POST['ids'],
                       'coordinacion_id': request.POST['idc'],
                   }
                   aData['eNivelesMallas'] = NivelMallaSerializer(eNivelesMallas, context=data_json, many=True).data
               return JsonResponse({"result": "ok", "aData": aData})
           except Exception as ex:
               return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        if action == 'loadListCareerLebelParallels':
           try:
               if not 'idm' in request.POST:
                   raise NameError('Carrera no encontrada')
               if not 'id' in request.POST:
                   raise NameError('Nivel no encontrada')
               aData = {}
               eMalla = Malla.objects.get(pk=request.POST['idm'])
               eNivelMalla = NivelMalla.objects.get(pk=request.POST['id'])
               eMaterias = Materia.objects.filter(asignaturamalla__malla_id=eMalla.id, asignaturamalla__nivelmalla_id=eNivelMalla.id, status=True,)
               eParalelos = Paralelo.objects.filter(pk__in=eMaterias.values_list('paralelomateria_id').distinct()).distinct()
               aData['eParalelos'] = []
               if eParalelos.values('id').exists():
                   data_json = {
                       'periodo_id': periodo.id,
                       'malla_id': eMalla.id,
                       'sesion_id': request.POST['ids'],
                       'coordinacion_id': request.POST['idc'],
                       'nivelmalla_id': eNivelMalla.id,
                   }
                   aData['eParalelos'] = ParaleloSerializer(eParalelos, context=data_json, many=True).data
               return JsonResponse({"result": "ok", "aData": aData})
           except Exception as ex:
               return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        if action == 'loadListParallelSubjects':
           try:
               if not 'idm' in request.POST:
                   raise NameError('Carrera no encontrada')
               if not 'id' in request.POST:
                   raise NameError('Nivel no encontrada')
               aData = {}
               print(request)
               eMalla = Malla.objects.get(pk=request.POST['idm'])
               eParalelo = Paralelo.objects.get(pk=request.POST['id'])
               eNivelMalla = NivelMalla.objects.get(pk=request.POST['idn'])
               eMaterias = Materia.objects.filter(asignaturamalla__malla_id=eMalla.id, asignaturamalla__nivelmalla_id=eNivelMalla.id, paralelomateria_id=eParalelo.id, status=True,)
               aData['eMaterias'] = []
               if eMaterias.values('id').exists():
                   data_json = {
                       'periodo_id': periodo.id,
                       'malla_id': eMalla.id,
                       'sesion_id': request.POST['ids'],
                       'coordinacion_id': request.POST['idc'],
                       'nivelmalla_id': eNivelMalla.id,
                       'paralelo_id': eParalelo.id,
                   }
                   aData['eMaterias'] = MateriaFilterSerializer(eMaterias, context=data_json, many=True).data
               return JsonResponse({"result": "ok", "aData": aData})
           except Exception as ex:
               return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        if action == 'loadListResponsableHorarioExamen':
            try:
                aData= {}
                if not 'tiporesponsable' in request.POST:
                    raise NameError('Tipo de responsable no encontrado')
                if not 'idm' in request.POST:
                    raise NameError('Materia no encontrada')
                eMateria = Materia.objects.get(pk=int(request.POST['idm']))
                tiporesponsable = int(request.POST['tiporesponsable'])
                if tiporesponsable == 0:
                    aData['eResponsables'] = []
                elif tiporesponsable == 1:
                    eProfesores = eMateria.profesores_materia()
                    aData['eResponsables'] = ProfesorMateriaSerializer(eProfesores, many=True).data if eProfesores.values("id").exists() else []
                elif tiporesponsable == 2:
                    eProfesorMaterias = ProfesorMateria.objects.filter(activo=True, status=True, materia__nivel__periodo=eMateria.nivel.periodo)
                    eProfesores = Profesor.objects.filter(pk__in=eProfesorMaterias.values_list('profesor_id', flat=True))
                    aData['eResponsables'] = ProfesorSerializer(eProfesores, many=True).data if eProfesores.values("id").exists() else []
                elif tiporesponsable == 3:
                    eAdministrativos = Administrativo.objects.filter(status=True, activo=True)
                    aData['eResponsables'] = AdministrativoSerializer(eAdministrativos, many=True).data if eAdministrativos.values("id").exists() else []
                return JsonResponse({"result": "ok", "aData": aData})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        elif action == 'saveSchedule':
            try:
                id = int(encrypt(request.POST['id'])) if 'id' in request.POST and request.POST['id'] and int(encrypt(request.POST['id'])) != 0 else None
                typeForm = 'edit' if id else 'new'
                f = HorarioExamenForm(request.POST)
                aData = {}
                if not f.is_valid():
                    raise NameError(u"Debe ingresar la información en todos los campos")

                fecha = datetime.strptime(f.cleaned_data['fecha'], '%Y-%m-%d')
                horainicio = datetime.strptime(f.cleaned_data['horainicio'], '%H:%M:%S %p')
                horafin = datetime.strptime(f.cleaned_data['horafin'], '%H:%M:%S %p')
                tiporesponsable = int(f.cleaned_data['tiporesponsable'])
                cantidad = f.cleaned_data['cantalumnos']
                eAula = Aula.objects.get(pk=int(request.POST['aula_id']))
                eMateria = Materia.objects.get(pk=f.cleaned_data['materia'])
                eMalla = eMateria.asignaturamalla.malla
                eNivelMalla = eMateria.asignaturamalla.nivelmalla
                eParalelo = eMateria.paralelomateria
                eProfesorMateria = None
                eProfesor = None
                eAdministrativo = None
                if tiporesponsable == 1:
                    eProfesorMateria = ProfesorMateria.objects.get(pk=int(request.POST['responsable']))#encrypt(request.POST['responsable'])
                elif tiporesponsable == 2:
                    eProfesor = Profesor.objects.get(pk=int(request.POST['responsable']))
                elif tiporesponsable == 3:
                    eAdministrativo = Administrativo.objects.get(pk=int(request.POST['responsable']))
                eMateria.actualizarhtml = True
                eMateria.save()
                eDetalleModeloEvaluativo = f.cleaned_data['modelo']
                VALIDAR_CONFLICTO_HORARIO = int(request.POST['validahorario']) == 1 if True else False

                if VALIDAR_CONFLICTO_HORARIO:
                    if horainicio > horafin:
                        raise NameError(u"Hora de comienzo no puede ser mayo a la hora de culmnación")
                    if cantidad > eAula.capacidad:
                        raise NameError(u"Capacidad el aula no permitida")
                    diferencia = timedelta(hours=horafin.hour, minutes=horafin.minute) - timedelta(hours=horainicio.hour, minutes=horainicio.minute)
                    if eMateria.nivel.modalidad.id in [1, 2] and not eMateria.nivel.coordinacion().pk == 1:
                        tiempo = timedelta(hours=1, minutes=29)
                        if tiempo != diferencia:
                            raise NameError(u"El tiempo debe ser de una hora y treinta minutos")
                    elif eMateria.nivel.modalidad.id == 3 and not eMateria.nivel.coordinacion().pk == 1:
                        tiempo = timedelta(hours=1, minutes=59)
                        if tiempo != diferencia:
                            raise NameError(u"El tiempo debe ser de dos horas")
                    else:
                        tiempo = timedelta(hours=1, minutes=29)
                        if tiempo != diferencia:
                            raise NameError(u"El tiempo debe ser de una hora y media")

                eHorarioExamenDetalles = HorarioExamenDetalle.objects.filter(horarioexamen__materia=eMateria,
                                                                             horarioexamen__detallemodelo=eDetalleModeloEvaluativo,
                                                                             status=True)
                eHorarioExamenDetalle = None
                if typeForm == 'new':
                    if VALIDAR_CONFLICTO_HORARIO:
                        if eAula.id != 218:
                            if HorarioExamenDetalle.objects.values("id").filter(Q(horainicio__lte=horainicio, horafin__gte=horafin), horarioexamen__fecha=fecha, status=True, aula=eAula, validahorario=True).exists():
                                raise NameError(u"Horario ocupado para el aula")
                        if eProfesorMateria:
                            if HorarioExamenDetalle.objects.values("id").filter(Q(horainicio__lte=horainicio, horafin__gte=horafin), horarioexamen__fecha=fecha, status=True, profesormateria=eProfesorMateria, validahorario=True).exists():
                                raise NameError(u"Horario ocupado para la materia")
                        if eProfesor:
                            if HorarioExamenDetalle.objects.values("id").filter(Q(horainicio__lte=horainicio, horafin__gte=horafin), horarioexamen__fecha=fecha, status=True, profesor=eProfesor, validahorario=True).exists():
                                raise NameError(u"Horario ocupado para la materia")
                        if eAdministrativo:
                            if HorarioExamenDetalle.objects.values("id").filter(Q(horainicio__lte=horainicio, horafin__gte=horafin), horarioexamen__fecha=fecha, status=True, administrativo=eAdministrativo, validahorario=True).exists():
                                raise NameError(u"Horario ocupado para la materia")
                        if eHorarioExamenDetalles.values("id").filter(Q(horainicio__lte=horainicio, horafin__gte=horafin), horarioexamen__fecha=fecha, validahorario=True).exists():
                            raise NameError(u"Horario ocupado para la materia")
                        totalPlanificados = int(eHorarioExamenDetalles.aggregate(total=Sum('cantalumnos'))['total']) if eHorarioExamenDetalles.values("id").exists() else 0
                        totalPlanificados = totalPlanificados + cantidad
                        if totalPlanificados > eMateria.cantidad_alumnos():
                            raise NameError(u"Cantidad de alumnos planificados sobrepasa la cantidad de alumnos matriculados")
                        if eProfesorMateria:
                            eHorarioExamenesDetalles = HorarioExamenDetalle.objects.filter(Q(horainicio__lte=horainicio, horafin__gte=horafin),
                                                                                           Q(Q(profesormateria__profesor__persona=eProfesorMateria.profesor.persona) |
                                                                                             Q(profesor__persona=eProfesorMateria.profesor.persona) |
                                                                                             Q(administrativo__persona=eProfesorMateria.profesor.persona)
                                                                                             ),
                                                                                           horarioexamen__fecha=fecha,
                                                                                           horarioexamen__detallemodelo_id=eDetalleModeloEvaluativo.id,
                                                                                           status=True)
                            if eHorarioExamenesDetalles.exists():
                                raise NameError(u"Horario de profesor responsable  ocupado")
                        if eProfesor:
                            eHorarioExamenesDetalles = HorarioExamenDetalle.objects.filter(Q(horainicio__lte=horainicio, horafin__gte=horafin),
                                                                                           Q(Q(profesormateria__profesor__persona=eProfesor.persona) |
                                                                                             Q(profesor__persona=eProfesor.persona) |
                                                                                             Q(administrativo__persona=eProfesor.persona)
                                                                                             ),
                                                                                           horarioexamen__fecha=fecha,
                                                                                           horarioexamen__detallemodelo_id=eDetalleModeloEvaluativo.id,
                                                                                           status=True)
                            if eHorarioExamenesDetalles.exists():
                                raise NameError(u"Horario de profesor responsable  ocupado")
                        if eAdministrativo:
                            eHorarioExamenesDetalles = HorarioExamenDetalle.objects.filter(Q(horainicio__lte=horainicio, horafin__gte=horafin),
                                                                                           Q(Q(profesormateria__profesor__persona=eAdministrativo.persona) |
                                                                                             Q(profesor__persona=eAdministrativo.persona) |
                                                                                             Q(administrativo__persona=eAdministrativo.persona)
                                                                                             ),
                                                                                           horarioexamen__fecha=fecha,
                                                                                           horarioexamen__detallemodelo_id=eDetalleModeloEvaluativo.id,
                                                                                           status=True)
                            if eHorarioExamenesDetalles.exists():
                                raise NameError(u"Horario de profesor responsable  ocupado")
                        eHorarioExamenesDetalles = HorarioExamenDetalle.objects.filter(Q(horainicio__lte=horainicio, horafin__gte=horafin),
                                                                                       horarioexamen__fecha=fecha,
                                                                                       horarioexamen__materia__asignaturamalla__malla_id=eMalla.id,
                                                                                       horarioexamen__materia__asignaturamalla__nivelmalla_id=eNivelMalla.id,
                                                                                       horarioexamen__detallemodelo_id=eDetalleModeloEvaluativo.id,
                                                                                       horarioexamen__materia__paralelomateria_id=eParalelo.id,
                                                                                       status=True)
                        if eHorarioExamenesDetalles.exists():
                            raise NameError(u"Conflicto de horario en paralelo")
                    eHorarioExamenes = HorarioExamen.objects.filter(materia=eMateria, fecha=fecha, detallemodelo_id=eDetalleModeloEvaluativo.id, status=True)
                    if not eHorarioExamenes.values("id").exists():
                        eHorarioExamen = HorarioExamen(materia=eMateria,
                                                       detallemodelo_id=eDetalleModeloEvaluativo.id,
                                                       fecha=fecha)
                        eHorarioExamen.save(request)
                        log(u'Adiciono Horario de examenes: %s' % eHorarioExamen, request, "add")
                    else:
                        eHorarioExamen = eHorarioExamenes.first()
                    if VALIDAR_CONFLICTO_HORARIO:
                        if not eHorarioExamen.maximo_por_hora(eHorarioExamen.fecha, horainicio, horafin, cantidad):
                            raise NameError(u"No puede ingresar mas alumnos en este rango de horas, debe crear una nueva jornada con un rango de horas o fecha diferente")
                    eHorarioExamenDetalle = HorarioExamenDetalle(horarioexamen=eHorarioExamen,
                                                                 horainicio=horainicio,
                                                                 horafin=horafin,
                                                                 aula=eAula,
                                                                 tiporesponsable=tiporesponsable,
                                                                 cantalumnos=cantidad,
                                                                 profesormateria=eProfesorMateria,
                                                                 profesor=eProfesor,
                                                                 administrativo=eAdministrativo,
                                                                 validahorario=VALIDAR_CONFLICTO_HORARIO)
                    eHorarioExamenDetalle.save(request)
                    log(u'Adiciono Detalle Horario de examenes: %s' % eHorarioExamenDetalle, request, "add")
                else:
                    pass

                eHorarios = HorarioExamenDetalle.objects.filter(horarioexamen__materia=eMateria, status=True, horarioexamen__status=True, horarioexamen__detallemodelo=eDetalleModeloEvaluativo).distinct().order_by('horainicio')
                eAlumnos = MateriaAsignada.objects.filter(status=True, retiramateria=False, materia=eMateria, matricula__retiradomatricula=False, matricula__status=True).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2', 'matricula__inscripcion__persona__nombres')
                eAsignados = HorarioExamenDetalleAlumno.objects.filter(horarioexamendetalle__in=eHorarios, status=True, materiaasignada__in=eAlumnos)
                if eAsignados.values("id").exists():
                    eAsignados.delete()
                for eHorario in eHorarios:
                    eAsignados = HorarioExamenDetalleAlumno.objects.filter(horarioexamendetalle__in=eHorarios, status=True, materiaasignada__in=eAlumnos)
                    cantidad = eHorario.cantalumnos
                    inicial = 0
                    ultimo = cantidad
                    for eAlumno in eAlumnos.exclude(pk__in=eAsignados.values_list('materiaasignada_id', flat=True))[inicial:ultimo]:
                        eHorarioExamenDetalleAlumno = HorarioExamenDetalleAlumno(materiaasignada=eAlumno,
                                                                                 horarioexamendetalle=eHorario)
                        eHorarioExamenDetalleAlumno.save(request)
                        log(u'Adiciono alumno al Horario de examenes: %s' % eHorarioExamenDetalleAlumno, request, "add")
                aData['eHorarioExamenDetalle'] = {}
                aData['indexClassroomSchedule'] = int(request.POST['indexClassroomSchedule'])
                aData['keyclassroom_vue'] = request.POST['keyclassroom_vue']
                if eHorarioExamenDetalle is not None:
                    fechastr = eHorarioExamenDetalle.horarioexamen.fecha.strftime('%Y-%m-%d')
                    aData['eHorarioExamenDetalle'] = {
                        "id": eHorarioExamenDetalle.id,
                        "date": fechastr,
                        "teacher": eHorarioExamenDetalle.profesormateria.profesor.__str__() if eHorarioExamenDetalle.profesormateria is not None else 'Sin Profesor',
                        "model_eval": eHorarioExamenDetalle.horarioexamen.detallemodelo.nombre,
                        "type_teacher": eHorarioExamenDetalle.profesormateria.tipoprofesor.__str__() if eHorarioExamenDetalle.profesormateria else 'Sin Tipo',
                        "university_career": eHorarioExamenDetalle.horarioexamen.materia.asignaturamalla.malla.carrera.__str__(),
                        "mesh_level": eHorarioExamenDetalle.horarioexamen.materia.asignaturamalla.nivelmalla.__str__(),
                        "parallel": eHorarioExamenDetalle.horarioexamen.materia.paralelomateria.__str__(),
                        "number_students":null_to_numeric(len(MateriaAsignada.objects.filter(status=True, materia=eHorarioExamenDetalle.horarioexamen.materia))),
                        "number_students_examen": eHorarioExamenDetalle.cantalumnos,
                        "name": f"{eHorarioExamenDetalle.horarioexamen.materia.asignaturamalla.asignatura.nombre}",
                    }

                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente", "aData":aData})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        elif action == 'deleteSchedule':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro el parametro del examen a eliminar")
                id = int(request.POST['id'])#int(encrypt(request.POST['id']))
                Aux_eHorarioExamenDetalle = eHorarioExamenDetalle = HorarioExamenDetalle.objects.get(pk=id)
                eHorarioExamen = eHorarioExamenDetalle.horarioexamen
                eMateria = eHorarioExamen.materia
                eDetalleModeloEvaluativo = eHorarioExamen.detallemodelo
                eHorarioExamenes = HorarioExamen.objects.filter(materia=eMateria, detallemodelo=eDetalleModeloEvaluativo)
                Aux_eHorarioExamenDetalle.delete()
                if not HorarioExamenDetalle.objects.values("id").filter(horarioexamen__in=eHorarioExamenes):
                    Aux_eHorarioExamenes = eHorarioExamenes
                    Aux_eHorarioExamenes.delete()
                    log(u'Elimino Horario de examenes: %s' % eHorarioExamenes, request, "del")
                log(u'Elimino Horario de examenes: %s' % eHorarioExamenDetalle, request, "del")
                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'loadFormSchedule':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['new', 'edit', 'view'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    f = HorarioExamenForm()
                    eHorarioExamenDetalle = None
                    id = 0
                    eAula = Aula.objects.filter(pk=int(request.GET['classroom_id'])).first()
                    if typeForm in ['edit', 'view']:
                        #id = int(encrypt(request.GET['id'])) if 'id' in request.GET and encrypt(request.GET['id']) and int(encrypt(request.GET['id'])) != 0 else None
                        id = int(request.GET['id']) if 'id' in request.GET and request.GET['id'] and int(request.GET['id']) != 0 else None
                        eHorarioExamenDetalle = HorarioExamenDetalle.objects.filter(pk=id).first()
                        if eHorarioExamenDetalle is None:
                            raise NameError(u"No existe formulario a editar")
                        eDataForm = model_to_dict(eHorarioExamenDetalle)
                        eDataForm['coordinacion'] = eHorarioExamenDetalle.horarioexamen.materia.coordinacion()
                        eDataForm['sesion'] = eHorarioExamenDetalle.horarioexamen.materia.nivel.sesion
                        eDataForm['carrera'] = eHorarioExamenDetalle.horarioexamen.materia.asignaturamalla.malla.carrera
                        eDataForm['nivel'] = eHorarioExamenDetalle.horarioexamen.materia.asignaturamalla.nivelmalla
                        eDataForm['paralelo'] = eHorarioExamenDetalle.horarioexamen.materia.paralelomateria
                        eDataForm['materia'] = eHorarioExamenDetalle.horarioexamen.materia.pk
                        eDataForm['aula'] = eHorarioExamenDetalle.aula
                        eDataForm['fecha'] = eHorarioExamenDetalle.horarioexamen.fecha
                        eDataForm['horainicio'] = eHorarioExamenDetalle.horainicio
                        eDataForm['horafin'] = eHorarioExamenDetalle.horafin
                        eDataForm['tiporesponsable'] = eHorarioExamenDetalle.tiporesponsable
                        eDataForm['responsable'] = eHorarioExamenDetalle.profesormateria.pk
                        eDataForm['modelo'] = eHorarioExamenDetalle.horarioexamen.detallemodelo
                        eDataForm['cantalumnos'] = eHorarioExamenDetalle.cantalumnos
                        eDataForm['validahorario'] = eHorarioExamenDetalle.validahorario
                        f.initial = eDataForm
                        if typeForm == 'view':
                            f.view()
                        if typeForm == 'edit':
                            pass
                            #puede_realizar_accion(request, 'feria.puede_modificar_cronogramaferia')
                        data['eHorarioExamenDetalle'] = eHorarioExamenDetalle
                        f.bloquearcampos()
                    else:
                        dataForm = {
                            'aula': eAula.__str__() if eAula is not None else 'Sin Aula',
                            'fecha': request.GET['fecha'],
                            'horainicio': request.GET['horainicio'],
                            'horafin': request.GET['horafin'],
                        }
                        f.initial = dataForm
                        f.bloquearcampos()
                        #puede_realizar_accion(request, 'feria.puede_agregar_cronogramaferia')
                    data['indexClassroomSchedule'] = request.GET['indexClassroomSchedule']
                    data['keyclassroom_vue'] = request.GET['keyclassroom_vue']
                    data['eAula'] = eAula
                    data['form'] = f
                    data['frmName'] = "frmSchedule"
                    data['typeForm'] = typeForm
                    data['id'] = encrypt(id)
                    template = get_template("adm_horarios/examenes_bloques_new/frm.html")
                    json_content = template.render(data, request)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            return HttpResponseRedirect(request.path)
        else:

            try:
                data['title'] = u'Administración de horarios de clases del periodo'
                eBloques = Bloque.objects.filter(status=True, tipo=1).order_by('pk')
                eBloques__serializer = BloqueSerializer(eBloques, many=True).data if eBloques.values('id').exists() else []
                data['eBloques'] = json.dumps(eBloques__serializer)
                # data['eBloque'] = eBloque = eBloques.first()
                # data['eAulas'] = eAulas = Aula.objects.filter(status=True, bloque_id=eBloque.id).order_by('pk')
                # data['eAula'] = eAula = eAulas.first()

                return render(request, "adm_horarios/examenes_bloques_new/view.html", data)

            except Exception as ex:
                data['msg_error'] = ex.__str__()
                return render(request, "adm_horarios/error.html", data)

