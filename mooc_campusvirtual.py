# -*- coding: UTF-8 -*-
from random import choice
from django.shortcuts import render
from sga.models import Persona, miinstitucion, CUENTAS_CORREOS, Inscripcion
from django.http import JsonResponse
from datetime import datetime
from settings import EMAIL_DOMAIN
from sga.tasks import send_html_mail, conectar_cuenta
from django.db import models, connection,connections,transaction
import unicodedata

def view(request):
    data = {}
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == "busqueda_virtual":
                try:
                    busqueda = request.POST['busqueda']
                    busqueda = busqueda.strip()
                    lista = []
                    if Persona.objects.filter(cedula=busqueda).exists():
                        persona = Persona.objects.filter(cedula=busqueda)[0]
                        if persona.es_administrativo() and persona.es_administrativo_perfilactivo() and not persona.es_profesor() :
                            return JsonResponse({"result": "bad","mensaje": u"Esta opción para su perfil no está disponible, solicitar el cambio de contraseña al personal de soporte de TIC."})

                        if persona.usuario is None:
                            return JsonResponse({"result": "bad","mensaje": u"No tiene usuario asignado en el sga, Contactese vía email: soportecampusvirtual@unemi.edu.ec o al teléfono (04) 2715081 , ext. 8100-8101"})

                        if persona.es_profesor():
                            cursor = connections['db_moodle_virtual'].cursor()
                            query = "SELECT * FROM mooc_user WHERE username='" + persona.usuario.username + "'"
                            cursor.execute(query)
                            resultado = cursor.fetchall()

                            if resultado.__len__():
                                lista.append([persona.nombre_completo(), persona.cedula, '', persona.usuario.username, persona.email, "profesor"])
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Usuario no registrado en el campus virtual. Contacto vía email: gestiontecno@unemi.edu.ec"})

                        elif persona.es_estudiante():
                            inscripcion = Inscripcion.objects.filter(persona=persona,sesion__id__in=[12,13])[0]
                            admision = not inscripcion.mi_coordinacion().id == 9

                            if not admision:
                                cursor = connections['db_moodle_virtual'].cursor()
                            else:
                                cursor = connections['db_moodle_semestre'].cursor()

                            query = "SELECT * FROM mooc_user WHERE username='"+persona.usuario.username+"'"
                            cursor.execute(query)
                            resultado = cursor.fetchall()

                            if resultado.__len__():
                                nombre_carrera = elimina_tildes(inscripcion.carrera.nombre)
                                lista.append([persona.nombre_completo(), persona.cedula, nombre_carrera.replace('ADMISION', ' '), persona.usuario.username, persona.email,"estudiante"])
                                data = {"result": "ok", "lista": lista}
                                return JsonResponse(data)
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Usuario no registrado en el campus virtual. Contacto vía email: soportecampusvirtual@unemi.edu.ec o al teléfono (04) 2715081 , ext. 8100-8101"})
                    return JsonResponse({"result": "bad", "mensaje": u"Tu búsqueda no ha devuelto resultado. Vuelve a intentarlo con otra información."})
                except Exception as ex:
                    pass

            elif action == "validar_usuario":
                try:
                    busqueda = request.POST['busqueda']
                    busqueda = busqueda.strip()
                    if Persona.objects.filter(cedula=busqueda).exists():
                        persona = Persona.objects.filter(cedula=busqueda)[0]
                        inscripcion = Inscripcion.objects.filter(persona=persona, sesion__id__in=[12, 13])[0]
                        admision = not inscripcion.mi_coordinacion().id == 9

                        if persona.usuario == None:
                            return JsonResponse({"result": "bad","mensaje": u"Usuario no registrado"})
                        else:
                            if not admision:
                                cursor = connections['db_moodle_virtual'].cursor()
                            else:
                                cursor = connections['db_moodle_semestre'].cursor()

                            query = "SELECT * FROM mooc_user WHERE username='" + str(persona.usuario.username) + "'"
                            cursor.execute(query)
                            resultado = cursor.fetchall()
                            if resultado.__len__():
                                data = {"result": "ok","permisoboton": 0,"correo":persona.email,"cedula":persona.cedula}
                                return JsonResponse(data)
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Usuario no registrado en el campus virtual. Contacto vía email: soportecampusvirtual@unemi.edu.ec o al teléfono (04) 2715081 , ext. 8100-8101"})
                    return JsonResponse({"result": "bad", "mensaje": u"Tu búsqueda no ha devuelto resultado. Vuelve a intentarlo con otra información."})
                except Exception as ex:
                    pass

            elif action == "generarnuevaclave":
                try:
                    usuario = request.POST['usuario']
                    if Persona.objects.filter(cedula=usuario).exists():
                        persona = Persona.objects.filter(cedula=usuario)[0]
                        cambioclave = generar_clave_aleatoria().strip()
                        correo=persona.email
                        inscripcion = Inscripcion.objects.filter(persona=persona, sesion__id__in=[12, 13])[0]
                        admision = not inscripcion.mi_coordinacion().id == 9
                        if not admision:
                            cursor = connections['db_moodle_virtual'].cursor()
                        else:
                            cursor = connections['db_moodle_semestre'].cursor()

                        query = "update mooc_user set password=MD5('"+cambioclave+"') where username='"+persona.usuario.username+"';"
                        cursor.execute(query)

                        send_html_mail("Solicitud de cambio de contraseña", "emails/cambioclavevirtual.html",
                                       {'sistema': u'Campus Virtual',
                                        'fecha': datetime.now().date,
                                        'persona': persona,
                                        't': miinstitucion(),
                                        'clave': cambioclave,
                                        'dominio': EMAIL_DOMAIN}, persona.lista_emails(), [],
                                       cuenta=CUENTAS_CORREOS[20][1])
                        persona.lista_emails_envio(), [],
                        return JsonResponse({"result": "ok", "data": str(correo)})
                    return JsonResponse({"result": "bad", "mensaje": u"No existe el usuario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

    else:
        if 'action' in request.GET:
            action = request.GET['action']

        else:
            data["background"] = 10
            return render(request, "mooc_campusvirtual/mooc_campusvirtual.html", data)


def generar_clave_aleatoria():
    longitud = 8
    valores = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    clave = ""
    clave = clave.join([choice(valores) for i in range(longitud)])
    return clave

def elimina_tildes(cadena):
    s = ''.join((c for c in unicodedata.normalize('NFD',cadena) if unicodedata.category(c) != 'Mn'))
    return s
