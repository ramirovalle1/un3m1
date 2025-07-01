from datetime import datetime, timedelta
from django.core.exceptions import ObjectDoesNotExist

from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from django.utils.safestring import mark_safe

from api.serializers.base.persona import PersonaBaseSerializer
from rest_framework import serializers

from inno.models import MateriaAsignadaPlanificacionSedeVirtualExamen, AulaPlanificacionSedeVirtualExamen, \
    TurnoPlanificacionSedeVirtualExamen, FechaPlanificacionSedeVirtualExamen, MatriculaSedeExamen, \
    DisertacionMateriaAsignadaPlanificacion, DisertacionGrupoPlanificacion, DisertacionAulaPlanificacion, \
    DisertacionTurnoPlanificacion, DisertacionFechaPlanificacion
from posgrado.models import SolicitudIngresoTitulacionPosgrado
from sga.models import Matricula, Nivel, Periodo, MateriaAsignada, Materia, Asignatura, Profesor, Persona, \
    ModeloEvaluativo, DetalleModeloEvaluativo, AsistenciaLeccion, EvaluacionGenerica, MatriculaGrupoSocioEconomico, \
    Malla, Inscripcion, Carrera, Silabo, HorarioExamen, HorarioExamenDetalle, LibroKohaProgramaAnaliticoAsignatura, \
    AsignaturaMalla, AprobarSilabo, GPGuiaPracticaSemanal, SilaboSemanal, DetalleSilaboSemanalTema, GPInstruccion, \
    Archivo, PlanificacionClaseSilabo, AvComunicacion, AvPreguntaDocente, ProfesorMateria, TestSilaboSemanal, \
    TareaSilaboSemanal, ForoSilaboSemanal, TareaPracticaSilaboSemanal, HorarioExamenDetalleAlumno, Aula, Bloque, \
    Administrativo, SedeVirtual, NivelMalla, Paralelo, LaboratorioVirtual, TipoAula, CodigoEvaluacion, \
    TemaTitulacionPosgradoMatricula
from sga.templatetags.sga_extras import encrypt


class ProfesorPersonaSerializer(PersonaBaseSerializer):

    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class PersonaSerializerId(PersonaBaseSerializer):
    class Meta:
        model = Persona
        fields = ('id',)

class ProfesorPersonaSerializer2(PersonaBaseSerializer):
    nombre_completo = serializers.SerializerMethodField()
    foto_perfil = serializers.SerializerMethodField()

    class Meta:
        model = Persona
        fields = ('nombre_completo','foto_perfil')

class MatriAsignaturaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model = Asignatura
        # fields = "__all__"
        fields = ('nombre', 'idm')
        #exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class ModeloEvaluativoSerializer(Helper_ModelSerializer):

    class Meta:
        model = ModeloEvaluativo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class DetalleModeloEvaluativoSerializer(Helper_ModelSerializer):
    parcialconfiguraexamen = serializers.SerializerMethodField()
    modelo = ModeloEvaluativoSerializer()

    class Meta:
        model = DetalleModeloEvaluativo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_parcialconfiguraexamen(self, obj):
        return obj.parcialconfiguraexamen()


class ProfesorSerializer(Helper_ModelSerializer):
    persona = ProfesorPersonaSerializer()
    idm = serializers.SerializerMethodField()

    class Meta:
        model = Profesor
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id

class ProfesorSerializer2(Helper_ModelSerializer):
    persona = ProfesorPersonaSerializer()
    idm = serializers.SerializerMethodField()

    class Meta:
        model = Profesor
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id

class ProfesorSerializer4(Helper_ModelSerializer):
    persona = ProfesorPersonaSerializer2()
    idm = serializers.SerializerMethodField()

    class Meta:
        model = Profesor
        fields =('persona','idm')

    def get_idm(self, obj):
        return obj.id

class EvaluacionGenericaSerializer(Helper_ModelSerializer):
    detallemodeloevaluativo = DetalleModeloEvaluativoSerializer()

    class Meta:
        model = EvaluacionGenerica
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class HorarioExamenDetalleSerializer(Helper_ModelSerializer):
    tipogrupo_display = serializers.SerializerMethodField()

    class Meta:
        model = HorarioExamenDetalle
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_tipogrupo_display(self, obj):
        return obj.get_tipogrupo_display()


class HorarioExamenSerializer(Helper_ModelSerializer):
    detallehoraexamen = serializers.SerializerMethodField()
    disponibleexamen = serializers.SerializerMethodField()
    detallemodelo = DetalleModeloEvaluativoSerializer()

    class Meta:
        model = HorarioExamen
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_detallehoraexamen(self, obj):
        detalle = obj.detallehoraexamen()
        return HorarioExamenDetalleSerializer(detalle, many=True).data if detalle else None

    def get_disponibleexamen(self, obj):
        return obj.disponibleexamen()


class SilaboSerializar(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    estado_planificacion_clases = serializers.SerializerMethodField()
    numero_guia_practicas = serializers.SerializerMethodField()
    class Meta:
        model = Silabo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id

    def get_estado_planificacion_clases(self, obj):
        return obj.estado_planificacion_clases()

    def get_numero_guia_practicas(self, obj):
        return obj.numero_guia_practicas()


class SilaboEstadoSerializar(Helper_ModelSerializer):
    class Meta:
        model = AprobarSilabo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ArchivoSerializer(Helper_ModelSerializer):
    download_link = serializers.SerializerMethodField()

    class Meta:
        model = Archivo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_download_link(self, obj):
        return obj.download_link()

class ProfesorMateriaSerializer(Helper_ModelSerializer):
    class Meta:
        model = ProfesorMateria
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class ProfesorSerializerEXAMEN(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    class Meta:
        model = Profesor
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']
    def get_idm(self, obj):
        return obj.id


class ProfesorMateriaSerializerEXAMEN(Helper_ModelSerializer):
    profesor = ProfesorSerializerEXAMEN()
    class Meta:
        model = ProfesorMateria
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriculaNivelMallaSerializer(Helper_ModelSerializer):

    class Meta:
        model = NivelMalla
        # fields = "__all__"
        fields = ('nombre',)
        #exclude = ['usuario_creacion', 'usuario_modificacion']

class MallaSerializer(Helper_ModelSerializer):

    class Meta:
        model = Malla
        fields = "__all__"
        # fields = ('modalidad')
        #exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriculaAsignaturaMallaSerializar(Helper_ModelSerializer):
    asignatura = MatriAsignaturaSerializer()
    nivelmalla = MatriculaNivelMallaSerializer()
    malla = MallaSerializer()

    class Meta:
        model = AsignaturaMalla
        # fields = "__all__"
        fields = ('asignatura','nivelmalla', 'malla')
        #exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriculaParaleloSerializar(Helper_ModelSerializer):

    class Meta:
        model = Paralelo
        fields = ('nombre','display')
        #exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriculaMateriaSerializer(Helper_ModelSerializer):
    asignatura = MatriAsignaturaSerializer()
    asignaturamalla = MatriculaAsignaturaMallaSerializar()
    #modeloevaluativo = ModeloEvaluativoSerializer()
    profesor = serializers.SerializerMethodField()
    nombre_mostrar = serializers.SerializerMethodField()
    nombre_mostrar_sin_profesor = serializers.SerializerMethodField()
    silabo = serializers.SerializerMethodField()
    horarioexamen = serializers.SerializerMethodField()
    syllabusword = serializers.SerializerMethodField()
    totalpreguntasalumnos = serializers.SerializerMethodField()
    totalcomunicacionmasiva = serializers.SerializerMethodField()
    #profesor_principal_sinautor = serializers.SerializerMethodField()
    #profesores_materia = serializers.SerializerMethodField()
    paralelomateria = MatriculaParaleloSerializar()

    class Meta:
        model = Materia
        #fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion', 'fecha_modificacion' , 'fecha_creacion', 'status',
                   'identificacion', 'alias', 'paralelo',
                   'rectora', 'cerrado', 'fechacierre',
                   'tutoria', 'practicas', 'grado' , 'cupo', 'usaperiodoevaluacion', 'diasactivacion',
                   'usaperiodocalificaciones' , 'diasactivacioncalificaciones', 'horassemanales', 'creditos',
                   'validacreditos', 'validapromedio', 'laboratorio', 'parcial', 'seevalua',
                   'inicioeval', 'fineval', 'cupoadicional', 'totalmatriculadocupoadicional',
                   'codigosakai', 'esintroductoria', 'inicioevalauto', 'finevalauto', 'modelotarjeta',
                   'namehtml', 'urlhtml' , 'actualizarhtml', 'inglesepunemi' , 'visiblehorario',
                   'validaconflictohorarioalu', 'fechainiciomatriculacionposgrado' , 'fechafinmatriculacionposgrado'
                   ,'asignaturaold', 'carrerascomunes','fechafinasistencias',
                   'modeloevaluativo']

    def get_profesor(self, obj):
        ePeriodoMatriculas = obj.nivel.periodo.periodomatricula_set.filter(status=True)
        profesor = obj.profesor_principal()
        if ePeriodoMatriculas.values("id").exists():
            ePeriodoMatricula = ePeriodoMatriculas[0]
            if not ePeriodoMatricula.ver_profesor_materia:
                profesor = None
        return ProfesorSerializer4(profesor).data if profesor else None

    def get_profesores_materia(self, obj):
        ePeriodoMatriculas = obj.nivel.periodo.periodomatricula_set.filter(status=True)
        ePeriodoMatriculas = obj.nivel.periodo.periodomatricula_set.filter(status=True)
        profesores = obj.profesores_materia()
        if ePeriodoMatriculas.values("id").exists():
            ePeriodoMatricula = ePeriodoMatriculas[0]
            if not ePeriodoMatricula.ver_profesor_materia:
                profesores = None
        return ProfesorMateriaSerializerEXAMEN(profesores, many=True).data if profesores else None

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

    def get_nombre_mostrar_sin_profesor(self, obj):
        return obj.nombre_mostrar_sin_profesor()

    def get_silabo(self, obj):
        profesor = obj.profesor_principal()
        silabo = obj.mi_silabo_activo(profesor)
        return SilaboSerializar(silabo).data if silabo else None

    def get_horarioexamen(self, obj):
        # horarioexamen = obj.horarioexamen()
        # return HorarioExamenSerializer(horarioexamen, many=True).data if horarioexamen else None
        return []

    def get_syllabusword(self, obj):
        archi = obj.syllabusword()
        return ArchivoSerializer(archi).data if archi else None

    def get_profesor_principal_sinautor(self, obj):
        archi = obj.profesor_principal_sinautor()
        return ProfesorSerializer2(archi).data if archi else None

    def get_totalpreguntasalumnos(self, obj):
        return obj.totalpreguntasalumnos()

    def get_totalcomunicacionmasiva(self, obj):
        return obj.totalcomunicacionmasiva()


class AsistenciaLeccionSerializer(Helper_ModelSerializer):

    class Meta:
        model = AsistenciaLeccion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MallaSerializer(Helper_ModelSerializer):

    class Meta:
        model = Malla
        # fields = "__all__"
        fields = ('misioncarrera', 'perfilprofesional', 'perfilegreso', 'objetivocarrera', 'modalidad')
        #exclude = ['usuario_creacion', 'usuario_modificacion']


class PeriodoSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model = Periodo
        fields = ('id','idm','urlmoodle', 'clasificacion', 'urlmoodle2','urlmoodleenlinea')
        #exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class NivelSerializer(Helper_ModelSerializer):
    #periodo = PeriodoSerializer()

    class Meta:
        model = Nivel
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class CarreraSerializer(Helper_ModelSerializer):
    mi_coordinacion = serializers.SerializerMethodField()

    class Meta:
        model = Carrera
        fields = "__all__"
        #fields = ('mi_coordinacion')
        #exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_mi_coordinacion(self, obj):
        return obj.mi_coordinacion()

class InscripcionSerializer(Helper_ModelSerializer):
    persona = PersonaSerializerId()
    #carrera = CarreraSerializer()

    class Meta:
        model = Inscripcion
        #fields = ('carrera','fecha')
        fields = ('id','persona','carrera','egresadocderecho')
        #exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriculaSerializer(Helper_ModelSerializer):
    inscripcion = InscripcionSerializer()
    #nivel = NivelSerializer()
    esppl = serializers.SerializerMethodField()
    tiene_matricula_sede_examen = serializers.SerializerMethodField()
    esta_visible_horario_examen = serializers.SerializerMethodField()
    sede_examen = serializers.SerializerMethodField()
    nombre_persona = serializers.SerializerMethodField()
    nombre_carrera = serializers.SerializerMethodField()
    nombre_periodo = serializers.SerializerMethodField()
    tiene_solicitud_de_ingreso_a_titulacion_posgrado = serializers.SerializerMethodField()
    tiene_propuesta_ya_registrada_posgrado = serializers.SerializerMethodField()
    tiene_propuesta_engrupo_y_no_tiene_solicitud = serializers.SerializerMethodField()

    class Meta:
        model = Matricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion','fecha_modificacion','fecha_creacion','status',
                   'pago','iece','becado','becaexterna','beneficiomonetario','tipomatricula',
                   'tipobeca','porcientobeca','montomensual','cantidadmeses','montobeneficio',
                   'observaciones','fecha','fechatope','hora','formalizada','promedionotas',
                   'promedioasistencias','totalhoras','totalcreditos','aprobadofinanzas',
                   'tipobecarecibe','nivelmalla','estado_matricula','retiradomatricula',
                   'paralelo','notificadoadmision','promedionotasvirtual','pasoayuda','aranceldiferido',
                   'actacompromiso','termino','fechatermino','automatriculapregrado','fechaautomatriculapregrado',
                   'automatriculaadmision','fechaautomatriculaadmision'
                   ]

    def get_esppl(self, obj):
        if obj.inscripcion.persona:
            return obj.inscripcion.persona.ppl
        return False

    def get_tiene_matricula_sede_examen(self, obj):
        return MatriculaSedeExamen.objects.values("id").filter(status=True, matricula=obj, detallemodeloevaluativo__alternativa__id__in=[20, 14]).exists()

    def get_esta_visible_horario_examen(self, obj):
        return MateriaAsignada.objects.values("id").filter(matricula=obj, visiblehorarioexamen=True, status=True).exists()

    def get_sede_examen(self,obj):
        return MatriculaSedeExamen.objects.filter(matricula=obj, detallemodeloevaluativo__alternativa__id__in=[20, 14]).first().sede.nombre if self.get_tiene_matricula_sede_examen(obj) else ''

    def get_nombre_persona(self, obj):
        return obj.inscripcion.persona.__str__()

    def get_nombre_carrera(self, obj):
        return obj.inscripcion.carrera.nombre

    def get_nombre_periodo(self, obj):
        return f"{obj.nivel.periodo.numero_cohorte_romano()} - {obj.nivel.periodo.anio}"

    def get_tiene_solicitud_de_ingreso_a_titulacion_posgrado(self,obj):
        return SolicitudIngresoTitulacionPosgrado.objects.filter(status=True,matricula = obj,firmado=True).exists()

    def get_tiene_propuesta_ya_registrada_posgrado(self,obj):
        return TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula= obj ).exists()

    def get_tiene_propuesta_engrupo_y_no_tiene_solicitud(self,obj):
        from datetime import datetime
        hoy = datetime.now()
        fecha_implementacion = datetime.strptime('18-11-2023', '%d-%m-%Y')
        tiene = True
        if hoy > fecha_implementacion:
            eTemaTitulacionPosgradoMatricula = TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula=obj)
            if eTemaTitulacionPosgradoMatricula.exists():
                if eTemaTitulacionPosgradoMatricula.first().cabeceratitulacionposgrado:
                    if not SolicitudIngresoTitulacionPosgrado.objects.filter(status=True, matricula=obj ,firmado =True).exists():
                        if not eTemaTitulacionPosgradoMatricula.exists():
                            tiene = False
                        else:
                            if eTemaTitulacionPosgradoMatricula.first().fecha_creacion < fecha_implementacion:
                                tiene = True
                            else:
                                tiene = False

                else:
                    if not SolicitudIngresoTitulacionPosgrado.objects.filter(status=True, matricula=obj,firmado =True).exists():
                        if not eTemaTitulacionPosgradoMatricula.exists():
                            tiene = False
            else:
                if not SolicitudIngresoTitulacionPosgrado.objects.filter(status=True, matricula=obj,firmado =True).exists():
                    tiene = False
        else:
            tiene = True
        return tiene









