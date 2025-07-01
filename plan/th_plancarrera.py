# -*- coding: UTF-8 -*-
import json
import os
import io
import sys

import requests
import xlsxwriter
import xlwt
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.forms.models import model_to_dict
from django.template.loader import get_template
from openpyxl import load_workbook

from plan.forms import PeriodoPlanThForm, ModeloTrabajadorPlanThForm, ModeloOrganizacionPlanThForm, \
    DafoPersonaPlanThForm, PlanAccionPersonaPlanThForm, PerfilPuestoPeriodoForm, MovilidadCarreraPlanThForm, \
    MovilidadSucesionPlanThForm, ModeloGestionGenericoPlanThForm
from plan.models import PeriodoPlanTh, DireccionPeriodoPlanTh, PersonaPlanTh, DafoPersonaPlanTh, \
    PlanAccionPersonaPlanTh, ModeloGestionOrganizacionPlanTh, MedioPlanTh, ModeloGestionTrabajadorPlanTh, \
    MovilidadPersonaPlanTh, TipoLineaPlanTh
from postulate.models import PersonaAplicarPartida
from settings import EMAIL_DOMAIN
from sga.funciones import MiPaginador, log, generar_nombre

from datetime import datetime

import xlsxwriter
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse,HttpResponse
from django.shortcuts import render
from decorators import secure_module
from sagest.forms import ContratosForm
from sagest.models import Contratos, ContratosCamposSeleccion, \
    Departamento, DenominacionPuesto, OtroRegimenLaboral, PersonaContratos, DistributivoPersona, PerfilPuestoTh, PeriodoPerfilPuesto, DireccionPerfilPuesto
from sga.commonviews import adduserdata
from sga.funciones import log
from docx import Document
from docx.shared import Pt

