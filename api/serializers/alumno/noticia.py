# coding=utf-8
from django.contrib.auth.models import User, Group
from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from sagest.models import TipoOtroRubro
from sga.models import Noticia, Archivo, NotificacionDeudaPeriodo, Periodo, Coordinacion
from rest_framework import serializers


class NoticiaSerializer(Helper_ModelSerializer):
    desde = serializers.SerializerMethodField()
    hasta = serializers.SerializerMethodField()
    imagen = serializers.SerializerMethodField()

    class Meta:
        model = Noticia
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_desde(self, obj):
        return obj.desde.strftime(DATE_FORMAT) if obj.desde else None

    def get_hasta(self, obj):
        return obj.hasta.strftime(DATE_FORMAT) if obj.hasta else None

    def get_imagen(self, obj):
        return self.get_media_url(obj.imagen.archivo.url) if obj.imagen else None


class PeriodoSerializer(Helper_ModelSerializer):

    class Meta:
        model = Periodo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class CoordinacionSerializer(Helper_ModelSerializer):

    class Meta:
        model = Coordinacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class TipoOtroRubroSerializer(Helper_ModelSerializer):

    class Meta:
        model = TipoOtroRubro
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NotificacionDeudaPeriodoSerializer(Helper_ModelSerializer):
    periodo = PeriodoSerializer()
    archivo = serializers.SerializerMethodField()
    fechainicionotificacion = serializers.SerializerMethodField()
    fechafinnotificacion = serializers.SerializerMethodField()
    coordinaciones = serializers.SerializerMethodField()
    tiposrubros = serializers.SerializerMethodField()

    class Meta:
        model = NotificacionDeudaPeriodo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_fechainicionotificacion(self, obj):
        return obj.fechafinnotificacion.strftime(DATETIME_FORMAT) if obj.fechainicionotificacion else None

    def get_fechafinnotificacion(self, obj):
        return obj.fechafinnotificacion.strftime(DATETIME_FORMAT) if obj.fechafinnotificacion else None

    def get_archivo(self, obj):
        return self.get_media_url(obj.archivo.url) if obj.archivo else None

    def get_coordinaciones(self, obj):
        eCoordinaciones = obj.coordinaciones.all()
        if eCoordinaciones.values("id").exists():
            return CoordinacionSerializer(eCoordinaciones, many=True).data
        return []

    def get_tiposrubros(self, obj):
        eTipoOtroRubros = obj.tiposrubros.all()
        if eTipoOtroRubros.values("id").exists():
            return TipoOtroRubroSerializer(eTipoOtroRubros, many=True).data
        return []