class CompaMateriaAsignadaSerializer(Helper_ModelSerializer):
    matricula = MatriculaSerializer()

    class Meta:
        model = MateriaAsignada
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ModeloEvaluativo2Serializer(Helper_ModelSerializer):

    class Meta:
        model = ModeloEvaluativo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class CodigoEvaluacionSerializer(Helper_ModelSerializer):

    class Meta:
        model = CodigoEvaluacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class DetalleModeloEvaluativo2Serializer(Helper_ModelSerializer):
    modelo = ModeloEvaluativo2Serializer()
    # alternativa = CodigoEvaluacionSerializer()

    class Meta:
        model = DetalleModeloEvaluativo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class HorarioExamen2Serializer(Helper_ModelSerializer):
    detallemodelo =DetalleModeloEvaluativo2Serializer()

    class Meta:
        model = HorarioExamen
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class Bloque2Serializer(Helper_ModelSerializer):
    class Meta:
        model = Bloque
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class AulaExamen2Serializer(Helper_ModelSerializer):
    bloque = Bloque2Serializer()
    idm = serializers.SerializerMethodField()
    class Meta:
        model = Aula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']
    def get_idm(self, obj):
        return obj.id

class Persona2Serializer(PersonaBaseSerializer):
    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class Persona3Serializer(PersonaBaseSerializer):
    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class Persona4Serializer(PersonaBaseSerializer):

    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class Persona5Serializer(PersonaBaseSerializer):
    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class Persona6Serializer(PersonaBaseSerializer):
    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class Profesor2Serializer(Helper_ModelSerializer):
    persona = Persona2Serializer()

    class Meta:
        model = Profesor
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ProfesorMateria2Serializer(Helper_ModelSerializer):
    profesor = Persona3Serializer()

    class Meta:
        model = ProfesorMateria
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ProfesorSerializerMateria(Helper_ModelSerializer):
    persona = Persona4Serializer()
    class Meta:
        model = Profesor
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ProfesorSerializer3(Helper_ModelSerializer):
    persona = Persona5Serializer()

    class Meta:
        model = Profesor
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class AdministrativoSerializer(Helper_ModelSerializer):
    persona = Persona6Serializer()
    class Meta:
        model = Administrativo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ProfesorMateriaSerializerHorarioExamenDetalle(Helper_ModelSerializer):
    profesor = Profesor2Serializer()

    class Meta:
        model = ProfesorMateria
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class HorarioExamenDetalle2Serializer(Helper_ModelSerializer):
    profesormateria = ProfesorMateria2Serializer()
    aula = AulaExamen2Serializer()
    horarioexamen = HorarioExamen2Serializer()
    profesormateria = ProfesorMateriaSerializerHorarioExamenDetalle()
    profesor = ProfesorSerializer3()
    administrativo = AdministrativoSerializer()

    class Meta:
        model = HorarioExamenDetalle
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class HorarioExamenDetalleAlumnoSerializer(Helper_ModelSerializer):
    horarioexamendetalle = HorarioExamenDetalle2Serializer()
    disponibleexamen = serializers.SerializerMethodField()
    fecha_actual = serializers.SerializerMethodField()
    hora_actual = serializers.SerializerMethodField()

    class Meta:
        model = HorarioExamenDetalleAlumno
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_disponibleexamen(self, obj):
        # return obj.disponibleexamen()
        return True

    def get_fecha_actual(self, obj):
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d')

    def get_hora_actual(self, obj):
        from datetime import datetime
        return datetime.now().strftime('%H:%M:%S')



