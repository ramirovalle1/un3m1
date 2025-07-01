# -*- coding: latin-1 -*-
from datetime import datetime, timedelta
import json
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.db import transaction
from decorators import secure_module, last_access
from sagest.models import Rubro
from settings import NOTA_ESTADO_EN_CURSO, MAXIMO_MATERIA_ONLINE, MATRICULACION_LIBRE, UTILIZA_GRATUIDADES, \
    PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD, PORCIENTO_PERDIDA_TOTAL_GRATUIDAD, NIVEL_MALLA_CERO
from sga.commonviews import adduserdata, materias_abiertas,materias_abiertas2, conflicto_materias_seleccionadas, nivel_matriculacion, \
    matricular, conflicto_materias_estudiante, contar_nivel, matricular_ingles_egresado
from sga.funciones import log, null_to_decimal, variable_valor
from sga.models import Materia, Asignatura, MateriaAsignada, Nivel, AsignaturaMalla, AlumnosPracticaMateria, Inscripcion


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    # 1 a 6 semestre de salud enfe nutri y fisio solo malla 2019 ok
    # 3 a 6 semestre Faci, educacion, comercial (solo mallas 2019)
    # modalidad en line no aplica solo presencial y semipresencial ok
    #bloquear turismo, idiomas
    # bloquear 6,7,8 no matricularse
    #21 al 26 mayo
    #primero procesar y luego habilitar la matricula
    #validar cupos y validar horarios

    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion
    inscripcionmalla = inscripcion.malla_inscripcion()
    mallaest = inscripcionmalla.malla.inicio.year
    confirmar_automatricula_admision = inscripcion.tiene_automatriculaadmision_por_confirmar(periodo)
    matricula = inscripcion.matricula()
    # if datetime(2021, 5, 28, 0, 0, 0).date() == datetime.now().date():
    # if confirmar_automatricula_admision and periodo.limite_agregacion < datetime.now().date():
    #     cordinacionid = inscripcion.carrera.coordinacion_carrera().id
    #     if cordinacionid in [9]:
    #         return HttpResponseRedirect("/?info=Estimado aspirante, el período de confirmación de la automatrícula ha culminado, usted no se encuentra matriculado")
    cordinacionid = inscripcion.carrera.coordinacion_carrera().id
    if cordinacionid in [9,7]:
        return HttpResponseRedirect("/?info=Estimado usuario, este módulo es solo para pregrado")

    # if inscripcion.carrera.modalidad == 3:
    #     return HttpResponseRedirect("/?info=Solo aplica para carreras con modalidad presencial y semipresencial")

    # #MODALIDAD EN LINEA
    # if inscripcion.carrera.modalidad == 3:
    #     matriculas = inscripcion.matricula_set.filter(nivel__periodo=periodo, cerrada=False)
    #     if matriculas.exists():
    #         matricula = matriculas[0]
    #         if matricula.nivelmalla.id < 1:
    #             return HttpResponseRedirect("/?info=Para las carrera de de modalidad En Linea, solo está para tercero y cuarto nivel.")
    #     else:
    #         if inscripcion.mi_nivel().nivel.id < 6 or inscripcion.mi_nivel().nivel.id > 4:
    #             return HttpResponseRedirect("/?info=Para las carrera de de modalidad En Linea, solo está para tercero y cuarto nivel.")

    if inscripcion.carrera.id in (variable_valor('CARRERA_NO_MATRICULAR_INGLES_ID')):
        return HttpResponseRedirect("/?info=No está habilitado para las carreras: Turismo presencial e Idiomas")

