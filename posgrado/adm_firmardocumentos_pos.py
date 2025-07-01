# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction

import io
import json
import fitz

from core.firmar_documentos_ec import JavaFirmaEc
from postulaciondip.models import ExpedienteContratacion, PersonalAContratar, InformeContratacion
from settings import SITE_STORAGE
from django.contrib import messages
from core.firmar_documentos import firmar, firmarmasivo, obtener_posicion_y, obtener_posicion_x_y, obtener_posicion_x_y_saltolinea
from django.core.files.base import ContentFile
from django.core.files import File as DjangoFile
from django.template.loader import get_template
from django.db.models import Max, Min, Case, When, Value, IntegerField, Count
from sga.tasks import send_html_mail
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from decorators import secure_module, last_access
from posgrado.forms import TipoDocumentoTitulacionForm, EstadoDocumentoTitulacionForm, RevisionExpedienteForm, ArchivoInvitacionForm
from posgrado.models import CohorteMaestria, InscripcionCohorte, Contrato, MaestriasAdmision,DetalleAprobacionContrato,\
EstadoDocumentoTitulacionPosgrado, TipoDocumentoTitulacionPosgrado, DocumentoTitulacionPosgrado, HistorialDocumentoTitulacionPosgrado
from sga.commonviews import adduserdata, traerNotificaciones
from sga.funciones_templatepdf import actagradoposgrado, actagradoposgradocomplexivo, actagradoposgrado2, actagradoposgradocomplexivo2, \
    numero_a_letras
from sga.models import Notificacion, TemaTitulacionPosgradoMatricula, Carrera, Periodo, Persona, ModuloGrupo, Modulo, Graduado
from sagest.models import PersonaDepartamentoFirmas, TipoOtroRubro, Rubro, CuentaContable
from sga.templatetags.sga_extras import encrypt
from sga.funciones import MiPaginador, log, remover_caracteres_tildes_unicode, remover_caracteres_especiales_unicode, \
    generar_nombre, notificacion3, variable_valor, notificacion
