from datetime import datetime
from django.db import transaction
from django.core.cache import cache
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.response_herlper import Helper_Response
from mobile.views import make_thumb_picture, make_thumb_fotopersona
from settings import GENERAR_TUMBAIL
from sga.funciones import generar_nombre, log
from sga.models import PerfilUsuario, Periodo, Persona
from sga.templatetags.sga_extras import encrypt


class ChangeProfileAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    def post(self, request):
        TIEMPO_ENCACHE = 60 * 15
        try:
            if 'multipart/form-data' in request.content_type:
                eRequest = request._request.POST
                eFiles = request._request.FILES
            else:
                eRequest = request.data
            hoy = datetime.now()
            payload = request.auth.payload
            if cache.has_key(f"perfilprincipal_id_{payload['perfilprincipal']['id']}"):
                ePerfilUsuario = cache.get(f"perfilprincipal_id_{payload['perfilprincipal']['id']}")
            else:
                ePerfilUsuario = PerfilUsuario.objects.db_manager("sga_select").get(pk=encrypt(payload['perfilprincipal']['id']))
                cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario, TIEMPO_ENCACHE)

            if 'id' in payload['periodo']:
                if cache.has_key(f"periodo_id_{payload['periodo']['id']}"):
                    ePeriodo = cache.get(f"periodo_id_{payload['periodo']['id']}")
                else:
                    ePeriodo = Periodo.objects.db_manager("sga_select").get(pk=encrypt(payload['periodo']['id']))
                    cache.set(f"periodo_id_{payload['periodo']['id']}", ePeriodo, TIEMPO_ENCACHE)
            eInscripcion = ePerfilUsuario.inscripcion
            ePersona = eInscripcion.persona

            action = eRequest['action']

            if action == "changeProfile":
                with transaction.atomic():
                    try:
                        ePersona = Persona.objects.get(pk=ePersona.id)
                        if not 'fileFoto' in eFiles:
                            raise NameError(u"Favor subir el archivo de la foto")

                        nfileFoto = eFiles['fileFoto']
                        extensionFoto = nfileFoto._name.split('.')
                        tamFoto = len(extensionFoto)
                        exteFoto = extensionFoto[tamFoto - 1]
                        if nfileFoto.size > 1500000:
                            raise NameError(u"Error al cargar la foto de perfil, el tamaño del archivo es mayor a 15 Mb.")
                        if not exteFoto.lower() in ['jpg']:
                            raise NameError(u"Error al cargar la foto de perfil, solo se permiten archivos .jpg")
                        nfileFoto._name = generar_nombre("foto_", nfileFoto._name)
                        eFotoPersona = ePersona.foto(nFile=nfileFoto, request=request)
                        make_thumb_picture(ePersona)
                        if GENERAR_TUMBAIL:
                            make_thumb_fotopersona(ePersona)
                        log(u'Adicionó foto de persona: %s' % eFotoPersona, request, "add")
                        return Helper_Response(isSuccess=True, data={}, message="Se ha cambiada correctamente la contraseña", status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acciòn no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
