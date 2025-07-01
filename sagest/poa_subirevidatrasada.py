# -*- coding: UTF-8 -*-

from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import  HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template

from decorators import secure_module
from sagest.forms import AccionDocumentoDetalleForm
from sagest.models import AccionDocumentoDetalle, AccionDocumentoDetalleRecord, PeriodoPoa, Departamento, \
    AccionDocumento, \
    InformeGenerado, UsuarioEvidencia, PoaArchivo, ObjetivoEstrategico
from sga.commonviews import adduserdata
from sga.funciones import generar_nombre,log
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import MONTH_CHOICES


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    data = {'title': u'Ingresar y consultar evidencias.'}
    adduserdata(request, data)
    persona = data['persona']
    usuario = UsuarioEvidencia.objects.filter(status=True, userpermiso=persona.usuario, tipopermiso=1).first()
    if not usuario:
        return HttpResponseRedirect("/?info=No tiene permisos asignado para este modulo.")
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'sin_evidencia':
            try:
                f = AccionDocumentoDetalleForm(request.POST, request.FILES)
                if f.is_valid():
                    if int(request.POST['record']) != 0:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(pk=int(request.POST['record']))
                        acciondocumentodetallerecord.observacion_envia = f.cleaned_data['observacion_envia']
                        acciondocumentodetallerecord.usuario_envia = request.user
                        acciondocumentodetallerecord.fecha_envia = datetime.now()
                        acciondocumentodetallerecord.save(request)
                    else:
                        acciondocumentodetalle = AccionDocumentoDetalle.objects.get(pk=int(request.POST['id']))
                        acciondocumentodetalle.acciondocumentodetallerecord_set.filter(procesado=False, status=True).update(procesado=True, status=False)
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord(acciondocumentodetalle=acciondocumentodetalle,
                                                                                    observacion_envia=f.cleaned_data['observacion_envia'],
                                                                                    usuario_envia=request.user,
                                                                                    estado_accion_aprobacion=7,
                                                                                    estado_accion_revisa=7,
                                                                                    fecha_envia=datetime.now())
                        acciondocumentodetallerecord.save(request)
                        acciondocumentodetalle.estado_accion = 7
                        acciondocumentodetalle.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            newfile._name = generar_nombre("Evidencia", newfile._name)
                            acciondocumentodetallerecord.archivo = newfile
                            acciondocumentodetallerecord.save(request)
                    log(u'añadio evidencia atrasada para revision sin evidencia: %s' % acciondocumentodetallerecord.id, request,
                        "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'descargarpoapdf':
            try:
                departamento = Departamento.objects.get(pk=usuario.unidadorganica_id)
                periodopoa = PeriodoPoa.objects.get(pk=request.POST['idperiodopoa'])
                datos = departamento.pdf_poadepartamento(periodopoa)
                return datos
            except Exception as ex:
                pass

        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'ver_observacion':
                try:
                    data = {}
                    acciondocumento = AccionDocumento.objects.get(pk=int(request.GET['iddocumento']))
                    return JsonResponse({"result": "ok", 'data': acciondocumento.observacion})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'ver_medio':
                try:
                    data = {}
                    acciondocumento = AccionDocumento.objects.get(pk=int(request.GET['iddocumento']))
                    return JsonResponse({"result": "ok", 'data': acciondocumento.medioverificacion.nombre})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'revisadepartamento':
                try:
                    data['title'] = u'POA Ingresar y consultar evidencias.'
                    data['departamento'] = departamento = Departamento.objects.get(pk=usuario.unidadorganica_id)
                    data['meses'] = MONTH_CHOICES
                    data['idp'] = int(request.GET['idp'])
                    fechamax = None
                    if int(request.GET['idp']) < 4:
                        data['idd'] = departamento.id
                        informegenerado = InformeGenerado.objects.filter(departamento=departamento, status=True).order_by("-id")
                        fechamax = informegenerado[0].fechamax if informegenerado.exists() else datetime.now().date() - timedelta(days=1)
                        if informegenerado.exists():
                            if informegenerado[0].tipo == 2 and not informegenerado[0].procesado:
                                fechamax = datetime.now().date() - timedelta(days=1)
                        data['fechamax'] = fechamax
                        data['habilitado'] = True if datetime.now().date() <= fechamax else False
                        data['mes_actual'] = 12 if PeriodoPoa.objects.get(pk=int(request.GET['idp'])).anio < datetime.now().year else datetime.now().month
                        data['documento'] = AccionDocumento.objects.filter(status=True, acciondocumentodetalle__status=True, acciondocumentodetalle__mostrar=True, indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=departamento.id, indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(request.GET['idp'])).order_by('indicadorpoa__objetivooperativo', 'indicadorpoa').distinct()
                        d = PoaArchivo.objects.filter(unidadorganica=departamento, status=True, periodopoa_id=int(request.GET['idp'])).order_by('-fecha')
                        if d:
                            data['p'] = d[0]
                        return render(request, "poa_subirevidatrasada/poadepartamento.html", data)
                    else:
                        if usuario.carrera_id:
                            data['idd'] = departamento.id
                            informegenerado = InformeGenerado.objects.filter(departamento=departamento, status=True, periodopoa_id=data['idp']).order_by("-id")
                            if departamento.id in[7, 13]:
                                fechamax = informegenerado[0].fechamax if informegenerado.exists() else datetime.now().date() # - timedelta(days=1)
                            else:
                                # fechamax = informegenerado[0].fechamax if informegenerado.exists() else datetime.now().date() - timedelta(days=1)
                                informefechamax = InformeGenerado.objects.filter(departamento=departamento, status=True,periodopoa_id=data['idp'],carrera_id=usuario.carrera_id).order_by("-fechamax")
                                fechamax = informefechamax[0].fechamax
                            # if informegenerado.exists():
                            #     if informegenerado[0].tipo == 2 and not informegenerado[0].procesado:
                            #         fechamax = datetime.now().date() - timedelta(days=1)
                            data['fechamax'] = fechamax
                            data['habilitado'] = True if datetime.now().date() <= fechamax else False
                            data['mes_actual'] = 12 if PeriodoPoa.objects.get(
                                pk=int(request.GET['idp'])).anio < datetime.now().year else datetime.now().month
                            data['documento'] = AccionDocumento.objects.filter(status=True,
                                                                               acciondocumentodetalle__status=True,
                                                                               acciondocumentodetalle__mostrar=True,
                                                                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=departamento.id,
                                                                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera_id=usuario.carrera_id,
                                                                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(
                                                                                   request.GET['idp'])).order_by(
                                'indicadorpoa__objetivooperativo', 'indicadorpoa').distinct()
                            d = PoaArchivo.objects.filter(unidadorganica=departamento, status=True,
                                                          periodopoa_id=int(request.GET['idp'])).order_by('-fecha')
                            if d:
                                data['p'] = d[0]
                        else:
                            data['idd'] = departamento.id
                            informegenerado = InformeGenerado.objects.filter(departamento=departamento, status=True, periodopoa_id=data['idp']).order_by("-id")
                            if departamento.id in[7, 13]:
                                fechamax = informegenerado[0].fechamax if informegenerado.exists() else datetime.now().date() # - timedelta(days=1)
                            else:
                                informefechamax = InformeGenerado.objects.filter(departamento=departamento, status=True,periodopoa_id=data['idp'],carrera__isnull=True).order_by("-fechamax")
                                if informefechamax:
                                    fechamax = informefechamax[0].fechamax
                                # fechamax = informegenerado[0].fechamax if informegenerado.exists() else datetime.now().date() - timedelta(days=1)
                            # if informegenerado.exists():
                            #     if informegenerado[0].tipo == 2 and not informegenerado[0].procesado:
                            #         fechamax = datetime.now().date() - timedelta(days=1)
                            if fechamax:
                                data['fechamax'] = fechamax
                                data['habilitado'] = True if datetime.now().date() <= fechamax else False
                            data['mes_actual'] = 12 if PeriodoPoa.objects.get(pk=int(request.GET['idp'])).anio < datetime.now().year else datetime.now().month
                            data['documento'] = AccionDocumento.objects.filter(status=True,
                                                                               acciondocumentodetalle__status=True,
                                                                               acciondocumentodetalle__mostrar=True,
                                                                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=departamento.id,
                                                                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True,
                                                                               indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(
                                                                                   request.GET['idp'])).order_by(
                                'indicadorpoa__objetivooperativo', 'indicadorpoa').distinct()
                            d = PoaArchivo.objects.filter(unidadorganica=departamento, status=True,
                                                          periodopoa_id=int(request.GET['idp'])).order_by('-fecha')
                            if d:
                                data['p'] = d[0]

                        return render(request, "poa_subirevidatrasada/poadepartamentocarrera.html", data)
                except Exception as ex:
                    pass

            if action == 'revisadepartamentodos':
                try:
                    data['title'] = u'POA Ingresar y consultar evidencias.'
                    data['departamento'] = departamento = Departamento.objects.get(pk=usuario.unidadorganica_id)
                    data['meses'] = MONTH_CHOICES
                    data['idp'] = int(request.GET['idp'])
                    fechamax = None
                    periodopoa = PeriodoPoa.objects.get(pk=data['idp'])
                    if periodopoa.informegenerado_set.filter(departamento=departamento, status=True):
                        fechamax = periodopoa.informegenerado_set.filter(departamento=departamento, status=True).order_by('-id')[0].fechamax
                    data['idd'] = departamento.id
                    # informegenerado = InformeGenerado.objects.filter(departamento=departamento, status=True, periodopoa_id=data['idp']).order_by("-id")
                    # if departamento.id in[7, 13]:
                    #     fechamax = informegenerado[0].fechamax if informegenerado.exists() else datetime.now().date() # - timedelta(days=1)
                    # else:
                    #     informefechamax = InformeGenerado.objects.filter(departamento=departamento, status=True,periodopoa_id=data['idp'],carrera__isnull=True).order_by("-fechamax")
                    #     if informefechamax:
                    #         fechamax = informefechamax[0].fechamax
                        # fechamax = informegenerado[0].fechamax if informegenerado.exists() else datetime.now().date() - timedelta(days=1)
                    # if informegenerado.exists():
                    #     if informegenerado[0].tipo == 2 and not informegenerado[0].procesado:
                    #         fechamax = datetime.now().date() - timedelta(days=1)
                    if fechamax:
                        data['fechamax'] = fechamax
                        data['habilitado'] = True if datetime.now().date() <= fechamax else False
                    data['mes_actual'] = 12 if PeriodoPoa.objects.get(pk=int(request.GET['idp'])).anio < datetime.now().year else datetime.now().month
                    data['documento'] = AccionDocumento.objects.filter(status=True,
                                                                       acciondocumentodetalle__status=True,
                                                                       acciondocumentodetalle__mostrar=True,
                                                                       indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__departamento_id=departamento.id,
                                                                       indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__carrera__isnull=True,
                                                                       indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=int(
                                                                           request.GET['idp'])).order_by('indicadorpoa__objetivooperativo__objetivotactico__objetivoestrategico__orden','indicadorpoa__objetivooperativo__objetivotactico__orden','indicadorpoa__objetivooperativo__orden','indicadorpoa__orden','orden').distinct()
                    d = PoaArchivo.objects.filter(unidadorganica=departamento, status=True, periodopoa_id=int(request.GET['idp'])).order_by('-fecha')
                    if d:
                        data['p'] = d[0]
                    return render(request, "poa_subirevidatrasada/revisadepartamentodos.html", data)
                except Exception as ex:
                    pass

            elif action == 'sin_evidencia' or action == 'con_evidencia':
                try:
                    data = {}
                    acciondocumentodetalle = AccionDocumentoDetalle.objects.get(pk=int(request.GET['iddocdet']))
                    data['documentodetallerecord'] = {}
                    if int(request.GET['record']) == 0:
                        data['form'] = AccionDocumentoDetalleForm
                    else:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(pk=int(request.GET['record']))
                        data['form'] = AccionDocumentoDetalleForm(initial={'observacion_envia': acciondocumentodetallerecord.observacion_envia})
                        data['documentodetallerecord'] = acciondocumentodetallerecord
                    data['permite_modificar'] = True
                    data['record'] = int(request.GET['record'])
                    data['modadd'] = True if int(request.GET['listo']) == 0 else False
                    data['records'] = acciondocumentodetalle.acciondocumentodetallerecord_set.all().order_by("-id")
                    data['acciondocumentodetalle'] = acciondocumentodetalle.__str__()
                    data['id'] = acciondocumentodetalle.id
                    data['idp'] = int(request.GET['idp'])
                    template = get_template("poa_subirevidatrasada/add_evidencia.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'sin_evidenciados' or action == 'con_evidenciados':
                try:
                    data = {}
                    acciondocumentodetalle = AccionDocumentoDetalle.objects.get(pk=int(request.GET['iddocdet']))
                    data['documentodetallerecord'] = {}
                    if int(request.GET['record']) == 0:
                        data['form'] = AccionDocumentoDetalleForm
                    else:
                        acciondocumentodetallerecord = AccionDocumentoDetalleRecord.objects.get(pk=int(request.GET['record']))
                        data['form'] = AccionDocumentoDetalleForm(initial={'observacion_envia': acciondocumentodetallerecord.observacion_envia})
                        data['documentodetallerecord'] = acciondocumentodetallerecord
                    data['permite_modificar'] = True
                    data['record'] = int(request.GET['record'])
                    data['modadd'] = True if int(request.GET['listo']) == 0 else False
                    data['records'] = acciondocumentodetalle.acciondocumentodetallerecord_set.all().order_by("-id")
                    data['acciondocumentodetalle'] = acciondocumentodetalle
                    data['id'] = acciondocumentodetalle.id
                    data['idp'] = int(request.GET['idp'])
                    template = get_template("poa_subirevidatrasada/add_evidenciados.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)
        else:
            periodo = PeriodoPoa.objects.filter(status=True, mostrar=True).order_by('-id')
            data['periodo'] = periodo
            return render(request, "poa_subirevidatrasada/view.html", data)