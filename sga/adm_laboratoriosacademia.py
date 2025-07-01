# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from decorators import secure_module, last_access
from sagest.models import ActivoFijo
from sga.commonviews import adduserdata
from sga.forms import LaboratorioAcademiaForm, InventarioLaboratorioAcademiaForm, ResponsableLaboratorioAcademiaForm, \
    PlanMantenimientoLaboratorioForm, InventarioLaboratorioAcademiaMaterialForm, NormativaLaboratorioAcademiaForm, InventarioLaboratorioEquipoForm, InventarioLaboratorioInsumoForm
from sga.funciones import MiPaginador, log, generar_nombre
from sga.models import LaboratorioAcademia, InventarioLaboratorioAcademia, ResponsableLaboratorioAcademia, \
    PlanMantenimientoLaboratorio, NormativaLaboratorioAcademia, TipoLaboratorio, AreaConocimientoTitulacion, \
    SubAreaConocimientoTitulacion, SubAreaEspecificaConocimientoTitulacion, Coordinacion, Carrera
from xlwt import easyxf
import random
from django.shortcuts import render
from decorators import secure_module
from django.forms.models import model_to_dict
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdfsaveqrcertificado, conviert_html_to_pdfsave
from xlwt import *

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = LaboratorioAcademiaForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})

                if f.is_valid():
                    laboratorioacademia = LaboratorioAcademia(nombre=f.cleaned_data['nombre'],
                                                              aula=f.cleaned_data['aula'],
                                                              capacidad=f.cleaned_data['capacidad'],
                                                              metroscuadrado=f.cleaned_data['metroscuadrado'],
                                                              tipo=f.cleaned_data['tipo'],
                                                              tipolaboratorio=f.cleaned_data['tipolaboratorio'],
                                                              estado=f.cleaned_data['estado'],
                                                              ubicacion=f.cleaned_data['ubicacion'],
                                                              coordinacion=f.cleaned_data['coordinacion'],
                                                              # nro_estudiantes=f.cleaned_data['nro_estudiantes'],
                                                              nro_equipos=f.cleaned_data['nro_equipos'],
                                                              fecha_inicio_utilizacion=f.cleaned_data['fecha_inicio_utilizacion'],
                                                              fecha_fin_utilizacion=f.cleaned_data['fecha_fin_utilizacion'],
                                                              carrera=f.cleaned_data['carrera'],
                                                              campo_amplio=f.cleaned_data['campo_amplio'],
                                                              campo_especifico=f.cleaned_data['campo_especifico'],
                                                              campo_detallado=f.cleaned_data['campo_detallado'],
                                                              )
                    laboratorioacademia.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            newfile._name = generar_nombre("laboratorioacademia_", newfile._name)
                            laboratorioacademia.archivo = newfile
                            laboratorioacademia.save(request)

                    log(u'Adiciono Laboratorio Academico: %s' % laboratorioacademia, request, "add")
                    return JsonResponse({"result": "ok", "id": laboratorioacademia.id})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                laboratorioacademia = LaboratorioAcademia.objects.get(pk=request.POST['id'])
                f = LaboratorioAcademiaForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})

                if f.is_valid():
                    laboratorioacademia.nombre = f.cleaned_data['nombre']
                    laboratorioacademia.aula = f.cleaned_data['aula']
                    laboratorioacademia.capacidad = f.cleaned_data['capacidad']
                    laboratorioacademia.metroscuadrado = f.cleaned_data['metroscuadrado']
                    laboratorioacademia.tipo = f.cleaned_data['tipo']
                    laboratorioacademia.tipolaboratorio= f.cleaned_data['tipolaboratorio']
                    laboratorioacademia.estado = f.cleaned_data['estado']
                    laboratorioacademia.ubicacion = f.cleaned_data['ubicacion']
                    laboratorioacademia.coordinacion = f.cleaned_data['coordinacion']
                    # laboratorioacademia.nro_estudiantes = f.cleaned_data['nro_estudiantes']
                    laboratorioacademia.carrera = f.cleaned_data['carrera']
                    laboratorioacademia.nro_equipos=f.cleaned_data['nro_equipos']
                    laboratorioacademia.fecha_inicio_utilizacion = f.cleaned_data['fecha_inicio_utilizacion']
                    laboratorioacademia.fecha_fin_utilizacion = f.cleaned_data['fecha_fin_utilizacion']
                    laboratorioacademia.campo_amplio = f.cleaned_data['campo_amplio']
                    laboratorioacademia.campo_especifico = f.cleaned_data['campo_especifico']
                    laboratorioacademia.campo_detallado = f.cleaned_data['campo_detallado']
                    laboratorioacademia.save(request)
                    log(u'Modifico Laboratorio Academico: %s' % laboratorioacademia, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addinventario':
            try:
                f = InventarioLaboratorioAcademiaForm(request.POST)
                if f.is_valid():
                    laboratorioacademia = LaboratorioAcademia.objects.filter(pk=request.POST['idlaboratorio'], status=True)[0]
                    inventariolaboratorioacademia = InventarioLaboratorioAcademia(laboratorio=laboratorioacademia,
                                                                                  activo_id=f.cleaned_data['activo'],
                                                                                  observacion=f.cleaned_data['observacion'],
                                                                                  fechadesde=f.cleaned_data['fechadesde'],
                                                                                  fechahasta=f.cleaned_data['fechahasta'],
                                                                                  vigente=f.cleaned_data['vigente'])
                    inventariolaboratorioacademia.save(request)
                    log(u'Adiciono Inventario Laboratorio Academico: %s' % inventariolaboratorioacademia, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editinventario':
            try:
                inventariolaboratorioacademia = InventarioLaboratorioAcademia.objects.get(pk=request.POST['id'])
                f = InventarioLaboratorioAcademiaForm(request.POST)
                if f.is_valid():
                    # inventariolaboratorioacademia.activo = f.cleaned_data['activo']
                    inventariolaboratorioacademia.observacion = f.cleaned_data['observacion']
                    inventariolaboratorioacademia.fechadesde = f.cleaned_data['fechadesde']
                    inventariolaboratorioacademia.fechahasta = f.cleaned_data['fechahasta']
                    inventariolaboratorioacademia.vigente = f.cleaned_data['vigente']
                    inventariolaboratorioacademia.save(request)
                    log(u'Modifico Inventario Laboratorio Academico: %s' % inventariolaboratorioacademia, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteinventario':
            try:
                id = int(request.POST['id'])
                data['filtro'] = filtro = InventarioLaboratorioAcademia.objects.filter(pk=int(id), status=True).first()
                if not filtro:
                    raise NameError('Registro no encontrado')
                log(u'Elimino Inventario Laboratorio Academico: %s' % filtro, request, "del")
                filtro.delete()
                return JsonResponse({'error': False, 'mensaje': u'Registro eliminado con éxito!'})
            except Exception as ex:
                return JsonResponse({'error': True, 'mensaje': ex})

        elif action == 'addinventarioproducto':
            try:
                f = InventarioLaboratorioAcademiaMaterialForm(request.POST)
                if f.is_valid():
                    laboratorioacademia = LaboratorioAcademia.objects.filter(pk=request.POST['idlaboratorio'], status=True)[0]
                    inventariolaboratorioacademia = InventarioLaboratorioAcademia(laboratorio=laboratorioacademia,
                                                                                  producto_id=f.cleaned_data['producto'],
                                                                                  observacion=f.cleaned_data['observacion'],
                                                                                  cantidad=f.cleaned_data['cantidad'],
                                                                                  fechadesde=f.cleaned_data['fechadesde'],
                                                                                  fechahasta=f.cleaned_data['fechahasta'],
                                                                                  vigente=f.cleaned_data['vigente'])
                    inventariolaboratorioacademia.save(request)
                    log(u'Adiciono Inventario Laboratorio Academico: %s' % inventariolaboratorioacademia, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editinventarioproducto':
            try:
                inventariolaboratorioacademia = InventarioLaboratorioAcademia.objects.get(pk=request.POST['id'])
                f = InventarioLaboratorioAcademiaMaterialForm(request.POST)
                if f.is_valid():
                    # inventariolaboratorioacademia.activo = f.cleaned_data['activo']
                    inventariolaboratorioacademia.observacion = f.cleaned_data['observacion']
                    inventariolaboratorioacademia.cantidad = f.cleaned_data['cantidad']
                    inventariolaboratorioacademia.fechadesde = f.cleaned_data['fechadesde']
                    inventariolaboratorioacademia.fechahasta = f.cleaned_data['fechahasta']
                    inventariolaboratorioacademia.vigente = f.cleaned_data['vigente']
                    inventariolaboratorioacademia.save(request)
                    log(u'Modifico Inventario Laboratorio Academico: %s' % inventariolaboratorioacademia, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteinventarioproducto':
            try:
                id = int(request.POST['id'])
                data['filtro'] = filtro = InventarioLaboratorioAcademia.objects.filter(pk=int(id), status=True).first()
                if not filtro:
                    raise NameError('Registro no encontrado')
                log(u'Elimino Inventario Laboratorio Academico: %s' % filtro, request, "del")
                filtro.delete()
                return JsonResponse({'error': False, 'mensaje': u'Registro eliminado con éxito!'})
            except Exception as ex:
                return JsonResponse({'error': True, 'mensaje': ex})

        elif action == 'addinventarioequipo':
            try:
                f = InventarioLaboratorioEquipoForm(request.POST)
                if f.is_valid():
                    inventariolaboratorioacademia = InventarioLaboratorioAcademia(laboratorio_id=request.POST['idlaboratorio'],
                                                                                  nombre=f.cleaned_data['nombre'],
                                                                                  observacion=f.cleaned_data['observacion'],
                                                                                  cantidad=f.cleaned_data['cantidad'],
                                                                                  tiposinventario=2,
                                                                                  estadoinventario=f.cleaned_data['estadoinventario'],
                                                                                  vigente=f.cleaned_data['vigente'])
                    inventariolaboratorioacademia.save(request)
                    log(u'Adiciono Inventario Laboratorio Academico: %s' % inventariolaboratorioacademia, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editinventarioequipo':
            try:
                inventariolaboratorioacademia = InventarioLaboratorioAcademia.objects.get(pk=request.POST['id'])
                f = InventarioLaboratorioEquipoForm(request.POST)
                if f.is_valid():
                    inventariolaboratorioacademia.observacion = f.cleaned_data['observacion']
                    inventariolaboratorioacademia.cantidad = f.cleaned_data['cantidad']
                    inventariolaboratorioacademia.nombre = f.cleaned_data['nombre']
                    inventariolaboratorioacademia.estadoinventario = f.cleaned_data['estadoinventario']
                    inventariolaboratorioacademia.vigente = f.cleaned_data['vigente']
                    inventariolaboratorioacademia.save(request)
                    log(u'Modifico Equipo Laboratorio Academico: %s' % inventariolaboratorioacademia, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteequipo':
            try:
                id = int(request.POST['id'])
                data['filtro'] = filtro = InventarioLaboratorioAcademia.objects.filter(pk=int(id), status=True).first()
                if not filtro:
                    raise NameError('Registro no encontrado')
                filtro.delete()
                return JsonResponse({'error': False, 'mensaje': u'Registro eliminado con éxito!'})
            except Exception as ex:
                return JsonResponse({'error': True, 'mensaje': ex})

        elif action == 'addinventarioinsumo':
            try:
                f = InventarioLaboratorioInsumoForm(request.POST)
                if f.is_valid():
                    inventariolaboratorioacademia = InventarioLaboratorioAcademia(laboratorio_id=request.POST['idlaboratorio'],
                                                                                  nombre=f.cleaned_data['nombre'],
                                                                                  observacion=f.cleaned_data['observacion'],
                                                                                  cantidad=f.cleaned_data['cantidad'],
                                                                                  tiposinventario=3,
                                                                                  vigente=f.cleaned_data['vigente'])
                    inventariolaboratorioacademia.save(request)
                    log(u'Adiciono Inventario Laboratorio Academico: %s' % inventariolaboratorioacademia, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editinventarioinsumo':
            try:
                inventariolaboratorioacademia = InventarioLaboratorioAcademia.objects.get(pk=request.POST['id'])
                f = InventarioLaboratorioInsumoForm(request.POST)
                if f.is_valid():
                    inventariolaboratorioacademia.observacion = f.cleaned_data['observacion']
                    inventariolaboratorioacademia.cantidad = f.cleaned_data['cantidad']
                    inventariolaboratorioacademia.nombre = f.cleaned_data['nombre']
                    inventariolaboratorioacademia.vigente = f.cleaned_data['vigente']
                    inventariolaboratorioacademia.save(request)
                    log(u'Modifico Insumo Laboratorio Academico: %s' % inventariolaboratorioacademia, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteinsumo':
            try:
                id = int(request.POST['id'])
                data['filtro'] = filtro = InventarioLaboratorioAcademia.objects.filter(pk=int(id), status=True).first()
                if not filtro:
                    raise NameError('Registro no encontrado')
                filtro.delete()
                return JsonResponse({'error': False, 'mensaje': u'Registro eliminado con éxito!'})
            except Exception as ex:
                return JsonResponse({'error': True, 'mensaje': ex})

        elif action == 'addinventariorespuesto':
            try:
                f = InventarioLaboratorioInsumoForm(request.POST)
                if f.is_valid():
                    inventariolaboratorioacademia = InventarioLaboratorioAcademia(laboratorio_id=request.POST['idlaboratorio'],
                                                                                  nombre=f.cleaned_data['nombre'],
                                                                                  observacion=f.cleaned_data['observacion'],
                                                                                  cantidad=f.cleaned_data['cantidad'],
                                                                                  tiposinventario=4,
                                                                                  vigente=f.cleaned_data['vigente'])
                    inventariolaboratorioacademia.save(request)
                    log(u'Adiciono Respuesto Laboratorio Academico: %s' % inventariolaboratorioacademia, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editinventariorespuesto':
            try:
                inventariolaboratorioacademia = InventarioLaboratorioAcademia.objects.get(pk=request.POST['id'])
                f = InventarioLaboratorioInsumoForm(request.POST)
                if f.is_valid():
                    inventariolaboratorioacademia.observacion = f.cleaned_data['observacion']
                    inventariolaboratorioacademia.cantidad = f.cleaned_data['cantidad']
                    inventariolaboratorioacademia.nombre = f.cleaned_data['nombre']
                    inventariolaboratorioacademia.vigente = f.cleaned_data['vigente']
                    inventariolaboratorioacademia.save(request)
                    log(u'Modifico Respuesto Laboratorio Academico: %s' % inventariolaboratorioacademia, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleterespuesto':
            try:
                id = int(request.POST['id'])
                data['filtro'] = filtro = InventarioLaboratorioAcademia.objects.filter(pk=int(id), status=True).first()
                if not filtro:
                    raise NameError('Registro no encontrado')
                filtro.delete()
                return JsonResponse({'error': False, 'mensaje': u'Registro eliminado con éxito!'})
            except Exception as ex:
                return JsonResponse({'error': True, 'mensaje': ex})

        elif action == 'addresponsable':
            try:
                f = ResponsableLaboratorioAcademiaForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})

                if f.is_valid():
                    laboratorioacademia = LaboratorioAcademia.objects.filter(pk=request.POST['idlaboratorio'], status=True)[0]
                    responsablelaboratorioacademia = ResponsableLaboratorioAcademia(laboratorio=laboratorioacademia,
                                                                                    persona=f.cleaned_data['persona'],
                                                                                    fechadesde=f.cleaned_data['fechadesde'],
                                                                                    fechahasta=f.cleaned_data['fechahasta'],
                                                                                    vigente=f.cleaned_data['vigente'],
                                                                                    jornada=f.cleaned_data['jornada'])
                    responsablelaboratorioacademia.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            newfile._name = generar_nombre("responsablelaboratorioacademia_", newfile._name)
                            responsablelaboratorioacademia.archivo = newfile
                            responsablelaboratorioacademia.save(request)
                    log(u'Adiciono Responsable Laboratorio Academico: %s' % responsablelaboratorioacademia, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editresponsable':
            try:
                responsablelaboratorioacademia = ResponsableLaboratorioAcademia.objects.get(pk=request.POST['id'])
                f = ResponsableLaboratorioAcademiaForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})

                if f.is_valid():
                    responsablelaboratorioacademia.fechadesde = f.cleaned_data['fechadesde']
                    responsablelaboratorioacademia.fechahasta = f.cleaned_data['fechahasta']
                    responsablelaboratorioacademia.vigente = f.cleaned_data['vigente']
                    responsablelaboratorioacademia.jornada = f.cleaned_data['jornada']
                    responsablelaboratorioacademia.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            newfile._name = generar_nombre("responsablelaboratorioacademia_", newfile._name)
                            responsablelaboratorioacademia.archivo = newfile
                            responsablelaboratorioacademia.save(request)
                    log(u'Modifico Responsable Laboratorio Academico: %s' % responsablelaboratorioacademia, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteresponsable':
            try:
                responsablelaboratorioacademia = ResponsableLaboratorioAcademia.objects.get(pk=int(request.POST['id']))
                responsablelaboratorioacademia.status=False
                responsablelaboratorioacademia.save(request)
                log(u'Elimino Responsable Laboratorio Academico: %s' % responsablelaboratorioacademia, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addmantenimiento':
            try:
                f = PlanMantenimientoLaboratorioForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})

                if f.is_valid():
                    laboratorioacademia = LaboratorioAcademia.objects.filter(pk=request.POST['idlaboratorio'], status=True)[0]
                    planmantenimientolaboratorio = PlanMantenimientoLaboratorio(laboratorio=laboratorioacademia,
                                                                                fechadesde=f.cleaned_data['fechadesde'],
                                                                                fechahasta=f.cleaned_data['fechahasta'],
                                                                                tipo=f.cleaned_data['tipo'])
                    planmantenimientolaboratorio.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            newfile._name = generar_nombre("planmantenimientolaboratorio_", newfile._name)
                            planmantenimientolaboratorio.archivo = newfile
                            planmantenimientolaboratorio.save(request)
                    log(u'Adiciono Plan Mantenimiento Laboratorio Academico: %s' % planmantenimientolaboratorio, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editmantenimiento':
            try:
                planmantenimientolaboratorio = PlanMantenimientoLaboratorio.objects.get(pk=request.POST['id'])
                f = PlanMantenimientoLaboratorioForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})

                if f.is_valid():
                    planmantenimientolaboratorio.fechadesde = f.cleaned_data['fechadesde']
                    planmantenimientolaboratorio.fechahasta = f.cleaned_data['fechahasta']
                    planmantenimientolaboratorio.tipo = f.cleaned_data['tipo']
                    planmantenimientolaboratorio.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            newfile._name = generar_nombre("planmantenimientolaboratorio_", newfile._name)
                            planmantenimientolaboratorio.archivo = newfile
                            planmantenimientolaboratorio.save(request)
                    log(u'Modifico Plan Mantenimiento Laboratorio Academico: %s' % planmantenimientolaboratorio, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletemantenimiento':
            try:
                planmantenimientolaboratorio = PlanMantenimientoLaboratorio.objects.get(pk=int(request.POST['id']))
                planmantenimientolaboratorio.status=False
                planmantenimientolaboratorio.save(request)
                log(u'Elimino Plan Mantenimiento Laboratorio Academico: %s' % planmantenimientolaboratorio, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addnormativa':
            try:
                f = NormativaLaboratorioAcademiaForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})

                if f.is_valid():
                    laboratorioacademia = LaboratorioAcademia.objects.filter(pk=request.POST['idlaboratorio'], status=True)[0]
                    normativalaboratorioacademia = NormativaLaboratorioAcademia(laboratorio=laboratorioacademia,
                                                                                fechadesde=f.cleaned_data['fechadesde'],
                                                                                fechahasta=f.cleaned_data['fechahasta'],
                                                                                vigente=f.cleaned_data['vigente'],
                                                                                observacion=f.cleaned_data['observacion'])
                    normativalaboratorioacademia.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            newfile._name = generar_nombre("normativalaboratorio_", newfile._name)
                            normativalaboratorioacademia.archivo = newfile
                            normativalaboratorioacademia.save(request)
                    log(u'Adiciono Normativa Laboratorio Academico: %s' % normativalaboratorioacademia, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editnormativa':
            try:
                normativalaboratorioacademia = NormativaLaboratorioAcademia.objects.get(pk=request.POST['id'])
                f = NormativaLaboratorioAcademiaForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})

                if f.is_valid():
                    normativalaboratorioacademia.fechadesde = f.cleaned_data['fechadesde']
                    normativalaboratorioacademia.fechahasta = f.cleaned_data['fechahasta']
                    normativalaboratorioacademia.vigente = f.cleaned_data['vigente']
                    normativalaboratorioacademia.observacion = f.cleaned_data['observacion']
                    normativalaboratorioacademia.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            newfile._name = generar_nombre("normativalaboratorio_", newfile._name)
                            normativalaboratorioacademia.archivo = newfile
                            normativalaboratorioacademia.save(request)
                    log(u'Modifico Normativa Laboratorio Academico: %s' % normativalaboratorioacademia, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletenormativa':
            try:
                normativalaboratorioacademia = NormativaLaboratorioAcademia.objects.get(pk=int(request.POST['id']))
                normativalaboratorioacademia.status=False
                normativalaboratorioacademia.save(request)
                log(u'Elimino Normativa Laboratorio Academico: %s' % normativalaboratorioacademia, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'detalle_activo':
            try:
                data['activo'] = activo = ActivoFijo.objects.get(pk=int(request.POST['id']))
                template = get_template("af_activofijo/detalle.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'subareaconocimiento':
            try:
                area = AreaConocimientoTitulacion.objects.get(pk=request.POST['id'])
                lista = []
                for subarea in SubAreaConocimientoTitulacion.objects.filter(areaconocimiento=area, status=True, tipo=2):
                    lista.append([subarea.id, subarea.nombre])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'subareaespecificaconocimiento':
            try:
                area = SubAreaConocimientoTitulacion.objects.get(pk=request.POST['id'])
                lista = []
                for subarea in SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True,
                                                                                      areaconocimiento=area, tipo=2):
                    lista.append([subarea.id, subarea.nombre])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'carreras':
            try:
                lista = []
                facultad = Coordinacion.objects.get(pk=int(request.POST['id']))
                carrera = Carrera.objects.filter(coordinacion=facultad).order_by('nombre')
                for c in carrera:
                    lista.append([c.id, c.nombre])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Laboratorios / Talleres / Centros de Simulación'
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'reportelaboratorio':
                try:
                    #id = request.get['id']
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 12, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Reporte Laboratorio' + random.randint(1,
                                                                                                             10000).__str__() + '.xls'
                    columns = [
                        (u"No.", 10000),
                        (u"NOMBRE", 10000),
                        (u"UBICACION ESPECIFICA", 6000),
                        (u"ESTADO", 6000),
                        (u"TIPO", 3000),
                        (u"TIPO DE LABORATORIO", 6000),
                        (u"Nro EQUIPOS", 6000),
                        (u"CAPACIDAD", 3000),
                        (u"FACULTAD", 6000),
                        (u"CARRERA", 12000),
                        (u"AULA", 17000),
                        (u"CAMPO AMPLIO", 17000),
                        (u"CAMPO ESPECIFICO", 17000),
                        (u'CAMPO DETALLADO', 17000),
                        (u"FECHA INICIO", 6000),
                        (u"FECHA FIN", 6000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 4
                    i = 1

                    for laboratorio in LaboratorioAcademia.objects.filter(status=True):
                        campo1 = laboratorio.nombre if laboratorio.nombre else ''
                        campo2 = laboratorio.ubicacion if laboratorio.ubicacion else ''
                        campo3 = str(laboratorio.estado) if laboratorio.estado else ''
                        campo4 = str(laboratorio.tipo) if laboratorio.tipo else ''
                        campo5 = laboratorio.tipolaboratorio.nombre if laboratorio.tipolaboratorio else ''
                        campo6 = str(laboratorio.nro_equipos) if laboratorio.nro_equipos else ''
                        campo7 = str(laboratorio.capacidad) if laboratorio.capacidad else ''
                        campo8 = str(laboratorio.coordinacion) if laboratorio.coordinacion else ''
                        campo9 = str(laboratorio.carrera) if laboratorio.carrera else ''
                        campo10 = str(laboratorio.aula) if laboratorio.aula.nombre else ''
                        campo11 = str(laboratorio.campo_amplio) if laboratorio.campo_amplio else ''
                        campo12 = str(laboratorio.campo_especifico) if laboratorio.campo_especifico else ''
                        campo13 = str(laboratorio.campo_detallado) if laboratorio.campo_detallado else ''
                        campo14 = str(laboratorio.fecha_inicio_utilizacion) if laboratorio.fecha_inicio_utilizacion else ''
                        campo15 = laboratorio.fecha_fin_utilizacion if laboratorio.fecha_fin_utilizacion else ''

                        ws.write(row_num, 0, i, font_style2)
                        ws.write(row_num, 1, campo1, font_style2)
                        ws.write(row_num, 2, campo2, font_style2)
                        ws.write(row_num, 3, campo3, font_style2)
                        ws.write(row_num, 4, campo4, font_style2)
                        ws.write(row_num, 5, campo5, font_style2)
                        ws.write(row_num, 6, campo6, font_style2)
                        ws.write(row_num, 7, campo7, font_style2)
                        ws.write(row_num, 8, campo8, font_style2)
                        ws.write(row_num, 9, campo9, font_style2)
                        ws.write(row_num, 10, campo10, font_style2)
                        ws.write(row_num, 11, campo11, font_style2)
                        ws.write(row_num, 12, campo12, font_style2)
                        ws.write(row_num, 13, campo13, font_style2)
                        ws.write(row_num, 14, campo14, font_style2)
                        ws.write(row_num, 15, campo15, font_style2)

                        i +=1
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'add':
                try:
                    data['title'] = u'Nuevo Laboratorio Academia'
                    form = LaboratorioAcademiaForm()
                    data['form'] = form
                    return render(request, "laboratoriosacademia/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Editar Laboratorio Academia'
                    data['laboratorio'] = laboratorioacademia = LaboratorioAcademia.objects.get(pk=request.GET['id'])
                    form = LaboratorioAcademiaForm(initial={'nombre': laboratorioacademia.nombre,
                                                            'aula': laboratorioacademia.aula,
                                                            'capacidad': laboratorioacademia.capacidad,
                                                            'metroscuadrado': laboratorioacademia.metroscuadrado,
                                                            'tipo': laboratorioacademia.tipo,
                                                            'tipolaboratorio': laboratorioacademia.tipolaboratorio,
                                                            'estado': laboratorioacademia.estado,
                                                            'ubicacion': laboratorioacademia.ubicacion,
                                                            'coordinacion': laboratorioacademia.coordinacion,
                                                            'nro_estudiantes': laboratorioacademia.nro_estudiantes,
                                                            'nro_equipos': laboratorioacademia.nro_equipos,
                                                            'fecha_inicio_utilizacion':laboratorioacademia.fecha_inicio_utilizacion,
                                                            'fecha_fin_utilizacion': laboratorioacademia.fecha_fin_utilizacion,
                                                            'carrera': laboratorioacademia.carrera,
                                                            'campo_amplio': laboratorioacademia.campo_amplio,
                                                            'campo_especifico': laboratorioacademia.campo_especifico,
                                                            'campo_detallado': laboratorioacademia.campo_detallado
                                                            })
                    data['form'] = form
                    return render(request, "laboratoriosacademia/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'addinventario':
                try:
                    data['title'] = u'Nuevo Inventario Laboratorio Academia - Activos'
                    data['laboratorio'] = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    form = InventarioLaboratorioAcademiaForm()
                    data['form'] = form
                    return render(request, "laboratoriosacademia/addinventario.html", data)
                except Exception as ex:
                    pass

            elif action == 'editinventario':
                try:
                    data['title'] = u'Editar Inventario Laboratorio Academia - Activos'
                    data['laboratorio'] = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    inventariolaboratorioacademia = InventarioLaboratorioAcademia.objects.get(pk=request.GET['id'])
                    form = InventarioLaboratorioAcademiaForm(initial={'activo': inventariolaboratorioacademia.activo,
                                                                      'observacion': inventariolaboratorioacademia.observacion,
                                                                      'fechadesde': inventariolaboratorioacademia.fechadesde,
                                                                      'fechahasta': inventariolaboratorioacademia.fechahasta,
                                                                      'vigente': inventariolaboratorioacademia.vigente})
                    data['inventariolaboratorio'] = inventariolaboratorioacademia
                    form.editar(inventariolaboratorioacademia)
                    data['form'] = form
                    return render(request, "laboratoriosacademia/editinventario.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteinventario':
                try:
                    data['title'] = u'Eliminar Inventario Laboratorio Academia - Activos'
                    data['laboratorio'] = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    data['inventario'] = InventarioLaboratorioAcademia.objects.get(pk=request.GET['id'])
                    return render(request, "laboratoriosacademia/deleteinventario.html", data)
                except Exception as ex:
                    pass

            elif action == 'addinventarioproducto':
                try:
                    data['title'] = u'Nuevo Inventario Laboratorio Academia - Materiales'
                    data['laboratorio'] = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    form = InventarioLaboratorioAcademiaMaterialForm()
                    data['form'] = form
                    return render(request, "laboratoriosacademia/addinventarioproducto.html", data)
                except Exception as ex:
                    pass

            elif action == 'editinventarioproducto':
                try:
                    data['title'] = u'Editar Inventario Laboratorio Academia - Materiales'
                    data['laboratorio'] = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    inventariolaboratorioacademia = InventarioLaboratorioAcademia.objects.get(pk=request.GET['id'])
                    form = InventarioLaboratorioAcademiaMaterialForm(initial={'producto': inventariolaboratorioacademia.producto,
                                                                              'observacion': inventariolaboratorioacademia.observacion,
                                                                              'cantidad': inventariolaboratorioacademia.cantidad,
                                                                              'fechadesde': inventariolaboratorioacademia.fechadesde,
                                                                              'fechahasta': inventariolaboratorioacademia.fechahasta,
                                                                              'vigente': inventariolaboratorioacademia.vigente})
                    data['inventariolaboratorio'] = inventariolaboratorioacademia
                    form.editar(inventariolaboratorioacademia)
                    data['form'] = form
                    return render(request, "laboratoriosacademia/editinventarioproducto.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteinventarioproducto':
                try:
                    data['title'] = u'Eliminar Inventario Laboratorio Academia - Materiales'
                    data['laboratorio'] = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    data['inventario'] = InventarioLaboratorioAcademia.objects.get(pk=request.GET['id'])
                    return render(request, "laboratoriosacademia/deleteinventario.html", data)
                except Exception as ex:
                    pass

            elif action == 'addinventarioequipo':
                try:
                    data['title'] = u'Nuevo Inventario Laboratorio Academia - Equipos'
                    data['laboratorio'] = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    form = InventarioLaboratorioEquipoForm()
                    data['form'] = form
                    return render(request, "laboratoriosacademia/addinventarioequipo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editinventarioequipo':
                try:
                    data['title'] = u'Editar Inventario Laboratorio Academia - Equipos'
                    data['laboratorio'] = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    inventariolaboratorioacademia = InventarioLaboratorioAcademia.objects.get(pk=request.GET['id'])
                    form = InventarioLaboratorioEquipoForm(initial={'nombre': inventariolaboratorioacademia.nombre,
                                                                    'observacion': inventariolaboratorioacademia.observacion,
                                                                    'cantidad': inventariolaboratorioacademia.cantidad,
                                                                    'estadoinventario': inventariolaboratorioacademia.estadoinventario,
                                                                    'vigente': inventariolaboratorioacademia.vigente})
                    data['inventariolaboratorio'] = inventariolaboratorioacademia
                    data['form'] = form
                    return render(request, "laboratoriosacademia/editinventarioequipo.html", data)
                except Exception as ex:
                    pass

            elif action == 'addinventarioinsumo':
                try:
                    data['title'] = u'Nuevo Inventario Laboratorio Academia - Insumos'
                    data['laboratorio'] = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    form = InventarioLaboratorioInsumoForm()
                    data['form'] = form
                    return render(request, "laboratoriosacademia/addinventarioinsumo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editinventarioinsumo':
                try:
                    data['title'] = u'Editar Inventario Laboratorio Academia - Insumos'
                    data['laboratorio'] = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    inventariolaboratorioacademia = InventarioLaboratorioAcademia.objects.get(pk=request.GET['id'])
                    form = InventarioLaboratorioInsumoForm(initial={'nombre': inventariolaboratorioacademia.nombre,
                                                                    'observacion': inventariolaboratorioacademia.observacion,
                                                                    'cantidad': inventariolaboratorioacademia.cantidad,
                                                                    'vigente': inventariolaboratorioacademia.vigente})
                    data['inventariolaboratorio'] = inventariolaboratorioacademia
                    data['form'] = form
                    return render(request, "laboratoriosacademia/editinventarioinsumo.html", data)
                except Exception as ex:
                    pass

            elif action == 'addinventariorespuesto':
                try:
                    data['title'] = u'Nuevo Inventario Laboratorio Academia - Respuesto'
                    data['laboratorio'] = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    form = InventarioLaboratorioInsumoForm()
                    data['form'] = form
                    return render(request, "laboratoriosacademia/addinventariorespuesto.html", data)
                except Exception as ex:
                    pass

            elif action == 'editinventariorespuesto':
                try:
                    data['title'] = u'Editar Inventario Laboratorio Academia - Respuesto'
                    data['laboratorio'] = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    inventariolaboratorioacademia = InventarioLaboratorioAcademia.objects.get(pk=request.GET['id'])
                    form = InventarioLaboratorioInsumoForm(initial={'nombre': inventariolaboratorioacademia.nombre,
                                                                    'observacion': inventariolaboratorioacademia.observacion,
                                                                    'cantidad': inventariolaboratorioacademia.cantidad,
                                                                    'vigente': inventariolaboratorioacademia.vigente})
                    data['inventariolaboratorio'] = inventariolaboratorioacademia
                    data['form'] = form
                    return render(request, "laboratoriosacademia/editinventariorespuesto.html", data)
                except Exception as ex:
                    pass

            elif action == 'ingresoinventario':
                try:
                    data['title'] = u'Ingreso Inventario Laboratorio Academia'
                    data['t'] = None
                    if 't' in request.GET:
                        data['t'] = int(request.GET['t'])
                    data['laboratorio'] = laboratorioacademia = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    data['inventariolaboratorioacademias'] = laboratorioacademia.inventariolaboratorioacademia_set.filter(status=True, activo__isnull=False)
                    data['inventariolaboratorioacademiasproducto'] = laboratorioacademia.inventariolaboratorioacademia_set.filter(status=True, producto__isnull=False)
                    data['listadoequiposincodigo'] = laboratorioacademia.inventariolaboratorioacademia_set.filter(status=True, tiposinventario=2)
                    data['listadoinsumos'] = laboratorioacademia.inventariolaboratorioacademia_set.filter(status=True, tiposinventario=3)
                    data['listadorespuestos'] = laboratorioacademia.inventariolaboratorioacademia_set.filter(status=True, tiposinventario=4)
                    # data['form2'] = PacDetalleGeneralForm()
                    # data['form3'] = PacDetalleGeneralAprobadoForm()
                    return render(request, "laboratoriosacademia/ingresoinventario.html", data)
                except Exception as ex:
                    pass

            elif action == 'addresponsable':
                try:
                    data['title'] = u'Nuevo Responsable Laboratorio Academia'
                    data['laboratorio'] = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    form = ResponsableLaboratorioAcademiaForm()
                    data['form'] = form
                    return render(request, "laboratoriosacademia/addresponsable.html", data)
                except Exception as ex:
                    pass

            elif action == 'editresponsable':
                try:
                    data['title'] = u'Editar Responsable Laboratorio Academia'
                    data['laboratorio'] = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    responsablelaboratorioacademia = ResponsableLaboratorioAcademia.objects.get(pk=request.GET['id'])
                    form = ResponsableLaboratorioAcademiaForm(initial={'persona': responsablelaboratorioacademia.persona,
                                                                       'laboratorio': responsablelaboratorioacademia.laboratorio,
                                                                       'fechadesde': responsablelaboratorioacademia.fechadesde,
                                                                       'fechahasta': responsablelaboratorioacademia.fechahasta,
                                                                       'vigente': responsablelaboratorioacademia.vigente,
                                                                       'jornada': responsablelaboratorioacademia.jornada})
                    data['responsablelaboratorioacademia'] = responsablelaboratorioacademia
                    form.editar()
                    data['form'] = form
                    return render(request, "laboratoriosacademia/editresponsable.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteresponsable':
                try:
                    data['title'] = u'Eliminar Responsable Laboratorio Academia'
                    data['laboratorio'] = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    data['responsablelaboratorioacademia'] = ResponsableLaboratorioAcademia.objects.get(pk=request.GET['id'])
                    return render(request, "laboratoriosacademia/deleteresponsable.html", data)
                except Exception as ex:
                    pass

            elif action == 'ingresoresponsable':
                try:
                    data['title'] = u'Ingreso Responsable Laboratorio Academia'
                    data['laboratorio'] = laboratorioacademia = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    data['responsablelaboratorioacademias'] = laboratorioacademia.responsablelaboratorioacademia_set.filter(status=True).order_by('persona')
                    # data['form2'] = PacDetalleGeneralForm()
                    # data['form3'] = PacDetalleGeneralAprobadoForm()
                    return render(request, "laboratoriosacademia/ingresoresponsable.html", data)
                except Exception as ex:
                    pass

            elif action == 'addmantenimiento':
                try:
                    data['title'] = u'Nuevo Plan Mantenimiento Laboratorio Academia'
                    data['laboratorio'] = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    form = PlanMantenimientoLaboratorioForm()
                    data['form'] = form
                    return render(request, "laboratoriosacademia/addmantenimiento.html", data)
                except Exception as ex:
                    pass

            elif action == 'editmantenimiento':
                try:
                    data['title'] = u'Editar Plan Mantenimiento Laboratorio Academia'
                    data['laboratorio'] = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    planmantenimientolaboratorio = PlanMantenimientoLaboratorio.objects.get(pk=request.GET['id'])
                    form = PlanMantenimientoLaboratorioForm(initial={'laboratorio': planmantenimientolaboratorio.laboratorio,
                                                                     'fechadesde': planmantenimientolaboratorio.fechadesde,
                                                                     'fechahasta': planmantenimientolaboratorio.fechahasta,
                                                                     'jornada': planmantenimientolaboratorio.tipo})
                    data['planmantenimientolaboratorio'] = planmantenimientolaboratorio
                    data['form'] = form
                    return render(request, "laboratoriosacademia/editmantenimiento.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletemantenimiento':
                try:
                    data['title'] = u'Eliminar Plan Mantenimiento Laboratorio Academia'
                    data['laboratorio'] = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    data['planmantenimientolaboratorio'] = PlanMantenimientoLaboratorio.objects.get(pk=request.GET['id'])
                    return render(request, "laboratoriosacademia/deletemantenimiento.html", data)
                except Exception as ex:
                    pass

            elif action == 'ingresomantenimiento':
                try:
                    data['title'] = u'Ingreso Plan Mantenimiento Laboratorio Academia'
                    data['laboratorio'] = laboratorioacademia = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    data['planmantenimientolaboratorios'] = laboratorioacademia.planmantenimientolaboratorio_set.filter(status=True)
                    # data['form2'] = PacDetalleGeneralForm()
                    # data['form3'] = PacDetalleGeneralAprobadoForm()
                    return render(request, "laboratoriosacademia/ingresomantenimiento.html", data)
                except Exception as ex:
                    pass

            elif action == 'addnormativa':
                try:
                    data['title'] = u'Nuevo Normativa/Reglamento Laboratorio Academia'
                    data['laboratorio'] = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    form = NormativaLaboratorioAcademiaForm()
                    data['form'] = form
                    return render(request, "laboratoriosacademia/addnormativa.html", data)
                except Exception as ex:
                    pass

            elif action == 'editnormativa':
                try:
                    data['title'] = u'Editar Normativa/Reglamento Laboratorio Academia'
                    data['laboratorio'] = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    normativalaboratorioacademia = NormativaLaboratorioAcademia.objects.get(pk=request.GET['id'])
                    form = NormativaLaboratorioAcademiaForm(initial={'fechadesde': normativalaboratorioacademia.fechadesde,
                                                                     'fechahasta': normativalaboratorioacademia.fechahasta,
                                                                     'vigente': normativalaboratorioacademia.vigente,
                                                                     'observacion': normativalaboratorioacademia.observacion})
                    data['normativalaboratorioacademia'] = normativalaboratorioacademia
                    data['form'] = form
                    return render(request, "laboratoriosacademia/editnormativa.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletenormativa':
                try:
                    data['title'] = u'Eliminar Normativa/Reglamento Laboratorio Academia'
                    data['laboratorio'] = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    data['normativalaboratorioacademia'] = NormativaLaboratorioAcademia.objects.get(pk=request.GET['id'])
                    return render(request, "laboratoriosacademia/deletenormativa.html", data)
                except Exception as ex:
                    pass

            elif action == 'ingresonormativa':
                try:
                    data['title'] = u'Ingreso Normativa/Reglamento Laboratorio Academia'
                    data['laboratorio'] = laboratorioacademia = LaboratorioAcademia.objects.filter(pk=request.GET['idlaboratorio'], status=True)[0]
                    data['normativalaboratorioacademias'] = laboratorioacademia.normativalaboratorioacademia_set.filter(status=True)
                    # data['form2'] = PacDetalleGeneralForm()
                    # data['form3'] = PacDetalleGeneralAprobadoForm()
                    return render(request, "laboratoriosacademia/ingresonormativa.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            if 'id' in request.GET:
                ids = request.GET['id']
                laboratorioacademia = LaboratorioAcademia.objects.filter(id=ids, status=True)
            elif 's' in request.GET:
                search = request.GET['s']
                laboratorioacademia = LaboratorioAcademia.objects.filter(Q(nombre__icontains=search) | Q(aula__nombre__icontains=search), status=True).distinct()
            else:
                laboratorioacademia = LaboratorioAcademia.objects.filter(status=True)
            paging = MiPaginador(laboratorioacademia, 25)
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
            data['laboratorios'] = page.object_list
            return render(request, "laboratoriosacademia/view.html", data)