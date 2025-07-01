# coding=utf-8
from datetime import datetime

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from sga.models import Inscripcion, SagResultadoEncuesta, MateriaAsignada, SagPeriodo
from sga.templatetags.sga_extras import encrypt
from django.core.cache import cache


class EncuestaEgresadoAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = None

    @api_security
    def post(self, request):
        TIEMPO_ENCACHE = 60 * 60 * 60
        try:
            hoy = datetime.now()
            payload = request.auth.payload
            eInscripcionEnCache = cache.get(f"inscripcion_id_{payload['inscripcion']['id']}")
            if eInscripcionEnCache:
                eInscripcion = eInscripcionEnCache
            else:
                if not Inscripcion.objects.db_manager("sga_select").values("id").filter(pk=encrypt(payload['inscripcion']['id'])).exists():
                    raise NameError(u"Inscripción no válida")
                eInscripcion = Inscripcion.objects.db_manager("sga_select").get(pk=encrypt(payload['inscripcion']['id']))
                cache.set(f"inscripcion_id_{payload['inscripcion']['id']}", eInscripcion, TIEMPO_ENCACHE)
            # ePersona = eInscripcion.persona

            eEncuestas_x_contestar = []
            eEncuestas_x_contetsar_EnCache = cache.get(f"encuestaegresado_por_contestar_alumnos_panel_{encrypt(eInscripcion.id)}") if cache.get(f"encuestaegresado_por_contestar_alumnos_panel_{encrypt(eInscripcion.id)}") else None
            if not eEncuestas_x_contetsar_EnCache is None:
                eEncuestas_x_contestar = eEncuestas_x_contetsar_EnCache
            else:
                eEncuestas_x_contestar = [{"id": 1, "pendiente": False}]
                if SagPeriodo.objects.values("id").filter(primeravez=True, estado=True, status=True).exists():
                    if not SagResultadoEncuesta.objects.values("id").filter(inscripcion=eInscripcion, status=True).exists():
                        if eInscripcion.mi_malla():
                            mimalla = eInscripcion.mi_malla()
                            ultimonivel = mimalla.ultimo_nivel_malla()
                            if MateriaAsignada.objects.values("id").filter(matricula__inscripcion_id=eInscripcion.id, materia__asignaturamalla__nivelmalla=ultimonivel, status=True).exists():
                                periodoalumno = MateriaAsignada.objects.filter(matricula__inscripcion_id=eInscripcion.id, materia__asignaturamalla__nivelmalla=ultimonivel, status=True)[0].materia.nivel.periodo
                                if SagPeriodo.objects.values("id").filter(primeravez=True, estado=True,fechainicio__lte=periodoalumno.inicio ,fechafin__gte=periodoalumno.inicio, status=True).exists():
                                    eEncuestas_x_contestar = [{"id": 1, "pendiente": True}]
                cache.set(f"encuestaegresado_por_contestar_alumnos_panel_{encrypt(eInscripcion.id)}", eEncuestas_x_contestar, TIEMPO_ENCACHE)

            data = {
                'eQuizzesEgre_to_answer': eEncuestas_x_contestar, # encuestas por contestar
            }
            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