#para inscribir mayor a 6to nivel
    #recordar comentar esta linea el 26 de mayo 2021
    # if inscripcion.mi_nivel().nivel.id < 6:
    #  return HttpResponseRedirect("/?info= Sólo está habilitado para los estudiantes que aprobaron sexto, séptimo, octavo y egresados.")

    # if inscripcion.carrera.id == 110 or inscripcion.carrera.id == 111 or inscripcion.carrera.id == 112:
    #     if inscripcion.mi_nivel().nivel.id > 6:
    #         return HttpResponseRedirect("/?info=Para las carreras de Nutrición y Dietética, Enfermería y Fisioterapia solo está aperturado desde 1 hasta 6 nivel")
    # else:
    #     if (inscripcion.mi_nivel().nivel.id <2 or inscripcion.mi_nivel().nivel.id > 6) and mallaest >= 2019:
    #         return HttpResponseRedirect("/?info=Habilitado solo para mallas 2019 a partir de 3 hasta 6 nivel ")
        # if mallaest < 2019:
        #     return HttpResponseRedirect("/?info=Habilitado solo para mallas 2019")
    # if inscripcion.mi_nivel().nivel.id < 7 or matricula:
    #     return HttpResponseRedirect("/?info= Este módulo sólo está habilitado para egresados.")

    #
    # if inscripcion.mi_nivel().nivel.id < 8 and  mallaest == 2019:
    #     return HttpResponseRedirect("/?info= Este módulo sólo está habilitado para los estudiantes que aprobaron octavo y egresados de la malla 2019.")
    #

    # if not mallaest in [2019,2020,2021,2022,2012,2011,2010,2009,2013]:
    #     return HttpResponseRedirect("/?info= Este módulo sólo está habilitado para los estudiantes de malla 2019, 2012 y egresados.")


    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'materiasabiertas':
                # return materias_abiertas(request, True)
                return materias_abiertas2(request, True)
            if action == 'matricularinglesegresado':
                return matricular_ingles_egresado(request, True)
            if action == 'matricular':
                try:
                    persona = request.session['persona']
                    if inscripcion.matriculado():
                        matricula = inscripcion.matricula()
                    else:
                        return matricular(request, False, True)
                    mismaterias = json.loads(request.POST['materias'])
                    materias = Materia.objects.filter(status=True,id__in=[int(x) for x in mismaterias])
                    for materia in materias:
                        if not materia.capacidad_disponible() > 0:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": "bad", "mensaje": u"Lo sentimos, se termino el cupo: " + materia.nombre_completo()})
                    for materia in materias:
                        matriculas = matricula.inscripcion.historicorecordacademico_set.filter(asignatura=materia.asignatura).count() + 1
                        if matricula.materiaasignada_set.filter(materia=materia).exists():
                            transaction.set_rollback(True)
                            return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra matriculado en esta materia: " + materia.nombre_completo()})
                        materiaasignada = MateriaAsignada(matricula=matricula,
                                                          materia=materia,
                                                          notafinal=0,
                                                          asistenciafinal=100,
                                                          cerrado=False,
                                                          matriculas=matriculas,
                                                          observaciones='',
                                                          estado_id=NOTA_ESTADO_EN_CURSO
                                                          )
                        materiaasignada.save()
                        materiaasignada.asistencias()
                        materiaasignada.evaluacion()
                        materiaasignada.mis_planificaciones()
                        if matriculas > 1 or matricula.inscripcion.persona.tiene_otro_titulo(matricula.inscripcion):
                            matricula.nuevo_calculo_matricula_ingles(materiaasignada)
                    # matricula.actualizar_horas_creditos()
                    # matricula.agregacion_aux(request)
                    #
                    # matricula.actualiza_matricula()
                    # matricula.inscripcion.actualiza_estado_matricula()
                    # matricula.calcula_nivel()

                    log(u'Automatricula modulos: %s' % matricula, request, "add")
                    valorpagar = str(null_to_decimal(Rubro.objects.filter(status=True, persona=persona, cancelado=False,observacion="INGLÉS %s" % periodo.nombre).aggregate(valor=Sum('valortotal'))['valor']))
                    return JsonResponse({"result": "ok", "valorpagar": valorpagar})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al matricular"})

            if action == 'conflictohorario_aux':
                mismaterias = json.loads(request.POST['mismaterias'])
                nivel = contar_nivel(mismaterias)
                return JsonResponse({"result": "ok", "nivel": nivel})

            if action == 'conflictohorario':
                try:
                    mismaterias = json.loads(request.POST['mismaterias'])
                    excluidas = Asignatura.objects.filter(historicorecordacademico__inscripcion=inscripcion, historicorecordacademico__aprobada=False, historicorecordacademico__completoasistencia=True).distinct()
                    if inscripcion.matriculado():
                        matricula = inscripcion.matricula()
                        materias = Materia.objects.filter(Q(id__in=[int(x) for x in mismaterias]) | Q(id__in=[x.materia.id for x in matricula.materiaasignada_set.filter(status=True)])).exclude(asignatura__id__in=excluidas).distinct()
                    else:
                        materias = Materia.objects.filter(Q(status=True), Q(id__in=[int(x) for x in mismaterias])).exclude(asignatura__id__in=excluidas).distinct()
                    # conflicto = conflicto_materias_seleccionadas(materias)
                    alumnaspracticascongrupo = AlumnosPracticaMateria.objects.values_list('profesormateria__id','grupoprofesor__id').filter( materiaasignada__materia__id__in=materias.values_list('id'), materiaasignada__matricula=matricula, grupoprofesor__isnull=False)
                    conflicto = conflicto_materias_estudiante(materias, None, alumnaspracticascongrupo)
                    # if conflicto:
                    #     return JsonResponse({"result": "bad", "mensaje": conflicto})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al verificar."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        try:
            data['title'] = u'Matriculación de modulos online'
            hoy = datetime.now().date()
            # NO PUEDE TENER MATERIAS MAS DE 5 AñOS
            if not inscripcion.recordacademico_set.filter(status=True, fecha__gte=hoy - timedelta(days=1825)).exclude(noaplica=True).exists() and inscripcion.recordacademico_set.filter(status=True).exists():
                return HttpResponseRedirect("/?info=Debe de acercarse a secretaria para matricularse, por no haber tomado materias hace mas de 5 años.")
            # MATRICULACION OBLIGATORIA POR SECRETARIA SI ES 3RA MATRICULA
            # if inscripcion.tiene_tercera_matricula():
            #     return HttpResponseRedirect("/?info=Atencion: usted no puede matricularse en un modulo por tener 3ra matricula.")


            # ---------------- desabilitado por carlos---------------------
            # if not inscripcion.matriculado():
            #     return HttpResponseRedirect("/alu_automatricula")
            # ---------------- desabilitado por carlos---------------------
            if matricula:
                nivel = matricula.nivel
                data['nivel'] = matricula.nivel
                if matricula.materiaasignada_set.filter(status=True, materia__nivel_id=1501, materia__cerrado=False).exists():
                    return HttpResponseRedirect("/?info=Atencion: usted no puede matricularse en otro modulo por tener un modulo seleccionado.")
            else:
                nivel = None
                nivelid = nivel_matriculacion(inscripcion)
                if nivelid < 0:
                    if nivelid == -1:
                        # return HttpResponseRedirect("/?info=Su carrera no tiene coordinacion, o no se ha abierto un nivel para su carrera.")
                        return HttpResponseRedirect(u"/?info=El periodo de matriculación no se encuentra activo.")
                    if nivelid == -2:
                        return HttpResponseRedirect("/?info=No existen niveles con cupo para matricularse.")
                    if nivelid == -3:
                        return HttpResponseRedirect("/?info=No existen paralelos disponibles.")
                    if nivelid == -4:
                        return HttpResponseRedirect("/?info=No existen paralelos para su nivel.")
                else:
                    nivel = Nivel.objects.get(pk=nivelid)
                    a = inscripcion.puede_matricularse_seguncronograma(nivel.periodo)
                    if a[0] == 2:
                        return HttpResponseRedirect(u"/?info=Aún no está habilitado el cronograma de matriculación de su carrera.")
                    if a[0] == 3:
                        return HttpResponseRedirect(u"/?info=Usted no realizó su Pre-Matrícula (matricularse después de dos días de haber iniciado matrícula ordinaria).")
                # PERIODO ACTIVO PARA MATRICULACION
                if not nivel.periodo.matriculacionactiva:
                    return HttpResponseRedirect("/?info=El periodo de matriculación no se encuentra activo.")
                # PASO TODOS LOS FILTRO DE LIMITACIONES
                data['inscripcion'] = inscripcion
                inscripcionmalla = inscripcion.malla_inscripcion()
                if not inscripcionmalla:
                    return HttpResponseRedirect("/?info=Debe tener malla asociada para poder matricularse.")
                minivel = None
                asignaturasmalla = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(status=True, malla=inscripcion.mi_malla())
                fechaultimamateriaprobada = None
                ultimamateriaaprobada = inscripcion.recordacademico_set.filter(status=True, asignatura__id__in=asignaturasmalla).exclude(noaplica=True).order_by('-fecha')
                # if ultimamateriaaprobada:
                #     # sumo 5 años
                #     fechaultimamateriaprobada = ultimamateriaaprobada[0].fecha + timedelta(days=1810)
                # if fechaultimamateriaprobada:
                #     if fechaultimamateriaprobada < nivel.periodo.inicio:
                #         return HttpResponseRedirect(u"/?info=Reglamento del Régimen Académico - DISPOSICIONES GENERALES: QUINTA.- Si un estudiante no finaliza su carrera o programa y se retira, podrá reingresar a la misma carrera o programa en el tiempo máximo de 5 años contados a partir de la fecha de su retiro. Si no estuviere aplicándose el mismo plan de estudios deberá completar todos los requisitos establecidos en el plan de estudios vigente a la fecha de su reingreso. Cumplido este plazo máximo para el referido reingreso, deberá reiniciar sus estudios en una carrera o programa vigente. En este caso el estudiante podrá homologar a través del mecanismo de validación de conocimientos, las asignaturas, cursos o sus equivalentes, en una carrera o programa vigente, de conformidad con lo establecido en el presente Reglamento.")

                if inscripcion.matricula_periodo(periodo):
                    minivel = inscripcion.matricula_periodo(periodo).nivelmalla
                data['semestre'] = semestre = inscripcion.avance_semestre(minivel)
                data['materiasmalla'] = inscripcionmalla.malla.asignaturamalla_set.filter(status=True).exclude(nivelmalla__id=NIVEL_MALLA_CERO).order_by('nivelmalla', 'ejeformativo')
                data['matriculacion_libre'] = MATRICULACION_LIBRE
                data['materiasmaximas'] = MAXIMO_MATERIA_ONLINE
                data['nivel'] = nivel
                data['malla'] = inscripcionmalla.malla
                data['total_materias_nivel'] = inscripcion.total_materias_nivel()
                data['total_materias_pendientes_malla'] = inscripcion.total_materias_pendientes_malla()
                data['materiasmodulos'] = inscripcionmalla.malla.modulomalla_set.filter(status=True)
                data['utiliza_gratuidades'] = variable_valor('UTILIZA_GRATUIDADES_INGLES')
                data['porciento_perdida_parcial_gratuidad'] = PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD
                data['porciento_perdida_total_gratuidad'] = PORCIENTO_PERDIDA_TOTAL_GRATUIDAD
                data['fichasocioeconomicainec'] = persona.fichasocioeconomicainec()
                return render(request, "alu_automatriculamodulos/view1.html", data)

            data['inscripcionalumno'] = Inscripcion.objects.get(pk=inscripcion.id)
            data['matricula'] = matricula
            malla = inscripcion.malla_inscripcion().malla
            if not malla:
                return HttpResponseRedirect("/?info=Debe tener malla asociada para poder matricularse.")

            data['malla'] = malla
            # carlos se le aumento el if, el else es lo que estaba
            if AsignaturaMalla.objects.filter(status=True,malla=malla, asignatura__modulo=True).exists():
                inscripcionmalla = inscripcion.malla_inscripcion()
                listamodulos = inscripcionmalla.malla.modulomalla_set.values_list('asignatura_id').filter(status=True)
                data['materiasmodulos'] = Asignatura.objects.filter(pk__in=listamodulos).distinct()
            else:
                # if inscripcion.aplica_b2:
                #     asignaturasvirtuales = Materia.objects.values_list('asignatura__id', flat=True).filter(nivel__periodo=nivel.periodo, tipomateria=2)
                #     data['materiasmodulos'] = Asignatura.objects.filter(Q(id__in=[x.asignatura.id for x in malla.asignaturamalla_set.all()]) | Q(id__in=[x.asignatura.id for x in malla.modulomalla_set.all()]), modulo=True).exclude(id__in=asignaturasvirtuales).distinct()
                # else:
                data['materiasmodulos'] = Asignatura.objects.filter(Q(id__in=[x.asignatura.id for x in malla.asignaturamalla_set.filter(status=True)]) | Q(id__in=[x.asignatura.id for x in malla.modulomalla_set.filter(status=True)]), modulo=True).distinct()
            # ------------   carlos aumentado -----------------------
            if not matricula:
                data['permiteagregaciones'] = nivel.periodo.limite_agregacion >= datetime.now().date()
            else:
                data['permiteagregaciones'] = matricula.nivel.periodo.limite_agregacion >= datetime.now().date()
            # ------------   carlos aumentado -----------------------
            #     data['permiteagregaciones'] = matricula.nivel.periodo.limite_agregacion >= datetime.now().date()
            # for x in  data['materiasmodulos']:
            #     inscripcion.puede_tomar_materia_modulo(x)
            return render(request, "alu_automatriculamodulos/view.html", data)
        except Exception as ex:
            return JsonResponse({"result": "bad", "mensaje": u"Error al verificar."})
