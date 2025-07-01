# coding=utf-8
import json
from datetime import datetime

from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.hojadevida import HojaVidaPersonaSerializer
from api.serializers.alumno.procesoelectoral import SedesElectoralesPeriodoSerializer, CabPadronElectoralSerializer, \
    PersonaSerializer
from sga.funciones import variable_valor, log
from sga.models import Inscripcion, Persona, PerfilUsuario, CabPadronElectoral, Matricula, DetPersonaPadronElectoral
from sga.templatetags.sga_extras import encrypt
from django.core.cache import cache

from voto.models import SedesElectoralesPeriodo, PersonasSede


class SedeElectoralAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = None

    @api_security
    def post(self, request):
        TIEMPO_ENCACHE = 60 * 60 * 60
        try:
            ahora = datetime.now()
            fecha_fin_cache = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
            tiempo_cache = fecha_fin_cache - ahora
            TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())

            payload = request.auth.payload
            ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
            eInscripcionEnCache = cache.get(f"inscripcion_id_{payload['inscripcion']['id']}")
            if eInscripcionEnCache:
                eInscripcion = eInscripcionEnCache
            else:
                if not Inscripcion.objects.db_manager("sga_select").values("id").filter(pk=encrypt(payload['inscripcion']['id'])).exists():
                    raise NameError(u"Inscripción no válida")
                eInscripcion = Inscripcion.objects.db_manager("sga_select").get(pk=encrypt(payload['inscripcion']['id']))
                cache.set(f"inscripcion_id_{payload['inscripcion']['id']}", eInscripcion, TIEMPO_ENCACHE)
            ePersona = eInscripcion.persona
            ver_modal = False
            ubirecomendada =None
            listadosedes= None
            data = {}
            obligatoria = False
            obligatoria = variable_valor('PROCESO_ELECTORAL_SEDE_OBLIGATORIO')

            if variable_valor('PROCESO_ELECTORAL'):
                if not cache.has_key(f"data_seleccion_sede_electoral_id_{encrypt(ePersona.pk)}_serializer_data"):
                    padronelectoral = CabPadronElectoral.objects.filter(activo=True, status=True).first()
                    eDetPersonaPadronElectoral = DetPersonaPadronElectoral.objects.filter(status=True, persona=ePersona, cab=padronelectoral,tipo= 1)
                    if eDetPersonaPadronElectoral.exists():
                        if not PersonasSede.objects.filter(status=True,persona = ePersona,sede__periodo = padronelectoral).exists():
                            ver_modal = True
                            if ePersona.canton:
                                if SedesElectoralesPeriodo.objects.filter(status=True, periodo=padronelectoral).filter(provincias__in=[ePersona.canton.provincia]).exists():
                                    ubirecomendada = SedesElectoralesPeriodo.objects.filter(status=True,periodo=padronelectoral).filter(provincias__in=[ePersona.canton.provincia]).first()
                            listadosedes = SedesElectoralesPeriodo.objects.filter(status=True, periodo=padronelectoral).order_by('canton__provincia__nombre')

                    listadosedes_serializer = SedesElectoralesPeriodoSerializer(listadosedes, many=True)
                    padronelectoral_serializer = CabPadronElectoralSerializer(padronelectoral)
                    ubirecomendada_serializer = SedesElectoralesPeriodoSerializer(ubirecomendada)
                    persona_serializer = PersonaSerializer(ePersona)

                    data = {
                        'ver_modal': ver_modal,
                        'obligatoria': obligatoria,
                        'ubirecomendada': ubirecomendada_serializer.data if ubirecomendada else None,
                        'padronelectoral': padronelectoral_serializer.data if padronelectoral else None,
                        'listadosedes': listadosedes_serializer.data if listadosedes else None,
                        'persona': persona_serializer.data if ePersona else None,
                    }
                    cache.set(f"data_seleccion_sede_electoral_id_{encrypt(ePersona.pk)}_serializer_data", data, TIEMPO_ENCACHE)
                else:
                    data = cache.get(f"data_seleccion_sede_electoral_id_{encrypt(ePersona.pk)}_serializer_data")





            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

class SaveSedeElectoralAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = None

    @api_security
    def post(self, request):
        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
            eFiles = request._request.FILES
        else:
            eRequest = request.data

        TIEMPO_ENCACHE = 60 * 60 * 60
        with transaction.atomic():
            try:
                hoy = datetime.now()
                payload = request.auth.payload
                ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
                es_estudiante = ePerfilUsuario.es_estudiante()
                if not ePerfilUsuario.es_estudiante():
                    raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                action = None
                persona = ePerfilUsuario.persona
                eInscripcion = ePerfilUsuario.inscripcion
                mensaje = ''

                if eRequest['id']:
                    idsede = int(eRequest['id'])
                    idperiodoelectoral = int(eRequest['periodoelectoral'])
                    if es_estudiante:
                        if idsede > 0:
                            periodoelectoral = CabPadronElectoral.objects.get(pk=idperiodoelectoral)
                            sedeelectoral = SedesElectoralesPeriodo.objects.get(pk=idsede)
                            getmatricula = Matricula.objects.select_related('inscripcion').filter(status=True,
                                                                                                  inscripcion__persona=persona,
                                                                                                  nivel__periodo=periodoelectoral.periodo,
                                                                                                  cerrada=False).first()
                            padronelectoral = CabPadronElectoral.objects.filter(activo=True, status=True).first()

                            if not PersonasSede.objects.filter(status=True,persona = persona,sede__periodo = padronelectoral).exists():
                                persede = PersonasSede(persona=persona,
                                                       sede=sedeelectoral,
                                                       canton=persona.canton,
                                                       perfil=ePerfilUsuario,
                                                       matricula=getmatricula,
                                                       inscripcion=eInscripcion)
                                persede.save(request)
                                log(u'Confirmo Lugar de Votación: %s' % (persede), request, "add")
                                mensaje = 'LUGAR DE VOTACIÓN CONFIRMADO\n CANTÓN: {}\n PROVINCIA: {}'.format( sedeelectoral.canton.nombre, sedeelectoral.canton.provincia.nombre)
                            else:
                                ePersonasSede = PersonasSede.objects.filter(status=True, persona=persona,sede__periodo = padronelectoral).first()
                                ePersonasSede.delete_cache()
                                # raise NameError("Usted ya se encuentra inscrito en una sede.")

                        else:
                            raise NameError("Debe seleccionar un lugar de votación")
                    else:
                        raise NameError("Su perfil actual debe ser de estudiante")
                else:
                    raise NameError("Debe seleccionar un lugar de votación")

                data = {
                    'mensaje': mensaje,
                }


                return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
            except Exception as ex:
                transaction.set_rollback(True)
                return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
