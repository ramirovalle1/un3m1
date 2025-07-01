# -*- coding: UTF-8 -*-
import json
import random
from datetime import datetime

import os
import xlrd
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import transaction, connection
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import RequestContext, Context
from django.template.loader import get_template
from openpyxl import load_workbook
from xlwt import *
from xlwt import easyxf
import xlwt

from decorators import secure_module
from postulate.models import PersonaAplicarPartida
from sagest.forms import DistributivoPersonaForm
from sagest.models import DistributivoPersona, RegimenLaboral, NivelOcupacional, ModalidadLaboral, EstadoPuesto, \
    EscalaOcupacional, DenominacionPuesto, PuestoAdicional, Departamento, EstructuraProgramatica, \
    DistributivoPersonaHistorial
from settings import EMAIL_DOMAIN, ARCHIVO_TIPO_GENERAL, SEXO_MASCULINO, \
    EMAIL_INSTITUCIONAL_AUTOMATICO, PROFESORES_GROUP_ID, SITE_STORAGE
from sga.commonviews import adduserdata
from sga.forms import ImportarArchivoXLSForm
from sga.funciones import MiPaginador, log, generar_nombre, calculate_username, generar_usuario, variable_valor, \
    convertir_fecha
from sga.models import Archivo, Persona, Provincia, Canton, Administrativo, Profesor, Coordinacion, \
    TiempoDedicacionDocente, miinstitucion, CUENTAS_CORREOS, Titulacion
