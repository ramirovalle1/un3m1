# -*- coding: UTF-8 -*-
import collections
import json
import random
import sys
from datetime import datetime, timedelta

from django.contrib import messages
from django.forms import model_to_dict
from xlwt import *
from xlwt import easyxf
import xlwt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from django.db.models.query_utils import Q
from decorators import secure_module
from sga.commonviews import adduserdata
from sga.forms import LlamadaRealizadaForm, RespuestaRecibidaForm, SolicitudTutorRespuestaForm, \
    SolicitudTutorObservacionForm
from sga.funciones import log, generar_nombre, convertir_fecha, MiPaginador, convertir_fecha_invertida
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import Materia, ProfesorMateria, DiapositivaSilaboSemanal, GuiaEstudianteSilaboSemanal, \
    GuiaDocenteSilaboSemanal, CompendioSilaboSemanal, Inscripcion, SeguimientoTutor, MatriculaSeguimientoTutor, \
    Matricula, CUENTAS_CORREOS, miinstitucion, CorreoMatriculaSeguimientoTutor, LlamadasMatriculaSeguimientoTutor, \
    RespuestasMatriculaSeguimientoTutor, SoporteAcademicoTutor, SeguimientoTutorSoporte, \
    MatriculaSeguimientoTutorSoporte, CorreoMatriculaSeguimientoTutorSoporte, LlamadasMatriculaTutorSoporte, \
    RespuestasMatriculaTutorSoporte, PonderacionSeguimiento, SolicitudTutorSoporteMatricula, \
    ESTADO_SOLICITUD_TUTOR, RespuestaSolicitudTutorSoporteMatricula, ObservacionSolicitudTutorSoporteMatricula, \
    Profesor, ProfesorDistributivoHoras, MateriaAsignada, Carrera, CorreoMatriculaTutorSoporte, \
    SolicitudTutorSoporteMateria, \
    RespuestaSolicitudTutorSoporteMateria, ObservacionSolicitudTutorSoporteMateria, CorreoMatriculaTutorNotificacion, \
    TipoProfesor, Notificacion, DetalleGrupoAsignatura
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt
import calendar
from django.db.models import Count
from openpyxl import workbook as openxl
from openpyxl.styles import Font as openxlFont
from openpyxl.styles.alignment import Alignment as alin


