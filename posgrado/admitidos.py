# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction, connections
from django.db.models import F
from django.template import Context
import io
import json
import fitz
import os
from docutils.nodes import error
import xlsxwriter
from settings import SITE_STORAGE
from django.contrib import messages
from core.firmar_documentos import firmar, firmarmasivo
from django.core.files import File as DjangoFile
from django.template.loader import get_template

from sagest.models import Rubro, TipoOtroRubro, Pago
from sga.funciones_templatepdf import certificadoadmtidoprograma
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from decorators import secure_module, last_access
from posgrado.forms import InscripcionCarreraForm, InscribirMatricularForm, HorarioMaestriaAdmitidoForm, AsignarHorarioAdmitidoForm
from posgrado.models import IntegranteGrupoEntrevitaMsc, CohorteMaestria, RequisitosGrupoCohorte, RequisitosMaestria, \
    InscripcionCohorte, GrupoExamenMsc, EvidenciaRequisitosAspirante, CambioAdmitidoCohorteInscripcion, Contrato, \
    MaestriasAdmision, DetalleAprobacionContrato, VentasProgramaMaestria, DetalleEvidenciaRequisitosAspirante, \
    HorariosProgramaMaestria, DetalleAtencionAdmitido
from sga.commonviews import adduserdata
from posgrado.commonviews import matricularposgrado
from settings import USA_TIPOS_INSCRIPCIONES, TIPO_INSCRIPCION_INICIAL
from sga.funciones import MiPaginador, log, variable_valor, null_to_decimal, remover_caracteres_tildes_unicode, remover_caracteres_especiales_unicode, \
    generar_nombre
from sga.models import Inscripcion, DocumentosDeInscripcion, InscripcionTipoInscripcion, miinstitucion, Sede, Sesion, \
    Modalidad, Carrera, Nivel, Materia, AsignaturaMalla, Malla, PerfilUsuario, CUENTAS_CORREOS, Matricula, MateriaAsignada