from sga.models import miinstitucion, CUENTAS_CORREOS,FirmaPersona
from datetime import datetime,timedelta
from django.db import connections
from sga.excelbackground import firmar_contratos_posgrado_vicerrectorado_background, reporte_contratos_diferido
import time
from xlwt import *
from settings import DEBUG
import xlwt
import sys
import random
import os
import xlsxwriter
unicode =str
@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    hoy = datetime.today()
    adduserdata(request, data)
    data['personasesion'] = personasesion = request.session['persona']
    periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'firmardocumentoindividual':
            try:
                contrato = Contrato.objects.get(pk=request.POST['idcontrato'])
                maestrante = InscripcionCohorte.objects.filter(pk=contrato.inscripcion.id, status=True)
                if not contrato.respaldoarchivocontrato:
                    contrato.respaldoarchivocontrato = contrato.archivocontrato
                    contrato.save(request)
                documento_a_firmar = contrato.respaldoarchivocontrato
                # obtener la posicion xy de la firma del doctor en el pdf
                palabras = ''
                objper = personasesion
                if contrato.ultima_evidencia() and contrato.ultima_evidencia().fecha_aprobacion.date() > datetime.strptime('2024-05-31', '%Y-%m-%d').date():
                    palabras = 'Ing. Eduardo Espinoza Solís, PhD.'
                    objper = PersonaDepartamentoFirmas.objects.filter(status=True, personadepartamento_id=26497,
                                                                      tipopersonadepartamento_id=1).first()
                elif contrato.inscripcion.cohortes.maestriaadmision.carrera.escuelaposgrado.id == 1:
                    palabras = 'Msc. Angelica Maria Solis Manzano'
                    objper = PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True,
                                                             tipopersonadepartamento_id=9, departamento_id=216).first()
                elif contrato.inscripcion.cohortes.maestriaadmision.carrera.escuelaposgrado.id == 2:
                    palabras = 'Msc. Graciela Josefina Castro Castillo'
                    objper = PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True,
                                                             tipopersonadepartamento_id=10, departamento_id=215).first()
                elif contrato.inscripcion.cohortes.maestriaadmision.carrera.escuelaposgrado.id == 3:
                    palabras = 'Msc. Luis Eduardo Solis Granda'
                    objper = PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True,
                                                             tipopersonadepartamento_id=11, departamento_id=163).first()
                y, numpaginafirma = obtener_posicion_y(documento_a_firmar.url, palabras)
                if not y and contrato.ultima_evidencia().fecha_aprobacion.date() > datetime.strptime('2024-05-31', '%Y-%m-%d').date():
                    palabras = 'PhD. Eduardo Espinoza Solís'
                    objper = PersonaDepartamentoFirmas.objects.filter(status=True, personadepartamento_id=26497,
                                                                      tipopersonadepartamento_id=1).first()
                    y, numpaginafirma = obtener_posicion_y(documento_a_firmar.url, palabras)
                # FIN obtener la posicion y
                if not y:
                    if contrato.contratolegalizado:
                        contrato.contratolegalizado = False
                    contrato.estado = 3
                    contrato.save(request)
                    detalleevidencia = DetalleAprobacionContrato(contrato_id=contrato.id)
                    detalleevidencia.save(request)
                    detalleevidencia.observacion = 'El nombre del dr. en la firma del contrato no es el correcto.'
                    detalleevidencia.persona = personasesion
                    detalleevidencia.estado_aprobacion = 3
                    detalleevidencia.fecha_aprobacion = datetime.now()
                    detalleevidencia.save(request)
                    messages.warning(request, "Alerta: El nombre en la firma del contrato no es el correcto. Se ha rechazado y enviado a comercialización.")
                    return JsonResponse({"result": "errornombre"})
                #fin obtener posicion
                firma = request.FILES["firma"]
                bytes_certificado = firma.read()
                extension_certificado = os.path.splitext(firma.name)[1][1:]
                passfirma = request.POST['palabraclave']
                txtFirmas = json.loads(request.POST['txtFirmas'])
                if not txtFirmas:
                    return JsonResponse({"result": "bad", "mensaje": u"No se ha podido seleccionar la ubicación de la firma"})
                generar_archivo_firmado = io.BytesIO()
                x = txtFirmas[-1]
                try:
                    datau = JavaFirmaEc(
                        archivo_a_firmar=documento_a_firmar, archivo_certificado=bytes_certificado,
                        extension_certificado=extension_certificado,
                        password_certificado=passfirma,
                        page=numpaginafirma, reason='Contrato legalizado', lx=115, ly=y)
                except Exception as ex:
                    from sga.funciones import notificacion
                    if contrato.contratolegalizado:
                        contrato.contratolegalizado = False
                    contrato.estado = 3
                    contrato.save(request)
                    detalleevidencia = DetalleAprobacionContrato(contrato_id=contrato.id)
                    detalleevidencia.save(request)
                    detalleevidencia.observacion = 'Documento con inconsistencia en la firma del Estudiante'
                    detalleevidencia.persona = personasesion
                    detalleevidencia.estado_aprobacion = 3
                    detalleevidencia.fecha_aprobacion = datetime.now()
                    detalleevidencia.save(request)
                    messages.warning(request, f'Documento con inconsistencia en la firma del ESTUDIANTE. Enviado a comercialización para su revisión.')

                    cuerpo = ('Contrato de pago con inconsistencia en la Firma del Estudiante: %s - %s' % (contrato.inscripcion.inscripcionaspirante.persona.cedula, contrato.inscripcion.inscripcionaspirante))
                    personanotificar = Persona.objects.get(pk=24145)
                    notificacion('Revisión de documento de Contrato de pago',
                                 cuerpo, personanotificar, None,
                                 '/comercial?action=evidenciacontrato&idcohorte=%s&aspirante=%s' % (encrypt(contrato.inscripcion.cohortes.id),encrypt(contrato.inscripcion.id)),
                                 contrato.pk, 1, 'sga', Contrato, request)

                    cuerpo = ('Documento con inconsistencia en la firma del ESTUDIANTE %s. Enviado a comercialización para su revisión.' % contrato.inscripcion.inscripcionaspirante)
                    notificacion('Firma electrónica SGA',
                                 cuerpo, personasesion, None, '',
                                 contrato.pk, 1, 'sga', Contrato, request)

                    return JsonResponse({"result": "badfirma"})
                from sga.funciones import notificacion
                if not datau:
                    return JsonResponse({"result": "bad", "mensaje": "error"})

                if datau.datos_del_certificado['cedula'] == objper.personadepartamento.cedula or variable_valor("CAN_SIGN"):
                    generar_archivo_firmado = io.BytesIO()
                    generar_archivo_firmado.write(datau.sign_and_get_content_bytes())
                    generar_archivo_firmado.seek(0)
                    extension = documento_a_firmar.name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    nombrefile_ = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(documento_a_firmar.name)).replace('-', '_').replace('.pdf', '')
                    _name = 'cp_contratopago_'+str(contrato.inscripcion.id)
                    file_obj = DjangoFile(generar_archivo_firmado, name=f"{_name}_firmado.pdf")
                    contrato.archivocontrato = file_obj
                    contrato.contratolegalizado = True
                    contrato.save(request)
                    detalleevidencia = DetalleAprobacionContrato(contrato_id=contrato.id)
                    detalleevidencia.save(request)
                    detalleevidencia.observacion = 'Contrato legalizado'
                    detalleevidencia.archivocontrato = file_obj
                    detalleevidencia.persona = personasesion
                    detalleevidencia.estado_aprobacion = 2
                    detalleevidencia.fecha_aprobacion = datetime.now()
                    detalleevidencia.save(request)
                    cuerpo = ('Documento firmado con éxito: %s' % contrato.inscripcion.inscripcionaspirante)
                    notificacion('Firma electrónica SGA',
                                 cuerpo, personasesion, None,
                                 '/firmardocumentosposgrado?action=firmaelectronicacontratos&s=%s'%(contrato.inscripcion.inscripcionaspirante.persona.cedula),
                                 contrato.pk, 1, 'sga', Contrato, request)

                    messages.success(request, f'Documento firmado con éxito')
                    log(u'Firmo Documento: {}'.format(nombrefile_), request, "add")

                    integrante = InscripcionCohorte.objects.get(status=True, pk=contrato.inscripcion.id)

                    asunto = u"CONTRATO APROBADO Y LEGALIZADO"
                    observacion = f'Se le comunica que el contrato de {integrante.formapagopac.descripcion} del admitido {integrante.inscripcionaspirante.persona} con cédula {integrante.inscripcionaspirante.persona.cedula} ha sido aprobado y legalizado. Por favor, dar seguimiento en la siguiente fase.'
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
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": f"La firma subida no pertenece al director/a {objper.personadepartamento}"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s"%ex})

        elif action == 'firmardocumentoindividual_old':
            try:
                contrato = Contrato.objects.get(pk=request.POST['idcontrato'])
                maestrante = InscripcionCohorte.objects.filter(pk=contrato.inscripcion.id, status=True)
                if not contrato.respaldoarchivocontrato:
                    contrato.respaldoarchivocontrato = contrato.archivocontrato
                    contrato.save(request)
                pdf = contrato.respaldoarchivocontrato
                #obtener la posicion xy de la firma del doctor en el pdf
                pdfname = SITE_STORAGE + contrato.respaldoarchivocontrato.url
                palabras = ''
                if contrato.inscripcion.cohortes.maestriaadmision.carrera.escuelaposgrado.id == 1:
                    palabras = 'Msc. Angelica Maria Solis Manzano'
                elif contrato.inscripcion.cohortes.maestriaadmision.carrera.escuelaposgrado.id == 2:
                    palabras = 'Msc. Graciela Josefina Castro Castillo'
                elif contrato.inscripcion.cohortes.maestriaadmision.carrera.escuelaposgrado.id == 3:
                    palabras = 'Msc. Luis Eduardo Solis Granda'
                documento = fitz.open(pdfname)
                numpaginafirma = int(documento.page_count)-1
                with fitz.open(pdfname) as document:
                    words_dict = {}
                    for page_number, page in enumerate(document):
                        if page_number == numpaginafirma:
                            words = page.get_text("blocks")
                            words_dict[0] = words
                valor = None
                for cadena in words_dict[0]:
                    if palabras in cadena[4]:
                        valor = cadena
                if valor:
                    y = 5000 - int(valor[3]) - 4110
                else:
                    if contrato.contratolegalizado:
                        contrato.contratolegalizado = False
                    contrato.estado = 3
                    contrato.save(request)
                    detalleevidencia = DetalleAprobacionContrato(contrato_id=contrato.id)
                    detalleevidencia.save(request)
                    detalleevidencia.observacion = 'El nombre del dr. en la firma del contrato no es el correcto.'
                    detalleevidencia.persona = personasesion
                    detalleevidencia.estado_aprobacion = 3
                    detalleevidencia.fecha_aprobacion = datetime.now()
                    detalleevidencia.save(request)
                    messages.warning(request, "Alerta: El nombre en la firma del contrato no es el correcto. Se ha rechazado y enviado a comercialización.")
                    return JsonResponse({"result": "errornombre"})
                #fin obtener posicion
                firma = request.FILES["firma"]
                passfirma = request.POST['palabraclave']
                txtFirmas = json.loads(request.POST['txtFirmas'])
                if not txtFirmas:
                    return JsonResponse({"result": "bad", "mensaje": u"No se ha podido seleccionar la ubicación de la firma"})
                generar_archivo_firmado = io.BytesIO()
                x = txtFirmas[-1]
                try:
                    datau, datas = firmar(request, passfirma, firma, pdf, numpaginafirma, x["x"], y, x["width"], x["height"])
                except Exception as ex:
                    from sga.funciones import notificacion
                    if contrato.contratolegalizado:
                        contrato.contratolegalizado = False
                    contrato.estado = 3
                    contrato.save(request)
                    detalleevidencia = DetalleAprobacionContrato(contrato_id=contrato.id)
                    detalleevidencia.save(request)
                    detalleevidencia.observacion = 'Documento con inconsistencia en la firma del Estudiante'
                    detalleevidencia.persona = personasesion
                    detalleevidencia.estado_aprobacion = 3
                    detalleevidencia.fecha_aprobacion = datetime.now()
                    detalleevidencia.save(request)
                    messages.warning(request, f'Documento con inconsistencia en la firma del ESTUDIANTE. Enviado a comercialización para su revisión.')

                    cuerpo = ('Contrato de pago con inconsistencia en la Firma del Estudiante: %s - %s' % (contrato.inscripcion.inscripcionaspirante.persona.cedula, contrato.inscripcion.inscripcionaspirante))
                    personanotificar = Persona.objects.get(pk=24145)
                    notificacion('Revisión de documento de Contrato de pago',
                                 cuerpo, personanotificar, None,
                                 '/comercial?action=evidenciacontrato&idcohorte=%s&aspirante=%s' % (encrypt(contrato.inscripcion.cohortes.id),encrypt(contrato.inscripcion.id)),
                                 contrato.pk, 1, 'sga', Contrato, request)

                    cuerpo = ('Documento con inconsistencia en la firma del ESTUDIANTE %s. Enviado a comercialización para su revisión.' % contrato.inscripcion.inscripcionaspirante)
                    notificacion('Firma electrónica SGA',
                                 cuerpo, personasesion, None, '',
                                 contrato.pk, 1, 'sga', Contrato, request)

                    return JsonResponse({"result": "badfirma"})
                if not datau:
                    return JsonResponse({"result": "bad", "mensaje": f"{datas}"})
                from sga.funciones import notificacion
                generar_archivo_firmado.write(datau)
                generar_archivo_firmado.write(datas)
                generar_archivo_firmado.seek(0)
                extension = pdf.name.split('.')
                tam = len(extension)
                exte = extension[tam - 1]
                nombrefile_ = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(pdf.name)).replace('-', '_').replace('.pdf', '')
                _name = 'cp_contratopago_'+str(contrato.inscripcion.id)
                file_obj = DjangoFile(generar_archivo_firmado, name=f"{_name}_firmado.pdf")
                contrato.archivocontrato = file_obj
                contrato.contratolegalizado = True
                contrato.save(request)
                detalleevidencia = DetalleAprobacionContrato(contrato_id=contrato.id)
                detalleevidencia.save(request)
                detalleevidencia.observacion = 'Contrato legalizado'
                detalleevidencia.archivocontrato = file_obj
                detalleevidencia.persona = personasesion
                detalleevidencia.estado_aprobacion = 2
                detalleevidencia.fecha_aprobacion = datetime.now()
                detalleevidencia.save(request)

                cuerpo = ('Documento firmado con éxito: %s' % contrato.inscripcion.inscripcionaspirante)
                notificacion('Firma electrónica SGA',
                             cuerpo, personasesion, None,
                             '/firmardocumentosposgrado?action=firmaelectronicacontratos&s=%s'%(contrato.inscripcion.inscripcionaspirante.persona.cedula),
                             contrato.pk, 1, 'sga', Contrato, request)

                messages.success(request, f'Documento firmado con éxito')
                log(u'Firmo Documento: {}'.format(nombrefile_), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s"%ex})

        elif action == 'firmardocumentomasivo_old':
            try:
                from sga.funciones import notificacion
                firma = request.FILES["firma"]
                passfirma = request.POST['palabraclave']
                contratosselect = request.POST['ids'].split(',')
                bandera = False
                p12 = None
                listainscripcion = []
                nombresmae = ''
                conterrornombre = 0
                conteoerror = 0
                for con in contratosselect:
                    contrato = Contrato.objects.get(pk=con)
                    if not contrato.respaldoarchivocontrato:
                        contrato.respaldoarchivocontrato = contrato.archivocontrato
                        contrato.save(request)
                    pdf = contrato.respaldoarchivocontrato
                    # obtener la posicion xy de la firma del doctor en el pdf
                    palabras = ''
                    if contrato.inscripcion.cohortes.maestriaadmision.carrera.escuelaposgrado.id == 1:
                        palabras = 'Msc. Angelica Maria Solis Manzano'
                    elif contrato.inscripcion.cohortes.maestriaadmision.carrera.escuelaposgrado.id == 2:
                        palabras = 'Msc. Graciela Josefina Castro Castillo'
                    elif contrato.inscripcion.cohortes.maestriaadmision.carrera.escuelaposgrado.id == 3:
                        palabras = 'Msc. Luis Eduardo Solis Granda'
                    y, numpaginafirma = obtener_posicion_y(pdf.url, palabras)
                    # FIN obtener la posicion y
                    if y:
                        generar_archivo_firmado = io.BytesIO()
                        datau, datas, p12 = firmarmasivo(request, p12, bandera, passfirma, firma, pdf, numpaginafirma, 115, y, 150, 45)
                        if p12:
                            bandera = True
                        if not datau:
                            return JsonResponse({"result": "bad", "mensaje": f"{datas}"})
                        if datau:
                            generar_archivo_firmado.write(datau)
                            generar_archivo_firmado.write(datas)
                            generar_archivo_firmado.seek(0)
                            extension = pdf.name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            nombrefile_ = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(pdf.name)).replace('-', '_').replace('.pdf', '')
                            _name = 'cp_contratopago_' + str(contrato.inscripcion.id)
                            file_obj = DjangoFile(generar_archivo_firmado, name=f"{_name}_firmado.pdf")
                            contrato.archivocontrato = file_obj
                            contrato.contratolegalizado = True
                            contrato.save(request)
                            detalleevidencia = DetalleAprobacionContrato(contrato_id=contrato.id)
                            detalleevidencia.save(request)
                            detalleevidencia.observacion = 'Contrato legalizado'
                            detalleevidencia.archivocontrato = file_obj
                            detalleevidencia.persona = personasesion
                            detalleevidencia.estado_aprobacion = 2
                            detalleevidencia.fecha_aprobacion = datetime.now()
                            detalleevidencia.save(request)
                            log(u'Masivo Firmó Documento: {}'.format(nombrefile_), request, "add")
                            listainscripcion.append(contrato.inscripcion.id)
                            nombresmae += '%s, '%contrato.inscripcion.inscripcionaspirante
                        else:
                            conteoerror += 1
                            if contrato.contratolegalizado:
                                contrato.contratolegalizado = False
                            contrato.estado = 3
                            contrato.save(request)
                            detalleevidencia = DetalleAprobacionContrato(contrato_id=contrato.id)
                            detalleevidencia.save(request)
                            detalleevidencia.observacion = 'Documento con inconsistencia en la firma del Estudiante'
                            detalleevidencia.persona = personasesion
                            detalleevidencia.estado_aprobacion = 3
                            detalleevidencia.fecha_aprobacion = datetime.now()
                            detalleevidencia.save(request)

                            cuerpo = ('Contrato de pago con inconsistencia en la Firma del Estudiante: %s - %s' % (contrato.inscripcion.inscripcionaspirante.persona.cedula, contrato.inscripcion.inscripcionaspirante))
                            personanotificar = Persona.objects.get(pk=24145)
                            notificacion('Revisión de documento de Contrato de pago',
                                         cuerpo, personanotificar, None,
                                         '/comercial?action=evidenciacontrato&idcohorte=%s&aspirante=%s' % (encrypt(contrato.inscripcion.cohortes.id), encrypt(contrato.inscripcion.id)),
                                         contrato.pk, 1, 'sga', Contrato, request)

                            cuerpo = ('Documento con inconsistencia en la firma del ESTUDIANTE %s. Enviado a comercialización para su revisión.' % contrato.inscripcion.inscripcionaspirante)
                            notificacion('Firma electrónica SGA',
                                         cuerpo, personasesion, None, '',
                                         contrato.pk, 1, 'sga', Contrato, request)
                    else:
                        conteoerror += 1
                        conterrornombre += 1
                        if contrato.contratolegalizado:
                            contrato.contratolegalizado = False
                        contrato.estado = 3
                        contrato.save(request)
                        detalleevidencia = DetalleAprobacionContrato(contrato_id=contrato.id)
                        detalleevidencia.save(request)
                        detalleevidencia.observacion = 'El nombre del dr. en la firma del contrato no es el correcto.'
                        detalleevidencia.persona = personasesion
                        detalleevidencia.estado_aprobacion = 3
                        detalleevidencia.fecha_aprobacion = datetime.now()
                        detalleevidencia.save(request)

                # maestrantes = InscripcionCohorte.objects.filter(pk__in=listainscripcion, status=True)
                # send_html_mail("Firma de Contratos POSGRADO.", "emails/notificarfirmacontratopago.html",
                #                {'sistema': u'Sistema de Gestión Académica',
                #                 'fecha': datetime.now().date(),
                #                 'hora': datetime.now().time(),
                #                 'maestrantes': maestrantes,
                #                 't': miinstitucion()},
                #                personasesion.lista_emails_envio(), [],
                #                cuenta=CUENTAS_CORREOS[0][1])

                if listainscripcion:
                    cuerpo = ('Documentos firmados con éxito: %s' % nombresmae)
                    notificacion('Firma electrónica SGA', cuerpo, personasesion, None, '/firmardocumentosposgrado?action=firmaelectronicacontratos', None, 1, 'sga', Contrato, request)
                    if conteoerror > 0:
                        messages.success(request, f'Documentos firmados con éxito. %s' % ('Existieron %s contratos con inconsistencia que no fueron firmados. Enviados a comercialización: %s' % (conteoerror, conterrornombre) if conterrornombre > 0 else ''))
                    else:
                        messages.success(request, f'Documentos firmados con éxito')
                else:
                    if conteoerror > 0:
                        messages.warning(request, f'%s' % ('Existieron %s contrato(s) con inconsistencia que no fueron firmados. Enviados a comercialización.' % conteoerror if conteoerror > 0 else ''))
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s"%ex})

        elif action == 'firmardocumentomasivo':
            try:
                from sga.funciones import notificacion
                passfirma = request.POST['palabraclave']
                firma = request.FILES["firma"]
                contratosselect = request.POST['ids'].split(',')

                if DEBUG:
                    personasesion = Persona.objects.get(id=20539)
                    noti = Notificacion(cuerpo='Firma de contratos en progreso',
                                        titulo='Firma en progreso', destinatario=personasesion,
                                        url='',
                                        prioridad=1, app_label='SGA',
                                        fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                        en_proceso=True)
                    noti.save(request)
                    firmar_contratos_posgrado_vicerrectorado_background(request=request, notiid=noti.pk, firma=firma,
                                                                        passfirma=passfirma,
                                                                        contratosselect=contratosselect,
                                                                        personasesion=personasesion).start()
                else:
                    bandera = False
                    p12 = None
                    listainscripcion = []
                    nombresmae = ''
                    conterrornombre = 0
                    conteoerror = 0
                    if not FirmaPersona.objects.filter(status=True, persona=personasesion, tipofirma=3).exists():
                        objetofirma=FirmaPersona(
                            persona=personasesion,
                            tipofirma=3,firma=firma
                        )
                        objetofirma.save(request)
                    # palabras = 'Dr. Edwuin Jesús Carrasquero Rodríguez'
                    for con in contratosselect:
                        objetofirma = FirmaPersona.objects.filter(status=True, persona=personasesion, tipofirma=3).last()
                        firmaarchivo = objetofirma.firma
                        bytes_certificado = firmaarchivo.read()
                        extension_certificado = os.path.splitext(firmaarchivo.name)[1][1:]

                        contrato = Contrato.objects.get(pk=con)
                        if not contrato.respaldoarchivocontrato:
                            contrato.respaldoarchivocontrato = contrato.archivocontrato
                            contrato.save(request)

                        palabras = ''
                        objper = personasesion

                        if contrato.ultima_evidencia() and contrato.ultima_evidencia().fecha_aprobacion.date() > datetime.strptime('2024-05-31', '%Y-%m-%d').date():
                            palabras = 'Ing. Eduardo Espinoza Solís, PhD.'
                            objper = PersonaDepartamentoFirmas.objects.filter(status=True, personadepartamento_id=26497,
                                                                              tipopersonadepartamento_id=1).first()
                        elif contrato.inscripcion.cohortes.maestriaadmision.carrera.escuelaposgrado.id == 1:
                            palabras = 'Msc. Angelica Maria Solis Manzano'
                            objper = PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True,
                                                                              tipopersonadepartamento_id=9,
                                                                              departamento_id=216).first()
                        elif contrato.inscripcion.cohortes.maestriaadmision.carrera.escuelaposgrado.id == 2:
                            palabras = 'Msc. Graciela Josefina Castro Castillo'
                            objper = PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True,
                                                                              tipopersonadepartamento_id=10,
                                                                              departamento_id=215).first()
                        elif contrato.inscripcion.cohortes.maestriaadmision.carrera.escuelaposgrado.id == 3:
                            palabras = 'Msc. Luis Eduardo Solis Granda'
                            objper = PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True,
                                                                              tipopersonadepartamento_id=11,
                                                                              departamento_id=163).first()

                        documento_a_firmar = contrato.respaldoarchivocontrato
                        # obtener la posicion xy de la firma del doctor en el pdf
                        y, numpaginafirma = obtener_posicion_y(documento_a_firmar.url, palabras)
                        # FIN obtener la posicion y
                        if not y and contrato.ultima_evidencia().fecha_aprobacion.date() > datetime.strptime('2024-05-31', '%Y-%m-%d').date():
                            palabras = 'PhD. Eduardo Espinoza Solís'
                            objper = PersonaDepartamentoFirmas.objects.filter(status=True, personadepartamento_id=26497,
                                                                              tipopersonadepartamento_id=1).first()
                            y, numpaginafirma = obtener_posicion_y(documento_a_firmar.url, palabras)
                        if y:
                            datau = JavaFirmaEc(
                                archivo_a_firmar=documento_a_firmar, archivo_certificado=bytes_certificado,
                                extension_certificado=extension_certificado,
                                password_certificado=passfirma,
                                page=numpaginafirma, reason='Contrato legalizado', lx=115, ly=y)
                            if datau:
                                if datau.datos_del_certificado['cedula'] == objper.personadepartamento.cedula or variable_valor("CAN_SIGN"):
                                    generar_archivo_firmado = io.BytesIO()
                                    generar_archivo_firmado.write(datau.sign_and_get_content_bytes())
                                    generar_archivo_firmado.seek(0)
                                    extension = documento_a_firmar.name.split('.')
                                    tam = len(extension)
                                    exte = extension[tam - 1]
                                    nombrefile_ = remover_caracteres_tildes_unicode(
                                        remover_caracteres_especiales_unicode(documento_a_firmar.name)).replace('-', '_').replace('.pdf', '')
                                    _name = 'cp_contratopago_' + str(contrato.inscripcion.id)
                                    file_obj = DjangoFile(generar_archivo_firmado, name=f"{remover_caracteres_especiales_unicode(_name)}_firmado.pdf")
                                    contrato.archivocontrato = file_obj
                                    contrato.contratolegalizado = True
                                    contrato.save(request)
                                    detalleevidencia = DetalleAprobacionContrato(contrato_id=contrato.id)
                                    detalleevidencia.save(request)
                                    detalleevidencia.observacion = 'Contrato legalizado'
                                    detalleevidencia.archivocontrato = file_obj
                                    detalleevidencia.persona = personasesion
                                    detalleevidencia.estado_aprobacion = 2
                                    detalleevidencia.fecha_aprobacion = datetime.now()
                                    detalleevidencia.save(request)
                                    log(u'Masivo Firmó Documento: {}'.format(nombrefile_), request, "add")
                                    listainscripcion.append(contrato.inscripcion.id)
                                    nombresmae += '%s, ' % contrato.inscripcion.inscripcionaspirante

                                    integrante = InscripcionCohorte.objects.get(status=True, pk=contrato.inscripcion.id)

                                    asunto = u"CONTRATO APROBADO Y LEGALIZADO"
                                    observacion = f'Se le comunica que el contrato de {integrante.formapagopac.descripcion} del admitido {integrante.inscripcionaspirante.persona} con cédula {integrante.inscripcionaspirante.persona.cedula} ha sido aprobado y legalizado. Por favor, dar seguimiento en la siguiente fase.'
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
                                else:
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": f"La firma subida no pertenece al director/a {objper.personadepartamento}"})
                            else:
                                conteoerror += 1
                                if contrato.contratolegalizado:
                                    contrato.contratolegalizado = False
                                contrato.estado = 3
                                contrato.save(request)
                                detalleevidencia = DetalleAprobacionContrato(contrato_id=contrato.id)
                                detalleevidencia.save(request)
                                detalleevidencia.observacion = 'Documento con inconsistencia en la firma del Estudiante'
                                detalleevidencia.persona = personasesion
                                detalleevidencia.estado_aprobacion = 3
                                detalleevidencia.fecha_aprobacion = datetime.now()
                                detalleevidencia.save(request)

                                cuerpo = ('Contrato de pago con inconsistencia en la Firma del Estudiante: %s - %s' % (
                                contrato.inscripcion.inscripcionaspirante.persona.cedula,
                                contrato.inscripcion.inscripcionaspirante))
                                personanotificar = Persona.objects.get(pk=24145)

                                notificacion('Revisión de documento de Contrato de pago',
                                             cuerpo, personanotificar, None,
                                             '/comercial?action=evidenciacontrato&idcohorte=%s&aspirante=%s' % (
                                             encrypt(contrato.inscripcion.cohortes.id), encrypt(contrato.inscripcion.id)),
                                             contrato.pk, 1, 'sga', Contrato, request)

                                cuerpo = (
                                            'Documento con inconsistencia en la firma del ESTUDIANTE %s. Enviado a comercialización para su revisión.' % contrato.inscripcion.inscripcionaspirante)
                                notificacion('Firma electrónica SGA',
                                             cuerpo, personasesion, None, '',
                                             contrato.pk, 1, 'sga', Contrato, request)
                        else:
                            conteoerror += 1
                            conterrornombre += 1
                            if contrato.contratolegalizado:
                                contrato.contratolegalizado = False
                            contrato.estado = 3
                            contrato.save(request)
                            detalleevidencia = DetalleAprobacionContrato(contrato_id=contrato.id)
                            detalleevidencia.save(request)
                            detalleevidencia.observacion = 'El nombre del dr. en la firma del contrato no es el correcto.'
                            detalleevidencia.persona = personasesion
                            detalleevidencia.estado_aprobacion = 3
                            detalleevidencia.fecha_aprobacion = datetime.now()
                            detalleevidencia.save(request)
                        time.sleep(2)
                    if listainscripcion:
                        cuerpo = ('Documentos firmados con éxito: %s' % nombresmae)
                        notificacion('Firma electrónica SGA', cuerpo, personasesion, None,
                                     '/firmardocumentosposgrado?action=firmaelectronicacontratos', None, 1, 'sga', Contrato,
                                     request)
                        if conteoerror > 0:
                            messages.success(request, f'Documentos firmados con éxito. %s' % (
                                'Existieron %s contratos con inconsistencia que no fueron firmados. Enviados a comercialización: %s' % (
                                conteoerror, conterrornombre) if conterrornombre > 0 else ''))
                        else:
                            messages.success(request, f'Documentos firmados con éxito')
                    else:
                        if conteoerror > 0:
                            messages.warning(request, f'%s' % (
                                'Existieron %s contrato(s) con inconsistencia que no fueron firmados. Enviados a comercialización.' % conteoerror if conteoerror > 0 else ''))
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s" % ex})

        elif action == 'aprobaroficiomasivo':
            try:
                contratosselect = request.POST['id'].split(',')
                if contratosselect[0] != '':
                    for con in contratosselect:
                        contrato = Contrato.objects.get(status=True, pk=con)
                        contrato.estado = 5
                        contrato.status = False
                        contrato.save(request)

                        ins = InscripcionCohorte.objects.get(status=True, pk=contrato.inscripcion.id)
                        ins.puedeeditarmp = True
                        ins.save(request)

                        detalle = DetalleAprobacionContrato(contrato=contrato,
                                                            estado_aprobacion=2,
                                                            fecha_aprobacion=datetime.now(),
                                                            observacion='Su oficio de terminación de contrato ha sido aprobado, se procede con la anulación de su contrato actual.',
                                                            archivocontrato=contrato.archivooficio,
                                                            persona=personasesion,
                                                            esoficio=True,
                                                            motivo_terminacion=contrato.motivo_terminacion)
                        detalle.save(request)

                        detalle = DetalleAprobacionContrato(contrato=contrato,
                                                            estado_aprobacion=5,
                                                            fecha_aprobacion=datetime.now(),
                                                            observacion='Contrato de ' + str(ins.formapagopac.descripcion) + ' anulado por oficio de terminación de contrato.',
                                                            archivocontrato=contrato.archivocontrato,
                                                            persona=personasesion,
                                                            motivo_terminacion=contrato.motivo_terminacion)
                        detalle.save(request)

                        if ins.formapagopac.id == 2:
                            detalle = DetalleAprobacionContrato(contrato=contrato,
                                                                estado_aprobacion=5,
                                                                fecha_aprobacion=datetime.now(),
                                                                observacion='Pagaré anulado por oficio de terminación de contrato.',
                                                                archivocontrato=contrato.archivopagare,
                                                                persona=personasesion,
                                                                espagare=True,
                                                                motivo_terminacion=contrato.motivo_terminacion)
                            detalle.save(request)

                        if ins.vendido:
                            url = '/comercial?action=ventasobtenidas&s=' + ins.inscripcionaspirante.persona.cedula
                        else:
                            url = '/comercial?s=' + ins.inscripcionaspirante.persona.cedula

                        asunto = u"OFICIO DE TERMINACIÓN DE CONTRATO APROBADO"
                        observacion = f'Se le comunica que el oficio de terminación de contrato de {ins.formapagopac.descripcion} del admitido {ins.inscripcionaspirante.persona} con cédula {ins.inscripcionaspirante.persona.cedula} han aprobado. Por favor, dar seguimiento en la siguiente fase.'
                        para = ins.asesor.persona
                        perfiu = ins.asesor.perfil_administrativo()

                        notificacion3(asunto, observacion, para, None,
                                      url,
                                      ins.pk, 1,
                                      'sga', InscripcionCohorte, perfiu, request)

                        finan = Persona.objects.get(status=True, pk=24145)
                        para2 = finan
                        perfiu2 = finan.perfilusuario_administrativo()

                        if ins.tiene_matricula_cohorte():
                            url2 = '/comercial?action=leadsmatriculados&s=' + ins.inscripcionaspirante.persona.cedula
                        else:
                            if ins.formapagopac.id == 2:
                                url2 = '/comercial?s=' + ins.inscripcionaspirante.persona.cedula
                            else:
                                url2 = '/comercial?action=prospectoscontado&s=' + ins.inscripcionaspirante.persona.cedula

                        notificacion3(asunto, observacion, para2, None,
                                      url2,
                                      ins.pk, 1,
                                      'sga', InscripcionCohorte, perfiu2, request)

                        log(u'Aprobó oficio de terminación de contrato: %s' % contrato, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f"{ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}"})

        elif action == 'rechazaroficiomasivo':
            try:
                contratosselect = request.POST['id'].split(',')

                if contratosselect[0] != '':
                    for con in contratosselect:
                        contrato = Contrato.objects.get(status=True, pk=con)
                        contrato.estado = 6
                        contrato.save()
                        ins = InscripcionCohorte.objects.get(status=True, pk=contrato.inscripcion.id)

                        if contrato.ultima_evidenciaoficio().estado_aprobacion != 3:
                            detalle = DetalleAprobacionContrato(contrato=contrato,
                                                                estado_aprobacion=3,
                                                                fecha_aprobacion=datetime.now(),
                                                                observacion='Su oficio de terminación de contrato ha sido RECHAZADO.',
                                                                archivocontrato=contrato.archivooficio,
                                                                persona=personasesion,
                                                                esoficio=True,
                                                                motivo_terminacion=contrato.motivo_terminacion)
                            detalle.save(request)

                            if ins.vendido:
                                url = '/comercial?action=ventasobtenidas&s=' + ins.inscripcionaspirante.persona.cedula
                            else:
                                url = '/comercial?s=' + ins.inscripcionaspirante.persona.cedula

                            asunto = u"OFICIO DE TERMINACIÓN DE CONTRATO RECHAZADO"
                            observacion = f'Se le comunica que el oficio de terminación de contrato de {ins.formapagopac.descripcion} del admitido {ins.inscripcionaspirante.persona} con cédula {ins.inscripcionaspirante.persona.cedula} ha sido RECHAZADO.'
                            para = ins.asesor.persona
                            perfiu = ins.asesor.perfil_administrativo()

                            notificacion3(asunto, observacion, para, None,
                                          url,
                                          ins.pk, 1,
                                          'sga', InscripcionCohorte, perfiu, request)

                            finan = Persona.objects.get(status=True, pk=24145)
                            para2 = finan
                            perfiu2 = finan.perfilusuario_administrativo()

                            if ins.tiene_matricula_cohorte():
                                url2 = '/comercial?action=leadsmatriculados&s=' + ins.inscripcionaspirante.persona.cedula
                            else:
                                if ins.formapagopac.id == 2:
                                    url2 = '/comercial?s=' + ins.inscripcionaspirante.persona.cedula
                                else:
                                    url2 = '/comercial?action=prospectoscontado&s=' + ins.inscripcionaspirante.persona.cedula

                            notificacion3(asunto, observacion, para2, None,
                                          url2,
                                          ins.pk, 1,
                                          'sga', InscripcionCohorte, perfiu2, request)

                            log(u'Rechazó oficio de terminación de contrato: %s' % contrato, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f"{ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}"})

        elif action == 'aprobaroficioindividual':
            try:
                contrato = Contrato.objects.get(status=True, pk=int(request.POST['id']))
                contrato.estado = 5
                contrato.status = False
                contrato.save(request)

                ins = InscripcionCohorte.objects.get(status=True, pk=contrato.inscripcion.id)
                ins.puedeeditarmp = True
                ins.save(request)

                detalle = DetalleAprobacionContrato(contrato=contrato,
                                                    estado_aprobacion=2,
                                                    fecha_aprobacion=datetime.now(),
                                                    observacion='Su oficio de terminación de contrato ha sido aprobado, se procede con la anulación de su contrato actual.',
                                                    archivocontrato=contrato.archivooficio,
                                                    persona=personasesion,
                                                    esoficio=True,
                                                    motivo_terminacion=contrato.motivo_terminacion)
                detalle.save(request)

                detalle = DetalleAprobacionContrato(contrato=contrato,
                                                    estado_aprobacion=5,
                                                    fecha_aprobacion=datetime.now(),
                                                    observacion='Contrato de ' + str(ins.formapagopac.descripcion) + ' anulado por oficio de terminación de contrato.',
                                                    archivocontrato=contrato.archivocontrato,
                                                    persona=personasesion,
                                                    motivo_terminacion=contrato.motivo_terminacion)
                detalle.save(request)

                if ins.formapagopac.id == 2:
                    detalle = DetalleAprobacionContrato(contrato=contrato,
                                                        estado_aprobacion=5,
                                                        fecha_aprobacion=datetime.now(),
                                                        observacion='Pagaré anulado por oficio de terminación de contrato.',
                                                        archivocontrato=contrato.archivopagare,
                                                        persona=personasesion,
                                                        espagare=True,
                                                        motivo_terminacion=contrato.motivo_terminacion)
                    detalle.save(request)

                if ins.vendido:
                    url = '/comercial?action=ventasobtenidas&s=' + ins.inscripcionaspirante.persona.cedula
                else:
                    url = '/comercial?s=' + ins.inscripcionaspirante.persona.cedula

                asunto = u"OFICIO DE TERMINACIÓN DE CONTRATO APROBADO"
                observacion = f'Se le comunica que el oficio de terminación de contrato de {ins.formapagopac.descripcion} del admitido {ins.inscripcionaspirante.persona} con cédula {ins.inscripcionaspirante.persona.cedula} han aprobado. Por favor, dar seguimiento en la siguiente fase.'
                para = ins.asesor.persona
                perfiu = ins.asesor.perfil_administrativo()

                notificacion3(asunto, observacion, para, None,
                              url,
                              ins.pk, 1,
                              'sga', InscripcionCohorte, perfiu, request)

                finan = Persona.objects.get(status=True, pk=24145)
                para2 = finan
                perfiu2 = finan.perfilusuario_administrativo()

                if ins.tiene_matricula_cohorte():
                    url2 = '/comercial?action=leadsmatriculados&s=' + ins.inscripcionaspirante.persona.cedula
                else:
                    if ins.formapagopac.id == 2:
                        url2 = '/comercial?s=' + ins.inscripcionaspirante.persona.cedula
                    else:
                        url2 = '/comercial?action=prospectoscontado&s=' + ins.inscripcionaspirante.persona.cedula

                notificacion3(asunto, observacion, para2, None,
                              url2,
                              ins.pk, 1,
                              'sga', InscripcionCohorte, perfiu2, request)

                log(u'Aprobó oficio de terminación de contrato: %s' % contrato, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f"{ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}"})

        elif action == 'rechazaroficioindividual':
            try:
                contrato = Contrato.objects.get(status=True, pk=int(request.POST['id']))
                ins = InscripcionCohorte.objects.get(status=True, pk=contrato.inscripcion.id)
                contrato.estado = 6
                contrato.save()

                if contrato.ultima_evidenciaoficio().estado_aprobacion != 3:
                    detalle = DetalleAprobacionContrato(contrato=contrato,
                                                        estado_aprobacion=3,
                                                        fecha_aprobacion=datetime.now(),
                                                        observacion='Su oficio de terminación de contrato ha sido RECHAZADO.',
                                                        archivocontrato=contrato.archivooficio,
                                                        persona=personasesion,
                                                        esoficio=True,
                                                        motivo_terminacion=contrato.motivo_terminacion)
                    detalle.save(request)

                    if ins.vendido:
                        url = '/comercial?action=ventasobtenidas&s=' + ins.inscripcionaspirante.persona.cedula
                    else:
                        url = '/comercial?s=' + ins.inscripcionaspirante.persona.cedula

                    asunto = u"OFICIO DE TERMINACIÓN DE CONTRATO RECHAZADO"
                    observacion = f'Se le comunica que el oficio de terminación de contrato de {ins.formapagopac.descripcion} del admitido {ins.inscripcionaspirante.persona} con cédula {ins.inscripcionaspirante.persona.cedula} ha sido RECHAZADO.'
                    para = ins.asesor.persona
                    perfiu = ins.asesor.perfil_administrativo()

                    notificacion3(asunto, observacion, para, None,
                                  url,
                                  ins.pk, 1,
                                  'sga', InscripcionCohorte, perfiu, request)

                    finan = Persona.objects.get(status=True, pk=24145)
                    para2 = finan
                    perfiu2 = finan.perfilusuario_administrativo()

                    if ins.tiene_matricula_cohorte():
                        url2 = '/comercial?action=leadsmatriculados&s=' + ins.inscripcionaspirante.persona.cedula
                    else:
                        if ins.formapagopac.id == 2:
                            url2 = '/comercial?s=' + ins.inscripcionaspirante.persona.cedula
                        else:
                            url2 = '/comercial?action=prospectoscontado&s=' + ins.inscripcionaspirante.persona.cedula

                    notificacion3(asunto, observacion, para2, None,
                                  url2,
                                  ins.pk, 1,
                                  'sga', InscripcionCohorte, perfiu2, request)

                    log(u'Rechazó oficio de terminación de contrato: %s' % contrato, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f"{ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}"})

        elif action == 'imprimir_contratoserror':
            try:
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('reporte_contratos')
                response = HttpResponse(content_type="application/ms-excel")
                columns = [
                    (u"N.", 1500),
                    (u"CÉDULA", 4000),
                    (u"MAESTRANTE", 12000),
                    (u"MAESTRÍA", 14000),
                    (u"COHORTE", 12000),
                    (u"NOMBRE DE FIRMA", 6000),
                    (u"TIPO CONTRATO", 6000),
                    (u"ESTADO", 6000),
                ]

                response['Content-Disposition'] = 'attachment; filename=reporte_contratos' + random.randint(1, 10000).__str__() + '.xls'
                style_title = xlwt.easyxf(
                    'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                style_title_2 = xlwt.easyxf(
                    'font: height 250, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                ws.write_merge(0, 0, 0, len(columns), 'UNIVERSIDAD ESTATAL DE MILAGRO', style_title)
                ws.write_merge(1, 1, 0, len(columns),
                               'LISTADO DE CONTRATOS DE PAGO',
                               style_title_2)
                row_num = 3
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                    ws.col(col_num).width = columns[col_num][1]
                date_format = xlwt.XFStyle()
                date_format.num_format_str = 'yyyy/mm/dd'

                maestria = cohorte = estadof = 0
                filtros, s, m = Q(status=True, estado=2), request.POST.get('s', ''), request.POST.get('m', '0')
                if s:
                    ss = s.split(' ')
                    if len(ss) == 1:
                        filtros = filtros & (
                                Q(inscripcion__inscripcionaspirante__persona__nombres__icontains=s) |
                                Q(inscripcion__inscripcionaspirante__persona__apellido1__icontains=s) |
                                Q(inscripcion__inscripcionaspirante__persona__apellido2__icontains=s) |
                                Q(inscripcion__inscripcionaspirante__persona__cedula__icontains=s) |
                                Q(inscripcion__inscripcionaspirante__persona__pasaporte__icontains=s) |
                                Q(numerocontrato__icontains=s)
                        )
                    else:
                        filtros = filtros & (Q(inscripcion__inscripcionaspirante__persona__apellido1__icontains=ss[0]) & Q(inscripcion__inscripcionaspirante__persona__apellido2__icontains=ss[1]))
                if 'maestria' in request.POST:
                    maestria = int(request.POST['maestria'])
                if 'cohorte' in request.POST:
                    cohorte = int(request.POST['cohorte'])
                if 'estadof' in request.POST:
                    estadof = int(request.POST['estadof'])
                if int(m):
                    filtros = filtros & (Q(inscripcion__formapagopac_id=m))
                if maestria > 0:
                    filtros = filtros & Q(inscripcion__cohortes__maestriaadmision__id=maestria)
                if cohorte > 0:
                    filtros = filtros & Q(inscripcion__cohortes__id=cohorte)
                if estadof > 0:
                    if estadof == 1:
                        ban = True
                    else:
                        ban = False
                    filtros = filtros & Q(contratolegalizado=ban)

                contratos = Contrato.objects.filter(filtros)
                row_num = 4

                for i, contrato in enumerate(contratos):
                    campo1 = str(contrato.inscripcion.inscripcionaspirante.persona.cedula) if contrato.inscripcion.inscripcionaspirante.persona.cedula else str(contrato.inscripcion.inscripcionaspirante.persona.pasaporte)
                    campo2 = str(contrato.inscripcion.inscripcionaspirante)
                    campo3 = str(contrato.inscripcion.cohortes.maestriaadmision)
                    campo4 = str(contrato.inscripcion.cohortes.descripcion)
                    campo5 = nombre_firma_dr_incorrecto(contrato)
                    campo6 = ''
                    resp = contrato.contrato_acorde_formapago()
                    if resp == True:
                        campo6 = 'CORRECTO'
                    elif resp == False:
                        campo6 = 'INCORRECTO'
                    else:
                        campo6 = ' - '
                    campo7 = 'FIRMADO' if contrato.contratolegalizado else 'PENDIENTE'

                    ws.write(row_num, 0, i+1, font_style2)
                    ws.write(row_num, 1, campo1, font_style2)
                    ws.write(row_num, 2, campo2, font_style2)
                    ws.write(row_num, 3, campo3, font_style2)
                    ws.write(row_num, 4, campo4, font_style2)
                    ws.write(row_num, 5, campo5, font_style2)
                    ws.write(row_num, 6, campo6, font_style2)
                    ws.write(row_num, 7, campo7, font_style2)

                    row_num += 1
                wb.save(response)
                return response
            except Exception as ex:
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg = ex.__str__()
                msg = f'{msg} {err}'

                return JsonResponse({"result": "bad", "mensaje": u"Error: %s"%msg})

        elif action == 'pdfactagradoposgrado':
            try:
                titulacion = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['id'])
                if not titulacion.documentotitulacionposgrado_set.values('id').filter(status=True).exists():
                    pdfname, qrresult = actagradoposgrado2(request.POST['id'])
                    instance = DocumentoTitulacionPosgrado(tematitulacionposgrado=titulacion,
                                                           tipodocumentotitulacion_id=1,
                                                           estadodocumentotitulacion_id=1,
                                                           fecha=hoy)
                    instance.save(request)
                    instance.archivo.name = pdfname
                    instance.save(request)
                    historial = HistorialDocumentoTitulacionPosgrado(documentotitulacion=instance,
                                                                     estadodocumentotitulacion_id=1,
                                                                     fecha=hoy)
                    historial.save(request)
                    historial.archivo.name = pdfname
                    historial.save(request)
                else:
                    res = titulacion.archivo_evidencia()
                    qrresult = 'http://127.0.0.1:8000' + res.url
                return JsonResponse({"result": "ok", 'url': qrresult})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar documento."})

        elif action == 'pdfactagradoposgradocomplexivo':
            try:
                titulacion = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['id'])
                if not titulacion.documentotitulacionposgrado_set.values('id').filter(status=True).exists():
                    pdfname, qrresult = actagradoposgradocomplexivo2(request.POST['id'])
                    instance = DocumentoTitulacionPosgrado(tematitulacionposgrado=titulacion,
                                                           tipodocumentotitulacion_id=2,
                                                           estadodocumentotitulacion_id=1,
                                                           fecha=hoy)
                    instance.save(request)
                    instance.archivo.name = pdfname
                    instance.save(request)
                    historial = HistorialDocumentoTitulacionPosgrado(documentotitulacion=instance,
                                                                     estadodocumentotitulacion_id=1,
                                                                     fecha=hoy)
                    historial.save(request)
                    historial.archivo.name = pdfname
                    historial.save(request)
                else:
                    res = titulacion.archivo_evidencia()
                    qrresult = 'http://127.0.0.1:8000' + res.url
                return JsonResponse({"result": "ok", 'url': qrresult})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar documento."})


        elif action == 'firmaractagradoindividual':
            try:
                from sga.funciones import notificacion
                titulacion = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['idtitulacion'])
                cargofirma = EstadoDocumentoTitulacionPosgrado.objects.get(pk=request.POST['cargofirma'])
                if titulacion.ultima_evidencia_titulacion():
                    pdf = titulacion.archivo_evidencia()
                    #obtener la posicion xy de la firma del doctor en el pdf
                    pdfname = SITE_STORAGE + titulacion.archivo_evidencia().url
                    palabras = cargofirma.nombrefirma+'\n'+cargofirma.descripcion
                    posx, posy, numpaginafirma = obtener_posicion_x_y(pdf.url, palabras)
                    if not posx and not posy:
                        messages.warning(request, "Alerta: El nombre en la firma del contrato no es el correcto.")
                        return JsonResponse({"result": "errornombre"})
                    #fin obtener posicion
                    firma = request.FILES["firma"]
                    passfirma = request.POST['palabraclave']
                    txtFirmas = json.loads(request.POST['txtFirmas'])
                    if not txtFirmas:
                        return JsonResponse({"result": "bad", "mensaje": u"No se ha podido seleccionar la ubicación de la firma"})
                    generar_archivo_firmado = io.BytesIO()
                    x = txtFirmas[-1]
                    datau, datas = firmar(request, passfirma, firma, pdf, numpaginafirma, posx, posy, x["width"], x["height"])
                    if not datau:
                        return JsonResponse({"result": "bad", "mensaje": f"{datas}"})
                    generar_archivo_firmado.write(datau)
                    generar_archivo_firmado.write(datas)
                    generar_archivo_firmado.seek(0)
                    extension = pdf.name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    nombrefile_ = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(pdf.name)).replace('-', '_').replace('.pdf', '')
                    _name = 'actagrado'+str(titulacion.id)
                    file_obj = DjangoFile(generar_archivo_firmado, name=f"{_name}_firmado.pdf")

                    instance = titulacion.ultima_evidencia_titulacion()
                    instance.estadodocumentotitulacion_id = 2
                    instance.archivo = file_obj
                    instance.save(request)
                    historial = HistorialDocumentoTitulacionPosgrado(documentotitulacion=instance,
                                                                     estadodocumentotitulacion_id=2,
                                                                     persona=personasesion,
                                                                     archivo=file_obj,
                                                                     fecha=hoy)
                    historial.save(request)
                    cuerpo = ('Documento firmado con éxito: %s' % titulacion.matricula.inscripcion)
                    notificacion('Firma electrónica SGA',
                                 cuerpo, personasesion, None,
                                 '/firmardocumentosposgrado?action=firmaactagrado&s=%s'%(titulacion.matricula.inscripcion.persona.cedula),
                                 titulacion.pk, 1, 'sga', titulacion, request)

                    messages.success(request, f'Documento firmado con éxito')
                    log(u'Firmo Documento: {}'.format(nombrefile_), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s"%ex})

        elif action == 'firmaractagradomasivo':
            try:
                from sga.funciones import notificacion
                cargofirma = EstadoDocumentoTitulacionPosgrado.objects.get(pk=request.POST['cargofirma'])
                firma = request.FILES["firma"]
                passfirma = request.POST['palabraclave']
                datosselect = request.POST['ids'].split(',')
                bandera = False
                p12 = None
                listainscripcion = []
                nombresmae = ''
                conterrornombre = 0
                conteoerror = 0
                for a in datosselect:
                    titulacion = TemaTitulacionPosgradoMatricula.objects.get(pk=a)
                    if titulacion.ultima_evidencia_titulacion():
                        # obtener la posicion xy de la firma del doctor en el pdf
                        pdf = titulacion.archivo_evidencia()
                        pdfname = SITE_STORAGE + titulacion.archivo_evidencia().url
                        palabras = cargofirma.descripcion
                        posx, posy, numpaginafirma = obtener_posicion_x_y(pdf.url, palabras)
                        # FIN obtener la posicion y
                        if posx and posy:
                            generar_archivo_firmado = io.BytesIO()
                            datau, datas, p12 = firmarmasivo(request, p12, bandera, passfirma, firma, pdf, numpaginafirma, posx, posy, 150, 45)
                            if p12:
                                bandera = True
                            if not datau:
                                return JsonResponse({"result": "bad", "mensaje": f"{datas}"})
                            if datau:
                                generar_archivo_firmado.write(datau)
                                generar_archivo_firmado.write(datas)
                                generar_archivo_firmado.seek(0)
                                extension = pdf.name.split('.')
                                tam = len(extension)
                                exte = extension[tam - 1]
                                nombrefile_ = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(pdf.name)).replace('-', '_').replace('.pdf', '')
                                _name = 'actagrado'+str(titulacion.id)
                                file_obj = DjangoFile(generar_archivo_firmado, name=f"{_name}_firmado.pdf")

                                instance = titulacion.ultima_evidencia_titulacion()
                                instance.estadodocumentotitulacion_id = 2
                                instance.archivo = file_obj
                                instance.save(request)
                                historial = HistorialDocumentoTitulacionPosgrado(documentotitulacion=instance,
                                                                                 estadodocumentotitulacion_id=2,
                                                                                 persona=personasesion,
                                                                                 archivo=file_obj,
                                                                                 fecha=hoy)
                                historial.save(request)
                                log(u'Masivo Firmó Documento: {}'.format(nombrefile_), request, "add")
                                listainscripcion.append(titulacion.matricula.inscripcion.id)
                                nombresmae += '%s, '%titulacion.matricula.inscripcion
                            else:
                                conteoerror += 1
                        else:
                            conteoerror += 1
                            conterrornombre += 1
                cuerpo = ('Documentos firmados con éxito: %s' % nombresmae)
                notificacion('Firma electrónica SGA', cuerpo, personasesion, None, '/firmardocumentosposgrado?action=firmaactagrado', None, 1, 'sga', titulacion, request)

                if listainscripcion:
                    if conteoerror > 0:
                        messages.success(request, f'Documentos firmados con éxito. %s' % ('Existieron %s actas con inconsistencia que no fueron firmados. %s' % (conteoerror, conterrornombre) if conterrornombre > 0 else ''))
                    else:
                        messages.success(request, f'Documentos firmados con éxito')
                else:
                    if conteoerror > 0:
                        messages.warning(request, f'%s' % ('Existieron %s actas con inconsistencia que no fueron firmados. %s' % (conteoerror, conterrornombre) if conterrornombre > 0 else ''))
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s"%ex})

        elif action == 'addtipodocumento':
            try:
                with transaction.atomic():
                    form = TipoDocumentoTitulacionForm(request.POST)
                    if form.is_valid():
                        if not TipoDocumentoTitulacionPosgrado.objects.values('id').filter(descripcion=form.cleaned_data['descripcion']).exists():
                            instance = TipoDocumentoTitulacionPosgrado(descripcion=form.cleaned_data['descripcion'])
                            instance.save(request)
                            log(u'Adicionó Tipo Documento Titulacion: %s' % instance, request, "add")
                            messages.success(request, 'Registro guardado con éxito.')
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            raise NameError(u'El registro ya existe.')
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'edittipodocumento':
            try:
                with transaction.atomic():
                    filtro = TipoDocumentoTitulacionPosgrado.objects.get(pk=int(encrypt(request.POST['id'])))
                    f = TipoDocumentoTitulacionForm(request.POST)
                    if f.is_valid():
                        if (f.cleaned_data['descripcion'],) in TipoDocumentoTitulacionPosgrado.objects.values_list('descripcion').filter(status=True).exclude(pk=filtro.id):
                            raise NameError(u'El resgistro ya existe.')
                        filtro.descripcion = f.cleaned_data['descripcion']
                        filtro.save(request)
                        log(u'Editó Tipo Documento Titulacion: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'deltipodocumento':
            try:
                with transaction.atomic():
                    instancia = TipoDocumentoTitulacionPosgrado.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó Tipo Documento Titulacion: %s' % instancia, request, "delete")
                    messages.success(request, 'Registro eliminado con éxito.')
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addestadodocumento':
            try:
                with transaction.atomic():
                    form = EstadoDocumentoTitulacionForm(request.POST)
                    if form.is_valid():
                        if not EstadoDocumentoTitulacionPosgrado.objects.values('id').filter(descripcion=form.cleaned_data['descripcion']).exists():
                            instance = EstadoDocumentoTitulacionPosgrado(descripcion=form.cleaned_data['descripcion'],
                                                                         nombrefirma=form.cleaned_data['nombrefirma'],
                                                                         orden=form.cleaned_data['orden'],
                                                                         habilitado=form.cleaned_data['habilitado'])
                            instance.save(request)
                            log(u'Adicionó Estado Documento Titulacion: %s' % instance, request, "add")
                            messages.success(request, 'Registro guardado con éxito.')
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            raise NameError(u'El registro ya existe.')
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'editestadodocumento':
            try:
                with transaction.atomic():
                    filtro = EstadoDocumentoTitulacionPosgrado.objects.get(pk=int(encrypt(request.POST['id'])))
                    f = EstadoDocumentoTitulacionForm(request.POST)
                    if f.is_valid():
                        if (f.cleaned_data['descripcion'],) in EstadoDocumentoTitulacionPosgrado.objects.values_list('descripcion').filter(status=True).exclude(pk=filtro.id):
                            raise NameError(u'El resgistro ya existe.')
                        filtro.descripcion = f.cleaned_data['descripcion']
                        filtro.nombrefirma = f.cleaned_data['nombrefirma']
                        filtro.orden = f.cleaned_data['orden']
                        filtro.habilitado = f.cleaned_data['habilitado']
                        filtro.save(request)
                        log(u'Editó Estado Documento Titulacion: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'delestadodocumento':
            try:
                with transaction.atomic():
                    instancia = EstadoDocumentoTitulacionPosgrado.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó Estado Documento Titulacion: %s' % instancia, request, "delete")
                    messages.success(request, 'Registro eliminado con éxito.')
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'revision_expediente_vicerrectorado':
            try:
                with transaction.atomic():
                    instancia = ExpedienteContratacion.objects.get(pk=int(request.POST['id']))
                    form = RevisionExpedienteForm(request.POST)
                    if form.is_valid():
                        instancia.revisado_vicerrectorado = True
                        instancia.observacion_vicerrectorado = form.cleaned_data['observacion']
                        instancia.estado_aprobacion_vicerrectorado = 2 if json.loads(request.POST['aprobacion']) == True else 3
                        instancia.save(request)
                        estado_aprobacion = "aprobado" if json.loads(request.POST['aprobacion']) == True else 'rechazado'
                        log(f'Realizó la revisión {estado_aprobacion} expediente vicerrectorado: %s' % instancia, request, "edit")
                        messages.success(request, 'Revisión guardada con éxito.')
                        return JsonResponse({"result": True}, safe=False)
                    else:
                        return JsonResponse({'result': False, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)

        elif action == 'firmar_acta_grado_por_archivo':
            try:
                persona = request.session.get('persona')
                observacion = f'Acta de grado firmado por {persona}'
                pk = request.POST.get('id', '0')
                if pk == 0:
                    raise NameError("Parametro no encontrado")
                eTemaTitulacionPosgradoMatricula = TemaTitulacionPosgradoMatricula.objects.get(pk=pk)
                if variable_valor("FIRMAR_ACTAS_EN_ORDEN"):
                    puede, mensaje = eTemaTitulacionPosgradoMatricula.puede_firmar_integrante_segun_orden(persona)
                else:
                    puede, mensaje= eTemaTitulacionPosgradoMatricula.integrante_ya_firmo(persona)

                if puede:
                    integrante = eTemaTitulacionPosgradoMatricula.get_integrante(persona)
                    pdf = eTemaTitulacionPosgradoMatricula.get_documento_informe()
                    palabras = u"%s" % integrante.persona.nombres
                    firma = request.FILES.get("firma")
                    passfirma = request.POST.get('palabraclave')
                    bytes_certificado = firma.read()
                    extension_certificado = os.path.splitext(firma.name)[1][1:]
                    x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(pdf.url, palabras)
                    datau = JavaFirmaEc(
                        archivo_a_firmar=pdf, archivo_certificado=bytes_certificado,
                        extension_certificado=extension_certificado,
                        password_certificado=passfirma,
                        page=int(numpaginafirma), reason='', lx=x + 50, ly=y + 20
                    ).sign_and_get_content_bytes()

                    documento_a_firmar = io.BytesIO()
                    documento_a_firmar.write(datau)
                    documento_a_firmar.seek(0)
                    orden_firma = f'_firm_orden_{str(integrante.ordenfirma.orden)}'
                    eTemaTitulacionPosgradoMatricula.get_documento_informe().save(f'{eTemaTitulacionPosgradoMatricula.get_documento_informe().name.split("/")[-1].replace(".pdf", "")}{orden_firma}.pdf', ContentFile(documento_a_firmar.read()))
                    integrante.firmo =True
                    integrante.save(request)
                    eTemaTitulacionPosgradoMatricula.estado_firmas_acta_graduado = integrante.ordenfirma.orden
                    eTemaTitulacionPosgradoMatricula.save(request)

                    eTemaTitulacionPosgradoMatricula.guardar_historial_firma_titulacion_pos_mat(request, observacion, eTemaTitulacionPosgradoMatricula.get_documento_informe())
                    log(u"Firmo Acta de grado", request, 'edit')

                    if integrante.ordenfirma.orden == 2:
                        if variable_valor('NOTI_FIRMA_ACTA_GRADO_RECTOR'):
                            eTemaTitulacionPosgradoMatricula.notificar_integrante_acta_de_grado_generada(request)
                    else:
                        eTemaTitulacionPosgradoMatricula.notificar_integrante_acta_de_grado_generada(request)
                else:
                    raise NameError(f"{mensaje}")

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s" % ex})

        elif action == 'firmar_acta_grado_masivo':
            try:
                def divide_list(lst, n):
                    # Genera sublistas de tamaño n
                    for i in range(0, len(lst), n):
                        yield lst[i:i + n]
                numero_de_intentos_global= 1
                passfirma = request.POST['palabraclave']
                firma = request.FILES["firma"]
                list_id_actas = request.POST['ids'].split(',')
                conteoerror_general = 0
                listactasfirmdas_general = []
                conteoerrorturno_general = 0
                actas_no_firmadas_general = []
                persona = request.session.get('persona')

                def procesar_lote_documentos_actas_de_grado(actas):
                    conteoerror = 0
                    conteoerrorturno = 0
                    for acta_id in actas:
                        observacion = f'Acta de grado firmado por {persona}'
                        eTemaTitulacionPosgradoMatricula = TemaTitulacionPosgradoMatricula.objects.filter(pk=acta_id)[0]

                        if variable_valor("FIRMAR_ACTAS_EN_ORDEN"):
                            puede, mensaje = eTemaTitulacionPosgradoMatricula.puede_firmar_integrante_segun_orden( persona)
                        else:
                            puede, mensaje = eTemaTitulacionPosgradoMatricula.integrante_ya_firmo(persona)

                        if puede:
                            integrante = eTemaTitulacionPosgradoMatricula.get_integrante(persona)
                            pdf = eTemaTitulacionPosgradoMatricula.get_documento_informe()
                            palabras = u"%s" % integrante.persona.nombres
                            firma.seek(0)
                            bytes_certificado = firma.read()
                            extension_certificado = os.path.splitext(firma.name)[1][1:]
                            x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(pdf.url, palabras)
                            if y and x:
                                datau = JavaFirmaEc(
                                    archivo_a_firmar=pdf, archivo_certificado=bytes_certificado,
                                    extension_certificado=extension_certificado,
                                    password_certificado=passfirma,
                                    page=int(numpaginafirma), reason='', lx=x + 50, ly=y + 20
                                ).sign_and_get_content_bytes()
                                if datau:
                                    documento_a_firmar = io.BytesIO()
                                    documento_a_firmar.write(datau)
                                    documento_a_firmar.seek(0)
                                    orden_firma = f'_firm_orden_{str(integrante.ordenfirma.orden)}'
                                    eTemaTitulacionPosgradoMatricula.get_documento_informe().save(
                                        f'{eTemaTitulacionPosgradoMatricula.get_documento_informe().name.split("/")[-1].replace(".pdf", "")}{orden_firma}.pdf',
                                        ContentFile(documento_a_firmar.read()))
                                    integrante.firmo = True
                                    integrante.save(request)
                                    eTemaTitulacionPosgradoMatricula.estado_firmas_acta_graduado = integrante.ordenfirma.orden
                                    eTemaTitulacionPosgradoMatricula.save(request)

                                    eTemaTitulacionPosgradoMatricula.guardar_historial_firma_titulacion_pos_mat(
                                        request,
                                        observacion,
                                        eTemaTitulacionPosgradoMatricula.get_documento_informe())
                                    log(u"Firmo Acta de grado", request, 'edit')
                                    listactasfirmdas_general.append(eTemaTitulacionPosgradoMatricula.id)
                                else:
                                    conteoerror += 1
                                    actas_no_firmadas_general.append(acta_id)
                            else:
                                conteoerror += 1
                                actas_no_firmadas_general.append(acta_id)
                        else:
                            conteoerrorturno += 1
                            actas_no_firmadas_general.append(acta_id)
                    return conteoerror,conteoerrorturno

                for sublist in divide_list(list_id_actas, 10):
                    conteoerror,conteoerrorturno = procesar_lote_documentos_actas_de_grado(sublist)
                    time.sleep(1)
                reintento = 1
                if actas_no_firmadas_general:
                    while reintento <= numero_de_intentos_global:
                        for sublist in divide_list(actas_no_firmadas_general, 10):
                            conteoerror, conteoerrorturno = procesar_lote_documentos_actas_de_grado(sublist)
                            if reintento == 1:
                                conteoerror_general +=conteoerror
                                conteoerrorturno_general +=conteoerrorturno
                        reintento += 1




                mensaje = f'{len(listactasfirmdas_general)} Documento(s) firmado(s) correctamente.'

                if conteoerrorturno_general > 0:
                    mensaje += f'. {conteoerrorturno_general} Documento(s) no fueron firmadas por no ser su turno.'

                if conteoerror_general > 0:
                    mensaje += f'. {conteoerror_general} Documento(s) con inconsistencia no fueron firmadas.'

                if listactasfirmdas_general:
                    messages.success(request, mensaje)
                    actas = TemaTitulacionPosgradoMatricula.objects.filter(id__in=listactasfirmdas_general)

                    for acta in actas:
                        if variable_valor("FIRMAR_ACTAS_EN_ORDEN"):
                            listpersonasanotificar = []
                            intengrantedebefirmar = acta.get_debe_firmar()
                            if intengrantedebefirmar:
                                if intengrantedebefirmar.persona not in listpersonasanotificar:
                                    listpersonasanotificar.append(intengrantedebefirmar.persona)
                            if listpersonasanotificar:
                                for persona in listpersonasanotificar:
                                    titulonotificacion = f"ACTAS DE GRADO PENDIENTES DE FIRMAR"
                                    cuerponotificacion = f"Se han generado actas de grado y es su turno de firmar los documentos, favor revisar."
                                    url = f"https://sga.unemi.edu.ec/firmardocumentosposgrado?action=firmaactagrado"
                                    notificacion = Notificacion(
                                        titulo=titulonotificacion,
                                        cuerpo=cuerponotificacion,
                                        destinatario=persona,
                                        url=url,
                                        content_type=None,
                                        object_id=None,
                                        prioridad=1,
                                        app_label='SGA',
                                        fecha_hora_visible=datetime.now() + timedelta(days=3))
                                    notificacion.save(request)
                        else:
                            integrantes = acta.get_integrantes_firman().exclude(firmo=True)

                            for integrante in integrantes:
                                titulonotificacion = f"ACTAS DE GRADO PENDIENTES DE FIRMAR"
                                cuerponotificacion = f"Se han generado actas de grado y es su turno de firmar los documentos, favor revisar."
                                url = f"https://sga.unemi.edu.ec/firmardocumentosposgrado?action=firmaactagrado"
                                notificacion = Notificacion(
                                    titulo=titulonotificacion,
                                    cuerpo=cuerponotificacion,
                                    destinatario=integrante.persona,
                                    url=url,
                                    content_type=None,
                                    object_id=None,
                                    prioridad=1,
                                    app_label='SGA',
                                    fecha_hora_visible=datetime.now() + timedelta(days=3))
                                notificacion.save(request)
                else:
                    if conteoerror_general > 0:
                        messages.warning(request, f'Existieron {conteoerror_general} Documento(s) con inconsistencia que no fueron firmadas.')

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s" % ex})

        elif action == 'firmar_acta_grado_por_token':
            try:
                persona = request.session.get('persona')
                observacion = f'Informe de contratación firmado por {persona}'
                pk = request.POST.get('id', '0')
                if pk == 0:
                    raise NameError("Parametro no encontrado")

                eTemaTitulacionPosgradoMatricula = TemaTitulacionPosgradoMatricula.objects.get(pk=pk)

                if variable_valor("FIRMAR_ACTAS_EN_ORDEN"):
                    puede, mensaje = eTemaTitulacionPosgradoMatricula.puede_firmar_integrante_segun_orden(persona)
                else:
                    puede, mensaje = eTemaTitulacionPosgradoMatricula.integrante_ya_firmo(persona)


                if puede:
                    integrante = eTemaTitulacionPosgradoMatricula.get_integrante(persona)
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
                                    _name = generar_nombre(f"{eTemaTitulacionPosgradoMatricula.get_documento_informe().__str__().split('/')[-1].replace('.pdf', '_')}", '')
                                    _name = remover_caracteres_tildes_unicode( remover_caracteres_especiales_unicode(_name)).lower().replace(' ', '_').replace('-','_')
                                    newfile._name = f"{_name}.pdf"

                                    # orden_firma = f'_firm_orden_{integrante.ordenfirma.orden}'
                                    # eTemaTitulacionPosgradoMatricula.get_documento_informe().save(
                                    #     f'{eTemaTitulacionPosgradoMatricula.get_documento_informe().name.split("/")[-1].replace(".pdf", "")}{orden_firma}.pdf',
                                    #     newfile)

                                    eTemaTitulacionPosgradoMatricula.archivo_acta_grado = newfile
                                    eTemaTitulacionPosgradoMatricula.save(request)

                                    eTemaTitulacionPosgradoMatricula.guardar_historial_firma_titulacion_pos_mat(request,
                                                                                                                observacion,
                                                                                                                eTemaTitulacionPosgradoMatricula.get_documento_informe())


                                    integrante.firmo = True
                                    integrante.save(request)
                                    eTemaTitulacionPosgradoMatricula.estado_firmas_acta_graduado = integrante.ordenfirma.orden
                                    eTemaTitulacionPosgradoMatricula.save(request)

                                    eTemaTitulacionPosgradoMatricula.guardar_historial_firma_titulacion_pos_mat(request,
                                                                                                                observacion,
                                                                                                                eTemaTitulacionPosgradoMatricula.get_documento_informe())
                                    # eInformeContratacion.actualizar_estado_del_informe_de_contratacion(request)
                                    log(u"Firmo Acta de grado", request, 'edit')
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivos PDF"})

                else:
                    raise NameError(f"{mensaje}")


                return JsonResponse({"result": "ok"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s" % ex})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Listado de inscripciones'
        persona = request.session['persona']
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'firmaelectronicacontratos':
                try:
                    data['title'] = 'Documentos de posgrado'
                    maestria = cohorte = estadof = cantidad = estadoegre = 0
                    bandera = False
                    idescuela = 0
                    s, m, url_vars = request.GET.get('s', ''), request.GET.get('m', '0'), ''

                    if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True, personadepartamento=persona,
                                                                tipopersonadepartamento_id=9, departamento_id=216).exists():
                        filtros = Q(status=True, estado=2, inscripcion__status=True,
                                    inscripcion__cohortes__maestriaadmision__carrera__escuelaposgrado_id=1)
                        idescuela = 1
                    elif PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True, personadepartamento=persona,
                                                                tipopersonadepartamento_id=10, departamento_id=215).exists():
                        filtros = Q(status=True, estado=2, inscripcion__status=True,
                                    inscripcion__cohortes__maestriaadmision__carrera__escuelaposgrado_id=2)
                        idescuela = 2
                    elif PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True, personadepartamento=persona,
                                                                tipopersonadepartamento_id=11, departamento_id=163).exists():
                        filtros = Q(status=True, estado=2, inscripcion__status=True,
                                    inscripcion__cohortes__maestriaadmision__carrera__escuelaposgrado_id=3)
                        idescuela = 3
                    else:
                        filtros = Q(status=True, estado=2, inscripcion__status=True)

                    cohortes = None
                    if 'maestria' in request.GET:
                        maestria = int(request.GET['maestria'])
                    if 'cohorte' in request.GET:
                        cohorte = int(request.GET['cohorte'])
                    if 'estadof' in request.GET:
                        estadof = int(request.GET['estadof'])
                    if 'estadoegre' in request.GET:
                        estadoegre = int(request.GET['estadoegre'])

                    if not cantidad:
                        cantidad = 25

                    if s:
                        ss = s.split(' ')
                        if len(ss) == 1:
                            filtros = filtros & (
                                                 Q(inscripcion__inscripcionaspirante__persona__nombres__icontains=s) |
                                                 Q(inscripcion__inscripcionaspirante__persona__apellido1__icontains=s) |
                                                 Q(inscripcion__inscripcionaspirante__persona__apellido2__icontains=s) |
                                                 Q(inscripcion__inscripcionaspirante__persona__cedula__icontains=s) |
                                                 Q(inscripcion__inscripcionaspirante__persona__pasaporte__icontains=s) |
                                                 Q(numerocontrato__icontains=s)
                                                 )
                            data['s'] = f"{s}"
                            url_vars += f"&s={s}"
                        else:
                            filtros = filtros & (Q(inscripcion__inscripcionaspirante__persona__apellido1__icontains=ss[0]) & Q(inscripcion__inscripcionaspirante__persona__apellido2__icontains=ss[1]))
                            data['s'] = f"{s}"
                            url_vars += f"&s={s}"

                    if int(m):
                        filtros = filtros & (Q(inscripcion__formapagopac_id=m))
                        data['m'] = f"{m}"
                        url_vars += f"&m={m}"
                        bandera = True

                    if maestria > 0:
                        data['maestria'] = maestria
                        filtros = filtros & Q(inscripcion__cohortes__maestriaadmision__id=maestria)
                        cohortes = CohorteMaestria.objects.filter(maestriaadmision__id=maestria)
                        url_vars += "&maestria={}".format(maestria)
                        bandera = True

                    if cohorte > 0:
                        data['cohorte'] = cohorte
                        filtros = filtros & Q(inscripcion__cohortes__id=cohorte)
                        url_vars += "&cohorte={}".format(cohorte)
                        bandera = True

                    if estadof > 0:
                        data['estadof'] = estadof
                        if estadof == 1:
                            ban = True
                        else:
                            ban = False
                        filtros = filtros & Q(contratolegalizado=ban)
                        url_vars += "&estadof={}".format(estadof)
                        bandera = True

                    if estadoegre > 0:
                        data['estadoegre'] = estadoegre
                        if estadoegre == 1:
                            listc = Contrato.objects.filter(filtros).values_list('inscripcion__inscripcion__id', flat=True).order_by('inscripcion__inscripcion__id').distinct()
                            idgra = Graduado.objects.filter(inscripcion__id__in=listc).values_list('inscripcion__id', flat=True).distinct()
                            idins = TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula__inscripcion__id__in=listc).exclude(matricula__inscripcion__id__in=idgra).values_list('matricula__inscripcion__id', flat=True).order_by('matricula__inscripcion__id').distinct()
                            filtros = filtros & Q(inscripcion__inscripcion__id__in=idins)
                        elif estadoegre == 2:
                            listc = Contrato.objects.filter(filtros).values_list('inscripcion__inscripcion__id', flat=True).order_by('inscripcion__inscripcion__id').distinct()
                            idgra = Graduado.objects.filter(inscripcion__id__in=listc).values_list('inscripcion__id', flat=True).distinct()
                            idins = TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula__inscripcion__id__in=listc).exclude(matricula__inscripcion__id__in=idgra).values_list('matricula__inscripcion__id', flat=True).order_by('matricula__inscripcion__id').distinct()
                            idto = idgra.union(idins)
                            idreal = Contrato.objects.filter(filtros).values_list('inscripcion__inscripcion__id', flat=True).exclude(inscripcion__inscripcion__id__in=idto).order_by('inscripcion__inscripcion__id').distinct()
                            filtros = filtros & Q(inscripcion__inscripcion__id__in=idreal)
                        elif estadoegre == 3:
                            listc = Contrato.objects.filter(filtros).values_list('inscripcion__inscripcion__id', flat=True).order_by('inscripcion__inscripcion__id').distinct()
                            idgra = Graduado.objects.filter(inscripcion__id__in=listc).values_list('inscripcion__id', flat=True).distinct()
                            filtros = filtros & Q(inscripcion__inscripcion__id__in=idgra)

                        url_vars += "&estadoegre={}".format(estadoegre)
                        bandera = True

                    listcontratos = Contrato.objects.filter(filtros).order_by('-fechacontrato','-contratolegalizado')

                    paging = MiPaginador(listcontratos, 15)
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
                    data['contratos'] = page.object_list
                    data['url_vars'] = url_vars
                    if idescuela > 0:
                        data['maestrialist'] = MaestriasAdmision.objects.filter(status=True, carrera__coordinacion__id=7, carrera__escuelaposgrado_id=idescuela, pk__in=Contrato.objects.values_list('inscripcion__cohortes__maestriaadmision__id').filter(status=True, estado=2))
                    else:
                        data['maestrialist'] = MaestriasAdmision.objects.filter(status=True, carrera__coordinacion__id=7, pk__in=Contrato.objects.values_list('inscripcion__cohortes__maestriaadmision__id').filter(status=True, estado=2))
                    data['cohorteslist'] = cohortes
                    data['canti'] = listcontratos.count()
                    data['count'] = Contrato.objects.filter(filtros).values('id').count()
                    # data['modulos'] = HistorialReservacionProspecto.objects.values_list('modulo_id', 'modulo__nombre', 'modulo__url').filter(status=True).distinct()
                    data['modulos'] = modulos = Contrato.objects.values_list('formapago_id', 'formapago__descripcion').filter(status=True).distinct().exclude(formapago=None).order_by('formapago_id')
                    return render(request, "firmadocumentosposgrado/firmarcontratospago.html", data)
                except Exception as ex:
                    pass

            elif action == 'oficiosposgrado':
                try:
                    data['title'] = 'Oficios de posgrado'
                    maestria = cohorte = estadof = cantidad = 0
                    bandera = False
                    filtros, s, m, url_vars = Q(estado__in=[4, 5, 6]), request.GET.get('s', ''), request.GET.get('m', '0'), ''
                    data['count'] = Contrato.objects.filter(filtros).values('id').count()

                    cohortes = None
                    if 'maestria' in request.GET:
                        maestria = int(request.GET['maestria'])
                    if 'cohorte' in request.GET:
                        cohorte = int(request.GET['cohorte'])
                    if 'estadof' in request.GET:
                        estadof = int(request.GET['estadof'])

                    if not cantidad:
                        cantidad = 25

                    if s:
                        ss = s.split(' ')
                        if len(ss) == 1:
                            filtros = filtros & (
                                                 Q(inscripcion__inscripcionaspirante__persona__nombres__icontains=s) |
                                                 Q(inscripcion__inscripcionaspirante__persona__apellido1__icontains=s) |
                                                 Q(inscripcion__inscripcionaspirante__persona__apellido2__icontains=s) |
                                                 Q(inscripcion__inscripcionaspirante__persona__cedula__icontains=s) |
                                                 Q(inscripcion__inscripcionaspirante__persona__pasaporte__icontains=s) |
                                                 Q(numerocontrato__icontains=s)
                                                 )
                            data['s'] = f"{s}"
                            url_vars += f"&s={s}"
                        else:
                            filtros = filtros & (Q(inscripcion__inscripcionaspirante__persona__apellido1__icontains=ss[0]) & Q(inscripcion__inscripcionaspirante__persona__apellido2__icontains=ss[1]))
                            data['s'] = f"{s}"
                            url_vars += f"&s={s}"

                    if int(m):
                        filtros = filtros & (Q(inscripcion__formapagopac_id=m))
                        data['m'] = f"{m}"
                        url_vars += f"&m={m}"
                        bandera = True

                    if maestria > 0:
                        data['maestria'] = maestria
                        filtros = filtros & Q(inscripcion__cohortes__maestriaadmision__id=maestria)
                        cohortes = CohorteMaestria.objects.filter(maestriaadmision__id=maestria)
                        url_vars += "&maestria={}".format(maestria)
                        bandera = True

                    if cohorte > 0:
                        data['cohorte'] = cohorte
                        filtros = filtros & Q(inscripcion__cohortes__id=cohorte)
                        url_vars += "&cohorte={}".format(cohorte)
                        bandera = True

                    if estadof > 0:
                        data['estadof'] = estadof
                        if estadof == 1:
                            filtros = filtros & Q(estado=5)
                        elif estadof == 2:
                            filtros = filtros & Q(estado=4)
                        else:
                            lis = []
                            listcontratos = Contrato.objects.filter(filtros).order_by('-fechacontrato',
                                                                                      '-contratolegalizado')
                            for contra in listcontratos:
                                if contra.ultima_evidenciaoficio().estado_aprobacion == 3:
                                    lis.append(contra.id)
                            filtros = filtros & Q(id__in=lis)
                        url_vars += "&estadof={}".format(estadof)
                        bandera = True

                    listcontratos = Contrato.objects.filter(filtros).order_by('-fechacontrato','-contratolegalizado')

                    paging = MiPaginador(listcontratos, listcontratos.count() if bandera and listcontratos else cantidad)
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
                    data['contratos'] = page.object_list
                    data['url_vars'] = url_vars
                    data['maestrialist'] = MaestriasAdmision.objects.filter(status=True, carrera__coordinacion__id=7, pk__in=Contrato.objects.values_list('inscripcion__cohortes__maestriaadmision__id').filter(status=True, estado=2))
                    data['cohorteslist'] = cohortes
                    data['canti'] = listcontratos.count()
                    # data['modulos'] = HistorialReservacionProspecto.objects.values_list('modulo_id', 'modulo__nombre', 'modulo__url').filter(status=True).distinct()
                    data['modulos'] = modulos = Contrato.objects.values_list('formapago_id', 'formapago__descripcion').filter(status=True).distinct().exclude(formapago=None).order_by('formapago_id')
                    return render(request, "firmadocumentosposgrado/oficiosposgrado.html", data)
                except Exception as ex:
                    pass

            elif action == 'view_requisitos_contratacion':
                try:
                    pk = request.GET.get('id', '0')
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    ePersonalAContratar = PersonalAContratar.objects.get(pk=pk)
                    data['personalcontratar'] = ePersonalAContratar
                    template = get_template('adm_expedientes/modal/requisitos.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'expedientecontratacion':
                try:
                    data['title'] = 'Expedientes de contratación'
                    eExpedienteContratacionId = ExpedienteContratacion.objects.filter(status=True).values_list("detalleInformeContratacion__informecontratacion", flat =True)
                    eInformeContratacion = InformeContratacion.objects.filter(status=True,pk__in = eExpedienteContratacionId)
                    paging = MiPaginador(eInformeContratacion , 25)
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
                    data['expedientes'] = page.object_list
                    return render(request, "firmadocumentosposgrado/expedientescontrataciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'detalleexpedientecontratacion':
                try:
                    data['title'] = 'Expedientes de contratación'
                    pk = request.GET.get('id', '0')

                    eExpedienteContratacion = ExpedienteContratacion.objects.filter(status=True,detalleInformeContratacion__informecontratacion_id = pk)
                    eInformeContratacion = InformeContratacion.objects.get(pk= pk)
                    paging = MiPaginador(eExpedienteContratacion , 25)
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
                    data['expedientes'] = page.object_list
                    data['eInformeContratacion'] = eInformeContratacion
                    return render(request, "firmadocumentosposgrado/detalleexpedientescontrataciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'firmarcontratopagoindividual':
                try:
                    data = {}
                    contrato = Contrato.objects.get(pk=request.GET['id'])
                    # data['integrante'] = integrante = InscripcionCohorte.objects.get(pk=request.GET['idi'])
                    data['integrante'] = integrante = contrato.inscripcion
                    data['contrato'] = contrato

                    template = get_template("firmadocumentosposgrado/firmarindividualcontrato.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'firmarcontratopagomasivo':
                try:
                    ids = None
                    # contrato = Contrato.objects.get(pk=request.GET['id'])
                    # data['contrato'] = contrato

                    if 'maestria' in request.GET:
                        idmaestria = int(request.GET['maestria'])

                    if 'ids' in request.GET:
                        ids = request.GET['ids']

                    leadsselect = ids
                    data['listadoseleccion'] = leadsselect

                    template = get_template("firmadocumentosposgrado/firmarmasivocontratos.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'html': json_content})
                except Exception as ex:
                    mensaje = 'Intentelo más tarde'
                    return JsonResponse({"result": False, "mensaje": mensaje})

            elif action == 'firmar_acta_grado_masivo':
                try:
                    ids = None

                    if 'ids' in request.GET:
                        ids = request.GET['ids']

                    leadsselect = ids
                    data['listadoseleccion'] = leadsselect

                    template = get_template("firmadocumentosposgrado/firmarmasivoactasdegrado.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'html': json_content})
                except Exception as ex:
                    mensaje = 'Intentelo más tarde'
                    return JsonResponse({"result": False, "mensaje": mensaje})

            elif action == 'firmaactagrado':
                try:
                    from sga.models import IntegranteFirmaTemaTitulacionPosgradoMatricula
                    data['title'] = 'Documentos de posgrado'
                    maestria = tperiodo = estadof = cantidad = 0
                    listfirmadopor = []
                    filtros, s, m, url_vars = Q(status=True, estado_firmas_acta_graduado__isnull=False,  matricula__inscripcion__graduado__isnull=False, califico=True, actacerrada=True), request.GET.get('s', ''), request.GET.get('m', '0'), ''
                    listadoperiodos = TemaTitulacionPosgradoMatricula.objects.values_list('matricula__nivel__periodo__id').filter(filtros).distinct()
                    listadocarreras = TemaTitulacionPosgradoMatricula.objects.values_list('matricula__inscripcion__carrera_id').filter(filtros).distinct()

                    if 'maestria' in request.GET:
                        maestria = int(request.GET['maestria'])
                    if 'tperiodo' in request.GET:
                        tperiodo = int(request.GET['tperiodo'])
                    if 'estadof' in request.GET:
                        estadof = int(request.GET['estadof'])

                    if 'firmadopor' in request.GET:
                        firmadopor = request.GET['firmadopor']
                        listfirmadopor = [int(numero) for numero in firmadopor.split(',')]

                    if s:
                        ss = s.split(' ')
                        if len(ss) == 1:
                            filtros = filtros & (
                                                 Q(matricula__inscripcion__persona__nombres__icontains=s) |
                                                 Q(matricula__inscripcion__persona__apellido1__icontains=s) |
                                                 Q(matricula__inscripcion__persona__apellido2__icontains=s) |
                                                 Q(matricula__inscripcion__persona__cedula__icontains=s) |
                                                 Q(matricula__inscripcion__persona__pasaporte__icontains=s) |
                                                 Q(matricula__inscripcion__persona__usuario__username__icontains=s)
                                                 )
                            data['s'] = f"{s}"
                            url_vars += f"&s={s}"
                        else:
                            filtros = filtros & (Q(matricula__inscripcion__persona__apellido1__icontains=ss[0]) & Q(matricula__inscripcion__persona__apellido2__icontains=ss[1]))
                            data['s'] = f"{s}"
                            url_vars += f"&s={s}"

                    if tperiodo > 0:
                        data['tperiodo'] = tperiodo
                        filtros = filtros & Q(matricula__nivel__periodo__id=tperiodo)
                        url_vars += "&tperiodo={}".format(tperiodo)
                        bandera = True

                    if maestria > 0:
                        data['maestria'] = maestria
                        filtros = filtros & Q(matricula__inscripcion__carrera_id=maestria)
                        url_vars += "&maestria={}".format(maestria)
                        bandera = True

                    if estadof > 0:
                        data['estadof'] = estadof
                        if estadof == 1:
                            firmo = True
                        if estadof == 2:
                            firmo = False
                        url_vars += "&estadof={}".format(estadof)
                        list_id_temas = IntegranteFirmaTemaTitulacionPosgradoMatricula.objects.filter(status=True, firmo=firmo,  persona_id=personasesion.id).values_list('tematitulacionposmat_id', flat=True).exclude(ordenfirma__tipo_acta_id__in = (9,10))
                        filtros = filtros & Q(id__in=list_id_temas)

                    if len(listfirmadopor) > 0:
                        from django.db.models import Count
                        data['firmadopor'] = listfirmadopor
                        list_id_temas = (
                            IntegranteFirmaTemaTitulacionPosgradoMatricula.objects
                                .filter(status=True, firmo=True, persona_id__in=listfirmadopor)
                                .values('tematitulacionposmat_id')
                                .annotate(num_personas=Count('persona_id'))
                                .filter(num_personas=len(listfirmadopor))
                                .values_list('tematitulacionposmat_id', flat=True)
                                .exclude(ordenfirma__tipo_acta_id__in=(9, 10))
                        )
                        filtros = filtros & Q(id__in=list_id_temas)
                        cadena_numeros = ','.join(map(str, listfirmadopor))
                        url_vars += "&firmadopor={}".format(cadena_numeros)

                    listids = []

                    eIntegranteFirmaTemaTitulacionPosgradoMatricula = IntegranteFirmaTemaTitulacionPosgradoMatricula.objects.filter(status=True,persona_id=personasesion.id).values_list('tematitulacionposmat_id', flat=True).exclude(ordenfirma__tipo_acta_id__in = (9,10))
                    listadoactas = TemaTitulacionPosgradoMatricula.objects.filter(filtros).filter(pk__in=eIntegranteFirmaTemaTitulacionPosgradoMatricula).distinct().order_by('tribunaltematitulacionposgradomatricula__fechadefensa')
                    if personasesion.usuario.is_superuser:
                        banderaacciones = True
                        listadoactas = TemaTitulacionPosgradoMatricula.objects.filter(filtros).distinct().order_by('tribunaltematitulacionposgradomatricula__fechadefensa')
                    # change
                    banderaacciones = True

                    INTEGRANTE_LOGEADO = None
                    for acta in listadoactas:
                        esintegrante = acta.get_es_integrante(personasesion)
                        if esintegrante:
                            if not INTEGRANTE_LOGEADO:
                                INTEGRANTE_LOGEADO =esintegrante
                                break

                    # for acta in listadoactas:
                    #     esintegrante = acta.get_es_integrante(personasesion)
                    #     if esintegrante:
                    #         if not INTEGRANTE_LOGEADO:
                    #             INTEGRANTE_LOGEADO =esintegrante
                    #
                    #     if variable_valor("FIRMAR_ACTAS_EN_ORDEN"):
                    #         if esintegrante and (acta.get_debe_firmar() == esintegrante):
                    #             listids.append(acta.id)
                    #     else:
                    #         if esintegrante :
                    #             listids.append(acta.id)

                    GENERADO = 0
                    FIRMADO_POR_VICERRECTO = 1
                    FIRMADO_POR_SECRETARIA = 2
                    FIRMADO_POR_RECTOR= 3
                    #
                    RECTOR= 1
                    SECRETARIA_GENERAL= 3
                    VICERRECTOR_DE_INVESTIGACION_Y_POSGRADO= 2
                    total_por_firmar = 0
                    if INTEGRANTE_LOGEADO:
                        if INTEGRANTE_LOGEADO.ordenfirma.id == VICERRECTOR_DE_INVESTIGACION_Y_POSGRADO:
                            listadoactas = listadoactas.annotate(
                                    estado_order=Case(
                                        When(estado_firmas_acta_graduado=GENERADO, then=Value(1)),
                                        When(estado_firmas_acta_graduado=FIRMADO_POR_VICERRECTO, then=Value(2)),
                                        When(estado_firmas_acta_graduado=FIRMADO_POR_SECRETARIA, then=Value(3)),
                                        When(estado_firmas_acta_graduado=FIRMADO_POR_RECTOR, then=Value(4)),
                                        default=Value(5),
                                        output_field=IntegerField()
                                    )
                                ).order_by('estado_order')
                            total_por_firmar = listadoactas.filter(estado_order=1).count()
                        elif INTEGRANTE_LOGEADO.ordenfirma.id == SECRETARIA_GENERAL:
                            listadoactas = listadoactas.annotate(
                                    estado_order=Case(
                                        When(estado_firmas_acta_graduado=GENERADO, then=Value(4)),
                                        When(estado_firmas_acta_graduado=FIRMADO_POR_VICERRECTO, then=Value(1)),
                                        When(estado_firmas_acta_graduado=FIRMADO_POR_SECRETARIA, then=Value(2)),
                                        When(estado_firmas_acta_graduado=FIRMADO_POR_RECTOR, then=Value(3)),
                                        default=Value(5),
                                        output_field=IntegerField()
                                    )
                                ).order_by('estado_order')
                            total_por_firmar = listadoactas.filter(estado_order=1).count()
                        elif INTEGRANTE_LOGEADO.ordenfirma.id == RECTOR:
                            listadoactas = listadoactas.annotate(
                                estado_order=Case(
                                    When(estado_firmas_acta_graduado=GENERADO, then=Value(4)),
                                    When(estado_firmas_acta_graduado=FIRMADO_POR_VICERRECTO, then=Value(3)),
                                    When(estado_firmas_acta_graduado=FIRMADO_POR_SECRETARIA, then=Value(1)),
                                    When(estado_firmas_acta_graduado=FIRMADO_POR_RECTOR, then=Value(2)),
                                    default=Value(5),
                                    output_field=IntegerField()
                                )
                            ).order_by('estado_order')
                            total_por_firmar = listadoactas.filter(estado_order=1).count()
                        else:
                            listadoactas = listadoactas
                            total_por_firmar = listadoactas.count()

                    paging = MiPaginador(listadoactas.distinct(), 15)
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
                    data['actas'] = page.object_list
                    data['url_vars'] = url_vars
                    data['periodolist'] = Periodo.objects.filter(status=True, pk__in=listadoperiodos)
                    data['maestrialist'] = Carrera.objects.filter(status=True, pk__in=listadocarreras)
                    data['canti'] = listadoactas.count()
                    data['banderaacciones'] = banderaacciones
                    data['persona'] = request.session.get('persona')
                    data['total_por_firmar'] = total_por_firmar
                    data['integrantes'] = IntegranteFirmaTemaTitulacionPosgradoMatricula.objects.filter(status=True).distinct('persona_id').order_by('persona_id')
                    return render(request, "firmadocumentosposgrado/viewactasgrado.html", data)
                except Exception as ex:
                    pass

            elif action == 'firmaractagradoindividual':
                try:
                    data = {}
                    titulacion = TemaTitulacionPosgradoMatricula.objects.get(pk=request.GET['id'])
                    if not titulacion.documentotitulacionposgrado_set.values('id').filter(status=True).exists():
                        if titulacion.mecanismotitulacionposgrado.id == 15:
                            pdfname, qrresult = actagradoposgradocomplexivo2(request.GET['id'])
                            tipo = 2
                        else:
                            pdfname, qrresult = actagradoposgrado2(request.GET['id'])
                            tipo = 1
                        instance = DocumentoTitulacionPosgrado(tematitulacionposgrado=titulacion,
                                                               tipodocumentotitulacion_id=tipo,
                                                               estadodocumentotitulacion_id=1,
                                                               fecha=hoy)
                        instance.save(request)
                        instance.archivo.name = pdfname
                        instance.save(request)
                        historial = HistorialDocumentoTitulacionPosgrado(documentotitulacion=instance,
                                                                         estadodocumentotitulacion_id=1,
                                                                         fecha=hoy)
                        historial.save(request)
                        historial.archivo.name = pdfname
                        historial.save(request)
                    data['integrante'] = integrante = titulacion.matricula.inscripcion.persona
                    data['titulacion'] = titulacion
                    data['cargofirma'] = cf = EstadoDocumentoTitulacionPosgrado.objects.filter(status=True, habilitado=True, orden__isnull=False).exclude(pk=1)

                    template = get_template("firmadocumentosposgrado/firmaractagradoindividual.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'firmaractagradomasivo':
                try:
                    ids = None
                    if 'ids' in request.GET:
                        ids = request.GET['ids']

                    leadsselect = ids
                    data['listadoseleccion'] = leadsselect
                    datos = leadsselect.split(',')

                    for t in datos:
                        titulacion = TemaTitulacionPosgradoMatricula.objects.get(pk=int(t))
                        if not titulacion.documentotitulacionposgrado_set.values('id').filter(status=True).exists():
                            if titulacion.mecanismotitulacionposgrado.id == 15:
                                pdfname, qrresult = actagradoposgradocomplexivo2(int(t))
                                tipo = 2
                            else:
                                pdfname, qrresult = actagradoposgrado2(int(t))
                                tipo = 1
                            instance = DocumentoTitulacionPosgrado(tematitulacionposgrado=titulacion,
                                                                   tipodocumentotitulacion_id=tipo,
                                                                   estadodocumentotitulacion_id=1,
                                                                   fecha=hoy)
                            instance.save(request)
                            instance.archivo.name = pdfname
                            instance.save(request)
                            historial = HistorialDocumentoTitulacionPosgrado(documentotitulacion=instance,
                                                                             estadodocumentotitulacion_id=1,
                                                                             fecha=hoy)
                            historial.save(request)
                            historial.archivo.name = pdfname
                            historial.save(request)
                    data['cargofirma'] = cf = EstadoDocumentoTitulacionPosgrado.objects.filter(status=True, habilitado=True, orden__isnull=False).exclude(pk=1)
                    template = get_template("firmadocumentosposgrado/firmaractagradomasivo.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'html': json_content})
                except Exception as ex:
                    mensaje = 'Intentelo más tarde'
                    return JsonResponse({"result": False, "mensaje": mensaje})

            elif action == 'tipodocumentotitulacion':
                try:
                    data['title'] = 'Tipos de documentos de titulación'
                    bandera = False
                    filtros, s, url_vars = Q(status=True), request.GET.get('s', ''), ''
                    if s:
                        filtros = filtros & (Q(descripcion__icontains=s))
                        data['s'] = f"{s}"
                        url_vars += f"&s={s}"
                    listado = TipoDocumentoTitulacionPosgrado.objects.filter(filtros).distinct().order_by('-id')
                    paging = MiPaginador(listado.distinct().order_by('-id'), listado.count() if bandera and listado else 15)
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
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    data['count'] = listado.count()
                    return render(request, "firmadocumentosposgrado/tipodocumentotitulacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addtipodocumento':
                try:
                    form = TipoDocumentoTitulacionForm()
                    data['action'] = 'addtipodocumento'
                    data['form'] = form
                    template = get_template("firmadocumentosposgrado/modals/formdocumentotitulacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edittipodocumento':
                try:
                    data['id'] = request.GET['id']
                    data['action'] = 'edittipodocumento'
                    data['filtro'] = filtro = TipoDocumentoTitulacionPosgrado.objects.get(pk=request.GET['id'])
                    form = TipoDocumentoTitulacionForm(initial={'descripcion':filtro.descripcion})
                    data['form'] = form
                    template = get_template("firmadocumentosposgrado/modals/formdocumentotitulacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'estadodocumentotitulacion':
                try:
                    data['title'] = 'Estados de documento de titulación'
                    bandera = False
                    filtros, s, url_vars = Q(status=True), request.GET.get('s', ''), ''
                    if s:
                        filtros = filtros & (Q(descripcion__icontains=s))
                        data['s'] = f"{s}"
                        url_vars += f"&s={s}"
                    listado = EstadoDocumentoTitulacionPosgrado.objects.filter(filtros).distinct().order_by('-id')
                    paging = MiPaginador(listado.distinct().order_by('orden','-habilitado'), listado.count() if bandera and listado else 15)
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
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    data['count'] = listado.count()
                    return render(request, "firmadocumentosposgrado/estadodocumentotitulacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addestadodocumento':
                try:
                    form = EstadoDocumentoTitulacionForm()
                    data['action'] = 'addestadodocumento'
                    data['form'] = form
                    template = get_template("firmadocumentosposgrado/modals/formdocumentotitulacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editestadodocumento':
                try:
                    data['id'] = request.GET['id']
                    data['action'] = 'editestadodocumento'
                    data['filtro'] = filtro = EstadoDocumentoTitulacionPosgrado.objects.get(pk=request.GET['id'])
                    form = EstadoDocumentoTitulacionForm(initial={'descripcion':filtro.descripcion,
                                                                  'nombrefirma':filtro.nombrefirma,
                                                                  'orden':filtro.orden,
                                                                  'habilitado':filtro.habilitado})
                    data['form'] = form
                    template = get_template("firmadocumentosposgrado/modals/formdocumentotitulacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'revision_expediente_vicerrectorado':
                try:
                    form = RevisionExpedienteForm()
                    instancia = ExpedienteContratacion.objects.filter(pk=int(request.GET['id']))
                    if instancia:
                        form = RevisionExpedienteForm(initial ={
                            'observacion':instancia.first().observacion_vicerrectorado
                        })
                    data['aprobacion'] = request.GET['aprobar']
                    data['form2'] = form
                    data['id'] = request.GET['id']
                    data['action'] = 'revision_expediente_vicerrectorado'
                    template = get_template('firmadocumentosposgrado/modals/formModal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'firmar_acta_grado_por_archivo':
                try:
                    tematitulacionposgradomatricula = TemaTitulacionPosgradoMatricula.objects.get(pk=request.GET['id'])
                    data['id'] = tematitulacionposgradomatricula.pk
                    data['action'] = 'firmar_acta_grado_por_archivo'
                    template = get_template("adm_firmardocumentos/modal/firmardocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'firmar_acta_grado_por_token':
                try:
                    tematitulacionposgradomatricula = TemaTitulacionPosgradoMatricula.objects.get(pk=request.GET['id'])
                    data['id'] = tematitulacionposgradomatricula.pk
                    data['action'] = 'firmar_acta_grado_por_token'
                    data['form2'] = ArchivoInvitacionForm()
                    template = get_template('adm_firmardocumentos/modal/formmodal.html')
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'verificar_turno_para_firmar':
                try:
                    pk = request.GET.get('id','0')
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    tematitulacionposgradomatricula = TemaTitulacionPosgradoMatricula.objects.get(pk=pk)
                    if variable_valor("FIRMAR_ACTAS_EN_ORDEN"):
                        puede, mensaje = tematitulacionposgradomatricula.puede_firmar_integrante_segun_orden(persona)
                    else:
                        puede, mensaje= tematitulacionposgradomatricula.integrante_ya_firmo(persona)
                    return JsonResponse({"result": True, "puede":puede,"mensaje":mensaje})
                except Exception as ex:
                    pass

            elif action == 'reportecontratosdiferidoresumen':
                try:
                    notifi = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                          titulo='Reporte de Seguimiento de contratos de pago diferido', destinatario=persona,
                                          url='',
                                          prioridad=1, app_label='SGA',
                                          fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                          en_proceso=True)
                    notifi.save(request)
                    reporte_contratos_diferido(request=request, notiid=notifi.id).start()
                    return JsonResponse({"result": True,
                                         "mensaje": u"El reporte de Seguimiento de contratos de pago diferido se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Gestionar firma de documentos de posgrado'

                misgrupos = ModuloGrupo.objects.filter(grupos__in=persona.usuario.groups.filter(id__in=[467,469,484])).distinct()
                modulos = Modulo.objects.values("id", "url", "icono", "nombre", "descripcion").filter(Q(modulogrupo__in=misgrupos), activo=True, submodulo=True).distinct().order_by('nombre')
                data['menu_panel'] = modulos

                # menu_panel = [
                #     {"url": '/firmardocumentosposgrado?action=firmaelectronicacontratos',
                #      "img": "/static/images/iconssga/icon_consulta_deudas.svg",
                #      "title": "Contratos de Pago",
                #      "description": "Documentos o contratos de pago de maestrantes.",
                #      },
                #     {"url": '/firmardocumentosposgrado?action=oficiosposgrado',
                #      "img": "/static/images/iconssga/icon_certificados_de_docentes.svg",
                #      "title": "Oficios de terminación de contrato",
                #      "description": "Oficios de terminación de contratos de servicios de posgrado.",
                #      },
                #     {"url": '/firmardocumentosposgrado?action=firmaactagrado',
                #      "img": "/static/images/iconssga/icon_certificados_de_docentes.svg",
                #      "title": "Actas de grado",
                #      "description": "Actas de grado de graduados.",
                #      }
                #     ,
                # ]
                # data['menu_panel'] = menu_panel
                return render(request, "firmadocumentosposgrado/panel.html", data)
            except Exception as ex:
                pass

def nombre_firma_dr_incorrecto(contrato):
    try:
        pdfname = SITE_STORAGE + contrato.archivocontrato.url
        # palabras = 'Dr. Edwuin Jesús Carrasquero Rodríguez'
        palabras = ''
        if contrato.inscripcion.cohortes.maestriaadmision.carrera.escuelaposgrado.id == 1:
            palabras = 'Msc. Angelica Maria Solis Manzano'
        elif contrato.inscripcion.cohortes.maestriaadmision.carrera.escuelaposgrado.id == 2:
            palabras = 'Msc. Graciela Josefina Castro Castillo'
        elif contrato.inscripcion.cohortes.maestriaadmision.carrera.escuelaposgrado.id == 3:
            palabras = 'Msc. Luis Eduardo Solis Granda'
        documento = fitz.open(pdfname)
        numpaginafirma = int(documento.page_count) - 1
        with fitz.open(pdfname) as document:
            words_dict = {}
            for page_number, page in enumerate(document):
                if page_number == numpaginafirma:
                    words = page.get_text("blocks")
                    words_dict[0] = words
        valor = None
        for cadena in words_dict[0]:
            if palabras in cadena[4]:
                valor = cadena
        if valor:
           return 'CORRECTO'
        else:
           return 'INCORRECTO'
    except Exception as ex:
        return ' - '
