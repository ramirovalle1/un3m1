# -*- coding: latin-1 -*-
import json
import random
import sys
from datetime import datetime
from decimal import Decimal
import os
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Q, F, FloatField
from django.db.models.functions import Coalesce
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from xlwt import *
from decorators import secure_module, last_access
from sagest.models import DistributivoPersona
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import variable_valor, generar_nombre, log, null_to_numeric
from sga.models import Inscripcion, Periodo, Carrera, Matricula, miinstitucion, MatriculaNovedad, CUENTAS_CORREOS, \
    Persona, UbicacionPersona, Nivel, NivelMalla, Coordinacion, Modalidad, DetPersonaPadronElectoral
from django.template import Context
from django.template.loader import get_template
from sga.tasks import send_html_mail, conectar_cuenta
from django.db.models import Q, Sum, Count, Max, F, Avg
from django.db.models.functions import Cast
from django.db.models import FloatField


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    data['periodo_actual'] = periodo = request.session['periodo']
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'reiniciarLocalidad':
            try:
                id = int(request.POST['id'])
                ubipersonas = UbicacionPersona.objects.get(pk=id)
                ubipersonas.actual = False
                ubipersonas.save(request)
                persona = Persona.objects.get(pk=ubipersonas.persona.pk)
                persona.localizacionactualizada = False
                persona.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                return JsonResponse({"result": "bad", "mensaje": str(ex)})
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        adduserdata(request, data)
        data['title'] = u'Ubicación Personas'
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'listaPersonaUbicacion':
                try:
                    qs_base = UbicacionPersona.objects.filter(status=True, actual=True)
                    ubipersonas = json.dumps(list(qs_base.values('id', 'latitud', 'longitud', 'persona__nombres', 'persona__apellido1', 'persona__apellido2', 'persona__canton__nombre', 'persona__provincia__nombre')))
                    return JsonResponse({"result": "ok", "cantidad": qs_base.count(), "listado": ubipersonas})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
            if action == 'listaPersonaUbicacionFiltros':
                try:
                    tipo = int(request.GET['tipo'])
                    ubipersonas = UbicacionPersona.objects.select_related('persona').filter(status=True, actual=True)
                    querypersona = Persona.objects.select_related().filter(status=True)
                    if tipo == 0:
                        pass
                    elif tipo == 1:
                        periodo_id = int(request.GET['periodo'])
                        modalidad_id = int(request.GET['modalidad'])
                        coordinacion = request.GET.getlist('coordinacion[]')
                        nivel_ids = request.GET.getlist('nivel[]')
                        periodo_get = Periodo.objects.get(pk=periodo_id)
                        matriculas_periodo = Matricula.objects.select_related('inscripcion').filter(status=True, nivel__periodo=periodo_get, retiradomatricula=False)
                        aplicatodos = len(request.GET.getlist('coordinacion[]')) == 1 and request.GET.getlist('coordinacion[]')[0] == '0'
                        aplicatodosnivel = len(request.GET.getlist('nivel[]')) == 1 and request.GET.getlist('nivel[]')[0] == '0'
                        if not aplicatodos:
                            matriculas_periodo = matriculas_periodo.filter(inscripcion__coordinacion__in=coordinacion)
                        if not aplicatodosnivel:
                            matriculas_periodo = matriculas_periodo.filter(nivelmalla__in=nivel_ids)
                        if modalidad_id > 0:
                            matriculas_periodo = matriculas_periodo.filter(inscripcion__modalidad_id=modalidad_id)
                        listapersonas = matriculas_periodo.values_list('inscripcion__persona_id', flat=True)
                        ubipersonas = ubipersonas.filter(persona__in=listapersonas)
                        querypersona = querypersona.filter(id__in=listapersonas)
                    elif tipo == 2:
                        ubipersonas = ubipersonas.filter(persona__perfilusuario__profesor__isnull=False, persona__perfilusuario__profesor__activo=True).filter(persona__perfilusuario__profesor__nivelcategoria_id=1).exclude(persona__apellido1__icontains='TECNICO').exclude(persona__apellido1__icontains='ADMISION').exclude(persona__apellido1__icontains='FACULTAD').exclude(persona__apellido1__icontains='CONTRATO').exclude(persona__apellido1__icontains='DOCENTE').exclude(persona__apellido1__iexact='DERECHO')
                        querypersona = querypersona.filter(perfilusuario__profesor__isnull=False, perfilusuario__profesor__activo=True).filter(perfilusuario__profesor__nivelcategoria_id=1).exclude(apellido1__icontains='TECNICO').exclude(apellido1__icontains='ADMISION').exclude(apellido1__icontains='FACULTAD').exclude(apellido1__icontains='CONTRATO').exclude(apellido1__icontains='DOCENTE').exclude(apellido1__iexact='DERECHO')
                    elif tipo == 3:
                        distributivopersonalist = DistributivoPersona.objects.filter(status=True, regimenlaboral_id=1, modalidadlaboral_id=1).values_list('persona_id',flat=True)
                        ubipersonas = ubipersonas.filter(persona__perfilusuario__administrativo__isnull=False, persona__administrativo__activo=True, persona__id__in=distributivopersonalist)
                        querypersona = querypersona.filter(perfilusuario__administrativo__isnull=False, perfilusuario__administrativo__activo=True, id__in=distributivopersonalist)
                    listaciudades = querypersona.values_list('canton', flat=True).annotate(total=Count('canton')).values('canton__nombre', 'canton__provincia__nombre', 'canton__provincia__pais__nombre', 'total').order_by('-total')
                    listaretorno = json.dumps(list(ubipersonas.values('id', 'latitud', 'longitud', 'persona__nombres', 'persona__apellido1', 'persona__apellido2', 'persona__canton__nombre', 'persona__provincia__nombre', 'persona__pais__nombre')))
                    data['listadociudades'] = listaciudades
                    data['totalpersonas'] = querypersona.count()
                    data['totalpersonasmapa'] = ubipersonas.count()
                    template = get_template("adm_ubicacionestudiantes/datoscanton.html")
                    return JsonResponse({"result": "ok", "cantidad": ubipersonas.count(), "listado": listaretorno, 'data': template.render(data)})
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return JsonResponse({"result": "bad", "mensaje": str(ex)})
            if action == 'excelUbicaciones':
                try:
                    tipo = int(request.GET['tipo'])
                    querypersona = Persona.objects.select_related().filter(status=True)
                    periodo_get = None
                    if tipo == 0:
                        pass
                    elif tipo == 1:
                        periodo_id = int(request.GET['periodo'])
                        modalidad_id = int(request.GET['modalidad'])
                        coordinacion = request.GET['coordinacion'].split(',')
                        nivel_ids = request.GET['nivel'].split(',')
                        periodo_get = Periodo.objects.get(pk=periodo_id)
                        matriculas_periodo = Matricula.objects.select_related('inscripcion').filter(status=True, nivel__periodo=periodo_get)
                        aplicatodos = coordinacion[0] == '0'
                        aplicatodosnivel = nivel_ids[0] == '0'
                        if not aplicatodos:
                            matriculas_periodo = matriculas_periodo.filter(inscripcion__coordinacion__in=coordinacion)
                        if not aplicatodosnivel:
                            matriculas_periodo = matriculas_periodo.filter(nivelmalla__in=nivel_ids)
                        if modalidad_id  > 0:
                            matriculas_periodo = matriculas_periodo.filter(inscripcion__modalidad_id=modalidad_id)
                        listapersonas = matriculas_periodo.values_list('inscripcion__persona_id',flat=True)
                        querypersona = querypersona.filter(id__in=listapersonas)
                    elif tipo == 2:
                        querypersona = querypersona.filter(perfilusuario__profesor__isnull=False, perfilusuario__profesor__activo=True).filter(perfilusuario__profesor__nivelcategoria_id=1).exclude(apellido1__icontains='TECNICO').exclude(apellido1__icontains='ADMISION').exclude(apellido1__icontains='FACULTAD').exclude(apellido1__icontains='CONTRATO').exclude(apellido1__icontains='DOCENTE').exclude(apellido1__iexact='DERECHO')
                    elif tipo == 3:
                        # distributivopersonalist = DistributivoPersona.objects.filter(status=True, regimenlaboral_id=1, modalidadlaboral_id=1).values_list('persona_id',flat=True)
                        # querypersona = querypersona.filter(perfilusuario__administrativo__isnull=False, perfilusuario__administrativo__activo=True, id__in=distributivopersonalist)
                        distributivopersonalist = DetPersonaPadronElectoral.objects.filter(status=True, tipo=3).values_list('persona__id',flat=True)
                        querypersona = querypersona.filter(perfilusuario__administrativo__isnull=False, perfilusuario__administrativo__activo=True, id__in=distributivopersonalist)
                    #INICIO EXCEL
                    __author__ = 'UNIVERSIDAD ESTATAL DE MILAGRO'
                    title = easyxf(
                        'font: name Calibri, color-index black, bold on , height 350; alignment: horiz centre')
                    fuentecabecera = easyxf(
                        'font: name Calibri, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf(
                        'font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentetexto = easyxf(
                        'font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    borders = Borders()
                    borders.left = Borders.THIN
                    borders.right = Borders.THIN
                    borders.top = Borders.THIN
                    borders.bottom = Borders.THIN
                    align = Alignment()
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style.borders = borders
                    font_style.alignment = align
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    font_style2.borders = borders
                    font_style2.alignment = align
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('LISTADO PERSONAS')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=ubicacion_personas' + random.randint(1, 10000).__str__() + '.xls'
                    ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    titulo_archivo = 'TODOS'
                    if tipo != 0:
                        if tipo == 1:
                            if periodo_get:
                                titulo_archivo = 'ESTUDIANTES {}'.format(periodo_get.nombre)
                            else:
                                titulo_archivo = 'ESTUDIANTES'
                        if tipo == 2:
                            titulo_archivo = 'DOCENTES'
                        if tipo == 3:
                            titulo_archivo = 'ADMINISTRATIVOS'
                    ws.write_merge(1, 1, 0, 9, titulo_archivo, title)
                    ws.write_merge(2, 2, 0, 9, 'REPORTE DE UBICACIÓN {}'.format(str(datetime.now().date())), fuentenormal)
                    if tipo == 1:
                        columns = [
                            (u"APELLIDOS", 8000),
                            (u"NOMBRES", 8000),
                            (u"CANTON", 8000),
                            (u"PROVINCIA", 8000),
                            (u"PAIS", 8000),
                            (u"FACULTAD", 8000),
                            (u"CARRERA", 8000),
                            (u"NIVEL", 8000),
                            (u"MODALIDAD", 8000),
                            (u"¿INFORMACIÓN ACTUALIZADA?", 11000),
                        ]
                        row_num = 4
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                            ws.col(col_num).width = columns[col_num][1]
                        row_num = 5
                        count = 1
                        for i in querypersona:
                            ws.write_merge(row_num, row_num, 0, 0, "{} {}".format(i.apellido1, i.apellido2), font_style2)
                            ws.write_merge(row_num, row_num, 1, 1, i.nombres, font_style2)
                            ws.write_merge(row_num, row_num, 2, 2, i.canton.nombre if i.canton else '', font_style2)
                            ws.write_merge(row_num, row_num, 3, 3, i.canton.provincia.nombre if i.canton else '', font_style2)
                            ws.write_merge(row_num, row_num, 4, 4, i.canton.provincia.pais.nombre if i.canton else '', font_style2)
                            alumatricula = Matricula.objects.select_related('inscripcion').filter(status=True, nivel__periodo=periodo_get).filter(inscripcion__persona=i.pk).first()
                            facultadstr, carrerastr, nivelstr, modalidadstr = '', '', '', ''
                            if alumatricula:
                                facultadstr = alumatricula.nivel.coordinacion()
                                carrerastr = alumatricula.inscripcion.carrera.nombre if alumatricula.inscripcion.carrera else ''
                                nivelstr = alumatricula.nivelmalla.nombre if alumatricula.nivelmalla else ''
                                modalidadstr = alumatricula.inscripcion.modalidad.nombre if alumatricula.inscripcion.modalidad else ''
                            ws.write_merge(row_num, row_num, 5, 5, str(facultadstr), font_style2)
                            ws.write_merge(row_num, row_num, 6, 6, carrerastr, font_style2)
                            ws.write_merge(row_num, row_num, 7, 7, nivelstr, font_style2)
                            ws.write_merge(row_num, row_num, 8, 8, modalidadstr, font_style2)
                            ws.write_merge(row_num, row_num, 9, 9, 'SI' if i.localizacionactualizada else 'NO', font_style2)
                            row_num += 1
                    elif tipo == 3:
                        columns = [
                            (u"APELLIDOS", 8000),
                            (u"NOMBRES", 8000),
                            (u"CANTON", 8000),
                            (u"PROVINCIA", 8000),
                            (u"PAIS", 8000),
                            (u"MODALIDAD LABORAL", 8000),
                            (u"ESTADO DEL PUESTO", 8000),
                            (u"¿INFORMACIÓN ACTUALIZADA?", 11000),
                        ]
                        row_num = 4
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                            ws.col(col_num).width = columns[col_num][1]
                        row_num = 5
                        count = 1
                        for i in querypersona:
                            ws.write_merge(row_num, row_num, 0, 0, "{} {}".format(i.apellido1, i.apellido2), font_style2)
                            ws.write_merge(row_num, row_num, 1, 1, i.nombres, font_style2)
                            ws.write_merge(row_num, row_num, 2, 2, i.canton.nombre if i.canton else '', font_style2)
                            ws.write_merge(row_num, row_num, 3, 3, i.canton.provincia.nombre if i.canton else '', font_style2)
                            ws.write_merge(row_num, row_num, 4, 4, i.canton.provincia.pais.nombre if i.canton else '', font_style2)
                            distributivo = i.distributivopersona_set.filter(status=True).order_by('id').last()
                            if distributivo:
                                ws.write_merge(row_num, row_num, 5, 5, distributivo.modalidadlaboral.descripcion if distributivo.modalidadlaboral else '', font_style2)
                                ws.write_merge(row_num, row_num, 6, 6, distributivo.estadopuesto.descripcion if distributivo.estadopuesto else '', font_style2)
                            ws.write_merge(row_num, row_num, 7, 7, 'SI' if i.localizacionactualizada else 'NO', font_style2)
                            row_num += 1
                    else:
                        columns = [
                            (u"APELLIDOS", 8000),
                            (u"NOMBRES", 8000),
                            (u"CANTON", 8000),
                            (u"PROVINCIA", 8000),
                            (u"PAIS", 8000),
                            (u"¿INFORMACIÓN ACTUALIZADA?", 11000),
                        ]
                        row_num = 4
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                            ws.col(col_num).width = columns[col_num][1]
                        row_num = 5
                        count = 1
                        for i in querypersona:
                            ws.write_merge(row_num, row_num, 0, 0, "{} {}".format(i.apellido1, i.apellido2), font_style2)
                            ws.write_merge(row_num, row_num, 1, 1, i.nombres, font_style2)
                            ws.write_merge(row_num, row_num, 2, 2, i.canton.nombre if i.canton else '', font_style2)
                            ws.write_merge(row_num, row_num, 3, 3, i.canton.provincia.nombre if i.canton else '', font_style2)
                            ws.write_merge(row_num, row_num, 4, 4, i.canton.provincia.pais.nombre if i.canton else '', font_style2)
                            ws.write_merge(row_num, row_num, 5, 5, 'SI' if i.localizacionactualizada else 'NO', font_style2)
                            row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": str(ex)})
            return HttpResponseRedirect(request.path)
        else:
            data['niveles'] = niveles = NivelMalla.objects.filter(status=True).order_by('orden')
            data['periodos_lista'] = periodos = Periodo.objects.filter(status=True).order_by('-pk')
            data['modalidad_lista'] = modalidad = Modalidad.objects.filter(status=True).order_by('-pk')
            data['coordinaciones'] = coordinaciones = Coordinacion.objects.filter(status=True).order_by('nombre')
            return render(request, "adm_ubicacionestudiantes/mapaleatflet.html", data)