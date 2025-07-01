# -*- coding: latin-1 -*-
from datetime import datetime, timedelta
from sagest.models import TrabajadorDiaJornada, MarcadasDia, PermisoInstitucionalDetalle
from sga.models import DiasNoLaborable


def calculando_marcadasotro(fechai, fechaf, persona):
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
                        diajornada.save()
                    if persona.marcadasdia_set.filter(fecha=fechai).exists():
                        marcadadia = persona.marcadasdia_set.filter(fecha=fechai)[0]
                    else:
                        marcadadia = MarcadasDia(persona=persona, fecha=fechai)
                        marcadadia.save()
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
                    diajornada.save()
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
                        diajornada.save()
                    if persona.marcadasdia_set.filter(fecha=fechai).exists():
                        marcadadia = persona.marcadasdia_set.filter(fecha=fechai)[0]
                    else:
                        marcadadia = MarcadasDia(persona=persona, fecha=fechai)
                        marcadadia.save()
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
                    diajornada.save()
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
                diajornada.save()
        fechai += timedelta(days=1)
