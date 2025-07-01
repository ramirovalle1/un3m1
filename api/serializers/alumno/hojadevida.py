
from api.serializers.base.persona import PersonaBaseSerializer, Helper_ModelSerializer
from med.models import PersonaExtension, PersonaExamenFisico, PersonaFichaMedica, TipoEnfermedad, Enfermedad
from sagest.models import Banco, TipoCuentaBanco, TipoVacunaCovid, VacunaCovid, VacunaCovidDosis, MotivoSalida, \
    OtroRegimenLaboral, DedicacionLaboral, ActividadLaboral, ExperienciaLaboral, OtroMerito
from sga.models import Persona, Raza, PersonaDatosFamiliares, \
    NacionalidadIndigena, Discapacidad, SubTipoDiscapacidad, PersonaEstadoCivil, \
    PersonaSituacionLaboral, ParentescoPersona, PerfilInscripcion, \
    PersonaDocumentoPersonal, Pais, Provincia, Canton, Parroquia, \
    InstitucionBeca, NivelTitulacion, PersonaSituacionLaboral, Archivo, \
    Inscripcion, TipoArchivo, CuentaBancariaPersona, TipoSangre, PersonaEnfermedad, Titulacion, Titulo, Colegio, \
    InstitucionEducacionSuperior, AreaTitulo, AreaConocimientoTitulacion, SubAreaConocimientoTitulacion, \
    SubAreaEspecificaConocimientoTitulacion, Capacitacion, TipoCurso, TipoCertificacion, TipoParticipacion, \
    TipoCapacitacion, ContextoCapacitacion, DetalleContextoCapacitacion, CertificadoIdioma, Idioma, NivelSuficencia, \
    InstitucionCertificadora, CertificacionPersona, ReferenciaPersona, Relacion, BecaPersona, MigrantePersona, \
    ArtistaPersona, CampoArtistico, DisciplinaDeportiva, DeportistaPersona, OperadoraMovil
from rest_framework import serializers

from datetime import datetime

from socioecon.models import FormaTrabajo




#DATOS NACIMIENTO Y DOMICILIO
class PaisSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()
    class Meta:
        model = Pais
        fields = ('nombre', 'nacionalidad', 'idm', 'value', 'label',)

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class ProvinciaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()
    class Meta:
        model = Provincia
        fields = ('nombre', 'idm', 'value', 'label',)

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class CantonSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()
    provincia = ProvinciaSerializer()

    class Meta:
        model = Canton
        fields = ('nombre', 'idm', 'value', 'label','provincia')

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class ParroquiaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()
    class Meta:
        model = Provincia
        fields = ('nombre', 'idm', 'value', 'label',)

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class PersonaSituacionLaboralSerializer(Helper_ModelSerializer):
    tipoinstitucionlaboral = serializers.SerializerMethodField()

    class Meta:
        model = PersonaSituacionLaboral
        fields= '__all__'

    def get_tipoinstitucionlaboral(self,obj):
        return obj.get_tipoinstitucionlaboral_display

class PersonaEstadoCivilSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model = PersonaEstadoCivil
        fields = '__all__'

    def get_idm(self, obj):
        return obj.id

class TipoSangreSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = TipoSangre
        fields = ('sangre', 'idm', 'value', 'label',)

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.sangre if obj and obj.sangre else None


class PersonaFichaMedicaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model = PersonaFichaMedica
        fields = '__all__'

    def get_id(self, obj):
        return obj.id

class PersonaExamenFisicoSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model = PersonaExamenFisico
        fields = ('personafichamedica', 'idm', 'peso', 'talla' )

    def get_idm(self, obj):
        return obj.id


class ColegioSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()

    class Meta:
        model= Colegio
        fields = '__all__'

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class InstitucionEducacionSuperiorSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()

    class Meta:
        model = InstitucionEducacionSuperior
        fields = '__all__'

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class NivelTitulacionSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model= NivelTitulacion
        fields = '__all__'

    def get_idm(self, obj):
        return obj.id

class SubAreaEspecificaConocimientoTitulacionSerializer(Helper_ModelSerializer):
    label = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()

    class Meta:
        model = SubAreaEspecificaConocimientoTitulacion
        fields = '__all__'

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None



class SubAreaConocimientoTitulacionSerializer(Helper_ModelSerializer):
    label = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()

    class Meta:
        model = SubAreaConocimientoTitulacion
        fields = '__all__'

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None


