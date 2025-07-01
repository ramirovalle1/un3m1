from rest_framework import serializers

from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.serializers.alumno.hojadevida import CantonSerializer
from api.serializers.base.persona import PersonaBaseSerializer
from sagest.models import Bloque
from sga.models import CabPadronElectoral, SolicitudInformacionPadronElectoral, DetPersonaPadronElectoral, Periodo, \
    Persona, Modalidad, Carrera, Inscripcion, Matricula, MesasPadronElectoral, TipoSolicitudInformacionPadronElectoral, \
    JustificacionPersonaPadronElectoral, HistorialJustificacionPersonaPadronElectoral
from voto.models import ConfiguracionMesaResponsable, SedesElectoralesPeriodo

def current_date_format(date):
    months = ("Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre")
    days = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")
    day_of_week = days[int(date.strftime("%w")) - 1]
    day = date.day
    month = months[date.month - 1]
    year = date.year
    return "{}, {} de {} del {}".format(day_of_week, day, month, year)

class BloqueSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    class Meta:
        model = Bloque
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk

class PersonaSerializer(PersonaBaseSerializer):
    pk = serializers.SerializerMethodField()
    class Meta:
        model = Persona
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk

class ModalidadSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    class Meta:
        model = Modalidad
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk

class CarreraSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    class Meta:
        model = Carrera
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk

class MatriculaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
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
    #inscripcion = InscripcionSerializer()

    class Meta:
        model = Matricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_nombre_completo(self, obj):
        return obj.inscripcion.persona.nombre_completo()

    def get_documento(self, obj):
        return obj.inscripcion.persona.documento()

    def get_tipo_documento(self, obj):
        return obj.inscripcion.persona.tipo_documento()

    def get_foto(self, obj):
        persona = obj.inscripcion.persona
        if persona.tiene_foto():
            return self.get_media_url(persona.foto().foto.url)
        if persona.sexo and persona.sexo.id == 1:
            foto_perfil = '/static/images/iconos/mujer.png'
        else:
            foto_perfil = '/static/images/iconos/hombre.png'
        return self.get_static_url(foto_perfil)

    def get_tiene_foto(self, obj):
        return obj.inscripcion.persona.tiene_foto()

    def get_ciudad(self, obj):
        persona = obj.inscripcion.persona
        return persona.canton.nombre if persona.canton else None

    def get_direccion_corta(self, obj):
        persona = obj.inscripcion.persona
        return persona.direccion_corta()

    def get_tiene_otro_titulo(self, obj):
        persona = obj.inscripcion.persona
        return persona.tiene_otro_titulo()

    def get_es_mujer(self, obj):
        persona = obj.inscripcion.persona
        return persona.es_mujer()

    def get_es_hombre(self, obj):
        persona = obj.inscripcion.persona
        return persona.es_hombre()

    def get_lista_emails(self, obj):
        persona = obj.inscripcion.persona
        return persona.lista_emails_2()

    def get_carrera(self, obj):
        return obj.inscripcion.carrera.nombre

    def get_nivel(self, obj):
        inscripcion = obj.inscripcion
        return inscripcion.mi_nivel().nivel.nombre if inscripcion.mi_nivel().nivel else ''

class InscripcionSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
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
    #inscripcion = InscripcionSerializer()

    class Meta:
        model = Inscripcion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
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

class PeriodoSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = Periodo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk

class MesasPadronElectoralSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = MesasPadronElectoral
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk

class CabPadronElectoralSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    periodo = PeriodoSerializer()
    fechalimiteconfirmacionsede_letra = serializers.SerializerMethodField()

    class Meta:
        model = CabPadronElectoral
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk

    def get_fechalimiteconfirmacionsede_letra(self, obj):
        return current_date_format(obj.fechalimiteconfirmacionsede) if obj.fechalimiteconfirmacionsede else None

class TipoSolicitudInformacionPadronElectoralSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = TipoSolicitudInformacionPadronElectoral
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk

class SolicitudInformacionPadronElectoralSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    tipo = TipoSolicitudInformacionPadronElectoralSerializer()
    persona = PersonaSerializer()
    validadopor = PersonaSerializer()
    cab = CabPadronElectoralSerializer()
    estados_display = serializers.SerializerMethodField()



    class Meta:
        model = SolicitudInformacionPadronElectoral
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk

    def get_estados_display(self, obj):
        return obj.get_estados_display()


class ConfiguracionMesaResponsableSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = ConfiguracionMesaResponsable
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk

class SedesElectoralesPeriodoSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    canton= CantonSerializer()
    class Meta:
        model = SedesElectoralesPeriodo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk


class DetPersonaPadronElectoralSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    cab = CabPadronElectoralSerializer()
    persona = PersonaSerializer()
    inscripcion= InscripcionSerializer()
    matricula = MatriculaSerializer()
    bloque = BloqueSerializer()
    mesa = MesasPadronElectoralSerializer()
    mesasede = ConfiguracionMesaResponsableSerializer()
    lugarsede = SedesElectoralesPeriodoSerializer()
    tipo = serializers.SerializerMethodField()
    class Meta:
        model = DetPersonaPadronElectoral
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk

    def get_tipo(self, obj):
        return obj.get_tipo()





class JustificacionPersonaPadronElectoralSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    estado_display = serializers.SerializerMethodField()
    inscripcion = DetPersonaPadronElectoral()

    class Meta:
        model = JustificacionPersonaPadronElectoral
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk

    def get_estado_display(self, obj):
        return obj.get_estados_justificacion_display()


class HistorialJustificacionPersonaPadronElectoralSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    justificativo = JustificacionPersonaPadronElectoralSerializer()

    class Meta:
        model = HistorialJustificacionPersonaPadronElectoral
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk



