# -*- coding: latin-1 -*-
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.db.models.query_utils import Q
from datetime import datetime, timedelta
from decorators import last_access
from sga.models import Materia, Silabo, UnidadResultadoProgramaAnalitico, TestSilaboSemanalAdmision, Carrera, SilaboSemanal
from sga.templatetags.sga_extras import encrypt
from sga.funciones import daterange
import xlrd

@last_access
@transaction.atomic()
def view(request):
    data = {}
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'addregistro':
                try:
                    d=''

                    return JsonResponse({'result': 'ok', "mensaje": u"Sus datos se enviaron correctamente, por favor revisar la notificación enviada a su correo."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'pregrado':
                try:
                    listahorariosasignados = []
                    listahorarioenlineasinc =[]
                    listahorarioenlineaasinc = []
                    data['materia'] = materia = Materia.objects.get(pk=int(encrypt(request.GET['codigo'])))
                    if Silabo.objects.filter(materia=materia, status=True).exists():
                        data['tienesilabo'] = True
                        data['silabo'] = silabo = Silabo.objects.get(materia=materia, status=True)
                        data['unidades'] = listaunidades = UnidadResultadoProgramaAnalitico.objects.filter(contenidoresultadoprogramaanalitico__programaanaliticoasignatura=silabo.programaanaliticoasignatura,status=True).order_by('orden')
                        # return render(request, "moodle/pregrado.html", data)
                        listasilabosemanal = SilaboSemanal.objects.values_list('id','fechainiciosemana','fechafinciosemana','detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__orden').\
                            filter(status=True, detallesilabosemanaltema__status=True, silabo__status=True,
                                   detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__status=True,
                                   detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico_id__in=listaunidades.values_list('id'),
                                   detallesilabosemanaltema__temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__status=True,
                                   silabo=silabo).distinct().order_by('numsemana')

                        a = False
                        numerounidad = 1
                        for silabo in listasilabosemanal:
                            fechahoy = datetime.now().date()
                            fechafin = silabo[2] + timedelta(days=1)

                            for dia in daterange(silabo[1], fechafin):
                                if fechahoy == dia:
                                    numerounidad = silabo[3]
                                    a = True
                        data['numerounidad'] = numerounidad
                        if materia.nivel.modalidad.id in [1,2,4]:
                            for listahor in  materia.clase_set.filter(activo=True).distinct('turno'):
                                listahorariosasignados.append([listahor.turno,listahor.get_dia_display()])
                        data['listahorariosasignados'] = listahorariosasignados
                        if materia.nivel.modalidad.id in [3]:
                            for listahor in  materia.clase_set.filter(activo=True,tipohorario=2).distinct('turno'):
                                listahorarioenlineasinc.append([listahor.turno,listahor.get_dia_display()])
                            for listahor in  materia.clase_set.filter(activo=True,tipohorario=7).distinct('turno'):
                                listahorarioenlineaasinc.append([listahor.turno,listahor.get_dia_display()])
                        data['listahorarioenlineasinc']=listahorarioenlineasinc
                        data['listahorarioenlineaasinc'] = listahorarioenlineaasinc
                        return render(request, "moodle/recursossilabovdos.html", data)
                    else:
                        data['tienesilabo'] = False
                        return render(request, "moodle/recursossilabovdos.html", data)
                        #return render(request, "moodle/recursossilabo.html", data)

                except Exception as ex:
                    pass

            if action == 'sedemilagro':
                try:
                    lista = []
                    workbook = xlrd.open_workbook('milagro.xlsx')
                    sheet = workbook.sheet_by_index(0)
                    linea = 1
                    for rowx in range(sheet.nrows):
                        if linea > 1:
                            cols = sheet.row_values(rowx)
                            lista.append([cols[0],cols[1],cols[2],cols[3],cols[4],cols[5],cols[6]])
                        linea += 1
                    data['listadoalumnos'] = lista
                    return render(request, "moodle/sedemilagro.html", data)
                except Exception as ex:
                    pass

            if action == 'admision':
                try:
                    listahorariosasignados = []
                    listahorarioenlineasinc = []
                    listahorarioenlineaasinc = []
                    if not Materia.objects.filter(pk=int(encrypt(request.GET['codigo']))).exists():
                        messages.error(request, 'Materia no existe')
                        return redirect('/')
                    data['materia'] = materia = Materia.objects.get(pk=int(encrypt(request.GET['codigo'])))
                    data['carrera'] = carrera = Carrera.objects.get(pk=materia.asignaturamalla.malla.carrera_id)
                    # data['listadolinkmateria'] = materia.linkmateriaexamen_set.filter(status=True)
                    data['listadoexamen'] = None
                    if TestSilaboSemanalAdmision.objects.filter(status=True, silabosemanal__silabo__status=True, silabosemanal__silabo__materia=materia, estado_id=4, detallemodelo__nombre__icontains='EX').exists():
                        data['listadoexamen'] = TestSilaboSemanalAdmision.objects.filter(status=True, silabosemanal__silabo__status=True,silabosemanal__silabo__materia=materia, estado_id=4, detallemodelo__nombre__icontains='EX')[0]
                    if Silabo.objects.filter(materia=materia, status=True).exists():
                        data['tienesilabo'] = True
                        data['silabo'] = silabo = Silabo.objects.get(materia=materia, status=True)
                        data['unidades'] = UnidadResultadoProgramaAnalitico.objects.filter(contenidoresultadoprogramaanalitico__programaanaliticoasignatura=silabo.programaanaliticoasignatura,status=True).order_by('orden')
                        # return render(request, "moodle/admision.html", data)
                        # nuevo html
                        if materia.nivel.modalidad.id in [1,2,4]:
                            for listahor in  materia.clase_set.filter(activo=True).distinct('turno'):
                                listahorariosasignados.append([listahor.turno,listahor.get_dia_display()])
                        data['listahorariosasignados'] = listahorariosasignados
                        if materia.nivel.modalidad.id in [3]:
                            for listahor in  materia.clase_set.filter(activo=True,tipohorario=2).distinct('turno'):
                                listahorarioenlineasinc.append([listahor.turno,listahor.get_dia_display()])
                            for listahor in  materia.clase_set.filter(activo=True,tipohorario=7).distinct('turno'):
                                listahorarioenlineaasinc.append([listahor.turno,listahor.get_dia_display()])
                        data['listahorarioenlineasinc']=listahorarioenlineasinc
                        data['listahorarioenlineaasinc'] = listahorarioenlineaasinc
                        return render(request, "moodle/admisionvdos.html", data)
                    else:
                        data['tienesilabo'] = False
                        # return render(request, "moodle/admision.html", data)
                        #nuevo html
                        return render(request, "moodle/admisionvdos.html", data)
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Registrar certificado'

            except Exception as ex:
                pass