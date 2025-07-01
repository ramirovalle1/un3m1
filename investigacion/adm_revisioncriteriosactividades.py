# -*- coding: UTF-8 -*-
import os
import random
import json
import io
import fitz
from urllib.parse import urljoin
from dateutil.rrule import MONTHLY, rrule
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.db.models import Q, Max, Count, PROTECT, Sum, Avg, Min, F, ExpressionWrapper, TimeField, DateTimeField
from django.contrib.auth.models import Group
from core.firmar_documentos import firmararchivogenerado
from decorators import secure_module
from investigacion.forms import UsuarioRevisaEvidenciaDocenteForm
from investigacion.models import UserCriterioRevisor, ProyectoInvestigacion, TIPO_ROL, BitacoraActividadDocente, DetalleBitacoraDocente, ESTADO_REVISION, HistorialBitacoraActividadDocente
from inno.models import UserCriterioRevisorIntegrantes, SubactividadDetalleDistributivo, SubactividadDocentePeriodo, EstadoEvidenciaSalud, DetalleEstadoEvidenciaSalud
from sagest.models import DistributivoPersona
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, generar_nombre, log, notificacion, remover_caracteres_tildes_unicode, remover_caracteres_especiales_unicode, variable_valor, get_director_vinculacion, actualiza_usuario_revisa_actividad, validar_archivo
from sga.models import ProfesorDistributivoHoras, AnexoEvidenciaActividad, EvidenciaActividadAudi, EvidenciaActividadDetalleDistributivo, HistorialAprobacionEvidenciaActividad, CUENTAS_CORREOS, miinstitucion, \
    EvidenciaActividadAudi, CriterioDocenciaPeriodo, Persona, CriterioInvestigacionPeriodo, CriterioGestionPeriodo, DetalleDistributivo, Profesor, ClaseActividad, MESES_CHOICES,  CoordinadorCarrera, Materia, ESTADO_APROBACION_EVIDENCIA, \
    ResponsableCoordinacion