from sga.models import InscripcionTesDrive, ItinerarioMallaEspecilidad
from datetime import datetime, timedelta
from decimal import Decimal
from xlwt import *
from xlwt import easyxf
import xlwt
import random
import zipfile
unicode =str
from secretaria.views.adm_secretaria import nombre_carrera_pos

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['personasesion'] = personasesion = request.session['persona']
    periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'inscribircarrera':
            try:
                f = InscripcionCarreraForm(request.POST)
                integrante = IntegranteGrupoEntrevitaMsc.objects.get(pk=int(encrypt(request.POST['id'])))
                if f.is_valid() and not Inscripcion.objects.filter(persona=integrante.inscripcion.inscripcionaspirante.persona, carrera=f.cleaned_data['carrera']).exists():
                    carrera = f.cleaned_data['carrera']
                    sesion = f.cleaned_data['sesion']
                    modalidad = f.cleaned_data['modalidad']
                    sede = f.cleaned_data['sede']
                    if Inscripcion.objects.filter(persona=integrante.inscripcion.inscripcionaspirante.persona, carrera=carrera).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra registrado en esa carrera."})
                    if not Inscripcion.objects.filter(persona=integrante.inscripcion.inscripcionaspirante.persona, carrera=carrera).exists():
                        inscripcion = Inscripcion(persona=integrante.inscripcion.inscripcionaspirante.persona,
                                                  fecha=datetime.now().date(),
                                                  carrera=carrera,
                                                  modalidad=modalidad,
                                                  sesion=sesion,
                                                  sede=sede,
                                                  colegio='',
                                                  aplica_b2=True,
                                                  fechainicioprimernivel=datetime.now().date(),
                                                  fechainiciocarrera=datetime.now().date())
                        inscripcion.save(request)
                        integrante.inscripcion.inscripcionaspirante.persona.crear_perfil(inscripcion=inscripcion)
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
                        documentos.save()
                        preguntasinscripcion = inscripcion.preguntas_inscripcion()
                        inscripciontesdrive = InscripcionTesDrive(inscripcion=inscripcion,
                                                                  licencia=False,
                                                                  record=False,
                                                                  certificado_tipo_sangre=False,
                                                                  prueba_psicosensometrica=False,
                                                                  certificado_estudios=False)
                        inscripciontesdrive.save()
                        inscripcion.malla_inscripcion()
                        inscripcion.actualizar_nivel()
                        if USA_TIPOS_INSCRIPCIONES:
                            inscripciontipoinscripcion = InscripcionTipoInscripcion(inscripcion=inscripcion, tipoinscripcion_id=TIPO_INSCRIPCION_INICIAL)
                            inscripciontipoinscripcion.save()
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'inscribirmatricular':
            try:
                integrante = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                inscripcioncohorte = integrante
                inscripcion=None
                idnivel=None
                idnivel = Nivel.objects.get(pk=int(request.POST['idn']))

                if not Inscripcion.objects.filter(persona=integrante.inscripcionaspirante.persona, carrera_id=integrante.cohortes.maestriaadmision.carrera.id).exists():
                    carrera = Carrera.objects.get(pk=integrante.cohortes.maestriaadmision.carrera.id)
                    sesion = Sesion.objects.get(pk=idnivel.sesion.id)
                    modalidad = Modalidad.objects.get(pk=idnivel.modalidad.id)
                    sede = Sede.objects.get(pk=idnivel.sede.id)
                    if not Inscripcion.objects.filter(persona=integrante.inscripcionaspirante.persona, carrera_id=integrante.cohortes.maestriaadmision.carrera.id).exists():
                        inscripcion = Inscripcion(persona=integrante.inscripcionaspirante.persona,
                                                  fecha=datetime.now().date(),
                                                  carrera=carrera,
                                                  modalidad=modalidad,
                                                  sesion=sesion,
                                                  sede=sede,
                                                  colegio='',
                                                  aplica_b2=True,
                                                  fechainicioprimernivel=datetime.now().date(),
                                                  fechainiciocarrera=datetime.now().date())
                        inscripcion.save(request)

                        inscripcioncohorte.inscripcion = inscripcion
                        inscripcioncohorte.save(request)

                        integrante.inscripcionaspirante.persona.crear_perfil(inscripcion=inscripcion)
                        if PerfilUsuario.objects.values_list('id').filter(inscripcion=inscripcion, status=True).exists():
                            perfil = PerfilUsuario.objects.filter(inscripcion=inscripcion, status=True).last()
                            perfil.inscripcionprincipal = True
                            perfil.save(request)

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
                        documentos.save()
                        preguntasinscripcion = inscripcion.preguntas_inscripcion()
                        inscripciontesdrive = InscripcionTesDrive(inscripcion=inscripcion,
                                                                  licencia=False,
                                                                  record=False,
                                                                  certificado_tipo_sangre=False,
                                                                  prueba_psicosensometrica=False,
                                                                  certificado_estudios=False)
                        inscripciontesdrive.save()
                        inscripcion.malla_inscripcion()
                        inscripcion.actualizar_nivel()
                        if USA_TIPOS_INSCRIPCIONES:
                            inscripciontipoinscripcion = InscripcionTipoInscripcion(inscripcion=inscripcion, tipoinscripcion_id=TIPO_INSCRIPCION_INICIAL)
                            inscripciontipoinscripcion.save()
                else:
                    inscripcion= Inscripcion.objects.filter(persona=integrante.inscripcionaspirante.persona, carrera_id=integrante.cohortes.maestriaadmision.carrera.id).first()

                    if not inscripcioncohorte.inscripcion:
                        inscripcioncohorte.inscripcion = inscripcion
                        inscripcioncohorte.save(request)

                    if PerfilUsuario.objects.values_list('id').filter(persona=integrante.inscripcionaspirante.persona, status=True).exists():
                        perfiles = PerfilUsuario.objects.filter(persona=integrante.inscripcionaspirante.persona, status=True)
                        if (inscripcion.id,) in perfiles.values_list('inscripcion_id'):
                            for perf in perfiles:
                                if perf.inscripcion == inscripcion:
                                    if not perf.inscripcionprincipal:
                                        perf.inscripcionprincipal = True
                                        perf.save(request)
                                else:
                                    if perf.inscripcionprincipal:
                                        perf.inscripcionprincipal = False
                                        perf.save(request)

                return matricularposgrado(inscripcion.id, idnivel.id, idnivel.periodo_id,request)
                        # return JsonResponse({"result": "ok"})
                    # else:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra registrado en esa carrera."})
                # else:
                #     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s"%ex})

        elif action == 'generarmatricula':
            try:
                integrante = IntegranteGrupoEntrevitaMsc.objects.get(pk=request.POST['id'])
                if integrante.inscripcion.cohortes.valormatricula:
                    valormatricula = integrante.inscripcion.cohortes.valormatricula
                    tiporubroarancel = TipoOtroRubro.objects.get(pk=2845)
                    rubro = Rubro(tipo=tiporubroarancel,
                                  persona=integrante.inscripcion.inscripcionaspirante.persona,
                                  cohortemaestria=integrante.inscripcion.cohortes,
                                  inscripcion=integrante.inscripcion,
                                  relacionados=None,
                                  nombre=tiporubroarancel.nombre + ' - ' + integrante.inscripcion.cohortes.maestriaadmision.descripcion + ' - ' + integrante.inscripcion.cohortes.descripcion,
                                  cuota=1,
                                  fecha=datetime.now().date(),
                                  fechavence=integrante.inscripcion.cohortes.fechavencerubro,
                                  valor=valormatricula,
                                  iva_id=1,
                                  valoriva=0,
                                  valortotal=valormatricula,
                                  saldo=valormatricula,
                                  epunemi=True,
                                  idrubroepunemi=0,
                                  admisionposgradotipo=2,
                                  cancelado=False)
                    rubro.save(request)
                    integrante.inscripcion.tipocobro = 2
                    integrante.inscripcion.tipo_id = 2845
                    integrante.inscripcion.save(request)
                log(u'Genero rubro por concepto matricula posgrado: %s programa de %s' % (integrante.inscripcion, integrante.inscripcion.cohortes.maestriaadmision.descripcion), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'generarrubroprograma':
            try:
                integrante = IntegranteGrupoEntrevitaMsc.objects.get(pk=request.POST['id'])
                if integrante.inscripcion.cohortes.valorprograma:
                    valorprograma = integrante.inscripcion.cohortes.valorprograma
                    tiporubroarancel = TipoOtroRubro.objects.get(pk=integrante.inscripcion.cohortes.tiporubro.id)
                    rubro = Rubro(tipo=tiporubroarancel,
                                  persona=integrante.inscripcion.inscripcionaspirante.persona,
                                  cohortemaestria=integrante.inscripcion.cohortes,
                                  inscripcion=integrante.inscripcion,
                                  relacionados=None,
                                  nombre=tiporubroarancel.nombre + ' - ' + integrante.inscripcion.cohortes.maestriaadmision.descripcion + ' - ' + integrante.inscripcion.cohortes.descripcion,
                                  cuota=1,
                                  fecha=datetime.now().date(),
                                  fechavence=integrante.inscripcion.cohortes.fechavencerubro,
                                  valor=valorprograma,
                                  iva_id=1,
                                  valoriva=0,
                                  valortotal=valorprograma,
                                  saldo=valorprograma,
                                  epunemi=True,
                                  idrubroepunemi=0,
                                  admisionposgradotipo=3,
                                  cancelado=False)
                    rubro.save(request)
                    integrante.inscripcion.tipocobro = 3
                    integrante.inscripcion.tipo = tiporubroarancel
                    integrante.inscripcion.save(request)
                    log(u'Genero rubro por concepto costo programa posgrado: %s programa de %s' % (integrante.inscripcion, integrante.inscripcion.cohortes.maestriaadmision.descripcion), request, "add")
                    arregloemail = [23, 24, 25, 26, 27, 28]
                    emailaleatorio = random.choice(arregloemail)
                    send_html_mail("Pago Maestría - Posgrado UNEMI.", "emails/notificacionrubroadmitidosipec.html",{'sistema': u'Admision - UNEMI', 'fecha': datetime.now().date(), 'fechavencerubro': integrante.inscripcion.cohortes.fechavencerubro,'cohorte': integrante.inscripcion.cohortes,'hora': datetime.now().time(), 't': miinstitucion()},integrante.inscripcion.inscripcionaspirante.persona.emailpersonal(), [],cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'pdfcertificadototalprograma':
            try:
                qrresult = certificadoadmtidoprograma(request.POST['idins'])
                return JsonResponse({"result": "ok", 'url': qrresult})
            except Exception as ex:
                transaction.set_rollback(True)
                import sys
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                print(f'${ex.__str__()}')
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delinscripcion':
            try:
                inscripcioncohorte = InscripcionCohorte.objects.get(pk=request.POST['idinscripcion'])
                inscripcioncohorte.status=False
                if Rubro.objects.filter(inscripcion=inscripcioncohorte,status=True).exists():
                    for statusrubro in Rubro.objects.filter(inscripcion=inscripcioncohorte,status=True):
                        statusrubro.status=False
                        statusrubro.save(request)
                        if statusrubro.epunemi and statusrubro.idrubroepunemi > 0:
                            cursor = connections['epunemi'].cursor()
                            sql = "UPDATE sagest_rubro SET status=false WHERE sagest_rubro.status=true and sagest_rubro.id=" + str(statusrubro.idrubroepunemi)
                            cursor.execute(sql)
                            cursor.close()
                            log(u'Elimino rubro: %s - %s' % (statusrubro, statusrubro.persona), request, "del")
                #grupoexamenmsc.save(request)

                inscripcioncohorte.save(request)
                log(u'Eliminó inscripcion y rubro: %s - %s' % (inscripcioncohorte, inscripcioncohorte.inscripcionaspirante), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar."})

        elif action == 'cambiocohorteadm':
            try:
                inscripcioncoohorte = InscripcionCohorte.objects.get(pk=request.POST['idinscripcioncohorteotracohorteadmitido'])
                cohortemaestria = CohorteMaestria.objects.get(pk=request.POST['id_cohorte'])
                cambioadmitidocohorete=CambioAdmitidoCohorteInscripcion(cohortes=cohortemaestria,inscripcionCohorte=inscripcioncoohorte,observacion=request.POST['obersavioncambiocohorte'])
                cambioadmitidocohorete.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al cambiar la cohorte."})

        elif action == 'firmardocumentoindividual':
            try:
                contrato = Contrato.objects.get(pk=request.POST['idcontrato'])
                maestrante = InscripcionCohorte.objects.filter(pk=contrato.inscripcion.id, status=True)
                if not contrato.respaldoarchivocontrato:
                    contrato.respaldoarchivocontrato = contrato.archivocontrato
                    contrato.save(request)
                pdf = contrato.respaldoarchivocontrato
                #obtener la posicion xy de la firma del doctor en el pdf
                pdfname = SITE_STORAGE + contrato.archivocontrato.url
                numpagina = 6
                if contrato.inscripcion.formapagopac.id == 1:
                    numpagina = 5
                with fitz.open(pdfname) as document:
                    words_dict = {}
                    for page_number, page in enumerate(document):
                        if page_number == numpagina:
                            words = page.get_text("blocks")
                            words_dict[0] = words
                dddd = words_dict[0]
                valor = dddd[2]
                y = 5000 - int(valor[3]) - 4110
                #fin obtener posicion
                firma = request.FILES["firma"]
                passfirma = request.POST['palabraclave']
                txtFirmas = json.loads(request.POST['txtFirmas'])
                if not txtFirmas:
                    messages.error(request, "Error: Debe seleccionar ubicación de la firma")
                    return redirect('/admitidos?action=firmaelectronicacontratos')
                    # return JsonResponse({'result': True, "mensaje": "Error: Debe seleccionar ubicación de la firma"}, safe=False)
                generar_archivo_firmado = io.BytesIO()
                x = txtFirmas[-1]
                datau, datas = firmar(request, passfirma, firma, pdf, x["numPage"], x["x"], y, x["width"], x["height"])
                if not datau:
                    messages.error(request, f"Error: {datas}")
                    return redirect('/admitidos?action=firmaelectronicacontratos')
                    # return JsonResponse({'result': True, "mensaje": datas}, safe=False)
                generar_archivo_firmado.write(datau)
                generar_archivo_firmado.write(datas)
                generar_archivo_firmado.seek(0)
                extension = pdf.name.split('.')
                tam = len(extension)
                exte = extension[tam - 1]
                nombrefile_ = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(pdf.name)).replace('-', '_').replace('.pdf', '')
                _name = generar_nombre(f'{request.user.username}', nombrefile_)
                file_obj = DjangoFile(generar_archivo_firmado, name=f"{_name}_firmado.pdf")
                contrato.archivocontrato = file_obj
                contrato.contratolegalizado = True
                contrato.save(request)
                detalleevidencia = DetalleAprobacionContrato(contrato_id=contrato.id)
                detalleevidencia.save(request)
                detalleevidencia.observacion = 'Contrato legalizado'
                detalleevidencia.persona = personasesion
                detalleevidencia.estado_aprobacion = 2
                detalleevidencia.fecha_aprobacion = datetime.now()
                detalleevidencia.save(request)
                if contrato.contratolegalizado:
                    send_html_mail("Firma de Contratos POSGRADO.", "emails/notificarfirmacontratopago.html",
                                   {'sistema': u'Sistema de Gestión Académica',
                                    'fecha': datetime.now().date(),
                                    'hora': datetime.now().time(),
                                    'maestrantes': maestrante,
                                    't': miinstitucion()},
                                    personasesion.lista_emails_envio(), [],
                                    cuenta=CUENTAS_CORREOS[0][1])
                messages.success(request, f'Documento firmado con exito')
                log(u'Firmo Documento: {}'.format(nombrefile_), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s"%ex})

        elif action == 'firmardocumentomasivo':
            try:
                firma = request.FILES["firma"]
                passfirma = request.POST['palabraclave']
                contratosselect = request.POST['ids'].split(',')
                bandera = False
                p12 = None
                listainscripcion = []
                for con in contratosselect:
                    contrato = Contrato.objects.get(pk=con)
                    if not contrato.respaldoarchivocontrato:
                        contrato.respaldoarchivocontrato = contrato.archivocontrato
                        contrato.save(request)
                    pdf = contrato.respaldoarchivocontrato
                    # obtener la posicion xy de la firma del doctor en el pdf
                    pdfname = SITE_STORAGE + contrato.archivocontrato.url
                    numpagina = 6
                    if contrato.inscripcion.formapagopac.id == 1:
                        numpagina = 5
                    with fitz.open(pdfname) as document:
                        words_dict = {}
                        for page_number, page in enumerate(document):
                            if page_number == numpagina:
                                words = page.get_text("blocks")
                                words_dict[0] = words
                    dddd = words_dict[0]
                    valor = dddd[2]
                    y = 5000 - int(valor[3]) - 4110
                    # fin obtener posicion

                    generar_archivo_firmado = io.BytesIO()
                    if contrato.inscripcion.formapagopac.id == 2:
                        datau, datas, p12 = firmarmasivo(request, p12, bandera, passfirma, firma, pdf, 6, 120.5, y, 150, 45)
                    else:
                        datau, datas, p12 = firmarmasivo(request, p12, bandera, passfirma, firma, pdf, 5, 113.5, y, 150, 45)
                    if not datau:
                        messages.error(request, f"Error: {datas}")
                        return redirect('/admitidos?action=firmaelectronicacontratos')
                    if p12:
                        bandera = True
                    generar_archivo_firmado.write(datau)
                    generar_archivo_firmado.write(datas)
                    generar_archivo_firmado.seek(0)
                    extension = pdf.name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    nombrefile_ = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(pdf.name)).replace('-', '_').replace('.pdf', '')
                    _name = generar_nombre(f'{request.user.username}', nombrefile_)
                    file_obj = DjangoFile(generar_archivo_firmado, name=f"{_name}_firmado.pdf")
                    contrato.archivocontrato = file_obj
                    contrato.contratolegalizado = True
                    contrato.save(request)
                    detalleevidencia = DetalleAprobacionContrato(contrato_id=contrato.id)
                    detalleevidencia.save(request)
                    detalleevidencia.observacion = 'Contrato legalizado'
                    detalleevidencia.persona = personasesion
                    detalleevidencia.estado_aprobacion = 2
                    detalleevidencia.fecha_aprobacion = datetime.now()
                    detalleevidencia.save(request)
                    log(u'Masivo Firmó Documento: {}'.format(nombrefile_), request, "add")
                    listainscripcion.append(contrato.inscripcion.id)
                maestrantes = InscripcionCohorte.objects.filter(pk__in=listainscripcion, status=True)
                send_html_mail("Firma de Contratos POSGRADO.", "emails/notificarfirmacontratopago.html",
                               {'sistema': u'Sistema de Gestión Académica',
                                'fecha': datetime.now().date(),
                                'hora': datetime.now().time(),
                                'maestrantes': maestrantes,
                                't': miinstitucion()},
                               personasesion.lista_emails_envio(), [],
                               cuenta=CUENTAS_CORREOS[0][1])
                messages.success(request, f'Documentos firmados con exito')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s"%ex})

        elif action == 'addhorariomaestria':
            try:
                f = HorarioMaestriaAdmitidoForm(request.POST)
                if f.is_valid():
                    if HorariosProgramaMaestria.objects.filter(status=True, maestria__carrera=f.cleaned_data['carrera'],
                                                               paralelo=f.cleaned_data['paralelo']).exists():
                        return JsonResponse({"result": True, 'mensaje': 'El paralelo ingresado ya existe en esa maestría'})

                    eMaestria = MaestriasAdmision.objects.filter(status=True, carrera=f.cleaned_data['carrera']).first()
                    eHorario = HorariosProgramaMaestria(maestria=eMaestria,
                                                        nombre=f.cleaned_data['horario'],
                                                        paralelo=f.cleaned_data['paralelo'])
                    eHorario.save(request)

                    log(u'Adicionó horario de maestría: %s' % eHorario, request, "add")
                    return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edithorariomaestria':
            try:
                eHorario = HorariosProgramaMaestria.objects.get(status=True, pk=int(request.POST['id']))

                f = HorarioMaestriaAdmitidoForm(request.POST)
                if f.is_valid():
                    if HorariosProgramaMaestria.objects.filter(status=True, maestria=eHorario.maestria,
                                                               paralelo=f.cleaned_data['paralelo']).exclude(id=eHorario.id).exists():
                        return JsonResponse({"result": True, 'mensaje': 'El paralelo ingresado ya existe en esa maestría'})

                    eHorario.nombre = f.cleaned_data['horario']
                    eHorario.paralelo = f.cleaned_data['paralelo']
                    eHorario.save(request)

                    log(u'Editó horario de maestría: %s' % eHorario, request, "add")
                    return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'asignarhorario':
            try:
                f = AsignarHorarioAdmitidoForm(request.POST)
                eAdmitido = InscripcionCohorte.objects.get(status=True, pk=int(request.POST['id']))
                if f.is_valid():
                    if DetalleAtencionAdmitido.objects.filter(status=True, admitido=eAdmitido).exists():
                        eHorarios = DetalleAtencionAdmitido.objects.filter(status=True, admitido=eAdmitido)
                        for eHorario in eHorarios:
                            eHorario.activo = False
                            eHorario.save(request)

                    eHorarioAct = DetalleAtencionAdmitido(admitido=eAdmitido,
                                                           horario=f.cleaned_data['horario'],
                                                           atendido=True)
                    eHorarioAct.save()

                    log(u'Adicionó horario de maestría del admitido: %s' % eHorarioAct, request, "add")
                    return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletehorariomaestria':
            try:
                eHorario = HorariosProgramaMaestria.objects.get(pk=int(request.POST['id']))
                eHorario.activo = False
                eHorario.save(request)
                log(u'Desactivó horario de programa de maestría: %s' % eHorario, request, "del")
                return JsonResponse({"result": 'ok', "mensaje": u"Horario eliminado correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        elif action == 'activehorariomaestria':
            try:
                eHorario = HorariosProgramaMaestria.objects.get(pk=int(request.POST['id']))
                eHorario.activo = True
                eHorario.save(request)
                log(u'Activó horario de programa de maestría: %s' % eHorario, request, "edit")
                return JsonResponse({"result": 'ok', "mensaje": u"Horario eliminado correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Listado de inscripciones'
        persona = request.session['persona']
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'inscribircarrera':
                try:
                    data['title'] = u'Inscripción de postulante admitido en carrera'
                    data['integrante'] = integrante = IntegranteGrupoEntrevitaMsc.objects.get(pk=int(encrypt(request.GET['id'])))
                    codigosesion = None
                    codigomodalidad = None
                    if periodo.nivel_set.filter(nivellibrecoordinacion__coordinacion_id=7, status=True):
                        nivel = periodo.nivel_set.get(nivellibrecoordinacion__coordinacion_id=7, status=True)
                        codigosesion = nivel.sesion_id
                        codigomodalidad = nivel.modalidad_id
                    form = InscripcionCarreraForm(initial={'sede': 1,
                                                           'carrera': integrante.inscripcion.cohortes.maestriaadmision.carrera,
                                                           # 'modalidad': integrante.inscripcion.cohortes.maestriaadmision.carrera.modalidad,
                                                           'modalidad': codigomodalidad,
                                                           'sesion': codigosesion})
                    data['form'] = form
                    return render(request, "admitidos/inscribircarrera.html", data)
                except Exception as ex:
                    pass

            if action == 'detallerequisitos':
                try:
                    tienerequisitos = False
                    data['tipo'] = int(request.GET['tipo'])
                    data['inscripcioncohorte'] = inscripcioncohorte = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    inscripciondescuento = None
                    data['inscripciondescuento'] = inscripciondescuento
                    if inscripcioncohorte.evidenciarequisitosaspirante_set.filter(status=True).exists():
                        tienerequisitos = True
                    data['tienerequisitos'] = tienerequisitos
                    if inscripcioncohorte.cohortes.tienecostoexamen:
                        if inscripcioncohorte.evidenciapagoexamen_set.filter(status=True):
                            tienepagoexamen = True
                            data['pagoexamen'] = evidpagoexamen = inscripcioncohorte.evidenciapagoexamen_set.filter(status=True)[0]
                            if evidpagoexamen.estadorevision == 2:
                                bloqueasubidapago = 2
                    if InscripcionCohorte.objects.filter(pk=int(request.GET['id']), grupo__isnull=True):
                        data['requisitos'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, requisito__claserequisito__clasificacion=1, status=True).order_by("id").distinct()
                        if inscripcioncohorte.subirrequisitogarante:
                            data['requisitosfi'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, requisito__claserequisito__clasificacion=3, status=True).order_by("id")
                        else:
                            data['requisitosfi'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, requisito__claserequisito__clasificacion=3, status=True, requisito__tipopersona__id=1).order_by("id")
                    else:
                        gruporequisitos = RequisitosGrupoCohorte.objects.values_list('requisito_id', flat=True).filter(grupo=inscripcioncohorte.grupo, status=True)
                        data['requisitos'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, requisito_id__in=gruporequisitos, requisito__claserequisito__clasificacion=1, status=True).order_by("id")
                        if inscripcioncohorte.subirrequisitogarante:
                            data['requisitosfi'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, requisito_id__in=gruporequisitos, requisito__claserequisito__clasificacion=3, status=True).order_by("id")
                        else:
                            data['requisitosfi'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, requisito_id__in=gruporequisitos, requisito__claserequisito__clasificacion=3, status=True, requisito__tipopersona__id=1).order_by("id")

                    template = get_template("comercial/modal/detallerequisitos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'listadoadmitidosconpago':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('listado_admitidos')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 35)
                    ws.set_column(2, 2, 25)
                    ws.set_column(3, 3, 15)
                    ws.set_column(4, 4, 40)
                    ws.set_column(5, 5, 40)
                    ws.set_column(6, 6, 40)
                    ws.set_column(7, 7, 15)
                    ws.set_column(8, 8, 35)
                    ws.set_column(9, 9, 15)
                    ws.set_column(10, 10, 20)
                    ws.set_column(11, 11, 25)
                    ws.set_column(12, 12, 15)
                    ws.set_column(13, 13, 15)
                    ws.set_column(14, 14, 15)
                    ws.set_column(15, 15, 15)
                    ws.set_column(16, 16, 15)
                    ws.set_column(17, 17, 15)
                    ws.set_column(18, 18, 15)
                    ws.set_column(19, 19, 15)
                    ws.set_column(20, 20, 15)
                    ws.set_column(21, 21, 15)
                    ws.set_column(22, 22, 20)
                    ws.set_column(23, 23, 15)
                    ws.set_column(24, 24, 20)
                    ws.set_column(25, 25, 20)
                    ws.set_column(26, 26, 40)
                    ws.set_column(27, 27, 40)
                    ws.set_column(28, 28, 40)
                    ws.set_column(29, 29, 25)
                    ws.set_column(30, 30, 15)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    ws.merge_range('A1:AE1', 'LISTADO DE ADMITIDOS', formatotitulo_filtros)
                    ws.write(1, 0, 'N°', formatoceldacab)
                    ws.write(1, 1, 'CARRERA', formatoceldacab)
                    ws.write(1, 2, 'COHORTE', formatoceldacab)
                    ws.write(1, 3, 'CÉDULA', formatoceldacab)
                    ws.write(1, 4, 'NOMBRES', formatoceldacab)
                    ws.write(1, 5, 'EMAIL', formatoceldacab)
                    ws.write(1, 6, 'EMAIL INSTITUCIONAL', formatoceldacab)
                    ws.write(1, 7, 'TELÉFONO', formatoceldacab)
                    ws.write(1, 8, 'DIRECCIÓN', formatoceldacab)
                    ws.write(1, 9, 'FECHA DE POSTULACIÓN', formatoceldacab)
                    ws.write(1, 10, 'FORMA DE PAGO', formatoceldacab)
                    ws.write(1, 11, 'MENCIÓN', formatoceldacab)
                    ws.write(1, 12, 'RUBRO GENERADO', formatoceldacab)
                    ws.write(1, 13, 'VALOR GENERADO', formatoceldacab)
                    ws.write(1, 14, 'VALOR PAGADO (ABONADO)', formatoceldacab)
                    ws.write(1, 15, 'SALDO', formatoceldacab)
                    ws.write(1, 16, 'VENCIDO', formatoceldacab)
                    ws.write(1, 17, 'RUBRO CANCELADO', formatoceldacab)
                    ws.write(1, 18, 'CONTRATO APROBADO', formatoceldacab)
                    ws.write(1, 19, 'PAGARÉ APROBADO', formatoceldacab)
                    ws.write(1, 20, 'CUOTA INICIAL PAGADA', formatoceldacab)
                    ws.write(1, 21, 'FECHA DE PAGO', formatoceldacab)
                    ws.write(1, 22, 'ESTADO', formatoceldacab)
                    ws.write(1, 23, 'FECHA DE INSCRIPCIÓN', formatoceldacab)
                    ws.write(1, 24, 'FECHA DE MATRÍCULA', formatoceldacab)
                    ws.write(1, 25, 'CURSO MATRICULADO', formatoceldacab)
                    ws.write(1, 26, 'INSCRITO POR', formatoceldacab)
                    ws.write(1, 27, 'MATRICULADO POR', formatoceldacab)
                    ws.write(1, 28, 'HOMOLOGACIÓN', formatoceldacab)
                    ws.write(1, 29, 'HORARIO', formatoceldacab)
                    ws.write(1, 30, 'PARALELO HORARIO', formatoceldacab)

                    filtro = Q(status=True, valida=True, facturado=True)

                    idc = ide = idf = 0
                    desde = hasta = ''

                    if 'idc' in request.GET:
                        idc = int(request.GET['idc'])

                    if 'ide' in request.GET:
                        ide = int(request.GET['ide'])

                    if 'idf' in request.GET:
                        idf = int(request.GET['idf'])

                    if 'desde' in request.GET:
                        desde = request.GET['desde']

                    if 'hasta' in request.GET:
                        hasta = request.GET['hasta']

                    if idc > 0:
                        filtro = filtro & (Q(inscripcioncohorte__cohortes__id=int(idc)))

                    if ide > 0:
                        if ide == 1:
                            filtro = filtro & Q(
                                Q(inscripcioncohorte__inscripcion__matricula__id=F('inscripcioncohorte__inscripcion__matricula__id')) &
                                Q(inscripcioncohorte__inscripcion__matricula__status=True)
                            )
                        else:
                            filtro = filtro & Q(
                                Q(inscripcioncohorte__inscripcion__matricula__isnull=True)
                            )

                    if idf > 0:
                        filtro = filtro & (Q(inscripcioncohorte__formapagopac__id=int(idf)))

                    if desde and hasta:
                        filtro = filtro & Q(fecha__range=(desde, hasta))

                    elif desde:
                        filtro = filtro & Q(fecha__gte=desde)

                    elif hasta:
                        filtro = filtro & Q(fecha__lte=hasta)

                    idins = VentasProgramaMaestria.objects.filter(filtro).values_list('inscripcioncohorte__id', flat=True).order_by('inscripcioncohorte__id').distinct()

                    eAdmitidos = InscripcionCohorte.objects.filter(id__in=idins).order_by('-id')

                    filas_recorridas = 3
                    cont = 1
                    for admitido in eAdmitidos:
                        pagoru = 'NO'
                        if admitido.formapagopac.id == 1:
                            if admitido.total_pagado_rubro_cohorte() == admitido.cohortes.valorprogramacertificado:
                                pagoru = 'SI'
                        else:
                            if admitido.total_pagado_rubro_cohorte() > 0:
                                pagoru = 'SI'

                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(admitido.cohortes.maestriaadmision.carrera), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(admitido.cohortes.descripcion), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.cedula), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.email if admitido.inscripcionaspirante.persona.email else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.emailinst if admitido.inscripcionaspirante.persona.emailinst else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.telefono if admitido.inscripcionaspirante.persona.telefono else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.direccion if admitido.inscripcionaspirante.persona.direccion else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str(admitido.fecha_creacion.date()), formatoceldaleft)
                        ws.write('K%s' % filas_recorridas, str(admitido.formapagopac.descripcion if admitido.formapagopac.descripcion else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('L%s' % filas_recorridas, str(admitido.mencion_cohorte()), formatoceldaleft)
                        ws.write('M%s' % filas_recorridas, str('SI' if admitido.total_generado_rubro() > 0 else 'NO'), formatoceldaleft)
                        ws.write('N%s' % filas_recorridas, admitido.total_generado_rubro(), decimalformat)
                        ws.write('O%s' % filas_recorridas, admitido.total_pagado_rubro_cohorte(), decimalformat)
                        ws.write('P%s' % filas_recorridas, admitido.total_pendiente(), decimalformat)
                        ws.write('Q%s' % filas_recorridas, str('SI' if admitido.total_vencido_rubro() > 0 else 'NO'), formatoceldaleft)
                        ws.write('R%s' % filas_recorridas, str(pagoru), formatoceldaleft)
                        ws.write('S%s' % filas_recorridas, str('SI' if admitido.tiene_contrato_aprobado() == True else 'NO'), formatoceldaleft)
                        ws.write('T%s' % filas_recorridas, str(admitido.tiene_pagare_aprobado()), formatoceldaleft)
                        ws.write('U%s' % filas_recorridas, str('SI' if admitido.pago_rubro_matricula() == True else 'NO'), formatoceldaleft)
                        ws.write('V%s' % filas_recorridas, str(admitido.fecha_primer_pago()), formatoceldaleft)
                        ws.write('W%s' % filas_recorridas, str('NO MATRICULADO' if admitido.esta_inscrito() == False else 'MATRICULADO'), formatoceldaleft)
                        ws.write('X%s' % filas_recorridas, str(admitido.fecha_inscrito()), formatoceldaleft)
                        ws.write('Y%s' % filas_recorridas, str(admitido.fecha_matriculacion2()), formatoceldaleft)
                        ws.write('Z%s' % filas_recorridas, str(admitido.curso_matriculado()[0] if len(admitido.curso_matriculado()) > 0 else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('AA%s' % filas_recorridas, str(admitido.inscrito_por()), formatoceldaleft)
                        ws.write('AB%s' % filas_recorridas, str(admitido.matriculado_por()), formatoceldaleft)
                        ws.write('AC%s' % filas_recorridas, str('INTERNA' if admitido.homologado == 1 else 'EXTERNA' if admitido.homologado == 2 else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('AD%s' % filas_recorridas, str(admitido.horario_seleccionado().horario if admitido.horario_seleccionado() else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('AE%s' % filas_recorridas, str(admitido.horario_seleccionado().horario.paralelo if admitido.horario_seleccionado() and admitido.horario_seleccionado().horario.paralelo else 'NO REGISTRA'), formatoceldaleft)

                        filas_recorridas += 1
                        print(f'{cont}/{eAdmitidos.count()}')
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'Listado_admitidos.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            if action == 'listadoadmitidossindatos':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('listado_admitidos_sin_datos')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 35)
                    ws.set_column(2, 2, 30)
                    ws.set_column(3, 3, 15)
                    ws.set_column(4, 4, 35)
                    ws.set_column(5, 5, 35)
                    ws.set_column(6, 6, 35)
                    ws.set_column(7, 7, 15)
                    ws.set_column(8, 8, 15)
                    ws.set_column(9, 9, 40)
                    ws.set_column(10, 10, 50)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    ws.merge_range('A1:I1', 'LISTADO DE ADMITIDOS SIN DATOS', formatotitulo_filtros)
                    ws.write(1, 0, 'N°', formatoceldacab)
                    ws.write(1, 1, 'CARRERA', formatoceldacab)
                    ws.write(1, 2, 'COHORTE', formatoceldacab)
                    ws.write(1, 3, 'CÉDULA', formatoceldacab)
                    ws.write(1, 4, 'NOMBRES', formatoceldacab)
                    ws.write(1, 5, 'EMAIL', formatoceldacab)
                    ws.write(1, 6, 'EMAIL INSTITUCIONAL', formatoceldacab)
                    ws.write(1, 7, 'TELÉFONO', formatoceldacab)
                    ws.write(1, 8, 'ESTADO', formatoceldacab)
                    ws.write(1, 9, 'ASESOR COMERCIAL', formatoceldacab)
                    ws.write(1, 10, 'DATOS POR LLENAR', formatoceldacab)

                    filtro = Q(status=True, valida=True, facturado=True)

                    idc = ide = idf = 0
                    desde = hasta = ''
                    if 'idc' in request.GET:
                        idc = int(request.GET['idc'])

                    if 'ide' in request.GET:
                        ide = int(request.GET['ide'])

                    if 'idf' in request.GET:
                        idf = int(request.GET['idf'])

                    if 'desde' in request.GET:
                        desde = request.GET['desde']

                    if 'hasta' in request.GET:
                        hasta = request.GET['hasta']

                    if idc > 0:
                        filtro = filtro & (Q(inscripcioncohorte__cohortes__id=int(idc)))

                    if ide > 0:
                        if ide == 1:
                            filtro = filtro & Q(
                                Q(inscripcioncohorte__inscripcion__matricula__id=F('inscripcioncohorte__inscripcion__matricula__id')) &
                                Q(inscripcioncohorte__inscripcion__matricula__status=True)
                            )
                        else:
                            filtro = filtro & Q(
                                Q(inscripcioncohorte__inscripcion__matricula__isnull=True)
                            )

                    if idf > 0:
                        filtro = filtro & (Q(inscripcioncohorte__formapagopac__id=int(idf)))

                    if desde and hasta:
                        filtro = filtro & Q(fecha__range=(desde, hasta))

                    elif desde:
                        filtro = filtro & Q(fecha__gte=desde)

                    elif hasta:
                        filtro = filtro & Q(fecha__lte=hasta)

                    idins = VentasProgramaMaestria.objects.filter(filtro).values_list('inscripcioncohorte__id', flat=True).order_by('inscripcioncohorte__id').distinct()

                    eAdmitidos = InscripcionCohorte.objects.filter(id__in=idins).order_by('-id')

                    filas_recorridas = 3
                    cont = 1
                    for admitido in eAdmitidos:
                        if admitido.completo_datos_matrices() == '1':
                            ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                            ws.write('B%s' % filas_recorridas, str(admitido.cohortes.maestriaadmision.carrera), formatoceldaleft)
                            ws.write('C%s' % filas_recorridas, str(admitido.cohortes.descripcion), formatoceldaleft)
                            ws.write('D%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.cedula), formatoceldaleft)
                            ws.write('E%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.nombre_completo_inverso()), formatoceldaleft)
                            ws.write('F%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.email if admitido.inscripcionaspirante.persona.email else 'NO REGISTRA'), formatoceldaleft)
                            ws.write('G%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.emailinst if admitido.inscripcionaspirante.persona.emailinst else 'NO REGISTRA'), formatoceldaleft)
                            ws.write('H%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.telefono if admitido.inscripcionaspirante.persona.telefono else 'NO REGISTRA'), formatoceldaleft)
                            ws.write('I%s' % filas_recorridas, str('NO MATRICULADO' if admitido.esta_inscrito() == False else 'MATRICULADO'), formatoceldaleft)
                            ws.write('J%s' % filas_recorridas, str(admitido.asesor.persona), formatoceldaleft)
                            ws.write('K%s' % filas_recorridas, str(admitido.datos_restantes()), formatoceldaleft)

                            filas_recorridas += 1
                            print(f'{cont}/{eAdmitidos.count()}')
                            cont += 1
                    workbook.close()
                    output.seek(0)
                    filename = 'Listado_admitidos_sin_datos.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            if action == 'descargarlistadohora':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('listado_admitidos_horario')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 35)
                    ws.set_column(2, 2, 30)
                    ws.set_column(3, 3, 15)
                    ws.set_column(4, 4, 35)
                    ws.set_column(5, 5, 35)
                    ws.set_column(6, 6, 35)
                    ws.set_column(7, 7, 15)
                    ws.set_column(8, 8, 15)
                    ws.set_column(9, 9, 40)
                    ws.set_column(10, 10, 25)
                    ws.set_column(11, 11, 25)
                    ws.set_column(12, 12, 25)
                    ws.set_column(13, 13, 25)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    eHorario = HorariosProgramaMaestria.objects.get(status=True, pk=int(request.GET['id']))

                    ws.merge_range('A1:N1', f'LISTADO DE ADMITIDOS HORARIO {eHorario}', formatotitulo_filtros)
                    ws.write(1, 0, 'N°', formatoceldacab)
                    ws.write(1, 1, 'CARRERA', formatoceldacab)
                    ws.write(1, 2, 'COHORTE', formatoceldacab)
                    ws.write(1, 3, 'CÉDULA', formatoceldacab)
                    ws.write(1, 4, 'NOMBRES', formatoceldacab)
                    ws.write(1, 5, 'EMAIL', formatoceldacab)
                    ws.write(1, 6, 'EMAIL INSTITUCIONAL', formatoceldacab)
                    ws.write(1, 7, 'TELÉFONO', formatoceldacab)
                    ws.write(1, 8, 'ESTADO', formatoceldacab)
                    ws.write(1, 9, 'ASESOR COMERCIAL', formatoceldacab)
                    ws.write(1, 10, 'HORARIO', formatoceldacab)
                    ws.write(1, 11, 'PARALELO', formatoceldacab)
                    ws.write(1, 12, 'FECHA DE ASIGNACIÓN DE HORARIO', formatoceldacab)
                    ws.write(1, 13, 'HORA DE ASIGNACIÓN DE HORARIO', formatoceldacab)

                    idadmitido = DetalleAtencionAdmitido.objects.filter(status=True, activo=True, atendido=True, horario=eHorario).values_list('admitido__id', flat=True)

                    eAdmitidos = InscripcionCohorte.objects.filter(id__in=idadmitido).order_by('-id')

                    filas_recorridas = 3
                    cont = 1
                    for admitido in eAdmitidos:
                        eDeta = DetalleAtencionAdmitido.objects.filter(status=True, activo=True, atendido=True, horario=eHorario, admitido=admitido).first()
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(admitido.cohortes.maestriaadmision.carrera), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(admitido.cohortes.descripcion), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.cedula), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.email if admitido.inscripcionaspirante.persona.email else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.emailinst if admitido.inscripcionaspirante.persona.emailinst else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.telefono if admitido.inscripcionaspirante.persona.telefono else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str('NO MATRICULADO' if admitido.esta_inscrito() == False else 'MATRICULADO'), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str(admitido.asesor.persona), formatoceldaleft)
                        ws.write('K%s' % filas_recorridas, str(eDeta.horario.nombre), formatoceldaleft)
                        ws.write('L%s' % filas_recorridas, str(eDeta.horario.paralelo if eDeta.horario.paralelo else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('M%s' % filas_recorridas, str(eDeta.fecha_creacion.date()), formatoceldaleft)
                        ws.write('N%s' % filas_recorridas, str(eDeta.fecha_creacion.time()), formatoceldaleft)

                        filas_recorridas += 1
                        print(f'{cont}/{eAdmitidos.count()}')
                        cont += 1
                    workbook.close()
                    output.seek(0)
                    filename = f'Listado_horario_asignado_{datetime.now()}.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            if action == 'descargarlistadoadmitidos':
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
                    ws = wb.add_sheet('exp_xls_post_part')
                    # ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")

                    cohorte = CohorteMaestria.objects.get(pk=int(request.GET['idcohorte']))

                    response['Content-Disposition'] = 'attachment; filename=listadoadmitidos'+ random.randint(1, 10000).__str__()  + '.xls'
                    row_num = 1
                    columns = [
                        (u"N.", 2000),
                        (u"CEDULA", 4000),
                        (u"NOMBRES", 10000),
                        (u"EMAIL", 6000),
                        (u"DIRECCIÓN", 12000),
                        (u"TELEFONO", 4000),
                        (u"FECHA INSCRIPCIÓN", 4000),
                        (u"MENCIÓN", 8000),
                        (u"FECHA DE PAGO", 4000),
                        (u"RUBRO GENERADO", 4000),
                        (u"RUBRO CANCELADO", 4000),
                        (u"ESTADO", 4000),
                        (u"SOLICITUD BECA", 18000),

                        (u"VALOR", 4000),
                        (u"VALOR TOTAL", 4000),
                        (u"ABONADO", 4000),
                        (u"SALDO", 4000),
                        (u"VENCIDO", 4000),
                        (u"CANCELADO", 4000),
                        (u"MAIL INSTITUCIONAL", 4000),
                        (u"FORMA DE PAGO", 6000),
                        (u"CONTRATO APROBADO", 6000),
                        (u"PAGARÉ APROBADO", 6000),
                        (u"CUOTA INICIAL PAGADA", 6000),
                        (u"CURSO", 6000),
                    ]
                    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    ws.write_merge(0, 0, 0, 14, cohorte.descripcion +'_'+cohorte.maestriaadmision.descripcion, estilo)
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]

                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    if cohorte.maestriaadmision.carrera.malla().tiene_itinerario_malla_especialidad():
                        if int(request.GET['mencion']) != 0:
                            if int(request.GET['mencion']) == 3:
                                listadoadmitidossinproceso = InscripcionCohorte.objects.filter(cohortes=cohorte, status=True,tipocobro__in=[2,3], itinerario=0).order_by('inscripcionaspirante__persona__apellido1', 'inscripcionaspirante__persona__apellido2')
                            else:
                                listadoadmitidossinproceso = InscripcionCohorte.objects.filter(cohortes=cohorte, status=True,tipocobro__in=[2,3], itinerario=int(request.GET['mencion'])).order_by('inscripcionaspirante__persona__apellido1', 'inscripcionaspirante__persona__apellido2')
                        else:
                            listadoadmitidossinproceso = InscripcionCohorte.objects.filter(cohortes=cohorte, status=True, tipocobro__in=[2, 3]).order_by('inscripcionaspirante__persona__apellido1', 'inscripcionaspirante__persona__apellido2')
                    if int(request.GET['estado']) > 0:
                        listadoadmitidossinproceso = InscripcionCohorte.objects.filter(cohortes=cohorte, status=True, tipocobro__in=[2, 3], formapagopac__id=int(request.GET['estado'])).order_by('inscripcionaspirante__persona__apellido1', 'inscripcionaspirante__persona__apellido2')
                    else:
                        listadoadmitidossinproceso = InscripcionCohorte.objects.filter(cohortes=cohorte, status=True,tipocobro__in=[2,3]).order_by('inscripcionaspirante__persona__apellido1', 'inscripcionaspirante__persona__apellido2')

                    row_num = 1
                    row_numprimera = 0
                    for lista in listadoadmitidossinproceso:
                        row_num += 1
                        if lista.inscripcionaspirante.persona.cedula:
                            campo2 = lista.inscripcionaspirante.persona.cedula
                        if lista.inscripcionaspirante.persona.pasaporte:
                            campo2 = lista.inscripcionaspirante.persona.pasaporte
                        campo5 = lista.inscripcionaspirante.persona.apellido1 + ' ' + lista.inscripcionaspirante.persona.apellido2 + ' ' + lista.inscripcionaspirante.persona.nombres
                        campo9 = lista.inscripcionaspirante.persona.email
                        campo22 = lista.inscripcionaspirante.persona.emailinst
                        campo10 = lista.inscripcionaspirante.persona.telefono
                        campo11 = 'NO'
                        campo12 = 'NO'
                        campo13 = ''
                        #Modoficar se relaciona con la tabla rubro

                        campo15='No existen rubros'
                        campo16='No existe rubros'
                        campo17='No existe rubros'
                        campo18='No existe rubros'
                        campo19='No existe rubros'
                        campo20='No existe rubros'
                        campo21='Sin Cancelar aún'
                        campo23='NO INSCRITO'

                        campo15 = lista.total_generado_rubro()
                        campo16 = lista.total_generado_rubro()
                        campo17 = lista.total_pagado_rubro_cohorte()
                        campo18 = lista.total_pendiente()

                        rubro1 = lista.rubro_set.filter(status=True).order_by('id')
                        valores = rubro1
                        #
                        for valor in valores:
                            r= Rubro.objects.get(pk=int(valor.id))
                            if Pago.objects.filter(rubro=r).exists():
                                for pago in Pago.objects.filter(rubro=r):
                                    campo21=pago.fecha
                        #
                        #     campo15,campo16,campo17,campo18  = r.valor,r.valortotal,r.total_pagado(),r.total_adeudado()
                        #
                            if r.vencido():
                                campo19='SI'
                            else:
                                campo19='NO'
                            if r.cancelado:
                                if r.esta_anulado():
                                    campo20='Anulado'
                                else:
                                    campo20='SI'
                            else:
                                campo20='NO'

                            break

                        if lista.tipocobro == 2:
                            if lista.genero_rubro_matricula():
                                campo11 = 'SI'
                            if lista.cancelo_rubro_matricula():
                                campo12 = 'SI'
                        if lista.tipocobro == 3:
                            if lista.genero_rubro_programa():
                                campo11 = 'SI'
                            if lista.cancelo_rubro_programa():
                                campo12 = 'SI'
                        if lista.tipobeca:
                            campo13 = lista.tipobeca.descuentoposgrado.nombre
                        if lista.esta_inscrito():
                            campo23 = 'INSCRITO'

                        campo24 = ''
                        if lista.itinerario != 0:
                            if lista.itinerario == 1:
                                campo24 = 'DERECHO PROCESAL CONSTITUCIONAL'
                            elif lista.itinerario == 2:
                                campo24 = 'DERECHO PROCESAL PENAL'
                        else:
                            campo24 = 'SIN MENCIÓN'

                        campo25 = lista.formapagopac.descripcion if lista.formapagopac else 'NO REGISTRA'
                        campo26 = 'SI' if lista.tiene_contrato_aprobado() == True else 'NO'
                        campo27 = 'SI' if lista.tiene_pagare_aprobado() == True else 'NO'

                        campo28 = ''
                        if lista.formapagopac:
                            if lista.formapagopac.id == 2:
                                if lista.pago_rubro_matricula():
                                    campo28 = 'SI'
                                else:
                                    campo28 = 'NO'

                        campo29 = ''
                        if lista.tiene_matricula_cohorte():
                            cur = lista.curso_matriculado()
                            if len(cur) > 0:
                                campo29 = cur[0]

                        campo14 = lista.fecha_creacion
                        campodir = lista.inscripcionaspirante.persona.direccion + ' ' + lista.inscripcionaspirante.persona.direccion2
                        row_numprimera += 1
                        ws.write(row_num, 0, row_numprimera, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo5, font_style2)
                        ws.write(row_num, 3, campo9, font_style2)
                        ws.write(row_num, 4, campodir, font_style2)
                        ws.write(row_num, 5, campo10, font_style2)
                        ws.write(row_num, 6, campo14, date_format)
                        ws.write(row_num, 7, campo24, date_format)
                        ws.write(row_num, 8, campo21, date_format)
                        ws.write(row_num, 9, campo11, font_style2)
                        ws.write(row_num, 10, campo20, font_style2)
                        ws.write(row_num, 11, campo23, font_style2)
                        ws.write(row_num, 12, campo13, font_style2)
                        ws.write(row_num, 13, campo15, font_style2)
                        ws.write(row_num, 14, campo16, font_style2)
                        ws.write(row_num, 15, campo17, font_style2)
                        ws.write(row_num, 16, campo18, font_style2)
                        ws.write(row_num, 17, campo19, font_style2)
                        ws.write(row_num, 18, campo20, font_style2)
                        ws.write(row_num, 19, campo22, font_style2)
                        ws.write(row_num, 20, campo25, font_style2)
                        ws.write(row_num, 21, campo26, font_style2)
                        ws.write(row_num, 22, campo27, font_style2)
                        ws.write(row_num, 23, campo28, font_style2)
                        ws.write(row_num, 24, campo29, font_style2)

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'inscribirmatricular':
                try:
                    admitido = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    data['action'] = 'inscribirmatricular'
                    data['id'] = admitido.id
                    eNivel = Nivel.objects.filter(status=True, periodo=admitido.cohortes.periodoacademico).first()
                    form = InscribirMatricularForm(initial={'maestria': admitido.cohortes.maestriaadmision.carrera,
                                                            'cohorte': admitido.cohortes.descripcion,
                                                            'modalidad': admitido.cohortes.maestriaadmision.carrera.get_modalidad_display(),
                                                            'periodo': admitido.cohortes.periodoacademico,
                                                            'admitido': admitido.inscripcionaspirante.persona,
                                                            'nivel': eNivel})
                    data['form'] = form
                    data['eNivel'] = eNivel
                    template = get_template('admitidos/inscribir_view.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'existerubroajutar':
                try:
                    data['title'] = u'Rubros vs Tabla de amotización'
                    contrato = rubroscohorte = tabla = None
                    data['inscripcioncohorte'] = ins = InscripcionCohorte.objects.get(pk=int(request.GET['idi']))
                    contrato = ins.contrato_set.filter(status=True).last()
                    data['rubroscohorte'] = rubroscohorte = Rubro.objects.filter(inscripcion=ins, cohortemaestria=ins.cohortes, status=True)
                    excluirrubros = Rubro.objects.values_list('id').filter(inscripcion=ins, cohortemaestria=ins.cohortes, status=True)
                    data['otrosrubros'] = otrosrubros = Rubro.objects.filter(persona=ins.inscripcionaspirante.persona, status=True).exclude(id__in=excluirrubros).order_by("id")
                    data['tablaamortizacion'] = tabla = contrato.tablaamortizacion_set.filter(status=True) if contrato else None
                    if tabla:
                        tiporubroarancel = TipoOtroRubro.objects.get(pk=2845)
                        data['nombrematricula'] = tiporubroarancel.nombre + ' - ' + ins.cohortes.maestriaadmision.descripcion + ' - ' + ins.cohortes.descripcion
                        data['valormatricula'] = vm = ins.Configfinanciamientocohorte.valormatricula if ins.Configfinanciamientocohorte else 0
                        total = 0
                        for valor in tabla:
                            total = total + valor.valor
                        data['total'] = total + Decimal(null_to_decimal(vm, 2)).quantize(Decimal('.01'))
                    template = get_template("comercial/rubrosvstablaamortizacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'detallepago':
                try:
                    data = {}
                    inscrito = InscripcionCohorte.objects.get(pk=request.GET['id'])
                    rubro1 = Rubro.objects.filter(inscripcion=inscrito, status=True)
                    data['rubros'] = rubro1
                    template = get_template("admitidos/detallepago.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'detallerequisitos':
                try:
                    tienerequisitos = False
                    data['inscripcioncohorte'] = inscripcioncohorte = InscripcionCohorte.objects.get(pk=request.GET['idi'])
                    inscripciondescuento = None
                    data['inscripciondescuento'] = inscripciondescuento
                    if inscripcioncohorte.evidenciarequisitosaspirante_set.filter(status=True).exists():
                        tienerequisitos = True
                    data['tienerequisitos'] = tienerequisitos
                    if inscripcioncohorte.cohortes.tienecostoexamen:
                        if inscripcioncohorte.evidenciapagoexamen_set.filter(status=True):
                            tienepagoexamen = True
                            data['pagoexamen'] = evidpagoexamen = inscripcioncohorte.evidenciapagoexamen_set.filter(status=True)[0]
                            if evidpagoexamen.estadorevision == 2:
                                bloqueasubidapago = 2
                    if InscripcionCohorte.objects.filter(pk=request.GET['idi'], grupo__isnull=True):
                        data['requisitos'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, status=True).order_by("id")
                    else:
                        gruporequisitos = RequisitosGrupoCohorte.objects.values_list('requisito_id', flat=True).filter(grupo=inscripcioncohorte.grupo, status=True)
                        data['requisitos'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, requisito_id__in=gruporequisitos, status=True).order_by("id")
                    template = get_template("admitidos/detallerequisitos.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'firmaelectronicacontratos':
                try:
                    data['title'] = 'Firma de contratos'
                    maestria = cohorte = estadof = cantidad = 0
                    bandera = False
                    filtros, s, m, url_vars = Q(status=True, estado=2), request.GET.get('s', ''), request.GET.get('m', '0'), ''
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
                            ban = True
                        else:
                            ban = False
                        filtros = filtros & Q(contratolegalizado=ban)
                        url_vars += "&estadof={}".format(estadof)
                        bandera = True

                    listcontratos = Contrato.objects.filter(filtros).order_by('fechacontrato','contratolegalizado')

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
                    return render(request, "admitidos/firmarcontratospago.html", data)
                except Exception as ex:
                    pass

            if action == 'firmarcontratopagoindividual':
                try:
                    data = {}
                    contrato = Contrato.objects.get(pk=request.GET['id'])
                    # data['integrante'] = integrante = InscripcionCohorte.objects.get(pk=request.GET['idi'])
                    data['integrante'] = integrante = contrato.inscripcion
                    data['contrato'] = contrato

                    template = get_template("admitidos/firmarindividualcontrato.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'firmarcontratopagomasivo':
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

                    template = get_template("admitidos/firmarmasivocontratos.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'html': json_content})
                except Exception as ex:
                    mensaje = 'Intentelo más tarde'
                    return JsonResponse({"result": False, "mensaje": mensaje})

            if action == 'descargarrequisitosadmision':
                try:
                    inscrito = InscripcionCohorte.objects.get(status=True, pk=int(request.GET['id']))
                    # url = '/media/recursos_zip/requistos_admision_%s.zip' % (encrypt(inscrito.id))
                    url = os.path.join(SITE_STORAGE, 'media', 'zip', 'requistos_admision.zip')
                    url_zip = url
                    fantasy_zip = zipfile.ZipFile(url, 'w')

                    requistosmaestria = RequisitosMaestria.objects.filter(status=True, cohorte=inscrito.cohortes,
                                                                          requisito__claserequisito__clasificacion__id=1).values_list(
                        'id', flat=True)
                    for requisto in requistosmaestria:
                        if EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=inscrito,
                                                                       requisitos_id=requisto,
                                                                       requisitos__requisito__claserequisito__clasificacion__id=1).exists():
                            evi = EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=inscrito,
                                                                              requisitos_id=requisto,
                                                                              requisitos__requisito__claserequisito__clasificacion__id=1).order_by(
                                '-id').first()
                            if DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia=evi).exists():
                                deta = DetalleEvidenciaRequisitosAspirante.objects.filter(status=True,
                                                                                          evidencia=evi).order_by(
                                    '-id').first()
                                if deta.estado_aprobacion == 2:
                                    carpeta_inscripcion = f"{inscrito.inscripcionaspirante.persona.cedula}/"
                                    fantasy_zip.write(deta.evidencia.archivo.path,
                                                      carpeta_inscripcion + os.path.basename(
                                                          deta.evidencia.archivo.path))
                                    # ext = deta.evidencia.archivo.__str__()[deta.evidencia.archivo.__str__().rfind("."):]
                                    # fantasy_zip.write(SITE_STORAGE + deta.evidencia.archivo.url, '%s%s' % (deta.evidencia.requisitos.requisito.nombre.replace(' ', '_'), ext.lower()))
                    fantasy_zip.close()
                    response = HttpResponse(open(url_zip, 'rb'), content_type='application/zip')
                    response['Content-Disposition'] = 'attachment; filename=actascomplexivofirmadas.zip'
                    return response
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error: %s" % ex})

            if action == 'descargarrequisitosadmisionmasivo':
                try:
                    cohorte = CohorteMaestria.objects.get(pk=int(request.GET['idc']))
                    filtro = Q(status=True, valida=True, facturado=True, inscripcioncohorte__cohortes=cohorte)

                    ide = idf = 0
                    desde = hasta = ''
                    if 'ide' in request.GET:
                        ide = int(request.GET['ide'])

                    if 'idf' in request.GET:
                        idf = int(request.GET['idf'])

                    if 'desde' in request.GET:
                        desde = request.GET['desde']

                    if 'hasta' in request.GET:
                        hasta = request.GET['hasta']

                    if ide > 0:
                        if ide == 1:
                            filtro = filtro & Q(
                                Q(inscripcioncohorte__inscripcion__matricula__id=F('inscripcioncohorte__inscripcion__matricula__id')) &
                                Q(inscripcioncohorte__inscripcion__matricula__status=True)
                            )
                        else:
                            filtro = filtro & Q(
                                Q(inscripcioncohorte__inscripcion__matricula__isnull=True)
                            )

                    if idf > 0:
                        filtro = filtro & (Q(inscripcioncohorte__formapagopac__id=int(idf)))

                    if desde and hasta:
                        filtro = filtro & Q(fecha__range=(desde, hasta))

                    elif desde:
                        filtro = filtro & Q(fecha__gte=desde)

                    elif hasta:
                        filtro = filtro & Q(fecha__lte=hasta)

                    idins = VentasProgramaMaestria.objects.filter(filtro).values_list('inscripcioncohorte__id',
                                                                                      flat=True).order_by(
                        'inscripcioncohorte__id').distinct()

                    eAdmitidos = InscripcionCohorte.objects.filter(id__in=idins).order_by('-id')

                    url = os.path.join(SITE_STORAGE, 'media', 'zip', 'requistos_admision.zip')
                    url_zip = url
                    fantasy_zip = zipfile.ZipFile(url, 'w')

                    paralelo = 'Ninguno'

                    for inscrito in eAdmitidos:
                        if inscrito.inscripcion:
                            if Matricula.objects.filter(status=True, inscripcion=inscrito.inscripcion).exists():
                                matricula = Matricula.objects.filter(status=True, inscripcion=inscrito.inscripcion).order_by('-id').first()
                                if MateriaAsignada.objects.filter(status=True, matricula=matricula).exists():
                                    paralelo = matricula.materiaasignada_set.filter(matricula__status=True, status=True).first().materia.paralelo
                                else:
                                    paralelo = 'Ninguno'
                            else:
                                paralelo = 'Ninguno'
                        else:
                            paralelo = 'Ninguno'

                        requistosmaestria = RequisitosMaestria.objects.filter(status=True, cohorte=inscrito.cohortes,
                                                                              requisito__claserequisito__clasificacion__id=1).values_list('id', flat=True)
                        for requisto in requistosmaestria:
                            if EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=inscrito,
                                                                           requisitos_id=requisto,
                                                                           requisitos__requisito__claserequisito__clasificacion__id=1).exists():
                                evi = EvidenciaRequisitosAspirante.objects.filter(status=True,
                                                                                  inscripcioncohorte=inscrito,
                                                                                  requisitos_id=requisto,
                                                                                  requisitos__requisito__claserequisito__clasificacion__id=1).order_by('-id').first()
                                if DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia=evi).exists():
                                    deta = DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia=evi).order_by('-id').first()
                                    if deta.estado_aprobacion == 2:
                                        carpeta_inscripcion = f"{paralelo}/{inscrito.inscripcionaspirante.persona.cedula} - {inscrito.inscripcionaspirante.persona.nombre_completo_inverso()}/"
                                        fantasy_zip.write(deta.evidencia.archivo.path, carpeta_inscripcion + os.path.basename(deta.evidencia.archivo.path))
                    fantasy_zip.close()
                    response = HttpResponse(open(url_zip, 'rb'), content_type='application/zip')
                    response['Content-Disposition'] = 'attachment; filename=requistos_admision.zip'
                    return response
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error: %s" % ex})

            if action == 'configuracionhorarios':
                try:
                    data['title'] = u'Configuración de horarios de programas de maestría'
                    url_vars = ''
                    filtro = Q(status=True)

                    idm = request.GET.get('idm', '0')

                    if int(idm):
                        filtro = filtro & (Q(maestria__id=int(idm)))
                        data['idm'] = int(idm)
                        url_vars += f"&idm={idm}"

                    eHorarios = HorariosProgramaMaestria.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(eHorarios, 25)
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
                    data['eHorarios'] = page.object_list
                    data["url_vars"] = url_vars
                    data["url_params"] = url_vars
                    data['eMaestrias'] = MaestriasAdmision.objects.filter(status=True, id__in=HorariosProgramaMaestria.objects.filter(status=True).values_list('maestria', flat=True))
                    return render(request, "admitidos/horarios.html", data)
                except Exception as ex:
                    pass

            if action == 'addhorariomaestria':
                try:
                    data['action'] = 'addhorariomaestria'
                    form = HorarioMaestriaAdmitidoForm()
                    data['form'] = form
                    template = get_template('admitidos/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'edithorariomaestria':
                try:
                    eHorario = HorariosProgramaMaestria.objects.get(status=True, pk=int(request.GET['id']))
                    data['action'] = 'edithorariomaestria'
                    form = HorarioMaestriaAdmitidoForm(initial={'carrera': eHorario.maestria.carrera,
                                                                'horario': eHorario.nombre,
                                                                'paralelo': eHorario.paralelo})
                    form.editar()
                    data['form'] = form
                    data['id'] = eHorario.id
                    template = get_template('admitidos/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'asignarhorario':
                try:
                    data['action'] = 'asignarhorario'
                    eAdmitido = InscripcionCohorte.objects.get(status=True, pk=int(request.GET['id']))

                    eHorario = None
                    if DetalleAtencionAdmitido.objects.filter(status=True, admitido=eAdmitido, activo=True).exists():
                        eHorario = DetalleAtencionAdmitido.objects.filter(status=True, admitido=eAdmitido, activo=True).first()
                    form = AsignarHorarioAdmitidoForm(initial={'admitido': eAdmitido.inscripcionaspirante.persona,
                                                               'maestria': eAdmitido.cohortes.maestriaadmision.carrera,
                                                               'cohorte': eAdmitido.cohortes.descripcion,
                                                               'horario': eHorario.horario if eHorario else None})

                    form.fields['horario'].queryset = HorariosProgramaMaestria.objects.filter(status=True, activo=True, maestria=eAdmitido.cohortes.maestriaadmision)
                    data['form'] = form
                    data['id'] = eAdmitido.id
                    template = get_template('admitidos/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Listado de admitidos'
                url_vars = ''
                filtro = Q(status=True, valida=True, facturado=True)

                ide = request.GET.get('ide', '0')
                idf = request.GET.get('idf', '0')
                idc = request.GET.get('idc', '0')
                desde = request.GET.get('desde', '')
                hasta = request.GET.get('hasta', '')

                if 's' in request.GET:
                    search = request.GET['s']
                    data['search'] = search
                    ss = search.split(' ')
                    if len(ss) == 1:
                        filtro = filtro & (Q(inscripcioncohorte__inscripcionaspirante__persona__apellido1__icontains=search) |
                                           Q(inscripcioncohorte__inscripcionaspirante__persona__apellido2__icontains=search) |
                                           Q(inscripcioncohorte__inscripcionaspirante__persona__nombres__icontains=search) |
                                           Q(inscripcioncohorte__inscripcionaspirante__persona__cedula__icontains=search))
                        url_vars += "&s={}".format(search)
                    elif len(ss) == 2:
                        filtro = filtro & (Q(inscripcioncohorte__inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                           Q(inscripcioncohorte__inscripcionaspirante__persona__apellido2__icontains=ss[1]))
                        url_vars += "&s={}".format(ss)
                    else:
                        filtro = filtro & (Q(inscripcioncohorte__inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                           Q(inscripcioncohorte__inscripcionaspirante__persona__apellido2__icontains=ss[1]) &
                                           Q(inscripcioncohorte__inscripcionaspirante__persona__nombres__icontains=ss[2]))
                        url_vars += "&s={}".format(ss)

                if int(idc):
                    filtro = filtro & (Q(inscripcioncohorte__cohortes__id=int(idc)))
                    data['idc'] = int(idc)
                    url_vars += f"&idc={idc}"

                if int(ide):
                    if int(ide) == 1:
                        filtro = filtro & Q(
                            Q(inscripcioncohorte__inscripcion__matricula__id=F('inscripcioncohorte__inscripcion__matricula__id')) &
                            Q(inscripcioncohorte__inscripcion__matricula__status=True)
                        )
                    else:
                        filtro = filtro & Q(
                            Q(inscripcioncohorte__inscripcion__matricula__isnull=True)
                        )
                    data['ide'] = int(ide)
                    url_vars += f"&ide={ide}"

                if int(idf):
                    filtro = filtro & (Q(inscripcioncohorte__formapagopac__id=int(idf)))
                    data['idf'] = int(idf)
                    url_vars += f"&idf={idf}"

                if desde and hasta:
                    data['desde'] = desde
                    data['hasta'] = hasta
                    filtro = filtro & Q(fecha__range=(desde, hasta))
                    url_vars += "&desde={}".format(desde)
                    url_vars += "&hasta={}".format(hasta)

                elif desde:
                    data['desde'] = desde
                    filtro = filtro & Q(fecha__gte=desde)
                    url_vars += "&desde={}".format(hasta)

                elif hasta:
                    data['hasta'] = hasta
                    filtro = filtro & Q(fecha__lte=hasta)
                    url_vars += "&hasta={}".format(hasta)

                idins = VentasProgramaMaestria.objects.filter(filtro).values_list('inscripcioncohorte__id', flat=True).order_by('inscripcioncohorte__id').distinct()

                eAdmitidos = InscripcionCohorte.objects.filter(id__in=idins).order_by('-id')
                paging = MiPaginador(eAdmitidos, 25)
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
                data['eAdmitidos'] = page.object_list
                data["url_vars"] = url_vars
                data["url_params"] = url_vars
                data['eCohortes'] = CohorteMaestria.objects.filter(status=True).order_by('-id').distinct()
                data['eAdmi'] = eAdmitidos.distinct().count()

                eMatriculados = Matricula.objects.filter(status=True, inscripcion__id__in=eAdmitidos.values_list('inscripcion__id', flat=True))
                eNoMatriculados = InscripcionCohorte.objects.filter(id__in=idins).exclude(inscripcion__id__in=eMatriculados.values_list('inscripcion__id', flat=True))

                data['eMatri'] = eMatriculados.distinct().count()
                data['eNoMatri'] = eNoMatriculados.distinct().count()
                data['eAtendidos'] = canti = DetalleAtencionAdmitido.objects.filter(status=True, admitido__in=eAdmitidos.values_list('id', flat=True)).distinct().count()
                noatendidos = 0
                if canti > eAdmitidos.distinct().count():
                    noatendidos = canti - eAdmitidos.distinct().count()
                else:
                    noatendidos = eAdmitidos.distinct().count() - canti
                data['eNoatendidos'] = noatendidos
                return render(request, "admitidos/view.html", data)
            except Exception as ex:
                pass