
#!/usr/bin/env python
import os
import sys


# SITE_ROOT = os.path.dirname(os.path.realpath(_file_))

# your_djangoproject_home = os.path.split(SITE_ROOT)[0]
# sys.path.append(your_djangoproject_home)
import xlrd
from django.core.wsgi import get_wsgi_application

from Moodle_Funciones import updaterubroepunemi

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from sga.models import *
from posgrado.models import *
from sagest.models import *

unidad = UnidadesPeriodo.objects.filter(periodo_id=112, orden=4, status=True).order_by('-fechasemanasfin')[0]
# print(unidad.fechafin)
listadomaterias = Materia.objects.filter(nivel__periodo_id=112, status=True)
contamateria = 0
for mate in listadomaterias:
    contamateria = contamateria + 1
    silabossemanal = DetalleSilaboSemanalTema.objects.values_list('silabosemanal_id', flat=True).filter(temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden=unidad.orden,silabosemanal__fechainiciosemana__gte=unidad.fechasemanasinicio,silabosemanal__fechafinciosemana__lte=unidad.fechasemanasfin, silabosemanal__silabo__materia=mate, silabosemanal__silabo__status=True, status=True)
    # print(silabossemanal.query)
    listapresentaciones = DiapositivaSilaboSemanal.objects.filter(iddiapositivamoodle__gt=0, silabosemanal_id__in=silabossemanal ,status=True)
    listacompendios = CompendioSilaboSemanal.objects.filter(idmcompendiomoodle__gt=0, silabosemanal_id__in=silabossemanal ,status=True)
    listaguiaestudiantes = GuiaEstudianteSilaboSemanal.objects.filter(idguiaestudiantemoodle__gt=0, silabosemanal_id__in=silabossemanal ,status=True)
    listaguiadocentes = GuiaDocenteSilaboSemanal.objects.filter(idguiadocentemoodle__gt=0, silabosemanal_id__in=silabossemanal ,status=True)
    listamateriales = MaterialAdicionalSilaboSemanal.objects.filter(idmaterialesmoodle__gt=0, silabosemanal_id__in=silabossemanal ,status=True)
    listavideomagistrales = VideoMagistralSilaboSemanal.objects.filter(idvidmagistralmoodle__gt=0, silabosemanal_id__in=silabossemanal ,status=True)
    listadoestudiantes = mate.materiaasignada_set.filter(status=True)
    contadorestudiantes = 0
    for estudiantes in listadoestudiantes:
        contadorestudiantes = contadorestudiantes + 1
        for presentacion in listapresentaciones:
            justificar = False
            if presentacion.fecha_creacion.date() > unidad.fechasemanasfin:
                justificar = True

            if AsistenciaMoodle.objects.filter(materiaasignada=estudiantes,presentacion=presentacion, status=True, unidad=unidad.orden).exists():
                if AsistenciaMoodle.objects.filter(materiaasignada=estudiantes,presentacion=presentacion, asistencia=False, status=True, unidad=unidad.orden).exists():
                    # asi = AsistenciaMoodle.objects.filter(materiaasignada=estudiantes,presentacion=presentacion, asistencia=False, status=True, unidad=unidad.orden)
                    asistenciamoodle = AsistenciaMoodle.objects.get(materiaasignada=estudiantes, presentacion=presentacion, unidad=unidad.orden)
                    verifica = estudiantes.verificaacceso(asistenciamoodle.id, unidad.fechasemanasinicio, unidad.fechasemanasfin, mate.idcursomoodle, 7, asistenciamoodle.presentacion.iddiapositivamoodle, justificaasistencia=justificar)
            else:
                asistencia = AsistenciaMoodle(materiaasignada=estudiantes,
                                              presentacion=presentacion,
                                              unidad=unidad.orden)
                asistencia.save()
                if AsistenciaMoodle.objects.filter(materiaasignada=estudiantes,presentacion=presentacion, asistencia=False, status=True, unidad=unidad.orden).exists():
                    asistenciamoodle = AsistenciaMoodle.objects.get(materiaasignada=estudiantes, presentacion=presentacion, unidad=unidad.orden)
                    verifica = estudiantes.verificaacceso(asistenciamoodle.id, unidad.fechasemanasinicio, unidad.fechasemanasfin, mate.idcursomoodle, 7, asistenciamoodle.presentacion.iddiapositivamoodle, justificaasistencia=justificar)

        for compendio in listacompendios:
            justificar = False
            if compendio.fecha_creacion.date() > unidad.fechasemanasfin:
                justificar = True
            if AsistenciaMoodle.objects.filter(materiaasignada=estudiantes,compendio=compendio, status=True, unidad=unidad.orden).exists():
                if AsistenciaMoodle.objects.filter(materiaasignada=estudiantes,compendio=compendio, asistencia=False, status=True, unidad=unidad.orden).exists():
                    asistenciamoodle = AsistenciaMoodle.objects.get(materiaasignada=estudiantes, compendio=compendio, unidad=unidad.orden)
                    verifica = estudiantes.verificaacceso(asistenciamoodle.id, unidad.fechasemanasinicio, unidad.fechasemanasfin, mate.idcursomoodle, 6, asistenciamoodle.compendio.idmcompendiomoodle, justificaasistencia=justificar)
            else:
                asistencia = AsistenciaMoodle(materiaasignada=estudiantes,
                                              compendio=compendio,
                                              unidad=unidad.orden)
                asistencia.save()
                if AsistenciaMoodle.objects.filter(materiaasignada=estudiantes,compendio=compendio, asistencia=False, status=True, unidad=unidad.orden).exists():
                    asistenciamoodle = AsistenciaMoodle.objects.get(materiaasignada=estudiantes, compendio=compendio, unidad=unidad.orden)
                    verifica = estudiantes.verificaacceso(asistenciamoodle.id, unidad.fechasemanasinicio, unidad.fechasemanasfin, mate.idcursomoodle, 6, asistenciamoodle.compendio.idmcompendiomoodle, justificaasistencia=justificar)

        for guiaestudiante in listaguiaestudiantes:
            justificar = False
            if guiaestudiante.fecha_creacion.date() > unidad.fechasemanasfin:
                justificar = True
            if AsistenciaMoodle.objects.filter(materiaasignada=estudiantes,guiaestudiante=guiaestudiante, status=True, unidad=unidad.orden).exists():
                if AsistenciaMoodle.objects.filter(materiaasignada=estudiantes,guiaestudiante=guiaestudiante, asistencia=False, status=True, unidad=unidad.orden).exists():
                    asistenciamoodle = AsistenciaMoodle.objects.get(materiaasignada=estudiantes, guiaestudiante=guiaestudiante, unidad=unidad.orden)
                    verifica = estudiantes.verificaacceso(asistenciamoodle.id, unidad.fechasemanasinicio, unidad.fechasemanasfin, mate.idcursomoodle, 10, asistenciamoodle.guiaestudiante.idguiaestudiantemoodle, justificaasistencia=justificar)
            else:
                asistencia = AsistenciaMoodle(materiaasignada=estudiantes,
                                              guiaestudiante=guiaestudiante,
                                              unidad=unidad.orden)
                asistencia.save()
                if AsistenciaMoodle.objects.filter(materiaasignada=estudiantes,guiaestudiante=guiaestudiante, asistencia=False, status=True, unidad=unidad.orden).exists():
                    asistenciamoodle = AsistenciaMoodle.objects.get(materiaasignada=estudiantes, guiaestudiante=guiaestudiante, unidad=unidad.orden)
                    verifica = estudiantes.verificaacceso(asistenciamoodle.id, unidad.fechasemanasinicio, unidad.fechasemanasfin, mate.idcursomoodle, 10, asistenciamoodle.guiaestudiante.idguiaestudiantemoodle, justificaasistencia=justificar)

        for guiadocente in listaguiadocentes:
            justificar = False
            if guiadocente.fecha_creacion.date() > unidad.fechasemanasfin:
                justificar = True
            if AsistenciaMoodle.objects.filter(materiaasignada=estudiantes,guiadocente=guiadocente, status=True, unidad=unidad.orden).exists():
                if AsistenciaMoodle.objects.filter(materiaasignada=estudiantes,guiadocente=guiadocente, asistencia=False, status=True, unidad=unidad.orden).exists():
                    asistenciamoodle = AsistenciaMoodle.objects.get(materiaasignada=estudiantes, guiadocente=guiadocente, unidad=unidad.orden)
                    verifica = estudiantes.verificaacceso(asistenciamoodle.id, unidad.fechasemanasinicio, unidad.fechasemanasfin, mate.idcursomoodle, 10, asistenciamoodle.guiadocente.idguiadocentemoodle, justificaasistencia=justificar)
            else:
                asistencia = AsistenciaMoodle(materiaasignada=estudiantes,
                                              guiadocente=guiadocente,
                                              unidad=unidad.orden)
                asistencia.save()
                if AsistenciaMoodle.objects.filter(materiaasignada=estudiantes,guiadocente=guiadocente, asistencia=False, status=True, unidad=unidad.orden).exists():
                    asistenciamoodle = AsistenciaMoodle.objects.get(materiaasignada=estudiantes, guiadocente=guiadocente, unidad=unidad.orden)
                    verifica = estudiantes.verificaacceso(asistenciamoodle.id, unidad.fechasemanasinicio, unidad.fechasemanasfin, mate.idcursomoodle, 10, asistenciamoodle.guiadocente.idguiadocentemoodle, justificaasistencia=justificar)

        for material in listamateriales:
            justificar = False
            if material.fecha_creacion.date() > unidad.fechasemanasfin:
                justificar = True
            if AsistenciaMoodle.objects.filter(materiaasignada=estudiantes,material=material, status=True, unidad=unidad.orden).exists():
                if AsistenciaMoodle.objects.filter(materiaasignada=estudiantes,material=material, asistencia=False, status=True, unidad=unidad.orden).exists():
                    asistenciamoodle = AsistenciaMoodle.objects.get(materiaasignada=estudiantes, material=material, unidad=unidad.orden)
                    verifica = estudiantes.verificaacceso(asistenciamoodle.id, unidad.fechasemanasinicio, unidad.fechasemanasfin, mate.idcursomoodle, 9, asistenciamoodle.material.idmaterialesmoodle, justificaasistencia=justificar)
            else:
                asistencia = AsistenciaMoodle(materiaasignada=estudiantes,
                                              material=material,
                                              unidad=unidad.orden)
                asistencia.save()
                if AsistenciaMoodle.objects.filter(materiaasignada=estudiantes,material=material, asistencia=False, status=True, unidad=unidad.orden).exists():
                        asistenciamoodle = AsistenciaMoodle.objects.get(materiaasignada=estudiantes, material=material, unidad=unidad.orden)
                        # print(str(asistenciamoodle.id) + '-' + str(unidad.fechasemanasinicio) + '-' + str(unidad.fechasemanasfin) + '-' + str(mate.idcursomoodle) + '-' + str(9) + '-' + str( asistenciamoodle.material.idmaterialesmoodle))
                        verifica = estudiantes.verificaacceso(asistenciamoodle.id, unidad.fechasemanasinicio, unidad.fechasemanasfin, mate.idcursomoodle, 9, asistenciamoodle.material.idmaterialesmoodle, justificaasistencia=justificar)

        for videomagistral in listavideomagistrales:
            justificar = False
            if videomagistral.fecha_creacion.date() > unidad.fechasemanasfin:
                justificar = True
            if AsistenciaMoodle.objects.filter(materiaasignada=estudiantes,videomagistral=videomagistral, status=True, unidad=unidad.orden).exists():
                if AsistenciaMoodle.objects.filter(materiaasignada=estudiantes,videomagistral=videomagistral, asistencia=False, status=True, unidad=unidad.orden).exists():
                    asistenciamoodle = AsistenciaMoodle.objects.get(materiaasignada=estudiantes, videomagistral=videomagistral, unidad=unidad.orden)
                    verifica = estudiantes.verificaacceso(asistenciamoodle.id, unidad.fechasemanasinicio, unidad.fechasemanasfin, mate.idcursomoodle, 8, asistenciamoodle.videomagistral.idvidmagistralmoodle, justificaasistencia=justificar)
            else:
                asistencia = AsistenciaMoodle(materiaasignada=estudiantes,
                                              videomagistral=videomagistral,
                                              unidad=unidad.orden)
                asistencia.save()
                if AsistenciaMoodle.objects.filter(materiaasignada=estudiantes,videomagistral=videomagistral, asistencia=False, status=True, unidad=unidad.orden).exists():
                        asistenciamoodle = AsistenciaMoodle.objects.get(materiaasignada=estudiantes, videomagistral=videomagistral, unidad=unidad.orden)
                        verifica = estudiantes.verificaacceso(asistenciamoodle.id, unidad.fechasemanasinicio, unidad.fechasemanasfin, mate.idcursomoodle, 8, asistenciamoodle.videomagistral.idvidmagistralmoodle, justificaasistencia=justificar)

    print('Codmateria ' + str(mate.id) +' Completando ' + str(contamateria) + ' de ' + str(listadomaterias.count()) + ' | Completado ' + str(round(null_to_numeric((contamateria/listadomaterias.count())*100),2)) + '% de 100%' )


