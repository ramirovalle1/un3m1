# -*- coding: latin-1 -*-
import json
import random
from xlwt import Workbook
from xlwt import *
from django.forms.models import model_to_dict
from django.template import Context
from django.template.loader import get_template
import sys
from settings import DEBUG
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction, connections
from django.db.models import Q, F, Sum, Count
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from inno.funciones import generar_clave_aleatoria
from inno.models import MatriculaSedeExamen, FechaPlanificacionSedeVirtualExamen, TurnoPlanificacionSedeVirtualExamen, \
    AulaPlanificacionSedeVirtualExamen, MateriaAsignadaPlanificacionSedeVirtualExamen, \
    AuditoriaMateriaAsignadaPlanificacionSedeVirtualExamen
from inno.runBackGround import ReportPlanificacionSedes, ReportHorariosExamenesSedes
from sga.commonviews import adduserdata, traerNotificaciones
from sga.funciones import log, puede_realizar_accion, MiPaginador, generar_nombre, null_to_decimal
from sga.models import Nivel, Materia, MateriaAsignada, SedeVirtual, LaboratorioVirtual, Notificacion, Malla, Matricula, \
    DetalleModeloEvaluativo, TipoAula, CoordinadorCarrera, Carrera, NivelMalla, Paralelo
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    periodo = request.session['periodo']
    persona = request.session['persona']
    hoy = datetime.now().date()
    if not persona.es_coordinadorcarrera_enlinea(request.session['periodo']) and not persona.usuario.is_superuser and not persona.grupos().values("id").filter(pk=143).exists():
        return HttpResponseRedirect(f"/adm_horarios?info=Acceso denegado")

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'actualizarCalificacion':
            try:
                if not 'idmap' in request.POST:
                    raise NameError(u"Parametro de materia asignada planificada no se encontro")
                if not 'iddmev' in request.POST:
                    raise NameError(u"Parametro de detalle de modelo evaluativo no se encontro")
                if not 'valor' in request.POST:
                    raise NameError(u"Parametro de calificación no se encontro")
                if not MateriaAsignadaPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=request.POST['idmap']):
                    raise NameError(u"Materia asignada planificada no se encontro")
                eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.get(pk=request.POST['idmap'])
                eDetalleModeloEvaluativos = eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada.materia.modeloevaluativo.campos()
                if not eDetalleModeloEvaluativos.values("id").filter(pk=request.POST['iddmev']).exists():
                    raise NameError(u"Detalle modelo evaluativo no se encontro")
                eDetalleModeloEvaluativo = eDetalleModeloEvaluativos.filter(pk=request.POST['iddmev']).first()
                valor = null_to_decimal(float(request.POST['valor']), eDetalleModeloEvaluativo.decimales)
                try:
                    if not valor:
                        valor = null_to_decimal(float(request.POST['valor']), eDetalleModeloEvaluativo.decimales)
                    if valor >= eDetalleModeloEvaluativo.notamaxima:
                        valor = eDetalleModeloEvaluativo.notamaxima
                    elif valor <= eDetalleModeloEvaluativo.notaminima:
                        valor = eDetalleModeloEvaluativo.notaminima
                except:
                    valor = eDetalleModeloEvaluativo.notaminima
                eMateriaAsignadaPlanificacionSedeVirtualExamen.calificacion = valor
                eMateriaAsignadaPlanificacionSedeVirtualExamen.save(request)
                isResult, message = eMateriaAsignadaPlanificacionSedeVirtualExamen.update_grade_grades()
                if not isResult:
                    raise NameError(message)
                eAuditoriaMateriaAsignadaPlanificacionSedeVirtualExamen = AuditoriaMateriaAsignadaPlanificacionSedeVirtualExamen(materiaasignadaplanificacion=eMateriaAsignadaPlanificacionSedeVirtualExamen,
                                                                                                                                 manual=False,
                                                                                                                                 calificacion=valor)
                eAuditoriaMateriaAsignadaPlanificacionSedeVirtualExamen.save(request)
                isResult, message = eAuditoriaMateriaAsignadaPlanificacionSedeVirtualExamen.update_grade_grades_history()
                if not isResult:
                    raise NameError(message)
                log(u'Registro de calificación (%s): %s de la Materia: %s de la Matricula: %s' % (eMateriaAsignadaPlanificacionSedeVirtualExamen.detallemodeloevaluativo.nombre, valor, eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada.materia, eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada.matricula), request, "add")
                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente los datos", "valor": valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'actualizarObservacion':
            try:
                if not 'idmap' in request.POST:
                    raise NameError(u"Parametro de materia asignada planificada no se encontro")
                if not 'iddmev' in request.POST:
                    raise NameError(u"Parametro de detalle de modelo evaluativo no se encontro")
                if not 'observacion' in request.POST:
                    raise NameError(u"Parametro de observación no se encontro")
                if not MateriaAsignadaPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=request.POST['idmap']):
                    raise NameError(u"Materia asignada planificada no se encontro")
                eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.get(pk=request.POST['idmap'])
                eDetalleModeloEvaluativos = eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada.materia.modeloevaluativo.campos()
                if not eDetalleModeloEvaluativos.values("id").filter(pk=request.POST['iddmev']).exists():
                    raise NameError(u"Detalle modelo evaluativo no se encontro")
                eDetalleModeloEvaluativo = eDetalleModeloEvaluativos.filter(pk=request.POST['iddmev']).first()
                observacion = request.POST['observacion']
                eMateriaAsignadaPlanificacionSedeVirtualExamen.observacion = observacion
                eMateriaAsignadaPlanificacionSedeVirtualExamen.save(request)
                isResult, message = eMateriaAsignadaPlanificacionSedeVirtualExamen.update_grade_grades()
                if not isResult:
                    raise NameError(message)
                eAuditoriaMateriaAsignadaPlanificacionSedeVirtualExamen = AuditoriaMateriaAsignadaPlanificacionSedeVirtualExamen(materiaasignadaplanificacion=eMateriaAsignadaPlanificacionSedeVirtualExamen,
                                                                                                                                 manual=False,
                                                                                                                                 observacion=observacion)
                eAuditoriaMateriaAsignadaPlanificacionSedeVirtualExamen.save(request)
                isResult, message = eAuditoriaMateriaAsignadaPlanificacionSedeVirtualExamen.update_grade_grades_history()
                if not isResult:
                    raise NameError(message)
                log(u'Registro de observación:%s del examen %s de la Materia: %s de la Matricula: %s' % (observacion, eMateriaAsignadaPlanificacionSedeVirtualExamen.detallemodeloevaluativo.nombre, eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada.materia, eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada.matricula), request, "add")
                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente los datos"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "message": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'listAlumnosPlanificacionExamenesSedes':
                try:
                    if not 'ids' in request.GET:
                        raise NameError(u"No existe parametro de sede")
                    if not 'idm' in request.GET:
                        raise NameError(u"No existe parametro de materia")
                    if not 'ids' in request.GET:
                        raise NameError(u"No existe parametro de tipo de aula")
                    if not Materia.objects.values("id").filter(pk=encrypt(request.GET['idm'])).exists():
                        raise NameError(u"No existe la materia")
                    if not SedeVirtual.objects.values("id").filter(pk=encrypt(request.GET['ids'])).exists():
                        raise NameError(u"No existe la sede")
                    if not TipoAula.objects.values("id").filter(pk=encrypt(request.GET['idt'])).exists():
                        raise NameError(u"No existe el tipo de aula")
                    data['eMateria'] = eMateria = Materia.objects.get(pk=encrypt(request.GET['idm']))
                    data['eSede'] = eSede = SedeVirtual.objects.get(pk=encrypt(request.GET['ids']))
                    data['eTipoAula'] = eTipoAula = TipoAula.objects.get(pk=encrypt(request.GET['idt']))
                    eDetalleModeloEvaluativos = eMateria.modeloevaluativo.campos_editarcalificacionmoodle()
                    eMateriaAsignadaPlanificacionSedeVirtualExamenes = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(materiaasignada__materia=eMateria,
                                                                                                                                    detallemodeloevaluativo_id__in=eDetalleModeloEvaluativos.values_list('id', flat=True),
                                                                                                                                    aulaplanificacion__turnoplanificacion__fechaplanificacion__periodo=periodo,
                                                                                                                                    aulaplanificacion__turnoplanificacion__fechaplanificacion__sede=eSede,
                                                                                                                                    aulaplanificacion__aula__tipo=eTipoAula
                                                                                                                                    )
                    data['eMateriaAsignadaPlanificacionSedeVirtualExamenes'] = eMateriaAsignadaPlanificacionSedeVirtualExamenes = eMateriaAsignadaPlanificacionSedeVirtualExamenes.order_by('materiaasignada__matricula__inscripcion__persona__apellido1', 'materiaasignada__matricula__inscripcion__persona__apellido2', 'materiaasignada__matricula__inscripcion__persona__nombres')
                    title = f'Listado de alumnos de la planificación reactivos en { eTipoAula.nombre.lower() }'
                    data['DEBUG'] = DEBUG
                    template = get_template("adm_horarios/resumen_sedes/materia/listadoalumnosplanificacionexamen.html")
                    return JsonResponse({"result": True, 'html': template.render(data), 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'rptCuadroCalificacionesSede':
                try:
                    if not 'ids' in request.GET:
                        raise NameError(u"No existe parametro de sede")
                    if not 'idm' in request.GET:
                        raise NameError(u"No existe parametro de materia")
                    if not 'ids' in request.GET:
                        raise NameError(u"No existe parametro de tipo de aula")
                    if not Materia.objects.values("id").filter(pk=encrypt(request.GET['idm'])).exists():
                        raise NameError(u"No existe la materia")
                    if not SedeVirtual.objects.values("id").filter(pk=encrypt(request.GET['ids'])).exists():
                        raise NameError(u"No existe la sede")
                    if not TipoAula.objects.values("id").filter(pk=encrypt(request.GET['idt'])).exists():
                        raise NameError(u"No existe el tipo de aula")
                    eMateria = Materia.objects.get(pk=encrypt(request.GET['idm']))
                    eProfesor = eMateria.profesor_principal_virtual()
                    eSede = SedeVirtual.objects.get(pk=encrypt(request.GET['ids']))
                    eTipoAula = TipoAula.objects.get(pk=encrypt(request.GET['idt']))
                    eDetalleModeloEvaluativos = eMateria.modeloevaluativo.campos_editarcalificacionmoodle()
                    eMateriaAsignadaPlanificacionSedeVirtualExamenes = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(materiaasignada__materia=eMateria,
                                                                                                                                    detallemodeloevaluativo_id__in=eDetalleModeloEvaluativos.values_list('id', flat=True),
                                                                                                                                    aulaplanificacion__turnoplanificacion__fechaplanificacion__periodo=periodo,
                                                                                                                                    aulaplanificacion__turnoplanificacion__fechaplanificacion__sede=eSede,
                                                                                                                                    aulaplanificacion__aula__tipo=eTipoAula
                                                                                                                                    )
                    borders = Borders()
                    borders.left = 1
                    borders.right = 1
                    borders.top = 1
                    borders.bottom = 1
                    titulo = easyxf('font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo2 = easyxf('font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                    fuentecabecera = easyxf('font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentemoneda = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right', num_format_str=' "$" #,##0.00')
                    fuentefecha = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center', num_format_str='yyyy-mm-dd')
                    fuentenumerodecimal = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right', num_format_str='#,##0.00')
                    fuentenumeroentero = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=CUADRO_NOTA_' + (eSede.alias if eSede.alias else eSede.nombre) + "_" + eTipoAula.nombre + "_" + eMateria.asignaturamalla.nivelmalla.__str__() + "_" + eMateria.asignatura.nombre + "_" + "_" + eMateria.paralelo + "_" + datetime.now().date().strftime("%d.%m.%Y") + "_" + random.randint(1, 10000).__str__() + '.xls'
                    ws = wb.add_sheet('cuadro_calificaciones')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 8, eMateria.asignaturamalla.malla.nombre_corto(), titulo2)
                    ws.write_merge(2, 2, 0, 8, eMateria.nombre_mostrar_sin_profesor(), titulo2)
                    ws.write_merge(3, 3, 0, 8, eProfesor.persona.nombre_completo_inverso() if eProfesor else 'SIN PROFESOR', titulo2)
                    ws.write_merge(4, 4, 0, 8, eSede.__str__(), titulo2)
                    ws.write_merge(5, 5, 0, 8, f'CUADRO DE CALIFICACIONES DE REACTIVOS {eTipoAula.nombre}', titulo2)
                    row_num = 7
                    columns = [
                        (u"#", 1000),
                        (u"ID", 6000),
                        (u"TIPO DOC.", 4000),
                        (u"DOCUMENTO", 3500),
                        (u"ALUMNO", 12000),
                        (u"ESTADO", 4000),
                        (u"ASISTENCIA", 6000),
                    ]
                    for eDetalleModeloEvaluativo in eDetalleModeloEvaluativos:
                        columns.append((u"%s" % eDetalleModeloEvaluativo.nombre, 3000))
                        columns.append((u"Retroalimentación", 20000))
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 7
                    fila = 0
                    eMateriaAsignadaPlanificacionSedeVirtualExamenes = eMateriaAsignadaPlanificacionSedeVirtualExamenes.order_by('materiaasignada__matricula__inscripcion__persona__apellido1', 'materiaasignada__matricula__inscripcion__persona__apellido2', 'materiaasignada__matricula__inscripcion__persona__nombres')
                    for eMateriaAsignadaPlanificacionSedeVirtualExamen in eMateriaAsignadaPlanificacionSedeVirtualExamenes:
                        row_num += 1
                        fila += 1
                        ePersona = eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada.matricula.inscripcion.persona
                        ws.write(row_num, 0, fila, fuentenormal)
                        ws.write(row_num, 1, encrypt(eMateriaAsignadaPlanificacionSedeVirtualExamen.pk), fuentenormal)
                        ws.write(row_num, 2, ePersona.tipo_documento(), fuentenormal)
                        ws.write(row_num, 3, ePersona.documento(), fuentenormal)
                        ws.write(row_num, 4, ePersona.nombre_completo_inverso(), fuentenormal)
                        ws.write(row_num, 5, eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada.estado.nombre, fuentenormal)
                        if eMateriaAsignadaPlanificacionSedeVirtualExamen.asistencia:
                            ws.write(row_num, 6, eMateriaAsignadaPlanificacionSedeVirtualExamen.fecha_asistencia, fuentefecha)
                        else:
                            ws.write(row_num, 6, "No se ha registrado asistencia", fuentenormal)
                        col_num = 6
                        for eDetalleModeloEvaluativo in eDetalleModeloEvaluativos:
                            col_num += 1
                            ws.write(row_num, col_num, "", fuentenormal)
                            col_num += 1
                            ws.write(row_num, col_num, "", fuentenormal)
                    wb.save(response)
                    return response
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?ida={encrypt(eMateria.id)}")

            return HttpResponseRedirect(request.path)
        else:
            try:
                if 'info' in request.GET:
                    data['info'] = request.GET['info']
                data['title'] = u'Resumen de examenes en sedes de carreras en línea'
                data['ePeriodo'] = periodo
                # eCoordinadorCarreras = CoordinadorCarrera.objects.values_list('carrera__id', flat=True).filter(periodo=periodo, persona=persona)
                # if eCoordinadorCarreras.values("id").filter(tipo__in=[1, 2]).exists():
                #     eCarreras = Carrera.objects.filter(pk__in=eCoordinadorCarreras.values_list('carrera__id', flat=True))
                if persona.usuario.is_superuser or persona.grupos().values("id").filter(pk=143).exists():
                    eCarreras = Carrera.objects.filter(coordinadorcarrera__periodo=periodo, modalidad=3).distinct()
                else:
                    eCarreras = Carrera.objects.filter(coordinadorcarrera__in=persona.gruposcarrera(periodo), modalidad=3).distinct()
                # miscoordinaciones = Carrera.objects.filter(grupocoordinadorcarrera__group__in=persona.grupos()).distinct()
                eMallas = Malla.objects.filter(carrera__in=eCarreras, modalidad_id=3)
                data['eMallas'] = eMallas
                if 'idm' in request.GET:
                    idm = int(encrypt(request.GET['idm']))
                    if not Malla.objects.filter(pk=idm):
                        raise NameError(u"Malla no encontrada")
                    eMalla = Malla.objects.get(pk=idm)
                    data['eMalla'] = eMalla
                    return render(request, "adm_horarios/resumen_sedes/malla/view.html", data)
                if 'idnm' in request.GET:
                    idnm = int(encrypt(request.GET['idnm']))
                    if not NivelMalla.objects.filter(pk=idnm):
                        raise NameError(u"Nivel de malla no encontrada")
                    eNivelMalla = NivelMalla.objects.get(pk=idnm)
                    if not 'id' in request.GET:
                        raise NameError(u"Malla no encontrada")
                    id = int(encrypt(request.GET['id']))
                    if not Malla.objects.filter(pk=id):
                        raise NameError(u"Malla no encontrada")
                    eMalla = Malla.objects.get(pk=id)
                    data['eNivelMalla'] = eNivelMalla
                    data['eMalla'] = eMalla
                    eParalelos = Paralelo.objects.filter(pk__in=Materia.objects.values_list('paralelomateria__id', flat=True).filter(nivel__periodo=periodo, asignaturamalla__malla=eMalla, asignaturamalla__nivelmalla=eNivelMalla)).distinct().order_by('id')
                    data['eParalelos'] = eParalelos
                    return render(request, "adm_horarios/resumen_sedes/nivelmalla/view.html", data)
                if 'idp' in request.GET:
                    idp = int(encrypt(request.GET['idp']))
                    if not Paralelo.objects.filter(pk=idp):
                        raise NameError(u"Paralelo no encontrado")
                    eParalelo = Paralelo.objects.get(pk=idp)
                    if not 'id' in request.GET:
                        raise NameError(u"Parametro no encontrado")
                    idnm , idm = (request.GET['id']).split('-')
                    idnm = int(encrypt(idnm))
                    if not NivelMalla.objects.filter(pk=idnm):
                        raise NameError(u"Nivel malla no encontrada")
                    eNivelMalla = NivelMalla.objects.get(pk=idnm)
                    idm = int(encrypt(idm))
                    if not Malla.objects.filter(pk=idm):
                        raise NameError(u"Malla no encontrada")
                    eMalla = Malla.objects.get(pk=idm)
                    data['eNivelMalla'] = eNivelMalla
                    data['eMalla'] = eMalla
                    eParalelos = Paralelo.objects.filter(pk__in=Materia.objects.values_list('paralelomateria__id', flat=True).filter(nivel__periodo=periodo, asignaturamalla__malla=eMalla, asignaturamalla__nivelmalla=eNivelMalla)).distinct().order_by('id')
                    data['eParalelos'] = eParalelos
                    data['eParalelo'] = eParalelo
                    data['eMaterias'] = Materia.objects.filter(nivel__periodo=periodo, asignaturamalla__malla=eMalla, asignaturamalla__nivelmalla=eNivelMalla, paralelomateria=eParalelo)

                    return render(request, "adm_horarios/resumen_sedes/paralelo/view.html", data)
                if 'ida' in request.GET:
                    ida = int(encrypt(request.GET['ida']))
                    if not Materia.objects.filter(pk=ida):
                        raise NameError(u"Materia no encontrado")
                    eMateria = Materia.objects.get(pk=ida)
                    eNivelMalla = eMateria.asignaturamalla.nivelmalla
                    eMalla = eMateria.asignaturamalla.malla
                    eParalelo = eMateria.paralelomateria
                    eParalelos = Paralelo.objects.filter(pk__in=Materia.objects.values_list('paralelomateria__id', flat=True).filter(nivel__periodo=periodo, asignaturamalla__malla=eMalla, asignaturamalla__nivelmalla=eNivelMalla)).distinct().order_by('id')
                    data['eNivelMalla'] = eNivelMalla
                    data['eMalla'] = eMalla
                    data['eParalelos'] = eParalelos
                    data['eParalelo'] = eParalelo
                    data['eMateria'] = eMateria
                    data['eMaterias'] = Materia.objects.filter(nivel__periodo=periodo, asignaturamalla__malla=eMalla, asignaturamalla__nivelmalla=eNivelMalla, paralelomateria=eParalelo)
                    eMateriaAsignadaPlanificacionSedeVirtualExamenes = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(materiaasignada__materia=eMateria, aulaplanificacion__turnoplanificacion__fechaplanificacion__periodo=periodo)
                    eSedes = SedeVirtual.objects.filter(pk__in=eMateriaAsignadaPlanificacionSedeVirtualExamenes.values_list('aulaplanificacion__turnoplanificacion__fechaplanificacion__sede__id', flat=True))
                    data['eSedes'] = eSedes
                    eTipoAulas = TipoAula.objects.filter(pk__in=eMateriaAsignadaPlanificacionSedeVirtualExamenes.values_list('aulaplanificacion__aula__tipo__id', flat=True))
                    aTipoAulas = []
                    for eTipoAula in eTipoAulas:
                        total = len(eMateriaAsignadaPlanificacionSedeVirtualExamenes.values("id").filter(aulaplanificacion__aula__tipo=eTipoAula))
                        aTipoAulas.append({'nombre': eTipoAula.nombre, 'total': total})
                    data['eTipoAulas'] = aTipoAulas
                    return render(request, "adm_horarios/resumen_sedes/materia/view.html", data)
                return render(request, "adm_horarios/resumen_sedes/panel.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                return render(request, "adm_horarios/error.html", data)
