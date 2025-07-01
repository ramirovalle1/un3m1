from datetime import datetime

from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from django.utils.safestring import mark_safe

from api.serializers.base.modalidad import BaseModalidadSerializer
from api.serializers.base.persona import PersonaBaseSerializer
from rest_framework import serializers

from posgrado.models import HistorialSolicitudProrrogaIngresoTemaMatricula, SolicitudProrrogaIngresoTemaMatricula, \
    Revision, Informe, SeccionInforme, SeccionInformePregunta, Pregunta, SeccionRevision, PreguntaRevision, \
    SolicitudIngresoTitulacionPosgrado, MecanismoDocumentosTutoriaPosgrado, EncuestaTitulacionPosgrado, \
    SedeEncuestaTitulacionPosgrado, JornadaSedeEncuestaTitulacionPosgrado, RespuestaSedeInscripcionEncuesta, \
    InscripcionEncuestaTitulacionPosgrado
from sagest.models import Publicacion
from sga.models import Matricula, Nivel, Periodo, MateriaAsignada, Materia, Asignatura, Profesor, Persona, \
    ModeloEvaluativo, DetalleModeloEvaluativo, AsistenciaLeccion, EvaluacionGenerica, MatriculaGrupoSocioEconomico, \
    Malla, Inscripcion, Carrera, Silabo, HorarioExamen, HorarioExamenDetalle, LibroKohaProgramaAnaliticoAsignatura, \
    AsignaturaMalla, AprobarSilabo, GPGuiaPracticaSemanal, SilaboSemanal, DetalleSilaboSemanalTema, GPInstruccion, \
    Archivo, PlanificacionClaseSilabo, AvComunicacion, AvPreguntaDocente, ProfesorMateria, \
    TemaTitulacionPosgradoMatricula, \
    PropuestaSubLineaInvestigacion, TemaTitulacionPosgradoMatriculaHistorial, MecanismoTitulacionPosgrado, \
    PropuestaLineaInvestigacion, RubricaTitulacionPosgrado, ConfiguracionTitulacionPosgrado, \
    TemaTitulacionPosgradoMatriculaCabecera, EtapaTemaTitulacionPosgrado, TutoriasTemaTitulacionPosgradoProfesor, \
    HistorialFirmaActaAprobacionComplexivo, CalificacionTitulacionPosgrado, TribunalTemaTitulacionPosgradoMatricula, \
    FotoPersona, TemaTitulacionPosgradoProfesor, Titulacion, Titulo, AreaTitulo, Pais, Provincia, Canton, Parroquia, \
    InstitucionEducacionSuperior, Colegio, FinanciamientoBeca, Capacitacion, TipoCertificacion, TipoParticipacion, \
    ContextoCapacitacion, DetalleContextoCapacitacion, TipoCapacitacion, AreaConocimientoTitulacion, \
    SubAreaConocimientoTitulacion, SubAreaEspecificaConocimientoTitulacion, SolicitudTutorTemaHistorial, Modalidad, \
    NivelMalla, EjeFormativo, MONTH_NAMES, InscripcionMalla, RevisionTutoriasTemaTitulacionPosgradoProfesor, \
    RevisionPropuestaComplexivoPosgrado, ArchivoRevisionPropuestaComplexivoPosgrado, DetalleGrupoTitulacionPostgrado, \
    GrupoTitulacionPostgrado, ModeloEvaluativoPosgrado, TemaTitulacionPosArchivoFinal, ProgramaEtapaTutoriaPosgrado, \
    ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor, MecanismoTitulacionPosgradoMalla, ItinerarioMallaEspecilidad


class ModalidadSerializer(BaseModalidadSerializer):
    class Meta:
        model = Modalidad
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class FotoPersonaSerializer(Helper_ModelSerializer):
    class Meta:
        model = FotoPersona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class PublicacionSerializer(Helper_ModelSerializer):
    class Meta:
        model = Publicacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class PersonaSerializer(PersonaBaseSerializer):
    obtenerfoto = serializers.SerializerMethodField()
    miformacionacademica = serializers.SerializerMethodField()
    miscapacitaciones = serializers.SerializerMethodField()
    mispublicaciones = serializers.SerializerMethodField()

    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_obtenerfoto(self, obj):
        foto_persona = None
        if obj.fotopersona_set.values("id").exists():
            foto_persona = obj.fotopersona_set.all()[0]
        return FotoPersonaSerializer(foto_persona).data if foto_persona else False

    def get_miformacionacademica(self, obj):
        miformacion = obj.titulacion_set.filter(status=True).order_by('-fechaobtencion')
        return TitulacionSerializer(miformacion, many=True).data if miformacion else []

    def get_miscapacitaciones(self, obj):
        miscapacitaciones = obj.capacitacion_set.filter(status=True)
        return CapacitacionSerializer(miscapacitaciones, many=True).data if miscapacitaciones else []

    def get_mispublicaciones(self, obj):
        mispublicaciones = obj.publicacion_set.filter(status=True)
        return PublicacionSerializer(mispublicaciones, many=True).data if mispublicaciones else []


