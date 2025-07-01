from _decimal import Decimal
from functools import reduce

from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render
from pdip.models import ContratoDip, ContratoCarrera
from posgrado.models import CohorteMaestria, MaestriasAdmision
from postulaciondip.models import DetalleInformeContratacion
from sga.commonviews import adduserdata
from django.db.models import Max, Min, Case, When, Value, IntegerField, Count,Sum, Q, F,Avg
from datetime import datetime

from sga.models import ProfesorMateria, Malla, Periodo, Profesor, Paralelo, Nivel, Coordinacion, Persona, \
    AsignaturaMalla
from collections import defaultdict


def obtener_fechas_inicio_fin(fecha_inicio,fecha_fin):
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta
    # Convertir las cadenas de fecha en objetos datetime
    fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
    fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
    # Calcular la diferencia en meses entre las fechas
    diferencia_meses = (fecha_fin.year - fecha_inicio.year) * 12 + fecha_fin.month - fecha_inicio.month + 1
    # Si la diferencia es 1, entonces es solo un mes
    if diferencia_meses == 1:
        return [(fecha_inicio, fecha_fin)]

    # Lista para almacenar las fechas de inicio y fin de cada mes
    fechas_inicio_fin = []

    # Iterar sobre los meses dentro del rango de fechas
    fecha_actual = fecha_inicio
    for _ in range(diferencia_meses):
        # Calcular la fecha de fin del mes actual
        fecha_fin_mes = fecha_actual + relativedelta(day=31)

        # Si la fecha de fin del mes actual es posterior a la fecha fin,
        # establecerla como la fecha fin
        if fecha_fin_mes > fecha_fin:
            fecha_fin_mes = fecha_fin

        # Agregar las fechas de inicio y fin del mes actual a la lista
        fechas_inicio_fin.append((fecha_actual, fecha_fin_mes))

        # Calcular la fecha de inicio del siguiente mes
        fecha_actual += relativedelta(months=1)
        fecha_actual = fecha_actual.replace(day=1)

    return fechas_inicio_fin


def calcular_valor_a_pagar_pago(fecha_inicio, fecha_fin, rmu):
    try:
        if fecha_inicio and fecha_fin:
            dias_transcurridos = 0
            total_pago_subtotal = 0
            total_pago_iva = 0
            valor_real_a_pagar_total = 0
            fechas_inicio_fin = obtener_fechas_inicio_fin(fecha_inicio, fecha_fin)
            for inicio, fin in fechas_inicio_fin:
                subtotal_contrato = 1086 / Decimal(1.15)
                iva_contrato = subtotal_contrato * Decimal(0.15)
                rmu_contrato = subtotal_contrato + iva_contrato
                valorporhora = subtotal_contrato / 30

                if fin.day == 31 or fin.day == 28:
                    dias_transcurridos = (fin - inicio).days
                else:
                    dias_transcurridos = (fin - inicio).days + 1

                if dias_transcurridos == 31 or (
                        inicio.month == 2 and (dias_transcurridos == 29 or dias_transcurridos == 28)):
                    dias_transcurridos = 30
                subtotal_a_pagar = round(valorporhora * dias_transcurridos, 2)
                total_pago_subtotal += subtotal_a_pagar

            total_pago_iva = round(total_pago_subtotal * Decimal(0.15) * 100) / 100
            # total_pago_iva =  round(total_pago_subtotal *Decimal(0.15), 2)
            total_a_pagar_rmu = round(float(total_pago_subtotal) + total_pago_iva, 2)
            valor_real_a_pagar_total = float(round(total_a_pagar_rmu, 1))
            if valor_real_a_pagar_total != total_a_pagar_rmu:
                if valor_real_a_pagar_total > total_a_pagar_rmu:
                    total_pago_iva = total_pago_iva + (valor_real_a_pagar_total - total_a_pagar_rmu)
                if valor_real_a_pagar_total < total_a_pagar_rmu:
                    total_pago_iva = total_pago_iva - (total_a_pagar_rmu - valor_real_a_pagar_total)

            return total_pago_subtotal, round(total_pago_iva, 2), valor_real_a_pagar_total, dias_transcurridos
        else:
            return 944.35, round(141.65, 2), 1086, 30

    except Exception as ex:
        pass


