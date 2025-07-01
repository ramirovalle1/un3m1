# -*- coding: UTF-8 -*-
import random
from datetime import datetime

import xlwt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.aggregates import Avg
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from xlwt import *

from decorators import secure_module, last_access
from settings import HOMITIRCAPACIDADHORARIO, CALCULO_POR_CREDITO, NOTA_ESTADO_EN_CURSO, MATRICULACION_LIBRE
from sga.commonviews import adduserdata, conflicto_materias_seleccionadas
from sga.forms import SolicitudForm, ConfiguracionTerceraMatriculaForm
from sga.funciones import MiPaginador, log, generar_nombre, fechatope, variable_valor
from sga.models import SolicitudMatricula, SolicitudDetalle, AsignaturaMalla, Asignatura, Matricula, Materia, \
    AgregacionEliminacionMaterias, MateriaAsignada, \
    Coordinacion, TipoSolicitud, ConfiguracionTerceraMatricula, Inscripcion, ProfesorMateria, GruposProfesorMateria, \
    AlumnosPracticaMateria
from sga.templatetags.sga_extras import encrypt


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
                solicitud = SolicitudMatricula.objects.get(pk=request.POST['id'])
                if int(request.POST['forma']) == 1:
                    solicitud.fechaaprueba = datetime.now()
                    solicitud.obseaprueba = request.POST['obsaprueba']
                    solicitud.personaaprueba=persona
                    solicitud.estadosolicitud=request.POST['estadosolicitud']
                elif int(request.POST['forma']) == 2:
                    solicitud.fechaapruebainforme = datetime.now()
                    solicitud.personaapruebainforme = persona
                    solicitud.obseinforme = request.POST['obsaprueba']
                solicitud.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'validaliterales':
            try:
                idinscripcion = request.POST['idinscripcion']
                tiposol = TipoSolicitud.objects.get(pk=request.POST['tiposolicitudid'])
                matricula = Matricula.objects.filter(inscripcion_id=idinscripcion,status=True).order_by('-id')[0]
                if tiposol.validar:
                    asignada = MateriaAsignada.objects.filter(matricula=matricula, status=True, materiaasignadaretiro__isnull=True)
                    numeroreprobadasnormales = asignada.values('id').filter(matriculas=1, estado_id__in=[2, 3, 4]).count()
                    numeroreprobadasterceras = asignada.values('id').filter(matriculas=2, estado_id__in=[2, 3, 4]).count()
                    if tiposol.id == 1:
                        if numeroreprobadasnormales == 0:
                            if numeroreprobadasterceras == 1:
                                totalpromedio = round(asignada.filter(matriculas=1).aggregate(promedio=Avg('notafinal'))['promedio'], 0)
                                if totalpromedio >= 75:
                                    result = {'result': 'ok'}
                                else:
                                    result = {'result': 'bad','mensaje': tiposol.descripcion + '<br><br>' + 'Su promedio de calificacion es menor a 75'}
                            else:
                                result = {'result': 'bad', 'mensaje': tiposol.descripcion + '<br><br>' + 'Tiene reprobada mas de una materia'}
                        else:
                            result = {'result': 'bad', 'mensaje': tiposol.descripcion + '<br><br>' + 'Tiene reprobada una materia o mas'}
                    else:
                        if tiposol.id == 2:
                            if numeroreprobadasnormales == 0:
                                if numeroreprobadasterceras == 1:
                                    totalasistencia = round(asignada.filter(matriculas=2).aggregate(promedio=Avg('asistenciafinal'))[
                                                                'promedio'])
                                    if totalasistencia >= 90:
                                        result = {'result': 'ok'}
                                    else:
                                        result = {'result': 'bad','mensaje': tiposol.descripcion + '<br><br>' + 'Su promedio de asistencia es menor a 90'}
                                else:
                                    result = {'result': 'bad', 'mensaje': tiposol.descripcion + '<br><br>' + 'Tiene reprobada mas de una materia'}
                            else:
                                result = {'result': 'bad', 'mensaje': tiposol.descripcion + '<br><br>' + 'Tiene reprobada una materia o mas'}
                else:
                    result = {'result': 'ok'}
                return JsonResponse(result)
            except Exception as ex:
                pass
                return JsonResponse({"result": "bad"})

        elif action == 'editsolicitud':
            try:
                if 'adjunto' in request.FILES:
                    newfile = request.FILES['adjunto']
                    extencion = newfile._name.split('.')
                    exte = extencion[1]
                    if newfile.size > 2194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error archivo mayor a 2Mb."})
                    if not exte == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf"})
                f = SolicitudForm(request.POST)
                solicitud = SolicitudMatricula.objects.get(pk=request.POST['id'])
                if f.is_valid():
                    solicitud.tiposolicitud = f.cleaned_data['tiposolicitud']
                    solicitud.descripcion = f.cleaned_data['descripcion']
                    solicitud.save(request)
                    if 'adjunto' in request.FILES:
                        newfile = request.FILES['adjunto']
                        newfile._name = generar_nombre("adjunto_", newfile._name)
                        solicitud.adjunto = newfile
                        solicitud.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addaperturafecha':
            try:
                f = ConfiguracionTerceraMatriculaForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['fechadesde']>=f.cleaned_data['fechahasta']:
                        return JsonResponse({"result": "bad", "mensaje": u"Fecha desde no puede ser mayor o igual que fecha hasta."})
                    if ConfiguracionTerceraMatricula.objects.values('id').filter(periodolectivo = f.cleaned_data['periodolectivo']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe el periodo en un registro de configuración."})
                    aperturafechas = ConfiguracionTerceraMatricula(fechaainicio = f.cleaned_data['fechadesde'],
                                                                   fechafin = f.cleaned_data['fechahasta'],
                                                                   nombre = f.cleaned_data['nombre'],
                                                                   activa = f.cleaned_data['activa'],
                                                                   periodolectivo = f.cleaned_data['periodolectivo'])
                    aperturafechas.save(request)
                    log(u'Adiciono apertura fecha 3ra. matricula: %s fecha inicio: %s fecha fin: %s periodo: %s - activo: %s' % (aperturafechas.nombre, aperturafechas.fechaainicio, aperturafechas.fechafin, aperturafechas.periodolectivo, aperturafechas.activa), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editaperturafecha':
            try:
                f = ConfiguracionTerceraMatriculaForm(request.POST)
                if f.is_valid():
                    aperturafechas = ConfiguracionTerceraMatricula.objects.get(pk=request.POST['id'])
                    if f.cleaned_data['fechadesde']>=f.cleaned_data['fechahasta']:
                        return JsonResponse({"result": "bad", "mensaje": u"Fecha desde no puede ser mayor o igual que fecha hasta."})
                    if ConfiguracionTerceraMatricula.objects.values('id').filter(periodolectivo = f.cleaned_data['periodolectivo']).exclude(id=aperturafechas.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe el periodo en un registro de configuración de tercera matriculas."})
                    aperturafechas.fechaainicio = f.cleaned_data['fechadesde']
                    aperturafechas.fechafin = f.cleaned_data['fechahasta']
                    aperturafechas.activa = f.cleaned_data['activa']
                    aperturafechas.nombre = f.cleaned_data['nombre']
                    aperturafechas.periodolectivo = f.cleaned_data['periodolectivo']
                    aperturafechas.save(request)
                    log(u'Modifico apertura fecha 3ra. matricula: %s fecha inicio: %s fecha fin: %s periodo %s activo: %s' % (aperturafechas.nombre,aperturafechas.fechaainicio,aperturafechas.fechafin,aperturafechas.periodolectivo,aperturafechas.activa), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'promotemateria':
            try:
                periodo = request.session['periodo']
                solicitud = SolicitudMatricula.objects.get(pk=int(request.POST['ids']))
                solicitud.matriculado = True
                if solicitud.estadosolicitud == 1:
                    solicitud.estadosolicitud = 2
                    solicitud.obseaprueba = 'Aprobado mediante Comisión Académica. Nota: Se asignó en la jornada que existe cupo disponible; usted debe acercarse a pagar el valor generado en un plazo de 24 horas laborales, caso contrario la matricula no es válida.'
                    solicitud.personaaprueba = persona
                solicitud.save(request)
                materia = Materia.objects.get(pk=int(request.POST['seleccionado']))
                solicituddetalle = SolicitudDetalle.objects.get(solicitudmatricula=solicitud, asignatura=materia.asignatura)
                solicituddetalle.matriculado = True
                solicituddetalle.save(request)
                # MATERIA PRACTICAS
                profesormateria = None
                grupoprofesormateria = None
                if materia.asignaturamalla.practicas:
                    if materia.asignaturamalla.malla.carrera.id.__str__() in variable_valor('LISTA_CARRERA_PARA_MATRICULA_GRUPO_PRACTICA'):
                        if not int(request.POST['selecpract']) > 0:
                            return JsonResponse({"result": "bad", "mensaje": u"Seleccione un horario de prácticas."})
                        else:
                            profesormateria = ProfesorMateria.objects.get(pk=int(request.POST['selecpract']), materia=materia)
                            if not int(request.POST['selecgrup']) > 0 and profesormateria.grupoprofesormateria():
                                return JsonResponse({"result": "bad", "mensaje": u"Seleccione un horario de prácticas."})
                            else:
                                if profesormateria.grupoprofesormateria():
                                    grupoprofesormateria = GruposProfesorMateria.objects.get(pk=int(request.POST['selecgrup']), profesormateria__materia=materia, profesormateria=profesormateria)
                                    profesormateria = None
                if Matricula.objects.values('id').filter(inscripcion=solicitud.inscripcion, nivel__periodo=periodo).exists():
                    matricula = Matricula.objects.get(inscripcion=solicitud.inscripcion, nivel__periodo=periodo)
                else:
                    if not solicitud.inscripcion.matriculado():
                        matricula = Matricula(inscripcion=solicitud.inscripcion,
                                              nivel=materia.nivel,
                                              pago=False,
                                              iece=False,
                                              becado=False,
                                              porcientobeca=0,
                                              fecha=datetime.now().date(),
                                              hora=datetime.now().time(),
                                              fechatope=fechatope(datetime.now().date()))
                        matricula.save(request)
                        # matricula.grupo_socio_economico()
                        # matriculagruposocioeconomico = matricula.matriculagruposocioeconomico_set.all()[0]
                        # matriculagruposocioeconomico.save()
                        matricula.confirmar_matricula()
                if MATRICULACION_LIBRE:
                    if not materia.tiene_capacidad():
                        return JsonResponse({"result": "bad", "mensaje": u"No existe cupo para esta materia"})
                    if grupoprofesormateria:
                        if not grupoprofesormateria.cuposdisponiblesgrupoprofesor() > 0:
                            return JsonResponse({"result": "bad", "mensaje": u"No existe cupo para en la practica"})
                if matricula.materiaasignada_set.values('id').filter(materia=materia).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra matriculado en esta materia"})
                materiaasignada = MateriaAsignada(matricula=matricula,
                                                  materia=materia,
                                                  notafinal=0,
                                                  asistenciafinal=0,
                                                  cerrado=False,
                                                  observaciones='',
                                                  estado_id=NOTA_ESTADO_EN_CURSO)
                materiaasignada.save(request)
                matricula.actualizar_horas_creditos()
                if profesormateria:
                    alumnopractica = AlumnosPracticaMateria(materiaasignada=materiaasignada,
                                                            profesormateria=profesormateria)
                    alumnopractica.save(request)
                    log(u'Materia (%s) con profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s)' % (materia, profesormateria, materiaasignada, alumnopractica.id), request, "add")
                elif grupoprofesormateria:
                    alumnopractica = AlumnosPracticaMateria(materiaasignada=materiaasignada,
                                                            profesormateria=grupoprofesormateria.profesormateria,
                                                            grupoprofesor=grupoprofesormateria)
                    alumnopractica.save(request)
                    log(u'Materia (%s) con grupo profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s) por modulo de 3ra matriculas' % ( materia, grupoprofesormateria, materiaasignada, alumnopractica.id), request, "add")
                conflicto = matricula.verificar_conflicto_en_materias()
                if conflicto:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": conflicto})
                materiaasignada.matriculas = materiaasignada.cantidad_matriculas()
                materiaasignada.asistencias()
                materiaasignada.evaluacion()
                materiaasignada.mis_planificaciones()
                materiaasignada.save(request)
                if matricula.nivel.nivelgrado:
                    log(u'Adiciono materia: %s' % materiaasignada, request, "add")
                else:
                    if datetime.now().date() < matricula.nivel.periodo.inicio_agregacion:
                        # AGREGACION DE MATERIAS EN MATRICULACION REGULAR SIN REALIZAR PAGOS
                        materiaasignada.save(request)
                        log(u'Adiciono materia: %s' % materiaasignada, request, "add")
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
                        registro.save(request)
                        log(u'Adiciono materia: %s' % materiaasignada, request, "add")
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
                            log(u'Adiciono materia: %s' % materiaasignada, request, "add")
                            if CALCULO_POR_CREDITO:
                                matricula.agregacion_aux(request)
                        else:
                            raise NameError('Error')
                materiaasignada.notificacion_3ra_matricula_materia(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al agregar la materia"})

        elif action == 'delaperturafecha':
            try:
                aperturafecha = ConfiguracionTerceraMatricula.objects.get(pk=int(encrypt(request.POST['id'])))
                if not aperturafecha.puede_eliminar():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, existen solicitudes."})
                log(u'Elimino apertura de fecha: %s(%s)' % (aperturafecha, aperturafecha.id), request, "del")
                aperturafecha.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'materiapractica':
            try:
                materia = Materia.objects.get(id=int(request.POST['mat']))
                inscripcion = Inscripcion.objects.get(pk=int(request.POST['idm']))
                # EXTRAMOS LOS DATOS DE LA MATERIA SELECCIONADA
                datos = materia.datos_practicas_materia(inscripcion)
                return JsonResponse({"result": "ok", "datos": datos})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'reporteexcel':
                try:
                    __author__ = 'Unemi'
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=exp_xls_post_part_' + random.randint(1, 10000).__str__() + '.xls'
                    tiposolicitud = request.GET['tipo']
                    columns = [
                        (u"FACULTAD", 8000),
                        (u"CARRERA", 8000),
                        (u"CEDULA", 3000),
                        (u"NOMBRES", 6000),
                        (u"ASIGNATURA", 6000),
                        (u"NIVEL", 3000),
                        (u"FECHA", 3000),
                        (u"ESTADO SOLICITUD", 4000),
                        (u"ESTADO MATRICULADO", 4000),
                        (u"LITERAL", 3000),
                        (u"OBSERVACION",8000),
                        (u"PERIODO",8000)
                    ]
                    row_num = 1
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    if tiposolicitud == '0':
                        results = SolicitudDetalle.objects.filter(status=True, solicitudmatricula__configuracionterceramatricula__periodolectivo=periodo).order_by('solicitudmatricula__inscripcion__persona__apellido1','solicitudmatricula__inscripcion__persona__apellido2')
                    else:
                        if tiposolicitud == '4':
                            results = SolicitudDetalle.objects.filter(solicitudmatricula__estadosolicitud=2, matriculado=False, status=True, solicitudmatricula__configuracionterceramatricula__periodolectivo=periodo).distinct()
                        else:
                            results = SolicitudDetalle.objects.filter(solicitudmatricula__estadosolicitud=tiposolicitud ,status=True, solicitudmatricula__configuracionterceramatricula__periodolectivo=periodo).order_by('solicitudmatricula__inscripcion__persona__apellido1', 'solicitudmatricula__inscripcion__persona__apellido2')
                    row_num = 2
                    for r in results:
                        i = 0
                        campo1 = r.solicitudmatricula.inscripcion.coordinacion.nombre
                        campo2 = r.solicitudmatricula.inscripcion.carrera.nombre
                        campo3 = r.solicitudmatricula.inscripcion.persona.cedula
                        campo4 = r.solicitudmatricula.inscripcion.persona.nombre_completo_inverso()
                        campo5 = r.asignatura.nombre
                        campo6 = ''
                        if AsignaturaMalla.objects.values('id').filter(asignatura=r.asignatura, malla=r.solicitudmatricula.inscripcion.malla_inscripcion().malla, status=True).exists():
                            asi = AsignaturaMalla.objects.get(asignatura=r.asignatura, malla=r.solicitudmatricula.inscripcion.malla_inscripcion().malla, status=True)
                            campo6 = asi.nivelmalla.nombre
                        campo7 = r.solicitudmatricula.fecha_creacion
                        campo8 = r.solicitudmatricula.get_estadosolicitud_display()
                        campo9 = r.solicitudmatricula.tiposolicitud.descripcion
                        estadomatriculado = r.matriculado
                        if estadomatriculado:
                            campo10 = 'MATRICULADO'
                        else:
                            campo10 = 'NO MATRICULADO'
                        campo11 = r.solicitudmatricula.obseinforme
                        campo12 = r.solicitudmatricula.configuracionterceramatricula.periodolectivo
                        ws.write(row_num, 0, campo1.__str__(), font_style2)
                        ws.write(row_num, 1, campo2.__str__(), font_style2)
                        ws.write(row_num, 2, campo3.__str__(), font_style2)
                        ws.write(row_num, 3, campo4.__str__(), font_style2)
                        ws.write(row_num, 4, campo5.__str__(), font_style2)
                        ws.write(row_num, 5, campo6.__str__(), font_style2)
                        ws.write(row_num, 6, campo7.__str__(), date_format)
                        ws.write(row_num, 7, campo8.__str__(), font_style2)
                        ws.write(row_num, 8, campo10.__str__(), font_style2)
                        ws.write(row_num, 9, campo9.__str__(), font_style2)
                        ws.write(row_num, 10, campo11.__str__(), font_style2)
                        ws.write(row_num, 11, campo12.__str__(), font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'verdetalle':
                try:
                    data = {}
                    solicitud = SolicitudMatricula.objects.get(pk=int(request.GET['id']))
                    data['solicitud'] = solicitud
                    data['materiassolicitud'] = SolicitudDetalle.objects.filter(solicitudmatricula=solicitud, status=True)
                    template = get_template("adm_solicitudmatricula/ultima/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'matricular':
                try:
                    data['title'] = u'Matricular - Solicitudes Matrícula por 3ra vez'
                    solicitud = SolicitudMatricula.objects.get(pk=int(request.GET['id']))
                    data['solicitud'] = solicitud
                    data['materiassolicitud'] = SolicitudDetalle.objects.filter(solicitudmatricula=solicitud, status=True)
                    return render(request, "adm_solicitudmatricula/ultima/matricular.html", data)
                except Exception as ex:
                    return render(request, "adm_solicitudmatricula/ultima/view.html", data)

            if action == 'promote':
                try:
                    data['title'] = u'Seleccionar materia para alumno'
                    data['asignatura'] = asignatura = Asignatura.objects.get(pk=request.GET['id'])
                    data['solicitud'] = SolicitudMatricula.objects.get(pk=int(request.GET['ids']))
                    data['periodo'] = periodo = request.session['periodo']
                    data['materias'] = Materia.objects.filter(asignatura=asignatura, nivel__periodo=periodo, cerrado=False, nivel__cerrado=False)
                    data['homitircapacidadhorario'] = HOMITIRCAPACIDADHORARIO
                    data['permiteagregaciones'] = True
                    return render(request, "adm_solicitudmatricula/ultima/promote.html", data)
                except Exception as ex:
                    pass

            if action == 'editsolicitud':
                try:
                    data['title'] = u'Editar Solicitud'
                    data['solicitud'] = solicitud = SolicitudMatricula.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = solicitud.inscripcion
                    form = SolicitudForm(initial={'tiposolicitud': solicitud.tiposolicitud,
                                                  'descripcion': solicitud.descripcion})
                    data['form'] = form
                    return render(request, "adm_solicitudmatricula/ultima/editsolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'detalle':
                try:
                    data = {}
                    solicitud = SolicitudMatricula.objects.get(pk=int(request.GET['id']))
                    data['solicitud'] = solicitud
                    data['materiassolicitud'] = SolicitudDetalle.objects.filter(solicitudmatricula=solicitud,status=True)
                    template = get_template("adm_solicitudmatricula/ultima/detalle_aprobar.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'aperturafecha':
                try:
                    data['title'] = u'Apertura fecha 3ra. matrícula'
                    data['fechas'] = ConfiguracionTerceraMatricula.objects.filter(status=True)
                    return render(request, "adm_solicitudmatricula/ultima/aperturafechas.html", data)
                except Exception as ex:
                    pass

            elif action == 'addaperturafecha':
                try:
                    data['title'] = u'Adicionar fechas de apertura'
                    data['form'] =  ConfiguracionTerceraMatriculaForm()
                    return render(request, "adm_solicitudmatricula/ultima/addaperturafecha.html", data)
                except Exception as ex:
                    pass

            elif action == 'editaperturafecha':
                try:
                    data['title'] = u'Editar fechas de aperturas'
                    data['aperturafechas'] = configuracion = ConfiguracionTerceraMatricula.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = ConfiguracionTerceraMatriculaForm(initial={'fechadesde': configuracion.fechaainicio,
                                                                      'fechahasta': configuracion.fechafin,
                                                                      'periodolectivo': configuracion.periodolectivo,
                                                                      'activa': configuracion.activa,
                                                                      'nombre': configuracion.nombre})
                    data['form'] = form
                    return render(request, "adm_solicitudmatricula/ultima/editaperturafecha.html", data)
                except Exception as ex:
                    pass

            elif action == 'delaperturafecha':
                try:
                    data['title'] = u'Eliminar apertura de fecha'
                    data['aperturafechas'] = ConfiguracionTerceraMatricula.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_solicitudmatricula/ultima/delaperturafecha.html", data)
                except Exception as ex:
                    pass

            elif action == 'informe':
                try:
                    data = {}
                    solicitud = SolicitudMatricula.objects.get(pk=int(request.GET['id']))
                    data['solicitud'] = solicitud
                    data['materiassolicitud'] = SolicitudDetalle.objects.filter(solicitudmatricula=solicitud,status=True)
                    template = get_template("adm_solicitudmatricula/ultima/informe.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Solicitudes Matrícula por 3ra vez'
            search = None
            search1 = 0
            searchcoor = None
            searchliteral = None
            ids = None
            inscripcionid = None
            idliterales = None
            # if puede_realizar_accion_afirmativo(request, 'sga.puede_matricula_tercera_vice'):
            #     idliterales = variable_valor('MATRICULA_TERCERAVICE')
            # if puede_realizar_accion_afirmativo(request, 'sga.puede_matricula_tercera_bie'):
            #     idliterales = variable_valor('MATRICULA_TERCERABIE')
            # if idliterales:
            #     listaliterales = TipoSolicitud.objects.filter(status=True, id__in=idliterales).order_by('descripcion')
            # else:
            listaliterales = TipoSolicitud.objects.filter(status=True).order_by('descripcion')
            if 'id' in request.GET:
                ids = request.GET['id']
                solicitudmatriculas = SolicitudMatricula.objects.filter(pk=ids, tiposolicitud_id__in=listaliterales, status=True, configuracionterceramatricula__periodolectivo=periodo)
            if 's' in request.GET:
                search = request.GET['s']
                if 'tipo' in request.GET:
                    search1 = int(request.GET['tipo'])
                    if search1 != 0:
                        if ' ' in search:
                            s = search.split(" ")
                            if search1 == 4:
                                detallesolicitud = SolicitudDetalle.objects.values_list('solicitudmatricula_id').filter(Q(solicitudmatricula__inscripcion__persona__apellido1__contains=s[0]) & Q(solicitudmatricula__inscripcion__persona__apellido2__contains=s[1]),matriculado=False, status=True)
                                solicitudmatriculas = SolicitudMatricula.objects.filter(pk__in=detallesolicitud, tiposolicitud_id__in=listaliterales, estadosolicitud=2, status=True, configuracionterceramatricula__periodolectivo=periodo)
                            else:
                                solicitudmatriculas = SolicitudMatricula.objects.filter(Q(inscripcion__persona__apellido1__contains=s[0]) & Q(inscripcion__persona__apellido2__contains=s[1]), estadosolicitud=search1,tiposolicitud_id__in=listaliterales, status=True, configuracionterceramatricula__periodolectivo=periodo)
                        else:
                            if search1 == 4:
                                detallesolicitud = SolicitudDetalle.objects.values_list('solicitudmatricula_id').filter(Q(inscripcion__persona__nombres__contains=search) | Q(inscripcion__persona__apellido1__contains=search) | Q(inscripcion__persona__apellido2__contains=search) | Q(inscripcion__persona__cedula__contains=search),matriculado=False, status=True)
                                solicitudmatriculas = SolicitudMatricula.objects.filter(pk__in=detallesolicitud, estadosolicitud=2, tiposolicitud_id__in=listaliterales, status=True, configuracionterceramatricula__periodolectivo=periodo)
                            else:
                                solicitudmatriculas = SolicitudMatricula.objects.filter(Q(inscripcion__persona__nombres__contains=search) | Q(inscripcion__persona__apellido1__contains=search) | Q(inscripcion__persona__apellido2__contains=search) | Q(inscripcion__persona__cedula__contains=search), estadosolicitud=search1, tiposolicitud_id__in=listaliterales, status=True, configuracionterceramatricula__periodolectivo=periodo)
                    else:
                        if ' ' in search:
                            s = search.split(" ")
                            solicitudmatriculas = SolicitudMatricula.objects.filter(Q(inscripcion__persona__apellido1__contains=s[0]) & Q(inscripcion__persona__apellido2__contains=s[1]), tiposolicitud_id__in=listaliterales, status=True, configuracionterceramatricula__periodolectivo=periodo)
                        else:
                            solicitudmatriculas = SolicitudMatricula.objects.filter(Q(inscripcion__persona__nombres__contains=search) | Q(inscripcion__persona__apellido1__contains=search) | Q(inscripcion__persona__apellido2__contains=search) | Q(inscripcion__persona__cedula__contains=search), tiposolicitud_id__in=listaliterales, status=True, configuracionterceramatricula__periodolectivo=periodo)
                else:
                    if ' ' in search:
                        s = search.split(" ")
                        solicitudmatriculas = SolicitudMatricula.objects.filter(Q(inscripcion__persona__apellido1__contains=s[0]) & Q(inscripcion__persona__apellido2__contains=s[1]),tiposolicitud_id__in=listaliterales, status=True, configuracionterceramatricula__periodolectivo=periodo)
                    else:
                        solicitudmatriculas = SolicitudMatricula.objects.filter(Q(inscripcion__persona__nombres__contains=search) | Q(inscripcion__persona__apellido1__contains=search) | Q(inscripcion__persona__apellido2__contains=search) | Q(inscripcion__persona__cedula__contains=search), tiposolicitud_id__in=listaliterales, status=True, configuracionterceramatricula__periodolectivo=periodo)

            else:
                if 'tipo' in request.GET:
                    search1 = int(request.GET['tipo'])
                    if search1 != 0:
                        if search1==4:
                            detallesolicitud = SolicitudDetalle.objects.values_list('solicitudmatricula_id').filter(matriculado=False, status=True)
                            solicitudmatriculas = SolicitudMatricula.objects.filter(pk__in=detallesolicitud,estadosolicitud=2, tiposolicitud_id__in=listaliterales, status=True, configuracionterceramatricula__periodolectivo=periodo)
                        else:
                            solicitudmatriculas = SolicitudMatricula.objects.filter(estadosolicitud=search1, tiposolicitud_id__in=listaliterales, status=True, configuracionterceramatricula__periodolectivo=periodo)
                    else:
                        solicitudmatriculas = SolicitudMatricula.objects.filter(tiposolicitud_id__in=listaliterales, status=True, configuracionterceramatricula__periodolectivo=periodo)
                else:
                    if 'idcoordinacion' in request.GET:
                        searchcoor = int(request.GET['idcoordinacion'])
                        if searchcoor != 0:
                            solicitudmatriculas = SolicitudMatricula.objects.filter(inscripcion__coordinacion=searchcoor, tiposolicitud_id__in=listaliterales, status=True, configuracionterceramatricula__periodolectivo=periodo)
                        else:
                            solicitudmatriculas = SolicitudMatricula.objects.filter(tiposolicitud_id__in=listaliterales, status=True, configuracionterceramatricula__periodolectivo=periodo)
                    else:
                        if 'idliteral' in request.GET:
                            searchliteral = int(request.GET['idliteral'])
                            if searchliteral != 0:
                                solicitudmatriculas = SolicitudMatricula.objects.filter(tiposolicitud_id=searchliteral, status=True, configuracionterceramatricula__periodolectivo=periodo)
                            else:
                                solicitudmatriculas = SolicitudMatricula.objects.filter(tiposolicitud_id__in=listaliterales, status=True, configuracionterceramatricula__periodolectivo=periodo)
                        else:
                            solicitudmatriculas = SolicitudMatricula.objects.filter(tiposolicitud_id__in=listaliterales, status=True, configuracionterceramatricula__periodolectivo=periodo)
            solicitudmatriculas = solicitudmatriculas.order_by('-fecha_creacion')
            paging = MiPaginador(solicitudmatriculas, 25)
            listacoordinacion = Coordinacion.objects.filter(pk__in=SolicitudMatricula.objects.values_list('inscripcion__coordinacion__id').filter(status=True).distinct('inscripcion__coordinacion__id').order_by('inscripcion__coordinacion__id')).order_by('nombre')
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
            data['solicitudmatriculas'] = page.object_list
            data['search'] = search if search else ""
            data['search1'] = search1
            data['searchcoor'] = searchcoor
            data['searchliteral'] = searchliteral
            data['listacoordinacion'] = listacoordinacion
            data['listaliterales'] = listaliterales
            data['ids'] = ids if ids else ""
            return render(request, "adm_solicitudmatricula/ultima/view.html", data)
