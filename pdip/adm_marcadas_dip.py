# -*- coding: UTF-8 -*-
import json
from datetime import datetime, timedelta
import xlrd
import random
from django.http.response import HttpResponse
from xlwt import *
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from openpyxl.drawing.image import Image
from decorators import last_access
from sagest.models import DistributivoPersona, ImportacionMarcada, RegistroMarcada, MarcadasDia, \
    DetalleJornada, Jornada, HistorialJornadaTrabajador, TrabajadorDiaJornada, PermisoInstitucionalDetalle, LogDia, LogMarcada
from settings import EMAIL_DOMAIN, PUESTO_ACTIVO_ID
from sga.commonviews import adduserdata
from sagest.forms import HistorialJornadaTrabajadorForm, JornadaLaboralForm, CambiarMarcadaForm
from sga.forms import ImportarArchivoXLSForm
from sga.funciones import MiPaginador, log, generar_nombre, convertir_fecha, puede_acceder_modulo, \
    puede_realizar_accion_afirmativo, puede_realizar_accion, convertir_fecha_invertida, convertir_fecha,\
    convertir_hora, puede_realizar_accion_is_superuser
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import Persona, DIAS_CHOICES, MESES_CHOICES, DiasNoLaborable
from sga.templatetags.sga_extras import encrypt

