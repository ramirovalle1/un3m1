import ast
import io
import json
import random
import sys
import openpyxl
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
import xlwt
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import Context
from django.template.loader import get_template
from xlwt import *
from django.shortcuts import render, redirect

from core.firmar_documentos import obtener_posicion_x_y_saltolinea
from core.firmar_documentos_ec import JavaFirmaEc
from decorators import secure_module
from postulaciondip.forms import RequisitosPagoPosgradoForm
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.templatetags.sga_extras import encrypt
from sga.funciones import MiPaginador, log, generar_nombre, remover_caracteres_especiales_unicode, notificacion, \
    remover_caracteres_tildes_unicode, puede_realizar_accion_afirmativo
from sagest.models import BitacoraActividadDiaria
from .models import *
from .forms import *
from django.db.models import Sum, Q, F, FloatField,Case, When, Value, IntegerField,BooleanField
from django.db.models.functions import Coalesce

def permisos_ver_opciones_view(persona):
    filtro = Q(status=True)
    gruporevision = ContratoDip.objects.values_list('persona_id', flat=True).filter(status=True, validadorgp=persona)
    if not persona.usuario.is_superuser:
        filtro = filtro & Q(contrato__persona__id__in=gruporevision) & Q(Q(estado=3) | Q(estado=7) | Q(estado=8))
    existen_solicitudes_para_grupo_revisor = SolicitudPago.objects.filter(filtro).order_by('-id').exists()
    existen_contratos_asignados = ContratoDip.objects.filter(status=True, validadorgp=persona,fechainicio__lte=datetime.now(), fechafin__gte=datetime.now()).exists()

    return existen_contratos_asignados,existen_solicitudes_para_grupo_revisor

def validarDiasSolicitud(request, fecha, data):
    try:
        diasemana, dias = fecha.strftime('%A'), 0
        if diasemana == 'Friday' or diasemana == 'friday':
            dias = 3
        if diasemana == 'Saturday' or diasemana == 'saturday':
            dias = 2
        if diasemana == 'Sunday' or diasemana == 'sunday':
            dias = 1
        return {'result': True, 'dias': dias}
    except Exception as ex:
        return {'result': False, 'ex': str(ex)}


def registroHistorial(request, solicitud, paso, estado, persona, observacion, tipo, falerta=None):
    try:
        historial = HistorialProcesoSolicitud(solicitud=solicitud, estado=estado, persona=persona, observacion=observacion, accion=tipo)
        if paso:
            historial.paso = paso
        if falerta:
            historial.fecha_maxima = falerta
        historial.save(request)
        return {'resp': True}
    except Exception as ex:
        return {'resp': False, 'ex': str(ex)}

def integrante_tiene_actas_de_pagos_asignadas(persona):
    # actas de pago por honoario profesionales
    existen_actas_de_pagos_que_deba_firmar = False
    eActaPagoPosgrado = ActaPagoPosgrado.objects.filter(status=True)
    if eActaPagoPosgrado.exists():
        existen_actas_de_pagos_que_deba_firmar = eActaPagoPosgrado.first().existen_acta_pago_que_deba_firmar(persona)

    return existen_actas_de_pagos_que_deba_firmar


def validacion_todas_las_solicitudes_son_del_mismo_mes(eSolicitudPagos):
    try:
        eDetalleActaPagoMes = eSolicitudPagos.values('fechainicio__month').distinct().order_by('fechainicio__month')
        eDetalleActaPagoAnio = eSolicitudPagos.values('fechainicio__year').distinct().order_by('fechainicio__year')
        return True if eDetalleActaPagoMes.count() == 1 and eDetalleActaPagoAnio.count() == 1 else False
    except Exception as ex:
        pass


def validacion_todas_las_solicitudes_son_tipo_administrativo(eSolicitudPagos):
    try:
        eDetalleActaPago = eSolicitudPagos.values('contrato__tipogrupo').filter(contrato__tipogrupo=1).distinct().order_by('contrato__tipogrupo')
        return True if eDetalleActaPago.count() == 1 else False
    except Exception as ex:
        pass


def validacion_todas_las_solicitudes_son_tipo_profesor(eSolicitudPagos):
    try:
        eDetalleActaPago = eSolicitudPagos.values('contrato__tipogrupo').filter(contrato__tipogrupo=2).distinct().order_by('contrato__tipogrupo')
        return True if eDetalleActaPago.count() == 1 else False
    except Exception as ex:
        pass


def get_requisitos_solicitados_configurados_administrativos():
    try:
        requisitos = None
        eGrupoRequisitoPago = GrupoRequisitoPago.objects.filter(status=True,activo=True,tipogrupo=1)
        if eGrupoRequisitoPago.exists():
            requisitos = eGrupoRequisitoPago.first().get_requisitos()
        return requisitos
    except Exception as ex:
        pass

def validacion_todas_las_solicitudes_subieron_los_requisitos_de_pago_excluyendo_la_factura(eSolicitudPagos):
    try:
        CERTIFICACION_BANCARIA = 5
        FORMATO_DE_PROVEEDORES = 6
        CERTIFICACION_PRESUPUESTARIA = 15
        CHECK_LIST_DE_PAGO = 16
        FACTURA = 4
        RELACION_DE_DEPENDENCIA_LABORAL = 20
        IMPEDIMENTO_EJERCER_CARGO_PUBLICO = 19
        TODOS_SUBIERON_TODOS_LOS_REQUISITOS = True
        for eSolicitudPago in eSolicitudPagos:
             for eRequisitoPagoDip in get_requisitos_solicitados_configurados_administrativos():
                 if not eRequisitoPagoDip.requisitopagodip.id == CHECK_LIST_DE_PAGO and not eRequisitoPagoDip.requisitopagodip.id ==  FACTURA and not eRequisitoPagoDip.requisitopagodip.id == IMPEDIMENTO_EJERCER_CARGO_PUBLICO and not eRequisitoPagoDip.requisitopagodip.id ==  RELACION_DE_DEPENDENCIA_LABORAL:
                     if not eSolicitudPago.tiene_cargado_documento_check_list_acta_pago(eRequisitoPagoDip.requisitopagodip):
                         TODOS_SUBIERON_TODOS_LOS_REQUISITOS = False
                         break
             if not TODOS_SUBIERON_TODOS_LOS_REQUISITOS:
                 break

        return TODOS_SUBIERON_TODOS_LOS_REQUISITOS
    except Exception as ex:
        pass

def validacion_todas_las_solicitudes_tienen_aprobado_los_requisitos_por_analista_excluyendo_la_factura(eSolicitudPagos):
    try:
        INFORME_DE_ACTIVIDADES = 14
        CERTIFICACION_BANCARIA = 5
        FORMATO_DE_PROVEEDORES = 6
        CERTIFICACION_PRESUPUESTARIA = 15
        CHECK_LIST_DE_PAGO = 16
        FACTURA = 4
        RELACION_DE_DEPENDENCIA_LABORAL = 20
        IMPEDIMENTO_EJERCER_CARGO_PUBLICO = 19
        TODOS_TIENEN_APROBADO_LOS_REQUISITOS_POR_ANALISTA = True
        for eSolicitudPago in eSolicitudPagos:
             for eRequisitoPagoDip in get_requisitos_solicitados_configurados_administrativos():
                 if not eRequisitoPagoDip.requisitopagodip.id == CHECK_LIST_DE_PAGO and not eRequisitoPagoDip.requisitopagodip.id ==  FACTURA and not eRequisitoPagoDip.requisitopagodip.id == INFORME_DE_ACTIVIDADES and not eRequisitoPagoDip.requisitopagodip.id == IMPEDIMENTO_EJERCER_CARGO_PUBLICO and not eRequisitoPagoDip.requisitopagodip.id ==  RELACION_DE_DEPENDENCIA_LABORAL:
                     if not eSolicitudPago.tiene_aprobado_por_analista_documento_check_list_acta_pago(eRequisitoPagoDip.requisitopagodip):
                         TODOS_TIENEN_APROBADO_LOS_REQUISITOS_POR_ANALISTA = False
                         break
             if not TODOS_TIENEN_APROBADO_LOS_REQUISITOS_POR_ANALISTA:
                 break

        return TODOS_TIENEN_APROBADO_LOS_REQUISITOS_POR_ANALISTA
    except Exception as ex:
        pass

