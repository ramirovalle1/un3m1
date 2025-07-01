from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from api.serializers.base.persona import PersonaBaseSerializer
from rest_framework import serializers
from sga.models import Matricula, Nivel, Periodo, MateriaAsignada, Materia, Asignatura, Profesor, Persona, \
    ModeloEvaluativo, DetalleModeloEvaluativo, AsistenciaLeccion, EvaluacionGenerica, MatriculaGrupoSocioEconomico, \
    Malla, Inscripcion, Carrera, Silabo, TipoEstado, ProfesorMateria, AsignaturaMalla
from inno.models import InscripcionEncuestaEstudianteSeguimientoSilabo, EncuestaGrupoEstudianteSeguimientoSilabo
from socioecon.models import GrupoSocioEconomico


class ProfesorPersonaSerializer(PersonaBaseSerializer):
    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriAsignaturaSerializer(Helper_ModelSerializer):

    class Meta:
        model = Asignatura
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class DetalleModeloEvaluativoSerializer(Helper_ModelSerializer):
    # codigoevaluativo = CodigoEvaluacionSerializer()

    class Meta:
        model = DetalleModeloEvaluativo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ModeloEvaluativoSerializer(Helper_ModelSerializer):
    campos = serializers.SerializerMethodField()

    class Meta:
        model = ModeloEvaluativo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_campos(self, obj):
        camp = obj.campos()
        detallesnotas =  DetalleModeloEvaluativoSerializer(camp, many = True)
        return detallesnotas.data if camp.exists() else []


