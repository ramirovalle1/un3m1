# -*- coding: UTF-8 -*-
import json
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from decorators import secure_module, last_access
from sagest.models import Rubro
from settings import MAXIMO_MATERIA_ONLINE
from settings import UTILIZA_NIVEL0_PROPEDEUTICO, MATRICULACION_LIBRE, HOMITIRCAPACIDADHORARIO, CALCULO_POR_CREDITO, \
    MATRICULACION_POR_NIVEL, UTILIZA_GRUPOS_ALUMNOS, UTILIZA_GRATUIDADES, PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD, \
    PORCIENTO_PERDIDA_TOTAL_GRATUIDAD, NOTIFICA_ELIMINACION_MATERIA, NOTA_ESTADO_EN_CURSO, \
    FINANCIERO_GROUP_ID, SECRETARIA_GROUP_ID, MATRICULAR_CON_DEUDA, USA_EVALUACION_INTEGRAL, MATRICULAS_SOLO_TERCERAS, CANTIDAD_MATRICULAS_MAXIMAS, \
    USA_RETIRO_MATERIA, USA_RETIRO_MATRICULA
from sga.commonviews import adduserdata, obtener_reporte, actualizar_nota, materias_abiertas, matricular, \
    conflicto_materias_seleccionadas, contar_nivel, matricular_admision, get_user_info
from sga.forms import RetiradoMatriculaForm, MatriculaMultipleForm, MoverMatriculaNivelForm, \
    HomologacionInscripcionForm, ConvalidacionInscripcionForm, RetiradoMateriaForm, CambioFechaAsignacionMateriaForm
from sga.funciones import log, tituloinstitucion, MiPaginador, lista_correo, puede_realizar_accion, variable_valor, notificacion_masivo_grupo
from sga.models import Nivel, Carrera, Sede, Matricula, MateriaAsignada, RecordAcademico, Materia, Asignatura, \
    Inscripcion,RetiroMatricula, AgregacionEliminacionMaterias, MateriaAsignadaRetiro, HomologacionInscripcion, \
    ConvalidacionInscripcion, MateriaAsignadaConvalidacion, MateriaAsignadaHomologacion, CUENTAS_CORREOS, EvaluacionGenerica, \
    DetalleModeloEvaluativo, ModeloEvaluativo, Persona, DetalleModificacionNota
from sga.tasks import send_html_mail, conectar_cuenta

