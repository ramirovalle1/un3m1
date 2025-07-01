# -*- coding: UTF-8 -*-
import json
import random
import sys
from datetime import timedelta, datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
import xlwt
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import Context
from django.template.loader import get_template
from django.views.decorators.csrf import csrf_exempt
from xlwt import *
from django.shortcuts import render
from decorators import secure_module, last_access
from sagest.forms import DepartamentoForm, IntegranteDepartamentoForm, ResponsableDepartamentoForm, \
    SeccionDepartamentoForm
from sagest.models import Departamento, SeccionDepartamento, OpcionSistema
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.tasks import send_html_mail
from .forms import ProcesoForm, CategoriaBalconForm, TipoBalconForm, RequisitoBalconForm, ServicioBalconForm, \
    AgenteForm, AsignarServicioForm, SolicitudBalconReasignarForm, SolicitudBalconRespuestaRapidaForm, \
    SolicitudBalconResolverForm, SolicitudBalconRespuestaRechazarForm, SolicitudBalconCerrarForm, \
    SolicitudBalconReasignarInternoForm, SolicitudManualBalconForm, SolicitudBalconGestionarForm
from sga.funciones import MiPaginador, log, generar_nombre, notificacion, convertir_fecha_invertida
from sga.models import Administrativo, Persona, TestSilaboSemanalAdmision, MateriaAsignada, Materia, Asignatura, \
    CUENTAS_CORREOS, Carrera, Coordinacion, Inscripcion, Externo
from .models import Proceso, Tipo, Categoria, Requisito, \
    Servicio, Agente, Solicitud, HistorialSolicitud, TIPO_SOLICITUD_BALCON, ESTADO_SOLICITUD_BALCON, ProcesoServicio, \
    Informacion, RequisitosConfiguracion, RequisitosSolicitud, ESTADO_HISTORIAL_SOLICITUD_BALCON, \
    RegistroNovedadesExternoAdmision
from .models import Proceso, Tipo, Categoria, Requisito,ResponsableDepartamento, \
    Servicio, Agente, Solicitud, HistorialSolicitud, TIPO_SOLICITUD_BALCON, ESTADO_SOLICITUD_BALCON, ProcesoServicio
