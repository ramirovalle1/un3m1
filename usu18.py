#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

import pyqrcode
from django.db import transaction
from django.http import HttpResponse


SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
import xlrd
from time import sleep
from sga.models import *
from sagest.models import *
from posgrado.models import *
from Moodle_Funciones import *
from datetime import date
from settings import PROFESORES_GROUP_ID, DEBUG, ADMINISTRADOR_ID, USA_TIPOS_INSCRIPCIONES, TIPO_INSCRIPCION_INICIAL, \
    DIAS_MATRICULA_EXPIRA
from sga.funciones import calculate_username, generar_usuario, fechatope, null_to_decimal
import xlwt
from xlwt import *
import unicodedata
from bd.models import CHOICES_FUNCION_DETALLE_REQUISITO
periodo = Periodo.objects.filter(pk=224)
from sga.funcionesxhtml2pdf import download_html_to_pdf, conviert_html_to_pdfsaveqrsilabo


def convertirfecha2(fecha):
    try:
        return date(int(fecha[0:4]), int(fecha[5:7]), int(fecha[8:10]))
    except Exception as ex:
        return datetime.now().date()


from moodle import moodle


def fechatope(fecha):
    contador = 0
    nuevafecha = fecha
    while contador < DIAS_MATRICULA_EXPIRA:
        nuevafecha = nuevafecha + timedelta(1)
        if nuevafecha.weekday() != 5 and nuevafecha.weekday() != 6:
            contador += 1
    return nuevafecha

import datetime

def aprendizajestemassilabo(lista_items1, idevaluacionaprendizaje, idsilabosemanal, ordenado):
    if lista_items1:
        if EvaluacionAprendizajeSilaboSemanal.objects.filter(evaluacionaprendizaje_id=idevaluacionaprendizaje, silabosemanal_id=idsilabosemanal, tipoactividadsemanal=1, status=True):
            evaluaciontema = EvaluacionAprendizajeSilaboSemanal.objects.get(evaluacionaprendizaje_id=idevaluacionaprendizaje, silabosemanal_id=idsilabosemanal, tipoactividadsemanal=1, status=True)
        else:
            evaluaciontema = EvaluacionAprendizajeSilaboSemanal(evaluacionaprendizaje_id=idevaluacionaprendizaje, silabosemanal_id=idsilabosemanal, tipoactividadsemanal=1, numactividad=ordenado)
            evaluaciontema.save()
        # for lista in lista_items1:
        if not EvaluacionAprendizajeTema.objects.filter(evaluacion=evaluaciontema, temasemanal_id=lista_items1, status=True):
            ingresoaprendizaje = EvaluacionAprendizajeTema(evaluacion=evaluaciontema, temasemanal_id=lista_items1)
            ingresoaprendizaje.save()



# codigos materia lenguaje
codigosmateriainvestigacion = [1406,
1411,
2670,
3278,
3420,
3750,
3812,
3859,
4443,
4780,
4820
]
silaboxduplicar = Silabo.objects.filter(materia_id=70723)[0]
listadoprofesormateria1 = ProfesorMateria.objects.filter(materia__nivel__periodo_id=224, tipoprofesor_id=16,materia__modeloevaluativo_id=27, status=True, materia__asignaturamalla__asignatura_id__in=codigosmateriainvestigacion).exclude(materia_id__in=[70723])
print(listadoprofesormateria1.count())
cuenta = 0
# for lmateriaprofesor in listadoprofesormateria1:
#     cuenta = cuenta + 1
#     if Silabo.objects.filter(materia=lmateriaprofesor.materia, status=True):
#         silaboaduplicar = Silabo.objects.filter(materia=lmateriaprofesor.materia, status=True)[0]
#         silaboaduplicar.delete()
#         print(cuenta)
c = 1
listadoprofesormateria = ProfesorMateria.objects.filter(materia__nivel__periodo_id=224, tipoprofesor_id=16,materia__modeloevaluativo_id=27,status=True, materia__asignaturamalla__asignatura_id__in=codigosmateriainvestigacion).exclude(materia_id__in=[70723])
print(listadoprofesormateria.count())

