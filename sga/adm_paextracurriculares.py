# -*- coding: UTF-8 -*-
import random
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
import xlwt
from xlwt import *

from sga.funciones import log, MiPaginador
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import PaeAreaPeriodoForm, PaeActividadesPeriodoAreasForm, PaeFechaActividadesForm, \
    PaeInscripcionActividadesFrom, PaeInscripcionActividadesArchivoForm
from sga.models import PaePeriodoAreas, PaeActividadesPeriodoAreas, PaeInscripcionActividades, \
    PaeFechaActividad, InscripcionActividadesSolicitud, Coordinacion, Persona, Inscripcion, PerfilAccesoUsuario
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    coordinacion = []
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    if persona.es_profesor():
        coordinacion = persona.profesor().coordinacion
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addareaperiodo':
            try:
                f = PaeAreaPeriodoForm(request.POST)
                if f.is_valid():
                    if not PaePeriodoAreas.objects.filter(periodo=periodo, areas=f.cleaned_data['area'] ,status=True).exists():
                        programas = PaePeriodoAreas(periodo=periodo,
                                                    areas=f.cleaned_data['area'],
                                                    nombre=f.cleaned_data['nombre']
                                                    )
                        programas.save(request)
                        log(u'añade area a periodo: %s' % programas, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"El area ya se encuentra registrada."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addactividad':
            try:
                f = PaeActividadesPeriodoAreasForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['nivelminimo'] or f.cleaned_data['nivelmaximo']:
                        if not f.cleaned_data['nivelminimo']:
                            return JsonResponse({"result": "bad","mensaje": u"Debe ingresar un nivel minimo."})
                        if not f.cleaned_data['nivelmaximo']:
                            return JsonResponse({"result": "bad","mensaje": u"Debe ingresar un nivel maximo."})
                    peridoactividades = PaeActividadesPeriodoAreas(periodoarea_id=request.POST['id'],
                                                                   coordinacion=f.cleaned_data['coordinacion'],
                                                                   carrera=f.cleaned_data['carrera'],
                                                                   nombre=f.cleaned_data['nombre'],
                                                                   descripcion=f.cleaned_data['descripcion'],
                                                                   fechainicio=f.cleaned_data['fechainicio'],
                                                                   fechafin=f.cleaned_data['fechafin'],
                                                                   general=f.cleaned_data['general'],
                                                                   calificar=f.cleaned_data['calificar'],
                                                                   notaaprobacion=f.cleaned_data['notaaprobacion'],
                                                                   maximacalificacion=f.cleaned_data['maximacalificacion'],
                                                                   minimaasistencia=f.cleaned_data['minimaasistencia'],
                                                                   cupo=f.cleaned_data['cupo'],
                                                                   nivelminimo=f.cleaned_data['nivelminimo'],
                                                                   nivelmaximo=f.cleaned_data['nivelmaximo'],
                                                                   nivel=f.cleaned_data['nivel'],
                                                                   tutorprincipal=f.cleaned_data['tutorprincipal'],
                                                                   link=f.cleaned_data['link'],
                                                                   grupo=f.cleaned_data['grupo']
                                                                   )
                    peridoactividades.save(request)
                    log(u'Adiciono actividad complementaria: %s %s %s' % (peridoactividades.id, peridoactividades, peridoactividades.cupo), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addfechaactividad':
            try:
                f = PaeFechaActividadesForm(request.POST)
                if f.is_valid():
                    if PaeFechaActividad.objects.filter(actividad_id=request.POST['id'],fecha=f.cleaned_data['fecha'],status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"No puede ingresar la misma fecha en la actividad."})
                    fechaactividad = PaeFechaActividad(actividad_id=request.POST['id'],
                                                       tutor_id=f.cleaned_data['profesor'],
                                                       lugar=f.cleaned_data['lugar'],
                                                       observacion=f.cleaned_data['observacion'],
                                                       fecha=f.cleaned_data['fecha'])
                    fechaactividad.save(request)
                    log(u'añade fecha a la actividad: %s' % fechaactividad, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editareaperiodo':
            try:
                f = PaeAreaPeriodoForm(request.POST)
                periodoarea = PaePeriodoAreas.objects.get(pk=request.POST['id'])
                if f.is_valid():
                    periodoarea.nombre = f.cleaned_data['nombre']
                    periodoarea.areas = f.cleaned_data['area']
                    periodoarea.save(request)
                    log(u'edita area a periodo: %s' % periodoarea, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editfechaactividad':
            try:
                f = PaeFechaActividadesForm(request.POST)
                fechaactividad = PaeFechaActividad.objects.get(pk=request.POST['id'])
                if f.is_valid():
                    fechaactividad.tutor_id = f.cleaned_data['profesor']
                    fechaactividad.lugar = f.cleaned_data['lugar']
                    fechaactividad.observacion = f.cleaned_data['observacion']
                    fechaactividad.fecha = f.cleaned_data['fecha']
                    fechaactividad.save(request)
                    log(u'edita fecha de actividad: %s' % fechaactividad, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'pdflistaactividades':
            try:
                data = {}
                data['fechaactual'] = datetime.now()
                if persona.es_profesor():
                    # data['actividades'] = PaeActividadesPeriodoAreas.objects.filter(periodoarea__periodo=periodo, coordinacion=coordinacion, status=True).order_by('coordinacion__nombre','nombre','periodoarea__nombre','periodoarea__areas__nombre')
                    data['actividades'] = PaeInscripcionActividades.objects.values_list('matricula__inscripcion__coordinacion__nombre', 'matricula__inscripcion__carrera__nombre', 'actividades__periodoarea__areas__nombre', 'actividades__nombre').filter(actividades__periodoarea__periodo=periodo,actividades__coordinacion=coordinacion,matricula__inscripcion__coordinacion=coordinacion, status=True, actividades__periodoarea__status=True,actividades__status=True).order_by('matricula__inscripcion__coordinacion__nombre', 'matricula__inscripcion__carrera__nombre', 'actividades__periodoarea__areas__nombre','actividades__nombre', 'actividades__periodoarea__nombre').annotate(count=Count('matricula_id'))
                else:
                    # data['actividades'] = PaeActividadesPeriodoAreas.objects.filter(periodoarea__periodo=periodo,status=True).order_by('coordinacion__nombre','nombre','periodoarea__nombre','periodoarea__areas__nombre')
                    data['actividades'] = PaeInscripcionActividades.objects.values_list('matricula__inscripcion__coordinacion__nombre', 'matricula__inscripcion__carrera__nombre', 'actividades__periodoarea__areas__nombre', 'actividades__nombre').filter(actividades__periodoarea__periodo=periodo,status=True,actividades__periodoarea__status=True,actividades__status=True).order_by('matricula__inscripcion__coordinacion__nombre', 'matricula__inscripcion__carrera__nombre', 'actividades__periodoarea__areas__nombre','actividades__nombre', 'actividades__periodoarea__nombre').annotate(count=Count('matricula_id'))
                return conviert_html_to_pdf(
                    'adm_paextracurricular/listaactividades_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        elif action == 'pdflistainscritos':
            try:
                actividad = PaeActividadesPeriodoAreas.objects.get(pk=request.POST['idactividad'])
                return conviert_html_to_pdf(
                    'adm_paextracurricular/inscritosactividades_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': actividad.listado_inscritos_reporte(),
                    }
                )
            except Exception as ex:
                return JsonResponse(  {"result": "bad", "mensaje": u"Problemas al ejecutar el reporte. %s" % ex})

        elif action == 'pdflistainscritosfecha':
            try:
                data = {}
                data['fechaactual'] = datetime.now()
                data['fechaactividad'] = PaeFechaActividad.objects.get(pk=request.POST['idfechacronograma'])
                data['actividad'] = actividad = PaeActividadesPeriodoAreas.objects.get(pk=request.POST['idactividad'])
                data['inscritos'] = PaeInscripcionActividades.objects.filter(actividades=actividad, status=True).order_by('matricula__inscripcion__sesion__nombre','matricula__inscripcion__persona__apellido1')
                return conviert_html_to_pdf(
                    'adm_paextracurricular/inscritosactividadesfechas_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        elif action == 'editactividad':
            try:
                f = PaeActividadesPeriodoAreasForm(request.POST)
                actividad = PaeActividadesPeriodoAreas.objects.get(pk=request.POST['id'])
                totalinscritos = PaeInscripcionActividades.objects.filter(actividades=actividad, status=True).count()
                if f.is_valid():
                    if f.cleaned_data['cupo'] < totalinscritos:
                        return JsonResponse({"result": "bad","mensaje": u"Lo sentimos, ya existe un número mayor de estudiantes inscritos en la actividad."})
                    if f.cleaned_data['nivelminimo'] or f.cleaned_data['nivelmaximo']:
                        if not f.cleaned_data['nivelminimo']:
                            return JsonResponse({"result": "bad","mensaje": u"Debe ingresar un nivel minimo."})
                        if not f.cleaned_data['nivelmaximo']:
                            return JsonResponse({"result": "bad","mensaje": u"Debe ingresar un nivel maximo."})
                    actividad.nombre = f.cleaned_data['nombre']
                    actividad.coordinacion = f.cleaned_data['coordinacion']
                    actividad.descripcion = f.cleaned_data['descripcion']
                    actividad.fechainicio = f.cleaned_data['fechainicio']
                    actividad.fechafin = f.cleaned_data['fechafin']
                    actividad.cupo = f.cleaned_data['cupo']
                    actividad.calificar = f.cleaned_data['calificar']
                    actividad.minimaasistencia = f.cleaned_data['minimaasistencia']
                    actividad.maximacalificacion = f.cleaned_data['maximacalificacion']
                    actividad.notaaprobacion = f.cleaned_data['notaaprobacion']
                    actividad.general = f.cleaned_data['general']
                    actividad.tutorprincipal = f.cleaned_data['tutorprincipal']
                    actividad.carrera = f.cleaned_data['carrera']
                    actividad.nivelminimo = f.cleaned_data['nivelminimo']
                    actividad.nivelmaximo = f.cleaned_data['nivelmaximo']
                    actividad.nivel = f.cleaned_data['nivel']
                    actividad.link =f.cleaned_data['link']
                    actividad.grupo =f.cleaned_data['grupo']
                    actividad.save(request)
                    log(u'Edito actividad complementaria: %s %s %s %s General: %s Fecha ini: %s Fecha fin: %s' % (actividad.id, actividad, actividad.cupo, actividad.coordinacion, actividad.general, actividad.fechainicio, actividad.fechafin), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteactividad':
            try:
                actividad = PaeActividadesPeriodoAreas.objects.get(pk=request.POST['id'])
                actividad.status = False
                actividad.save(request)
                log(u'elimino actividad: %s' % actividad, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletecronograma':
            try:
                cronograma = PaeFechaActividad.objects.get(pk=request.POST['id'])
                cronograma.status = False
                cronograma.save(request)
                log(u'elimino cronograma: %s' % cronograma, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteparticipante':
            try:
                inscrito = PaeInscripcionActividades.objects.get(pk=request.POST['id'])
                log(u'Eliminó participante actividad complementaria: %s' % inscrito, request, "del")
                inscrito.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteareaperiodo':
            try:
                areaperiodo = PaePeriodoAreas.objects.get(pk=request.POST['id'])
                areaperiodo.status = False
                areaperiodo.save(request)
                log(u'elimino area de periodo: %s' % areaperiodo, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'enviareliminacion':
            try:
                if InscripcionActividadesSolicitud.objects.get(status=True,pk=request.POST['id']):
                    inscripcion=InscripcionActividadesSolicitud.objects.get(status=True,pk=request.POST['id'])
                    inscripcion.estado=int(request.POST['estado'])
                    inscripcion.save(request)
                    log(u'Cambio %s estado de solicitud elimimacion actividades complementarias: %s' % ( persona,inscripcion), request, "edit")
                    if int(request.POST['estado']) == 2:
                        inscrito = PaeInscripcionActividades.objects.filter(matricula=inscripcion.matricula, actividades=inscripcion.actividades)[0]
                        if inscrito.puedeeliminarinscripciondirector():
                            log(u'Eliminó %s a participante %s  actividad complementaria: ' % (persona, inscrito), request, "del")
                            inscrito.delete()
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Ya no puede eliminar inscrito"})
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Ya envió solicitud."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addinscripcion':
            try:
                f = PaeInscripcionActividadesFrom(request.POST)
                if f.is_valid():
                    # persona = Persona.objects.get(id=f.cleaned_data['persona'])
                    # matricula = persona.inscripcion_set.filter(status=True)[0].matricula_periodo(periodo)
                    matricula = Inscripcion.objects.get(id=f.cleaned_data['inscripcion']).matricula_periodo(periodo)
                    if not matricula:
                        return JsonResponse({"result": "bad", "mensaje": u"Lo sentimos, no esta matriculado."})
                    actividad = PaeActividadesPeriodoAreas.objects.get(pk=request.POST['id'],status=True)
                    if not actividad.paeinscripcionactividades_set.values("id").filter(matricula=matricula, status=True).exists():
                        totalinscritos = actividad.paeinscripcionactividades_set.values("id").filter(status=True).count()
                        if totalinscritos >= actividad.cupo:
                            return JsonResponse({"result": "bad", "mensaje": u"Lo sentimos, no hay cupo disponible."})
                        inscripcionactividad = PaeInscripcionActividades(matricula=matricula, actividades=actividad)
                        inscripcionactividad.save(request)
                        log(u'Adiciono actividad complementaria: %s' % inscripcionactividad, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Lo sentimos, ya esta inscrito en esta actividad."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'reporteactividades':
            try:
                data['periodoarea'] = periodoarea = PaePeriodoAreas.objects.get(pk=int(request.POST['idpa']))
                data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=int(encrypt(request.POST['idc'])))
                data['actividades'] = PaeActividadesPeriodoAreas.objects.filter(periodoarea=periodoarea, coordinacion=coordinacion, status=True).order_by('coordinacion', 'nombre')
                return conviert_html_to_pdf('adm_paextracurricular/reporte_actividades_complementaria.html', {'pagesize': 'A4', 'datos': data})
            except Exception as ex:
                return HttpResponseRedirect("/adm_paextracurricular?info=%s" % 'Error al generar informe de de activiades complementarias.')

        elif action == 'reporte_actividades_facultad':
            try:
                data['periodoarea'] = periodoarea = PaePeriodoAreas.objects.get(pk=int(request.POST['idpa']))
                data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=int(request.POST['idf']))
                lista_actividades = PaeActividadesPeriodoAreas.objects.values_list('id', flat=False).filter(periodoarea=periodoarea, coordinacion=coordinacion, status=True).order_by('coordinacion', 'nombre')
                data['inscritos'] = inscritos = PaeInscripcionActividades.objects.filter(status=True, actividades__id__in=lista_actividades).order_by('matricula__inscripcion__persona__apellido1','matricula__inscripcion__persona__apellido2')
                if int(request.POST['tipo']) == 1:#Pdf
                    return conviert_html_to_pdf('adm_paextracurricular/reporte_actividades_facultad.html', {'pagesize': 'A4 landscape', 'data': data})
                elif int(request.POST['tipo']) == 2:#Excel
                    __author__ = 'Unemi'
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Registro-actividades-'+ random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"CÉDULA", 6000),
                        (u"APELLIDO Y NOMBRES", 12000),
                        (u"NIVEL", 6000),
                        (u"CARRERA", 15000),
                        (u"FECHA ACTIVIDAD", 6000),
                        (u"SECCION/JORNADA", 6000),
                        (u"ACTIVIDAD COMPLEMENTARIA QUE REALIZÓ", 16000),
                        (u"PORCENTAJE DE ASISTENCIA", 6000),
                        (u"CALIFICACIÓN", 6000),
                    ]
                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num += 1
                    for i in inscritos:
                        ws.write(row_num, 0, i.matricula.inscripcion.persona.cedula if i.matricula.inscripcion.persona.cedula else i.matricula.inscripcion.persona.pasaporte, font_style2)
                        ws.write(row_num, 1, i.matricula.inscripcion.persona.nombre_completo_inverso(), font_style2)
                        ws.write(row_num, 2, i.matricula.inscripcion.mi_nivel().nivel.nombre if i.matricula.inscripcion.mi_nivel() else '', font_style2)
                        ws.write(row_num, 3, '%s' %i.matricula.inscripcion.carrera if i.matricula.inscripcion.carrera else '', font_style2)
                        ws.write(row_num, 4, i.actividades.fechainicio.strftime("%d/%m/%Y")+' - '+ i.actividades.fechafin.strftime("%d/%m/%Y") if i.actividades.fechainicio and i.actividades.fechafin else '', font_style2)
                        ws.write(row_num, 5, i.matricula.nivel.sesion.nombre if i.matricula.nivel.sesion else '', font_style2)
                        ws.write(row_num, 6, '%s' %i.actividades if i.actividades else '', font_style2)
                        ws.write(row_num, 7, '%s' %i.registra_asistencia_actividad() if i.registra_asistencia_actividad() else '', font_style2)
                        ws.write(row_num, 8, '%s' %i.nota if i.nota else '', font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
            except Exception as ex:
                return HttpResponseRedirect("/adm_paextracurricular?info=%s" % 'Error al generar informe de de activiades complementarias.')

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addareaperiodo':
                try:
                    data['title'] = u'Adicionar Área'
                    form = PaeAreaPeriodoForm()
                    data['form'] = form
                    return render(request, "adm_paextracurricular/addareaperiodo.html", data)
                except Exception as ex:
                    pass

            elif action == 'addactividad':
                try:
                    data['title'] = u'Adicionar Actividad'
                    data['periodoareas'] = PaePeriodoAreas.objects.get(pk=request.GET['idperiodoarea'])
                    form = PaeActividadesPeriodoAreasForm()
                    form.cargarnivel(periodo)
                    data['form'] = form
                    return render(request, "adm_paextracurricular/addactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'addfechaactividad':
                try:
                    data['title'] = u'Adicionar Fecha'
                    data['fechaactividad'] = PaeActividadesPeriodoAreas.objects.get(pk=request.GET['idactividad'])
                    form = PaeFechaActividadesForm()
                    data['form'] = form
                    return render(request, "adm_paextracurricular/addfechaactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'excelactividades':
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
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=LISTADO_ACTIVIDADES_COMPLEMENTARIAS' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"FACULTAD", 10000),
                        (u"CARRERA", 10000),
                        (u"AREA", 6000),
                        (u"ARTICULO", 10000),
                        (u"TOTAL PARTICIPANTES", 2000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    data = {}
                    data['fechaactual'] = datetime.now()
                    if persona.es_profesor():
                        actividades = PaeInscripcionActividades.objects.values_list(
                            'matricula__inscripcion__coordinacion__nombre', 'matricula__inscripcion__carrera__nombre',
                            'actividades__periodoarea__areas__nombre', 'actividades__nombre').filter(
                            actividades__periodoarea__periodo=periodo,
                            actividades__coordinacion=coordinacion,
                            matricula__inscripcion__coordinacion=coordinacion, status=True,
                            actividades__periodoarea__status=True, actividades__status=True).order_by(
                            'matricula__inscripcion__coordinacion__nombre', 'matricula__inscripcion__carrera__nombre',
                            'actividades__periodoarea__areas__nombre', 'actividades__nombre',
                            'actividades__periodoarea__nombre').annotate(count=Count('matricula_id'))
                    else:
                        actividades = PaeInscripcionActividades.objects.values_list(
                            'matricula__inscripcion__coordinacion__nombre', 'matricula__inscripcion__carrera__nombre',
                            'actividades__periodoarea__areas__nombre', 'actividades__nombre').filter(
                            actividades__periodoarea__periodo=periodo, status=True,
                            actividades__periodoarea__status=True, actividades__status=True).order_by(
                            'matricula__inscripcion__coordinacion__nombre', 'matricula__inscripcion__carrera__nombre',
                            'actividades__periodoarea__areas__nombre', 'actividades__nombre',
                            'actividades__periodoarea__nombre').annotate(count=Count('matricula_id'))
                    row_num = 4
                    for actividad in actividades:
                        i = 0
                        campo1 = actividad[0]
                        campo2 = actividad[1]
                        campo3 = actividad[2]
                        campo4 = actividad[3]
                        campo5 = actividad[4]

                        ws.write(row_num, 0, campo1, font_style)
                        ws.write(row_num, 1, campo2, font_style)
                        ws.write(row_num, 2, campo3, font_style)
                        ws.write(row_num, 3, campo4, font_style)
                        ws.write(row_num, 4, campo5, font_style)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'editfechaactividad':
                try:
                    data['title'] = u'Editar Cronograma'
                    data['fechaactividad'] = fechaactividad = PaeFechaActividad.objects.get(pk=request.GET['idfechaactividad'])
                    form = PaeFechaActividadesForm(initial={'profesor': fechaactividad.tutor,
                                                            'lugar': fechaactividad.lugar,
                                                            'observacion': fechaactividad.observacion,
                                                            'fecha': fechaactividad.fecha})
                    data['form'] = form
                    return render(request, "adm_paextracurricular/editfechaactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'editareaperiodo':
                try:
                    data['title'] = u'Editar Área'
                    data['periodoareas'] = periodoareas = PaePeriodoAreas.objects.get(pk=request.GET['id'])
                    form = PaeAreaPeriodoForm(initial={'nombre': periodoareas.nombre,
                                                       'area': periodoareas.areas})
                    data['form'] = form
                    return render(request, "adm_paextracurricular/editareaperiodo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editactividad':
                try:
                    data['title'] = u'Editar Actividad'
                    data['actividades'] = actividades = PaeActividadesPeriodoAreas.objects.get(pk=request.GET['id'])
                    form = PaeActividadesPeriodoAreasForm(initial={'nombre': actividades.nombre,
                                                                   'coordinacion': actividades.coordinacion,
                                                                   'descripcion': actividades.descripcion,
                                                                   'fechainicio': actividades.fechainicio,
                                                                   'fechafin': actividades.fechafin,
                                                                   'cupo': actividades.cupo,
                                                                   'minimaasistencia': actividades.minimaasistencia,
                                                                   'maximacalificacion': actividades.maximacalificacion,
                                                                   'notaaprobacion': actividades.notaaprobacion,
                                                                   'calificar': actividades.calificar,
                                                                   'general': actividades.general,
                                                                   'carrera': actividades.carrera,
                                                                   'nivelminimo': actividades.nivelminimo,
                                                                   'nivelmaximo': actividades.nivelmaximo,
                                                                   'nivel': actividades.nivel,
                                                                   'tutorprincipal': actividades.tutorprincipal,
                                                                   'link': actividades.link,
                                                                   'grupo': actividades.grupo,
                                                                   })
                    form.editar(actividades.coordinacion.id)
                    form.cargarnivel(periodo)
                    data['form'] = form
                    return render(request, "adm_paextracurricular/editactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'listaactvidades':
                try:
                    data['title'] = u'Actividades'
                    search = None
                    ids = None
                    data['periodoarea'] = periodoarea = PaePeriodoAreas.objects.get(pk=request.GET['idperiodoarea'])
                    actividades = PaeActividadesPeriodoAreas.objects.filter(periodoarea_id=periodoarea.id, status=True).order_by('coordinacion', 'nombre')
                    coordinacionesid = actividades.values_list("coordinacion__id", flat=False)
                    listacoorid = []
                    for cor in coordinacionesid:
                        if not cor in listacoorid:
                            listacoorid.append(cor)
                    listacoorid.sort()
                    data['coordinaciones'] = Coordinacion.objects.filter(pk__in=[x[0] for x in listacoorid])
                    actividades = actividades.filter(coordinacion__in=persona.mis_coordinaciones())
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            actividades = actividades.filter(Q(nombre__icontains=search) | Q(descripcion__icontains=search))
                        else:
                            actividades = actividades.filter((Q(nombre__icontains=ss[0])& Q(nombre__icontains=ss[1])) | (Q(descripcion__icontains=ss[1])& Q(descripcion__icontains=ss[1])))
                    if 'f' in request.GET and int(request.GET['f'])>0:
                        data['fid'] = int(request.GET['f'])
                        actividades = actividades.filter(coordinacion__id=int(request.GET['f']))
                    paging = MiPaginador(actividades, 20)
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
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['actividades'] = page.object_list
                    return render(request, "adm_paextracurricular/listaactvidades.html", data)
                except Exception as ex:
                    pass

            elif action == 'listafechasactvidades':
                try:
                    data['title'] = u'Actividades'
                    data['actividad'] = actividad = PaeActividadesPeriodoAreas.objects.get(pk=request.GET['idactividad'])
                    data['fechaactividades'] = PaeFechaActividad.objects.filter(actividad=actividad, status=True).order_by('fecha')
                    return render(request, "adm_paextracurricular/listafechasactvidades.html", data)
                except Exception as ex:
                    pass

            elif action == 'listainscritos':
                try:
                    data['title'] = u'Listado de Inscritos'
                    search = None
                    ids = None
                    data['actividad'] = actividad = PaeActividadesPeriodoAreas.objects.get(pk=request.GET['idactividad'], status=True)
                    if 's' in request.GET:
                        search = request.GET['s']
                        if ' ' in search:
                            s = search.split(" ")
                            listadoinscritos = PaeInscripcionActividades.objects.filter(((Q(matricula__inscripcion__persona__apellido1__contains=s[0]) &
                                                                                          Q(matricula__inscripcion__persona__apellido2__contains=s[1]))),
                                                                                        actividades=actividad,status=True).order_by('matricula__inscripcion__persona__apellido1','matricula__inscripcion__persona__apellido2')
                        else:
                            listadoinscritos = PaeInscripcionActividades.objects.filter(
                                (Q(matricula__inscripcion__persona__nombres__contains=search) |
                                 Q(matricula__inscripcion__persona__apellido1__contains=search) |
                                 Q(matricula__inscripcion__persona__apellido2__contains=search)),
                                actividades=actividad, status=True).order_by('matricula__inscripcion__persona__apellido1','matricula__inscripcion__persona__apellido2')
                    else:
                        listadoinscritos = PaeInscripcionActividades.objects.filter(actividades=actividad, status=True).order_by('matricula__inscripcion__persona__apellido1','matricula__inscripcion__persona__apellido2')
                    # participantes = ParticipantesMatrices.objects.filter(status=True, matrizevidencia_id=2, proyecto=proyectos).order_by('-tipoparticipante', 'inscripcion__persona__apellido1')
                    paging = MiPaginador(listadoinscritos, 25)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listadoinscritos'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_paextracurricular/listadoinscritos.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteactividad':
                try:
                    data['title'] = u'Eliminar Actividad'
                    data['actividad'] = PaeActividadesPeriodoAreas.objects.get(pk=request.GET['idactividad'])
                    return render(request, "adm_paextracurricular/deleteactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteareaperiodo':
                try:
                    data['title'] = u'Eliminar Área'
                    data['areaperiodo'] = PaePeriodoAreas.objects.get(pk=request.GET['idareaperiodo'])
                    return render(request, "adm_paextracurricular/deleteareaperiodo.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletecronograma':
                try:
                    data['title'] = u'Eliminar Cronograma'
                    data['fechaactividad'] = PaeFechaActividad.objects.get(pk=request.GET['idfechaactividad'])
                    return render(request, "adm_paextracurricular/deletecronograma.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteparticipante':
                try:
                    data['title'] = u'Eliminar Participante'
                    data['inscrito'] = PaeInscripcionActividades.objects.get(pk=request.GET['idlista'])
                    return render(request, "adm_paextracurricular/deleteparticipante.html", data)
                except Exception as ex:
                    pass

            elif action == 'addinscripcion':
                try:
                    data['actividad'] = actividad = PaeActividadesPeriodoAreas.objects.get(pk=request.GET['id'])
                    data['title'] = u'Inscribir ' + str(actividad.nombre)
                    form = PaeInscripcionActividadesFrom()
                    data['form'] = form
                    return render(request, "adm_paextracurricular/addinscripcion.html", data)
                except Exception as ex:
                    pass

            elif action == 'busquedaalumno':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if s.__len__() == 2:
                        persona = Persona.objects.filter(apellido1__icontains=s[0], apellido2__icontains=s[1],real=True).distinct()[:15]
                    else:
                        persona = Persona.objects.filter(Q(real=True) & ( Q(nombres__contains=s[0]) | Q(apellido1__contains=s[0]) | Q( apellido2__contains=s[0]) | Q(cedula__contains=s[0]))).distinct()[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_repr()} for x in persona]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Listado de Áreas'
            data['periodosareas'] = PaePeriodoAreas.objects.select_related().filter(periodo=periodo, status=True).order_by('nombre')
            return render(request, "adm_paextracurricular/view.html", data)