def view(request):
    data = {}
    adduserdata(request, data)
    hoy = datetime.now().date()
    data['personasesion'] = persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'coordinadores':
                try:
                    data['title'] = f'Coordinadores de maestría'
                    data['tag_active'] = 1
                    fecha = request.GET.get('fecha', '')
                    url_vars = '&action=coordinadores'
                    mes = 0
                    anio = 0
                    if fecha:
                        mes, anio = fecha.split('/')
                        mes = int(mes)  # Convierte el mes de str a int si es necesario
                        anio = int(anio)  # Convierte el año de str a int si es necesario
                        url_vars += "&fecha={}".format(fecha)
                    maestriaadmision_id = CohorteMaestria.objects.filter(periodoacademico__tipo_id=3,status=True).values_list('maestriaadmision_id', flat=True)
                    eMaestriasAdmision = MaestriasAdmision.objects.filter(status=True, id__in=maestriaadmision_id).order_by('id').exclude(pk__in=[57, 59])
                    coordinadores_contador = defaultdict(int)
                    def obtener_datos_maestria_coordinadores(e,mes,anio):
                        if e.pk== 46:
                            eCohorteMaestrias =  CohorteMaestria.objects.filter(status=True, maestriaadmision__id__in=[57, 46],periodoacademico__activo=True, periodoacademico__fin__gte=hoy, periodoacademico__inicio__lte=hoy).order_by('-id')
                            eMallas = Malla.objects.filter(carrera_id__in=[267, 236],vigente=True) if Malla.objects.filter( carrera_id__in=[267, 236], vigente=True).exists() else None
                            rmu_total_por_paralelo = rmu_total_paralelo_coordinadores(e, eCohorteMaestrias, eMallas,mes,anio)
                        else:
                            eMallas = Malla.objects.filter(carrera_id=e.carrera.pk, vigente=True) if Malla.objects.filter( carrera_id=e.carrera.pk, vigente=True).exists() else None
                            rmu_total_por_paralelo = rmu_total_paralelo_coordinadores(e, e.cohortes_maestria_activas(), eMallas,mes,anio)
                        cantidad_coordinadores = CohorteMaestria.objects.filter(status=True, maestriaadmision=e, activo=True, periodoacademico__activo=True).values_list('coordinador',flat=True).distinct()
                        eCoordinadores = Persona.objects.filter(pk__in=cantidad_coordinadores)
                        ofertada= e.ofertada()
                        eCohorteMaestrias = obtener_cohortes_coordinadores(e, eMallas,mes,anio)

                        if ofertada:
                            eContratoDip = obtener_contrato_coordinadores(e)
                            if eContratoDip:
                                coordinadores_contador[eContratoDip.pk] = eContratoDip.valortotal
                            return {
                                'eMaestriaAdmisionPk': e.pk,
                                'eCarrera': e.carrera,
                                'eMallas': eMallas,
                                'eCohorteMaestrias': eCohorteMaestrias,
                                'eContratoDip': eContratoDip ,
                                'rmu_por_total_paralelo': rmu_total_por_paralelo,
                                'eCoordinadores': eCoordinadores,
                            }
                        else:
                            return None

                    def obtener_cohortes_coordinadores(e, eMallas,mes,anio):
                        eCohorteMaestrias = e.cohortes_maestria_activas()
                        if e.pk == 46:
                            eCohorteMaestrias = eCohorteMaestrias.union(CohorteMaestria.objects.filter(status=True, maestriaadmision__id__in=[57,46], periodoacademico__activo=True,periodoacademico__fin__gte=hoy,periodoacademico__inicio__lte=hoy).order_by('-id'))
                            eMallas = Malla.objects.filter(carrera_id__in=[267,236], vigente=True) if Malla.objects.filter( carrera_id__in=[267,236], vigente=True).exists() else None
                        # Filtra las cohortes que tienen más de 0 paralelos
                        # cohortes_filtradas = filter(
                        #     lambda eCohorteMaestria: obtener_paralelos(eCohorteMaestria.periodoacademico, eMallas) > 0,
                        #     eCohorteMaestrias
                        # )

                        detalles_cohortes = list(map(lambda eCohorteMaestria: {
                            'cohorte_id': eCohorteMaestria.pk,
                            'ePeriodo': eCohorteMaestria.periodoacademico,
                            'cantidad_paralelos': (cantidad:=obtener_paralelos_coordinadores(eCohorteMaestria.periodoacademico,eMallas,mes,anio)),
                            'rmu_por_cohorte': rmu_por_cohorte_coordinadores(e,cantidad,eMallas,mes,anio),


                        }, eCohorteMaestrias))
                        return detalles_cohortes

                    def obtener_contrato_coordinadores(maestriaadmision):
                        from pdip.models import ContratoDip
                        from sga.models import CoordinadorCarrera
                        eeCoordinadorCarrera = CoordinadorCarrera.objects.filter(carrera=maestriaadmision.carrera,periodo__activo =True)
                        if eeCoordinadorCarrera:
                            eCoordinador = eeCoordinadorCarrera[0].persona
                            contrato_id = ContratoCarrera.objects.filter(status=True,carrera=maestriaadmision.carrera).values_list('contrato_id',flat=True)
                            eContrato = ContratoDip.objects.filter(status=True,pk__in =contrato_id,estado=2, cargo__nombre__icontains='COORDINADOR').order_by('-id').first()
                            return eContrato

                        return None

                    def obtener_paralelos_coordinadores(periodoacademico,eMallas,mes,anio):
                        from django.db.models.functions import ExtractMonth, ExtractYear
                        cantidad= 0
                        eNivel = Nivel.objects.filter(periodo_id=periodoacademico.pk, status=True).first()
                        if eNivel:
                            if mes == 0 or anio == 0:
                                paralelos = eNivel.materia_set.values_list('paralelo', flat=True).filter(status=True, asignaturamalla__malla__in=eMallas.values_list('id', flat=True)).distinct()
                            else:
                                paralelos = eNivel.materia_set.filter(status=True, asignaturamalla__malla_id__in=eMallas.values_list( 'id', flat=True)).annotate(
                                    inicio_mes=ExtractMonth('inicio'),
                                    inicio_anio=ExtractYear('inicio'),
                                    fin_mes=ExtractMonth('fin'),
                                    fin_anio=ExtractYear('fin')
                                ).filter(
                                    inicio_mes=mes,
                                    inicio_anio=anio
                                ).values_list('paralelo', flat=True)


                            eParalelos = Paralelo.objects.filter( nombre__in=paralelos,status=True)
                            cantidad = eParalelos.count()
                        return cantidad

                    def rmu_total_paralelo_coordinadores(maestriaadmision,eCohorteMaestrias,eMallas,mes,anio):
                        rmu = 0
                        cantidad_paralelos = 0
                        contrato = obtener_contrato_coordinadores(maestriaadmision)
                        for eCohorteMaestria in eCohorteMaestrias:
                            cantidad_paralelos += obtener_paralelos_coordinadores(eCohorteMaestria.periodoacademico, eMallas,mes,anio)

                        if contrato and cantidad_paralelos !=0:
                            rmu = round(contrato.valortotal / cantidad_paralelos, 2)
                        return rmu

                    def rmu_por_cohorte_coordinadores(e,cantidad,eMallas,mes,anio):
                        if e.pk == 46:
                            eCohorteMaestrias = CohorteMaestria.objects.filter(status=True, maestriaadmision__id__in=[57,46], periodoacademico__activo=True, periodoacademico__fin__gte=hoy, periodoacademico__inicio__lte=hoy).order_by('-id')
                            rmu_total_por_paralelo = rmu_total_paralelo_coordinadores(e, eCohorteMaestrias, eMallas,mes,anio)
                        else:
                            rmu_total_por_paralelo = rmu_total_paralelo_coordinadores(e, e.cohortes_maestria_activas(), eMallas,mes,anio)
                        if cantidad !=0:
                            return round(rmu_total_por_paralelo * cantidad, 2)
                        return 0

                    def obtener_coordinadores():
                        return dict(coordinadores_contador)

                    def obtener_rmu_total_coordinadores():
                        suma_rmu = sum(coordinadores_contador.values())
                        return round(suma_rmu,2)


                    estructura = list(filter(None, map(lambda e: obtener_datos_maestria_coordinadores(e,mes,anio), eMaestriasAdmision)))
                    estructura = sorted(estructura, key=lambda x: x['eMaestriaAdmisionPk'])
                    data['estructura'] = estructura
                    data['cantidad_coordinadores'] = obtener_coordinadores()
                    data['total_rmu'] = obtener_rmu_total_coordinadores()


                    return render(request, "finanzas/coordinadores/view.html", data)
                except Exception as ex:
                    return JsonResponse({'isSuccess': False, 'message': f'Error al generar reporte. {ex.__str__()}'})

            elif action == 'coordinadoresapoyo':
                try:
                    data['title'] = f'Coordinadores de apoyo'
                    data['tag_active'] = 2
                    fecha_inicio, fecha_fin, filtro, url_vars =  request.GET.get('fecha_inicio', ''), request.GET.get('fecha_fin', ''), Q(status=True), ''
                    url_vars = '&action=coordinadoresapoyo'
                    if fecha_inicio:
                        url_vars += "&fecha_inicio={}".format(fecha_inicio)

                    if fecha_fin:
                        url_vars += "&fecha_fin={}".format(fecha_fin)



                    # Diccionario global para contar los profesores
                    profesor_contador = defaultdict(int)


                    maestriaadmision_id = CohorteMaestria.objects.filter(periodoacademico__tipo_id=3, status=True).values_list('maestriaadmision_id',flat=True)
                    eMaestriasAdmision = MaestriasAdmision.objects.filter(status=True, id__in=maestriaadmision_id).order_by('id')


                    total_pago_subtotal, total_pago_iva, valor_real_a_pagar_total, dias_transcurridos = calcular_valor_a_pagar_pago(fecha_inicio, fecha_fin,1086)

                    def obtener_datos_maestria(e,fecha_inicio,feha_fin):
                        eMallas = Malla.objects.filter(carrera_id=e.carrera.pk,vigente=True) if Malla.objects.filter( carrera_id=e.carrera.pk,vigente=True).exists() else None
                        ofertada = e.ofertada()
                        if ofertada:
                            return {
                                'eMaestriaAdmisionPk': e.pk,
                                'eCarrera': e.carrera,
                                'eMallas': eMallas,
                                'eCohorteMaestrias': obtener_cohortes(e, eMallas, e.carrera,fecha_inicio,feha_fin),
                                'coordinadoresresumen': obtener_detalles_coordinadores(e.carrera.pk,0)

                            }
                        else:
                            return None

                    def obtener_cohortes(e, eMallas, eCarrera,fecha_inicio,feha_fin):
                        eCohorteMaestrias = e.cohortes_maestria_activas()
                        detalles_cohortes = list(map(lambda eCohorteMaestria: {
                            'cohorte_id': eCohorteMaestria.pk,
                            'ePeriodo': eCohorteMaestria.periodoacademico,
                            'eParalelos': obtener_paralelos(eCohorteMaestria.periodoacademico, eMallas, eCarrera,fecha_inicio,feha_fin),
                            'coordinadoresresumen': obtener_detalles_coordinadores(0,eCohorteMaestria.periodoacademico.pk)
                        }, eCohorteMaestrias))
                        return detalles_cohortes

                    def obtener_paralelos(periodoacademico,eMallas,eCarrera,fecha_inicio,feha_fin):
                        detalles_paralelos= None
                        eNivel = Nivel.objects.filter(periodo_id=periodoacademico.pk, status=True).first()
                        if eNivel:
                            eParalelos = Paralelo.objects.filter( nombre__in=eNivel.materia_set.values_list('paralelo', flat=True).filter(status=True, asignaturamalla__malla__in=eMallas.values_list('id',flat=True)).distinct(),status=True)
                            detalles_paralelos = list(map(lambda eParalelo: {
                                'eParalelo': eParalelo,
                                'eCoordinadores': obtener_personascoordinadorapoyo(eParalelo, eMallas, eNivel, eCarrera,fecha_inicio,feha_fin),
                            }, eParalelos))
                        return detalles_paralelos

                    def obtener_personascoordinadorapoyo(eParalelo, eMallas, eNivel, eCarrera,fecha_inicio,feha_fin):
                        from sga.models import Persona
                        eMaterias = eNivel.materia_set.filter(status=True, asignaturamalla__malla_id__in=eMallas.values_list('id',flat=True), paralelo=eParalelo.nombre)
                        if fecha_inicio and feha_fin:
                            profesor__id = ProfesorMateria.objects.filter(materia__in=eMaterias, tipoprofesor_id=8, status=True, profesor__activo=True,materia__inicio__lte=fecha_fin,  materia__fin__gte=fecha_inicio ).distinct().values_list( 'profesor__id', flat=True).filter()
                        else:
                            profesor__id = ProfesorMateria.objects.filter(materia__in=eMaterias, tipoprofesor_id=8, status=True, profesor__activo=True).distinct().values_list( 'profesor__id', flat=True).filter()
                        eProfesores = Profesor.objects.filter(pk__in=profesor__id)
                        detalles_personas = list(map(lambda eProfesor:
                                                     {'eProfesor': eProfesor,
                                                     'cantidad': obtener_conteo_profesores,
                                                     'division': obtener_conteo_profesores_division,
                                                      },
                                                     eProfesores))
                        # Actualizar el contador de profesores
                        for eProfesor in eProfesores:
                            if eProfesor.pk not in profesor_contador:
                                profesor_contador[eProfesor.pk] = {
                                    'conteo': 0,
                                    'carreras': set(),
                                    'periodos': set()
                                }

                            profesor_contador[eProfesor.pk]['conteo'] += 1
                            profesor_contador[eProfesor.pk]['carreras'].add(eCarrera.pk)
                            profesor_contador[eProfesor.pk]['periodos'].add(eNivel.periodo.pk)

                        return detalles_personas

                    def obtener_conteo_profesores():
                        return dict(profesor_contador)

                    def obtener_conteo_profesores_division():
                        # Calcula la división del valor 1086 por el conteo de temas para cada profesor
                        profesor_contador_dividido = {key: round(valor_real_a_pagar_total / details['conteo'], 2) for key, details in profesor_contador.items()}
                        return profesor_contador_dividido

                    def total_rmu():
                        cantidad = len(obtener_conteo_profesores())
                        total = valor_real_a_pagar_total * cantidad
                        return total

                    def obtener_detalles_coordinadores(carrera_id= 0,periodo_id= 0):
                        detalles_profesores = {
                            prof_id: {
                                'conteo': details['conteo'],
                                'carreras': list(details['carreras']),
                                'periodos': list(details['periodos'])
                            } for prof_id, details in profesor_contador.items()
                        }
                        cantidad_profesores_carrera = 0
                        cantidad_profesores_carrera_periodo = 0
                        # Contar cuántos profesores pertenecen a la carrera especificada

                        if carrera_id !=0:
                            cantidad_profesores_carrera = sum(1 for details in profesor_contador.values() if carrera_id in details['carreras'])
                        if periodo_id !=0:
                            cantidad_profesores_carrera_periodo = sum( 1 for details in profesor_contador.values() if periodo_id in details['periodos'])
                        return {
                            'detalles_profesores': detalles_profesores,
                            'cantidad_profesores_carrera': cantidad_profesores_carrera,
                            'cantidad_profesores_carrera_periodo': cantidad_profesores_carrera_periodo
                        }


                    estructura = list(filter(None, map(lambda e: obtener_datos_maestria(e, fecha_inicio, fecha_fin), eMaestriasAdmision)))
                    data['estructura'] = estructura
                    data['cantidad_coordinadores_apoyo'] = obtener_conteo_profesores()
                    data['total_rmu_coordinador_de_apoyo'] = total_rmu()
                    data['fecha_inicio'] = fecha_inicio
                    data['fecha_fin'] = fecha_fin
                    data['valor_real_a_pagar_total'] = valor_real_a_pagar_total

                    return render(request, "finanzas/coordinadoresapoyo/view.html", data)
                except Exception as ex:
                    return JsonResponse({'isSuccess': False, 'message': f'Error al generar reporte. {ex.__str__()}'})

            elif action == 'profesormodulo':
                try:
                    total_certificar_acumulado = Decimal('0.0')
                    data['title'] = f'Profesores de módulos'
                    data['tag_active'] = 3
                    fecha = request.GET.get('fecha', '')
                    url_vars = '&action=profesormodulo'
                    mes = 0
                    anio = 0
                    if fecha:
                        mes, anio = fecha.split('/')
                        mes = int(mes)  # Convierte el mes de str a int si es necesario
                        anio = int(anio)  # Convierte el año de str a int si es necesario
                        url_vars += "&fecha={}".format(fecha)

                    maestriaadmision_id = CohorteMaestria.objects.filter(periodoacademico__tipo_id=3,  status=True).values_list('maestriaadmision_id', flat=True)
                    eMaestriasAdmision = MaestriasAdmision.objects.filter(status=True, id__in=maestriaadmision_id).order_by('id')

                    def obtener_datos_maestria_profesormodulo(e,mes,anio):
                        eMallas = Malla.objects.filter(carrera_id=e.carrera.pk,vigente=True) if Malla.objects.filter( carrera_id=e.carrera.pk, vigente=True).exists() else None
                        ofertada = e.ofertada()
                        eCohorteMaestrias = obtener_cohortes_profesormodulo(e, eMallas,mes,anio)

                        if ofertada:
                            return {
                                'eMaestriaAdmisionPk': e.pk,
                                'eCarrera': e.carrera,
                                'eMallas': eMallas,
                                'eCohorteMaestrias': eCohorteMaestrias,
                                'programa_pac': obtener_programa_pac_instauracion_profesormodulo( e.carrera.pk)
                            }
                        else:
                            return None

                    def obtener_cohortes_profesormodulo(e, eMallas,mes,anio):
                        eCohorteMaestrias = e.cohortes_maestria_activas()
                        detalles_cohortes = list(map(lambda eCohorteMaestria: {
                            'cohorte_id': eCohorteMaestria.pk,
                            'ePeriodo': eCohorteMaestria.periodoacademico,
                            'cantidad_paralelos': (cantidad := obtener_paralelos_profesormodulo(eCohorteMaestria.periodoacademico, eMallas)),
                            'cantidad_modulos': (cantidad := obtener_modulos_malla_profesormodulo(eCohorteMaestria.periodoacademico,eMallas,mes,anio)),
                            'desgloce_modulo': desgloce_modulo_profesormodulo(eCohorteMaestria.periodoacademico,eMallas,mes,anio)

                        }, eCohorteMaestrias))
                        return detalles_cohortes


                    def obtener_paralelos_profesormodulo(periodoacademico, eMallas):
                        cantidad = 0
                        eNivel = Nivel.objects.filter(periodo_id=periodoacademico.pk, status=True).first()
                        if eNivel:
                            eParalelos = Paralelo.objects.filter(nombre__in=eNivel.materia_set.values_list('paralelo', flat=True).filter(status=True, asignaturamalla__malla_id__in = eMallas.values_list('id',flat=True)).distinct(),status=True)
                            cantidad = eParalelos.count()
                        return cantidad

                    def obtener_modulos_malla_profesormodulo(periodoacademico, eMallas, mes, anio):
                        from django.db.models.functions import ExtractMonth, ExtractYear
                        cantidad = 0
                        eNivel = Nivel.objects.filter(periodo_id=periodoacademico.pk, status=True).first()
                        if eNivel:
                            if mes == 0 or anio == 0:
                                eMaterias = eNivel.materia_set.filter(status=True, asignaturamalla__malla_id__in=eMallas.values_list( 'id', flat=True))
                            else:
                                eMaterias = eNivel.materia_set.filter(status=True,
                                                                      asignaturamalla__malla_id__in=eMallas.values_list(
                                                                          'id', flat=True)).annotate(
                                    inicio_mes=ExtractMonth('inicio'),
                                    inicio_anio=ExtractYear('inicio'),
                                    fin_mes=ExtractMonth('fin'),
                                    fin_anio=ExtractYear('fin')
                                ).filter(
                                    inicio_mes=mes,
                                    inicio_anio=anio
                                )

                            asignaturamalla_id = eMaterias.distinct().values_list('asignaturamalla_id',flat=True)
                            eAsignaturaMalla = AsignaturaMalla.objects.filter(pk__in=asignaturamalla_id)
                            cantidad = eAsignaturaMalla.count()
                        return cantidad

                    def agrupar_por_horas_profesormodulo(detalles_materia,periodoacademico,eMallas):
                        nonlocal total_certificar_acumulado
                        # Agrupar por total_horas_por_mes y contar cuántas hay en cada grupo
                        horas_por_mes_conteo = defaultdict(lambda: {'materias_ids': []})
                        cantidad_paralelo = obtener_paralelos_profesormodulo(periodoacademico, eMallas)
                        for detalle in detalles_materia:
                            horas_por_mes = detalle['total_horas_por_mes']
                            horas_por_mes_conteo[horas_por_mes]['materias_ids'].append(detalle['eMateriaPk'])
                            eDetalleInformeContratacion = DetalleInformeContratacion.objects.filter(status=True,  personalcontratar__actaparalelo__convocatoria__asignaturamalla__id__in= horas_por_mes_conteo[horas_por_mes][ 'materias_ids'],  personalcontratar__actaparalelo__convocatoria__periodo=periodoacademico)
                            horas_por_mes_conteo[horas_por_mes]['total_multiplicacion'] = horas_por_mes * len( horas_por_mes_conteo[horas_por_mes]['materias_ids'])
                            horas_por_mes_conteo[horas_por_mes]['valorhora'] = Decimal(str(eDetalleInformeContratacion.first().valor_x_hora)) if eDetalleInformeContratacion else 50.00
                            horas_por_mes_conteo[horas_por_mes]['total_certificar'] = totalcertificacion =  cantidad_paralelo * (Decimal(horas_por_mes * len( horas_por_mes_conteo[horas_por_mes]['materias_ids']))) * (Decimal(str(eDetalleInformeContratacion.first().valor_x_hora)) if eDetalleInformeContratacion else Decimal(str(50)))
                            total_certificar_acumulado += horas_por_mes_conteo[horas_por_mes]['total_certificar']
                        return horas_por_mes_conteo

                    def calcular_total_multiplicacion_profesormodulo(horas_por_mes_conteo):
                        for horas_por_mes, datos in horas_por_mes_conteo.items():
                            datos['total_multiplicacion'] = horas_por_mes * len(datos['materias_ids'])
                        return horas_por_mes_conteo

                    def desgloce_modulo_profesormodulo(periodoacademico,eMallas,mes,anio):
                        from django.db.models.functions import ExtractMonth, ExtractYear
                        from postulaciondip.models import DetalleInformeContratacion
                        eMaterias = None
                        eNivel = Nivel.objects.filter(periodo_id=periodoacademico.pk, status=True).first()
                        if eNivel:
                            if mes == 0 or anio == 0:
                                eMaterias = eNivel.materia_set.filter(status=True, asignaturamalla__malla_id__in=eMallas.values_list('id', flat=True))
                            else:
                                eMaterias = eNivel.materia_set.filter(status=True, asignaturamalla__malla_id__in=eMallas.values_list('id', flat=True)).annotate(
                                    inicio_mes=ExtractMonth('inicio'),
                                    inicio_anio=ExtractYear('inicio'),
                                    fin_mes=ExtractMonth('fin'),
                                    fin_anio=ExtractYear('fin')
                                ).filter(
                                    inicio_mes=mes,
                                    inicio_anio=anio
                                )

                            asignaturamalla_id = eMaterias.distinct().values_list('asignaturamalla_id', flat=True)
                            eAsignaturaMallas = AsignaturaMalla.objects.filter(pk__in=asignaturamalla_id)


                            detalles_materia = list(map(lambda eAsignaturaMalla: {
                                'eMateriaPk': eAsignaturaMalla.pk,
                                'eDetalleInformeContratacion': DetalleInformeContratacion.objects.filter(status=True, personalcontratar__actaparalelo__convocatoria__asignaturamalla__id = eAsignaturaMalla.pk,  personalcontratar__actaparalelo__convocatoria__periodo=periodoacademico),
                                'total_horas_por_mes': (eAsignaturaMalla.horasacdtotal),
                            }, eAsignaturaMallas))
                            # Agrupar por total_horas_por_mes
                            horas_por_mes_conteo = agrupar_por_horas_profesormodulo(detalles_materia,periodoacademico,eMallas)
                            # Calcular total_multiplicacion
                            horas_por_mes_conteo = calcular_total_multiplicacion_profesormodulo(horas_por_mes_conteo)

                            # Convertir defaultdict a dict para la salida final
                            horas_por_mes_conteo = dict(horas_por_mes_conteo)



                            return {
                                'detalles_materia': detalles_materia,
                                'horas_por_mes_conteo': horas_por_mes_conteo
                            }


                        return None

                    def obtener_programa_pac_instauracion_profesormodulo(carrera_id):
                        from inno.models import ProgramaPac
                        eProgramaPac = ProgramaPac.objects.filter(status=True,carrera_id=carrera_id)

                    def get_total_certificar():
                        return total_certificar_acumulado

                    estructura = list(filter(None, map(lambda e: obtener_datos_maestria_profesormodulo(e,mes,anio), eMaestriasAdmision)))
                    estructura = sorted(estructura, key=lambda x: x['eMaestriaAdmisionPk'])
                    data['estructura'] = estructura
                    data['total_certificar'] = get_total_certificar()

                    return render(request, "finanzas/profesormodulo/view.html", data)
                except Exception as ex:
                    return JsonResponse({'isSuccess': False, 'message': f'Error al generar reporte. {ex.__str__()}'})

        else:
            try:
                data['title'] = f'Contabilidad posgrado'
                data['tag_active'] = 0
                return render(request, "finanzas/view.html", data)
            except Exception as ex:
                pass