class AreaConocimientoTitulacionSerializer(Helper_ModelSerializer):
    label = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()

    class Meta:
        model = AreaConocimientoTitulacion
        fields = '__all__'

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class TituloSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    nivel = NivelTitulacionSerializer()
    areaconocimiento = AreaConocimientoTitulacionSerializer()
    #areaconocimiento_dis = serializers.SerializerMethodField()
    subareaconocimiento_disp = serializers.SerializerMethodField()
    #subareaconocimiento_dis = serializers.SerializerMethodField()
    subareaespecificaconocimiento_disp = serializers.SerializerMethodField()
    #subareaespecificaconocimiento_dis = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()


    class Meta:
        model = Titulo
        fields = '__all__'

    def get_idm(self, obj):
        return obj.id

    def get_subareaconocimiento_disp(self, obj):
        des = None
        if obj and obj.subareaconocimiento:
            des = obj.subareaconocimiento.nombre
        return des

    def get_subareaespecificaconocimiento_disp(self, obj):
        des = None
        if obj and obj.subareaespecificaconocimiento:
            des = obj.subareaespecificaconocimiento.nombre
        return des

    def get_areaconocimiento_dis(self, obj):
        if obj and obj.areaconocimiento:
            campo_seria = obj.areaconocimiento.all()
            return AreaConocimientoTitulacionSerializer(campo_seria, many=True).data if campo_seria.exists() else []


    def get_subareaconocimiento_dis(self,obj):
        if obj and obj.subareaconocimiento:
            campo_seria = obj.subareaconocimiento.all()
            return SubAreaConocimientoTitulacionSerializer(campo_seria, many=True).data if campo_seria.exists() else []

    def get_subareaespecificaconocimiento_dis(self, obj):
        if obj and obj.subareaespecificaconocimiento:
            campo_seria = obj.subareaespecificaconocimiento.all()
            return SubAreaEspecificaConocimientoTitulacionSerializer(campo_seria, many=True).data if campo_seria.exists() else []


    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None


class AreaTituloSerializer(Helper_ModelSerializer):
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = AreaTitulo
        fields = '__all__'

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None


class TitulacionSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    titulo = TituloSerializer()
    archivo_download = serializers.SerializerMethodField()
    registroarchivo_download = serializers.SerializerMethodField()
    institucion = InstitucionEducacionSuperiorSerializer()
    colegio = ColegioSerializer()
    areatitulo = AreaTituloSerializer()
    tipobeca_display = serializers.SerializerMethodField()
    financiamientobeca_disp = serializers.SerializerMethodField()
    personaaprobaciontitulo_disp = serializers.SerializerMethodField()
    pais = PaisSerializer()
    provincia = ProvinciaSerializer()
    canton = CantonSerializer()
    parroquia= ParroquiaSerializer()
    pais_des = serializers.SerializerMethodField()
    provincia_des = serializers.SerializerMethodField()
    canton_des = serializers.SerializerMethodField()
    parroquia_des = serializers.SerializerMethodField()



    class Meta:
            model = Titulacion
            fields = '__all__'

    def get_idm(self, obj):
        return obj.id

    def get_archivo_download(self, obj):
        if obj.archivo:
            return self.get_media_url(obj.archivo.url)
        return None

    def get_registroarchivo_download(self, obj):
        if obj.registroarchivo:
            return self.get_media_url(obj.registroarchivo.url)
        return None

    def get_tipobeca_display(self, obj):
        display = None
        if obj and obj.tipobeca:
            display = obj.tipobeca.get_display()
        return display

    def get_financiamientobeca_disp(self, obj):
        dis = None
        if obj and obj.financiamientobeca:
            dis = obj.financiamientobeca.nombre

    def get_personaaprobaciontitulo_disp(self, obj):
        dis = None
        if obj and obj.personaaprobaciontitulo:
            dis = obj.personaaprobaciontitulo.nombre_completo()

    def get_pais_des(self, obj):
        des = None
        if obj and obj.pais:
            des = obj.pais.nombre
        return des

    def get_provincia_des(self, obj):
        des = None
        if obj and obj.provincia:
            des = obj.provincia.nombre
        return des

    def get_canton_des(self, obj):
        des = None
        if obj and obj.canton:
            des = obj.canton.nombre
        return des

    def get_parroquia_des(self, obj):
        des = None
        if obj and obj.parroquia:
            des = obj.parroquia.nombre
        return des

