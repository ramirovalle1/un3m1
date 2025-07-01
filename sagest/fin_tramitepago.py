# -*- coding: UTF-8 -*-
import json
from datetime import *
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http.response import HttpResponseRedirect
from django.shortcuts import render
from django.http import JsonResponse
from django.template import Context
from django.template.loader import get_template
from decorators import last_access, secure_module
from sagest.commonviews import secuencia_egreso
from sagest.forms import TramitePagoForm, DocumentoTramiteForm, BeneficiariosForm, RetencionesDocumentoTramitePagoForm, \
    DocumentoXmlTramiteForm, CertificacionTramiteForm, DocumentoPdfTramiteForm, ComprobanteEgresoForm, \
    TraspasoTramiteForm, RechazoTramiteForm
from sagest.models import TramitePago, RecorridoTramite, DocumentosTramitePago, DetalleDocumentoPago, \
    BeneficiariTramitePago, CodigoRetencion, \
    RetencionesDocumentoTramitePago, Departamento, ComprobanteEgreso, CertificacionPartida, CertificacionTramitePago, \
    AccionesTramitePago, null_to_decimal, DistributivoPersona
from settings import TIPO_TRAMITE_PAGO_ROL, BENEFICIARIO_UNEMI
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import log, generar_nombre, variable_valor, MiPaginador
from sga.models import miinstitucion, CUENTAS_CORREOS
from sga.tasks import send_html_mail, conectar_cuenta


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = TramitePagoForm(request.POST)
                if f.is_valid():
                    secuencia = secuencia_egreso(request)
                    secuencia.tramitepago += 1
                    secuencia.save(request)
                    tipo = f.cleaned_data['tipotramite']
                    tramite = TramitePago(tipotramite=tipo,
                                          fechainicio=datetime.now().date(),
                                          numero=secuencia.tramitepago,
                                          origen=persona.mi_departamento(),
                                          responsable=persona,
                                          motivo=f.cleaned_data['motivo'],
                                          valortotal=f.cleaned_data['valortotal'])
                    tramite.save(request)
                    if tipo.aprobadorectorado:
                        tramite.aprobadorectorado = True
                        tramite.fechaaprobador = datetime.now().date()
                        tramite.save(request)
                    if tipo.aprobadofinanciero:
                        tramite.aprobadofinanciero = True
                        tramite.fechaaprobadof = datetime.now().date()
                        tramite.save(request)
                    recorrido = RecorridoTramite(tramitepago=tramite,
                                                 departamento=persona.mi_departamento(),
                                                 estado=tramite.estado,
                                                 fecharecibido=datetime.now(),
                                                 accion_id=1)
                    recorrido.save(request)
                    if tipo.id == TIPO_TRAMITE_PAGO_ROL:
                        beneficiairo = BeneficiariTramitePago(tramitepago=tramite,
                                                              beneficiario_id=BENEFICIARIO_UNEMI,
                                                              valor=Decimal(f.cleaned_data['valortotal']))
                        beneficiairo.save(request)
                    log(u'Adiciono nuevo tramite: %s' % tramite, request, "add")
                    return JsonResponse({"result": "ok", 'id': tramite.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'subir':
            try:
                form = DocumentoTramiteForm(request.POST, request.FILES)
                if form.is_valid():
                    documento = DocumentosTramitePago.objects.get(pk=int(request.POST['id']))
                    if 'archivo' in request.FILES:
                        nfile = request.FILES['archivo']
                        nfile._name = generar_nombre("documentotramite_", nfile._name)
                        documento.archivo = nfile
                        documento.save(request)
                        log(u'Modifico archivo de documento: %s' % documento, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"No escoje archivo."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"El archivo no tiene el formato correcto."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'subirxml':
            try:
                form = DocumentoXmlTramiteForm(request.POST, request.FILES)
                if form.is_valid():
                    documento = DocumentosTramitePago.objects.get(pk=int(request.POST['id']))
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("documentoxmltramite_", nfile._name)
                    documentoretencion = documento.retencion()
                    documentoretencion.archivoxml = nfile
                    documentoretencion.numero = form.cleaned_data['numero']
                    documentoretencion.save(request)
                    log(u'Subió XML de retencion: %s' % documentoretencion, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"El archivo no tiene el formato correcto."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'subirpdf':
            try:
                form = DocumentoPdfTramiteForm(request.POST, request.FILES)
                if form.is_valid():
                    documento = DocumentosTramitePago.objects.get(pk=int(request.POST['id']))
                    documentoretencion = documento.retencion()
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("documentopdftramite_", nfile._name)
                    documentoretencion.archivopdf = nfile
                    documentoretencion.save(request)
                    log(u'Subió PDF de retencion: %s' % documentoretencion, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"El archivo no tiene el formato correcto."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'adddocumentos':
            try:
                f = DocumentoTramiteForm(request.POST, request.FILES)
                documento = None
                tramite = TramitePago.objects.get(pk=int(request.POST['id']))
                if f.is_valid():
                    tipodocumento = f.cleaned_data['tipodocumento']
                    ubicacion = tramite.ubicacion_actual()
                    nfile = None
                    if 'archivo' in request.FILES:
                        nfile = request.FILES['archivo']
                        nfile._name = generar_nombre("documentotramite_", nfile._name)
                    if tipodocumento.id == 1:
                        valortotal = Decimal(request.POST['totaldoc'])
                        valorbase = Decimal(request.POST['totalbase'])
                        documento = DocumentosTramitePago(tramitepago=tramite,
                                                          numero=f.cleaned_data['numero'],
                                                          tipodocumento=tipodocumento,
                                                          departamento=persona.mi_departamento(),
                                                          nombre=f.cleaned_data['nombre'],
                                                          descripcion=f.cleaned_data['descripcion'],
                                                          subtotal0=f.cleaned_data['subtotal0'],
                                                          subtotaliva=f.cleaned_data['subtotaliva'],
                                                          iva=f.cleaned_data['iva'],
                                                          descuento=f.cleaned_data['descuento'],
                                                          beneficiario=f.cleaned_data['beneficiario'],
                                                          baseimponible=valorbase,
                                                          archivo=nfile,
                                                          total=valortotal)
                        documento.save(request)
                    else:
                        documento = DocumentosTramitePago(tramitepago=tramite,
                                                         tipodocumento=tipodocumento,
                                                          numero=f.cleaned_data['numero'],
                                                         departamento=persona.mi_departamento(),
                                                         nombre=f.cleaned_data['nombre'],
                                                         descripcion=f.cleaned_data['descripcion'],
                                                         archivo=nfile)
                        documento.save(request)
                    log(u'Adiciono nuevo documento al tramite: %s' % tramite, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addbeneficiario':
            try:
                f = BeneficiariosForm(request.POST, request.FILES)
                tramite = TramitePago.objects.get(pk=int(request.POST['id']))
                if f.is_valid():
                    valoractual = Decimal(tramite.total_beneficiarios()) + Decimal(f.cleaned_data['total'])
                    if valoractual > tramite.valortotal:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor por beneficiario supera el total del Trámite."})
                    beneficiairo = BeneficiariTramitePago(tramitepago=tramite,
                                                          beneficiario_id=f.cleaned_data['beneficiario'],
                                                          valor=Decimal(f.cleaned_data['total']))
                    beneficiairo.save(request)
                    log(u'Adiciono nuevo beneficiario al tramite: %s' % tramite, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addretencion':
            try:
                f = RetencionesDocumentoTramitePagoForm(request.POST)
                documento = DocumentosTramitePago.objects.get(pk=int(request.POST['id']))
                if f.is_valid():
                    valor = Decimal(request.POST['valorret'])
                    retencion = RetencionesDocumentoTramitePago(documentotramitepago=documento,
                                                                codigo_id=f.cleaned_data['codigo'],
                                                                valorretenido=valor)
                    retencion.save(request)
                    log(u'Adiciono retención al documento del tramite: %s' % documento, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addcertificacion':
            try:
                f = CertificacionTramiteForm(request.POST)
                tramite = TramitePago.objects.get(pk=int(request.POST['id']))
                if f.is_valid():
                    cert = CertificacionPartida.objects.get(pk=int(f.cleaned_data['certificacion']))
                    if cert.saldo > tramite.valortotal:
                        return JsonResponse({"result": "bad", "mensaje": u"El monto de la certificación es mayor al trámite"})
                    certificacion = CertificacionTramitePago(tramitepago=tramite,
                                                             certificacion=cert)
                    certificacion.save(request)
                    log(u'Adiciono certificacion al tramite: %s' % certificacion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editdocumentos':
            try:
                f = DocumentoTramiteForm(request.POST)
                if f.is_valid():
                    documento = DocumentosTramitePago.objects.get(pk=request.POST['id'])
                    documento.beneficiario = f.cleaned_data['beneficiario']
                    documento.descripcion = f.cleaned_data['descripcion'].strip()
                    documento.nombre = f.cleaned_data['nombre'].strip()
                    documento.save(request)
                    log(u'Modifico Documento de trámite: %s' % documento, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'detalle_tramite':
            try:
                data['tramite'] = tramite = TramitePago.objects.get(pk=int(request.POST['id']))
                data['documentos'] = tramite.documentostramitepago_set.all()
                data['recorridos'] = tramite.recorridotramite_set.all().order_by('-fecharecibido')
                data['partidas'] = tramite.detallepartidatramitepago_set.all()
                data['beneficiarios'] = tramite.beneficiaritramitepago_set.all()
                template = get_template("fin_tramitepago/detalle.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'detalle_revisiones':
            try:
                data['documento'] = documento = DocumentosTramitePago.objects.get(pk=int(request.POST['id']))
                data['detalles'] = documento.detalledocumentopago_set.all().exclude(recorrido=persona.mi_departamento())
                template = get_template("fin_tramitepago/detallerevisiones.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'detalle_retenciones':
            try:
                data['documento'] = documento = DocumentosTramitePago.objects.get(pk=int(request.POST['id']))
                data['detalles'] = documento.retencionesdocumentotramitepago_set.all()
                template = get_template("fin_tramitepago/detalleretensiones.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'verificar_doc':
            try:
                documento = DocumentosTramitePago.objects.get(pk=int(request.POST['id']))
                recorrido = RecorridoTramite.objects.get(pk=int(request.POST['ruta']))
                if request.POST['estado'] == u'true':
                    detalle = DetalleDocumentoPago(recorrido=recorrido,
                                                   documentopago=documento,
                                                   verificado=True)
                    detalle.save(request)
                    log(u'Adiciono detalle documento de pago - Tramite de pago: %s - %s - %s - [%s]' % (detalle.recorrido,detalle.documentopago,detalle.verificado,detalle.id), request, "add")
                else:
                    if documento.detalle_documento(recorrido):
                        detalle = documento.detalle_documento(recorrido)
                        log(u'Elimino detalle documento de pago - Tramite de pago: %s - %s - %s - [%s]' % (detalle.recorrido, detalle.documentopago, detalle.verificado, detalle.id), request, "del")
                        detalle.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'verificar_doc_todos':
            try:
                tramite = TramitePago.objects.get(pk=int(request.POST['id']))
                recorrido = RecorridoTramite.objects.get(pk=int(request.POST['ruta']))
                for documento in tramite.documentostramitepago_set.all():
                    if request.POST['estado'] == u'true':
                        detalle = DetalleDocumentoPago(recorrido=recorrido,
                                                       documentopago=documento,
                                                       verificado=True)
                        detalle.save(request)
                        log(u'Adiciono detalle documento de pago - Tramite de pago: %s - %s - %s - [%s]' % (detalle.recorrido, detalle.documentopago, detalle.verificado, detalle.id), request, "add")
                    else:
                        if documento.detalle_documento(recorrido):
                            detalle = documento.detalle_documento(recorrido)
                            log(u'Elimino detalle documento de pago - Tramite de pago: %s - %s - %s - [%s]' % (detalle.recorrido, detalle.documentopago, detalle.verificado, detalle.id), request, "del")
                            detalle.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'finalizarcomp':
            try:
                comprobante = ComprobanteEgreso.objects.get(pk=int(request.POST['id']))
                comprobante.estado = 2
                comprobante.save(request)
                secuencia = secuencia_egreso(request)
                if not comprobante.numero:
                    secuencia.resumenegreso += 1
                    secuencia.save(request)
                    comprobante.numero = secuencia.resumenegreso
                comprobante.save(request)
                log(u'Finalizar comprobante: %s' % comprobante, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'eliminarcomprobante':
            try:
                comprobante = ComprobanteEgreso.objects.get(pk=int(request.POST['id']))
                comprobante.documentostramitepago_set.update(comprobante=None)
                comprobante.beneficiaritramitepago_set.update(comprobante=None)
                comprobante.delete()
                log(u'Elimino comprobante: %s' % comprobante, request, "delete")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'actualizaobservacion':
            try:
                documento = DocumentosTramitePago.objects.get(pk=int(request.POST['id']))
                recorrido = RecorridoTramite.objects.get(pk=int(request.POST['idr']))
                if documento.detalle_documento(recorrido):
                    detalle = documento.detalle_documento(recorrido)
                    detalle.observacion = request.POST['valobser']
                    detalle.save(request)
                    log(u'Actualizo observacion en detalle documento de pago - Tramite de pago: %s - %s - %s - [%s]' % (detalle.recorrido, detalle.documentopago, detalle.verificado, detalle.id), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

        if action == 'calcula_retencion':
            try:
                codigo = CodigoRetencion.objects.get(pk=int(request.POST['id']))
                doc = DocumentosTramitePago.objects.get(pk=int(request.POST['doc']))
                porcentaje = codigo.porcentaje
                valorretenido = 0
                if codigo.impuestoretenido.id == 1:
                    valorretenido = Decimal((Decimal(doc.baseimponible) * Decimal(porcentaje))/100).quantize(Decimal('.01'))
                elif codigo.impuestoretenido.id == 2:
                    valorretenido = Decimal((Decimal(doc.iva) * Decimal(porcentaje)) / 100).quantize(Decimal('.01'))
                return JsonResponse({"result": "ok", "valor": float(valorretenido)})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

        if action == 'monto_certificacion':
            try:
                cert = CertificacionPartida.objects.get(pk=int(request.POST['id']))
                monto = cert.saldo
                return JsonResponse({"result": "ok", "valor": float(monto)})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

        if action == 'eliminartramite':
            try:
                tramite = TramitePago.objects.get(pk=int(request.POST['id']))
                tramite.recorridotramite_set.all().delete()
                tramite.beneficiaritramitepago_set.all().delete()
                tramite.documentostramitepago_set.all().delete()
                tramite.detallepartidatramitepago_set.all().delete()
                tramite.status = False
                tramite.save(request)
                log(u'Elimino tramite: %s' % tramite, request, "delete")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'eliminarcert':
            try:
                cert = CertificacionTramitePago.objects.get(pk=int(request.POST['id']))
                cert.delete()
                log(u'Elimino certificación: %s' % cert, request, "delete")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'eliminarbeneficiario':
            try:
                beneficiario = BeneficiariTramitePago.objects.get(pk=int(request.POST['id']))
                beneficiario.delete()
                log(u'Elimino beneficiario: %s' % beneficiario, request, "delete")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'accion_dep':
            try:
                dep = Departamento.objects.get(pk=int(request.POST['id']))
                lista = []
                for acciones in AccionesTramitePago.objects.filter(Q(permiso__user__persona__departamento=dep) | Q(permiso__group__user__persona__departamento=dep)).distinct():
                    lista.append([acciones.id, acciones.accion])
                return JsonResponse({"result": "ok", "lista": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'traspasar_tramite':
            try:
                tramite = TramitePago.objects.get(pk=int(request.POST['id']))
                actual = tramite.ubicacion_actual()
                if not tramite.documentostramitepago_set.exists():
                    return JsonResponse({"result": "bad", "mensaje": u"No se han adjuntado documentos al trámite"})
                if tramite.documentostramitepago_set.filter(detalledocumentopago__verificado=False).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Existen documentos que no han sido verificados"})
                departamento = Departamento.objects.get(pk=int(request.POST['dep']))
                accion = AccionesTramitePago.objects.get(pk=int(request.POST['per']))
                recorrido = RecorridoTramite(tramitepago=tramite,
                                             departamento=departamento,
                                             accion=accion,
                                             estado=tramite.estado,
                                             fecharecibido=datetime.now())
                recorrido.save(request)
                actual.fechaproceso = datetime.now()
                actual.estado = 3
                actual.save(request)
                log(u'Movio tramite: %s' % tramite, request, "delete")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'rechazar_tramite':
            try:
                tramite = TramitePago.objects.get(pk=int(request.POST['id']))
                motivo = request.POST['motivo']
                tramite.estado = 2
                tramite.motivorechazo = motivo
                tramite.fechafin = datetime.now().date()
                tramite.save(request)
                log(u'Movio tramite: %s' % tramite, request, "delete")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'eliminardoc':
            try:
                documento = DocumentosTramitePago.objects.get(pk=int(request.POST['id']))
                documento.delete()
                log(u'Elimino documento: %s' % documento, request, "delete")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'enviarxml':
            try:
                doc = DocumentosTramitePago.objects.get(id=int(request.POST['id']))
                beneficiario = doc.beneficiario
                send_html_mail("Notificacion de Deudas", "emails/envio_comprobante.html", {'sistema': u'Sistema de Gestión Administrativa', 'doc': doc, 'beneficiario': beneficiario, 't': miinstitucion()}, [beneficiario.beneficiario.email, ], [], cuenta=CUENTAS_CORREOS[1][1])
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'marcarpagado':
            try:
                tramite = TramitePago.objects.get(pk=int(request.POST['id']))
                tramite.pagado = True
                tramite.fechapagado = datetime.now().date()
                tramite.save(request)
                log(u'Confirmo Pago de tarmite: %s' % tramite, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'marcaracreditado':
            try:
                tramite = TramitePago.objects.get(pk=int(request.POST['id']))
                tramite.acreditado = True
                tramite.estado = 3
                tramite.fechafin = datetime.now().date()
                tramite.fechaacreditado = datetime.now().date()
                tramite.save(request)
                log(u'Confirmo Acreditacion de tarmite: %s' % tramite, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'aprobarrectorado':
            try:
                tramite = TramitePago.objects.get(pk=int(request.POST['id']))
                tramite.aprobadorectorado = True
                tramite.fechaaprobador = datetime.now().date()
                tramite.save(request)
                log(u'Confirmo Aprobacion de tarmite: %s' % tramite, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'aprobarfinanciero':
            try:
                tramite = TramitePago.objects.get(pk=int(request.POST['id']))
                tramite.aprobadofinanciero = True
                tramite.fechaaprobadof = datetime.now().date()
                tramite.save(request)
                log(u'Confirmo Aprobacion de tarmite: %s' % tramite, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'comprobante':
            try:
                f = ComprobanteEgresoForm(request.POST)
                if f.is_valid():
                    facturas = None
                    docs = 0
                    riva = 0
                    rf = 0
                    if 'lista_items1' in request.POST:
                        facturas = json.loads(request.POST['lista_items1'])
                    if 'valdoc' in request.POST and Decimal(request.POST['valdoc']) > 0:
                        docs = null_to_decimal(request.POST['valdoc'], 2)
                    if 'retiva' in request.POST and Decimal(request.POST['retiva']) > 0:
                        riva = null_to_decimal(request.POST['retiva'], 2)
                    if 'retfuente' in request.POST and Decimal(request.POST['retfuente']) > 0:
                        rf = null_to_decimal(request.POST['retfuente'], 2)
                    beneficiario = f.cleaned_data['beneficiario']
                    comprobante = ComprobanteEgreso(beneficiario=beneficiario.beneficiario.nombre_completo(),
                                                    identificacion=f.cleaned_data['identificacion'],
                                                    fecha=f.cleaned_data['fecha'],
                                                    valordocumentos=docs,
                                                    totalretenidoiva=riva,
                                                    totalretenidofuente=rf,
                                                    totalanticipos=f.cleaned_data['totalanticipos'],
                                                    totalotros=f.cleaned_data['totalotros'],
                                                    totalmultas=f.cleaned_data['totalmultas'],
                                                    totalpagar=f.cleaned_data['totalpagar'],
                                                    concepto=f.cleaned_data['concepto'],
                                                    observacion=f.cleaned_data['observacion'])
                    comprobante.save(request)
                    beneficiario.comprobante = comprobante
                    beneficiario.save(request)
                    if facturas:
                        for d in facturas:
                            factura = DocumentosTramitePago.objects.get(pk=int(d['id']))
                            factura.comprobante = comprobante
                            factura.beneficiario = beneficiario
                            factura.save()
                    log(u'Adiciono nuevo comprobante de egreso: %s' % comprobante, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'id_benef':
            try:
                tramite = TramitePago.objects.get(pk=int(request.POST['id']))
                b = BeneficiariTramitePago.objects.get(pk=int(request.POST['b']))
                beneficiario = b.beneficiario
                ide = beneficiario.identificacion()
                lista = []
                valdoc = 0
                ret = 0
                data = {}
                data['detalles'] = DocumentosTramitePago.objects.filter(comprobante__isnull=True, tramitepago=tramite, beneficiario__beneficiario=beneficiario)
                template = get_template("fin_tramitepago/documentoscomprobante.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'datos': json_content, 'ide': ide, 'concepto': tramite.motivo})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Agregar Trámite de Pago'
                    form = TramitePagoForm()
                    form.adicionar(persona)
                    data['form'] = form
                    return render(request, "fin_tramitepago/add.html", data)
                except Exception as ex:
                    pass

            if action == 'subir':
                try:
                    data['title'] = u'Subir Archivo'
                    data['documento'] = documento = DocumentosTramitePago.objects.get(pk=request.GET['id'])
                    form = DocumentoTramiteForm()
                    form.subir()
                    data['form'] = form
                    return render(request, "fin_tramitepago/subir.html", data)
                except Exception as ex:
                    pass

            if action == 'subirxml':
                try:
                    data['title'] = u'Archivos XML'
                    data['documento'] = documento = DocumentosTramitePago.objects.get(pk=request.GET['id'])
                    form = DocumentoXmlTramiteForm()
                    data['form'] = form
                    return render(request, "fin_tramitepago/subirxml.html", data)
                except Exception as ex:
                    pass

            if action == 'subirpdf':
                try:
                    data['title'] = u'Archivos PDF'
                    data['documento'] = documento = DocumentosTramitePago.objects.get(pk=request.GET['id'])
                    form = DocumentoPdfTramiteForm()
                    data['form'] = form
                    return render(request, "fin_tramitepago/subirpdf.html", data)
                except Exception as ex:
                    pass

            if action == 'adddocumentos':
                try:
                    data['title'] = u'Agregar Documento de Trámite de Pago'
                    data['tramite'] = tramite = TramitePago.objects.get(pk=int(request.GET['id']))
                    form = DocumentoTramiteForm()
                    form.adicionar(tramite)
                    data['form'] = form
                    return render(request, "fin_tramitepago/adddocumento.html", data)
                except Exception as ex:
                    pass

            if action == 'addbeneficiario':
                try:
                    data['title'] = u'Agregar Beneficiario de Trámite de Pago'
                    data['tramite'] = tramite = TramitePago.objects.get(pk=int(request.GET['id']))
                    data['form'] = BeneficiariosForm()
                    return render(request, "fin_tramitepago/addbeneficiario.html", data)
                except Exception as ex:
                    pass

            if action == 'addretencion':
                try:
                    data['title'] = u'Agregar Retención al Documento'
                    data['doc'] = doc = DocumentosTramitePago.objects.get(pk=int(request.GET['id']))
                    form = RetencionesDocumentoTramitePagoForm()
                    form.agregar()
                    data['form'] = form
                    return render(request, "fin_tramitepago/addretencion.html", data)
                except Exception as ex:
                    pass

            if action == 'addcertificacion':
                try:
                    data['title'] = u'Agregar Certificación'
                    data['tramite'] = tramite = TramitePago.objects.get(pk=int(request.GET['id']))
                    data['form'] = CertificacionTramiteForm()
                    return render(request, "fin_tramitepago/addcertificacion.html", data)
                except Exception as ex:
                    pass

            if action == 'editdocumentos':
                try:
                    data['title'] = u'Editar Documento de Trámite de Pago'
                    data['documento'] = documento = DocumentosTramitePago.objects.get(pk=int(request.GET['id']))
                    data['mi_departamento'] = persona.mi_departamento()
                    form = DocumentoTramiteForm(initial={'tipodocumento': documento.tipodocumento.id,
                                                         'beneficiario': documento.beneficiario,
                                                         'nombre': documento.nombre,
                                                         'subtotal0': documento.subtotal0,
                                                         'subtotaliva': documento.subtotaliva,
                                                         'retencionfuente': documento.retencionfuente,
                                                         'total': documento.total,
                                                         'archivo': documento.archivo,
                                                         'descripcion': documento.descripcion})
                    form.editar(documento)
                    data['form'] = form
                    return render(request, "fin_tramitepago/editdocumento.html", data)
                except Exception as ex:
                    pass

            if action == 'documentos':
                try:
                    data['title'] = u'Documentos del Trámite de Pago'
                    data['tramite'] = tramite = TramitePago.objects.get(pk=int(request.GET['id']))
                    data['actual'] = tramite.ubicacion_actual()
                    data['mi_departamento'] = persona.mi_departamento()
                    data['documentos'] = tramite.documentostramitepago_set.all()
                    return render(request, "fin_tramitepago/documentos.html", data)
                except Exception as ex:
                    pass

            if action == 'comprobante':
                try:
                    data['title'] = u'Agregar Comprobante'
                    data['tramite'] = tramite = TramitePago.objects.get(pk=int(request.GET['id']))
                    form = ComprobanteEgresoForm(initial={'tramite': tramite})
                    form.adicionar(tramite)
                    data['form'] = form
                    return render(request, "fin_tramitepago/addcomprobante.html", data)
                except Exception as ex:
                    pass

            if action == 'miscomprobante':
                try:
                    data['title'] = u'Comprobantes del tramite'
                    data['id'] = request.GET['id']
                    data['tramite'] = tramite = TramitePago.objects.get(pk=int(request.GET['id']))
                    lista = []
                    for i in tramite.beneficiaritramitepago_set.all():
                        if i.comprobante:
                            lista.append(i.comprobante.id)
                    data['comprobantes'] = ComprobanteEgreso.objects.filter(id__in=lista)
                    data['reporte_0'] = obtener_reporte('comprobantes_egresos')
                    return render(request, "fin_tramitepago/comprobantestramite.html", data)
                except Exception as ex:
                    pass

            if action == 'finalizarcomp':
                try:
                    data['title'] = u'Confirmar finalizar comprobante'
                    data['comprobante'] = ComprobanteEgreso.objects.get(pk=int(request.GET['id']))
                    return render(request, "fin_tramitepago/finalizar.html", data)
                except:
                    pass

            if action == 'eliminarcomprobante':
                try:
                    data['title'] = u'Confirmar eliminar Comprobante de Egresos'
                    data['idc'] = request.GET['idc']
                    data['comprobante'] = ComprobanteEgreso.objects.get(pk=int(request.GET['id']))
                    return render(request, "fin_tramitepago/eliminarcomp.html", data)
                except:
                    pass

            if action == 'beneficiarios':
                try:
                    data['title'] = u'Beneficiarios del Trámite de Pago'
                    data['tramite'] = tramite = TramitePago.objects.get(pk=int(request.GET['id']))
                    data['actual'] = tramite.ubicacion_actual()
                    data['mi_departamento'] = persona.mi_departamento()
                    data['beneficiarios'] = tramite.beneficiaritramitepago_set.all()
                    return render(request, "fin_tramitepago/beneficiarios.html", data)
                except Exception as ex:
                    pass

            if action == 'certificaciones':
                try:
                    data['title'] = u'Certificaciones Presupuestarias'
                    data['tramite'] = tramite = TramitePago.objects.get(pk=int(request.GET['id']))
                    data['actual'] = tramite.ubicacion_actual()
                    data['mi_departamento'] = persona.mi_departamento()
                    data['certificaciones'] = tramite.certificaciontramitepago_set.all()
                    return render(request, "fin_tramitepago/certificaciones.html", data)
                except Exception as ex:
                    pass

            if action == 'retenciones':
                try:
                    data['title'] = u'Retenciones del Documento'
                    data['doc'] = doc = DocumentosTramitePago.objects.get(pk=int(request.GET['id']))
                    data['retenciones'] = doc.retencionesdocumentotramitepago_set.all()
                    return render(request, "fin_tramitepago/retenciones.html", data)
                except Exception as ex:
                    pass

            if action == 'comprobantes':
                try:
                    data['title'] = u'Comprobantes de Egresos'
                    data['comprobantes'] = ComprobanteEgreso.objects.all()
                    return render(request, "fin_tramitepago/comprobantes.html", data)
                except Exception as ex:
                    pass

            if action == 'eliminartramite':
                try:
                    data['title'] = u'Confirmar eliminar Tramite de Pagos'
                    data['tramite'] = TramitePago.objects.get(pk=int(request.GET['id']))
                    return render(request, "fin_tramitepago/eliminar.html", data)
                except:
                    pass

            if action == 'eliminarcert':
                try:
                    data['title'] = u'Confirmar eliminar Certificación'
                    data['cert'] = CertificacionTramitePago.objects.get(pk=int(request.GET['id']))
                    return render(request, "fin_tramitepago/eliminarcert.html", data)
                except:
                    pass

            if action == 'eliminarbeneficiario':
                try:
                    data['title'] = u'Confirmar eliminar Beneficiario'
                    data['persona'] = beneficiario = BeneficiariTramitePago.objects.get(pk=int(request.GET['id']))
                    data['tramite'] = beneficiario.tramitepago
                    return render(request, "fin_tramitepago/eliminarbeneficiario.html", data)
                except:
                    pass

            if action == 'eliminardoc':
                try:
                    data['title'] = u'Confirmar eliminar Documento'
                    data['doc'] = doc = DocumentosTramitePago.objects.get(pk=int(request.GET['id']))
                    data['tramite'] = doc.tramitepago
                    return render(request, "fin_tramitepago/eliminardoc.html", data)
                except:
                    pass

            if action == 'marcarpagado':
                try:
                    data['title'] = u'Confirmar Pago del Trámite'
                    data['tramite'] = TramitePago.objects.get(pk=int(request.GET['id']))
                    return render(request, "fin_tramitepago/marcarpagado.html", data)
                except:
                    pass

            if action == 'marcaracreditado':
                try:
                    data['title'] = u'Confirmar Acreditación del Trámite'
                    data['tramite'] = TramitePago.objects.get(pk=int(request.GET['id']))
                    return render(request, "fin_tramitepago/marcaracreditado.html", data)
                except:
                    pass

            if action == 'aprobarrectorado':
                try:
                    data['title'] = u'Confirmar Pago del Trámite'
                    data['tramite'] = TramitePago.objects.get(pk=int(request.GET['id']))
                    return render(request, "fin_tramitepago/aprobarrectorado.html", data)
                except:
                    pass

            if action == 'aprobarfinanciero':
                try:
                    data['title'] = u'Confirmar Pago del Trámite'
                    data['tramite'] = TramitePago.objects.get(pk=int(request.GET['id']))
                    return render(request, "fin_tramitepago/aprobarfinanciero.html", data)
                except:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            if not DistributivoPersona.objects.filter(persona=persona):
                return HttpResponseRedirect('/?info=Ud. no tiene asignado un cargo.')
            data['title'] = u'Tramites de Pagos'
            ids = None
            search = None
            if 's' in request.GET:
                search = request.GET['s']
                tramite = TramitePago.objects.filter(Q(tipotramite__nombre__icontains=search, status=True) |
                                                     Q(fechainicio__icontains=search, status=True) |
                                                     Q(origen__nombre__icontains=search, status=True) |
                                                     Q(motivo__icontains=search, status=True)).distinct().order_by('-fechainicio')
            elif 'id' in request.GET:
                ids = request.GET['id']
                tramite = TramitePago.objects.filter(id=ids, status=True).order_by('-fechainicio')
            else:
                tramite = TramitePago.objects.filter(status=True).order_by('-fechainicio')
            paging = MiPaginador(tramite, 25)
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
            data['ids'] = ids if ids else None
            data['page'] = page
            data['tramites'] = page.object_list
            data['reporte_0'] = obtener_reporte('cierre_sesion_caja')
            data['form'] = TraspasoTramiteForm()
            data['form2'] = RechazoTramiteForm()
            data['mi_departamento'] = persona.mi_departamento()
            data['search'] = search if search else ""
            return render(request, "fin_tramitepago/view.html", data)