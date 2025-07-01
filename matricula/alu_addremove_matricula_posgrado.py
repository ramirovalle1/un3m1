# -*- coding: latin-1 -*-
import os
from datetime import datetime
import code128
import pyqrcode
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.template.context import Context
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template

from decorators import secure_module, last_access
from matricula.funciones import valid_intro_module_estudiante, get_nivel_matriculacion
from matricula.models import PeriodoMatricula
from sagest.models import Rubro
from settings import SITE_STORAGE, CALCULO_POR_CREDITO, USA_EVALUACION_INTEGRAL, USA_RETIRO_MATERIA, \
    UTILIZA_GRATUIDADES, NOTA_ESTADO_APROBADO, MAXIMO_MATERIA_ONLINE, HOMITIRCAPACIDADHORARIO, \
    NOTIFICA_ELIMINACION_MATERIA, NOTA_ESTADO_EN_CURSO, MATRICULACION_LIBRE
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import log, variable_valor
from sga.models import Matricula, Inscripcion, ConfirmarMatricula, ModuloMalla, PracticasPreprofesionalesInscripcion, \
    ParticipantesMatrices, AsignaturaMalla, RecordAcademico, MateriaCupo, Asignatura, Materia, AuditoriaMatricula, \
    Carrera, MateriaAsignada, AgregacionEliminacionMaterias, AlumnosPracticaMateria, GruposProfesorMateria, \
    ProfesorMateria
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsavecertificados
from django.db import connections, transaction