class OperadoraMovilSerializer(Helper_ModelSerializer):
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = OperadoraMovil
        fields = '__all__'

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None


class HojaVidaPersonaSerializer(PersonaBaseSerializer):

    sexo_display = serializers.SerializerMethodField()
    sangre = TipoSangreSerializer()
    estado_civil = PersonaEstadoCivilSerializer()
    estado_civil_display = serializers.SerializerMethodField()
    #documentos_personales = serializers.SerializerMethodField()
    #situacion_laboral = serializers.SerializerMethodField()

    mis_titulos = serializers.SerializerMethodField()
    nivel_titulo = serializers.SerializerMethodField()

    #titulacion = serializers.SerializerMethodField()

    paisnacimiento = PaisSerializer()
    provincianacimiento = ProvinciaSerializer()
    cantonnacimiento = CantonSerializer()
    parroquianacimiento = ParroquiaSerializer()
    pais = PaisSerializer()
    provincia = ProvinciaSerializer()
    canton = CantonSerializer()
    parroquia = ParroquiaSerializer()
    download_croquis = serializers.SerializerMethodField()
    download_planilla = serializers.SerializerMethodField()



    class Meta:
        model = Persona
        fields = '__all__'

    def get_sexo_display(self, obj):
        return obj.sexo.nombre

    def get_estado_civil_display (self, obj):
        estadoCivil = obj.estado_civil()
        return estadoCivil.nombre if estadoCivil else None

    def get_nivel_titulo(self, obj):

        idtitulaciones = Titulacion.objects.filter(status=True, persona=obj).values_list('titulo__nivel__id')
        nivelTitulo = NivelTitulacion.objects.filter(status=True, id__in=idtitulaciones)
        return NivelTitulacionSerializer(nivelTitulo, many=True).data if nivelTitulo.exists() else []


    def get_mis_titulos(self, obj):
        if Titulacion.objects.filter(persona=obj, status=True).exists():
            titulos = Titulacion.objects.filter(persona=obj, status=True)
            return TitulacionSerializer(titulos, many=True).data
        return None

    def get_titulacion(self, obj):
        titulaciones = []
        from sga.templatetags.sga_extras import encrypt
        niveles = self.get_nivel_titulo(obj)
        for nivel in niveles:
            titulos = Titulo.objects.filter(nivel_id=int(encrypt(nivel['id'])))
            for titulo in titulos:
                titulacion = Titulacion.objects.filter(titulo=titulo, persona=obj)
                if titulacion:
                    titulaciones.append(titulacion)
        return titulaciones

    def get_download_croquis(self, obj):
        if obj.archivocroquis:
            return self.get_media_url(obj.archivocroquis.url)
        return None

    def get_download_planilla(self, obj):
        if obj.archivoplanillaluz:
            return self.get_media_url(obj.archivoplanillaluz.url)
        return None

    # def get_documentos_personales(self, obj):
    #     if obj.personadocumentopersonal_set.values("id").exists():
    #         return obj.personadocumentopersonal_set.all()[0]
    #     return None

    # def get_situacion_laboral(self, obj):
    #     return obj.personasituacionlaboral_set.filter(status=True).first()


class PersonaDocumentoPersonalSerializer(Helper_ModelSerializer):
    download_cedula = serializers.SerializerMethodField()
    download_libreta = serializers.SerializerMethodField()
    download_votacion =  serializers.SerializerMethodField()
    download_tiposangre = serializers.SerializerMethodField()

    class Meta:
        model = PersonaDocumentoPersonal
        fields = '__all__'

    def get_download_cedula(self, obj):
        if obj.cedula:
            return self.get_media_url(obj.cedula.url)
        return None

    def get_download_libreta(self, obj):
        if obj.libretamilitar:
            return self.get_media_url(obj.libretamilitar.url)
        return None
    def get_download_votacion(self, obj):
        if obj.papeleta:
            return self.get_media_url(obj.papeleta.url)
        return None

    def get_download_tiposangre(self, obj):
        if obj.tiposangre:
            return self.get_media_url(obj.tiposangre.url)
        return None

class ParentescoPersonaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()
    class Meta:
        model = ParentescoPersona
        fields = '__all__'

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None


