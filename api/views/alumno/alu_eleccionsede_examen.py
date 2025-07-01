from datetime import datetime
from django.db import  transaction, models, connection, connections
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status

from inno.models import MatriculaSedeExamen
from sga.funciones import log, variable_valor
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from sga.models import Matricula
from api.serializers.alumno.encuesta import MatriculaSedeExamenSerializer

class SeleccionMatriculaSedeExamenAPIView(APIView):
    #permission_classes = (IsAuthenticated,)
    api_key_module = None

    @api_security
    def post(self, request,*args, **kwargs):
        with transaction.atomic():
            try:
                if 'multipart/form-data' in request.content_type:
                    eRequest = request._request.POST
                    eFiles = request._request.FILES
                else:
                    eRequest = request.data

                matricula = eRequest.get('matricula')
                sede = eRequest.get('sede')
                aceptoterminos = eRequest.get('aceptoterminos')
                detallemodeloevaluativo = eRequest.get('detallemodeloevaluativo')
                if MatriculaSedeExamen.objects.filter(matricula_id = matricula, status = True).exists():
                    sedeexamen = MatriculaSedeExamen.objects.get(matricula_id = matricula)
                    sedeexamen.sede_id = sede
                    sedeexamen.matricula_id = matricula
                    sedeexamen.aceptotermino = aceptoterminos
                    sedeexamen.detallemodeloevaluativo_id = detallemodeloevaluativo
                    sedeexamen.save()
                    print("Se edito sede")
                    log(f"Edito sede de examen :{sede}_{matricula}", request, 'edit')
                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)

                if ENCUESTA_ACTIVA_MOODLE := variable_valor('ENCUESTA_ACTIVA_MOODLE'):
                    cnmoodle = connections['aulagradob'].cursor()
                    matri_obj = Matricula.objects.get(id=matricula)
                    ins = matri_obj.inscripcion
                    usermoodle = ins.persona.usuario.username
                    if usermoodle:
                        sql = f"Select id, username From mooc_user Where username = '{usermoodle}'"
                        cnmoodle.execute(sql)
                        registro = cnmoodle.fetchall()
                        try:
                            usermoodle = registro[0][1]
                            sql = f"Update mooc_user Set suspended=0 Where username = '{usermoodle}'"
                            cnmoodle.execute(sql)
                        except Exception as ex:
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={},
                                                   message=f'Ocurrio un error: {ex.__str__()}',
                                                   status=status.HTTP_200_OK)

                matri_examen = MatriculaSedeExamen(
                    sede_id = sede,
                    matricula_id = matricula,
                    aceptotermino= aceptoterminos,
                    detallemodeloevaluativo_id= detallemodeloevaluativo
                )
                matri_examen.save(request)
                log(f"Selecciono sede de examen :{sede}_{matricula}",request,'add')
                return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)
            except Exception as ex:
                transaction.set_rollback(True)
                return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)