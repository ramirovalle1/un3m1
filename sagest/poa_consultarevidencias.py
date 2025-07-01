# -*- coding: UTF-8 -*-

import json
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template
from decorators import secure_module
from sagest.forms import AccionDocumentoRevisaForm
from sagest.models import AccionDocumentoDetalle, AccionDocumentoDetalleRecord, PeriodoPoa, Departamento, \
    AccionDocumento, InformeGenerado, UsuarioConsultaEvidencia, ObjetivoEstrategico, UsuarioEvidencia
from settings import PERSONA_APRUEBA_POA
from sga.commonviews import adduserdata
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import MONTH_CHOICES, MESES_CHOICES, Persona, Carrera
from sga.funciones import log


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    data = {'title': u'Consultar Evidencia'}
    adduserdata(request, data)
    persona = request.session['persona']
    eUsuario = UsuarioEvidencia.objects.filter(userpermiso_id=persona.usuario_id, status=True,  tipopermiso=3)
    if not eUsuario:
        return HttpResponseRedirect("/?info=No tiene permiso para acceder a este módulo.")
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'sin_evidencia':
            try:
                f = AccionDocumentoRevisaForm(request.POST)
                if f.is_valid():
                    if int(request.POST['record']) == 0:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord(acciondocumentodetalle_id=int(request.POST['id']),
                                                                                    observacion_envia="SAGES: NO EXITE REGISTRADO EVIDENCIA",
                                                                                    observacion_revisa=f.cleaned_data['observacion'],
                                                                                    usuario_revisa=request.user,
                                                                                    estado_accion_revisa=f.cleaned_data['estado_accion'],
                                                                                    estado_accion_aprobacion=7,
                                                                                    fecha_revisa=datetime.now())
                    else:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(pk=int(request.POST['record']))
                        acciondocumentodetallerecord.observacion_revisa = f.cleaned_data['observacion']
                        acciondocumentodetallerecord.usuario_revisa = request.user
                        acciondocumentodetallerecord.estado_accion_revisa = f.cleaned_data['estado_accion']
                        acciondocumentodetallerecord.fecha_revisa = datetime.now()
                    acciondocumentodetallerecord.save(request)
                    acciondocumentodetallerecord.acciondocumentodetalle.estado_accion = 4
                    acciondocumentodetallerecord.acciondocumentodetalle.save(request)
                    log(u'Agrego archivo detalle record: %s' % acciondocumentodetallerecord, request, "add")
                    return HttpResponse(json.dumps({"result": "ok"}), content_type="application/json")
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": "Error al guardar los datos."}), content_type="application/json")

        elif action == 'ver_observacion':
            try:
                data = {}
                acciondocumento = AccionDocumento.objects.get(pk=int(request.GET['iddocumento']))
                return HttpResponse(json.dumps({"result": "ok", 'data': acciondocumento.observacion}),
                                    content_type="application/json")
            except Exception as ex:
                return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al obtener los datos."}),
                                    content_type="application/json")

        if action == 'con_evidencia':
            try:
                f = AccionDocumentoRevisaForm(request.POST)
                if f.is_valid():
                    if int(request.POST['record']) == 0:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord(acciondocumentodetalle_id=int(request.POST['id']),
                                                                                    observacion_revisa=f.cleaned_data['observacion'],
                                                                                    usuario_revisa=request.user,
                                                                                    estado_accion_revisa=f.cleaned_data['estado_accion'],
                                                                                    estado_accion_aprobacion=7,
                                                                                    fecha_revisa=datetime.now())
                    else:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(pk=int(request.POST['record']))
                        acciondocumentodetallerecord.observacion_revisa = f.cleaned_data['observacion']
                        acciondocumentodetallerecord.usuario_revisa = request.user
                        acciondocumentodetallerecord.estado_accion_revisa = f.cleaned_data['estado_accion']
                        acciondocumentodetallerecord.fecha_revisa = datetime.now()
                    acciondocumentodetallerecord.save(request)
                    acciondocumentodetallerecord.acciondocumentodetalle.estado_accion = 4
                    acciondocumentodetallerecord.acciondocumentodetalle.save(request)
                    log(u'Agrego archivo detalle record: %s' % acciondocumentodetallerecord, request, "add")
                    return HttpResponse(json.dumps({"result": "ok"}), content_type="application/json")
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": "Error al guardar los datos."}), content_type="application/json")

        if action == 'descargarpoapdf':
            try:
                departamento = Departamento.objects.get(pk=request.POST['iddepartamento'])
                periodopoa = PeriodoPoa.objects.get(pk=request.POST['idperiodopoa'])
                reportepdf = departamento.pdf_poadepartamento(periodopoa)
                return reportepdf
            except Exception as ex:
                pass

        return HttpResponse(json.dumps({"result": "bad", "mensaje": "Solicitud Incorrecta."}), content_type="application/json")
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'consultadepartamento':
                try:
                    data['title'] = u'Departamento consultar documentos.'
                    if int(request.GET['idp']) < 4:
                        ids = UsuarioEvidencia.objects.values_list('unidadorganica').filter(userpermiso_id=persona.usuario_id,status=True, tipopermiso=3)
                        data['departamento'] = Departamento.objects.filter(pk__in=ids,objetivoestrategico__periodopoa_id=int(request.GET['idp']), objetivoestrategico__status=True).distinct()
                        data['periodo'] = int(request.GET['idp'])
                        data['periodopoa'] = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                        return render(request, "poa_consultarevidencias/consultadepartamento.html", data)
                    else:
                        ids = UsuarioEvidencia.objects.values_list('unidadorganica').filter(userpermiso_id=persona.usuario_id, status=True, tipopermiso=3)
                        data['departamento'] = ObjetivoEstrategico.objects.values('departamento__id','departamento__nombre', 'carrera__id','carrera__nombre').filter(departamento__in=ids, periodopoa_id=int(request.GET['idp']), status=True).distinct().order_by('departamento__nombre', 'departamento__id', 'carrera__id', 'carrera__nombre')
                        data['periodo'] = int(request.GET['idp'])
                        data['periodopoa'] = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                        return render(request, "poa_consultarevidencias/consultadepartamentocarrera.html", data)
                except Exception as ex:
                    pass

            if action == 'consultadepartamentodos':
                try:
                    data['title'] = u'Departamento consultar documentos.'
                    ePermisos = UsuarioEvidencia.objects.filter(userpermiso_id=persona.usuario_id, status=True, tipopermiso=3)
                    filtro = Q(status=True, periodopoa_id=int(request.GET['idp']))
                    idsd = list(ePermisos.filter(unidadorganica__isnull=False, gestion__isnull=True, carrera__isnull=True).values_list('unidadorganica_id', flat=True))
                    idsg = list(ePermisos.filter(unidadorganica__isnull=False, gestion__isnull=False, carrera__isnull=True).values_list('gestion_id', flat=True))
                    idsc = list(ePermisos.filter(unidadorganica__isnull=False, gestion__isnull=True, carrera__isnull=False).values_list('carrera_id', flat=True))
                    filtro_ids = Q()
                    if idsd:
                        filtro_ids |= Q(departamento_id__in=idsd)
                    if idsg:
                        filtro_ids |= Q(gestion_id__in=idsg)
                    if idsc:
                        filtro_ids |= Q(carrera_id__in=idsc)
                    filtro &= filtro_ids
                    data['departamento'] = ObjetivoEstrategico.objects.filter(filtro).distinct()
                    data['periodo'] = int(request.GET['idp'])
                    data['periodopoa'] = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                    return render(request, "poa_consultarevidencias/consultadepartamentodos.html", data)
                except Exception as ex:
                    pass

            elif action == 'poadepartamento':
                try:
                    data['title'] = u'Consultar POA.'
                    if int(request.GET['idp']) < 4:
                        if UsuarioEvidencia.objects.filter(userpermiso_id=persona.usuario_id,
                                                           tipopermiso=3,
                                                           status=True,
                                                           unidadorganica_id=int(request.GET['idd'])).exists():
                            a = 0
                        else:
                            return HttpResponseRedirect("/?info=No tiene permiso para acceder a este módulo.")
                        data['departamento'] = Departamento.objects.get(pk=int(request.GET['idd']))
                        data['meses'] = [x[1][:3] for x in MONTH_CHOICES]
                        data['idp'] = int(request.GET['idp'])
                        data['idd'] = int(request.GET['idd'])
                        data['periodopoa'] = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                        data['documento'] = AccionDocumento.objects.filter(status=True, acciondocumentodetalle__status=True, indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']), indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).order_by('indicadorpoa__objetivooperativo', 'indicadorpoa').distinct()
                        return render(request, "poa_consultarevidencias/poadepartamento.html", data)
                    else:
                        if UsuarioEvidencia.objects.filter(userpermiso_id=persona.usuario_id,
                                                                   tipopermiso=3,
                                                                   status=True,
                                                                   unidadorganica_id=int(request.GET['idd'])).exists():
                            a = 0
                        else:
                            return HttpResponseRedirect("/?info=No tiene permiso para acceder a este módulo.")
                        data['departamento'] = Departamento.objects.get(pk=int(request.GET['idd']))
                        data['meses'] = [x[1][:3] for x in MONTH_CHOICES]
                        data['idp'] = int(request.GET['idp'])
                        data['idd'] = int(request.GET['idd'])
                        data['idc'] = int(request.GET['idc'])
                        data['periodopoa'] = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                        data['carrera'] = ''
                        if data['idc']!=0:
                            data['carrera'] = Carrera.objects.get(pk=int(request.GET['idc']))
                            data['documento'] = AccionDocumento.objects.filter(status=True, acciondocumentodetalle__status=True, indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']),indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera_id=int(request.GET['idc']), indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).order_by('indicadorpoa__objetivooperativo', 'indicadorpoa').distinct()
                        else:
                            data['documento'] = AccionDocumento.objects.filter(status=True, acciondocumentodetalle__status=True, indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']),indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True, indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).order_by('indicadorpoa__objetivooperativo', 'indicadorpoa').distinct()
                        return render(request, "poa_consultarevidencias/poadepartamentocarrera.html", data)
                except Exception as ex:
                    pass

            elif action == 'poadepartamentodos':
                try:
                    data['title'] = u'Consultar POA.'
                    if UsuarioEvidencia.objects.filter(userpermiso_id=persona.usuario_id,
                                                       tipopermiso=3,
                                                       status=True,
                                                       unidadorganica_id=int(request.GET['idd'])).exists():
                        a = 0
                    else:
                        return HttpResponseRedirect("/?info=No tiene permiso para acceder a este módulo.")
                    data['departamento'] = Departamento.objects.get(pk=int(request.GET['idd']))
                    data['meses'] = [x[1][:3] for x in MONTH_CHOICES]
                    data['idp'] = int(request.GET['idp'])
                    data['idd'] = int(request.GET['idd'])
                    data['idc'] = int(request.GET['idc'])
                    data['periodopoa'] = PeriodoPoa.objects.get(pk=int(request.GET['idp']))
                    data['carrera'] = ''
                    if data['idc']!=0:
                        data['carrera'] = Carrera.objects.get(pk=int(request.GET['idc']))
                        data['documento'] = AccionDocumento.objects.filter(status=True, acciondocumentodetalle__status=True, indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']),indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera_id=int(request.GET['idc']), indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).order_by('indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__orden','indicadorpoa__objetivooperativo__objetivotactico__orden','indicadorpoa__objetivooperativo__orden','indicadorpoa__orden','orden').distinct()
                    else:
                        data['documento'] = AccionDocumento.objects.filter(status=True, acciondocumentodetalle__status=True, indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=int(request.GET['idd']),indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True, indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).order_by('indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__orden','indicadorpoa__objetivooperativo__objetivotactico__orden','indicadorpoa__objetivooperativo__orden','indicadorpoa__orden','orden').distinct()
                    return render(request, "poa_consultarevidencias/poadepartamentodos.html", data)
                except Exception as ex:
                    pass

            elif action == 'sin_evidencia':
                try:
                    data = {}
                    acciondocumentodetalle = AccionDocumentoDetalle.objects.get(pk=int(request.GET['iddocdet']))
                    if int(request.GET['record']) == 0:
                        form = AccionDocumentoRevisaForm()
                    else:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(pk=int(request.GET['record']))
                        form = AccionDocumentoRevisaForm(initial={'observacion': acciondocumentodetallerecord.observacion_revisa,
                                                                  'estado_accion': acciondocumentodetallerecord.estado_accion_revisa})
                    data['records'] = acciondocumentodetalle.acciondocumentodetallerecord_set.all().order_by("-id")
                    form.tipo_sin_evidencia(1)
                    data['form'] = form
                    data['modadd'] = True if int(request.GET['listo']) == 0 else False
                    data['record'] = int(request.GET['record'])
                    data['idp'] = int(request.GET['idp'])
                    data['idd'] = int(request.GET['idd'])
                    data['permite_modificar'] = True
                    data['acciondocumentodetalle'] = acciondocumentodetalle.__str__()
                    data['id'] = acciondocumentodetalle.id
                    template = get_template("poa_consultarevidencias/sin_evidencia.html")
                    json_content = template.render(data)
                    return HttpResponse(json.dumps({"result": "ok", 'data': json_content}), content_type="application/json")
                except Exception as ex:
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al obtener los datos."}), content_type="application/json")

            elif action == 'con_evidencia':
                try:
                    data = {}
                    acciondocumentodetalle = AccionDocumentoDetalle.objects.get(pk=int(request.GET['iddocdet']))
                    if int(request.GET['record']) == 0:
                        form = AccionDocumentoRevisaForm()
                    else:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(pk=int(request.GET['record']))
                        form = AccionDocumentoRevisaForm(initial={'observacion': acciondocumentodetallerecord.observacion_revisa,
                                                                  'estado_accion': acciondocumentodetallerecord.estado_accion_revisa})
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
                    template = get_template("poa_consultarevidencias/con_evidencia.html")
                    json_content = template.render(data)
                    return HttpResponse(json.dumps({"result": "ok", 'data': json_content}), content_type="application/json")
                except Exception as ex:
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al obtener los datos."}), content_type="application/json")

            elif action == 'monitoreo':
                try:
                    data = {}
                    data['idp'] = int(request.GET['idp'])
                    data['idd'] = int(request.GET['idd'])
                    data['meses'] = [x[1] for x in MONTH_CHOICES]
                    data['mes'] = datetime.now().month - 1
                    data['departamento'] = Departamento.objects.get(pk=int(request.GET['idd']))
                    if not Persona.objects.filter(usuario__usuarioevidencia__tipousuario=2, usuario__usuarioevidencia__unidadorganica_id=int(request.GET['idd'])).exists():
                        return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Este departamento no tiene configurado el director, realizarlo en la opcion - Poa Usuario registra"}), content_type="application/json")
                    template = get_template("poa_revisaevidencia/monitoreo_view.html")
                    json_content = template.render(data)
                    return HttpResponse(json.dumps({"result": "ok", 'data': json_content}), content_type="application/json")
                except Exception as ex:
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al obtener los datos."}), content_type="application/json")

            elif action == 'monitoreo_pdf':
                try:
                    data = datosinforme(int(request.GET['idp']), int(request.GET['idd']), int(request.GET['mes']))
                    firma = [Persona.objects.get(usuario=request.user), Persona.objects.get(pk=PERSONA_APRUEBA_POA),
                             Persona.objects.get(usuario__usuarioevidencia__tipousuario=2, usuario__usuarioevidencia__unidadorganica_id=int(request.GET['idd']))]
                    data['firma'] = firma
                    return conviert_html_to_pdf('poa_consultarevidencias/monitoreo_pdf.html', {'pagesize': 'A4', 'data': data})
                except Exception as ex:
                    pass

            elif action == 'informe':
                try:
                    data = {}
                    data['idp'] = int(request.GET['idp'])
                    data['idd'] = int(request.GET['idd'])
                    data['mes'] = mes = int(request.GET['mes'])
                    informe = InformeGenerado.objects.filter(mes=mes, periodopoa_id=int(request.GET['idp']), departamento_id=int(request.GET['idd']), status=True)
                    data['informepre'] = informe.filter(tipo=1)[0] if informe.filter(tipo=1).exists() else {}
                    data['informefin'] = informe.filter(tipo=2)[0] if informe.filter(tipo=2).exists() else {}
                    template = get_template("poa_consultarevidencias/informe_view.html")
                    json_content = template.render(data)
                    return HttpResponse(json.dumps({"result": "ok", 'data': json_content}), content_type="application/json")
                except Exception as ex:
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al obtener los datos."}), content_type="application/json")

            return HttpResponseRedirect(request.path)
        else:
            periodo = PeriodoPoa.objects.filter(status=True).order_by('-anio')
            data['periodo'] = periodo
            return render(request, "poa_consultarevidencias/view.html", data)


def datosinforme(idp, idd, mes):
    data = {}
    data['idp'] = idp
    data['idd'] = idd
    periodo = PeriodoPoa.objects.get(pk=idp)
    departamento = Departamento.objects.get(pk=idd)
    data['periodo'] = periodo
    fechafinanterior = (datetime(periodo.anio, mes, 1, 0, 0, 0) - timedelta(days=1)).date()
    data['departamento'] = departamento
    data['mesid'] = mes
    data['mes'] = MESES_CHOICES[mes - 1][1]
    evidencias = AccionDocumentoDetalle.objects.filter(acciondocumento__status=True, mostrar=True, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento, status=True).distinct()
    evidencia_mes = evidencias.filter(inicio__month=mes).distinct()
    listadelmes = []
    for e in evidencia_mes.order_by("acciondocumento__indicadorpoa__objetivooperativo", "acciondocumento"):
        if e not in listadelmes:
            listadelmes.append(e)
    excluir = []
    for e in evidencias:
        if e.inicio.month != e.fin.month:
            if e.inicio.month <= mes <= e.fin.month:
                excluir.append(e)
                if e not in listadelmes:
                    listadelmes.append(e)
    lista = []
    for p in AccionDocumentoDetalle.objects.filter(acciondocumento__status=True, mostrar=True, inicio__lt=fechafinanterior, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa=periodo, acciondocumento__indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento=departamento, status=True).order_by("-inicio", "acciondocumento__indicadorpoa__objetivooperativo", "acciondocumento").distinct():
        if not (p.estado_accion in [6, 2]):
            if p.acciondocumentodetallerecord_set.exists():
                record = p.detrecord()
                if record.exists():
                    if not record[0] in excluir:
                        if record[0].acciondocumentodetalle.inicio.month == record[0].acciondocumentodetalle.fin.month:
                            if record[0] not in lista:
                                lista.append(record[0])
                        else:
                            if record[0].acciondocumentodetalle.inicio.month <= mes <= record[0].acciondocumentodetalle.fin.month:
                                if record[0] not in listadelmes:
                                    listadelmes.append(record[0])
                            else:
                                if record[0] not in lista:
                                    lista.append(record[0])

    data['evidencia_anterior'] = lista
    data['evidencia_mes'] = listadelmes
    return data