class TituloSerializer(Helper_ModelSerializer):
    class Meta:
        model = Titulo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class AreaTituloSerializer(Helper_ModelSerializer):
    class Meta:
        model = AreaTitulo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class InstitucionEducacionSuperiorSerializer(Helper_ModelSerializer):
    class Meta:
        model = InstitucionEducacionSuperior
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ColegioSerializer(Helper_ModelSerializer):
    class Meta:
        model = Colegio
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class FinanciamientoBecaSerializer(Helper_ModelSerializer):
    class Meta:
        model = FinanciamientoBeca
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class PaisSerializer(Helper_ModelSerializer):
    class Meta:
        model = Pais
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ParroquiaSerializer(Helper_ModelSerializer):
    class Meta:
        model = Parroquia
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ProvinciaSerializer(Helper_ModelSerializer):
    class Meta:
        model = Provincia
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class CantonSerializer(Helper_ModelSerializer):
    class Meta:
        model = Canton
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class TitulacionSerializer(Helper_ModelSerializer):
    titulo = TituloSerializer()
    areatitulo = AreaTituloSerializer()
    institucion = InstitucionEducacionSuperiorSerializer()
    pais = PaisSerializer()
    provincia = ProvinciaSerializer()
    canton = CantonSerializer()
    parroquia = ParroquiaSerializer()
    colegio = ColegioSerializer()

    class Meta:
        model = Titulacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class TipoCertificacionSerializer(Helper_ModelSerializer):
    class Meta:
        model = TipoCertificacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class TipoParticipacionSerializer(Helper_ModelSerializer):
    class Meta:
        model = TipoParticipacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class TipoCapacitacionSerializer(Helper_ModelSerializer):
    class Meta:
        model = TipoCapacitacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ContextoCapacitacionSerializer(Helper_ModelSerializer):
    class Meta:
        model = ContextoCapacitacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class DetalleContextoCapacitacionSerializer(Helper_ModelSerializer):
    class Meta:
        model = DetalleContextoCapacitacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class AreaConocimientoTitulacionSerializer(Helper_ModelSerializer):
    class Meta:
        model = AreaConocimientoTitulacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class SubAreaConocimientoTitulacionSerializer(Helper_ModelSerializer):
    class Meta:
        model = SubAreaConocimientoTitulacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class SubAreaEspecificaConocimientoTitulacionSerializer(Helper_ModelSerializer):
    class Meta:
        model = SubAreaEspecificaConocimientoTitulacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class CapacitacionSerializer(Helper_ModelSerializer):
    tipocertificacion = TipoParticipacionSerializer()
    tipoparticipacion = TipoParticipacionSerializer()
    tipocapacitacion = TipoCapacitacionSerializer()
    contextocapacitacion = ContextoCapacitacionSerializer()
    detallecontextocapacitacion = DetalleContextoCapacitacionSerializer()
    areaconocimiento = AreaConocimientoTitulacionSerializer()
    subareaconocimiento = SubAreaConocimientoTitulacionSerializer()
    subareaespecificaconocimiento = SubAreaEspecificaConocimientoTitulacionSerializer()
    pais = PaisSerializer()
    provincia = ProvinciaSerializer()
    canton = CantonSerializer()
    parroquia = ParroquiaSerializer()

    class Meta:
        model = Capacitacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class PeriodoSerializer(Helper_ModelSerializer):
    class Meta:
        model = Periodo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class CarreraSerializer(Helper_ModelSerializer):
    class Meta:
        model = Carrera
        exclude = ['usuario_creacion', 'usuario_modificacion']


class EjeFormativoSerializer(Helper_ModelSerializer):
    class Meta:
        model = EjeFormativo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NivelMallaSerializer(Helper_ModelSerializer):
    class Meta:
        model = NivelMalla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MallaSerializer(Helper_ModelSerializer):
    carrera = CarreraSerializer()
    modalidad = ModalidadSerializer()
    niveles = serializers.SerializerMethodField()
    ejesformativos = serializers.SerializerMethodField()
    fecha_display = serializers.SerializerMethodField()

    class Meta:
        model = Malla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_niveles(self, obj):
        niveles = obj.niveles_malla()
        if niveles.values("id").exists():
            return NivelMallaSerializer(niveles, many=True).data
        return []

    def get_ejesformativos(self, obj):
        ejes = EjeFormativo.objects.filter(status=True, id__in=AsignaturaMalla.objects.values_list('ejeformativo_id',
                                                                                                   flat=True).filter(
            malla=obj, status=True, vigente=True).distinct()).order_by('nombre')
        return EjeFormativoSerializer(ejes, many=True).data if ejes.values("id").exists() else []

    def get_fecha_display(self, obj):
        return u"%s %s" % (MONTH_NAMES[obj.inicio.month - 1], str(obj.inicio.year))


class InscripcionSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    nombre_completo = serializers.SerializerMethodField()
    tipo_documento = serializers.SerializerMethodField()
    documento = serializers.SerializerMethodField()
    foto = serializers.SerializerMethodField()
    tiene_foto = serializers.SerializerMethodField()
    ciudad = serializers.SerializerMethodField()
    direccion_corta = serializers.SerializerMethodField()
    tiene_otro_titulo = serializers.SerializerMethodField()
    es_mujer = serializers.SerializerMethodField()
    es_hombre = serializers.SerializerMethodField()
    lista_emails = serializers.SerializerMethodField()
    carrera = serializers.SerializerMethodField()
    nivel = serializers.SerializerMethodField()

    # inscripcion = InscripcionSerializer()

    class Meta:
        model = Inscripcion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id

    def get_nombre_completo(self, obj):
        return obj.persona.nombre_completo()

    def get_documento(self, obj):
        return obj.persona.documento()

    def get_tipo_documento(self, obj):
        return obj.persona.tipo_documento()

    def get_foto(self, obj):
        persona = obj.persona
        if persona.tiene_foto():
            return self.get_media_url(persona.foto().foto.url)
        if persona.sexo and persona.sexo.id == 1:
            foto_perfil = '/static/images/iconos/mujer.png'
        else:
            foto_perfil = '/static/images/iconos/hombre.png'
        return self.get_static_url(foto_perfil)

    def get_tiene_foto(self, obj):
        return obj.persona.tiene_foto()

    def get_ciudad(self, obj):
        persona = obj.persona
        return persona.canton.nombre if persona.canton else None

    def get_direccion_corta(self, obj):
        persona = obj.persona
        return persona.direccion_corta()

    def get_tiene_otro_titulo(self, obj):
        persona = obj.persona
        return persona.tiene_otro_titulo()

    def get_es_mujer(self, obj):
        persona = obj.persona
        return persona.es_mujer()

    def get_es_hombre(self, obj):
        persona = obj.persona
        return persona.es_hombre()

    def get_lista_emails(self, obj):
        persona = obj.persona
        return persona.lista_emails_2()

    def get_carrera(self, obj):
        return obj.carrera.nombre

    def get_nivel(self, obj):
        return obj.mi_nivel().nivel.nombre if obj.mi_nivel().nivel else ''


class InscripcionMallaSerializer(Helper_ModelSerializer):
    inscripcion = InscripcionSerializer()
    malla = MallaSerializer()

    class Meta:
        model = InscripcionMalla
        exclude = ['usuario_creacion', 'usuario_modificacion']


class EtapaTemaTitulacionPosgradoSerializer(Helper_ModelSerializer):
    obtener_id = serializers.SerializerMethodField()

    class Meta:
        model = EtapaTemaTitulacionPosgrado
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_obtener_id(self, obj):
        return obj.pk


class ConfiguracionTitulacionPosgradoSerializer(Helper_ModelSerializer):
    periodo = PeriodoSerializer()
    carrera = CarreraSerializer()
    obtenerid = serializers.SerializerMethodField()

    class Meta:
        model = ConfiguracionTitulacionPosgrado
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_obtenerid(self, obj):
        return obj.pk


class ProgramaEtapaTutoriaPosgradoSerializer(Helper_ModelSerializer):
    etapatutoria = EtapaTemaTitulacionPosgradoSerializer()
    convocatoria = ConfiguracionTitulacionPosgradoSerializer()
    obtener_id = serializers.SerializerMethodField()

    class Meta:
        model = ProgramaEtapaTutoriaPosgrado
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_obtener_id(self, obj):
        return obj.pk


class MatriculaSerializer(Helper_ModelSerializer):
    obtenerid = serializers.SerializerMethodField()
    nombre_persona = serializers.SerializerMethodField()
    nombre_carrera = serializers.SerializerMethodField()
    nombre_periodo = serializers.SerializerMethodField()

    def get_obtenerid(self, obj):
        return obj.pk

    def get_nombre_persona(self, obj):
        return obj.inscripcion.persona.__str__()

    def get_nombre_carrera(self, obj):
        return obj.inscripcion.carrera.nombre

    def get_nombre_periodo(self, obj):
        return f"{obj.nivel.periodo.numero_cohorte_romano()} - {obj.nivel.periodo.anio}"

    class Meta:
        model = Matricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class PropuestaLineaInvestigacionSerializer(Helper_ModelSerializer):
    obtenerid = serializers.SerializerMethodField()

    def get_obtenerid(self, obj):
        return obj.pk

    class Meta:
        model = PropuestaLineaInvestigacion
        exclude = ['usuario_creacion', 'usuario_modificacion']


class PropuestaSubLineaInvestigacionSerializer(Helper_ModelSerializer):
    linea = PropuestaLineaInvestigacionSerializer()
    obtenerid = serializers.SerializerMethodField()

    class Meta:
        model = PropuestaSubLineaInvestigacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_obtenerid(self, obj):
        return obj.pk


class MecanismoTitulacionPosgradoSerializer(Helper_ModelSerializer):
    obtenerid = serializers.SerializerMethodField()
    mecanismo = serializers.SerializerMethodField()

    class Meta:
        model = MecanismoTitulacionPosgrado
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_obtenerid(self, obj):
        return obj.pk

    def get_mecanismo(self, obj):
        return obj.get_mecanismo_posgrado()

    def to_representation(self, obj):
        data = super().to_representation(obj)
        if obj.id == 15:
            data['display'] = obj.get_mecanismo_posgrado()
        return data


