# -*- coding: UTF-8 -*-
import json
import os
import sys
from datetime import datetime
from itertools import chain

import pyqrcode
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import get_template
from django.template import Context

from balcon.models import Informacion, Proceso, Solicitud, Agente, Servicio, HistorialSolicitud, ProcesoServicio, \
    RequisitosConfiguracion, RequisitosSolicitud, Categoria
from decorators import secure_module, last_access
from even.models import PeriodoEvento, RegistroEvento, DetallePeriodoEvento
from sagest.models import Congreso, InscritoCongreso, Rubro
from settings import SITE_STORAGE
from sga.commonviews import adduserdata
from sga.funciones import log, generar_nombre, notificacion, remover_caracteres_especiales_unicode
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsaveqrcertificadoscongresoinscrito
from sga.templatetags.sga_extras import encrypt
from django.db import connections

import random
@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    perfilprincipal = request.session['perfilprincipal']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'delinscripcion':
            try:
                inscribir = InscritoCongreso.objects.get(pk=int(request.POST['id']))

                if inscribir.cancelo_rubro():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, el inscrito ya cuenta rubros cancelados."})
                log(u'Elimino Incrito de congreso : %s [%s]' % (inscribir,inscribir.id), request, "del")
                inscribir.status=False
                inscribir.save(request)
                if inscribir.congreso.tiporubro:
                    if Rubro.objects.filter(persona=inscribir.participante,tipo=inscribir.congreso.tiporubro,cancelado=False, status=True).exists():
                        listarubros = Rubro.objects.filter(persona=inscribir.participante,tipo=inscribir.congreso.tiporubro,cancelado=False, status=True)
                        for rubro in listarubros:
                            rubro.status=False
                            rubro.save(request)
                            log(u'Elimino Rubro en congreso : %s [%s]' % (inscribir, inscribir.congreso), request, "del")
                            if rubro.epunemi and rubro.idrubroepunemi > 0:
                                cursor = connections['epunemi'].cursor()
                                sql = "UPDATE sagest_rubro SET status=false WHERE sagest_rubro.status=true and sagest_rubro.id=" + str(
                                    rubro.idrubroepunemi)
                                cursor.execute(sql)
                                cursor.close()

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'solicitar_certifi':
            try:
                id = request.POST['id_congreso']
                congreso = Congreso.objects.get(id=id, status=True)
                inscrito = InscritoCongreso.objects.filter(congreso=congreso, participante=persona, status=True)


            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad",
                                     "mensaje": f"Error al solicitar certificado. {ex}({sys.exc_info()[-1].tb_lineno})"})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            # return HttpResponseRedirect(request.path)

            if action == 'listadocongresos':
                try:
                    data['title'] = u'Congresos'
                    data['listado'] = congresos = Congreso.objects.filter(status=True).order_by('-pk')
                    return render(request, "congresos/listado.html", data)
                except Exception as ex:
                    return redirect('/')

            if action == 'delinscripcion':
                try:
                    data['title'] = u'Eiminar inscripción congreso'
                    data['inscribir'] = InscritoCongreso.objects.get(pk=request.GET['id'])
                    return render(request, "congresos/delinscripcion.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u'Mis Congresos'
                data['congresos'] = congresos = persona.inscritocongreso_set.filter(status=True).distinct()
                paging = Paginator(congresos, 30)
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
                data['page'] = page
                return render(request, "congresos/view.html", data)
            except Exception as ex:
                pass




def certificado_congreso_tendencias_turisticas(inscrito):
    data = {}
    data['congreso'] = congreso = inscrito.congreso
    data['inscrito'] = inscrito
    mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
           "octubre", "noviembre", "diciembre"]
    data['fecha'] = u"Milagro, %s de %s del %s" % (
        datetime.now().day, str(mes[datetime.now().month - 1]), datetime.now().year)
    qrname = 'qr_certificado_' + str(inscrito.id)
    # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'certificadoscongresoinscrito', ''))
    # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
    rutapdf = folder + qrname + '.pdf'
    rutaimg = folder + qrname + '.png'
    if os.path.isfile(rutapdf):
        os.remove(rutaimg)
        os.remove(rutapdf)
    url = pyqrcode.create('http://sga.unemi.edu.ec//media/certificadoscongresoinscrito/' + qrname + '.pdf')
    # url = pyqrcode.create('http://127.0.0.1:8000//media/qrcode/certificados/' + qrname + '.pdf')
    imageqr = url.png(folder + qrname + '.png', 16, '#000000')
    data['qrname'] = qrname
    return conviert_html_to_pdfsaveqrcertificadoscongresoinscrito(
        'congreso/certificado_pdf.html',
        {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
    )
