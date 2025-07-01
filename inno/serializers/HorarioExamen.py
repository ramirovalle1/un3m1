# coding=utf-8
from datetime import datetime

from inno.models import FechaPlanificacionSedeVirtualExamen, TurnoPlanificacionSedeVirtualExamen, \
    AulaPlanificacionSedeVirtualExamen, MateriaAsignadaPlanificacionSedeVirtualExamen
from sga.funciones import null_to_decimal, null_to_numeric, variable_valor
from sga.models import Carrera, Sesion, Coordinacion, Modalidad, Malla, NivelMalla, Paralelo, AsignaturaMalla, \
    Materia, Asignatura, MateriaAsignada, ModeloEvaluativo, Persona, ProfesorMateria, Profesor, TipoProfesor, Clase, \
    Aula, Bloque, Turno, DetalleModeloEvaluativo, HorarioExamen, HorarioExamenDetalle, Administrativo, Matricula, \
    Inscripcion, InscripcionEncuestaGrupoEstudiantes, RespuestaPreguntaEncuestaGrupoEstudiantes, MONTH_NAMES, \
    SedeVirtual, LaboratorioVirtual
from rest_framework import serializers
from api.serializers.base.modalidad import BaseModalidadSerializer
from api.serializers.base.persona import PersonaBaseSerializer
from api.helpers.serializers_model_helper import Helper_ModelSerializer
from sga.templatetags.sga_extras import encrypt


class TipoProfesorSerializer(Helper_ModelSerializer):
    class Meta:
        model = TipoProfesor
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class BloqueSerializer(Helper_ModelSerializer):

    class Meta:
        model = Bloque
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class AulaSerializer(Helper_ModelSerializer):
    bloque = BloqueSerializer()
    display = serializers.SerializerMethodField()

    class Meta:
        model = Aula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_display(self, obj):
        if obj.bloque:
            return u'%s - %s (Cap: %s)' % (obj.nombre, obj.bloque.descripcion, str(obj.capacidad))
        return u'%s (Cap: %s)' % (obj.nombre, str(obj.capacidad))


class PersonaSerializer(PersonaBaseSerializer):

    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NivelMallaSerializer(Helper_ModelSerializer):
    tiene_conflicto_horarioexamen_aula = serializers.SerializerMethodField()

    class Meta:
        model = NivelMalla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_tiene_conflicto_horarioexamen_aula(self, obj):
        conflicto = obj.tiene_conflicto_horarioexamen_aula(self.context['periodo_id'], self.context['sesion_id'], self.context['coordinacion_id'],  self.context['malla_id'])
        return conflicto


class ModeloEvaluativoSerializer(Helper_ModelSerializer):

    class Meta:
        model = ModeloEvaluativo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class DetalleModeloEvaluativoSerializer(Helper_ModelSerializer):

    class Meta:
        model = DetalleModeloEvaluativo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class AsignaturaSerializer(Helper_ModelSerializer):

    class Meta:
        model = Asignatura
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ParaleloSerializer(Helper_ModelSerializer):
    tiene_conflicto_horarioexamen_aula = serializers.SerializerMethodField()

    class Meta:
        model = Paralelo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_tiene_conflicto_horarioexamen_aula(self, obj):
        conflicto = obj.tiene_conflicto_horarioexamen_aula(self.context['periodo_id'], self.context['sesion_id'], self.context['coordinacion_id'],  self.context['malla_id'], self.context['nivelmalla_id'])
        return conflicto


class CoordinacionSerializer(Helper_ModelSerializer):

    class Meta:
        model = Coordinacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ModalidadSerializer(BaseModalidadSerializer):
    class Meta:
        model = Modalidad
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class SesionSerializer(Helper_ModelSerializer):
    class Meta:
        model = Sesion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class CarreraSerializer(Helper_ModelSerializer):
    modalidad_display = serializers.SerializerMethodField()

    class Meta:
        model = Carrera
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_modalidad_display(self, obj):
        return obj.get_modalidad_display()


class MallaSerializer(Helper_ModelSerializer):
    carrera = CarreraSerializer()
    tiene_conflicto_horarioexamen_aula = serializers.SerializerMethodField()

    class Meta:
        model = Malla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_tiene_conflicto_horarioexamen_aula(self, obj):
        conflicto = obj.tiene_conflicto_horarioexamen_aula(self.context['periodo_id'], self.context['sesion_id'], self.context['coordinacion_id'])
        return conflicto