class MecanismoTitulacionPosgradoMallaSerializer(Helper_ModelSerializer):
    idmecanismomalla = serializers.SerializerMethodField()
    obtenerid = serializers.SerializerMethodField()
    mecanismotitulacionposgrado = MecanismoTitulacionPosgradoSerializer()
    display = serializers.SerializerMethodField()

    class Meta:
        model = MecanismoTitulacionPosgradoMalla
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idmecanismomalla(self, obj):
        return obj.pk

    def get_obtenerid(self, obj):
        return obj.mecanismotitulacionposgrado.pk

    def get_mecanismo(self, obj):
        return obj.mecanismotitulacionposgrado.get_mecanismo_posgrado()

    def get_display(self, obj):
        return obj.mecanismotitulacionposgrado.__str__() if obj.mecanismotitulacionposgrado.__str__() else None

    def to_representation(self, obj):
        data = super().to_representation(obj)
        if obj.id == 15:
            data['display'] = obj.mecanismotitulacionposgrado.get_mecanismo_posgrado()
        return data


class RubricaTitulacionPosgradoSerializer(Helper_ModelSerializer):
    class Meta:
        model = RubricaTitulacionPosgrado
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ProfesorSerializer(Helper_ModelSerializer):
    persona = PersonaSerializer()

    class Meta:
        model = Profesor
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class TemaTitulacionPosgradoMatriculaCabeceraSerializar(Helper_ModelSerializer):
    sublinea = PropuestaSubLineaInvestigacionSerializer()
    mecanismotitulacionposgrado = MecanismoTitulacionPosgradoSerializer()
    convocatoria = ConfiguracionTitulacionPosgradoSerializer()
    tutor = ProfesorSerializer()
    #
    tema_correcto = serializers.SerializerMethodField()
    archivofinal = serializers.SerializerMethodField()
    tiene_documentos_tutoria_configurado = serializers.SerializerMethodField()
    documentos_tutoria_configurado = serializers.SerializerMethodField()

    class Meta:
        model = TemaTitulacionPosgradoMatriculaCabecera
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_tema_correcto(self, obj):
        tema = obj.tribunaltematitulacionposgradomatricula_set.filter(status=True)
        return tema[0].subtema if tema else ''

    def get_archivofinal(self, obj):
        archivosubir = obj.tematitulacionposarchivofinal_set.filter(status=True)
        return TemaTitulacionPosArchivoFinalSerializer(archivosubir[0]).data if archivosubir else None

    def get_tiene_documentos_tutoria_configurado(self,obj):
        return obj.mecanismotitulacionposgrado.tiene_documentos_tutoria_configurado(obj.convocatoria_id)

    def get_documentos_tutoria_configurado(self,obj):
        documentos= obj.mecanismotitulacionposgrado.get_documentos_tutoria_configurado(obj.convocatoria_id)
        return MecanismoDocumentosTutoriaPosgradoSerializer(documentos,many=True).data if documentos else []

    def get_respuestas_encuestas(self,obj):
        try:
            obj.get_seleccion_sede_graduacion()
        except Exception as ex:
            pass

