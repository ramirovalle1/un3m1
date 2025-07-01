import jwt
import json
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.conf import settings

from sga.models import Persona, DetPersonaPadronElectoral, CabPadronElectoral


@csrf_exempt
def logintei_view(request):
    try:
        if request.method == "POST":

            if not CabPadronElectoral.objects.values('id').filter(status=True, activo=True).exists():
                raise NameError(u"No existe periodo electoral activo")

            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')

            user_ = authenticate(username=username, password=password)

            if user_:
                token = generatetei_token(user_)
                qspersona = Persona.objects.filter(status=True, usuario=user_)
                if not qspersona.exists():
                    raise NameError(u"Usted no cuenta con perfil en nuestro sistema")
                persona_ = qspersona.first()

                # if not DetPersonaPadronElectoral.objects.values('id').filter(persona=persona_, status=True, cab__activo=True).exists():
                #     raise NameError(u"Usted no forma parte del padron electoral")

                user_data = {
                    'token': token,
                    'user': {
                        "id": persona_.id,
                        "username": username,
                        "first_name": persona_.nombres,
                        "last_name": f"{persona_.apellido1} {persona_.apellido2}",
                        "fullName": f"{persona_.nombres} {persona_.apellido1} {persona_.apellido2}",
                        "email": persona_.emailinst,
                        "celular": persona_.telefono,
                        "photo": str(persona_.get_foto()),
                    }
                }
                return JsonResponse({"success": True, "data": user_data}, status=200)
            else:
                return JsonResponse({"success": False, "msg": "Credenciales Incorrectas"}, status=401)
    except Exception as ex:
        return JsonResponse({"success": False, "msg": f"{ex}"}, status=405)


def generatetei_token(user):
    payload = {
        'user_id': user.id,
        'username': user.username,
        'exp': datetime.utcnow() + timedelta(days=1),
        'iat': datetime.utcnow(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