@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
# @secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_profesor():
        return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    data['profesor'] = profesor = perfilprincipal.profesor
    periodo = request.session['periodo']
    hoy = datetime.now().date()
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'verestudiante':
            try:
                id = int(request.POST['id'])
                inscripcion = Inscripcion.objects.get(pk=id)
                data['inscripcion'] = inscripcion
                data['persona'] = inscripcion.persona
                template = get_template("pro_tutoria/verestudiante.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        if action == 'verseguimiento':
            try:
                matricula = Matricula.objects.get(pk=int(request.POST['id']))
                materia = Materia.objects.get(pk=int(request.POST['idmateria']))
                data['persona'] = matricula.inscripcion.persona
                data['correos'] = CorreoMatriculaSeguimientoTutor.objects.filter(status=True,matriculaseguimientotutor__matricula=matricula,matriculaseguimientotutor__status=True, matriculaseguimientotutor__seguimiento__status=True, matriculaseguimientotutor__seguimiento__materia=materia).order_by('fecha')
                data['llamadas'] = LlamadasMatriculaSeguimientoTutor.objects.filter(status=True,matriculaseguimientotutor__matricula=matricula,matriculaseguimientotutor__status=True, matriculaseguimientotutor__seguimiento__status=True, matriculaseguimientotutor__seguimiento__materia=materia).order_by('fecha')
                data['respuestas'] = RespuestasMatriculaSeguimientoTutor.objects.filter(status=True,matriculaseguimientotutor__matricula=matricula,matriculaseguimientotutor__status=True, matriculaseguimientotutor__seguimiento__status=True, matriculaseguimientotutor__seguimiento__materia=materia).order_by('fecha')
                template = get_template("pro_tutoria/verseguimiento.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        if action == 'veracciones':
            try:
                id = int(encrypt(request.POST['id']))
                matriculaseguimiento = MatriculaSeguimientoTutor.objects.get(pk=id)
                seguimiento = matriculaseguimiento.seguimiento
                # matricula = matriculaseguimiento.matricula
                # materia = seguimiento.materia
                # fechai = seguimiento.fechainicio
                # fechaf = seguimiento.fechafin
                # idmatriculas = CorreoMatriculaSeguimientoTutor.objects.values_list('matricula__id', flat=True).filter(matricula=matricula, materia=materia,status=True, fecha__range=(fechai,fechaf))
                data['matricula'] = matriculaseguimiento
                template = get_template("pro_tutoria/veracciones.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        if action == 'veraccionessoporte':
            try:
                id = int(encrypt(request.POST['id']))
                matricula = Matricula.objects.get(pk=id)
                # matricula = matriculaseguimiento.matricula
                # materia = seguimiento.materia
                # fechai = seguimiento.fechainicio
                # fechaf = seguimiento.fechafin
                # idmatriculas = CorreoMatriculaSeguimientoTutor.objects.values_list('matricula__id', flat=True).filter(matricula=matricula, materia=materia,status=True, fecha__range=(fechai,fechaf))
                data['matricula'] = matricula
                data['profesor'] = profesor
                template = get_template("pro_tutoria/veracciones.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        if action == 'notificaramarillo':
            try:
                hoy = datetime.now().date()
                lista = json.loads(request.POST['lista'])
                # materia = Materia.objects.get(pk=int(request.POST['id']))
                seguimiento = SeguimientoTutor.objects.get(pk=int(request.POST['idseguimiento']))
                materia = seguimiento.materia.asignaturamalla.asignatura.nombre
                # observacion = "Reciba un cordial saludo de quienes conformamos la Universidad Estatal de Milagro, el motivo de este correo electrónico es invitarlo a continuar participando del proceso de formación, hemos visto que su interacción en el aula virtual ha visto disminuido, nos gustaría saber si hay algo en que podamos ayudarlo para que continúe con ahincó su proceso de formación. <br>En todo caso si considera necesario se puede poner en contacto conmigo en calidad de DOCENTE TUTOR, mis datos de contacto se encuentra en la firma del presente mail.<br>Saludos,"
                observacion = request.POST['observacion']
                for elemento in lista:
                    # matricula = Matricula.objects.get(pk=int(elemento))
                    matriculaseguimiento = MatriculaSeguimientoTutor.objects.get(matricula__id=int(elemento), seguimiento=seguimiento)
                    persona = matriculaseguimiento.matricula.inscripcion.persona
                    c = CorreoMatriculaSeguimientoTutor(matriculaseguimientotutor=matriculaseguimiento, fecha=hoy, contenido=observacion, tipo=1)
                    c.save(request)
                    send_html_mail("Notificación", "emails/notificacionamarillo.html", {'t': miinstitucion(),'sistema': request.session['nombresistema'],'persona': persona, 'profesor': profesor, 'observacion': observacion, 'materia': materia, 'titulo': 'Notificación de acompañamiento y soporte'}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[0][1])
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        if action == 'notificaramarillosoporte':
            try:
                hoy = datetime.now().date()
                lista = json.loads(request.POST['lista'])
                # materia = Materia.objects.get(pk=int(request.POST['id']))
                seguimiento = SeguimientoTutorSoporte.objects.get(pk=int(request.POST['idseguimiento']))
                materia = seguimiento.materia.asignaturamalla.asignatura.nombre
                # observacion = "Reciba un cordial saludo de quienes conformamos la Universidad Estatal de Milagro, el motivo de este correo electrónico es invitarlo a continuar participando del proceso de formación, hemos visto que su interacción en el aula virtual ha visto disminuido, nos gustaría saber si hay algo en que podamos ayudarlo para que continúe con ahincó su proceso de formación. <br>En todo caso si considera necesario se puede poner en contacto conmigo en calidad de DOCENTE TUTOR, mis datos de contacto se encuentra en la firma del presente mail.<br>Saludos,"
                observacion = request.POST['observacion']
                for elemento in lista:
                    # matricula = Matricula.objects.get(pk=int(elemento))
                    matriculaseguimiento = MatriculaSeguimientoTutorSoporte.objects.get(matricula__id=int(elemento), seguimiento=seguimiento)
                    persona = matriculaseguimiento.matricula.inscripcion.persona
                    c = CorreoMatriculaSeguimientoTutorSoporte(matriculaseguimientotutor=matriculaseguimiento,
                                                               fecha=hoy,
                                                               contenido=observacion,
                                                               tipo=1)
                    c.save(request)
                    send_html_mail("Notificación", "emails/notificacionamarillo.html", {'t': miinstitucion(),'sistema': request.session['nombresistema'],'persona': persona, 'profesor': profesor, 'observacion': observacion, 'materia': materia}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[0][1])
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        if action == 'notificarcorreooporte':
            try:
                hoy = datetime.now().date()
                lista = json.loads(request.POST['lista'])
                observacion = request.POST['observacion']
                for elemento in lista:
                    # matricula = Matricula.objects.get(pk=int(elemento))
                    matricula = Matricula.objects.get(id=int(elemento))
                    persona = matricula.inscripcion.persona
                    c = CorreoMatriculaTutorSoporte(matricula=matricula,
                                                    tutor=profesor,
                                                    fecha=hoy,
                                                    contenido=observacion,
                                                    tipo=1)
                    c.save(request)
                    send_html_mail("Notificación", "emails/notificacioncorreo.html", {'t': miinstitucion(),'sistema': request.session['nombresistema'],'persona': persona, 'profesor': profesor, 'observacion': observacion}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[0][1])
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        if action == 'notificarestudiante':
            try:
                hoy = datetime.now().date()
                lista = json.loads(request.POST['lista'])
                observacion = request.POST['observacion']
                for elemento in lista:
                    # matricula = Matricula.objects.get(pk=int(elemento))
                    matricula = Matricula.objects.get(id=int(elemento))
                    persona = matricula.inscripcion.persona
                    lista = persona.emailpersonal()
                    c = CorreoMatriculaTutorNotificacion(matricula=matricula,
                                                    tutor=profesor,
                                                    fecha=hoy,
                                                    contenido=observacion)
                    c.save(request)
                    send_html_mail("Notificación", "emails/notificacioncorreo.html", {'t': miinstitucion(),'sistema': request.session['nombresistema'],
                                                                                      'persona': persona, 'profesor': profesor, 'observacion': observacion},
                                                                                        lista, [], cuenta=CUENTAS_CORREOS[0][1])
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        if action == 'notificarrojo':
            try:
                hoy = datetime.now().date()
                lista = json.loads(request.POST['lista'])
                # materia = Materia.objects.get(pk=int(request.POST['id']))
                seguimiento = SeguimientoTutor.objects.get(pk=int(request.POST['idseguimiento']))
                materia = seguimiento.materia.asignaturamalla.asignatura.nombre
                observacion = request.POST['observacion']
                for elemento in lista:
                    # matricula = Matricula.objects.get(pk=int(elemento))
                    matriculaseguimiento = MatriculaSeguimientoTutor.objects.get(matricula__id=int(elemento),seguimiento=seguimiento)
                    persona = matriculaseguimiento.matricula.inscripcion.persona
                    c = CorreoMatriculaSeguimientoTutor(matriculaseguimientotutor=matriculaseguimiento,
                                                        # materia=materia,
                                                        fecha=hoy,
                                                        contenido=observacion,
                                                        tipo=2)
                    c.save(request)
                    send_html_mail("Notificación", "emails/notificacionrojo.html", {'t': miinstitucion(),'sistema': request.session['nombresistema'],'persona': persona, 'profesor': profesor, 'observacion': observacion, 'materia': materia,  'titulo': 'Notificación de acompañamiento y soporte'}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[0][1])
                    # send_html_mail("Notificación", "emails/notificacionrojo.html", {'t': miinstitucion(),'sistema': request.session['nombresistema'],'persona': persona, 'profesor': profesor, 'observacion': observacion, 'materia': materia}, ['chrisstianandres@gmail.com'], [], cuenta=CUENTAS_CORREOS[0][1])
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        if action == 'notificarrojosoporte':
            try:
                hoy = datetime.now().date()
                lista = json.loads(request.POST['lista'])
                # materia = Materia.objects.get(pk=int(request.POST['id']))
                seguimiento = SeguimientoTutorSoporte.objects.get(pk=int(request.POST['idseguimiento']))
                materia = seguimiento.materia.asignaturamalla.asignatura.nombre
                observacion = request.POST['observacion']
                for elemento in lista:
                    # matricula = Matricula.objects.get(pk=int(elemento))
                    matriculaseguimiento = MatriculaSeguimientoTutorSoporte.objects.get(matricula__id=int(elemento),seguimiento=seguimiento)
                    persona = matriculaseguimiento.matricula.inscripcion.persona
                    c = CorreoMatriculaSeguimientoTutorSoporte(matriculaseguimientotutor=matriculaseguimiento,
                                                               # materia=materia,
                                                               fecha=hoy,
                                                               contenido=observacion,
                                                               tipo=2)
                    c.save(request)
                    send_html_mail("Notificación", "emails/notificacionrojo.html", {'t': miinstitucion(),'sistema': request.session['nombresistema'],'persona': persona, 'profesor': profesor, 'observacion': observacion, 'materia': materia}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[0][1])
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        elif action == 'addllamada':
            try:
                form = LlamadaRealizadaForm(request.POST)
                if form.is_valid():
                    matriculaseguimiento = MatriculaSeguimientoTutor.objects.get(pk=int(request.POST['id']))
                    llamada=LlamadasMatriculaSeguimientoTutor(matriculaseguimientotutor = matriculaseguimiento,
                                                              fecha=form.cleaned_data['fecha'],
                                                              hora=form.cleaned_data['hora'],
                                                              minutos=form.cleaned_data['minutos'],
                                                              descripcion=form.cleaned_data['descripcion'])
                    llamada.save(request)
                    log(u'Adiciono llamada realizada : %s' % (llamada), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addllamadasoporte':
            try:
                form = LlamadaRealizadaForm(request.POST)
                if form.is_valid():
                    matricula = Matricula.objects.get(pk=int(request.POST['id']))
                    llamada=LlamadasMatriculaTutorSoporte(matricula = matricula,
                                                          tutor=profesor,
                                                          fecha=form.cleaned_data['fecha'],
                                                          hora=form.cleaned_data['hora'],
                                                          minutos=form.cleaned_data['minutos'],
                                                          descripcion=form.cleaned_data['descripcion'])
                    llamada.save(request)
                    log(u'Adiciono llamada realizada : %s' % (llamada), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        # elif action == 'addllamadasoporte':
        #     try:
        #         form = LlamadaRealizadaForm(request.POST)
        #         if form.is_valid():
        #                 matriculaseguimiento = MatriculaSeguimientoTutorSoporte.objects.get(pk=int(request.POST['id']))
        #                 llamada=LlamadasMatriculaSeguimientoTutorSoporte(matriculaseguimientotutor = matriculaseguimiento,
        #                                                                  fecha=form.cleaned_data['fecha'],
        #                                                                  hora=form.cleaned_data['hora'],
        #                                                                  minutos=form.cleaned_data['minutos'],
        #                                                                  descripcion=form.cleaned_data['descripcion'])
        #                 llamada.save(request)
        #                 log(u'Adiciono llamada realizada : %s' % (llamada), request, "add")
        #                 return JsonResponse({"result": "ok"})
        #         else:
        #              raise NameError('Error')
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        #
        elif action == 'addrespuesta':
            try:
                form = RespuestaRecibidaForm(request.POST)
                if form.is_valid():
                    matriculaseguimiento = MatriculaSeguimientoTutor.objects.get(pk=int(request.POST['id']))
                    respuesta=RespuestasMatriculaSeguimientoTutor(matriculaseguimientotutor = matriculaseguimiento,
                                                                  fecha=form.cleaned_data['fecha'],
                                                                  hora=form.cleaned_data['hora'],
                                                                  tipo=form.cleaned_data['tipo'],
                                                                  descripcion=form.cleaned_data['descripcion'])
                    respuesta.save(request)
                    log(u'Adiciono respuesta recibida : %s' % (respuesta), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addrespuestasoporte':
            try:
                form = RespuestaRecibidaForm(request.POST)
                if form.is_valid():
                    matricula = Matricula.objects.get(pk=int(request.POST['id']))
                    respuesta=RespuestasMatriculaTutorSoporte(matricula = matricula,
                                                              tutor=profesor,
                                                              fecha=form.cleaned_data['fecha'],
                                                              hora=form.cleaned_data['hora'],
                                                              tipo=form.cleaned_data['tipo'],
                                                              descripcion=form.cleaned_data['descripcion'])
                    respuesta.save(request)
                    log(u'Adiciono respuesta recibida : %s' % (respuesta), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        # elif action == 'addrespuestasoporte':
        #     try:
        #         form = RespuestaRecibidaForm(request.POST)
        #         if form.is_valid():
        #                 matriculaseguimiento = MatriculaSeguimientoTutorSoporte.objects.get(pk=int(request.POST['id']))
        #                 respuesta=RespuestasMatriculaSeguimientoTutorSoporte(matriculaseguimientotutor = matriculaseguimiento,
        #                                                                      fecha=form.cleaned_data['fecha'],
        #                                                                      hora=form.cleaned_data['hora'],
        #                                                                      tipo=form.cleaned_data['tipo'],
        #                                                                      descripcion=form.cleaned_data['descripcion'])
        #                 respuesta.save(request)
        #                 log(u'Adiciono respuesta recibida : %s' % (respuesta), request, "add")
        #                 return JsonResponse({"result": "ok"})
        #         else:
        #              raise NameError('Error')
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        #
        elif action == 'respondersolicitud':
            try:
                form = SolicitudTutorRespuestaForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]

                    if arch.sizee > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if exte.lower() == 'pdf' or exte.lower() == 'jpg' or exte.lower() == 'jpeg':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})

                solicitud = SolicitudTutorSoporteMatricula.objects.get(pk=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    archivo = None
                    if 'archivo' in request.FILES:
                        archivo = request.FILES['archivo']
                        archivo._name = generar_nombre("respondersolicitud", archivo._name)

                    respuesta = RespuestaSolicitudTutorSoporteMatricula(solicitud=solicitud,
                                                                        descripcion=form.cleaned_data['respuesta'],
                                                                        archivo=archivo)
                    respuesta.save(request)
                    solicitud.estado = 3
                    solicitud.fecharespuesta = datetime.now().date()
                    solicitud.tutor = profesor
                    solicitud.save(request)
                    log(u'Ingreso respuesta solicitud: %s' % respuesta, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'observacionsolicitud':
            try:
                form = SolicitudTutorObservacionForm(request.POST)
                solicitud = SolicitudTutorSoporteMatricula.objects.get(pk=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    observacion = ObservacionSolicitudTutorSoporteMatricula(solicitud=solicitud,
                                                                            observacion=form.cleaned_data['observacion'])
                    observacion.save(request)
                    log(u'Ingreso observacion solicitud: %s' % observacion, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'eliminarseguimiento':
            try:
                seguimiento = SeguimientoTutor.objects.get(pk=request.POST['id'])
                log(u'Elimino seguimiento tutor: %s ' % (seguimiento), request, "del")
                seguimiento.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'calcularseguimiento':
            try:
                seguimiento = SeguimientoTutor.objects.get(pk=request.POST['id'])
                ponderacion_plataforma = PonderacionSeguimiento.objects.filter(periodo=periodo,tiposeguimiento=1).first()
                ponderacion_recurso = PonderacionSeguimiento.objects.filter(periodo=periodo, tiposeguimiento=2).first()
                ponderacion_actividad = PonderacionSeguimiento.objects.filter(periodo=periodo,tiposeguimiento=3).first()
                if not ponderacion_plataforma or not ponderacion_recurso or not ponderacion_actividad:
                    return JsonResponse({"result": "bad", "mensaje": u"No existe configurado los porcentajes de ponderación para este periodo."})
                ponderacion_plataforma = ponderacion_plataforma.porcentaje
                ponderacion_recurso = ponderacion_recurso.porcentaje
                ponderacion_actividad = ponderacion_actividad.porcentaje
                materia = seguimiento.materia
                materiasasignadas = materia.materiaasignada_set.filter(matricula__retiradomatricula=False, retiramateria=False, status=True, matricula__status=True).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                hoy = datetime.now().date()
                if seguimiento:
                    finic = seguimiento.fechainicio
                    ffinc = seguimiento.fechafin

                lista = []
                listaalumnos = []
                if materia.tareas_asignatura_moodle(finic, ffinc):
                    listaidtareas = []
                    for listatarea in materia.tareas_asignatura_moodle(finic, ffinc):
                        listaidtareas.append(listatarea[0])
                    lista.append(listaidtareas)
                else:
                    lista.append(0)
                if materia.foros_asignatura_moodledos(finic, ffinc):
                    listaidforum = []
                    for listaforo in materia.foros_asignatura_moodledos(finic, ffinc):
                        listaidforum.append(listaforo[0])
                    lista.append(listaidforum)
                else:
                    lista.append(0)
                if materia.test_asignatura_moodle(finic, ffinc):
                    listaidtest = []
                    for listatest in materia.test_asignatura_moodle(finic, ffinc):
                        listaidtest.append(listatest)
                    lista.append(listaidtest)
                else:
                    lista.append(0)
                diapositivas = DiapositivaSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia,silabosemanal__fechafinciosemana__range=(finic, ffinc),silabosemanal__silabo__status=True,iddiapositivamoodle__gt=0)
                if diapositivas:
                    listaidpresentacion = []
                    for listadias in diapositivas:
                        listaidpresentacion.append(listadias.iddiapositivamoodle)
                    lista.append(listaidpresentacion)
                else:
                    lista.append(0)
                fechacalcula = datetime.strptime('2020-07-24', '%Y-%m-%d').date()
                if finic > fechacalcula:
                    guiasestudiantes = GuiaEstudianteSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia, silabosemanal__fechafinciosemana__range=(finic, ffinc),silabosemanal__silabo__status=True, idguiaestudiantemoodle__gt=0)
                    if guiasestudiantes:
                        listaidguiaestudiante = []
                        for listaguiasestu in guiasestudiantes:
                            listaidguiaestudiante.append(listaguiasestu.idguiaestudiantemoodle)
                        lista.append(listaidguiaestudiante)
                    else:
                        lista.append(0)
                    guiasdocentes = GuiaDocenteSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia,silabosemanal__fechafinciosemana__range=(finic, ffinc),silabosemanal__silabo__status=True,idguiadocentemoodle__gt=0)
                    if guiasdocentes:
                        listaidguiadocente = []
                        for listaguiasdoce in guiasdocentes:
                            listaidguiadocente.append(listaguiasdoce.idguiadocentemoodle)
                        lista.append(listaidguiadocente)
                    else:
                        lista.append(0)
                    compendios = CompendioSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia,silabosemanal__fechafinciosemana__range=(finic, ffinc),silabosemanal__silabo__status=True,idmcompendiomoodle__gt=0)
                    if compendios:
                        listaidcompendio = []
                        for listacompendios in compendios:
                            listaidcompendio.append(listacompendios.idmcompendiomoodle)
                        lista.append(listaidcompendio)
                    else:
                        lista.append(0)
                else:
                    lista.append(0)
                    lista.append(0)
                    lista.append(0)
                totalverde = 0
                totalamarillo = 0
                totalrojo = 0
                for alumnos in materiasasignadas:
                    nombres = alumnos.matricula.inscripcion.persona.apellido1 + ' ' + alumnos.matricula.inscripcion.persona.apellido2 + ' ' + alumnos.matricula.inscripcion.persona.nombres
                    esppl = 'NO'
                    esdiscapacidad = 'NO'
                    if alumnos.matricula.inscripcion.persona.ppl:
                        esppl = 'SI'
                    if alumnos.matricula.inscripcion.persona.mi_perfil().tienediscapacidad:
                        esdiscapacidad = 'SI'
                    totalaccesologuin = float("{:.2f}".format(alumnos.matricula.inscripcion.persona.total_loguinusermoodle(finic, ffinc)))
                    totalaccesorecurso = float("{:.2f}".format(alumnos.matricula.inscripcion.persona.total_accesorecursomoodle(finic, ffinc,materia.idcursomoodle, lista)))
                    if totalaccesologuin == 0:
                        totalcumplimiento = 0
                    else:
                        totalcumplimiento = float("{:.2f}".format(alumnos.matricula.inscripcion.persona.total_cumplimientomoodle(finic, ffinc,materia.idcursomoodle, lista)))

                    totalporcentaje = float("{:.2f}".format(((((totalaccesologuin * ponderacion_plataforma) / 100) + ((totalaccesorecurso * ponderacion_recurso) / 100) + ((totalcumplimiento * ponderacion_actividad) / 100)))))

                    if totalporcentaje >= 70:
                        colorfondo = '5bb75b'
                        totalverde += 1
                    if totalporcentaje <= 30:
                        colorfondo = 'b94a48'
                        totalrojo += 1
                    if totalporcentaje > 31 and totalporcentaje < 70:
                        colorfondo = 'faa732'
                        totalamarillo += 1
                    listaalumnos.append([alumnos.matricula.inscripcion.persona.cedula,
                                         nombres,
                                         esppl,
                                         esdiscapacidad,
                                         totalaccesologuin,
                                         totalaccesorecurso,
                                         totalcumplimiento,
                                         totalporcentaje,
                                         alumnos.matricula.inscripcion.persona.email,
                                         alumnos.matricula.inscripcion.persona.telefono,
                                         alumnos.matricula.inscripcion.persona.canton,
                                         colorfondo,
                                         alumnos.matricula.inscripcion.id,
                                         alumnos.matricula])

                porcentajeverde = float("{:.2f}".format((totalverde / materiasasignadas.count()) * 100))
                porcentajerojo = float("{:.2f}".format((totalrojo / materiasasignadas.count()) * 100))
                porcentajeamarillo = float("{:.2f}".format((totalamarillo / materiasasignadas.count()) * 100))

                for integrantes in listaalumnos:
                    ppl = False
                    if integrantes[2] == 'SI':
                        ppl = True
                    discapacidad = False
                    if integrantes[3] == 'SI':
                        discapacidad = True
                    if not MatriculaSeguimientoTutor.objects.filter(seguimiento=seguimiento, matricula=integrantes[13]).exists():
                        m = MatriculaSeguimientoTutor(seguimiento=seguimiento,
                                                      matricula=integrantes[13],
                                                      ppl=ppl,
                                                      discapacidad=discapacidad,
                                                      accesoplataforma=integrantes[4],
                                                      accesorecurso=integrantes[5],
                                                      cumplimientoactividades=integrantes[6],
                                                      promediovariables=integrantes[7],
                                                      color=integrantes[11])
                        m.save(request)
                    else:
                        m = MatriculaSeguimientoTutor.objects.get(seguimiento=seguimiento, matricula=integrantes[13])
                        m.ppl = ppl
                        m.discapacidad = discapacidad
                        m.accesoplataforma = integrantes[4]
                        m.accesorecurso = integrantes[5]
                        m.cumplimientoactividades = integrantes[6]
                        m.promediovariables = integrantes[7]
                        m.color = integrantes[11]
                        m.save(request)

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al calcular seguimiento los datos."})

        elif action == 'calcularseguimientoposgrado':
            try:
                seguimiento = SeguimientoTutor.objects.get(pk=int(encrypt(request.POST['codseguimiento'])))
                seguimiento.save()
                ponderacion_plataforma = 33
                ponderacion_recurso = 33
                ponderacion_actividad = 34
                materia = seguimiento.materia
                materiasasignadas = materia.materiaasignada_set.filter(matricula__retiradomatricula=False, retiramateria=False, status=True, matricula__status=True).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                hoy = datetime.now().date()
                if seguimiento:
                    finic = seguimiento.fechainicio
                    ffinc = seguimiento.fechafin

                lista = []
                listaalumnos = []
                if materia.tareas_asignatura_moodle(finic, ffinc):
                    listaidtareas = []
                    for listatarea in materia.tareas_asignatura_moodle(finic, ffinc):
                        listaidtareas.append(listatarea[0])
                    lista.append(listaidtareas)
                else:
                    lista.append(0)
                if materia.foros_asignatura_moodledos(finic, ffinc):
                    listaidforum = []
                    for listaforo in materia.foros_asignatura_moodledos(finic, ffinc):
                        listaidforum.append(listaforo[0])
                    lista.append(listaidforum)
                else:
                    lista.append(0)
                if materia.test_asignatura_moodle(finic, ffinc):
                    listaidtest = []
                    for listatest in materia.test_asignatura_moodle(finic, ffinc):
                        listaidtest.append(listatest)
                    lista.append(listaidtest)
                else:
                    lista.append(0)
                diapositivas = DiapositivaSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia,silabosemanal__fechafinciosemana__range=(finic, ffinc),silabosemanal__silabo__status=True,iddiapositivamoodle__gt=0)
                if diapositivas:
                    listaidpresentacion = []
                    for listadias in diapositivas:
                        listaidpresentacion.append(listadias.iddiapositivamoodle)
                    lista.append(listaidpresentacion)
                else:
                    lista.append(0)
                fechacalcula = datetime.strptime('2020-07-24', '%Y-%m-%d').date()
                if finic > fechacalcula:
                    guiasestudiantes = GuiaEstudianteSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia, silabosemanal__fechafinciosemana__range=(finic, ffinc),silabosemanal__silabo__status=True, idguiaestudiantemoodle__gt=0)
                    if guiasestudiantes:
                        listaidguiaestudiante = []
                        for listaguiasestu in guiasestudiantes:
                            listaidguiaestudiante.append(listaguiasestu.idguiaestudiantemoodle)
                        lista.append(listaidguiaestudiante)
                    else:
                        lista.append(0)
                    guiasdocentes = GuiaDocenteSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia,silabosemanal__fechafinciosemana__range=(finic, ffinc),silabosemanal__silabo__status=True,idguiadocentemoodle__gt=0)
                    if guiasdocentes:
                        listaidguiadocente = []
                        for listaguiasdoce in guiasdocentes:
                            listaidguiadocente.append(listaguiasdoce.idguiadocentemoodle)
                        lista.append(listaidguiadocente)
                    else:
                        lista.append(0)
                    compendios = CompendioSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia,silabosemanal__fechafinciosemana__range=(finic, ffinc),silabosemanal__silabo__status=True,idmcompendiomoodle__gt=0)
                    if compendios:
                        listaidcompendio = []
                        for listacompendios in compendios:
                            listaidcompendio.append(listacompendios.idmcompendiomoodle)
                        lista.append(listaidcompendio)
                    else:
                        lista.append(0)
                else:
                    lista.append(0)
                    lista.append(0)
                    lista.append(0)
                totalverde = 0
                totalamarillo = 0
                totalrojo = 0
                for alumnos in materiasasignadas:
                    nombres = alumnos.matricula.inscripcion.persona.apellido1 + ' ' + alumnos.matricula.inscripcion.persona.apellido2 + ' ' + alumnos.matricula.inscripcion.persona.nombres
                    esppl = 'NO'
                    esdiscapacidad = 'NO'
                    if alumnos.matricula.inscripcion.persona.ppl:
                        esppl = 'SI'
                    if alumnos.matricula.inscripcion.persona.mi_perfil().tienediscapacidad:
                        esdiscapacidad = 'SI'
                    totalaccesologuin = float("{:.2f}".format(alumnos.matricula.inscripcion.persona.total_loguinusermoodleposgrado(finic, ffinc)))
                    totalaccesorecurso = float("{:.2f}".format(alumnos.matricula.inscripcion.persona.total_accesorecursomoodleposgrado(finic, ffinc,materia.idcursomoodle, lista)))
                    totalcumplimiento = float("{:.2f}".format(alumnos.matricula.inscripcion.persona.total_cumplimientomoodleposgrado(finic, ffinc,materia.idcursomoodle, lista)))
                    totalporcentaje = float("{:.2f}".format(((((totalaccesologuin * ponderacion_plataforma) / 100) + ((totalaccesorecurso * ponderacion_recurso) / 100) + ((totalcumplimiento * ponderacion_actividad) / 100)))))

                    if totalporcentaje >= 70:
                        colorfondo = '5bb75b'
                        totalverde += 1
                    if totalporcentaje <= 30:
                        colorfondo = 'b94a48'
                        totalrojo += 1
                    if totalporcentaje > 31 and totalporcentaje < 70:
                        colorfondo = 'faa732'
                        totalamarillo += 1
                    listaalumnos.append([alumnos.matricula.inscripcion.persona.cedula,
                                         nombres,
                                         esppl,
                                         esdiscapacidad,
                                         totalaccesologuin,
                                         totalaccesorecurso,
                                         totalcumplimiento,
                                         totalporcentaje,
                                         alumnos.matricula.inscripcion.persona.email,
                                         alumnos.matricula.inscripcion.persona.telefono,
                                         alumnos.matricula.inscripcion.persona.canton,
                                         colorfondo,
                                         alumnos.matricula.inscripcion.id,
                                         alumnos.matricula])

                porcentajeverde = float("{:.2f}".format((totalverde / materiasasignadas.count()) * 100))
                porcentajerojo = float("{:.2f}".format((totalrojo / materiasasignadas.count()) * 100))
                porcentajeamarillo = float("{:.2f}".format((totalamarillo / materiasasignadas.count()) * 100))

                for integrantes in listaalumnos:
                    ppl = False
                    if integrantes[2] == 'SI':
                        ppl = True
                    discapacidad = False
                    if integrantes[3] == 'SI':
                        discapacidad = True
                    if not MatriculaSeguimientoTutor.objects.filter(seguimiento=seguimiento, matricula=integrantes[13]).exists():
                        m = MatriculaSeguimientoTutor(seguimiento=seguimiento,
                                                      matricula=integrantes[13],
                                                      ppl=ppl,
                                                      discapacidad=discapacidad,
                                                      accesoplataforma=integrantes[4],
                                                      accesorecurso=integrantes[5],
                                                      cumplimientoactividades=integrantes[6],
                                                      promediovariables=integrantes[7],
                                                      color=integrantes[11])
                        m.save(request)
                    else:
                        m = MatriculaSeguimientoTutor.objects.get(seguimiento=seguimiento, matricula=integrantes[13])
                        m.ppl = ppl
                        m.discapacidad = discapacidad
                        m.accesoplataforma = integrantes[4]
                        m.accesorecurso = integrantes[5]
                        m.cumplimientoactividades = integrantes[6]
                        m.promediovariables = integrantes[7]
                        m.color = integrantes[11]
                        m.save(request)

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al calcular seguimiento los datos."})

        elif action == 'calcularseguimientosoporte':
            try:
                seguimiento = SeguimientoTutorSoporte.objects.get(pk=request.POST['id'])
                idmateria = seguimiento.materia.id
                ponderacion_plataforma = PonderacionSeguimiento.objects.get(periodo=periodo,tiposeguimiento=1).porcentaje
                ponderacion_recurso = PonderacionSeguimiento.objects.get(periodo=periodo, tiposeguimiento=2).porcentaje
                ponderacion_actividad = PonderacionSeguimiento.objects.get(periodo=periodo,tiposeguimiento=3).porcentaje
                idmateriaasignada = SoporteAcademicoTutor.objects.values_list('materiaasignada__id', flat=True).filter(status=True, periodo=periodo, tutor=profesor,materiaasignada__materia__id=int(idmateria)).distinct()
                listaalumnostotal = []
                for materia in Materia.objects.filter(id=idmateria).distinct():
                    materiasasignadas = materia.materiaasignada_set.filter(pk__in=idmateriaasignada,matricula__estado_matricula__in=[2,3]).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                    hoy = datetime.now().date()
                    if seguimiento:
                        finic = seguimiento.fechainicio
                        ffinc = seguimiento.fechafin

                    lista = []
                    listaalumnos = []
                    if materia.tareas_asignatura_moodle(finic, ffinc):
                        listaidtareas = []
                        for listatarea in materia.tareas_asignatura_moodle(finic, ffinc):
                            listaidtareas.append(listatarea[0])
                        lista.append(listaidtareas)
                    else:
                        lista.append(0)
                    if materia.foros_asignatura_moodledos(finic, ffinc):
                        listaidforum = []
                        for listaforo in materia.foros_asignatura_moodledos(finic, ffinc):
                            listaidforum.append(listaforo[0])
                        lista.append(listaidforum)
                    else:
                        lista.append(0)
                    if materia.test_asignatura_moodle(finic, ffinc):
                        listaidtest = []
                        for listatest in materia.test_asignatura_moodle(finic, ffinc):
                            listaidtest.append(listatest)
                        lista.append(listaidtest)
                    else:
                        lista.append(0)
                    diapositivas = DiapositivaSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia,silabosemanal__fechafinciosemana__range=(finic, ffinc),silabosemanal__silabo__status=True,iddiapositivamoodle__gt=0)
                    if diapositivas:
                        listaidpresentacion = []
                        for listadias in diapositivas:
                            listaidpresentacion.append(listadias.iddiapositivamoodle)
                        lista.append(listaidpresentacion)
                    else:
                        lista.append(0)
                    fechacalcula = datetime.strptime('2020-07-24', '%Y-%m-%d').date()
                    if finic > fechacalcula:
                        guiasestudiantes = GuiaEstudianteSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia,silabosemanal__fechafinciosemana__range=(finic, ffinc), silabosemanal__silabo__status=True,idguiaestudiantemoodle__gt=0)
                        if guiasestudiantes:
                            listaidguiaestudiante = []
                            for listaguiasestu in guiasestudiantes:
                                listaidguiaestudiante.append(listaguiasestu.idguiaestudiantemoodle)
                            lista.append(listaidguiaestudiante)
                        else:
                            lista.append(0)
                        guiasdocentes = GuiaDocenteSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia,silabosemanal__fechafinciosemana__range=(finic, ffinc),silabosemanal__silabo__status=True,idguiadocentemoodle__gt=0)
                        if guiasdocentes:
                            listaidguiadocente = []
                            for listaguiasdoce in guiasdocentes:
                                listaidguiadocente.append(listaguiasdoce.idguiadocentemoodle)
                            lista.append(listaidguiadocente)
                        else:
                            lista.append(0)
                        compendios = CompendioSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia,silabosemanal__fechafinciosemana__range=(finic, ffinc),silabosemanal__silabo__status=True,idmcompendiomoodle__gt=0)
                        if compendios:
                            listaidcompendio = []
                            for listacompendios in compendios:
                                listaidcompendio.append(listacompendios.idmcompendiomoodle)
                            lista.append(listaidcompendio)
                        else:
                            lista.append(0)
                    else:
                        lista.append(0)
                        lista.append(0)
                        lista.append(0)
                    totalverde = 0
                    totalamarillo = 0
                    totalrojo = 0
                    for alumnos in materiasasignadas:
                        nombres = alumnos.matricula.inscripcion.persona.apellido1 + ' ' + alumnos.matricula.inscripcion.persona.apellido2 + ' ' + alumnos.matricula.inscripcion.persona.nombres
                        esppl = 'NO'
                        esdiscapacidad = 'NO'
                        if alumnos.matricula.inscripcion.persona.ppl:
                            esppl = 'SI'
                        if alumnos.matricula.inscripcion.persona.mi_perfil().tienediscapacidad:
                            esdiscapacidad = 'SI'
                        totalaccesologuin = float("{:.2f}".format(alumnos.matricula.inscripcion.persona.total_loguinusermoodle(finic, ffinc)))
                        totalaccesorecurso = float("{:.2f}".format(alumnos.matricula.inscripcion.persona.total_accesorecursomoodle(finic, ffinc,materia.idcursomoodle,lista)))
                        totalcumplimiento = float("{:.2f}".format(alumnos.matricula.inscripcion.persona.total_cumplimientomoodle(finic, ffinc,materia.idcursomoodle,lista)))
                        totalporcentaje = float("{:.2f}".format(((((totalaccesologuin * ponderacion_plataforma) / 100) + ((totalaccesorecurso * ponderacion_recurso) / 100) + ((totalcumplimiento * ponderacion_actividad) / 100)))))
                        if totalporcentaje >= 70:
                            colorfondo = '5bb75b'
                            totalverde += 1
                        if totalporcentaje <= 30:
                            colorfondo = 'b94a48'
                            totalrojo += 1
                        if totalporcentaje > 31 and totalporcentaje < 70:
                            colorfondo = 'faa732'
                            totalamarillo += 1
                        listaalumnos.append([alumnos.matricula.inscripcion.persona.cedula,
                                             nombres,
                                             esppl,
                                             esdiscapacidad,
                                             totalaccesologuin,
                                             totalaccesorecurso,
                                             totalcumplimiento,
                                             totalporcentaje,
                                             alumnos.matricula.inscripcion.persona.email,
                                             alumnos.matricula.inscripcion.persona.telefono,
                                             alumnos.matricula.inscripcion.persona.canton,
                                             colorfondo,
                                             alumnos.matricula.inscripcion.id,
                                             alumnos.matricula,
                                             materia])

                        listaalumnostotal.append([alumnos.matricula.inscripcion.persona.cedula,
                                                  nombres,
                                                  esppl,
                                                  esdiscapacidad,
                                                  totalaccesologuin,
                                                  totalaccesorecurso,
                                                  totalcumplimiento,
                                                  totalporcentaje,
                                                  alumnos.matricula.inscripcion.persona.email,
                                                  alumnos.matricula.inscripcion.persona.telefono,
                                                  alumnos.matricula.inscripcion.persona.canton,
                                                  colorfondo,
                                                  alumnos.matricula.inscripcion.id,
                                                  alumnos.matricula,
                                                  materia])

                    porcentajeverde = float("{:.2f}".format((totalverde / materiasasignadas.count()) * 100))
                    porcentajerojo = float("{:.2f}".format((totalrojo / materiasasignadas.count()) * 100))
                    porcentajeamarillo = float("{:.2f}".format((totalamarillo / materiasasignadas.count()) * 100))
                    for integrantes in listaalumnos:
                        ppl = False
                        if integrantes[2] == 'SI':
                            ppl = True
                        discapacidad = False
                        if integrantes[3] == 'SI':
                            discapacidad = True
                        if not MatriculaSeguimientoTutorSoporte.objects.filter(seguimiento=seguimiento,matricula=integrantes[13]).exists():
                            m = MatriculaSeguimientoTutorSoporte(seguimiento=seguimiento,
                                                                 matricula=integrantes[13],
                                                                 ppl=ppl,
                                                                 discapacidad=discapacidad,
                                                                 accesoplataforma=integrantes[4],
                                                                 accesorecurso=integrantes[5],
                                                                 cumplimientoactividades=integrantes[6],
                                                                 promediovariables=integrantes[7],
                                                                 color=integrantes[11])
                            m.save(request)
                        else:
                            m = MatriculaSeguimientoTutorSoporte.objects.get(seguimiento=seguimiento, matricula=integrantes[13])
                            m.ppl = ppl
                            m.discapacidad = discapacidad
                            m.accesoplataforma = integrantes[4]
                            m.accesorecurso = integrantes[5]
                            m.cumplimientoactividades = integrantes[6]
                            m.promediovariables = integrantes[7]
                            m.color = integrantes[11]
                            m.save(request)

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al calcular seguimiento los datos."})

        elif action == 'eliminarseguimientosoporte':
            try:
                seguimiento = SeguimientoTutorSoporte.objects.get(pk=request.POST['id'])
                log(u'Elimino seguimiento tutor soporte: %s ' % (seguimiento), request, "del")
                seguimiento.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'verobservaciones':
            try:
                id = int(request.POST['id'])
                solicitud = SolicitudTutorSoporteMatricula.objects.get(pk=id)
                data['solicitud'] = solicitud
                data['respuestas_tutor'] = respuesta = solicitud.respuestasolicitudtutorsoportematricula_set.filter(status=True).order_by('id')
                data['observaciones_tutor'] = solicitud.observacionsolicitudtutorsoportematricula_set.filter(status=True).order_by('-id')
                data['atendido'] = ''
                data['respuestas_estudiante'] = ''
                if respuesta:
                    data['atendido'] = respuesta[0].atendida
                    data['respuestas_estudiante'] = respuesta[0].respuesta
                template = get_template("pro_tutoria/verobservaciones.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        elif action == 'informe_seguimiento_virtual':
            mensaje = "Problemas al generar el informe"
            try:
                materias = []
                listacarreras = []
                lista1 = ""
                coord = 0
                suma = 0
                coordinacion = None
                profesormateria = None
                profesormateriaparacoordinacion = None
                tutor = Profesor.objects.get(pk=int(encrypt(request.POST['idprofe'])))

                hoy = datetime.now().date()
                finio = request.POST['fini']
                ffino = request.POST['ffin']
                finic = convertir_fecha(finio)
                ffinc = convertir_fecha(ffino)
                profesormateriaparacoordinacion=profesormateria = ProfesorMateria.objects.filter(profesor=profesor, tipoprofesor_id=8,materia__nivel__modalidad_id=3,materia__nivel__periodo=periodo, activo=True).exclude(materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by('desde','materia__asignatura__nombre')
                if profesormateria:
                    suma = profesormateria.aggregate(total=Sum('hora'))['total']
                if profesormateriaparacoordinacion:
                    lista = []
                    for x in profesormateriaparacoordinacion:
                        materias.append(x.materia)
                        if x.materia.carrera():
                            carrera = x.materia.carrera()
                            if not carrera in listacarreras:
                                listacarreras.append(carrera)
                            lista.append(carrera)
                    cuenta1 = collections.Counter(lista).most_common(1)
                    carrera = cuenta1[0][0]
                    coordinacion = carrera.coordinacionvalida
                    matriculados = MateriaAsignada.objects.filter(materiaasignadaretiro__isnull=True,matricula__estado_matricula__in=[2,3],materia__id__in=profesormateriaparacoordinacion.values_list('materia__id', flat=True)).distinct()
                    # for x in matriculados:
                    #     if x.id != matriculados.order_by('-id')[0].id:
                    #         if x.matricula.inscripcion.persona.idusermoodle:
                    #             lista1 += str(x.matricula.inscripcion.persona.idusermoodle) + ","
                    #     else:
                    #         lista1 += str(x.matricula.inscripcion.persona.idusermoodle)
                distributivo = ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=tutor, status=True)[0] if ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=tutor,status=True).exists() else None
                # carreramateriasprofesor = Materia.objects.filter(status=True,materiaasignada__soporteacademicotutor__tutor=profesor,materiaasignada__status=True,materiaasignada__soporteacademicotutor__periodo=periodo,materiaasignada__soporteacademicotutor__status=True).distinct().order_by('asignaturamalla').distinct()
                carreramateriasprofesor = Carrera.objects.filter(status=True,malla__asignaturamalla__materia__materiaasignada__soporteacademicotutor__tutor=profesor,malla__asignaturamalla__materia__materiaasignada__status=True,malla__asignaturamalla__materia__materiaasignada__soporteacademicotutor__periodo=periodo,malla__asignaturamalla__materia__materiaasignada__soporteacademicotutor__status=True).distinct().order_by('id').distinct()
                numero_solicitudes_devuelto = SolicitudTutorSoporteMatricula.objects.filter(fecha_creacion__range=(finic,ffinc), status=True,matricula__estado_matricula__in=[2,3],matricula__materiaasignada__soporteacademicotutor__periodo=periodo,matricula__materiaasignada__soporteacademicotutor__tutor=profesor,estado=4).distinct().count()
                numero_solicitudes_tramite = SolicitudTutorSoporteMatricula.objects.filter(fecha_creacion__range=(finic,ffinc), status=True,matricula__estado_matricula__in=[2,3],matricula__materiaasignada__soporteacademicotutor__periodo=periodo,matricula__materiaasignada__soporteacademicotutor__tutor=profesor,estado=2).distinct().count()
                numero_solicitudes_cerrado = SolicitudTutorSoporteMatricula.objects.filter(fecha_creacion__range=(finic,ffinc), status=True,matricula__estado_matricula__in=[2,3],matricula__materiaasignada__soporteacademicotutor__periodo=periodo,matricula__materiaasignada__soporteacademicotutor__tutor=profesor,estado=3).distinct().count()
                numero_solicitudes_solicitado = SolicitudTutorSoporteMatricula.objects.filter(fecha_creacion__range=(finic,ffinc), status=True,matricula__estado_matricula__in=[2,3],matricula__materiaasignada__soporteacademicotutor__periodo=periodo,matricula__materiaasignada__soporteacademicotutor__tutor=profesor,estado=1).distinct().count()
                if periodo.versionreporte == 2:
                    return conviert_html_to_pdf('pro_tutoria/informe_seguimiento_virtual.html',{'pagesize': 'A4',
                                                                                                'data': {'profesor': tutor,
                                                                                                         'periodo': periodo,
                                                                                                         'fechaactual': hoy,
                                                                                                         'fini': finic,
                                                                                                         'ffin': ffinc,
                                                                                                         'inicio': finio,
                                                                                                         'fin': ffino,
                                                                                                         'coordinacion': coordinacion,
                                                                                                         'distributivo': distributivo,
                                                                                                         'materias': materias,
                                                                                                         'materias_soporte': carreramateriasprofesor,
                                                                                                         'numero_solicitudes_devuelto': numero_solicitudes_devuelto,
                                                                                                         'numero_solicitudes_tramite': numero_solicitudes_tramite,
                                                                                                         'numero_solicitudes_cerrado': numero_solicitudes_cerrado,
                                                                                                         'numero_solicitudes_solicitado': numero_solicitudes_solicitado
                                                                                                         }
                                                                                                })
                if periodo.versionreporte == 3:
                    return conviert_html_to_pdf('pro_tutoria/informe_seguimiento_virtualv3.html', {'pagesize': 'A4',
                                                                                                   'data': {'profesor': tutor,
                                                                                                            'periodo': periodo,
                                                                                                            'fechaactual': hoy,
                                                                                                            'fini': finic,
                                                                                                            'ffin': ffinc,
                                                                                                            'inicio': finio,
                                                                                                            'fin': ffino,
                                                                                                            'coordinacion': coordinacion,
                                                                                                            'distributivo': distributivo,
                                                                                                            'materias': materias,
                                                                                                            'materias_soporte': carreramateriasprofesor,
                                                                                                            'numero_solicitudes_devuelto': numero_solicitudes_devuelto,
                                                                                                            'numero_solicitudes_tramite': numero_solicitudes_tramite,
                                                                                                            'numero_solicitudes_cerrado': numero_solicitudes_cerrado,
                                                                                                            'numero_solicitudes_solicitado': numero_solicitudes_solicitado
                                                                                                            }
                                                                                                   })
            except Exception as ex:
                return HttpResponseRedirect("/pro_tutoria?info=%s" % mensaje)

        elif action == 'respondersolicitudmimateria':
            try:
                form = SolicitudTutorRespuestaForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]

                    if arch.sizee > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if exte.lower() == 'pdf' or exte.lower() == 'jpg' or exte.lower() == 'jpeg':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})

                solicitud = SolicitudTutorSoporteMateria.objects.get(pk=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    archivo = None
                    if 'archivo' in request.FILES:
                        archivo = request.FILES['archivo']
                        archivo._name = generar_nombre("respondersolicitudmimateria", archivo._name)

                    respuesta = RespuestaSolicitudTutorSoporteMateria(solicitud=solicitud,
                                                                      descripcion=form.cleaned_data['respuesta'],
                                                                      archivo=archivo)
                    respuesta.save(request)
                    solicitud.estado = 3
                    solicitud.fecharespuesta = datetime.now().date()
                    solicitud.save(request)
                    log(u'Ingreso respuesta solicitud de mi materia: %s' % respuesta, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'observacionsolicitudmimateria':
            try:
                form = SolicitudTutorObservacionForm(request.POST)
                solicitud = SolicitudTutorSoporteMateria.objects.get(pk=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    observacion = ObservacionSolicitudTutorSoporteMateria(solicitud=solicitud,
                                                                          observacion=form.cleaned_data['observacion'])
                    observacion.save(request)
                    log(u'Ingreso observacion solicitud de mi materia: %s' % observacion, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        elif action == 'verobservacionesmimateria':
            try:
                data['solicitud'] = solicitud = SolicitudTutorSoporteMateria.objects.get(pk=int(request.POST['id']))
                data['respuestas_tutor'] = respuesta = solicitud.respuestasolicitudtutorsoportemateria_set.filter(status=True).order_by('id')
                data['observaciones_tutor'] = solicitud.observacionsolicitudtutorsoportemateria_set.filter(status=True).order_by('-id')
                data['atendido'] = ''
                data['respuestas_estudiante'] = respuestas = []
                if respuesta:
                    for r in respuesta:
                        item = {'descripcion': r.descripcion, 'atendido': r.atendida, 'respuesta_estudiante': r.respuesta, 'estado':r.solicitud.estado}
                        respuestas.append(item)
                    # data['respuestas'] = respuestas
                    # data['atendido'] = respuesta[0].atendida
                    # data['respuestas_estudiante'] = respuesta[0].respuesta
                template = get_template("pro_tutoria/verobservacionesmimateria.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        if action == 'ingresarseguimientoposgrado':
            try:
                ponderacion_plataforma = 33
                ponderacion_recurso = 33
                ponderacion_actividad = 34
                data['title'] = u'Seguimiento'
                materia = Materia.objects.get(pk=int(encrypt(request.POST['id'])))
                materiasasignadas = materia.materiaasignada_set.filter(matricula__estado_matricula__in=[2,3]).order_by(
                    'matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                hoy = datetime.now().date()
                seguimiento = materia.seguimientotutor_set.filter(status=True).order_by('-fechainicio')
                finio = request.POST['fini']
                ffino = request.POST['ffin']
                finic = convertir_fecha_invertida(finio)
                ffinc = convertir_fecha_invertida(ffino)
                lista = []
                listaalumnos = []
                if materia.tareas_asignatura_moodle(finic, ffinc):
                    listaidtareas = []
                    for listatarea in materia.tareas_asignatura_moodle(finic, ffinc):
                        listaidtareas.append(listatarea[0])
                    lista.append(listaidtareas)
                else:
                    lista.append(0)
                if materia.foros_asignatura_moodledos(finic, ffinc):
                    listaidforum = []
                    for listaforo in materia.foros_asignatura_moodledos(finic, ffinc):
                        listaidforum.append(listaforo[0])
                    lista.append(listaidforum)
                else:
                    lista.append(0)
                if materia.test_asignatura_moodle(finic, ffinc):
                    listaidtest = []
                    for listatest in materia.test_asignatura_moodle(finic, ffinc):
                        listaidtest.append(listatest)
                    lista.append(listaidtest)
                else:
                    lista.append(0)
                diapositivas = DiapositivaSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia,
                                                                       silabosemanal__fechafinciosemana__range=(
                                                                       finic, ffinc),
                                                                       silabosemanal__silabo__status=True,
                                                                       iddiapositivamoodle__gt=0)
                if diapositivas:
                    listaidpresentacion = []
                    for listadias in diapositivas:
                        listaidpresentacion.append(listadias.iddiapositivamoodle)
                    lista.append(listaidpresentacion)
                else:
                    lista.append(0)
                fechacalcula = datetime.strptime('2020-07-24', '%Y-%m-%d').date()
                if finic > fechacalcula:
                    guiasestudiantes = GuiaEstudianteSilaboSemanal.objects.filter(
                        silabosemanal__silabo__materia=materia, silabosemanal__fechafinciosemana__range=(finic, ffinc),
                        silabosemanal__silabo__status=True, idguiaestudiantemoodle__gt=0)
                    if guiasestudiantes:
                        listaidguiaestudiante = []
                        for listaguiasestu in guiasestudiantes:
                            listaidguiaestudiante.append(listaguiasestu.idguiaestudiantemoodle)
                        lista.append(listaidguiaestudiante)
                    else:
                        lista.append(0)
                    guiasdocentes = GuiaDocenteSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia,
                                                                            silabosemanal__fechafinciosemana__range=(
                                                                            finic, ffinc),
                                                                            silabosemanal__silabo__status=True,
                                                                            idguiadocentemoodle__gt=0)
                    if guiasdocentes:
                        listaidguiadocente = []
                        for listaguiasdoce in guiasdocentes:
                            listaidguiadocente.append(listaguiasdoce.idguiadocentemoodle)
                        lista.append(listaidguiadocente)
                    else:
                        lista.append(0)
                    compendios = CompendioSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia,
                                                                       silabosemanal__fechafinciosemana__range=(
                                                                       finic, ffinc),
                                                                       silabosemanal__silabo__status=True,
                                                                       idmcompendiomoodle__gt=0)
                    if compendios:
                        listaidcompendio = []
                        for listacompendios in compendios:
                            listaidcompendio.append(listacompendios.idmcompendiomoodle)
                        lista.append(listaidcompendio)
                    else:
                        lista.append(0)
                else:
                    lista.append(0)
                    lista.append(0)
                    lista.append(0)
                totalverde = 0
                totalamarillo = 0
                totalrojo = 0
                for alumnos in materiasasignadas:
                    nombres = alumnos.matricula.inscripcion.persona.apellido1 + ' ' + alumnos.matricula.inscripcion.persona.apellido2 + ' ' + alumnos.matricula.inscripcion.persona.nombres
                    esppl = 'NO'
                    esdiscapacidad = 'NO'
                    if alumnos.matricula.inscripcion.persona.ppl:
                        esppl = 'SI'
                    if alumnos.matricula.inscripcion.persona.mi_perfil().tienediscapacidad:
                        esdiscapacidad = 'SI'
                    totalaccesologuin = float("{:.2f}".format(
                        alumnos.matricula.inscripcion.persona.total_loguinusermoodleposgrado(finic, ffinc)))
                    totalaccesorecurso = float("{:.2f}".format(
                        alumnos.matricula.inscripcion.persona.total_accesorecursomoodleposgrado(finic, ffinc,
                                                                                                materia.idcursomoodle,
                                                                                                lista)))
                    totalcumplimiento = float("{:.2f}".format(
                        alumnos.matricula.inscripcion.persona.total_cumplimientomoodleposgrado(finic, ffinc,
                                                                                               materia.idcursomoodle,
                                                                                               lista)))
                    totalporcentaje = float("{:.2f}".format(((((totalaccesologuin * ponderacion_plataforma) / 100) + (
                                (totalaccesorecurso * ponderacion_recurso) / 100) + ((
                                                                                                 totalcumplimiento * ponderacion_actividad) / 100)))))

                    if totalporcentaje >= 70:
                        colorfondo = '5bb75b'
                        totalverde += 1
                    if totalporcentaje <= 30:
                        colorfondo = 'b94a48'
                        totalrojo += 1
                    if totalporcentaje > 31 and totalporcentaje < 70:
                        colorfondo = 'faa732'
                        totalamarillo += 1
                    listaalumnos.append([alumnos.matricula.inscripcion.persona.cedula,
                                         nombres,
                                         esppl,
                                         esdiscapacidad,
                                         totalaccesologuin,
                                         totalaccesorecurso,
                                         totalcumplimiento,
                                         totalporcentaje,
                                         alumnos.matricula.inscripcion.persona.email,
                                         alumnos.matricula.inscripcion.persona.telefono,
                                         alumnos.matricula.inscripcion.persona.canton,
                                         colorfondo,
                                         alumnos.matricula.inscripcion.id,
                                         alumnos.matricula])

                porcentajeverde = float("{:.2f}".format((totalverde / materiasasignadas.count()) * 100))
                porcentajerojo = float("{:.2f}".format((totalrojo / materiasasignadas.count()) * 100))
                porcentajeamarillo = float("{:.2f}".format((totalamarillo / materiasasignadas.count()) * 100))
                data['materia'] = materia
                data['periodo'] = periodo
                data['materiasasignadas'] = materiasasignadas
                data['fechaactual'] = hoy
                data['fini'] = finic
                data['ffin'] = ffinc
                data['lista'] = lista
                data['listaalumnos'] = listaalumnos
                data['totalverde'] = totalverde
                data['totalrojo'] = totalrojo
                data['totalamarillo'] = totalamarillo
                data['porcentajeverde'] = porcentajeverde
                data['porcentajerojo'] = porcentajerojo
                data['porcentajeamarillo'] = porcentajeamarillo

                s = SeguimientoTutor.objects.filter(materia=materia, tutor=profesor, fechainicio__lte=hoy,
                                                    fechafin__gte=hoy)
                if not s:
                    s = SeguimientoTutor(tutor=profesor,
                                         fechainicio=finic,
                                         fechafin=ffinc,
                                         materia=materia,
                                         periodo=periodo)
                    s.save(request)
                else:
                    s = s[0]
                data['seguimiento'] = s
                # s.matriculaseguimientotutor_set.all().delete()
                for integrantes in listaalumnos:
                    ppl = False
                    if integrantes[2] == 'SI':
                        ppl = True
                    discapacidad = False
                    if integrantes[3] == 'SI':
                        discapacidad = True
                    if not MatriculaSeguimientoTutor.objects.filter(seguimiento=s, matricula=integrantes[13]).exists():
                        m = MatriculaSeguimientoTutor(seguimiento=s,
                                                      matricula=integrantes[13],
                                                      ppl=ppl,
                                                      discapacidad=discapacidad,
                                                      accesoplataforma=integrantes[4],
                                                      accesorecurso=integrantes[5],
                                                      cumplimientoactividades=integrantes[6],
                                                      promediovariables=integrantes[7],
                                                      color=integrantes[11])
                        m.save(request)
                    else:
                        m = MatriculaSeguimientoTutor.objects.get(seguimiento=s, matricula=integrantes[13])
                        m.ppl = ppl
                        m.discapacidad = discapacidad
                        m.accesoplataforma = integrantes[4]
                        m.accesorecurso = integrantes[5]
                        m.cumplimientoactividades = integrantes[6]
                        m.promediovariables = integrantes[7]
                        m.color = integrantes[11]
                        m.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                pass

        if action == 'marcarretirado':
            materiaasignada = MateriaAsignada.objects.get(id=int(encrypt(request.POST['id'])))
            materiaasignada.retiromanual = True
            materiaasignada.fecharetiromanual = datetime.now().date()
            materiaasignada.save()
            log(u'Marco un alumno como retirado : %s' % materiaasignada, request, "add")
            return JsonResponse({"result": "ok"})

        if action == 'desmarcarretirado':
            materiaasignada = MateriaAsignada.objects.get(id=int(encrypt(request.POST['id'])))
            materiaasignada.retiromanual = False
            materiaasignada.fecharetiromanual = None
            materiaasignada.save(request)
            log(u'Desmarcó un alumno como retirado : %s' % materiaasignada, request, "add")
            return JsonResponse({"result": "ok"})

        if action == 'subirarchivo':
            try:
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    exte = exte.lower()

                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte == 'pdf' and not exte == 'jpg' and not exte == 'jpeg' and not exte == 'png':
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})

                solicitud = SolicitudTutorSoporteMateria.objects.get(pk=int(encrypt(request.POST['id'])))

                archivo = None
                if 'archivo' in request.FILES:
                    archivo = request.FILES['archivo']
                    archivo._name = generar_nombre("respondersolicitudmimateria", archivo._name)

                respuesta = RespuestaSolicitudTutorSoporteMateria(solicitud=solicitud,
                                                                  descripcion=request.POST['respuesta'], archivo=archivo)
                respuesta.save(request)
                solicitud.estado = 2
                solicitud.fecharespuesta = datetime.now().date()
                solicitud.save(request)
                log(u'Ingreso respuesta solicitud de mi materia: %s' % respuesta, request, "edit")

                # Notificacion para el alumno
                notificacion = Notificacion(
                    titulo='Respuesta del docente  %s' % respuesta.solicitud.profesor.persona.nombre_completo_minus(),
                    cuerpo='Tiene una respuesta de la asignatura %s' % respuesta.solicitud.materiaasignada.materia,
                    destinatario=respuesta.solicitud.materiaasignada.matricula.inscripcion.persona,
                    url="/alu_solicitudtutor?action=gestionrespuestas&id={}".format(solicitud.pk),
                    content_type=None,
                    object_id=solicitud.pk,
                    prioridad=2,
                    fecha_hora_visible=datetime.now() + timedelta(days=1),
                    app_label='sga',
                )
                notificacion.save(request)
                return JsonResponse({"result": "ok", 'mensaje': 'Respuesta enviada Correctamente'})
            except Exception as e:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", 'mensaje':'Error en la transaccion '+str(e)})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'ingresarseguimiento':
                try:
                    if PonderacionSeguimiento.objects.filter(status=True, tiposeguimiento=1).exists():
                        ponderacion_plataforma = PonderacionSeguimiento.objects.filter(status=True, tiposeguimiento=1).order_by('-id').first().porcentaje
                    if PonderacionSeguimiento.objects.filter(status=True, tiposeguimiento=2).exists():
                        ponderacion_recurso = PonderacionSeguimiento.objects.filter(status=True, tiposeguimiento=2).order_by('-id').first().porcentaje
                    if PonderacionSeguimiento.objects.filter(status=True, tiposeguimiento=3).exists():
                        ponderacion_actividad = PonderacionSeguimiento.objects.filter(status=True, tiposeguimiento=3).order_by('-id').first().porcentaje
                    data['title'] = u'Seguimiento'
                    materia = Materia.objects.get(pk=int(encrypt(request.GET['id'])))
                    # materiasasignadas = materia.materiaasignada_set.filter(matricula__estado_matricula__in=[2,3]).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                    materiasasignadas = materia.materiaasignada_set.filter(matricula__retiradomatricula=False, retiramateria=False, status=True, matricula__status=True).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                    hoy = datetime.now().date()
                    seguimiento = materia.seguimientotutor_set.filter(status=True).order_by('-fechainicio')
                    if seguimiento:
                        seguimientoaux = materia.seguimientotutor_set.filter(status=True,fechainicio__lte=hoy,fechafin__gte=hoy).order_by('-fechainicio')
                        if seguimientoaux:
                            finic = seguimientoaux[0].fechainicio
                            ffinc = seguimientoaux[0].fechafin
                        else:
                            finic = seguimiento[0].fechafin + timedelta(days=1)
                            ffinc = hoy
                    else:
                        finic = materia.inicio
                        ffinc = hoy

                    lista = []
                    listaalumnos = []
                    if materia.tareas_asignatura_moodle(finic,ffinc):
                        listaidtareas = []
                        for listatarea in materia.tareas_asignatura_moodle(finic, ffinc):
                            listaidtareas.append(listatarea[0])
                        lista.append(listaidtareas)
                    else:
                        lista.append(0)
                    if materia.foros_asignatura_moodledos(finic,ffinc):
                        listaidforum = []
                        for listaforo in materia.foros_asignatura_moodledos(finic,ffinc):
                            listaidforum.append(listaforo[0])
                        lista.append(listaidforum)
                    else:
                        lista.append(0)
                    if materia.test_asignatura_moodle(finic,ffinc):
                        listaidtest = []
                        for listatest in materia.test_asignatura_moodle(finic,ffinc):
                            listaidtest.append(listatest)
                        lista.append(listaidtest)
                    else:
                        lista.append(0)
                    diapositivas = DiapositivaSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia, silabosemanal__fechafinciosemana__range=(finic,ffinc), silabosemanal__silabo__status=True, iddiapositivamoodle__gt=0)
                    if diapositivas:
                        listaidpresentacion = []
                        for listadias in diapositivas:
                            listaidpresentacion.append(listadias.iddiapositivamoodle)
                        lista.append(listaidpresentacion)
                    else:
                        lista.append(0)
                    fechacalcula = datetime.strptime('2020-07-24', '%Y-%m-%d').date()
                    if finic > fechacalcula:
                        guiasestudiantes = GuiaEstudianteSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia, silabosemanal__fechafinciosemana__range=(finic, ffinc), silabosemanal__silabo__status=True, idguiaestudiantemoodle__gt=0)
                        if guiasestudiantes:
                            listaidguiaestudiante = []
                            for listaguiasestu in guiasestudiantes:
                                listaidguiaestudiante.append(listaguiasestu.idguiaestudiantemoodle)
                            lista.append(listaidguiaestudiante)
                        else:
                            lista.append(0)
                        guiasdocentes = GuiaDocenteSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia, silabosemanal__fechafinciosemana__range=(finic, ffinc), silabosemanal__silabo__status=True, idguiadocentemoodle__gt=0)
                        if guiasdocentes:
                            listaidguiadocente = []
                            for listaguiasdoce in guiasdocentes:
                                listaidguiadocente.append(listaguiasdoce.idguiadocentemoodle)
                            lista.append(listaidguiadocente)
                        else:
                            lista.append(0)
                        compendios = CompendioSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia, silabosemanal__fechafinciosemana__range=(finic, ffinc), silabosemanal__silabo__status=True, idmcompendiomoodle__gt=0)
                        if compendios:
                            listaidcompendio = []
                            for listacompendios in compendios:
                                listaidcompendio.append(listacompendios.idmcompendiomoodle)
                            lista.append(listaidcompendio)
                        else:
                            lista.append(0)
                    else:
                        lista.append(0)
                        lista.append(0)
                        lista.append(0)
                    totalverde = 0
                    totalamarillo = 0
                    totalrojo = 0
                    for alumnos in materiasasignadas:
                        nombres = alumnos.matricula.inscripcion.persona.apellido1 + ' ' + alumnos.matricula.inscripcion.persona.apellido2 + ' ' +alumnos.matricula.inscripcion.persona.nombres
                        esppl = 'NO'
                        esdiscapacidad = 'NO'
                        if alumnos.matricula.inscripcion.persona.ppl:
                            esppl = 'SI'
                        if alumnos.matricula.inscripcion.persona.mi_perfil().tienediscapacidad:
                            esdiscapacidad = 'SI'
                        if alumnos.matricula.nivel.periodo_id>=113:
                            totalaccesologuin = float("{:.2f}".format(
                                alumnos.matricula.inscripcion.persona.total_loguinusermoodle_sin_findesemana(finic,
                                                                                                             ffinc, alumnos.materia)))
                        else:
                            totalaccesologuin = float("{:.2f}".format(alumnos.matricula.inscripcion.persona.total_loguinusermoodle(finic, ffinc, alumnos.materia)))
                        totalaccesorecurso = float("{:.2f}".format(alumnos.matricula.inscripcion.persona.total_accesorecursomoodle(finic, ffinc,materia.idcursomoodle,lista)))
                        if totalaccesologuin == 0:
                            totalcumplimiento = 0
                        else:
                            totalcumplimiento = float("{:.2f}".format(alumnos.matricula.inscripcion.persona.total_cumplimientomoodle(finic, ffinc,materia.idcursomoodle,lista)))

                        totalporcentaje = float("{:.2f}".format(((((totalaccesologuin*ponderacion_plataforma)/100) + ((totalaccesorecurso*ponderacion_recurso)/100) + ((totalcumplimiento*ponderacion_actividad)/100)))))


                        if totalporcentaje >= 70:
                            colorfondo = '5bb75b'
                            totalverde += 1
                        if totalporcentaje <= 30:
                            colorfondo = 'b94a48'
                            totalrojo += 1
                        if totalporcentaje >= 31 and totalporcentaje < 70:
                            colorfondo = 'faa732'
                            totalamarillo += 1
                        if totalporcentaje >= 100:
                            totalporcentaje=100.0
                        listaalumnos.append([alumnos.matricula.inscripcion.persona.cedula,
                                             nombres,
                                             esppl,
                                             esdiscapacidad,
                                             totalaccesologuin,
                                             totalaccesorecurso,
                                             totalcumplimiento,
                                             totalporcentaje,
                                             alumnos.matricula.inscripcion.persona.email,
                                             alumnos.matricula.inscripcion.persona.telefono,
                                             alumnos.matricula.inscripcion.persona.canton,
                                             colorfondo,
                                             alumnos.matricula.inscripcion.id,
                                             alumnos.matricula,
                                             alumnos.esta_retirado(),
                                             alumnos.id,
                                             alumnos.retiromanual])

                    porcentajeverde = float("{:.2f}".format((totalverde / materiasasignadas.count()) * 100))
                    porcentajerojo = float("{:.2f}".format((totalrojo / materiasasignadas.count()) * 100))
                    porcentajeamarillo = float("{:.2f}".format((totalamarillo / materiasasignadas.count()) * 100))
                    data['materia'] = materia
                    data['periodo'] = periodo
                    data['materiasasignadas'] = materiasasignadas
                    data['fechaactual'] = hoy
                    data['fini'] = finic
                    data['ffin'] = ffinc
                    data['lista'] = lista
                    data['listaalumnos'] = listaalumnos
                    data['totalverde'] = totalverde
                    data['totalrojo'] = totalrojo
                    data['totalamarillo'] = totalamarillo
                    data['porcentajeverde'] = porcentajeverde
                    data['porcentajerojo'] = porcentajerojo
                    data['porcentajeamarillo'] = porcentajeamarillo

                    s = SeguimientoTutor.objects.filter(materia=materia, tutor=profesor, fechainicio__lte=hoy,fechafin__gte=hoy)
                    if not s:
                        s = SeguimientoTutor(tutor=profesor,
                                             fechainicio=finic,
                                             fechafin=ffinc,
                                             materia=materia,
                                             periodo=periodo)
                        s.save(request)
                    else:
                        s = s[0]
                    data['seguimiento'] = s
                    # s.matriculaseguimientotutor_set.all().delete()
                    for integrantes in listaalumnos:
                        ppl = False
                        if integrantes[2] == 'SI':
                            ppl = True
                        discapacidad = False
                        if integrantes[3] == 'SI':
                            discapacidad = True
                        if not MatriculaSeguimientoTutor.objects.filter(seguimiento=s,matricula=integrantes[13]).exists():
                            m = MatriculaSeguimientoTutor(seguimiento=s,
                                                          matricula=integrantes[13],
                                                          ppl=ppl,
                                                          discapacidad=discapacidad,
                                                          accesoplataforma=integrantes[4],
                                                          accesorecurso=integrantes[5],
                                                          cumplimientoactividades=integrantes[6],
                                                          promediovariables=integrantes[7],
                                                          color=integrantes[11])
                            m.save(request)
                        else:
                            m = MatriculaSeguimientoTutor.objects.get(seguimiento=s,matricula=integrantes[13])
                            m.ppl = ppl
                            m.discapacidad = discapacidad
                            m.accesoplataforma = integrantes[4]
                            m.accesorecurso = integrantes[5]
                            m.cumplimientoactividades = integrantes[6]
                            m.promediovariables = integrantes[7]
                            m.color = integrantes[11]
                            m.save(request)

                    return render(request, 'pro_tutoria/ingresarseguimiento.html', data)
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    print(ex)
                    messages.error(request, f"{'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)} {ex}")

            if action == 'enviarcorreomasivo':
                try:
                    data['title'] = u'Envío Masivo de Correos'
                    materia = Materia.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    materiasasignadas = materia.materiaasignada_set.filter(matricula__estado_matricula__in=[2,3], status=True).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                    hoy = datetime.now().date()

                    listaalumnos = []

                    for alumnos in materiasasignadas:
                        nombres = alumnos.matricula.inscripcion.persona.apellido1 + ' ' + alumnos.matricula.inscripcion.persona.apellido2 + ' ' +alumnos.matricula.inscripcion.persona.nombres
                        esppl = 'NO'
                        esdiscapacidad = 'NO'
                        if alumnos.matricula.inscripcion.persona.ppl:
                            esppl = 'SI'
                        if alumnos.matricula.inscripcion.persona.mi_perfil().tienediscapacidad:
                            esdiscapacidad = 'SI'

                        listaalumnos.append([alumnos.matricula.inscripcion.persona.cedula,
                                             nombres,
                                             esppl,
                                             esdiscapacidad,
                                             alumnos.matricula.inscripcion.persona.email,
                                             alumnos.matricula.inscripcion.persona.telefono,
                                             alumnos.matricula.inscripcion.persona.canton,
                                             # colorfondo,
                                             alumnos.matricula.inscripcion.id,
                                             alumnos.matricula,
                                             alumnos.esta_retirado(),
                                             alumnos.id,
                                             alumnos.retiromanual])
                    data['materia'] = materia
                    data['periodo'] = periodo
                    data['materiasasignadas'] = materiasasignadas
                    data['fechaactual'] = hoy

                    data['listaalumnos'] = listaalumnos

                    return render(request, 'pro_tutoria/enviarcorreomasivo.html', data)
                except Exception as ex:
                    pass

            if action == 'ingresarseguimientosoporte':
                try:
                    data['title'] = u'Seguimiento'
                    # carrera = Carrera.objects.get(pk=int(encrypt(request.GET['id'])))
                    # materia = Materia.objects.get(pk=int(encrypt(request.GET['id'])))
                    # idmaterias = SoporteAcademicoTutor.objects.values_list('materiaasignada__materia__id', flat=True).filter(status=True, periodo=periodo, tutor=profesor,materiaasignada__materia__asignaturamalla__malla__carrera=carrera).distinct()
                    ponderacion_plataforma = PonderacionSeguimiento.objects.get(periodo=periodo,tiposeguimiento=1).porcentaje
                    ponderacion_recurso = PonderacionSeguimiento.objects.get(periodo=periodo,tiposeguimiento=2).porcentaje
                    ponderacion_actividad = PonderacionSeguimiento.objects.get(periodo=periodo,tiposeguimiento=3).porcentaje
                    idmateriaasignada = SoporteAcademicoTutor.objects.values_list('materiaasignada__id', flat=True).filter(status=True, periodo=periodo, tutor=profesor,materiaasignada__materia__id=int(encrypt(request.GET['id']))).distinct()
                    listaalumnostotal = []
                    for materia in Materia.objects.filter(id=int(encrypt(request.GET['id']))).distinct():
                        materiasasignadas = materia.materiaasignada_set.filter(pk__in=idmateriaasignada,matricula__estado_matricula__in=[2,3]).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                        hoy = datetime.now().date()
                        seguimiento = materia.seguimientotutorsoporte_set.filter(status=True, tutor=profesor).order_by('-fechainicio')
                        if seguimiento:
                            seguimientoaux = materia.seguimientotutorsoporte_set.filter(status=True, tutor=profesor,fechainicio__lte=hoy,fechafin__gte=hoy).order_by('-fechainicio')
                            if seguimientoaux:
                                finic = seguimientoaux[0].fechainicio
                                ffinc = seguimientoaux[0].fechafin
                            else:
                                finic = seguimiento[0].fechafin + timedelta(days=1)
                                ffinc = hoy
                        else:
                            finic = materia.inicio
                            ffinc = hoy

                        lista = []
                        listaalumnos = []
                        if materia.tareas_asignatura_moodle(finic,ffinc):
                            listaidtareas = []
                            for listatarea in materia.tareas_asignatura_moodle(finic, ffinc):
                                listaidtareas.append(listatarea[0])
                            lista.append(listaidtareas)
                        else:
                            lista.append(0)
                        if materia.foros_asignatura_moodledos(finic,ffinc):
                            listaidforum = []
                            for listaforo in materia.foros_asignatura_moodledos(finic,ffinc):
                                listaidforum.append(listaforo[0])
                            lista.append(listaidforum)
                        else:
                            lista.append(0)
                        if materia.test_asignatura_moodle(finic,ffinc):
                            listaidtest = []
                            for listatest in materia.test_asignatura_moodle(finic,ffinc):
                                listaidtest.append(listatest)
                            lista.append(listaidtest)
                        else:
                            lista.append(0)
                        diapositivas = DiapositivaSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia, silabosemanal__fechafinciosemana__range=(finic,ffinc), silabosemanal__silabo__status=True, iddiapositivamoodle__gt=0)
                        if diapositivas:
                            listaidpresentacion = []
                            for listadias in diapositivas:
                                listaidpresentacion.append(listadias.iddiapositivamoodle)
                            lista.append(listaidpresentacion)
                        else:
                            lista.append(0)
                        fechacalcula = datetime.strptime('2020-07-24', '%Y-%m-%d').date()
                        if finic > fechacalcula:
                            guiasestudiantes = GuiaEstudianteSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia, silabosemanal__fechafinciosemana__range=(finic, ffinc), silabosemanal__silabo__status=True, idguiaestudiantemoodle__gt=0)
                            if guiasestudiantes:
                                listaidguiaestudiante = []
                                for listaguiasestu in guiasestudiantes:
                                    listaidguiaestudiante.append(listaguiasestu.idguiaestudiantemoodle)
                                lista.append(listaidguiaestudiante)
                            else:
                                lista.append(0)
                            guiasdocentes = GuiaDocenteSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia, silabosemanal__fechafinciosemana__range=(finic, ffinc), silabosemanal__silabo__status=True, idguiadocentemoodle__gt=0)
                            if guiasdocentes:
                                listaidguiadocente = []
                                for listaguiasdoce in guiasdocentes:
                                    listaidguiadocente.append(listaguiasdoce.idguiadocentemoodle)
                                lista.append(listaidguiadocente)
                            else:
                                lista.append(0)
                            compendios = CompendioSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia, silabosemanal__fechafinciosemana__range=(finic, ffinc), silabosemanal__silabo__status=True, idmcompendiomoodle__gt=0)
                            if compendios:
                                listaidcompendio = []
                                for listacompendios in compendios:
                                    listaidcompendio.append(listacompendios.idmcompendiomoodle)
                                lista.append(listaidcompendio)
                            else:
                                lista.append(0)
                        else:
                            lista.append(0)
                            lista.append(0)
                            lista.append(0)
                        totalverde = 0
                        totalamarillo = 0
                        totalrojo = 0
                        for alumnos in materiasasignadas:
                            nombres = alumnos.matricula.inscripcion.persona.apellido1 + ' ' + alumnos.matricula.inscripcion.persona.apellido2 + ' ' +alumnos.matricula.inscripcion.persona.nombres
                            esppl = 'NO'
                            esdiscapacidad = 'NO'
                            if alumnos.matricula.inscripcion.persona.ppl:
                                esppl = 'SI'
                            if alumnos.matricula.inscripcion.persona.mi_perfil().tienediscapacidad:
                                esdiscapacidad = 'SI'
                            totalaccesologuin = float("{:.2f}".format(alumnos.matricula.inscripcion.persona.total_loguinusermoodle(finic, ffinc)))
                            totalaccesorecurso = float("{:.2f}".format(alumnos.matricula.inscripcion.persona.total_accesorecursomoodle(finic, ffinc,materia.idcursomoodle,lista)))
                            totalcumplimiento = float("{:.2f}".format(alumnos.matricula.inscripcion.persona.total_cumplimientomoodle(finic, ffinc,materia.idcursomoodle,lista)))
                            totalporcentaje = float("{:.2f}".format(((((totalaccesologuin * ponderacion_plataforma) / 100) + ((totalaccesorecurso * ponderacion_recurso) / 100) + ((totalcumplimiento * ponderacion_actividad) / 100)))))
                            if totalporcentaje >= 70:
                                colorfondo = '5bb75b'
                                totalverde += 1
                            if totalporcentaje <= 30:
                                colorfondo = 'b94a48'
                                totalrojo += 1
                            if totalporcentaje > 31 and totalporcentaje < 70:
                                colorfondo = 'faa732'
                                totalamarillo += 1
                            listaalumnos.append([alumnos.matricula.inscripcion.persona.cedula,
                                                 nombres,
                                                 esppl,
                                                 esdiscapacidad,
                                                 totalaccesologuin,
                                                 totalaccesorecurso,
                                                 totalcumplimiento,
                                                 totalporcentaje,
                                                 alumnos.matricula.inscripcion.persona.email,
                                                 alumnos.matricula.inscripcion.persona.telefono,
                                                 alumnos.matricula.inscripcion.persona.canton,
                                                 colorfondo,
                                                 alumnos.matricula.inscripcion.id,
                                                 alumnos.matricula,
                                                 materia])

                            listaalumnostotal.append([alumnos.matricula.inscripcion.persona.cedula,
                                                      nombres,
                                                      esppl,
                                                      esdiscapacidad,
                                                      totalaccesologuin,
                                                      totalaccesorecurso,
                                                      totalcumplimiento,
                                                      totalporcentaje,
                                                      alumnos.matricula.inscripcion.persona.email,
                                                      alumnos.matricula.inscripcion.persona.telefono,
                                                      alumnos.matricula.inscripcion.persona.canton,
                                                      colorfondo,
                                                      alumnos.matricula.inscripcion.id,
                                                      alumnos.matricula,
                                                      materia])

                        porcentajeverde = float("{:.2f}".format((totalverde / materiasasignadas.count()) * 100))
                        porcentajerojo = float("{:.2f}".format((totalrojo / materiasasignadas.count()) * 100))
                        porcentajeamarillo = float("{:.2f}".format((totalamarillo / materiasasignadas.count()) * 100))
                        data['materia'] = materia
                        # data['materia'] = materia
                        # data['periodo'] = periodo
                        # data['materiasasignadas'] = materiasasignadas
                        # data['fechaactual'] = hoy
                        # data['fini'] = finic
                        # data['ffin'] = ffinc
                        # data['lista'] = lista

                        # data['totalverde'] = totalverde
                        # data['totalrojo'] = totalrojo
                        # data['totalamarillo'] = totalamarillo
                        # data['porcentajeverde'] = porcentajeverde
                        # data['porcentajerojo'] = porcentajerojo
                        # data['porcentajeamarillo'] = porcentajeamarillo

                        s = SeguimientoTutorSoporte.objects.filter(materia=materia, tutor=profesor, fechainicio__lte=hoy,fechafin__gte=hoy)
                        if not s:
                            s = SeguimientoTutorSoporte(tutor=profesor,
                                                        fechainicio=finic,
                                                        fechafin=ffinc,
                                                        materia=materia,
                                                        periodo=periodo)
                            s.save(request)
                        else:
                            s = s[0]
                        data['seguimiento'] = s
                        # s.matriculaseguimientotutor_set.all().delete()
                        for integrantes in listaalumnos:
                            ppl = False
                            if integrantes[2] == 'SI':
                                ppl = True
                            discapacidad = False
                            if integrantes[3] == 'SI':
                                discapacidad = True
                            if not MatriculaSeguimientoTutorSoporte.objects.filter(seguimiento=s,matricula=integrantes[13]).exists():
                                m = MatriculaSeguimientoTutorSoporte(seguimiento=s,
                                                                     matricula=integrantes[13],
                                                                     ppl=ppl,
                                                                     discapacidad=discapacidad,
                                                                     accesoplataforma=integrantes[4],
                                                                     accesorecurso=integrantes[5],
                                                                     cumplimientoactividades=integrantes[6],
                                                                     promediovariables=integrantes[7],
                                                                     color=integrantes[11])
                                m.save(request)
                            else:
                                m = MatriculaSeguimientoTutorSoporte.objects.get(seguimiento=s,matricula=integrantes[13])
                                m.ppl = ppl
                                m.discapacidad = discapacidad
                                m.accesoplataforma = integrantes[4]
                                m.accesorecurso = integrantes[5]
                                m.cumplimientoactividades = integrantes[6]
                                m.promediovariables = integrantes[7]
                                m.color = integrantes[11]
                                m.save(request)
                    data['listaalumnos'] = listaalumnostotal
                    return render(request, 'pro_tutoria/ingresarseguimientosoporte.html', data)
                except Exception as ex:
                    pass

            if action == 'veralumnos':
                try:
                    data['title'] = u'Alumnos de la materia'
                    search = None
                    materia = Materia.objects.get(pk=int(encrypt(request.GET['id'])))
                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        if len(ss) == 2:
                            materiasasignadas = materia.materiaasignada_set.filter(Q(matricula__inscripcion__persona__apellido1__icontains=ss[0]) &
                                                                                   Q(matricula__inscripcion__persona__apellido2__icontains=ss[1]),matricula__estado_matricula__in=[2,3]).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                        else:
                            materiasasignadas = materia.materiaasignada_set.filter(Q(matricula__inscripcion__persona__nombres__icontains=search) |
                                                                                   Q(matricula__inscripcion__persona__apellido1__icontains=search) |
                                                                                   Q(matricula__inscripcion__persona__apellido2__icontains=search) |
                                                                                   Q(matricula__inscripcion__persona__cedula__icontains=search), matricula__estado_matricula__in=[2,3]).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                    else:
                        materiasasignadas = materia.materiaasignada_set.filter(matricula__estado_matricula__in=[2,3]).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                    data['materia'] = materia
                    numerofilas = 25
                    paging = MiPaginador(materiasasignadas, numerofilas)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                            if p == 1:
                                numerofilasguiente = numerofilas
                            else:
                                numerofilasguiente = numerofilas * (p - 1)
                        else:
                            p = paginasesion
                            if p == 1:
                                numerofilasguiente = numerofilas
                            else:
                                numerofilasguiente = numerofilas * (p - 1)
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['numerofilasguiente'] = numerofilasguiente
                    data['numeropagina'] = p
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['listaalumnos'] = page.object_list
                    data['url_vars'] = "&action={}&id={}".format(action, request.GET['id'])
                    return render(request, 'pro_tutoria/veralumnos.html', data)
                except Exception as ex:
                    pass

            if action == 'veralumnossoporte':
                try:
                    data['title'] = u'Seguimiento'
                    carrera = Carrera.objects.get(pk=int(encrypt(request.GET['id'])))
                    idmatriculados = SoporteAcademicoTutor.objects.values_list('materiaasignada__id', flat=True).filter(periodo=periodo, tutor=profesor, status=True)
                    # materiasasignadas = MateriaAsignada.objects.filter(id__in=idmatriculados, matricula__estado_matricula__in=[2,3], materia__asignaturamalla__malla__carrera=carrera).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2').distinct()
                    materiasasignadas = Matricula.objects.filter(materiaasignada__id__in=idmatriculados, estado_matricula__in=[2,3], materiaasignada__materia__asignaturamalla__malla__carrera=carrera).order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2').distinct()
                    data['listaalumnos'] = materiasasignadas
                    data['carrera'] = carrera
                    return render(request, 'pro_tutoria/veralumnossoporte.html', data)
                except Exception as ex:
                    pass

            if action == 'visualizarseguimiento':
                try:
                    data['title'] = u'Seguimientos'
                    data['materia'] = materia = Materia.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['seguimientos'] = seguimientos = materia.seguimientotutor_set.filter(status=True).order_by(
                        'fechainicio')
                    data['ultimo'] = seguimientos.count()
                    return render(request, 'pro_tutoria/visualizarseguimiento.html', data)
                except Exception as ex:
                    pass

            if action == 'visualizarseguimientomodal':
                try:
                    data['title'] = u'Resumen de seguimiento tutor'

                    data['profesor'] = profesor = Profesor.objects.get(pk=int(encrypt(request.GET['ipd'])))
                    materias = profesor.profesorparalelos(periodo).values('materia_id')
                    data['seguimientos'] = seguimientos = SeguimientoTutor.objects.filter(status=True, materia_id__in=materias).order_by('fechainicio')
                    data['ultimo'] = seguimientos.count()
                    template = get_template("pro_tutoria/modalseguimientodetalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})


            if action == 'informe_pdf_seguimiento':
                try:
                    rfecha = request.GET['rfechas'].split(' - ')
                    finicio, ffin = convertir_fecha_invertida(rfecha[0]), convertir_fecha_invertida(rfecha[1])
                    profesoresid = request.GET['profesores'].split(',')
                    profesores = Profesor.objects.filter(status=True, id__in=profesoresid)
                    periodo = periodo
                    return conviert_html_to_pdf('pro_tutoria/pdfseguimientotutor.html',
                                                {'pagesize': 'A4', 'data': {'profesores': profesores, 'hoy': datetime.now().date() ,'fini': finicio, 'ffin': ffin, 'periodo': periodo,'persona':persona}})
                except Exception as ex:
                    pass




            if action == 'visualizarseguimientotutor':
                try:
                    data['materias'] = materias = request.GET['id']
                    data['desde'] = desde = request.GET['desde']
                    data['hasta'] = hasta = request.GET['hasta']
                    data['pm'] = pm = Profesor.objects.filter(status=True, id=materias).first()
                    data['periodo'] = periodo
                    if not pm:
                        raise NameError('No existe el registro')
                    # materia.seguimientotutorsoporte_set.filter(status=True, tutor=profesor).order_by('fechainicio')
                    template = get_template("pro_tutoria/seguimientomodalreporte.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": str(ex)})
            if action == 'visualizarseguimientosoporte':
                try:
                    data['title'] = u'Seguimientos'
                    materia = Materia.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['seguimientos'] = seguimientos = materia.seguimientotutorsoporte_set.filter(status=True, tutor=profesor).order_by('fechainicio')
                    data['ultimo'] = seguimientos.count()
                    return render(request, 'pro_tutoria/visualizarseguimientosoporte.html', data)
                except Exception as ex:
                    pass
            if action == 'visualizarseguimientodetalle':
                try:
                    data['title'] = u'Seguimientos'
                    seguimiento = SeguimientoTutor.objects.get(pk=int(encrypt(request.GET['id'])))
                    ultimo = SeguimientoTutor.objects.filter(periodo=seguimiento.periodo, materia=seguimiento.materia, tutor=seguimiento.tutor).order_by('id').last()
                    data['ultimo'] = ultimo.id == int(encrypt(request.GET['id']))
                    data['seguimiento'] = seguimiento
                    lista_retirados_manual = seguimiento.materia.materiaasignada_set.values_list('matricula__inscripcion__id', flat=True).filter(Q(materia__nivel__periodo=periodo) & Q(status=True, matricula__status=True, matricula__inscripcion__status=True) & (Q(retiramateria=True) | Q(retiromanual=True)))
                    if seguimiento.materia.asignaturamalla.malla.carrera.mi_coordinacion2() == 7:
                        data['seguimientos'] = seguimiento.matriculaseguimientotutor_set.filter(status=True).exclude(matricula__inscripcion__id__in=lista_retirados_manual).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                        return render(request, 'pro_tutoria/visualizarseguimientodetalleposgrado.html', data)
                    else:
                        data['seguimientos'] = seguimiento.matriculaseguimientotutor_set.filter(status=True).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                        return render(request, 'pro_tutoria/visualizarseguimientodetalle.html', data)
                except Exception as ex:
                    pass

            if action == 'visualizarseguimientodetallesoporte':
                try:
                    data['title'] = u'Seguimientos'
                    seguimiento = SeguimientoTutorSoporte.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['seguimiento'] = seguimiento
                    data['seguimientos'] = seguimiento.matriculaseguimientotutorsoporte_set.filter(status=True).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                    return render(request, 'pro_tutoria/visualizarseguimientodetallesoporte.html', data)
                except Exception as ex:
                    pass

            if action == 'addllamada':
                try:
                    hora = str(datetime.now().hour)
                    minuto = str(datetime.now().minute)
                    h = u"%s:%s" % (hora,minuto)
                    data['title'] = u'Llamada Realizada'
                    data['matriculaseguimiento'] = MatriculaSeguimientoTutor.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form'] = LlamadaRealizadaForm(initial={'hora': h, 'fecha': hoy})
                    return render(request, "pro_tutoria/addllamada.html", data)
                except Exception as ex:
                    pass

            if action == 'addllamadasoporte':
                try:
                    hora = str(datetime.now().hour)
                    minuto = str(datetime.now().minute)
                    h = u"%s:%s" % (hora,minuto)
                    data['title'] = u'Llamada Realizada'
                    data['matricula'] = Matricula.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form'] = LlamadaRealizadaForm(initial={'hora': h,
                                                                 'fecha': hoy})
                    return render(request, "pro_tutoria/addllamadasoporte.html", data)
                except Exception as ex:
                    pass

            # if action == 'addllamadasoporte':
            #     try:
            #         hora = str(datetime.now().hour)
            #         minuto = str(datetime.now().minute)
            #         h = u"%s:%s" % (hora,minuto)
            #         data['title'] = u'Llamada Realizada'
            #         data['matriculaseguimiento'] = MatriculaSeguimientoTutorSoporte.objects.get(pk=int(encrypt(request.GET['id'])))
            #         data['form'] = LlamadaRealizadaForm(initial={'hora': h,
            #                                                      'fecha': hoy})
            #         return render(request, "pro_tutoria/addllamadasoporte.html", data)
            #     except Exception as ex:
            #         pass
            #
            if action == 'addrespuesta':
                try:
                    data['title'] = u'Respuesta recibida'
                    hora = str(datetime.now().hour)
                    minuto = str(datetime.now().minute)
                    h = u"%s:%s" % (hora, minuto)
                    data['matriculaseguimiento'] = MatriculaSeguimientoTutor.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form'] = RespuestaRecibidaForm(initial={'hora': h, 'fecha': hoy})
                    return render(request, "pro_tutoria/addrespuesta.html", data)
                except Exception as ex:
                    pass

            if action == 'addrespuestasoporte':
                try:
                    data['title'] = u'Respuesta Recibida'
                    hora = str(datetime.now().hour)
                    minuto = str(datetime.now().minute)
                    h = u"%s:%s" % (hora, minuto)
                    data['matricula'] = Matricula.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form'] = RespuestaRecibidaForm(initial={'hora': h,
                                                                  'fecha': hoy})
                    return render(request, "pro_tutoria/addrespuestasoporte.html", data)
                except Exception as ex:
                    pass

            # if action == 'addrespuestasoporte':
            #     try:
            #         data['title'] = u'Respuesta Recibida'
            #         hora = str(datetime.now().hour)
            #         minuto = str(datetime.now().minute)
            #         h = u"%s:%s" % (hora, minuto)
            #         data['matriculaseguimiento'] = MatriculaSeguimientoTutorSoporte.objects.get(pk=int(encrypt(request.GET['id'])))
            #         data['form'] = RespuestaRecibidaForm(initial={'hora': h,
            #                                                      'fecha': hoy})
            #         return render(request, "pro_tutoria/addrespuestasoporte.html", data)
            #     except Exception as ex:
            #         pass
            #
            elif action == 'respondersolicitud':
                try:
                    data['title'] = u'Solicitud'
                    data['estado'] = request.GET['estado']
                    solicitud = SolicitudTutorSoporteMatricula.objects.get(pk=int(encrypt(request.GET['id'])))
                    if solicitud.estado==1:
                        solicitud.estado=2
                        solicitud.save(request)
                    form = SolicitudTutorRespuestaForm(initial={'tipo': solicitud.tipo,
                                                                'descripcion': solicitud.descripcion})
                    data['idsolicitud'] = solicitud.id
                    form.respuestas()
                    data['form'] = form
                    return render(request, "pro_tutoria/respondersolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'respondersolicitudmodal':
                try:
                    data['title'] = u'Solicitud'
                    data['solicitud'] = solicitud = SolicitudTutorSoporteMateria.objects.get(pk=int(request.GET['id']))
                    form = SolicitudTutorRespuestaForm(initial={'tipo': solicitud.tipo, 'descripcion': solicitud.descripcion})
                    data['idsolicitud'] = solicitud.id
                    form.respuestas()
                    data['form'] = form
                    # return render(request, "pro_tutoria/respondersolicitud.html", data)
                    template = get_template("pro_tutoria/respondersolicitudmodal.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'observacionsolicitud':
                try:
                    data['title'] = u'Solicitud'
                    data['estado'] = request.GET['estado']
                    solicitud = SolicitudTutorSoporteMatricula.objects.get(pk=int(encrypt(request.GET['id'])))
                    if solicitud.estado==1:
                        solicitud.estado=2
                        solicitud.save(request)
                    form = SolicitudTutorObservacionForm()
                    data['idsolicitud'] = solicitud.id
                    data['form'] = form
                    return render(request, "pro_tutoria/observacionsolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'eliminarseguimiento':
                try:
                    data['title'] = u'Eliminar Seguimiento'
                    data['seguimiento'] = seguimiento = SeguimientoTutor.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "pro_tutoria/eliminarseguimiento.html", data)
                except Exception as ex:
                    pass

            elif action == 'calcularseguimiento':
                try:
                    data['title'] = u'Calcular Seguimiento'
                    data['seguimiento'] = seguimiento = SeguimientoTutor.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "pro_tutoria/calcularseguimiento.html", data)
                except Exception as ex:
                    pass


            elif action == 'calcularseguimientosoporte':
                try:
                    data['title'] = u'Calcular Seguimiento'
                    data['seguimiento'] = seguimiento = SeguimientoTutorSoporte.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "pro_tutoria/calcularseguimientosoporte.html", data)
                except Exception as ex:
                    pass

            elif action == 'eliminarseguimientosoporte':
                try:
                    data['title'] = u'Eliminar Seguimiento'
                    data['seguimiento'] = seguimiento = SeguimientoTutorSoporte.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "pro_tutoria/eliminarseguimientosoporte.html", data)
                except Exception as ex:
                    pass

            elif action == 'descargaracompanamiento':
                try:
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    # ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_estudiantes' + random.randint(1,10000).__str__() + '.xls'
                    row_num = 0
                    columns = [
                        (u"N.", 2000),
                        (u"CÉDULA", 4000),
                        (u"NOMBRE", 4000),
                        (u"DIRECCIÓN", 7000),
                        (u"TELÉFONO", 4000),
                        (u"CELULAR", 4000),
                        (u"PPL", 4000),
                        (u"CORREO PERSONAL", 4000),
                        (u"CORREO INSTITUCIONAL", 4000),
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    hora_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    hora_format = xlwt.easyxf(num_format_str='h:mm')
                    materia = Materia.objects.get(pk=int(encrypt(request.GET['id'])))
                    materiasasignadas = materia.materiaasignada_set.filter(matricula__estado_matricula__in=[2,3]).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                    row_num = 0
                    for lista in materiasasignadas:
                        row_num += 1
                        if lista.matricula.inscripcion.persona.cedula:
                            campo2 = lista.matricula.inscripcion.persona.cedula
                        else:
                            campo2 = lista.matricula.inscripcion.persona.pasaporte
                        campo3 = u"%s %s %s" % (lista.matricula.inscripcion.persona.apellido1, lista.matricula.inscripcion.persona.apellido2,
                                                lista.matricula.inscripcion.persona.nombres)
                        campo4 = u"%s %s" % (lista.matricula.inscripcion.persona.direccion, lista.matricula.inscripcion.persona.direccion2)
                        campo5 = u"%s" % (lista.matricula.inscripcion.persona.telefono_conv)
                        campo6 = u"%s" % (lista.matricula.inscripcion.persona.telefono)
                        ppl = u"SI ES PPL" if lista.matricula.inscripcion.persona.ppl else "NO ES PPL"
                        email=u"%s" % (lista.matricula.inscripcion.persona.email)
                        emailinst=u"%s" % (lista.matricula.inscripcion.persona.emailinst)
                        ws.write(row_num, 0, row_num, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        ws.write(row_num, 6, ppl, font_style2)
                        ws.write(row_num, 7, email, font_style2)
                        ws.write(row_num, 8, emailinst, font_style2)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'descargarsoportte':
                try:
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    # ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_estudiantes' + random.randint(1,10000).__str__() + '.xls'
                    row_num = 0
                    columns = [
                        (u"N.", 2000),
                        (u"CÉDULA", 4000),
                        (u"NOMBRE", 4000),
                        (u"DIRECCIÓN", 7000),
                        (u"TELÉFONO", 4000),
                        (u"CELULAR", 4000),
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    hora_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    hora_format = xlwt.easyxf(num_format_str='h:mm')
                    carrera = Carrera.objects.get(pk=int(encrypt(request.GET['id'])))
                    idmatriculados = SoporteAcademicoTutor.objects.values_list('materiaasignada__id', flat=True).filter(periodo=periodo, tutor=profesor, status=True)
                    # materiasasignadas = MateriaAsignada.objects.filter(id__in=idmatriculados, matricula__estado_matricula__in=[2,3], materia__asignaturamalla__malla__carrera=carrera).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2').distinct()
                    materiasasignadas = Matricula.objects.filter(materiaasignada__id__in=idmatriculados,estado_matricula__in=[2,3],materiaasignada__materia__asignaturamalla__malla__carrera=carrera).order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2').distinct()
                    row_num = 0
                    for lista in materiasasignadas:
                        row_num += 1
                        if lista.inscripcion.persona.cedula:
                            campo2 = lista.inscripcion.persona.cedula
                        else:
                            campo2 = lista.inscripcion.persona.pasaporte
                        campo3 = u"%s %s %s" % (lista.inscripcion.persona.apellido1, lista.inscripcion.persona.apellido2,lista.inscripcion.persona.nombres)
                        campo4 = u"%s %s" % (lista.inscripcion.persona.direccion, lista.inscripcion.persona.direccion2)
                        campo5 = u"%s" % (lista.inscripcion.persona.telefono_conv)
                        campo6 = u"%s" % (lista.inscripcion.persona.telefono)

                        ws.write(row_num, 0, row_num, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'respondersolicitudmimateria':
                try:
                    data['title'] = u'Solicitud'
                    data['solicitud'] = solicitud = SolicitudTutorSoporteMateria.objects.get(pk=int(encrypt(request.GET['id'])))
                    if solicitud.estado==1:
                        solicitud.estado=2
                        solicitud.save(request)
                    form = SolicitudTutorRespuestaForm(initial={'tipo': solicitud.tipo,
                                                                'descripcion': solicitud.descripcion})
                    form.respuestas()
                    data['form'] = form
                    return render(request, "pro_tutoria/respondersolicitudmimateria.html", data)
                except Exception as ex:
                    pass

            elif action == 'observacionsolicitudmimateria':
                try:
                    data['title'] = u'Solicitud'
                    data['solicitud'] = solicitud = SolicitudTutorSoporteMateria.objects.get(pk=int(encrypt(request.GET['id'])))
                    if solicitud.estado == 1:
                        solicitud.estado = 2
                        solicitud.save(request)
                    form = SolicitudTutorObservacionForm()
                    data['form'] = form
                    return render(request, "pro_tutoria/observacionsolicitudmimateria.html", data)
                except Exception as ex:
                    pass


            elif action == 'verobservacionesmimateria':
                try:
                    data['solicitud'] = solicitud = SolicitudTutorSoporteMateria.objects.get(pk=int(request.GET['id']))
                    data['title'] = 'Gestion de respuestas de seguimiento acádemico'
                    # data['respuestas_tutor'] = respuesta = solicitud.respuestasolicitudtutorsoportemateria_set.filter(
                    #     status=True).order_by('id')
                    # data['observaciones_tutor'] = solicitud.observacionsolicitudtutorsoportemateria_set.filter(
                    #     status=True).order_by('-id')
                    # data['atendido'] = ''
                    # data['respuestas_estudiante'] = respuestas = []
                    # if respuesta:
                    #     for r in solicitud.respuestas():
                    #         print(r.archivo)
                    #         # item = {'descripcion': r.descripcion, 'atendido': r.atendida,
                    #         #         'respuesta_estudiante': r.respuesta, 'estado': r.solicitud.estado}
                    #         # respuestas.append(model_to_dict(r))
                    #     data['respuestas'] = respuestas
                    #     # data['atendido'] = respuesta[0].atendida
                    #     # data['respuestas_estudiante'] = respuesta[0].respuesta
                    # # template = get_template("pro_tutoria/verobservacionesmimateria.html")
                    # # json_content = template.render(data)

                    return render(request, "pro_tutoria/gestionrespuestas.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass


            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Acompañamiento y soporte'
                data['materias'] = Materia.objects.filter(profesormateria__profesor=profesor, nivel__periodo=periodo,nivel__periodo__visible=True).distinct().order_by('-profesormateria__tipoprofesor_id', 'asignatura')
                data['profesormaterias'] = profesormateria = ProfesorMateria.objects.filter(profesor=profesor,materia__nivel__periodo=periodo,materia__nivel__periodo__visible=True,status=True,activo=True).distinct().order_by('materia__asignatura')
                #Acompañamiento academico
                materiasprofesor = None
                if periodo:
                    if periodo.ocultarmateria:
                        materiasprofesor = None
                    else:
                        # materiasprofesor = Materia.objects.filter(profesormateria__profesor=profesor, profesormateria__tipoprofesor__id__in=[8] , nivel__periodo=periodo,nivel__periodo__visible=True, profesormateria__status=True,status=True,profesormateria__activo=True).distinct().order_by('asignatura').distinct()
                        materiasprofesor = Materia.objects.filter(profesormateria__profesor=profesor, nivel__periodo=periodo,nivel__periodo__visible=True, profesormateria__status=True,status=True,profesormateria__activo=True).distinct().order_by('-profesormateria__tipoprofesor_id', 'asignatura').distinct()

                # Extrae materias con profesor tipo tutor virtual, excluyendo materias donde el docente(logueado) sea tipo tutor virtual
                materiacontutorvirtual = materiasprofesor.filter(profesormateria__tipoprofesor_id=8).values_list('id', flat=True).exclude(pk__in=materiasprofesor.filter(profesormateria__tipoprofesor_id=8, profesormateria__profesor=profesor).values_list('id', flat=True))

                # Solo para carreras en linea y materias transvresales
                if periodo.tipo_id != 3 and periodo.clasificacion != 2:
                    if materiasprofesor:
                        materiasprofesor = materiasprofesor.filter(Q(asignaturamalla__transversal=True) | Q(asignaturamalla__malla__carrera__modalidad=3) | Q(asignaturamalla__malla__carrera__coordinacion=9)).exclude(pk__in=materiacontutorvirtual)

                # Soporte Academico
                carreramateriasprofesor = None
                if periodo:
                    if periodo.ocultarmateria:
                        carreramateriasprofesor = None
                    else:
                        carreramateriasprofesor = Carrera.objects.filter(status=True, malla__asignaturamalla__materia__materiaasignada__soporteacademicotutor__tutor=profesor ,malla__status=True,malla__asignaturamalla__status=True, malla__asignaturamalla__materia__status=True, malla__asignaturamalla__materia__materiaasignada__soporteacademicotutor__periodo=periodo).distinct().order_by('nombre').distinct()
                    # carreramateriasprofesor = Materia.objects.filter(status=True, materiaasignada__soporteacademicotutor__tutor=profesor ,materiaasignada__status=True, materiaasignada__soporteacademicotutor__periodo=periodo, materiaasignada__soporteacademicotutor__status=True).distinct().order_by('asignaturamalla').distinct()
                data['carreramateriasprofesor'] = carreramateriasprofesor
                data['periodo'] = periodo
                data['profesor'] = profesor
                data['numeros_estudiantes'] = Inscripcion.objects.filter(status=True, matricula__estado_matricula__in=[2,3], matricula__materiaasignada__soporteacademicotutor__periodo=periodo, matricula__materiaasignada__soporteacademicotutor__tutor=profesor).distinct().count()
                idstipo =  materiasprofesor.filter(profesormateria__profesor=profesor).values_list('profesormateria__tipoprofesor_id', flat=True).distinct()
                data['tipoprofesor'] = TipoProfesor.objects.filter(id__in=idstipo).values_list('profesormateria__tipoprofesor_id', 'profesormateria__tipoprofesor__nombre').distinct()
                estado = 1
                if 'estado' in request.GET:
                    estado = int(request.GET['estado'])
                if 'tipopro' in request.GET:
                    data['tipopro'] = tipopro = int(request.GET['tipopro'])
                    if tipopro > 0:
                        materiasprofesor = materiasprofesor.filter(profesormateria__tipoprofesor_id=tipopro, profesormateria__profesor=profesor)
                data['estado_seleccionado'] = estado
                solicitudes = SolicitudTutorSoporteMatricula.objects.filter(status=True, matricula__estado_matricula__in=[2,3], matricula__materiaasignada__soporteacademicotutor__periodo=periodo, matricula__materiaasignada__soporteacademicotutor__tutor=profesor).distinct()
                # data['solicitudes'] = solicitudes.filter(estado=estado).distinct()
                data['sol'] = sol = SolicitudTutorSoporteMateria.objects.filter(
                    status=True, profesor=profesor, materiaasignada__matricula__estado_matricula__in=[2, 3],
                    materiaasignada__matricula__nivel__periodo=periodo).distinct()

                data['estados'] = estados = []
                for e in ESTADO_SOLICITUD_TUTOR:
                    if not e[0] == 4:
                        estados.append([e[0], e[1], sol.filter(estado=e[0]).distinct().count()])
                estadosolicitudmimateria=1
                if 'estadosolicitudmimateria' in request.GET:
                    estadosolicitudmimateria = int(request.GET['estadosolicitudmimateria'])
                data['estadosolicitudmimateria'] = estadosolicitudmimateria
                data['solicitudesmimateria'] =solicitudesmimateria= SolicitudTutorSoporteMateria.objects.filter(status=True,profesor=profesor, materiaasignada__matricula__estado_matricula__in=[2, 3], materiaasignada__matricula__nivel__periodo=periodo, estado=estadosolicitudmimateria).distinct()
                data['tiponomostrar'] = [3, 4]
                data['fechaactual'] = datetime.now().date()


                # para mostrar los seguimientos de las materias transaversales

                if profesor.autor_puede_ver_seguimentos(periodo):
                    formato = "%Y-%m-%d"
                    hoy = datetime.now().date()
                    asig=DetalleGrupoAsignatura.objects.filter(status=True, grupo__responsablegrupoasignatura__profesor=profesor).values('asignatura_id')
                    pids = ProfesorMateria.objects.filter(materia__nivel__periodo=periodo,profesor__persona__real=True, materia__asignaturamalla__transversal=True, materia__asignatura_id__in=asig, activo=True, tipoprofesor_id=16).values_list('profesor_id', flat=True)
                    data['profesores'] = Profesor.objects.filter(status=True, id__in=pids, persona__real=True).distinct()
                    search, desde, hasta, filtro = request.GET.get('s', ''), request.GET.get('desde', datetime(hoy.year, hoy.month, 1)), request.GET.get('hasta', datetime(hoy.year, hoy.month, calendar.monthrange(hoy.year, hoy.month)[1])), Q(status=True)
                    if 'desde' in request.GET:
                        desde = datetime.strptime(desde, formato).date()
                    if 'hasta' in request.GET:
                        hasta = datetime.strptime(hasta, formato).date()
                    data['desde'] = desde
                    data['hasta'] = hasta
                if periodo.ocultarmateria:
                    materiasprofesor = False
                data['materiasprofesor'] = materiasprofesor.distinct().order_by('id')
                data['firstmat'] = materiasprofesor.first()
                return render(request, "pro_tutoria/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect(f"/?info=No puede acceder al módulo")
