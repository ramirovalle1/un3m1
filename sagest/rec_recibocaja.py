# -*- coding: UTF-8 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from decorators import secure_module, last_access
from sagest.commonviews import anio_ejercicio, secuencia_recaudacion
from settings import TESORERO_ID
from sga.commonviews import adduserdata, obtener_reporte
from sagest.forms import CierreSesionCajaForm, ReciboCajaForm, CustomDateInput
from sga.funciones import MiPaginador, log, variable_valor
from sagest.models import LugarRecaudacion, SesionCaja, CierreSesionCaja, Factura, ReciboCaja


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    data['persona_factura'] = persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if 'aniofiscalpresupuesto' in request.session:
        anio = request.session['aniofiscalpresupuesto']
    else:
        anio = anio_ejercicio().anioejercicio
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addrecibo':
            try:
                sesioncaja = SesionCaja.objects.get(pk=request.POST['id'])
                if not sesioncaja.abierta:
                    return JsonResponse({"result": "bad", "mensaje": u"La sesion de caja no esta abierta."})
                f = ReciboCajaForm(request.POST)
                if f.is_valid():
                    secuencia = secuencia_recaudacion(request, sesioncaja.caja.puntoventa, 'recibocaja')
                    # secuencia.recibocaja += 1
                    # secuencia.save(request)
                    if ReciboCaja.objects.filter(numero=secuencia).exists():
                        return {'result': 'bad', "mensaje": u"Numero de recibo caja ya existe."}
                    recibocaja = ReciboCaja(sesioncaja=sesioncaja,
                                            numerocompleto=sesioncaja.caja.puntoventa.establecimiento.strip() + "-" + sesioncaja.caja.puntoventa.puntoventa.strip() + "-" + str(
                                                secuencia).zfill(9),
                                            numero=secuencia,
                                            concepto=f.cleaned_data['concepto'],
                                            partida=f.cleaned_data['partidassaldo'],
                                            valor=f.cleaned_data['valor'],
                                            fechacomprobante=f.cleaned_data['fechacomprobante'],
                                            persona_id=f.cleaned_data['persona'])
                    recibocaja.save(request)
                    log(u'Adiciono recibo de caja: %s' % sesioncaja, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                f = ReciboCajaForm(request.POST, request.FILES)
                if f.is_valid():
                    recibocaja = ReciboCaja.objects.get(pk=request.POST['id'])
                    recibocaja.valor = f.cleaned_data['valor']
                    recibocaja.concepto = f.cleaned_data['concepto']
                    recibocaja.partida = f.cleaned_data['partidassaldo']
                    recibocaja.fechacomprobante=f.cleaned_data['fechacomprobante']
                    recibocaja.save(request)
                    log(u'Modifico recibo de caja: %s' % recibocaja, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delrecibo':
            try:
                recibo = ReciboCaja.objects.get(pk=request.POST['id'])
                log(u'Elimino recibo de caja: %s' % recibo, request, "del")
                recibo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'cerrarsesion':
            try:
                form = CierreSesionCajaForm(request.POST)
                tesorero_id = variable_valor('TESORERO')
                lugarrecaudacion = LugarRecaudacion.objects.filter(persona=persona)[0]
                sesioncaja = lugarrecaudacion.sesioncaja_set.get(pk=int(request.POST['id']))
                if not sesioncaja.abierta:
                    return JsonResponse({"result": "bad", "mensaje": u"La sesión de caja ya esta cerrada."})
                if form.is_valid():
                    cs = CierreSesionCaja(sesion=sesioncaja,
                                          bill100=form.cleaned_data['bill100'],
                                          bill50=form.cleaned_data['bill50'],
                                          bill20=form.cleaned_data['bill20'],
                                          bill10=form.cleaned_data['bill10'],
                                          bill5=form.cleaned_data['bill5'],
                                          bill2=form.cleaned_data['bill2'],
                                          bill1=form.cleaned_data['bill1'],
                                          total=0,
                                          mon1=form.cleaned_data['mon1'],
                                          mon50=form.cleaned_data['mon50'],
                                          mon25=form.cleaned_data['mon25'],
                                          mon10=form.cleaned_data['mon10'],
                                          mon5=form.cleaned_data['mon5'],
                                          mon1c=form.cleaned_data['mon1c'],
                                          deposito=form.cleaned_data['deposito'],
                                          cheques=form.cleaned_data['cheques'],
                                          transfer=form.cleaned_data['transfer'],
                                          tarjeta=form.cleaned_data['tarjeta'],
                                          tesorero_id=tesorero_id,
                                          fecha=datetime.now())
                    cs.save(request)
                    sesioncaja.abierta = False
                    sesioncaja.save(request)
                    sesioncaja.generar_resumen_partida()
                    log(u'Cerro sesion en caja: %s - sesion caja: %s ' % (cs, sesioncaja), request, "del")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'detalle_sesioncaja':
            try:
                data['sesion'] = sesion = SesionCaja.objects.get(pk=int(request.POST['id']))
                data['cierre'] = sesion.cierre_sesion()
                template = get_template("rec_caja/detalle.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addrecibo':
                try:
                    data['title'] = u'Adicionar recibo de caja'
                    form = ReciboCajaForm()
                    form.fields['fechacomprobante'].widget = CustomDateInput(
                        attrs={'type': 'date', 'class': 'form-control', 'formwidth': '50%'})

                    form.adicionar(anio)
                    data['form'] = form
                    data['sesioncaja'] = sesioncaja = SesionCaja.objects.get(pk=request.GET['caja'])
                    form.fields['fechacomprobante'].initial = str(sesioncaja.fecha)
                    return render(request, "rec_recibocaja/addrecibo.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Modificar Recibo de Caja'
                    data['recibo'] = recibo = ReciboCaja.objects.get(pk=request.GET['id'])
                    form = ReciboCajaForm(initial={'valor': recibo.valor,
                                                   'concepto': recibo.concepto,
                                                   'partidassaldo': recibo.partida,
                                                   'persona': recibo.persona})
                    form.editar(recibo, anio)
                    form.fields['fechacomprobante'].widget = CustomDateInput(attrs={'type': 'date', 'class': 'form-control', 'formwidth': '50%'})
                    form.fields['fechacomprobante'].initial = str(recibo.fechacomprobante)
                    data['form'] = form
                    return render(request, 'rec_recibocaja/edit.html', data)
                except Exception as ex:
                    pass

            if action == 'delrecibo':
                try:
                    data['title'] = u'Eliminar Recibo de Caja'
                    data['recibo'] = ReciboCaja.objects.get(pk=request.GET['id'])
                    return render(request, 'rec_recibocaja/delete.html', data)
                except Exception as ex:
                    pass

            elif action == 'cerrarsesion':
                try:
                    data['title'] = u"Cierre de sesión de cobranzas en caja"
                    data['sesioncaja'] = sesioncaja = SesionCaja.objects.get(pk=request.GET['id'])
                    if sesioncaja.caja.persona != request.session['persona']:
                        raise NameError('Error')
                    data['form'] = CierreSesionCajaForm(initial={'tarjeta': sesioncaja.total_tarjeta_sesion(),
                                                                 'cheques': sesioncaja.total_cheque_sesion(),
                                                                 'depositos': sesioncaja.total_deposito_sesion(),
                                                                 'electronico': sesioncaja.total_electronico_sesion(),
                                                                 'transfer': sesioncaja.total_transferencia_sesion()})
                    return render(request, "rec_caja/cerrarsesion.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Recibos de caja.'
                ids = None
                search = None
                url_vars = f""
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        recibocaja = ReciboCaja.objects.filter(
                            Q(sesioncaja__caja__persona__apellido1__icontains=search) |
                            Q(sesioncaja__caja__persona__apellido2__icontains=search) |
                            Q(sesioncaja__caja__persona__nombres__icontains=search) |
                            Q(persona__nombres__icontains=search) |
                            Q(persona__apellido1__icontains=search) |
                            Q(persona__apellido2__icontains=search) |
                            Q(numero__icontains=search) |
                            Q(concepto__icontains=search)
                            ).distinct().order_by('-numero')
                    else:
                        recibocaja = ReciboCaja.objects.filter(
                            Q(sesioncaja__caja__persona__apellido1__icontains=ss[0]) &
                            Q(sesioncaja__caja__persona__apellido2__icontains=ss[1]) |
                            Q(persona__apellido1__icontains=ss[0])
                            & Q(persona__apellido2__icontains=ss[1]) |
                            Q(concepto__icontains=search)
                            ).distinct().order_by('-numero')
                    url_vars += f"&s={search}"
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    recibocaja = ReciboCaja.objects.filter(id=ids)
                else:
                    recibocaja = ReciboCaja.objects.all().order_by('-numero')
                paging = MiPaginador(recibocaja, 25)
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
                sesioncaja = None
                if LugarRecaudacion.objects.filter(persona=request.session['persona'],
                                                   puntoventa__activo=True).exists():
                    caja = LugarRecaudacion.objects.filter(persona=request.session['persona'], puntoventa__activo=True)[
                        0]
                    if caja.sesioncaja_set.filter(abierta=True).exists():
                        sesioncaja = caja.sesioncaja_set.filter(abierta=True)[0]
                data['sesioncaja'] = sesioncaja
                data['rangospaging'] = paging.rangos_paginado(p)
                data['ids'] = ids if ids else None
                data['page'] = page
                data['recibocajas'] = page.object_list
                data['search'] = search if search else ""
                data['reporte_0'] = obtener_reporte('comprobante_entrega_factura_no')
                data['url_vars'] = url_vars
                return render(request, "rec_recibocaja/view.html", data)
            except Exception as ex:
                pass