from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt, encrypt_alu


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
def view(request):
    data = {}
    adduserdata(request, data)
    valid, msg_error = valid_intro_module_estudiante(request, 'posgrado')
    if not valid:
        return HttpResponseRedirect(f"/?info={msg_error}")
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']
    inscripcion = perfilprincipal.inscripcion
    hoy = datetime.now().date()

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'calcular':
                try:
                    matricula = Matricula.objects.get(pk=request.POST['id'])
                    matricula.agregacion_aux(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al calcular los rubros."})

            elif action == 'materiapractica':
                try:
                    materia = Materia.objects.get(id=int(request.POST['mat']))
                    matricula = Matricula.objects.get(pk=int(request.POST['idm']))
                    # EXTRAMOS LOS DATOS DE LA MATERIA SELECCIONADA
                    datos = materia.datos_practicas_materia(matricula.inscripcion)
                    return JsonResponse({"result": "ok", "datos": datos})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al solicitar cupo."})


            elif action == 'solicitarcupo':
                try:
                    if MateriaCupo.objects.filter(materia_id=int(request.POST['idmateria']), matricula_id=int(request.POST['idmatricula'])).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya solicitó cupo."})
                    else:
                        materiacupo = MateriaCupo(materia_id=request.POST['idmateria'],
                                                  matricula_id=request.POST['idmatricula'],
                                                  estadosolicitud=1)
                        materiacupo.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al solicitar cupo."})

            if action == 'promotemateria':
                try:
                    matricula_id = int(request.POST['idma']) if 'idma' in request.POST and request.POST['idma'] else None
                    if not Matricula.objects.values('id').filter(pk=matricula_id).exists():
                        raise NameError(u"Matricula no existe")
                    matricula = Matricula.objects.get(pk=matricula_id)
                    nivel = matricula.nivel
                    periodomatricula = None
                    if nivel.periodo.periodomatricula_set.values('id').filter(status=True).exists():
                        periodomatricula = nivel.periodo.periodomatricula_set.filter(status=True)[0]
                    if not periodomatricula:
                        raise NameError(u"Periodo académico no existe")
                    materia = Materia.objects.get(pk=int(request.POST['seleccionado']))
                    # para actualizar el itinerario en inscripcion
                    personainscripcion = Inscripcion.objects.get(pk=matricula.inscripcion.id)
                    if not personainscripcion.itinerario or personainscripcion.itinerario < 1:
                       if materia.asignaturamalla.itinerario > 0:
                           codigoitinerario = int(materia.asignaturamalla.itinerario)
                           personainscripcion.itinerario=codigoitinerario
                           personainscripcion.save(request)

                    profesormateria = None
                    grupoprofesormateria = None
                    # COVID19
                    if materia.asignaturamalla.practicas:
                        if materia.asignaturamalla.malla.carrera.id.__str__() in variable_valor('LISTA_CARRERA_PARA_MATRICULA_GRUPO_PRACTICA'):
                            if not int(request.POST['selecpract']) > 0:
                                raise NameError(u"Seleccione un horario de prácticas.")
                            else:
                                profesormateria = ProfesorMateria.objects.get(pk=int(request.POST['selecpract']), materia=materia)
                                if not int(request.POST['selecgrup']) > 0 and profesormateria.grupoprofesormateria():
                                    raise NameError(u"Seleccione un horario de prácticas.")
                                else:
                                    if profesormateria.grupoprofesormateria():
                                        grupoprofesormateria = GruposProfesorMateria.objects.get(pk=int(request.POST['selecgrup']), profesormateria__materia=materia, profesormateria = profesormateria)
                                        profesormateria = None
                    if matricula.inscripcion.existe_en_malla(materia.asignatura) and not matricula.inscripcion.puede_tomar_materia(materia.asignatura):
                        raise NameError(u"No puede tomar esta materia por tener precedencias")
                    if matricula.inscripcion.existe_en_modulos(materia.asignatura) and not matricula.inscripcion.puede_tomar_materia_modulo(materia.asignatura):
                        raise NameError(u"No puede tomar esta materia por tener precedencias")
                    #COVID19
                    if MATRICULACION_LIBRE:
                        if not materia.tiene_capacidad():
                            raise NameError(u"No existe cupo para esta materia")
                        if grupoprofesormateria:
                            if not grupoprofesormateria.cuposdisponiblesgrupoprofesor() > 0:
                                raise NameError(u"No existe cupo para en la practica")
                    if matricula.materiaasignada_set.values('id').filter(materia=materia).exists():
                        raise NameError(u"Ya se encuentra matriculado en esta materia")

                    materiaasignada = MateriaAsignada(matricula=matricula,
                                                      materia=materia,
                                                      notafinal=0,
                                                      asistenciafinal=0,
                                                      cerrado=False,
                                                      observaciones='',
                                                      estado_id=NOTA_ESTADO_EN_CURSO)
                    materiaasignada.save(request)
                    if profesormateria:
                        alumnopractica = AlumnosPracticaMateria(materiaasignada=materiaasignada, profesormateria=profesormateria)
                        alumnopractica.save(request)
                        log(u'Materia (%s) con profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s)' % (materia, profesormateria, materiaasignada, alumnopractica.id), request, "add")
                    elif grupoprofesormateria:
                        alumnopractica = AlumnosPracticaMateria(materiaasignada=materiaasignada, profesormateria=grupoprofesormateria.profesormateria, grupoprofesor=grupoprofesormateria)
                        alumnopractica.save(request)
                        log(u'Materia (%s) con grupo profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s) desde modulo adiciona materia' % ( materia, grupoprofesormateria, materiaasignada, alumnopractica.id), request, "add")
                    matricula.actualizar_horas_creditos()
                    #COVID19
                    if not inscripcion.carrera.modalidad == 3:
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
                        if datetime.now().date() < materia.nivel.fechainicioagregacion:
                            # AGREGACION DE MATERIAS EN MATRICULACION REGULAR SIN REALIZAR PAGOS
                            materiaasignada.save(request)
                            log(u'Adiciono materia: %s' % materiaasignada, request, "add")
                            if CALCULO_POR_CREDITO:
                                matricula.agregacion_aux(request)
                                # matricula.calcular_rubros_matricula(cobro)
                        elif matricula.nivel.puede_agregar_materia_matricula():
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
                            if not materia.asignatura.modulo:
                                raise NameError(u"Acción no encontrada")
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
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al agregar la materia: %s" % ex.__str__()})

            elif action == 'delmateria':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    matricula = materiaasignada.matricula
                    # if Rubro.objects.filter(matricula=matricula, status=True, cancelado=True).exists():
                    #     return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar materias, porque existen rubros de la matricula cancelados"})
                    # else:
                    materia = materiaasignada.materia
                    if matricula.nivel.nivelgrado:
                        if matricula.materiaasignada_set.values('id').filter(status=True).count() > 1:
                            bandera = 0
                            log(u'Elimino materia asignada: %s' % materiaasignada, request, "del")
                            materiaasignada.materia.descontar_cupo_adicional(request)
                            materiaasignada.delete()
                            matricula.actualizar_horas_creditos()
                        else:
                            # return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar, por lo menos debe de existir una materia"})
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

                        if matricula.nivel.fechafinagregacion >= datetime.now().date():
                            if matricula.materiaasignada_set.values('id').filter(status=True).count() > 1:
                                bandera = 0
                                log(u'Elimino materia asignada: %s' % materiaasignada, request, "del")
                                if NOTIFICA_ELIMINACION_MATERIA:
                                    send_html_mail("Materia eliminada", "emails/materiaeliminada.html", {'sistema': request.session['nombresistema'], 'materia': materia, 'matricula': matricula, 't': tituloinstitucion()}, lista_correo([FINANCIERO_GROUP_ID, SECRETARIA_GROUP_ID]), [], cuenta=variable_valor('CUENTAS_CORREOS')[5])
                                materiaasignada.materia.descontar_cupo_adicional(request)
                                matricula.eliminar_materia(materiaasignada, request)
                                matricula.actualizar_horas_creditos()
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar, por lo menos debe de existir una materia"})
                                # bandera = 1
                                # rubro = Rubro.objects.filter(matricula=matricula, status=True)
                                # if rubro:
                                #     if rubro[0].tiene_pagos():
                                #         transaction.set_rollback(True)
                                #         return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar ultima materia, porque matricula tiene rubros pagados"})
                                #     log(u'Elimino matricula por ultima materia: %s' % materiaasignada, request, "del")
                                #     matricula.eliminar_materia(materiaasignada, request)
                                #     matricula.delete()
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar materias fuera de las fecha de agregaciones"})
                    if CALCULO_POR_CREDITO:
                        if bandera == 0:
                            matricula.agregacion_aux(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar la materia."})

        if action == 'delconfirmarmatricula':
            try:
                matricula = Matricula.objects.get(pk=request.POST['idmatriculaeliminar'])
                rubro = Rubro.objects.filter(matricula=matricula, status=True)
                if rubro:
                    # if rubro.filter(bloqueado=True).exists():
                    #    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar la matricula, porque su deuda fue generada al banco."})
                    if Rubro.objects.filter(matricula=matricula, status=True)[0].tiene_pagos():
                        return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar la matricula, porque existen rubros de la matricula ya cancelados."})
                delpersona = matricula
                auditoria = AuditoriaMatricula(inscripcion=matricula.inscripcion,
                                               periodo=matricula.nivel.periodo,
                                               tipo=3)
                auditoria.save(request)
                matricula.delete()
                log(u'Elimino matricula: %s' % delpersona, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar la matricula"})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Matriculas de alumnos'
        persona = request.session['persona']
        miscarreras = Carrera.objects.filter(grupocoordinadorcarrera__group__in=persona.grupos()).distinct()
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'promote':
                try:
                    data['title'] = u'Seleccionar materia para alumno'
                    data['asignatura'] = asignatura = Asignatura.objects.get(pk=int(encrypt_alu(request.GET['id'])))
                    data['matricula'] = matricula = Matricula.objects.get(pk=int(encrypt_alu(request.GET['matricula'])))
                    # buscar paralelo
                    a = matricula.materiaasignada_set.filter(status=True, materia__asignaturamalla__nivelmalla_id=int(request.GET['idnivel']))
                    if a:
                        paralelo = a[0].materia.paralelo
                        data['materias'] = Materia.objects.filter(paralelo=paralelo, asignatura=asignatura,  nivel__cerrado=False, nivel__periodo=matricula.nivel.periodo, carrerascomunes__isnull=True, asignaturamalla__malla=matricula.inscripcion.mi_malla()).distinct().order_by('id')
                    else:
                        data['materias'] = Materia.objects.filter(asignatura=asignatura,  nivel__cerrado=False, nivel__periodo=matricula.nivel.periodo, carrerascomunes__isnull=True, asignaturamalla__malla=matricula.inscripcion.mi_malla()).distinct().order_by('id')
                    data['homitircapacidadhorario'] = HOMITIRCAPACIDADHORARIO
                    data['permiteagregaciones'] = matricula.nivel.periodo.limite_agregacion >= datetime.now().date()
                    return render(request, "matricula_addremove/posgrado/promote.html", data)
                except Exception as ex:
                    pass

            if action == 'calcular':
                try:
                    data['title'] = u'Seleccionar materia para alumno'
                    data['matricula'] = Matricula.objects.get(pk=request.GET['id'])
                    return render(request, "matricula_addremove/posgrado/calcular.html", data)
                except Exception as ex:
                    pass

            elif action == 'delmateria':
                try:
                    data['title'] = u'Eliminar materia de asignadas'
                    data['materiaasignada'] = MateriaAsignada.objects.get(pk=request.GET['id'])
                    return render(request, "matricula_addremove/posgrado/delmateria.html", data)
                except Exception as ex:
                    pass

            elif action == 'verdetalle':
                try:
                    data = {}
                    data = valida_matricular_requisitotitulacion(data, inscripcion)
                    template = get_template("matricula_addremove/posgrado/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Matriculación Online'
                periodomatricula = None
                matricula = None
                if inscripcion.tiene_perdida_carrera():
                    raise NameError(u"ATENCIÓN: Su limite de matricula por perdida de una o mas asignaturas correspondientes a su plan de estudios, ha excedido. Por favor, acercarse a Secretaria para mas informacion.")
                if inscripcion.tiene_cuarta_matricula():
                    raise NameError(u"ATENCIÓN: Su limite de matricula por perdida de una o mas asignaturas correspondientes a su plan de estudios, ha excedido. Por favor, acercarse a Secretaria para mas informacion.")
                if not PeriodoMatricula.objects.values_list('id').filter(status=True, activo=True, periodo=periodo).exists():
                    raise NameError(u"Estimado/a estudiante, el periodo de matriculación se encuentra inactivo")
                periodomatricula = PeriodoMatricula.objects.filter(status=True, activo=True, periodo=periodo)
                if periodomatricula.count() > 1:
                    raise NameError(u"Estimado/a estudiante, proceso de matriculación no se encuentra activo")
                periodomatricula = periodomatricula[0]
                if not periodomatricula.esta_periodoactivomatricula():
                    raise NameError(u"Estimado/a estudiante, el periodo de matriculación se encuentra inactivo")
                nivelid = get_nivel_matriculacion(inscripcion, periodomatricula.periodo)
                if nivelid < 0:
                    if nivelid == -1:
                        raise NameError(u"Estimado/a estudiante, su carrera no tiene coordinacion o no se encuentra abierto un nivel para su carrera.")
                    if nivelid == -2:
                        raise NameError(u"Estimado/a estudiante, no existen niveles con cupo para matricularse")
                    if nivelid == -3:
                        raise NameError(u"Estimado/a estudiante, no existen paralelos disponibles")
                    if nivelid == -4:
                        raise NameError(u"Estimado/a estudiante, no existen paralelos para su nivel")
                if not Matricula.objects.values('id').filter(inscripcion=inscripcion, nivel__periodo=periodomatricula.periodo).exists():
                    raise NameError(u"ATENCIÓN: Para usar este módulo, debe estar matriculado en el periodo actual: [%s]" % periodomatricula.periodo)

                data['matricula'] = matricula = Matricula.objects.filter(inscripcion=inscripcion, nivel__periodo=periodomatricula.periodo)[0]
                if not ConfirmarMatricula.objects.values("id").filter(matricula=matricula, status=True).exists():
                    confirmarmatricula = ConfirmarMatricula(matricula=matricula, estado=True)
                    confirmarmatricula.save(request)

                if not AuditoriaMatricula.objects.values("id").filter(inscripcion=matricula.inscripcion, periodo=matricula.nivel.periodo, tipo=1).exists():
                    auditoria = AuditoriaMatricula(inscripcion=matricula.inscripcion,
                                                   periodo=matricula.nivel.periodo,
                                                   tipo=1)
                    auditoria.save(request)
                nivel = matricula.nivel
                data['materias'] = materias = matricula.materiaasignada_set.all().order_by('materia__asignaturamalla__nivelmalla__orden')
                puede = True
                # if materias.count() >= periodomatricula.num_materias_maxima:
                #     puede = False
                data['puede'] = puede
                data['puedeagregar'] = matricula.nivel.puede_agregar_materia_matricula()
                data['puedequitar'] = matricula.nivel.puede_quitar_materia_matricula()
                # data['permiteagregaciones'] = matricula.nivel.fechafinagregacion >= datetime.now().date()
                # data['permiteretiros'] = matricula.nivel.fechafinagregacion >= datetime.now().date()
                data['fecha_hoy'] = datetime.now().date()
                data['carrera'] = matricula.inscripcion.carrera.nombre
                materiasnodisponibles = Materia.objects.filter(asignaturamalla__malla__carrera=matricula.inscripcion.carrera,
                                                               rectora=True, cerrado=False, nivel__cerrado=False,
                                                               nivel__periodo=matricula.nivel.periodo,
                                                               carrerascomunes__isnull=True)
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
                    if not matricula.inscripcion.ya_aprobada(x.asignatura) and not matricula.materiaasignada_set.filter(materia__asignatura=x.asignatura).exists():
                        pendientes_modulos.append(x.asignatura)
                pendientes = []
                for x in malla.asignaturamalla_set.all().order_by('nivelmalla'):
                    if not matricula.inscripcion.ya_aprobada(x.asignatura) and not matricula.materiaasignada_set.values('id').filter(materia__asignatura=x.asignatura).exists():
                        if x.asignatura.modulo and not inscripcion.coordinacion.id in [7]:
                            pendientes_modulos.append(x.asignatura)
                        else:
                            pendientes.append(x)
                data['pendientes'] = pendientes
                data['inscripcion'] = inscripcion
                data['inscripcionpersona'] = Inscripcion.objects.get(pk=inscripcion.id)
                data['pendientes_modulos'] = pendientes_modulos
                # data['recordsp'] = RecordAcademico.objects.filter(inscripcion=matricula.inscripcion, aprobada=True).order_by('asignatura')
                data['calculo_por_credito'] = CALCULO_POR_CREDITO
                data['usa_evaluacion_integral'] = USA_EVALUACION_INTEGRAL
                data['usa_retiro_materia'] = USA_RETIRO_MATERIA

                data['utiliza_gratuidades'] = UTILIZA_GRATUIDADES
                data['valor_pendiente'] = matricula.total_saldo_rubro()
                data['valor_pagados'] = matricula.total_pagado_rubro()
                data = valida_matricular_requisitotitulacion(data, inscripcion)
                data['materiascupo'] = MateriaCupo.objects.filter(matricula__inscripcion=inscripcion, matricula__nivel__periodo=periodo, status=True)
                return render(request, "matricula_addremove/posgrado/view.html", data)
            except Exception as ex:
                data['msg_matricula'] = ex.__str__()
                return render(request, "matricula_addremove/view.html", data)



def valida_matricular_requisitotitulacion(data, inscripcion):
    vali_alter = 0
    vali_tenido = 0
    requisitosaprobados = False
    data['inscripcion'] = inscripcion
    malla = inscripcion.inscripcionmalla_set.filter(status=True)[0].malla
    perfil = inscripcion.persona.mi_perfil()
    data['tiene_discapidad'] = perfil.tienediscapacidad

    # PASO 1
    vali_alter += 1
    data['creditos'] = inscripcion.aprobo_asta_penultimo_malla()
    if inscripcion.aprobo_asta_penultimo_malla() and inscripcion.esta_matriculado_ultimo_nivelrequisito():
        vali_tenido += 1
    data['cantasigaprobadas'] = inscripcion.cantidad_asig_aprobada_penultimo_malla()
    data['cantasigaprobar'] = inscripcion.cantidad_asig_aprobar_penultimo_malla()
    data['esta_mat_ultimo_nivel'] = inscripcion.esta_matriculado_ultimo_nivelrequisito()
    # PASO 2
    # vali_alter += 1
    # total_materias_malla = malla.cantidad_materiasaprobadas()
    # cantidad_materias_aprobadas_record = inscripcion.recordacademico_set.filter(aprobada=True, status=True,asignatura__in=[x.asignatura for x in malla.asignaturamalla_set.filter(status=True)]).count()
    # poraprobacion = round(cantidad_materias_aprobadas_record * 100 / total_materias_malla, 0)
    # data['mi_nivel'] = nivel = inscripcion.mi_nivel()
    # inscripcionmalla = inscripcion.malla_inscripcion()
    # niveles_maximos = inscripcionmalla.malla.niveles_regulares
    # if poraprobacion >= 100:
    #     data['nivel'] = True
    #     vali_tenido += 1
    # PASO 3
    vali_alter += 1
    if inscripcion.adeuda_a_la_fecha() == 0:
        data['deudas'] = True
        vali_tenido += 1
    data['deudasvalor'] = inscripcion.adeuda_a_la_fecha()
    # PASO 4
    vali_alter += 1
    ficha = 0
    if inscripcion.persona.nombres and inscripcion.persona.apellido1 and inscripcion.persona.apellido2 and inscripcion.persona.nacimiento and inscripcion.persona.cedula and inscripcion.persona.nacionalidad and inscripcion.persona.email and inscripcion.persona.estado_civil and inscripcion.persona.sexo:
        data['datospersonales'] = True
        ficha += 1
    if inscripcion.persona.paisnacimiento and inscripcion.persona.provincianacimiento and inscripcion.persona.cantonnacimiento and inscripcion.persona.parroquianacimiento:
        data['datosnacimientos'] = True
        ficha += 1
    examenfisico = inscripcion.persona.datos_examen_fisico()
    if inscripcion.persona.sangre and examenfisico.peso and examenfisico.talla:
        data['datosmedicos'] = True
        ficha += 1
    if inscripcion.persona.pais and inscripcion.persona.provincia and inscripcion.persona.canton and inscripcion.persona.parroquia and inscripcion.persona.direccion and inscripcion.persona.direccion2 and inscripcion.persona.num_direccion and inscripcion.persona.telefono_conv or inscripcion.persona.telefono:
        data['datosdomicilio'] = True
        ficha += 1
    if perfil.raza:
        data['etnia'] = True
        ficha += 1
    if ficha == 5:
        vali_tenido += 1
    # PASO 5
    vali_alter += 1
    modulo_ingles = ModuloMalla.objects.filter(malla=malla, status=True).exclude(asignatura_id=782)
    numero_modulo_ingles = modulo_ingles.count()
    lista = []
    listaid = []
    for modulo in modulo_ingles:
        if inscripcion.estado_asignatura(modulo.asignatura) == NOTA_ESTADO_APROBADO:
            lista.append(modulo.asignatura.nombre)
            listaid.append(modulo.asignatura.id)
    data['modulo_ingles_aprobados'] = lista
    data['modulo_ingles_faltante'] = modulo_ingles.exclude(asignatura_id__in=[int(i) for i in listaid])
    if numero_modulo_ingles > 0:
        if numero_modulo_ingles == len(listaid):
            data['modulo_ingles'] = True
        #ponerlo dentro del if cuando valide ingles
        vali_tenido += 1
    # PASO 6
    vali_alter += 1
    totalhoras = 0
    practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.filter(inscripcion=inscripcion, status=True, culminada=True)
    data['malla_horas_practicas'] = malla.horas_practicas
    if practicaspreprofesionalesinscripcion.exists():
        for practicas in practicaspreprofesionalesinscripcion:
            if practicas.tiposolicitud == 3:
                totalhoras += practicas.horahomologacion if practicas.horahomologacion else 0
            else:
                totalhoras += practicas.numerohora
        if totalhoras >= malla.horas_practicas:
            data['practicaspreprofesionales'] = True
            vali_tenido += 1
    data['practicaspreprofesionalesvalor'] = totalhoras
    # PASO 7
    vali_alter += 1
    data['malla_horas_vinculacion'] = malla.horas_vinculacion
    horastotal = ParticipantesMatrices.objects.filter(matrizevidencia_id=2, status=True, proyecto__status=True,inscripcion_id=inscripcion.id).aggregate(horastotal=Sum('horas'))['horastotal']
    horastotal = horastotal if horastotal else 0
    if horastotal >= malla.horas_vinculacion:
        data['vinculacion'] = True
        vali_tenido += 1
    data['horas_vinculacion'] = horastotal
    # PASO 8
    vali_alter += 1
    asignatura = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(malla__id=32)
    data['record_computacion'] = record = RecordAcademico.objects.filter(inscripcion__id=inscripcion.id, asignatura__id__in=asignatura, aprobada=True)
    creditos_computacion = 0
    data['malla_creditos_computacion'] = malla.creditos_computacion
    for comp in record:
        creditos_computacion += comp.creditos
    if malla.creditos_computacion > 0:
        if creditos_computacion >= malla.creditos_computacion:
            data['computacion'] = True
        #poerlo dentro del if - cuando validen computacion
        vali_tenido += 1
    data['creditos_computacion'] = creditos_computacion
    if vali_alter == vali_tenido:
        data['aprueba'] = True
        requisitosaprobados = True

    data['computacion'] = True
    data['modulo_ingles'] = True
    data['requisitosaprobados'] = requisitosaprobados

    return data