class PersonaExtensionSerializer(Helper_ModelSerializer):
    persona = HojaVidaPersonaSerializer()
    parentescoemergencia = ParentescoPersonaSerializer()
    class Meta:
        model = PersonaExtension
        fields = '__all__'
class RazaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = Raza
        fields = '__all__'

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class NacionalidadIndigenaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()
    class Meta:
        model = NacionalidadIndigena
        fields = '__all__'

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class TipoDiscapacidadSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = Discapacidad
        fields = '__all__'
    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class SubTipoDiscapacidadSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()
    #discapacidad = TipoDiscapacidadSerializer()

    class Meta:
        model = SubTipoDiscapacidad
        fields = '__all__'

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class InstitucionBecaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = InstitucionBeca
        fields = '__all__'

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class NivelTitulacionSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()
    class Meta:
        model = NivelTitulacion
        fields = '__all__'

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class FormaTrabajoSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = FormaTrabajo
        fields = '__all__'

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class PersonaDatosFamiliaresSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    parentesco = ParentescoPersonaSerializer()
    download_cedulaidentidad = serializers.SerializerMethodField()
    download_ceduladiscapacidad = serializers.SerializerMethodField()
    obtener_edad = serializers.SerializerMethodField()
    lista_telefonos = serializers.SerializerMethodField()
    niveltitulacion = NivelTitulacionSerializer()
    formatrabajo = FormaTrabajoSerializer()

    class Meta:
        model = PersonaDatosFamiliares
        fields = '__all__'

    def get_idm(self, obj):
        return obj.id
    def get_lista_telefonos(self, obj):
        lista = []
        if obj.telefono:
            lista.append(obj.telefono)
        if obj.telefono_conv:
            lista.append(obj.telefono_conv)
        return lista

    def get_obtener_edad(self, obj):
        if obj.nacimiento:
            return int((datetime.now().date() - obj.nacimiento).days / 365.25)
        else:
            return 0

    def get_download_cedulaidentidad(self, obj):
        if obj.cedulaidentidad :
            return self.get_media_url(obj.cedulaidentidad.url)
        return None

    def get_download_ceduladiscapacidad(self, obj):
        if obj.ceduladiscapacidad:
            return self.get_media_url(obj.ceduladiscapacidad.url)
        return None



class InscripcionSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model = Inscripcion
        fields = ('idm', )

    def get_idm(self, obj):
        return obj.id

class PerfilInscripcionSerializer(Helper_ModelSerializer):
    raza = RazaSerializer()
    nacionalidadindigena = NacionalidadIndigenaSerializer()
    tipodiscapacidad = TipoDiscapacidadSerializer()
    institucionvalida = InstitucionBecaSerializer()
    download_link = serializers.SerializerMethodField()

    class Meta:
        model = PerfilInscripcion
        fields = '__all__'

    def get_download_link(self, obj):
        if obj.archivoraza:
            return self.get_media_url(obj.archivoraza.url)

class PersonaSituacionLaboralSerializer(Helper_ModelSerializer):

    class Meta:
        model = PersonaSituacionLaboral
        fields = '__all__'


class TipoArchivoSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = TipoArchivo
        fields = '__all__'

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class ArchivoSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    tipo = TipoArchivoSerializer()
    download_link = serializers.SerializerMethodField()

    class Meta:
        model = Archivo
        fields ='__all__'

    def get_idm(self, obj):
        return obj.id
    def get_download_link(self, obj):
        if obj.archivo:
            return self.get_media_url(obj.archivo.url)
        return None

class BancoSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = Banco
        fields= '__all__'

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class TipoCuentaBancoSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = TipoCuentaBanco
        fields = '__all__'

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class CuentaBancariaPersonaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    banco = BancoSerializer()
    tipocuentabanco = TipoCuentaBancoSerializer()
    download_link = serializers.SerializerMethodField()

    class Meta:
        model = CuentaBancariaPersona
        fields = '__all__'

    def get_idm(self, obj):
        return obj.id

    def get_download_link(self, obj):
        if obj.archivo:
            return self.get_media_url(obj.archivo.url)
        return None

class PersonaSangreSerializer(Helper_ModelSerializer):
    sangre = TipoSangreSerializer()

    class Meta:
        model = Persona
        fields= ('sangre',)

class TipoEnfermedadSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model = TipoEnfermedad
        fields = '__all__'

    def get_idm(self, obj):
        return obj.id

class EnfermedadSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    tipo = TipoEnfermedadSerializer()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = Enfermedad
        fields = '__all__'

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.descripcion if obj and obj.descripcion else None

class PersonaEnfermedadSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    enfermedad = EnfermedadSerializer()

    download_link = serializers.SerializerMethodField()
    class Meta:
        model = PersonaEnfermedad
        fields = '__all__'

    def get_idm(self, obj):
        return obj.id

    def get_download_link(self, obj):
        if obj.archivomedico:
            return self.get_media_url(obj.archivomedico.url)
        return None


class TipoVacunaCovidSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = TipoVacunaCovid
        fields = '__all__'

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self,obj):
        return obj.nombre if obj and obj.nombre else None

class VacunaCovidDosisSerializer(Helper_ModelSerializer):
    fechadosis = serializers.SerializerMethodField()
    class Meta:
        model= VacunaCovidDosis
        fields = '__all__'

    def get_fechadosis(self, obj):
        return obj.fechadosis.date()

class VacunaCovidSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    tipovacuna = TipoVacunaCovidSerializer()
    certificado_download = serializers.SerializerMethodField()
    dosis = serializers.SerializerMethodField()
    total_dosis = serializers.SerializerMethodField()

    class Meta:
        model = VacunaCovid
        fields= '__all__'

    def get_idm(self, obj):
        return obj.id
    def get_certificado_download(self, obj):
        if obj.certificado:
            return self.get_media_url(obj.certificado.url)
        return None

    def get_dosis(self, obj):
        dosis = obj.dosis()
        return VacunaCovidDosisSerializer(dosis, many=True).data if dosis.exists() else []

    def get_total_dosis(self, obj):
        return obj.total_dosis()

class TipoCursoSerializer(Helper_ModelSerializer):
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = TipoCurso
        fields = '__all__'

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None


class TipoCertificacionSerializer(Helper_ModelSerializer):
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = TipoCertificacion
        fields = '__all__'

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class TipoParticipacionSerializer(Helper_ModelSerializer):
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = TipoParticipacion
        fields = '__all__'

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class TipoCapacitacionSerializer(Helper_ModelSerializer):
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = TipoCapacitacion
        fields = '__all__'

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None


class ContextoCapacitacionSerializer(Helper_ModelSerializer):
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = ContextoCapacitacion
        fields = '__all__'

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class DetalleContextoCapacitacionSerializer(Helper_ModelSerializer):
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = DetalleContextoCapacitacion
        fields = '__all__'

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None



class CapacitacionSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    #tipo_display = serializers.SerializerMethodField()
    tipocurso = TipoCursoSerializer()
    tipocertificacion = TipoCertificacionSerializer()
    tipoparticipacion = TipoParticipacionSerializer()
    tipocapacitacion = TipoCapacitacionSerializer()
    contextocapacitacion = ContextoCapacitacionSerializer()
    detallecontextocapacitacion = DetalleContextoCapacitacionSerializer()
    archivo_download_link = serializers.SerializerMethodField()
    areaconocimiento = AreaConocimientoTitulacionSerializer()
    subareaconocimiento = SubAreaConocimientoTitulacionSerializer()
    subareaespecificaconocimiento = SubAreaEspecificaConocimientoTitulacionSerializer()
    contextocapacitacion_des = serializers.SerializerMethodField()
    detallecontextocapacitacion_des = serializers.SerializerMethodField()
    pais = PaisSerializer()
    provincia = ProvinciaSerializer()
    canton = CantonSerializer()
    parroquia = ParroquiaSerializer()
    pais_des = serializers.SerializerMethodField()
    provincia_des = serializers.SerializerMethodField()
    canton_des = serializers.SerializerMethodField()
    parroquia_des = serializers.SerializerMethodField()
    personaaprobacioncapacitacion_des = serializers.SerializerMethodField()
    tienecapacitacioncronograma =serializers.SerializerMethodField()

    

    class Meta:
        model = Capacitacion
        fields = '__all__'

    def get_idm(self,obj):
        return obj.id

    def get_archivo_download_link(self, obj):
        if obj.archivo:
            return self.get_media_url(obj.archivo.url)
        return None

    # def get_tipo_display(self, obj):
    #     display = None
    #     if obj and obj.tipo:
    #         display = obj.tipo.get_display()
    #     return display

    def get_contextocapacitacion_des(self, obj):
        nom = None
        if obj.contextocapacitacion:
            nom = obj.contextocapacitacion.nombre
            return nom

    def get_detallecontextocapacitacion_des(self, obj):
        nom = None
        if obj.detallecontextocapacitacion:
            nom = obj.detallecontextocapacitacion.nombre
            return nom
    def get_pais_des(self, obj):
        des = None
        if obj and obj.pais:
            des = obj.pais.nombre
        return des

    def get_provincia_des(self, obj):
        des = None
        if obj and obj.provincia:
            des = obj.provincia.nombre
        return des

    def get_canton_des(self, obj):
        des = None
        if obj and obj.canton:
            des = obj.canton.nombre
        return des

    def get_parroquia_des(self, obj):
        des = None
        if obj and obj.parroquia:
            des = obj.parroquia.nombre
        return des

    def get_personaaprobacioncapacitacion_des(self, obj):
        if obj.personaaprobacioncapacitacion:
            return obj.personaaprobacioncapacitacion.nombre_completo()
        return None

    def get_tienecapacitacioncronograma(self, obj):
        return obj.planificarcapacitaciones_set.filter(status=True)

