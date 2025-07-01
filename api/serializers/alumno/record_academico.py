# coding=utf-8
from datetime import datetime

from oma.models import InscripcionCurso
from sga.funciones import null_to_decimal
from sga.models import Inscripcion, NivelMalla, MateriaAsignada, Nivel, Malla, Carrera, Persona, \
    Periodo, Asignatura, Sesion, Materia, AsignaturaMalla, Coordinacion, Sede, RecordAcademico, ModuloMalla, \
    MateriaCursoEscuelaComplementaria, CursoEscuelaComplementaria, Profesor, Modalidad, MateriaAsignadaHomologacion, \
    MateriaAsignadaConvalidacion, HomologacionInscripcion, HistoricoRecordAcademico
from rest_framework import serializers
from api.serializers.base.persona import PersonaBaseSerializer
from api.serializers.base.modalidad import BaseModalidadSerializer
from api.helpers.serializers_model_helper import Helper_ModelSerializer


class NotaSesionSerializer(Helper_ModelSerializer):

    class Meta:
        model = Sesion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NotaPersonaSerializer(PersonaBaseSerializer):

    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NotaProfesorSerializer(Helper_ModelSerializer):
    persona = NotaPersonaSerializer()

    class Meta:
        model = Profesor
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NotaCoordinacionSerializer(Helper_ModelSerializer):

    class Meta:
        model = Coordinacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NotaCarreraSerializer(Helper_ModelSerializer):

    class Meta:
        model = Carrera
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NotaModalidadSerializer(BaseModalidadSerializer):

    class Meta:
        model = Modalidad
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NotaInscripcionSerializer(Helper_ModelSerializer):
    persona = NotaPersonaSerializer()
    carrera = NotaCarreraSerializer()
    coordinacion = NotaCoordinacionSerializer()
    sesion = NotaSesionSerializer()
    modalidad = NotaModalidadSerializer()
    promedio_general = serializers.SerializerMethodField()
    total_creditos_malla = serializers.SerializerMethodField()
    total_creditos_modulos = serializers.SerializerMethodField()
    total_creditos_otros = serializers.SerializerMethodField()
    total_horas = serializers.SerializerMethodField()
    total_creditos = serializers.SerializerMethodField()
    total_aprobadas = serializers.SerializerMethodField()
    total_reprobadas = serializers.SerializerMethodField()
    total_horas_practicas = serializers.SerializerMethodField()
    total_horas_vinculacion = serializers.SerializerMethodField()
    es_exonerado = serializers.SerializerMethodField()

    class Meta:
        model = Inscripcion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_total_creditos_malla(self, obj):
        return null_to_decimal(obj.total_creditos_malla(), 2)

    def get_total_creditos_modulos(self, obj):
        return null_to_decimal(obj.total_creditos_modulos(), 2)

    def get_total_creditos_otros(self, obj):
        return null_to_decimal(obj.total_creditos_otros(), 2)

    def get_total_horas(self, obj):
        return null_to_decimal(obj.total_horas())

    def get_total_creditos(self, obj):
        return null_to_decimal(obj.total_creditos(), 2)

    def get_promedio_general(self, obj):
        return null_to_decimal(obj.promedio_record(), 2)

    def get_total_aprobadas(self, obj):
        return len(obj.recordacademico_set.values('id').filter(aprobada=True, valida=True))

    def get_total_reprobadas(self, obj):
        return len(obj.recordacademico_set.values('id').filter(aprobada=False, valida=True))

    def get_total_horas_practicas(self, obj):
        return obj.numero_horas_practicas_pre_profesionales()

    def get_total_horas_vinculacion(self, obj):
        return obj.numero_horas_proyectos_vinculacion()

    def get_es_exonerado(self, obj):
        return (obj.fechainicioprimernivel if obj.fechainicioprimernivel else datetime.now().date()) <= datetime(2009, 1, 21, 23, 59, 59).date()


class NotaPeriodoSerializer(Helper_ModelSerializer):

    class Meta:
        model = Periodo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NotaMallaSerializer(Helper_ModelSerializer):
    carrera = NotaCarreraSerializer()

    class Meta:
        model = Malla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NotaNivelMallaSerializer(Helper_ModelSerializer):

    class Meta:
        model = NivelMalla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NotaAsignaturaSerializer(Helper_ModelSerializer):

    class Meta:
        model = Asignatura
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NotaAsignaturaMallaSerializer(Helper_ModelSerializer):
    asignatura = NotaAsignaturaSerializer()
    nivelmalla = NotaNivelMallaSerializer()
    malla = NotaMallaSerializer()

    class Meta:
        model = AsignaturaMalla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NotaSedeSerializer(Helper_ModelSerializer):

    class Meta:
        model = Sede
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NotaNivelSerializer(Helper_ModelSerializer):
    sede = NotaSedeSerializer()
    periodo = NotaPeriodoSerializer()

    class Meta:
        model = Nivel
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NotaMateriaSerializer(Helper_ModelSerializer):
    nivel = NotaNivelSerializer()
    asignatura = NotaAsignaturaSerializer()
    asignaturamalla = NotaAsignaturaMallaSerializer()

    class Meta:
        model = Materia
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NotaMateriaAsignadaSerializer(Helper_ModelSerializer):
    materia = NotaMateriaSerializer()


    class Meta:
        model = MateriaAsignada
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NotaModuloMallaSerializer(Helper_ModelSerializer):
    malla = NotaMallaSerializer()
    asignatura = NotaAsignaturaSerializer()

    class Meta:
        model = ModuloMalla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NotaAsignaturaSerializer(Helper_ModelSerializer):

    class Meta:
        model = Asignatura
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NotaCursoEscuelaComplementariaSerializer(Helper_ModelSerializer):

    class Meta:
        model = CursoEscuelaComplementaria
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NotaMateriaCursoEscuelaComplementariaSerializer(Helper_ModelSerializer):
    curso = NotaCursoEscuelaComplementariaSerializer()

    class Meta:
        model = MateriaCursoEscuelaComplementaria
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class HistoricoPeriodoSerializer(Helper_ModelSerializer):
    class Meta:
        model = Periodo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class HistoricoNivelSerializer(Helper_ModelSerializer):
    periodo = HistoricoPeriodoSerializer()
    class Meta:
        model = Nivel
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class ProfesorPersonaSerializer(PersonaBaseSerializer):
    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class ProfesorSerializer(Helper_ModelSerializer):
    persona = ProfesorPersonaSerializer()

    class Meta:
        model = Profesor
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class HistoricoMateriaSerializer(Helper_ModelSerializer):
    nivel = HistoricoNivelSerializer()
    profesor_principal = serializers.SerializerMethodField()

    class Meta:
        model = Materia
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_profesor_principal(self, obj):
        profesor = obj.profesor_principal()
        return ProfesorSerializer(profesor).data if profesor else None

