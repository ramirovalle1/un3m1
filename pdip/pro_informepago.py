import io
import json
import os
import sys
import time
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q, Sum, F, Avg, DecimalField, ExpressionWrapper
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template

from core.firmar_documentos import obtener_posicion_x_y_saltolinea
from core.firmar_documentos_ec import JavaFirmaEc
from decorators import secure_module
from inno.models import InformeMensualDocente, HorasInformeMensualDocente, HistorialInforme
from pdip.forms import SolicitudInformePagoForm
from pdip.models import ContratoDip, SolicitudPago, RequisitoSolicitudPago, HistorialProcesoSolicitud, \
    HistorialObseracionSolicitudPago, SolicitudInformePago, ContratoCarrera, ContratoAreaPrograma
from sga.commonviews import adduserdata
from sga.funciones import variable_valor, MiPaginador, convertir_fecha_hora_invertida, log, notificacion
from sga.funcionesxhtml2pdf import conviert_html_to_pdf_name_bitacora
from sga.models import Profesor, DetalleDistributivo
from sga.templatetags.sga_extras import encrypt, nombremes


@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    usuario = request.user
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    # if not perfilprincipal.es_profesor():
    #     return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    data['profesor'] = profesor = perfilprincipal.profesor
    periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addsolicitudinfoconsolidado':
            try:
                data['hoy'] = hoy = datetime.now()
                id = request.POST.get('id', None)
                contrato = ContratoDip.objects.get(status=True, id=int(encrypt(id)))
                form = SolicitudInformePagoForm(request.POST)
                lista_id = json.loads(request.POST.get('lista_items1', None))
                if len(lista_id) <= 0: raise NameError("Debe seleccionar al menos un informe mensual")

                if not form.is_valid():
                    raise NameError(f"{[{k:v[0]} for k,v in form.errors.items()]}")
                fi,ff = form.cleaned_data['fechainicio'], form.cleaned_data['fechafin']
                sec_informe = contrato.secuencia_informe()
                if SolicitudPago.objects.values('id').filter(status=True, fechainicio__date=fi,
                                                             fechaifin__date=ff,
                                                             contrato=contrato).exists():
                    raise NameError(f"Estimad{'o' if persona.es_mujer() else 'a'} {persona}, ya cuenta con una solicitud en las fechas indicadas, favor de revisar en informes generados de posgrado.")
                solicitud = SolicitudPago(
                    fechainicio=fi,
                    fechaifin=ff,
                    contrato=contrato,
                    estado=0,
                    numero=sec_informe
                )
                solicitud.save(request)
                hrs_total = 0.0
                hrs_totales_contr = contrato.get_tiempo_dedicacion()
                for id_l in lista_id:
                    info_mensual = InformeMensualDocente.objects.get(status=True,id=int(encrypt(id_l)))
                    total_horas = DetalleDistributivo.objects.filter(status=True, distributivo=info_mensual.distributivo).aggregate(total_horas=Sum('horas'))['total_horas']
                    sol_info = SolicitudInformePago(solicitud=solicitud, informe_id=int(encrypt(id_l)))
                    sol_info.save(request)
                    hrs_total += total_horas if total_horas else 0
                if hrs_total > hrs_totales_contr: raise NameError(
                    f'Suma un total de {hrs_total} horas semanales y su maximo de horas semanales es {hrs_totales_contr}')
                data['fini'], data['ffin'] = fi, ff
                data['contrato'] = contrato
                data['carreras'] = ContratoCarrera.objects.filter(contrato=contrato, status=True)
                data['areasprogramas'] = ContratoAreaPrograma.objects.filter(contrato=contrato, status=True)
                data['periodos'] = inf = InformeMensualDocente.objects.filter(status=True,solicitudinformepago__solicitud=solicitud)
                data['criterios'] = detalles = DetalleDistributivo.objects.filter(status=True,
                                                                                  distributivo_id__in=inf.values_list(
                                                                                      'distributivo_id',
                                                                                      flat=True)).annotate(
                    hrs_total=Sum('horas')).distinct()
                data['resmuen_criterios'] = HorasInformeMensualDocente.objects.filter(status=True,
                                                                                      informe__in=inf.values_list('id',
                                                                                                                  flat=True)) \
                    .values_list("criteriodocenciaperiodo__criterio__id", "criteriodocenciaperiodo__criterio__nombre") \
                    .annotate(hpm_total=Sum('hpm'), hem_total=Sum('hem'), pcm_total=ExpressionWrapper(
                    F('hem_total') * 100.0 / F('hpm_total'),
                    output_field=DecimalField(max_digits=5, decimal_places=2)
                ), ).order_by('criteriodocenciaperiodo__criterio__id').distinct()
                data['resumen_total'] = horas = HorasInformeMensualDocente.objects.filter(status=True,
                                                                                          informe__in=inf.values_list(
                                                                                              'id', flat=True)) \
                    .aggregate(hpm_total=Sum('hpm'), hem_total=Sum('hem'))
                data['porcentaje_resumentotal'] = (horas['hem_total'] / horas['hpm_total']) * 100
                titulaciones = persona.mis_titulaciones()
                data['titulaciones'] = titulaciones = titulaciones.filter(titulo__nivel_id__in=[3, 4])

                nombresinciales = ''
                nombre = persona.nombres.split()
                if len(nombre) > 1:
                    nombresiniciales = '{}{}'.format(nombre[0][0], nombre[1][0])
                else:
                    nombresiniciales = '{}'.format(nombre[0][0])
                inicialespersona = '{}{}{}'.format(nombresiniciales, persona.apellido1[0], persona.apellido2[0])
                name_file = f'informe_actividad_diaria_{inicialespersona.lower()}_{solicitud.numero}.pdf'
                resp = conviert_html_to_pdf_name_bitacora(
                    'pro_informepago/informe_consolidadopdf.html',
                    {"data": data}, name_file)
                if resp[0]:
                    resp[1].seek(0)
                    fil_content = resp[1].read()
                    resp = ContentFile(fil_content)
                else:
                    return resp[1]
                if RequisitoSolicitudPago.objects.values('id').filter(status=True, solicitud=solicitud,requisito_id=14).exists():
                    requisito = RequisitoSolicitudPago.objects.filter(status=True, solicitud=solicitud,requisito_id=14).order_by('-id').first()
                else:
                    requisito = RequisitoSolicitudPago(
                        solicitud=solicitud,
                        requisito_id=14,#producion 14
                        observacion=f'Informe generado por {persona.__str__()}'
                    )
                    requisito.save(request)
                if HistorialProcesoSolicitud.objects.filter(status=True, persona_ejecucion=persona,requisito=requisito):
                    hist_= HistorialProcesoSolicitud.objects.filter(status=True, persona_ejecucion=persona,requisito=requisito).order_by('-id').first()
                    hist_.fecha_ejecucion=hoy
                else:
                    hist_ = HistorialProcesoSolicitud(
                        observacion=f'Informe firmado por {persona.__str__()}',
                        fecha_ejecucion=hoy,
                        persona_ejecucion=persona,
                        requisito=requisito
                    )
                hist_.archivo.save(f'{name_file.replace(".pdf", "")}.pdf',resp)
                hist_.save(request)
                cuerpo = f"Informe mensual de posgrado generado por {persona}"

                obshisto = HistorialObseracionSolicitudPago(
                    solicitud=solicitud,
                    observacion=cuerpo,
                    persona=persona,
                    estado=0,
                    fecha=hoy
                )
                obshisto.save(request)
                log(f'Genero el informe mensual de la solicitud: {solicitud}', request, 'change')
                template = get_template("formfirmaelectronica.html")
                res_js = {'result':False,}
            except Exception as ex:
                transaction.set_rollback(True)
                msg_err = f"{ex} ({sys.exc_info()[-1].tb_lineno})"
                res_js = {'result':True, 'mensaje':msg_err}
            return JsonResponse(res_js)

        elif action == 'delsolicitud':
            try:
                id = request.POST.get('id', None)
                soli = SolicitudPago.objects.get(status=True, id=int(encrypt(id)))
                soli.status=False
                soli.save(request)
                log(f"Eliminó la solcitud de pago: {soli}", request, 'del')
                res_js = {'error': False }
            except Exception as ex:
                transaction.set_rollback(True)
                msg_err = f"{ex} ({sys.exc_info()[-1].tb_lineno})"
                res_js = {'error': True, 'message':msg_err}
            return JsonResponse(res_js)

        elif action == 'generarinforme':
            try:
                id = request.POST.get('id', None)
                soli = SolicitudPago.objects.get(status=True, id=int(encrypt(id)))
                requisito = RequisitoSolicitudPago.objects.filter(status=True, solicitud=soli, requisito_id=14).order_by('-id').first()
                historial = HistorialProcesoSolicitud.objects.filter(status=True, persona_ejecucion=persona, requisito=requisito).order_by('-id').first()
                data['fini'], data['ffin'] = soli.fechainicio, soli.fechaifin
                data['contrato'] = contrato = soli.contrato
                data['carreras'] = ContratoCarrera.objects.filter(contrato=contrato, status=True)
                data['areasprogramas'] = ContratoAreaPrograma.objects.filter(contrato=contrato, status=True)
                data['periodos'] = inf = InformeMensualDocente.objects.filter(status=True,solicitudinformepago__solicitud=soli)
                data['criterios'] = detalles = DetalleDistributivo.objects.filter(status=True, distributivo_id__in=inf.values_list('distributivo_id', flat=True)).annotate(hrs_total=Sum('horas')).distinct()
                data['resmuen_criterios'] = HorasInformeMensualDocente.objects.filter(status=True,
                                                                                      informe__in=inf.values_list('id',
                                                                                                                  flat=True)) \
                    .values_list("criteriodocenciaperiodo__criterio__id", "criteriodocenciaperiodo__criterio__nombre") \
                    .annotate(hpm_total=Sum('hpm'), hem_total=Sum('hem'), pcm_total=ExpressionWrapper(
                    F('hem_total') * 100.0 / F('hpm_total'),
                    output_field=DecimalField(max_digits=5, decimal_places=2)
                ), ).order_by('criteriodocenciaperiodo__criterio__id').distinct()
                data['resumen_total'] = horas =  HorasInformeMensualDocente.objects.filter(status=True, informe__in=inf.values_list('id', flat=True)) \
                    .aggregate(hpm_total=Sum('hpm'), hem_total=Sum('hem'))
                data['porcentaje_resumentotal'] = (horas['hem_total']/horas['hpm_total'])*100
                titulaciones = persona.mis_titulaciones()
                data['titulaciones'] = titulaciones = titulaciones.filter(titulo__nivel_id__in=[3, 4])
                nombresinciales = ''
                nombre = persona.nombres.split()
                if len(nombre) > 1:
                    nombresiniciales = '{}{}'.format(nombre[0][0], nombre[1][0])
                else:
                    nombresiniciales = '{}'.format(nombre[0][0])
                inicialespersona = '{}{}{}'.format(nombresiniciales, persona.apellido1[0], persona.apellido2[0])
                name_file = f'informe_profesor_actividad_diaria_{inicialespersona.lower()}_{soli.numero}.pdf'

                resp = conviert_html_to_pdf_name_bitacora(
                    'pro_informepago/informe_consolidadopdf.html',
                    {"data": data}, name_file)
                if resp[0]:
                    resp[1].seek(0)
                    fil_content = resp[1].read()
                    resp = ContentFile(fil_content)
                else:
                    return resp[1]
                historial.archivo.save(f'{name_file.replace(".pdf", "")}.pdf', resp)
                historial.save(request)
                res_js = {'error': False }
            except Exception as ex:
                transaction.set_rollback(True)
                msg_err = f"{ex} ({sys.exc_info()[-1].tb_lineno})"
                res_js = {'error': True, 'message': msg_err}
            return JsonResponse(res_js)

        elif action == 'informe-administrativo-posgrado':
            try:
                data['hoy'] = hoy = datetime.now()
                id = request.POST.get('contrato_posgrado', None)
                certificado = request.FILES["firma"]
                contrasenaCertificado = request.POST['palabraclave']
                extension_certificado = os.path.splitext(certificado.name)[1][1:]
                bytes_certificado = certificado.read()

                reg = HistorialProcesoSolicitud.objects.get(status=True, id=int(encrypt(id)))
                requi = reg.requisito
                if HistorialProcesoSolicitud.objects.filter(status=True, persona_ejecucion=persona,
                                                            requisito=reg.requisito):
                    hist_ = HistorialProcesoSolicitud.objects.filter(status=True, persona_ejecucion=persona,
                                                                     requisito=reg.requisito).order_by('-id').first()
                    hist_.fecha_ejecucion = hoy
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

                #INFORMES MENSUALES GENERADOS POR EL DOCETE INVITADO
                informes = hist_.requisito.solicitud.load_info_monthly()
                for inf in informes:
                    informe = inf.informe
                    hist_inf = HistorialInforme(
                        informe=informe,
                        personafirmas=persona,
                        estado=2,
                        fechafirma=hoy.date(),
                    )
                    hist_inf.save(request)
                    x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(reg.archivo.url, palabras)
                    datau = JavaFirmaEc(
                        archivo_a_firmar=reg.archivo, archivo_certificado=bytes_certificado,
                        extension_certificado=extension_certificado,
                        password_certificado=contrasenaCertificado,
                        page=int(numpaginafirma), reason='', lx=x + 50, ly=y + 20
                    ).sign_and_get_content_bytes()
                    documento_a_firmar = io.BytesIO()
                    documento_a_firmar.write(datau)
                    documento_a_firmar.seek(0)
                    hist_inf.archivo.save(f'{reg.archivo.name.split("/")[-1].replace(".pdf", "")}_firmado.pdf',
                                 ContentFile(documento_a_firmar.read()))
                    informe.estado=2
                    informe.save(request)
                    time.sleep(1)

                x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(reg.archivo.url, palabras)
                datau = JavaFirmaEc(
                    archivo_a_firmar=reg.archivo, archivo_certificado=bytes_certificado,
                    extension_certificado=extension_certificado,
                    password_certificado=contrasenaCertificado,
                    page=int(numpaginafirma), reason='', lx=x + 50, ly=y + 20
                ).sign_and_get_content_bytes()
                documento_a_firmar = io.BytesIO()
                documento_a_firmar.write(datau)
                documento_a_firmar.seek(0)
                hist_.archivo.save(f'{reg.archivo.name.split("/")[-1].replace(".pdf", "")}_firmado.pdf',
                                   ContentFile(documento_a_firmar.read()))
                time.sleep(3)
                requi.estado = 0
                requi.save(request)
                persona_notificacion = None
                redirect_mod = f'/adm_solicitudpago'
                estado_solicitud = 6
                requisito = hist_.requisito
                solicitud = requisito.solicitud
                contrato = solicitud.contrato
                if contrato.validadorgp:
                    persona_notificacion = contrato.validadorgp
                    redirect_mod = f'/adm_solicitudpago?action=viewinformesmen'
                    estado_solicitud = 3
                else:
                    persona_notificacion = contrato.gestion.responsable
                solicitud.estado = estado_solicitud
                solicitud.save(request)
                cuerpo = f"Informe mensual de posgrado generado y firmado por {persona}"
                obshisto = HistorialObseracionSolicitudPago(
                    solicitud=solicitud,
                    observacion=cuerpo,
                    persona=persona,
                    estado=estado_solicitud,
                    fecha=hoy
                )
                obshisto.save(request)
                notificacion(
                    "Solicitud de pago de %s para validación del informe mensual de posgrado" % hist_.requisito.solicitud.contrato.persona,
                    cuerpo, persona_notificacion, None, redirect_mod,
                    hist_.id,
                    1, 'sga', hist_, request)
                log(f'Firmo el informe mensual de la solicitud: {solicitud}',request,'change')
                res_json = {"result": False}
            except Exception as ex:
                err_ = f"Ocurrio un error: {ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}"
                transaction.set_rollback(True)
                res_json = {"result": True, "mensaje": err_}
            return JsonResponse(res_json)

        return JsonResponse({'result':False,'message':'Ocurrio un error al buscar la acción realizada'})

    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addsolicitudinfoconsolidado':
                try:
                    id = request.GET.get('id', None)
                    if not id: raise NameError("No hay un contrato de posgrado vigente")
                    data['contrato'] = contrato = ContratoDip.objects.get(id=int(encrypt(id)), status=True)
                    form = SolicitudInformePagoForm()
                    data['seccionado'] = True
                    data['form'] = form
                    template = get_template('pro_informepago/modal/addsolicitud.html')
                    res_js = {'result':True, 'data': template.render(data)}
                except Exception as ex:
                    msg_err = f"{ex} ({sys.exc_info()[-1].tb_lineno})"
                    res_js = {'result': False,'message':msg_err}
                return JsonResponse(res_js)

            elif action == 'loadinformes':
                try:
                    fini = request.GET.get('fini', None)
                    ffin = request.GET.get('ffin', None)
                    fi, ff = convertir_fecha_hora_invertida(fini + " 00:01"), convertir_fecha_hora_invertida(ffin + " 23:59")
                    filtro = Q(status=True, fechainicio=fi.date(), fechafin=ff.date(),distributivo__profesor=profesor, distributivo__periodo__tipo__id__in=[3, 4])
                    informes = InformeMensualDocente.objects.filter(filtro).exclude(solicitudinformepago__informe_id=F('id'), solicitudinformepago__solicitud__status=True).distinct().order_by('id')
                    estructura = [{
                        'periodo':f"{inf.distributivo.periodo}<br>INFORME DE EVIDENCIA CORRESPONDIENTE A: { nombremes(inf.fechafin).upper() } { inf.fechafin.strftime('%Y')}",
                        'file':inf.archivo.url,'pk':encrypt(inf.id),
                        'fechainicio':inf.fechainicio,'fechafin':inf.fechafin,
                        'promedio':inf.promedio,
                        'criterios_hora':[
                            {
                                'id':encrypt(det.pk),
                                'criterio': str(det.criteriodocenciaperiodo.criterio),
                                'horas':det.horas
                            } for det in DetalleDistributivo.objects.filter(status=True, distributivo=inf.distributivo)
                        ],
                        'total_horas': DetalleDistributivo.objects.filter(status=True, distributivo=inf.distributivo).aggregate(total_horas = Sum('horas'))['total_horas']
                    } for inf in informes]
                    res_js = {'result':True, 'list':estructura}
                except Exception as ex:
                    msg_err = f"{ex} ({sys.exc_info()[-1].tb_lineno})"
                    res_js = {'result':False, 'message':msg_err}
                return JsonResponse(res_js)
        else:
            try:
                data['title'] = u'Solicitud de pago'
                data['docente'] = Profesor.objects.get(pk=profesor.id)
                hoy = datetime.now()
                search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
                data['contrato'] = contrato = ContratoDip.objects.filter(status=True, persona=persona, fechainicio__lte=hoy.date(), fechafin__gte=hoy.date(),estado=2).order_by('-id').first()
                data['versioninfo'] = hoy.strftime('%Y%m%d_%H%M%S')
                data['eliminartodo'] = variable_valor('ELIMINAR_INFORMES_FIRMADOS')
                data['listadoinformes'] = InformeMensualDocente.objects.filter(distributivo__profesor=profesor, distributivo__periodo__tipo__id__in=[3,4], status=True).order_by('id')
                listado = SolicitudPago.objects.filter(filtro).filter(contrato__persona=persona).order_by('-id')

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
                return render(request, "pro_informepago/view.html", data)
            except Exception as ex:
                msg_err = f"{ex} ({sys.exc_info()[-1].tb_lineno})"
                return HttpResponseRedirect(f'/?info={msg_err}')