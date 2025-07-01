# coding=utf-8
import sys
from hashlib import md5
from secrets import token_hex
from datetime import datetime, timedelta
from django.db import connection, transaction, connections
from django.db.models import Sum, F
from rest_framework import status
from api.helpers.response_herlper import Helper_Response
from bd.funciones import generate_code
from bd.models import UserToken
from matricula.funciones import TIPO_PROFESOR_PRACTICA, valida_conflicto_materias_estudiante_enroll, \
    agregacion_aux_pregrado, calcula_nivel, get_client_ip, generar_acta_compromiso, pre_inscripcion_practicas_pre_profesionales
from matricula.models import MateriaAsignadaToken, MatriculaToken
from settings import HOMITIRCAPACIDADHORARIO, MATRICULACION_LIBRE, NOTA_ESTADO_EN_CURSO, RUBRO_ARANCEL, EMAIL_DOMAIN, \
    DEBUG
from sga.funciones import variable_valor, fechatope, log, null_to_decimal, generar_nombre
from sga.funcionesxhtml2pdf import conviert_html_to_pdf_save_file_model
from sga.models import PerfilUsuario, Materia, GruposProfesorMateria, ProfesorMateria, Matricula, MateriaAsignada, \
    AlumnosPracticaMateria, miinstitucion, CUENTAS_CORREOS, ConfirmaCapacidadTecnologica
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt

unicode = str


def validate_entry_to_student_api(ePerfilUsuario, level=None):
    try:
        if not ePerfilUsuario.es_estudiante():
            raise NameError(u"Solo los perfiles de aspirante pueden ingresar al modulo.")
        if not level or not level in ['admision', 'pregrado', 'posgrado']:
            raise NameError(u"Solicitud no identificada")

        inscripcion = ePerfilUsuario.inscripcion

        if level == 'admision':
            if not inscripcion.mi_coordinacion().id in [9]:
                raise NameError(u"Estimado/a aspirante, este módulo solo se encuentra activo para estudiantes de admisión")
        elif level == 'pregrado':
            if not inscripcion.mi_coordinacion().id in [1, 2, 3, 4, 5]:
                raise NameError(u"Estimado/a estudiante, este módulo solo se encuentra activo para estudiantes de pregrado")
        elif level == 'posgrado':
            if not inscripcion.mi_coordinacion().id in [7, 10]:
                raise NameError(u"Estimado/a estudiante, este módulo solo se encuentra activo para estudiantes de posgrado")

        if inscripcion.bloqueomatricula:
            raise NameError(u"Estimado/a, su matrícula se encuentra bloqueada, por favor contactarse con secretaria de la coordinación")
        if not DEBUG:
            if inscripcion.es_graduado() or inscripcion.egresado() or inscripcion.estainactivo() or inscripcion.retiro_carrera():
                raise NameError(u"Estimado/a, solo se permiten aspirantes activos")
        return True, None
    except Exception as ex:
        return False, ex.__str__()


