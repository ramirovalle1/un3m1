# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from sagest.models import datetime, PeriodoPac
from sga.commonviews import adduserdata


def rango_anios():
    if PeriodoPac.objects.exists():
        inicio = datetime.now().year
        fin = PeriodoPac.objects.order_by('anio')[0].anio
        return range(inicio, fin - 1, -1)
    return [datetime.now().date().year]


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module


def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']


            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'PAC UNEMI'

            data['anios'] = anios = rango_anios()
            if 'anio' in request.GET:
                request.session['anio'] = int(request.GET['anio'])
            else:
                request.session['anio'] = anios[0]
            data['anioselect'] = anioselect = request.session['anio']
            cursor = connection.cursor()
            # data = {}
            sql = "select d.mes, (case d.mes when 1 then 'ENERO' when 2 then 'FEBRERO' when 3 then 'MARZO' when 4 then 'ABRIL' when 5 then 'MAYO' when 6 then 'JUNIO' when 7 then 'JULIO' when 8 then 'AGOSTO' when 9 then 'SEPTIEMBRE' when 10 then 'OCTUBRE' when 11 then 'NOVIEMBRE' when 12 then 'DICIEMBRE' end) as mesletra, sum(d.valor) as valor, sum(d.valorejecutado) as valorejecutado from sagest_pacdetalladogeneral d, sagest_pacgeneral pc ,sagest_periodopac p "\
                  " where pc.id=d.pacgeneral_id and d.status=true and pc.status=true and p.id=pc.periodo_id and p.anio=%s GROUP by d.mes order by d.mes"
            cursor.execute(sql, [anioselect])
            data['results'] = cursor.fetchall()

            return render(request, "totalpac/view.html", data)
