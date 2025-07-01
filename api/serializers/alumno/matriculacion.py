# coding=utf-8
from django.contrib.auth.models import User, Group
from django.db.models import Q, Sum

from api.serializers.base.tipoestado import TipoEstadoBaseSerializer
from bd.models import FuncionRequisitoIngresoUnidadIntegracionCurricular
from inno.models import RequisitoIngresoUnidadIntegracionCurricular, MallaHorasSemanalesComponentes
from matricula.models import PeriodoMatricula, ArticuloUltimaMatricula, CasoUltimaMatricula
from settings import RUBRO_ARANCEL
from sga.funciones import null_to_decimal
from sga.models import Inscripcion, InscripcionMalla, NivelMalla, MateriaAsignada, Nivel, Malla, Carrera, Persona, \
    Periodo, PreMatricula, PreMatriculaAsignatura, Asignatura, Sesion, Materia, AsignaturaMalla, Matricula, Paralelo, \
    TipoEstado, Coordinacion, Clase, Sede, AlumnosPracticaMateria, Raza, PerfilInscripcion, Discapacidad, \
    InstitucionBeca, NacionalidadIndigena, Credo, PersonaReligion, Pais, MigrantePersona
from rest_framework import serializers
from api.serializers.base.persona import PersonaBaseSerializer
from api.helpers.serializers_model_helper import Helper_ModelSerializer
from sga.templatetags.sga_extras import encrypt


class MatriCredoSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model = Credo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class MatriRazaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model = Raza
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class MatriInstitucionBecaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model = InstitucionBeca
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class MatriDiscapacidadSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model = Discapacidad
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class MatriNacionalidadIndigenaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model = NacionalidadIndigena
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class MatriPerfilInscripcionSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model = PerfilInscripcion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class MatriParaleloSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model = Paralelo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class MatriSesionSerializer(Helper_ModelSerializer):

    class Meta:
        model = Sesion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriPersonaSerializer(PersonaBaseSerializer):

    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriCoordinacionSerializer(Helper_ModelSerializer):

    class Meta:
        model = Coordinacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriCarreraSerializer(Helper_ModelSerializer):

    class Meta:
        model = Carrera
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriInscripcionSerializer(Helper_ModelSerializer):
    carrera = MatriCarreraSerializer()
    sesion = MatriSesionSerializer()
    tiene_perdida_gratuidad = serializers.SerializerMethodField()
    motivos_perdida_gratuidad = serializers.SerializerMethodField()

    class Meta:
        model = Inscripcion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_tiene_perdida_gratuidad(self, obj):
        return obj.tiene_perdida_gratuidad()

    def get_motivos_perdida_gratuidad(self, obj):
        return obj.motivos_perdida_gratuidad()


class MatriPeriodoSerializer(Helper_ModelSerializer):

    class Meta:
        model = Periodo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriArticuloUltimaMatriculaSerializer(Helper_ModelSerializer):

    class Meta:
        model = ArticuloUltimaMatricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriCasoUltimaMatriculaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    articulo = MatriArticuloUltimaMatriculaSerializer()

    class Meta:
        model = CasoUltimaMatricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class MatriConfiguracionUltimaMatriculaSerializer(Helper_ModelSerializer):
    articulo = MatriArticuloUltimaMatriculaSerializer()
    caso = MatriCasoUltimaMatriculaSerializer(many=True)
    tipo_display = serializers.SerializerMethodField()

    class Meta:
        model = CasoUltimaMatricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_tipo_display(self, obj):
        return obj.get_tipo_display()


class MatriPeriodoMatriculaSerializer(Helper_ModelSerializer):
    periodo = MatriPeriodoSerializer()
    configuracion_ultima_matricula = MatriConfiguracionUltimaMatriculaSerializer()
    bloquea_por_deuda = serializers.SerializerMethodField()

    class Meta:
        model = PeriodoMatricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_bloquea_por_deuda(self, obj):
        is_superuser = self.context.get('is_superuser', False)
        return False if is_superuser else obj.bloquea_por_deuda