def action_enroll_pregrado(request, inscripcion, periodomatricula, nivel, mis_clases, cobro, casoultimamatricula):
    with transaction.atomic():
        try:
            hoy = datetime.now().date()
            persona = inscripcion.persona
            periodo = periodomatricula.periodo
            malla = inscripcion.mi_malla()
            # PERDIDA DE CARRERA POR 4TA MATRICULA
            if inscripcion.tiene_perdida_carrera(periodomatricula.num_matriculas):
                raise NameError(u"Tiene limite de matriculas.")
            # regular o irregular
            tipo_matricula_ri= None

            try:
                tipo_matricula_ri = int(request.data['tipo_matricula'])
            except Exception as ex:
                tipo_matricula_ri = int(request.session.get('tipo_matricula'))

            # MATERIAS PRACTICAS
            mis_practicas = []
            mis_materias_congrupo = []
            for m in mis_clases:
                if m['practica']:
                    for k, v in m['practica'].items():
                        if k == 'id':
                            mis_practicas.append(v)
                            mis_materias_congrupo.append(int(m['id']))
            mis_materias = []
            for m in mis_clases:
                mis_materias.append(int(m['id']))
            materias = Materia.objects.filter(id__in=mis_materias,status=True)
            mis_materias_singrupo = []
            for m in materias:
                if m.asignaturamalla.tipomateria_id == TIPO_PROFESOR_PRACTICA:
                    if not m.id in mis_materias_congrupo:
                        mis_materias_singrupo.append(m.id)
            # MATERIAS PRACTICAS
            grupoprofesormaterias = GruposProfesorMateria.objects.filter(id__in=mis_practicas)
            # profesoresmateriassingrupo = ProfesorMateria.objects.filter(id__in=materias.values('profesormateria__id').filter(profesormateria__gruposprofesormateria__isnull=True)).exclude(materia__in=grupoprofesormaterias.values('profesormateria__materia'))
            profesoresmateriassingrupo = ProfesorMateria.objects.filter(materia_id__in=mis_materias_singrupo, tipoprofesor_id=TIPO_PROFESOR_PRACTICA)

            if periodomatricula.valida_horario_materia:
                # VALIDACION MATERIAS TIENE PRACTICAS PARA LA CARRERA DE ENFERMERIA Y NUTRICION
                if inscripcion.carrera.id in [1, 3]:
                    totalpracticas = len(materias.values('id').filter(asignaturamalla__practicas=True, id__in=grupoprofesormaterias.values('materia__id'))) + len(materias.values('id').filter(asignaturamalla__practicas=True, id__in=grupoprofesormaterias.values('profesormateria__materia__id')))
                    if not len(materias.values('id').filter(asignaturamalla__practicas=True)) == totalpracticas:
                        raise NameError(u"Falta de seleccionar horario de practicas")

            if periodomatricula.valida_conflicto_horario and malla.modalidad_id != 3:
                conflicto, msg = valida_conflicto_materias_estudiante_enroll(mis_clases)
                if conflicto:
                    raise NameError(msg)

            if periodomatricula.valida_cupo_materia:
                # VERIFICANDO CUPO MATERIAS PRACTICAS EN PROFESOR MATERIA CON PÁRALELO
                for gpm in grupoprofesormaterias:
                    validar = True
                    if gpm.profesormateria.materia.tipomateria == TIPO_PROFESOR_PRACTICA:
                        validar = variable_valor('VALIDAR_HORARIO_CUPO_MATERIA_VIRTUAL')
                    if validar:
                        if not HOMITIRCAPACIDADHORARIO and gpm.cuposdisponiblesgrupoprofesor() <= 0:
                            raise NameError(u"Capacidad limite de la materia en la práctica:  " + unicode(gpm.profesormateria.materia) + ", seleccione otro.")

                # LIMITE DE MATRICULAS EN EL PARALELO
                if not MATRICULACION_LIBRE and nivel.capacidadmatricula <= len(nivel.matricula_set.values('id')):
                    raise NameError(u"Capacidad matricula limite del paralelo: " + unicode(nivel.paralelo) + ", seleccione otro.")
                # habilitar cuando sea matriculacion
                # if estudiante and 'matriculamodulos' not in request.POST:
                #     if nivel.fechatopematriculaex and hoy > nivel.fechatopematriculaex:
                #         return JsonResponse({"result": "bad", "reload": False, "mensaje": u"Fuera del periodo de matriculacion."})
                # habilitar cuando sea matriculacion


            # MATRICULA
            costo_materia_total = 0
            if inscripcion.matricula_set.values('id').filter(nivel__periodo=periodo).exists():
                raise NameError(u"Ya se encuentra matriculado.")

            for materia in materias:
                if periodomatricula.valida_cupo_materia:
                    if not materia.tiene_cupo_materia():
                        if materia.cupoadicional > 0:
                            if not materia.existen_cupos_con_adicional():
                                raise NameError(u"Capacidad limite de la materia: " + unicode(materia.asignatura) + ", seleccione otro.")
                        else:
                            raise NameError(u"Capacidad limite de la materia: " + unicode(materia.asignatura) + ", seleccione otro.")
            with transaction.atomic():
                matricula = Matricula(inscripcion=inscripcion,
                                      nivel=nivel,
                                      pago=False,
                                      iece=False,
                                      becado=False,
                                      porcientobeca=0,
                                      fecha=datetime.now().date(),
                                      hora=datetime.now().time(),
                                      fechatope=fechatope(datetime.now().date()),
                                      termino=True,
                                      fechatermino=datetime.now())
                matricula.save(request)
                matricula.grupo_socio_economico(tipo_matricula_ri, request)
                # matriculagruposocioeconomico = matricula.matriculagruposocioeconomico_set.all()[0]
                # matriculagruposocioeconomico.tipomatricula=tipo_matricula
                # matriculagruposocioeconomico.save()
                matricula.confirmar_matricula(request)
                codigoitinerario = 0
                for materia in materias:
                    matriculacupoadicional = False
                    if not inscripcion.itinerario or inscripcion.itinerario < 1:
                        if materia.asignaturamalla.itinerario > 0:
                            codigoitinerario = int(materia.asignaturamalla.itinerario)
                    if periodomatricula.valida_cupo_materia:
                        if not materia.tiene_cupo_materia():
                            if materia.cupoadicional > 0:
                                if not materia.existen_cupos_con_adicional():
                                    transaction.set_rollback(True)
                                    raise NameError(u"Capacidad limite de la materia: " + unicode(materia.asignatura) + ", seleccione otro.")
                                else:
                                    matriculacupoadicional = True
                            else:
                                transaction.set_rollback(True)
                                raise NameError(u"Capacidad limite de la materia: " + unicode(materia.asignatura) + ", seleccione otro.")

                    matriculas = len(matricula.inscripcion.historicorecordacademico_set.values('id').filter(asignatura=materia.asignatura, fecha__lt=materia.nivel.fin)) + 1
                    materiaasignada = MateriaAsignada(matricula=matricula,
                                                      materia=materia,
                                                      notafinal=0,
                                                      asistenciafinal=0,
                                                      cerrado=False,
                                                      matriculas=matriculas,
                                                      observaciones='',
                                                      estado_id=NOTA_ESTADO_EN_CURSO,
                                                      casoultimamatricula=casoultimamatricula,
                                                      sinasistencia=False)

                    if periodo.valida_asistencia:
                        if malla.modalidad.es_enlinea():
                            materiaasignada.sinasistencia = True
                    else:
                        materiaasignada.sinasistencia = True

                    materiaasignada.save(request)

                    if matriculacupoadicional:
                        materia.totalmatriculadocupoadicional += 1
                        materia.cupo += 1
                        materia.save(request, update_fields=['totalmatriculadocupoadicional', 'cupo'])
                        log(u'Estudiante matriculado en cupo adicional materia: %s - estudiante: %s y se aumento un cupo en materia' % (materia, matricula), request, "add")
                    if materia.asignaturamalla.asignaturapracticas and materia.asignaturamalla.asignaturavinculacion:
                        pdf2, response2 = generar_acta_compromiso(materiaasignada)
                        pre_inscripcion_practicas_pre_profesionales(request, materiaasignada, matricula, pdf2, 'add')
                        materiaasignada.actacompromisopracticas = pdf2
                        materiaasignada.actacompromisovinculacion = pdf2
                    elif materia.asignaturamalla.asignaturapracticas:
                        pdf, response = generar_acta_compromiso(materiaasignada)
                        pre_inscripcion_practicas_pre_profesionales(request, materiaasignada, matricula, pdf, 'add')
                        materiaasignada.actacompromisopracticas = pdf
                    elif materia.asignaturamalla.asignaturavinculacion:
                        pdfv, responsev = generar_acta_compromiso(materiaasignada)
                        materiaasignada.actacompromisovinculacion = pdfv
                    materiaasignada.asistencias()
                    materiaasignada.evaluacion()
                    materiaasignada.mis_planificaciones()
                    materiaasignada.save(request)
                    # MATRICULA EN LA PRACTICA QUE NO TENGAN GRUPO
                    if profesoresmateriassingrupo.values('id').filter(materia=materia).exists():
                        profemate = profesoresmateriassingrupo.filter(materia=materia)[0]
                        alumnopractica = AlumnosPracticaMateria(materiaasignada=materiaasignada,
                                                                profesormateria=profemate)
                        alumnopractica.save(request)
                        log(u'Materia (%s) con profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s)' % (materia, profemate, materiaasignada, alumnopractica.id), request, "add")
                    # MATRICULA EN LA PRACTICA QUE SI TENGAN GRUPOS
                    elif grupoprofesormaterias.values('id').filter(profesormateria__materia=materia).exists():
                        profemate_congrupo = grupoprofesormaterias.filter(profesormateria__materia=materia)[0]
                        if periodomatricula.valida_cupo_materia:
                            validar = True
                            if profemate_congrupo.profesormateria.materia.tipomateria == 2:
                                validar = variable_valor('VALIDAR_HORARIO_CUPO_MATERIA_VIRTUAL')
                            if validar:
                                if not HOMITIRCAPACIDADHORARIO and profemate_congrupo.cuposdisponiblesgrupoprofesor() <= 0:
                                    raise NameError(u"Capacidad limite de la materia en la práctica:  " + unicode(profemate_congrupo.profesormateria.materia) + ", seleccione otro.")

                        alumnopractica = AlumnosPracticaMateria(materiaasignada=materiaasignada,
                                                                profesormateria=profemate_congrupo.profesormateria,
                                                                grupoprofesor=profemate_congrupo)
                        alumnopractica.save(request)
                        log(u'Materia (%s) con grupo profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s)' % (materia, profemate_congrupo, materiaasignada, alumnopractica.id), request, "add")
                    log(u'Materia seleccionada matricula: %s' % materiaasignada, request, "add")
                matricula.actualizar_horas_creditos()
                if not inscripcion.itinerario or inscripcion.itinerario < 1:
                    inscripcion.itinerario = codigoitinerario
                    inscripcion.save(request, update_fields=['itinerario'])
            # with transaction.atomic():
            #     if int(cobro) > 0:
            #         agregacion_aux_pregrado(request, matricula)
            #     matricula.actualiza_matricula()
            #     matricula.inscripcion.actualiza_estado_matricula()
            #     matricula.grupo_socio_economico(tipo_matricula_ri)
            #     calcula_nivel(matricula)

            matricula.agregacion_aux(request)
            matricula.calcula_nivel()

            if periodomatricula.valida_envio_mail:
                # send_html_mail("Automatricula", "emails/matricula.html",
                #                {
                #                    'sistema': request.session['nombresistema'],
                #                    'matricula': matricula,
                #                    't': miinstitucion(),
                #                    'ip': get_client_ip(request),
                #                }, inscripcion.persona.lista_emails_envio(), [],
                #                cuenta=CUENTAS_CORREOS[0][1])
                pass
            log(u'Automatricula estudiante: %s' % matricula, request, "add")

            valorpagar = str(null_to_decimal(matricula.rubro_set.filter(status=True).aggregate(valor=Sum('valortotal'))['valor']))

            descripcionarancel = ''
            valorarancel = ''
            if (ra := matricula.rubro_set.filter(status=True, tipo_id=RUBRO_ARANCEL).first()) is not None:
                descripcionarancel = ra.nombre
                valorarancel = str(ra.valortotal)

                matricula.aranceldiferido = 2
                matricula.save(request)

            ConfirmaCapacidadTecnologica.objects.filter(persona=matricula.inscripcion.persona).update(confirmado=True)
            # request.session['periodo'] = matricula.nivel.periodo
            return True, None, {"valorpagar": valorpagar, "descripcionarancel": descripcionarancel, "valorarancel": valorarancel, "phase": matricula.id, "periodo_id": encrypt(matricula.nivel.periodo.id)}
        except Exception as ex:
            transaction.set_rollback(True)
            return False, ex, {}


