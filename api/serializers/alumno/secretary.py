# coding=utf-8
from datetime import timedelta, datetime

from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType

from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from api.serializers.alumno.certificado import CertificadoSerializer
from api.serializers.base.persona import PersonaBaseSerializer
from secretaria.models import Servicio, CategoriaServicio, Solicitud, HistorialSolicitud
from sagest.models import TipoOtroRubro, Rubro, Pago, ComprobanteRecaudacion, TipoComprobanteRecaudacion
from sga.models import Persona, AsignaturaMalla, Asignatura, PerfilUsuario, Inscripcion, Carrera
from rest_framework import serializers

class PagoObjectRelatedField(serializers.RelatedField):
    def to_representation(self, value):
        if isinstance(value, Pago):
            serializer = PagoSerializer(value)
            return serializer.data
        raise Exception('Unexpected type of tagged object')


class TipoOtroRubroSerializer(Helper_ModelSerializer):
    class Meta:
        model = TipoOtroRubro
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class TipoComprobanteRecaudacionSerializer(Helper_ModelSerializer):

    class Meta:
        model = TipoComprobanteRecaudacion
        fields = '__all__'

class ComprobanteRecaudacionSerializer(Helper_ModelSerializer):
    tipocomprobanterecaudacion = TipoComprobanteRecaudacionSerializer()

    class Meta:
        model = ComprobanteRecaudacion
        fields = ('tipocomprobanterecaudacion',)


class ResponsablePersona(PersonaBaseSerializer):

    class Meta:
        model = Persona
        fields = ('nombre_completo', )


class CategoriaServicioSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = CategoriaServicio
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk


class ServicioSerializer(Helper_ModelSerializer):
    categoria = CategoriaServicioSerializer()
    tiporubro = TipoOtroRubroSerializer()
    proceso_display = serializers.SerializerMethodField()

    class Meta:
        model = Servicio
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_proceso_display(self, obj):
        return obj.get_proceso_display()


class CarreraSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    nombrecarrera = serializers.SerializerMethodField()

    class Meta:
        model = Carrera
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk

    def get_nombrecarrera(self, obj):
        if obj.mencion:
            nombre = f'{obj.nombre} CON MENCIÓN EN {obj.mencion}'
        else:
            nombre = obj.nombre
        return nombre

class SolicitudSerializer(Helper_ModelSerializer):
    servicio = ServicioSerializer()
    estado_display = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    puede_eliminar = serializers.SerializerMethodField()
    color_estado_display = serializers.SerializerMethodField()
    certificado = serializers.SerializerMethodField()
    archivo_solicitud = serializers.SerializerMethodField()
    archivo_respuesta = serializers.SerializerMethodField()
    fecha_limite_pago = serializers.SerializerMethodField()
    costo2modulos = serializers.SerializerMethodField()
    maestria = serializers.SerializerMethodField()
    pk = serializers.SerializerMethodField()
    tiene_pago = serializers.SerializerMethodField()
    tiene_rubro = serializers.SerializerMethodField()
    costoredondeado = serializers.SerializerMethodField()
    obs_rechazo = serializers.SerializerMethodField()

    class Meta:
        model = Solicitud
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_estado_display(self, obj):
        return obj.get_estado_display()

    def get_total(self, obj):
        return obj.total()

    def get_puede_eliminar(self, obj):
        return obj.puede_eliminar()

    def get_color_estado_display(self, obj):
        return obj.color_estado_display()

    def get_certificado(self, obj):
        if obj.servicio.proceso in (1, 2, 8):
            eCertificado = obj.origen_content_object
            return CertificadoSerializer(eCertificado).data
        return None

    def get_archivo_solicitud(self, obj):
        return self.get_media_url(
            obj.archivo_solicitud.url) if obj.archivo_solicitud and obj.archivo_solicitud.url else None

    def get_archivo_respuesta(self, obj):
        return self.get_media_url(
            obj.archivo_respuesta.url) if obj.archivo_respuesta and obj.archivo_respuesta.url else None

    def get_fecha_limite_pago(self, obj):
        fecha_limite = datetime.combine(obj.fecha, obj.hora) + timedelta(hours=obj.tiempo_cobro)
        return fecha_limite.strftime('%Y-%m-%d - %H:%M:%S')

    def get_costo2modulos(self, obj):
        from api.views.alumno.secretary.solicitud import costo_tit_ex
        return costo_tit_ex(obj.perfil.inscripcion)

    def get_costoredondeado(self, obj):
        from decimal import Decimal
        return Decimal(obj.servicio.costo).quantize(Decimal('.01'))

    def get_maestria(self, obj):
        return obj.perfil.inscripcion.carrera.nombre

    def get_pk(self, obj):
        return obj.pk

    def get_tiene_pago(self, obj):
        estado = "NO"
        if Rubro.objects.filter(status=True, solicitud=obj, tipo=obj.servicio.tiporubro, cancelado=True).exists():
            if Pago.objects.filter(status=True, rubro__solicitud=obj, rubro__tipo=obj.servicio.tiporubro).exists():
                estado = "SI"
        return estado

    def get_tiene_rubro(self, obj):
        estado = "NO"
        if Rubro.objects.filter(status=True, solicitud=obj, tipo=obj.servicio.tiporubro).exists():
            estado = "SI"
        return estado

    def get_obs_rechazo(self, obj):
        obs = ''
        if HistorialSolicitud.objects.filter(status=True, solicitud=obj, estado=7).exists():
            obs = HistorialSolicitud.objects.filter(status=True, solicitud=obj, estado=7).first().observacion
        return obs


class PagoSerializer(Helper_ModelSerializer):
    #content_type = serializers.SerializerMethodField()
    comprobante = ComprobanteRecaudacionSerializer()
    class Meta:
        model = Pago
        fields = '__all__'

    #def get_content_type(self, obj):
    #    return ContentType.objects.get_for_model(obj)


class HistorialSolicitudSerializer(Helper_ModelSerializer):
    solicitud = SolicitudSerializer()
    responsable = ResponsablePersona()
    #destino_content_object = PagoObjectRelatedField(many=True, read_only=True)
    pago = serializers.SerializerMethodField()
    estado_display = serializers.SerializerMethodField()

    class Meta:
        model = HistorialSolicitud
        fields = '__all__'

    def get_estado_display(self, obj):
        return obj.get_estado_display()

    def get_pago(self, obj):
        ePago = obj.destino_content_object
        if ePago:
            return PagoSerializer(ePago).data
        else:
            return None

class RubroSerializer(Helper_ModelSerializer):

    class Meta:
        model = Rubro
        fields= '__all__'

class AsignaturaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = Asignatura
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk

class AsignaturaMallaSerializer(Helper_ModelSerializer):
    asignatura = AsignaturaSerializer()
    pk = serializers.SerializerMethodField()

    class Meta:
        model = AsignaturaMalla
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk

