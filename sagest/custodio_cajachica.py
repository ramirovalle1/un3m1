# -*- coding: UTF-8 -*-
import json
from datetime import datetime, timedelta
from _decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max
from django.db.models import Q
from django.template.context import Context
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from decorators import secure_module
from django.forms import model_to_dict

from sagest.commonviews import anio_ejercicio
from sagest.forms import PartidaCajaChica, SolicitudCajaChicaForm, ComprobanteCajaChicaForm, \
    ComprobanteCajaChicaLiquidacionForm, ReposicionCajaChicaForm
from sagest.models import null_to_numeric, SolicitudCajaChica, PartidaCajaChica, CajaChica,ComprobanteCajaChica, ComprobanteCajaChicaLiquidacion, \
    null_to_decimal,SolicitudReposicionCajaChica, SolicitudReposicionCajaChicaAprobacion

from settings import EMAIL_DOMAIN, PUESTO_ACTIVO_ID
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, convertir_fecha, generar_nombre, formato12h,numero_a_letras,fecha_letra_formato_fecha
from sga.models import miinstitucion, CUENTAS_CORREOS
from sga.tasks import send_html_mail, conectar_cuenta
from sga.funcionesxhtml2pdf import conviert_html_to_pdf


@login_required(redirect_field_name='ret', login_url='/loginsagest')
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    if CajaChica.objects.filter(status=True, custodio=persona).exists():
        data['cajachica']=cajachica = CajaChica.objects.filter(status=True, custodio=persona)[0]
    else:
        return HttpResponseRedirect("/?info=Ud. no es custodio de caja chica.")
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addsolicitud':
            try:
                f = SolicitudCajaChicaForm(request.POST, request.FILES)
                if f.is_valid():
                    if f.cleaned_data['valor']>cajachica.valor:
                        return JsonResponse({"result": "bad", "mensaje": u"Lo sentimos su valor máximo a solicitar es de %s" % cajachica.valormaximo})
                    secuenciautilizada=SolicitudCajaChica.objects.values_list("secuencia",flat=True).filter(status=True)
                    if not SolicitudCajaChica.objects.filter(status=False).exclude(secuencia__in=secuenciautilizada).exists():
                        secuencia=null_to_numeric(SolicitudCajaChica.objects.filter(status=True).aggregate(secu=Max("secuencia"))['secu'])+1
                    else:
                        secuencia = null_to_numeric(SolicitudCajaChica.objects.filter(status=False).exclude(secuencia__in=secuenciautilizada).aggregate(secu=Max("secuencia"))['secu'])
                    solicitud = SolicitudCajaChica(secuencia=secuencia,
                                                   solicita=persona,
                                                   partidacajachica=f.cleaned_data['partidacajachica'],
                                                   fechasolicitud=datetime.now().date(),
                                                   valor=f.cleaned_data['valor'],
                                                   concepto=f.cleaned_data['concepto'],
                                                   estadosolicitud=1)
                    solicitud.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'exportarcomprobante':
            try:
                data['comprobante'] = comprobante = ComprobanteCajaChica.objects.get(pk=int(request.POST['id']))
                data['valorenletra'] = valorenletra= numero_a_letras(comprobante.valor)
                data['fechaenletra'] = fechaenletra= fecha_letra_formato_fecha(str(comprobante.fechasolicitud))
                return conviert_html_to_pdf('custodio_cajachica/exportarcomprobante.html',
                                            {'pagesize': 'A4',
                                             'comprobante': comprobante,
                                             'valorenletra': valorenletra,
                                             'fechaenletra': fechaenletra})
            except Exception as ex:
                pass

        elif action == 'editsolicitud':
            try:
                solicitud = SolicitudCajaChica.objects.get(pk=request.POST['id'])
                f = SolicitudCajaChicaForm(request.POST)
                if f.is_valid():
                    solicitud.valor = f.cleaned_data['valor']
                    solicitud.concepto = f.cleaned_data['concepto']
                    solicitud.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delesolicitud':
            try:
                solicitud = SolicitudCajaChica.objects.get(pk=int(request.POST['id']))
                solicitud.status = False
                solicitud.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'verdetalle':
            try:
                data = {}
                data['solicitud'] = solicitud = SolicitudCajaChica.objects.get(pk=int(request.POST['id']))
                data['aprobadores'] = solicitud.solicitudcajachicaaprobacion_set.filter(status=True)
                template = get_template("aprobar_cajachica/detalle.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'addreposicion':
            try:
                f = ReposicionCajaChicaForm(request.POST)
                if f.is_valid():
                    secuenciautilizada = SolicitudReposicionCajaChica.objects.values_list("secuencia", flat=True).filter(status=True)
                    if not SolicitudReposicionCajaChica.objects.filter(status=False).exclude(secuencia__in=secuenciautilizada).exists():
                        secuencia = null_to_numeric(SolicitudReposicionCajaChica.objects.filter(status=True).aggregate(secu=Max("secuencia"))['secu']) + 1
                    else:
                        secuencia = null_to_numeric(SolicitudReposicionCajaChica.objects.filter(status=False).exclude(secuencia__in=secuenciautilizada).aggregate(secu=Max("secuencia"))['secu'])
                    solicitud = SolicitudReposicionCajaChica(secuencia=secuencia,
                                                             solicitudcajachica=f.cleaned_data['solicitudcajachica'],
                                                             cajachica=cajachica,
                                                             estadosolicitud=1)
                    solicitud.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delereposicion':
            try:
                solicitud = SolicitudReposicionCajaChica.objects.get(pk=int(request.POST['id']))
                solicitud.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addcomprobante':
            try:
                f = ComprobanteCajaChicaForm(request.POST, request.FILES)
                if f.is_valid():
                    solicitudreposicion=SolicitudReposicionCajaChica.objects.get(id=int(request.POST['idsol']))
                    valoraprobado=cajachica.valoraprobado()
                    valorliquidado=cajachica.valorliquidado()
                    if valorliquidado>valoraprobado:
                        return JsonResponse({"result": "bad","mensaje": u"Lo sentimos su valor máximo a solicitar es de %s" % cajachica.valoraprobado()})
                    secuenciautilizada = ComprobanteCajaChica.objects.values_list("secuencia", flat=True).filter(status=True)
                    if not ComprobanteCajaChica.objects.filter(status=False).exclude(secuencia__in=secuenciautilizada).exists():
                        secuencia = null_to_numeric(ComprobanteCajaChica.objects.filter(status=True).aggregate(secu=Max("secuencia"))['secu']) + 1
                    else:
                        secuencia = null_to_numeric(ComprobanteCajaChica.objects.filter(status=False).exclude(secuencia__in=secuenciautilizada).aggregate(secu=Max("secuencia"))['secu'])
                    comprobante = ComprobanteCajaChica(secuencia=secuencia,
                                                     solicitudreposicion=solicitudreposicion,
                                                     fechasolicitud=datetime.now().date(),
                                                     valor=f.cleaned_data['valor'],
                                                     concepto=f.cleaned_data['concepto'],
                                                     estadocomprobante=1)
                    comprobante.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcomprobante':
            try:
                comprobante = ComprobanteCajaChica.objects.get(pk=request.POST['id'])
                f = ComprobanteCajaChicaForm(request.POST)
                if f.is_valid():
                    comprobante.valor = f.cleaned_data['valor']
                    comprobante.concepto = f.cleaned_data['concepto']
                    comprobante.save(request)

                    partida = PartidaCajaChica.objects.filter(status=True, cajachica=cajachica)[0]
                    partida.valorcomprometido = partida.valorcomprometido + comprobante.valor if partida.valorcomprometido else comprobante.valor
                    partida.save()

                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delecomprobante':
            try:
                comprobante = ComprobanteCajaChica.objects.get(pk=int(request.POST['id']))
                comprobante.status=False
                comprobante.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'verdetallecomprobante':
            try:
                data = {}
                data['comprobante'] = comprobante = ComprobanteCajaChica.objects.get(pk=int(request.POST['id']))
                data['aprobadores'] = comprobante.comprobantecajachicaaprobacion_set.filter(status=True)
                data['valorenletra']=numero_a_letras(comprobante.valor)
                data['fechaenletra']=fecha_letra_formato_fecha(str(comprobante.fechasolicitud))
                template = get_template("custodio_cajachica/detallecomprobante.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'addliquidacion':
            try:
                f = ComprobanteCajaChicaLiquidacionForm(request.POST, request.FILES)
                if f.is_valid():
                    if ComprobanteCajaChicaLiquidacion.objects.filter(status=True, numeroretencion=f.cleaned_data['numeroretencion']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Número de retención ya existe."})
                    comprobante = ComprobanteCajaChica.objects.get(pk=request.POST['idc'])
                    liquidacion = ComprobanteCajaChicaLiquidacion(comprobante=comprobante,
                                                                  numeroretencion=f.cleaned_data['numeroretencion'] ,
                                                                  numerofactura=f.cleaned_data['numerofactura'],
                                                                  fecha=f.cleaned_data['fecha'],
                                                                  base0=f.cleaned_data['base0'],
                                                                  baseiva=f.cleaned_data['baseiva'],
                                                                  ivacausado=f.cleaned_data['ivacausado'],
                                                                  ivaretenido=f.cleaned_data['ivaretenido'],
                                                                  impuestoretenido=f.cleaned_data['impuestoretenido'],
                                                                  total=f.cleaned_data['total'],
                                                                  observacion=f.cleaned_data['observacion'])
                    liquidacion.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editliquidacion':
            try:
                comprobante = ComprobanteCajaChica.objects.get(pk=request.POST['idc'])
                liquidacion = ComprobanteCajaChicaLiquidacion.objects.get(pk=request.POST['id'])
                f = ComprobanteCajaChicaLiquidacionForm(request.POST)
                if f.is_valid():
                    liquidacion.numeroretencion = f.cleaned_data['numeroretencion']
                    liquidacion.numerofactura = f.cleaned_data['numerofactura']
                    liquidacion.fecha = f.cleaned_data['fecha']
                    liquidacion.base0 = f.cleaned_data['base0']
                    liquidacion.baseiva = f.cleaned_data['baseiva']
                    liquidacion.ivacausado = f.cleaned_data['ivacausado']
                    liquidacion.ivaretenido = f.cleaned_data['ivaretenido']
                    liquidacion.impuestoretenido = f.cleaned_data['impuestoretenido']
                    liquidacion.total = f.cleaned_data['total']
                    liquidacion.observacion = f.cleaned_data['observacion']
                    liquidacion.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleliquidacion':
            try:
                liquidacion = ComprobanteCajaChicaLiquidacion.objects.get(pk=request.POST['id'])
                liquidacion.status=False
                liquidacion.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'liquidar':
            try:
                comprobante = ComprobanteCajaChica.objects.get(pk=request.POST['id'])
                data['valorcumplido'] = valorcumplido = comprobante.validarcumplimientovalor()
                if valorcumplido !=0 and valorcumplido != comprobante.valor:
                    comprobante.valor = valorcumplido
                comprobante.estadocomprobante=2
                comprobante.save(request)
                solicitudaprobada= SolicitudCajaChica.objects.filter(status=True, id=comprobante.solicitudreposicion.solicitudcajachica.id)[0]
                partida = PartidaCajaChica.objects.filter(status=True, id=comprobante.solicitudreposicion.solicitudcajachica.partidacajachica.id)[0]
                partida.valorcomprometido = partida.valorcomprometido + comprobante.valor if partida.valorcomprometido else comprobante.valor
                partida.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'cambiarestadoreposicion':
            try:
                valorefectivo = null_to_decimal(request.POST['valorefectivo'],2)
                solicitud = SolicitudReposicionCajaChica.objects.get(status=True,id=request.POST['id'])
                solicitud.valorreembolzar=solicitud.resumencomprobante()
                solicitud.valorefectivo=valorefectivo
                solicitud.fechasolicitud=datetime.now().date()
                solicitud.estadosolicitud=2
                solicitud.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addsolicitud':
                try:
                    data['title'] = u'Solicitar'
                    form = SolicitudCajaChicaForm()
                    form.addcustodio(persona)
                    data['form'] = form
                    data['cajachica']= CajaChica.objects.filter(status=True, custodio=persona)[0]
                    return render(request, "custodio_cajachica/addsolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'editsolicitud':
                try:
                    data['title'] = u'Editar solicitud'
                    data['solicitud']=solicitud=SolicitudCajaChica.objects.get(id=request.GET['id'])
                    initial = model_to_dict(solicitud)
                    form= SolicitudCajaChicaForm(initial=initial)
                    form.addcustodio(solicitud.solicita)
                    data['form'] =form
                    return render(request, "custodio_cajachica/editsolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'delesolicitud':
                try:
                    data['title'] = u'Eliminar solicitud'
                    data['solicitud'] = SolicitudCajaChica.objects.get(pk=int(request.GET['id']))
                    return render(request, "custodio_cajachica/delesolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'solicitudesreposicion':
                try:
                    data['title'] = u'Solicitudes de Consumo'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        reposicion = SolicitudReposicionCajaChica.objects.filter(status=True, cajachica=cajachica).filter(
                            Q(secuencia__contains=search) |
                            Q(cajachica_custodio__cedula__icontains=search) |
                            Q(cajachica_custodio__pasaporte__icontains=search)|
                            Q(cajachica_custodio__nombres__icontains=search) |
                            Q(cajachica_custodio__apellido1__icontains=search) |
                            Q(cajachica_custodio__apellido2__icontains=search)
                        ).distinct()
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        reposicion = SolicitudReposicionCajaChica.objects.filter(id=ids, cajachica=cajachica)
                    else:
                        reposicion = SolicitudReposicionCajaChica.objects.filter(status=True, cajachica=cajachica)
                    paging = MiPaginador(reposicion, 20)
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
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['solictudes'] = page.object_list
                    return render(request, 'custodio_cajachica/solicitudesreposicion.html', data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addreposicion':
                try:
                    data['title'] = u'Generar'
                    form = ReposicionCajaChicaForm()
                    form.porcustodio()
                    data['form'] = form
                    return render(request, "custodio_cajachica/addreposicion.html", data)
                except Exception as ex:
                    pass

            elif action == 'delereposicion':
                try:
                    data['title'] = u'Eliminar reposición'
                    data['reposicion'] = SolicitudReposicionCajaChica.objects.get(pk=int(request.GET['id']))
                    return render(request, "custodio_cajachica/delereposicion.html", data)
                except Exception as ex:
                    pass

            elif action == 'comprobantes':
                try:
                    data['title'] = u'Comprobantes de caja chica'
                    search = None
                    ids = None
                    data['idsol']=reposicion=int(request.GET['idsol'])
                    data['solicitud']=SolicitudReposicionCajaChica.objects.get(id=reposicion)
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        comprobante = ComprobanteCajaChica.objects.filter(status=True,solicitudreposicion=reposicion ).filter(
                            Q(concepto__contains=search) |
                            Q(solicita__cedula__icontains=search) |
                            Q(solicita__pasaporte__icontains=search)|
                            Q(solicita__nombres__icontains=search) |
                            Q(solicita__apellido1__icontains=search) |
                            Q(solicita__apellido2__icontains=search)
                        ).distinct()
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        comprobante = ComprobanteCajaChica.objects.filter(id=ids, solicitudreposicion=reposicion)
                    else:
                        comprobante = ComprobanteCajaChica.objects.filter(status=True, solicitudreposicion=reposicion)
                    paging = MiPaginador(comprobante, 20)
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
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['comprobantes'] = page.object_list
                    return render(request, 'custodio_cajachica/comprobantes.html', data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addcomprobante':
                try:
                    data['title'] = u'Añadir comprobante'
                    data['idsol'] = reposicion = int(request.GET['idsol'])
                    form = ComprobanteCajaChicaForm()
                    data['cajachica'] = caja=CajaChica.objects.filter(custodio=persona)[0]
                    # data['porcentaje']=porcentaje= null_to_decimal(Decimal(caja.valormaximo) * Decimal(0.3),2)
                    form.addcustodio(caja.valormaximo)
                    data['form'] = form
                    return render(request, "custodio_cajachica/addcomprobante.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcomprobante':
                try:
                    data['title'] = u'Editar comprobante'
                    data['idsol'] = reposicion = int(request.GET['idsol'])
                    data['id'] = id = int(request.GET['id'])
                    data['comprobante']=comprobante=ComprobanteCajaChica.objects.get(id=int(id))
                    initial = model_to_dict(comprobante)
                    form= ComprobanteCajaChicaForm(initial=initial)
                    form.editcustodio()
                    data['form'] =form
                    data['valorinicial']=comprobante.valor
                    # data['valormaximo']=porcentaje= null_to_decimal(Decimal(comprobante.cajachica.valormaximo) * Decimal(0.3),2)
                    data['valormaximo']=comprobante.solicitudreposicion.cajachica.valormaximo
                    return render(request, "custodio_cajachica/editcomprobante.html", data)
                except Exception as ex:
                    pass

            elif action == 'delecomprobante':
                try:
                    data['title'] = u'Eliminar comprobante'
                    data['idsol'] = reposicion = int(request.GET['idsol'])
                    data['comprobante'] = ComprobanteCajaChica.objects.get(pk=int(request.GET['id']))
                    return render(request, "custodio_cajachica/delecomprobante.html", data)
                except Exception as ex:
                    pass

            elif action == 'liquidaciones':
                try:
                    data['title'] = u'Liquidaciones de comprobante '
                    idc=int(request.GET['id'])
                    data['idsol']=int(request.GET['idsol'])
                    search = None
                    ids = None
                    data['comprobante']=comprobante=ComprobanteCajaChica.objects.get(id=idc)
                    data['valorcumplido']=valorcumplido = comprobante.validarcumplimientovalor()
                    liquidaciones=comprobante.comprobantecajachicaliquidacion_set.filter(status=True)
                    paging = MiPaginador(liquidaciones, 20)
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
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['liquidaciones'] = page.object_list
                    return render(request, 'custodio_cajachica/liquidaciones.html', data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addliquidacion':
                try:
                    data['title'] = u'Añadir liquidación'
                    idc = int(request.GET['idc'])
                    data['idsol'] = int(request.GET['idsol'])
                    data['comprobante']=comprobante = ComprobanteCajaChica.objects.get(id=idc)
                    data['valorcumplido']=valorcumplido=comprobante.validarcumplimientovalor()
                    form = ComprobanteCajaChicaLiquidacionForm()
                    form.add(comprobante,valorcumplido)
                    data['form'] = form
                    return render(request, "custodio_cajachica/addliquidacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'editliquidacion':
                try:
                    data['title'] = u'Editar liquidación'
                    idc=int(request.GET['idc'])
                    data['idsol'] = int(request.GET['idsol'])
                    data['comprobante'] = comprobante = ComprobanteCajaChica.objects.get(id=idc)
                    data['liquidacion']=liquidacion = ComprobanteCajaChicaLiquidacion.objects.get(pk=request.GET['id'])
                    data['comprobante'] = comprobante = ComprobanteCajaChica.objects.get(id=idc)
                    data['valorcumplido'] = valorcumplido = comprobante.validarcumplimientovalor()
                    initial = model_to_dict(liquidacion)
                    form= ComprobanteCajaChicaLiquidacionForm(initial=initial)
                    form.add(comprobante, valorcumplido)
                    data['form'] =form
                    return render(request, "custodio_cajachica/editliquidacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleliquidacion':
                try:
                    data['title'] = u'Eliminar liquidación'
                    data['idsol'] = int(request.GET['idsol'])
                    data['comprobante'] = ComprobanteCajaChica.objects.get(pk=int(request.GET['idc']))
                    data['liquidacion'] = ComprobanteCajaChicaLiquidacion.objects.get(pk=int(request.GET['id']))
                    return render(request, "custodio_cajachica/deleliquidacion.html", data)
                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Solicitud de caja chica.'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
            if search:
                solicitud = SolicitudCajaChica.objects.filter(status=True).filter(
                    Q(concepto__contains=search) |
                    Q(solicita__cedula__icontains=search) |
                    Q(solicita__pasaporte__icontains=search) |
                    Q(solicita__nombres__icontains=search) |
                    Q(solicita__apellido1__icontains=search) |
                    Q(solicita__apellido2__icontains=search) , solicita=persona).distinct().order_by('-fechasolicitud', '-secuencia')
            elif 'id' in request.GET:
                ids = request.GET['id']
                solicitud = SolicitudCajaChica.objects.filter(id=ids, solicita=persona)
            else:
                solicitud = SolicitudCajaChica.objects.filter(status=True, solicita=persona).order_by('-fechasolicitud', '-secuencia')
            paging = MiPaginador(solicitud, 20)
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
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['solicitudescaja'] = page.object_list
            return render(request, 'custodio_cajachica/view.html', data)

