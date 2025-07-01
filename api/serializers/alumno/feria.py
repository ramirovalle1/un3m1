from rest_framework import serializers
from django.db.models import Sum, F
from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from api.serializers.base.persona import PersonaBaseSerializer
from api.serializers.base.reporte import ReporteBaseSerializer
from sga.funciones import variable_valor
from sga.models import Matricula, Inscripcion, Profesor, Carrera, Persona
from feria.models import SolicitudFeria, CronogramaFeria, ParticipanteFeria


class PersonaTutorSerializer(PersonaBaseSerializer):

    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class PersonaParticipanteSerializer(PersonaBaseSerializer):

    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class TutorSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    persona = PersonaTutorSerializer()

    class Meta:
        model = Profesor
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class CarreraSerializer(Helper_ModelSerializer):

    class Meta:
        model = Carrera
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


# class InscripcionSerializer(Helper_ModelSerializer):
#     persona = PersonaParticipanteSerializer()
#
#     class Meta:
#         model = Inscripcion
#         # fields = "__all__"
#         exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriculaSerializer(Helper_ModelSerializer):
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
    #inscripcion = InscripcionSerializer()

    class Meta:
        model = Matricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
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
    #inscripcion = InscripcionSerializer()

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


class CronogramaFeriaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    carrera = CarreraSerializer(many=True, read_only=True)

    class Meta:
        model = CronogramaFeria
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class ParticipanteFeriaSerializer(Helper_ModelSerializer):
    matricula = MatriculaSerializer()

    class Meta:
        model = ParticipanteFeria
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class SolicitudFeriaSerializer(Helper_ModelSerializer):
    cronograma = CronogramaFeriaSerializer()
    participantes = serializers.SerializerMethodField()
    certificado_participacion = serializers.SerializerMethodField()
    certificado_ganador = serializers.SerializerMethodField()
    certificado_ganadorfacultad = serializers.SerializerMethodField()
    modificarsolicitud = serializers.SerializerMethodField()
    docpropuesta = serializers.SerializerMethodField()
    tutor = TutorSerializer()

    class Meta:
        model = SolicitudFeria
        # fields = "__all__"
        exclude = ['usuario_modificacion']

    def get_participantes(self, obj):
        participantes = obj.get_participantes_inscripciones()
        return InscripcionSerializer(participantes, many=True).data if participantes.values('id').exists() else []

    def get_docpropuesta(self, obj):
        return self.get_media_url(obj.get_docpropuesta())

    def get_certificado_participacion(self, obj):
        user_id = self.context.get('user_id')
        if user_id is not None:
            participante = obj.participanteferia_set.filter(inscripcion__persona__usuario=self.context['user_id']).first()
            if participante is not None:
                if participante.certificado.name is not None and participante.certificado.name != '':
                    return self.get_media_url(participante.certificado.url)
        return None

    def get_certificado_ganador(self, obj):
        user_id = self.context.get('user_id')
        if user_id is not None:
            participante = obj.participanteferia_set.filter(inscripcion__persona__usuario=self.context['user_id']).first()
            if participante is not None:
                if participante.certificadoganador.name is not None and participante.certificadoganador.name != '':
                    return self.get_media_url(participante.certificadoganador.url)
        return None

    def get_certificado_ganadorfacultad(self, obj):
        user_id = self.context.get('user_id')
        if user_id is not None:
            participante = obj.participanteferia_set.filter(inscripcion__persona__usuario=self.context['user_id']).first()
            if participante is not None:
                if participante.certificadoganadorfacultad.name is not None and participante.certificadoganadorfacultad.name != '':
                    return self.get_media_url(participante.certificadoganadorfacultad.url)
        return None


    def get_modificarsolicitud(self, obj):
        return variable_valor('MODIFICAR_SOLICITUD_FERIA')