class MatriculaMateriaAsignadaSerializer(Helper_ModelSerializer):
    # asistencia_real = serializers.SerializerMethodField()
    materia = MatriculaMateriaSerializer()
    # asistencia_plan = serializers.SerializerMethodField()
    idm = serializers.SerializerMethodField()
    # horarioexamendetallealumno = serializers.SerializerMethodField()
    es_modulo_ingles = serializers.SerializerMethodField()
    # tiene_horarioexamendetallealumno = serializers.SerializerMethodField()
    # tiene_planficacionvirtualexamen = serializers.SerializerMethodField()
    tienesilabo = serializers.SerializerMethodField()

    class Meta:
        model = MateriaAsignada
        #fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion', 'fecha_modificacion' , 'fecha_creacion', 'status',
                   'notafinal','asistenciafinalzoom','cerrado','fechacierre',
                   'matriculas','observaciones','estado','sinasistencia','evaluar', 'fechaevaluar',
                   'fechaasignacion', 'retiramateria', 'notaexonera','cobroperdidagratuidad','retiromanual',
                   'fecharetiromanual','automatricula','importa_nota','casoultimamatricula',
                   'rubro'
                   ]

    # def get_asistencia_real(self, obj):
    #     return obj.asistencia_real()

    # def get_asistencia_plan(self, obj):
    #     return obj.asistencia_plan()

    def get_idm(self, obj):
        return obj.id

    # def get_horarioexamendetallealumno(self, obj):
    #     horario = obj.horarioexamendetallealumno()
    #     return HorarioExamenDetalleAlumnoSerializer(horario, many=True).data if horario else None

    def get_es_modulo_ingles(self, obj):
        eMalla = obj.matricula.inscripcion.mi_malla()
        return obj.materia.asignatura.es_modulo_malla(eMalla)

    # def get_tiene_horarioexamendetallealumno(self, obj):
    #     return obj.tiene_horarioexamendetallealumno()
    #
    # def get_tiene_planficacionvirtualexamen(self, obj):
    #     return obj.tiene_planficacionvirtualexamen()

    def get_tienesilabo(self, obj):
        if obj.materia:
            if obj.materia.silabo_set.values('id').filter(status=True).exists():
                return True
        return False


