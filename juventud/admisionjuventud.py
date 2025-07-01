# -*- coding: latin-1 -*-
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.db.models.query_utils import Q
from datetime import datetime
from decorators import last_access
from juventud.forms import RegistroProgramaForm
from juventud.models import Programaformacion, Personaformacion, PersonaPrograma
from sga.funciones import validarcedula
from sga.models import DetalleConfiguracionDescuentoPosgrado, miinstitucion, CUENTAS_CORREOS
from posgrado.models import CONTACTO_MAESTRIA,  CanalInformacionMaestria
from sga.tasks import send_html_mail


@last_access
@transaction.atomic()
def view(request):
    data = {}
    data['url_'] = request.path
    data['currenttime'] = datetime.now()
    data['fecha_actual'] = fecha_actual = datetime.now()
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'addpersona':
                try:
                    f = RegistroProgramaForm(request.POST)
                    if f.is_valid():
                        zona = False
                        if request.POST['zona'] == 'true':
                            zona = True
                        elif request.POST['zona'] == 'false':
                            zona = False
                        if f.cleaned_data['cedula'][:2] == u'VS' or f.cleaned_data['cedula'][:2] == u'vs':
                            if not Personaformacion.objects.filter(pasaporte=f.cleaned_data['cedula']).exists():
                                persona = Personaformacion(pasaporte=f.cleaned_data['cedula'],
                                                           nombres=f.cleaned_data['nombres'],
                                                           apellido1=f.cleaned_data['apellido1'],
                                                           apellido2=f.cleaned_data['apellido2'],
                                                           email=f.cleaned_data['email'],
                                                           telefono=f.cleaned_data['telefono'],
                                                           sexo_id=request.POST['genero'],
                                                           pais_id=request.POST['pais'],
                                                           provincia_id=request.POST['provincia'],
                                                           canton_id=request.POST['canton'],
                                                           direccion=request.POST['direccion'],
                                                           fechanacimiento=request.POST['fechanacimiento'],
                                                           lugarnacimiento=request.POST['nacimiento']
                                                           )
                                persona.save(request)
                                perprograma = PersonaPrograma(personaformacion=persona,
                                                              programa_id=1,
                                                              nombreproyecto=request.POST['id_proyecto'],
                                                              poblacion=request.POST['id_poblacion'],
                                                              meta=request.POST['id_meta'],
                                                              resultado=request.POST['id_resultado'],
                                                              terminocondicion=zona)
                                perprograma.save(request)
                            else:
                                persona = Personaformacion.objects.filter(pasaporte=f.cleaned_data['cedula']).last()
                                persona.email = f.cleaned_data['email']
                                persona.telefono = f.cleaned_data['telefono']
                                persona.pais_id = request.POST['pais']
                                persona.provincia_id = request.POST['provincia']
                                persona.canton_id = request.POST['canton']
                                persona.direccion = request.POST['direccion']
                                persona.lugarnacimiento = request.POST['nacimiento']
                                persona.save(request)
                                if persona.personaprograma_set.filter(programa_id=1, status=True).exists():
                                    perprograma = persona.personaprograma_set.filter(programa_id=1, status=True)[0]
                                    perprograma.nombreproyecto=request.POST['id_proyecto']
                                    perprograma.poblacion=request.POST['id_poblacion']
                                    perprograma.meta=request.POST['id_meta']
                                    perprograma.resultado=request.POST['id_resultado']
                                else:
                                    perprograma = PersonaPrograma(personaformacion=persona,
                                                                  programa_id=1,
                                                                  nombreproyecto=request.POST['id_proyecto'],
                                                                  poblacion=request.POST['id_poblacion'],
                                                                  meta=request.POST['id_meta'],
                                                                  resultado=request.POST['id_resultado'],
                                                                  terminocondicion=zona)
                                    perprograma.save(request)
                        else:
                            if not Personaformacion.objects.filter(Q(cedula=f.cleaned_data['cedula']) | Q(pasaporte=f.cleaned_data['cedula']), status=True).exists():
                                persona = Personaformacion(cedula=f.cleaned_data['cedula'],
                                                           nombres=f.cleaned_data['nombres'],
                                                           apellido1=f.cleaned_data['apellido1'],
                                                           apellido2=f.cleaned_data['apellido2'],
                                                           email=f.cleaned_data['email'],
                                                           telefono=f.cleaned_data['telefono'],
                                                           sexo_id=request.POST['genero'],
                                                           pais_id=request.POST['pais'],
                                                           provincia_id=request.POST['provincia'],
                                                           canton_id=request.POST['canton'],
                                                           direccion=request.POST['direccion'],
                                                           fechanacimiento=request.POST['fechanacimiento'],
                                                           lugarnacimiento=request.POST['nacimiento']
                                                           )
                                persona.save(request)
                                perprograma = PersonaPrograma(personaformacion=persona,
                                                              programa_id=1,
                                                              nombreproyecto=request.POST['id_proyecto'],
                                                              poblacion=request.POST['id_poblacion'],
                                                              meta=request.POST['id_meta'],
                                                              resultado=request.POST['id_resultado'],
                                                              terminocondicion=zona)
                                perprograma.save(request)
                            else:
                                persona = Personaformacion.objects.filter(Q(cedula=f.cleaned_data['cedula']) | Q(pasaporte=f.cleaned_data['cedula'])).first()
                                persona.email = f.cleaned_data['email']
                                persona.telefono = f.cleaned_data['telefono']
                                persona.pais_id = request.POST['pais']
                                persona.provincia_id = request.POST['provincia']
                                persona.canton_id = request.POST['canton']
                                persona.direccion = request.POST['direccion']
                                persona.lugarnacimiento = request.POST['nacimiento']
                                persona.save(request)
                                if persona.personaprograma_set.filter(programa_id=1, status=True).exists():
                                    perprograma = persona.personaprograma_set.filter(programa_id=1, status=True)[0]
                                    perprograma.nombreproyecto=request.POST['id_proyecto']
                                    perprograma.poblacion=request.POST['id_poblacion']
                                    perprograma.meta=request.POST['id_meta']
                                    perprograma.resultado=request.POST['id_resultado']
                                else:
                                    perprograma = PersonaPrograma(personaformacion=persona,
                                                                  programa_id=1,
                                                                  nombreproyecto=request.POST['id_proyecto'],
                                                                  poblacion=request.POST['id_poblacion'],
                                                                  meta=request.POST['id_meta'],
                                                                  resultado=request.POST['id_resultado'],
                                                                  terminocondicion=zona)
                                    perprograma.save(request)
                        send_html_mail("Inscripción a la Escuela de Liderazgo", "emails/notificacion_juventud.html",
                                       {'sistema': u'SISTEMA', 't': miinstitucion(), 'tiposistema_': 2}, [persona.email], [], cuenta=CUENTAS_CORREOS[4][1])
                        return JsonResponse({'result': 'ok', "idpersona": persona.id})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

            elif action == 'registroformacion':
                try:
                    cedula = request.POST['cedula'].strip()
                    hoy = datetime.now().date()
                    if request.POST['tipoidentificacion'].strip() == '1':
                        resp = validarcedula(cedula)
                        if resp != 'Ok':
                            raise NameError(u"%s."%(resp))

                    itinerario = 0
                    datospersona = None
                    provinciaid = 0
                    cantonid = 0
                    cantonnom = ''
                    lugarestudio = ''
                    carrera = ''
                    profesion = ''
                    institucionlabora = ''
                    cargo = ''
                    teleoficina = ''
                    idgenero = 0
                    habilitaemail = 0
                    if cedula:
                        if Personaformacion.objects.filter(cedula=cedula).exists():
                            datospersona = Personaformacion.objects.get(cedula=cedula)
                        elif Personaformacion.objects.filter(pasaporte=cedula).exists():
                            datospersona = Personaformacion.objects.get(pasaporte=cedula)
                    if datospersona:
                        return JsonResponse({"result": "ok", "idpersona": datospersona.id, "apellido1": datospersona.apellido1, "apellido2": datospersona.apellido2,
                                             "nombres": datospersona.nombres, "email": datospersona.email, "telefono": datospersona.telefono, "genero":datospersona.sexo.id,
                                             "pais": datospersona.pais.id if datospersona.pais else 0,"provincia": datospersona.provincia.id if datospersona.provincia else 0, "canton": datospersona.canton.id if datospersona.canton else 0, "direccion": datospersona.direccion})
                    else:
                        return JsonResponse({"result": "no"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"%s"%(ex)})

            elif action == 'consultacedula':
                try:
                    cedula = request.POST['cedula'].strip()
                    hoy = datetime.now().date()
                    if request.POST['tipoidentificacion'].strip() == '1':
                        resp = validarcedula(cedula)
                        if resp != 'Ok':
                            raise NameError(u"%s."%(resp))

                    itinerario = 0
                    datospersona = None
                    provinciaid = 0
                    cantonid = 0
                    cantonnom = ''
                    lugarestudio = ''
                    carrera = ''
                    profesion = ''
                    institucionlabora = ''
                    cargo = ''
                    teleoficina = ''
                    idgenero = 0
                    habilitaemail = 0
                    if cedula:
                        if Personaformacion.objects.filter(cedula=cedula).exists():
                            datospersona = Personaformacion.objects.get(cedula=cedula)
                        elif Personaformacion.objects.filter(pasaporte=cedula).exists():
                            datospersona = Personaformacion.objects.get(pasaporte=cedula)
                    if datospersona:
                        return JsonResponse({"result": "ok", "idpersona": datospersona.id, "apellido1": datospersona.apellido1, "apellido2": datospersona.apellido2,
                                             "nombres": datospersona.nombres, "email": datospersona.email, "telefono": datospersona.telefono, "genero":datospersona.sexo.id,"nacimiento":datospersona.lugarnacimiento,
                                             "pais": datospersona.pais.id if datospersona.pais else 0,"provincia": datospersona.provincia.id if datospersona.provincia else 0, "canton": datospersona.canton.id if datospersona.canton else 0, "direccion": datospersona.direccion})
                    else:
                        return JsonResponse({"result": "no"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"%s"%(ex)})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'listcampoespecifico':
                try:

                    return JsonResponse(data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Registrar certificado'
                hoy = fecha_actual
                puedeinscribirse = False
                if  Programaformacion.objects.filter(pk=1, activo=True, status=True):
                    puedeinscribirse=True
                    data['programa'] = programa = Programaformacion.objects.get(pk=1, status=True)
                    data['banneradjunto'] = programa.download_banner()
                data['puedeinscribirse'] = puedeinscribirse
                return render(request, "admisionjuventud/admisionjuventud.html", data)
            except Exception as ex:
                pass