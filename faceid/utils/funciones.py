import json
import os
import re
from datetime import datetime
from unidecode import unidecode
from PIL import Image
from decorators import inhouse_check
from faceid.models import PersonaMarcada
from faceid.views.marcadas import file_json_img
from sagest.models import DistributivoPersona
from settings import DEBUG
from sga.funciones import variable_valor, generar_nombre

def funcionarios_importar():
    personas_marcadas = PersonaMarcada.objects.filter(status=True).values_list('persona_id', flat=True)
    return DistributivoPersona.objects.filter(status=True).exclude(persona_id__in=personas_marcadas)


def permiso_marcaje(persona, request):
    context = {'result':True, 'mensaje':'Puede marcar'}
    persona_marcada=PersonaMarcada.objects.filter(persona=persona, status=True).last()
    context['persona_marcada']=persona_marcada
    if not persona_marcada or not persona_marcada.activo:
        context['result']=False
        context['mensaje']='Su usuario no tiene permisos para marcar en el sistema.'
        return context
    if persona_marcada:
        if not persona_marcada.externo:
            in_work = inhouse_check(request) if not DEBUG else True
            if not in_work:
                context['result']=False
                context['mensaje']='Su usuario no tiene permisos para marcar fuera de la institución.'
                return context
        if persona_marcada.solo_pc:
            MOBILE_AGENT_RE = re.compile(r".*(iphone|mobile|androidtouch)", re.IGNORECASE)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            is_mobile = True if 'mobile' in request.GET else MOBILE_AGENT_RE.match(user_agent)
            if is_mobile:
                context['result']=False
                context['mensaje']='Su usuario no tiene permisos para marcar desde un dispositivo móvil.'
                return context
    return context

def addglobal_var(data):
    data['marcadas'] = True
    hoy = datetime.now()
    data['tiempo'] = {"hour": str(hoy.time().hour).zfill(2),
                      "minute": str(hoy.time().minute).zfill(2),
                      "second": str(hoy.time().second).zfill(2)}
    try:
        elementos = variable_valor('ELEMENTOS_MARCADAS')
        for i in range(4 - len(elementos)):
            elementos.append('')
        mostrar_video, data['url_video'], mostrar_img, data['url_img'] = elementos
        if mostrar_img:
            data['mostrar_img'] = eval(mostrar_img)
        data['mostrar_video'] = eval(mostrar_video)
    except Exception as ex:
        pass

def file_json_img(json_img):
    import base64
    from django.core.files.base import ContentFile
    from sga.funciones import generar_nombre
    image_data = json_img['image']
    # Remover el encabezado 'data:image/jpeg;base64,' que no es parte del contenido real de la imagen
    format, imgstr = image_data.split(';base64,')
    ext = format.split('/')[-1]  # Obtén la extensión del archivo
    # Decodificar la imagen
    img_data = base64.b64decode(imgstr)
    # Crear un archivo Django desde los datos de imagen
    name_file=generar_nombre('uploaded_image', f'name_original.{ext}')
    img_file = ContentFile(img_data, name=name_file)
    return img_file