def action_enroll_posgrado(request, inscripcion, periodomatricula, nivel, mis_clases, cobro, casoultimamatricula):
    try:
        hoy = datetime.now().date()
        persona = inscripcion.persona
        periodo = periodomatricula.periodo
        malla = inscripcion.mi_malla()

        # PERDIDA DE CARRERA POR 4TA MATRICULA
        if inscripcion.tiene_perdida_carrera(periodomatricula.num_matriculas):
            raise NameError(u"Tiene limite de matriculas.")
        # regular o irregular
        tipo_matricula_ri = int(request.data['tipo_matricula'])
        # MATERIAS PRACTICAS
        mis_practicas = []
        mis_materias_congrupo = []
        for m in mis_clases:
            if m['practica']:
                for k, v in m['practica'].items():
                    if k == 'id':
                        mis_practicas.append(v)
                        mis_materias_congrupo.append(int(m['id']))
        mis_materias = []
        for m in mis_clases:
            mis_materias.append(int(m['id']))
        materias = Materia.objects.filter(id__in=mis_materias,status=True)
        mis_materias_singrupo = []
        for m in materias:
            if m.asignaturamalla.tipomateria_id == TIPO_PROFESOR_PRACTICA:
                if not m.id in mis_materias_congrupo:
                    mis_materias_singrupo.append(m.id)
        # MATERIAS PRACTICAS
        grupoprofesormaterias = GruposProfesorMateria.objects.filter(id__in=mis_practicas)
        # profesoresmateriassingrupo = ProfesorMateria.objects.filter(id__in=materias.values('profesormateria__id').filter(profesormateria__gruposprofesormateria__isnull=True)).exclude(materia__in=grupoprofesormaterias.values('profesormateria__materia'))
        profesoresmateriassingrupo = ProfesorMateria.objects.filter(materia_id__in=mis_materias_singrupo, tipoprofesor_id=TIPO_PROFESOR_PRACTICA)

        if periodomatricula.valida_horario_materia:
            # VALIDACION MATERIAS TIENE PRACTICAS PARA LA CARRERA DE ENFERMERIA Y NUTRICION
            if inscripcion.carrera.id in [1, 3]:
                totalpracticas = len(materias.values('id').filter(asignaturamalla__practicas=True, id__in=grupoprofesormaterias.values('materia__id'))) + len(materias.values('id').filter(asignaturamalla__practicas=True, id__in=grupoprofesormaterias.values('profesormateria__materia__id')))
                if not len(materias.values('id').filter(asignaturamalla__practicas=True)) == totalpracticas:
                    raise NameError(u"Falta de seleccionar horario de practicas")

        if periodomatricula.valida_conflicto_horario and inscripcion.carrera.modalidad != 3:
            conflicto, msg = valida_conflicto_materias_estudiante_enroll(mis_clases)
            if conflicto:
                raise NameError(msg)

        if periodomatricula.valida_cupo_materia:
            # VERIFICANDO CUPO MATERIAS PRACTICAS EN PROFESOR MATERIA CON PÁRALELO
            for gpm in grupoprofesormaterias:
                validar = True
                if gpm.profesormateria.materia.tipomateria == TIPO_PROFESOR_PRACTICA:
                    validar = variable_valor('VALIDAR_HORARIO_CUPO_MATERIA_VIRTUAL')
                if validar:
                    if not HOMITIRCAPACIDADHORARIO and gpm.cuposdisponiblesgrupoprofesor() <= 0:
                        raise NameError(u"Capacidad limite de la materia en la práctica:  " + unicode(gpm.profesormateria.materia) + ", seleccione otro.")

            # LIMITE DE MATRICULAS EN EL PARALELO
            if not MATRICULACION_LIBRE and nivel.capacidadmatricula <= len(nivel.matricula_set.values('id')):
                raise NameError(u"Capacidad matricula limite del paralelo: " + unicode(nivel.paralelo) + ", seleccione otro.")

        # MATRICULA
        costo_materia_total = 0
        for materia in materias:
            if periodomatricula.valida_cupo_materia:
                if not materia.tiene_cupo_materia():
                    if materia.cupoadicional > 0:
                        if not materia.existen_cupos_con_adicional():
                            raise NameError(u"Capacidad limite de la materia: " + unicode(materia.asignatura) + ", seleccione otro.")
                    else:
                        raise NameError(u"Capacidad limite de la materia: " + unicode(materia.asignatura) + ", seleccione otro.")
        with transaction.atomic():
            matricula = None
            if not inscripcion.matricula_set.values('id').filter(nivel__periodo=periodo).exists():
                matricula = Matricula(inscripcion=inscripcion,
                                      nivel=nivel,
                                      pago=False,
                                      iece=False,
                                      becado=False,
                                      porcientobeca=0,
                                      fecha=datetime.now().date(),
                                      hora=datetime.now().time(),
                                      fechatope=fechatope(datetime.now().date()),
                                      termino=True,
                                      fechatermino=datetime.now())
                matricula.save(request)
            else:
                matricula = inscripcion.matricula_set.filter(nivel__periodo=periodo)[0]

            matricula.confirmar_matricula()
            codigoitinerario = 0
            for materia in materias:
                matriculacupoadicional = False
                if not inscripcion.itinerario or inscripcion.itinerario < 1:
                    if materia.asignaturamalla.itinerario > 0:
                        codigoitinerario = int(materia.asignaturamalla.itinerario)
                if periodomatricula.valida_cupo_materia:
                    if not materia.tiene_cupo_materia():
                        if materia.cupoadicional > 0:
                            if not materia.existen_cupos_con_adicional():
                                transaction.set_rollback(True)
                                raise NameError(u"Capacidad limite de la materia: " + unicode(materia.asignatura) + ", seleccione otro.")
                            else:
                                matriculacupoadicional = True
                        else:
                            transaction.set_rollback(True)
                            raise NameError(u"Capacidad limite de la materia: " + unicode(materia.asignatura) + ", seleccione otro.")

                matriculas = len(matricula.inscripcion.historicorecordacademico_set.values('id').filter(asignatura=materia.asignatura, fecha__lt=materia.nivel.fin)) + 1
                materiaasignada = MateriaAsignada(matricula=matricula,
                                                  materia=materia,
                                                  notafinal=0,
                                                  asistenciafinal=0,
                                                  cerrado=False,
                                                  matriculas=matriculas,
                                                  observaciones='',
                                                  estado_id=NOTA_ESTADO_EN_CURSO,
                                                  casoultimamatricula=casoultimamatricula,
                                                  sinasistencia=False)
                if periodo.valida_asistencia:
                    if malla.modalidad.es_enlinea():
                        materiaasignada.sinasistencia = True
                else:
                    materiaasignada.sinasistencia = True

                materiaasignada.save(request)
                if matriculacupoadicional:
                    materia.totalmatriculadocupoadicional += 1
                    materia.cupo += 1
                    materia.save(request)
                    log(u'Estudiante matriculado en cupo adicional materia: %s - estudiante: %s y se aumento un cupo en materia' % (materia, matricula), request, "add")
                materiaasignada.asistencias()
                materiaasignada.evaluacion()
                materiaasignada.mis_planificaciones()
                materiaasignada.save(request)
                # MATRICULA EN LA PRACTICA QUE NO TENGAN GRUPO
                if profesoresmateriassingrupo.values('id').filter(materia=materia).exists():
                    profemate = profesoresmateriassingrupo.filter(materia=materia)[0]
                    alumnopractica = AlumnosPracticaMateria(materiaasignada=materiaasignada,
                                                            profesormateria=profemate)
                    alumnopractica.save(request)
                    log(u'Materia (%s) con profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s)' % (materia, profemate, materiaasignada, alumnopractica.id), request, "add")
                # MATRICULA EN LA PRACTICA QUE SI TENGAN GRUPOS
                elif grupoprofesormaterias.values('id').filter(profesormateria__materia=materia).exists():
                    profemate_congrupo = grupoprofesormaterias.filter(profesormateria__materia=materia)[0]
                    if periodomatricula.valida_cupo_materia:
                        validar = True
                        if profemate_congrupo.profesormateria.materia.tipomateria == 2:
                            validar = variable_valor('VALIDAR_HORARIO_CUPO_MATERIA_VIRTUAL')
                        if validar:
                            if not HOMITIRCAPACIDADHORARIO and profemate_congrupo.cuposdisponiblesgrupoprofesor() <= 0:
                                raise NameError(u"Capacidad limite de la materia en la práctica:  " + unicode(profemate_congrupo.profesormateria.materia) + ", seleccione otro.")

                    alumnopractica = AlumnosPracticaMateria(materiaasignada=materiaasignada,
                                                            profesormateria=profemate_congrupo.profesormateria,
                                                            grupoprofesor=profemate_congrupo)
                    alumnopractica.save(request)
                    log(u'Materia (%s) con grupo profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s)' % (materia, profemate_congrupo, materiaasignada, alumnopractica.id), request, "add")
                log(u'Materia seleccionada matricula: %s' % materiaasignada, request, "add")
            matricula.actualizar_horas_creditos()
            if not inscripcion.itinerario or inscripcion.itinerario < 1:
                inscripcion.itinerario = codigoitinerario
                inscripcion.save(request)

        matricula.actualiza_matricula()
        matricula.inscripcion.actualiza_estado_matricula()
        matricula.asigna_matricula_rubros()

        matricula.agregacion_aux(request)
        matricula.calcula_nivel()

        log(u'Automatricula estudiante: %s' % matricula, request, "add")

        inccohorte = inscripcion.inscripcioncohorte_set.filter(status=True)[0]
        valorpagar = str(null_to_decimal(persona.rubro_set.filter(status=True, inscripcion=inccohorte, cancelado=False, fechavence__lt=hoy).aggregate(valor=Sum('valortotal'))['valor']))
        descripcionarancel = ''
        valorarancel = ''

        ConfirmaCapacidadTecnologica.objects.filter(persona=matricula.inscripcion.persona).update(confirmado=True)
        return True, None, {"valorpagar": valorpagar, "descripcionarancel": descripcionarancel, "valorarancel": valorarancel, "phase": matricula.id, "periodo_id": encrypt(matricula.nivel.periodo.id)}
    except Exception as ex:
        transaction.set_rollback(True)
        return False, ex, {}


