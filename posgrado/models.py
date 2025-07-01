# -*- coding: UTF-8 -*-
import json
import math
import operator
import os
import random
import time
import sys
from datetime import datetime, timedelta, date
from decimal import Decimal
import PyPDF2

from dateutil import rrule
from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.contrib.sessions.models import Session
from django.db import models, transaction
from django.db.models import Sum, UniqueConstraint, F, Value
from django.db.models.functions import Coalesce

from posgrado.proccess_background import notificar_responder_encuesta_sede_graduacion_posgrado
from sga.funciones import ModeloBase, null_to_decimal, variable_valor, null_to_numeric, log, \
    remover_caracteres_tildes_unicode, remover_caracteres_especiales_unicode, elimina_tildes
from django.contrib.contenttypes.models import ContentType
from sga.models import Administrativo, Matricula, Persona, TIPO_ARCHIVO_PORSGRADO, DIAS_CHOICES, Nivel, Paralelo, Malla, \
    ProfesorMateria, Profesor, Periodo, AsignaturaMalla, Carrera, ZONA_DOMICILIO
from django.db.models import Q
unicode = str

ESTADO_REVISION = (
    (1, u"PENDIENTE"),
    (2, u"APROBADO"),
    (3, u"RECHAZADO"),
)

ESTADO_BALANCE_COSTO = (
    (0, u"Generado"),
    (1, u"Válidado por experto del area"),
)
CONTACTO_MAESTRIA = (
    (1, u"Facebook"),
    (2, u"Instagram"),
    (3, u"LinkedIn"),
    (4, u"Mail"),
    (5, u"WhatsApp"),
    (6, u"Referido por un amigo"),
    (7, u"Otro"),
)

TIPO_COBRO = (
    (1, u"SIN RUBRO"),
    (2, u"MATRICULA"),
    (3, u"COSTO TOTAL"),
)

TIPO_ARCHIVO = (
    (1, u"PDF"),
    (2, u"IMG"),
)

ESTADO_REVISION_APROBAR = (
    (2, u"APROBADO"),
    (3, u"RECHAZADO"),
)


ESTADO_SOLICITUD_MATRICULA = (
    (1, u"SOLICITADO"),
    (2, u"APROBADO"),
    (3, u"RECHAZADO"),
)

ESTADO_EXAMEN_MSC = (
    (1, u'PENDIENTE'),
    (2, u'APROBADO'),
    (3, u'RECHAZADO')
)

ESTADO_ENTREVISTA_MSC = (
    (1, u'APROBADO'),
    (2, u'RECHAZADO')
)

ESTADO_ASESOR_COMERCIAL = (
    (1, u"PENDIENTE"),
    (2, u"ASIGNADO"),
)

ESTADO_FORMA_PAGO = (
    (1, u"PENDIENTE"),
    (2, u"APROBADO"),
    (3, u"RECHAZADO"),
)

ESTADO_CONTRATO = (
    (1, u"PENDIENTE"),
    (2, u"APROBADO"),
    (3, u"RECHAZADO"),
    (4, u"EN PROCESO DE ANULACIÓN"),
    (5, u"ANULADO"),
    (6, u"OFICIO RECHAZADO"),
)

ESTADO_META = (
    (1, u"NO CUMPLIDA"),
    (2, u"CUMPLIDA"),
)

GRUPO_ROL = (
    (1, u"SIN ASIGNAR"),
    (2, u"TERRITORIO 1"),
    (3, u"TERRITORIO 2"),
    (4, u"EJECUTIVO"),
)

MOTIVO_OFICIO = (
    (0, u'---------'),
    (1, u"CAMBIO DE COHORTE"),
    (2, u"CAMBIO DE MODALIDAD DE PAGO"),
    (3, u"CAMBIO DE TABLA DE AMORTIZACIÓN"),
    (4, u"CAMBIO DE MAESTRÍA"),
    (5, u"CAMBIO DE MENCIÓN"),
)

ITINERARIO_ASIGNATURA_MALLA = (
    (0, u'---------'),
    (1, u'1'),
    (2, u'2'),
    (3, u'3')
)

ESTADO_ATENDIDO = (
    (1, u"POR ATENDER"),
    (2, u"ATENDIDO"),
)

IDENTIFICA_HOMOLOGADO = (
    (0, u'---------'),
    (1, u'INTERNA'),
    (2, u'EXTERNA'),
)

MOTIVO_RECHAZA_DESACTIVA = (
    (1, u"---------"),
    (2, u"NO APLICA POR SER BACHILLER"),
    (3, u"NO APLICA POR SER TECNÓLOGO"),
    (4, u"YA TIENE  UNA  O MAS POSTULACIONES EN OTRA MAESTRIA"),
    (5, u"SIN DINERO"),
    (6, u"CURSANDO EN OTRA UNIVERSIDAD"),
    (7, u"NO APLICA POR SU PERFIL DE PREGRADO"),
    (8, u"NO HUBO RESPUESTA DEL POSTULANTE"),
    (9, u"DESINTERÉS"),
)

#REVISION DE INFORME TITULACION POSGRADO
TIPO_PREGUNTA = (
(1, u"SI_NO"),
)

TIPO_INFORME = (
(1, u"INFORME DE REVISIÓN DEL TRABAJO DE TITULACIÓN"),
)

ESTADO_DICTAMEN = (
(1, u"EN REVISIÓN"),
(2, u"ACEPTADO SIN OBSERVACIONES, PROCEDE A SUSTENTACIÓN"),
(3, u"ACEPTADO CON MODIFICACIONES MENORES, PROCEDE A SUSTENTACIÓN"),
(4, u"DENEGADO, CON OBSERVACIONES MAYORES"),
(5, u"REPROBADO, NO CUMPLE CON LOS PARÁMETROS ESTABLECIDOS"),
)

MESES_CHOICES = (
    (1, u'Enero'),
    (2, u'Febrero'),
    (3, u'Marzo'),
    (4, u'Abril'),
    (5, u'Mayo'),
    (6, u'Junio'),
    (7, u'Julio'),
    (8, u'Agosto'),
    (9, u'Septiembre'),
    (10, u'Octubre'),
    (11, u'Noviembre'),
    (12, u'Diciembre')
)

class MaestriasAdmision(ModeloBase):
    carrera = models.ForeignKey('sga.Carrera', null=True, blank=True, verbose_name=u'Carrera', on_delete=models.CASCADE)
    descripcion = models.CharField(default='', max_length=200, verbose_name=u"Descripcion")
    enlace = models.CharField(default='https://www.unemi.edu.ec/index.php/maestrias/', max_length=500, verbose_name=u'URL de la maestria')
    cuposlibres = models.IntegerField(default=0, verbose_name=u'Cupos a vender de la maestría')


    def __str__(self):
        # return u'%s - %s' % (self.carrera, self.descripcion)
        return self.descripcion


    @staticmethod
    def ingresos_cuentas_por_cobrar_por_anio_and_carrera(anio,eCarreras):
        try:

            def obtener_presupuestado_hasta_anio_and_mes_actual(anio, mes, eCarrera):
                try:
                    from sagest.models import Rubro
                    from datetime import datetime, timedelta
                    # Calcular la última fecha del mes proporcionado
                    ultima_fecha_mes = datetime(anio, mes, 1).replace(day=28) + timedelta(days=4)  # Esto asegura que estamos en el siguiente mes
                    ultima_fecha_mes = ultima_fecha_mes.replace(day=1) - timedelta(days=1)  # Mover al último día del mes actual
                    if mes == 1:
                        presupuestado_mes_actual_pagado = Rubro.objects.filter(status=True, inscripcion__cohortes__maestriaadmision__carrera=eCarrera,fechavence__year=anio, fechavence__month=mes, saldo=0).aggregate(total_valor=Sum('valortotal'))['total_valor']
                        presupuestado_mes_actual_con_saldo = Rubro.objects.filter(status=True, inscripcion__cohortes__maestriaadmision__carrera=eCarrera, fechavence__year=anio, fechavence__month=mes, saldo__gt=0).aggregate(total_saldo=Sum('saldo'))['total_saldo']
                        valortotal = (presupuestado_mes_actual_pagado if presupuestado_mes_actual_pagado else 0) + (presupuestado_mes_actual_con_saldo if presupuestado_mes_actual_con_saldo else 0)
                    else:
                        presupuestado_mes_actual_sin_saldo_meses_anteriores =  Rubro.objects.filter(status=True, inscripcion__cohortes__maestriaadmision__carrera=eCarrera, fechavence__year=anio, fechavence__month=mes).exclude(fechavence__year=anio,fechavence__month__gte=mes,saldo=0).aggregate( total_valor=Sum('valortotal'))['total_valor']
                        presupuestado_mes_actual_con_saldo_meses_anteriores = Rubro.objects.filter(status=True, inscripcion__cohortes__maestriaadmision__carrera=eCarrera, fechavence__year=anio, fechavence__month=mes, saldo__gt=0).aggregate(total_saldo=Sum('saldo'))['total_saldo']
                        valortotal = (presupuestado_mes_actual_sin_saldo_meses_anteriores if presupuestado_mes_actual_sin_saldo_meses_anteriores else 0) + ( presupuestado_mes_actual_con_saldo_meses_anteriores if presupuestado_mes_actual_con_saldo_meses_anteriores else 0)
                    return valortotal
                except Exception as ex:
                    raise

            def obtener_presupuestado_hasta_anio_and_mes_actual_sin_incluir_este_anio_mes(anio, mes, eCarrera):
                try:
                    from sagest.models import Rubro
                    from datetime import datetime, timedelta
                    # Calcular la última fecha del mes proporcionado
                    ultima_fecha_mes = datetime(anio, mes, 1).replace(day=28) + timedelta(days=4)  # Esto asegura que estamos en el siguiente mes
                    ultima_fecha_mes = ultima_fecha_mes.replace(day=1) - timedelta(days=1)  # Mover al último día del mes actual
                    if mes == 1:
                        presupuestado_mes_actual_pagado = Rubro.objects.filter(status=True, inscripcion__cohortes__maestriaadmision__carrera=eCarrera,fechavence__lte=ultima_fecha_mes, saldo=0).exclude(fechavence__year=anio, fechavence__month=mes).aggregate(total_valor=Sum('valortotal'))['total_valor']
                        presupuestado_mes_actual_con_saldo = Rubro.objects.filter(status=True, inscripcion__cohortes__maestriaadmision__carrera=eCarrera, fechavence__lte=ultima_fecha_mes,  saldo__gt=0).exclude(fechavence__year=anio, fechavence__month=mes).aggregate(total_saldo=Sum('saldo'))['total_saldo']
                        valortotal = (presupuestado_mes_actual_pagado if presupuestado_mes_actual_pagado else 0) + (presupuestado_mes_actual_con_saldo if presupuestado_mes_actual_con_saldo else 0)
                    else:
                        presupuestado_mes_actual_sin_saldo_meses_anteriores =  Rubro.objects.filter(status=True, inscripcion__cohortes__maestriaadmision__carrera=eCarrera,fechavence__lte=ultima_fecha_mes,).exclude(fechavence__year=anio, fechavence__month=mes,fechavence__month__gte=mes,saldo=0).aggregate( total_valor=Sum('valortotal'))['total_valor']
                        presupuestado_mes_actual_con_saldo_meses_anteriores = Rubro.objects.filter(status=True, inscripcion__cohortes__maestriaadmision__carrera=eCarrera,fechavence__lte=ultima_fecha_mes, saldo__gt=0).exclude(fechavence__year=anio, fechavence__month=mes).aggregate(total_saldo=Sum('saldo'))['total_saldo']
                        valortotal = (presupuestado_mes_actual_sin_saldo_meses_anteriores if presupuestado_mes_actual_sin_saldo_meses_anteriores else 0) + ( presupuestado_mes_actual_con_saldo_meses_anteriores if presupuestado_mes_actual_con_saldo_meses_anteriores else 0)
                    return valortotal
                except Exception as ex:
                    raise

            def obtener_presupuestado_hasta_anio_and_mes_actual_acumulado(anio, mes, eCarrera):
                try:
                    from sagest.models import Rubro
                    from datetime import datetime, timedelta
                    # Calcular la última fecha del mes proporcionado
                    ultima_fecha_mes = datetime(anio, mes, 1).replace(day=28) + timedelta(days=4)  # Esto asegura que estamos en el siguiente mes
                    ultima_fecha_mes = ultima_fecha_mes.replace(day=1) - timedelta(days=1)  # Mover al último día del mes actual
                    if mes == 1:
                        presupuestado_mes_actual_pagado = Rubro.objects.filter(status=True, inscripcion__cohortes__maestriaadmision__carrera=eCarrera,fechavence__year=anio, fechavence__month=mes, saldo=0).aggregate(total_valor=Sum('valortotal'))['total_valor']
                        presupuestado_mes_actual_con_saldo = Rubro.objects.filter(status=True, inscripcion__cohortes__maestriaadmision__carrera=eCarrera, fechavence__year=anio, fechavence__month=mes, saldo__gt=0).aggregate(total_saldo=Sum('saldo'))['total_saldo']
                        valortotal = (presupuestado_mes_actual_pagado if presupuestado_mes_actual_pagado else 0) + (presupuestado_mes_actual_con_saldo if presupuestado_mes_actual_con_saldo else 0)
                    else:
                        presupuestado_mes_actual_sin_saldo_meses_anteriores =  Rubro.objects.filter(status=True, inscripcion__cohortes__maestriaadmision__carrera=eCarrera, fechavence__year=anio, fechavence__month=mes).exclude(fechavence__year=anio,fechavence__month__gte=mes,saldo=0).aggregate( total_valor=Sum('valortotal'))['total_valor']
                        presupuestado_mes_actual_con_saldo_meses_anteriores = Rubro.objects.filter(status=True, inscripcion__cohortes__maestriaadmision__carrera=eCarrera, fechavence__year=anio, fechavence__month=mes, saldo__gt=0).aggregate(total_saldo=Sum('saldo'))['total_saldo']
                        valortotal = (presupuestado_mes_actual_sin_saldo_meses_anteriores if presupuestado_mes_actual_sin_saldo_meses_anteriores else 0) + ( presupuestado_mes_actual_con_saldo_meses_anteriores if presupuestado_mes_actual_con_saldo_meses_anteriores else 0)
                    return valortotal
                except Exception as ex:
                    raise

            def obtener_presupuestado_hasta_anio_and_mes_actual_sin_incluir_este_anio_mes(anio, mes, eCarrera):
                try:
                    from sagest.models import Rubro
                    from datetime import datetime, timedelta
                    # Calcular la última fecha del mes proporcionado
                    ultima_fecha_mes = datetime(anio, mes, 1).replace(day=28) + timedelta(days=4)  # Esto asegura que estamos en el siguiente mes
                    ultima_fecha_mes = ultima_fecha_mes.replace(day=1) - timedelta(days=1)  # Mover al último día del mes actual
                    if mes == 1:
                        presupuestado_mes_actual_pagado = Rubro.objects.filter(status=True, inscripcion__cohortes__maestriaadmision__carrera=eCarrera,fechavence__lte=ultima_fecha_mes, saldo=0).exclude(fechavence__year=anio, fechavence__month=mes).aggregate(total_valor=Sum('valortotal'))['total_valor']
                        presupuestado_mes_actual_con_saldo = Rubro.objects.filter(status=True, inscripcion__cohortes__maestriaadmision__carrera=eCarrera, fechavence__lte=ultima_fecha_mes,  saldo__gt=0).exclude(fechavence__year=anio, fechavence__month=mes).aggregate(total_saldo=Sum('saldo'))['total_saldo']
                        valortotal = (presupuestado_mes_actual_pagado if presupuestado_mes_actual_pagado else 0) + (presupuestado_mes_actual_con_saldo if presupuestado_mes_actual_con_saldo else 0)
                    else:
                        presupuestado_mes_actual_sin_saldo_meses_anteriores =  Rubro.objects.filter(status=True, inscripcion__cohortes__maestriaadmision__carrera=eCarrera,fechavence__lte=ultima_fecha_mes,).exclude(fechavence__year=anio, fechavence__month=mes,fechavence__month__gte=mes,saldo=0).aggregate( total_valor=Sum('valortotal'))['total_valor']
                        presupuestado_mes_actual_con_saldo_meses_anteriores = Rubro.objects.filter(status=True, inscripcion__cohortes__maestriaadmision__carrera=eCarrera,fechavence__lte=ultima_fecha_mes, saldo__gt=0).exclude(fechavence__year=anio, fechavence__month=mes).aggregate(total_saldo=Sum('saldo'))['total_saldo']
                        valortotal = (presupuestado_mes_actual_sin_saldo_meses_anteriores if presupuestado_mes_actual_sin_saldo_meses_anteriores else 0) + ( presupuestado_mes_actual_con_saldo_meses_anteriores if presupuestado_mes_actual_con_saldo_meses_anteriores else 0)
                    return valortotal
                except Exception as ex:
                    raise

            def obtener_presupuestado_hasta_anio_and_mes_actual_acumulado(anio, mes, eCarrera):
                try:
                    from sagest.models import Rubro
                    from datetime import datetime, timedelta
                    # Calcular la última fecha del mes proporcionado
                    ultima_fecha_mes = datetime(anio, mes, 1).replace(day=28) + timedelta(days=4)  # Esto asegura que estamos en el siguiente mes
                    ultima_fecha_mes = ultima_fecha_mes.replace(day=1) - timedelta(days=1)  # Mover al último día del mes actual
                    if mes == 1:
                        presupuestado_mes_actual_pagado = Rubro.objects.filter(status=True, inscripcion__cohortes__maestriaadmision__carrera=eCarrera,fechavence__lte=ultima_fecha_mes, saldo=0).aggregate(total_valor=Sum('valortotal'))['total_valor']
                        presupuestado_mes_actual_con_saldo = Rubro.objects.filter(status=True, inscripcion__cohortes__maestriaadmision__carrera=eCarrera, fechavence__lte=ultima_fecha_mes, saldo__gt=0).aggregate(total_saldo=Sum('saldo'))['total_saldo']
                        valortotal = (presupuestado_mes_actual_pagado if presupuestado_mes_actual_pagado else 0) + (presupuestado_mes_actual_con_saldo if presupuestado_mes_actual_con_saldo else 0)
                    else:
                        presupuestado_mes_actual_sin_saldo_meses_anteriores = \
                        Rubro.objects.filter(status=True, inscripcion__cohortes__maestriaadmision__carrera=eCarrera,
                                             fechavence__lte=ultima_fecha_mes).exclude(fechavence__year=anio,
                                                                                       fechavence__month__gte=mes,
                                                                                       saldo=0).aggregate(
                            total_valor=Sum('valortotal'))['total_valor']
                        presupuestado_mes_actual_con_saldo_meses_anteriores = \
                        Rubro.objects.filter(status=True, inscripcion__cohortes__maestriaadmision__carrera=eCarrera,
                                             fechavence__year=anio, fechavence__month__gte=mes, saldo__gt=0).aggregate(
                            total_saldo=Sum('saldo'))['total_saldo']
                        valortotal = (presupuestado_mes_actual_sin_saldo_meses_anteriores if presupuestado_mes_actual_sin_saldo_meses_anteriores else 0) + (
                                         presupuestado_mes_actual_con_saldo_meses_anteriores if presupuestado_mes_actual_con_saldo_meses_anteriores else 0)
                    return valortotal
                except Exception as ex:
                    raise

            def obtener_cuentas_por_cobrar_anio_mes_actual(anio, mes, eCarrera):
                try:
                    from sagest.models import Rubro, Pago
                    valortotal = Pago.objects.filter(status=True, rubro_id__in=Rubro.objects.filter(status=True,
                                                                                                    inscripcion__cohortes__maestriaadmision__carrera=eCarrera,
                                                                                                    fecha_creacion__year=anio).values_list(
                        'id', flat=True).distinct(), fecha__year=anio, fecha__month=mes).aggregate(
                        total_valor=Sum('valortotal'))['total_valor']
                    return valortotal
                except Exception as ex:
                    raise

            def obtener_cuentas_por_cobrar_anios_anteriores(anio, mes, eCarrera):
                try:
                    from sagest.models import Rubro, Pago
                    valortotal = Pago.objects.filter(status=True, fecha__year=anio, fecha__month=mes,
                                                     rubro_id__in=Rubro.objects.filter(status=True,
                                                                                       inscripcion__cohortes__maestriaadmision__carrera=eCarrera,
                                                                                       fecha_creacion__year__lt=anio)).aggregate(
                        total_valor=Sum('valortotal'))['total_valor']
                    return valortotal
                except Exception as ex:
                    raise

            def obtener_total_pagado_anio_mes_actual(anio, mes, eCarrera):
                try:
                    from sagest.models import Rubro, Pago
                    valortotal = Pago.objects.filter(status=True, rubro_id__in=Rubro.objects.filter(status=True,
                                                                                                    inscripcion__cohortes__maestriaadmision__carrera=eCarrera).values_list(
                        'id', flat=True).distinct(), fecha__year=anio, fecha__month=mes).aggregate(
                        total_valor=Sum('valortotal'))['total_valor']
                    return valortotal
                except Exception as ex:
                    raise

            def encabezado_meses(anio, eCarrera):
                try:
                    meses = []
                    for mes in range(1, 13):
                        info = {
                            'anio': anio,
                            'numero_mes': mes,
                            'nombre_mes': MESES_CHOICES[mes - 1][1],
                            'detalle_mes': detalle_meses(anio, mes, eCarrera)
                        }
                        meses.append(info)
                    return meses

                except Exception as ex:
                    raise

            def detalle_meses(anio, mes, eCarrera):
                detalle = []
                detalle.append(
                    {
                        'cuentas_por_cobrar_anios_anteriores': obtener_cuentas_por_cobrar_anios_anteriores(anio, mes,eCarrera),
                        'cuentas_por_cobrar_anio_mes_actual': obtener_cuentas_por_cobrar_anio_mes_actual(anio, mes, eCarrera),
                        'presupuestado_anio_mes_actual': obtener_presupuestado_hasta_anio_and_mes_actual(anio, mes,eCarrera),
                        'presupuestado_anio_mes_sin_mes_actual': obtener_presupuestado_hasta_anio_and_mes_actual_sin_incluir_este_anio_mes(anio, mes,eCarrera),
                        'presupuestado_anio_hasta_mes_actual_acumulado': obtener_presupuestado_hasta_anio_and_mes_actual_acumulado(anio, mes,eCarrera),
                        'pagado': obtener_total_pagado_anio_mes_actual(anio, mes, eCarrera),
                    }
                )
                return detalle

            def ingresos_cuentas_por_cobrar_por_anio_and_carrera(eCarrera, anio):
                return {
                    'eCarrera': eCarrera,
                    'encabezado_meses': encabezado_meses(anio, eCarrera)

                }

            estructura = list(filter(None,map(lambda eCarrera: ingresos_cuentas_por_cobrar_por_anio_and_carrera(eCarrera,anio),eCarreras)))

            return estructura
        except Exception as ex:
            pass

    @staticmethod
    def generar_reporte_cuentas_por_cobrar_anio_and_excel(anio, estructura, diccionario_totales_por_mes, meses, request):
        try:
            import io
            import xlsxwriter
            from pdip.funciones import FORMATOS_CELDAS_EXCEL
            from django.http import HttpResponse
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            ws = workbook.add_worksheet()

            ftitulo1 = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo1"])
            fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])
            fcuerpo = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdanumerodecimal"])


            ws.merge_range(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo1)
            ws.merge_range(1, 0, 1, 8, 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADOS', ftitulo1)
            ws.merge_range(2, 0, 2, 8, f'CUENTAS POR COBRAR: {anio} ', ftitulo1)
            columns = [
                (u"PROGRAMA", 30),
                (u"MODALIDAD", 25),

            ]

            row_num = 4
            for col_num in range(len(columns)):
                ws.write(row_num, col_num, columns[col_num][0], fcabeceracolumna)
                ws.set_column(col_num, col_num, columns[col_num][1])

            # Escribir encabezados para los meses
            col_num += 1
            for numero, mes in meses:
                ws.merge_range(row_num, col_num, row_num, col_num + 3, mes.upper(), fcabeceracolumna)
                ws.write(row_num + 1, col_num, "CUENTAS POR COBRAR AÑOS ANTERIORES", fcabeceracolumna)
                ws.write(row_num + 1, col_num + 1, "CUENTAS POR COBRAR", fcabeceracolumna)
                ws.write(row_num + 1, col_num + 2, "PRESUPUESTADO EN EL MES", fcabeceracolumna)
                ws.write(row_num + 1, col_num + 3, "PRESUPUESTADO SIN ESTE MES", fcabeceracolumna)
                ws.write(row_num + 1, col_num + 4, "PRESUPUESTADO ACUMULADO", fcabeceracolumna)
                ws.write(row_num + 1, col_num + 5, "PAGADO", fcabeceracolumna)
                ws.set_column(col_num, col_num + 5, 20)
                col_num += 4

            # Escribir los datos del cuerpo de la tabla
            row_num += 2
            for item in estructura:
                col_num = 0
                ws.write(row_num, col_num, item['eCarrera'].nombre_completo())
                ws.write(row_num, col_num + 1, item['eCarrera'].get_modalidad_display())
                col_num += 2
                for a in item['encabezado_meses']:
                    for mes in a['detalle_mes']:
                        ws.write(row_num, col_num, mes['cuentas_por_cobrar_anios_anteriores'] if mes['cuentas_por_cobrar_anios_anteriores'] else "-")
                        ws.write(row_num, col_num + 1, mes['cuentas_por_cobrar_anio_mes_actual'] if mes['cuentas_por_cobrar_anio_mes_actual'] else "-")
                        ws.write(row_num, col_num + 2, mes['presupuestado_anio_mes_actual'] if mes['presupuestado_anio_mes_actual'] else "-")
                        ws.write(row_num, col_num + 3, mes['presupuestado_anio_mes_sin_mes_actual'] if mes['presupuestado_anio_mes_sin_mes_actual'] else "-")
                        ws.write(row_num, col_num + 4, mes['presupuestado_anio_hasta_mes_actual_acumulado'] if mes['presupuestado_anio_hasta_mes_actual_acumulado'] else "-")
                        ws.write(row_num, col_num + 5, mes['pagado'] if mes['pagado'] else "-")
                        col_num += 6
                row_num += 1

            # Añadir la fila de totales
            ws.write(row_num, 0, "Totales", fcuerpo)
            ws.write(row_num, 1, "", fcuerpo)
            col_num = 2
            for anio, meses_totales in diccionario_totales_por_mes.items():
                for mes, totales in meses_totales.items():
                    ws.write(row_num, col_num, totales['total_cuentas_por_cobrar_anios_anteriores'], fcuerpo)
                    ws.write(row_num, col_num + 1, totales['total_cuentas_por_cobrar_anio_mes_actual'], fcuerpo)
                    ws.write(row_num, col_num + 2, totales['total_presupuestado_anio_mes_actual'], fcuerpo)
                    ws.write(row_num, col_num + 3, totales['total_presupuestado_anio_mes_actual_sin_este_mes'], fcuerpo)
                    ws.write(row_num, col_num + 4, totales['total_presupuestado_anio_mes_actual_acumulado'], fcuerpo)
                    ws.write(row_num, col_num + 5, totales['total_pagado'], fcuerpo)
                    col_num += 6

            workbook.close()
            output.seek(0)
            filename = f'cuentas_por_cobrar_{anio}.xlsx'
            response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        except Exception as ex:
            raise

    def en_uso(self):
        return self.cohortemaestria_set.exists()

    def nombre_corto(self):
        return self.carrera.nombre[11:] if self.carrera.nombre[:6] == 'MAESTR' else self.carrera.nombre

    def cohortes_maestria(self):
        return CohorteMaestria.objects.filter(status=True, maestriaadmision=self).order_by('-id')

    def cohortes_maestria_abiertas(self):
        return CohorteMaestria.objects.filter(status=True, maestriaadmision=self, procesoabierto=True).order_by('-id')

    def cohortes_maestria_cerradas(self):
        return CohorteMaestria.objects.filter(status=True, maestriaadmision=self, procesoabierto=False).order_by('-id')

    def cantidad_asesores_asignados(self):
        metas = 0
        if AsesorMeta.objects.filter(status=True, maestria=self).exists():
            metas = AsesorMeta.objects.filter(status=True, maestria=self).values_list('asesor__id').order_by('asesor__id').distinct().count()
        return metas

    def cant_metas_mes(self, anio, mes):
        metas = 0
        if AsesorMeta.objects.filter(status=True, maestria=self, asesor__activo=True).exists():
            idmetas = AsesorMeta.objects.filter(status=True, maestria=self, asesor__activo=True).values_list('id', flat=True).order_by('id').distinct()
            if DetalleAsesorMeta.objects.filter(status=True, asesormeta__id__in=idmetas, inicio__month=mes, inicio__year=anio).exists():
                metas = DetalleAsesorMeta.objects.filter(status=True, asesormeta__id__in=idmetas, inicio__month=mes, inicio__year=anio).distinct().count()
        return metas

    def cant_sin_metas_mes(self, anio, mes):
        asig = self.cantidad_asesores_asignados()
        metas = 0
        if AsesorMeta.objects.filter(status=True, maestria=self, asesor__activo=True).exists():
            idmetas = AsesorMeta.objects.filter(status=True, maestria=self, asesor__activo=True).values_list('id', flat=True).order_by('id').distinct()
            if DetalleAsesorMeta.objects.filter(status=True, asesormeta__id__in=idmetas, inicio__month=mes, inicio__year=anio).exists():
                metas = DetalleAsesorMeta.objects.filter(status=True, asesormeta__id__in=idmetas, inicio__month=mes, inicio__year=anio).distinct().count()
        return asig - metas

    def lista_asesores_asignados(self):
        lista = None
        if AsesorMeta.objects.filter(status=True, maestria=self).exists():
            idase = AsesorMeta.objects.filter(status=True, maestria=self).values_list('asesor__id').order_by('asesor__id').distinct()
            lista = AsesorComercial.objects.filter(status=True, id__in=idase)
        return lista

    def ventas_maestrias_validas(self, anio, mes):
        ventas = VentasProgramaMaestria.objects.filter(status=True, inscripcioncohorte__cohortes__maestriaadmision=self, valida=True, fecha__month=mes, fecha__year=anio).count()
        return ventas

    def ventas_validas_asesor(self, anio, mes, asesor):
        ventas = VentasProgramaMaestria.objects.filter(status=True, asesor=asesor,
                                                       inscripcioncohorte__cohortes__maestriaadmision=self, valida=True, fecha__month=mes,
                                                       fecha__year=anio).count()
        return ventas

    def recaudado_maestria_format(self, anio, mes):
        from sagest.models import Rubro, Pago
        ventas = 0
        idins = VentasProgramaMaestria.objects.filter(status=True, inscripcioncohorte__cohortes__maestriaadmision=self, valida=True, fecha__month=mes, fecha__year=anio).values_list('inscripcioncohorte__id', flat=True)
        idr = Rubro.objects.filter(status=True, inscripcion__id__in=idins, inscripcion__cohortes__maestriaadmision=self).values_list('id', flat=True)
        if len(idr) > 0:
            ventas = Decimal(null_to_decimal(Pago.objects.filter(status=True, rubro__id__in=idr).aggregate(total=Sum('valortotal'))['total'], 2)).quantize(Decimal('.01'))
        return f"{ventas:,.2f}"

    def recaudado_asesor(self, anio, mes, asesor):
        from sagest.models import Rubro, Pago
        ventas = 0
        idins = VentasProgramaMaestria.objects.filter(status=True, asesor=asesor,
                                                      inscripcioncohorte__cohortes__maestriaadmision=self, valida=True, fecha__month=mes,
                                                      fecha__year=anio).values_list('inscripcioncohorte__id', flat=True)
        idr = Rubro.objects.filter(status=True, inscripcion__id__in=idins, inscripcion__cohortes__maestriaadmision=self).values_list('id', flat=True)
        if len(idr) > 0:
            ventas = Decimal(null_to_decimal(Pago.objects.filter(status=True, rubro__id__in=idr).aggregate(total=Sum('valortotal'))['total'], 2)).quantize(Decimal('.01'))
        return ventas

    def recaudado_asesor_real(self, anio, mes, asesor):
        from sagest.models import Rubro, Pago
        ventas = self.ventas_validas_asesor(anio, mes, asesor)
        valormaestria = 1
        if CohorteMaestria.objects.filter(status=True, maestriaadmision=self, valorprogramacertificado__gt=0):
            valormaestria = CohorteMaestria.objects.filter(status=True, maestriaadmision=self, valorprogramacertificado__gt=0).order_by('id').first().valorprogramacertificado
        idins = VentasProgramaMaestria.objects.filter(status=True, asesor=asesor,
                                                      inscripcioncohorte__cohortes__maestriaadmision=self, valida=True, fecha__month=mes,
                                                      fecha__year=anio).values_list('inscripcioncohorte__id', flat=True)
        idr = Rubro.objects.filter(status=True, inscripcion__id__in=idins, inscripcion__cohortes__maestriaadmision=self).values_list('id', flat=True)
        ventas = Decimal(null_to_decimal(ventas * valormaestria)).quantize(Decimal('.01'))
        return ventas

    def recaudado_maestria(self, anio, mes):
        from sagest.models import Rubro, Pago
        ventas = 0
        idins = VentasProgramaMaestria.objects.filter(status=True,
                                                      inscripcioncohorte__cohortes__maestriaadmision=self, valida=True, fecha__month=mes,
                                                      fecha__year=anio).values_list('inscripcioncohorte__id', flat=True)
        idr = Rubro.objects.filter(status=True, inscripcion__id__in=idins, inscripcion__cohortes__maestriaadmision=self).values_list('id', flat=True)
        if len(idr) > 0:
            ventas = Decimal(null_to_decimal(Pago.objects.filter(status=True, rubro__id__in=idr).aggregate(total=Sum('valortotal'))['total'], 2)).quantize(Decimal('.01'))
        return ventas

    def recaudado_maestria_real(self, anio, mes):
        from sagest.models import Rubro, Pago
        ventas = self.ventas_maestrias_validas(anio, mes)
        valormaestria = 1
        if CohorteMaestria.objects.filter(status=True, maestriaadmision=self, valorprogramacertificado__gt=0):
            valormaestria = CohorteMaestria.objects.filter(status=True, maestriaadmision=self, valorprogramacertificado__gt=0).order_by('id').first().valorprogramacertificado
        idins = VentasProgramaMaestria.objects.filter(status=True,
                                                      inscripcioncohorte__cohortes__maestriaadmision=self, valida=True, fecha__month=mes,
                                                      fecha__year=anio).values_list('inscripcioncohorte__id', flat=True)
        idr = Rubro.objects.filter(status=True, inscripcion__id__in=idins, inscripcion__cohortes__maestriaadmision=self).values_list('id', flat=True)
        ventas = Decimal(null_to_decimal(ventas * valormaestria)).quantize(Decimal('.01'))
        return ventas

    def porcentaje_cumplimiento(self, anio, mes, asesor):
        from sagest.models import Rubro, Pago
        porcentaje = 0
        ventas = self.ventas_validas_asesor(anio, mes, asesor)


        metas = DetalleAsesorMeta.objects.filter(status=True, inicio__month=mes, inicio__year=anio,
                                                 asesormeta__maestria=self, asesormeta__asesor=asesor).first().cantidad

        if ventas > 0 and metas > 0:
            # if ventas > metas:
            #     porcentaje = 100
            # else:
            tot = (ventas/metas) * 100
            porcentaje = Decimal(null_to_decimal(tot)).quantize(Decimal('.01'))
        else:
            porcentaje = 0
        return porcentaje

    def porcentaje_cumplimiento_maes(self, anio, mes):
        from sagest.models import Rubro, Pago
        porcentaje = 0
        ventas = self.ventas_maestrias_validas(anio, mes)

        metas = DetalleAsesorMeta.objects.filter(status=True, inicio__month=mes, inicio__year=anio, asesormeta__maestria=self).aggregate(total=Sum('cantidad'))['total']

        if ventas > 0 and metas > 0:
            # if ventas > metas:
            #     porcentaje = 100
            # else:
            tot = (ventas/metas) * 100
            porcentaje = Decimal(null_to_decimal(tot)).quantize(Decimal('.01'))
        else:
            porcentaje = 0
        return porcentaje

    def tiene_metas_mes(self, anio, mes):
        estado = False
        if AsesorMeta.objects.filter(status=True, maestria=self).exists():
            idmetas = AsesorMeta.objects.filter(status=True, maestria=self).values_list('id', flat=True).order_by('id').distinct()
            if DetalleAsesorMeta.objects.filter(status=True, asesormeta__id__in=idmetas, inicio__month=mes, inicio__year=anio).exists():
                estado = True
        return estado

    def ids_cabecerameta(self):
        try:
            lista = None
            if AsesorMeta.objects.filter(status=True, maestria=self).exists():
                lista = AsesorMeta.objects.filter(status=True, maestria=self).values_list('id', flat=True).order_by('id').distinct()
            return list(lista) if lista != None else lista
        except Exception as ex:
            pass

    def total_metas(self):
        deta = 0
        if AsesorMeta.objects.filter(status=True, maestria=self).exists():
            lista = AsesorMeta.objects.filter(status=True, maestria=self).values_list('id', flat=True).order_by('id').distinct()
            deta = DetalleAsesorMeta.objects.filter(status=True, asesormeta__id__in=lista).aggregate(total=Sum('cantidad'))['total']
        return deta

    def total_metas_mes(self, mes, anio):
        deta = 0
        if DetalleAsesorMeta.objects.filter(status=True, inicio__month=mes, inicio__year=anio, asesormeta__maestria=self).exists():
            deta = DetalleAsesorMeta.objects.filter(status=True, inicio__month=mes, inicio__year=anio, asesormeta__maestria=self).aggregate(total=Sum('cantidad'))['total']
        return deta

    def sobrante(self, mes, anio):
        cupos = CuposMaestriaMes.objects.get(status=True, maestria=self, inicio__month=mes, inicio__year=anio)
        result = cupos.cuposlibres - self.total_metas_mes(mes, anio)
        return result

    def ofertada(self):
        hoy = datetime.now().date()
        estado = False
        if CohorteMaestria.objects.values('id').filter(maestriaadmision=self, fechainicioinsp__lte=hoy,
                                                       fechafininsp__gte=hoy, activo=True, status=True).exists():
            estado = True

        elif CohorteMaestria.objects.values('id').filter(maestriaadmision=self, fechainiciorequisito__lte=hoy,
                                                        fechafinrequisito__gte=hoy, activo=True, status=True).exists():
            estado = True

        elif CohorteMaestria.objects.values('id').filter(maestriaadmision=self, fechainiciocohorte__lte=hoy,
                                                        fechafincohorte__gte=hoy, activo=True, status=True).exists():
            estado = False
        return estado

    def menciones(self):
        from sga.models import ItinerarioMallaEspecilidad
        malla = self.carrera.malla()
        return ItinerarioMallaEspecilidad.objects.filter(malla=malla, status=True)

    def tiene_requisitos_homologacion(self):
        return True if RequisitosMaestria.objects.filter(status=True, maestria=self) else False

    class Meta:
        verbose_name = u"MaestriasAdmisiones"
        verbose_name_plural = u"MaestriasAdmision"
        ordering = ['descripcion']
        unique_together = ('descripcion',)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(MaestriasAdmision, self).save(*args, **kwargs)

    def cohortes_maestria_activas(self):
        hoy = datetime.now().date()
        return CohorteMaestria.objects.filter(status=True, maestriaadmision=self, periodoacademico__activo=True,periodoacademico__fin__gte=hoy,periodoacademico__inicio__lte=hoy).order_by('-id')

    def get_profesor_materia_coordindadores_de_apoyo(self,periodo_id,desde,hasta):
        eProfesorMateria = ProfesorMateria.objects.filter(status=True, tipoprofesor_id=8 ,materia__nivel__periodo_id=periodo_id, desde__lte=desde, hasta__lte=hasta)

class TablaEntrevistaMaestria(ModeloBase):
    nombre = models.CharField(default='', max_length=250, verbose_name=u'Nombre de tabla')
    estado = models.BooleanField(default=True, verbose_name=u'Estado')

    def __str__(self):
        return u'%s' % self.nombre

    def mi_detalle(self):
        if self.estadoentrevista_set.filter(status=True).exists():
            return self.estadoentrevista_set.filter(status=True)
        return None

    def tabla_seleccionada(self, cohorte):
        return True if self.cohortemaestria_set.filter(status=True, pk=int(cohorte)).exists() else False

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(TablaEntrevistaMaestria, self).save(*args, **kwargs)


class EstadoEntrevista(ModeloBase):
    tablaentrevista = models.ForeignKey(TablaEntrevistaMaestria, blank=True, null=True, verbose_name=u'Tabla', on_delete=models.CASCADE)
    observacion = models.TextField(default='', verbose_name=u'Observación')
    ponderacion = models.FloatField(blank=True, null=True, verbose_name=u'Ponderación')
    # estado = models.IntegerField(choices=ESTADO_ENTREVISTA_MSC, default=1, verbose_name=u'Estado')

    def __str__(self):
        return u'%s' % self.observacion

    def esta_uso(self):
        return True if self.integrantegrupoentrevitamsc_set.all().exists() else False

    def save(self, *args, **kwargs):
        self.observacion = self.observacion.upper()
        super(EstadoEntrevista, self).save(*args, **kwargs)

TIPO_COHORTE = (
    (1, "EXAMEN Y ENTREVISTA"),
    (2, "EXAMEN"),
    (3, "APROBACIÓN DE REQUISITOS"),
)


class CohorteMaestria(ModeloBase):
    descripcion = models.CharField(default='', max_length=200, verbose_name=u"Nombre")
    maestriaadmision = models.ForeignKey(MaestriasAdmision, null=True, blank=True, verbose_name=u'Materia', on_delete=models.CASCADE)
    modalidad = models.ForeignKey('sga.Modalidad', null=True, blank=True, verbose_name=u'Modalidad', on_delete=models.CASCADE)
    tablaentrevista = models.ForeignKey(TablaEntrevistaMaestria, null=True, blank=True, verbose_name=u'Tabla ponderacion entrevista', on_delete=models.CASCADE)
    alias = models.CharField(default='', max_length=100, verbose_name=u"Alias")
    numerochorte = models.IntegerField(default=0, verbose_name=u'Numero de cohorte')
    cupodisponible = models.IntegerField(default=0, verbose_name=u'cupos disponibles de ingreso')
    cantidadgruposexamen = models.IntegerField(default=0, verbose_name=u'Numero de grupos de examen')
    fechainiciocohorte = models.DateField(verbose_name=u"Fecha Inicio cohorte", null=True, blank=True)
    fechafincohorte = models.DateField(verbose_name=u"Fecha Fin cohorte", null=True, blank=True)
    fechainicioinsp = models.DateField(verbose_name=u"Fecha Inicio de cohorte", null=True, blank=True)
    fechafininsp = models.DateField(verbose_name=u"Fecha Fin de cohorte", null=True, blank=True)
    fechainicioextraordinariainsp = models.DateField(verbose_name=u"Fecha inicio extraordinaria de cohorte", null=True, blank=True)
    fechafinextraordinariainsp = models.DateField(verbose_name=u"Fecha Fin extraordinaria de cohorte", null=True, blank=True)
    fechainiciorequisito = models.DateField(verbose_name=u"Fecha Inicio Requisito", null=True, blank=True)
    fechafinrequisito = models.DateField(verbose_name=u"Fecha Fin Requisito", null=True, blank=True)
    fechafinrequisitobeca = models.DateField(verbose_name=u'Fecha fin requisitos de beca', blank=True, null=True)
    fechainicioexamen = models.DateField(verbose_name=u"Fecha inicio examen", null=True, blank=True)
    fechafinexamen = models.DateField(verbose_name=u"Fecha fin examen", null=True, blank=True)
    notaminimaexa = models.FloatField(default=0, verbose_name=u'Nota minima de examen')
    notamaximaexa = models.FloatField(default=0, verbose_name=u'Nota maxima de examen')
    notaminimatest = models.FloatField(default=0, verbose_name=u'Nota minima de test')
    notamaximatest = models.FloatField(default=0, verbose_name=u'Nota maxima test')
    ponderacionminimaentrevista = models.FloatField(default=0, verbose_name=u'Ponderación minima de la entrevista')
    ponderacionmaximaentrevista = models.FloatField(default=0, verbose_name=u'Ponderación maxima de la entrevista')
    tienecostoexamen = models.BooleanField(default=False, verbose_name=u"Tiene costo el examen")
    valorexamen = models.FloatField(default=0, verbose_name=u'Valor del exámen')
    tienecostomatricula = models.BooleanField(default=False, verbose_name=u"Tiene costo la matricula")
    valormatricula = models.FloatField(null=True, blank=True, verbose_name=u'Valor del mátricula')
    tienecuota = models.BooleanField(default=False, verbose_name=u"Tiene cuotas")
    numerocuota = models.IntegerField(null=True, blank=True, verbose_name=u'Numero de cuotas de la maestria')
    valorcuota = models.FloatField(null=True, blank=True, verbose_name=u'Valor de la cuota de la maestria')
    activo = models.BooleanField(default=True, verbose_name=u"Activo")
    tienecostotramite = models.BooleanField(default=False, verbose_name=u"Tiene costo trámite")
    valortramite = models.FloatField(null=True, blank=True, verbose_name=u'Valor del trámite')
    cantidadgruposentrevista = models.IntegerField(default=0,null=True, blank=True, verbose_name=u'Numero de grupos de entrevista')
    minutosrango = models.IntegerField(default=0, verbose_name=u'Cada cuanto minutos son de entrevista por entrevistado')
    archivomatriz = models.FileField(upload_to='archivomatriz/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo')
    totaladmitidoscohorte = models.IntegerField(default=0, verbose_name=u'Total admitidos por cohorte')
    coordinador = models.ForeignKey('sga.Persona', null=True, blank=True, verbose_name=u'Persona', on_delete=models.CASCADE)
    urlmoodle = models.CharField(default='https://aulaposgrado.unemi.edu.ec/', max_length=500, verbose_name=u'url moodle pregrado presencial y virtual')
    keymoodle = models.CharField(default='65293afed416ee1dc5dd1b137c35f03d', max_length=500, verbose_name=u'key moodle')
    procesoabierto = models.BooleanField(default=True, verbose_name=u"Si el proceso esta abierto o no")
    tienecostototal = models.BooleanField(default=False, verbose_name=u"Cuando se genera el rubro total del valor completo para la maestría y no tienen valor de matrícula")
    valorprograma = models.FloatField(default=0, verbose_name=u'Valor total del programa')
    tiporubro = models.ForeignKey('sagest.TipoOtroRubro', blank=True, null=True, verbose_name=u"Tipo", on_delete=models.CASCADE)
    fechavencerubro = models.DateField(verbose_name=u"Fecha vence  rubro", null=True, blank=True)
    observacionrubro = models.TextField(blank=True, null=True, verbose_name=u"Observación rubro")
    fechainiordinaria = models.DateField(verbose_name=u"Fecha inicio matricula ordinaria", null=True, blank=True)
    fechafinordinaria = models.DateField(verbose_name=u"Fecha fin matricula ordinaria", null=True, blank=True)
    fechainiextraordinaria = models.DateField(verbose_name=u"Fecha inicio matricula extraordinaria", null=True, blank=True)
    fechafinextraordinaria = models.DateField(verbose_name=u"Fecha fin matricula extraordinaria", null=True, blank=True)
    valorprogramacertificado = models.FloatField(default=0, verbose_name=u'Valor total del programa para certificado')
    presupuestobeca = models.FloatField(default=0, verbose_name=u'Monto presupuesto para becas')
    tipo = models.IntegerField(choices=TIPO_COHORTE, default=1, verbose_name=u'Estado Email evidencia')
    cuposlibres = models.IntegerField(default=0, verbose_name=u'Cupos libres de la cohorte')
    periodoacademico = models.ForeignKey('sga.Periodo', verbose_name=u'Periodo académico', on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return u'%s - %s' % (self.maestriaadmision.descripcion, self.descripcion)

    def en_uso(self):
        return self.requisitosmaestria_set.exists()

    def idnumber(self):
        anoini = self.fechainiciocohorte.year
        anofin = self.fechafincohorte.year
        if anoini != anofin:
            ano = '%s-%s' % (anoini, anofin)
        else:
            ano = '%s' % anoini
        return u'COHORTE%s-%s' % (self.id, ano)

    def puederevisar(self):
        hoy = datetime.now().date()
        if hoy > self.fechafinrequisito:
            return True
        else:
            return False

    def listadorequisitocohorte(self):
        return self.requisitosmaestria_set.filter(status=True).order_by('id')

    def tiene_gruporequisitos(self):
        return self.gruporequisitocohorte_set.filter(status=True)

    def existe_sinproceso(self):
        return self.integrantegrupoentrevitamsc_set.filter(status=True).exists()

    def gruporequisitos(self):
        return self.gruporequisitocohorte_set.filter(status=True)

    def tiene_requisitos(self):
        return self.requisitosmaestria_set.filter(status=True)

    def total_inscritos(self):
        return self.inscripcioncohorte_set.values('id').filter(status=True).count()

    def total_inscritossinnotificar(self):
        return self.inscripcioncohorte_set.values('id').filter(estado_emailevidencia=1, status=True).count()

    def listapreguntas(self,tipo):
        return self.preguntamaestria_set.filter(pregunta__tipopregunta=tipo,status=True)

    def total_preguntas(self):
        return self.preguntamaestria_set.values('id').filter(status=True).count()

    def total_requisitos(self):
        return self.requisitosmaestria_set.values('id').filter(status=True).count()

    def costo_maestria(self):
        if self.tienecuota:
            return null_to_decimal((self.numerocuota * self.valorcuota),2)
        return None

    def totalcosto_maestria(self):
        if self.tienecuota:
            return null_to_decimal((self.numerocuota * self.valorcuota + self.valorexamen + self.valormatricula),2)
        return None

    def puede_subir_requisitos(self):
        fecha = datetime.now().date()
        return True if CohorteMaestria.objects.filter(status=True, pk=self.id, fechainiciorequisito__lte=fecha, fechafinrequisito__gte=fecha).exists() else False

    def total_evidencia_cohorte(self):
        return self.requisitosmaestria_set.values('id').filter(status=True).count()

    def tiene_grupoexamen(self):
        return self.grupoexamenmsc_set.filter(status=True)

    def cant_requisitos(self):
        return self.requisitosmaestria_set.values('id').filter(status=True).count()

    def puede_editar_prespuestobecas(self):
        return not self.inscripcioncohorte_set.values('id').filter(status=True, tipobeca__isnull=False, descuentoposgradomatricula__estado__in=[2, 4]).exists()

    def valor_utilizado_presupuestobecas(self):
        from sga.models import DescuentoPosgradoMatricula
        utilizado = null_to_decimal(DescuentoPosgradoMatricula.objects.filter(inscripcioncohorte__cohortes=self, status=True, estado__in=[2, 4, 8, 10]).aggregate(totalutilizado=Sum('valordescuento'))['totalutilizado'], 2)
        return utilizado

    def saldo_disponible_presupuestobecas(self):
        # from sga.models import DescuentoPosgradoMatricula
        # utilizado = null_to_decimal(DescuentoPosgradoMatricula.objects.filter(inscripcioncohorte__cohortes=self, status=True, estado__in=[2, 4]).aggregate(totalutilizado=Sum('valordescuento'))['totalutilizado'], 2)
        # return Decimal(self.presupuestobeca).quantize(Decimal('.01')) - utilizado
        return self.presupuestobeca - self.valor_utilizado_presupuestobecas()

    def total_recaudado_maestria(self, anio):
        from sagest.models import Rubro, Pago
        try:
            total_recaudado = 0
            listado_admitidos_pagos = []

            idadmitidos = InscripcionCohorte.objects.filter(status=True, cohortes__id=self.id).values_list('id', flat=True)

            for idadmitido in idadmitidos:
                if Rubro.objects.filter(inscripcion__id=idadmitido, status=True).exists():
                    admitido = InscripcionCohorte.objects.get(pk=idadmitido)
                    rubrocohorte = Rubro.objects.get(inscripcion=admitido)
                    costomaestria = admitido.cohortes.valorprogramacertificado

                    cantinscripciones = InscripcionCohorte.objects.filter(inscripcionaspirante__id=admitido.inscripcionaspirante.id).count()

                    if costomaestria > 0:
                        diezporciento = costomaestria * 0.10

                        if costomaestria == rubrocohorte.valor:
                            valorpagado = admitido.total_pagado_cohorte()
                        else:
                            if cantinscripciones > 1:
                                valorpagado = admitido.total_pagado_cohorte()
                            else:
                                valorpagado = admitido.inscripcionaspirante.persona.total_pagado_maestria()

                        if valorpagado >= diezporciento:
                            if anio != 0:
                                if Pago.objects.filter(rubro__inscripcion__id=admitido.id, fecha__year=anio).order_by('id').exists():
                                    pago = Pago.objects.filter(rubro__inscripcion__id=admitido.id, fecha__year=anio).order_by('id').first()
                                    listado_admitidos_pagos.append(pago.rubro.inscripcion.id)
                            else:
                                listado_admitidos_pagos.append(admitido.id)

            ventas = Rubro.objects.filter(status=True, inscripcion_id__in=listado_admitidos_pagos)

            for venta in ventas:
                if venta.matricula:
                    tot_venta = venta.matricula.total_pagado_alumno_rubro_maestria()
                else:
                    tot_venta = null_to_numeric(
                        Pago.objects.filter(rubro__persona=venta.persona, status=True, rubro__tipo__tiporubro=1).exclude(pagoliquidacion__isnull=False).exclude(
                            factura__valida=False).aggregate(valor=Sum('valortotal'))['valor'])

                total_recaudado += tot_venta

            return total_recaudado
        except Exception as ex:
            pass

    def total_por_recaudar_maestria(self, anio):
        from sagest.models import Pago, Rubro
        try:
            total_maestria = 0
            listado_admitidos_pagos = []

            idadmitidos = InscripcionCohorte.objects.filter(status=True, cohortes__id=self.id).values_list('id', flat=True)

            for idadmitido in idadmitidos:
                if Rubro.objects.filter(inscripcion__id=idadmitido, status=True).exists():
                    admitido = InscripcionCohorte.objects.get(pk=idadmitido)
                    rubrocohorte = Rubro.objects.get(inscripcion=admitido)
                    costomaestria = admitido.cohortes.valorprogramacertificado

                    cantinscripciones = InscripcionCohorte.objects.filter(inscripcionaspirante__id=admitido.inscripcionaspirante.id).count()

                    if costomaestria > 0:
                        diezporciento = costomaestria * 0.10

                        if costomaestria == rubrocohorte.valor:
                            valorpagado = admitido.total_pagado_cohorte()
                        else:
                            if cantinscripciones > 1:
                                valorpagado = admitido.total_pagado_cohorte()
                            else:
                                valorpagado = admitido.inscripcionaspirante.persona.total_pagado_maestria()

                        if valorpagado >= diezporciento:
                            if anio != 0:
                                if Pago.objects.filter(rubro__inscripcion__id=admitido.id, fecha__year=anio).order_by('id').exists():
                                    pago = Pago.objects.filter(rubro__inscripcion__id=admitido.id, fecha__year=anio).order_by('id').first()
                                    listado_admitidos_pagos.append(pago.rubro.inscripcion.id)
                            else:
                                listado_admitidos_pagos.append(admitido.id)

            ventas = Rubro.objects.filter(status=True, inscripcion_id__in=listado_admitidos_pagos)

            for venta in ventas:
                tot_venta = venta.inscripcion.cohortes.valorprogramacertificado

                total_maestria += tot_venta

            por_recaudar =  total_maestria - float(self.total_recaudado_maestria(anio))

            return por_recaudar
        except Exception as ex:
            pass

    def total_admitidos_maestria(self):
        from sagest.models import Rubro

        idadmitidos = InscripcionCohorte.objects.filter(status=True, cohortes__id=self.id).values_list('id', flat=True)

        admitidos = Rubro.objects.filter(status=True, admisionposgradotipo__in=[2, 3],
                                                          inscripcion_id__in=idadmitidos).count()

        return admitidos

    def total_maestrantes(self):
        from sagest.models import Rubro

        listado_admitidos_pagos = []
        idadmitidos = InscripcionCohorte.objects.filter(status=True, cohortes__id=self.id).values_list('id', flat=True)

        for idadmitido in idadmitidos:
            if Rubro.objects.filter(inscripcion__id=idadmitido, status=True).exists():
                admitido = InscripcionCohorte.objects.get(pk=idadmitido)
                rubrocohorte = Rubro.objects.get(inscripcion=admitido)
                costomaestria = admitido.cohortes.valorprogramacertificado

                cantinscripciones = InscripcionCohorte.objects.filter(inscripcionaspirante__id=admitido.inscripcionaspirante.id).count()

                if costomaestria > 0:
                    diezporciento = costomaestria * 0.10

                    if costomaestria == rubrocohorte.valor:
                        valorpagado = admitido.total_pagado_cohorte()
                    else:
                        if cantinscripciones > 1:
                            valorpagado = admitido.total_pagado_cohorte()
                        else:
                            valorpagado = admitido.inscripcionaspirante.persona.total_pagado_maestria()

                    if valorpagado >= diezporciento:
                        listado_admitidos_pagos.append(admitido.id)

        maestrantes = Rubro.objects.filter(status=True, admisionposgradotipo__in=[2, 3],
                                                          inscripcion_id__in=listado_admitidos_pagos).count()

        return maestrantes

    def total_registrados(self):
        return InscripcionCohorte.objects.filter(status=True, cohortes=self).count()

    def tiene_requisitos_comercializacion(self):
        return True if RequisitosMaestria.objects.filter(status=True, cohorte=self, obligatorio=True, requisito__claserequisito__clasificacion__id=3).exists() else False

    def ventas_cohortes_facturadas(self, desde, hasta):
        ventas = VentasProgramaMaestria.objects.filter(status=True, inscripcioncohorte__cohortes=self, facturado=True, fecha__range=(desde, hasta)).count()
        return ventas

    def ventas_cohortes_reportadas(self, desde, hasta):
        ventas = VentasProgramaMaestria.objects.filter(status=True, inscripcioncohorte__cohortes=self, facturado=False, fecha__range=(desde, hasta)).count()
        return ventas

    def ventas_cohortes_rechazadas(self, desde, hasta):
        ventas = VentasProgramaMaestria.objects.filter(status=True, inscripcioncohorte__cohortes=self, valida=False, fecha__range=(desde, hasta)).count()
        return ventas

    def ventas_cohortes_validas(self, desde, hasta):
        ventas = VentasProgramaMaestria.objects.filter(status=True, inscripcioncohorte__cohortes=self, valida=True, fecha__range=(desde, hasta)).count()
        return ventas

    def cantidad_asesores_asignados(self):
        metas = 0
        if AsesorMeta.objects.filter(status=True, cohorte=self).exists():
            metas = AsesorMeta.objects.filter(status=True, cohorte=self).values_list('asesor__id').order_by('asesor__id').distinct().count()
        return metas

    def cantidad_asesores_asignados_ina(self):
        metas = 0
        if AsesorMeta.objects.filter(status=True, cohorte=self, asesor__activo=False).exists():
            metas = AsesorMeta.objects.filter(status=True, cohorte=self, asesor__activo=False).values_list('asesor__id', flat=True).order_by('asesor__id').distinct().count()
        return metas

    def cantidad_asesores_asignados_act(self):
        metas = 0
        if AsesorMeta.objects.filter(status=True, cohorte=self, asesor__activo=True).exists():
            metas = AsesorMeta.objects.filter(status=True, cohorte=self, asesor__activo=True).values_list('asesor__id', flat=True).order_by('asesor__id').distinct().count()
        return metas

    def cant_metas_mes(self, anio, mes):
        metas = 0
        if AsesorMeta.objects.filter(status=True, cohorte=self, asesor__activo=True).exists():
            idmetas = AsesorMeta.objects.filter(status=True, cohorte=self, asesor__activo=True).values_list('id', flat=True).order_by('id').distinct()
            if DetalleAsesorMeta.objects.filter(status=True, asesormeta__id__in=idmetas, inicio__month=mes, inicio__year=anio).exists():
                metas = DetalleAsesorMeta.objects.filter(status=True, asesormeta__id__in=idmetas, inicio__month=mes, inicio__year=anio).distinct().count()
        return metas

    def cant_sin_metas_mes(self, anio, mes):
        asig = self.cantidad_asesores_asignados()
        metas = 0
        if AsesorMeta.objects.filter(status=True, cohorte=self, asesor__activo=True).exists():
            idmetas = AsesorMeta.objects.filter(status=True, cohorte=self, asesor__activo=True).values_list('id', flat=True).order_by('id').distinct()
            if DetalleAsesorMeta.objects.filter(status=True, asesormeta__id__in=idmetas, inicio__month=mes, inicio__year=anio).exists():
                metas = DetalleAsesorMeta.objects.filter(status=True, asesormeta__id__in=idmetas, inicio__month=mes, inicio__year=anio).distinct().count()
        return asig - metas

    def tiene_metas_mes(self, anio, mes):
        estado = False
        if AsesorMeta.objects.filter(status=True, cohorte=self).exists():
            idmetas = AsesorMeta.objects.filter(status=True, cohorte=self).values_list('id', flat=True).order_by('id').distinct()
            if DetalleAsesorMeta.objects.filter(status=True, asesormeta__id__in=idmetas, inicio__month=mes, inicio__year=anio).exists():
                estado = True
        return estado

    class Meta:
        verbose_name = u"CohorteMaestria"
        verbose_name_plural = u"CohorteMaestriaes"
        ordering = ['maestriaadmision']

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        self.alias = self.alias.upper()
        super(CohorteMaestria, self).save(*args, **kwargs)


class InscripcionAspirante(ModeloBase):
    persona = models.ForeignKey('sga.Persona', verbose_name=u'Persona', on_delete=models.CASCADE)
    cohortes = models.ForeignKey(CohorteMaestria, blank=True, null=True, verbose_name=u'Maestria periodo', on_delete=models.CASCADE)
    titulograduado = models.CharField(default='', max_length=500, verbose_name=u'Titulo graduado')
    titulouniversidad = models.CharField(default='', max_length=500, verbose_name=u'Como se informo')
    activo = models.BooleanField(default=True, verbose_name=u"Activo")

    def __str__(self):
        return u'%s' % self.persona

    def segunda_inscripcion(self):
        return True if InscripcionCohorte.objects.filter(status=True, inscripcionaspirante=self, doblepostulacion=True).exists() else False

class ConfigFinanciamientoCohorte(ModeloBase):
    descripcion = models.TextField(blank=True, null=True, verbose_name=u"Descripción")
    cohorte = models.ForeignKey(CohorteMaestria, null=True, blank=True, verbose_name=u'Cohorte Maestria', on_delete=models.CASCADE)
    valormatricula = models.FloatField(default=0, blank=True, null=True, verbose_name=u'Valor Matricula')
    valorarancel = models.FloatField(default=0, blank=True, null=True, verbose_name=u'Valor Arancel')
    valortotalprograma = models.FloatField(default=0, blank=True, null=True, verbose_name=u'Valor total del programa')
    porcentajeminpagomatricula = models.FloatField(default=0, blank=True, null=True, verbose_name=u'Porcentaje mín pago matrícula')
    porcentajedescuentoconvenio = models.FloatField(default=0, blank=True, null=True, verbose_name=u'Porcentaje descuento convenio')
    maxnumcuota = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Máx número de cuotas')
    fecha = models.DateField(verbose_name=u"Fecha corte de cuotas", null=True, blank=True)

    def __str__(self):
        return f'{self.descripcion} - {self.porcentajeminpagomatricula}% - {self.maxnumcuota} cuotas'
        # return u'%s - %s - %s' % (self.descripcion, str(self.porcentajeminpagomatricula), str(self.maxnumcuota))
        # return u'%s' % self.descripcion

    class Meta:
        verbose_name = u'Configuración Financiamiento Cohorte'
        verbose_name_plural = u'Configuraciones Financiamiento Cohorte'
        ordering = ('id',)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(ConfigFinanciamientoCohorte,self).save(*args, **kwargs)

    def tablaamortizacioncohortemaestria(self, insc, hoy):
        tablaamortizacion = []
        porcentajedesc = 0
        valorarancel = 0
        valordescuento = 0
        maxnumcuota = self.maxnumcuota
        valortotalprograma = Decimal(null_to_decimal(self.valortotalprograma, 2)).quantize(Decimal('.01'))
        porcentajemae = Decimal(null_to_decimal(self.porcentajeminpagomatricula, 2)).quantize(Decimal('.01'))
        valormatricula = Decimal(null_to_decimal((valortotalprograma * porcentajemae) / 100, 2)).quantize(Decimal('.01'))
        if self.porcentajedescuentoconvenio > 0:
            porcentajedesc = Decimal(null_to_decimal(self.porcentajedescuentoconvenio, 2)).quantize(Decimal('.01'))
            valordescuento = Decimal(null_to_decimal((valortotalprograma * porcentajedesc) / 100, 2)).quantize(Decimal('.01'))
        valorarancel = valortotalprograma - valormatricula
        fechainiciopago = hoy
        fechavence = self.fecha

        # Registro de pago inicial, matricula
        tablaamortizacion += [('', '', '', valormatricula, valorarancel)]

        # Generacion de cuotas convertir la fecha
        dia = int(fechavence.day)
        mes = int(fechavence.month)
        anio = int(fechavence.year)
        bandera = 0
        valorcuota = 0
        valordescontado = 0
        valorpendiente = 0
        ultimo_dia = int(fechavence.day)

        # Generacion de la primera cuota aplicando porcentaje de la cuota inicial
        for n in range(maxnumcuota):
            if bandera == 0:
                fechavence = date(anio, mes, dia)
                if self.porcentajedescuentoconvenio > 0:
                    valorcuota = Decimal(null_to_decimal((valorarancel-valordescuento) / maxnumcuota)).quantize(Decimal('.01'))
                else:
                    valorcuota = Decimal(null_to_decimal(valorarancel / maxnumcuota)).quantize(Decimal('.01'))
                valorpendiente = valorarancel - valorcuota
                tablaamortizacion += [(n+1, fechainiciopago, fechavence, valorcuota, valorpendiente)]
                valordescontado = valorcuota + valorcuota
                valorpendiente = valorarancel - valordescontado
                bandera = 1
                mes += 1
                if mes == 13:
                    mes = 1
                    anio += 1
            else:
                salio = True
                d = 0
                while salio:
                    try:
                        fechavence = date(anio, mes, dia - d)
                        salio = False
                    except:
                        salio = True
                    d += 1
                mes += 1
                if mes == 13:
                    mes = 1
                    anio += 1
                if n == maxnumcuota-1:
                    # Generacion de cuota final para evitar perder decimales(centavo$)
                    if self.porcentajedescuentoconvenio > 0:
                        valorfinal = Decimal(null_to_decimal(valorarancel-valordescuento)).quantize(Decimal('.01')) - (valorcuota * (maxnumcuota - 1))
                        valordescontado = valordescontado + valorfinal - valorcuota
                        valorpendiente = valorarancel - valordescontado
                        tablaamortizacion += [(maxnumcuota, fechainiciopago, fechavence, valorfinal, valorpendiente)]
                        tablaamortizacion += [(maxnumcuota+1, fechainiciopago, fechavence, valordescuento, valorpendiente-valordescuento)]
                    else:
                        valorfinal = Decimal(null_to_decimal(valorarancel)).quantize(Decimal('.01')) - (valorcuota * (maxnumcuota - 1))
                        valordescontado = valordescontado + valorfinal - valorcuota
                        valorpendiente = valorarancel - valordescontado
                        tablaamortizacion += [(maxnumcuota, fechainiciopago, fechavence, valorfinal, valorpendiente)]
                else:
                    tablaamortizacion += [(n + 1, fechainiciopago, fechavence, valorcuota, valorpendiente)]
                    valordescontado = valordescontado + valorcuota
                    valorpendiente = valorarancel - valordescontado
        return tablaamortizacion

class GrupoRequisitoCohorte(ModeloBase):
    observacion = models.TextField(blank=True, null=True, verbose_name=u"Observación")
    cohorte = models.ForeignKey(CohorteMaestria, null=True, blank=True, verbose_name=u'Cohorte Maestria', on_delete=models.CASCADE)
    orden = models.IntegerField(blank=True, null=True, verbose_name=u'Orden nivel')

    def __str__(self):
        return u'%s' % self.observacion

    def mis_requisitosgrupos(self):
        return self.requisitosgrupocohorte_set.filter(status=True)

class RolAsesor(ModeloBase):
    descripcion = models.TextField(default='', verbose_name=u'Descripcion')

    def __str__(self):
        return u'%s' % self.descripcion

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(RolAsesor,self).save(*args, **kwargs)

    class Meta:
        verbose_name = u"Rol Asesor"
        verbose_name_plural = u"Roles Asesores"
        ordering = ['id']


class AsesorComercial(ModeloBase):
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Asesor Comercial', on_delete=models.CASCADE)
    rol = models.ForeignKey(RolAsesor, blank=True, null=True, verbose_name=u'Rol del Asesor', on_delete=models.CASCADE)
    fecha_desde = models.DateTimeField(blank=True, null=True, verbose_name=u'Vigencia Asesor Desde')
    fecha_hasta = models.DateTimeField(blank=True, null=True, verbose_name=u'Vigencia Asesor Hasta')
    telefono = models.CharField(default='', max_length=50, verbose_name=u"Telefono de trabajo")
    activo = models.BooleanField(blank=True, null=True, default=True, verbose_name=u"Activo")
    rolgrupo = models.IntegerField(choices=GRUPO_ROL, default=1, verbose_name=u'Grupo Territorio')

    def __str__(self):
        return u'%s' % self.persona

    def cohortesasignadas(self):
        return AsesorMeta.objects.filter(asesor_id=self.id, status=True).distinct().order_by('-id')

    def cantidad_reservaciones_pendientes(self):
        return HistorialReservacionProspecto.objects.filter(persona=self.persona, status=True, estado_asesor=1).count()

    def asignados(self):
        aa = datetime.now().date().year
        asi =aa + 1
        return InscripcionCohorte.objects.filter(status=True, asesor=self, fecha_creacion__year__in=[aa, asi]).count()

    def atendidos(self):
        aa = datetime.now().date().year
        asi =aa + 1
        return InscripcionCohorte.objects.filter(status=True, asesor=self, tiporespuesta__isnull=False, fecha_creacion__year__in=[aa, asi]).count()

    def no_atendidos(self):
        aa = datetime.now().date().year
        asi =aa + 1
        return InscripcionCohorte.objects.filter(status=True, asesor=self, tiporespuesta__isnull=True, fecha_creacion__year__in=[aa, asi]).count()

    def ventas_obtenidas(self):
        aa = datetime.now().date().year
        asi =aa + 1
        return VentasProgramaMaestria.objects.filter(status=True, asesor=self, valida=True, fecha__year__in=[aa, asi]).count()

    def ventas_obtenidas_fecha(self, lista):
        return VentasProgramaMaestria.objects.filter(status=True, asesor=self, valida=True, inscripcioncohorte__id__in=lista).count()

    def tiene_meta_cohorte(self, idc):
        return True if AsesorMeta.objects.filter(asesor_id=self.id, status=True, cohorte__id=idc) else False

    def perfil_administrativo(self):
        from sga.models import PerfilUsuario, Administrativo
        if Administrativo.objects.filter(status=True, persona=self.persona).exists():
            admin = Administrativo.objects.filter(status=True, persona=self.persona).first()
            if PerfilUsuario.objects.filter(status=True, persona=self.persona, administrativo=admin).exists():
                perfil = PerfilUsuario.objects.filter(status=True, persona=self.persona, administrativo=admin).first()
                return perfil
            else:
                return None
        else:
            return None

    def territorios(self):
        return AsesorTerritorio.objects.filter(status=True, asesor=self)

    class Meta:
        verbose_name = u"Asesor Comercial"
        verbose_name_plural = u"Asesores Comerciales"
        ordering = ['id']


class AsesorMeta(ModeloBase):
    asesor = models.ForeignKey(AsesorComercial, blank=True, null=True, verbose_name=u'Asesor Comercial', on_delete=models.CASCADE)
    fecha_inicio_meta = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha de Inicio Meta')
    fecha_fin_meta = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha de Fin Meta')
    meta = models.IntegerField(blank=True, null=True, verbose_name=u'Meta')
    cohorte = models.ForeignKey(CohorteMaestria, null=True, blank=True, verbose_name=u'Cohorte Maestria', on_delete=models.CASCADE)
    maestria = models.ForeignKey(MaestriasAdmision, null=True, blank=True, verbose_name=u'Maestria asignada', on_delete=models.CASCADE)
    estado = models.IntegerField(choices=ESTADO_META, default=1, verbose_name=u'Estado de la meta')

    def __str__(self):
        return u'%s' % self.asesor

    def total_ventas_reportadas(self):
        try:
            return VentasProgramaMaestria.objects.filter(status=True, asesor=self.asesor, inscripcioncohorte__cohortes=self.cohorte, facturado=False).count()
        except Exception as ex:
            pass

    def total_ventas_facturadas(self):
        try:
            return VentasProgramaMaestria.objects.filter(status=True, asesor=self.asesor, inscripcioncohorte__cohortes=self.cohorte, facturado=True).count()
        except Exception as ex:
            pass

    def total_ventas_validas(self):
        try:
            return VentasProgramaMaestria.objects.filter(status=True, asesor=self.asesor, inscripcioncohorte__cohortes=self.cohorte, valida=True).count()
        except Exception as ex:
            pass

    def total_ventas_rechazadas(self):
        try:
            return VentasProgramaMaestria.objects.filter(status=True, asesor=self.asesor, inscripcioncohorte__cohortes=self.cohorte, valida=False).count()
        except Exception as ex:
            pass

    def metas_pendientes(self):
        return self.meta - self.total_ventas_validas()

    def estado_meta(self):
        estado = False
        if self.total_ventas_validas() > self.meta:
            estado = True
        return estado

    def listado_maestrantes(self):
        from sagest.models import Rubro

        listado_ventas = []

        idadmitidos = InscripcionCohorte.objects.filter(cohortes=self.cohorte,
                                                        status=True,
                                                        asesor = self.asesor).values_list('id', flat=True)

        for idadmitido in idadmitidos:
            if Rubro.objects.filter(inscripcion__id=idadmitido).exists():
                admitido = InscripcionCohorte.objects.get(pk=idadmitido)
                rubrocohorte = Rubro.objects.get(inscripcion=admitido)
                costomaestria = admitido.cohortes.valorprogramacertificado
                diezporciento = costomaestria * 0.10

                if costomaestria == rubrocohorte.valor:
                    valorpagado = admitido.total_pagado_cohorte()
                else:
                    valorpagado = admitido.inscripcionaspirante.persona.total_pagado_maestria()

                if valorpagado >= diezporciento:
                    listado_ventas.append(admitido.id)

        return Rubro.objects.filter(status=True, admisionposgradotipo__in=[2, 3], inscripcion_id__in=listado_ventas)

    def cant_vent_ase(self, anio, mes):
        metas = 0
        if VentasProgramaMaestria.objects.filter(status=True, asesor=self.asesor, inscripcioncohorte__cohortes__maestriaadmision=self.maestria, fecha__year=anio, fecha__month=mes, valida=True).exists():
            metas = VentasProgramaMaestria.objects.filter(status=True, asesor=self.asesor, inscripcioncohorte__cohortes__maestriaadmision=self.maestria, fecha__year=anio, fecha__month=mes, valida=True).count()
        return metas

    class Meta:
        verbose_name = u"Asesor Meta"
        verbose_name_plural = u"Asesores Metas"
        ordering = ['id']

class DetalleAsesorMeta(ModeloBase):
    asesormeta = models.ForeignKey(AsesorMeta, blank=True, null=True, verbose_name=u'Cabecera meta', on_delete=models.CASCADE)
    inicio = models.DateField(blank=True, null=True, verbose_name=u'Inicio de meta')
    fin = models.DateField(blank=True, null=True, verbose_name=u'Fin de meta')
    cantidad = models.IntegerField(blank=True, null=True, default=0, verbose_name=u'Cantidad de ventas a conseguir')
    estado = models.IntegerField(choices=ESTADO_META, default=1, verbose_name=u'Estado de la meta')

    def __str__(self):
        return u'%s - %s' % (self.asesormeta.asesor, self.cantidad)

    def cant_vent_rep(self):
        metas = 0
        anio = self.inicio.year
        mes = self.inicio.month
        if VentasProgramaMaestria.objects.filter(status=True, asesor=self.asesormeta.asesor, inscripcioncohorte__cohortes__maestriaadmision=self.asesormeta.maestria, fecha__year=anio, fecha__month=mes, facturado=False).exists():
            metas = VentasProgramaMaestria.objects.filter(status=True, asesor=self.asesormeta.asesor, inscripcioncohorte__cohortes__maestriaadmision=self.asesormeta.maestria, fecha__year=anio, fecha__month=mes, facturado=False).count()
        return metas

    def cant_vent_fac(self):
        metas = 0
        anio = self.inicio.year
        mes = self.inicio.month
        if VentasProgramaMaestria.objects.filter(status=True, asesor=self.asesormeta.asesor, inscripcioncohorte__cohortes__maestriaadmision=self.asesormeta.maestria, fecha__year=anio, fecha__month=mes, facturado=True).exists():
            metas = VentasProgramaMaestria.objects.filter(status=True, asesor=self.asesormeta.asesor, inscripcioncohorte__cohortes__maestriaadmision=self.asesormeta.maestria, fecha__year=anio, fecha__month=mes, facturado=True).count()
        return metas

    def cant_vent_val(self):
        metas = 0
        anio = self.inicio.year
        mes = self.inicio.month
        if VentasProgramaMaestria.objects.filter(status=True, asesor=self.asesormeta.asesor, inscripcioncohorte__cohortes__maestriaadmision=self.asesormeta.maestria, fecha__year=anio, fecha__month=mes, valida=True).exists():
            metas = VentasProgramaMaestria.objects.filter(status=True, asesor=self.asesormeta.asesor, inscripcioncohorte__cohortes__maestriaadmision=self.asesormeta.maestria, fecha__year=anio, fecha__month=mes, valida=True).count()
        return metas

    def cant_vent_rec(self):
        metas = 0
        anio = self.inicio.year
        mes = self.inicio.month
        if VentasProgramaMaestria.objects.filter(status=True, asesor=self.asesormeta.asesor, inscripcioncohorte__cohortes__maestriaadmision=self.asesormeta.maestria, fecha__year=anio, fecha__month=mes, valida=False).exists():
            metas = VentasProgramaMaestria.objects.filter(status=True, asesor=self.asesormeta.asesor, inscripcioncohorte__cohortes__maestriaadmision=self.asesormeta.maestria, fecha__year=anio, fecha__month=mes, valida=False).count()
        return metas

    def metas_pendientes(self):
        if self.cant_vent_val() > self.cantidad:
            tot = 0
        else:
            tot = self.cantidad - self.cant_vent_val()
        return tot

    def estado_meta(self):
        estado = False
        if self.cant_vent_val() >= self.cantidad:
            estado = True
        return estado

    def mesmeta(self):
        return int(self.inicio.month)

    def porcentaje_cumplimiento(self):
        from sagest.models import Rubro, Pago
        porcentaje = 0
        ventas = self.cant_vent_val()


        metas = self.cantidad

        if ventas > 0 and metas > 0:
            tot = (ventas/metas) * 100
            porcentaje = Decimal(null_to_decimal(tot)).quantize(Decimal('.01'))
        else:
            porcentaje = 0
        return porcentaje

    class Meta:
        verbose_name = u"Detalle de metas"
        verbose_name_plural = u"Detalle de metas mensuales"
        ordering = ['id']

class CuposMaestriaMes(ModeloBase):
    maestria = models.ForeignKey(MaestriasAdmision, null=True, blank=True, verbose_name=u'Maestria', on_delete=models.CASCADE)
    inicio = models.DateField(blank=True, null=True, verbose_name=u'Inicio de meta')
    fin = models.DateField(blank=True, null=True, verbose_name=u'Fin de meta')
    cuposlibres = models.IntegerField(default=0, verbose_name=u'Cupos a vender de la maestría')
    estado = models.IntegerField(choices=ESTADO_META, default=1, verbose_name=u'Estado de la meta mensual')

    def __str__(self):
        return u'%s - %s - %s' % (self.maestria, self.inicio, self.fin)

    class Meta:
        verbose_name = u"Cupo maestría mensual"
        verbose_name_plural = u"Cupos maestría mensuales"
        ordering = ['-id']

class AsesorTerritorio(ModeloBase):
    asesor = models.ForeignKey(AsesorComercial, blank=True, null=True, verbose_name=u'Asesor Comercial', on_delete=models.CASCADE)
    canton = models.ForeignKey('sga.Canton', blank=True, null=True, verbose_name=u'Territorio asignado', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s - %s' % (self.asesor, self.canton.nombre)

    class Meta:
        verbose_name = u"Asesor Territorio"
        verbose_name_plural = u"Asesores de Territorio"
        ordering = ['-id']

class TipoRespuestaProspecto(ModeloBase):
    descripcion = models.CharField(default='', blank=True, null=True, max_length=300, verbose_name=u"Descripción")

    def __str__(self):
        return u"%s" % self.descripcion

    class Meta:
        verbose_name = u'Tipo de Respuesta de Prospecto'
        verbose_name_plural = u'Tipos de Respuesta de Prospecto'
        ordering = ['descripcion']

class CanalInformacionMaestria(ModeloBase):
    descripcion = models.CharField(default='', blank=True, null=True, max_length=300, verbose_name=u"Descripción")
    valido_form = models.BooleanField(default=False, verbose_name=u"Para presentar en formulario externo")

    def __str__(self):
        return u"%s" % self.descripcion

    class Meta:
        verbose_name = u'Canal de Información'
        verbose_name_plural = u'Canales de Información'
        ordering = ['descripcion']

class InscripcionCohorte(ModeloBase):
    inscripcionaspirante = models.ForeignKey(InscripcionAspirante, verbose_name=u'Inscripcion Aspirante', on_delete=models.CASCADE)
    cohortes = models.ForeignKey(CohorteMaestria, blank=True, null=True, verbose_name=u'Programa de maestría', on_delete=models.CASCADE)
    activo = models.BooleanField(default=True, verbose_name=u"Activo")
    aproboproceso = models.BooleanField(default=False, verbose_name=u"Aprobó proceso de maestria")
    fecharecibo = models.DateField(blank=True, null=True, verbose_name=u'fecha de recibo')
    grupo = models.ForeignKey(GrupoRequisitoCohorte, blank=True, null=True, verbose_name=u'Programa de maestría', on_delete=models.CASCADE)
    estado_emailevidencia = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u'Estado Email evidencia')
    fecha_emailevidencia = models.DateTimeField(blank=True, null=True)
    persona_emailevidencia = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Quien aprueba o rechaza evidencias', on_delete=models.CASCADE)
    estado_aprobador = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u'Estado Email evidencia')
    fecha_aprobador = models.DateTimeField(blank=True, null=True)
    persona_aprobador = models.ForeignKey('sga.Persona', blank=True, null=True,related_name='+', verbose_name=u'Quien aprueba o rechaza evidencias', on_delete=models.CASCADE)
    persona_permisosubir = models.ForeignKey('sga.Persona', blank=True, null=True,related_name='+', verbose_name=u'Quien aprueba o rechaza evidencias', on_delete=models.CASCADE)
    fecha_permisosubir = models.DateTimeField(blank=True, null=True)
    envioemailrecordatorio = models.BooleanField(default=False, verbose_name=u"Envió email recordatorio")
    fecha_envioemailrecordatorio = models.DateTimeField(blank=True, null=True)
    tipobeca = models.ForeignKey('sga.DetalleConfiguracionDescuentoPosgrado', blank=True, null=True, verbose_name=u'Tipo de beca', on_delete=models.CASCADE)
    contactomaestria = models.IntegerField(choices=CONTACTO_MAESTRIA, blank=True, null=True, verbose_name=u'Contacto maestria')
    inscripcion = models.ForeignKey('sga.Inscripcion', blank=True, null=True, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    tipocobro = models.IntegerField(choices=TIPO_COBRO, default=1, verbose_name=u'tipo de cobro')
    tipo = models.ForeignKey('sagest.TipoOtroRubro', blank=True, null=True, verbose_name=u"Tipo", on_delete=models.CASCADE)
    codigoqr = models.BooleanField(default=False, verbose_name=u"Admitidos generado con código QR")
    asesor = models.ForeignKey(AsesorComercial, blank=True, null=True, verbose_name=u'Asesor Comercial', on_delete=models.CASCADE)
    estado_asesor = models.IntegerField(choices=ESTADO_ASESOR_COMERCIAL, default=1, verbose_name=u'Estado aprobacion Lead')
    tiulacionaspirante = models.ForeignKey('sga.Titulacion', null=True, blank=True, verbose_name=u'Titulacion', on_delete=models.SET_NULL)
    cantexperiencia = models.FloatField(default=0, verbose_name=u'Años de experiencia')
    formapagopac = models.ForeignKey('inno.TipoFormaPagoPac', blank=True, null=True, verbose_name=u'Forma de Pago', on_delete=models.CASCADE)
    estadoformapago = models.IntegerField(choices=ESTADO_FORMA_PAGO, default=1, verbose_name=u'Estado de forma de pago')
    numcuotaspago = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Número de cuotas')
    tiporespuesta = models.ForeignKey(TipoRespuestaProspecto, blank=True, null=True, verbose_name=u'Respuesta del Prospecto', on_delete=models.CASCADE)
    itinerario = models.IntegerField(choices=ITINERARIO_ASIGNATURA_MALLA, default=0, blank=True, null=True, verbose_name=u'Itinerario')
    Configfinanciamientocohorte = models.ForeignKey(ConfigFinanciamientoCohorte, blank=True, null=True, verbose_name=u'Configuración financiamiento cohorte', on_delete=models.CASCADE)
    atencion_financiamiento = models.IntegerField(choices=ESTADO_ATENDIDO, default=1, verbose_name=u'Estado atención financiamiento')
    doblepostulacion = models.BooleanField(default=False, verbose_name=u'Verfica si el postulante va cursar dos maestrias')
    subirrequisitogarante = models.BooleanField(default=True, verbose_name=u'Verfica si el postulante debe subir requisistos de garante')
    canal = models.ForeignKey(CanalInformacionMaestria, blank=True, null=True, verbose_name=u'Canal de Informacion', on_delete=models.CASCADE)
    preaprobado = models.BooleanField(default=False, verbose_name=u'Verfica si el postulante cumple con sus requisitos de admision')
    todosubido = models.BooleanField(default=False, verbose_name=u'Verfica si el postulante tiene todas sus evidencias de admisión subidas')
    tienerechazo = models.BooleanField(default=False, verbose_name=u'Verifica si el postulante tiene alguna evidencia rechazada')
    vendido = models.BooleanField(default=False, verbose_name=u'Verifica si el postulante es una venta para el asesor')
    todosubidofi = models.BooleanField(default=False, verbose_name=u'Verifica si el tiene subido todos los requisitos de financiamiento')
    tienerechazofi = models.BooleanField(default=False, verbose_name=u'Verifica si el postulante tiene alguna evidencia de financiamiento rechazada')
    aceptado = models.BooleanField(default=False, verbose_name=u'Verifica si el postulante aceptó su modalidad de pago')
    puedeeditarmp = models.BooleanField(default=True, verbose_name=u'Puede editar modalidad de pago')
    puedesubiroficio = models.BooleanField(default=False, verbose_name=u'Puede subir oficio de terminación de contrato')
    leaddezona = models.BooleanField(default=False, verbose_name=u'Lead contactado por asesor de zona')
    es_becado = models.BooleanField(default=False, verbose_name=u'Verifica si el postulante tiene beca')
    convenio = models.ForeignKey('posgrado.Convenio', blank=True, null=True, verbose_name=u'Convenio de posgrado', on_delete=models.CASCADE)
    motivo_rechazo_desactiva = models.IntegerField(choices=MOTIVO_RECHAZA_DESACTIVA, default=1, verbose_name=u'Motivo rechazo o desactivado', null=True, blank=True)
    homologado = models.IntegerField(choices=IDENTIFICA_HOMOLOGADO, default=0, verbose_name=u'Tipo Homologación', null=True, blank=True)

    def __str__(self):
        return u'%s - %s' % (self.inscripcionaspirante, self.cohortes)

    class Meta:
        verbose_name = u"Inscripción cohorte"
        verbose_name_plural = u"Inscripciones cohortes"
        ordering = ['id']

    def cambioadmitido(self):
        if CambioAdmitidoCohorteInscripcion.objects.filter(status=True,inscripcionCohorte=self).exists():
            return CambioAdmitidoCohorteInscripcion.objects.filter(status=True,inscripcionCohorte=self).order_by('-id').first()
        return None

    def esta_inscrito(self):
        from sga.models import Inscripcion
        x = Inscripcion.objects.filter(persona=self.inscripcionaspirante.persona, carrera=self.cohortes.maestriaadmision.carrera).exists()
        return True if Inscripcion.objects.filter(persona=self.inscripcionaspirante.persona, carrera=self.cohortes.maestriaadmision.carrera).exists() and self.inscripcion and self.inscripcion.matriculado_periodo(self.cohortes.periodoacademico) else False

    def eliminar_aspirante_matricula(self):
        rubro1 = self.rubro_set.filter(status=True)
        return rubro1

    def puede_eliminar_aspirante_matricula(self):
        rubros1 = self.rubro_set.filter(status=True)
        elimina = True
        if self.genero_rubro_matricula() or self.genero_rubro_programa():
            for rubro in rubros1:
                if not (rubro.total_pagado() >= 0 and rubro.total_pagado() <= 0):
                    elimina = False
        else:
            elimina = False
        return elimina

    def eval_entrevista(self):
        return self.integrantegrupoentrevitamsc_set.filter(status=True)[0].estadoentrevista

    def listacuotas(self):
        return Pago.objects.filter(inscripcioncohorte=self,status=True).order_by('id')

    def sube_evidenciapagoexamen(self):
        return self.evidenciapagoexamen_set.filter(status=True)

    def tiene_evidenciapagoexamen(self):
        return self.evidenciapagoexamen_set.filter(status=True)[0]

    def puedeeliminar(self):
        hoy = datetime.now().date()
        if not self.evidenciarequisitosaspirante_set.filter(status=True).exists() or self.cohortes.fechafinrequisito >= hoy:
            return True
        else:
            return False

    def puederevisar(self):
        hoy = datetime.now().date()
        if hoy > self.cohortes.fechafinrequisito:
            return True
        else:
            return False

    def pago_examen(self):
        if self.pago_set.filter(tipo_id=1, status=True):
            return self.pago_set.filter(tipo_id=1, status=True)[0].cuotapago_set.filter(status=True)[0].valor
        else:
            return 0

    def pago_matricula(self):
        if self.pago_set.filter(tipo_id=2, status=True):
            return self.pago_set.filter(tipo_id=2, status=True)[0].cuotapago_set.filter(status=True)[0].valor
        else:
            return 0

    def nota_examentest(self):
        if self.integrantegrupoexamenmsc_set.filter(status=True).exists():
            return self.integrantegrupoexamenmsc_set.filter(status=True)[0].notatest
        return None

    def nota_examen(self):
        if self.integrantegrupoexamenmsc_set.filter(status=True).exists():
            return self.integrantegrupoexamenmsc_set.filter(status=True)[0].notaexa
        return None

    def promedio(self):
        if self.integrantegrupoexamenmsc_set.filter(status=True).exists():
            return self.integrantegrupoexamenmsc_set.filter(status=True)[0].notafinal
        return None

    def total_evidencias(self):
        #requisitosexcluir = ClaseRequisito.objects.values_list('requisito__id').filter(clasificacion=3, status=True)
        # if self.formapagopac_id == 2:
        #     requisitosexcluir = []
        requistosmaestria = RequisitosMaestria.objects.filter(status=True, cohorte=self.cohortes, requisito__claserequisito__clasificacion__id=1, obligatorio=True).values_list('id', flat=True)
        cont = 0
        if not self.grupo:
            for requisto in requistosmaestria:
                if EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=self,
                                                               requisitos_id=requisto,
                                                               requisitos__requisito__claserequisito__clasificacion__id=1).exists():
                    cont += 1
            return cont
            #return self.evidenciarequisitosaspirante_set.values("id").filter(status=True).exclude(requisitos__requisito_id__in=requisitosexcluir).count()
        else:
            gruporequisitos = self.grupo.requisitosgrupocohorte_set.values_list('requisito_id', flat=True).filter(status=True)

            for requisto in requistosmaestria:
                if EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=self,
                                                               requisitos_id=requisto,
                                                               requisitos__requisito__claserequisito__clasificacion__id=1,
                                                               requisitos__requisito__id__in=gruporequisitos).exists():
                    cont += 1
            return cont
                #return self.evidenciarequisitosaspirante_set.values("id").filter(requisitos__requisito_id__in=gruporequisitos,status=True).exclude(requisitos__requisito_id__in=requisitosexcluir).count()

    def total_evidence_lead(self):
        requistosmaestria = RequisitosMaestria.objects.filter(status=True, cohorte=self.cohortes, requisito__claserequisito__clasificacion__id=1, obligatorio=True).values_list('id', flat=True)
        cont = 0
        estado = False
        for requisto in requistosmaestria:
            if EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=self, requisitos_id=requisto, requisitos__requisito__claserequisito__clasificacion__id=1).exists():
                evi = EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=self, requisitos_id=requisto, requisitos__requisito__claserequisito__clasificacion__id=1).order_by('-id').first()
                deta = DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia=evi).order_by('-id').first()
                if deta.estadorevision == 1 or deta.estado_aprobacion == 2:
                    cont += 1

        if cont == requistosmaestria.count():
            estado = True

        return estado

    def total_evidence_lead_fi(self):
        if self.subirrequisitogarante:
            requistosmaestria = RequisitosMaestria.objects.filter(status=True, cohorte=self.cohortes, requisito__claserequisito__clasificacion__id=3, obligatorio=True).values_list('id', flat=True)
        else:
            requistosmaestria = RequisitosMaestria.objects.filter(status=True, cohorte=self.cohortes, requisito__claserequisito__clasificacion__id=3, requisito__tipopersona__id=1, obligatorio=True).values_list('id', flat=True)
        cont = 0
        estado = False
        for requisto in requistosmaestria:
            if EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=self, requisitos_id=requisto, requisitos__requisito__claserequisito__clasificacion__id=3).exists():
                evi = EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=self, requisitos_id=requisto, requisitos__requisito__claserequisito__clasificacion__id=3).order_by('-id').first()
                deta = DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia=evi).order_by('-id').first()
                if deta.estadorevision == 1 or deta.estado_aprobacion == 2:
                    cont += 1

        if cont == requistosmaestria.count():
            estado = True

        return estado

    def act_evidencias_rechazadas(self):
        requistosmaestria = RequisitosMaestria.objects.filter(status=True, cohorte=self.cohortes, requisito__claserequisito__clasificacion__id=1).values_list('id', flat=True)
        cont = 0
        estado = False
        for requisto in requistosmaestria:
            if EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=self,
                                                           requisitos_id=requisto,
                                                           requisitos__requisito__claserequisito__clasificacion__id=1).exists():
                evi = EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=self,
                                                           requisitos_id=requisto,
                                                           requisitos__requisito__claserequisito__clasificacion__id=1).order_by('-id').first()
                if DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia=evi).exists():
                    deta = DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia=evi).order_by('-id').first()
                    if deta.estado_aprobacion == 3:
                        estado = True
                        break
        return estado

    def act_evidencias_subidas(self):
        requistosmaestria = RequisitosMaestria.objects.filter(status=True, cohorte=self.cohortes, requisito__claserequisito__clasificacion__id=1).values_list('id', flat=True)
        cont = 0
        estado = False
        for requisto in requistosmaestria:
            if EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=self,
                                                           requisitos_id=requisto,
                                                           requisitos__requisito__claserequisito__clasificacion__id=1).exists():
                evi = EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=self,
                                                           requisitos_id=requisto,
                                                           requisitos__requisito__claserequisito__clasificacion__id=1).order_by('-id').first()
                if DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia=evi).exists():
                    deta = DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia=evi).order_by('-id').first()
                    if deta.estado_aprobacion == 1:
                        estado = True
                        break
        return estado

    def nombre_evidencias_rechazadas(self):
        requistosmaestria = RequisitosMaestria.objects.filter(status=True, cohorte=self.cohortes, requisito__claserequisito__clasificacion__id=1).values_list('id', flat=True)
        cont = 0
        estado = False
        lista = []
        evidences = ""
        for requisto in requistosmaestria:
            if EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=self,
                                                           requisitos_id=requisto,
                                                           requisitos__requisito__claserequisito__clasificacion__id=1).exists():
                evi = EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=self,
                                                           requisitos_id=requisto,
                                                           requisitos__requisito__claserequisito__clasificacion__id=1).order_by('-id').first()
                if DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia=evi).exists():
                    deta = DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia=evi).order_by('-id').first()
                    if deta.estado_aprobacion == 3:
                        lista.append(evi.requisitos.requisito.nombre)
        if len(lista) > 0:
            co = 1
            for element in lista:
                if co == len(lista):
                    evidences += str(element) + "."
                    co += 1
                else:
                    evidences += str(element) + ", "
                    co += 1
        return evidences

    def fecha_ultimaevidenciaobligatoria(self):
        requisitosexcluir = ClaseRequisito.objects.values_list('requisito__id').filter(clasificacion=3, status=True)
        ultimafecha = None
        requisitos_cohorte = RequisitosMaestria.objects.filter(status=True, cohorte=self.cohortes).values_list('id', flat=True).exclude(requisito__claserequisito__clasificacion=3)
        if not self.grupo:
            ultimafecha = self.evidenciarequisitosaspirante_set.values("fecha_creacion").filter(status=True, requisitos__obligatorio=True, requisitos__id__in=requisitos_cohorte).exclude(
                requisitos__requisito_id__in=requisitosexcluir)
        else:
            gruporequisitos = self.grupo.requisitosgrupocohorte_set.values_list('requisito_id', flat=True).filter(
                status=True)
            ultimafecha = self.evidenciarequisitosaspirante_set.values("fecha_creacion").filter(
                requisitos__requisito_id__in=gruporequisitos, status=True, requisitos__obligatorio=True).exclude(
                requisitos__requisito_id__in=requisitosexcluir)
        if ultimafecha:
            ultimafecha = ultimafecha.order_by("-fecha_creacion").first()['fecha_creacion']
        return ultimafecha

    def tuvo_evidencias_rechazo(self):
        return True if DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia__inscripcioncohorte=self, estado_aprobacion=3).exists() else False

    def fecha_ultimo_rechazo(self):
        detalles = DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia__inscripcioncohorte=self, estado_aprobacion=3).order_by('-fecha_aprobacion').first()
        return detalles.fecha_aprobacion.date()

    def fecha_ultima_subida(self):
        detalles = DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia__inscripcioncohorte=self, estado_aprobacion=1).order_by('-fecha').first()
        return detalles.fecha.date()

    def dias_transcurridos(self):
        dias = 0
        if self.fecha_ultimaevidenciaobligatoria():
            dias = (datetime.now().date() - self.fecha_ultimaevidenciaobligatoria().date()).days
            dias = dias if dias > 0 else 0
        return dias

    def dias_transcurridos_over(self):
        dias = 0
        if self.fecha_aprobador and self.fecha_ultimaevidenciaobligatoria():
            dias = (self.fecha_aprobador.date() - self.fecha_ultimaevidenciaobligatoria().date()).days
            dias = dias if dias > 0 else 0
        return dias

    def tiene_preaprobacion_histo(self):
        return True if DetallePreAprobacionPostulante.objects.filter(status=True, inscripcion=self).exists() else False

    def ultima_fecha_preaprobacion(self):
        return DetallePreAprobacionPostulante.objects.filter(status=True, inscripcion=self,
                                                                 preaprobado=True).order_by('-id').first().fecha_creacion.date()

    def dias_sin_revisar(self):
        try:
            dias = 0
            dias_no_contados = 0
            # Fecha Actual
            factual = datetime.now().date()
            # Fecha de Pre-aprobacion
            if DetallePreAprobacionPostulante.objects.filter(status=True, inscripcion=self, preaprobado=True).exists():
                deta = DetallePreAprobacionPostulante.objects.filter(status=True, inscripcion=self,
                                                                     preaprobado=True).order_by('id').first()
                fpreapro = deta.fecha_creacion.date()
                if deta.dias == 0:
                    #Ultima fecha de rechazo
                    if self.act_evidencias_rechazadas():
                        frecha = self.fecha_ultimo_rechazo()
                        dias = (frecha - fpreapro).days
                        dias = dias if dias > 0 else 0
                    elif DetallePreAprobacionPostulante.objects.filter(status=True, inscripcion=self, preaprobado=True).count() > 1 and self.tuvo_evidencias_rechazo():
                        detalle = DetallePreAprobacionPostulante.objects.filter(status=True, inscripcion=self, preaprobado=True).order_by('-id').first()
                        #Fecha de nueva Pre-aprobación
                        fnupreapro = detalle.fecha_creacion.date()
                        frecha = self.fecha_ultimo_rechazo()
                        dias_no_contados = (fnupreapro - frecha).days
                        if self.estado_aprobador == 2 and self.fecha_aprobador:
                            fapro = self.fecha_aprobador.date()
                            dias = (fapro - fpreapro).days
                            dias = dias - dias_no_contados
                            deta.dias = dias
                            deta.save()
                        else:
                            dias = (factual - fpreapro).days
                            dias = dias - dias_no_contados
                            dias = dias if dias > 0 else 0
                    elif self.act_evidencias_subidas() and self.tuvo_evidencias_rechazo():
                        frecha = self.fecha_ultimo_rechazo()
                        dias = (frecha - fpreapro).days
                        dias = dias if dias > 0 else 0
                    elif self.estado_aprobador == 2 and self.fecha_aprobador:
                        # Fecha de aprobación requisitos
                        fapro = self.fecha_aprobador.date()
                        dias = (fapro - fpreapro).days
                        dias = dias if dias > 0 else 0
                        deta.dias = dias
                        deta.save()
                    else:
                        dias = (factual - fpreapro).days
                        dias = dias if dias > 0 else 0
                else:
                    dias = deta.dias
            return dias
        except Exception as ex:
            pass

    def total_evidenciasgrupocohorte(self):
        requisitosexcluir = ClaseRequisito.objects.values_list('requisito__id').filter(clasificacion=3, status=True)
        # if self.formapagopac_id == 2:
        #     requisitosexcluir = []
        if not self.grupo:
            return self.cohortes.requisitosmaestria_set.values('id').filter(status=True).exclude(requisito_id__in=requisitosexcluir).count()
        else:
            gruporequisitos = self.grupo.requisitosgrupocohorte_set.values_list('requisito_id',flat=True).filter(status=True)
            return self.cohortes.requisitosmaestria_set.values('id').filter(requisito_id__in=gruporequisitos, status=True).exclude(requisito_id__in=requisitosexcluir).count()

    def total_evidenciasgrupocohorteobligatorias(self):
        requisitosexcluir = ClaseRequisito.objects.values_list('requisito__id').filter(clasificacion=3, status=True)
        # if self.formapagopac_id == 2:
        #     requisitosexcluir = []
        if not self.grupo:
            return self.cohortes.requisitosmaestria_set.values('id').filter(obligatorio=True, status=True).exclude(requisito_id__in=requisitosexcluir).count()
        else:
            gruporequisitos = self.grupo.requisitosgrupocohorte_set.values_list('requisito_id',flat=True).filter(status=True)
            return self.cohortes.requisitosmaestria_set.values('id').filter(obligatorio=True, requisito_id__in=gruporequisitos, status=True).exclude(requisito_id__in=requisitosexcluir).count()

    def total_evidenciasaprobadas(self):
        requistosmaestria = RequisitosMaestria.objects.filter(status=True, cohorte=self.cohortes, requisito__claserequisito__clasificacion__id=1).values_list('id', flat=True)
        cont = 0
        for requisto in requistosmaestria:
            if EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=self,
                                                           requisitos_id=requisto,
                                                           requisitos__requisito__claserequisito__clasificacion__id=1).exists():
                evi = EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=self,
                                                           requisitos_id=requisto,
                                                           requisitos__requisito__claserequisito__clasificacion__id=1).order_by('-id').first()
                if DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia=evi).exists():
                    deta = DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia=evi).order_by('-id').first()
                    if deta.estado_aprobacion == 2:
                        cont += 1
        return cont
        # requisitosexcluir = ClaseRequisito.objects.values_list('requisito__id').filter(clasificacion=3, status=True)
        # if self.formapagopac_id == 2:
        #     requisitosexcluir = []
        # requisitos_cohorte = RequisitosMaestria.objects.filter(status=True, cohorte=self.cohortes).values_list('id', flat=True).exclude(requisito__claserequisito__clasificacion=3)
        # evidencias = self.evidenciarequisitosaspirante_set.filter(status=True, requisitos__id__in=requisitos_cohorte).exclude(requisitos__requisito_id__in=requisitosexcluir)
        # num_apro = 0
        # for evi in evidencias:
        #     if evi.detalleevidenciarequisitosaspirante_set.filter(status=True).exists():
        #         if evi.detalleevidenciarequisitosaspirante_set.filter(status=True).order_by('-id')[0].esta_aprobado():
        #             num_apro=num_apro+1
        # return num_apro

    def total_evidenciassinrechazar(self):
        requistosmaestria = RequisitosMaestria.objects.filter(status=True, cohorte=self.cohortes, requisito__claserequisito__clasificacion__id=1).values_list('id', flat=True)
        cont = 0
        for requisto in requistosmaestria:
            if EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=self,
                                                           requisitos_id=requisto,
                                                           requisitos__requisito__claserequisito__clasificacion__id=1).exists():
                evi = EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=self,
                                                           requisitos_id=requisto,
                                                           requisitos__requisito__claserequisito__clasificacion__id=1).order_by('-id').first()
                if DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia=evi).exists():
                    deta = DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia=evi).order_by('-id').first()
                    if deta.estado_aprobacion != 3:
                        cont += 1
        return cont

        # requisitosexcluir = ClaseRequisito.objects.values_list('requisito__id').filter(clasificacion=3, status=True)
        # if self.formapagopac_id == 2:
        #     requisitosexcluir = []
        # requisitos_cohorte = RequisitosMaestria.objects.filter(status=True, cohorte=self.cohortes).values_list('id', flat=True).exclude(requisito__claserequisito__clasificacion=3)
        # evidencias = self.evidenciarequisitosaspirante_set.filter(status=True, requisitos__id__in=requisitos_cohorte).exclude(requisitos__requisito_id__in=requisitosexcluir).values_list('id', flat=True)
        # num = 0
        # for evi in evidencias:
        #     if evi.detalleevidenciarequisitosaspirante_set.filter(status=True).exists():
        #         if evi.detalleevidenciarequisitosaspirante_set.filter(
        #                 Q(status=True) & ~Q(estado_aprobacion=3)).order_by('-id'):
        #             num = num + 1
        # num = DetalleEvidenciaRequisitosAspirante.objects.values('id').filter(
        #                                 Q(evidencia__in=evidencias) & (
        #                                     Q(status=True) & ~Q(estado_aprobacion=3))).distinct().count()
        # return num

    def total_evidenciasaprobadas_clase(self):
        try:
            # requisitosexcluir = ClaseRequisito.objects.values_list('requisito__id').filter(clasificacion=3, status=True)
            # if self.formapagopac_id == 2:
            #     requisitosexcluir = ClaseRequisito.objects.values_list('requisito__id').filter(clasificacion=1, status=True)
            if self.subirrequisitogarante:
                evidencias = self.evidenciarequisitosaspirante_set.filter(status=True, requisitos__requisito__claserequisito__clasificacion__id=3).exclude(requisitos__requisito__id__in=[56, 57, 59])
                num_apro = 0
                for evi in evidencias:
                    if evi.detalleevidenciarequisitosaspirante_set.filter(status=True).exists():
                        if evi.detalleevidenciarequisitosaspirante_set.filter(status=True).order_by('-id')[0].esta_aprobado():
                            num_apro=num_apro+1
            else:
                evidencias = self.evidenciarequisitosaspirante_set.filter(status=True, requisitos__requisito__claserequisito__clasificacion__id=3, requisitos__requisito__tipopersona__id=1)
                num_apro = 0
                for evi in evidencias:
                    if evi.detalleevidenciarequisitosaspirante_set.filter(status=True).exists():
                        if evi.detalleevidenciarequisitosaspirante_set.filter(status=True).order_by('-id')[0].esta_aprobado():
                            num_apro=num_apro+1
            return num_apro
        except Exception as ex:
            pass

    def total_evidenciasrechazadas(self):
        requistosmaestria = RequisitosMaestria.objects.filter(status=True, cohorte=self.cohortes, requisito__claserequisito__clasificacion__id=1).values_list('id', flat=True)
        cont = 0
        for requisto in requistosmaestria:
            if EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=self,
                                                           requisitos_id=requisto,
                                                           requisitos__requisito__claserequisito__clasificacion__id=1).exists():
                evi = EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=self,
                                                           requisitos_id=requisto,
                                                           requisitos__requisito__claserequisito__clasificacion__id=1).order_by('-id').first()
                if DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia=evi).exists():
                    deta = DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia=evi).order_by('-id').first()
                    if deta.estado_aprobacion == 3:
                        cont += 1
        return cont
        # requisitosexcluir = ClaseRequisito.objects.values_list('requisito__id').filter(clasificacion=3, status=True)
        # # if self.formapagopac_id == 2:
        # #     requisitosexcluir = []
        # requisitos_cohorte = RequisitosMaestria.objects.filter(status=True, cohorte=self.cohortes).values_list('id', flat=True).exclude(requisito__claserequisito__clasificacion=3)
        # evidencias = self.evidenciarequisitosaspirante_set.filter(status=True, requisitos__id__in=requisitos_cohorte).exclude(requisitos__requisito_id__in=requisitosexcluir)
        # num_apro = 0
        # for evi in evidencias:
        #     if evi.detalleevidenciarequisitosaspirante_set.filter(status=True).exists():
        #         if evi.detalleevidenciarequisitosaspirante_set.filter(status=True).order_by('-id')[0].estado_rechazado():
        #             num_apro=num_apro+1
        # return num_apro

    def total_evidencias_financiamiento(self):
        # idrequisitoscomer = ClaseRequisito.objects.filter(clasificacion=3).values_list('requisito__id', flat=True)
        if self.subirrequisitogarante:
            requisitosfinan = RequisitosMaestria.objects.filter(status=True, cohorte=self.cohortes, requisito__claserequisito__clasificacion__id=3).values_list('id', flat=True).exclude(requisito__id__in=[56, 57, 59])
        else:
            requisitosfinan = RequisitosMaestria.objects.filter(status=True, cohorte=self.cohortes, requisito__claserequisito__clasificacion__id=3, requisito__tipopersona__id=1).values_list('id', flat=True)
        return self.evidenciarequisitosaspirante_set.filter(status=True, requisitos__id__in=requisitosfinan).count()

    def total_requisitos_financiamiento(self):
        # idrequisitoscomer = ClaseRequisito.objects.filter(clasificacion=3).values_list('requisito__id', flat=True)
        if self.subirrequisitogarante:
            return RequisitosMaestria.objects.filter(status=True, cohorte=self.cohortes, requisito__claserequisito__clasificacion__id=3).values_list('id', flat=True).exclude(requisito__id__in=[56, 57, 59]).count()
        else:
            return RequisitosMaestria.objects.filter(status=True, cohorte=self.cohortes, requisito__claserequisito__clasificacion__id=3, requisito__tipopersona__id=1).values_list('id', flat=True).count()

    def total_evidenciasrechazadas_fi(self):
        requistosmaestria = RequisitosMaestria.objects.filter(status=True, cohorte=self.cohortes, requisito__claserequisito__clasificacion__id=3, obligatorio=True).values_list('id', flat=True)
        cont = 0
        for requisto in requistosmaestria:
            if EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=self,
                                                           requisitos_id=requisto,
                                                           requisitos__requisito__claserequisito__clasificacion__id=3).exists():
                evi = EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=self,
                                                           requisitos_id=requisto,
                                                           requisitos__requisito__claserequisito__clasificacion__id=3).order_by('-id').first()
                if DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia=evi).exists():
                    deta = DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia=evi).order_by('-id').first()
                    if deta.estado_aprobacion == 3:
                        cont += 1
        return cont

    def total_evidenciasaprobadas_fi(self):
        requistosmaestria = RequisitosMaestria.objects.filter(status=True, cohorte=self.cohortes, requisito__claserequisito__clasificacion__id=3).values_list('id', flat=True)
        cont = 0
        for requisto in requistosmaestria:
            if EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=self,
                                                           requisitos_id=requisto,
                                                           requisitos__requisito__claserequisito__clasificacion__id=3).exists():
                evi = EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=self,
                                                           requisitos_id=requisto,
                                                           requisitos__requisito__claserequisito__clasificacion__id=3).order_by('-id').first()
                if DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia=evi).exists():
                    deta = DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia=evi).order_by('-id').first()
                    if deta.estado_aprobacion == 2:
                        cont += 1
        return cont

    def total_evidencias_obligatorio(self):
        claserequisitoadmision = ClaseRequisito.objects.values_list('requisito__id', flat=True).filter(clasificacion=1, status=True)
        # if self.formapagopac_id == 2:
        #     requisitosexcluir = []
        evidencias = self.evidenciarequisitosaspirante_set.filter(status=True, requisitos__requisito_id__in=claserequisitoadmision)
        num_apro = 0
        for evi in evidencias:
            if evi.detalleevidenciarequisitosaspirante_set.filter(status=True, evidencia__requisitos__obligatorio=True).exists():
                if evi.detalleevidenciarequisitosaspirante_set.filter(status=True).order_by('-id')[0].esta_aprobado():
                    num_apro=num_apro+1
        return num_apro

    def tiene_contrato_subido(self):
        if Contrato.objects.filter(status=True, inscripcion=self).exists():
            contra = Contrato.objects.get(status=True, inscripcion=self)
            if contra.archivocontrato:
                flag = 2
            else:
                flag = 0
        else:
            flag = 0
        return flag

    def tiene_pagare_subido(self):
        if Contrato.objects.filter(status=True, inscripcion=self).exists():
            contra = Contrato.objects.get(status=True, inscripcion=self)
            if contra.archivopagare:
                flag = 2
            else:
                flag = 0
        else:
            flag = 0
        return flag

    def estado_contrato_subido(self):
        if Contrato.objects.filter(status=True, inscripcion=self).exists():
            contra = Contrato.objects.get(status=True, inscripcion=self)
            if contra.detalleaprobacioncontrato_set.filter(status=True, espagare=False).exists():
                evicon = contra.detalleaprobacioncontrato_set.filter(status=True, espagare=False).order_by('-id')[0]
                if evicon.esta_con_pendiente():
                    flag = 1
                elif evicon.esta_aprobado():
                    flag = 2
                elif evicon.esta_con_rechazado():
                    flag = 3
        return flag

    def estado_pagare_subido(self):
        if Contrato.objects.filter(status=True, inscripcion=self).exists():
            contra = Contrato.objects.get(status=True, inscripcion=self)
            if contra.detalleaprobacioncontrato_set.filter(status=True, espagare=True).exists():
                evicon = contra.detalleaprobacioncontrato_set.filter(status=True, espagare=True).order_by('-id')[0]
                if evicon.esta_con_pendiente():
                    flag = 1
                elif evicon.esta_aprobado():
                    flag = 2
                elif evicon.esta_con_rechazado():
                    flag = 3
        return flag

    def cumple_con_requisitos(self):
        requisitosexcluir = ClaseRequisito.objects.values_list('requisito__id').filter(clasificacion=3, status=True)
        return True if self.total_evidenciasaprobadas_clase() == self.cohortes.requisitosmaestria_set.values("id").filter(status=True).exclude(requisito_id__in=requisitosexcluir).count() else False

    def cumple_con_requisitos_comercializacion(self):
        # requisitosexcluir = ClaseRequisito.objects.values_list('requisito__id').filter(clasificacion=1, status=True)
        if self.subirrequisitogarante:
            return True if self.total_evidenciasaprobadas_clase() >= self.cohortes.requisitosmaestria_set.values("id").filter(status=True, obligatorio=True, requisito__claserequisito__clasificacion__id=3).exclude(requisito__id__in=[56, 57, 59]).count() else False
        else:
            return True if self.total_evidenciasaprobadas_clase() >= self.cohortes.requisitosmaestria_set.values("id").filter(status=True, obligatorio=True, requisito__tipopersona__id=1, requisito__claserequisito__clasificacion__id=3).count() else False

    def validar_boton(self):
        cohorte = self.cohortes
        bandera = 0
        for re in cohorte.requisitosmaestria_set.filter(status=True, obligatorio=True):
            ingresoevidencias = re.detalle_requisitosmaestriacohorte(self)
            if not ingresoevidencias.ultima_evidencia().estado_aprobacion == 2:
                bandera = 1
        if bandera == 0:
            return True
        return False

    def tiene_inscripcion(self):
        return self.inscripcion_set.values('id').filter(status=True).count()

    def notas_examen(self, cohorte):
        if self.integrantegrupoexamenmsc_set.filter(grupoexamen__cohorte__id=cohorte).exists():
            return self.integrantegrupoexamenmsc_set.filter(grupoexamen__cohorte__id=cohorte)[0]
        return None

    def mi_entrevista(self, cohorte):
        if self.integrantegrupoentrevitamsc_set.filter(grupoentrevista__cohortes__id=cohorte).exists():
            return self.integrantegrupoentrevitamsc_set.filter(grupoentrevista__cohortes__id=cohorte)[0]
        return None

    def genero_rubro_matricula(self):
        return self.rubro_set.filter(status=True,admisionposgradotipo=2, inscripcion=self, cohortemaestria=self.cohortes).exists()

    def cancelo_rubro_matricula(self):
        if self.formapagopac:
            if self.formapagopac.id == 2:
                totalpagado = self.total_pagado_rubro_cohorte()
                costomaestria = self.cohortes.valorprograma
                if totalpagado == costomaestria:
                    return True
                else:
                    return False
            else:
                return self.rubro_set.filter(status=True, admisionposgradotipo=2, inscripcion=self, cohortemaestria=self.cohortes, cancelado=True).exists()
        else:
            return self.rubro_set.filter(status=True, admisionposgradotipo=2, inscripcion=self, cohortemaestria=self.cohortes, cancelado=True).exists()

    def genero_rubro_programa(self):
        return self.rubro_set.filter(status=True,admisionposgradotipo=3, inscripcion=self, cohortemaestria=self.cohortes).exists()

    def genero_rubro_programa2(self):
        return self.rubro_set.filter(status=True,admisionposgradotipo=3, inscripcion=self, cohortemaestria=self.cohortes).exists()

    def cancelo_rubro_programa(self):
        if self.formapagopac:
            if self.formapagopac.id == 2:
                totalpagado = self.total_pagado_rubro_cohorte()
                costomaestria = self.cohortes.valorprograma
                if totalpagado == costomaestria:
                    return True
                else:
                    return False
            else:
                return self.rubro_set.filter(status=True, admisionposgradotipo=3, inscripcion=self, cohortemaestria=self.cohortes, cancelado=True).exists()
        else:
            return self.rubro_set.filter(status=True,admisionposgradotipo=3, inscripcion=self, cohortemaestria=self.cohortes, cancelado=True).exists()


    def tiene_garante(self):
        return True if GarantePagoMaestria.objects.filter(status=True, inscripcioncohorte=self).exists() else False

    def garantemaestria(self):
        return GarantePagoMaestria.objects.filter(status=True, inscripcioncohorte=self).order_by('-id')[0]

    def tiene_pagos_rubros(self):
        from sagest.models import Rubro
        if Rubro.objects.values('id').filter(status=True, admisionposgradotipo__in=[2,3], inscripcion=self, cohortemaestria=self.cohortes).exists():
            rubros = Rubro.objects.filter(status=True, admisionposgradotipo__in=[2, 3], inscripcion=self, cohortemaestria=self.cohortes).order_by('id')
            for rubro in rubros:
                if rubro.tiene_pagos():
                    pago = True
                    break
                else:
                    pago = False
        else:
            pago = False

        return pago

    def esadmitido(self):
        return IntegranteGrupoEntrevitaMsc.objects.filter(estado_emailadmitido=2, cohorteadmitidasinproceso__isnull=True, status=True, inscripcion__status=True, inscripcion=self)

    def valor_maestria(self):
        return self.cohortes.valorprogramacertificado

    def tiene_rubro_generado(self):
        if self.cohortes.valorprograma > 0:
            return self.genero_rubro_programa()
        else:
            return self.genero_rubro_matricula()

    def tiene_rubro_pagado(self):
        if self.cohortes.valorprograma > 0:
            return self.cancelo_rubro_programa()
        else:
            return self.cancelo_rubro_matricula()

    def rubro_generado_ins(self):
        from sagest.models import Rubro
        return True if Rubro.objects.filter(status=True, inscripcion=self, persona=self.inscripcionaspirante.persona).exists() else False

    def solicitudbeca(self):
        return self.descuentoposgradomatricula_set.filter(status=True)[0]

    def curso_matriculado(self):
        from sga.models import Matricula, MateriaAsignada
        cursos = []
        matricula = Matricula.objects.filter(status=True, inscripcion=self.inscripcion).order_by('-id').first()
        if MateriaAsignada.objects.filter(status=True, matricula=matricula).exists():
            for curso in matricula.materiaasignada_set.filter(matricula__status=True, status=True):
                if curso.materia.paralelo not in cursos:
                    cursos.append(curso.materia.paralelo)
        return cursos

    def tiene_matricula_cohorte(self):
        from sga.models import Matricula
        return True if Matricula.objects.filter(status=True, inscripcion=self.inscripcion, retiradomatricula=False).exists() else False

    def tiene_contrato_legalizado(self):
        estado = False
        if Contrato.objects.filter(status=True, inscripcion=self, contratolegalizado=True).exists():
            estado = True
        return estado

    def matricula_cohorte(self):
        from sga.models import Matricula
        return Matricula.objects.filter(status=True, inscripcion=self.inscripcion).order_by('-id')[0]

    def total_pagado_cohorte(self):
        from sagest.models import Pago
        return null_to_numeric(
            Pago.objects.filter(rubro__persona=self.inscripcionaspirante.persona, status=True, rubro__tipo__tiporubro=1, rubro__inscripcion=self).exclude(pagoliquidacion__isnull=False).exclude(
                factura__valida=False).aggregate(valor=Sum('valortotal'))['valor'])

    def tiene_cambiada_forma_pago(self):
        deta = DetalleAprobacionFormaPago.objects.filter(status=True, inscripcion=self, tipofinanciamiento__isnull=True).exclude(observacion='TODAS LAS EVIDENCIAS HAN SIDO APROBADAS').count()
        if deta >= 1:
            return 'SI'
        else:
            return 'NO'

    def fecha_asignacion_asesor(self):
        if HistorialAsesor.objects.filter(inscripcion=self, asesor=self.asesor).exists():
            histo = HistorialAsesor.objects.filter(inscripcion=self, asesor=self.asesor).order_by('-fecha_creacion').first()
            return histo.fecha_inicio
        else:
            return self.fecha_creacion

    def ultima_obervacion(self):
        return HistorialRespuestaProspecto.objects.filter(status=True, inscripcion=self).order_by('-fecha_creacion').first()

    def ultima_asignacion(self):
        return HistorialAsesor.objects.filter(status=True, inscripcion=self).order_by('-fecha_creacion').first()

    def fecha_matriculacion(self):
        try:
            from sga.models import Matricula
            matri = Matricula.objects.filter(status=True, inscripcion=self.inscripcion).order_by('-id')[0]
            return matri.fecha_creacion
        except Exception as ex:
            pass

    def fecha_matriculacion2(self):
        try:
            from sga.models import Matricula
            matri = ''
            if self.inscripcion:
                if Matricula.objects.filter(status=True, inscripcion=self.inscripcion).exists():
                    matri = Matricula.objects.filter(status=True, inscripcion=self.inscripcion).order_by('-id').first().fecha_creacion.date()
                else:
                    matri = 'NO REGISTRA'
            else:
                matri = 'NO REGISTRA'
            return matri
        except Exception as ex:
            pass

    def matriculado_por(self):
        try:
            from sga.models import Matricula, Persona, MateriaAsignada
            matri = ''
            if self.inscripcion:
                if Matricula.objects.filter(status=True, inscripcion=self.inscripcion).exists():
                    usu = Matricula.objects.filter(status=True, inscripcion=self.inscripcion).order_by('-id').first()
                    if MateriaAsignada.objects.filter(status=True, matricula=usu).exists():
                        mateasi = MateriaAsignada.objects.filter(status=True, matricula=usu).order_by('id').first()
                        per = Persona.objects.get(status=True, usuario=mateasi.usuario_creacion)
                        matri = per.nombre_completo_inverso()
                    else:
                        per = Persona.objects.get(status=True, usuario=usu.usuario_creacion)
                        matri = per.nombre_completo_inverso()
                else:
                    matri = 'NO REGISTRA'
            else:
                matri = 'NO REGISTRA'
            return matri
        except Exception as ex:
            pass

    def dias_sin_atender(self):
        try:
            if self.asesor:
                d1 = self.fecha_asignacion_asesor()
                d2 = self.ultima_obervacion().fecha_creacion
                intervalo = d2 - d1
                return intervalo.days
            else:
                return 0
        except Exception as ex:
            pass

    def numero_reservaciones(self):
        return HistorialReservacionProspecto.objects.filter(status=True, inscripcion=self).count()

    def tiene_reservaciones(self):
        return True if HistorialReservacionProspecto.objects.filter(status=True, inscripcion=self).exists() else False

    def reservacion_prospectos(self):
        return HistorialReservacionProspecto.objects.filter(status=True, inscripcion=self).order_by('-id')[0]

    def fue_atendido(self):
        return True if self.tiporespuesta is not None and self.tiporespuesta != 1 else False

    def reservacion_asesor(self):
        return HistorialReservacionProspecto.objects.get(status=True, inscripcion=self)

    def supervisor_que_asigno(self):
        return HistorialAsesor.objects.filter(status=True, inscripcion=self).order_by('-fecha_creacion')[0]

    def prospecto_calle(self):
        if self.asesor:
            if self.asesor.id == 13 and self.supervisor_que_asigno().usuario_creacion.id == 24559:
                calle = True
            else:
                calle = False
        else:
            calle = False
        return calle

    def login_admision_posgrado(self):
        from bd.models import LogEntryLogin
        if LogEntryLogin.objects.filter(action_app=3, user=self.inscripcionaspirante.persona.usuario).exists():
            login = LogEntryLogin.objects.filter(action_app=3, user=self.inscripcionaspirante.persona.usuario).order_by('-action_time')[0]
            if login.action_flag == 1:
                flag = 1
            elif login.action_flag == 2:
                flag = 2
            else:
                flag = 3
        else:
            flag = 3
        return flag

    def acceso_sistema(self):
        from bd.models import LogEntryLogin
        if LogEntryLogin.objects.filter(action_app=3, user=self.inscripcionaspirante.persona.usuario).exists():
            login = LogEntryLogin.objects.filter(action_app=3, user=self.inscripcionaspirante.persona.usuario).order_by('-action_time')[0]
            if login.action_flag == 1:
                flag = 'LOGIN EXITOSO'
            elif login.action_flag == 2:
                flag = 'LOGIN FALLIDO'
            else:
                flag = 'NO HA ACCEDIDO AL SISTEMA'
        else:
            flag = 'NO HA ACCEDIDO AL SISTEMA'
        return flag

    def detalle_finan(self):
        fina = DetalleAprobacionFormaPago.objects.filter(inscripcion=self, status=True)
        return fina.order_by('fecha_creacion')[0] if fina.exists() else None


    def total_generado_rubro(self):
        from sagest.models import Rubro
        if Rubro.objects.filter(status=True, inscripcion=self).exists():
            totalgenerado = Decimal(null_to_decimal(Rubro.objects.values_list('valor').filter(status=True, inscripcion=self).aggregate(valor=Sum('valor'))['valor'], 2)).quantize(Decimal('.01'))
            return totalgenerado
        else:
            return 0

    def total_pagado_rubro_cohorte(self):
        from sagest.models import Pago
        if Pago.objects.filter(status=True, rubro__inscripcion__id=self.id).exists():
            totalpagado = Decimal(null_to_decimal(Pago.objects.values_list('valortotal').filter(status=True, rubro__status=True, rubro__inscripcion__id=self.id).exclude(factura__valida=False).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))
            return totalpagado
        else:
            return 0

    def fecha_inscrito(self):
        from sga.models import Inscripcion
        fecha = ''
        if self.inscripcion:
            fechains = Inscripcion.objects.filter(pk=self.inscripcion.id, status=True).first()
            if fechains:
                fecha = fechains.fecha_creacion.date()
            else:
                fecha = 'NO REGISTRA'
        else:
            fecha = 'NO REGISTRA'
        return fecha

    def inscrito_por(self):
        from sga.models import Inscripcion, Persona
        ins = ''
        if self.inscripcion:
            inscri = Inscripcion.objects.filter(pk=self.inscripcion.id, status=True).first()
            if inscri:
                per = Persona.objects.get(status=True, usuario=inscri.usuario_creacion)
                if per.id in [10813, 24145]:
                    ins = per.nombre_completo_inverso() + " (INSCRITO POR APROBACIÓN DE CONTRATO)"
                else:
                    ins = per.nombre_completo_inverso()
            else:
                ins = 'NO REGISTRA'
        else:
            ins = 'NO REGISTRA'
        return ins

    def ids_rubros(self):
        from sagest.models import Rubro
        ids = []
        rubros = Rubro.objects.filter(status=True, inscripcion=self).order_by('id')
        for ru in rubros:
            ids.append(ru.id)
        return ids

    def total_pendiente(self):
        vpp = self.cohortes.valorprogramacertificado
        vp = self.total_pagado_rubro_cohorte()
        return vpp - float(vp)

    def total_vencido_rubro(self):
        from sagest.models import Rubro
        hoy = datetime.now().date()
        if Rubro.objects.filter(status=True, inscripcion=self, fechavence__lt=hoy, cancelado=False).exists():
            totalvencido = Decimal(null_to_decimal(Rubro.objects.values_list('valor').filter(status=True, inscripcion=self, fechavence__lt=hoy, cancelado=False).aggregate(valor=Sum('valor'))['valor'], 2)).quantize(Decimal('.01'))
            return totalvencido
        else:
            return 0

    def listado_rubros_maestria(self):
        from sagest.models import Rubro
        return Rubro.objects.filter(status=True, inscripcion=self).order_by('id')

    def cantidad_rubros_ins(self):
        from sagest.models import Rubro
        if Rubro.objects.filter(status=True, inscripcion=self).exists():
            return Rubro.objects.filter(status=True, inscripcion=self).count()
        else:
            return 0

    def amortizacion(self):
        if self.Configfinanciamientocohorte:
            cuotaini = self.Configfinanciamientocohorte.valormatricula
            if Contrato.objects.filter(status=True, inscripcion=self).exists():
                contract = Contrato.objects.filter(status=True, inscripcion=self).order_by('-fecha_creacion')[0]
                if TablaAmortizacion.objects.filter(status=True, contrato=contract).exists():
                    cuotas = TablaAmortizacion.objects.filter(status=True, contrato=contract).count()
                    valorcu = TablaAmortizacion.objects.filter(status=True, contrato=contract)[0].valor
                    return '$ ' + str(cuotaini) + ' con ' + str(cuotas) + ' cuotas de ' + '$ ' + str(valorcu)
                else:
                    return 'NO HA ACEPTADO NI DESCARGADO PAGARÉ'
            else:
                return 'NO TIENE PAGARÉ'
        else:
            return 'NO TIENE TIPO DE FINANCIAMIENTO ASIGNADO'

    def tiene_documentos(self):
        if Contrato.objects.filter(status=True, inscripcion=self).exists():
            contract = Contrato.objects.filter(status=True, inscripcion=self).order_by('-fecha_creacion')[0]
            if contract.archivocontrato and contract.archivopagare:
                if contract.estado == 2 and contract.estadopagare == 2:
                    return 'TIENE APROBADO CONTRATO Y PAGARÉ'
                elif contract.estado == 2:
                    return 'SOLO TIENE APROBADO CONTRATO'
                elif contract.estadopagare == 2:
                    return 'SOLO TIENE APROBADO PAGARÉ'
                else:
                    return 'EN PROCESO'
            elif contract.archivocontrato:
                return 'SOLO HA SUBIDO CONTRATO'
            elif contract.archivopagare:
                return 'SOLO HA SUBIDO PAGARÉ'
            else:
                return 'NO HA SUBIDO LOS DOCUMENTOS'
        else:
            return 'NO HA DESCARGADO CONTRATO'

    def nombre_garante(self):
        if GarantePagoMaestria.objects.filter(status=True, inscripcioncohorte=self).exists():
            gara = GarantePagoMaestria.objects.filter(status=True, inscripcioncohorte=self).order_by('-fecha_creacion')[0]
            return gara.apellido1 + ' ' + gara.apellido2 + ' ' + gara.nombres
        else:
            return 'SIN GARANTE'
    def garante_prospecto(self):
        if GarantePagoMaestria.objects.filter(status=True, inscripcioncohorte=self).exists():
            return GarantePagoMaestria.objects.filter(status=True, inscripcioncohorte=self).order_by('-fecha_creacion')[0]

    def tiene_rubro_cuadrado(self):
        cuadre = None
        if self.cohortes.valorprograma:
            valormaestria = self.cohortes.valorprograma
            if self.total_generado_rubro() == valormaestria:
                cuadre = True
            else:
                cuadre = False
        elif self.cohortes.valorprogramacertificado:
            valormaestria = self.cohortes.valorprogramacertificado
            if self.total_generado_rubro() == valormaestria:
                cuadre = True
            else:
                cuadre = False

        return cuadre


    def tiene_contrato_aprobado(self):
        estado = False
        if Contrato.objects.filter(status=True, inscripcion=self).exists():
            contra = Contrato.objects.filter(status=True, inscripcion=self).order_by('-id')[0]
            if contra.archivocontrato:
                if contra.detalleaprobacioncontrato_set.filter(status=True, espagare=False).exists():
                    evicon = contra.detalleaprobacioncontrato_set.filter(status=True, espagare=False).order_by('-id')[0]
                    if evicon.esta_aprobado():
                        estado = True
        return estado

    def tiene_pagare_aprobado(self):
        estado = 'NO'
        if self.formapagopac and self.formapagopac.id == 2:
            if Contrato.objects.filter(status=True, inscripcion=self).exists():
                contra = Contrato.objects.filter(status=True, inscripcion=self).order_by('-id')[0]
                if contra.archivopagare:
                    if contra.detalleaprobacioncontrato_set.filter(status=True, espagare=True).exists():
                        evicon = contra.detalleaprobacioncontrato_set.filter(status=True, espagare=True).order_by('-id')[0]
                        if evicon.esta_aprobado():
                            estado = 'SI'
        else:
            estado = 'PAGO DE CONTADO (NO REQUIERE PAGARÉ)'
        return estado

    def pago_rubro_matricula(self):
        from sagest.models import Rubro
        if self.formapagopac:
            if self.formapagopac.id == 2:
                return True if Rubro.objects.filter(status=True, inscripcion=self, admisionposgradotipo=2, cancelado=True).exists() else False
            elif self.formapagopac.id == 1:
                return True if self.total_pagado_rubro_cohorte() == self.cohortes.valorprogramacertificado else False

    def cuadre_con_epunemi(self):
        from django.db import connections
        from sagest.models import Rubro
        cuadre = False
        rubrosunemi = Rubro.objects.filter(status=True, inscripcion=self, persona=self.inscripcionaspirante.persona)
        rubrosepunemi = []
        sumaepunemi = sumarubrosunemi = 0
        cursor = connections['epunemi'].cursor()
        for rubro in rubrosunemi:
            sql = """SELECT id, valor FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND anulado=FALSE; """ % (rubro.id)
            cursor.execute(sql)
            registrorubro = cursor.fetchone()
            if registrorubro is not None:
                rubrosepunemi.append(registrorubro[0])
                sumaepunemi = sumaepunemi + registrorubro[1]

        if rubrosunemi.count() == len(rubrosepunemi):
            sumarubrosunemi = self.total_generado_rubro()

            if sumarubrosunemi == sumaepunemi:
                cuadre = True

        return cuadre

    def tiene_comprobante_subido(self):
        from sagest.models import ComprobanteAlumno
        return True if ComprobanteAlumno.objects.filter(status=True, persona=self.inscripcionaspirante.persona, asesor=self.asesor).exists() else False

    def comprobantes_leads(self):
        from sagest.models import ComprobanteAlumno
        return ComprobanteAlumno.objects.filter(status=True, persona=self.inscripcionaspirante.persona).order_by('-id')

    def mencion_cohorte(self):
        from sga.models import ItinerarioMallaEspecilidad
        mencion = ''
        if ItinerarioMallaEspecilidad.objects.filter(status=True, malla=self.cohortes.maestriaadmision.carrera.malla()).exists():
            if self.itinerario > 0:
                iti = ItinerarioMallaEspecilidad.objects.filter(status=True, malla=self.cohortes.maestriaadmision.carrera.malla(), itinerario=self.itinerario).first()
                if iti:
                    mencion = iti.nombre
                else:
                    mencion = 'TIENE ASIGNADO UN ITINERARIO INEXISTENTE'
            else:
                mencion = 'NO TIENE ASIGNADA UNA MENCIÓN'
        else:
            mencion = 'ESTA MAESTRÍA NO TIENE VARIAS MENCIONES'
        return mencion

    def comprobantes_epunemi(self):
        from django.db import connections
        try:
            cursor = connections['epunemi'].cursor()
            sql = """SELECT comp.id, comp.fecha_creacion, (NOW()::DATE - comp.fecha_creacion::DATE) AS dias, comp.curso, comp.carrera, comp.valor, comp.fechapago, comp.observacion, comp.tipocomprobante, comp.comprobantes, comp.estados, comp.cuentadeposito_id, comp.idcomprobanteunemi, RIGHT(comp.comprobantes, 4), comp.persona_id FROM sagest_comprobantealumno comp INNER JOIN sga_persona per ON comp.persona_id = per.id WHERE comp.status = TRUE AND per.cedula = '%s'""" % (self.inscripcionaspirante.persona.cedula)
            cursor.execute(sql)
            rows = cursor.fetchall()
            return rows
        except Exception as ex:
            pass

    def pedidos_epunemi(self):
        from django.db import connections
        try:
            cursor = connections['epunemi'].cursor()
            sql = """SELECT TO_CHAR(pedidoonline.fecha_creacion, 'dd-mm-YYYY') AS fecha,
                        TO_CHAR(pedidoonline.fecha_creacion, 'hh:mm') AS hora,
                        pedidoonline.estado,
                        pedidoonline.tipopago,
                        pagotransdep.tipocomprobante,
                        pedidoonline.subtotal,
                        pedidoonline.total,
                        pagotransdep.comprobantes,
                        pedidoonline.observacion,
                        (ARRAY_TO_STRING(array(SELECT rubro.nombre FROM sagest_rubro rubro WHERE rubro.id = detallepedidoonline.rubro_id), ', ')) AS rubros,
                        TO_CHAR(pedidoonline.fpago, 'dd-mm-YYYY') AS fpago,
                        pagotransdep.cuentadeposito_id                        
                        FROM crm_pedidoonline pedidoonline
                        INNER JOIN crm_detallepedidoonline detallepedidoonline ON pedidoonline.id = detallepedidoonline.pedido_id
                        LEFT JOIN crm_pagotransdep pagotransdep ON pagotransdep.pedido_id = pedidoonline.id
                        INNER JOIN sga_persona persona ON pedidoonline.persona_id = persona.id
                        WHERE pedidoonline."status" 
                        AND persona.cedula='%s' """ % (self.inscripcionaspirante.persona.cedula)
            cursor.execute(sql)
            rows = cursor.fetchall()
            return rows
        except Exception as ex:
            pass

    def fecha_primer_pago(self):
        from sagest.models import Rubro, Pago
        pago = None
        try:
            if self.formapagopac and self.formapagopac.id == 2:
                if Rubro.objects.filter(status=True, inscripcion=self, admisionposgradotipo=2).exists():
                    primerrubro = Rubro.objects.filter(status=True, inscripcion=self, admisionposgradotipo=2).order_by('id')[0]
                    pago = Pago.objects.filter(status=True, rubro = primerrubro).order_by('id')[0]
                else:
                    primerrubro = Rubro.objects.filter(status=True, inscripcion=self).order_by('id')[0]
                    pago = Pago.objects.filter(status=True, rubro = primerrubro).order_by('id')[0]
            else:
                if Rubro.objects.filter(status=True, inscripcion=self).exists():
                    primerrubro = Rubro.objects.filter(status=True, inscripcion=self).order_by('id')[0]
                    pago = Pago.objects.filter(status=True, rubro=primerrubro).order_by('id')[0]
            return pago.fecha if pago else None
        except Exception as ex:
            pass

    def comprobante_subido(self):
        from sagest.models import ComprobanteAlumno
        estado = False
        if ComprobanteAlumno.objects.filter(status=True, persona=self.inscripcionaspirante.persona, asesor=self.asesor, asesor__isnull=False).exists():
            estado = True
        # elif ComprobanteAlumno.objects.filter(status=True, persona=self.inscripcionaspirante.persona, carrera__icontains=str(self.cohortes.maestriaadmision.carrera.nombre)).exists():
        #     estado = True
        return estado

    def comprobante_subido_epunemi(self):
        try:
            from django.db import connections
            from sagest.models import ComprobanteAlumno

            estado = False
            cursor = connections['epunemi'].cursor()

            sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (self.inscripcionaspirante.persona.cedula, self.inscripcionaspirante.persona.cedula, self.inscripcionaspirante.persona.cedula)
            cursor.execute(sql)
            idalumno = cursor.fetchone()

            if self.asesor:
                if idalumno is None:
                    estado = False
                else:
                    sql = """SELECT comalu.id FROM sagest_comprobantealumno comalu INNER JOIN sga_persona perso on comalu.persona_id=perso.id 
                    WHERE perso.id=%s AND comalu.status=TRUE AND comalu.asesor = '%s' AND comalu.telefono_asesor = '%s' ORDER BY comalu.id asc LIMIT 1; """ % (idalumno[0], self.asesor.persona.nombre_completo_inverso(), self.asesor.persona.telefono)
                    cursor.execute(sql)
                    registrocomprobante = cursor.fetchone()
                    if registrocomprobante is not None:
                        estado = True
                    else:
                        estado = False
            else:
                estado = False
            return estado
        except Exception as ex:
            pass

    def get_comprobante_subido(self):
        from sagest.models import ComprobanteAlumno
        if ComprobanteAlumno.objects.filter(status=True, persona=self.inscripcionaspirante.persona, asesor=self.asesor).exists():
            return ComprobanteAlumno.objects.filter(status=True, persona=self.inscripcionaspirante.persona, asesor=self.asesor).order_by('id')[0]
        # elif ComprobanteAlumno.objects.filter(status=True, persona=self.inscripcionaspirante.persona, carrera__icontains=str(self.cohortes.maestriaadmision.carrera.nombre)).exists():
        #     return ComprobanteAlumno.objects.filter(status=True, persona=self.inscripcionaspirante.persona, carrera__icontains=str(self.cohortes.maestriaadmision.carrera.nombre)).order_by('id')[0]

    def get_comprobante_inscripcion(self):
        from sagest.models import ComprobanteAlumno
        if ComprobanteAlumno.objects.filter(status=True, inscripcioncohorte=self.id, asesor=self.asesor).exists():
            return ComprobanteAlumno.objects.filter(status=True, inscripcioncohorte=self.id, asesor=self.asesor).order_by('-id')[0]
        else:
            if ComprobanteAlumno.objects.filter(status=True, persona=self.inscripcionaspirante.persona, asesor=self.asesor).exists():
                return ComprobanteAlumno.objects.filter(status=True, asesor=self.asesor, persona=self.inscripcionaspirante.persona).order_by('-id')[0]


    def get_comprobante_subido_epunemi(self):
        from django.db import connections
        from sagest.models import ComprobanteAlumno

        try:
            cursor = connections['epunemi'].cursor()
            sql = """SELECT comalu.fecha_creacion FROM sagest_comprobantealumno comalu INNER JOIN sga_persona perso on comalu.persona_id=perso.id 
            WHERE perso.cedula='%s' AND comalu.status=TRUE AND comalu.asesor = '%s' AND comalu.telefono_asesor = '%s' ORDER BY comalu.id asc LIMIT 1; """ % (self.inscripcionaspirante.persona.cedula, self.asesor.persona.nombre_completo_inverso(), self.asesor.persona.telefono)
            cursor.execute(sql)
            registrocomprobante = cursor.fetchone()

            return registrocomprobante[0]
        except Exception as ex:
            pass

    def tiene_pedidoonline_transferencia(self):
        try:
            from django.db import connections
            from sagest.models import Rubro
            primer = Rubro.objects.filter(status=True, inscripcion=self).order_by('id').first()
            estado = False
            idpedidos = []
            cursor = connections['epunemi'].cursor()
            sql = """SELECT deta.id FROM crm_pedidoonline pedi 
                    INNER JOIN crm_detallepedidoonline deta ON deta.pedido_id = pedi.id
                    INNER JOIN sga_persona per ON pedi.persona_id = per.id
                    INNER JOIN crm_pagotransdep pag on pag.pedido_id = pedi.id
                    WHERE (per.cedula='%s' OR per.pasaporte='%s' OR per.ruc='%s') AND pedi."status"
                    AND deta."status" AND deta.rubro_id = %s AND pedi.estado IN (1,2) 
                    AND pedi.tipopago = 2 AND pag.tipocomprobante = 2""" % (
                    self.inscripcionaspirante.persona.cedula, self.inscripcionaspirante.persona.cedula,
                    self.inscripcionaspirante.persona.cedula, primer.idrubroepunemi)
            cursor.execute(sql)
            tienepedido = cursor.fetchone()

            if tienepedido is not None:
                estado = True
            cursor.close()
            return estado
        except Exception as ex:
            pass

    def fecha_pedidoonline_transferencia(self):
        try:
            from django.db import connections
            from sagest.models import Rubro
            primer = Rubro.objects.filter(status=True, inscripcion=self).order_by('id').first()
            idpedidos = []
            cursor = connections['epunemi'].cursor()
            sql = """SELECT pedi.fecha_creacion FROM crm_pedidoonline pedi 
                    INNER JOIN crm_detallepedidoonline deta ON deta.pedido_id = pedi.id
                    INNER JOIN sga_persona per ON pedi.persona_id = per.id
                    INNER JOIN crm_pagotransdep pag on pag.pedido_id = pedi.id
                    WHERE (per.cedula='%s' OR per.pasaporte='%s' OR per.ruc='%s') AND pedi."status"
                    AND deta."status" AND deta.rubro_id = %s AND pedi.estado IN (1,2) 
                    AND pedi.tipopago = 2 AND pag.tipocomprobante = 2 ORDER BY deta.id DESC LIMIT 1;""" % (
                    self.inscripcionaspirante.persona.cedula, self.inscripcionaspirante.persona.cedula,
                    self.inscripcionaspirante.persona.cedula, primer.idrubroepunemi)
            cursor.execute(sql)
            fechapedido = cursor.fetchone()
            return fechapedido[0]
        except Exception as ex:
            pass

    def tiene_pedidoonline_deposito(self):
        try:
            from django.db import connections
            from sagest.models import Rubro
            primer = Rubro.objects.filter(status=True, inscripcion=self).order_by('id').first()
            estado = False
            idpedidos = []
            cursor = connections['epunemi'].cursor()
            sql = """SELECT deta.id FROM crm_pedidoonline pedi 
                    INNER JOIN crm_detallepedidoonline deta ON deta.pedido_id = pedi.id
                    INNER JOIN sga_persona per ON pedi.persona_id = per.id
                    INNER JOIN crm_pagotransdep pag on pag.pedido_id = pedi.id
                    WHERE (per.cedula='%s' OR per.pasaporte='%s' OR per.ruc='%s') AND pedi."status"
                    AND deta."status" AND deta.rubro_id = %s AND pedi.estado IN (1,2) 
                    AND pedi.tipopago = 2 AND pag.tipocomprobante = 1""" % (
                    self.inscripcionaspirante.persona.cedula, self.inscripcionaspirante.persona.cedula,
                    self.inscripcionaspirante.persona.cedula, primer.idrubroepunemi)
            cursor.execute(sql)
            tienepedido = cursor.fetchone()

            if tienepedido is not None:
                estado = True
            cursor.close()
            return estado
        except Exception as ex:
            pass

    def fecha_pedidoonline_deposito(self):
        try:
            from django.db import connections
            from sagest.models import Rubro
            primer = Rubro.objects.filter(status=True, inscripcion=self).order_by('id').first()
            idpedidos = []
            cursor = connections['epunemi'].cursor()
            sql = """SELECT pedi.fecha_creacion FROM crm_pedidoonline pedi 
                    INNER JOIN crm_detallepedidoonline deta ON deta.pedido_id = pedi.id
                    INNER JOIN sga_persona per ON pedi.persona_id = per.id
                    INNER JOIN crm_pagotransdep pag on pag.pedido_id = pedi.id
                    WHERE (per.cedula='%s' OR per.pasaporte='%s' OR per.ruc='%s') AND pedi."status"
                    AND deta."status" AND deta.rubro_id = %s AND pedi.estado IN (1,2) 
                    AND pedi.tipopago = 2 AND pag.tipocomprobante = 1 ORDER BY deta.id DESC LIMIT 1;""" % (
                    self.inscripcionaspirante.persona.cedula, self.inscripcionaspirante.persona.cedula,
                    self.inscripcionaspirante.persona.cedula, primer.idrubroepunemi)
            cursor.execute(sql)
            fechapedido = cursor.fetchone()
            return fechapedido[0]
        except Exception as ex:
            pass

    def tiene_pedidoonline_kushki(self):
        try:
            from django.db import connections
            from sagest.models import Rubro
            primer = Rubro.objects.filter(status=True, inscripcion=self).order_by('id').first()
            estado = False
            idpedidos = []
            cursor = connections['epunemi'].cursor()
            sql = """SELECT deta.id FROM crm_pedidoonline pedi 
                    INNER JOIN crm_detallepedidoonline deta ON deta.pedido_id = pedi.id
                    INNER JOIN sga_persona per ON pedi.persona_id = per.id
                    WHERE (per.cedula='%s' OR per.pasaporte='%s' OR per.ruc='%s') AND pedi."status"
                    AND deta."status" AND deta.rubro_id = %s AND pedi.estado IN (1,2) AND pedi.tipopago = 1""" % (
                    self.inscripcionaspirante.persona.cedula, self.inscripcionaspirante.persona.cedula,
                    self.inscripcionaspirante.persona.cedula, primer.idrubroepunemi)
            cursor.execute(sql)
            tienepedido = cursor.fetchone()

            if tienepedido is not None:
                estado = True
            cursor.close()
            return estado
        except Exception as ex:
            pass

    def fecha_pedidoonline_kushki(self):
        try:
            from django.db import connections
            from sagest.models import Rubro
            primer = Rubro.objects.filter(status=True, inscripcion=self).order_by('id').first()
            idpedidos = []
            cursor = connections['epunemi'].cursor()
            sql = """SELECT pedi.fecha_creacion FROM crm_pedidoonline pedi 
                    INNER JOIN crm_detallepedidoonline deta ON deta.pedido_id = pedi.id
                    INNER JOIN sga_persona per ON pedi.persona_id = per.id
                    WHERE (per.cedula='%s' OR per.pasaporte='%s' OR per.ruc='%s') AND pedi."status"
                    AND deta."status" AND deta.rubro_id = %s AND pedi.estado IN (1,2) AND pedi.tipopago = 1 ORDER BY deta.id DESC LIMIT 1;""" % (
                    self.inscripcionaspirante.persona.cedula, self.inscripcionaspirante.persona.cedula,
                    self.inscripcionaspirante.persona.cedula, primer.idrubroepunemi)
            cursor.execute(sql)
            fechapedido = cursor.fetchone()
            return fechapedido[0]
        except Exception as ex:
            pass

    def nombre_mencion(self):
        from sga.models import ItinerarioMallaEspecilidad
        try:
            iti = ItinerarioMallaEspecilidad.objects.filter(status=True, malla=self.cohortes.maestriaadmision.carrera.malla(), itinerario=self.itinerario).order_by('-id').first()
            return iti.nombre
        except Exception as ex:
            pass

    def nombre_resolucion(self):
        from sga.models import ItinerarioMallaEspecilidad
        try:
            iti = ItinerarioMallaEspecilidad.objects.filter(status=True, malla=self.cohortes.maestriaadmision.carrera.malla(), itinerario=self.itinerario).order_by('-id').first()
            return iti.numeroresolucion if iti.numeroresolucion else ''
        except Exception as ex:
            pass

    def fecha_cancelacion(self):
        listado_fechas2 = []
        if self.comprobante_subido():
            d = {'fecha': self.get_comprobante_subido().fecha_creacion.date(),
                 'medio': 'COMPROBANTE SUBIDO POR ASESOR'}
            listado_fechas2.append(d)
        elif self.comprobante_subido_epunemi():
            d = {'fecha': self.get_comprobante_subido_epunemi(), 'medio': 'COMPROBANTE SUBIDO POR CONSULTA SALDOS'}
            listado_fechas2.append(d)
        elif self.total_pagado_rubro_cohorte() > 0:
            d = {'fecha': self.fecha_primer_pago(), 'medio': 'VENTA DIRECTA DE CAJA'}
            listado_fechas2.append(d)
        first = listado_fechas2[0]['fecha']
        return first

    def tiene_grupo_examen(self):
        return True if self.integrantegrupoexamenmsc_set.filter(grupoexamen__estado_emailentrevista=2, status=True, inscripcion__status=True).exists() else False

    def grupo_examen(self):
        return self.integrantegrupoexamenmsc_set.get(grupoexamen__estado_emailentrevista=2, status=True)

    def tiene_grupo_entrevista(self):
        return True if self.integrantegrupoentrevitamsc_set.filter(grupoentrevista__estado_emailentrevista=2, status=True, inscripcion__status=True).exists() else False

    def grupo_entrevista(self):
        return self.integrantegrupoentrevitamsc_set.get(grupoentrevista__estado_emailentrevista=2, status=True)

    def matricula_activa_cohorte(self):
        from sagest.models import Matricula
        return True if Matricula.objects.filter(status=True, inscripcion=self.inscripcion, inscripcion__carrera=self.cohortes.maestriaadmision.carrera, retiradomatricula=False).exists() else False

    def retirado_matricula(self):
        from sagest.models import Matricula
        return True if Matricula.objects.filter(status=True, inscripcion=self.inscripcion,
                                                inscripcion__carrera=self.cohortes.maestriaadmision.carrera,
                                                retiradomatricula=True).exists() else False
    def contrato_posgrado(self):
        return Contrato.objects.filter(status=True, inscripcion=self, inscripcion__status=True).last()

    def garante_posgrado(self):
        return True if GarantePagoMaestria.objects.filter(status=True, inscripcioncohorte=self).exists() else False

    def tiene_contrato_anulado(self):
        return True if Contrato.objects.filter(status=False, estado=5, inscripcion=self).exists() else False

    def reservar_lead_territorio(self):
        from sga.funciones import notificacion4
        reservacion = None
        if AsesorTerritorio.objects.filter(status=True, canton=self.inscripcionaspirante.persona.canton).exists():
            if not self.tiene_reservaciones() and self.leaddezona:
                territorio = AsesorTerritorio.objects.filter(status=True, canton=self.inscripcionaspirante.persona.canton).first()
                asesor = AsesorComercial.objects.get(status=True, pk=territorio.asesor.id)
                reservacion = HistorialReservacionProspecto(inscripcion_id=self.id,
                                                            persona_id=asesor.persona.id,
                                                            observacion='Reservado automáticamente por concepto de zonas o territorio')
                reservacion.save()

                asunto = u"RESERVACIÓN DE PROSPECTO DE TERRITORIO"
                observacion = f'Se le comunica que se ha reservado de forma automática al prospecto {self} para su posterior asignación al asesor de territorio {reservacion.persona.nombre_completo_inverso()} por concepto de atención de zonas. Por favor, dar seguimiento a la reservación.'

                supervisores = Persona.objects.filter(status=True, id__in=variable_valor('PERSONAL_SUPERVISION'))

                for supervisor in supervisores:
                    para = supervisor
                    perfiu = supervisor.perfilusuario_administrativo()

                    notificacion4(asunto, observacion, para, None,
                                  '/comercial?action=leadsregistrados&id=' + str(asesor.id) + '&s=' + str(self.inscripcionaspirante.persona.cedula) + '&idc=0',
                                  reservacion.pk, 1,
                                  'sga', HistorialReservacionProspecto, perfiu)
        else:
            self.leaddezona = False
            self.save()
        return reservacion

    def asignar_asesor_convenio(self):
        from sga.funciones import notificacion4
        if self.convenio:
            if ConvenioAsesor.objects.filter(status=True, convenio=self.convenio).exists():
                convenio = ConvenioAsesor.objects.filter(status=True, convenio=self.convenio).first()
                self.asesor = convenio.asesor
                self.estado_asesor = 2
                self.save()

                histo = HistorialAsesor(inscripcion_id=self.id, fecha_inicio=self.fecha_modificacion,
                                        fecha_fin=None, asesor=self.asesor,
                                        observacion='Fue asignado a un asesor relacionado al convenio seleccionado')
                histo.save()

                asunto= u"POSTULACIÓN A MAESTRIA ASIGNADA POR CONVENIO"
                observacion= u"Se le comunica que se le ha asignado la siguiente postulación mediante la selección de convenio"
                para = self.asesor.persona
                perfiu = para.perfilusuario_administrativo()
                notificacion4(asunto, observacion, para, None,
                              '/comercial?s=' + str(self.inscripcionaspirante.persona.cedula) + '&idc=0&ide=0&ida=0&idanio=2024&desde=&hasta=&cantidad=25&idcan=0',
                              self.pk, 1, 'sga', InscripcionCohorte, perfiu)
                return True
            else:
                return False
        else:
            return False

    def asignar_mismo_asesor(self):
        if InscripcionCohorte.objects.filter(status=True, asesor__isnull=False, inscripcionaspirante__persona=self.inscripcionaspirante.persona, asesor__activo=True).exists():
            asesor = InscripcionCohorte.objects.filter(status=True, asesor__isnull=False, inscripcionaspirante__persona=self.inscripcionaspirante.persona, asesor__activo=True).order_by('-id').first().asesor
            self.asesor = asesor
            self.estado_asesor = 2
            self.save()

            histo = HistorialAsesor(inscripcion_id=self.id, fecha_inicio=self.fecha_modificacion,
                                    fecha_fin=None, asesor=self.asesor, observacion='Fue asignado a un asesor que ya lo trabajó anteriormente')
            histo.save()
            return True
        else:
            return False

    def revivir_postulacion(self):
        from sagest.models import Rubro
        from django.db import connections

        hoy = datetime.now().date()
        per = Persona.objects.get(pk=1)
        if CohorteMaestria.objects.values('id').filter(maestriaadmision__carrera=self.cohortes.maestriaadmision.carrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True, procesoabierto=True).exists():
            cohorte = CohorteMaestria.objects.filter(maestriaadmision__carrera=self.cohortes.maestriaadmision.carrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True, procesoabierto=True).first()

            listarequisitos = EvidenciaRequisitosAspirante.objects.filter(inscripcioncohorte=self,
                                                                          requisitos__requisito__claserequisito__clasificacion=1)
            canrequi = RequisitosMaestria.objects.filter(status=True, obligatorio=True,
                                                         cohorte__id=cohorte.id,
                                                         requisito__claserequisito__clasificacion=1).distinct().count()
            listarequisitosfinan = EvidenciaRequisitosAspirante.objects.filter(inscripcioncohorte=self,
                                                                               requisitos__requisito__claserequisito__clasificacion=3)

            if self.subirrequisitogarante:
                canrequifi = RequisitosMaestria.objects.filter(status=True, obligatorio=True,
                                                               cohorte__id=cohorte.id,
                                                               requisito__claserequisito__clasificacion=3).distinct().count()
            else:
                canrequifi = RequisitosMaestria.objects.filter(status=True, obligatorio=True,
                                                               cohorte__id=cohorte.id,
                                                               requisito__claserequisito__clasificacion=3).exclude(
                    requisito__id__in=[56, 57, 59]).distinct().count()

            # SI TIENE EVIDENCIAS DE ADMISION EN LA COHORTE PASADA
            for lis in listarequisitos:
                if RequisitosMaestria.objects.filter(requisito=lis.requisitos.requisito, cohorte_id=cohorte.id,
                                                     status=True):
                    requi = RequisitosMaestria.objects.filter(requisito=lis.requisitos.requisito,
                                                              cohorte_id=cohorte.id, status=True)[0]
                    lis.requisitos = requi
                    lis.save()

            canevi = EvidenciaRequisitosAspirante.objects.filter(inscripcioncohorte=self,
                                                                 requisitos__cohorte__id=cohorte.id,
                                                                 requisitos__requisito__claserequisito__clasificacion=1,
                                                                 detalleevidenciarequisitosaspirante__estado_aprobacion=2,
                                                                 requisitos__status=True).distinct().count()

            if canevi == canrequi:
                self.estado_aprobador = 2
            else:
                self.estado_aprobador = 1
                self.todosubido = False
                self.preaprobado = False

            self.save()

            # SI TIENE EVIDENCIAS DE FINANCIAMIENTO EN LA COHORTE PASADA
            if self.formapagopac:
                if self.formapagopac.id == 2:
                    for listf in listarequisitosfinan:
                        if RequisitosMaestria.objects.filter(requisito=listf.requisitos.requisito,
                                                             cohorte_id=cohorte.id, status=True,
                                                             requisito__claserequisito__clasificacion=3):
                            requifinan = RequisitosMaestria.objects.filter(requisito=listf.requisitos.requisito,
                                                                           cohorte_id=cohorte.id, status=True,
                                                                           requisito__claserequisito__clasificacion=3)[0]
                            listf.requisitos = requifinan
                            listf.save()

                    canevifi = EvidenciaRequisitosAspirante.objects.filter(inscripcioncohorte=self,
                                                                           requisitos__cohorte__id=cohorte.id,
                                                                           requisitos__requisito__claserequisito__clasificacion=3,
                                                                           detalleevidenciarequisitosaspirante__estado_aprobacion=2).count()

                    if canevifi == canrequifi:
                        self.estadoformapago = 2
                    else:
                        self.estadoformapago = 1
                        self.todosubidofi = False

                    self.save()

            # SI TIENE RUBROS GENERADOS
            chorte = CohorteMaestria.objects.get(id=cohorte.id, status=True)
            if Rubro.objects.filter(inscripcion=self, status=True).exists():
                rubros = Rubro.objects.filter(inscripcion=self, status=True)
                for rubro in rubros:
                    if rubro.idrubroepunemi != 0:
                        cursor = connections['epunemi'].cursor()
                        sql = """SELECT id FROM sagest_pago WHERE rubro_id=%s; """ % (rubro.idrubroepunemi)
                        cursor.execute(sql)
                        tienerubropagos = cursor.fetchone()

                        if tienerubropagos is None:
                            sql = """DELETE FROM sagest_rubro WHERE sagest_rubro.id=%s AND sagest_rubro.idrubrounemi=%s; """ % (
                                rubro.idrubroepunemi, rubro.id)
                            cursor.execute(sql)
                            cursor.close()

                        rubro.status = False
                        rubro.save()

            if self.cohortes.tipo == 1:
                if IntegranteGrupoExamenMsc.objects.filter(status=True, inscripcion=self).exists():
                    lista = IntegranteGrupoExamenMsc.objects.filter(status=True, inscripcion=self)
                    for li in lista:
                        li.status = False
                        li.save()

                if IntegranteGrupoEntrevitaMsc.objects.filter(status=True, inscripcion=self).exists():
                    lista2 = IntegranteGrupoEntrevitaMsc.objects.filter(status=True, inscripcion=self)
                    for li2 in lista2:
                        li2.status = False
                        li2.save()

            elif self.cohortes.tipo == 2:
                if IntegranteGrupoExamenMsc.objects.filter(status=True, inscripcion=self).exists():
                    lista = IntegranteGrupoExamenMsc.objects.filter(status=True, inscripcion=self)
                    for li in lista:
                        li.status = False
                        li.save()

            if Contrato.objects.filter(status=True, inscripcion=self).exists():
                contratopos = Contrato.objects.get(status=True, inscripcion=self)

                detalleevidencia = DetalleAprobacionContrato(contrato_id=contratopos.id, espagare=False,
                                                             observacion='Rechazado por cambio de cohorte',
                                                             persona=per, estado_aprobacion=3,
                                                             fecha_aprobacion=datetime.now(),
                                                             archivocontrato=contratopos.archivocontrato)
                detalleevidencia.save()

                if contratopos.inscripcion.formapagopac.id == 2:
                    detalleevidencia = DetalleAprobacionContrato(contrato_id=contratopos.id, espagare=True,
                                                                 observacion='Rechazado por cambio de cohorte',
                                                                 persona=per, estado_aprobacion=3,
                                                                 fecha_aprobacion=datetime.now(),
                                                                 archivocontrato=contratopos.archivopagare)
                    detalleevidencia.save()

                contratopos.estado = 3
                contratopos.estadopagare = 3
                contratopos.save()

            observacion = f'Cambio de {self.cohortes} a {chorte}.'
            cambio = CambioAdmitidoCohorteInscripcion(inscripcionCohorte=self, cohortes=chorte, observacion=observacion)
            cambio.save()

            self.cohortes_id = chorte
            self.tiporespuesta = None
            self.status = True
            self.save()
        else:
            self.tiporespuesta = None
            self.status = True
            self.save()
        return True

    def subio_requisitos_homologacion(self):
        estado = False
        cantirequisitos = RequisitosMaestria.objects.filter(status=True, maestria=self.cohortes.maestriaadmision, requisito__claserequisito__clasificacion__id=4, obligatorio=True).count()
        cantidadrequisubidos = EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=self, requisitos__maestria=self.cohortes.maestriaadmision,
                                                                           requisitos__requisito__claserequisito__clasificacion__id=4, requisitos__obligatorio=True).count()
        if cantirequisitos == cantidadrequisubidos:
            estado = True

        return estado

    def completo_datos_matrices(self):
        estado = '0'
        if self.inscripcionaspirante.persona.paisnacimiento is None:
            estado = '1'
        if self.inscripcionaspirante.persona.provincianacimiento is None:
            estado = '1'
        if self.inscripcionaspirante.persona.cantonnacimiento is None:
            estado = '1'
        if self.inscripcionaspirante.persona.pais is None:
            estado = '1'
        if self.inscripcionaspirante.persona.provincia is None:
            estado = '1'
        if self.inscripcionaspirante.persona.canton is None:
            estado = '1'
        if self.inscripcionaspirante.persona.mi_perfil().raza is None:
            estado = '1'
        if self.inscripcionaspirante.persona.mi_perfil().raza and self.inscripcionaspirante.persona.mi_perfil().raza.id == 1 and self.inscripcionaspirante.persona.mi_perfil().nacionalidadindigena is None:
            estado = '1'
        if self.inscripcionaspirante.persona.mi_perfil().tienediscapacidad:
            if self.inscripcionaspirante.persona.mi_perfil().tipodiscapacidad is None:
                estado = '1'
            if self.inscripcionaspirante.persona.mi_perfil().porcientodiscapacidad is None or self.inscripcionaspirante.persona.mi_perfil().porcientodiscapacidad == 0:
                estado = '1'
            if self.inscripcionaspirante.persona.mi_perfil().carnetdiscapacidad is None:
                estado = '1'

        enteros_resultantes = [int(num) for num in variable_valor('IDS_INSCRITOS_P')]

        if self.id in enteros_resultantes:
            estado = '0'
        return estado

    def datos_restantes(self):
        estado = ''
        if self.inscripcionaspirante.persona.paisnacimiento is None:
            estado += 'País de origen, '
        if self.inscripcionaspirante.persona.provincianacimiento is None:
            estado += 'Provincia de origen, '
        if self.inscripcionaspirante.persona.cantonnacimiento is None:
            estado += 'Canton de origen, '
        if self.inscripcionaspirante.persona.pais is None:
            estado += 'País de residencia, '
        if self.inscripcionaspirante.persona.provincia is None:
            estado += 'Provincia de residencia, '
        if self.inscripcionaspirante.persona.canton is None:
            estado += 'Canton de residencia, '
        if self.inscripcionaspirante.persona.mi_perfil().raza is None:
            estado += 'Etnia, '
        if self.inscripcionaspirante.persona.mi_perfil().raza and self.inscripcionaspirante.persona.mi_perfil().raza.id == 1 and self.inscripcionaspirante.persona.mi_perfil().nacionalidadindigena is None:
            estado += 'Nacionalidad Indígena, '
        if self.inscripcionaspirante.persona.mi_perfil().tienediscapacidad:
            if self.inscripcionaspirante.persona.mi_perfil().tipodiscapacidad is None:
                estado += 'Tipo de discapacidad, '
            if self.inscripcionaspirante.persona.mi_perfil().porcientodiscapacidad is None or self.inscripcionaspirante.persona.mi_perfil().porcientodiscapacidad == 0:
                estado += 'Porcentaje de discapacidad, '
            if self.inscripcionaspirante.persona.mi_perfil().carnetdiscapacidad is None:
                estado += 'Carnet de discapacidad'
        return estado

    def obj_venta(self):
        return VentasProgramaMaestria.objects.filter(status=True, valida=True, facturado=True).first()

    def horario_seleccionado(self):
        horario = None
        if DetalleAtencionAdmitido.objects.filter(status=True, admitido=self, activo=True).exists():
            horario = DetalleAtencionAdmitido.objects.filter(status=True, admitido=self, activo=True).first()
        return horario

    def delete(self, *args, **kwargs):
        if self.estado_aprobador == 2:
            raise NameError(u"No puede eliminar la inscripción, porque el lead se encuentra admitido en el programa de maestría")
        if self.tiene_contrato_subido() or self.tiene_pagare_subido():
            raise NameError(u"No puede eliminar la inscripción, porque el lead tiene subido contratos")
        if self.total_pagado_rubro_cohorte() > 0:
            raise NameError(u"No puede eliminar la insripción, porque el lead registra pagos de rubros de maestría")
        super(InscripcionCohorte, self).delete(*args, **kwargs)

class DetallePreAprobacionPostulante(ModeloBase):
    inscripcion = models.ForeignKey(InscripcionCohorte, blank=True, null=True, verbose_name=u'Prospecto', on_delete=models.CASCADE)
    preaprobado = models.BooleanField(default=False, verbose_name=u'Verfica si el postulante cumple con sus requisitos de admision')
    dias = models.IntegerField(default=0, verbose_name=u'Dias que tomó la aprobación')

    def __str__(self):
        return u'%s' % self.inscripcion

    class Meta:
        verbose_name = "Detalle de Pre aprobación de Postulante"
        verbose_name_plural = "Detalles de Pre aprobación de Postulante"
        ordering = ['-id']


class HistorialRespuestaProspecto(ModeloBase):
    inscripcion = models.ForeignKey(InscripcionCohorte, blank=True, null=True, verbose_name=u'Prospecto', on_delete=models.CASCADE)
    tiporespuesta = models.ForeignKey(TipoRespuestaProspecto, blank=True, null=True, verbose_name=u'Respuesta del Prospecto', on_delete=models.CASCADE)
    observacion = models.TextField(blank=True, null=True, verbose_name=u"Observación")

    def __str__(self):
        return u'%s' % self.inscripcion.inscripcionaspirante

    class Meta:
        verbose_name = "Historial de Respuesta de Contacto de Lead"
        verbose_name_plural = "Historiales de Respuesta de Contacto de Leads"
        ordering = ['-id']

class HistorialReservacionProspecto(ModeloBase):
    inscripcion = models.ForeignKey(InscripcionCohorte, blank=True, null=True, verbose_name=u'Prospecto', on_delete=models.CASCADE)
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Asesor Comercial', on_delete=models.CASCADE)
    observacion = models.TextField(blank=True, null=True, verbose_name=u"Observación")
    estado_asesor = models.IntegerField(choices=ESTADO_ASESOR_COMERCIAL, default=1, verbose_name=u'Estado de la Reservación')

    def __str__(self):
        return u'%s' % self.inscripcion.inscripcionaspirante

    class Meta:
        verbose_name = "Historial de Reservación de Prospecto"
        verbose_name_plural = "Historiales de Reservación de Prospecto"
        ordering = ['-id']



class DetalleAprobacionFormaPago(ModeloBase):
    inscripcion = models.ForeignKey(InscripcionCohorte, blank=True, null=True, verbose_name=u'Prospecto', on_delete=models.CASCADE)
    formapagopac = models.ForeignKey('inno.TipoFormaPagoPac', blank=True, null=True, verbose_name=u'Forma de Pago', on_delete=models.CASCADE)
    estadoformapago = models.IntegerField(choices=ESTADO_FORMA_PAGO, default=1, verbose_name=u'Estado de forma de pago')
    observacion = models.TextField(blank=True, null=True, verbose_name=u"Observación")
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Asesor Comercial/Financiamiento', on_delete=models.CASCADE)
    tipofinanciamiento = models.ForeignKey(ConfigFinanciamientoCohorte, blank=True, null=True, verbose_name=u'Tipo de Financiamiento', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.inscripcion.inscripcionaspirante

    class Meta:
        verbose_name = u"Detalle de Aprobacion"
        verbose_name_plural = u"Detalles de Aprobacion"
        ordering = ['-id']

    def estadohistorial(self):
        return dict(ESTADO_FORMA_PAGO)[self.estadoformapago]


class GarantePagoMaestria(ModeloBase):
    inscripcioncohorte = models.ForeignKey(InscripcionCohorte, blank=True, null=True, verbose_name=u'Aspirante', on_delete=models.CASCADE)
    # personajuridica = models.IntegerField(choices=GARANTE_PERSONA_JURIDICA, default=2, verbose_name=u'Es persona jurídica')
    cedula = models.CharField(default='', max_length=20, verbose_name=u"Número de cédula")
    nombres = models.CharField(default='', max_length=100, verbose_name=u'Nombres')
    apellido1 = models.CharField(default='', max_length=50, verbose_name=u"1er Apellido")
    apellido2 = models.CharField(default='', max_length=50, verbose_name=u"2do Apellido")
    genero = models.ForeignKey("sga.Sexo", blank=True, null=True, verbose_name=u'Género', on_delete=models.CASCADE)
    # estadocivil = models.ForeignKey('sga.PersonaEstadoCivil', blank=True, null=True,verbose_name=u"Estado civil", on_delete=models.CASCADE)
    email = models.CharField(default='', max_length=200, verbose_name=u"Correo electrónico")
    telefono = models.CharField(default='', max_length=50, verbose_name=u"Teléfono movil")
    direccion = models.CharField(default='', max_length=300, verbose_name=u"Dirección")
    # relaciondependencia = models.IntegerField(choices=GARANTE_RELACION_DEPENDENCIA, blank=True, null=True, verbose_name=u'Trabaja con relacción de dependencia')

    def __str__(self):
        return u'%s - %s %s %s' % (self.cedula, self.nombres, self.apellido1, self.apellido2)

    class Meta:
        verbose_name = u"Garante Pago Maestría"
        verbose_name_plural = u"Garantes Pago Maestría"
        ordering = ['-id']

    def nombre_completo(self):
        return self.nombres + ' ' + self.apellido1 + ' ' + self.apellido2

    def save(self, *args, **kwargs):
        self.nombres = self.nombres.strip().upper()
        self.apellido1 = self.apellido1.strip().upper()
        self.apellido2 = self.apellido2.strip().upper() if self.apellido2 else ''
        self.direccion = self.direccion.strip().upper()
        super(GarantePagoMaestria, self).save(*args, **kwargs)

class SecuenciaContratoPagare(ModeloBase):
    anioejercicio = models.ForeignKey('sagest.AnioEjercicio', verbose_name=u'Anio Ejercicio', on_delete=models.CASCADE)
    secuenciacontrato = models.IntegerField(default=0, verbose_name=u'Secuencia Contratos')
    secuenciapagare = models.IntegerField(default=0, verbose_name=u'Secuencia Pagarés')

    class Meta:
        verbose_name = u"Secuencia de contrato y pagaré"
        verbose_name_plural = u"Secuencias de contratos y pagarés"

    def save(self, *args, **kwargs):
        super(SecuenciaContratoPagare, self).save(*args, **kwargs)

class RecordatorioPagoMaestrante(ModeloBase):
    matricula = models.ForeignKey('sga.Matricula', blank=True, null=True, verbose_name=u'Maestrante', on_delete=models.CASCADE)
    rubro = models.ForeignKey('sagest.Rubro', verbose_name=u'Rubro Vencido', blank=True, null=True, on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='recordatoriomaestrante/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo de recordatorio de pagos vencidos')

    def __str__(self):
        return u'%s' % self.matricula.inscripcion.persona

    class Meta:
        verbose_name = u"Recordatorio de pago"
        verbose_name_plural = u"Recordatorios de pago"
        ordering = ['-id']

class Contrato(ModeloBase):
    inscripcion = models.ForeignKey(InscripcionCohorte, blank=True, null=True, verbose_name=u'Aspirante', on_delete=models.CASCADE)
    numerocontrato = models.IntegerField(blank=True, null=True, verbose_name=u'Numero de contrato')
    fechacontrato = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha de contrato')
    formapago = models.ForeignKey('inno.TipoFormaPagoPac', null=True, blank=True, verbose_name=u'Forma de Pago', on_delete=models.CASCADE)
    estado = models.IntegerField(choices=ESTADO_CONTRATO, default=1, verbose_name=u'Estado')
    archivocontrato = models.FileField(upload_to='contratopagoaspitanteposgradofirmado/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo de contrato aspirante posgrado firmado')
    observacion = models.TextField(blank=True, null=True, verbose_name=u'Observacion archivo contrato')
    numeropagare = models.IntegerField(blank=True, null=True, verbose_name=u'Numero de pagaré')
    fechapagare = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha de pagaré')
    estadopagare = models.IntegerField(choices=ESTADO_CONTRATO, default=1, verbose_name=u'Estado de pagaré')
    archivopagare = models.FileField(upload_to='pagareaspitanteposgradofirmado/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo de pagaré aspirante posgrado firmado')
    observacionpagare = models.TextField(blank=True, null=True, verbose_name=u'Observación archivo pagaré')
    tablaamortizacionajustada = models.BooleanField(default=False, verbose_name=u'¿Se há ajustado la tabla de amortización?')
    contratolegalizado = models.BooleanField(default=False, verbose_name=u'¿Se há legalizado contrato?')
    respaldoarchivocontrato = models.FileField(upload_to='respaldocontratopago/%Y/%m/%d', blank=True, null=True, verbose_name=u'Respaldo cotrato pago')
    archivodescargado = models.FileField(upload_to='archivodescargado', blank=True, null=True, verbose_name=u'Contrato descargado')
    archivooficiodescargado = models.FileField(upload_to='oficiodescargado', blank=True, null=True, verbose_name=u'Archivo de solicitud de terminación de contrato descargado')
    archivooficio = models.FileField(upload_to='oficioterminacion/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo de solicitud de terminación de contrato firmado')
    motivo_terminacion = models.IntegerField(choices=MOTIVO_OFICIO, default=0, verbose_name=u'Motivo de terminación')

    def __str__(self):
        return u'%s' % self.inscripcion.inscripcionaspirante

    def ultima_evidencia(self):
        if self.detalleaprobacioncontrato_set.filter(status=True, espagare=False, esoficio=False).exists():
            return self.detalleaprobacioncontrato_set.filter(status=True, espagare=False, esoficio=False).order_by('-id')[0]
        return None

    def contrato_acorde_formapago(self):
        try:
            if self.archivocontrato:
                pdf2contrato = PyPDF2.PdfFileReader(self.archivocontrato)
                if pdf2contrato:
                    numeropagina = pdf2contrato.numPages-1
                    if self.inscripcion.formapagopac.id == 1:
                        if numeropagina == 5:
                            return True
                    else:
                        if self.inscripcion.formapagopac.id == 2:
                            if numeropagina == 6:
                                return True
            return False
        except Exception as ex:
            return None


    def ultima_evidencia_estado(self):
        if self.detalleaprobacioncontrato_set.filter(status=True, espagare=False).exists():
            deta = self.detalleaprobacioncontrato_set.filter(status=True, espagare=False).order_by('-id')[0]
            if deta.estado_aprobacion == 1:
                return 'PENDIENTE'
            elif deta.estado_aprobacion == 2:
                return 'APROBADO'
            elif deta.estado_aprobacion == 3:
                return 'RECHAZADO'
        return None

    def ultima_evidencia_aspirante(self):
        if self.detalleaprobacioncontrato_set.filter(status=True, espagare=False, estadorevision=1).exists():
            return self.detalleaprobacioncontrato_set.filter(status=True, espagare=False, estadorevision=1).order_by('-id')[0]
        return None

    def download_evidencia(self):
        return self.archivocontrato.url

    def download_evidencia_respaldo(self):
        return self.respaldoarchivocontrato.url

    def download_descargado(self):
        return self.archivodescargado.url

    def download_oficio(self):
        return self.archivooficio.url

    def ultima_evidenciapagare(self):
        if self.detalleaprobacioncontrato_set.filter(status=True, espagare=True, esoficio=False).exists():
            return self.detalleaprobacioncontrato_set.filter(status=True, espagare=True, esoficio=False).order_by('-id')[0]
        return None

    def ultima_evidenciaoficio(self):
        if self.detalleaprobacioncontrato_set.filter(status=True, esoficio=True).exists():
            return self.detalleaprobacioncontrato_set.filter(status=True, esoficio=True).order_by('-id')[0]
        return None

    def ultima_evidenciapagare_estado(self):
        if self.detalleaprobacioncontrato_set.filter(status=True, espagare=True).exists():
            deta = self.detalleaprobacioncontrato_set.filter(status=True, espagare=True).order_by('-id')[0]
            if deta.estado_aprobacion == 1:
                return 'PENDIENTE'
            elif deta.estado_aprobacion == 2:
                return 'APROBADO'
            elif deta.estado_aprobacion == 3:
                return 'RECHAZADO'
        return None

    def ultima_evidencia_aspirantepagare(self):
        if self.detalleaprobacioncontrato_set.filter(status=True, espagare=True, estadorevision=1).exists():
            return self.detalleaprobacioncontrato_set.filter(status=True, espagare=True, estadorevision=1).order_by('-id')[0]
        return None

    def download_evidenciapagare(self):
        return self.archivopagare.url

    def estado_estudio(self):
        from sga.models import Graduado, TemaTitulacionPosgradoMatricula
        estado = '1'
        if self.inscripcion.inscripcion:
            if Graduado.objects.filter(status=True, inscripcion_id=self.inscripcion.inscripcion.id).exists():
                estado = '3'
            elif TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula__inscripcion_id=self.inscripcion.inscripcion.id).exists():
                estado = '2'
        return estado

    class Meta:
        verbose_name = u"Contrato de pago"
        verbose_name_plural = u"Contratos de pago"
        ordering = ['-id']

class DetalleAprobacionContrato(ModeloBase):
    contrato = models.ForeignKey(Contrato, blank=True, null=True, verbose_name=u'Contrato', on_delete=models.CASCADE)
    estadorevision = models.IntegerField(choices=ESTADO_CONTRATO, default=1, verbose_name=u'Estado Revisión')
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Quien aprueba', on_delete=models.CASCADE)
    estado_aprobacion = models.IntegerField(choices=ESTADO_CONTRATO, default=1, verbose_name=u'Estado Aprobacion')
    fecha_aprobacion = models.DateTimeField(blank=True, null=True, verbose_name=u"Fecha de aprobacion o rechazo")
    observacion = models.TextField(blank=True, null=True, verbose_name=u"Observación aprobador")
    espagare = models.BooleanField(default=False, verbose_name=u'¿Es un registro de pagaré?')
    esoficio = models.BooleanField(default=False, verbose_name=u'¿Es un registro de oficio?')
    archivocontrato = models.FileField(upload_to='contratopagoaspitanteposgradofirmado/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo de contrato aspirante posgrado firmado')
    archivopagare = models.FileField(upload_to='pagareaspitanteposgradofirmado/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo de pagaré aspirante posgrado firmado')
    archivooficio = models.FileField(upload_to='oficioterminacion/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo de solicitud de terminación de contrato')
    motivo_terminacion = models.IntegerField(choices=MOTIVO_OFICIO, default=0, verbose_name=u'Motivo de terminación')

    def __str__(self):
        return u'%s' % self.contrato.inscripcion.inscripcionaspirante

    def esta_aprobado(self):
        return True if self.estado_aprobacion == 2 else False

    def esta_rechazado(self):
        return True if self.estado_aprobacion == 3 else False

    def esta_pendiente(self):
        return True if self.estadorevision == 1 else False

    def esta_con_pendiente(self):
        return True if self.estado_aprobacion == 1 else False

    def esta_con_rechazado(self):
        return True if self.estado_aprobacion == 3 else False

    def responsable(self):
        return Persona.objects.get(status=True, usuario_id=self.usuario_creacion.id)

    def download_evidencia(self):
        return self.archivocontrato.url

    def download_evidenciapagare(self):
        return self.archivopagare.url

    def download_evidenciaoficio(self):
        return self.archivooficio.url

    class Meta:
        verbose_name = u"Detalle de Aprobacion"
        verbose_name_plural = u"Detalles de Aprobacion"
        ordering = ['-id']

    def save(self, *args, **kwargs):
        if self.observacion:
            self.observacion = self.observacion.upper()
        super(DetalleAprobacionContrato, self).save(*args, **kwargs)

class TablaAmortizacion(ModeloBase):
    contrato = models.ForeignKey(Contrato, blank=True, null=True, verbose_name=u'Contrato', on_delete=models.CASCADE)
    # numerocuota = models.IntegerField(default=0, verbose_name=u'Número de cuota')
    cuota = models.IntegerField(default=0, verbose_name=u'Número de cuota')
    nombre = models.CharField(max_length= 500, blank=True, null=True, verbose_name=u'Nombre')
    valor = models.DecimalField(default=0, max_digits=30, decimal_places=2, verbose_name=u'Valor')
    # fechainiciopago= models.DateField(blank=True, null=True, verbose_name=u"Fecha de aprobacion o rechazo")
    # fechafinpago = models.DateField(blank=True, null=True, verbose_name=u"Fecha de aprobacion o rechazo")
    fecha = models.DateField(blank=True, null=True, verbose_name=u"Fecha ")
    fechavence = models.DateField(blank=True, null=True, verbose_name=u"Fecha vence")

    def __str__(self):
        return u'%s' % self.nombre

    # def esta_pendiente(self):
    #     return True if self.estadorevision == 1 else False

    def esta_enuso(self):
        return True if self.rubro_set.filter(status=True) else False

    class Meta:
        verbose_name = u"Tabla de amortización"
        verbose_name_plural = u"Tablas de amortización"
        ordering = ['cuota']

    def save(self, *args, **kwargs):
        if self.nombre:
            self.nombre = self.nombre.upper()
        super(TablaAmortizacion, self).save(*args, **kwargs)

class HistorialAsesor(ModeloBase):
    inscripcion = models.ForeignKey(InscripcionCohorte, blank=True, null=True, verbose_name=u'Lead', on_delete=models.CASCADE)
    fecha_inicio = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha de Inicio Asesor')
    fecha_fin = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha de Fin Asesor')
    asesor = models.ForeignKey(AsesorComercial, blank=True, null=True, verbose_name=u'Asesor Comercial', on_delete=models.CASCADE)
    observacion = models.TextField(blank=True, null=True, verbose_name=u"Observación")

    def __str__(self):
        return u'%s' % self.inscripcion.inscripcionaspirante

    class Meta:
        verbose_name = u"Historial Asesor"
        verbose_name_plural = u"Historiales Asesores"
        ordering = ['-id']

class CambioAdmitidoCohorteInscripcion(ModeloBase):
    observacion = models.CharField(default='', max_length=500, verbose_name=u"Observación")
    inscripcionCohorte = models.ForeignKey(InscripcionCohorte, blank=True, null=True, verbose_name=u'Inscripción cohorte', on_delete=models.CASCADE)
    cohortes = models.ForeignKey(CohorteMaestria, blank=True, null=True, verbose_name=u'Cohorte maestría', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.cohortes

class TipoPago(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u"Nombre")

    def __str__(self):
        return u'%s' % self.nombre


class Pago(ModeloBase):
    inscripcioncohorte = models.ForeignKey(InscripcionCohorte, blank=True, null=True, verbose_name=u'InscripcionCohorte', on_delete=models.CASCADE)
    inscripcion = models.ForeignKey('sga.Inscripcion', blank=True, null=True, verbose_name=u'Inscripcion', on_delete=models.CASCADE)
    tipo = models.ForeignKey(TipoPago, blank=True, null=True, verbose_name=u'Tipo', on_delete=models.CASCADE)
    numerocuota = models.FloatField(default=0, blank=True, null=True,verbose_name=u'Numero cuota')
    cancelado = models.BooleanField(default=False, verbose_name=u'Cancelado')

    def __str__(self):
        return u'%s' % self.inscripcioncohorte

    def valorpagado(self):
        if self.cuotapago_set.filter(status=True).exists():
            return self.cuotapago_set.filter(status=True)[0].valor
        else:
            return ''

    def valorpagadopago(self):
        if self.cuotapago_set.filter(status=True).exists():
            return self.cuotapago_set.filter(status=True)[0].valor


    # def valorincompleto(self):
    #     if self.cuotapagadas_set.filter(cancelado=False, status=True).exists():
    #         return self.cuotapagadas_set.filter(cancelado=False, status=True).aggregate(valor=Sum('valor'))['valor']
    #     else:
    #         return ''


class CuotaPago(ModeloBase):
    pago = models.ForeignKey(Pago, verbose_name=u'Persona', on_delete=models.CASCADE)
    fechapago = models.DateField(blank=True, null=True, verbose_name=u"Fecha de pago")
    valor = models.FloatField(default=0, verbose_name=u'Valor mensual')

    def __str__(self):
        return u'%s' % self.valor


class CuotaPagadas(ModeloBase):
    pago = models.ForeignKey(Pago, verbose_name=u'Pago', on_delete=models.CASCADE)
    cuotapago = models.ForeignKey(CuotaPago, verbose_name=u'Cuota Pago', on_delete=models.CASCADE)
    valor = models.FloatField(default=0, verbose_name=u'Valor mensual')
    cancelado = models.BooleanField(default=False, verbose_name=u'Cancelado')

    def __str__(self):
        return u'%s' % self.valor


class TipoPreguntasPrograma(ModeloBase):
    descripcion = models.TextField(default='', verbose_name=u'Descripcion')

    def __str__(self):
        return u'%s' % self.descripcion

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(TipoPreguntasPrograma, self).save(*args, **kwargs)


class PreguntasPrograma(ModeloBase):
    tipopregunta = models.ForeignKey(TipoPreguntasPrograma, null=True, blank=True, verbose_name=u'Tipo Pregunta', on_delete=models.CASCADE)
    descripcion = models.TextField(default='', verbose_name=u'Descripcion')

    def __str__(self):
        return u'%s' % self.descripcion

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(PreguntasPrograma, self).save(*args, **kwargs)


class PreguntaMaestria(ModeloBase):
    cohortes = models.ForeignKey(CohorteMaestria, blank=True, null=True,verbose_name=u'Cohore Maestría', on_delete=models.CASCADE)
    pregunta = models.ForeignKey(PreguntasPrograma, blank=True, null=True,verbose_name=u'Pregunta', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s - %s' % (self.cohortes, self.pregunta)

    def mi_respuesta(self, idinscripentreviata):
        if self.respuestaentrevitamsc_set.filter(status=True, integrante_id=idinscripentreviata).exists():
            return self.respuestaentrevitamsc_set.filter(status=True, integrante_id=idinscripentreviata)[0].respuesta
        return None

    class Meta:
        verbose_name = u"PreguntaMaestria"
        verbose_name_plural = u"PreguntasMaestrias"
        ordering = ['cohortes']

    def save(self, *args, **kwargs):
        super(PreguntaMaestria, self).save(*args, **kwargs)


class TipoPersonaRequisito(ModeloBase):
    nombre = models.CharField(default='', max_length=250, verbose_name=u"Nombre del tipo de persona que sube el requisito")

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"TipoPersonaRequisito"
        verbose_name_plural = u"TipoPersonaRequisitos"
        ordering = ['nombre']
        unique_together = ('nombre',)

class Requisito(ModeloBase):
    nombre = models.CharField(default='', max_length=250, verbose_name=u"Nombre del archivo")
    observacion = models.CharField(default='', max_length=500, verbose_name=u"Observación")
    activo = models.BooleanField(default=True, verbose_name=u"Activo")
    archivo = models.FileField(upload_to='formatorequisito/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo')
    tipoarchivo = models.IntegerField(choices=TIPO_ARCHIVO, default=1, verbose_name=u'Formato pdf o img')
    tipopersona = models.ForeignKey(TipoPersonaRequisito, null=True, blank=True, verbose_name=u'Tipo de Persona', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.nombre

    def esta_uso(self):
        estado = False
        if self.claserequisito_set.all().exists():
            for clase in self.claserequisito_set.all():
                if clase.clasificacion.id in [1,3]:
                    estado = True if clase.requisito.requisitosmaestria_set.exists() else False
                    if estado == True:
                        return estado
                if clase.clasificacion.id == 2:
                    estado = True if clase.requisito.detallerequisitoingreso_set.exists() else False
                    if estado == True:
                        return estado
        return estado

    def download_link(self):
        return self.archivo.url

    def mi_requisito(self, idcohorte):
        if self.requisitosmaestria_set.filter(status=True).exists():
            if self.requisitosmaestria_set.filter(cohorte_id=idcohorte).exists():
                return self.requisitosmaestria_set.filter(cohorte_id=idcohorte)[0]
            else:
                return False
        else:
            return False

    class Meta:
        verbose_name = u"Requisito"
        verbose_name_plural = u"Requisitos"
        ordering = ['nombre']
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.observacion = self.observacion.upper()
        super(Requisito, self).save(*args, **kwargs)

class TipoClasificacionRequisito(ModeloBase):
    descripcion = models.TextField(default='', blank=True, null=True, verbose_name=u"Tipo de clasificación de requisito")

    def __str__(self):
        return u'%s' %self.descripcion

    def esta_uso(self):
        return True if self.claserequisito_set.all().exists() else False

    class Meta:
        verbose_name = u"Tipo Clasificación Requisito"
        verbose_name_plural = u"Tipo de clasificaciones de requisito"
        ordering = ['id']

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(TipoClasificacionRequisito, self).save(*args, **kwargs)

class ClaseRequisito(ModeloBase):
    requisito = models.ForeignKey(Requisito, null=True, blank=True, verbose_name=u'Requisito', on_delete=models.CASCADE)
    clasificacion = models.ForeignKey(TipoClasificacionRequisito, null=True, blank=True, verbose_name=u'Clasificación', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s - %s' % (self.requisito.nombre, self.clasificacion)

    def esta_uso(self):
        if self.clasificacion.id == 1:
            return True if self.requisito.requisitosmaestria_set.exists() else False
        if self.clasificacion.id == 2:
            return True if self.requisito.detallerequisitoingreso_set.exists() else False

    class Meta:
        verbose_name = u"Clase de Requisito"
        verbose_name_plural = u"Clase de Requisitos"
        ordering = ['requisito']

class RequisitosMaestria(ModeloBase):
    requisito = models.ForeignKey(Requisito, null=True, blank=True, verbose_name=u'Cohorte Maestria', on_delete=models.CASCADE)
    cohorte = models.ForeignKey(CohorteMaestria, null=True, blank=True, verbose_name=u'Cohorte Maestria', on_delete=models.CASCADE)
    maestria = models.ForeignKey(MaestriasAdmision, null=True, blank=True, verbose_name=u'Maestria', on_delete=models.CASCADE)
    obligatorio = models.BooleanField(default=True, verbose_name=u"Obligatorio")

    def __str__(self):
        return u'%s' % self.requisito

    def esta_uso(self):
        return True if self.evidenciarequisitosaspirante_set.all().exists() else False

    def detalle_requisitosmaestria(self, aspirante):
        if self.evidenciarequisitosaspirante_set.filter(inscripcioncohorte=aspirante,status=True).exists():
            return self.evidenciarequisitosaspirante_set.filter(inscripcioncohorte__inscripcionaspirante=aspirante,status=True)[0]
        else:
            return None

    def detalle_requisitosmaestriacohorte(self, inscripcioncohorte):
        if self.evidenciarequisitosaspirante_set.values("id").filter(inscripcioncohorte=inscripcioncohorte,status=True).exists():
            return self.evidenciarequisitosaspirante_set.filter(inscripcioncohorte=inscripcioncohorte,status=True).first()
        else:
            return None

    class Meta:
        verbose_name = u"MaestriaPeriodoAdmision"
        verbose_name_plural = u"MaestriaPeriodoAdmisiones"
        ordering = ['cohorte']

    def save(self, *args, **kwargs):
        super(RequisitosMaestria, self).save(*args, **kwargs)


class RequisitosGrupoCohorte(ModeloBase):
    requisito = models.ForeignKey(Requisito, null=True, blank=True, verbose_name=u'Requisito Maestria', on_delete=models.CASCADE)
    grupo = models.ForeignKey(GrupoRequisitoCohorte, null=True, blank=True, verbose_name=u'Grupo Cohorte Maestria', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.requisito

class EvidenciaRequisitosAspirante(ModeloBase):
    inscripcioncohorte = models.ForeignKey(InscripcionCohorte, blank=True, null=True, verbose_name=u'Inscripcion Cohorte', on_delete=models.CASCADE)
    requisitos = models.ForeignKey(RequisitosMaestria, blank=True, null=True, verbose_name=u'Requisitos', on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='evidenciaaspirantes/%Y/%m/%d', blank=True, null=True,verbose_name=u'Archivo')


    def __str__(self):
        return u'%s' % self.requisitos

    def ultima_evidencia(self):
        if self.detalleevidenciarequisitosaspirante_set.filter(status=True).exists():
            return self.detalleevidenciarequisitosaspirante_set.filter(status=True).order_by('-id')[0]
        return None

    def ultima_evidencia_aspirante(self):
        if self.detalleevidenciarequisitosaspirante_set.filter(status=True, estadorevision=1).exists():
            return self.detalleevidenciarequisitosaspirante_set.filter(status=True, estadorevision=1).order_by('-id')[0]
        return None

    # def ultima_evidencia_aprobador(self):
    #     if self.detalleevidenciarequisitosaspirante_set.filter(Q(status=True), (Q(estadorevision=2)| Q(estadorevision=3))).exists():
    #         return self.detalleevidenciarequisitosaspirante_set.filter(Q(status=True), (Q(estadorevision=2)| Q(estadorevision=3))).order_by('-id')[0]
    #     return None

    def download_evidencia(self):
        return self.archivo.url

    def save(self, *args, **kwargs):
        # self.observacion = self.observacion.upper()
        super(EvidenciaRequisitosAspirante, self).save(*args, **kwargs)


class DetalleEvidenciaRequisitosAspirante(ModeloBase):
    evidencia = models.ForeignKey(EvidenciaRequisitosAspirante, blank=True, null=True, verbose_name=u'Evidencia', on_delete=models.CASCADE)
    estadorevision = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u'Estado Revisión')
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Quien aprueba', on_delete=models.CASCADE)
    fecha = models.DateTimeField(blank=True, null=True, verbose_name=u"Fecha de subida evidencia")
    observacion = models.TextField(blank=True, null=True, verbose_name=u"Observación postulante")
    fecha_aprobacion = models.DateTimeField(blank=True, null=True, verbose_name=u"Fecha de aprobacion o rechazo")
    observacion_aprobacion = models.TextField(blank=True, null=True, verbose_name=u"Observación aprobador")
    estado_aprobacion = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u'Estado Aprobacion')

    def __str__(self):
        return u'%s' % self.observacion

    def esta_aprobado(self):
        return True if self.estado_aprobacion == 2 else False

    def estado_rechazado(self):
        return True if self.estado_aprobacion == 3 else False

    def esta_rechazado(self):
        return True if self.estadorevision == 3 else False

    def esta_pendiente(self):
        return True if self.estadorevision == 1 else False

    def save(self, *args, **kwargs):
        self.observacion = self.observacion.upper()
        if self.observacion_aprobacion:
            self.observacion_aprobacion = self.observacion_aprobacion.upper()
        super(DetalleEvidenciaRequisitosAspirante, self).save(*args, **kwargs)


class EvidenciaPagoExamen(ModeloBase):
    inscripcioncohorte = models.ForeignKey(InscripcionCohorte, blank=True, null=True, verbose_name=u'Inscripcion Cohorte', on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='evidenciapagoexamen/%Y/%m/%d', blank=True, null=True,verbose_name=u'Archivo')
    estadorevision = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u'Estado Revisión')

    def __str__(self):
        return u'%s' % self.inscripcioncohorte

    def download_pagoexamen(self):
        return self.archivo.url

    def save(self, *args, **kwargs):
        super(EvidenciaPagoExamen, self).save(*args, **kwargs)


class GrupoExamenMsc(ModeloBase):
    profesor = models.ForeignKey('sga.Profesor', blank=True, null=True, verbose_name=u'Profesor', on_delete=models.CASCADE)
    cohorte = models.ForeignKey(CohorteMaestria, blank=True, null=True, verbose_name=u'Cohorte de maestria', on_delete=models.CASCADE)
    lugar = models.CharField(default='', max_length=100, verbose_name=u'Lugar de examen')
    fecha = models.DateField(blank=True, null=True, verbose_name=u'fecha bde exsamen')
    hora = models.TimeField(blank=True, null=True, verbose_name=u'Hora de examen')
    observacion = models.TextField(default='', verbose_name=u'Observación')
    urlzoom = models.TextField(default='', verbose_name=u'URL Zoom')
    visible = models.BooleanField(default=True, verbose_name=u'Visible')
    estado_emailentrevista = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u'Estado Email evidencia')
    fecha_emailentrevista = models.DateTimeField(blank=True, null=True)
    persona_emailentrevista = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Quien aprueba o rechaza evidencias', on_delete=models.CASCADE)
    idgrupomoodle = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'id de grupo de moodle')
    codigonumber = models.CharField(default='', max_length=100, verbose_name=u'Codigo number sagest')

    def __str__(self):
        return u'%s - %s' % (self.lugar, self.cohorte.descripcion)

    class Meta:
        ordering = ['profesor', ]


    def mis_integrantes(self):
        return self.integrantegrupoexamenmsc_set.filter(inscripcion__status=True,status=True).order_by('inscripcion__inscripcionaspirante__persona__apellido1','inscripcion__inscripcionaspirante__persona__apellido2')

    def fecha_pasada(self):
        if self.fecha > datetime.now().date():
            return True
        else:
            return False

    def total_inscritos(self):
        return self.mis_integrantes().values('id').count()

    def puede_eliminar_grupo(self):
        return True if not self.integrantegrupoexamenmsc_set.values("id").filter(status=True).exists() else False

    def crear_actualizar_estudiantes_cursogrupoex(self, moodle):
        #################################################################################################################
        # AGREGAR ESTUDIANTE
        #################################################################################################################
        from sga.funciones import log
        try:
            # if self.idcursomoodle:
            contador = 0
            cursoid = 3
            # cursoid = self.idcursomoodle
            for estudiante in self.integrantegrupoexamenmsc_set.filter(status=True):
                contador += 1
                persona = estudiante.inscripcion.inscripcionaspirante.persona
                idnumber_user = persona.identificacion()
                bestudiante = moodle.BuscarUsuario('idnumber', 1, idnumber_user)
                estudianteid = 0
                # if not bestudiante:
                #     bestudiante = moodle.BuscarUsuario('idnumber', idnumber_user)
                #
                # if bestudiante['users']:
                #     if 'id' in bestudiante['users'][0]:
                #         estudianteid = bestudiante['users'][0]['id']
                # else:
                #     notuser = moodle.BuscarUsuario('username', persona.usuario.username)
                #     if not notuser:
                #         notuser = moodle.BuscarUsuario('username', persona.usuario.username)
                #     if notuser['users']:
                #         elminar = moodle.EliminarUsuario(notuser['users'][0]['id'])

                bestudiante = moodle.CrearUsuario(u'%s' % persona.usuario.username,
                                                  u'%s' % persona.identificacion(),
                                                  u'%s %s' % (persona.apellido1, persona.apellido2),
                                                  u'%s' % persona.nombres,
                                                  u'%s' % persona.email,
                                                  idnumber_user,
                                                  u'%s' % persona.canton.nombre if persona.canton else '',
                                                  u'%s' % persona.pais.nombre if persona.pais else '')
                # estudianteid = bestudiante[0]['id']
                if estudianteid > 0:
                    rolest = moodle.EnrolarCurso(5, 1, estudianteid, cursoid)
                    if persona.idusermoodle != estudianteid:
                        persona.idusermoodle = estudianteid
                        persona.save()
                print('************Estudiante: %s *** %s' % (contador, persona))
            # self.quitar_estudiantes_curso(moodle)
        except Exception as ex:
            log(u'Moodle Error al crear Estudiante: %s' % persona, None, "add", User.objects.get(pk=1))
            print('Error al crear estudiante %s' % ex)

    def crear_actualizar_docente_grupo_posgrado(self, moodle, tipourl):
        #################################################################################################################
        # AGREGAR DOCENTE
        #################################################################################################################
        from sga.funciones import log
        from sga.models import Profesor
        try:
            if self.idgrupomoodle:
                cursoid = self.idgrupomoodle
                if self.quitar_docente_grupo(moodle, tipourl):
                    # docentes = self.mis_profesores_autores()
                    docentes = Profesor.objects.filter(pk=self.profesor.id)
                    for curpro in docentes:
                        profesor = curpro
                        if profesor and profesor.persona.usuario and not 'POR DEFINIR' in profesor.persona.nombres:
                            persona = profesor.persona
                            username = persona.usuario.username
                            bprofesor = moodle.BuscarUsuario(self.cohorte, tipourl, 'username', username)
                            profesorid = 0
                            if not bprofesor:
                                bprofesor = moodle.BuscarUsuario(self.cohorte, tipourl, 'username', username)

                            if bprofesor['users']:
                                if 'id' in bprofesor['users'][0]:
                                    profesorid = bprofesor['users'][0]['id']
                            else:
                                idnumber_user = persona.identificacion()
                                notuser = moodle.BuscarUsuario(self.cohorte, tipourl, 'idnumber', idnumber_user)
                                if not notuser:
                                    notuser = moodle.BuscarUsuario(self.cohorte, tipourl, 'idnumber', idnumber_user)
                                if notuser['users']:
                                    elminar = moodle.EliminarUsuario(self.cohorte, tipourl, notuser['users'][0]['id'])

                                bprofesor = moodle.CrearUsuario(self.cohorte, tipourl, u'%s' % persona.usuario.username,
                                                                u'%s' % persona.identificacion(),
                                                                u'%s' % persona.nombres,
                                                                u'%s %s' % (persona.apellido1, persona.apellido2),
                                                                u'%s' % persona.emailinst,
                                                                idnumber_user,
                                                                u'%s' % persona.canton.nombre if persona.canton else '',
                                                                u'%s' % persona.pais.nombre if persona.pais else '')
                                profesorid = bprofesor[0]['id']

                            if profesorid > 0:
                                # PROFESOR-ABR-SEP2018
                                # rolest = moodle.EnrolarCurso(self.nivel.periodo, 3, profesorid, cursoid)
                                # PROFESOR-OCT-FEB2019
                                rolest = moodle.EnrolarCurso(self.cohorte, tipourl,9, profesorid, cursoid)
                                if persona.idusermoodleposgrado != profesorid:
                                    persona.idusermoodleposgrado = profesorid
                                    persona.save()
                            print('**********PROFESOR: %s' % profesor)
        except Exception as ex:
            # log(u'Moodle Error al crear docente: %s' % persona, None, "add", User.objects.get(pk=1))
            print('Error al crear docente %s' % ex)

    def quitar_docente_grupo(self, moodle , tipourl):
        from django.db import connections
        cursor = connections['moodle_pos'].cursor()
        #################################################################################################################
        # QUITAR DOCENTE
        #################################################################################################################
        if self.idgrupomoodle:
            cursoid = self.idgrupomoodle
            idprofesores = ""
            for x in self.values_list('profesor__persona__idusermoodle', flat=False).filter(status=True).order_by('id'):
                idprofesores += "%s," % x[0]
            idprofesores = self.profesor_id
            query = """SELECT DISTINCT enrol.userid, asi.roleid from mooc_user_enrolments enrol 
                        inner join mooc_role_assignments asi on asi.userid=enrol.userid and asi.roleid in(%s) 
                        where enrol.enrolid in(select en.id from mooc_enrol en where en.courseid=%s) 
                        AND enrol.userid not in(%s0) """ % (9, cursoid, idprofesores)
            cursor.execute(query)
            row = cursor.fetchall()
            if row:
                for deluser in row:
                    unrolest = moodle.UnEnrolarCurso(self.cohorte, tipourl, deluser[1], deluser[0], cursoid)
                    print('************ Eliminar Profesor: *** %s' % deluser[0])
        return True

    def crear_actualizar_estudiantes_grupo_posgrado(self, moodle, tipourl, codigoinscritogrupoexamen):
        #################################################################################################################
        # AGREGAR ESTUDIANTE
        #################################################################################################################
        from sga.funciones import log
        if self.idgrupomoodle:
            contador = 0
            cursoid = self.idgrupomoodle
            for estudiante in self.integrantegrupoexamenmsc_set.filter(pk=codigoinscritogrupoexamen,status=True):
                try:
                    contador += 1
                    bandera=0
                    persona = estudiante.inscripcion.inscripcionaspirante.persona
                    username = persona.usuario.username
                    bestudiante = moodle.BuscarUsuario(self.cohorte, tipourl, 'username', username)
                    estudianteid = 0
                    if not bestudiante:
                        bestudiante = moodle.BuscarUsuario(self.cohorte, tipourl, 'username', username)

                    if bestudiante['users']:
                        if 'id' in bestudiante['users'][0]:
                            estudianteid = bestudiante['users'][0]['id']
                    else:
                        idnumber_user = persona.identificacion()
                        notuser = moodle.BuscarUsuario(self.cohorte, tipourl, 'idnumber', idnumber_user)
                        if not notuser:
                            notuser = moodle.BuscarUsuario(self.cohorte, tipourl, 'idnumber', idnumber_user)
                        if notuser['users']:
                            elminar = moodle.EliminarUsuario(self.cohorte, tipourl, notuser['users'][0]['id'])

                        bestudiante = moodle.CrearUsuario(self.cohorte, tipourl, u'%s' % persona.usuario.username,
                                                          u'%s' % persona.identificacion(),
                                                          u'%s' % persona.nombres,
                                                          u'%s %s' % (persona.apellido1, persona.apellido2),
                                                          # u'%s' % persona.email,
                                                          u'%s' % persona.emailinst,
                                                          idnumber_user,
                                                          u'%s' % persona.canton.nombre if persona.canton else '',
                                                          u'%s' % persona.pais.nombre if persona.pais else '')
                        estudianteid = bestudiante[0]['id']
                    if estudianteid > 0:
                        # rolest = moodle.EnrolarCurso(5, estudianteid, cursoid)
                        # Estudiante-oct-feb2019
                        # rolest = moodle.EnrolarCurso(5, estudianteid, cursoid)
                        rolest = moodle.EnrolarCurso(self.cohorte,tipourl, 10, estudianteid, cursoid)
                        if persona.idusermoodleposgrado != estudianteid:
                            persona.idusermoodleposgrado = estudianteid
                            persona.save()
                    print('************Estudiante: %s *** %s' % (contador, persona))
                except Exception as ex:
                    log(u'Moodle Error al crear Estudiante: %s' % persona, None, "add", User.objects.get(pk=1))
                    print('Error al crear estudiante %s' % ex)

    def crear_actualizar_categoria_notas_grupo_posgrado(self):
        from django.db import connections
        from sga.models import ModeloEvaluativo
        cursor = connections['moodle_pos'].cursor()
        #################################################################################################################
        # AGREGAR SISTEMA DE CALIFICACION
        #################################################################################################################
        if self.idgrupomoodle:
            cursoid = self.idgrupomoodle
            modeloevaluativo = ModeloEvaluativo.objects.get(pk=3)
            modelonotas = modeloevaluativo.detallemodeloevaluativo_set.filter(migrarmoodle=True)
            if modelonotas:
                query = u"SELECT id FROM mooc_grade_categories WHERE parent is null and depth=1 and courseid= %s" % cursoid
                cursor.execute(query)
                row = cursor.fetchall()
                padrenota = 0
                fecha = int(time.mktime(datetime.now().date().timetuple()))
                if not row:
                    query = u"INSERT INTO mooc_grade_categories(courseid, parent, depth, path, fullname, aggregation, keephigh, droplow, aggregateonlygraded, hidden, timecreated, timemodified) VALUES (%s, null, 1, E'', E'?', 13, 0, 0, 0, 0, %s, %s)" % (cursoid, fecha, fecha)
                    cursor.execute(query)
                    query = u"SELECT id FROM mooc_grade_categories WHERE parent is null and depth=1 and courseid= %s" % cursoid
                    cursor.execute(query)
                    row = cursor.fetchall()
                    query = u"UPDATE mooc_grade_categories SET path='/%s/' WHERE id= %s" % (row[0][0], row[0][0])
                    cursor.execute(query)
                    padrenota = row[0][0]
                else:
                    padrenota = row[0][0]
                if padrenota > 0:
                    ordennota = 1
                    query = u"SELECT id FROM mooc_grade_items WHERE courseid=%s and itemtype='course' and iteminstance=%s" % (cursoid, padrenota)
                    cursor.execute(query)
                    row = cursor.fetchall()
                    if not row:
                        query = u"INSERT INTO mooc_grade_items (courseid, categoryid, itemname, itemtype, itemmodule, iteminstance, itemnumber, iteminfo, idnumber, calculation, gradetype, grademax, grademin, scaleid, outcomeid, gradepass, multfactor, plusfactor, aggregationcoef, aggregationcoef2, sortorder, display, decimals, hidden, locked, locktime, needsupdate, weightoverride, timecreated, timemodified) VALUES (%s, null, null, E'course', null, %s, null, null, null, null, 1, 100, 0, null, null, 0, 1, 0, 0, 0, %s, 0, 2, 0, 0, 0, 0, 0, %s, %s)" % (cursoid, padrenota, ordennota, fecha, fecha)
                        cursor.execute(query)

                    for modelo in modelonotas:
                        query = u"SELECT id FROM mooc_grade_categories WHERE parent=%s and depth=2 and courseid= %s and fullname='%s'" % (padrenota, cursoid, modelo.nombre)
                        cursor.execute(query)
                        row = cursor.fetchall()
                        padremodelo = 0
                        if not row:
                            query = u"INSERT INTO mooc_grade_categories(courseid, parent, depth, path, fullname, aggregation, keephigh, droplow, aggregateonlygraded, hidden, timecreated, timemodified) VALUES (%s, %s, 2, E'', E'%s', 0, 0, 0, 0, 0, %s, %s)" % (cursoid, padrenota, modelo.nombre, fecha, fecha)
                            cursor.execute(query)
                            query = u"SELECT id FROM mooc_grade_categories WHERE parent=%s and depth=2 and courseid= %s and fullname='%s'" % (padrenota, cursoid, modelo.nombre)
                            cursor.execute(query)
                            row = cursor.fetchall()
                            padremodelo = row[0][0]
                            query = u"UPDATE mooc_grade_categories SET path='/%s/%s/' WHERE id= %s" % (padrenota, padremodelo, padremodelo)
                            cursor.execute(query)
                        else:
                            padremodelo = row[0][0]
                        if padremodelo > 0:
                            ordennota += 1
                            query = u"SELECT id FROM mooc_grade_items WHERE courseid=%s and itemtype='category' and iteminstance=%s" % (cursoid, padremodelo)
                            cursor.execute(query)
                            row = cursor.fetchall()
                            if not row:
                                query = u"INSERT INTO mooc_grade_items (courseid, categoryid, itemname, itemtype, itemmodule, iteminstance, itemnumber, iteminfo, idnumber, calculation, gradetype, grademax, grademin, scaleid, outcomeid, gradepass, multfactor, plusfactor, aggregationcoef, aggregationcoef2, sortorder, display, decimals, hidden, locked, locktime, needsupdate, weightoverride, timecreated, timemodified) " \
                                        u"VALUES (%s, null, E'', E'category', null, %s, null, E'', E'', null, 1, %s, 0, null, null, 0, 1, 0, 0, %s, %s, 0, %s, 0, 0, 0, 0, 0, %s, %s)" \
                                        % (cursoid, padremodelo, modelo.notamaxima, null_to_decimal(modelo.notamaxima / 100, 2), ordennota, modelo.decimales, fecha, fecha)
                                cursor.execute(query)

    def crear_grupo_moodle(self, codigoinscritogrupoexamen, contadoringreso):
        from django.db import connections
        from moodle import moodle
        from sga.models import Coordinacion, Carrera, NivelMalla
        cursor = connections['moodle_pos'].cursor()
        #################################################################################################################
        #################################################################################################################
        # servidor
        AGREGAR_MODELO_NOTAS = True
        AGREGAR_ESTUDIANTE = True
        AGREGAR_DOCENTE = True

        parent_grupoid = 0
        tipourl = 1
        periodo = self.cohorte
        bgrupo = moodle.BuscarCategoriasid(periodo, tipourl, 70)
        # bgrupo = moodle.BuscarCategoriasid(periodo, tipourl,periodo.categoria)
        if bgrupo:
            if 'id' in bgrupo[0]:
                parent_grupoid = bgrupo[0]['id']
        contador = 0

        if parent_grupoid >= 0:
            if contadoringreso == 0:
                """"
                CREANDO EL PERIODO DE COHORTE EL ID SE CONFIGURA EN VARIABLES GLABALES
                """
                bperiodo = moodle.BuscarCategorias(periodo, tipourl, periodo.idnumber())
                parent_periodoid = 0
                if bperiodo:
                    if 'id' in bperiodo[0]:
                        parent_periodoid = bperiodo[0]['id']
                else:
                    bperiodo = moodle.CrearCategorias(periodo, tipourl, periodo.__str__(), periodo.idnumber(), periodo.__str__(), parent=parent_grupoid)
                    parent_periodoid = bperiodo[0]['id']
                # print('Periodo lectivo: %s' % periodo)
                if parent_periodoid > 0:
                    """"
                    CREANDO LAS COORDINACIONES
                    """
                    cordinaciones = Coordinacion.objects.filter(id=7).distinct()
                    for coordinacion in cordinaciones:
                        idnumber_coordinacion = u'%s-COR%s' % (periodo.idnumber(), coordinacion.id)
                        bcoordinacion = moodle.BuscarCategorias(periodo, tipourl, idnumber_coordinacion)
                        parent_coordinacionid = 0
                        if bcoordinacion:
                            if 'id' in bcoordinacion[0]:
                                parent_coordinacionid = bcoordinacion[0]['id']
                        else:
                            bcoordinacion = moodle.CrearCategorias(periodo, tipourl, coordinacion, idnumber_coordinacion,coordinacion.nombre, parent=parent_periodoid)
                            parent_coordinacionid = bcoordinacion[0]['id']
                        # print('**Facultad: %s' % coordinacion)
                        if parent_coordinacionid > 0:
                            """"
                            CREANDO LAS CARRERAS
                            """
                            idcarrera = self.cohorte.maestriaadmision.carrera.id
                            carreras = Carrera.objects.filter(pk=idcarrera).distinct()
                            for carrera in carreras:
                                idnumber_carrera = u'%s-COR%s-CARR%s' % (periodo.idnumber(), coordinacion.id, carrera.id)
                                bcarrera = moodle.BuscarCategorias(periodo, tipourl, idnumber_carrera)
                                parent_carreraid = 0
                                if bcarrera:
                                    if 'id' in bcarrera[0]:
                                        parent_carreraid = bcarrera[0]['id']
                                else:
                                    bcarrera = moodle.CrearCategorias(periodo, tipourl, carrera, idnumber_carrera,carrera.nombre, parent=parent_coordinacionid)
                                    parent_carreraid = bcarrera[0]['id']
                                # print('****Carrera: %s' % carrera)
                                if parent_carreraid > 0:
                                    """"
                                    CREANDO LOS NIVELES DE MALLA
                                    """
                                    niveles = NivelMalla.objects.filter(pk=1).distinct()
                                    for semestre in niveles:
                                        idnumber_semestre = u'%s-COR%s-CARR%s-NIVEL%s' % (
                                            periodo.idnumber(), coordinacion.id, carrera.id, semestre.id)
                                        bsemestre = moodle.BuscarCategorias(periodo, tipourl, idnumber_semestre)
                                        categoryid = 0
                                        if bsemestre:
                                            if 'id' in bsemestre[0]:
                                                categoryid = bsemestre[0]['id']
                                        else:
                                            bsemestre = moodle.CrearCategorias(periodo, tipourl, semestre,idnumber_semestre, semestre.nombre,parent=parent_carreraid)
                                            categoryid = bsemestre[0]['id']
                                        # print('******Semestre: %s' % semestre)
                                        if categoryid > 0:
                                            """"
                                            CREANDO LOS CURSOS
                                            """
                                            cursos = GrupoExamenMsc.objects.filter(id=self.id)
                                            for curso in cursos:
                                                if curso.codigonumber:
                                                    idnumber_curso = curso.codigonumber
                                                else:
                                                    idnumber_curso = u'%s-COR%s-CARR%s-NIVEL%s-CURS%s' % (periodo.idnumber(), coordinacion.id, carrera.id, semestre.id, curso.id)
                                                bcurso = moodle.BuscarCursos(periodo, tipourl, 'idnumber', idnumber_curso)
                                                if not bcurso:
                                                    bcurso = moodle.BuscarCursos(periodo, tipourl, 'idnumber',idnumber_curso)
                                                numsections = 1
                                                # planificacionclasesilabo = curso.planificacionclasesilabo_materia_set.filter(status=True)
                                                # if planificacionclasesilabo:
                                                #     numsections = planificacionclasesilabo[0].tipoplanificacion.detalle_planificacion().count()
                                                # objetivocur = ObjetivoProgramaAnaliticoAsignatura.objects.filter(programaanaliticoasignatura__asignaturamalla=curso.asignaturamalla,programaanaliticoasignatura__activo=True,programaanaliticoasignatura__status=True)
                                                summary = u''
                                                # if objetivocur:
                                                #     summary = objetivocur[0].descripcion
                                                startdate = int(time.mktime(curso.fecha.timetuple()))
                                                enddate = int(time.mktime(curso.fecha.timetuple()))
                                                cursoid = 0
                                                if bcurso['courses']:
                                                    if 'id' in bcurso['courses'][0]:
                                                        cursoid = bcurso['courses'][0]['id']
                                                else:
                                                    bcurso = moodle.CrearCursos(periodo, tipourl,u'%s' % curso.__str__(),u'%s,[%s] - %s[%s]' % (str(curso.fecha),curso.id, curso.id,curso.id), categoryid, idnumber_curso,summary, startdate, enddate, numsections)
                                                    cursoid = bcurso[0]['id']
                                                # print('********Curso: %s' % curso)
                                                if cursoid > 0:
                                                    if curso.idgrupomoodle != cursoid:
                                                        curso.codigonumber = idnumber_curso
                                                        curso.idgrupomoodle = cursoid
                                                        curso.save()

                                                    if AGREGAR_MODELO_NOTAS:
                                                        curso.crear_actualizar_categoria_notas_grupo_posgrado()

                                                    if AGREGAR_DOCENTE:
                                                        curso.crear_actualizar_docente_grupo_posgrado(moodle, 1)

                                                    if AGREGAR_ESTUDIANTE:
                                                        curso.crear_actualizar_estudiantes_grupo_posgrado(moodle, 1, codigoinscritogrupoexamen)
            else:
                curso = GrupoExamenMsc.objects.get(id=self.id)
                if AGREGAR_ESTUDIANTE:
                    curso.crear_actualizar_estudiantes_grupo_posgrado(moodle, 1, codigoinscritogrupoexamen)


    def categorias_moodle_curso(self):
        from django.db import connections
        cursor = connections['moodle_pos'].cursor()
        sql = """select DISTINCT upper(gc.fullname),it.sortorder  from mooc_grade_grades nota 
                 inner join mooc_grade_items it on nota.itemid=it.id and courseid=%s and itemtype='category' 
                 inner join mooc_grade_categories gc on gc.courseid=it.courseid and gc.id=it.iteminstance and gc.depth=2 
                 where not upper(gc.fullname)='RE'
                 order by it.sortorder ;
                """ % str(self.idgrupomoodle)
        cursor.execute(sql)
        results = cursor.fetchall()
        return results

    def categorias_moodle_curso_count(self):
        from django.db import connections
        cursor = connections['moodle_pos'].cursor()
        sql = "select count(contar.fullname) from(select DISTINCT gc.fullname,it.sortorder  from mooc_grade_grades nota " \
              " inner join mooc_grade_items it on nota.itemid=it.id and courseid=" + str(self.idgrupomoodle) + " and itemtype='category' " \
                                                                                                               " inner join mooc_grade_categories gc on gc.courseid=it.courseid and gc.id=it.iteminstance and gc.depth=2 order by it.sortorder) as contar ;"
        cursor.execute(sql)
        results = cursor.fetchall()
        return results

    def notas_de_moodle(self, persona):
        from django.db import connections
        cursor = connections['moodle_pos'].cursor()
        sql = """
                        SELECT ROUND(nota.finalgrade,2), UPPER(gc.fullname)
                                FROM mooc_grade_grades nota
                        INNER JOIN mooc_grade_items it ON nota.itemid=it.id AND courseid=%s AND itemtype='category'
                        INNER JOIN mooc_grade_categories gc ON gc.courseid=it.courseid AND gc.id=it.iteminstance AND gc.depth=2
                        INNER JOIN mooc_user us ON nota.userid=us.id
                        WHERE us.id ='%s' and not UPPER(gc.fullname)='RE'
                        ORDER BY it.sortorder
                        """ % (str(self.idgrupomoodle), persona.idusermoodleposgrado)

        cursor.execute(sql)
        results = cursor.fetchall()
        return results

    def save(self, *args, **kwargs):
        self.lugar = self.lugar.upper()
        self.observacion = self.observacion.upper()
        super(GrupoExamenMsc, self).save(*args, **kwargs)


class IntegranteGrupoExamenMsc(ModeloBase):
    inscripcion = models.ForeignKey(InscripcionCohorte, blank=True, null=True, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    grupoexamen = models.ForeignKey(GrupoExamenMsc, blank=True, null=True, verbose_name=u'Grupo de examen', on_delete=models.CASCADE)
    notaexa = models.FloatField(blank=True, null=True, verbose_name=u'Nota examen')
    notatest = models.FloatField(blank=True, null=True, verbose_name=u'Nota Test')
    notafinal = models.FloatField(blank=True, null=True, verbose_name=u'Nota Final')
    estado = models.IntegerField(choices=ESTADO_EXAMEN_MSC, default=1, verbose_name=u'Estado del examen')
    observacion = models.TextField(default='', verbose_name=u'Observación')
    encursomoodle = models.BooleanField(default=False, verbose_name=u"Esta en curso moodle")

    def __str__(self):
        return u'%s' % self.inscripcion

    class Meta:
        ordering = ['inscripcion', ]

    def campo(self, campo):
        # if self.evaluacion_generica().filter(detallemodeloevaluativo__nombre=campo).exists():
        #     return self.evaluacion_generica().filter(detallemodeloevaluativo__nombre=campo)[0]
        return null_to_decimal(self.notafinal,2)

    def puede_eliminar_integrante(self):
        return True if self.estado == 1 else False


    def save(self, *args, **kwargs):
        self.observacion = self.observacion.upper()
        super(IntegranteGrupoExamenMsc, self).save(*args, **kwargs)


class GrupoEntrevistaMsc(ModeloBase):
    administrativo = models.ForeignKey('sga.Administrativo', blank=True, null=True, verbose_name=u'Profesor', on_delete=models.CASCADE)
    cohortes = models.ForeignKey(CohorteMaestria, blank=True, null=True, verbose_name=u'Cohorte de maestría', on_delete=models.CASCADE)
    lugar = models.CharField(default='', max_length=100, verbose_name=u'Lugar de examen')
    fecha = models.DateField(blank=True, null=True, verbose_name=u'fecha bde exsamen')
    observacion = models.TextField(default='', verbose_name=u'Observación')
    visible = models.BooleanField(default=True, verbose_name=u'Visible')
    estado_emailentrevista = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u'Estado Email evidencia')
    fecha_emailentrevista = models.DateTimeField(blank=True, null=True)
    persona_emailentrevista = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Quien aprueba o rechaza evidencias', on_delete=models.CASCADE)
    horainicio = models.TimeField(blank=True, null=True, verbose_name=u'Hora de inicio de entrevista')
    urlzoom = models.TextField(default='', verbose_name=u'URL Zoom')

    def __str__(self):
        return u'%s - %s' % (self.observacion, self.administrativo)

    class Meta:
        ordering = ['administrativo', ]

    def mis_integrantes(self):
        return self.integrantegrupoentrevitamsc_set.filter(status=True).order_by('inscripcion__inscripcionaspirante__persona__apellido1','inscripcion__inscripcionaspirante__persona__apellido2')

    def total_inscritos(self):
        return self.mis_integrantes().values('id').count()

    def mis_participantes_entrevista(self):
        if self.integrantegrupoentrevitamsc_set.values("id").filter(status=True).exists():
            return self.integrantegrupoentrevitamsc_set.filter(status=True)
        return None

    def total_participantes_entrevista(self):
        if self.integrantegrupoentrevitamsc_set.values("id").filter(status=True).exists():
            return self.integrantegrupoentrevitamsc_set.values("id").filter(status=True).count()
        return 0

    def puede_eliminar_grupo_entrevista(self):
        return True if not self.integrantegrupoentrevitamsc_set.filter(status=True).exists() else False

    def total_admitidos_cohorte(self):
        if self.integrantegrupoentrevitamsc_set.filter(estado_emailadmitido=2, cohorteadmitidasinproceso__isnull=True, status=True).exists():
            return True
        else:
            return False

    def save(self, *args, **kwargs):
        self.observacion = self.observacion.upper()
        super(GrupoEntrevistaMsc, self).save(*args, **kwargs)


ESTADO_ENTREVISTA = (
    (1, u'PENDIENTE'),
    (2, u'APROBADO'),
    (3, u'RECHAZADO')
)

class IntegranteGrupoEntrevitaMsc(ModeloBase):
    inscripcion = models.ForeignKey(InscripcionCohorte, blank=True, null=True, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    grupoentrevista = models.ForeignKey(GrupoEntrevistaMsc, blank=True, null=True, verbose_name=u'Grupo de entrevista', on_delete=models.CASCADE)
    estadoentrevista = models.ForeignKey(EstadoEntrevista, blank=True, null=True, verbose_name=u'Estado Entrevista', on_delete=models.CASCADE)
    lugar = models.CharField(default='', max_length=300, verbose_name=u'Lugar de entrevista')
    fecha = models.DateField(blank=True, null=True, verbose_name=u'fecha de entrevista')
    horadesde = models.TimeField(blank=True, null=True, verbose_name=u'Hora desde')
    horahasta = models.TimeField(blank=True, null=True, verbose_name=u'Hora hasta')
    observacion = models.TextField(default='', verbose_name=u'Observación')
    estado = models.IntegerField(choices=ESTADO_ENTREVISTA, default=1, verbose_name=u'Estado del examen')
    notaentrevista = models.FloatField(blank=True, null=True, verbose_name=u'Nota Entrevista')
    notafinal = models.FloatField(default=0,blank=True, null=True, verbose_name=u'Nota Final')
    entrevista = models.BooleanField(default=False, verbose_name=u'Entrevistado')
    estado_emailadmitido = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u'Estado Email evidencia')
    fecha_emailadmitido = models.DateTimeField(blank=True, null=True)
    persona_emailadmitido = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Quien aprueba o rechaza evidencias', on_delete=models.CASCADE)
    cohorteadmitidasinproceso = models.ForeignKey(CohorteMaestria, blank=True, null=True, verbose_name=u'Cohorte Maestria', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.inscripcion

    class Meta:
        ordering = ['inscripcion', ]



    def tiene_entrevista(self):
        return True if self.respuestaentrevitamsc_set.filter(status=True).exists() else False

    def eliminar_aspirante_programa(self):
        from sagest.models import Rubro
        rubro1 = Rubro.objects.filter(inscripcion=self.inscripcion, status=True)
        return rubro1


    def save(self, *args, **kwargs):
        self.observacion = self.observacion.upper()
        self.lugar = self.lugar.upper()
        super(IntegranteGrupoEntrevitaMsc, self).save(*args, **kwargs)


class RespuestaEntrevitaMsc(ModeloBase):
    integrante = models.ForeignKey(IntegranteGrupoEntrevitaMsc, blank=True, null=True, verbose_name=u'Integrante', on_delete=models.CASCADE)
    preguntacohorte = models.ForeignKey(PreguntaMaestria, blank=True, null=True, verbose_name=u'Pregunta Cohorte', on_delete=models.CASCADE)
    respuesta = models.TextField(default='', verbose_name=u'Respuesta')

    def __str__(self):
        return u'%s' % self.respuesta

    def save(self, *args, **kwargs):
        self.respuesta = self.respuesta.upper()
        super(RespuestaEntrevitaMsc, self).save(*args, **kwargs)


class FormatoCarreraIpec(ModeloBase):
    carrera = models.ForeignKey('sga.Carrera', blank=True, null=True, verbose_name=u'Carrera', on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='formatocarrerapreinscripcionipec', blank=True, null=True,verbose_name=u'Archivo')
    correomaestria = models.EmailField(default='',blank=True, null=True, verbose_name=u'Correo de la maestría')
    banner = models.FileField(upload_to='banner', blank=True, null=True, verbose_name=u'Banner de la maestría')


    def __str__(self):
        return u'%s' % self.correomaestria

    def download_link(self):
        return self.archivo.url

    def download_banner(self):
        return self.banner.url


class PreInscripcion(ModeloBase):
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Persona', on_delete=models.CASCADE)
    fecha_hora = models.DateTimeField(blank=True, null=True, verbose_name=u'fecha de registro')
    carrera = models.ForeignKey('sga.Carrera', blank=True, null=True, verbose_name=u'Carrera', on_delete=models.CASCADE)
    formato = models.ForeignKey(FormatoCarreraIpec, blank=True, null=True, verbose_name=u'Formato', on_delete=models.CASCADE)
    enviocorreo = models.BooleanField(default=False, verbose_name=u'Verfica si envio correo de requisitos')
    rutapdf = models.FileField(upload_to='qrcode/certificados', blank=True, null=True,verbose_name=u'Archivo certificado de preinscripcion')
    evidencias = models.BooleanField(default=False, verbose_name=u'Verifica si envio las evidencias de la maestria')
    aceptarpreinscripcion = models.BooleanField(default=False, verbose_name=u'Verifica si se acepto la inscripcion para la maestria')


    def __str__(self):
        return u'%s' % self.persona

    def download_formato(self):
        return self.formato.download_link()

    class Meta:
        ordering = ['persona', ]


class InteresadoMaestria(ModeloBase):
    nombre = models.TextField(default='', verbose_name=u'Nombre')
    email = models.EmailField(default='', blank=True, null=True, verbose_name=u'Email Interesado')
    telefono = models.TextField(default='', verbose_name=u'Teléfono')
    profesion = models.TextField(default='', verbose_name=u'Profesión')
    fecha_hora = models.DateTimeField(blank=True, null=True, verbose_name=u'fecha de registro')
    carrera = models.ForeignKey('sga.Carrera', blank=True, null=True, verbose_name=u'Carrera', on_delete=models.CASCADE)

    def __str__(self):
        return u'%s - %s' % (self.nombre, self.correo)

    class Meta:
        ordering = ['nombre', ]


class EvidenciasMaestrias(ModeloBase):
    preinscripcion = models.ForeignKey(PreInscripcion, verbose_name=u'PreInscripcion', on_delete=models.CASCADE)
    hojavida = models.FileField(upload_to='requisitosmaestriapreinscripcionipec', blank=True, null=True,verbose_name=u'Archivo hoja de vida pre inscripcion ipec')
    copiavotacion = models.FileField(upload_to='requisitosmaestriapreinscripcionipec', blank=True, null=True,verbose_name=u'Archivo certificado votacion pre inscripcion ipec')
    copiacedula = models.FileField(upload_to='requisitosmaestriapreinscripcionipec', blank=True, null=True,verbose_name=u'Archivo cedula pre inscripcion ipec')
    senescyt  = models.FileField(upload_to='requisitosmaestriapreinscripcionipec', blank=True, null=True,verbose_name=u'Archivo titulo senescyt pre inscripcion ipec')
    lenguaextranjera = models.FileField(upload_to='requisitosmaestriapreinscripcionipec', blank=True, null=True,verbose_name=u'Archivo certificado lengua extranjera pre inscripcion ipec')
    observaciones = models.TextField(default='', blank=True, null=True, verbose_name=u'Observaciones')

    def __str__(self):
        return u'%s' % self.preinscripcion

    def download_hojavida(self):
        return self.hojavida.url

    def download_copiavotacion(self):
        return self.copiavotacion.url

    def download_copiacedula(self):
        return self.copiacedula.url

    def download_senescyt(self):
        return self.senescyt.url

    def download_lenguaextranjera(self):
        return self.senescyt.url

    class Meta:
        ordering = ['preinscripcion', ]


HISTORIAL_CHOICES = (
    (1, "PENDIENTE"),
    (2, "EL ESTUDIANTE CONTESTÓ"),
    (3, "EL ESTUDIANTE NO CONTESTÓ"),
    (4, "EL ESTUDIANTE NO ESTÁ INTERESADO"),
    (5, "EL ESTUDIANTE CONFIRMO SU PARTICIPACIÓN"),
)

class InteresadoProgramaMaestria(ModeloBase):
    nombres = models.CharField(default='', blank=True, null=True, max_length=1000, verbose_name='Nombres')
    cedula = models.CharField(default='', blank=True, null=True, max_length=1000, verbose_name='Cédula')
    telefono = models.CharField(default='', blank=True, null=True, max_length=1000, verbose_name='Teléfono')
    telefono_adicional = models.CharField(default='', blank=True, null=True, max_length=1000, verbose_name='Teléfono Adicional')
    correo = models.CharField(default='', blank=True, null=True, max_length=1000, verbose_name='Correo')
    observacion = models.CharField(default='', blank=True, null=True, max_length=1000, verbose_name='Observación')
    programa = models.ForeignKey(MaestriasAdmision, null=True, blank=True, verbose_name=u'Programa', on_delete=models.CASCADE)
    accion = models.PositiveIntegerField(choices=HISTORIAL_CHOICES, default=1, blank=True, null=True, verbose_name='Acción')

    def get_lastobser(self):
        return HistorialInteresadoProgramaMaestria.objects.filter(status=True, cab=self).order_by('pk').last()

    def get_accion(self):
        return dict(HISTORIAL_CHOICES)[self.accion]

    def __str__(self):
        return u'%s %s' % (self.programa, self.nombres)

    class Meta:
        verbose_name = u"Interesado en Programa Maestría"
        verbose_name_plural = u"Interesados en Programas Maestrías"

    def save(self, *args, **kwargs):
        self.nombres = self.nombres.upper()
        super(InteresadoProgramaMaestria, self).save(*args, **kwargs)


class HistorialInteresadoProgramaMaestria(ModeloBase):
    cab = models.ForeignKey(InteresadoProgramaMaestria, null=True, blank=True, verbose_name="Ficha", on_delete=models.CASCADE)
    accion = models.PositiveIntegerField(choices=HISTORIAL_CHOICES, verbose_name='Acción')
    detalle = models.TextField(null=True, blank=True)

    def get_accion(self):
        return dict(HISTORIAL_CHOICES)[self.accion]

    class Meta:

        verbose_name = "Historial de Interesados"
        verbose_name_plural = "Historial de Interesados"
        ordering = ('pk',)

class ConfigurarFirmaAdmisionPosgrado(ModeloBase):
    administrativo = models.ForeignKey(Administrativo, null=True, blank=True, verbose_name='Administrativo', on_delete=models.CASCADE)
    cargo = models.CharField(verbose_name='Cargo', null=True, blank=True, max_length=1000)

    def __str__(self):
        return u'%s' % (self.administrativo.persona)

    class Meta:
        verbose_name = "Configurar Firma para Admisión Posgrado"
        verbose_name_plural = "Configurar Firmas para Admisión Posgrado"
        ordering = ('administrativo',)


ESTADO_PROYECTO_VINCULACION = ((1, 'APROBADO'), (2, 'PENDIENTE'), (3, 'RECHAZADO'))
TIPO_EVIDENCIA = ((1, 'PDF'), (2, 'LINK'))

class ProyectoVinculacion(ModeloBase):
    titulo = models.TextField(verbose_name=u'Titulo', null=True, blank=True)
    descripcion = models.TextField(verbose_name=u'Descripcion', null=True, blank=True)
    estadoaprobacion = models.IntegerField(choices=ESTADO_PROYECTO_VINCULACION, blank=True, null=True, verbose_name=u"Estado", default=2)

    def __str__(self):
        return u'%s' % self.titulo

    class Meta:
        verbose_name = u"Proyecto de vinculacion"
        verbose_name_plural = u"Proyectos de vinculacion"
        ordering = ('-pk',)

    def save(self, *args, **kwargs):
        self.titulo = self.titulo.strip().upper() if self.titulo else ''
        super(ProyectoVinculacion, self).save(*args, **kwargs)

    def get_detalleaprobacion(self):
        return self.detalleaprobacionproyecto_set.filter(status=True)

    def color_estadoaprobacion(self):
        estado = 'primary'
        if self.estadoaprobacion == 1:
            estado = 'success'
        elif self.estadoaprobacion == 2:
            estado = 'secondary'
        elif self.estadoaprobacion == 3:
            estado = 'danger'
        return estado

class ParticipanteProyectoVinculacionPos(ModeloBase):
    inscripcion = models.ForeignKey('sga.Inscripcion', blank=True, null=True, verbose_name=u'Inscripcion', on_delete=models.CASCADE)
    proyectovinculacion = models.ForeignKey(ProyectoVinculacion, verbose_name=u"Proyecto de vinculacion", blank=True, null=True, on_delete=models.CASCADE)
    evidencia = models.FileField(verbose_name=u"Evidencia", upload_to='posgrado/proyectovinculacion/%Y/%m/%d', null=True, blank=True, default='')
    tipoevidencia = models.IntegerField(choices=TIPO_EVIDENCIA, blank=True, null=True, verbose_name=u"Tipo de evidencia", default=1)

    def __str__(self):
        return u'%s' % self.inscripcion.persona.nombre_completo_inverso()

    class Meta:
        verbose_name = u"Participante del proyecto de vinculacion"
        verbose_name_plural = u"Participantes del proyecto de vinculacion"
        ordering = ('-pk',)
        unique_together = ('proyectovinculacion', 'inscripcion',)

class DetalleAprobacionProyecto(ModeloBase):
    observacion = models.TextField(verbose_name=u"Observacion", blank=True, null=True)
    proyectovinculacion = models.ForeignKey(ProyectoVinculacion, verbose_name=u"Proyecto de vinculacion", blank=True, null=True, on_delete=models.CASCADE)
    estadoaprobacion = models.IntegerField(choices=ESTADO_PROYECTO_VINCULACION, blank=True, null=True, verbose_name=u"Estado", default=2)
    persona = models.ForeignKey('sga.Persona', verbose_name=u"Persona", blank=True, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return u'%s' % self.proyectovinculacion

    class Meta:
        verbose_name = u"Detalle aprobacion de proyecto"
        verbose_name_plural = u"Detalle aprobacion de proyectos"
        ordering = ('-pk',)

    def color_estadoaprobacion(self):
        estado = 'primary'
        if self.estadoaprobacion == 1:
            estado = 'success'
        elif self.estadoaprobacion == 2:
            estado = 'secondary'
        elif self.estadoaprobacion == 3:
            estado = 'danger'
        return estado

class SolicitudProrrogaIngresoTemaMatricula(ModeloBase):
    matricula = models.ForeignKey(Matricula, on_delete=models.CASCADE, verbose_name=u'Matricula')
    observacion = models.TextField(verbose_name=u"Observación")
    estado = models.IntegerField(choices=ESTADO_SOLICITUD_MATRICULA, default=1, verbose_name=u"Estado solicitud")
    fechainicioprorroga = models.DateField(verbose_name=u'Fecha inicio prorroga', blank=True, null=True)
    fechafinprorroga = models.DateField(verbose_name=u'Fecha fin prorroga', blank=True, null=True)

    def historial_solicitud(self):
        return self.historialsolicitudprorrogaingresotemamatricula_set.filter(status=True)

    def __str__(self):
        return u'%s' % (self.matricula)

    class Meta:
        verbose_name = "Solicitud Prorroga  Ingreso Tema Matricula"
        verbose_name_plural = "Solicitud Prorroga  Ingreso Tema Matricula"
        ordering = ('id',)


class HistorialSolicitudProrrogaIngresoTemaMatricula(ModeloBase):
    solicitud = models.ForeignKey(SolicitudProrrogaIngresoTemaMatricula, on_delete=models.CASCADE,verbose_name=u'Solicitud')
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE,verbose_name=u'Persona')
    estado = models.IntegerField(choices=ESTADO_SOLICITUD_MATRICULA, default=1, verbose_name=u"Estado solicitud")

    def __str__(self):
        return u'%s' % (self.solicitud)

    class Meta:
        verbose_name = u'Historial Solicitud Prorroga  Ingreso Tema Matricula'
        verbose_name_plural = u'Historial Solicitud Prorroga  Ingreso Tema Matricula'
        ordering = ('id',)

## revision trabajo final de titulacion posgrado
class Pregunta(ModeloBase):
    descripcion = models.TextField(default='', verbose_name=u'Descripcion')

    def __str__(self):
        return u'%s' % (self.descripcion)

    class Meta:
        verbose_name = u'Pregunta'
        verbose_name_plural = u'Preguntas'
        ordering = ('id',)

class Informe(ModeloBase):
    descripcion = models.TextField(default='', verbose_name=u'Descripcion')
    tipo = models.IntegerField(choices=TIPO_INFORME, default=1, verbose_name=u"Tipo informe")
    mecanismotitulacionposgrado= models.ForeignKey('sga.MecanismoTitulacionPosgrado', on_delete=models.CASCADE , verbose_name=u'Mecanismo Titulación',blank=True, null = True,)
    estado = models.BooleanField(default=False, verbose_name=u'Activo')

    def __str__(self):
        return u'%s' % (self.descripcion)

    def en_uso(self):
        return self.seccioninforme_set.filter(status=True).exists()

    def obtener_secciones(self):
        return self.seccioninforme_set.filter(status=True).order_by('id')

    def obtener_dictamen(self):
        return ESTADO_DICTAMEN[1:]

    class Meta:
        verbose_name = u'Informe'
        verbose_name_plural = u'Informes'
        ordering = ('id',)

class SeccionInforme(ModeloBase):
    informe = models.ForeignKey(Informe, on_delete=models.CASCADE,verbose_name=u'informe')
    seccion = models.ForeignKey('sga.EtapaTemaTitulacionPosgrado', on_delete=models.CASCADE,verbose_name=u'Sección')
    orden = models.IntegerField(default=0, verbose_name=u'Orden')

    def __str__(self):
        return u'%s: %s' % (self.informe,self.seccion)

    def obtener_preguntas_seccion(self):
        return self.seccioninformepregunta_set.filter(status=True)

    def en_uso(self):
        return  self.seccioninformepregunta_set.filter(status=True).exists()

    class Meta:
        verbose_name = u'Informe etapa'
        verbose_name_plural = u'Informe etapa'
        ordering = ('id',)

class SeccionInformePregunta(ModeloBase):
    seccion_informe = models.ForeignKey(SeccionInforme, on_delete=models.CASCADE,verbose_name=u'informe etapa')
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE,verbose_name=u'Pregunta')
    tipo_pregunta = models.IntegerField(choices=TIPO_PREGUNTA, default=1, verbose_name=u"Tipo pregunta")

    def __str__(self):
        return u'%s' % (self.pregunta)

    def en_uso(self):
        return self.preguntarevision_set.filter(status=True).exists()

    class Meta:
        verbose_name = u'Informe etapa'
        verbose_name_plural = u'Informe etapa'
        ordering = ('id',)

class Revision(ModeloBase):
    tribunal = models.ForeignKey('sga.TribunalTemaTitulacionPosgradoMatricula', on_delete=models.CASCADE,verbose_name=u'tribunal')
    archivo = models.FileField(upload_to='archivorevisionpos/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo')
    estado = models.IntegerField(choices=ESTADO_DICTAMEN, default=1, verbose_name=u"Estado")
    observacion = models.TextField(verbose_name=u"Observación")

    def __str__(self):
        return u'%s' % (self.tribunal)

    def obtener_secciones(self):
        return self.seccionrevision_set.filter(status=True).order_by('id')

    def existen_preguntas_sin_responder(self):
        return self.preguntarevision_set.filter(status=True, respuesta ='').exists()

    def obtener_dictamen(self):
        return ESTADO_DICTAMEN[1:]

    def crear_estructura_informe(self,informe,request):
        for seccion in informe.obtener_secciones():
            seccionrevision = SeccionRevision(
                revision=self,
                seccion_informe=seccion
            )
            seccionrevision.save(request)
            for pregunta in seccion.obtener_preguntas_seccion():
                preguntarevision = PreguntaRevision(
                    revision=self,
                    seccion_revision=seccionrevision,
                    seccion_informe_pregunta=pregunta
                )
                preguntarevision.save(request)

    def obtener_temas_individual_o_pareja_titulacion(self):
        maestrantes = []
        if self.tribunal.tematitulacionposgradomatriculacabecera:
            for tema in self.tribunal.tematitulacionposgradomatriculacabecera.obtener_parejas():
                maestrantes.append(tema)
        else:
            maestrantes.append(self.tribunal.tematitulacionposgradomatricula)

        return maestrantes

    def obtener_tutor_individual_pareja(self):
        tutor = None
        if self.tribunal.tematitulacionposgradomatriculacabecera:
            tutor = self.tribunal.tematitulacionposgradomatriculacabecera.tutor
        else:
            tutor = self.tribunal.tematitulacionposgradomatricula.tutor
        return tutor

    def obtener_maestria(self):
        if self.tribunal.tematitulacionposgradomatriculacabecera:
            maestria = self.tribunal.tematitulacionposgradomatriculacabecera.obtener_parejas()[0].matricula.inscripcion.carrera
        else:
            maestria = self.tribunal.tematitulacionposgradomatricula.matricula.inscripcion.carrera
        return maestria

    def obtener_historial_de_revisiones(self):
        return self.historialdocrevisiontribunal_set.filter(status=True).order_by('-id')

    def obtener_mecanismo(self):
        if self.tribunal.tematitulacionposgradomatriculacabecera:
            mecanismo = self.tribunal.tematitulacionposgradomatriculacabecera.mecanismotitulacionposgrado
        else:
            mecanismo = self.tribunal.tematitulacionposgradomatricula.mecanismotitulacionposgrado
        return mecanismo

    def obtener_correccion_revision_tribunal(self):
        tema =None
        correccion =None
        if self.tribunal.tematitulacionposgradomatriculacabecera:
            tema = self.tribunal.tematitulacionposgradomatriculacabecera
            correccion = self.tribunal.tematitulacionposgradomatriculacabecera.tematitulacionposarchivofinal_set.filter(status=True)
        else:
            tema = self.tribunal.tematitulacionposgradomatricula
            correccion = self.tribunal.tematitulacionposgradomatricula.tematitulacionposarchivofinal_set.filter(status=True)

        return correccion.first() if correccion else None







    class Meta:
        verbose_name = u'Revision'
        verbose_name_plural = u'Revisiones'
        ordering = ('id',)

class SeccionRevision(ModeloBase):
    revision = models.ForeignKey(Revision, on_delete=models.CASCADE,verbose_name=u'Revisión')
    seccion_informe = models.ForeignKey(SeccionInforme, on_delete=models.CASCADE,verbose_name=u'Sección')
    observacion = models.TextField(verbose_name=u"Observación")

    def __str__(self):
        return u'%s: %s' % (self.revision,self.seccion_informe)

    def obtener_preguntas_revision(self):
        return self.preguntarevision_set.filter(status=True)

    class Meta:
        verbose_name = u'Seccion Revisión'
        verbose_name_plural = u'Seccion Revisiones'
        ordering = ('id',)

class PreguntaRevision(ModeloBase):
    revision = models.ForeignKey(Revision, on_delete=models.CASCADE,verbose_name=u'Revisión')
    seccion_revision = models.ForeignKey(SeccionRevision, on_delete=models.CASCADE,verbose_name=u'Sección Revisión')
    seccion_informe_pregunta = models.ForeignKey(SeccionInformePregunta, on_delete=models.CASCADE,verbose_name=u'Sección pregunta')
    respuesta = models.TextField(default='', verbose_name=u'Respuesta')
    def __str__(self):
        return u'%s: %s' % (self.revision,self.seccion_informe_pregunta)

    class Meta:
        verbose_name = u'Seccion Revisión'
        verbose_name_plural = u'Seccion Revisiones'
        ordering = ('id',)


class HistorialDocRevisionTribunal(ModeloBase):
    revision = models.ForeignKey(Revision, on_delete=models.CASCADE,verbose_name=u'Revisión')
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE,verbose_name=u'Persona')
    estado = models.IntegerField(choices=ESTADO_DICTAMEN, default=1, verbose_name=u"Estado")
    observacion = models.TextField(verbose_name=u"Observación")
    def __str__(self):
        return u'%s' % (self.revision)

    class Meta:
        verbose_name = u'Historial Revisión'
        verbose_name_plural = u'Historial Revisión'

class EstadoDocumentoTitulacionPosgrado(ModeloBase):
    descripcion = models.CharField(default='', max_length=200, verbose_name=u'Descripcion')
    nombrefirma = models.CharField(default='', max_length=500, verbose_name=u'Nombre')
    habilitado = models.BooleanField(default=True, verbose_name=u'Habilitado')
    orden = models.IntegerField(blank=True, null=True, verbose_name=u'Orden')

    def __str__(self):
        return u'%s' % self.descripcion

    class Meta:
        verbose_name = u"Estado Documento Titulacion Posgrado"
        verbose_name_plural = u"Estados de Documento Titulacion Posgrado"
        unique_together = ('descripcion',)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(EstadoDocumentoTitulacionPosgrado, self).save(*args, **kwargs)

    def en_uso(self):
        return True if self.documentotitulacionposgrado_set.values('id').filter(status=True).exists() else False

class TipoDocumentoTitulacionPosgrado(ModeloBase):
    descripcion = models.CharField(default='', max_length=300, verbose_name=u'Descripcion')

    def __str__(self):
        return u'%s' % self.descripcion

    class Meta:
        verbose_name = u"Tipo Documento Titulacion Posgrado"
        verbose_name_plural = u"Tipos de Documento Titulacion Posgrado"
        unique_together = ('descripcion',)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper()
        super(TipoDocumentoTitulacionPosgrado, self).save(*args, **kwargs)

    def en_uso(self):
        return True if self.documentotitulacionposgrado_set.values('id').filter(status=True).exists() else False

class DocumentoTitulacionPosgrado(ModeloBase):
    tematitulacionposgrado = models.ForeignKey('sga.TemaTitulacionPosgradoMatricula', blank=True, null=True, verbose_name=u"Tema Titulacion Posgrado Matricula", on_delete=models.CASCADE)
    tipodocumentotitulacion = models.ForeignKey(TipoDocumentoTitulacionPosgrado, blank=True, null=True, verbose_name=u"Tipo Documento Titulacion Posgrado", on_delete=models.CASCADE)
    estadodocumentotitulacion = models.ForeignKey(EstadoDocumentoTitulacionPosgrado, blank=True, null=True, verbose_name=u"EstadoDocumentoTitulacionPosgrado", on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='documentotitulacionposgrado/%Y/%m/%d', blank=True, null=True, verbose_name=u'Documento titulacion posgrado')
    fecha = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha')

    def __str__(self):
        return u'%s - %s: %s' % (self.tematitulacionposgrado.__str__(), self.tipodocumentotitulacion.__str__(), self.estadodocumentotitulacion.__str__())

    class Meta:
        verbose_name = u"Documento Titulacion Posgrado"
        verbose_name_plural = u"Documentos Titulacion Posgrado"
        ordering = ['-id']

class HistorialDocumentoTitulacionPosgrado(ModeloBase):
    documentotitulacion = models.ForeignKey(DocumentoTitulacionPosgrado, blank=True, null=True, verbose_name=u"Documento Titulacion Posgrado", on_delete=models.CASCADE)
    estadodocumentotitulacion = models.ForeignKey(EstadoDocumentoTitulacionPosgrado, blank=True, null=True, verbose_name=u"EstadoDocumentoTitulacionPosgrado", on_delete=models.CASCADE)
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Quien modifica', on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='documentotitulacionposgradohistorial/%Y/%m/%d', blank=True, null=True, verbose_name=u'Documento titulacion posgrado historial')
    fecha = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha')

    def __str__(self):
        return u'%s: %s' % (self.documentotitulacion.__str__(), self.persona.__str__())

    class Meta:
        verbose_name = u"Historial Documento Titulacion Posgrado"
        verbose_name_plural = u"Historial Documentos Titulacion Posgrado"
        ordering = ['-id']


class ConfiguraInformePrograma(ModeloBase):
    informe = models.ForeignKey(Informe, blank=True, null=True, verbose_name=u'Informe', on_delete=models.CASCADE)
    mecanismotitulacionposgrado = models.ForeignKey('sga.mecanismotitulacionposgrado', verbose_name=u'Mecanismo', on_delete=models.CASCADE)
    programa = models.ForeignKey('sga.carrera', blank=True, null=True, verbose_name=u'Programa', on_delete=models.CASCADE)
    estado = models.BooleanField(default=False, verbose_name=u'Activo')
    def __str__(self):
        return f'{self.informe} - {self.mecanismotitulacionposgrado} - {self.programa}'

    class Meta:
        verbose_name = u"Configura Informe Programa"
        verbose_name_plural = u"Configura Informe Programa"
        ordering = ['-id']

class ProductoSecretaria(ModeloBase):
    codigo = models.CharField(max_length=10, verbose_name=u"Código")
    descripcion = models.CharField(max_length=350, verbose_name=u"Descripcion", db_index=True)
    servicio = models.ForeignKey('secretaria.Servicio', related_name='+', on_delete=models.CASCADE, blank=True, null=True, verbose_name=u"Servicio")
    costo = models.DecimalField(max_digits=30, decimal_places=16, default=0, blank=True, null=True, verbose_name=u'Costo')
    tiempo_cobro = models.IntegerField(default=72, blank=True, null=True, verbose_name=u"Tiempo de cobro")
    visible = models.BooleanField(default=False, verbose_name=u"Visible?")

    def __str__(self):
        return f'{self.codigo} - {self.descripcion}'

    def costo_ingreso_titulacion(self, inscripcion):
        from sga.models import Matricula, AsignaturaMalla
        dosmod = 0
        matricula = Matricula.objects.filter(status=True, inscripcion=inscripcion).order_by('id').first()
        cohorte = CohorteMaestria.objects.filter(status=True, periodoacademico=matricula.nivel.periodo).first()
        mallas = AsignaturaMalla.objects.filter(status=True, malla__carrera=cohorte.maestriaadmision.carrera, asignatura__status=True, itinerario__in=[0, inscripcion.itinerario]).count()
        if cohorte.valorprogramacertificado:
            dosmod = (cohorte.valorprogramacertificado / mallas) * 2
        elif cohorte.valorprograma:
            dosmod = (cohorte.valorprograma / mallas) * 2
        return dosmod

    class Meta:
        verbose_name = u"Producto de secretaria"
        verbose_name_plural = u"Productos de secretarias"
        ordering = ['-id']

class ActividadCronogramaTitulacion(ModeloBase):
    nombre = models.CharField(max_length=350, verbose_name=u"Actividad", db_index=True)
    descripcion = models.TextField(default='', verbose_name=u'Descripcion')

    def __str__(self):
        return f'{self.nombre}'

    class Meta:
        verbose_name = u"Actividad de cronograma de titulación"
        verbose_name_plural = u"Actividades de cronograma de titulación"
        ordering = ['-id']

    def subido_por(self):
        from sga.models import Persona
        return Persona.objects.get(usuario=self.usuario_creacion.id)

class DetalleActividadCronogramaTitulacion(ModeloBase):
    solicitud = models.ForeignKey('secretaria.Solicitud', verbose_name="Solicitud del maestrante", on_delete=models.CASCADE)
    periodo = models.ForeignKey('sga.Periodo', verbose_name="Periodo de titulacion", on_delete=models.CASCADE)
    actividad = models.ForeignKey(ActividadCronogramaTitulacion, verbose_name="Actividad", on_delete=models.CASCADE)
    inicio = models.DateField(verbose_name=u"Fecha de inicio", null=True, blank=True)
    fin = models.DateField(verbose_name=u"Fecha de fin", null=True, blank=True)
    observacion = models.TextField(default='', verbose_name=u'Observacion')

    def __str__(self):
        return f'{self.solicitud} - {self.actividad}'

    class Meta:
        verbose_name = u"Detalle de actividad de cronograma de titulación"
        verbose_name_plural = u"Detalles de actividades de cronograma de titulación"
        ordering = ['-id']

class VentasProgramaMaestria(ModeloBase):
    inscripcioncohorte = models.ForeignKey(InscripcionCohorte, blank=True, null=True, verbose_name=u'Postulante', on_delete=models.CASCADE)
    fecha = models.DateField(blank=True, null=True, verbose_name=u"Fecha")
    hora = models.TimeField(blank=True, null=True, verbose_name=u"Hora")
    asesor = models.ForeignKey(AsesorComercial, blank=True, null=True, verbose_name=u'Asesor Comercial', on_delete=models.CASCADE)
    mediopago = models.CharField(default='', max_length=100, verbose_name=u'Medio de Pago')
    facturado = models.BooleanField(default=False, verbose_name=u'¿Venta Facturada?')
    valida = models.BooleanField(default=True, verbose_name=u'¿Venta Válida?')

    def __str__(self):
        return f'{self.inscripcioncohorte.inscripcionaspirante.persona} - {self.inscripcioncohorte.cohortes}'

    class Meta:
        verbose_name = u"Venta de programa de maestría"
        verbose_name_plural = u"Ventas de programa de maestría"
        ordering = ['-id']

class EscuelaPosgrado(ModeloBase):
    nombre= models.CharField(max_length=350, verbose_name=u"Escuela de negocios", db_index=True)

    def __str__(self):
        return f'{self.nombre}'

    class Meta:
        verbose_name = u"Escuela Posgrado"
        verbose_name_plural = u"Escuela Posgrado"
        ordering = ['-id']

class SolicitudIngresoTitulacionPosgrado(ModeloBase):
    matricula = models.ForeignKey('sga.Matricula', on_delete=models.CASCADE,verbose_name=u'Matricula')
    archivo = models.FileField(upload_to='solicitudingresotitulacion/%Y/%m/%d',verbose_name=u'Archivo')
    mecanismotitulacionposgrado = models.ForeignKey('sga.MecanismoTitulacionPosgrado', on_delete=models.CASCADE,verbose_name=u'Mecanismo Titulación')
    firmado = models.BooleanField(default=False, verbose_name=u'firmado')

    def __str__(self):
        return "solicitud de ingreso a unidad de titulación"

    def download_link(self):
        return self.archivo.url

    class Meta:
        verbose_name = u'Solicitud Ingreso Titulacion Posgrado'
        verbose_name_plural = u'Solicitud Ingreso Titulacion Posgrado'
        ordering = ('id',)

class Convenio(ModeloBase):
    descripcion = models.CharField(default='', max_length=250, verbose_name=u'Descripcion')
    fechaInicio = models.DateField(verbose_name=u'Fecha Inicio')
    valido_form = models.BooleanField(default=False, verbose_name=u"Para presentar en formulario externo", blank=True, null=True)
    aplicadescuento = models.BooleanField(default=False, verbose_name=u"Para aplicar descuento", blank=True, null=True)
    porcentajedescuento =  models.FloatField(default=0, verbose_name=u'Porcentaje descuento', blank=True, null=True)
    archivo = models.FileField(upload_to='convenioposgrado/%Y/%m/%d',verbose_name=u'Archivo', blank = True, null = True)
    suberequisito = models.BooleanField(default=False, verbose_name=u"Para subir requisito", blank=True, null=True)
    descripcionrequisito = models.CharField(default='', max_length=250, verbose_name=u'Descripcion requisito', blank=True, null=True)

    def lista_asesores_asignados(self):
        lista = None
        if ConvenioAsesor.objects.filter(status=True, convenio=self).exists():
            lista = ConvenioAsesor.objects.filter(status=True, convenio=self).order_by('asesor__id').distinct()
            #lista = AsesorComercial.objects.filter(status=True, id__in=idase)
        return lista

    def __str__(self):
        return f'[{self.id}] - {self.descripcion}'

    def download_link(self):
        return self.archivo.url

    class Meta:
        verbose_name = u'Convenio'
        verbose_name_plural = u'Convenios'
        ordering = ('id',)

class EvidenciaRequisitoConvenio(ModeloBase):
    inscripcion = models.ForeignKey(InscripcionCohorte, verbose_name=u'Inscripcion Cohorte', on_delete=models.CASCADE)
    convenio = models.ForeignKey(Convenio, verbose_name=u'Convenio', on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='requisitoconvenioposgrado/%Y/%m/%d', blank=True, null = True,verbose_name=u'Archivo')

    class Meta:
        verbose_name = u'Evidencia requisito convenio'
        verbose_name_plural = u'Evidencias requisito convenio'
        ordering = ('id',)

    def __str__(self):
        return f'{self.convenio.descripcion} - {self.inscripcion.inscripcionaspirante}'

    def ultima_evidencia(self):
        if self.detalleevidenciarequisitoconvenio_set.filter(status=True).exists():
            return self.detalleevidenciarequisitoconvenio_set.filter(status=True).order_by('-id')[0]
        return None

class DetalleEvidenciaRequisitoConvenio(ModeloBase):
    evidenciarequisitoconvenio = models.ForeignKey(EvidenciaRequisitoConvenio, verbose_name=u'Evidencia requisito convenio', on_delete=models.CASCADE)
    persona = models.ForeignKey('sga.Persona', blank=True, null=True, verbose_name=u'Quien aprueba', on_delete=models.CASCADE)
    estado_aprobacion = models.IntegerField(choices=ESTADO_REVISION, default=1, verbose_name=u'Estado Aprobacion')
    fecha_aprobacion = models.DateTimeField(blank=True, null=True, verbose_name=u"Fecha de aprobacion o rechazo")
    observacion = models.TextField(blank=True, null=True, verbose_name=u"Observación aprobador")
    archivo = models.FileField(upload_to='requisitoconvenioposgrado/%Y/%m/%d', blank=True, null = True, verbose_name=u'Archivo')

    class Meta:
        verbose_name = u'Detalle evidencia requisito convenio'
        verbose_name_plural = u'Detalles evidencia requisito convenio'
        ordering = ('id',)

    def __str__(self):
        return f'{self.evidenciarequisitoconvenio.inscripcion.inscripcionaspirante}'

class ConvenioAsesor(ModeloBase):
    convenio = models.ForeignKey(Convenio, verbose_name=u'Convenio', on_delete=models.CASCADE)
    asesor = models.ForeignKey(AsesorComercial, verbose_name=u'Asesor', on_delete=models.CASCADE)
    fechaFin = models.DateField(verbose_name=u'Fecha Fin')

    def __str__(self):
        return f'Convenio [{self.convenio.id}] - {self.asesor}'

    class Meta:
        verbose_name = u'Convenio Asesor'
        verbose_name_plural = u'Convenio Asesores'
        ordering = ('id',)

class MecanismoDocumentosTutoriaPosgrado(ModeloBase):
    mecanismotitulacionposgrado = models.ForeignKey("sga.MecanismoTitulacionPosgrado", on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Mecanismo')
    convocatoria = models.ForeignKey("sga.ConfiguracionTitulacionPosgrado",on_delete=models.CASCADE, verbose_name=u'Convocatoria', blank=True, null=True)
    tipo = models.IntegerField(choices=TIPO_ARCHIVO_PORSGRADO, default=1, verbose_name=u"Tipo de Archivo")
    orden = models.IntegerField(default=0, verbose_name=u'Orden')

    class Meta:
        verbose_name = u"MecanismoDocumentosTutoriaPosgrado"
        verbose_name_plural = u"MecanismoDocumentosTutoriaPosgrado"
        ordering = ['id']

    def __str__(self):
        return u'%s' % self.get_tipo_display()

class CabeceraNotificacionMasiva(ModeloBase):
    titulo = models.CharField(verbose_name=u'Titulo de la Notificación', max_length=300)
    cuerpo = models.TextField(verbose_name=u'Cuerpo de la Notificación')

    class Meta:
        verbose_name = u"CabeceraNotificacionMasiva"
        verbose_name_plural = u"CabeceraNotificacionMasiva"
        ordering = ['id']

    def __str__(self):
        return u'%s' % self.titulo


class DetalleCabeceraNotificacionMasiva(ModeloBase):
    cabeceranotificacionmasiva = models.ForeignKey(CabeceraNotificacionMasiva, on_delete=models.CASCADE, verbose_name=u'cabecera')
    notificacion = models.ForeignKey("sga.Notificacion", on_delete=models.CASCADE, verbose_name=u'notificacion')

    class Meta:
        verbose_name = u"CabeceraNotificacionMasiva"
        verbose_name_plural = u"CabeceraNotificacionMasiva"
        ordering = ['id']

    def __str__(self):
        return u'%s' % self.cabeceranotificacionmasiva

class EncuestaTitulacionPosgrado(ModeloBase):
    periodo = models.ForeignKey("sga.Periodo", on_delete=models.CASCADE, verbose_name=u'periodo', blank=True, null = True)
    configuraciontitulacionposgrados = models.ManyToManyField("sga.ConfiguracionTitulacionPosgrado",verbose_name=u'convocatorias')
    descripcion = models.CharField(verbose_name=u'Descripciòn', max_length=600,default = '')
    inicio = models.DateField(blank=True, null=True, verbose_name=u'Fecha Inicio')
    fin = models.DateField(blank=True, null=True, verbose_name=u'Fecha Fin')
    activo = models.BooleanField(default=False, verbose_name=u"Activo")

    class Meta:
        verbose_name = u"EncuestaTitulacionPosgrado"
        verbose_name_plural = u"EncuestaTitulacionPosgrado"
        ordering = ['id']

    def __str__(self):
        return u'%s' % self.descripcion

    def get_convocatorias_str(self):
        try:
            mensaje =''
            for convocatoria in self.configuraciontitulacionposgrados.all():
                mensaje += f'{convocatoria.__str__()}, '
            return mensaje
        except Exception as ex:
            return ''

    def get_sedes(self):
        return self.sedeencuestatitulacionposgrado_set.filter(status=True)

    def get_temastitulacion_de_todas_las_convocatorias(self):
        from sga.models import TemaTitulacionPosgradoMatricula
        return TemaTitulacionPosgradoMatricula.objects.filter(status=True,matricula__inscripcion__graduado__isnull=False, convocatoria__in=self.configuraciontitulacionposgrados.all())

    def get_encuestados(self):
        return self.inscripcionencuestatitulacionposgrado_set.filter(status=True)

    def en_uso(self):
        try:
            esedeencuestatitulacionposgrado =  self.sedeencuestatitulacionposgrado_set.filter(status=True).exists()
            einscripcionencuestatitulacionposgrado = self.inscripcionencuestatitulacionposgrado_set.filter(status=True).exists()

            return True if (esedeencuestatitulacionposgrado or einscripcionencuestatitulacionposgrado) else False
        except Exception as ex:
            return False

    def notificar_encuesta(self,request):
        try:
            a = notificar_responder_encuesta_sede_graduacion_posgrado(request, self.get_encuestados().filter(respondio=False))
            a.start()
        except Exception as ex:
            pass

class SedeEncuestaTitulacionPosgrado(ModeloBase):
    encuestatitulacionposgrado = models.ForeignKey(EncuestaTitulacionPosgrado,on_delete=models.CASCADE, verbose_name=u'encuesta')
    canton = models.ForeignKey("sga.Canton",on_delete=models.CASCADE, verbose_name=u'canton')

    class Meta:
        verbose_name = u"SedeEncuestaTitulacionPosgrado"
        verbose_name_plural = u"SedeEncuestaTitulacionPosgrado"
        ordering = ['id']

    def en_uso(self):
        return True if self.jornadasedeencuestatitulacionposgrado_set.filter(status=True).exists() else False

    def __str__(self):
        return u'%s' % self.canton

    def get_jornada(self):
        return self.jornadasedeencuestatitulacionposgrado_set.filter(status=True)

class JornadaSedeEncuestaTitulacionPosgrado(ModeloBase):
    sedeencuestatitulacionposgrado = models.ForeignKey(SedeEncuestaTitulacionPosgrado,on_delete=models.CASCADE, verbose_name=u'sede')
    fecha = models.DateField(blank=True, null=True, verbose_name=u'Fecha', db_index=True)
    hora_inicio = models.TimeField(verbose_name=u'Hora inicio')
    hora_fin = models.TimeField(verbose_name=u'Hora fin')
    cupo = models.IntegerField(default=0, verbose_name=u'Cantidad de cupos')

    class Meta:
        verbose_name = u"SedeEncuestaTitulacionPosgrado"
        verbose_name_plural = u"SedeEncuestaTitulacionPosgrados"
        ordering = ['id']

    def __str__(self):
        return u'%s -inicio: %s fin: %s' % (self.fecha,self.hora_inicio, self.hora_fin)

    def en_uso(self):
        return True if self.respuestasedeinscripcionencuesta_set.filter(status=True).exists() else False

    def get_cupo_asignado(self):
        return self.respuestasedeinscripcionencuesta_set.filter(status=True,jornadasedeencuestatitulacionposgrado = self).count()

    def get_cupo_disponible(self):
        return self.cupo - self.get_cupo_asignado()

class InscripcionEncuestaTitulacionPosgrado(ModeloBase):
    encuestatitulacionposgrado = models.ForeignKey(EncuestaTitulacionPosgrado, on_delete=models.CASCADE,verbose_name=u'encuesta',blank=True, null=True)
    inscripcion = models.ForeignKey("sga.Inscripcion", on_delete=models.CASCADE, verbose_name=u'Inscripción',blank=True, null=True)
    respondio = models.BooleanField(default=False, verbose_name=u"Respondido")
    observacion = models.TextField(default='', verbose_name=u'observación', blank=True, null=True)
    participa = models.BooleanField(default=False, verbose_name=u"Respondido")
    archivo = models.FileField(upload_to='sedegraduacion/archivo', blank=True, null=True, verbose_name=u'Archivo')
    bloque = models.TextField(default='', verbose_name=u'bloque')
    fila = models.TextField(default='', verbose_name=u'fila')
    asiento = models.TextField(default='', verbose_name=u'asiento')
    asistio = models.BooleanField(default=False, verbose_name=u"asistencia")

    class Meta:
        verbose_name = u"InscripcionEncuestaTitulacionPosgrado"
        verbose_name_plural = u"InscripcionEncuestaTitulacionPosgrados"
        ordering = ['id']

    def __str__(self):
        return u'%s' % self.inscripcion

    def get_resultado_encuestado(self):
        return self.respuestasedeinscripcionencuesta_set.filter(status=True).first() if self.respuestasedeinscripcionencuesta_set.filter(status=True).exists() else None

    def puede_generar_pdf_qr(self):
        return True if self.asiento and self.fila and self.bloque else False

    def generar_qr_pdf_sede_graduacion(self,request):
        try:
            from settings import SITE_STORAGE
            from sga.funcionesxhtml2pdf import conviert_html_to_pdf_save_file_model
            from sga.funciones import generar_nombre
            import pyqrcode
            IS_DEBUG = variable_valor('IS_DEBUG')
            data = {}
            dominio_sistema = 'http://127.0.0.1:8000'
            if not IS_DEBUG:
                dominio_sistema = 'https://sga.unemi.edu.ec'
            data["DOMINIO_DEL_SISTEMA"] = dominio_sistema
            temp = lambda x: remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(x.__str__()))

            qrname = f'qr_sede_graduacion_{random.randint(1, 100000).__str__()}_{self.encuestatitulacionposgrado.pk}_{self.id}'
            folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'sedegraduacionposgrado', 'qr'))
            directory = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'sedegraduacionposgrado'))
            os.makedirs(f'{directory}/qr/', exist_ok=True)
            try:
                os.stat(directory)
            except:
                os.mkdir(directory)
            nombrepersona = temp(self.inscripcion.persona.__str__()).replace(' ', '_')
            htmlname = 'sedegraduacion_{}_{}'.format(nombrepersona, random.randint(1, 100000).__str__())
            urlname = "/media/qrcode/sedegraduacionposgrado/%s" % htmlname
            data['url_qr'] = url_qr = f'{SITE_STORAGE}/media/qrcode/sedegraduacionposgrado/qr/{htmlname}.png'

            url = pyqrcode.create(f'{dominio_sistema}/adm_configuracionpropuesta?action=verificar_asistencia_sede_graduacion&id={self.pk}')
            imageqr = url.png(f'{directory}/qr/{htmlname}.png', 16, '#000000')
            data['qrname'] = 'qr' + qrname
            data['eInscripcionEncuestaTitulacionPosgrado'] = self

            pdf_file, response = conviert_html_to_pdf_save_file_model(
                'adm_configuracionpropuesta/encuestas/configuracion/doc/qr_sede_graduacion.html',
                {'pagesize': '1080px 1350px', 'data': data}
            )
            filename = generar_nombre(f'sedegraduacion_{random.randint(1, 100000).__str__()}_{self.id}_', f'{self.encuestatitulacionposgrado.pk}') + ".pdf"
            self.archivo.save(filename, pdf_file, save=True)
            self.save(request)
        except Exception as ex:
            pass

    def respondio_and_participa(self):
        return True if self.participa and self.respondio else False

class RespuestaSedeInscripcionEncuesta(ModeloBase):
    inscripcionencuestatitulacionposgrado = models.ForeignKey(InscripcionEncuestaTitulacionPosgrado, on_delete=models.CASCADE, verbose_name=u'Inscripción',blank=True, null=True)
    jornadasedeencuestatitulacionposgrado = models.ForeignKey(JornadaSedeEncuestaTitulacionPosgrado, on_delete=models.CASCADE, verbose_name=u'jornada',blank=True, null=True)

    class Meta:
        verbose_name = u"RespuestaSedeInscripcionEncuesta"
        verbose_name_plural = u"RespuestaSedeInscripcionEncuestas"
        ordering = ['id']

    def __str__(self):
        return u'%s' % self.inscripcionencuestatitulacionposgrado

class EncuestaSatisfaccionDocente(ModeloBase):
    class TipoEncuesta(models.IntegerChoices):
        DOCENTE = 1, "DOCENTE"
        ESTUDIANTES = 2, "ESTUDIANTES"

    descripcion = models.TextField(default='', verbose_name=u'Descripcion', blank=True, null=True)
    tipo = models.IntegerField(choices=TipoEncuesta.choices, default=TipoEncuesta.DOCENTE, verbose_name=u"Tipo de encuesta")
    leyenda = models.TextField(default='', verbose_name=u'Leyenda', blank=True, null=True)
    activo = models.BooleanField(default=True, verbose_name=u"Activo")
    obligatoria = models.BooleanField(default=False, verbose_name=u"Obligatoria")

    class Meta:
        verbose_name = u"Encuesta de satisfaccion docente"
        verbose_name_plural = u"Encuestas de satifaccion docente"
        ordering = ['id']

    def __str__(self):
        return u'%s' % self.descripcion

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        return EncuestaSatisfaccionDocente.objects.filter(descripcion__contains=q).distinct()[:limit]

    def flexbox_repr(self):
        return self.descripcion

    def cantidadencuestados(self):
        return self.inscripcionencuestasatisfacciondocente_set.only("id").filter(status=True, respondio=True).count()

    def cantidadpoblacion(self):
        return self.inscripcionencuestasatisfacciondocente_set.only("id").filter(status=True).count()

    def encuestados(self):
        return self.inscripcionencuestasatisfacciondocente_set.filter(status=True, respondio=True)

    def enuso(self):
        return self.preguntaencuestasatisfacciondocente_set.only("id").filter(status=True).exists()

    def preguntas(self):
        return self.preguntaencuestasatisfacciondocente_set.filter(status=True).order_by('orden')

    def delete(self, *args, **kwargs):
        super(EncuestaSatisfaccionDocente, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.descripcion = self.descripcion.upper().strip()
        super(EncuestaSatisfaccionDocente, self).save(*args, **kwargs)

    def get_preguntas(self):
        return self.preguntaencuestasatisfacciondocente_set.filter(status=True)

class PreguntaEncuestaSatisfaccionDocente(ModeloBase):
    class TipoPregunta(models.IntegerChoices):
        CUADRICULA = 1, "CUADRICULA"
        SI_NO = 2, "SI_NO"
        RANGO = 3, "RANGO"
        ABIERTA = 4, "ABIERTA"
        NUMERO = 5, "NUMERO"
        MULTIPLE = 6, "MULTIPLE"
        FECHA = 7, "FECHA"

    encuesta = models.ForeignKey(EncuestaSatisfaccionDocente, on_delete=models.CASCADE, null=True, blank=True, verbose_name=u"Encuesta")
    tipo = models.IntegerField(choices=TipoPregunta.choices, default=TipoPregunta.CUADRICULA, verbose_name=u"Tipo pregunta")
    descripcion = models.TextField(default='', verbose_name=u'Descripcion', blank=True, null=True)
    observacionporno = models.TextField(default='', verbose_name=u'Observacion por No', blank=True, null=True)
    orden = models.IntegerField(blank=True, null=True, verbose_name=u'Orden pregunta')
    obligatoria = models.BooleanField(default=True, verbose_name=u"obligatoria")

    class Meta:
        verbose_name = u"Pregunta de Encuesta SD"
        verbose_name_plural = u"Preguntas de Encuestas SD"
        ordering = ['id']

    def __str__(self):
        return f'Encuesta: {self.encuesta} - Pregunta: {self.descripcion}'

    def enuso(self):
        return RespuestaCuadriculaEncuestaSatisfaccionDocente.objects.only("id").filter(pregunta=self, status=True).exists()

    def opciones_cuadricula_columnas(self):
        return self.opcioncuadriculaencuestasatisfacciondocente_set.filter(status=True, tipoopcion=2).order_by('orden')

    def opciones_cuadricula_filas(self):
        return self.opcioncuadriculaencuestasatisfacciondocente_set.filter(status=True, tipoopcion=1).order_by('orden')

    def total_opciones_cuadricula_filas(self):
        return self.opcioncuadriculaencuestasatisfacciondocente_set.only("id").filter(status=True, tipoopcion=1).count()

    def total_opciones_cuadricula_columnas(self):
        return self.opcioncuadriculaencuestasatisfacciondocente_set.only("id").filter(status=True, tipoopcion=2).count()

    def opcionotros(self):
        return self.opcioncuadriculaencuestasatisfacciondocente_set.only("id").filter(status=True, opcotros=True).exists()

    def opcionarchivo(self):
        return self.opcioncuadriculaencuestasatisfacciondocente_set.only("id").filter(status=True, oparchivo=True).exists()

    def respuesta_inscrito(self, inscrito):
        return RespuestaCuadriculaEncuestaSatisfaccionDocente.objects.filter(pregunta=self, status=True, inscripcionencuesta=inscrito).first()

    def delete(self, *args, **kwargs):
        super(PreguntaEncuestaSatisfaccionDocente, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        super(PreguntaEncuestaSatisfaccionDocente, self).save(*args, **kwargs)

class OpcionCuadriculaEncuestaSatisfaccionDocente(ModeloBase):
    class TipoOpcionCuadricula(models.IntegerChoices):
        FILA = 1, "FILA"
        COLUMNA = 2, "COLUMNA"

    pregunta = models.ForeignKey(PreguntaEncuestaSatisfaccionDocente, on_delete=models.CASCADE, null=True, blank=True, verbose_name=u"Pregunta")
    descripcion = models.TextField(default='', verbose_name=u'Descripcion', blank=True, null=True)
    valor = models.IntegerField(blank=True, null=True, verbose_name=u'Valor Peso')
    orden = models.IntegerField(blank=True, null=True, verbose_name=u'Orden Valor')
    tipoopcion = models.IntegerField(choices=TipoOpcionCuadricula.choices, default=TipoOpcionCuadricula.FILA, verbose_name=u"Tipo opción de la cuadrícula")
    secuenciapregunta = models.ForeignKey(PreguntaEncuestaSatisfaccionDocente, related_name='+', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=u"Pregunta secuencia")
    opcotros = models.BooleanField(default=False, verbose_name=u"Opcion Otros")
    oparchivo = models.BooleanField(default=False, verbose_name=u"Opcion Archivo")

    def __str__(self):
        return u'Opción: %s' % (self.descripcion)

    def enuso(self):
        return self.pregunta.respuestacuadriculaencuestasatisfacciondocente_set.only("id").filter(status=True).exists()

    def save(self, *args, **kwargs):
        super(OpcionCuadriculaEncuestaSatisfaccionDocente, self).save(*args, **kwargs)

class InscripcionEncuestaSatisfaccionDocente(ModeloBase):
    encuesta = models.ForeignKey(EncuestaSatisfaccionDocente, on_delete=models.CASCADE, null=True, blank=True, verbose_name=u"Encuesta")
    profesormateria = models.ForeignKey('sga.ProfesorMateria', on_delete=models.CASCADE, null=True, blank=True, verbose_name=u"Profesor Materia")
    materiaasignada = models.ForeignKey('sga.MateriaAsignada', on_delete=models.CASCADE, null=True, blank=True, verbose_name=u"Maestrante")
    respondio = models.BooleanField(default=False, verbose_name=u"Respondido")
    inicio = models.DateField(blank=True, null=True, verbose_name=u'Inicio de la encuesta')
    fin = models.DateField(blank=True, null=True, verbose_name=u'Fin de la encuesta')

    class Meta:
        verbose_name = u"Profesor y modulo encuestado"
        verbose_name_plural = u"Profesores y modulos encuestados"
        ordering = ['id']

    def __str__(self):
        if self.profesormateria:
            return f'Profesor: {self.profesormateria.profesor.persona} - Modulo: {self.profesormateria.materia.asignatura} {self.profesormateria.materia.paralelo}'
        else:
            return f'Estudiante: {self.materiaasignada.matricula.inscripcion.persona} - Modulo: {self.materiaasignada.materia.asignatura} {self.materiaasignada.materia.paralelo}'

    def estado_eval(self):
        hoy = datetime.now().date()
        return self.inicio <= hoy <= self.fin

    def fecha_eval(self):
        return RespuestaCuadriculaEncuestaSatisfaccionDocente.objects.filter(status=True, inscripcionencuesta=self).first().fecha_creacion

class RespuestaCuadriculaEncuestaSatisfaccionDocente(ModeloBase):
    inscripcionencuesta = models.ForeignKey(InscripcionEncuestaSatisfaccionDocente, on_delete=models.CASCADE, verbose_name=u"Inscripcion Encuesta")
    pregunta = models.ForeignKey(PreguntaEncuestaSatisfaccionDocente, on_delete=models.CASCADE, verbose_name=u"Pregunta")
    opcioncuadricula = models.ForeignKey(OpcionCuadriculaEncuestaSatisfaccionDocente, on_delete=models.CASCADE, verbose_name=u'Opción de la cuadrícula')
    respuesta = models.TextField(default='', verbose_name=u'Respuesta')
    archivo = models.FileField(upload_to='encuestapos/archivo', blank=True, null=True,verbose_name=u'Archivo')

    class Meta:
        verbose_name = u"Respuesta de pregunta/cuadricula de encuesta SD"
        verbose_name_plural = u"Respuestas de pregunta/cuadricula de encuesta SD"
        ordering = ['id']

    def __str__(self):
        return f'Encuestado: {self.inscripcionencuesta} - Pregunta: {self.pregunta}'

class DetalleRespuestaRubricaPosgrado(ModeloBase):
    respuestarubrica = models.ForeignKey('sga.RespuestaRubrica', on_delete=models.CASCADE)
    rubricapregunta = models.ForeignKey('sga.RubricaPreguntas', on_delete=models.CASCADE)
    valor = models.FloatField(default=0)
    justificacion = models.CharField(max_length=600, blank=True, null=True, verbose_name=u'Justificacion')

    class Meta:
        verbose_name = u"Detalle de respuesta posgrado"
        verbose_name_plural = u"Detalles de respuesta posgrado"
        ordering = ['id']

    def __str__(self):
        return f'Pregunta: {self.respuestarubrica} - Respuesta: {self.valor}'

class ConfiguracionProgramaProfesorInvitado(ModeloBase):
     carrera = models.ManyToManyField('sga.Carrera', verbose_name=u'Carreras profesor invitado')
     rmu_coordinador_de_apoyo = models.DecimalField(max_digits=30, decimal_places=2, default=0,verbose_name=u"RMU coordinador de apoyo")

     class Meta:
         verbose_name = u"ConfiguracionProgramaProfesorInvitado"
         verbose_name_plural = u"ConfiguracionProgramaProfesorInvitado"
         ordering = ['id']

     def __str__(self):
         return f'{self.pk}'

class BalanceCosto(ModeloBase):
    anio = models.IntegerField(default=0, verbose_name=u'Anio del periodo')
    mes = models.IntegerField(choices=MESES_CHOICES, default=0, verbose_name=u'Mes')
    descripcion = models.CharField(default='', max_length=150, verbose_name=u"Descripcion")
    estado = models.IntegerField(default=0, choices=ESTADO_BALANCE_COSTO, verbose_name=u'Estado')
    #campos reporte profesor invitado
    cantidad_medio_tiempo = models.IntegerField(default=0, verbose_name=u'cantidad medio tiempo')
    medio_tiempo = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"valor Medio tiempo profesor invitado")
    cantidad_tiempo_completo = models.IntegerField(default=0, verbose_name=u'cantidad tiempo completo')
    tiempo_completo = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"valor Tiempo completo profesor invitado")
    #campos reporte costo variable
    costo_por_publicidad = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"Costo por publicidad")
    evento_promocionales = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"Eventos promocionales")
    materiales_de_oficina = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"Materiales de oficiona")

    #totales de cada reporte
    total_reporte_coordinador = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"total reporte coordinador")
    total_reporte_coordinador_apoyo = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"total reporte coordinador apoyo")
    total_reporte_profesor_modular = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"total reporte profesor modular")
    total_reporte_profesor_invitado_posgrado = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"total reporte profesor invitado posgrado")
    total_reporte_personal_administrativo = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"total reporte personal administrativo")
    total_reporte_costo_variable = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"total reporte costo variable")

    def __str__(self):
        return f'[{self.pk}]{self.anio} - {self.mes}'

    def generar_reporte_balance_costo_mensual_excel(self,request):
        try:
            import io
            import xlsxwriter
            from pdip.funciones import FORMATOS_CELDAS_EXCEL
            from django.http import HttpResponse
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            ws = workbook.add_worksheet()

            ftitulo1 = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo1"])
            fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])


            ws.merge_range(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo1)
            ws.merge_range(1, 0, 1, 8, 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADOS', ftitulo1)
            ws.merge_range(2, 0, 2, 8, f'BALANCE DE COSTO MENSUAL: {self.anio} - {self.get_mes_display().upper()} ', ftitulo1)
            columns = [
                (u"PROGRAMA", 30),
                (u"MODALIDAD", 25),
                (u"COHORTE", 25),
                (u"TOTAL PARALELO", 20),
                (u"COSTOS FIJOS", 20),
                (u"COSTOS VARIABLES", 20),
                (u"COSTOS TOTALES", 20),
                (u"INGRESOS MATRICULA", 20),
                (u"OTROS INGRESOS", 20),
                (u"TOTAL INGRESOS", 20),
                (u"TOTAL", 20)
            ]

            row_num = 4
            for col_num in range(len(columns)):
                ws.write(row_num, col_num, columns[col_num][0], fcabeceracolumna)
                ws.set_column(col_num, col_num, columns[col_num][1])

            eBalanceCostoReporteMensual = self.get_reporte_mensual()

            row_num += 1
            for grupo_carrera in eBalanceCostoReporteMensual:
                first = True
                rowspan = grupo_carrera['rowspan']
                for item in grupo_carrera['items']:
                    if first:
                        if rowspan > 1:
                            ws.merge_range(row_num, 0, row_num + rowspan - 1, 0, f"{grupo_carrera['carrera'].nombre_completo()}")
                            ws.merge_range(row_num, 1, row_num + rowspan - 1, 1, grupo_carrera['carrera'].get_modalidad_display())
                        else:
                            ws.write(row_num,0, f"{grupo_carrera['carrera'].nombre_completo()}")
                            ws.write(row_num,1,grupo_carrera['carrera'].get_modalidad_display())

                        first = False
                    ws.write(row_num, 2, f"{item['periodo'].numero_cohorte_romano()} - {item['periodo'].anio}")
                    ws.write(row_num, 3, item['paralelo'].totalparalelo)
                    ws.write(row_num, 4, f"{item['paralelo'].costofijo}")
                    ws.write(row_num, 5, f"{item['paralelo'].costovariable}")
                    ws.write(row_num, 6, f"{item['paralelo'].get_costos_totales()}")
                    ws.write(row_num, 7, f"{item['paralelo'].ingresos}")
                    ws.write(row_num, 8, f"{item['paralelo'].otrosingresos}")
                    ws.write(row_num, 9, f"{item['paralelo'].totalingresos}")
                    ws.write(row_num, 10, f"{item['paralelo'].get_total()}")
                    row_num += 1

            # Total row
            total_row_num = row_num
            ws.write(total_row_num, 0, 'Total', fcabeceracolumna)
            ws.merge_range(total_row_num, 0, total_row_num, 2, 'Total', fcabeceracolumna)
            ws.write(total_row_num, 4, f'{self.get_total_costos_fijos()}')
            ws.write(total_row_num, 5, f'{self.get_total_costos_variables()}')
            ws.write(total_row_num, 6, f'{self.get_total_costo_totales()}')
            ws.write(total_row_num, 7, f'{self.get_total_ingresos_matricula()}')
            ws.write(total_row_num, 8, f'{self.get_total_otros_ingresos()}')
            ws.write(total_row_num, 9, f'{self.get_total_ingresos()}')
            ws.write(total_row_num, 10, f'{self.get_ganancias()}')


            workbook.close()
            output.seek(0)
            filename = f'balance_de_costo_mensual_{self.pk}_{self.anio}_{self.mes}.xlsx'
            response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def generar_reporte_balance_costo_mensual_coordinador_programa_excel(self,request):
        try:
            import io
            import xlsxwriter
            from pdip.funciones import FORMATOS_CELDAS_EXCEL
            from django.http import HttpResponse
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            ws = workbook.add_worksheet()

            ftitulo1 = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo1"])
            fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])


            ws.merge_range(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo1)
            ws.merge_range(1, 0, 1, 8, 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADOS', ftitulo1)
            ws.merge_range(2, 0, 2, 8, f'COORDINADORES DE MAESTRÍA: {self.anio} - {self.get_mes_display().upper()} ', ftitulo1)
            columns = [
                (u"PROGRAMA", 30),
                (u"MODALIDAD", 25),
                (u"COHORTE", 25),
                (u"TOTAL PARALELO", 20),
                (u"COORDINADORES DE MAESTRÍA", 20),
                (u"RMU/PARALELO", 20),
                (u"RMU", 20),
                (u"CATEGORIA", 20)
            ]

            row_num = 4
            for col_num in range(len(columns)):
                ws.write(row_num, col_num, columns[col_num][0], fcabeceracolumna)
                ws.set_column(col_num, col_num, columns[col_num][1])

            eBalanceCostoReporteCoordinadores = self.get_reporte_coordinadores()

            row_num += 1
            for grupo_carrera in eBalanceCostoReporteCoordinadores:
                first = True
                for item in grupo_carrera['items']:
                    if first:
                        ws.write(row_num, 0, f"{grupo_carrera['carrera'].nombre_completo()}")
                        ws.write(row_num, 1, grupo_carrera['carrera'].get_modalidad_display())
                        ws.write(row_num, 4, item.cantidad_coordinadores)
                        ws.write(row_num, 6, item.rmu)
                        first = False
                    ws.write(row_num, 2, f'{item.periodo.numero_cohorte_romano()} - {item.periodo.anio}')
                    ws.write(row_num, 3, item.totalparalelo)
                    ws.write(row_num, 5, item.rmu_por_paralelo)
                    ws.write(row_num, 7, 'Coordinador de maestría')
                    row_num += 1

            # Total row
            total_row_num = row_num + 1
            ws.merge_range(total_row_num, 0, total_row_num, 3, 'Total Coordinadores', fcabeceracolumna)
            ws.write(total_row_num, 4, self.get_total_coordinadores())
            ws.write(total_row_num, 5, self.get_total_rmu_division_rmu_por_rmu_por_paralelo())
            ws.write(total_row_num, 6, '')

            workbook.close()
            output.seek(0)
            filename = f'balance_de_costo_mensual_coordinador_{self.pk}_{self.anio}_{self.mes}.xlsx'
            response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def generar_reporte_balance_costo_mensual_coordinador_apoyo_excel(self,request):
        try:
            import io
            import xlsxwriter
            from pdip.funciones import FORMATOS_CELDAS_EXCEL
            from django.http import HttpResponse
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            ws = workbook.add_worksheet()

            ftitulo1 = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo1"])
            fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])


            ws.merge_range(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo1)
            ws.merge_range(1, 0, 1, 8, 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADOS', ftitulo1)
            ws.merge_range(2, 0, 2, 8, f'COORDINADORES DE APOYO MAESTRÍA: {self.anio} - {self.get_mes_display().upper()} ', ftitulo1)
            columns = [
                (u"PROGRAMA", 30),
                (u"MODALIDAD", 25),
                (u"COHORTE", 25),
                (u"TOTAL PARALELO", 20),
                (u"N° COORDINADORES DE APOYO", 20),
                (u"N° DE HORA", 20),
                (u"TOTAL", 20),
                (u"DISTRIBUCIÓN", 20),
                (u"CATEGORÍA", 20)
            ]

            row_num = 4
            for col_num in range(len(columns)):
                ws.write(row_num, col_num, columns[col_num][0], fcabeceracolumna)
                ws.set_column(col_num, col_num, columns[col_num][1])

            eBalanceCostoReporteCoordinadoresApoyo = self.get_reporte_coordinadores_apoyo()

            row_num += 1
            for grupo_carrera in eBalanceCostoReporteCoordinadoresApoyo:
                first = True
                for item in grupo_carrera['items']:
                    if first:
                        ws.write(row_num, 0, f"{grupo_carrera['carrera'].nombre_completo()}")
                        ws.write(row_num, 1, grupo_carrera['carrera'].get_modalidad_display())
                        ws.write(row_num, 6, f"{grupo_carrera['total']}")
                        first = False
                    ws.write(row_num, 2, f'{item.periodo.numero_cohorte_romano()} - {item.periodo.anio}')
                    ws.write(row_num, 3, item.totalparalelo)
                    ws.write(row_num, 4, item.cantidad_coordinadorapoyo)
                    ws.write(row_num, 5, item.numero_de_hora)
                    ws.write(row_num, 7, f'{item.distribucion}')
                    ws.write(row_num, 8, 'Coordinador de apoyo')
                    row_num += 1

            # Total row
            total_row_num = row_num
            ws.write(total_row_num, 0, 'Total', fcabeceracolumna)
            ws.merge_range(total_row_num, 0, total_row_num, 5, 'Total', fcabeceracolumna)
            ws.write(total_row_num, 6, f'{self.total_acumulado_coordinador_apoyo()}')
            ws.write(total_row_num, 7, f'{self.total_reporte_coordinador_apoyo}')

            workbook.close()
            output.seek(0)
            filename = f'balance_de_costo_mensual_coordinador_apoyo_{self.pk}_{self.anio}_{self.mes}.xlsx'
            response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def generar_reporte_balance_costo_mensual_profesor_posgrado_excel(self,request):
        try:
            import io
            import xlsxwriter
            from pdip.funciones import FORMATOS_CELDAS_EXCEL
            from django.http import HttpResponse
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            ws = workbook.add_worksheet()

            ftitulo1 = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo1"])
            fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])


            ws.merge_range(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo1)
            ws.merge_range(1, 0, 1, 8, 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADOS', ftitulo1)
            ws.merge_range(2, 0, 2, 8, f'PROFESOR POSGRADO: {self.anio} - {self.get_mes_display().upper()} ', ftitulo1)
            columns = [
                (u"PROGRAMA", 30),
                (u"MODALIDAD", 25),
                (u"COHORTE", 25),
                (u"TOTAL PARALELO", 20),
                (u"N° PROFESORES POSGRADO", 20),
                (u"RMU POR COHORTE", 20),
                (u"TOTAL", 20),
                (u"RMU/PARALELO", 20),
                (u"TOTAL", 20),
                (u"CATEGORÍA", 20)
            ]

            row_num = 4
            for col_num in range(len(columns)):
                ws.write(row_num, col_num, columns[col_num][0], fcabeceracolumna)
                ws.set_column(col_num, col_num, columns[col_num][1])

            eBalanceCostoReporteProfesorModular = self.get_reporte_profesor_modular_invitado()


            row_num += 1
            for grupo_carrera in eBalanceCostoReporteProfesorModular:
                first = True
                for item in grupo_carrera['items']:
                    if first:
                        ws.write(row_num, 0, f"{grupo_carrera['carrera'].nombre_completo()}")
                        ws.write(row_num, 1, grupo_carrera['carrera'].get_modalidad_display())
                        ws.write(row_num, 4, f"{grupo_carrera['cantidad_medio_tiempo_tiempo_completo']}")
                        ws.write(row_num, 6, f"{grupo_carrera['total_medio_tiempo_tiempo_completo']}")
                        ws.write(row_num, 7, f"{grupo_carrera['rmu_por_paralelo']}")
                        ws.write(row_num, 8, f"{grupo_carrera['total_rmu_por_maestria']}")
                        first = False
                    ws.write(row_num, 2, f'{item.periodo.numero_cohorte_romano()} - {item.periodo.anio}')
                    ws.write(row_num, 3, item.totalparalelo)

                    ws.write(row_num, 5, item.rmu_por_cohorte)
                    ws.write(row_num, 9, 'Profesor posgrado')
                    row_num += 1

            # Fila de total
            total_row_num = row_num
            ws.merge_range(total_row_num, 0, total_row_num, 3, '')
            ws.write(total_row_num, 4, self.get_total_paralelos_profesor_invitado(),fcabeceracolumna)

            workbook.close()
            output.seek(0)
            filename = f'balance_de_costo_mensual_profesor_posgrado_{self.pk}_{self.anio}_{self.mes}.xlsx'
            response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def generar_reporte_balance_costo_mensual_costo_variable_excel(self,request):
        try:
            import io
            import xlsxwriter
            from pdip.funciones import FORMATOS_CELDAS_EXCEL
            from django.http import HttpResponse
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            ws = workbook.add_worksheet()

            ftitulo1 = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo1"])
            fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])

            ws.merge_range(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo1)
            ws.merge_range(1, 0, 1, 8, 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADOS', ftitulo1)
            ws.merge_range(2, 0, 2, 8, f'PROFESOR POSGRADO: {self.anio} - {self.get_mes_display().upper()} ', ftitulo1)
            columns = [
                (u"PROGRAMA", 30),
                (u"MODALIDAD", 25),
                (u"COHORTE", 25),
                (u"TOTAL PARALELO", 20),
                (u"COSTO POR PUBLICIDAD", 20),
                (u"EVENTOS PROMOCIONALES", 20),
                (u"MATERIALES DE OFICINA", 20),
                (u"TOTAL", 20)
            ]

            row_num = 4
            for col_num in range(len(columns)):
                ws.write(row_num, col_num, columns[col_num][0], fcabeceracolumna)
                ws.set_column(col_num, col_num, columns[col_num][1])

            EBalanceCostoReporteCostoVariable = self.get_reporte_costo_variable()


            row_num += 1
            for grupo_carrera in EBalanceCostoReporteCostoVariable:
                first = True
                for item in grupo_carrera['items']:
                    if first:
                        ws.write(row_num, 0, f"{grupo_carrera['carrera'].nombre_completo()}")
                        ws.write(row_num, 1, grupo_carrera['carrera'].get_modalidad_display())
                        first = False
                    ws.write(row_num, 2, f'{item.periodo.numero_cohorte_romano()} - {item.periodo.anio}')
                    ws.write(row_num, 3, item.totalparalelo)
                    ws.write(row_num, 4, item.costos_por_publicidad)
                    ws.write(row_num, 5, item.eventos_promocionales)
                    ws.write(row_num, 6, item.materiales_de_oficina)
                    ws.write(row_num, 7, item.get_total())
                    row_num += 1

            # Fila de total


            workbook.close()
            output.seek(0)
            filename = f'balance_de_costo_mensual_profesor_posgrado_{self.pk}_{self.anio}_{self.mes}.xlsx'
            response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def generar_reporte_balance_costo_mensual_personal_administrativo_excel(self,request):
        try:
            import io
            import xlsxwriter
            from pdip.funciones import FORMATOS_CELDAS_EXCEL
            from django.http import HttpResponse
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            ws = workbook.add_worksheet()

            ftitulo1 = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo1"])
            fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])

            ws.merge_range(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo1)
            ws.merge_range(1, 0, 1, 8, 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADOS', ftitulo1)
            ws.merge_range(2, 0, 2, 8, f'PERSONAL ADMINISTRATIVO: {self.anio} - {self.get_mes_display().upper()} ', ftitulo1)
            columns = [
                (u"PROGRAMA", 30),
                (u"MODALIDAD", 25),
                (u"COHORTE", 25),
                (u"TOTAL PARALELO", 20),
                (u"PERSONAL ADMINISTRATIVO", 20),
                (u"RMU POR COHORTE", 20),
                (u"TOTAL PROGRAMA", 20),
                (u"TOTAL ACTIVIDADES", 20),
                (u"TOTAL", 20),
                (u"RMU POR PARALELO", 20),
                (u"CATEGORÍA", 20)
            ]

            row_num = 4
            for col_num in range(len(columns)):
                ws.write(row_num, col_num, columns[col_num][0], fcabeceracolumna)
                ws.set_column(col_num, col_num, columns[col_num][1])

            eBalanceCostoReportePersonalAdministrativo = self.get_reporte_personal_administrativo()


            row_num += 1
            for grupo_carrera in eBalanceCostoReportePersonalAdministrativo:
                first = True
                for item in grupo_carrera['items']:
                    if first:
                        ws.write(row_num, 0, f"{grupo_carrera['carrera'].nombre_completo()}")
                        ws.write(row_num, 1, grupo_carrera['carrera'].get_modalidad_display())
                        ws.write(row_num, 4, grupo_carrera['total_administrativos'])
                        ws.write(row_num, 6, grupo_carrera['total_por_carrera_de_hoja_de_trabajo'])
                        ws.write(row_num, 7, grupo_carrera['division_total_actividades_por_numero_de_programa'])
                        ws.write(row_num, 8, grupo_carrera['total'])
                        ws.write(row_num, 9, grupo_carrera['rmu_por_paralelo'])
                        first = False
                    ws.write(row_num, 2, f'{item.periodo.numero_cohorte_romano()} - {item.periodo.anio}')
                    ws.write(row_num, 3, item.totalparalelo)
                    ws.write(row_num, 5, item.rmu_por_cohorte)
                    ws.write(row_num, 10, ' Personal Administrativo')

                    row_num += 1

                    # Fila de total
                total_row_num = row_num
                ws.merge_range(total_row_num, 0, total_row_num, 3, 'Total', fcabeceracolumna)
                ws.write(total_row_num, 4, self.get_total_administrativos_reporte_hoja_de_trabajo(), fcabeceracolumna)
                ws.write(total_row_num, 6, f"{self.get_total_hoja_personal_administrativo_por_el_valor_por_programa()}", fcabeceracolumna)
                ws.write(total_row_num, 8, f"{self.total_reporte_personal_administrativo}", fcabeceracolumna)


            workbook.close()
            output.seek(0)
            filename = f'balance_de_costo_mensual_personal_administrativo_{self.pk}_{self.anio}_{self.mes}.xlsx'
            response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def generar_reporte_balance_costo_mensual_profesor_modular_excel(self,request):
        try:
            import io
            import xlsxwriter
            from pdip.funciones import FORMATOS_CELDAS_EXCEL
            from django.http import HttpResponse
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            ws = workbook.add_worksheet()

            ftitulo1 = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo1"])
            fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])

            ws.merge_range(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo1)
            ws.merge_range(1, 0, 1, 8, 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADOS', ftitulo1)
            ws.merge_range(2, 0, 2, 8, f'PERSONAL ADMINISTRATIVO: {self.anio} - {self.get_mes_display().upper()} ', ftitulo1)
            columns = [
                (u"PROGRAMA", 30),
                (u"MODALIDAD", 25),
                (u"COHORTE", 25),
                (u"TOTAL PARALELO", 20),
                (u"N° DE MÓDULOS A DICTAR CONFORME A MALLA", 20),
                (u"DESGLOCE DE LOS MODULOS A DICTAR", 20),
                (u"N° DE HORAS POR MÓDULOS", 20),
                (u"TOTAL HORAS", 20),
                (u"VALOR POR HORA", 20),
                (u"SUBTOTAL", 20),
                (u"SUBTOTAL A CERTIFICAR", 20),
                (u"MULTIPLICADOR", 20),
                (u"TOTAL A CERTIFICAR", 20),
                (u"CATEGORÍA", 20)
            ]

            row_num = 4
            for col_num in range(len(columns)):
                ws.write(row_num, col_num, columns[col_num][0], fcabeceracolumna)
                ws.set_column(col_num, col_num, columns[col_num][1])

            eBalanceCostoReporteProfesorModular = self.get_reporte_profesor_modular()

            row_num += 1
            for grupo_carrera in eBalanceCostoReporteProfesorModular:
                first = True
                if isinstance(grupo_carrera, dict):
                    for item in grupo_carrera['items']:
                        if first:
                            ws.write(row_num, 0, f"{grupo_carrera['carrera'].nombre_completo()}")
                            ws.write(row_num, 1, grupo_carrera['carrera'].get_modalidad_display())
                            ws.write(row_num, 2, f"{grupo_carrera['periodo'].numero_cohorte_romano()} - {grupo_carrera['periodo'].anio}")
                            ws.write(row_num, 3, item.totalparalelo)
                            ws.write(row_num, 4, item.cantidad_modulo_dictar)
                            ws.write(row_num, 10,item.get_total_certificar())
                            ws.write(row_num, 11,self.get_multiplicador(grupo_carrera['carrera'].pk, grupo_carrera['periodo'].pk))
                            ws.write(row_num, 12, self.get_tot_certificar(grupo_carrera['carrera'].pk,grupo_carrera['periodo'].pk))

                            first = False

                        ws.write(row_num, 5, item.desgloce_cantidad_modulo)
                        ws.write(row_num, 6, item.numero_de_hora_por_modulo)
                        ws.write(row_num, 7, item.cantidad_modulo_por_horas)
                        ws.write(row_num, 8, item.valor_por_hora)
                        ws.write(row_num, 9, item.get_sub_total_certificar())
                        ws.write(row_num, 13, f"Profesor") if not item.es_profesor_invitado() else ws.write(row_num, 13, f"Sin categoria")

                        row_num += 1

            # Fila de total
            total_row_num = row_num
            ws.merge_range(total_row_num, 0, total_row_num, 11, 'Total profesores modulares', fcabeceracolumna)
            ws.write(total_row_num, 12, f"{self.total_reporte_profesor_modular}",fcabeceracolumna)

            workbook.close()
            output.seek(0)
            filename = f'balance_de_costo_mensual_profesor_modular_{self.pk}_{self.anio}_{self.mes}.xlsx'
            response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def generar_reporte_mensual_acumulado_excel(self,request,ids):
        try:
            import io
            import xlsxwriter
            from pdip.funciones import FORMATOS_CELDAS_EXCEL
            from django.http import HttpResponse
            from collections import defaultdict
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            ws = workbook.add_worksheet()
            eBalanceCostos = BalanceCosto.objects.filter(pk__in=ids).order_by('anio','mes')
            ftitulo1 = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo1"])
            fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])
            fnegative = workbook.add_format({'font_color': 'red'})
            ws.merge_range(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo1)
            ws.merge_range(1, 0, 1, 8, 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADOS', ftitulo1)
            ws.merge_range(2, 0, 2, 8, f'REPORTE MENSUAL DE COSTO ACUMULADO', ftitulo1)
            columns = [
                (u"PROGRAMA", 30),
                (u"MODALIDAD", 25)

            ]
            # Obtener los meses seleccionados
            fechas_seleccionadas = eBalanceCostos.values_list('anio','mes').distinct()
            meses_y_anios = [f"{anio} - {mes_nombre}" for anio, mes in fechas_seleccionadas for mes_valor, mes_nombre in MESES_CHOICES if mes == mes_valor]

            # Añadir columnas para cada mes seleccionado
            for fecha in meses_y_anios:
                columns.extend([
                    (f"COSTOS {fecha.upper()}", 25),
                    (f"INGRESOS {fecha.upper()}", 25),
                    (f"TOTAL {fecha.upper()}", 25)
                ])

            row_num = 4
            for col_num in range(len(columns)):
                ws.write(row_num, col_num, columns[col_num][0], fcabeceracolumna)
                ws.set_column(col_num, col_num, columns[col_num][1])

            row_num += 1
            ids_carreras = BalanceCostoCarrera.objects.filter(balancecosto__status=True,status=True,balancecosto__in = eBalanceCostos).values_list('carrera',flat=True).distinct()
            eCarreras = Carrera.objects.filter(status=True,pk__in =ids_carreras).order_by('id')

            # Agrupar datos por carrera y fecha
            datos_acumulados = defaultdict( lambda: defaultdict(lambda: {'costos_fijos': 0, 'costos_variables': 0, 'ingresos': 0}))
            for carrera in eCarreras:
                for balance in eBalanceCostos:
                    balance_costo_carrera_periodo_paralelos = BalanceCostoCarreraPeriodoParalelo.objects.filter(balancecostocarreraperiodo__balancecostocarrera__carrera=carrera, balancecostocarreraperiodo__balancecostocarrera__balancecosto=balance)
                    for paralelo in balance_costo_carrera_periodo_paralelos:
                        fecha = f"{balance.anio} - {next(mes_nombre for mes_valor, mes_nombre in MESES_CHOICES if mes_valor == balance.mes)}"
                        datos_acumulados[carrera][fecha]['costos_fijos'] += paralelo.costofijo
                        datos_acumulados[carrera][fecha]['costos_variables'] += paralelo.costovariable
                        datos_acumulados[carrera][fecha]['ingresos'] += paralelo.ingresos
                        datos_acumulados[carrera][fecha]['otrosingresos'] += paralelo.otrosingresos
                        datos_acumulados[carrera][fecha]['totalingresos'] += paralelo.totalingresos

            # Escribir datos en el reporte
            for carrera, datos in datos_acumulados.items():
                ws.write(row_num, 0, carrera.nombre)
                ws.write(row_num, 1, carrera.get_modalidad_display())
                col_num = 2
                for fecha in meses_y_anios:
                    ws.write(row_num, col_num,  datos[fecha]['costos_fijos'] + datos[fecha]['costos_variables'])
                    ws.write(row_num, col_num + 1,  datos[fecha]['ingresos'])
                    ws.write(row_num, col_num + 2,  (datos[fecha]['ingresos'] - (datos[fecha]['costos_fijos'] + datos[fecha]['costos_variables'])))
                    col_num += 3

                row_num += 1

            workbook.close()
            output.seek(0)
            filename = f'balance_de_costo_mensual_acumulado_{self.pk}_{self.anio}.xlsx'
            response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def get_configuraciones(self):
        return ConfiguracionProgramaProfesorInvitado.objects.filter(status=True).first()

    def get_estado_badge(self):
        if self.estado == 0:
            return f"<span class='badge rounded-pill bg-warning'>{self.get_estado_display()}</span>"

        if self.estado == 1:
            return f"<span class='badge rounded-pill bg-success'>{self.get_estado_display()}</span>"

    def estado_balance_generado(self):
        return True if self.estado == 0 else False

    def estado_balance_validado(self):
        return True if self.estado == 1 else False

    class Meta:
        verbose_name = u"Balance de costo"
        verbose_name_plural = u"Balance de costos"
        ordering = ['id']

    def get_configuracion_programas_maestrias_aplican_profesor_invitado(self):
        return ConfiguracionProgramaProfesorInvitado.objects.filter(status=True).first()

    def get_subtotal_certificar_profesor_modulo(self,carrera_id,periodo_id):
        return BalanceCostoReporteProfesorModulo.objects.filter(status=True, balancecosto=self, carrera_id=carrera_id,periodo_id=periodo_id).aggregate(total_certificar=Sum(F('desgloce_cantidad_modulo') * F('numero_de_hora_por_modulo') * F('valor_por_hora')))['total_certificar']

    def get_cantidad_medio_tiempo(self):
        return self.cantidad_medio_tiempo

    def get_cantidad_tiempo_completo(self):
        return self.cantidad_tiempo_completo

    def get_total_tiempo_completo(self):
        return self.tiempo_completo

    def get_total_medio_tiempo_tiempo_completo(self):
        return self.medio_tiempo + self.tiempo_completo

    def get_total_medio_tiempo(self):
        return self.medio_tiempo

    def get_tota_costos_variables_pestana(self):
        return round(self.costo_por_publicidad + self.evento_promocionales + self.materiales_de_oficina,2)

    def save_carrera(self,request,carrera):
        eBalanceCostoCarrera = BalanceCostoCarrera(
            balancecosto = self,
            carrera = carrera
        )
        eBalanceCostoCarrera.save(request)
        return eBalanceCostoCarrera

    def generar_estructura_base_balance_costo(self,request):
        try:
            maestrias_admisions = self.get_maestrias_admision_vigentes()
            for maestrias_admision in maestrias_admisions:
                ofertada = maestrias_admision.cohortes_maestria_activas()
                if ofertada:
                    eMallas = self.get_mallas(maestrias_admision.carrera)
                    eBalanceCostoCarrera = self.save_carrera(request, maestrias_admision.carrera)
                    eCohorteMaestrias = maestrias_admision.cohortes_maestria_activas()
                    for eCohorteMaestria in eCohorteMaestrias:
                        eBalanceCostoCarreraPeriodo = eBalanceCostoCarrera.save_periodo(request, eCohorteMaestria.periodoacademico)
                        totalparalelo = self.obtener_total_paralelos( eCohorteMaestria.periodoacademico, eMallas, self.mes, self.anio)
                        eBalanceCostoCarreraPeriodo.save_totalparalelos(request, totalparalelo)
        except Exception as ex:
            messages.error(request, f'Ocurrió un error al generar estructura balance de costo: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def save_reporte_coordinador_programa(self, request):
        try:
            with transaction.atomic():
                for items_a_replicar in self.get_estructura_balance_costo():
                    carrera = items_a_replicar.balancecostocarreraperiodo.balancecostocarrera.carrera
                    periodo = items_a_replicar.balancecostocarreraperiodo.periodo
                    totalparalelo = items_a_replicar.totalparalelo

                    rmu = self.obtener_rmu_coordinador_programa(carrera)


                    eBalanceCostoReporteCoordinador = BalanceCostoReporteCoordinador(
                        balancecosto=self,
                        carrera=carrera,
                        periodo=periodo,
                        totalparalelo=totalparalelo,
                        rmu=rmu
                    )
                    eBalanceCostoReporteCoordinador.save(request)
                self.save_total_reporte_coordinador_programa(request,self.get_coordinador_programa_total_rmu())
        except Exception as ex:
            messages.error(request, f'Ocurrió un error al guardar  reporte coordinador programa: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
            raise

    def guardar_costo_fijo_coordinador_programa(self,request):
        try:
            eBalanceCostoReporteCoordinadores = self.get_balancecostoreportecoordinador()
            total_paralelos_carreas_agrupadas = self.get_total_paralelos_por_carreras_agrupadas_por_division_de_menciones()
            # Agrupar los datos por carrera
            rmu_por_paralelo = 0
            for item in eBalanceCostoReporteCoordinadores:
                if item.rmu != 0:
                    if item.totalparalelo != 0:
                        rmu_por_paralelo = self.get_total_paralelos_agrupado_por_menciones_o_individual(total_paralelos_carreas_agrupadas, item)
                    else:
                        rmu_por_paralelo = 0
                else:
                    rmu_por_paralelo = 0
                self.save_todos_los_costos_fijos(request, item.carrera, item.periodo, rmu_por_paralelo)
        except Exception as ex:
            messages.error(request, f'Ocurrió un error al guardar costos fijos coordinador de programa: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def guardar_costo_fijo_personal_administrativo(self,request):
        try:
            eBalanceCostoReportePersonalAdministrativo = self.get_balancecostoreportepersonaladministrativo()
            # Agrupar los datos por carrera
            for item in eBalanceCostoReportePersonalAdministrativo:
                rmu_por_cohorte = round(self.rmu_por_paralelo_hoja_de_trabajo_balance_costo_mensual(item.carrera) * item.totalparalelo, 2)
                self.save_todos_los_costos_fijos(request, item.carrera, item.periodo, rmu_por_cohorte)
        except Exception as ex:
            messages.error(request, f'Ocurrió un error al guardar costos fijos personal administrativo: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def get_ingresos_balancedecosto_mensual(self,request,ePeriodo,eCarrera,eMes,eAnio):
        try:
            from sagest.models import Pago
            from django.db.models.functions import ExtractMonth, ExtractYear
            total_pagado = 0
            otrosingresos = 0

            # Filter para obtener rubros solo por matricula
            filtros_ingreso_matricula = Q(pagoliquidacion__isnull=True,
                                          rubro__tipo__subtiporubro=1,
                                          rubro__matricula__nivel__periodo=ePeriodo,
                                          rubro__matricula__inscripcion__carrera=eCarrera,
                                          status=True,
                                          rubro__status=True)

            total_pagado = Decimal(null_to_decimal(
                Pago.objects.values_list('valortotal').filter(filtros_ingreso_matricula)
                .exclude(factura__valida=False)
                .annotate(fecha_mes=ExtractMonth('fecha'), fecha_anio=ExtractYear('fecha'))
                .filter(fecha_mes=eMes, fecha_anio=eAnio)
                .aggregate(valor=Sum('valortotal'))['valor'] or 0, 2)).quantize(Decimal('.01'))

            # Filtros para otros ingresos anclados a la maestria
            filtro_otros_ingresos = Q(~Q(rubro__tipo__subtiporubro=1),
                                      pagoliquidacion__isnull=True,
                                      rubro__matricula__nivel__periodo=ePeriodo,
                                      rubro__matricula__inscripcion__carrera=eCarrera,
                                      status=True,
                                      rubro__status=True)

            otrosingresos = Decimal(null_to_decimal(
                Pago.objects.values_list('valortotal').filter(filtro_otros_ingresos)
                .exclude(factura__valida=False)
                .annotate(fecha_mes=ExtractMonth('fecha'), fecha_anio=ExtractYear('fecha'))
                .filter(fecha_mes=eMes, fecha_anio=eAnio)
                .aggregate(valor=Sum('valortotal'))['valor'] or 0, 2)).quantize(Decimal('.01'))

            return total_pagado, otrosingresos
        except Exception as ex:
            messages.error(request, f'Ocurrió un error al obtener todos los ingresos de matricula, otros ingresos balance de costo: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
            raise

    def guardar_costo_fijo_profesor_modulo(self,request):
        try:
            carreras_periodos_ids = self.balancecostoreporteprofesormodulo_set.filter(status=True).values_list('carrera_id', 'periodo_id').distinct('carrera_id', 'periodo_id').order_by('carrera_id', 'periodo_id')

            for carrera_id, periodo_id in carreras_periodos_ids:
                eBalanceCostoCarreraPeriodo = BalanceCostoCarreraPeriodo.objects.filter(status=True, balancecostocarrera__carrera_id=carrera_id,periodo__id=periodo_id, balancecostocarrera__balancecosto=self).first()
                total_certificar = BalanceCostoCarreraPeriodo.objects.filter(status=True, balancecostocarrera__carrera_id=carrera_id, periodo__id=periodo_id, balancecostocarrera__balancecosto=self).aggregate(total=Sum( F('cantidad_modulos_mult_pmodular') * F('subtotal_certificar_pmodular')))['total']
                self.save_todos_los_costos_fijos(request, eBalanceCostoCarreraPeriodo.balancecostocarrera.carrera, eBalanceCostoCarreraPeriodo.periodo, total_certificar)
        except Exception as ex:
            messages.error(request, f'Ocurrió un error al guardar los costs fijos: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def guardar_ingresos(self,request):
        try:
            with transaction.atomic():
                eBalanceCostoReporteProfesorModular = self.get_balancecostoreporteprofesormodulo()
                # Agrupar los datos por carrera
                if eBalanceCostoReporteProfesorModular:
                    for item in eBalanceCostoReporteProfesorModular:
                        total_ingresos_matricula,otrosingresos = self.get_ingresos_balancedecosto_mensual(request,item.periodo,item.carrera,self.mes,self.anio)
                        self.save_todos_los_ingresos(request, item.carrera, item.periodo, total_ingresos_matricula,otrosingresos)
        except Exception as ex:
            messages.error(request,f'Ocurrió un error al guardar todso los ingresos de total matricula, otros ingresos, otros ingresos balance de costo: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
            raise

    def guardar_costo_variable_profesor_modulo_invitado(self, request):
        try:
            rmu_por_paralelo = (self.get_total_tiempo_completo() + self.get_total_medio_tiempo()) / self.get_total_paralelos_profesor_invitado()
            eBalanceCostoReporteProfesorModuloInvitado = self.get_balancecostoreporteprofesormoduloinvitado()
            for item in eBalanceCostoReporteProfesorModuloInvitado:
                rmu_por_cohorte = round(Decimal(rmu_por_paralelo * item.totalparalelo), 2)
                self.save_todos_los_costos_variables(request, item.carrera, item.periodo, rmu_por_cohorte)
        except Exception as ex:
            messages.error(request, f'Ocurrió un error : {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def guardar_costo_variable_pestana_costo_variables(self, request):
        try:
            eBalanceCostoReporteCostoVariable = self.get_balancecostoreportecostovariable()
            for item in eBalanceCostoReporteCostoVariable:
                self.save_todos_los_costos_variables(request, item.carrera, item.periodo, item.get_total())
        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def calcular_costos_por_publicidad_por_cohorte(self,total_paralelo):
        try:
            return round( (self.costo_por_publicidad /self.get_total_paralelos_pestana_costo_variable())* total_paralelo,2)
        except ZeroDivisionError:
            return 0
        except Exception as ex:
            raise

    def calcular_costos_por_eventos_promocionales_por_cohorte(self,total_paralelo):
        try:
            return round((self.evento_promocionales /self.get_total_paralelos_pestana_costo_variable())*total_paralelo,2)
        except ZeroDivisionError:
            return 0
        except Exception as ex:
            raise

    def calcular_costos_por_materiales_de_oficina_por_cohorte(self,total_paralelo):
        try:
            return round((self.materiales_de_oficina/self.get_total_paralelos_pestana_costo_variable())*total_paralelo,2)
        except ZeroDivisionError:
            return 0
        except Exception as ex:
            raise

    def calcular_costos_por_costos_variables(self, request):
        try:
            eBalanceCostoReporteCostoVariable = self.get_balancecostoreportecostovariable()
            for item in eBalanceCostoReporteCostoVariable:
                item.costos_por_publicidad =self.calcular_costos_por_publicidad_por_cohorte(item.totalparalelo)
                item.eventos_promocionales = self.calcular_costos_por_eventos_promocionales_por_cohorte(item.totalparalelo)
                item.materiales_de_oficina = self.calcular_costos_por_materiales_de_oficina_por_cohorte(item.totalparalelo)
                item.save(request)
        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def guardar_costo_variable_coordinadores_de_apoyo(self, request):
        try:
            eBalanceCostoReporteCoordinadoresApoyo = self.get_balancecostoreportecoordinadorapoyo()
            diccionario_coordinadores_de_apoyos = self.get_todos_los_profesores_de_niveles_y_materia_coordinadores_de_apoyo()
            # Agrupar los datos por carrera
            for item in eBalanceCostoReporteCoordinadoresApoyo:
                total_distribucion = self.get_total_distribucion(self.get_periodos(item.carrera), self.get_mallas(item.carrera), diccionario_coordinadores_de_apoyos)
                cantidad_paralelos_por_carrera = self.get_cantidad_paralelos_por_carrera(item.carrera)
                distribucion = round((total_distribucion / cantidad_paralelos_por_carrera) * item.totalparalelo if cantidad_paralelos_por_carrera != 0 else 0, 2)
                self.save_todos_los_costos_variables(request, item.carrera, item.periodo, distribucion)
        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def save_reporte_coordinador_apoyo(self, request):
        try:
            with transaction.atomic():

                for items_a_replicar in self.get_estructura_balance_costo():
                    carrera = items_a_replicar.balancecostocarreraperiodo.balancecostocarrera.carrera
                    periodo = items_a_replicar.balancecostocarreraperiodo.periodo
                    totalparalelo = items_a_replicar.totalparalelo
                    cantidad_coordinadorapoyo = 0
                    numero_de_hora = 40
                    eBalanceCostoReporteCoordinadorApoyo = BalanceCostoReporteCoordinadorApoyo(
                        balancecosto=self,
                        carrera=carrera,
                        periodo=periodo,
                        totalparalelo=totalparalelo,
                        cantidad_coordinadorapoyo=cantidad_coordinadorapoyo,
                        numero_de_hora=numero_de_hora
                    )
                    eBalanceCostoReporteCoordinadorApoyo.save(request)
                diccionario_coordinadores_de_apoyos = self.get_todos_los_profesores_de_niveles_y_materia_coordinadores_de_apoyo()

                self.save_total_distribucion_por_carrera_coordinador_apoyo(request,diccionario_coordinadores_de_apoyos)
                self.save_total_reporte_coordinadorapoyo_programa(request,self.total_acumulado_distribucion_coordinador_apoyo())
        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
            raise

    def save_reporte_profesor_modulo(self, request):
        try:
            with transaction.atomic():
                for items_a_replicar in self.get_estructura_balance_costo():
                    carrera = items_a_replicar.balancecostocarreraperiodo.balancecostocarrera.carrera
                    periodo = items_a_replicar.balancecostocarreraperiodo.periodo
                    totalparalelo = items_a_replicar.totalparalelo
                    cantidad_modulo_dictar = self.get_numeros_de_modulos_a_dictar_conforme_a_la_malla(periodo, self.get_mallas( carrera),self.mes, self.anio)
                    detalleseAsignaturaMallas = self.get_desgloce_de_los_modulos_a_dictar(periodo, self.get_mallas(carrera))
                    # desgloce_de_los_modulos_a_dictar_agrupados = self.get_desgloce_de_los_modulos_a_dictar_agrupados(detalleseAsignaturaMallas)
                    if detalleseAsignaturaMallas:
                        for detalleseAsignaturaMalla in detalleseAsignaturaMallas:
                            eBalanceCostoReporteProfesorModulo = BalanceCostoReporteProfesorModulo(
                                balancecosto=self,
                                carrera=carrera,
                                periodo=periodo,
                                totalparalelo=totalparalelo,
                                cantidad_modulo_dictar=cantidad_modulo_dictar,
                                desgloce_cantidad_modulo=1,
                                numero_de_hora_por_modulo=detalleseAsignaturaMalla['horasacdtotal'],
                                valor_por_hora=detalleseAsignaturaMalla['valor_x_hora'],
                            )
                            eBalanceCostoReporteProfesorModulo.save(request)
                    else:
                        eBalanceCostoReporteProfesorModulo = BalanceCostoReporteProfesorModulo(
                            balancecosto=self,
                            carrera=carrera,
                            periodo=periodo,
                            totalparalelo=totalparalelo,
                            cantidad_modulo_dictar=0,
                            desgloce_cantidad_modulo=0,
                            numero_de_hora_por_modulo=0,
                            valor_por_hora=0,
                        )
                        eBalanceCostoReporteProfesorModulo.save(request)
                self.save_total_a_certificar_por_carrera_and_periodo_profesor_modulo(request)
                self.save_total_reporte_profesor_modular(request,self.get_total_a_certificar_profesor_modulo())
        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
            raise

    def save_reporte_profesor_modulo_invitado(self, request):
        try:
            with transaction.atomic():
                for items_a_replicar in self.get_estructura_balance_costo():
                    carrera = items_a_replicar.balancecostocarreraperiodo.balancecostocarrera.carrera
                    periodo = items_a_replicar.balancecostocarreraperiodo.periodo
                    totalparalelo = items_a_replicar.totalparalelo
                    if carrera in self.get_configuracion_programas_maestrias_aplican_profesor_invitado().carrera.all():
                        eBalanceCostoReporteProfesorModuloInvitado = BalanceCostoReporteProfesorModuloInvitado(
                            balancecosto=self,
                            carrera=carrera,
                            periodo=periodo,
                            totalparalelo=totalparalelo,
                        )
                        eBalanceCostoReporteProfesorModuloInvitado.save(request)
        except Exception as ex:
            messages.error(request, f'Ocurrió un error save_reporte_profesor_modulo_invitado: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
            raise

    def save_reporte_costo_variable(self, request):
        try:
            with transaction.atomic():
                for items_a_replicar in self.get_estructura_balance_costo():
                    carrera = items_a_replicar.balancecostocarreraperiodo.balancecostocarrera.carrera
                    periodo = items_a_replicar.balancecostocarreraperiodo.periodo
                    totalparalelo = items_a_replicar.totalparalelo
                    eBalanceCostoReporteCostoVariable = BalanceCostoReporteCostoVariable(
                        balancecosto=self,
                        carrera=carrera,
                        periodo=periodo,
                        totalparalelo=totalparalelo,
                    )
                    eBalanceCostoReporteCostoVariable.save(request)
        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
            raise

    def save_reporte_administrativo(self, request):
        try:
            with transaction.atomic():
                self.duplicar_estructura_general_hoja_de_trabajo_en_balance_costo_mensual(request)
                for items_a_replicar in self.get_estructura_balance_costo():
                    carrera = items_a_replicar.balancecostocarreraperiodo.balancecostocarrera.carrera
                    periodo = items_a_replicar.balancecostocarreraperiodo.periodo
                    totalparalelo = items_a_replicar.totalparalelo
                    eBalanceCostoReportePersonalAdministrativo = BalanceCostoReportePersonalAdministrativo(
                        balancecosto=self,
                        carrera=carrera,
                        periodo=periodo,
                        totalparalelo=totalparalelo
                    )
                    eBalanceCostoReportePersonalAdministrativo.save(request)
                eTotal = self.get_total_costo_por_actividad_carrera_personal_administrativo()
                self.save_total_reporte_personal_administrativo(request, eTotal)

        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
            raise

    def save_todos_los_costos_fijos(self,request,eCarrera,ePeriodo,eCostoFijo):
        try:
            ebalance_costo_carrera_periodo_paralelos = BalanceCostoCarreraPeriodoParalelo.objects.filter(balancecostocarreraperiodo__periodo = ePeriodo, balancecostocarreraperiodo__balancecostocarrera__carrera=eCarrera,balancecostocarreraperiodo__balancecostocarrera__balancecosto=self)
            for ebalance_costo_carrera_periodo_paralelo in ebalance_costo_carrera_periodo_paralelos:
                ebalance_costo_carrera_periodo_paralelo.save_costosfijo(request,Decimal(eCostoFijo))
        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def save_todos_los_costos_variables(self,request,eCarrera,ePeriodo,eCostoVariable):
        try:

            ebalance_costo_carrera_periodo_paralelos = BalanceCostoCarreraPeriodoParalelo.objects.filter(balancecostocarreraperiodo__periodo = ePeriodo, balancecostocarreraperiodo__balancecostocarrera__carrera=eCarrera,balancecostocarreraperiodo__balancecostocarrera__balancecosto=self)
            for ebalance_costo_carrera_periodo_paralelo in ebalance_costo_carrera_periodo_paralelos:
                ebalance_costo_carrera_periodo_paralelo.save_costosvariable(request,Decimal(eCostoVariable))
        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def save_total_a_certificar_por_carrera_and_periodo_profesor_modulo(self,request):
        try:
            carreras_periodos_ids = self.balancecostoreporteprofesormodulo_set.filter(status=True).values_list('carrera_id', 'periodo_id').distinct('carrera_id', 'periodo_id').order_by('carrera_id', 'periodo_id')

            for carrera_id, periodo_id in carreras_periodos_ids:
                eBalanceCostoCarreraPeriodo = BalanceCostoCarreraPeriodo.objects.filter(status=True, balancecostocarrera__carrera_id=carrera_id,periodo__id=periodo_id, balancecostocarrera__balancecosto=self).first()
                eBalanceCostoCarreraPeriodo.cantidad_modulos_mult_pmodular = 1
                eBalanceCostoCarreraPeriodo.subtotal_certificar_pmodular = self.get_subtotal_certificar_profesor_modulo(carrera_id,periodo_id)
                eBalanceCostoCarreraPeriodo.save()
        except  Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def save_total_distribucion_por_carrera_coordinador_apoyo(self,request,diccionario_coordinadores_de_apoyos):
        try:
            eBalanceCostoReporteCoordinadoresApoyo = self.get_balancecostoreportecoordinadorapoyo()

            for eCarrera in eBalanceCostoReporteCoordinadoresApoyo.values_list('carrera_id',flat=True).distinct('carrera_id').order_by('carrera_id'):
                carrera = Carrera.objects.get(pk=eCarrera)
                total_distribucion = self.get_total_distribucion(self.get_periodos(carrera), self.get_mallas(carrera), diccionario_coordinadores_de_apoyos)
                eBalanceCostoCarrera = BalanceCostoCarrera.objects.filter(status=True, carrera_id=carrera.pk,balancecosto=self).first()
                eBalanceCostoCarrera.total_distribucion = total_distribucion
                eBalanceCostoCarrera.save()


            for item in eBalanceCostoReporteCoordinadoresApoyo:
                total_distribucion = BalanceCostoCarrera.objects.filter(status=True, carrera_id=item.carrera.pk,balancecosto=self).first().total_distribucion
                cantidad_paralelos_por_carrera = self.get_cantidad_paralelos_por_carrera(item.carrera)
                item.cantidad_coordinadorapoyo = self.total_profesores_apoyo( self.get_paralelos_de_niveles_y_materia_coordinador(item.periodo, self.get_mallas(item.carrera), diccionario_coordinadores_de_apoyos))
                item.distribucion = round((total_distribucion / cantidad_paralelos_por_carrera) * item.totalparalelo if cantidad_paralelos_por_carrera != 0 else 0,2)
                item.save(request)

        except  Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def reiniciar_todos_los_costos_fijos_de_los_programas(self, request, eCarrera, ePeriodo):
        try:
            ebalance_costo_carrera_periodo_paralelos = BalanceCostoCarreraPeriodoParalelo.objects.filter(
                balancecostocarreraperiodo__periodo=ePeriodo,
                balancecostocarreraperiodo__balancecostocarrera__carrera=eCarrera,
                balancecostocarreraperiodo__balancecostocarrera__balancecosto=self)
            for ebalance_costo_carrera_periodo_paralelo in ebalance_costo_carrera_periodo_paralelos:
                ebalance_costo_carrera_periodo_paralelo.reiniciar_costos_fijos(request)
        except Exception as ex:
            messages.error(request, f'Ocurrió un error al reiniciar_todos_los_costos_fijos_de_los_programas: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}' )

    def reiniciar_todos_los_costos_variables_de_los_programas(self, request, eCarrera, ePeriodo):
        try:
            ebalance_costo_carrera_periodo_paralelos = BalanceCostoCarreraPeriodoParalelo.objects.filter(
                balancecostocarreraperiodo__periodo=ePeriodo,
                balancecostocarreraperiodo__balancecostocarrera__carrera=eCarrera,
                balancecostocarreraperiodo__balancecostocarrera__balancecosto=self)
            for ebalance_costo_carrera_periodo_paralelo in ebalance_costo_carrera_periodo_paralelos:
                ebalance_costo_carrera_periodo_paralelo.reiniciarcostosvariables(request)
        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def save_total_reporte_coordinador_programa(self,request,eTotal):
        self.total_reporte_coordinador = eTotal
        self.save(request)

    def save_total_reporte_coordinadorapoyo_programa(self,request,eTotal):
        self.total_reporte_coordinador_apoyo = eTotal
        self.save(request)

    def save_total_reporte_profesor_modular(self,request,eTotal):
        self.total_reporte_profesor_modular = eTotal
        self.save(request)

    def save_total_reporte_profesor_invitado_posgrado(self,request,eTotal):
        self.total_reporte_profesor_invitado_posgrado = eTotal
        self.save(request)

    def save_total_reporte_personal_administrativo(self,request,eTotal):
        self.total_reporte_personal_administrativo = eTotal
        self.save(request)

    def save_total_reporte_costo_variable (self,request,eTotal):
        try:
            self.total_reporte_costo_variable = eTotal
            self.save(request)
        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
            raise


    def save_todos_los_ingresos(self,request,eCarrera,ePeriodo,eIngresos,otrosingresos):
        try:

            ebalance_costo_carrera_periodo_paralelos = BalanceCostoCarreraPeriodoParalelo.objects.filter(balancecostocarreraperiodo__periodo = ePeriodo, balancecostocarreraperiodo__balancecostocarrera__carrera=eCarrera,balancecostocarreraperiodo__balancecostocarrera__balancecosto=self)
            for ebalance_costo_carrera_periodo_paralelo in ebalance_costo_carrera_periodo_paralelos:
                ingresosmatricula = ebalance_costo_carrera_periodo_paralelo.save_ingresos_matricula(request,Decimal(eIngresos))
                otros_ingresos = ebalance_costo_carrera_periodo_paralelo.save_otros_ingresos(request,Decimal(otrosingresos))
                totalingresos = ingresosmatricula + otros_ingresos
                ebalance_costo_carrera_periodo_paralelo.save_total_ingresos(request,Decimal(totalingresos))
        except Exception as ex:
            messages.error(request, f'Ocurrió un error al guardar  todos los ingresos: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
            raise

    def save_items_reportes_del_balance_de_costo(self, request):
        try:
            with transaction.atomic():
                self.save_reporte_coordinador_programa(request)
                self.save_reporte_coordinador_apoyo(request)
                self.save_reporte_profesor_modulo(request)
                self.save_reporte_profesor_modulo_invitado(request)
                self.save_reporte_costo_variable(request)
                self.save_reporte_administrativo(request)
                self.actualizar_costos_fijos(request)
                self.actualizar_costos_variables(request)
                self.guardar_ingresos(request)
        except Exception as ex:
            raise

    def actualizar_costos_fijos(self,request):
        try:
            with transaction.atomic():
                self.reiniciar_costos_fijos(request)
                self.guardar_costo_fijo_coordinador_programa(request)
                self.guardar_costo_fijo_personal_administrativo(request)
                self.guardar_costo_fijo_profesor_modulo(request)
        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
            raise

    def actualizar_costos_variables(self,request):
        try:
            with transaction.atomic():
                self.reiniciar_costos_variables(request)
                self.guardar_costo_variable_profesor_modulo_invitado(request)
                self.guardar_costo_variable_coordinadores_de_apoyo(request)
                self.guardar_costo_variable_pestana_costo_variables(request)
        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
            raise

    def reiniciar_costos_fijos(self,request):
        try:
            eBalanceCostoReporteCoordinadores = self.get_balancecostoreportecoordinador()#cualquier reporte ya que son lo mismmo hasta paralelo entonces son lo mismo que balance costo el general
            for item in eBalanceCostoReporteCoordinadores:
                self.reiniciar_todos_los_costos_fijos_de_los_programas(request, item.carrera, item.periodo)
        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def reiniciar_costos_variables(self,request):
        try:
            eBalanceCostoReporteCoordinadores = self.get_balancecostoreportecoordinador()#cualquier reporte ya que son lo mismmo hasta elcampo paraleloo entonces son lo mismo que balance costo el general
            for item in eBalanceCostoReporteCoordinadores:
                self.reiniciar_todos_los_costos_variables_de_los_programas(request, item.carrera, item.periodo)
        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def get_mallas(self, eCarrera):
        return Malla.objects.filter(carrera_id=eCarrera.pk, vigente=True) if Malla.objects.filter(carrera_id=eCarrera.pk, vigente=True).exists() else None

    def get_periodos(self, eCarrera):
        periodo_id = self.balancecostoreportecoordinadorapoyo_set.filter(status=True,carrera =eCarrera ).values_list('periodo_id',flat=True).distinct()
        return Periodo.objects.filter(pk__in=periodo_id)

    def get_todos_los_profesores_de_niveles_y_materia_coordinadores_de_apoyo(self):
        from sga.models import Persona
        from collections import defaultdict
        # Diccionario global para contar los profesores
        profesor_contador = defaultdict(int)
        maestriaadmision_id = CohorteMaestria.objects.filter(periodoacademico__tipo_id=3, status=True).values_list('maestriaadmision_id', flat=True)
        eMaestriasAdmisiones = MaestriasAdmision.objects.filter(status=True, id__in=maestriaadmision_id).order_by('id')

        for eMaestriaAdmision in eMaestriasAdmisiones:
            eMallas = self.get_mallas(eMaestriaAdmision.carrera)
            ofertada = eMaestriaAdmision.cohortes_maestria_activas()
            if ofertada:
                eCohorteMaestrias = eMaestriaAdmision.cohortes_maestria_activas()
                for eCohorteMaestria in eCohorteMaestrias:
                    eNivel = Nivel.objects.filter(periodo_id=eCohorteMaestria.periodoacademico.pk, status=True).first()
                    if eNivel:
                        eParalelos = Paralelo.objects.filter(nombre__in=eNivel.materia_set.values_list('paralelo', flat=True).filter(status=True, asignaturamalla__malla__in=eMallas.values_list( 'id', flat=True)).distinct(), status=True)
                        for eParalelo in eParalelos:
                            eMaterias = eNivel.materia_set.filter(status=True, asignaturamalla__malla_id__in=eMallas.values_list( 'id', flat=True), paralelo=eParalelo.nombre)
                            profesor__id = ProfesorMateria.objects.filter(materia__in=eMaterias, tipoprofesor_id=8, status=True, profesor__activo=True,materia__inicio__year=self.anio,materia__inicio__month =self.mes).distinct().values_list('profesor__id', flat=True)
                            eProfesores = Profesor.objects.filter(pk__in=profesor__id)
                            # Actualizar el contador de profesores
                            for eProfesor in eProfesores:
                                if eProfesor.pk not in profesor_contador:
                                    profesor_contador[eProfesor.pk] = {
                                        'conteo': 0,
                                        'carreras': set(),
                                        'periodos': set()
                                    }

                                profesor_contador[eProfesor.pk]['conteo'] += 1
                                profesor_contador[eProfesor.pk]['carreras'].add(eMaestriaAdmision.carrera.pk)
                                profesor_contador[eProfesor.pk]['periodos'].add(eNivel.periodo.pk)

        return profesor_contador

    def get_todos_los_profesores_de_niveles_y_materia_coordinadores_de_apoyo_division(self,diccionario_coordinadores_de_apoyos):
        profesor_contador_dividido = {key: round(self.get_configuraciones().rmu_coordinador_de_apoyo / details['conteo'], 2) for key, details in diccionario_coordinadores_de_apoyos.items()}
        return profesor_contador_dividido

    def get_cantidad_asignado_como_coordinador_apoyo(self,eProfesor,diccionario_coordinadores_de_apoyos):
        valor = diccionario_coordinadores_de_apoyos.get(eProfesor.pk, 0)
        return valor

    def get_division_rmu_asignado_como_coordinador_apoyo(self,eProfesor,todos_coordinadores_de_apoyos):
        valor = todos_coordinadores_de_apoyos.get(eProfesor.pk, 0)
        return valor

    def get_profesor_materia(self,eMallas,eNivel,nombre_paralelo,diccionario_coordinadores_de_apoyos):
        from collections import defaultdict
        profesor_contador = defaultdict(int)
        eMaterias = eNivel.materia_set.filter(status=True,asignaturamalla__malla_id__in=eMallas.values_list('id', flat=True),paralelo=nombre_paralelo)
        profesor__id = ProfesorMateria.objects.filter(materia__in=eMaterias, tipoprofesor_id=8, status=True, profesor__activo=True,materia__inicio__year=self.anio,materia__inicio__month =self.mes).distinct().values_list( 'profesor__id', flat=True)
        todos_coordinadores_de_apoyos = self.get_todos_los_profesores_de_niveles_y_materia_coordinadores_de_apoyo_division(diccionario_coordinadores_de_apoyos)
        eProfesores = Profesor.objects.filter(pk__in=profesor__id)
        DetalleProfesorMaterias = list(map(lambda eProfesor: {
            'eProfesor': eProfesor,
            'cantidad': self.get_cantidad_asignado_como_coordinador_apoyo(eProfesor,diccionario_coordinadores_de_apoyos),
            'rmu_division': self.get_division_rmu_asignado_como_coordinador_apoyo(eProfesor,todos_coordinadores_de_apoyos),

        }, eProfesores))
        return DetalleProfesorMaterias

    def get_paralelos_de_niveles_y_materia_coordinador(self,ePeriodo,eMallas,diccionario_coordinadores_de_apoyos):
        detalles_paralelos = None
        eNivel = Nivel.objects.filter(periodo_id=ePeriodo.pk, status=True).first()
        if eNivel:
            eParalelos = Paralelo.objects.filter(nombre__in=eNivel.materia_set.values_list('paralelo', flat=True).filter(status=True, asignaturamalla__malla__in=eMallas.values_list('id',flat=True)).distinct(),status=True)

            detalles_paralelos = list(map(lambda eParalelo: {
                'eParalelo': eParalelo,
                'eProfesorMaterias': self.get_profesor_materia(eMallas,eNivel,eParalelo.nombre,diccionario_coordinadores_de_apoyos),
            }, eParalelos))

        return detalles_paralelos

    def get_materias_de_niveles_y_materia(self,ePeriodo,eMallas):
        materias = None
        eNivel = Nivel.objects.filter(periodo_id=ePeriodo.pk, status=True).first()
        if eNivel:
            materias = eNivel.materia_set.filter(status=True, asignaturamalla__malla__in=eMallas.values_list(  'id', flat=True)).distinct()
            # detalles_materias = list(map(lambda materia: {
            #     'eMateria': materia,
            #
            # }, materias))

        return materias

    def get_total_coordinadores(self):
        from collections import defaultdict
        total_paralelos_carreas_agrupadas = self.get_total_paralelos_por_carreras_agrupadas_por_division_de_menciones()
        total_coordinadores = self.get_balancecostoreportecoordinador().exclude(rmu=0).values_list('carrera_id').distinct().order_by('carrera_id').count()
        for persona_id, details in total_paralelos_carreas_agrupadas.items():  # vuelvo a leer las carreras agrupadas por menciones
            num_carreras = len(details['carreras'])  # total de carreras en esta iteración
            for i, ecarrera in enumerate(details['carreras']):
                carrera_agrupada = Carrera.objects.get(pk=ecarrera)
                total_coordinadores -= 1
                if i == num_carreras - 2:
                    break  # solo acumulo el rmu de una carrera el resto lo ignoro ya que son las misma personas mismo rmu
        return total_coordinadores

    def get_coordinador_programa_total_rmu(self):
        try:
            from collections import defaultdict
            eBalanceCostoReporteCoordinadores = self.get_balancecostoreportecoordinador()
            total_paralelos_carreas_agrupadas = self.get_total_paralelos_por_carreras_agrupadas_por_division_de_menciones()

            acumulador = 0
            agrupado_por_carrera = defaultdict(list)
            for item in eBalanceCostoReporteCoordinadores:
                agrupado_por_carrera[item.carrera].append(item)
            carreras_combinadas = set()
            for persona_id, details in total_paralelos_carreas_agrupadas.items():
                carreras_combinadas.update(details['carreras'])

            for carrera, items in agrupado_por_carrera.items():
                if not carrera.pk in carreras_combinadas:#excluyo a las carreras con menciones repetidas
                    acumulador += items[0].rmu

            for persona_id, details in total_paralelos_carreas_agrupadas.items():#vuelvo a leer las carreras agrupadas por menciones
                for ecarrera in details['carreras']:
                    carrera_agrupada = Carrera.objects.get(pk=ecarrera)
                    acumulador += self.obtener_rmu_coordinador_programa(carrera_agrupada)
                    break#solo acumulo el rmu de una carrera el resto lo ignoro ya que son las misma personas mismo rmu


            return round(acumulador,2)
        except Exception as ex:
            raise

    def get_total_paralelos_agrupado_por_menciones_o_individual(self, total_paralelos_carreas_agrupadas, item):
        try:
            found = False
            rmu_por_paralelo = 0
            for persona_id, details in total_paralelos_carreas_agrupadas.items():
                if item.carrera.id in details['carreras']:
                    total_paralelos_carreras_or_carrera = details['total_paralelos']
                    found = True
                    break
            if not found:
                total_paralelos_carreras_or_carrera = self.get_cantidad_paralelos_por_carrera(item.carrera.id)

            rmu_dividido_por_total_paralelo = item.rmu / total_paralelos_carreras_or_carrera
            rmu_por_paralelo = round(float((item.totalparalelo * rmu_dividido_por_total_paralelo)), 2)
            return rmu_por_paralelo
        except ZeroDivisionError:
            return 0

    def get_total_rmu_division_rmu_por_rmu_por_paralelo(self):
        eBalanceCostoReporteCoordinadores = self.get_balancecostoreportecoordinador()
        total_paralelos_carreas_agrupadas = self.get_total_paralelos_por_carreras_agrupadas_por_division_de_menciones()
        acumulador = 0
        for item in eBalanceCostoReporteCoordinadores:
            if item.rmu != 0:
                item.cantidad_coordinadores = 1
                if item.totalparalelo !=0:
                    acumulador += self.get_total_paralelos_agrupado_por_menciones_o_individual(total_paralelos_carreas_agrupadas,item)
        return Decimal(round(acumulador)).quantize(Decimal('0.00'))

    def get_cantidad_paralelos_por_carrera(self,carrera):
        total_paralelos =BalanceCostoCarreraPeriodoParalelo.objects.filter(status=True,balancecostocarreraperiodo__balancecostocarrera__balancecosto= self,balancecostocarreraperiodo__status=True,balancecostocarreraperiodo__balancecostocarrera__status=True,balancecostocarreraperiodo__balancecostocarrera__balancecosto__status=True,balancecostocarreraperiodo__balancecostocarrera__carrera = carrera).aggregate(total=Sum('totalparalelo'))['total']
        return total_paralelos

    def get_coordinador_programa_maestria(self,carrera):
        eCoordinadores = Persona.objects.filter(pk__in=CohorteMaestria.objects.filter(status=True, maestriaadmision__carrera=carrera, activo=True, periodoacademico__activo=True).values_list('coordinador', flat=True).distinct())
        return eCoordinadores

    def get_contrato_coordinador_carrera(self,carrera):
        from pdip.models import ContratoDip,ContratoCarrera
        from sga.models import CoordinadorCarrera
        hoy = datetime.now().date()
        eeCoordinadorCarrera = CoordinadorCarrera.objects.filter(carrera=carrera, periodo__activo=True)
        if eeCoordinadorCarrera:
            eCoordinador = eeCoordinadorCarrera[0].persona
            contrato_id = ContratoCarrera.objects.filter(status=True, carrera=carrera).values_list('contrato_id', flat=True)
            eContrato = ContratoDip.objects.filter(status=True, pk__in=contrato_id, estado=2, cargo__nombre__icontains='COORDINADOR').order_by('-id').first()
            return eContrato
        return None

    def get_reporte_coordinadores(self):
        try:
            from collections import defaultdict
            eBalanceCostoReporteCoordinadores = self.get_balancecostoreportecoordinador()
            total_paralelos_carreas_agrupadas = self.get_total_paralelos_por_carreras_agrupadas_por_division_de_menciones()
            # Agrupar los datos por carrera
            agrupado_por_carrera = defaultdict(list)
            for item in eBalanceCostoReporteCoordinadores:
                if item.rmu != 0:
                    item.cantidad_coordinadores = 1
                    if item.totalparalelo !=0:
                        item.rmu_por_paralelo = self.get_total_paralelos_agrupado_por_menciones_o_individual(total_paralelos_carreas_agrupadas,item)
                    else:
                        item.rmu_por_paralelo =0
                else:
                    item.cantidad_coordinadores = 0
                    item.rmu_por_paralelo = 0

                agrupado_por_carrera[item.carrera].append(item)
            # Crear una lista con la información necesaria para el template
            datos_para_template = []
            for carrera, items in agrupado_por_carrera.items():
                datos_para_template.append({
                    'carrera': carrera,
                    'contrato_coordinador': self.get_contrato_coordinador_carrera(carrera),
                    'coordinadores': self.get_coordinador_programa_maestria(carrera),
                    'items': items,
                    'rowspan': len(items)
                })
            carreras_al_final =[]
            for persona_id, details in total_paralelos_carreas_agrupadas.items():
                for carrera_id in details['carreras']:
                    if carrera_id not in carreras_al_final:
                        carreras_al_final.append(carrera_id)

            datos_para_template = sorted(datos_para_template, key=lambda x: (x['carrera'].id in carreras_al_final, x['carrera'].id))
            for contador, data in enumerate(datos_para_template, 1):
                data['contador'] = contador

            return datos_para_template
        except Exception as ex:
            pass

    def get_total_distribucion(self, ePeriodos, eMallas, diccionario_coordinadores_de_apoyos):
        acumulador = 0
        for ePeriodo in ePeriodos:
            eNivel = Nivel.objects.filter(periodo_id=ePeriodo.pk, status=True).first()
            if eNivel:
                eParalelos = Paralelo.objects.filter(nombre__in=eNivel.materia_set.values_list('paralelo', flat=True).filter(status=True, asignaturamalla__malla__in=eMallas.values_list( 'id', flat=True)).distinct(),status=True)

                detalles_paralelos = list(map(lambda eParalelo: {
                    'eParalelo': eParalelo,
                    'eProfesorMaterias': self.get_profesor_materia(eMallas, eNivel, eParalelo.nombre,diccionario_coordinadores_de_apoyos),
                }, eParalelos))
                if detalles_paralelos:
                    for detalles_paralelo in detalles_paralelos:
                        for detalles_paralelo in detalles_paralelo['eProfesorMaterias']:
                            acumulador+= detalles_paralelo['rmu_division']
        return Decimal(round(acumulador)).quantize(Decimal('0.00'))

    def total_acumulado_distribucion_coordinador_apoyo(self):
        try:
            acumulador =BalanceCostoCarrera.objects.filter(status=True, balancecosto=self).aggregate(total_distribucion_sum=Sum('total_distribucion'))['total_distribucion_sum']
            return round(acumulador or 0, 2)
        except Exception as ex:
            raise

    def total_acumulado_coordinador_apoyo(self):
        try:
            from collections import defaultdict
            total_distribucion = self.get_balancecostoreportecoordinadorapoyo().aggregate(total_distribucion_sum=Sum('distribucion'))['total_distribucion_sum']
            return Decimal(round(total_distribucion)).quantize(Decimal('0.00'))
        except Exception as ex:
            raise NameError(f'error: {ex}, linea {sys.exc_info()[-1].tb_lineno}')

    def total_profesores_apoyo(self,detalles_paralelos):
        try:
            from collections import defaultdict
            total = 0
            profesor_contador = defaultdict(int)
            if detalles_paralelos:
                for paralelo  in detalles_paralelos:
                    if paralelo:
                        for eProfesorMaterias in paralelo['eProfesorMaterias'] :
                            if eProfesorMaterias['eProfesor'].pk not in profesor_contador:
                                profesor_contador[eProfesorMaterias['eProfesor'].pk]

            return len(profesor_contador)
        except Exception as ex:
            raise NameError(f'error: {ex}, linea {sys.exc_info()[-1].tb_lineno}')

    def get_total_distribucion_guardado_en_balance_costo_carrera_general(self,carrera):
        return BalanceCostoCarrera.objects.filter(status=True, carrera_id=carrera.pk,balancecosto=self).first().total_distribucion

    def get_reporte_coordinadores_apoyo(self):
        try:
            from collections import defaultdict
            diccionario_coordinadores_de_apoyos = self.get_todos_los_profesores_de_niveles_y_materia_coordinadores_de_apoyo()
            eBalanceCostoReporteCoordinadoresApoyo = self.get_balancecostoreportecoordinadorapoyo()
            # Agrupar los datos por carrera
            agrupado_por_carrera = defaultdict(list)
            for item in eBalanceCostoReporteCoordinadoresApoyo:
                agrupado_por_carrera[item.carrera].append(item)
            # Crear una lista con la información necesaria para el template
            datos_para_template = []
            contador =0
            for carrera, items in agrupado_por_carrera.items():
                contador+=1
                total = self.get_total_distribucion_guardado_en_balance_costo_carrera_general(carrera)
                datos_para_template.append({
                    'contador': contador,
                    'carrera': carrera,
                    'total': total,
                    'items': items,
                    'rowspan': len(items)
                })
            return datos_para_template
        except Exception as ex:
            pass

    def get_costo_por_maestria_total_hoja_de_trabajo_balance_de_costo_mensual(self,eCarrera):
        try:
            eActividades = GestionIntegrantesActividadCarreraPosgradoHojaTrabajo.objects.filter(status=True,gestionintegrantesposgradohojatrabajo__status=True,gestionintegrantesposgradohojatrabajo__gestionposgradohojatrabajo__status=True,gestionintegrantesposgradohojatrabajo__gestionposgradohojatrabajo__balancecosto__status=True,gestionintegrantesposgradohojatrabajo__gestionposgradohojatrabajo__balancecosto= self , carrera=eCarrera)
            total = 0
            for eActividad in eActividades:
                total += eActividad.get_mensual()
            return round(total,2)
        except Exception as ex:
            return 0

    def get_costo_total_por_actividad_hoja_de_trabajo_balance_de_costo_mensual(self):
        try:
            eActividades = GestionIntegrantesActividadCarreraPosgradoHojaTrabajo.objects.filter(status=True,gestionintegrantesposgradohojatrabajo__status=True,gestionintegrantesposgradohojatrabajo__gestionposgradohojatrabajo__status=True,gestionintegrantesposgradohojatrabajo__gestionposgradohojatrabajo__balancecosto__status=True,gestionintegrantesposgradohojatrabajo__gestionposgradohojatrabajo__balancecosto= self , carrera__isnull=True)
            total = 0
            for eActividad in eActividades:
                total += eActividad.get_mensual()
            return round(total,2)
        except Exception as ex:
            return 0

    def get_division_total_actividades_balancecosto_hoja_trabajo_cantidad_programa(self):
        try:
            return round(self.get_costo_total_por_actividad_hoja_de_trabajo_balance_de_costo_mensual() / self.get_cantidad_de_programas_personal_administrativo_balance_de_costo(),2)
        except Exception as ex:
            return 0

    def sumatoria_costos_por_actividad_programas_asociados_y_no_asociados(self,eCarrera):
        try:
            return round(self.get_division_total_actividades_balancecosto_hoja_trabajo_cantidad_programa() + self.get_costo_por_maestria_total_hoja_de_trabajo_balance_de_costo_mensual(eCarrera),2)
        except Exception as ex:
            return 0

    def rmu_por_paralelo_hoja_de_trabajo_balance_costo_mensual(self,eCarrera):
        try:
            total = 0
            total_costo_programa_actividad = self.sumatoria_costos_por_actividad_programas_asociados_y_no_asociados(eCarrera)
            if self.get_cantidad_paralelos_por_carrera(eCarrera) != 0:
                total = Decimal(total_costo_programa_actividad/self.get_cantidad_paralelos_por_carrera(eCarrera))
            return round(total,2)
        except Exception as ex:
            return 0

    def get_total_administrativos_reporte_hoja_de_trabajo(self):
        return GestionIntegrantesPosgradoHojaTrabajo.objects.filter(status=True,gestionposgradohojatrabajo__status=True,gestionposgradohojatrabajo__balancecosto__status=True, gestionposgradohojatrabajo__balancecosto=self).count()

    def get_total_administrativos_reporte_hoja_de_trabajo_por_carrera(self,eCarrera):
        cantidad = GestionIntegrantesActividadCarreraPosgradoHojaTrabajo.objects.filter(status=True,
                                                                             gestionintegrantesposgradohojatrabajo__status=True,
                                                                             gestionintegrantesposgradohojatrabajo__gestionposgradohojatrabajo__status=True,
                                                                             gestionintegrantesposgradohojatrabajo__gestionposgradohojatrabajo__balancecosto__status=True,
                                                                             gestionintegrantesposgradohojatrabajo__gestionposgradohojatrabajo__balancecosto=self,
                                                                             carrera=eCarrera).values_list('gestionintegrantesposgradohojatrabajo_id',flat=True).distinct().count()
        return cantidad

    def get_total_hoja_personal_administrativo_por_el_valor_por_programa(self):
        try:
            total = 0
            carrera_ids = self.balancecostoreportepersonaladministrativo_set.filter(status=True,balancecosto__status=True).values_list('carrera_id',flat=True).order_by('carrera_id').distinct()
            # Agrupar los datos por carrera
            eCarreras = Carrera.objects.filter(status=True, pk__in = carrera_ids)
            for eCarrera in eCarreras:
                total+=self.get_costo_por_maestria_total_hoja_de_trabajo_balance_de_costo_mensual(eCarrera)
            return round(total,2)
        except Exception as ex:
            return 0

    def get_total_costo_por_actividad_carrera_personal_administrativo(self):
        try:
            total = 0
            # Agrupar los datos por carrera
            listCarrerasIds = self.balancecostoreportepersonaladministrativo_set.filter(status=True,balancecosto__status=True).values_list('carrera_id',flat=True).order_by('carrera_id').distinct()
            eCarreras = Carrera.objects.filter(pk__in=listCarrerasIds)
            for eCarrera in eCarreras:
                total+= self.sumatoria_costos_por_actividad_programas_asociados_y_no_asociados(eCarrera)
            return round(total,2)
        except Exception as ex:
            raise  # Re-lanza la misma excepción

    def get_total_rmu_por_paralelo_hoja_personal_administrativo(self):
        try:
            total = 0
            eBalanceCostoReportePersonalAdministrativo = self.get_balancecostoreportepersonaladministrativo()
            for item in eBalanceCostoReportePersonalAdministrativo:
                total+= self.rmu_por_paralelo_hoja_de_trabajo_balance_costo_mensual(item.carrera)
            return round(total,2)
        except Exception as ex:
            return 0

    def get_total_rmu_por_cohorte_hoja_personal_administrativo(self):
        try:
            total = 0
            eBalanceCostoReportePersonalAdministrativo = self.get_balancecostoreportepersonaladministrativo()
            for item in eBalanceCostoReportePersonalAdministrativo:
                total+= round(self.rmu_por_paralelo_hoja_de_trabajo_balance_costo_mensual(item.carrera) * item.totalparalelo, 2)
            return round(total,2)
        except Exception as ex:
            return 0

    def get_cantidad_de_programas_personal_administrativo_balance_de_costo(self):
        try:
            from collections import defaultdict
            eBalanceCostoReportePersonalAdministrativo = self.get_balancecostoreportepersonaladministrativo()
            # Agrupar los datos por carrera
            agrupado_por_carrera = defaultdict(list)
            for item in eBalanceCostoReportePersonalAdministrativo:
                agrupado_por_carrera[item.carrera].append(item)
            return  len(agrupado_por_carrera)
        except Exception as ex:
            return 0

    def get_reporte_personal_administrativo(self):
        try:
            from collections import defaultdict
            eBalanceCostoReportePersonalAdministrativo = self.get_balancecostoreportepersonaladministrativo()
            # Agrupar los datos por carrera
            agrupado_por_carrera = defaultdict(list)
            for item in eBalanceCostoReportePersonalAdministrativo:
                item.rmu_por_cohorte = round(self.rmu_por_paralelo_hoja_de_trabajo_balance_costo_mensual(item.carrera) * item.totalparalelo,2)
                agrupado_por_carrera[item.carrera].append(item)
            # Crear una lista con la información necesaria para el template
            datos_para_template = []
            contador = 0
            division_total_actividades_por_numero_de_programa = self.get_division_total_actividades_balancecosto_hoja_trabajo_cantidad_programa()
            for carrera, items in agrupado_por_carrera.items():
                contador+=1
                rmu_por_paralelo = self.rmu_por_paralelo_hoja_de_trabajo_balance_costo_mensual(carrera)
                total_por_carrera_de_hoja_de_trabajo = self.get_costo_por_maestria_total_hoja_de_trabajo_balance_de_costo_mensual(carrera)
                total_administrativos = self.get_total_administrativos_reporte_hoja_de_trabajo_por_carrera(carrera)
                datos_para_template.append({
                    'contador': contador,
                    'carrera': carrera,
                    'items': items,
                    'division_total_actividades_por_numero_de_programa': division_total_actividades_por_numero_de_programa,
                    'rmu_por_paralelo': rmu_por_paralelo,
                    'total_por_carrera_de_hoja_de_trabajo': total_por_carrera_de_hoja_de_trabajo,
                    'total': self.sumatoria_costos_por_actividad_programas_asociados_y_no_asociados(carrera),
                    'total_administrativos': total_administrativos,
                    'rowspan': len(items),
                })


            return datos_para_template
        except Exception as ex:
            pass

    def get_reporte_costo_variable(self):
        try:
            from collections import defaultdict
            BalanceCostoReporteCostoVariable = self.get_balancecostoreportecostovariable()
            # Agrupar los datos por carrera
            agrupado_por_carrera = defaultdict(list)
            for item in BalanceCostoReporteCostoVariable:
                agrupado_por_carrera[item.carrera].append(item)
            # Crear una lista con la información necesaria para el template
            datos_para_template = []
            contador = 0
            for carrera, items in agrupado_por_carrera.items():
                contador += 1
                datos_para_template.append({
                    'contador': contador,
                    'carrera': carrera,
                    'items': items,
                    'rowspan': len(items),
                })

            return datos_para_template
        except Exception as ex:
            pass

    def get_total_costos_fijos(self):
        try:
            return BalanceCostoCarreraPeriodoParalelo.objects.filter(status=True,balancecostocarreraperiodo__status=True, balancecostocarreraperiodo__balancecostocarrera__status=True, balancecostocarreraperiodo__balancecostocarrera__balancecosto=self).aggregate(total=Sum('costofijo'))['total']
        except Exception as ex:
            return 0

    def get_total_costos_variables(self):
        try:
            return BalanceCostoCarreraPeriodoParalelo.objects.filter(status=True, balancecostocarreraperiodo__status=True, balancecostocarreraperiodo__balancecostocarrera__status=True, balancecostocarreraperiodo__balancecostocarrera__balancecosto=self).aggregate(total=Sum('costovariable'))['total']
        except Exception as ex:
            return 0

    def get_total_ingresos_matricula(self):
        try:
            return BalanceCostoCarreraPeriodoParalelo.objects.filter(status=True, balancecostocarreraperiodo__status=True, balancecostocarreraperiodo__balancecostocarrera__status=True, balancecostocarreraperiodo__balancecostocarrera__balancecosto=self).aggregate(total=Sum('ingresos'))['total']
        except Exception as ex:
            return 0

    def get_total_otros_ingresos(self):
        try:
            return BalanceCostoCarreraPeriodoParalelo.objects.filter(status=True, balancecostocarreraperiodo__status=True, balancecostocarreraperiodo__balancecostocarrera__status=True, balancecostocarreraperiodo__balancecostocarrera__balancecosto=self).aggregate(total=Sum('otrosingresos'))['total']
        except Exception as ex:
            return 0

    def get_total_ingresos(self):
        try:
            return BalanceCostoCarreraPeriodoParalelo.objects.filter(status=True, balancecostocarreraperiodo__status=True, balancecostocarreraperiodo__balancecostocarrera__status=True, balancecostocarreraperiodo__balancecostocarrera__balancecosto=self).aggregate(total=Sum('totalingresos'))['total']
        except Exception as ex:
            return 0

    def get_total_costo_totales(self):
        try:
            total = 0
            eBalanceCostoCarreraPeriodoParalelos =  BalanceCostoCarreraPeriodoParalelo.objects.filter(status=True, balancecostocarreraperiodo__status=True, balancecostocarreraperiodo__balancecostocarrera__status=True, balancecostocarreraperiodo__balancecostocarrera__balancecosto=self)
            for eBalanceCostoCarreraPeriodoParalelo in eBalanceCostoCarreraPeriodoParalelos:
                total += eBalanceCostoCarreraPeriodoParalelo.get_costos_totales()
            return round(total,2)
        except Exception as ex:
            return 0

    def get_ganancias(self):
        try:
            total = 0
            eBalanceCostoCarreraPeriodoParalelos =  BalanceCostoCarreraPeriodoParalelo.objects.filter(status=True, balancecostocarreraperiodo__status=True, balancecostocarreraperiodo__balancecostocarrera__status=True, balancecostocarreraperiodo__balancecostocarrera__balancecosto=self)
            for eBalanceCostoCarreraPeriodoParalelo in eBalanceCostoCarreraPeriodoParalelos:
                total += eBalanceCostoCarreraPeriodoParalelo.get_total()
            return round(total,2)
        except Exception as ex:
            return 0

    def get_reporte_mensual(self):
        try:
            from collections import defaultdict
            # Obtener todas las carreras con sus periodos y paralelos
            balance_costo_carreras = BalanceCostoCarrera.objects.filter(balancecosto=self).select_related('carrera')
            balance_costo_carrera_periodos = BalanceCostoCarreraPeriodo.objects.filter(balancecostocarrera__in=balance_costo_carreras).select_related('balancecostocarrera', 'periodo')
            balance_costo_carrera_periodo_paralelos = BalanceCostoCarreraPeriodoParalelo.objects.filter(balancecostocarreraperiodo__in=balance_costo_carrera_periodos).select_related('balancecostocarreraperiodo')

            # Agrupar los datos por carrera
            agrupado_por_carrera = defaultdict(list)
            for paralelo in balance_costo_carrera_periodo_paralelos:
                carrera = paralelo.balancecostocarreraperiodo.balancecostocarrera.carrera
                periodo = paralelo.balancecostocarreraperiodo.periodo
                agrupado_por_carrera[carrera].append({
                    'periodo': periodo,
                    'paralelo': paralelo
                })

            # Crear una lista con la información necesaria para el template
            datos_para_template = []
            contador = 0
            for carrera, items in agrupado_por_carrera.items():
                contador += 1
                datos_para_template.append({
                    'contador': contador,
                    'carrera': carrera,
                    'items': items,
                    'rowspan': len(items),
                })

            return datos_para_template
        except Exception as ex:
            pass

    def get_total_a_certificar_profesor_modulo(self):
        total = BalanceCostoCarreraPeriodo.objects.filter(
            status=True,
            balancecostocarrera__balancecosto=self
        ).aggregate(
            total_modular=Sum(
                F('cantidad_modulos_mult_pmodular') * F('subtotal_certificar_pmodular')
            )
        )['total_modular']

        return round(total or 0, 2)

    def get_reporte_profesor_modular(self):
        try:
            from collections import defaultdict
            eBalanceCostoReporteProfesorModular = self.get_balancecostoreporteprofesormodulo()
            # Agrupar los datos por carrera
            agrupado_por_carrera = defaultdict(lambda: defaultdict(list))
            for item in eBalanceCostoReporteProfesorModular:
                item.cantidad_modulo_por_horas = item.get_total_horas()
                item.subtotal_certificar = item.get_sub_total_certificar()
                agrupado_por_carrera[item.carrera][item.periodo].append(item)
            # Crear una lista con la información necesaria para el template
            datos_para_template = []
            contador_carrera = 0
            for carrera, periodos in agrupado_por_carrera.items():
                contador_carrera += 1
                items_por_carrera = []
                for periodo, items in periodos.items():
                    items_por_carrera.extend(items)
                    datos_para_template.append({
                        'contador': contador_carrera,
                        'carrera': carrera,
                        'periodo': periodo,
                        'multiplicador': self.get_multiplicador(carrera.pk,periodo.pk),
                        'totcertificar': self.get_tot_certificar(carrera.pk,periodo.pk),
                        'pk_carrera_periodo_del_balance_de_costo': self.get_id_periodo_carrera_balance_costo(carrera.pk,periodo.pk),
                        'items': items,
                        'rowspan': len(items)
                    })
                # Agregar los items de cada carrera a la lista general
                datos_para_template.extend(items_por_carrera)

            return datos_para_template
        except Exception as ex:
            pass

    def get_total_paralelos_profesor_invitado(self):
        try:
            from collections import defaultdict
            cantidad = 0
            eBalanceCostoReporteProfesorModular = self.get_balancecostoreporteprofesormoduloinvitado()
            agrupado_por_carrera = defaultdict(list)
            for item in eBalanceCostoReporteProfesorModular:
                agrupado_por_carrera[item.carrera].append(item)
            for carrera, items in agrupado_por_carrera.items():
                cantidad += self.get_cantidad_paralelos_por_carrera(carrera)
            return cantidad
        except Exception as ex:
            return 0

    def get_total_paralelos_pestana_costo_variable(self):
        try:
            from collections import defaultdict
            cantidad = 0
            eBalanceCostoReporteCostoVariable = self.get_balancecostoreportecostovariable()
            agrupado_por_carrera = defaultdict(list)
            for item in eBalanceCostoReporteCostoVariable:
                agrupado_por_carrera[item.carrera].append(item)
            for carrera, items in agrupado_por_carrera.items():
                cantidad += self.get_cantidad_paralelos_por_carrera(carrera)
            return cantidad
        except Exception as ex:
            return 0

    def get_total_rmu_por_maestria_profesor_invitado(self,eCarrera):
        try:
            rmu_por_cohorte =0
            eBalanceCostoReporteProfesorModular = self.get_balancecostoreporteprofesormoduloinvitado().filter(carrera=eCarrera)
            # Agrupar los datos por carrera
            rmu_por_paralelo = (self.get_total_tiempo_completo() + self.get_total_medio_tiempo()) / self.get_total_paralelos_profesor_invitado()
            for item in eBalanceCostoReporteProfesorModular:
                rmu_por_cohorte += round(Decimal(rmu_por_paralelo * item.totalparalelo), 2)
            return round(Decimal(rmu_por_cohorte),2)
        except Exception as ex:
            return 0

    def get_reporte_profesor_modular_invitado(self):
        try:
            from collections import defaultdict
            eBalanceCostoReporteProfesorModular = self.get_balancecostoreporteprofesormoduloinvitado()
            # Agrupar los datos por carrera
            rmu_por_paralelo = ( self.get_total_tiempo_completo() + self.get_total_medio_tiempo()) / self.get_total_paralelos_profesor_invitado()
            agrupado_por_carrera = defaultdict(list)
            for item in eBalanceCostoReporteProfesorModular:
                item.rmu_por_cohorte = round(Decimal(rmu_por_paralelo *  item.totalparalelo),2)
                agrupado_por_carrera[item.carrera].append(item)
            # Crear una lista con la información necesaria para el template
            datos_para_template = []
            contador = 0
            for carrera, items in agrupado_por_carrera.items():
                cantidad_medio_tiempo_tiempo_completo = self.get_cantidad_medio_tiempo() + self.get_cantidad_tiempo_completo()
                total_medio_tiempo_tiempo_completo = self.get_total_tiempo_completo()+self.get_total_medio_tiempo()
                total_rmu_por_maestria = self.get_total_rmu_por_maestria_profesor_invitado(carrera)
                contador += 1
                datos_para_template.append({
                    'contador': contador,
                    'carrera': carrera,
                    'cantidad_medio_tiempo_tiempo_completo': cantidad_medio_tiempo_tiempo_completo,
                    'total_medio_tiempo_tiempo_completo': total_medio_tiempo_tiempo_completo,
                    'rmu_por_paralelo' : round(rmu_por_paralelo,2),
                    'total_rmu_por_maestria' : total_rmu_por_maestria,
                    'items': items,
                    'rowspan': len(items),
                })

            return datos_para_template
        except Exception as ex:
            pass

    def get_maestrias_admision_vigentes(self):
        maestriaadmision_id = CohorteMaestria.objects.filter(periodoacademico__tipo_id=3, status=True).values_list('maestriaadmision_id', flat=True)
        eMaestriasAdmisions = MaestriasAdmision.objects.filter(status=True, id__in=maestriaadmision_id).order_by('id')
        return eMaestriasAdmisions

    def obtener_total_paralelos(self,periodoacademico, eMallas, mes, anio):
        from django.db.models.functions import ExtractMonth, ExtractYear
        cantidad = 0
        eNivel = Nivel.objects.filter(periodo_id=periodoacademico.pk, status=True).first()
        if eNivel:
            if mes == 0 or anio == 0:
                paralelos = eNivel.materia_set.values_list('paralelo', flat=True).filter(status=True,asignaturamalla__malla__in=eMallas.values_list('id',flat=True)).distinct()
            else:
                paralelos = eNivel.materia_set.filter(status=True,asignaturamalla__malla_id__in=eMallas.values_list('id',flat=True)).annotate(
                    inicio_mes=ExtractMonth('inicio'),
                    inicio_anio=ExtractYear('inicio'),
                    fin_mes=ExtractMonth('fin'),
                    fin_anio=ExtractYear('fin')
                ).filter(
                    inicio_mes=mes,
                    inicio_anio=anio
                ).values_list('paralelo', flat=True)

            eParalelos = Paralelo.objects.filter(nombre__in=paralelos, status=True)
            cantidad = eParalelos.count()
        return cantidad

    def obtener_rmu_coordinador_programa(self,eCarrera):
        from pdip.models import ContratoDip,ContratoCarrera
        from sga.models import CoordinadorCarrera
        from calendar import monthrange
        anio = int(self.anio)
        mes = int(self.mes)
        rmu = 0
        fecha_entrada = date(anio, mes, 1)
        ultimo_dia_mes = monthrange(anio, mes)[1]
        fecha_fin = date(anio, mes, ultimo_dia_mes)
        eeCoordinadorCarrera = CoordinadorCarrera.objects.filter(carrera=eCarrera, periodo__activo=True)
        if eeCoordinadorCarrera:
            eCoordinador = eeCoordinadorCarrera[0].persona
            contrato_id = ContratoCarrera.objects.filter(status=True, carrera=eCarrera).values_list('contrato_id', flat=True)
            eContratoDip = ContratoDip.objects.filter(status=True, pk__in=contrato_id, estado=2, cargo__nombre__icontains='COORDINADOR').order_by('-id')
            if not eContratoDip:
                eContratoDip = ContratoDip.objects.filter(
                    status=True,
                    pk__in=contrato_id,
                    cargo__nombre__icontains='COORDINADOR',
                    fechainicio__year=anio,
                    fechafin__lte=fecha_fin
                ).order_by('-id')

            eContrato = eContratoDip.first()
            if eContrato:
                rmu = eContrato.valortotal

        return rmu

    def get_estructura_balance_costo(self):
        try:
            eBalanceCostoCarreraPeriodoParalelos = BalanceCostoCarreraPeriodoParalelo.objects.filter(status=True,balancecostocarreraperiodo__status=True, balancecostocarreraperiodo__balancecostocarrera__status=True, balancecostocarreraperiodo__balancecostocarrera__balancecosto=self)
            return eBalanceCostoCarreraPeriodoParalelos
        except Exception as ex:
            pass

    def duplicar_estructura_general_hoja_de_trabajo_en_balance_costo_mensual(self,request):
        try:
            eGestionPosgrados = GestionPosgrado.objects.filter(status=True)
            for eGestionPosgrado in eGestionPosgrados:
                eGestionPosgradoHojaTrabajo = GestionPosgradoHojaTrabajo(
                    balancecosto = self,
                    descripcion =eGestionPosgrado.descripcion
                )
                eGestionPosgradoHojaTrabajo.save(request)

                for integrante in eGestionPosgrado.get_integrantes():
                    eGestionIntegrantesPosgradoHojaTrabajo = GestionIntegrantesPosgradoHojaTrabajo(
                        gestionposgradohojatrabajo = eGestionPosgradoHojaTrabajo,
                        persona = integrante.persona,
                        rmu = integrante.rmu
                    )
                    eGestionIntegrantesPosgradoHojaTrabajo.save(request)
                    for actividad in integrante.get_actividades():
                        eGestionIntegrantesActividadCarreraPosgradoHojaTrabajo = GestionIntegrantesActividadCarreraPosgradoHojaTrabajo(
                            gestionintegrantesposgradohojatrabajo = eGestionIntegrantesPosgradoHojaTrabajo,
                            carrera = actividad.carrera,
                            actividadpersonalposgrado =actividad.actividadpersonalposgrado,
                            hora_de_trabajo = actividad.hora_de_trabajo
                        )
                        eGestionIntegrantesActividadCarreraPosgradoHojaTrabajo.save(request)
        except Exception as ex:
            messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')

    def get_numeros_de_modulos_a_dictar_conforme_a_la_malla(self,periodoacademico, eMallas, mes, anio):
        from django.db.models.functions import ExtractMonth, ExtractYear
        cantidad = 0
        eNivel = Nivel.objects.filter(periodo_id=periodoacademico.pk, status=True).first()
        if eNivel:
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
            eAsignaturaMalla = AsignaturaMalla.objects.filter(pk__in=asignaturamalla_id)
            cantidad = eAsignaturaMalla.count()
        return cantidad

    def persona_a_contratar_de_informe_contratacion(self,periodoacademico,eAsignaturaMalla):
        from postulaciondip.models import DetalleInformeContratacion
        return DetalleInformeContratacion.objects.filter(personalcontratar__actaparalelo__status=True,personalcontratar__actaparalelo__convocatoria__status=True, personalcontratar__status=True,status=True, personalcontratar__actaparalelo__convocatoria__asignaturamalla__id=eAsignaturaMalla.pk,personalcontratar__actaparalelo__convocatoria__periodo=periodoacademico)

    def get_desgloce_de_los_modulos_a_dictar(self,periodoacademico,eMallas):
        from django.db.models.functions import ExtractMonth, ExtractYear
        from postulaciondip.models import DetalleInformeContratacion
        eMaterias = None
        eNivel = Nivel.objects.filter(periodo_id=periodoacademico.pk, status=True).first()
        if eNivel:
            eMaterias = eNivel.materia_set.filter(status=True, asignaturamalla__malla_id__in=eMallas.values_list('id', flat=True)).annotate(
                inicio_mes=ExtractMonth('inicio'),
                inicio_anio=ExtractYear('inicio'),
                fin_mes=ExtractMonth('fin'),
                fin_anio=ExtractYear('fin')
            ).filter(
                inicio_mes=self.mes,
                inicio_anio=self.anio
            )

            asignaturamalla_id = eMaterias.distinct().values_list('asignaturamalla_id', flat=True)
            eAsignaturaMallas = AsignaturaMalla.objects.filter(pk__in=asignaturamalla_id)
            detalleseAsignaturaMallas = list(map(lambda eAsignaturaMalla: {
                'eAsignaturaMallaPk': eAsignaturaMalla.pk,
                'valor_x_hora':   Decimal(str(self.persona_a_contratar_de_informe_contratacion(periodoacademico,eAsignaturaMalla).first().valor_x_hora))  if self.persona_a_contratar_de_informe_contratacion(periodoacademico,eAsignaturaMalla) else 0,
                'horasacdtotal': (eAsignaturaMalla.horasacdtotal),
            }, eAsignaturaMallas))

            return detalleseAsignaturaMallas

    def get_desgloce_de_los_modulos_a_dictar_agrupados(self,detalleseAsignaturaMallas):
        from collections import defaultdict
        # Diccionario para almacenar el conteo de módulos según horas y valor por hora
        contador_modulos = defaultdict(int)
        if detalleseAsignaturaMallas:
            for modulo in detalleseAsignaturaMallas:
                key = (modulo['horasacdtotal'], modulo['valor_x_hora'])
                contador_modulos[key] += 1
        return contador_modulos

    def get_balancecostoreportecoordinador(self):
        return self.balancecostoreportecoordinador_set.filter(status=True,balancecosto__status=True)

    def get_balancecostoreportecoordinadorapoyo(self):
        return self.balancecostoreportecoordinadorapoyo_set.filter(status=True,balancecosto__status=True)

    def get_balancecostoreportepersonaladministrativo(self):
        return self.balancecostoreportepersonaladministrativo_set.filter(status=True,balancecosto__status=True)

    def get_balancecostoreporteprofesormodulo(self):
        return self.balancecostoreporteprofesormodulo_set.filter(status=True,balancecosto__status=True)

    def get_balancecostoreporteprofesormoduloinvitado(self):
        return self.balancecostoreporteprofesormoduloinvitado_set.filter(status=True,balancecosto__status=True)

    def get_balancecostoreportecostovariable(self):
        return self.balancecostoreportecostovariable_set.filter(status=True,balancecosto__status=True)

    def get_coordindadores_repetidos_por_programa(self):
        eBalanceCostoCarreras = BalanceCostoCarrera.objects.filter(status=True,balancecosto =self)
        coordinador_dict = {}
        for eBalanceCostoCarrera in eBalanceCostoCarreras:
            ePersona = self.get_contrato_coordinador_carrera(eBalanceCostoCarrera.carrera).persona if self.get_contrato_coordinador_carrera(eBalanceCostoCarrera.carrera) else None
            if ePersona:
                if ePersona.id not in coordinador_dict:
                    coordinador_dict[ePersona.id] = []
                coordinador_dict[ePersona.id].append(eBalanceCostoCarrera.carrera.id)
        coordinadores_repetidos = {key: value for key, value in coordinador_dict.items() if len(value) > 1}

        return coordinadores_repetidos

    def get_total_paralelos_por_carreras_agrupadas_por_division_de_menciones(self):
        persona_coordinador_carreras = self.get_coordindadores_repetidos_por_programa()
        detailed_results = {}
        paralelos= 0
        for persona_id, carrera_ids in persona_coordinador_carreras.items():
            total_paralelos = 0
            carrera_paralelos = {}
            for carrera_id in carrera_ids:
                # Step 4: Get the total paralelos for each carrera
                paralelos = self.get_cantidad_paralelos_por_carrera(carrera_id)
                carrera_paralelos[carrera_id] = paralelos
                total_paralelos += paralelos

            detailed_results[persona_id] = {
                "carreras": carrera_ids,
                "total_paralelos": total_paralelos,
                "paralelos_por_carrera": carrera_paralelos
            }

        return detailed_results

    def get_total_personal_administrativo(self):
        return GestionIntegrantesPosgradoHojaTrabajo.objects.values_list('persona_id',flat=True).filter(status=True,gestionposgradohojatrabajo__balancecosto = self).count()

    def get_id_periodo_carrera_balance_costo(self,carrera_id,periodo_id):
        return BalanceCostoCarreraPeriodo.objects.filter(status=True,balancecostocarrera__carrera_id = carrera_id,periodo_id = periodo_id, balancecostocarrera__balancecosto = self).values_list('id',flat=True).first()

    def get_multiplicador(self,carrera_id,periodo_id):
        return BalanceCostoCarreraPeriodo.objects.filter(status=True,balancecostocarrera__carrera_id = carrera_id,periodo_id = periodo_id, balancecostocarrera__balancecosto = self).values_list('cantidad_modulos_mult_pmodular',flat=True).first()

    def get_tot_certificar(self,carrera_id,periodo_id):
        total = BalanceCostoCarreraPeriodo.objects.filter(
            status=True,
            balancecostocarrera__balancecosto=self,
            balancecostocarrera__carrera_id=carrera_id, periodo_id=periodo_id,
        ).aggregate(
            total_modular=Sum(
                F('cantidad_modulos_mult_pmodular') * F('subtotal_certificar_pmodular')
            )
        )['total_modular']

        return round(total or 0, 2)

    def existe_otro_balance_de_costo_validado_en_el_mismo_mes_and_anio(self):
        return BalanceCosto.objects.filter(status=True,anio = self.anio,mes = self.mes,estado=1).exclude(pk=self.pk).exists()

class BalanceCostoCarrera(ModeloBase):
    balancecosto = models.ForeignKey(BalanceCosto, verbose_name=u'Balance costo', on_delete=models.CASCADE)
    carrera = models.ForeignKey('sga.Carrera', verbose_name=u'Carrera', on_delete=models.CASCADE)
    total_distribucion = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"distribucion total por carrera coordinador de apoyo")

    def __str__(self):
        return f'[{self.pk}]{self.balancecosto} - {self.carrera}'

    def save_periodo(self,request,periodo):
        eBalanceCostoCarreraPeriodo = BalanceCostoCarreraPeriodo(
            balancecostocarrera = self,
            periodo = periodo
        )
        eBalanceCostoCarreraPeriodo.save(request)
        log(u'Agregó carrera balance costo: %s' % eBalanceCostoCarreraPeriodo, request, "add")
        return eBalanceCostoCarreraPeriodo

    class Meta:
        verbose_name = u"Balance de costo carrera"
        verbose_name_plural = u"Balance de costos carreras"
        ordering = ['id']

class BalanceCostoCarreraPeriodo(ModeloBase):
    balancecostocarrera = models.ForeignKey(BalanceCostoCarrera, verbose_name=u'Balance Costo Carrera Periodo', on_delete=models.CASCADE)
    periodo = models.ForeignKey('sga.Periodo', verbose_name=u'Periodo', on_delete=models.CASCADE)
    cantidad_modulos_mult_pmodular = models.DecimalField(max_digits=30, decimal_places=4, default=1, verbose_name=u"Cantidad de modulos a multiplicar de modulos a dictar profesor modular")
    subtotal_certificar_pmodular = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"subTotal certificar profesor modular por periodode carrera")

    def __str__(self):
        return f'[{self.pk}]-{self.balancecostocarrera} - {self.periodo}'

    def save_totalparalelos(self,request,totalparalelo):
        eBalanceCostoCarreraPeriodoParalelo = BalanceCostoCarreraPeriodoParalelo(
            balancecostocarreraperiodo = self,
            totalparalelo = totalparalelo
        )
        eBalanceCostoCarreraPeriodoParalelo.save(request)
        log(u'Agregó periodos balance costo: %s' % eBalanceCostoCarreraPeriodoParalelo, request, "add")

    class Meta:
        verbose_name = u"Balance de costo periodo"
        verbose_name_plural = u"Balance de costos periodos"
        ordering = ['id']

class BalanceCostoCarreraPeriodoParalelo(ModeloBase):
    balancecostocarreraperiodo = models.ForeignKey(BalanceCostoCarreraPeriodo, verbose_name=u'BalanceCostoCarreraPeriodo', on_delete=models.CASCADE)
    totalparalelo = models.IntegerField(default=0, verbose_name=u'Total paralelos')
    costofijo = models.DecimalField(max_digits=30, decimal_places=2, default=0,verbose_name=u"costos fijos")
    costovariable = models.DecimalField(max_digits=30, decimal_places=2, default=0,verbose_name=u"costos fijos")
    ingresos = models.DecimalField(max_digits=30, decimal_places=2, default=0,verbose_name=u"ingresos matricula")
    otrosingresos = models.DecimalField(max_digits=30, decimal_places=2, default=0,verbose_name=u"otros ingresos")
    totalingresos = models.DecimalField(max_digits=30, decimal_places=2, default=0,verbose_name=u"total ingresos")

    def __str__(self):
        return f'[{self.pk}]-{self.balancecostocarreraperiodo} - {self.totalparalelo}'

    def get_costos_totales(self):
        return round(self.costofijo + self.costovariable,2)

    def get_total(self):
        return round(self.totalingresos - self.get_costos_totales(),2)

    def save_costosfijo(self, request,eCosto):
        self.costofijo = self.costofijo + eCosto
        self.save(request)

    def save_costosvariable(self, request,eCostoVariable):
        self.costovariable = self.costovariable + eCostoVariable
        self.save(request)

    def reiniciar_costos_fijos(self, request):
        self.costofijo = 0
        self.save(request)

    def reiniciarcostosvariables(self, request):
        self.costovariable = 0
        self.save(request)

    def save_ingresos_matricula(self, request,eIngreso):
        try:
            self.ingresos = eIngreso
            self.save(request)
            return self.ingresos
        except Exception as ex:
            messages.error(request, f'Ocurrió un error al guardar ingresos matricula: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
            raise

    def save_otros_ingresos(self, request,otroingresos):
        try:
            self.otrosingresos = otroingresos
            self.save(request)
            return self.otrosingresos
        except Exception as ex:
            messages.error(request, f'Ocurrió un error al guardar otros ingresos: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
            raise

    def save_total_ingresos(self, request,totalingresos):
        try:
            self.totalingresos = totalingresos
            self.save(request)
        except Exception as ex:
            messages.error(request, f'Ocurrió un error al guardar total ingresos: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
            raise


    class Meta:
        verbose_name = u"Balance de costo paralelos del periodo"
        verbose_name_plural = u"Balance de costos paralelos de los periodos"
        ordering = ['id']

class BalanceCostoReporteCoordinador(ModeloBase):
    balancecosto = models.ForeignKey(BalanceCosto, verbose_name=u'Balance costo', on_delete=models.CASCADE)
    carrera = models.ForeignKey('sga.Carrera', verbose_name=u'Carrera', on_delete=models.CASCADE)
    periodo = models.ForeignKey('sga.Periodo', verbose_name=u'Periodo', on_delete=models.CASCADE)
    totalparalelo = models.IntegerField(default=0,verbose_name=u'Total paralelos')
    rmu = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"Rmu coordinador")

    def __str__(self):
        return f'Coordinador: {self.balancecosto} - {self.carrera} - {self.periodo}'

    class Meta:
        verbose_name = u"Balance de costo Reporte Coordinador"
        verbose_name_plural = u"Balance de costos Reporte coordinadores"
        ordering = ['id']

class BalanceCostoReporteCoordinadorApoyo(ModeloBase):
    balancecosto = models.ForeignKey(BalanceCosto, verbose_name=u'Balance costo', on_delete=models.CASCADE)
    carrera = models.ForeignKey('sga.Carrera', verbose_name=u'Carrera', on_delete=models.CASCADE)
    periodo = models.ForeignKey('sga.Periodo', verbose_name=u'Periodo', on_delete=models.CASCADE)
    totalparalelo = models.IntegerField(default=0,verbose_name=u'Total paralelos')
    cantidad_coordinadorapoyo = models.IntegerField(default=0,verbose_name=u'cantidad coordinador apoyo')
    numero_de_hora = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"numero_hora")
    distribucion = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"distribucion por cohorte")

    def __str__(self):
        return f'Coordinador apoyo: {self.balancecosto} - {self.carrera}'

    class Meta:
        verbose_name = u"Balance de costo Reporte Coordinador apoyo"
        verbose_name_plural = u"Balance de costos Reporte coordinadores apoyos"
        ordering = ['id']

class BalanceCostoReporteProfesorModulo(ModeloBase):
    balancecosto = models.ForeignKey(BalanceCosto, verbose_name=u'Balance costo', on_delete=models.CASCADE)
    carrera = models.ForeignKey('sga.Carrera', verbose_name=u'Carrera', on_delete=models.CASCADE)
    periodo = models.ForeignKey('sga.Periodo', verbose_name=u'Periodo', on_delete=models.CASCADE)
    totalparalelo = models.IntegerField(default=0,verbose_name=u'Total paralelos')
    cantidad_modulo_dictar = models.IntegerField(default=0,verbose_name=u'cantidad modulos a dictar')
    desgloce_cantidad_modulo = models.IntegerField(default=0,verbose_name=u'cantidad modulos desgloce')
    numero_de_hora_por_modulo = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"numero_hora")
    valor_por_hora = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"valor por hora")

    def get_total_horas(self):
        return round(self.desgloce_cantidad_modulo * self.numero_de_hora_por_modulo, 2)

    def get_sub_total_certificar(self):
        return round(self.get_total_horas() * self.valor_por_hora, 2)

    def get_total_certificar(self):
        total = 0
        total = BalanceCostoReporteProfesorModulo.objects.filter(
            status=True,
            balancecosto=self.balancecosto,
            carrera=self.carrera,
            periodo=self.periodo
        ).aggregate(
            total_certificar=Sum(
                F('desgloce_cantidad_modulo') * F('numero_de_hora_por_modulo') * F('valor_por_hora')
            )
        )['total_certificar']

        return round(total or 0, 2)

    def es_profesor_invitado(self):
        return True if self.valor_por_hora == 0 and self.totalparalelo!=0 and self.cantidad_modulo_dictar !=0 else False

    def __str__(self):
        return f'Profesor Módulo: {self.balancecosto} - {self.carrera} - {self.periodo}'

    class Meta:
        verbose_name = u"Balance de costo Reporte Profesor Módulo"
        verbose_name_plural = u"Balance de costos Reporte Profesor Módulos"
        ordering = ['id']

class BalanceCostoReporteProfesorModuloInvitado(ModeloBase):
    balancecosto = models.ForeignKey(BalanceCosto, verbose_name=u'Balance costo', on_delete=models.CASCADE)
    carrera = models.ForeignKey('sga.Carrera', verbose_name=u'Carrera', on_delete=models.CASCADE)
    periodo = models.ForeignKey('sga.Periodo', verbose_name=u'Periodo', on_delete=models.CASCADE)
    totalparalelo = models.IntegerField(default=0,verbose_name=u'Total paralelos')

    def __str__(self):
        return f'Profesor Módulo invitado: {self.balancecosto} - {self.carrera} - {self.periodo}'

    class Meta:
        verbose_name = u"Balance de costo Reporte Profesor Módulo invitado"
        verbose_name_plural = u"Balance de costos Reporte Profesor Módulos invitado"
        ordering = ['id']

class ActividadPersonalPosgrado(ModeloBase):
    descripcion = models.CharField(default='', max_length=200, verbose_name=u"Descripcion")

    def __str__(self):
        return f' {self.descripcion}'

    class Meta:
        verbose_name = u"ActividadesPersonalPosgrado"
        verbose_name_plural = u"ActividadesPersonalPosgrado"
        ordering = ['id']

class GestionPosgrado(ModeloBase):
    descripcion = models.CharField(default='', max_length=200, verbose_name=u"Descripcion")

    def get_integrantes(self):
        return self.gestionintegrantesposgrado_set.filter(status=True)

    def __str__(self):
        return f' {self.descripcion}'

    def en_uso(self):
        return self.gestionintegrantesposgrado_set.filter(status=True).exists()


    def get_costo_por_maestria_total_hoja_de_trabajo(self,eGestionIntegrantesActividadCarreraPosgrados,eCarrera):
        eActividades = eGestionIntegrantesActividadCarreraPosgrados.filter(carrera=eCarrera)
        total = 0
        for eActividad in eActividades:
            total += eActividad.get_mensual()
        return total

    def get_resumen_carrera_hoja_trabajo(self):
        eGestionIntegrantesActividadCarreraPosgrados = GestionIntegrantesActividadCarreraPosgrado.objects.filter(status=True,gestionintegrantesposgrado__status=True, gestionintegrantesposgrado__gestionposgrado__status=True).distinct()
        carrera_id = eGestionIntegrantesActividadCarreraPosgrados.values_list('carrera_id', flat=True).distinct()
        eCarreras = Carrera.objects.filter(pk__in=carrera_id)

        listado = list(map( lambda eCarrera: {
            'eCarrera':eCarrera,
            'total': self.get_costo_por_maestria_total_hoja_de_trabajo(eGestionIntegrantesActividadCarreraPosgrados,eCarrera),
        },eCarreras))

        return listado

    def get_total_por_todas_lasactividad_hoja_trabajo(self):
        eActividades  = GestionIntegrantesActividadCarreraPosgrado.objects.filter(status=True,gestionintegrantesposgrado__status=True, gestionintegrantesposgrado__gestionposgrado__status=True, carrera__isnull=True).distinct()
        total = 0
        for eActividad in eActividades:
            total += eActividad.get_mensual()
        return total


    class Meta:
        verbose_name = u"Gestion Posgrado"
        verbose_name_plural = u"Gestion Posgrado"
        ordering = ['id']

class GestionIntegrantesPosgrado(ModeloBase):
    gestionposgrado = models.ForeignKey(GestionPosgrado, verbose_name=u'Persona', on_delete=models.CASCADE)
    persona = models.ForeignKey('sga.Persona', verbose_name=u'Persona', on_delete=models.CASCADE)
    rmu = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"Rmu coordinador")

    def __str__(self):
        return f' {self.persona}'

    def en_uso(self):
        return self.gestionintegrantesactividadcarreraposgrado_set.filter(status=True).exists()

    def get_costo_por_hora(self):
        rmu_total = self.rmu
        valorpordia = rmu_total / 30
        valorporhora = valorpordia / 8 #horas
        return valorporhora

    def get_actividades(self):
        return self.gestionintegrantesactividadcarreraposgrado_set.filter(status=True)

    def get_total_horas_de_trabajo(self):
        return self.gestionintegrantesactividadcarreraposgrado_set.filter(status=True).aggregate(total=Sum('hora_de_trabajo'))['total']

    def get_total_costo_diario(self):
        total = 0
        for actividad in self.get_actividades():
            total += actividad.get_diario()
        return total

    def get_total_costo_mensual(self):
        total = 0
        total = round(self.get_total_costo_diario() * 30)
        return total

    class Meta:
        verbose_name = u"GestionIntegrantesPosgrado"
        verbose_name_plural = u"GestionIntegrantesPosgrado"
        ordering = ['id']

class GestionIntegrantesActividadCarreraPosgrado(ModeloBase):
    gestionintegrantesposgrado = models.ForeignKey(GestionIntegrantesPosgrado, verbose_name=u'Persona', on_delete=models.CASCADE)
    carrera = models.ForeignKey('sga.Carrera', null=True, blank=True, verbose_name=u'Carrera', on_delete=models.CASCADE)
    actividadpersonalposgrado = models.ForeignKey(ActividadPersonalPosgrado, null=True, blank=True, verbose_name=u'actividad', on_delete=models.CASCADE)
    hora_de_trabajo= models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"horas de trabajos")

    def __str__(self):
        return f' {self.get_actividad()}'

    def get_actividad(self):
        return self.carrera if self.carrera else self.actividadpersonalposgrado

    def get_diario(self):
        costo_por_hora = self.gestionintegrantesposgrado.get_costo_por_hora()
        return costo_por_hora * self.hora_de_trabajo

    def get_mensual(self):
        return round(self.get_diario() * 30)

    class Meta:
        verbose_name = u"GestionIntegrantesActividadCarreraPosgrado"
        verbose_name_plural = u"GestionIntegrantesActividadCarreraPosgrado"
        ordering = ['id']

class BalanceCostoReporteCostoVariable(ModeloBase):
    balancecosto = models.ForeignKey(BalanceCosto, verbose_name=u'Balance costo', on_delete=models.CASCADE)
    carrera = models.ForeignKey('sga.Carrera', verbose_name=u'Carrera', on_delete=models.CASCADE)
    periodo = models.ForeignKey('sga.Periodo', verbose_name=u'Periodo', on_delete=models.CASCADE)
    totalparalelo = models.IntegerField(default=0,verbose_name=u'Total paralelos')
    costos_por_publicidad = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"costo por publicidad")
    eventos_promocionales = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"eventos promocionales")
    materiales_de_oficina = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"materiales de oficina")

    def __str__(self):
        return f'Costos variables: {self.balancecosto} - {self.carrera} - {self.periodo}'

    def get_total(self):
        return round(self.costos_por_publicidad +  self.eventos_promocionales + self.materiales_de_oficina,2)

    class Meta:
        verbose_name = u"Balance de costo Reporte costo variable"
        verbose_name_plural = u"Balance de costos Reporte costos variables"
        ordering = ['id']

class BalanceCostoReportePersonalAdministrativo(ModeloBase):
    balancecosto = models.ForeignKey(BalanceCosto, verbose_name=u'Balance costo', on_delete=models.CASCADE)
    carrera = models.ForeignKey('sga.Carrera', verbose_name=u'Carrera', on_delete=models.CASCADE)
    periodo = models.ForeignKey('sga.Periodo', verbose_name=u'Periodo', on_delete=models.CASCADE)
    totalparalelo = models.IntegerField(default=0,verbose_name=u'Total paralelos')

    def __str__(self):
        return f'Profesor Módulo invitado: {self.balancecosto} - {self.carrera} - {self.periodo}'

    class Meta:
        verbose_name = u"Balance de costo Reporte Profesor Módulo invitado"
        verbose_name_plural = u"Balance de costos Reporte Profesor Módulos invitado"
        ordering = ['id']

class GestionPosgradoHojaTrabajo(ModeloBase):
    balancecosto = models.ForeignKey(BalanceCosto, verbose_name=u'balancecosto', on_delete=models.CASCADE)
    descripcion = models.CharField(default='', max_length=200, verbose_name=u"Descripcion")

    def get_integrantes(self):
        return self.gestionintegrantesposgradohojatrabajo_set.filter(status=True)

    def __str__(self):
        return f' {self.descripcion}'

    def en_uso(self):
        return self.gestionintegrantesposgradohojatrabajo_set.filter(status=True).exists()


    def get_costo_por_maestria_total_hoja_de_trabajo(self,eGestionIntegrantesActividadCarreraPosgradoHojaTrabajos,eCarrera):
        eActividades = eGestionIntegrantesActividadCarreraPosgradoHojaTrabajos.filter(carrera=eCarrera)
        total = 0
        for eActividad in eActividades:
            total += eActividad.get_mensual()
        return total

    def get_resumen_carrera_hoja_trabajo(self):
        eGestionIntegrantesActividadCarreraPosgradoHojaTrabajos = GestionIntegrantesActividadCarreraPosgradoHojaTrabajo.objects.filter(status=True,gestionintegrantesposgradohojatrabajo__status=True, gestionintegrantesposgradohojatrabajo__gestionposgradohojatrabajo__status=True,gestionintegrantesposgradohojatrabajo__gestionposgradohojatrabajo__balancecosto =self.balancecosto).distinct()
        carrera_id = eGestionIntegrantesActividadCarreraPosgradoHojaTrabajos.values_list('carrera_id', flat=True).distinct()
        eCarreras = Carrera.objects.filter(pk__in=carrera_id)

        listado = list(map( lambda eCarrera: {
            'eCarrera':eCarrera,
            'total': self.get_costo_por_maestria_total_hoja_de_trabajo(eGestionIntegrantesActividadCarreraPosgradoHojaTrabajos,eCarrera),
        },eCarreras))

        return listado

    def get_total_por_todas_lasactividad_hoja_trabajo(self):
        eActividades  = GestionIntegrantesActividadCarreraPosgradoHojaTrabajo.objects.filter(status=True,gestionintegrantesposgradohojatrabajo__status=True, gestionintegrantesposgradohojatrabajo__gestionposgradohojatrabajo__status=True, carrera__isnull=True, gestionintegrantesposgradohojatrabajo__gestionposgradohojatrabajo__balancecosto =self.balancecosto).distinct()
        total = 0
        for eActividad in eActividades:
            total += eActividad.get_mensual()
        return total

    class Meta:
        verbose_name = u"Gestion Posgrado"
        verbose_name_plural = u"Gestion Posgrado"
        ordering = ['id']

class GestionIntegrantesPosgradoHojaTrabajo(ModeloBase):
    gestionposgradohojatrabajo = models.ForeignKey(GestionPosgradoHojaTrabajo, verbose_name=u'Persona', on_delete=models.CASCADE)
    persona = models.ForeignKey('sga.Persona', verbose_name=u'Persona', on_delete=models.CASCADE)
    rmu = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"Rmu coordinador")

    def __str__(self):
        return f' {self.persona}'

    def en_uso(self):
        return self.gestionintegrantesactividadcarreraposgradohojatrabajo_set.filter(status=True).exists()

    def get_costo_por_hora(self):
        rmu_total = self.rmu
        valorpordia = rmu_total / 30
        valorporhora = valorpordia / 8 #horas
        return valorporhora

    def get_actividades(self):
        return self.gestionintegrantesactividadcarreraposgradohojatrabajo_set.filter(status=True)

    def get_total_horas_de_trabajo(self):
        return self.gestionintegrantesactividadcarreraposgradohojatrabajo_set.filter(status=True).aggregate(total=Sum('hora_de_trabajo'))['total']

    def get_total_costo_diario(self):
        total = 0
        for actividad in self.get_actividades():
            total += actividad.get_diario()
        return total

    def get_total_costo_mensual(self):
        total = 0
        total = round(self.get_total_costo_diario() * 30)
        return total

    class Meta:
        verbose_name = u"GestionIntegrantesPosgrado"
        verbose_name_plural = u"GestionIntegrantesPosgrado"
        ordering = ['id']

class GestionIntegrantesActividadCarreraPosgradoHojaTrabajo(ModeloBase):
    gestionintegrantesposgradohojatrabajo = models.ForeignKey(GestionIntegrantesPosgradoHojaTrabajo, verbose_name=u'Persona', on_delete=models.CASCADE)
    carrera = models.ForeignKey('sga.Carrera', null=True, blank=True, verbose_name=u'Carrera', on_delete=models.CASCADE)
    actividadpersonalposgrado = models.ForeignKey(ActividadPersonalPosgrado, null=True, blank=True, verbose_name=u'actividad', on_delete=models.CASCADE)
    hora_de_trabajo= models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"horas de trabajos")

    def __str__(self):
        return f' {self.get_actividad()}'

    def get_actividad(self):
        return self.carrera if self.carrera else self.actividadpersonalposgrado

    def get_diario(self):
        costo_por_hora = self.gestionintegrantesposgradohojatrabajo.get_costo_por_hora()
        return costo_por_hora * self.hora_de_trabajo

    def get_mensual(self):
        return round(self.get_diario() * 30)

    class Meta:
        verbose_name = u"GestionIntegrantesActividadCarreraPosgrado"
        verbose_name_plural = u"GestionIntegrantesActividadCarreraPosgrado"
        ordering = ['id']

class Perms(models.Model):
    class Meta:
        permissions = (
            ("puede_asignar_asesor", "Puede asignar asesor comercial"),
            ("puede_confirmar_pre_asignacion", "Puede confirmar la asignacion de un lead"),
            ("puede_ver_historial", "Puede ver el historial de asesores de un lead"),
            ("puede_ver_metas_personales", "Puede ver metas personales"),
            ("puede_configurar_asesor", "Puede configurar asesores"),
            ("puede_adicionar_leads", "Puede adicionar leads"),
            ("puede_ver_leads_asesor", "Puede ver leads registrados por un asesor"),
            ("puede_reasignar_asesor_masivo", "Puede reasignar un asesor de forma masiva a varios leads"),
            ("puede_adicionar_meta", "Puede adicionar meta de ventas"),
            ("puede_editar_meta", "Puede editar meta de ventas"),
            ("puede_eliminar_meta", "Puede eliminar meta de ventas"),
            ("puede_ver_reporteria", "Puede ver Reporteria"),
            ("puede_cambiar_formapago", "Puede cambiar forma de pago"),
            ("puede_ver_historial_forma_pago", "Puede ver el historial de forma de pago"),
            ("puede_ver_requisitos_financiamiento", "Puede ver requisitos de financiamiento"),
            ("puede_aprobar_requisitos_financiamiento", "Puede aprobar requisitos de financiamiento"),
            ("puede_configurar_financiamiento", "Puede configurar financiamiento"),
            ("puede_ver_historial_reserva", "Puede ver historial de reservaciones"),
            ("puede_reservar_prospectos", "Puede realizar reservaciones"),
            ("puede_ver_detalle_requisitos_admision", "Puede ver detalle de requisitos de admisión"),
            ("puede_firmar_contratos_pago", "Puede firmar contratos pago"),
            ("puede_ver_contratos_pagares", "Puede ver contratos y pagarés"),
            ("puede_entrar_como_usuario", "Puede entrar como usuario posgrado"),
            ("puede_subir_comprobante_pago_posgrado", "Puede subir comprobante de pago posgrado"),
            ("puede_ver_estadisticas_comercializacion", "Puede ver estadisticas del area comercial de posgrado"),
            ("puede_editar_rubro_fechas", "Puede editar rubros con fechas anteriores"),
            ("puede_generar_informe", "Puede generar informe homologacion interna"),
            ("puede_crear_encuestas_satisfaccion", "Puede crear encuestas de satisfaccion"),
            ("puede_configurar_evaluaciones_posgrado", "Puede configurar evaluaciones de desempeño de Posgrado"),
            ("puede_ver_solicitudes_gestion_balcon", "Puede ver listado general de solicitudes" ),
            ("puede_configurar_grupos_atencion_balcon", "Puede configurar grupos de atención balcón"),
            ("puede_planificar_fechas_hetero", "Puede planificar fechas de heteroevaluación"),
            ("puede_planificar_fechas_auto", "Puede planificar fechas de autoevaluación"),
            ("puede_planificar_fechas_dir", "Puede planificar fechas de directivos"),
            ("puede_planificar_fechas_satis", "Puede planificar fechas de encuesta de satisfacción"),
            ("puede_planificar_fechas_satis_est", "Puede planificar fechas de encuesta de satisfacción"),
            ("puede_procesar_resultados", "Puede procesar resultados de evaluaciones"),
            ("puede_crear_rubricas", "Puede crear rubricas para posgrado"),
            ("puede_ver_reportes_eval", "Puede ver reportes de evaluación docente posgrado"),
            ("es_gestor_de_seguimiento_a_graduados_posgrado", "Gestor de seguimiento a graduados de posgrado"),
            ("puede_ver_estadisticas_eval_pos", "Puede ver estadísticas de evaluación posgrado"),
            ("puede_ver_estadisticas_eval_edu", "Puede ver estadísticas de evaluación posgrado educación"),
            ("puede_ver_estadisticas_eval_sal", "Puede ver estadísticas de evaluación posgrado salud"),
            ("puede_ver_estadisticas_eval_neg", "Puede ver estadísticas de evaluación posgrado negocios"),
            ("puede_ver_estadisticas_eval_general", "Puede ver estadísticas de evaluación posgrado general"),
        )

class DepartamentoAtencionBalcon(ModeloBase):
    nombre = models.CharField(max_length=100, verbose_name=u'Nombre')

    def __str__(self):
        return f'{self.nombre}'

    def get_list_grupos(self):
        return GrupoAtencionBalcon.objects.filter(status=True, departamento_atencion=self)

    def puede_eliminar(self):
        if self.get_list_grupos().count() > 0:
            return False
        return True



    class Meta:
        verbose_name = 'Departamento Atencion Balcon'
        verbose_name_plural = 'Departamentos Atencion Balcon'
        ordering = ['nombre']

class GrupoAtencionBalcon(ModeloBase):
    nombre = models.CharField(max_length=100, verbose_name=u'Nombre')
    departamento_atencion = models.ForeignKey(DepartamentoAtencionBalcon, on_delete=models.CASCADE, verbose_name=u'Departamento de Atención')
    lider = models.ForeignKey('sga.Persona', on_delete=models.CASCADE, verbose_name=u'Líder de grupo')

    def __str__(self):
        return f'{self.nombre} - {self.departamento_atencion}'


    def get_integrantes(self):
        return IntegranteGrupoAtencionBalcon.objects.filter(grupo_atencion=self, status=True)

    class Meta:
        verbose_name = 'Grupo Atencion Balcon'
        verbose_name_plural = 'Grupos Atencion Balcon'
        ordering = ['nombre']

class IntegranteGrupoAtencionBalcon(ModeloBase):
    grupo_atencion = models.ForeignKey(GrupoAtencionBalcon, on_delete=models.CASCADE, verbose_name=u'Grupo de atención')
    integrante = models.ForeignKey('sga.Persona', on_delete=models.CASCADE, verbose_name=u'Integrante del grupo')
    activo = models.BooleanField(default=True, verbose_name=u'Activo')

    def __str__(self):
        return f'{self.integrante} - {self.grupo_atencion}'

    class Meta:
        verbose_name = 'Integrante Grupo Atencion Balcon'
        verbose_name_plural = 'Integrantes Grupos Atencion Balcon'
        ordering = ['integrante']

class TipoSolicitante(ModeloBase):
    nombre = models.CharField(max_length=100, verbose_name=u'Nombre')
    tipo_perfil = models.ForeignKey('sga.PerfilUsuario', on_delete=models.CASCADE, verbose_name=u'Tipo de perfil')

    def __str__(self):
        return f'{self.nombre} - {self.tipo_perfil}'

    class Meta:
        verbose_name = 'Tipo Solicitante'
        verbose_name_plural = 'Tipos Solicitantes'
        ordering = ['nombre']

class TipoSolicitudBalcon(ModeloBase):
    nombre = models.CharField(max_length=100, null=True, blank=True, verbose_name=u'Nombre')
    descripcion = models.TextField(default='', verbose_name=u'Descripción')

    def __str__(self):
        return f'{self.nombre}'

    class Meta:
        verbose_name = 'Tipo Solicitud'
        verbose_name_plural = 'Tipos Solicitudes'
        ordering = ['nombre']

class SolicitudBalcon(ModeloBase):
    from sga.models import MateriaAsignada
    from simple_history.models import HistoricalRecords

    # tipo_solicitud = models.IntegerField(choices=TipoSolicitud.choices, default=TipoSolicitud.NINGUNO, verbose_name=u'Tipo de solicitud')
    # tipo_solicitate = models.ForeignKey(TipoSolicitante, on_delete=models.CASCADE, verbose_name=u'Tipo de solicitante')

    class EstadoSolicitud(models.IntegerChoices):
        NUEVO = 1, 'Nuevo'
        EN_GESTION = 2, 'En gestión'
        FINALIZADA = 3, 'Finalizado'
        EN_REASIGNACION = 4, 'En reasignación',
        CON_RESPONSABLE = 5, 'Asignada responsable'


    class TipoProceso(models.IntegerChoices):
        SOLICITUD = 1, 'Solicitud'
        GESTION = 2, 'Gestión'

    tipo_solicitud = models.ForeignKey(TipoSolicitudBalcon, null=True, blank=True, on_delete=models.CASCADE, verbose_name=u'Tipo de solicitud')
    titulo = models.CharField(max_length=100, null=True, blank=True, verbose_name=u'Título')
    detalle = models.TextField(default='', verbose_name=u'Detalle de la solicitud')
    fecha_solicitud = models.DateField(auto_now_add=True, verbose_name=u'Fecha de solicitud')
    respuesta = models.TextField(default='', verbose_name=u'Respuesta')
    fecha_respuesta = models.DateField(null=True, blank=True, verbose_name=u'Fecha de respuesta')
    materia_asignada = models.ForeignKey(MateriaAsignada, on_delete=models.CASCADE, verbose_name=u'Materia', null=True, blank=True)
    estado = models.IntegerField(choices=EstadoSolicitud.choices, default=EstadoSolicitud.NUEVO, verbose_name=u'Estado de la solicitud')
    persona_recepta = models.ForeignKey('sga.Persona', related_name='+', on_delete=models.CASCADE, verbose_name=u'Persona que recepta', null=True, blank=True)
    calificacion = models.IntegerField(default=0, verbose_name=u'Calificación')
    calificacion_comentario = models.TextField(default='', verbose_name=u'Comentario')
    calificacion_fecha = models.DateField(null=True, blank=True, verbose_name=u'Fecha de calificación')

    tipo_proceso = models.IntegerField(choices=TipoProceso.choices, default=TipoProceso.SOLICITUD, verbose_name=u'Tipo de proceso')
    grupo_atencion = models.ForeignKey(GrupoAtencionBalcon, null=True, blank=True, on_delete=models.CASCADE, verbose_name=u'Departamento de atención')
    detalle_gestion = models.TextField(default='', verbose_name=u'Detalle de la gestión')
    responsable = models.ForeignKey(IntegranteGrupoAtencionBalcon, null=True, blank=True, on_delete=models.CASCADE, verbose_name=u'Responsable de Gestión')
    asignado_por = models.ForeignKey('sga.Persona', related_name='+', null=True, blank=True, on_delete=models.CASCADE, verbose_name=u'Asignado por')
    fecha_inicio_gestion = models.DateField(null=True, blank=True, verbose_name=u'Fecha de inicio de gestión')
    fecha_finaliza_gestion = models.DateField(null=True, blank=True, verbose_name=u'Fecha de finalización de gestión')
    motivo_reasignacion = models.TextField(default='', verbose_name=u'Motivo de reasignación')

    history = HistoricalRecords()


    def __str__(self):
        return f'{self.tipo_solicitud.__str__()} - {self.titulo}'

    def fecha_solicitud_format(self):
        return self.fecha_solicitud.strftime('%d/%m/%Y')

    def to_json(self):
        from django.forms.models import model_to_dict
        item = model_to_dict(self)
        item['fecha_solicitud'] = self.fecha_solicitud_format()
        item['maestrante'] = self.get_maestrante()
        item['persona_recepta'] = self.persona_recepta.__str__()
        return item

    def get_lista_adjuntos(self):
        return AdjuntoSolicitudBalcon.objects.filter(solicitud=self, status=True, tipo=1)

    def get_adjunto_gestion(self):
        return AdjuntoSolicitudBalcon.objects.filter(solicitud=self, status=True, tipo=2)

    def get_respuesta_archivo(self):
        archivoRespuesta = AdjuntoSolicitudBalcon.objects.filter(solicitud=self, tipo=3).first()
        if archivoRespuesta:
            return archivoRespuesta.archivo
        return None

    def get_maestrante(self):
        return self.materia_asignada.matricula.inscripcion

    def estado_label(self):
        if self.estado == 1:
            return {'class': 'badge badge-primary', 'text': 'Nuevo'}
        elif self.estado == 2:
            return {'class': 'badge badge-info', 'text': 'En gestión'}
        elif self.estado == 3:
            return {'class': 'badge badge-success', 'text': 'Finalizado'}
        elif self.estado == 4:
            return {'class': 'badge badge-warning', 'text': 'En reasignación'}
        elif self.estado == 5:
            return {'class': 'badge badge-secondary', 'text': 'Asignada responsable'}
        else:
            return {'class': 'badge badge-danger', 'text': 'Desconocido'}

    def es_reasignada(self):
        return self.estado == 4

    def get_calificacion_display(self):
        from django.utils.html import format_html
        if self.calificacion > 0:
            estrellas_llenas = '★' * self.calificacion
            estrellas_vacias = '☆' * (5 - self.calificacion)
            return format_html('<div id="rating" class="stars">{}</div>', estrellas_llenas + estrellas_vacias)
        return ''

    def is_finalizada_calificacion(self):
        return self.calificacion > 0 and self.estado == 3

    def historical_solicitud(self):
        historys = self.history.all()
        if historys.exists():
            return historys.exclude(estado__in=[4, 5])
        return None

    def historical_gestiom(self):
        historys = self.history.all()

    def get_profesores_materiaasignada(self):
        return self.materia_asignada.materia.profesormateria_set.filter(status=True)

    class Meta:
        verbose_name = 'Solicitud Balcon'
        verbose_name_plural = 'Solicitudes Balcon'
        ordering = ['tipo_solicitud']

class AdjuntoSolicitudBalcon(ModeloBase):

    class TipoAdjunto(models.IntegerChoices):
        SOLICITUD = 1, 'Solicitud'
        GESTION = 2, 'Gestion'
        RESPUESTA = 3, 'Respuesta'

    solicitud = models.ForeignKey('SolicitudBalcon', on_delete=models.CASCADE, verbose_name=u'Solicitud')
    archivo = models.FileField(upload_to='solicitudesposgrado/adjuntos/%Y', verbose_name=u'Archivo')
    nombre = models.CharField(max_length=100, null=True, blank=True, verbose_name=u'Nombre')
    tipo = models.IntegerField(choices=TipoAdjunto.choices, default=TipoAdjunto.SOLICITUD, verbose_name=u'Tipo de adjunto')

    def __str__(self):
        return f'{self.solicitud} - {self.archivo}'

    def is_pdf(self):
        return self.archivo.name.endswith('.pdf')

    class Meta:
        verbose_name = 'Adjunto Solicitud'
        verbose_name_plural = 'Adjuntos Solicitudes'
        ordering = ['solicitud']

class HorariosProgramaMaestria(ModeloBase):
    maestria = models.ForeignKey(MaestriasAdmision, null=True, blank=True, verbose_name=u'Materia', on_delete=models.CASCADE)
    nombre = models.TextField(default='', verbose_name=u'Horario')
    paralelo = models.CharField(max_length=100, null=True, blank=True, verbose_name=u'Paralelo')
    activo = models.BooleanField(default=True, verbose_name=u'Horario activo')

    def __str__(self):
        return f'{self.nombre} - PARALELO {self.paralelo}'

    def cantidad_admitidos(self):
        cant = 0
        if DetalleAtencionAdmitido.objects.filter(status=True, activo=True, atendido=True, horario=self).exists():
            cant = DetalleAtencionAdmitido.objects.filter(status=True, activo=True, atendido=True, horario=self).values_list('admitido__id', flat=True).order_by('admitido__id').distinct().count()
        return cant
    class Meta:
        verbose_name = 'Horario de programa de maestria'
        verbose_name_plural = 'Horarios de programa de maestria'
        ordering = ['-id']

class DetalleAtencionAdmitido(ModeloBase):
    admitido = models.ForeignKey(InscripcionCohorte, blank=True, null=True, verbose_name=u'Admitido con pago', on_delete=models.CASCADE)
    horario = models.ForeignKey(HorariosProgramaMaestria, blank=True, null=True, verbose_name=u'Horario seleccionado', on_delete=models.CASCADE)
    atendido = models.BooleanField(default=False, verbose_name=u'Verfica si ha sido asignado el horario')
    activo = models.BooleanField(default=True, verbose_name=u'Horario activo')

    def __str__(self):
        return u'%s' % self.admitido.inscripcionaspirante

    class Meta:
        verbose_name = "Detalle de atención del admitido"
        verbose_name_plural = "Detalles de atención del admitido"
        ordering = ['-id']

class CatalogoClasificadorPresupuestario(ModeloBase):
    descripcion = models.TextField(max_length=200, verbose_name=u'Descripción')
    activo = models.BooleanField(default=True, verbose_name=u'¿Activo?')

    class Meta:
        verbose_name = "Catalogo Clasificador Presupuestario"
        verbose_name_plural = "Catalogo Clasificadores Presupuestarios"
    def __str__(self):
        return f"{self.descripcion}"

class ClasificadorPresupuestario(ModeloBase):
    clasificadorpresupuestario = models.ForeignKey(CatalogoClasificadorPresupuestario, on_delete=models.CASCADE,verbose_name=u'Catalogo Clasificador Presupuestario')
    codigo_naturaleza = models.CharField(max_length=10)
    codigo_grupo = models.CharField(max_length=10, null=True, blank=True)
    codigo_subgrupo = models.CharField(max_length=10, null=True, blank=True)
    codigo_rubro = models.CharField(max_length=10, null=True, blank=True)
    nombre = models.CharField(max_length=800, verbose_name=u'Nombre')
    descripcion = models.TextField(max_length=800, verbose_name=u'Descripción')

    class Meta:
        verbose_name = "Clasificador Presupuestario"
        verbose_name_plural = "Clasificadores Presupuestarios"
        ordering = ['codigo_naturaleza', 'codigo_grupo', 'codigo_subgrupo', 'codigo_rubro']

    def __str__(self):
        return f"{self.get_codigo_clasificador_presupuestario } - {self.nombre}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.codigo_naturaleza and self.codigo_grupo and not self.codigo_subgrupo and not  self.codigo_rubro:
            raise ValidationError("Debe definir la naturaleza antes de definir el grupo.")

        if not self.codigo_naturaleza and not self.codigo_grupo and  self.codigo_subgrupo and not  self.codigo_rubro:
            raise ValidationError("Debe definir la naturaleza y grupo antes de definir el subgrupo.")

        if not self.codigo_naturaleza and not self.codigo_grupo and not self.codigo_subgrupo and not self.codigo_rubro:
            raise ValidationError("Debe definir la naturaleza, grupo y subgrupo antes de definir el rubro.")

        if  self.codigo_naturaleza and  not self.codigo_grupo and  self.codigo_subgrupo and not  self.codigo_rubro:
            raise ValidationError("Debe definir El grupo antes de definir el subgrupo.")

        if  self.codigo_naturaleza and self.codigo_grupo and  not self.codigo_subgrupo and  self.codigo_rubro:
            raise ValidationError("Debe definir El subgrupo antes de definir el rubro.")

        if  not self.codigo_naturaleza and self.codigo_grupo and  self.codigo_subgrupo and  self.codigo_rubro:
            raise ValidationError("Debe definir la naturaleza antes de definir el rubro.")

        if not self.codigo_naturaleza and not self.codigo_grupo and self.codigo_subgrupo and self.codigo_rubro:
            raise ValidationError("Debe definir la naturaleza y grupo antes de definir el rubro.")

        if not self.codigo_naturaleza and not self.codigo_grupo and not self.codigo_subgrupo and self.codigo_rubro:
            raise ValidationError("Debe definir la naturaleza,grupo y subgrupo antes de definir el rubro.")

        if self.codigo_naturaleza and not self.codigo_grupo and  self.codigo_subgrupo and self.codigo_rubro:
            raise ValidationError("Debe definir grupo  antes de definir el rubro.")

        if self.codigo_naturaleza and not self.codigo_grupo and  not self.codigo_subgrupo and self.codigo_rubro:

            raise ValidationError("Debe definir grupo y subgrupo antes de definir el rubro.")

        if ClasificadorPresupuestario.objects.filter(
                Q(status=True),
                codigo_naturaleza=self.codigo_naturaleza,
                codigo_grupo=self.codigo_grupo,
                codigo_subgrupo=self.codigo_subgrupo,
                codigo_rubro=self.codigo_rubro
        ).exclude(id=self.id).exists():
            raise ValidationError(f"Ya existe un clasificador con esta combinación de códigos.")

    @staticmethod
    def ultima_naturaleza(id_clp):
        return ClasificadorPresupuestario.objects.values_list('codigo_naturaleza', flat=True).filter(status=True,
                   clasificadorpresupuestario=id_clp).order_by('-codigo_naturaleza').first()
    @staticmethod
    def ultimo_grupo(id_clp, cod_nat):
        cod_naturaleza = ClasificadorPresupuestario.ultima_naturaleza(id_clp)
        return ClasificadorPresupuestario.objects.values_list('codigo_grupo', flat=True).filter(status=True,
                   clasificadorpresupuestario=id_clp, codigo_naturaleza=cod_nat).order_by('-codigo_grupo').exclude(
                                                                            codigo_grupo__isnull=True).first()

    @staticmethod
    def ultimo_subgrupo(id_clp, cod_nat, cod_grupo):
        return ClasificadorPresupuestario.objects.values_list('codigo_grupo', flat=True).filter(status=True,
                   clasificadorpresupuestario=id_clp,codigo_naturaleza=cod_nat, codigo_grupo=cod_grupo ).order_by(
                    '-codigo_grupo').exclude(codigo_subgrupo__isnull=True).first()

    @staticmethod
    def ultimo_rubro(id_clp, cod_nat, cod_grupo, cod_subgrupo):
        return ClasificadorPresupuestario.objects.values_list('codigo_rubro', flat=True).filter(status=True,
                      clasificadorpresupuestario=id_clp,codigo_naturaleza=cod_nat, codigo_grupo=cod_grupo,
                      codigo_subgrupo=cod_subgrupo).order_by('-codigo_rubro').exclude(codigo_rubro__isnull=True).first()

    @property
    def get_codigo_clasificador_presupuestario(self):
        return ".".join(filter(None, [self.codigo_naturaleza, self.codigo_grupo, self.codigo_subgrupo, self.codigo_rubro]))

    def get_grupos(self):
        return ClasificadorPresupuestario.objects.filter(status=True, clasificadorpresupuestario=self.clasificadorpresupuestario,
                                                         codigo_naturaleza=self.codigo_naturaleza).exclude(id=self.id).exclude(
                                                                codigo_subgrupo__isnull=False)

    def get_subgrupos(self):
        return ClasificadorPresupuestario.objects.filter(status=True, clasificadorpresupuestario=self.clasificadorpresupuestario,
                                                            codigo_naturaleza=self.codigo_naturaleza, codigo_grupo=self.codigo_grupo).exclude(id=self.id).exclude(
                                                                codigo_rubro__isnull=False)

    def get_rubros(self):
        return ClasificadorPresupuestario.objects.filter(status=True, clasificadorpresupuestario=self.clasificadorpresupuestario,
                                                            codigo_naturaleza=self.codigo_naturaleza, codigo_grupo=self.codigo_grupo,
                                                            codigo_subgrupo=self.codigo_subgrupo).exclude(id=self.id)

    def es_naturaleza(self):
        return True if self.codigo_naturaleza is not None and self.codigo_grupo is None and self.codigo_subgrupo is None and self.codigo_rubro is None else False

    def es_grupo(self):
        return True if self.codigo_naturaleza is not None and self.codigo_grupo is not None and self.codigo_subgrupo is None and self.codigo_rubro is None else False

    def es_sub_grupo(self):
        return True if self.codigo_naturaleza is not None and self.codigo_grupo is not None and self.codigo_subgrupo is not None and self.codigo_rubro is None else False

    def es_rubro(self):
        return True if self.codigo_naturaleza is not None and self.codigo_grupo is not None and self.codigo_subgrupo is not None and self.codigo_rubro is not None else False

    def esta_en_uso(self):
        return AsociacionPresupuestaria.objects.filter(clasificadorpresupuestario=self,
                                                       status=True,
                                                       cuentacontable__status=True,
                                                       cuentacontable__catalogocuentacontable__status=True).exists()

class CatalogoCuentaContable(ModeloBase):
    descripcion = models.TextField(max_length=200, verbose_name=u'Descripción')
    activo = models.BooleanField(default=True, verbose_name=u'¿Activo?')

    class Meta:
        verbose_name = "Catalogo Cuenta Contable"
        verbose_name_plural = "Catalogo Cuenta Contable"

    def __str__(self):
        return f"{self.descripcion}"

class CuentaContable(ModeloBase):
    class TipoCuenta(models.IntegerChoices):
        INGRESO = 1,"Ingreso"
        EGRESO = 2, "Egreso"
        PATRIMONIO = 3, "Patrimonio"
        ORDEN = 4, "Orden"

    class ConfiguracionCampoValor(models.IntegerChoices):
        ninguno = 0,"ninguno"
        total_reporte_coordinador = 1,"Total Coordinador"
        total_reporte_coordinador_apoyo = 2, "Total Coordinador de Apoyo"
        total_reporte_profesor_modular = 3, "Total Profesor Modular"
        total_reporte_profesor_invitado_posgrado = 4, "Total Profesor Invitado Posgrado"
        total_reporte_personal_administrativo = 5, "Total Personal Administrativo"
        total_reporte_costo_variable = 6, "Total Costo Variable"
        total_otros_ingresos = 7, "Total otros ingresos"

    catalogocuentacontable = models.ForeignKey(CatalogoCuentaContable, on_delete=models.CASCADE,verbose_name=u'Catalogo Cuenta Contable')
    codigo_categoria = models.CharField(max_length=10)
    codigo_grupo = models.CharField(max_length=10, null=True, blank=True)
    codigo_subgrupo = models.CharField(max_length=10, null=True, blank=True)
    codigo_rubro = models.CharField(max_length=10, null=True, blank=True)
    codigo_subrubro = models.CharField(max_length=10, null=True, blank=True)
    nombre = models.CharField(max_length=700, verbose_name=u'Nombre')
    descripcion = models.TextField(max_length=800, verbose_name=u'Descripción')
    tipo = models.IntegerField(choices=TipoCuenta.choices, default=TipoCuenta.INGRESO, verbose_name=u'Tipo cuenta')
    carrera = models.ForeignKey('sga.Carrera', null=True, blank=True, verbose_name=u'Carrera', on_delete=models.CASCADE)
    configuracioncampo = models.IntegerField(choices=ConfiguracionCampoValor.choices, default=ConfiguracionCampoValor.ninguno,verbose_name="Campo de Balance de Costo")

    class Meta:
        verbose_name = "Cuenta Contable"
        verbose_name_plural = "Cuentas Contable"

    def __str__(self):
        return f"{self.get_codigo_cuenta_contable} - {self.nombre}"

    @property
    def get_codigo_cuenta_contable(self):
        return ".".join(filter(None, [self.codigo_categoria, self.codigo_grupo, self.codigo_subgrupo, self.codigo_rubro, self.codigo_subrubro]))

    def clean(self):
        from django.core.exceptions import ValidationError
        codes = ['codigo_categoria', 'codigo_grupo', 'codigo_subgrupo', 'codigo_rubro', 'codigo_subrubro', 'carrera']

        # Check if each code is defined in the correct order
        for i, code in enumerate(codes):
            if getattr(self, code) and not all(getattr(self, c) for c in codes[:i]):
                error_message = f"Debe definir {', '.join(codes[:i])} antes de definir {code}."
                raise ValidationError(error_message)

        if CuentaContable.objects.filter(
                Q(status=True),
                codigo_categoria=self.codigo_categoria,
                codigo_grupo=self.codigo_grupo,
                codigo_subgrupo=self.codigo_subgrupo,
                codigo_rubro=self.codigo_rubro,
                codigo_subrubro=self.codigo_subrubro,
                carrera=self.carrera
        ).exclude(id=self.id).exists():
            raise ValidationError(f"Ya existe una cuenta contable con esta combinación de códigos.")

    def es_categoria(self):
        return True if self.codigo_categoria is not None and self.codigo_grupo is None and self.codigo_subgrupo is None and self.codigo_rubro is None and self.codigo_subrubro is None else False

    def es_grupo(self):
        return True if self.codigo_categoria is not None and self.codigo_grupo is not None and self.codigo_subgrupo is None and self.codigo_rubro is None and self.codigo_subrubro is None else False

    def es_sub_grupo(self):
        return True if self.codigo_categoria is not None and self.codigo_grupo is not None and self.codigo_subgrupo is not None and self.codigo_rubro is None and self.codigo_subrubro is None else False

    def es_rubro(self):
        return True if self.codigo_categoria is not None and self.codigo_grupo is not None and self.codigo_subgrupo is not None and self.codigo_rubro is not None and self.codigo_subrubro is None else False

    def es_subrubro(self):
        return True if self.codigo_categoria is not None and self.codigo_grupo is not None and self.codigo_subgrupo is not None and self.codigo_rubro is not None and not self.codigo_subrubro is None else False

    def get_asociacion_presupuestaria(self):
        return self.asociacionpresupuestaria_set.filter(status=True)

    def es_ingreso(self):
        return True if self.tipo == 1 else False

    def es_egreso(self):
        return True if self.tipo == 2 else False

    def esta_en_uso(self):
        eCuentaFlujoEfectivoMensual = CuentaFlujoEfectivoMensual.objects.filter(status=True,actividadflujoefectivomensual__status=True,actividadflujoefectivomensual__flujoefectivomensual__status=True,cuentacontable = self).exists()
        eDetalleEstadoResultadoIntegral = DetalleEstadoResultadoIntegral.objects.filter(estado_resultado_integral__status=True,status=True,cuentacontable = self).exists()
        eDetalleEjecucionPresupuestaria = DetalleEjecucionPresupuestaria.objects.filter(ejecucion_presupuestaria__status=True,status=True,cuentacontable = self).exists()
        return True if eCuentaFlujoEfectivoMensual or eDetalleEstadoResultadoIntegral or eDetalleEjecucionPresupuestaria else False

class AsociacionPresupuestaria(ModeloBase):

    class TipoCuenta(models.IntegerChoices):
        DEBITO = 1,"Debito"
        CREDITO = 2, "Credito"

    cuentacontable = models.ForeignKey(CuentaContable, on_delete=models.CASCADE, verbose_name=u'Cuenta Contable')
    clasificadorpresupuestario = models.ForeignKey(ClasificadorPresupuestario, on_delete=models.CASCADE, verbose_name=u'Clasificador Presupuestario')
    tipo = models.IntegerField(choices=TipoCuenta.choices,default =TipoCuenta.CREDITO,  verbose_name=u'Tipo asociación cuenta')

    def __str__(self):
        return f"{self.clasificadorpresupuestario} - {self.get_tipo_display()}"

    class Meta:
        verbose_name = "Asociacion Presupuestaria"
        verbose_name_plural = "Asociacion Presupuestaria"

class ConfFlujoEfectivo(ModeloBase):

    class TipoFlujoEfectivo(models.IntegerChoices):
        OPERACION = 1,"Actividades de Operación"
        INVERSION = 2, "Actividades de Inversión"
        FINANCIAMENTO = 3, "Actividades de Financiamiento"

    tipoflujo = models.IntegerField(choices=TipoFlujoEfectivo.choices,default=TipoFlujoEfectivo.OPERACION, verbose_name=u'Tipo operacion')
    orden = models.IntegerField(blank=True, null=True, verbose_name=u'Orden')

    class Meta:
        verbose_name = "Configuración general  Flujo de efectivo"
        verbose_name_plural = "Configuración general Flujo de efectivo"

    def __str__(self):
        return f"{self.get_tipoflujo_display()}"

    def get_cuentas(self):
        return self.confcuentaflujoefectivo_set.filter(status=True).order_by('cuentacontable__tipo',Coalesce('cuentacontable__codigo_categoria', Value('\uffff')), Coalesce('cuentacontable__codigo_grupo', Value('\uffff')),Coalesce('cuentacontable__codigo_subgrupo', Value('\uffff')),Coalesce('cuentacontable__codigo_rubro', Value('\uffff')),Coalesce('cuentacontable__codigo_subrubro', Value('\uffff')))

class ConfCuentaFlujoEfectivo(ModeloBase):

    class ConfiguracionCampoValor(models.IntegerChoices):
        ninguno = 0,"ninguno"
        total_reporte_coordinador = 1,"Total Coordinador"
        total_reporte_coordinador_apoyo = 2, "Total Coordinador de Apoyo"
        total_reporte_profesor_modular = 3, "Total Profesor Modular"
        total_reporte_profesor_invitado_posgrado = 4, "Total Profesor Invitado Posgrado"
        total_reporte_personal_administrativo = 5, "Total Personal Administrativo"
        total_reporte_costo_variable = 6, "Total Costo Variable"
        total_otros_ingresos = 7, "Total otros ingresos"

    confflujoefectivo = models.ForeignKey(ConfFlujoEfectivo, on_delete=models.CASCADE,verbose_name=u'Configuración general Flujo de efectivo')
    cuentacontable = models.ForeignKey(CuentaContable, on_delete=models.CASCADE, verbose_name=u'Configuración general  Cuenta Contable')
    configuracioncampo = models.IntegerField(choices=ConfiguracionCampoValor.choices, default=ConfiguracionCampoValor.ninguno,verbose_name="Campo de Balance de Costo")

    class Meta:
        verbose_name = "Cuenta Flujo de efectivo"
        verbose_name_plural = "Cuenta Flujo de efectivo"

    def __str__(self):
        return f"{self.cuentacontable}"

class FlujoEfectivoMensual(ModeloBase):

    class TipoEstado(models.IntegerChoices):
        GENERADO = 0,"Generado"
        VALIDADO = 1, "Válidado"
    anio = models.IntegerField(default=0, verbose_name=u'Anio del periodo')
    mes = models.IntegerField(choices=MESES_CHOICES, default=0, verbose_name=u'Mes')
    descripcion = models.CharField(default='', max_length=150, verbose_name=u"Descripcion")
    estado = models.IntegerField(choices=TipoEstado.choices,default =TipoEstado.GENERADO,  verbose_name=u'Tipo estado')
    superavit = models.DecimalField(max_digits=30, decimal_places=2, default=0, verbose_name=u"Superavit")

    def __str__(self):
        return f'[{self.pk}]{self.anio} - {self.get_mes_display()}'

    class Meta:
        verbose_name = u"Flujo Efectivo mensual"
        verbose_name_plural = u"Flujo Efectivo mensual"
        ordering = ['id']

    def buscar_valor_en_balance_de_costo_mensual(self,request,mes,anio,carrera_id):
        try:
            valor = 0
            with transaction.atomic():
                if BalanceCosto.objects.filter(status=True,anio=anio,mes=mes,estado= 1).exists():
                    valor = BalanceCostoCarreraPeriodoParalelo.objects.filter(balancecostocarreraperiodo__balancecostocarrera__carrera_id= carrera_id,status=True,balancecostocarreraperiodo__balancecostocarrera__balancecosto__anio=anio,balancecostocarreraperiodo__balancecostocarrera__balancecosto__mes=mes,balancecostocarreraperiodo__balancecostocarrera__balancecosto__estado= 1,balancecostocarreraperiodo__status=True, balancecostocarreraperiodo__balancecostocarrera__status=True, balancecostocarreraperiodo__balancecostocarrera__balancecosto__status=True).aggregate(total_ingresos=Sum('ingresos'))['total_ingresos'] or 0
                else:
                    valor = 0
            return valor
        except Exception as ex:
            messages.error(request, f'Ocurrió un error al asignar el valor del balance de costo: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
            raise

    def buscar_totales_reportes_valor_en_reportes_mensuales(self,request,mes,anio,configuracioncampo):
        try:
            valor = 0
            with transaction.atomic():
                if BalanceCosto.objects.filter(status=True,anio=anio,mes=mes,estado= 1).exists():
                    eBalanceCosto = BalanceCosto.objects.filter(status=True, anio=anio, mes=mes, estado=1).first()

                    if configuracioncampo == 1:
                        valor = eBalanceCosto.total_reporte_coordinador
                    elif configuracioncampo == 2:
                        valor = eBalanceCosto.total_reporte_coordinador_apoyo
                    elif configuracioncampo == 3:
                        valor = eBalanceCosto.total_reporte_profesor_modular
                    elif configuracioncampo == 4:
                        valor = eBalanceCosto.total_reporte_profesor_invitado_posgrado
                    elif configuracioncampo == 5:
                        valor = eBalanceCosto.total_reporte_personal_administrativo
                    elif configuracioncampo == 6:
                        valor = eBalanceCosto.total_reporte_costo_variable
                    elif configuracioncampo == 7:
                        valor = BalanceCostoCarreraPeriodoParalelo.objects.filter(status=True,balancecostocarreraperiodo__balancecostocarrera__balancecosto__anio=anio,balancecostocarreraperiodo__balancecostocarrera__balancecosto__mes=mes,balancecostocarreraperiodo__balancecostocarrera__balancecosto__estado= 1,balancecostocarreraperiodo__status=True, balancecostocarreraperiodo__balancecostocarrera__status=True, balancecostocarreraperiodo__balancecostocarrera__balancecosto__status=True).aggregate(total_otrosingresos=Sum('otrosingresos'))['total_otrosingresos'] or 0
                    else:
                        valor = 0
            return valor
        except Exception as ex:
            messages.error(request, f'Ocurrió un error al asignar el valor del balance de costo: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
            raise

    def generar_estructura_flujo_efectivo_mensual(self,request):
        try:
            with transaction.atomic():
                eConfFlujoEfectivos = ConfFlujoEfectivo.objects.filter(status=True).order_by('id')
                for eConfFlujoEfectivo in eConfFlujoEfectivos:
                    eActividadFlujoEfectivoMensual = ActividadFlujoEfectivoMensual(
                        flujoefectivomensual=self,
                        tipoflujo=eConfFlujoEfectivo.tipoflujo,
                        orden=eConfFlujoEfectivo.orden,
                    )
                    eActividadFlujoEfectivoMensual.save(request)
                    log(u'Agregó actividad flujo de efectivo: %s' % eActividadFlujoEfectivoMensual, request, "add")
                    for confcuenta in eConfFlujoEfectivo.get_cuentas():
                        eCuentaFlujoEfectivoMensual = CuentaFlujoEfectivoMensual(
                            actividadflujoefectivomensual = eActividadFlujoEfectivoMensual,
                            cuentacontable =confcuenta.cuentacontable
                        )
                        eCuentaFlujoEfectivoMensual.save(request)
                        if confcuenta.cuentacontable.carrera:
                            eCuentaFlujoEfectivoMensual.valor = self.buscar_valor_en_balance_de_costo_mensual(request, self.mes, self.anio, confcuenta.cuentacontable.carrera_id)
                            eCuentaFlujoEfectivoMensual.save(request)

                        if not confcuenta.configuracioncampo == 0 and  not confcuenta.cuentacontable.carrera:
                            eCuentaFlujoEfectivoMensual.valor = self.buscar_totales_reportes_valor_en_reportes_mensuales(request, self.mes, self.anio, confcuenta.configuracioncampo)
                            eCuentaFlujoEfectivoMensual.save(request)
                        log(u'Agregó cuenta a la actividad flujo de efectivo: %s' % eCuentaFlujoEfectivoMensual, request, "add")

                    for eCuentaFlujoEfectivoMensual in eActividadFlujoEfectivoMensual.get_cuenta_flujo_efectivo():
                        if not eCuentaFlujoEfectivoMensual.cuenta_no_puede_ser_editada():
                            eCuentaFlujoEfectivoMensual.recalcular_cuenta_padre_flujo_efectivo(request,eCuentaFlujoEfectivoMensual.cuentacontable)
                            eCuentaFlujoEfectivoMensual.actualizar_total_ingresos_por_actividad_flujoefectivo(request)
                            eCuentaFlujoEfectivoMensual.actualizar_total_egresos_por_actividad_flujoefectivo(request)
                            eCuentaFlujoEfectivoMensual.actualizar_resultado_por_actividad_flujoefectivo(request)
                            eCuentaFlujoEfectivoMensual.actualizar_superavit_flujoefectivo(request)
                            log(u'actualizo el sistema valor cuenta flujo efectivo: %s' % eCuentaFlujoEfectivoMensual, request,"edit")

        except Exception as ex:
            messages.error(request, f'Ocurrió un error al generar estructura del flujo de efectivo: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
            raise

    def get_estado_badge(self):
        if self.estado == 0:
            return f"<span class='badge rounded-pill bg-warning'>{self.get_estado_display()}</span>"

        if self.estado == 1:
            return f"<span class='badge rounded-pill bg-success'>{self.get_estado_display()}</span>"

    def estado_flujo_efectivo_generado(self):
        return True if self.estado == 0 else False

    def estado_flujo_efectivo_validado(self):
        return True if self.estado == 1 else False

    def get_actividad_flujo_efectivo(self):
        return self.actividadflujoefectivomensual_set.filter(status=True).order_by('orden')

    def generar_reporte_flujo_efectivo_mensual_excel(self,request):
        try:
            import io
            import xlsxwriter
            from pdip.funciones import FORMATOS_CELDAS_EXCEL
            from django.http import HttpResponse
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            ws = workbook.add_worksheet()

            ftitulo1 = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo1"])
            fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])
            textonegrita = workbook.add_format(FORMATOS_CELDAS_EXCEL["textonegrita"])

            ws.merge_range(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo1)
            ws.merge_range(1, 0, 1, 8, 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADOS', ftitulo1)
            ws.merge_range(2, 0, 2, 8, f'FLUJO DE EFECTIVO MENSUAL: {self.anio} - {self.get_mes_display().upper()} ', ftitulo1)
            columns = [
                (u"CÓDIGO", 30),
                (u"CUENTA CONTABLE", 160),
                (u"INGRESO", 25),
                (u"EGRESO", 20),
                (u"RESULTADO", 20),
            ]

            row_num = 4
            for col_num in range(len(columns)):
                ws.write(row_num, col_num, columns[col_num][0], fcabeceracolumna)
                ws.set_column(col_num, col_num, columns[col_num][1])

            row_num += 1
            for actividad in self.get_actividad_flujo_efectivo():
                # Merge row for each activity title
                ws.write(row_num, 0, '')
                ws.write(row_num, 1, actividad.get_tipoflujo_display(), textonegrita)
                ws.write(row_num, 2, actividad.total_ingresos)
                ws.write(row_num, 3, actividad.total_egresos)
                ws.write(row_num, 4, actividad.resultado)
                row_num += 1

                for cuenta in actividad.get_cuenta_flujo_efectivo():
                    ws.write(row_num, 0, cuenta.cuentacontable.get_codigo_cuenta_contable)  # Código
                    ws.write(row_num, 1, cuenta.cuentacontable.nombre)  # Cuenta contable

                    if cuenta.cuentacontable.es_ingreso():
                        ws.write(row_num, 2, cuenta.valor if not cuenta.cuenta_no_puede_ser_editada() else "")  # Ingreso
                    else:
                        ws.write(row_num, 2, "")

                    if cuenta.cuentacontable.es_egreso():
                        ws.write(row_num, 3, cuenta.valor if not cuenta.cuenta_no_puede_ser_editada() else "")  # Egreso
                    else:
                        ws.write(row_num, 3, "")

                    row_num += 1

            # Fila de total
            total_row_num = row_num
            ws.merge_range(total_row_num, 0, total_row_num, 3, 'SUPERAVIT', fcabeceracolumna)
            ws.write(total_row_num, 4, f"{self.superavit}", fcabeceracolumna)

            # Finalize workbook
            workbook.close()
            output.seek(0)
            filename = f'flujo_de_efectivo_mensual_{self.pk}_{self.anio}_{self.mes}.xlsx'
            response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        except Exception as ex:
            raise

    def existe_otro_flujo_de_efectivo_validado_en_el_mismo_mes_and_anio(self):
        return FlujoEfectivoMensual.objects.filter(status=True,anio = self.anio,mes = self.mes,estado=1).exclude(pk=self.pk).exists()

class ActividadFlujoEfectivoMensual(ModeloBase):

    class TipoFlujoEfectivo(models.IntegerChoices):
        OPERACION = 1,"Actividades de Operación"
        INVERSION = 2, "Actividades de Inversión"
        FINANCIAMENTO = 3, "Actividades de Financiamiento"

    flujoefectivomensual = models.ForeignKey(FlujoEfectivoMensual, on_delete=models.CASCADE, verbose_name=u'Flujo de efectivo mensual')
    tipoflujo = models.IntegerField(choices=TipoFlujoEfectivo.choices,default=TipoFlujoEfectivo.OPERACION,verbose_name=u'tipo Flujo de efectivo')
    orden = models.IntegerField(blank=True, null=True, verbose_name=u'Orden')
    total_ingresos = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    total_egresos = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    resultado = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)

    class Meta:
        verbose_name = "Flujo de efectivo"
        verbose_name_plural = "Flujo de efectivo"

    def __str__(self):
        return f"{self.get_tipoflujo_display()}"

    def get_cuenta_flujo_efectivo(self):
        return self.cuentaflujoefectivomensual_set.filter(status=True).order_by('cuentacontable__tipo',Coalesce('cuentacontable__codigo_categoria', Value('\uffff')), Coalesce('cuentacontable__codigo_grupo', Value('\uffff')),Coalesce('cuentacontable__codigo_subgrupo', Value('\uffff')),Coalesce('cuentacontable__codigo_rubro', Value('\uffff')),Coalesce('cuentacontable__codigo_subrubro', Value('\uffff')))

class CuentaFlujoEfectivoMensual(ModeloBase):
    actividadflujoefectivomensual = models.ForeignKey(ActividadFlujoEfectivoMensual, on_delete=models.CASCADE,verbose_name=u'Actividad Flujo de efectivo mensual')
    cuentacontable = models.ForeignKey(CuentaContable, on_delete=models.CASCADE, verbose_name=u'Cuenta Contable')
    valor = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)

    class Meta:
        verbose_name = "Cuenta Flujo de efectivo mensual"
        verbose_name_plural = "Cuenta Flujo de efectivo mensual"

    def __str__(self):
        return f"{self.cuentacontable}"

    def cuenta_no_puede_ser_editada(self):
        if self.cuentacontable.es_categoria():
            return CuentaFlujoEfectivoMensual.objects.filter(
                Q(actividadflujoefectivomensual__flujoefectivomensual=self.actividadflujoefectivomensual.flujoefectivomensual),
                Q(status=True),
                Q(cuentacontable__codigo_categoria=self.cuentacontable.codigo_categoria),
                ).exclude(cuentacontable_id=self.cuentacontable.id).exists()

        elif self.cuentacontable.es_grupo():
            return CuentaFlujoEfectivoMensual.objects.filter(
                Q(actividadflujoefectivomensual__flujoefectivomensual=self.actividadflujoefectivomensual.flujoefectivomensual),
                Q(status=True),
                Q(cuentacontable__codigo_categoria=self.cuentacontable.codigo_categoria),
                Q(cuentacontable__codigo_grupo=self.cuentacontable.codigo_grupo),
                ).exclude(cuentacontable_id=self.cuentacontable.id).exists()
        elif self.cuentacontable.es_sub_grupo():
            return CuentaFlujoEfectivoMensual.objects.filter(
                Q(actividadflujoefectivomensual__flujoefectivomensual=self.actividadflujoefectivomensual.flujoefectivomensual),
                Q(status=True),
                Q(cuentacontable__codigo_categoria=self.cuentacontable.codigo_categoria),
                Q(cuentacontable__codigo_grupo=self.cuentacontable.codigo_grupo),
                Q(cuentacontable__codigo_subgrupo=self.cuentacontable.codigo_subgrupo),
                ).exclude(cuentacontable_id=self.cuentacontable.id).exists()
        elif self.cuentacontable.es_rubro():
            return CuentaFlujoEfectivoMensual.objects.filter(
                Q(actividadflujoefectivomensual__flujoefectivomensual=self.actividadflujoefectivomensual.flujoefectivomensual),
                Q(status=True),
                Q(cuentacontable__codigo_categoria=self.cuentacontable.codigo_categoria),
                Q(cuentacontable__codigo_grupo=self.cuentacontable.codigo_grupo),
                Q(cuentacontable__codigo_subgrupo=self.cuentacontable.codigo_subgrupo),
                Q(cuentacontable__codigo_rubro=self.cuentacontable.codigo_rubro),
            ).exclude(cuentacontable_id=self.cuentacontable.id).exists()
        elif  self.cuentacontable.es_subrubro():
            return CuentaFlujoEfectivoMensual.objects.filter(
                Q(actividadflujoefectivomensual__flujoefectivomensual=self.actividadflujoefectivomensual.flujoefectivomensual),
                Q(status=True),
                Q(cuentacontable__codigo_categoria=self.cuentacontable.codigo_categoria),
                Q(cuentacontable__codigo_grupo=self.cuentacontable.codigo_grupo),
                Q(cuentacontable__codigo_subgrupo=self.cuentacontable.codigo_subgrupo),
                Q(cuentacontable__codigo_rubro=self.cuentacontable.codigo_rubro),
                Q(cuentacontable__codigo_subrubro=self.cuentacontable.codigo_subrubro),
            ).exclude(cuentacontable_id=self.cuentacontable.id).exists()
        else:
            return False

    def recalcular_cuenta_padre_flujo_efectivo(self,request,cuentacontable):
        if cuentacontable.es_categoria():
            pass
        elif cuentacontable.es_grupo():
            # busco cuenta padre
            eCuentaFlujoEfectivoMensual = CuentaFlujoEfectivoMensual.objects.filter(status=True,actividadflujoefectivomensual__status=True,actividadflujoefectivomensual__flujoefectivomensual__status=True,
                                                                                    actividadflujoefectivomensual__flujoefectivomensual=self.actividadflujoefectivomensual.flujoefectivomensual,actividadflujoefectivomensual=self.actividadflujoefectivomensual,
                                                                                    cuentacontable__codigo_categoria=cuentacontable.codigo_categoria,
                                                                                    cuentacontable__codigo_grupo__isnull=True,
                                                                                    cuentacontable__codigo_subgrupo__isnull=True,
                                                                                    cuentacontable__codigo_rubro__isnull=True,
                                                                                    cuentacontable__codigo_subrubro__isnull=True)
            if eCuentaFlujoEfectivoMensual.exists():
                # si existe cuentas hijas sumo su valor
                eCuentaFlujoEfectivoMensual = eCuentaFlujoEfectivoMensual.first()
                eCuentaFlujoEfectivoMensual.valor = CuentaFlujoEfectivoMensual.objects.filter(
                    Q(actividadflujoefectivomensual__flujoefectivomensual=self.actividadflujoefectivomensual.flujoefectivomensual,actividadflujoefectivomensual=self.actividadflujoefectivomensual),
                    Q(status=True,actividadflujoefectivomensual__status=True,actividadflujoefectivomensual__flujoefectivomensual__status=True),
                    Q(cuentacontable__codigo_categoria=self.cuentacontable.codigo_categoria),
                    Q(cuentacontable__codigo_grupo__isnull=False),
                    Q(cuentacontable__codigo_subgrupo__isnull=True),
                    Q(cuentacontable__codigo_rubro__isnull=True),
                    Q(cuentacontable__codigo_subrubro__isnull=True),
                ).aggregate(total_valor=Sum('valor'))['total_valor']
                eCuentaFlujoEfectivoMensual.save(request)
                # si la cuenta padre tambien tiene padre repito el proceso enviando la cuenta padre para verificar si tiene padre
                self.recalcular_cuenta_padre_flujo_efectivo(request, eCuentaFlujoEfectivoMensual.cuentacontable)
        elif cuentacontable.es_sub_grupo():
            # busco cuenta padre
            eCuentaFlujoEfectivoMensual = CuentaFlujoEfectivoMensual.objects.filter(status=True,actividadflujoefectivomensual__status=True,actividadflujoefectivomensual__flujoefectivomensual__status=True,actividadflujoefectivomensual=self.actividadflujoefectivomensual,
                                                                                    actividadflujoefectivomensual__flujoefectivomensual=self.actividadflujoefectivomensual.flujoefectivomensual,
                                                                                    cuentacontable__codigo_categoria=cuentacontable.codigo_categoria,
                                                                                    cuentacontable__codigo_grupo=cuentacontable.codigo_grupo,
                                                                                    cuentacontable__codigo_subgrupo__isnull=True,
                                                                                    cuentacontable__codigo_rubro__isnull=True,
                                                                                    cuentacontable__codigo_subrubro__isnull=True)
            if eCuentaFlujoEfectivoMensual.exists():
                # si existe cuentas hijas sumo su valor
                eCuentaFlujoEfectivoMensual = eCuentaFlujoEfectivoMensual.first()
                eCuentaFlujoEfectivoMensual.valor = CuentaFlujoEfectivoMensual.objects.filter(
                    Q(actividadflujoefectivomensual__flujoefectivomensual=self.actividadflujoefectivomensual.flujoefectivomensual,actividadflujoefectivomensual=self.actividadflujoefectivomensual),
                    Q(status=True,actividadflujoefectivomensual__status=True,actividadflujoefectivomensual__flujoefectivomensual__status=True),
                    Q(cuentacontable__codigo_categoria=self.cuentacontable.codigo_categoria),
                    Q(cuentacontable__codigo_grupo=self.cuentacontable.codigo_grupo),
                    Q(cuentacontable__codigo_subgrupo__isnull=False),
                    Q(cuentacontable__codigo_rubro__isnull=True),
                    Q(cuentacontable__codigo_subrubro__isnull=True),
                ).aggregate(total_valor=Sum('valor'))['total_valor']
                eCuentaFlujoEfectivoMensual.save(request)
                # si la cuenta padre tambien tiene padre repito el proceso enviando la cuenta padre para verificar si tiene padre
                self.recalcular_cuenta_padre_flujo_efectivo(request, eCuentaFlujoEfectivoMensual.cuentacontable)
        elif cuentacontable.es_rubro():
            # busco cuenta padre
            eCuentaFlujoEfectivoMensual = CuentaFlujoEfectivoMensual.objects.filter(status=True,actividadflujoefectivomensual__status=True,actividadflujoefectivomensual__flujoefectivomensual__status=True,
                                                                                    actividadflujoefectivomensual__flujoefectivomensual=self.actividadflujoefectivomensual.flujoefectivomensual,actividadflujoefectivomensual=self.actividadflujoefectivomensual,
                                                                                    cuentacontable__codigo_categoria=cuentacontable.codigo_categoria,
                                                                                    cuentacontable__codigo_grupo=cuentacontable.codigo_grupo,
                                                                                    cuentacontable__codigo_subgrupo=cuentacontable.codigo_subgrupo,
                                                                                    cuentacontable__codigo_rubro__isnull=True,
                                                                                    cuentacontable__codigo_subrubro__isnull=True)
            if eCuentaFlujoEfectivoMensual.exists():
                # si existe cuentas hijas sumo su valor
                eCuentaFlujoEfectivoMensual = eCuentaFlujoEfectivoMensual.first()
                eCuentaFlujoEfectivoMensual.valor = CuentaFlujoEfectivoMensual.objects.filter(
                    Q(actividadflujoefectivomensual__flujoefectivomensual=self.actividadflujoefectivomensual.flujoefectivomensual,actividadflujoefectivomensual=self.actividadflujoefectivomensual),
                    Q(status=True,actividadflujoefectivomensual__status=True,actividadflujoefectivomensual__flujoefectivomensual__status=True),
                    Q(cuentacontable__codigo_categoria=self.cuentacontable.codigo_categoria),
                    Q(cuentacontable__codigo_grupo=self.cuentacontable.codigo_grupo),
                    Q(cuentacontable__codigo_subgrupo=self.cuentacontable.codigo_subgrupo),
                    Q(cuentacontable__codigo_rubro__isnull=False),
                    Q(cuentacontable__codigo_subrubro__isnull=True),
                ).aggregate(total_valor=Sum('valor'))['total_valor']
                eCuentaFlujoEfectivoMensual.save(request)
                # si la cuenta padre tambien tiene padre repito el proceso enviando la cuenta padre para verificar si tiene padre
                self.recalcular_cuenta_padre_flujo_efectivo(request, eCuentaFlujoEfectivoMensual.cuentacontable)
        elif cuentacontable.es_subrubro():
            #busco cuenta padre
            eCuentaFlujoEfectivoMensual = CuentaFlujoEfectivoMensual.objects.filter(status=True,
                                                                                    actividadflujoefectivomensual__status=True,
                                                                                    actividadflujoefectivomensual__flujoefectivomensual__status=True,actividadflujoefectivomensual=self.actividadflujoefectivomensual,
                                                                                    actividadflujoefectivomensual__flujoefectivomensual=self.actividadflujoefectivomensual.flujoefectivomensual,
                                                                                    cuentacontable__codigo_categoria=cuentacontable.codigo_categoria,
                                                                                    cuentacontable__codigo_grupo=cuentacontable.codigo_grupo,
                                                                                    cuentacontable__codigo_subgrupo=cuentacontable.codigo_subgrupo,
                                                                                    cuentacontable__codigo_rubro=cuentacontable.codigo_rubro,
                                                                                    cuentacontable__codigo_subrubro__isnull=True)
            if eCuentaFlujoEfectivoMensual.exists():
                # si existe cuentas hijas sumo su valor
                eCuentaFlujoEfectivoMensual = eCuentaFlujoEfectivoMensual.first()
                eCuentaFlujoEfectivoMensual.valor = CuentaFlujoEfectivoMensual.objects.filter(
                    Q(actividadflujoefectivomensual__flujoefectivomensual=self.actividadflujoefectivomensual.flujoefectivomensual,actividadflujoefectivomensual=self.actividadflujoefectivomensual),
                    Q(status=True,actividadflujoefectivomensual__status=True,actividadflujoefectivomensual__flujoefectivomensual__status=True),
                    Q(cuentacontable__codigo_categoria=self.cuentacontable.codigo_categoria),
                    Q(cuentacontable__codigo_grupo=self.cuentacontable.codigo_grupo),
                    Q(cuentacontable__codigo_subgrupo=self.cuentacontable.codigo_subgrupo),
                    Q(cuentacontable__codigo_rubro=self.cuentacontable.codigo_rubro),
                    Q(cuentacontable__codigo_subrubro__isnull=False),
                ).aggregate(total_valor=Sum('valor'))['total_valor']
                eCuentaFlujoEfectivoMensual.save(request)
                # si la cuenta padre tambien tiene padre repito el proceso enviando la cuenta padre para verificar si tiene padre
                self.recalcular_cuenta_padre_flujo_efectivo(request, eCuentaFlujoEfectivoMensual.cuentacontable)
        else:
            pass


    def actualizar_total_ingresos_por_actividad_flujoefectivo(self,request):
        actividad = self.actividadflujoefectivomensual
        actividad.total_ingresos = self.sumar_ingresos()
        actividad.save(request)

    def actualizar_total_egresos_por_actividad_flujoefectivo(self,request):
        actividad = self.actividadflujoefectivomensual
        actividad.total_egresos = self.sumar_egresos()
        actividad.save(request)

    def actualizar_resultado_por_actividad_flujoefectivo(self,request):
        actividad = self.actividadflujoefectivomensual
        actividad.resultado = actividad.total_ingresos - actividad.total_egresos
        actividad.save(request)

    def actualizar_superavit_flujoefectivo(self,request):
        superavit = 0
        eActividadFlujoEfectivoMensuals = ActividadFlujoEfectivoMensual.objects.filter(status=True,flujoefectivomensual__status=True,flujoefectivomensual = self.actividadflujoefectivomensual.flujoefectivomensual)
        for eActividadFlujoEfectivoMensual in eActividadFlujoEfectivoMensuals:
            superavit += eActividadFlujoEfectivoMensual.resultado

        flujoefectivomensual = self.actividadflujoefectivomensual.flujoefectivomensual
        flujoefectivomensual.superavit = superavit
        flujoefectivomensual.save(request)

    def sumar_ingresos(self):
        valor = 0
        eCuentaFlujoEfectivoMensuals = CuentaFlujoEfectivoMensual.objects.filter(status=True,
                                                                                actividadflujoefectivomensual__status=True,
                                                                                actividadflujoefectivomensual__flujoefectivomensual__status=True,
                                                                                actividadflujoefectivomensual__flujoefectivomensual=self.actividadflujoefectivomensual.flujoefectivomensual,
                                                                                actividadflujoefectivomensual=self.actividadflujoefectivomensual,
                                                                                cuentacontable__tipo = 1)
        for eCuentaFlujoEfectivoMensual in eCuentaFlujoEfectivoMensuals:
            if not eCuentaFlujoEfectivoMensual.cuenta_no_puede_ser_editada():
                valor += eCuentaFlujoEfectivoMensual.valor
        return valor


    def sumar_egresos(self):
        valor = 0
        eCuentaFlujoEfectivoMensuals = CuentaFlujoEfectivoMensual.objects.filter(status=True,
                                                                                 actividadflujoefectivomensual__status=True,
                                                                                 actividadflujoefectivomensual__flujoefectivomensual__status=True,
                                                                                 actividadflujoefectivomensual__flujoefectivomensual=self.actividadflujoefectivomensual.flujoefectivomensual,
                                                                                 actividadflujoefectivomensual=self.actividadflujoefectivomensual,
                                                                                 cuentacontable__tipo=2)
        for eCuentaFlujoEfectivoMensual in eCuentaFlujoEfectivoMensuals:
            if not eCuentaFlujoEfectivoMensual.cuenta_no_puede_ser_editada():
                valor += eCuentaFlujoEfectivoMensual.valor
        return valor

class ConfEstadoResultadoIntegral(ModeloBase):
    cuentacontable = models.ForeignKey(CuentaContable, on_delete=models.CASCADE, verbose_name=u'Configuración general  Cuenta Contable')

    class Meta:
        verbose_name = "Cuenta del estado de resultado"
        verbose_name_plural = "Cuentas del estado de resultado"

    def __str__(self):
        return f"{self.cuentacontable}"

class EstadoResultadoIntegral(ModeloBase):
    anio = models.IntegerField(default=0, verbose_name=u'Año')
    meses = models.TextField(default='', verbose_name=u'Meses')
    fecha = models.DateField(null=True, blank=True, verbose_name=u'Fecha')

    class Meta:
        verbose_name = "Estado de resultado integral"
        verbose_name_plural = "Estados de resultado integral"

    def set_meses(self, meses):
        self.meses = json.dumps(meses)

    def get_meses(self):
        return json.loads(self.meses)

    def get_rango_meses(self):
        return f"{self.get_meses()[0][1]} a {self.get_meses()[-1][1]}"

    def get_detalle_resultados(self):
        return self.detalleestadoresultadointegral_set.filter(status=True)


    def generar_reporte_estadoresultadointegral_excel(self,request):
        try:
            import io
            import xlsxwriter
            from pdip.funciones import FORMATOS_CELDAS_EXCEL
            from django.http import HttpResponse
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            ws = workbook.add_worksheet()

            ftitulo1 = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo1"])
            fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])
            textonegrita = workbook.add_format(FORMATOS_CELDAS_EXCEL["textonegrita"])

            ws.merge_range(0, 0, 0, 3, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo1)
            ws.merge_range(1, 0, 1, 3, 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADOS', ftitulo1)
            ws.merge_range(2, 0, 2, 3, f'ESTADO DE RESULTADO INTEGRAL', ftitulo1)
            ws.merge_range(3, 0, 3, 3, f'Desde {self.get_rango_meses()} del {self.anio} ', ftitulo1)
            columns = [
                (u"CÓDIGO", 30),
                (u"CUENTA CONTABLE", 160),
                (u"EJERCICIO VIGENTE", 25),
            ]

            row_num = 5
            for col_num in range(len(columns)):
                ws.write(row_num, col_num, columns[col_num][0], fcabeceracolumna)
                ws.set_column(col_num, col_num, columns[col_num][1])

            row_num += 1
            for detalle in self.get_detalle_resultados():
                # Merge row for each activity title
                ws.write(row_num, 0, detalle.cuentacontable.get_codigo_cuenta_contable, textonegrita)
                ws.write(row_num, 1, detalle.cuentacontable.nombre)
                ws.write(row_num, 2, detalle.valor)
                row_num += 1

            # Finalize workbook
            workbook.close()
            output.seek(0)
            filename = f'estado_resultado_integral_{self.pk}_{self.anio}_{self.get_rango_meses()}.xlsx'
            response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        except Exception as ex:
            raise

    def __str__(self):
        return f"{self.anio}"

class DetalleEstadoResultadoIntegral(ModeloBase):
    estado_resultado_integral = models.ForeignKey(EstadoResultadoIntegral, null=True, blank=True, on_delete=models.CASCADE, verbose_name=u'Estado de resultado integral')
    cuentacontable = models.ForeignKey(CuentaContable, null=True, blank=True, on_delete=models.CASCADE, verbose_name=u'Cuenta Contable')
    valor = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name=u'Valor')

    class Meta:
        verbose_name = "Detalle Estado Resultado Integral"
        verbose_name_plural = "Detalle Estado Resultado Integral"

    def __str__(self):
        return f"{self.cuentacontable}"


class ConfigEjecucionPresupuestaria(ModeloBase):
    cuentacontable = models.ForeignKey(CuentaContable, on_delete=models.CASCADE, verbose_name=u'Configuración general Cuenta Contable')

    class Meta:
        verbose_name = "Cuenta de ejecución presupuestaria"
        verbose_name_plural = "Cuentas de ejecución presupuestaria"

    def __str__(self):
        return f"{self.cuentacontable}"


class EjecucionPresupuestaria(ModeloBase):
    anio = models.IntegerField(default=0, verbose_name=u'Año')
    meses = models.TextField(default='', verbose_name=u'Meses')
    fecha = models.DateField(null=True, blank=True, verbose_name=u'Fecha')

    class Meta:
        verbose_name = "Ejecución presupuestaria"
        verbose_name_plural = "Ejecución presupuestaria"

    def __str__(self):
        return f"{self.anio}"

    def set_meses(self, meses):
        self.meses = json.dumps(meses)

    def get_meses(self):
        return json.loads(self.meses)

    def get_rango_meses(self):
        return f"{self.get_meses()[0][1]} a {self.get_meses()[-1][1]}"

    def get_detalle_resultados(self):
        return self.detalleejecucionpresupuestaria_set.filter(status=True)

    def generar_reporte_ejecucionpresupuestaria_excel(self,request):
        try:
            import io
            import xlsxwriter
            from pdip.funciones import FORMATOS_CELDAS_EXCEL
            from django.http import HttpResponse
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            ws = workbook.add_worksheet()

            ftitulo1 = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo1"])
            fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])
            textonegrita = workbook.add_format(FORMATOS_CELDAS_EXCEL["textonegrita"])

            ws.merge_range(0, 0, 0, 3, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo1)
            ws.merge_range(1, 0, 1, 3, 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADOS', ftitulo1)
            ws.merge_range(2, 0, 2, 3, f'REPORTE DE EFICIENCIA PRESUPUESTARIA', ftitulo1)
            columns = [
                (u"CÓDIGO", 30),
                (u"DENOMINACIÓN", 100),
                (u"CODIFICADO", 25),
                (u"DEVENGADO", 25),
                (u"SALDO", 25),
                (u"CATALOGO DE CUENTAS", 100),
            ]

            row_num = 4
            for col_num in range(len(columns)):
                ws.write(row_num, col_num, columns[col_num][0], fcabeceracolumna)
                ws.set_column(col_num, col_num, columns[col_num][1])

            row_num += 1
            for detalle in self.get_detalle_resultados():
                # Merge row for each activity title
                ws.write(row_num, 0, f"{detalle.cuentacontable.get_asociacion_presupuestaria()[0].clasificadorpresupuestario.get_codigo_clasificador_presupuestario}" if detalle.cuentacontable.get_asociacion_presupuestaria().first() else '' , textonegrita)
                ws.write(row_num, 1, f"{detalle.cuentacontable.get_asociacion_presupuestaria()[0].clasificadorpresupuestario.nombre}" if detalle.cuentacontable.get_asociacion_presupuestaria().first() else '')
                ws.write(row_num, 2, detalle.codificado)
                ws.write(row_num, 3, detalle.devengado)
                ws.write(row_num, 4, detalle.saldo)
                ws.write(row_num, 5, f"{detalle.cuentacontable.get_codigo_cuenta_contable}  -  {detalle.cuentacontable.nombre}" )
                row_num += 1

            # Finalize workbook
            workbook.close()
            output.seek(0)
            filename = f'ejecucion_presupuestaria_{self.pk}_{self.anio}_{self.get_rango_meses()}.xlsx'
            response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        except Exception as ex:
            raise

    @staticmethod
    def CrearActualizarEjecucionPresupuestaria():
        pass

class DetalleEjecucionPresupuestaria(ModeloBase):
    ejecucion_presupuestaria = models.ForeignKey(EjecucionPresupuestaria, on_delete=models.CASCADE, verbose_name=u'Ejecución presupuestaria')
    cuentacontable = models.ForeignKey(CuentaContable, on_delete=models.CASCADE, verbose_name=u'Cuenta Contable')
    codificado = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name=u'Codificado')
    devengado = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name=u'Devengado')
    saldo = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name=u'Saldo')

    def __str__(self):
        return f"{self.cuentacontable}"

    class Meta:
        verbose_name = "Detalle de ejecución presupuestaria"
        verbose_name_plural = "Detalles de ejecución presupuestaria"


class PuntoEquilibrio(ModeloBase):
    carrera = models.ForeignKey('sga.Carrera', on_delete=models.CASCADE, verbose_name=u'Carrera')
    valor_maestria = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name=u'Valor de la maestría')
    proyeccion_ventas = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name=u'Proyección de la maestría')
    valor_proyectado = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name=u'Valor proyectado')
    costo_variable = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name=u'Costo variable')
    costo_fijo = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name=u'Costo fijo')
    punto_equilibrio = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name=u'Punto de equilibrio')
    valor_punto_equilibrio = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name=u'Valor en dolares del punto de equilibrio')
    num_modulos = models.IntegerField(default=0, verbose_name=u'Número de módulos')

    class Meta:
        verbose_name = u"Punto de equilibrio"
        verbose_name_plural = u"Puntos de equilibrio"
        ordering = ['carrera']

    def __str__(self):
        return f'{self.carrera}'

    def calcular_valor_proyectado(self):
        self.valor_proyectado = self.valor_maestria * self.proyeccion_ventas

    def calculo_valores_punto_equilibrio(self):
        self.valor_proyectado = float(self.valor_maestria) * float(self.proyeccion_ventas)

        resta = float(self.valor_maestria) - float(self.costo_variable)
        if resta > 0:
            self.punto_equilibrio = float(self.costo_fijo) / resta
        self.valor_punto_equilibrio = float(self.punto_equilibrio) * float(self.valor_maestria)

    def get_superavit(self):
        superavit = self.valor_proyectado - self.valor_punto_equilibrio
        superavit_curso = superavit * self.num_modulos
        costo_modulos = self.costo_fijo / self.num_modulos if self.num_modulos > 0 else 0
        return {'superavit': superavit, 'superavit_curso': superavit_curso, 'costo_modulos': costo_modulos}


class DetalleFechasEvalDirMateria(ModeloBase):
    materia = models.ForeignKey('sga.Materia', on_delete=models.CASCADE, null=True, blank=True, verbose_name=u"Encuesta")
    inicio = models.DateField(blank=True, null=True, verbose_name=u'Inicio de la evaluación de directivos')
    fin = models.DateField(blank=True, null=True, verbose_name=u'Fin de la evaluación de directivos')

    class Meta:
        verbose_name = u"Detalle de Fechas de evaluación de directivos"
        verbose_name_plural = u"Detalles de Fechas de evaluación de directivos"
        ordering = ['id']

    def __str__(self):
        return f'{self.materia} - Inicio {self.inicio} - Fin {self.fin}'

class DetalleResultadosEvaluacionPosgrado(ModeloBase):
    materia = models.ForeignKey('sga.Materia', on_delete=models.CASCADE, null=True, blank=True, verbose_name=u"Modulo")
    procesado = models.BooleanField(default=False, verbose_name=u'¿Procesado correctamente?')
    descripcion = models.TextField(max_length=1000, verbose_name=u'Descripción de la ejecución')
    total = models.IntegerField(default=0,verbose_name=u'Cantidad hetero')
    auto = models.BooleanField(default=False, verbose_name=u'¿Autoevaluacion realizada?')
    director = models.BooleanField(default=False, verbose_name=u'¿Evaluador por Director?')
    coordinador = models.BooleanField(default=False, verbose_name=u'¿Evaluador por Coordinador?')

    class Meta:
        verbose_name = u"Detalle de resultados de procesamiento"
        verbose_name_plural = u"Detalles de resultados de procesamiento"
        ordering = ['id']

    def __str__(self):
        return f'{self.materia} - {self.total}'

class RespuestaEvaluacionAcreditacionPosgrado(ModeloBase):
    proceso = models.ForeignKey('sga.ProcesoEvaluativoAcreditacion', on_delete=models.CASCADE)
    tipoinstrumento = models.IntegerField(default=0, verbose_name=u'Instrumento')
    profesor = models.ForeignKey('sga.Profesor', on_delete=models.CASCADE)
    tipoprofesor = models.ForeignKey('sga.TipoProfesor', blank=True, null=True, verbose_name=u'Tipo Profesor', on_delete=models.CASCADE)
    evaluador = models.ForeignKey('sga.Persona', blank=True, null=True, on_delete=models.CASCADE)
    materia = models.ForeignKey('sga.Materia', blank=True, null=True, on_delete=models.CASCADE)
    materiaasignada = models.ForeignKey('sga.MateriaAsignada', blank=True, null=True, on_delete=models.CASCADE)
    coordinacion = models.ForeignKey('sga.Coordinacion', blank=True, null=True, on_delete=models.CASCADE)
    carrera = models.ForeignKey('sga.Carrera', blank=True, null=True, on_delete=models.CASCADE)
    fecha = models.DateTimeField()
    accionmejoras = models.TextField(default='', verbose_name=u'Mejoras')
    formacioncontinua = models.TextField(default='', verbose_name=u'Formación continua')
    valortotaldocencia = models.FloatField(default=0)
    valortotalinvestigacion = models.FloatField(default=0)
    valortotalgestion = models.FloatField(default=0)
    tipomejoras = models.ForeignKey('sga.TipoObservacionEvaluacion', related_name='tipmejo_set', verbose_name=u"Tipo mejoras", blank=True, null=True, on_delete=models.CASCADE)
    tipocontinua = models.ForeignKey('sga.TipoObservacionEvaluacion', related_name='tipconti_set', verbose_name=u"Tipo continua", blank=True, null=True, on_delete=models.CASCADE)
    tutoriaacademica = models.BooleanField(default=False, verbose_name=u"Para saber si el alumno tuvo tutoria academica en la materia, enotnces evalua rubrica de tutoria academica")
    procesada = models.BooleanField(default=False, verbose_name=u"Cuando esta true es porque ya fue recalculado")

    def __str__(self):
        return u'%s - %s - %s' % (elimina_tildes(self.profesor), self.evaluador if self.evaluador else '', self.materia.asignatura if self.materia else '')

    def valor_rubricapregunta_posgrado(self, rubrica, rubpregunta):
        try:
            detalleresrubrica = DetalleRespuestaRubricaPos.objects.filter(respuestarubrica__rubrica=rubrica,respuestarubrica__respuestaevaluacion=self, rubricapregunta=rubpregunta)
            if detalleresrubrica:
                valor = detalleresrubrica[0].valor
                justificacion = detalleresrubrica[0].justificacion  # Suponiendo que el campo se llama justificacion
                return {'valor': valor, 'justificacion': justificacion}
            else:
                return {'valor': 0, 'justificacion': ""}
        except Exception as ex:
            pass

    class Meta:
        unique_together = ('profesor', 'evaluador', 'materia', 'tipoprofesor',)
        ordering = ('profesor', 'evaluador')

class RespuestaRubricaPosgrado(ModeloBase):
    respuestaevaluacion = models.ForeignKey(RespuestaEvaluacionAcreditacionPosgrado, on_delete=models.CASCADE)
    rubrica = models.ForeignKey('sga.Rubrica', on_delete=models.CASCADE)
    valor = models.FloatField(default=0)

    class Meta:
        verbose_name = u"Respuesta Rubrica Posgrado"
        verbose_name_plural = u"Respuestas rubrica Posgrado"
        ordering = ['id']

class DetalleRespuestaRubricaPos(ModeloBase):
    respuestarubrica = models.ForeignKey(RespuestaRubricaPosgrado, on_delete=models.CASCADE)
    rubricapregunta = models.ForeignKey('sga.RubricaPreguntas', on_delete=models.CASCADE)
    valor = models.FloatField(default=0)
    justificacion = models.CharField(max_length=600, blank=True, null=True, verbose_name=u'Justificacion')

    class Meta:
        verbose_name = u"Detalle Respuesta Rubrica Posgrado"
        verbose_name_plural = u"Detalles Respuestas rubrica Posgrado"
        ordering = ['id']

class SagPosgradoPregunta(ModeloBase):
    nombre = models.CharField(max_length=1000, verbose_name=u"Nombre")
    descripcion = models.CharField(max_length=1000, verbose_name=u"Descripcion")

    def __str__(self):
        return u'%s' % self.nombre

class SagPosgradoPeriodo(ModeloBase):
    class TipoPeriodoEncuesta(models.IntegerChoices):
        PRIMERAENCUESTA = 1,"Primera encuesta"
        SEGUNDAENCUESTA = 2, "Segunda encuesta"
        TERCERAENCUESTA = 3, "Tercera encuesta"

    anio = models.IntegerField(default=0, verbose_name=u'Anio del periodo')
    tipoperiodo = models.IntegerField(choices=TipoPeriodoEncuesta.choices, default=TipoPeriodoEncuesta.PRIMERAENCUESTA, verbose_name=u'Tipo')
    nombre = models.CharField(max_length=150, verbose_name=u"Nombre")
    descripcion = models.CharField(max_length=150, verbose_name=u"Descripcion")
    fechainicio = models.DateField(verbose_name=u'Fecha incio')
    fechafin = models.DateField(verbose_name=u'Fecha fin')
    estado = models.BooleanField(default=False, verbose_name=u"Estado")

    def __str__(self):
        return u'%s - %s (%s)' % (self.nombre,self.get_tipoperiodo_display(),self.anio)

class SagPosgradoEncuesta(ModeloBase):
    sagposgradoperiodo = models.ForeignKey(SagPosgradoPeriodo, on_delete=models.CASCADE, verbose_name=u"Periodo")
    nombre = models.CharField(max_length=150, verbose_name=u"Nombre")
    descripcion = models.TextField(verbose_name=u"Descripcion")
    orden = models.IntegerField(default=0, verbose_name=u'Orden')
    estado = models.BooleanField(default=True, verbose_name=u"Estado")

    def __str__(self):
        return u'%s' % self.nombre

class SagPosgradoEncuestaCarrera(ModeloBase):
    sagposgradoencuesta = models.ForeignKey(SagPosgradoEncuesta, on_delete=models.CASCADE, verbose_name=u"Encuesta")
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, verbose_name=u"Carrera")

    def __str__(self):
        return u'%s %s' % (self.sagposgradoencuesta.nombre, self.carrera.nombre_completo())



class PersonaDataPosgrado(ModeloBase):
    persona = models.ForeignKey('sga.Persona', null=True, blank=True, verbose_name=u'Persona', on_delete=models.CASCADE)
    nombres = models.CharField(default='', max_length=100, verbose_name=u'Nombre')
    apellido1 = models.CharField(default='', max_length=50, verbose_name=u"1er Apellido")
    apellido2 = models.CharField(default='', max_length=50, verbose_name=u"2do Apellido")
    cedula = models.CharField(default='', max_length=20, verbose_name=u"Cedula", blank=True, db_index=True)
    pasaporte = models.CharField(default='', max_length=20, blank=True, verbose_name=u"Pasaporte", db_index=True)
    nacimiento = models.DateField(verbose_name=u"Fecha de nacimiento o constitución")
    sexo = models.ForeignKey("sga.Sexo", default=2, verbose_name=u'Sexo', on_delete=models.CASCADE)
    nacionalidad = models.CharField(default='', max_length=100, verbose_name=u'Nacionalidad')
    paisnacionalidad = models.ForeignKey("sga.Pais", blank=True, null=True, related_name='+', verbose_name=u'País de nacionalidad', on_delete=models.CASCADE)
    pais = models.ForeignKey("sga.Pais", blank=True, null=True, related_name='+', verbose_name=u'País residencia', on_delete=models.CASCADE)
    provincia = models.ForeignKey("sga.Provincia", blank=True, null=True, related_name='+', verbose_name=u"Provincia de residencia", on_delete=models.CASCADE)
    canton = models.ForeignKey("sga.Canton", blank=True, null=True, related_name='+', verbose_name=u"Canton de residencia", on_delete=models.CASCADE)
    parroquia = models.ForeignKey("sga.Parroquia", blank=True, null=True, related_name='+', verbose_name=u"Parroquia de residencia", on_delete=models.CASCADE)
    ciudadela = models.CharField(default='', max_length=300, verbose_name=u"Ciudadela")
    sector = models.CharField(default='', max_length=300, verbose_name=u"Sector de residencia")
    zona = models.IntegerField(choices=ZONA_DOMICILIO, blank=True, null=True, verbose_name=u'Zona de domicilio')
    ciudad = models.CharField(default='', max_length=50, verbose_name=u"Ciudad de residencia")
    direccion = models.CharField(default='', max_length=300, verbose_name=u"Calle principal")
    direccion2 = models.CharField(default='', max_length=300, verbose_name=u"Calle secundaria")
    num_direccion = models.CharField(default='', max_length=15, verbose_name=u"Numero")
    referencia = models.CharField(default='', max_length=100, verbose_name=u"Referencia")
    telefono = models.CharField(default='', max_length=50, verbose_name=u"Telefono movil")
    telefono_conv = models.CharField(default='', max_length=50, verbose_name=u"Telefono fijo")
    email = models.CharField(default='', max_length=200, verbose_name=u"Correo electronico personal")
    emailinst = models.CharField(default='', max_length=200, verbose_name=u"Correo electronico institucional")
    graduado = models.BooleanField(default=False, verbose_name=u'Graduado')
    registradosistema = models.BooleanField(default=False, verbose_name=u'Registrado sistema')
    sinregistrosistema = models.BooleanField(default=False, verbose_name=u'Sin registro sistema')

    def __str__(self):
        return u'%s %s %s' % (self.apellido1, self.apellido2, self.nombres)

    def nombre_minus(self):
        try:
            nombreslist = self.nombres.split(' ')
            nombrepersona = self.nombres.capitalize()
            if len(nombreslist) == 2:
                nombrepersona = '{} {}'.format(str(nombreslist[0]).capitalize(), str(nombreslist[1]).capitalize())
                return u'%s' % (nombrepersona)
            elif len(nombreslist) == 3:
                nombrepersona = '{} {} {}'.format(str(nombreslist[0]).capitalize(), str(nombreslist[1]).capitalize(), str(nombreslist[2]).capitalize())
                return u'%s' % (nombrepersona)
            else:
                return u'%s' % (nombrepersona)
        except Exception as ex:
            return self.nombres.capitalize()


    def nombre_completo_minus(self):
        apellido1list = self.apellido1.split(' ')
        apellido1 = self.apellido1.capitalize()
        if len(apellido1list) == 2:
            apellido1 = '{} {}'.format(str(apellido1list[0]).capitalize(), str(apellido1list[1]).capitalize())
        elif len(apellido1list) == 3:
            apellido1 = '{} {} {}'.format(str(apellido1list[0]).capitalize(), str(apellido1list[1]).capitalize(),
                                          str(apellido1list[2]).capitalize())
        apellido2list = self.apellido2.split(' ')
        apellido2 = self.apellido2.capitalize()
        if len(apellido2list) == 2:
            apellido2 = '{} {}'.format(str(apellido2list[0]).capitalize(), str(apellido2list[1]).capitalize())
        elif len(apellido2list) == 3:
            apellido2 = '{} {} {}'.format(str(apellido2list[0]).capitalize(), str(apellido2list[1]).capitalize(),
                                          str(apellido2list[2]).capitalize())
        completo = '{} {} {}'.format(str(self.nombre_minus()), str(apellido1), str(apellido2))
        return u'%s' % (completo)

    def get_programas_posgrados(self):
            return self.personadataposgradoprograma_set.filter(status=True)

    class Meta:
        verbose_name = u"PersonaDataPosgrado"
        verbose_name_plural = u"PersonaDataPosgrado"
        ordering = ['id']

class PersonaDataPosgradoPrograma(ModeloBase):
    persona = models.ForeignKey(PersonaDataPosgrado, verbose_name=u'Persona data posgrado', on_delete=models.CASCADE)
    inscripcion = models.ForeignKey("sga.Inscripcion", blank=True, null=True, verbose_name=u'Inscripción', on_delete=models.CASCADE)
    carrera = models.ForeignKey('sga.Carrera',  verbose_name=u'Carrera', on_delete=models.CASCADE)
    fechagraduado = models.DateField(verbose_name=u"Fecha de graduación")

    def __str__(self):
        return u'%s' % (self.persona)

    class Meta:
        verbose_name = u"PersonaDataPosgradoPrograma"
        verbose_name_plural = u"PersonaDataPosgradoPrograma"
        ordering = ['id']