class HistoricoAsignaturaSerializer(Helper_ModelSerializer):

    class Meta:
        model = Asignatura
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class HistoricoNivelMallaSerializer(Helper_ModelSerializer):

    class Meta:
        model = NivelMalla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class HistoricoHomologacionInscripcionMallaSerializer(Helper_ModelSerializer):

    class Meta:
        model = HomologacionInscripcion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class HistoricoMateriaCursoEscuelaComplementariaSerializer(Helper_ModelSerializer):
    profesor = ProfesorSerializer()
    class Meta:
        model = MateriaCursoEscuelaComplementaria
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class HistoricoRecordAcademicoSerializer(Helper_ModelSerializer):
    asignatura = HistoricoAsignaturaSerializer()
    materiaregular= HistoricoMateriaSerializer()
    nivel_asignatura = serializers.SerializerMethodField()
    datos_homologacion = serializers.SerializerMethodField()
    materiacurso= HistoricoMateriaCursoEscuelaComplementariaSerializer()

    class Meta:
        model = HistoricoRecordAcademico
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_nivel_asignatura(self, obj):
        asig= obj.nivel_asignatura()
        nivelm = HistoricoNivelMallaSerializer(asig)
        return nivelm.data

    def get_datos_homologacion(self, obj):
        datos = obj.datos_homologacion()
        datoshomo = HistoricoHomologacionInscripcionMallaSerializer(datos)
        return datoshomo.data


class InscripcionCursoSerializer(Helper_ModelSerializer):
    archivocertificado = serializers.SerializerMethodField()

    class Meta:
        model = InscripcionCurso
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_archivocertificado(self, obj):
        if obj.archivocertificado:
            return self.get_media_url(obj.archivocertificado.url)
        return None


class NotaRecorAcademicoSerializer(Helper_ModelSerializer):
    modulomalla = NotaModuloMallaSerializer()
    asignaturamalla = NotaAsignaturaMallaSerializer()
    asignatura = NotaAsignaturaSerializer()
    asignaturaold = NotaAsignaturaSerializer()
    materiaregular = NotaMateriaSerializer()
    materiacurso = NotaMateriaCursoEscuelaComplementariaSerializer()
    asignaturamallahistorico = NotaAsignaturaMallaSerializer()
    profesor = serializers.SerializerMethodField()
    tiene_deuda_matricula = serializers.SerializerMethodField()
    ocultarnota = serializers.SerializerMethodField()
    archivohomologacion = serializers.SerializerMethodField()
    archivoconvalidacion = serializers.SerializerMethodField()
    ofimatica = InscripcionCursoSerializer()

    class Meta:
        model = RecordAcademico
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_profesor(self, obj):
        if not obj.inscripcion.modalidad.es_enlinea():
            eProfesor = obj.profesor()
        else:
            eProfesor = obj.profesor_virtual()
        return NotaProfesorSerializer(eProfesor).data if eProfesor else None

    def get_tiene_deuda_matricula(self, obj):
        if obj.inscripcion.coordinacion and obj.inscripcion.coordinacion.id == 9:
            if obj.materiaregular:
                periodo = obj.materiaregular.nivel.periodo
                return obj.inscripcion.tiene_deuda_matricula(periodo)
            return False
        return False

    def get_ocultarnota(self, obj):
        if obj.inscripcion.coordinacion and obj.inscripcion.coordinacion.id == 9:
            if obj.materiaregular:
               return obj.materiaregular.nivel.periodo.ocultarnota
            return False
        return False

    def get_archivohomologacion(self, obj):
        if obj.homologada:
            homologacion = obj.datos_homologacion()
            if not homologacion:
                return None
            if not homologacion.archivo:
                return None
            if not homologacion.archivo.url:
                return None
            return self.get_media_url(homologacion.archivo.url)
        return None

    def get_archivoconvalidacion(self, obj):
        if obj.convalidacion:
            convalidacion = obj.datos_convalidacion()
            if not convalidacion:
                return None
            if not convalidacion.archivo:
                return None
            if not convalidacion.archivo.url:
                return None
            return self.get_media_url(convalidacion.archivo.url)
        return None