class AuxMallaSerializer(Helper_ModelSerializer):
    carrera = CarreraSerializer()
    display = serializers.SerializerMethodField()

    class Meta:
        model = Malla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_display(self, obj):
        return u'%s (%s %s)' % (obj.carrera.nombre_completo(), MONTH_NAMES[obj.inicio.month - 1], str(obj.inicio.year))


class AuxNivelMallaSerializer(Helper_ModelSerializer):

    class Meta:
        model = NivelMalla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class AuxAsignaturaMallaSerializer(Helper_ModelSerializer):
    malla = AuxMallaSerializer()
    asignatura = AsignaturaSerializer()
    nivelmalla = AuxNivelMallaSerializer()

    class Meta:
        model = AsignaturaMalla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class AsignaturaMallaSerializer(Helper_ModelSerializer):
    malla = MallaSerializer()
    asignatura = AsignaturaSerializer()
    nivelmalla = NivelMallaSerializer()

    class Meta:
        model = AsignaturaMalla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class AdministrativoSerializer(Helper_ModelSerializer):
    persona = PersonaSerializer()
    display = serializers.SerializerMethodField()

    class Meta:
        model = Administrativo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_display(self, obj):
        return f"{obj.persona.nombre_completo()}"


class ProfesorSerializer(Helper_ModelSerializer):
    persona = PersonaSerializer()
    display = serializers.SerializerMethodField()

    class Meta:
        model = Profesor
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_display(self, obj):
        return f"{obj.persona.nombre_completo()}"


class ProfesorMateriaSerializer(Helper_ModelSerializer):
    profesor = ProfesorSerializer()
    tipoprofesor = TipoProfesorSerializer()
    display = serializers.SerializerMethodField()

    class Meta:
        model = ProfesorMateria
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_display(self, obj):
        return f"{obj.tipoprofesor.nombre} - {obj.profesor.persona.nombre_completo()}"


class TurnoSerializer(Helper_ModelSerializer):

    class Meta:
        model = Turno
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ClaseSerializer(Helper_ModelSerializer):
    turno = TurnoSerializer()
    tipohorario_display = serializers.SerializerMethodField()
    dia_display = serializers.SerializerMethodField()
    aula = AulaSerializer()

    class Meta:
        model = Clase
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_tipohorario_display(self, obj):
        return obj.get_tipohorario_display()

    def get_dia_display(self, obj):
        return obj.get_dia_display()


