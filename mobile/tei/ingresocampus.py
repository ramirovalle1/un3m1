import hashlib
import sys

import jwt
import json
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.conf import settings

from sga.models import Persona, DetPersonaPadronElectoral, CabPadronElectoral
from voto.models import ConfiguracionMesaResponsable


@csrf_exempt
def ingresocampustei_view(request):
    if request.method == "POST":
        if 'action' in request.POST:
            pass
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'validateCode':
                try:
                    qr, personaid = str(request.GET['qr']), int(request.GET['id'])
                    if qr:
                        persona_ = Persona.objects.get(id=personaid)
                        qsenmesa = DetPersonaPadronElectoral.objects.filter(persona=persona_, status=True,
                                                                            cab__activo=True, tipo__in=[2, 3]).values_list('mesa__id', flat=True)
                        personalogistica = ConfiguracionMesaResponsable.objects.filter(status=True,
                                                                                       periodo__status=True,
                                                                                       periodo__activo=True,
                                                                                       logistica__in=[persona_.id]).values_list('mesa__id', flat=True)
                        listmesas = list(qsenmesa) + list(personalogistica)
                        qsempadronado = DetPersonaPadronElectoral.objects.filter(status=True, cab__status=True, cab__activo=True, codigo_qr=qr)
                        if qsempadronado.exists():
                            empadronadoqr = qsempadronado.first()
                            aData = {'foto_perfil': str(empadronadoqr.persona.get_foto()), 'mesa': empadronadoqr.mesa.__str__() , 'documento': empadronadoqr.persona.identificacion(), 'nombre_completo': f"{empadronadoqr.persona.nombres} {empadronadoqr.persona.apellido1} {empadronadoqr.persona.apellido2}"}
                            if not empadronadoqr.mesa.id in listmesas:
                                resp_ = {"success": True, 'acceso': False, "aData": aData, 'msg': f"Asistencia no puede ser tomada, persona pertenece a otra mesa, mesa asignada:"}
                                return JsonResponse(resp_, status=200)
                            empadronadoqr.persona_valida_id = personaid
                            empadronadoqr.fechavalida = datetime.now().date()
                            empadronadoqr.validado = True
                            empadronadoqr.save(request)
                            resp_ = {"success": True, 'acceso': True, "aData": aData, 'msg': f"Acceso Permitido"}
                            return JsonResponse(resp_, status=200)
                        else:
                            return JsonResponse({"success": False, 'msg': 'Codigo QR no valido'}, status=200)
                    else:
                        raise NameError('Codigo QR no valido')
                except Exception as ex:
                    return JsonResponse({"success": False, "msg": f"{ex} - Error Line: {sys.exc_info()[-1].tb_lineno}"}, status=200)

            if action == 'loadQrIngresoCampus':
                try:
                    userid = request.GET['user']
                    lugarvotacion, coordinacion, carrera, modalidad = 'SIN ASIGNAR', 'SIN ASIGNAR', 'SIN ASIGNAR', 'SIN ASIGNAR'
                    generarqr, enmesa, rolmesa, lugarmesa = False, False, 'SIN ASIGNAR', 'SIN ASIGNAR'
                    periodo = CabPadronElectoral.objects.filter(status=True, activo=True).first().nombre
                    persona_ = Persona.objects.get(id=userid)
                    # if not DetPersonaPadronElectoral.objects.values('id').filter(persona=persona_, status=True, cab__activo=True).exists():
                    #     raise NameError(u"Usted no forma parte del padron electoral")
                    codigoqr = generate_unique_code(userid)
                    qsenmesa = DetPersonaPadronElectoral.objects.filter(persona=persona_, status=True, cab__activo=True, tipo__in=[2, 3])
                    empadronado = DetPersonaPadronElectoral.objects.filter(persona=persona_, status=True, cab__activo=True, tipo=1).first()
                    if empadronado:
                        generarqr = True
                        codigoqr = empadronado.codigo_qr
                        lugarvotacion = empadronado.mesa.__str__() if empadronado.mesa else 'SIN ASIGNAR'
                        if empadronado.inscripcion:
                            coordinacion = empadronado.inscripcion.coordinacion.alias if empadronado.inscripcion.coordinacion else 'SIN ASIGNAR'
                            carrera = empadronado.inscripcion.carrera.__str__() if empadronado.inscripcion.carrera else 'SIN ASIGNAR'
                    personamesa = qsenmesa.first()
                    if personamesa:
                        if personamesa.info_mesa():
                            enmesa = True
                            generarqr = False
                            rolmesa = personamesa.info_mesa()[0]
                            lugarmesa = personamesa.info_mesa()[1]
                    personalogistica = ConfiguracionMesaResponsable.objects.filter(status=True, periodo__status=True, periodo__activo=True, logistica__in=[persona_.id])
                    if personalogistica:
                        enmesa = True
                        generarqr = False
                        personalog_ = personalogistica.first()
                        rolmesa = 'LOGISTICA'
                        if personalogistica.count() == 1:
                            lugarmesa = personalog_.mesa.__str__()
                        else:
                            lugarmesa = 'ASIGNACIÓN LIBRE'
                    resp_ = {"success": True, "generaqr": generarqr, "qrCodeData": codigoqr, "periodo": periodo,
                             "coordinacion": coordinacion, "carrera": carrera, 'lugarvotacion': lugarvotacion,
                             'enmesa': enmesa, 'rolmesa': rolmesa, 'lugarmesa': lugarmesa}
                    return JsonResponse(resp_, status=200)
                except Exception as ex:
                    print(ex)
                    return JsonResponse({"success": False, "msg": f"{ex}"}, status=200)

            return JsonResponse({"success": False, "msg": f"Método no permitido: {action}"}, status=200)


def generate_unique_code(user_id):
    try:
        now = datetime.now()
        year = now.year
        month = now.month
        day = now.day
        hour = now.hour
        minute = now.minute
        unique_string = f"{user_id}{year}{month}{day}{hour}{minute}"
        unique_code = hashlib.md5(unique_string.encode()).hexdigest()
        return unique_code
    except Exception as ex:
        return '0'