class TemaTitulacionPosgradoMatriculaSerializar(Helper_ModelSerializer):
    matricula = MatriculaSerializer()
    sublinea = PropuestaSubLineaInvestigacionSerializer()
    mecanismotitulacionposgrado = MecanismoTitulacionPosgradoSerializer()
    convocatoria = ConfiguracionTitulacionPosgradoSerializer()
    rubrica = RubricaTitulacionPosgradoSerializer()
    cabeceratitulacionposgrado = TemaTitulacionPosgradoMatriculaCabeceraSerializar()
    tutor = ProfesorSerializer()
    # metodos
    estadoaprobacion = serializers.SerializerMethodField()
    tema_correcto = serializers.SerializerMethodField()
    detalletribunal = serializers.SerializerMethodField()
    idmecanismotitulacion = serializers.SerializerMethodField()
    obtener_calificacion_ensayo = serializers.SerializerMethodField()
    obtener_calificacion_total_complexivo = serializers.SerializerMethodField()
    obtener_nota_examen_complexivo = serializers.SerializerMethodField()
    archivofinal = serializers.SerializerMethodField()
    calificacion_completa = serializers.SerializerMethodField()
    cumple_malla_completa_aprobada = serializers.SerializerMethodField()
    tiene_documentos_tutoria_configurado = serializers.SerializerMethodField()
    documentos_tutoria_configurado = serializers.SerializerMethodField()
    archivo_acta_sustentacion = serializers.SerializerMethodField()


    class Meta:
        model = TemaTitulacionPosgradoMatricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_archivo_acta_sustentacion(self, obj):
        return self.get_media_url(
            obj.archivo_acta_sustentacion.url) if obj.archivo_acta_sustentacion and obj.archivo_acta_sustentacion.url else None

    def get_estadoaprobacion(self, obj):
        return obj.estado_aprobacion().estado

    def get_tema_correcto(self, obj):
        t = obj.tribunaltematitulacionposgradomatricula_set.filter(status=True)
        if t:
            return t[0].subtema
        return ''

    def get_idmecanismotitulacion(self, obj):
        return obj.mecanismotitulacionposgrado.id

    def get_detalletribunal(self, obj):
        detalletribunal = obj.tribunaltematitulacionposgradomatricula_set.filter(status=True)
        return TribunalTemaTitulacionPosgradoMatriculaSerializer(detalletribunal,
                                                                 many=True).data if detalletribunal else []

    def get_archivofinal(self, obj):
        archivosubir = obj.tematitulacionposarchivofinal_set.filter(status=True)
        return TemaTitulacionPosArchivoFinalSerializer(archivosubir[0]).data if archivosubir else None

    def get_obtener_calificacion_ensayo(self, obj):
        nota = 0
        if not obj.cabeceratitulacionposgrado:
            if obj.cargo_documento_ensayo():
                if obj.revisionpropuestacomplexivoposgrado_set.filter(status=True).order_by('-id').exists():
                    documento = obj.revisionpropuestacomplexivoposgrado_set.filter(status=True).order_by('-id')[0]
                    if documento.estado == 2:
                        nota = documento.calificacion
        else:
            if obj.cabeceratitulacionposgrado.cargo_documento_ensayo():
                if obj.cabeceratitulacionposgrado.revisionpropuestacomplexivoposgrado_set.filter(status=True).order_by(
                        '-id').exists():
                    documento = obj.cabeceratitulacionposgrado.revisionpropuestacomplexivoposgrado_set.filter(
                        status=True).order_by('-id')[0]
                    if documento.estado == 2:
                        nota = documento.calificacion
        return nota

    def get_obtener_calificacion_total_complexivo(self, obj):
        nota_examen = 0
        nota_ensayo = 0
        if obj.obtener_nota_examen_complexivo():
            if obj.obtener_nota_examen_complexivo().nota:
                nota_examen = obj.obtener_nota_examen_complexivo().nota
        if obj.cabeceratitulacionposgrado:
            if obj.obtener_calificacion_ensayo_pareja():
                nota_ensayo = obj.obtener_calificacion_ensayo_pareja()

        else:
            if obj.obtener_calificacion_ensayo_individual():
                nota_ensayo = obj.obtener_calificacion_ensayo_individual()  #

        return nota_ensayo + nota_examen

    def get_obtener_nota_examen_complexivo(self, obj):
        nota = 0
        if obj.detallegrupotitulacionpostgrado_set.filter(status=True).exists():
            if obj.detallegrupotitulacionpostgrado_set.filter(status=True)[0].nota:
                nota = obj.detallegrupotitulacionpostgrado_set.filter(status=True)[0].nota

        return nota

    def get_calificacion_completa(self, obj):
        detallecalificacion = obj.calificaciontitulacionposgrado_set.filter(status=True).order_by(
            'tipojuradocalificador')
        return True if detallecalificacion and 0 not in detallecalificacion.values_list('puntajerubricas',
                                                                                        flat=True) and False not in detallecalificacion.values_list(
            'confirmacalificacionrubricas', flat=True) else False

    def get_cumple_malla_completa_aprobada(self, obj):
        malla = obj.matricula.inscripcion.malla_inscripcion().malla
        if malla.tiene_itinerario_malla_especialidad():
            idasignaturasmalla = malla.asignaturamalla_set.values_list('id', flat=True).filter(status=True, itinerario__in=[0,obj.matricula.inscripcion.itinerario,None])
        else:
            idasignaturasmalla = malla.asignaturamalla_set.values_list('id', flat=True).filter(status=True)
        cantidadmalla = idasignaturasmalla.count()
        cantidadaprobadas = obj.matricula.inscripcion.recordacademico_set.filter(status=True,asignaturamalla_id__in=idasignaturasmalla, aprobada=True).count()
        return True if cantidadmalla == cantidadaprobadas else False

    def get_tiene_documentos_tutoria_configurado(self,obj):
        return obj.mecanismotitulacionposgrado.tiene_documentos_tutoria_configurado(obj.convocatoria_id)

    def get_documentos_tutoria_configurado(self,obj):
        documentos= obj.mecanismotitulacionposgrado.get_documentos_tutoria_configurado(obj.convocatoria_id)
        return MecanismoDocumentosTutoriaPosgradoSerializer(documentos,many=True).data if documentos else []

class TemaTitulacionPosgradoMatriculaHistorialSerializar(Helper_ModelSerializer):
    tematitulacionposgradomatricula = TemaTitulacionPosgradoMatriculaSerializar()
    persona = serializers.SerializerMethodField()

    class Meta:
        model = TemaTitulacionPosgradoMatriculaHistorial
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_persona(self, obj):
        return obj.persona()


class PreguntaSerializer(Helper_ModelSerializer):
    class Meta:
        model = Pregunta
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class InformeSerializer(Helper_ModelSerializer):
    mecanismotitulacionposgrado = MecanismoTitulacionPosgradoSerializer()

    class Meta:
        model = Informe
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class SeccionInformeSerializer(Helper_ModelSerializer):
    informe = InformeSerializer()
    seccion = EtapaTemaTitulacionPosgradoSerializer()

    class Meta:
        model = SeccionInforme
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class SeccionInformePreguntaSerializer(Helper_ModelSerializer):
    seccion_informe = SeccionInformeSerializer()
    pregunta = PreguntaSerializer()
    tipo_pregunta_display = serializers.SerializerMethodField()

    class Meta:
        model = SeccionInformePregunta
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_tipo_pregunta_display(self, obj):
        return obj.get_tipo_pregunta_display()


class RevisionSerializer(Helper_ModelSerializer):
    estado_display = serializers.SerializerMethodField()
    obtener_secciones = serializers.SerializerMethodField()
    obtener_dictamen = serializers.SerializerMethodField()
    obtener_correccion = serializers.SerializerMethodField()

    class Meta:
        model = Revision
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_estado_display(self, obj):
        return obj.get_estado_display()

    def get_obtener_secciones(self, obj):
        secciones = obj.seccionrevision_set.filter(status=True).order_by('id')
        return SeccionRevisionSerializer(secciones, many=True).data if secciones else []

    def get_obtener_dictamen(self, obj):
        return obj.obtener_dictamen()

    def get_obtener_correccion(self, obj):
        correccion = obj.obtener_correccion_revision_tribunal()
        return TemaTitulacionPosArchivoFinalSerializer(correccion).data if correccion else False


class PreguntaRevisionSerializer(Helper_ModelSerializer):
    seccion_informe_pregunta = SeccionInformePreguntaSerializer()

    class Meta:
        model = PreguntaRevision
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class SeccionRevisionSerializer(Helper_ModelSerializer):
    seccion_informe = SeccionInformeSerializer()
    obtener_preguntas_revision = serializers.SerializerMethodField()

    class Meta:
        model = SeccionRevision
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_obtener_preguntas_revision(self, obj):
        preguntas = obj.preguntarevision_set.filter(status=True)
        return PreguntaRevisionSerializer(preguntas, many=True).data if preguntas else []


class TribunalTemaTitulacionPosgradoMatriculaSerializer(Helper_ModelSerializer):
    class Meta:
        model = TribunalTemaTitulacionPosgradoMatricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class TutoriasTemaTitulacionPosgradoProfesorSerializer(Helper_ModelSerializer):
    tematitulacionposgradomatricula = TemaTitulacionPosgradoMatriculaSerializar()
    tutor = ProfesorSerializer()
    tematitulacionposgradomatriculacabecera = TemaTitulacionPosgradoMatriculaCabeceraSerializar()
    programaetapatutoria = ProgramaEtapaTutoriaPosgradoSerializer()
    revisiones_tutoria = serializers.SerializerMethodField()
    modalidad_display = serializers.SerializerMethodField()

    class Meta:
        model = TutoriasTemaTitulacionPosgradoProfesor
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_revisiones_tutoria(self, obj):
        revisiones = obj.obtener_revisiones_tutoria()
        return RevisionTutoriasTemaTitulacionPosgradoProfesorSerializer(revisiones,
                                                                        many=True).data if revisiones else []

    def get_modalidad_display(self, obj):
        return obj.get_modalidad_display()


class HistorialFirmaActaAprobacionComplexivoSerializer(Helper_ModelSerializer):
    tema = TemaTitulacionPosgradoMatriculaSerializar()
    persona = PersonaSerializer()
    estado_acta_firma = serializers.SerializerMethodField()

    class Meta:
        model = HistorialFirmaActaAprobacionComplexivo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_estado_acta_firma(self, obj):
        return obj.get_estado_acta_firma_display()


class CalificacionTitulacionPosgradoSerializer(Helper_ModelSerializer):
    tematitulacionposgradomatricula = TemaTitulacionPosgradoMatriculaSerializar()
    juradocalificador = ProfesorSerializer()
    tipojuradocalificador = serializers.SerializerMethodField()

    class Meta:
        model = CalificacionTitulacionPosgrado
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_tipojuradocalificador(self, obj):
        return obj.get_tipojuradocalificador_display()


class InscripcionSerializer(Helper_ModelSerializer):
    persona = PersonaSerializer()
    carrera = CarreraSerializer()

    class Meta:
        model = Inscripcion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriculaSerializer(Helper_ModelSerializer):
    inscripcion = InscripcionSerializer()

    class Meta:
        model = Matricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class TemaTitulacionPosgradoProfesorSerializer(Helper_ModelSerializer):
    tematitulacionposgradomatricula = TemaTitulacionPosgradoMatriculaSerializar()
    profesor = ProfesorSerializer()
    tematitulacionposgradomatriculacabecera = TemaTitulacionPosgradoMatriculaCabeceraSerializar()
    obtener_estado_seleccion_estudiante = serializers.SerializerMethodField()

    class Meta:
        model = TemaTitulacionPosgradoProfesor
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_obtener_estado_seleccion_estudiante(self, obj):
        return obj.get_estado_estudiante_display()


class SolicitudTutorTemaHistorialSerializer(Helper_ModelSerializer):
    tematitulacionposgradoprofesor = TemaTitulacionPosgradoProfesorSerializer()
    persona = PersonaSerializer()

    class Meta:
        model = SolicitudTutorTemaHistorial
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesorSerializer(Helper_ModelSerializer):
    tipodisplay = serializers.SerializerMethodField()

    class Meta:
        model = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_tipodisplay(self, obj):
        return obj.get_tipo_display()


