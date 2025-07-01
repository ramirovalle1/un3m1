from rest_framework import serializers
from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from api.serializers.base.persona import PersonaBaseSerializer
from balcon.models import Proceso, Categoria, ProcesoServicio, Informacion, Servicio, RequisitosConfiguracion, Requisito, \
    Solicitud, RequisitosSolicitud, HistorialSolicitud, EncuestaProceso, PreguntaEncuestaProceso
from certi.models import ConfiguracionCarnet, Carnet
from sagest.models import OpcionSistema
from sga.models import Matricula, Persona, Modulo


class PersonaSerializer(PersonaBaseSerializer):

    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class RequisitosSolicitudSerializer(Helper_ModelSerializer):
    descripcion = serializers.SerializerMethodField()

    class Meta:
        model = RequisitosSolicitud
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_descripcion(self, obj):
        return obj.requisito.requisito.descripcion if obj.requisito else ''


class HistorialSolicitudSerializer(Helper_ModelSerializer):
    estado_display = serializers.SerializerMethodField()
    asignaenvia = serializers.SerializerMethodField()
    asignadorecibe = serializers.SerializerMethodField()
    #proceso = serializers.SerializerMethodField()
    departamento = serializers.SerializerMethodField()
    servicio = serializers.SerializerMethodField()
    respuestarapida = serializers.SerializerMethodField()
    typefile = serializers.SerializerMethodField()

    class Meta:
        model = HistorialSolicitud
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_estado_display(self, obj):
        return obj.get_estado_display()

    def get_asignaenvia(self, obj):
        return obj.asignaenvia.__str__() if obj.asignaenvia is not None  else ''

    def get_asignadorecibe(self, obj):
        return obj.asignadorecibe.__str__() if obj.asignadorecibe is not None else ''

    # def get_proceso(self, obj):
    #     return obj.proceso.descripcion if obj.proceso is not None else ''

    def get_departamento(self, obj):
        return obj.departamento.nombre if obj.departamento is not None else ''

    def get_servicio(self, obj):
        serv = ''
        if obj.servicio is not None:
            if obj.servicio.servicio is not None:
                serv = obj.servicio.servicio.__str__()
        return serv

    def get_respuestarapida(self, obj):
        return obj.respuestarapida.__str__() if obj.respuestarapida is not None else ''

    def get_typefile(self, obj):
        return obj.typefile()


class SolicitudSerializer(Helper_ModelSerializer):
    estado_display = serializers.SerializerMethodField()
    tipo_display = serializers.SerializerMethodField()
    numero_display = serializers.SerializerMethodField()
    typefile = serializers.SerializerMethodField()
    requisitos = serializers.SerializerMethodField()
    detalle = serializers.SerializerMethodField()
    solicitante = serializers.SerializerMethodField()
    agente = serializers.SerializerMethodField()
    codigo = serializers.SerializerMethodField()
    puede_calificar_proceso = serializers.SerializerMethodField()
    urlservice = serializers.SerializerMethodField()

    class Meta:
        model = Solicitud
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_estado_display(self, obj):
        return obj.get_estado_display()

    def get_tipo_display(self, obj):
        return obj.get_tipo_display()

    def get_numero_display(self, obj):
        return f'{obj.numero}'.rjust(5, '0')

    def get_typefile(self, obj):
        return obj.typefile()

    def get_requisitos(self, obj):
        reqs = obj.requisitossolicitud_set.all()
        return RequisitosSolicitudSerializer(reqs, many=True).data if reqs.values_list('id', flat=True).exists() else []

    def get_detalle(self, obj):
        return obj.detalle()

    def get_solicitante(self, obj):
        return obj.solicitante.__str__() if obj.solicitante else ''

    def get_agente(self, obj):
        return obj.agente.__str__() if obj.agente else ''

    def get_codigo(self, obj):
        return obj.get_codigo()

    def get_puede_calificar_proceso (self, obj):
        return obj.puede_calificar_proceso()

    def get_urlservice (self, obj):
        service = obj.historialsolicitud_set.filter(status=True).first()
        return service.servicio.url if service != None else None



class ProcesoSerializer(Helper_ModelSerializer):

    class Meta:
        model = Proceso
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class ModuloSerializer(Helper_ModelSerializer):

    class Meta:
        model = Modulo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class OpcionSistemaSerializer(Helper_ModelSerializer):
    modulo = ModuloSerializer()

    class Meta:
        model = OpcionSistema
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ServicioSerializer(Helper_ModelSerializer):

    class Meta:
        model = Servicio
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class RequisitoSerializer(Helper_ModelSerializer):

    class Meta:
        model = Requisito
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class RequisitosConfiguracionSerializer(Helper_ModelSerializer):
    requisito = RequisitoSerializer()

    class Meta:
        model = RequisitosConfiguracion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ProcesoServicioSerializer(Helper_ModelSerializer):
    proceso = ProcesoSerializer()
    servicio = ServicioSerializer()
    opcsistema = OpcionSistemaSerializer()
    requisitos = serializers.SerializerMethodField()

    class Meta:
        model = ProcesoServicio
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_requisitos(self, obj):
        requisitos = obj.requisitosconfiguracion_set.filter(status=True, activo=True)
        return RequisitosConfiguracionSerializer(requisitos, many=True).data if requisitos.values_list('id', flat=True).exists() else []

class InformacionSerializer(Helper_ModelSerializer):
    servicio = ProcesoServicioSerializer()
    archivomostrar = serializers.SerializerMethodField()
    archivodescargar = serializers.SerializerMethodField()
    typefilemostrar = serializers.SerializerMethodField()
    typefiledescargar = serializers.SerializerMethodField()

    class Meta:
        model = Informacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_typefilemostrar(self, obj):
        return obj.typefilemostrar()

    def get_typefiledescargar(self, obj):
        return obj.typefiledescargar()

    def get_archivomostrar(self, obj):
        return self.get_media_url(obj.archivomostrar.url) if obj.archivomostrar.name != '' else None

    def get_archivodescargar(self, obj):
        return self.get_media_url(obj.archivodescargar.url) if obj.archivodescargar.name != '' else None

    def get_informacion(self, obj):
        path_media = self.get_media_url('/media/')
        return obj.informacion.replace('/media/', path_media)


class CategoriaSerializer(Helper_ModelSerializer):
    procesos = serializers.SerializerMethodField()

    class Meta:
        model = Categoria
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_procesos(self, obj):
        eProcesos = obj.procesos()
        return ProcesoSerializer(eProcesos, many=True).data if eProcesos.values_list('id', flat=True).exists() else []


class PreguntaEncuestaProcesoSerializer(Helper_ModelSerializer):
    configuracion = serializers.SerializerMethodField()

    class Meta:
        model = PreguntaEncuestaProceso
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_configuracion(self, obj):
        return obj.encuesta.configuracion_estrellas()

class EncuestaProcesoSerializer(Helper_ModelSerializer):
    preguntas = serializers.SerializerMethodField()

    class Meta:
        model = EncuestaProceso
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_preguntas(self, obj):
        solicitud = self.context.get('solicitud', None)
        preguntas = obj.preguntas(solicitud)
        return PreguntaEncuestaProcesoSerializer(preguntas, many=True).data if preguntas.values_list('id', flat=True).exists() else []