class HorarioExamenSerializer(Helper_ModelSerializer):
    detallemodelo = DetalleModeloEvaluativoSerializer()

    class Meta:
        model = HorarioExamen
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class HorarioExamenDetalleSerializer(Helper_ModelSerializer):
    horarioexamen = HorarioExamenSerializer()
    aula = AulaSerializer()
    conflicto_horarioexamen_aula = serializers.SerializerMethodField()
    conflicto_horarioexamen_profesor = serializers.SerializerMethodField()
    responsable = serializers.SerializerMethodField()
    puede_editar = serializers.SerializerMethodField()
    puede_eliminar = serializers.SerializerMethodField()

    class Meta:
        model = HorarioExamenDetalle
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_conflicto_horarioexamen_aula(self, obj):
        horariosexamenes = obj.conflicto_horarioexamen_aula()
        return HorarioExamenDetalleAuxSerializer(horariosexamenes, many=True).data if horariosexamenes.values("id").exists() else []

    def get_conflicto_horarioexamen_profesor(self, obj):
        horariosexamenes = obj.conflicto_horarioexamen_profesor()
        return HorarioExamenDetalleAuxSerializer(horariosexamenes, many=True).data if horariosexamenes.values("id").exists() else []

    def get_responsable(self, obj):
        if obj.tiporesponsable == 0:
            return []
        elif obj.tiporesponsable == 1:
            return ProfesorMateriaSerializer(obj.profesormateria).data if not obj.profesormateria is None else {}
        elif obj.tiporesponsable == 2:
            return ProfesorSerializer(obj.profesor).data if not obj.profesor is None else {}
        elif obj.tiporesponsable == 3:
            return AdministrativoSerializer(obj.administrativo).data if not obj.administrativo is None else {}

    def get_puede_editar(self, obj):
        coordinacion = obj.horarioexamen.materia.coordinacion_materia()
        examen = obj.horarioexamen.detallemodelo
        if not coordinacion:
            return False
        if coordinacion.id in [1,2,3,4,5]:
            puede_editar_ex1 = variable_valor('PUEDE_EDITAR_EXAMEN_1_PREGRADO')
            puede_editar_ex2 = variable_valor('PUEDE_EDITAR_EXAMEN_2_PREGRADO')
            puede_editar_re = variable_valor('PUEDE_EDITAR_EXAMEN_RE_PREGRADO')
            if examen.nombre == 'EX1':
                return puede_editar_ex1
            elif examen.nombre == 'EX2':
                return puede_editar_ex2
            elif examen.nombre == 'RE':
                return puede_editar_re
        elif coordinacion.id in [9]:
            puede_editar_ex = variable_valor('PUEDE_EDITAR_EXAMEN_ADMISION')
            if examen.nombre == 'EX':
                return puede_editar_ex
        return False

    def get_puede_eliminar(self, obj):
        coordinacion = obj.horarioexamen.materia.coordinacion_materia()
        examen = obj.horarioexamen.detallemodelo
        if not coordinacion:
            return False
        if coordinacion.id in [1,2,3,4,5]:
            puede_eliminar_ex1 = variable_valor('PUEDE_ELIMINAR_EXAMEN_1_PREGRADO')
            puede_eliminar_ex2 = variable_valor('PUEDE_ELIMINAR_EXAMEN_2_PREGRADO')
            puede_eliminar_re = variable_valor('PUEDE_ELIMINAR_EXAMEN_RE_PREGRADO')
            if examen.nombre == 'EX1':
                return puede_eliminar_ex1
            elif examen.nombre == 'EX2':
                return puede_eliminar_ex2
            elif examen.nombre == 'RE':
                return puede_eliminar_re
        elif coordinacion.id in [9]:
            puede_eliminar_ex = variable_valor('PUEDE_ELIMINAR_EXAMEN_ADMISION')
            if examen.nombre == 'EX':
                return puede_eliminar_ex
        return False


class HorarioExamenDetalleAuxSerializer(Helper_ModelSerializer):

    horarioexamen = HorarioExamenSerializer()
    aula = AulaSerializer()

    class Meta:
        model = HorarioExamenDetalle
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MateriaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    asignaturamalla = AsignaturaMallaSerializer()
    asignatura = AsignaturaSerializer()
    matriculados = serializers.SerializerMethodField()
    modeloevaluativo = ModeloEvaluativoSerializer()
    configuracionexamen = serializers.SerializerMethodField()
    profesores = serializers.SerializerMethodField()
    horario_clase = serializers.SerializerMethodField()
    horario_examen = serializers.SerializerMethodField()
    aulaprincipal = serializers.SerializerMethodField()
    tiene_conflictohorarioexamen = serializers.SerializerMethodField()

    class Meta:
        model = Materia
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id

    def get_matriculados(self, obj):
        return null_to_numeric(len(MateriaAsignada.objects.filter(status=True, materia=obj)))

    def get_profesores(self, obj):
        eProfesores = obj.profesores_materia()
        return ProfesorMateriaSerializer(eProfesores, many=True).data if eProfesores.values("id").exists() else []

    def get_horario_clase(self, obj):
        eClases = Clase.objects.filter(status=True, activo=True, materia=obj)
        eAulas = Aula.objects.filter(pk__in=eClases.values_list("aula_id", flat=True))
        aData = []
        if eAulas.values("id").exists():
            for eAula in eAulas:
                eAula_s = AulaSerializer(eAula).data
                eClases_s = ClaseSerializer(eClases.filter(aula=eAula).order_by("dia", 'turno__comienza'), many=True).data
                eAula_s.__setitem__('eClases', eClases_s)
                aData.append(eAula_s)
        return aData

    def get_horario_examen(self, obj):
        configuracionexamen = obj.configuracionexamen()
        if configuracionexamen:
            eHorarioExamenDetalles = HorarioExamenDetalle.objects.filter(horarioexamen__materia=obj, horarioexamen__detallemodelo__in=configuracionexamen, status=True).order_by('horarioexamen__detallemodelo__orden')
            return HorarioExamenDetalleSerializer(eHorarioExamenDetalles, many=True).data if eHorarioExamenDetalles.values("id").exists() else []
        return []

    def get_configuracionexamen(self, obj):
        configuracionexamen = obj.configuracionexamen()
        if configuracionexamen:
            return DetalleModeloEvaluativoSerializer(configuracionexamen, many=True).data if configuracionexamen.values("id").exists() else []
        return []

    def get_aulaprincipal(self, obj):
        eClases = Clase.objects.filter(status=True, activo=True, materia=obj)
        eAulas = Aula.objects.filter(pk__in=eClases.values_list("aula_id", flat=True))
        return AulaSerializer(eAulas.first()).data if eAulas.values("id").exists() else None

    def get_tiene_conflictohorarioexamen(self, obj):
        return obj.tiene_conflictohorarioexamen() > 0


class InscripcionSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    persona = PersonaSerializer()
    carrera = CarreraSerializer()
    modalidad = ModalidadSerializer()

    class Meta:
        model = Inscripcion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class MatriculaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    inscripcion = InscripcionSerializer()
    sedeexamenes = serializers.SerializerMethodField()

    class Meta:
        model = Matricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def sedeexamenes(self, obj):
        eInscripcionEncuestaGrupoEstudiantes = InscripcionEncuestaGrupoEstudiantes.objects.filter(status=True, inscripcion=obj)
        if not eInscripcionEncuestaGrupoEstudiantes.values("id").filter(respondio=True).exists():
            return 'Milagro'
        eInscripcionEncuestaGrupoEstudiante = eInscripcionEncuestaGrupoEstudiantes.filter(respondio=True).first()
        eRespuestaPreguntaEncuestaGrupoEstudiantes = RespuestaPreguntaEncuestaGrupoEstudiantes.objects.filter(inscripcionencuesta=eInscripcionEncuestaGrupoEstudiante)
        # if eRespuestaPreguntaEncuestaGrupoEstudiantes.filter(respuesta__isnull=)

    def get_idm(self, obj):
        return obj.id

class MateriaAsignadaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    matricula = MatriculaSerializer()
    materia = MateriaSerializer()

    class Meta:
        model = MateriaAsignada
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class AuxParaleloSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model = Paralelo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class AuxMateriaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    asignaturamalla = AuxAsignaturaMallaSerializer()
    asignatura = AsignaturaSerializer()
    paralelomateria = AuxParaleloSerializer()

    class Meta:
        model = Materia
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class AuxMatriculaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    inscripcion = InscripcionSerializer()

    class Meta:
        model = Matricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class AuxMateriaAsignadaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    matricula = AuxMatriculaSerializer()
    materia = AuxMateriaSerializer()

    class Meta:
        model = MateriaAsignada
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class MateriaAsignadaPlanificacionSedeVirtualExamenSerializer(Helper_ModelSerializer):
    materiaasignada = AuxMateriaAsignadaSerializer()

    class Meta:
        model = MateriaAsignadaPlanificacionSedeVirtualExamen
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class LaboratorioVirtualSerializer(Helper_ModelSerializer):

    class Meta:
        model = LaboratorioVirtual
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class AulaPlanificacionSedeVirtualExamenSerializer(Helper_ModelSerializer):
    aula = LaboratorioVirtualSerializer()
    cantidadad_planificadas = serializers.SerializerMethodField()
    enuso = serializers.SerializerMethodField()
    responsable = PersonaSerializer()
    supervisor = PersonaSerializer()
    cant_asistencia = serializers.SerializerMethodField()

    class Meta:
        model = AulaPlanificacionSedeVirtualExamen
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_display(self, obj):
        return f"{obj.aula.nombre} ({obj.aula.capacidad}) - Turno: {obj.turnoplanificacion.horainicio.__str__()} a {obj.turnoplanificacion.horafin.__str__()} - Fecha: {obj.turnoplanificacion.fechaplanificacion.fecha.__str__()} - Sede: {obj.turnoplanificacion.fechaplanificacion.sede.__str__()}"

    def get_cantidadad_planificadas(self, obj):
        return obj.cantidadad_planificadas()

    def get_enuso(self, obj):
        return obj.enuso()

    def get_cant_asistencia(self, obj):
        return obj.turnoplanificacion.fechaplanificacion.sede.get_asistencias(sede= None, fecha=None, turno=None, aula=obj,periodo =obj.turnoplanificacion.fechaplanificacion.periodo)


class TurnoPlanificacionSedeVirtualExamenSerializer(Helper_ModelSerializer):
    aulasplanificadas = serializers.SerializerMethodField()
    idm = serializers.SerializerMethodField()
    enuso = serializers.SerializerMethodField()
    cant_asistencia = serializers.SerializerMethodField()

    class Meta:
        model = TurnoPlanificacionSedeVirtualExamen
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_aulasplanificadas(self, obj):
        if 'isView_AulaPlanificacion' in self.context and self.context['isView_AulaPlanificacion']:
            eAulaPlanificacionSedeVirtualExamenes = AulaPlanificacionSedeVirtualExamen.objects.filter(turnoplanificacion=obj, status=True)
            return AulaPlanificacionSedeVirtualExamenSerializer(eAulaPlanificacionSedeVirtualExamenes, context=self.context, many=True).data if eAulaPlanificacionSedeVirtualExamenes.values("id").exists() else []
        return []

    def get_display(self, obj):
        return f"{obj.horainicio.__str__()} a {obj.horafin.__str__()} - Fecha: {obj.fechaplanificacion.fecha.__str__()} - Sede: {obj.fechaplanificacion.sede.__str__()}"

    def get_idm(self, obj):
        return obj.id

    def get_enuso(self, obj):
        return obj.enuso()

    def get_cant_asistencia(self, obj):
        return obj.fechaplanificacion.sede.get_asistencias(sede= None, fecha=None, turno=obj, aula=None,periodo =obj.fechaplanificacion.periodo)


class FechaPlanificacionSedeVirtualExamenSerializer(Helper_ModelSerializer):
    horasplanificadas = serializers.SerializerMethodField()
    sede_id = serializers.SerializerMethodField()
    idm = serializers.SerializerMethodField()
    enuso = serializers.SerializerMethodField()
    supervisor = PersonaSerializer()
    cant_asistencia = serializers.SerializerMethodField()
    class Meta:
        model = FechaPlanificacionSedeVirtualExamen
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_horasplanificadas(self, obj):
        if 'isView_HoraPlanificacion' in self.context and self.context['isView_HoraPlanificacion']:
            eTurnoPlanificacionSedeVirtualExamenes = TurnoPlanificacionSedeVirtualExamen.objects.filter(fechaplanificacion=obj, status=True)
            return TurnoPlanificacionSedeVirtualExamenSerializer(eTurnoPlanificacionSedeVirtualExamenes, context=self.context, many=True).data if eTurnoPlanificacionSedeVirtualExamenes.values("id").exists() else []
        return []

    def get_display(self, obj):
        return f"{obj.fecha.__str__()} - Sede: {obj.sede.__str__()}"

    def get_sede_id(self, obj):
        return encrypt(obj.id)

    def get_idm(self, obj):
        return obj.id

    def get_enuso(self, obj):
        return obj.enuso()

    def get_cant_asistencia(self, obj):
        return obj.sede.get_asistencias(sede= None, fecha=obj, turno=None, aula=None,periodo =obj.periodo)


class SedeVirtualSerializer(Helper_ModelSerializer):
    fechaplanificacion = serializers.SerializerMethodField()
    idm = serializers.SerializerMethodField()

    class Meta:
        model = SedeVirtual
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_fechaplanificacion(self, obj):
        if 'isView_FechaPlanificacion' in self.context and self.context['isView_FechaPlanificacion']:
            eFechaPlanificacionSedeVirtualExamenes = FechaPlanificacionSedeVirtualExamen.objects.filter(sede=obj, periodo_id=self.context['periodo_id'], status=True)
            return FechaPlanificacionSedeVirtualExamenSerializer(eFechaPlanificacionSedeVirtualExamenes, context=self.context, many=True).data if eFechaPlanificacionSedeVirtualExamenes.values("id").exists() else []
        return []

    def get_idm(self, obj):
        return obj.id

