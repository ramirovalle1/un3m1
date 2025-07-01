from rest_framework import serializers
from django.db.models import Sum, F
from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from datetime import datetime

from api.serializers.alumno.ubicacion import PaisSerializer, ProvinciaSerializer, CantonSerializer, ParroquiaSerializer
from api.serializers.base.persona import Helper_ModelSerializer, PersonaBaseSerializer
from med.models import PersonaExtension, Enfermedad, TipoEnfermedad
from sagest.models import VacunaCovid, TipoVacunaCovid, VacunaCovidDosis
from sga.models import Persona, Sexo, PersonaEstadoCivil, ParentescoPersona, NivelTitulacion, Discapacidad, \
    InstitucionBeca, PersonaDatosFamiliares, PerfilInscripcion, Raza, NacionalidadIndigena, PersonaSituacionLaboral, \
    TipoArchivo, Archivo, TipoSangre, PersonaEnfermedad, Titulacion, Titulo, InstitucionEducacionSuperior, Colegio, \
    FinanciamientoBeca, DetalleTitulacionBachiller, AreaTitulo, Capacitacion, TipoCurso, TipoCertificacion, \
    TipoParticipacion, TipoCapacitacion, ContextoCapacitacion, DetalleContextoCapacitacion, \
    AreaConocimientoTitulacion, SubAreaConocimientoTitulacion, SubAreaEspecificaConocimientoTitulacion, \
    CertificadoIdioma, Idioma, InstitucionCertificadora, NivelSuficencia, CertificacionPersona, MigrantePersona, \
    PersonaDetalleMaternidad, ArtistaPersona, CampoArtistico, DeportistaPersona, DisciplinaDeportiva, \
    ParticipantesMatrices, BecaPersona, BecaAsignacion, CuentaBancariaPersona
from socioecon.models import FormaTrabajo


class SexoSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = Sexo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class PersonaEstadoCivilSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = PersonaEstadoCivil
        # fields = "__all__"
        exclude = ['codigo_tthh', 'usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class DatosPersonalesSerializer(Helper_ModelSerializer):
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
    tiene_discapasidad = serializers.SerializerMethodField()
    raza = serializers.SerializerMethodField()
    sexo = SexoSerializer()
    paisnacimiento = PaisSerializer()
    provincianacimiento = ProvinciaSerializer()
    cantonnacimiento = CantonSerializer()
    parroquianacimiento = ParroquiaSerializer()
    paisnacionalidad = PaisSerializer()
    pais = PaisSerializer()
    provincia = ProvinciaSerializer()
    canton = CantonSerializer()
    parroquia = ParroquiaSerializer()
    download_croquis = serializers.SerializerMethodField()
    download_planilla_luz = serializers.SerializerMethodField()
    tipocelular_display = serializers.SerializerMethodField()
    zona_display = serializers.SerializerMethodField()

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

    def get_tiene_discapasidad(self, obj):
        return obj.tiene_discapasidad_new()

    def get_raza(self, obj):
        mi_perfil = obj.mi_perfil()
        if mi_perfil and mi_perfil.raza:
            return mi_perfil.raza.nombre
        return None

    def get_download_croquis(self, obj):
        archivo = obj.archivocroquis
        return self.get_media_url(archivo.url) if archivo else None

    def get_download_planilla_luz(self, obj):
        archivo = obj.archivoplanillaluz
        return self.get_media_url(archivo.url) if archivo else None

    def get_tipocelular_display(self, obj):
        tipocelular = obj.tipocelular
        return obj.get_tipocelular_display() if tipocelular else None

    def get_zona_display(self, obj):
        zona = obj.zona
        return obj.get_zona_display() if zona else None


class DatosPersonalesPersonaSerializer(PersonaBaseSerializer):
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


class ParentescoPersonaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = ParentescoPersona
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


class DatosPersonalesFamiliaresSerializer(Helper_ModelSerializer):
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


class DatosPersonalesDiscapacidadSerializer(Helper_ModelSerializer):
    tipodiscapacidad = DiscapacidadSerializer()
    download_archivo = serializers.SerializerMethodField()
    institucionvalida = InstitucionBecaSerializer()
    tipodiscapacidadmultiple = serializers.SerializerMethodField()
    estadoarchivodiscapacidad_display = serializers.SerializerMethodField()

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

    def get_estadoarchivodiscapacidad_display(self, obj):
        estadoarchivodiscapacidad = obj.estadoarchivodiscapacidad
        return obj.get_estadoarchivodiscapacidad_display() if estadoarchivodiscapacidad else None



class DatosPersonalesEmbarazoSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = PersonaDetalleMaternidad
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class RazaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = Raza
        # fields = "__all__"
        exclude = ['codigo_tthh', 'usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class NacionalidadIndigenaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = NacionalidadIndigena
        # fields = "__all__"
        exclude = ['codigo_tthh', 'usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class DatosPersonalesCuentaBancariaSerializer(Helper_ModelSerializer):
    download_archivocuentabancaria = serializers.SerializerMethodField()
    nombre_banco = serializers.SerializerMethodField()
    nombre_tipo_cuenta = serializers.SerializerMethodField()

    class Meta:
        model = CuentaBancariaPersona
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_download_archivocuentabancaria(self, obj):
        archivo = obj.archivo
        return self.get_media_url(archivo.url) if archivo else None

    def get_nombre_banco(self, obj):
        return obj.banco.nombre if obj.banco else None

    def get_nombre_tipo_cuenta(self, obj):
        return obj.tipocuentabanco.nombre if obj.tipocuentabanco else None


class DatosPersonalesEtniaSerializer(Helper_ModelSerializer):
    raza = RazaSerializer()
    nacionalidadindigena = NacionalidadIndigenaSerializer()
    download_archivoraza = serializers.SerializerMethodField()
    estadoarchivoraza_display = serializers.SerializerMethodField()

    class Meta:
        model = PerfilInscripcion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_download_archivoraza(self, obj):
        archivo = obj.archivoraza
        return self.get_media_url(archivo.url) if archivo else None

    def get_estadoarchivoraza_display(self, obj):
        estadoarchivoraza = obj.estadoarchivoraza
        return obj.get_estadoarchivoraza_display() if estadoarchivoraza else None


class DatosPersonalesSituacionLaboralSerializer(Helper_ModelSerializer):
    tipoinstitucionlaboral_display = serializers.SerializerMethodField()

    class Meta:
        model = PersonaSituacionLaboral
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_tipoinstitucionlaboral_display(self, obj):
        return obj.get_tipoinstitucionlaboral_display()



class DatosPersonalesMigrantePersonaSerializer(Helper_ModelSerializer):
    paisresidencia = PaisSerializer()
    download_archivo = serializers.SerializerMethodField()
    estadoarchivo_display = serializers.SerializerMethodField()

    class Meta:
        model = MigrantePersona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_download_archivo(self, obj):
        archivo = obj.archivo
        return self.get_media_url(archivo.url) if archivo else None

    def get_estadoarchivo_display(self, obj):
        estadoarchivo = obj.estadoarchivo
        return obj.get_estadoarchivo_display() if estadoarchivo else None


class TipoVacunaCovidSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = TipoVacunaCovid
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class TipoSangreSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = TipoSangre
        # fields = "__all__"
        exclude = ['codigo_tthh', 'usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class VacunaCovidDosisSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    fechadosis = serializers.SerializerMethodField()

    class Meta:
        model = VacunaCovidDosis
        fields = ['cabvacuna', 'fechadosis', 'pk', 'numdosis']
        # exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_fechadosis(self, obj):
        return obj.fechadosis.strftime('%Y-%m-%d')


class VacunaCovidSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    tipovacuna = TipoVacunaCovidSerializer()
    dosis = serializers.SerializerMethodField()
    download_certificado = serializers.SerializerMethodField()

    class Meta:
        model = VacunaCovid
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_dosis(self, obj):
        eDosis = VacunaCovidDosis.objects.filter(cabvacuna=obj)
        return VacunaCovidDosisSerializer(eDosis, many=True).data if eDosis.values("id").exists() else []

    def get_download_certificado(self, obj):
        archivo = obj.certificado
        return self.get_media_url(archivo.url) if archivo else None


class TipoEnfermedadSerializer(Helper_ModelSerializer):

    class Meta:
        model = TipoEnfermedad
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class EnfermedadSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    tipo = TipoEnfermedadSerializer()

    class Meta:
        model = Enfermedad
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class PersonaEnfermedadSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    enfermedad = EnfermedadSerializer()
    download_archivomedico = serializers.SerializerMethodField()
    estadoarchivo_display = serializers.SerializerMethodField()

    class Meta:
        model = PersonaEnfermedad
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_estadoarchivo_display(self, obj):
        return obj.get_estadoarchivo_display()

    def get_download_archivomedico(self, obj):
        archivo = obj.archivomedico
        return self.get_media_url(archivo.url) if archivo else None


class DatosPersonalesMedicosSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    tipo_documento = serializers.SerializerMethodField()
    documento = serializers.SerializerMethodField()
    nombre_completo = serializers.SerializerMethodField()
    estadocivil = PersonaEstadoCivilSerializer()
    parentescoemergencia = ParentescoPersonaSerializer()
    sexo = serializers.SerializerMethodField()
    email_personal = serializers.SerializerMethodField()
    foto_perfil = serializers.SerializerMethodField()
    tipo_sangre = serializers.SerializerMethodField()
    download_archivosangre = serializers.SerializerMethodField()
    estadotiposangre = serializers.SerializerMethodField()
    estadotiposangre_display = serializers.SerializerMethodField()
    peso = serializers.SerializerMethodField()
    talla = serializers.SerializerMethodField()
    vacunas_covid_19 = serializers.SerializerMethodField()
    enfermedades = serializers.SerializerMethodField()

    class Meta:
        model = PersonaExtension
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_nombre_completo(self, obj):
        return obj.persona.nombre_completo()

    def get_sexo(self, obj):
        return obj.persona.sexo.nombre

    def get_email_personal(self, obj):
        return obj.persona.email

    def get_tipo_documento(self, obj):
        return obj.persona.tipo_documento()

    def get_documento(self, obj):
        return obj.persona.documento()

    def get_tipo_sangre(self, obj):
        sangre = obj.persona.sangre
        return TipoSangreSerializer(sangre).data if sangre else None

    def get_download_archivosangre(self, obj):
        documento = obj.persona.documentos_personales()
        if documento is None:
            return None
        return self.get_media_url(documento.tiposangre.url) if documento.tiposangre else None

    def get_estadotiposangre(self, obj):
        documento = obj.persona.documentos_personales()
        if documento is None:
            return None
        return documento.estadotiposangre

    def get_estadotiposangre_display(self, obj):
        documento = obj.persona.documentos_personales()
        if documento is None:
            return None
        return documento.get_estadotiposangre_display()

    def get_peso(self, obj):
        ePersonaExamenFisico = obj.personaexamenfisico()
        return ePersonaExamenFisico.peso if ePersonaExamenFisico else None

    def get_talla(self, obj):
        ePersonaExamenFisico = obj.personaexamenfisico()
        return ePersonaExamenFisico.talla if ePersonaExamenFisico else None

    def get_foto_perfil(self, obj):
        if obj.persona.tiene_foto():
            return self.get_media_url(obj.persona.foto().foto.url)
        if obj.persona.sexo and obj.persona.sexo.id == 1:
            foto_perfil = '/static/images/iconos/mujer.png'
        else:
            foto_perfil = '/static/images/iconos/hombre.png'
        return self.get_static_url(foto_perfil)

    def get_vacunas_covid_19(self, obj):
        eVacunas = VacunaCovid.objects.filter(persona=obj.persona)
        return VacunaCovidSerializer(eVacunas, many=True).data if eVacunas.values("id").exists() else []

    def get_enfermedades(self, obj):
        ePersonaEnfermedades = obj.persona.mis_enfermedades()
        return PersonaEnfermedadSerializer(ePersonaEnfermedades, many=True).data if ePersonaEnfermedades.values("id").exists() else []


class NivelTitulacionSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    nivel_display = serializers.SerializerMethodField()
    tipo_display = serializers.SerializerMethodField()

    class Meta:
        model = NivelTitulacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion', 'rango', 'codigo_tthh']

    def get_pk(self, obj):
        return obj.id

    def get_nivel_display(self, obj):
        return obj.get_nivel_display()

    def get_tipo_display(self, obj):
        return obj.get_tipo_display()


class TituloSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    nivel = NivelTitulacionSerializer()

    class Meta:
        model = Titulo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion', 'grado', 'areaconocimiento', 'subareaconocimiento', 'subareaespecificaconocimiento', 'codigo_tthh']

    def get_pk(self, obj):
        return obj.id


class AreaTituloSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = AreaTitulo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion', 'codigo']

    def get_pk(self, obj):
        return obj.id


class InstitucionEducacionSuperiorSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = InstitucionEducacionSuperior
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion', 'codigo', 'pais']

    def get_pk(self, obj):
        return obj.id


class ColegioSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    tipo_display = serializers.SerializerMethodField()

    class Meta:
        model = Colegio
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion', 'codigo', 'canton']

    def get_pk(self, obj):
        return obj.id

    def get_tipo_display(self, obj):
        return obj.get_tipo_display()


class FinanciamientoBecaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = FinanciamientoBeca
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion', 'codigo']

    def get_pk(self, obj):
        return obj.id

    def get_tipo_display(self, obj):
        return obj.get_tipo_display()


class DetalleTitulacionBachillerSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    download_actagrado = serializers.SerializerMethodField()
    download_reconocimientoacademico = serializers.SerializerMethodField()

    class Meta:
        model = DetalleTitulacionBachiller
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_download_actagrado(self, obj):
        archivo = obj.actagrado
        return self.get_media_url(archivo.url) if archivo else None

    def get_download_reconocimientoacademico(self, obj):
        archivo = obj.reconocimientoacademico
        return self.get_media_url(archivo.url) if archivo else None


class FormacionAcademicaMisTitulosSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    titulo = TituloSerializer()
    areatitulo = AreaTituloSerializer()
    pais = PaisSerializer()
    provincia = ProvinciaSerializer()
    canton = CantonSerializer()
    parroquia = ParroquiaSerializer()
    institucion = InstitucionEducacionSuperiorSerializer()
    colegio = ColegioSerializer()
    tipobeca_display = serializers.SerializerMethodField()
    download_archivo = serializers.SerializerMethodField()
    download_registroarchivo = serializers.SerializerMethodField()
    detalletitulacionbachiller = serializers.SerializerMethodField()

    class Meta:
        model = Titulacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_tipobeca_display(self, obj):
        return obj.get_tipobeca_display()

    def get_download_archivo(self, obj):
        archivo = obj.archivo
        return self.get_media_url(archivo.url) if archivo else None

    def get_download_registroarchivo(self, obj):
        archivo = obj.registroarchivo
        return self.get_media_url(archivo.url) if archivo else None

    def get_detalletitulacionbachiller(self, obj):
        eDetalleTitulacionBachiller = DetalleTitulacionBachiller.objects.filter(titulacion=obj).last()
        return DetalleTitulacionBachillerSerializer(eDetalleTitulacionBachiller).data if not eDetalleTitulacionBachiller is None else None


class TipoCursoSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = TipoCurso
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion', 'codigo_tthh']

    def get_pk(self, obj):
        return obj.id


class TipoCertificacionSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = TipoCertificacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class TipoParticipacionSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = TipoParticipacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class TipoCapacitacionSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = TipoCapacitacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class ContextoCapacitacionSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = ContextoCapacitacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class DetalleContextoCapacitacionSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = DetalleContextoCapacitacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class AreaConocimientoTitulacionSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    tipo_display = serializers.SerializerMethodField()

    class Meta:
        model = AreaConocimientoTitulacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion', 'codigo', 'codigocaces', 'migrado', 'vigente']

    def get_pk(self, obj):
        return obj.id

    def get_tipo_display(self, obj):
        return obj.get_tipo_display()


class SubAreaConocimientoTitulacionSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    tipo_display = serializers.SerializerMethodField()

    class Meta:
        model = SubAreaConocimientoTitulacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion', 'codigo', 'codigocaces', 'migrado', 'vigente']

    def get_pk(self, obj):
        return obj.id

    def get_tipo_display(self, obj):
        return obj.get_tipo_display()


class SubAreaEspecificaConocimientoTitulacionSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    tipo_display = serializers.SerializerMethodField()

    class Meta:
        model = SubAreaEspecificaConocimientoTitulacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion', 'codigo', 'codigocaces', 'migrado', 'vigente']

    def get_pk(self, obj):
        return obj.id

    def get_tipo_display(self, obj):
        return obj.get_tipo_display()


class FormacionAcademicaMisCapacitacionesSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    tipo_display = serializers.SerializerMethodField()
    tipocurso = TipoCursoSerializer()
    tipocertificacion = TipoCertificacionSerializer()
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
    download_archivo = serializers.SerializerMethodField()
    modalidad_display = serializers.SerializerMethodField()

    class Meta:
        model = Capacitacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_tipo_display(self, obj):
        return obj.get_tipo_display()

    def get_download_archivo(self, obj):
        archivo = obj.archivo
        return self.get_media_url(archivo.url) if archivo else None

    def get_modalidad_display(self, obj):
        return obj.get_modalidad_display()


class IdiomaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = Idioma
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class InstitucionCertificadoraSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = InstitucionCertificadora
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class NivelSuficenciaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = NivelSuficencia
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class FormacionAcademicaCertificadosIdiomasSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    idioma = IdiomaSerializer()
    institucioncerti = InstitucionCertificadoraSerializer()
    nivelsuficencia = NivelSuficenciaSerializer()
    estado_display = serializers.SerializerMethodField()
    download_archivo = serializers.SerializerMethodField()

    class Meta:
        model = CertificadoIdioma
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_estado_display(self, obj):
        return obj.get_estado_display()

    def get_download_archivo(self, obj):
        archivo = obj.archivo
        return self.get_media_url(archivo.url) if archivo else None


class FormacionAcademicaCertificacionesPersonaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    download_archivo = serializers.SerializerMethodField()

    class Meta:
        model = CertificacionPersona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_download_archivo(self, obj):
        archivo = obj.archivo
        return self.get_media_url(archivo.url) if archivo else None


class CampoArtisticoSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = CampoArtistico
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class ArtistaPersonaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    campoartistico = serializers.SerializerMethodField()
    download_archivo = serializers.SerializerMethodField()
    estadoarchivo_display = serializers.SerializerMethodField()

    class Meta:
        model = ArtistaPersona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_download_archivo(self, obj):
        archivo = obj.archivo
        return self.get_media_url(archivo.url) if archivo else None

    def get_estadoarchivo_display(self, obj):
        estadoarchivo = obj.estadoarchivo
        return obj.get_estadoarchivo_display() if estadoarchivo else None

    def get_campoartistico(self, obj):
        eCampoArtisticos = obj.campoartistico.all()
        return CampoArtisticoSerializer(eCampoArtisticos, many=True).data if eCampoArtisticos.values("id").exists() else []



class DisciplinaDeportivaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = DisciplinaDeportiva
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class DeportistaPersonaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    disciplina = serializers.SerializerMethodField()
    paisevento = PaisSerializer()
    download_archivoevento = serializers.SerializerMethodField()
    estadoarchivoevento_display = serializers.SerializerMethodField()
    download_archivoentrena = serializers.SerializerMethodField()
    estadoarchivoentrena_display = serializers.SerializerMethodField()

    class Meta:
        model = DeportistaPersona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_download_archivoevento(self, obj):
        archivoevento = obj.archivoevento
        return self.get_media_url(archivoevento.url) if archivoevento else None

    def get_estadoarchivoevento_display(self, obj):
        estadoarchivoevento = obj.estadoarchivoevento
        return obj.get_estadoarchivoevento_display() if estadoarchivoevento else None

    def get_disciplina(self, obj):
        eDisciplinaDeportivas = obj.disciplina.all()
        return DisciplinaDeportivaSerializer(eDisciplinaDeportivas, many=True).data if eDisciplinaDeportivas.values("id").exists() else []

    def get_download_archivoentrena(self, obj):
        archivoentrena = obj.archivoentrena
        return self.get_media_url(archivoentrena.url) if archivoentrena else None

    def get_estadoarchivoentrena_display(self, obj):
        estadoarchivoentrena = obj.estadoarchivoentrena
        return obj.get_estadoarchivoentrena_display() if estadoarchivoentrena else None


class FormacionAcademicaParticipantesMatricesSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    programa = serializers.SerializerMethodField()
    proyecto = serializers.SerializerMethodField()
    tipo = serializers.SerializerMethodField()

    class Meta:
        model = ParticipantesMatrices
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_programa(self, obj):
        try:
            programa = obj.proyecto.programa.nombre
        except:
            programa = 'ACTIVIDAD EXTRACURRICULAR'
        return programa

    def get_proyecto(self, obj):
        try:
            proyecto = obj.proyecto.nombre
        except:
            proyecto = obj.actividad.titulo
        return proyecto

    def get_tipo(self, obj):
        try:
            tipo = obj.proyecto.tipo
            if tipo == 2:
                tipo = 'INVESTIGACIÓN'
            elif tipo == 1:
                tipo = 'VINCULACIÓN'
            else:
                tipo = 'VINCULACIÓN'
        except:
            tipo = 'VINCULACIÓN'
        return tipo


class FormacionAcademicaBecaPersonaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    tipoinstitucion_display = serializers.SerializerMethodField()
    institucion = InstitucionBecaSerializer()
    download_archivo = serializers.SerializerMethodField()
    estadoarchivo_display = serializers.SerializerMethodField()

    class Meta:
        model = BecaPersona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_tipoinstitucion_display(self, obj):
        return obj.get_tipoinstitucion_display()

    def get_download_archivo(self, obj):
        archivo = obj.archivo
        return self.get_media_url(archivo.url) if archivo else None

    def get_estadoarchivo_display(self, obj):
        return obj.get_estadoarchivo_display()


class FormacionAcademicaBecaAsignacionSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    periodo = serializers.SerializerMethodField()
    institucion = serializers.SerializerMethodField()
    tipobeca = serializers.SerializerMethodField()
    finalizo = serializers.SerializerMethodField()

    class Meta:
        model = BecaAsignacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_periodo(self, obj):
        try:
            periodo = obj.solicitud.periodo.nombre
        except:
            periodo = None
        return periodo

    def get_institucion(self, obj):
        return 'Universidad Estatal de Milagro'

    def get_tipobeca(self, obj):
        try:
            tipobeca = obj.solicitud.becatipo.nombre
        except:
            tipobeca = None
        return tipobeca

    def get_finalizo(self, obj):
        try:
            finalizo = obj.solicitud.periodo.finalizo()
        except:
            finalizo = False
        return finalizo