class RevisionTutoriasTemaTitulacionPosgradoProfesorSerializer(Helper_ModelSerializer):
    tematitulacionposgradomatricula = TemaTitulacionPosgradoMatriculaSerializar()
    tematitulacionposgradomatriculacabecera = TemaTitulacionPosgradoMatriculaCabeceraSerializar()
    tutoria_avance = serializers.SerializerMethodField()
    correccion = serializers.SerializerMethodField()
    archivos = serializers.SerializerMethodField()
    propuesta = serializers.SerializerMethodField()
    extracto = serializers.SerializerMethodField()
    urkund = serializers.SerializerMethodField()
    correccion = serializers.SerializerMethodField()
    estado_display = serializers.SerializerMethodField()

    class Meta:
        model = RevisionTutoriasTemaTitulacionPosgradoProfesor
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_tutoria_avance(self, obj):
        avance = obj.get_tutoria_avance()
        return ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesorSerializer(avance).data if avance else []

    def get_correccion(self, obj):
        correccion = obj.get_correccion()
        return ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesorSerializer(correccion).data if correccion else []

    def get_archivos(self, obj):
        return ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesorSerializer(obj.get_archivos(),
                                                                               many=True).data if obj.get_archivos() else []

    def get_propuesta(self, obj):
        return ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesorSerializer(
            obj.get_propuesta()).data if obj.get_propuesta() else []

    def get_extracto(self, obj):
        return ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesorSerializer(
            obj.get_extracto()).data if obj.get_extracto() else []

    def get_urkund(self, obj):
        return ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesorSerializer(
            obj.get_urkund()).data if obj.get_urkund() else []

    def get_estado_display(self, obj):
        return obj.get_estado_display()


class RevisionPropuestaComplexivoPosgradoSerializer(Helper_ModelSerializer):
    tematitulacionposgradomatricula = TemaTitulacionPosgradoMatriculaSerializar()
    tematitulacionposgradomatriculacabecera = TemaTitulacionPosgradoMatriculaCabeceraSerializar()
    archivos = serializers.SerializerMethodField()
    propuesta = serializers.SerializerMethodField()
    extracto = serializers.SerializerMethodField()
    urkund = serializers.SerializerMethodField()
    correccion = serializers.SerializerMethodField()

    class Meta:
        model = RevisionPropuestaComplexivoPosgrado
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_archivos(self, obj):
        return ArchivoRevisionPropuestaComplexivoPosgradoSerializer(obj.get_archivos(),
                                                                    many=True).data if obj.get_archivos() else []

    def get_propuesta(self, obj):
        return ArchivoRevisionPropuestaComplexivoPosgradoSerializer(
            obj.get_propuesta()).data if obj.get_propuesta() else []

    def get_extracto(self, obj):
        return ArchivoRevisionPropuestaComplexivoPosgradoSerializer(
            obj.get_extracto()).data if obj.get_extracto() else []

    def get_urkund(self, obj):
        return ArchivoRevisionPropuestaComplexivoPosgradoSerializer(obj.get_urkund()).data if obj.get_urkund() else []

    def get_correccion(self, obj):
        return ArchivoRevisionPropuestaComplexivoPosgradoSerializer(
            obj.get_correccion()).data if obj.get_correccion() else []


class ArchivoRevisionPropuestaComplexivoPosgradoSerializer(Helper_ModelSerializer):
    tipodisplay = serializers.SerializerMethodField()

    class Meta:
        model = ArchivoRevisionPropuestaComplexivoPosgrado
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_tipodisplay(self, obj):
        return obj.get_tipo_display()


class ModeloEvaluativoPosgradoSerializer(Helper_ModelSerializer):
    class Meta:
        model = ModeloEvaluativoPosgrado
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class ItinerarioMallaEspecilidadSerializer(Helper_ModelSerializer):
    class Meta:
        model = ItinerarioMallaEspecilidad
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class GrupoTitulacionPostgradoSerializer(Helper_ModelSerializer):
    configuracion = ConfiguracionTitulacionPosgradoSerializer()
    itinerariomallaespecilidad = ItinerarioMallaEspecilidadSerializer()
    tutor = ProfesorSerializer()
    modeloevaluativo = ModeloEvaluativoPosgradoSerializer()
    puedeelejirgrupo = serializers.SerializerMethodField()
    cuposdisponibles = serializers.SerializerMethodField()

    class Meta:
        model = GrupoTitulacionPostgrado
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_puedeelejirgrupo(self, obj):
        return True if obj.fecha > datetime.now().date() else False

    def get_cuposdisponibles(self, obj):
        return (obj.cupo - obj.detallegrupotitulacionpostgrado_set.filter(status=True).count())


class DetalleGrupoTitulacionPostgradoSerializer(Helper_ModelSerializer):
    grupoTitulacionPostgrado = GrupoTitulacionPostgradoSerializer()
    inscrito = TemaTitulacionPosgradoMatriculaSerializar()

    class Meta:
        model = DetalleGrupoTitulacionPostgrado
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class TemaTitulacionPosArchivoFinalSerializer(Helper_ModelSerializer):
    personaprueba = PersonaSerializer()
    estado_display = serializers.SerializerMethodField()

    class Meta:
        model = TemaTitulacionPosArchivoFinal
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_estado_display(self, obj):
        return obj.get_estado_display()


