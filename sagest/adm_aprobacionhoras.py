# -*- coding: UTF-8 -*-
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template

from decorators import secure_module
from sagest.forms import AprobacionMarcadasForm
from sagest.models import DistributivoPersona, TrabajadorDiaJornada
from settings import PUESTO_ACTIVO_ID
from sga.commonviews import adduserdata
from sga.funciones import log
from sga.models import Persona
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    usuario = request.user
    jefe = request.session['persona']
    departamento = jefe.mi_departamento()
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'meses_anio':
            try:
                distributivo = DistributivoPersona.objects.get(pk=int(request.POST['id']))
                anio = request.POST['anio']
                lista = []
                for elemento in TrabajadorDiaJornada.objects.filter(persona=distributivo.persona, anio=anio).order_by('mes').distinct():
                    if [elemento.mes, elemento.rep_mes()] not in lista:
                        lista.append([elemento.mes, elemento.rep_mes()])
                return JsonResponse({"result": "ok", "lista": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'detalle_jornda_trab':
            try:
                data = {}
                data['distributivo'] = distributivo = DistributivoPersona.objects.get(pk=int(request.POST['id']))
                anio = request.POST['anio']
                mes = request.POST['mes']
                data['mes'] = mes
                data['h'] = False
                if 'h' in request.POST:
                    data['h'] = True
                data['horainicio'] = datetime(2016, 1, 1, 0, 0, 0)
                data['horafin'] = datetime(2016, 1, 1, 23, 59, 59)
                data['dias'] = TrabajadorDiaJornada.objects.filter(persona=distributivo.persona, anio=anio, mes=mes, status=True).order_by('fecha')
                template = get_template("adm_aprobacionhoras/detallejornadatrab.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'aprobar':
            try:
                f = AprobacionMarcadasForm(request.POST)
                if f.is_valid():
                    trabajadordiajornada = TrabajadorDiaJornada.objects.get(pk=request.POST['id'])

                    trabajadordiajornada.totalsegundostrabajadosaux = trabajadordiajornada.totalsegundostrabajados
                    trabajadordiajornada.totalsegundosextrasaux = trabajadordiajornada.totalsegundosextras
                    trabajadordiajornada.totalsegundosatrasosaux = trabajadordiajornada.totalsegundosatrasos
                    trabajadordiajornada.save(request)
                    jornada = trabajadordiajornada.jornada
                    jornadasdia = jornada.detallejornada_set.filter(dia=trabajadordiajornada.fecha.isoweekday())
                    duracionjornada = 0
                    for jornadamarcada in jornadasdia:
                        duracionjornada = duracionjornada + (datetime(trabajadordiajornada.fecha.year, trabajadordiajornada.fecha.month, trabajadordiajornada.fecha.day, jornadamarcada.horafin.hour,jornadamarcada.horafin.minute, jornadamarcada.horafin.second) - (datetime(trabajadordiajornada.fecha.year, trabajadordiajornada.fecha.month, trabajadordiajornada.fecha.day, jornadamarcada.horainicio.hour,jornadamarcada.horainicio.minute,jornadamarcada.horainicio.second))).seconds

                    totalsegundostrabajados = trabajadordiajornada.totalsegundostrabajados
                    totalsegundosatrasos = trabajadordiajornada.totalsegundosatrasos
                    totalsegundosextras = trabajadordiajornada.totalsegundosextras
                    if totalsegundosatrasos > 0:
                        # a los segundos de atrasos le resto las horas adicionales
                        totalsegundosatrasos = totalsegundosatrasos - totalsegundosextras
                        if totalsegundosatrasos < 0:
                            totalsegundosatrasos = 0
                        totalsegundostrabajados = totalsegundostrabajados + totalsegundosextras
                        if totalsegundostrabajados > duracionjornada:
                            totalsegundostrabajados = duracionjornada

                    trabajadordiajornada.totalsegundostrabajados = totalsegundostrabajados
                    trabajadordiajornada.totalsegundosextras = 0
                    trabajadordiajornada.totalsegundosatrasos = totalsegundosatrasos
                    trabajadordiajornada.aprobado = True
                    trabajadordiajornada.observacion = f.cleaned_data['observacion']

                    trabajadordiajornada.save(request)
                    log(u'Aprobo dia jornada: %s' % trabajadordiajornada, request, "edit")
                    # return render(request, "adm_aprobacionhoras?action=vermarcada&id=%s" % trabajadordiajornada.persona.id, data)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar los datos."})

        if action == 'desaprobar':
            try:
                trabajadordiajornada = TrabajadorDiaJornada.objects.get(pk=request.POST['id'])
                trabajadordiajornada.totalsegundostrabajados = trabajadordiajornada.totalsegundostrabajadosaux
                trabajadordiajornada.totalsegundosextras = trabajadordiajornada.totalsegundosextrasaux
                trabajadordiajornada.totalsegundosatrasos = trabajadordiajornada.totalsegundosatrasosaux
                trabajadordiajornada.totalsegundostrabajadosaux = 0
                trabajadordiajornada.totalsegundosextrasaux = 0
                trabajadordiajornada.totalsegundosatrasosaux = 0
                trabajadordiajornada.aprobado = False
                trabajadordiajornada.observacion = ''
                trabajadordiajornada.save(request)
                log(u'Desaprobo dia jornada: %s' % trabajadordiajornada, request, "edit")
                # return render(request, "adm_aprobacionhoras?action=vermarcada&id=%s" % trabajadordiajornada.persona.id, data)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'vermarcada':
                try:
                    data['h'] = False
                    data['title'] = u'Detalle Jornada laboral'
                    empleado = Persona.objects.filter(pk=int(encrypt(request.GET['id'])))[0]
                    data['distributivo'] = distributivo = empleado.distributivopersona_set.filter(unidadorganica=departamento, estadopuesto__id=PUESTO_ACTIVO_ID)[0]
                    data['anios'] = distributivo.lista_anios_trabajados()
                    data['jornadas'] = distributivo.persona.historialjornadatrabajador_set.all()
                    data['anioselect'] = datetime.now().year
                    data['messelect'] = datetime.now().month
                    if 'messelect' in request.GET:
                        data['messelect'] = request.GET['messelect']
                    return render(request, "adm_aprobacionhoras/detallejornadastrabajador.html", data)
                except Exception as ex:
                    pass

            if action == 'aprobar':
                try:
                    data['title'] = u'Aprobación de Marcadas'
                    data['empleado'] = Persona.objects.get(pk=int(encrypt(request.GET['idp'])))
                    data['trabajadordiajornada'] = TrabajadorDiaJornada.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['messelect'] = int(request.GET['messelect'])
                    data['form'] = AprobacionMarcadasForm()
                    return render(request, "adm_aprobacionhoras/aprobar.html", data)
                except Exception as ex:
                    pass

            if action == 'desaprobar':
                try:
                    data['title'] = u'Desaprobación de Marcadas'
                    data['persona'] = Persona.objects.get(pk=request.GET['idp'])
                    data['trabajadordiajornada'] = TrabajadorDiaJornada.objects.get(pk=request.GET['id'])
                    data['form'] = AprobacionMarcadasForm()
                    return render(request, "adm_aprobacionhoras/desaprobar.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Integrantes Departamento'
            integrantes =  departamento.mis_integrantes()
            data['integrantes'] = integrantes
            data['departamento'] = departamento
            return render(request, 'adm_aprobacionhoras/view.html', data)