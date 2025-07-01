# -*- coding: UTF-8 -*-
from datetime import datetime, time
import random

import xlrd
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from django.http.response import HttpResponse
from xlwt import *

from decorators import secure_module, last_access
from sga.forms import ImportarArchivoXLSForm
from sagest.models import DistributivoPersona, TrabajadorDiaJornada, LogDia, RegistroMarcada, MarcadasDia, \
    ImportacionMarcada, LogMarcada, Departamento
from settings import PUESTO_ACTIVO_ID
from sga.commonviews import adduserdata
from sga.funciones import log, generar_nombre
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import Persona, MESES_CHOICES, DiasNoLaborable
from sga.templatetags.sga_extras import encrypt


def extraervalores(id, mes, anio, h):
    data = {}
    data['distributivo'] = distributivo = DistributivoPersona.objects.get(pk=int(id))
    data['anio'] = anio = anio
    data['mes_nombre'] = MESES_CHOICES[int(mes) - 1][1]
    data['h'] = h
    data['horainicio'] = horainicio = datetime(2016, 1, 1, 0, 0, 0)
    data['horafin'] = horafin = datetime(2016, 1, 1, 23, 59, 59)
    fechas = TrabajadorDiaJornada.objects.values_list('fecha').filter(persona=distributivo.persona, anio=anio, mes=mes, status=True).order_by('fecha')
    dias_no_laborable = DiasNoLaborable.objects.values_list('fecha').filter(fecha__in=fechas).exclude( periodo__isnull=False)
    data['dias'] = dias = TrabajadorDiaJornada.objects.filter(persona=distributivo.persona, anio=anio, mes=mes, status=True).exclude(fecha__in=dias_no_laborable).order_by('fecha')
    total_trabajadas_horas = 0
    total_trabajadas_minutos = 0
    total_permisos_horas = 0
    total_permisos_minutos = 0
    total_extras_horas = 0
    total_extras_minutos = 0
    total_atrasos_horas = 0
    total_atrasos_minutos = 0
    for dia in dias:
        total_trabajadas_horas += dia.trabajadas_horas()
        total_trabajadas_minutos += dia.trabajadas_minutos()
        total_permisos_horas += dia.permisos_horas()
        total_permisos_minutos += dia.permisos_minutos()
        total_extras_horas += dia.extras_horas()
        total_extras_minutos += dia.extras_minutos()
        total_atrasos_horas += dia.atrasos_horas()
        total_atrasos_minutos += dia.atrasos_minutos()
    if total_trabajadas_minutos > 59:
        total_trabajadas_horas += int(total_trabajadas_minutos / 60)
        total_trabajadas_minutos = int(total_trabajadas_minutos % 60)
    if total_permisos_minutos > 59:
        total_permisos_horas += int(total_permisos_minutos / 60)
        total_permisos_minutos = int(total_permisos_minutos % 60)
    if total_extras_minutos > 59:
        total_extras_horas += int(total_extras_minutos / 60)
        total_extras_minutos = int(total_extras_minutos % 60)
    if total_atrasos_minutos > 59:
        total_atrasos_horas += int(total_atrasos_minutos / 60)
        total_atrasos_minutos = int(total_atrasos_minutos % 60)
    data['total_trabajadas_horas'] = total_trabajadas_horas
    data['total_trabajadas_minutos'] = total_trabajadas_minutos
    data['total_permisos_horas'] = total_permisos_horas
    data['total_permisos_minutos'] = total_permisos_minutos
    data['total_extras_horas'] = total_extras_horas
    data['total_extras_minutos'] = total_extras_minutos
    data['total_atrasos_horas'] = total_atrasos_horas
    data['total_atrasos_minutos'] = total_atrasos_minutos
    return data


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    usuario = request.user
    persona = request.session['persona']
    if persona.es_directordepartamental():
        departamento = Departamento.objects.filter(responsable=persona, integrantes__isnull=False).distinct()[0]
    else:
        departamento = persona.mi_cargo_actualadm().unidadorganica
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'meses_anio':
            try:
                distributivo = DistributivoPersona.objects.get(pk=int(request.POST['id']))
                anio = request.POST['anio']
                lista = []
                for elemento in TrabajadorDiaJornada.objects.filter(persona=distributivo.persona, anio=anio).order_by('mes').distinct():
                    if [elemento.mes, elemento.rep_mes()] not in lista:
                        lista.append([elemento.mes, elemento.rep_mes()])
                return JsonResponse({"result": "ok", "lista": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'meses_anio':
            try:
                distributivo = DistributivoPersona.objects.get(pk=int(request.POST['id']))
                anio = request.POST['anio']
                lista = []
                for elemento in TrabajadorDiaJornada.objects.filter(persona=distributivo.persona, anio=anio).order_by('mes').distinct():
                    if [elemento.mes, elemento.rep_mes()] not in lista:
                        lista.append([elemento.mes, elemento.rep_mes()])
                return JsonResponse({"result": "ok", "lista": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'meses_anio_log':
            try:
                distributivo = DistributivoPersona.objects.get(pk=int(request.POST['id']))
                anio = request.POST['anio']
                lista = []
                for e in LogDia.objects.filter(persona=distributivo.persona, fecha__year=anio, status=True).order_by('fecha').distinct():
                    if [e.fecha.month, MESES_CHOICES[e.fecha.month - 1][1]] not in lista:
                        lista.append([e.fecha.month, MESES_CHOICES[e.fecha.month - 1][1]])
                return JsonResponse({"result": "ok", "lista": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'detalle_jornda_trab':
            try:
                data = {}
                data['distributivo'] = distributivo = DistributivoPersona.objects.get(pk=int(request.POST['id']))
                anio = request.POST['anio']
                mes = request.POST['mes']
                data['h'] = False
                if 'h' in request.POST:
                    data['h'] = True
                data['horainicio'] = datetime(2016, 1, 1, 0, 0, 0)
                data['horafin'] = datetime(2016, 1, 1, 23, 59, 59)
                data['dias'] = TrabajadorDiaJornada.objects.filter(persona=distributivo.persona, anio=anio, mes=mes, status=True).order_by('fecha')
                template = get_template("adm_vermarcadas/detallejornadatrab.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'detalle_jornda_trab_log':
            try:
                data = {}
                data['distributivo'] = distributivo = DistributivoPersona.objects.get(pk=int(request.POST['id']))
                anio = request.POST['anio']
                mes = request.POST['mes']
                data['dias'] = LogDia.objects.filter(persona=distributivo.persona, fecha__year=anio, fecha__month=mes, status=True).order_by('fecha')
                template = get_template("adm_vermarcadas/detallejornadatrab_log.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        elif action == 'detalle_jornada_pdf':
            try:
                data = extraervalores(request.POST['id'],request.POST['mes'],request.POST['anio'],True if 'h' in request.POST else False)
                return conviert_html_to_pdf('th_marcadas/detalle_jornada_pdf.html',{'pagesize': 'A4', 'data': data})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        elif action == 'importar_vc':
            try:
                form = ImportarArchivoXLSForm(request.POST, request.FILES)
                if form.is_valid():
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("importacion_", nfile._name)
                    archivo = ImportacionMarcada(archivo=nfile)
                    archivo.save(request)
                    workbook = xlrd.open_workbook(archivo.archivo.file.name)
                    sheet = workbook.sheet_by_index(0)
                    for rowx in range(sheet.nrows):
                        cols = sheet.row_values(rowx)
                        if Persona.objects.filter(identificacioninstitucion=int(cols[0])).exists():
                            persona = Persona.objects.filter(identificacioninstitucion=int(cols[0])).distinct()[0]
                            fecha = xlrd.xldate_as_datetime(cols[1], 0)
                            hora = fecha.time()
                            if hora == time(0, 0, 0):
                                hora = xlrd.xldate_as_datetime(cols[2], 0).time()
                                fecha = fecha.replace(hour=hora.hour, minute=hora.minute, second=hora.second)
                            if not hora == time(0, 0, 0):
                                if persona.marcadasdia_set.filter(fecha=fecha.date()).exists():
                                    marcadadia = persona.marcadasdia_set.filter(fecha=fecha.date())[0]
                                else:
                                    marcadadia = MarcadasDia(persona=persona,
                                                             fecha=fecha.date(),
                                                             segundos=0)
                                    marcadadia.save(request)
                                if persona.logdia_set.filter(fecha=fecha.date()).exists():
                                    logdia = persona.logdia_set.filter(fecha=fecha.date()).first()
                                    if logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha,
                                                                                            fechafin__gte=logdia.fecha).exists():
                                        logdia.jornada = \
                                        logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha,
                                                                                             fechafin__gte=logdia.fecha).order_by(
                                            'fechainicio')[0].jornada
                                    elif logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha,
                                                                                              fechafin=None).exists():
                                        logdia.jornada = \
                                        logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha,
                                                                                             fechafin=None)[0].jornada
                                    logdia.cantidadmarcadas += 1
                                    logdia.procesado = False
                                else:
                                    if not LogDia.objects.filter(persona=persona, fecha=fecha.date()).exists():
                                        logdia = LogDia(persona=persona,
                                                        fecha=fecha.date(),
                                                        cantidadmarcadas=1)
                                        logdia.save(request)
                                    else:
                                        logdia = LogDia.objects.get(persona=persona, fecha=fecha)

                                if not logdia.logmarcada_set.filter(time=fecha).exists():
                                    registro = LogMarcada(logdia=logdia,
                                                          time=fecha,
                                                          secuencia=logdia.cantidadmarcadas)
                                    registro.save(request)
                                else:
                                    registro = logdia.logmarcada_set.filter(time=fecha).order_by('time').first()

                                for l in LogDia.objects.filter(persona=persona, status=True, procesado=False).order_by(
                                        "fecha"):
                                    if not l.jornada:
                                        if l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha,
                                                                                           fechafin__gte=l.fecha).exists():
                                            l.jornada = \
                                            l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha,
                                                                                            fechafin__gte=l.fecha).order_by(
                                                'fechainicio')[0].jornada
                                        elif l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha,
                                                                                             fechafin=None).exists():
                                            l.jornada = \
                                            l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha,
                                                                                            fechafin=None)[0].jornada

                                    cm = l.logmarcada_set.filter(status=True).count()
                                    MarcadasDia.objects.filter(persona=l.persona, fecha=l.fecha).delete()
                                    l.cantidadmarcadas = cm
                                    if (cm % 2) == 0:
                                        marini = 1
                                        for dl in l.logmarcada_set.filter(status=True).order_by("time"):
                                            if marini == 2:
                                                salida = dl.time
                                                marini = 1
                                                if l.persona.marcadasdia_set.filter(fecha=l.fecha).exists():
                                                    marcadadia = l.persona.marcadasdia_set.filter(fecha=l.fecha)[0]
                                                else:
                                                    marcadadia = MarcadasDia(persona=l.persona,
                                                                             fecha=l.fecha,
                                                                             logdia=l,
                                                                             segundos=0)
                                                    marcadadia.save(request)
                                                if not marcadadia.registromarcada_set.filter(entrada=entrada).exists():
                                                    registro = RegistroMarcada(marcada=marcadadia,
                                                                               entrada=entrada,
                                                                               salida=salida,
                                                                               segundos=(salida - entrada).seconds)
                                                    registro.save(request)
                                                marcadadia.actualizar_marcadas()
                                            else:
                                                entrada = dl.time
                                                marini += 1
                                        l.procesado = True
                                    else:
                                        l.cantidadmarcadas = 0
                                    l.save(request)
                                marcadadia.actualizar_marcadas()
                    log(u'Importo plantilla personal: %s' % persona, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'vermarcada':
                try:
                    data['title'] = u'LOG de Marcadas'
                    empleado = Persona.objects.filter(pk=int(request.GET['id']))[0]
                    data['distributivo'] = distributivo = empleado.distributivopersona_set.filter(unidadorganica=departamento, estadopuesto__id=PUESTO_ACTIVO_ID)[0]
                    data['anios'] = distributivo.lista_anios_trabajados_log()
                    if 'destino' in request.GET:
                        if 'ida' in request.GET:
                            data['destino'] =str(request.GET['destino'])+ '&ida='+str(request.GET['ida'])
                        else:
                            aumentar='?'
                            destino=''
                            if 's' in request.GET:
                                aumentar += '&s='+request.GET['s']
                            if 'idc' in request.GET:
                                aumentar += '&idc=' + request.GET['idc']
                            if 'destino' in request.GET:
                                destino = request.GET['destino']
                            data['destino'] = request.GET['destino'] + aumentar if aumentar.__len__()>1 else destino
                    data['jornadas'] = distributivo.persona.historialjornadatrabajador_set.all()
                    return render(request, "adm_vermarcadas/logmarcadas.html", data)
                except Exception as ex:
                    pass

            elif action == 'reportedetalleexcel':
                try:
                    borders = Borders()
                    borders.left = 1
                    borders.right = 1
                    borders.top = 1
                    borders.bottom = 1
                    data = extraervalores(request.GET['id'], request.GET['m'], request.GET['a'],
                                          True if 'h' in request.GET else False)
                    distributivo = data['distributivo']
                    __author__ = 'Unemi'
                    title = easyxf('font: name Arial, bold on, height 350; alignment: horiz centre')
                    title1 = easyxf('font: name Bodoni MT, bold on, height 400; alignment: horiz centre')
                    title2 = easyxf('font: name Arial, bold on, height 200; alignment: horiz left')
                    title3 = easyxf('font: name Arial, bold on, height 200; alignment: horiz center')
                    style = easyxf('font: name Arial, height 200; align:wrap on, horiz centre,vert centre')
                    style2 = easyxf('font: name Arial, height 200; align:wrap on, horiz left,vert centre')
                    style3 = easyxf('font: name Arial, bold on, height 200; align:wrap on, horiz right,vert centre')
                    style.borders = borders
                    style2.borders = borders
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('DETALLE_JORNADA_LABORAL')
                    ws.write_merge(1, 1, 0, 5, 'DETALLES DE JORNADA LABORAL', title1)
                    ws.write_merge(2, 2, 0, 5, '', title2)
                    response = HttpResponse(content_type="application/ms-excel")
                    # response['Content-Disposition'] = 'attachment; filename=JORNADA_LABORAL_DE_'+distributivo.persona.apellido1.__str__()+"_"+distributivo.persona.apellido2.__str__() +"_"+distributivo.persona.nombres.__str__()+"_"+ random.randint(1, 10000).__str__() + '.xls'
                    response['Content-Disposition'] = 'attachment; filename=JORNADA_LABORAL_' + random.randint(1, 10000).__str__() + '.xls'
                    ws.col(0).width = 1000
                    ws.col(1).width = 15000
                    ws.col(2).width = 4000
                    ws.col(3).width = 4000
                    ws.col(4).width = 4000
                    ws.col(5).width = 4000
                    row_num = 3
                    ws.write_merge(row_num, row_num, 0, 1, 'Cédula: ' + distributivo.persona.cedula.__str__(), title2)
                    ws.write_merge(row_num, row_num, 2, 5, 'Mod.Lab: ' + distributivo.modalidadlaboral.__str__(),
                                   title2)
                    row_num = 4
                    ws.write_merge(row_num, row_num, 0, 1,
                                   'Apellidos: ' + distributivo.persona.apellido1.__str__() + " " + distributivo.persona.apellido2.__str__(),
                                   title2)
                    ws.write_merge(row_num, row_num, 2, 5, 'Nombres: ' + distributivo.persona.nombres.__str__(), title2)
                    row_num = 5
                    ws.write_merge(row_num, row_num, 0, 1, 'Régimen Laboral: ' + distributivo.regimenlaboral.__str__(),
                                   title2)
                    ws.write_merge(row_num, row_num, 2, 5,
                                   'Mes - Año: ' + data['mes_nombre'].__str__() + " - " + data['anio'].__str__(),
                                   title2)
                    title3.borders = borders
                    title2.borders = borders
                    row_num = 6
                    ws.write(row_num, 0, "Dia", title3)
                    ws.write(row_num, 1, "Jornada", title2)
                    ws.write(row_num, 2, "Hrs. trabajada", title3)
                    ws.write(row_num, 3, "Hrs. permisos", title3)
                    ws.write(row_num, 4, "Hrs. extras", title3)
                    ws.write(row_num, 5, "Hrs. atrasos", title3)
                    row_num = 7
                    for dia in data['dias']:
                        campo1 = dia.fecha.strftime('%d')
                        campo2 = dia.jornada.nombre + "\n" + "Jornada"
                        for distributivo in data['distributivo'].detalle_jornada(dia):
                            campo2 += distributivo.horainicio.strftime("%H:%M") + " - " + distributivo.horafin.strftime(
                                "%H:%M")
                        campo3 = dia.trabajadas_horas().__str__() + " Hrs. - " + dia.trabajadas_minutos().__str__() + " Min."
                        campo4 = dia.permisos_horas().__str__() + " Hrs. - " + dia.permisos_minutos().__str__() + " Min."
                        campo5 = dia.extras_horas().__str__() + " Hrs. - " + dia.extras_minutos().__str__() + " Min."
                        campo6 = dia.atrasos_horas().__str__() + " Hrs. - " + dia.atrasos_minutos().__str__() + " Min."
                        ws.write(row_num, 0, campo1, style)
                        ws.write(row_num, 1, campo2, style2)
                        ws.write(row_num, 2, campo3, style)
                        ws.write(row_num, 3, campo4, style)
                        ws.write(row_num, 4, campo5, style)
                        ws.write(row_num, 5, campo6, style)
                        row_num += 1
                    ws.col(2).height = 1000
                    ws.write(row_num, 1, "Total horas:   ", style3)
                    ws.write(row_num, 2, data['total_trabajadas_horas'].__str__() + " Hrs.-" + data[
                        'total_trabajadas_minutos'].__str__() + " Min.", style)
                    ws.write(row_num, 3, data['total_permisos_horas'].__str__() + "Hrs.-" + data[
                        'total_permisos_minutos'].__str__() + " Min.", style)
                    ws.write(row_num, 4, data['total_extras_horas'].__str__() + " Hrs.-" + data[
                        'total_extras_minutos'].__str__() + " Min.", style)
                    ws.write(row_num, 5, data['total_atrasos_horas'].__str__() + " Hrs.-" + data[
                        'total_atrasos_minutos'].__str__() + " Min.", style)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'importar_vc':
                try:
                    data['title'] = u'Importar log de marcadas'
                    data['form'] = ImportarArchivoXLSForm()
                    return render(request, "adm_vermarcadas/formimportar_vc.html", data)
                except Exception as ex:
                    pass


            elif action == 'logmarcadas':
                try:
                    data['title'] = u'LOG de Marcadas'
                    data['distributivo'] = distributivo = DistributivoPersona.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['anios'] = distributivo.lista_anios_trabajados_log()
                    if 'destino' in request.GET:
                        if 'ida' in request.GET:
                            data['destino'] =str(request.GET['destino'])+ '&ida='+str(request.GET['ida'])
                        else:
                            aumentar='?'
                            destino=''
                            if 's' in request.GET:
                                aumentar += '&s='+request.GET['s']
                            if 'idc' in request.GET:
                                aumentar += '&idc=' + request.GET['idc']
                            if 'destino' in request.GET:
                                destino = request.GET['destino']
                            data['destino'] = request.GET['destino'] + aumentar if aumentar.__len__()>1 else destino
                    data['jornadas'] = distributivo.persona.historialjornadatrabajador_set.all()
                    return render(request, "adm_vermarcadas/logmarcadas.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Integrantes Departamento'
                integrantes =  departamento.mis_integrantes()
                data['integrantes'] = integrantes
                data['departamento'] = departamento
                return render(request, 'adm_vermarcadas/view.html', data)
            except Exception as ex:
                pass