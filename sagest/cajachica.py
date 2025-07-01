# -*- coding: UTF-8 -*-
import json
from datetime import datetime, timedelta
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
from sagest.forms import CajaChicaForm, PartidaCajaChicaForm, SolicitudCajaChicaForm, ComprobanteCajaChicaForm,ReposicionCajaChicaForm, ComprobanteCajaChicaLiquidacionForm
from sagest.models import  null_to_numeric, SolicitudCajaChica, PartidaCajaChica, CajaChica,SolicitudCajaChicaAprobacion,\
    ComprobanteCajaChica,SolicitudReposicionCajaChica, ComprobanteCajaChicaLiquidacion, SolicitudReposicionCajaChicaAprobacion

from settings import EMAIL_DOMAIN, PUESTO_ACTIVO_ID
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, convertir_fecha, generar_nombre,numero_a_letras,fecha_letra_formato_fecha, null_to_decimal
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
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addcajachica':
            try:
                f = CajaChicaForm(request.POST, request.FILES)
                if f.is_valid():
                    cajachica = CajaChica(descripcion=f.cleaned_data['descripcion'],
                                          valor=f.cleaned_data['valor'],
                                          valormaximo=f.cleaned_data['valormaximo'],
                                          custodio_id=f.cleaned_data['custodio'],
                                          verificador_id=f.cleaned_data['verificador'],
                                          departamento=f.cleaned_data['departamento'])
                    cajachica.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcajachica':
            try:
                ingreso = CajaChica.objects.get(pk=request.POST['id'])
                f = CajaChicaForm(request.POST)
                if f.is_valid():
                    ingreso.descripcion = f.cleaned_data['descripcion']
                    ingreso.valormaximo = f.cleaned_data['valormaximo']
                    ingreso.custodio_id = f.cleaned_data['custodio']
                    ingreso.verificador_id = f.cleaned_data['verificador']
                    ingreso.departamento=f.cleaned_data['departamento']
                    ingreso.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delecajachica':
            try:
                ingreso = CajaChica.objects.get(pk=int(request.POST['id']))
                ingreso.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addconfiguracion':
            try:
                f = PartidaCajaChicaForm(request.POST, request.FILES)
                if f.is_valid():
                    anio = anio_ejercicio()
                    configuracion = PartidaCajaChica(cajachica=f.cleaned_data['cajachica'],
                                                     partida=f.cleaned_data['partida'],
                                                     valorinicial=f.cleaned_data['valorinicial'],
                                                     valorsaldo=f.cleaned_data['valorinicial'],
                                                     anioejercicio=anio)
                    configuracion.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editconfiguracion':
            try:
                configuracion = PartidaCajaChica.objects.get(pk=request.POST['id'])
                f = PartidaCajaChicaForm(request.POST)
                if f.is_valid():
                    configuracion.cajachica = f.cleaned_data['cajachica']
                    configuracion.partida = f.cleaned_data['partida']
                    configuracion.valorinicial = f.cleaned_data['valorinicial']
                    configuracion.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleconfiguracion':
            try:
                configuracion = PartidaCajaChica.objects.get(pk=int(request.POST['id']))
                configuracion.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addsolicitud':
            try:
                f = SolicitudCajaChicaForm(request.POST, request.FILES)
                if f.is_valid():
                    secuenciautilizada = SolicitudCajaChica.objects.values_list("secuencia", flat=True).filter(status=True)
                    if not SolicitudCajaChica.objects.filter(status=False).exclude(secuencia__in=secuenciautilizada).exists():
                        secuencia = null_to_numeric(SolicitudCajaChica.objects.filter(status=True).aggregate(secu=Max("secuencia"))['secu']) + 1
                    else:
                        secuencia = null_to_numeric(SolicitudCajaChica.objects.filter(status=False).exclude(secuencia__in=secuenciautilizada).aggregate(secu=Max("secuencia"))['secu'])
                    solicitud = SolicitudCajaChica(secuencia=secuencia,
                                                   solicita=f.cleaned_data['solicita'].custodio,
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
                solicitud.status=False
                solicitud.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'obtenerpartida':
            try:
                cajachica = CajaChica.objects.get(pk=request.POST['id'])
                partidas=PartidaCajaChica.objects.filter(cajachica=cajachica)
                lista = []
                for partida in partidas:
                    lista.append([partida.id, partida.nombrecompleto()])
                return JsonResponse({'result': 'ok', 'lista': lista, 'valor':cajachica.valor})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'addaprobacion':
            try:
                solicitud = SolicitudCajaChica.objects.get(pk=request.POST['id'])
                esta=int(request.POST['esta'])
                if solicitud.partidacajachica.valorsaldo<=0:
                    return JsonResponse({"result": "bad", "mensaje": u"Lo sentimos ya no tiene saldo"})
                aprobar = SolicitudCajaChicaAprobacion(solicitud=solicitud,
                                                       fechaaprobacion=datetime.now().date(),
                                                       observacion=request.POST['obse'],
                                                       aprueba=persona,
                                                       estadosolicitud=esta)
                aprobar.save(request)
                solicitud.actulizar_estado(request)
                # solicitud.partidacajachica.valorcomprometido = 0
                if esta == 1:
                    solicitud.partidacajachica.valordescontado = solicitud.partidacajachica.valordescontado+solicitud.valor if solicitud.partidacajachica.valordescontado else solicitud.valor
                    solicitud.partidacajachica.valorsaldo = solicitud.partidacajachica.valorsaldo - solicitud.valor if solicitud.partidacajachica.valorsaldo else solicitud.valor
                    solicitud.partidacajachica.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'obtenervalorcaja':
            try:
                cajachica = CajaChica.objects.get(pk=request.POST['id'])
                return JsonResponse({'result': 'ok', 'valor': cajachica.valormaximo})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'addcomprobante':
            try:
                f = ComprobanteCajaChicaForm(request.POST, request.FILES)
                if f.is_valid():
                    solicitudreposicion=SolicitudReposicionCajaChica.objects.get(id=int(request.POST['idsol']))
                    valoraprobado=f.cleaned_data['cajachica'].valoraprobado()
                    valorliquidado=f.cleaned_data['cajachica'].valorliquidado()
                    if valorliquidado>valoraprobado:
                        return JsonResponse({"result": "bad","mensaje": u"Lo sentimos su valor máximo a solicitar es de %s" % f.cleaned_data['cajachica'].valoraprobado()})
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

        elif action == 'exportarsolicitud':
            try:
                data['solicitud'] = solicitud = SolicitudReposicionCajaChica.objects.get(pk=int(request.POST['id']))
                data['comprobantes'] = comprobantes = solicitud.detallecomprobantes()
                data['valorenletra'] = valorenletra= numero_a_letras(solicitud.valortotal)
                data['fechaenletra'] = fechaenletra= fecha_letra_formato_fecha(str(datetime.now().date()))
                return conviert_html_to_pdf('custodio_cajachica/exportarsolicitud.html',
                                            {'pagesize': 'A4',
                                             'solicitud': solicitud,
                                             'valorenletra': valorenletra,
                                             'fechaenletra': fechaenletra,
                                             'comprobantes': comprobantes})
            except Exception as ex:
                pass

        elif action == 'addreposicion':
            try:
                f = ReposicionCajaChicaForm(request.POST)
                if f.is_valid():
                    secuenciautilizada = SolicitudReposicionCajaChica.objects.values_list("secuencia",flat=True).filter(status=True)
                    if not SolicitudReposicionCajaChica.objects.filter(status=False).exclude(secuencia__in=secuenciautilizada).exists():
                        secuencia = null_to_numeric(SolicitudReposicionCajaChica.objects.filter(status=True).aggregate(secu=Max("secuencia"))['secu']) + 1
                    else:
                        secuencia = null_to_numeric(SolicitudReposicionCajaChica.objects.filter(status=False).exclude(secuencia__in=secuenciautilizada).aggregate(secu=Max("secuencia"))['secu'])
                    solicitud = SolicitudReposicionCajaChica(secuencia=secuencia,
                                                             solicitudcajachica=f.cleaned_data['solicitudcajachica'],
                                                             cajachica=f.cleaned_data['cajachica'],
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

        elif action == 'addaprobacion_reposicion':
            try:
                solicitud = SolicitudReposicionCajaChica.objects.get(pk=request.POST['id'])
                esta = int(request.POST['esta'])
                if esta == 1:
                    solicitudaprobada = SolicitudCajaChica.objects.filter(status=True,id=solicitud.solicitudcajachica.id)[0]
                    partida = PartidaCajaChica.objects.filter(status=True, id=solicitud.solicitudcajachica.partidacajachica.id)[0]
                    partida.valorcomprometido=partida.valorcomprometido - solicitud.valortotal
                    partida.save()
                    solicitudaprobada.valordescontado = solicitudaprobada.valordescontado+solicitud.valortotal if solicitudaprobada.valordescontado else solicitud.valortotal
                    solicitudaprobada.valorsaldo = solicitudaprobada.valorsaldo-solicitud.valortotal if solicitudaprobada.valorsaldo else solicitud.valortotal
                    solicitudaprobada.save()
                aprobar = SolicitudReposicionCajaChicaAprobacion(solicitud=solicitud,
                                                       fechaaprobacion=datetime.now().date(),
                                                       observacion=request.POST['obse'],
                                                       aprueba=persona,
                                                       estadosolicitud=esta)
                aprobar.save(request)
                solicitud.actualizar_estado(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'cajachica':
                try:
                    data['title'] = u'Caja chica.'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        caja = CajaChica.objects.filter(status=True).filter(
                            Q(descripcion__contains=search) |
                            Q(custodio__cedula__icontains=search) |
                            Q(custodio__pasaporte__icontains=search) |
                            Q(custodio__nombres__icontains=search) |
                            Q(custodio__apellido1__icontains=search) |
                            Q(custodio__apellido2__icontains=search)).distinct()
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        caja = CajaChica.objects.filter(id=ids)
                    else:
                        caja = CajaChica.objects.filter(status=True)
                    paging = MiPaginador(caja, 20)
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
                    data['cajachica'] = page.object_list
                    return render(request, 'cajachica/cajachica.html', data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addcajachica':
                try:
                    data['title'] = u'Agregar Caja Chica'
                    form = CajaChicaForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, "cajachica/addcajachica.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcajachica':
                try:
                    data['title'] = u'Editar Caja Chica'
                    data['cajachica']=cajachica=CajaChica.objects.get(id=request.GET['id'])
                    initial = model_to_dict(cajachica)
                    form= CajaChicaForm(initial=initial)
                    form.editar(cajachica)
                    data['form'] =form
                    return render(request, "cajachica/editcajachica.html", data)
                except Exception as ex:
                    pass

            elif action == 'delecajachica':
                try:
                    data['title'] = u'Eliminar Caja chica'
                    data['cajachica'] = CajaChica.objects.get(pk=int(request.GET['id']))
                    return render(request, "cajachica/delecajachica.html", data)
                except Exception as ex:
                    pass

            elif action == 'configuracion':
                try:
                    data['title'] = u'Configuración'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        caja = PartidaCajaChica.objects.filter(status=True).filter(
                            Q(cajachica__descripcion__contains=search) | Q(partida__nombre__contains=search) | Q(partida__codigo__contains=search) |
                            Q(cajachica__custodio__cedula__icontains=search) |
                            Q(cajachica__custodio__pasaporte__icontains=search)|
                            Q(cajachica__custodio__nombres__icontains=search) |
                            Q(cajachica__custodio__apellido1__icontains=search) |
                            Q(cajachica__custodio__apellido2__icontains=search) ).distinct()
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        caja = PartidaCajaChica.objects.filter(id=ids)
                    else:
                        caja = PartidaCajaChica.objects.filter(status=True)
                    paging = MiPaginador(caja, 20)
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
                    data['configuracion'] = page.object_list
                    return render(request, 'cajachica/configuracion.html', data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addconfiguracion':
                try:
                    data['title'] = u'Configurar caja'
                    form = PartidaCajaChicaForm()
                    data['form'] = form
                    return render(request, "cajachica/addconfiguracion.html", data)
                except Exception as ex:
                    pass

            elif action == 'editconfiguracion':
                try:
                    data['title'] = u'Editar configuracion'
                    data['configuracion']=configuracion=PartidaCajaChica.objects.get(id=request.GET['id'])
                    initial = model_to_dict(configuracion)
                    form= PartidaCajaChicaForm(initial=initial)
                    data['form'] =form
                    return render(request, "cajachica/editconfiguracion.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleconfiguracion':
                try:
                    data['title'] = u'Eliminar configuración'
                    data['configuracion'] = PartidaCajaChica.objects.get(pk=int(request.GET['id']))
                    return render(request, "cajachica/deleconfiguracion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addsolicitud':
                try:
                    data['title'] = u'Solicitar'
                    form = SolicitudCajaChicaForm()
                    data['form'] = form
                    return render(request, "cajachica/addsolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'editsolicitud':
                try:
                    data['title'] = u'Editar solicitud'
                    data['solicitud']=solicitud=SolicitudCajaChica.objects.get(id=request.GET['id'])
                    initial = model_to_dict(solicitud)
                    form= SolicitudCajaChicaForm(initial=initial)
                    form.edit(solicitud.solicita)
                    data['valormaximo']=CajaChica.objects.filter(custodio=solicitud.solicita)[0].valormaximo
                    data['valorinicial']=solicitud.valor
                    data['form'] =form
                    return render(request, "cajachica/editsolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'delesolicitud':
                try:
                    data['title'] = u'Eliminar solicitud'
                    data['solicitud'] = SolicitudCajaChica.objects.get(pk=int(request.GET['id']))
                    return render(request, "cajachica/delesolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'detalle':
                try:
                    data = {}
                    data['solicitud'] = solicitud = SolicitudCajaChica.objects.get(pk=int(request.GET['id']))
                    data['aprobador'] = persona
                    data['fecha'] = datetime.now().date()
                    data['aprobadores'] = solicitud.solicitudcajachicaaprobacion_set.filter(status=True)
                    template = get_template("aprobar_cajachica/detalle_aprobar.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'verdetalle':
                try:
                    data = {}
                    data['solicitud'] = solicitud = SolicitudCajaChica.objects.get(pk=int(request.GET['id']))
                    data['aprobadores'] = solicitud.solicitudcajachicaaprobacion_set.filter(status=True)
                    template = get_template("aprobar_cajachica/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'solicitudesreposicion':
                try:
                    data['title'] = u'Solicitudes de Consumo'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        reposicion = SolicitudReposicionCajaChica.objects.filter(status=True).filter(
                            Q(secuencia__contains=search) |
                            Q(cajachica_custodio__cedula__icontains=search) |
                            Q(cajachica_custodio__pasaporte__icontains=search)|
                            Q(cajachica_custodio__nombres__icontains=search) |
                            Q(cajachica_custodio__apellido1__icontains=search) |
                            Q(cajachica_custodio__apellido2__icontains=search)
                        ).distinct()
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        reposicion = SolicitudReposicionCajaChica.objects.filter(id=ids)
                    else:
                        reposicion = SolicitudReposicionCajaChica.objects.filter(status=True)
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
                    return render(request, 'cajachica/solicitudesreposicion.html', data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addreposicion':
                try:
                    data['title'] = u'Generar'
                    form = ReposicionCajaChicaForm()
                    data['form'] = form
                    return render(request, "cajachica/addreposicion.html", data)
                except Exception as ex:
                    pass

            elif action == 'delereposicion':
                try:
                    data['title'] = u'Eliminar reposición'
                    data['reposicion'] = SolicitudReposicionCajaChica.objects.get(pk=int(request.GET['id']))
                    return render(request, "cajachica/delereposicion.html", data)
                except Exception as ex:
                    pass

            elif action == 'detalleregistro':
                try:
                    data = {}
                    data['solicitud'] = solicitud = SolicitudReposicionCajaChica.objects.get(pk=int(request.GET['id']))
                    data['comprobantes'] = solicitud.detallecomprobantes()
                    template = get_template("aprobar_cajachica/detalleregistro.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'detallesolicitud1':
                try:
                    data = {}
                    data['solicitud'] = solicitud = SolicitudReposicionCajaChica.objects.get(pk=int(request.GET['id']))
                    data['aprobador'] = persona
                    data['fecha'] = datetime.now().date()
                    data['aprobadores'] = solicitud.solicitudreposicioncajachicaaprobacion_set.filter(status=True)
                    template = get_template("aprobar_cajachica/detalle_aprobarsolicitud1.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'verdetallesolicitud1':
                try:
                    data = {}
                    data['solicitud'] = solicitud = SolicitudReposicionCajaChica.objects.get(pk=int(request.GET['id']))
                    data['aprobadores'] = solicitud.solicitudreposicioncajachicaaprobacion_set.filter(status=True)
                    template = get_template("aprobar_cajachica/detalle_aprobarsolicitud2.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'comprobantes':
                try:
                    data['title'] = u'Comprobantes de caja chica'
                    search = None
                    ids = None
                    data['idsol']= idsol = request.GET['idsol']
                    data['solicitud']= SolicitudReposicionCajaChica.objects.get(status=True, id=idsol)
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        comprobante = ComprobanteCajaChica.objects.filter(status=True, solicitudreposicion=idsol).filter(
                            Q(concepto__contains=search) |
                            Q(solicita__cedula__icontains=search) |
                            Q(solicita__pasaporte__icontains=search)|
                            Q(solicita__nombres__icontains=search) |
                            Q(solicita__apellido1__icontains=search) |
                            Q(solicita__apellido2__icontains=search)
                        ).distinct()
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        comprobante = ComprobanteCajaChica.objects.filter(id=ids)
                    else:
                        comprobante = ComprobanteCajaChica.objects.filter(status=True, solicitudreposicion=idsol)
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
                    return render(request, 'cajachica/comprobantes.html', data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addcomprobante':
                try:
                    data['title'] = u'Añadir comprobante'
                    data['idsol']= int(request.GET['idsol'])
                    form = ComprobanteCajaChicaForm()
                    data['form'] = form
                    return render(request, "cajachica/addcomprobante.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcomprobante':
                try:
                    data['title'] = u'Editar comprobante'
                    data['comprobante']=comprobante=ComprobanteCajaChica.objects.get(id=request.GET['id'])
                    initial = model_to_dict(comprobante)
                    form= ComprobanteCajaChicaForm(initial=initial)
                    form.edit(comprobante.solicita)
                    data['form'] =form
                    data['valorinicial']=comprobante.valor
                    data['valormaximo']=comprobante.cajachica.valormaximo
                    return render(request, "cajachica/editcomprobante.html", data)
                except Exception as ex:
                    pass

            elif action == 'delecomprobante':
                try:
                    data['title'] = u'Eliminar comprobante'
                    data['comprobante'] = ComprobanteCajaChica.objects.get(pk=int(request.GET['id']))
                    return render(request, "cajachica/delecomprobante.html", data)
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
                    return render(request, 'cajachica/liquidaciones.html', data)
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
                    return render(request, "cajachica/addliquidacion.html", data)
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
                    return render(request, "cajachica/editliquidacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleliquidacion':
                try:
                    data['title'] = u'Eliminar liquidación'
                    data['idsol'] = int(request.GET['idsol'])
                    data['comprobante'] = ComprobanteCajaChica.objects.get(pk=int(request.GET['idc']))
                    data['liquidacion'] = ComprobanteCajaChicaLiquidacion.objects.get(pk=int(request.GET['id']))
                    return render(request, "cajachica/deleliquidacion.html", data)
                except Exception as ex:
                    pass



            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Caja chica.'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                ss = search.split(' ')
                while '' in ss:
                    ss.remove('')
                if len(ss) == 1:
                    caja = SolicitudCajaChica.objects.filter(status=True).filter(Q(concepto__contains=search) |
                                                                                 Q(solicita__cedula__icontains=search) |
                                                                                 Q(solicita__pasaporte__icontains=search) |
                                                                                 Q(solicita__nombres__icontains=search) |
                                                                                 Q(solicita__apellido1__icontains=search) |
                                                                                 Q(solicita__apellido2__icontains=search)
                                                                                 ).distinct().order_by('-fechasolicitud', '-secuencia')
                else:
                    caja = SolicitudCajaChica.objects.filter(status=True).filter(Q(concepto__contains=ss[0]) | Q(concepto__contains=ss[1]) |
                                                                                 Q(solicita__cedula__icontains=ss[0]) | Q(solicita__cedula__icontains=ss[1]) |
                                                                                 Q(solicita__pasaporte__icontains=ss[0]) | Q(solicita__pasaporte__icontains=ss[1]) |
                                                                                 Q(solicita__nombres__icontains=ss[0]) | Q(solicita__nombres__icontains=ss[1]) |
                                                                                 Q(solicita__apellido1__icontains=ss[0]) & Q(solicita__apellido2__icontains=ss[1])
                                                                                 ).distinct().order_by('-fechasolicitud', '-secuencia')
            elif 'id' in request.GET:
                ids = request.GET['id']
                caja = SolicitudCajaChica.objects.filter(id=ids)
            else:
                caja = SolicitudCajaChica.objects.filter(status=True).order_by('-fechasolicitud', '-secuencia')
            paging = MiPaginador(caja, 20)
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
            return render(request, 'cajachica/view.html', data)

