# -*- coding: UTF-8 -*-
import os
import sys
import json
import requests
from datetime import datetime, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from django.db.models.query_utils import Q
from django.db.models import Sum
from decimal import Decimal
from django.db.models.aggregates import Count, Max
from django.forms import model_to_dict
from django.db import connections

from decorators import secure_module, last_access
from sagest.models import CapConfiguracionIpec, Rubro, RegistroRubro, ComprobanteAlumno, TipoOtroRubro, CuentaContable
from sga.commonviews import adduserdata
from posgrado.commonviews import secuencia_contratopagare
from posgrado.forms import RequisitosMaestriaForm, AdmiCohorteMaestriaForm, RequisitosMaestriaImgForm, CohorteMaestriaForm, RegistroPagoForm, ContratoPagoMaestriaForm, GarantePagoMaestriaForm, \
    numeroCuotasPagoForm, TitulacionPersonaAdmisionPosgradoForm, EvidenciaRequisitoAdmisionForm, ValidarPerfilAdmisionForm
from sga.funciones import generar_nombre, log, numero_a_letras, convertir_fecha, validar_archivo, null_to_decimal, validarcedula, variable_valor, notificacion3
from posgrado.models import RequisitosMaestria, EvidenciaRequisitosAspirante, InscripcionCohorte, CohorteMaestria, \
    DetalleEvidenciaRequisitosAspirante, RequisitosGrupoCohorte, EvidenciaPagoExamen, ClaseRequisito, Contrato, \
    DetalleAprobacionContrato, ConfigFinanciamientoCohorte, GarantePagoMaestria, TablaAmortizacion, CanalInformacionMaestria, \
    DetalleAprobacionFormaPago, ProductoSecretaria
from sga.funciones_templatepdf import certificadoadmtidoprograma, contratoformapagoprograma, pagareaspirantemae, oficioterminacioncontrato
from sga.models import Persona, DescuentoPosgradoMatricula, RequisitosDetalleConfiguracionDescuentoPosgrado, \
    EvidenciasDescuentoPosgradoMatricula, DetalleEvidenciaDescuentoPosgradoMatricula, Malla, FirmaPersona, \
    DescuentoPosgradoMatriculaRecorrido, Titulacion, CamposTitulosPostulacion, Carrera, Titulo, SubAreaConocimientoTitulacion, \
    SubAreaEspecificaConocimientoTitulacion, Reporte, AsignaturaMalla, PeriodoCarreraCosto, PerfilUsuario, Pais
