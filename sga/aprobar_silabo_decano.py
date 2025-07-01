# -*- coding: latin-1 -*-
import random
from datetime import datetime

import xlwt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template
from xlwt import *

from decorators import secure_module, last_access
from settings import ARCHIVO_TIPO_SYLLABUS
from sga.commonviews import adduserdata
from sga.forms import ArchivoForm
from sga.funciones import MiPaginador, log, variable_valor
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import Archivo, ProfesorMateria, Materia, Silabo, \
    Malla, NivelMalla, AprobarSilabo, \
    GPGuiaPracticaSemanal, AprobarSilaboDecano, Carrera


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    # miscarreras = Carrera.objects.filter(coordinadorcarrera__in=persona.gruposcarrera(periodo)).distinct()
    miscoordinaciones = persona.mis_coordinaciones()
    # Carrera.objects.filter(grupocoordinadorcarrera__group__in=persona.grupos()).distinct()
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == ' ':
                try:
                    form = ArchivoForm(request.POST)
                    if form.is_valid():
                        materia = Archivo.objects.filter(pk=request.POST['id'])[0].materia
                        profesor = materia.profesormateria_set.filter(status=True, principal=True)[0].profesor
                        Archivo.objects.filter(materia=materia).update(aprobado=False)
                        archivopdf = Archivo.objects.filter(materia=materia, tipo_id=ARCHIVO_TIPO_SYLLABUS, profesor=profesor, archivo__contains='.pdf').order_by('-id')[0]
                        archivopdf.aprobado = form.cleaned_data['aprobado']
                        archivopdf.observacion = form.cleaned_data['observacion']
                        archivopdf.save(request)
                        archivoword = Archivo.objects.filter(materia=materia, tipo_id=ARCHIVO_TIPO_SYLLABUS, profesor=profesor, archivo__contains='.doc').order_by('-id')[0]
                        archivoword.aprobado = form.cleaned_data['aprobado']
                        archivoword.observacion = form.cleaned_data['observacion']
                        archivoword.save(request)
                        log(u'Aprobo silabo: %s' % materia, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'mostrarsilabodigital':
                try:
                    if 'idm' in request.POST:
                        silabo = Silabo.objects.get(pk=int(request.POST['ids']), status=True)
                        if silabo.materia.asignaturamalla.malla.carrera.modalidad == 3:
                            return conviert_html_to_pdf(
                                'pro_planificacion/silabo_virtual3_pdf.html' if periodo.id >= 112 else 'pro_planificacion/silabo_virtual2_pdf.html' if periodo.id >= 95 else 'pro_planificacion/silabo_virtual_pdf.html',
                                {
                                    'pagesize': 'A4',
                                    'data': silabo.silabo_virtual2_pdf() if periodo.id >= 95 else silabo.silabo_virtual_pdf(),
                                }
                            )
                        else:
                            return conviert_html_to_pdf(
                                'pro_planificacion/silabo_2_pdf.html' if periodo.id >= 112 else 'pro_planificacion/silabo_pdf.html',
                                {
                                    'pagesize': 'A4',
                                    'data': silabo.silabo_pdf(),
                                }
                            )
                except Exception as ex:
                    pass

            if action == 'programaanalitico_pdf':
                try:
                    materia = Materia.objects.get(pk=request.POST['id'])
                    data['proanalitico'] = pro = materia.asignaturamalla.programaanaliticoasignatura_set.filter(status=True, activo=True)[0]
                    return conviert_html_to_pdf(
                        'mallas/programanaliticoposgrado_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': pro.plananalitico_pdf(periodo),
                            'materia':materia,'periodo':periodo
                        }
                    )
                except Exception as ex:
                    pass

            if action == 'aprobar_silabo':
                try:
                    if 'id' in request.POST and 'st' in request.POST and 'obs' in request.POST:
                        silabo = Silabo.objects.get(pk=int(request.POST['id']))
                        aprobars = AprobarSilaboDecano(silabo=silabo,
                                                       observacion=request.POST['obs'],
                                                       persona=persona,
                                                       fecha=datetime.now(),
                                                      estadoaprobacion=request.POST['st'])
                        aprobars.save(request)
                        if variable_valor('APROBAR_SILABO') == int(request.POST['st']):
                            if silabo.materia.asignaturamalla.malla.carrera.coordinacion_carrera().id == 7:
                                silabo.aprobado = True
                                silabo.save(request)
                            log(u'Aprobó el sílabo %s el director: %s' % (silabo,persona), request, "add")
                            #silabo.materia.crear_actualizar_silabo_curso()
                        else:
                            aprobars = AprobarSilabo(silabo=silabo,
                                                     observacion=request.POST['obs'],
                                                     persona=persona,
                                                     fecha=datetime.now(),
                                                     estadoaprobacion=request.POST['st'])
                            aprobars.save(request)
                            log(u'Rechazó el sílabo %s el director: %s' % (silabo, persona), request, "add")
                        return JsonResponse({"result": "ok","idm":silabo.materia.id})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'detalleaprobacion':
                try:
                    data['silabo'] = silabo = Silabo.objects.get(pk=int(request.POST['id']))
                    data['historialaprobacion'] = silabo.aprobarsilabodecano_set.filter(status=True).order_by('-id').exclude(estadoaprobacion=variable_valor('PENDIENTE_SILABO'))
                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    template = get_template("aprobar_silabo_decano/detalleaprobacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            # if action == 'confirmarreactivo':
            #     try:
            #         materia = Materia.objects.get(pk=request.POST['id'])
            #         iddetalle = request.POST['iddetalle']
            #         reactivomateria = ReactivoMateria(materia = materia,
            #                                           fecha = datetime.now(),
            #                                           persona = persona,
            #                                           detallemodelo_id = iddetalle)
            #         reactivomateria.save(request)
            #         log(u'Confirmo Reactivo: %s' % reactivomateria, request, "add")
            #         return JsonResponse({"result": "ok"})
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})
            #
            # if action == 'eliminarconfirmacion':
            #     try:
            #         materia = Materia.objects.get(pk=request.POST['id'])
            #         iddetalle = request.POST['iddetalle']
            #         reactivomateria = ReactivoMateria.objects.filter(materia = materia,detallemodelo_id = iddetalle)
            #         log(u'Elimino Confirmacion Reactivo: %s' % reactivomateria, request, "del")
            #         reactivomateria.delete()
            #         return JsonResponse({"result": "ok"})
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})
            #
            # elif action == 'practicapdf':
            #     try:
            #         silabo = Silabo.objects.get(pk=int(request.POST['ids']))
            #         data['practicas'] = GPGuiaPracticaSemanal.objects.filter(status=True, silabosemanal__silabo=silabo).order_by('silabosemanal__numsemana')
            #         data['decano'] = silabo.materia.coordinacion_materia().responsable_periododos(silabo.materia.nivel.periodo, 1) if silabo.materia.coordinacion_materia().responsable_periododos(silabo.materia.nivel.periodo, 1) else None
            #         data['director'] = silabo.materia.asignaturamalla.malla.carrera.coordinador(silabo.materia.nivel.periodo, silabo.profesor.coordinacion.sede).persona.nombre_completo_inverso() if silabo.materia.asignaturamalla.malla.carrera.coordinador(silabo.materia.nivel.periodo, silabo.profesor.coordinacion.sede) else None
            #         return conviert_html_to_pdf(
            #             'pro_planificacion/practica_pdf.html',
            #             {
            #                 'pagesize': 'A4',
            #                 'data': data,
            #             }
            #         )
            #     except Exception as ex:
            #         pass
            #
            # elif action == 'practica_indpdf':
            #     try:
            #         practica = GPGuiaPracticaSemanal.objects.get(status=True, pk=int(request.POST['id']))
            #         data['practicas'] = GPGuiaPracticaSemanal.objects.filter(status=True, id=practica.id)
            #         data['decano'] = practica.silabosemanal.silabo.materia.coordinacion_materia().responsable_periododos(practica.silabosemanal.silabo.materia.nivel.periodo, 1) if practica.silabosemanal.silabo.materia.coordinacion_materia().responsable_periododos(practica.silabosemanal.silabo.materia.nivel.periodo, 1) else None
            #         data['director'] = practica.silabosemanal.silabo.materia.asignaturamalla.malla.carrera.coordinador(practica.silabosemanal.silabo.materia.nivel.periodo, practica.silabosemanal.silabo.profesor.coordinacion.sede).persona.nombre_completo_inverso() if practica.silabosemanal.silabo.materia.asignaturamalla.malla.carrera.coordinador(practica.silabosemanal.silabo.materia.nivel.periodo, practica.silabosemanal.silabo.profesor.coordinacion.sede) else None
            #         return conviert_html_to_pdf(
            #             'pro_planificacion/practica_pdf.html',
            #             {
            #                 'pagesize': 'A4',
            #                 'data': data,
            #             }
            #         )
            #     except Exception as ex:
            #         pass
            #
            # elif action == 'revisarpractica':
            #     try:
            #         if 'id' in request.POST and 'observacion' in request.POST and 'estado' in request.POST:
            #             if int(request.POST['id']) > 0 and int(request.POST['estado']) > 0:
            #                 estado = EstadoGuiaPractica(guipractica_id=request.POST['id'], observacion=request.POST['observacion'], fecha=datetime.now().date(), persona=persona, estado=request.POST['estado'])
            #                 estado.save(request)
            #                 log(u'Rechazo %s la guía de práctica: %s de la materia %s' % (persona, estado.guipractica, estado.guipractica.silabosemanal.silabo.materia), request, "rech")
            #                 return JsonResponse({"result": "ok", 'idestadogp':estado.estado, 'estadogp':estado.guipractica.nombre_estado_guiapractica()})
            #             else:
            #                 return JsonResponse({"result": "bad", "mensaje": "Es obligatorio el estado."})
            #         else:
            #             return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})
            #
            elif action == 'detallerevicion':
                try:
                    data['title'] = u'Detalle de revisión de guías de práctica'
                    practica = GPGuiaPracticaSemanal.objects.get(pk=request.POST['id'])
                    data['revisiones'] = practica.estadoguiapractica_set.filter(status=True).order_by('-fecha')
                    template = get_template("aprobar_silabo_decano/detallerevision.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            # elif action == 'aprobarguiapractica':
            #     try:
            #         if 'id' in request.POST:
            #             practicas = GPGuiaPracticaSemanal.objects.values_list('id').filter(silabosemanal__silabo__materia__profesormateria__profesor__coordinacion__carrera__in=persona.mis_carreras(), silabosemanal__silabo__materia__nivel__periodo__id=request.POST['id'], estadoguiapractica__estado=2).distinct().order_by('silabosemanal__silabo', 'silabosemanal')
            #             for p in practicas:
            #                 if not EstadoGuiaPractica.objects.values('id').filter(pk=p[0], estado=3).exists():
            #                     estado = EstadoGuiaPractica(guipractica_id=p[0], fecha=datetime.now().date(), persona=persona, estado=3)
            #                     estado.save(request)
            #                     log(u'Aprobó, %s la guía de práctica: %s de la materia %s' % (persona, estado.guipractica, estado.guipractica.silabosemanal.silabo.materia), request, "aprob")
            #             return JsonResponse({"result": "ok"})
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})
            #
            elif action == 'silaboposgradopdf':
                try:
                    silabo = Silabo.objects.get(pk=int(request.POST['ids']), status=True)
                    return conviert_html_to_pdf(
                        'aprobar_silabo/silabo_virtual_posgrado_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': silabo.silabo_virtual_posgrado_pdf(),
                        }
                    )
                except Exception as ex:
                    pass

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'aprobarsilabo':
                try:
                    data['title'] = u'Aprobar Silabo'
                    data['archivo'] = archivo = Archivo.objects.filter(pk=request.GET['id'])[0]
                    form = ArchivoForm(initial={'observacion': archivo.observacion,
                                                'aprobado': archivo.aprobado})
                    data['form'] = form
                    return render(request, "aprobar_silabo_decano/aprobarsilabo.html", data)
                except Exception as ex:
                    pass

            if action == 'versilabos':
                try:
                    data['title'] = u'Silabos Materia'
                    materia = Materia.objects.filter(pk=request.GET['id'])[0]
                    data['archivos'] = archivo = Archivo.objects.filter(materia=materia, archivo__contains='.doc').order_by('-id')
                    data['ultimo'] = Archivo.objects.filter(materia=materia, archivo__contains='.doc').order_by('-id')[0]
                    return render(request, "aprobar_silabo_decano/versilabos.html", data)
                except Exception as ex:
                    pass

            if action == 'listadosilabos':
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
                        'Content-Disposition'] = 'attachment; filename=silabo' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"MATERIA", 8000),
                        (u"PROFESOR", 10000),
                        (u"NIVEL CARRERA SESION", 8000),
                        (u"TIENE SILABO", 2000),
                        (u"TIENE PLAN ANALÍTICO", 2000),
                    ]
                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    # if miscarreras:
                    #     listaprofesores =  ProfesorMateria.objects.filter(materia__asignaturamalla__malla__carrera__in=miscarreras, materia__nivel__periodo=periodo, activo=True, principal=True).distinct().order_by('profesor')
                    # else:
                    listaprofesores = ProfesorMateria.objects.filter(materia__nivel__periodo=periodo, activo=True, principal=True).distinct().order_by('profesor')
                    # listaprofesores =  ProfesorMateria.objects.filter(materia__asignaturamalla__malla__carrera__in=miscoordinaciones).filter(materia__nivel__periodo=periodo, activo=True, principal=True).distinct().order_by('profesor')
                    row_num = 1
                    for profesores in listaprofesores:
                        tienearchivo = 'NO'
                        if Archivo.objects.values('id').filter(materia=profesores.materia, tipo_id=ARCHIVO_TIPO_SYLLABUS, archivo__contains='.doc').exists():
                            tienearchivo = 'SI'
                        tieneplan = 'NO'
                        if profesores.materia.asignaturamalla.programaanaliticoasignatura():
                            tieneplan = 'SI'
                        i = 0
                        campo1 = profesores.materia.asignatura.nombre
                        campo2 = profesores.profesor.persona.apellido1 + ' ' + profesores.profesor.persona.apellido2 + ' ' + profesores.profesor.persona.nombres
                        campo3 = profesores.materia.nivel.paralelo
                        if profesores.materia.nivel.carrera:
                            campo3 = campo3 + ' - ' + profesores.materia.nivel.carrera.alias
                        elif profesores.materia.asignaturamalla.malla.carrera:
                            campo3 = campo3 + ' - ' + profesores.materia.asignaturamalla.malla.carrera.alias
                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, tienearchivo, font_style2)
                        ws.write(row_num, 4, tieneplan, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'listadosilabosdigitales':
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
                        'Content-Disposition'] = 'attachment; filename=silabo' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"FACULTAD", 10000),
                        (u"CARRERA", 10000),
                        (u"ASIGNATURA", 10000),
                        (u"NIVEL", 6000),
                        (u"PARALELO", 8000),
                        (u"PROFESOR", 10000),
                        (u"TIENE SILABO", 5000),
                        (u"FECHA DE CREACIÓN DEL SÍLABO", 7000),
                        (u"POCENTAJE PLANIFICADO", 7000),
                        (u"ESTADO APROBACION DEL SÍLABO", 10000),
                        (u"USUARIO QUIEN APROBÓ EL SÍLABO", 10000),
                        (u"OBSERVACIÓN DE APROBACION", 10000),
                        (u"FECHA DE APROBACION", 10000),
                        (u"TIENE PROGRAMA ANALITICO", 15000),
                        (u"FECHA DE CREACIÓN DE PROGRAMA ANALITICO", 15000),
                        (u"SÍLABO (FIRMADO Y ESCANEADO)", 15000),
                        (u"TIENE GUÍA DE PRÁCTICA", 8000),
                        (u"CANTIDAD G.P", 8000),
                    ]
                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    # if miscarreras:
                    #     listaprofesores =  ProfesorMateria.objects.filter(materia__asignaturamalla__malla__carrera__in=miscarreras, materia__nivel__periodo=periodo, activo=True, principal=True).distinct().order_by('profesor')
                    # else:
                    listamaterias = ProfesorMateria.objects.filter(materia__nivel__periodo=periodo, activo=True, principal=True).distinct().order_by('materia__asignaturamalla__malla__carrera')
                    # listaprofesores =  ProfesorMateria.objects.filter(materia__asignaturamalla__malla__carrera__in=miscoordinaciones).filter(materia__nivel__periodo=periodo, activo=True, principal=True).distinct().order_by('profesor')
                    row_num = 1
                    for materia in listamaterias:
                        facultad = '%s' % materia.materia.asignaturamalla.malla.carrera.coordinaciones()[0].nombre if materia.materia.asignaturamalla.malla.carrera.coordinaciones() else ""
                        campo1 = '%s' % materia.materia.asignaturamalla.malla.carrera.nombre_completo()
                        campo2 = '%s' % materia.materia.asignaturamalla.asignatura.nombre
                        campo3 = '%s' % materia.materia.asignaturamalla.nivelmalla
                        campo4 = '%s' % materia.materia.paralelo if materia.materia.paralelo else ''
                        campo5 = '%s' % materia.profesor.persona.nombre_completo_inverso()
                        campo6 = 'SI' if materia.materia.tiene_silabo() else 'NO'
                        campo7 = materia.materia.silabo_actual().fecha_creacion.strftime("%d-%m-%Y") if materia.materia.tiene_silabo() else ''
                        campo8 = str(materia.materia.silabo_actual().estado_planificacion_clases())+' %' if materia.materia.tiene_silabo() and materia.materia.tiene_silabo_semanal() else ''#porcentaje
                        estado = None
                        if materia.materia.silabo_actual():
                            if materia.materia.silabo_actual().estado_aprobacion():
                                estado = materia.materia.silabo_actual().estado_aprobacion()
                        campo9 = ''
                        if materia.materia.tiene_silabo():
                            campo9 = 'PENDIENTE'
                        campo10 = ''
                        campo11 = ''
                        campo12 = ''
                        if estado:
                            campo9 = '%s' % estado.get_estadoaprobacion_display()
                            campo10 = '%s' % estado.persona.nombre_completo_inverso()
                            campo11 = '%s' % estado.observacion
                            campo12 = '%s' % estado.fecha.strftime("%d-%m-%Y")
                        campo13 = ''
                        campo14 = ''
                        campo15 = 'NO'
                        campo16 = ''
                        campo17 = ''
                        if materia.materia.silabo_actual():
                            campo13 = 'DESACTIVADO'
                            if materia.materia.silabo_actual().programaanaliticoasignatura.activo:
                                campo13 = 'ACTIVO'
                            campo14 = '%s' % materia.materia.silabo_actual().programaanaliticoasignatura.fecha_creacion.strftime("%d-%m-%Y")
                            if materia.materia.silabo_actual().numero_guia_practicas():
                                campo15 = 'SI'
                                campo16 = str(materia.materia.silabo_actual().numero_guia_practicas())
                            campo17 = 'NO'
                            if materia.materia.silabo_actual().silabofirmado:
                                campo17 = 'SI'
                        ws.write(row_num, 0, facultad, font_style2)
                        ws.write(row_num, 1, campo1, font_style2)
                        ws.write(row_num, 2, campo2, font_style2)
                        ws.write(row_num, 3, campo3, font_style2)
                        ws.write(row_num, 4, campo4, font_style2)
                        ws.write(row_num, 5, campo5, font_style2)
                        ws.write(row_num, 6, campo6, font_style2)
                        ws.write(row_num, 7, campo7, font_style2)
                        ws.write(row_num, 8, campo8, font_style2)
                        ws.write(row_num, 9, campo9, font_style2)
                        ws.write(row_num, 10, campo10, font_style2)
                        ws.write(row_num, 11, campo11, font_style2)
                        ws.write(row_num, 12, campo12, font_style2)
                        ws.write(row_num, 13, campo13, font_style2)
                        ws.write(row_num, 14, campo14, font_style2)
                        ws.write(row_num, 15, campo17, font_style2)
                        ws.write(row_num, 16, campo15, font_style2)
                        ws.write(row_num, 17, campo16, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'listar_silabos':
                try:
                    # data['materia'] = materia = Materia.objects.get(pk=pm.materia.id)
                    data['materia'] = materia = Materia.objects.get(pk=int(request.GET['id']))
                    data['profesor'] = materia.profesor_principal()
                    # data['profesor'] = pm.profesor
                    data['silabos'] = materia.silabo_set.all().order_by('fecha_creacion')
                    # data['silabos'] = materia.silabo_set.filter(profesor=pm.profesor).order_by('fecha_creacion')
                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    template = get_template("aprobar_silabo_decano/listasilabos.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            # elif action == 'detalle_temasxplanificar':
            #     try:
            #         silabo = Silabo.objects.get(pk=int(request.GET['ids']))
            #         stemas = DetalleSilaboSemanalTema.objects.values("temaunidadresultadoprogramaanalitico_id").filter(silabosemanal__silabo=silabo, status=True)
            #         ssubtemas = DetalleSilaboSemanalSubtema.objects.values("subtemaunidadresultadoprogramaanalitico_id").filter(silabosemanal__silabo=silabo, status=True)
            #         tem = TemaUnidadResultadoProgramaAnalitico.objects.values_list("id", flat=True).filter(status=True, unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura_id=silabo.programaanaliticoasignatura.id).exclude(pk__in=stemas)
            #         data['subtemas'] = subtemas = SubtemaUnidadResultadoProgramaAnalitico.objects.filter(status=True, temaunidadresultadoprogramaanalitico__unidadresultadoprogramaanalitico__contenidoresultadoprogramaanalitico__programaanaliticoasignatura_id=silabo.programaanaliticoasignatura.id).exclude(pk__in=ssubtemas)
            #         st = subtemas.values_list("temaunidadresultadoprogramaanalitico_id", flat=True).all().distinct('temaunidadresultadoprogramaanalitico_id')
            #         data['temas'] = TemaUnidadResultadoProgramaAnalitico.objects.filter(Q(pk__in=st) | Q(pk__in=tem)).order_by("unidadresultadoprogramaanalitico__orden")
            #         template = get_template("pro_planificacion/detalle_temasxplanificar.html")
            #         json_content = template.render(data)
            #         return JsonResponse({"result": "ok", 'data': json_content})
            #     except Exception as ex:
            #         return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
            #         pass
            #
            elif action == 'seguimientosilabo':
                try:
                    data['title'] = u'Seguimiento de Sílabo'
                    materia = Materia.objects.get(pk=request.GET['id'])
                    data['silabo'] = materia.silabo_actual()
                    data['profesormateria'] = ProfesorMateria.objects.filter(materia=materia, status=True)[0]
                    silabo = materia.silabo_actual()
                    data['semanas'] = silabo.silabosemanal_set.filter(status=True).order_by('numsemana')
                    return render(request, "aprobar_silabo_decano/seguimientosilabo.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            # elif action == 'confirmarreactivo':
            #     try:
            #         data['title'] = u'Confirmar Reactivo'
            #         data['materia'] = Materia.objects.get(pk=request.GET['idmate'])
            #         data['iddetalle'] = request.GET['iddetalle']
            #         if 's' in request.GET:
            #             data['search'] = request.GET['s']
            #         if 'nid' in request.GET:
            #             data['nid'] = request.GET['nid']
            #         if 'mid' in request.GET:
            #             data['mid'] = request.GET['mid']
            #         return render(request, 'aprobar_silabo/confirmarreactivo.html', data)
            #     except Exception as ex:
            #         pass
            #
            # elif action == 'eliminarconfirmacion':
            #     try:
            #         data['title'] = u'Eliminar Confirmación'
            #         data['materia'] = Materia.objects.get(pk=request.GET['idmate'])
            #         data['iddetalle'] = request.GET['iddetalle']
            #         if 's' in request.GET:
            #             data['search'] = request.GET['s']
            #         if 'nid' in request.GET:
            #             data['nid'] = request.GET['nid']
            #         if 'mid' in request.GET:
            #             data['mid'] = request.GET['mid']
            #         return render(request, 'aprobar_silabo/eliminarconfirmacion.html', data)
            #     except Exception as ex:
            #         pass
            #
            elif action == 'reportereactivo':
                try:
                    periodo = request.GET['periodo']

                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=reactivo.xls'
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
                    ws.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)

                    ws.col(0).width = 6000
                    ws.col(1).width = 6000
                    ws.col(2).width = 6000
                    ws.col(3).width = 6000
                    ws.col(4).width = 6000
                    ws.col(5).width = 6000
                    ws.col(6).width = 6000

                    ws.write(4, 0, 'FACULTAD')
                    ws.write(4, 1, 'CARRERA')
                    ws.write(4, 2, 'NIVEL')
                    ws.write(4, 3, 'PARALELO')
                    ws.write(4, 4, 'ASIGNATURA')
                    ws.write(4, 5, 'DOCENTE')
                    ws.write(4, 6, 'CONFIRMADO REACTIVO 1')
                    ws.write(4, 7, 'FECHA CONFIRMACION')
                    ws.write(4, 8, 'CONFIRMADO REACTIVO 2')
                    ws.write(4, 9, 'FECHA CONFIRMACION')
                    miscarreras = Carrera.objects.filter(coordinadorcarrera__in=persona.gruposcarrera(periodo)).distinct()
                    a = 4
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    materias = Materia.objects.filter(nivel__periodo=periodo, status=True, profesormateria__isnull=False, asignaturamalla__malla__carrera__in=miscarreras).distinct().order_by('asignaturamalla__malla__carrera__coordinacion','asignaturamalla__nivelmalla','asignaturamalla__malla__carrera','paralelo').exclude(asignaturamalla__malla__carrera__coordinacion__id__in=[9])
                    for materia in materias:
                        a += 1
                        ws.write(a, 0, u'%s'%materia.asignaturamalla.malla.carrera.coordinacion_set.all()[0].nombre)
                        ws.write(a, 1, u'%s'%materia.asignaturamalla.malla.carrera.nombre)
                        ws.write(a, 2, u'%s'%materia.asignaturamalla.nivelmalla.nombre)
                        ws.write(a, 3, u'%s'%materia.paralelo)
                        ws.write(a, 4, u'%s'%materia.asignatura.nombre)
                        ws.write(a, 5, u'%s'%materia.profesor_materia_principal().profesor.persona.nombre_completo_inverso())
                        reactivo1 = materia.reactivomateria_set.filter(status=True).exclude(detallemodelo__nombre__icontains='EX2')
                        reactivo_1 = 'NO'
                        fecha1 = ''
                        if reactivo1.values('id').exists():
                            reactivo_1 = 'SI'
                            fecha1 = reactivo1[0].fecha
                        reactivo2 = materia.reactivomateria_set.filter(status=True,detallemodelo__nombre__icontains='EX2')
                        reactivo_2 = 'NO'
                        fecha2 = ''
                        if reactivo2.values('id').exists():
                            reactivo_2 = 'SI'
                            fecha2 = reactivo2[0].fecha
                        ws.write(a, 6, u'%s'%reactivo_1)
                        ws.write(a, 7, u'%s' %fecha1)
                        ws.write(a, 8, u'%s'%reactivo_2)
                        ws.write(a, 9, u'%s' %fecha2)

                    a += 1
                    # ws.write_merge(a + 2, a + 2, 0, 1, datetime.today(), date_format)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            # elif action == 'guiapracticas':
            #     try:
            #         data['silabo'] = silabo = Silabo.objects.get(pk=int(request.GET['id']))
            #         data['materia'] = '%s - %s - %s %s' %(silabo.materia.asignaturamalla.asignatura, silabo.materia.asignaturamalla.nivelmalla, silabo.materia.paralelo, silabo.materia.nivel.paralelo)
            #         data['practicas'] = GPGuiaPracticaSemanal.objects.filter(status=True, silabosemanal__silabo=silabo).order_by('silabosemanal')
            #         template = get_template("aprobar_silabo/guiapracticas.html")
            #         json_content = template.render(data)
            #         return JsonResponse({"result": "ok", 'html': json_content})
            #     except Exception as ex:
            #         return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
            #         pass
            #
            # elif action == 'revisarpractica':
            #     try:
            #         data['title'] = u'Rechazar Guía de práctica'
            #         data['estados'] = ([2,'REVISADO'],[4,'RECHAZADO'])
            #         data['practica'] = GPGuiaPracticaSemanal.objects.get(pk=request.GET['id'])
            #         template = get_template("aprobar_silabo/revisionguiapractica.html")
            #         json_content = template.render(data)
            #         return JsonResponse({"result": "ok", 'data': json_content})
            #     except Exception as ex:
            #         pass
            #
            # elif action == 'aprobacionguiaspracticas':
            #     try:
            #         data['title'] = u'Confirmar aprobación de guiás de prácticas'
            #         data['carreras'] = persona.mis_carreras().values_list('nombre')
            #         data['period'] = periodo
            #         return render(request, 'aprobar_silabo/aprobarguiapractica.html', data)
            #     except Exception as ex:
            #         pass
            #
            # elif action == 'listaguiapractica':
            #     try:
            #         data['title'] = u'Listado de guías de prácticas'
            #         search = None
            #         practicas = GPGuiaPracticaSemanal.objects.filter(silabosemanal__silabo__materia__profesormateria__profesor__coordinacion__carrera__in=persona.mis_carreras(), silabosemanal__silabo__materia__nivel__periodo=periodo).distinct().order_by('silabosemanal__silabo', 'silabosemanal')
            #         if 's' in request.GET:
            #             search = request.GET['s']
            #             s = search.split(" ")
            #             if len(s) == 2:
            #                 practicas = practicas.filter((Q(silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre__icontains=s[0])& Q(silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre__icontains=s[1]))| (Q(silabosemanal__silabo__materia__profesormateria__profesor__persona__nombres__icontains=s[0])& Q(silabosemanal__silabo__materia__profesormateria__profesor__persona__nombres__icontains=s[1]))| (Q(silabosemanal__silabo__materia__profesormateria__profesor__persona__apellido1__icontains=s[0])& Q(silabosemanal__silabo__materia__profesormateria__profesor__persona__apellido2__icontains=s[1])))
            #             else:
            #                 practicas = practicas.filter(Q(silabosemanal__silabo__materia__asignaturamalla__asignatura__nombre__icontains=search)| Q(silabosemanal__silabo__materia__profesormateria__profesor__persona__nombres__icontains=search)| Q(silabosemanal__silabo__materia__profesormateria__profesor__persona__apellido1__icontains=search))
            #         paging = MiPaginador(practicas, 20)
            #         p = 1
            #         try:
            #             paginasesion = 1
            #             if 'paginador' in request.session:
            #                 paginasesion = int(request.session['paginador'])
            #             if 'page' in request.GET:
            #                 p = int(request.GET['page'])
            #             else:
            #                 p = paginasesion
            #             try:
            #                 page = paging.page(p)
            #             except:
            #                 p = 1
            #             page = paging.page(p)
            #         except:
            #             page = paging.page(p)
            #         request.session['paginador'] = p
            #         data['paging'] = paging
            #         data['page'] = page
            #         data['rangospaging'] = paging.rangos_paginado(p)
            #         data['practicas'] = page.object_list
            #         data['search'] = search if search else ""
            #         return render(request, 'aprobar_silabo/listaguiaspracticas.html', data)
            #     except Exception as ex:
            #         pass
            #
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Aprobar sílabo Autoridad'
                if not request.session['periodo'].visible:
                    return HttpResponseRedirect("/?info=Periodo Inactivo.")
                data['mallas'] = malla = Malla.objects.filter(carrera__in=persona.mis_carreras()).distinct()
                data['nivelmalla'] = NivelMalla.objects.filter(status=True)
                search = None
                mallaid = None
                nivelmallaid = None
                ids = None
                profesormaterias = ProfesorMateria.objects.filter(activo=True, status=True, materia__nivel__periodo__visible=True, materia__nivel__periodo=periodo, materia__silabo__aprobarsilabo__estadoaprobacion=2).distinct('materia').order_by('materia')
                if miscoordinaciones:
                    # profesormaterias = profesormaterias.filter(materia__asignaturamalla__malla__carrera__in=miscarreras)
                    profesormaterias = profesormaterias.filter(activo=True, status=True, materia__asignaturamalla__malla__carrera__coordinacion__in=miscoordinaciones)
                # else:
                #     profesormaterias = profesormaterias.filter(activo=True, status=True, materia__asignaturamalla__malla__carrera__in=persona.mis_carreras())
                if 'nid' in request.GET:
                    if int(request.GET['nid']) > 0:
                        nivelmallaid = NivelMalla.objects.get(pk=int(request.GET['nid']))
                        profesormaterias = profesormaterias.filter(activo=True, status=True, materia__asignaturamalla__nivelmalla__id=nivelmallaid.id)
                    else:
                        nivelmallaid = int(request.GET['nid'])
                if 'mid' in request.GET:
                    if int(request.GET['mid']) > 0:
                        mallaid = Malla.objects.get(pk=int(request.GET['mid']))
                        profesormaterias = profesormaterias.filter(activo=True, status=True, materia__asignaturamalla__malla__carrera__coordinacion__in=miscoordinaciones)
                    else:
                        mallaid = int(request.GET['mid'])
                if 'id' in request.GET:
                    ids = int(request.GET['id'])
                    profesormaterias = profesormaterias.filter(activo=True, status=True, materia__id=int(request.GET['id']))

                if 's' in request.GET:
                    search = request.GET['s']
                    s = search.split(" ")
                    if len(s) == 2:
                        profesormaterias = profesormaterias.filter(activo=True, status=True).filter((Q(profesor__persona__nombres__icontains=s[0]) & Q(profesor__persona__apellido1__icontains=s[1])) | (Q(profesor__persona__apellido1__icontains=s[0]) & Q(profesor__persona__apellido2__icontains=s[1])) | (Q(materia__asignatura__nombre__icontains=s[0]) & Q(materia__asignatura__nombre__icontains=s[1])))
                    else:
                        profesormaterias = profesormaterias.filter(activo=True, status=True).filter(Q(profesor__persona__apellido1__icontains=search) | Q(profesor__persona__apellido2__icontains=search) | Q(materia__asignatura__nombre__icontains=search))

                paging = MiPaginador(profesormaterias, 25)
                p = 1
                try:
                    paginasesion = 1
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
                data['profesormaterias'] = page.object_list
                data['search'] = search if search else ""
                data['mid'] = mallaid.id if mallaid else 0
                data['nid'] = nivelmallaid.id if nivelmallaid else 0
                data['ids'] = ids
                data['aprobar'] = variable_valor('APROBAR_SILABO')
                data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                data['periodo'] = periodo
                return render(request, "aprobar_silabo_decano/view.html", data)
            except Exception as ex:
                pass