from django.db.models import OuterRef, Subquery

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    hoy=datetime.now()
    usuario = request.user
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addsolicitudmodal':
            try:
                with transaction.atomic():
                    newfile = None
                    tipo = int(request.POST['tipo'])
                    form = SolicitudManualBalconForm(request.POST, request.FILES)
                    if form.is_valid():
                        servicio = ProcesoServicio.objects.get(pk=int(request.POST['servicio']))
                        subesolicitud = servicio.proceso.subesolicitud
                        solicitante = Persona.objects.get(pk=request.POST['persona'])
                        perfil = None
                        if solicitante.perfilusuario_set.filter(visible=True,inscripcionprincipal=True).exists():
                            perfil = solicitante.perfilusuario_set.filter(visible=True,inscripcionprincipal=True).first()
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Persona no cuenta con perfil usuario"}, safe=False)
                        ultimasoli = Solicitud.objects.filter(solicitante=solicitante).order_by('numero').last()
                        numsoli = ultimasoli.numero + 1 if ultimasoli else 1
                        tipo = int(request.POST['tipo'])
                        soli = Solicitud(descripcion=form.cleaned_data['descripcion'].upper(),
                                         tipo=tipo,
                                         solicitante=solicitante,
                                         perfil=perfil,
                                         estado=1,
                                         numero=numsoli)
                        if subesolicitud:
                            if 'doc_solicitud' in request.FILES:
                                newfile = request.FILES['doc_solicitud']
                                extension = newfile._name.split('.')
                                tam = len(extension)
                                exte = extension[tam - 1]
                                if newfile.size > 4194304:
                                    return JsonResponse(
                                        {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                                if exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                                    newfile._name = generar_nombre("solicitud_", newfile._name)
                                else:
                                    return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                                soli.archivo = newfile
                            else:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": True, "mensaje": "FALTA SUBIR SOLICITUD"}, safe=False)
                        agentelibre = None
                        if Agente.objects.filter(status=True, estado=True).exists():
                            agente = Agente.objects.filter(status=True, estado=True)
                            agenteslista = {}
                            for a in agente:
                                agenteslista[a.pk] = a.total_solicitud()
                            ordenados = sorted(agenteslista.items(), key=lambda x: x[1])
                            agentelibre = Agente.objects.get(pk=ordenados[0][0])
                            soli.agente = agentelibre
                        soli.save(request)
                        requisitos = servicio.requisitosconfiguracion_set.filter(status=True)
                        for req in requisitos:
                            if not'doc_{}'.format(req.requisito.pk) in request.FILES:
                                if req.obligatorio:
                                    nombredocumento = req.requisito.nombre
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": True, "mensaje": "FALTA SUBIR {}".format(nombredocumento)},safe=False)
                            else:
                                solicitante = Persona.objects.get(pk=request.POST['persona'])
                                nombrepersona_str = solicitante.__str__().lower().replace(' ', '_')
                                nombre = req.requisito.pk
                                nombredoc = "doc_{}".format(req.requisito.pk)
                                newfile = request.FILES[nombredoc]
                                nombrefoto = '{}_{}'.format(nombrepersona_str, nombre)
                                newfile._name = generar_nombre(nombrefoto.strip(), newfile._name)
                                det = RequisitosSolicitud(solicitud=soli, requisito=req, archivo=newfile)
                                det.save(request)
                        log(u'Adiciono Solicitud para el balcon: %s' % soli, request, "add")
                        #proceso_id = int(request.POST['proceso']) if 'proceso' in request.POST and request.POST['proceso'] else 0
                        servicio_id = int(request.POST['servicio']) if 'servicio' in request.POST and request.POST['servicio'] else 0
                        if Servicio.objects.filter(pk=servicio_id).exists():
                            historial = HistorialSolicitud(servicio_id=servicio_id,
                                                           solicitud=soli,
                                                           asignadorecibe=agentelibre.persona if agentelibre else None)
                            historial.save(request)
                            log(u'Se asigna servicio: %s' % historial.servicio, request, "add")

                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde. -- {}".format(ex)}, safe=False)

        if action == 'addprocesosol':
            try:
                f = AsignarServicioForm(request.POST)
                solicitud = Solicitud.objects.get(id=request.POST['id'])
                solicitud.save(request)
                if f.is_valid():
                    historial = HistorialSolicitud(
                                                   solicitud=solicitud,
                                                   asignaenvia=persona,
                                                   servicio=f.cleaned_data['servicio'],
                                                   )
                    historial.save(request)
                    solicitud.agenteactual = persona
                    solicitud.save(request)
                    log(u'Adiciono proceso a solicitud: %s' % historial, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde. -- {}".format(ex)}, safe=False)

        if action == 'cambiaprocesosol':
            try:
                f = AsignarServicioForm(request.POST)
                solicitud = Solicitud.objects.get(id=request.POST['id'])
                if f.is_valid():

                    historialbase = HistorialSolicitud.objects.filter(solicitud=solicitud).last()
                    historial = HistorialSolicitud(solicitud=solicitud,
                                                   asignadorecibe=historialbase.asignadorecibe,
                                                   servicio=f.cleaned_data['servicio'],
                                                   )
                    historial.save(request)
                    solicitud.agenteactual = historial.asignadorecibe
                    solicitud.save(request)
                    proceso = historial.servicio.proceso
                    historial.departamento = proceso.departamento
                    historial.asignadorecibe = proceso.persona
                    historial.asignaenvia = persona
                    historial.estado = 1
                    historial.save(request)
                    solicitud.estado = 3
                    solicitud.save(request)
                    log(u'Cambió proceso a solicitud: %s' % historial, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde. -- {}".format(ex)}, safe=False)

        if action == 'addrespuestarapida':
            with transaction.atomic():
                try:
                    filtro = Solicitud.objects.get(pk=request.POST['id'])
                    filtro.estado = 4
                    filtro.save(request)
                    historialbase = HistorialSolicitud.objects.filter(solicitud=filtro).last()
                    nota = HistorialSolicitud(solicitud=filtro,
                                              asignadorecibe=historialbase.asignadorecibe,
                                              departamento=historialbase.departamento,
                                              asignaenvia=persona,
                                              observacion=request.POST['observacion'],
                                              servicio=historialbase.servicio,
                                              estado=4)
                    nota.save(request)
                    filtro.agenteactual = nota.asignadorecibe
                    filtro.save(request)
                    log(u'Adiciono una respuesta rapida en balcon: %s' % filtro, request, "add")

                    # if 'notificaralumno' in request.POST:
                    #     if request.POST['notificaralumno'] == 'on':
                    #         send_html_mail("COMPROBANTE PAGO RECIBIDO", "emails/respcomprobantealumno.html",
                    #                        {
                    #                            'sistema': u'EMPRESA PUBLICA DE PRODUCCIÓN Y DESARROLLO ESTRATÉGICO DE LA UNIVERSIDAD ESTATAL DE MILAGRO',
                    #                            'pago': filtro, 'nota': nota, 't': miinstitucion()}, [filtro.email], [],
                    #                        None, cuenta=CUENTAS_CORREOS[4][1])

                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde. -- {}".format(ex)}, safe=False)

        if action == 'resolver':
            with transaction.atomic():
                try:
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        extension = newfile._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if newfile.size > 4194304:
                            return JsonResponse({"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                        if exte in ['pdf','jpg','jpeg','png','jpeg','peg']:
                            newfile._name = generar_nombre("cerrarsolicitud_", newfile._name)
                        else:
                            return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                    filtro = Solicitud.objects.get(pk=request.POST['id'])
                    filtro.estado = 3
                    filtro.save(request)
                    historialbase = HistorialSolicitud.objects.filter(solicitud=filtro).last()
                    nota = HistorialSolicitud(solicitud=filtro,
                                       asignadorecibe=historialbase.asignadorecibe,
                                       departamento=historialbase.departamento,
                                       asignaenvia=persona,
                                       observacion=request.POST['observacion'],
                                       servicio=historialbase.servicio,
                                       estado=3)
                    if 'archivo' in request.FILES:
                        nota.archivo = newfile
                    nota.save(request)
                    filtro.agenteactual = nota.asignadorecibe
                    filtro.save(request)
                    log(u'Cerro Solicitud en balcon: %s' % filtro, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde. -- {}".format(ex)}, safe=False)

        if action == 'reasignar':
            with transaction.atomic():
                try:
                    # if request.POST['departamento'] == '0':
                    #     transaction.set_rollback(True)
                    #     return JsonResponse({"result": True, "mensaje": "Debe asignar una dirección."}, safe=False)
                    #
                    # departamento = Departamento.objects.get(pk=int(request.POST['departamento']))

                    # if HistorialSolicitud.objects.filter( status=True,solicitud_id=int(request.POST['id']),asignadorecibe_id=int(request.POST['asignadorecibe'])).exists():
                    #     transaction.set_rollback(True)
                    #     return JsonResponse({"result": True, "mensaje": "Esta persona ya cuenta con una asignación en esta solicitud."}, safe=False)

                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        extension = newfile._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if newfile.size > 4194304:
                            return JsonResponse({"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                        if exte in ['pdf','jpg','jpeg','png','jpeg','peg']:
                            newfile._name = generar_nombre("cerrarsolicitud_", newfile._name)
                        else:
                            return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                    filtro = Solicitud.objects.get(pk=request.POST['id'])

                    historialbase = HistorialSolicitud.objects.filter(solicitud=filtro).last()
                    asignadorecibe = Persona.objects.get(pk=int(request.POST['asignadorecibe']))
                    nota = HistorialSolicitud(solicitud=filtro,
                                              asignaenvia=persona,
                                              servicio=historialbase.servicio,
                                              asignadorecibe=asignadorecibe,
                                              departamento=asignadorecibe.mi_departamento(),
                                              departamentoenvia=persona.mi_departamento(),
                                              observacion=request.POST['observacion'],
                                              estado=2)
                    if 'archivo' in request.FILES:
                        nota.archivo = newfile
                    nota.save(request)
                    filtro.agenteactual = nota.asignadorecibe
                    filtro.save(request)
                    log(u'Cerro Solicitud en balcon: %s' % filtro, request, "add")
                    titulo=f"Reasignación de solicitud de {filtro.solicitante.nombre_completo_minus()} en balcón de servicios"
                    cuerpo = f'Se ha reasignado una solicitud de {filtro.solicitante.nombre_completo_minus()}'
                    notificacion(titulo,cuerpo, nota.asignadorecibe, None, 'adm_solicitudbalcon', filtro.id, 1, 'sga', Solicitud, request)
                    lista_email = nota.asignadorecibe.lista_emails()
                    # lista_email = ['jguachuns@unemi.edu.ec', ]
                    datos_email = {'sistema': request.session['nombresistema'],
                                   'fecha': hoy.date(),
                                   'hora': hoy.time(),
                                   'historial_s': nota,
                                   'persona': nota.asignadorecibe,
                                   'mensaje': cuerpo}
                    template = "emails/notificacion_balcon.html"
                    send_html_mail(titulo, template, datos_email, lista_email, [], [],cuenta=CUENTAS_CORREOS[0][1])
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde. -- {}".format(ex)}, safe=False)

        if action == 'reasignarinterno':
            with transaction.atomic():
                try:

                    asignadorecibe = int(request.POST['asignadorecibe'])
                    departamento = persona.mi_departamento()

                    if HistorialSolicitud.objects.filter(asignadorecibe_id=asignadorecibe,solicitud_id=int(request.POST['id']), status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True,
                                             "mensaje": "La persona ya cuenta con una asignación en esta solicitud."},
                                            safe=False)

                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        extension = newfile._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if newfile.size > 4194304:
                            return JsonResponse(
                                {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                        if exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                            newfile._name = generar_nombre("cerrarsolicitud_", newfile._name)
                        else:
                            return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                    filtro = Solicitud.objects.get(pk=request.POST['id'])

                    historialbase = HistorialSolicitud.objects.filter(solicitud=filtro).last()
                    nota = HistorialSolicitud(solicitud=filtro,
                                              asignaenvia=persona,
                                              servicio=historialbase.servicio,
                                              asignadorecibe_id=int(request.POST['asignadorecibe']),
                                              departamentoenvia=departamento,
                                              departamento=departamento,
                                              observacion=request.POST['observacion'],
                                              estado=2)
                    if 'archivo' in request.FILES:
                        nota.archivo = newfile
                    nota.save(request)
                    filtro.agenteactual = nota.asignadorecibe
                    filtro.save(request)
                    log(u'Reasigna interno solicitud en balcon: %s' % filtro, request, "add")

                    titulo=f"Reasignación de solicitud de {filtro.solicitante.nombre_completo_minus()} en balcón de servicios"
                    cuerpo = f'Se ha reasignado una solicitud de {filtro.solicitante.nombre_completo_minus()}'
                    notificacion("Solicitud de %s en balcón de servicios" % filtro.solicitante,
                                 cuerpo, nota.asignadorecibe, None, 'adm_solicitudbalcon', filtro.id,
                                 1, 'sga', Solicitud, request)
                    lista_email = nota.asignadorecibe.lista_emails()
                    # lista_email = ['jguachuns@unemi.edu.ec', ]
                    datos_email = {'sistema': request.session['nombresistema'],
                                   'fecha': hoy.date(),
                                   'hora': hoy.time(),
                                   'historial_s': nota,
                                   'persona': nota.asignadorecibe,
                                   'mensaje': cuerpo}
                    template = "emails/notificacion_balcon.html"
                    send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde. -- {}".format(ex)}, safe=False)

        if action == 'enviardepa':
                    with transaction.atomic():
                        try:
                            solicitud = Solicitud.objects.get(pk=int(request.POST['id']))
                            proceso =  solicitud.historialsolicitud_set.filter(status=True).last()
                            personalibre = None
                            if ResponsableDepartamento.objects.filter(status=True, estado=True,departamento=proceso.servicio.proceso.departamento).exists():
                                responsables = ResponsableDepartamento.objects.filter(status=True, estado=True,departamento=proceso.servicio.proceso.departamento)
                                agenteslista = {}
                                for a in responsables:
                                    agenteslista[a.pk] = a.total_solicitud()
                                ordenados = sorted(agenteslista.items(), key=lambda x: x[1])
                                personalibre = ResponsableDepartamento.objects.get(pk=ordenados[0][0])
                            else:
                                return JsonResponse({"result": True, "mensaje": "La dirección no cuenta con un responsable."}, safe=False)


                            historial = HistorialSolicitud(
                                solicitud = solicitud,
                                asignaenvia=persona,
                                asignadorecibe=personalibre.responsable,
                                #departamentoenvia=persona.departamentopersona(),
                                departamento=proceso.servicio.proceso.departamento,
                                servicio=proceso.servicio,
                                estado=2
                            )
                            solicitud.estado=3
                            historial.save(request)
                            solicitud.agenteactual = historial.asignadorecibe
                            solicitud.save(request)
                            titulo = f"Solicitud de {solicitud.solicitante.nombre_completo_minus()} en balcón de servicios"
                            cuerpo = f'Ha recibido una solicitud de {solicitud.solicitante.nombre_completo_minus()}'
                            notificacion(titulo, cuerpo, personalibre.responsable, None, 'adm_solicitudbalcon', solicitud.id,1, 'sga', Solicitud, request)

                            lista_email = personalibre.responsable.lista_emails()
                            # lista_email = ['jguachuns@unemi.edu.ec', ]
                            datos_email = {'sistema': request.session['nombresistema'],
                                           'fecha': hoy.date(),
                                           'hora': hoy.time(),
                                           'solicitud': solicitud,
                                           'servicio':historial.servicio,
                                           'persona': personalibre.responsable,
                                           'mensaje': cuerpo}
                            template = "emails/notificacion_balcon.html"
                            send_html_mail(titulo, template, datos_email, lista_email, [], [],cuenta=CUENTAS_CORREOS[0][1])
                            return JsonResponse({'result': 'ok'})
                        except Exception as ex:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Intentelo más tarde. -- {}".format(ex)}, safe=False)

        if action == 'addagente':
            with transaction.atomic():
                try:
                    if request.POST['asignadorecibe'] == '0':
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Debe asignar una dirección."}, safe=False)
                    if HistorialSolicitud.objects.filter(asignadorecibe_id=int(request.POST['asignadorecibe']),
                                                         status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse(
                            {"result": True, "mensaje": "Está persona ya cuenta con una asignación en esta solicitud."},
                            safe=False)
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        extension = newfile._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if newfile.size > 4194304:
                            return JsonResponse(
                                {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                        if exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                            newfile._name = generar_nombre("cerrarsolicitud_", newfile._name)
                        else:
                            return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                    filtro = Solicitud.objects.get(pk=request.POST['id'])
                    nota = HistorialSolicitud(solicitud=filtro,
                                              asignaenvia=persona,
                                              asignadorecibe_id=int(request.POST['asignadorecibe']),
                                              departamento_id=int(request.POST['departamento']),
                                              observacion=request.POST['observacion'],
                                              estado=2)
                    if 'archivo' in request.FILES:
                        nota.archivo = newfile
                    nota.save(request)
                    filtro.agenteactual = nota.asignadorecibe
                    filtro.save(request)
                    log(u'Cerro Solicitud en balcon: %s' % filtro, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde. -- {}".format(ex)}, safe=False)

        if action == 'rechazar':
            with transaction.atomic():
                try:
                    filtro = Solicitud.objects.get(pk=request.POST['id'])
                    filtro.estado = 2
                    filtro.save(request)
                    historialbase = HistorialSolicitud.objects.filter(solicitud=filtro).last()
                    nota = HistorialSolicitud(solicitud=filtro,
                                              asignaenvia=persona,
                                              observacion=request.POST['observacion'],
                                              servicio=historialbase.servicio,
                                              asignadorecibe=historialbase.asignadorecibe,
                                              departamentoenvia=historialbase.departamentoenvia,
                                              departamento=historialbase.departamento,
                                              estado=4)
                    nota.save(request)
                    filtro.agenteactual = historialbase.asignadorecibe
                    filtro.save(request)
                    log(u'Rechazo Solicitud en balcon: %s' % filtro, request, "add")

                    titulo = f"Solicitud en balcón de servicios (Rechazada)"
                    cuerpo = ('Su solicitud ha sido rechazada. \n Motivo: %s' % nota.observacion)
                    notificacion(titulo,
                                 cuerpo, filtro.solicitante, None, 'alu_solicitudbalcon?action=misolicitudes', filtro.id,
                                 1, 'sga', Solicitud, request)
                    cuerpo=f'Su solicitud en {str(nota.servicio).lower()} fue cambiado de estado.'
                    lista_email = filtro.solicitante.lista_emails()
                    # lista_email = ['jguachuns@unemi.edu.ec', ]
                    datos_email = {'sistema': request.session['nombresistema'],
                                   'fecha': hoy.date(),
                                   'hora': hoy.time(),
                                   'validacion': nota,
                                   'persona': filtro.solicitante,
                                   'mensaje': cuerpo}
                    template = "emails/notificacion_balcon.html"
                    send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde. -- {}".format(ex)}, safe=False)

        if action == 'gestionar':
            with transaction.atomic():
                try:
                    filtro = Solicitud.objects.get(pk=request.POST['id'])
                    historialbase = HistorialSolicitud.objects.filter(solicitud=filtro).last()
                    f = SolicitudBalconGestionarForm(request.POST)
                    if f.is_valid():
                        if filtro.estado == 1 and (int(f.cleaned_data['estado']) == 4 or int(f.cleaned_data['estado']) == 3):
                            return JsonResponse({"result": True, "mensaje": "La solicitud no se encuentra en una dirección."}, safe=False)
                        filtro.estado = int(f.cleaned_data['estado'])
                        filtro.save(request)
                        estado = 4

                        if filtro.estado == 3 :
                            estado = 2
                        elif filtro.estado == 4 :
                            estado = 3
                        elif filtro.estado == 1 :
                            estado = 1


                        nota = HistorialSolicitud(solicitud=filtro,
                                                  asignaenvia=persona,
                                                  observacion=f.cleaned_data['observacion'],
                                                  servicio=historialbase.servicio,
                                                  asignadorecibe=historialbase.asignadorecibe,
                                                  departamentoenvia=historialbase.departamentoenvia,
                                                  departamento=historialbase.departamento,
                                                  estado=estado)
                        nota.save(request)
                        filtro.agenteactual = historialbase.asignadorecibe
                        filtro.save(request)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            extension = newfile._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if newfile.size > 4194304:
                                return JsonResponse(
                                    {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                            if exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                                newfile._name = generar_nombre("cerrarsolicitud_", newfile._name)
                            else:
                                return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                            nota.archivo = newfile
                            nota.save(request)
                        log(u'gestionó Solicitud en balcon: %s' % filtro, request, "add")

                        titulo = f"Solicitud en balcón de servicios ({filtro.get_estado_display().capitalize()})"
                        cuerpo = ('Su solicitud ha sido procesada. \n Motivo: %s' % nota.observacion)
                        notificacion('Estimado(a) %s su solicitud %s requiere atención ' % (filtro.solicitante,filtro.get_codigo()),
                                     cuerpo, filtro.solicitante, None, 'alu_solicitudbalcon?action=misolicitudes', filtro.id,
                                     1, 'sga', Solicitud, request)

                        cuerpo = f'Su solicitud en {str(nota.servicio).lower()} ha sido procesada'
                        lista_email = filtro.solicitante.lista_emails()
                        # lista_email = ['jguachuns@unemi.edu.ec', ]
                        datos_email = {'sistema': request.session['nombresistema'],
                                       'fecha': hoy.date(),
                                       'hora': hoy.time(),
                                       'validacion': nota,
                                       'persona': filtro.solicitante,
                                       'mensaje': cuerpo}
                        template = "emails/notificacion_balcon.html"
                        send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Formulario incorrecto o incompleto"}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde. -- {}".format(ex)}, safe=False)

        if action == 'cerrar':
            with transaction.atomic():
                try:
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        extension = newfile._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if newfile.size > 4194304:
                            return JsonResponse({"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                        if exte in ['pdf','jpg','jpeg','png','jpeg','peg']:
                            newfile._name = generar_nombre("cerrarsolicitud_", newfile._name)
                        else:
                            return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                    filtro = Solicitud.objects.get(pk=request.POST['id'])
                    filtro.estado = 5
                    historialbase = HistorialSolicitud.objects.filter(solicitud=filtro).last()
                    nota = HistorialSolicitud(solicitud=filtro,
                                              asignaenvia=historialbase.asignaenvia,
                                              asignadorecibe=historialbase.asignadorecibe,
                                              departamentoenvia=historialbase.departamentoenvia,
                                              departamento=historialbase.departamento,
                                              servicio=historialbase.servicio,
                                              observacion=request.POST['observacion'],
                                              estado=4)
                    if 'archivo' in request.FILES:
                        nota.archivo = newfile
                    nota.save(request)
                    filtro.agenteactual = historialbase.asignadorecibe
                    filtro.save(request)
                    log(u'Cerro Solicitud en balcon: %s' % filtro, request, "add")
                    cuerpo = (nota.observacion)

                    titulo = f"Solicitud en balcón de servicios ({filtro.get_estado_display().capitalize()})"
                    notificacion("Respuesta a solicitud %s en balcón de servicios" % filtro.codigo,
                                 cuerpo, filtro.solicitante, None, 'alu_solicitudbalcon?action=misolicitudes',
                                 filtro.id,
                                 1, 'sga', Solicitud, request)
                    cuerpo = f'Su solicitud en {str(nota.servicio).lower()} ha sido cerrada'
                    lista_email = filtro.solicitante.lista_emails()
                    # lista_email = ['jguachuns@unemi.edu.ec', ]
                    datos_email = {'sistema': request.session['nombresistema'],
                                   'fecha': hoy.date(),
                                   'hora': hoy.time(),
                                   'validacion': nota,
                                   'persona': filtro.solicitante,
                                   'mensaje': cuerpo}
                    template = "emails/notificacion_balcon.html"
                    send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde. -- {}".format(ex)}, safe=False)

        if action == 'reportefiltros':
            try:
                __author__ = 'Unemi'
                style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                  num_format_str='#,##0.00')
                style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                title = easyxf(
                    'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                style1 = easyxf(num_format_str='D-MMM-YY')
                fuentecabecera = easyxf(
                    'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('Listado')
                ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=Lista de solicitudes ' + random.randint(1,
                                                                                                                10000).__str__() + '.xls'
                columns = [
                    (u"N", 3000),
                    (u"NOMBRE SOLICITANTE", 12000),
                    (u"CEDULA", 4500),
                    (u"CARRERA", 12000),
                    (u"SERVICIO", 10000),
                    (u"TIPO DE SOLICITUD", 12000),
                    (u"ESTADO DE SOLICITUD", 12000),
                    (u"FECHA", 4500),
                    (u"AGENTE ASIGNADO", 10000),
                    (u"DIRECCIÓN ASIGNADA", 10000),
                    (u"FECHA ASIGNACIÓN A DIRECCIÓN", 10000)
                ]
                row_num = 1
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                    ws.col(col_num).width = columns[col_num][1]
                date_format = xlwt.XFStyle()
                date_format.num_format_str = 'yyyy-mm-dd'
                date_formatreverse = xlwt.XFStyle()
                date_formatreverse.num_format_str = 'dd/mm/yyyy'
                row_num = 2
                cont = 0


                # estadoselect = tiposelect = agenteselect =  desde = hasta = ''
                # if 'est' in request.POST:
                #     estadoselect = (request.POST['est'])
                # if 'tip' in request.POST:
                #     tiposelect = (request.POST['tip'])
                # if 'ag' in request.POST:
                #     agenteselect = (request.POST['ag'])
                # if 'desde' in request.POST:
                #     fechainicio = (request.POST['desde'])
                # if 'hasta' in request.POST:
                #     fechafin = (request.POST['hasta'])
                #     if hasta != '':
                #         fechaconv = convertir_fecha_invertida(request.POST['hasta'])
                #         fechafin = fechaconv + + timedelta(days=1)
                    # fechafin = (request.POST['hasta'])

                # if 'direccion' in request.POST:
                #     direccion = (request.POST['direccion'])
                #     historialdireccion = HistorialSolicitud.objects.filter(status=True, departamento_id=int(direccion)).values_list('solicitud__id', flat=True)
                #     filtro = filtro & Q(id__in=list(historialdireccion))

                # solicitudes = Solicitud.objects.filter(status=True).order_by('-fecha_creacion')
                # if estadoselect !='':
                #     solicitudes = solicitudes.filter(estado=estadoselect)
                # if tiposelect !='':
                #     solicitudes = solicitudes.filter(tipo=tiposelect)
                # if agenteselect !='':
                #     solicitudes = solicitudes.filter(agente_id=agenteselect)
                # if fechainicio !='':
                #     solicitudes = solicitudes.filter(fecha_creacion__gte=fechainicio)
                # if fechafin !='':
                #     solicitudes = solicitudes.filter(fecha_creacion__lte=fechafin)

                for sol in solicitudes:
                    cont += 1
                    historial = sol.traer_ultimo_con_departamento()
                    fecha = str(sol.fecha_creacion.date())
                    solicitante = str(sol.solicitante.nombre_completo_inverso())
                    carrera = str(sol.perfil.inscripcion.carrera) if sol.perfil.inscripcion else ''
                    cedula = sol.solicitante.identificacion()
                    servicio = str(sol.ver_servicio())
                    estado = str(sol.get_estado())
                    tipo = str(sol.get_tiposolicitud())
                    agente = str(sol.agente.persona.nombre_completo_inverso())
                    fecha_direccion =  str(historial.fecha_creacion.date()) if historial else ''
                    direccion = str(historial.departamento) if historial else ''

                    ws.write(row_num, 0, cont, font_style2)
                    ws.write(row_num, 1, solicitante, font_style2)
                    ws.write(row_num, 2, cedula, font_style2)
                    ws.write(row_num, 3, carrera, font_style2)
                    ws.write(row_num, 4, servicio, font_style2)
                    ws.write(row_num, 5, tipo, font_style2)
                    ws.write(row_num, 6, estado, font_style2)
                    ws.write(row_num, 7, fecha, font_style2)
                    ws.write(row_num, 8, agente, font_style2)
                    ws.write(row_num, 9, direccion, font_style2)
                    ws.write(row_num, 10, fecha_direccion, font_style2)
                    row_num += 1
                wb.save(response)
                return response
            except Exception as ex:
                pass

        if action == 'respondermasivo':
            with transaction.atomic():
                try:
                    estado = int(request.POST['estado'])
                    asignatura = int(request.POST['materia'])
                    test=TestSilaboSemanalAdmision.objects.get(id=int(request.POST['opcion']))

                    opciones = TestSilaboSemanalAdmision.objects.values_list('id').filter(titulo=test.titulo,status=True)
                    solicitudes = Solicitud.objects.filter(id__in=RegistroNovedadesExternoAdmision.objects.values_list('solicitud_id').filter(test_id__in=opciones,status=True,materiaasignada__materia__asignatura_id=asignatura),status=True,estado__gt=1)
                    # opcion = request.POST['opcion']
                    observacion = request.POST['observacion']

                    # solicitudes = Solicitud.objects.filter(id__in=RegistroNovedadesExternoAdmision.objects.values_list('solicitud_id').filter(status=True),estado__gte=1)
                    for solicitud in solicitudes:
                        historialbase = HistorialSolicitud.objects.filter(solicitud=solicitud).last()
                        historialbase.estado = estado
                        historialbase.observacion= observacion
                        historialbase.save()

                        if estado == 1 or estado == 2:
                            solicitud.estado=2
                        if estado == 3:
                            solicitud.estado=4
                        if estado == 4:
                            solicitud.estado=5
                        solicitud.save()

                        log(u'Respondió masivo a Solicitud en balcon: %s' % solicitud, request, "edit")

                        cuerpo = (observacion)
                        notificacion("Respuesta a solicitud %s en balcón de servicios" % solicitud.codigo,
                                     cuerpo, solicitud.solicitante, None, 'alu_solicitudbalcon?action=misolicitudes', solicitud.id,
                                     1, 'sga', Solicitud, request)
                        titulo = f"Solicitud en balcón de servicios ({solicitud.get_estado_display().capitalize()})"
                        cuerpo = f'Su solicitud en {str(historialbase.servicio).lower()} ha sido {solicitud.get_estado_display().capitalize()}'
                        lista_email = solicitud.solicitante.lista_emails()
                        # lista_email = ['jguachuns@unemi.edu.ec', ]
                        datos_email = {'sistema': request.session['nombresistema'],
                                       'fecha': hoy.date(),
                                       'hora': hoy.time(),
                                       'validacion': historialbase,
                                       'persona': solicitud.solicitante,
                                       'mensaje': cuerpo}
                        template = "emails/notificacion_balcon.html"
                        send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde. -- {}".format(ex)}, safe=False)

        if action == 'respondermasivototal':
            with transaction.atomic():
                try:
                    estado = int(request.POST['estado'])
                    estadoselect = int(request.POST['estadoselect'])
                    observacion = request.POST['observacion']

                    servicio = ProcesoServicio.objects.get(pk=int(request.POST['servicio']))
                    historiales = HistorialSolicitud.objects.values_list("solicitud_id",flat=True).filter(status=True,solicitud__estado=estadoselect,servicio=servicio, solicitud__status=True).distinct('solicitud_id')
                    solicitudes = Solicitud.objects.filter(status=True, id__in=historiales)

                    for solicitud in solicitudes:
                        solicitud.estado = estado
                        solicitud.save()
                        historialbase = HistorialSolicitud(solicitud=solicitud,
                                                           servicio=servicio,
                                                           asignaenvia=persona,
                                                           observacion=observacion,
                                                           estado=4)

                        historialbase.save()
                        log(u'Respondió masivo a Solicitud en balcon: %s' % solicitud, request, "edit")
                        cuerpo = (observacion)
                        notificacion("Respuesta a solicitud %s en balcón de servicios" % solicitud.codigo,
                                     cuerpo, solicitud.solicitante, None, 'alu_solicitudbalcon?action=misolicitudes', solicitud.id,
                                     1, 'sga', Solicitud, request)

                        titulo = f"Solicitud en balcón de servicios ({solicitud.get_estado_display().capitalize()})"
                        cuerpo = f'Su solicitud en {str(historialbase.servicio).lower()} fue cambiado de estado.'
                        lista_email = solicitud.solicitante.lista_emails()
                        # lista_email = ['jguachuns@unemi.edu.ec', ]
                        datos_email = {'sistema': request.session['nombresistema'],
                                       'fecha': hoy.date(),
                                       'hora': hoy.time(),
                                       'validacion': historialbase,
                                       'persona': solicitud.solicitante,
                                       'mensaje': cuerpo}
                        template = "emails/notificacion_balcon.html"
                        send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde. -- {}".format(ex)}, safe=False)

        if action == 'reasignarmasivo':
            try:
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    extension = newfile._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if newfile.size > 4194304:
                        return JsonResponse(
                            {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                        newfile._name = generar_nombre("cerrarsolicitud_", newfile._name)
                    else:
                        return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                asignadorecibe = Persona.objects.get(pk=int(request.POST['persona']))
                observacion = request.POST['observacion']
                lista = json.loads(request.POST['lista'])

                for elemento in lista:
                    filtro = Solicitud.objects.get(pk=int(elemento))
                    historialbase = HistorialSolicitud.objects.filter(solicitud=filtro).last()

                    nota = HistorialSolicitud(solicitud=filtro,
                                              asignaenvia=persona,
                                              servicio=historialbase.servicio,
                                              asignadorecibe=asignadorecibe,
                                              departamento=asignadorecibe.mi_departamento(),
                                              departamentoenvia=persona.mi_departamento(),
                                              observacion=observacion,
                                              estado=2)
                    if 'archivo' in request.FILES:
                        nota.archivo = newfile
                    nota.save(request)
                    filtro.estado = 3
                    filtro.agenteactual = asignadorecibe
                    filtro.save(request)
                    log(u'Cerro Solicitud en balcon: %s' % filtro, request, "add")
                    titulo = f"Reasignación de solicitud de {filtro.solicitante.nombre_completo_minus()} en balcón de servicios"
                    cuerpo = f'Se ha reasignado una solicitud de {filtro.solicitante.nombre_completo_minus()}'
                    notificacion(titulo, cuerpo, nota.asignadorecibe, None, 'adm_solicitudbalcon', filtro.id, 1, 'sga',
                                 Solicitud, request)
                    lista_email = nota.asignadorecibe.lista_emails()
                    datos_email = {'sistema': request.session['nombresistema'],
                                   'fecha': hoy.date(),
                                   'hora': hoy.time(),
                                   'historial_s': nota,
                                   'persona': nota.asignadorecibe,
                                   'mensaje': cuerpo}
                    template = "emails/notificacion_balcon.html"
                    send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        if action == 'reasignarmasivo2':
            try:
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    extension = newfile._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if newfile.size > 4194304:
                        return JsonResponse(
                            {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                        newfile._name = generar_nombre("cerrarsolicitud_", newfile._name)
                    else:
                        return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                asignadorecibe = Persona.objects.get(pk=int(request.POST['persona']))
                observacion = request.POST['observacion']
                lista = json.loads(request.POST['lista'])
                cant = 0

                for elemento in lista:
                    cant += 1
                    filtro = Solicitud.objects.get(pk=int(elemento))
                    historialbase = HistorialSolicitud.objects.filter(solicitud=filtro).last()
                    nota = HistorialSolicitud(solicitud=filtro,
                                              asignaenvia=persona,
                                              servicio=historialbase.servicio,
                                              asignadorecibe=asignadorecibe,
                                              departamento=asignadorecibe.mi_departamento(),
                                              departamentoenvia=persona.mi_departamento(),
                                              observacion=observacion,
                                              estado=2)
                    if 'archivo' in request.FILES:
                        nota.archivo = newfile
                    nota.save(request)
                    filtro.estado = 3
                    filtro.agenteactual = asignadorecibe
                    filtro.save(request)
                    log(u'Cerro Solicitud en balcon: %s' % filtro, request, "add")

                titulo = f"Reasignación varias solicitud en balcón de servicios"
                mensaje = f'Se ha reasignado en total de: {cant} Solicitudes'
                notificacion(titulo, mensaje, nota.asignadorecibe, None, 'adm_solicitudbalcon', filtro.id, 1, 'sga',Solicitud, request)
                lista_email = asignadorecibe.lista_emails()
                datos_email = {'sistema': request.session['nombresistema'],
                               'fecha': hoy.date(),
                               'hora': hoy.time(),
                               'historial_s': nota,
                               'persona': asignadorecibe,
                               'mensaje': mensaje}
                template = "emails/reasignar_masivo_balcon.html"
                send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        if action == 'gestionarmasivo':
            try:
                observacion = request.POST['observacion']
                lista = json.loads(request.POST['lista'])
                for elemento in lista:
                    estado = int(request.POST['estado'])
                    filtro = Solicitud.objects.get(pk=int(elemento))
                    historialbase = HistorialSolicitud.objects.filter(solicitud=filtro).last()
                    filtro.estado = estado
                    filtro.save(request)
                    estado = 4

                    if filtro.estado == 3:
                        estado = 2
                    elif filtro.estado == 4:
                        estado = 3
                    elif filtro.estado == 1:
                        estado = 1

                    nota = HistorialSolicitud(solicitud=filtro,
                                              asignaenvia=persona,
                                              observacion=observacion,
                                              servicio=historialbase.servicio,
                                              asignadorecibe=historialbase.asignadorecibe,
                                              departamentoenvia=historialbase.departamentoenvia,
                                              departamento=historialbase.departamento,
                                              estado=estado)
                    nota.save(request)

                    filtro.agenteactual = historialbase.asignadorecibe
                    filtro.save(request)

                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        extension = newfile._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if newfile.size > 4194304:
                            return JsonResponse(
                                {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                        if exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                            newfile._name = generar_nombre("cerrarsolicitud_", newfile._name)
                        else:
                            return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                        nota.archivo = newfile
                        nota.save(request)
                    log(u'gestionó Solicitud en balcon: %s' % filtro, request, "add")

                    titulo = f"Solicitud en balcón de servicios ({filtro.get_estado_display().capitalize()})"
                    cuerpo = ('Su solicitud ha sido procesada. \n Motivo: %s' % nota.observacion)
                    notificacion(
                        'Estimado(a) %s su solicitud %s requiere atención ' % (filtro.solicitante, filtro.get_codigo()),
                        cuerpo, filtro.solicitante, None, 'alu_solicitudbalcon?action=misolicitudes', filtro.id,
                        1, 'sga', Solicitud, request)

                    cuerpo = f'Su solicitud en {str(nota.servicio).lower()} ha sido procesada'
                    lista_email = filtro.solicitante.lista_emails()
                    datos_email = {'sistema': request.session['nombresistema'],
                                   'fecha': hoy.date(),
                                   'hora': hoy.time(),
                                   'validacion': nota,
                                   'persona': filtro.solicitante,
                                   'mensaje': cuerpo}
                    template = "emails/notificacion_balcon.html"
                    send_html_mail(titulo, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[0][1])
                return JsonResponse({"result": "ok"})


            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde. -- {}".format(ex)}, safe=False)

        return JsonResponse({"result": True, "mensaje": u"Solicitud Incorrecta."})


    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'buscarpersona3':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    query = Persona.objects.filter(status=True)
                    if len(s) == 1:
                        per = query.filter((Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(apellido2__icontains=q) | Q(cedula__contains=q))).distinct()[:15]
                    elif len(s) == 2:
                        per = query.filter((Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) |
                                           (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1])) |
                                           (Q(nombres__icontains=s[0]) & Q(apellido1__contains=s[1]))).distinct()[:15]
                    else:
                        per = query.filter((Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) &
                                            Q(apellido2__contains=s[2])) | (Q(nombres__contains=s[0]) &
                                            Q(nombres__contains=s[1]) & Q(apellido1__contains=s[2]))).distinct()[:15]
                    data = {"result": "ok",
                            "results": [{"id": x.id, "name": str(x.nombre_completo())}
                                        for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'addsolicitudmodal':
                try:
                    data['tipo'] = id = request.GET['id']
                    #data['proceso'] = request.GET['proceso']
                    data['servicio'] = servicio = request.GET['servicio']
                    data['proceso'] = servicio = ProcesoServicio.objects.get(pk=servicio)
                    data['requisitos'] = requisitos = RequisitosConfiguracion.objects.filter(status=True, servicio=servicio)
                    data['subesolicitud'] = servicio.proceso.subesolicitud
                    # proceso = Proceso.objects.get(pk= int(request.GET['proceso']))
                    #if proceso.subesolicitud()
                    data['form2'] = SolicitudManualBalconForm()
                    template = get_template("adm_solicitudbalcon/addsolicitud.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'reasignar':
                try:
                    data['title'] = u'Reasignar Solicitud'
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = Solicitud.objects.get(pk=int(id))
                    data['form2'] = SolicitudBalconReasignarForm()
                    template = get_template("adm_solicitudbalcon/reasignar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'reasignarmasivo':
                try:
                    data['title'] = u'Reasignar Masivo'
                    template = get_template("adm_solicitudbalcon/reasignarmasivo.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

            if action == 'reasignarmasivo2':
                try:
                    data['title'] = u'Reasignar Masivo'
                    template = get_template("adm_solicitudbalcon/reasignarmasivo.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

            if action == 'gestionarmasivo':
                try:
                    data['title'] = u'Responder Masivo'
                    data['estados'] = ESTADO_SOLICITUD_BALCON
                    template = get_template("adm_solicitudbalcon/gestionarmasivo.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

            if action == 'reasignarinterno':
                try:
                    data['title'] = u'Reasignar Solicitud'
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = Solicitud.objects.get(pk=int(id))
                    data['form2'] = SolicitudBalconReasignarInternoForm()
                    data['gdep'] = persona.mi_departamento()
                    template = get_template("adm_solicitudbalcon/reasignarinterno.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'viewprocesos':
                try:
                    data['title'] = u'Seleccionar Proceso'
                    data['filtro'] = filtro =  Proceso.objects.filter(status=True, activoadmin=True)
                    template = get_template("adm_solicitudbalcon/verprocesos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'selsub':
                try:
                    pk = int(request.GET['pk'])
                    data['proceso'] = procesos = Proceso.objects.get(pk=pk, status=True)
                    idslist = ProcesoServicio.objects.filter(proceso=procesos,status=True).values_list('id', flat=True)
                    data['informacion'] = informacion = Informacion.objects.filter(mostrar=True,tipo=2,status=True, servicio_id__in=idslist)
                    template = get_template('adm_solicitudbalcon/verinformacion.html')
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content,
                                         'titulo': 'SELECCIONAR SERVICIO'})
                except Exception as ex:
                    return JsonResponse({"result": False})

            # if action == 'enviar':
            #     try:
            #         data['title'] = u'Enviar Solicitud'
            #         data['id'] = id = request.GET['id']
            #         data['filtro'] = filtro = Solicitud.objects.get(pk=int(id))
            #         data['form2'] = SolicitudBalconReasignarForm()
            #         template = get_template("adm_solicitudbalcon/reasignar.html")
            #         return JsonResponse({"result": True, 'data': template.render(data)})
            #     except Exception as ex:
            #         pass

            if action == 'addagente':
                try:
                    data['title'] = u'Asignar Agente'
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = Solicitud.objects.get(pk=int(id))
                    data['form2'] = SolicitudBalconReasignarForm()
                    template = get_template("adm_solicitudbalcon/reasignar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addprocesosol':
                try:
                    data['title'] = u'Adicionar proceso'
                    data['id'] = request.GET['id']
                    form = AsignarServicioForm()
                    form.fields['servicio'].queryset = ProcesoServicio.objects.none()
                    data['form2'] = form
                    template = get_template("adm_solicitudbalcon/procesomodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'cambiaprocesosol':
                try:
                    data['title'] = u'Cambiar proceso'
                    data['id'] = request.GET['id']
                    form = AsignarServicioForm()
                    form.fields['servicio'].queryset = ProcesoServicio.objects.none()
                    data['form2'] = form
                    template = get_template("adm_solicitudbalcon/procesomodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addrespuestarapida':
                try:
                    data['title'] = u'Adicionar Respuesta'
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = Solicitud.objects.get(pk=int(id))
                    data['detalle'] = HistorialSolicitud.objects.filter(status=True, solicitud=filtro).order_by('pk')
                    data['form2'] = SolicitudBalconRespuestaRapidaForm()
                    template = get_template("adm_solicitudbalcon/addrespuesta.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'resolver':
                try:
                    data['title'] = u'Resolver Solicitud'
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = Solicitud.objects.get(pk=int(id))
                    data['form2'] = SolicitudBalconResolverForm()
                    template = get_template("adm_solicitudbalcon/resolver.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': f'{ex}'})

            if action == 'rechazar':
                try:
                    data['title'] = u'Rechazar Solicitud'
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = Solicitud.objects.get(pk=int(id))
                    data['form2'] = SolicitudBalconRespuestaRechazarForm()
                    template = get_template("adm_solicitudbalcon/rechazar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'gestionar':
                try:
                    data['title'] = u'Gestionar Solicitud'
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = Solicitud.objects.get(pk=int(id))
                    data['form2'] = SolicitudBalconGestionarForm()
                    template = get_template("adm_solicitudbalcon/resolver.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'cerrar':
                try:
                    data['title'] = u'Cerrar Solicitud'
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = Solicitud.objects.get(pk=int(id))
                    data['form2'] = SolicitudBalconCerrarForm()
                    template = get_template("adm_solicitudbalcon/cerrar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'respondermasivo':
                try:
                    data['title'] = u'Responder masivo admisión'
                    data['estados'] = ESTADO_HISTORIAL_SOLICITUD_BALCON
                    data['opciones'] = TestSilaboSemanalAdmision.objects.filter(id__in=RegistroNovedadesExternoAdmision.objects.values_list('test_id').filter(status=True).order_by( 'test__titulo').distinct('test__titulo'))
                    data['materias'] = Asignatura.objects.filter(id__in=RegistroNovedadesExternoAdmision.objects.values_list('materiaasignada__materia__asignatura_id').filter(status=True).order_by('materiaasignada__materia__asignatura').distinct())
                    template = get_template("adm_solicitudbalcon/segmentomasivo.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

            if action == 'respondermasivototal':
                try:
                    data['title'] = u'Responder Masivo'
                    data['estados'] = ESTADO_SOLICITUD_BALCON
                    data['opciones'] = ProcesoServicio.objects.filter(status=True).order_by('proceso_id')
                    template = get_template("adm_solicitudbalcon/segmentomasivototal.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

            if action == 'verproceso':
                try:
                    data['title'] = u'Ver Historial'
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = Solicitud.objects.get(pk=int(id))
                    data['detalle'] = HistorialSolicitud.objects.filter(status=True, solicitud=filtro).order_by('pk')
                    template = get_template("adm_solicitudbalcon/verhistorial.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'razonconsultalist':
                id = (request.GET['id']).replace(",", "")
                proceso = Proceso.objects.get(pk=int(id))
                filtro = ProcesoServicio.objects.filter(proceso=proceso,status=True)
                if 'search' in request.GET:
                    search = request.GET['search']
                    filtro = filtro.filter(servicio__nombre__icontains=search).order_by('-id')
                resp = [{'id': cr.pk, 'text': cr.servicio.nombre} for cr in filtro]
                return HttpResponse(json.dumps({'state': True, 'result': resp}))

            if action == 'buscarpersona':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    dep = Departamento.objects.get(status=True, pk=int(request.GET['gdep']))
                    if len(s) == 1:
                        per = dep.integrantes.filter((Q(distributivopersona__isnull=False) | Q(profesor__isnull=False)),
                                                     (Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(
                                                         apellido2__icontains=q) | Q(cedula__contains=q)),
                                                     Q(status=True)).distinct()[:15]
                    elif len(s) == 2:
                        per = dep.integrantes.filter((Q(distributivopersona__isnull=False) | Q(profesor__isnull=False)),
                                                     (Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) | (
                                                             Q(nombres__icontains=s[0]) & Q(
                                                         nombres__icontains=s[1])) | (
                                                             Q(nombres__icontains=s[0]) & Q(
                                                         apellido1__contains=s[1]))).filter(status=True).distinct()[
                              :15]
                    else:
                        per = dep.integrantes.filter((Q(distributivopersona__isnull=False) | Q(profesor__isnull=False)),
                                                     (Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(
                                                         apellido2__contains=s[2])) | (Q(nombres__contains=s[0]) & Q(
                                                         nombres__contains=s[1]) & Q(apellido1__contains=s[2]))).filter(
                            status=True).distinct()[:15]

                    data = {"result": "ok",
                            "results": [{"id": x.id, "name": str(x.nombre_completo())}
                                        for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'buscarpersonad':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    dep = Departamento.objects.get(status=True, pk=int(request.GET['gdep']))
                    if len(s) == 1:
                        per = dep.integrantes.filter((Q(distributivopersona__isnull=False) | Q(profesor__isnull=False)),
                                                     (Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(
                                                         apellido2__icontains=q) | Q(cedula__contains=q)),
                                                     Q(status=True)).distinct()[:15]
                    elif len(s) == 2:
                        per = dep.integrantes.filter((Q(distributivopersona__isnull=False) | Q(profesor__isnull=False)),
                                                     (Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) | (
                                                             Q(nombres__icontains=s[0]) & Q(
                                                         nombres__icontains=s[1])) | (
                                                             Q(nombres__icontains=s[0]) & Q(
                                                         apellido1__contains=s[1]))).filter(status=True).distinct()[
                              :15]
                    else:
                        per = dep.integrantes.filter((Q(distributivopersona__isnull=False) | Q(profesor__isnull=False)),
                                                     (Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(
                                                         apellido2__contains=s[2])) | (Q(nombres__contains=s[0]) & Q(
                                                         nombres__contains=s[1]) & Q(apellido1__contains=s[2]))).filter(
                            status=True).distinct()[:15]

                    data = {"result": "ok",
                            "results": [{"id": x.id, "name": str(x.nombre_completo())}
                                        for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'descargasolicitudes':
                try:
                    solicitudes = Solicitud.objects.filter(status=True)

                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Listado')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Lista de solicitudes ' + random.randint(1,
                                                                                                    10000).__str__() + '.xls'
                    columns = [
                        (u"N", 3000),
                        (u"NOMBRE SOLICITANTE", 12000),
                        (u"CEDULA", 4500),
                        (u"CARRERA", 12000),
                        (u"SERVICIO", 10000),
                        (u"TIPO DE SOLICITUD", 12000),
                        (u"ESTADO DE SOLICITUD", 12000),
                        (u"FECHA", 4500),
                        (u"AGENTE ASIGNADO", 10000),
                        (u"DIRECCIÓN ASIGNADA", 10000),
                        (u"FECHA ASIGNACIÓN A DIRECCIÓN", 10000)
                    ]

                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    row_num = 2
                    cont=0
                    for sol in solicitudes:
                        cont+=1
                        historial = sol.ver_servicio()
                        fecha = str(sol.fecha_creacion.date())
                        solicitante = str(sol.solicitante.nombre_completo_inverso())
                        carrera = str(sol.perfil.inscripcion.carrera) if sol.perfil.inscripcion else ''
                        cedula = sol.solicitante.identificacion()
                        asignado = historial.departamento
                        fecha_asignación = historial.fecha_creacion
                        servicio = str(historial)
                        estado = str(sol.get_estado())
                        tipo = str(sol.get_tiposolicitud())
                        agente = str(sol.agente.persona.nombre_completo_inverso())

                        ws.write(row_num, 0, cont, font_style2)
                        ws.write(row_num, 1, solicitante, font_style2)
                        ws.write(row_num, 2, cedula, font_style2)
                        ws.write(row_num, 3, carrera, font_style2)
                        ws.write(row_num, 4, servicio, font_style2)
                        ws.write(row_num, 5, tipo, font_style2)
                        ws.write(row_num, 6, estado, font_style2)
                        ws.write(row_num, 7, fecha, font_style2)
                        ws.write(row_num, 8, agente, font_style2)
                        ws.write(row_num, 9, asignado, font_style2)
                        ws.write(row_num, 10, fecha_asignación, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    print(ex)


            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Solicitudes del balcon'
                direccion, idagente, desde, hasta, tipo, estados, \
                search, responsable, filtro,  filtro2, url_vars, devueltos,ordentemporal, proceso, coordinacion, externo = request.GET.get('direccion', ''), request.GET.get('agente', ''), \
                                                      request.GET.get('desde', ''), request.GET.get('hasta',''), request.GET.get('tipo', ''), \
                                                      request.GET.get('estados', ''), request.GET.get('s', ''), request.GET.get('responsable', ''), \
                                                      Q(status=True), Q(status=True), '', request.GET.get('devueltos', ''), request.GET.get('ordentemporal', ''),request.GET.get('proceso', ''), \
                                                      request.GET.get('coordinacion', ''),request.GET.get('externo', '')

                if desde:
                    data['desde'] = desde
                    url_vars += "&desde={}".format(desde)
                    filtro = filtro & Q(fecha_creacion__gte=desde)

                if hasta:
                    data['hasta'] = hasta
                    url_vars += "&hasta={}".format(hasta)
                    fechaconv = convertir_fecha_invertida(hasta)
                    hasta = fechaconv + + timedelta(days=1)
                    filtro = filtro & Q(fecha_creacion__lte=hasta)

                if tipo:
                    data['tipo'] = int(tipo)
                    url_vars += "&tipo={}".format(tipo)
                    filtro = filtro & Q(tipo=int(tipo))

                if idagente:
                    data['idagente'] = int(idagente)
                    url_vars += "&agente={}".format(idagente)
                    filtro = filtro & Q(agente_id=int(idagente))

                if direccion:
                    data['direccionid'] = int(direccion)
                    url_vars += "&direccion={}".format(direccion)
                    historialdireccion = HistorialSolicitud.objects.filter(status=True, departamento_id=int(direccion)).values_list('solicitud__id', flat=True)
                    filtro = filtro & Q(id__in=list(historialdireccion))

                if estados:
                    data['estados'] = int(estados)
                    url_vars += "&estados={}".format(estados)
                    filtro = filtro & Q(estado=int(estados))

                if search:
                    s = search.split(' ')
                    if len(s) == 1:
                        filtro = filtro & (Q(codigo__unaccent__icontains=search) | Q(solicitante__cedula__icontains=search) |
                                           Q(solicitante__apellido1__unaccent__icontains=search) | Q(solicitante__apellido2__unaccent__icontains=search)
                                           |Q (descripcion__unaccent__icontains=search))
                    if len(s) >= 2:
                        filtro = filtro & (Q(solicitante__apellido1__unaccent__icontains=s[0]) & Q(solicitante__apellido2__unaccent__icontains=s[1])
                                           | Q(solicitante__nombres__unaccent__icontains=search) |Q (descripcion__unaccent__icontains=search))

                    data["search"] = search
                    url_vars += '&s=' + search

                if responsable:
                    s1 = responsable.split(' ')
                    if len(s1) == 1:
                        filtro = filtro & (Q(agenteactual__cedula__icontains=responsable) |
                                             Q(agenteactual__apellido1__unaccent__icontains=responsable) |
                                             Q(agenteactual__apellido2__unaccent__icontains=responsable))
                    if len(s1) >= 2:
                        filtro = filtro & (Q(agenteactual__apellido1__unaccent__icontains=s1[0]) &
                                             Q(agenteactual__apellido2__unaccent__icontains=s1[1]))

                    data["responsable"] = responsable
                    url_vars += f'&responsable={responsable}'

                listado = Solicitud.objects.filter(filtro).order_by('-id')

                if proceso:
                    data['procesoid'] = int(proceso)
                    url_vars += "&proceso={}".format(proceso)
                    historialsol = HistorialSolicitud.objects.filter(status=True,servicio__servicio_id=int(proceso)).values_list('solicitud__id', flat=True)
                    listado = listado.filter(Q(id__in=list(historialsol)))

                if coordinacion:
                    data['coordinacionid'] = int(coordinacion)
                    url_vars += "&coordinaicon={}".format(coordinacion)
                    coordi = Solicitud.objects.filter(status=True, perfil__inscripcion__carrera__coordinacion__id=coordinacion).values_list('solicitante_id',flat=True)
                    listado = listado.filter(solicitante_id__in=coordi)

                if externo:
                    data['externo'] = externo
                    url_vars += f"&externo={externo}"
                    if externo == '1':
                        ext = Solicitud.objects.filter(status=True, perfil__externo__isnull=False).values_list('perfil_id', flat=True)
                        listado = listado.filter(perfil_id__in=ext)
                    elif externo is None:
                        ext = Solicitud.objects.filter(status=True, perfil__externo__isnull=True).values_list('perfil_id', flat=True)
                        listado = listado.filter(perfil_id__in=ext)

                if ordentemporal:
                    data['orden'] = ordentemporal
                    url_vars += f"&ordentemporal={ordentemporal}"
                    if ordentemporal == 'masreciente':
                        listado = listado.order_by('-fecha_creacion')
                    elif ordentemporal == 'masantiguo':
                        listado = listado.order_by('fecha_creacion')

                agenteid = None
                agente=None
                if Agente.objects.filter(persona=persona).exists():
                    data['agente']= agente = Agente.objects.get(persona=persona)
                    agenteid = agente.pk
                if not persona.usuario.is_superuser:
                    if not agente or not agente.admin:
                            # if not agente.admin:
                            #     listado = Solicitud.objects.filter(filtro).filter(agente=agente).order_by('-id')
                        listaasignados = HistorialSolicitud.objects.filter(status=True, solicitud_id__in=listado.values_list('id',flat=True), asignadorecibe=persona).values_list('solicitud__id',flat=True)
                            # pks= [ x.id for x in listado if x.ver_servicio().asignadorecibe == persona]
                            #listado = Solicitud.objects.filter(pk__in=HistorialSolicitud.objects.values_list('solicitud').filter(departamento=persona.mi_departamento())).distinct()
                        listado = listado.filter(Q(pk__in=listaasignados) | Q(agente_id=agenteid)).distinct()
                            #listado = Solicitud.objects.filter().distinct()

                if devueltos:
                    data['devueltos'] = True
                    url_vars += "&devueltos=on"
                    idsdevueltos = [l.id for l in listado if l.devuelto()]
                    # for l in listado:
                    #     if l.devuelto():
                    #         idsdevueltos.append(l.id)
                    listado = listado.filter(id__in=idsdevueltos)

                if 'export_to_excel' in request.GET:
                    try:
                        __author__ = 'Unemi'
                        style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                        style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                          num_format_str='#,##0.00')
                        style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                        title = easyxf(
                            'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                        style1 = easyxf(num_format_str='D-MMM-YY')
                        fuentecabecera = easyxf(
                            'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                        font_style = XFStyle()
                        font_style.font.bold = True
                        font_style2 = XFStyle()
                        font_style2.font.bold = False
                        wb = Workbook(encoding='utf-8')
                        ws = wb.add_sheet('Listado')
                        ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                        response = HttpResponse(content_type="application/ms-excel")
                        response['Content-Disposition'] = 'attachment; filename=Lista de solicitudes ' + random.randint(1,
                                                                                                                        10000).__str__() + '.xls'
                        columns = [
                            (u"N", 3000),
                            (u"NOMBRE SOLICITANTE", 12000),
                            (u"CEDULA", 4500),
                            (u"CARRERA", 12000),
                            (u"SERVICIO", 10000),
                            (u"TIPO DE SOLICITUD", 12000),
                            (u"ESTADO DE SOLICITUD", 12000),
                            (u"FECHA", 4500),
                            (u"AGENTE ASIGNADO", 10000),
                            (u"DIRECCIÓN ASIGNADA", 10000),
                            (u"FECHA ASIGNACIÓN A DIRECCIÓN", 10000),
                            (u"UBICACIÓN INICIAL", 10000),
                            (u"UBICACIÓN ACTUAL DEL PROCESO", 10000),
                            (u"RESPONSABLE", 10000)
                        ]
                        row_num = 1
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                            ws.col(col_num).width = columns[col_num][1]
                        date_format = xlwt.XFStyle()
                        date_format.num_format_str = 'yyyy-mm-dd'
                        date_formatreverse = xlwt.XFStyle()
                        date_formatreverse.num_format_str = 'dd/mm/yyyy'
                        row_num = 2
                        cont = 0

                        for sol in listado:
                            cont += 1
                            qsbasehistorial = sol.historialsolicitud_set.filter(status=True, departamento__isnull=False).order_by('id')
                            historial = qsbasehistorial.last()
                            fecha = str(sol.fecha_creacion.date())
                            solicitante = str(sol.solicitante.nombre_completo_inverso())
                            carrera = str(sol.perfil.inscripcion.carrera) if sol.perfil.inscripcion else ''
                            cedula = sol.solicitante.identificacion()
                            servicio = str(sol.ver_servicio())
                            estado = str(sol.get_estado())
                            tipo = str(sol.get_tiposolicitud())
                            agente = str(sol.agente.persona.nombre_completo_inverso()) if sol.agente else ''
                            if historial:
                                fecha_direccion = str(historial.fecha_creacion.date()) if historial else ''
                                direccion = historial.departamento.__str__() if historial.departamento else ''
                            else:
                                fecha_direccion = ''
                                direccion = ''
                            ws.write(row_num, 0, cont, font_style2)
                            ws.write(row_num, 1, solicitante, font_style2)
                            ws.write(row_num, 2, cedula, font_style2)
                            ws.write(row_num, 3, carrera, font_style2)
                            ws.write(row_num, 4, servicio, font_style2)
                            ws.write(row_num, 5, tipo, font_style2)
                            ws.write(row_num, 6, estado, font_style2)
                            ws.write(row_num, 7, fecha, font_style2)
                            ws.write(row_num, 8, agente, font_style2)
                            ws.write(row_num, 9, direccion, font_style2)
                            ws.write(row_num, 10, fecha_direccion, font_style2)
                            inicio = qsbasehistorial.first()
                            actual = qsbasehistorial.last()
                            if inicio:
                                ws.write(row_num, 11, inicio.departamento.__str__() if inicio.departamento else '', font_style2)
                            else:
                                ws.write(row_num, 11, '', font_style2)
                            if actual:
                                ws.write(row_num, 12, actual.departamento.__str__() if actual.departamento else '', font_style2)
                                ws.write(row_num, 13, actual.asignadorecibe.nombre_completo_minus() if actual.asignadorecibe else '', font_style2)

                            else:
                                ws.write(row_num, 12, '', font_style2)

                            row_num += 1
                        wb.save(response)
                        return response
                    except Exception as ex:
                        return JsonResponse({'ex': str(ex)})

                paging = MiPaginador(listado, 15)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session:
                        paginasesion = int(request.session['paginador'])
                    if 'page' in request.GET:
                        p = int(request.GET['page'])
                    else:
                        p = paginasesion
                    try:
                        page = paging.page(p)
                    except:
                        p = 1
                    page = paging.page(p)
                except:
                    page = paging.page(p)
                request.session['paginador'] = p
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data["url_vars"] = url_vars
                data['solicitudes'] = page.object_list
                data['email_domain'] = EMAIL_DOMAIN
                data['tiposol'] = TIPO_SOLICITUD_BALCON
                data['estadossol'] = ESTADO_SOLICITUD_BALCON
                data['totalcount'] = listado.count()
                data['listagentes'] = Agente.objects.filter(status=True).order_by('persona')
                data['listproceso'] = Servicio.objects.filter(status=True).order_by('nombre')
                data['listcoodinacion'] = Coordinacion.objects.filter(Q(status=True) & Q(id__in=[1,2,3,4,5,9]))
                data['listdirecciones'] = Departamento.objects.filter(status=True).order_by('nombre')
                return render(request, 'adm_solicitudbalcon/view.html', data)
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                return JsonResponse({'ex': f"{ex}, Linea {sys.exc_info()[-1].tb_lineno}"})