class LibroKohaProgramaAnaliticoAsignaturaSerializer(Helper_ModelSerializer):
    carrera = CarreraSerializer()

    class Meta:
        model = LibroKohaProgramaAnaliticoAsignatura
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class AsignaturaMallaSerializar(Helper_ModelSerializer):
    nombre_completo = serializers.CharField(read_only=True)

    class Meta:
        model = AsignaturaMalla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_nombre_completo(self, obj):
        return obj.nombre_completo()


class MateriaSilaboSerializar(Helper_ModelSerializer):
    asignaturamalla = AsignaturaMallaSerializar()
    nivel = NivelSerializer()
    profesor = serializers.SerializerMethodField()
    tiene_silabo_aprobado = serializers.SerializerMethodField()

    class Meta:
        model = Materia
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_profesor(self, obj):
        profesor = obj.profesor_principal()
        return ProfesorSerializer(profesor).data if profesor else None

    def get_tiene_silabo_aprobado(self, obj):
        profesor = obj.profesor_principal()
        pro = profesor.id
        silabo = obj.tiene_silabo_aprobado(pro)
        return SilaboEstadoSerializar(silabo).data if silabo else None


class Silabo_2_Serializar(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    estado_planificacion_clases = serializers.SerializerMethodField()
    materia = MateriaSilaboSerializar()
    tiene_aprobaciones = serializers.SerializerMethodField()
    estado_aprobacion = serializers.SerializerMethodField()

    class Meta:
        model = Silabo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id

    def get_estado_planificacion_clases(self, obj):
        return obj.estado_planificacion_clases()

    def get_tiene_aprobaciones(self, obj):
        return obj.tiene_aprobaciones()

    def get_estado_aprobacion(self, obj):
        estado = obj.estado_aprobacion()
        return SilaboEstadoSerializar(estado).data if estado else None


class PlanificacionClaseSilabo_Serializer(Helper_ModelSerializer):

    class Meta:
        model = PlanificacionClaseSilabo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class DetalleSilaboSemanalTema_Serializer(Helper_ModelSerializer):

    class Meta:
        model = DetalleSilaboSemanalTema
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class SilaboSemanal_Serializar(Helper_ModelSerializer):
    silabo = Silabo_2_Serializar()
    cronograma_silabo_semana= serializers.SerializerMethodField()
    cronograma_silabo_n_semana= serializers.SerializerMethodField()

    class Meta:
        model = SilaboSemanal
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_cronograma_silabo_semana(self, obj):
        planificacion = obj.silabo.cronograma_silabo(obj.fechainiciosemana, obj.fechafinciosemana)
        if planificacion:
            return PlanificacionClaseSilabo_Serializer(planificacion[0]).data
        return None

    def get_cronograma_silabo_n_semana(self, obj):
        planificacion = obj.silabo.cronograma_silabo_n_semana(obj.fechainiciosemana, obj.fechafinciosemana)
        if planificacion:
            return planificacion
        return None


class GPInstruccionSerializer(Helper_ModelSerializer):
    download_link = serializers.SerializerMethodField()

    class Meta:
        model = GPInstruccion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_download_link(self, obj):
        return obj.download_link()


class GPGuiaPracticaSemanal_Serializar(Helper_ModelSerializer):
    temapractica = DetalleSilaboSemanalTema_Serializer()
    silabosemanal = SilaboSemanal_Serializar()
    id_estado_guiapractica = serializers.SerializerMethodField()
    nombre_estado_guiapractica = serializers.SerializerMethodField()
    mi_instruccion = serializers.SerializerMethodField()

    class Meta:
        model = GPGuiaPracticaSemanal
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_id_estado_guiapractica(self, obj):
        return obj.id_estado_guiapractica()

    def get_nombre_estado_guiapractica(self, obj):
        return obj.nombre_estado_guiapractica()

    def get_mi_instruccion(self, obj):
        instru = obj.mi_instruccion()
        return GPInstruccionSerializer(instru).data if instru else None


class AvComunicacionSerializer(Helper_ModelSerializer):

    class Meta:
        model = AvComunicacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class AvComunicacionSerializer(Helper_ModelSerializer):
    comunicacion_p = serializers.SerializerMethodField()

    class Meta:
        model = AvComunicacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_comunicacion_p(self, obj):
        return mark_safe(obj.comunicado)


class MateriaPreguntaSerializer(Helper_ModelSerializer):
    nombre_mostrar = serializers.SerializerMethodField()
    nombre_mostrar_virtual = serializers.SerializerMethodField()

    class Meta:
        model = Materia
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_nombre_mostrar(self, obj):
        nombre = obj.nombre_mostrar()
        ePeriodoMatriculas = obj.nivel.periodo.periodomatricula_set.filter(status=True)
        if ePeriodoMatriculas.values("id").exists():
            ePeriodoMatricula = ePeriodoMatriculas[0]
            if not ePeriodoMatricula.ver_profesor_materia:
                nombre = obj.nombre_mostrar_sin_profesor()
        return nombre

    def get_nombre_mostrar_virtual(self, obj):
        nombre = obj.nombre_mostrar_virtual()
        ePeriodoMatriculas = obj.nivel.periodo.periodomatricula_set.filter(status=True)
        if ePeriodoMatriculas.values("id").exists():
            ePeriodoMatricula = ePeriodoMatriculas[0]
            if not ePeriodoMatricula.ver_profesor_materia:
                nombre = obj.nombre_mostrar_sin_profesor()
        return nombre


class ProfesorMateriaSerializer(Helper_ModelSerializer):
    materia = MateriaPreguntaSerializer()

    class Meta:
        model = ProfesorMateria
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class AvPreguntaDocenteSerializer(Helper_ModelSerializer):
    profersormateria = ProfesorMateriaSerializer()
    en_uso = serializers.SerializerMethodField()

    class Meta:
        model = AvPreguntaDocente
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_en_uso(self, obj):
        return obj.en_uso()


class TestSilaboSemanalSerializer(Helper_ModelSerializer):

    class Meta:
        model = TestSilaboSemanal
        exclude = ['usuario_creacion', 'usuario_modificacion']


class TareaSilaboSemanalSerializer(Helper_ModelSerializer):

    class Meta:
        model = TareaSilaboSemanal
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ForoSilaboSemanalSerializer(Helper_ModelSerializer):

    class Meta:
        model = ForoSilaboSemanal
        exclude = ['usuario_creacion', 'usuario_modificacion']


class TareaPracticaSilaboSemanalSerializer(Helper_ModelSerializer):

    class Meta:
        model = TareaPracticaSilaboSemanal
        exclude = ['usuario_creacion', 'usuario_modificacion']


class TipoAulaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model = TipoAula
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class BloqueSerializer(Helper_ModelSerializer):
    foto = serializers.SerializerMethodField()
    class Meta:
        model = Bloque
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_foto(self, obj):
        if obj.foto:
            return self.get_media_url(obj.foto.url)
        return None


class LaboratorioVirtualSerializer(Helper_ModelSerializer):
    bloque = BloqueSerializer()
    tipo = TipoAulaSerializer()

    class Meta:
        model = LaboratorioVirtual
        exclude = ['usuario_creacion', 'usuario_modificacion']


class SedeVirtuallSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    imagen = serializers.SerializerMethodField()
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = SedeVirtual
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_fields(self):
        fields = super().get_fields()

        exclude_fields = self.context.get('exclude_fields', [])
        for field in exclude_fields:
            # providing a default prevents a KeyError
            # if the field does not exist
            fields.pop(field, default=None)

        return fields

    def get_imagen(self, obj):
        if obj.foto and obj.foto.url:
            return self.get_media_url(obj.foto.url)
        return None

    def get_imagen_url(self, obj):
        if obj.foto and obj.foto.url:
            return obj.foto.url
        return None

    def get_pk(self, obj):
        return obj.id


class FechaPlanificacionSedeVirtualExamenSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    sede = SedeVirtuallSerializer()
    es_pasado = serializers.SerializerMethodField()

    class Meta:
        model = FechaPlanificacionSedeVirtualExamen
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_fields(self):
        fields = super().get_fields()

        exclude_fields = self.context.get('exclude_fields', [])
        for field in exclude_fields:
            # providing a default prevents a KeyError
            # if the field does not exist
            fields.pop(field, default=None)

        return fields

    def get_pk(self, obj):
        return obj.id

    def get_es_pasado(self, obj):
        from datetime import datetime
        ahora = datetime.now()
        return obj.fecha < ahora.date()


class TurnoPlanificacionSedeVirtualExamenSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    fechaplanificacion = FechaPlanificacionSedeVirtualExamenSerializer()
    es_pasado = serializers.SerializerMethodField()

    class Meta:
        model = TurnoPlanificacionSedeVirtualExamen
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_fields(self):
        fields = super().get_fields()

        exclude_fields = self.context.get('exclude_fields', [])
        for field in exclude_fields:
            # providing a default prevents a KeyError
            # if the field does not exist
            fields.pop(field, default=None)

        return fields

    def get_pk(self, obj):
        return obj.id

    def get_es_pasado(self, obj):
        from datetime import datetime
        ahora = datetime.now()
        if obj.fechaplanificacion.fecha < ahora.date():
            return True
        else:
            if obj.fechaplanificacion.fecha == ahora.date():
                # horainicio = obj.horainicio
                horafin = obj.horafin
                return not ahora.time() <= horafin
            return False


class AulaPlanificacionSedeVirtualExamenSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    turnoplanificacion= TurnoPlanificacionSedeVirtualExamenSerializer()
    aula = LaboratorioVirtualSerializer()
    responsable = Persona4Serializer()

    class Meta:
        model = AulaPlanificacionSedeVirtualExamen
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class MateriaAsignadaPlanificacionSedeVirtualExamenSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = MateriaAsignada
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk



class PlanificacionSedeSerializer(Helper_ModelSerializer):
    aulaplanificacion = AulaPlanificacionSedeVirtualExamenSerializer()
    materiaasignada = MateriaAsignadaPlanificacionSedeVirtualExamenSerializer()
    detallemodeloevaluativo = DetalleModeloEvaluativo2Serializer()
    puede_copiar_clave = serializers.SerializerMethodField()
    url_qr = serializers.SerializerMethodField()
    url_profesor = serializers.SerializerMethodField()
    puede_ir_meet = serializers.SerializerMethodField()

    class Meta:
        model = MateriaAsignadaPlanificacionSedeVirtualExamen
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_puede_copiar_clave(self, obj):
        # return obj.materiaasignada.matricula.inscripcion.modalidad_id == 3 and obj.habilitadoexamen and obj.password
        es_virtual = obj.aulaplanificacion.aula.tipo_id == 5
        habilitadoexamen = obj.habilitadoexamen
        password = obj.password
        return es_virtual and habilitadoexamen and password

    def get_url_qr(self, obj):
        return self.get_media_url(obj.url_qr) if obj.url_qr else None

    def get_url_profesor(self, obj):
        profesor = Profesor.objects.filter(status=True, persona=obj.aulaplanificacion.responsable).first()
        return profesor.urlzoom if profesor else ''

    def get_puede_ir_meet(self, obj):
        ahora = datetime.now()
        fecha = obj.aulaplanificacion.turnoplanificacion.fechaplanificacion.fecha
        inicio = obj.aulaplanificacion.turnoplanificacion.horainicio
        fin = obj.aulaplanificacion.turnoplanificacion.horafin
        fechainicio = datetime.combine(fecha, inicio)
        fechainicio = fechainicio - timedelta(minutes=15)
        fechafin = datetime.combine(fecha, fin)
        return fechainicio <= ahora <= fechafin


class AuxMatriculaMateriaAsignadaSerializer(Helper_ModelSerializer):
    materia = MatriculaMateriaSerializer()
    idm = serializers.SerializerMethodField()
    es_modulo_ingles = serializers.SerializerMethodField()
    horarioexamendetallealumno = serializers.SerializerMethodField()
    disertaciones = serializers.SerializerMethodField()
    planificacionsede = serializers.SerializerMethodField()

    class Meta:
        model = MateriaAsignada
        #fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id

    def get_es_modulo_ingles(self, obj):
        eMalla = obj.matricula.inscripcion.mi_malla()
        return obj.materia.asignatura.es_modulo_malla(eMalla)

    def get_horarioexamendetallealumno(self, obj):
        eMateriaAsignada = obj
        fecha_actual = datetime.now().date()
        eHorarioExamenDetalleAlumnos = HorarioExamenDetalleAlumno.objects.filter(materiaasignada=eMateriaAsignada, status=True)
        return HorarioExamenDetalleAlumnoSerializer(eHorarioExamenDetalleAlumnos, many=True).data if eHorarioExamenDetalleAlumnos.values("id").exists() else []

    def get_disertaciones(self, obj):
        eMateriaAsignada = obj
        eDisertaciones = DisertacionMateriaAsignadaPlanificacion.objects.filter(materiaasignada=eMateriaAsignada, status=True)
        return DisertacionMateriaAsignadaPlanificacionSerializer(eDisertaciones, many=True).data if eDisertaciones.values("id").exists() else []

    def get_planificacionsede(self, obj):
        eMateriaAsignada = obj
        ePlanificacionSede = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(materiaasignada=eMateriaAsignada, status=True)
        return PlanificacionSedeSerializer(ePlanificacionSede, many=True).data if ePlanificacionSede.values("id").exists() else []


class MatriculaSedeExamenSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    download_archivoidentidad = serializers.SerializerMethodField()
    download_archivofoto = serializers.SerializerMethodField()
    tiene_fase_1 = serializers.SerializerMethodField()
    tiene_fase_2 = serializers.SerializerMethodField()
    tiene_paso_1 = serializers.SerializerMethodField()
    tiene_paso_2 = serializers.SerializerMethodField()
    tiene_materia_codigo_qr = serializers.SerializerMethodField()
    terminos_examenes = serializers.SerializerMethodField()
    urltermino = serializers.SerializerMethodField()

    class Meta:
        model = MatriculaSedeExamen
        #fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id

    def get_download_archivoidentidad(self, obj):
        if obj.archivoidentidad:
            archivoidentidad = obj.archivoidentidad
            return self.get_media_url(archivoidentidad.url) if archivoidentidad else None
        ePersonaDocumentoPersonal = obj.matricula.inscripcion.persona.documentos_personales()
        if ePersonaDocumentoPersonal:
            return self.get_media_url(ePersonaDocumentoPersonal.cedula.url) if ePersonaDocumentoPersonal.cedula else None
        return None

    def get_download_archivofoto(self, obj):
        if obj.archivofoto:
            archivofoto = obj.archivofoto
            return self.get_media_url(archivofoto.url) if archivofoto else None
        if obj.matricula.inscripcion.persona.tiene_foto():
            return self.get_media_url(obj.matricula.inscripcion.persona.foto().foto.url)
        return None

    def get_tiene_fase_1(self, obj):
        tiene_archivoidentidad = False
        if obj.archivoidentidad:
            tiene_archivoidentidad = True if obj.archivoidentidad.url else False
        tiene_archivofoto = False
        if obj.archivofoto:
            tiene_archivofoto = True if obj.archivofoto.url else False
        return tiene_archivoidentidad is True and tiene_archivofoto is True

    def get_tiene_paso_1(self, obj):
        tiene_archivoidentidad = False
        if obj.archivoidentidad:
            tiene_archivoidentidad = True if obj.archivoidentidad.url else False
        return tiene_archivoidentidad

    def get_tiene_paso_2(self, obj):
        tiene_archivofoto = False
        if obj.archivofoto:
            tiene_archivofoto = True if obj.archivofoto.url else False
        return tiene_archivofoto

    def get_tiene_fase_2(self, obj):
        tiene_fase_aceptada = False
        if obj.fechaaceptotermino:
            tiene_fase_aceptada = True
        return tiene_fase_aceptada

    def get_terminos_examenes(self, obj):
        es_admision = obj.matricula.inscripcion.es_admision()
        es_pregrado = obj.matricula.inscripcion.es_pregrado()
        if es_admision or es_pregrado:
            if ePeriodoMatricula := obj.matricula.nivel.periodo.periodomatricula_set.filter(status=True, mostrar_terminos_examenes=True).first():
                return {'view': True,
                        'text': ePeriodoMatricula.terminos_examenes if es_pregrado else ePeriodoMatricula.terminos_nivelacion}
        return {'view': False,
                'text': None}

    def get_urltermino(self, obj):
        return self.get_media_url(obj.urltermino) if obj.urltermino else None

    def get_tiene_materia_codigo_qr(self, obj):
        return MateriaAsignadaPlanificacionSedeVirtualExamen.objects.values("id").filter(materiaasignada__matricula=obj.matricula, utilizar_qr=True, materiaasignada__visiblehorarioexamen=True).exists()


class DisertacionFechaPlanificacionSerializer(Helper_ModelSerializer):
    sede = SedeVirtuallSerializer()

    class Meta:
        model = DisertacionFechaPlanificacion
        #fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class DisertacionTurnoPlanificacionSerializer(Helper_ModelSerializer):
    fechaplanificacion = DisertacionFechaPlanificacionSerializer()

    class Meta:
        model = DisertacionTurnoPlanificacion
        #fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class DisertacionAulaPlanificacionSerializer(Helper_ModelSerializer):
    turnoplanificacion = DisertacionTurnoPlanificacionSerializer()
    aula = LaboratorioVirtualSerializer()

    class Meta:
        model = DisertacionAulaPlanificacion
        #fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class DisertacionGrupoPlanificacionSerializer(Helper_ModelSerializer):
    responsable = Persona4Serializer()
    detallemodeloevaluativo = DetalleModeloEvaluativo2Serializer()
    aulaplanificacion = DisertacionAulaPlanificacionSerializer()
    link_meet = serializers.SerializerMethodField()

    class Meta:
        model = DisertacionGrupoPlanificacion
        #fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_link_meet(self, obj):
        link = None
        if (eProfesor := obj.responsable.profesor()) is not None:
            link = eProfesor.urlzoom if eProfesor.urlzoom else None
        return link


class DisertacionMateriaAsignadaPlanificacionSerializer(Helper_ModelSerializer):
    grupoplanificacion = DisertacionGrupoPlanificacionSerializer()
    puede_ingresar = serializers.SerializerMethodField()

    class Meta:
        model = DisertacionMateriaAsignadaPlanificacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_puede_ingresar(self, obj):
        hoy = datetime.now()
        fecha = obj.grupoplanificacion.aulaplanificacion.turnoplanificacion.fechaplanificacion.fecha
        return hoy.date() == fecha

