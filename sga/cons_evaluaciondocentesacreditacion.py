# -*- coding: latin-1 -*-
import xlwt
from django.template.loader import get_template
from django.template import Context
from xlwt import *
import random
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from sga.funciones import log, elimina_tildes, MiPaginador
from django.db.models import Sum, Q
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.models import Profesor, Carrera, Matricula, RespuestaEvaluacionAcreditacion, DetalleRespuestaRubrica, \
    RespuestaRubrica, ProfesorMateria, Coordinacion, ActividadDetalleDistributivoCarrera, DetalleDistributivo, ProfesorDistributivoHoras


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    periodo = data['periodo']
    data['proceso'] = proceso = periodo.proceso_evaluativo()
    if 'idtipoinstrumento' in request.GET:
        idtipoinstrumento = request.GET['idtipoinstrumento']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'delete':
            try:
                detrespuesrubrica = DetalleRespuestaRubrica.objects.filter(respuestarubrica__respuestaevaluacion=request.POST['id'])
                detrespuesrubrica.delete()
                respuestarubrica = RespuestaRubrica.objects.filter(respuestaevaluacion=request.POST['id'])
                respuestarubrica.delete()
                respuestaevaluacion = RespuestaEvaluacionAcreditacion.objects.filter(pk=request.POST['id'])
                log(u"Elimino Evaluacion Tipo Instrumento: %s -%s" % (idtipoinstrumento, elimina_tildes(respuestaevaluacion)), request, "del")
                respuestaevaluacion.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'deleteevaluacion':
            try:
                evaluacion =RespuestaEvaluacionAcreditacion.objects.get(pk=request.POST['id'])
                log(u"Elimino Evaluacion docentes de acreditacion: %s [%s]" % (evaluacion, evaluacion.id), request, "del")
                evaluacion.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'delete':
                try:
                    data['title'] = u'Eliminar Evaluación'
                    data['evaluaciones'] = tipo = RespuestaEvaluacionAcreditacion.objects.get(pk=request.GET['id'])
                    data['tipoinstrumento'] = tipo.tipoinstrumento
                    data['idc'] = request.GET['idc']
                    return render(request, 'cons_evaluaciondocentesacreditacion/delete.html', data)
                except Exception as ex:
                    pass

            if action == 'verevaluacion':
                try:
                    data['title'] = u'Docentes Evaluados'
                    data['carrera'] = Carrera.objects.get(pk=request.GET['idcar'])
                    data['estudiante'] = almatricula = Matricula.objects.get(pk=request.GET['matriculaid'])
                    data['evaluaciones'] = RespuestaEvaluacionAcreditacion.objects.filter(proceso__periodo=periodo,evaluador=almatricula.inscripcion.persona,tipoinstrumento=1)
                    return render(request, "cons_evaluaciondocentesacreditacion/listaevaluacion.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteevaluacion':
                try:
                    data['title'] = u'Eliminar Evaluación'
                    data['matriculaid'] = request.GET['matriculaid']
                    data['idcar'] = request.GET['idcar']
                    data['evaluacion'] = RespuestaEvaluacionAcreditacion.objects.get(pk=request.GET['idevaluacion'])
                    return render(request, "cons_evaluaciondocentesacreditacion/deleteevaluacion.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteauto':
                try:
                    data['title'] = u'Eliminar Autoevaluación'
                    data['evaluaciones'] = tipo = RespuestaEvaluacionAcreditacion.objects.get(pk=request.GET['id'])
                    data['tipoinstrumento'] = tipo.tipoinstrumento
                    data['idc'] = request.GET['idc']
                    return render(request, 'cons_evaluaciondocentesacreditacion/deleteauto.html', data)
                except Exception as ex:
                    pass

            if action == 'detallerubrica':
                try:
                    data = {}
                    data['proceso'] = proceso
                    data['nomprofe'] = nomprofe = Profesor.objects.get(pk=request.GET['idprofe'])
                    data['listadorubricasevaluadas'] = RespuestaRubrica.objects.filter(respuestaevaluacion__proceso__periodo=periodo,respuestaevaluacion__profesor=nomprofe, respuestaevaluacion__tipoinstrumento__in=[2,3,4]).order_by('respuestaevaluacion__tipoinstrumento','rubrica__nombre')
                    template = get_template("cons_evaluaciondocentesacreditacion/detallerubrica.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'deletedetalleevaluacionrubrica':
                try:
                    data = {}
                    data['proceso'] = proceso
                    detallerespuestarubrica = RespuestaRubrica.objects.get(pk=request.GET['id'])
                    log(u"Elimino detalle Evaluacion Tipo Instrumento: %s -%s" % (detallerespuestarubrica.respuestaevaluacion.tipoinstrumento, elimina_tildes(detallerespuestarubrica.respuestaevaluacion)), request, "del")
                    detallerespuestarubrica.delete()
                    data['nomprofe'] = nomprofe = Profesor.objects.get(pk=request.GET['idprofe'])
                    data['listadorubricasevaluadas'] = RespuestaRubrica.objects.filter(respuestaevaluacion__proceso__periodo=periodo,respuestaevaluacion__profesor=nomprofe, respuestaevaluacion__tipoinstrumento__in=[2,3,4]).order_by('respuestaevaluacion__tipoinstrumento','rubrica__nombre')
                    template = get_template("cons_evaluaciondocentesacreditacion/detallerubrica.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'excelfaltantesevaluar':
                try:
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    # ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Faltantes_Evaluar' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"FACULTAD", 8000),
                        (u"CARRERA", 8000),
                        (u"TIPO", 2500),
                        (u"CEDULA", 4500),
                        (u"EVALUADO", 10000),
                        (u"EVALUADOR", 10000),
                        (u"FECHA / HORA PROGRAMADO PAR", 10000),
                        (u"LUGAR PROGRAMADO PAR", 10000),
                        (u"FECHA / HORA PROGRAMADO DIRECTIVO", 10000),
                        (u"LUGAR PROGRAMADO DIRECTIVO", 10000),
                    ]
                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    lista = request.GET['cadenatexto']
                    elementos = lista.split(',')
                    nomfacultad = Coordinacion.objects.get(pk=request.GET['idcoor'])
                    nomcarrera = Carrera.objects.get(pk=request.GET['idcar'])
                    row_num = 1
                    for elemento in elementos:
                        individuales = elemento.split('_')
                        profesor = Profesor.objects.get(persona__cedula=individuales[0])
                        i = 0
                        campo1 = individuales[3]
                        campo2 = individuales[0]
                        campo3 = individuales[1]
                        if individuales[2] == 'AUTOEVALUACION':
                            campo4 = ''
                        else:
                            campo4 = individuales[2]
                        campo5 = nomfacultad.nombre
                        campo6 = nomcarrera.nombre + ' ' + nomcarrera.mencion
                        programadapar = profesor.profesorfechaparessincoor(periodo)
                        programadadirectivo = profesor.profesorfechaparessincoor(periodo)
                        campo7 = ""
                        campo8 = ""
                        campo9 = ""
                        campo10 = ""
                        if programadapar:
                            campo7 = programadapar.fecha.strftime("%d/%m/%Y") + " hora inicio " + programadapar.horainicio.strftime("%H:%M")+ " hora fin " + programadapar.horafin.strftime("%H:%M")
                            campo8 = programadapar.lugar.upper()
                        if programadadirectivo:
                            campo9 = programadadirectivo.fecha.strftime("%d/%m/%Y") + " hora inicio " + programadadirectivo.horainicio.strftime("%H:%M") + " hora fin " + programadadirectivo.horafin.strftime("%H:%M")
                            campo10 = programadadirectivo.lugar.upper()
                        ws.write(row_num, 0, campo5, font_style2)
                        ws.write(row_num, 1, campo6, font_style2)
                        ws.write(row_num, 2, campo1, font_style2)
                        ws.write(row_num, 3, campo2, font_style2)
                        ws.write(row_num, 4, campo3, font_style2)
                        ws.write(row_num, 5, campo4, font_style2)
                        ws.write(row_num, 6, campo7, font_style2)
                        ws.write(row_num, 7, campo8, font_style2)
                        ws.write(row_num, 8, campo9, font_style2)
                        ws.write(row_num, 9, campo10, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

        else:
            search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
            listahoras = []
            llenardocentes = []
            codigocarrera = 0
            if not request.session['periodo'].visible:
                return HttpResponseRedirect("/?info=Periodo Inactivo.")
            data['title'] = u'Consulta de evaluaciones docentes'


            # data['profesores'] = Profesor.objects.filter(profesormateria__principal=True, profesormateria__materia__asignaturamalla__malla__carrera=data['carrera'], profesormateria__materia__nivel__periodo=data['periodo']).distinct()
            # data['profe'] = listaprofesores = ProfesorMateria.objects.values_list('profesor__id', 'profesor__persona__apellido1', 'profesor__persona__apellido2', 'profesor__persona__nombres', 'materia__asignaturamalla__malla__carrera__nombre', 'materia__asignaturamalla__malla__carrera__id', 'profesor__coordinacion__alias', 'profesor__categoria__nombre').filter(materia__nivel__periodo=proceso.periodo).distinct().annotate(prom=Sum('hora')).order_by('profesor__persona__apellido1', 'profesor__persona__apellido2', '-prom')
            # data['profe'] = listaprofesores = ProfesorDistributivoHoras.objects.filter(periodo=proceso.periodo).order_by('profesor__persona__apellido1', 'profesor__persona__apellido2')
            # estudiantes = Matricula.objects.filter(inscripcion__carrera=data['carrera'], nivel__periodo=data['periodo']).distinct().order_by('inscripcion')
            # url_vars += "&action=docentesevaluar&idmodalidad=" + request.GET['idmodalidad'] + "&idtipoprofesor=" + request.GET['idtipoprofesor']
            listadocentes = ProfesorDistributivoHoras.objects.filter(periodo=proceso.periodo, periodo__tipo=proceso.periodo.tipo, profesor__persona__real=True, status=True).order_by('profesor__persona__apellido1', 'profesor__persona__apellido2')
            data['carreras'] = carreras = Carrera.objects.filter(pk__in=listadocentes.values_list('carrera_id'), activa=True)
            if 's' in request.GET:
                search = request.GET['s']
                url_vars += f"&s={search}"
                ss = search.split(' ')
                if len(ss) == 1:
                    listadocentes = listadocentes.filter(Q(profesor__persona__nombres__icontains=search) |
                                                         Q(profesor__persona__apellido1__icontains=search) |
                                                         Q(profesor__persona__apellido2__icontains=search) |
                                                         Q(profesor__persona__cedula__icontains=search) |
                                                         Q(profesor__persona__pasaporte__icontains=search))
                else:
                    listadocentes = listadocentes.filter(Q(profesor__persona__apellido1__icontains=ss[0]) &
                                                         Q(profesor__persona__apellido2__icontains=ss[1]))
            idc = 0
            if 'idc' in request.GET:
                data['idc'] = idc = request.GET['idc']
                codigocarrera = request.GET['idc']
                data['idcoor'] = 0
                if idc == 'N':
                    listadocentes = listadocentes.filter(carrera__isnull=True)
                else:
                    data['idc'] = idc = int(request.GET['idc'])
                    codigocarrera = int(request.GET['idc'])
                    if idc > 0:
                        listadocentes = listadocentes.filter(carrera_id=idc)
            else:
                data['carrera'] = carreras[0]
                # data['idc'] = idc = carreras[0].id
                data['idc'] = 0
                data['idcoor'] = carreras[0].coordinaciones()[0]

            url_vars += "&idc=" + str(idc)
            numerofilas = 25
            paging = MiPaginador(listadocentes, numerofilas)
            p = 1
            try:
                paginasesion = 1
                if 'paginador' in request.session:
                    paginasesion = int(request.session['paginador'])
                if 'page' in request.GET:
                    p = int(request.GET['page'])
                    if p == 1:
                        numerofilasguiente = numerofilas
                    else:
                        numerofilasguiente = numerofilas * (p - 1)
                else:
                    p = paginasesion
                    if p == 1:
                        numerofilasguiente = numerofilas
                    else:
                        numerofilasguiente = numerofilas * (p - 1)
                try:
                    page = paging.page(p)
                except:
                    p = 1
                page = paging.page(p)
            except:
                page = paging.page(p)
            request.session['paginador'] = p
            data['numeropagina'] = p
            data['numerofilasguiente'] = numerofilasguiente
            data['paging'] = paging
            data['rangospaging'] = paging.rangos_paginado(p)
            data['page'] = page
            data['search'] = search if search else ""
            # data['estudiantes'] = page.object_list
            # for p in listaprofesores:
            #     b = 0
            #     ingreso = 0
            #     for x in listahoras:
            #         if p[0] == x[0]:
            #             b = 1
            #     if b == 0:
            #         listahoras.append(p)
            # for llenardoc in listahoras:
            #     if llenardoc[5] == data['idc']:
            #         llenardocentes.append(llenardoc[0])
            # docentesdirectores = ActividadDetalleDistributivoCarrera.objects.values_list('actividaddetalle__criterio__distributivo__profesor_id', flat=True).filter(
            #     actividaddetalle__criterio__distributivo__periodo=periodo,carrera_id=codigocarrera,status=True).distinct()
            # data['listaestudiodoctorados'] = DetalleDistributivo.objects.filter(distributivo__periodo=periodo, hetero=True, criteriogestionperiodo__criterio_id=35,criteriodocenciaperiodo__isnull=True).distinct().order_by('distributivo__profesor__persona__apellido1')
            # listadoc1 = Profesor.objects.filter(pk__in=docentesdirectores)
            # listadoc2 = Profesor.objects.filter(pk__in=llenardocentes)
            # data['profesores'] = listadoc1 | listadoc2
            data['listadoprofesores'] = page.object_list
            data["url_vars"] = url_vars
            return render(request, "cons_evaluaciondocentesacreditacion/view.html", data)