class ProfesorSerializer(Helper_ModelSerializer):
    persona = ProfesorPersonaSerializer()

    class Meta:
        model = Profesor
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class EvaluacionGenericaSerializer(Helper_ModelSerializer):
    detallemodeloevaluativo = DetalleModeloEvaluativoSerializer()

    class Meta:
        model = EvaluacionGenerica
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class SilaboSerializar(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model = Silabo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class MatriculaMateriaSerializer(Helper_ModelSerializer):
    asignatura = MatriAsignaturaSerializer()
    modeloevaluativo = ModeloEvaluativoSerializer()
    profesor = serializers.SerializerMethodField()
    nombre_mostrar = serializers.SerializerMethodField()
    mostrar_asigmalla = serializers.SerializerMethodField()
    silabo = serializers.SerializerMethodField()
    tipoprofesor = serializers.SerializerMethodField()
    fechainicioencuesta = serializers.SerializerMethodField()
    fechafinencuesta = serializers.SerializerMethodField()
    respondido = serializers.SerializerMethodField()
    encuestaactiva = serializers.SerializerMethodField()

    class Meta:
        model = Materia
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_tipoprofesor(self,obj):
        id_tipoprofesor = ProfesorMateria.objects.values_list(
            'tipoprofesor__id', flat=True).filter(status=True, materia_id=obj.id)
        if id_tipoprofesor:
            return id_tipoprofesor
        return None

    def get_mostrar_asigmalla(self,obj):
        idmalla = AsignaturaMalla.objects.values_list('malla_id').filter(pk=obj.asignaturamalla_id)
        if idmalla:
            return idmalla
        return None

    def get_fechainicioencuesta(self,obj):
        fechainicio = EncuestaGrupoEstudianteSeguimientoSilabo.objects.values_list(
            'fechainicioencuesta', flat=True).filter(status=True,
                                                     encuestagrupoestudiantes__inscripcionencuestaestudianteseguimientosilabo__materia_id=obj.id).distinct()
        if fechainicio:
            return fechainicio.first()
        return None

    def get_fechafinencuesta(self,obj):
        fechafin = EncuestaGrupoEstudianteSeguimientoSilabo.objects.values_list(
            'fechafinencuesta', flat=True).filter(status=True,
                                                     encuestagrupoestudiantes__inscripcionencuestaestudianteseguimientosilabo__materia_id=obj.id).distinct()
        if fechafin:
            return fechafin.first()
        return None

    def get_respondido(self,obj):
        respondio = InscripcionEncuestaEstudianteSeguimientoSilabo.objects.values_list(
            'respondio', flat=True).filter(status=True, materia_id=obj.id)
        if respondio:
            return respondio
        return None

    def get_encuestaactiva(self,obj):
        activo = EncuestaGrupoEstudianteSeguimientoSilabo.objects.values_list(
            'encuestagrupoestudiantes__activo', flat=True).filter(status=True,
                                                     encuestagrupoestudiantes__inscripcionencuestaestudianteseguimientosilabo__materia_id=obj.id).distinct()
        if activo:
            return activo.first()
        return None

    def get_profesor(self, obj):
        ePeriodoMatriculas = obj.nivel.periodo.periodomatricula_set.filter(status=True)
        profesor = obj.profesor_principal()
        if ePeriodoMatriculas.values("id").exists():
            ePeriodoMatricula = ePeriodoMatriculas[0]
            if not ePeriodoMatricula.ver_profesor_materia:
                profesor = None
        return ProfesorSerializer(profesor).data if profesor else None

    def get_nombre_mostrar(self, obj):
        import datetime
        hoy = datetime.datetime.now().date()
        nombre = obj.nombre_mostrar() if hoy >= obj.inicio else obj.nombre_mostrar_sin_profesor()
        ePeriodoMatriculas = obj.nivel.periodo.periodomatricula_set.filter(status=True)
        if ePeriodoMatriculas.values("id").exists():
            ePeriodoMatricula = ePeriodoMatriculas[0]
            if not ePeriodoMatricula.ver_profesor_materia:
                nombre = obj.nombre_mostrar_sin_profesor()
        return nombre

    def get_silabo(self, obj):
        profesor = obj.profesor_principal()
        silabo = obj.mi_silabo_activo(profesor)
        return SilaboSerializar(silabo).data if silabo else None

class InscripcionEncuestaEstudianteSeguimientoSilaboSerializer(Helper_ModelSerializer):
    materia = MatriculaMateriaSerializer()

    class Meta:
        model =  InscripcionEncuestaEstudianteSeguimientoSilabo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class AsistenciaLeccionSerializer(Helper_ModelSerializer):

    class Meta:
        model = AsistenciaLeccion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MallaSerializer(Helper_ModelSerializer):

    class Meta:
        model = Malla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class GrupoSocioEconomicoSerializer(Helper_ModelSerializer):

    class Meta:
        model = GrupoSocioEconomico
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class PeriodoSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model = Periodo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class NivelSerializer(Helper_ModelSerializer):
    periodo = PeriodoSerializer()

    class Meta:
        model = Nivel
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriculaGrupoSocioEconomicoSerializer(Helper_ModelSerializer):
    gruposocioeconomico = GrupoSocioEconomicoSerializer()

    class Meta:
        model = MatriculaGrupoSocioEconomico
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class CarreraSerializer(Helper_ModelSerializer):

    class Meta:
        model = Carrera
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class InscripcionSerializer(Helper_ModelSerializer):
    persona = ProfesorPersonaSerializer()
    carrera = CarreraSerializer()

    class Meta:
        model = Inscripcion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriculaSerializer(Helper_ModelSerializer):
    inscripcion = InscripcionSerializer()
    nivel = NivelSerializer()
    gruposocioeconomico = serializers.SerializerMethodField()
    total_pagado_rubro = serializers.SerializerMethodField()
    total_saldo_rubro = serializers.SerializerMethodField()
    tiene_deuda = serializers.SerializerMethodField()

    class Meta:
        model = Matricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_gruposocioeconomico(self, obj):
        mat = obj.matriculagruposocioeconomico()
        return GrupoSocioEconomicoSerializer(mat).data if mat else None

    def get_total_pagado_rubro(self, obj):
        return obj.total_pagado_rubro()

    def get_total_saldo_rubro(self, obj):
        return obj.total_saldo_rubro()

    def get_tiene_deuda(self, obj):
        return obj.tiene_deuda_pendiente()


class CompaMateriaAsignadaSerializer(Helper_ModelSerializer):
    matricula = MatriculaSerializer()

    class Meta:
        model = MateriaAsignada
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class TipoEstadoSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model = TipoEstado
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class MatriculaMateriaAsignadaSerializer(Helper_ModelSerializer):
    matricula = MatriculaSerializer()
    asistencia_real = serializers.SerializerMethodField()
    materia = MatriculaMateriaSerializer()
    asistencia_plan = serializers.SerializerMethodField()
    evaluaciong = serializers.SerializerMethodField()
    homologada = serializers.SerializerMethodField()
    retirado = serializers.SerializerMethodField()
    convalidada = serializers.SerializerMethodField()
    es_modulo_ingles = serializers.SerializerMethodField()
    estado = TipoEstadoSerializer()
    url_actacompromiso = serializers.SerializerMethodField()
    url_actacompromisovinculacion = serializers.SerializerMethodField()

    class Meta:
        model = MateriaAsignada
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_url_actacompromiso(self, obj):
        if obj.actacompromisopracticas:
            return self.get_media_url(obj.actacompromisopracticas.url)
        return None

    def get_url_actacompromisovinculacion(self, obj):
        if obj.actacompromisovinculacion:
            return self.get_media_url(obj.actacompromisovinculacion.url)
        return None

    def get_asistencia_real(self, obj):
        return obj.asistencia_real()

    def get_convalidada(self, obj):
        return obj.convalidada()

    def get_homologada(self, obj):
        return obj.homologada()

    def get_retirado(self, obj):
        return obj.retirado()

    def get_asistencia_plan(self, obj):
        return obj.asistencia_plan()

    def get_evaluaciong(self, obj):
        eva = obj.evaluacion_generica()
        evadetalle = EvaluacionGenericaSerializer(eva, many=True)
        return evadetalle.data if eva.exists() else []

    def get_es_modulo_ingles(self, obj):
        eMalla = obj.matricula.inscripcion.mi_malla()
        return obj.materia.asignatura.es_modulo_malla(eMalla)
