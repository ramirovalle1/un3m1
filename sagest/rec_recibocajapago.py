# -*- coding: UTF-8 -*-
from datetime import time
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from sagest.forms import ReciboCajaPagoAnularForm
from sagest.models import datetime, Banco, PagoReciboCaja, Rubro
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log
from django.template import Context
from django.template.loader import get_template


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'anular_recibo':
            try:
                recibocaja = PagoReciboCaja.objects.get(pk=int(request.POST['id']))

                if recibocaja.anulado:
                    return JsonResponse({"result": "bad", "mensaje": u"El Recibo de Caja ya ha sido anulado por otro usuario."})

                f = ReciboCajaPagoAnularForm(request.POST)
                if f.is_valid():
                    # Anulo el recibo de caja
                    recibocaja.anulado = True
                    recibocaja.observacion = f.cleaned_data['observacion'].strip().upper()
                    recibocaja.save(request)

                    # Consulto los pagos asociados al recibo
                    for pago in recibocaja.pagos.all():
                        # Elimino el pago
                        pago.status = False
                        pago.save(request)

                        rubro = Rubro.objects.get(pk=pago.rubro.id)
                        # Se deja el saldo que estaba antes del pago
                        rubro.saldo = rubro.saldo + pago.valortotal
                        rubro.cancelado = False
                        rubro.save(request)

                    log(u'Anuló recibo de caja de pago: %s  - %s' % (persona, recibocaja), request, "edit")

                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'mostrardetalle':
                try:
                    data = {}
                    data['recibo'] = recibo = PagoReciboCaja.objects.get(pk=int(request.GET['id']))
                    data['pagos'] = recibo.pagos.all().order_by('rubro_id')
                    template = get_template("rec_recibocajapago/detallerubros.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'anular_recibo':
                try:
                    data['title'] = u'Anular Recibo de Caja de Pago'
                    data['id'] = int(request.GET['id'])

                    form = ReciboCajaPagoAnularForm()

                    template = get_template("rec_recibocajapago/anularrecibocajapago.html")
                    data['form'] = form
                    data['recibo'] = PagoReciboCaja.objects.get(pk=int(request.GET['id']))
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Recibos de Caja de Pagos de Rubros'
            search = None
            ids = None

            if 's' in request.GET:
                search = request.GET['s'].strip()
                recibos = PagoReciboCaja.objects.filter(Q(persona__nombres__icontains=search)|
                                                 Q(persona__apellido1__icontains=search)|
                                                 Q(persona__apellido2__icontains=search)|
                                                 Q(persona__cedula__icontains=search)|
                                                 Q(persona__ruc__icontains=search)|
                                                 Q(persona__pasaporte__icontains=search)|
                                                        Q(numerocompleto__icontains=search),
                                                        status=True
                                                        ).order_by('-numero')
            elif 'id' in request.GET:
                ids = request.GET['id']
                recibos = PagoReciboCaja.objects.filter(status=True, pk=ids)
            else:
                recibos = PagoReciboCaja.objects.filter(status=True).order_by('-numero')

            paging = MiPaginador(recibos, 25)
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
            data['recibos'] = page.object_list

            data['totalsolicitudes'] = total = recibos.count()
            data['totalaprobadas'] = aprobadas = 0# solicitudes.filter(estado=2).count()
            data['totalrechazadas'] = rechazadas = 0# solicitudes.filter(estado=3).count()
            data['totalrevision'] = revision = 0# solicitudes.filter(estado=5).count()
            data['totalpendiente'] = total - (aprobadas + rechazadas + revision)
            # data['estadodocumento'] = estadodocumento


            data['fechaactual'] = datetime.now().strftime('%d-%m-%Y')
            return render(request, "rec_recibocajapago/view.html", data)