unicode=str

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['personasesion'] = persona = request.session['persona']
    data['periodo'] = periodo = request.session['periodo']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'deudavencida':
                try:
                    inscripcion = Inscripcion.objects.get(pk=request.POST['iid'])
                    deuda = inscripcion.adeuda_a_la_fecha()
                    if deuda > 0:
                        result = {'result': 'bad', 'deuda': deuda}
                    else:
                        result = {'result': 'ok', 'deuda': deuda}
                    return JsonResponse(result)
                except Exception as ex:
                    pass
                    return JsonResponse({"result": "bad"})

            elif action == 'promotemateria':
                try:
                    matricula = Matricula.objects.get(pk=int(request.POST['idma']))
                    materia = Materia.objects.get(pk=int(request.POST['seleccionado']))
                    if matricula.inscripcion.existe_en_malla(materia.asignatura) and not matricula.inscripcion.puede_tomar_materia(materia.asignatura):
                        return JsonResponse({"result": "bad", "mensaje": u"No puede tomar esta materia por tener precedencias"})
                    if matricula.inscripcion.existe_en_modulos(materia.asignatura) and not matricula.inscripcion.puede_tomar_materia_modulo(materia.asignatura):
                        return JsonResponse({"result": "bad", "mensaje": u"No puede tomar esta materia por tener precedencias"})
                    if MATRICULACION_LIBRE:
                        if not materia.tiene_capacidad():
                            return JsonResponse({"result": "bad", "mensaje": u"No existe cupo para esta materia"})
                    if matricula.materiaasignada_set.filter(materia=materia).exists():
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
                    materias = Materia.objects.filter(id__in=[x.materia.id for x in matricula.materiaasignada_set.filter(sinasistencia=False)])
                    conflicto = conflicto_materias_seleccionadas(materias)
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
                                matricula.calcular_rubros_matricula()
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
                            log(u'Adiciono materia: %s' % registro, request, "add")
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
                                registro.save(request)
                                log(u'Adiciono materia: %s' % registro, request, "add")
                                if CALCULO_POR_CREDITO:
                                    matricula.agregacion_aux(request)
                            else:
                                 raise NameError('Error')
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al agregar la materia"})


            elif action == 'conflictohorario':
                mismaterias = json.loads(request.POST['mismaterias'])
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                excluidas = Asignatura.objects.filter(historicorecordacademico__inscripcion=inscripcion,
                                                      historicorecordacademico__aprobada=False,
                                                      historicorecordacademico__sinasistencia=True).distinct()
                materias = Materia.objects.filter(id__in=[int(x) for x in mismaterias]).exclude(asignatura__id__in=excluidas)
                nivel = contar_nivel(mismaterias)
                conflicto = conflicto_materias_seleccionadas(materias)
                if conflicto:
                    return JsonResponse({"result": "bad", "mensaje": conflicto})
                return JsonResponse({"result": "ok", "nivel": nivel})

            elif action == 'conflictohorario_aux':
                nivel = 0
                mismaterias = json.loads(request.POST['mismaterias'])
                if len(mismaterias) > 0:
                    nivel = contar_nivel(mismaterias)
                return JsonResponse({"result": "ok", "nivel": nivel})

            elif action == 'addmatriculamulti':
                try:
                    form = MatriculaMultipleForm(request.POST)
                    f = form
                    if f.is_valid():
                        nivel = Nivel.objects.get(pk=request.POST['nivelrpocedencia'])
                        fecha = datetime.now().date()
                        if fecha > nivel.fechatopematriculaes:
                            return JsonResponse({"result": "bad", "mensaje": u"Fuera de rago de fecha de matriculacion extraordinaria."})
                        if nivel.matricula_set.all().count() >= nivel.capacidadmatricula:
                            return JsonResponse({"result": "bad", "mensaje": u"Limite de matriculas para el paralelo."})
                        lista = request.POST.getlist('ins')
                        for inscripcion_id in lista:
                            inscripcion = Inscripcion.objects.get(pk=int(inscripcion_id))
                            if not inscripcion.matriculado():
                                if inscripcion.persona.tiene_deuda():
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": "bad", "mensaje": u"El estudiante: " + unicode(inscripcion.persona.nombre_completo()) + " Tiene rubros pendientes de pago."})
                                if inscripcion.tiene_perdida_carrera():
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": "bad", "mensaje": u"El estudiante: " + unicode(inscripcion.persona.nombre_completo()) + " tiene perdida de carrera."})
                                matricula = Matricula(inscripcion=inscripcion,
                                                      nivel=nivel,
                                                      pago=False,
                                                      iece=False,
                                                      becado=False,
                                                      porcientobeca=0,
                                                      fecha=datetime.now().date(),
                                                      hora=datetime.now().time())
                                matricula.save(request)
                                log(u'Adiciono matricula multiple: %s' % matricula, request, "add")
                                nivel = matricula.nivel
                                materias = nivel.materia_set.filter(Q(cerrado=False) | Q(cerrado=None))
                                inscripcion = matricula.inscripcion
                                tercera = inscripcion.tiene_tercera_matricula()
                                for materia in materias:
                                    if not inscripcion.ya_aprobada(materia.asignatura) and inscripcion.puede_tomar_materia(materia.asignatura):
                                        adicionar = True
                                        if tercera and MATRICULAS_SOLO_TERCERAS:
                                            if not inscripcion.cantidad_matriculas(materia.asignatura) == CANTIDAD_MATRICULAS_MAXIMAS:
                                                adicionar = False
                                        if adicionar:
                                            materiaasignada = MateriaAsignada(matricula=matricula,
                                                                              materia=materia,
                                                                              notafinal=0,
                                                                              cerrado=False,
                                                                              asistenciafinal=0,
                                                                              observaciones='',
                                                                              estado_id=NOTA_ESTADO_EN_CURSO)
                                            materiaasignada.save(request)
                                            log(u'Adiciono materia asignada: %s' % materiaasignada, request, "add")
                                            materiaasignada.matriculas = materiaasignada.cantidad_matriculas()
                                            materiaasignada.save(request)
                                            materiaasignada.evaluacion()
                                            materiaasignada.asistencias()
                                            materiaasignada.mis_planificaciones()
                                matricula.calcular_rubros_matricula()
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al matricular los estudiantes."})

            elif action == 'delmateria':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    matricula = materiaasignada.matricula
                    materia = materiaasignada.materia
                    if matricula.nivel.nivelgrado:
                        if matricula.materiaasignada_set.filter(status=True).count() > 1:
                            bandera = 0
                            log(u'Elimino materia asignada: %s' % materiaasignada, request, "del")
                            materiaasignada.delete()
                            matricula.actualizar_horas_creditos()
                        else:
                            bandera = 1
                            rubro = Rubro.objects.filter(matricula=matricula, status=True)
                            if rubro:
                                if rubro[0].tiene_pagos():
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar ultima materia, porque matricula tiene rubros pagados"})
                            log(u'Elimino matricula por ultima materia: %s' % materiaasignada, request, "del")
                            materiaasignada.delete()
                            matricula.delete()
                    else:
                        if matricula.nivel.periodo.fecha_agregaciones():
                            if matricula.materiaasignada_set.filter(status=True).count() > 1:
                                bandera = 0
                                log(u'Elimino materia asignada: %s' % materiaasignada, request, "del")
                                if NOTIFICA_ELIMINACION_MATERIA:
                                    send_html_mail("Materia eliminada", "emails/materiaeliminada.html", {'sistema': request.session['nombresistema'], 'materia': materia, 'matricula': matricula, 't': tituloinstitucion()}, lista_correo([FINANCIERO_GROUP_ID, SECRETARIA_GROUP_ID]), [], cuenta=CUENTAS_CORREOS[5][1])
                                matricula.eliminar_materia(materiaasignada, request)
                                matricula.actualizar_horas_creditos()
                            else:
                                bandera = 1
                                rubro = Rubro.objects.filter(matricula=matricula, status=True)
                                if rubro:
                                    if rubro[0].tiene_pagos():
                                        transaction.set_rollback(True)
                                        return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar ultima materia, porque matricula tiene rubros pagados"})
                                    log(u'Elimino matricula por ultima materia: %s' % materiaasignada, request, "del")
                                    matricula.eliminar_materia(materiaasignada, request)
                                    matricula.delete()
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar materias fuera de las fecha de agregaciones"})
                    if CALCULO_POR_CREDITO:
                        if bandera == 0:
                            matricula.agregacion_aux(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar la materia."})

            elif action == 'sinasistencia':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    materiaasignada.sinasistencia = True
                    materiaasignada.actualiza_estado()
                    log(u'Modifico estado asistencia: %s' % materiaasignada, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'conasistencia':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    materiaasignada.sinasistencia = False
                    materiaasignada.actualiza_estado()
                    log(u'Modifico estado asistencia: %s' % materiaasignada, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'autorizarevaluacion':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    materiaasignada.evaluar = True
                    materiaasignada.fechaevaluar = datetime.now()
                    materiaasignada.save(request)
                    log(u'Autorizo evaluacion: %s' % materiaasignada, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'delmatricula':
                try:
                    matricula = Matricula.objects.get(pk=request.POST['id'])
                    for materiaasignada in matricula.materiaasignada_set.all():
                        materiaasignada.delete()
                    log(u'Elimino matricula: %s' % matricula, request, "del")
                    matricula.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'retirar':
                try:
                    matricula = Matricula.objects.get(pk=request.POST['id'])
                    f = RetiradoMatriculaForm(request.POST)
                    if f.is_valid():
                        if not matricula.retirado():
                            matricula.retiro_academico(f.cleaned_data['motivo'])
                            log(u'Retiro la matricula: %s' % matricula, request, "edit")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra retirado de la matricula."})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'retirarmateria':
                try:
                    materia = MateriaAsignada.objects.get(pk=request.POST['id'])
                    f = RetiradoMateriaForm(request.POST)
                    if f.is_valid():
                        if not materia.retirado():
                            retiro = MateriaAsignadaRetiro(materiaasignada=materia,
                                                           motivo=f.cleaned_data['motivo'],
                                                           valida=False,
                                                           fecha=datetime.now().date())
                            retiro.save(request)
                            materia.retiramateria = True
                            materia.save(request)
                            log(u'Retiro de materia: %s' % retiro, request, "edit")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra retirado de la materia."})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'materiasabiertas':
                return materias_abiertas(request,True, False)

            elif action == 'moveranivel':
                try:
                    matricula = Matricula.objects.get(pk=request.POST['id'])
                    f = MoverMatriculaNivelForm(request.POST)
                    if f.is_valid():
                        nuevonivel = f.cleaned_data['nivel']
                        if matricula.nivel != nuevonivel:
                            for ma in matricula.materiaasignada_set.all():
                                if nuevonivel.materia_set.filter(asignatura=ma.materia.asignatura).exists():
                                    materiaexistente = nuevonivel.materia_set.filter(asignatura=ma.materia.asignatura)[0]
                                    materianueva = MateriaAsignada(matricula=matricula,
                                                                   materia=materiaexistente,
                                                                   notafinal=0,
                                                                   asistenciafinal=0,
                                                                   observaciones='',
                                                                   fechaasignacion=datetime.now().date(),
                                                                   estado_id=NOTA_ESTADO_EN_CURSO)
                                    materianueva.save(request)
                                    materianueva.matriculas = materianueva.cantidad_matriculas()
                                    materianueva.save(request)
                                    materianueva.asistencias()
                                    ma.delete()
                            matricula.nivel = nuevonivel
                            matricula.save(request)
                        if UTILIZA_GRUPOS_ALUMNOS and not MATRICULACION_POR_NIVEL:
                            matricula.inscripcion.inscripcion_grupo(nuevonivel.grupo)
                        matricula.actualizar_horas_creditos()
                        log(u'Cambio de nivel: %s' % matricula, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'matricular':
                return matricular_admision(request, False)

            if action == 'movermateriasession':
                try:
                    materia = Materia.objects.get(pk=request.POST['mid'])
                    if MATRICULACION_LIBRE:
                        if not materia.tiene_capacidad():
                            return JsonResponse({"result": "bad", "mensaje": u"No existe cupo para esta materia"})
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['maid'])
                    asistencias = materiaasignada.asistencialeccion_set.all()
                    asistencias.delete()
                    evaluaciones = materiaasignada.evaluacion()
                    evaluaciones.delete()
                    materiaasignada.materia = materia
                    materiaasignada.save(request)
                    materiaasignada.notafinal = 0
                    materiaasignada.fechaasignacion = datetime.now().date()
                    materiaasignada.asistenciafinal = 0
                    materiaasignada.save(request)
                    conflicto = conflicto_materias_seleccionadas(Materia.objects.filter(id__in=[x.materia.id for x in materiaasignada.matricula.materiaasignada_set.all()]))
                    if conflicto:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": conflicto})
                    materiaasignada.asistencias()
                    materiaasignada.evaluacion()
                    materiaasignada.mis_planificaciones()
                    materiaasignada.matricula.actualizar_horas_creditos()
                    log(u'Cambio seccion materia: %s' % materiaasignada, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'nota':
                try:
                    persona = request.session['persona']
                    materiaasignada = MateriaAsignada.objects.filter(pk=request.POST['maid']).first()
                    auditoria = DetalleModificacionNota(materiaasignada_id=request.POST['maid'], campo=request.POST['sel'], notaanterior=request.POST['unidad'],notaactual=request.POST['val'])
                    auditoria.save(request)
                    inscripcion = materiaasignada.matricula.inscripcion.persona
                    mensaje = f"Se modificó la nota correspondiente al {request.POST['sel'].upper()} {'de la' if inscripcion.es_mujer() else 'del'} alumn{'a' if inscripcion.es_mujer() else 'o'} {inscripcion} en la materia de {materiaasignada.materia} del periodo {materiaasignada.materia.nivel.periodo} por {'la' if persona.es_mujer() else 'el'} {request.session['perfilprincipal']}, {persona}"
                    log_message = (f"{mensaje} Nota anterior {request.POST['unidad']} - Nota Actual {request.POST['val']}")
                    log(log_message, request, 'edit')
                    notificacion_masivo_grupo(u"Modificación de notas", mensaje, 49, f'/matriculas_admision?action=calificaciontardia&id={materiaasignada.id}', materiaasignada.pk, 1, 'sga', materiaasignada)
                    result = actualizar_nota(request)
                    correo_datos_adicionales = {
                        'sel': request.POST['sel'].upper(),
                        'genero': "de la" if inscripcion.es_mujer() else "del",
                        'estud': "a" if inscripcion.es_mujer() else "o",
                        'inscripcion': inscripcion,
                        'materia': materiaasignada.materia.asignatura.nombre,
                        'periodo': materiaasignada.materia.nivel.periodo.nombre,
                        'genero2':"la" if persona.es_mujer() else "el",
                        'perfil': request.session['perfilprincipal'],
                        'persona': persona,
                        'nota_anterior': request.POST['unidad'],
                        'nota_actual': request.POST['val']
                    }
                    send_html_mail(f"Actualizacion de Nota", "emails/cambio_notas.html",
                                   {'context': correo_datos_adicionales,
                                    'user_info': get_user_info(request)},
                                   persona.lista_emails_envio(),
                                   ['sga@unemi.edu.ec'], [],
                                   cuenta=CUENTAS_CORREOS[16][1])
                    return JsonResponse(result)

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'homologar':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    f = HomologacionInscripcionForm(request.POST)
                    if f.is_valid():
                        if materiaasignada.materiaasignadahomologacion_set.exists():
                            materiaasignadahomologacion = materiaasignada.materiaasignadahomologacion_set.all()[0]
                            homologacion = materiaasignadahomologacion.homologacion
                            homologacion.carrera = f.cleaned_data['carrera']
                            homologacion.asignatura = f.cleaned_data['asignatura']
                            homologacion.fecha = f.cleaned_data['fecha']
                            homologacion.nota_ant = f.cleaned_data['nota_ant']
                            homologacion.observaciones = f.cleaned_data['observaciones']
                            homologacion.creditos = f.cleaned_data['creditos']
                            homologacion.save(request)
                        else:
                            homologacion = HomologacionInscripcion(carrera=f.cleaned_data['carrera'],
                                                                   asignatura=f.cleaned_data['asignatura'],
                                                                   fecha=f.cleaned_data['fecha'],
                                                                   nota_ant=f.cleaned_data['nota_ant'],
                                                                   observaciones=f.cleaned_data['observaciones'],
                                                                   creditos=f.cleaned_data['creditos'])
                            homologacion.save(request)
                            materiaasignadahomologacion = MateriaAsignadaHomologacion(materiaasignada=materiaasignada,
                                                                                      homologacion=homologacion)
                            materiaasignadahomologacion.save(request)
                        log(u'Adicionada homologacion: %s' % homologacion, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'convalidar':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    f = ConvalidacionInscripcionForm(request.POST)
                    if f.is_valid():
                        if materiaasignada.materiaasignadaconvalidacion_set.exists():
                            materiaasignadaconvalidacion = materiaasignada.materiaasignadaconvalidacion_set.all()[0]
                            convalidacion = materiaasignadaconvalidacion.convalidacion
                            convalidacion.centro = f.cleaned_data['centro']
                            convalidacion.carrera = f.cleaned_data['carrera']
                            convalidacion.asignatura = f.cleaned_data['asignatura']
                            convalidacion.anno = f.cleaned_data['anno']
                            convalidacion.nota_ant = f.cleaned_data['nota_ant']
                            convalidacion.nota_act = f.cleaned_data['nota_act']
                            convalidacion.observaciones = f.cleaned_data['observaciones']
                            convalidacion.creditos = f.cleaned_data['creditos']
                            convalidacion.save(request)
                        else:
                            convalidacion = ConvalidacionInscripcion(centro=f.cleaned_data['centro'],
                                                                     carrera=f.cleaned_data['carrera'],
                                                                     asignatura=f.cleaned_data['asignatura'],
                                                                     anno=f.cleaned_data['anno'],
                                                                     nota_ant=f.cleaned_data['nota_ant'],
                                                                     nota_act=f.cleaned_data['nota_act'],
                                                                     observaciones=f.cleaned_data['observaciones'],
                                                                     creditos=f.cleaned_data['creditos'])
                            convalidacion.save(request)
                            materiaasignadaconvalidacion = MateriaAsignadaConvalidacion(materiaasignada=materiaasignada,
                                                                                        convalidacion=convalidacion)
                            materiaasignadaconvalidacion.save(request)
                        log(u'Adicionada convalidacion: %s' % convalidacion, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'fechaasignacion':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    f = CambioFechaAsignacionMateriaForm(request.POST)
                    if f.is_valid():
                        materiaasignada.fechaasignacion = f.cleaned_data['fecha']
                        materiaasignada.save(request)
                        log(u'Modifico la fecha de asignacion de la materia: %s' % materiaasignada, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'viewauditoria':
                try:
                    data['planificacion'] = materiaasignada = MateriaAsignada.objects.get(pk=int(request.POST['id']))
                    template = get_template("matriculas_admision/viewauditoria.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Matriculas de alumnos'
        persona = request.session['persona']
        miscarreras = Carrera.objects.filter(grupocoordinadorcarrera__group__in=persona.grupos()).distinct()
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'matricula':
                try:
                    data['title'] = u'Matricula de nivel académico'
                    nivel = Nivel.objects.get(pk=request.GET['id'])
                    ret = None
                    if 'ret' in request.GET:
                        ret = request.GET['ret']
                    periodo = request.session['periodo']
                    search = ""
                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        while '' in ss:
                            ss.remove('')
                        if len(ss) == 1:
                            matriculas = Matricula.objects.filter(Q(inscripcion__persona__nombres__icontains=search) |
                                                                  Q(inscripcion__persona__apellido1__icontains=search) |
                                                                  Q(inscripcion__persona__apellido2__icontains=search) |
                                                                  Q(inscripcion__persona__cedula__icontains=search) |
                                                                  Q(inscripcion__persona__pasaporte__icontains=search) |
                                                                  Q(inscripcion__identificador__icontains=search) |
                                                                  Q(inscripcion__inscripciongrupo__grupo__nombre__icontains=search) |
                                                                  Q(inscripcion__carrera__nombre__icontains=search) |
                                                                  Q(inscripcion__persona__usuario__username__icontains=search), nivel=nivel).order_by('inscripcion__persona').distinct()
                        else:
                            matriculas = Matricula.objects.filter(Q(inscripcion__persona__apellido1__icontains=ss[0]),
                                                                  Q(inscripcion__persona__apellido2__icontains=ss[1]), nivel=nivel).order_by('inscripcion__persona').distinct()
                    elif 'idm' in request.GET:
                        matriculas = Matricula.objects.filter(nivel=nivel, id=request.GET['idm']).order_by('inscripcion__persona').distinct()
                    else:
                        matriculas = Matricula.objects.filter(nivel=nivel).order_by('inscripcion__persona').distinct()
                    paging = MiPaginador(matriculas, 25)
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
                    data['matriculas'] = page.object_list
                    data['search'] = search if search else ""
                    data['ret'] = ret if ret else ""
                    data['nivel'] = nivel
                    data['periodo'] = periodo
                    data['matriculados_total'] = Matricula.objects.filter(nivel=nivel).count()
                    data['matriculalibre'] = MATRICULACION_LIBRE
                    data['calculocreditos'] = CALCULO_POR_CREDITO
                    data['reporte_0'] = obtener_reporte('lista_alumnos_matriculados')
                    data['reporte_1'] = obtener_reporte('certificado_matricula_alumno')
                    data['reporte_2'] = obtener_reporte('reporte_compromiso_pago')
                    data['matriculacion_libre'] = MATRICULACION_LIBRE
                    data['usa_retiro_matricula'] = USA_RETIRO_MATRICULA
                    data['permiteagregaciones'] = periodo.limite_agregacion >= datetime.now().date()
                    data['permiteretiro'] = periodo.limite_retiro >= datetime.now().date()
                    return render(request, "matriculas_admision/matricula.html", data)
                except Exception as ex:
                    pass

            elif action == 'addmatriculalibre':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Matricular estudiante'
                    data['periodo'] = periodo = request.session['periodo']
                    data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['id'])
                    data['total_materias_nivel'] = 0
                    inscripcion = None
                    if 'iid' in request.GET:
                        inscripcion = Inscripcion.objects.get(pk=request.GET['iid'])
                        if not persona.usuario.is_superuser:
                            if inscripcion.persona.tiene_matricula_periodo(periodo):
                                return HttpResponseRedirect("/?info=Ya se encuentra matriculado en el periodo en otra Carrerar")
                        if inscripcion.carrera not in nivel.coordinacion().carrera.all():
                            return HttpResponseRedirect("/matriculas_admision?action=addmatriculalibre&err=1&ide=" + request.GET['iid'] + "&id=" + str(nivel.id))
                        if inscripcion.modalidad != nivel.modalidad:
                            return HttpResponseRedirect("/matriculas_admision?action=addmatriculalibre&err=2&ide=" + request.GET['iid'] + "&id=" + str(nivel.id))
                        if inscripcion.sesion != nivel.sesion:
                            return HttpResponseRedirect("/matriculas_admision?action=addmatriculalibre&err=3&ide=" + request.GET['iid'] + "&id=" + str(nivel.id))
                        inscripcionmalla = inscripcion.malla_inscripcion()
                        if not inscripcionmalla:
                            return HttpResponseRedirect("/?info=Debe tener malla asociada para poder matricularse.")
                        if not MATRICULAR_CON_DEUDA:
                            if inscripcion.adeuda_a_la_fecha():
                                return HttpResponseRedirect("/matriculas_admision?action=addmatriculalibre&err=5&ide=" + request.GET['iid'] + "&id=" + str(nivel.id))
                        if inscripcion.matriculado_periodo(periodo):
                            return HttpResponseRedirect("/matriculas_admision?action=addmatriculalibre&err=6&ide=" + request.GET['iid'] + "&id=" + str(nivel.id))
                        # if 'ide' in request.GET:
                        #     inscripcion = Inscripcion.objects.get(pk=request.GET['ide'])

                        data['inscripcion'] = inscripcion
                        data['iid'] = inscripcion.id
                        data['total_materias_nivel'] = inscripcion.total_materias_nivel()
                        data['materiasmalla'] = inscripcionmalla.malla.asignaturamalla_set.all().order_by('nivelmalla','ejeformativo')
                        data['materiasmodulos'] = inscripcionmalla.malla.modulomalla_set.all()
                        data['total_materias_pendientes_malla'] = inscripcion.total_materias_pendientes_malla()
                    else:
                        data['matriculado'] = False
                        data['materiasmalla'] = None
                        data['materiasmodulos'] = None
                        data['iid'] = None
                    data['materiasmaximas'] = MAXIMO_MATERIA_ONLINE
                    data['utiliza_gratuidades'] = UTILIZA_GRATUIDADES
                    data['err'] = int(request.GET['err']) if 'err' in request.GET else ''
                    data['nombreerroneo'] = Inscripcion.objects.get(pk=request.GET['ide']).persona.nombre_completo() if 'err' in request.GET else ''
                    data['porciento_perdida_parcial_gratuidad'] = PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD
                    data['porciento_perdida_total_gratuidad'] = PORCIENTO_PERDIDA_TOTAL_GRATUIDAD
                    # if RecordAcademico.objects.filter(aprobada=False, inscripcion=inscripcion).exists():
                    #     data['tiene_reprobada'] = True
                    # else:
                    #     data['tiene_reprobada'] = False
                    return render(request, "matriculas_admision/addmatriculalibre.html", data)
                except Exception as ex:
                    pass

            elif action == 'addmatriculamulti':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Matricular estudiantes'
                    data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['id'])
                    form = MatriculaMultipleForm(initial={'nivel': nivel})
                    form.editar()
                    data['form'] = form
                    if MATRICULACION_POR_NIVEL:
                        if nivel.nivelgrado:
                            data['inscripciones'] = Inscripcion.objects.filter(inscripcionnivel__nivel=nivel.nivelmalla, sede=nivel.sede, carrera=nivel.carrera, retirocarrera__isnull=True, graduado__isnull=True).distinct()
                        else:
                            data['inscripciones'] = Inscripcion.objects.filter(inscripcionnivel__nivel=nivel.nivelmalla, modalidad=nivel.modalidad, sesion=nivel.sesion, sede=nivel.sede, carrera=nivel.carrera, retirocarrera__isnull=True, graduado__isnull=True).distinct()
                    else:
                        data['inscripciones'] = nivel.grupo.miembros()
                    return render(request, "matriculas_admision/addmatriculamulti.html", data)
                except Exception as ex:
                    pass

            elif action == 'delmatricula':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Borrar matricula de estudiante'
                    matricula = Matricula.objects.get(pk=request.GET['id'])
                    data['matricula'] = matricula
                    data['tiene_evaluacion'] = matricula.tiene_evaluacion()
                    return render(request, "matriculas_admision/delmatricula.html", data)
                except Exception as ex:
                    pass

            elif action == 'continua':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    matricula = Matricula.objects.get(pk=request.GET['id'])
                    if not matricula.nivel.cerrado:
                        retiro = matricula.retiromatricula_set.all()
                        retiro.delete()
                        matricula.retiradomatricula = False
                        matricula.save(request)
                        retirnomaterias = MateriaAsignadaRetiro.objects.filter(materiaasignada__matricula=matricula)
                        log(u'Elimino retiro de matricula: %s' % retiro, request, "del")
                        for hm in retirnomaterias:
                            hm.materiaasignada.retiramateria = False
                            hm.materiaasignada.save(request)
                        retirnomaterias.delete()
                    return HttpResponseRedirect("/matriculas_admision?action=matricula&id=" + str(matricula.nivel.id))
                except Exception as ex:
                    pass

            elif action == 'moveranivel':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Mover matricula de estudiante a otro nivel'
                    periodo = request.session['periodo']
                    matricula = Matricula.objects.get(pk=request.GET['id'])
                    data['matricula'] = matricula
                    f = MoverMatriculaNivelForm()
                    if not MATRICULACION_LIBRE:
                        f.for_nivel(matricula)
                    else:
                        f.niveles_activos(periodo)
                    data['form'] = f
                    return render(request, "matriculas_admision/moveranivel.html", data)
                except Exception as ex:
                    pass

            elif action == 'retirar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Retirar matricula de estudiante'
                    data['matricula'] = Matricula.objects.get(pk=request.GET['id'])
                    data['form'] = RetiradoMatriculaForm()
                    return render(request, "matriculas_admision/retirar.html", data)
                except Exception as ex:
                    pass

            elif action == 'retirarmateria':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Retirar de la materia al estudiante'
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    data['materiaasignada'] = materiaasignada
                    data['form'] = RetiradoMateriaForm()
                    return render(request, "matriculas_admision/retirarmateria.html", data)
                except Exception as ex:
                    pass

            elif action == 'continuarmateria':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    retiro = materiaasignada.materiaasignadaretiro_set.all()
                    materiaasignada.retiramateria = False
                    materiaasignada.save(request)
                    log(u"Elimino retiro de materia:" + unicode(materiaasignada), request, "del")
                    retiro.delete()
                    return HttpResponseRedirect("/matriculas_admision?action=materias&id=" + str(materiaasignada.matricula.id))
                except Exception as ex:
                    pass

            elif action == 'auditoria':
                try:
                    data['auditoriadetalle']=auditoria = DetalleModificacionNota.objects.filter(materiaasignada_id=request.GET['id'])
                    template = get_template("matriculas_admision/auditorianota.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'calificaciontardia':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_calificacion_tardia')
                    data['title'] = u'Calificación tardía'
                    data['materiaasignada'] = MateriaAsignada.objects.get(pk=request.GET['id'])
                    data['validardeuda'] = False
                    data['incluyepago'] = False
                    data['incluyedatos'] = False
                    return render(request, "matriculas_admision/calificaciontardia.html", data)
                except Exception as ex:
                    pass

            elif action == 'segmento':
                try:
                    data['materiaasignada'] = MateriaAsignada.objects.filter(id=request.GET['idma'])
                    data['auditoriadetalle'] = DetalleModificacionNota.objects.filter(materiaasignada_id=request.GET['idma'])
                    data['materia'] = Materia.objects.get(pk=request.GET['id'])
                    data['validardeuda'] = False
                    data['incluyepago'] = False
                    data['incluyedatos'] = False
                    if persona.usuario.is_superuser:
                        data['auditor'] = False
                    else:
                        data['auditor'] = puede_realizar_accion(request, 'sga.puede_modificar_calificacion_tardia')
                    data['cronograma'] = None
                    data['permitecambiarcodigo'] = False
                    return render(request, "matriculas_admision/segmento.html", data)
                except Exception as ex:
                    pass

            elif action == 'materias':
                try:
                    data['title'] = u'Materias asignadas'
                    data['matricula'] = matricula = Matricula.objects.get(pk=request.GET['id'])
                    data['materias'] = materias = matricula.materiaasignada_set.all()
                    data['carrera'] = matricula.inscripcion.carrera.nombre
                    materiasnodisponibles = Materia.objects.filter(cerrado=False, nivel__cerrado=False, nivel__periodo=matricula.nivel.periodo)
                    disponibles = []
                    for materiad in materiasnodisponibles:
                        if materiad.asignatura.id not in disponibles:
                            disponibles.append(materiad.asignatura.id)
                    tomadas = []
                    for materiad in materias:
                        if materiad.materia.asignatura.id not in tomadas:
                            tomadas.append(materiad.materia.asignatura.id)
                    data['asignaturaslibres'] = Asignatura.objects.filter(id__in=disponibles).distinct().order_by('nombre')
                    malla = matricula.inscripcion.malla_inscripcion().malla
                    pendientes_modulos = []
                    for x in malla.modulomalla_set.all():
                        if not matricula.inscripcion.ya_aprobada(x.asignatura):
                            pendientes_modulos.append(x.asignatura)
                    pendientes = []
                    for x in malla.asignaturamalla_set.all().order_by('nivelmalla'):
                        if not matricula.inscripcion.ya_aprobada(x.asignatura) and not matricula.materiaasignada_set.filter(materia__asignaturamalla__asignatura=x.asignatura).exists():
                            if x.asignatura.modulo:
                                pendientes_modulos.append(x.asignatura)
                            else:
                                pendientes.append(x)
                    data['pendientes'] = pendientes
                    data['pendientes_modulos'] = pendientes_modulos
                    data['recordsp'] = RecordAcademico.objects.filter(inscripcion=matricula.inscripcion, aprobada=True).order_by('asignatura')
                    data['calculo_por_credito'] = CALCULO_POR_CREDITO
                    data['usa_evaluacion_integral'] = USA_EVALUACION_INTEGRAL
                    data['usa_retiro_materia'] = USA_RETIRO_MATERIA
                    data['permiteagregaciones'] = matricula.nivel.periodo.limite_agregacion >= datetime.now().date()
                    data['permiteretiro'] = matricula.nivel.periodo.limite_retiro >= datetime.now().date()
                    data['valor_pendiente'] = matricula.total_saldo_rubro()
                    data['valor_pagados'] = matricula.total_pagado_rubro()
                    return render(request, "matriculas_admision/materias.html", data)
                except Exception as ex:
                    pass

            elif action == 'delmateria':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Eliminar materia de asignadas'
                    data['materiaasignada'] = MateriaAsignada.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas_admision/delmateria.html", data)
                except Exception as ex:
                    pass

            elif action == 'sinasistencia':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'No tomar en cuenta asistencia'
                    data['materiaasignada'] = MateriaAsignada.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas_admision/sinasistencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'conasistencia':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Tomar en cuenta asistencia'
                    data['materiaasignada'] = MateriaAsignada.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas_admision/conasistencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'autorizarevaluacion':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_autorizacion_evaluacion')
                    data['title'] = u'Autorizado a evaluar'
                    data['materiaasignada'] = MateriaAsignada.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas_admision/autorizarevaluacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'promote':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Seleccionar materia para alumno'
                    data['asignatura'] = asignatura = Asignatura.objects.get(pk=request.GET['id'])
                    data['matricula'] = matricula = Matricula.objects.get(pk=request.GET['matricula'])
                    data['materias'] = Materia.objects.filter(asignatura=asignatura, nivel__periodo=matricula.nivel.periodo, cerrado=False, nivel__cerrado=False)
                    data['homitircapacidadhorario'] = HOMITIRCAPACIDADHORARIO
                    data['permiteagregaciones'] = matricula.nivel.periodo.limite_agregacion >= datetime.now().date()
                    return render(request, "matriculas_admision/promote.html", data)
                except Exception as ex:
                    pass

            elif action == 'movermateriasession':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Mover materia de session'
                    data['materiaasignada'] = materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    data['materias'] = Materia.objects.filter(asignatura=materiaasignada.materia.asignatura, nivel__periodo=materiaasignada.matricula.nivel.periodo, cerrado=False, nivel__cerrado=False).exclude(id=materiaasignada.materia.id)
                    data['matricula'] = materiaasignada.matricula
                    data['homitircapacidadhorario'] = HOMITIRCAPACIDADHORARIO
                    return render(request, "matriculas_admision/movermateriasession.html", data)
                except Exception as ex:
                    pass

            elif action == 'validapararecord':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    retiro = materiaasignada.retiro()
                    retiro.valida = True
                    retiro.save(request)
                    return HttpResponseRedirect("/matriculas_admision?action=materias&id=" + str(materiaasignada.matricula.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'novalidapararecord':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    retiro = materiaasignada.retiro()
                    retiro.valida = False
                    retiro.save(request)
                    return HttpResponseRedirect("/matriculas_admision?action=materias&id=" + str(materiaasignada.matricula.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'convalidar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Homologación de materia'
                    data['materiaasignada'] = materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    if materiaasignada.materiaasignadaconvalidacion_set.exists():
                        materiaasignadaconvalidacion = materiaasignada.materiaasignadaconvalidacion_set.all()[0]
                        data['form'] = ConvalidacionInscripcionForm(initial={'asignatura': materiaasignadaconvalidacion.convalidacion.asignatura,
                                                                             'centro': materiaasignadaconvalidacion.convalidacion.centro,
                                                                             'carrera': materiaasignadaconvalidacion.convalidacion.carrera,
                                                                             'creditos': materiaasignadaconvalidacion.convalidacion.creditos,
                                                                             'observaciones': materiaasignadaconvalidacion.convalidacion.observaciones,
                                                                             'nota_ant': materiaasignadaconvalidacion.convalidacion.nota_ant,
                                                                             'nota_act': materiaasignadaconvalidacion.convalidacion.nota_act,
                                                                             'anno': materiaasignadaconvalidacion.convalidacion.anno})
                    else:
                        data['form'] = ConvalidacionInscripcionForm(initial={'asignatura': materiaasignada.materia.asignatura.nombre,
                                                                             'creditos': materiaasignada.materia.creditos,
                                                                             'nota_ant': 0,
                                                                             'nota_act': 0,
                                                                             'anno': datetime.now().date().year})
                    return render(request, "matriculas_admision/convalidar.html", data)
                except Exception as ex:
                    pass

            elif action == 'fechaasignacion':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Cambiar fecha asignacion de la materia'
                    data['materiaasignada'] = materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    data['form'] = CambioFechaAsignacionMateriaForm(initial={'fecha': materiaasignada.matricula.fecha})
                    return render(request, "matriculas_admision/fechaasignacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'delconvalidacion':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    if materiaasignada.materiaasignadaconvalidacion_set.exists():
                        materiaasignadaconvalidacion = materiaasignada.materiaasignadaconvalidacion_set.all()[0]
                        log(u'Elimino convalidacion de materia: %s' % materiaasignadaconvalidacion, request, "del")
                        materiaasignadaconvalidacion.delete()
                    return HttpResponseRedirect("matriculas_admision?action=materias&id=" + str(materiaasignada.matricula.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'delhomologacion':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    if materiaasignada.materiaasignadahomologacion_set.exists():
                        materiaasignadahomologacion = materiaasignada.materiaasignadahomologacion_set.all()[0]
                        log(u'Elimino homologacion de materia: %s' % materiaasignada, request, "del")
                        materiaasignadahomologacion.delete()
                    return HttpResponseRedirect("matriculas_admision?action=materias&id=" + str(materiaasignada.matricula.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'homologar':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    data['title'] = u'Homologacion de materia'
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    if materiaasignada.materiaasignadahomologacion_set.exists():
                        materiaasignadahomologacion = materiaasignada.materiaasignadahomologacion_set.all()[0]
                        data['form'] = HomologacionInscripcionForm(initial={'carrera': materiaasignadahomologacion.homologacion.carrera,
                                                                            'asignatura': materiaasignadahomologacion.homologacion.asignatura,
                                                                            'fecha': materiaasignadahomologacion.homologacion.fecha,
                                                                            'nota_ant': materiaasignadahomologacion.homologacion.nota_ant,
                                                                            'creditos': materiaasignadahomologacion.homologacion.creditos,
                                                                            'observaciones': materiaasignadahomologacion.homologacion.observaciones})
                    else:
                        data['form'] = HomologacionInscripcionForm(initial={'fecha': datetime.now().date(),
                                                                            'nota_ant': 0,
                                                                            'creditos': materiaasignada.materia.creditos})
                    data['materiaasignada'] = materiaasignada
                    return render(request, "matriculas_admision/homologar.html", data)
                except Exception as ex:
                    pass

            elif action == 'actualizarrecord':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    materiaasignada.cierre_materia_asignada()
                    log(u'Actualizar record: %s' % materiaasignada, request, "edit")
                    return HttpResponseRedirect("matriculas_admision?action=materias&id=" + str(materiaasignada.matricula.id))
                except Exception as ex:
                    pass

            elif action == 'ver_notas':
                try:
                    if not periodo.ocultarnota or persona.usuario.is_superuser:
                        data['inscripcion'] = Inscripcion.objects.filter(id=request.GET['idinscripcion'])[0]
                        data['materiasasignadas'] = maateriaasignada = MateriaAsignada.objects.filter(id=request.GET['idcurso'])
                        data['matricula'] = maateriaasignada[0].matricula
                        return render(request, "matriculas_admision/ver_notas.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Matriculas de alumnos'
            if MATRICULACION_LIBRE:
                return HttpResponseRedirect("/niveles")
            periodo = request.session['periodo']
            data['sedes'] = Sede.objects.all()
            data['carreras'] = Carrera.objects.all()
            data['niveles'] = Nivel.objects.filter(periodo=data['periodo'], carrera__in=data['carreras']).order_by('paralelo')
            data['niveles_abiertos'] = Nivel.objects.filter(cerrado=False, periodo=data['periodo'], carrera__in=data['carreras'])
            data['niveles_cerrados'] = Nivel.objects.filter(cerrado=True, periodo=data['periodo'], carrera__in=data['carreras'])
            data['usa_nivel0'] = UTILIZA_NIVEL0_PROPEDEUTICO
            data['total_matriculados'] = Matricula.objects.filter(nivel__periodo=periodo).count()
            data['total_retirados'] = RetiroMatricula.objects.filter(matricula__nivel__periodo=periodo).count()
            data['total_actual'] = data['total_matriculados'] - data['total_retirados']
            return render(request, "matriculas_admision/view.html", data)