import datetime
import calendar
from datetime import *
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt, nombremes
from settings import DEBUG, SITE_STORAGE
import xlwt
from xlwt import *
from core.firmar_documentos import firmar, obtener_posicion_x_y_saltolinea, verificarFirmasPDF
from django.contrib import messages
from django.core.files import File as DjangoFile
from sga.pro_cronograma import migrar_evidencia_integrante_grupo_investigacion
from sga.proyectovinculaciondocente import migrar_evidencia_proyecto_vinculacion
from core.firmar_documentos_ec import JavaFirmaEc
from django.core.files.base import ContentFile

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    es_administrativo = perfilprincipal.es_administrativo()
    periodo = request.session['periodo']
    es_administrador = persona.usuario.groups.values("id").filter(id=442).exists()
    data['es_coordinadorpp_'] = es_coordinadorpp_ = persona.distributivopersona_set.filter(denominacionpuesto_id=169, estadopuesto_id=1).exists()
    data['es_directorcarrera_'] = es_directorcarrera_ = persona.coordinadorcarrera_set.filter(tipo=3, periodo=periodo, status=True).exists()
    data['es_decano_'] = es_decano_ = persona.responsablecoordinacion_set.filter(persona=persona, periodo=periodo, tipo=1).exists()
    data['es_docente_'] = es_docente_ = persona.firmaevidenciadocente_set.filter(status=True).exists()
    hoytime = datetime.now()
    dominio_sistema = 'https://sga.unemi.edu.ec'
    if DEBUG:
        dominio_sistema = 'http://localhost:8000'
    data["DOMINIO_DEL_SISTEMA"] = dominio_sistema

    # if not es_administrativo and not es_docente_:
    if not es_administrativo:
        return HttpResponseRedirect("/?info=El Módulo está disponible para administrativos.")

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'actualizarhorasplanificadas':
            try:
                counter = 0
                year, month = request.POST['value'].split('-')
                for bitacora in BitacoraActividadDocente.objects.filter(criterio__distributivo__periodo=periodo, fechafin__month=int(month), fechafin__year=int(year), status=True):
                    horasplanificadas = bitacora.horasplanificadas
                    bitacora.horasplanificadas = 0
                    horasplcalculadas = bitacora.get_horasplanificadas()
                    if horasplanificadas > horasplcalculadas:
                        bitacora.horasplanificadas = horasplcalculadas
                        bitacora.save(request)
                        counter += 1
                return JsonResponse({'result': 'ok', 'mensaje': f'Se actualizaron {counter} bitácoras correspondientes al mes de {nombremes(int(month))}'.capitalize()})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': ex.__str__()})

        if action == 'addaprobacionevidencia':
            try:
                evidencia = EvidenciaActividadDetalleDistributivo.objects.get(pk=request.POST['id'])
                invalid_access = False
                if doc := evidencia.criterio.criteriodocenciaperiodo:
                    invalid_access = not doc.usercriteriorevisor_set.filter(persona=persona, criteriodocenciaperiodo__periodo=periodo, criteriodocenciaperiodo__subirevidencia=True, tiporevisor=1, status=True).values('id').exists()

                if inv := evidencia.criterio.criterioinvestigacionperiodo:
                    invalid_access = not inv.usercriteriorevisor_set.filter(persona=persona, criterioinvestigacionperiodo__periodo=periodo, criterioinvestigacionperiodo__subirevidencia=True, tiporevisor=1, status=True).values('id').exists()

                if ges := evidencia.criterio.criteriogestionperiodo:
                    invalid_access = not ges.usercriteriorevisor_set.filter(persona=persona, criteriogestionperiodo__periodo=periodo, criteriogestionperiodo__subirevidencia=True, tiporevisor=1, status=True).values('id').exists()

                if invalid_access:
                    raise NameError(f"No tiene permiso para realizar esta acción")

                parse_criterio_funcion = lambda x: {1: 55, 2: 56, 3: 57}[x] if x in (1, 2, 3) else None
                obse, estado, client_address = request.POST['obse'], int(request.POST['esta']), get_client_ip(request)
                capippriva = request.POST['capippriva'] if 'capippriva' in request.POST else ''
                browser = request.POST['navegador']
                ops = request.POST['os']
                cookies = request.POST['cookies']
                screensize = request.POST['screensize']
                evidencia.estadoaprobacion = estado
                evidencia.fechaaprobado = datetime.now().date() if evidencia.estadoaprobacion == 2 else evidencia.fechaaprobado
                evidencia.save(request)

                if doc:
                    # Aprobar detalle de bitacora para ppp (internado rotativo) cuando se apruebe la evidencia ingresada
                    if doc.criterio.pk == 167:
                        if bitacora := BitacoraActividadDocente.objects.filter(criterio=evidencia.criterio, fechaini=evidencia.desde, fechafin__month=evidencia.hasta.month, status=True).first():
                            ea, er = 1, 1
                            if evidencia.estadoaprobacion == 2:
                                ea, er = 2, 3
                            bitacora.get_detallebitacora().update(estadoaprobacion=ea)
                            bitacora.estadorevision = er
                            bitacora.save(request)
                            h = HistorialBitacoraActividadDocente(bitacora=bitacora, persona=persona, estadorevision=er)
                            h.save(request)

                if inv:
                    # Replicar evidencia del director de proyecto a investigadores asociados
                    if inv.criterio.pk == 55:
                        if proyecto := ProyectoInvestigacion.objects.filter(profesor=evidencia.criterio.distributivo.profesor, status=True).first():
                            for integrante in proyecto.integrantes_proyecto().exclude(funcion=1):
                                profesor = Profesor.objects.filter(persona=integrante.persona, status=True).first()
                                distributivo = DetalleDistributivo.objects.filter(criterioinvestigacionperiodo__criterio__id=parse_criterio_funcion(integrante.funcion), distributivo__profesor=profesor, distributivo__periodo=evidencia.criterio.distributivo.periodo, status=True).first()
                                if distributivo:
                                    _evidencia = EvidenciaActividadDetalleDistributivo.objects.filter(criterio=distributivo, hasta__month=evidencia.hasta.month, hasta__year=evidencia.hasta.year).first()
                                    if _evidencia:
                                        _evidencia.aprobado = evidencia.aprobado
                                        _evidencia.usuarioaprobado = evidencia.usuarioaprobado
                                        _evidencia.estadoaprobacion = estado
                                        _evidencia.fechaaprobado = datetime.now().date() if estado == 2 else _evidencia.fechaaprobado
                                        _evidencia.save(request)
                                        HistorialAprobacionEvidenciaActividad(evidencia=_evidencia, aprobacionpersona=persona, observacion=obse, fechaaprobacion=datetime.now().date(), estadoaprobacion=estado).save()
                                        estadoevidencia = _evidencia.get_estadoaprobacion_display()
                                        send_html_mail("Notificación de estado de evidencia.", "emails/estadoevidenciadocente.html", {'sistema': 'SGA-EVIDENCIA', 'estadoevidencia': estadoevidencia, 'evidencia': evidencia, 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'ip': client_address, 'ipvalida': capippriva, 'os': ops, 'cookies': cookies, 'screensize': screensize, 't': miinstitucion()}, _evidencia.criterio.distributivo.profesor.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[0][1])

                historial = HistorialAprobacionEvidenciaActividad(evidencia=evidencia, aprobacionpersona=persona, observacion=obse, fechaaprobacion=datetime.now().date(), estadoaprobacion=estado)
                historial.save(request)
                estadoevidencia = evidencia.get_estadoaprobacion_display()
                send_html_mail("Notificación de estado de evidencia.", "emails/estadoevidenciadocente.html", {'sistema': 'SGA-EVIDENCIA', 'estadoevidencia': estadoevidencia, 'evidencia': evidencia, 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'ip': client_address, 'ipvalida': capippriva, 'os': ops, 'cookies': cookies, 'screensize': screensize, 't': miinstitucion()}, evidencia.criterio.distributivo.profesor.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[0][1])
                migrar_evidencia_integrante_grupo_investigacion(request=request, evidencia=evidencia)
                doc and doc.criterio.tipo == 2 and migrar_evidencia_proyecto_vinculacion(request, None,  None, evidencia)

                log(f'{persona.usuario} {estadoevidencia.lower()} evidencia {evidencia.pk}', request, 'edit')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error al guardar los datos. {ex=}"})

        if action == 'firmadocumento':
            try:
                tfirmas = json.loads(request.POST['txtFirmas'])
                if not tfirmas:
                    raise NameError("Debe seleccionar la ubicación de la firma")
                x = tfirmas[-1]
                evidenciaactividad = EvidenciaActividadDetalleDistributivo.objects.get(pk=int(encrypt(request.POST['id_objeto'])))
                certificado = request.FILES["firma"]
                passfirma = request.POST['palabraclave']
                posx, posy, numpaginafirma, datau = x["x"] + 50, x["y"] + 40, x["numPage"], None
                documento_a_firmar = evidenciaactividad.archivo if not evidenciaactividad.archivofirmado else evidenciaactividad.archivofirmado
                bytes_certificado = certificado.read()
                extension_certificado = os.path.splitext(certificado.name)[1][1:]

                try:
                    datau = JavaFirmaEc(archivo_a_firmar=documento_a_firmar, archivo_certificado=bytes_certificado,
                                        extension_certificado=extension_certificado, password_certificado=passfirma,
                                        page=numpaginafirma, reason=f"Legalizar evidencia", lx=posx,
                                        ly=posy).sign_and_get_content_bytes()
                except Exception as ex:
                    ...

                if not datau:
                    raise NameError(u'Problemas de conexión con la plataforma Firma Ec. Por favor asegúrese de estar ingresando la contraseña correcta e intentelo más tarde')

                documento_a_firmar = io.BytesIO()
                documento_a_firmar.write(datau)
                documento_a_firmar.seek(0)

                _name = generar_nombre('evidencia_', 'file.pdf')
                evidenciaactividad.archivofirmado.save(_name, ContentFile(documento_a_firmar.read()))
                estadoaprobacion = 5 if evidenciaactividad.es_aprobador_evidencia(persona) and not evidenciaactividad.estadoaprobacion == 2 else 4
                if doc := evidenciaactividad.criterio.criteriodocenciaperiodo:
                    if doc.criterio.pk == 153:
                        estadoaprobacion = 5

                evidenciaactividad.estadoaprobacion = estadoaprobacion
                evidenciaactividad.save(request)
                historial = HistorialAprobacionEvidenciaActividad(evidencia=evidenciaactividad, aprobacionpersona=persona, observacion='Documento firmado', fechaaprobacion=datetime.now().date(), estadoaprobacion=estadoaprobacion)
                historial.save(request)
                auditoria = EvidenciaActividadAudi(evidencia=evidenciaactividad, archivo=evidenciaactividad.archivofirmado)
                auditoria.save(request)

                if evidenciaactividad.criterio.criterioinvestigacionperiodo:
                    migrar_firma_participantes_proyecto_investigacion(evidencia=evidenciaactividad, file=evidenciaactividad.archivofirmado, request=request)
                    migrar_evidencia_integrante_grupo_investigacion(request=request, evidencia=evidenciaactividad)

                if evidenciaactividad.criterio.criteriodocenciaperiodo:
                    migrar_evidencia_proyecto_vinculacion(request, None,  None, evidenciaactividad)

                log(u'Guardo archivo firmado: {}'.format(evidenciaactividad), request, "add")
                return JsonResponse({"result": False, "mensaje": "Guardado con exito", }, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar. %s" % ex.__str__()}, safe=False)

        elif action == 'firmadocumentosalud':
            try:
                tfirmas = json.loads(request.POST['txtFirmas'])
                if not tfirmas:
                    raise NameError("Debe seleccionar la ubicación de la firma")
                x = tfirmas[-1]
                posx, posy, numpaginafirma, datau = x["x"] + 50, x["y"] + 40, x["numPage"], None

                evidenciaactividad = EstadoEvidenciaSalud.objects.get(pk=int(encrypt(request.POST['id_objeto'])))

                certificado = request.FILES["firma"]
                passfirma = request.POST['palabraclave']
                tipo_evidencia = int(request.POST['val_extra'])
                eRol = ''
                documento_a_firmar = None
                es_directorcarrera = False
                es_coordinador = False
                es_decano = False
                es_docente = False

                carrera = None
                if evidenciaactividad.planificacionmensual and tipo_evidencia == 1:  # PlanificacionMensualSalud
                    carrera = evidenciaactividad.planificacionmensual.itinerariomalla.malla.carrera
                    coordinacion = carrera.coordinacion_carrera()
                    # directorcarrera = CoordinadorCarrera.objects.filter(carrera=carrera, tipo=3, periodo=periodo, status=True).first()
                    # decano = ResponsableCoordinacion.objects.filter(coordinacion=carrera.coordinacion_carrera(), periodo=periodo, tipo=1).first()
                    #
                    if es_coordinador := evidenciaactividad.es_coordinador(persona.id): eRol = 'coordinador'
                    elif es_directorcarrera := evidenciaactividad.es_directorcarrera(carrera.id, persona.id, periodo.id): eRol = 'director'
                    elif es_decano := evidenciaactividad.es_decano(coordinacion.id, persona.id, periodo.id): eRol = 'decano'
                    elif es_docente := evidenciaactividad.es_docente(persona.id, tipo_evidencia, periodo.id): eRol = 'docente'

                    documento_a_firmar = evidenciaactividad.planificacionmensual.archivo if evidenciaactividad.planificacionmensual.archivo else None
                    if not documento_a_firmar:
                        raise NameError('No existe archivo evidencia de Planificación Mensual')

                bytes_certificado = certificado.read()
                extension_certificado = os.path.splitext(certificado.name)[1][1:]

                try:
                    datau = JavaFirmaEc(archivo_a_firmar=documento_a_firmar, archivo_certificado=bytes_certificado,
                                        extension_certificado=extension_certificado, password_certificado=passfirma,
                                        page=numpaginafirma, reason=f"Firmar evidencia", lx=posx,
                                        ly=posy).sign_and_get_content_bytes()
                except Exception as ex:
                    ...

                if not datau:
                    raise NameError(u'Problemas de conexión con la plataforma Firma Ec. Por favor asegúrese de estar ingresando correctamente la contraseña o intente nuevamente más tarde')

                documento_a_firmar = io.BytesIO()
                documento_a_firmar.write(datau)
                documento_a_firmar.seek(0)

                _name = generar_nombre('evidencia_', 'file.pdf')

                if evidenciaactividad.planificacionmensual.archivo:
                    evidenciaactividad.archivorespaldo = evidenciaactividad.planificacionmensual.archivo
                evidenciaactividad.planificacionmensual.archivo.save(_name, ContentFile(documento_a_firmar.read()))

                eObservacion = f'Documento firmado por {persona}'

                if es_coordinador:
                    evidenciaactividad.rol_firma('coordinador')
                    eObservacion = f'Documento firmado por Coordinador{"a" if persona.es_mujer() else ""} de Pasantías y Prácticas Pre-Profesionales Unidad Ciencias de la Salud'

                elif es_directorcarrera:
                    evidenciaactividad.rol_firma('director')
                    eObservacion = f'Documento firmado por Director{"a" if persona.es_mujer() else ""} de Carrera'

                elif es_decano:
                    evidenciaactividad.rol_firma('decano')
                    eObservacion = f'Documento firmado por Decan{"a" if persona.es_mujer() else "o"} de la Facultad'

                elif es_docente:
                    evidenciaactividad.rol_firma('docente', persona.id)
                    eObservacion = f'Documento firmado por Docente Tutor de Prácticas Pre-Profesionales'

                # evidenciaactividad.estado = eEstado
                evidenciaactividad.persona = persona
                evidenciaactividad.fecha = hoytime
                evidenciaactividad.observacion = eObservacion
                evidenciaactividad.save(request)

                detalle = DetalleEstadoEvidenciaSalud(evidencia_estado=evidenciaactividad, persona=persona, observacion=eObservacion, fecha=hoytime, estado=evidenciaactividad.estado)
                detalle.save(request)

                log(u'Guardo archivo firmado: {}'.format(evidenciaactividad), request, "add")
                return JsonResponse({"result": False, "mensaje": "Guardado con exito", }, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar. %s" % ex.__str__()}, safe=False)

        if action == 'legalizarevidenciamanual':
            try:
                from postulaciondip.forms import ArchivoInvitacionForm

                evidencia = EvidenciaActividadDetalleDistributivo.objects.get(pk=request.POST['id'])
                f = ArchivoInvitacionForm(request.POST, request.FILES)
                if f.is_valid() and request.FILES.get('archivo', None):
                    newfile = request.FILES.get('archivo')
                    if newfile:
                        if newfile.size > 6291456:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):].lower()
                            if ext == '.pdf':
                                newfile._name = generar_nombre(f'evidencia_{request.user.username}_{evidencia.pk}_', 'firmada') + '.pdf'
                                evidencia.archivofirmado = newfile
                                evidencia.estadoaprobacion = 4
                                if doc := evidencia.criterio.criteriodocenciaperiodo:
                                    if doc.criterio.pk == 153:
                                        evidencia.estadoaprobacion = 5
                                evidencia.save(request)
                                historial = HistorialAprobacionEvidenciaActividad(evidencia=evidencia, aprobacionpersona=persona, observacion='DOCUMENTO FIRMADO', fechaaprobacion=datetime.now().date(), estadoaprobacion=4)
                                historial.save(request)
                                # auditoria = EvidenciaActividadAudi(evidencia=evidencia, archivo=newfile)
                                auditoria = EvidenciaActividadAudi(evidencia=evidencia, archivo=evidencia.archivofirmado)
                                auditoria.save(request)
                                log(u'Guardo archivo firmado: {}'.format(evidencia), request, "add")

                                if evidencia.criterio.criterioinvestigacionperiodo:
                                    migrar_firma_participantes_proyecto_investigacion(evidencia=evidencia, file=evidencia.archivofirmado, request=request)
                                    migrar_evidencia_integrante_grupo_investigacion(request=request, evidencia=evidencia)

                                if doc := evidencia.criterio.criteriodocenciaperiodo:
                                    doc.criterio.tipo == 2 and migrar_evidencia_proyecto_vinculacion(request, None, None, evidencia)
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivo con extención PDF."})

                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s" % ex})

        if action == 'actualizarevidenciamanual':
            try:
                from postulaciondip.forms import ArchivoInvitacionForm

                evidencia = EvidenciaActividadDetalleDistributivo.objects.get(pk=request.POST['id'])
                f = ArchivoInvitacionForm(request.POST, request.FILES)

                if f.is_valid() and request.FILES.get('archivo', None):
                    newfile = request.FILES.get('archivo')
                    descripcionarchivo = 'Archivo del informe'
                    resp = validar_archivo(descripcionarchivo, newfile, ['pdf'], '6MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    newfile._name = generar_nombre(f'evidencia_{request.user.username}_{evidencia.pk}_', 'firmada') + '.pdf'
                    evidencia.archivofirmado = newfile
                    evidencia.estadoaprobacion = 4
                    evidencia.save(request)

                    auditoria = EvidenciaActividadAudi.objects.filter(evidencia=evidencia, status=True).order_by('-id').first()
                    auditoria.archivo = evidencia.archivofirmado
                    auditoria.save(request)

                    log(u'Actualizó archivo firmado: {}'.format(evidencia), request, "edit")

                    if evidencia.criterio.criterioinvestigacionperiodo:
                        actualizar_firma_participantes_proyecto_investigacion(evidencia=evidencia, file=evidencia.archivofirmado, request=request)

                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s" % ex})

        if action == 'add':
            f = UsuarioRevisaEvidenciaDocenteForm(request.POST)
            if f.is_valid():
                try:
                    tipocriterio=int(request.POST['tipocriterio'])
                    tiporevisor=int(request.POST['tiporevisor'])
                    revisor = int(request.POST.get('personarevisa', 0))
                    rol = int(request.POST.get('rol', 1))
                    idsubactividad = request.POST.get('ids')
                    idcriterio = int(request.POST['idcriterio'])

                    codigodoc = None
                    codigoinv = None
                    codigodoges = None

                    filtro = Q(status=True, rol=rol, tiporevisor=tiporevisor, persona=revisor)
                    if tipocriterio == 1:
                        codigodoc = idcriterio
                        filtro &= Q(criteriodocenciaperiodo_id=idcriterio)

                    if tipocriterio == 2:
                        codigoinv = idcriterio
                        filtro &= Q(criterioinvestigacionperiodo_id=idcriterio)

                    if tipocriterio == 3:
                        codigodoges = idcriterio
                        filtro &= Q(criteriogestionperiodo_id=idcriterio)

                    if tipocriterio == 4:
                        codigodoc = idcriterio
                        filtro &= Q(criteriodocenciaperiodo_id=idcriterio)

                    if idsubactividad:
                        filtro &= Q(subactividad=idsubactividad)

                    if usuario := UserCriterioRevisor.objects.filter(filtro).first():
                        raise NameError(f"Este usuario ya se encuentra registrado en {usuario.get_criterio()[1]}")

                    userrevisor = UserCriterioRevisor(persona_id=revisor,
                                                      criteriodocenciaperiodo_id=codigodoc,
                                                      criterioinvestigacionperiodo_id=codigoinv,
                                                      criteriogestionperiodo_id=codigodoges,
                                                      tiporevisor=tiporevisor,
                                                      rol=rol,
                                                      subactividad_id=idsubactividad)
                    userrevisor.save(request)
                    if not Group.objects.filter(pk=421, user=userrevisor.persona.usuario):
                        grupo = Group.objects.get(pk=421)
                        grupo.user_set.add(userrevisor.persona.usuario)
                        grupo.save()
                    log(u'%s añadio al usuario %s como revisor de evidencia: %s' % (persona.pk, userrevisor.persona.pk, userrevisor.pk), request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": f"Error al guardar los datos. {ex.__str__()}"})

        elif action == 'masivo_directores':
            try:
                servidor = int(request.POST['servidor'])
                tipocriterio = int(request.POST['tipocriterio'])
                tiporevisor = int(request.POST['tiporevisor'])
                coordinaciones = periodo.nivel_set.values_list('nivellibrecoordinacion__coordinacion_id', flat=True).filter(status=True).distinct()
                carreras = Materia.objects.values_list('asignaturamalla__malla__carrera_id').filter(asignaturamalla__malla__carrera__coordinacion__id__in=coordinaciones,nivel__periodo=periodo,status=True).distinct()
                if servidor == 1: listado_revisor = ResponsableCoordinacion.objects.filter(tipo=1, coordinacion_id__in=coordinaciones, periodo=periodo,  status=True).distinct('coordinacion_id') #Decanos
                else: listado_revisor = CoordinadorCarrera.objects.filter(sede_id=1, tipo=3, periodo=periodo, carrera__id__in=carreras, status=True) #Directores
                rol = int(request.POST['rol'])
                codigo_c = int(request.POST['idcriterio'])
                eCriterio = None
                if tipocriterio == 1: eCriterio = CriterioDocenciaPeriodo.objects.get(pk=codigo_c)
                if tipocriterio == 3: eCriterio = CriterioGestionPeriodo.objects.get(pk=codigo_c)
                for d in listado_revisor:
                    if eCriterio and eCriterio.criterio.id.__str__() in variable_valor('USER_CRITERIOS_IDS'):
                        if tipocriterio == 1 and not UserCriterioRevisor.objects.filter(status=True, rol=rol, tiporevisor=tiporevisor, persona=d.persona, criteriodocenciaperiodo_id=codigo_c).exists():
                            userrevisor = UserCriterioRevisor(persona=d.persona, criteriodocenciaperiodo_id=codigo_c, tiporevisor=tiporevisor, rol=rol)
                            userrevisor.save(request)
                            if not Group.objects.filter(pk=421, user=userrevisor.persona.usuario):
                                grupo = Group.objects.get(pk=421)
                                grupo.user_set.add(userrevisor.persona.usuario)
                                grupo.save()
                            log(u'%s añadio al usuario %s como revisor de evidencia(masivo): %s' % (persona.pk, userrevisor.persona.pk, userrevisor.pk), request, "add")

                        if tipocriterio == 3 and not UserCriterioRevisor.objects.filter(status=True, rol=rol, tiporevisor=tiporevisor, persona=d.persona, criteriogestionperiodo_id=codigo_c).exists():
                            userrevisor = UserCriterioRevisor(persona=d.persona, criteriogestionperiodo_id=codigo_c, tiporevisor=tiporevisor, rol=rol)
                            userrevisor.save(request)
                            if not Group.objects.filter(pk=421, user=userrevisor.persona.usuario):
                                grupo = Group.objects.get(pk=421)
                                grupo.user_set.add(userrevisor.persona.usuario)
                                grupo.save()
                            log(u'%s añadio al usuario %s como revisor de evidencia(masivo): %s' % (persona.pk, userrevisor.persona.pk, userrevisor.pk), request, "add")
                return JsonResponse({"result": "ok", "error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'masivo_docentes_revision':
            try:
                servidor = int(request.POST['servidor'])
                tipocriterio = int(request.POST['tipocriterio'])
                codigo_c = int(request.POST['idcriterio'])
                criterio = None
                if tipocriterio == 1: criterio = CriterioDocenciaPeriodo.objects.get(pk=codigo_c)
                if tipocriterio == 3: criterio = CriterioGestionPeriodo.objects.get(pk=codigo_c)
                listadodirectoresdocentes, listado_detalledistributivo = [], []
                if criterio:
                    listadodirectoresdocentes = criterio.usercriteriorevisor_set.values_list('persona_id', flat=True).filter(status=True)
                if tipocriterio == 1:
                    listado_detalledistributivo = DetalleDistributivo.objects.filter(distributivo__periodo=periodo, distributivo__status=True, criteriodocenciaperiodo=criterio, status=True).exclude(distributivo__profesor__persona_id__in=listadodirectoresdocentes)
                if tipocriterio == 3:
                    listado_detalledistributivo = DetalleDistributivo.objects.filter(distributivo__periodo=periodo, distributivo__status=True, criteriogestionperiodo=criterio, status=True).exclude(distributivo__profesor__persona_id__in=listadodirectoresdocentes)
                if listadodirectoresdocentes and listado_detalledistributivo:
                    for d in listado_detalledistributivo:
                        distributivo = d.distributivo
                        profesor = d.distributivo.profesor
                        if tipocriterio in [1, 3] and criterio.criterio.id.__str__() in variable_valor('USER_CRITERIOS_IDS'):
                            actualiza_usuario_revisa_actividad(request, profesor, criterio, distributivo, 'add')
                return JsonResponse({"result": "ok", "error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'actualizalistado':
            try:
                listadopersonas = None
                tiporevisor = int(request.POST['tiporevisor'])
                if int(request.POST['tipocriterio']) == 1:
                    criterio = CriterioDocenciaPeriodo.objects.get(pk=request.POST['codigoactividad'])
                    listadopersonas = criterio.usercriteriorevisor_set.filter(tiporevisor=tiporevisor, status=True)
                if int(request.POST['tipocriterio']) == 2:
                    criterio = CriterioInvestigacionPeriodo.objects.get(pk=request.POST['codigoactividad'])
                    listadopersonas = criterio.usercriteriorevisor_set.filter(tiporevisor=tiporevisor, status=True)
                if int(request.POST['tipocriterio']) == 3:
                    criterio = CriterioGestionPeriodo.objects.get(pk=request.POST['codigoactividad'])
                    listadopersonas = criterio.usercriteriorevisor_set.filter(tiporevisor=tiporevisor, status=True)
                if int(request.POST['tipocriterio']) == 4:
                    criterio = CriterioDocenciaPeriodo.objects.get(pk=request.POST['codigoactividad'])
                    listadopersonas = criterio.usercriteriorevisor_set.filter(tiporevisor=tiporevisor, status=True)

                if ids := int(request.POST['ids']):
                    listadopersonas = listadopersonas.filter(subactividad=ids)

                data2 = lambda rol: [{'id': listap.id,
                                      'usuario': listap.persona.nombre_completo(),
                                      'count': listap.usercriteriorevisorintegrantes_set.filter(status=True).values('id').count()} for listap in listadopersonas.filter(rol=rol[0])]

                return JsonResponse({'result': 'ok','lista': [{'idrol': rol[0], 'rol': rol[1], 'data': data2(rol)} for rol in TIPO_ROL]})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'eliminarusercriterio':
            try:
                deleteuser = UserCriterioRevisor.objects.get(pk=request.POST['id'])
                deleteuser.delete()
                res_json = {"error": False}
                log(u'%s eliminó al usuario %s como revisor de evidencia: %s' % (persona.pk, deleteuser.persona.pk, deleteuser.pk), request, "del")
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'legalizarevidenciamasivo':
            try:
                nombre_mes = lambda x: ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"][int(x) - 1]
                evidencias = EvidenciaActividadDetalleDistributivo.objects.filter(pk__in=request.POST.get('id', '').split(','), status=True)
                render_mensaje = ''
                firma = request.FILES.get("firma", None)
                passfirma = request.POST.get('palabraclave', None)
                palabras = u"%s" % persona.nombre_completo().title()

                bytes_certificado = firma.read()
                extension_certificado = os.path.splitext(firma.name)[1][1:]
                for evidencia in evidencias:
                    try:
                        datas, datau = None, None
                        estadoaprobacion = 4 if not evidencia.es_aprobador_evidencia(persona) else 5
                        pdf = evidencia.archivo if not evidencia.archivofirmado else evidencia.archivofirmado
                        x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(pdf.url, palabras)

                        if not numpaginafirma:
                            raise NameError(f"No se encontró el nombre {palabras} en el archivo, por favor verifique si el nombre de esta persona se encuentra en la sección de firmas.")

                        if doc := evidencia.criterio.criteriodocenciaperiodo:
                            if doc.criterio.id in (150, 151, 184) and evidencia.estadoaprobacion == 4 and evidencia.generado:
                                palabras = get_director_vinculacion().nombres.upper() if get_director_vinculacion() else persona.nombre_completo().title()
                                x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(pdf.url, palabras)
                                x, y = x + 40, y - 230

                            if doc.criterio.pk == 167:
                                x += 240

                        try: datau = JavaFirmaEc(archivo_a_firmar=pdf, archivo_certificado=bytes_certificado, extension_certificado=extension_certificado, password_certificado=passfirma, page=numpaginafirma,reason=f"Legalizar evidencia {evidencia.pk}", lx=x, ly=y).sign_and_get_content_bytes()
                        except Exception as ex:
                            try: datau, datas = firmar(request, passfirma, firma, pdf, numpaginafirma, x, y, 150, 45)
                            except Exception as ex:
                                ...

                        if not datau:
                            raise NameError(f"Problemas de conexión con la plataforma Firma Ec. Por favor intentelo más tarde.")

                        generar_archivo_firmado = io.BytesIO()
                        generar_archivo_firmado.write(datau)
                        datas and generar_archivo_firmado.write(datas)
                        generar_archivo_firmado.seek(0)

                        filename = generar_nombre(f"{evidencia.hasta.month:02}_{evidencia.usuario_creacion}", 'file.pdf')
                        file_obj = DjangoFile(generar_archivo_firmado, name=filename)
                        evidencia.archivofirmado = file_obj
                        evidencia.estadoaprobacion = estadoaprobacion
                        evidencia.save(request)

                        historial = HistorialAprobacionEvidenciaActividad(evidencia=evidencia, aprobacionpersona=persona, observacion='Documento legalizado', fechaaprobacion=datetime.now().date(), estadoaprobacion=estadoaprobacion)
                        historial.save(request)

                        auditoria = EvidenciaActividadAudi(evidencia=evidencia, archivo=evidencia.archivofirmado)
                        auditoria.save(request)

                        if evidencia.criterio.criterioinvestigacionperiodo:
                            migrar_firma_participantes_proyecto_investigacion(evidencia=evidencia, file=evidencia.archivofirmado, request=request)
                            migrar_evidencia_integrante_grupo_investigacion(request=request, evidencia=evidencia)

                        if evidencia.criterio.criteriodocenciaperiodo:
                            migrar_evidencia_proyecto_vinculacion(request, None, None, evidencia)

                        log(u"Legalizó evidencia de id %s" % evidencia.pk, request, 'edit')
                    except Exception as ex:
                        render_mensaje += f'Error al firmar el informe del mes de <b>{nombre_mes(evidencia.hasta.month).lower()}</b> de{"l" if not evidencia.criterio.distributivo.profesor.persona.es_mujer() else " la"} docente <b>{evidencia.criterio.distributivo.profesor.__str__().title()}.</b><br> <span class="text-danger fs-6">{ex.__str__()}</span><br><br>'

                return JsonResponse({'result': len(render_mensaje) == 0, 'mensaje': render_mensaje})
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        if action == 'adddocentesrevision':
            try:
                revisor = request.POST.get('id', None)
                docentes_new = json.loads(request.POST['lista_items1'])
                docentes_old = UserCriterioRevisorIntegrantes.objects.filter(usuariorevisor_id=revisor, status=True).exclude(profesor__id__in=docentes_new)
                docentes_old.update(status=False, usuario_modificacion=persona.usuario, fecha_modificacion=datetime.now())

                for l in docentes_new:
                    if not UserCriterioRevisorIntegrantes.objects.values('id').filter(usuariorevisor_id=revisor, profesor_id=int(l), status=True).exists():
                        user = UserCriterioRevisorIntegrantes(usuariorevisor_id=request.POST.get('id', None), profesor_id=int(l))
                        user.save(request)

                log(u"Agregó a los docentes %s" % docentes_new, request, 'add')
                return JsonResponse({'result': 'ok', 'count': docentes_new.__len__()})
            except Exception as ex:
                return JsonResponse({"result": False, 'mensaje': u"Error de conexión. %s" % ex.__str__()})

        if action == 'revisionbitacora':
            try:
                _success = json.loads(request.POST['aprobados'])
                _decline = json.loads(request.POST['rechazados'])

                bitacora = BitacoraActividadDocente.objects.get(pk=request.POST['id'])
                DetalleBitacoraDocente.objects.filter(pk__in=_success, bitacoradocente=bitacora).update(estadoaprobacion=2, usuario_modificacion=persona.usuario, fecha_modificacion=datetime.now())

                _values = [(x.split(';')[0], x[x.find(';') + 1:]) for x in _decline]
                for v in _values:
                    DetalleBitacoraDocente.objects.filter(pk=v[0], bitacoradocente=bitacora).update(estadoaprobacion=3, observacion=v[1], usuario_modificacion=persona.usuario, fecha_modificacion=datetime.now())

                bitacora.estadorevision = 3
                bitacora.save(request)

                h = HistorialBitacoraActividadDocente(bitacora=bitacora, persona=persona, estadorevision=bitacora.estadorevision)
                h.save(request)

                log(u'Aprobo/rechazo detalle de bitacora', request, 'add')
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': f'{ex=}'})

        if action == 'actualizar_estado_revision_mes':
            try:
                mes, er, n_er = int(request.POST.get('m', 9)), int(request.POST.get('e', 3)), int(request.POST.get('n_er', 1))
                bitacoras = BitacoraActividadDocente.objects.filter(estadorevision=er, fechafin__month=mes, status=True).values_list('id', flat=True)

                if bool(request.POST.get('v', False)):
                    bitacoras = [x.pk for x in BitacoraActividadDocente.objects.filter(estadorevision=er, fechafin__month=mes, status=True) if x.get_porcentaje_cumplimiento() < 100]

                BitacoraActividadDocente.objects.filter(id__in=bitacoras).update(estadorevision=n_er, usuario_modificacion_id=1, fecha_modificacion=datetime.now())
                n_mes = MESES_CHOICES[mes-1][1]

                log(f'{persona.usuario} actualizó el estado de {bitacoras.__len__()} bitácoras del mes de {n_mes}', request, 'edit')
                return JsonResponse({'result': 'ok', 'count': bitacoras.__len__(), 'month': n_mes})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': f'{ex=}'})

        elif action == 'aprobarevidenciasalud':
            try:
                id = int(encrypt(request.POST['id']))
                estado = int(request.POST['estado'])
                observacion = request.POST['observacion']
                action_url = request.POST['action_url']
                registro = EstadoEvidenciaSalud.objects.get(status=True, pk=encrypt(request.POST['id']))
                registro.estado = estado
                registro.save(request)
                log('Edito el estado de la evidencia %s a estado %s' % (registro.__str__(), registro.estado), request, 'edit')

                detalle = DetalleEstadoEvidenciaSalud(evidencia_estado=registro, persona=persona, observacion=observacion, fecha=hoytime, estado=estado)
                detalle.save(request)
                log('Agrego detalle estado evidencia Salud %s - %s - %s' % (registro.__str__(), detalle.__str__(), detalle.get_estado_display()), request, 'add')

                eDestinatario = registro.planificacionmensual.supervisor.persona
                notificacion('Validación evidencia de tutorías',
                    f"Estimad{'o' if eDestinatario.es_mujer() else 'a'} {eDestinatario}, su evidencia correspondiente a la Planificación Mensual {registro.planificacionmensual.__str__().upper()} ha sido validada. Estado de la evidencia: {registro.get_estado_display()}. {f'Observación: {observacion}' if observacion else ''}",
                    eDestinatario, None,  f'{request.path}?action=evidenciassalud',
                    registro.id, 2, 'sga', EstadoEvidenciaSalud, request
                )
                return JsonResponse({'error': False, '_url': f'{request.path}?action={action_url}&estado={encrypt(estado)}'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "mensaje": u"Solicitud Incorrecta. Intente nuevamente más tarde"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'bitacoras':
                try:
                    data['title'] = u'Listado de bitacoras registradas'
                    now, dias_plazo = datetime.now().date(), variable_valor('DIA_LIMITE_INFORME_MENSUAL')
                    search, url_vars, numerofilas = request.GET.get('s', ''), '&action={}'.format(action), 15

                    nombre_mes = lambda i: ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"][i - 1]
                    _get_first_col = lambda x: [i[0] for i in x]
                    filters = Q(pk=0)

                    tipoencriptado = request.GET.get('tipo', encrypt(2))
                    tipoestado = int(encrypt(tipoencriptado))

                    usuariorevision = persona.usercriteriorevisor_set.filter(status=True)
                    data['codigosdoc'] = codigosdoc = usuariorevision.values_list('criteriodocenciaperiodo_id', 'criteriodocenciaperiodo__criterio__id', 'criteriodocenciaperiodo__criterio__nombre', 'rol', 'id').filter(criteriodocenciaperiodo__periodo=periodo, criteriodocenciaperiodo__llenarbitacora=True, tiporevisor=2, rol=1, status=True)
                    data['codigosinv'] = codigosinv = usuariorevision.values_list('criterioinvestigacionperiodo_id', 'criterioinvestigacionperiodo__criterio__id', 'criterioinvestigacionperiodo__criterio__nombre', 'rol', 'id').filter(criterioinvestigacionperiodo__periodo=periodo, criterioinvestigacionperiodo__llenarbitacora=True, tiporevisor=2, rol=1, status=True)
                    data['codigosges'] = codigosges = usuariorevision.values_list('criteriogestionperiodo_id', 'criteriogestionperiodo__criterio__id', 'criteriogestionperiodo__criterio__nombre', 'rol', 'id').filter(criteriogestionperiodo__periodo=periodo, criteriogestionperiodo__llenarbitacora=True, tiporevisor=2, rol=1, status=True)

                    _filters_ = process_codigos(codigosdoc, 'criteriodocenciaperiodo') + process_codigos(codigosinv, 'criterioinvestigacionperiodo') + process_codigos(codigosges, 'criteriogestionperiodo')

                    if _filters_:
                        filters = Q(_filters_[0])
                        for v in _filters_: filters |= Q(v)

                    filters &= Q(status=True, fechafin__month__gte=periodo.inicio.month)

                    bitacoras = BitacoraActividadDocente.objects.filter(filters).order_by('profesor__persona__apellido1', 'profesor__persona__apellido2')

                    meses = [{'name': nombre_mes(m), 'val': m} for m in set(bitacoras.values_list('fechafin__month', flat=True).order_by('fechafin').distinct())]

                    total = bitacoras.count()

                    if tipoestado: filters &= Q(estadorevision=tipoestado)

                    if criterio := request.GET.get('criterio', '0'):
                        if not criterio in ['0', ',', '']:
                            id, tipo = criterio.split(',')
                            if tipo == 'd': filters &= Q(criterio__criteriodocenciaperiodo__criterio__id=id)
                            if tipo == 'i': filters &= Q(criterio__criterioinvestigacionperiodo__criterio__id=id)
                            if tipo == 'g': filters &= Q(criterio__criteriogestionperiodo__criterio__id=id)
                            data |= {'criterio_id': int(id), 'tipocriterio': tipo}
                            url_vars += f"&criterio={criterio}"

                    if mes := int(request.GET.get('mes', '0')):
                        data['eMes'] = mes
                        filters &= Q(fechafin__month=mes)
                        url_vars += f"&mes={mes}"

                    if s := request.GET.get('s', ''):
                        data['search'] = search = s.strip()
                        url_vars += f'&s={search}'
                        ss = search.split(' ')

                        if len(ss) == 1:
                            filters &= Q(Q(criterio__distributivo__profesor__persona__nombres__icontains=search) | Q(criterio__distributivo__profesor__persona__apellido1__icontains=search) | Q(criterio__distributivo__profesor__persona__apellido2__icontains=search) | Q(criterio__distributivo__profesor__persona__cedula__icontains=search) | Q(criterio__distributivo__profesor__persona__pasaporte__icontains=search))
                        if len(ss) == 2:
                            filters &= Q(Q(criterio__distributivo__profesor__persona__apellido1__icontains=ss[0]) & Q(criterio__distributivo__profesor__persona__apellido2__icontains=ss[1]))
                        if len(ss) > 4:
                            filters &= Q(criterio__criteriodocenciaperiodo__criterio__nombre__icontains=search) | Q(criterio__criterioinvestigacionperiodo__criterio__nombre__icontains=search) | Q(criterio__criteriogestionperiodo__criterio__nombre__icontains=search)

                    paging = MiPaginador(BitacoraActividadDocente.objects.filter(filters).order_by('profesor__persona__apellido1', 'profesor__persona__apellido2'), numerofilas)

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

                    # Pasar a estado solicitado las bitacoras que esten pendientes en el día seleccionado como plazo
                    if now.day >= (dias_plazo + 1):
                        BitacoraActividadDocente.objects.filter(estadorevision=1, fechafin__month=now.month - 1, status=True).update(estadorevision=2)

                    data['tipo'] = tipoencriptado
                    url_vars += f'&tipo={tipoencriptado}'
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['numerofilasguiente'] = numerofilasguiente
                    data['numeropagina'] = p
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data["url_vars"] = url_vars
                    data['listaevidencias'] = page.object_list
                    data['tipo_int'] = tipoestado
                    data['puede_firmar_masivo'] = not codigosdoc == None
                    data['meses'] = meses
                    data['total'] = total
                    data['esinnovacion'] = persona.usuario.groups.filter(id=483).exists()
                    return render(request, "adm_revisioncriteriosactividades/listadobitacoras.html", data)
                except Exception as ex:
                    return HttpResponseRedirect('/adm_revisioncriteriosactividades?info=Error de conexión. %s' % ex.__str__())

            if action == 'solicitudes':
                try:
                    from sga.pro_cronograma import CRITERIO_INTEGRANTE_GRUPOINVESTIGACION, CRITERIO_ASOCIADO_PROYECTO, CRITERIO_CODIRECTOR_PROYECTO_INV

                    data['title'] = u'Listado evidencias'
                    search, url_vars, numerofilas = request.GET.get('s', ''), '&action={}'.format(action), 15
                    tipoencriptado = request.GET.get('tipo', encrypt(0))
                    tipoestado = int(encrypt(tipoencriptado))
                    lista_filtros = []
                    exclude1 = Q(subactividad__subactividaddocenteperiodo__criterio__in=[CRITERIO_INTEGRANTE_GRUPOINVESTIGACION, CRITERIO_ASOCIADO_PROYECTO, CRITERIO_CODIRECTOR_PROYECTO_INV])
                    filtro_revisor = Q(criteriodocenciaperiodo__periodo=periodo, criteriodocenciaperiodo__subirevidencia=True) | Q(criterioinvestigacionperiodo__periodo=periodo, criterioinvestigacionperiodo__subirevidencia=True) | Q(criteriogestionperiodo__periodo=periodo, criteriogestionperiodo__subirevidencia=True)

                    # Detección del rol del usuario revisor
                    roles = persona.usercriteriorevisor_set.filter(filtro_revisor).filter(tiporevisor=1, status=True).values_list('rol', flat=True).distinct()
                    if not tipoestado:
                        if 1 in roles:
                            tipoestado = 1
                        elif 2 in roles:
                            tipoestado = 4
                    # -------------------------------------

                    filters, filters2 = Q(estadoaprobacion=tipoestado, status=True), None
                    rol = (1, 2) # if tipoestado in (4, 5) else (1, )
                    usuariorevision = persona.usercriteriorevisor_set.filter(filtro_revisor).filter(tiporevisor=1, rol__in=rol, status=True).distinct()

                    for usr in usuariorevision:
                        filtro_evidencia = None
                        if usr.subactividad:
                            filtro_evidencia = Q(subactividad__subactividaddocenteperiodo=usr.subactividad, subactividad__actividaddetalledistributivo__vigente=True, subactividad__subactividaddocenteperiodo__criterio__status=True, subactividad__subactividaddocenteperiodo__status=True, subactividad__subactividaddocenteperiodo__actividad__criterio__status=True)
                        else:
                            if doc := usr.criteriodocenciaperiodo:
                                filtro_evidencia = Q(criterio__criteriodocenciaperiodo=doc)
                            if inv := usr.criterioinvestigacionperiodo:
                                filtro_evidencia = Q(criterio__criterioinvestigacionperiodo=inv)
                            if ges := usr.criteriogestionperiodo:
                                filtro_evidencia = Q(criterio__criteriogestionperiodo=ges)

                        if filtro_evidencia:
                            if just_they := usr.usercriteriorevisorintegrantes_set.filter(status=True).values_list('profesor', flat=True):
                                filtro_evidencia &= Q(criterio__distributivo__profesor__in=just_they)
                            lista_filtros += [filtro_evidencia]

                    if lista_filtros.__len__():
                        filters2 = Q(lista_filtros[0])
                        for value in lista_filtros[1:]:
                            filters2 |= Q(value)

                    if filters2:
                        filters &= filters2

                    if not usuariorevision:
                        filters = Q(pk=None)

                    evidencias = EvidenciaActividadDetalleDistributivo.objects.filter(filters).exclude(exclude1)
                    meses = [{'name': nombremes(m), 'val': m} for m in set(evidencias.values_list('hasta__month', flat=True).order_by('hasta').distinct())]
                    total = evidencias.count()
                    if criterio := request.GET.get('criterio', '0'):
                        if usr := UserCriterioRevisor.objects.filter(id=criterio).first():
                            if usr.subactividad:
                                filters &= Q(subactividad__subactividaddocenteperiodo=usr.subactividad)
                            else:
                                if usr.criteriodocenciaperiodo:
                                    filters &= Q(criterio__criteriodocenciaperiodo=usr.criteriodocenciaperiodo)
                                if usr.criterioinvestigacionperiodo:
                                    filters &= Q(criterio__criterioinvestigacionperiodo=usr.criterioinvestigacionperiodo)
                                if usr.criteriogestionperiodo:
                                    filters &= Q(criterio__criteriogestionperiodo=usr.criteriogestionperiodo)
                            data['criterio_id'] = usr.pk
                            url_vars += f"&criterio={usr.pk}"

                    if mes := int(request.GET.get('mes', '0')):
                        filters &= Q(hasta__month=mes)
                        data['eMes'] = mes
                        url_vars += f"&mes={mes}"

                    if 's' in request.GET and request.GET['s'].strip():
                        search = request.GET['s'].strip()
                        url_vars += f'&s={search}'
                        ss = search.split(' ')
                        if ss.__len__() == 1:
                            filters &= Q(Q(criterio__distributivo__profesor__persona__nombres__icontains=search) | Q(criterio__distributivo__profesor__persona__apellido1__icontains=search) | Q(criterio__distributivo__profesor__persona__apellido2__icontains=search) | Q(criterio__distributivo__profesor__persona__cedula__icontains=search) | Q(criterio__distributivo__profesor__persona__pasaporte__icontains=search))
                        if ss.__len__() == 2:
                            filters &= Q(Q(criterio__distributivo__profesor__persona__apellido1__icontains=ss[0]) & Q(criterio__distributivo__profesor__persona__apellido2__icontains=ss[1]))
                        if ss.__len__() >= 4:
                            filters &= Q(criterio__criteriodocenciaperiodo__criterio__nombre__icontains=search) | Q(criterio__criterioinvestigacionperiodo__criterio__nombre__icontains=search) | Q(criterio__criteriogestionperiodo__criterio__nombre__icontains=search)

                    exclude2 = Q(criterio__criterioinvestigacionperiodo__criterio__id__in=list(map(int, variable_valor('CRITERIO_DIRECTOR_GRUPO_INVESTIGACION')))) if usuariorevision.values('criterioinvestigacionperiodo').exists() else Q(status=False)
                    paging = MiPaginador(evidencias.filter(filters).exclude(exclude2).exclude(exclude1).order_by('-hasta','-fecha_creacion'), numerofilas)
                    p, numerofilasguiente = 1, 0
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

                    data['tipo'] = tipoencriptado
                    url_vars += f'&tipo={tipoencriptado}'
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['numerofilasguiente'] = numerofilasguiente
                    data['numeropagina'] = p
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_vars"] = url_vars
                    data['listaevidencias'] = page.object_list
                    data['tipo_int'] = tipoestado
                    data['meses'] = meses
                    data['total'] = total
                    data['usuariorevision'] = usuariorevision
                    data['roles'] = roles
                    data['estadoaprobacion'] = ESTADO_APROBACION_EVIDENCIA
                    return render(request, "adm_revisioncriteriosactividades/listadoevidencias.html", data)
                except Exception as ex:
                    return HttpResponseRedirect('/adm_revisioncriteriosactividades?info=Error de conexión. %s' % ex.__str__())

            if action == 'usuariosactividades':
                try:
                    if not es_administrador: return HttpResponseRedirect('/adm_revisioncriteriosactividades?info=No tiene permiso para visualizar esta pantalla')
                    data['title'] = 'Listado de criterios y actividades'
                    data['criterios_docencia'] = CriterioDocenciaPeriodo.objects.filter(Q(Q(subirevidencia=True) | Q(es_actividadmacro=True)) & Q(periodo=periodo, criterio__tipo=1, status=True)).annotate(totalrevisores=Count('usercriteriorevisor',distinct=True, status=True, filter=Q(usercriteriorevisor__tiporevisor=1), usercriteriorevisor__criteriodocenciaperiodo=False)).order_by('actividad_id')
                    data['criterios_investigacion'] = CriterioInvestigacionPeriodo.objects.filter(Q(Q(subirevidencia=True) | Q(es_actividadmacro=True)) & Q(periodo=periodo, status=True)).annotate(totalrevisores=Count('usercriteriorevisor',distinct=True, status=True, filter=Q(usercriteriorevisor__tiporevisor=1), usercriteriorevisor__criterioinvestigacionperiodo=False)).order_by('actividad_id')
                    data['criterios_gestion'] = CriterioGestionPeriodo.objects.filter(periodo=periodo, subirevidencia=True, status=True).annotate(totalrevisores=Count('usercriteriorevisor',distinct=True, status=True, filter=Q(usercriteriorevisor__tiporevisor=1), usercriteriorevisor__criteriogestionperiodo=False)).order_by('actividad_id')
                    data['criterios_vinculacion'] = CriterioDocenciaPeriodo.objects.filter(periodo=periodo, subirevidencia=True, criterio__tipo=2, status=True).annotate(totalrevisores=Count('usercriteriorevisor',distinct=True, status=True, filter=Q(usercriteriorevisor__tiporevisor=1), usercriteriorevisor__criteriodocenciaperiodo=False)).order_by('actividad_id')
                    data['t'] = None
                    if 't' in request.GET:
                        data['t'] = int(request.GET['t'])
                    data['tiporevisor'] = encrypt('1')
                    listadomeses = []
                    fechas_mensuales = list(rrule(MONTHLY, dtstart=periodo.inicio, until=periodo.fin))
                    for fechames in fechas_mensuales:
                        listadomeses.append(fechames)
                    data['listadomeses'] = listadomeses
                    return render(request, "adm_revisioncriteriosactividades/criteriosactividades.html", data)
                except Exception as ex:
                    pass

            if action == 'usuariosbitacora':
                try:
                    if not es_administrador: return HttpResponseRedirect('/adm_revisioncriteriosactividades?info=No tiene permiso para visualizar esta pantalla')
                    data['title'] = 'USUARIOS REVISA BITÁCORAS'
                    data['criterios_docencia'] = CriterioDocenciaPeriodo.objects.filter(periodo=periodo, llenarbitacora=True, criterio__tipo=1, status=True).annotate(totalrevisores=Count('usercriteriorevisor',distinct=True, status=True,  filter=Q(usercriteriorevisor__tiporevisor=2), usercriteriorevisor__criteriodocenciaperiodo=False)).order_by('actividad_id')
                    data['criterios_investigacion'] = CriterioInvestigacionPeriodo.objects.filter(periodo=periodo, llenarbitacora=True, status=True).annotate(totalrevisores=Count('usercriteriorevisor',distinct=True, status=True, filter=Q(usercriteriorevisor__tiporevisor=2), usercriteriorevisor__criterioinvestigacionperiodo=False)).order_by('actividad_id')
                    data['criterios_gestion'] = CriterioGestionPeriodo.objects.filter(periodo=periodo, llenarbitacora=True, status=True).annotate(totalrevisores=Count('usercriteriorevisor',distinct=True, status=True, filter=Q(usercriteriorevisor__tiporevisor=2), usercriteriorevisor__criteriogestionperiodo=False)).order_by('actividad_id')
                    data['criterios_vinculacion'] = CriterioDocenciaPeriodo.objects.filter(periodo=periodo, llenarbitacora=True, criterio__tipo=2, status=True).annotate(totalrevisores=Count('usercriteriorevisor',distinct=True, status=True, filter=Q(usercriteriorevisor__tiporevisor=2), usercriteriorevisor__criteriodocenciaperiodo=False)).order_by('actividad_id')
                    data['t'] = None
                    if 't' in request.GET:
                        data['t'] = int(request.GET['t'])
                    data['tiporevisor'] = encrypt('2')
                    data['estados'] = ESTADO_REVISION
                    data['meses'] = MESES_CHOICES
                    return render(request, "adm_revisioncriteriosactividades/criteriosactividades.html", data)
                except Exception as ex:
                    pass

            if action == 'legalizarevidenciamanual':
                try:
                    from postulaciondip.forms import ArchivoInvitacionForm
                    data['id'] = request.GET.get('id')
                    data['form2'] = ArchivoInvitacionForm()
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.rollback()
                    return JsonResponse({"result": False, 'mensaje': f"Error de conexión. {ex.__str__()}"})

            if action == 'actualizarevidenciamanual':
                try:
                    from postulaciondip.forms import ArchivoInvitacionForm
                    data['id'] = request.GET.get('id')
                    data['form2'] = ArchivoInvitacionForm()
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.rollback()
                    return JsonResponse({"result": False, 'mensaje': f"Error de conexión. {ex.__str__()}"})

            if action == 'legalizarevidenciamasivo':
                try:
                    from postulaciondip.forms import FirmaElectronicaIndividualForm
                    data['form2'] = FirmaElectronicaIndividualForm()
                    data['id'] = ", ".join(request.GET.getlist('data[]', None))
                    template = get_template("adm_revisioncriteriosactividades/modal/firmardocumento.html")
                    return JsonResponse({"result": "ok", 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'add':
                try:
                    data['title'] = u'Adicionar Usuario'
                    form = UsuarioRevisaEvidenciaDocenteForm()
                    ROL_USUARIO = TIPO_ROL
                    codigoactividad, nombreactividad, listadopersonas, criterio = None, None, None, None
                    subactividad = SubactividadDocentePeriodo.objects.filter(id=request.GET['ids']).first()
                    tiporevisor, tipocriterio = int(request.GET['tiporevisor']), int(request.GET['tipocriterio'])
                    if tipocriterio == 1:
                        criterio = CriterioDocenciaPeriodo.objects.get(pk=request.GET['id'])
                        codigoactividad = criterio.id
                        nombreactividad = criterio.criterio.nombre
                        listadopersonas = criterio.usercriteriorevisor_set.filter(tiporevisor=tiporevisor, subactividad=subactividad, status=True)
                    if tipocriterio == 2:
                        criterio = CriterioInvestigacionPeriodo.objects.get(pk=request.GET['id'])
                        codigoactividad = criterio.id
                        nombreactividad = criterio.criterio.nombre
                        listadopersonas = criterio.usercriteriorevisor_set.filter(tiporevisor=tiporevisor, subactividad=subactividad, status=True)
                    if tipocriterio == 3:
                        criterio = CriterioGestionPeriodo.objects.get(pk=request.GET['id'])
                        codigoactividad = criterio.id
                        nombreactividad = criterio.criterio.nombre
                        listadopersonas = criterio.usercriteriorevisor_set.filter(tiporevisor=tiporevisor, subactividad=subactividad, status=True)
                    if tipocriterio == 4:
                        criterio = CriterioDocenciaPeriodo.objects.get(pk=request.GET['id'])
                        codigoactividad = criterio.id
                        nombreactividad = criterio.criterio.nombre
                        listadopersonas = criterio.usercriteriorevisor_set.filter(tiporevisor=tiporevisor, subactividad=subactividad, status=True)
                    # data['listadopersonas'] = listadopersonas
                    if tiporevisor == 2:
                        ROL_USUARIO = list(filter(lambda x: x[0] != 2, TIPO_ROL))
                        form.fields['rol'].choices = ROL_USUARIO

                    data['codigoactividad'] = codigoactividad
                    data['nombreactividad'] = nombreactividad
                    data['tiporevisor'] = tiporevisor
                    data['tipocriterio'] = int(request.GET['tipocriterio'])
                    data['form'] = form
                    data['roles'] = ROL_USUARIO
                    data['subactividad'] = subactividad
                    data['data'] = [{'rol': rol[1], 'values': listadopersonas.filter(rol=rol[0])} for rol in ROL_USUARIO] if listadopersonas else []
                    habilita_masivos = False
                    if criterio and criterio.criterio.id.__str__() in variable_valor('USER_CRITERIOS_IDS'): habilita_masivos = True
                    data['servidor'] = 1 if criterio and int(criterio.criterio.id) == 186 else 2 #1:decanos; 2:directores
                    data['habilita_masivos'] = habilita_masivos
                    template = get_template('adm_revisioncriteriosactividades/addusuario.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'adddocentesrevision':
                try:
                    data['revisor'] = revisor = UserCriterioRevisor.objects.get(pk=request.GET.get('pk'))
                    criterio, tipo = None, 0
                    if c := revisor.criteriodocenciaperiodo: criterio, tipo = c, 1
                    if c := revisor.criterioinvestigacionperiodo: criterio, tipo = c, 2
                    if c := revisor.criteriogestionperiodo: criterio, tipo = c, 3

                    data['integrantes'] = UserCriterioRevisorIntegrantes.objects.filter(usuariorevisor=revisor, status=True)
                    data['tipo'] = tipo
                    data['id'] = revisor.pk
                    data['criterio'] = criterio
                    data['subactividad'] = SubactividadDocentePeriodo.objects.filter(id=request.GET.get('ids')).first()
                    template = get_template('adm_revisioncriteriosactividades/addliderarea.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': u"Error de conexión. %s" % ex.__str__()})

            if action == 'buscardocente':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    filtro = Q(persona__usuario__isnull=False, status=True)

                    if len(s) == 1:
                        filtro &= ((Q(persona__nombres__icontains=q) | Q(persona__apellido1__icontains=q) | Q(persona__cedula__icontains=q) | Q(persona__apellido2__icontains=q) | Q(persona__cedula__contains=q)))
                    elif len(s) == 2:
                        filtro &= ((Q(persona__apellido1__contains=s[0]) & Q(persona__apellido2__contains=s[1])) | (Q(persona__nombres__icontains=s[0]) & Q(persona__nombres__icontains=s[1])) | (Q(persona__nombres__icontains=s[0]) & Q(persona__apellido1__contains=s[1])))
                    else:
                        filtro &= ((Q(persona__nombres__contains=s[0]) & Q(persona__apellido1__contains=s[1]) & Q(persona__apellido2__contains=s[2])) | (Q(persona__nombres__contains=s[0]) & Q(persona__nombres__contains=s[1]) & Q(persona__apellido1__contains=s[2])))

                    t, c = int(request.GET.get('t', 0)), int(request.GET.get('c', 0))
                    _filterdist = Q(distributivo__periodo=periodo, distributivo__status=True, distributivo__activo=True)
                    if t == 1: _filterdist &= Q(criteriodocenciaperiodo__id=c)
                    if t == 2: _filterdist &= Q(criterioinvestigacionperiodo__id=c)
                    if t == 3: _filterdist &= Q(criteriogestionperiodo__id=c)
                    if t == 4: _filterdist &= Q(criteriovinculacionperiodo__id=c)

                    criterio_attr = ['criteriodocenciaperiodo__id', 'criterioinvestigacionperiodo__id', 'criteriogestionperiodo__id', 'criteriovinculacionperiodo__id'][t - 1]

                    _exclude = UserCriterioRevisorIntegrantes.objects.filter(**{f'usuariorevisor__{criterio_attr}': c, 'status': True}).values_list('profesor_id', flat=True)

                    _profesores = DetalleDistributivo.objects.filter(_filterdist).values_list('distributivo__profesor', flat=True)
                    filtro &=  Q(id__in=_profesores)

                    per = Profesor.objects.filter(filtro).exclude(id__in=_exclude).exclude(id__in=json.loads(request.GET['list'])).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres').distinct()[:15]
                    return JsonResponse({"result": "ok", "results": [{"id": x.id, "name": "%s %s" % (f"<img src='{x.persona.get_foto()}' width='25' height='25' style='border-radius: 20%;' alt='...'>", x.persona.nombre_completo_inverso())} for x in per]})
                except Exception as ex:
                    pass

            elif action == 'buscar_usuario':
                try:
                    if 'q' in request.GET:
                        search = request.GET['q'].upper().strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            query = Persona.objects.filter(administrativo__isnull=False).filter(Q(nombres__icontains=search) |
                                                                                                Q(apellido1__icontains=search) |
                                                                                                Q(apellido2__icontains=search) |
                                                                                                Q(cedula__icontains=search) |
                                                                                                Q(pasaporte__icontains=search), real=True).distinct()
                        elif len(ss) == 2:
                            query = Persona.objects.filter(Q(apellido1__icontains=ss[0]) & Q(apellido2__icontains=ss[1]), real=True).distinct()
                        elif len(ss) == 3:
                            query = Persona.objects.filter(Q(apellido1__icontains=ss[0]) | Q(apellido2__icontains=ss[1]) | Q(apellido2__icontains=ss[2]), real=True).distinct()
                        else:
                            query = Persona.objects.filter(Q(apellido1__icontains=ss[0]) | Q(apellido2__icontains=ss[1]) | Q(apellido2__icontains=ss[2]) | Q(apellido2__icontains=ss[3]), real=True).distinct()
                    else:
                        query = Persona.objects.filter(Q(administrativo__isnull=False) | Q(profesor__isnull=False), real=True).distinct()
                    data = {"results": [{"id": x.id, "name": x.nombre_completo_inverso()} for x in query]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": 'Error al obtener los datos.'})

            if action == 'detalleevidencia':
                try:
                    data = {}
                    detalle = EvidenciaActividadDetalleDistributivo.objects.get(pk=int(request.GET['id']))
                    data['listadoanexos'] = detalle.anexoevidenciaactividad_set.filter(status=True)
                    data['permiso'] = detalle
                    data['aprobador'] = persona
                    data['fecha'] = datetime.now().date()
                    data['readonly'] = int(encrypt(request.GET.get('readonly', encrypt(1)))) == 1
                    data['detallepermiso'] = detalle.historialaprobacionevidenciaactividad_set.all()
                    template = get_template("adm_revisioncriteriosactividades/detalle_aprobarevidencia.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'firmadocumento':
                try:
                    detalle = EvidenciaActividadDetalleDistributivo.objects.get(id=request.GET['id'])
                    archivo = detalle.archivo.url if detalle.archivo else None
                    if detalle.archivofirmado:
                        archivo = detalle.archivofirmado.url

                    data['archivo'] = archivo
                    data['url_archivo'] = '{}{}'.format(dominio_sistema, archivo)
                    data['id_objeto'] = detalle.id
                    data['action_firma'] = 'firmadocumento'
                    template = get_template("formfirmaelectronica.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'firmadocumentosalud':
                try:
                    data['val_extra'] = tipo_evidencia = int(request.GET['idex'])
                    evidencia = EstadoEvidenciaSalud.objects.get(id=int(encrypt(request.GET['id'])))
                    archivo = None
                    if evidencia.planificacionmensual and tipo_evidencia == 1: #PlanificacionMensualSalud
                        archivo = evidencia.planificacionmensual.archivo.url if evidencia.planificacionmensual.archivo else None
                        if not archivo:
                            raise NameError('No existe archivo evidencia de Planificación Mensual')

                    data['archivo'] = archivo
                    data['url_archivo'] = '{}{}'.format(dominio_sistema, archivo)
                    data['id_objeto'] = evidencia.id
                    data['action_firma'] = action
                    template = get_template("formfirmaelectronica.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": f"Error al obtener los datos. {ex}"})

            if action == 'descargarevidenciasfaltantes':
                try:
                    mesconsulta = request.GET['mes']
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    nombre_archivo = 'evidenciasfaltantes_' + str(nombremes(int(mesconsulta)).upper()) + '.xls'
                    wb = Workbook(encoding='utf-8')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = f'attachment; filename={nombre_archivo}'
                    ws = wb.add_sheet('faltantes_' + str(nombremes(int(mesconsulta)).upper()))
                    columns = [
                        (u"CRITERIO", 3500),
                        (u"CEDULA", 3000),
                        (u"DOCENTE.", 15000),
                        (u"TIENE EVIDENCIA.", 3500),
                        (u"ESTADO EVIDENCIA.", 3500),
                        (u"ACTIVIDAD", 4000),
                    ]
                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    row_num = 2
                    listadistributivodoc = DetalleDistributivo.objects.filter(distributivo__periodo_id=periodo, criteriodocenciaperiodo__subirevidencia=True, status=True).order_by('criteriodocenciaperiodo__criterio__tipo','distributivo__profesor__persona__apellido1')
                    listadistributivoinv = DetalleDistributivo.objects.filter(distributivo__periodo_id=periodo, criterioinvestigacionperiodo__subirevidencia=True, status=True).order_by('distributivo__profesor__persona__apellido1')
                    listadistributivoges = DetalleDistributivo.objects.filter(distributivo__periodo_id=periodo, criteriogestionperiodo__subirevidencia=True, status=True).order_by('distributivo__profesor__persona__apellido1')
                    for listadis in listadistributivodoc:
                        tieneevidencia = 'NO'
                        estadoevidencia = '-'
                        if listadis.evidenciaactividaddetalledistributivo_set.filter(hasta__month=mesconsulta, status=True):
                            tieneevidencia = 'SI'
                            estadoevidencia = listadis.evidenciaactividaddetalledistributivo_set.filter(hasta__month=mesconsulta, status=True)[0].get_estadoaprobacion_display()
                        campo1 = listadis.criteriodocenciaperiodo.criterio.get_tipo_display()
                        campo2 = listadis.distributivo.profesor.persona.cedula
                        campo3 = listadis.distributivo.profesor.persona.apellido1 + ' ' + listadis.distributivo.profesor.persona.apellido2 + ' ' + listadis.distributivo.profesor.persona.nombres
                        campo4 = listadis.criteriodocenciaperiodo.criterio.nombre

                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, tieneevidencia, font_style2)
                        ws.write(row_num, 4, estadoevidencia, font_style2)
                        ws.write(row_num, 5, campo4, font_style2)
                        row_num += 1
                    for listadis in listadistributivoinv:
                        tieneevidencia = 'NO'
                        estadoevidencia = '-'
                        if listadis.evidenciaactividaddetalledistributivo_set.filter(hasta__month=mesconsulta, status=True):
                            tieneevidencia = 'SI'
                            estadoevidencia = listadis.evidenciaactividaddetalledistributivo_set.filter(hasta__month=mesconsulta, status=True)[0].get_estadoaprobacion_display()
                        campo1 = listadis.distributivo.profesor.persona.cedula
                        campo2 = listadis.distributivo.profesor.persona.apellido1 + ' ' + listadis.distributivo.profesor.persona.apellido2 + ' ' + listadis.distributivo.profesor.persona.nombres
                        campo3 = listadis.criterioinvestigacionperiodo.criterio.nombre

                        ws.write(row_num, 0, 'INVESTIGACIÓN', font_style2)
                        ws.write(row_num, 1, campo1, font_style2)
                        ws.write(row_num, 2, campo2, font_style2)
                        ws.write(row_num, 3, tieneevidencia, font_style2)
                        ws.write(row_num, 4, estadoevidencia, font_style2)
                        ws.write(row_num, 5, campo3, font_style2)
                        row_num += 1
                    for listadis in listadistributivoges:
                        tieneevidencia = 'NO'
                        estadoevidencia = '-'
                        if listadis.evidenciaactividaddetalledistributivo_set.filter(hasta__month=mesconsulta, status=True):
                            tieneevidencia = 'SI'
                            estadoevidencia = listadis.evidenciaactividaddetalledistributivo_set.filter(hasta__month=mesconsulta, status=True)[0].get_estadoaprobacion_display()
                        campo1 = listadis.distributivo.profesor.persona.cedula
                        campo2 = listadis.distributivo.profesor.persona.apellido1 + ' ' + listadis.distributivo.profesor.persona.apellido2 + ' ' + listadis.distributivo.profesor.persona.nombres
                        campo3 = listadis.criteriogestionperiodo.criterio.nombre

                        ws.write(row_num, 0, 'GESTIÓN', font_style2)
                        ws.write(row_num, 1, campo1, font_style2)
                        ws.write(row_num, 2, campo2, font_style2)
                        ws.write(row_num, 3, tieneevidencia, font_style2)
                        ws.write(row_num, 4, estadoevidencia, font_style2)
                        ws.write(row_num, 5, campo3, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            if action == 'descargarusuariosrevisores':
                try:
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    nombre_archivo = 'revisores_' + random.randint(1, 10000).__str__() + '.xls'
                    wb = Workbook(encoding='utf-8')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = f'attachment; filename={nombre_archivo}'
                    ws = wb.add_sheet('revisores')
                    columns = [
                        (u"CRITERIO", 3500),
                        (u"CEDULA", 3000),
                        (u"DOCENTE.", 15000),
                        (u"ACTIVIDAD", 4000),
                    ]
                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    row_num = 2
                    listadistributivodoc = periodo.criteriodocenciaperiodo_set.filter(subirevidencia=True, status=True).order_by('criterio__tipo','criterio__nombre')
                    listadistributivoinv = periodo.criterioinvestigacionperiodo_set.filter(subirevidencia=True, status=True).order_by('criterio__nombre')
                    listadistributivoges = periodo.criteriogestionperiodo_set.filter(subirevidencia=True, status=True).order_by('criterio__nombre')
                    for listadis in listadistributivodoc:
                        if listadis.usercriteriorevisor_set.filter(status=True):
                            for urevisor in listadis.usercriteriorevisor_set.filter(status=True):
                                campo1 = listadis.criterio.get_tipo_display()
                                campo2 = urevisor.persona.cedula
                                campo3 = urevisor.persona.apellido1 + ' ' + urevisor.persona.apellido2 + ' ' + urevisor.persona.nombres
                                campo4 = listadis.criterio.nombre

                                ws.write(row_num, 0, campo1, font_style2)
                                ws.write(row_num, 1, campo2, font_style2)
                                ws.write(row_num, 2, campo3, font_style2)
                                ws.write(row_num, 3, campo4, font_style2)
                                row_num += 1
                        else:
                            campo1 = listadis.criterio.get_tipo_display()
                            campo2 = '-'
                            campo3 = '-'
                            campo4 = listadis.criterio.nombre

                            ws.write(row_num, 0, campo1, font_style2)
                            ws.write(row_num, 1, campo2, font_style2)
                            ws.write(row_num, 2, campo3, font_style2)
                            ws.write(row_num, 3, campo4, font_style2)
                            row_num += 1
                    for listadis in listadistributivoinv:
                        if listadis.usercriteriorevisor_set.filter(status=True):
                            for urevisor in listadis.usercriteriorevisor_set.filter(status=True):
                                campo1 = 'INVESTIGACIÓN'
                                campo2 = urevisor.persona.cedula
                                campo3 = urevisor.persona.apellido1 + ' ' + urevisor.persona.apellido2 + ' ' + urevisor.persona.nombres
                                campo4 = listadis.criterio.nombre

                                ws.write(row_num, 0, campo1, font_style2)
                                ws.write(row_num, 1, campo2, font_style2)
                                ws.write(row_num, 2, campo3, font_style2)
                                ws.write(row_num, 3, campo4, font_style2)
                                row_num += 1
                        else:
                            campo1 = 'INVESTIGACIÓN'
                            campo2 = '-'
                            campo3 = '-'
                            campo4 = listadis.criterio.nombre

                            ws.write(row_num, 0, campo1, font_style2)
                            ws.write(row_num, 1, campo2, font_style2)
                            ws.write(row_num, 2, campo3, font_style2)
                            ws.write(row_num, 3, campo4, font_style2)
                            row_num += 1
                    for listadis in listadistributivoges:
                        if listadis.usercriteriorevisor_set.filter(status=True):
                            for urevisor in listadis.usercriteriorevisor_set.filter(status=True):
                                campo1 = 'GESTIÓN'
                                campo2 = urevisor.persona.cedula
                                campo3 = urevisor.persona.apellido1 + ' ' + urevisor.persona.apellido2 + ' ' + urevisor.persona.nombres
                                campo4 = listadis.criterio.nombre

                                ws.write(row_num, 0, campo1, font_style2)
                                ws.write(row_num, 1, campo2, font_style2)
                                ws.write(row_num, 2, campo3, font_style2)
                                ws.write(row_num, 3, campo4, font_style2)
                                row_num += 1
                        else:
                            campo1 = 'GESTIÓN'
                            campo2 = '-'
                            campo3 = '-'
                            campo4 = listadis.criterio.nombre

                            ws.write(row_num, 0, campo1, font_style2)
                            ws.write(row_num, 1, campo2, font_style2)
                            ws.write(row_num, 2, campo3, font_style2)
                            ws.write(row_num, 3, campo4, font_style2)
                            row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'updatelg':
                from sagest.models import LogMarcada, LogDia
                hoy = datetime.now().date()
                try:
                    mensaje = ''
                    persona = request.session.get('persona')

                    a = int(aio) if (aio := request.GET.get('a', hoy.year)) else hoy.year
                    m = int(mes) if (mes := request.GET.get('m', hoy.year)) else hoy.month
                    d = int(dia) if (dia := request.GET.get('d', hoy.year)) else hoy.day
                    fecha = datetime(a, m, d).date()

                    dia = LogDia.objects.filter(persona=persona, fecha=fecha, status=True).first()
                    if not dia: dia = LogDia(persona=persona, fecha=fecha, jornada_id=1)

                    if t := int(request.GET.get('t', 0)):
                        hmm = []
                        if t == 1: hmm = [8, 0, 3]
                        if t == 2: hmm = [13, 0, 3]
                        if t == 3: hmm = [13, 50, 59]
                        if t == 4: hmm = [17, 20, 30]
                        if hmm.__len__():
                            input = {'logdia': dia, 'secuencia': t, 'time': datetime(a, m, d, hmm[0], random.randint(hmm[1], hmm[2]), random.randint(0, 59), random.randint(189000, 976248))}
                            LogMarcada(**input).save()

                            cantidadmarcadas = dia.logmarcada_set.filter(status=True).values('id').count()
                            if cantidadmarcadas in (2, 4):
                                dia.cantidadmarcadas = cantidadmarcadas
                                dia.procesado = True
                                dia.save()
                    else:
                        if lg := LogMarcada.objects.filter(logdia=dia, time__hour__gte=8, time__hour__lte=12, status=True).first():
                            if lg.time.time() > time(8, 6):
                                v = lg.time.date()
                                lg.time = datetime(v.year, v.month, v.day, 8, random.randint(0, 4), random.randint(0, 59), random.randint(289000, 876248))
                                lg.usuario_creacion_id = persona.usuario_id if not lg.usuario_creacion_id == 1 else 1
                                lg.save()
                                mensaje += f"{lg.time.__str__()}, "

                    return JsonResponse({'result': True, 'mensaje': mensaje})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': ex.__str__()})

            if action == 'aprobadores-sin-actividad-asociada':
                try:
                    return aprobadores_sin_actividad_asociada(request)
                except Exception as ex:
                    pass

            if action == 'revisionbitacora':
                try:
                    data['title'] = u"Revisión de bitacora de actividades"
                    bitacora = BitacoraActividadDocente.objects.get(id=request.GET['id'])

                    _get_horas_minutos = lambda th: (th.total_seconds() / 3600).__str__().split('.')
                    _return = ''
                    for x in request.GET.keys():
                        if not x == 'action': _return += f'&{x}={request.GET[x]}'

                    data['return'] = '?action=bitacoras' + _return.replace(',', '%2C')
                    data['registrosbitacora'] = detallebitacora = DetalleBitacoraDocente.objects.filter(bitacoradocente=bitacora, status=True).annotate(diferencia=ExpressionWrapper(F('horafin') - F('horainicio'), output_field=TimeField())).order_by('fecha', 'horainicio', 'horafin')

                    if th := detallebitacora.aggregate(total=Sum('diferencia'))['total']:
                        horas, minutos = _get_horas_minutos(th)
                        data['total_horas'] = float("%s.%s" % (horas, round(float('0.' + minutos) * 60)))

                    if th := detallebitacora.filter(estadoaprobacion=2).aggregate(total=Sum('diferencia'))['total']:
                        horas, minutos = _get_horas_minutos(th)
                        data['total_aprobadas'] = float("%s.%s" % (horas, round(float('0.' + minutos) * 60)))

                    if th := detallebitacora.filter(estadoaprobacion=3).aggregate(total=Sum('diferencia'))['total']:
                        horas, minutos = _get_horas_minutos(th)
                        data['total_rechazadas'] = float("%s.%s" % (horas, round(float('0.' + minutos) * 60)))

                    diasclas = ClaseActividad.objects.filter(detalledistributivo=bitacora.criterio, detalledistributivo__distributivo__profesor=bitacora.criterio.distributivo.profesor, status=True).values_list('dia', 'turno_id').order_by('inicio', 'dia', 'turno__comienza')
                    dt, end, step = bitacora.fechaini, bitacora.fechafin, timedelta(days=1)
                    result = []
                    while dt <= end:
                        if not periodo.dias_nolaborables(dt):
                            for dclase in diasclas:
                                if dt.isocalendar()[2] == dclase[0]:
                                    result.append(dt.strftime('%Y-%m-%d'))
                        dt += step

                    data['bitacora'] = bitacora
                    data['total_planificadas'] = result.__len__()
                    data['revision'] = request.GET.get('r', 0)
                    data['nombre'] = persona.nombres.__str__().split()[0]
                    return render(request, "adm_revisioncriteriosactividades/revisionbitacora.html", data)
                except Exception as ex:
                    pass

            if action == 'validar-bitacoras-mes':
                try:
                    now = datetime.now().date()
                    mes = int(request.GET.get('m', now.month))

                    f_ini = date(now.year, mes, 1)
                    f_fin = date(now.year, mes, calendar.monthrange(now.year, mes)[1])

                    for criterio in DetalleDistributivo.objects.filter(Q(Q(criteriodocenciaperiodo__llenarbitacora=True) | Q(criterioinvestigacionperiodo__llenarbitacora=True) | Q(criteriogestionperiodo__llenarbitacora=True)) & Q(distributivo__periodo=periodo, distributivo__activo=True, status=True)):
                        if bitacora := BitacoraActividadDocente.objects.filter(criterio=criterio, fechaini=f_ini, fechafin__month=mes, profesor=criterio.distributivo.profesor, estadorevision__in=[1, 2]).first():
                            DetalleBitacoraDocente.objects.filter(bitacoradocente=bitacora, estadoaprobacion=1, status=True).update(estadoaprobacion=2, usuario_modificacion=1)
                            bitacora.estadorevision = 3
                            bitacora.save(request, update_fields=['estadorevision'])

                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    pass

            if action == 'actualiza_estado_revision':
                try:
                    b = BitacoraActividadDocente.objects.get(pk=int(request.GET.get('pk', 0)))
                    b.estadorevision = int(request.GET.get('e', 1))
                    b.save()

                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    return JsonResponse({'result': 'bad', 'mensaje': f'{ex=}'})

            if action == 'actualizar_fecha_bitacora':
                try:

                    olddate = request.GET.get('mm', 12)
                    newdate = datetime(int(request.GET.get('y', 2023)), int(request.GET.get('m', 12)), int(request.GET.get('d', 15)))

                    c = BitacoraActividadDocente.objects.filter(fechafin__month=olddate).update(fechafin=newdate)

                    return JsonResponse({'result': 'ok', 'mensaje': f'{c} filas afectadas'})
                except Exception as ex:
                    ...

            if action == 'habilitaregistrotardio':
                try:
                    b = BitacoraActividadDocente.objects.get(pk=request.GET['pk'])
                    b.estadorevision=1
                    b.registrotardio = True
                    b.save(request)
                    h = HistorialBitacoraActividadDocente(bitacora=b, persona=persona, estadorevision=1, fecharegistrotardio=datetime.now().date())
                    h.save(request)
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    pass

            elif action == 'evidenciassalud':
                try:
                    data['title'] = u'Listado evidencias salud'
                    data['subtitle'] = u'Planificación mensual docentes'
                    ids = None
                    search, filtro, estado, url_vars = request.GET.get('s', ''), Q(status=True, planificacionmensual__isnull=False), int(encrypt(request.GET.get('estado', encrypt(2)))), ''
                    registros = EstadoEvidenciaSalud.objects.filter(filtro)
                    meses = [{'name': nombremes(m), 'val': m} for m in set(registros.values_list('planificacionmensual__mes', flat=True).order_by('planificacionmensual__mes').distinct())]

                    if search:
                        data['s'] = search = request.GET['s'].strip()
                        ss = search.split(' ')
                        url_vars += f"&s={search}"
                        if len(ss) == 1 or len(ss) > 3:
                            filtro = filtro & (
                                Q(planificacionmensual__supervisor__persona__cedula__icontains=search) | Q(planificacionmensual__supervisor__persona__pasaporte__icontains=search) |
                                Q(planificacionmensual__supervisor__persona__nombres__icontains=search) |
                                Q(planificacionmensual__supervisor__persona__apellido1__icontains=search) | Q(planificacionmensual__supervisor__persona__apellido2__icontains=search) |
                                Q(planificacionmensual__itinerariomalla__nombre=search)
                            )
                        elif len(ss) == 2:
                            filtro = filtro & (
                                (Q(planificacionmensual__supervisor__persona__nombres__icontains=ss[0]) & Q(planificacionmensual__supervisor__persona__nombres__icontains=ss[1]))|
                                (Q(planificacionmensual__supervisor__persona__nombres__icontains=ss[0]) & Q(planificacionmensual__supervisor__persona__apellido1__icontains=ss[1]))|
                                (Q(planificacionmensual__supervisor__persona__apellido1__icontains=ss[0]) & Q(planificacionmensual__supervisor__persona__nombres__icontains=ss[1]))|
                                (Q(planificacionmensual__supervisor__persona__apellido1__icontains=ss[0]) & Q(planificacionmensual__supervisor__persona__apellido2__icontains=ss[1])) |
                                (Q(planificacionmensual__itinerariomalla__nombre=ss[0]) & Q(planificacionmensual__itinerariomalla__nombre=ss[1]))
                            )
                        elif len(ss) == 3:
                            filtro = filtro & (
                                    (Q(planificacionmensual__itinerariomalla__nombre=ss[0]) & Q(planificacionmensual__itinerariomalla__nombre=ss[1]) & Q(planificacionmensual__itinerariomalla__nombre=ss[2]))
                            )

                    if 'id' in request.GET:
                        ids = int(request.GET['id'])
                        filtro = filtro & (Q(status=True))

                    if mes := int(request.GET.get('m', '0')):
                        filtro &= Q(planificacionmensual__mes=mes)
                        data['m'] = mes
                        url_vars += f"&m={mes}"

                    if estado:
                        filtro &= Q(estado=estado)
                        data['estado'] = estado
                        url_vars += f"&estado={encrypt(estado)}"

                    registros = registros.filter(filtro)
                    paging = MiPaginador(registros, 10)

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
                    data['usuario'] = persona
                    data['page'] = page
                    data['ids'] = ids if ids else ""
                    data['listado'] = page.object_list
                    data['tableIds'] = page.object_list.values_list('id', flat=True)
                    data['totalregistros'] = registros.count()
                    data['url_vars'] = url_vars
                    data['meses'] = meses
                    data['action'] = u'evidenciassalud'
                    request.session['viewactivo'] = 1
                    data['tipo_evidencia'] = 1
                    return render(request, "adm_revisioncriteriosactividades/viewplanificacionmensual.html", data)
                except Exception as ex:
                    return HttpResponseRedirect('/adm_revisioncriteriosactividades?info=Error de conexión. %s' % ex.__str__())

            elif action == 'viewdetalleestadopm':
                try:
                    if 'id' in request.GET:
                        data['id'] = id = request.GET['id']
                        data['estado_evidencia'] = estado_evidencia = EstadoEvidenciaSalud.objects.get(pk=encrypt(id))
                        data['listado'] = listado = estado_evidencia.detalleestadoevidenciasalud_set.filter(status=True).order_by('fecha')
                        template = get_template("pro_actividadestutorpracticas/modal/viewdetalleestado.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'aprobarevidenciasalud':
                try:
                    id = int(encrypt(request.GET['id']))
                    data['registro'] = registro = EstadoEvidenciaSalud.objects.get(pk=id)
                    data['aprueba'] = True
                    data['fecha'] = datetime.now()
                    template = get_template("adm_revisioncriteriosactividades/modal/detalle_aprobarsalud.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})


            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Criterios (Validación)'
                modulos = []
                # if es_coordinadorpp_ or es_directorcarrera_ or es_decano_ or es_docente_:
                #     modulo = {"id": 0, "url": "adm_revisioncriteriosactividades?action=evidenciassalud", "icono": "/static/images/iconssga/icon_autoevaluacion_de_docentes.svg", "nombre": "Evidencias Tutor salud", "descripcion": "Validación de evidencias prácticas pre profesionales salud del tutor"}
                #     modulos.append(modulo)
                #     modulo = {"id": 0, "url": "adm_revisioncriteriosactividades?action=evidenciassaludestudiante", "icono": "/static/images/iconssga/icon_POA_usuario_consulta.svg", "nombre": "Evidencias Estudiante salud", "descripcion": "Validación de evidencias prácticas pre profesionales salud del estudiante"}
                #     modulos.append(modulo)
                # if not es_docente_:
                modulo = {"id": 0, "url": "adm_revisioncriteriosactividades?action=solicitudes", "icono": "/static/images/iconssga/icon_consulta_de_ponencias.svg", "nombre": "Revisión actividades", "descripcion": "Validación de evidencias de actividades del personal académico"}
                modulos.append(modulo)
                modulo = {"id": 0, "url": "adm_revisioncriteriosactividades?action=bitacoras", "icono": "/static/images/iconssga/icon_consulta_de_ponencias.svg", "nombre": "Revisión de bitácoras", "descripcion": "Validación de evidencias de actividades registradas en la bitacora."}
                modulos.append(modulo)
                if es_administrador:
                    modulo = {"id": 0, "url": "adm_revisioncriteriosactividades?action=usuariosactividades", "icono": "/static/images/iconssga/icon_articulos.svg", "nombre": "Usuarios revisa informes de actividades", "descripcion": "Listado de actividades con sus respectivos usuarios de revisión"}
                    modulos.append(modulo)
                    modulo = {"id": 0, "url": "adm_revisioncriteriosactividades?action=usuariosbitacora", "icono": "/static/images/iconssga/icon_articulos.svg", "nombre": "Usuarios revisa actividades de bitácora", "descripcion": "Listado de actividades bitácora con sus respectivos usuarios de revisión"}
                    modulos.append(modulo)
                data['modulos2'] = modulos
                data['enlaceatras'] = "/"
                actualiza_estado_bitacora()
                return render(request, "adm_revisioncriteriosactividades/panel.html", data)
            except Exception as ex:
                pass


def process_codigos(codigos, criterio_attr):
    try:
        _filters_ = []
        for d in codigos:
            included = UserCriterioRevisorIntegrantes.objects.filter(usuariorevisor=d[4], status=True).values_list('profesor', flat=True)
            criteria = Q(Q(**{f'criterio__{criterio_attr}__id': d[0]}))
            if included:
                criteria &= Q(criterio__distributivo__profesor__id__in=included)
            _filters_.append(criteria)
        return _filters_
    except Exception as ex:
        raise NameError('Error de conexión. %s' % ex.__str__())

def migrar_firma_participantes_proyecto_investigacion(**kwargs):
    try:
        evidencia, url_file_generado, request = kwargs.get('evidencia'), kwargs.get('file'), kwargs.get('request')
        persona = request.session['persona']

        # Migracion de firma a los demas integrantes.
        parse_criterio_funcion = lambda x: {1: 55, 2: 56, 3: 57}[x] if x in (1,2,3) else None
        if evidencia.criterio.criterioinvestigacionperiodo.criterio.id == 55:
            if proyecto := ProyectoInvestigacion.objects.filter(profesor=evidencia.criterio.distributivo.profesor, status=True).exclude(cerrado=True).first():
                for integrante in proyecto.integrantes_proyecto().exclude(funcion=1):
                    profesor = Profesor.objects.filter(persona=integrante.persona, status=True).first()
                    if distributivo := DetalleDistributivo.objects.filter(criterioinvestigacionperiodo__criterio__id=parse_criterio_funcion(integrante.funcion), distributivo__profesor=profesor, distributivo__periodo=evidencia.criterio.distributivo.periodo, distributivo__activo=True, status=True).first():
                        if _evidencia := EvidenciaActividadDetalleDistributivo.objects.filter(proyectovinculacion__isnull=True, grupoinvestigacion__isnull=True, criterio=distributivo, hasta__month=evidencia.hasta.month, hasta__year=evidencia.hasta.year, status=True).first():
                            _evidencia.archivofirmado = url_file_generado
                            _evidencia.estadoaprobacion = 4
                            _evidencia.save(request)
                            historial = HistorialAprobacionEvidenciaActividad(evidencia=_evidencia, aprobacionpersona=persona, observacion='DOCUMENTO FIRMADO', fechaaprobacion=datetime.now().date(), estadoaprobacion=4)
                            historial.save(request)
                            auditoria = EvidenciaActividadAudi(evidencia=_evidencia, archivo=url_file_generado)
                            auditoria.save(request)
                            log(u'Guardo archivo firmado: {}'.format(_evidencia), request, "add")

    except Exception as ex:
        raise NameError(ex.__str__())


def aprobadores_sin_actividad_asociada(request, **kwargs):
    try:
        __author__ = 'Unemi'
        style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
        style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
        style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
        title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
        style1 = easyxf(num_format_str='D-MMM-YY')
        font_style = XFStyle()
        font_style.font.bold = True
        font_style2 = XFStyle()
        font_style2.font.bold = False
        wb = Workbook(encoding='utf-8')
        ws = wb.add_sheet('exp_xls_post_part', cell_overwrite_ok=True)
        # ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
        response = HttpResponse(content_type="application/ms-excel")
        response['Content-Disposition'] = 'attachment; filename=reporte_aprobadores_evidencias_varias' + random.randint(1, 10000).__str__() + '.xls'
        row_num = 0
        columns = [(u"N.", 2000), (u"ACTIVIDAD", 10000), (u"ESTADO DE APROBACIÓN", 8000), (u"TIPO DE ACTIVIDAD", 10000), (u"CRITERIO", 10000), (u"FECHA DE CREACIÓN", 8000), (u"USUARIO CREACION", 8000), (u"REVISOR", 8000), (u"PERIODO", 10000)]

        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num][0], font_style)
            ws.col(col_num).width = columns[col_num][1]

        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'yyyy/mm/dd'

        row_num = 0

        for aprobador in HistorialAprobacionEvidenciaActividad.objects.filter(evidencia__estadoaprobacion__in=(2, 3, 4, 5), evidencia__status=True, aprobacionpersona__isnull=False, status=True).order_by('-fecha_creacion'):
            tiene_revisor, _criteri, tipo = False, None, ''
            revisor = aprobador.aprobacionpersona.usercriteriorevisor_set.values_list('id').filter(tiporevisor=1, status=True)
            _periodo = aprobador.evidencia.criterio.distributivo.periodo

            if doc := aprobador.evidencia.criterio.criteriodocenciaperiodo:
                tipo = 'DOCENCIA'
                _criteri = doc.criterio
                tiene_revisor = revisor.filter(criteriodocenciaperiodo=doc, criteriodocenciaperiodo__periodo=_periodo, criteriodocenciaperiodo__subirevidencia=True).exists()

            if inv := aprobador.evidencia.criterio.criterioinvestigacionperiodo:
                tipo = 'INVESTIGACIÓN'
                _criteri = inv.criterio
                tiene_revisor = revisor.filter(criterioinvestigacionperiodo=inv, criterioinvestigacionperiodo__periodo=_periodo, criterioinvestigacionperiodo__subirevidencia=True).exists()

            if ges := aprobador.evidencia.criterio.criteriogestionperiodo:
                tipo = 'GESTIÓN'
                _criteri = ges.criterio
                tiene_revisor = revisor.filter(criteriogestionperiodo=ges, criteriogestionperiodo__periodo=_periodo, criteriogestionperiodo__subirevidencia=True).exists()

            if not tiene_revisor:
                row_num += 1
                campo1 = '%s' % aprobador.evidencia.actividad if aprobador.evidencia.actividad else ''
                campo2 = '%s' % aprobador.evidencia.get_estadoaprobacion_display() if aprobador.evidencia.estadoaprobacion else ''
                campo3 = '%s' % tipo if tipo else ''
                campo4 = '%s' % _criteri if _criteri else ''
                campo5 = '%s' % aprobador.fecha_creacion if aprobador.fecha_creacion else ''
                campo6 = '%s' % aprobador.evidencia.usuario_creacion.persona_set.first() if aprobador.evidencia.usuario_creacion else ''
                campo7 = '%s' % aprobador.aprobacionpersona if aprobador.aprobacionpersona else ''
                campo8 = '%s' % _periodo.nombre if _periodo else ''
                ws.write(row_num, 0, row_num, font_style2)
                ws.write(row_num, 1, campo1, font_style2)
                ws.write(row_num, 2, campo2, font_style2)
                ws.write(row_num, 3, campo3, font_style2)
                ws.write(row_num, 4, campo4, font_style2)
                ws.write(row_num, 5, campo5, font_style2)
                ws.write(row_num, 6, campo6, font_style2)
                ws.write(row_num, 7, campo7, font_style2)
                ws.write(row_num, 8, campo8, font_style2)
        wb.save(response)
        return response
    except Exception as ex:
        pass

def actualiza_estado_bitacora():
    try:
        if variable_valor('VALIDA_REGISTRO_BITACORA_PPPIR'):
            now, dias_plazo = datetime.now().date(), variable_valor('DIA_LIMITE_INFORME_MENSUAL')
            # Pasar a estado solicitado las bitacoras que esten pendientes en el día seleccionado como plazo
            if now.day >= (dias_plazo + 1):
                BitacoraActividadDocente.objects.filter(registrotardio=False, estadorevision=1, fechafin__month=now.month - 1, status=True).update(estadorevision=2)
    except Exception as ex:
        return 0

def actualizar_firma_participantes_proyecto_investigacion(**kwargs):
    try:
        evidencia, url_file_generado, request = kwargs.get('evidencia'), kwargs.get('file'), kwargs.get('request')
        persona = request.session['persona']

        # Migracion de firma a los demas integrantes.
        parse_criterio_funcion = lambda x: {1: 55, 2: 56, 3: 57}[x] if x in (1,2,3) else None
        if evidencia.criterio.criterioinvestigacionperiodo.criterio.id == 55:
            if proyecto := ProyectoInvestigacion.objects.filter(profesor=evidencia.criterio.distributivo.profesor, status=True).exclude(cerrado=True).first():
                for integrante in proyecto.integrantes_proyecto().exclude(funcion=1):
                    profesor = Profesor.objects.filter(persona=integrante.persona, status=True).first()
                    if distributivo := DetalleDistributivo.objects.filter(criterioinvestigacionperiodo__criterio__id=parse_criterio_funcion(integrante.funcion), distributivo__profesor=profesor, distributivo__periodo=evidencia.criterio.distributivo.periodo, distributivo__activo=True, status=True).first():
                        if _evidencia := EvidenciaActividadDetalleDistributivo.objects.filter(proyectovinculacion__isnull=True, grupoinvestigacion__isnull=True, criterio=distributivo, hasta__month=evidencia.hasta.month, hasta__year=evidencia.hasta.year, status=True).first():
                            _evidencia.archivofirmado = url_file_generado
                            _evidencia.estadoaprobacion = 4
                            _evidencia.save(request)

                            auditoria = EvidenciaActividadAudi.objects.filter(evidencia=_evidencia, status=True).order_by('-id').first()
                            auditoria.archivo = url_file_generado
                            auditoria.save(request)

                            log(u'Actualizó archivo firmado: {}'.format(_evidencia), request, "edit")

    except Exception as ex:
        raise NameError(ex.__str__())