def generateCodeDeleteMatricula(request, matricula):
    with transaction.atomic():
        try:
            fecha = datetime.now().date()
            hora = datetime.now().time()
            fecha_hora = fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__()
            if not matricula:
                raise NameError(u"Matricula no encontrada")
            inscripcion = matricula.inscripcion
            persona = inscripcion.persona
            usuario = persona.usuario
            if not usuario:
                raise NameError(u"Usuario no encontrado")
            code = generate_code(6)
            token = md5(str(encrypt(usuario.id) + fecha_hora).encode("utf-8")).hexdigest()
            if matricula.matriculatoken_set.values("id").filter(status=True, isActive=True, user_token__user=usuario, user_token__isActive=True, user_token__action_type=3, user_token__date_expires__gte=datetime.now()).exists():
                raise NameError(u"Mantiene una recuperación de contraseña activa.")
            else:
                # BUSCAR TODAS LAS MATERIAS ASIGNADAS QUE TENGAN TOKEN ACTIVOS PARA INACTIVAR
                mis_materias = matricula.mismaterias()
                aMateriaAsignadaTokens = MateriaAsignadaToken.objects.filter(status=True, materia_asignada__in=mis_materias, isActive=True).update(isActive=False)
                UserToken.objects.filter(user=usuario, isActive=True, action_type=2).update(isActive=False)
                aMatriculaTokens = MatriculaToken.objects.filter(matricula=matricula, status=True, isActive=True).update(isActive=False)
                UserToken.objects.filter(user=usuario, isActive=True, action_type=3).update(isActive=False)
                eUserToken = UserToken(user=usuario,
                                       token=token,
                                       action_type=3,
                                       date_expires=datetime.now() + timedelta(days=1),
                                       app=4,
                                       isActive=True)
                eUserToken.save(request)
                eMatriculaToken = MatriculaToken(matricula=matricula,
                                                 user_token=eUserToken,
                                                 codigo=code,
                                                 isActive=True,
                                                 num_email=1)
                eMatriculaToken.save(request)
                log(u'Genera codigo y token de eliminar la matricula: %s' % matricula, request, "add")
                app_label = 'sie'
                sistema = u'Sistema Integrado Estudiantil'
                try:
                    send_html_mail("Código de confirmación - Eliminar matrícula",
                                   "emails/solicitud_eliminar_matricula.html",
                                   {'sistema': sistema,
                                    'fecha': datetime.now().date,
                                    'persona': persona,
                                    'matricula': matricula,
                                    'fecha_g': eMatriculaToken.fecha_creacion.date(),
                                    'hora_g': eMatriculaToken.fecha_creacion.time(),
                                    'token': token,
                                    'codigo': code,
                                    'app_label': app_label,
                                    't': miinstitucion(),
                                    'ip': get_client_ip(request),
                                    'dominio': EMAIL_DOMAIN
                                    },
                                   persona.lista_emails(), [],
                                   cuenta=CUENTAS_CORREOS[7][1])
                except Exception as ex1:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass
            return Helper_Response(isSuccess=True, data={}, message=f'Se genero un correo con un código o link para eliminar matrícula.',status=status.HTTP_200_OK)
        except Exception as ex:
            transaction.set_rollback(True)
            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)


