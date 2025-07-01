# -*- coding: latin-1 -*-
import sys
import os
import requests
from statistics import mode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.template import Context
from django.db import transaction, connection
from datetime import datetime, timedelta
from django.db.models import Q, Count, F, Min, Max, CharField, Value, DateField
from django.template.loader import get_template
from django.views.decorators.csrf import csrf_exempt

from decorators import secure_module, last_access
from inno.funciones import haber_aprobado_modulos_computacion, haber_aprobado_modulos_ingles, secuencia_evidencia
from inno.models import SecuenciaEvidenciaSalud, ROL_ACTIVIDAD
from sagest.models import DistributivoPersona
from django.db.models.functions import TruncWeek, Concat, Cast, TruncDate
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import PracticasPreprofesionalesInscripcionSolicitarForm, \
    EvidenciaPracticasForm, EvidenciaPracticasNormalForm, RetiroPracticasForm, CargarAdjuntoPracticaForm, \
    InquietudConsultaEstudianteForm, EvidenciaHomologacionForm, ReemplazarDocumentoHomologacionForm
from sga.funciones import generar_nombre, log, MiPaginador, notificacion, remover_caracteres_especiales_unicode
from sga.models import PracticasPreprofesionalesInscripcion, EvidenciaPracticasProfesionales, \
    DetalleEvidenciasPracticasPro, CUENTAS_CORREOS, OfertasPracticas, ItinerariosMalla, \
    AperturaPracticaPreProfesional, FormatoPracticaPreProfesional, ClaseActividad, Turno, \
    ArchivoGeneralPracticaPreProfesionales, PeriodoEvidenciaPracticaProfesionales, \
    PlanPracticaPreProfesional, ProgramaPracticaPreProfesional, CartaVinculacionPracticasPreprofesionales, \
    InquietudPracticasPreprofesionales, ConfiguracionEvidenciaHomologacionPractica, \
    DetalleEvidenciaHomologacionPractica, EvidenciaHomologacionPractica, PreInscripcionPracticasPP, \
    DetallePreInscripcionPracticasPP, EstudiantesAgendaPracticasTutoria, PracticasTutoria, CarreraHomologacion, \
    CarreraHomologacionRequisitos, SolicitudHomologacionPracticas, DocumentosSolicitudHomologacionPracticas, \
    MESES_CHOICES, AgendaPracticasTutoria, HistorialDocumentosSolicitudHomologacionPracticas, DetalleCartaInscripcion

from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt_alu, encrypt
from django.forms import  model_to_dict
from settings import DEBUG, SITE_STORAGE
from sga.funcionesxhtml2pdf import conviert_html_to_pdf_name, download_html_to_pdf, html_to_pdfsave_evienciassalud


