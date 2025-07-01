# -*- coding: latin-1 -*-
import json
import random
import openpyxl
from openpyxl import load_workbook
from xlwt import *
from django.forms.models import model_to_dict
from django.template import Context
from django.template.loader import get_template
import sys
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction, connections
from django.db.models import Q, F, Sum, Count
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from posgrado.forms import AdmiPeriodoForm
from settings import MATRICULACION_LIBRE, VERIFICAR_CONFLICTO_DOCENTE
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import ClaseForm, AulaForm, ClaseTodosturnosForm, ClaseHorarioForm
from sga.funciones import log, variable_valor, null_to_decimal, convertir_fecha_invertida, convertir_hora, puede_realizar_accion
from sga.models import Sede, Carrera, Nivel, Turno, Clase, Materia, NivelMalla, Malla, Aula, Profesor, \
    ProfesorMateria, ClaseAsincronica, DIAS_CHOICES, Bloque, Sesion, NivelLibreCoordinacion, Coordinacion, Paralelo, \
    DetalleModeloEvaluativo, HorarioExamenDetalle, HorarioExamen, MateriaAsignada, HorarioExamenDetalleAlumno, \
    TIPO_GRUPOS, Administrativo
from sga.templatetags.sga_extras import encrypt
from inno.serializers.HorarioExamen import CoordinacionSerializer, SesionSerializer, MallaSerializer, \
    NivelMallaSerializer, ParaleloSerializer, MateriaSerializer, AulaSerializer


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    periodo = request.session['periodo']
    hoy = datetime.now().date()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'loadDetailLevel':
            try:
                if not 'idc' in request.POST:
                    raise NameError(u"No se encontro el parametro de coordinación")
                if not 'ids' in request.POST:
                    raise NameError(u"No se encontro el parametro de sección")
                eCoordinacion = Coordinacion.objects.get(pk=encrypt(request.POST['idc']))
                eSesion = Sesion.objects.get(pk=encrypt(request.POST['ids']))
                aData = {}
                aData['eCoordinacion'] = CoordinacionSerializer(eCoordinacion).data
                aData['eSesion'] = SesionSerializer(eSesion).data
                eNiveles = Nivel.objects.filter(status=True, periodo=periodo, sesion=eSesion, nivellibrecoordinacion__coordinacion=eCoordinacion)
                eMaterias = Materia.objects.filter(nivel__in=eNiveles, status=True)
                aData['eMallas'] = []
                aData['eMalla'] = {}
                aData['eNivelesMalla'] = []
                aData['eNivelMalla'] = {}
                aData['eParalelos'] = []
                aData['eParalelo'] = {}
                aData['eMaterias'] = []
                conflicto = False
                if eMaterias.values("id").exists():
                    eMallas = Malla.objects.filter(pk__in=eMaterias.values_list("asignaturamalla__malla_id", flat=True)).order_by('carrera__nombre')
                    eMalla = eMallas.first()
                    if 'idm' in request.POST and request.POST['idm']:
                        eMalla = eMallas.filter(pk=encrypt(request.POST['idm'])).first()
                    eNivelesMalla = NivelMalla.objects.filter(pk__in=eMaterias.values_list("asignaturamalla__nivelmalla_id", flat=True).filter(asignaturamalla__malla=eMalla)).distinct().order_by('orden')
                    eNivelMalla = eNivelesMalla.first()
                    if 'idnm' in request.POST and request.POST['idnm']:
                        eNivelMallatemp = eNivelesMalla.filter(pk=encrypt(request.POST['idnm'])).first()
                        eNivelMalla = eNivelMalla if eNivelMallatemp is None else eNivelMallatemp
                    eParalelos = Paralelo.objects.filter(pk__in=eMaterias.values_list("paralelomateria_id", flat=True).filter(asignaturamalla__malla=eMalla, asignaturamalla__nivelmalla=eNivelMalla)).distinct()
                    eParalelo = eParalelos.first()
                    if 'idp' in request.POST and request.POST['idp']:
                        eParalelotemp = eParalelos.filter(pk=encrypt(request.POST['idp'])).first()
                        eParalelo = eParalelo if eParalelotemp is None else eParalelotemp
                    eMaterias = eMaterias.filter(asignaturamalla__malla=eMalla, asignaturamalla__nivelmalla=eNivelMalla, paralelomateria=eParalelo)
                    # conflicto = eMaterias.annotate(conflicto=Count('horarioexamen__horarioexamendetalle',
                    #                                filter=Q(Q(horarioexamen__horarioexamendetalle__horainicio__lte=F('horarioexamen__horarioexamendetalle__horafin'), horarioexamen__horarioexamendetalle__horafin__gte=F('horarioexamen__horarioexamendetalle__horainicio'))|
                    #                                         Q(horarioexamen__horarioexamendetalle__horainicio__lte=F('horarioexamen__horarioexamendetalle__horainicio'), horarioexamen__horarioexamendetalle__horafin__gte=F('horarioexamen__horarioexamendetalle__horainicio'))|
                    #                                         Q(horarioexamen__horarioexamendetalle__horainicio__lte=F('horarioexamen__horarioexamendetalle__horafin'), horarioexamen__horarioexamendetalle__horafin__gte=F('horarioexamen__horarioexamendetalle__horafin'))
                    #                                         )& ~Q(horarioexamen__horarioexamendetalle__id=F('horarioexamen__horarioexamendetalle__id')) & Q(status=True,
                    #                                         horarioexamen__detallemodelo=F('horarioexamen__detallemodelo'),
                    #                                         horarioexamen__fecha=F('horarioexamen__fecha'),
                    #                                         horarioexamen__status=True,
                    #                                         horarioexamen__horarioexamendetalle__aula=F('horarioexamen__horarioexamendetalle__aula')), distinct=True)).values('conflicto', 'asignatura__nombre')

                    data_json = {
                                    'periodo_id': periodo.id,
                                    'sesion_id': eSesion.id,
                                    'coordinacion_id': eCoordinacion.id,
                                    'nivelmalla_id': eNivelMalla.id,
                                    'paralelo_id': eParalelo.id,
                                    'malla_id': eMalla.id,
                                 }
                    aData['conflicto'] = conflicto
                    aData['eMallas'] = MallaSerializer(eMallas, context=data_json, many=True).data
                    aData['eMalla'] = MallaSerializer(eMalla, context=data_json).data
                    aData['eNivelesMalla'] = NivelMallaSerializer(eNivelesMalla, context=data_json, many=True).data
                    aData['eNivelMalla'] = NivelMallaSerializer(eNivelMalla, context=data_json).data
                    aData['eParalelos'] = ParaleloSerializer(eParalelos, context=data_json, many=True).data
                    aData['eParalelo'] = ParaleloSerializer(eParalelo, context=data_json).data
                    aData['eMaterias'] = MateriaSerializer(eMaterias, context=data_json, many=True).data
                return JsonResponse({"result": "ok", "aData": aData})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        elif action == 'saveHorarioExamen':
            try:
                # VALIDAR_CONFLICTO_HORARIO= variable_valor('VALIDAR_CONFLICTO_HORARIO')

                # if VALIDAR_CONFLICTO_HORARIO:
                if not 'idm' in request.POST:
                    raise NameError(u"No se encontro el parametro de la materia del horario de examen")

                if not 'ida' in request.POST:
                    raise NameError(u"No se encontro el parametro del aula del horario de examen")

                idhed = 0
                if 'idhed' in request.POST:
                    idhed = encrypt(request.POST['idhed'])

                if not 'iddm' in request.POST:
                    raise NameError(u"No se encontro el parametro de detalle del modelo evaluativo")

                if not 'fecha' in request.POST:
                    raise NameError(u"No se encontro el parametro de fecha")

                if not 'h_comienza' in request.POST:
                    raise NameError(u"No se encontro el parametro de hora de comienzo")

                if not 'h_termina' in request.POST:
                    raise NameError(u"No se encontro el parametro de hora de termino")

                if not 'cantidad' in request.POST:
                    raise NameError(u"No se encontro el parametro de cantidad de alumnos")

                if not 'idr' in request.POST:
                    raise NameError(u"No se encontro el parametro de responsable")

                if not 'tiporesponsable' in request.POST:
                    raise NameError(u"No se encontro el parametro de tipo responsable")

                if not 'validahorario' in request.POST:
                    raise NameError(u"No se encontro el parametro de valida horario")
                ida = encrypt(request.POST['ida'])

                idm = encrypt(request.POST['idm'])
                iddm = encrypt(request.POST['iddm'])
                fecha = request.POST['fecha']
                h_comienza = request.POST['h_comienza']
                h_termina = request.POST['h_termina']
                VALIDAR_CONFLICTO_HORARIO = int(request.POST['validahorario']) == 1 if True else False
                tiporesponsable = int(request.POST['tiporesponsable'])
                cantidad = int(request.POST['cantidad'])
                eMateria = Materia.objects.get(pk=idm)
                eMalla = eMateria.asignaturamalla.malla
                eNivelMalla = eMateria.asignaturamalla.nivelmalla
                eParalelo = eMateria.paralelomateria
                eProfesorMateria = None
                eProfesor = None
                eAdministrativo = None
                if tiporesponsable == 1:
                    eProfesorMateria = ProfesorMateria.objects.get(pk=encrypt(request.POST['idr']))
                elif tiporesponsable == 2:
                    eProfesor = Profesor.objects.get(pk=encrypt(request.POST['idr']))
                elif tiporesponsable == 3:
                    eAdministrativo = Administrativo.objects.get(pk=encrypt(request.POST['idr']))
                eMateria.actualizarhtml = True
                eMateria.save()
                eAula = Aula.objects.get(pk=ida)
                eDetalleModeloEvaluativo = DetalleModeloEvaluativo.objects.get(pk=iddm)
                fecha = convertir_fecha_invertida(fecha)
                h_comienza = convertir_hora(h_comienza)
                h_termina = convertir_hora(h_termina)
                if VALIDAR_CONFLICTO_HORARIO:
                    if h_comienza > h_termina:
                        raise NameError(u"Hora de comienzo no puede ser mayo a la hora de culmnación")
                    if cantidad > eAula.capacidad:
                        raise NameError(u"Capacidad el aula no permitida")
                    diferencia = timedelta(hours=h_termina.hour, minutes=h_termina.minute) - timedelta(hours=h_comienza.hour, minutes=h_comienza.minute)
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
                if idhed == 0:
                    if VALIDAR_CONFLICTO_HORARIO:
                        if eAula.id != 218:
                            if HorarioExamenDetalle.objects.values("id").filter(Q(horainicio__lte=h_termina, horafin__gte=h_comienza), horarioexamen__fecha=fecha, status=True, aula=eAula, validahorario=True).exists():
                                raise NameError(u"Horario ocupado para el aula")
                        if eProfesorMateria:
                            if HorarioExamenDetalle.objects.values("id").filter(Q(horainicio__lte=h_termina, horafin__gte=h_comienza), horarioexamen__fecha=fecha, status=True, profesormateria=eProfesorMateria, validahorario=True).exists():
                                raise NameError(u"Horario ocupado para la materia")
                        if eProfesor:
                            if HorarioExamenDetalle.objects.values("id").filter(Q(horainicio__lte=h_termina, horafin__gte=h_comienza), horarioexamen__fecha=fecha, status=True, profesor=eProfesor, validahorario=True).exists():
                                raise NameError(u"Horario ocupado para la materia")
                        if eAdministrativo:
                            if HorarioExamenDetalle.objects.values("id").filter(Q(horainicio__lte=h_termina, horafin__gte=h_comienza), horarioexamen__fecha=fecha, status=True, administrativo=eAdministrativo, validahorario=True).exists():
                                raise NameError(u"Horario ocupado para la materia")
                        if eHorarioExamenDetalles.values("id").filter(Q(horainicio__lte=h_termina, horafin__gte=h_comienza), horarioexamen__fecha=fecha, validahorario=True).exists():
                            raise NameError(u"Horario ocupado para la materia")
                        totalPlanificados = int(eHorarioExamenDetalles.aggregate(total=Sum('cantalumnos'))['total']) if eHorarioExamenDetalles.values("id").exists() else 0
                        totalPlanificados = totalPlanificados + cantidad
                        if totalPlanificados > eMateria.cantidad_alumnos():
                            raise NameError(u"Cantidad de alumnos planificados sobrepasa la cantidad de alumnos matriculados")
                        if eProfesorMateria:
                            eHorarioExamenesDetalles = HorarioExamenDetalle.objects.filter(Q(horainicio__lte=h_termina, horafin__gte=h_comienza),
                                                                                           Q(Q(profesormateria__profesor__persona=eProfesorMateria.profesor.persona) |
                                                                                             Q(profesor__persona=eProfesorMateria.profesor.persona) |
                                                                                             Q(administrativo__persona=eProfesorMateria.profesor.persona)
                                                                                             ),
                                                                                           horarioexamen__fecha=fecha,
                                                                                           horarioexamen__detallemodelo_id=iddm,
                                                                                           status=True)
                            if eHorarioExamenesDetalles.exists():
                                raise NameError(u"Horario de profesor responsable  ocupado")
                        if eProfesor:
                            eHorarioExamenesDetalles = HorarioExamenDetalle.objects.filter(Q(horainicio__lte=h_termina, horafin__gte=h_comienza),
                                                                                           Q(Q(profesormateria__profesor__persona=eProfesor.persona) |
                                                                                             Q(profesor__persona=eProfesor.persona) |
                                                                                             Q(administrativo__persona=eProfesor.persona)
                                                                                             ),
                                                                                           horarioexamen__fecha=fecha,
                                                                                           horarioexamen__detallemodelo_id=iddm,
                                                                                           status=True)
                            if eHorarioExamenesDetalles.exists():
                                raise NameError(u"Horario de profesor responsable  ocupado")
                        if eAdministrativo:
                            eHorarioExamenesDetalles = HorarioExamenDetalle.objects.filter(Q(horainicio__lte=h_termina, horafin__gte=h_comienza),
                                                                                           Q(Q(profesormateria__profesor__persona=eAdministrativo.persona) |
                                                                                             Q(profesor__persona=eAdministrativo.persona) |
                                                                                             Q(administrativo__persona=eAdministrativo.persona)
                                                                                             ),
                                                                                           horarioexamen__fecha=fecha,
                                                                                           horarioexamen__detallemodelo_id=iddm,
                                                                                           status=True)
                            if eHorarioExamenesDetalles.exists():
                                raise NameError(u"Horario de profesor responsable  ocupado")
                        eHorarioExamenesDetalles = HorarioExamenDetalle.objects.filter(Q(horainicio__lte=h_termina, horafin__gte=h_comienza),
                                                                                       horarioexamen__fecha=fecha,
                                                                                       horarioexamen__materia__asignaturamalla__malla_id=eMalla.id,
                                                                                       horarioexamen__materia__asignaturamalla__nivelmalla_id=eNivelMalla.id,
                                                                                       horarioexamen__detallemodelo_id=iddm,
                                                                                       horarioexamen__materia__paralelomateria_id=eParalelo.id,
                                                                                       status=True)
                        if eHorarioExamenesDetalles.exists():
                            raise NameError(u"Conflicto de horario en paralelo")
                    eHorarioExamenes = HorarioExamen.objects.filter(materia=eMateria, fecha=fecha, detallemodelo_id=iddm, status=True)
                    if not eHorarioExamenes.values("id").exists():
                        eHorarioExamen = HorarioExamen(materia=eMateria,
                                                       detallemodelo_id=iddm,
                                                       fecha=fecha)
                        eHorarioExamen.save(request)
                        log(u'Adiciono Horario de examenes: %s' % eHorarioExamen, request, "add")
                    else:
                        eHorarioExamen = eHorarioExamenes.first()
                    if VALIDAR_CONFLICTO_HORARIO:
                        if not eHorarioExamen.maximo_por_hora(eHorarioExamen.fecha, h_comienza, h_termina, cantidad):
                            raise NameError(u"No puede ingresar mas alumnos en este rango de horas, debe crear una nueva jornada con un rango de horas o fecha diferente")
                else:
                    eHorarioExamenDetalle = HorarioExamenDetalle.objects.get(pk=idhed)
                    if VALIDAR_CONFLICTO_HORARIO:
                        if eAula.id != 218:
                            if HorarioExamenDetalle.objects.values("id").filter(Q(horainicio__lte=h_termina, horafin__gte=h_comienza), horarioexamen__fecha=fecha, status=True, aula=eAula, validahorario=True).exclude(pk=eHorarioExamenDetalle.pk).exists():
                                raise NameError(u"Horario ocupado para el aula")
                        if eProfesorMateria:
                            if HorarioExamenDetalle.objects.values("id").filter(Q(horainicio__lte=h_termina, horafin__gte=h_comienza), horarioexamen__fecha=fecha, status=True, profesormateria=eProfesorMateria, validahorario=True).exclude(pk=eHorarioExamenDetalle.pk).exists():
                                raise NameError(u"Horario ocupado para la materia")
                        if eProfesor:
                            if HorarioExamenDetalle.objects.values("id").filter(Q(horainicio__lte=h_termina, horafin__gte=h_comienza), horarioexamen__fecha=fecha, status=True, profesor=eProfesor, validahorario=True).exclude(pk=eHorarioExamenDetalle.pk).exists():
                                raise NameError(u"Horario ocupado para la materia")
                        if eAdministrativo:
                            if HorarioExamenDetalle.objects.values("id").filter(Q(horainicio__lte=h_termina, horafin__gte=h_comienza), horarioexamen__fecha=fecha, status=True, administrativo=eAdministrativo, validahorario=True).exclude(pk=eHorarioExamenDetalle.pk).exists():
                                raise NameError(u"Horario ocupado para la materia")
                        if eHorarioExamenDetalles.values("id").filter(Q(horainicio__lte=h_termina, horafin__gte=h_comienza), horarioexamen__fecha=fecha, validahorario=True).exclude(pk=eHorarioExamenDetalle.pk).exists():
                            raise NameError(u"Horario ocupado para la materia")
                        totalPlanificados = int(eHorarioExamenDetalles.exclude(pk=eHorarioExamenDetalle.pk).aggregate(total=Sum('cantalumnos'))['total']) if eHorarioExamenDetalles.values("id").exclude(pk=eHorarioExamenDetalle.pk).exists() else 0
                        totalPlanificados = totalPlanificados + cantidad
                        if totalPlanificados > eMateria.cantidad_alumnos():
                            raise NameError(u"Cantidad de alumnos planificados sobrepasa la cantidad de alumnos matriculados")

                        if eProfesorMateria:
                            eHorarioExamenesDetalles = HorarioExamenDetalle.objects.filter(Q(horainicio__lte=h_termina, horafin__gte=h_comienza),
                                                                                           Q(Q(profesormateria__profesor__persona=eProfesorMateria.profesor.persona) |
                                                                                             Q(profesor__persona=eProfesorMateria.profesor.persona) |
                                                                                             Q(administrativo__persona=eProfesorMateria.profesor.persona)
                                                                                             ),
                                                                                           horarioexamen__fecha=fecha,
                                                                                           horarioexamen__detallemodelo_id=iddm,
                                                                                           status=True).exclude(pk=eHorarioExamenDetalle.pk)
                            if eHorarioExamenesDetalles.exists():
                                raise NameError(u"Horario de profesor responsable  ocupado")
                        if eProfesor:
                            eHorarioExamenesDetalles = HorarioExamenDetalle.objects.filter(Q(horainicio__lte=h_termina, horafin__gte=h_comienza),
                                                                                           Q(Q(profesormateria__profesor__persona=eProfesor.persona) |
                                                                                             Q(profesor__persona=eProfesor.persona) |
                                                                                             Q(administrativo__persona=eProfesor.persona)
                                                                                             ),
                                                                                           horarioexamen__fecha=fecha,
                                                                                           horarioexamen__detallemodelo_id=iddm,
                                                                                           status=True).exclude(pk=eHorarioExamenDetalle.pk)
                            if eHorarioExamenesDetalles.exists():
                                raise NameError(u"Horario de profesor responsable  ocupado")
                        if eAdministrativo:
                            eHorarioExamenesDetalles = HorarioExamenDetalle.objects.filter(Q(horainicio__lte=h_termina, horafin__gte=h_comienza),
                                                                                           Q(Q(profesormateria__profesor__persona=eAdministrativo.persona) |
                                                                                             Q(profesor__persona=eAdministrativo.persona) |
                                                                                             Q(administrativo__persona=eAdministrativo.persona)
                                                                                             ),
                                                                                           horarioexamen__fecha=fecha,
                                                                                           horarioexamen__detallemodelo_id=iddm,
                                                                                           status=True).exclude(pk=eHorarioExamenDetalle.pk)
                            if eHorarioExamenesDetalles.exists():
                                raise NameError(u"Horario de profesor responsable  ocupado")

                        eHorarioExamenesDetalles = HorarioExamenDetalle.objects.filter(Q(horainicio__lte=h_termina, horafin__gte=h_comienza),
                                                                                       horarioexamen__fecha=fecha,
                                                                                       horarioexamen__materia__asignaturamalla__malla_id=eMalla.id,
                                                                                       horarioexamen__materia__asignaturamalla__nivelmalla_id=eNivelMalla.id,
                                                                                       horarioexamen__detallemodelo_id=iddm,
                                                                                       horarioexamen__materia__paralelomateria_id=eParalelo.id,
                                                                                       status=True).exclude(pk=eHorarioExamenDetalle.pk)
                        if eHorarioExamenesDetalles.exists():
                            raise NameError(u"Conflicto de horario en paralelo")

                    eHorarioExamen = eHorarioExamenDetalle.horarioexamen
                    if eHorarioExamen.fecha != fecha or eHorarioExamen.detallemodelo_id != int(iddm):
                        eHorarioExamenes = HorarioExamen.objects.filter(materia=eMateria, fecha=fecha, detallemodelo_id=iddm, status=True)
                        if not eHorarioExamenes.values("id").exists():
                            eHorarioExamen = HorarioExamen(materia=eMateria,
                                                           detallemodelo_id=iddm,
                                                           fecha=fecha)
                            eHorarioExamen.save(request)
                            log(u'Adiciono Horario de examenes: %s' % eHorarioExamen, request, "add")
                        else:
                            eHorarioExamen = eHorarioExamenes.first()
                    if VALIDAR_CONFLICTO_HORARIO:
                        if not eHorarioExamen.maximo_por_hora(eHorarioExamen.fecha, h_comienza, h_termina, cantidad):
                            raise NameError(u"No puede ingresar mas alumnos en este rango de horas, debe crear una nueva jornada con un rango de horas o fecha diferente")
                if idhed == 0:
                    eHorarioExamenDetalles = HorarioExamenDetalle.objects.filter(status=True, horarioexamen=eHorarioExamen, horainicio=h_comienza, horafin=h_termina)
                    if VALIDAR_CONFLICTO_HORARIO:
                        if eHorarioExamenDetalles.values("id").exists():
                            raise NameError(u"Ya existe horario en la jornada ingresada")

                        # eHorarioExamenesDetalles = HorarioExamenDetalle.objects.filter(Q(horainicio__lte=h_termina, horafin__gte=h_comienza),
                        #                                                                horarioexamen__fecha=fecha,
                        #                                                                horarioexamen__detallemodelo_id=iddm,
                        #                                                                profesormateria__profesor=eProfesorMateria.profesor,
                        #                                                                status=True)
                        # if eHorarioExamenesDetalles.exists():
                        #     raise NameError(u"Horario de profesor  ocupado")
                        #
                        # eHorarioExamenesDetalles = HorarioExamenDetalle.objects.filter(Q(horainicio__lte=h_termina, horafin__gte=h_comienza), horarioexamen__fecha=fecha,
                        #                                                                   horarioexamen__materia__asignaturamalla__malla_id=eMalla.id,
                        #                                                                   horarioexamen__materia__asignaturamalla__nivelmalla_id=eNivelMalla.id,
                        #                                                                   horarioexamen__detallemodelo_id=iddm,
                        #                                                                   horarioexamen__materia__paralelomateria_id=eParalelo.id,
                        #                                                                   status=True)
                        # if eHorarioExamenesDetalles.exists():
                        #     raise NameError(u"Conflicto de horario en paralelo")
                    eHorarioExamenDetalle = HorarioExamenDetalle(horarioexamen=eHorarioExamen,
                                                                 horainicio=h_comienza,
                                                                 horafin=h_termina,
                                                                 aula=eAula,
                                                                 cantalumnos=cantidad,
                                                                 profesormateria=eProfesorMateria,
                                                                 profesor=eProfesor,
                                                                 administrativo=eAdministrativo,
                                                                 validahorario=VALIDAR_CONFLICTO_HORARIO)
                    eHorarioExamenDetalle.save(request)
                    log(u'Adiciono Detalle Horario de examenes: %s' % eHorarioExamenDetalle, request, "add")
                else:
                    eHorarioExamenDetalles = HorarioExamenDetalle.objects.filter(status=True, horarioexamen=eHorarioExamen)
                    if VALIDAR_CONFLICTO_HORARIO:
                        if eHorarioExamenDetalles.values("id").filter(horainicio=h_comienza, horafin=h_termina, horarioexamen__fecha=fecha).exclude(pk=idhed).exists():
                            raise NameError(u"Ya existe horario en la jornada ingresada")
                    eHorarioExamenDetalle = eHorarioExamenDetalles.filter(pk=idhed).first()
                    eHorarioExamenDetalle.horainicio=h_comienza
                    eHorarioExamenDetalle.horafin=h_termina
                    eHorarioExamenDetalle.aula=eAula
                    eHorarioExamenDetalle.cantalumnos=cantidad
                    eHorarioExamenDetalle.profesormateria=eProfesorMateria
                    eHorarioExamenDetalle.profesor=eProfesor
                    eHorarioExamenDetalle.administrativ=eAdministrativo
                    eHorarioExamenDetalle.validahorario=VALIDAR_CONFLICTO_HORARIO
                    eHorarioExamenDetalle.save(request)
                    log(u'Edito Detalle Horario de examenes: %s' % eHorarioExamenDetalle, request, "edit")
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
                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        elif action == 'deleteHorarioExamen':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro el parametro del examen a eliminar")
                id = int(encrypt(request.POST['id']))
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

        elif action == 'cloneHorarioExamen':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro el examen a clonar")

                if not 'iddm' in request.POST:
                    raise NameError(u"No se encontro el parametro de detalle del modelo evaluativo")

                if not 'fecha' in request.POST:
                    raise NameError(u"No se encontro el parametro de fecha")
                id = int(encrypt(request.POST['id']))
                iddm = encrypt(request.POST['iddm'])
                fecha = request.POST['fecha']
                fecha = convertir_fecha_invertida(fecha)
                eDetalleModeloEvaluativo = DetalleModeloEvaluativo.objects.get(pk=iddm)
                eHorarioExamenDetalle = HorarioExamenDetalle.objects.get(pk=id)
                VALIDAR_CONFLICTO_HORARIO = eHorarioExamenDetalle.validahorario
                eHorarioExamen = eHorarioExamenDetalle.horarioexamen
                eMateria = eHorarioExamen.materia
                eCloneHorarioExamenDetalle = eHorarioExamenDetalle
                eCloneHorarioExamen = eHorarioExamen
                eCloneHorarioExamen.pk = None
                eCloneHorarioExamen.fecha = fecha
                eCloneHorarioExamen.detallemodelo = eDetalleModeloEvaluativo
                eCloneHorarioExamen.save(request)
                eCloneHorarioExamenDetalle.pk = None
                eCloneHorarioExamenDetalle.horarioexamen = eCloneHorarioExamen
                eCloneHorarioExamenDetalle.save(request)
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
                        eHorarioExamenDetalleAlumno = HorarioExamenDetalleAlumno(materiaasignada=eAlumno, horarioexamendetalle=eHorario)
                        eHorarioExamenDetalleAlumno.save(request)
                        log(u'Adiciono alumno al Horario de examenes: %s' % eHorarioExamenDetalleAlumno, request, "add")
                log(u'Adiciono horario de examen: %s' % eCloneHorarioExamenDetalle, request, "add")
                return JsonResponse({"result": "ok", "mensaje": u"Se clono correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'reporteaula_examenes':
                try:
                    periodo = request.GET['periodo']
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 12, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=exp_xls_post_part_' + random.randint(1, 10000).__str__() + '.xls'
                    row_num = 3
                    columns = [
                        (u"AULA", 6000),
                        (u"CAPACIDAD AULA", 6000),
                        (u"CUPO MATRICULA", 6000),
                        (u"MATRICULADOS", 6000),
                        (u"INSCRITOS", 6000),
                        (u"CANTIDAD ALUMNOS", 6000),
                        (u"DÍAS", 6000),
                        (u"FECHA", 6000),
                        (u"INICIO HORARIO", 6000),
                        (u"FIN HORARIO", 6000),
                        (u"HORARIOS", 6000),
                        (u"ASIGNATURA", 6000),
                        (u"MODALIDAD", 6000),
                        (u"IDMATERIA", 6000),
                        (u"JORNADA", 6000),
                        (u"NIVEL", 6000),
                        (u"MODELO EVALUATIVO", 6000),
                        (u"CARRERA", 6000),
                        (u"PARALELO", 6000),
                        (u"DOCENTE", 6000),
                        (u"TIPO PROFESOR", 6000),
                        (u"CATEGORIA", 6000),
                        (u"DEDICACIÓN", 6000),
                        (u"PRINCIPAL", 6000),
                        (u"FACULTAD", 6000),
                        (u"TIPO MATERIA", 6000),
                        (u"ID HORARIO", 4000),
                        (u"INICIO MATERIA", 4000),
                        (u"FIN MATERIA", 4000),
                        (u"TIPO GRUPO", 4000),
                        (u"ES PRÁCTICA", 4000),
                        (u"SILABO", 4000),
                        (u"TIENE GUIA PRÁCTICA", 4000),
                        (u"CONFLICTO HORARIO PROFESOR", 20000),
                        (u"CONFLICTO HORARIO AULA", 20000),
                        (u"CAPACIDAD MAXIMA", 20000),
                        # (u"ID MATERIA", 4000),

                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    cursor = connections['sga_select'].cursor()
                    # lista_json = []
                    # data = {}
                    sql = f"""SELECT
                                    al.nombre AS Aula, al.capacidad AS capacidad_aula, mat.cupo AS cupo_matriculas,
                                    (SELECT COUNT(*)
                                  FROM sga_materiaasignada mas1, sga_matricula mat1, sga_nivel ni1
                                  WHERE mat1.estado_matricula in (2,3) AND mas1.matricula_id=mat1.id 
                                    AND mat1.nivel_id=ni1.id 
                                    AND ni1.periodo_id=ni.periodo_id 
                                    AND mas1.materia_id=mat.id AND mas1.retiramateria=FALSE AND mas1."status") AS matriculados,
                                   (
                                SELECT COUNT(*)
                                FROM sga_materiaasignada mas1, sga_matricula mat1, sga_nivel ni1
                                WHERE mat1.estado_matricula=1 AND mas1.matricula_id=mat1.id AND mat1.nivel_id=ni1.id 
                                AND ni1.periodo_id=ni.periodo_id AND mas1.materia_id=mat.id) AS inscritos,
                                    hdex.cantalumnos  cantidad_alumnos,
                                    (CASE EXTRACT(isodow  FROM hex.fecha) WHEN 1 THEN 'LUNES' WHEN 2 THEN 'MARTES' WHEN 3 THEN 'MIERCOLES' WHEN 4 THEN 'JUEVES' WHEN 5 THEN 'VIERNES' WHEN 6 THEN 'SABADO' WHEN 7 THEN 'DOMINGO' END) AS dia,
                                    hex.fecha, 
                                    hdex.horainicio,
                                    hdex.horafin,
                                    (hdex.horainicio|| '  ' ||hdex.horafin) AS Horario,
                                    asi.nombre asignatura, 
                                    (select CASE WHEN mod.modalidad = 1 THEN 'PRESENCIAL' else 'VIRTUAL' END) as modalidad,
                                    mat.id AS idmateria,
                                    ni.paralelo AS jornada, 
                                    nmall.nombre AS nivel,
                                  dmev.nombre modeloevaluativo,
                                    ca.nombre AS Carrera, mat.paralelo AS paralelo, per.apellido1 ||' '|| per.apellido2 ||' '|| per.nombres AS docente,
                                  tipop.nombre AS tipo_profesor, cat.nombre AS categorizacion,ded.nombre AS dedicacion,
                                  (CASE pm.principal WHEN TRUE THEN 'SI' ELSE 'NO' END) AS principal, cor.nombre AS facultad, 
                                    (CASE asimall.practicas WHEN TRUE THEN 'SI' ELSE 'NO' END) AS tipomateria,
                                    hex.id id_horario,
                                    mat.inicio AS Inicio_materia, 
                                    mat.fin AS Fin_materia, 
                                    hdex.tipogrupo tipo_grupo,
                                    --cl.tipohorario AS cl_tipohorario,
                                    (CASE asimall.practicas WHEN TRUE THEN 'SI' ELSE 'NO' END) AS asimall_practicas,
                                     (CASE 
                                (SELECT count(*) 
                                        FROM sga_silabo AS sga_s 
                                        WHERE sga_s.materia_id = pm.materia_id AND sga_s.status=True AND sga_s.codigoqr=True
                                    ) 
                                        WHEN 0 THEN
                                            'NO'
                                        ELSE 
                                            'SI'
                                        END
                                    ) AS silabo,
                                    (SELECT 
                                count(sga_tp.*) 
                        FROM sga_tareapracticasilabosemanal AS sga_tp
                        INNER JOIN sga_silabosemanal AS sga_ss ON sga_tp.silabosemanal_id = sga_ss.id
                        INNER JOIN sga_silabo AS sga_s ON sga_ss.silabo_id = sga_s.id
                        INNER JOIN sga_materia AS sga_m ON sga_m.id = sga_s.materia_id
                        WHERE 
                            sga_s.status= TRUE 
                            AND sga_s.codigoqr= TRUE 
                            AND sga_m.id = mat.id 
                            AND sga_tp.estado_id!=3 
                            AND sga_tp.status=True
                        ) AS trabajos_practicos, 
                        conflictos_profesor.nombres conflicto_horario_profesor, 
                         conflictos_aula.nombres conflicto_horario_aula,
                        (CASE when  hdex.cantalumnos>al.capacidad THEN 'SI' ELSE 'NO' END) capacidad_maxima_aula
                        FROM sga_horarioexamen hex
                        INNER JOIN  sga_horarioexamendetalle hdex ON hdex.horarioexamen_id=hex.id
                        INNER JOIN sga_materia mat ON mat.id=hex.materia_id
                        INNER JOIN sga_nivel ni ON mat.nivel_id=ni.id
                        INNER JOIN sga_asignatura asi ON mat.asignatura_id=asi.id
                        INNER JOIN sga_asignaturamalla asimall ON mat.asignaturamalla_id = asimall.id
                        INNER JOIN sga_nivelmalla nmall ON asimall.nivelmalla_id = nmall.id 
                        INNER JOIN sga_malla mall ON asimall.malla_id = mall.id 
                        INNER JOIN sga_carrera ca ON mall.carrera_id=ca.id
                        INNER JOIN sga_detallemodeloevaluativo dmev ON dmev.id=hex.detallemodelo_id
                        INNER JOIN sga_modeloevaluativo mev ON mev.id=dmev.modelo_id
                        INNER JOIN sga_profesormateria pm ON pm.id=hdex.profesormateria_id
                        INNER JOIN sga_tipoprofesor tipop ON tipop.id=pm.tipoprofesor_id
                        INNER JOIN sga_profesor pr ON pr.id=pm.profesor_id --AND cl.profesor_id=pr.id
                        INNER JOIN sga_tiempodedicaciondocente ded ON pr.dedicacion_id=ded.id
                        INNER JOIN sga_categorizaciondocente cat ON pr.categoria_id=cat.id
                        INNER JOIN sga_persona per ON per.id=pr.persona_id
                        INNER JOIN sga_coordinacion_carrera cc ON cc.carrera_id=ca.id
                        INNER JOIN sga_coordinacion cor ON cor.id=cc.coordinacion_id
                        LEFT JOIN sga_detalleasignaturamallamodalidad mod ON asimall.id = mod.asignaturamalla_id 
                        LEFT JOIN sga_aula al ON hdex.aula_id=al.id
                        LEFT JOIN LATERAL	(
                                    SELECT 
                                    array_to_string(array_agg(distinct sga_asignatura.nombre),',') nombres 
                                    FROM "sga_horarioexamendetalle" 
                                        INNER JOIN "sga_horarioexamen" ON ("sga_horarioexamendetalle"."horarioexamen_id" = "sga_horarioexamen"."id") 
                                        INNER JOIN "sga_profesormateria" ON ("sga_horarioexamendetalle"."profesormateria_id" = "sga_profesormateria"."id") 
                                        LEFT  JOIN sga_materia ON sga_materia.id=sga_horarioexamen.materia_id
                                        LEFT  JOIN sga_asignatura ON sga_asignatura.id=sga_materia.asignatura_id
                                        INNER JOIN sga_detallemodeloevaluativo ON sga_detallemodeloevaluativo.id=sga_horarioexamen.detallemodelo_id
                                        INNER JOIN sga_modeloevaluativo ON sga_modeloevaluativo.id=sga_detallemodeloevaluativo.modelo_id
                                    WHERE 
                                    (
                                    --"sga_horarioexamen"."detallemodelo_id" = hex.detallemodelo_id
                                    sga_modeloevaluativo.id=mev.id
                                    AND "sga_horarioexamen"."fecha" = hex.fecha
                                    AND "sga_horarioexamen"."status" 
                                    AND "sga_profesormateria"."profesor_id" =pr.id
                                    AND "sga_horarioexamendetalle"."status" 
                                    AND (((sga_horarioexamendetalle.horafin >= hdex.horafin AND sga_horarioexamendetalle.horainicio <= hdex.horainicio)
                                                OR (sga_horarioexamendetalle.horafin = hdex.horafin AND sga_horarioexamendetalle.horainicio = hdex.horainicio)
                                                        OR( hdex.horainicio   BETWEEN sga_horarioexamendetalle.horainicio  AND sga_horarioexamendetalle.horafin)
                                                        OR ( hdex.horafin   BETWEEN sga_horarioexamendetalle.horainicio  AND sga_horarioexamendetalle.horafin))) 
                                                        AND NOT ("sga_horarioexamendetalle"."id" = hdex.id))
                        ) conflictos_profesor ON  True
                        
                         LEFT JOIN LATERAL	(
                             SELECT 
                                     array_to_string(array_agg(distinct sga_asignatura.nombre),',') nombres 
                             FROM "sga_horarioexamendetalle" 
                                 INNER JOIN "sga_horarioexamen" ON ("sga_horarioexamendetalle"."horarioexamen_id" = "sga_horarioexamen"."id")
                                 INNER JOIN sga_materia ON sga_materia.id=sga_horarioexamen.materia_id
                                 INNER JOIN sga_asignatura ON sga_asignatura.id=sga_materia.asignatura_id
                             WHERE 
                                 (	
                                 "sga_horarioexamendetalle"."aula_id" = hdex.aula_id 
                                 AND "sga_horarioexamen"."detallemodelo_id" = hex.detallemodelo_id
                                 AND "sga_horarioexamen"."fecha" = hex.fecha
                                 AND "sga_horarioexamen"."status" 
                                 AND "sga_horarioexamendetalle"."aula_id"!=218
                                 AND "sga_horarioexamendetalle"."status" 
                                 AND 
                                     (((sga_horarioexamendetalle.horafin >= hdex.horafin AND sga_horarioexamendetalle.horainicio <= hdex.horainicio)
                                                 OR(  hdex.horainicio BETWEEN sga_horarioexamendetalle.horainicio  AND sga_horarioexamendetalle.horafin)
                                                 OR (  hdex.horafin BETWEEN sga_horarioexamendetalle.horainicio  AND sga_horarioexamendetalle.horafin))) 
                             AND NOT ("sga_horarioexamendetalle"."id" = hdex.id))
                         ) conflictos_aula ON  True
                        WHERE 
                        ni.periodo_id={periodo} AND 
                        hex.status AND hdex.status
                        """
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    row_num = 4
                    for r in results:
                        i = 0
                        campo1 = r[0]
                        campo2 = r[1]
                        campo3 = r[2]
                        campo4 = r[3]
                        campo5 = r[4]
                        campo6 = r[5]
                        campo7 = r[6]
                        campo8 = r[7]
                        campo9 = r[8]
                        campo10 = r[9]
                        campo11 = r[10]
                        campo12 = r[11]
                        campo13 = r[12]
                        campo14 = r[13]
                        campo15 = r[14]
                        campo16 = r[15]
                        campo17 = r[16]
                        campo18 = r[17]
                        campo19 = r[18]
                        campo20 = r[19]
                        campo21 = r[20]
                        campo22 = r[21]
                        campo23 = r[22]
                        campo24 = r[23]
                        campo25 = r[24]
                        campo26 = r[25]
                        campo27 = r[26]
                        campo28 = r[27]
                        campo29 = r[28]
                        campo30 = dict(TIPO_GRUPOS)[r[29]]
                        campo31 = r[30]
                        campo32 = r[31]
                        campo33 = r[32]
                        campo34 = r[33]
                        campo35 = r[34]
                        campo36 = r[35]
                        ws.write(row_num, 0, u"%s" % campo1, font_style2)
                        ws.write(row_num, 1, u"%s" % campo2, font_style2)
                        ws.write(row_num, 2, u"%s" % campo3, font_style2)
                        ws.write(row_num, 3, u"%s" % campo4, font_style2)
                        ws.write(row_num, 4, u"%s" % campo5, font_style2)
                        ws.write(row_num, 5, u"%s" % campo6, font_style2)
                        ws.write(row_num, 6, u"%s" % campo7, style1)
                        ws.write(row_num, 7, u"%s" % campo8, style1)
                        ws.write(row_num, 8, u"%s" % campo9, style1)
                        ws.write(row_num, 9, u"%s" % campo10, font_style2)
                        ws.write(row_num, 10, u"%s" % campo11, font_style2)
                        ws.write(row_num, 11, u"%s" % campo12, font_style2)
                        ws.write(row_num, 12, u"%s" % campo13, font_style2)
                        ws.write(row_num, 13, u"%s" % campo14, font_style2)
                        ws.write(row_num, 14, u"%s" % campo15, font_style2)
                        ws.write(row_num, 15, u"%s" % campo16, font_style2)
                        ws.write(row_num, 16, u"%s" % campo17, font_style2)
                        ws.write(row_num, 17, u"%s" % campo18, font_style2)
                        ws.write(row_num, 18, u"%s" % campo19, font_style2)
                        ws.write(row_num, 19, u"%s" % campo20, font_style2)
                        ws.write(row_num, 20, u"%s" % campo21, font_style2)
                        ws.write(row_num, 21, u"%s" % campo22, font_style2)
                        ws.write(row_num, 22, u"%s" % campo23, font_style2)
                        ws.write(row_num, 23, u"%s" % campo24, font_style2)
                        ws.write(row_num, 24, u"%s" % campo25, font_style2)
                        ws.write(row_num, 25, u"%s" % campo26, font_style2)
                        ws.write(row_num, 26, u"%s" % campo27, font_style2)
                        ws.write(row_num, 27, u"%s" % campo28, style1)
                        ws.write(row_num, 28, u"%s" % campo29, style1)
                        ws.write(row_num, 29, u"%s" % campo30, font_style2)
                        ws.write(row_num, 30, u"%s" % campo31, font_style2)
                        ws.write(row_num, 31, u"%s" % campo32, font_style2)
                        ws.write(row_num, 32, u"%s" % campo33, font_style2)
                        ws.write(row_num, 33, u"%s" % campo34, font_style2)
                        ws.write(row_num, 34, u"%s" % campo35, font_style2)
                        ws.write(row_num, 35, u"%s" % campo36, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect("/adm_horarios/examenes")
        else:
            try:
                data['title'] = u'Administración de horarios de exámenes'
                data['ePeriodo'] = periodo
                eNiveles = Nivel.objects.filter(periodo=periodo, materia__isnull=False)
                eNivelLibreCoordinaciones = NivelLibreCoordinacion.objects.filter(nivel_id__in=eNiveles.values_list("id", flat=True))
                eCoordinaciones = Coordinacion.objects.filter(pk__in=eNivelLibreCoordinaciones.values_list("coordinacion_id", flat=True))
                data['eCoordinaciones'] = eCoordinaciones
                data['eAulas'] = Aula.objects.filter(status=True)
                return render(request, "adm_horarios/examenes/view.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                return render(request, "adm_horarios/error.html", data)