def reenvioCodeDeleteMatricula(request, matricula):
    with transaction.atomic():
        try:
            inscripcion = matricula.inscripcion
            persona = inscripcion.persona
            usuario = persona.usuario
            if not matricula.matriculatoken_set.values("id").filter(status=True, isActive=True, user_token__user=usuario, user_token__isActive=True, user_token__action_type=3, user_token__date_expires__gte=datetime.now()).exists():
                raise NameError(u"No mantiene código activo.")
            eMatriculaToken = matricula.matriculatoken_set.filter(status=True, isActive=True, user_token__user=usuario, user_token__isActive=True, user_token__action_type=3, user_token__date_expires__gte=datetime.now())[0]
            eUserToken = eMatriculaToken.user_token
            eMatriculaToken.num_email = eMatriculaToken.num_email + 1
            eMatriculaToken.save(request)
            log(u'Reenvio de codigo y token de eliminar matricula: %s' % matricula, request, "add")
            app_label = 'sie'
            sistema = u'Sistema Integrado Estudiantil'
            try:
                send_html_mail("Código de confirmación - Retiro de materia",
                               "emails/solicitud_eliminar_matricula.html",
                               {'sistema': sistema,
                                'fecha': datetime.now().date,
                                'fecha_g': eMatriculaToken.fecha_creacion.date(),
                                'hora_g': eMatriculaToken.fecha_creacion.time(),
                                'persona': persona,
                                'matricula': matricula,
                                'token': eUserToken.token,
                                'codigo': eMatriculaToken.codigo,
                                'app_label': app_label,
                                't': miinstitucion(),
                                'dominio': EMAIL_DOMAIN,
                                'ip': get_client_ip(request),
                                },
                               persona.lista_emails(), [],
                               cuenta=CUENTAS_CORREOS[7][1])
            except Exception as ex1:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                pass
            contador = matricula.contador_reenviar_email_token()
            return Helper_Response(isSuccess=True, data={"contador": contador}, message=f'Se reenvio correo con un código o link para eliminar la matrícula.', status=status.HTTP_200_OK)
        except Exception as ex:
            transaction.set_rollback(True)
            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)


