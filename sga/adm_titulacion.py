# # -*- coding: latin-1 -*-
# import json
# import os
# import random
# from datetime import datetime, timedelta
# import xlwt
# from django.contrib.auth.decorators import login_required
# from django.db import transaction, connection
# from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
# from django.shortcuts import render
# from xlwt import *
# from decorators import secure_module, last_access
# from settings import MATRICULACION_LIBRE, UTILIZA_GRUPOS_ALUMNOS, NOMBRE_NIVEL_AUTOMATICO, MATRICULACION_POR_NIVEL, CAPACIDAD_MATERIA_INICIAL, \
#     CUPO_POR_MATERIA, APROBACION_DISTRIBUTIVO, USA_EVALUACION_INTEGRAL, TIPO_DOCENTE_TEORIA, TIPO_DOCENTE_PRACTICA, \
#     VERIFICAR_CONFLICTO_DOCENTE, TIPO_CUOTA_RUBRO, SITE_ROOT
# from sga.commonviews import adduserdata, obtener_reporte, conflicto_materias_seleccionadas
# from sga.forms import NivelForm, NivelFormEdit, ProfesorMateriaForm, PagoNivelForm, MateriaDividirForm, MateriaNivel, \
#     OtroNivelForm, MateriaNivelMalla, CambiarAulaForm, ListaModeloEvaluativoForm, CalificacionDiaForm, EvaluacionDiaForm, \
#     FechafinAsistenciasForm, EditProfesorMateriaForm
# from sga.funciones import log, convertir_fecha, puede_realizar_accion, puede_realizar_accion_afirmativo
# from sga.models import Periodo, Sede, Carrera, Nivel, Materia, ProfesorMateria, MateriaAsignada, PagoNivel, \
#     Coordinacion, Asignatura, AsignaturaMalla, \
#     Malla, ModeloEvaluativo, NivelMalla, EvaluacionGenerica, Leccion, AlumnosPracticaMateria, Matricula, DiasNoLaborable
# unicode =str
#
# @login_required(redirect_field_name='ret', login_url='/loginsga')
# # @secure_module
# @last_access
# @transaction.atomic()
# def view(request):
#     data = {}
#     adduserdata(request, data)
#     persona = request.session['persona']
#     periodo = request.session['periodo']
#     if request.method == 'POST':
#         action = request.POST['action']
#
#         if action == 'add':
#             try:
#                 periodo = Periodo.objects.get(pk=request.POST['periodo'])
#                 form = NivelForm(request.POST)
#                 if form.is_valid():
#                     if periodo.fin < form.cleaned_data['fin']:
#                         return JsonResponse({"result": "bad", "mensaje": u"Fecha fin incorrecta."})
#                     if periodo.inicio > form.cleaned_data['inicio']:
#                         return JsonResponse({"result": "bad", "mensaje": u"Fecha inicio incorrecta."})
#                     if form.cleaned_data['fechatopematriculaesp'] < form.cleaned_data['fechatopematriculaext'] or form.cleaned_data['fechatopematriculaesp'] > form.cleaned_data['fin']:
#                         return JsonResponse({"result": "bad", "mensaje": u"Fecha tope matricula especial incorrecta."})
#                     if form.cleaned_data['fechatopematriculaext'] < form.cleaned_data['fechatopematricula']:
#                         return JsonResponse({"result": "bad", "mensaje": u"Fecha tope matricula incorrecta."})
#                     if MATRICULACION_LIBRE:
#                         coordinacion = Coordinacion.objects.get(pk=request.POST['coordinacion'])
#                         if NOMBRE_NIVEL_AUTOMATICO:
#                             nombre = form.cleaned_data['sesion'].nombre + ' - ' + coordinacion.alias
#                         else:
#                             nombre = form.cleaned_data['paralelo']
#                         if Nivel.objects.filter(periodo=periodo, sesion=form.cleaned_data['sesion'], modalidad=form.cleaned_data['modalidad'], nivellibrecoordinacion__coordinacion=coordinacion).exists():
#                             return JsonResponse({"result": "bad", "mensaje": u"Ya existe un nivel creado en esa sesion y modalidad."})
#                         nivel = Nivel(periodo=periodo,
#                                       sesion=form.cleaned_data['sesion'],
#                                       inicio=form.cleaned_data['inicio'],
#                                       fin=form.cleaned_data['fin'],
#                                       paralelo=nombre,
#                                       modalidad=form.cleaned_data['modalidad'],
#                                       sede=coordinacion.sede,
#                                       cerrado=False,
#                                       fechatopematricula=form.cleaned_data['fechatopematricula'],
#                                       fechatopematriculaex=form.cleaned_data['fechatopematriculaext'],
#                                       fechatopematriculaes=form.cleaned_data['fechatopematriculaesp'],
#                                       nivelgrado=form.cleaned_data['nivelgrado'],
#                                       aplicabecas=True if not form.cleaned_data['nivelgrado'] else False)
#                         nivel.save(request)
#                         nivel.coordinacion(coordinacion)
#                     else:
#                         sede = Sede.objects.get(pk=request.POST['sede'])
#                         carrera = Carrera.objects.get(pk=request.POST['carrera'])
#                         nivel = Nivel(periodo=periodo,
#                                       sede=sede,
#                                       carrera=carrera,
#                                       malla=form.cleaned_data['malla'],
#                                       nivelmalla=form.cleaned_data['nivelmalla'],
#                                       sesion=form.cleaned_data['grupo'].sesion if UTILIZA_GRUPOS_ALUMNOS and not MATRICULACION_POR_NIVEL else form.cleaned_data['sesion'],
#                                       modalidad=form.cleaned_data['grupo'].modalidad if UTILIZA_GRUPOS_ALUMNOS and not MATRICULACION_POR_NIVEL else form.cleaned_data['modalidad'],
#                                       grupo=form.cleaned_data['grupo'] if UTILIZA_GRUPOS_ALUMNOS and not MATRICULACION_POR_NIVEL else None,
#                                       inicio=form.cleaned_data['inicio'],
#                                       fin=form.cleaned_data['fin'],
#                                       paralelo=form.cleaned_data['paralelo'],
#                                       cerrado=False,
#                                       capacidadmatricula=form.cleaned_data['capacidad'],
#                                       fechatopematricula=form.cleaned_data['fechatopematricula'],
#                                       fechatopematriculaex=form.cleaned_data['fechatopematriculaext'],
#                                       fechatopematriculaes=form.cleaned_data['fechatopematriculaesp'],
#                                       nivelgrado=form.cleaned_data['nivelgrado'],
#                                       aplicabecas=True if not form.cleaned_data['nivelgrado'] else False)
#                         nivel.save(request)
#                         nivel.coordinacion()
#                         malla = form.cleaned_data['malla']
#                         nivelmalla = form.cleaned_data['nivelmalla']
#                         modelo = ModeloEvaluativo.objects.filter(principal=True)[0]
#                         for materiamalla in malla.asignaturamalla_set.filter(nivelmalla=nivelmalla):
#                             materianivel = Materia(asignatura=materiamalla.asignatura,
#                                                    asignaturamalla=materiamalla,
#                                                    nivel=nivel,
#                                                    horas=materiamalla.horas,
#                                                    horassemanales=materiamalla.horas,
#                                                    creditos=materiamalla.creditos,
#                                                    identificacion=materiamalla.identificacion,
#                                                    inicio=periodo.inicio,
#                                                    fin=periodo.fin,
#                                                    rectora=materiamalla.rectora,
#                                                    practicas=materiamalla.practicas,
#                                                    modeloevaluativo=modelo,
#                                                    cupo=CAPACIDAD_MATERIA_INICIAL if CUPO_POR_MATERIA else 0,
#                                                    cerrado=False)
#                             materianivel.save(request)
#                     log(u'Adiciono nivel: %s' % nivel, request, "add")
#                     return JsonResponse({"result": "ok"})
#                 else:
#                      raise NameError('Error')
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
#
#         elif action == 'nivelvisible':
#             try:
#                 nivel = Nivel.objects.get(pk=request.POST['nid'])
#                 status = True if request.POST['status'] == "1" else False
#                 ext = nivel.extension()
#                 ext.visible = status
#                 ext.save(request)
#                 log(u'cambio estado visible de nivel: %s' % nivel, request, "edit")
#                 return JsonResponse({"result": "ok"})
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad"})
#
#         elif action == 'nivelmatricular':
#             try:
#                 nivel = Nivel.objects.get(pk=request.POST['nid'])
#                 status = True if request.POST['status'] == "1" else False
#                 ext = nivel.extension()
#                 ext.puedematricular = status
#                 ext.save(request)
#                 log(u'cambio estado puedematricular de nivel: %s' % nivel, request, "edit")
#                 return JsonResponse({"result": "ok"})
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad"})
#
#         elif action == 'dividir':
#             try:
#                 f = MateriaDividirForm(request.POST)
#                 if f.is_valid():
#                     for ma_id in request.POST.getlist('ins'):
#                         ma = MateriaAsignada.objects.get(pk=ma_id, matricula__estado_matricula__in=[2,3])
#                         ma.materia = f.cleaned_data['materia']
#                         ma.save(request)
#                     log(u'dividio materia: %s' % ma, request, "edit")
#                     return JsonResponse({"result": "ok"})
#                 else:
#                     raise NameError('Error')
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
#
#         elif action == 'addpagos':
#             try:
#                 nivel = Nivel.objects.get(pk=request.POST['id'])
#                 f = PagoNivelForm(request.POST)
#                 if f.is_valid():
#                     if PagoNivel.objects.filter(nivel=nivel, tipo=f.cleaned_data['tipo'], cuota=f.cleaned_data['cuota']).exists():
#                         return JsonResponse({"result": "bad", "mensaje": u"Ya existe ese tipo de pago registrado."})
#                     pagonivel = PagoNivel(nivel=nivel,
#                                           tipo=f.cleaned_data['tipo'],
#                                           cuota=f.cleaned_data['cuota'],
#                                           fecha=f.cleaned_data['fecha'],
#                                           valor=f.cleaned_data['valor'])
#                     pagonivel.save(request)
#                     log(u'Adiciono pago nivel: %s' % pagonivel, request, "add")
#                     return JsonResponse({"result": "ok"})
#                 else:
#                     raise NameError('Error')
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
#
#         elif action == 'editpagos':
#             try:
#                 pagonivel = PagoNivel.objects.get(pk=request.POST['id'])
#                 nivel = pagonivel.nivel
#                 f = PagoNivelForm(request.POST)
#                 if f.is_valid():
#                     pagonivel.fecha = f.cleaned_data['fecha']
#                     pagonivel.valor = f.cleaned_data['valor']
#                     pagonivel.save(request)
#                     log(u'Modifico pago nivel: %s' % pagonivel, request, "edit")
#                     return JsonResponse({"result": "ok"})
#                 else:
#                      raise NameError('Error')
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
#
#         elif action == 'edit':
#             try:
#                 f = NivelFormEdit(request.POST)
#                 nivel = Nivel.objects.get(pk=request.POST['id'])
#                 if f.is_valid():
#                     if nivel.periodo.fin < f.cleaned_data['fin']:
#                         return JsonResponse({"result": "bad", "mensaje": u"Fecha fin incorrecta."})
#                     if nivel.periodo.inicio > f.cleaned_data['inicio']:
#                         return JsonResponse({"result": "bad", "mensaje": u"Fecha inicio incorrecta."})
#                     if f.cleaned_data['fechatopematriculaesp'] < f.cleaned_data['fechatopematriculaext'] or f.cleaned_data['fechatopematriculaesp'] > f.cleaned_data['fin']:
#                         return JsonResponse({"result": "bad", "mensaje": u"Fecha tope matricula especial incorrecta."})
#                     if f.cleaned_data['fechatopematriculaext'] < f.cleaned_data['fechatopematricula']:
#                         return JsonResponse({"result": "bad", "mensaje": u"Fecha tope matricula incorrecta."})
#                     nivel.paralelo = f.cleaned_data['paralelo']
#                     nivel.inicio = f.cleaned_data['inicio']
#                     nivel.fin = f.cleaned_data['fin']
#                     nivel.fechatopematricula = f.cleaned_data['fechatopematricula']
#                     nivel.fechatopematriculaex = f.cleaned_data['fechatopematriculaext']
#                     nivel.fechatopematriculaes = f.cleaned_data['fechatopematriculaesp']
#                     nivel.capacidadmatricula = f.cleaned_data['capacidad']
#                     log(u'Modifico nivel: %s' % nivel, request, "edit")
#                     nivel.save(request)
#                     return JsonResponse({"result": "ok"})
#                 else:
#                     raise NameError('Error')
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
#
#         elif action == 'copy':
#             try:
#                 f = NivelFormEdit(request.POST)
#                 nivel = Nivel.objects.get(pk=request.POST['id'])
#                 if f.is_valid():
#                     nuevonivel = Nivel(periodo=nivel.periodo,
#                                        sede=nivel.sede,
#                                        carrera=nivel.carrera,
#                                        modalidad=nivel.modalidad,
#                                        malla=nivel.malla,
#                                        nivelmalla=nivel.nivelmalla,
#                                        sesion=nivel.sesion,
#                                        grupo=nivel.grupo,
#                                        inicio=f.cleaned_data['inicio'],
#                                        fin=f.cleaned_data['fin'],
#                                        paralelo=f.cleaned_data['paralelo'],
#                                        cerrado=False,
#                                        capacidadmatricula=f.cleaned_data['capacidad'],
#                                        fechatopematricula=f.cleaned_data['fechatopematricula'],
#                                        fechatopematriculaex=f.cleaned_data['fechatopematriculaext'],
#                                        fechatopematriculaes=f.cleaned_data['fechatopematriculaesp'],
#                                        nivelgrado=nivel.nivelgrado,
#                                        aplicabecas=nivel.aplicabecas)
#                     nuevonivel.save(request)
#                     for materia in nivel.materia_set.all():
#                             materianivel = Materia(asignatura=materia.asignatura,
#                                                    nivel=nuevonivel,
#                                                    horas=materia.horas,
#                                                    horassemanales=int(materia.horas / 16),
#                                                    creditos=materia.creditos,
#                                                    identificacion=materia.identificacion,
#                                                    inicio=materia.inicio,
#                                                    fin=materia.fin,
#                                                    rectora=materia.rectora,
#                                                    practicas=materia.practicas,
#                                                    modeloevaluativo=materia.modeloevaluativo,
#                                                    cerrado=False)
#                             materianivel.save(request)
#                     for pago in nivel.pagonivel_set.all():
#                         pagonivel = PagoNivel(nivel=nuevonivel,
#                                               tipo=pago.tipo,
#                                               fecha=pago.fecha,
#                                               valor=pago.valor)
#                         pagonivel.save(request)
#                     return JsonResponse({"result": "ok"})
#                 else:
#                      raise NameError('Error')
#             except Exception as d:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
#
#         elif action == 'copypagos':
#             try:
#                 nivel = Nivel.objects.get(pk=request.POST['id'])
#                 f = OtroNivelForm(request.POST)
#                 if f.is_valid():
#                     nuevonivel = f.cleaned_data['nivel']
#                     pagos = nuevonivel.pagonivel_set.all()
#                     for pago in pagos:
#                         pago.delete()
#                     for pago in nivel.pagonivel_set.all():
#                         pagonivel = PagoNivel(nivel=nuevonivel,
#                                               tipo=pago.tipo,
#                                               fecha=pago.fecha,
#                                               valor=pago.valor)
#                         pagonivel.save(request)
#                     log(u'Duplico pagos: %s - %s' % (nivel, f.cleaned_data['nivel']), request, "edit")
#                     return JsonResponse({"result": "ok"})
#                 else:
#                     raise NameError('Error')
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
#
#         elif action == 'avance_asistencia':
#             try:
#                 periodo = Periodo.objects.get(pk=int(request.POST['idperiodo']))
#
#                 coordinaciones = Coordinacion.objects.filter(carrera__malla__asignaturamalla__materia__nivel__periodo=periodo).order_by('-id').distinct()
#                 diasnolaborables = DiasNoLaborable.objects.filter(periodo=periodo).order_by('fecha')
#                 # claseshorarios = Clase.objects.filter(materia__nivel__periodo=periodo, activo=True).distinct().order_by('materia__profesormateria__profesor', 'turno__comienza')
#                 output_folder = os.path.join(os.path.join(SITE_ROOT, 'media', 'asistencias'))
#                 __author__ = 'Unemi'
#                 style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
#                 style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
#                 style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
#                 title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
#                 style1 = easyxf(num_format_str='D-MMM-YY')
#                 font_style = XFStyle()
#                 font_style.font.bold = True
#                 font_style2 = XFStyle()
#                 font_style2.font.bold = False
#                 wb = Workbook(encoding='utf-8')
#                 for coordinacion1 in coordinaciones:
#                     ws = wb.add_sheet(coordinacion1.alias)
#                     coordinacionid=coordinacion1.id
#                     ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
#                     ws.write(1, 0, "Periodo: "+periodo.nombre, font_style2)
#                     ws.write(2, 0, "Fecha Corte: "+request.POST['fecha'], font_style2)
#                     nombre = "AVANCE_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
#                     filename = os.path.join(output_folder, nombre)
#                     ruta = "media/asistencias/" + nombre
#                     book = xlwt.Workbook()
#                     columns = [
#                         (u"FACULTAD", 6000),
#                         (u"CARRERA", 6000),
#                         (u"NIVEL", 6000),
#                         (u"PARALELO", 6000),
#                         (u"DOCENTE", 6000),
#                         (u"ASIGNATURA", 6000),
#                         (u"HORAS PROGRAMADAS MENSUAL", 6000),
#                         (u"HORAS INGRESADAS", 6000),
#                         (u"HORAS FALTAS", 6000),
#                         (u"HORAS TOTAL ASISTENCIAS", 6000),
#                         (u"PORCENTAJE AVANCE FECHA TOPE", 6000),
#                         (u"PORCENTAJE AVANCE SEMESTRE", 6000),
#                         (u"FECHA INICIO MATERIA", 6000),
#                         (u"FECHA FIN MATERIA", 6000),
#                     ]
#                     row_num = 3
#                     for col_num in range(len(columns)):
#                         ws.write(row_num, col_num, columns[col_num][0], font_style)
#                         ws.col(col_num).width = columns[col_num][1]
#
#                     # profesormateria = ProfesorMateria.objects.filter(materia__nivel__periodo=periodo, principal=True).distinct().order_by('materia__asignaturamalla__malla__carrera','profesor')
#                     # asistencialeccion = AsistenciaLeccion.objects.filter(materiaasignada__materia__nivel__periodo=periodo, leccion__fecha__lte=fecha).order_by("materiaasignada__materia").distinct("materiaasignada__materia")
#                     cursor = connection.cursor()
#                     sql = "select tabladocente.facultad , tabladocente.carrera, tabladocente.nivel, tabladocente.paralelo, tabladocente.docente,tabladocente.asignatura, tabladocente.horas , COALESCE(tablaasistencia.asistencia,0) as asistencia, tabladocente.inicio, tabladocente.fin,  " \
#                           " (select count(*) from sga_faltasmateriaperiodo fm1 where fm1.materia_id=tabladocente.materiaid) as faltas " \
#                           " from (select pm.id as profesormateriaid, m.inicio, m.fin, m.id as materiaid, co.nombre as facultad, ca.nombre as carrera, nm.nombre as nivel, m.paralelo, (per.apellido1 || ' ' || per.apellido2 || ' ' || per.nombres) as docente,asi.nombre as asignatura, m.horas " \
#                           " from sga_profesormateria pm, sga_materia m, sga_nivel n, sga_asignaturamalla am, sga_malla ma,sga_carrera ca, sga_coordinacion_carrera cc, sga_coordinacion co, sga_nivelmalla nm, sga_profesor pr, sga_persona per, sga_asignatura asi " \
#                           " where m.id=pm.materia_id and n.id=m.nivel_id and am.id=m.asignaturamalla_id and ma.id=am.malla_id and ca.id=ma.carrera_id and cc.carrera_id=ca.id and co.id=cc.coordinacion_id and nm.id=am.nivelmalla_id and pr.id=pm.profesor_id and per.id=pr.persona_id " \
#                           " and asi.id=m.asignatura_id and n.periodo_id= "+ request.POST['idperiodo'] +" and co.id="+ str(coordinacionid) +" order by co.nombre, ca.nombre, nm.nombre, m.paralelo, docente) as tabladocente " \
#                           " left join (select mat1.id as materiaid, count(mat1.id) as asistencia from sga_leccion l1 , sga_clase c1 , sga_materia mat1, sga_nivel ni1 where l1.clase_id=c1.id and c1.materia_id=mat1.id and mat1.nivel_id=ni1.id and l1.fecha<= '"+ request.POST['fecha'] +"' and ni1.periodo_id="+ request.POST['idperiodo'] +" " \
#                           " and l1.fecha not in (select dnl1.fecha from sga_diasnolaborable dnl1 where dnl1.periodo_id="+ request.POST['idperiodo'] +") GROUP by mat1.id) as tablaasistencia on tablaasistencia.materiaid=tabladocente.materiaid order by tabladocente.facultad , tabladocente.carrera, tabladocente.nivel, tabladocente.paralelo, tabladocente.docente"
#                     cursor.execute(sql)
#                     results = cursor.fetchall()
#                     row_num = 4
#                     for r in results:
#                         i = 0
#                         campo1 = r[0]
#                         campo2 = r[1]
#                         campo3 = r[2]
#                         campo4 = r[3]
#                         campo5 = r[4]
#                         campo6 = r[5]
#                         campo7 = r[6]
#                         campo8 = r[7]
#                         campo9 = 0
#                         if r[6] > 0:
#                             porcentajeperiodo=round((float(r[7])/r[6])*100,2)
#                             if porcentajeperiodo>100:
#                                 porcentajeperiodo=100
#                             campo9 = porcentajeperiodo
#                         campo13 = 0
#                         if (r[10]+r[7]) > 0:
#                             porcentajefecha=round((float(r[7])/(r[10]+r[7]))*100,2)
#                             if porcentajefecha>100:
#                                 porcentajefecha=100
#                             campo13 = porcentajefecha
#
#                         campo10 = r[8]
#                         campo11 = r[9]
#                         campo12 = r[10]
#
#                         ws.write(row_num, 0, campo1, font_style2)
#                         ws.write(row_num, 1, campo2, font_style2)
#                         ws.write(row_num, 2, campo3, font_style2)
#                         ws.write(row_num, 3, campo4, font_style2)
#                         ws.write(row_num, 4, campo5, font_style2)
#                         ws.write(row_num, 5, campo6, font_style2)
#                         ws.write(row_num, 6, campo7, font_style2)
#                         ws.write(row_num, 7, campo8, font_style2)
#                         ws.write(row_num, 8, campo12, font_style2)
#                         ws.write(row_num, 9, campo12+campo8, font_style2)
#                         ws.write(row_num, 10, campo13, font_style2)
#                         ws.write(row_num, 11, campo9, font_style2)
#                         ws.write(row_num, 12, campo10, style1)
#                         ws.write(row_num, 13, campo11, style1)
#                         # while i < len(r):
#                         #     # ws.write(row_num, i, r[i], font_style)
#                         #     # ws.col(i).width = columns[i][1]
#                         row_num += 1
#                 wb.save(filename)
#                 # return book
#                 return JsonResponse({'result': 'ok', 'archivo': ruta})
#             except Exception as ex:
#                 pass
#
#         elif action == 'delete':
#             try:
#                 nivel = Nivel.objects.get(pk=request.POST['id'])
#                 log(u'Elimino nivel: %s' % nivel, request, "del")
#                 if not nivel.puede_eliminarse():
#                     return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar el nivel."})
#                 nivel.delete()
#                 return JsonResponse({"result": "ok"})
#             except Exception as ex:
#                 pass
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})
#
#         elif action == 'aprobar':
#             try:
#                 nivel = Nivel.objects.get(pk=request.POST['id'])
#                 log(u'Aprobo distributivo: %s' % nivel, request, "del")
#                 nivel.distributivoaprobado = True
#                 nivel.responsableaprobacion = request.session['persona']
#                 nivel.fechaprobacion = datetime.now().date()
#                 nivel.save(request)
#                 return JsonResponse({"result": "ok"})
#             except Exception as ex:
#                 pass
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})
#
#         elif action == 'addmateria':
#             try:
#                 nivel = Nivel.objects.get(pk=request.POST['nid'])
#                 f = MateriaNivel(request.POST)
#                 if f.is_valid():
#                     asignatura = f.cleaned_data['asignatura'] if 'asignatura' in request.POST else f.cleaned_data['asignaturamalla'].asignatura
#                     modelo = f.cleaned_data['modelo']
#                     materia = Materia(asignatura=asignatura,
#                                       asignaturamalla=f.cleaned_data['asignaturamalla'] if 'asignaturamalla' in request.POST else None,
#                                       nivel=nivel,
#                                       horas=f.cleaned_data['horas'] if not MATRICULACION_LIBRE else f.cleaned_data['asignaturamalla'].horas,
#                                       horassemanales=int(f.cleaned_data['horassemanales']),
#                                       creditos=f.cleaned_data['creditos'] if not MATRICULACION_LIBRE else f.cleaned_data['asignaturamalla'].creditos,
#                                       identificacion=f.cleaned_data['identificacion'] if not MATRICULACION_LIBRE else f.cleaned_data['asignaturamalla'].identificacion,
#                                       alias=f.cleaned_data['alias'],
#                                       paralelo=f.cleaned_data['paralelo'] if 'paralelo' in request.POST else '',
#                                       inicio=f.cleaned_data['inicio'],
#                                       fin=f.cleaned_data['fin'],
#                                       cerrado=False,
#                                       rectora=f.cleaned_data['rectora'],
#                                       practicas=f.cleaned_data['practicas'],
#                                       tutoria=f.cleaned_data['tutoria'],
#                                       grado=f.cleaned_data['grado'],
#                                       validacreditos=f.cleaned_data['validacreditos'],
#                                       validapromedio=f.cleaned_data['validapromedio'],
#                                       modeloevaluativo=modelo,
#                                       cupo=f.cleaned_data['cupo'] if 'cupo' in request.POST else 0)
#                     materia.save(request)
#                     if materia.rectora:
#                         materia.carrerascomunes = f.cleaned_data['carreras']
#                         materia.save(request)
#                     log(u'Adiciono materia en nivel: %s' % materia, request, "add")
#                     return JsonResponse({"result": "ok"})
#                 else:
#                      raise NameError('Error')
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
#
#         elif action == 'addmateriamalla':
#             try:
#                 nivel = Nivel.objects.get(pk=request.POST['nid'])
#                 f = MateriaNivelMalla(request.POST)
#                 if f.is_valid():
#                     listado = request.POST['seleccionados']
#                     materiasmalla = AsignaturaMalla.objects.filter(id__in=[int(x) for x in listado.split(',')])
#                     for materiamalla in materiasmalla:
#                         materia = Materia(asignatura=materiamalla.asignatura,
#                                           asignaturamalla=materiamalla,
#                                           nivel=nivel,
#                                           horas=materiamalla.horas,
#                                           horassemanales=int(materiamalla.horas / 16),
#                                           creditos=materiamalla.creditos,
#                                           identificacion=materiamalla.identificacion,
#                                           paralelo=f.cleaned_data['paralelo'],
#                                           inicio=nivel.inicio,
#                                           fin=nivel.fin,
#                                           cerrado=False,
#                                           rectora=materiamalla.rectora,
#                                           practicas=materiamalla.practicas,
#                                           tutoria=False,
#                                           grado=False,
#                                           validacreditos=True,
#                                           validapromedio=True,
#                                           modeloevaluativo=f.cleaned_data['modelo'],
#                                           cupo=CAPACIDAD_MATERIA_INICIAL if CUPO_POR_MATERIA else 0)
#                         materia.save(request)
#                         log(u'Adiciono materia en nivel: %s' % materia, request, "add")
#                     return JsonResponse({"result": "ok"})
#                 else:
#                     raise NameError('Error')
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
#
#         elif action == 'editmateria':
#             try:
#                 materia = Materia.objects.get(pk=request.POST['id'])
#                 f = MateriaNivel(request.POST)
#                 if f.is_valid():
#                     if not f.cleaned_data['practicas'] and materia.practicas and materia.profesormateria_set.filter(tipoprofesor__id=TIPO_DOCENTE_PRACTICA).exists():
#                         return JsonResponse({"result": "bad", "mensaje": u"Existen docentes de practica en la materia."})
#                     if not f.cleaned_data['practicas'] and materia.practicas and materia.practicapreprofesional_set.exists():
#                         return JsonResponse({"result": "bad", "mensaje": u"Existen practicas realizadas en la materia."})
#                     if Leccion.objects.filter(clase__materia=materia, fecha__lt=f.cleaned_data['inicio']).exists():
#                         return JsonResponse({"result": "bad", "mensaje": u"Existen clases impartidas antes de esta fecha."})
#                     if Leccion.objects.filter(clase__materia=materia, fecha__gt=f.cleaned_data['fin']).exists():
#                         return JsonResponse({"result": "bad", "mensaje": u"Existen clases impartidas despues de esta fecha."})
#                     if f.cleaned_data['inicio'] < materia.nivel.inicio or f.cleaned_data['inicio'] > materia.nivel.fin or f.cleaned_data['inicio'] > materia.fin:
#                         return JsonResponse({"result": "bad", "mensaje": u"Fecha inicio incorrecta."})
#                     if not f.cleaned_data['practicas'] and materia.practicapreprofesional_set.exists():
#                         return JsonResponse({"result": "bad", "mensaje": u"La materia ya tiene prácticas realizadas."})
#                     materia.horassemanales = int(f.cleaned_data['horassemanales'])
#                     if not MATRICULACION_LIBRE:
#                         materia.horas = f.cleaned_data['horas']
#                         materia.creditos = f.cleaned_data['creditos']
#                     if 'identificacion' in request.POST:
#                         materia.identificacion = f.cleaned_data['identificacion']
#                     materia.paralelo = f.cleaned_data['paralelo'] if 'paralelo' in request.POST else ''
#                     materia.inicio = f.cleaned_data['inicio']
#                     materia.alias = f.cleaned_data['alias']
#                     materia.fin = f.cleaned_data['fin']
#                     materia.validapromedio = f.cleaned_data['validapromedio']
#                     materia.validacreditos = f.cleaned_data['validacreditos']
#                     materia.rectora = f.cleaned_data['rectora']
#                     if materia.rectora:
#                         materia.carrerascomunes = f.cleaned_data['carreras']
#                     else:
#                         materia.carrerascomunes.clear()
#                     materia.practicas = f.cleaned_data['practicas']
#                     materia.save(request)
#                     if CUPO_POR_MATERIA:
#                         if f.cleaned_data['cupo'] < materia.cantidad_matriculas_materia():
#                             materia.cupo = materia.cantidad_matriculas_materia()
#                         else:
#                             materia.cupo = f.cleaned_data['cupo']
#                         materia.save(request)
#                     return JsonResponse({"result": "ok"})
#                 else:
#                      raise NameError('Error')
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
#
#         elif action == 'deletemateria':
#             try:
#                 materia = Materia.objects.get(pk=request.POST['id'])
#                 log(u'Elimino materia: %s' % materia, request, "del")
#                 if not materia.tiene_matriculas():
#                     materia.delete()
#                 return JsonResponse({"result": "ok"})
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})
#
#         elif action == 'addprofesor':
#             try:
#                 materia = Materia.objects.get(pk=request.POST['mid'])
#                 f = ProfesorMateriaForm(request.POST)
#                 if f.is_valid():
#                     inicio = f.cleaned_data['desde']
#                     fin = f.cleaned_data['hasta']
#                     idtipoprofesor = f.cleaned_data['tipoprofesor'].id
#                     if inicio < materia.inicio or fin > materia.fin:
#                         return JsonResponse({"result": "bad", "mensaje": u"Fechas incorrectas."})
#                     if materia.profesormateria_set.filter(profesor=f.cleaned_data['profesor']).exists():
#                         m = materia.profesormateria_set.filter(profesor=f.cleaned_data['profesor'])[0]
#                         if m.activo:
#                             return JsonResponse({"result": "bad", "mensaje": u"Ya el docente esta registrado la materia."})
#                         else:
#                             m.activo = True
#                             m.save(request)
#                     if f.cleaned_data['tipoprofesor'].id == TIPO_DOCENTE_TEORIA and materia.profesormateria_set.filter(tipoprofesor__id=TIPO_DOCENTE_TEORIA, activo=True).exists():
#                         return JsonResponse({"result": "bad", "mensaje": u"Ya existe un docente principal registrado la materia."})
#                     pm = ProfesorMateria(segmento=f.cleaned_data['segmento'],
#                                          materia=materia,
#                                          profesor=f.cleaned_data['profesor'],
#                                          principal=True if f.cleaned_data['tipoprofesor'].id == TIPO_DOCENTE_TEORIA else False,
#                                          tipoprofesor=f.cleaned_data['tipoprofesor'],
#                                          hora=f.cleaned_data['hora'],
#                                          desde=inicio,
#                                          hasta=fin)
#                     pm.save(request)
#                     if pm.principal:
#                         for op in pm.materia.profesormateria_set.filter(principal=True).exclude(id=pm.id):
#                             if pm.materia.nivel.distributivoaprobado:
#                                 op.activo = False
#                             else:
#                                 op.principal = False
#                             op.save(request)
#                     # pm.profesor.actualizar_distributivo_horas(pm.materia.nivel.periodo, idtipoprofesor)
#                     if VERIFICAR_CONFLICTO_DOCENTE:
#                         conflicto = conflicto_materias_seleccionadas(pm.profesor.materias_imparte_periodo(periodo))
#                         if conflicto:
#                             transaction.set_rollback(True)
#                             return JsonResponse({"result": "bad", "mensaje": conflicto})
#                     if materia.profesormateria_set.count() > 1:
#                         materia.practicas = True
#                         materia.save(request)
#                     # sirve para verificar que al ingresar en el distributivo no sobrepase el numero de horas segun el tiempo de dedicacion
#                     # distributivo=pm.profesor.distributivohoras(pm.materia.nivel.periodo)
#                     # if distributivo.sobrepasa_horas():
#                     #     transaction.set_rollback(True)
#                     #     return JsonResponse({"result": "bad", "mensaje": u"Limite de horas a sobrepasado."})
#                     log(u'Adiciono profesor de materia: %s' % pm, request, "add")
#                     return JsonResponse({"result": "ok"})
#                 else:
#                     raise NameError('Error')
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
#
#         elif action == 'editprofesor':
#             try:
#                 f = EditProfesorMateriaForm(request.POST)
#                 if f.is_valid():
#                     pm = ProfesorMateria.objects.get(pk=request.POST['id'])
#                     profesor = pm.profesor
#                     periodo = pm.materia.nivel.periodo
#                     idtipoprofesor = f.cleaned_data['tipoprofesor']
#                     if f.cleaned_data['tipoprofesor']:
#                         pm.tipoprofesor = f.cleaned_data['tipoprofesor']
#                     pm.desde = f.cleaned_data['desde']
#                     pm.hasta = f.cleaned_data['hasta']
#                     pm.hora = f.cleaned_data['hora']
#                     pm.save(request)
#                     # profesor.actualizar_distributivo_horas(periodo,idtipoprofesor)
#                     log(u'Modifico profesor de materia: %s' % pm, request, "del")
#                     return JsonResponse({"result": "ok"})
#                 else:
#                      raise NameError('Error')
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al Modificar los datos."})
#
#         elif action == 'delprofesor':
#             try:
#                 pm = ProfesorMateria.objects.get(pk=request.POST['id'])
#                 idtipoprofesor = pm.tipoprofesor_id
#                 profesor = pm.profesor
#                 periodo = pm.materia.nivel.periodo
#                 log(u'Elimino profesor de materia: %s' % pm, request, "del")
#                 if not pm.materia.nivel.distributivoaprobado:
#                     pm.delete()
#                 else:
#                     pm.activo = False
#                     pm.save(request)
#                 # profesor.actualizar_distributivo_horas(periodo, idtipoprofesor)
#                 return JsonResponse({"result": "ok"})
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})
#
#         elif action == 'updatefechainicio':
#             try:
#                 materia = Materia.objects.get(pk=request.POST['mid'])
#                 fechainicio = convertir_fecha(request.POST['fecha'])
#                 if fechainicio < materia.nivel.inicio or fechainicio > materia.nivel.fin or fechainicio > materia.fin:
#                     return JsonResponse({"result": "bad", "mensaje": u"Fecha inicio incorrecta."})
#                 if Leccion.objects.filter(clase__materia=materia, fecha__lt=fechainicio).exists():
#                     return JsonResponse({"result": "bad", "mensaje": u"Existen clases impartidas antes de esta fecha."})
#                 for pm in materia.profesormateria_set.all():
#                     pm.desde = fechainicio
#                     pm.save(request)
#                 materia.inicio = fechainicio
#                 materia.save(request)
#                 log(u'Modifico fecha inicio: %s' % materia, request, "edit")
#                 return JsonResponse({'result': 'ok', 'fecha': materia.inicio.strftime("%d-%m-%Y"), 'profesores': materia.profesores_materia().count()})
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({'result': 'bad'})
#
#         elif action == 'updatefechafin':
#             try:
#                 materia = Materia.objects.get(pk=request.POST['mid'])
#                 fechafin = convertir_fecha(request.POST['fecha'])
#                 if Leccion.objects.filter(clase__materia=materia, fecha__gt=fechafin).exists():
#                     return JsonResponse({"result": "bad", "mensaje": u"Existen clases impartidas despues de esta fecha."})
#                 for pm in materia.profesormateria_set.all():
#                     pm.hasta = fechafin
#                     pm.save(request)
#                 materia.fin = fechafin
#                 materia.fechafinasistencias = fechafin
#                 materia.save(request)
#                 for asig in materia.asignados_a_esta_materia():
#                     asig.save(request)
#                     asig.actualiza_estado()
#                     asig.actualiza_notafinal()
#                 log(u'Modifico fecha fin: %s' % materia, request, "edit")
#                 return JsonResponse({'result': 'ok', 'fecha': materia.fin.strftime("%d-%m-%Y"), 'profesores': materia.profesores_materia().count()})
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({'result': 'bad'})
#
#         elif action == 'updatecupomateria':
#             try:
#                 materia = Materia.objects.get(pk=request.POST['mid'])
#                 valor = int(request.POST['valor'])
#                 if valor < materia.cantidad_matriculas_materia():
#                     return JsonResponse({"result": "bad", "mensaje": u"No puede establecer un cupo menor a " + materia.cantidad_matriculas_materia().__str__()})
#                 cupoanterior = materia.cupo
#                 materia.cupo = valor
#                 materia.save(request)
#                 log(u'Adiciono cupo a materia: %s cupo anterior: %s cupo actual: %s' % (materia, str(cupoanterior), str(materia.cupo)),request, "add")
#                 return JsonResponse({'result': 'ok', 'valor': materia.cupo})
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({'result': 'bad'})
#
#         elif action == 'cambiaraula':
#             try:
#                 materia = Materia.objects.get(pk=request.POST['id'])
#                 f = CambiarAulaForm(request.POST)
#                 if f.is_valid():
#                     clases = materia.clase_set.filter(activo=True)
#                     for c in clases:
#                         c.aula = f.cleaned_data['aula']
#                         c.save(request)
#                     log(u'cambio alula: %s' % clases, request, "edit")
#                     return JsonResponse({"result": "ok"})
#                 else:
#                     raise NameError('Error')
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
#
#         elif action == 'cambiarmodelo':
#             try:
#                 materia = Materia.objects.get(pk=request.POST['id'])
#                 f = ListaModeloEvaluativoForm(request.POST)
#                 if f.is_valid():
#                     if materia.cerrado:
#                         return JsonResponse({"result": "bad", "mensaje": u"La materia se encuentra cerrada."})
#                     if materia.materiaasignada_set.filter(notafinal__gt=0).exists():
#                         return JsonResponse({"result": "bad", "mensaje": u"No se puede cambiar el modelo, existen calificaciones ingresadas."})
#                     materia.modeloevaluativo = f.cleaned_data['modelo']
#                     materia.save(request)
#                     evaluaciones = EvaluacionGenerica.objects.filter(materiaasignada__materia=materia)
#                     evaluaciones.delete()
#                     for maa in materia.asignados_a_esta_materia():
#                         maa.evaluacion()
#                         maa.notafinal = 0
#                         maa.save(request)
#                     if materia.cronogramaevaluacionmodelo_set.exists():
#                         cronograma = materia.cronogramaevaluacionmodelo_set.all()[0]
#                         cronograma.materias.remove(materia)
#                     log(u'Modifico modelo evaluativo: %s' % materia, request, "edit")
#                     return JsonResponse({"result": "ok"})
#                 else:
#                      raise NameError('Error')
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
#
#         elif action == 'vaciarcalificaciones':
#             try:
#                 materia = Materia.objects.get(pk=request.POST['id'])
#                 if materia.cerrado:
#                     return JsonResponse({"result": "bad", "mensaje": u"La materia se encuentra cerrada."})
#                 if (datetime(materia.inicio.year, materia.inicio.month, materia.inicio.day, 0, 0, 0) + timedelta(days=15)).date() <= datetime.now().date():
#                     return JsonResponse({"result": "bad", "mensaje": u"No se pueden eliminar las calificaciones."})
#                 EvaluacionGenerica.objects.filter(materiaasignada__materia=materia).update(valor=0)
#                 for asignado in materia.asignados_a_esta_materia():
#                     if not asignado.convalidada() and not asignado.homologada():
#                         asignado.notafinal = 0
#                         asignado.save(request)
#                 log(u'Elimino calificaciones de materia: %s' % materia, request, "edit")
#                 return JsonResponse({"result": "ok"})
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
#
#         elif action == 'diasacalificar':
#             try:
#                 materia = Materia.objects.get(pk=request.POST['id'])
#                 form = CalificacionDiaForm(request.POST)
#                 if form.is_valid():
#                     materia.usaperiodocalificaciones = form.cleaned_data['usaperiodocalificaciones']
#                     materia.diasactivacioncalificaciones = form.cleaned_data['diasactivacioncalificaciones'] if not form.cleaned_data['usaperiodocalificaciones'] else 1
#                     materia.save(request)
#                     log(u'Cambio en fecha de calificaciones de materia: %s' % materia, request, "edit")
#                     return JsonResponse({"result": "ok"})
#                 else:
#                      raise NameError('Error')
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
#
#         elif action == 'diasaevaluar':
#             try:
#                 materia = Materia.objects.get(pk=request.POST['id'])
#                 form = EvaluacionDiaForm(request.POST)
#                 if form.is_valid():
#                     materia.usaperiodoevaluacion = form.cleaned_data['usaperiodoevaluacion']
#                     materia.diasactivacion = form.cleaned_data['diasactivacion'] if not form.cleaned_data['usaperiodoevaluacion'] else 1
#                     materia.save(request)
#                     log(u'Cambio en fecha de evaluaciones de materia: %s' % materia, request, "edit")
#                     return JsonResponse({"result": "ok"})
#                 else:
#                     raise NameError('Error')
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
#
#         elif action == 'fechaasistencias':
#             try:
#                 materia = Materia.objects.get(pk=request.POST['id'])
#                 form = FechafinAsistenciasForm(request.POST)
#                 if form.is_valid():
#                     materia.fechafinasistencias = form.cleaned_data['fecha']
#                     materia.save(request)
#                     materia.recalcularmateria()
#                     log(u'Cambio fecha fin de asistencias de materia: %s' % materia, request, "edit")
#                     return JsonResponse({"result": "ok"})
#                 else:
#                     raise NameError('Error')
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
#
#         elif action == 'precierrem':
#             try:
#                 nivel = Nivel.objects.get(pk=request.POST['nid'])
#                 materias = []
#                 for matricula in nivel.matricula_set.all():
#                     mo = {'nombre': unicode(matricula.inscripcion.persona.nombre_completo()), 'id': matricula.id}
#                     materias.append(mo)
#                 return JsonResponse({"result": "ok", "cantidad": len(materias), "materias": materias})
#             except Exception as ex:
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al generar lista de precierre"})
#
#         elif action == 'bloqueohorarios':
#             try:
#                 nivel = Nivel.objects.get(pk=request.POST['id'])
#                 extension = nivel.extension()
#                 extension.visible = True if request.POST['val'] == 'y' else False
#                 extension.save(request)
#                 return JsonResponse({"result": "ok"})
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad"})
#
#         elif action == 'bloqueocupos':
#             try:
#                 nivel = Nivel.objects.get(pk=request.POST['id'])
#                 extension = nivel.extension()
#                 extension.puedematricular = True if request.POST['val'] == 'y' else False
#                 extension.save(request)
#                 return JsonResponse({"result": "ok"})
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad"})
#
#         elif action == 'bloqueoprofesor':
#             try:
#                 nivel = Nivel.objects.get(pk=request.POST['id'])
#                 extension = nivel.extension()
#                 extension.modificardocente = True if request.POST['val'] == 'y' else False
#                 extension.save(request)
#                 return JsonResponse({"result": "ok"})
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad"})
#
#         elif action == 'cierrema':
#             try:
#                 ma = MateriaAsignada.objects.get(pk=request.POST['maid'])
#                 ma.cierre_materia_asignada()
#                 return JsonResponse({"result": "ok"})
#             except Exception as ex:
#                 return JsonResponse({"result": "bad"})
#
#         elif action == 'cierremag':
#             try:
#                 matricula = Matricula.objects.get(pk=request.POST['maid'])
#                 matricula.cerrada = True
#                 matricula.save(request)
#                 return JsonResponse({"result": "ok"})
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad"})
#
#         elif action == 'cierren':
#             try:
#                 nivel = Nivel.objects.get(pk=request.POST['nid'])
#                 nivel.cerrado = True
#                 nivel.fechacierre = datetime.now()
#                 nivel.save(request)
#                 return JsonResponse({"result": "ok"})
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad"})
#
#         elif action == 'infoasignatura':
#             try:
#                 if MATRICULACION_LIBRE:
#                     asignaturamalla = AsignaturaMalla.objects.get(pk=request.POST['aid'])
#                     return JsonResponse({'result': 'ok', 'creditos': asignaturamalla.creditos, 'codigo': asignaturamalla.identificacion, 'horas': asignaturamalla.horas, 'horassemanales': int(asignaturamalla.horas / 16), 'malla': 'si'})
#                 else:
#                     asignatura = Asignatura.objects.get(pk=request.POST['aid'])
#                     return JsonResponse({'result': 'ok', 'creditos': asignatura.creditos, 'codigo': asignatura.codigo, 'horas': asignatura.creditos * 16, 'horassemanales': 0, 'malla': 'si'})
#             except Exception as ex:
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
#
#         if action == 'alumnospractica':
#             try:
#                 profesormateria = ProfesorMateria.objects.get(pk=request.POST['id'])
#                 seleccionados = MateriaAsignada.objects.filter(id__in=[int(x) for x in request.POST['listamaterias'].split(',')])
#                 for materiaasignada in profesormateria.materia.asignados_a_esta_materia():
#                     if materiaasignada.alumnospracticamateria_set.exists():
#                         participantepractica = materiaasignada.alumnospracticamateria_set.all()[0]
#                         if materiaasignada in seleccionados:
#                             participantepractica.profesormateria = profesormateria
#                             participantepractica.save(request)
#                         else:
#                             if participantepractica.profesormateria == profesormateria:
#                                 participantepractica.delete()
#                     else:
#                         if materiaasignada in seleccionados:
#                             participantepractica = AlumnosPracticaMateria(materiaasignada=materiaasignada,
#                                                                           profesormateria=profesormateria)
#                             participantepractica.save(request)
#                 log(u'Establecio alumnos de practica: %s' % profesormateria.materia, request, "add")
#                 return JsonResponse({"result": "ok"})
#             except Exception as ex:
#                 transaction.set_rollback(True)
#                 return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
#
#         return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
#     else:
#         if 'action' in request.GET:
#             action = request.GET['action']
#
#             if action == 'add':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_modificar_niveles')
#                     data['title'] = u'Adicionar nivel académico'
#                     periodo = request.session['periodo']
#                     coordinacion = Coordinacion.objects.get(pk=request.GET['coordinacion'])
#                     form = NivelForm(initial={'coordinacion': coordinacion,
#                                               'aplicabecas': True,
#                                               'paralelo': periodo.nombre,
#                                               'inicio': periodo.inicio,
#                                               'fin': periodo.fin,
#                                               'fechatopematricula': periodo.fin,
#                                               'fechatopematriculaext': periodo.fin,
#                                               'fechatopematriculaesp': periodo.fin})
#                     form.nivellibrecoordinacion()
#                     data['formulario'] = 'nivellibreform'
#                     data['coordinacion'] = coordinacion
#                     data['form'] = form
#                     data['periodo'] = periodo
#                     return render(request, "niveles/add.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'abrirn':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_modificar_niveles')
#                     n = Nivel.objects.get(pk=request.GET['nid'])
#                     n.cerrado = False
#                     n.save(request)
#                     log(u'Abrio nivel: %s' % n, request, "edit")
#                     return HttpResponseRedirect("/niveles?action=materias&id=" + request.GET['nid'])
#                 except Exception as ex:
#                     transaction.set_rollback(True)
#                     pass
#
#             elif action == 'edit':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_modificar_niveles')
#                     data['title'] = u'Editar nivel académico'
#                     data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['id'])
#                     form = NivelFormEdit(initial={'paralelo': nivel.paralelo,
#                                                   'inicio': nivel.inicio,
#                                                   'fin': nivel.fin,
#                                                   'fechatopematricula': nivel.fechatopematricula,
#                                                   'capacidad': nivel.capacidadmatricula,
#                                                   'fechatopematriculaext': nivel.fechatopematriculaex,
#                                                   'fechatopematriculaesp': nivel.fechatopematriculaes})
#                     if MATRICULACION_LIBRE:
#                         form.nivellibrecoordinacion()
#                     data['form'] = form
#                     return render(request, "niveles/edit.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'copy':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_modificar_niveles')
#                     data['title'] = u'Duplicar nivel'
#                     data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['id'])
#                     data['form'] = NivelFormEdit(initial={'paralelo': nivel.paralelo,
#                                                           'inicio': nivel.inicio,
#                                                           'fin': nivel.fin,
#                                                           'fechatopematricula': nivel.fechatopematricula,
#                                                           'fechatopematriculaesp': nivel.fechatopematriculaes,
#                                                           'fechatopematriculaext': nivel.fechatopematriculaex})
#                     return render(request, "niveles/copy.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'copypagos':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_modificar_niveles')
#                     data['title'] = u'Copia cronograma de pagos a otro nivel'
#                     data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['id'])
#                     form = OtroNivelForm()
#                     form.sin_minivel(nivel)
#                     data['form'] = form
#                     return render(request, "niveles/copypagos.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'del':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_modificar_niveles')
#                     data['title'] = u'Borrar nivel académico'
#                     data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['id'])
#                     return render(request, "niveles/del.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'vaciarcalificaciones':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_eliminar_calificaciones_materia')
#                     data['title'] = u'Vaciar calificaciones'
#                     if 'mallaid' in request.GET:
#                         data['mallaid'] = mallaid = request.GET['mallaid']
#                     if 'nivelmallaid' in request.GET:
#                         data['nivelmallaid'] = mallaid = request.GET['nivelmallaid']
#                     data['materia'] = Materia.objects.get(pk=request.GET['id'])
#                     return render(request, "niveles/vaciarcalificaciones.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'diasacalificar':
#                 try:
#                     # puede_realizar_accion(request, 'sga.puede_modificar_materias')
#                     data['title'] = u'Dias para calificar la materia'
#                     if 'mallaid' in request.GET:
#                         data['mallaid'] = mallaid = request.GET['mallaid']
#                     if 'nivelmallaid' in request.GET:
#                         data['nivelmallaid'] = mallaid = request.GET['nivelmallaid']
#                     data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
#                     data['form'] = CalificacionDiaForm(initial={'usaperiodocalificaciones': materia.usaperiodocalificaciones,
#                                                                 'diasactivacioncalificaciones': materia.diasactivacioncalificaciones})
#                     return render(request, "niveles/diasacalificar.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'fechaasistencias':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_modificar_materias')
#                     data['title'] = u'Fechas a tomar en cuenta para asistencias'
#                     if 'mallaid' in request.GET:
#                         data['mallaid'] = mallaid = request.GET['mallaid']
#                     if 'nivelmallaid' in request.GET:
#                         data['nivelmallaid'] = mallaid = request.GET['nivelmallaid']
#                     data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
#                     data['form'] = FechafinAsistenciasForm(initial={'fecha': materia.fechafinasistencias})
#                     return render(request, "niveles/fechafinasistencias.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'diasaevaluar':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_modificar_autorizacion_evaluacion')
#                     data['title'] = u'Dias para evaluar la materia'
#                     if 'mallaid' in request.GET:
#                         data['mallaid'] = mallaid = request.GET['mallaid']
#                     if 'nivelmallaid' in request.GET:
#                         data['nivelmallaid'] = mallaid = request.GET['nivelmallaid']
#                     data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
#                     data['form'] = EvaluacionDiaForm(initial={'usaperiodoevaluacion': materia.usaperiodoevaluacion,
#                                                               'diasactivacion': materia.diasactivacion})
#                     return render(request, "niveles/diasaevaluar.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'abrirm':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_abrir_materia')
#                     mallaid = None
#                     nivelmallaid = None
#                     if 'mallaid' in request.GET:
#                         data['mallaid'] = mallaid = request.GET['mallaid']
#                     if 'nivelmallaid' in request.GET:
#                         data['nivelmallaid'] = nivelmallaid = request.GET['nivelmallaid']
#                     materia = Materia.objects.get(pk=request.GET['id'])
#                     materia.cerrado = False
#                     materia.save(request)
#                     for asig in materia.asignados_a_esta_materia():
#                         asig.cerrado = True
#                         asig.save(request)
#                     log(u'Abrio  materia: %s' % materia, request, "del")
#                     return HttpResponseRedirect("/niveles?action=materias&id=" + str(materia.nivel.id) + (("&mallaid=" + mallaid) if mallaid else '') + (("&nivelmallaid=" + nivelmallaid) if nivelmallaid else ''))
#                 except Exception as ex:
#                     transaction.set_rollback(True)
#
#             elif action == 'cerrarm':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_cerrar_materia')
#                     mallaid = None
#                     nivelmallaid = None
#                     if 'mallaid' in request.GET:
#                         data['mallaid'] = mallaid = request.GET['mallaid']
#                     if 'nivelmallaid' in request.GET:
#                         data['nivelmallaid'] = nivelmallaid = request.GET['nivelmallaid']
#                     materia = Materia.objects.get(pk=request.GET['id'])
#                     materia.cerrado = True
#                     materia.fechacierre = datetime.now().date()
#                     materia.save(request)
#                     for asig in materia.asignados_a_esta_materia():
#                         asig.cerrado = True
#                         asig.save(request)
#                         asig.actualiza_estado()
#                     for asig in materia.asignados_a_esta_materia():
#                         asig.cierre_materia_asignada()
#                     materia.materiaasignada_set.all()[0].cierre_materia_asignada_pre()
#                     return HttpResponseRedirect("/niveles?action=materias&id=" + str(materia.nivel.id) + (("&mallaid=" + mallaid) if mallaid else '') + (("&nivelmallaid=" + nivelmallaid) if nivelmallaid else ''))
#                 except Exception as ex:
#                     transaction.set_rollback(True)
#                     pass
#
#             elif action == 'tomandom':
#                 try:
#                     data['title'] = u'Tomando la materia'
#                     data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
#                     data['materiasasignadas'] = materia.materiaasignada_set.filter(matricula__estado_matricula__in=[2,3]).order_by('matricula__inscripcion__persona')
#                     data['nivel'] = materia.nivel
#                     if 'mallaid' in request.GET:
#                         data['mallaid'] = request.GET['mallaid']
#                     if 'nivelmallaid' in request.GET:
#                         data['nivelmallaid'] = request.GET['nivelmallaid']
#                     return render(request, "niveles/tomandom.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'materias':
#                 try:
#                     data['title'] = u'Materias del nivel académico'
#                     data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['id'])
#                     data['reporte_0'] = obtener_reporte('mate_cronogramaperiodo')
#                     data['reporte_1'] = obtener_reporte('clases_consolidado')
#                     data['reporte_2'] = obtener_reporte('acta_notas')
#                     data['reporte_3'] = obtener_reporte('lista_alumnos_matriculados_materia')
#                     data['reporte_4'] = obtener_reporte('listado_asistencia_dias')
#                     data['reporte_5'] = obtener_reporte('lista_control_calificaciones')
#                     data['reporte_6'] = obtener_reporte('control_academico')
#                     data['reporte_7'] = obtener_reporte('acta_notas_parcial')
#                     data['reporte_8'] = obtener_reporte('mate_cronogramaperiodo_carrera')
#                     data['reporte_9'] = obtener_reporte('horario_carrera')
#                     data['reporte_10'] = obtener_reporte('horario_carrera_nivelmalla')
#                     data['reporte_11'] = obtener_reporte('total_matriculados_asignaturas')
#                     carreras = persona.mis_carreras()
#                     if MATRICULACION_LIBRE:
#                         carreras = carreras.filter(id__in=nivel.coordinacion().carrera.all())
#                         mallas = Malla.objects.filter(carrera__in=carreras).distinct()
#                         malla = None
#                         nivelmalla = None
#                         if 'mallaid' in request.GET:
#                             malla = mallas.get(pk=int(request.GET['mallaid']))
#                         else:
#                             if mallas.exists():
#                                 malla = mallas[0]
#                         data['malla'] = malla
#                         data['mallaid'] = malla.id if malla else 0
#                         if 'nivelmallaid' in request.GET and int(request.GET['nivelmallaid']) > 0:
#                             nivelmalla = NivelMalla.objects.get(pk=int(request.GET['nivelmallaid']))
#                             data['nivelmalla'] = nivelmalla
#                             data['nivelmallaid'] = nivelmalla.id if nivelmalla else ""
#                         if nivelmalla:
#                             materias = nivel.materia_set.filter(asignaturamalla__malla=malla, asignaturamalla__nivelmalla=nivelmalla).order_by('asignaturamalla__nivelmalla', 'asignatura__nombre', 'inicio', 'identificacion', 'id')
#                         else:
#                             materias = nivel.materia_set.filter(asignaturamalla__malla=malla).order_by('asignaturamalla__nivelmalla', 'asignatura__nombre', 'inicio', 'identificacion', 'id')
#                         data['materias'] = materias
#                         data['mallas'] = mallas
#                     else:
#                         data['materias'] = nivel.materia_set.all().order_by('asignatura__nombre', 'inicio', 'identificacion', 'id')
#                     data['bloqueado'] = nivel.bloqueado()
#                     data['nivelesmalla'] = NivelMalla.objects.all()
#                     data['nobloqueadocupos'] = nivel.extension().puedematricular
#                     data['nobloqueadodocente'] = nivel.extension().modificardocente if MATRICULACION_LIBRE else True
#                     data['matriculacion_libre'] = MATRICULACION_LIBRE
#                     data['cupo_por_materia'] = CUPO_POR_MATERIA
#                     data['usa_evaluacion_integral'] = USA_EVALUACION_INTEGRAL
#                     return render(request, "niveles/materias.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'pagos':
#                 try:
#                     data['title'] = u'Cronograma de pagos del nivel académico'
#                     data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['id'])
#                     data['pagos'] = nivel.pagonivel_set.all()
#                     return render(request, "niveles/pagos.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'addpagos':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_modificar_pagos_nivel')
#                     data['title'] = u'Adicionar cronograma de pagos al nivel académico'
#                     data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['id'])
#                     data['form'] = PagoNivelForm()
#                     data['tipo_cuota_rubro'] = TIPO_CUOTA_RUBRO
#                     return render(request, "niveles/addpagos.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'cambiarmodelo':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_modificar_modelo_evaluativo_materia')
#                     data['title'] = u'Cambiar modelo evaluativo'
#                     data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
#                     form = ListaModeloEvaluativoForm()
#                     form.excluir_modeloactual(materia.modeloevaluativo)
#                     data['form'] = form
#                     data['nivel'] = materia.nivel
#                     if 'mallaid' in request.GET:
#                         data['mallaid'] = mallaid = request.GET['mallaid']
#                     if 'nivelmallaid' in request.GET:
#                         data['nivelmallaid'] = request.GET['nivelmallaid']
#                     return render(request, "niveles/cambiarmodelo.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'dividir':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_modificar_materias')
#                     data['title'] = u'Dividir matriculados en una materia'
#                     data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
#                     form = MateriaDividirForm()
#                     form.desde_materia(materia)
#                     data['form'] = form
#                     if 'mallaid' in request.GET:
#                         data['mallaid'] = mallaid = request.GET['mallaid']
#                     if 'nivelmallaid' in request.GET:
#                         data['nivelmallaid'] = request.GET['nivelmallaid']
#                     return render(request, "niveles/dividir.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'editpagos':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_modificar_niveles')
#                     data['title'] = u'Editar cronograma de pagos del nivel'
#                     data['pagonivel'] = pagonivel = PagoNivel.objects.get(pk=request.GET['id'])
#                     data['nivel'] = pagonivel.nivel
#                     form = PagoNivelForm(initial={'fecha': pagonivel.fecha,
#                                                   'tipo': pagonivel.tipo,
#                                                   'cuota': pagonivel.cuota,
#                                                   'valor': pagonivel.valor})
#                     form.editar()
#                     data['form'] = form
#                     return render(request, "niveles/editpagos.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'delpagos':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_modificar_niveles')
#                     pagonivel = PagoNivel.objects.get(pk=request.GET['id'])
#                     nivel = pagonivel.nivel
#                     pagonivel.delete()
#                     return HttpResponseRedirect("/niveles?action=pagos&id=" + str(nivel.id))
#                 except Exception as ex:
#                     transaction.set_rollback(True)
#                     pass
#
#             elif action == 'editmateria':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_modificar_materias')
#                     data['title'] = u'Editar materia de nivel académico'
#                     data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
#                     form = MateriaNivel(initial={'asignatura': materia.asignatura,
#                                                  'asignaturamalla': materia.asignaturamalla,
#                                                  'horas': materia.horas,
#                                                  'horassemanales': materia.horassemanales,
#                                                  'modelo': materia.modeloevaluativo,
#                                                  'creditos': materia.creditos,
#                                                  'cupo': materia.cupo,
#                                                  'identificacion': materia.identificacion,
#                                                  'alias': materia.alias,
#                                                  'paralelo': materia.paralelo,
#                                                  'tutoria': materia.tutoria,
#                                                  'practicas': materia.practicas,
#                                                  'validacreditos': materia.validacreditos,
#                                                  'validapromedio': materia.validapromedio,
#                                                  'rectora': materia.rectora,
#                                                  'carreras': materia.carrerascomunes.all(),
#                                                  'inicio': materia.inicio,
#                                                  'fin': materia.fin})
#                     form.sin_modificarla(materia.nivel, materia.asignaturamalla)
#                     if 'mallaid' in request.GET:
#                         data['mallaid'] = mallaid = request.GET['mallaid']
#                     if 'nivelmallaid' in request.GET:
#                         data['nivelmallaid'] = nivelmallaid = request.GET['nivelmallaid']
#                     data['form'] = form
#                     return render(request, "niveles/editmateria.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'addmateria':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_modificar_materias')
#                     data['title'] = u'Adicionar materia a nivel académico'
#                     data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['id'])
#                     form = MateriaNivel(initial={'inicio': nivel.inicio,
#                                                  'fin': nivel.fin,
#                                                  'creditos': 0,
#                                                  'horassemanales': 0,
#                                                  'horas': 0,
#                                                  'cupo': CAPACIDAD_MATERIA_INICIAL})
#                     mallaid = None
#                     nivelmallaid = None
#                     if 'mallaid' in request.GET:
#                         data['mallaid'] = mallaid = request.GET['mallaid']
#                     if 'nivelmallaid' in request.GET:
#                         data['nivelmallaid'] = nivelmallaid = request.GET['nivelmallaid']
#                     if MATRICULACION_LIBRE:
#                         form.matriculacion_libre(mallaid, nivelmallaid)
#                     else:
#                         form.matriculacion_regular()
#                     data['form'] = form
#                     return render(request, "niveles/addmateria.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'materiasmalla':
#                 try:
#                     malla = Malla.objects.get(pk=request.GET['mid'])
#                     data['materiasmalla'] = asignaturasmalla = malla.asignaturamalla_set.all().order_by('nivelmalla')
#                     segmento = render(request, "niveles/materiasmalla.html", data)
#                     return JsonResponse({"result": "ok", "segmento": segmento.content})
#                 except Exception as ex:
#                     return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
#
#             elif action == 'addmateriamalla':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_modificar_materias')
#                     data['title'] = u'Adicionar materia a nivel académico de una malla'
#                     data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['id'])
#                     if 'mallaid' not in request.GET:
#                         return HttpResponseRedirect('/niveles?action=materias&id=' + request.GET['id'])
#                     data['mallaid'] = mallaid = request.GET['mallaid']
#                     if 'nivelmallaid' in request.GET:
#                         data['nivelmallaid'] = nivelmallaid = request.GET['nivelmallaid']
#                     form = MateriaNivelMalla(initial={'malla': mallaid})
#                     form.mallas(mallaid)
#                     data['form'] = form
#                     return render(request, "niveles/addmateriamalla.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'deletemateria':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_modificar_materias')
#                     data['title'] = u'Borrar materia de nivel académico'
#                     data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
#                     data['nivel'] = materia.nivel
#                     if 'mallaid' in request.GET:
#                         data['mallaid'] = request.GET['mallaid']
#                     if 'nivelmallaid' in request.GET:
#                         data['nivelmallaid'] = request.GET['nivelmallaid']
#                     return render(request, "niveles/deletemateria.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'delprofesor':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_modificar_materias')
#                     data['title'] = u'Eliminar profesor de materia'
#                     data['profesormateria'] = profesormateria = ProfesorMateria.objects.get(pk=request.GET['id'])
#                     data['nivel'] = profesormateria.materia.nivel
#                     if 'mallaid' in request.GET:
#                         data['mallaid'] = request.GET['mallaid']
#                     if 'nivelmallaid' in request.GET:
#                         data['nivelmallaid'] = request.GET['nivelmallaid']
#                     return render(request, "niveles/delprofesor.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'alumnospractica':
#                 try:
#                     data['title'] = u'Alumnos de practica'
#                     data['profesormateria'] = profesormateria = ProfesorMateria.objects.get(pk=request.GET['id'])
#                     data['materiasasignadas'] = profesormateria.materia.materiaasignada_set.all().order_by('matricula__inscripcion__persona')
#                     data['nivel'] = profesormateria.materia.nivel
#                     if 'mallaid' in request.GET:
#                         data['mallaid'] = request.GET['mallaid']
#                     if 'nivelmallaid' in request.GET:
#                         data['nivelmallaid'] = request.GET['nivelmallaid']
#                     return render(request, "niveles/alumnospractica.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'aprobar':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_autorizar_distributivo')
#                     data['title'] = u'Aprobar distributivo de nivel académico'
#                     data['nivel'] = Nivel.objects.get(pk=request.GET['id'])
#                     return render(request, "niveles/aprobar.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'cambiaraula':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_modificar_aula_horario')
#                     data['title'] = u'Cambiar aula de materia en el horario'
#                     data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
#                     form = CambiarAulaForm()
#                     form.excluir_aulas_actuales(materia.nivel, materia.nivel.coordinacion())
#                     if 'mallaid' in request.GET:
#                         data['mallaid'] = request.GET['mallaid']
#                     if 'nivelmallaid' in request.GET:
#                         data['nivelmallaid'] = request.GET['nivelmallaid']
#                     data['form'] = form
#                     data['nivel'] = materia.nivel
#                     return render(request, "niveles/cambiaraula.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'addprofesor':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_modificar_profesor_materia')
#                     data['title'] = u'Adicionar profesor a materia de nivel académico'
#                     data['materia'] = materia = Materia.objects.get(pk=request.GET['mid'])
#                     data['form'] = ProfesorMateriaForm(initial={'segmento': 'MATERIA',
#                                                                 'desde': materia.inicio,
#                                                                 'hasta': materia.fin,
#                                                                 'hora': materia.horassemanales })
#                     if 'mallaid' in request.GET:
#                         data['mallaid'] = request.GET['mallaid']
#                     if 'nivelmallaid' in request.GET:
#                         data['nivelmallaid'] = request.GET['nivelmallaid']
#                     return render(request, "niveles/addprofesor.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'editprofesor':
#                 try:
#                     puede_realizar_accion(request, 'sga.puede_modificar_profesor_materia')
#                     data['title'] = u'Editar profesor a materia de nivel académico'
#                     profesormateria = ProfesorMateria.objects.get(pk=request.GET['id'])
#                     data['materia'] = profesormateria.materia
#                     data['tipoprofesor'] = profesormateria.tipoprofesor
#                     data['profesor'] = profesormateria.profesor
#                     data['segmento'] = profesormateria.segmento
#                     data['desde'] = profesormateria.desde
#                     data['hasta'] = profesormateria.hasta
#                     data['hora'] = profesormateria.hora
#                     data['id'] = pk = request.GET['id']
#                     form = EditProfesorMateriaForm(initial={'segmento': profesormateria.segmento,
#                                                             'desde': profesormateria.desde,
#                                                             'hasta': profesormateria.hasta,
#                                                             'materia': profesormateria.materia,
#                                                             'tipoprofesor': profesormateria.tipoprofesor,
#                                                             'profesor': profesormateria.profesor,
#                                                             'hora': profesormateria.hora})
#
#                     if puede_realizar_accion_afirmativo(request, 'sga.puede_modificar_tipoprofesor'):
#                         form.editar_tipo()
#                     else:
#                         form.editar()
#                     if 'mallaid' in request.GET:
#                         data['mallaid'] = request.GET['mallaid']
#                     if 'nivelmallaid' in request.GET:
#                         data['nivelmallaid'] = request.GET['nivelmallaid']
#                     data['form'] = form
#                     return render(request, "niveles/editprofesor.html", data)
#                 except Exception as ex:
#                     pass
#
#             elif action == 'reporte':
#                 try:
#                     periodo = request.GET['periodo']
#                     coordinacion = request.GET['coordinacion']
#                     __author__ = 'Unemi'
#                     style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
#                     style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
#                     style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
#                     title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
#                     style1 = easyxf(num_format_str='D-MMM-YY')
#                     font_style = XFStyle()
#                     font_style.font.bold = True
#                     font_style2 = XFStyle()
#                     font_style2.font.bold = False
#                     wb = Workbook(encoding='utf-8')
#                     ws = wb.add_sheet('exp_xls_post_part')
#                     ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
#                     response = HttpResponse(content_type="application/ms-excel")
#                     response[
#                         'Content-Disposition'] = 'attachment; filename=exp_xls_post_part_' + random.randint(
#                         1, 10000).__str__() + '.xls'
#
#                     columns = [
#                         (u"PERIODO", 6000),
#                         (u"FACULTAD", 6000),
#                         (u"CARRERA", 6000),
#                         (u"NIVEL", 6000),
#                         (u"PARALELO", 6000),
#                         (u"DOCENTE", 6000),
#                         (u"ASIGNATURA", 6000),
#                         (u"PROMEDIO PARCIAL 1", 6000),
#                         (u"PROMEDIO PARCIAL 1 CON NOTA", 6000),
#                         (u"PROMEDIO PARCIAL 2", 6000),
#                         (u"PROMEDIO PARCIAL 2 CON NOTA", 6000),
#                         (u"PROMEDIO NOTA FINAL", 6000),
#                         (u"PROMEDIO NOTA FINAL CON NOTA", 6000),
#                     ]
#                     row_num = 3
#                     for col_num in range(len(columns)):
#                         ws.write(row_num, col_num, columns[col_num][0], font_style)
#                         ws.col(col_num).width = columns[col_num][1]
#                     cursor = connection.cursor()
#                     sql = "SELECT DISTINCT sga_periodo.nombre AS Periodo, sga_coordinacion.nombre AS Facultad, sga_carrera.nombre AS Carrera, " \
#                           " sga_nivelmalla.nombre as Nivel, sga_materia.paralelo as Paralelo, (sga_persona.apellido1 || ' ' || sga_persona.apellido2 || ' ' || sga_persona.nombres) AS Docente, " \
#                           " sga_asignatura.nombre AS Asignatura, (select round(avg(valor),2) from public.sga_materiaasignada sga_materiaasignada, public.sga_matricula sga_matricula , public.sga_evaluaciongenerica sga_evaluaciongenerica, public.sga_detallemodeloevaluativo sga_detallemodeloevaluativo where sga_materiaasignada.matricula_id=sga_matricula.id and sga_matricula.estado_matricula in (2,3) " \
#                           " and sga_materiaasignada.materia_id=sga_materia.id and sga_evaluaciongenerica.materiaasignada_id=sga_materiaasignada.id and sga_detallemodeloevaluativo.id=sga_evaluaciongenerica.detallemodeloevaluativo_id and sga_detallemodeloevaluativo.id in (14,4)) as P1COMPLETO, " \
#                           " (select round(avg(valor),2) from public.sga_materiaasignada sga_materiaasignada, public.sga_matricula sga_matricula ,public.sga_evaluaciongenerica sga_evaluaciongenerica, public.sga_detallemodeloevaluativo sga_detallemodeloevaluativo where sga_materiaasignada.matricula_id=sga_matricula.id and sga_matricula.estado_matricula in (2,3) and sga_materiaasignada.materia_id=sga_materia.id " \
#                           " and sga_evaluaciongenerica.materiaasignada_id=sga_materiaasignada.id and sga_detallemodeloevaluativo.id=sga_evaluaciongenerica.detallemodeloevaluativo_id and sga_detallemodeloevaluativo.id in (14,4) and sga_materiaasignada.notafinal>0) as P1CONNOTA, " \
#                           " (select round(avg(valor),2) from public.sga_materiaasignada sga_materiaasignada,  public.sga_matricula sga_matricula, public.sga_evaluaciongenerica sga_evaluaciongenerica, public.sga_detallemodeloevaluativo sga_detallemodeloevaluativo where sga_materiaasignada.matricula_id=sga_matricula.id and sga_matricula.estado_matricula in (2,3) and sga_materiaasignada.materia_id=sga_materia.id " \
#                           " and sga_evaluaciongenerica.materiaasignada_id=sga_materiaasignada.id and sga_detallemodeloevaluativo.id=sga_evaluaciongenerica.detallemodeloevaluativo_id and sga_detallemodeloevaluativo.nombre='P2') as P2COMPLETO, " \
#                           " (select round(avg(valor),2) from public.sga_materiaasignada sga_materiaasignada, public.sga_matricula sga_matricula ,public.sga_evaluaciongenerica sga_evaluaciongenerica, public.sga_detallemodeloevaluativo sga_detallemodeloevaluativo where sga_materiaasignada.matricula_id=sga_matricula.id and sga_matricula.estado_matricula in (2,3) and sga_materiaasignada.materia_id=sga_materia.id " \
#                           " and sga_evaluaciongenerica.materiaasignada_id=sga_materiaasignada.id and sga_detallemodeloevaluativo.id=sga_evaluaciongenerica.detallemodeloevaluativo_id and sga_detallemodeloevaluativo.nombre='P2'  and sga_materiaasignada.notafinal>0) as P2CONNOTA, " \
#                           " (select round(avg(m1.notafinal),2) from sga_materiaasignada m1, sga_matricula mat where m1.matricula_id=mat.id and mat.estado_matricula in (2,3) and m1.materia_id=sga_materia.id and m1.notafinal>0) as Nota_FinalCONNOTA, " \
#                           " (select round(avg(m1.notafinal),2) from sga_materiaasignada m1, sga_matricula mat where m1.matricula_id=mat.id and mat.estado_matricula in (2,3) and m1.materia_id=sga_materia.id) as Nota_FinalCOMPLETO FROM public.sga_profesor sga_profesor RIGHT OUTER JOIN public.sga_profesormateria sga_profesormateria ON sga_profesor.id = sga_profesormateria.profesor_id inner JOIN public.sga_persona sga_persona ON sga_profesor.persona_id = sga_persona.id inner JOIN public.sga_materia sga_materia ON sga_profesormateria.materia_id = sga_materia.id inner JOIN public.sga_nivel sga_nivel ON sga_materia.nivel_id = sga_nivel.id inner JOIN public.sga_asignatura sga_asignatura ON sga_materia.asignatura_id = sga_asignatura.id inner JOIN public.sga_asignaturamalla sga_asignaturamalla ON sga_materia.asignaturamalla_id = sga_asignaturamalla.id inner join public.sga_nivelmalla sga_nivelmalla ON sga_nivelmalla.id=sga_asignaturamalla.nivelmalla_id inner JOIN public.sga_malla sga_malla ON sga_asignaturamalla.malla_id = sga_malla.id inner JOIN public.sga_carrera sga_carrera ON sga_malla.carrera_id = sga_carrera.id inner JOIN public.sga_coordinacion_carrera sga_coordinacion_carrera ON sga_carrera.id = sga_coordinacion_carrera.carrera_id inner JOIN public.sga_coordinacion sga_coordinacion ON sga_coordinacion_carrera.coordinacion_id = sga_coordinacion.id inner JOIN public.sga_periodo sga_periodo ON sga_nivel.periodo_id = sga_periodo.id WHERE sga_profesormateria.principal = True And sga_periodo.id = '"+periodo+"' And sga_coordinacion.id = '"+coordinacion+"' ORDER BY sga_carrera.nombre ASC, Docente ASC, sga_asignatura.nombre ASC"
#                     cursor.execute(sql)
#                     results = cursor.fetchall()
#                     row_num = 4
#                     for r in results:
#                         i = 0
#                         campo1 = r[0]
#                         campo2 = r[1]
#                         campo3 = r[2]
#                         campo4 = r[3]
#                         campo5 = r[4]
#                         campo6 = r[5]
#                         campo7 = r[6]
#                         campo8 = r[7]
#                         campo9 = r[8]
#                         campo10 = r[9]
#                         campo11 = r[10]
#                         campo12 = r[12]
#                         campo13 = r[11]
#                         ws.write(row_num, 0, campo1, font_style2)
#                         ws.write(row_num, 1, campo2, font_style2)
#                         ws.write(row_num, 2, campo3, font_style2)
#                         ws.write(row_num, 3, campo4, font_style2)
#                         ws.write(row_num, 4, campo5, font_style2)
#                         ws.write(row_num, 5, campo6, font_style2)
#                         ws.write(row_num, 6, campo7, font_style2)
#                         ws.write(row_num, 7, campo8, font_style2)
#                         ws.write(row_num, 8, campo9, font_style2)
#                         ws.write(row_num, 9, campo10, font_style2)
#                         ws.write(row_num, 10, campo11, font_style2)
#                         ws.write(row_num, 11, campo12, font_style2)
#                         ws.write(row_num, 12, campo13, font_style2)
#                         # while i < len(r):
#                         #     # ws.write(row_num, i, r[i], font_style)
#                         #     # ws.col(i).width = columns[i][1]
#                         row_num += 1
#                     wb.save(response)
#                     return response
#                 except Exception as ex:
#                     pass
#
#             elif action == 'reportedistributivo':
#                 try:
#                     periodo = request.GET['periodo']
#                     __author__ = 'Unemi'
#                     style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
#                     style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
#                     style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
#                     title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
#                     style1 = easyxf(num_format_str='D-MMM-YY')
#                     font_style = XFStyle()
#                     font_style.font.bold = True
#                     font_style2 = XFStyle()
#                     font_style2.font.bold = False
#                     wb = Workbook(encoding='utf-8')
#                     ws = wb.add_sheet('exp_xls_post_part')
#                     ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
#                     response = HttpResponse(content_type="application/ms-excel")
#                     response[
#                         'Content-Disposition'] = 'attachment; filename=exp_xls_post_part_' + random.randint(
#                         1, 10000).__str__() + '.xls'
#                     columns = [
#                         (u"FACULTAD", 6000),
#                         (u"CARRERA", 6000),
#                         (u"SECCIÓN", 6000),
#                         (u"NIVEL", 6000),
#                         (u"PARALELO", 6000),
#                         (u"IDMATERIA", 2500),
#                         (u"ASIGNATURA", 6000),
#                         (u"CUPO", 6000),
#                         (u"MATRICULADOS", 6000),
#                         (u"DOCENTE", 6000),
#                         (u"CEDULA", 6000),
#                         (u"USUARIO", 6000),
#                         (u"HORAS SEMANALES", 4000),
#                         (u"TIPO", 4000),
#                         (u"CORREO PERSONAL", 4000),
#                         (u"CORREO INSTITUCIONAL", 4000),
#                         (u"TIPO PROFESOR", 4000),
#                         (u"DESDE", 4000),
#                         (u"HASTA", 4000),
#                         (u"DEDICACION", 5000),
#                         (u"CATEGORIA", 4000)
#                     ]
#                     row_num = 3
#                     for col_num in range(len(columns)):
#                         ws.write(row_num, col_num, columns[col_num][0], font_style)
#                         ws.col(col_num).width = columns[col_num][1]
#                     cursor = connection.cursor()
#                     sql = "SELECT " \
#                           " sga_coordinacion.nombre AS Facultad, " \
#                           " sga_carrera.nombre AS Carrera, " \
#                           " sga_sesion.nombre AS Seccion, " \
#                           " sga_nivelmalla.nombre AS Nivel, " \
#                           " sga_materia.paralelo as Paralelo, " \
#                           " sga_materia.id AS Idmateria, " \
#                           " sga_asignatura.nombre AS Asignatura, " \
#                           " sga_persona.apellido1 || ' ' || sga_persona.apellido2 || ' ' || sga_persona.nombres  AS Docente, " \
#                           " sga_profesormateria.hora AS sga_profesormateria_hora, " \
#                           " (case sga_profesormateria.principal when true then 'PRINCIPAL' else 'PRACTICA' end) as Tipo, " \
#                           " sga_persona.cedula, (select u.username from auth_user u where u.id=sga_persona.usuario_id), sga_persona.email, sga_persona.emailinst, " \
#                           " sga_materia.cupo as cupo, (select count(*) from sga_materiaasignada ma, sga_matricula mat1 where ma.matricula_id=mat1.id and mat1.estado_matricula in (2,3) and ma.materia_id=sga_materia.id and ma.id not in (select mr.materiaasignada_id from sga_materiaasignadaretiro mr)) as nmatriculados, " \
#                           " sga_tipoprofesor.nombre as Tipoprofesor, " \
#                           " sga_profesormateria.desde as desde, " \
#                           " sga_profesormateria.hasta as hasta, " \
#                           " (select ti.nombre from sga_profesordistributivohoras dis,sga_tiempodedicaciondocente ti where dis.dedicacion_id=ti.id and dis.profesor_id=sga_profesor.id and periodo_id=" + periodo + " and dis.status=True) as dedicacion, " \
#                           " (select ca.nombre from sga_profesordistributivohoras dis,sga_categorizaciondocente ca where dis.categoria_id=ca.id and dis.profesor_id=sga_profesor.id and dis.periodo_id=" + periodo + " and dis.status=True) as categoria " \
#                           " FROM " \
#                           " public.sga_profesor sga_profesor " \
#                           " INNER JOIN public.sga_profesormateria sga_profesormateria ON sga_profesor.id = sga_profesormateria.profesor_id " \
#                           " INNER JOIN public.sga_tipoprofesor sga_tipoprofesor ON sga_tipoprofesor.id = sga_profesormateria.tipoprofesor_id " \
#                           " INNER JOIN public.sga_persona sga_persona ON sga_profesor.persona_id = sga_persona.id " \
#                           " INNER JOIN public.sga_materia sga_materia ON sga_profesormateria.materia_id = sga_materia.id " \
#                           " INNER JOIN public.sga_nivel sga_nivel ON sga_materia.nivel_id = sga_nivel.id " \
#                           " INNER JOIN public.sga_asignatura sga_asignatura ON sga_materia.asignatura_id = sga_asignatura.id " \
#                           " INNER JOIN public.sga_asignaturamalla sga_asignaturamalla ON sga_materia.asignaturamalla_id = sga_asignaturamalla.id " \
#                           " INNER JOIN public.sga_nivelmalla sga_nivelmalla ON sga_asignaturamalla.nivelmalla_id = sga_nivelmalla.id " \
#                           " INNER JOIN public.sga_malla sga_malla ON sga_asignaturamalla.malla_id = sga_malla.id " \
#                           " INNER JOIN public.sga_carrera sga_carrera ON sga_malla.carrera_id = sga_carrera.id  " \
#                           " INNER JOIN public.sga_coordinacion_carrera sga_coordinacion_carrera ON sga_carrera.id = sga_coordinacion_carrera.carrera_id " \
#                           " INNER JOIN public.sga_coordinacion sga_coordinacion ON sga_coordinacion_carrera.coordinacion_id = sga_coordinacion.id " \
#                           " INNER JOIN public.sga_sesion sga_sesion ON sga_nivel.sesion_id = sga_sesion.id " \
#                           " INNER JOIN public.sga_periodo sga_periodo ON sga_nivel.periodo_id = sga_periodo.id " \
#                           " WHERE " \
#                           " sga_periodo.id = " + periodo + " " \
#                           " ORDER BY " \
#                           " sga_coordinacion.nombre, sga_carrera.nombre, sga_sesion.nombre, sga_nivelmalla.nombre,sga_materia.paralelo,sga_asignatura.nombre "
#                     cursor.execute(sql)
#                     results = cursor.fetchall()
#                     row_num = 4
#                     for r in results:
#                         i = 0
#                         campo1 = r[0]
#                         campo2 = r[1]
#                         campo3 = r[2]
#                         campo4 = r[3]
#                         campo5 = r[4]
#                         campo6 = r[5]
#                         campo7 = r[6]
#                         campo8 = r[7]
#                         campo9 = r[8]
#                         campo10 = r[9]
#                         campo11 = r[10]
#                         campo12 = r[11]
#                         campo13 = r[12]
#                         campo14 = r[13]
#                         campo15 = r[14]
#                         campo16 = r[15]
#                         campo17 = r[16]
#                         campo18 = r[17]
#                         campo19 = r[18]
#                         campo20 = r[19]
#                         campo21 = r[20]
#
#                         ws.write(row_num, 0, campo1, font_style2)
#                         ws.write(row_num, 1, campo2, font_style2)
#                         ws.write(row_num, 2, campo3, font_style2)
#                         ws.write(row_num, 3, campo4, font_style2)
#                         ws.write(row_num, 4, campo5, font_style2)
#                         ws.write(row_num, 5, campo6, font_style2)
#                         ws.write(row_num, 6, campo7, font_style2)
#                         ws.write(row_num, 7, campo15, font_style2)
#                         ws.write(row_num, 8, campo16, font_style2)
#                         ws.write(row_num, 9, campo8, font_style2)
#                         ws.write(row_num, 10, campo11, font_style2)
#                         ws.write(row_num, 11, campo12, font_style2)
#                         ws.write(row_num, 12, campo9, font_style2)
#                         ws.write(row_num, 13, campo10, font_style2)
#                         ws.write(row_num, 14, campo13, font_style2)
#                         ws.write(row_num, 15, campo14, font_style2)
#                         ws.write(row_num, 16, campo17, font_style2)
#                         ws.write(row_num, 17, campo18, style1)
#                         ws.write(row_num, 18, campo19, style1)
#                         ws.write(row_num, 19, campo20, style1)
#                         ws.write(row_num, 20, campo21, style1)
#                         row_num += 1
#                     wb.save(response)
#                     return response
#                 except Exception as ex:
#                     pass
#
#             elif action == 'sinhorarios':
#                 try:
#                     periodo = request.GET['periodo']
#                     __author__ = 'Unemi'
#                     style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
#                     style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
#                     style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
#                     title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
#                     style1 = easyxf(num_format_str='D-MMM-YY')
#                     font_style = XFStyle()
#                     font_style.font.bold = True
#                     font_style2 = XFStyle()
#                     font_style2.font.bold = False
#                     wb = Workbook(encoding='utf-8')
#                     ws = wb.add_sheet('exp_xls_post_part')
#                     ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
#                     response = HttpResponse(content_type="application/ms-excel")
#                     response[
#                         'Content-Disposition'] = 'attachment; filename=exp_xls_post_part_' + random.randint(
#                         1, 10000).__str__() + '.xls'
#                     columns = [
#                         (u"MATERIA", 10000),
#                         (u"PARALELO", 3000),
#                         (u"SECCIÓN", 6000),
#                         (u"NIVEL", 6000),
#                         (u"CARRERA", 6000)
#                     ]
#                     row_num = 3
#                     for col_num in range(len(columns)):
#                         ws.write(row_num, col_num, columns[col_num][0], font_style)
#                         ws.col(col_num).width = columns[col_num][1]
#                     cursor = connection.cursor()
#                     sql = "select a.nombre, m.paralelo, n.paralelo, nm.nombre, car.nombre, c.turno_id from sga_materia m " \
#                            "inner join sga_nivel n on m.nivel_id=n.id and n.periodo_id=" + periodo + " " \
#                            "left join sga_clase c on c.materia_id=m.id " \
#                            "inner join sga_asignatura a on a.id=m.asignatura_id " \
#                            "inner join sga_asignaturamalla am on am.id=m.asignaturamalla_id " \
#                            "inner join sga_nivelmalla nm on nm.id=am.nivelmalla_id " \
#                            "inner join sga_malla malla on malla.id=am.malla_id " \
#                            "inner join sga_carrera car on car.id=malla.carrera_id " \
#                            "where c.turno_id is null "
#                     cursor.execute(sql)
#                     results = cursor.fetchall()
#                     row_num = 4
#                     for r in results:
#                         i = 0
#                         campo1 = r[0]
#                         campo2 = r[1]
#                         campo3 = r[2]
#                         campo4 = r[3]
#                         campo5 = r[4]
#                         ws.write(row_num, 0, campo1, font_style2)
#                         ws.write(row_num, 1, campo2, font_style2)
#                         ws.write(row_num, 2, campo3, font_style2)
#                         ws.write(row_num, 3, campo4, font_style2)
#                         ws.write(row_num, 4, campo5, font_style2)
#                         row_num += 1
#                     wb.save(response)
#                     return response
#                 except Exception as ex:
#                     pass
#
#             elif action == 'reporteaula':
#                 try:
#                     periodo = request.GET['periodo']
#                     __author__ = 'Unemi'
#                     style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
#                     style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
#                     style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
#                     title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
#                     style1 = easyxf(num_format_str='D-MMM-YY')
#                     font_style = XFStyle()
#                     font_style.font.bold = True
#                     font_style2 = XFStyle()
#                     font_style2.font.bold = False
#                     wb = Workbook(encoding='utf-8')
#                     ws = wb.add_sheet('exp_xls_post_part')
#                     ws.write_merge(0, 0, 0, 12, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
#                     response = HttpResponse(content_type="application/ms-excel")
#                     response[
#                         'Content-Disposition'] = 'attachment; filename=exp_xls_post_part_' + random.randint(
#                         1, 10000).__str__() + '.xls'
#                     columns = [
#                         (u"AULA", 6000),
#                         (u"CAPACIDAD AULA", 6000),
#                         (u"CUPO MATRICULA", 6000),
#                         (u"MATRICULADOS", 6000),
#                         (u"DÍAS", 6000),
#                         (u"INICIO", 6000),
#                         (u"FIN", 6000),
#                         (u"HORARIOS", 6000),
#                         (u"ASIGNATURA", 6000),
#                         (u"JORNADA", 6000),
#                         (u"NIVEL", 6000),
#                         (u"PARALELO", 6000),
#                         (u"CARRERA", 6000),
#                         (u"DOCENTE", 6000),
#                         (u"PRINCIPAL", 6000),
#                         (u"FACULTAD", 6000),
#                     ]
#                     row_num = 3
#                     for col_num in range(len(columns)):
#                         ws.write(row_num, col_num, columns[col_num][0], font_style)
#                         ws.col(col_num).width = columns[col_num][1]
#                     cursor = connection.cursor()
#                     # lista_json = []
#                     # data = {}
#                     sql = "select al.nombre as Aula, al.capacidad as capacidad_aula, mat.cupo as cupo_matriculas," \
#                           " (select count(*) from sga_materiaasignada mas1, sga_matricula mat1, sga_nivel ni1 where mat1.estado_matricula in (2,3) and mas1.matricula_id=mat1.id and mat1.nivel_id=ni1.id and ni1.periodo_id=ni.periodo_id and mas1.materia_id=mat.id) as Matriculados," \
#                           " (case cl.dia  when 1 then 'LUNES' when 2 then 'MARTES' when 3 then 'MIERCOLES' when 4 then 'JUEVES' when 5 then 'VIERNES' when 6 then 'SABADO' when 7 then 'DOMINGO'  end) as dia ," \
#                           " cl.inicio , cl.fin , (tu.comienza|| '  ' || tu.termina) as Horario, asi.nombre as Asignatura , ni.paralelo as jornada , nmall.nombre as nivel , ca.nombre as Carrera, mat.paralelo as paralelo , per.apellido1 ||' '|| per.apellido2 ||' '|| per.nombres as docente," \
#                           " (case pm.principal when true then 'SI' else 'NO' end) as principal, cor.nombre as facultad" \
#                           " from sga_clase cl, sga_aula al, sga_materia mat, sga_nivel ni, sga_asignatura asi ,sga_asignaturamalla asimall, sga_nivelmalla nmall, sga_malla mall , sga_carrera ca ,  sga_turno tu , sga_profesormateria pm," \
#                           " sga_profesor pr, sga_persona per, sga_coordinacion_carrera cc, sga_coordinacion cor" \
#                           " where cl.aula_id=al.id and cl.materia_id=mat.id and mat.nivel_id=ni.id and mat.asignatura_id=asi.id and  mat.asignaturamalla_id = asimall.id and" \
#                           " pm.materia_id=mat.id and pr.id=pm.profesor_id and per.id=pr.persona_id and asimall.nivelmalla_id = nmall.id and asimall.malla_id = mall.id and tu.id=cl.turno_id and  mall.carrera_id=ca.id" \
#                           " and cc.carrera_id=ca.id  and cor.id=cc.coordinacion_id and ni.periodo_id='" + periodo + "' "
#                     cursor.execute(sql)
#                     results = cursor.fetchall()
#                     row_num = 4
#                     for r in results:
#                         i = 0
#                         campo1 = r[0]
#                         campo2 = r[1]
#                         campo3 = r[2]
#                         campo4 = r[3]
#                         campo5 = r[4]
#                         campo6 = r[5]
#                         campo7 = r[6]
#                         campo8 = r[7]
#                         campo9 = r[8]
#                         campo10 = r[9]
#                         campo11 = r[10]
#                         campo12 = r[12]
#                         campo13 = r[11]
#                         campo14 = r[13]
#                         campo15 = r[14]
#                         campo16 = r[15]
#
#                         ws.write(row_num, 0, campo1, font_style2)
#                         ws.write(row_num, 1, campo2, font_style2)
#                         ws.write(row_num, 2, campo3, font_style2)
#                         ws.write(row_num, 3, campo4, font_style2)
#                         ws.write(row_num, 4, campo5, font_style2)
#                         ws.write(row_num, 5, campo6, style1)
#                         ws.write(row_num, 6, campo7, style1)
#                         ws.write(row_num, 7, campo8, font_style2)
#                         ws.write(row_num, 8, campo9, font_style2)
#                         ws.write(row_num, 9, campo10, font_style2)
#                         ws.write(row_num, 10, campo11, font_style2)
#                         ws.write(row_num, 11, campo12, font_style2)
#                         ws.write(row_num, 12, campo13, font_style2)
#                         ws.write(row_num, 13, campo14, font_style2)
#                         ws.write(row_num, 14, campo15, font_style2)
#                         ws.write(row_num, 15, campo16, font_style2)
#                         row_num += 1
#                     wb.save(response)
#                     return response
#                 except Exception as ex:
#                     pass
#
#             elif action == 'reportealumnos':
#                 try:
#                     periodo = request.GET['periodo']
#                     __author__ = 'Unemi'
#                     style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
#                     style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
#                     style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
#                     title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
#                     style1 = easyxf(num_format_str='D-MMM-YY')
#                     font_style = XFStyle()
#                     font_style.font.bold = True
#                     font_style2 = XFStyle()
#                     font_style2.font.bold = False
#                     wb = Workbook(encoding='utf-8')
#                     ws = wb.add_sheet('exp_xls_post_part')
#                     ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
#                     response = HttpResponse(content_type="application/ms-excel")
#                     response[
#                         'Content-Disposition'] = 'attachment; filename=exp_xls_post_part_' + random.randint(
#                         1, 10000).__str__() + '.xls'
#                     columns = [
#                         (u"FACULTAD", 6000),
#                         (u"CARRERA", 6000),
#                         (u"SECCION", 6000),
#                         (u"NIVEL", 6000),
#                         (u"ASIGNATURA", 6000),
#                         (u"ALUMNO", 6000),
#                         (u"NOTA FINAL", 6000),
#                         (u"ASISTENCIA", 6000),
#                         (u"ESTADO", 6000),
#                         (u"DOCENTE", 6000),
#                         (u"TELEFONO", 6000),
#                         (u"EMAIL", 6000),
#                         (u"EMAIL INST", 6000),
#                         (u"CIUDAD", 6000),
#                         (u"DIRECCION", 12000),
#                         (u"PARALELO", 12000),
#                         (u"VECES DE MATRICULA", 6000),
#                         (u"CREDITOS", 6000),
#                     ]
#                     row_num = 3
#                     for col_num in range(len(columns)):
#                         ws.write(row_num, col_num, columns[col_num][0], font_style)
#                         ws.col(col_num).width = columns[col_num][1]
#                     cursor = connection.cursor()
#                     # lista_json = []
#                     # data = {}
#                     sql = "SELECT DISTINCT " \
#                           "   sga_coordinacion.nombre as sga_coordinacion_nombre, " \
#                           "   sga_carrera.nombre AS sga_carrera_nombre, " \
#                           "   sga_sesion.nombre AS sga_sesion_nombre, " \
#                           "   sga_nivelmalla.nombre as sga_nivelmalla_nombre, " \
#                           "   sga_asignatura.nombre as sga_asignatura_nombre, " \
#                           "   sga_persona.apellido1 || ' ' || sga_persona.apellido2  || ' ' ||  sga_persona.nombres AS sga_persona_nombres, " \
#                           "   sga_materiaasignada.notafinal as notafinal, " \
#                           "   sga_materiaasignada.asistenciafinal as asistenciafinal, " \
#                           "   (select p.apellido1 || ' ' || p.apellido2 || ' ' || p.nombres from sga_persona p where p.id=sga_profesor.persona_id) as docente, " \
#                           "   sga_tipoestado.nombre as estado, " \
#                           "   sga_nivelmalla.id as sga_nivelmalla_id," \
#                           "   sga_persona.telefono, sga_persona.email, sga_persona.emailinst, sga_persona.ciudad, " \
#                           "   sga_persona.direccion || ', ' || sga_persona.direccion2 || ' #:' || sga_persona.num_direccion || ' , SECTOR:' || sga_persona.sector as direccion, sga_materia.paralelo, sga_materiaasignada.matriculas, sga_asignaturamalla.creditos" \
#                         " FROM sga_persona sga_persona " \
#                         "      RIGHT OUTER JOIN sga_inscripcion sga_inscripcion ON sga_persona.id = sga_inscripcion.persona_id " \
#                         "     INNER JOIN sga_matricula sga_matricula ON sga_matricula.inscripcion_id=sga_inscripcion.id " \
#                         "    inner join sga_materiaasignada sga_materiaasignada on sga_materiaasignada.matricula_id=sga_matricula.id " \
#                         "     inner join sga_materia sga_materia on sga_materia.id=sga_materiaasignada.materia_id " \
#                         "     LEFT join sga_profesormateria on sga_profesormateria.materia_id=sga_materia.id " \
#                         "     LEFT join sga_profesor on sga_profesor.id=sga_profesormateria.profesor_id " \
#                         "     inner join sga_asignatura sga_asignatura on sga_asignatura.id=sga_materia.asignatura_id " \
#                         "      inner join sga_asignaturamalla sga_asignaturamalla on sga_asignaturamalla.id=sga_materia.asignaturamalla_id " \
#                         "    inner join sga_nivel sga_nivel ON sga_nivel.id=sga_matricula.nivel_id and sga_nivel.periodo_id= '" + periodo + "' " \
#                         "      inner join sga_nivelmalla sga_nivelmalla on sga_nivelmalla.id=sga_asignaturamalla.nivelmalla_id " \
#                         "     INNER JOIN sga_carrera sga_carrera ON sga_inscripcion.carrera_id = sga_carrera.id " \
#                         "     INNER JOIN sga_coordinacion_carrera on sga_coordinacion_carrera.carrera_id=sga_carrera.id " \
#                         "     INNER JOIN sga_coordinacion on sga_coordinacion.id=sga_coordinacion_carrera.coordinacion_id " \
#                         "     INNER JOIN sga_modalidad sga_modalidad ON sga_inscripcion.modalidad_id = sga_modalidad.id " \
#                         "     INNER JOIN sga_sesion sga_sesion ON sga_inscripcion.sesion_id = sga_sesion.id " \
#                         "     inner join sga_tipoestado on sga_tipoestado.id=sga_materiaasignada.estado_id " \
#                         "    where sga_matricula.estado_matricula in (2,3) and sga_matricula.id not in (select ma.id from (select mat.id as id, count(ma.materia_id)  as numero " \
#                         "    from sga_Matricula mat, sga_Nivel n, sga_materiaasignada  ma, sga_materia mate, sga_asignatura asi " \
#                         "    where mat.estado_matricula in (2,3) and mat.nivel_id = n.id and mat.id = ma.matricula_id and ma.materia_id = mate.id and mate.asignatura_id = asi.id and n.periodo_id = '" + periodo + "' " \
#                         "    and asi.modulo = True group by mat.id)  ma, (select mat.id as id, count(ma.materia_id) as numero from sga_Matricula mat, sga_Nivel n, sga_materiaasignada ma, " \
#                         "    sga_materia mate, sga_asignatura asi where mat.estado_matricula in (2,3) and mat.nivel_id = n.id and mat.id = ma.matricula_id and ma.materia_id = mate.id and mate.asignatura_id = asi.id and n.periodo_id = '" + periodo + "' " \
#                         "    group by mat.id) mo where ma.id = mo.id and ma.numero = mo.numero) order by sga_carrera.nombre,sga_nivelmalla.id,sga_sesion.nombre,sga_persona_nombres"
#                     cursor.execute(sql)
#                     results = cursor.fetchall()
#                     row_num = 4
#                     for r in results:
#                         i = 0
#                         campo1 = r[0]
#                         campo2 = r[1]
#                         campo3 = r[2]
#                         campo4 = r[3]
#                         campo5 = r[4]
#                         campo6 = r[5]
#                         campo7 = r[6]
#                         campo8 = r[7]
#                         campo9 = r[8]
#                         campo10 = r[9]
#                         campo11 = r[11]
#                         campo12 = r[12]
#                         campo13 = r[13]
#                         campo14 = r[14]
#                         campo15 = r[15]
#                         campo16 = r[16]
#                         campo17 = r[17]
#                         campo18 = r[18]
#
#                         ws.write(row_num, 0, campo1, font_style2)
#                         ws.write(row_num, 1, campo2, font_style2)
#                         ws.write(row_num, 2, campo3, font_style2)
#                         ws.write(row_num, 3, campo4, font_style2)
#                         ws.write(row_num, 4, campo5, font_style2)
#                         ws.write(row_num, 5, campo6, font_style2)
#                         ws.write(row_num, 6, campo7, font_style2)
#                         ws.write(row_num, 7, campo8, font_style2)
#                         ws.write(row_num, 8, campo10, font_style2)
#                         ws.write(row_num, 9, campo9, font_style2)
#                         ws.write(row_num, 10, campo11, font_style2)
#                         ws.write(row_num, 11, campo12, font_style2)
#                         ws.write(row_num, 12, campo13, font_style2)
#                         ws.write(row_num, 13, campo14, font_style2)
#                         ws.write(row_num, 14, campo15, font_style2)
#                         ws.write(row_num, 15, campo16, font_style2)
#                         ws.write(row_num, 16, campo17, font_style2)
#                         ws.write(row_num, 17, campo18, font_style2)
#
#                         row_num += 1
#                     wb.save(response)
#                     return response
#                 except Exception as ex:
#                     pass
#
#             elif action == 'reportealumnospre':
#                 try:
#                     periodo = request.GET['periodo']
#                     __author__ = 'Unemi'
#                     style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
#                     style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
#                     style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
#                     title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
#                     style1 = easyxf(num_format_str='D-MMM-YY')
#                     font_style = XFStyle()
#                     font_style.font.bold = True
#                     font_style2 = XFStyle()
#                     font_style2.font.bold = False
#                     wb = Workbook(encoding='utf-8')
#                     ws = wb.add_sheet('exp_xls_post_part')
#                     ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
#                     response = HttpResponse(content_type="application/ms-excel")
#                     response[
#                         'Content-Disposition'] = 'attachment; filename=exp_xls_post_part_' + random.randint(
#                         1, 10000).__str__() + '.xls'
#                     columns = [
#                         (u"FACULTAD", 6000),
#                         (u"CARRERA", 6000),
#                         (u"SECCION", 6000),
#                         (u"NIVEL", 6000),
#                         (u"ASIGNATURA", 6000),
#                         (u"CEDULA", 6000),
#                         (u"ALUMNO", 6000),
#                         (u"NOTA FINAL", 6000),
#                         (u"PROMEDIO", 6000),
#                         (u"ASISTENCIA", 6000),
#                         (u"ESTADO", 6000),
#                         (u"DOCENTE", 6000),
#                         (u"TELEFONO", 6000),
#                         (u"EMAIL", 6000),
#                         (u"EMAIL INST", 6000),
#                         (u"CIUDAD", 6000),
#                         (u"DIRECCION", 12000),
#                         (u"PARALELO", 12000),
#                     ]
#                     row_num = 3
#                     for col_num in range(len(columns)):
#                         ws.write(row_num, col_num, columns[col_num][0], font_style)
#                         ws.col(col_num).width = columns[col_num][1]
#                     cursor = connection.cursor()
#                     # lista_json = []
#                     # data = {}
#                     sql = "SELECT DISTINCT " \
#                           "   sga_coordinacion.nombre as sga_coordinacion_nombre, " \
#                           "   sga_carrera.nombre AS sga_carrera_nombre, " \
#                           "   sga_sesion.nombre AS sga_sesion_nombre, " \
#                           "   sga_nivelmalla.nombre as sga_nivelmalla_nombre, " \
#                           "   sga_asignatura.nombre as sga_asignatura_nombre, " \
#                           "   sga_persona.apellido1 || ' ' || sga_persona.apellido2  || ' ' ||  sga_persona.nombres AS sga_persona_nombres, " \
#                           "   sga_materiaasignada.notafinal as notafinal, " \
#                           "   sga_materiaasignada.asistenciafinal as asistenciafinal, " \
#                           "   (select p.apellido1 || ' ' || p.apellido2 || ' ' || p.nombres from sga_persona p where p.id=sga_profesor.persona_id) as docente, " \
#                           "   sga_tipoestado.nombre as estado, " \
#                           "   sga_nivelmalla.id as sga_nivelmalla_id," \
#                           "   sga_persona.telefono, sga_persona.email, sga_persona.emailinst, sga_persona.ciudad, " \
#                           "   sga_persona.direccion || ', ' || sga_persona.direccion2 || ' #:' || sga_persona.num_direccion || ' , SECTOR:' || sga_persona.sector as direccion, sga_materia.paralelo, " \
#                           " (select sum((case when a1.id = '1939' then(ma1.notafinal * 0.15) else (case when mo1.id = 4 then(ma1.notafinal * 0.10) else (ma1.notafinal * 0.25) end) end) ) " \
#                           " from sga_materiaasignada ma1, sga_materia m1, sga_modeloevaluativo mo1, sga_asignatura a1 where ma1.matricula_id = sga_matricula.id and ma1.status = true and m1.id = ma1.materia_id and m1.status = true " \
#                           " and mo1.id = m1.modeloevaluativo_id and mo1.status = true and a1.id = m1.asignatura_id and a1.status = true) as notapromedio, sga_persona.cedula " \
#                     " FROM sga_persona sga_persona " \
#                         "      RIGHT OUTER JOIN sga_inscripcion sga_inscripcion ON sga_persona.id = sga_inscripcion.persona_id " \
#                         "     INNER JOIN sga_matricula sga_matricula ON sga_matricula.inscripcion_id=sga_inscripcion.id " \
#                         "    inner join sga_materiaasignada sga_materiaasignada on sga_materiaasignada.matricula_id=sga_matricula.id " \
#                         "     inner join sga_materia sga_materia on sga_materia.id=sga_materiaasignada.materia_id " \
#                         "     LEFT join sga_profesormateria on sga_profesormateria.materia_id=sga_materia.id " \
#                         "     LEFT join sga_profesor on sga_profesor.id=sga_profesormateria.profesor_id " \
#                         "     inner join sga_asignatura sga_asignatura on sga_asignatura.id=sga_materia.asignatura_id " \
#                         "      inner join sga_asignaturamalla sga_asignaturamalla on sga_asignaturamalla.id=sga_materia.asignaturamalla_id " \
#                         "    inner join sga_nivel sga_nivel ON sga_nivel.id=sga_matricula.nivel_id and sga_nivel.periodo_id= '" + periodo + "' " \
#                         "      inner join sga_nivelmalla sga_nivelmalla on sga_nivelmalla.id=sga_asignaturamalla.nivelmalla_id " \
#                         "     INNER JOIN sga_carrera sga_carrera ON sga_inscripcion.carrera_id = sga_carrera.id " \
#                         "     INNER JOIN sga_coordinacion_carrera on sga_coordinacion_carrera.carrera_id=sga_carrera.id " \
#                         "     INNER JOIN sga_coordinacion on sga_coordinacion.id=sga_coordinacion_carrera.coordinacion_id " \
#                         "     INNER JOIN sga_modalidad sga_modalidad ON sga_inscripcion.modalidad_id = sga_modalidad.id " \
#                         "     INNER JOIN sga_sesion sga_sesion ON sga_inscripcion.sesion_id = sga_sesion.id " \
#                         "     inner join sga_tipoestado on sga_tipoestado.id=sga_materiaasignada.estado_id " \
#                         "    where sga_matricula.id not in (select ma.id from (select mat.id as id, count(ma.materia_id)  as numero " \
#                         "    from sga_Matricula mat, sga_Nivel n, sga_materiaasignada  ma, sga_materia mate, sga_asignatura asi " \
#                         "    where mat.nivel_id = n.id and mat.id = ma.matricula_id and ma.materia_id = mate.id and mate.asignatura_id = asi.id and n.periodo_id = '" + periodo + "' " \
#                         "    and asi.modulo = True group by mat.id)  ma, (select mat.id as id, count(ma.materia_id) as numero from sga_Matricula mat, sga_Nivel n, sga_materiaasignada ma, " \
#                         "    sga_materia mate, sga_asignatura asi where mat.nivel_id = n.id and mat.id = ma.matricula_id and ma.materia_id = mate.id and mate.asignatura_id = asi.id and n.periodo_id = '" + periodo + "' " \
#                         "    group by mat.id) mo where ma.id = mo.id and ma.numero = mo.numero) order by sga_carrera.nombre,sga_nivelmalla.id,sga_sesion.nombre,sga_persona_nombres"
#                     cursor.execute(sql)
#                     results = cursor.fetchall()
#                     row_num = 4
#                     for r in results:
#                         i = 0
#                         campo1 = r[0]
#                         campo2 = r[1]
#                         campo3 = r[2]
#                         campo4 = r[3]
#                         campo5 = r[4]
#                         campo6 = r[5]
#                         campo7 = r[6]
#                         campo8 = r[7]
#                         campo9 = r[8]
#                         campo10 = r[9]
#                         campo11 = r[11]
#                         campo12 = r[12]
#                         campo13 = r[13]
#                         campo14 = r[14]
#                         campo15 = r[15]
#                         campo16 = r[16]
#                         campo17 = round(r[17],0)
#                         campo18 = r[18]
#
#
#                         ws.write(row_num, 0, campo1, font_style2)
#                         ws.write(row_num, 1, campo2, font_style2)
#                         ws.write(row_num, 2, campo3, font_style2)
#                         ws.write(row_num, 3, campo4, font_style2)
#                         ws.write(row_num, 4, campo5, font_style2)
#                         ws.write(row_num, 5, campo18, font_style2)
#                         ws.write(row_num, 6, campo6, font_style2)
#                         ws.write(row_num, 7, campo7, font_style2)
#                         ws.write(row_num, 8, campo17, font_style2)
#                         ws.write(row_num, 9, campo8, font_style2)
#                         ws.write(row_num, 10, campo10, font_style2)
#                         ws.write(row_num, 11, campo9, font_style2)
#                         ws.write(row_num, 12, campo11, font_style2)
#                         ws.write(row_num, 13, campo12, font_style2)
#                         ws.write(row_num, 14, campo13, font_style2)
#                         ws.write(row_num, 15, campo14, font_style2)
#                         ws.write(row_num, 16, campo15, font_style2)
#                         ws.write(row_num, 17, campo16, font_style2)
#
#                         row_num += 1
#                     wb.save(response)
#                     return response
#                 except Exception as ex:
#                     pass
#
#             if action == 'reporteprematriculados':
#                 try:
#                     idcarrera = request.GET['id']
#                     cursor = connection.cursor()
#                     response = HttpResponse(content_type="application/ms-excel")
#                     response['Content-Disposition'] = 'attachment; filename=prematricula_asignaturas.xls'
#                     __author__ = 'Unemi'
#                     style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
#                     style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
#                     style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
#                     title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
#                     style1 = easyxf(num_format_str='D-MMM-YY')
#                     font_style = XFStyle()
#                     font_style.font.bold = True
#                     font_style2 = XFStyle()
#                     font_style2.font.bold = False
#                     wb = Workbook(encoding='utf-8')
#                     ws = wb.add_sheet('exp_xls_post_part')
#                     # ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
#
#
#                     columns=[
#                         (u"N.", 2000),
#                         (u"CARRERA", 6000),
#                         (u"MALLA", 3000),
#                         (u"IDENTIFICACION", 6000),
#                         (u"ASIGNATURA", 6000),
#                         (u"NIVEL", 4000),
#                         (u"MATUTINA", 2000),
#                         (u"VESPERTINA", 2000),
#                         (u"NOCTURNA", 2000),
#                         (u"FIN DE SEMANA", 2000),
#                         (u"TOTAL", 2000),
#                     ]
#                     row_num = 0
#                     for col_num in range(len(columns)):
#                         ws.write(row_num, col_num, columns[col_num][0], font_style)
#                         ws.col(col_num).width = columns[col_num][1]
#                     date_format = xlwt.XFStyle()
#                     date_format.num_format_str = 'yyyy/mm/dd'
#                     a = 0
#                     listaestudiante = "select codigomalla,carreras,identificacion,asignatura,nivel,totalmanana,vespertina,nocturna,finsemana," \
#                                       "(totalmanana+vespertina+nocturna+finsemana) as total,inicio " \
#                                       "from (select  smalla.id as codigomalla,carr.nombre as carreras,smalla.inicio,asi.identificacion,(mat.nombre || ' [' || mat.codigo || ']' ) as asignatura," \
#                                       "nmall.nombre as nivel,(SELECT count(sga_asignatura.id) FROM sga_asignatura " \
#                                       "INNER JOIN sga_prematricula_asignaturas ON (sga_asignatura.id = sga_prematricula_asignaturas.asignatura_id) " \
#                                       "INNER JOIN sga_prematricula ON (sga_prematricula_asignaturas.prematricula_id = sga_prematricula.id) " \
#                                       "INNER JOIN sga_inscripcion ON (sga_prematricula.inscripcion_id = sga_inscripcion.id) " \
#                                       "INNER JOIN sga_inscripcionmalla ON (sga_inscripcion.id = sga_inscripcionmalla.inscripcion_id) " \
#                                       "WHERE sga_prematricula.periodo_id = '" + str(periodo.id) + "' AND sga_inscripcion.sesion_id = 1 " \
#                                       "AND sga_inscripcionmalla.malla_id = smalla.id " \
#                                       "AND sga_asignatura.id = asi.asignatura_id )as totalmanana,(SELECT count(sga_asignatura.id) " \
#                                       "FROM sga_asignatura INNER JOIN sga_prematricula_asignaturas ON (sga_asignatura.id = sga_prematricula_asignaturas.asignatura_id) " \
#                                       "INNER JOIN sga_prematricula ON (sga_prematricula_asignaturas.prematricula_id = sga_prematricula.id) " \
#                                       "INNER JOIN sga_inscripcion ON (sga_prematricula.inscripcion_id = sga_inscripcion.id) " \
#                                       "INNER JOIN sga_inscripcionmalla ON (sga_inscripcion.id = sga_inscripcionmalla.inscripcion_id) " \
#                                       "WHERE sga_prematricula.periodo_id = '" + str(periodo.id) + "'  AND sga_inscripcion.sesion_id = 4 " \
#                                       "AND sga_inscripcionmalla.malla_id = smalla.id  AND sga_asignatura.id = asi.asignatura_id )as vespertina," \
#                                       "(SELECT count(sga_asignatura.id)FROM sga_asignatura " \
#                                       "INNER JOIN sga_prematricula_asignaturas ON sga_asignatura.id = sga_prematricula_asignaturas.asignatura_id " \
#                                       "INNER JOIN sga_prematricula ON sga_prematricula_asignaturas.prematricula_id = sga_prematricula.id " \
#                                       "INNER JOIN sga_inscripcion ON sga_prematricula.inscripcion_id = sga_inscripcion.id " \
#                                       "INNER JOIN sga_inscripcionmalla ON sga_inscripcion.id = sga_inscripcionmalla.inscripcion_id " \
#                                       "WHERE sga_prematricula.periodo_id = '" + str(periodo.id) + "'  AND sga_inscripcion.sesion_id = 5  " \
#                                       "AND sga_inscripcionmalla.malla_id = smalla.id  AND sga_asignatura.id = asi.asignatura_id )as nocturna," \
#                                       "(SELECT count(sga_asignatura.id) FROM sga_asignatura " \
#                                       "INNER JOIN sga_prematricula_asignaturas ON sga_asignatura.id = sga_prematricula_asignaturas.asignatura_id " \
#                                       "INNER JOIN sga_prematricula ON sga_prematricula_asignaturas.prematricula_id = sga_prematricula.id " \
#                                       "INNER JOIN sga_inscripcion ON sga_prematricula.inscripcion_id = sga_inscripcion.id " \
#                                       "INNER JOIN sga_inscripcionmalla ON sga_inscripcion.id = sga_inscripcionmalla.inscripcion_id " \
#                                       "WHERE sga_prematricula.periodo_id = '" + str(periodo.id) + "'  AND sga_inscripcion.sesion_id = 7 " \
#                                       "AND sga_inscripcionmalla.malla_id = smalla.id  AND sga_asignatura.id = asi.asignatura_id )as finsemana " \
#                                       "from sga_asignaturamalla asi left join sga_asignatura mat on asi.asignatura_id=mat.id " \
#                                       "left join sga_nivelmalla  nmall on nmall.id=asi.nivelmalla_id " \
#                                       "left join sga_malla  smalla on smalla.id=asi.malla_id " \
#                                       "left join sga_carrera  carr on carr.id=smalla.carrera_id " \
#                                       "where carr.id='" + idcarrera + "' order by nmall.id, mat.nombre) as d"
#                     cursor.execute(listaestudiante)
#                     results = cursor.fetchall()
#                     for per in results:
#                         a += 1
#                         ws.write(a, 0, a)
#                         ws.write(a, 1, per[1])
#                         ws.write(a, 2, per[10], date_format)
#                         ws.write(a, 3, per[2])
#                         ws.write(a, 4, per[3])
#                         ws.write(a, 5, per[4])
#                         ws.write(a, 6, per[5])
#                         ws.write(a, 7, per[6])
#                         ws.write(a, 8, per[7])
#                         ws.write(a, 9, per[8])
#                         ws.write(a, 10, per[9])
#                     wb.save(response)
#                     return response
#                 except Exception as ex:
#                     pass
#
#             elif action == 'totalmatriculados':
#                 try:
#                     periodo = request.GET['periodo']
#                     cursor = connection.cursor()
#                     response = HttpResponse(content_type="application/ms-excel")
#                     response['Content-Disposition'] = 'attachment; filename=listado_alumnos.xls'
#                     wb = xlwt.Workbook()
#                     ws = wb.add_sheet('Sheetname')
#                     estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
#                     ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
#                     ws.col(0).width = 1000
#                     ws.col(1).width = 6000
#                     ws.col(2).width = 3000
#                     ws.col(3).width = 3000
#                     ws.col(4).width = 3000
#                     ws.col(5).width = 6000
#                     ws.col(6).width = 6000
#                     ws.col(7).width = 6000
#                     ws.col(8).width = 6000
#                     ws.col(9).width = 6000
#                     ws.col(10).width = 6000
#                     ws.col(11).width = 1000
#                     ws.write(4, 0, 'N.')
#                     ws.write(4, 1, 'PERIODO')
#                     ws.write(4, 2, 'NIVEL')
#                     ws.write(4, 3, 'SECCION')
#                     ws.write(4, 4, 'CEDULA')
#                     ws.write(4, 5, 'APELLIDOS')
#                     ws.write(4, 6, 'NOMBRES')
#                     ws.write(4, 7, 'SEXO')
#                     ws.write(4, 8, 'FECHANACIMIENTO')
#                     ws.write(4, 9, 'EMAIL')
#                     ws.write(4, 10, 'EMAILINST')
#                     ws.write(4, 11, 'COORDINACION')
#                     ws.write(4, 12, 'CARRERA')
#                     ws.write(4, 13, 'TELEFONO')
#                     a = 4
#                     date_format = xlwt.XFStyle()
#                     date_format.num_format_str = 'yyyy/mm/dd'
#                     listaestudiante = "select mat.id,per.nombre as periodo,nv.nombre as nivel,p.cedula,p.apellido1,p.apellido2,p.nombres,p.email,p.emailinst," \
#                                       "coor.nombre as coordinacion,car.nombre as carrera, ses.nombre as sesion,p.telefono,p.sexo_id as sexo,p.nacimiento " \
#                                       "from sga_matricula mat,sga_inscripcion i,sga_persona p,sga_nivel n,sga_carrera car,sga_coordinacion coor,sga_coordinacion_carrera cca, sga_periodo per, sga_nivelmalla nv,sga_inscripcionnivel inniv,sga_sesion ses " \
#                                       "where mat.estado_matricula in (2,3) and mat.inscripcion_id=i.id and i.persona_id=p.id and mat.nivel_id=n.id and i.carrera_id=car.id and " \
#                                       "car.id=cca.carrera_id and cca.coordinacion_id=coor.id and n.periodo_id=per.id and i.id=inniv.inscripcion_id and " \
#                                       "inniv.nivel_id=nv.id and n.periodo_id = '" + periodo + "' and i.sesion_id=ses.id"
#                     cursor.execute(listaestudiante)
#                     results = cursor.fetchall()
#                     for per in results:
#                         a += 1
#                         ws.write(a, 0, a - 4)
#                         ws.write(a, 1, per[1])
#                         ws.write(a, 2, per[2])
#                         ws.write(a, 3, per[11])
#                         ws.write(a, 4, per[3])
#                         ws.write(a, 5, per[4] + ' ' + per[5])
#                         ws.write(a, 6, per[6])
#                         if per[13] == 1:
#                             sexo = 'FEMENINO'
#                         else:
#                             sexo = 'MASCULINO'
#                         ws.write(a, 7, sexo)
#                         ws.write(a, 8, per[14], date_format)
#                         ws.write(a, 9, per[7])
#                         ws.write(a, 10, per[8])
#                         ws.write(a, 11, per[9])
#                         ws.write(a, 12, per[10])
#                         ws.write(a, 13, per[12])
#                     # ws.write(a+2, 0, 'Fecha:')
#                     # ws.write(a+2, 1, datetime.today(),date_format)
#                     ws.write_merge(a + 2, a + 2, 0, 1, datetime.today(), date_format)
#                     wb.save(response)
#                     return response
#                 except Exception as ex:
#                     pass
#
#             elif action == 'totalmatriculadossinmodulos':
#                 try:
#                     periodo = request.GET['periodo']
#                     cursor = connection.cursor()
#                     response = HttpResponse(content_type="application/ms-excel")
#                     response['Content-Disposition'] = 'attachment; filename=listado_alumnos.xls'
#                     wb = xlwt.Workbook()
#                     ws = wb.add_sheet('Sheetname')
#                     estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
#                     ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
#                     ws.col(0).width = 1000
#                     ws.col(1).width = 6000
#                     ws.col(2).width = 3000
#                     ws.col(3).width = 3000
#                     ws.col(4).width = 6000
#                     ws.col(5).width = 6000
#                     ws.col(6).width = 6000
#                     ws.col(7).width = 6000
#                     ws.col(8).width = 4000
#                     ws.col(9).width = 6000
#                     ws.col(10).width = 6000
#                     ws.col(11).width = 1000
#                     ws.col(14).width = 4000
#                     ws.col(15).width = 4000
#                     ws.col(16).width = 4000
#                     ws.write(4, 0, 'N.')
#                     ws.write(4, 1, 'PERIODO')
#                     ws.write(4, 2, 'NIVEL_CRE')
#                     ws.write(4, 3, 'NIVEL_MAT')
#                     ws.write(4, 4, 'SECCION')
#                     ws.write(4, 5, 'CEDULA')
#                     ws.write(4, 6, 'APELLIDOS')
#                     ws.write(4, 7, 'NOMBRES')
#                     ws.write(4, 8, 'SEXO')
#                     ws.write(4, 9, 'FECHANACIMIENTO')
#                     ws.write(4, 10, 'EMAIL')
#                     ws.write(4, 11, 'EMAILINST')
#                     ws.write(4, 12, 'COORDINACION')
#                     ws.write(4, 13, 'CARRERA')
#                     ws.write(4, 14, 'COD. SENESCYT')
#                     ws.write(4, 15, 'TELEFONO')
#                     ws.write(4, 16, 'USUARIO')
#                     ws.write(4, 17, 'INSCRIPCION')
#                     ws.write(4, 18, 'LGTBI')
#                     ws.write(4, 19, 'ETNIA')
#                     ws.write(4, 20, 'NACIONALIDAD')
#                     ws.write(4, 21, 'PAIS')
#                     ws.write(4, 22, 'PROVINCIA')
#                     ws.write(4, 23, 'CANTON')
#                     ws.write(4, 24, 'DIRECCION')
#                     ws.write(4, 25, 'ESTADO SOCIO ECONOMICO')
#                     ws.write(4, 26, 'REALIZADO')
#                     a = 4
#                     date_format = xlwt.XFStyle()
#                     date_format.num_format_str = 'yyyy/mm/dd'
#                     listaestudiante = "select mat.id,per.nombre as periodo,nv.nombre as nivel,p.cedula,p.apellido1,p.apellido2,p.nombres,p.email,p.emailinst," \
#                                       "coor.nombre as coordinacion,car.nombre as carrera,car.codigo as codigo, p.sexo_id as sexo,p.nacimiento,ses.nombre as sesion,p.telefono, usu.username,mat.inscripcion_id, " \
#                                       "(select nmt.nombre from sga_nivelmalla nmt where nmt.id=mat.nivelmalla_id) as nivelmalla, p.lgtbi, car.mencion, (select raza.nombre from sga_perfilinscripcion perfil,sga_raza raza where perfil.persona_id=p.id and perfil.raza_id=raza.id) as etnia,p.nacionalidad,  " \
#                                       "(select nombre from sga_pais pais where p.pais_id = pais.id) as pais, " \
#                                       "(select nombre from sga_provincia prov where p.provincia_id = prov.id) as provincia, " \
#                                       "(select nombre from sga_canton canton where p.canton_id = canton.id) as canton, " \
#                                       "p.direccion , p.direccion2, (select gru.codigo || ' " " ' ||gru.nombre from socioecon_fichasocioeconomicainec ficha, socioecon_gruposocioeconomico gru where ficha.grupoeconomico_id=gru.id and ficha.persona_id=p.id) as grupo, " \
#                                       "(select fich.confirmar from socioecon_fichasocioeconomicainec fich where fich.persona_id = p.id) as confirmar " \
#                                       "from sga_matricula mat,sga_inscripcion i,sga_persona p,auth_user usu,sga_nivel n,sga_carrera car,sga_coordinacion coor, " \
#                                       "sga_coordinacion_carrera cca, sga_periodo per, sga_nivelmalla nv,sga_inscripcionnivel inniv,sga_sesion ses " \
#                                       "where mat.estado_matricula in (2,3) and mat.inscripcion_id=i.id and i.persona_id=p.id and usu.id=p.usuario_id and mat.nivel_id=n.id and i.carrera_id=car.id and car.id=cca.carrera_id " \
#                                       "and cca.coordinacion_id=coor.id and n.periodo_id=per.id and i.id=inniv.inscripcion_id and inniv.nivel_id=nv.id " \
#                                       "and n.periodo_id='" + periodo + "'  and i.sesion_id=ses.id and mat.id not in (select ret.matricula_id from sga_retiromatricula ret) and mat.id not in(select ma.id from (select  mat.id as id,count(ma.materia_id)  as numero " \
#                                       "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma,sga_materia mate, " \
#                                       "sga_asignatura asi where mat.estado_matricula in (2,3) and mat.nivel_id=n.id and mat.id=ma.matricula_id " \
#                                       "and ma.materia_id=mate.id and mate.asignatura_id=asi.id and n.periodo_id='" + periodo + "'  " \
#                                       "and asi.modulo=True group by mat.id) ma,(select  mat.id as id, count(ma.materia_id) as numero " \
#                                       "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma, " \
#                                       "sga_materia mate, sga_asignatura asi where mat.estado_matricula in (2,3) and mat.nivel_id=n.id and mat.id=ma.matricula_id " \
#                                       "and ma.materia_id=mate.id and mate.asignatura_id=asi.id and n.periodo_id='" + periodo + "'  group by mat.id) mo " \
#                                       "where ma.id=mo.id and ma.numero=mo.numero);"
#                     cursor.execute(listaestudiante)
#                     results = cursor.fetchall()
#                     for per in results:
#                         a += 1
#                         ws.write(a, 0, a - 4)
#                         ws.write(a, 1, per[1])
#                         ws.write(a, 2, per[2])
#                         ws.write(a, 3, per[18])
#                         ws.write(a, 4, per[14])
#                         ws.write(a, 5, per[3])
#                         ws.write(a, 6, per[4] + ' ' + per[5])
#                         ws.write(a, 7, per[6])
#                         if per[12] == 1:
#                             sexo = 'FEMENINO'
#                         else:
#                             sexo = 'MASCULINO'
#                         ws.write(a, 8, sexo)
#                         ws.write(a, 9, per[13], date_format)
#                         ws.write(a, 10, per[7])
#                         ws.write(a, 11, per[8])
#                         ws.write(a, 12, per[9])
#                         ws.write(a, 13, per[10] + (" MENCION " + per[20] if per[20] else ""))
#                         ws.write(a, 14, per[11])
#                         ws.write(a, 15, per[15])
#                         ws.write(a, 16, per[16])
#                         ws.write(a, 17, per[17])
#                         ws.write(a, 18, "SI" if per[19] else "NO")
#                         ws.write(a, 19, per[21])
#                         ws.write(a, 20, per[22])
#                         ws.write(a, 21, per[23])
#                         ws.write(a, 22, per[24])
#                         ws.write(a, 23, per[25])
#                         ws.write(a, 24, per[26] + ' ' + per[27])
#                         ws.write(a, 25, per[28])
#                         if per[29]:
#                             ws.write(a, 26, 'SI')
#                         else:
#                             ws.write(a, 26, 'NO')
#                     # ws.write(a+2, 0, 'Fecha:')
#                     # ws.write(a+2, 1, datetime.today(),date_format)
#                     ws.write_merge(a + 2, a + 2, 0, 1, datetime.today(), date_format)
#                     wb.save(response)
#                     return response
#                 except Exception as ex:
#                     pass
#
#             elif action == 'totalactividadesdocentes':
#                 try:
#                     periodo = request.GET['periodo']
#                     cursor = connection.cursor()
#                     response = HttpResponse(content_type="application/ms-excel")
#                     response['Content-Disposition'] = 'attachment; filename=listado_actividaddocente.xls'
#                     wb = xlwt.Workbook()
#                     ws = wb.add_sheet('Sheetname')
#                     estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
#                     ws.col(0).width = 1000
#                     ws.col(1).width = 3000
#                     ws.col(2).width = 10000
#                     ws.col(3).width = 4000
#                     ws.col(4).width = 10000
#                     ws.col(5).width = 0
#                     ws.col(6).width = 6000
#                     ws.col(7).width = 2000
#                     ws.col(8).width = 6000
#                     ws.col(9).width = 6000
#                     ws.write(0, 0, 'N.')
#                     ws.write(0, 1, 'CRITERIO')
#                     ws.write(0, 2, 'FACULTAD')
#                     ws.write(0, 3, 'CEDULA')
#                     ws.write(0, 4, 'APELLIDOS Y NOMBRES')
#                     ws.write(0, 5, 'USUARIO')
#                     ws.write(0, 6, 'ACTIVIDAD')
#                     ws.write(0, 7, 'HORAS')
#                     ws.write(0, 8, 'DEDICACION')
#                     ws.write(0, 9, u'CATEGORIZACIÓN')
#                     a = 0
#                     date_format = xlwt.XFStyle()
#                     date_format.num_format_str = 'yyyy/mm/dd'
#                     listaestudiante = "select 'Docencia' as criterio,coor.nombre as facultad,per.apellido1, per.apellido2 , per.nombres as docente," \
#                         "cri.nombre as actividad,detdis.horas,us.username, td.nombre,(select cat.nombre from sga_categorizaciondocente cat where cat.id=pro.categoria_id ), per.cedula " \
#                         "from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriodocenciaperiodo critd, " \
#                         "sga_tiempodedicaciondocente td, " \
#                         "sga_criteriodocencia cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us " \
#                         "where dis.profesor_id=pro.id " \
#                         "and td.id=dis.dedicacion_id " \
#                         "and pro.persona_id=per.id  " \
#                         "and per.usuario_id=us.id " \
#                         "and pro.coordinacion_id=coor.id " \
#                         "and dis.id=detdis.distributivo_id " \
#                         "and detdis.criteriodocenciaperiodo_id=critd.id " \
#                         "and critd.criterio_id=cri.id " \
#                         "and detdis.criteriodocenciaperiodo_id is not null " \
#                         "and dis.periodo_id='" + periodo + "' " \
#                         "union all " \
#                         "select 'Investigacion' as criterio,coor.nombre as facultad,per.apellido1 , per.apellido2, per.nombres as docente, " \
#                         "cri.nombre as actividad,detdis.horas,us.username , td.nombre,(select cat.nombre from sga_categorizaciondocente cat where cat.id=pro.categoria_id ), per.cedula " \
#                         "from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criterioinvestigacionperiodo critd, " \
#                         "sga_tiempodedicaciondocente td, " \
#                         "sga_criterioinvestigacion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us " \
#                         "where dis.profesor_id=pro.id  " \
#                         "and td.id=dis.dedicacion_id " \
#                         "and pro.persona_id=per.id " \
#                         "and per.usuario_id=us.id " \
#                         "and pro.coordinacion_id=coor.id " \
#                         "and dis.id=detdis.distributivo_id " \
#                         "and detdis.criterioinvestigacionperiodo_id=critd.id " \
#                         "and critd.criterio_id=cri.id " \
#                         "and detdis.criterioinvestigacionperiodo_id is not null " \
#                         "and dis.periodo_id='" + periodo + "' " \
#                         "union all " \
#                         "select 'Gestion' as criterio,coor.nombre as facultad,per.apellido1 , per.apellido2 , per.nombres as docente, " \
#                         "cri.nombre as actividad,detdis.horas,us.username , td.nombre,(select cat.nombre from sga_categorizaciondocente cat where cat.id=pro.categoria_id ), per.cedula " \
#                         "from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriogestionperiodo critd, " \
#                         "sga_tiempodedicaciondocente td, " \
#                         "sga_criteriogestion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us " \
#                         "where dis.profesor_id=pro.id " \
#                         "and td.id=dis.dedicacion_id  " \
#                         "and pro.persona_id=per.id " \
#                         "and per.usuario_id=us.id " \
#                         "and pro.coordinacion_id=coor.id " \
#                         "and dis.id=detdis.distributivo_id " \
#                         "and detdis.criteriogestionperiodo_id=critd.id " \
#                         "and critd.criterio_id=cri.id " \
#                         "and detdis.criteriogestionperiodo_id is not null " \
#                         "and dis.periodo_id='" + periodo + "';"
#                     cursor.execute(listaestudiante)
#                     results = cursor.fetchall()
#                     for per in results:
#                         a += 1
#                         ws.write(a, 0, a)
#                         ws.write(a, 1, per[0])
#                         ws.write(a, 2, per[1])
#                         ws.write(a, 3, per[10])
#                         ws.write(a, 4, per[2] + ' ' + per[3] + ' ' + per[4])
#                         ws.write(a, 5, per[7])
#                         ws.write(a, 6, per[5])
#                         ws.write(a, 7, per[6])
#                         ws.write(a, 8, per[8])
#                         ws.write(a, 9, per[9])
#                     wb.save(response)
#                     return response
#                 except Exception as ex:
#                     pass
#
#             elif action == 'totalactividadesdocentesmaterias':
#                 try:
#                     periodo = request.GET['periodo']
#                     cursor = connection.cursor()
#                     response = HttpResponse(content_type="application/ms-excel")
#                     response['Content-Disposition'] = 'attachment; filename=listado_actividaddocente.xls'
#                     wb = xlwt.Workbook()
#                     ws = wb.add_sheet('Sheetname')
#                     estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
#                     #ws.write_merge(0, 0, 0, 5, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
#                     ws.col(0).width = 10000
#                     ws.col(1).width = 4000
#                     ws.col(2).width = 4000
#                     ws.col(3).width = 2000
#                     ws.col(4).width = 6000
#                     ws.col(5).width = 2000
#                     ws.col(6).width = 10000
#                     ws.col(7).width = 3000
#                     ws.col(8).width = 3000
#                     ws.col(9).width = 6000
#                     ws.col(10).width = 6000
#                     ws.col(11).width = 4000
#                     ws.col(12).width = 6000
#                     ws.col(13).width = 4000
#                     ws.col(14).width = 10000
#                     ws.col(15).width = 10000
#                     ws.col(16).width = 5000
#                     ws.col(17).width = 5000
#                     ws.col(18).width = 5000
#                     ws.write(0, 0, 'CARRERA')
#                     ws.write(0, 1, 'SECCION')
#                     ws.write(0, 2, 'NIVEL')
#                     ws.write(0, 3, 'PARALELO')
#                     ws.write(0, 4, 'ACTIVIDADES/MATERIAS')
#                     ws.write(0, 5, 'HORAS')
#                     ws.write(0, 6, 'APELLIDOS Y NOMBRES')
#                     ws.write(0, 7, 'CRITERIO')
#                     ws.write(0, 8, 'CEDULA')
#                     ws.write(0, 9, 'CORREO INSTITUCIONAL')
#                     ws.write(0, 10, u'CATEGORIZACIÓN')
#                     ws.write(0, 11, 'DEDICACION')
#                     ws.write(0, 12, 'FACULTAD')
#                     ws.write(0, 13, 'TIPO PROFESOR')
#                     ws.write(0, 14, 'TITULO MASTER')
#                     ws.write(0, 15, 'TITULO PHD')
#                     ws.write(0, 16, 'ETNIA')
#                     ws.write(0, 17, 'SEXO')
#                     ws.write(0, 18, 'LGTBI')
#                     a = 0
#                     date_format = xlwt.XFStyle()
#                     date_format.num_format_str = 'yyyy/mm/dd'
#                     listaestudiante = "select 'Docencia' as criterio,coor.nombre as facultad,per.apellido1, per.apellido2 , per.nombres as docente, " \
#                                       "null,null as nivel,null, cri.nombre as actividad,detdis.horas,us.username, td.nombre, " \
#                                       "(select cat.nombre from sga_categorizaciondocente cat  " \
#                                       "where cat.id=dis.categoria_id ),null,per.cedula,per.emailinst,us.username, " \
#                                       "null as tipoprofesor,(SELECT array_to_string(array_agg(tit.nombre),',')   " \
#                                       "FROM sga_titulacion tc ,sga_titulo tit where tc.titulo_id=tit.id and tc.persona_id=per.id  " \
#                                       "and tit.nivel_id=4 and tit.grado_id=2 and tc.verificado=true) as master , " \
#                                       "(SELECT array_to_string(array_agg(tit.nombre),',') FROM sga_titulacion tc ,sga_titulo tit  " \
#                                       "where tc.titulo_id=tit.id and tc.persona_id=per.id and tit.nivel_id=4 and tit.grado_id=1 and tc.verificado=true) as phd," \
#                                       "(select (raza.nombre) from sga_perfilinscripcion perfil,sga_raza raza where perfil.raza_id=raza.id and perfil.persona_id=per.id and perfil.status=True)  as etnia,  " \
#                                       "(select nombre from sga_sexo sexo where sexo.id=per.sexo_id ) as sexo,per.lgtbi " \
#                                       "from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriodocenciaperiodo critd,  " \
#                                       "sga_tiempodedicaciondocente td,  " \
#                                       "sga_criteriodocencia cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us  " \
#                                       "where dis.profesor_id=pro.id  " \
#                                       "and td.id=dis.dedicacion_id  " \
#                                       "and pro.persona_id=per.id   " \
#                                       "and per.usuario_id=us.id  " \
#                                       "and dis.coordinacion_id=coor.id  " \
#                                       "and dis.id=detdis.distributivo_id  " \
#                                       "and detdis.criteriodocenciaperiodo_id=critd.id  " \
#                                       "and critd.criterio_id=cri.id  " \
#                                       "and detdis.criteriodocenciaperiodo_id is not null  " \
#                                       "and dis.periodo_id='" + periodo + "' and cri.id not in (15,16,17,18)  " \
#                                       "union all  " \
#                                       "select 'Investigacion' as criterio,coor.nombre as facultad,per.apellido1 , per.apellido2, per.nombres as docente,  " \
#                                       "null,null as nivel,null, cri.nombre as actividad,detdis.horas,us.username , td.nombre, " \
#                                       "(select cat.nombre from sga_categorizaciondocente cat where cat.id=dis.categoria_id ), " \
#                                       "null,per.cedula,per.emailinst,us.username,null as tipoprofesor,(SELECT array_to_string(array_agg(tit.nombre),',')  " \
#                                       "FROM sga_titulacion tc ,sga_titulo tit where tc.titulo_id=tit.id and tc.persona_id=per.id  " \
#                                       "and tit.nivel_id=4 and tit.grado_id=2 and tc.verificado=true) as master , " \
#                                       "(SELECT array_to_string(array_agg(tit.nombre),',') FROM sga_titulacion tc ,sga_titulo tit  " \
#                                       "where tc.titulo_id=tit.id and tc.persona_id=per.id and tit.nivel_id=4 and tit.grado_id=1 and tc.verificado=true) as phd,  " \
#                                       "(select (raza.nombre) from sga_perfilinscripcion perfil,sga_raza raza where perfil.raza_id=raza.id and perfil.persona_id=per.id and perfil.status=True)  as etnia,  " \
#                                      "(select nombre from sga_sexo sexo where sexo.id=per.sexo_id ) as sexo,per.lgtbi " \
#                                      "from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criterioinvestigacionperiodo critd,  " \
#                                       "sga_tiempodedicaciondocente td,  " \
#                                          "sga_criterioinvestigacion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us  " \
#                                          "where dis.profesor_id=pro.id   " \
#                                          "and td.id=dis.dedicacion_id  " \
#                                          "and pro.persona_id=per.id  " \
#                                          "and per.usuario_id=us.id  " \
#                                          "and dis.coordinacion_id=coor.id  " \
#                                          "and dis.id=detdis.distributivo_id  " \
#                                          "and detdis.criterioinvestigacionperiodo_id=critd.id  " \
#                                          "and critd.criterio_id=cri.id  " \
#                                          "and detdis.criterioinvestigacionperiodo_id is not null  " \
#                                          "and dis.periodo_id='" + periodo + "' " \
#                                          "union all  " \
#                                          "select 'Gestion' as criterio,coor.nombre as facultad,per.apellido1 , per.apellido2 , per.nombres as docente,  " \
#                                          "null,null as nivel,null, cri.nombre as actividad,detdis.horas,us.username , td.nombre, " \
#                                          "(select cat.nombre from sga_categorizaciondocente cat where cat.id=dis.categoria_id ),null, " \
#                                          "per.cedula,per.emailinst,us.username,null as tipoprofesor ,(SELECT array_to_string(array_agg(tit.nombre),',')  " \
#                                          "FROM sga_titulacion tc ,sga_titulo tit where tc.titulo_id=tit.id and tc.persona_id=per.id  " \
#                                          "and tit.nivel_id=4 and tit.grado_id=2 and tc.verificado=true) as master , " \
#                                          "(SELECT array_to_string(array_agg(tit.nombre),',') FROM sga_titulacion tc ,sga_titulo tit  " \
#                                          "where tc.titulo_id=tit.id and tc.persona_id=per.id and tit.nivel_id=4 and tit.grado_id=1 and tc.verificado=true) as phd,  " \
#                                          "(select (raza.nombre) from sga_perfilinscripcion perfil,sga_raza raza where perfil.raza_id=raza.id and perfil.persona_id=per.id and perfil.status=True)  as etnia, " \
#                                         "(select nombre from sga_sexo sexo where sexo.id=per.sexo_id ) as sexo,per.lgtbi " \
#                                         "from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriogestionperiodo critd,  " \
#                                          "sga_tiempodedicaciondocente td,  " \
#                                          "sga_criteriogestion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us  " \
#                                          "where dis.profesor_id=pro.id  " \
#                                          "and td.id=dis.dedicacion_id   " \
#                                          "and pro.persona_id=per.id  " \
#                                          "and per.usuario_id=us.id  " \
#                                          "and dis.coordinacion_id=coor.id  " \
#                                          "and dis.id=detdis.distributivo_id  " \
#                                          "and detdis.criteriogestionperiodo_id=critd.id  " \
#                                          "and critd.criterio_id=cri.id  " \
#                                          "and detdis.criteriogestionperiodo_id is not null  " \
#                                          "and dis.periodo_id='" + periodo + "' " \
#                                          "union all  " \
#                                          "select 'Materias' as criterio,coor.nombre as facultad,per.apellido1 , per.apellido2 , per.nombres as docente,  " \
#                                          "mat.paralelo,nmalla.nombre as nivel,carr.nombre as carreras, asig.nombre as actividad,mat.horassemanales,us.username ,  " \
#                                          "td.nombre,(select cat.nombre from sga_categorizaciondocente cat, sga_profesordistributivohoras dist " \
# 										  "where cat.id=dist.categoria_id and dist.periodo_id='" + periodo + "' and dist.profesor_id=pro.id ),ses.nombre as sesion, " \
#                                          "per.cedula,per.emailinst,us.username,tipro.nombre as tipoprofesor,(SELECT array_to_string(array_agg(tit.nombre),',')  " \
#                                          "FROM sga_titulacion tc ,sga_titulo tit where tc.titulo_id=tit.id and tc.persona_id=per.id  " \
#                                          "and tit.nivel_id=4 and tit.grado_id=2 and tc.verificado=true) as master , " \
#                                          "(SELECT array_to_string(array_agg(tit.nombre),',') FROM sga_titulacion tc ,sga_titulo tit  " \
#                                          "where tc.titulo_id=tit.id and tc.persona_id=per.id and tit.nivel_id=4 and tit.grado_id=1 and tc.verificado=true) as phd,  " \
#                                          "(select (raza.nombre) from sga_perfilinscripcion perfil,sga_raza raza where perfil.raza_id=raza.id and perfil.persona_id=per.id and perfil.status=True)  as etnia,  " \
#                                          "(select nombre from sga_sexo sexo where sexo.id=per.sexo_id ) as sexo,per.lgtbi " \
#                                          "from sga_profesormateria pmat,sga_materia mat,sga_nivel niv,sga_profesor pro,sga_persona per,  " \
#                                          "sga_asignaturamalla asimalla,sga_malla malla,sga_carrera carr,sga_asignatura asig,  " \
#                                          "sga_nivelmalla nmalla,auth_user us,sga_coordinacion_carrera corcar,sga_coordinacion coor,  " \
#                                          "sga_tiempodedicaciondocente td ,sga_sesion ses, sga_tipoprofesor tipro  " \
#                                          "where pmat.profesor_id=pro.id  " \
#                                          "and pro.persona_id=per.id   " \
#                                          "and per.usuario_id=us.id    " \
#                                          "and pro.dedicacion_id=td.id  " \
#                                          "and pmat.materia_id=mat.id  " \
#                                          "and mat.nivel_id=niv.id and niv.sesion_id=ses.id  " \
#                                          "and mat.asignaturamalla_id=asimalla.id  " \
#                                          "and asimalla.malla_id=malla.id  " \
#                                          "and malla.carrera_id=carr.id  " \
#                                          "and corcar.carrera_id=carr.id  " \
#                                          "and corcar.coordinacion_id=coor.id  " \
#                                          "and asimalla.asignatura_id=asig.id and asimalla.nivelmalla_id=nmalla.id and pmat.tipoprofesor_id=tipro.id  " \
#                                          "and niv.periodo_id='" + periodo + "' "
#                     cursor.execute(listaestudiante)
#                     results = cursor.fetchall()
#                     for per in results:
#                         a += 1
#                         ws.write(a, 0, per[7])
#                         ws.write(a, 1, per[13])
#                         ws.write(a, 2, per[6])
#                         ws.write(a, 3, per[5])
#                         ws.write(a, 4, per[8])
#                         ws.write(a, 5, per[9])
#                         ws.write(a, 6, per[2] + ' ' + per[3] + ' ' + per[4])
#                         ws.write(a, 7, per[0])
#                         ws.write(a, 8, per[14])
#                         ws.write(a, 9, per[16] + '@unemi.edu.ec')
#                         ws.write(a, 10, per[12])
#                         ws.write(a, 11, per[11])
#                         ws.write(a, 12, per[1])
#                         ws.write(a, 13, per[17])
#                         ws.write(a, 14, per[18])
#                         ws.write(a, 15, per[19])
#                         ws.write(a, 16, per[20])
#                         ws.write(a, 17, per[21])
#                         if per[22]:
#                             lgtbi = 'SI'
#                         else:
#                             lgtbi = 'NO'
#                         ws.write(a, 18, lgtbi)
#                     wb.save(response)
#                     return response
#                 except Exception as ex:
#                     pass
#
#             elif action == 'totalmatriculadossolomodulos':
#                 try:
#                     periodo = request.GET['periodo']
#                     cursor = connection.cursor()
#                     response = HttpResponse(content_type="application/ms-excel")
#                     response['Content-Disposition'] = 'attachment; filename=listado_alumnos.xls'
#                     wb = xlwt.Workbook()
#                     ws = wb.add_sheet('Sheetname')
#                     estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
#                     ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
#                     ws.col(0).width = 1000
#                     ws.col(1).width = 6000
#                     ws.col(2).width = 3000
#                     ws.col(3).width = 3000
#                     ws.col(4).width = 6000
#                     ws.col(5).width = 6000
#                     ws.col(6).width = 6000
#                     ws.col(7).width = 6000
#                     ws.col(8).width = 6000
#                     ws.col(9).width = 6000
#                     ws.col(10).width = 1000
#                     ws.write(4, 0, 'N.')
#                     ws.write(4, 1, 'PERIODO')
#                     ws.write(4, 2, 'NIVEL')
#                     ws.write(4, 3, 'SECCION')
#                     ws.write(4, 4, 'CEDULA')
#                     ws.write(4, 5, 'APELLIDOS')
#                     ws.write(4, 6, 'NOMBRES')
#                     ws.write(4, 7, 'SEXO')
#                     ws.write(4, 8, 'EMAIL')
#                     ws.write(4, 9, 'EMAILINST')
#                     ws.write(4, 10, 'COORDINACION')
#                     ws.write(4, 11, 'CARRERA')
#                     ws.write(4, 12, 'TELEFONO')
#                     a = 4
#                     date_format = xlwt.XFStyle()
#                     date_format.num_format_str = 'yyyy/mm/dd'
#                     listaestudiante = "select mat.id,per.nombre as periodo,nv.nombre as nivel,p.cedula,p.apellido1,p.apellido2,p.nombres,p.email,p.emailinst, " \
#                                       "coor.nombre as coordinacion,car.nombre as carrera, p.sexo_id as sexo,ses.nombre as sesion,p.telefono " \
#                                       "from sga_matricula mat,sga_inscripcion i,sga_persona p,sga_nivel n,sga_carrera car,sga_coordinacion coor, " \
#                                       "sga_coordinacion_carrera cca, sga_periodo per, sga_nivelmalla nv,sga_inscripcionnivel inniv,sga_sesion ses " \
#                                       "where mat.inscripcion_id=i.id and i.persona_id=p.id and mat.nivel_id=n.id and i.carrera_id=car.id and car.id=cca.carrera_id " \
#                                       "and cca.coordinacion_id=coor.id and n.periodo_id=per.id and i.id=inniv.inscripcion_id and inniv.nivel_id=nv.id " \
#                                       "and n.periodo_id='" + periodo + "' and i.sesion_id=ses.id and mat.id in(select ma.id from (select  mat.id as id,count(ma.materia_id)  as numero " \
#                                       "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma,sga_materia mate, " \
#                                       "sga_asignatura asi where mat.nivel_id=n.id and mat.id=ma.matricula_id " \
#                                       "and ma.materia_id=mate.id and mate.asignatura_id=asi.id and n.periodo_id='" + periodo + "' " \
#                                       "and asi.modulo=True group by mat.id) ma,(select  mat.id as id, count(ma.materia_id) as numero " \
#                                       "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma, " \
#                                       "sga_materia mate, sga_asignatura asi where mat.nivel_id=n.id and mat.id=ma.matricula_id " \
#                                       "and ma.materia_id=mate.id and mate.asignatura_id=asi.id and n.periodo_id='" + periodo + "' group by mat.id) mo " \
#                                       "where ma.id=mo.id and ma.numero=mo.numero);"
#                     cursor.execute(listaestudiante)
#                     results = cursor.fetchall()
#                     for per in results:
#                         a += 1
#                         ws.write(a, 0, a - 4)
#                         ws.write(a, 1, per[1])
#                         ws.write(a, 2, per[2])
#                         ws.write(a, 3, per[12])
#                         ws.write(a, 4, per[3])
#                         ws.write(a, 5, per[4] + ' ' + per[5])
#                         ws.write(a, 6, per[6])
#                         if per[11] == 1:
#                             sexo = 'FEMENINO'
#                         else:
#                             sexo = 'MASCULINO'
#                         ws.write(a, 7, sexo)
#                         ws.write(a, 8, per[7])
#                         ws.write(a, 9, per[8])
#                         ws.write(a, 10, per[9])
#                         ws.write(a, 11, per[10])
#                         ws.write(a, 12, per[13])
#                     # ws.write(a+2, 0, 'Fecha:')
#                     # ws.write(a+2, 1, datetime.today(),date_format)
#                     ws.write_merge(a + 2, a + 2, 0, 1, datetime.today(), date_format)
#                     wb.save(response)
#                     return response
#                 except Exception as ex:
#                     pass
#
#             return HttpResponseRedirect(request.path)
#         else:
#             r = False
#             data['title'] = u'Niveles académicos'
#             data['aprobacion_distributivo'] = APROBACION_DISTRIBUTIVO
#             periodo = request.session['periodo']
#             data['periodo'] = periodo
#             data['coordinaciones'] = persona.mis_coordinaciones()
#             # if persona.id in[825, 4471, 843, 813, 4462, 739, 28780, 26986, 27893, 26987, 2492, 1244, 26988, 26989, 26990, 26991, 26993, 26994, 26997, 26998, 28137, 29056]:
#             #     r = True
#             # if r == False:
#             #     return HttpResponseRedirect("/?info=No tiene permiso al modulo.")
#             return render(request, "adm_titulacion/view.html", data)
