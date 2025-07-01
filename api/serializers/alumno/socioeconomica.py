from rest_framework import serializers
from django.db.models import Sum, F
from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from api.serializers.alumno.ubicacion import PaisSerializer, ProvinciaSerializer, CantonSerializer, ParroquiaSerializer
from api.serializers.base.persona import PersonaBaseSerializer
from sga.models import Persona, Carrera, Inscripcion, PersonaEstadoCivil, Sexo, PersonaDatosFamiliares, \
    ParentescoPersona, NivelTitulacion, Discapacidad, InstitucionBeca, PerfilInscripcion
from socioecon.models import FormaTrabajo, FichaSocioeconomicaINEC, TipoHogar, PersonaCubreGasto, NivelEstudio, \
    OcupacionJefeHogar, TipoVivienda, TipoViviendaPro, MaterialPared, MaterialPiso, CantidadBannoDucha, \
    TipoServicioHigienico, CantidadTVColorHogar, CantidadVehiculoHogar, CantidadCelularHogar, ProveedorServicio


class PersonaSerializer(PersonaBaseSerializer):
    identificacion = serializers.SerializerMethodField()
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_identificacion(self, obj):
        return obj.identificacion()

    def get_nombre_completo(self, obj):
        return obj.nombre_completo()


class CarreraSerializer(Helper_ModelSerializer):
    nombre_mostrar = serializers.SerializerMethodField()

    class Meta:
        model = Carrera
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_nombre_mostrar(self, obj):
        return obj.__str__()


class InscripcionSerializer(Helper_ModelSerializer):
    persona = PersonaSerializer()
    carrera = CarreraSerializer()

    class Meta:
        model = Inscripcion
        exclude = ['usuario_creacion', 'usuario_modificacion']


class PersonaEstadoCivilSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = PersonaEstadoCivil
        # fields = "__all__"
        exclude = ['codigo_tthh', 'usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class SexoSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = Sexo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class NivelTitulacionSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = NivelTitulacion
        # fields = "__all__"
        exclude = ['codigo_tthh', 'usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class ParentescoPersonaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = ParentescoPersona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class FormaTrabajoSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = FormaTrabajo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class DiscapacidadSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = Discapacidad
        # fields = "__all__"
        exclude = ['codigo_tthh', 'usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class InstitucionBecaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = InstitucionBeca
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class PersonaDatosFamiliaresSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    parentesco = ParentescoPersonaSerializer()
    niveltitulacion = NivelTitulacionSerializer()
    formatrabajo = FormaTrabajoSerializer()
    tipodiscapacidad = DiscapacidadSerializer()
    institucionvalida = InstitucionBecaSerializer()
    rangoedad_display = serializers.SerializerMethodField()
    tipoinstitucionlaboral_display = serializers.SerializerMethodField()
    download_identificacion = serializers.SerializerMethodField()
    download_discapacidad = serializers.SerializerMethodField()
    download_autorizadoministerio = serializers.SerializerMethodField()
    tienediscapacidad = serializers.SerializerMethodField()

    class Meta:
        model = PersonaDatosFamiliares
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_rangoedad_display(self, obj):
        return obj.get_rangoedad_display() if obj.rangoedad else None

    def get_tipoinstitucionlaboral_display(self, obj):
        return obj.get_tipoinstitucionlaboral_display() if obj.tipoinstitucionlaboral else None

    def get_download_identificacion(self, obj):
        return self.get_media_url(obj.cedulaidentidad.url) if obj.cedulaidentidad else None

    def get_download_discapacidad(self, obj):
        return self.get_media_url(obj.ceduladiscapacidad.url) if obj.ceduladiscapacidad else None

    def get_download_autorizadoministerio(self, obj):
        return self.get_media_url(obj.autorizadoministerio.url) if obj.autorizadoministerio else None

    def get_tienediscapacidad(self, obj):
        return obj.tipodiscapacidad is not None


class PersonaDatosPersonalesSerializer(Helper_ModelSerializer):
    tipo_documento = serializers.CharField(read_only=True)
    documento = serializers.CharField(read_only=True)
    download_documento = serializers.SerializerMethodField()
    estadodocumento_display = serializers.SerializerMethodField()
    estadodocumento = serializers.SerializerMethodField()
    download_papeleta = serializers.SerializerMethodField()
    estadopapeleta_display = serializers.SerializerMethodField()
    estadopapeleta = serializers.SerializerMethodField()
    download_libretamilitar = serializers.SerializerMethodField()
    estadolibretamilitar_display = serializers.SerializerMethodField()
    estadolibretamilitar = serializers.SerializerMethodField()
    foto_perfil = serializers.SerializerMethodField()
    estado_civil = serializers.SerializerMethodField()
    sexo = SexoSerializer()

    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_documento(self, obj):
        return obj.documento()

    def get_download_documento(self, obj):
        ePersonaDocumentoPersonal = obj.documentos_personales()
        if ePersonaDocumentoPersonal is None:
            return None
        return self.get_media_url(ePersonaDocumentoPersonal.cedula.url) if ePersonaDocumentoPersonal.cedula else None

    def get_estadodocumento_display(self, obj):
        ePersonaDocumentoPersonal = obj.documentos_personales()
        if ePersonaDocumentoPersonal is None:
            return None
        return ePersonaDocumentoPersonal.get_estadocedula_display() if ePersonaDocumentoPersonal.estadocedula else None

    def get_estadodocumento(self, obj):
        ePersonaDocumentoPersonal = obj.documentos_personales()
        if ePersonaDocumentoPersonal is None:
            return None
        return ePersonaDocumentoPersonal.estadocedula

    def get_download_papeleta(self, obj):
        ePersonaDocumentoPersonal = obj.documentos_personales()
        if ePersonaDocumentoPersonal is None:
            return None
        return self.get_media_url(ePersonaDocumentoPersonal.papeleta.url) if ePersonaDocumentoPersonal.papeleta else None

    def get_estadopapeleta_display(self, obj):
        ePersonaDocumentoPersonal = obj.documentos_personales()
        if ePersonaDocumentoPersonal is None:
            return None
        return ePersonaDocumentoPersonal.get_estadopapeleta_display() if ePersonaDocumentoPersonal.estadopapeleta else None

    def get_estadopapeleta(self, obj):
        ePersonaDocumentoPersonal = obj.documentos_personales()
        if ePersonaDocumentoPersonal is None:
            return None
        return ePersonaDocumentoPersonal.estadopapeleta

    def get_download_libretamilitar(self, obj):
        ePersonaDocumentoPersonal = obj.documentos_personales()
        if ePersonaDocumentoPersonal is None:
            return None
        return self.get_media_url(ePersonaDocumentoPersonal.libretamilitar.url) if ePersonaDocumentoPersonal.libretamilitar else None

    def get_estadolibretamilitar_display(self, obj):
        ePersonaDocumentoPersonal = obj.documentos_personales()
        if ePersonaDocumentoPersonal is None:
            return None
        return ePersonaDocumentoPersonal.get_estadolibretamilitar_display() if ePersonaDocumentoPersonal.estadolibretamilitar else None

    def get_estadolibretamilitar(self, obj):
        ePersonaDocumentoPersonal = obj.documentos_personales()
        if ePersonaDocumentoPersonal is None:
            return None
        return ePersonaDocumentoPersonal.estadolibretamilitar

    def get_tipo_documento(self, obj):
        return obj.tipo_documento()

    def get_foto_perfil(self, obj):
        if obj.tiene_foto():
            return self.get_media_url(obj.foto().foto.url)
        if obj.sexo and obj.sexo.id == 1:
            foto_perfil = '/static/images/iconos/mujer.png'
        else:
            foto_perfil = '/static/images/iconos/hombre.png'
        return self.get_static_url(foto_perfil)

    def get_estado_civil(self, obj):
        estado_civil = obj.estado_civil()
        if estado_civil:
            return PersonaEstadoCivilSerializer(estado_civil).data
        return None


class PersonaDatosDiscapacidadSerializer(Helper_ModelSerializer):
    tipodiscapacidad = DiscapacidadSerializer()
    download_archivo = serializers.SerializerMethodField()
    institucionvalida = InstitucionBecaSerializer()
    tipodiscapacidadmultiple = serializers.SerializerMethodField()

    class Meta:
        model = PerfilInscripcion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_download_archivo(self, obj):
        archivo = obj.archivo
        return self.get_media_url(archivo.url) if archivo else None

    def get_tipodiscapacidadmultiple(self, obj):
        eDiscapacidades = obj.tipodiscapacidadmultiple.all()
        return DiscapacidadSerializer(eDiscapacidades, many=True).data if eDiscapacidades.values("id").exists() else []


class PersonaDatosNacimientoSerializer(Helper_ModelSerializer):
    paisnacimiento = PaisSerializer()
    provincianacimiento = ProvinciaSerializer()
    cantonnacimiento = CantonSerializer()
    parroquianacimiento = ParroquiaSerializer()

    class Meta:
        model = Persona
        fields = ['id', 'paisnacimiento', 'provincianacimiento', 'cantonnacimiento', 'parroquianacimiento']
        # exclude = ['usuario_creacion', 'usuario_modificacion']


class PersonaDatosDomicilioSerializer(Helper_ModelSerializer):
    pais = PaisSerializer()
    provincia = ProvinciaSerializer()
    canton = CantonSerializer()
    parroquia = ParroquiaSerializer()
    download_croquis = serializers.SerializerMethodField()
    download_planilla_luz = serializers.SerializerMethodField()

    class Meta:
        model = Persona
        fields = ['id', 'pais', 'provincia', 'canton', 'parroquia', 'direccion', 'direccion2', 'num_direccion',
                  'referencia', 'sector', 'ciudadela', 'telefono', 'telefono_conv', 'tipocelular', 'archivocroquis',
                  'sectorlugar', 'archivoplanillaluz', 'download_croquis', 'download_planilla_luz']
        # exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_download_croquis(self, obj):
        archivo = obj.archivocroquis
        return self.get_media_url(archivo.url) if archivo else None

    def get_download_planilla_luz(self, obj):
        archivo = obj.archivoplanillaluz
        return self.get_media_url(archivo.url) if archivo else None


class TipoHogarSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = TipoHogar
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class PersonaCubreGastoSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = PersonaCubreGasto
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class PersonaEstructuraFamiliarSerializer(Helper_ModelSerializer):
    tipohogar = TipoHogarSerializer()
    personacubregasto = PersonaCubreGastoSerializer()

    class Meta:
        model = FichaSocioeconomicaINEC
        fields = ['id', 'tipohogar', 'escabezafamilia', 'esdependiente', 'personacubregasto', 'otroscubregasto']
        # exclude = ['usuario_creacion', 'usuario_modificacion']


class NivelEstudioSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = NivelEstudio
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class OcupacionJefeHogarSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = OcupacionJefeHogar
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class PersonaNivelEducacionSerializer(Helper_ModelSerializer):
    niveljefehogar = NivelEstudioSerializer()
    ocupacionjefehogar = OcupacionJefeHogarSerializer()

    class Meta:
        model = FichaSocioeconomicaINEC
        fields = ['id', 'niveljefehogar', 'alguienafiliado', 'alguienseguro', 'ocupacionjefehogar']
        # exclude = ['usuario_creacion', 'usuario_modificacion']


class TipoViviendaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = TipoVivienda
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class TipoViviendaProSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = TipoViviendaPro
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class MaterialParedSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = MaterialPared
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class MaterialPisoSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = MaterialPiso
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class CantidadBannoDuchaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = CantidadBannoDucha
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class TipoServicioHigienicoSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = TipoServicioHigienico
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class PersonaCaracteristicaViviendaSerializer(Helper_ModelSerializer):
    tipovivienda = TipoViviendaSerializer()
    tipoviviendapro = TipoViviendaProSerializer()
    materialpared = MaterialParedSerializer()
    materialpiso = MaterialPisoSerializer()
    cantbannoducha = CantidadBannoDuchaSerializer()
    tiposervhig = TipoServicioHigienicoSerializer()

    class Meta:
        model = FichaSocioeconomicaINEC
        fields = ['id', 'tipovivienda', 'tipoviviendapro', 'materialpared', 'materialpiso', 'cantbannoducha',
                  'tiposervhig']
        # exclude = ['usuario_creacion', 'usuario_modificacion']


class PersonaHabitoConsumoSerializer(Helper_ModelSerializer):

    class Meta:
        model = FichaSocioeconomicaINEC
        fields = ['id', 'compravestcc', 'usainternetseism', 'usacorreonotrab', 'registroredsocial', 'leidolibrotresm']
        # exclude = ['usuario_creacion', 'usuario_modificacion']


class CantidadTVColorHogarSerializer(Helper_ModelSerializer):

    class Meta:
        model = CantidadTVColorHogar
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class CantidadVehiculoHogarSerializer(Helper_ModelSerializer):

    class Meta:
        model = CantidadVehiculoHogar
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class PersonaPosesionBienesSerializer(Helper_ModelSerializer):
    canttvcolor = CantidadTVColorHogarSerializer()
    cantvehiculos = CantidadVehiculoHogarSerializer()

    class Meta:
        model = FichaSocioeconomicaINEC
        fields = ['id', 'tienetelefconv', 'tienecocinahorno', 'tienerefrig', 'tienelavadora', 'tienemusica', 'canttvcolor', 'cantvehiculos']
        # exclude = ['usuario_creacion', 'usuario_modificacion']


class CantidadCelularHogarSerializer(Helper_ModelSerializer):

    class Meta:
        model = CantidadCelularHogar
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class ProveedorServicioSerializer(Helper_ModelSerializer):

    class Meta:
        model = ProveedorServicio
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class PersonaAccesoTecnologiaSerializer(Helper_ModelSerializer):
    cantcelulares = CantidadCelularHogarSerializer()
    proveedorinternet = ProveedorServicioSerializer()

    class Meta:
        model = FichaSocioeconomicaINEC
        fields = ['id', 'tieneinternet', 'internetpanf', 'proveedorinternet', 'tienedesktop', 'equipotienecamara', 'tienelaptop', 'cantcelulares']
        # exclude = ['usuario_creacion', 'usuario_modificacion']


class PersonaInstalacionesSerializer(Helper_ModelSerializer):

    class Meta:
        model = FichaSocioeconomicaINEC
        fields = ['id', 'tienesala', 'tienecomedor', 'tienecocina', 'tienebanio', 'tieneluz', 'tieneagua', 'tienetelefono', 'tienealcantarilla']
        # exclude = ['usuario_creacion', 'usuario_modificacion']


class PersonaActividadExtracurricularesSerializer(Helper_ModelSerializer):
    tipoactividad_display = serializers.SerializerMethodField()
    tipotarea_display = serializers.SerializerMethodField()

    class Meta:
        model = FichaSocioeconomicaINEC
        fields = ['id','tipoactividad_display', 'tipotarea_display', 'horastareahogar', 'horastrabajodomestico', 'horastrabajofuera', 'tipoactividad', 'horashacertareas', 'tipotarea', 'otrostarea', 'otrosactividad']
        # exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_tipoactividad_display(self, obj):
        return obj.get_tipoactividad_display()

    def get_tipotarea_display(self, obj):
        return obj.get_tipotarea_display()


class PersonaRecursosEstudioSerializer(Helper_ModelSerializer):

    class Meta:
        model = FichaSocioeconomicaINEC
        fields = ['id', 'tienefolleto', 'tienecomputador', 'tieneenciclopedia', 'otrosrecursos', 'tienecyber', 'tienebiblioteca', 'tienemuseo', 'tienearearecreacion', 'otrossector']
        # exclude = ['usuario_creacion', 'usuario_modificacion']


class PersonaSaludEstudianteSerializer(Helper_ModelSerializer):
    estadogeneral_display = serializers.SerializerMethodField()
    salubridadvida_display = serializers.SerializerMethodField()

    class Meta:
        model = FichaSocioeconomicaINEC
        fields = ['id', 'tienediabetes', 'tienehipertencion', 'tieneparkinson', 'tienecancer', 'tienealzheimer', 'tienevitiligo', 'tienedesgastamiento',
                  'tienepielblanca', 'otrasenfermedades', 'tienesida', 'enfermedadescomunes', 'salubridadvida', 'estadogeneral', 'tratamientomedico',
                  'estadogeneral_display', 'salubridadvida_display']
        # exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_estadogeneral_display(self, obj):
        return obj.get_estadogeneral_display()

    def get_salubridadvida_display(self, obj):
        return obj.get_salubridadvida_display()




