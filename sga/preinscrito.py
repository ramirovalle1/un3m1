# -*- coding: latin-1 -*-
import json
from asyncio import log
from datetime import datetime
from django.contrib.auth.models import User, Group
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from docutils.parsers.rst.directives import percentage

from settings import CLAVE_USUARIO_CEDULA, DEFAULT_PASSWORD, EMAIL_INSTITUCIONAL_AUTOMATICO, EMAIL_DOMAIN, \
    USA_TIPOS_INSCRIPCIONES, TIPO_INSCRIPCION_INICIAL, ALUMNOS_GROUP_ID, \
    REGISTRO_NUEVOS_ESTUDIANTES
from sga.forms import PreInscritoAutoregistroForm
from sga.funciones import convertir_fecha, calculate_username, variable_valor
from sga.models import Inscripcion, Persona, Carrera, Modalidad, Sede, Sesion, InscripcionTesDrive, \
    InscripcionTipoInscripcion, \
    DocumentosDeInscripcion, ParametrosAutoInscripcion, miinstitucion, CUENTAS_CORREOS
from sga.tasks import send_html_mail, conectar_cuenta


@transaction.atomic()
def view(request):
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'carrera':
                try:
                    sede = Sede.objects.get(pk=request.POST['id'])
                    nlista = {}
                    for carrera in Carrera.objects.filter(id__in=[x.carrera.id for x in ParametrosAutoInscripcion.objects.filter(sede=sede)]).distinct():
                        nlista.update({carrera.id: {'id': carrera.id, 'nombre': carrera.flexbox_repr()}})
                    return JsonResponse({'result': 'ok', 'lista': nlista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'modalidad':
                try:
                    sede = Sede.objects.get(pk=request.POST['id'])
                    carrera = Carrera.objects.get(pk=request.POST['idc'])
                    nlista = {}
                    for modalidad in Modalidad.objects.filter(id__in=[x.modalidad.id for x in ParametrosAutoInscripcion.objects.filter(sede=sede, carrera=carrera)]).distinct():
                        nlista.update({modalidad.id: {'id': modalidad.id, 'nombre': modalidad.nombre}})
                    return JsonResponse({'result': 'ok', 'lista': nlista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'sesion':
                try:
                    sede = Sede.objects.get(pk=request.POST['id'])
                    carrera = Carrera.objects.get(pk=request.POST['idc'])
                    modalidad = Modalidad.objects.get(pk=request.POST['idm'])
                    nlista = {}
                    for sesion in Sesion.objects.filter(id__in=[x.sesion.id for x in ParametrosAutoInscripcion.objects.filter(sede=sede, carrera=carrera, modalidad=modalidad)]).distinct():
                        nlista.update({sesion.id: {'id': sesion.id, 'nombre': sesion.nombre}})
                    return JsonResponse({'result': 'ok', 'lista': nlista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'registro':
                try:
                    f = PreInscritoAutoregistroForm(request.POST)
                    if f.is_valid():
                        if Inscripcion.objects.filter(persona__cedula=f.cleaned_data['cedula']).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Existe una inscripcion con esta identificacion, debe registrarse por secretaria."})
                        persona = Persona(nombres=request.POST['nombres'],
                                          apellido1=request.POST['apellido1'],
                                          apellido2=request.POST['apellido2'],
                                          nacimiento=convertir_fecha(request.POST['nacimiento']),
                                          cedula=request.POST['cedula'],
                                          pasaporte='',
                                          sexo_id=request.POST['sexo'],
                                          telefono=f.cleaned_data['telefono'],
                                          telefono_conv=f.cleaned_data['telefono_conv'],
                                          email=f.cleaned_data['email'],
                                          direccion=request.POST['direccion'])
                        persona.save(request)
                        log(u'Adicionó una nueva presona para pre inscripción: %s' % persona, request, "add")
                        persona.cambiar_clave()
                        username = calculate_username(persona)
                        if CLAVE_USUARIO_CEDULA:
                            password = persona.cedula
                        else:
                            password = DEFAULT_PASSWORD
                        emailinst_ = '{}@unemi.edu.ec'.format(username)
                        user = User.objects.create_user(username, emailinst_, password)
                        user.save()
                        if EMAIL_INSTITUCIONAL_AUTOMATICO:
                            persona.emailinst = user.username + '@' + EMAIL_DOMAIN
                        else:
                            persona.emailinst = f.cleaned_data['emailinst']
                        persona.usuario = user
                        persona.save(request)
                        g = Group.objects.get(pk=ALUMNOS_GROUP_ID)
                        g.user_set.add(user)
                        g.save()
                        inscripcion = Inscripcion(persona=persona,
                                                  fecha=datetime.now().date(),
                                                  especialidad_id=33,
                                                  carrera=f.cleaned_data['carrera'],
                                                  modalidad=f.cleaned_data['modalidad'],
                                                  sesion=f.cleaned_data['sesion'],
                                                  sede=f.cleaned_data['sede'])
                        inscripcion.save(request)
                        log(u'Adicionó una nueva pre inscripción: %s' % inscripcion, request, "add")
                        inscripcion.preguntas_inscripcion()
                        inscripcion.persona.mi_perfil()
                        inscripcion.malla_inscripcion()
                        inscripcion.actualizar_nivel()
                        if USA_TIPOS_INSCRIPCIONES:
                            inscripciontipoinscripcion = InscripcionTipoInscripcion(inscripcion=inscripcion,
                                                                                    tipoinscripcion_id=TIPO_INSCRIPCION_INICIAL)
                            inscripciontipoinscripcion.save(request)
                        inscripciontesdrive = InscripcionTesDrive(inscripcion=inscripcion,
                                                                  licencia=False,
                                                                  record=False,
                                                                  certificado_tipo_sangre=False,
                                                                  prueba_psicosensometrica=False,
                                                                  certificado_estudios=False)
                        inscripciontesdrive.save(request)
                        documentos = DocumentosDeInscripcion(inscripcion=inscripcion,
                                                             titulo=False,
                                                             acta=False,
                                                             cedula=False,
                                                             votacion=False,
                                                             actaconv=False,
                                                             partida_nac=False,
                                                             pre=False,
                                                             observaciones_pre='',
                                                             fotos=False)
                        documentos.save(request)
                        send_html_mail("Preinscripcion exitosa.", "emails/confirmacionpreins.html", {'sistema': request.session['nombresistema'], 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'usuario': username, 'contrasena': password, 't': miinstitucion()}, persona.lista_emails_envio(), REGISTRO_NUEVOS_ESTUDIANTES, cuenta=CUENTAS_CORREOS[0][1])
                        return JsonResponse({'result': 'ok', 'id': inscripcion.id, 'clave': password})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar la registro."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if "persona" in request.session:
            return HttpResponseRedirect("/")
        data = {}
        data['form'] = PreInscritoAutoregistroForm(initial={'fecha': datetime.now().date(),
                                                            'nacimiento': datetime.now().date()})
        return render(request, "preinscrito/view.html", data)