def generateCodeRemoveMateria(request, materiaasignada):
    with transaction.atomic():
        try:
            fecha = datetime.now().date()
            hora = datetime.now().time()
            fecha_hora = fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__()
            if not materiaasignada:
                raise NameError(u"Materia no encontrada")
            materia = materiaasignada.materia
            matricula = materiaasignada.matricula
            inscripcion = matricula.inscripcion
            persona = inscripcion.persona
            usuario = persona.usuario
            if not usuario:
                raise NameError(u"Usuario no encontrado")
            code = generate_code(6)
            token = md5(str(encrypt(usuario.id) + fecha_hora).encode("utf-8")).hexdigest()
            if materiaasignada.materiaasignadatoken_set.values("id").filter(status=True, isActive=True, user_token__user=usuario, user_token__isActive=True, user_token__action_type=2, user_token__date_expires__gte=datetime.now()).exists():
                raise NameError(u"Mantiene un código activo.")
            else:
                mis_materias = matricula.mismaterias()
                mis_materias = mis_materias.exclude(pk=materiaasignada.id)
                UserToken.objects.filter(user=usuario, isActive=True, action_type=2).exclude(pk__in=MateriaAsignadaToken.objects.values("user_token__id").filter(status=True, materia_asignada__in=mis_materias, isActive=True).distinct()).update(isActive=False)
                eUserToken = UserToken(user=usuario,
                                       token=token,
                                       action_type=2,
                                       date_expires=datetime.now() + timedelta(days=1),
                                       app=4,
                                       isActive=True)
                eUserToken.save(request)
                eMateriaAsignadaToken = MateriaAsignadaToken(materia_asignada=materiaasignada,
                                                             user_token=eUserToken,
                                                             codigo=code,
                                                             isActive=True,
                                                             num_email=1)
                eMateriaAsignadaToken.save(request)
                log(u'Genera codigo y token de retiro de materia: %s de la matricula: %s' % (materia, matricula), request, "add")
                app_label = 'sie'
                sistema = u'Sistema Integral Estudiantil'
                try:
                    send_html_mail("Código de confirmación - Retiro de materia",
                                   "emails/solicitud_retiro_materia.html",
                                   {'sistema': sistema,
                                    'fecha': datetime.now().date,
                                    'fecha_g': fecha,
                                    'hora_g': hora,
                                    'persona': persona,
                                    'materia': materia,
                                    'matricula': matricula,
                                    'token': token,
                                    'codigo': code,
                                    'app_label': app_label,
                                    't': miinstitucion(),
                                    'dominio': EMAIL_DOMAIN,
                                    'ip': get_client_ip(request),
                                    },
                                   persona.lista_emails(), [],
                                   cuenta=CUENTAS_CORREOS[7][1])
                except Exception as ex1:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass
            return Helper_Response(isSuccess=True, data={}, message=f'Se genero un correo con un código o link para retirar la materia.', status=status.HTTP_200_OK)
        except Exception as ex:
            transaction.set_rollback(True)
            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)


