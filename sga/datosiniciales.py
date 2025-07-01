# -*- coding: UTF-8 -*-
import random
from datetime import datetime
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from bd.funciones import recoveryPassword
from settings import EMAIL_DOMAIN, SERVER_RESPONSE
from sga.funciones import variable_valor, log, validar_ldap_aux, resetear_clavepostulante
from sga.models import Persona, miinstitucion, CUENTAS_CORREOS, Inscripcion
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt


def generar_cambio_clave():
    clave = ''
    for i in range(50):
        clave += random.choice('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_')
    return clave


@transaction.atomic()
def view(request):
    if request.method == "POST":
        if "action" in request.POST:
            action = request.POST['action']

            if action == "busqueda":
                try:
                    busqueda = request.POST['busqueda']
                    busqueda = busqueda.upper()
                    if Persona.objects.db_manager("sga_select").filter(cedula=busqueda).exists():
                        persona = Persona.objects.filter(cedula=busqueda)[0]
                        if persona.es_administrativo() and persona.es_administrativo_perfilactivo():
                            return JsonResponse({"result": "bad", "mensaje": u"Esta opción para su perfil no está disponible, solicitar el cambio de contraseña al personal de soporte de TIC."})
                        elif persona.es_profesor():
                            lista = persona.lista_emails()
                            if lista.__len__() <= 0:
                                return JsonResponse({"result": "ok", "cantidad": 1, "id": str(persona.id), "ced": persona.cedula, "nombre": persona.nombre_completo(), "user": persona.usuario.username, "permisoboton": 0, "perfiles": persona.mis_perfilesusuarios().count()})
                            return JsonResponse({"result": "ok", "cantidad": 1, "id": str(persona.id), "ced": persona.cedula, "nombre": persona.nombre_completo(), "user": persona.usuario.username, "permisoboton": 1, "perfiles": persona.mis_perfilesusuarios().count()})
                        elif persona.es_estudiante():
                            lista = persona.lista_emails()
                            if lista.__len__() <= 0:
                                return JsonResponse({"result": "ok", "cantidad": 1, "id": str(persona.id), "ced": persona.cedula, "nombre": persona.nombre_completo(), "user": persona.usuario.username, "permisoboton": 0, "perfiles": persona.mis_perfilesusuarios().count()})
                            return JsonResponse({"result": "ok", "cantidad": 1, "id": str(persona.id), "ced": persona.cedula, "nombre": persona.nombre_completo(), "user": persona.usuario.username, "permisoboton": 1, "perfiles": persona.mis_perfilesusuarios().count()})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Esta opción para su perfil no está disponible, solicitar el cambio de contraseña al personal de soporte de TIC."})
                    return JsonResponse({"result": "bad", "mensaje": u"Tu búsqueda no ha devuelto resultado. Vuelve a intentarlo con otra información."})
                except Exception as ex:
                    pass

            if action == "busquedaadministrativo":
                try:
                    busqueda = request.POST['busqueda']
                    busqueda = busqueda.upper()
                    if Persona.objects.db_manager("sga_select").filter(cedula=busqueda).exists():
                        persona = Persona.objects.filter(Q(cedula=busqueda) | Q(pasaporte=busqueda))[0]
                        if persona.es_administrativo() or persona.es_profesor():
                            return JsonResponse({"result": "ok", "id": persona.usuario.id})
                        else:
                            return JsonResponse({"result": "bad",
                                                 "mensaje": u"Esta opción solo está disponible para los administrativos."})
                    return JsonResponse({"result": "bad", "mensaje": u"No tiene acceso al sistema."})
                except Exception as ex:
                    pass

            if action == "busquedaestudianteaspirante":
                try:
                    busqueda = request.POST['busqueda']
                    busqueda = busqueda.upper()
                    personaingreso = Persona.objects.db_manager("sga_select").filter(Q(cedula=busqueda) | Q(pasaporte=busqueda))[0]
                    if not personaingreso.usuario.is_superuser:
                        if Persona.objects.db_manager("sga_select").filter(cedula=busqueda).exists():
                            persona = Persona.objects.db_manager("sga_select").filter(Q(cedula=busqueda) | Q(pasaporte=busqueda))[0]
                            if persona.es_administrativo() or persona.es_profesor():
                                return JsonResponse({"result": "bad", "mensaje": u"Esta opción solo está disponible para aspirantes."})
                            else:
                                return JsonResponse({"result": "ok", "id": persona.usuario.id, "email": persona.email})
                    return JsonResponse({"result": "bad", "mensaje": u"No tiene acceso al sistema."})
                except Exception as ex:
                    pass

            if action == "generarnuevaclave":
                try:
                    usuario = request.POST['usuario']
                    if Persona.objects.db_manager("sga_select").filter(cedula=usuario).exists():
                        persona = Persona.objects.filter(cedula=usuario)[0]
                        user=persona.usuario
                        usuario = persona.usuario
                        usuario.set_password(generar_cambio_clave())
                        usuario.save()

                        cambioclave = persona.cambiar_clave()
                        cambioclave.solicitada = True
                        cambioclave.clavecambio = generar_cambio_clave()
                        cambioclave.save(request)
                        log(u'Genero nuevo cambio de contraseña: %s [%s]' % (persona,persona.id), request, "add", user=user)
                        # cuenta = 7
                        # if SERVER_RESPONSE in ['209', '207', '211']:
                        #     cuenta = 4
                        correo=persona.emailinst
                        send_html_mail("Solicitud de cambio de contraseña", "emails/cambioclave.html",
                                       {'sistema': u'Sistema de Gestión Académica',
                                        'fecha': datetime.now().date,
                                        'persona': persona,
                                        't': miinstitucion(),
                                        'clave': cambioclave.clavecambio,
                                        'dominio': EMAIL_DOMAIN},persona.lista_emails(), [],
                                       cuenta=CUENTAS_CORREOS[7][1])
                        # persona.lista_emails_envio(), [],
                        return JsonResponse({"result": "ok", "data": str(correo)})
                        # return JsonResponse({"result": "ok"})
                    return JsonResponse({"result": "bad", "mensaje": u"No existe el usuario"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})

            if action == "generarnuevaclaveadministrativo":
                try:
                    usuario = int(request.POST['usuario'])
                    if Persona.objects.db_manager("sga_select").filter(usuario__id=usuario).exists():
                        persona = Persona.objects.filter(usuario__id=usuario)[0]
                        user = persona.usuario
                        cambioclave = persona.cambiar_clave()
                        cambioclave.solicitada = True
                        cambioclave.clavecambio = generar_cambio_clave()
                        cambioclave.save(request)
                        log(u'Genero nueva clave administrativo: %s [%s] - cambio clave: %s ' % (persona, persona.id, cambioclave), request, "add", user=user)
                        send_html_mail("Solicitud de cambio de contraseña.", "emails/cambioclaveadministrativo.html",
                                       {'sistema': u'Sistema de Gestión',
                                        'fecha': datetime.now().date(),
                                        'persona': persona,
                                        't': miinstitucion(),
                                        'clave': cambioclave.clavecambio,
                                        'dominio': EMAIL_DOMAIN}, persona.lista_emails_envio(), [],
                                       coneccion=CUENTAS_CORREOS[7][1])
                        return JsonResponse({"result": "ok"})
                    return JsonResponse({"result": "bad", "mensaje": u"No existe el usuario"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})

            if action == "generarnuevaclaveaspirante":
                try:
                    usuario = int(request.POST['usuario'])
                    if Persona.objects.db_manager("sga_select").filter(usuario__id=usuario).exists():
                        persona = Persona.objects.filter(usuario__id=usuario)[0]
                        user = persona.usuario
                        resetear_clavepostulante(persona)
                        clave = ''
                        if persona.cedula:
                            clave = persona.cedula.strip()
                        elif persona.pasaporte:
                            clave = persona.pasaporte.strip()
                        log(u'Genero nueva clave estudiante o postulante: %s [%s]' % (persona, persona.id), request,
                            "add", user=user)
                        send_html_mail("Solicitud de cambio de contraseña.", "emails/cambioclavepostulante.html",
                                       {'sistema': u'Sistema de Gestión',
                                        'fecha': datetime.now().date(),
                                        'persona': persona,
                                        't': miinstitucion(),
                                        'clave': clave,
                                        'dominio': EMAIL_DOMAIN}, persona.lista_emails(), [],
                                       coneccion=CUENTAS_CORREOS[7][1])
                        return JsonResponse({"result": "ok"})
                    return JsonResponse({"result": "bad", "mensaje": u"No existe el usuario"})
                except Exception as ex:
                    pass

            if action == "resetear":
                try:
                    persona = Persona.objects.get(pk=request.POST['id'])
                    clave = request.POST['idc']
                    password = request.POST['clave']
                    espacio = mayuscula = minuscula = numeros = False
                    long = len(password)  # Calcula la longitud de la contraseña
                    # y = password.isalnum()  # si es alfanumérica retona True
                    for carac in password:
                        espacio = True if carac.isspace() else espacio  # si encuentra un espacio se cambia el valor user
                        mayuscula = True if carac.isupper() else mayuscula  # acumulador o contador de mayusculas
                        minuscula = True if carac.islower() == True else minuscula  # acumulador o contador de minúsculas
                        numeros = True if carac.isdigit() == True else numeros  # acumulador o contador de numeros

                    if espacio == True:  # hay espacios en blanco
                        return JsonResponse({"result": "bad", "mensaje": u"La clave no puede contener espacios."})
                    if not mayuscula or not minuscula or not numeros or long < 8:
                        return JsonResponse({"result": "bad",
                                             "mensaje": u"La clave elegida no es segura: debe contener letras minúsculas, mayúsculas, números y al menos 8 carácter."})

                    solictado = persona.solicitud_cambio_clave(clave)
                    if not solictado:
                        return JsonResponse({"result": "bad", "mensaje": u"Solicitud de cambio antigua."})
                    persona.clave_cambiada()
                    usuario = persona.usuario
                    usuario.set_password(password)
                    usuario.save()
                    if variable_valor('VALIDAR_LDAP'):
                        validar_ldap_aux(usuario.username, password, persona)
                    log(u'Reseteo clave - modo recuperacion: %s [%s] - cambio clave: %s ' % (persona, persona.id, usuario), request, "add", user=persona.usuario)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"No se pudo cambiar la clave. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'confirmar':
                try:
                    data = {}
                    data['title'] = u'Cambio de malla'
                    hoy = datetime.now()
                    personainscripcion = Inscripcion.objects.get(pk=int(encrypt(request.GET['id'])))
                    if not personainscripcion.confimacion_online:
                        personainscripcion.confimacion_online = True
                        personainscripcion.fecha_online = hoy
                        personainscripcion.save()
                        data['personaconfirma'] = personainscripcion
                        cuenta = 20
                        nombrecorto = personainscripcion.persona.nombres.split(" ")
                        send_html_mail("Mensaje desde el Campus Virtual UNEMI", "emails/conofirmaciononline.html",
                                       {'sistema': u'Inicio de clases',
                                        'fecha': datetime.now(),
                                        'nombrecorto': nombrecorto[0],
                                        'persona': personainscripcion,
                                        't': miinstitucion(),
                                        'dominio': EMAIL_DOMAIN}, personainscripcion.persona.emailpersonal(), [],
                                       coneccion=CUENTAS_CORREOS[cuenta][1])
                    return render(request, "datosiniciales/confirmaemail.html", data)
                except Exception as ex:
                    pass
        else:
            data = {}
            if 'id' in request.GET:
                data['persona'] = persona = Persona.objects.get(pk=int(request.GET['id']))
            else:
                return HttpResponseRedirect('/')
            if 'idc' in request.GET:
                data['clave'] = clave = request.GET['idc']
            else:
                return HttpResponseRedirect('/')
            if not persona.cambioclavepersona_set.exists():
                return HttpResponseRedirect('/')
            data['background'] = random.randint(1, 2)
            return render(request, 'datosiniciales/view.html', data)
