# -*- coding: latin-1 -*-
from _decimal import Decimal
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.db.models import Sum
from django.template import Context
from django.template.loader import get_template
from decorators import secure_module, last_access
from inno.models import PeriodoMalla, DetallePeriodoMalla
from matricula.models import PeriodoMatricula
from sagest.models import TipoOtroRubro, Rubro
from settings import PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD, RUBRO_ARANCEL, RUBRO_MATRICULA, NOTA_ESTADO_EN_CURSO
from sga.commonviews import adduserdata, obtener_reporte, actualizar_nota_planificacion
from sga.funciones import null_to_decimal, variable_valor, log
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdfsaveqrcertificado, \
    conviert_html_to_pdfsaveqrsilabo
from sga.models import Matricula, MateriaAsignada, InscripcionMalla, AsignaturaMalla, Materia, \
    PeriodoGrupoSocioEconomico, Inscripcion, PerdidaGratuidad, AuditoriaNotas, AgregacionEliminacionMaterias, Silabo
from sga.templatetags.sga_extras import encrypt_alu
from django.db import connection, connections, transaction
from moodle import moodle


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    data['periodoseleccionado'] = periodoseleccionado = request.session['periodo']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    data['inscripcion'] = inscripcion = perfilprincipal.inscripcion
    periodo = request.session['periodo']

    # automatricula de pregrado
    confirmar_automatricula_pregrado = inscripcion.tiene_automatriculapregrado_por_confirmar(periodo)
    if confirmar_automatricula_pregrado:
        mat = inscripcion.mi_matricula_periodo(periodo.id)
        if mat.nivel.fechainicioagregacion > datetime.now().date():
            return HttpResponseRedirect("/?info=Estimado estudiante, se informa que el proceso de aceptación de matrícula empieza %s" % mat.nivel.fechainicioagregacion.__str__())
        if mat.nivel.fechafinagregacion < datetime.now().date():
            return HttpResponseRedirect("/?info=Estimado estudiante, el período de confirmación de la automatrícula ha culminado, usted no se encuentra matriculado")
        if PeriodoMatricula.objects.values("id").filter(periodo=periodo, status=True).exists():
            ePeriodoMatricula = PeriodoMatricula.objects.filter(periodo=periodo, status=True)[0]
            if not ePeriodoMatricula.activo:
                return HttpResponseRedirect("/?info=Estimado aspirante, se informa que el proceso de matrícula se encuentra inactivo")
        return HttpResponseRedirect("/alu_matricula/pregrado")

    # automatricula de admisión
    confirmar_automatricula_admision = inscripcion.tiene_automatriculaadmision_por_confirmar(periodo)
    if confirmar_automatricula_admision:
        mat = inscripcion.mi_matricula_periodo(periodo.id)
        if mat.nivel.fechainicioagregacion > datetime.now().date():
            return HttpResponseRedirect("/?info=Estimado aspirante, se informa que el proceso de aceptación de matrícula empieza %s" % mat.nivel.fechainicioagregacion.__str__())
        if mat.nivel.fechafinagregacion < datetime.now().date():
            return HttpResponseRedirect("/?info=Estimado aspirante, el período de confirmación de la automatrícula ha culminado, usted no se encuentra matriculado")
        if PeriodoMatricula.objects.values("id").filter(periodo=periodo, status=True).exists():
            ePeriodoMatricula = PeriodoMatricula.objects.filter(periodo=periodo, status=True)[0]
            if not ePeriodoMatricula.activo:
                return HttpResponseRedirect("/?info=Estimado estudiante, se informa que el proceso de matrícula se encuentra inactivo")
        return HttpResponseRedirect("/alu_matricula/admision")

    if request.method == 'POST':
        action = request.POST['action']
        if action == 'detalle_matricula':
            try:
                matricula = Matricula.objects.get(pk=int(request.POST['idmatricula']))
                cursor = connections['sga_select'].cursor()
                sql = "select am.nivelmalla_id, count(am.nivelmalla_id) as cantidad_materias_seleccionadas " \
                      " from sga_materiaasignada ma, sga_materia m, sga_asignaturamalla am where ma.status=true and ma.matricula_id=" + str(
                    matricula.id) + " and m.status=true and m.id=ma.materia_id and am.status=true and am.id=m.asignaturamalla_id GROUP by am.nivelmalla_id, am.malla_id order by count(am.nivelmalla_id) desc, am.nivelmalla_id desc limit 1;"
                cursor.execute(sql)
                results = cursor.fetchall()
                nivel = 0
                for per in results:
                    nivel = per[0]
                    cantidad_seleccionadas = per[1]
                cantidad_nivel = 0
                materiasnivel = []
                for asignaturamalla in AsignaturaMalla.objects.filter(nivelmalla__id=nivel, status=True, malla=matricula.inscripcion.mi_malla()):
                    if Materia.objects.filter(status=True,nivel__periodo=matricula.nivel.periodo, asignaturamalla=asignaturamalla).exists():
                        if matricula.inscripcion.estado_asignatura(asignaturamalla.asignatura) != 1:
                            cantidad_nivel += 1
                porcentaje_seleccionadas = int(round(Decimal((float(cantidad_nivel) * float(PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD)) / 100).quantize(Decimal('.00')), 0))
                cobro = 0
                if matricula.inscripcion.estado_gratuidad == 1 or matricula.inscripcion.estado_gratuidad == 2:
                    if (cantidad_seleccionadas < porcentaje_seleccionadas):
                        # mensaje = u"Estudiante irregular, se ha matriculado en menos de %s, debe cancelar por todas las asignaturas." % PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD
                        mensaje = f"Estudiante irregular, se ha matriculado en menos del {PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD}% porciento, debe cancelar por todas las asignaturas."
                        cobro = 1
                    else:
                        mensaje = u"Debe cancelar por las asignaturas que se matriculó por más de una vez."
                        cobro = 2
                else:
                    if matricula.inscripcion.estado_gratuidad == 2:
                        mensaje = u"Su estado es de pérdida parcial de la gratuidad. Debe cancelar por las asignaturas que se matriculó por más de una vez."
                        cobro = 2
                    else:
                        mensaje = u"Alumno Regular"
                        cobro = 3
                if matricula.inscripcion.persona.tiene_otro_titulo(inscripcion=matricula.inscripcion):
                    mensaje = ''
                    if matricula.inscripcion.persona.tiene_otro_titulo(inscripcion=matricula.inscripcion):
                        mensaje = u"El estudiante registra título  en otra IES Pública. Su estado es de pérdida total de la gratuidad. Debe cancelar por todas las asignaturas."
                    elif PerdidaGratuidad.objects.filter(inscripcion=matricula.inscripcion).exists():
                        mensaje = u"El estudiante registra perdida de gratuidad reportado por la SENESCYT. Su estado es de pérdida total de la gratuidad. Debe cancelar por todas las asignaturas."
                    cobro = 3
                if cobro > 0:
                    for materiaasignada in matricula.materiaasignada_set.filter(status=True):
                        if cobro == 1:
                            materiasnivel.append(materiaasignada.materia)
                        else:
                            if cobro == 2:
                                if materiaasignada.matriculas > 1:
                                    materiasnivel.append(materiaasignada.materia)
                            else:
                                materiasnivel.append(materiaasignada.materia)
                eGrupoSocioEconomico = matricula.matriculagruposocioeconomico() if matricula.matriculagruposocioeconomico() else None

                valorgrupo = 0
                if matricula.nivel.periodo.tipocalculo == 1:
                    ePeriodoGrupoSocioEconomico = PeriodoGrupoSocioEconomico.objects.filter(status=True, periodo=matricula.nivel.periodo, gruposocioeconomico=eGrupoSocioEconomico)[0]
                    valorgrupo = ePeriodoGrupoSocioEconomico.valor
                else:
                    malla = matricula.inscripcion.mi_malla()
                    if malla is None:
                        raise NameError(u"Malla sin configurar")
                    periodomalla = PeriodoMalla.objects.filter(periodo=matricula.nivel.periodo, malla=malla, status=True)
                    if not periodomalla.values("id").exists():
                        raise NameError(u"Malla no tiene configurado valores de cobro")
                    periodomalla = periodomalla[0]
                    detalleperiodomalla = DetallePeriodoMalla.objects.filter(periodomalla=periodomalla,
                                                                             gruposocioeconomico=eGrupoSocioEconomico,
                                                                             status=True
                                                                             )
                    if not detalleperiodomalla.values("id").exists():
                        raise NameError(u"Malla en grupo socioeconomico no tiene configurado valores de cobro")
                    valorgrupo = detalleperiodomalla[0].valor
                data['mensaje'] = mensaje
                data['valorgrupo'] = valorgrupo
                data['materiasnivel'] = materiasnivel
                data['matricula'] = matricula
                tiporubroarancel = TipoOtroRubro.objects.filter(pk=RUBRO_ARANCEL)[0]
                tiporubromatricula = TipoOtroRubro.objects.filter(pk=RUBRO_MATRICULA)[0]
                valorarancel = null_to_decimal(Rubro.objects.filter(matricula=matricula, status=True, tipo=tiporubroarancel).aggregate(valor=Sum('valortotal'))['valor'])
                valormatricula = null_to_decimal(Rubro.objects.filter(matricula=matricula, status=True, tipo=tiporubromatricula).aggregate(valor=Sum('valortotal'))['valor'])
                data['valorarancel'] = valorarancel
                data['valormatricula'] = valormatricula
                data['valorpagar'] = valorarancel + valormatricula
                template = get_template("matriculas/detalle_matricula.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'confirmar_materiaasignada':
            try:
                materiaasignada = MateriaAsignada.objects.get(pk=int(encrypt_alu(request.POST['idmateriaasignada'])))
                if not materiaasignada.automatricula:
                    materiaasignada.automatricula = True
                    materiaasignada.save(request)
                    if variable_valor('ENROLAR_INGLES'):
                        materiaasignada.materia.crear_actualizar_un_estudiante_curso(moodle, 1, materiaasignada.matricula)
                    log(u'Acepta auto matricula materia asignada: %s' % materiaasignada, request, "edit")
                return JsonResponse({"result": "ok", 'idcursomoodle': materiaasignada.materia.idcursomoodle})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        elif action == 'buscar_nota_ingles':
            try:
                data = {}
                data['inscritos'] = materiaasignada = MateriaAsignada.objects.filter(pk=int(encrypt_alu(request.POST['idmateriaasignada'])))
                data['materia'] = materiaasignada[0].materia
                template = get_template("alu_materias/notasmoodle.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'guardar_nota_ingles':
            try:
                alumno = MateriaAsignada.objects.get(pk=int(encrypt_alu(request.POST['idmateriaasignada'])))
                matricula = alumno.matricula
                if not alumno.materia.notas_de_moodle(alumno.matricula.inscripcion.persona):
                    raise NameError(u"Lo sentimos, no se encuentra notas del examen.")
                for notasmooc in alumno.materia.notas_de_moodle(alumno.matricula.inscripcion.persona):
                    campo = alumno.campo(notasmooc[1].upper())
                    if Decimal(notasmooc[0]) <= 0:
                        raise NameError(u"Lo sentimos, no se puede importar notas con cero.")
                    if type(notasmooc[0]) is Decimal:
                        if null_to_decimal(campo.valor) != float(notasmooc[0]) or (alumno.asistenciafinal < campo.detallemodeloevaluativo.modelo.asistenciaaprobar):
                            actualizar_nota_planificacion(alumno.id, notasmooc[1].upper(), notasmooc[0])
                            auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                                                            calificacion=notasmooc[0])
                            auditorianotas.save(request)
                    else:
                        if null_to_decimal(campo.valor) != float(0) or (alumno.asistenciafinal < campo.detallemodeloevaluativo.modelo.asistenciaaprobar):
                            actualizar_nota_planificacion(alumno.id, notasmooc[1].upper(), notasmooc[0])
                            auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False, calificacion=0)
                            auditorianotas.save(request)
                alumno.importa_nota = True
                alumno.cerrado = True
                alumno.fechacierre = datetime.now().date()
                alumno.save(request, actualiza=False)
                d = locals()
                exec(alumno.materia.modeloevaluativo.logicamodelo, globals(), d)
                d['calculo_modelo_evaluativo'](alumno)
                alumno.cierre_materia_asignada()
                if not matricula.inscripcion.modulos_ingles_mi_malla():
                    raise NameError(u"Su malla no tiene módulo configurados, por favor contáctese con su Director de carrera.")
                auxiliar_cupo = 0
                modulomalla = None
                if matricula.inscripcion.ultimo_modulo_ingles_pendiente():
                    modulomalla = matricula.inscripcion.ultimo_modulo_ingles_pendiente()
                    materias = Materia.objects.filter(status=True, nivel_id=658, asignatura=modulomalla.asignatura, inglesepunemi=True).exclude(id__in=[46031, 46032, 46033, 46034, 46035, 46036, 46037, 46038, 46039, 46040])
                    for materia in materias:
                        if materia.tiene_capacidad():
                            matriculas = 1
                            materiaasignada = None
                            matriculas = matricula.inscripcion.historicorecordacademico_set.filter(asignatura=materia.asignatura).count() + 1
                            if not MateriaAsignada.objects.filter(matricula=matricula, materia__asignatura=modulomalla.asignatura).exists():
                                materiaasignada = MateriaAsignada(matricula=matricula,
                                                                  materia=materia,
                                                                  notafinal=0,
                                                                  asistenciafinal=100,
                                                                  cerrado=False,
                                                                  matriculas=matriculas,
                                                                  observaciones='',
                                                                  estado_id=NOTA_ESTADO_EN_CURSO,
                                                                  automatricula=False,
                                                                  importa_nota=False,
                                                                  sinasistencia=True)
                                materiaasignada.save()
                                materiaasignada.evaluacion()
                                creditos = materiaasignada.materia.creditos
                                if materiaasignada.existe_modulo_en_malla():
                                    creditos = materiaasignada.materia_modulo_malla().creditos
                                registro = AgregacionEliminacionMaterias(matricula=matricula,
                                                                         agregacion=True,
                                                                         asignatura=materiaasignada.materia.asignatura,
                                                                         responsable=persona,
                                                                         fecha=datetime.now().date(),
                                                                         creditos=creditos,
                                                                         nivelmalla=materiaasignada.materia.nivel.nivelmalla if materiaasignada.materia.nivel.nivelmalla else None,
                                                                         matriculas=materiaasignada.matriculas)
                                registro.save()
                                if matriculas > 1 or matricula.inscripcion.persona.tiene_otro_titulo(matricula.inscripcion):
                                    matricula.calculo_matricula_ingles(materiaasignada)
                                auxiliar_cupo = 1
                                break
                else:
                    auxiliar_cupo = 1
                if auxiliar_cupo == 0:
                    raise NameError(u"Lo lamentamos, no hay cupo para el siguiente módulo de inglés: %s" % modulomalla.asignatura)
                log(u'Importa nota inglés %s' % alumno, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'friends':
                try:
                    if inscripcion.mi_coordinacion().id != 9:
                        data['title'] = u'Compañeros de mi clase'
                        data['materiasasignada'] = materiaasignada = MateriaAsignada.objects.get(pk=int(encrypt_alu(request.GET['id'])))
                        data['materiasasignadas'] = MateriaAsignada.objects.filter(materia__id=materiaasignada.materia.id).order_by("matricula__inscripcion__persona")
                        return render(request, "alu_materias/friends.html", data)
                except Exception as ex:
                    pass

            elif action == 'ver_actividades_sakai':
                try:
                    data['title'] = u'Actividades'
                    data['inscripcion'] = Inscripcion.objects.get(pk=int(encrypt_alu(request.GET['idinscripcion'])))
                    data['materia'] = Materia.objects.get(id=int(encrypt_alu(request.GET['idcurso'])))
                    return render(request, "alu_materias/ver_actividades_sakai.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Asignaturas de la matrícula'
                # if inscripcion.sesion_id == 13:
                #     return HttpResponseRedirect("/?info=Modulo bloqueado temporalmente.")

                if 'matriculaid' in request.GET:
                    if not Matricula.objects.db_manager("sga_select").filter(pk=int(encrypt_alu(request.GET['matriculaid'])), inscripcion=inscripcion).exists():
                        return HttpResponseRedirect("/?info=Matrícula no le pertence.")
                    data['matricula'] = matricula = Matricula.objects.db_manager("sga_select").filter(pk=int(encrypt_alu(request.GET['matriculaid'])), status=True, inscripcion=inscripcion).first()
                else:
                    # if variable_valor('VALIDA_ASISTENCIA_PAGO'):
                    #     matricula1 = Matricula.objects.filter(nivel__periodo=periodoseleccionado, estado_matricula__in=[2,3], inscripcion=inscripcion)
                    # else:
                    if periodoseleccionado:
                        matricula1 = Matricula.objects.db_manager("sga_select").filter(status=True, nivel__periodo_id=periodoseleccionado.id, inscripcion_id=inscripcion.id)
                    else:
                        matricula1 = None
                    if matricula1:
                        data['matricula'] = matricula = matricula1[0]
                    else:
                        data['matricula'] = matricula = inscripcion.ultima_matricula()
                if not matricula:
                    return HttpResponseRedirect("/?info=Ud. aún no se encuentra matriculado")
                data['matricula'] = matricula
                # data['matriculas'] = inscripcion.matricula_set.db_manager("sga_select").all()
                data['materiasasignadas'] = matricula.materiaasignada_set.db_manager("sga_select").filter(status=True).order_by('materia__inicio')
                data['reporte_0'] = obtener_reporte('certificado_promocion_alumno')
                data['malla'] = malla = InscripcionMalla.objects.db_manager("sga_select").get(inscripcion=inscripcion).malla
                data['valor_pendiente'] = matricula.total_saldo_rubro()
                data['valor_pagados'] = matricula.total_pagado_rubro()
                data['admision'] = not inscripcion.mi_coordinacion().id == 9
                data['periodotipo'] = False
                d = datetime.now()
                data['horasegundo'] = d.strftime('%Y%m%d_%H%M%S')
                # valorgrupo = PeriodoGrupoSocioEconomico.objects.db_manager("sga_select").values("valor").filter(status=True, periodo=matricula.nivel.periodo,gruposocioeconomico=matricula.matriculagruposocioeconomico())[0].get("valor") if PeriodoGrupoSocioEconomico.objects.filter(status=True, periodo=matricula.nivel.periodo,gruposocioeconomico=matricula.matriculagruposocioeconomico()).exists() else 0
                # data['valorgrupo'] = valorgrupo
                if periodoseleccionado.tipo.id == 2:
                    data['periodotipo'] = True
                contar_llenos = 0
                if malla.perfilegreso:
                    contar_llenos += 1
                if malla.perfilprofesional:
                    contar_llenos += 1
                if malla.objetivocarrera:
                    contar_llenos += 1
                if malla.misioncarrera:
                    contar_llenos += 1

                data['contar_llenos'] = contar_llenos
                if inscripcion.mi_coordinacion().id == 9:
                    # if inscripcion.carrera_id in [97,98,99,100,101,104,105]:
                    #     data['visualiza']  = False
                    # else:
                    data['visualiza'] = True
                    return render(request, "alu_materias/viewadmisionvirtual.html", data)
                elif inscripcion.modalidad_id == 3 and inscripcion.mi_coordinacion().id != 9:
                    return render(request, "alu_materias/viewpregradovirtual.html", data)
                else:
                    return render(request, "alu_materias/view.html", data)
            except Exception as ex:
                pass
