# -*- coding: UTF-8 -*-
from datetime import datetime, timedelta
import xlrd
import random
from xlwt import *
from xlwt import easyxf
import xlwt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.db.models import Max
from django.http import  HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template

from decorators import secure_module
from sagest.forms import AccionDocumentoRevisaForm, InformeArchivoForm, AccionDocumentoEditaDuplicaForm, \
    AperturaInformeForm, AccionDocumentoDetalleForm, InformesProcesadosForm, EvidenciaDocumentalForm, \
    AccionDocumentoRevisaActividadForm
from sagest.models import AccionDocumentoDetalle, AccionDocumentoDetalleRecord, PeriodoPoa, Departamento, \
    AccionDocumento, \
    InformeGenerado, InformeGeneradoDetalle, AperturarInforme, null_to_numeric, PoaArchivo, PoaInformeFinal, \
    ObjetivoEstrategico, InformeGeneradoFacultad, EvidenciaDocumentalPoa, RubricaPoa, TIPO_MATRIZPOAARCHIVO, \
    MatrizValoracionPoa, MatrizArchivosPoa
from settings import PERSONA_APRUEBA_POA, COPIA_POA, ACUMULAR_DOS_MESES
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import generar_nombre, addworkdays, convertir_fecha, variable_valor, log, null_to_decimal, trimestre
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, write_pdf
from sga.models import MONTH_CHOICES, MESES_CHOICES, Persona, miinstitucion, Carrera, CUENTAS_CORREOS
from sga.tasks import send_html_mail, conectar_cuenta


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    data = {'title': u'Aprobar Evidencia'}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'subir_firma':
            try:
                f = InformeArchivoForm(request.POST, request.FILES)
                if f.is_valid():
                    informegenerado = InformeGenerado.objects.get(pk=int(request.POST['id']))
                    informegenerado.fechamax = f.cleaned_data['fechamax']
                    informegenerado.procesado = True
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            newfile._name = generar_nombre("FinalconFirma", newfile._name)
                            informegenerado.archivo = newfile
                    informegenerado.save(request)
                    listacorreo = listadecorreos(informegenerado.departamento)
                    data['mes'] = MESES_CHOICES[informegenerado.mes - 1][1]
                    if informegenerado.mes == 12:
                        data['mes_revisar'] = MESES_CHOICES[0][1]
                    else:
                        data['mes_revisar'] = MESES_CHOICES[informegenerado.mes][1]

                    asunto = u"POA - INFORME DE CUMPLIMIENTO %s, %s" % (data['mes'], informegenerado.departamento)
                    persona = Persona.objects.filter(usuario__usuarioevidencia__tipousuario=2, usuario__usuarioevidencia__unidadorganica=informegenerado.departamento)[0]
                    send_html_mail(asunto, "emails/informe_final.html", {'sistema': request.session['nombresistema'], 'informe': informegenerado, 'fechamax': informegenerado.fechamax, 'mes': data['mes'], 'mes_revisar': data['mes_revisar'], 'responsable': persona.nombre_titulo(), 'recargo': persona.mi_cargo(), 't': miinstitucion()}, listacorreo, [], [informegenerado.archivo, ], cuenta=CUENTAS_CORREOS[1][1])
                    for record in informegenerado.informegeneradodetalle_set.all():
                        record.acciondocumentodetallerecord.procesado = True
                        record.acciondocumentodetallerecord.save(request)
                    log(u'Subio firma: %s' % informegenerado, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'addsubirinformesfac':
            try:
                f = InformesProcesadosForm(request.POST, request.FILES)
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
                if ext == '.pdf':
                    a = 1
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                if d.size > 6291456:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 6 Mb."})
                if f.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("informesfac_", newfile._name)
                    informefac = InformeGeneradoFacultad.objects.get(pk=request.POST['id'])
                    informefac.archivo = newfile
                    informefac.save(request)
                    log(u'Subio informes por facultad: %s' % informefac, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editarfecha':
            try:
                if int(request.POST['id']) != 0:
                    informegenerado = InformeGenerado.objects.get(pk=int(request.POST['id']))
                    aperturarinforme = AperturarInforme(informegenerado=informegenerado,
                                                        fechaold=informegenerado.fechamax,
                                                        fechanew=convertir_fecha(request.POST['fechanew']),
                                                        motivo=request.POST['motivo'])
                    aperturarinforme.save(request)
                    informegenerado.fechamax = convertir_fecha(request.POST['fechanew'])
                    informegenerado.save(request)
                    log(u'Edito fecha informe: %s' % informegenerado, request, "edit")
                else:
                    informes = InformeGenerado.objects.filter(periodopoa=int(request.POST['idp'])).order_by("departamento", "-mes", "-tipo")
                    depa = []
                    for d in informes:
                        if d.departamento not in depa:
                            depa.append(d.departamento)
                            aperturarinforme = AperturarInforme(informegenerado=d,
                                                                fechaold=d.fechamax,
                                                                fechanew=convertir_fecha(request.POST['fechanew']),
                                                                motivo=u"[INGRESO MASIVO]:%s" % request.POST['motivo'])
                            aperturarinforme.save(request)
                            d.fechamax = convertir_fecha(request.POST['fechanew'])
                            d.save(request)
                    log(u'Edito fecha informe: %s' % informes, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'con_evidencia' or action == 'sin_evidencia':
            try:
                f = AccionDocumentoRevisaForm(request.POST)
                if f.is_valid():
                    acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(pk=int(request.POST['record']))
                    acciondocumentodetallerecord.observacion_aprobacion = f.cleaned_data['observacion']
                    acciondocumentodetallerecord.usuario_aprobacion = request.user
                    acciondocumentodetallerecord.estado_accion_aprobacion = f.cleaned_data['estado_accion']
                    acciondocumentodetallerecord.fecha_aprobacion = datetime.now()
                    acciondocumentodetallerecord.save(request)
                    acciondocumentodetallerecord.acciondocumentodetalle.estado_accion = f.cleaned_data['estado_accion']
                    acciondocumentodetallerecord.acciondocumentodetalle.save(request)
                    log(u'edito documento de revision: %s' % acciondocumentodetallerecord, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'con_evidenciados' or action == 'sin_evidenciados':
            try:
                f = AccionDocumentoRevisaActividadForm(request.POST)
                if f.is_valid():
                    acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(pk=int(request.POST['record']))
                    acciondocumentodetallerecord.observacion_aprobacion = f.cleaned_data['observacion']
                    acciondocumentodetallerecord.usuario_aprobacion = request.user
                    acciondocumentodetallerecord.estado_accion_aprobacion = f.cleaned_data['rubrica'].id
                    acciondocumentodetallerecord.rubrica_aprobacion = f.cleaned_data['rubrica']
                    acciondocumentodetallerecord.fecha_aprobacion = datetime.now()
                    acciondocumentodetallerecord.save(request)
                    acciondocumentodetallerecord.acciondocumentodetalle.estado_accion = f.cleaned_data['rubrica'].id
                    acciondocumentodetallerecord.acciondocumentodetalle.estado_rubrica = f.cleaned_data['rubrica']
                    acciondocumentodetallerecord.acciondocumentodetalle.save(request)
                    log(u'edito documento de revision: %s' % acciondocumentodetallerecord, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'editarobse':
            try:
                f = AccionDocumentoEditaDuplicaForm(request.POST)
                if f.is_valid():
                    acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(pk=int(request.POST['record']))
                    if 'duplica' in request.POST:
                        if f.cleaned_data['duplica']:
                            acciondocumentodetallerecord.id = None
                            acciondocumentodetallerecord.fecha_creacion = datetime.now()
                            acciondocumentodetallerecord.usuario_creacion = request.user
                            acciondocumentodetallerecord.procesado = False
                            acciondocumentodetallerecord.status = True
                            acciondocumentodetallerecord.fecha_aprobacion = datetime.now()
                            acciondocumentodetallerecord.usuario_aprobacion = request.user
                            acciondocumentodetallerecord.fecha_revisa = datetime.now()
                            acciondocumentodetallerecord.observacion_envia = "SAGEST: DUPLICADO DE EVIDENCIA"
                            acciondocumentodetallerecord.estado_accion_aprobacion = f.cleaned_data['estado_accion']
                    acciondocumentodetallerecord.observacion_aprobacion = f.cleaned_data['observacion']
                    acciondocumentodetallerecord.save(request)
                    if 'duplica' in request.POST:
                        if f.cleaned_data['duplica']:
                            acciondocumentodetallerecord.acciondocumentodetalle.estado_accion = f.cleaned_data['estado_accion']
                            acciondocumentodetallerecord.acciondocumentodetalle.save(request)
                            log(u'duplico documento de revision: %s' % acciondocumentodetallerecord, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'eliminarfinal':
            try:
                informegenerado = InformeGenerado.objects.get(pk=int(request.POST['idi']))
                informegenerado.informegeneradodetalle_set.all().update(status=False)
                informegenerado.status = False
                informegenerado.save(request)
                log(u'elimino documento de revision: %s' % informegenerado, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'vistaprevia':
            try:
                idc = int(request.POST['idc'])
                if idc == 0:
                    data = datosinforme(int(request.POST['idp']), int(request.POST['idd']), int(request.POST['mes']))
                else:
                    data = datosinformecarrera(int(request.POST['idp']), int(request.POST['idd']), int(request.POST['mes']) ,int(request.POST['idc']))
                data['vistareco'] = request.POST['reco']
                return conviert_html_to_pdf('poa_aprobarevidencia/informe_pdf_final.html', {'pagesize': 'A4', 'data': data})
            except Exception as ex:
                pass

        if action == 'vistaprevianewformato':
            try:
                idc = int(request.POST['idc'])
                if idc == 0:
                    data = datosinforme(int(request.POST['idp']), int(request.POST['idd']), int(request.POST['mes']))
                else:
                    data = datosinformecarrera(int(request.POST['idp']), int(request.POST['idd']), int(request.POST['mes']) ,int(request.POST['idc']))
                data['vistareco'] = request.POST['reco']
                return conviert_html_to_pdf('poa_aprobarevidencia/informe_pdf_final_new.html', {'pagesize': 'A4', 'data': data})
            except Exception as ex:
                pass

        if action == 'generarinforme':
            try:
                if not Persona.objects.filter(usuario__usuarioevidencia__tipousuario=2, usuario__usuarioevidencia__unidadorganica_id=int(request.POST['idd'])).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Este departamento no tiene configurado el director, realizarlo en la opcion - Poa Usuario registra"})
                if request.POST['tipo'] == 'preliminar':
                    fechamax = addworkdays(datetime.now().date(), 2)
                    tipo = 1
                else:
                    tipo = 2
                    if datetime.now().month < 12:
                        fecha = (datetime(datetime.now().year, datetime.now().month + 1, 5, 0, 0, 0)).date()
                    else:
                        fecha = (datetime(datetime.now().year, datetime.now().month, 5, 0, 0, 0)).date()
                    fechamax = fecha  # addworkdays(fecha, 4)
                if not InformeGenerado.objects.filter(mes=int(request.POST['mes']), departamento_id=int(request.POST['idd']), periodopoa_id=int(request.POST['idp']), tipo=tipo, status=True).exists():
                    numinfo = null_to_numeric(InformeGenerado.objects.filter(periodopoa_id=int(request.POST['idp']), tipo=tipo, status=True).aggregate(secu=Max("numinfo"))['secu'])
                    informegenerado = InformeGenerado(periodopoa_id=int(request.POST['idp']),
                                                      departamento_id=int(request.POST['idd']),
                                                      mes=int(request.POST['mes']),
                                                      tipo=tipo,
                                                      fechamax=fechamax,
                                                      numinfo=numinfo + 1,
                                                      recomendacion=request.POST['recomendacion'])
                    informegenerado.save(request)
                    data = datosinforme(int(request.POST['idp']), int(request.POST['idd']), int(request.POST['mes']))
                    data['tipoid'] = tipo
                    filepre = write_pdf('poa_aprobarevidencia/informe_pdf_final.html', {'pagesize': 'A4', 'data': data}, generar_nombre(request.POST['tipo'], 'prueba.pdf'))
                    if filepre:
                        informegenerado.archivo = filepre
                        informegenerado.save(request)
                        # if request.POST['tipo'] == 'preliminar':
                        #     listacorreo = listadecorreos(informegenerado.departamento)
                        #     asunto = u"POA - INFORME PRELIMINAR %s, %s" % (data['mes'], informegenerado.departamento)
                        #     persona = Persona.objects.filter(usuario__usuarioevidencia__tipousuario=2, usuario__usuarioevidencia__unidadorganica__id=int(request.POST['idd']))[0]
                        # send_html_mail(asunto, "emails/informe_preliminar.html", {'sistema': request.session['nombresistema'], 'informe': informegenerado, 'mes': data['mes'], 'responsable': persona.nombre_titulo(), 'recargo': persona.mi_cargo(), 't': miinstitucion()}, listacorreo, [], [informegenerado.archivo, ])
                    for p in data['evidencia_mes']:
                        informedetalle = InformeGeneradoDetalle(informegenerado_id=informegenerado.id,
                                                                acciondocumentodetallerecord_id=p.id,
                                                                observacion_aprobacion=p.observacion_aprobacion,
                                                                estado_accion_aprobacion=p.estado_accion_aprobacion)
                        informedetalle.save(request)
                    for p in data['evidencia_anterior']:
                        informedetalle = InformeGeneradoDetalle(informegenerado_id=informegenerado.id,
                                                                acciondocumentodetallerecord_id=p.id,
                                                                observacion_aprobacion=p.observacion_aprobacion,
                                                                estado_accion_aprobacion=p.estado_accion_aprobacion)
                        informedetalle.save(request)
                    log(u'genero informe: %s' % informegenerado, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'generarinformefacultad':
            try:
                if InformeGeneradoFacultad.objects.filter(informegenerado=request.POST['idinformegenerado']).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Informe Facultad ya existe"})
                informegenerado = InformeGeneradoFacultad(informegenerado_id=request.POST['idinformegenerado'],
                                                          recomendacion=request.POST['recomendacion'])
                informegenerado.save(request)
                log(u'genero informe de facultad: %s' % informegenerado, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'generarinformecarrera':
            try:
                if request.POST['idc'] == '0':
                    personadirector = None
                    if not Persona.objects.filter(usuario__usuarioevidencia__tipousuario=2, usuario__usuarioevidencia__unidadorganica_id=int(request.POST['idd']),usuario__usuarioevidencia__carrera__isnull=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Este departamento no tiene configurado el director, realizarlo en la opcion - Poa Usuario registra"})
                    else:
                        personadirector = Persona.objects.filter(usuario__usuarioevidencia__tipousuario=2, usuario__usuarioevidencia__unidadorganica_id=int(request.POST['idd']),usuario__usuarioevidencia__carrera__isnull=True)[0]
                    if request.POST['tipo'] == 'preliminar':
                        fechamax = addworkdays(datetime.now().date(), 2)
                        tipo = 1
                    else:
                        tipo = 2
                        if datetime.now().month < 12:
                            fecha = (datetime(datetime.now().year, datetime.now().month + 1, 5, 0, 0, 0)).date()
                        else:
                            fecha = (datetime(datetime.now().year, datetime.now().month, 5, 0, 0, 0)).date()
                        fechamax = fecha  # addworkdays(fecha, 4)
                    if not InformeGenerado.objects.filter(mes=int(request.POST['mes']), departamento_id=int(request.POST['idd']), periodopoa_id=int(request.POST['idp']),carrera__isnull=True, tipo=tipo, status=True).exists():
                        numinfo = null_to_numeric(InformeGenerado.objects.filter(periodopoa_id=int(request.POST['idp']), tipo=tipo, status=True).aggregate(secu=Max("numinfo"))['secu'])
                        informegenerado = InformeGenerado(periodopoa_id=int(request.POST['idp']),
                                                          departamento_id=int(request.POST['idd']),
                                                          mes=int(request.POST['mes']),
                                                          tipo=tipo,
                                                          fechamax=fechamax,
                                                          personadirector=personadirector,
                                                          numinfo=numinfo + 1,
                                                          recomendacion=request.POST['recomendacion'])
                        informegenerado.save(request)
                        data = datosinforme(int(request.POST['idp']), int(request.POST['idd']), int(request.POST['mes']))
                        data['tipoid'] = tipo
                        filepre = write_pdf('poa_aprobarevidencia/informe_pdf_final_new.html', {'pagesize': 'A4', 'data': data}, generar_nombre(request.POST['tipo'], 'prueba.pdf'))
                        if filepre:
                            informegenerado.archivo = filepre
                            informegenerado.save(request)
                            # if request.POST['tipo'] == 'preliminar':
                            #     listacorreo = listadecorreos(informegenerado.departamento)
                            #     asunto = u"POA - INFORME PRELIMINAR %s, %s" % (data['mes'], informegenerado.departamento)
                            #     persona = Persona.objects.filter(usuario__usuarioevidencia__tipousuario=2, usuario__usuarioevidencia__carrera__isnull=True, usuario__usuarioevidencia__unidadorganica__id=int(request.POST['idd']))[0]
                            #     send_html_mail(asunto, "emails/informe_preliminar.html", {'sistema': request.session['nombresistema'], 'informe': informegenerado, 'mes': data['mes'], 'responsable': persona.nombre_titulo(), 'recargo': persona.mi_cargo(), 't': miinstitucion()}, listacorreo, [], [informegenerado.archivo, ])
                        for p in data['evidencia_mes']:
                            informedetalle = InformeGeneradoDetalle(informegenerado_id=informegenerado.id,
                                                                    acciondocumentodetallerecord_id=p.id,
                                                                    observacion_aprobacion=p.observacion_aprobacion,
                                                                    estado_accion_aprobacion=p.estado_accion_aprobacion)
                            informedetalle.save(request)
                        for p in data['evidencia_anterior']:
                            informedetalle = InformeGeneradoDetalle(informegenerado_id=informegenerado.id,
                                                                    acciondocumentodetallerecord_id=p.id,
                                                                    observacion_aprobacion=p.observacion_aprobacion,
                                                                    estado_accion_aprobacion=p.estado_accion_aprobacion)
                            informedetalle.save(request)
                    log(u'genero informe por carrera: %s' % informegenerado, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    personacarrera = None
                    personadirector = None
                    if not Persona.objects.filter(usuario__usuarioevidencia__tipousuario=3, usuario__usuarioevidencia__unidadorganica_id=int(request.POST['idd']), usuario__usuarioevidencia__carrera__id=int(request.POST['idc'])).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Este departamento no tiene configurado el director de carrera, realizarlo en la opcion - Poa Usuario registra"})
                    else:
                        personacarrera = Persona.objects.filter(usuario__usuarioevidencia__tipousuario=3, usuario__usuarioevidencia__unidadorganica_id=int(request.POST['idd']), usuario__usuarioevidencia__carrera__id=int(request.POST['idc']))[0]
                    if not Persona.objects.filter(usuario__usuarioevidencia__tipousuario=2, usuario__usuarioevidencia__unidadorganica_id=int(request.POST['idd']),usuario__usuarioevidencia__carrera__isnull=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Este departamento no tiene configurado el director, realizarlo en la opcion - Poa Usuario registra"})
                    else:
                        personadirector = Persona.objects.filter(usuario__usuarioevidencia__tipousuario=2, usuario__usuarioevidencia__unidadorganica_id=int(request.POST['idd']),usuario__usuarioevidencia__carrera__isnull=True)[0]
                    if request.POST['tipo'] == 'preliminar':
                        fechamax = addworkdays(datetime.now().date(), 2)
                        tipo = 1
                    else:
                        tipo = 2
                        if datetime.now().month < 12:
                            fecha = (datetime(datetime.now().year, datetime.now().month + 1, 5, 0, 0, 0)).date()
                        else:
                            fecha = (datetime(datetime.now().year, datetime.now().month, 5, 0, 0, 0)).date()
                        fechamax = fecha  # addworkdays(fecha, 4)
                    if not InformeGenerado.objects.filter(mes=int(request.POST['mes']), departamento_id=int(request.POST['idd']), carrera_id=int(request.POST['idc']), periodopoa_id=int(request.POST['idp']), tipo=tipo, status=True).exists():
                        numinfo = null_to_numeric(InformeGenerado.objects.filter(periodopoa_id=int(request.POST['idp']), tipo=tipo, status=True).aggregate(secu=Max("numinfo"))['secu'])
                        informegenerado = InformeGenerado(periodopoa_id=int(request.POST['idp']),
                                                          departamento_id=int(request.POST['idd']),
                                                          mes=int(request.POST['mes']),
                                                          tipo=tipo,
                                                          fechamax=fechamax,
                                                          numinfo=numinfo + 1,
                                                          recomendacion=request.POST['recomendacion'],
                                                          personacarrera=personacarrera,
                                                          personadirector=personadirector,
                                                          carrera_id=int(request.POST['idc']))
                        informegenerado.save(request)
                        data = datosinformecarrera(int(request.POST['idp']), int(request.POST['idd']), int(request.POST['mes']), int(request.POST['idc']))
                        data['tipoid'] = tipo
                        filepre = write_pdf('poa_aprobarevidencia/informe_pdf_final_new.html', {'pagesize': 'A4', 'data': data}, generar_nombre(request.POST['tipo'], 'prueba.pdf'))
                        if filepre:
                            informegenerado.archivo = filepre
                            informegenerado.save(request)
                            # if request.POST['tipo'] == 'preliminar':
                            #     listacorreo = listadecorreos(informegenerado.departamento)
                            #     asunto = u"POA - INFORME PRELIMINAR %s, %s" % (data['mes'], informegenerado.departamento)
                            #     persona = Persona.objects.filter(usuario__usuarioevidencia__tipousuario=3, usuario__usuarioevidencia__carrera_id=int(request.POST['idc']), usuario__usuarioevidencia__unidadorganica__id=int(request.POST['idd']))[0]
                            #     send_html_mail(asunto, "emails/informe_preliminar.html", {'sistema': request.session['nombresistema'], 'informe': informegenerado, 'mes': data['mes'], 'responsable': persona.nombre_titulo(), 'recargo': persona.mi_cargo(), 't': miinstitucion()}, listacorreo, [], [informegenerado.archivo, ])
                        for p in data['evidencia_mes']:
                            informedetalle = InformeGeneradoDetalle(informegenerado_id=informegenerado.id,
                                                                    acciondocumentodetallerecord_id=p.id,
                                                                    observacion_aprobacion=p.observacion_aprobacion,
                                                                    estado_accion_aprobacion=p.estado_accion_aprobacion)
                            informedetalle.save(request)
                        for p in data['evidencia_anterior']:
                            informedetalle = InformeGeneradoDetalle(informegenerado_id=informegenerado.id,
                                                                    acciondocumentodetallerecord_id=p.id,
                                                                    observacion_aprobacion=p.observacion_aprobacion,
                                                                    estado_accion_aprobacion=p.estado_accion_aprobacion)
                            informedetalle.save(request)
                    log(u'genero informe por carrera: %s' % informegenerado, request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'generarinformedos':
            try:
                if request.POST['idc'] == '0':
                    personadirector = None
                    if not Persona.objects.filter(usuario__usuarioevidencia__tipousuario=2, usuario__usuarioevidencia__unidadorganica_id=int(request.POST['idd']),usuario__usuarioevidencia__carrera__isnull=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Este departamento no tiene configurado el director, realizarlo en la opcion - Poa Usuario registra"})
                    else:
                        personadirector = Persona.objects.filter(usuario__usuarioevidencia__tipousuario=2, usuario__usuarioevidencia__unidadorganica_id=int(request.POST['idd']),usuario__usuarioevidencia__carrera__isnull=True)[0]
                    if request.POST['tipo'] == 'preliminar':
                        fechamax = addworkdays(datetime.now().date(), 2)
                        tipo = 1
                    else:
                        tipo = 2
                        if datetime.now().month < 12:
                            fecha = (datetime(datetime.now().year, datetime.now().month + 1, 5, 0, 0, 0)).date()
                        else:
                            fecha = (datetime(datetime.now().year, datetime.now().month, 5, 0, 0, 0)).date()
                        fechamax = fecha  # addworkdays(fecha, 4)
                    if not InformeGenerado.objects.filter(mes=int(request.POST['mes']), departamento_id=int(request.POST['idd']), periodopoa_id=int(request.POST['idp']),carrera__isnull=True, tipo=tipo, status=True).exists():
                        numinfo = null_to_numeric(InformeGenerado.objects.filter(periodopoa_id=int(request.POST['idp']), tipo=tipo, status=True).aggregate(secu=Max("numinfo"))['secu'])
                        informegenerado = InformeGenerado(periodopoa_id=int(request.POST['idp']),
                                                          departamento_id=int(request.POST['idd']),
                                                          mes=int(request.POST['mes']),
                                                          tipo=tipo,
                                                          fechamax=fechamax,
                                                          personadirector=personadirector,
                                                          numinfo=numinfo + 1,
                                                          recomendacion=request.POST['recomendacion'])
                        informegenerado.save(request)
                        data = datosinforme(int(request.POST['idp']), int(request.POST['idd']), int(request.POST['mes']))
                        data['tipoid'] = tipo
                        filepre = write_pdf('poa_aprobarevidencia/informe_pdf_final_new.html', {'pagesize': 'A4', 'data': data}, generar_nombre(request.POST['tipo'], 'prueba.pdf'))
                        if filepre:
                            informegenerado.archivo = filepre
                            informegenerado.save(request)
                            # if request.POST['tipo'] == 'preliminar':
                            #     listacorreo = listadecorreos(informegenerado.departamento)
                            #     asunto = u"POA - INFORME PRELIMINAR %s, %s" % (data['mes'], informegenerado.departamento)
                            #     persona = Persona.objects.filter(usuario__usuarioevidencia__tipousuario=2, usuario__usuarioevidencia__carrera__isnull=True, usuario__usuarioevidencia__unidadorganica__id=int(request.POST['idd']))[0]
                            #     send_html_mail(asunto, "emails/informe_preliminar.html", {'sistema': request.session['nombresistema'], 'informe': informegenerado, 'mes': data['mes'], 'responsable': persona.nombre_titulo(), 'recargo': persona.mi_cargo(), 't': miinstitucion()}, listacorreo, [], [informegenerado.archivo, ])
                        for p in data['evidencia_mes']:
                            informedetalle = InformeGeneradoDetalle(informegenerado_id=informegenerado.id,
                                                                    acciondocumentodetallerecord_id=p.id,
                                                                    observacion_aprobacion=p.observacion_aprobacion,
                                                                    estado_accion_aprobacion=p.estado_accion_aprobacion)
                            informedetalle.save(request)
                        for p in data['evidencia_anterior']:
                            informedetalle = InformeGeneradoDetalle(informegenerado_id=informegenerado.id,
                                                                    acciondocumentodetallerecord_id=p.id,
                                                                    observacion_aprobacion=p.observacion_aprobacion,
                                                                    estado_accion_aprobacion=p.estado_accion_aprobacion)
                            informedetalle.save(request)
                    log(u'genero informe por carrera: %s' % informegenerado, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    personacarrera = None
                    personadirector = None
                    if not Persona.objects.filter(usuario__usuarioevidencia__tipousuario=3, usuario__usuarioevidencia__unidadorganica_id=int(request.POST['idd']), usuario__usuarioevidencia__carrera__id=int(request.POST['idc'])).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Este departamento no tiene configurado el director de carrera, realizarlo en la opcion - Poa Usuario registra"})
                    else:
                        personacarrera = Persona.objects.filter(usuario__usuarioevidencia__tipousuario=3, usuario__usuarioevidencia__unidadorganica_id=int(request.POST['idd']), usuario__usuarioevidencia__carrera__id=int(request.POST['idc']))[0]
                    if not Persona.objects.filter(usuario__usuarioevidencia__tipousuario=2, usuario__usuarioevidencia__unidadorganica_id=int(request.POST['idd']),usuario__usuarioevidencia__carrera__isnull=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Este departamento no tiene configurado el director, realizarlo en la opcion - Poa Usuario registra"})
                    else:
                        personadirector = Persona.objects.filter(usuario__usuarioevidencia__tipousuario=2, usuario__usuarioevidencia__unidadorganica_id=int(request.POST['idd']),usuario__usuarioevidencia__carrera__isnull=True)[0]
                    if request.POST['tipo'] == 'preliminar':
                        fechamax = addworkdays(datetime.now().date(), 2)
                        tipo = 1
                    else:
                        tipo = 2
                        if datetime.now().month < 12:
                            fecha = (datetime(datetime.now().year, datetime.now().month + 1, 5, 0, 0, 0)).date()
                        else:
                            fecha = (datetime(datetime.now().year, datetime.now().month, 5, 0, 0, 0)).date()
                        fechamax = fecha  # addworkdays(fecha, 4)
                    if not InformeGenerado.objects.filter(mes=int(request.POST['mes']), departamento_id=int(request.POST['idd']), carrera_id=int(request.POST['idc']), periodopoa_id=int(request.POST['idp']), tipo=tipo, status=True).exists():
                        numinfo = null_to_numeric(InformeGenerado.objects.filter(periodopoa_id=int(request.POST['idp']), tipo=tipo, status=True).aggregate(secu=Max("numinfo"))['secu'])
                        informegenerado = InformeGenerado(periodopoa_id=int(request.POST['idp']),
                                                          departamento_id=int(request.POST['idd']),
                                                          mes=int(request.POST['mes']),
                                                          tipo=tipo,
                                                          fechamax=fechamax,
                                                          numinfo=numinfo + 1,
                                                          recomendacion=request.POST['recomendacion'],
                                                          personacarrera=personacarrera,
                                                          personadirector=personadirector,
                                                          carrera_id=int(request.POST['idc']))
                        informegenerado.save(request)
                        data = datosinformecarrera(int(request.POST['idp']), int(request.POST['idd']), int(request.POST['mes']), int(request.POST['idc']))
                        data['tipoid'] = tipo
                        filepre = write_pdf('poa_aprobarevidencia/informe_pdf_final_new.html', {'pagesize': 'A4', 'data': data}, generar_nombre(request.POST['tipo'], 'prueba.pdf'))
                        if filepre:
                            informegenerado.archivo = filepre
                            informegenerado.save(request)
                            # if request.POST['tipo'] == 'preliminar':
                            #     listacorreo = listadecorreos(informegenerado.departamento)
                            #     asunto = u"POA - INFORME PRELIMINAR %s, %s" % (data['mes'], informegenerado.departamento)
                            #     persona = Persona.objects.filter(usuario__usuarioevidencia__tipousuario=3, usuario__usuarioevidencia__carrera_id=int(request.POST['idc']), usuario__usuarioevidencia__unidadorganica__id=int(request.POST['idd']))[0]
                            #     send_html_mail(asunto, "emails/informe_preliminar.html", {'sistema': request.session['nombresistema'], 'informe': informegenerado, 'mes': data['mes'], 'responsable': persona.nombre_titulo(), 'recargo': persona.mi_cargo(), 't': miinstitucion()}, listacorreo, [], [informegenerado.archivo, ])
                        for p in data['evidencia_mes']:
                            informedetalle = InformeGeneradoDetalle(informegenerado_id=informegenerado.id,
                                                                    acciondocumentodetallerecord_id=p.id,
                                                                    observacion_aprobacion=p.observacion_aprobacion,
                                                                    estado_accion_aprobacion=p.estado_accion_aprobacion)
                            informedetalle.save(request)
                        for p in data['evidencia_anterior']:
                            informedetalle = InformeGeneradoDetalle(informegenerado_id=informegenerado.id,
                                                                    acciondocumentodetallerecord_id=p.id,
                                                                    observacion_aprobacion=p.observacion_aprobacion,
                                                                    estado_accion_aprobacion=p.estado_accion_aprobacion)
                            informedetalle.save(request)
                    log(u'genero informe por carrera: %s' % informegenerado, request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'agregar_archivo_departamento':
            try:
                f = AccionDocumentoDetalleForm(request.POST, request.FILES)
                if f.is_valid():
                    periodopoa = PeriodoPoa.objects.get(pk=int(request.POST['idp']))
                    departamento = Departamento.objects.get(pk=int(request.POST['idd']))
                    poaarchivo = PoaArchivo(periodopoa=periodopoa,
                                            unidadorganica=departamento,
                                            observacion=f.cleaned_data['observacion_envia'],
                                            fecha=datetime.now())
                    poaarchivo.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            newfile._name = generar_nombre("archivo_depa", newfile._name)
                            poaarchivo.archivo = newfile
                            poaarchivo.save(request)
                    log(u'edito archivo departamento: %s' % poaarchivo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'informe_form':
            try:
                poainformefinal = PoaInformeFinal(periodopoa_id=request.POST['idp'],
                                                  unidadorganica_id=request.POST['idd'],
                                                  fecha=datetime.now(),
                                                  observacion=request.POST['obs'],
                                                  objetivosplanificados=request.POST['objetivos'],
                                                  objetivos=request.POST['total_objetivos'],
                                                  planificado=float(request.POST['planifiacado']),
                                                  ejecutado=float(request.POST['ejecutado']),
                                                  ejecutadoparcial=float(request.POST['parcial']),
                                                  nocumple=float(request.POST['nocum']),
                                                  pendiente=float(request.POST['pendiente']),
                                                  cumplimiento=float(request.POST['cumplimiento']),
                                                  mes=request.POST['mes'])
                poainformefinal.save(request)
                log(u'genero informe poa final: %s' % poainformefinal, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'descargarpoapdf':
            try:
                departamento = Departamento.objects.get(pk=request.POST['iddepartamento'])
                periodopoa = PeriodoPoa.objects.get(pk=request.POST['idperiodopoa'])
                reportepdf = departamento.pdf_poadepartamento(periodopoa)
                return reportepdf
            except Exception as ex:
                pass

        if action == 'editevidenciadocumental':
            try:
                persona = request.session['persona']
                evidencia = EvidenciaDocumentalPoa.objects.get(pk=request.POST['codievid'])
                evidencia.evidenciaaprobador = request.POST['evidencia']
                evidencia.descripcionaprobador = request.POST['descripcion']
                evidencia.fechaaprobador = datetime.now().date()
                evidencia.personaaprobador = persona
                evidencia.save(request)
                log(u'Modifico evidencia documental: %s ' % evidencia, request, "edit")
                return JsonResponse({"result": "ok", "evidencia": evidencia.evidenciaaprobador, "descripcion": evidencia.descripcionaprobador, "fechaaprobador": evidencia.fechaaprobador })
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'consultaevidenciadocumental':
            try:
                evidenciadocumental = EvidenciaDocumentalPoa.objects.get(pk=request.POST['codievid'])
                if evidenciadocumental.evidenciaaprobador:
                    evidencia = evidenciadocumental.evidenciaaprobador
                else:
                    evidencia = evidenciadocumental.evidencia
                if evidenciadocumental.descripcionaprobador:
                    descripcion = evidenciadocumental.descripcionaprobador
                else:
                    descripcion = evidenciadocumental.descripcion
                idevidencia = evidenciadocumental.id
                return JsonResponse({"result": "ok", 'evidencia': evidencia, 'descripcion': descripcion, 'idevidencia': idevidencia})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'addfechaaperturaevidencia':
            try:
                iddep = request.POST['iddep']
                idper = request.POST['idper']
                fecha = request.POST['fecha']
                aperturafecha = InformeGenerado(periodopoa_id=idper,
                                                departamento_id=iddep,
                                                fechamax=fecha)
                aperturafecha.save(request)
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad'})

        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'descargarlistado':
                try:
                    __author__ = 'Unemi'
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('DEPARTAMENTOS')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_poa' + random.randint(1, 10000).__str__() + '.xls'
                    row_num = 0
                    columns = [
                        (u"N.", 2000),
                        (u"DEPARTAMENTO", 18000),
                        (u"PUNTAJE", 2000),
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listado = MatrizArchivosPoa.objects.filter(matrizvaloracionpoa__evaluacionperiodo__informeanual=True, matrizvaloracionpoa__evaluacionperiodo__periodopoa=int(request.GET['idp']), tipomatrizarchivo=3, status=True).order_by('-totalobjetivo')
                    row_num = 0
                    for lista in listado:
                        row_num += 1
                        campo2 = lista.matrizvaloracionpoa.departamento.nombre
                        campo3 = lista.totalobjetivo

                        ws.write(row_num, 0, row_num, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'revisadepartamento':
                try:
                    data['title'] = u'Departamento aprobar documentos.'
                    if int(request.GET['idp']) < 4:
                        data['departamento'] = Departamento.objects.filter(objetivoestrategico__periodopoa_id=int(request.GET['idp']), objetivoestrategico__status=True).distinct()
                        data['periodo'] = int(request.GET['idp'])
                        data['periodopoa'] = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                        data['reporte_0'] = obtener_reporte('informe_general_final')
                        return render(request, "poa_aprobarevidencia/revisadepartamento.html", data)
                    else:
                        # data['departamento'] = Departamento.objects.filter(objetivoestrategico__periodopoa_id=int(request.GET['idp']), objetivoestrategico__status=True).distinct()
                        data['departamento'] = ObjetivoEstrategico.objects.values('departamento__id', 'departamento__nombre', 'carrera__id','carrera__nombre').filter(periodopoa_id=int(request.GET['idp']), status=True).distinct().order_by('departamento__nombre', 'departamento__id', 'carrera__id','carrera__nombre')
                        data['periodo'] = int(request.GET['idp'])
                        data['periodopoa'] = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                        data['reporte_0'] = obtener_reporte('informe_general_final')
                        return render(request, "poa_aprobarevidencia/revisadepartamentocarrera.html", data)
                except Exception as ex:
                    pass

            if action == 'revisadepartamentodos':
                try:
                    data['title'] = u'Departamento aprobar documentos.'
                    # data['departamento'] = ObjetivoEstrategico.objects.values('departamento__id', 'departamento__nombre', 'carrera__id','carrera__nombre').filter(periodopoa_id=int(request.GET['idp']), status=True).distinct().order_by('departamento__nombre', 'departamento__id', 'carrera__id','carrera__nombre')
                    data['departamento'] = ObjetivoEstrategico.objects.filter(periodopoa_id=int(request.GET['idp']), status=True).order_by('departamento_id', 'carrera_id', 'gestion_id').distinct('departamento_id','carrera_id','gestion_id')
                    data['periodo'] = int(request.GET['idp'])
                    data['periodopoa'] = periodopoa = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                    data['evaluacionperiodopoa'] = evaluacionperiodopoa = periodopoa.evaluacionperiodopoa_set.filter(status=True).order_by('id')
                    data['totalevaluacionperiodopoa'] = evaluacionperiodopoa.count()
                    data['listabloquear'] = MatrizValoracionPoa.objects.values_list('departamento_id', flat=True).filter(matrizarchivospoa__tipomatrizarchivo=3, evaluacionperiodo__informeanual=True, evaluacionperiodo__periodopoa=periodopoa, status=True)
                    data['tipomatrizarchivo'] = TIPO_MATRIZPOAARCHIVO
                    data['reporte_0'] = obtener_reporte('informe_general_final')
                    return render(request, "poa_aprobarevidencia/revisadepartamentodos.html", data)
                except Exception as ex:
                    pass

            elif action == 'addsubirinformesfac':
                try:
                    data['title'] = u'Informe'
                    data['form'] = InformesProcesadosForm
                    data['idinformegen'] = request.GET['idinformegen']
                    data['informefac'] = InformeGeneradoFacultad.objects.get(pk=request.GET['idinformegen'])
                    template = get_template("poa_aprobarevidencia/add_informesgenerados.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'informepdf_facultad':
                try:
                    data['title'] = u'Adicionar Programa'
                    adduserdata(request, data)
                    # informedetallado = InformeGeneradoDetalle.objects.filter(informegenerado=informegenerado,status=True)
                    data = datosinformegeneralfacultad(int(request.GET['idperiodo']), int(request.GET['iddepartamento']), int(request.GET['idmes']))
                    data['departamentoss'] = Departamento.objects.get(pk=int(request.GET['iddepartamento']))
                    data['carrerasinforme'] = InformeGenerado.objects.filter(periodopoa_id=int(request.GET['idperiodo']), departamento_id=int(request.GET['iddepartamento']),mes=int(request.GET['idmes']), tipo=2, carrera__isnull=False, status=True)
                    data['obse'] = request.GET['obse']
                    data['fechahoy'] = datetime.now().date()
                    data['periodo'] = PeriodoPoa.objects.get(pk=int(request.GET['idperiodo']))
                    return conviert_html_to_pdf(
                        'poa_aprobarevidencia/informefacultad_pdf.html',
                        {
                            'pagesize': 'A4',
                            'listaacciones': data
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'poadepartamento':
                try:
                    data['title'] = u'Aprobación POA.'
                    if int(request.GET['idp']) < 4:
                        data['departamento'] = Departamento.objects.get(pk=int(request.GET['idd']))
                        data['meses'] = MONTH_CHOICES
                        data['periodopoa'] = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                        data['idp'] = int(request.GET['idp'])
                        data['idd'] = int(request.GET['idd'])
                        data['mes_actual'] = 12 if PeriodoPoa.objects.get(pk=int(request.GET['idp'])).anio < datetime.now().year else datetime.now().month
                        data['documento'] = AccionDocumento.objects.filter(status=True, acciondocumentodetalle__status=True, indicadorpoa__status=True, indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']), indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).order_by('indicadorpoa__objetivooperativo', 'indicadorpoa').distinct()
                        return render(request, "poa_aprobarevidencia/poadepartamento.html", data)
                    else:
                        data['departamento'] = Departamento.objects.get(pk=int(request.GET['idd']))
                        data['meses'] = MONTH_CHOICES
                        data['periodopoa'] = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                        data['idp'] = int(request.GET['idp'])
                        data['idd'] = int(request.GET['idd'])
                        data['idc'] = idc = int(request.GET['idc'])
                        data['carrera'] = ''
                        data['mes_actual'] = 12 if PeriodoPoa.objects.get(pk=int(request.GET['idp'])).anio < datetime.now().year else datetime.now().month
                        lista = []
                        if idc == 0:
                            data['documento'] = acciones = AccionDocumento.objects.filter(status=True,acciondocumentodetalle__status=True,indicadorpoa__status=True,indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']),indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True, indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).order_by('indicadorpoa__objetivooperativo', 'indicadorpoa').distinct()
                        else:
                            data['carrera'] = Carrera.objects.get(pk=int(request.GET['idc']))
                            data['documento'] = acciones = AccionDocumento.objects.filter(status=True,acciondocumentodetalle__status=True,indicadorpoa__status=True,indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']),indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__id=int(request.GET['idc']), indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).order_by('indicadorpoa__objetivooperativo', 'indicadorpoa').distinct()
                        mesesevidencias=AccionDocumentoDetalle.objects.select_related().filter(acciondocumento__in=acciones, status=True).distinct()
                        for mevidencias in mesesevidencias:
                            lista.append(mevidencias.fin.month)
                        data['mesesevidencias'] = lista
                        return render(request, "poa_aprobarevidencia/poadepartamentocarrera.html", data)
                except Exception as ex:
                    pass

            elif action == 'poadepartamentodos':
                try:
                    data['title'] = u'Aprobación POA.'
                    data['departamento'] = Departamento.objects.get(pk=int(request.GET['idd']))
                    data['meses'] = MONTH_CHOICES
                    data['periodopoa'] = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                    data['idp'] = int(request.GET['idp'])
                    data['idd'] = int(request.GET['idd'])
                    data['idc'] = idc = int(request.GET['idc'])
                    data['carrera'] = ''
                    data['mes_actual'] = 12 if PeriodoPoa.objects.get(pk=int(request.GET['idp'])).anio < datetime.now().year else datetime.now().month
                    lista = []
                    if idc == 0:
                        data['documento'] = acciones = AccionDocumento.objects.filter(status=True,acciondocumentodetalle__status=True,indicadorpoa__status=True,indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']),indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True, indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).order_by('indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__orden','indicadorpoa__objetivooperativo__objetivotactico__orden','indicadorpoa__objetivooperativo__orden','indicadorpoa__orden','orden').distinct()
                    else:
                        data['carrera'] = Carrera.objects.get(pk=int(request.GET['idc']))
                        data['documento'] = acciones = AccionDocumento.objects.filter(status=True,acciondocumentodetalle__status=True,indicadorpoa__status=True,indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']),indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__id=int(request.GET['idc']), indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).order_by('indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__orden','indicadorpoa__objetivooperativo__objetivotactico__orden','indicadorpoa__objetivooperativo__orden','indicadorpoa__orden','orden').distinct()
                    mesesevidencias=AccionDocumentoDetalle.objects.select_related().filter(acciondocumento__in=acciones, status=True).distinct()
                    for mevidencias in mesesevidencias:
                        lista.append(mevidencias.fin.month)
                    data['mesesevidencias'] = lista
                    return render(request, "poa_aprobarevidencia/poadepartamentodos.html", data)
                except Exception as ex:
                    pass

            elif action == 'sin_evidencia':
                try:
                    data = {}
                    if int(request.GET['idp']) < 4:
                        acciondocumentodetalle = AccionDocumentoDetalle.objects.get(pk=int(request.GET['iddocdet']))
                        if int(request.GET['record']) == 0:
                            form = {}
                        else:
                            acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(pk=int(request.GET['record']))
                            form = AccionDocumentoRevisaForm(initial={'observacion': acciondocumentodetallerecord.observacion_revisa if not acciondocumentodetallerecord.observacion_aprobacion else acciondocumentodetallerecord.observacion_aprobacion,
                                                                      'estado_accion': acciondocumentodetallerecord.estado_accion_revisa if not acciondocumentodetallerecord.usuario_aprobacion else acciondocumentodetallerecord.estado_accion_aprobacion})
                            form.tipo_sin_evidencia(1)
                        data['records'] = acciondocumentodetalle.acciondocumentodetallerecord_set.all().order_by("-id")
                        data['form'] = form
                        data['modadd'] = True if int(request.GET['listo']) == 0 else False
                        data['record'] = int(request.GET['record'])
                        data['idp'] = int(request.GET['idp'])
                        data['idd'] = int(request.GET['idd'])
                        data['permite_modificar'] = True
                        data['acciondocumentodetalle'] = acciondocumentodetalle.__str__()
                        data['id'] = acciondocumentodetalle.id
                        template = get_template("poa_aprobarevidencia/sin_evidencia.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content})
                    else:
                        acciondocumentodetalle = AccionDocumentoDetalle.objects.get(pk=int(request.GET['iddocdet']))
                        if int(request.GET['record']) == 0:
                            form = {}
                        else:
                            acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(
                                pk=int(request.GET['record']))
                            form = AccionDocumentoRevisaForm(initial={
                                'observacion': acciondocumentodetallerecord.observacion_revisa if not acciondocumentodetallerecord.observacion_aprobacion else acciondocumentodetallerecord.observacion_aprobacion,
                                'estado_accion': acciondocumentodetallerecord.estado_accion_revisa if not acciondocumentodetallerecord.usuario_aprobacion else acciondocumentodetallerecord.estado_accion_aprobacion})
                            form.tipo_sin_evidencia(1)
                        data['records'] = acciondocumentodetalle.acciondocumentodetallerecord_set.all().order_by("-id")
                        data['form'] = form
                        data['modadd'] = True if int(request.GET['listo']) == 0 else False
                        data['record'] = int(request.GET['record'])
                        data['idp'] = int(request.GET['idp'])
                        data['idd'] = int(request.GET['idd'])
                        data['idc'] = int(request.GET['idc'])
                        data['permite_modificar'] = True
                        data['acciondocumentodetalle'] = acciondocumentodetalle.__str__()
                        data['id'] = acciondocumentodetalle.id
                        template = get_template("poa_aprobarevidencia/sin_evidenciacarrera.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'sin_evidenciados':
                try:
                    data = {}
                    acciondocumentodetalle = AccionDocumentoDetalle.objects.get(pk=int(request.GET['iddocdet']))
                    if int(request.GET['record']) == 0:
                        form = {}
                    else:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(
                            pk=int(request.GET['record']))
                        form = AccionDocumentoRevisaActividadForm(initial={
                            'observacion': acciondocumentodetallerecord.observacion_revisa if not acciondocumentodetallerecord.observacion_aprobacion else acciondocumentodetallerecord.observacion_aprobacion,
                            'rubrica': acciondocumentodetallerecord.rubrica_revisa if not acciondocumentodetallerecord.usuario_aprobacion else acciondocumentodetallerecord.rubrica_aprobacion})
                        form.tipo_sin_evidencia()
                    data['rubrica'] = RubricaPoa.objects.filter(muestraformulario=True, status=True)
                    data['records'] = acciondocumentodetalle.acciondocumentodetallerecord_set.all().order_by("-id")
                    data['form'] = form
                    data['modadd'] = True if int(request.GET['listo']) == 0 else False
                    data['record'] = int(request.GET['record'])
                    data['idp'] = int(request.GET['idp'])
                    data['idd'] = int(request.GET['idd'])
                    data['idc'] = int(request.GET['idc'])
                    data['permite_modificar'] = True
                    data['acciondocumentodetalle'] = acciondocumentodetalle.__str__()
                    data['id'] = acciondocumentodetalle.id
                    data['acciondocumental'] = acciondocumentodetalle.evidenciadocumentalpoa_set.filter(status=True).order_by('id')
                    data['formevid'] = EvidenciaDocumentalForm()
                    template = get_template('poa_aprobarevidencia/sin_evidenciados.html')
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editarfecha':
                try:
                    data = {}
                    records = []
                    if int(request.GET['iid']) != 0:
                        informe = InformeGenerado.objects.get(pk=int(request.GET['iid']))
                        form = AperturaInformeForm(initial={'fechaodl': informe.fechamax,
                                                            'fechanew': datetime.now().date()})
                        records = AperturarInforme.objects.filter(status=True, informegenerado__departamento=informe.departamento).order_by("-fecha_creacion")
                    else:
                        form = AperturaInformeForm(initial={'fechanew': datetime.now().date()})
                    form.editar()
                    data['id'] = request.GET['iid']
                    data['idp'] = request.GET['idp']
                    data['form'] = form
                    data['records'] = records
                    template = get_template("poa_aprobarevidencia/aperturarfecha.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'informe_general':
                try:
                    data = {}
                    data['idp'] = int(request.GET['idp'])
                    data['idd'] = int(request.GET['idd'])
                    m = []
                    for x in MONTH_CHOICES:
                        if x[0] <= int(request.GET['mes']):
                            m.append(x[1])
                    data['meses'] = [x for x in m]
                    data['mes'] = int(request.GET['mes'])
                    data['departamento'] = Departamento.objects.get(pk=int(request.GET['idd']))
                    data['reporte_0'] = obtener_reporte('informe_general')
                    data['records'] = PoaInformeFinal.objects.filter(status=True, unidadorganica_id=data['idd'], periodopoa_id=data['idp']).order_by("-fecha")
                    template = get_template("poa_aprobarevidencia/informe_general.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'agregar_archivo_departamento':
                try:
                    data = {}
                    periodopoa = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                    departamento = Departamento.objects.get(pk=int(request.GET['idd']))
                    form = AccionDocumentoDetalleForm()
                    data['form'] = form
                    data['periodopoa'] = periodopoa
                    data['idp'] = request.GET['idp']
                    data['idd'] = request.GET['idd']
                    data['permite_modificar'] = True
                    data['departamento'] = departamento
                    data['action'] = 'agregar_archivo_departamento'
                    data['records'] = PoaArchivo.objects.filter(periodopoa=periodopoa, unidadorganica=departamento, status=True)
                    template = get_template("poa_aprobarevidencia/agregar_archivo_departamento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'informe_form':
                try:
                    data = {}
                    periodo = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                    data['periodo'] = periodo.id
                    data['action'] = 'informe_form'
                    data['mes'] = request.GET['mes']
                    data['idp'] = request.GET['idp']
                    data['idd'] = request.GET['idd']
                    mes = int(request.GET['mes']) + 1 if int(request.GET['mes']) < 12 else 1
                    fechafin = (datetime(periodo.anio if int(request.GET['mes']) < 12 else periodo.anio + 1, mes, 1, 0, 0, 0) - timedelta(days=1)).date()
                    data['departamento'] = Departamento.objects.get(pk=int(request.GET['idd']))
                    acciondocumentodetalle = AccionDocumentoDetalle.objects.filter(acciondocumento__status=True, mostrar=True, status=True, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa__id=int(request.GET['idp']), acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento__id=int(request.GET['idd']))
                    data['objetivos'] = acciondocumentodetalle.filter(inicio__lt=fechafin).count()
                    data['total_objetivos'] = acciondocumentodetalle.count()
                    data['planifiacdo'] = round((float(data['objetivos']) / float(data['total_objetivos'])) * 100, 2)
                    ejecutado = acciondocumentodetalle.filter(inicio__lt=fechafin, estado_accion__in=[2, 6]).count()
                    parcial = acciondocumentodetalle.filter(inicio__lt=fechafin, estado_accion=5).count()
                    parcialequivalente = parcial * 0.5
                    totalobjetivosrealizados = ejecutado + parcialequivalente
                    data['ejecutado'] = round((float(ejecutado) / float(data['total_objetivos'])) * 100, 2)
                    data['parcial'] = round((float(parcialequivalente) / float(data['total_objetivos'])) * 100, 2)
                    nocum = acciondocumentodetalle.filter(inicio__lt=fechafin, estado_accion=1).count()
                    data['nocum'] = round((float(nocum) / float(data['total_objetivos'])) * 100, 2)
                    pendiente = acciondocumentodetalle.filter(inicio__lt=fechafin, estado_accion=3).count()
                    data['pendiente'] = round((float(pendiente) / float(data['total_objetivos'])) * 100, 2)
                    data['cumplimiento'] = round((float(data['ejecutado']) / float(data['planifiacdo'])) * 100, 2)
                    template = get_template("poa_aprobarevidencia/informe_form.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'ver_observacion':
                try:
                    data = {}
                    acciondocumento = AccionDocumento.objects.get(pk=int(request.GET['iddocumento']))
                    return JsonResponse({"result": "ok", 'data': acciondocumento.observacion})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'ver_medio':
                try:
                    data = {}
                    acciondocumento = AccionDocumento.objects.get(pk=int(request.GET['iddocumento']))
                    return JsonResponse({"result": "ok", 'data': acciondocumento.medioverificacion.nombre})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'con_evidencia':
                try:
                    if int(request.GET['idp']) < 4:
                        data = {}
                        acciondocumentodetalle = AccionDocumentoDetalle.objects.get(pk=int(request.GET['iddocdet']))
                        if int(request.GET['record']) == 0:
                            form = AccionDocumentoRevisaForm()
                        else:
                            acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(
                                pk=int(request.GET['record']))
                            form = AccionDocumentoRevisaForm(initial={'observacion': acciondocumentodetallerecord.observacion_revisa if not acciondocumentodetallerecord.observacion_aprobacion else acciondocumentodetallerecord.observacion_aprobacion,
                                                                      'estado_accion': acciondocumentodetallerecord.estado_accion_revisa if not acciondocumentodetallerecord.usuario_aprobacion else acciondocumentodetallerecord.estado_accion_aprobacion})
                            data['documentodetallerecord'] = acciondocumentodetallerecord

                        data['records'] = acciondocumentodetalle.acciondocumentodetallerecord_set.all().order_by("-id")
                        form.tipo_sin_evidencia(2)
                        data['form'] = form
                        data['modadd'] = True if int(request.GET['listo']) == 0 else False
                        data['record'] = int(request.GET['record'])
                        data['idp'] = int(request.GET['idp'])
                        data['idd'] = int(request.GET['idd'])
                        data['permite_modificar'] = True
                        data['acciondocumentodetalle'] = acciondocumentodetalle.__str__()
                        data['id'] = acciondocumentodetalle.id
                        template = get_template("poa_aprobarevidencia/con_evidencia.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content})
                    else:
                        data = {}
                        acciondocumentodetalle = AccionDocumentoDetalle.objects.get(pk=int(request.GET['iddocdet']))
                        if int(request.GET['record']) == 0:
                            form = AccionDocumentoRevisaForm()
                        else:
                            acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(
                                pk=int(request.GET['record']))
                            form = AccionDocumentoRevisaForm(initial={
                                'observacion': acciondocumentodetallerecord.observacion_revisa if not acciondocumentodetallerecord.observacion_aprobacion else acciondocumentodetallerecord.observacion_aprobacion,
                                'estado_accion': acciondocumentodetallerecord.estado_accion_revisa if not acciondocumentodetallerecord.usuario_aprobacion else acciondocumentodetallerecord.estado_accion_aprobacion})
                            data['documentodetallerecord'] = acciondocumentodetallerecord

                        data['records'] = acciondocumentodetalle.acciondocumentodetallerecord_set.all().order_by("-id")
                        form.tipo_sin_evidencia(2)
                        data['form'] = form
                        data['modadd'] = True if int(request.GET['listo']) == 0 else False
                        data['record'] = int(request.GET['record'])
                        data['idp'] = int(request.GET['idp'])
                        data['idd'] = int(request.GET['idd'])
                        data['idc'] = int(request.GET['idc'])
                        data['permite_modificar'] = True
                        data['acciondocumentodetalle'] = acciondocumentodetalle.__str__()
                        data['id'] = acciondocumentodetalle.id
                        template = get_template("poa_aprobarevidencia/con_evidenciacarrera.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'con_evidenciados':
                try:
                    data = {}
                    acciondocumentodetalle = AccionDocumentoDetalle.objects.get(pk=int(request.GET['iddocdet']))
                    if int(request.GET['record']) == 0:
                        form = AccionDocumentoRevisaActividadForm()
                    else:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(
                            pk=int(request.GET['record']))
                        form = AccionDocumentoRevisaActividadForm(initial={
                            'observacion': acciondocumentodetallerecord.observacion_revisa if not acciondocumentodetallerecord.observacion_aprobacion else acciondocumentodetallerecord.observacion_aprobacion,
                            'rubrica': acciondocumentodetallerecord.rubrica_revisa if not acciondocumentodetallerecord.usuario_aprobacion else acciondocumentodetallerecord.rubrica_aprobacion})
                        data['documentodetallerecord'] = acciondocumentodetallerecord

                    data['records'] = acciondocumentodetalle.acciondocumentodetallerecord_set.filter(status=True).order_by("-id")
                    form.tipo_sin_evidencia()
                    data['rubrica'] = RubricaPoa.objects.filter(muestraformulario=True, status=True)
                    data['form'] = form
                    data['modadd'] = True if int(request.GET['listo']) == 0 else False
                    data['record'] = int(request.GET['record'])
                    data['idp'] = int(request.GET['idp'])
                    data['idd'] = int(request.GET['idd'])
                    data['idc'] = int(request.GET['idc'])
                    data['permite_modificar'] = True
                    data['acciondocumentodetalle'] = acciondocumentodetalle.__str__()
                    data['id'] = acciondocumentodetalle.id
                    data['acciondocumental'] = acciondocumentodetalle.evidenciadocumentalpoa_set.filter(status=True).order_by('id')
                    data['formevid'] = EvidenciaDocumentalForm()
                    template = get_template("poa_aprobarevidencia/con_evidenciados.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'form_informe':
                try:
                    idc = int(request.GET['idc'])
                    if idc == 0:
                        data = datosinforme(int(request.GET['idp']), int(request.GET['idd']), int(request.GET['mes']))
                    else:
                        data = datosinformecarrera(int(request.GET['idp']), int(request.GET['idd']), int(request.GET['mes']), int(request.GET['idc']))
                    template = get_template("poa_aprobarevidencia/informe_pdf.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'form_informe_new':
                try:
                    idc = int(request.GET['idc'])
                    if idc == 0:
                        data = datosinforme(int(request.GET['idp']), int(request.GET['idd']), int(request.GET['mes']))
                    else:
                        data = datosinformecarrera(int(request.GET['idp']), int(request.GET['idd']), int(request.GET['mes']), int(request.GET['idc']))
                    template = get_template("poa_aprobarevidencia/informe_pdf_new.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'form_informe_dos':
                try:
                    idc = int(request.GET['idc'])
                    data = datosinformedos(int(request.GET['idp']), int(request.GET['idd']), int(request.GET['mes']))
                    template = get_template("poa_aprobarevidencia/informe_pdf_new.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'generagrafica':
                try:
                    import time
                    data['title'] = u'Graficas por departamento'
                    lista = []
                    messeleccionado = 0
                    objetivos = 0
                    data['periodopoa'] = periodopoa = PeriodoPoa.objects.get(pk=int(request.GET['periodopoa']))
                    data['meses'] = MESES_CHOICES
                    if request.GET['mes'] == '0':
                        ahora = InformeGenerado.objects.values_list('mes',flat=True).filter(periodopoa=periodopoa,tipo=2,status=True).distinct().order_by('-mes')[0]
                        data['mes'] = messeleccionado = int(ahora)
                        data['ahora'] = ahora
                    else:
                        ahora = InformeGenerado.objects.values_list('mes', flat=True).filter(periodopoa=periodopoa, tipo=2, status=True).distinct().order_by('-mes')[0]
                        data['mes'] = messeleccionado = int(request.GET['mes'])
                        data['ahora'] = ahora
                    iddepartamentos = ObjetivoEstrategico.objects.values_list('departamento_id').filter(periodopoa_id=periodopoa.id, status=True)
                    data['departamentos'] = departamentos = Departamento.objects.filter(pk__in=iddepartamentos,status=True).order_by('nombre')
                    mes = int(messeleccionado) + 1 if int(messeleccionado) < 12 else 1
                    fechafin = (datetime(periodopoa.anio if int(messeleccionado) < 12 else periodopoa.anio + 1, mes, 1, 0, 0,0) - timedelta(days=1)).date()
                    for depa in departamentos:
                        acciondocumentodetalle = AccionDocumentoDetalle.objects.filter(acciondocumento__status=True, mostrar=True, status=True, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa__id=periodopoa.id,acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento__id=depa.id)
                        objetivos = acciondocumentodetalle.filter(inicio__lt=fechafin).count()
                        ejecutado = acciondocumentodetalle.filter(inicio__lt=fechafin, estado_accion__in=[2, 6]).count()
                        parcial = acciondocumentodetalle.filter(inicio__lt=fechafin, estado_accion__in=[5]).count()
                        parcialequivalente = parcial * 0.5
                        totalobjetivosrealizados = ejecutado + parcialequivalente
                        if objetivos > 0:
                            cumplimiento = null_to_decimal((float(totalobjetivosrealizados) / float(objetivos)) * 100,2)
                        else:
                            cumplimiento = 0
                        lista.append([depa.id, depa.nombre, cumplimiento, objetivos, ejecutado, parcial])
                    data['lista'] = lista
                    return render(request, "poa_aprobarevidencia/graficas.html", data)
                except Exception as ex:
                    pass

            elif action == 'editarobse':
                try:
                    data = {}
                    acciondocumentodetalle = AccionDocumentoDetalle.objects.get(pk=int(request.GET['iddocdet']))
                    if int(request.GET['record']) != 0:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(pk=int(request.GET['record']))
                        form = AccionDocumentoEditaDuplicaForm(initial={'observacion': acciondocumentodetallerecord.observacion_aprobacion,
                                                                        'estado_accion': acciondocumentodetallerecord.estado_accion_aprobacion})
                        data['documentodetallerecord'] = acciondocumentodetallerecord

                        data['records'] = acciondocumentodetalle.acciondocumentodetallerecord_set.all().order_by("-id")
                        form.tipo_sin_evidencia()
                        if acciondocumentodetallerecord.usuario_aprobacion is None or acciondocumentodetallerecord.usuario_revisa is None:
                            form.bloquea_duplicado()
                        data['form'] = form
                        data['modadd'] = True
                        data['record'] = int(request.GET['record'])
                        data['idp'] = int(request.GET['idp'])
                        data['idd'] = int(request.GET['idd'])
                        data['permite_modificar'] = True
                        data['acciondocumentodetalle'] = acciondocumentodetalle.__str__()
                        data['id'] = acciondocumentodetalle.id

                        template = get_template("poa_aprobarevidencia/editarobse.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Lo sentimos, no se puede editar"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'informe':
                try:
                    data = {}
                    data['idp'] = int(request.GET['idp'])
                    data['idd'] = int(request.GET['idd'])
                    data['mes'] = mes = int(request.GET['mes'])
                    informe = InformeGenerado.objects.filter(mes=mes, periodopoa_id=int(request.GET['idp']), departamento_id=int(request.GET['idd']), status=True)
                    data['informepre'] = informe.filter(tipo=1)[0] if informe.filter(tipo=1).exists() else {}
                    data['informefin'] = informe.filter(tipo=2)[0] if informe.filter(tipo=2).exists() else {}
                    data['form'] = InformeArchivoForm(initial={'fechamax': informe.filter(tipo=2)[0].fechamax}) if informe.filter(tipo=2).exists() else {}
                    periodo = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                    departamento = Departamento.objects.get(pk=int(request.GET['idd']))
                    if mes < 12:
                        fechafin = (datetime(periodo.anio, mes + 1, 1, 0, 0, 0) - timedelta(days=1)).date()
                    else:
                        fechafin = (datetime(periodo.anio + 1, 1, 1, 0, 0, 0) - timedelta(days=1)).date()
                    falta = 0
                    if informe.exists():
                        if informe.filter(tipo=2).exists():
                            data['procesados'] = informe.filter(tipo=2)[0].informegeneradodetalle_set.filter(status=True)
                        elif informe.filter(tipo=1).exists():
                            data['documentos'] = documentos = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__mostrar=True, acciondocumentodetalle__status=True, acciondocumentodetalle__inicio__lte=fechafin, status=True, procesado=False, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']), acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).order_by("-acciondocumentodetalle__inicio", "acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo", "acciondocumentodetalle__acciondocumento__orden").distinct()
                            for p in documentos:
                                if (p.acciondocumentodetalle.estado_accion == 7 or p.acciondocumentodetalle.estado_accion == 4 or p.acciondocumentodetalle.estado_accion == 0) and falta == 0:
                                    if p.acciondocumentodetalle.pedirinforme(mes=mes):
                                        falta = 1
                    else:
                        data['documentos'] = documentos = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__mostrar=True, acciondocumentodetalle__status=True, procesado=False, acciondocumentodetalle__inicio__lte=fechafin, status=True, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']), acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).order_by("-acciondocumentodetalle__inicio", "acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo", "acciondocumentodetalle__acciondocumento__orden").distinct()
                        data['docu'] = docu = AccionDocumentoDetalle.objects.filter(acciondocumento__status=True, status=True, mostrar=True, inicio__month=mes, estado_accion=0, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']), acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).distinct()
                        if docu.exists():
                            for p in docu:
                                if p.pedirinforme(mes=mes):
                                    falta = 1
                        for p in documentos:
                            if p.acciondocumentodetalle.pedirinforme(mes=mes):
                                if (p.acciondocumentodetalle.estado_accion == 7 or p.acciondocumentodetalle.estado_accion == 4 or p.acciondocumentodetalle.estado_accion == 0) and falta == 0:
                                    falta = 1
                    data['falta'] = falta
                    template = get_template("poa_aprobarevidencia/informe_view.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'informecarrera':
                try:
                    data = {}
                    data['idp'] = int(request.GET['idp'])
                    data['idd'] = int(request.GET['idd'])
                    data['idc'] = idc = int(request.GET['idc'])
                    data['mes'] = mes = int(request.GET['mes'])
                    if idc == 0:
                        informe = InformeGenerado.objects.filter(mes=mes, periodopoa_id=int(request.GET['idp']), departamento_id=int(request.GET['idd']),carrera__isnull=True, status=True)
                    else:
                        informe = InformeGenerado.objects.filter(mes=mes, periodopoa_id=int(request.GET['idp']), carrera_id=int(request.GET['idc']), departamento_id=int(request.GET['idd']), status=True)
                    data['informepre'] = informe.filter(tipo=1)[0] if informe.filter(tipo=1).exists() else {}
                    data['informefin'] = informe.filter(tipo=2)[0] if informe.filter(tipo=2).exists() else {}
                    data['form'] = InformeArchivoForm(initial={'fechamax': informe.filter(tipo=2)[0].fechamax}) if informe.filter(tipo=2).exists() else {}
                    periodo = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                    departamento = Departamento.objects.get(pk=int(request.GET['idd']))
                    if mes < 12:
                        fechafin = (datetime(periodo.anio, mes + 1, 1, 0, 0, 0) - timedelta(days=1)).date()
                    else:
                        fechafin = (datetime(periodo.anio + 1, 1, 1, 0, 0, 0) - timedelta(days=1)).date()
                    falta = 0
                    if informe.exists():
                        if informe.filter(tipo=2).exists():
                            data['procesados'] = informe.filter(tipo=2)[0].informegeneradodetalle_set.filter(status=True)
                        elif informe.filter(tipo=1).exists():
                            if idc == 0:
                                data['documentos'] = documentos = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__mostrar=True, acciondocumentodetalle__status=True, acciondocumentodetalle__inicio__lte=fechafin, status=True, procesado=False, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']), acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).order_by("-acciondocumentodetalle__inicio", "acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo", "acciondocumentodetalle__acciondocumento__orden").distinct()
                            else:
                                data['documentos'] = documentos = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__mostrar=True, acciondocumentodetalle__status=True, acciondocumentodetalle__inicio__lte=fechafin, status=True, procesado=False, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']),acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera_id=int(request.GET['idc']), acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).order_by("-acciondocumentodetalle__inicio", "acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo", "acciondocumentodetalle__acciondocumento__orden").distinct()
                            for p in documentos:
                                if (p.acciondocumentodetalle.estado_accion == 7 or p.acciondocumentodetalle.estado_accion == 4 or p.acciondocumentodetalle.estado_accion == 0) and falta == 0:
                                    if p.acciondocumentodetalle.pedirinforme(mes=mes):
                                        falta = 1
                    else:
                        if idc == 0:
                            data['documentos'] = documentos = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__mostrar=True, acciondocumentodetalle__status=True, procesado=False, acciondocumentodetalle__inicio__lte=fechafin, status=True, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']),acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).order_by("-acciondocumentodetalle__inicio", "acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo", "acciondocumentodetalle__acciondocumento__orden").distinct()
                            data['docu'] = docu = AccionDocumentoDetalle.objects.filter(acciondocumento__status=True, status=True, mostrar=True, inicio__month=mes, estado_accion=0, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']),acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).distinct()
                        else:
                            data['documentos'] = documentos = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__mostrar=True, acciondocumentodetalle__status=True, procesado=False, acciondocumentodetalle__inicio__lte=fechafin, status=True, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']),acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera_id=int(request.GET['idc']), acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).order_by("-acciondocumentodetalle__inicio", "acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo", "acciondocumentodetalle__acciondocumento__orden").distinct()
                            data['docu'] = docu = AccionDocumentoDetalle.objects.filter(acciondocumento__status=True, status=True, mostrar=True, inicio__month=mes, estado_accion=0, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']),acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera_id=int(request.GET['idc']), acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).distinct()
                        if docu.exists():
                            for p in docu:
                                if p.pedirinforme(mes=mes):
                                    falta = 1
                        for p in documentos:
                            if p.acciondocumentodetalle.pedirinforme(mes=mes):
                                if (p.acciondocumentodetalle.estado_accion == 7 or p.acciondocumentodetalle.estado_accion == 4 or p.acciondocumentodetalle.estado_accion == 0) and falta == 0:
                                    falta = 1
                    data['falta'] = falta
                    template = get_template("poa_aprobarevidencia/informe_viewcarrera.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'informedos':
                try:
                    data = {}
                    data['idp'] = int(request.GET['idp'])
                    data['idd'] = int(request.GET['idd'])
                    data['idc'] = idc = int(request.GET['idc'])
                    data['mes'] = mes = int(request.GET['mes'])
                    informe = InformeGenerado.objects.filter(mes=mes, periodopoa_id=int(request.GET['idp']), departamento_id=int(request.GET['idd']),carrera__isnull=True, status=True)
                    data['informepre'] = informe.filter(tipo=1)[0] if informe.filter(tipo=1).exists() else {}
                    data['informefin'] = informe.filter(tipo=2)[0] if informe.filter(tipo=2).exists() else {}
                    data['form'] = InformeArchivoForm(initial={'fechamax': informe.filter(tipo=2)[0].fechamax}) if informe.filter(tipo=2).exists() else {}
                    periodo = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                    departamento = Departamento.objects.get(pk=int(request.GET['idd']))
                    if mes < 12:
                        fechafin = (datetime(periodo.anio, mes + 1, 1, 0, 0, 0) - timedelta(days=1)).date()
                    else:
                        fechafin = (datetime(periodo.anio + 1, 1, 1, 0, 0, 0) - timedelta(days=1)).date()
                    falta = 0
                    if informe.exists():
                        if informe.filter(tipo=2).exists():
                            data['procesados'] = informe.filter(tipo=2)[0].informegeneradodetalle_set.filter(status=True)
                        elif informe.filter(tipo=1).exists():
                            if idc == 0:
                                data['documentos'] = documentos = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__mostrar=True, acciondocumentodetalle__status=True, acciondocumentodetalle__inicio__lte=fechafin, status=True, procesado=False, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']), acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).order_by("-acciondocumentodetalle__inicio", "acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo", "acciondocumentodetalle__acciondocumento__orden").distinct()
                            else:
                                data['documentos'] = documentos = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__mostrar=True, acciondocumentodetalle__status=True, acciondocumentodetalle__inicio__lte=fechafin, status=True, procesado=False, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']),acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera_id=int(request.GET['idc']), acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).order_by("-acciondocumentodetalle__inicio", "acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo", "acciondocumentodetalle__acciondocumento__orden").distinct()
                            for p in documentos:
                                if (p.acciondocumentodetalle.estado_accion == 7 or p.acciondocumentodetalle.estado_accion == 4 or p.acciondocumentodetalle.estado_accion == 0) and falta == 0:
                                    if p.acciondocumentodetalle.pedirinforme(mes=mes):
                                        falta = 1
                    else:
                        data['documentos'] = documentos = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__mostrar=True, acciondocumentodetalle__status=True, procesado=False, acciondocumentodetalle__inicio__lte=fechafin, status=True, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']),acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).order_by("-acciondocumentodetalle__inicio", "acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo", "acciondocumentodetalle__acciondocumento__orden").distinct()
                        data['docu'] = docu = AccionDocumentoDetalle.objects.filter(acciondocumento__status=True, status=True, mostrar=True, inicio__month=mes, estado_accion=0, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']),acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).distinct()
                        if docu.exists():
                            for p in docu:
                                if p.pedirinforme(mes=mes):
                                    falta = 1
                        for p in documentos:
                            if p.acciondocumentodetalle.pedirinforme(mes=mes):
                                if (p.acciondocumentodetalle.estado_accion == 7 or p.acciondocumentodetalle.estado_accion == 4 or p.acciondocumentodetalle.estado_accion == 0) and falta == 0:
                                    falta = 1
                    data['falta'] = falta
                    template = get_template("poa_aprobarevidencia/informedos.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'informegeneralfacultad':
                try:
                    data = {}
                    # data['idp'] = int(request.GET['idp'])
                    # data['idd'] = int(request.GET['idd'])
                    data = datosinformegeneralfacultad(int(request.GET['idperiodo']),
                                                       int(request.GET['iddepartamento']), int(request.GET['idmes']))
                    data['departamentoss'] = Departamento.objects.get(pk=int(request.GET['iddepartamento']))
                    data['idmes'] = int(request.GET['idmes'])
                    data['carrerasinforme'] = InformeGenerado.objects.filter(
                        periodopoa_id=int(request.GET['idperiodo']), departamento_id=int(request.GET['iddepartamento']),
                        mes=int(request.GET['idmes']), tipo=2, carrera__isnull=False, status=True)
                    data['periodo'] = PeriodoPoa.objects.get(pk=int(request.GET['idperiodo']))
                    template = get_template("poa_aprobarevidencia/informe_viewfacultades.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'graficaobjetivo':
                try:
                    data['title'] = u'Gráfica objetivos por departamento.'
                    if int(request.GET['idp']) < 4:
                        data['departamento'] = Departamento.objects.get(pk=int(request.GET['idd']))
                        data['meses'] = MONTH_CHOICES
                        data['periodopoa'] = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                        data['idp'] = int(request.GET['idp'])
                        data['idd'] = int(request.GET['idd'])
                        data['mes_actual'] = 12 if PeriodoPoa.objects.get(pk=int(request.GET['idp'])).anio < datetime.now().year else datetime.now().month
                        data['documento'] = AccionDocumento.objects.filter(status=True, acciondocumentodetalle__status=True, indicadorpoa__status=True, indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']), indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).order_by('indicadorpoa__objetivooperativo', 'indicadorpoa').distinct()
                        return render(request, "poa_aprobarevidencia/poadepartamento.html", data)
                    else:
                        lista=[]
                        ejecutadoporcentaje=0
                        objetivos = 0
                        ejecutado = 0
                        parcial = 0
                        cumplimientototal = 0
                        data['departamento'] =departamento= Departamento.objects.get(pk=int(request.GET['idd']))
                        data['periodopoa'] = periodopoa = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                        data['idp'] = int(request.GET['idp'])
                        data['idd'] = int(request.GET['idd'])
                        data['idc'] = idc = int(request.GET['idc'])
                        data['meses'] = MESES_CHOICES
                        if request.GET['mes'] == '0':
                            ahora =InformeGenerado.objects.values_list('mes', flat=True).filter(periodopoa=periodopoa, tipo=2,status=True).distinct().order_by( '-mes')[0]
                            data['mes'] = messeleccionado = int(ahora)
                            data['ahora'] = ahora
                        else:
                            ahora = InformeGenerado.objects.values_list('mes', flat=True).filter(periodopoa=periodopoa, tipo=2,status=True).distinct().order_by('-mes')[0]
                            data['mes'] = messeleccionado = int(request.GET['mes'])
                            data['ahora'] = ahora
                        mes = int(messeleccionado) + 1 if int(messeleccionado) < 12 else 1
                        fechafin = (datetime(periodopoa.anio if int(messeleccionado) < 12 else periodopoa.anio + 1, mes, 1, 0, 0,0) - timedelta(days=1)).date()
                        if idc == 0:
                            objetivos = departamento.objetivos_operativos(periodopoa.anio)
                        else:
                            objetivos = departamento.objetivos_operativosxcarrera(periodopoa.anio,idc)
                            data['carrera'] = Carrera.objects.get(status=True, id=idc)
                        for obj in objetivos:
                            acciondocumentodetalle = AccionDocumentoDetalle.objects.select_related().filter(
                                acciondocumento__status=True, mostrar=True, status=True,
                                acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa__id=periodopoa.id,
                                acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento,
                                acciondocumento__indicadorpoa__objetivooperativo=obj)
                            objetivos = acciondocumentodetalle.filter(inicio__lt=fechafin).count()
                            ejecutado = acciondocumentodetalle.filter(inicio__lt=fechafin, estado_accion__in=[2, 6]).count()
                            parcial = acciondocumentodetalle.filter(inicio__lt=fechafin, estado_accion__in=[5]).count()
                            parcialequivalente = parcial * 0.5
                            totalobjetivosrealizados = ejecutado + parcialequivalente
                            if objetivos>0:
                                cumplimiento = null_to_decimal((float(totalobjetivosrealizados) / float(objetivos)) * 100, 2)
                            else:
                                cumplimiento=0
                            lista.append([obj.id, obj.descripcion, cumplimiento, objetivos, ejecutado, parcial])

                        data['lista'] = lista

                        # acciondocumentodetalle = AccionDocumentoDetalle.objects.select_related().filter(
                        #     acciondocumento__status=True, mostrar=True, status=True,
                        #     acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa__id=periodopoa.id,
                        #     acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento,
                        #     acciondocumento__indicadorpoa__objetivooperativo=obj)
                        # objetivos = acciondocumentodetalle.filter(inicio__lt=fechafin).count()
                        # ejecutado = acciondocumentodetalle.filter(inicio__lt=fechafin,estado_accion__in=[2, 6]).count()
                        # parcial = acciondocumentodetalle.filter(inicio__lt=fechafin,estado_accion__in=[5]).count()
                        # parcialequivalente = parcial * 0.5
                        # totalobjetivosrealizados = ejecutado + parcialequivalente
                        # total_objetivos = acciondocumentodetalle.count()
                        # objetivosplanificados = null_to_decimal((float(objetivos) / float(total_objetivos)) * 100, 2)
                        # objetivosejecutados = null_to_decimal((float(totalobjetivosrealizados) / float(total_objetivos)) * 100, 2)
                        # if objetivosplanificados>0:
                        #     cumplimiento = null_to_decimal((float(totalobjetivosrealizados) / float(objetivos)) * 100, 2)
                        #     cumplimientototal = null_to_decimal(((objetivos * cumplimiento) / 100), 0)
                        # else:
                        #     cumplimiento=0
                        #     cumplimientototal=0
                        # lista.append([obj.id, obj.descripcion, total_objetivos, objetivosejecutados, cumplimiento,objetivos, cumplimientototal, ejecutado, parcial])



                        # for obj in objetivos:
                        #     acciondocumentodetalle = AccionDocumentoDetalle.objects.filter(
                        #         acciondocumento__status=True, mostrar=True, status=True,
                        #         acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa__id=periodopoa.id,
                        #         acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento,
                        #         acciondocumento__indicadorpoa__objetivooperativo=obj)
                        #     data['periodo'] = periodopoa.id
                        #     mes = int(messeleccionado) + 1 if int(messeleccionado) < 12 else 1
                        #     fechafin = (datetime(periodopoa.anio if int(messeleccionado) < 12 else periodopoa.anio + 1, mes, 1, 0, 0, 0) - timedelta(days=1)).date()
                        #     ejecutado = acciondocumentodetalle.filter(inicio__lt=fechafin,estado_accion__in=[2, 6]).count()
                        #     parcial = acciondocumentodetalle.filter(inicio__lt=fechafin,estado_accion__in=[5]).count()
                        #     parcial1=parcial*0.5
                        #     ejecutado1 = ejecutado + parcial1
                        #     totalacciones = 0
                        #     cumplimientototal = 0
                        #     data['total_objetivos'] = acciondocumentodetalle.count()
                        #     data['objetivos'] = objetivos1 = acciondocumentodetalle.filter(inicio__lt=fechafin).count()
                        #     data['planifiacdo'] = null_to_decimal((float(data['objetivos']) / float(data['total_objetivos'])) * 100, 2)
                        #     if ejecutado:
                        #         totalacciones = data['total_objetivos']
                        #         ejecutadoporcentaje = null_to_decimal((float(ejecutado1) / float(data['total_objetivos'])) * 100, 2)
                        #         cumplimiento = null_to_decimal((float(ejecutadoporcentaje) / float(data['planifiacdo'])) * 100, 2)
                        #         cumplimientototal = null_to_decimal(((objetivos1 * cumplimiento) / 100), 0)
                        #     elif parcial :
                        #         cumplimiento = null_to_decimal((float(parcial1) / float(data['planifiacdo'])) * 100, 2)
                        #         cumplimiento = 0
                        #     else:
                        #         cumplimiento =0
                        #         cumplimiento = 0
                        #     lista.append([obj.id, obj.descripcion, totalacciones, ejecutadoporcentaje, cumplimiento, objetivos1,ejecutado,parcial])

                        # for obj in objetivos:
                        #     acciondocumentodetalle = AccionDocumentoDetalle.objects.select_related().filter(
                        #         acciondocumento__status=True, mostrar=True, status=True,
                        #         acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa__id=periodopoa.id,
                        #         acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento,
                        #         acciondocumento__indicadorpoa__objetivooperativo=obj)
                        #     data['periodo'] = periodopoa.id
                        #     objetivos = 0
                        #     ejecutado = 0
                        #     parcial = 0
                        #     cumplimientototal = 0
                        #     mes = int(messeleccionado) + 1 if int(messeleccionado) < 12 else 1
                        #     fechafin = (datetime(periodopoa.anio if int(messeleccionado) < 12 else periodopoa.anio + 1, mes, 1,0, 0, 0) - timedelta(days=1)).date()
                        #     objetivos = acciondocumentodetalle.filter(inicio__lt=fechafin).count()
                        #     ejecutado = acciondocumentodetalle.filter(inicio__lt=fechafin,estado_accion__in=[2, 6]).count()
                        #     parcial = acciondocumentodetalle.filter(inicio__lt=fechafin,estado_accion__in=[5]).count()
                        #     parcialequivalente=parcial*0.5
                        #     totalobjetivosrealizados=ejecutado+parcialequivalente
                        #     total_objetivos = acciondocumentodetalle.count()
                        #     objetivosplanificados = null_to_decimal((float(objetivos) / float(total_objetivos)) * 100, 2)
                        #
                        #     objetivosejecutados = null_to_decimal((float(totalobjetivosrealizados) / float(total_objetivos)) * 100,2)
                        #     cumplimiento = null_to_decimal((float(objetivosejecutados) / float(objetivosplanificados)) * 100, 2)
                        #     cumplimientototal = null_to_decimal(((objetivos * cumplimiento) / 100), 0)
                        #
                        #     lista.append([obj.id, obj.descripcion, total_objetivos, objetivosejecutados, cumplimiento,objetivos,cumplimientototal, ejecutado, parcial])
                        # data['lista'] = lista

                        # data['objetivos'] = objetivos = departamento.objetivos_operativosxcarrera(periodopoa.anio,idc)
                        # data['carrera'] =Carrera.objects.get(status=True,id=idc)
                        # for obj in objetivos:
                        #     ejecutado = acciondocumentodetalle.filter(inicio__lt=fechafin,estado_accion__in=[2, 6]).count()
                        #     parcial = acciondocumentodetalle.filter(inicio__lt=fechafin,estado_accion__in=[5]).count()
                        #     parcial1 = parcial * 0.5
                        #     ejecutado1=ejecutado+parcial1
                        #     totalacciones = 0
                        #     cumplimientototal = 0
                        #     data['objetivos'] = objetivos1 = acciondocumentodetalle.filter(inicio__lt=fechafin).count()
                        #     if ejecutado:
                        #         data['total_objetivos'] = acciondocumentodetalle.count()
                        #         totalacciones = data['total_objetivos']
                        #         data['planifiacdo'] = null_to_decimal((float(data['objetivos']) / float(data['total_objetivos'])) * 100, 2)
                        #         ejecutadoporcentaje = null_to_decimal((float(ejecutado1) / float(data['total_objetivos'])) * 100, 2)
                        #         cumplimiento = null_to_decimal((float(ejecutadoporcentaje) / float(data['planifiacdo'])) * 100, 2)
                        #         cumplimientototal = null_to_decimal(((objetivos1 * cumplimiento) / 100), 0)
                        #     else:
                        #         ejecutadoporcentaje = 0
                        #         cumplimiento = 0

                        return render(request, "poa_aprobarevidencia/graficasobjetivos.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            periodo = PeriodoPoa.objects.filter(status=True).order_by('-id')
            data['periodo'] = periodo
            return render(request, "poa_aprobarevidencia/view.html", data)


def datosinformegeneralfacultad(idp, idd, mes):
    data = {}
    data['idp'] = idp
    data['idd'] = idd
    data['existeinforme'] = 0
    data['mes_anterior'] = MESES_CHOICES[mes - 2][1]
    data['dos_meses'] = ACUMULAR_DOS_MESES
    periodo = PeriodoPoa.objects.get(pk=idp)
    departamento = Departamento.objects.get(pk=idd)
    informegenerado = InformeGenerado.objects.get(periodopoa_id=idp, departamento_id=idd, mes=mes, tipo=2, carrera__isnull=True, status=True)
    data['informegenerado'] = informegenerado
    if InformeGeneradoFacultad.objects.filter(informegenerado=informegenerado,status=True).exists():
        data['existeinforme'] = 1
        data['recomendacioninforme'] = InformeGeneradoFacultad.objects.get(informegenerado=informegenerado,status=True)
    informedetallado = InformeGeneradoDetalle.objects.filter(informegenerado=informegenerado,status=True)
    data['periodo'] = periodo
    if not ACUMULAR_DOS_MESES:
        fechafinanterior = (datetime(periodo.anio, mes, 1, 0, 0, 0) - timedelta(days=1)).date()
    else:
        fechafinanterior = (datetime(periodo.anio, (mes - 1), 1, 0, 0, 0) - timedelta(days=1)).date()
    data['departamento'] = departamento
    data['mesid'] = mes
    data['nomtrimestre'] = trimestre(mes)
    data['mes'] = MESES_CHOICES[mes - 1][1]
    informe = InformeGenerado.objects.filter(mes=mes, periodopoa=periodo, departamento=departamento,carrera__isnull=True, status=True).order_by("-tipo")
    data['informe'] = informe[0] if informe.exists() else {}
    data['fecha'] = informe[0].fecha_creacion if informe.exists() else datetime.now().date()
    data['recomendacion'] = informe[0].recomendacion if informe.exists() else ""
    data['tipoid'] = 1 if not informe.exists() else 2
    # evidencias = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__status=True, acciondocumentodetalle__mostrar=True, procesado=False, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento,acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True, status=True)
    evidencias = InformeGeneradoDetalle.objects.filter(informegenerado=informegenerado,status=True)
    if not ACUMULAR_DOS_MESES:
        evidencia_mes = evidencias.filter(acciondocumentodetallerecord__acciondocumentodetalle__inicio__month=mes)
    #        evidencia_mes = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__status=True, acciondocumentodetalle__mostrar=True, procesado=False, acciondocumentodetalle__inicio__month=mes, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento, status=True)
    else:
        # mes1 = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__status=True, acciondocumentodetalle__mostrar=True, procesado=False, acciondocumentodetalle__inicio__month=mes, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento, status=True)
        # mes2 = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__status=True, acciondocumentodetalle__mostrar=True, procesado=False, acciondocumentodetalle__inicio__month=(mes - 1), acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento, status=True)
        mes1 = evidencias.filter(acciondocumentodetallerecord__acciondocumentodetalle__inicio__month=mes)
        mes2 = evidencias.filter(acciondocumentodetallerecord__acciondocumentodetalle__inicio__month=(mes - 1))
        if mes1:
            if mes2:
                evidencia_mes = mes1 | mes2
            else:
                evidencia_mes = mes1
        else:
            evidencia_mes = mes2

    usuarior = usuarioa = []
    if evidencia_mes:
        d=1
        # usuario = evidencia_mes.values("usuario_revisa").annotate(contador=Count("usuario_revisa")).order_by("usuario_revisa", "-contador")[:1]
        # usuarior = evidencia_mes.values("usuario_revisa").annotate(contador=Count("usuario_revisa")).order_by("usuario_revisa", "-contador")[:1]
        # usuarioa = evidencia_mes.values("usuario_aprobacion").annotate(contador=Count("usuario_aprobacion")).order_by("usuario_aprobacion", "-contador")[:1]
    else:
        # datae = AccionDocumentoDetalle.objects.filter(acciondocumento__status=True, mostrar=True, inicio__lt=fechafinanterior, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento,acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True, status=True).order_by("-inicio", "acciondocumento__indicadorpoa__objetivooperativo", "acciondocumento")
        datae = InformeGeneradoDetalle.objects.filter(informegenerado=informegenerado,acciondocumentodetallerecord__acciondocumentodetalle__inicio__lt=fechafinanterior,status=True).order_by("-acciondocumentodetallerecord__acciondocumentodetalle__inicio", "acciondocumentodetallerecord__acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo", "acciondocumentodetallerecord__acciondocumentodetalle__acciondocumento")
        if datae:
            ulti_mes = datae[0].acciondocumentodetallerecord.acciondocumentodetalle.inicio.month
            user_evidencia = datae.filter(acciondocumentodetallerecord__acciondocumentodetalle__inicio__month=ulti_mes)
            usuarior = user_evidencia.values("acciondocumentodetallerecord__usuario_revisa").annotate(contador=Count("acciondocumentodetallerecord__usuario_revisa")).order_by("acciondocumentodetallerecord__usuario_revisa", "-contador")[:1]
            usuarioa = user_evidencia.values("acciondocumentodetallerecord__usuario_aprobacion").annotate(contador=Count("acciondocumentodetallerecord__usuario_aprobacion")).order_by("acciondocumentodetallerecord__usuario_aprobacion", "-contador")[:1]

    firma = []
    elabora = False
    if usuarior or usuarioa:
        if evidencia_mes:
            r = Persona.objects.get(usuario_id=usuarior[0].get("usuario_revisa"))
            a = Persona.objects.get(usuario_id=usuarioa[0].get("usuario_aprobacion"))
        else:
            r = Persona.objects.get(usuario_id=usuarior[0].get("acciondocumentodetallerecord__usuario_revisa"))
            a = Persona.objects.get(usuario_id=usuarioa[0].get("acciondocumentodetallerecord__usuario_aprobacion"))

        if a.id != r.id:
            elabora = True
            firma.append(r)
            firma.append(a)
        else:
            firma.append(r)
    firma.append(Persona.objects.get(pk=PERSONA_APRUEBA_POA))
    data['firma'] = firma
    data['elabora'] = elabora
    listadelmes = []
    for e in evidencia_mes.order_by("-acciondocumentodetallerecord__acciondocumentodetalle__inicio", "acciondocumentodetallerecord__acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo", "acciondocumentodetallerecord__acciondocumentodetalle__acciondocumento"):
        if e.estado_accion_aprobacion not in [0, 4, 7]:
            if e.acciondocumentodetallerecord not in listadelmes:
                listadelmes.append(e.acciondocumentodetallerecord)
    excluir = []
    for e in evidencias:
        if e.acciondocumentodetallerecord.acciondocumentodetalle.inicio.month != e.acciondocumentodetallerecord.acciondocumentodetalle.fin.month:
            if e.acciondocumentodetallerecord.acciondocumentodetalle.inicio.month <= mes <= e.acciondocumentodetallerecord.acciondocumentodetalle.fin.month:
                excluir.append(e)
                if e.estado_accion_aprobacion not in [0, 4, 7]:
                    if e.acciondocumentodetallerecord not in listadelmes:
                        listadelmes.append(e.acciondocumentodetallerecord)
    lista = []
    # for p in AccionDocumentoDetalle.objects.filter(acciondocumento__status=True, mostrar=True, inicio__lt=fechafinanterior, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento,acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True, status=True).order_by("-inicio", "acciondocumento__indicadorpoa__objetivooperativo", "acciondocumento"):
    for p in InformeGeneradoDetalle.objects.filter(informegenerado=informegenerado,acciondocumentodetallerecord__acciondocumentodetalle__inicio__lt=fechafinanterior,status=True):
        # if p.acciondocumentodetallerecord_set.exists():
        record = p.acciondocumentodetallerecord
        if record:
            # if not(p.estado_accion_aprobacion in[6, 2]):
            if not (record.procesado and p.estado_accion_aprobacion in [6, 2]):
                if not record in excluir:
                    if p.acciondocumentodetallerecord.acciondocumentodetalle.inicio.month == p.acciondocumentodetallerecord.acciondocumentodetalle.fin.month:
                        if record not in lista:
                            lista.append(record)
                    else:
                        if p.acciondocumentodetallerecord.acciondocumentodetalle.inicio.month <= mes <= p.acciondocumentodetallerecord.acciondocumentodetalle.fin.month:
                            if p.estado_accion_aprobacion not in [0, 4, 7]:
                                if record not in listadelmes:
                                    listadelmes.append(record)
                        else:
                            if record not in lista:
                                lista.append(record)
    data['evidencia_anterior'] = lista
    data['evidencia_mes'] = listadelmes
    data["leye_mes"] = conclusiones(data['evidencia_mes'], data, periodo, data['evidencia_anterior'], mes)
    data['secuencia'] = 0
    if informe.exists():
        if informe[0].tipo == 1:
            data['secu'] = 0
            data['tipo'] = "INFORME PRELIMINAR"
        else:
            data['tipo'] = "INFORME"
        data['secuencia'] = informe[0].numinfo
        data['tipoinforme'] = "INFORME DE CUMPLIMIENTO" if informe[0].tipo == 2 else "INFORME PRELIMINAR"
    else:
        data['tipoinforme'] = "INFORME PRELIMINAR"
        data['secu'] = 0
        data['tipo'] = "INFORME PRELIMINAR"
    return data


def datosinformegeneralfacultadcarrera(idp, idd, mes, idcarr):
    data = {}
    data['idp'] = idp
    data['idd'] = idd
    data['idc'] = idcarr
    data['mes_anterior'] = MESES_CHOICES[mes - 2][1]
    data['dos_meses'] = ACUMULAR_DOS_MESES
    periodo = PeriodoPoa.objects.get(pk=idp)
    departamento = Departamento.objects.get(pk=idd)
    informegenerado = InformeGenerado.objects.get(periodopoa_id=idp,departamento_id=idd,mes=mes, tipo=2, carrera_id=idcarr,status=True)
    informedetallado = InformeGeneradoDetalle.objects.filter(informegenerado=informegenerado,status=True)
    data['periodo'] = periodo
    if not ACUMULAR_DOS_MESES:
        fechafinanterior = (datetime(periodo.anio, mes, 1, 0, 0, 0) - timedelta(days=1)).date()
    else:
        fechafinanterior = (datetime(periodo.anio, (mes - 1), 1, 0, 0, 0) - timedelta(days=1)).date()
    data['departamento'] = departamento
    data['mesid'] = mes
    data['nomtrimestre'] = trimestre(mes)
    data['mes'] = MESES_CHOICES[mes - 1][1]
    informe = InformeGenerado.objects.filter(mes=mes, periodopoa=periodo, departamento=departamento,carrera_id=idcarr, status=True).order_by("-tipo")
    data['informe'] = informe[0] if informe.exists() else {}
    data['fecha'] = informe[0].fecha_creacion if informe.exists() else datetime.now().date()
    # data['recomendacion'] = informe[0].recomendacion if informe.exists() else ""
    data['tipoid'] = 1 if not informe.exists() else 2
    # evidencias = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__status=True, acciondocumentodetalle__mostrar=True, procesado=False, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento,acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True, status=True)
    evidencias = InformeGeneradoDetalle.objects.filter(informegenerado=informegenerado,status=True)
    if not ACUMULAR_DOS_MESES:
        evidencia_mes = evidencias.filter(acciondocumentodetallerecord__acciondocumentodetalle__inicio__month=mes)
    #        evidencia_mes = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__status=True, acciondocumentodetalle__mostrar=True, procesado=False, acciondocumentodetalle__inicio__month=mes, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento, status=True)
    else:
        # mes1 = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__status=True, acciondocumentodetalle__mostrar=True, procesado=False, acciondocumentodetalle__inicio__month=mes, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento, status=True)
        # mes2 = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__status=True, acciondocumentodetalle__mostrar=True, procesado=False, acciondocumentodetalle__inicio__month=(mes - 1), acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento, status=True)
        mes1 = evidencias.filter(acciondocumentodetallerecord__acciondocumentodetalle__inicio__month=mes)
        mes2 = evidencias.filter(acciondocumentodetallerecord__acciondocumentodetalle__inicio__month=(mes - 1))
        if mes1:
            if mes2:
                evidencia_mes = mes1 | mes2
            else:
                evidencia_mes = mes1
        else:
            evidencia_mes = mes2

    usuarior = usuarioa = []
    if evidencia_mes:
        d=1
        # usuario = evidencia_mes.values("usuario_revisa").annotate(contador=Count("usuario_revisa")).order_by("usuario_revisa", "-contador")[:1]
        # usuarior = evidencia_mes.values("usuario_revisa").annotate(contador=Count("usuario_revisa")).order_by("usuario_revisa", "-contador")[:1]
        # usuarioa = evidencia_mes.values("usuario_aprobacion").annotate(contador=Count("usuario_aprobacion")).order_by("usuario_aprobacion", "-contador")[:1]
    else:
        # datae = AccionDocumentoDetalle.objects.filter(acciondocumento__status=True, mostrar=True, inicio__lt=fechafinanterior, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento,acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True, status=True).order_by("-inicio", "acciondocumento__indicadorpoa__objetivooperativo", "acciondocumento")
        datae = InformeGeneradoDetalle.objects.filter(informegenerado=informegenerado,acciondocumentodetallerecord__acciondocumentodetalle__inicio__lt=fechafinanterior,status=True).order_by("-acciondocumentodetallerecord__acciondocumentodetalle__inicio", "acciondocumentodetallerecord__acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo", "acciondocumentodetallerecord__acciondocumentodetalle__acciondocumento")
        if datae:
            ulti_mes = datae[0].acciondocumentodetallerecord.acciondocumentodetalle.inicio.month
            user_evidencia = datae.filter(acciondocumentodetallerecord__acciondocumentodetalle__inicio__month=ulti_mes)
            usuarior = user_evidencia.values("acciondocumentodetallerecord__usuario_revisa").annotate(contador=Count("acciondocumentodetallerecord__usuario_revisa")).order_by("acciondocumentodetallerecord__usuario_revisa", "-contador")[:1]
            usuarioa = user_evidencia.values("acciondocumentodetallerecord__usuario_aprobacion").annotate(contador=Count("acciondocumentodetallerecord__usuario_aprobacion")).order_by("acciondocumentodetallerecord__usuario_aprobacion", "-contador")[:1]

    firma = []
    elabora = False
    if usuarior or usuarioa:
        if evidencia_mes:
            r = Persona.objects.get(usuario_id=usuarior[0].get("usuario_revisa"))
            a = Persona.objects.get(usuario_id=usuarioa[0].get("usuario_aprobacion"))
        else:
            r = Persona.objects.get(usuario_id=usuarior[0].get("acciondocumentodetallerecord__usuario_revisa"))
            a = Persona.objects.get(usuario_id=usuarioa[0].get("acciondocumentodetallerecord__usuario_aprobacion"))

        if a.id != r.id:
            elabora = True
            firma.append(r)
            firma.append(a)
        else:
            firma.append(r)
    firma.append(Persona.objects.get(pk=PERSONA_APRUEBA_POA))
    data['firma'] = firma
    data['elabora'] = elabora
    listadelmes = []
    for e in evidencia_mes.order_by("-acciondocumentodetallerecord__acciondocumentodetalle__inicio", "acciondocumentodetallerecord__acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo", "acciondocumentodetallerecord__acciondocumentodetalle__acciondocumento"):
        if e.estado_accion_aprobacion not in [0, 4, 7]:
            if e.acciondocumentodetallerecord not in listadelmes:
                listadelmes.append(e.acciondocumentodetallerecord)
    excluir = []
    for e in evidencias:
        if e.acciondocumentodetallerecord.acciondocumentodetalle.inicio.month != e.acciondocumentodetallerecord.acciondocumentodetalle.fin.month:
            if e.acciondocumentodetallerecord.acciondocumentodetalle.inicio.month <= mes <= e.acciondocumentodetallerecord.acciondocumentodetalle.fin.month:
                excluir.append(e)
                if e.estado_accion_aprobacion not in [0, 4, 7]:
                    if e.acciondocumentodetallerecord not in listadelmes:
                        listadelmes.append(e.acciondocumentodetallerecord)
    lista = []
    # for p in AccionDocumentoDetalle.objects.filter(acciondocumento__status=True, mostrar=True, inicio__lt=fechafinanterior, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento,acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True, status=True).order_by("-inicio", "acciondocumento__indicadorpoa__objetivooperativo", "acciondocumento"):
    for p in InformeGeneradoDetalle.objects.filter(informegenerado=informegenerado,acciondocumentodetallerecord__acciondocumentodetalle__inicio__lt=fechafinanterior,status=True):
        # if p.acciondocumentodetallerecord_set.exists():
        record = p.acciondocumentodetallerecord
        if record:
            if not(record.procesado and p.estado_accion_aprobacion in[6, 2]):
                # cuando genero el informe final mandaba a cambiar el estado a procesado habla serio Yepez tuve que quitar para q procese el reporte
                # if not(p.estado_accion_aprobacion in[6, 2]):
                if not record in excluir:
                    if p.acciondocumentodetallerecord.acciondocumentodetalle.inicio.month == p.acciondocumentodetallerecord.acciondocumentodetalle.fin.month:
                        if record not in lista:
                            lista.append(record)
                    else:
                        if p.acciondocumentodetallerecord.acciondocumentodetalle.inicio.month <= mes <= p.acciondocumentodetallerecord.acciondocumentodetalle.fin.month:
                            if p.estado_accion_aprobacion not in [0, 4, 7]:
                                if record not in listadelmes:
                                    listadelmes.append(record)
                        else:
                            if record not in lista:
                                lista.append(record)
    data['evidencia_anterior'] = lista
    data['evidencia_mes'] = listadelmes
    data["leye_mes"] = conclusiones(data['evidencia_mes'], data, periodo, data['evidencia_anterior'], mes)
    data['secuencia'] = 0
    if informe.exists():
        if informe[0].tipo == 1:
            data['secu'] = 0
            data['tipo'] = "INFORME PRELIMINAR"
        else:
            data['tipo'] = "INFORME"
        data['secuencia'] = informe[0].numinfo
        data['tipoinforme'] = "INFORME DE CUMPLIMIENTO" if informe[0].tipo == 2 else "INFORME PRELIMINAR"
    else:
        data['tipoinforme'] = "INFORME PRELIMINAR"
        data['secu'] = 0
        data['tipo'] = "INFORME PRELIMINAR"
    return data


def datosinforme(idp, idd, mes):
    data = {}
    data['idp'] = idp
    data['idd'] = idd
    data['mes_anterior'] = MESES_CHOICES[mes - 2][1]
    data['dos_meses'] = ACUMULAR_DOS_MESES
    periodo = PeriodoPoa.objects.get(pk=idp)
    departamento = Departamento.objects.get(pk=idd)
    data['periodo'] = periodo
    if not ACUMULAR_DOS_MESES:
        fechafinanterior = (datetime(periodo.anio, mes, 1, 0, 0, 0) - timedelta(days=1)).date()
    else:
        fechafinanterior = (datetime(periodo.anio, (mes - 1), 1, 0, 0, 0) - timedelta(days=1)).date()
    data['departamento'] = departamento
    data['mesid'] = mes
    data['nomtrimestre'] = trimestre(mes)
    data['mes'] = MESES_CHOICES[mes - 1][1]
    informe = InformeGenerado.objects.filter(mes=mes, periodopoa=periodo, departamento=departamento,carrera__isnull=True, status=True).order_by("-tipo")
    data['informe'] = informe[0] if informe.exists() else {}
    data['fecha'] = informe[0].fecha_creacion if informe.exists() else datetime.now().date()
    data['recomendacion'] = informe[0].recomendacion if informe.exists() else ""
    data['tipoid'] = 1 if not informe.exists() else 2
    evidencias = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__status=True, acciondocumentodetalle__mostrar=True, procesado=False, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento,acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True, status=True)
    if not ACUMULAR_DOS_MESES:
        evidencia_mes = evidencias.filter(acciondocumentodetalle__inicio__month=mes)
    #        evidencia_mes = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__status=True, acciondocumentodetalle__mostrar=True, procesado=False, acciondocumentodetalle__inicio__month=mes, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento, status=True)
    else:
        # mes1 = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__status=True, acciondocumentodetalle__mostrar=True, procesado=False, acciondocumentodetalle__inicio__month=mes, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento, status=True)
        # mes2 = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__status=True, acciondocumentodetalle__mostrar=True, procesado=False, acciondocumentodetalle__inicio__month=(mes - 1), acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento, status=True)
        mes1 = evidencias.filter(acciondocumentodetalle__inicio__month=mes)
        mes2 = evidencias.filter(acciondocumentodetalle__inicio__month=(mes - 1))
        if mes1:
            if mes2:
                evidencia_mes = mes1 | mes2
            else:
                evidencia_mes = mes1
        else:
            evidencia_mes = mes2

    usuarior = usuarioa = []
    if evidencia_mes:
        usuario = evidencia_mes.values("usuario_revisa").annotate(contador=Count("usuario_revisa")).order_by("usuario_revisa", "-contador")[:1]
        usuarior = evidencia_mes.values("usuario_revisa").annotate(contador=Count("usuario_revisa")).order_by("usuario_revisa", "-contador")[:1]
        usuarioa = evidencia_mes.values("usuario_aprobacion").annotate(contador=Count("usuario_aprobacion")).order_by("usuario_aprobacion", "-contador")[:1]
    else:
        datae = AccionDocumentoDetalle.objects.filter(acciondocumento__status=True, mostrar=True, inicio__lt=fechafinanterior, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento,acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True, status=True).order_by("-inicio", "acciondocumento__indicadorpoa__objetivooperativo", "acciondocumento")
        if datae:
            ulti_mes = datae[0].inicio.month
            user_evidencia = datae.filter(inicio__month=ulti_mes)
            usuarior = user_evidencia.values("acciondocumentodetallerecord__usuario_revisa").annotate(contador=Count("acciondocumentodetallerecord__usuario_revisa")).order_by("acciondocumentodetallerecord__usuario_revisa", "-contador")[:1]
            usuarioa = user_evidencia.values("acciondocumentodetallerecord__usuario_aprobacion").annotate(contador=Count("acciondocumentodetallerecord__usuario_aprobacion")).order_by("acciondocumentodetallerecord__usuario_aprobacion", "-contador")[:1]

    firma = []
    elabora = False
    if usuarior or usuarioa:
        if evidencia_mes:
            r = Persona.objects.get(usuario_id=usuarior[0].get("usuario_revisa"))
            a = Persona.objects.get(usuario_id=usuarioa[0].get("usuario_aprobacion"))
        else:
            r = Persona.objects.get(usuario_id=usuarior[0].get("acciondocumentodetallerecord__usuario_revisa"))
            a = Persona.objects.get(usuario_id=usuarioa[0].get("acciondocumentodetallerecord__usuario_aprobacion"))

        if a.id != r.id:
            elabora = True
            firma.append(r)
            firma.append(a)
        else:
            firma.append(r)
    firma.append(Persona.objects.get(pk=PERSONA_APRUEBA_POA))
    data['firma'] = firma
    data['elabora'] = elabora
    listadelmes = []
    for e in evidencia_mes.order_by("-acciondocumentodetalle__inicio", "acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo", "acciondocumentodetalle__acciondocumento"):
        if e.estado_accion_aprobacion not in [0, 4, 7]:
            if e not in listadelmes:
                listadelmes.append(e)
    excluir = []
    for e in evidencias:
        if e.acciondocumentodetalle.inicio.month != e.acciondocumentodetalle.fin.month:
            if e.acciondocumentodetalle.inicio.month <= mes <= e.acciondocumentodetalle.fin.month:
                excluir.append(e)
                if e.estado_accion_aprobacion not in [0, 4, 7]:
                    if e not in listadelmes:
                        listadelmes.append(e)
    lista = []
    for p in AccionDocumentoDetalle.objects.filter(acciondocumento__status=True, mostrar=True, inicio__lt=fechafinanterior, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento,acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True, status=True).order_by("-inicio", "acciondocumento__indicadorpoa__objetivooperativo", "acciondocumento"):
        if p.acciondocumentodetallerecord_set.exists():
            record = p.detrecord()
            if record.exists():
                if not(record[0].procesado and p.estado_accion in[6, 2]):
                    if not record[0] in excluir:
                        if p.inicio.month == p.fin.month:
                            if record[0] not in lista:
                                lista.append(record[0])
                        else:
                            if p.inicio.month <= mes <= p.fin.month:
                                if p.estado_accion not in [0, 4, 7]:
                                    if record[0] not in listadelmes:
                                        listadelmes.append(record[0])
                            else:
                                if record[0] not in lista:
                                    lista.append(record[0])
    data['evidencia_anterior'] = lista
    data['evidencia_mes'] = listadelmes
    data["leye_mes"] = conclusiones(data['evidencia_mes'], data, periodo, data['evidencia_anterior'], mes)
    data['secuencia'] = 0
    if informe.exists():
        if informe[0].tipo == 1:
            data['secu'] = 0
            data['tipo'] = "INFORME PRELIMINAR"
        else:
            data['tipo'] = "INFORME"
        data['secuencia'] = informe[0].numinfo
        data['tipoinforme'] = "INFORME DE CUMPLIMIENTO" if informe[0].tipo == 2 else "INFORME PRELIMINAR"
    else:
        data['tipoinforme'] = "INFORME PRELIMINAR"
        data['secu'] = 0
        data['tipo'] = "INFORME PRELIMINAR"
    return data


def datosinformedos(idp, idd, mes):
    data = {}
    data['idp'] = idp
    data['idd'] = idd
    data['mes_anterior'] = MESES_CHOICES[mes - 2][1]
    data['dos_meses'] = ACUMULAR_DOS_MESES
    periodo = PeriodoPoa.objects.get(pk=idp)
    departamento = Departamento.objects.get(pk=idd)
    data['periodo'] = periodo
    if not ACUMULAR_DOS_MESES:
        fechafinanterior = (datetime(periodo.anio, mes, 1, 0, 0, 0) - timedelta(days=1)).date()
    else:
        fechafinanterior = (datetime(periodo.anio, (mes - 1), 1, 0, 0, 0) - timedelta(days=1)).date()
    data['departamento'] = departamento
    data['mesid'] = mes
    data['nomtrimestre'] = trimestre(mes)
    data['mes'] = MESES_CHOICES[mes - 1][1]
    informe = InformeGenerado.objects.filter(mes=mes, periodopoa=periodo, departamento=departamento,carrera__isnull=True, status=True).order_by("-tipo")
    data['informe'] = informe[0] if informe.exists() else {}
    data['fecha'] = informe[0].fecha_creacion if informe.exists() else datetime.now().date()
    data['recomendacion'] = informe[0].recomendacion if informe.exists() else ""
    data['tipoid'] = 1 if not informe.exists() else 2
    evidencias = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__status=True, acciondocumentodetalle__mostrar=True, procesado=False, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento,acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True, status=True)
    if not ACUMULAR_DOS_MESES:
        evidencia_mes = evidencias.filter(acciondocumentodetalle__inicio__month=mes)
    #        evidencia_mes = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__status=True, acciondocumentodetalle__mostrar=True, procesado=False, acciondocumentodetalle__inicio__month=mes, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento, status=True)
    else:
        # mes1 = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__status=True, acciondocumentodetalle__mostrar=True, procesado=False, acciondocumentodetalle__inicio__month=mes, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento, status=True)
        # mes2 = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__status=True, acciondocumentodetalle__mostrar=True, procesado=False, acciondocumentodetalle__inicio__month=(mes - 1), acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento, status=True)
        mes1 = evidencias.filter(acciondocumentodetalle__inicio__month=mes)
        mes2 = evidencias.filter(acciondocumentodetalle__inicio__month=(mes - 1))
        if mes1:
            if mes2:
                evidencia_mes = mes1 | mes2
            else:
                evidencia_mes = mes1
        else:
            evidencia_mes = mes2

    usuarior = usuarioa = []
    if evidencia_mes:
        usuario = evidencia_mes.values("usuario_revisa").annotate(contador=Count("usuario_revisa")).order_by("usuario_revisa", "-contador")[:1]
        usuarior = evidencia_mes.values("usuario_revisa").annotate(contador=Count("usuario_revisa")).order_by("usuario_revisa", "-contador")[:1]
        usuarioa = evidencia_mes.values("usuario_aprobacion").annotate(contador=Count("usuario_aprobacion")).order_by("usuario_aprobacion", "-contador")[:1]
    else:
        datae = AccionDocumentoDetalle.objects.filter(acciondocumento__status=True, mostrar=True, inicio__lt=fechafinanterior, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento,acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True, status=True).order_by("-inicio", "acciondocumento__indicadorpoa__objetivooperativo", "acciondocumento")
        if datae:
            ulti_mes = datae[0].inicio.month
            user_evidencia = datae.filter(inicio__month=ulti_mes)
            usuarior = user_evidencia.values("acciondocumentodetallerecord__usuario_revisa").annotate(contador=Count("acciondocumentodetallerecord__usuario_revisa")).order_by("acciondocumentodetallerecord__usuario_revisa", "-contador")[:1]
            usuarioa = user_evidencia.values("acciondocumentodetallerecord__usuario_aprobacion").annotate(contador=Count("acciondocumentodetallerecord__usuario_aprobacion")).order_by("acciondocumentodetallerecord__usuario_aprobacion", "-contador")[:1]

    firma = []
    elabora = False
    if usuarior or usuarioa:
        if evidencia_mes:
            r = Persona.objects.get(usuario_id=usuarior[0].get("usuario_revisa"))
            a = Persona.objects.get(usuario_id=usuarioa[0].get("usuario_aprobacion"))
        else:
            r = Persona.objects.get(usuario_id=usuarior[0].get("acciondocumentodetallerecord__usuario_revisa"))
            a = Persona.objects.get(usuario_id=usuarioa[0].get("acciondocumentodetallerecord__usuario_aprobacion"))

        if a.id != r.id:
            elabora = True
            firma.append(r)
            firma.append(a)
        else:
            firma.append(r)
    firma.append(Persona.objects.get(pk=PERSONA_APRUEBA_POA))
    data['firma'] = firma
    data['elabora'] = elabora
    listadelmes = []
    for e in evidencia_mes.order_by("-acciondocumentodetalle__inicio", "acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo", "acciondocumentodetalle__acciondocumento"):
        if e.estado_accion_aprobacion not in [0, 4, 7]:
            if e not in listadelmes:
                listadelmes.append(e)
    excluir = []
    for e in evidencias:
        if e.acciondocumentodetalle.inicio.month != e.acciondocumentodetalle.fin.month:
            if e.acciondocumentodetalle.inicio.month <= mes <= e.acciondocumentodetalle.fin.month:
                excluir.append(e)
                if e.estado_accion_aprobacion not in [0, 4, 7]:
                    if e not in listadelmes:
                        listadelmes.append(e)
    lista = []
    for p in AccionDocumentoDetalle.objects.filter(acciondocumento__status=True, mostrar=True, inicio__lt=fechafinanterior, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento,acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True, status=True).order_by("-inicio", "acciondocumento__indicadorpoa__objetivooperativo", "acciondocumento"):
        if p.acciondocumentodetallerecord_set.exists():
            record = p.detrecord()
            if record.exists():
                if not(record[0].procesado and p.estado_accion in[6, 2]):
                    if not record[0] in excluir:
                        if p.inicio.month == p.fin.month:
                            if record[0] not in lista:
                                lista.append(record[0])
                        else:
                            if p.inicio.month <= mes <= p.fin.month:
                                if p.estado_accion not in [0, 4, 7]:
                                    if record[0] not in listadelmes:
                                        listadelmes.append(record[0])
                            else:
                                if record[0] not in lista:
                                    lista.append(record[0])
    data['evidencia_anterior'] = lista
    data['evidencia_mes'] = listadelmes
    data["leye_mes"] = conclusionesdos(data['evidencia_mes'], data, periodo, data['evidencia_anterior'], mes)
    data['secuencia'] = 0
    if informe.exists():
        if informe[0].tipo == 1:
            data['secu'] = 0
            data['tipo'] = "INFORME PRELIMINAR"
        else:
            data['tipo'] = "INFORME"
        data['secuencia'] = informe[0].numinfo
        data['tipoinforme'] = "INFORME DE CUMPLIMIENTO" if informe[0].tipo == 2 else "INFORME PRELIMINAR"
    else:
        data['tipoinforme'] = "INFORME PRELIMINAR"
        data['secu'] = 0
        data['tipo'] = "INFORME PRELIMINAR"
    return data

def datosinformecarrera(idp, idd, mes, idcar):
    data = {}
    data['idp'] = idp
    data['idd'] = idd
    data['idc'] = idcar
    data['nomcarrera'] = Carrera.objects.get(pk=idcar)
    data['mes_anterior'] = MESES_CHOICES[mes - 2][1]
    data['dos_meses'] = ACUMULAR_DOS_MESES
    periodo = PeriodoPoa.objects.get(pk=idp)
    departamento = Departamento.objects.get(pk=idd)
    data['periodo'] = periodo
    if not ACUMULAR_DOS_MESES:
        fechafinanterior = (datetime(periodo.anio, mes, 1, 0, 0, 0) - timedelta(days=1)).date()
    else:
        fechafinanterior = (datetime(periodo.anio, (mes - 1), 1, 0, 0, 0) - timedelta(days=1)).date()
    data['departamento'] = departamento
    data['mesid'] = mes
    data['nomtrimestre'] = trimestre(mes)
    data['mes'] = MESES_CHOICES[mes - 1][1]
    informe = InformeGenerado.objects.filter(mes=mes, periodopoa=periodo, departamento=departamento, carrera_id=idcar, status=True).order_by("-tipo")
    data['informe'] = informe[0] if informe.exists() else {}
    data['fecha'] = informe[0].fecha_creacion if informe.exists() else datetime.now().date()
    data['recomendacion'] = informe[0].recomendacion if informe.exists() else ""
    data['tipoid'] = 1 if not informe.exists() else 2
    evidencias = AccionDocumentoDetalleRecord.objects.filter(acciondocumentodetalle__acciondocumento__status=True, acciondocumentodetalle__status=True, acciondocumentodetalle__mostrar=True, procesado=False, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento,acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__id=idcar, status=True)
    if not ACUMULAR_DOS_MESES:
        evidencia_mes = evidencias.filter(acciondocumentodetalle__inicio__month=mes)
    else:
        mes1 = evidencias.filter(acciondocumentodetalle__inicio__month=mes)
        mes2 = evidencias.filter(acciondocumentodetalle__inicio__month=(mes - 1))
        if mes1:
            if mes2:
                evidencia_mes = mes1 | mes2
            else:
                evidencia_mes = mes1
        else:
            evidencia_mes = mes2

    usuarior = usuarioa = []
    if evidencia_mes:
        usuario = evidencia_mes.values("usuario_revisa").annotate(contador=Count("usuario_revisa")).order_by("usuario_revisa", "-contador")[:1]
        usuarior = evidencia_mes.values("usuario_revisa").annotate(contador=Count("usuario_revisa")).order_by("usuario_revisa", "-contador")[:1]
        usuarioa = evidencia_mes.values("usuario_aprobacion").annotate(contador=Count("usuario_aprobacion")).order_by("usuario_aprobacion", "-contador")[:1]
    else:
        datae = AccionDocumentoDetalle.objects.filter(acciondocumento__status=True, mostrar=True, inicio__lt=fechafinanterior, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento,acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__id=idcar, status=True).order_by("-inicio", "acciondocumento__indicadorpoa__objetivooperativo", "acciondocumento")
        if datae:
            ulti_mes = datae[0].inicio.month
            user_evidencia = datae.filter(inicio__month=ulti_mes)
            usuarior = user_evidencia.values("acciondocumentodetallerecord__usuario_revisa").annotate(contador=Count("acciondocumentodetallerecord__usuario_revisa")).order_by("acciondocumentodetallerecord__usuario_revisa", "-contador")[:1]
            usuarioa = user_evidencia.values("acciondocumentodetallerecord__usuario_aprobacion").annotate(contador=Count("acciondocumentodetallerecord__usuario_aprobacion")).order_by("acciondocumentodetallerecord__usuario_aprobacion", "-contador")[:1]

    firma = []
    elabora = False
    if usuarior or usuarioa:
        if evidencia_mes:
            r = Persona.objects.get(usuario_id=usuarior[0].get("usuario_revisa"))
            a = Persona.objects.get(usuario_id=usuarioa[0].get("usuario_aprobacion"))
        else:
            r = Persona.objects.get(usuario_id=usuarior[0].get("acciondocumentodetallerecord__usuario_revisa"))
            a = Persona.objects.get(usuario_id=usuarioa[0].get("acciondocumentodetallerecord__usuario_aprobacion"))

        if a.id != r.id:
            elabora = True
            firma.append(r)
            firma.append(a)
        else:
            firma.append(r)
    firma.append(Persona.objects.get(pk=PERSONA_APRUEBA_POA))
    data['firma'] = firma
    data['elabora'] = elabora
    listadelmes = []
    for e in evidencia_mes.order_by("-acciondocumentodetalle__inicio", "acciondocumentodetalle__acciondocumento__indicadorpoa__objetivooperativo", "acciondocumentodetalle__acciondocumento"):
        if e.estado_accion_aprobacion not in [0, 4, 7]:
            if e not in listadelmes:
                listadelmes.append(e)
    excluir = []
    for e in evidencias:
        if e.acciondocumentodetalle.inicio.month != e.acciondocumentodetalle.fin.month:
            if e.acciondocumentodetalle.inicio.month <= mes <= e.acciondocumentodetalle.fin.month:
                excluir.append(e)
                if e.estado_accion_aprobacion not in [0, 4, 7]:
                    if e not in listadelmes:
                        listadelmes.append(e)
    lista = []
    for p in AccionDocumentoDetalle.objects.filter(acciondocumento__status=True, mostrar=True, inicio__lt=fechafinanterior, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento,acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__id=idcar, status=True).order_by("-inicio", "acciondocumento__indicadorpoa__objetivooperativo", "acciondocumento"):
        if p.acciondocumentodetallerecord_set.exists():
            record = p.detrecord()
            if record.exists():
                if not(record[0].procesado and p.estado_accion in[6, 2]):
                    if not record[0] in excluir:
                        if p.inicio.month == p.fin.month:
                            if record[0] not in lista:
                                lista.append(record[0])
                        else:
                            if p.inicio.month <= mes <= p.fin.month:
                                if p.estado_accion not in [0, 4, 7]:
                                    if record[0] not in listadelmes:
                                        listadelmes.append(record[0])
                            else:
                                if record[0] not in lista:
                                    lista.append(record[0])
    data['evidencia_anterior'] = lista
    data['evidencia_mes'] = listadelmes
    data["leye_mes"] = conclusiones(data['evidencia_mes'], data, periodo, data['evidencia_anterior'], mes)
    data['secuencia'] = 0
    if informe.exists():
        if informe[0].tipo == 1:
            data['secu'] = 0
            data['tipo'] = "INFORME PRELIMINAR"
        else:
            data['tipo'] = "INFORME"
        data['secuencia'] = informe[0].numinfo
        data['tipoinforme'] = "INFORME DE CUMPLIMIENTO" if informe[0].tipo == 2 else "INFORME PRELIMINAR"
    else:
        data['tipoinforme'] = "INFORME PRELIMINAR"
        data['secu'] = 0
        data['tipo'] = "INFORME PRELIMINAR"
    return data


def conclusiones(evidencia_mes, data, periodo, evidencia_anterior, mes):
    leye_mes = []
    vector = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    if evidencia_mes:
        cont = 0
        for e in evidencia_mes:
            cont += 1
            vector[e.estado_accion_aprobacion] += 1
        leyendac = ""
        ind = uind = 0
        for e in vector:
            if e > 0:
                uind = ind
            ind += 1
        ind = sump = 0
        for e in range(8):
            if vector[e] > 0:
                if (cont - (vector[2])) > 0:
                    porce = round((float(vector[e]) / float(cont - (vector[2]))) * 100, 2)
                else:
                    porce = 0
                if ind == uind:
                    porce = 100 - sump
                elif ind not in [2]:
                    sump += porce
                if ind not in [2]:
                    leyendac += u" %s %s %s (%s%s)," % (vector[e], (u"acción" if vector[e] == 1 else "acciones"), (fraseaccion(e, vector)), porce, u"%")
            ind += 1
        if leyendac != "":
            if not ACUMULAR_DOS_MESES:
                # frase = u"Una vez cumplido el plazo de recepción de evidencias correspondientes a la ejecución del POA de " + data['mes'].lower() + " del " + str(periodo.anio) + u", se observa que" + leyendac[:-1] + "."
                frase = u"Una vez cumplido el plazo de recepción de evidencias correspondientes a la ejecución del POA del " + trimestre(mes) + " del " + str(periodo.anio) + u", se observa que" + leyendac[:-1] + "."
            else:
                frase = u"Una vez cumplido el plazo de recepción de evidencias correspondientes a la ejecución del POA de los meses " + data['mes'].lower() + "-" + data['mes_anterior'].lower() + " del " + str(periodo.anio) + u", se observa que" + leyendac[:-1] + "."
            leye_mes.append(frase)
    if evidencia_anterior:
        vector = [[0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0],
                  [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0],
                  [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0],
                  [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0]]
        cont = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        for e in evidencia_anterior:
            cont[e.acciondocumentodetalle.inicio.month - 1] += 1
            vector[e.acciondocumentodetalle.inicio.month - 1][e.estado_accion_aprobacion] += 1
        x = mes - 2
        while x >= 0:
            leyendac = ""
            ind = uind = 0
            for e in vector[x]:
                if e > 0:
                    uind = ind
                ind += 1
            ind = sump = 0
            for e in vector[x]:
                if e > 0:
                    if (cont[x] - vector[x][2]) > 0:
                        porce = round((float(e) / float(cont[x] - vector[x][2])) * 100, 2)
                    else:
                        porce = 0
                    if ind == uind:
                        porce = 100 - sump
                    elif ind not in [2]:
                        sump += porce
                    if ind not in [2]:
                        leyendac += u" %s %s %s (%s%s)," % (e, (u"acción" if e == 1 else "acciones"), (fraseaccion(ind, vector[x])), porce, u"%")
                ind += 1
            if leyendac != "":
                # frase = u"En las acciones del mes de " + MESES_CHOICES[x][1].lower() + " del " + str(periodo.anio) + u", se observa que" + leyendac[:-1] + "."
                frase = u"En las acciones del " + trimestre(x + 1) + " del " + str(periodo.anio) + u", se observa que" + leyendac[:-1] + "."
                leye_mes.append(frase)
            x -= 1
    return leye_mes


def conclusionesdos(evidencia_mes, data, periodo, evidencia_anterior, mes):
    leye_mes = []
    vector = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    if evidencia_mes:
        cont = 0
        for e in evidencia_mes:
            cont += 1
            vector[e.rubrica_aprobacion.id] += 1
        leyendac = ""
        ind = uind = 0
        for e in vector:
            if e > 0:
                uind = ind
            ind += 1
        ind = sump = 0
        for e in range(8):
            if vector[e] > 0:
                if (cont - (vector[2])) > 0:
                    porce = round((float(vector[e]) / float(cont - (vector[2]))) * 100, 2)
                else:
                    porce = 0
                if ind == uind:
                    porce = 100 - sump
                elif ind not in [2]:
                    sump += porce
                if ind not in [2]:
                    leyendac += u" %s %s %s (%s%s)," % (vector[e], (u"acción" if vector[e] == 1 else "acciones"), (fraseaccion(e, vector)), porce, u"%")
            ind += 1
        if leyendac != "":
            if not ACUMULAR_DOS_MESES:
                # frase = u"Una vez cumplido el plazo de recepción de evidencias correspondientes a la ejecución del POA de " + data['mes'].lower() + " del " + str(periodo.anio) + u", se observa que" + leyendac[:-1] + "."
                frase = u"Una vez cumplido el plazo de recepción de evidencias correspondientes a la ejecución del POA del " + trimestre(mes) + " del " + str(periodo.anio) + u", se observa que" + leyendac[:-1] + "."
            else:
                frase = u"Una vez cumplido el plazo de recepción de evidencias correspondientes a la ejecución del POA de los meses " + data['mes'].lower() + "-" + data['mes_anterior'].lower() + " del " + str(periodo.anio) + u", se observa que" + leyendac[:-1] + "."
            leye_mes.append(frase)
    if evidencia_anterior:
        vector = [[0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0],
                  [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0],
                  [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0],
                  [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0]]
        cont = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        for e in evidencia_anterior:
            cont[e.acciondocumentodetalle.inicio.month - 1] += 1
            vector[e.acciondocumentodetalle.inicio.month - 1][e.rubrica_aprobacion.id] += 1
        x = mes - 2
        while x >= 0:
            leyendac = ""
            ind = uind = 0
            for e in vector[x]:
                if e > 0:
                    uind = ind
                ind += 1
            ind = sump = 0
            for e in vector[x]:
                if e > 0:
                    if (cont[x] - vector[x][2]) > 0:
                        porce = round((float(e) / float(cont[x] - vector[x][2])) * 100, 2)
                    else:
                        porce = 0
                    if ind == uind:
                        porce = 100 - sump
                    elif ind not in [2]:
                        sump += porce
                    if ind not in [2]:
                        leyendac += u" %s %s %s (%s%s)," % (e, (u"acción" if e == 1 else "acciones"), (fraseaccion(ind, vector[x])), porce, u"%")
                ind += 1
            if leyendac != "":
                # frase = u"En las acciones del mes de " + MESES_CHOICES[x][1].lower() + " del " + str(periodo.anio) + u", se observa que" + leyendac[:-1] + "."
                frase = u"En las acciones del " + trimestre(x + 1) + " del " + str(periodo.anio) + u", se observa que" + leyendac[:-1] + "."
                leye_mes.append(frase)
            x -= 1
    return leye_mes

def fraseaccion(e, vector):
    tiene = ""
    if e == 1:  # no cumple
        tiene = "no cumple" if vector[e] == 1 else " no se cumplieron"
    elif e == 2:  # no aplica
        tiene = " no aplica" if vector[e] == 1 else " no aplican"
    elif e == 3:  # pendiente
        tiene = "tiene cumplimiento pendiente" if vector[e] == 1 else "tienen cumplimiento pendiente"
    elif e == 5:  # cumple parcial
        tiene = "tiene cumplimiento parcial" if vector[e] == 1 else "tienen cumplimiento parcial"
    elif e == 6:  # cumple total
        tiene = "tiene cumplimiento total" if vector[e] == 1 else " tienen cumplimiento total"
    return tiene


def listadecorreos(departamento):
    listacorreo = []
    for x in Persona.objects.filter(usuario__usuarioevidencia__unidadorganica=departamento, usuario__usuarioevidencia__status=True).distinct():
        listacorreo.extend(x.lista_emails_interno())
    for x in Persona.objects.filter(pk__in=COPIA_POA):
        listacorreo.extend(x.lista_emails_interno())
    return listacorreo