@csrf_exempt
@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    data['inscripcionpersona'] = inscripcion = perfilprincipal.inscripcion
    dominio_sistema = 'https://sga.unemi.edu.ec'
    if DEBUG:
        dominio_sistema = 'http://localhost:8000'
    data["DOMINIO_DEL_SISTEMA"] = dominio_sistema
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'confirmacionasistencia':
            try:
                id = int(request.POST['id'])
                value = request.POST['value']
                filtro = EstudiantesAgendaPracticasTutoria.objects.get(pk=id)
                filtro.estado_confirmacion = value
                filtro.save(request)
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deletesolicitudhomologacion':
            try:
                with transaction.atomic():
                    instancia = SolicitudHomologacionPracticas.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Solicitud de Homologación: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'add':
            try:
                with transaction.atomic():
                    id = request.POST['id']
                    periodohomologacion = AperturaPracticaPreProfesional.objects.get(pk=id)
                    f = PracticasPreprofesionalesInscripcionSolicitarForm(request.POST)
                    if f.is_valid():

                        # if f.cleaned_data['numerohora'] < f.cleaned_data['itinerario'].horas_practicas:
                        #     transaction.set_rollback(True)
                        #     return JsonResponse({"result": True, "mensaje": "Número de horas a homologar ({}h) es menor a las horas requeridas en el itinerario ({}h).".format(f.cleaned_data['numerohora'], f.cleaned_data['itinerario'].horas_practicas)},  safe=False)

                        if SolicitudHomologacionPracticas.objects.filter(apertura=periodohomologacion, status=True, inscripcion=inscripcion, itinerario=f.cleaned_data['itinerario'], estados__in=[0,1]).exists():
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Ya existe una solicitud de homologación con este itinerario."},  safe=False)

                        totalsubidos = 0
                        documentos_requeridos = CarreraHomologacionRequisitos.objects.filter(status=True, carrera__apertura=periodohomologacion, itinerario=f.cleaned_data['itinerario'], tipo= f.cleaned_data['tipotrabajo'])
                        if not documentos_requeridos.exists():
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Debe subir requisitos de homologación para continuar."},  safe=False)

                        for dr in documentos_requeridos:
                            if 'doc_{}'.format(dr.documento.nombre_input()) in request.FILES:
                                totalsubidos += 1

                        if not totalsubidos == documentos_requeridos.count():
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Debe subir todos los requisitos."},  safe=False)

                        solicitud = SolicitudHomologacionPracticas(apertura=periodohomologacion,
                                                                   inscripcion=inscripcion,
                                                                   itinerario=f.cleaned_data['itinerario'],
                                                                   tipotrabajo=f.cleaned_data['tipotrabajo'],
                                                                   numerohora=f.cleaned_data['numerohora'],
                                                                   otraempresaempleadora=f.cleaned_data['otraempresaempleadora'],
                                                                   departamento=f.cleaned_data['departamento'],
                                                                   tipoinstitucion=f.cleaned_data['tipoinstitucion'],
                                                                   sectoreconomico=f.cleaned_data['sectoreconomico'],
                                                                   tipo=1,
                                                                   tiposolicitud=3)
                        solicitud.save(request)

                        for dr in documentos_requeridos:
                            if 'doc_{}'.format(dr.documento.nombre_input()) in request.FILES:
                                newfile = request.FILES['doc_{}'.format(dr.documento.nombre_input())]
                                extension = newfile._name.split('.')
                                tam = len(extension)
                                exte = extension[tam - 1]
                                if newfile.size > 10485760:
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                                if not exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                                docrequerido = DocumentosSolicitudHomologacionPracticas(solicitud=solicitud, documento=dr)
                                nombre_persona = remover_caracteres_especiales_unicode(persona.apellido1).lower().replace(' ','_')
                                newfile._name = generar_nombre("{}__{}".format(nombre_persona, dr.documento.nombre_input()), newfile._name)
                                docrequerido.archivo = newfile
                                docrequerido.save(request)

                        log(u'Adiciono Solicitud de Homologación: %s' % solicitud, request, "add")
                        fechavalidacion = "{} hasta {}".format(str(periodohomologacion.fechainicioverrequisitos), str(periodohomologacion.fechacierreverrequisitos))
                        return JsonResponse({"result": False, 'mensaje': 'Solicitud registrada con éxito, sus datos serán validados desde {}.'.format(fechavalidacion), 'modalsuccess': True, 'to': '{}?action=verproceso&id={}'.format(request.path, encrypt(solicitud.pk))}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'reemplazardocumento':
            try:
                postar = DocumentosSolicitudHomologacionPracticas.objects.get(id=int(request.POST['id']))
                f = ReemplazarDocumentoHomologacionForm(request.POST)
                if f.is_valid():
                    newfile = request.FILES['archivo']
                    extension = newfile._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if newfile.size > 10485760:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                    if not exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg', 'PDF']:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                    nombre_persona = remover_caracteres_especiales_unicode(persona.apellido1).lower().replace(' ', '_')
                    newfile._name = generar_nombre("{}__{}".format(nombre_persona, postar.documento.documento.nombre_input()),
                                                   newfile._name)
                    postar.archivo = newfile
                    postar.corregido=True
                    postar.save(request)

                    historial=HistorialDocumentosSolicitudHomologacionPracticas.objects.filter(documento=postar.id).order_by('fecha').last()
                    historial.fecha_correccion=postar.fecha_modificacion
                    historial.save(request)

                    if  not DocumentosSolicitudHomologacionPracticas.objects.filter(solicitud=postar.solicitud_id, corregido=False).exists():
                        soli = SolicitudHomologacionPracticas.objects.get(id=postar.solicitud_id)
                        asunto = soli.inscripcion.persona.apellido1 + " " + soli.inscripcion.persona.apellido2 + " " + soli.inscripcion.persona.nombres + " SOLICITA REVISION DE DOCUMENTOS"
                        para = soli.persona_vinculacion
                        notificacion(asunto, soli.observacion, para, None,
                                     '/alu_practicaspreprofesionalesinscripcion?action=solicitantes&id={}&search={}'.format(
                                         soli.apertura_id, soli.inscripcion.persona.cedula),
                                     soli.pk, 1, 'sga', SolicitudHomologacionPracticas, request)

                    log(u'Documento Homologación %s estudiante: %s' % (postar, postar.solicitud.inscripcion), request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al obtener los datos. {}".format(ex)})

        if action == 'add1':
            try:
                f = PracticasPreprofesionalesInscripcionSolicitarForm(request.POST, request.FILES)
                if not  'archivo' in request.FILES:
                    return JsonResponse({"result": "bad", "mensaje": u"Falta de subir el archivo de solicitud."})
                d = request.FILES['archivo']
                newfilesd = d._name
                ext = newfilesd[newfilesd.rfind("."):]
                if ext == '.pdf' or ext == '.PDF':
                    a = 1
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                if d.size > 10485760:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                if f.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("solicitudpracticas_", newfile._name)
                    empresaempleadora = None
                    configuracionevidencia = None
                    otraempresaempleadora = ''
                    if int(request.POST['ofertaid']) > 0:
                        ofertapracticas = OfertasPracticas.objects.filter(id=int(request.POST['ofertaid']), inicio__lte=datetime.now().date(), fin__gte=datetime.now().date(), carrera=inscripcion.carrera, status=True)[0]
                        if not ofertapracticas:
                            return JsonResponse({"result": "bad", "mensaje": u"No puede inscribirse en oferta"})
                        if not ofertapracticas.haycupo():
                            return JsonResponse({"result": "bad", "mensaje": u"No hay cupos para la oferta"})
                        empresaempleadora = ofertapracticas.empresa
                        otraempresaempleadora = ofertapracticas.otraempresaempleadora if ofertapracticas.otraempresaempleadora else ""
                        departamento = ofertapracticas.departamento
                        fechadesde = ofertapracticas.iniciopractica
                        fechahasta = ofertapracticas.finpractica
                        tipoinstitucion = ofertapracticas.tipoinstitucion
                        sectoreconomico = ofertapracticas.sectoreconomico
                        otraempresa = ofertapracticas.otraempresa
                        tipo = ofertapracticas.tipo
                        numerohora = ofertapracticas.numerohora
                    else:
                        # if f.cleaned_data['tutorunemi']:
                        #     tutoruniversidad = int(f.cleaned_data['tutorunemi'])
                        # else:
                        #     tutoruniversidad = None
                        if f.cleaned_data['otraempresa']:
                            otraempresaempleadora = f.cleaned_data['otraempresaempleadora']
                        else:
                            empresaempleadora = f.cleaned_data['empresaempleadora']
                        if int(f.cleaned_data['tipopractica']) == 1 and int(f.cleaned_data['tiposolicitud']) == 3:
                            fechadesde = None
                            fechahasta = None
                        else:
                            fechadesde = f.cleaned_data['fechadesde']
                            fechahasta = f.cleaned_data['fechahasta']
                        tipo = f.cleaned_data['tipopractica']
                        departamento = f.cleaned_data['departamento']
                        tipoinstitucion = f.cleaned_data['tipoinstitucion']
                        sectoreconomico = f.cleaned_data['sectoreconomico']
                        numerohora = f.cleaned_data['numerohora']
                        otraempresa = f.cleaned_data['otraempresa']
                        configuracionevidencia = f.cleaned_data['configuracionevidencia']
                    practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion(inscripcion=inscripcion,
                                                                                                tipo=tipo,
                                                                                                fechadesde=fechadesde,
                                                                                                # vigente=f.cleaned_data['vigente'],
                                                                                                fechahasta=fechahasta,
                                                                                                departamento=departamento,
                                                                                                # tutorunemi_id=tutoruniversidad,
                                                                                                numerohora=numerohora,
                                                                                                institucion='',
                                                                                                tipoinstitucion=tipoinstitucion,
                                                                                                sectoreconomico=sectoreconomico,
                                                                                                tiposolicitud=f.cleaned_data['tiposolicitud'],
                                                                                                empresaempleadora=empresaempleadora,
                                                                                                otraempresa=otraempresa,
                                                                                                otraempresaempleadora=otraempresaempleadora,
                                                                                                archivo=newfile,
                                                                                                configuracionevidencia=configuracionevidencia)
                    if not int(tipo)==6:
                        if f.cleaned_data['tutorempresa']:
                            practicaspreprofesionalesinscripcion.tutorempresa=f.cleaned_data['tutorempresa']
                        malla = inscripcion.mi_malla()
                        nivel = inscripcion.mi_nivel().nivel
                        # if not f.cleaned_data['tiposolicitud'] == 3:
                        if ItinerariosMalla.objects.values('id').filter(malla=malla, nivel__id__lte=nivel.id, status=True).exists():
                            if not f.cleaned_data['itinerario']:
                                return JsonResponse({"result": "bad", "mensaje": u"Seleccione un itinerario."})
                            itinerario = ItinerariosMalla.objects.filter(id=f.cleaned_data['itinerario'].id, malla=malla, nivel__id__lte=nivel.id, status=True)
                            if itinerario:
                                practicaspreprofesionalesinscripcion.itinerariomalla = f.cleaned_data['itinerario']
                            else:
                                if nivel.id < 5:
                                    return JsonResponse({"result": "bad", "mensaje": u"Para solicitar debes haber pasado el 5 nivel."})
                    if int(encrypt(request.POST['idps']))> 0:
                        aperturapractica =  AperturaPracticaPreProfesional.objects.get(pk=int(encrypt(request.POST['idps'])))
                        practicaspreprofesionalesinscripcion.aperturapractica = aperturapractica
                        if aperturapractica.periodoppp:
                            practicaspreprofesionalesinscripcion.periodoppp = aperturapractica.periodoppp
                    practicaspreprofesionalesinscripcion.save(request)
                    if int(request.POST['ofertaid']) > 0:
                        practicaspreprofesionalesinscripcion.oferta=ofertapracticas
                        practicaspreprofesionalesinscripcion.save(request)
                    log(u'Adiciono practicas profesionales inscripcion: %s [%s] en el periodo [%s]' % (practicaspreprofesionalesinscripcion, practicaspreprofesionalesinscripcion.id, practicaspreprofesionalesinscripcion.periodoppp), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cargaradjunto':
            try:
                f = CargarAdjuntoPracticaForm(request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext == '.pdf':
                            if not ext == '.PDF':
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        if newfile.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                        if newfile:
                            newfile._name = generar_nombre("archivo_solicitud_practica", newfile._name)
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, debe subir un archivo."})
                if f.is_valid():
                    practicas = PracticasPreprofesionalesInscripcion.objects.get(pk=int(encrypt(request.POST['idp'])))
                    practicas.archivo = newfile
                    practicas.save(request)
                    log(u'Cargo adjunto de solicitud de practicas profesionales inscripcion: %s [%s]' % (practicas, practicas.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cargararchivo':
            try:
                practicas = PracticasPreprofesionalesInscripcion.objects.get(pk=request.POST['id'])

                estarechazadoevidencia = False
                if DetalleEvidenciasPracticasPro.objects.filter(status=True, evidencia_id=request.POST['idevidencia'], inscripcionpracticas_id=request.POST['id'], estadotutor=0).exists():
                    detalle = DetalleEvidenciasPracticasPro.objects.get(status=True, evidencia_id=request.POST['idevidencia'], inscripcionpracticas_id=request.POST['id'], estadotutor=0)
                    estarechazadoevidencia = True if detalle.estadotutor or detalle.estadorevision else False
                archivoant=None
                if practicas.formatoevidenciaalumno() == 1:
                    if practicas.evidenciasxfecha() or practicas.autorizarevidenciax24hrs() or  practicas.autorizarxevidencia7dias() or estarechazadoevidencia:
                        f = EvidenciaPracticasForm(request.POST, request.FILES)
                        # 2.5MB - 2621440
                        # 5MB - 5242880
                        # 10MB - 10485760
                        # 20MB - 20971520
                        # 50MB - 5242880
                        # 100MB 104857600
                        # 250MB - 214958080
                        # 500MB - 429916160
                        d = request.FILES['archivo']
                        newfilesd = d._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if ext == '.pdf' or ext == '.PDF':
                            a = 1
                        else:
                            return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf."})
                        if d.size > 20971520:
                            return JsonResponse({"result": True, "mensaje": u"Error, archivo mayor a 20 Mb."})
                        if f.is_valid():
                            newfile = None
                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                newfile._name = generar_nombre("informespracticas_", newfile._name)
                            if DetalleEvidenciasPracticasPro.objects.filter(status=True, evidencia_id=request.POST['idevidencia'], inscripcionpracticas_id=request.POST['id'], estadotutor=0).exists():
                                detalle = DetalleEvidenciasPracticasPro.objects.get(status=True, evidencia_id=request.POST['idevidencia'], inscripcionpracticas_id=request.POST['id'], estadotutor=0)
                                detalle.descripcion = f.cleaned_data['descripcion']
                                if f.cleaned_data['puntaje']:
                                    detalle.puntaje = f.cleaned_data['puntaje']
                                if detalle.estadorevision == 3 or detalle.estadorevision == 0:
                                    detalle.estadorevision = 1
                                elif detalle.estadotutor == 3:
                                    detalle.estadotutor = 0
                                # detalle.personaaprueba_id = None
                                # detalle.obseaprueba = None
                                # detalle.fechaaprueba = None
                                detalle.archivo = newfile
                                detalle.fechaarchivo = datetime.now()
                                detalle.save(request)
                            else:
                                if f.cleaned_data['puntaje']:
                                    detalle = DetalleEvidenciasPracticasPro(evidencia_id=request.POST['idevidencia'],
                                                                            inscripcionpracticas_id=request.POST['id'],
                                                                            descripcion=f.cleaned_data['descripcion'],
                                                                            puntaje=f.cleaned_data['puntaje'],
                                                                            archivo=newfile,
                                                                            fechaarchivo=datetime.now(),
                                                                            estadotutor=0)

                                else:
                                    detalle = DetalleEvidenciasPracticasPro(evidencia_id=request.POST['idevidencia'],
                                                                            inscripcionpracticas_id=request.POST['id'],
                                                                            descripcion=f.cleaned_data['descripcion'],
                                                                            fechaarchivo=datetime.now(),
                                                                            archivo=newfile, estadotutor=0)
                                detalle.save(request)
                            log(u'Adiciono evidencia de articulos en practicas profesionales: %s [%s]' % (detalle, detalle.id), request, "add")
                            if f.cleaned_data['puntaje']:
                                detalle.inscripcionpracticas.aprobacion_promedio_nota(request)
                            asunto = u"NOTIFICACIÓN INGRESO DE DOCUMENTO AL PORTAFOLIO"
                            send_html_mail(asunto,
                                           "emails/ingreso_evipracpreprofesionales.html",
                                           {'sistema': request.session['nombresistema'],
                                            'evidencia': detalle.evidencia.nombre,
                                            'alumno': inscripcion.persona},
                                           inscripcion.persona.lista_emails_envio(),[],
                                           cuenta=CUENTAS_CORREOS[4][1])
                            if detalle.evidencia.orden != 11 and detalle.evidencia.orden != 9 and detalle.evidencia.orden != 13 and detalle.evidencia.orden != 12:
                                supervisor = ''
                                tutor = ''
                                if detalle.inscripcionpracticas.supervisor:
                                    supervisor = detalle.inscripcionpracticas.supervisor.persona.nombre_completo_inverso()
                                if detalle.inscripcionpracticas.tutorunemi:
                                    tutor = detalle.inscripcionpracticas.tutorunemi.persona.nombre_completo_inverso()
                                    asunto1 = "NOTIFICACIÓN INGRESO DE EVIDENCIA PRÁCTICAS PREPROFESIONALES"
                                    send_html_mail(asunto1, "emails/notificasubeevidenciapracticatutor.html",
                                                   {'sistema': request.session['nombresistema'],
                                                    'detalle': detalle,
                                                    'alumno': detalle.inscripcionpracticas.inscripcion.persona.nombre_completo_inverso(),
                                                    'carrera': detalle.inscripcionpracticas.inscripcion.carrera.nombre_completo(),
                                                    'tutor': tutor,
                                                    'supervisor': supervisor},
                                                   detalle.inscripcionpracticas.tutorunemi.persona.lista_emails_envio(),
                                                   [],
                                                   cuenta=CUENTAS_CORREOS[0][1])
                            return JsonResponse({"result": False})

                    else:
                        # if not practicas.autorizarevidenciax24hrs():
                        return JsonResponse({"result": False, "mensaje": u"Ha excedido el límite de tiempo de carga de evidencias."})
                elif practicas.formatoevidenciaalumno() == 2:
                        f = EvidenciaPracticasForm(request.POST, request.FILES)
                        # 2.5MB - 2621440
                        # 5MB - 5242880
                        # 10MB - 10485760
                        # 20MB - 20971520
                        # 50MB - 5242880
                        # 100MB 104857600
                        # 250MB - 214958080
                        # 500MB - 429916160
                        d = request.FILES['archivo']
                        newfilesd = d._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if ext == '.pdf' or ext == '.PDF':
                            a = 1
                        else:
                            return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf."})
                        if d.size > 20971520:
                            return JsonResponse({"result": True, "mensaje": u"Error, archivo mayor a 20 Mb."})
                        if f.is_valid():
                            newfile = None
                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                newfile._name = generar_nombre("informespracticas_", newfile._name)
                            detalle = DetalleEvidenciasPracticasPro.objects.filter(status=True, evidencia_id=request.POST['idevidencia'], inscripcionpracticas_id=request.POST['id']).first()
                            if detalle:
                                if detalle.estadotutor == 2:
                                    raise NameError('La evidencia ya se encuestra en estado APROBADO')
                                if detalle.fechainicio and detalle.fechafin :
                                    if detalle.fechainicio.date() <= datetime.now().date() and detalle.fechafin.date() >= datetime.now().date():
                                        detalle.descripcion = f.cleaned_data['descripcion']
                                        if f.cleaned_data['puntaje']:
                                            detalle.puntaje = f.cleaned_data['puntaje']
                                        if detalle.estadorevision == 3 or detalle.estadorevision == 0:
                                            detalle.estadorevision = 1
                                        elif detalle.estadotutor == 3:
                                            detalle.estadotutor = 0
                                        if detalle.archivo:
                                            archivoant = detalle.archivo
                                        # detalle.personaaprueba_id = None
                                        # detalle.obseaprueba = None
                                        # detalle.fechaaprueba = None
                                        detalle.archivo = newfile
                                        detalle.fechaarchivo = datetime.now()
                                        detalle.save(request)
                                        if not archivoant:
                                            cursor = connection.cursor()
                                            sqlperiodo = "UPDATE sga_detalleevidenciaspracticaspro SET fecha_modificacion = null,fecha_creacion = '" + str(detalle.fecha_modificacion) + "' WHERE sga_detalleevidenciaspracticaspro.id=" + str(
                                                detalle.id) + ""
                                            cursor.execute(sqlperiodo)
                                        log(u'Adiciono evidencia de articulos en practicas profesionales: %s [%s]' % (detalle, detalle.id), request, "add")
                                        asunto = u"NOTIFICACIÓN INGRESO DE DOCUMENTO AL PORTAFOLIO"
                                        send_html_mail(asunto,
                                                       "emails/ingreso_evipracpreprofesionales.html",
                                                       {'sistema': request.session['nombresistema'],
                                                        'evidencia': detalle.evidencia.nombre,
                                                        'alumno': inscripcion.persona},
                                                       inscripcion.persona.lista_emails_envio(), [],
                                                       cuenta=CUENTAS_CORREOS[4][1])
                                        if detalle.evidencia.orden != 11 and detalle.evidencia.orden != 9 and detalle.evidencia.orden != 13 and detalle.evidencia.orden != 12:
                                            supervisor = ''
                                            tutor = ''
                                            if detalle.inscripcionpracticas.supervisor:
                                                supervisor = detalle.inscripcionpracticas.supervisor.persona.nombre_completo_inverso()
                                            if detalle.inscripcionpracticas.tutorunemi:
                                                tutor = detalle.inscripcionpracticas.tutorunemi.persona.nombre_completo_inverso()
                                                asunto1 = "NOTIFICACIÓN INGRESO DE EVIDENCIA PRÁCTICAS PREPROFESIONALES"
                                                send_html_mail(asunto1, "emails/notificasubeevidenciapracticatutor.html",
                                                               {'sistema': request.session['nombresistema'],
                                                                'detalle': detalle,
                                                                'alumno': detalle.inscripcionpracticas.inscripcion.persona.nombre_completo_inverso(),
                                                                'carrera': detalle.inscripcionpracticas.inscripcion.carrera.nombre_completo(),
                                                                'tutor': tutor,
                                                                'supervisor': supervisor},
                                                               detalle.inscripcionpracticas.tutorunemi.persona.lista_emails_envio(),
                                                               [],
                                                               cuenta=CUENTAS_CORREOS[0][1])
                                        return JsonResponse({"result": False})
                                    elif practicas.autorizarevidenciax24hrs() or practicas.autorizarxevidencia7dias() or estarechazadoevidencia:
                                        detalle.descripcion = f.cleaned_data['descripcion']
                                        if f.cleaned_data['puntaje']:
                                            detalle.puntaje = f.cleaned_data['puntaje']
                                        if detalle.estadorevision == 3 or detalle.estadorevision == 0:
                                            detalle.estadorevision = 1
                                        elif detalle.estadotutor == 3:
                                            detalle.estadotutor = 0
                                        if detalle.archivo:
                                            archivoant = detalle.archivo
                                        # detalle.personaaprueba_id = None
                                        # detalle.obseaprueba = None
                                        # detalle.fechaaprueba = None
                                        detalle.archivo = newfile
                                        detalle.fechaarchivo = datetime.now()
                                        detalle.save(request)
                                        if not archivoant:
                                            cursor = connection.cursor()
                                            sqlperiodo = "UPDATE sga_detalleevidenciaspracticaspro SET fecha_modificacion = null,fecha_creacion = '" + str(detalle.fecha_modificacion) + "' WHERE sga_detalleevidenciaspracticaspro.id=" + str(detalle.id) + ""
                                            cursor.execute(sqlperiodo)
                                        log(u'Adiciono evidencia de articulos en practicas profesionales: %s [%s]' % (
                                        detalle, detalle.id), request, "add")
                                        asunto = u"NOTIFICACIÓN INGRESO DE DOCUMENTO AL PORTAFOLIO"
                                        send_html_mail(asunto,
                                                       "emails/ingreso_evipracpreprofesionales.html",
                                                       {'sistema': request.session['nombresistema'],
                                                        'evidencia': detalle.evidencia.nombre,
                                                        'alumno': inscripcion.persona},
                                                       inscripcion.persona.lista_emails_envio(), [],
                                                       cuenta=CUENTAS_CORREOS[4][1])
                                        if detalle.evidencia.orden != 11 and detalle.evidencia.orden != 9 and detalle.evidencia.orden != 13 and detalle.evidencia.orden != 12:
                                            supervisor = ''
                                            tutor = ''
                                            if detalle.inscripcionpracticas.supervisor:
                                                supervisor = detalle.inscripcionpracticas.supervisor.persona.nombre_completo_inverso()
                                            if detalle.inscripcionpracticas.tutorunemi:
                                                tutor = detalle.inscripcionpracticas.tutorunemi.persona.nombre_completo_inverso()
                                                asunto1 = "NOTIFICACIÓN INGRESO DE EVIDENCIA PRÁCTICAS PREPROFESIONALES"
                                                send_html_mail(asunto1, "emails/notificasubeevidenciapracticatutor.html",
                                                               {'sistema': request.session['nombresistema'],
                                                                'detalle': detalle,
                                                                'alumno': detalle.inscripcionpracticas.inscripcion.persona.nombre_completo_inverso(),
                                                                'carrera': detalle.inscripcionpracticas.inscripcion.carrera.nombre_completo(),
                                                                'tutor': tutor,
                                                                'supervisor': supervisor},
                                                               detalle.inscripcionpracticas.tutorunemi.persona.lista_emails_envio(),
                                                               [],
                                                               cuenta=CUENTAS_CORREOS[0][1])
                                        return JsonResponse({"result": False})
                                    else:
                                        # if not practicas.autorizarevidenciax24hrs():
                                        return JsonResponse({"result": True, "mensaje": u"Ha excedido el límite de tiempo de carga de evidencias."})
                                else:
                                    # detalle = DetalleEvidenciasPracticasPro(evidencia_id=request.POST['idevidencia'],
                                    #                                         inscripcionpracticas_id=request.POST['id'],
                                    #                                         descripcion=f.cleaned_data['descripcion'],
                                    #                                         puntaje=f.cleaned_data['puntaje'],
                                    #                                         archivo=newfile)
                                    # detalle.save(request)
                                    return JsonResponse({"result": True,"mensaje": u"No tiene registrado fechas para subir evidencias"})
                            else:
                                return JsonResponse({"result": True, "mensaje": str(ex)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": str(ex)})

        if action == 'cargararchivohomologacion':
            try:
                practicas = PracticasPreprofesionalesInscripcion.objects.get(pk=request.POST['id'])
                estarechazadoevidencia = False
                if DetalleEvidenciaHomologacionPractica.objects.filter(evidencia_id=request.POST['idevidencia'], inscripcionpracticas_id=request.POST['id']).exists():
                    detalle = DetalleEvidenciaHomologacionPractica.objects.get(evidencia_id=request.POST['idevidencia'], inscripcionpracticas_id=request.POST['id'])
                    estarechazadoevidencia = True if detalle.estadotutor or detalle.estadorevision else False
                archivoant=None
                f = EvidenciaHomologacionForm(request.POST, request.FILES)
                d = request.FILES['archivo']
                newfilesd = d._name
                ext = newfilesd[newfilesd.rfind("."):]
                if ext == '.pdf' or ext == '.PDF':
                    a = 1
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                if d.size > 20971520:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                if f.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("informespracticas_", newfile._name)
                    if DetalleEvidenciaHomologacionPractica.objects.filter(evidencia_id=request.POST['idevidencia'],
                                                                           inscripcionpracticas_id=request.POST[
                                                                               'id']).exists():
                        detalle = DetalleEvidenciaHomologacionPractica.objects.get(
                            evidencia_id=request.POST['idevidencia'], inscripcionpracticas_id=request.POST['id'])
                        detalle.descripcion = f.cleaned_data['descripcion']
                        if f.cleaned_data['puntaje']:
                            detalle.puntaje = f.cleaned_data['puntaje']
                        if detalle.estadorevision == 3 or detalle.estadorevision == 0:
                            detalle.estadorevision = 1
                        elif detalle.estadotutor == 3:
                            detalle.estadotutor = 0
                        detalle.archivo = newfile
                        detalle.fechaarchivo = datetime.now()
                        detalle.save(request)
                    else:
                        if f.cleaned_data['puntaje']:
                            detalle = DetalleEvidenciaHomologacionPractica(evidencia_id=request.POST['idevidencia'],
                                                                           inscripcionpracticas_id=request.POST['id'],
                                                                           descripcion=f.cleaned_data['descripcion'],
                                                                           puntaje=f.cleaned_data['puntaje'],
                                                                           archivo=newfile,
                                                                           fechaarchivo=datetime.now(),
                                                                           estadotutor=0)

                        else:
                            detalle = DetalleEvidenciaHomologacionPractica(evidencia_id=request.POST['idevidencia'],
                                                                           inscripcionpracticas_id=request.POST['id'],
                                                                           descripcion=f.cleaned_data['descripcion'],
                                                                           fechaarchivo=datetime.now(),
                                                                           archivo=newfile, estadotutor=0)
                        detalle.save(request)
                    log(u'Adiciono evidencia de articulos para homologación en practicas profesionales: %s [%s]' % (
                    detalle, detalle.id), request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addevidenciaspracticasnormal':
            try:
                f = EvidenciaPracticasForm(request.POST, request.FILES)
                # 2.5MB - 2621440
                # 5MB - 5242880
                # 6MB - 6291456
                # 10MB - 10485760
                # 20MB - 20971520
                # 50MB - 5242880
                # 100MB 104857600
                # 250MB - 214958080
                # 500MB - 429916160
                d = request.FILES['archivo']
                newfilesd = d._name
                ext = newfilesd[newfilesd.rfind("."):]
                if ext == '.pdf':
                    a = 1
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                if d.size > 20971520:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                if f.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("informespracticas_", newfile._name)
                    if DetalleEvidenciasPracticasPro.objects.filter(evidencia_id=request.POST['idevidencia'], status=True,inscripcionpracticas_id=request.POST['id']).exists():
                        detalle = DetalleEvidenciasPracticasPro.objects.get(evidencia_id=request.POST['idevidencia'], status=True,inscripcionpracticas_id=request.POST['id'])
                        detalle.descripcion = f.cleaned_data['descripcion']
                        detalle.estadorevision = 1
                        detalle.personaaprueba_id = None
                        detalle.obseaprueba = None
                        detalle.fechaaprueba = None
                        detalle.archivo = newfile
                        detalle.fechaarchivo = datetime.now()
                        detalle.save(request)
                    else:
                        detalle = DetalleEvidenciasPracticasPro(evidencia_id=request.POST['idevidencia'],
                                                                inscripcionpracticas_id=request.POST['id'],
                                                                descripcion=f.cleaned_data['descripcion'],
                                                                puntaje=0, fechaarchivo = datetime.now(),
                                                                archivo=newfile)
                        detalle.save(request)
                    log(u'Adiciono evidencia de practicas normal en alumno practicas profesionales: %s [%s]' % (detalle, detalle.id),request, "add")
                    asunto = u"NOTIFICACIÓN INGRESO DE DOCUMENTO AL PORTAFOLIO"
                    send_html_mail(asunto, "emails/ingreso_evipracpreprofesionales.html",{'sistema': request.session['nombresistema'],'evidencia': detalle.evidencia.nombre,'alumno': inscripcion.persona}, inscripcion.persona.lista_emails_envio(),[], cuenta=CUENTAS_CORREOS[4][1])
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addevidenciashomologacionnormal':
            try:
                f = EvidenciaHomologacionForm(request.POST, request.FILES)
                d = request.FILES['archivo']
                newfilesd = d._name
                ext = newfilesd[newfilesd.rfind("."):]
                if ext == '.pdf':
                    a = 1
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                if d.size > 20971520:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                if f.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("informespracticas_", newfile._name)
                    if DetalleEvidenciaHomologacionPractica.objects.filter(evidencia_id=request.POST['idevidencia'], inscripcionpracticas_id=request.POST['id']).exists():
                        detalle = DetalleEvidenciaHomologacionPractica.objects.get(evidencia_id=request.POST['idevidencia'], inscripcionpracticas_id=request.POST['id'])
                        detalle.descripcion = f.cleaned_data['descripcion']
                        detalle.estadorevision = 1
                        detalle.personaaprueba_id = None
                        detalle.obseaprueba = None
                        detalle.fechaaprueba = None
                        detalle.archivo = newfile
                        detalle.fechaarchivo = datetime.now()
                        detalle.save(request)
                    else:
                        detalle = DetalleEvidenciaHomologacionPractica(evidencia_id=request.POST['idevidencia'],
                                                                inscripcionpracticas_id=request.POST['id'],
                                                                descripcion=f.cleaned_data['descripcion'],
                                                                puntaje=0, fechaarchivo = datetime.now(),
                                                                archivo=newfile)
                        detalle.save(request)
                    log(u'Adiciono evidencia para homologación de practicas normal en alumno practicas profesionales: %s [%s]' % (detalle, detalle.id),request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'retiro':
            try:
                f = RetiroPracticasForm(request.POST, request.FILES)
                # 2.5MB - 2621440
                # 5MB - 5242880
                # 6MB - 6291456
                # 10MB - 10485760
                # 20MB - 20971520
                # 50MB - 5242880
                # 100MB 104857600
                # 250MB - 214958080
                # 500MB - 429916160
                d = request.FILES['archivoretiro']
                newfilesd = d._name
                ext = newfilesd[newfilesd.rfind("."):]
                if ext == '.pdf':
                    a = 1
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                if d.size > 10485760:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                if f.is_valid():
                    newfile = None
                    if 'archivoretiro' in request.FILES:
                        newfile = request.FILES['archivoretiro']
                        newfile._name = generar_nombre("archivoretiro_", newfile._name)

                    practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.get(id=request.POST['id'])
                    practicaspreprofesionalesinscripcion.archivoretiro = newfile
                    practicaspreprofesionalesinscripcion.estadosolicitud = 5
                    practicaspreprofesionalesinscripcion.save(request)
                    log(u'Retiro de practicas profesionales: %s [%s]' % (practicaspreprofesionalesinscripcion, practicaspreprofesionalesinscripcion.id),request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al Retirar los datos."})

        elif action == 'delete':
            try:
                practicas = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.POST['id']))
                log(u'Eliminó practica preprofesionales inscripcion: %s' % practicas, request, "del")
                if practicas.oferta:
                    ofertapracticas = practicas.oferta
                    ofertapracticas.cupos += 1
                    ofertapracticas.save(request)
                practicas.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'listatipossolicitudes':
            try:
                aperturasolicitudpractica = AperturaPracticaPreProfesional.objects.get(pk=int(request.POST['id']))
                aperturatiposolicituddetalle = aperturasolicitudpractica.detalletiposolicitud().filter(tipo=int(request.POST['idt'])).distinct('tiposolicitud').order_by('tiposolicitud')
                lista = [(detalleapertura.tiposolicitud, detalleapertura.get_tiposolicitud_display()) for detalleapertura in aperturatiposolicituddetalle]
                return JsonResponse({"result": "ok", "lista":lista})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addinquietud':
            try:
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 41943040:
                        return JsonResponse({"result": True, "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 40Mb"})
                form = InquietudConsultaEstudianteForm(request.POST)
                if form.is_valid():
                    practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.POST['id']))
                    # practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.filter(pk=int(encrypt(request.POST['id']))).distinct().order_by('-fecha_creacion')
                    add = InquietudPracticasPreprofesionales(practica = practicaspreprofesionalesinscripcion,
                                                                      inquietud = form.cleaned_data['inquietud'],
                                                                      observacion = form.cleaned_data['observacion'],
                                                                      fechaingreso = datetime.now().date())
                    if 'archivo' in request.FILES:
                        nfile = request.FILES['archivo']
                        nombre_persona = remover_caracteres_especiales_unicode(persona.apellido1).lower().replace(' ', '_')
                        nfile._name = generar_nombre("inquietud_{}".format(nombre_persona), nfile._name)
                        add.archivo = nfile
                    add.save(request)
                    asunto = u"NUEVA INQUIETUD DE {} PRÁCTICAS PREPROFESIONALES".format(practicaspreprofesionalesinscripcion.inscripcion.persona.nombre_completo_inverso())
                    para = practicaspreprofesionalesinscripcion.tutorunemi.persona
                    observacion = 'Acceder a inquietudes para responder.'
                    notificacion(asunto, observacion, para, None, '/pro_cronograma?action=listatutorias', add.pk, 1, 'sga', InquietudPracticasPreprofesionales, request)
                    log(u'Adicionó inquietud de practica preprofesional al tutor : %s' % (add), request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editinquietud':
            try:
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 41943040:
                        return JsonResponse({"result": True, "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 40Mb"})
                form = InquietudConsultaEstudianteForm(request.POST)
                if form.is_valid():
                    edit = InquietudPracticasPreprofesionales.objects.get(pk=int(request.POST['id']))
                    edit.observacion=form.cleaned_data['observacion']
                    edit.inquietud=form.cleaned_data['inquietud']
                    edit.fechaingreso=datetime.now().date()
                    if 'archivo' in request.FILES:
                        nfile = request.FILES['archivo']
                        nombre_persona = remover_caracteres_especiales_unicode(persona.apellido1).lower().replace(' ', '_')
                        nfile._name = generar_nombre("inquietud_{}".format(nombre_persona), nfile._name)
                        edit.archivo = nfile
                    edit.save(request)
                    log(u'Edito inquietud de practica preprofesional al tutor: (%s)' % (edit), request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        # elif action == 'addinquietudconsultaestudiante':
        #     try:
        #         form = InquietudConsultaEstudianteForm(request.POST)
        #         if form.is_valid():
        #             practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.get(pk=int(encrypt_alu(request.POST['id_practica'])))
        #             # practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.filter(pk=int(encrypt(request.POST['id']))).distinct().order_by('-fecha_creacion')
        #             add = InquietudPracticasPreprofesionales(practica = practicaspreprofesionalesinscripcion,
        #                                                               inquietud = form.cleaned_data['inquietud'],
        #                                                               fechaingreso = datetime.now().date())
        #             add.save(request)
        #             log(u'Adicionó inquietud de practica preprofesional al tutor : %s' % (add), request, "add")
        #             return JsonResponse({"result": "ok"})
        #         else:
        #             return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        # elif action == 'editinquietudconsultaestudiante':
        #     try:
        #         form = InquietudConsultaEstudianteForm(request.POST)
        #         if form.is_valid():
        #             edit = InquietudPracticasPreprofesionales.objects.get(pk=int(encrypt_alu(request.POST['id'])))
        #             edit.inquietud=form.cleaned_data['inquietud']
        #             edit.fechaingreso=datetime.now().date()
        #             edit.save(request)
        #
        #             log(u'Edito inquietud de practica preprofesional al tutor: (%s)' % (edit), request, "edit")
        #             return JsonResponse({"result": "ok"})
        #         else:
        #             raise NameError('Error')
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'deleteinquietudconsultaestudiante':
            try:
                deleteobjeto = InquietudPracticasPreprofesionales.objects.get(pk=int(encrypt_alu(request.POST['id'])))
                log(u'Eliminó inquietud de practica preprofesional al tutor: %s' % deleteobjeto,request, "del")
                deleteobjeto.status = False
                deleteobjeto.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'listaevidenciashomologacion':
            try:
                configuracionevidencia = ConfiguracionEvidenciaHomologacionPractica.objects.get(
                    pk=int(encrypt_alu(request.POST['id'])))
                evidenciashomologacion = configuracionevidencia.evidenciashomologacion()
                DetalleEvidenciaHomologacionPractica.objects.filter()
                lista = [(evidencia.id, evidencia.orden, evidencia.nombre,
                          evidencia.descargar_archivo() if evidencia.archivo else None,
                          evidencia.nombrearchivo,
                          evidencia.descargar_archivo() if evidencia.archivo else None,
                          evidencia.nombrearchivo)
                         for evidencia in evidenciashomologacion]
                return JsonResponse({"result": "ok", "lista": lista})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

        elif action == 'deletesalud':
            try:
                practicas = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.POST['id']))
                detalle = practicas.preinscripcion
                if detalle:
                    # excluir el itinerario para la selección de los demás estudiantes
                    turno = None
                    if orden := detalle.inscripcion.ordenprioridadinscripcion_set.first():
                        grupoorden = detalle.preinscripcion.configuracionordenprioridadinscripcion_set.filter(status=True).first().grupoorden if detalle.preinscripcion.configuracionordenprioridadinscripcion_set.filter(status=True).first() else None
                        if grupoorden:
                            if turno := orden.obtenerturnoinscripcion(grupoorden, detalle.preinscripcion):
                                orden.excluirdato += str(detalle.itinerariomalla.id) + ','
                                orden.save(request)
                                if not DetallePreInscripcionPracticasPP.objects.filter(preinscripcion=detalle.preinscripcion, inscripcion=detalle.inscripcion, status=True).exclude(pk=detalle.id).exists():
                                    orden.status = False
                                    orden.save(request)

                    if detalle.puede_eliminar_todo(detalle.inscripcion):
                        respuestas = detalle.inscripcion.detallerespuestapreinscripcionppp_set.filter(preinscripcion=detalle.preinscripcion)
                        if respuestas:
                            for r in respuestas:
                                r.delete()
                        detalle.delete()
                    else:
                        detalle.delete()
                    log(u'Eliminó la pre-inscripción de practicas preprofesionales: %s - %s' % (persona, detalle), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        # elif action == 'notificarrevision':
        #     try:
        #
        #         soli = SolicitudHomologacionPracticas.objects.get(id=int(request.POST['id']))
        #         asunto = soli.inscripcion.persona.apellido1+" "+soli.inscripcion.persona.apellido2+" "+soli.inscripcion.persona.nombres+" SOLICITA REVISION DE DOCUMENTOS"
        #         para = soli.persona_vinculacion
        #         notificacion(asunto, soli.observacion, para, None,
        #                      '/alu_practicaspreprofesionalesinscripcion?action=solicitantes&id={}&search={}'.format(soli.apertura_id,soli.inscripcion.persona.cedula),
        #                      soli.pk, 1, 'sga', SolicitudHomologacionPracticas, request)
        #
        #         log(u'notificacion de  documento homologación estudiante: %s %s' % ( soli, soli.persona_vinculacion),
        #             request, "notificacion")
        #         return JsonResponse({"result": "ok"})
        #
        #     except Exception as ex:
        #         pass

        # if action == 'validaraccesodoc':
        #     try:
        #         practicas = PracticasPreprofesionalesInscripcion.objects.get(id=encrypt_alu(request.POST['id']))
        #         #evidencia = DetalleEvidenciasPracticasPro.objects.get(id=encrypt_alu(request.POST['ide']))
        #         if practicas.inscripcion.persona == persona:
        #             #if DetalleEvidenciasPracticasPro.objects.filter(id=evidencia.id, inscripcionpracticas__inscripcion__persona_id=persona.id).exists():
        #             url="/media/" + str(evidencia.archivo)
        #             return JsonResponse({'result': 'ok', 'url':url})
        #             # else:
        #             #     return JsonResponse({"result": "bad", "mensaje": u"Usuario no es dueño del documento."})
        #         else:
        #             return JsonResponse({"result": "bad", "mensaje": u"Usuario no es dueño del documento."})
        #     except Exception as ex:
        #         return JsonResponse({"result": "bad", "mensaje": u"Documento Externo."})

    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Registro de Solicitud Homologación Practicas'
                    # initial = {'fechadesde': datetime.now().date(), 'fechahasta': datetime.now().date()}
                    form = PracticasPreprofesionalesInscripcionSolicitarForm()
                    data['ofertaid'] = 0
                    malla = inscripcion.mi_malla()
                    nivel = inscripcion.nivelmatriculamalla()
                    form.cargar_itinerario(malla, nivel)
                    aperturasolicitudpractica = inscripcion.aperturassolicitudpracticaspreprofesionales_estudiante()
                    data['itinerarioscarrera'] = itinerarioscarrera = ItinerariosMalla.objects.filter(malla=malla, status=True).order_by('nivel__orden')
                    data['itinerarios'] = itinerarios = ItinerariosMalla.objects.filter(malla=malla, nivel__id__lte=nivel.id, status=True).order_by('nivel__orden')
                    if aperturasolicitudpractica:
                        data['filtro'] = aperturasolicitudpractica
                        data['aperturasolicitudpractica'] = aperturasolicitudpractica.id
                        carreraqs = CarreraHomologacion.objects.filter(apertura=aperturasolicitudpractica, carrera=inscripcion.carrera)
                        if carreraqs.exists():
                            data['carrerahomologacion'] = carreraqs.first()
                        else:
                            messages.warning(request, 'No existen periodos de homologación disponibles')
                            return redirect('/alu_practicaspro?action=procesohomologacion')
                        # form.cargar_tipopractica(aperturasolicitudpractica)
                        solicitudes = SolicitudHomologacionPracticas.objects.filter(status=True, apertura=aperturasolicitudpractica, inscripcion=inscripcion, estados__in=[0,1]).values_list('itinerario__id', flat=True)
                        form.fields['itinerario'].queryset = ItinerariosMalla.objects.filter(malla=malla, nivel__id__lte=nivel.id, status=True).exclude(pk__in=solicitudes).order_by('nivel__orden')
                        data['form'] = form
                        data['configuracionevidencia'] = ConfiguracionEvidenciaHomologacionPractica.objects.filter(carrera=inscripcion.carrera)
                        return render(request, "alu_practicaspro/form_homologacion.html", data)
                    else:
                        messages.warning(request, 'No existen periodos de homologación disponibles')
                        return redirect('/alu_practicaspro?action=procesohomologacion')
                except Exception as ex:
                    text_error = 'Error on line {} {}'.format(sys.exc_info()[-1].tb_lineno, str(ex))
                    return JsonResponse({'ex': f"{text_error}"})

            if action == 'verproceso':
                try:
                    data['title'] = u'Proceso de Solicitud Homologación Practicas'
                    data['solicitud'] = solicitud = SolicitudHomologacionPracticas.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['documentos'] = documentos = DocumentosSolicitudHomologacionPracticas.objects.filter(solicitud=solicitud).order_by('documento__documento__nombre')
                    data['filtro'] = filtro = solicitud.apertura
                    carreraqs = CarreraHomologacion.objects.filter(apertura=filtro, carrera=inscripcion.carrera)
                    form = PracticasPreprofesionalesInscripcionSolicitarForm(initial=model_to_dict(solicitud))
                    malla = inscripcion.mi_malla()
                    nivel = inscripcion.mi_nivel().nivel
                    form.cargar_itinerario(malla, nivel)
                    form.ver_proceso()
                    data['form'] = form
                    if carreraqs.exists():
                        data['carrerahomologacion'] = carreraqs.first()
                    pasoactual = 1
                    data['paso2'] = paso2 = False if not documentos.exists() else True
                    data['paso3'] = paso3 = False if not solicitud.revision_vinculacion == 1 else True
                    data['paso4'] = paso4 = False if not solicitud.revision_director == 1 else True
                    data['paso5'] = paso5 = False if not solicitud.estados == 1 else True
                    if paso2:
                        pasoactual = 2
                    if paso3:
                        pasoactual = 3
                    if paso4:
                        pasoactual = 4
                    if paso5:
                        pasoactual = 5
                    data['pasoactual'] = pasoactual
                    return render(request, "alu_practicaspro/wizard_homologacion.html", data)
                except Exception as ex:
                    return

            if action == 'cargadocumentosview':
                try:
                    data['id'] = id = request.GET['id']
                    data['itinerarioid'] = itinerarioid = request.GET['itinerario']
                    data['tipocontrato'] = tipocontrato = request.GET['tipocontrato']
                    data['filtro'] = filtro = AperturaPracticaPreProfesional.objects.get(pk=id)
                    data['documentos'] = documentos = CarreraHomologacionRequisitos.objects.filter(status=True, tipo=tipocontrato, itinerario__id=itinerarioid, carrera__apertura=filtro).order_by('documento__nombre')
                    template = get_template("alu_practicaspro/documentositinerario.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'reemplazardocumento':
                try:
                    data['filtro'] = solicitud = DocumentosSolicitudHomologacionPracticas.objects.get(pk=int(request.GET['id']))
                    form = ReemplazarDocumentoHomologacionForm(initial=model_to_dict(solicitud))
                    data['form2'] = form
                    template = get_template("alu_practicaspro/modal/reemplazardocumento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'procesohomologacion':
                try:
                    data['title'] = u'Procesos de Homologación'
                    data['listado'] = listado = SolicitudHomologacionPracticas.objects.filter(status=True, inscripcion=inscripcion).order_by('-pk')
                    data['aperturasolicitudpractica'] = aperturasolicitudpractica = inscripcion.aperturassolicitudpracticaspreprofesionales_estudiante()
                    return render(request, "alu_practicaspro/view_procesohomologacion.html", data)
                except Exception as ex:
                    pass

            if action == 'addoferta':
                try:
                    data['title'] = u'Inscribirse en oferta'
                    hoy = datetime.now().date()
                    ofertapracticas = OfertasPracticas.objects.filter(pk=int(encrypt_alu(request.GET['id'])), inicio__lte=hoy, fin__gte=hoy, carrera=inscripcion.carrera, status=True)
                    if ofertapracticas:
                        if not ofertapracticas[0].haycupo():
                            ofertapracticas = None
                    if ofertapracticas:
                        ofertapracticas = ofertapracticas[0]
                        form = PracticasPreprofesionalesInscripcionSolicitarForm(initial={'fechadesde': ofertapracticas.iniciopractica,
                                                                                          'fechahasta': ofertapracticas.finpractica,
                                                                                          'departamento': ofertapracticas.departamento,
                                                                                          'tipopractica': ofertapracticas.tipo,
                                                                                          'numerohora': ofertapracticas.numerohora,
                                                                                          'itinerario':ofertapracticas.itinerariosmalla.all(),
                                                                                          'otraempresa':ofertapracticas.otraempresa,
                                                                                          'tipoinstitucion': ofertapracticas.tipoinstitucion,
                                                                                          'sectoreconomico': ofertapracticas.sectoreconomico})
                        data['ofertaid'] = ofertapracticas.id
                        data['aperturasolicitudpractica'] = 0
                        form.bloquear_oferta()
                        form.cargar_tiposolicitud()
                        form.otraempresa_oferta(ofertapracticas)
                        malla = inscripcion.mi_malla()
                        nivel = inscripcion.mi_nivel().nivel
                        form.cargar_itinerariooferta(ofertapracticas.itinerariosmalla.all(), malla, nivel)
                        data['form'] = form
                    else:
                        raise NameError('Error')
                    return render(request, "alu_practicaspro/add.html", data)
                except Exception as ex:
                    pass

            if action == 'subirarchivos':
                try:
                    data['title'] = u' Carga de Evidencias de Prácticas Preprofesionales'
                    data['practicas'] = practicas = PracticasPreprofesionalesInscripcion.objects.get(pk=encrypt_alu(request.GET['id']))
                    if practicas.inscripcion.persona == persona:
                        data['evidencias'] =None
                        data['coordinacion'] = practicas.inscripcion.carrera.coordinacion_set.filter(status=True).first()
                        data['periodopractica'] = practicas.periodoppp
                        if practicas.periodoppp:
                            data['evidencias'] = practicas.periodoppp.evidencias_practica()
                        # elif PeriodoEvidenciaPracticaProfesionales.objects.filter(status=True, carrera=inscripcion.carrera).exists():
                        #         periodoevidencia = PeriodoEvidenciaPracticaProfesionales.objects.filter(status=True, carrera=inscripcion.carrera)[0]
                        #         data['evidencias'] = periodoevidencia.evidencias_practica()
                        data['formevidencias'] = EvidenciaPracticasForm()
                        return render(request, "alu_practicaspro/evidenciaspracticas.html", data)
                except Exception as ex:
                    pass
            if action == 'subirarchivoshomologacion':
                try:
                    data['title'] = u' Carga de Evidencias para homologación de Prácticas Preprofesionales'
                    data['practicas'] = practicas = PracticasPreprofesionalesInscripcion.objects.get(pk=request.GET['id'])
                    data['evidencias'] =None
                    if practicas.configuracionevidencia:
                        data['evidencias'] = practicas.configuracionevidencia.evidenciashomologacion()
                    elif ConfiguracionEvidenciaHomologacionPractica.objects.filter(status=True, carrera=inscripcion.carrera).exists():
                            configuracionevidencia = ConfiguracionEvidenciaHomologacionPractica.objects.filter(status=True, carrera=inscripcion.carrera)[0]
                            data['evidencias'] = configuracionevidencia.evidenciashomologacion()
                    data['formevidencias'] = EvidenciaHomologacionForm()
                    return render(request, "alu_practicaspro/evidenciashomologacion.html", data)
                except Exception as ex:
                    pass

            if action == 'addevidenciaspracticas':
                try:
                    data['title'] = u'Evidencias de Prácticas Preprofesionales'
                    data['form'] = EvidenciaPracticasForm
                    data['id'] = request.GET['id']
                    data['idevidencia'] = request.GET['idevidencia']
                    template = get_template("alu_practicaspro/add_evidenciaspracticas.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            if action == 'addevidenciaspracticasnormal':
                try:
                    data['title'] = u'Evidencia Programa'
                    data['form'] = EvidenciaPracticasNormalForm
                    data['id'] = request.GET['id']
                    data['idevidencia'] = request.GET['idevidencia']
                    template = get_template("alu_practicaspro/add_evidenciaspracticasnormal.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            if action == 'addevidenciashomologacionnormal':
                try:
                    data['title'] = u'Evidencia Programa'
                    data['form'] = EvidenciaPracticasNormalForm
                    data['id'] = request.GET['id']
                    data['idevidencia'] = request.GET['idevidencia']
                    template = get_template("alu_practicaspro/add_evidenciashomologacionnormal.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            if action == 'cargararchivo':
                try:
                    data['title'] = u'Evidencias de Prácticas Preprofesionales'
                    data['id'] = request.GET['id']
                    data['idevidencia'] = idevidencia=request.GET['idevidencia']
                    evidencia=EvidenciaPracticasProfesionales.objects.get(pk=idevidencia)
                    data['evidencia'] = evidencia
                    form = EvidenciaPracticasForm()
                    if not evidencia.puntaje:
                        form.concalificacion()
                    data['form'] = form
                    template = get_template("alu_practicaspro/add_evidenciaspracticas.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            if action == 'generarevidenciapracticapdf':
                try:
                    periodo = request.session['periodo']
                    ahora = datetime.now()
                    data_extra, detalle = {}, None
                    evidencia = EvidenciaPracticasProfesionales.objects.filter(id=int(request.GET.get('idevidencia', 0)), status=True).first()
                    detalle = DetalleEvidenciasPracticasPro.objects.filter(status=True, evidencia=evidencia, inscripcionpracticas_id=request.GET['id'], estadotutor=0).first()
                    if detalle:
                        regformato = evidencia.evidenciaformatoppp_set.filter(status=True).last()
                        if not regformato.formato:
                            raise NameError(f'Error al obtener los datos. No existe configurado un formato html en la Evidencia: {evidencia}. Intente nuevamente más tarde.')
                        formatohtml = regformato.formato.htmlnombre
                        data['DEBUG'] = DEBUG
                        data['fecha_creacion'] = datetime.now().date()
                        data['evidencia'] = evidencia
                        data['detalle'] = detalle
                        data['practicapp'] = practicapp = detalle.inscripcionpracticas
                        data['inscripcion'] = inscripcion = detalle.inscripcionpracticas.inscripcion
                        data['periodoppp'] = practicapp.periodoppp
                        nivel = practicapp.nivelmalla if practicapp.nivelmalla else practicapp.itinerariomalla.nivel if practicapp.itinerariomalla else ''
                        data['nivel'] = nivel.nombre.split(' ')[0] if nivel else ''
                        data['centrosalud'] = practicapp.empresaempleadora if practicapp.empresaempleadora else practicapp.asignacionempresapractica if practicapp.asignacionempresapractica else practicapp.otraempresaempleadora if practicapp.otraempresaempleadora else ''
                        data['regbitacora'] = bitacora = detalle.inscripcionpracticas.bitacoraactividadestudianteppp_set.filter(status=True).first()
                        data['mesbitacora'] = bitacora.nombre.split(':')[1].strip() if bitacora else '---'
                        # data['registros'] = registros = obtener_actividades_por_semana(bitacora.detallebitacoraestudianteppp_set.filter(status=True)) if bitacora else []

                        #Obtener el nombre del Itinerario conforme al formato del documento
                        if practicapp.itinerariomalla.malla.carrera.id in [3, 111]:
                            aux = practicapp.itinerariomalla.nombre.split('-')
                            nombreitinerario = aux[0].split('PROFESIONALES EN ')[1] + '- ' + aux[1].split('PROFESIONALES EN ')[1]
                        elif practicapp.itinerariomalla.malla.carrera.id in [112]:
                            nombreitinerario = practicapp.itinerariomalla.nombre.split('PROFESIONALES ')[1]
                        else:
                            nombreitinerario = practicapp.itinerariomalla.nombre
                        data['nombreitinerario'] = nombreitinerario
                        #cargos
                        data['tutor'] = tutor = practicapp.tutorunemi if practicapp.tutorunemi else practicapp.supervisor
                        data['coordinadorppp'] = coordinadorppp = DistributivoPersona.objects.get(denominacionpuesto_id=169, estadopuesto_id=1)
                        data['directorcarrera'] = directorcarrera = inscripcion.carrera.coordinador(periodo, 1)
                        data['decanocarrera'] = decanocarrera = inscripcion.carrera.coordinaciones()[0].responsable_periododos(periodo, 1)
                        matricula = inscripcion.matricula_set.filter(nivel__periodo=periodo)[0] if inscripcion.matricula_set.filter(nivel__periodo=periodo).exists() else None
                        eFilter, busquedaitinerario = Q(materia__asignaturamalla__nivelmalla=nivel, status=True), nombreitinerario.split('-') #obtener los docentes de las asignaturas
                        if len(busquedaitinerario) == 1: eFilter &= Q(materia__asignaturamalla__asignatura__nombre__icontains=busquedaitinerario[0].strip())
                        if len(busquedaitinerario) == 2: eFilter &= Q(Q(materia__asignaturamalla__asignatura__nombre__icontains=busquedaitinerario[0].strip()) | Q(materia__asignaturamalla__asignatura__nombre__icontains=busquedaitinerario[1].strip()))
                        materias = matricula.materiaasignada_set.filter(eFilter) if matricula else None
                        listadoDocentes = []
                        for m in materias:
                            if inscripcion.carrera.id in [111]:
                                nombremateria = m.materia.asignatura.nombre.split('PROFESIONALES EN ')[1].strip()
                            elif inscripcion.carrera.id in [110]:
                                nombremateria = m.materia.asignatura.nombre.split('ROTATIVO:')[1].strip()
                            elif inscripcion.carrera.id in [112]:
                                nombremateria = m.materia.asignatura.nombre.split('PROFESIONALES ')[1].strip()
                            else:
                                nombremateria = m.materia.asignatura.nombre
                            listadoDocentes.append([nombremateria, m.materia.profesor_principal()])
                        data['docentes'] = listadoDocentes
                        habilitarol, habilitatipo = False, False
                        if inscripcion.carrera.id in [3, 111]:
                            habilitarol, habilitatipo = False, True
                        elif inscripcion.carrera.id in [1, 110]:
                            habilitarol, habilitatipo = True, True
                        elif inscripcion.carrera.id in [112]:
                            habilitarol, habilitatipo = True, False
                        else:
                            habilitarol, habilitatipo = True, True

                        data['habilitarol'] = habilitarol
                        data['habilitatipo'] = habilitatipo

                        qrname = f"evidencia_{persona.usuario.username}_{evidencia.pk}"
                        rutafolder = f"evidenciasprapofesionales/{str(ahora.year)}/{ahora.month:02d}/{ahora.day:02d}/"
                        if True:
                        # if not detalle.archivo:
                        #     secuencia = secuencia_evidencia(evidencia.periodoppp, inscripcion, 'secuenciainforme')
                        #     data['secuencia'] = secuencia
                            data['secuencia'] = 2
                            folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'evidenciasprapofesionales', str(ahora.year), f'{ahora.month:02d}', f'{ahora.day:02d}', ''))
                            os.makedirs(folder, exist_ok=True)
                            generaevidencia, viewarchivogenerado = html_to_pdfsave_evienciassalud(f"alu_practicaspro/formatos_salud/{formatohtml}",
                                                                           {'pagesize': 'A4',
                                                                           'data': data,
                                                                           'evidencia': evidencia, 'tablapdf': True
                                                                           }, qrname+'.pdf', rutafolder
                                                                       )
                            # detalle.archivo = rutafolder + qrname + '.pdf'
                            # detalle.save(request)
                            repues = 'media'+'/'+rutafolder + qrname + '.pdf'
                            return JsonResponse({'result': 'ok', 'url': repues})
                            # return HttpResponse(SITE_STORAGE+'media'+rutafolder + qrname + '.pdf')
                        else:
                            response = requests.get(dominio_sistema + str(detalle.archivo.url))
                            response = HttpResponse(response.content, content_type='application/pdf')
                            response['Content-Disposition'] = 'attachment; filename={}.pdf'.format(qrname)
                            return response
                    else:
                        raise NameError('Error al obtener los datos.')
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'cargararchivohomologacion':
                try:
                    data['title'] = u'Evidencias de Prácticas Preprofesionales'
                    data['id'] = request.GET['id']
                    data['idevidencia'] = idevidencia=request.GET['idevidencia']
                    evidencia=EvidenciaHomologacionPractica.objects.get(pk=idevidencia)
                    data['evidencia'] = evidencia
                    form = EvidenciaHomologacionForm()
                    if not evidencia.puntaje:
                        form.concalificacion()
                    data['form'] = form
                    template = get_template("alu_practicaspro/add_evidenciashomologacionnormal.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            if action == 'retiro':
                try:
                    data['title'] = u'Retiro de Prácticas Preprofesionales'
                    data['id'] = request.GET['id']
                    data['practicaspreprofesionalesinscripcion'] = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.GET['id']))
                    form = RetiroPracticasForm()
                    data['form'] = form
                    return render(request, "alu_practicaspro/retiro.html", data)
                except Exception as ex:
                    pass

            if action == 'ver_observacion':
                try:
                    data = {}
                    solicitud = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.GET['idsolicitud']))
                    return JsonResponse({"result": "ok", 'data': solicitud.obseaprueba})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar Practicas PreProfesionales'
                    data['action'] = action
                    data['campo'] = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_practicaspro/delete.html", data)
                except:
                    pass

            elif action == 'horariotutor':
                try:
                    data['title'] = u'Horario del tutor académico'
                    data['practica'] = practica = PracticasPreprofesionalesInscripcion.objects.get(pk=int(encrypt(request.GET['id'])))
                    distributivoprofesor = practica.horarioactividadtutorpractica()
                    data['listaidcriterio'] = listaidcriterio = [6, 23, 31]
                    turnos = None
                    puede_ver_horario = False
                    if distributivoprofesor:
                        actividades = ClaseActividad.objects.filter(detalledistributivo__distributivo__id=distributivoprofesor.id, detalledistributivo__criteriodocenciaperiodo__criterio__id__in=listaidcriterio)
                        turnos = Turno.objects.filter(status=True, mostrar=True, id__in=actividades.values_list('turno__id')).distinct().order_by('comienza')
                        puede_ver_horario = True if distributivoprofesor.periodo.visible == True and distributivoprofesor.periodo.visiblehorario == True else False
                    data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
                    data['turnos'] = turnos
                    data['puede_ver_horario'] = puede_ver_horario
                    data['distributivoprofesor'] = distributivoprofesor
                    return render(request, "alu_practicaspro/horarioactividadtutoracademico.html", data)
                except:
                    pass

            elif action == 'ofertaspracticas':
                try:
                    data['title'] = u'Listado de Ofertas Prácticas'
                    search = None
                    ids = None
                    ofertasregistradas = PracticasPreprofesionalesInscripcion.objects.values_list('oferta__id').filter(inscripcion=perfilprincipal.inscripcion, oferta__isnull=False, status=True).distinct()
                    if 'id' in request.GET:
                        ids = request.GET['id']
                        ofertas = OfertasPracticas.objects.filter(pk=ids, inicio__lte=datetime.now().date(), fin__gte=datetime.now().date(), carrera=inscripcion.carrera, status=True).exclude(pk__in=ofertasregistradas).distinct().order_by('-inicio')
                    elif 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            ofertas = OfertasPracticas.objects.filter(cupos=search, inicio__lte=datetime.now().date(), fin__gte=datetime.now().date(), carrera=inscripcion.carrera, status=True).exclude(pk__in=ofertasregistradas).distinct().order_by('-inicio')
                        else:
                            ofertas = OfertasPracticas.objects.filter(Q(inicio__lte=datetime.now().date()), Q(fin__gte=datetime.now().date()), Q(carrera=inscripcion.carrera), ((Q(empresa__nombre__icontains=search) | Q(departamento__nombre__icontains=search)) | (Q(otraempresaempleadora__icontains=search) & Q(otraempresaempleadora__icontains=search))), Q(status=True)).exclude(pk__in=ofertasregistradas).distinct().order_by('-inicio')
                    else:
                        ofertas = OfertasPracticas.objects.filter(status=True, inicio__lte=datetime.now().date(), fin__gte=datetime.now().date(), carrera=inscripcion.carrera).exclude(pk__in=ofertasregistradas).distinct().order_by('-inicio')
                    if ItinerariosMalla.objects.values('id').filter(malla = inscripcion.mi_malla(), status=True).exists():
                        ofertas = ofertas.filter(itinerariosmalla__malla=inscripcion.mi_malla(), itinerariosmalla__nivel__id__lte=inscripcion.mi_nivel().nivel.id).distinct().exclude(pk__in=ofertasregistradas).order_by('-inicio')
                    paging = MiPaginador(ofertas, 25)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['ofertas'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "alu_practicaspro/ofertaspracticas.html", data)
                except Exception as ex:
                    pass

            elif action == 'cartavinculacion':
                try:
                    data['title'] = u'Mis cartas de vinculación'
                    search = None
                    cartavinculacion = None
                    isnulldirector = False
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            cartavinculacion = CartaVinculacionPracticasPreprofesionales.objects.filter(pk=search,
                                                                                                        status=True, detallecartainscripcion__inscripcion__inscripcion__persona_id=inscripcion.persona.id, director__isnull=isnulldirector)
                        else:
                            if ' ' in search:
                                s = search.split(" ")
                                if len(s) == 1:
                                    cartavinculacion = CartaVinculacionPracticasPreprofesionales.objects.filter(
                                        Q(carrera__nombre__icontains=s[0]), Q(status=True),detallecartainscripcion__inscripcion__inscripcion__persona_id=inscripcion.persona.id, director__isnull=isnulldirector)
                                elif len(s) == 2:
                                    cartavinculacion = CartaVinculacionPracticasPreprofesionales.objects.filter(
                                        Q(carrera__nombre__icontains=s[0]) & Q(carrera__nombre__icontains=s[1]) & Q(
                                            status=True), detallecartainscripcion__inscripcion__inscripcion__persona_id=inscripcion.persona.id, director__isnull=isnulldirector)
                                elif len(s) == 3:
                                    cartavinculacion = CartaVinculacionPracticasPreprofesionales.objects.filter(
                                        Q(carrera__nombre__icontains=s[0]) & Q(carrera__nombre__icontains=s[1]) & Q(
                                            carrera__nombre__icontains=s[2]), Q(status=True),detallecartainscripcion__inscripcion__inscripcion__persona_id=inscripcion.persona.id, director__isnull=isnulldirector)
                            else:
                                cartavinculacion = CartaVinculacionPracticasPreprofesionales.objects.filter(status=True,detallecartainscripcion__inscripcion__inscripcion__persona_id=inscripcion.persona.id, director__isnull=isnulldirector)
                    else:
                        cartavinculacion = CartaVinculacionPracticasPreprofesionales.objects.filter(status=True,detallecartainscripcion__inscripcion__inscripcion__persona_id=inscripcion.persona.id, director__isnull=isnulldirector)
                    paging = MiPaginador(cartavinculacion, 25)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['cartasvinculacion'] = page.object_list
                    data['search'] = search if search else ""
                    return render(request, "alu_practicaspro/viewmiscartas.html", data)
                except Exception as ex:
                    pass

            elif action == 'vercartavinculacion':
                try:
                    data['cartavinculacion'] = cartavinculacion = CartaVinculacionPracticasPreprofesionales.objects.get(pk=int(encrypt_alu(request.GET['id'])))
                    data['inscripciones'] = cartavinculacion.detallecartainscripcion_set.filter(status=True)
                    data['itinerarios'] = cartavinculacion.detallecartaitinerario_set.filter(status=True)
                    return render(request, "alu_practicaspreprofesionalesinscripcion/modalvercartavinculacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'miplanpractica':
                try:
                    data['title'] = u' Plan de Prácticas Preprofesionales'
                    hoy = datetime.now().date()

                    programa=ProgramaPracticaPreProfesional.objects.values_list('plan_id',flat=True).filter(status=True,carrera=inscripcion.carrera).distinct()
                    data['planes']=PlanPracticaPreProfesional.objects.filter(status=True,id__in=programa,fechadesde__lte=hoy, fechahasta__gte=hoy)
                    data['inscripcion'] = inscripcion

                    return render(request, "alu_practicaspro/plan_practica_ofertas.html", data)
                except:
                    pass

            elif action == 'agendatutorias':
                try:
                    data['title'] = u'Agenda de tutorías en prácticas'
                    querybasetutorias = EstudiantesAgendaPracticasTutoria.objects.select_related('estudiante__inscripcion').filter(status=True, estudiante__inscripcion=inscripcion, cab__status=True)
                    listacab = AgendaPracticasTutoria.objects.filter(status=True, pk__in=querybasetutorias.values_list('cab',flat=True)).distinct('fecha').values_list('fecha',flat=True)
                    listfechas = list(listacab)
                    data['meses'] = MESES_CHOICES
                    data['anios'] = sorted(set([l2[0] for l2 in [ str(l).split('-') for l in listfechas]]))
                    url_vars, anio_seleccionado, mes_seleccionado = '', request.GET.get('anio', datetime.now().year), request.GET.get('mes', datetime.now().month)
                    if anio_seleccionado:
                        data['anio'] = anio = int(anio_seleccionado)
                        if 'anio' in request.GET and request.GET['anio'].isdigit():
                            url_vars += "&anio={}".format(anio_seleccionado)
                    if mes_seleccionado:
                        data['mes'] = mes = int(mes_seleccionado)
                        data['mes_sel'] = datetime.strptime("2021-{}-01".format(mes), '%Y-%m-%d')
                        if 'mes' in request.GET and request.GET['mes'].isdigit():
                            url_vars += "&mes={}".format(mes_seleccionado)
                    data['tutorias_hoy'] = tutorias_hoy = querybasetutorias.filter(cab__fecha__month=mes_seleccionado, cab__fecha__year=anio_seleccionado, cab__fecha=datetime.now().date()).order_by('cab__fecha', 'cab__hora_inicio')
                    data['totalhoy'] = tutorias_hoy.count()
                    data['tutorias_mes'] = tutorias_mes = querybasetutorias.filter(cab__fecha__month=mes_seleccionado, cab__fecha__year=anio_seleccionado).exclude(cab__fecha=datetime.now().date()).order_by('-cab__fecha', 'cab__hora_inicio')
                    data['totalmes'] = tutorias_mes.count()
                    data['url_vars'] = url_vars
                    return render(request, "alu_practicaspro/agendatutorias.html", data)
                except Exception as ex:
                    pass

            # elif action == 'vermisofertas':
            #     data['title'] = u'Solicitud de Inscripción'
            #     data['ofertas'] = OfertasPracticasInscripciones.objects.filter(inscripcion__persona=persona)
            #     return render(request, "alu_practicaspro/vermisofertas.html", data)

            elif action == 'inquietudconsultaestudiante':
                try:
                    data['title'] = u'Ingreso de Consulta de Estudiante'
                    data['inscrip'] = inscripcion
                    search = None

                    # practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.filter(inscripcion=perfilprincipal.inscripcion, status=True).exclude(culminada=True,retirado=True,tiposolicitud=2).distinct().order_by('-fecha_creacion')
                    practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.get(pk= int(encrypt_alu(request.GET['id_practica'])))
                    inquietudes = InquietudPracticasPreprofesionales.objects.filter(status=True,practica=practicaspreprofesionalesinscripcion).order_by('-id')
                    data['practica'] = practicaspreprofesionalesinscripcion
                    # for pr in preinscripciones:
                    #     pr.recorrido1(request)

                    if 's' in request.GET:
                        search = request.GET['s']
                        s = search.split(" ")
                        if len(s) == 1:
                            inquietudes = inquietudes.filter(Q(inquietud__icontains=search))
                        elif len(s) == 2:
                            inquietudes = inquietudes.filter((Q(inquietud__icontains=s[0])))
                    paging = MiPaginador(inquietudes, 20)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['inquietudes'] = page.object_list
                    data['search'] = search if search else ""
                    return render(request, "alu_practicaspro/listarinquietudconsultaestudiante.html", data)
                except Exception as ex:
                    pass

            elif action == 'addinquietud':
                try:
                    data['id'] = request.GET['id']
                    form = InquietudConsultaEstudianteForm()
                    data['form2'] = form
                    template = get_template("alu_practicaspro/modal/forminquietud.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editinquietud':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = InquietudPracticasPreprofesionales.objects.get(pk=int(request.GET['id']))
                    data['form2'] = InquietudConsultaEstudianteForm(initial=model_to_dict(filtro))
                    template = get_template("alu_practicaspro/modal/forminquietud.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            # elif action == 'addinquietudconsultaestudiante':
            #     try:
            #         data['title'] = u'Adicionar Inquietud de Practica'
            #         data['id_practica'] = request.GET['id_practica']
            #         form = InquietudConsultaEstudianteForm()
            #         data['form'] = form
            #         return render(request, "alu_practicaspro/addinquietudconsultaestudiante.html", data)
            #         #
            #         # template = get_template("alu_practicaspro/addinquietudconsultaestudiante.html")
            #         # json_content = template.render(data)
            #         # return JsonResponse({"result": "ok", 'html': json_content})
            #     except Exception as ex:
            #         pass

            # elif action == 'editinquietudconsultaestudiante':
            #     try:
            #         data['title'] = u'Editar Inquietud de Practica'
            #         data['id_practica'] = request.GET['id_practica']
            #         data['inquietud'] =  inquietud = InquietudPracticasPreprofesionales.objects.get(pk=int(encrypt_alu(request.GET['id'])))
            #         data['form'] = InquietudConsultaEstudianteForm(initial= model_to_dict(inquietud))
            #         return render(request, "alu_practicaspro/editinquietudconsultaestudiante.html", data)
            #     except Exception as ex:
            #         pass

            elif action == 'deleteinquietudconsultaestudiante':
                try:
                    data['title'] = u'Eliminar Inquietud de Practica'
                    data['id_practica'] = request.GET['id_practica']
                    data['inquietud'] = InquietudPracticasPreprofesionales.objects.get(pk=int(encrypt_alu(request.GET['id'])))
                    return render(request, "alu_practicaspro/deleteinquietudconsultaestudiante.html", data)
                except Exception as ex:
                    pass

            elif action == 'verrespuesta':
                try:
                    data['inquietud'] = inquietud = InquietudPracticasPreprofesionales.objects.get(pk=int(encrypt_alu(request.GET['id'])))
                    data['respuesta'] = inquietud.respuestas()
                    template = get_template("alu_practicaspro/verrespuesta.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'vertutorias':
                try:
                    data['id'] = id = int(request.GET['id'])
                    data['estudiante'] = estudiante = PracticasPreprofesionalesInscripcion.objects.get(pk=id)
                    data['tutorias'] = tutorias = PracticasTutoria.objects.filter(status=True, practica=estudiante).order_by('fechainicio')
                    template = get_template("alu_practicaspro/mistutorias.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            elif action == 'veragendastutorias':
                try:
                    data['id'] = id = int(request.GET['id'])
                    data['hoy'] = hoy = datetime.now().date()
                    data['tutoriashoy'] = EstudiantesAgendaPracticasTutoria.objects.filter(status=True, estudiante__inscripcion=inscripcion, cab__fecha=hoy, cab__status=True).order_by('cab__hora_inicio')
                    data['estudiantes'] = estudiantes = EstudiantesAgendaPracticasTutoria.objects.filter(status=True, estudiante_id=id, cab__status=True).exclude(cab__fecha=hoy).order_by('-cab__fecha')
                    template = get_template("alu_practicaspro/misagendastutorias.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            elif action == 'veragendahoy':
                try:
                    data['hoy'] = hoy = datetime.now().date()
                    data['tutoriashoy'] = EstudiantesAgendaPracticasTutoria.objects.filter(status=True, estudiante__inscripcion=inscripcion, cab__fecha=hoy, cab__status=True).order_by('cab__hora_inicio')
                    data['estudiantes'] = estudiantes = EstudiantesAgendaPracticasTutoria.objects.filter(status=True, estudiante__inscripcion=inscripcion, cab__status=True).exclude(cab__fecha=hoy).order_by('-cab__fecha')
                    template = get_template("alu_practicaspro/misagendastutorias.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            elif action == 'deletesalud':
                try:
                    data['title'] = u'Eliminar Practicas PreProfesionales'
                    data['action'] = action
                    data['campo'] = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_practicaspro/delete.html", data)
                except:
                    pass

        else:
            try:
                enespera = 1
                practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.filter(inscripcion=perfilprincipal.inscripcion, status=True).distinct().order_by('-fecha_creacion')
                data['title'] = u'Mis Prácticas Preprofesionales'
                data['formatoevidencias1'] = EvidenciaPracticasProfesionales.objects.filter(status=True,fechafin__lte='2017-09-30').exclude(nombrearchivo="")
                data['formatoevidencias2'] = EvidenciaPracticasProfesionales.objects.filter(nombrearchivo__isnull=False,status=True,fechainicio__gte='2017-10-01').exclude(nombrearchivo="")
                data['inscrip'] = inscripcion
                # if practicaspreprofesionalesinscripcion.filter():
                #     estados = practicaspreprofesionalesinscripcion.filter()[:1][0]
                #     # if estados.estadosolicitud == 1:
                #     #     enespera = 1
                #     # if estados.tiposolicitud == 1 or estados.tiposolicitud == 2:
                #     #     enespera = 1
                #     #     if estados.estadosolicitud == 3:
                #     #         enespera = 0
                #     if estados.estadosolicitud == 3:
                #         enespera = 0
                #     if estados.estadosolicitud == 2 and estados.culminada == True:
                #         enespera = 0
                #     if estados.culminada == True:
                #         enespera = 0
                # else:
                #     enespera = 0
                data['enespera'] = enespera
                malla = inscripcion.mi_malla()
                nivel = perfilprincipal.inscripcion.mi_nivel().nivel
                itinerario = ItinerariosMalla.objects.filter(malla=malla, nivel__id__lte=nivel.id, status=True)
                data['puede_adicionar'] = True
                # if itinerario:
                #     data['puede_adicionar'] = True
                # else:
                #     # data['puede_adicionar'] = inscripcion.mi_nivel().nivel.id >= 4
                #     data['puede_adicionar'] = True
                data['hojavidallena'] = False if persona.hojavida_llenapracticas() else True

                data['practicaspreprofesionales'] = practicaspreprofesionalesinscripcion
                if inscripcion.carrera.mi_coordinacion2() == 1:
                    data['reporte_0'] = obtener_reporte('certificado_prapre_empresa_salud')
                else:
                    data['reporte_0'] = obtener_reporte('certificado_prapre_empresa')

                data['reporte_1'] = obtener_reporte('certificado_actividadextracurricular')

                data['form2'] = CargarAdjuntoPracticaForm()
                data['aperturasolicitudpractica'] = inscripcion.aperturassolicitudpracticaspreprofesionales_estudiante()
                data['formatospractica'] = FormatoPracticaPreProfesional.objects.filter(status=True, vigente=True)
                practicaretirado =  practicaspreprofesionalesinscripcion.filter(retirado=True, fechahastapenalizacionretiro__gte=datetime.now().date()).order_by('-fechahastapenalizacionretiro')
                data['tienepenalizacionpractica'] = practicaretirado[0] if practicaretirado.exists() else None
                archivosGenerales = ArchivoGeneralPracticaPreProfesionales.objects.filter(status=True, visible=True, carrera__isnull=True)
                archivosCarrera = ArchivoGeneralPracticaPreProfesionales.objects.filter(status=True, visible=True, carrera=inscripcion.carrera)

                data['archivosgenerales'] = list(archivosGenerales)+list(archivosCarrera)

                data['programa']  = ProgramaPracticaPreProfesional.objects.filter(status=True, carrera_id=inscripcion.carrera_id).exists()
                iddetallecartainscripcion = DetalleCartaInscripcion.objects.filter(status=True, inscripcion__inscripcion__persona__id=inscripcion.persona.id).values_list('carta__id', flat=True)
                data['cartavinculacion']  = CartaVinculacionPracticasPreprofesionales.objects.filter(id__in=iddetallecartainscripcion, director__isnull=False).exists()

                # PRE-INSCRIPCIONES PRACTICAS PREPROFESIONALES
                data['confpreinscripcion'] = conf = \
                PreInscripcionPracticasPP.objects.filter(fechainicio__lte=datetime.now().date(),
                                                         fechafin__gte=datetime.now().date())[
                    0] if PreInscripcionPracticasPP.objects.filter(fechainicio__lte=datetime.now().date(),
                                                                   fechafin__gte=datetime.now().date()).exists() else []
                tiene_preinscripcion = False
                if inscripcion.inscripcionmalla_set.filter(status=True):
                    if not inscripcion.cumple_total_parcticapp():
                        preinscripcion = []
                        itinerarios = []
                        falta_horas = False
                        cant_preguntas = 0
                        respondio = False
                        if conf and not DetallePreInscripcionPracticasPP.objects.filter(preinscripcion=conf,
                                                                                        inscripcion=inscripcion).exists():
                            tiene_preinscripcion = True
                            if conf.coordinaciones():
                                if conf.carreras():
                                    if PreInscripcionPracticasPP.objects.filter(fechainicio__lte=datetime.now().date(),
                                                                                fechafin__gte=datetime.now().date(),
                                                                                carrera=inscripcion.carrera).exists():
                                        preinscripcion = \
                                        PreInscripcionPracticasPP.objects.filter(fechainicio__lte=datetime.now().date(),
                                                                                 fechafin__gte=datetime.now().date(),
                                                                                 carrera=inscripcion.carrera)[0]
                                else:
                                    if PreInscripcionPracticasPP.objects.filter(fechainicio__lte=datetime.now().date(),
                                                                                fechafin__gte=datetime.now().date(),
                                                                                coordinacion=inscripcion.carrera.coordinacion_set.filter(
                                                                                        status=True)[0]).exists():
                                        preinscripcion = \
                                        PreInscripcionPracticasPP.objects.filter(fechainicio__lte=datetime.now().date(),
                                                                                 fechafin__gte=datetime.now().date(),
                                                                                 coordinacion=
                                                                                 inscripcion.carrera.coordinacion_set.filter(
                                                                                     status=True)[0])[0]
                                        if preinscripcion.computacionaprobado:
                                            preinscripcion = preinscripcion if haber_aprobado_modulos_computacion(inscripcion) else []
                                        if preinscripcion.inglesaprobado:
                                            preinscripcion = preinscripcion if haber_aprobado_modulos_ingles(inscripcion) else []
                            else:
                                preinscripcion = conf
                            listapre = inscripcion.detallepreinscripcionpracticaspp_set.values_list(
                                'itinerariomalla_id', flat=False).filter(status=True, estado=1)
                            if inscripcion.mi_malla():
                                if inscripcion.mi_malla().itinerariosmalla_set.filter(status=True).exists():
                                    listaitinerariorealizado = inscripcion.cumple_total_horas_itinerario()
                                    itinerariosvalidosid = []
                                    for it in inscripcion.inscripcionmalla_set.filter(status=True)[0].malla.itinerariosmalla_set.filter(status=True):
                                        nivelhasta = it.nivel.orden
                                        if inscripcion.todas_materias_aprobadas_rango_nivel(1, nivelhasta-1):
                                            itinerariosvalidosid.append(it.pk)
                                    itinerarios = inscripcion.mi_malla().itinerariosmalla_set.filter(status=True, nivel__orden__lte=inscripcion.mi_nivel().nivel.orden+1).filter(pk__in=itinerariosvalidosid).exclude(id__in=listaitinerariorealizado).exclude(id__in=listapre)
                                else:
                                    if inscripcion.mi_nivel().nivel.orden > 5:
                                        if not inscripcion.detallepreinscripcionpracticaspp_set.filter(status=True,
                                                                                                       itinerariomalla__isnull=True).exists():
                                            falta_horas = inscripcion.cumple_total_parcticapp()
                                    else:
                                        preinscripcion = []
                                respondio = conf.detallerespuestapreinscripcionppp_set.filter(
                                    inscripcion=inscripcion).exists()
                            if not respondio:
                                cant_preguntas = conf.preguntas().count()
                        if preinscripcion:
                            data['preinscripcion'] = preinscripcion
                            extrapreins = preinscripcion.extrapreinscripcionpracticaspp_set.filter(status=True).last()
                            data['enlinea'] = extrapreins.enlinea if extrapreins else False
                            data['inglesaprobado'] = inglesaprobado = haber_aprobado_modulos_ingles(inscripcion.id)
                            data['computacionaprobado'] = computacionaprobado = haber_aprobado_modulos_computacion(inscripcion.id)
                            validar_preinscripcion_ = True
                            if not preinscripcion.inglesaprobado and not preinscripcion.computacionaprobado:
                                validar_preinscripcion_ = True
                            if preinscripcion.inglesaprobado and not preinscripcion.computacionaprobado:
                                validar_preinscripcion_ = inglesaprobado
                            if not preinscripcion.inglesaprobado and preinscripcion.computacionaprobado:
                                validar_preinscripcion_ = computacionaprobado
                            if preinscripcion.inglesaprobado and preinscripcion.computacionaprobado:
                                validar_preinscripcion_ = (computacionaprobado and inglesaprobado)
                            data['validar_preinscripcion_'] = validar_preinscripcion_
                        data['itinerarios'] = itinerarios
                        if not itinerarios:
                            tiene_preinscripcion = False
                        data['falta_horas'] = falta_horas
                        data['cant_preg'] = cant_preguntas
                        data['respondio'] = respondio
                data['tiene_preinscripcion'] = tiene_preinscripcion
                data['inscripcion'] = inscripcion = perfilprincipal.inscripcion

                data['noti_tutorias'] = EstudiantesAgendaPracticasTutoria.objects.filter(status=True, estudiante__inscripcion=inscripcion, cab__fecha=datetime.now().date(), cab__status=True, cab__estados_agenda=0).count()
                data['tutorias_por_confirmar'] = EstudiantesAgendaPracticasTutoria.objects.filter(estado_confirmacion=0, status=True, estudiante__inscripcion=inscripcion, cab__fecha__gte=datetime.now().date(), cab__status=True, cab__estados_agenda=0).count()

                fechainicioprimernivel = inscripcion.fechainicioprimernivel if inscripcion.fechainicioprimernivel else datetime.now().date()
                excluiralumnos = datetime(2009, 1, 21, 23, 59, 59).date()
                data['esexonerado'] = fechainicioprimernivel <= excluiralumnos

                return render(request, "alu_practicaspro/view.html", data)
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                print(str(ex))
                text_error = 'Error on line {} {}'.format(sys.exc_info()[-1].tb_lineno, str(ex))
                return JsonResponse({'ex': text_error})

def genera_secuencial():
    secuencial = SecuenciaEvidenciaSalud.objects.filter(status=True).first()
    return secuencial.liquidacioncompra + 1 if secuencial.liquidacioncompra > 0 else 1