def reenvioCodeRemoveMateria(request, materiaasignada):
    with transaction.atomic():
        try:
            materia = materiaasignada.materia
            matricula = materiaasignada.matricula
            inscripcion = matricula.inscripcion
            persona = inscripcion.persona
            usuario = persona.usuario
            if not materiaasignada.materiaasignadatoken_set.values("id").filter(status=True, isActive=True, user_token__user=usuario, user_token__isActive=True, user_token__action_type=2, user_token__date_expires__gte=datetime.now()).exists():
                raise NameError(u"No mantiene código activo.")
            eMateriaAsignadaToken = materiaasignada.materiaasignadatoken_set.filter(status=True, isActive=True, user_token__user=usuario, user_token__isActive=True, user_token__action_type=2, user_token__date_expires__gte=datetime.now())[0]
            eUserToken = eMateriaAsignadaToken.user_token
            eMateriaAsignadaToken.num_email = eMateriaAsignadaToken.num_email + 1
            eMateriaAsignadaToken.save(request)
            log(u'Reenvio de codigo y token de retiro de materia: %s de la matricula: %s' % (materia, matricula), request, "add")
            app_label = 'sie'
            sistema = u'Sistema Integrado Estudiantil'
            try:
                send_html_mail("Código de confirmación - Retiro de materia",
                               "emails/solicitud_retiro_materia.html",
                               {'sistema': sistema,
                                'fecha': datetime.now().date,
                                'fecha_g': eMateriaAsignadaToken.fecha_creacion.date(),
                                'hora_g': eMateriaAsignadaToken.fecha_creacion.time(),
                                'persona': persona,
                                'materia': materia,
                                'matricula': matricula,
                                'token': eUserToken.token,
                                'codigo': eMateriaAsignadaToken.codigo,
                                'app_label': app_label,
                                't': miinstitucion(),
                                'dominio': EMAIL_DOMAIN,
                                'ip': get_client_ip(request),
                                },
                               persona.lista_emails(), [],
                               cuenta=CUENTAS_CORREOS[7][1])
            except Exception as ex1:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                pass
            contador = materiaasignada.contador_reenviar_email_token()
            return Helper_Response(isSuccess=True, data={"contador": contador}, message=f'Se reenvio correo con un código o link para retirar la materia.', status=status.HTTP_200_OK)
        except Exception as ex:
            transaction.set_rollback(True)
            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

