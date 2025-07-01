# -*- coding: UTF-8 -*-
import json
import random
import sys

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
import xlwt
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import Context
from django.template.loader import get_template
from xlwt import *
from django.shortcuts import render, redirect
from decorators import secure_module
from sagest.forms import DepartamentoForm, IntegranteDepartamentoForm, ResponsableDepartamentoForm, \
    SeccionDepartamentoForm
from sagest.models import Departamento, SeccionDepartamento, OpcionSistema
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from .forms import GEDCIndicadoresForm, GEDCCabForm, GEDCCabEncuestaForm
from sga.funciones import MiPaginador, log, generar_nombre, remover_caracteres_especiales_unicode
from sga.models import Administrativo, Persona, InstitucionEducacionSuperior
from .models import GEDCCab, GEDCIndicador, GEDCPreguntas, GEDCPersona, GEDCRespuestas


@transaction.atomic()
def view(request):
    data = {'email_domain': EMAIL_DOMAIN}

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            res_json = []
            if action == 'responder':
                try:
                    with transaction.atomic():
                        id = int(request.POST['id'])
                        cabecera = GEDCCab.objects.get(pk=id)
                        listapreguntas = []
                        banderapais = False
                        if 'pais' in request.POST:
                            pais = request.POST['pais']
                            if pais:
                                banderapais = True
                        if not banderapais:
                            if 'otropais' in request.POST:
                                otropais = request.POST['otropais']
                                if otropais:
                                    banderapais = True
                        if not banderapais:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "DEBE SELECCIONAR O ESCRIBIR UN PAIS DE ORIGEN."}, safe=False)
                        otrauniversidad = ''
                        universidad = ''
                        banderauniversidad = False
                        if 'universidad' in request.POST:
                            universidad = request.POST['universidad']
                            if universidad:
                                banderauniversidad = True
                        if not banderauniversidad:
                            if 'otrauniversidad' in request.POST:
                                otrauniversidad = request.POST['otrauniversidad']
                                if otrauniversidad:
                                    banderauniversidad = True
                        if not banderauniversidad:
                            otrauniversidad = 'NINGUNA'
                            # transaction.set_rollback(True)
                            # return JsonResponse({"result": True, "mensaje": "DEBE SELECCIONAR O ESCRIBIR UNA UNIVERSIDAD."}, safe=False)
                        evaluacion = GEDCPersona(cab=cabecera,
                                                 pais_id=request.POST['pais'],
                                                 universidad_id=universidad,
                                                 otropais=request.POST['otropais'],
                                                 otrauniversidad=otrauniversidad,
                                                 genero=request.POST['genero'])
                        evaluacion.save(request)
                        for x, y in request.POST.lists():
                            if len(x) > 5 and x[:5] == 'valor':
                                indicador = GEDCPreguntas.objects.get(pk=x[5:])
                                listapreguntas.append(indicador.pk)
                        for li in listapreguntas:
                            pregunta = GEDCPreguntas.objects.get(pk=li)
                            respuesta = GEDCRespuestas(cab=evaluacion, pregunta=pregunta)
                            respuesta.indicador = pregunta.indicador
                            if pregunta.indicador.evalua:
                                nameid = 'eval{}'.format(li)
                                if nameid in request.POST:
                                    eval = request.POST[nameid]
                                    respuesta.respevalua = True if eval == 'True' else False
                                else:
                                    if pregunta.obligatorio:
                                        transaction.set_rollback(True)
                                        return JsonResponse({"result": True, "mensaje": "Complete toda la información."}, safe=False)
                            if pregunta.indicador.calificacion:
                                nameid = 'cal{}'.format(li)
                                if nameid in request.POST:
                                    calificacion = request.POST[nameid]
                                    respuesta.respcalificacion = int(calificacion)
                                else:
                                    if pregunta.obligatorio:
                                        transaction.set_rollback(True)
                                        return JsonResponse({"result": True, "mensaje": "Complete toda la información."}, safe=False)
                            if pregunta.indicador.observacion:
                                nameid = 'obs{}'.format(li)
                                if nameid in request.POST:
                                    observacion = request.POST[nameid]
                                    respuesta.respobservacion = observacion
                                else:
                                    if pregunta.obligatorio:
                                        transaction.set_rollback(True)
                                        return JsonResponse({"result": True, "mensaje": "Complete toda la información."}, safe=False)
                            if pregunta.indicador.evidencias:
                                nameid = 'file{}'.format(li)
                                if nameid in request.FILES:
                                    file = request.FILES[nameid]
                                    newfile = request.FILES[nameid]
                                    nombrefoto = "respuesta_{}".format(pregunta.pk)
                                    newfile._name = generar_nombre(nombrefoto.strip(), newfile._name)
                                    respuesta.respevidencia = newfile
                                else:
                                    if pregunta.obligatorio:
                                        transaction.set_rollback(True)
                                        return JsonResponse({"result": True, "mensaje": "Complete toda la información."}, safe=False)
                            respuesta.save()
                        evaluacion.save(request)
                        messages.success(request, 'Encuesta Registrada')
                        return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'consultaruniversidades':
                id = (request.GET['id']).replace(",", "")
                filtro = InstitucionEducacionSuperior.objects.filter(status=True, pais__pk=int(id)).order_by('nombre')
                if 'search' in request.GET:
                    search = request.GET['search']
                    filtro = filtro.filter(nombre__icontains=search).order_by('-id')
                resp = [{'id': cr.pk, 'text': cr.nombre} for cr in filtro if cr.status]
                return HttpResponse(json.dumps({'state': True, 'result': resp}))

    if 'enc' in request.GET:
        nameid = request.GET['enc']
        encuesta = GEDCCab.objects.filter(nombreurl=nameid, publicar=True, status=True)
        if encuesta.exists():
            data['filtro'] = cab = encuesta.first()
            data['form'] = form = GEDCCabEncuestaForm()
            data['preguntas'] = preguntas = GEDCPreguntas.objects.filter(cab=cab, status=True).order_by('orden')
            return render(request, 'adm_gedcevaluacion/encuesta/encuesta.html', data)
        else:
            return redirect('/')
    else:
        return redirect('/')