@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    usuario = request.user
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']
    hoy = datetime.now()
    if request.method == 'POST':
        res_json = []
        action = request.POST['action']

        if action == 'validarrequisito':
            try:
                instance = RequisitoPasoSolicitudPagos.objects.get(id=int(request.POST['id']))
                instance.estado = request.POST['est']
                instance.observacion = request.POST['obs']
                instance.save(request)
                log(u'{} : Validación de Requisito Individual - {}'.format(instance.paso.paso.descripcion, instance), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'validarpaso':
            try:
                with transaction.atomic():
                    filtro = PasoSolicitudPagos.objects.get(pk=int(request.POST['id']))
                    filtro.estado = request.POST['estado']
                    filtro.observacion = request.POST['observacion'].upper()
                    filtro.fecha_revision = datetime.now()
                    filtro.persona_revision = persona
                    filtro.save(request)
                    solicitud = SolicitudPago.objects.get(pk=filtro.solicitud.pk)
                    pasoanterior = solicitud.traer_ultimo_historial()
                    pasoanterior.estado = 3
                    pasoanterior.fecha_ejecucion = datetime.now()
                    pasoanterior.persona_ejecucion = persona
                    pasoanterior.save(request)
                    respmensaje = ''
                    if filtro.estado == '1':
                        pasosiguiente = PasoSolicitudPagos.objects.filter(solicitud=filtro.solicitud, paso__pasoanterior=filtro.paso)
                        if pasosiguiente.exists():
                            filtropaso = pasosiguiente.first()
                            filtropaso.estado = 2
                            fechaactual, fechalimite = datetime.now(), datetime.now()
                            validar = validarDiasSolicitud(request, fechaactual, data)
                            if validar['result']:
                                dias, horas = validar['dias'], filtropaso.paso.tiempoalerta_carga
                                fechalimite = fechaactual + timedelta(days=dias) + timedelta(hours=filtropaso.paso.tiempoalerta_carga)
                            filtropaso.save(request)
                            registroHistorial(request, filtropaso.solicitud, filtropaso, 2, persona, filtropaso.paso.descripcion, 1, fechalimite)
                            respmensaje = 'Validación guardada, se habilitó un lapso de {} horas para la generación del informe.'.format(filtro.paso.tiempoalerta_carga)
                        else:
                            if filtro.paso.finaliza:
                                respmensaje = 'Validación del proceso para la solcitiud del pago finalizada.'
                        messages.success(request, '{} APROBADO'.format(filtro.paso.descripcion))
                    else:
                        messages.success(request, '{} RECHAZADO'.format(filtro.paso.descripcion))
                        fechaactual, fechalimite = datetime.now(), datetime.now()
                        validar = validarDiasSolicitud(request, fechaactual, data)
                        if validar['result']:
                            dias, horas = validar['dias'], filtro.paso.tiempoalerta_validacion
                            fechalimite = fechaactual + timedelta(days=dias) + timedelta(hours=filtro.paso.tiempoalerta_validacion)
                        registroHistorial(request, filtro.solicitud, filtro, 2, persona, 'CORREGIR DOCUMENTOS SOPORTE', 1, fechalimite)
                        respmensaje = 'Validación guardada, se habilitó un lapso de {} horas para corregir la información.'.format(filtro.paso.tiempoalerta_carga)
                    log(u'{} : Validación de Requisitos - {}'.format(filtro.paso.descripcion, filtro), request, "edit")
                    return JsonResponse({"result": False, 'modalsuccess': True, 'mensaje': respmensaje}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'cargarrequisitos':
            try:
                with transaction.atomic():
                    filtro = PasoSolicitudPagos.objects.get(pk=int(request.POST['id']))
                    filtro.estado = 6
                    filtro.fecha_revision = datetime.now()
                    filtro.persona_revision = persona
                    filtro.save(request)
                    solicitud = SolicitudPago.objects.get(pk=filtro.solicitud.pk)
                    pasoanterior = solicitud.traer_ultimo_historial()
                    pasoanterior.estado = 3
                    pasoanterior.fecha_ejecucion = datetime.now()
                    pasoanterior.persona_ejecucion = persona
                    pasoanterior.save(request)
                    respmensaje = ''
                    for dr in filtro.requisito_paso():
                        if 'req{}'.format(dr.pk) in request.FILES:
                            newfile = request.FILES['req{}'.format(dr.pk)]
                            extension = newfile._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if newfile.size > 15194304:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                            if not exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                            nombre_persona = remover_caracteres_especiales_unicode(persona.apellido1).lower().replace(' ','_')
                            newfile._name = generar_nombre("{}__{}".format(nombre_persona, dr.requisito.nombre_input()), newfile._name)
                            dr.archivo = newfile
                            dr.save(request)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Suba todo los requisitos, {}.".format(dr.requisito.nombre)}, safe=False)
                    fechaactual, fechalimite = datetime.now(), datetime.now()
                    validar = validarDiasSolicitud(request, fechaactual, data)
                    if validar['result']:
                        dias, horas = validar['dias'], filtro.paso.tiempoalerta_validacion
                        fechalimite = fechaactual + timedelta(days=dias) + timedelta(hours=filtro.paso.tiempoalerta_validacion)
                    registroHistorial(request, filtro.solicitud, filtro, 2, persona, 'VALIDACIÓN DE {}'.format(filtro.paso.descripcion), 2, fechalimite)
                    respmensaje = 'Documentación cargada, se habilitó un lapso de {} horas para la validación de la información.'.format(filtro.paso.tiempoalerta_validacion)
                    log(u'Valido Paso de Solicitud de Pago: {}'.format(filtro), request, "edit")
                    return JsonResponse({"result": False, 'modalsuccess': True, 'mensaje': respmensaje}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'edit_rmu_iva_acta_pago':
            try:
                pk = request.POST.get('id', None)
                f = DetalleActaPagoValoresForm(request.POST)
                if f.is_valid():
                    eDetalleActaPago = DetalleActaPago.objects.get(pk=pk)
                    eDetalleActaPago.rmu = f.cleaned_data.get('rmu')
                    eDetalleActaPago.valoriva = f.cleaned_data.get('valorIva')
                    eDetalleActaPago.valortotal = f.cleaned_data.get('valorTotal')
                    eDetalleActaPago.save(request)
                    log(f'Edit valor a pagar : {eDetalleActaPago}', request, 'change')
                    eDetalleActaPago.actapagoposgrado.generar_pdf_acta_pago_en_tiempo_real(request,persona)

                return JsonResponse({"result": True, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos."})

        elif action == 'edit_documentacion_de_soporte_acta_pago':
            try:
                pk = request.POST.get('id', None)
                f = DetalleItemsActaPagoPosgradoForm(request.POST)
                if f.is_valid():
                    eDetalleItemsActaPagoPosgrado = DetalleItemsActaPagoPosgrado.objects.get(pk=pk)
                    eDetalleItemsActaPagoPosgrado.detallecontrato = f.cleaned_data.get('detallecontrato')
                    eDetalleItemsActaPagoPosgrado.documentohabilitante = f.cleaned_data.get('documentohabilitante')
                    eDetalleItemsActaPagoPosgrado.observacion = f.cleaned_data.get('observacion')
                    eDetalleItemsActaPagoPosgrado.save(request)
                    log(f'Edit detalle item acta pago : {eDetalleItemsActaPagoPosgrado}', request, 'change')
                    eDetalleItemsActaPagoPosgrado.actapagoposgrado.generar_pdf_acta_pago_en_tiempo_real(request,persona)

                return JsonResponse({"result": True, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos."})

        elif action == 'add_documentacion_de_soporte_acta_pago':
            try:
                pk = request.POST.get('id', None)
                f = DetalleItemsActaPagoPosgradoForm(request.POST)
                if f.is_valid():
                    eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=pk)
                    eDetalleItemsActaPagoPosgrado = DetalleItemsActaPagoPosgrado(
                        actapagoposgrado=eActaPagoPosgrado,
                        detallecontrato=f.cleaned_data.get('detallecontrato'),
                        documentohabilitante=f.cleaned_data.get('documentohabilitante'),
                        observacion = f.cleaned_data.get('observacion')
                    )

                    eDetalleItemsActaPagoPosgrado.save(request)
                    log(f'Add detalle item acta pago : {eDetalleItemsActaPagoPosgrado}', request, 'add')
                    eDetalleItemsActaPagoPosgrado.actapagoposgrado.generar_pdf_acta_pago_en_tiempo_real(request,persona)

                return JsonResponse({"result": True, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos."})

        elif action == 'informe-administrativo-posgrado-masivo':
            try:
                data['hoy'] = hoy = datetime.now()
                ids = request.POST.get('contrato_posgrado',None).split(',')
                certificado = request.FILES["firma"]
                contrasenaCertificado = request.POST['palabraclave']
                extension_certificado = os.path.splitext(certificado.name)[1][1:]
                bytes_certificado = certificado.read()
                for id in ids:
                    reg = HistorialProcesoSolicitud.objects.get(status=True,id=int(encrypt(id)))
                    requi = reg.requisito
                    if HistorialProcesoSolicitud.objects.filter(status=True, persona_ejecucion=persona,requisito=reg.requisito):
                        hist_= HistorialProcesoSolicitud.objects.filter(status=True, persona_ejecucion=persona,requisito=reg.requisito).order_by('-id').first()
                        hist_.fecha_ejecucion=hoy
                    else:
                        hist_ = HistorialProcesoSolicitud(
                            observacion=f'Informe firmado por {persona.__str__()}',
                            fecha_ejecucion=hoy,
                            persona_ejecucion=persona,
                            requisito=requi,
                            estado=1
                        )
                        hist_.save(request)
                    palabras = f'{persona}'
                    x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(reg.archivo.url, palabras)
                    datau = JavaFirmaEc(
                        archivo_a_firmar=reg.archivo, archivo_certificado=bytes_certificado,
                        extension_certificado=extension_certificado,
                        password_certificado=contrasenaCertificado,
                        page=int(numpaginafirma), reason='', lx=x+50, ly=y+20
                    ).sign_and_get_content_bytes()
                    documento_a_firmar = io.BytesIO()
                    documento_a_firmar.write(datau)
                    documento_a_firmar.seek(0)
                    hist_.archivo.save(f'{reg.archivo.name.split("/")[-1].replace(".pdf", "")}_firmado.pdf',ContentFile(documento_a_firmar.read()))
                    requi.estado = 1
                    requi.save(request)
                    cuerpo = f"Informe mensual para pago de posgrado validado y firmado por {persona}"
                    persona_notificacion = None
                    redirect_mod = f'/adm_solicitudpago'
                    estado_solicitud = 7
                    requisito = hist_.requisito
                    solicitud = requisito.solicitud
                    contrato = solicitud.contrato
                    if contrato.validadorgp:
                        persona_notificacion = contrato.validadorgp
                        redirect_mod = f'/adm_solicitudpago?action=viewinformesmen'
                    else:
                        persona_notificacion = contrato.persona
                    solicitud.estado = estado_solicitud
                    solicitud.save(request)
                    cuerpo = f"Informe mensual de posgrado validado y firmado por {persona}"
                    notificacion(
                        "Informe mensual de posgrado validado por %s" % persona,
                        cuerpo, requi.solicitud.contrato.persona, None, f'/pro_solicitudpago',
                        requi.solicitud.id,
                        1, 'sga', requi, request)
                    persona_gestionposgrado = Persona.objects.get(status=True, id=2356)
                    notificacion(
                        "Solicitud de pago de %s firmado por su jefe inmediato" % hist_.requisito.solicitud.contrato.persona,
                        cuerpo, persona_notificacion, None, f'https://sga.unemi.edu.ec{hist_.archivo.url}',
                        hist_.id,
                        1, 'sga', hist_, request)
                    obshisto = HistorialObseracionSolicitudPago(
                        solicitud=solicitud,
                        observacion=cuerpo,
                        persona=persona,
                        estado=estado_solicitud,
                        fecha=hoy
                    )
                    obshisto.save(request)
                    log(f'Firma jefe inmediato el informe mensual de la solicitud: {solicitud}', request, 'change')
                    ###
                    soli = solicitud
                    soli.estado = 8
                    soli.save(request)
                    log(f'Aprobo el informe validado por el jefe inmediato: {soli}', request, 'change')
                    log(f'Firma jefe inmediato el informe mensual de la solicitud: {solicitud}', request, 'change')
                res_json = {"result": False}
            except Exception as ex:
                err_ = f"Ocurrio un error: {ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}"
                transaction.set_rollback(True)
                res_json = {"result": True, "mensaje": err_}
            return JsonResponse(res_json)

        elif action == 'informe-administrativo-posgrado':
            try:
                data['hoy'] = hoy = datetime.now()
                id = request.POST.get('contrato_posgrado',None)
                certificado = request.FILES["firma"]
                contrasenaCertificado = request.POST['palabraclave']
                extension_certificado = os.path.splitext(certificado.name)[1][1:]
                bytes_certificado = certificado.read()

                reg = HistorialProcesoSolicitud.objects.get(status=True,id=int(encrypt(id)))
                requi = reg.requisito
                if HistorialProcesoSolicitud.objects.filter(status=True, persona_ejecucion=persona,requisito=reg.requisito):
                    hist_= HistorialProcesoSolicitud.objects.filter(status=True, persona_ejecucion=persona,requisito=reg.requisito).order_by('-id').first()
                    hist_.fecha_ejecucion=hoy
                else:
                    hist_ = HistorialProcesoSolicitud(
                        observacion=f'Informe firmado por {persona.__str__()}',
                        fecha_ejecucion=hoy,
                        persona_ejecucion=persona,
                        requisito=requi,
                        estado=1
                    )
                    hist_.save(request)
                palabras = f'{persona}'
                x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(reg.archivo.url, palabras)
                datau = JavaFirmaEc(
                    archivo_a_firmar=reg.archivo, archivo_certificado=bytes_certificado,
                    extension_certificado=extension_certificado,
                    password_certificado=contrasenaCertificado,
                    page=int(numpaginafirma), reason='', lx=x+50, ly=y+20
                ).sign_and_get_content_bytes()
                documento_a_firmar = io.BytesIO()
                documento_a_firmar.write(datau)
                documento_a_firmar.seek(0)
                hist_.archivo.save(f'{reg.archivo.name.split("/")[-1].replace(".pdf", "")}_firmado.pdf',ContentFile(documento_a_firmar.read()))
                requi.estado = 1
                requi.save(request)
                cuerpo = f"Informe mensual para pago de posgrado validado y firmado por {persona}"
                persona_notificacion = None
                redirect_mod = f'/adm_solicitudpago'
                estado_solicitud = 7
                requisito = hist_.requisito
                solicitud = requisito.solicitud
                contrato = solicitud.contrato
                if contrato.validadorgp:
                    persona_notificacion = contrato.validadorgp
                    redirect_mod = f'/adm_solicitudpago?action=viewinformesmen'
                else:
                    persona_notificacion = contrato.persona
                solicitud.estado = estado_solicitud
                solicitud.save(request)
                notificacion(
                    "Informe mensual de posgrado validado por %s" % persona,
                    cuerpo, requi.solicitud.contrato.persona, None, f'/pro_solicitudpago',
                    requi.solicitud.id,
                    1, 'sga', requi, request)
                notificacion(
                    "Solicitud de pago de %s firmado por su jefe inmediato" % hist_.requisito.solicitud.contrato.persona,
                    cuerpo, persona_notificacion, None, f'https://sga.unemi.edu.ec{hist_.archivo.url}',
                    hist_.id,
                    1, 'sga', hist_, request)
                obshisto = HistorialObseracionSolicitudPago(
                    solicitud=solicitud,
                    observacion=cuerpo,
                    persona=persona,
                    estado=estado_solicitud,
                    fecha=hoy
                )
                obshisto.save(request)
                log(f'Firma jefe inmediato el informe mensual de la solicitud: {solicitud}', request, 'change')
                ###
                soli = solicitud
                soli.estado = 8
                soli.save(request)
                log(f'Aprobo el informe validado por el jefe inmediato: {soli}', request, 'change')

                obshisto = HistorialObseracionSolicitudPago(
                    solicitud=soli,
                    observacion=f'El informe ha sido aprobado.',
                    persona=persona,
                    estado=8,
                    fecha=datetime.now()
                )
                obshisto.save(request)


                res_json = {"result": False}
            except Exception as ex:
                err_ = f"Ocurrio un error: {ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}"
                transaction.set_rollback(True)
                res_json = {"result": True, "mensaje": err_}
            return JsonResponse(res_json)

        elif action == 'notificarcambios':
            try:
                id = request.POST['id']
                numero = int(request.POST.get('numero'))
                obse = request.POST.get('obs')
                requisito = RequisitoSolicitudPago.objects.get(status=True, id=int(encrypt(id)))
                soli = requisito.solicitud
                if numero==1:
                    requisito.estado = 2
                    requisito.save(request)
                    soli.estado = 6
                    soli.save(request)
                    notificacion(f'Se aprobó solicitud de pago de {soli.contrato.persona}.',f'El informe y requisitos de pago han sido aprobados. {obse}',soli.contrato.gestion.responsable,None,'/adm_solicitudpago',soli.id,1,'sga',soli,request)
                    obshisto = HistorialObseracionSolicitudPago(
                        solicitud=soli,
                        observacion=f'El informe ha sido aprobado. {obse}',
                        persona=persona,
                        estado=6,
                        fecha=datetime.now()
                    )
                    obshisto.save(request)
                elif numero==2:
                    requisito.estado = 5
                    requisito.save(request)
                    soli.estado = 5
                    soli.save(request)
                    notificacion(f'Se devolvió la solicitud  de pago.', f'La solicitud se ha devuelto: {soli} por el motivo: {obse}', soli.contrato.persona, None, '/pro_solicitudpago', soli.id, 1, 'sga', soli,request)
                    obshisto = HistorialObseracionSolicitudPago(
                        solicitud=soli,
                        observacion=f'El informe se ha devuelto el informe {soli} por el motivo: {obse}',
                        persona=persona,
                        estado=0,
                        fecha=datetime.now()
                    )
                    obshisto.save(request)
                res_js = {'result':True}
            except Exception as ex:
                err_ = f'{ex} ({sys.exc_info()[-1].tb_lineno})'
                res_js = {'result':False, 'mensaje':err_}
            return JsonResponse(res_js)

        elif action == 'notificarcambiosfinal':
            try:
                id = request.POST['id']
                numero = int(request.POST.get('numero'))
                obse = request.POST.get('obs')
                requisito = RequisitoSolicitudPago.objects.get(status=True, id=int(encrypt(id)))
                soli = requisito.solicitud
                if numero == 1:
                    requisito.estado = 2
                    requisito.save(request)
                    soli.estado = 8
                    soli.save(request)
                    log(f'Aprobo el informe validado por el jefe inmediato: {soli}', request, 'change')
                    notificacion(f'Se aprobó el informe de pago de {soli.contrato.persona}.',
                                 f'El informe ha sido aprobado. {obse}', soli.contrato.persona, None,
                                 '/adm_solicitudpago', soli.id, 1, 'sga', soli, request)

                    obshisto = HistorialObseracionSolicitudPago(
                        solicitud=soli,
                        observacion=f'El informe ha sido aprobado. {obse}',
                        persona=persona,
                        estado=8,
                        fecha=datetime.now()
                    )
                    obshisto.save(request)
                elif numero == 2:
                    requisito.estado = 5
                    requisito.save(request)
                    soli.estado = 5
                    soli.save(request)
                    log(f'Rechazo el informe validado por el jefe inmediato: {soli}', request, 'change')
                    notificacion(f'Se devolvió el informe de pago.',
                                 f'El informe se ha devuelto el informe {soli} por el motivo: {obse}',
                                 soli.contrato.persona, None, '/pro_solicitudpago', soli.id, 1, 'sga', soli, request)

                    notificacion(f'Jefe inmediato devolvió el informe de pago.',
                                 f'El informe se ha devuelto el informe {soli} por el motivo: {obse}',
                                 soli.contrato.gestion.responsable, None, '/pro_solicitudpago?action=viewinformesmen', soli.id, 1, 'sga', soli, request)
                    obshisto = HistorialObseracionSolicitudPago(
                        solicitud=soli,
                        observacion=f'El informe se ha devuelto el informe {soli} por el motivo: {obse}',
                        persona=persona,
                        estado=0,
                        fecha=datetime.now()
                    )
                    obshisto.save(request)

                res_js = {'result': True}
            except Exception as ex:
                err_ = f'{ex} ({sys.exc_info()[-1].tb_lineno})'
                res_js = {'result': False, 'mensaje': ''}
            return JsonResponse(res_js)

        elif action == 'notificarcambiosfinaljefeinmediado':
                    try:
                        id = request.POST['id']
                        numero = int(request.POST.get('numero'))
                        obse = request.POST.get('obs')
                        requisito = RequisitoSolicitudPago.objects.get(status=True, id=int(encrypt(id)))
                        soli = requisito.solicitud
                        if numero == 1:
                            requisito.estado = 2
                            requisito.save(request)
                            soli.estado = 8
                            soli.save(request)
                            log(f'Aprobo el informe validado por el jefe inmediato: {soli}', request, 'change')
                            notificacion(f'Se aprobó el informe de pago de {soli.contrato.persona}.',
                                         f'El informe ha sido aprobado. {obse}', soli.contrato.persona, None,
                                         '/adm_solicitudpago', soli.id, 1, 'sga', soli, request)

                            obshisto = HistorialObseracionSolicitudPago(
                                solicitud=soli,
                                observacion=f'El informe ha sido aprobado. {obse}',
                                persona=persona,
                                estado=8,
                                fecha=datetime.now()
                            )
                            obshisto.save(request)
                        elif numero == 2:
                            requisito.estado = 5
                            requisito.save(request)
                            soli.estado = 0
                            soli.save(request)
                            log(f'Rechazo el informe validado por el jefe inmediato: {soli}', request, 'change')
                            notificacion(f'Se devolvió el informe de pago.',
                                         f'El informe se ha devuelto el informe {soli} por el motivo: {obse}',
                                         soli.contrato.persona, None, '/pro_solicitudpago', soli.id, 1, 'sga', soli, request)

                            notificacion(f'Jefe inmediato devolvió el informe de pago.',
                                         f'El informe se ha devuelto el informe {soli} por el motivo: {obse}',
                                         soli.contrato.validadorgp, None, '/pro_solicitudpago?action=viewinformesmen', soli.id, 1, 'sga', soli, request)
                            obshisto = HistorialObseracionSolicitudPago(
                                solicitud=soli,
                                observacion=f'El informe se ha devuelto el informe {soli} por el motivo: {obse}',
                                persona=persona,
                                estado=0,
                                fecha=datetime.now()
                            )
                            obshisto.save(request)

                        res_js = {'result': True}
                    except Exception as ex:
                        err_ = f'{ex} ({sys.exc_info()[-1].tb_lineno})'
                        res_js = {'result': False, 'mensaje': ''}
                    return JsonResponse(res_js)

        elif action == 'aprobar_actividade_ind':
            try:
                datos = json.loads(request.POST.get('datos', []))
                id = request.POST.get('id_soli', None)
                soli = SolicitudPago.objects.get(status=True, id=int(encrypt(id)))
                soli.estado = 6
                soli.save(request)
                requisito = RequisitoSolicitudPago.objects.filter(status=True, solicitud=soli, requisito_id=14).order_by('id').first()
                requisito.estado = 2
                requisito.save(request)
                notificacion(f'Se aprobó el informe de pago de {soli.contrato.persona}.',
                             f'El informe ha sido aprobado.', soli.contrato.gestion.responsable, None,
                             '/adm_solicitudpago', soli.id, 1, 'sga', soli, request)
                obshisto = HistorialObseracionSolicitudPago(
                    solicitud=soli,
                    observacion=f'El informe ha sido aprobado.',
                    persona=persona,
                    estado=6,
                    fecha=datetime.now()
                )
                obshisto.save(request)
                res_js = {'result': True}
            except Exception as ex:
                transaction.set_rollback(True)
                msg_err = f'{ex} ({sys.exc_info()[-1].tb_lineno})'
                res_js = {'result': False, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'rechazar_actividades_ind':
            try:
                datos = json.loads(request.POST.get('datos',[]))
                id = request.POST.get('id_soli',None)
                soli = SolicitudPago.objects.get(status=True, id=int(encrypt(id)))
                if len(datos) <= 0: raise NameError("Debe haber realizado al menos una observación a un registro.")
                for registro in datos:
                    bitacora = BitacoraActividadDiaria.objects.get(status=True, id=int(encrypt(registro['id'])))
                    bitacora.observacion = registro['observacion']
                    bitacora.corregida = False
                    bitacora.save(request)
                soli.estado = 5
                soli.save(request)
                requisito = RequisitoSolicitudPago.objects.filter(status=True, solicitud=soli, requisito_id=14).order_by('-id').first()
                requisito.estado = 5
                requisito.save(request)
                notificacion(f'Se devolvió el informe de pago.',
                             f'El informe se ha devuelto el informe {soli}',
                             soli.contrato.persona, None, f'/pro_solicitudpago?action=viewrevisionactividades&id={encrypt(soli.id)}', soli.id, 1, 'sga', soli, request)
                obshisto = HistorialObseracionSolicitudPago(
                    solicitud=soli,
                    observacion=f'El informe se ha devuelto el informe {soli}',
                    persona=persona,
                    estado=0,
                    fecha=datetime.now()
                )
                obshisto.save(request)
                log(f"Actualizo las actividades de la bitacora: {datos}", request, "change")
                res_js = {'result':True}
            except Exception as ex:
                transaction.set_rollback(True)
                msg_err = f'{ex} ({sys.exc_info()[-1].tb_lineno})'
                res_js = {'result':False,'mensaje':msg_err}
            return JsonResponse(res_js)

        elif action == 'verificar_aprobacion_requisitos_actividades':
            try:
                LEGALIZADO_JEFE_INMEDIATO =7
                POR_LEGALIZADO_JEFE_INMEDIATO =6
                PROCESO_EN_EJECUCIÓN_G_P= 8
                id = request.POST.get('id_soli',None)
                soli = SolicitudPago.objects.get(status=True, id=int(encrypt(id)))
                requisito = RequisitoSolicitudPago.objects.filter(status=True, solicitud=soli, requisito_id=14).order_by('-id').first()
                requisito.estado = 2
                requisito.save(request)
                obshisto = HistorialObseracionSolicitudPago(
                    solicitud=soli,
                    observacion=f'El informe ha sido aprobado las actividades {soli}',
                    persona=persona,
                    estado=2,
                    fecha=datetime.now()
                )
                obshisto.save(request)
                log(f"aprobo las actividades de la bitacora", request, "change")
                soli.estado = 3
                soli.save(request)
                if persona.pk.__str__()  in variable_valor('ANALISTAS_PAGO_DEPARTAMENTO_TIC'):  # guerra gaibor -encargadapagos tics
                    if soli.tienen_aprobado_los_requisitos_por_analista_excluyendo_la_factura_y_requisitos_tics():
                        if not soli.estado == PROCESO_EN_EJECUCIÓN_G_P:
                            if soli.estado == LEGALIZADO_JEFE_INMEDIATO:
                                soli.estado = PROCESO_EN_EJECUCIÓN_G_P
                            else:
                                soli.estado = POR_LEGALIZADO_JEFE_INMEDIATO
                            soli.save(request)
                else:
                    if soli.tienen_aprobado_los_requisitos_por_analista_excluyendo_la_factura():
                        if not soli.estado == PROCESO_EN_EJECUCIÓN_G_P:
                            if soli.estado == LEGALIZADO_JEFE_INMEDIATO:
                                soli.estado = PROCESO_EN_EJECUCIÓN_G_P
                            else:
                                soli.estado = POR_LEGALIZADO_JEFE_INMEDIATO
                            soli.save(request)
                res_js = {'result':True}
            except Exception as ex:
                transaction.set_rollback(True)
                msg_err = f'{ex} ({sys.exc_info()[-1].tb_lineno})'
                res_js = {'result':False,'mensaje':msg_err}
            return JsonResponse(res_js)

        elif action == 'validar_requisito_pago':
            try:
                eHistorialProcesoSolicitud = HistorialProcesoSolicitud.objects.get(pk=int(request.POST['id']))
                estado, observacion,fecha_caducidad = int(request.POST.get('est', 0)), request.POST.get('obs'), request.POST.get('fecha_caducidad')
                if not estado == 0:
                    eHistorialProcesoSolicitud.guardar_revision_requisito_pago(request,estado,observacion,persona,fecha_caducidad)
                return JsonResponse({"result": "ok", 'mensaje': u"Requisito validado"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

        elif action == 'revision_final_requisito_de_pago':
            try:
                PROCESO_EN_EJECUCION_G_P = 8
                LEGALIZADO_JEFE_INMEDIATO = 7
                POR_LEGALIZADO_JEFE_INMEDIATO = 6
                eSolicitudPago = SolicitudPago.objects.get(pk=int(request.POST['id']))
                if persona.pk.__str__()  in variable_valor('ANALISTAS_PAGO_DEPARTAMENTO_TIC'):  # guerra gaibor -encargadapagos tics
                    if eSolicitudPago.tienen_aprobado_los_requisitos_por_analista_excluyendo_la_factura_y_requisitos_tics() and (eSolicitudPago.traer_file_firmado_colaborador().requisito.estado ==  2 or eSolicitudPago.traer_file_firmado_colaborador().requisito.estado == 1 ):
                        if not eSolicitudPago.estado == PROCESO_EN_EJECUCION_G_P:
                            if eSolicitudPago.estado == LEGALIZADO_JEFE_INMEDIATO:
                                eSolicitudPago.estado = PROCESO_EN_EJECUCION_G_P
                                notificacion(f'Solicitud de pago aprobada para informe {eSolicitudPago.contrato.persona}.',
                                             f'El informe y requisitos de pago han sido aprobados para informe de pago.',
                                             eSolicitudPago.contrato.validadorgp, None, '/adm_solicitudpago',
                                             eSolicitudPago.id, 1,
                                             'sga', eSolicitudPago, request)
                            else:
                                eSolicitudPago.estado = POR_LEGALIZADO_JEFE_INMEDIATO
                                notificacion(f'Revisión Solicitud de pago {eSolicitudPago.contrato.persona}.',
                                             f'Revisión del informe de actividades',
                                             eSolicitudPago.contrato.gestion.responsable, None, '/adm_solicitudpago', eSolicitudPago.id, 1,
                                             'sga', eSolicitudPago, request)
                            eSolicitudPago.save(request)
                else:
                    if eSolicitudPago.tienen_aprobado_los_requisitos_por_analista_excluyendo_la_factura() and (
                            eSolicitudPago.traer_file_firmado_colaborador().requisito.estado == 2 or eSolicitudPago.traer_file_firmado_colaborador().requisito.estado == 1):
                        if not eSolicitudPago.estado == PROCESO_EN_EJECUCION_G_P:
                            if eSolicitudPago.estado == LEGALIZADO_JEFE_INMEDIATO:
                                eSolicitudPago.estado = PROCESO_EN_EJECUCION_G_P
                                notificacion(
                                    f'Solicitud de pago aprobada para informe {eSolicitudPago.contrato.persona}.',
                                    f'El informe y requisitos de pago han sido aprobados para informe de pago.',
                                    eSolicitudPago.contrato.validadorgp, None, '/adm_solicitudpago',
                                    eSolicitudPago.id, 1,
                                    'sga', eSolicitudPago, request)
                            else:
                                eSolicitudPago.estado = POR_LEGALIZADO_JEFE_INMEDIATO
                                notificacion(f'Revisión Solicitud de pago {eSolicitudPago.contrato.persona}.',
                                             f'Revisión del informe de actividades',
                                             eSolicitudPago.contrato.gestion.responsable, None, '/adm_solicitudpago',
                                             eSolicitudPago.id, 1,
                                             'sga', eSolicitudPago, request)
                            eSolicitudPago.save(request)
                return JsonResponse({"result": "ok", 'mensaje': u"Requisitos validados"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

        elif action == 'importarcontratopago':
            try:
                pk = int(request.POST['id'])
                eRequisitoSolicitudPago = RequisitoSolicitudPago.objects.get(pk=pk)
                result =eRequisitoSolicitudPago.importar_guardar_contrato(request,persona)
                if result:
                    return JsonResponse({"result": "ok", 'mensaje': u"Requisito validado"})
                else:
                    return JsonResponse({"result": "bad", 'mensaje': u"No se encontro el archivo al migrar"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

        elif action == 'importarcertificacionpago':
            try:
                pk = int(request.POST['id'])
                eRequisitoSolicitudPago = RequisitoSolicitudPago.objects.get(pk=pk)
                result = eRequisitoSolicitudPago.importar_guardar_certificacionpresupuestaria(request,persona)
                if result:
                    return JsonResponse({"result": "ok", 'mensaje': u"Requisito validado"})
                else:
                    return JsonResponse({"result": "bad", 'mensaje': u"No se encontro el archivo al migrar"})
                return JsonResponse({"result": "ok", 'mensaje': u"Requisito validado"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})


        elif action == 'generar_acta_pago':
            try:
                id_string = request.POST.get('ids', 0)
                id_list = ast.literal_eval(id_string)
                eSolicitudPagos = SolicitudPago.objects.filter(status=True, pk__in =id_list )
                eConfiguracionActaPago = ConfiguracionActaPago.objects.filter(status=True).first()
                eActaPagoPosgrado = ActaPagoPosgrado(
                    fechaemision = hoy,
                    solicitadopor =  eConfiguracionActaPago.solicitadopor,
                    para =  eConfiguracionActaPago.para
                )
                eActaPagoPosgrado.save(request)
                eActaPagoPosgrado.set_secuencia_documento()
                guardado_correcto , mensaje = eActaPagoPosgrado.generar_actualizar_data_contenido_acta_pagos(eSolicitudPagos,persona,request)
                if not guardado_correcto:
                    raise NameError(mensaje)
                else:
                    eActaPagoPosgrado.generar_pdf_acta_pago_en_tiempo_real(request,persona)
                    return JsonResponse({"result": False, 'mensaje': mensaje,'rt':f"/adm_solicitudpago?action=configuraractapago&id={eActaPagoPosgrado.pk}"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"{ex.__str__()}"})

        elif action == 'firma_masiva_acta_pago_posgrado':
            try:
                id_string = request.POST.get('ids', 0)
                id_list = ast.literal_eval(id_string)
                observacion = f'Acta de pago firmado por {persona}'
                eActaPagoPosgrados = ActaPagoPosgrado.objects.filter(pk__in=id_list)
                firma = request.FILES.get("firma")
                passfirma = request.POST.get('palabraclave')
                persona = request.session.get('persona')
                observacion = f'Acta de pago firmado por {persona}'
                firma = request.FILES.get("firma")
                passfirma = request.POST.get('palabraclave')
                bytes_certificado = firma.read()
                extension_certificado = os.path.splitext(firma.name)[1][1:]

                for eActaPagoPosgrado in eActaPagoPosgrados:
                    puede, mensaje = eActaPagoPosgrado.puede_firmar_integrante_segun_orden(persona)
                    if puede:
                        integrante = eActaPagoPosgrado.get_integrante(persona)


                        if eActaPagoPosgrado.persona_es_quien_firma_acta_pago_check_list(integrante.pk):
                            pdf = eActaPagoPosgrado.archivo_check_list
                            palabras = u"%s" % integrante.persona
                            x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(pdf.url, palabras.lower().title(),horizontal=True)
                            datau = JavaFirmaEc(
                                archivo_a_firmar=pdf, archivo_certificado=bytes_certificado,
                                extension_certificado=extension_certificado,
                                password_certificado=passfirma,
                                page=int(numpaginafirma), reason='', lx=x + 5, ly=y -15
                            ).sign_and_get_content_bytes()

                            documento_a_firmar = io.BytesIO()
                            documento_a_firmar.write(datau)
                            documento_a_firmar.seek(0)
                            eActaPagoPosgrado.archivo_check_list.save(f'{eActaPagoPosgrado.archivo_check_list.name.split("/")[-1].replace(".pdf", "")}_firmado.pdf', ContentFile(documento_a_firmar.read()))
                            eActaPagoPosgrado.guardar_historial_acta_pago(request, persona, f"Check list firmado por  {persona}", eActaPagoPosgrado.archivo_check_list)
                        if not eActaPagoPosgrado.acta_pago_por_legalizar():
                            eActaPagoPosgrado.generar_actualizar_acta_pago_pdf_tics(request)

                        if integrante.persona.pk == 843:
                            palabras = 'DIRECTORA DE TECNOLOGÍA DE LA INFORMACIÓN Y COMUNICACIONES'
                        else:
                            palabras = u"%s" % integrante.persona.nombre_titulos3y4()
                        pdf = eActaPagoPosgrado.archivo
                        x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(pdf.url, palabras)

                        datau = JavaFirmaEc(
                            archivo_a_firmar=pdf, archivo_certificado=bytes_certificado,
                            extension_certificado=extension_certificado,
                            password_certificado=passfirma,
                            page=int(numpaginafirma), reason='', lx=x + 360, ly=y -15
                        ).sign_and_get_content_bytes()

                        documento_a_firmar = io.BytesIO()
                        documento_a_firmar.write(datau)
                        documento_a_firmar.seek(0)

                        eActaPagoPosgrado.archivo.save(f'{eActaPagoPosgrado.archivo.name.split("/")[-1].replace(".pdf", "")}_firmado.pdf', ContentFile(documento_a_firmar.read()))
                        integrante.firmo =True
                        integrante.save(request)
                        if eActaPagoPosgrado.persona_es_quien_firma_acta_pago_memo(integrante.pk) and not integrante.persona.pk == 843:
                            pdf = eActaPagoPosgrado.archivo_memo
                            palabras = u"%s" % integrante
                            x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(pdf.url, palabras.lower().title())
                            datau = JavaFirmaEc(
                                archivo_a_firmar=pdf, archivo_certificado=bytes_certificado,
                                extension_certificado=extension_certificado,
                                password_certificado=passfirma,
                                page=int(numpaginafirma), reason='', lx=x + 5, ly=y + 5
                            ).sign_and_get_content_bytes()

                            documento_a_firmar = io.BytesIO()
                            documento_a_firmar.write(datau)
                            documento_a_firmar.seek(0)
                            eActaPagoPosgrado.archivo_memo.save(f'{eActaPagoPosgrado.archivo_memo.name.split("/")[-1].replace(".pdf", "")}_firmado.pdf', ContentFile(documento_a_firmar.read()))


                        eActaPagoPosgrado.guardar_historial_acta_pago(request, persona, observacion,eActaPagoPosgrado.archivo)
                        eActaPagoPosgrado.actualizar_estado_del_acta_pago(request)
                        log(u"Firmo acta de pago por honorarios profesionales", request, 'edit')
                        eActaPagoPosgrado.notificar_orden_integrante_toca_firmar(request)
                    else:
                        raise NameError(f"{mensaje}")


                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s" % ex})


        elif action == 'add_integrantefirmaactapago':
            try:
                f = ActaPagoIntegrantesFirmaForm(request.POST)
                pk = int(request.POST.get('id','0'))
                if pk == 0:
                    raise NameError("Parametro no encontrado")
                eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=pk)
                f.edit(request.POST['persona'])
                if f.is_valid():
                    eActaPagoIntegrantesFirma = ActaPagoIntegrantesFirma(actapagoposgrado= eActaPagoPosgrado, ordenfirmaactapago=f.cleaned_data['responsabilidadfirma'], persona=f.cleaned_data['persona'])
                    eActaPagoIntegrantesFirma.save(request)
                    eActaPagoIntegrantesFirma.actapagoposgrado.generar_pdf_acta_pago_en_tiempo_real(request,persona)
                    log(u"Add eActaPagoIntegrantesFirma", request, 'add')
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.",
                                         "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'editsolicitadoporactapago':
            try:
                pk = request.POST.get('id', None)
                f = PersonaActaPagoForm(request.POST)
                f.edit(request.POST['persona'])
                if f.is_valid():
                    eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=pk)
                    eActaPagoPosgrado.solicitadopor = f.cleaned_data.get('persona')
                    eActaPagoPosgrado.save(request)
                    eActaPagoPosgrado.generar_pdf_acta_pago_en_tiempo_real(request,persona)
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
                return JsonResponse({"result": True, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos."})

        elif action == 'edit_integrantefirmaactapago':
            try:
                f = ActaPagoIntegrantesFirmaForm(request.POST)
                eActaPagoIntegrantesFirma = ActaPagoIntegrantesFirma.objects.get(pk=request.POST.get('id'))
                f.edit(request.POST['persona'])
                if f.is_valid():
                    eActaPagoIntegrantesFirma.ordenfirmaactapago=f.cleaned_data.get('responsabilidadfirma')
                    eActaPagoIntegrantesFirma.persona=f.cleaned_data.get('persona')
                    eActaPagoIntegrantesFirma.save(request)
                    eActaPagoIntegrantesFirma.actapagoposgrado.generar_pdf_acta_pago_en_tiempo_real(request,persona)
                    log(u"Editó eActaPagoIntegrantesFirma", request, 'edit')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'actualizar_contrato_analista_validador':
            try:
                f = ContratoDipValidadorAnalistaForm(request.POST)
                eContratoDip = ContratoDip.objects.get(pk=request.POST.get('id'))
                f.edit(request.POST['validadorgp'])
                if f.is_valid():
                    eContratoDip.validadorgp=f.cleaned_data.get('validadorgp')
                    eContratoDip.tipogrupo=f.cleaned_data.get('tipogrupo')
                    eContratoDip.tipopago=f.cleaned_data.get('tipopago')
                    eContratoDip.certificacion=f.cleaned_data.get('certificacion')
                    eContratoDip.save(request)
                    log(u"Editó contrato analista validador", request, 'edit')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Solicitud incorrecta. {ex.__str__()}"})

        elif action == 'eliminar_detalleactapago':
            try:
                eDetalleActaPago = DetalleActaPago.objects.get(pk=int(request.POST['id']))
                eDetalleActaPago.status = False
                eDetalleActaPago.save(request)
                eDetalleActaPago.actapagoposgrado.generar_pdf_acta_pago_en_tiempo_real(request,persona)
                log(f"Eliminó del acta de pago a {eDetalleActaPago.solicitudpago.contrato}", request, 'del')
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()
        elif action == 'eliminar_detalleitemactapago':
            try:
                eDetalleItemsActaPagoPosgrado = DetalleItemsActaPagoPosgrado.objects.get(pk=int(request.POST['id']))
                eDetalleItemsActaPagoPosgrado.status = False
                eDetalleItemsActaPagoPosgrado.save(request)
                eDetalleItemsActaPagoPosgrado.actapagoposgrado.generar_pdf_acta_pago_en_tiempo_real(request,persona)
                log(f"Eliminó detalle item  del acta de pago a {eDetalleItemsActaPagoPosgrado}", request, 'del')
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()

        elif action == 'eliminar_acta_pago':
            try:
                eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=int(request.POST['id']))
                eActaPagoPosgrado.status = False
                eActaPagoPosgrado.eliminar_ultimasecuencia()
                eActaPagoPosgrado.save(request)
                DetalleActaPago.objects.filter(status=True,actapagoposgrado =eActaPagoPosgrado).update(status=False)
                log(f"Eliminó acta de pago:{eActaPagoPosgrado.codigo}", request, 'del')
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()

        elif action == 'delete_integrantefirmaactapago':
            try:
                eActaPagoIntegrantesFirma = ActaPagoIntegrantesFirma.objects.get(pk=int(request.POST['id']))
                log(u'Elimino eActaPagoIntegrantesFirma: %s' % eActaPagoIntegrantesFirma, request, "del")
                eActaPagoIntegrantesFirma.status = False
                eActaPagoIntegrantesFirma.save(request)
                eActaPagoIntegrantesFirma.actapagoposgrado.generar_pdf_acta_pago_en_tiempo_real(request,persona)
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'deletesolicitudpagoposgrado':
            try:
                eSolicitudPago = SolicitudPago.objects.get(pk=int(request.POST['id']))
                log(u'Elimino SolicitudPago: %s' % eSolicitudPago, request, "del")
                eSolicitudPago.status = False
                eSolicitudPago.save(request)
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'save-marco-juridico-acta-pago':
            try:
                f = ActaPagoMarcoJuridicoForm(request.POST)
                eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk = int(request.POST.get('id',0)))
                if f.is_valid():
                    eActaPagoPosgrado.marcojuridico = f.cleaned_data['descripcion']
                    eActaPagoPosgrado.save(request)
                    eActaPagoPosgrado.generar_pdf_acta_pago_en_tiempo_real(request,persona)

                else:
                    messages.error("Error al guardar")

                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                return HttpResponseRedirect(f"/adm_solicitudpago?action=configuraractapago_personal_pago&id={eActaPagoPosgrado.pk}&info={ex.__str__()}")

        elif action == 'save-detallememo-acta-pago':
            try:
                f = ActaPagoDetalleMemoPosgradoForm(request.POST)
                eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk = int(request.POST.get('id',0)))
                if f.is_valid():
                    eActaPagoPosgrado.detallememoposgrado = f.cleaned_data['detallememoposgrado']
                    eActaPagoPosgrado.save(request)
                    eActaPagoPosgrado.generar_pdf_acta_pago_en_tiempo_real(request,persona)

                else:
                    messages.error("Error al guardar")

                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                return HttpResponseRedirect(f"/adm_solicitudpago?action=configuraractapago_memoposgrado&id={eActaPagoPosgrado.pk}&info={ex.__str__()}")

        elif action == 'save-conclusiones-acta-pago':
            try:
                f = ActaPagoConclusionesForm(request.POST)
                eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=int(request.POST.get('id', 0)))
                if f.is_valid():
                    eActaPagoPosgrado.conclusiones = f.cleaned_data['conclusion']
                    eActaPagoPosgrado.save(request)
                    eActaPagoPosgrado.generar_pdf_acta_pago_en_tiempo_real(request,persona)
                else:
                    messages.error("Error al guardar")

                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                return HttpResponseRedirect(f"/adm_solicitudpago?action=configuraractapago_personal_pago&id={eActaPagoPosgrado.pk}&info={ex.__str__()}")

        elif action == 'save-recomendaciones-acta-pago':
            try:
                f = ActaPagoRecomendacionesForm(request.POST)
                eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=int(request.POST.get('id', 0)))
                if f.is_valid():
                    eActaPagoPosgrado.recomendaciones = f.cleaned_data['descripcion']
                    eActaPagoPosgrado.save(request)
                    eActaPagoPosgrado.generar_pdf_acta_pago_en_tiempo_real(request,persona)
                else:
                    messages.error("Error al guardar")

                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                return HttpResponseRedirect(
                    f"/adm_solicitudpago?action=configuraractapago_personal_pago&id={eActaPagoPosgrado.pk}&info={ex.__str__()}")

        elif action == 'subir_manual_acta_pago':
            try:
                f = SubirArchivoForm(request.POST,request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        if newfile.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf' or ext == '.PDF':
                                newfile._name = generar_nombre("ACTA_PAGO_", newfile._name)
                            else:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, Solo archivo con extención. pdf."})

                pk = int(request.POST.get('id','0'))
                eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=pk)
                if f.is_valid():
                    if newfile:
                        LEGALIZADA = 3
                        eActaPagoPosgrado.archivo = newfile
                        eActaPagoPosgrado.save(request)
                        eActaPagoPosgrado.estado= LEGALIZADA
                        eActaPagoPosgrado.actualizar_todos_los_integrantes_a_firmado_completo(request)
                        eActaPagoPosgrado.save(request)
                        eActaPagoPosgrado.guardar_historial_acta_pago(request, persona, 'acta pago subido manual', eActaPagoPosgrado.archivo)
                        log(u"Editó documento acta pago %s" % eActaPagoPosgrado, request, 'edit')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error al editar el documento del informe de contratación. {ex.__str__()}"})

        elif action == 'subir_memorandum_dip':
            try:
                f = SubirArchivoForm(request.POST,request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        if newfile.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf' or ext == '.PDF':
                                newfile._name = generar_nombre("MEMORANDUM_DIRECCION_POSGRADO_", newfile._name)
                            else:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, Solo archivo con extención. pdf."})

                pk = int(request.POST.get('id','0'))
                eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=pk)
                if f.is_valid():
                    if newfile:
                        ENVIADO_VIP = 4
                        eActaPagoPosgrado.archivo_memo = newfile
                        eActaPagoPosgrado.save(request)
                        eActaPagoPosgrado.estado= ENVIADO_VIP
                        eActaPagoPosgrado.save(request)
                        ids_solicitudes = eActaPagoPosgrado.get_detalle_solicitudes().values_list('solicitudpago_id',flat=True)
                        eSolicitudPago = SolicitudPago.objects.filter(pk__in=ids_solicitudes).update(estadotramite=1)
                        log(u"actualizo memo dip enviado %s" % eActaPagoPosgrado, request, 'edit')
                        eActaPagoPosgrado.guardar_historial_acta_pago(request, persona,  f"Actualizo memo dip manual  {persona}", eActaPagoPosgrado.archivo_memo)
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error al editar el documento del informe de contratación. {ex.__str__()}"})

        elif action == 'solo_actualizar_memorandum_dip':
            try:
                f = SubirArchivoForm(request.POST,request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        if newfile.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf' or ext == '.PDF':
                                newfile._name = generar_nombre("MEMORANDUM_DIRECCION_POSGRADO_", newfile._name)
                            else:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, Solo archivo con extención. pdf."})

                pk = int(request.POST.get('id','0'))
                eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=pk)
                if f.is_valid():
                    if newfile:
                        eActaPagoPosgrado.archivo_memo = newfile
                        eActaPagoPosgrado.save(request)
                        log(u"actualizo memo dip %s" % eActaPagoPosgrado, request, 'edit')
                        eActaPagoPosgrado.guardar_historial_acta_pago(request, persona, f"Actualizo memo dip manual  {persona}", eActaPagoPosgrado.archivo_memo)
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error al editar el documento del informe de contratación. {ex.__str__()}"})

        elif action == 'subir_check_list_general':
            try:
                f = SubirArchivoForm(request.POST,request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        if newfile.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf' or ext == '.PDF':
                                newfile._name = generar_nombre("CHECK_LIST_GENERAL_", newfile._name)
                            else:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, Solo archivo con extención. pdf."})

                pk = int(request.POST.get('id','0'))
                eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=pk)
                if f.is_valid():
                    if newfile:
                        eActaPagoPosgrado.archivo_check_list = newfile
                        eActaPagoPosgrado.save(request)
                        log(u"actualizo archivo check list %s" % eActaPagoPosgrado, request, 'edit')
                        eActaPagoPosgrado.guardar_historial_acta_pago(request, persona,  f"Check list actualizado manualmente  {persona}", eActaPagoPosgrado.archivo_check_list)
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error al editar el documento del informe de contratación. {ex.__str__()}"})

        elif action == 'subir_acta_pago':
            try:
                f = SubirArchivoForm(request.POST,request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        if newfile.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf' or ext == '.PDF':
                                newfile._name = generar_nombre("ACTA_PAGO_", newfile._name)
                            else:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, Solo archivo con extención. pdf."})

                pk = int(request.POST.get('id','0'))
                eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=pk)
                if f.is_valid():
                    if newfile:
                        eActaPagoPosgrado.archivo = newfile
                        eActaPagoPosgrado.save(request)
                        log(u"actualizo archivo Acta pago %s" % eActaPagoPosgrado, request, 'edit')
                        eActaPagoPosgrado.guardar_historial_acta_pago(request, persona, f"Acta pago subida manualmente  {persona}", eActaPagoPosgrado.archivo)
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error al editar el documento del informe de contratación. {ex.__str__()}"})

        elif action == 'subir_memorandum_vice':
            try:
                f = SubirArchivoForm(request.POST,request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        if newfile.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf' or ext == '.PDF':
                                newfile._name = generar_nombre("actapagomanual_", newfile._name)
                            else:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, Solo archivo con extención. pdf."})

                pk = int(request.POST.get('id','0'))
                eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=pk)
                if f.is_valid():
                    if newfile:
                        ENVIADO_A_EPUNEMI = 5
                        eActaPagoPosgrado.archivo_memo_vice = newfile
                        eActaPagoPosgrado.save(request)
                        eActaPagoPosgrado.estado= ENVIADO_A_EPUNEMI
                        eActaPagoPosgrado.save(request)
                        ids_solicitudes = eActaPagoPosgrado.get_detalle_solicitudes().values_list('solicitudpago_id', flat=True)
                        eSolicitudPago = SolicitudPago.objects.filter(pk__in=ids_solicitudes).update(estadotramite=3)
                    log(u"actualizo memo dip enviado %s" % eActaPagoPosgrado, request, 'edit')
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error al editar el documento del informe de contratación. {ex.__str__()}"})

        elif action == 'solo_actualizar_memorandum_vice':
            try:
                f = SubirArchivoForm(request.POST, request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        if newfile.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf' or ext == '.PDF':
                                newfile._name = generar_nombre("actapagomanual_", newfile._name)
                            else:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, Solo archivo con extención. pdf."})

                pk = int(request.POST.get('id', '0'))
                eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=pk)
                if f.is_valid():
                    if newfile:
                        eActaPagoPosgrado.archivo_memo_vice = newfile
                        eActaPagoPosgrado.save(request)
                        log(u"actualizo memo dip %s" % eActaPagoPosgrado, request, 'edit')
                        eActaPagoPosgrado.guardar_historial_acta_pago(request, persona, f"Archivo memo actualizado  {persona}",  eActaPagoPosgrado.archivo_memo_vice)
                    return JsonResponse({"result": True})
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.",
                                         "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                transaction.rollback()
                return JsonResponse({"result": False, "mensaje": f"Error al editar el documento del informe de contratación. {ex.__str__()}"})

        elif action == 'notificar_integrantes_firmar':
            try:
                id = int(request.POST.get('id', '0'))
                if id == 0:
                    raise NameError(u"No se encontro el parametro de registro.")
                eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=id)
                eActaPagoPosgrado.notificar_orden_integrante_toca_firmar(request)
                return JsonResponse({'result': True, 'pk': eActaPagoPosgrado.pk})
            except Exception as ex:
                pass

        elif action == 'notificar_subir_facturas':
            try:
                id = int(request.POST.get('id', '0'))
                if id == 0:
                    raise NameError(u"No se encontro el parametro de registro.")
                eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=id)
                eActaPagoPosgrado.notificar_subir_factura_profesionales(request)
                return JsonResponse({'result': True, 'pk': eActaPagoPosgrado.pk})
            except Exception as ex:
                pass

        elif action == 'notificar_subir_facturas_epunemi':
            try:
                id = int(request.POST.get('id', '0'))
                if id == 0:
                    raise NameError(u"No se encontro el parametro de registro.")
                eSolicitudPago = SolicitudPago.objects.get(pk=id)
                eSolicitudPago.notificar_subir_factura(request)

                return JsonResponse({'result': True, 'pk': eSolicitudPago.pk})
            except Exception as ex:
                pass

        elif action == 'aprobar_factura_para_realizar_el_pago_epunemi':
            try:
                FACTURA_APROBADA_POR_EPUNEMI = 5
                id = int(request.POST.get('id', '0'))
                if id == 0:
                    raise NameError(u"No se encontro el parametro de registro.")
                eSolicitudPago = SolicitudPago.objects.get(pk=id)
                eSolicitudPago.estadotramitepago = FACTURA_APROBADA_POR_EPUNEMI
                eSolicitudPago.save(request)
                return JsonResponse({'result': True, 'pk': eSolicitudPago.pk})
            except Exception as ex:
                pass

        elif action == 'rechazar_factura_para_realizar_el_pago_epunemi':
            try:
                ACTUALIZAR_FACTURA = 3
                id = int(request.POST.get('id', '0'))
                obs = request.POST.get('obs', '')
                if id == 0:
                    raise NameError(u"No se encontro el parametro de registro.")
                eRequisitoSolicitudPago = RequisitoSolicitudPago.objects.get(status=True, id=id)
                eSolicitudPago = eRequisitoSolicitudPago.solicitud
                eSolicitudPago.estadotramitepago = ACTUALIZAR_FACTURA
                eSolicitudPago.notificar_rechazo_epunemi_actualizar_factura(request)
                eSolicitudPago.guardar_historial_de_rechazo_factura_por_epunemi(request,eRequisitoSolicitudPago,obs,persona)
                eSolicitudPago.save(request)
                return JsonResponse({'result': True, 'pk': eSolicitudPago.pk})
            except Exception as ex:
                pass

        elif action == 'notificar_pago_realizado_epunemi':
            try:
                hoy = datetime.now().date()
                id = int(request.POST.get('id', '0'))
                if id == 0:
                    raise NameError(u"No se encontro el parametro de registro.")
                eDetalleActaPago = DetalleActaPago.objects.get(pk=id)
                eDetalleActaPago.solicitudpago.notificar_pago_realizado(request)
                eDetalleActaPago.solicitudpago.guardar_pago_realizado(request, hoy, eDetalleActaPago.solicitudpago.fechaifin.month, eDetalleActaPago.solicitudpago.fechaifin.year, eDetalleActaPago.valortotal)
                return JsonResponse({'result': True, 'pk': eDetalleActaPago.pk})
            except Exception as ex:
                pass

        elif action == 'firmar_acta_pago_por_archivo':
            try:
                persona = request.session.get('persona')
                observacion = f'Acta de pago firmado por {persona}'
                pk = request.POST.get('id', '0')
                if pk == 0:
                    raise NameError("Parametro no encontrado")
                eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=pk)
                puede, mensaje = eActaPagoPosgrado.puede_firmar_integrante_segun_orden(persona)
                if puede:
                    integrante = eActaPagoPosgrado.get_integrante(persona)
                    firma = request.FILES.get("firma")
                    passfirma = request.POST.get('palabraclave')
                    bytes_certificado = firma.read()
                    extension_certificado = os.path.splitext(firma.name)[1][1:]


                    if eActaPagoPosgrado.persona_es_quien_firma_acta_pago_check_list(integrante.pk):
                        pdf = eActaPagoPosgrado.archivo_check_list
                        palabras = u"%s" % integrante.persona
                        x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(pdf.url, palabras.lower().title(),horizontal=True)
                        datau = JavaFirmaEc(
                            archivo_a_firmar=pdf, archivo_certificado=bytes_certificado,
                            extension_certificado=extension_certificado,
                            password_certificado=passfirma,
                            page=int(numpaginafirma), reason='', lx=x + 5, ly=y -15
                        ).sign_and_get_content_bytes()

                        documento_a_firmar = io.BytesIO()
                        documento_a_firmar.write(datau)
                        documento_a_firmar.seek(0)
                        eActaPagoPosgrado.archivo_check_list.save(f'{eActaPagoPosgrado.archivo_check_list.name.split("/")[-1].replace(".pdf", "")}_firmado.pdf', ContentFile(documento_a_firmar.read()))
                        eActaPagoPosgrado.guardar_historial_acta_pago(request, persona, f"Check list firmado por  {persona}", eActaPagoPosgrado.archivo_check_list)
                    if not eActaPagoPosgrado.acta_pago_por_legalizar():
                        eActaPagoPosgrado.generar_actualizar_acta_pago_pdf_tics(request)

                    if integrante.persona.pk == 843:
                        palabras = 'DIRECTOR/A DE TECNOLOGÍA DE LA INFORMACIÓN Y COMUNICACIONES'
                    else:
                        palabras = u"%s" % integrante.persona.nombre_titulos3y4()
                    pdf = eActaPagoPosgrado.archivo
                    x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(pdf.url, palabras)

                    datau = JavaFirmaEc(
                        archivo_a_firmar=pdf, archivo_certificado=bytes_certificado,
                        extension_certificado=extension_certificado,
                        password_certificado=passfirma,
                        page=int(numpaginafirma), reason='', lx=x + 360, ly=y -15
                    ).sign_and_get_content_bytes()

                    documento_a_firmar = io.BytesIO()
                    documento_a_firmar.write(datau)
                    documento_a_firmar.seek(0)

                    eActaPagoPosgrado.archivo.save(f'{eActaPagoPosgrado.archivo.name.split("/")[-1].replace(".pdf", "")}_firmado.pdf', ContentFile(documento_a_firmar.read()))
                    integrante.firmo =True
                    integrante.save(request)
                    if eActaPagoPosgrado.persona_es_quien_firma_acta_pago_memo(integrante.pk) and not integrante.persona.pk == 843:
                        pdf = eActaPagoPosgrado.archivo_memo
                        palabras = u"%s" % integrante
                        x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(pdf.url, palabras.lower().title())
                        datau = JavaFirmaEc(
                            archivo_a_firmar=pdf, archivo_certificado=bytes_certificado,
                            extension_certificado=extension_certificado,
                            password_certificado=passfirma,
                            page=int(numpaginafirma), reason='', lx=x + 5, ly=y + 5
                        ).sign_and_get_content_bytes()

                        documento_a_firmar = io.BytesIO()
                        documento_a_firmar.write(datau)
                        documento_a_firmar.seek(0)
                        eActaPagoPosgrado.archivo_memo.save(f'{eActaPagoPosgrado.archivo_memo.name.split("/")[-1].replace(".pdf", "")}_firmado.pdf', ContentFile(documento_a_firmar.read()))


                    eActaPagoPosgrado.guardar_historial_acta_pago(request, persona, observacion,eActaPagoPosgrado.archivo)
                    eActaPagoPosgrado.actualizar_estado_del_acta_pago(request)
                    log(u"Firmo acta de pago por honorarios profesionales", request, 'edit')
                    eActaPagoPosgrado.notificar_orden_integrante_toca_firmar(request)
                else:
                    raise NameError(f"{mensaje}")


                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s" % ex})

        elif action == 'firmar_acta_pago_por_token':
            try:
                persona = request.session.get('persona')
                observacion = f'Acta Pago firmado por {persona}'
                pk = request.POST.get('id', '0')
                if pk == 0:
                    raise NameError("Parametro no encontrado")
                eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=pk)
                puede, mensaje = eActaPagoPosgrado.puede_firmar_integrante_segun_orden(persona)
                if puede:
                    integrante = eActaPagoPosgrado.get_integrante(persona)
                    f = SubirArchivoForm(request.POST, request.FILES)
                    if f.is_valid() and request.FILES.get('archivo', None):
                        newfile = request.FILES.get('archivo')
                        if newfile:
                            if newfile.size > 6291456:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):].lower()
                                if ext == '.pdf':
                                    _name = generar_nombre(f"{eActaPagoPosgrado.codigo.__str__()}", '')
                                    _name = remover_caracteres_tildes_unicode( remover_caracteres_especiales_unicode(_name)).lower().replace(' ', '_').replace('-','_')
                                    newfile._name = generar_nombre(u"%s_" % _name, f"{_name}.pdf")

                                    eActaPagoPosgrado.archivo = newfile
                                    eActaPagoPosgrado.save(request)
                                    eActaPagoPosgrado.guardar_historial_acta_pago(request, persona,
                                                                                                observacion,
                                                                                                eActaPagoPosgrado.archivo)
                                    integrante.firmo = True
                                    integrante.save(request)
                                    eActaPagoPosgrado.actualizar_estado_del_acta_pago(request)
                                    log(u"Firmo acta de pago por honorarios profesionales por token", request, 'edit')
                                    eActaPagoPosgrado.notificar_orden_integrante_toca_firmar(request)
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivos PDF"})

                else:
                    raise NameError(f"{mensaje}")


                return JsonResponse({"result": "ok"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s" % ex})

        elif action == 'reiniciar_acta_pago':
            try:
                id = int(request.POST.get('id', '0'))
                if id == 0:
                    raise NameError(u"No se encontro el parametro de registro.")

                eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=id)
                eActaPagoPosgrado.reiniciar_acta_pago(request,persona)
                log(u'reinicio acta de pago: %s' % eActaPagoPosgrado, request, "edit")
                return JsonResponse({'result': True, 'pk':eActaPagoPosgrado.pk})
            except Exception as ex:
                pass

        elif action == 'actualizar_orden_opcional_de_requisitos_pagos':
            try:
                id = int(request.POST.get('id', '0'))
                if id == 0:
                    raise NameError(u"No se encontro el parametro de registro.")

                eGrupoRequisitoPago = GrupoRequisitoPago.objects.get(pk=id)
                eGrupoRequisitoPago.actualizar_orden_tipo_opcional_de_solicitudes_de_requisitos_de_pagos(request,persona)
                log(u'actualizo orden y tipo opcional de todos los requisitos de pago: %s' % eGrupoRequisitoPago, request, "edit")
                return JsonResponse({'result': True})
            except Exception as ex:
                pass

        elif action == 'delsolicitudpago':
            try:
                eSolicitudPago = SolicitudPago.objects.get(pk=int(request.POST['id']))
                eSolicitudPago.status = False
                eSolicitudPago.save(request)
                log(f"Eliminó solicitud de pago {eSolicitudPago}", request, 'del')
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()

        elif action == 'actualizar_requisito_analista_pago':
            try:
                with transaction.atomic():
                    hoy = datetime.now().date()
                    pk = int(request.POST.get('id', '0'))
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eRequisitoSolicitudPago = RequisitoSolicitudPago.objects.get(pk=pk)
                    form = RequisitosPagoPosgradoForm(request.POST, request.FILES)
                    form.is_valid()
                    if not form.cleaned_data['fecha_caducidad']:
                        raise NameError("Ingrese la fecha de caducidad")

                    observacion = 'requisito actualizado por el personal revisor'
                    archivo = None
                    if 'archivo' in request.FILES:

                        arch = request.FILES['archivo']
                        ext = arch.name.split('.')[-1]
                        if ext not in ['pdf','PDF','.pdf','.PDF', ]: raise NameError(f"El formato del archivo no es permitido, debe ser uno de los siguientes: '.pdf'")

                        if arch.size > 10485760: raise NameError("El tamaño del archivo excede el límite de 10MB")

                        nombre_req = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode((eRequisitoSolicitudPago.requisito.nombre.__str__()).replace(' ', '_')))
                        arch.name = generar_nombre(f'{nombre_req}', arch.name)
                        APROBADO = 2
                        RECHAZADO = 5
                        ACTUALIZAR = 8
                        hist_ = HistorialProcesoSolicitud(
                            observacion=observacion,
                            fecha_ejecucion=hoy,
                            persona_ejecucion=persona,
                            fecha_caducidad=form.cleaned_data['fecha_caducidad'],
                            requisito=eRequisitoSolicitudPago,
                            estado=APROBADO
                        )
                        hist_.archivo = arch
                        hist_.save(request)
                        eRequisitoSolicitudPago.estado = APROBADO
                        eRequisitoSolicitudPago.observacion = observacion
                        eRequisitoSolicitudPago.save(request)
                        if eRequisitoSolicitudPago.solicitud.get_detalle_acta_pago():
                            existe_registro_con_archivo = HistorialProcesoSolicitud.objects.filter(Q(requisito=eRequisitoSolicitudPago) &Q(archivo__exact='') &Q(archivo__isnull=False)).exists()
                            if not existe_registro_con_archivo:
                                eRequisitoSolicitudPago.solicitud.get_detalle_acta_pago().actapagoposgrado.generar_actualizar_check_list_pago_pdf( request)

                            eRequisitoSolicitudPagoCheckList = RequisitoSolicitudPago.objects.filter(status=True, requisito_id=16,solicitud=eRequisitoSolicitudPago.solicitud)
                            if eRequisitoSolicitudPagoCheckList.exists():
                                hist_ = HistorialProcesoSolicitud(
                                    observacion='CHECK LIST ACTUALIZADO AUTOMATICAMENTE',
                                    fecha_ejecucion=hoy,
                                    persona_ejecucion=persona,
                                    requisito=eRequisitoSolicitudPagoCheckList.first()
                                )
                                hist_.archivo = eRequisitoSolicitudPago.solicitud.generar_documento_pdf_check_list_de_pago_solicitud(request, eRequisitoSolicitudPago.solicitud.contrato.validadorgp)
                                hist_.save(request)
                        else:
                            eRequisitoSolicitudPago.solicitud.generar_documento_pdf_check_list_de_pago_solicitud(request,eRequisitoSolicitudPago.solicitud.contrato.validadorgp)
                            eRequisitoSolicitudPagoCheckList = RequisitoSolicitudPago.objects.filter(status=True, requisito_id=16,solicitud=eRequisitoSolicitudPago.solicitud)
                            if eRequisitoSolicitudPagoCheckList.exists():
                                hist_ = HistorialProcesoSolicitud(
                                    observacion='CHECK LIST ACTUALIZADO AUTOMATICAMENTE',
                                    fecha_ejecucion=hoy,
                                    persona_ejecucion=persona,
                                    requisito=eRequisitoSolicitudPagoCheckList.first()
                                )
                                hist_.archivo = eRequisitoSolicitudPago.solicitud.generar_documento_pdf_check_list_de_pago_solicitud(request, eRequisitoSolicitudPago.solicitud.contrato.validadorgp)
                                hist_.save(request)
                        return JsonResponse({"result": "ok", "error": False})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": ex.__str__()})
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'validarrequisito':
                try:
                    data['paso'] = paso = PasoSolicitudPagos.objects.get(pk=int(request.GET['id']))
                    ESTADOS_PASOS_SOLICITUD = ((1, u'APROBADO'), (4, u'RECHAZADO'))
                    ESTADOS_DOCUMENTOS = ((1, u'APROBADO'), (4, u'CORREGIR'))
                    data['estados'] = ESTADOS_PASOS_SOLICITUD
                    data['estados_documentos'] = ESTADOS_DOCUMENTOS
                    data['documentos'] = paso.requisito_paso()
                    template = get_template('adm_solicitudpago/modal/validardocumento.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": ex})

            if action == 'cargarrequisitos':
                try:
                    data['paso'] = paso = PasoSolicitudPagos.objects.get(pk=int(request.GET['id']))
                    ESTADOS_PASOS_SOLICITUD = ((1, u'APROBADO'), (4, u'RECHAZADO'))
                    ESTADOS_DOCUMENTOS = ((1, u'APROBADO'), (4, u'CORREGIR'))
                    data['estados'] = ESTADOS_PASOS_SOLICITUD
                    data['estados_documentos'] = ESTADOS_DOCUMENTOS
                    data['documentos'] = paso.requisito_paso()
                    template = get_template('adm_solicitudpago/modal/cargarrequisitos.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": ex})

            if action == 'estverificacionrequisitos':
                id, ESTADOS_PASOS_SOLICITUD, resp = request.GET['id'], (), []
                filtro = PasoSolicitudPagos.objects.get(pk=id)
                totaldocumentos = RequisitoPasoSolicitudPagos.objects.filter(status=True, paso=filtro).exists()
                totalaprobados = RequisitoPasoSolicitudPagos.objects.filter(status=True, paso=filtro, estado=1).exists()
                if RequisitoPasoSolicitudPagos.objects.filter(status=True, paso=filtro, estado=4).exists():
                    resp = [{'id': 4, 'text': 'RECHAZADO'}]
                else:
                    if totaldocumentos == totalaprobados:
                        ESTADOS_PASOS_SOLICITUD = ((1, u'APROBADO'), (4, u'RECHAZADO'))
                        resp = [{'id': cr[0], 'text': cr[1]} for cr in ESTADOS_PASOS_SOLICITUD]
                return HttpResponse(json.dumps({'state': True, 'result': resp}))

            if action == 'verhistorial':
                try:
                    data['title'] = u'Ver Historial'
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = SolicitudPago.objects.get(pk=int(id))
                    data['detalle'] = HistorialProcesoSolicitud.objects.filter(status=True, solicitud=filtro).order_by('-pk')
                    template = get_template("adm_solicitudpago/modal/verhistorial.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'verproceso':
                id = int(encrypt(request.GET['id']))
                data['filtro'] = filtro = SolicitudPago.objects.get(pk=id)
                data['title'] = 'SOLICITUD DE PAGO #{}'.format(filtro.numero)
                return render(request, 'pro_solicitudpago/verprocesosolicitud.html', data)

            elif action == 'viewhistorialrequisito':
                try:
                    id = encrypt(request.GET['id'])
                    reg = HistorialProcesoSolicitud.objects.filter(status=True,requisito_id=int(id))
                    data['lista'] = reg
                    template = get_template('th_hojavida/informacionlaboral/modal/viewhistoryrequiposgrado.html')
                    res_js = {'result':True,'data':template.render(data)}
                except Exception as ex:
                    err_ = f'Ocurrio un error: {ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}'
                    res_js = {'result':False,'mensaje':err_}
                return JsonResponse(res_js)

            elif action == 'viewinformesmen':
                try:
                    data['title'] = u'Solicitudes de Pagos'
                    request.session['viewrevisionpago'] = 2
                    estsolicitud, search, desde, hasta, filtro, url_vars = request.GET.get('estsolicitud',''), request.GET.get('search',''), request.GET.get('desde', ''), request.GET.get('hasta', ''), Q(status=True), '&action=viewinformesmen'
                    id = request.GET.get('id',None)
                    if not persona.usuario.is_superuser and not puede_realizar_accion_afirmativo(request, 'pdip.puede_ver_todas_las_solicitudes_de_pago_posgrado'):
                        filtro = filtro & Q(contrato__validadorgp=persona)

                    if estsolicitud:
                        data['estsolicitud'] = estsolicitud = int(estsolicitud)
                        url_vars += "&estsolicitud={}".format(estsolicitud)
                        filtro = filtro & Q(estado=estsolicitud)
                    # else:
                    #     filtro = filtro & (Q(estado=0) |Q(estado=3) | Q(estado=7) | Q(estado=8))

                    if desde:
                        data['desde'] = desde
                        url_vars += "&desde={}".format(desde)
                        filtro = filtro & Q(fecha_creacion__gte=desde)

                    if hasta:
                        data['hasta'] = hasta
                        url_vars += "&hasta={}".format(hasta)
                        filtro = filtro & Q(fecha_creacion__lte=hasta)

                    if search:
                        data['search'] = search
                        s = search.split()
                        if len(s) == 1:
                            filtro = filtro & (Q(contrato__persona__apellido2__icontains=search) | Q( contrato__persona__cedula__icontains=search) | Q(contrato__persona__apellido1__icontains=search))
                        else:
                            filtro = filtro & ( Q(contrato__persona__apellido1__icontains=s[0]) & Q(contrato__persona__apellido2__icontains=s[1]))
                        url_vars += '&search={}'.format(search)
                    if id:
                        filtro = filtro & Q(id=int(encrypt(id)))
                    lista_resultados = SolicitudPago.objects.filter(filtro).order_by('-id').annotate(
                            estado_order=Case(
                                When(estado=3, then=Value(1)),
                                When(estado=8, then=Value(2)),
                                When(estado=7, then=Value(3)),
                                When(estado=6, then=Value(4)),
                                When(estado=4, then=Value(5)),
                                When(estado=5, then=Value(6)),
                                When(estado=1, then=Value(7)),
                                When(estado=2, then=Value(8)),
                                default=Value(9),
                                output_field=IntegerField()
                            )
                        ).order_by('estado_order','-id')
                    existen_contratos_asignados, existen_solicitudes_para_grupo_revisor = permisos_ver_opciones_view(persona)
                    data['existen_contratos_asignados'] = existen_contratos_asignados
                    data['existen_solicitudes_para_grupo_revisor'] = existen_solicitudes_para_grupo_revisor
                    data['integrante_tiene_actas_de_pagos_asignadas'] = integrante_tiene_actas_de_pagos_asignadas(persona)

                    paging = MiPaginador(lista_resultados, 20)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
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

                    lista_resultados = page.object_list
                    if persona.pk.__str__() in variable_valor(
                            'ANALISTAS_PAGO_DEPARTAMENTO_TIC'):  # guerra gaibor -encargadapagos tics
                        listado = list(filter(lambda x: x, map(lambda x: (x, x.calcular_valor_a_pagar_pago(),
                                                                          x.tienen_aprobado_los_requisitos_por_analista_excluyendo_la_factura_y_requisitos_tics(),
                                                                          x.traer_file_firmado_colaborador().fecha_modificacion if x.traer_file_firmado_colaborador() else x.fecha_creacion),
                                                               lista_resultados)))
                    else:
                        listado = list(filter(lambda x: x, map(lambda x: (x, x.calcular_valor_a_pagar_pago(),
                                                                          x.tienen_aprobado_los_requisitos_por_analista_excluyendo_la_factura(),
                                                                          x.traer_file_firmado_colaborador().fecha_modificacion if x.traer_file_firmado_colaborador() else x.fecha_creacion),
                                                               lista_resultados)))

                        # Filtrar y ordenar los elementos con estado_order = 1
                    estado_order_1 = [x for x in listado if x[0].estado_order == 1]
                    otros = [x for x in listado if x[0].estado_order != 1]

                    estado_order_1_ordenados = sorted(estado_order_1,
                                                      key=lambda x: x[3])  # Ordenar por fecha_modificacion

                    # Combinar los elementos ordenados
                    listado_final = estado_order_1_ordenados + otros
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data["url_vars"] = url_vars
                    data['email_domain'] = EMAIL_DOMAIN
                    data['estado_solicitud'] = ESTADOS_PAGO_SOLICITUD
                    data['totcount'] = len(listado)
                    data['listado'] = listado_final

                    return render(request, 'adm_solicitudpago/viewgest.html', data)
                except Exception as ex:
                    pass

            elif action == 'viewcontratoasignados':
                try:
                    url_vars = '&action=viewcontratoasignados'
                    request.session['viewrevisionpago'] = 1
                    eContratoDip = ContratoDip.objects.filter(status=True,validadorgp=persona,fechainicio__lte=datetime.now() , fechafin__gte = datetime.now())
                    data['total'] = eContratoDip.count()
                    existen_contratos_asignados, existen_solicitudes_para_grupo_revisor = permisos_ver_opciones_view(persona)
                    data['existen_contratos_asignados'] = existen_contratos_asignados
                    data['existen_solicitudes_para_grupo_revisor'] = existen_solicitudes_para_grupo_revisor
                    data['integrante_tiene_actas_de_pagos_asignadas'] = integrante_tiene_actas_de_pagos_asignadas(persona)
                    paging = MiPaginador(eContratoDip, 20)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
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
                    data['eContratoDip'] = page.object_list

                    return render(request, 'adm_solicitudpago/revisionpago/viewcontratoasignados.html', data)
                except Exception as ex:
                    pass

            elif action == 'view_actas_pago':
                try:
                    if not (persona.usuario.is_superuser or  puede_realizar_accion_afirmativo(request, 'pdip.puede_visualizar_actas_de_pagos_posgrado')):
                        raise NameError("No tiene permisos para acceder a la gestión de actas de pago")
                    url_vars = '&action=view_actas_pago'
                    existen_contratos_asignados, existen_solicitudes_para_grupo_revisor = permisos_ver_opciones_view(persona)
                    data['existen_contratos_asignados'] = existen_contratos_asignados
                    data['existen_solicitudes_para_grupo_revisor'] = existen_solicitudes_para_grupo_revisor
                    data['integrante_tiene_actas_de_pagos_asignadas'] = integrante_tiene_actas_de_pagos_asignadas(persona)
                    filtro = Q(status=True)
                    id_estado_acta_pago = int(request.GET.get('id_estado_acta', '0'))
                    search = request.GET.get('searchinput', '')
                    request.session['viewrevisionpago'] = 3
                    if  puede_realizar_accion_afirmativo(request, 'pdip.puede_gestionar_todas_las_actas_de_pago_posgrado')  or  persona.usuario.is_superuser:
                        eActaPagoPosgrado = ActaPagoPosgrado.objects.filter(status=True)
                    else:
                        if integrante_tiene_actas_de_pagos_asignadas(persona):
                            eActaPagoPosgrado = ActaPagoPosgrado.objects.filter(status=True).filter(actapagointegrantesfirma__persona=persona,status=True)
                        else:
                            eActaPagoPosgrado = ActaPagoPosgrado.objects.none()
                    if id_estado_acta_pago != 0:
                        filtro &= Q(estado=id_estado_acta_pago)
                        data['id_estado_seleccionado'] = int(id_estado_acta_pago)
                        url_vars += "&id_estado_acta={}".format(id_estado_acta_pago)

                    if search.isdigit():
                        filtro &= Q(codigo__contains=search)
                    elif search != '':
                        filtro &= Q(codigo__contains=search)
                        url_vars += "&searchinput={}".format(search)

                    if pk := request.GET.get('pk', ''):
                        filtro &= Q(pk=pk)
                        url_vars += "&pk={}".format(pk)
                    data['total'] = eActaPagoPosgrado.filter(filtro).count()


                    paging = MiPaginador(eActaPagoPosgrado.filter(filtro), 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
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
                    data['eActaPagoPosgrados'] = page.object_list
                    data['estados_acta'] = ESTADO_ACTA_PAGO

                    return render(request, 'adm_solicitudpago/revisionpago/view_solicitudes_de_pago.html', data)
                except Exception as ex:
                    pass
            elif action == 'viewcontratossinasignar':
                try:
                    existen_contratos_asignados, existen_solicitudes_para_grupo_revisor = permisos_ver_opciones_view(persona)
                    data['existen_contratos_asignados'] = existen_contratos_asignados
                    data['existen_solicitudes_para_grupo_revisor'] = existen_solicitudes_para_grupo_revisor
                    data['integrante_tiene_actas_de_pagos_asignadas'] = integrante_tiene_actas_de_pagos_asignadas(persona)
                    eContratoDip = ContratoDip.objects.filter(status=True, validadorgp__isnull=True,fechainicio__lte=datetime.now(),fechafin__gte=datetime.now())
                    search, filtro, url_vars = request.GET.get('search', ''), Q(status=True), '&action=viewcontratossinasignar'
                    request.session['viewrevisionpago'] = 7

                    if search:
                        data['search'] = search
                        s = search.split()
                        if len(s) == 1:
                            filtro = filtro & (Q(persona__apellido2__icontains=search) | Q(
                                persona__cedula__icontains=search) | Q(
                                persona__apellido1__icontains=search))
                        else:
                            filtro = filtro & (Q(persona__apellido1__icontains=s[0]) & Q(
                                persona__apellido2__icontains=s[1]))
                        url_vars += '&search={}'.format(search)

                    paging = MiPaginador(eContratoDip.filter(filtro), 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
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
                    data['eContratoDip'] = page.object_list

                    return render(request, 'adm_solicitudpago/revisionpago/view_contratossinasignar.html', data)
                except Exception as ex:
                    pass

            elif action == 'viewpersonalvalidopago':
                try:
                    request.session['viewrevisionpago'] = 6
                    existen_contratos_asignados, existen_solicitudes_para_grupo_revisor = permisos_ver_opciones_view(persona)
                    data['existen_contratos_asignados'] = existen_contratos_asignados
                    data['existen_solicitudes_para_grupo_revisor'] = existen_solicitudes_para_grupo_revisor
                    data['integrante_tiene_actas_de_pagos_asignadas'] = integrante_tiene_actas_de_pagos_asignadas(persona)
                    id = request.GET.get('id', None)
                    search, desde, hasta, filtro, url_vars =  request.GET.get('search', ''), request.GET.get('desde', ''), request.GET.get('hasta', ''), Q(status=True,estado = 8), '&action=viewpersonalvalidopago'
                    if not persona.usuario.is_superuser and not puede_realizar_accion_afirmativo(request, 'pdip.puede_ver_todas_las_solicitudes_de_pago_posgrado'):
                        filtro = filtro & Q(contrato__validadorgp=persona)

                    if desde:
                        data['desde'] = desde
                        url_vars += "&desde={}".format(desde)
                        filtro = filtro & Q(fecha_creacion__gte=desde)

                    if hasta:
                        data['hasta'] = hasta
                        url_vars += "&hasta={}".format(hasta)
                        filtro = filtro & Q(fecha_creacion__lte=hasta)

                    if search:
                        data['search'] = search
                        s = search.split()
                        if len(s) == 1:
                            filtro = filtro & (Q(contrato__persona__apellido2__icontains=search) | Q( contrato__persona__cedula__icontains=search) | Q(contrato__persona__apellido1__icontains=search))
                        else:
                            filtro = filtro & ( Q(contrato__persona__apellido1__icontains=s[0]) & Q(contrato__persona__apellido2__icontains=s[1]))
                        url_vars += '&search={}'.format(search)

                    if id:
                        filtro = filtro & Q(id=int(id))

                    lista_resultados= SolicitudPago.objects.filter(filtro)
                    if persona.pk.__str__() in variable_valor('ANALISTAS_PAGO_DEPARTAMENTO_TIC'):  # guerra gaibor -encargadapagos tics
                        eSolicitudPagos = list(filter(lambda x: x[1], map(lambda x: (
                        x, x.tienen_aprobado_los_requisitos_por_analista_excluyendo_la_factura_y_requisitos_tics(),
                        x.calcular_valor_a_pagar_pago(), x.solicitud_esta_en_acta_de_pago(),
                        x.traer_file_firmado_colaborador().fecha_modificacion if x.traer_file_firmado_colaborador() else x.fecha_creacion),
                                                                          lista_resultados)))
                    else:
                        eSolicitudPagos = list(filter(lambda x: x[1], map(lambda x: (
                        x, x.tienen_aprobado_los_requisitos_por_analista_excluyendo_la_factura(),
                        x.calcular_valor_a_pagar_pago(), x.solicitud_esta_en_acta_de_pago(),
                        x.traer_file_firmado_colaborador().fecha_modificacion if x.traer_file_firmado_colaborador() else x.fecha_creacion),
                                                                          lista_resultados)))

                    eSolicitudPagos.sort(key=lambda x: not x[3] is False)

                    paging = MiPaginador(eSolicitudPagos, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
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
                    data['eSolicitudPagos'] = eSolicitudPagos
                    data['totcount'] = len(eSolicitudPagos) if eSolicitudPagos else 0
                    return render(request, 'adm_solicitudpago/revisionpago/view_personal_valido_de_pago.html', data)
                except Exception as ex:
                    pass

            elif action == 'firmaractapago':
                try:
                    request.session['viewrevisionpago'] = 5
                    ids_acta_pagos = ActaPagoIntegrantesFirma.objects.values_list('actapagoposgrado',flat =True).filter(status=True, persona=persona).distinct()
                    filtro = Q(status=True, estado__in =[2,3],pk__in = ids_acta_pagos)
                    data['title'] = u"Firmar actas de pagos por honorarios profesionales"
                    url_vars = f"&action={action}"
                    search = None
                    search = request.GET.get('searchinput', '')

                    if search.isdigit():
                        filtro &= Q(codigo__contains=search)
                    elif search != '':
                        filtro &= Q(codigo__contains=search)
                        url_vars += "&searchinput={}".format(search)

                    if pk := request.GET.get('pk', ''):
                        filtro &= Q(pk=pk)
                        url_vars += "&pk={}".format(pk)
                    lista_resultados = ActaPagoPosgrado.objects.filter(filtro).order_by('estado').distinct()

                    existen_contratos_asignados, existen_solicitudes_para_grupo_revisor = permisos_ver_opciones_view(persona)
                    data['existen_contratos_asignados'] = existen_contratos_asignados
                    data['existen_solicitudes_para_grupo_revisor'] = existen_solicitudes_para_grupo_revisor
                    data['integrante_tiene_actas_de_pagos_asignadas'] = integrante_tiene_actas_de_pagos_asignadas(persona)

                    eActaPagoPosgrado = list(filter(lambda x:  x[1],map(lambda x: (x,x.puede_firmar_integrante_segun_orden(persona)[0]),lista_resultados)))

                    paging = MiPaginador(eActaPagoPosgrado, 12)
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
                    data['eActaPagoPosgrado'] = page.object_list
                    data['searchinput'] = search if search else ""
                    data['url_vars'] = url_vars
                    return render(request, 'adm_solicitudpago/revisionpago/firmaractapagos.html', data)
                except Exception as ex:
                    pass

            elif action == 'facturas_a_pagar':
                try:
                    request.session['viewrevisionpago'] = 8
                    ENVIADO_A_EPUNEMI=5
                    data['title'] = u"Personal de Posgrado - Facturas"
                    estsolicitud,search, desde, hasta, filtro, url_vars = request.GET.get('estsolicitud',''), request.GET.get('search', ''), request.GET.get('desde', ''), request.GET.get('hasta', ''), Q( status=True,actapagoposgrado__estado=ENVIADO_A_EPUNEMI), '&action=facturas_a_pagar'
                    id = request.GET.get('id', None)

                    if estsolicitud:
                        data['estsolicitud'] = estsolicitud = int(estsolicitud)
                        url_vars += "&estsolicitud={}".format(estsolicitud)
                        filtro = filtro & Q(solicitudpago__estadotramitepago=estsolicitud)

                    if desde:
                        data['desde'] = desde
                        url_vars += "&desde={}".format(desde)
                        filtro = filtro & Q(solicitudpago__fecha_creacion__gte=desde)

                    if hasta:
                        data['hasta'] = hasta
                        url_vars += "&hasta={}".format(hasta)
                        filtro = filtro & Q(solicitudpago__fecha_creacion__lte=hasta)

                    if search:
                        data['search'] = search
                        s = search.split()
                        if len(s) == 1:
                            filtro = filtro & (Q(solicitudpago__contrato__persona__apellido2__icontains=search) | Q(solicitudpago__contrato__persona__cedula__icontains=search) | Q(solicitudpago__contrato__persona__apellido1__icontains=search)  | Q(solicitudpago__contrato__persona__cedula__contains=search))
                        else:
                            filtro = filtro & (Q(solicitudpago__contrato__persona__apellido1__icontains=s[0]) & Q(
                                solicitudpago__contrato__persona__apellido2__icontains=s[1]))
                        url_vars += '&search={}'.format(search)
                    if id:
                        filtro = filtro & Q(id=int(id))



                    existen_contratos_asignados, existen_solicitudes_para_grupo_revisor = permisos_ver_opciones_view(persona)
                    data['existen_contratos_asignados'] = existen_contratos_asignados
                    data['existen_solicitudes_para_grupo_revisor'] = existen_solicitudes_para_grupo_revisor
                    data['integrante_tiene_actas_de_pagos_asignadas'] = integrante_tiene_actas_de_pagos_asignadas(persona)

                    # casos_ordenamiento = [
                    #     Case(When(solicitudpago__puede_subir_factura=False, then=0), output_field=BooleanField()),
                    #     Case(When(solicitudpago__puede_subir_factura=True, then=1), output_field=BooleanField()),
                    #     Case(When(solicitudpago__pago_realizado=False, then=0), output_field=BooleanField()),
                    #     Case(When(solicitudpago__pago_realizado=True, then=1), output_field=BooleanField())
                    # ]
                    lista_resultados = DetalleActaPago.objects.filter(filtro)  # .order_by(*casos_ordenamiento)
                    paging = MiPaginador(lista_resultados, 40)
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

                    lista_resultados = page.object_list
                    eDetalleActaPagos = list(filter(lambda x: x[1],
                                                  map(lambda x: (x,
                                                                 x.solicitudpago.calcular_valor_a_pagar_pago(),
                                                                 x.solicitudpago.get_factura(),
                                                                 x.solicitudpago.fechasubidafactura,
                                                                 ),lista_resultados)))

                    # Ordenar la lista con una función personalizada
                    eDetalleActaPagos_ordenados = sorted(eDetalleActaPagos, key=lambda x: bool(x[2]), reverse=True)
                    eDetalleActaPagos_ordenados = sorted(eDetalleActaPagos_ordenados, key=lambda x: (not x[3], x[3]))
                    # Obtener solo los objetos ordenados
                    resultados_ordenados = list(map(lambda x: x, eDetalleActaPagos_ordenados))

                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['eDetalleActaPagos'] = resultados_ordenados
                    data['searchinput'] = search if search else ""
                    data['url_vars'] = url_vars
                    data['total'] = len(resultados_ordenados)
                    data['estado_solicitud'] = ESTADOS_TRAMITE_PAGO
                    return render(request, 'adm_solicitudpago/epunemi/view.html', data)
                except Exception as ex:
                    pass


            elif action == 'viewrevisionsolicitudpago':
                try:
                    pk = int(request.GET.get('id','0'))
                    resultado = SolicitudPago.objects.filter(status=True,contrato_id = pk)
                    eSolicitudPagos = list(filter(lambda x: x, map(lambda x: (x, x.calcular_valor_a_pagar_pago()),resultado)))
                    paging = MiPaginador(eSolicitudPagos, 20)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
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
                    data['eSolicitudPago'] = page.object_list
                    data['totcount'] = len(eSolicitudPagos)
                    return render(request, 'adm_solicitudpago/revisionpago/viewrevsolicitudpago.html', data)
                except Exception as ex:
                    pass

            elif action == 'viewrevisionrequisitossolicitudpago':
                try:
                    INFORME_ACTIVIDAD = 14
                    CHECK_LIST_DE_PAGO = 16
                    FACTURA = 4
                    FORMATO_DE_PROVEEDORES = 6
                    RELACION_DEPENDENCIA_LABORAL = 20
                    IMPEDIMENTO_PARA_EJERCER_CARGO_PUBLICO = 19
                    pk = int(request.GET.get('id','0'))
                    tipo = int(request.GET.get('tipo','0'))
                    data['tipo']= tipo

                    url_vars = f'&action=viewrevisionrequisitossolicitudpago&&id={pk}'
                    eSolicitudPago = SolicitudPago.objects.get(id= pk)
                    if persona.pk.__str__()  in variable_valor('ANALISTAS_PAGO_DEPARTAMENTO_TIC'):  # guerra gaibor -encargadapagos tics
                        eRequisitoSolicitudPago = eSolicitudPago.traer_pasos_solicitud().order_by('orden').exclude(requisito_id__in =(CHECK_LIST_DE_PAGO,IMPEDIMENTO_PARA_EJERCER_CARGO_PUBLICO,RELACION_DEPENDENCIA_LABORAL,))
                    else:
                        eRequisitoSolicitudPago = eSolicitudPago.traer_pasos_solicitud().order_by('orden').exclude(requisito_id__in =(CHECK_LIST_DE_PAGO,))
                    data['eSolicitudPago'] = eSolicitudPago

                    paging = MiPaginador(eRequisitoSolicitudPago, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
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
                    data['eRequisitosPagos'] = page.object_list
                    return render(request, 'adm_solicitudpago/revisionpago/viewrevrequisitopago.html', data)
                except Exception as ex:
                    pass

            elif action == 'generar_acta_pago':
                try:
                    ids = request.GET.getlist('ids[]')
                    eSolicitudPagos = SolicitudPago.objects.filter(status=True, pk__in =ids)
                    data['eSolicitudPagos'] = eSolicitudPagos
                    data['ids'] = ids

                    data['subieron_todos_sus_requisitos_de_pago'] =subieron_todos_sus_requisitos_de_pago = validacion_todas_las_solicitudes_subieron_los_requisitos_de_pago_excluyendo_la_factura(eSolicitudPagos)
                    data['todos_tienen_aprobado_sus_requisitos_de_pago'] =todos_tienen_aprobado_sus_requisitos_de_pago = validacion_todas_las_solicitudes_tienen_aprobado_los_requisitos_por_analista_excluyendo_la_factura(eSolicitudPagos)
                    #data['todos_son_administrativos'] = todos_son_administrativos = validacion_todas_las_solicitudes_son_tipo_administrativo(eSolicitudPagos)
                    #data['solicitudes_son_del_mismo_mes'] =solicitudes_son_del_mismo_mes =validacion_todas_las_solicitudes_son_del_mismo_mes(eSolicitudPagos)
                    data['puede_generar_acta_de_pago'] = True if subieron_todos_sus_requisitos_de_pago and todos_tienen_aprobado_sus_requisitos_de_pago else False
                    template = get_template('adm_solicitudpago/revisionpago/modal/form_generar_acta_pago.html')
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})

                    return render(request, '', data)
                except Exception as ex:
                    pass

            elif action == 'loadhisotryobser':
                try:
                    id = request.GET.get('id', None)
                    hsitobs = HistorialObseracionSolicitudPago.objects.filter(status=True, solicitud_id = int(encrypt(id)))
                    data['listado'] = hsitobs
                    template = get_template('pro_solicitudpago/modal/viewhistoryobservacion.html')
                    res_js = {'result': True, 'data': template.render(data)}
                except Exception as ex:
                    err_ = f'Ocurrio un error: {ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}'
                    res_js = {'result': False, 'mensaje': err_}
                return JsonResponse(res_js)

            elif action == 'reviewactivities':
                try:
                    id = request.GET.get('id')
                    solicitud = SolicitudPago.objects.get(status=True, id=int(encrypt(id)))
                    fil_bitacora = Q(fecha__date__gte=solicitud.fechainicio.date(), fecha__date__lte=solicitud.fechaifin.date(), persona=solicitud.contrato.persona, status=True)
                    fecha_actual = solicitud.fechainicio
                    data['fechas'] = [fecha_actual + timedelta(days=d) for d in range((solicitud.fechaifin - solicitud.fechainicio).days + 1)]
                    actividades = BitacoraActividadDiaria.objects.filter(fil_bitacora).order_by('fecha')
                    data['title'] = f'Revisión de actividades intividuales - {solicitud.contrato.persona}'
                    data['soli'] = solicitud
                    data['actividades'] = actividades
                    return render(request,'adm_solicitudpago/viewactivities.html', data)
                except Exception as ex:
                    msg_err = f'{ex} ({sys.exc_info()[-1].tb_lineno})'
                    return HttpResponseRedirect(f'{request.path}?info={msg_err}')

            elif action == 'configuraractapago':
                try:
                    data['title'] = u'Configurar Acta Pago'
                    request.session['viewrevisionpago'] = 3
                    request.session['viewrevisionpago_configuracion_Acta'] = 'datos_generales'
                    eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=request.GET.get('id'))
                    data['eActaPagoPosgrado'] = eActaPagoPosgrado
                    existen_contratos_asignados, existen_solicitudes_para_grupo_revisor = permisos_ver_opciones_view(persona)
                    data['existen_contratos_asignados'] = existen_contratos_asignados
                    data['existen_solicitudes_para_grupo_revisor'] = existen_solicitudes_para_grupo_revisor
                    data['integrante_tiene_actas_de_pagos_asignadas'] = integrante_tiene_actas_de_pagos_asignadas(persona)

                    return render(request, "adm_solicitudpago/revisionpago/view_conf_acta_pago.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/adm_solicitudpago?action=view_actas_pago&info=%s" % ex.__str__())

            elif action == 'configuraractapago_personal_pago':
                try:
                    data['title'] = u'Configurar Acta Pago'
                    request.session['viewrevisionpago'] = 3
                    request.session['viewrevisionpago_configuracion_Acta'] = 'personal_pago'
                    eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=request.GET.get('id'))
                    eActaPagoMarcoJuridicoForm = ActaPagoMarcoJuridicoForm()
                    eActaPagoMarcoJuridicoForm.fields['descripcion'].initial = eActaPagoPosgrado.marcojuridico
                    data['eActaPagoPosgrado'] = eActaPagoPosgrado
                    data['ActaPagoMarcoJuridicoForm'] = eActaPagoMarcoJuridicoForm
                    CERTIFICACION_BANCARIA=5
                    FORMATO_DE_PROVEEDORES=6
                    CERTIFICACION_PRESUPUESTARIA = 15
                    CHECK_LIST_DE_PAGO =16
                    data['requisitos_cantidad_hoja_1'] = lista_requisitos = [CERTIFICACION_BANCARIA,FORMATO_DE_PROVEEDORES,CERTIFICACION_PRESUPUESTARIA,CHECK_LIST_DE_PAGO]
                    existen_contratos_asignados, existen_solicitudes_para_grupo_revisor = permisos_ver_opciones_view(persona)
                    data['existen_contratos_asignados'] = existen_contratos_asignados
                    data['existen_solicitudes_para_grupo_revisor'] = existen_solicitudes_para_grupo_revisor
                    data['integrante_tiene_actas_de_pagos_asignadas'] = integrante_tiene_actas_de_pagos_asignadas(persona)
                    return render(request, "adm_solicitudpago/revisionpago/configuracionactapago/conf_acta_pago_personal_pago.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/adm_solicitudpago?action=view_actas_pago&info=%s" % ex.__str__())

            elif action == 'edit_rmu_iva_acta_pago':
                try:
                    pk = request.GET.get('id', None)
                    eDetalleActaPago = DetalleActaPago.objects.get(pk=pk)
                    form = DetalleActaPagoValoresForm(initial={
                        'rmu':eDetalleActaPago.rmu,
                        'valorIva':eDetalleActaPago.valoriva,
                        'valorTotal':eDetalleActaPago.valortotal
                    })
                    data['form2'] = form
                    data['id'] = pk
                    template = get_template('adm_solicitudpago/revisionpago/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
            elif action == 'edit_documentacion_de_soporte_acta_pago':
                try:
                    pk = request.GET.get('id', None)
                    eDetalleItemsActaPagoPosgrado = DetalleItemsActaPagoPosgrado.objects.get(pk=pk)
                    form = DetalleItemsActaPagoPosgradoForm(initial={
                        'detallecontrato':eDetalleItemsActaPagoPosgrado.detallecontrato,
                        'documentohabilitante':eDetalleItemsActaPagoPosgrado.documentohabilitante,
                        'observacion':eDetalleItemsActaPagoPosgrado.observacion
                    })
                    data['form2'] = form
                    data['id'] = pk
                    template = get_template('adm_solicitudpago/revisionpago/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
            elif action == 'add_documentacion_de_soporte_acta_pago':
                try:
                    pk = request.GET.get('id', None)
                    form = DetalleItemsActaPagoPosgradoForm()
                    data['form2'] = form
                    data['id'] = pk
                    template = get_template('adm_solicitudpago/revisionpago/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'configuraractapago_conclusiones_recomendaciones':
                try:
                    data['title'] = u'Configurar Acta Pago'
                    request.session['viewrevisionpago'] = 3
                    request.session['viewrevisionpago_configuracion_Acta'] = 'conclusiones_recomendaciones'
                    eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=request.GET.get('id'))
                    data['eActaPagoPosgrado'] = eActaPagoPosgrado
                    eActaPagoConclusionesForm = ActaPagoConclusionesForm()
                    eActaPagoRecomendacionesForm = ActaPagoRecomendacionesForm()
                    eActaPagoConclusionesForm.fields['conclusion'].initial = eActaPagoPosgrado.conclusiones
                    eActaPagoRecomendacionesForm.fields['descripcion'].initial = eActaPagoPosgrado.recomendaciones

                    data['ActaPagoConclusionesForm'] = eActaPagoConclusionesForm
                    data['ActaPagoRecomendacionesForm'] = eActaPagoRecomendacionesForm
                    existen_contratos_asignados, existen_solicitudes_para_grupo_revisor = permisos_ver_opciones_view(persona)
                    data['existen_contratos_asignados'] = existen_contratos_asignados
                    data['existen_solicitudes_para_grupo_revisor'] = existen_solicitudes_para_grupo_revisor
                    data['integrante_tiene_actas_de_pagos_asignadas'] = integrante_tiene_actas_de_pagos_asignadas(persona)

                    return render(request, "adm_solicitudpago/revisionpago/configuracionactapago/conf_acta_pago_conclusion_recomendaciones.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/adm_solicitudpago?action=view_actas_pago&info=%s" % ex.__str__())

            elif action == 'configuraractapago_generar_pdf':
                try:
                    data['title'] = u'Configurar Acta Pago'
                    request.session['viewrevisionpago'] = 3
                    request.session['viewrevisionpago_configuracion_Acta'] = 'generar_pdf'
                    eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=request.GET.get('id'))
                    data['eActaPagoPosgrado'] = eActaPagoPosgrado
                    eActaPagoConclusionesForm = ActaPagoConclusionesForm()
                    eActaPagoRecomendacionesForm = ActaPagoRecomendacionesForm()
                    eActaPagoConclusionesForm.fields['conclusion'].initial = eActaPagoPosgrado.conclusiones
                    eActaPagoRecomendacionesForm.fields['descripcion'].initial = eActaPagoPosgrado.recomendaciones

                    data['ActaPagoConclusionesForm'] = eActaPagoConclusionesForm
                    data['ActaPagoRecomendacionesForm'] = eActaPagoRecomendacionesForm
                    existen_contratos_asignados, existen_solicitudes_para_grupo_revisor = permisos_ver_opciones_view(persona)
                    data['existen_contratos_asignados'] = existen_contratos_asignados
                    data['existen_solicitudes_para_grupo_revisor'] = existen_solicitudes_para_grupo_revisor
                    data['integrante_tiene_actas_de_pagos_asignadas'] = integrante_tiene_actas_de_pagos_asignadas(persona)


                    return render(request, "adm_solicitudpago/revisionpago/configuracionactapago/conf_acta_pago_generar_pdf.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/adm_solicitudpago?action=view_actas_pago&info=%s" % ex.__str__())

            elif action == 'configuraractapago_memoposgrado':
                try:
                    data['title'] = u'Configurar Acta Pago'
                    request.session['viewrevisionpago'] = 3
                    request.session['viewrevisionpago_configuracion_Acta'] = 'configurar_memo_posgrado'
                    eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=request.GET.get('id'))
                    data['fechaemision'] = eActaPagoPosgrado.convertir_fecha_a_fecha_letra(eActaPagoPosgrado.fechaemision)
                    data['eActaPagoPosgrado'] = eActaPagoPosgrado
                    eActaPagoDetalleMemoPosgradoForm = ActaPagoDetalleMemoPosgradoForm()
                    eActaPagoDetalleMemoPosgradoForm.fields['detallememoposgrado'].initial = eActaPagoPosgrado.detallememoposgrado
                    data['eActaPagoDetalleMemoPosgradoForm'] = eActaPagoDetalleMemoPosgradoForm
                    existen_contratos_asignados, existen_solicitudes_para_grupo_revisor = permisos_ver_opciones_view(persona)
                    data['existen_contratos_asignados'] = existen_contratos_asignados
                    data['existen_solicitudes_para_grupo_revisor'] = existen_solicitudes_para_grupo_revisor
                    data['integrante_tiene_actas_de_pagos_asignadas'] = integrante_tiene_actas_de_pagos_asignadas(persona)
                    return render(request, "adm_solicitudpago/revisionpago/configuracionactapago/conf_acta_pago_memorandum.html", data)
                except Exception as ex:
                    return HttpResponseRedirect("/adm_solicitudpago?action=view_actas_pago&info=%s" % ex.__str__())

            elif action == 'integrantes_firman_acta_pago':
                try:
                    data['title'] = u'Integrantes firman Informe de contratación'
                    eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=request.GET.get('id'))
                    data['eActaPagoPosgrado'] = eActaPagoPosgrado
                    return render(request, "adm_solicitudpago/revisionpago/integrantesfirmaactapago.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit_integrantefirmaactapago':
                try:
                    eActaPagoIntegrantesFirma = ActaPagoIntegrantesFirma.objects.get(pk=request.GET.get('id'))

                    f = ActaPagoIntegrantesFirmaForm(initial={
                        'responsabilidadfirma': eActaPagoIntegrantesFirma.ordenfirmaactapago,
                        'persona': eActaPagoIntegrantesFirma.persona
                    })
                    f.edit(eActaPagoIntegrantesFirma.persona.pk)

                    data['form2'] = f
                    data['id'] = eActaPagoIntegrantesFirma.pk
                    template = get_template('adm_solicitudpago/modal/form_modal.html')

                    return JsonResponse({"result": True, 'data': template.render(data)})

                except Exception as ex:
                    pass

            elif action == 'actualizar_contrato_analista_validador':
                try:
                    eContratoDip = ContratoDip.objects.get(pk=request.GET.get('id'))

                    f = ContratoDipValidadorAnalistaForm(initial=model_to_dict(eContratoDip))
                    data['form2'] = f
                    data['filtro'] = eContratoDip
                    data['id'] = eContratoDip.pk
                    template = get_template('adm_solicitudpago/modal/form_modal.html')

                    return JsonResponse({"result": True, 'data': template.render(data)})

                except Exception as ex:
                    pass

            elif action == 'add_integrantefirmaactapago':
                try:
                    f = ActaPagoIntegrantesFirmaForm()
                    data['form2'] = f
                    data['id'] = int(request.GET.get('id', '0'))
                    template = get_template('adm_solicitudpago/modal/form_modal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editsolicitadoporactapago':
                try:
                    pk = request.GET.get('id', None)
                    eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=pk)
                    form = PersonaActaPagoForm(initial={
                        'persona':eActaPagoPosgrado.solicitadopor
                    })
                    data["id"] = eActaPagoPosgrado.pk
                    data['form2'] = form
                    template = get_template('adm_solicitudpago/modal/form_modal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'buscarpersona':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    filtro = Q(usuario__isnull=False,status=True)
                    if len(s) == 1:
                        filtro &= ((Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(cedula__icontains=q) | Q(apellido2__icontains=q) | Q(cedula__contains=q)))
                    elif len(s) == 2:
                        filtro &= ((Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) |
                                   (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1])) |
                                   (Q(nombres__icontains=s[0]) & Q(apellido1__contains=s[1])))
                    else:
                        filtro &= ((Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(apellido2__contains=s[2])) |
                                   (Q(nombres__contains=s[0]) & Q(nombres__contains=s[1]) & Q(apellido1__contains=s[2])))

                    per = Persona.objects.filter(filtro).exclude(cedula='').order_by('apellido1', 'apellido2', 'nombres').distinct()[:15]
                    return JsonResponse({"result": "ok", "results": [{"id": x.id, "name": "%s %s" % (f"<img src='{x.get_foto()}' width='25' height='25' style='border-radius: 20%;' alt='...'>", x.nombre_completo_inverso())} for x in per]})
                except Exception as ex:
                    pass

            elif action == 'buscaradministrativo':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if len(s) == 1:
                        personas = Administrativo.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                      | Q(persona__apellido2__icontains=s[0])
                                                      | Q(persona__cedula__icontains=s[0])
                                                      | Q(persona__pasaporte__icontains=s[0])
                                                      | Q(persona__ruc__icontains=s[0]),
                                                      status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    else:
                        personas = Administrativo.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                               & Q(persona__apellido2__icontains=s[1]),
                                                           status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso())} for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'generaractapago':
                try:
                    eActaPagoPosgrado = ActaPagoPosgrado.objects.filter(pk=request.GET.get('id', None)).first()
                    if persona.pk.__str__()  in  variable_valor('ANALISTAS_PAGO_DEPARTAMENTO_TIC'):  # guerra gaibor -encargadapagos tics
                        url_check = eActaPagoPosgrado.generar_actualizar_check_list_pago_pdf_tics(request)
                        url = eActaPagoPosgrado.generar_actualizar_acta_pago_pdf_tics(request)
                        url_memo = eActaPagoPosgrado.generar_actualizar_memo_pago_pdf(request)
                    else:
                        eActaPagoPosgrado.actualizar_codigos_acta_pago_and_memo(request)
                        url_check = eActaPagoPosgrado.generar_actualizar_check_list_pago_pdf(request)
                        url = eActaPagoPosgrado.generar_actualizar_acta_pago_pdf(request)
                        url_memo = eActaPagoPosgrado.generar_actualizar_memo_pago_pdf(request)
                    return JsonResponse({'result': True})


                except Exception as ex:
                    return JsonResponse({'result':False, 'mensaje': u"%s" % ex.__str__()})

            elif action == 'historial_acta_pago':
                try:
                    pk = int(request.GET.get('id', '0'))
                    if not pk:
                        raise NameError("Parametro no encontrado")

                    eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk = pk)

                    data['eActaPagoPosgrado'] = eActaPagoPosgrado
                    template = get_template('adm_solicitudpago/revisionpago/modal/historial_acta_pago.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'subir_check_list_general':
                try:
                    data['form2'] = SubirArchivoForm()
                    pk = int(request.GET.get('id', '0'))
                    data['id'] = pk
                    template = get_template("adm_solicitudpago/modal/form_modal.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    print(ex)
                    print(sys.exc_info()[-1].tb_lineno)
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})

            elif action == 'subir_acta_pago':
                try:
                    data['form2'] = SubirArchivoForm()
                    pk = int(request.GET.get('id', '0'))
                    data['id'] = pk
                    template = get_template("adm_solicitudpago/modal/form_modal.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    print(ex)
                    print(sys.exc_info()[-1].tb_lineno)
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})

            elif action == 'subir_memorandum_dip':
                try:
                    data['form2'] = SubirArchivoForm()
                    pk = int(request.GET.get('id', '0'))
                    data['id'] = pk
                    template = get_template("adm_solicitudpago/modal/form_modal.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    print(ex)
                    print(sys.exc_info()[-1].tb_lineno)
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})

            elif action == 'solo_actualizar_memorandum_dip':
                try:
                    data['form2'] = SubirArchivoForm()
                    pk = int(request.GET.get('id', '0'))
                    data['id'] = pk
                    template = get_template("adm_solicitudpago/modal/form_modal.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    print(ex)
                    print(sys.exc_info()[-1].tb_lineno)
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})

            elif action == 'subir_memorandum_vice':
                try:
                    data['form2'] = SubirArchivoForm()
                    pk = int(request.GET.get('id', '0'))
                    data['id'] = pk
                    template = get_template("adm_solicitudpago/modal/form_modal.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    print(ex)
                    print(sys.exc_info()[-1].tb_lineno)
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})

            elif action == 'solo_actualizar_memorandum_vice':
                try:
                    data['form2'] = SubirArchivoForm()
                    pk = int(request.GET.get('id', '0'))
                    data['id'] = pk
                    template = get_template("adm_solicitudpago/modal/form_modal.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    print(ex)
                    print(sys.exc_info()[-1].tb_lineno)
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})

            elif action == 'subir_manual_acta_pago':
                try:
                    f = SubirArchivoActaPagoForm()
                    data['form2'] = f
                    data['id'] = request.GET.get('id','0')
                    template = get_template("adm_solicitudpago/modal/form_modal.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    print(ex)
                    print(sys.exc_info()[-1].tb_lineno)
                    return JsonResponse({"result": False, "mensaje": f"Lo sentimos, {ex.__str__()}"})

            elif action == 'verificar_turno_para_firmar':
                try:
                    pk = request.GET.get('id','0')
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=pk)
                    puede, mensaje = eActaPagoPosgrado.puede_firmar_integrante_segun_orden(persona)
                    return JsonResponse({"result": True, "puede":puede,"mensaje":mensaje})
                except Exception as ex:
                    pass

            elif action == 'firmar_acta_pago_por_token':
                try:
                    eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=request.GET['id'])
                    data['form2'] = SubirArchivoForm()
                    template = get_template('adm_solicitudpago/modal/form_modal.html')
                    data['id'] = eActaPagoPosgrado.pk
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'firmar_acta_pago_por_archivo':
                try:
                    eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=request.GET['id'])
                    f = FirmaElectronicaIndividualForm()
                    data['id'] = eActaPagoPosgrado.pk
                    template = get_template("adm_solicitudpago/modal/firmardocumento.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'firma_masiva_acta_pago_posgrado':
                try:
                    ids = request.GET.getlist('ids[]')
                    data['ids'] = ids
                    f = FirmaElectronicaIndividualForm()
                    template = get_template("adm_solicitudpago/modal/firmardocumento.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'actualizar_requisito_analista_pago':
                try:
                    pk = int(request.GET.get('id', '0'))
                    eRequisitoSolicitudPago = RequisitoSolicitudPago.objects.get(pk=pk)
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    form = RequisitosPagoPosgradoForm()
                    data['form2'] = form
                    data['id'] = eRequisitoSolicitudPago.pk
                    template = get_template('adm_solicitudpago/revisionpago/modal/modalrequisito.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
            elif action == 'descarga_masiva_documentos':
                try:
                    id = request.GET.get('id', 0)
                    if id == 0: raise NameError("Parametro no encontrado")
                    eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=id)
                    response =eActaPagoPosgrado.descargar_requisitos_todos(request)
                    if response:
                        return response
                    else:
                        raise NameError("Error ,.rar")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            elif action == 'descarga_individual_documentos':
                    try:
                        id = request.GET.get('id', 0)
                        if id == 0: raise NameError("Parametro no encontrado")
                        eSolicitudPago = SolicitudPago.objects.get(pk=id)
                        response = eSolicitudPago.descargar_requisitos(request)
                        if response:
                            return response
                        else:
                            raise NameError("Error ,.rar")

                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)
            elif action == 'historial_de_pago_contrato_posgrado':
                id = request.GET.get('id',0)
                eContratoDip = ContratoDip.objects.get(pk=id)
                data['estructura'] = eContratoDip.estructura_de_pagos_contrato()

                template = get_template('adm_contratodip/modal/modal_pagos_contrato.html')
                return JsonResponse({"result": True, 'data': template.render(data)})

        else:
            try:
                data['title'] = u'Solicitudes de Pagos'
                request.session['viewrevisionpago'] = 4
                estsolicitud, search, desde, hasta, filtro, url_vars = request.GET.get('estsolicitud', ''), request.GET.get('search', ''), request.GET.get('desde', ''), request.GET.get('hasta', ''), Q(status=True,contrato__gestion__responsable=persona), ''
                LISTA_ESTADO = [6]
                gruporevision = ContratoDip.objects.values_list('persona_id', flat=True).filter(status=True,validadorgp=persona).exists()
                data['gruporevision'] = gruporevision

                if estsolicitud:
                    data['estsolicitud'] = estsolicitud = int(estsolicitud)
                    url_vars += "&estsolicitud={}".format(estsolicitud)
                    LISTA_ESTADO.append(estsolicitud)

                if desde:
                    data['desde'] = desde
                    url_vars += "&desde={}".format(desde)
                    filtro = filtro & Q(fecha_creacion__gte=desde)

                if hasta:
                    data['hasta'] = hasta
                    url_vars += "&hasta={}".format(hasta)
                    filtro = filtro & Q(fecha_creacion__lte=hasta)

                if search:
                    data['search'] = search
                    s = search.split()
                    if len(s) == 1:
                        filtro = filtro & (Q(contrato__persona__apellido2__icontains=search) | Q(contrato__persona__cedula__icontains=search) | Q(contrato__persona__apellido1__icontains=search))
                    else:
                        filtro = filtro & (Q(contrato__persona__apellido1__icontains=s[0]) & Q(contrato__persona__apellido2__icontains=s[1]))
                    url_vars += '&search={}'.format(search)

                lista_resultados = SolicitudPago.objects.filter(filtro).order_by('-id').filter(estado__in= LISTA_ESTADO)

                existen_contratos_asignados, existen_solicitudes_para_grupo_revisor = permisos_ver_opciones_view(persona)
                data['existen_contratos_asignados'] = existen_contratos_asignados
                data['existen_solicitudes_para_grupo_revisor'] = existen_solicitudes_para_grupo_revisor
                data['integrante_tiene_actas_de_pagos_asignadas'] = integrante_tiene_actas_de_pagos_asignadas(persona)
                listado = list(filter(lambda x: x, map(lambda x: (x, x.calcular_valor_a_pagar_pago(),x.tienen_aprobado_los_requisitos_por_analista_excluyendo_la_factura()),lista_resultados)))
                paging = MiPaginador(listado, 20)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session:
                        paginasesion = int(request.session['paginador'])
                    if 'page' in request.GET:
                        p = int(request.GET['page'])
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
                data['listado'] = page.object_list
                data['totcount'] = len(listado)
                data['email_domain'] = EMAIL_DOMAIN
                data['estado_solicitud'] = ESTADOS_PAGO_SOLICITUD


                return render(request, 'adm_solicitudpago/view.html', data)
            except Exception as ex:
                print(ex)
                print(sys.exc_info()[-1].tb_lineno)
