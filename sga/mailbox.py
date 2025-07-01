# -*- coding: latin-1 -*-
from datetime import datetime
import os
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import last_access

from settings import PROFESORES_GROUP_ID, ALUMNOS_GROUP_ID, MAXIMO_ADJUNTO_ENVIO, ARCHIVO_TIPO_GENERAL, \
    EMPLEADORES_GRUPO_ID
from sga.commonviews import adduserdata
from sga.funciones import remover_caracteres_especiales, log
from sga.models import Mensaje, MensajeDestinatario, Persona, Archivo, Coordinacion, Matricula


def handle_uploaded_file(f, name):
    fecha = datetime.now().date()
    hora = datetime.now().time()
    fname = "/".join(['media', 'documentos', fecha.year.__str__(), fecha.month.__str__().zfill(2), fecha.day.__str__().zfill(2), hora.hour.__str__().zfill(2) + hora.minute.__str__().zfill(2) + hora.second.__str__().zfill(2), remover_caracteres_especiales(name)])
    if not os.path.exists(os.path.dirname(fname)):
        os.makedirs(os.path.dirname(fname))
    nfile = open(fname, 'wb+')
    for chunk in f.chunks():
        nfile.write(chunk)
    url = fname[6:]
    nfile.close()
    return url


@login_required(redirect_field_name='ret', login_url='/loginsga')
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    perfilprincipal = request.session['perfilprincipal']
    persona = request.session['persona']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'add':
                try:
                    destinatarioanterior = None
                    if 'reenvio' in request.POST:
                        destinatarioanterior = MensajeDestinatario.objects.get(pk=request.POST['reenvio'])
                    nuevo = Mensaje(asunto=request.POST['asunto'],
                                    contenido=request.POST['mensaje'],
                                    fecha=datetime.now().date(),
                                    hora=datetime.now().time(),
                                    origen=request.session['persona'],
                                    borrador=False)
                    nuevo.save(request)
                    if 'reenvio' not in request.POST:
                        if request.FILES:
                            for name, filename in request.FILES.iteritems():
                                archivo_save = handle_uploaded_file(request.FILES[name], filename._name)
                                archivo = Archivo(nombre=filename._name,
                                                  fecha=datetime.now().date(),
                                                  archivo=archivo_save,
                                                  tipo_id=ARCHIVO_TIPO_GENERAL)
                                archivo.save(request)
                                nuevo.archivo.add(archivo)
                    else:
                        for archivo in destinatarioanterior.mensaje.archivo.all():
                            archivo = Archivo(nombre=archivo.nombre,
                                              fecha=datetime.now().date(),
                                              archivo=archivo.archivo,
                                              tipo_id=ARCHIVO_TIPO_GENERAL)
                            archivo.save(request)
                            nuevo.archivo.add(archivo)
                    destinatarios = request.POST['seleccion'].split(",")
                    for destinatario in destinatarios:
                        nuevodestinatario = MensajeDestinatario(mensaje=nuevo,
                                                                destinatario=Persona.objects.get(pk=int(destinatario)),
                                                                leido=False)
                        nuevodestinatario.save(request)
                        if 'reenvio' in request.POST:
                            nuevodestinatario.reenvio = destinatarioanterior.mensaje
                            nuevodestinatario.save(request)
                    log(u'Adiciono mensaje: %s' % nuevo, request, "add")
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'vermensajein':
                try:
                    mensaje = Mensaje.objects.get(pk=request.POST['id'])
                    if mensaje.mensajedestinatario_set.filter(destinatario__id=request.POST['destinatario']).exists():
                        dest = mensaje.mensajedestinatario_set.filter(destinatario__id=request.POST['destinatario'])[0]
                        dest.leido = True
                        dest.fecha = datetime.now().date()
                        dest.hora = datetime.now().time()
                        dest.save(request)
                        lista = []
                        for archivo in mensaje.archivo.all():
                            lista.append({'nombre': archivo.nombre, 'url': archivo.download_link()})
                        return JsonResponse({'result': 'ok', 'archivos': lista, 'id': mensaje.id, 'contenido': mensaje.contenido, 'asunto': mensaje.asunto, 'datosenvio': mensaje.origen.nombre_completo() + ' - ' + mensaje.fecha.strftime("%d-%m-%Y") + ' a las ' + mensaje.hora.strftime("%I:%M %p")})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'delin':
                try:
                    mensajes = request.POST['ids']
                    ids = mensajes.split(',')
                    for idm in ids:
                        inbox = MensajeDestinatario.objects.get(pk=int(idm))
                        inbox.leido = True
                        inbox.visible = False
                        inbox.save(request)
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'delout':
                try:
                    mensajes = request.POST['ids']
                    ids = mensajes.split(',')
                    for idm in ids:
                        inbox = Mensaje.objects.get(pk=int(idm))
                        inbox.visible = False
                        inbox.save(request)
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'vermensajeout':
                try:
                    mensaje = Mensaje.objects.get(pk=request.POST['id'])
                    if mensaje.mensajedestinatario_set.filter(destinatario__id=request.POST['destinatario']).exists():
                        dest = mensaje.mensajedestinatario_set.filter(destinatario__id=request.POST['destinatario'])[0]
                        dest.leido = True
                        dest.fecha = datetime.now().date()
                        dest.hora = datetime.now().time()
                        dest.save(request)
                        lista = []
                        for archivo in mensaje.archivo.all():
                            lista.append({'nombre': archivo.nombre, 'url': archivo.download_link()})
                        return JsonResponse({'result': 'ok', 'archivos': lista, 'id': mensaje.id, 'contenido': mensaje.contenido, 'asunto': mensaje.asunto, 'datosenvio': mensaje.origen.nombre_completo() + ' - ' + mensaje.fecha.strftime("%d-%m-%Y") + ' a las ' + mensaje.hora.strftime("%I:%M %p")})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'data':
                try:
                    q = request.GET['q'].upper()
                    model = eval('Persona')
                    query = model.flexbox_query(q)
                    return JsonResponse({"results": [{"id": str(x.id), "name": x.flexbox_repr(), "nombre_corto": x.nombre_completo_simple()} for x in query]})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'add':
                try:
                    data['title'] = u'Nuevo mensaje'
                    listacontactos = []
                    # ESTUDIANTES
                    if perfilprincipal.es_estudiante():
                        inscripcion = perfilprincipal.inscripcion
                        matricula = inscripcion.matricula()
                        if matricula:
                            materias = matricula.materiaasignada_set.all()
                            listacontactos.append((0, u"MIS PROFESORES"))
                            for ma in materias:
                                profesores = ma.materia.profesores_materia()
                                if profesores:
                                    largo = profesores.count()
                                    listacontactos.append((0, u"MATERIA - " + ma.materia.asignatura.nombre[:15] + "...", ma.id, ma.materia.asignatura.nombre))
                                    for idx, p in enumerate(profesores):
                                        if idx + 1 < largo:
                                            listacontactos.append((p.profesor.persona.id, p.profesor.persona.nombre_completo_simple()))
                                        else:
                                            listacontactos.append((p.profesor.persona.id, p.profesor.persona.nombre_completo_simple(), 0))
                            listacontactos.append((0, "", 0, 0))

                            listacontactos.append((0, u"MIS COMPAÑEROS"))
                            for ma in materias:
                                listacontactos.append((0, ma.materia.asignatura.nombre, ma.materia.id))
                                largo = ma.materia.materiaasignada_set.count()
                                for idx, m in enumerate(ma.materia.materiaasignada_set.all()):
                                    if idx + 1 < largo:
                                        listacontactos.append((m.matricula.inscripcion.persona.id, m.matricula.inscripcion.persona.nombre_completo_simple()))
                                    else:
                                        listacontactos.append((m.matricula.inscripcion.persona.id, m.matricula.inscripcion.persona.nombre_completo_simple(), 0))
                            listacontactos.append((0, "", 0, 0))
                        grupos = Group.objects.all().exclude(id__in=[ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID])
                        listacontactos.append((0, u"PERSONAL INSTITUCION"))
                        for grupo in grupos:
                            personas = Persona.objects.filter(usuario__groups=grupo, usuario__is_active=True).order_by('nombres', 'apellido1')
                            largo = personas.count()
                            if largo > 0:
                                listacontactos.append((0, grupo.name, grupo.id))
                                for idx, m in enumerate(personas):
                                    if idx + 1 < largo:
                                        listacontactos.append((m.id, m.nombre_completo_simple()))
                                    else:
                                        listacontactos.append((m.id, m.nombre_completo_simple(), 0))
                        listacontactos.append((0, "", 0, 0))

                    # ADMINISTRATIVOS
                    else:
                        grupos = Group.objects.all().exclude(id__in=[ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID, EMPLEADORES_GRUPO_ID])
                        listacontactos.append((0, u"PERSONAL INSTITUCION"))
                        for grupo in grupos:
                            personas = Persona.objects.filter(usuario__groups=grupo, usuario__is_active=True)
                            if personas:
                                listacontactos.append((0, grupo.name, grupo.id))
                                for idx, m in enumerate(personas):
                                    if idx + 1 < personas.count():
                                        listacontactos.append((m.id, m.nombre_completo_simple()))
                                    else:
                                        listacontactos.append((m.id, m.nombre_completo_simple(), 0))
                        listacontactos.append((0, "", 0, 0))
                        listacontactos.append((0, u"DOCENTES ACTIVOS"))
                        personas = Persona.objects.filter(profesor__isnull=False, profesor__activo=True).order_by('nombres', 'apellido1')
                        if personas:
                            listacontactos.append((0, "DOCENTES"))
                            for idx, m in enumerate(personas):
                                if idx + 1 < personas.count():
                                    listacontactos.append((m.id, m.nombre_completo_simple()))
                                else:
                                    listacontactos.append((m.id, m.nombre_completo_simple(), 0))
                        listacontactos.append((0, "", 0, 0))
                        listacontactos.append((0, u"ALUMNOS MATRICULADOS"))
                        periodo = request.session['periodo']
                        coordinaciones = Coordinacion.objects.all()
                        for coordinacion in coordinaciones:
                            personas = Matricula.objects.filter(nivel__nivellibrecoordinacion__coordinacion=coordinacion, nivel__periodo_id=periodo.id).order_by('inscripcion__persona__nombres', 'inscripcion__persona__apellido1')
                            largo = personas.count()
                            if largo > 0:
                                listacontactos.append((0, coordinacion.nombre, coordinacion.id))
                                for idx, m in enumerate(personas):
                                    if idx + 1 < largo:
                                        listacontactos.append((m.inscripcion.persona.id, m.inscripcion.persona.nombre_completo_simple()))
                                    else:
                                        listacontactos.append((m.inscripcion.persona.id, m.inscripcion.persona.nombre_completo_simple(), 0))
                            listacontactos.append((0, "", 0, 0))
                        if persona.profesor():
                            listacontactos.append((0, "", 0, 0))
                            listacontactos.append((0, u"MIS MATERIAS"))
                            periodo = request.session['periodo']
                            profesormaterias = persona.profesor().mis_materias(periodo)
                            if profesormaterias:
                                for profesormateria in profesormaterias:
                                    materia = profesormateria.materia
                                    personas = materia.asignados_a_esta_materia()
                                    largo = personas.count()
                                    if largo > 0:
                                        listacontactos.append((0, u"MATERIA - " + profesormateria.materia.asignatura.nombre[:15] + "...", profesormateria.materia.id, profesormateria.materia.asignatura.nombre))
                                        for idx, m in enumerate(personas):
                                            if idx + 1 < largo:
                                                listacontactos.append((m.matricula.inscripcion.persona.id, m.matricula.inscripcion.persona.nombre_completo_simple()))
                                            else:
                                                listacontactos.append((m.matricula.inscripcion.persona.id, m.matricula.inscripcion.persona.nombre_completo_simple(), 0))
                                    listacontactos.append((0, "", 0, 0))

                    data['listacontactos'] = listacontactos
                    data['limite_ficheros'] = MAXIMO_ADJUNTO_ENVIO
                    data['asunto_respuesta'] = None
                    if "respuesta" in request.GET:
                        data['respuesta'] = Persona.objects.get(pk=request.GET['respuesta'])
                        data['asunto_respuesta'] = Mensaje.objects.get(pk=request.GET['asunto_respuesta']).asunto
                    if "reenvio" in request.GET:
                        data['reenvio'] = MensajeDestinatario.objects.get(pk=request.GET['reenvio'])
                    return render(request, "mailbox/nuevomensaje.html", data)
                except Exception as ex:
                    pass

            elif action == "vin":
                try:
                    data['title'] = u'Mensaje'
                    persona = request.session['persona']
                    mensaje = Mensaje.objects.get(pk=request.GET['id'])
                    destinatario = mensaje.mensajedestinatario_set.filter(destinatario=persona)[0]
                    destinatario.leido = True
                    destinatario.save(request)
                    data['mensaje'] = mensaje
                    data['destinatario'] = destinatario
                    return render(request, "mailbox/vermensajein.html", data)
                except Exception as ex:
                    pass

            elif action == "vout":
                try:
                    data['title'] = u'Mensaje'
                    mensaje = Mensaje.objects.get(pk=request.GET['id'])
                    data['mensaje'] = mensaje
                    return render(request, "mailbox/vermensajeout.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Buzon de mensajes'
            data['inbox'] = MensajeDestinatario.objects.filter(destinatario=persona, visible=True).order_by('-mensaje__fecha', '-mensaje__hora')
            data['outbox'] = Mensaje.objects.filter(origen=persona, borrador=False, visible=True).order_by('-fecha', '-hora')
            return render(request, "mailbox/inbox.html", data)