class HorasSemanalesSerializer(Helper_ModelSerializer):

    class Meta:
        model = MallaHorasSemanalesComponentes
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class MatriMallaSerializer(Helper_ModelSerializer):
    carrera = MatriCarreraSerializer()
    horassemanales = serializers.SerializerMethodField()

    class Meta:
        model = Malla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_horassemanales(self, obj):
        horassem = obj.mallahorassemanalescomponentes_set.filter(status=True)
        return HorasSemanalesSerializer(horassem, many=True).data



class MatriInscripcionMallaSerializer(Helper_ModelSerializer):

    class Meta:
        model = InscripcionMalla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriculaSerializer(Helper_ModelSerializer):
    inscripcion = MatriInscripcionSerializer()
    tiene_token = serializers.SerializerMethodField()
    puede_reenviar_token = serializers.SerializerMethodField()
    contador_reenviar_email_token = serializers.SerializerMethodField()
    puede_quitar = serializers.SerializerMethodField()
    puede_agregar = serializers.SerializerMethodField()
    total_horas_semanales = serializers.SerializerMethodField()
    total_horas_contacto_docente = serializers.SerializerMethodField()
    tiene_pagos_matricula = serializers.SerializerMethodField()
    total_pagado_rubro = serializers.SerializerMethodField()
    total_saldo_rubro = serializers.SerializerMethodField()
    gratuidad = serializers.SerializerMethodField()
    rubros = serializers.SerializerMethodField()
    rubro_arancel = serializers.SerializerMethodField()
    puede_diferir_rubro_arancel = serializers.SerializerMethodField()
    nivel_id = serializers.SerializerMethodField()

    class Meta:
        model = Matricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_tiene_token(self, obj):
        return obj.tiene_token_retiro()

    def get_puede_reenviar_token(self, obj):
        return obj.puede_reenviar_email_token()

    def get_contador_reenviar_email_token(self, obj):
        return obj.contador_reenviar_email_token()

    def get_puede_quitar(self, obj):
        # if not obj.nivel.puede_quitar_materia_matricula():
        #     return False
        if obj.nivel.periodo.periodomatricula_set.values('id').filter(status=True).exists():
            periodomatricula = obj.nivel.periodo.periodomatricula_set.filter(status=True)[0]
            if not periodomatricula.ver_eliminar_matricula:
                return False
            if periodomatricula.puede_eliminar_materia_rubro_pagados:
                if obj.tiene_pagos_matricula():
                    return False
            if periodomatricula.puede_eliminar_materia_rubro_diferidos:
                if obj.aranceldiferido == 1:
                    return False
            # return periodomatricula.ver_eliminar_matricula and not obj.tiene_pagos_matricula() and obj.nivel.puede_quitar_materia_matricula()
        return True

    def get_puede_agregar(self, obj):
        if not obj.nivel.puede_agregar_materia_matricula():
            return False
        if obj.nivel.periodo.periodomatricula_set.values('id').filter(status=True).exists():
            periodomatricula = obj.nivel.periodo.periodomatricula_set.filter(status=True)[0]
            if not periodomatricula.puede_agregar_materia:
                return False
            if not periodomatricula.puede_agregar_materia_rubro_pagados:
                if obj.tiene_pagos_matricula():
                    return False
            if periodomatricula.puede_agregar_materia_rubro_diferidos:
                if obj.aranceldiferido == 1:
                    return False
        return True

    def get_total_horas_semanales(self, obj):
        materiasasignadas = obj.materiaasignada_set.all().order_by('materia__asignaturamalla__nivelmalla__orden')
        total = 0
        for ma in materiasasignadas:
            total = total + ma.materia.asignaturamalla.horastotal()
        return total

    def get_total_horas_contacto_docente(self, obj):
        materiasasignadas = obj.materiaasignada_set.all().order_by('materia__asignaturamalla__nivelmalla__orden')
        total = 0
        for ma in materiasasignadas:
            total = total + ma.materia.asignaturamalla.horasacdsemanal
        return total

    def get_tiene_pagos_matricula(self, obj):
        return obj.tiene_pagos_matricula()

    def get_total_pagado_rubro(self, obj):
        return obj.total_pagado_rubro()

    def get_total_saldo_rubro(self, obj):
        return obj.total_saldo_rubro()

    def get_gratuidad(self, obj):
        return obj.gratuidad()

    def get_rubros(self, obj):
        return obj.gratuidad()

    def get_puede_diferir_rubro_arancel(self, obj):
        return obj.puede_diferir_rubro_arancel()

    def get_rubro_arancel(self, obj):
        descripcion = ''
        valorarancel = obj.valor_total_rubros_arancel()
        if (rubro := obj.rubro_set.filter(status=True, tipo_id=RUBRO_ARANCEL).first()) is not None:
            descripcion = rubro.nombre
        return {'valorarancel': valorarancel, 'descripcion': descripcion}

    def get_nivel_id(self, obj):
        return encrypt(obj.nivel_id)


class MatriNivelMallaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model = NivelMalla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class MatriAsignaturaSerializer(Helper_ModelSerializer):

    class Meta:
        model = Asignatura
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriAsignaturaMallaSerializer(Helper_ModelSerializer):
    asignatura = MatriAsignaturaSerializer()
    nivelmalla = MatriNivelMallaSerializer()
    malla = MatriMallaSerializer()
    horas_semanal = serializers.SerializerMethodField()

    class Meta:
        model = AsignaturaMalla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_horas_semanal(self, obj):
        return obj.horastotal()


class MatriHorarioClaseSerializer(Helper_ModelSerializer):

    class Meta:
        model = Clase
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriSedeSerializer(Helper_ModelSerializer):

    class Meta:
        model = Sede
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriNivelSerializer(Helper_ModelSerializer):
    sede = MatriSedeSerializer()

    class Meta:
        model = Nivel
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriMateriaSerializer(Helper_ModelSerializer):
    nivel = MatriNivelSerializer()
    asignatura = MatriAsignaturaSerializer()
    asignaturamalla = MatriAsignaturaMallaSerializer()
    paralelomateria = MatriParaleloSerializer()
    puede_agregar = serializers.SerializerMethodField()
    coordinacion = serializers.SerializerMethodField()

    class Meta:
        model = Materia
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_puede_agregar(self, obj):
        return obj.nivel.puede_agregar_materia_matricula()

    def get_coordinacion(self, obj):
        return MatriCoordinacionSerializer(obj.coordinacion()).data if obj.coordinacion() else None