class IdiomaSerializer(Helper_ModelSerializer):
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = Idioma
        fields = '__all__'

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class InstitucionCertificadoraSerializer(Helper_ModelSerializer):
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
            model = InstitucionCertificadora
            fields ='__all__'

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class NivelSuficenciaSerializer(Helper_ModelSerializer):
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = NivelSuficencia
        fields= '__all__'

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.descripcion if obj and obj.descripcion else None


class CertificadoIdiomaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    idioma = IdiomaSerializer()
    institucioncerti = InstitucionCertificadoraSerializer()
    nivelsuficencia = NivelSuficenciaSerializer()
    archivo_download = serializers.SerializerMethodField()


    class Meta:
        model = CertificadoIdioma
        fields= '__all__'


    def get_idm(self, obj):
        return obj.id

    def get_archivo_download(self, obj):
        if obj.archivo:
            return self.get_media_url(obj.archivo.url)
        return None


class CertificadoPersonaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    archivo_download = serializers.SerializerMethodField()

    class Meta:
        model = CertificacionPersona
        fields= '__all__'


    def get_idm(self, obj):
        return obj.id

    def get_archivo_download(self, obj):
        if obj.archivo:
            return self.get_media_url(obj.archivo.url)
        return None

class MotivoSalidaSerializer(Helper_ModelSerializer):
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()
    class Meta:
        model = MotivoSalida
        fields = '__all__'

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class OtroRegimenLaboralSerializer(Helper_ModelSerializer):
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = OtroRegimenLaboral
        fields = '__all__'

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class DedicacionLaboralSerializer(Helper_ModelSerializer):
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = DedicacionLaboral
        fields = '__all__'

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class ActividadLaboralSerializer(Helper_ModelSerializer):
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = ActividadLaboral
        fields = '__all__'

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None



class ExperienciaLaboralSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    pais =PaisSerializer()
    provincia = ProvinciaSerializer()
    canton = CantonSerializer()
    parroquia = ParroquiaSerializer()
    motivosalida = MotivoSalidaSerializer()
    motivosalida_dis = serializers.SerializerMethodField()
    regimenlaboral = OtroRegimenLaboralSerializer()
    regimenlaboral_dis = serializers.SerializerMethodField()
    dedicacionlaboral = DedicacionLaboralSerializer()
    dedicacionlaboral_dis = serializers.SerializerMethodField()
    actividadlaboral = ActividadLaboralSerializer()
    actividadlaboral_dis = serializers.SerializerMethodField()
    archivo_download = serializers.SerializerMethodField()
    rep_tipoinstitucion = serializers.SerializerMethodField()

    class Meta:
        model = ExperienciaLaboral
        fields = '__all__'

    def get_idm(self, obj):
        return obj.id

    def get_motivosalida_dis(self, obj):
        if obj and obj.motivosalida:
            return obj.motivosalida.nombre
        return None

    def get_regimenlaboral_dis(self, obj):
        if obj and obj.regimenlaboral:
            return obj.regimenlaboral.nombre
        return None

    def get_dedicacionlaboral_dis(self,obj):
        if obj and obj.dedicacionlaboral:
            return obj.dedicacionlaboral.nombre
        return None

    def get_actividadlaboral_dis(self, obj):
        if obj and obj.actividadlaboral:
            return obj.actividadlaboral.nombre
        return None

    def get_archivo_download(self, obj):
        if obj.archivo:
            return self.get_media_url(obj.archivo.url)
        return None

    def get_rep_tipoinstitucion(self, obj):
        return obj.rep_tipoinstitucion()

class OtroMeritoSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    archivo_download = serializers.SerializerMethodField()
    class Meta:
        model = OtroMerito
        fields= '__all__'

    def get_idm(self, obj):
        return obj.id

    def get_archivo_download(self, obj):
        if obj.archivo:
            return self.get_media_url(obj.archivo.url)
        return None


class RelacionSerializer(Helper_ModelSerializer):
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = Relacion
        fields = '__all__'

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class ReferenciaPersonaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    nombre_completo = serializers.SerializerMethodField()
    relacion = RelacionSerializer()

    class Meta:
        model= ReferenciaPersona
        fields='__all__'

    def get_idm(self, obj):
        return obj.id

    def get_nombre_completo(self, obj):
        if obj.nombres and obj.apellidos:
            return '%s %s' % (obj.nombres, obj.apellidos)

class BecaPersonaSerializer(Helper_ModelSerializer):
    institucion = InstitucionBecaSerializer()
    class Meta:
        model = BecaPersona
        fields = '__all__'


class MigrantePersonaSerializer(Helper_ModelSerializer):
    paisresidencia = PaisSerializer()
    paisresidencia_dis = serializers.SerializerMethodField()
    download_link = serializers.SerializerMethodField()
    class Meta:
        model= MigrantePersona
        fields = '__all__'

    def get_paisresidencia_dis(self, obj):
        if obj and obj.paisresidencia:
            return obj.paisresidencia.nombre
        return None

    def get_download_link(self, obj):
        if obj.archivo:
            return self.get_media_url(obj.archivo.url)
        return None

class CampoArtisticoSerializer(Helper_ModelSerializer):
    value= serializers.SerializerMethodField()
    label= serializers.SerializerMethodField()

    class Meta:
        model= CampoArtistico
        fields= '__all__'

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.descripcion if obj and obj.descripcion else None

class ArtistaPersonaSerializer(Helper_ModelSerializer):
    #campoartistico = CampoArtisticoSerializer()
    #estadoarchivo = serializers.SerializerMethodField()
    campoartistico_dis = serializers.SerializerMethodField()
    download_link = serializers.SerializerMethodField()
    class Meta:
        model= ArtistaPersona
        fields= '__all__'

    def get_campoartistico_dis(self,obj):
        if obj and obj.campoartistico:
            campo_seria =  obj.campoartistico.all()
            return CampoArtisticoSerializer(campo_seria,many=True).data if campo_seria.exists() else []

    def get_download_link(self, obj):
        if obj.archivo:
            return self.get_media_url(obj.archivo.url)
        return None

class DisciplinaDeportivaSerializer(Helper_ModelSerializer):
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = DisciplinaDeportiva
        fields = '__all__'

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.descripcion if obj and obj.descripcion else None


class DeportistaPersonaSerializer(Helper_ModelSerializer):
    disciplinas_dis = serializers.SerializerMethodField()
    download_link_entrena = serializers.SerializerMethodField()
    download_link_evento = serializers.SerializerMethodField()
    paisevento  = PaisSerializer()
    pais_dis = serializers.SerializerMethodField()

    class Meta:
        model = DeportistaPersona
        fields= '__all__'

    def get_disciplinas_dis(self,obj):
        if obj and obj.disciplina:
            campo_seria =  obj.disciplina.all()
            return DisciplinaDeportivaSerializer(campo_seria,many=True).data if campo_seria.exists() else []


    def get_download_link_entrena(self, obj):
        if obj.archivoentrena:
            return self.get_media_url(obj.archivoentrena.url)
        return None

    def get_download_link_evento(self, obj):
        if obj.archivoevento:
            return self.get_media_url(obj.archivoevento.url)
        return None

    def get_pais_dis(self, obj):
        if obj and obj.paisevento:
            return obj.paisevento.nombre
        return None