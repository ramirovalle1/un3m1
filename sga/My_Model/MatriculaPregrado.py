# -*- coding: UTF-8 -*-
from _decimal import Decimal

from django import template
from django.db import models, transaction
from django.db.models import manager, Max, Q, Sum
from settings import TIPO_RESPUESTA_EVALUACION, USA_TIPOS_INSCRIPCIONES, TIPO_INSCRIPCION_INICIAL, \
    DIAS_MATRICULA_EXPIRA, NOTA_ESTADO_EN_CURSO, ADMINISTRADOR_ID, DEBUG
from sga.funciones import fechaletra_corta, fields_model, field_default_value_model, trimestre, null_to_decimal, \
    convertir_fecha, variable_valor
from sga.models import Matricula, Inscripcion, Carrera, Coordinacion, ConfigMatriculacionPrimerNivel, \
    MatriculacionPrimerNivelCarrera, Materia, Nivel, DocumentosDeInscripcion, InscripcionTipoInscripcion, \
    InscripcionTesDrive, RecordAcademico, MateriaAsignada, Sesion, Paralelo, AuditoriaMatricula, PerdidaGratuidad
from datetime import datetime, timedelta, date
from django.core.exceptions import ObjectDoesNotExist


class My_MatriculaPregrado(Matricula):
    objects = models.Manager()

    class Meta:
        proxy = True

    def __init__(self, *args, **kwargs):
        super(My_MatriculaPregrado, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        super(My_MatriculaPregrado, self).save(*args, **kwargs)


class My_InscripcionPregrado(Inscripcion):
    objects = models.Manager()

    class Meta:
        proxy = True

    def __init__(self, *args, **kwargs):
        super(My_InscripcionPregrado, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        super(My_InscripcionPregrado, self).save(*args, **kwargs)

    # def asignacion_promocion(self):
    #     matriculas = Matricula.objects.filter(inscripcion=self, status=True).order_by('-periodo_id')


class My_CarreraPregrado(Carrera):
    objects = models.Manager()

    class Meta:
        proxy = True

    def __init__(self, *args, **kwargs):
        super(My_CarreraPregrado, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        super(My_CarreraPregrado, self).save(*args, **kwargs)

    def load_my_career_pregrado(self, periodoa, periodop):
        config = My_ConfigMatriculacionPrimerNivel.objects.filter(periodoadmision=periodoa, periodopregrado=periodop, status=True)
        carrerapregrado = None
        if config.exists():
            carrerapregrado = My_MatriculacionPrimerNivelCarrera.objects.filter(configuracion=config[0], carreraadmision=self, status=True)
            if carrerapregrado.exists():
                carrerapregrado = carrerapregrado[0].carrerapregrado
        return carrerapregrado

    def load_number_enrolled(self, periodoa, periodop):
        matriculas_admision = My_MatriculaPregrado.objects.filter(nivel__periodo=periodoa, aprobado=True, inscripcion__carrera=self).count()
        config = My_ConfigMatriculacionPrimerNivel.objects.filter(periodoadmision=periodoa, periodopregrado=periodop, status=True)
        matriculas_pregrado = 0
        detalle = None
        total_cupo_pregrado = 0
        detalle_paralelos = []
        if config.exists():
            detalle = My_MatriculacionPrimerNivelCarrera.objects.filter(configuracion=config[0], carreraadmision=self, status=True)
            if detalle.exists():
                carrerapregrado = detalle[0].carrerapregrado
                matriculas_pregrado = len(My_MatriculaPregrado.objects.filter(nivel__periodo=periodop, inscripcion__carrera=carrerapregrado, nivelmalla__id__lt=2))
        por_matricular = matriculas_admision - matriculas_pregrado
        if detalle:
            if detalle[0].carrerapregrado:
                niveles_pregrado = Nivel.objects.filter(periodo=detalle[0].configuracion.periodopregrado, sesion__in=detalle[0].sesiones.filter(), materia__asignaturamalla__nivelmalla__id__lt=2, materia__asignaturamalla__malla__carrera=detalle[0].carrerapregrado).distinct()
                paralelos = Paralelo.objects.filter(pk__in=niveles_pregrado.values_list('materia__paralelomateria'))
                cupo = 0
                cupo_aux = 0
                for paralelo in paralelos:
                    #cupo += niveles_pregrado.filter(materia__paralelomateria=paralelo).aggregate(total=Sum('materia__cupo'))['total']
                    cupo_aux =  min(Materia.objects.filter(nivel__in=niveles_pregrado, paralelomateria=paralelo, asignaturamalla__nivelmalla__id__lt=2, asignaturamalla__malla__carrera=detalle[0].carrerapregrado).values_list('cupo', flat=True))
                    cupo += cupo_aux
                    detalle_paralelos.append({'id': paralelo.id, 'nombre': paralelo.nombre, 'cupo': cupo_aux})
                if niveles_pregrado.exists():
                    total_cupo_pregrado = cupo

        return {'admision': matriculas_admision, 'pregrado': matriculas_pregrado, 'por_matricular': por_matricular, 'cupos': total_cupo_pregrado, 'paralelos': detalle_paralelos}

    def load_can_matricular(self, periodoadmision, periodopregrado):
        config = My_ConfigMatriculacionPrimerNivel.objects.filter(periodoadmision=periodoadmision, periodopregrado=periodopregrado, status=True)
        can_matricular = False
        if config.exists():
            carrerapregrado = My_MatriculacionPrimerNivelCarrera.objects.filter(configuracion=config[0], carreraadmision=self, status=True)
            if carrerapregrado.exists() and carrerapregrado[0].sesiones.filter().exists():
                can_matricular = True
        return can_matricular

    def can_rerun(self, periodoadmision, periodopregrado):
        config = My_ConfigMatriculacionPrimerNivel.objects.filter(periodoadmision=periodoadmision, periodopregrado=periodopregrado, status=True)
        can_rerun = False
        if config.exists():
            detalle = My_MatriculacionPrimerNivelCarrera.objects.filter(configuracion=config[0], carreraadmision=self, status=True)
            if detalle.exists():
                can_rerun = True if detalle[0].ejecutoaccion else False
        return can_rerun


class My_CoordinacionPregrado(Coordinacion):
    objects = models.Manager()

    class Meta:
        proxy = True

    def __init__(self, *args, **kwargs):
        super(My_CoordinacionPregrado, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        super(My_CoordinacionPregrado, self).save(*args, **kwargs)

    def list_careers_by_and_period(self, periodo):
        carrera_ids = My_MatriculaPregrado.objects.filter(nivel__periodo_id=periodo, aprobado=True, inscripcion__carrera__coordinacionvalida=self).values_list('inscripcion__carrera_id').distinct()
        carreras = My_CarreraPregrado.objects.filter(id__in=carrera_ids).distinct()
        return carreras


class My_ConfigMatriculacionPrimerNivel(ConfigMatriculacionPrimerNivel):
    objects = models.Manager()

    class Meta:
        proxy = True

    def __init__(self, *args, **kwargs):
        super(My_ConfigMatriculacionPrimerNivel, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        super(My_ConfigMatriculacionPrimerNivel, self).save(*args, **kwargs)

    def has_detail(self):
        return My_MatriculacionPrimerNivelCarrera.objects.filter(configuracion=self, status=True).exists()

    def list_careers_first_level(self):
        carreras = My_MatriculacionPrimerNivelCarrera.objects.filter(configuracion=self, status=True)
        return carreras

    def list_careers_admision_add_detail(self, periodo):
        carreras_ids = My_MatriculaPregrado.objects.values_list('inscripcion__carrera_id').filter(nivel__periodo=periodo, aprobado=True).distinct()
        #carreras_ids = My_InscripcionPregrado.objects.values_list('carrera_id').filter(id__in=inscripcion_ids).distinct()
        exCarreras = My_MatriculacionPrimerNivelCarrera.objects.values_list('carreraadmision_id').filter(configuracion=self, status=True, carreraadmision__isnull=False).distinct()
        if exCarreras.exists():
            carreras = My_CarreraPregrado.objects.filter(id__in=carreras_ids).exclude(id__in=exCarreras).distinct()
        else:
            carreras = My_CarreraPregrado.objects.filter(id__in=carreras_ids).distinct()
        return carreras

    def list_careers_pregrado_add_detail(self, periodo):
        carrera_ids = Materia.objects.values_list('asignaturamalla__malla__carrera_id').filter(nivel__periodo=periodo, status=True).distinct()
        exCarreras = My_MatriculacionPrimerNivelCarrera.objects.values_list('carrerapregrado_id').filter(configuracion=self, status=True, carrerapregrado__isnull=False).distinct()
        if exCarreras.exists():
            carreras = My_CarreraPregrado.objects.filter(id__in=carrera_ids).exclude(id__in=exCarreras).distinct()
        else:
            carreras = My_CarreraPregrado.objects.filter(id__in=carrera_ids).distinct()
        return carreras

    def load_statistics(self):
        total_admision = 0
        total_inscritos = 0
        total_matriculados = 0
        total_x_matricular = 0
        total_aceptado_matricula = 0
        total_rechazado_matricula = 0
        total_x_confirmar_matricula = 0
        niveles_admision = Nivel.objects.filter(periodo=self.periodoadmision)
        alumnos_admision = My_MatriculaPregrado.objects.filter(status=True, aprobado=True,
                                                               nivel__in=niveles_admision.values_list('id'))
        if alumnos_admision.exists():
            total_admision = alumnos_admision.count()
            careraspregrado = self.list_careers_first_level()
            if careraspregrado.exists():
                inscripciones_pregrado = Inscripcion.objects.filter(
                    persona_id__in=alumnos_admision.values_list('inscripcion__persona_id'),
                    carrera_id__in=careraspregrado.values_list('carrerapregrado_id'), usuario_creacion_id=1).exclude(fechainiciocarrera__isnull=True)
                if inscripciones_pregrado.exists():
                    total_inscritos = inscripciones_pregrado.count()
                    niveles_pregrado = Nivel.objects.filter(periodo=self.periodopregrado,
                                                            materia__asignaturamalla__nivelmalla__id__lt=2,
                                                            materia__asignaturamalla__malla__carrera_id__in=careraspregrado.values_list('carrerapregrado_id'))
                    if niveles_pregrado.exists():
                        matriculas_pregrado = My_MatriculaPregrado.objects.filter(status=True,
                                                                                  inscripcion__in=inscripciones_pregrado,
                                                                                  nivel__in=niveles_pregrado)
                        if matriculas_pregrado.exists():
                            total_matriculados = matriculas_pregrado.count()
                            total_x_matricular = total_inscritos - total_matriculados
                            total_aceptado_matricula = matriculas_pregrado.filter(automatriculapregrado=True, termino=True).count()
                            total_x_confirmar_matricula = matriculas_pregrado.filter(automatriculapregrado=True, termino=False).count()
                            rechazaron = AuditoriaMatricula.objects.filter(inscripcion__in=inscripciones_pregrado,
                                                                           periodo=self.periodopregrado, tipo=3).exclude(inscripcion_id__in=matriculas_pregrado.values_list('inscripcion_id'))
                            if rechazaron.exists():
                                total_rechazado_matricula = rechazaron.count()

        return {'total_admision': total_admision,
                'total_inscritos': total_inscritos,
                'total_matriculados': total_matriculados,
                'total_x_matricular': total_x_matricular,
                'total_aceptado_matricula': total_aceptado_matricula,
                'total_rechazado_matricula': total_rechazado_matricula,
                'total_x_confirmar_matricula': total_x_confirmar_matricula,
                }

    def can_add_detail(self, periodo):
        return self.list_careers_admision_add_detail(periodo).exists()


class My_MatriculacionPrimerNivelCarrera(MatriculacionPrimerNivelCarrera):
    objects = models.Manager()

    class Meta:
        proxy = True

    def __init__(self, *args, **kwargs):
        super(My_MatriculacionPrimerNivelCarrera, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        super(My_MatriculacionPrimerNivelCarrera, self).save(*args, **kwargs)

    def matricular_primer_nivel_by_carrera(self, persona):
        import sys
        from matricula.funciones import get_tipo_matricula
        from sagest.models import Rubro
        try:
            ID_NIVEL_MALLA_PRIMERO = 1
            ID_NIVEL_MALLA_SEGUNDO = 2
            niveles_admision = Nivel.objects.filter(periodo=self.configuracion.periodoadmision)
            alumnos_admision = My_MatriculaPregrado.objects.filter(status=True, aprobado=True, nivel__in=niveles_admision.values_list('id'), inscripcion__carrera=self.carreraadmision)
            niveles_pregrado = Nivel.objects.filter(periodo=self.configuracion.periodopregrado, sesion__in=self.sesiones.filter(), materia__asignaturamalla__nivelmalla__id__lt=2, materia__asignaturamalla__malla__carrera=self.carrerapregrado).distinct()
            paralelos = Paralelo.objects.filter(pk__in=niveles_pregrado.values_list('materia__paralelomateria'))
            total_cupo_pregrado = 0
            for paralelo in paralelos:
                total_cupo_pregrado += min(Materia.objects.filter(nivel__in=niveles_pregrado, paralelomateria=paralelo, asignaturamalla__nivelmalla__id__lt=2, asignaturamalla__malla__carrera=self.carrerapregrado).values_list('cupo', flat=True))
            total_cupo_admision = alumnos_admision.count()
            sesiones = Sesion.objects.filter(pk__in=niveles_pregrado.values_list('sesion_id').distinct())
            num_sesiones = sesiones.count()
            distribucion_cupo_por_sesiones = round(total_cupo_pregrado / num_sesiones)
            paralelos = Paralelo.objects.filter(pk__in=niveles_pregrado.values_list('materia__paralelomateria_id').distinct())
            num_paralelos = paralelos.count()
            distribucion_cupo_por_paralelo = round(total_cupo_pregrado / num_paralelos)
            limitinicial = 0
            # limitfinial = distribucion_cupo_por_paralelo
            limitfinial = limitinicial
            nivel = None
            sesion = None
            for paralelo in paralelos:
                #nivel = niveles_pregrado.filter(materia__paralelomateria=paralelo)[0]
                nivel = Nivel.objects.filter(periodo=self.configuracion.periodopregrado, sesion__in=self.sesiones.filter(), materia__asignaturamalla__nivelmalla__id__lt=2, materia__asignaturamalla__malla__carrera=self.carrerapregrado, materia__paralelomateria=paralelo).distinct()[0]
                fechainicioprimernivel = variable_valor('FECHA_INICIO_PRIMER_NIVEL')
                fechainiciocarrera = variable_valor('FECHA_INICIO_CARRERA')
                if nivel.fechainicioagregacion:
                    fechainicioprimernivel = nivel.fechainicioagregacion
                sesion = nivel.sesion
                if Materia.objects.values("id").filter(status=True, nivel=nivel, paralelomateria=paralelo, asignaturamalla__nivelmalla__id__lt=2, asignaturamalla__malla__carrera=self.carrerapregrado, cupo__gt=0).exists():
                    distribucion_cupo_por_paralelo = min(Materia.objects.filter(status=True, nivel=nivel, paralelomateria=paralelo, asignaturamalla__nivelmalla__id__lt=2, asignaturamalla__malla__carrera=self.carrerapregrado).values_list('cupo', flat=True))
                    limitfinial = (limitfinial + distribucion_cupo_por_paralelo) - 1
                    for matriculaadmision in alumnos_admision.filter(inscripcion__carrera=self.carreraadmision)[limitinicial:limitfinial]:
                        persona = matriculaadmision.inscripcion.persona
                        print("%s" %matriculaadmision.inscripcion.id)
                        if matriculaadmision.inscripcion_id == 172128:
                            print("uuuuuuu")
                        # definir sesion
                        carrera = self.carrerapregrado
                        sede = matriculaadmision.inscripcion.sede
                        modalidad = matriculaadmision.inscripcion.modalidad
                        coordinacion = self.carrerapregrado.coordinacion_set.filter(status=True)[0]
                        colegio = persona.inscripcion_set.all()[0].colegio
                        perfilpersona = persona.mi_perfil()
                        raza_id = 6

                        if perfilpersona:
                            raza_id = perfilpersona.raza_id
                        if not Inscripcion.objects.filter(persona=persona, carrera=self.carrerapregrado).exists():
                            inscripcion = Inscripcion(persona=persona,
                                                      fecha=datetime.now().date(),
                                                      carrera=self.carrerapregrado,
                                                      coordinacion=coordinacion,
                                                      modalidad=modalidad,
                                                      sesion=sesion,
                                                      sede=sede,
                                                      colegio=colegio,
                                                      aplica_b2=True,
                                                      fechainicioprimernivel=fechainicioprimernivel,
                                                      fechainiciocarrera=fechainiciocarrera)
                            inscripcion.save(usuario_id=ADMINISTRADOR_ID)
                            persona.crear_perfil(inscripcion=inscripcion,visible=False,principal=True)
                            documentos = DocumentosDeInscripcion(inscripcion=inscripcion,
                                                                 titulo=False,
                                                                 acta=False,
                                                                 cedula=False,
                                                                 votacion=False,
                                                                 actaconv=False,
                                                                 partida_nac=False,
                                                                 pre=False,
                                                                 observaciones_pre='',
                                                                 fotos=False)
                            documentos.save(usuario_id=ADMINISTRADOR_ID)
                            preguntasinscripcion = inscripcion.preguntas_inscripcion()
                            perfil_inscripcion = inscripcion.persona.mi_perfil()

                            perfil_inscripcion.raza_id = raza_id
                            perfil_inscripcion.save(usuario_id=ADMINISTRADOR_ID)
                            inscripciontesdrive = InscripcionTesDrive(inscripcion=inscripcion,
                                                                      licencia=False,
                                                                      record=False,
                                                                      certificado_tipo_sangre=False,
                                                                      prueba_psicosensometrica=False,
                                                                      certificado_estudios=False)
                            inscripciontesdrive.save(usuario_id=ADMINISTRADOR_ID)
                            # inscripcion.mi_malla()
                            inscripcion.malla_inscripcion()
                            inscripcion.actualizar_nivel()
                            if USA_TIPOS_INSCRIPCIONES:
                                inscripciontipoinscripcion = InscripcionTipoInscripcion(inscripcion=inscripcion,
                                                                                        tipoinscripcion_id=TIPO_INSCRIPCION_INICIAL)
                                inscripciontipoinscripcion.save(usuario_id=ADMINISTRADOR_ID)
                        else:
                            inscripcion = Inscripcion.objects.filter(persona=persona, carrera=carrera)[0]
                            perfil_inscripcion = inscripcion.persona.mi_perfil()
                            perfil_inscripcion.raza_id = raza_id
                            perfil_inscripcion.save(usuario_id=ADMINISTRADOR_ID)
                        inscripcion.sesion = sesion
                        inscripcion.save(usuario_id=ADMINISTRADOR_ID)
                        if matriculaadmision.inscripcion.estado_gratuidad == 3:
                            ePerdidaGratuidadAdmisions = PerdidaGratuidad.objects.filter(inscripcion=matriculaadmision.inscripcion, status=True)
                            ePerdidaGratuidadAdmision = None
                            observacion = 'Reportado por la SENESCYT'
                            if ePerdidaGratuidadAdmisions.values("id").exists():
                                ePerdidaGratuidadAdmision = ePerdidaGratuidadAdmisions[0]
                                if ePerdidaGratuidadAdmision.observacion:
                                    observacion = ePerdidaGratuidadAdmision.observacion
                                if not PerdidaGratuidad.objects.values('id').filter(inscripcion=inscripcion, status=True).exists():
                                    ePerdidaGratuidad = PerdidaGratuidad(inscripcion=inscripcion,
                                                                         motivo=1,
                                                                         observacion=observacion)
                                    ePerdidaGratuidad.save(usuario_id=ADMINISTRADOR_ID)
                                # else:
                                #     ePerdidaGratuidad = PerdidaGratuidad.objects.filter(inscripcion=inscripcion, status=True)[0]
                                #     ePerdidaGratuidad.inscripcion=inscripcion
                                #     ePerdidaGratuidad.motivo=1
                                #     ePerdidaGratuidad.observacion=observacion
                                #     ePerdidaGratuidad.save(usuario_id=ADMINISTRADOR_ID)
                                    inscripcion.estado_gratuidad = 3
                                    inscripcion.porcentaje_perdida_gratuidad = 100
                                    inscripcion.save(usuario_id=ADMINISTRADOR_ID)
                        # considerar si que existe en titulo persona
                        # tiene_otro_titulo = persona.tiene_otro_titulo(inscripcion=inscripcion)
                        # if DEBUG:
                        #     tiene_otro_titulo = False
                        # if not tiene_otro_titulo:
                        if not inscripcion.matricula_periodo(self.configuracion.periodopregrado):
                            matricula = Matricula(inscripcion=inscripcion,
                                                  nivel=nivel,
                                                  pago=False,
                                                  iece=False,
                                                  becado=False,
                                                  porcientobeca=0,
                                                  fecha=datetime.now().date(),
                                                  hora=datetime.now().time(),
                                                  fechatope=fechatope(datetime.now().date()),
                                                  automatriculapregrado=True,
                                                  fechaautomatriculapregrado=datetime.now(),
                                                  estado_matricula=2)
                            matricula.save(usuario_id=ADMINISTRADOR_ID)
                        else:
                            matricula=None
                            if not MateriaAsignada.objects.filter(status=True,matricula=inscripcion.matricula_periodo(self.configuracion.periodopregrado)).exists():
                                matricula = Matricula.objects.get(inscripcion=inscripcion, nivel=nivel)
                        if matricula:
                            asignatura_malla = RecordAcademico.objects.values_list('asignatura__id', flat=True).filter(asignaturamalla__nivelmalla__id__lt=ID_NIVEL_MALLA_SEGUNDO, aprobada=True)

                            for materia in Materia.objects.filter(nivel=nivel, paralelomateria=paralelo, asignaturamalla__malla__carrera=carrera, nivel__sesion=sesion, asignaturamalla__nivelmalla__id=ID_NIVEL_MALLA_PRIMERO):
                                if not MateriaAsignada.objects.filter(matricula=matricula, materia=materia).exists():
                                    matriculas = matricula.inscripcion.historicorecordacademico_set.filter(asignatura=materia.asignatura, fecha__lt=materia.nivel.fin).count() + 1
                                    materiaasignada = MateriaAsignada(matricula=matricula,
                                                                      materia=materia,
                                                                      notafinal=0,
                                                                      asistenciafinal=100,
                                                                      asistenciafinalzoom=100,
                                                                      cerrado=False,
                                                                      matriculas=matriculas,
                                                                      observaciones='',
                                                                      estado_id=NOTA_ESTADO_EN_CURSO)
                                    if carrera.modalidad == 3 and  carrera.coordinacion_set.filter(status=True)[0].pk in(1,2,3,4,5):
                                        materiaasignada.sinasistencia = True

                                    materiaasignada.save(usuario_id=ADMINISTRADOR_ID)
                                    materiaasignada.asistencias()
                                    materiaasignada.evaluacion()
                                    materiaasignada.mis_planificaciones()
                                    materiaasignada.save(usuario_id=ADMINISTRADOR_ID)
                                    print(u"matriculado (%s) en la materia %s " % (persona.cedula, materia))
                                else:
                                    print(u"ya estaba matriculado (%s) en la materia %s " % (persona.cedula, materia))
                                # actualizo de una vez el aula virtual
                                # materia.crear_actualizar_estudiantes_curso(moodle, 1)
                            inscripcion.actualizar_nivel()
                            matricula.actualiza_matricula()
                            matricula.inscripcion.actualiza_estado_matricula()
                            matricula.grupo_socio_economico(1)
                            matricula.calcula_nivel()
                            # CALCULO DE RUBROS EN ESTADO - FALSE
                            if matricula.inscripcion.persona.tiene_otro_titulo():
                                matricula.agregacion_aux(None)
                                matricula.inscripcion.actualiza_estado_matricula()
                                valid, msg, aData = get_tipo_matricula(None, matricula)
                                if not valid:
                                    raise NameError(msg)
                                cantidad_nivel = aData['cantidad_nivel']
                                porcentaje_perdidad_parcial_gratuidad = aData['porcentaje_perdidad_parcial_gratuidad']
                                cantidad_seleccionadas = aData['cantidad_seleccionadas']
                                porcentaje_seleccionadas = int(round(
                                    Decimal((float(cantidad_nivel) * float(
                                        porcentaje_perdidad_parcial_gratuidad)) / 100).quantize(
                                        Decimal('.00')), 0))
                                if (cantidad_seleccionadas < porcentaje_seleccionadas):
                                    matricula.grupo_socio_economico(2)
                                else:
                                    matricula.grupo_socio_economico(1)
                                matricula.calcula_nivel()
                                matricula.aranceldiferido = 2
                                matricula.actacompromiso = None
                                matricula.save()
                                if not PerdidaGratuidad.objects.values('id').filter(inscripcion=inscripcion,status=True).exists():
                                    observacion = f"Reportado por la SENESCYT"
                                    observacion = f"{observacion}, Registra TITULO TERCER NIVEL REGISTRO SNIESE"
                                    ePerdidaGratuidad = PerdidaGratuidad(inscripcion=inscripcion)
                                    ePerdidaGratuidad.motivo = 1
                                    ePerdidaGratuidad.titulo = None
                                    ePerdidaGratuidad.titulo_sniese = True
                                    ePerdidaGratuidad.observacion = observacion
                                    ePerdidaGratuidad.save(usuario_id=persona.usuario.id)
                                    inscripcion.gratuidad = False
                                    inscripcion.estado_gratuidad = 3
                                    inscripcion.save(usuario_id=ADMINISTRADOR_ID)
                                Rubro.objects.filter(matricula=matricula).update(status=False)
                                print(matricula)

                            #print(u"matriculado %s" % persona.cedula)
                    # cambio los limites para la nueva consulta
                    limitinicial = limitfinial - 1
                    # limitfinial = (limitfinial + distribucion_cupo_por_paralelo) - 1
        except Exception as ex:
            print(ex)
            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
            textoerror = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)

    def crear_inscripcion_primer_nivel_by_carrera(self, persona):

        ID_NIVEL_MALLA_PRIMERO = 1
        ID_NIVEL_MALLA_SEGUNDO = 2
        niveles_admision = Nivel.objects.filter(periodo=self.configuracion.periodoadmision)
        alumnos_admision = My_MatriculaPregrado.objects.filter(status=True, aprobado=True,
                                                               nivel__in=niveles_admision.values_list('id'),
                                                               inscripcion__carrera=self.carreraadmision)
        niveles_pregrado = Nivel.objects.filter(periodo=self.configuracion.periodopregrado,
                                                sesion__in=self.sesiones.filter(),
                                                materia__asignaturamalla__nivelmalla__id__lt=2,
                                                materia__asignaturamalla__malla__carrera=self.carrerapregrado).distinct()
        paralelos = Paralelo.objects.filter(pk__in=niveles_pregrado.values_list('materia__paralelomateria'))
        total_cupo_pregrado = 0
        for paralelo in paralelos:
            total_cupo_pregrado += min(Materia.objects.filter(nivel__in=niveles_pregrado, paralelomateria=paralelo, asignaturamalla__nivelmalla__id__lt=2, asignaturamalla__malla__carrera=self.carrerapregrado).values_list('cupo', flat=True))
        total_cupo_admision = alumnos_admision.count()
        sesiones = Sesion.objects.filter(pk__in=niveles_pregrado.values_list('sesion_id').distinct())
        num_sesiones = sesiones.count()
        distribucion_cupo_por_sesiones = round(total_cupo_pregrado / num_sesiones)
        paralelos = Paralelo.objects.filter(pk__in=niveles_pregrado.values_list('materia__paralelomateria_id').distinct())
        num_paralelos = paralelos.count()
        distribucion_cupo_por_paralelo = round(total_cupo_pregrado / num_paralelos)
        limitinicial = 0
        # limitfinial = distribucion_cupo_por_paralelo
        limitfinial = limitinicial

        nivel = None
        sesion = None
        for paralelo in paralelos:
            # nivel = niveles_pregrado.filter(materia__paralelomateria=paralelo)[0]
            nivel = Nivel.objects.filter(periodo=self.configuracion.periodopregrado, sesion__in=self.sesiones.filter(),
                                         materia__asignaturamalla__nivelmalla__id__lt=2,
                                         materia__asignaturamalla__malla__carrera=self.carrerapregrado,
                                         materia__paralelomateria=paralelo).distinct()[0]
            if limitinicial != 0:
                limitinicial = limitfinial - 1
            limitfinial = (limitfinial + distribucion_cupo_por_paralelo) - 1
            fechainicioprimernivel =variable_valor('FECHA_INICIO_PRIMER_NIVEL')
            fechainiciocarrera = variable_valor('FECHA_INICIO_CARRERA')
            if nivel.fechainicioagregacion:
                fechainicioprimernivel = nivel.fechainicioagregacion
            sesion = nivel.sesion
            for matriculaadmision in alumnos_admision.filter(inscripcion__carrera=self.carreraadmision)[limitinicial:limitfinial]:
                persona = matriculaadmision.inscripcion.persona
                # definir sesion
                carrera = self.carrerapregrado
                sede = matriculaadmision.inscripcion.sede
                modalidad = matriculaadmision.inscripcion.modalidad
                coordinacion = self.carrerapregrado.coordinacion_set.filter(status=True)[0]
                colegio = persona.inscripcion_set.all()[0].colegio
                perfilpersona = persona.mi_perfil()
                raza_id = 6

                if perfilpersona:
                    raza_id = perfilpersona.raza_id
                if not Inscripcion.objects.filter(persona=persona, carrera=self.carrerapregrado).exists():
                    inscripcion = Inscripcion(persona=persona,
                                              fecha=datetime.now().date(),
                                              carrera=self.carrerapregrado,
                                              coordinacion=coordinacion,
                                              modalidad=modalidad,
                                              sesion=sesion,
                                              sede=sede,
                                              colegio=colegio,
                                              aplica_b2=True,
                                              fechainicioprimernivel=fechainicioprimernivel,
                                              fechainiciocarrera=fechainiciocarrera)
                    inscripcion.save(usuario_id=ADMINISTRADOR_ID)
                    persona.crear_perfil(inscripcion=inscripcion, visible=False, principal=True)
                    documentos = DocumentosDeInscripcion(inscripcion=inscripcion,
                                                         titulo=False,
                                                         acta=False,
                                                         cedula=False,
                                                         votacion=False,
                                                         actaconv=False,
                                                         partida_nac=False,
                                                         pre=False,
                                                         observaciones_pre='',
                                                         fotos=False)
                    documentos.save(usuario_id=ADMINISTRADOR_ID)
                    preguntasinscripcion = inscripcion.preguntas_inscripcion()
                    perfil_inscripcion = inscripcion.persona.mi_perfil()
                    perfil_inscripcion.raza_id = raza_id
                    perfil_inscripcion.save(usuario_id=ADMINISTRADOR_ID)
                    inscripciontesdrive = InscripcionTesDrive(inscripcion=inscripcion,
                                                              licencia=False,
                                                              record=False,
                                                              certificado_tipo_sangre=False,
                                                              prueba_psicosensometrica=False,
                                                              certificado_estudios=False)
                    inscripciontesdrive.save(usuario_id=ADMINISTRADOR_ID)
                    # inscripcion.mi_malla()
                    #inscripcion.malla_inscripcion()
                    malla_inscripcion(inscripcion)
                    inscripcion.actualizar_nivel()
                    if USA_TIPOS_INSCRIPCIONES:
                        inscripciontipoinscripcion = InscripcionTipoInscripcion(inscripcion=inscripcion,
                                                                                tipoinscripcion_id=TIPO_INSCRIPCION_INICIAL)
                        inscripciontipoinscripcion.save(usuario_id=ADMINISTRADOR_ID)
                    inscripcion.sesion = sesion
                else:
                    inscripcion = Inscripcion.objects.filter(persona=persona, carrera=carrera)[0]
                    perfil_inscripcion = inscripcion.persona.mi_perfil()
                    perfil_inscripcion.raza_id = raza_id
                    perfil_inscripcion.save(usuario_id=ADMINISTRADOR_ID)
                inscripcion.save(usuario_id=ADMINISTRADOR_ID)
                inscripcion.actualizar_nivel()
            # cambio los limites para la nueva consulta
            # limitinicial = limitfinial - 1
            # limitfinial = (limitfinial + distribucion_cupo_por_paralelo) - 1


def fechatope(fecha):
    contador = 0
    nuevafecha = fecha
    while contador < DIAS_MATRICULA_EXPIRA:
        nuevafecha = nuevafecha + timedelta(1)
        if nuevafecha.weekday() != 5 and nuevafecha.weekday() != 6:
            contador += 1
    return nuevafecha

def malla_inscripcion(inscripcion):
    from sga.models import Malla, InscripcionMalla
    eInscripcionMalla = inscripcion.inscripcionmalla_set.filter(status=True).first()
    if eInscripcionMalla:
        return eInscripcionMalla
    eMallas = Malla.objects.filter(carrera=inscripcion.carrera, validamatricula=True)
    eMalla = None
    if (eMalla_aux := eMallas.filter(modalidad=inscripcion.modalidad).order_by('-inicio').first()) is not None:
        eMalla = eMalla_aux
    if not eMalla:
        eMalla = eMalla = eMallas.filter(vigente=True).order_by('-inicio').first()
    if eMalla:
        eInscripcionMalla = InscripcionMalla(inscripcion=inscripcion, malla=eMalla)
        eInscripcionMalla.save()
        return eInscripcionMalla
    return None