from sga.tasks import send_html_mail, conectar_cuenta
from settings import MEDIA_ROOT,MEDIA_URL
import io
import xlsxwriter
from urllib.request import urlopen

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

        if action == 'add':
            try:
                form = DistributivoPersonaForm(request.POST)
                if form.is_valid():
                    administrativo = Administrativo.objects.get(status=True, id=form.cleaned_data['persona'])
                    if DistributivoPersona.objects.filter(persona=administrativo.persona,
                                                          regimenlaboral=form.cleaned_data['regimenlaboral'],
                                                          status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})

                    distributivopersona = DistributivoPersona(persona=administrativo.persona,
                                                              regimenlaboral=form.cleaned_data['regimenlaboral'],
                                                              nivelocupacional=form.cleaned_data['nivelocupacional'],
                                                              modalidadlaboral=form.cleaned_data['modalidadlaboral'],
                                                              partidaindividual=form.cleaned_data['partidaindividual'],
                                                              estadopuesto=form.cleaned_data['estadopuesto'],
                                                              grado=form.cleaned_data['grado'],
                                                              rmuescala=Decimal(form.cleaned_data['rmuescala']).quantize(Decimal('.01')),
                                                              rmupuesto=Decimal(form.cleaned_data['rmupuesto']).quantize(Decimal('.01')),
                                                              rmusobrevalorado=Decimal(form.cleaned_data['rmupuesto']).quantize(Decimal('.01')),
                                                              escalaocupacional=form.cleaned_data['escalaocupacional'],
                                                              rucpatronal=form.cleaned_data['rucpatronal'],
                                                              codigosucursal=form.cleaned_data['codigosucursal'],
                                                              tipoidentificacion=form.cleaned_data['tipoidentificacion'],
                                                              denominacionpuesto=form.cleaned_data['denominacionpuesto'],
                                                              puestoadicinal=form.cleaned_data['puestoadicinal'],
                                                              unidadorganica=form.cleaned_data['unidadorganica'],
                                                              aporteindividual=Decimal(form.cleaned_data['aporteindividual']).quantize(Decimal('.01')),
                                                              aportepatronal=Decimal(form.cleaned_data['aportepatronal']).quantize(Decimal('.01')),
                                                              estructuraprogramatica=form.cleaned_data['estructuraprogramatica'],
                                                              comisioservicios=form.cleaned_data['comisioservicios'])
                    distributivopersona.save(request)
                    log(u'Nuevo distributivo personal: %s' % distributivopersona, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'edit':
            try:
                form = DistributivoPersonaForm(request.POST)
                if form.is_valid():
                    distributivopersona = DistributivoPersona.objects.filter(pk=int(request.POST['id']))[0]
                    if DistributivoPersona.objects.filter(persona=distributivopersona.persona,
                                                          regimenlaboral=form.cleaned_data['regimenlaboral'],
                                                          status=True).exclude(pk=int(request.POST['id'])).exists():
                        return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})

                    # distributivopersona.persona_id=form.cleaned_data['persona']
                    distributivopersona.regimenlaboral=form.cleaned_data['regimenlaboral']
                    distributivopersona.nivelocupacional=form.cleaned_data['nivelocupacional']
                    distributivopersona.modalidadlaboral=form.cleaned_data['modalidadlaboral']
                    distributivopersona.partidaindividual=form.cleaned_data['partidaindividual']
                    distributivopersona.estadopuesto=form.cleaned_data['estadopuesto']
                    distributivopersona.grado=form.cleaned_data['grado']
                    distributivopersona.rmuescala=Decimal(form.cleaned_data['rmuescala']).quantize(Decimal('.01'))
                    distributivopersona.rmupuesto=Decimal(form.cleaned_data['rmupuesto']).quantize(Decimal('.01'))
                    distributivopersona.rmusobrevalorado=Decimal(form.cleaned_data['rmupuesto']).quantize(Decimal('.01'))
                    distributivopersona.escalaocupacional=form.cleaned_data['escalaocupacional']
                    distributivopersona.rucpatronal=form.cleaned_data['rucpatronal']
                    distributivopersona.codigosucursal=form.cleaned_data['codigosucursal']
                    distributivopersona.tipoidentificacion=form.cleaned_data['tipoidentificacion']
                    distributivopersona.denominacionpuesto=form.cleaned_data['denominacionpuesto']
                    distributivopersona.puestoadicinal=form.cleaned_data['puestoadicinal']
                    distributivopersona.unidadorganica=form.cleaned_data['unidadorganica']
                    distributivopersona.aporteindividual=Decimal(form.cleaned_data['aporteindividual']).quantize(Decimal('.01'))
                    distributivopersona.aportepatronal=Decimal(form.cleaned_data['aportepatronal']).quantize(Decimal('.01'))
                    distributivopersona.estructuraprogramatica=form.cleaned_data['estructuraprogramatica']
                    distributivopersona.comisioservicios=form.cleaned_data['comisioservicios']
                    distributivopersona.save(request)
                    log(u'Modificacion distributivo personal: %s' % distributivopersona, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'importar':
                try:
                    data['title'] = u'Importar datos del sistema de gobierno'
                    data['form'] = ImportarArchivoXLSForm()
                    return render(request, "th_plantilla/importar.html", data)
                except Exception as ex:
                    pass

            if action == 'add':
                try:
                    data['title'] = u'Adicionar distributivo del personal'
                    data['form'] = DistributivoPersonaForm()
                    return render(request, "th_plantilla/add.html", data)
                except:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar distributivo Personal'
                    data['distributivopersona'] = distributivopersona = DistributivoPersona.objects.filter(pk=request.GET['id'])[0]
                    form = DistributivoPersonaForm(initial={'regimenlaboral': distributivopersona.regimenlaboral,
                                                            'nivelocupacional': distributivopersona.nivelocupacional,
                                                            'modalidadlaboral': distributivopersona.modalidadlaboral,
                                                            'partidaindividual': distributivopersona.partidaindividual,
                                                            'estadopuesto': distributivopersona.estadopuesto,
                                                            'grado': distributivopersona.grado,
                                                            'rmuescala': distributivopersona.rmuescala,
                                                            'rmupuesto': distributivopersona.rmupuesto,
                                                            'rmusobrevalorado': distributivopersona.rmusobrevalorado,
                                                            'escalaocupacional': distributivopersona.escalaocupacional,
                                                            'rucpatronal': distributivopersona.rucpatronal,
                                                            'codigosucursal': distributivopersona.codigosucursal,
                                                            'tipoidentificacion': distributivopersona.tipoidentificacion,
                                                            'denominacionpuesto': distributivopersona.denominacionpuesto,
                                                            'puestoadicinal': distributivopersona.puestoadicinal,
                                                            'unidadorganica': distributivopersona.unidadorganica,
                                                            'aporteindividual': distributivopersona.aporteindividual,
                                                            'aportepatronal': distributivopersona.aportepatronal,
                                                            'estructuraprogramatica': distributivopersona.estructuraprogramatica,
                                                            'comisioservicios': distributivopersona.comisioservicios})
                    form.edit(distributivopersona)
                    data['form'] = form
                    return render(request, "th_plantilla/edit.html", data)
                except:
                    pass



            return HttpResponseRedirect(request.path)
        else:

            data['title'] = u'Validar documentos'
            url_vars = ''
            filtro = Q(status=True,esganador=True,)
            search = None
            ids = None

            if 's' in request.GET:

                search = request.GET['s'].strip()
                ss = search.split(' ')
                if len(ss) == 1:
                    filtro = filtro & (Q(persona__nombres__icontains=search) |
                                       Q(persona__apellido1__icontains=search) |
                                       Q(persona__apellido2__icontains=search) |
                                       Q(persona__cedula__icontains=search))
                else:
                    filtro = filtro & ((Q(persona__nombres__icontains=ss[0]) & Q(persona__nombres__icontains=ss[1])) |
                                       (Q(persona__apellido1__icontains=ss[0]) &
                                        Q(persona__apellido2__icontains=ss[1])) |
                                       Q(persona__cedula__icontains=ss[0]))

                    if request.GET['s'] != '':
                        search = request.GET['s']

                if search:
                    filtro = filtro & (Q(persona__nombres__icontains=search) |
                                       Q(persona__apellido1__icontains=search) |
                                       Q(persona__apellido2__icontains=search) |
                                       Q(persona__cedula__icontains=search) )
                url_vars += '&s=' + search

            # contratos = ContratoPersona.objects.filter(filtro, contrato__anio=anioselect)
            contratos = PersonaAplicarPartida.objects.filter(filtro)

            paging = MiPaginador(contratos, 20)
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
            data['search'] = search if search else ""
            data["url_vars"] = url_vars
            data['ids'] = ids if ids else ""
            data['candidatos'] = page.object_list
            return render(request, 'th_revisadocumento/view.html', data)