class MatriTipoEstadoSerializer(TipoEstadoBaseSerializer):

    class Meta:
        model = TipoEstado
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriMateriaAsignadaSerializer(Helper_ModelSerializer):
    materia = MatriMateriaSerializer()
    matricula = MatriculaSerializer()
    estado = MatriTipoEstadoSerializer()
    convalidada = serializers.SerializerMethodField()
    homologada = serializers.SerializerMethodField()
    retirado = serializers.SerializerMethodField()
    existe_en_malla = serializers.SerializerMethodField()
    valida_pararecord = serializers.SerializerMethodField()
    aprobada = serializers.SerializerMethodField()
    pertenece_malla = serializers.SerializerMethodField()
    tiene_token_retiro = serializers.SerializerMethodField()
    puede_reenviar_email_token = serializers.SerializerMethodField()
    contador_reenviar_email_token = serializers.SerializerMethodField()
    practica = serializers.SerializerMethodField()
    totalrecordasignatura = serializers.SerializerMethodField()
    va_num_matricula = serializers.SerializerMethodField()
    puede_quitar = serializers.SerializerMethodField()
    tiene_token = serializers.SerializerMethodField()
    puede_reenviar_token = serializers.SerializerMethodField()
    contador_reenviar_email_token = serializers.SerializerMethodField()

    class Meta:
        model = MateriaAsignada
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_convalidada(self, obj):
        return obj.convalidada()

    def get_homologada(self, obj):
        return obj.homologada()

    def get_retirado(self, obj):
        return obj.retirado()

    def get_existe_en_malla(self, obj):
        return obj.existe_en_malla()

    def get_valida_pararecord(self, obj):
        return obj.valida_pararecord()

    def get_aprobada(self, obj):
        return obj.aprobada()

    def get_pertenece_malla(self, obj):
        return obj.pertenece_malla()

    def get_tiene_token_retiro(self, obj):
        return obj.tiene_token_retiro()

    def get_puede_reenviar_email_token(self, obj):
        return obj.puede_reenviar_email_token()

    def get_contador_reenviar_email_token(self, obj):
        return obj.contador_reenviar_email_token()

    def get_practica(self, obj):
        practica = None
        alumnopracticamateria = obj.alumnopracticamateria()
        if alumnopracticamateria:
            if alumnopracticamateria.grupoprofesor:
                practica = alumnopracticamateria.grupoprofesor.get_paralelopractica_display()
        return practica

    def get_totalrecordasignatura(self, obj):
        eInscripcion = obj.matricula.inscripcion
        return eInscripcion.total_record_asignaturatodo(obj.materia.asignatura)

    def get_va_num_matricula(self, obj):
        return self.get_totalrecordasignatura(obj) + 1

    def get_puede_quitar(self, obj):
        if not obj.materia.nivel.puede_quitar_materia_matricula():
            return False
        if obj.matricula.nivel.periodo.periodomatricula_set.values('id').filter(status=True).exists():
            periodomatricula = obj.matricula.nivel.periodo.periodomatricula_set.filter(status=True)[0]
            if periodomatricula.puede_eliminar_materia_rubro_pagados:
                if obj.matricula.tiene_pagos_matricula():
                    return False
            if periodomatricula.puede_eliminar_materia_rubro_diferidos:
                if obj.matricula.aranceldiferido == 1:
                    return False
            puede_quitar_materia = self.get_totalrecordasignatura(obj) <= 2 and not obj.homologada() and not obj.convalidada() and obj.valida_pararecord() and not obj.retirado() and not obj.materia.cerrado and obj.notafinal == 0
            return puede_quitar_materia
        return True

    def get_tiene_token(self, obj):
        return obj.tiene_token_retiro()

    def get_puede_reenviar_token(self, obj):
        return obj.puede_reenviar_email_token()

    def get_contador_reenviar_email_token(self, obj):
        return obj.contador_reenviar_email_token()


class MatriAsignaturaSerializer(Helper_ModelSerializer):
    id_display = serializers.SerializerMethodField()

    class Meta:
        model = Asignatura
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_id_display(self, obj):
        return obj.id


class MatriPreMatriculaAsignaturaSerializer(Helper_ModelSerializer):
    modalidad_display = serializers.SerializerMethodField()
    asignatura = MatriAsignaturaSerializer()
    sesion = MatriSesionSerializer()

    class Meta:
        model = PreMatriculaAsignatura
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_modalidad_display(self, obj):
        return obj.get_modalidad_display()


class MatriPreMatriculaSerializer(Helper_ModelSerializer):
    prematriculaasignatura = MatriPreMatriculaAsignaturaSerializer(many=True)

    class Meta:
        model = PreMatricula
        exclude = ['usuario_creacion', 'usuario_modificacion', 'asignaturas']


class MatriFuncionRequisitoIngresoUnidadIntegracionCurricularSerializer(Helper_ModelSerializer):

    class Meta:
        model = FuncionRequisitoIngresoUnidadIntegracionCurricular
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriRequisitoIngresoUnidadIntegracionCurricularSerializer(Helper_ModelSerializer):
    requisito = MatriFuncionRequisitoIngresoUnidadIntegracionCurricularSerializer()
    cumple = serializers.SerializerMethodField()

    class Meta:
        model = RequisitoIngresoUnidadIntegracionCurricular
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_cumple(self, obj):
        return False


class MatriPersonaReligionSerializer(Helper_ModelSerializer):

    class Meta:
        model = PersonaReligion
        exclude = ['usuario_creacion', 'usuario_modificacion']


class PaisSerializer(Helper_ModelSerializer):

    class Meta:
        model = Pais
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MigrantePersonaSerializer(Helper_ModelSerializer):
    paisresidenciaencr = serializers.SerializerMethodField()

    class Meta:
        model = MigrantePersona
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_paisresidenciaencr(self, obj):
        return encrypt(obj.paisresidencia_id)


class MatriRubro(Helper_ModelSerializer):

    class Meta:
        from sagest.models import Rubro
        model = Rubro
        exclude = ['usuario_creacion', 'usuario_modificacion']