from sga.models import Persona, NivelTitulacion


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addperiodo':
            try:
                with transaction.atomic():
                    if PeriodoPlanTh.objects.filter(fechainicio=request.POST['fechainicio'],fechafin=request.POST['fechafin'], status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'El registro ya existe.'}, safe=False)
                    form = PeriodoPlanThForm(request.POST)
                    if form.is_valid():
                        instance = PeriodoPlanTh(fechainicio=form.cleaned_data['fechainicio'],
                                                     fechafin=form.cleaned_data['fechafin'],
                                                     descripcion=form.cleaned_data['descripcion'],
                                                     estado=1)
                        instance.save(request)

                        log(u'Adicionó periodo de plan de carrera: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'editperiodo':
            try:
                with transaction.atomic():
                    periodo = PeriodoPlanTh.objects.get(pk=request.POST['id'])
                    form = PeriodoPlanThForm(request.POST)
                    if form.is_valid():
                        periodo.descripcion=form.cleaned_data['descripcion']
                        periodo.fechainicio=form.cleaned_data['fechainicio']
                        periodo.fechafin=form.cleaned_data['fechafin']
                        periodo.save(request)
                        log(u'Editó periodo %s' % (periodo), request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'editdafo':
            try:
                with transaction.atomic():
                    dafo = DafoPersonaPlanTh.objects.get(pk=request.POST['id'])
                    form = DafoPersonaPlanThForm(request.POST)
                    if form.is_valid():
                        dafo.tipo=form.cleaned_data['tipo']
                        dafo.descripcion=form.cleaned_data['descripcion']
                        dafo.save(request)
                        log(u'Editó dafo %s' % (dafo), request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'deleteperiodo':
            try:
                with transaction.atomic():
                    instancia = PeriodoPlanTh.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó periodo: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'deletedafo':
            try:
                with transaction.atomic():
                    instancia = DafoPersonaPlanTh.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó dafo: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'deleteplan':
            try:
                with transaction.atomic():
                    instancia = PlanAccionPersonaPlanTh.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó plan: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'editorganizacion':
            try:
                with transaction.atomic():
                    perfil = PersonaPlanTh.objects.get(pk=request.POST['id'])
                    form = ModeloOrganizacionPlanThForm(request.POST)
                    if form.is_valid():
                        perfil.organizacion=form.cleaned_data['organizacion']
                        perfil.save(request)
                        log(u'Asignó modelo de organización %s a perfil: %s' % (perfil.organizacion, perfil), request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'edittrabajador':
            try:
                with transaction.atomic():
                    perfil = PersonaPlanTh.objects.get(pk=request.POST['id'])
                    form = ModeloTrabajadorPlanThForm(request.POST)
                    if form.is_valid():
                        perfil.trabajador=form.cleaned_data['trabajador']
                        perfil.save(request)
                        log(u'Asignó modelo de trabajador %s a perfil: %s' % (perfil.trabajador, perfil), request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'guardartexto':
            try:
                with transaction.atomic():
                    perfil = PersonaPlanTh.objects.get(pk=request.POST['id'])
                    tipo = int(request.POST['tipo'])
                    dato = request.POST['dato'].strip().replace('  ', ' ')
                    if tipo == 1:
                        perfil.vision = dato
                    elif tipo == 2:
                        perfil.objetivo = dato
                    elif tipo==3:
                        perfil.comentarios = dato
                    perfil.save(request)
                    log(u'Editó texto: %s' % (dato), request, "add")
                    return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'adddafo':
            try:
                with transaction.atomic():
                    if DafoPersonaPlanTh.objects.filter(descripcion=request.POST['descripcion'], status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'El registro ya existe.'}, safe=False)
                    form = DafoPersonaPlanThForm(request.POST)
                    if form.is_valid():
                        instance = DafoPersonaPlanTh( descripcion=form.cleaned_data['descripcion'],
                                                      tipo=form.cleaned_data['tipo'],
                                                      persona_id=request.POST['id']
                                                      )
                        instance.save(request)

                        log(u'Adicionó periodo de plan de carrera: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'addmovcarrera':
            try:
                with transaction.atomic():
                    if MovilidadPersonaPlanTh.objects.filter(areaconocimiento=request.POST['areaconocimiento'],unidadorganizacional=request.POST['unidadorganizacional'],cargo=request.POST['cargo'],persona_id=request.POST['id'], status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'El registro ya existe.'}, safe=False)
                    form = MovilidadCarreraPlanThForm(request.POST)
                    if form.is_valid():
                        instance = MovilidadPersonaPlanTh( areaconocimiento=form.cleaned_data['areaconocimiento'],
                                                      unidadorganizacional=form.cleaned_data['unidadorganizacional'],
                                                      cargo=form.cleaned_data['cargo'],
                                                      persona_id=request.POST['id'],
                                                      tipo=1
                                                      )
                        instance.save(request)

                        log(u'Adicionó movilidad por carrera: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'editmovcarrera':
            try:
                with transaction.atomic():
                    instance = MovilidadPersonaPlanTh.objects.get(pk=request.POST['id'])
                    form = MovilidadCarreraPlanThForm(request.POST)
                    if form.is_valid():
                        instance.areaconocimiento = form.cleaned_data['areaconocimiento']
                        instance.unidadorganizacional = form.cleaned_data['unidadorganizacional']
                        instance.cargo = form.cleaned_data['cargo']
                        instance.save(request)
                        log(u'Edito Movilidad carrera plan carrera: %s' % (instance), request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'deletemovilidad':
            try:
                with transaction.atomic():
                    instancia = MovilidadPersonaPlanTh.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino organización plan de carrera: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'addmovsucesion':
            try:
                with transaction.atomic():
                    if MovilidadPersonaPlanTh.objects.filter(competencia=request.POST['competencia'],tipolinea=request.POST['tipolinea'],unidadorganizacional=request.POST['unidadorganizacional'],cargo=request.POST['cargo'],persona_id=request.POST['id'], status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'El registro ya existe.'}, safe=False)
                    form = MovilidadSucesionPlanThForm(request.POST)
                    if form.is_valid():
                        instance = MovilidadPersonaPlanTh( competencia=form.cleaned_data['competencia'],
                                                      tipolinea=form.cleaned_data['tipolinea'],
                                                      unidadorganizacional=form.cleaned_data['unidadorganizacional'],
                                                      cargo=form.cleaned_data['cargo'],
                                                      persona_id=request.POST['id'],
                                                      tipo=2
                                                      )
                        instance.save(request)

                        log(u'Adicionó movilidad por sucesion: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'editmovsucesion':
            try:
                with transaction.atomic():
                    instance = MovilidadPersonaPlanTh.objects.get(pk=request.POST['id'])
                    form = MovilidadSucesionPlanThForm(request.POST)
                    if form.is_valid():
                        instance.competencia = form.cleaned_data['competencia']
                        instance.tipolinea = form.cleaned_data['tipolinea']
                        instance.unidadorganizacional = form.cleaned_data['unidadorganizacional']
                        instance.cargo = form.cleaned_data['cargo']
                        instance.save(request)
                        log(u'Edito Movilidad carrera plan carrera: %s' % (instance), request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'detalle_plantilla':
            try:
                if 'id' in request.POST:
                    data['detallePlantilla'] = Contratos.objects.get(pk=request.POST['id'],status=True)
                    data['camposPlantilla'] = ContratosCamposSeleccion.objects.filter(contrato=request.POST['id'],status=True)
                    template = get_template("th_contrato/detalle_plantilla.html")
                    return JsonResponse({"result": 'ok', 'data': template.render(data)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'addplan':
            try:
                with transaction.atomic():
                    perfil = PersonaPlanTh.objects.get(pk=request.POST['id'])
                    if PlanAccionPersonaPlanTh.objects.filter(competencia=request.POST['competencia'],medio=request.POST['medio'],persona=perfil, status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'El registro ya existe.'}, safe=False)
                    form = PlanAccionPersonaPlanThForm(request.POST)
                    if form.is_valid():
                        instance = PlanAccionPersonaPlanTh(competencia=form.cleaned_data['competencia'],
                                                     medio=form.cleaned_data['medio'],
                                                     porcentaje_medio=form.cleaned_data['porcentaje_medio'],
                                                     tematica=form.cleaned_data['tematica'],
                                                     validacionplan=form.cleaned_data['validacionplan'],
                                                     evidencia=form.cleaned_data['evidencia'],
                                                     persona=perfil
                                                     )
                        instance.save(request)

                        log(u'Adicionó periodo de plan de carrera: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'editplan':
            try:
                with transaction.atomic():
                    plan = PlanAccionPersonaPlanTh.objects.get(pk=request.POST['id'])
                    form = PlanAccionPersonaPlanThForm(request.POST)
                    if form.is_valid():
                        plan.competencia=form.cleaned_data['competencia']
                        plan.medio=form.cleaned_data['medio']
                        plan.porcentaje_medio=form.cleaned_data['porcentaje_medio']
                        plan.tematica=form.cleaned_data['tematica']
                        plan.validacionplan=form.cleaned_data['validacionplan']
                        plan.evidencia=form.cleaned_data['evidencia']
                        plan.save(request)
                        log(u'Editó plan : %s' % (plan), request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'adddireccion':
            try:
                with transaction.atomic():
                    if not 'id' in request.POST:
                        raise NameError('Parametro id no encontrado')
                    if not 'direcciones' in request.POST:
                        raise NameError('Parametro de direcciones no encontrado')
                    periodo_id = int(request.POST['id'])
                    direcciones = json.loads(request.POST['direcciones'])
                    for direccion_id in direcciones:
                        direccionplan = DireccionPeriodoPlanTh(
                            direccion_id=int(direccion_id),
                            periodo_id=periodo_id
                        )
                        direccionplan.responsable = direccionplan.direccion.responsable
                        direccionplan.save(request)
                        log(u'Adicionó direccion de período plan carrera: %s' % direccionplan, request, "add")

                    return JsonResponse({"result": True, "mensaje": 'Se agregagaron correctamente las direcciones'}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": ex.__str__()}, safe=False)

        if action == 'deletedireccion':
            try:
                with transaction.atomic():
                    if not 'id' in request.POST:
                        raise NameError('Parametro id no encontrado')
                    id = int(request.POST['id'])
                    direccionplan = DireccionPeriodoPlanTh.objects.get(pk=id)
                    direccionplantemp = direccionplan
                    if direccionplan.personaplanth_set.filter(status=True).values_list('id', flat=True).exists():
                        raise NameError('El registro contiene uno o varios perfiles')
                    direccionplan.delete()
                    log(u'Eliminio direccion de período plan carrera: %s' % direccionplantemp, request, "del")
                    return JsonResponse({"result": True, "message": u'Se elimino correctamente la dirección %s'%(direccionplantemp)}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "message": ex.__str__()}, safe=False)

        if action == 'addperfil':
            try:
                with transaction.atomic():
                    if not 'id' in request.POST:
                        raise NameError('Parametro id no encontrado')
                    if not 'perfiles' in request.POST:
                        raise NameError('Parametro de perfiles no encontrado')
                    direccion_id = int(request.POST['id'])
                    perfiles = json.loads(request.POST['perfiles'])
                    for perfil_id in perfiles:
                        personadistributivo = DistributivoPersona.objects.get(pk=int(perfil_id))
                        personal = PersonaPlanTh(
                            direccion_id=int(direccion_id),
                            persona=personadistributivo.persona,
                            puesto=personadistributivo.denominacionpuesto,
                            escala=personadistributivo.escalaocupacional
                        )
                        personal.save(request)
                        log(u'Adicionó personal de plan de carrera: %s' %(personal), request, "add")

                    return JsonResponse({"result": True, "mensaje": 'Se agregagaron correctamente las direcciones'}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": ex.__str__()}, safe=False)

        if action == 'loadDataTablePerfilPuesto':
            try:
                txt_filter = request.POST['sSearch'] if request.POST['sSearch'] else ''
                limit = int(request.POST['iDisplayLength']) if request.POST['iDisplayLength'] else 25
                offset = int(request.POST['iDisplayStart']) if request.POST['iDisplayStart'] else 0
                tCount = 0
                if not 'id' in request.POST:
                    raise 'Parametro id no encontrado'
                id = int(request.POST['id'])
                perfiles = PerfilPuestoTh.objects.filter(direccion_id=id, status=True)
                if txt_filter:
                    search = txt_filter.strip()
                    perfiles = perfiles.filter(Q(codigo__icontains=search)|
                                               Q(denominacionpuesto__descripcion__icontains=search)|
                                               Q(denominacionperfil__puesto__descripcion__icontains=search)
                                               )
                tCount = perfiles.count()
                if offset == 0:
                    rows = perfiles[offset:limit]
                else:
                    rows = perfiles[offset:offset + limit]
                aaData = []
                for row in rows:
                    aaData.append([{'codigo': row.codigo,
                                    'denominacionpuesto': row.denominacionpuesto.__str__()
                                    },
                                    row.denominacionperfil.__str__(),
                                    row.get_nivel_display(),
                                   [area.__str__() for area in row.areas_de_conocimiento()],
                                   {
                                     'rol': row.escala.rol.descripcion,
                                     'grupoocupacional': row.escala.grupoocupacional.__str__(),
                                     'grado': row.escala.nivel.nivel.__str__(),
                                     'rmu': row.escala.rmu,
                                   },
                                   {
                                       'id': row.id,
                                       'nombre': row.__str__()
                                   }
                                   # [{'niveltitulo': p.niveltitulo.__str__(), 'meses_anios': p.meses_to_anio()} for p in row.denominacionperfil.nivelesexperiencia()]
                                   ])
                return JsonResponse({"result": "ok", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__(), "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        if action == 'savePuestoPerfil':
            try:
                with transaction.atomic():
                    if not 'id' in request.POST:
                        raise NameError('Parametro id no encontrado')
                    if not 'idperfil' in request.POST:
                        raise NameError('Parametro de idperfil no encontrado')
                    id = int(request.POST['id'])
                    idperfil = int(request.POST['idperfil'])
                    personaplan = PersonaPlanTh.objects.get(pk=idperfil)
                    personaplan.perfil_id = id
                    personaplan.save(request)
                    log(u'Actualizó perfil puesto : %s' %(personaplan), request, "edit")
                    return JsonResponse({"result": True, "mensaje": 'Se actualizo correctamente el perfil puesto'}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": ex.__str__()}, safe=False)

        if action == 'addorganizacionTh':
            try:
                with transaction.atomic():
                    if ModeloGestionOrganizacionPlanTh.objects.filter(descripcion=request.POST['descripcion'], status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'El registro ya existe.'}, safe=False)
                    form = ModeloGestionGenericoPlanThForm(request.POST)
                    if form.is_valid():
                        instance = ModeloGestionOrganizacionPlanTh(descripcion=form.cleaned_data['descripcion'],
                                                      activo=form.cleaned_data['activo'])
                        instance.save(request)
                        log(u'Adicionó organización de plan de carrera: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'editorganizacionTh':
            try:
                with transaction.atomic():
                    instance = ModeloGestionOrganizacionPlanTh.objects.get(pk=request.POST['id'])
                    form = ModeloGestionGenericoPlanThForm(request.POST)
                    if form.is_valid():
                        instance.descripcion=form.cleaned_data['descripcion']
                        instance.activo=form.cleaned_data['activo']
                        instance.save(request)
                        log(u'Edito organización plan carrera: %s' % (instance), request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'deleteorganizacionTh':
            try:
                with transaction.atomic():
                    instancia = ModeloGestionOrganizacionPlanTh.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino organización plan de carrera: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'addtrabajadorTh':
            try:
                with transaction.atomic():
                    if ModeloGestionTrabajadorPlanTh.objects.filter(descripcion=request.POST['descripcion'], status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'El registro ya existe.'}, safe=False)
                    form = ModeloGestionGenericoPlanThForm(request.POST)
                    if form.is_valid():
                        instance = ModeloGestionTrabajadorPlanTh(descripcion=form.cleaned_data['descripcion'],
                                                      activo=form.cleaned_data['activo'])
                        instance.save(request)
                        log(u'Adicionó trabajo de plan de carrera: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'edittrabajadorTh':
            try:
                with transaction.atomic():
                    instance = ModeloGestionTrabajadorPlanTh.objects.get(pk=request.POST['id'])
                    form = ModeloGestionGenericoPlanThForm(request.POST)
                    if form.is_valid():
                        instance.descripcion=form.cleaned_data['descripcion']
                        instance.activo=form.cleaned_data['activo']
                        instance.save(request)
                        log(u'Edito trabajo plan carrera: %s' % (instance), request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'deletetrabajadorTh':
            try:
                with transaction.atomic():
                    instancia = ModeloGestionTrabajadorPlanTh.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino trabajo plan de carrera: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'addmedioTh':
            try:
                with transaction.atomic():
                    if MedioPlanTh.objects.filter(descripcion=request.POST['descripcion'], status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'El registro ya existe.'}, safe=False)
                    form = ModeloGestionGenericoPlanThForm(request.POST)
                    if form.is_valid():
                        instance = MedioPlanTh(descripcion=form.cleaned_data['descripcion'],
                                                      activo=form.cleaned_data['activo'])
                        instance.save(request)
                        log(u'Adicionó medio de plan de carrera: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'editmedioTh':
            try:
                with transaction.atomic():
                    instance = MedioPlanTh.objects.get(pk=request.POST['id'])
                    form = ModeloGestionGenericoPlanThForm(request.POST)
                    if form.is_valid():
                        instance.descripcion=form.cleaned_data['descripcion']
                        instance.activo=form.cleaned_data['activo']
                        instance.save(request)
                        log(u'Edito medio plan carrera: %s' % (instance), request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'deletemedioTh':
            try:
                with transaction.atomic():
                    instancia = MedioPlanTh.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino medio plan de carrera: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'addtipolineaTh':
            try:
                with transaction.atomic():
                    if TipoLineaPlanTh.objects.filter(descripcion=request.POST['descripcion'], status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'El registro ya existe.'}, safe=False)
                    form = ModeloGestionGenericoPlanThForm(request.POST)
                    if form.is_valid():
                        instance = TipoLineaPlanTh(descripcion=form.cleaned_data['descripcion'],
                                               activo=form.cleaned_data['activo'])
                        instance.save(request)
                        log(u'Adicionó medio de plan de carrera: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'edittipolineaTh':
            try:
                with transaction.atomic():
                    instance = TipoLineaPlanTh.objects.get(pk=request.POST['id'])
                    form = ModeloGestionGenericoPlanThForm(request.POST)
                    if form.is_valid():
                        instance.descripcion = form.cleaned_data['descripcion']
                        instance.activo = form.cleaned_data['activo']
                        instance.save(request)
                        log(u'Edito medio plan carrera: %s' % (instance), request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'deletetipolineaTh':
            try:
                with transaction.atomic():
                    instancia = TipoLineaPlanTh.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino medio plan de carrera: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'activardasactivarregistro':
            try:
                with transaction.atomic():
                    app_label = request.POST['app_label']
                    model_name = request.POST['model_name']
                    val = request.POST['val']
                    id = int(request.POST['id'])
                    contentype = ContentType.objects.get_by_natural_key(app_label, model_name)
                    model_class = contentype.model_class()
                    instance = model_class.objects.get(pk=id)
                    instance.activo = val == 'y'
                    instance.save(request)
                    log(u'Actualizó estado del modelo %s plan de carrera: %s -> %s' % (instance._meta.model_name, instance, instance.activo), request, "edit")
                    res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'cambiaritemmenu':
            itemanterior = request.session['viewmenuconfiguracionactivo']
            try:
                with transaction.atomic():
                    item = int(request.POST['item'])
                    request.session['viewmenuconfiguracionactivo'] = item
                res_json = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                request.session['viewmenuconfiguracionactivo'] = itemanterior
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addperiodo':
                try:
                    form = PeriodoPlanThForm()
                    data['form'] = form
                    template = get_template("th_plancarrera/modal/formperiodo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editperiodo':
                try:
                    data['filtro'] = periodo = PeriodoPlanTh.objects.get(pk=request.GET['id'])
                    data['form'] = PeriodoPlanThForm(initial=model_to_dict(periodo))
                    template = get_template("th_plancarrera/modal/formperiodo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editdafo':
                try:
                    data['filtro'] = dafo = DafoPersonaPlanTh.objects.get(pk=request.GET['id'])
                    data['form'] = DafoPersonaPlanThForm(initial=model_to_dict(dafo))
                    template = get_template("th_plancarrera/modal/formdafo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'adddireccion':
                try:
                    usados = DireccionPeriodoPlanTh.objects.values_list('direccion_id', flat=True).filter(status=True,periodo_id=request.GET['id'])
                    data['periodo_id'] = request.GET['id']
                    data['direcciones'] = Departamento.objects.filter(status=True, integrantes__isnull=False).distinct().exclude(pk__in=usados)
                    template = get_template('th_plancarrera/modal/direcciones.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editorganizacion':
                try:
                    form = ModeloOrganizacionPlanThForm()
                    data['form'] = form
                    data['filtro'] = PersonaPlanTh.objects.get(pk=request.GET['id'])
                    template = get_template("th_plancarrera/modal/formmodelo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'edittrabajador':
                try:
                    form = ModeloTrabajadorPlanThForm()
                    data['form'] = form
                    data['filtro'] = PersonaPlanTh.objects.get(pk=request.GET['id'])
                    template = get_template("th_plancarrera/modal/formmodelo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addplan':
                try:
                    form = PlanAccionPersonaPlanThForm()
                    data['form'] = form
                    data['filtro'] = PersonaPlanTh.objects.get(pk=int(request.GET['id']))
                    template = get_template("th_plancarrera/modal/formplan.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addmovcarrera':
                try:
                    form = MovilidadCarreraPlanThForm()
                    data['form'] = form
                    data['filtro'] = PersonaPlanTh.objects.get(pk=int(request.GET['id']))
                    template = get_template("th_plancarrera/modal/formmovilidad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editmovcarrera':
                try:
                    data['filtro'] = filtro = MovilidadPersonaPlanTh.objects.get(pk=request.GET['id'])
                    form = MovilidadCarreraPlanThForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("th_plancarrera/modal/formmovilidad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addmovsucesion':
                try:
                    form = MovilidadSucesionPlanThForm()
                    data['form'] = form
                    data['filtro'] = PersonaPlanTh.objects.get(pk=int(request.GET['id']))
                    template = get_template("th_plancarrera/modal/formmovilidad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editmovsucesion':
                try:
                    data['filtro'] = filtro = MovilidadPersonaPlanTh.objects.get(pk=request.GET['id'])
                    form = MovilidadSucesionPlanThForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("th_plancarrera/modal/formmovilidad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editplan':
                try:
                    data['filtro'] = plan = PlanAccionPersonaPlanTh.objects.get(pk=request.GET['id'])
                    form = PlanAccionPersonaPlanThForm(initial=model_to_dict(plan))
                    data['form'] = form
                    template = get_template("th_plancarrera/modal/formplan.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'direcciones':
                try:
                    data['periodo'] =  periodo = PeriodoPlanTh.objects.get(pk=int(request.GET['idp']))
                    data['title'] = u'Unidades organizacionales'
                    url_vars = '&action=direcciones&idp=%s' % request.GET['idp']
                    filtro = (Q(periodo=periodo,status=True))
                    search = None
                    ids = None

                    if 's' in request.GET:
                        search = request.GET['s']
                        filtro = filtro & (Q(direccion__nombre__icontains=search) |
                                           Q(descripcion__icontains=search))
                        url_vars += '&s=' + search

                    direcciones = DireccionPeriodoPlanTh.objects.filter(filtro).order_by('-id')

                    paging = MiPaginador(direcciones, 25)
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
                    data['url_vars'] = url_vars
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['direcciones'] = page.object_list
                    return render(request, "th_plancarrera/viewdireccion.html", data)
                except Exception as ex:
                    pass

            if action == 'perfiles':
                try:
                    data['periodo'] = direccion = DireccionPeriodoPlanTh.objects.get(pk=int(request.GET['idd']))
                    data['title'] = u'Perfiles'
                    url_vars = ''
                    filtro = (Q(direccion=direccion,status=True))
                    search = None
                    ids = None

                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(persona__nombres__icontains=search) |
                                               Q(persona__apellido1__icontains=search) |
                                               Q(persona__apellido2__icontains=search) |
                                               Q(persona__pasaporte__icontains=search) |
                                               Q(persona__cedula__icontains=search)
                                               )
                        else:
                            filtro = filtro & (
                                        (Q(persona__nombres__icontains=ss[0]) & Q(persona__nombres__icontains=ss[1])) |
                                        (Q(persona__apellido1__icontains=ss[0]) &
                                         Q(persona__apellido2__icontains=ss[1])) |
                                         Q(persona__pasaporte__icontains=ss[0])|
                                        Q(persona__cedula__icontains=ss[0]))
                        url_vars += '&s=' + search

                    perfiles = PersonaPlanTh.objects.filter(filtro).order_by('-id')

                    paging = MiPaginador(perfiles, 25)
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
                    data['perfiles'] = page.object_list
                    return render(request, "th_plancarrera/viewpersonal.html", data)
                except Exception as ex:
                    pass

            if action == 'addperfil':
                try:
                    if not 'id' in request.GET:
                        raise NameError('parametro id no encontrado')
                    id = int(request.GET['id'])
                    direccion = DireccionPeriodoPlanTh.objects.get(pk=id)
                    data['direccion'] = direccion
                    template = get_template('th_plancarrera/modal/perfiles.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': ex.__str__()})

            if action == 'configurar':
                try:
                    data['title'] = u'Configuraciones'
                    hoy = datetime.now().date()
                    if 'tab' in request.GET:
                        data['tab'] = request.GET['tab']

                    if not 'viewmenuconfiguracionactivo' in request.session:
                        request.session['viewmenuconfiguracionactivo'] = 1
                    # data['perfil'] = perfil = PersonaPlanTh.objects.get(pk=request.GET['id'])
                    data['organizacion'] = ModeloGestionOrganizacionPlanTh.objects.filter(status=True).order_by('-id')
                    data['trabajador'] = ModeloGestionTrabajadorPlanTh.objects.filter(status=True).order_by('-id')
                    data['medio'] = MedioPlanTh.objects.filter(status=True).order_by('-id')
                    data['tipo'] = TipoLineaPlanTh.objects.filter(status=True).order_by('-id')

                    return render(request, 'th_plancarrera/viewconfigurar.html', data)
                except Exception as ex:
                    pass

            if action == 'addorganizacionTh':
                try:
                    form = ModeloGestionGenericoPlanThForm()
                    data['form'] = form
                    template = get_template('th_plancarrera/modal/formconfigurar.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': ex.__str__()})

            if action == 'editorganizacionTh':
                try:
                    data['filtro'] = filtro = ModeloGestionOrganizacionPlanTh.objects.get(pk=request.GET['id'])
                    form = ModeloGestionGenericoPlanThForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("th_plancarrera/modal/formmodelo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addtrabajadorTh':
                try:
                    form = ModeloGestionGenericoPlanThForm()
                    data['form'] = form
                    template = get_template('th_plancarrera/modal/formconfigurar.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': ex.__str__()})

            if action == 'edittrabajadorTh':
                try:
                    data['filtro'] = filtro = ModeloGestionTrabajadorPlanTh.objects.get(pk=request.GET['id'])
                    form = ModeloGestionGenericoPlanThForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("th_plancarrera/modal/formmodelo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addmedioTh':
                try:
                    form = ModeloGestionGenericoPlanThForm()
                    data['form'] = form
                    template = get_template('th_plancarrera/modal/formconfigurar.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': ex.__str__()})

            if action == 'editmedioTh':
                try:
                    data['filtro'] = filtro = MedioPlanTh.objects.get(pk=request.GET['id'])
                    form = ModeloGestionGenericoPlanThForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("th_plancarrera/modal/formmodelo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addtipolineaTh':
                try:
                    form = ModeloGestionGenericoPlanThForm()
                    data['form'] = form
                    template = get_template('th_plancarrera/modal/formconfigurar.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': ex.__str__()})

            if action == 'edittipolineaTh':
                try:
                    data['filtro'] = filtro = TipoLineaPlanTh.objects.get(pk=request.GET['id'])
                    form = ModeloGestionGenericoPlanThForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("th_plancarrera/modal/formmodelo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'ficha':
                try:
                    data['title'] = u'Hoja de Vida'
                    hoy = datetime.now().date()
                    if 'tab' in request.GET:
                        data['tab'] = request.GET['tab']
                    data['perfil'] = perfil = PersonaPlanTh.objects.get(pk=request.GET['id'])
                    # data['otrascertificaciones'] = CertificadoIdioma.objects.filter(status=True,
                    #                                                                 persona=persona).order_by('id')
                    data['niveltitulo'] = NivelTitulacion.objects.filter(pk__in=[1,2,3,4], status=True).order_by('-rango')
                    dafo = DafoPersonaPlanTh.objects.filter(persona=perfil, status=True).order_by('-id')
                    data['debilidades'] = dafo.filter(tipo=1)
                    data['amenazas'] = dafo.filter(tipo=2)
                    data['fortalezas'] = dafo.filter(tipo=3)
                    data['oportunidades'] = dafo.filter(tipo=4)
                    movilidad = MovilidadPersonaPlanTh.objects.filter(persona=perfil, status=True)
                    data['movilidadcarrera'] = movilidad.filter(tipo=1)
                    data['movilidadsucesion'] = movilidad.filter(tipo=2)

                    # data['solicitudes'] = SolicitudPublicacion.objects.filter(persona=persona, aprobado=False,
                    #                                                           status=True).order_by('-fecha_creacion')
                    # data['numpartidas'] = Partida.objects.filter(status=True, convocatoria__vigente=True,
                    #                                              convocatoria__finicio__lte=hoy,
                    #                                              convocatoria__ffin__gte=hoy, vigente=True).count()

                    return render(request, "th_plancarrera/viewperfil.html", data)
                except Exception as ex:
                    pass

            if action == 'adddafo':
                try:
                    form = DafoPersonaPlanThForm()
                    data['filtro'] = PersonaPlanTh.objects.get(pk=int(request.GET['id']))
                    data['form'] = form
                    template = get_template("th_plancarrera/modal/formdafo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'loadFormPerfilPuesto':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['new', 'edit', 'view'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    ultimoperiodo = PeriodoPerfilPuesto.objects.filter(status=True).order_by('fecha_creacion').first()
                    form = PerfilPuestoPeriodoForm()#{'periodopuesto': ultimoperiodo}
                    form.editar()
                    data['personaplan'] = PersonaPlanTh.objects.get(pk=int(request.GET['id']))
                    data['form'] = form
                    template = get_template("th_plancarrera/modal/formperfilpuesto.html")
                    return JsonResponse({"result": True, 'data': template.render(data, request=request)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': ex.__str__()})

            if action == 'buscardireccionesperiodopuesto':
                try:
                    id = request.GET.get('id')
                    #filtro = CategoriaPlantillas.objects.get(pk=id)
                    listado = DireccionPerfilPuesto.objects.filter(periodo_id=id, status=True, activo=True)
                    if 'search' in request.GET:
                        search = request.GET['search']
                        listado = listado.filter(Q(direccion__nombre__icontains=search))
                    resp = [{'id': x.pk, 'text': f'{x.__str__()}'} for x in listado]
                    return JsonResponse({"result": True, 'data': resp})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': ex.__str__()})

            return HttpResponseRedirect(request.path)
        else:

            data['title'] = u'Periodos en plan de carrera'
            request.session['viewmenuconfiguracionactivo'] = 1
            url_vars = ''
            filtro = Q(status=True)
            search = None
            ids = None

            if 's' in request.GET:

                search = request.GET['s'].strip()
                filtro = filtro & ( Q(descripcion__icontains=search))
                url_vars += '&s=' + search

            periodos = PeriodoPlanTh.objects.filter(filtro).order_by('-id')

            paging = MiPaginador(periodos, 20)
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
            data["url_vars"] = url_vars
            data['ids'] = ids if ids else ""
            data['planes'] = page.object_list
            return render(request, 'th_plancarrera/view.html', data)
