from django.contrib.auth import authenticate
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser

from api.lookproxy.decorator import lookproxy_auth_required
from sga.funciones import bad_json, ok_json
from sga.models import Persona, Periodo, Matricula
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from rest_framework.response import Response
from rest_framework import status
from api.helpers.response_herlper import Helper_Response


class LoginLookProxyView(APIView):
    parser_class = (MultiPartParser, FormParser,)
    merchantId = '$Un3m12023'

    @lookproxy_auth_required
    def post(self, request, format=None, *args, **kwargs):
        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
            eFiles = request._request.FILES
        else:
            eRequest = request.data
        try:
            #username, password = (eRequest['username']).lower(), eRequest['password']
            emailinst = (eRequest['email']).lower()
            qsuser = User.objects.filter(email=emailinst, is_active=True)
            if qsuser.exists():
                user = qsuser.first()
                #pwd_valid = check_password(password, user.password)
                # if not pwd_valid:
                #     return Helper_Response(isSuccess=False, data={}, message=f'Contraseña incorrecta',  status=status.HTTP_200_OK)
                qspersona = Persona.objects.filter(usuario=user, status=True)
                if qspersona.exists():
                    persona_ = qspersona.first()
                    inscripcion = persona_.inscripcion_principal()
                    if inscripcion:
                        if not inscripcion.activo:
                            return Helper_Response(isSuccess=False, data={}, message=f'Perfil desabilitado',  status=status.HTTP_200_OK)
                        qsmatricula = Matricula.objects.filter(status=True, cerrada=False, inscripcion=inscripcion)
                        if qsmatricula:
                            loguser = authenticate(email=emailinst)
                            if loguser:
                                matricula_ = qsmatricula.first()
                                data_ = {'idusuario': user.id, 'nombrecompleto': f'{persona_.nombre_completo()}', 'nombres': persona_.nombres,
                                         'apellido1': persona_.apellido1, 'apellido2': persona_.apellido2,
                                         'correoinstitucional': persona_.emailinst, 'tipo': matricula_.nivel.periodo.get_clasificacion_display(),
                                         'facultad': inscripcion.coordinacion.__str__(), 'carrera': inscripcion.carrera.__str__(),
                                         'modalidad': matricula_.nivel.modalidad.__str__(), 'nivel': matricula_.nivelmalla.__str__()}
                                return Helper_Response(isSuccess=True, data=data_, message=f'',  status=status.HTTP_200_OK)
                            else:
                                return Helper_Response(isSuccess=False, data={}, message=f'Credenciales incorrectas',  status=status.HTTP_200_OK)
                        else:
                            if persona_.es_profesor():
                                loguser = authenticate(email=emailinst)
                                if loguser:
                                    data_ = {'idusuario': user.id, 'nombrecompleto': f'{persona_.nombre_completo()}', 'nombres': persona_.nombres,
                                             'apellido1': persona_.apellido1, 'apellido2': persona_.apellido2,
                                             'correoinstitucional': persona_.emailinst, 'tipo': 'DOCENTE',
                                             'facultad': 'N/A', 'carrera': 'N/A',
                                             'modalidad': 'N/A', 'nivel': 'N/A'}
                                    return Helper_Response(isSuccess=True, data=data_, message=f'', status=status.HTTP_200_OK)
                                else:
                                    return Helper_Response(isSuccess=False, data={}, message=f'Credenciales incorrectas', status=status.HTTP_200_OK)
                            elif persona_.es_administrativo():
                                loguser = authenticate(email=emailinst)
                                if loguser:
                                    data_ = {'idusuario': user.id, 'nombrecompleto': f'{persona_.nombre_completo()}', 'nombres': persona_.nombres,
                                             'apellido1': persona_.apellido1, 'apellido2': persona_.apellido2,
                                             'correoinstitucional': persona_.emailinst, 'tipo': 'ADMINISTRATIVO',
                                             'facultad': 'N/A', 'carrera': 'N/A',
                                             'modalidad': 'N/A', 'nivel': 'N/A'}
                                    return Helper_Response(isSuccess=True, data=data_, message=f'', status=status.HTTP_200_OK)
                                else:
                                    return Helper_Response(isSuccess=False, data={}, message=f'Credenciales incorrectas', status=status.HTTP_200_OK)
                            else:
                                return Helper_Response(isSuccess=False, data={}, message=f'Usted no cuenta con matrícula activa',  status=status.HTTP_200_OK)
                    else:
                        if persona_.es_profesor():
                            loguser = authenticate(email=emailinst)
                            if loguser:
                                data_ = {'idusuario': user.id, 'nombrecompleto': f'{persona_.nombre_completo()}', 'nombres': persona_.nombres,
                                         'apellido1': persona_.apellido1, 'apellido2': persona_.apellido2,
                                         'correoinstitucional': persona_.emailinst, 'tipo': 'DOCENTE',
                                         'facultad': 'N/A', 'carrera': 'N/A',
                                         'modalidad': 'N/A', 'nivel': 'N/A'}
                                return Helper_Response(isSuccess=True, data=data_, message=f'', status=status.HTTP_200_OK)
                            else:
                                return Helper_Response(isSuccess=False, data={}, message=f'Credenciales incorrectas', status=status.HTTP_200_OK)
                        elif persona_.es_administrativo():
                            loguser = authenticate(email=emailinst)
                            if loguser:
                                data_ = {'idusuario': user.id, 'nombrecompleto': f'{persona_.nombre_completo()}', 'nombres': persona_.nombres,
                                         'apellido1': persona_.apellido1, 'apellido2': persona_.apellido2,
                                         'correoinstitucional': persona_.emailinst, 'tipo': 'ADMINISTRATIVO',
                                         'facultad': 'N/A', 'carrera': 'N/A',
                                         'modalidad': 'N/A', 'nivel': 'N/A'}
                                return Helper_Response(isSuccess=True, data=data_, message=f'', status=status.HTTP_200_OK)
                            else:
                                return Helper_Response(isSuccess=False, data={}, message=f'Usted no tiene perfil estudiante',  status=status.HTTP_200_OK)
            else:
                return Helper_Response(isSuccess=False, data={}, message=f'Usuario Invalido',  status=status.HTTP_200_OK)

        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}',  status=status.HTTP_200_OK)