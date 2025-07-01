# -*- coding: latin-1 -*-
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.db.models.query_utils import Q
from datetime import datetime
from decorators import last_access
from posgrado.forms import RegistroRequisitosMaestriaForm, RegistroRequisitosMaestriaForm1

from sga.funciones import generar_nombre
from sga.models import Persona, Carrera, CUENTAS_CORREOS
from posgrado.models import PreInscripcion, FormatoCarreraIpec, EvidenciasMaestrias, CohorteMaestria, MaestriasAdmision, \
    InteresadoProgramaMaestria
from django.forms import model_to_dict
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt


@last_access
@transaction.atomic()
def view(request):
    data = {}
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'addregistro':
                try:
                    hoy = datetime.now().date()
                    cedula = request.POST['cedula'].strip() if 'cedula' in request.POST else ''
                    nombres = request.POST['nombres']
                    email = request.POST['email']
                    telefono = request.POST['telefono']
                    carrera = request.POST['carrera']
                    programa = MaestriasAdmision.objects.get(pk=carrera)
                    preinscrito = InteresadoProgramaMaestria(nombres=nombres,
                                                 cedula=cedula,
                                                 telefono=telefono,
                                                 correo=email,
                                                 programa=programa)
                    preinscrito.save(request)

                    # lista = []
                    # if preinscrito.persona.emailinst:
                    #     lista.append(preinscrito.persona.emailinst)
                    # if preinscrito.persona.email:
                    #     lista.append(preinscrito.persona.email)
                    # if formato.correomaestria:
                    #     lista.append(formato.correomaestria)
                    # lista.append(conectar_cuenta(CUENTAS_CORREOS[18][1]))
                    # asunto = u"Confirmación de pre-inscripción de maestría"
                    # send_html_mail(asunto, "emails/notificacion_preinscripcion_ipec.html",
                    #                     {'sistema': 'Posgrado UNEMI', 'preinscrito': preinscrito,'formato': formato.banner},
                    #                     lista, [], [],
                    #                     cuenta=CUENTAS_CORREOS[18][1])
                    return JsonResponse({'result': 'ok',
                                         "mensaje": u"Sus datos se enviaron correctamente, por favor revisar la notificación enviada a su correo."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'SOLICITAR INFORMACIÓN'
                hoy = datetime.now().date()
                data['listadomaestriascohorte'] = CohorteMaestria.objects.filter(activo=True, fechainicioinsp__lte=hoy,
                                                                                 fechafininsp__gte=hoy,
                                                                                 status=True).order_by('id')
                data['carreras'] = FormatoCarreraIpec.objects.filter(carrera__id__in=[154, 155], status=True).order_by('-id')
                return render(request, "seguimientointeresados/interesadosmaestria.html", data)
            except Exception as ex:
                pass
