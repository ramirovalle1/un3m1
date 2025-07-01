# -*- coding: UTF-8 -*-
import random
from datetime import datetime
from django.template.loader import get_template
import xlwt
from xlwt import *
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template import Context
from decorators import secure_module, last_access
from settings import MATRICULACION_LIBRE, NOTA_ESTADO_EN_CURSO, CALCULO_POR_CREDITO
from sga.commonviews import adduserdata, conflicto_materias_seleccionadas
from sga.funciones import MiPaginador, log
from sga.models import MateriaCupo, MateriaAsignada, Materia, AgregacionEliminacionMaterias


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    miscarreras = persona.mis_carreras()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addaprobacion':
            try:
                solicitud = MateriaCupo.objects.get(pk=request.POST['id'])
                if int(request.POST['estadosolicitud']) == 2:
                    matricula = solicitud.matricula
                    materia = solicitud.materia
                    if matricula.materiaasignada_set.values('id').filter(materia=materia).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra matriculado en esta materia"})
                    if matricula.inscripcion.existe_en_malla(materia.asignatura) and not matricula.inscripcion.puede_tomar_materia(materia.asignatura):
                        return JsonResponse({"result": "bad", "mensaje": u"No puede tomar esta materia por tener precedencias"})
                    if matricula.inscripcion.existe_en_modulos(materia.asignatura) and not matricula.inscripcion.puede_tomar_materia_modulo(materia.asignatura):
                        return JsonResponse({"result": "bad", "mensaje": u"No puede tomar esta materia por tener precedencias"})
                    if MATRICULACION_LIBRE:
                        if not materia.tiene_capacidad():
                            materia.cupo = materia.cupo + 1
                            materia.save(request)
                    materiaasignada = MateriaAsignada(matricula=matricula,
                                                      materia=materia,
                                                      notafinal=0,
                                                      asistenciafinal=0,
                                                      cerrado=False,
                                                      observaciones='',
                                                      estado_id=NOTA_ESTADO_EN_CURSO)
                    materiaasignada.save(request)
                    matricula.actualizar_horas_creditos()
                    conflicto = materiaasignada.matricula.verificar_conflicto_en_materias()
                    if conflicto:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": conflicto})
                    materiaasignada.matriculas = materiaasignada.cantidad_matriculas()
                    materiaasignada.asistencias()
                    materiaasignada.evaluacion()
                    materiaasignada.mis_planificaciones()
                    materiaasignada.save(request)
                    if matricula.nivel.nivelgrado:
                        log(u'Adiciono materia por aprobación de cupo: %s' % materiaasignada, request, "add")
                    else:
                        if datetime.now().date() < matricula.nivel.periodo.inicio_agregacion:
                            # AGREGACION DE MATERIAS EN MATRICULACION REGULAR SIN REALIZAR PAGOS
                            materiaasignada.save()
                            log(u'Adiciono materia por aprobación de cupo: %s' % materiaasignada, request, "add")
                            if CALCULO_POR_CREDITO:
                                matricula.agregacion_aux(request)
                                # matricula.calcular_rubros_matricula(cobro)
                        elif matricula.nivel.periodo.fecha_agregaciones():
                            # AGREGACION DE MATERIAS EN FECHAS DE AGREGACIONES
                            registro = AgregacionEliminacionMaterias(matricula=matricula,
                                                                     agregacion=True,
                                                                     asignatura=materiaasignada.materia.asignatura,
                                                                     responsable=request.session['persona'],
                                                                     fecha=datetime.now().date(),
                                                                     creditos=materiaasignada.materia.creditos,
                                                                     nivelmalla=materiaasignada.materia.nivel.nivelmalla if materiaasignada.materia.nivel.nivelmalla else None,
                                                                     matriculas=materiaasignada.matriculas)
                            registro.save()
                            log(u'Adiciono materia por aprobación de cupo: %s' % materiaasignada, request, "add")
                            if CALCULO_POR_CREDITO:
                                matricula.agregacion_aux(request)
                        else:
                            # AGREGACION DE MATERIAS TERMINADA LAS AGREGACIONES
                            if materia.asignatura.modulo:
                                registro = AgregacionEliminacionMaterias(matricula=matricula,
                                                                         agregacion=True,
                                                                         asignatura=materiaasignada.materia.asignatura,
                                                                         responsable=request.session['persona'],
                                                                         fecha=datetime.now().date(),
                                                                         creditos=materiaasignada.materia.creditos,
                                                                         nivelmalla=materiaasignada.materia.nivel.nivelmalla if materiaasignada.materia.nivel.nivelmalla else None,
                                                                         matriculas=materiaasignada.matriculas)
                                registro.save()
                                log(u'Adiciono materia por aprobación de cupo: %s' % materiaasignada, request, "add")
                                if CALCULO_POR_CREDITO:
                                    matricula.agregacion_aux(request)
                            else:
                                raise NameError('Error')
                solicitud.fechaaprueba = datetime.now()
                solicitud.obseaprueba = request.POST['obsaprueba']
                solicitud.personaaprueba = persona
                solicitud.estadosolicitud = request.POST['estadosolicitud']
                solicitud.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'reporteexcel':
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
                        'Content-Disposition'] = 'attachment; filename=exp_xls_post_part_' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"FACULTAD", 8000),
                        (u"CARRERA", 8000),
                        (u"CEDULA", 3000),
                        (u"NOMBRES", 6000),
                        (u"ASIGNATURA", 10000),
                        (u"NIVEL ASIG.", 6000),
                        (u"PARALELO ASIG.", 4000),
                        (u"PROFESOR PRINCIPAL ASIG.", 6000),
                        (u"FECHA", 3000),
                        (u"ESTADO", 3000),
                    ]
                    row_num = 1
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    results = MateriaCupo.objects.filter(matricula__nivel__periodo=periodo, status=True).order_by('matricula__inscripcion__persona__apellido1')
                    row_num = 2
                    for r in results:
                        i = 0
                        campo1 = r.matricula.inscripcion.coordinacion.nombre
                        campo2 = r.matricula.inscripcion.carrera.nombre
                        campo3 = r.matricula.inscripcion.persona.cedula
                        campo4 = r.matricula.inscripcion.persona.nombre_completo_inverso()
                        campo5 = r.materia.asignatura.__str__()
                        campo6 = r.materia.nivel.paralelo.__str__()
                        campo7 = r.materia.paralelo.__str__()
                        campo8 = r.materia.profesor_principal().__str__() if r.materia.profesor_principal() else ""
                        campo9 = r.fecha_creacion
                        campo10 = r.get_estadosolicitud_display()
                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        ws.write(row_num, 6, campo7, font_style2)
                        ws.write(row_num, 7, campo8, font_style2)
                        ws.write(row_num, 8, campo9, date_format)
                        ws.write(row_num, 9, campo10, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'verdetalle':
                try:
                    data = {}
                    data['materiacupo'] = MateriaCupo.objects.get(pk=request.GET['id'], status=True)
                    template = get_template("adm_solicitudcupo/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'detalle':
                try:
                    data = {}
                    data['materiacupo'] = MateriaCupo.objects.get(pk=request.GET['id'], status=True)
                    template = get_template("adm_solicitudcupo/detalle_aprobar.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Solicitudes de Cupos'
            search = None
            ids = None
            inscripcionid = None
            if 'id' in request.GET:
                ids = request.GET['id']
                solicitudcupo = MateriaCupo.objects.select_related().filter(pk=ids,status=True).order_by('estadosolicitud', '-fecha_creacion')
            elif 's' in request.GET:
                search = request.GET['s']
                if ' ' in search:
                    s = search.split(" ")
                    solicitudcupo = MateriaCupo.objects.select_related().filter(Q(matricula__inscripcion__persona__apellido1__contains=s[0]) & Q(matricula__inscripcion__persona__apellido2__contains=s[1]), matricula__nivel__periodo=periodo, status=True).order_by('matricula__inscripcion__persona__apellido1')
                else:
                    solicitudcupo = MateriaCupo.objects.select_related().filter(Q(matricula__inscripcion__persona__nombres__contains=search) | Q(matricula__inscripcion__persona__apellido1__contains=search) | Q(matricula__inscripcion__persona__apellido2__contains=search) | Q(matricula__inscripcion__persona__cedula__contains=search), matricula__nivel__periodo=periodo, status=True).order_by('estadosolicitud', '-fecha_creacion')
            else:
                solicitudcupo = MateriaCupo.objects.select_related().filter(matricula__nivel__periodo=periodo, status=True).order_by('estadosolicitud', '-fecha_creacion')
            paging = MiPaginador(solicitudcupo, 25)
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
            data['solicitudcupo'] = page.object_list
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            return render(request, "adm_solicitudcupo/view.html", data)