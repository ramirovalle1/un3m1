# -*- coding: UTF-8 -*-
import json
import random
import sys

import openpyxl
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
import xlwt
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import Context
from django.template.loader import get_template
from docx import Document
from xlwt import *
from django.shortcuts import render, redirect
from decorators import secure_module
from postulaciondip.models import InscripcionInvitacion, HistorialInvitacion, Proceso
from sagest.models import Departamento, SeccionDepartamento, OpcionSistema
from settings import EMAIL_DOMAIN, SITE_ROOT
from sga.commonviews import adduserdata
from sga.templatetags.sga_extras import encrypt
from .forms import PerfilPuestoDipForm, RequisitoPagoDipForm, CampoContratoDipForm, PlantillaContratoDipForm, \
    ProcesoPagoForm, PasoProcesoPagoForm, ContratoDipForm, ContratoMetodoPago, DisponerContratoDipForm
from sga.funciones import MiPaginador, log, generar_nombre, remover_caracteres_especiales_unicode
from sga.models import Administrativo, Persona, ProfesorMateria
from .models import *
from django.db.models import Sum, Q, F, FloatField
from django.db.models.functions import Coalesce
from datetime import datetime, timedelta

@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    usuario = request.user
    if request.method == 'POST':
        res_json = []
        action = request.POST['action']

        if action == 'addcontrato':
            try:
                f = DisponerContratoDipForm(request.POST)
                if f.is_valid():
                    if ContratoDip.objects.filter(invitacion_id=request.POST['invitacion'],status=True).exists():
                        return JsonResponse({"result": True, "mensaje": "Esta persona registra un contrato."}, safe=False)

                    contrato = ContratoDip(
                        invitacion_id=request.POST['invitacion'],
                        estado=0
                    )
                    contrato.save(request)
                    historial = HistorialContratoDip(contratodip=contrato,
                                                     observacion=request.POST['observacion'],
                                                     estado = 0)
                    historial.save(request)
                    log(u'Dispuso elaboración  de Contrato : %s' % contrato, request, "add")


                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)



        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']


            if action == 'addcontrato':
                try:
                    data['form2'] = DisponerContratoDipForm()
                    data['invitacion'] = request.GET['invitacion']
                    template = get_template("dir_contratodip/modal/formcontrato.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editcontrato':
                try:
                    data['title'] = u'Editar Contrato'
                    data['filtro'] = filtro = ContratoDip.objects.get(pk=int(request.GET['id']))
                    data['totalCuotas'] = ContratoDipMetodoPago.objects.filter(status=True, contratodip=int(
                        request.GET['id'])).count()
                    form = ContratoDipForm(initial=model_to_dict(filtro))
                    form.fields['persona'].queryset = Persona.objects.filter(pk=filtro.persona.pk)
                    if filtro.materia:
                        form.fields['materia'].queryset = ProfesorMateria.objects.filter(pk=filtro.materia.pk)
                    data['form'] = form
                    return render(request, "adm_contratodip/editcontrato.html", data)
                except Exception as ex:
                    pass

            if action == 'historial':
                try:
                    data['title'] = u'Ver Historial'
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = ContratoDip.objects.get(pk=int(id))
                    data['detalle'] = HistorialContratoDip.objects.filter(status=True, contratodip=filtro).order_by('pk')
                    template = get_template("dir_contratodip/modal/historial.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


        else:
            data['title'] = u'Contratos Posgrado'
            search = None
            ids = None
            listado = InscripcionInvitacion.objects.filter(pasosproceso__finaliza=True,status=True,estado=2)
            if 's' in request.GET:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                if len(ss) == 1:
                    listado = listado.filter(Q(inscripcion__persona__apellido1__icontains=search) |
                                             Q(inscripcion__persona__apellido2__icontains=search) |
                                             Q(inscripcion__persona__nombres__icontains=search) |
                                             Q(inscripcion__persona__cedula__icontains=search)|
                                             Q(inscripcion__persona__email__icontains=search) |
                                             Q(inscripcion__persona__emailinst__icontains=search) )

                else:
                    listado = listado.filter(Q(inscripcion__persona__apellido1__icontains=search[0]) &
                                             Q(inscripcion__persona__apellido2__icontains=search[1])).distinct()
            elif 'id' in request.GET:
                ids = int(request.GET['id'])
                listado = listado.filter(id=ids)



            paging = MiPaginador(listado, 25)
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
            data['usuario'] = usuario
            data['page'] = page
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['listado'] = page.object_list
            data['totcount'] = listado.count()
            data['email_domain'] = EMAIL_DOMAIN
            data['fecha'] = datetime.now().date()
            return render(request, 'dir_contratodip/view.html', data)