class SolicitudProrrogaIngresoTemaMatriculaSerializer(Helper_ModelSerializer):
    matricula = MatriculaSerializer()
    estado_display = serializers.SerializerMethodField()

    class Meta:
        model = SolicitudProrrogaIngresoTemaMatricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_estado_display(self, obj):
        return obj.get_estado_display()


class HistorialSolicitudProrrogaIngresoTemaMatriculaSerializer(Helper_ModelSerializer):
    solicitud = SolicitudProrrogaIngresoTemaMatriculaSerializer()
    persona = PersonaSerializer()
    estado_display = serializers.SerializerMethodField()

    class Meta:
        model = HistorialSolicitudProrrogaIngresoTemaMatricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_estado_display(self, obj):
        return obj.get_estado_display()


class SolicitudIngresoTitulacionPosgradoSerializer(Helper_ModelSerializer):
    mecanismotitulacionposgrado = MecanismoTitulacionPosgradoSerializer()

    class Meta:
        model = SolicitudIngresoTitulacionPosgrado
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class MecanismoDocumentosTutoriaPosgradoSerializer(Helper_ModelSerializer):
    mecanismotitulacionposgrado = MecanismoTitulacionPosgradoSerializer()
    convocatoria = ConfiguracionTitulacionPosgradoSerializer()
    pk = serializers.SerializerMethodField()
    fieldset = serializers.SerializerMethodField()
    id_field = serializers.SerializerMethodField()
    name_field = serializers.SerializerMethodField()

    class Meta:
        model = MecanismoDocumentosTutoriaPosgrado
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_fieldset(self,obj):
        name = ''
        if obj.tipo == 7:
            name = 'fieldset_borrador_articulo'

        if obj.tipo == 8:
            name = 'fieldset_carta_de_aceptacion'
        if obj.tipo == 9:
            name = 'fieldset_acta_de_acompanamieno'
        return name

    def get_id_field(self,obj):
        name = ''
        if obj.tipo == 7:
            name = 'id_borrador_articulo'

        if obj.tipo == 8:
            name = 'id_carta_de_aceptacion'
        if obj.tipo == 9:
            name = 'id_acta_de_acompanamieno'
        return name

    def get_name_field(self, obj):
        name = ''
        if obj.tipo == 7:
            name = 'borrador_articulo'

        if obj.tipo == 8:
            name = 'carta_de_aceptacion'
        if obj.tipo == 9:
            name = 'acta_de_acompanamieno'
        return name


class JornadaSedeEncuestaTitulacionPosgradoSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    jornada_display = serializers.SerializerMethodField()
    cupo_disponible = serializers.SerializerMethodField()

    class Meta:
        model = JornadaSedeEncuestaTitulacionPosgrado
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_jornada_display(self,obj):
        return f"{obj.fecha} desde {obj.hora_inicio} hasta {obj.hora_fin}"

    def get_cupo_disponible(self,obj):
        return obj.get_cupo_disponible()

class SedeEncuestaTitulacionPosgradoSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    canton = CantonSerializer()
    jornadas = serializers.SerializerMethodField()

    class Meta:
        model = SedeEncuestaTitulacionPosgrado
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_jornadas(self, obj):
        eJornadaSedeEncuestaTitulacionPosgradoSerializer = JornadaSedeEncuestaTitulacionPosgradoSerializer(obj.get_jornada(),many=True)
        return eJornadaSedeEncuestaTitulacionPosgradoSerializer.data if obj.get_jornada() else []


class EncuestaTitulacionPosgradoSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    periodo= PeriodoSerializer()
    sedes = serializers.SerializerMethodField()

    class Meta:
        model = EncuestaTitulacionPosgrado
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_sedes(self,obj):
        eSedeEncuestaTitulacionPosgradoSerializer =  SedeEncuestaTitulacionPosgradoSerializer(obj.get_sedes(), many=True)
        return eSedeEncuestaTitulacionPosgradoSerializer.data if obj.get_sedes() else []

class InscripcionEncuestaTitulacionPosgradoSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    respuesta_encuesta = serializers.SerializerMethodField()
    encuestatitulacionposgrado = EncuestaTitulacionPosgradoSerializer()

    class Meta:
        model = InscripcionEncuestaTitulacionPosgrado
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_respuesta_encuesta(self, obj):
        try:
            info = {}
            eRespuestaSedeInscripcionEncuesta = obj.get_resultado_encuestado()
            respondio = obj.respondio
            jornada = ''
            sede = ''
            if eRespuestaSedeInscripcionEncuesta:
                jornada = eRespuestaSedeInscripcionEncuesta.jornadasedeencuestatitulacionposgrado.__str__()
                sede = eRespuestaSedeInscripcionEncuesta.jornadasedeencuestatitulacionposgrado.sedeencuestatitulacionposgrado.__str__()

            info={
                'respondio':respondio,
                'jornada':jornada,
                'sede':sede,
            }
            return info
        except Exception as ex:
            pass