from inno.models import InfraestructuraEquipamientoInformacionPac, TipoFormaPagoPac, DetallePerfilIngreso, PerfilInscripcion
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from socioecon.models import FichaSocioeconomicaINEC
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from settings import SITE_STORAGE
from sga.reportes import run_report_v1
import shutil
from core.firmar_documentos import obtener_posicion_x_y_saltolinea
from core.firmar_documentos_ec import JavaFirmaEc
from django.core.files.base import ContentFile
from secretaria.models import Servicio, Solicitud, HistorialSolicitud, SolicitudAsignatura
from django.contrib.contenttypes.fields import ContentType
from secretaria.funciones import generar_codigo_solicitud
from sagest.forms import DatosPersonalesMaestranteForm
import io
@login_required(redirect_field_name='ret', login_url='/loginposgrado')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    hoy = datetime.now().date()
    adduserdata(request, data)
    persona = request.session['persona']
    aspirante = persona.inscripcionaspirante_set.filter(status=True)[0]
    perfilprincipal = request.session['perfilprincipal']
    urlepunemi = 'https://sagest.epunemi.gob.ec/'
    # urlepunemi = 'http://127.0.0.1:8001/'
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'registropago':
            try:
                with transaction.atomic():
                    activofact = False
                    inscripcioncohorte = InscripcionCohorte.objects.get(pk=int(encrypt(request.POST['id'])))
                    cuentadeposito = int(request.POST['cuentadeposito'])
                    telefono = str(request.POST['telefono'])
                    email = str(request.POST['email'])
                    fechapago = convertir_fecha(request.POST['fecha'])
                    valor = Decimal(request.POST['valor'])
                    observacion = request.POST['observacion']
                    tipocomprobante = int(request.POST['tipocomprobante'])
                    persona_get = Persona.objects.get(pk=persona.id)
                    persona_get.telefono = telefono
                    persona_get.email = email
                    persona_get.save()
                    # DATOS FACTURACION
                    nombres = request.POST['nombres']
                    apellidos = request.POST['apellidos']
                    identificacion = request.POST['identificacion']
                    correo = request.POST['correo']
                    telefonofactura = request.POST['telefonofactura']
                    direccion = request.POST['direccion']
                    cuentadepositoget = cuentadeposito
                    if valor <= 0:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "El valor debe ser mayor a cero."}, safe=False)
                    if 'archivo' in request.FILES:
                        form = RegistroPagoForm(request.POST)
                        if form.is_valid():
                            activofacturacion = form.cleaned_data['activo']
                            nombrepersona = persona_get.__str__()
                            nombrepersona_str = persona_get.__str__().lower().replace(' ', '_')
                            comprobante = ComprobanteAlumno(persona=persona_get,
                                                            telefono=telefono,
                                                            email=email,
                                                            curso=inscripcioncohorte.cohortes.maestriaadmision.carrera.nombre,
                                                            carrera=inscripcioncohorte.cohortes.maestriaadmision.carrera.nombre,
                                                            cuentadeposito=cuentadepositoget,
                                                            valor=valor,
                                                            fechapago=fechapago,
                                                            observacion=observacion,
                                                            inscripcioncohorte=inscripcioncohorte,
                                                            tipocomprobante=tipocomprobante)
                            if activofacturacion:
                                activofact = True
                                comprobante.nombres = nombres
                                comprobante.apellidos = apellidos
                                comprobante.identificacion = identificacion
                                comprobante.correo = correo
                                comprobante.telefonofactura = telefonofactura
                                comprobante.direccion = direccion
                            comprobante.activofacturacionotros = activofact

                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                if newfile.size > 10485760:
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})

                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if not (ext.lower() == '.pdf' or ext.lower() == '.png'):
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf o .png"}, safe=False)

                                nombrefoto = 'comprobante_{}'.format(persona.cedula)
                                newfile._name = generar_nombre(nombrefoto.strip(), newfile._name)
                                comprobante.comprobantes = newfile
                            comprobante.save()

                            if persona.cedula:
                                personacedula = str(persona.cedula)
                            if persona.pasaporte:
                                personacedula = str(persona.pasaporte)
                            if persona.ruc:
                                personacedula = str(persona.ruc)

                            url = urlepunemi + "api?a=apisavecomprobante" \
                                  "&tiporegistro=1&clavesecreta=unemiepunemi2022&personacedula=" + personacedula + "&cuentadeposito=" + str(cuentadeposito) + \
                                  "&telefono=" + str(persona.telefono) + \
                                  "&email=" + persona.email + \
                                  "&fecha=" + str(comprobante.fechapago) + \
                                  "&archivocomprobante=" + str(comprobante.comprobantes) + \
                                  "&valor=" + str(comprobante.valor) + \
                                  "&curso=" + comprobante.curso + \
                                  "&carrera=" + comprobante.carrera + \
                                  "&observacion=" + comprobante.observacion + \
                                  "&codigocomprobante=" + str(comprobante.id) + \
                                  "&tipocomprobante=" + str(comprobante.tipocomprobante)

                            if activofacturacion:
                                url = url + "&activofacturacion" + "&onombres=" + comprobante.nombres + \
                                "&oapellidos=" + comprobante.apellidos + \
                                "&oidentificacion=" + comprobante.identificacion + \
                                "&ocorreo=" + comprobante.correo + \
                                "&otelefonofactura=" + comprobante.telefonofactura + \
                                "&odireccion=" + comprobante.direccion

                            print(url)
                            r = requests.get(url)
                            for lista in r.json():
                                comprobante.idcomprobanteepunemi = lista['codigocomprobante']
                                comprobante.save()
                            return JsonResponse({"result": False, "mensaje":'Datos guardados correctamente'})
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Falta subir evidencia del comprobante de pago."}, safe=False)
            except Exception as ex:
                # mensajeerror = "{} - {}".format(ex, 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                # messages.error(request, mensajeerror)
                transaction.set_rollback(True)
                #return JsonResponse({"result": True, "mensaje": "Intentelo más tarde.", "mensajeerror": mensajeerror}, safe=False)
                return JsonResponse({"result": True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                     "mensaje": "Error en el formulario"})

        if action == 'registroanticipo':
            try:
                with transaction.atomic():
                    inscripcioncohorte = InscripcionCohorte.objects.get(pk=int(encrypt(request.POST['id'])))
                    cuentadeposito = request.POST['cuentadeposito']
                    telefono = str(request.POST['telefono'])
                    email = str(request.POST['email'])
                    fechapago = convertir_fecha(request.POST['fecha'])
                    valor = Decimal(request.POST['valor'])
                    observacion = str(request.POST['observacion'])
                    tipocomprobante = int(request.POST['tipocomprobante'])
                    persona_get = Persona.objects.get(pk=persona.id)
                    persona_get.telefono = telefono
                    persona_get.email = email
                    persona_get.save()
                    cuentadepositoget = cuentadeposito
                    if valor <= 0:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "El valor debe ser mayor a cero."}, safe=False)
                    if 'archivo' in request.FILES:
                        form = RegistroPagoForm(request.POST)
                        if form.is_valid():
                            nombrepersona = persona_get.__str__()
                            nombrepersona_str = persona_get.__str__().lower().replace(' ', '_')
                            comprobante = ComprobanteAlumno(persona=persona_get,
                                                            telefono=telefono,
                                                            email=email,
                                                            curso=inscripcioncohorte.cohortes.maestriaadmision.carrera.nombre,
                                                            carrera=inscripcioncohorte.cohortes.maestriaadmision.carrera.nombre,
                                                            cuentadeposito=cuentadepositoget,
                                                            valor=valor,
                                                            fechapago=fechapago,
                                                            observacion=observacion,
                                                            inscripcioncohorte=inscripcioncohorte,
                                                            tiporegistro=2,
                                                            tipocomprobante=tipocomprobante)
                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                if newfile.size > 10485760:
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if not (ext.lower() == '.pdf' or ext.lower() == '.png'):
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf o .png."})

                                nombrefoto = 'comprobante_{}'.format(nombrepersona_str)
                                newfile._name = generar_nombre(nombrefoto.strip(), newfile._name)
                                comprobante.comprobantes = newfile
                            comprobante.save()

                            if persona.cedula:
                                personacedula = str(persona.cedula)
                            if persona.pasaporte:
                                personacedula = str(persona.pasaporte)
                            if persona.ruc:
                                personacedula = str(persona.ruc)

                            url = urlepunemi + "api?a=apisavecomprobante" \
                                  "&tiporegistro=2&clavesecreta=unemiepunemi2022&personacedula=" + personacedula + "&cuentadeposito=" + str(cuentadeposito) + \
                                  "&telefono=" + str(persona.telefono) + \
                                  "&email=" + persona.email + \
                                  "&fecha=" + str(comprobante.fechapago) + \
                                  "&archivocomprobante=" + str(comprobante.comprobantes) + \
                                  "&valor=" + str(comprobante.valor) + \
                                  "&curso=" + comprobante.curso + \
                                  "&carrera=" + comprobante.carrera + \
                                  "&observacion=" + comprobante.observacion + \
                                  "&codigocomprobante=" + str(comprobante.id) + \
                                  "&tipocomprobante=" + str(comprobante.tipocomprobante)
                            print(url)
                            r = requests.get(url)
                            for lista in r.json():
                                comprobante.idcomprobanteepunemi = lista['codigocomprobante']
                                comprobante.save()
                            return JsonResponse({"result": False, "mensaje": 'Datos guardados correctamente'}, safe=False)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Falta subir evidencia del comprobante de pago."}, safe=False)
            except Exception as ex:
                mensajeerror = "{} - {}".format(ex, 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                messages.error(request, mensajeerror)
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde.", "mensajeerror": mensajeerror}, safe=False)


        if action == 'cargararchivo':
            try:
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                f = RequisitosMaestriaForm(request.POST)
                if f.is_valid():
                    inscripcioncohorte = InscripcionCohorte.objects.get(pk=request.POST['id'])
                    requisitosmaestria = RequisitosMaestria.objects.get(pk=request.POST['idevidencia'])
                    if not EvidenciaRequisitosAspirante.objects.filter(requisitos=requisitosmaestria, inscripcioncohorte=inscripcioncohorte, status=True).exists():
                        requisitomaestria = EvidenciaRequisitosAspirante(requisitos=requisitosmaestria,
                                                                         inscripcioncohorte=inscripcioncohorte)
                        requisitomaestria.save(request)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("requisitopgrado_", newfile._name)
                            requisitomaestria.archivo = newfile
                            requisitomaestria.save(request)
                        log(u'Adicionó requisito de maestria aspirante: %s' % requisitomaestria.requisitos, request, "add")
                        detalle = DetalleEvidenciaRequisitosAspirante(evidencia=requisitomaestria,
                                                                      estadorevision=1,
                                                                      # persona=inscripcioncohorte.inscripcionaspirante.persona,
                                                                      fecha=datetime.now().date(),
                                                                      observacion=f.cleaned_data['observacion'])
                        detalle.save(request)

                        if inscripcioncohorte.total_evidence_lead():
                            inscripcioncohorte.todosubido = True
                            if inscripcioncohorte.tiporespuesta and inscripcioncohorte.tiporespuesta.id == 6:
                                inscripcioncohorte.tiporespuesta.id = 5
                            inscripcioncohorte.tienerechazo = False
                            inscripcioncohorte.save()

                        if inscripcioncohorte.total_evidence_lead_fi():
                            inscripcioncohorte.todosubidofi = True
                            inscripcioncohorte.tienerechazofi = False
                            inscripcioncohorte.save()

                        asunto = u"REQUISITO DE ADMISIÓN SUBIDO"
                        observacion = f'Se le comunica que el postulante {inscripcioncohorte.inscripcionaspirante.persona} ha subido el requisito {detalle.evidencia.requisitos.requisito.nombre}, mismo que fue anteriormente rechazado por Secretaría. Por favor, revisar el caso y pre-aprobar los requisitos del postulante. Puede dar clic en la URL para ser redirigido directamente al postulante  que presenta dicha observación.'
                        para = inscripcioncohorte.asesor.persona
                        perfiu = inscripcioncohorte.asesor.perfil_administrativo()

                        notificacion3(asunto, observacion, para, None,
                                      '/comercial?s=' + inscripcioncohorte.inscripcionaspirante.persona.cedula,
                                      detalle.pk, 1,
                                      'sga', DetalleEvidenciaRequisitosAspirante, perfiu, request)

                        return JsonResponse({"result": "ok"})
                    else:
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            if newfile.size > 10485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                            else:
                                newfiles = request.FILES['archivo']
                                newfilesd = newfiles._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if not ext.lower() == '.pdf':
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        f = RequisitosMaestriaForm(request.POST)
                        requisito = EvidenciaRequisitosAspirante.objects.get(requisitos=requisitosmaestria, inscripcioncohorte=inscripcioncohorte, status=True)
                        if f.is_valid():
                            # requisito.observacion = f.cleaned_data['observacion']
                            # requisito.estadorevision = 1
                            # requisito.save(request)
                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                newfile._name = generar_nombre("requisitopgrado_", newfile._name)
                                requisito.archivo = newfile
                                requisito.save(request)
                            detalle = DetalleEvidenciaRequisitosAspirante(evidencia=requisito,
                                                                          estadorevision=1,
                                                                          # persona=inscripcioncohorte.inscripcionaspirante.persona,
                                                                          fecha=datetime.now().date(),
                                                                          observacion=f.cleaned_data['observacion'])
                            detalle.save(request)
                            log(u'Editó requisito de maestría aspirante: %s' % requisito, request, "edit")

                            if inscripcioncohorte.total_evidence_lead_fi():
                                inscripcioncohorte.todosubidofi = True
                                inscripcioncohorte.tienerechazofi = False
                                inscripcioncohorte.save()

                            if inscripcioncohorte.total_evidence_lead():
                                inscripcioncohorte.todosubido = True
                                if inscripcioncohorte.tiporespuesta and inscripcioncohorte.tiporespuesta.id == 6:
                                    inscripcioncohorte.tiporespuesta.id = 5
                                inscripcioncohorte.tienerechazo = False
                                inscripcioncohorte.save()

                            asunto = u"REQUISITO DE ADMISIÓN SUBIDO"
                            observacion = f'Se le comunica que el postulante {inscripcioncohorte.inscripcionaspirante.persona} ha subido el requisito {detalle.evidencia.requisitos.requisito.nombre}, mismo que fue anteriormente rechazado por Secretaría. Por favor, revisar el caso y pre-aprobar los requisitos del postulante. Puede dar clic en la URL para ser redirigido directamente al postulante  que presenta dicha observación.'
                            para = inscripcioncohorte.asesor.persona
                            perfiu = inscripcioncohorte.asesor.perfil_administrativo()

                            notificacion3(asunto, observacion, para, None,
                                          '/comercial?s=' + inscripcioncohorte.inscripcionaspirante.persona.cedula,
                                          detalle.pk, 1,
                                          'sga', DetalleEvidenciaRequisitosAspirante, perfiu, request)

                            return JsonResponse({"result": "ok"})
                        else:
                            raise NameError('Error')
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cargararchivobecas':
            try:
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                f = RequisitosMaestriaForm(request.POST)
                if f.is_valid():
                    inscripcioncohorte = solicitudbeca = DescuentoPosgradoMatricula.objects.get(pk=request.POST['id'])
                    requisitosmaestria = RequisitosDetalleConfiguracionDescuentoPosgrado.objects.get(pk=request.POST['idevidencia'])
                    if not EvidenciasDescuentoPosgradoMatricula.objects.filter(requisitosdetalleconfiguraciondescuentoposgrado=requisitosmaestria, descuentoposgradomatricula=inscripcioncohorte, status=True).exists():
                        requisitomaestria = EvidenciasDescuentoPosgradoMatricula(requisitosdetalleconfiguraciondescuentoposgrado=requisitosmaestria, descuentoposgradomatricula=inscripcioncohorte)
                        requisitomaestria.save(request)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("requisitodescuentoposgrado_", newfile._name)
                            requisitomaestria.archivo = newfile
                            requisitomaestria.save(request)
                        log(u'Adicionó requisito de descuento maestria solicitante: %s' % requisitomaestria.requisitosdetalleconfiguraciondescuentoposgrado, request, "add")
                        detalle = DetalleEvidenciaDescuentoPosgradoMatricula(evidencia=requisitomaestria,
                                                                             estadorevision=1,
                                                                             fecha=datetime.now().date(),
                                                                             observacion=f.cleaned_data['observacion'])
                        detalle.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            if newfile.size > 10485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                            else:
                                newfiles = request.FILES['archivo']
                                newfilesd = newfiles._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if not ext.lower() == '.pdf':
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        f = RequisitosMaestriaForm(request.POST)
                        requisito = EvidenciasDescuentoPosgradoMatricula.objects.get(requisitosdetalleconfiguraciondescuentoposgrado=requisitosmaestria, descuentoposgradomatricula=inscripcioncohorte, status=True)
                        if f.is_valid():
                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                newfile._name = generar_nombre("requisitopgrado_", newfile._name)
                                requisito.archivo = newfile
                                requisito.save(request)
                            detalle = DetalleEvidenciaDescuentoPosgradoMatricula(evidencia=requisito,
                                                                                 estadorevision=1,
                                                                                 fecha=datetime.now().date(),
                                                                                 observacion=f.cleaned_data['observacion'])
                            detalle.save(request)

                            # Verificar estados de las evidencias: todos deben tener estado CARGADO para poner el estado
                            # de la solicitud en SOLICITADO
                            asignar_solicitado = True
                            for evidencia in solicitudbeca.evidencias():
                                if evidencia.ultima_evidencia().estado_aprobacion == 2:
                                    continue

                                if evidencia.ultima_evidencia().estado_aprobacion != 1:
                                    asignar_solicitado = False
                                    break

                            if asignar_solicitado:
                                solicitudbeca.estado = 1
                                solicitudbeca.save(request)

                                # Agrego recorrido de la solicitud
                                recorridosolicitud = DescuentoPosgradoMatriculaRecorrido(
                                    descuentoposgradomatricula=solicitudbeca,
                                    fecha=datetime.now().date(),
                                    persona=persona,
                                    observacion='SOLICITUD ACTUALIZADA',
                                    estado=1
                                )
                                recorridosolicitud.save(request)

                            log(u'Editó requisito de descuento maestria solicitante: %s' % requisito, request, "edit")
                            return JsonResponse({"result": "ok"})
                        else:
                            raise NameError('Error')
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cargararchivoimagen':
            try:
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if ext.lower() == '.jpg' or ext.lower() == '.png' or ext.lower() == '.jpeg' or ext.lower() == '.JPG' or ext.lower() == '.PNG' or ext.lower() == '.JPEG':
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .jpg, .png."})
                f = RequisitosMaestriaImgForm(request.POST)
                if f.is_valid():
                    inscripcioncohorte = InscripcionCohorte.objects.get(pk=request.POST['id'])
                    requisitosmaestria = RequisitosMaestria.objects.get(pk=request.POST['idevidencia'])
                    if not EvidenciaRequisitosAspirante.objects.filter(requisitos=requisitosmaestria, inscripcioncohorte=inscripcioncohorte, status=True).exists():
                        requisitomaestria = EvidenciaRequisitosAspirante(requisitos=requisitosmaestria,
                                                                         inscripcioncohorte=inscripcioncohorte)
                        requisitomaestria.save(request)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("requisitopgrado_", newfile._name)
                            requisitomaestria.archivo = newfile
                            requisitomaestria.save(request)
                        log(u'Adicionó requisito de maestria aspirante: %s' % requisitomaestria.requisitos, request, "add")
                        detalle = DetalleEvidenciaRequisitosAspirante(evidencia=requisitomaestria,
                                                                      estadorevision=1,
                                                                      # persona=inscripcioncohorte.inscripcionaspirante.persona,
                                                                      fecha=datetime.now().date(),
                                                                      observacion=f.cleaned_data['observacion'])
                        detalle.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            if newfile.size > 10485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                            else:
                                newfiles = request.FILES['archivo']
                                newfilesd = newfiles._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext.lower() == '.jpg' or ext.lower() == '.png' or ext.lower() == '.jpeg' or ext.lower() == '.JPG' or ext.lower() == '.PNG' or ext.lower() == '.JPEG':
                                    a = 1
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .jpg, .png."})
                        f = RequisitosMaestriaImgForm(request.POST)
                        requisito = EvidenciaRequisitosAspirante.objects.get(requisitos=requisitosmaestria, inscripcioncohorte=inscripcioncohorte, status=True)
                        if f.is_valid():
                            # requisito.observacion = f.cleaned_data['observacion']
                            # requisito.estadorevision = 1
                            # requisito.save(request)
                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                newfile._name = generar_nombre("requisitopgrado_", newfile._name)
                                requisito.archivo = newfile
                                requisito.save(request)
                            detalle = DetalleEvidenciaRequisitosAspirante(evidencia=requisito,
                                                                          estadorevision=1,
                                                                          # persona=inscripcioncohorte.inscripcionaspirante.persona,
                                                                          fecha=datetime.now().date(),
                                                                          observacion=f.cleaned_data['observacion'])
                            detalle.save(request)
                            log(u'Editó requisito de maestría aspirante: %s' % requisito, request, "edit")
                            return JsonResponse({"result": "ok"})
                        else:
                            raise NameError('Error')
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deletebeca':
            try:
                inscripcioncohorte = InscripcionCohorte.objects.get(pk=request.POST['id'])
                inscripcioncohorte.tipobeca = None
                inscripcioncohorte.save(request)

                solicitudbeca = inscripcioncohorte.descuentoposgradomatricula_set.filter(status=True)[0]
                solicitudbeca.estado = 7
                solicitudbeca.save(request)

                recorridobeca = DescuentoPosgradoMatriculaRecorrido(
                    descuentoposgradomatricula=solicitudbeca,
                    fecha=datetime.now().date(),
                    persona=persona,
                    observacion='SOLICITUD ANULADA POR POSTULANTE',
                    estado=7
                )
                recorridobeca.save(request)

                log(u'Anuló solicitud de beca de posgrado: %s' % solicitudbeca, request, "edit")

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cargamasiva':
            try:
                inscripcioncohorte = InscripcionCohorte.objects.get(pk=request.POST['id'])
                listadorequisitosmaestria = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, status=True)
                for requi in listadorequisitosmaestria:
                    nombrefile = 'requisito' + str(requi.id)
                    if nombrefile in request.FILES:
                        if not EvidenciaRequisitosAspirante.objects.filter(requisitos=requi, inscripcioncohorte=inscripcioncohorte, status=True).exists():
                            requisitomaestria = EvidenciaRequisitosAspirante(requisitos=requi,
                                                                             inscripcioncohorte=inscripcioncohorte)
                            requisitomaestria.save(request)
                            newfile = request.FILES[nombrefile]
                            newfile._name = generar_nombre("requisitopgrado_" + str(requi.id) + "_", newfile._name)
                            requisitomaestria.archivo = newfile
                            requisitomaestria.save(request)
                            log(u'Adicionó requisito de maestria aspirante: %s' % requisitomaestria.requisitos, request, "add")
                            detalle = DetalleEvidenciaRequisitosAspirante(evidencia=requisitomaestria,
                                                                          estadorevision=1,
                                                                          fecha=datetime.now().date(),
                                                                          observacion='')
                            detalle.save(request)

                if inscripcioncohorte.total_evidence_lead_fi():
                    inscripcioncohorte.todosubidofi = True
                    inscripcioncohorte.tienerechazofi = False
                    inscripcioncohorte.save()

                if inscripcioncohorte.total_evidence_lead():
                    inscripcioncohorte.todosubido = True
                    if inscripcioncohorte.tiporespuesta and inscripcioncohorte.tiporespuesta.id == 6:
                        inscripcioncohorte.tiporespuesta.id = 5
                    inscripcioncohorte.tienerechazo = False
                    inscripcioncohorte.save()

                    if inscripcioncohorte.estado_aprobador != 2:
                        asunto = u"SUBIÓ TODOS LOS REQUISITOS DE ADMISIÓN"
                        observacion = f'Se le comunica que el postulante {inscripcioncohorte.inscripcionaspirante.persona} con cédula {inscripcioncohorte.inscripcionaspirante.persona.cedula} ha subido todos sus requisitos de admisión. Por favor, pre-aprobar los requisitos del postulante. Puede dar clic en la URL para ser redirigido directamente al postulante pendiente de pre-aprobación.'
                        para = inscripcioncohorte.asesor.persona
                        perfiu = inscripcioncohorte.asesor.perfil_administrativo()

                        notificacion3(asunto, observacion, para, None,
                                      '/comercial?action=leadsporpreaprobar&s=' + inscripcioncohorte.inscripcionaspirante.persona.cedula,
                                      inscripcioncohorte.pk, 1,
                                      'sga', InscripcionCohorte, perfiu, request)

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cargamasivabecas':
            try:
                inscripcioncohorte = DescuentoPosgradoMatricula.objects.get(pk=request.POST['id'])
                listadorequisitosmaestria = RequisitosDetalleConfiguracionDescuentoPosgrado.objects.filter(detalleconfiguraciondescuentoposgrado=inscripcioncohorte.detalleconfiguraciondescuentoposgrado, status=True)
                for requi in listadorequisitosmaestria:
                    nombrefile = 'requisito' + str(requi.id)
                    if nombrefile in request.FILES:
                        if not EvidenciasDescuentoPosgradoMatricula.objects.filter(requisitosdetalleconfiguraciondescuentoposgrado=requi, descuentoposgradomatricula=inscripcioncohorte, status=True).exists():
                            requisitomaestria = EvidenciasDescuentoPosgradoMatricula(requisitosdetalleconfiguraciondescuentoposgrado=requi, descuentoposgradomatricula=inscripcioncohorte)
                            requisitomaestria.save(request)
                            newfile = request.FILES[nombrefile]
                            newfile._name = generar_nombre("requisitodescuentoposgrado_" + str(requi.id) + "_", newfile._name)
                            requisitomaestria.archivo = newfile
                            requisitomaestria.save(request)
                            log(u'Adicionó requisito descuento de maestria solicitante: %s' % requisitomaestria.requisitosdetalleconfiguraciondescuentoposgrado,
                                request, "add")
                            detalle = DetalleEvidenciaDescuentoPosgradoMatricula(evidencia=requisitomaestria,
                                                                                 estadorevision=1,
                                                                                 fecha=datetime.now().date(),
                                                                                 observacion='')
                            detalle.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'subirpago':
            try:
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                f = RequisitosMaestriaForm(request.POST)
                if f.is_valid():
                    ids = request.POST['id']
                    inscripcioncohorte = InscripcionCohorte.objects.get(pk=request.POST['id'])
                    if not EvidenciaPagoExamen.objects.filter(inscripcioncohorte=inscripcioncohorte, status=True).exists():
                        pagoexamen = EvidenciaPagoExamen(inscripcioncohorte=inscripcioncohorte, estadorevision=1)
                        pagoexamen.save(request)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("pagoexamenpgrado_", newfile._name)
                            pagoexamen.archivo = newfile
                            pagoexamen.save(request)
                        log(u'Adicionó pago examen maestria: %s' % pagoexamen.inscripcioncohorte, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            if newfile.size > 10485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                            else:
                                newfiles = request.FILES['archivo']
                                newfilesd = newfiles._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if not ext.lower() == '.pdf':
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        f = RequisitosMaestriaForm(request.POST)
                        pagoexamen = EvidenciaPagoExamen.objects.get(inscripcioncohorte=inscripcioncohorte, status=True)
                        if f.is_valid():
                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                newfile._name = generar_nombre("requisitopgrado_", newfile._name)
                                pagoexamen.archivo = newfile
                                pagoexamen.estadorevision = 1
                                pagoexamen.save(request)
                            log(u'Editó pago examen maestria: %s' % pagoexamen.inscripcioncohorte, request, "edit")
                            return JsonResponse({"result": "ok"})
                        else:
                            raise NameError('Error')
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'pdfcertificadototalprograma':
            try:
                qrresult = certificadoadmtidoprograma(request.POST['idins'])
                return JsonResponse({"result": "ok", 'url': qrresult})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addcohorte':
            try:
                f = AdmiCohorteMaestriaForm(request.POST)
                if f.is_valid():
                    if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, maestria=f.cleaned_data['maestria'], status=True).exists():
                        inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                maestria=f.cleaned_data['maestria'])
                        inscripcioncohorte.save(request)
                        log(u'Adicionó inscripcion cohorte: %s' % inscripcioncohorte.inscripcionaspirante, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe una inscripción con maestría."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'aplicarcohorte':
            try:
                cohorte = CohorteMaestria.objects.get(pk=request.POST['idcohorte'])
                # if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes__maestriaadmision=cohorte.maestriaadmision).exists():
                inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante, cohortes=cohorte)
                inscripcioncohorte.save(request)
                log(u'Aplicó a programa de maestría: %s - %s' % (inscripcioncohorte, aspirante), request, "add")
                return JsonResponse({"result": "ok"})
                # else:
                #     return JsonResponse({"result": "bad", "mensaje": u"Usted ya se encuentra inscrito en la ("+str(cohorte.maestriaadmision)+" - "+str(cohorte.descripcion)+")"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al solicitar cupo."})

        if action == 'delinscripcion':
            try:
                inscripcioncohorte = InscripcionCohorte.objects.get(pk=request.POST['id'])
                inscripcioncohorte.status = False
                inscripcioncohorte.save()
                log(u'Eliminó inscripcion: %s - %s' % (inscripcioncohorte, inscripcioncohorte.inscripcionaspirante), request, "del")
                return JsonResponse({"result": "ok", "mensaje": u"Postulación eliminada correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        if action == 'aplicarcohortegrupo':
            try:
                cohorte = CohorteMaestria.objects.get(pk=request.POST['idcohorte'])
                # if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes__maestriaadmision=cohorte.maestriaadmision).exists():
                # if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, status=True, cohortes=cohorte).exists():
                inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante, cohortes=cohorte, grupo_id=request.POST['idgrupo'])
                inscripcioncohorte.save(request)
                log(u'Aplicó a programa de maestría: %s - %s' % (inscripcioncohorte, aspirante), request, "add")
                return JsonResponse({"result": "ok"})
                # else:
                #     return JsonResponse({"result": "bad", "mensaje": u"Usted ya se encuentra inscrito en la ("+str(cohorte.maestriaadmision)+" - "+str(cohorte.descripcion)+")"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al solicitar cupo."})

        if action == 'addgarantepagomaestria':
            try:
                insc = InscripcionCohorte.objects.get(pk=request.POST['id'])
                f = GarantePagoMaestriaForm(request.POST)
                resp = validarcedula(request.POST['cedula'].strip())
                if resp != 'Ok':
                    raise NameError(u"Problemas con la cédula: %s." % (resp))
                if f.is_valid():
                    if not GarantePagoMaestria.objects.filter(cedula=f.cleaned_data['cedula'], status=True).exists():
                        garante = GarantePagoMaestria(inscripcioncohorte=insc,
                                                      cedula=f.cleaned_data['cedula'],
                                                      nombres=f.cleaned_data['nombres'],
                                                      apellido1=f.cleaned_data['apellido1'],
                                                      apellido2=f.cleaned_data['apellido2'],
                                                      genero=f.cleaned_data['genero'],
                                                      telefono=f.cleaned_data['telefono'],
                                                      email=f.cleaned_data['email'],
                                                      direccion=f.cleaned_data['direccion'])
                        garante.save(request)
                        log(u'Adicionó garante de pago: %s al aspirante %s' %(garante, insc), request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        raise NameError("La persona ya es garante de otro aspirante a mestría.")
                else:
                    raise NameError("Error en el formulario.")
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Error al registrar. %s"%(ex)}, safe=False)

        if action == 'editgarantepagomaestria':
            try:
                insc = InscripcionCohorte.objects.get(pk=request.POST['id'])
                f = GarantePagoMaestriaForm(request.POST)
                if f.is_valid():
                    garante = GarantePagoMaestria.objects.get(pk=request.POST['idg'])
                    garante.nombres=f.cleaned_data['nombres']
                    garante.apellido1=f.cleaned_data['apellido1']
                    garante.apellido2=f.cleaned_data['apellido2']
                    garante.genero=f.cleaned_data['genero']
                    garante.telefono=f.cleaned_data['telefono']
                    garante.email=f.cleaned_data['email']
                    garante.direccion=f.cleaned_data['direccion']
                    garante.save(request)
                    log(u'Editó garante de pago del aspirante %s' %(insc), request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError("Error en el formulario.")
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Error al editar garante: %s."%(ex)}, safe=False)

        if action == 'delgarantepagomaestria':
            try:
                garante = GarantePagoMaestria.objects.get(pk=request.POST['id'])
                garante.status = False
                garante.save(request)
                log(u'Eliminó garante: %s del aspirante  %s' % (garante, garante.inscripcioncohorte), request, "del")
                return JsonResponse({"result": "ok", "mensaje": u"Garante eliminado correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        if action == 'cargarcontratopago':
            try:
                hayarchivos = False
                if 'archivo' in request.FILES:
                    hayarchivos = True
                    descripcionarchivo = 'Contrato de pago'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivo'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar un archivo (Contrato)."})

                f = ContratoPagoMaestriaForm(request.POST, request.FILES)
                if f.is_valid():
                    if hayarchivos:
                        contratopago = request.FILES['archivo']
                        contratopago._name = generar_nombre("contratopago", contratopago._name)
                        insc = InscripcionCohorte.objects.get(pk=int(encrypt(request.POST['id'])))
                        if Contrato.objects.filter(status=True, inscripcion=insc, inscripcion__status=True).exists():
                            contrato = Contrato.objects.get(status=True, inscripcion=insc, inscripcion__status=True)
                            contrato.fechacontrato = hoy
                            contrato.formapago_id = int(request.POST['fpago'])
                            contrato.estado = 1
                            contrato.archivocontrato = contratopago
                            contrato.observacion = request.POST['observacion']
                            if contrato.contratolegalizado:
                               contrato.contratolegalizado = False
                            if contrato.respaldoarchivocontrato:
                               contrato.respaldoarchivocontrato = None
                            contrato.save(request)
                            log(u'Adicionó Contrato de : %s' % (insc), request, "edit")

                            detalle = DetalleAprobacionContrato(contrato=contrato,
                                                                  estado_aprobacion=1,
                                                                  observacion=request.POST['observacion'],
                                                                  archivocontrato=contratopago)
                            detalle.save(request)
                            return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar contrato."})

        if action == 'cargarpagareaspirantemaestria':
            try:
                hayarchivos = False
                if 'archivo' in request.FILES:
                    hayarchivos = True
                    descripcionarchivo = 'Pagaré del aspirante'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivo'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar un archivo (Pagaré)."})

                f = ContratoPagoMaestriaForm(request.POST, request.FILES)
                if f.is_valid():
                    if hayarchivos:
                        pagare = request.FILES['archivo']
                        pagare._name = generar_nombre("pagareaspirantemaestriafirmado", pagare._name)
                        insc = InscripcionCohorte.objects.get(pk=int(encrypt(request.POST['id'])))
                        if Contrato.objects.filter(status=True, inscripcion=insc).exists():
                            contrato = Contrato.objects.get(status=True, inscripcion=insc)
                            contrato.fechapagare = hoy
                            contrato.estadopagare = 1
                            contrato.archivopagare = pagare
                            contrato.observacionpagare = request.POST['observacion']
                            contrato.save(request)
                            log(u'Adicionó pagaré de : %s' % (insc), request, "edit")

                            detalle = DetalleAprobacionContrato(contrato=contrato,
                                                                  estado_aprobacion=1,
                                                                  observacion='Nuevo archivo pagaré',
                                                                  espagare=True)
                            detalle.save(request)
                            return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar pagaré."})

        if action == 'pdfcontratopagoprograma':
            try:
                numcontrato = 0
                idins = request.POST['idins']
                admitido = InscripcionCohorte.objects.get(status=True, pk=int(idins))
                registro = Contrato.objects.filter(status=True, inscripcion__id=idins, inscripcion__status=True).last()
                secuenciacp = secuencia_contratopagare(request, datetime.now().year)
                if not registro or not registro.numerocontrato:
                    secuenciacp.secuenciacontrato += 1
                    secuenciacp.save(request)
                    if Contrato.objects.filter(status=True, numerocontrato=secuenciacp.secuenciacontrato, fechacontrato__year=secuenciacp.anioejercicio.anioejercicio).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Error al generar el contrato, intente nuevamente"})
                    else:
                        if Contrato.objects.filter(status=True,inscripcion_id=idins).exists():
                            ct = Contrato.objects.filter(inscripcion_id=idins, status=True,).last()
                            ct.numerocontrato = secuenciacp.secuenciacontrato
                            ct.save(request)
                            log(u'Editó número contrato: %s' % (ct), request, "add")
                        else:
                            ct = Contrato(inscripcion_id=idins, numerocontrato=secuenciacp.secuenciacontrato)
                            ct.save(request)
                            log(u'Adicionó numero contrato: %s' % (ct), request, "add")
                        numcontrato = ct.numerocontrato
                else:
                    if Contrato.objects.get(status=True, inscripcion__id=idins, inscripcion__status=True).numerocontrato:
                        numcontrato = Contrato.objects.get(status=True, inscripcion__id=idins, inscripcion__status=True).numerocontrato

                cont = Contrato.objects.get(status=True, inscripcion__id=idins)

                tipo = 'pdf'
                paRequest = {
                    'idins': admitido.id,
                    'numcontrato': numcontrato
                }

                reporte = None
                if admitido.formapagopac.id == 1:
                    reporte = Reporte.objects.get(id=663)
                elif admitido.formapagopac.id == 2:
                    reporte = Reporte.objects.get(id=664)

                d = run_report_v1(reporte=reporte, tipo=tipo, paRequest=paRequest, request=request)

                if not d['isSuccess']:
                    raise NameError(d['mensaje'])
                else:
                    url_archivo = (SITE_STORAGE + d['data']['reportfile']).replace('\\', '/')
                    url_archivo = (url_archivo).replace('//', '/')
                    _name = generar_nombre(f'contrato_{request.user.username}_{idins}_','descargado')
                    folder = os.path.join(SITE_STORAGE, 'media', 'archivodescargado', '')
                    if not os.path.exists(folder):
                        os.makedirs(folder)
                    folder_save = os.path.join('archivodescargado', '').replace('\\', '/')
                    url_file_generado = f'{folder_save}{_name}.pdf'
                    ruta_creacion = SITE_STORAGE
                    ruta_creacion = ruta_creacion.replace('\\', '/')
                    shutil.copy(url_archivo, ruta_creacion + '/media/' + url_file_generado)

                    cont.archivodescargado = url_file_generado
                    cont.save(request)
                    # return JsonResponse({"result": "ok", 'url': cont.download_descargado()})
                    return JsonResponse({"result": "ok", 'url': d['data']['reportfile']})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al descargar.%s"%(ex)})

        if action == 'pdfpagareprograma':
            try:
                numpagare = 0
                idins = request.POST['idins']
                idconfig = request.POST['idconfig']
                ct = registro = Contrato.objects.filter(status=True, inscripcion__id=idins).first()
                secuenciacp = secuencia_contratopagare(request, datetime.now().year)
                if not registro or not registro.numeropagare:
                    secuenciacp.secuenciapagare += 1
                    secuenciacp.save(request)
                    if Contrato.objects.filter(status=True, numeropagare=secuenciacp.secuenciapagare, fechacontrato__year=secuenciacp.anioejercicio.anioejercicio).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Error al generar el pagaré, intente nuevamente"})
                    else:
                        if Contrato.objects.filter(status=True, inscripcion_id=idins).exists():
                            ct = Contrato.objects.filter(inscripcion_id=idins, status=True, ).last()
                            ct.numeropagare = secuenciacp.secuenciapagare
                            ct.save(request)
                            log(u'Editó número pagaré: %s' % (ct), request, "add")
                        else:
                            ct = Contrato(inscripcion_id=idins, numeropagare=secuenciacp.secuenciapagare)
                            ct.save(request)
                            log(u'Adicionó número pagaré: %s' % (ct), request, "add")
                        numpagare = ct.numeropagare
                else:
                    numpagare = Contrato.objects.filter(status=True,inscripcion__id=idins).last().numeropagare

                qrresult = pagareaspirantemae(idins, idconfig, numpagare)
                if qrresult:
                    if not ct.tablaamortizacion_set.values('id').filter(status=True).exists():
                        financiamiento = ConfigFinanciamientoCohorte.objects.get(pk=idconfig)
                        tablaamortizacion = financiamiento.tablaamortizacioncohortemaestria(idins, datetime.now())
                        des = str(ct.inscripcion.cohortes.maestriaadmision)+' - '+ str(ct.inscripcion.cohortes.descripcion)
                        desmatricula = 'MATRICULA DE POSTGRADO - %s'%des
                        desconvenio = ''
                        if ct.inscripcion.convenio:
                            if ct.inscripcion.convenio.aplicadescuento:
                                desconvenio = 'CONVENIOS POSGRADOS - %s'%des
                        for t in tablaamortizacion:
                            # if t[0] != '':
                            cnombre = ''
                            if t[0] != '':
                                if t[0] > financiamiento.maxnumcuota:
                                    cnombre = desconvenio
                                else:
                                    cnombre = des
                            else:
                                cnombre = desmatricula
                            amortizacion = TablaAmortizacion(
                                                        contrato=ct,
                                                        cuota=t[0] if t[0] != '' else 0,
                                                        nombre=cnombre,
                                                        valor=t[3],
                                                        fecha=t[1] if t[1] != '' else hoy,
                                                        fechavence=t[2] if t[2] != '' else ct.inscripcion.cohortes.fechavencerubro)
                            amortizacion.save(request)
                        log(u'registró tabla de amortización de %s' % (ct), request, "add")
                return JsonResponse({"result": "ok", 'url': qrresult})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al descargar pagaré."})

        if action == 'pdfoficioterminacioncontrato':
            try:
                contrato = Contrato.objects.get(status=True, pk=int(request.POST['idcon']))
                qrresult = oficioterminacioncontrato(request.POST['idcon'])

                url_archivo = (SITE_STORAGE + qrresult[24:]).replace('\\', '/')
                url_archivo = (url_archivo).replace('//', '/')
                _name = generar_nombre(f'oficio_{request.user.username}_{contrato.id}_', 'descargado')
                folder = os.path.join(SITE_STORAGE, 'media', 'archivooficiodescargado', '')
                if not os.path.exists(folder):
                    os.makedirs(folder)
                folder_save = os.path.join('archivooficiodescargado', '').replace('\\', '/')
                url_file_generado = f'{folder_save}{_name}.pdf'
                ruta_creacion = SITE_STORAGE
                ruta_creacion = ruta_creacion.replace('\\', '/')
                shutil.copy(url_archivo, ruta_creacion + '/media/' + url_file_generado)

                contrato.archivooficiodescargado = url_file_generado
                contrato.save(request)
                return JsonResponse({"result": "ok", 'url': qrresult})
            except Exception as ex:
                transaction.set_rollback(True)
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                print(f'${ex.__str__()}')
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'pdfsolicitudhomologacion':
            try:
                postulante = InscripcionCohorte.objects.get(status=True, pk=int(request.POST['idins']))
                eProducto = ProductoSecretaria.objects.get(servicio__id=int(request.POST['idservi']))
                asigselect = request.POST['ids'].split(',')

                if not postulante.subio_requisitos_homologacion():
                    return JsonResponse({"result": "bad", "mensaje": u"Por favor, suba todos los requisitos de homologación obligatorios."})

                eServicio = eProducto.servicio
                valor = Decimal(eProducto.costo).quantize(Decimal('.01'))
                eContentTypeProducto = ContentType.objects.get_for_model(eProducto)

                ePerfilUsuario = PerfilUsuario.objects.filter(status=True, persona=postulante.inscripcionaspirante.persona, inscripcionaspirante__isnull=False).first()
                parametros = {
                    'vqr': postulante.id
                }

                result = generar_codigo_solicitud(eServicio)
                success = result.get('success', False)
                codigo = result.get('codigo', None)
                secuencia = result.get('secuencia', 0)
                suffix = result.get('suffix', None)
                prefix = result.get('prefix', None)
                if not success:
                    raise NameError(u"Código de solicitud no se pudo generar")
                if codigo is None:
                    raise NameError(u"Código de solicitud no se pudo generar")
                if secuencia == 0:
                    raise NameError(u"Secuenia del código de solicitud no se pudo generar")
                if suffix is None:
                    raise NameError(u"Sufijo del código de solicitud no se pudo generar")
                if prefix is None:
                    raise NameError(u"Prefijo del código de solicitud no se pudo generar")

                eSolicitudes = Solicitud.objects.filter(Q(en_proceso=True) | Q(estado__in=[23]), status=True,
                                                        perfil_id=ePerfilUsuario.pk, servicio_id=eServicio.pk,
                                                        origen_content_type_id=eContentTypeProducto.pk,
                                                        inscripcioncohorte=postulante,
                                                        origen_object_id=eProducto.id).exclude(servicio__proceso=8)
                if not eSolicitudes.values("id").exists():

                    if asigselect[0] == '':
                        return JsonResponse({"result": "bad", "mensaje": u"Por favor, seleccione al menos una asignatura a homologar."})

                    eSolicitud = Solicitud(codigo=codigo,
                                           secuencia=secuencia,
                                           prefix=prefix,
                                           suffix=suffix,
                                           perfil_id=ePerfilUsuario.pk,
                                           servicio_id=eServicio.pk,
                                           origen_content_type=eContentTypeProducto,
                                           origen_object_id=eProducto.pk,
                                           descripcion=f'Solicitud ({codigo}) de Homologación de asignaturas Posgrado con código {eProducto.codigo} - {eProducto.descripcion}',
                                           fecha=datetime.now().date(),
                                           hora=datetime.now().time(),
                                           estado=23,
                                           cantidad=1,
                                           valor_unitario=valor,
                                           subtotal=valor,
                                           iva=0,
                                           descuento=0,
                                           en_proceso=False,
                                           parametros=parametros,
                                           tiempo_cobro=eProducto.tiempo_cobro,
                                           inscripcioncohorte=postulante)
                    eSolicitud.save(request)
                    log(u'Adicionó solicitud de homologación: %s del aspirante %s' % (eSolicitud, postulante), request, "add")

                    asigselect = request.POST['ids'].split(',')

                    for asi in asigselect:
                        asignaturamalla = AsignaturaMalla.objects.get(status=True, pk=int(asi))
                        eSolicitudAsig = SolicitudAsignatura(
                            solicitud=eSolicitud,
                            asignaturamalla=asignaturamalla,
                            estado=1
                        )
                        eSolicitudAsig.save()
                        log(u'Adicionó asignaturas de homologación: %s del aspirante %s' % (eSolicitudAsig, postulante), request, "add")

                else:
                    eSolicitud = Solicitud.objects.filter(Q(en_proceso=True) | Q(estado__in=[23]), status=True,
                                                            perfil_id=ePerfilUsuario.pk, servicio_id=eServicio.pk,
                                                            origen_content_type_id=eContentTypeProducto.pk,
                                                            inscripcioncohorte=postulante,
                                                            origen_object_id=eProducto.id).exclude(servicio__proceso=8).first()

                    if asigselect[0] != '':
                        for asi in asigselect:
                            asignaturamalla = AsignaturaMalla.objects.get(status=True, pk=int(asi))
                            eSolicitudAsig = SolicitudAsignatura(
                                solicitud=eSolicitud,
                                asignaturamalla=asignaturamalla,
                                estado=1
                            )
                            eSolicitudAsig.save()
                            log(u'Adicionó asignaturas de homologación: %s del aspirante %s' % (eSolicitudAsig, postulante), request, "add")

                tipo = 'pdf'
                paRequest = {
                    'idins': eSolicitud.id,
                }

                reporte = Reporte.objects.get(id=668)

                d = run_report_v1(reporte=reporte, tipo=tipo, paRequest=paRequest, request=request)

                if not d['isSuccess']:
                    return JsonResponse({"result": "bad", "mensaje": d['mensaje']})
                else:
                    urlsga = 'https://sga.unemi.edu.ec/'
                    url_archivo = (urlsga + d['data']['reportfile']).replace('\\', '/')
                    url_archivo = (url_archivo).replace('//', '/')
                    _name = generar_nombre(f'soli_hp_{request.user.username}_{eSolicitud.id}_','descargado')
                    folder = os.path.join(urlsga, 'media', 'archivohomologaciondescargado', '')
                    if not os.path.exists(folder):
                        os.makedirs(folder)
                    folder_save = os.path.join('archivohomologaciondescargado', '').replace('\\', '/')
                    url_file_generado = f'{folder_save}{_name}.pdf'
                    ruta_creacion = urlsga
                    ruta_creacion = ruta_creacion.replace('\\', '/')
                    shutil.copy(url_archivo, ruta_creacion + '/media/' + url_file_generado)

                    eSolicitud.archivo_solicitud = url_file_generado
                    eSolicitud.save(request)

                    if not HistorialSolicitud.objects.filter(status=True, solicitud=eSolicitud):
                        eHistorialSolicitud = HistorialSolicitud(solicitud=eSolicitud,
                                                                 observacion=eSolicitud.descripcion,
                                                                 fecha=eSolicitud.fecha,
                                                                 hora=eSolicitud.hora,
                                                                 estado=eSolicitud.estado,
                                                                 responsable=eSolicitud.inscripcioncohorte.inscripcionaspirante.persona,
                                                                 archivo=eSolicitud.archivo_solicitud)
                        eHistorialSolicitud.save(request)

                    return JsonResponse({"result": "ok", 'url': eSolicitud.download_descargado()})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al descargar.%s"%(ex)})

        if action == 'cargarcombo_titulacion':
            try:
                persona = Persona.objects.filter(pk=request.POST['id']).last()
                lista = []
                if persona:
                    for titulo in persona.titulacion_set.filter(status=True, educacionsuperior=True):
                        lista.append([titulo.id, titulo.titulo.__str__()])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'extraercampos':
            try:
                titulacion = None
                cantexperiencia = 0
                ce = 'Campo Específico: '
                insc = InscripcionCohorte.objects.get(pk=request.POST['insc'])
                if request.POST['id']:
                    titulacion = Titulacion.objects.filter(pk=request.POST['id']).last()
                if titulacion:
                    campotitulos = CamposTitulosPostulacion.objects.filter(status=True, titulo=titulacion.titulo)
                    for campotitulo in campotitulos:
                        for campoe in campotitulo.campoespecifico.all():
                            ce = ce + campoe.__str__() + ' | '
                return JsonResponse({'result': 'ok', 'ce': ce})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

        if action == 'validarperfilingreso':
            try:
                titulacion = None
                cantexperiencia = 0
                # ce = 'Campo Específico: '
                insc = InscripcionCohorte.objects.get(pk=request.POST['insc'])
                if request.POST['id']:
                    titulacion = Titulacion.objects.filter(pk=request.POST['id']).last()
                # if titulacion:
                #     campotitulos = CamposTitulosPostulacion.objects.filter(status=True, titulo=titulacion.titulo)
                #     for campotitulo in campotitulos:
                #         for campoe in campotitulo.campoespecifico.all():
                #             ce = ce + campoe.__str__() + ' | '
                perfilingreso = None
                if 'idperfil' in request.POST and request.POST['idperfil']:
                    perfilingreso = DetallePerfilIngreso.objects.get(pk=request.POST['idperfil'])
                if perfilingreso:
                    cantexperiencia = request.POST['cantexperiencia'] if 'cantexperiencia' in request.POST and request.POST['cantexperiencia'] else 0
                    if not perfilingreso.alltitulos:
                        # if not insc.tiulacionaspirante:
                        # todos los campos especificos de los titulos de perfil
                        listcetituloperfil = CamposTitulosPostulacion.objects.values_list('campoespecifico__nombre', flat=True).filter(titulo__in=perfilingreso.titulo.all()).distinct()
                        # todos los campos especificos del titulo del postulante
                        listcetitulopos = CamposTitulosPostulacion.objects.values_list('campoespecifico__nombre', flat=True).filter(titulo=titulacion.titulo).distinct()
                        aplicamaestria = False
                        for campoesp in listcetitulopos:
                            if campoesp in listcetituloperfil:
                               aplicamaestria = True
                        if not aplicamaestria:
                            titulosaplica = ''
                            campotitulos = CamposTitulosPostulacion.objects.filter(status=True, titulo__in=perfilingreso.titulo.all()).distinct()
                            for campotitulo in campotitulos:
                                titulosaplica = titulosaplica +'<br> * '+campotitulo.__str__().title()
                                # for campoes in campotitulo.campoespecifico.all():
                                #     titulosaplica = titulosaplica + campoes.__str__().capitalize() + ' | '
                            if not int(cantexperiencia) > 0:
                                return JsonResponse({'result': 'noaplica', 'titulos': titulosaplica})
                    if perfilingreso.experiencia: #si el perfil cuenta con experiencia
                        if int(cantexperiencia) >= 0:
                            experienciamaestria = perfilingreso.cantidadexperiencia
                            if not insc.cantexperiencia >= experienciamaestria:
                                if not float(cantexperiencia) >= float(experienciamaestria):
                                    return JsonResponse({'result': 'noexperiencia', 'cantidad': experienciamaestria})
                    if titulacion:
                        insc.tiulacionaspirante = titulacion
                    if int(cantexperiencia) > 0:
                        insc.cantexperiencia = cantexperiencia
                    insc.save(request)
                    log(u'Actualizó titulación y experiencia de la inscripción: %s' % insc, request, "edit")

                    if insc.tiulacionaspirante and titulacion.registroarchivo:
                        requisitosmaestria = RequisitosMaestria.objects.filter(status=True, cohorte=insc.cohortes, requisito__id__in=[52, 6, 14, 16, 4, 29]).first()
                        if not EvidenciaRequisitosAspirante.objects.filter(requisitos=requisitosmaestria,
                                                                           inscripcioncohorte=insc,
                                                                           status=True).exists():
                            requisitomaestria = EvidenciaRequisitosAspirante(requisitos=requisitosmaestria,
                                                                             inscripcioncohorte=insc)
                            requisitomaestria.save(request)
                            requisitomaestria.archivo = titulacion.registroarchivo
                            requisitomaestria.save(request)
                            log(u'Adicionó requisito de maestria aspirante: %s' % requisitomaestria.requisitos, request, "add")
                            detalle = DetalleEvidenciaRequisitosAspirante(evidencia=requisitomaestria,
                                                                          estadorevision=1,
                                                                          # persona=inscripcioncohorte.inscripcionaspirante.persona,
                                                                          fecha=datetime.now().date(),
                                                                          observacion='Título validado en el perfil de ingreso (afinidad)')
                            detalle.save(request)

                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

        elif action == 'addtitulacionpos':
            try:
                with transaction.atomic():
                    persona = Persona.objects.get(pk=int(request.POST['idpersona']))
                    f = TitulacionPersonaAdmisionPosgradoForm(request.POST, request.FILES)
                    if 'registroarchivo' in request.FILES:
                        registroarchivo = request.FILES['registroarchivo']
                        extencion1 = registroarchivo._name.split('.')
                        exte1 = extencion1[1]
                        if registroarchivo.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                        if not exte1 == 'pdf' and not exte1 == 'png' and not exte1 == 'jpg' and not exte1 == 'jpeg' and not exte1 == 'jpg':
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Archivo SENESCYT solo en formato .pdf, jpg, jpeg, png"})
                    if f.is_valid():
                        if persona:
                            titulo = None
                            if request.POST['registrartitulo'] == 'true':

                                if Titulo.objects.filter(nombre__unaccent=f.cleaned_data['nombre'].upper()).exists():
                                    return JsonResponse({"result": "bad", "mensaje": u"Imposible guardar registro. El título %s ya se encuentra registrado." % (f.cleaned_data['nombre'])})
                                if Titulo.objects.filter(nombre=f.cleaned_data['nombre'].upper(), nivel=f.cleaned_data['nivel']).exists():
                                    return JsonResponse({"result": "bad", "mensaje": u"Imposible guardar registro. El título %s ya se encuentra registrado." % (f.cleaned_data['nombre'])})
                                if f.cleaned_data['nivel'].id == 4 and not f.cleaned_data['grado']:
                                    return JsonResponse({"result": "bad", "mensaje": u"Por favor seleccione grado."})

                                titulo = Titulo(nombre=f.cleaned_data['nombre'],
                                                abreviatura=f.cleaned_data['abreviatura'],
                                                nivel=f.cleaned_data['nivel'],
                                                grado=f.cleaned_data['grado'],
                                                areaconocimiento=f.cleaned_data['campoamplio'][0],
                                                subareaconocimiento=f.cleaned_data['campoespecifico'][0],
                                                subareaespecificaconocimiento=f.cleaned_data['campodetallado'][0]
                                                )
                                titulo.save(request)
                                titulacion = Titulacion(persona=persona,
                                                        titulo=titulo,
                                                        registro=f.cleaned_data['registro'],
                                                        # pais=f.cleaned_data['pais'],
                                                        # provincia=f.cleaned_data['provincia'],
                                                        # canton=f.cleaned_data['canton'],
                                                        # parroquia=f.cleaned_data['parroquia'],
                                                        educacionsuperior=True,
                                                        institucion=f.cleaned_data['institucion'])
                                titulacion.save(request)
                            else:
                                titulo = f.cleaned_data['titulo']
                                if Titulacion.objects.filter(persona=persona, titulo=titulo).exists():
                                    raise NameError("No se puede guardar título. Usted ya tiene registrado su título %s." % (titulo))
                                titulacion = Titulacion(persona=persona,
                                                        titulo=f.cleaned_data['titulo'],
                                                        registro=f.cleaned_data['registro'],
                                                        # pais=f.cleaned_data['pais'],
                                                        # provincia=f.cleaned_data['provincia'],
                                                        # canton=f.cleaned_data['canton'],
                                                        # parroquia=f.cleaned_data['parroquia'],
                                                        educacionsuperior=True,
                                                        institucion=f.cleaned_data['institucion'])
                                titulacion.save(request)
                        if 'registroarchivo' in request.FILES:
                            newfile2 = request.FILES['registroarchivo']
                            if newfile2:
                                newfile2._name = generar_nombre("archivosenecyt_", newfile2._name)
                                titulacion.registroarchivo = newfile2
                                titulacion.save(request)
                        campotitulo = None
                        if CamposTitulosPostulacion.objects.filter(status=True, titulo=titulo).exists():
                            campotitulo = CamposTitulosPostulacion.objects.filter(status=True, titulo=titulo).first()
                        else:
                            campotitulo = CamposTitulosPostulacion(titulo=titulo)
                            campotitulo.save(request)

                        if not f.cleaned_data['campoamplio']:
                            if titulo.areaconocimiento:
                                if not campotitulo.campoamplio.filter(id=titulo.areaconocimiento.id):
                                    campotitulo.campoamplio.add(titulo.areaconocimiento)
                            else:
                                raise NameError("El título %s no cuenta con campo amplio, específico y detallado. Favor comuníquese con servicios informáticos (servicios.informaticos@unemi.edu.ec) para actualizar los datos del título." % (titulo))
                            if titulo.subareaconocimiento:
                                if not campotitulo.campoespecifico.filter(id=titulo.subareaconocimiento.id):
                                    campotitulo.campoespecifico.add(titulo.subareaconocimiento)
                            if titulo.subareaespecificaconocimiento:
                                if not campotitulo.campodetallado.filter(id=titulo.subareaespecificaconocimiento.id):
                                    campotitulo.campodetallado.add(titulo.subareaespecificaconocimiento)
                        else:
                            for ca in f.cleaned_data['campoamplio']:
                                if not campotitulo.campoamplio.filter(id=ca.id):
                                    campotitulo.campoamplio.add(ca)
                            for ce in f.cleaned_data['campoespecifico']:
                                if not campotitulo.campoespecifico.filter(id=ce.id):
                                    campotitulo.campoespecifico.add(ce)
                            for cd in f.cleaned_data['campodetallado']:
                                if not campotitulo.campodetallado.filter(id=cd.id):
                                    campotitulo.campodetallado.add(cd)
                        campotitulo.save(request)
                        log(u'Adicionó titulación admisión de posgrado: %s' % titulacion, request, "add")
                        return JsonResponse({"result": "ok", "idpersona": persona.id})
                    else:
                        # raise NameError('Error')
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s" % (ex)})

        elif action == 'existetablaamortizacion':
            try:
                existe = False
                if 'id' in request.POST and request.POST['id']:
                   contrato = Contrato.objects.filter(pk=request.POST['id']).last()
                if contrato:
                    tablaamortizacion = contrato.tablaamortizacion_set.values('id').filter(status=True)
                    if tablaamortizacion:
                        existe = True
                if existe:
                    return JsonResponse({'result': 'ok'})
                else:
                    return JsonResponse({"result": "bad"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

        elif action == 'actualizarcanal':
            try:
                inscripcion = InscripcionCohorte.objects.get(status=True, id=int(request.POST['idins']))
                canal = CanalInformacionMaestria.objects.get(status=True, id=int(request.POST['id']))

                inscripcion.canal = canal
                inscripcion.save(request)
                log(u'Actualizó el canal de información del prospecto: %s' % inscripcion, request, "edit")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

        elif action == 'addarchivorequi':
            try:
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})

                f = EvidenciaRequisitoAdmisionForm(request.POST, request.FILES)
                if f.is_valid():
                    inscripcioncohorte = InscripcionCohorte.objects.get(pk=int(encrypt(request.POST['idins'])))
                    requisitosmaestria = RequisitosMaestria.objects.get(pk=int(encrypt(request.POST['id'])))
                    if not EvidenciaRequisitosAspirante.objects.filter(requisitos=requisitosmaestria, inscripcioncohorte=inscripcioncohorte, status=True).exists():
                        requisitomaestria = EvidenciaRequisitosAspirante(requisitos=requisitosmaestria,
                                                                         inscripcioncohorte=inscripcioncohorte)
                        requisitomaestria.save(request)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("requisitopgrado_", newfile._name)
                            requisitomaestria.archivo = newfile
                            requisitomaestria.save(request)
                        log(u'Adicionó requisito de maestria aspirante: %s' % requisitomaestria.requisitos, request, "add")
                        detalle = DetalleEvidenciaRequisitosAspirante(evidencia=requisitomaestria,
                                                                      estadorevision=1,
                                                                      # persona=inscripcioncohorte.inscripcionaspirante.persona,
                                                                      fecha=datetime.now().date(),
                                                                      observacion=f.cleaned_data['observacion'])
                        detalle.save(request)

                        if inscripcioncohorte.total_evidence_lead_fi():
                            inscripcioncohorte.todosubidofi = True
                            inscripcioncohorte.tienerechazofi = False
                            inscripcioncohorte.save()

                        if inscripcioncohorte.total_evidence_lead():
                            inscripcioncohorte.todosubido = True
                            if inscripcioncohorte.tiporespuesta and inscripcioncohorte.tiporespuesta.id == 6:
                                inscripcioncohorte.tiporespuesta.id = 5
                            inscripcioncohorte.tienerechazo = False
                            inscripcioncohorte.save()

                            if inscripcioncohorte.estado_aprobador != 2:
                                asunto = u"SUBIÓ TODOS LOS REQUISITOS DE ADMISIÓN"
                                observacion = f'Se le comunica que el postulante {inscripcioncohorte.inscripcionaspirante.persona} con cédula {inscripcioncohorte.inscripcionaspirante.persona.cedula} ha subido todos sus requisitos de admisión. Por favor, pre-aprobar los requisitos del postulante. Puede dar clic en la URL para ser redirigido directamente al postulante pendiente de pre-aprobación.'
                                para = inscripcioncohorte.asesor.persona
                                perfiu = inscripcioncohorte.asesor.perfil_administrativo()

                                notificacion3(asunto, observacion, para, None,
                                              '/comercial?action=leadsporpreaprobar&s=' + inscripcioncohorte.inscripcionaspirante.persona.cedula,
                                              inscripcioncohorte.pk, 1,
                                              'sga', InscripcionCohorte, perfiu, request)

                        return JsonResponse({"result": False}, safe=False)
                    else:
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            if newfile.size > 10485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                            else:
                                newfiles = request.FILES['archivo']
                                newfilesd = newfiles._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if not ext.lower() == '.pdf':
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        f = RequisitosMaestriaForm(request.POST, request.FILES)
                        requisito = EvidenciaRequisitosAspirante.objects.get(requisitos=requisitosmaestria, inscripcioncohorte=inscripcioncohorte, status=True)
                        if f.is_valid():
                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                newfile._name = generar_nombre("requisitopgrado_", newfile._name)
                                requisito.archivo = newfile
                                requisito.save(request)
                            detalle = DetalleEvidenciaRequisitosAspirante(evidencia=requisito,
                                                                          estadorevision=1,
                                                                          fecha=datetime.now().date(),
                                                                          observacion=f.cleaned_data['observacion'])
                            detalle.save(request)
                            log(u'Editó requisito de maestría aspirante: %s' % requisito, request, "edit")

                            if inscripcioncohorte.total_evidence_lead():
                                inscripcioncohorte.todosubido = True
                                if inscripcioncohorte.tiporespuesta and inscripcioncohorte.tiporespuesta.id == 6:
                                    inscripcioncohorte.tiporespuesta_id = 5
                                inscripcioncohorte.tienerechazo = False
                                inscripcioncohorte.save()

                            if inscripcioncohorte.total_evidence_lead_fi():
                                inscripcioncohorte.todosubidofi = True
                                inscripcioncohorte.tienerechazofi = False
                                inscripcioncohorte.save()

                            if inscripcioncohorte.estado_aprobador != 2:
                                asunto = u"SUBIÓ TODOS LOS REQUISITOS DE ADMISIÓN"
                                observacion = f'Se le comunica que el postulante {inscripcioncohorte.inscripcionaspirante.persona} con cédula {inscripcioncohorte.inscripcionaspirante.persona.cedula} ha subido todos sus requisitos de admisión. Por favor, pre-aprobar los requisitos del postulante. Puede dar clic en la URL para ser redirigido directamente al postulante pendiente de pre-aprobación.'
                                para = inscripcioncohorte.asesor.persona
                                perfiu = inscripcioncohorte.asesor.perfil_administrativo()

                                notificacion3(asunto, observacion, para, None,
                                              '/comercial?action=leadsporpreaprobar&s=' + inscripcioncohorte.inscripcionaspirante.persona.cedula,
                                              inscripcioncohorte.pk, 1,
                                              'sga', InscripcionCohorte, perfiu, request)

                            return JsonResponse({"result": False}, safe=False)
                        else:
                            return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                                 "message": "Error en el formulario"})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addarchivorequi2':
            try:
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})

                f = EvidenciaRequisitoAdmisionForm(request.POST, request.FILES)
                if f.is_valid():
                    inscripcioncohorte = InscripcionCohorte.objects.get(pk=int(encrypt(request.POST['idins'])))
                    requisitosmaestria = RequisitosMaestria.objects.get(pk=int(encrypt(request.POST['id'])))
                    if not EvidenciaRequisitosAspirante.objects.filter(requisitos=requisitosmaestria, inscripcioncohorte=inscripcioncohorte, status=True).exists():
                        requisitomaestria = EvidenciaRequisitosAspirante(requisitos=requisitosmaestria,
                                                                         inscripcioncohorte=inscripcioncohorte)
                        requisitomaestria.save(request)
                        log(u'Adicionó requisito de homologación: %s' % requisitomaestria.requisitos, request, "add")
                    else:
                        requisitomaestria = EvidenciaRequisitosAspirante.objects.filter(requisitos=requisitosmaestria,
                                                                         inscripcioncohorte=inscripcioncohorte).order_by('-id').first()

                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("requisitopgrado_", newfile._name)
                        requisitomaestria.archivo = newfile
                        requisitomaestria.save(request)

                    detalle = DetalleEvidenciaRequisitosAspirante(evidencia=requisitomaestria,
                                                                  estadorevision=1,
                                                                  persona=persona,
                                                                  fecha=datetime.now().date(),
                                                                  observacion=f.cleaned_data['observacion'])
                    detalle.save(request)
                    log(u'Adicionó evidencia de requisito de homologación: %s' % detalle, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'cargarrequisitoconvenio':
            try:
                from posgrado.models import EvidenciaRequisitoConvenio, DetalleEvidenciaRequisitoConvenio
                from posgrado.forms import RequisitoConvenioAspiranteForm
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})

                f = RequisitoConvenioAspiranteForm(request.POST, request.FILES)
                if f.is_valid():
                    insc = InscripcionCohorte.objects.get(pk=int(encrypt(request.POST['id'])))
                    archivoconvenio = request.FILES['archivo']
                    archivoconvenio._name = generar_nombre("requisitoconvenio", archivoconvenio._name)
                    if EvidenciaRequisitoConvenio.objects.filter(inscripcion = insc, convenio=insc.convenio, status=True).exists():
                        evidencia = EvidenciaRequisitoConvenio.objects.filter(inscripcion = insc, convenio=insc.convenio, status =True).last()
                        evidencia.archivo = archivoconvenio
                        evidencia.save(request)
                    else:
                        evidencia = EvidenciaRequisitoConvenio(inscripcion = insc, convenio = insc.convenio, archivo = archivoconvenio)
                        evidencia.save(request)
                    detalle = DetalleEvidenciaRequisitoConvenio(evidenciarequisitoconvenio=evidencia,
                                                                  estado_aprobacion=1,
                                                                  archivo=archivoconvenio,
                                                                  observacion='Nuevo archivo requisito convenio')
                    detalle.save(request)
                    log(u'Adicionó requisito convenio de : %s' % (insc), request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar pagaré."})

        elif action == 'confirmarmodalidadpago':
            try:
                admitido = InscripcionCohorte.objects.get(status=True, pk=int(request.POST['id']))
                formapago = TipoFormaPagoPac.objects.get(status=True, pk=int(request.POST['fp']))
                admitido.aceptado = True
                admitido.formapagopac = formapago
                admitido.save(request)

                observacion = ''
                if int(request.POST['fp']) == 1:
                    observacion = 'Aceptó modalidad de pago por contado'
                else:
                    observacion = 'Aceptó modalidad de pago diferido'

                deta = DetalleAprobacionFormaPago(inscripcion_id=admitido.id,
                                                  formapagopac=formapago,
                                                  estadoformapago=1,
                                                  observacion=observacion,
                                                  persona=persona)
                deta.save(request)
                log(u'Confirmó la modalidad de pago por contado: %s' % admitido, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'firmar_contrato_posgrado':
            try:
                id_ins = request.POST.get('id_ins',None)
                integrante = InscripcionCohorte.objects.get(status=True, pk=int(id_ins))
                data['hoy'] = hoy = datetime.now()
                certificado = request.FILES["firma"]
                contrasenaCertificado = request.POST['palabraclave']
                extension_certificado = os.path.splitext(certificado.name)[1][1:]
                bytes_certificado = certificado.read()

                contrato = Contrato.objects.get(status=True, inscripcion=integrante)
                name_file = f'contrato_firmado{id_ins}_{contrato.numerocontrato}.pdf'

                # archivo_borrar = contrato.archivodescargado.url
                texto = f'{integrante.inscripcionaspirante.persona.cedula}'
                x,y, numpaginafirma = obtener_posicion_x_y_saltolinea(contrato.archivodescargado.url, texto)
                datau = JavaFirmaEc(
                    archivo_a_firmar=contrato.archivodescargado, archivo_certificado=bytes_certificado,
                    extension_certificado=extension_certificado,
                    password_certificado=contrasenaCertificado,
                    page=int(numpaginafirma), reason='', lx=x+5, ly=y+20
                )

                if datau.datos_del_certificado['cedula'] == integrante.inscripcionaspirante.persona.cedula:
                    documento_a_firmar = io.BytesIO()
                    documento_a_firmar.write(datau.sign_and_get_content_bytes())
                    documento_a_firmar.seek(0)
                    contrato.archivocontrato.save(f'{name_file.replace(".pdf","")}_firmado.pdf',ContentFile(documento_a_firmar.read()))

                    contrato.estado = 2
                    contrato.save(request)
                    detalle = DetalleAprobacionContrato(contrato=contrato,
                                                        estado_aprobacion=2,
                                                        fecha_aprobacion=datetime.now(),
                                                        observacion='Su contrato ha sido firmado correctamente.',
                                                        archivocontrato=contrato.archivocontrato,
                                                        persona=persona)
                    detalle.save(request)

                    asunto = u"CONTRATO FIRMADO"
                    observacion = f'Se le comunica que el contrato de {integrante.formapagopac.descripcion} del admitido {integrante.inscripcionaspirante.persona} con cédula {integrante.inscripcionaspirante.persona.cedula} han sido firmado correctamente. Por favor, dar seguimiento en la siguiente fase.'
                    para = integrante.asesor.persona
                    perfiu = integrante.asesor.perfil_administrativo()

                    notificacion3(asunto, observacion, para, None,
                                  '/comercial?s=' + integrante.inscripcionaspirante.persona.cedula,
                                  integrante.pk, 1,
                                  'sga', InscripcionCohorte, perfiu, request)

                    finan = Persona.objects.get(status=True, pk=24145)
                    para2 = finan
                    perfiu2 = finan.perfilusuario_administrativo()
                    url = ''
                    if integrante.formapagopac.id == 2:
                        url = '/comercial?s=' + integrante.inscripcionaspirante.persona.cedula
                    else:
                        url = '/comercial?action=prospectoscontado&s=' + integrante.inscripcionaspirante.persona.cedula

                    notificacion3(asunto, observacion, para2, None,
                                  url,
                                  integrante.pk, 1,
                                  'sga', InscripcionCohorte, perfiu2, request)

                    return JsonResponse({'result':False,'to':f'/alu_requisitosmaestria?action=listadorequisitosinscripcion&idinscripcioncohorte={encrypt(id_ins)}&next={encrypt(6)}'})
                else:
                    return JsonResponse({'result': True, 'mensaje': f"La firma ingresada no pertenece al admitido {integrante.inscripcionaspirante.persona} con número de cédula {integrante.inscripcionaspirante.persona.cedula}"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f"{ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}"})

        elif action == 'firmar_oficio_posgrado':
            try:
                id_con = request.POST.get('id_con',None)
                contrato = Contrato.objects.get(status=True, pk=int(id_con))
                integrante = InscripcionCohorte.objects.get(status=True, pk=contrato.inscripcion.id)

                certificado = request.FILES["firma2"]
                contrasenaCertificado = request.POST['palabraclave2']
                motivo = int(request.POST['id_motivo'])
                extension_certificado = os.path.splitext(certificado.name)[1][1:]
                bytes_certificado = certificado.read()

                contrato = Contrato.objects.get(status=True, inscripcion=integrante)
                name_file = f'oficio_firmado{integrante.id}_{contrato.numerocontrato}.pdf'

                # archivo_borrar = contrato.archivodescargado.url
                texto = 'Atentamente'
                x,y, numpaginafirma = obtener_posicion_x_y_saltolinea(contrato.archivooficiodescargado.url, texto)
                datau = JavaFirmaEc(
                    archivo_a_firmar=contrato.archivooficiodescargado, archivo_certificado=bytes_certificado,
                    extension_certificado=extension_certificado,
                    password_certificado=contrasenaCertificado,
                    page=int(numpaginafirma), reason='', lx=x+5, ly=y+50
                ).sign_and_get_content_bytes()
                documento_a_firmar = io.BytesIO()
                documento_a_firmar.write(datau)
                documento_a_firmar.seek(0)
                contrato.archivooficio.save(f'{name_file.replace(".pdf","")}_firmado.pdf',ContentFile(documento_a_firmar.read()))

                contrato.estado = 4
                contrato.motivo_terminacion = motivo
                contrato.save(request)
                detalle = DetalleAprobacionContrato(contrato=contrato,
                                                    estado_aprobacion=4,
                                                    fecha_aprobacion=datetime.now(),
                                                    observacion='Su oficio ha sido firmado correctamente.',
                                                    archivocontrato=contrato.archivooficio,
                                                    persona=persona,
                                                    esoficio=True,
                                                    motivo_terminacion=motivo)
                detalle.save(request)

                url = ''
                url2 = ''
                if integrante.vendido:
                    url = '/comercial?action=ventasobtenidas&s=' + integrante.inscripcionaspirante.persona.cedula
                else:
                    url = '/comercial?s=' + integrante.inscripcionaspirante.persona.cedula

                asunto = u"OFICIO DE TERMINACIÓN DE CONTRATO FIRMADO"
                observacion = f'Se le comunica que el oficio de terminación de contrato de {integrante.formapagopac.descripcion} del admitido {integrante.inscripcionaspirante.persona} con cédula {integrante.inscripcionaspirante.persona.cedula} han sido firmado correctamente. Por favor, dar seguimiento en la siguiente fase.'
                para = integrante.asesor.persona
                perfiu = integrante.asesor.perfil_administrativo()

                notificacion3(asunto, observacion, para, None,
                              url,
                              integrante.pk, 1,
                              'sga', InscripcionCohorte, perfiu, request)

                finan = Persona.objects.get(status=True, pk=24145)
                para2 = finan
                perfiu2 = finan.perfilusuario_administrativo()

                if integrante.tiene_matricula_cohorte():
                    url2 = '/comercial?action=leadsmatriculados&s=' + integrante.inscripcionaspirante.persona.cedula
                else:
                    if integrante.formapagopac.id == 2:
                        url2 = '/comercial?s=' + integrante.inscripcionaspirante.persona.cedula
                    else:
                        url2 = '/comercial?action=prospectoscontado&s=' + integrante.inscripcionaspirante.persona.cedula

                notificacion3(asunto, observacion, para2, None,
                              url2,
                              integrante.pk, 1,
                              'sga', InscripcionCohorte, perfiu2, request)

                return JsonResponse({'result':False,'to':f'/alu_requisitosmaestria?action=listadorequisitosinscripcion&idinscripcioncohorte={encrypt(integrante.id)}&next={encrypt(6)}'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f"{ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}"})

        elif action == 'adddatospersonales':
            try:
                if PerfilInscripcion.objects.filter(persona=persona).exists():
                    ePerfilInscripcion = PerfilInscripcion.objects.get(persona=persona)
                else:
                    ePerfilInscripcion = PerfilInscripcion(persona=persona,
                                                           tienediscapacidad=False)
                    ePerfilInscripcion.save()

                f = DatosPersonalesMaestranteForm(request.POST, request.FILES)
                if not f.is_valid():
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        raise NameError("Error, el tamaño del archivo de cédula es mayor a 4 Mb.")
                    if not exte.lower() == 'pdf':
                        raise NameError("Solo se permiten archivos .pdf")

                    persona.mi_perfil().archivo = arch

                ePerfilInscripcion.tienediscapacidad = f.cleaned_data['tienediscapacidad']
                ePerfilInscripcion.tipodiscapacidad = f.cleaned_data['tipodiscapacidad']
                ePerfilInscripcion.porcientodiscapacidad = f.cleaned_data['porcientodiscapacidad'] if f.cleaned_data['porcientodiscapacidad'] is not None else 0
                ePerfilInscripcion.carnetdiscapacidad = f.cleaned_data['carnetdiscapacidad']
                ePerfilInscripcion.raza = f.cleaned_data['raza']
                ePerfilInscripcion.nacionalidadindigena = f.cleaned_data['nacionalidadindigena']
                ePerfilInscripcion.save(request)

                persona.paisnacimiento = f.cleaned_data['paisori']
                persona.provincianacimiento = f.cleaned_data['provinciaori']
                persona.cantonnacimiento = f.cleaned_data['cantonori']
                persona.pais = f.cleaned_data['paisresi']
                persona.provincia = f.cleaned_data['provinciaresi']
                persona.canton = f.cleaned_data['cantonresi']
                persona.lgtbi = f.cleaned_data['lgtbi']
                persona.save(request)

                log(u'Modifico datos personales: %s' % persona, request, "edit")
                return JsonResponse({'result': False, 'mensaje': 'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos: {ex}'})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            if action == 'cargararchivo':
                try:
                    data['title'] = u'Evidencias de requisitos de maestría'
                    data['id'] = request.GET['id']
                    if 'fp' in request.GET:
                        data['fpago'] = request.GET['fp']
                    data['idevidencia'] = request.GET['idevidencia']
                    requisito = RequisitosMaestria.objects.get(pk=int(request.GET['idevidencia']), status=True)
                    form = RequisitosMaestriaForm()
                    data['form'] = form
                    template = get_template("alu_requisitosmaestria/add_requisitomaestria.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, "nombre": "SUBIR DOCUMENTO DE REQUISITO " + str(requisito.requisito.nombre)})
                except Exception as ex:
                    pass

            if action == 'cargararchivobecas':
                try:
                    data['title'] = u'Evidencias de requisitos de Solicitud Descuento'
                    data['id'] = request.GET['id']
                    data['idevidencia'] = request.GET['idevidencia']
                    data['idinscripcion'] = request.GET['idinscripcion']
                    requisito = RequisitosDetalleConfiguracionDescuentoPosgrado.objects.get(pk=int(request.GET['idevidencia']), status=True)
                    form = RequisitosMaestriaForm()
                    data['form'] = form
                    template = get_template("alu_requisitosmaestria/add_requisitomaestriabecas.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, "nombre": "SUBIR DOCUMENTO DE REQUISITO " + str(requisito.requisito)})
                except Exception as ex:
                    pass

            if action == 'cargararchivoimagen':
                try:
                    data['title'] = u'Evidencias de requisitos de maestría'
                    data['id'] = request.GET['id']
                    if 'fp' in request.GET:
                        data['fpago'] = request.GET['fp']
                    data['idevidencia'] = request.GET['idevidencia']
                    requisito = RequisitosMaestria.objects.get(pk=int(request.GET['idevidencia']), status=True)
                    form = RequisitosMaestriaImgForm()
                    data['form'] = form
                    template = get_template("alu_requisitosmaestria/add_requisitomaestriaimagen.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, "nombre": "SUBIR DOCUMENTO DE REQUISITO " + str(requisito.requisito.nombre)})
                except Exception as ex:
                    pass

            if action == 'subirpago':
                try:
                    data['title'] = u'Evidencias de pago exámen'
                    data['id'] = request.GET['id']
                    form = RequisitosMaestriaForm()
                    data['form'] = form
                    template = get_template("alu_requisitosmaestria/add_pagoexamen.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, "nombre": "SUBIR EVIDENCIA DE PAGO "})
                except Exception as ex:
                    pass

            if action == 'listadorequisitos':
                try:
                    data['title'] = u'Requisitos de programas de Maestría'
                    data['aspirante'] = aspirante
                    tienepagoexamen = False
                    ventanaactiva = 1
                    bloqueasubidapago = 1
                    data['inscripcioncohorte'] = inscripcioncohorte = InscripcionCohorte.objects.get(pk=int(encrypt(request.GET['idinscripcioncohorte'])))
                    if inscripcioncohorte.cohortes.tienecostoexamen:
                        if inscripcioncohorte.evidenciapagoexamen_set.filter(status=True):
                            tienepagoexamen = True
                            data['pagoexamen'] = evidpagoexamen = inscripcioncohorte.evidenciapagoexamen_set.filter(status=True)[0]
                            if evidpagoexamen.estadorevision == 2:
                                bloqueasubidapago = 2
                    data['bloqueasubidapago'] = bloqueasubidapago
                    data['tienepagoexamen'] = tienepagoexamen
                    permisorequisito = False
                    if inscripcioncohorte.cohortes.fechafinrequisito >= hoy:
                        permisorequisito = True
                    data['permisorequisito'] = permisorequisito
                    # if InscripcionCohorte.objects.filter(grupo__isnull=True):
                    if InscripcionCohorte.objects.filter(pk=int(encrypt(request.GET['idinscripcioncohorte'])), grupo__isnull=True):
                        data['requisitos'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, status=True).order_by("id")
                    else:
                        gruporequisitos = RequisitosGrupoCohorte.objects.values_list('requisito_id', flat=True).filter(grupo=inscripcioncohorte.grupo, status=True)
                        data['requisitos'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, requisito_id__in=gruporequisitos, status=True).order_by("id")
                    if inscripcioncohorte.integrantegrupoexamenmsc_set.filter(grupoexamen__estado_emailentrevista=2, grupoexamen__visible=True, status=True).exists():
                        data['integranteexamen'] = inscripcioncohorte.integrantegrupoexamenmsc_set.get(grupoexamen__estado_emailentrevista=2, grupoexamen__visible=True, status=True)
                        ventanaactiva = 2
                    if inscripcioncohorte.integrantegrupoentrevitamsc_set.filter(grupoentrevista__estado_emailentrevista=2, grupoentrevista__visible=True, status=True).exists():
                        data['integranteentrevista'] = inscripcioncohorte.integrantegrupoentrevitamsc_set.get(grupoentrevista__estado_emailentrevista=2, grupoentrevista__visible=True, status=True)
                        ventanaactiva = 3
                    if inscripcioncohorte.integrantegrupoentrevitamsc_set.filter(estado_emailadmitido=2, cohorteadmitidasinproceso__isnull=True, status=True).exists():
                        data['aspiranteadmitido'] = inscripcioncohorte.integrantegrupoentrevitamsc_set.get(estado_emailadmitido=2, cohorteadmitidasinproceso__isnull=True, status=True)
                        ventanaactiva = 4
                        data['otracohorte'] = 0
                    if inscripcioncohorte.integrantegrupoentrevitamsc_set.filter(cohorteadmitidasinproceso__isnull=False, status=True).exists():
                        data['aspiranteadmitido'] = inscripcioncohorte.integrantegrupoentrevitamsc_set.get(cohorteadmitidasinproceso__isnull=False, status=True)
                        ventanaactiva = 4
                        data['otracohorte'] = 1
                    data['ventanaactiva'] = ventanaactiva

                    return render(request, "alu_requisitosmaestria/requisitosmaestria.html", data)
                except Exception as ex:
                    pass

            elif action == 'cargarrequisitoconvenio':
                try:
                    from posgrado.forms import RequisitoConvenioAspiranteForm
                    data['action'] = 'cargarrequisitoconvenio'
                    form2 = RequisitoConvenioAspiranteForm()
                    data['filtro'] = filtro = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    data['fpago'] = request.GET['fp']
                    data['form2'] = form2
                    template = get_template("alu_requisitosmaestria/addcontratopago.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'listadorequisitosinscripcion':
                try:
                    from posgrado.models import EvidenciaRequisitoConvenio
                    data['title'] = u'Admisión en programas de maestría'
                    data['aspirante'] = aspirante
                    vt = False
                    vexpe = False
                    tienepagoexamen = False
                    ventanaactiva = 1
                    bloqueasubidapago = 1
                    tienerequisitos = False
                    integranteexamen = integranteentrevista = garante = contrato = None
                    data['uno'] = 1
                    data['dos'] = 2
                    data['tres'] = 3
                    data['cuatro'] = 4
                    data['cinco'] = 5
                    data['seis'] = 6
                    data['siete'] = 7
                    data['ocho'] = 8
                    data['nueve'] = 9

                    data['inscripcioncohorte'] = inscripcioncohorte = InscripcionCohorte.objects.get(pk=int(encrypt(request.GET['idinscripcioncohorte'])))
                    data['idpersona'] = persona.id
                    data['titulaciones'] = Titulacion.objects.filter(status=True, persona=inscripcioncohorte.inscripcionaspirante.persona, titulo__nivel__id__in=[3,4], educacionsuperior=True)

                    data['canales'] = CanalInformacionMaestria.objects.filter(status=True)
                    if str(inscripcioncohorte.id) not in variable_valor('INSCRIPCIONES_NOVALIDA_PERFILINGRESO'):
                        if inscripcioncohorte.cohortes.maestriaadmision.carrera.programapac_set.last() and inscripcioncohorte.cohortes.maestriaadmision.carrera.programapac_set.last().funcionsustantivadocenciapac_set.last() and inscripcioncohorte.cohortes.maestriaadmision.carrera.programapac_set.last().funcionsustantivadocenciapac_set.last().detalleperfilingreso_set.last():
                            data['perfilingreso'] = perfilingreso = inscripcioncohorte.cohortes.maestriaadmision.carrera.programapac_set.last().funcionsustantivadocenciapac_set.last().detalleperfilingreso_set.last()
                            data['idperfilingreso'] = perfilingreso.id
                            if perfilingreso.experiencia > 0: #si el perfil cuenta con experiencia
                                data['validarexperiencia'] = vexpe = True
                                data['experiencia'] = perfilingreso.cantidadexperiencia
                            else:
                                data['validarexperiencia'] = vexpe = False

                            campotitulos = CamposTitulosPostulacion.objects.filter(status=True, titulo__in=perfilingreso.titulo.all()).distinct()
                            data['campotitulos'] = campotitulos

                            if campotitulos:
                                data['validartitulo'] = vt = True
                            else:
                                data['validartitulo'] = vt = False

                    inscripciondescuento = None
                    tienerequisitosbecas = False
                    tienerequisitoshomologacion = False
                    registrocomprobantepago = None
                    registroanticipo = None
                    if inscripcioncohorte.tipobeca:
                        if not DescuentoPosgradoMatricula.objects.filter(inscripcioncohorte=inscripcioncohorte, status=True):
                            desposgrado = DescuentoPosgradoMatricula(detalleconfiguraciondescuentoposgrado=inscripcioncohorte.tipobeca,
                                                                     inscripcioncohorte=inscripcioncohorte)
                            desposgrado.save(request)

                            recorridobeca = DescuentoPosgradoMatriculaRecorrido(
                                descuentoposgradomatricula=desposgrado,
                                fecha=datetime.now().date(),
                                persona=persona,
                                observacion='SOLICITUD REGISTRADA',
                                estado=1
                            )
                            recorridobeca.save(request)
                            log(u'Agregó solicitud de beca de posgrado: %s' % desposgrado, request, "add")
                        else:
                            desposgrado = DescuentoPosgradoMatricula.objects.filter(detalleconfiguraciondescuentoposgrado=inscripcioncohorte.tipobeca, inscripcioncohorte=inscripcioncohorte, status=True)[0]
                        inscripciondescuento = desposgrado
                        if inscripciondescuento.evidenciasdescuentoposgradomatricula_set.filter(status=True).exists():
                            tienerequisitosbecas = True
                    data['tienerequisitosbecas'] = tienerequisitosbecas
                    data['inscripciondescuento'] = inscripciondescuento
                    if inscripcioncohorte.evidenciarequisitosaspirante_set.filter(status=True).exists():
                        tienerequisitos = True
                    data['tienerequisitos'] = tienerequisitos

                    # if inscripcioncohorte.evidenciarequisitosaspirante_set.filter(status=True, requisitos__requisito__claserequisito__clasificacion__id=4).exists():
                    #     tienerequisitoshomologacion = True
                    # data['tienerequisitoshomologacion'] = tienerequisitoshomologacion

                    tienerequisitosfi = False
                    if inscripcioncohorte.evidenciarequisitosaspirante_set.filter(status=True, requisitos__requisito__claserequisito__clasificacion__id=3).exists():
                        tienerequisitosfi = True
                    data['tienerequisitosfi'] = tienerequisitosfi

                    if inscripcioncohorte.cohortes.tienecostoexamen:
                        if inscripcioncohorte.evidenciapagoexamen_set.filter(status=True):
                            tienepagoexamen = True
                            data['pagoexamen'] = evidpagoexamen = inscripcioncohorte.evidenciapagoexamen_set.filter(status=True)[0]
                            if evidpagoexamen.estadorevision == 2:
                                bloqueasubidapago = 2
                    data['bloqueasubidapago'] = bloqueasubidapago
                    data['tienepagoexamen'] = tienepagoexamen
                    permisorequisito = False
                    if hoy >= inscripcioncohorte.cohortes.fechainiciorequisito and hoy <= inscripcioncohorte.cohortes.fechafinrequisito:
                        permisorequisito = True
                    data['permisorequisito'] = permisorequisito
                    # if InscripcionCohorte.objects.filter(grupo__isnull=True):
                    if InscripcionCohorte.objects.filter(pk=int(encrypt(request.GET['idinscripcioncohorte'])), grupo__isnull=True):
                        requisitosexcluir = ClaseRequisito.objects.values_list('requisito__id').filter(clasificacion=3, status=True)
                        data['requisitos'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, status=True).exclude(requisito__in=requisitosexcluir).order_by("id")
                    else:
                        gruporequisitos = RequisitosGrupoCohorte.objects.values_list('requisito_id', flat=True).filter(grupo=inscripcioncohorte.grupo, status=True)
                        data['requisitos'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, requisito_id__in=gruporequisitos, status=True).order_by("id")
                    if inscripcioncohorte.integrantegrupoexamenmsc_set.filter(grupoexamen__estado_emailentrevista=2, status=True, inscripcion__status=True).exists():
                        data['integranteexamen'] = integranteexamen = inscripcioncohorte.integrantegrupoexamenmsc_set.get(grupoexamen__estado_emailentrevista=2, status=True)
                        # ventanaactiva = 2
                    if inscripcioncohorte.integrantegrupoentrevitamsc_set.filter(grupoentrevista__estado_emailentrevista=2, status=True, inscripcion__status=True).exists():
                        data['integranteentrevista'] = integranteentrevista = inscripcioncohorte.integrantegrupoentrevitamsc_set.get(grupoentrevista__estado_emailentrevista=2, status=True)
                        # ventanaactiva = 3

                    #SI CUMPLE CON LA CONDICIÓN SELECIONA LA PESTAÑA A VIZUALIZAR financiamiento formapagopac_id == 2
                    permisorequisitocomercia = False
                    data['fechafincomercializacion'] = fechafincomercializacion = inscripcioncohorte.cohortes.fechafininsp + timedelta(days=30)
                    if fechafincomercializacion >= hoy:
                        permisorequisitocomercia = True
                    data['permisorequisitocomercia'] = permisorequisitocomercia

                    if 'ventanacomercial' in request.GET:
                        a=0
                        # ventanaactiva = 3.2
                    if inscripcioncohorte.formapagopac:
                        if inscripcioncohorte.formapagopac_id == 2:
                            if inscripcioncohorte.subirrequisitogarante:
                                # requisitosexcluir = ClaseRequisito.objects.values_list('requisito__id').filter(clasificacion=1, status=True)
                                data['requisitoscomercializacion'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, status=True, requisito__claserequisito__clasificacion__id=3).exclude(requisito__id__in=[56, 57, 59]).order_by("requisito__tipopersona__id")
                            else:
                                # requisitosexcluir = ClaseRequisito.objects.values_list('requisito__id').filter(clasificacion=1, status=True)
                                data['requisitoscomercializacion'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, status=True, requisito__tipopersona__id=1, requisito__claserequisito__clasificacion__id=3).order_by("id")


                    if 'ventanacontrato' in request.GET and request.GET['ventanacontrato']:
                        a=0
                        # ventanaactiva = float(request.GET['ventanacontrato'])
                    formapago = 1
                    if inscripcioncohorte.formapagopac:
                        formapago = inscripcioncohorte.formapagopac.id
                    if TipoFormaPagoPac.objects.filter(pk=formapago).exists():
                        data['fpago'] = fpago = TipoFormaPagoPac.objects.filter(pk=formapago).last()
                        data['contrato'] = contrato = Contrato.objects.filter(status=True, inscripcion=inscripcioncohorte, inscripcion__status=True).last()
                    if formapago == 2:
                        data['garante'] = garante = inscripcioncohorte.garantepagomaestria_set.filter(status=True).last()
                    if inscripcioncohorte.integrantegrupoentrevitamsc_set.filter(estado_emailadmitido=2, cohorteadmitidasinproceso__isnull=True, status=True).exists():
                        data['aspiranteadmitido'] = inscripcioncohorte.integrantegrupoentrevitamsc_set.get(estado_emailadmitido=2, cohorteadmitidasinproceso__isnull=True, status=True)
                        # ventanaactiva = 4
                        data['otracohorte'] = 0
                    if inscripcioncohorte.integrantegrupoentrevitamsc_set.filter(cohorteadmitidasinproceso__isnull=False, status=True, inscripcion__status=True).exists():
                        data['aspiranteadmitido'] = inscripcioncohorte.integrantegrupoentrevitamsc_set.get(cohorteadmitidasinproceso__isnull=False, status=True)
                        # ventanaactiva = 4
                        data['otracohorte'] = 1
                    if inscripcioncohorte.evidenciarequisitoconvenio_set.filter(status=True, convenio = inscripcioncohorte.convenio).exists():
                        data['requisitoconvenio'] = inscripcioncohorte.evidenciarequisitoconvenio_set.get(status=True, convenio = inscripcioncohorte.convenio)

                    # if inscripcioncohorte.inscripcionaspirante.persona.usuario.id == 35288:
                    #     malla = inscripcioncohorte.cohortes.maestriaadmision.carrera.malla()
                    #
                    #     data['asignaturas'] = asignaturas = AsignaturaMalla.objects.filter(status=True, malla=malla).order_by('asignatura__nombre')
                    #     data['totalhoras'] = AsignaturaMalla.objects.filter(status=True, malla=malla).order_by('asignatura__nombre').aggregate(horas=Sum('horas'))['horas']
                    #     data['totalcreditos'] = AsignaturaMalla.objects.filter(status=True, malla=malla).order_by('asignatura__nombre').aggregate(creditos=Sum('creditos'))['creditos']
                    #     data['requisitoshomologacion'] = RequisitosMaestria.objects.filter(maestria=inscripcioncohorte.cohortes.maestriaadmision, status=True, requisito__claserequisito__clasificacion__id=4).order_by("id")
                    #     if inscripcioncohorte.cohortes.valorprogramacertificado:
                    #         data['costomodulo'] = inscripcioncohorte.cohortes.valorprogramacertificado / asignaturas.count()
                    #     else:
                    #         if PeriodoCarreraCosto.objects.filter(Status=True, carrera=inscripcioncohorte.cohortes.maestriaadmision.carrera).exists():
                    #             valor = PeriodoCarreraCosto.objects.filter(Status=True, carrera=inscripcioncohorte.cohortes.maestriaadmision.carrera).first()
                    #             data['costomodulo'] = valor / asignaturas.count()
                    #         else:
                    #             data['costomodulo'] = 0
                    #     data['servicio'] = eServicio = Servicio.objects.get(status=True, pk=15)
                    #     ePerfilUsuario = PerfilUsuario.objects.filter(status=True,
                    #                                                   persona=inscripcioncohorte.inscripcionaspirante.persona,
                    #                                                   inscripcionaspirante__isnull=False).first()
                    #
                    #     eProducto = ProductoSecretaria.objects.get(servicio__id=eServicio.pk)
                    #     eContentTypeProducto = ContentType.objects.get_for_model(eProducto)
                    #
                    #     eSolicitudes = Solicitud.objects.filter(Q(en_proceso=True) | Q(estado__in=[23]), status=True,
                    #                                             perfil_id=ePerfilUsuario.pk, servicio_id=eServicio.pk,
                    #                                             origen_content_type_id=eContentTypeProducto.pk,
                    #                                             inscripcioncohorte=inscripcioncohorte,
                    #                                             origen_object_id=eProducto.id).exclude(servicio__proceso=8)
                    #     if eSolicitudes.values("id").exists():
                    #         eSolicitud = Solicitud.objects.filter(Q(en_proceso=True) | Q(estado__in=[23]), status=True,
                    #                                               perfil_id=ePerfilUsuario.pk, servicio_id=eServicio.pk,
                    #                                               origen_content_type_id=eContentTypeProducto.pk,
                    #                                               inscripcioncohorte=inscripcioncohorte,
                    #                                               origen_object_id=eProducto.id).exclude(servicio__proceso=8).first()
                    #         data['eSolicitud'] = eSolicitud

                    if vexpe or vt:
                        ventanaactiva = 1
                        data['fase1'] = True
                        if inscripcioncohorte.cohortes.tipo == 1:
                            if inscripcioncohorte.tiulacionaspirante:
                                ventanaactiva = 2
                                data['fase2'] = True
                                if inscripcioncohorte.estado_aprobador == 2:
                                    ventanaactiva = 4
                                    data['fase4'] = True
                                    if integranteexamen and integranteexamen.estado == 2:
                                        ventanaactiva = 5
                                        data['fase5'] = True
                                        if integranteentrevista and integranteentrevista.estado == 2:
                                            ventanaactiva = 8
                                            data['fase8'] = True
                                            if inscripcioncohorte.formapagopac.id == 2:
                                                if inscripcioncohorte.aceptado:
                                                    ventanaactiva = 3
                                                    data['fase3'] = True
                                                    if inscripcioncohorte.subirrequisitogarante:
                                                        if garante and inscripcioncohorte.estadoformapago == 2 and inscripcioncohorte.Configfinanciamientocohorte:
                                                            ventanaactiva = 6
                                                            data['fase6'] = True
                                                            if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and contrato.ultima_evidenciapagare() and contrato.ultima_evidenciapagare().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                                                ventanaactiva = 9
                                                                data['fase9'] = True
                                                            if inscripcioncohorte.completo_datos_matrices() == '0':
                                                                ventanaactiva = 7
                                                                data['fase7'] = True
                                                    else:
                                                        if inscripcioncohorte.estadoformapago == 2 and inscripcioncohorte.Configfinanciamientocohorte:
                                                            ventanaactiva = 6
                                                            data['fase6'] = True
                                                            if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and contrato.ultima_evidenciapagare() and contrato.ultima_evidenciapagare().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                                                ventanaactiva = 9
                                                                data['fase9'] = True
                                                            if inscripcioncohorte.completo_datos_matrices() == '0':
                                                                ventanaactiva = 7
                                                                data['fase7'] = True
                                            else:
                                                if inscripcioncohorte.aceptado:
                                                    ventanaactiva = 6
                                                    data['fase6'] = True
                                                    if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                                        ventanaactiva = 7
                                                        data['fase7'] = True

                        elif inscripcioncohorte.cohortes.tipo == 2:
                            if inscripcioncohorte.tiulacionaspirante:
                                ventanaactiva = 2
                                data['fase2'] = True
                                if inscripcioncohorte.estado_aprobador == 2:
                                    ventanaactiva = 4
                                    data['fase4'] = True
                                    if integranteexamen and integranteexamen.estado == 2:
                                        ventanaactiva = 8
                                        data['fase8'] = True
                                        if inscripcioncohorte.formapagopac.id == 2:
                                            if inscripcioncohorte.aceptado:
                                                ventanaactiva = 3
                                                data['fase3'] = True
                                                if inscripcioncohorte.subirrequisitogarante:
                                                    if garante and inscripcioncohorte.estadoformapago == 2 and inscripcioncohorte.Configfinanciamientocohorte:
                                                        ventanaactiva = 6
                                                        data['fase6'] = True
                                                        if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and contrato.ultima_evidenciapagare() and contrato.ultima_evidenciapagare().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                                            ventanaactiva = 7
                                                            data['fase7'] = True
                                                else:
                                                    if inscripcioncohorte.estadoformapago == 2 and inscripcioncohorte.Configfinanciamientocohorte:
                                                        ventanaactiva = 6
                                                        data['fase6'] = True
                                                        if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and contrato.ultima_evidenciapagare() and contrato.ultima_evidenciapagare().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                                            ventanaactiva = 9
                                                            data['fase9'] = True
                                                        if inscripcioncohorte.completo_datos_matrices() == '0':
                                                            ventanaactiva = 7
                                                            data['fase7'] = True
                                        else:
                                            if inscripcioncohorte.aceptado:
                                                ventanaactiva = 6
                                                data['fase6'] = True
                                                if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                                    ventanaactiva = 9
                                                    data['fase9'] = True
                                                if inscripcioncohorte.completo_datos_matrices() == '0':
                                                    ventanaactiva = 7
                                                    data['fase7'] = True
                        else:
                            if inscripcioncohorte.tiulacionaspirante:
                                ventanaactiva = 2
                                data['fase2'] = True
                                if inscripcioncohorte.estado_aprobador == 2:
                                    ventanaactiva = 8
                                    data['fase8'] = True
                                    if inscripcioncohorte.formapagopac.id == 2:
                                        if inscripcioncohorte.aceptado:
                                            ventanaactiva = 3
                                            data['fase3'] = True
                                            if inscripcioncohorte.subirrequisitogarante:
                                                if garante and inscripcioncohorte.estadoformapago == 2 and inscripcioncohorte.Configfinanciamientocohorte:
                                                    ventanaactiva = 6
                                                    data['fase6'] = True
                                                    if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and contrato.ultima_evidenciapagare() and contrato.ultima_evidenciapagare().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                                        ventanaactiva = 9
                                                        data['fase9'] = True
                                                    if inscripcioncohorte.completo_datos_matrices() == '0':
                                                        ventanaactiva = 7
                                                        data['fase7'] = True
                                            else:
                                                if inscripcioncohorte.estadoformapago == 2 and inscripcioncohorte.Configfinanciamientocohorte:
                                                    ventanaactiva = 6
                                                    data['fase6'] = True
                                                    if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and contrato.ultima_evidenciapagare() and contrato.ultima_evidenciapagare().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                                        ventanaactiva = 9
                                                        data['fase9'] = True
                                                    if inscripcioncohorte.completo_datos_matrices() == '0':
                                                        ventanaactiva = 7
                                                        data['fase7'] = True
                                    else:
                                        if inscripcioncohorte.aceptado:
                                            ventanaactiva = 6
                                            data['fase6'] = True
                                            if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                                ventanaactiva = 9
                                                data['fase9'] = True
                                            if inscripcioncohorte.completo_datos_matrices() == '0':
                                                ventanaactiva = 7
                                                data['fase7'] = True
                    else:
                        ventanaactiva = 2
                        data['fase2'] = True
                        if inscripcioncohorte.estado_aprobador == 2:
                            ventanaactiva = 8
                            data['fase8'] = True
                            if inscripcioncohorte.formapagopac.id == 2:
                                if inscripcioncohorte.aceptado:
                                    ventanaactiva = 3
                                    data['fase3'] = True
                                    if inscripcioncohorte.subirrequisitogarante:
                                        if garante and inscripcioncohorte.estadoformapago == 2 and inscripcioncohorte.Configfinanciamientocohorte:
                                            ventanaactiva = 6
                                            data['fase6'] = True
                                            if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and contrato.ultima_evidenciapagare() and contrato.ultima_evidenciapagare().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                                ventanaactiva = 7
                                                data['fase7'] = True
                                    else:
                                        if inscripcioncohorte.estadoformapago == 2 and inscripcioncohorte.Configfinanciamientocohorte:
                                            ventanaactiva = 6
                                            data['fase6'] = True
                                            if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and contrato.ultima_evidenciapagare() and contrato.ultima_evidenciapagare().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                                ventanaactiva = 9
                                                data['fase9'] = True
                                            if inscripcioncohorte.completo_datos_matrices() == '0':
                                                ventanaactiva = 7
                                                data['fase7'] = True
                            else:
                                if inscripcioncohorte.aceptado:
                                    ventanaactiva = 6
                                    data['fase6'] = True
                                    if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                        ventanaactiva = 9
                                        data['fase9'] = True
                                    if inscripcioncohorte.completo_datos_matrices() == '0':
                                        ventanaactiva = 7
                                        data['fase7'] = True
                    next = 0
                    if 'next' in request.GET:
                        next = request.GET['next']
                        if next:
                            ventanaactiva = int(encrypt(next))
                    data['ventanaactiva'] = ventanaactiva
                    return render(request, "alu_requisitosmaestria/listadorequisitosinscripcion.html", data)
                except Exception as ex:
                    pass

            if action == 'addgarantepagomaestria':
                try:
                    data['action'] = 'addgarantepagomaestria'
                    data['id'] = request.GET['idins']
                    insc = InscripcionCohorte.objects.get(pk=request.GET['idins'])
                    form = GarantePagoMaestriaForm()
                    data['form'] = form
                    template = get_template("alu_requisitosmaestria/addgarantepagomaestria.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'verfacturas':
                try:
                    id= int(request.GET['id'])
                    data['filtro'] = filtro = Rubro.objects.get(pk=int(id))
                    data['listado_facturas'] = filtro.pago_set.filter(status=True).order_by('-pk')
                    template=get_template('alu_requisitosmaestria/verfacturas.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editgarantepagomaestria':
                try:
                    data['action'] = 'editgarantepagomaestria'
                    data['id'] = request.GET['idins']
                    data['idg'] = request.GET['idg']
                    garante = GarantePagoMaestria.objects.get(pk=request.GET['idg'])
                    initial = model_to_dict(garante)
                    form = GarantePagoMaestriaForm(initial=initial)
                    form.editar()
                    data['form'] = form
                    template = get_template("alu_requisitosmaestria/addgarantepagomaestria.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content, "nombre": "EDITAR GARANTE"})
                except Exception as ex:
                    pass

            if action == 'cargarcontratopago':
                try:
                    # data['title'] = u'Contrato de pago'
                    form2 = ContratoPagoMaestriaForm()
                    data['filtro'] = filtro = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    data['fpago'] = request.GET['fp']
                    data['form2'] = form2
                    template = get_template("alu_requisitosmaestria/addcontratopago.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'aceptartablaamortizacionpagaremae':
                try:
                    data['id'] = request.GET['id']
                    data['inscripcioncohorte'] = insc = InscripcionCohorte.objects.get(pk=request.GET['id'])
                    data['contrato'] = contrato = insc.contrato_set.last()
                    configuracion = None
                    if insc.Configfinanciamientocohorte:
                        data['configuracion'] = configuracion = ConfigFinanciamientoCohorte.objects.filter(pk=insc.Configfinanciamientocohorte.id).last()
                    if insc.contrato_set.values('id').last() and insc.contrato_set.last().tablaamortizacion_set.values('id').filter(status=True) and insc.contrato_set.last().tablaamortizacionajustada:
                        tablaamortizacion = []
                        contrato = contrato
                        montototal = contrato.tablaamortizacion_set.values_list('valor').filter(status=True)
                        total = Decimal(0)
                        valorpendiente = Decimal(0)
                        for valor in montototal:
                            total = total + valor[0]
                        data['total'] = total
                        tablaamortizacionajustada = contrato.tablaamortizacion_set.values_list('cuota', 'fecha', 'fechavence', 'valor').filter(status=True)
                        for tabla in tablaamortizacionajustada:
                            if tabla[0] == 0:
                                valorarancel = total - tabla[3]
                                valorpendiente = valorarancel
                                tablaamortizacion += [('', '', '', tabla[3], valorarancel)]
                            else:
                                valorpendiente = valorpendiente - tabla[3]
                                tablaamortizacion += [(tabla[0], tabla[1], tabla[2], tabla[3], valorpendiente)]

                        data['tablaamortizacion'] = tablaamortizacion
                    else:
                        if configuracion:
                            data['tablaamortizacion'] = tablaamortizacion = configuracion.tablaamortizacioncohortemaestria(insc,hoy)
                            total=0
                            for valor in tablaamortizacion:
                                total = total + valor[3]
                            data['total'] = total
                    template = get_template("alu_requisitosmaestria/modaltablaamortizacionpagare.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'cargarpagareaspirantemaestria':
                try:
                    form2 = ContratoPagoMaestriaForm()
                    data['filtro'] = filtro = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    data['fpago'] = request.GET['fp']
                    data['form2'] = form2
                    template = get_template("alu_requisitosmaestria/addcontratopago.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addtitulacionpos':
                try:
                    data['title'] = u'Adicionar titulación'
                    data['carrera'] = carrera = Carrera.objects.get(pk=request.GET['idcarrera'])
                    form = TitulacionPersonaAdmisionPosgradoForm()
                    form.adicionar()
                    data['form2'] = form
                    template = get_template("interesadosmaestria/addtitulacionpos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'listcampoespecifico':
                try:
                    campoamplio = request.GET.get('campoamplio')
                    listcampoamplio = campoamplio
                    if len(campoamplio) > 1:
                        listcampoamplio = campoamplio.split(',')
                    querybase = SubAreaConocimientoTitulacion.objects.filter(status=True, areaconocimiento__in=listcampoamplio).order_by('codigo')
                    if 'q' in request.GET:
                        q = request.GET['q'].upper().strip()
                        if q != 'UNDEFINED':
                            querybase = querybase.filter((Q(nombre__icontains=q) | Q(codigo__icontains=q))).distinct()[:30]
                    data = {"result": "ok", "results": [{"id": x.id, "idca": x.areaconocimiento.id, "name": "{} - {}".format(x.codigo, x.nombre)} for x in querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'listcampodetallado':
                try:
                    campoespecifico = request.GET.get('campoespecifico')
                    listcampoespecifico = campoespecifico
                    if len(campoespecifico) > 1:
                        listcampoespecifico = campoespecifico.split(',')
                    querybase = SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, areaconocimiento__in=listcampoespecifico).order_by('codigo')
                    if 'q' in request.GET:
                        q = request.GET['q'].upper().strip()
                        if q != 'UNDEFINED':
                            querybase = querybase.filter((Q(nombre__icontains=q) | Q(codigo__icontains=q))).distinct()[:30]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {}".format(x.codigo, x.nombre)} for x in querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'listagruposrequisitos':
                try:
                    data['title'] = u'Requisitos y perfil de ingreso'
                    data['cohorte'] = cohorte = CohorteMaestria.objects.get(status=True, pk=int(encrypt(request.GET['id'])))
                    data['grupos'] = cohorte.gruporequisitocohorte_set.filter(status=True).order_by('orden')
                    return render(request, "alu_requisitosmaestria/listagrupos.html", data)
                except Exception as ex:
                    pass

            if action == 'fichasocioeconomica':
                try:
                    if int(encrypt(request.GET['idrequibeca'])) == 18:
                        nompersona = Persona.objects.get(pk=persona.id)
                        nompersona.mi_ficha()
                        if FichaSocioeconomicaINEC.objects.values('id').filter(persona=nompersona).exists():
                            ficha = FichaSocioeconomicaINEC.objects.get(persona=nompersona)
                            ficha.confirmar = False
                            ficha.save()
                            return HttpResponseRedirect('/alu_socioecon')
                except Exception as ex:
                    pass

            if action == 'registropago':
                try:
                    data['title'] = u'Registro de pago'
                    data['inscripcioncohorte'] = inscripcioncohorte = InscripcionCohorte.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = RegistroPagoForm(initial={'telefono': persona.telefono,
                                                     'email': persona.email})
                    data['form2'] = form
                    url = urlepunemi + "api?a=apicuentas&clavesecreta=unemiepunemi2022"
                    r = requests.get(url)
                    listadocuentas = []
                    for lista in r.json():
                        listadocuentas.append([lista['id'], lista['nombre'], lista['numerocuenta'], lista['tipo']])
                    data['listadocuentas'] = listadocuentas
                    template = get_template("alu_requisitosmaestria/registropago.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'registroanticipo':
                try:
                    data['title'] = u'Comprobante'
                    data['inscripcioncohorte'] = inscripcioncohorte = InscripcionCohorte.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = RegistroPagoForm(initial={'telefono': inscripcioncohorte.inscripcionaspirante.persona.telefono,
                                                     'email': inscripcioncohorte.inscripcionaspirante.persona.email})
                    data['form2'] = form
                    url = urlepunemi + "api?a=apicuentas&clavesecreta=unemiepunemi2022"
                    r = requests.get(url)
                    listadocuentas = []
                    for lista in r.json():
                        listadocuentas.append([lista['id'], lista['nombre'],lista['numerocuenta'],lista['tipo']])
                    data['listadocuentas'] = listadocuentas
                    template = get_template("alu_requisitosmaestria/registroanticipo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'validarperfil':
                try:
                    experi = None
                    data['title'] = u'Asignar horario de retiro'
                    data['action'] = request.GET['action']
                    data['id'] = id = int(request.GET['id'])
                    data['uno'] = 1
                    data['insc'] = InscripcionCohorte.objects.get(status=True, pk=int(request.GET['insc']))
                    data['idperfilingreso'] = int(request.GET['idperfilingreso'])
                    # data['idperfilingreso'] = DetallePerfilIngreso.objects.get(status=True, pk=int(request.GET['idperfilingreso']))
                    if request.GET['experiencia'] == '':
                        experi = float(0)
                    else:
                        experi = float(request.GET['experiencia'])
                    data['experiencia'] = experi
                    data['validarexperiencia'] = expe = request.GET['vexpe']
                    data['validartitulo'] = titu = request.GET['vtitulo']

                    titulacion = Titulacion.objects.get(status=True, pk=id)
                    form = ValidarPerfilAdmisionForm(initial={'titulo': titulacion.titulo,
                                                              'postulante': titulacion.persona.nombre_completo_inverso()})

                    if expe == 'False':
                        form.sin_cantidad()
                    if titu == 'False':
                        form.sin_titulo()

                    data['form'] = form
                    data['urlaction'] = '/alu_requisitosmaestria'
                    template = get_template("alu_requisitosmaestria/validarpefil.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'addarchivorequi':
                try:
                    form2 = EvidenciaRequisitoAdmisionForm()
                    data['filtro'] = filtro = RequisitosMaestria.objects.get(pk=int(request.GET['id']))
                    data['idrequisito'] = request.GET['id']
                    data['idins'] = request.GET['idins']
                    if request.GET['idm']:
                        data['action'] = 'addarchivorequi2'
                    else:
                        data['action'] = 'addarchivorequi'
                    data['form2'] = form2
                    template = get_template("alu_requisitosmaestria/addarchivorequi.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'buscartitulos':
                try:
                    # id = request.GET['id']
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    querybase = Titulo.objects.filter(nivel_id__in=[3, 4, 21, 22, 23, 30], status=True)
                    # if len(s) == 1:
                    per = querybase.filter((Q(nombre__icontains=q) | Q(abreviatura__icontains=q)), Q(status=True)).distinct()[:30]
                    # elif len(s) == 2:
                    #     per = querybase.filter((Q(nombre__contains=s[0]) & Q(nombre__contains=s[1])) | (Q(abreviatura__icontains=s[0]) & Q(abreviatura__icontains=s[1]))).filter(status=True).distinct()[:30]
                    # else:
                    #     per = querybase.filter((Q(nombre__contains=s[0]) & Q(nombre__contains=s[1])) | (Q(abreviatura__contains=s[0]) & Q(abreviatura__contains=s[1]))).filter(status=True).distinct()[:30]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {}".format(x.abreviatura, x.nombre)} for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'adddatospersonales':
                try:
                    data['title'] = u'Actualizar datos personales'
                    ins = InscripcionCohorte.objects.get(pk=int(request.GET['idp']))
                    form = DatosPersonalesMaestranteForm(initial={'paisori': ins.inscripcionaspirante.persona.paisnacimiento,
                                                                  'provinciaori': ins.inscripcionaspirante.persona.provincianacimiento,
                                                                  'cantonori': ins.inscripcionaspirante.persona.cantonnacimiento,
                                                                  'paisresi': ins.inscripcionaspirante.persona.pais if ins.inscripcionaspirante.persona.pais else '',
                                                                  'provinciaresi': ins.inscripcionaspirante.persona.provincia if ins.inscripcionaspirante.persona.provincia else '',
                                                                  'cantonresi': ins.inscripcionaspirante.persona.canton if ins.inscripcionaspirante.persona.canton else '',
                                                                  'tienediscapacidad': ins.inscripcionaspirante.persona.mi_perfil().tienediscapacidad if ins.inscripcionaspirante.persona.mi_perfil().tienediscapacidad else False,
                                                                  'tipodiscapacidad': ins.inscripcionaspirante.persona.mi_perfil().tipodiscapacidad if ins.inscripcionaspirante.persona.mi_perfil().tipodiscapacidad else '',
                                                                  'porcientodiscapacidad': ins.inscripcionaspirante.persona.mi_perfil().porcientodiscapacidad if ins.inscripcionaspirante.persona.mi_perfil().porcientodiscapacidad else 0,
                                                                  'carnetdiscapacidad': ins.inscripcionaspirante.persona.mi_perfil().carnetdiscapacidad if ins.inscripcionaspirante.persona.mi_perfil().carnetdiscapacidad else '',
                                                                  'archivo': ins.inscripcionaspirante.persona.mi_perfil().archivo if ins.inscripcionaspirante.persona.mi_perfil().archivo else '',
                                                                  'raza': ins.inscripcionaspirante.persona.mi_perfil().raza if ins.inscripcionaspirante.persona.mi_perfil().raza else '',
                                                                  'nacionalidadindigena': ins.inscripcionaspirante.persona.mi_perfil().nacionalidadindigena if ins.inscripcionaspirante.persona.mi_perfil().nacionalidadindigena else '',
                                                                  'lgtbi': ins.inscripcionaspirante.persona.lgtbi})
                    visible_fields = form.visible_fields()
                    total_fields = len(visible_fields)
                    lista = [(1, 'Ubicación demográfica', visible_fields[0:6]),
                             (2, 'Discapacidad', visible_fields[6:11]),
                             (3, 'Etnia/Raza', visible_fields[11:total_fields])
                             ]
                    data['form'] = lista
                    data['switchery'] = True
                    data['clavebi'] = 'foreign'
                    data['action'] = 'adddatospersonales'
                    data['idins'] = ins.id
                    template = get_template('alu_requisitosmaestria/formdatospersonales.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Postulaciones a programas de maestría'
            data['aspirante'] = aspirante = persona.inscripcionaspirante_set.filter(status=True)[0]
            data['aspirantepersona'] = persona
            data['inscripcionescohorte'] = InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, status=True)
            data['listadomaestriascohorte'] = CohorteMaestria.objects.filter(activo=True, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, status=True).exclude(inscripcioncohorte__cohortes__isnull=False, inscripcioncohorte__inscripcionaspirante=aspirante).order_by('id')

            if DescuentoPosgradoMatricula.objects.filter(status=True, inscripcioncohorte__inscripcionaspirante=aspirante, estado=6).exists():
                solicitud = DescuentoPosgradoMatricula.objects.get(status=True, inscripcioncohorte__inscripcionaspirante=aspirante, estado=6)
                ultimanovedad = solicitud.ultima_novedad()
                MAXIMO_DIAS = 5
                plazo = MAXIMO_DIAS - abs((datetime.now().date() - ultimanovedad.fecha).days)

                if plazo > 0:
                    data['mostrarmsgbeca'] = True
                    data['plazo'] = plazo

            return render(request, "alu_requisitosmaestria/inscripcionescohorte.html", data)
