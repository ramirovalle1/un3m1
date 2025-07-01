
import io
import os
import sys
import xlsxwriter
import xlwt
import openpyxl
from xlwt import *

# SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
# print(f"YOUR_PATH: {YOUR_PATH}")
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
# print(f"SITE_ROOT: {SITE_ROOT}")
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
# print(f"your_djangoproject_home: {your_djangoproject_home}")
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from django.http import HttpResponse
from settings import MEDIA_ROOT, BASE_DIR
from xlwt import easyxf, XFStyle
from sga.adm_criteriosactividadesdocente import asistencia_tutoria
from inno.models import *
from sga.models import *
from sagest.models import *
from Moodle_Funciones import buscarQuiz, estadoQuizIndividual, accesoQuizIndividual

"""
matriculas=Matricula.objects.filter(status=True,nivel__periodo_id=177)
# recorrer las materias de cada matricula
for matricula in matriculas:
    for materia in matricula.materiaasignada_set.filter(status=True):
        if materia.materia.asignaturamalla.asignaturamallapredecesora_set.filter(status=True):
            if Rubro.objects.filter(status=True,matricula=matricula):
                print(materia, 'Si tiene rubro')
            else:
                print(materia)
"""

"""
rubros = Rubro.objects.filter(status=True,cancelado=False).order_by('-id')[:100]
for rubro in rubros:
    rubro.status=False
    rubro.save()
    print(f'Rubro {rubro.nombre}, persona {rubro.persona}, cedula {rubro.persona.cedula}')
"""
#0944334762
"""
def activar_rubros():
    rubros = Rubro.objects.filter(status=False,pk__in=[660950,660984,660985,657725,661129])
    # rubros = Rubro.objects.filter(status=False,pk__in=[658837])
    for rubro in rubros:
        print("{}".format(rubro.persona))
        if not rubro.tiene_pagos() and not rubro.bloqueado:
            rubro.status = True
            rubro.save()


        else:
            print("NO SE PUEDE ELIMINAR POR QUE TIENE PAGOS O ESTA BLOQUEADO")


def liquidar_rubros():
    rubros = Rubro.objects.filter(status=True,pk__in=[660950,660984,660985,657725,612646,661129])
    for rubro in rubros:
        if not rubro.bloqueado:
            subtotal0 = 0
            subtotaliva = 0
            iva = 0
            if rubro.iva.porcientoiva > 0:
                subtotaliva = Decimal(rubro.saldo / (rubro.iva.porcientoiva + 1)).quantize(
                    Decimal('.01'))
                iva = Decimal(rubro.saldo - subtotaliva).quantize(Decimal('.01'))
            else:
                subtotal0 = rubro.saldo

            pago = Pago(rubro=rubro,
                        fecha=datetime.now().date(),
                        subtotal0=subtotal0,
                        subtotaliva=subtotaliva,
                        iva=iva,
                        valordescuento=0,
                        valortotal=rubro.saldo,
                        efectivo=False)
            pago.save()
            liquidacion = PagoLiquidacion(fecha=datetime.now().date(),
                                          motivo='Liquidación de rubro autorizado por GTA por 2da matrícula de titulación',
                                          valor=rubro.saldo)
            liquidacion.save()
            liquidacion.pagos.add(pago)
            rubro.save()

        else:
            print('tiene rubro bloqueado')
    print('fin')

activar_rubros()
liquidar_rubros()

"""
'''
def actualizar_criteriosdocencia(periodo):
    per = Periodo.objects.get(id=periodo)
    distributivos = ProfesorDistributivoHoras.objects.filter(status=True, coordinacion__id__in=[1, 2, 3, 4, 5, 9])
    try:
    # APOYO AL PROCESO DE ASIGNATURAS TRANSVERSALES ----->164
        for distributivo in distributivos:
            detalle = distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo__criterio_id=166).first()
            if detalle.values('id').exists():
                detalle = distributivo.detalle_horas_docencia().get(criteriodocenciaperiodo__criterio_id=166)
                actividades = ActividadDetalleDistributivo.objects.filter(status=True, criterio=detalle )
                detalle.save()
                for actividad in actividades:
                    if not ActividadDetalleDistributivo.objects.filter(status=True, criterio=detalle).exists():
                        act = ActividadDetalleDistributivo(criterio=detalle, nombre=detalle.criteriodocenciaperiodo.criterio.nombre)
                        act.save()
                    if str(actividad.nombre) == '':
                        actividad.nombre ='APOYO AL PROCESO DE ASIGNATURAS TRANSVERSALES'
                        actividad.save()

                    print('Nombre de actividad distributivo actualizada', distributivo.profesor.persona.nombre_completo_minus(), actividad.nombre)
    except Exception as ex:
        print(ex)

'''
def actualizar_criteriosdocencia(criterio):
    #criterioDoc = CriterioDocenciaPeriodo.objects.filter(criterio__id=criterio, periodo__id=177)
    #detalledis = DetalleDistributivo.objects.filter(criteriodocenciaperiodo__id__in=criterioDoc.all())
    distributivos = ProfesorDistributivoHoras.objects.filter(status=True, periodo_id=177)

    try:
        for distributivo in distributivos:
            detalle = distributivo.detalle_horas_docencia().filter(criteriodocenciaperiodo__criterio_id=criterio)
            if detalle.values('id').exists():
                cr = CriterioDocenciaPeriodo.objects.filter(status=True, criterio_id=164, periodo_id=177).first()
                if not cr:
                    raise NameError('Criterio no encontrado')
                detalle.update(criteriodocenciaperiodo=cr)
                detalle = detalle.first()
                actividades = ActividadDetalleDistributivo.objects.filter(status=True, criterio=detalle)

                for actividad in actividades:
                    actividad.nombre = "APOYO AL PROCESO DE ASIGNATURAS TRANSVERSALES"
                    actividad.save()
                print('criterio actualizado', distributivo.profesor.persona.nombre_completo_minus(), detalle.nombre)

    except Exception as ex:
        print(ex)

actualizar_criteriosdocencia(166)