from pdip.models import ContratoDip


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'importar_log':
            try:
                form = ImportarArchivoXLSForm(request.POST, request.FILES)
                if form.is_valid():
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("importacion_log_", nfile._name)
                    archivo = ImportacionMarcada(archivo=nfile)
                    archivo.save(request)
                    workbook = xlrd.open_workbook(archivo.archivo.file.name)
                    sheet = workbook.sheet_by_index(0)
                    for rowx in range(sheet.nrows):
                        cols = sheet.row_values(rowx)
                        if cols[5] != "":
                            if Persona.objects.filter(Q(cedula=cols[5]) | Q(pasaporte=cols[5])).exists():
                                persona = Persona.objects.filter(Q(cedula=cols[5]) | Q(pasaporte=cols[5])).distinct()[0]
                                if cols[2] != persona.identificacioninstitucion:
                                    persona.identificacioninstitucion = cols[2]
                                    persona.save(request)
                                fecha = convertir_fecha(cols[3][:10])
                                time = datetime(fecha.year, fecha.month, fecha.day, int(cols[3].split(':')[0][10:13]), int(cols[3].split(':')[1]))
                                if persona.logdia_set.filter(fecha=fecha).exists():
                                    logdia = persona.logdia_set.filter(fecha=fecha)[0]
                                    if logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin__gte=logdia.fecha).exists():
                                        logdia.jornada = logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin__gte=logdia.fecha).order_by('fechainicio')[0].jornada
                                    elif logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin=None).exists():
                                        logdia.jornada = logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin=None)[0].jornada
                                    logdia.cantidadmarcadas += 1
                                    logdia.procesado = False
                                else:
                                    logdia = LogDia(persona=persona, fecha=fecha, cantidadmarcadas=1, importacion=archivo)
                                logdia.save(request)
                                if not logdia.logmarcada_set.filter(time=time).exists():
                                    registro = LogMarcada(logdia=logdia,
                                                          time=time,
                                                          secuencia=logdia.cantidadmarcadas)
                                    registro.save(request)
                                for l in LogDia.objects.filter(persona=persona, status=True, procesado=False).order_by("fecha"):
                                    if not l.jornada:
                                        if l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin__gte=l.fecha).exists():
                                            l.jornada = l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin__gte=l.fecha).order_by('fechainicio')[0].jornada
                                        elif l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin=None).exists():
                                            l.jornada = l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin=None)[0].jornada

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
                                    if l.procesado:
                                        calculando_marcadas(request, l.fecha, l.fecha, l.persona)
                    # for l in LogDia.objects.filter(status=True, procesado=False).order_by("fecha"):
                    #     if not l.jornada:
                    #         if l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin__gte=l.fecha).exists():
                    #             l.jornada = l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin__gte=l.fecha).order_by('fechainicio')[0].jornada
                    #         elif l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin=None).exists():
                    #             l.jornada = l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin=None)[0].jornada
                    #
                    #     cm = l.logmarcada_set.filter(status=True).count()
                    #     MarcadasDia.objects.filter(persona=l.persona, fecha=l.fecha).delete()
                    #     l.cantidadmarcadas = cm
                    #     if (cm % 2) == 0:
                    #         marini = 1
                    #         for dl in l.logmarcada_set.filter(status=True).order_by("time"):
                    #             if marini == 2:
                    #                 salida = dl.time
                    #                 marini = 1
                    #                 if l.persona.marcadasdia_set.filter(fecha=l.fecha).exists():
                    #                     marcadadia = l.persona.marcadasdia_set.filter(fecha=l.fecha)[0]
                    #                 else:
                    #                     marcadadia = MarcadasDia(persona=l.persona,
                    #                                              fecha=l.fecha,
                    #                                              logdia=l,
                    #                                              segundos=0)
                    #                     marcadadia.save(request)
                    #                 if not marcadadia.registromarcada_set.filter(entrada=entrada).exists():
                    #                     registro = RegistroMarcada(marcada=marcadadia,
                    #                                                entrada=entrada,
                    #                                                salida=salida,
                    #                                                segundos=(salida - entrada).seconds)
                    #                     registro.save(request)
                    #                 marcadadia.actualizar_marcadas()
                    #             else:
                    #                 entrada = dl.time
                    #                 marini += 1
                    #         l.procesado = True
                    #     else:
                    #         l.cantidadmarcadas = 0
                    #     l.save(request)
                    #     if l.procesado:
                    #         calculando_marcadas(request, l.fecha, l.fecha, l.persona)
                    log(u'Importo plantilla log personal: %s' % persona, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'importar_logindividual':
            try:
                cedula = request.POST['cedula']
                fecaregistro = request.POST['fecha']
                if cedula != "":
                    if Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula)).exists():
                        persona = Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula)).distinct()[0]
                        fecha_aux = fecaregistro.split(" ")[0]
                        hora_aux = fecaregistro.split(" ")[1]
                        fecha = convertir_fecha(fecha_aux)
                        time = datetime(fecha.year, fecha.month, fecha.day, int(hora_aux.split(':')[0]), int(hora_aux.split(':')[1]))
                        if persona.logdia_set.filter(fecha=fecha).exists():
                            logdia = persona.logdia_set.filter(fecha=fecha)[0]
                            if logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin__gte=logdia.fecha).exists():
                                logdia.jornada = logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin__gte=logdia.fecha).order_by('fechainicio')[0].jornada
                            elif logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin=None).exists():
                                logdia.jornada = logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin=None)[0].jornada
                            logdia.cantidadmarcadas += 1
                            logdia.procesado = False
                        else:
                            logdia = LogDia(persona=persona, fecha=fecha, cantidadmarcadas=1)
                        logdia.save(request)
                        if not logdia.logmarcada_set.filter(time=time).exists():
                            registro = LogMarcada(logdia=logdia,
                                                  time=time,
                                                  secuencia=logdia.cantidadmarcadas)
                            registro.save(request)
                        for l in LogDia.objects.filter(persona=persona, status=True, procesado=False).order_by("fecha"):
                            if not l.jornada:
                                if l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin__gte=l.fecha).exists():
                                    l.jornada = l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin__gte=l.fecha).order_by('fechainicio')[0].jornada
                                elif l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin=None).exists():
                                    l.jornada = l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin=None)[0].jornada

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
                            if l.procesado:
                                calculando_marcadas(request, l.fecha, l.fecha, l.persona)
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'importar':
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
                        if Persona.objects.filter(Q(cedula=cols[2]) | Q(pasaporte=cols[2])).exists():
                            persona = Persona.objects.filter(Q(cedula=cols[2]) | Q(pasaporte=cols[2])).distinct()[0]
                            fecha = convertir_fecha(cols[5])
                            salida = datetime(fecha.year, fecha.month, fecha.day, int(cols[10].split(':')[0]), int(cols[10].split(':')[1]))
                            entrada = datetime(fecha.year, fecha.month, fecha.day, int(cols[9].split(':')[0]), int(cols[9].split(':')[1]))
                            if persona.marcadasdia_set.filter(fecha=fecha).exists():
                                marcadadia = persona.marcadasdia_set.filter(fecha=fecha)[0]
                            else:
                                marcadadia = MarcadasDia(persona=persona,
                                                         fecha=fecha,
                                                         segundos=0)
                                marcadadia.save(request)
                            if not marcadadia.registromarcada_set.filter(entrada=entrada).exists():
                                registro = RegistroMarcada(marcada=marcadadia,
                                                           entrada=entrada,
                                                           salida=salida,
                                                           segundos=(salida - entrada).seconds)
                                registro.save(request)
                            marcadadia.actualizar_marcadas()
                    log(u'Importo plantilla personal: %s' % persona, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'add':
            try:
                f = HistorialJornadaTrabajadorForm(request.POST)
                if f.is_valid():
                    # distributivo = DistributivoPersona.objects.get(pk=int(request.POST['id']))
                    persona = Persona.objects.get(pk=int(request.POST['id']))
                    if persona.historialjornadatrabajador_set.filter(fechafin=None):
                        return JsonResponse({"result": "bad", "mensaje": u"Existe una Jornada asignada actual."})
                    if HistorialJornadaTrabajador.objects.filter(Q(fechainicio__lte=f.cleaned_data['fechainicio']) & Q(fechafin__gte=f.cleaned_data['fechainicio']),persona=persona).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Fecha inicial incorrecta."})
                    if not f.cleaned_data['actual']:
                        if HistorialJornadaTrabajador.objects.filter(Q(fechainicio__lte=f.cleaned_data['fechafin']) & Q(fechafin__gte=f.cleaned_data['fechafin']), persona=persona).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Fecha inicial o final incorrecta."})
                    historial = HistorialJornadaTrabajador(persona=persona,
                                                           jornada=f.cleaned_data['jornada'],
                                                           fechainicio=f.cleaned_data['fechainicio'],
                                                           fechafin=f.cleaned_data['fechafin'])
                    historial.save(request)
                    log(u'Adiciono historial de jornada al trabajador: %s [%s]' % (historial, historial.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editjornadatrab':
            try:
                f = HistorialJornadaTrabajadorForm(request.POST)
                if f.is_valid():
                    jornada = HistorialJornadaTrabajador.objects.get(pk=int(request.POST['id']))
                    if jornada.persona.historialjornadatrabajador_set.filter(fechafin=None).exclude(id=jornada.id):
                        return JsonResponse({"result": "bad", "mensaje": u"Existe una Jornada asignada actual."})
                    if HistorialJornadaTrabajador.objects.filter(Q(fechainicio__lte=f.cleaned_data['fechainicio']) & Q(fechafin__gte=f.cleaned_data['fechainicio']),persona=jornada.persona).exclude(id=jornada.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Fecha inicial incorrecta."})
                    if not f.cleaned_data['actual']:
                        if HistorialJornadaTrabajador.objects.filter(Q(fechainicio__lte=f.cleaned_data['fechafin']) & Q(fechafin__gte=f.cleaned_data['fechafin']), persona=jornada.persona).exclude(id=jornada.id).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Fecha inicial o final incorrecta."})
                    jornada.fechainicio=f.cleaned_data['fechainicio']
                    jornada.fechafin=f.cleaned_data['fechafin']
                    jornada.save(request)
                    log(u'Modifico jornada: %s' % jornada, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'lista':
            try:
                if int(request.POST['idp']) == 0:
                    # distributivo = DistributivoPersona.objects.filter(persona__isnull=False, persona__historialjornadatrabajador__isnull=False).distinct()
                    persona = Persona.objects.filter(historialjornadatrabajador__isnull=False).distinct()
                else:
                    persona = Persona.objects.filter(id=int(request.POST['idp']),historialjornadatrabajador__isnull=False).distinct()
                lista = []
                for per in persona:
                    personas = {'distributivo': per.nombre_completo(), 'id': per.id}
                    lista.append(personas)
                return JsonResponse({"result": "ok", "cantidad": len(lista), "personas": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar lista para calcular jornadas"})

        elif action == 'calculando':
            try:
                fechai = convertir_fecha(request.POST['fechai'])
                fechaf = convertir_fecha(request.POST['fechaf'])
                persona = Persona.objects.get(pk=request.POST['maid'])
                calculando_marcadas(request, fechai, fechaf, persona)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        elif action == 'hdmarcada':
            try:
                logmarcada = LogMarcada.objects.get(pk=int(request.POST['id']))
                MarcadasDia.objects.filter(persona=logmarcada.logdia.persona, fecha=logmarcada.logdia.fecha).delete()
                logmarcada.status = not logmarcada.status
                logmarcada.logdia.cantidadmarcadas = 0
                logmarcada.logdia.procesado = False
                logmarcada.logdia.save(request)
                logmarcada.save(request)
                cm = logmarcada.logdia.logmarcada_set.filter(status=True).count()
                logmarcada.logdia.cantidadmarcadas = cm
                if (cm % 2) == 0:
                    marini = 1
                    for dl in logmarcada.logdia.logmarcada_set.filter(status=True).order_by("time"):
                        if marini == 2:
                            salida = dl.time
                            marini = 1
                            if logmarcada.logdia.persona.marcadasdia_set.filter(fecha=logmarcada.logdia.fecha).exists():
                                marcadadia = logmarcada.logdia.persona.marcadasdia_set.filter(fecha=logmarcada.logdia.fecha)[0]
                            else:
                                marcadadia = MarcadasDia(persona=logmarcada.logdia.persona,
                                                         fecha=logmarcada.logdia.fecha,
                                                         logdia=logmarcada.logdia,
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
                    logmarcada.logdia.procesado = True
                else:
                    logmarcada.logdia.cantidadmarcadas = 0
                    logmarcada.logdia.procesado = False
                logmarcada.logdia.save(request)
                calculando_marcadas(request, logmarcada.time.date(), logmarcada.time.date(), logmarcada.logdia.persona)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        elif action == 'edit':
            try:
                f = HistorialJornadaTrabajadorForm(request.POST)
                if f.is_valid():
                    distributivo = DistributivoPersona.objects.get(pk=int(request.POST['id']))
                    if distributivo.persona.historialjornadatrabajador_set.filter(fechafin=None):
                        return JsonResponse({"result": "bad", "mensaje": u"Existe una Jornada asignada actual."})
                    historial = HistorialJornadaTrabajador(persona=distributivo.persona,
                                                           jornada=f.cleaned_data['jornada'],
                                                           fechainicio=f.cleaned_data['fechainicio'],
                                                           fechafin=f.cleaned_data['fechafin'])
                    historial.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addjornada':
            try:
                f = JornadaLaboralForm(request.POST)
                datos = json.loads(request.POST['lista_items1'])
                lista = []
                if not datos:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar un rango de tiempo."})
                for d in datos:
                    fechainicio = datetime(datetime.now().year, 1, int(d['dia']))
                    horainicio = int(d['entrada'].split(':')[0])
                    minutoinicio = int(d['entrada'].split(':')[1])
                    fechafin = datetime(datetime.now().year, 1, int(d['dia']))
                    horafin = int(d['salida'].split(':')[0])
                    minutofin = int(d['salida'].split(':')[1])
                    lista.append([datetime(fechainicio.year, fechainicio.month, fechainicio.day, horainicio, minutoinicio), datetime(fechafin.year, fechafin.month, fechafin.day, horafin, minutofin)])
                p = 1

                def hora_dia(hr, mi):
                    now = datetime.now()
                    return now.replace(hour=hr, minute=mi, second=0, microsecond=0)

                for elemento in lista:
                    otros = lista
                    otros.remove(elemento)
                    for otro in otros:
                        if otro[0] <= elemento[0] <= otro[1]:
                            if hora_dia(otro[0].hour, otro[0].minute) <= hora_dia(elemento[0].hour, elemento[0].minute) <= hora_dia(otro[1].hour, otro[1].minute):
                                return JsonResponse({"result": "bad", "mensaje": u"Error fechas incorrectas."})
                        if otro[0] <= elemento[1] <= otro[1]:
                            if hora_dia(otro[0].hour, otro[0].minute) <= hora_dia(elemento[1].hour, elemento[1].minute) <= hora_dia( otro[1].hour, otro[1].minute):
                                return JsonResponse({"result": "bad", "mensaje": u"Error fechas incorrectas."})
                    p += 1
                if f.is_valid():
                    jornada = Jornada(nombre=f.cleaned_data['nombre'])
                    jornada.save(request)
                    for elemento in datos:
                        detalle = DetalleJornada(jornada=jornada,
                                                 dia=elemento['dia'],
                                                 horainicio=elemento['entrada'],
                                                 horafin=elemento['salida'])
                        detalle.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editjornada':
            try:
                f = JornadaLaboralForm(request.POST)
                datos = json.loads(request.POST['lista_items1'])
                lista = []
                if not datos:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar un rango de tiempo."})
                for d in datos:
                    fechainicio = datetime(datetime.now().year, 1, int(d['dia']))
                    horainicio = int(d['entrada'].split(':')[0])
                    minutoinicio = int(d['entrada'].split(':')[1])
                    fechafin = datetime(datetime.now().year, 1, int(d['dia']))
                    horafin = int(d['salida'].split(':')[0])
                    minutofin = int(d['salida'].split(':')[1])
                    lista.append([datetime(fechainicio.year, fechainicio.month, fechainicio.day, horainicio, minutoinicio), datetime(fechafin.year, fechafin.month, fechafin.day, horafin, minutofin)])
                p = 1

                def hora_dia(hr, mi):
                    now = datetime.now()
                    return now.replace(hour=hr, minute=mi, second=0, microsecond=0)

                for elemento in lista:
                    otros = lista
                    otros.remove(elemento)
                    for otro in otros:
                        if otro[0] <= elemento[0] <= otro[1]:
                            if hora_dia(otro[0].hour, otro[0].minute) <= hora_dia(elemento[0].hour, elemento[0].minute) <= hora_dia(otro[1].hour, otro[1].minute):
                                return JsonResponse({"result": "bad", "mensaje": u"Error fechas incorrectas."})
                        if otro[0] <= elemento[1] <= otro[1]:
                            if hora_dia(otro[0].hour, otro[0].minute) <= hora_dia(elemento[1].hour, elemento[1].minute) <= hora_dia(otro[1].hour, otro[1].minute):
                                return JsonResponse({"result": "bad", "mensaje": u"Error fechas incorrectas."})
                    p += 1
                if f.is_valid():
                    jornada = Jornada.objects.get(pk=int(request.POST['id']))
                    jornada.detallejornada_set.all().delete()
                    jornada.save(request)
                    for elemento in datos:
                        detalle = DetalleJornada(jornada=jornada,
                                                 dia=elemento['dia'],
                                                 horainicio=elemento['entrada'],
                                                 horafin=elemento['salida'])
                        detalle.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'cerrarjornada':
            try:
                f = HistorialJornadaTrabajadorForm(request.POST)
                if f.is_valid():
                    # persona = Persona.objects.get(id=int(request.POST['id']))
                    jornada = HistorialJornadaTrabajador.objects.get(pk=int(request.POST['id']))
                    jornada.fechafin = f.cleaned_data['fechafin']
                    jornada.save(request)
                    log(u'Cerro jornada: %s' % jornada, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'eliminarjornadatrab':
            try:
                jornada = HistorialJornadaTrabajador.objects.get(pk=int(request.POST['id']))
                jornada.delete()
                log(u'Elimino jornada: %s' % jornada, request, "delete")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'meses_anio':
            try:
                personad = Persona.objects.get(pk=int(request.POST['id']))
                anio = request.POST['anio']
                lista = []
                for elemento in TrabajadorDiaJornada.objects.filter(persona=personad, anio=anio).order_by('mes').distinct():
                    if [elemento.mes, elemento.rep_mes()] not in lista:
                        lista.append([elemento.mes, elemento.rep_mes()])
                return JsonResponse({"result": "ok", "lista": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'meses_anio_log':
            try:
                # distributivo = DistributivoPersona.objects.get(pk=int(request.POST['id']))
                personad = Persona.objects.get(pk=int(request.POST['id']))
                anio = request.POST['anio']
                lista = []
                for e in LogDia.objects.filter(persona=personad, fecha__year=anio, status=True).order_by('fecha').distinct():
                    if [e.fecha.month, MESES_CHOICES[e.fecha.month - 1][1]] not in lista:
                        lista.append([e.fecha.month, MESES_CHOICES[e.fecha.month - 1][1]])
                return JsonResponse({"result": "ok", "lista": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'detalle_jornda_trab':
            try:
                data = {}
                data['persona'] = personad = Persona.objects.get(pk=int(request.POST['id']))
                # data ['distributivo'] = distributivo = DistributivoPersona.objects.get(pk=int(request.POST['id']))
                if ContratoDip.objects.filter(persona=personad, status=True).exists():
                    data['distributivo'] = ContratoDip.objects.filter(persona= personad, status=True)[0]
                anio = request.POST['anio']
                mes = request.POST['mes']
                data['h'] = False
                if 'h' in request.POST:
                    data['h'] = True
                data['horainicio'] = datetime(2016, 1, 1, 0, 0, 0)
                data['horafin'] = datetime(2016, 1, 1, 23, 59, 59)
                if TrabajadorDiaJornada.objects.filter(persona=personad).exists():
                    data['dias'] = TrabajadorDiaJornada.objects.filter(persona=personad, anio=anio, mes=mes, status=True).order_by('fecha')
                template = get_template("adm_contratodip/detallejornadatrabdip.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        elif action == 'detalle_jornda_trab_log':
            try:
                data = {}
                # data['distributivo'] = distributivo = DistributivoPersona.objects.get(pk=int(request.POST['id']))
                data['persona'] = personad = Persona.objects.get(pk=int(request.POST['id']))
                # data['distributivo'] = DistributivoPersona.objects.filter(persona=distributivo.persona, estadopuesto__id=PUESTO_ACTIVO_ID)[0]
                anio = request.POST['anio']
                mes = request.POST['mes']
                data['puede_modificar'] = puede_realizar_accion_afirmativo(request, 'sagest.puede_modificar_hoja_vida') or puede_realizar_accion_afirmativo(request, 'sagest.puede_modificar_marcadas') or int(request.POST['pued_modificar']) == 1
                data['dias'] = LogDia.objects.filter(persona=personad, fecha__year=anio, fecha__month=mes, status=True).order_by('fecha')
                data['addmarcada'] = True if puede_realizar_accion_afirmativo(request,'sagest.puede_agregar_marcada_log') else False
                template = get_template("th_marcadas/detallejornadatrab_log.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        elif action == 'detalle_jornada_pdf':
            try:
                data = extraervalores(request.POST['id'],request.POST['mes'],request.POST['anio'],True if 'h' in request.POST else False)
                return conviert_html_to_pdf('adm_contratodip/detalle_jornada_pdf.html',{'pagesize': 'A4', 'data': data})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        elif action == 'informemarcada':
            mensaje = "Problemas al generar el informe de marcadas."
            try:
                fini = convertir_fecha_invertida(request.POST['fini'])
                ffin = convertir_fecha_invertida(request.POST['ffin'])
                data['personaadmin'] = persona = Persona.objects.get(id=int(request.POST['idpersona']))
                marcadas = LogDia.objects.filter(persona=persona, fecha__gte=fini, fecha__lte=ffin, status=True).order_by('fecha')
                return conviert_html_to_pdf('th_hojavida/informemarcadas.html',
                                            {'pagesize': 'A4',
                                             'marcadas': marcadas,
                                             'persona': persona,'fechainicio':fini,'fechafin':ffin,'hoy':datetime.now().date()
                                             })
            except Exception as ex:
                return HttpResponseRedirect("/th_hojavida?info=%s" % mensaje)

        elif action == 'addmarcada':
            try:
                if puede_realizar_accion(request, 'sagest.puede_agregar_marcada_log'):
                    logdia=LogDia.objects.get(id=int(request.POST['dia']))
                    fecha=logdia.fecha
                    hora=request.POST['time']
                    time = datetime(fecha.year, fecha.month, fecha.day, int(hora.split(':')[0]), int(hora.split(':')[1]))
                    if not LogMarcada.objects.filter(status=True,logdia=logdia,time=time).exists():
                        secuencia=int(request.POST['marc'])
                        registro = LogMarcada(logdia=logdia,
                                              time=time,
                                              secuencia=secuencia)
                        registro.save(request)
                        if not usuario.is_superuser:
                            log(u'agrego marcada : %s' % registro, request, "edit")
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Marcada ya existe"})
                    calculando_marcadas(request, registro.time.date(), registro.time.date(), logdia.persona)
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addmarcada2':
            try:
                if puede_realizar_accion_is_superuser(request, 'sagest.puede_agregar_marcada_log'):
                    fecha =  request.POST['dia'] if 'dia' in request.POST and request.POST['dia'] else None
                    hora =  request.POST['time'] if 'time' in request.POST and request.POST['time'] else None
                    if not fecha or not hora:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                    fecha = datetime.strptime(request.POST['dia'], '%Y-%m-%d').date()
                    time1 = convertir_hora(request.POST['time'])
                    time = datetime(fecha.year, fecha.month, fecha.day, time1.hour, time1.minute, time1.second)
                    horaactual = time.hour
                    minutoactual = time.minute
                    segundoactual = time.second
                    if persona.logdia_set.filter(fecha=fecha).exists():
                        logdia = persona.logdia_set.filter(fecha=fecha).first()
                        if logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin__gte=logdia.fecha).exists():
                            logdia.jornada = logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin__gte=logdia.fecha).order_by('fechainicio')[0].jornada
                        elif logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin=None).exists():
                            logdia.jornada = logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin=None)[0].jornada
                        logdia.cantidadmarcadas += 1
                        logdia.procesado = False
                    else:
                        logdia = LogDia(persona=persona,
                                        fecha=fecha,
                                        cantidadmarcadas=1)
                    logdia.save(request)
                    if not logdia.logmarcada_set.filter(time=time).exists():
                        registro = LogMarcada(logdia=logdia,
                                              time=time,
                                              secuencia=logdia.cantidadmarcadas)
                        registro.save(request)
                    else:
                        registro = logdia.logmarcada_set.filter(time=time).order_by('time').first()

                    for l in LogDia.objects.filter(persona=persona, status=True, procesado=False).order_by("fecha"):
                        if not l.jornada:
                            if l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha,
                                                                               fechafin__gte=l.fecha).exists():
                                l.jornada = l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha,
                                                                                            fechafin__gte=l.fecha).order_by(
                                    'fechainicio')[0].jornada
                            elif l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha,
                                                                                 fechafin=None).exists():
                                l.jornada = l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha,
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
                        # if l.procesado:
                        #     calculando_marcadas(request, l.fecha, l.fecha, l.persona)
                    calculando_marcadas(request, registro.time.date(), registro.time.date(), persona)
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editmarcada':
            try:
                form = CambiarMarcadaForm(request.POST)
                if form.is_valid():
                    if puede_realizar_accion(request, 'sagest.puede_agregar_marcada_log'):
                        logmarcada=LogMarcada.objects.get(id=int(request.POST['id']))
                        time1 = form.cleaned_data['hora']
                        time = datetime(logmarcada.time.year, logmarcada.time.month, logmarcada.time.day, time1.hour, time1.minute, time1.second)
                        logmarcada.time = time
                        logmarcada.logdia.procesado=False
                        logmarcada.logdia.save(request)
                        logmarcada.save(request)
                        cm = logmarcada.logdia.logmarcada_set.filter(status=True).count()
                        logmarcada.logdia.cantidadmarcadas = cm
                        if logmarcada.logdia.persona.marcadasdia_set.filter(fecha=logmarcada.logdia.fecha).exists():
                            marcadadia = logmarcada.logdia.persona.marcadasdia_set.filter(fecha=logmarcada.logdia.fecha,
                                                                                          status=True)[0]
                            if marcadadia.registromarcada_set.all().exists():
                                registrosm = marcadadia.registromarcada_set.all()
                                for r in registrosm:
                                    r.delete()

                        else:
                            marcadadia = MarcadasDia(persona=logmarcada.logdia.persona,
                                                     fecha=logmarcada.logdia.fecha,
                                                     logdia=logmarcada.logdia,
                                                     segundos=0)
                            marcadadia.save(request)
                        if (cm % 2) == 0:
                            marini = 1
                            for dl in logmarcada.logdia.logmarcada_set.filter(status=True).order_by("time"):
                                if marini == 2:
                                    salida = dl.time
                                    marini = 1
                                    registro=None
                                    if marcadadia.registromarcada_set.filter(status=True,entrada=entrada).exists():
                                        registro = marcadadia.registromarcada_set.filter(status=True,entrada=entrada)[0]
                                        registro.entrada=entrada
                                        registro.salida=salida
                                        registro.segundos=(salida - entrada).seconds

                                    else:
                                        registro = RegistroMarcada(marcada=marcadadia,
                                                                   entrada=entrada,
                                                                   salida=salida,
                                                                   segundos=(salida - entrada).seconds)
                                    registro.save(request)

                                    marcadadia.actualizar_marcadas()
                                else:
                                    entrada = dl.time
                                    marini += 1
                            logmarcada.logdia.procesado = True
                        else:
                            logmarcada.logdia.cantidadmarcadas = 0
                            logmarcada.logdia.procesado = False
                        logmarcada.logdia.save(request)
                        calculando_marcadas(request, logmarcada.time.date(), logmarcada.time.date(),
                                            logmarcada.logdia.persona)

                        log(u'editó marcada : %s' % logmarcada, request, "edit")

                        return JsonResponse({"result": False}, safe=False)

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Error al guardar los datos."}, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'importar':
                try:
                    data['title'] = u'Importar datos del biometricos'
                    data['form'] = ImportarArchivoXLSForm()
                    return render(request, "th_marcadas/importar.html", data)
                except Exception as ex:
                    pass

            if action == 'importar_log':
                try:
                    data['title'] = u'Importar datos LOG del biometricos'
                    data['form'] = ImportarArchivoXLSForm()
                    return render(request, "th_marcadas/importar_log.html", data)
                except Exception as ex:
                    pass

            if action == 'jornadastrabajador':
                try:
                    data['title'] = u'Jornada laboral'
                    # data['distributivo'] = distributivo = DistributivoPersona.objects.get(pk=int(request.GET['id']))
                    data['trabajador'] = persona = Persona.objects.get(pk=int(request.GET['id']))
                    data['dias'] = DIAS_CHOICES
                    data['jornadas'] = persona.historialjornadatrabajador_set.all()
                    return render(request, "adm_contratodip/jornadastrabajadorpdip.html", data)
                except Exception as ex:
                    pass

            if action == 'detallejornadatrabajador':
                try:
                    data['h'] = False
                    data['title'] = u'Detalle Jornada laboral'
                    # data['distributivo'] = distributivo = DistributivoPersona.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['personaadminis'] = persona = Persona.objects.get(pk=int(encrypt(request.GET['id'])))
                    # data['anios'] = persona.distributivopersona_set.filter(status=True )[0].lista_anios_trabajados()
                    data['anios'] = persona.lista_anios_trabajados_log()
                    data['jornadas'] = persona.historialjornadatrabajador_set.all()
                    data['fecha'] = datetime.now().date()
                    return render(request, "adm_contratodip/viewmarcadas.html", data)
                except Exception as ex:
                    pass

            if action == 'logmarcadas':
                try:
                    data['title'] = u'LOG de Marcadas'
                    # data['distributivo'] = distributivo = DistributivoPersona.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['personaadminis'] = persona = Persona.objects.get(pk=int(encrypt(request.GET['id'])))
                    if persona.contratodip_set.filter(status=True ).exists():
                        data['distributivo'] = distributivo = persona.contratodip_set.filter(status=True )[0]
                    data['anios'] = persona.lista_anios_trabajados_log()
                    data['pued_modificar'] = 0
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
                    data['jornadas'] = persona.historialjornadatrabajador_set.all()
                    data['hora'] = str(datetime.now().time())[0:5]
                    puede_crear_marcada = False
                    # try:
                    #     puede_crear_marcada = puede_realizar_accion_is_superuser(request, 'sagest.puede_crear_marcada')
                    # except:
                    #     puede_crear_marcada = False
                    data['puede_crear_marcada'] = puede_crear_marcada
                    return render(request, "adm_contratodip/logmarcadasdip.html", data)
                except Exception as ex:
                    pass

            if action == 'add':
                try:
                    data['title'] = u'Adicionar Jornada laboral'
                    # data['distributivo'] = DistributivoPersona.objects.get(pk=int(request.GET['id']))
                    data['persona'] = Persona.objects.get(pk=int(request.GET['id']))
                    data['form'] = HistorialJornadaTrabajadorForm()
                    return render(request, "adm_contratodip/addjornada.html", data)
                except Exception as ex:
                    pass

            if action == 'cerrarjornada':
                try:
                    data['title'] = u'Confirmar cerrar jornada'
                    data['jornada'] = jornada = HistorialJornadaTrabajador.objects.get(pk=int(request.GET['id']))
                    data['persona'] = Persona.objects.get(pk=int(request.GET['per']))
                    # data['distributivo'] = DistributivoPersona.objects.get(pk=int(request.GET['per']))
                    form = HistorialJornadaTrabajadorForm(initial={'jornada':jornada.jornada,
                                                                   'fechainicio': jornada.fechainicio,
                                                                   'fechafin': datetime.now().date()})
                    form.cerrar()
                    data['form'] = form
                    return render(request, "th_marcadas/cerrar.html", data)
                except:
                    pass

            if action == 'addjornada':
                try:
                    data['title'] = u'Adicionar Jornada laboral'
                    data['form'] = JornadaLaboralForm()
                    return render(request, "th_marcadas/addjornada.html", data)
                except Exception as ex:
                    pass

            if action == 'editjornada':
                try:
                    data['title'] = u'Editar Jornada laboral'
                    data['jornada'] = jornada = Jornada.objects.get(pk=int(request.GET['id']))
                    data['detalles'] = jornada.detallejornada_set.all().order_by('dia', 'horainicio')
                    form = JornadaLaboralForm(initial={'nombre': jornada.nombre})
                    form.editar()
                    data['form'] = form
                    return render(request, "th_marcadas/editjornada.html", data)
                except Exception as ex:
                    pass

            if action == 'editjornadatrab':
                try:
                    data['title'] = u'Editar Jornada del Trabajador'
                    data['jornada'] = jornada = HistorialJornadaTrabajador.objects.get(pk=int(request.GET['id']))
                    # data['distributivo'] = DistributivoPersona.objects.get(pk=int(request.GET['per']))
                    data['persona'] = Persona.objects.get(pk=int(request.GET['per']))
                    form = HistorialJornadaTrabajadorForm(initial={'jornada': jornada.jornada,
                                                                   'fechainicio': jornada.fechainicio,
                                                                   'fechafin': jornada.fechafin if jornada.fechafin else datetime.now().date()})
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_contratodip/editjornadatrabdip.html", data)
                except Exception as ex:
                    pass

            if action == 'jornadas':
                try:
                    data['title'] = u'Jornadas laborales'
                    data['jornadas'] = Jornada.objects.all()
                    return render(request, "th_marcadas/jornadas.html", data)
                except Exception as ex:
                    pass

            if action == 'eliminarjornada':
                try:
                    data['title'] = u'Confirmar eliminar Jornada de Trabajo'
                    data['jornada'] = Jornada.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_marcadas/eliminar.html", data)
                except Exception as ex:
                    pass

            if action == 'hdmarcada':
                try:
                    data['logmarcada'] = logmarcada = LogMarcada.objects.get(pk=request.GET['id'])
                    data['title'] = u'Deshabilitar Marcada' if logmarcada.status else u'Habilitar Marcada'
                    return render(request, "th_marcadas/hdmarcada.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'reportedetalleexcel':
                try:
                    borders = Borders()
                    borders.left = 1
                    borders.right = 1
                    borders.top = 1
                    borders.bottom = 1
                    data = extraervalores(request.GET['id'], request.GET['m'], request.GET['a'],True if 'h' in request.GET else False)
                    distributivo=data['distributivo']
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
                    response[
                        'Content-Disposition'] = 'attachment; filename=JORNADA_LABORAL_' + random.randint(
                        1, 10000).__str__() + '.xls'
                    ws.col(0).width = 1000
                    ws.col(1).width = 15000
                    ws.col(2).width = 4000
                    ws.col(3).width = 4000
                    ws.col(4).width = 4000
                    ws.col(5).width = 4000
                    row_num = 3
                    ws.write_merge(row_num, row_num, 0, 1, 'Cédula: '+distributivo.persona.cedula.__str__(), title2)
                    ws.write_merge(row_num, row_num, 2, 5, 'Mod.Lab: '+distributivo.modalidadlaboral.__str__(), title2)
                    row_num = 4
                    ws.write_merge(row_num, row_num, 0, 1, 'Apellidos: '+distributivo.persona.apellido1.__str__()+" "+distributivo.persona.apellido2.__str__(), title2)
                    ws.write_merge(row_num, row_num, 2, 5, 'Nombres: '+distributivo.persona.nombres.__str__(), title2)
                    row_num = 5
                    ws.write_merge(row_num, row_num, 0, 1, 'Régimen Laboral: '+distributivo.regimenlaboral.__str__(), title2)
                    ws.write_merge(row_num, row_num, 2, 5, 'Mes - Año: '+data['mes_nombre'].__str__()+" - "+data['anio'].__str__(), title2)
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
                        campo2 = dia.jornada.nombre +"\n"+ "Jornada"
                        for distributivo in data['distributivo'].detalle_jornada(dia):
                            campo2 += distributivo.horainicio.strftime("%H:%M") +" - "+ distributivo.horafin.strftime("%H:%M")
                        campo3 = dia.trabajadas_horas().__str__()+" Hrs. - "+ dia.trabajadas_minutos().__str__() +" Min."
                        campo4 = dia.permisos_horas().__str__()+" Hrs. - "+ dia.permisos_minutos().__str__() +" Min."
                        campo5 = dia.extras_horas().__str__()+" Hrs. - "+ dia.extras_minutos().__str__() +" Min."
                        campo6 = dia.atrasos_horas().__str__()+" Hrs. - "+ dia.atrasos_minutos().__str__() +" Min."
                        ws.write(row_num, 0, campo1, style)
                        ws.write(row_num, 1, campo2, style2)
                        ws.write(row_num, 2, campo3, style)
                        ws.write(row_num, 3, campo4, style)
                        ws.write(row_num, 4, campo5, style)
                        ws.write(row_num, 5, campo6, style)
                        row_num += 1
                    ws.col(2).height = 1000
                    ws.write(row_num, 1, "Total horas:   ", style3)
                    ws.write(row_num, 2, data['total_trabajadas_horas'].__str__()+" Hrs.-"+data['total_trabajadas_minutos'].__str__()+" Min.", style)
                    ws.write(row_num, 3, data['total_permisos_horas'].__str__()+"Hrs.-"+data['total_permisos_minutos'].__str__()+" Min.", style)
                    ws.write(row_num, 4, data['total_extras_horas'].__str__()+" Hrs.-"+data['total_extras_minutos'].__str__()+" Min.", style)
                    ws.write(row_num, 5, data['total_atrasos_horas'].__str__()+" Hrs.-"+data['total_atrasos_minutos'].__str__()+" Min.", style)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'eliminarjornadatrab':
                try:
                    data['title'] = u'Confirmar eliminar Jornada de Trabajo'
                    # data['distributivo'] = DistributivoPersona.objects.get(pk=int(request.GET['per']))
                    data['persona'] = Persona.objects.get(pk=int(request.GET['per']))
                    data['jornada'] = HistorialJornadaTrabajador.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_marcadas/eliminarjornada.html", data)
                except Exception as ex:
                    pass

            elif action == 'editmarcada':
                try:
                    logmarcada = LogMarcada.objects.get(pk=request.GET['id'])
                    form = CambiarMarcadaForm(initial={'hora':logmarcada.time.time()})
                    data['form'] = form
                    data['id'] = request.GET['id']
                    template = get_template("th_marcadas/modal/formmarcada.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass



            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Marcadas de biometricos.'
            if not puede_acceder_modulo(request):
                return HttpResponseRedirect('/?info=Usted no tiene permiso para usar este modulo.')
            search = None
            ids = None
            personasmarcadas = LogDia.objects.values_list('persona__id', flat=True).filter(status=True, persona__status=True).distinct()
            if 's' in request.GET:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                if len(ss) == 1:
                    # plantillas = DistributivoPersona.objects.filter(Q(persona__nombres__icontains=search) |
                    #                                                 Q(persona__apellido1__icontains=search) |
                    #                                                 Q(persona__apellido2__icontains=search) |
                    #                                                 Q(persona__cedula__icontains=search) |
                    #                                                 Q(persona__pasaporte__icontains=search)).distinct()
                    plantillas = Persona.objects.select_related().filter(Q(nombres__icontains=search) |
                                                                    Q(apellido1__icontains=search) |
                                                                    Q(apellido2__icontains=search) |
                                                                    Q(cedula__icontains=search) |
                                                                    Q(pasaporte__icontains=search),
                                                                         id__in=personasmarcadas).distinct()
                else:
                    plantillas = Persona.objects.select_related().filter(Q(apellido1__icontains=ss[0])
                                                                         & Q(apellido2__icontains=ss[1]), id__in=personasmarcadas, status=True).distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                # plantillas = DistributivoPersona.objects.filter(estadopuesto__id=PUESTO_ACTIVO_ID, id=ids)
                plantillas = Persona.objects.select_related().filter(id__in=personasmarcadas, id=ids, status=True)
            else:
                # plantillas = DistributivoPersona.objects.filter(estadopuesto__id=PUESTO_ACTIVO_ID)
                plantillas = Persona.objects.select_related().filter(id__in = personasmarcadas, status=True)
            paging = MiPaginador(plantillas, 20)
            p = 1
            try:
                paginasesion = 1
                page = None
                if 'paginador' in request.session:
                    paginasesion = int(request.session['paginador'])
                if 'page' in request.GET:
                    p = int(request.GET['page'])
                else:
                    p = paginasesion
                try:
                    page = paging.page(p)
                except:
                    p = 1
                page = paging.page(p)
            except:
                page = paging.page(p)
            request.session['paginador'] = p
            data['paging'] = paging
            data['rangospaging'] = paging.rangos_paginado(p)
            data['page'] = page
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['plantillas'] = page.object_list
            data['email_domain'] = EMAIL_DOMAIN
            data['fecha'] = datetime.now().date()
            return render(request, 'th_marcadas/view.html', data)

def extraervalores(id, mes, anio, h):
    data = {}
    bitaco = []

    data['persona'] = personad = Persona.objects.get(pk=int(id))
    # data['distributivo'] = distributivo = DistributivoPersona.objects.get(pk=int(id))
    distributivo=None
    if ContratoDip.objects.values('id').filter(persona=personad, status=True).exists():
        distributivo = ContratoDip.objects.filter(persona=personad, status=True)[0]
    data['distributivo'] = distributivo
    data['anio'] = anio = anio
    data['mes_nombre'] = MESES_CHOICES[int(mes) - 1][1]
    data['h'] = h
    data['horainicio'] = horainicio = datetime(2016, 1, 1, 0, 0, 0)
    data['horafin'] = horafin = datetime(2016, 1, 1, 23, 59, 59)
    fechas = TrabajadorDiaJornada.objects.values_list('fecha').filter(persona=personad, anio=anio, mes=mes, status=True).order_by('fecha')
    dias_no_laborable = DiasNoLaborable.objects.values_list('fecha').filter(fecha__in=fechas).exclude( periodo__isnull=False)
    data['dias'] = dias = TrabajadorDiaJornada.objects.filter(persona=personad, anio=anio, mes=mes, status=True).exclude(fecha__in=dias_no_laborable).order_by('fecha')
    total_trabajadas_horas = 0
    total_trabajadas_minutos = 0
    total_permisos_horas = 0
    total_permisos_minutos = 0
    total_extras_horas = 0
    total_extras_minutos = 0
    total_atrasos_horas = 0
    total_atrasos_minutos = 0
    total_ho = 0
    total_mi = 0
    total_pago = 0
    for dia in dias:
        total_trabajadas_horas += dia.trabajadas_horas()
        total_trabajadas_minutos += dia.trabajadas_minutos()
        total_permisos_horas += dia.permisos_horas()
        total_permisos_minutos += dia.permisos_minutos()
        total_extras_horas += dia.extras_horas()
        total_extras_minutos += dia.extras_minutos()
        total_atrasos_horas += dia.atrasos_horas()
        total_atrasos_minutos += dia.atrasos_minutos()
        total_ho +=dia.total_horas_calculadas()[0]
        total_mi +=dia.total_horas_calculadas()[1]
        total_pago +=dia.pago_dia()
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
    if total_mi >59:
        total_ho+=int(total_mi/60)
        total_mi = int(total_mi %60)
    data['total_trabajadas_horas'] = total_trabajadas_horas
    data['total_trabajadas_minutos'] = total_trabajadas_minutos
    data['total_permisos_horas'] = total_permisos_horas
    data['total_permisos_minutos'] = total_permisos_minutos
    data['total_extras_horas'] = total_extras_horas
    data['total_extras_minutos'] = total_extras_minutos
    data['total_atrasos_horas'] = total_atrasos_horas
    data['total_atrasos_minutos'] = total_atrasos_minutos
    data['total_ho'] = total_ho
    data['total_mi'] = total_mi
    data['pago_total'] = round(total_pago,2)
    return data


@login_required(redirect_field_name='ret', login_url='/loginsagest')
def calculando_marcadas(request, fechai, fechaf, persona):
    b = range(86400)
    while fechai <= fechaf:
        c = [[] for i in b]
        if not DiasNoLaborable.objects.filter(fecha=fechai).exclude(periodo__isnull=False).exists():
            if persona.historialjornadatrabajador_set.filter(fechainicio__lte=fechai, fechafin__gte=fechai).exists():
                jornada = persona.historialjornadatrabajador_set.filter(fechainicio__lte=fechai, fechafin__gte=fechai).order_by('fechainicio')[0]
                if jornada.jornada.detallejornada_set.filter(dia=fechai.isoweekday()).exists():
                    jornadasdia = jornada.jornada.detallejornada_set.filter(dia=fechai.isoweekday())
                    if TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai).exists():
                        diajornada = TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai)[0]
                        diajornada.jornada = jornada.jornada
                        diajornada.totalsegundostrabajados = 0
                        diajornada.totalsegundospermisos = 0
                        diajornada.totalsegundosextras = 0
                        diajornada.totalsegundosatrasos = 0
                    else:
                        diajornada = TrabajadorDiaJornada(persona=persona,
                                                          fecha=fechai,
                                                          anio=fechai.year,
                                                          mes=fechai.month,
                                                          jornada=jornada.jornada)
                        diajornada.save(request)
                    if persona.marcadasdia_set.filter(fecha=fechai).exists():
                        marcadadia = persona.marcadasdia_set.filter(fecha=fechai)[0]
                    else:
                        marcadadia = MarcadasDia(persona=persona, fecha=fechai)
                        marcadadia.save(request)
                    totalsegundostrabajados = 0
                    totalsegundosextras = 0
                    totalsegundosatraso = 0
                    totalpermisos = 0
                    totalpermisosantes = 0
                    for marcada in marcadadia.registromarcada_set.all():
                        duracion = (marcada.salida - marcada.entrada).seconds
                        inicio = (marcada.entrada.time().hour * 60 * 60) + (marcada.entrada.time().minute * 60) + marcada.entrada.time().second
                        fin = (marcada.salida.time().hour * 60 * 60) + (marcada.salida.time().minute * 60) + marcada.salida.time().second
                        while inicio <= fin:
                            c[inicio].append('m')
                            inicio += 1
                    for jornadamarcada in jornadasdia:
                        duracionjornada = (datetime(fechai.year, fechai.month, fechai.day, jornadamarcada.horafin.hour, jornadamarcada.horafin.minute, jornadamarcada.horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, jornadamarcada.horainicio.hour, jornadamarcada.horainicio.minute, jornadamarcada.horainicio.second))).seconds
                        iniciojornada = (jornadamarcada.horainicio.hour * 60 * 60) + (jornadamarcada.horainicio.minute * 60) + jornadamarcada.horainicio.second
                        finjornada = (jornadamarcada.horafin.hour * 60 * 60) + (jornadamarcada.horafin.minute * 60) + jornadamarcada.horafin.second
                        while iniciojornada <= finjornada:
                            c[iniciojornada].append('j')
                            iniciojornada += 1
                    for permiso in PermisoInstitucionalDetalle.objects.filter(permisoinstitucional__solicita=persona, fechainicio__lte=fechai, fechafin__gte=fechai, permisoinstitucional__estadosolicitud=3):
                        # VACACIONES
                        if permiso.permisoinstitucional.tiposolicitud == 3:
                            horainicio = datetime(2016, 1, 0, 0, 0, 0)
                            horafin = datetime(2016, 1, 1, 23, 0, 0)
                            duracionpermiso = (datetime(fechai.year, fechai.month, fechai.day, horafin.hour, horafin.minute, horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, horainicio.hour, horainicio.minute, horainicio.second))).seconds
                            iniciopermiso = (horainicio.hour * 60 * 60) + (horainicio.minute * 60) + horainicio.second
                            finpermiso = (horafin.hour * 60 * 60) + (horafin.minute * 60) + horafin.second
                        else:
                            duracionpermiso = (datetime(fechai.year, fechai.month, fechai.day, permiso.horafin.hour, permiso.horafin.minute, permiso.horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, permiso.horainicio.hour, permiso.horainicio.minute, permiso.horainicio.second))).seconds
                            iniciopermiso = (permiso.horainicio.hour * 60 * 60) + (permiso.horainicio.minute * 60) + permiso.horainicio.second
                            finpermiso = (permiso.horafin.hour * 60 * 60) + (permiso.horafin.minute * 60) + permiso.horafin.second
                        while iniciopermiso <= finpermiso:
                            c[iniciopermiso].append('p')
                            iniciopermiso += 1
                    for i in c:
                        if len(i):
                            if 'm' in i:
                                if 'j' in i:
                                    totalsegundostrabajados += 1
                                else:
                                    totalsegundosextras += 1
                            elif 'j' in i:
                                if 'p' in i:
                                    totalpermisos += 1
                                else:
                                    totalsegundosatraso += 1
                            else:
                                totalpermisosantes += 1
                    diajornada.totalsegundosatrasos = totalsegundosatraso
                    diajornada.totalsegundostrabajados = totalsegundostrabajados
                    diajornada.totalsegundosextras = totalsegundosextras
                    diajornada.totalsegundospermisos = totalpermisos
                    diajornada.save(request)
            elif persona.historialjornadatrabajador_set.filter(fechainicio__lte=fechai, fechafin=None).exists():
                jornada = persona.historialjornadatrabajador_set.filter(fechainicio__lte=fechai, fechafin=None)[0]
                if jornada.jornada.detallejornada_set.filter(dia=fechai.isoweekday()).exists():
                    jornadasdia = jornada.jornada.detallejornada_set.filter(dia=fechai.isoweekday())
                    if TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai).exists():
                        diajornada = TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai)[0]
                        diajornada.jornada = jornada.jornada
                        diajornada.totalsegundostrabajados = 0
                        diajornada.totalsegundospermisos = 0
                        diajornada.totalsegundosextras = 0
                        diajornada.totalsegundosatrasos = 0
                    else:
                        diajornada = TrabajadorDiaJornada(persona=persona,
                                                          fecha=fechai,
                                                          anio=fechai.year,
                                                          mes=fechai.month,
                                                          jornada=jornada.jornada)
                        diajornada.save(request)
                    if persona.marcadasdia_set.filter(fecha=fechai).exists():
                        marcadadia = persona.marcadasdia_set.filter(fecha=fechai)[0]
                    else:
                        marcadadia = MarcadasDia(persona=persona, fecha=fechai)
                        marcadadia.save(request)
                    totalsegundostrabajados = 0
                    totalsegundosextras = 0
                    totalsegundosatraso = 0
                    totalpermisos = 0
                    totalpermisosantes = 0
                    for marcada in marcadadia.registromarcada_set.all():
                        duracion = (marcada.salida - marcada.entrada).seconds
                        inicio = (marcada.entrada.time().hour * 60 * 60) + (marcada.entrada.time().minute * 60) + marcada.entrada.time().second
                        fin = (marcada.salida.time().hour * 60 * 60) + (marcada.salida.time().minute * 60) + marcada.salida.time().second
                        while inicio <= fin:
                            c[inicio].append('m')
                            inicio += 1
                    for jornadamarcada in jornadasdia:
                        duracionjornada = (datetime(fechai.year, fechai.month, fechai.day, jornadamarcada.horafin.hour, jornadamarcada.horafin.minute, jornadamarcada.horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, jornadamarcada.horainicio.hour, jornadamarcada.horainicio.minute, jornadamarcada.horainicio.second))).seconds
                        iniciojornada = (jornadamarcada.horainicio.hour * 60 * 60) + (jornadamarcada.horainicio.minute * 60) + jornadamarcada.horainicio.second
                        finjornada = (jornadamarcada.horafin.hour * 60 * 60) + (jornadamarcada.horafin.minute * 60) + jornadamarcada.horafin.second
                        while iniciojornada <= finjornada:
                            c[iniciojornada].append('j')
                            iniciojornada += 1
                    for permiso in PermisoInstitucionalDetalle.objects.filter(permisoinstitucional__solicita=persona, fechainicio__lte=fechai, fechafin__gte=fechai, permisoinstitucional__estadosolicitud=3):
                        # VACACIONES
                        if permiso.permisoinstitucional.tiposolicitud == 3:
                            horainicio = datetime(2016, 1, 1, 0, 0, 0)
                            horafin = datetime(2016, 1, 1, 23, 0, 0)
                            duracionpermiso = (datetime(fechai.year, fechai.month, fechai.day, horafin.hour, horafin.minute, horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, horainicio.hour, horainicio.minute, horainicio.second))).seconds
                            iniciopermiso = (horainicio.hour * 60 * 60) + (horainicio.minute * 60) + horainicio.second
                            finpermiso = (horafin.hour * 60 * 60) + (horafin.minute * 60) + horafin.second
                        else:
                            duracionpermiso = (datetime(fechai.year, fechai.month, fechai.day, permiso.horafin.hour, permiso.horafin.minute, permiso.horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, permiso.horainicio.hour, permiso.horainicio.minute, permiso.horainicio.second))).seconds
                            iniciopermiso = (permiso.horainicio.hour * 60 * 60) + (permiso.horainicio.minute * 60) + permiso.horainicio.second
                            finpermiso = (permiso.horafin.hour * 60 * 60) + (permiso.horafin.minute * 60) + permiso.horafin.second
                        while iniciopermiso <= finpermiso:
                            c[iniciopermiso].append('p')
                            iniciopermiso += 1
                    for i in c:
                        if len(i):
                            if 'm' in i:
                                if 'j' in i:
                                    totalsegundostrabajados += 1
                                else:
                                    totalsegundosextras += 1
                            elif 'j' in i:
                                if 'p' in i:
                                    totalpermisos += 1
                                else:
                                    totalsegundosatraso += 1
                            else:
                                totalpermisosantes += 1
                    diajornada.totalsegundosatrasos = totalsegundosatraso
                    diajornada.totalsegundostrabajados = totalsegundostrabajados
                    diajornada.totalsegundosextras = totalsegundosextras
                    diajornada.totalsegundospermisos = totalpermisos
                    diajornada.save(request)
        else:
            if TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai).exists():
                jornada = persona.historialjornadatrabajador_set.filter(fechainicio__lte=fechai, fechafin=None)[0]
                diajornada = TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai)[0]
                diajornada.jornada = jornada.jornada
                diajornada.totalsegundostrabajados = 0
                diajornada.totalsegundospermisos = 0
                diajornada.totalsegundosextras = 0
                diajornada.totalsegundosatrasos = 0
                diajornada.status = False
                diajornada.save(request)
        fechai += timedelta(days=1)