#PROCESO
contador = 0
if c == 1:
    for lmateriaprofesor in listadoprofesormateria:
        listadostestmigrar = []
        contador = contador + 1
        print(str(contador) + ' de ' + str(listadoprofesormateria.count()))
        if not Silabo.objects.filter(materia=lmateriaprofesor.materia, status=True):
            if ProgramaAnaliticoAsignatura.objects.filter(asignaturamalla=lmateriaprofesor.materia.asignaturamalla, status=True, activo=True):
                programa=ProgramaAnaliticoAsignatura.objects.filter(asignaturamalla=lmateriaprofesor.materia.asignaturamalla, status=True, activo=True)[0]
                nuevosilabo = Silabo(materia=lmateriaprofesor.materia,
                                     profesor=lmateriaprofesor.profesor,
                                     programaanaliticoasignatura=programa)
                nuevosilabo.save()
        if Silabo.objects.filter(materia=lmateriaprofesor.materia, status=True):
            silaboaduplicar = Silabo.objects.filter(materia=lmateriaprofesor.materia, status=True)[0]
            if not silaboaduplicar.silabosemanal_set.filter(status=True).exists():
                if silaboaduplicar.materia.tiene_cronograma():
                    planificacionsilaboact = PlanificacionClaseSilabo.objects.filter(tipoplanificacion__planificacionclasesilabo_materia__materia=silaboaduplicar.materia, examen=False, status=True).exclude(semana=0).order_by('orden')
                    for pact in planificacionsilaboact:
                        if PlanificacionClaseSilabo.objects.filter(tipoplanificacion__planificacionclasesilabo_materia__materia=silaboxduplicar.materia, status=True, semana=pact.semana):
                            pant = PlanificacionClaseSilabo.objects.filter(tipoplanificacion__planificacionclasesilabo_materia__materia=silaboxduplicar.materia, status=True, semana=pact.semana)[0]
                            if silaboxduplicar.silabosemanal_set.filter(status=True, fechainiciosemana__gte=pant.fechainicio, fechafinciosemana__lte=pant.fechafin).exists():
                                semana = silaboxduplicar.silabosemanal_set.filter(status=True, fechainiciosemana__gte=pant.fechainicio, fechafinciosemana__lte=pant.fechafin)[0]
                                if semana:
                                    silabosemana = SilaboSemanal(silabo=silaboaduplicar,
                                                                 numsemana=pact.semana,
                                                                 semana=pact.fechainicio.isocalendar()[1],
                                                                 fechainiciosemana=pact.fechainicio,
                                                                 fechafinciosemana=pact.fechafin,
                                                                 objetivoaprendizaje=semana.objetivoaprendizaje,
                                                                 enfoque=semana.enfoque,
                                                                 enfoquedos=semana.enfoquedos,
                                                                 enfoquetres=semana.enfoquetres,
                                                                 recursos=semana.recursos,
                                                                 evaluacion=semana.evaluacion,
                                                                 horaspresencial=semana.horaspresencial,
                                                                 horaautonoma=semana.horaautonoma
                                                                 )
                                    silabosemana.save()
                                    if semana.detallesilabosemanalbibliografia_set.filter(status=True).exists():
                                        for blibliografiabasia in semana.detallesilabosemanalbibliografia_set.filter(status=True):
                                            detallebb = DetalleSilaboSemanalBibliografia(silabosemanal=silabosemana, bibliografiaprogramaanaliticoasignatura=blibliografiabasia.bibliografiaprogramaanaliticoasignatura, status=True)
                                            detallebb.save()
                                    if semana.detallesilabosemanalbibliografiadocente_set.filter(status=True).exists():
                                        for bibliografiacomplementaria in semana.detallesilabosemanalbibliografiadocente_set.filter(status=True):
                                            detallebc = DetalleSilaboSemanalBibliografiaDocente(silabosemanal=silabosemana, librokohaprogramaanaliticoasignatura=bibliografiacomplementaria.librokohaprogramaanaliticoasignatura, status=True)
                                            detallebc.save()

                                    temaprogramadestino = None

                                    listaunidadtema = []

                                    if semana.detallesilabosemanaltema_set.filter(status=True, temaunidadresultadoprogramaanalitico__status=True).exists():
                                        for itemtema in semana.detallesilabosemanaltema_set.filter(status=True, temaunidadresultadoprogramaanalitico__status=True):
                                            numerotemaorigen = itemtema.temaunidadresultadoprogramaanalitico.orden
                                            textoorigen = itemtema.temaunidadresultadoprogramaanalitico.descripcion
                                            unidadorigen = itemtema.temaunidadresultadoprogramaanalitico.unidadresultadoprogramaanalitico.orden
                                            listaunidadtema.append([unidadorigen, numerotemaorigen])
                                            proganaliticoasigdestino = silaboaduplicar.programaanaliticoasignatura
                                            proganaliticoasigdestino = silaboaduplicar.programaanaliticoasignatura.asignaturamalla
                                            temaprogramadestino = TemaUnidadResultadoProgramaAnalitico.objects.filter(unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__asignaturamalla=proganaliticoasigdestino, unidadresultadoprogramaanalitico__orden=unidadorigen, orden=numerotemaorigen, status=True, unidadresultadoprogramaanalitico__status=True, unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__status=True,
                                                                                                                      unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__status=True, unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__activo=True)

                                            if temaprogramadestino:
                                                temadestino = temaprogramadestino[0]
                                                if itemtema.objetivoaprendizaje:
                                                    obj = itemtema.objetivoaprendizaje
                                                else:
                                                    obj = silabosemana.objetivoaprendizaje
                                                tema = DetalleSilaboSemanalTema(silabosemanal=silabosemana, temaunidadresultadoprogramaanalitico=temadestino, objetivoaprendizaje=obj, status=True)
                                                tema.save()
                                                listadostestmigrar.append([itemtema.id, tema.id])
                                                if semana.subtemaadicionalessilabo_set.filter(status=True, tema=tema).exists():
                                                    for subtemaadicional in semana.subtemaadicionalessilabo_set.filter(status=True, tema=tema):
                                                        sub = SubTemaAdicionalesSilabo(silabosemanal=silabosemana, tema=tema, subtema=subtemaadicional.subtema)
                                                        sub.save()
                                    #
                                    # if semana.detallesilabosemanaltema_set.filter(status=True, temaunidadresultadoprogramaanalitico__status=True).exists():
                                    #     for itemtema in semana.detallesilabosemanaltema_set.filter(status=True, temaunidadresultadoprogramaanalitico__status=True):
                                    #         if itemtema.objetivoaprendizaje:
                                    #             obj = itemtema.objetivoaprendizaje
                                    #         else:
                                    #             obj = silabosemana.objetivoaprendizaje
                                    #         tema = DetalleSilaboSemanalTema(silabosemanal=silabosemana, temaunidadresultadoprogramaanalitico=itemtema.temaunidadresultadoprogramaanalitico, objetivoaprendizaje=obj, status=True)
                                    #         tema.save()
                                    #         listadostestmigrar.append([itemtema.id, tema.id, semana])




                                    if semana.bibliograbiaapasilabo_set.filter(status=True).exists():
                                        for bibliografiavirtual in semana.bibliograbiaapasilabo_set.filter(status=True):
                                            bibli = BibliograbiaAPASilabo(silabosemanal=silabosemana, bibliografia=bibliografiavirtual.bibliografia)
                                            bibli.save()

                                    if temaprogramadestino:
                                        temadestino = temaprogramadestino[0]

                                        if semana.detallesilabosemanalsubtema_set.filter(status=True, subtemaunidadresultadoprogramaanalitico__status=True).exists():
                                            for itemsubtema in semana.detallesilabosemanalsubtema_set.filter(status=True, subtemaunidadresultadoprogramaanalitico__status=True):
                                                numerosubtemaorigen = itemsubtema.subtemaunidadresultadoprogramaanalitico.orden
                                                textosubtemaorigen = itemsubtema.subtemaunidadresultadoprogramaanalitico.descripcion
                                                proganaliticoasigdestino = silaboaduplicar.programaanaliticoasignatura
                                                proganaliticoasigdestino = silaboaduplicar.programaanaliticoasignatura.asignaturamalla

                                                for itemtema in listaunidadtema:
                                                    unidadorigenlista = itemtema[0]
                                                    numerotemaorigenlista = itemtema[1]

                                                    # if unidadorigenlista == 2 and numerotemaorigenlista == 3:
                                                    #     print("Hola")

                                                    subtemaprogramadestino = SubtemaUnidadResultadoProgramaAnalitico.objects.filter(temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__asignaturamalla=proganaliticoasigdestino, temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden=unidadorigenlista, temaunidadresultadoprogramaanalitico__orden=numerotemaorigenlista,
                                                                                                                                    temaunidadresultadoprogramaanalitico__status=True, orden=numerosubtemaorigen, status=True, temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__status=True, temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__status=True,
                                                                                                                                    temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__status=True, temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura__activo=True)

                                                    for subtemadestino in subtemaprogramadestino:
                                                        if not DetalleSilaboSemanalSubtema.objects.filter(silabosemanal=silabosemana, subtemaunidadresultadoprogramaanalitico=subtemadestino, status=True).exists():
                                                            subtema = DetalleSilaboSemanalSubtema(silabosemanal=silabosemana, subtemaunidadresultadoprogramaanalitico=subtemadestino, status=True)
                                                            subtema.save()

                                    if semana.recursosdidacticossemanal_set.filter(status=True).exists():
                                        for recurso in semana.recursosdidacticossemanal_set.filter(status=True):
                                            recurso = RecursosDidacticosSemanal(silabosemanal=silabosemana, descripcion=recurso.descripcion, link=recurso.link)
                                            recurso.save()
                                    if semana.articulosilabosemanal_set.filter(status=True).exists():
                                        for articulo in semana.articulosilabosemanal_set.filter(status=True):
                                            a = ArticuloSilaboSemanal(silabosemanal=silabosemana, articulo=articulo.articulo)
                                            a.save()

                    if silaboaduplicar.versionsilabo == 2:
                        if listadostestmigrar:
                            ordentest = 0
                            listadoaprendizaje = EvaluacionAprendizajeComponente.objects.filter(status=True)
                            for listami in listadostestmigrar:
                                idtemaantiguo = listami[0]
                                idtemaactual = ''
                                # idtemaactual = list(listami[1])

                                # semanaactual = DetalleSilaboSemanalTema.objects.get(pk=listami[1])
                                for lisaprendizaje in listadoaprendizaje:
                                    if EvaluacionAprendizajeTema.objects.filter(temasemanal_id=listami[0], evaluacion__evaluacionaprendizaje_id=lisaprendizaje.id, evaluacion__tipoactividadsemanal=1, status=True):
                                        itentest = EvaluacionAprendizajeTema.objects.get(temasemanal_id=listami[0], evaluacion__evaluacionaprendizaje_id=lisaprendizaje.id, evaluacion__tipoactividadsemanal=1, status=True)
                                        semanaactual = silaboaduplicar.silabosemanal_set.get(numsemana=itentest.evaluacion.silabosemanal.numsemana)
                                        ordentest = itentest.evaluacion.numactividad
                                        aprendizajestemassilabo(listami[1], lisaprendizaje.id, semanaactual.id, ordentest)


                    # coordinadorprograma = None
                    # coordinadoracademico = None
                    silabo = silaboaduplicar
                    # carrera = silabo.materia.asignaturamalla.malla.carrera
                    # if silabo.materia.nivel.periodo.tipo.id in [1, 2]:
                    #     cp = CoordinadorCarrera.objects.filter(periodo_id=202, carrera=carrera, tipo=3)
                    #     if cp:
                    #         coordinadorprograma = cp[0].persona
                    #     ca = Departamento.objects.filter(status=True, nombre__icontains='POSTGRADO')
                    #     if ca:
                    #         coordinadoracademico = ca[0].responsable
                    #     aprobars = AprobarSilabo(silabo=silabo,
                    #                              observacion='',
                    #                              persona_id=1,
                    #                              fecha=datetime.datetime.now(),
                    #                              estadoaprobacion=2)
                    #     aprobars.save()
                    #     if not silabo.silabofirmas_set.filter(status=True):
                    #         silabofirmas = SilaboFirmas(silabo=silabo,
                    #                                     coordinadorprograma=coordinadorprograma,
                    #                                     coordinadoracademico=coordinadoracademico)
                    #         silabofirmas.save()
                    #     else:
                    #         silabofirmas = SilaboFirmas.objects.filter(silabo_id=silabo, status=True)[0]
                    #         silabofirmas.coordinadorprograma = coordinadorprograma
                    #         silabofirmas.coordinadoracademico = coordinadoracademico
                    #         silabofirmas.save()


                    materia = silabo.materia
                    materia.actualizarhtml = True
                    materia.save()
                    silabo.codigoqr = True
                    silabo.save()
                    if silabo.versionsilabo == 2 and silabo.materia.nivel.periodo.tipo.id in [1, 2]:
                        qrname = 'qr_silabo_' + str(encrypt(silabo.id))
                        folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'silabodocente', 'qr'))
                        # folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'silabodocente', ''))
                        rutapdf = folder + qrname + '.pdf'
                        rutaimg = folder + qrname + '.png'
                        if os.path.isfile(rutapdf):
                            os.remove(rutapdf)
                        if os.path.isfile(rutaimg):
                            os.remove(rutaimg)
                        url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/silabodocente/' + qrname + '.pdf')
                        # url = pyqrcode.create('http://127.0.0.1:8000/media/qrcode/silabodocente/' + qrname + '.pdf')
                        imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                        imagenqr = 'qr' + qrname
                        valida = conviert_html_to_pdfsaveqrsilabo(
                            'pro_planificacion/silabovs2_pdf.html',
                            {'datos': silabo.silabodetalletemas_pdf(),
                             'data': silabo.silabovdos_pdf(),
                             'imprimeqr': True,
                             'qrname': imagenqr
                             }, qrname + '.pdf'
                        )
                        if valida:
                            os.remove(rutaimg)
                            silabo.codigoqr = True
                            silabo.save()


