# -*- coding: UTF-8 -*-
from datetime import datetime, timedelta, date
import xlwt
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from xlwt import XFStyle, easyxf
from decorators import secure_module
from sagest.models import DistributivoPersona, DetalleJornada, TrabajadorDiaJornada, PermisoInstitucional, \
    RegimenLaboral
from sga.commonviews import adduserdata
from sga.funciones import convertir_fecha


def detalle_permisos(personaid,fecha):
    if PermisoInstitucional.objects.filter(solicita__id=personaid, permisoinstitucionaldetalle__fechainicio__lte=fecha, permisoinstitucionaldetalle__fechafin__gte=fecha).exists():
        return PermisoInstitucional.objects.filter(solicita__id=personaid, permisoinstitucionaldetalle__fechainicio__lte=fecha, permisoinstitucionaldetalle__fechafin__gte=fecha)[0].motivo
    return ''


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'descarga':
                try:
                    fecha = convertir_fecha(request.GET['fecha'])
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=marcadas.xls'
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('Sheetname')
                    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    ws.write_merge(0, 0, 0, 3, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
                    ws.col(0).width = 1000
                    ws.col(1).width = 6000
                    ws.col(2).width = 3000
                    ws.write(4, 0, 'FUNCIONARIO')
                    ws.write(4, 1, 'JORNADA')
                    ws.write(4, 2, 'HORAS ATRASO')
                    a = 4
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    plantillas = TrabajadorDiaJornada.objects.filter(fecha=fecha).order_by('persona')
                    for per in plantillas:
                        a += 1
                        cargo = ""
                        if per.persona.mi_cargo():
                            cargo = per.persona.mi_cargo().descripcion
                        ws.write(a, 0, per.persona.nombre_completo_inverso()+" - "+cargo)
                        texto = ""
                        if per.jornada:
                            texto = per.jornada.nombre
                        for jornada1 in per.persona.mi_plantilla_actual().detalle_jornada(per):
                            texto = texto + str(jornada1.horainicio)+" - "+str(jornada1.horafin)
                        ws.write(a, 1, texto)
                        texto1 = str(per.atrasos_horas())+" Hrs. - "+str(per.atrasos_minutos())+" Min."
                        ws.write(a, 2, texto1)
                    # ws.write(a+2, 0, 'Fecha:')
                    # ws.write(a+2, 1, datetime.today(),date_format)
                    ws.write_merge(a + 2, a + 2, 0, 1, datetime.today(), date_format)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'atrasodeldia':
                try:
                    fechai = convertir_fecha(request.GET['fechai'])
                    fechaf = convertir_fecha(request.GET['fechaf'])
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=marcadas.xls'
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('Sheetname')
                    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    ws.write_merge(0, 0, 0, 3, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
                    ws.col(0).width = 9000
                    ws.col(1).width = 16000
                    ws.col(2).width = 3000
                    ws.col(3).width = 3000
                    ws.write(1, 0, 'FECHA DESDE')
                    ws.write(2, 0, 'FECHA FIN')
                    ws.write(1, 1, '%s' % fechai)
                    ws.write(2, 1, '%s' % fechaf)

                    ws.write(4, 0, 'FUNCIONARIO')
                    ws.write(4, 1, 'JORNADA ACTUAL')
                    fecha = fechai
                    i = 2
                    while fecha <= fechaf:
                        ws.write(4, i, 'Jorn. In(%s)' % fecha.day)
                        i += 1
                        ws.write(4, i, 'Marc. In(%s)' % fecha.day)
                        i += 1
                        ws.write(4, i, 'Atraso(%s)' % fecha.day)
                        i += 1
                        fecha = fecha + timedelta(hours=24)

                    a = 4
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    plantillas = DistributivoPersona.objects.filter(estadopuesto=1, status=True).order_by('persona')
                    for per in plantillas:
                        a += 1
                        ws.write(a, 0, per.persona.nombre_completo_inverso())
                        texto = texto1 = ""
                        verifica = per.persona.jornada_actual()
                        if verifica:
                            texto = verifica.jornada.nombre
                        ws.write(a, 1, texto)
                        i = 2

                        fecha = fechai
                        while fecha <= fechaf:
                            texto1 = ""
                            time1 = time2 = 0
                            verifica = per.persona.jornada_fecha(fecha)
                            if verifica:
                                jornada = verifica.jornada
                                for jornada1 in DetalleJornada.objects.filter(jornada=jornada, dia=fecha.isoweekday()).order_by("horainicio")[:1]:
                                    texto1 = str(jornada1.horainicio)
                                    time1 = jornada1.horainicio
                            ws.write(a, i, texto1)
                            i += 1
                            texto1 = ""
                            if per.persona.logdia_set.filter(fecha=fecha, status=True).exists():
                                if per.persona.logdia_set.filter(fecha=fecha, status=True)[0].logmarcada_set.filter(status=True).exists():
                                   texto1 = per.persona.logdia_set.filter(fecha=fecha, status=True)[0].logmarcada_set.filter(status=True).order_by("time")[:1][0].time.strftime("%H:%M")
                                   time2 = per.persona.logdia_set.filter(fecha=fecha, status=True)[0].logmarcada_set.filter(status=True).order_by("time")[:1][0].time.time()
                            ws.write(a, i, texto1)
                            i += 1
                            atraso = None
                            if time2 and time1:
                                if time2 > time1:
                                    atraso = datetime.combine(date.today(), time2) - datetime.combine(date.today(), time1)
                            ws.write(a, i, str(atraso) if atraso else "")
                            fecha = fecha + timedelta(hours=24)
                            i += 1
                    # ws.write(a+2, 0, 'Fecha:')
                    # ws.write(a+2, 1, datetime.today(),date_format)
                    ws.write_merge(a + 2, a + 2, 0, 1, datetime.today(), date_format)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'atrasototal':
                try:
                    fechai = convertir_fecha(request.GET['fechai'])
                    fechaf = convertir_fecha(request.GET['fechaf'])
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=marcadas.xls'
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('Sheetname')
                    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    ws.write_merge(0, 0, 0, 3, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
                    ws.col(0).width = 3000
                    ws.col(1).width = 10000
                    ws.col(2).width = 6000
                    ws.col(3).width = 3000
                    i = 5
                    while i <= 24:
                        ws.col(i).width = 2000
                        i += 1
                    ws.write(1, 0, 'FECHA DESDE')
                    ws.write(2, 0, 'FECHA FIN')
                    ws.write(1, 1, '%s' % fechai)
                    ws.write(2, 1, '%s' % fechaf)

                    ws.write(4, 0, 'CEDULA')
                    ws.write(4, 1, 'FUNCIONARIO')
                    ws.write(4, 2, 'FACULTAD')
                    ws.write(4, 3, 'REGIMEN LABORAL')
                    ws.write(4, 4, 'FECHA')

                    ws.write(4, 5, 'Jorn 1.')
                    ws.write(4, 6, 'Jorn 2.')
                    ws.write(4, 7, 'Jorn 3.')
                    ws.write(4, 8, 'Jorn 4.')
                    ws.write(4, 9, 'Jorn 5.')
                    ws.write(4, 10, 'Jorn 6.')

                    ws.write(4, 11, 'Marc 1.')
                    ws.write(4, 12, 'Marc 2.')
                    ws.write(4, 13, 'Marc 3.')
                    ws.write(4, 14, 'Marc 4.')
                    ws.write(4, 15, 'Marc 5.')
                    ws.write(4, 16, 'Marc 6.')
                    ws.write(4, 17, 'Marc 7.')
                    ws.write(4, 18, 'Marc 8.')

                    ws.write(4, 19, 'Atra 1.')
                    ws.write(4, 20, 'Atra 2.')
                    ws.write(4, 21, 'Atra 3.')
                    ws.write(4, 22, 'Atra 4.')
                    ws.write(4, 23, 'Atra 5.')
                    ws.write(4, 24, 'Atra 6.')

                    a = 4
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    plantillas = DistributivoPersona.objects.filter(estadopuesto=1, status=True).order_by('persona')
                    for per in plantillas:
                        fecha = fechai
                        while fecha <= fechaf:
                            a += 1
                            ws.write(a, 0, u"%s" % per.persona.identificacion())
                            ws.write(a, 1, u"%s" % per.persona.nombre_completo_inverso())
                            verifica = per.persona.jornada_fecha(fecha)
                            ws.write(a, 2, u"%s" % per.unidadorganica)
                            ws.write(a, 3, u"%s" % per.regimenlaboral)
                            ws.write(a, 4, u"%s" % fecha)
                            canjor = []
                            if verifica:
                                jornada = verifica.jornada
                                i = 5
                                for jornada1 in DetalleJornada.objects.filter(jornada=jornada, dia=fecha.isoweekday(), status=True).order_by("horainicio"):
                                    ws.write(a, i, jornada1.horainicio.strftime("%H:%M"))
                                    canjor.append(jornada1.horainicio)
                                    i += 1
                                    ws.write(a, i, jornada1.horafin.strftime("%H:%M"))
                                    canjor.append(jornada1.horafin)
                                    i += 1
                                if i == 5:
                                    ws.write(a, i, u"NO LABORA ESTE DIA")
                            else:
                                ws.write(a, 5, u"NO TIENE ASIGNADA UNA JORNADA")

                            canmar = []
                            if per.persona.logdia_set.filter(fecha=fecha, status=True).exists():
                                i = 11
                                logdia = per.persona.logdia_set.get(fecha=fecha, status=True)
                                for lm in logdia.logmarcada_set.filter(status=True).order_by("time"):
                                    ws.write(a, i, lm.time.strftime("%H:%M"))
                                    canmar.append(lm.time.time())
                                    i += 1
                            i = 19
                            if (len(canmar) > 0 and len(canjor) > 0) and (len(canmar) == len(canjor)):
                                c = 0
                                for j in canjor:
                                    atraso = None
                                    if c % 2 == 0:
                                        if canmar[c] > j:
                                            atraso = datetime.combine(date.today(), canmar[c]) - datetime.combine(date.today(), j)
                                    else:
                                        if j > canmar[c]:
                                            atraso = datetime.combine(date.today(), j) - datetime.combine(date.today(), canmar[c])
                                    ws.write(a, i, str(atraso) if atraso else "")
                                    c += 1
                                    i += 1
                            else:
                                ws.write(a, i, u"NO CUMPLE CON TODAS LAS MARCADAS O NO TIENE JORNADA")
                            # aqui cerramos la fechas
                            fecha = fecha + timedelta(hours=24)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'detalle':
                try:
                    fechai = convertir_fecha(request.GET['fechai'])
                    fechaf = convertir_fecha(request.GET['fechaf'])
                    fechaic = str(fechai)
                    fechafc = str(fechaf)
                    regimen = request.GET['regimen']
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=marcadas.xls'
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('Sheetname')
                    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    fuentecabecera = easyxf('font: name Times New Roman, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Times New Roman, color-index black, height 150; align: wrap on, horiz center; borders: left thin, right thin, top thin, bottom thin')
                    ws.write_merge(0, 0, 0, 12, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
                    ws.col(0).width = 10000
                    ws.col(1).width = 5000
                    ws.col(2).width = 20000
                    ws.col(3).width = 3000
                    ws.col(4).width = 3000
                    ws.col(5).width = 3000
                    ws.col(6).width = 3000
                    ws.col(7).width = 3000
                    ws.col(8).width = 3000
                    ws.col(9).width = 3000
                    ws.col(10).width = 10000
                    ws.col(11).width = 10000
                    ws.col(12).width = 10000


                    ws.write(1, 0, 'FECHA DESDE')
                    ws.write(2, 0, 'FECHA FIN')
                    ws.write(1, 1, '%s' % fechai)
                    ws.write(2, 1, '%s' % fechaf)

                    ws.write(4, 0, 'FUNCIONARIO',fuentecabecera)
                    ws.write(4, 1, 'REGIMEN',fuentecabecera)
                    ws.write(4, 2, 'JORNADA',fuentecabecera)
                    ws.write(4, 3, 'FECHA',fuentecabecera)
                    ws.write(4, 4, 'Marc 1.',fuentecabecera)
                    ws.write(4, 5, 'Marc 2.',fuentecabecera)
                    ws.write(4, 6, 'Marc 3.',fuentecabecera)
                    ws.write(4, 7, 'Marc 4.',fuentecabecera)
                    ws.write(4, 8, 'Marc 5.',fuentecabecera)
                    ws.write(4, 9, 'Marc 6.',fuentecabecera)
                    ws.write(4, 10, 'PERMISOS EN EL SISTEMA INSTITUCIONAL - SAGEST',fuentecabecera)
                    ws.write(4, 11, 'TOTALIDAD DE ATRASOS GENERADOS',fuentecabecera)
                    ws.write(4, 12, 'HORAS ADICIONALES LABORADAS',fuentecabecera)

                    a = 4
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    cursor = connection.cursor()
                    sql=""
                    sql = "select tabla.persona, tabla.fecha, " \
                          " COALESCE((select  array_to_string(array_agg(j.nombre),',') from sagest_historialjornadatrabajador hj, sagest_jornada j where j.id=hj.jornada_id and j.status=true and hj.fechainicio<=tabla.fecha and hj.fechafin>=tabla.fecha and hj.persona_id=tabla.personaid), " \
                          " (select  array_to_string(array_agg(j.nombre),',') from sagest_historialjornadatrabajador hj, sagest_jornada j where j.id=hj.jornada_id and j.status=true and hj.fechainicio<=tabla.fecha and hj.fechafin is null and hj.persona_id=tabla.personaid)) as jornada,  " \
                          " COALESCE((select to_char(logm.time, 'HH24:MI:SS') as hora from sagest_logmarcada logm where logm.logdia_id=tabla.id1 and logm.status=true order by logm.time limit 1 OFFSET 0),'') as hora1,    " \
                          " COALESCE((select to_char(logm.time, 'HH24:MI:SS') as hora from sagest_logmarcada logm where logm.logdia_id=tabla.id1 and logm.status=true order by logm.time limit 1 OFFSET 1),'') as hora2,    " \
                          " COALESCE((select to_char(logm.time, 'HH24:MI:SS') as hora from sagest_logmarcada logm where logm.logdia_id=tabla.id1 and logm.status=true order by logm.time limit 1 OFFSET 2),'') as hora3,    " \
                          " COALESCE((select to_char(logm.time, 'HH24:MI:SS') as hora from sagest_logmarcada logm where logm.logdia_id=tabla.id1 and logm.status=true order by logm.time limit 1 OFFSET 3),'') as hora4,    " \
                          " COALESCE((select to_char(logm.time, 'HH24:MI:SS') as hora from sagest_logmarcada logm where logm.logdia_id=tabla.id1 and logm.status=true order by logm.time limit 1 OFFSET 4),'') as hora5,    " \
                          " COALESCE((select to_char(logm.time, 'HH24:MI:SS') as hora from sagest_logmarcada logm where logm.logdia_id=tabla.id1 and logm.status=true order by logm.time limit 1 OFFSET 5),'') as hora6, tabla.id , tabla.personaid, " \
                          " (select lpad(cast((tj1.totalsegundosatrasos / 3600) as text),2,'0')||':'||lpad(cast((tj1.totalsegundosatrasos/ 60 - 60 * (tj1.totalsegundosatrasos / 3600)) as text),2,'0')||':'||lpad(cast((tj1.totalsegundosatrasos - tj1.totalsegundosatrasos / 60 * 60) as text),2,'0') as atraso " \
                          " from sagest_trabajadordiajornada tj1 where tj1.status=true and tj1.persona_id=tabla.personaid and tj1.fecha=tabla.fecha limit 1) as atraso,  " \
                          " (select lpad(cast((tj1.totalsegundosextras / 3600) as text),2,'0')||':'||lpad(cast((tj1.totalsegundosextras/ 60 - 60 * (tj1.totalsegundosextras / 3600)) as text),2,'0')||':'||lpad(cast((tj1.totalsegundosextras - tj1.totalsegundosextras / 60 * 60) as text),2,'0') as demas " \
                          " from sagest_trabajadordiajornada tj1 where tj1.status=true and tj1.persona_id=tabla.personaid and tj1.fecha=tabla.fecha limit 1) as demas,  " \
                          " COALESCE((select count(*) from sagest_logmarcada logm where logm.logdia_id=tabla.id1 and logm.status=true ),0) as marcadas, permiso.motivo, " \
                          " (select count(*) " \
                          " from sagest_trabajadordiajornada t " \
                          " inner join sagest_distributivopersona d on d.estadopuesto_id=1 and d.status=true and t.persona_id=d.persona_id " \
                          " inner join sga_persona p on p.id=d.persona_id and p.status=true  " \
                          " inner join sagest_regimenlaboral r on r.id=d.regimenlaboral_id and r.status=true " \
                          " left join sagest_logdia l on l.status=true and  p.id=l.persona_id and t.persona_id=p.id and t.fecha=l.fecha " \
                          " where r.id="+regimen+" and t.fecha>='" + fechaic + "' and t.fecha<='" + fechafc + "'  " \
                          " and t.fecha not in (select dl.fecha from sga_diasnolaborable dl where dl.status=true and dl.fecha>='" + fechaic + "' and dl.fecha<='" + fechafc + "' " \
                          " and dl.periodo_id is null) and p.id=tabla.personaid GROUP BY personaid) as registros, tabla.descripcion " \
                          " from (select p.id as personaid, t.fecha, p.id, (p.apellido1||' '||p.apellido2||' '||p.nombres) as persona,l.id as id1,r.id as id2 ,r.descripcion   " \
                          " from sagest_trabajadordiajornada t  " \
                          " inner join sagest_distributivopersona d on d.estadopuesto_id=1 and d.status=true and t.persona_id=d.persona_id " \
                          " inner join sga_persona p on p.id=d.persona_id and p.status=true  " \
                          " inner join sagest_regimenlaboral r on r.id=d.regimenlaboral_id and r.status=true " \
                          " left join sagest_logdia l on l.status=true and  p.id=l.persona_id and t.persona_id=p.id and t.fecha=l.fecha " \
                          " where r.id="+regimen+" and t.fecha>='" + fechaic + "' and t.fecha<='" + fechafc + "'  " \
                          " and t.fecha not in (select dl.fecha from sga_diasnolaborable dl where dl.status=true and dl.fecha>='" + fechaic + "' and dl.fecha<='" + fechafc + "' " \
                          " and dl.periodo_id is null) GROUP BY personaid, t.fecha, l.id, r.id order by persona, t.fecha) as tabla  " \
                          " left join (select p1.motivo, p1.solicita_id, d1.fechainicio, d1.fechafin from sagest_permisoinstitucional p1, sagest_permisoinstitucionaldetalle d1 " \
                          " where p1.id=d1.permisoinstitucional_id and p1.status=true and d1.status=true   " \
                          " and p1.estadosolicitud=3 and  (d1.fechainicio-CAST('60 days' AS INTERVAL)) <= '" + fechaic + "' and (d1.fechafin+CAST('60 days' AS INTERVAL))>='" + fechafc + "') as permiso " \
                          " on permiso.solicita_id=tabla.personaid and permiso.fechainicio<=tabla.fecha and permiso.fechafin>=tabla.fecha order by tabla.persona, tabla.fecha;"
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    row_num = 5
                    persona = ""
                    for per in results:
                        if row_num == 917:
                            pass
                        campo1 = per[0]
                        campo2 = per[2]
                        campo3 = str(per[1])
                        campo4 = per[3]
                        campo5 = per[4]
                        campo6 = per[5]
                        campo7 = per[6]
                        campo8 = per[7]
                        campo9 = per[8]
                        # campo10 = detalle_permisos(per[10], convertir_fecha_invertida(campo3))
                        campo10 = per[14]
                        campo11 = per[11]
                        campo12 = per[12]
                        verificacion =  divmod(per[13],2)
                        campo13 = ''
                        if int(verificacion[1]) != 0:
                            campo13 = "ERROR EN LAS MARCADAS"
                        campo14 = per[16]

                        # ws.write(row_num, 0, campo1, font_style2)
                        if (persona != campo1):
                            numero = per[15]
                            if numero > 0:
                                numero = per[15] - 1
                            ws.write_merge(row_num, row_num+numero, 0, 0, campo1, fuentenormal)
                            persona = campo1
                        ws.write_merge(row_num, row_num, 1, 1, campo14, fuentenormal)
                        ws.write(row_num, 2, campo2, fuentenormal)
                        ws.write(row_num, 3, campo3, fuentenormal)
                        ws.write(row_num, 4, campo4, fuentenormal)
                        ws.write(row_num, 5, campo5, fuentenormal)
                        ws.write(row_num, 6, campo6, fuentenormal)
                        ws.write(row_num, 7, campo7, fuentenormal)
                        ws.write(row_num, 8, campo8, fuentenormal)
                        ws.write(row_num, 9, campo9, fuentenormal)
                        ws.write(row_num, 10, campo10, fuentenormal)
                        ws.write(row_num, 11, campo11, fuentenormal)
                        ws.write(row_num, 12, campo12, fuentenormal)
                        ws.write(row_num, 13, campo13, fuentenormal)
                        row_num += 1
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            if action == 'detalleatrasos':
                try:
                    fechai = convertir_fecha(request.GET['fechai'])
                    fechaf = convertir_fecha(request.GET['fechaf'])
                    fechaic = str(fechai)
                    fechafc = str(fechaf)
                    regimen = request.GET['regimen']
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=marcadas.xls'
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('Sheetname')
                    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    fuentecabecera = easyxf('font: name Times New Roman, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Times New Roman, color-index black, height 150; align: wrap on, horiz center; borders: left thin, right thin, top thin, bottom thin')
                    ws.write_merge(0, 0, 0, 12, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
                    ws.col(0).width = 10000
                    ws.col(1).width = 5000
                    ws.col(2).width = 20000

                    reg = RegimenLaboral.objects.get(pk=int(regimen))

                    ws.write(1, 0, 'FECHA DESDE')
                    ws.write(2, 0, 'FECHA FIN')
                    ws.write(1, 1, '%s' % fechai)
                    ws.write(2, 1, '%s' % fechaf)
                    ws.write(3, 0, 'RÉGIMEN: %s' % reg.descripcion)

                    ws.write(4, 0, 'FUNCIONARIO',fuentecabecera)
                    ws.write(4, 1, 'UNIDAD ADMINISTRATIVA',fuentecabecera)
                    ws.write(4, 2, 'JORNADA LABORAL',fuentecabecera)
                    lista_fechas = []
                    col = 3
                    for dia in daterange(fechai, (fechaf + timedelta(days=1))):
                        lista_fechas.append(str(dia))
                        ws.col(col).width = 3000
                        ws.write(4, col, str(dia),fuentecabecera)
                        col += 1
                    ws.col(col).width = 7000
                    ws.write(4, col, 'TOTALIDAD DE ATRASOS GENERADOS',fuentecabecera)
                    a = 4
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    cursor = connection.cursor()
                    sql=""
                    sql = "select tabla.departamento, tabla.persona, " \
                          " COALESCE((select array_to_string(array_agg(j.nombre),',') from sagest_historialjornadatrabajador hj, sagest_jornada j where j.id=hj.jornada_id and j.status=true and hj.fechainicio<=now() and hj.fechafin>=now() and hj.persona_id=tabla.personaid), " \
                          " (select array_to_string(array_agg(j.nombre),',') from sagest_historialjornadatrabajador hj, sagest_jornada j where j.id=hj.jornada_id and j.status=true and hj.fechainicio<=now() and hj.fechafin is null and hj.persona_id=tabla.personaid)) as jornada "
                    for dia in daterange(fechai, (fechaf + timedelta(days=1))):
                        sql = sql + " ,COALESCE((select lpad(cast((tj1.totalsegundosatrasos / 3600) as text),2,'0')||':'||lpad(cast((tj1.totalsegundosatrasos/ 60 - 60 * (tj1.totalsegundosatrasos / 3600)) as text),2,'0')||':'||lpad(cast((tj1.totalsegundosatrasos - tj1.totalsegundosatrasos / 60 * 60) as text),2,'0') as atraso " \
                                    " from sagest_trabajadordiajornada tj1 where tj1.status=true and tj1.persona_id=tabla.personaid and tj1.fecha='"+ str(dia) +"' limit 1),'') as atraso1 "
                    sql = sql + " from (select p.id as personaid, (p.apellido1||' '||p.apellido2||' '||p.nombres) as persona,r.descripcion, depa.nombre as departamento " \
                                " from sagest_trabajadordiajornada t " \
                                " inner join sagest_distributivopersona d on d.estadopuesto_id=1 and d.status=true and t.persona_id=d.persona_id " \
                                " inner join sga_persona p on p.id=d.persona_id and p.status=true " \
                                " inner join sagest_regimenlaboral r on r.id=d.regimenlaboral_id and r.status=true " \
                                " inner join sagest_departamento depa on depa.id=d.unidadorganica_id " \
                                " where r.id ="+regimen+" and t.fecha>='" + fechaic + "' and t.fecha<='" + fechafc + "' " \
                                " and t.fecha not in (select dl.fecha from sga_diasnolaborable dl where dl.status=true and dl.fecha>='" + fechaic + "' and dl.fecha<='" + fechafc + "' " \
                                " and dl.periodo_id is null) GROUP BY personaid, r.id, depa.nombre order by persona ) as tabla order by tabla.persona;"
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    row_num = 5
                    persona = ""
                    listado_persona = []
                    for per in results:
                        ws.write(row_num, 0, per[1], font_style2)
                        ws.write(row_num, 1, per[0], font_style2)
                        ws.write(row_num, 2, per[2], font_style2)
                        col = 3
                        dato = 3
                        suma_segundos = 0
                        for dia in daterange(fechai, (fechaf + timedelta(days=1))):
                            atraso = ''
                            if per[dato] != '00:00:00' and per[dato] != '':
                                atraso = per[dato]
                                aux = atraso.split(':')
                                suma_segundos += (int(aux[0])*3600)+(int(aux[1])*60)+int(aux[0])
                            ws.write(row_num, col, atraso, font_style2)
                            col += 1
                            dato += 1
                        atrasos = '00:00:00'
                        if suma_segundos > 0:
                            horas = int((suma_segundos/3600))
                            residuo1 = suma_segundos - (horas*3600)
                            minutos = int((residuo1/60))
                            residuo2 = residuo1 - (minutos*60)
                            segundos = residuo2
                            horas1 = str(horas)
                            if len(str(horas)) == 1:
                                horas1 = '0'+str(horas)
                            minutos1 = str(minutos)
                            if len(str(minutos)) == 1:
                                minutos1 = '0'+str(minutos)
                            segundos1 = str(segundos)
                            if len(str(segundos)) == 1:
                                segundos1 = '0'+str(segundos)
                            atrasos = horas1 + ':' + minutos1 + ':' + segundos1
                        ws.write(row_num, col, str(atrasos), font_style2)
                        row_num += 1
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            if action == 'detallemarcadasanual':
                try:
                    anio = str(request.GET['anio'])
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=marcadas.xls'
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('Sheetname')
                    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    fuentecabecera = easyxf('font: name Times New Roman, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Times New Roman, color-index black, height 150; align: wrap on, horiz center; borders: left thin, right thin, top thin, bottom thin')
                    ws.write_merge(0, 0, 0, 15, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
                    ws.col(0).width = 10000
                    ws.col(1).width = 10000
                    ws.col(1).width = 10000
                    ws.write(1, 0, 'DEPARTAMENTO',fuentecabecera)
                    ws.write(1, 1, 'DENOMINACIÓN PUESTO',fuentecabecera)
                    ws.write(1, 2, 'TRABAJADOR',fuentecabecera)
                    ws.write(1, 3, 'SEXO',fuentecabecera)
                    ws.write(1, 4, 'ENERO',fuentecabecera)
                    ws.write(1, 5, 'FEBRERO',fuentecabecera)
                    ws.write(1, 6, 'MARZO',fuentecabecera)
                    ws.write(1, 7, 'ABRIL',fuentecabecera)
                    ws.write(1, 8, 'MAYO',fuentecabecera)
                    ws.write(1, 9, 'JUNIO',fuentecabecera)
                    ws.write(1, 10, 'JULIO',fuentecabecera)
                    ws.write(1, 11, 'AGOSTO',fuentecabecera)
                    ws.write(1, 12, 'SEPTIEMBRE',fuentecabecera)
                    ws.write(1, 13, 'OCTUBRE',fuentecabecera)
                    ws.write(1, 14, 'NOVIEMBRE',fuentecabecera)
                    ws.write(1, 15, 'DICIEMBRE',fuentecabecera)
                    ws.write(1, 16, 'TOTAL',fuentecabecera)
                    a = 4
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    cursor = connection.cursor()
                    sql=""
                    sql = "select depa.nombre as departamento, de.descripcion as cargo, tabla.persona, tabla.sexo, " \
                          " COALESCE((select lpad(cast((sum(tj1.totalsegundostrabajados) / 3600) as text),3,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados)/ 60 - 60 * (sum(tj1.totalsegundostrabajados) / 3600)) as text),2,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados) - sum(tj1.totalsegundostrabajados) / 60 * 60) as text),2,'0') as trabajadas " \
                          " from sagest_trabajadordiajornada tj1 where tj1.status=true and tj1.persona_id=tabla.personaid and extract(year from tj1.fecha)="+ anio +" and extract(month from tj1.fecha)=1),'000:00:00') as trabajadas_enero, " \
                          " COALESCE((select lpad(cast((sum(tj1.totalsegundostrabajados) / 3600) as text),3,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados)/ 60 - 60 * (sum(tj1.totalsegundostrabajados) / 3600)) as text),2,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados) - sum(tj1.totalsegundostrabajados) / 60 * 60) as text),2,'0') as trabajadas " \
                          " from sagest_trabajadordiajornada tj1 where tj1.status=true and tj1.persona_id=tabla.personaid and extract(year from tj1.fecha)="+ anio +" and extract(month from tj1.fecha)=2),'000:00:00') as trabajadas_febrero, " \
                          " COALESCE((select lpad(cast((sum(tj1.totalsegundostrabajados) / 3600) as text),3,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados)/ 60 - 60 * (sum(tj1.totalsegundostrabajados) / 3600)) as text),2,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados) - sum(tj1.totalsegundostrabajados) / 60 * 60) as text),2,'0') as trabajadas " \
                          " from sagest_trabajadordiajornada tj1 where tj1.status=true and tj1.persona_id=tabla.personaid and extract(year from tj1.fecha)="+ anio +" and extract(month from tj1.fecha)=3),'000:00:00') as trabajadas_marzo, " \
                          " COALESCE((select lpad(cast((sum(tj1.totalsegundostrabajados) / 3600) as text),3,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados)/ 60 - 60 * (sum(tj1.totalsegundostrabajados) / 3600)) as text),2,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados) - sum(tj1.totalsegundostrabajados) / 60 * 60) as text),2,'0') as trabajadas " \
                          " from sagest_trabajadordiajornada tj1 where tj1.status=true and tj1.persona_id=tabla.personaid and extract(year from tj1.fecha)="+ anio +" and extract(month from tj1.fecha)=4),'000:00:00') as trabajadas_abril, " \
                          " COALESCE((select lpad(cast((sum(tj1.totalsegundostrabajados) / 3600) as text),3,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados)/ 60 - 60 * (sum(tj1.totalsegundostrabajados) / 3600)) as text),2,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados) - sum(tj1.totalsegundostrabajados) / 60 * 60) as text),2,'0') as trabajadas " \
                          " from sagest_trabajadordiajornada tj1 where tj1.status=true and tj1.persona_id=tabla.personaid and extract(year from tj1.fecha)="+ anio +" and extract(month from tj1.fecha)=5),'000:00:00') as trabajadas_mayo, " \
                          " COALESCE((select lpad(cast((sum(tj1.totalsegundostrabajados) / 3600) as text),3,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados)/ 60 - 60 * (sum(tj1.totalsegundostrabajados) / 3600)) as text),2,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados) - sum(tj1.totalsegundostrabajados) / 60 * 60) as text),2,'0') as trabajadas " \
                          " from sagest_trabajadordiajornada tj1 where tj1.status=true and tj1.persona_id=tabla.personaid and extract(year from tj1.fecha)="+ anio +" and extract(month from tj1.fecha)=6),'000:00:00') as trabajadas_junio, " \
                          " COALESCE((select lpad(cast((sum(tj1.totalsegundostrabajados) / 3600) as text),3,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados)/ 60 - 60 * (sum(tj1.totalsegundostrabajados) / 3600)) as text),2,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados) - sum(tj1.totalsegundostrabajados) / 60 * 60) as text),2,'0') as trabajadas " \
                          " from sagest_trabajadordiajornada tj1 where tj1.status=true and tj1.persona_id=tabla.personaid and extract(year from tj1.fecha)="+ anio +" and extract(month from tj1.fecha)=7),'000:00:00') as trabajadas_julio, " \
                          " COALESCE((select lpad(cast((sum(tj1.totalsegundostrabajados) / 3600) as text),3,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados)/ 60 - 60 * (sum(tj1.totalsegundostrabajados) / 3600)) as text),2,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados) - sum(tj1.totalsegundostrabajados) / 60 * 60) as text),2,'0') as trabajadas " \
                          " from sagest_trabajadordiajornada tj1 where tj1.status=true and tj1.persona_id=tabla.personaid and extract(year from tj1.fecha)="+ anio +" and extract(month from tj1.fecha)=8),'000:00:00') as trabajadas_agosto, " \
                          " COALESCE((select lpad(cast((sum(tj1.totalsegundostrabajados) / 3600) as text),3,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados)/ 60 - 60 * (sum(tj1.totalsegundostrabajados) / 3600)) as text),2,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados) - sum(tj1.totalsegundostrabajados) / 60 * 60) as text),2,'0') as trabajadas " \
                          " from sagest_trabajadordiajornada tj1 where tj1.status=true and tj1.persona_id=tabla.personaid and extract(year from tj1.fecha)="+ anio +" and extract(month from tj1.fecha)=9),'000:00:00') as trabajadas_septiembre, " \
                          " COALESCE((select lpad(cast((sum(tj1.totalsegundostrabajados) / 3600) as text),3,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados)/ 60 - 60 * (sum(tj1.totalsegundostrabajados) / 3600)) as text),2,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados) - sum(tj1.totalsegundostrabajados) / 60 * 60) as text),2,'0') as trabajadas " \
                          " from sagest_trabajadordiajornada tj1 where tj1.status=true and tj1.persona_id=tabla.personaid and extract(year from tj1.fecha)="+ anio +" and extract(month from tj1.fecha)=10),'000:00:00') as trabajadas_octubre, " \
                          " COALESCE((select lpad(cast((sum(tj1.totalsegundostrabajados) / 3600) as text),3,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados)/ 60 - 60 * (sum(tj1.totalsegundostrabajados) / 3600)) as text),2,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados) - sum(tj1.totalsegundostrabajados) / 60 * 60) as text),2,'0') as trabajadas " \
                          " from sagest_trabajadordiajornada tj1 where tj1.status=true and tj1.persona_id=tabla.personaid and extract(year from tj1.fecha)="+ anio +" and extract(month from tj1.fecha)=11),'000:00:00') as trabajadas_noviembre, " \
                          " COALESCE((select lpad(cast((sum(tj1.totalsegundostrabajados) / 3600) as text),3,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados)/ 60 - 60 * (sum(tj1.totalsegundostrabajados) / 3600)) as text),2,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados) - sum(tj1.totalsegundostrabajados) / 60 * 60) as text),2,'0') as trabajadas " \
                          " from sagest_trabajadordiajornada tj1 where tj1.status=true and tj1.persona_id=tabla.personaid and extract(year from tj1.fecha)="+ anio +" and extract(month from tj1.fecha)=12),'000:00:00') as trabajadas_diciembre, " \
                          " COALESCE((select lpad(cast((sum(tj1.totalsegundostrabajados) / 3600) as text),4,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados)/ 60 - 60 * (sum(tj1.totalsegundostrabajados) / 3600)) as text),2,'0')||':'||lpad(cast((sum(tj1.totalsegundostrabajados) - sum(tj1.totalsegundostrabajados) / 60 * 60) as text),2,'0') as trabajadas " \
                          " from sagest_trabajadordiajornada tj1 where tj1.status=true and tj1.persona_id=tabla.personaid and extract(year from tj1.fecha)="+ anio +"),'0000:00:00') as trabajadas_total " \
                          " from (select p.id as personaid, p.id, (p.apellido1||' '||p.apellido2||' '||p.nombres) as persona, (case p.sexo_id when 1 then 'FEMENINO' else 'MASCULINO' end) as sexo " \
                          " from sagest_trabajadordiajornada t   " \
                          " inner join sagest_distributivopersona d on d.estadopuesto_id=1 and d.status=true and t.persona_id=d.persona_id " \
                          " inner join sga_persona p on p.id=d.persona_id and p.status=true   " \
                          " inner join sagest_regimenlaboral r on r.id=d.regimenlaboral_id and r.status=true " \
                          " left join sagest_logdia l on l.status=true and  p.id=l.persona_id and t.persona_id=p.id and t.fecha=l.fecha " \
                          " where r.id=1 and extract(year from t.fecha)="+ anio +"   " \
                          " and t.fecha not in (select dl.fecha from sga_diasnolaborable dl where dl.status=true and extract(year from dl.fecha)="+ anio +" " \
                          " and dl.periodo_id is null) GROUP BY personaid order by persona) as tabla " \
                          " inner join sagest_distributivopersona d on d.estadopuesto_id=1 and d.status=true and d.persona_id=tabla.personaid " \
                          " inner join sagest_denominacionpuesto de on de.id=d.denominacionpuesto_id and de.status=true " \
                          " inner join sagest_departamento depa on d.unidadorganica_id=depa.id and depa.status=true " \
                          " left join (select p1.motivo, p1.solicita_id, d1.fechainicio, d1.fechafin from sagest_permisoinstitucional p1, sagest_permisoinstitucionaldetalle d1 " \
                          " where p1.id=d1.permisoinstitucional_id and p1.status=true and d1.status=true    " \
                          " and p1.estadosolicitud=3 and  (d1.fechainicio-CAST('60 days' AS INTERVAL)) <= '"+ anio +"-01-01' and (d1.fechafin+CAST('60 days' AS INTERVAL))>='"+ anio +"-12-31') as permiso " \
                          " on permiso.solicita_id=tabla.personaid and permiso.fechainicio<='"+ anio +"-01-01' and permiso.fechafin>='"+ anio +"-12-31'  " \
                          "  order by departamento, tabla.persona"
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    row_num = 2
                    persona = ""
                    listado_persona = []
                    for per in results:
                        ws.write(row_num, 0, per[0], font_style2)
                        ws.write(row_num, 1, per[1], font_style2)
                        ws.write(row_num, 2, per[2], font_style2)
                        ws.write(row_num, 3, per[3], font_style2)
                        ws.write(row_num, 4, per[4], font_style2)
                        ws.write(row_num, 5, per[5], font_style2)
                        ws.write(row_num, 6, per[6], font_style2)
                        ws.write(row_num, 7, per[7], font_style2)
                        ws.write(row_num, 8, per[8], font_style2)
                        ws.write(row_num, 9, per[9], font_style2)
                        ws.write(row_num, 10, per[10], font_style2)
                        ws.write(row_num, 11, per[11], font_style2)
                        ws.write(row_num, 12, per[12], font_style2)
                        ws.write(row_num, 13, per[13], font_style2)
                        ws.write(row_num, 14, per[14], font_style2)
                        ws.write(row_num, 15, per[15], font_style2)
                        ws.write(row_num, 16, per[16], font_style2)
                        row_num += 1
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Consulta de Marcadas.'
            data['fecha'] = fecha = date(int(request.GET['fecha'][6:10]), int(request.GET['fecha'][3:5]), int(request.GET['fecha'][0:2])) if 'fecha' in request.GET else datetime.now().date()
            plantillas = TrabajadorDiaJornada.objects.filter(fecha=fecha, persona__distributivopersona__isnull=False).order_by('persona')
            data['dias'] = plantillas
            return render(request, "th_marcadas/detallemarcadastrabajador.html", data)
