import sys
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Value, Sum
from django.db.models.functions import Coalesce
from django.forms import model_to_dict
from django.shortcuts import render, redirect

from django.core.cache import cache
from decorators import secure_module, last_access
from posgrado.forms import BalanceCostoForm, GestionHojaTrabajoForm, IntegranteGestionHojaTrabajoForm, \
    ActividadIntegranteGestionHojaTrabajoForm, ProfesorInvitadoValoresForm, ConfigurarCarreraProfesorInvitadoForm, \
    CostoVariableValoresForm, ConfigurarRmuForm, CatalogoClasificadorPresupuestarioFORM, ClasificadorPresupuestarioFORM, \
    CuentaContableFORM, CatalogoCuentaContableForm, FlujoEfectivoForm, AsociarCuentaFlujoEfectivoTotalForm, \
    CuentaEstadoResultadoIntegralForm, EstadoResultadoIntegralFORM, CuentaEjecucionPresupuestariaFORM, \
    EjecucionPresupuestariaFORM
from posgrado.models import BalanceCosto, GestionPosgrado, GestionIntegrantesPosgrado, \
    GestionIntegrantesActividadCarreraPosgrado, CohorteMaestria, MaestriasAdmision, \
    ConfiguracionProgramaProfesorInvitado, GestionPosgradoHojaTrabajo, CatalogoClasificadorPresupuestario, \
    ClasificadorPresupuestario, CatalogoCuentaContable, CuentaContable, AsociacionPresupuestaria, \
    BalanceCostoCarreraPeriodo, MESES_CHOICES, ConfFlujoEfectivo, ConfCuentaFlujoEfectivo, FlujoEfectivoMensual, \
    CuentaFlujoEfectivoMensual, ConfEstadoResultadoIntegral, EstadoResultadoIntegral, DetalleEstadoResultadoIntegral, \
    ConfigEjecucionPresupuestaria, EjecucionPresupuestaria, DetalleEjecucionPresupuestaria, PuntoEquilibrio
from sga.commonviews import adduserdata
from django.http import JsonResponse,HttpResponseRedirect
from django.template.loader import get_template
from sga.funciones import log, MiPaginador
from collections import defaultdict

from sga.models import Persona, Carrera, Periodo
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    hoy = datetime.now().date()
    mes_actual = hoy.month
    anio_actual = hoy.year
    data['personasesion'] = persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'addbalancecosto':
                try:
                    f = BalanceCostoForm(request.POST, request.FILES)
                    if  f.is_valid():
                        with transaction.atomic():
                            eBalanceCosto = BalanceCosto(
                                mes=f.cleaned_data['mes'],
                                anio=f.cleaned_data['anio'],
                                descripcion=f.cleaned_data['descripcion']
                            )
                            eBalanceCosto.save(request)
                            log(u'Agregó nuevo balance de costo mensual: %s' % eBalanceCosto, request, "add")
                            eBalanceCosto.generar_estructura_base_balance_costo(request)
                            eBalanceCosto.save_items_reportes_del_balance_de_costo(request)
                    else:
                        return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in f.errors.items()]})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "ok", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'actualizar_profesor_invitado':
                try:
                    f = ProfesorInvitadoValoresForm(request.POST, request.FILES)
                    id = int(request.POST.get('id', '0') or '0')
                    eBalanceCosto = BalanceCosto.objects.get(pk=id)
                    if f.is_valid():
                        eBalanceCosto.cantidad_medio_tiempo = f.cleaned_data['cantidad_medio_tiempo']
                        eBalanceCosto.medio_tiempo = f.cleaned_data['medio_tiempo']
                        eBalanceCosto.cantidad_tiempo_completo = f.cleaned_data['cantidad_tiempo_completo']
                        eBalanceCosto.tiempo_completo = f.cleaned_data['tiempo_completo']
                        eBalanceCosto.save(request)
                        eBalanceCosto.actualizar_costos_variables(request)
                        log(u'actualizo costo medio tiempo y tiempo completo invitado: %s' % eBalanceCosto, request, "add")

                    else:
                        return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in f.errors.items()]})

                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'actualizar_pestana_costos_variables':
                try:
                    f = CostoVariableValoresForm(request.POST, request.FILES)
                    id = int(request.POST.get('id', '0') or '0')
                    eBalanceCosto = BalanceCosto.objects.get(pk=id)
                    if f.is_valid():
                        eBalanceCosto.costo_por_publicidad = f.cleaned_data['costo_por_publicidad']
                        eBalanceCosto.evento_promocionales = f.cleaned_data['evento_promocionales']
                        eBalanceCosto.materiales_de_oficina = f.cleaned_data['materiales_de_oficina']
                        eBalanceCosto.save(request)
                        eBalanceCosto.calcular_costos_por_costos_variables(request)
                        eBalanceCosto.actualizar_costos_variables(request)
                        log(u'actualizo costos variables: %s' % eBalanceCosto, request, "add")

                    else:
                        return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in f.errors.items()]})

                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'add_gestion_hoja_trabajo':
                try:
                    f = GestionHojaTrabajoForm(request.POST, request.FILES)
                    if f.is_valid():
                        eGestionPosgrado = GestionPosgrado(
                            descripcion=f.cleaned_data['descripcion']
                        )
                        eGestionPosgrado.save(request)
                        log(u'Agregó nueva gestion hoja de trabajo: %s' % eGestionPosgrado, request, "add")
                    else:
                        return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in f.errors.items()]})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'aprobar_balance_costo_mensual':
                try:
                    pk = int(request.POST.get('id', '0') or '0')
                    if pk == 0:
                        raise NameError("Parametro no encontrado")

                    eBalanceCosto = BalanceCosto.objects.get(pk=pk)
                    eBalanceCosto.estado = 1
                    eBalanceCosto.save(request)
                    log(u'valido balance mensual de costo: %s' % eBalanceCosto, request, "edit")
                    return JsonResponse({'result': True, 'pk': eBalanceCosto.pk})

                except Exception as ex:
                    pass

            elif action == 'edit_gestion_hoja_trabajo':
                try:
                    id = int(request.POST.get('id', '0') or '0')
                    if id == 0:
                        raise NameError("Parametro no encontrado")

                    eGestionPosgrado = GestionPosgrado.objects.get(pk=id)
                    f = GestionHojaTrabajoForm(request.POST, request.FILES)
                    if f.is_valid():
                        eGestionPosgrado.descripcion =  f.cleaned_data['descripcion']
                        eGestionPosgrado.save(request)
                        log(u'Edit gestion hoja de trabajo: %s' % eGestionPosgrado, request, "edit")
                    else:
                        return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in f.errors.items()]})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'edit_programa_aplica_profesor_invitado':
                try:

                    eConfiguracionProgramaProfesorInvitado = ConfiguracionProgramaProfesorInvitado.objects.filter(status=True)
                    f = ConfigurarCarreraProfesorInvitadoForm(request.POST, request.FILES)
                    if eConfiguracionProgramaProfesorInvitado.exists():
                        filtro = eConfiguracionProgramaProfesorInvitado.first()
                        if f.is_valid():
                            filtro.carrera.clear()
                            filtro.carrera.set(f.cleaned_data['carrera'])
                            filtro.save(request)
                            log(u'Edito programas de maestrias aplican profesor invitado: %s' % filtro, request, "edit")
                        else:
                            return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in f.errors.items()]})
                    else:
                        if f.is_valid():
                            eConfiguracionProgramaProfesorInvitado = ConfiguracionProgramaProfesorInvitado()
                            eConfiguracionProgramaProfesorInvitado.save(request)
                            eConfiguracionProgramaProfesorInvitado.carrera.set(f.cleaned_data['carrera'])
                            eConfiguracionProgramaProfesorInvitado.save(request)
                            log(u'Adiciono programas de maestrias aplican profesor invitado: %s' % eConfiguracionProgramaProfesorInvitado, request, "add")
                        else:
                            return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.","form": [{key: value[0]} for key, value in f.errors.items()]})

                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'editar_rmu_coordinador_apoyo':
                try:
                    eConfiguracionProgramaProfesorInvitado = ConfiguracionProgramaProfesorInvitado.objects.filter(status=True)
                    f = ConfigurarRmuForm(request.POST, request.FILES)
                    if eConfiguracionProgramaProfesorInvitado.exists():
                        filtro = eConfiguracionProgramaProfesorInvitado.first()
                        if f.is_valid():
                            filtro.rmu_coordinador_de_apoyo = f.cleaned_data['rmu']
                            filtro.save(request)
                            log(u'Edito rmu coordinador de apoyo: %s' % filtro, request, "edit")
                        else:
                            return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in f.errors.items()]})
                    else:
                        if f.is_valid():
                            eConfiguracionProgramaProfesorInvitado = ConfiguracionProgramaProfesorInvitado(
                                rmu_coordinador_de_apoyo =  f.cleaned_data['rmu'],
                            )
                            eConfiguracionProgramaProfesorInvitado.save(request)
                            log(u'Adiciono rmu coordinador de apoyo: %s' % eConfiguracionProgramaProfesorInvitado, request, "add")
                        else:
                            return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.","form": [{key: value[0]} for key, value in f.errors.items()]})

                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'edit_integrante_gestion_hoja_trabajo':
                try:
                    id = int(request.POST.get('id', '0') or '0')
                    if id == 0:
                        raise NameError("Parametro no encontrado")

                    eGestionIntegrantesPosgrado = GestionIntegrantesPosgrado.objects.get(pk=id)

                    f = IntegranteGestionHojaTrabajoForm(request.POST, request.FILES)
                    f.edit(request.POST['persona'])
                    if f.is_valid():
                        eGestionIntegrantesPosgrado.persona =  f.cleaned_data['persona']
                        eGestionIntegrantesPosgrado.rmu =  f.cleaned_data['rmu']
                        eGestionIntegrantesPosgrado.save(request)
                        log(u'Edit integrante gestion hoja de trabajo: %s' % eGestionIntegrantesPosgrado, request, "edit")
                    else:
                        return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in f.errors.items()]})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'add_integrante_gestion_hoja_trabajo':
                try:
                    f = IntegranteGestionHojaTrabajoForm(request.POST, request.FILES)
                    gestionposgrado_id =  int(request.POST.get('id','0'))
                    f.edit(request.POST['persona'])
                    if f.is_valid():
                        eGestionIntegrantesPosgrado = GestionIntegrantesPosgrado(
                            gestionposgrado_id=gestionposgrado_id,
                            persona=f.cleaned_data['persona'],
                            rmu=f.cleaned_data['rmu'],
                        )
                        eGestionIntegrantesPosgrado.save(request)
                        log(u'Agregó nuevo integrante a la gestion de hoja de trabajo: %s' % eGestionIntegrantesPosgrado, request, "add")
                    else:
                        return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in f.errors.items()]})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'add_actividad_integrante_gestion_hoja_trabajo':
                try:
                    f = ActividadIntegranteGestionHojaTrabajoForm(request.POST, request.FILES)
                    gestionintegrantesposgrado_id =  int(request.POST.get('id','0'))
                    carrera_id = int(request.POST.get('carrera', '0') or '0')
                    if not carrera_id == 0:
                        f.edit(carrera_id)

                    if f.is_valid():
                        if f.cleaned_data['carrera']:
                            eGestionIntegrantesActividadCarreraPosgrado = GestionIntegrantesActividadCarreraPosgrado(
                                gestionintegrantesposgrado_id=gestionintegrantesposgrado_id,
                                carrera=f.cleaned_data['carrera'],
                                actividadpersonalposgrado=f.cleaned_data['actividadpersonalposgrado'],
                                hora_de_trabajo=f.cleaned_data['hora_de_trabajo'],
                            )
                        else:
                            eGestionIntegrantesActividadCarreraPosgrado = GestionIntegrantesActividadCarreraPosgrado(
                                gestionintegrantesposgrado_id=gestionintegrantesposgrado_id,
                                actividadpersonalposgrado=f.cleaned_data['actividadpersonalposgrado'],
                                hora_de_trabajo=f.cleaned_data['hora_de_trabajo'],
                            )
                        eGestionIntegrantesActividadCarreraPosgrado.save(request)
                        log(u'Agregó nuevo integrante a la gestion de hoja de trabajo: %s' % eGestionIntegrantesActividadCarreraPosgrado, request, "add")
                    else:
                        return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in f.errors.items()]})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'edit_actividad_integrante_gestion_hoja_trabajo':
                try:
                    f = ActividadIntegranteGestionHojaTrabajoForm(request.POST, request.FILES)
                    id = int(request.POST.get('id', '0') or '0')
                    carrera_id = int(request.POST.get('carrera', '0') or '0')
                    eGestionIntegrantesActividadCarreraPosgrado = GestionIntegrantesActividadCarreraPosgrado.objects.get( pk=id)
                    if not carrera_id == 0:
                        f.edit(carrera_id)
                    if f.is_valid():
                        if f.cleaned_data['carrera']:
                            eGestionIntegrantesActividadCarreraPosgrado.carrera = f.cleaned_data['carrera']
                        else:
                            eGestionIntegrantesActividadCarreraPosgrado.carrera =None
                        eGestionIntegrantesActividadCarreraPosgrado.actividadpersonalposgrado =f.cleaned_data['actividadpersonalposgrado']
                        eGestionIntegrantesActividadCarreraPosgrado.hora_de_trabajo =f.cleaned_data['hora_de_trabajo']
                        eGestionIntegrantesActividadCarreraPosgrado.save(request)
                        log(u'edit  integrante a la gestion de hoja de trabajo: %s' % eGestionIntegrantesActividadCarreraPosgrado, request, "add")
                    else:
                        return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in f.errors.items()]})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'eliminar_gestion_hoja_de_trabajo':
                try:
                    eGestionPosgrado = GestionPosgrado.objects.get(pk=int(request.POST['id']))
                    eGestionPosgrado.status = False
                    eGestionPosgrado.save(request)
                    log(f"Eliminó gestion posgrado:{eGestionPosgrado}", request, 'del')
                    return JsonResponse({"result": True, "error": False})
                except Exception as ex:
                    transaction.rollback()

            elif action == 'eliminar_balance_de_costo':
                try:
                    eBalanceCosto = BalanceCosto.objects.get(pk=int(request.POST['id']))
                    eBalanceCosto.status = False
                    eBalanceCosto.save(request)
                    log(f"Eliminó balance de costo mensual:{eBalanceCosto}", request, 'del')
                    return JsonResponse({"result": True, "error": False})
                except Exception as ex:
                    transaction.rollback()

            elif action == 'eliminar_integrante_gestion_hoja_de_trabajo':
                try:
                    eGestionIntegrantesPosgrado = GestionIntegrantesPosgrado.objects.get(pk=int(request.POST['id']))
                    eGestionIntegrantesPosgrado.get_actividades().update(status=False)
                    eGestionIntegrantesPosgrado.status = False
                    eGestionIntegrantesPosgrado.save(request)
                    log(f"Eliminó integrante gestion posgrado:{eGestionIntegrantesPosgrado}", request, 'del')
                    return JsonResponse({"result": True, "error": False})
                except Exception as ex:
                    transaction.rollback()

            elif action == 'eliminar_actividad_integrante_hoja_de_trabajo':
                try:
                    eGestionIntegrantesActividadCarreraPosgrado = GestionIntegrantesActividadCarreraPosgrado.objects.get(pk=int(request.POST['id']))
                    eGestionIntegrantesActividadCarreraPosgrado.status = False
                    eGestionIntegrantesActividadCarreraPosgrado.save(request)
                    log(f"Eliminó actividad de integrante de la gestion :{eGestionIntegrantesActividadCarreraPosgrado}", request, 'del')
                    return JsonResponse({"result": True, "error": False})
                except Exception as ex:
                    transaction.rollback()

            elif action == 'add_catalogo_clasificador_presupuestario':
                try:
                    form = CatalogoClasificadorPresupuestarioFORM(request.POST)
                    if form.is_valid():
                        eCatalogoClasificadorPresupuestario = CatalogoClasificadorPresupuestario(
                            descripcion=form.cleaned_data['descripcion'],
                            activo = form.cleaned_data['activo']
                        )
                        eCatalogoClasificadorPresupuestario.save(request)
                        log(u'Agregó nuevo catalogo de presupuesto: %s' % eCatalogoClasificadorPresupuestario, request, "add")
                    else:
                        return JsonResponse({"result": False, "message": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in form.errors.items()]})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "message": f"Error: {ex.__str__()}"})

            elif action == 'edit_catalogo_clasificador_presupuestario':
                try:
                    form = CatalogoClasificadorPresupuestarioFORM(request.POST)
                    eCatalogoClasificadorPresupuestario = CatalogoClasificadorPresupuestario.objects.get(pk=int(encrypt(request.POST['id'])))
                    if form.is_valid():
                        eCatalogoClasificadorPresupuestario.descripcion =form.cleaned_data['descripcion']
                        eCatalogoClasificadorPresupuestario.activo = form.cleaned_data['activo']
                        eCatalogoClasificadorPresupuestario.save(request)
                        log(u'Editó nuevo catalogo de presupuesto: %s' % eCatalogoClasificadorPresupuestario, request, "edit")
                    else:
                        return JsonResponse({"result": False, "message": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in form.errors.items()]})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "message": f"Error: {ex.__str__()}"})

            elif action == 'edit_catalogo_cuenta_contable':
                try:
                    form = CatalogoCuentaContableForm(request.POST)
                    eCatalogoCuentaContable = CatalogoCuentaContable.objects.get(pk=int(encrypt(request.POST['id'])))
                    if form.is_valid():
                        eCatalogoCuentaContable.descripcion =form.cleaned_data['descripcion']
                        eCatalogoCuentaContable.activo = form.cleaned_data['activo']
                        eCatalogoCuentaContable.save(request)
                        log(u'Editó  catalogo de cuentas contable: %s' % eCatalogoCuentaContable, request, "edit")
                    else:
                        return JsonResponse({"result": False, "message": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in form.errors.items()]})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "message": f"Error: {ex.__str__()}"})

            elif action == 'add_clasificador_presupuestario':
                try:
                    form = ClasificadorPresupuestarioFORM(request.POST)
                    id_cat = request.POST['catalogo']
                    form.set_queryset_catalogo(id_cat)
                    if form.is_valid():

                        eClasificadorPresupuestario = ClasificadorPresupuestario(
                            clasificadorpresupuestario=form.cleaned_data['catalogo'],
                            codigo_naturaleza=form.cleaned_data['codigo_naturaleza'] if form.cleaned_data['codigo_naturaleza'] else None,
                            codigo_grupo=form.cleaned_data['codigo_grupo'] if form.cleaned_data['codigo_grupo'] else None,
                            codigo_subgrupo=form.cleaned_data['codigo_subgrupo'] if form.cleaned_data['codigo_subgrupo'] else None,
                            codigo_rubro=form.cleaned_data['codigo_rubro'] if form.cleaned_data['codigo_rubro'] else None,
                            nombre=form.cleaned_data['nombre'],
                            descripcion=form.cleaned_data['descripcion'],
                        )
                        # Llamada al método clean() para ejecutar las validaciones
                        eClasificadorPresupuestario.clean()
                        eClasificadorPresupuestario.save(request)


                        log(u'Agregó nueva clasificacion de presupuesto %s' % eClasificadorPresupuestario, request, "add")
                    else:
                        return JsonResponse({"result": False, "message": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in form.errors.items()]})
                    res_js = {'result': True}
                except Exception as ex:
                    transaction.set_rollback(True)
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'message': msg_err}
                return JsonResponse(res_js)

            elif action == 'edit_clasificador_presupuestario':
                try:
                    form = ClasificadorPresupuestarioFORM(request.POST)
                    id_cat = request.POST['catalogo']
                    id = int(encrypt(request.POST['id']))
                    eClasificadorPresupuestario = ClasificadorPresupuestario.objects.get(pk=id)
                    form.set_queryset_catalogo(id_cat)
                    if form.is_valid():
                        eClasificadorPresupuestario.nombre = form.cleaned_data['nombre']
                        eClasificadorPresupuestario.descripcion = form.cleaned_data['descripcion']
                        eClasificadorPresupuestario.codigo_naturaleza = form.cleaned_data['codigo_naturaleza']
                        eClasificadorPresupuestario.codigo_grupo = form.cleaned_data['codigo_grupo']
                        eClasificadorPresupuestario.codigo_subgrupo = form.cleaned_data['codigo_subgrupo']
                        eClasificadorPresupuestario.codigo_rubro = form.cleaned_data['codigo_rubro']
                        eClasificadorPresupuestario.clean()
                        eClasificadorPresupuestario.save(request)
                        log(u'Edito nueva clasificacion de presupuesto %s' % eClasificadorPresupuestario, request,
                            "add")
                    else:
                        return JsonResponse({"result": False, "message": f"Error al validar los datos.",
                                             "form": [{key: value[0]} for key, value in form.errors.items()]})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "message": f"Error: {ex.__str__()}"})

            elif action == 'eliminar_cuenta_clasificador_presupuestario':
                try:
                    eClasificadorPresupuestario = ClasificadorPresupuestario.objects.get(pk=int(request.POST['id']))
                    eClasificadorPresupuestario.status = False
                    if eClasificadorPresupuestario.esta_en_uso():
                        return JsonResponse({"result": False, "error": True, "message": "No se puede eliminar, esta en uso."})
                    eClasificadorPresupuestario.save(request)
                    log(f"Eliminó integrante gestion posgrado:{eClasificadorPresupuestario}", request, 'del')
                    return JsonResponse({"result": True, "error": False})
                except Exception as ex:
                    transaction.rollback()
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'add_catalogo_cuenta_contable':
                try:
                    form = CatalogoClasificadorPresupuestarioFORM(request.POST)
                    if form.is_valid():
                        eCatalogoCuentaContable = CatalogoCuentaContable(
                            descripcion=form.cleaned_data['descripcion'],
                            activo = form.cleaned_data['activo']
                        )
                        eCatalogoCuentaContable.save(request)
                        log(u'Agregó nuevo catalogo de cuenta contable: %s' % eCatalogoCuentaContable, request, "add")
                    else:
                        return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in form.errors.items()]})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'add_cuenta_contable':
                try:
                    form = CuentaContableFORM(request.POST)
                    id_cat = request.POST['catalogocuentacontable']
                    form.set_queryset_catalogo(id_cat)
                    id_carrera = request.POST.get('carrera', None)
                    if id_carrera:
                        form.set_carrera(id_carrera)
                    if form.is_valid():
                        eCuentaContable = CuentaContable(
                            catalogocuentacontable=form.cleaned_data['catalogocuentacontable'],
                            codigo_categoria=form.cleaned_data['codigo_categoria'] if form.cleaned_data['codigo_categoria'] else None,
                            codigo_grupo=form.cleaned_data['codigo_grupo'] if form.cleaned_data['codigo_grupo'] else None,
                            codigo_subgrupo=form.cleaned_data['codigo_subgrupo'] if form.cleaned_data['codigo_subgrupo'] else None,
                            codigo_rubro=form.cleaned_data['codigo_rubro'] if form.cleaned_data['codigo_rubro'] else None,
                            codigo_subrubro=form.cleaned_data['codigo_subrubro'] if form.cleaned_data['codigo_subrubro'] else None,
                            tipo = form.cleaned_data['tipo'] if form.cleaned_data['tipo'] else 1,
                            nombre=form.cleaned_data['nombre'],
                            descripcion=form.cleaned_data['descripcion'],
                            carrera = form.cleaned_data['carrera']
                        )
                        # Llamada al método clean() para ejecutar las validaciones
                        eCuentaContable.clean()
                        eCuentaContable.save(request)

                        # clasificadores = request.POST.getlist('id_clasificador')
                        clasificadores = request.POST.get('id_clasificador', None)
                        if clasificadores:
                            import json
                            clasificadores = json.loads(clasificadores)
                            for item in clasificadores:
                                id = item['id']
                                tipo = item['tipo']
                                eClasificadorPresupuestario = ClasificadorPresupuestario.objects.get(pk=id)
                                eAsociacionPresupuestaria = AsociacionPresupuestaria(
                                    cuentacontable=eCuentaContable,
                                    clasificadorpresupuestario=eClasificadorPresupuestario,
                                    tipo=tipo
                                )
                                eAsociacionPresupuestaria.save(request)

                        log(u'Agregó nueva cuenta contable %s' % eCuentaContable, request,
                            "add")
                    else:
                        return JsonResponse({"result": False, "message": f"Error al validar los datos.",
                                             "form": [{key: value[0]} for key, value in form.errors.items()]})
                    res_js = {'result': True}
                except Exception as ex:
                    transaction.set_rollback(True)
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'message': msg_err}
                return JsonResponse(res_js)

            elif action == 'edit_cuenta_contable':
                try:
                    form = CuentaContableFORM(request.POST)
                    id_cat = request.POST['catalogocuentacontable']
                    id = int(encrypt(request.POST['id']))
                    eCuentaContable = CuentaContable.objects.get(pk=id)
                    form.set_queryset_catalogo(id_cat)
                    id_carrera = request.POST.get('carrera', None)
                    if id_carrera:
                        form.set_carrera(int(id_carrera))
                    if form.is_valid():
                        eCuentaContable.codigo_categoria = form.cleaned_data['codigo_categoria'] if form.cleaned_data['codigo_categoria'] else None
                        eCuentaContable.codigo_grupo = form.cleaned_data['codigo_grupo'] if form.cleaned_data['codigo_grupo'] else None
                        eCuentaContable.codigo_subgrupo = form.cleaned_data['codigo_subgrupo'] if form.cleaned_data['codigo_subgrupo'] else None
                        eCuentaContable.codigo_rubro = form.cleaned_data['codigo_rubro'] if form.cleaned_data['codigo_rubro'] else None
                        eCuentaContable.codigo_subrubro = form.cleaned_data['codigo_subrubro'] if form.cleaned_data['codigo_subrubro'] else None
                        eCuentaContable.tipo = form.cleaned_data['tipo'] if form.cleaned_data['tipo'] else 1
                        eCuentaContable.nombre = form.cleaned_data['nombre']
                        eCuentaContable.descripcion = form.cleaned_data['descripcion']
                        eCuentaContable.clean()
                        eCuentaContable.save(request)

                        clasificadores = request.POST.get('id_clasificador', None)
                        if clasificadores:
                            import json
                            clasificadores = json.loads(clasificadores)
                            for item in clasificadores:
                                id = item['id']
                                tipo = item['tipo']
                                eClasificadorPresupuestario = ClasificadorPresupuestario.objects.get(pk=id)
                                eAsociacionPresupuestaria = AsociacionPresupuestaria(
                                    cuentacontable=eCuentaContable,
                                    clasificadorpresupuestario=eClasificadorPresupuestario,
                                    tipo=tipo
                                )
                                eAsociacionPresupuestaria.save(request)
                        log(u'Edito cuenta contable %s' % eCuentaContable, request, "add")
                    else:
                        return JsonResponse({"result": False, "message": f"Error al validar los datos.",
                                             "form": [{key: value[0]} for key, value in form.errors.items()]})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "message": f"Error: {ex.__str__()}"})

            elif action == 'delete_cuenta_contable':
                try:
                    eCuentaContable = CuentaContable.objects.get(pk=int(request.POST['id']))
                    if eCuentaContable.esta_en_uso():
                        return JsonResponse({"result": False, "error": True, "message": "No se puede eliminar, esta cuenta contable esta en uso."})
                    eCuentaContable.status = False
                    eCuentaContable.save(request)
                    log(f"Eliminó cuenta contable:{eCuentaContable}", request, 'del')
                    return JsonResponse({"result": True, "error": False})
                except Exception as ex:
                    transaction.rollback()
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'delete_asociacion':
                try:
                    eAsociacion = AsociacionPresupuestaria.objects.get(pk=int(request.POST['id']))
                    eAsociacion.status = False
                    eAsociacion.save(request)
                    log(f"Eliminó asociación presupuestaria:{eAsociacion}", request, 'del')
                    return JsonResponse({"result": True, "error": False})
                except Exception as ex:
                    transaction.rollback()
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'guardar_total_certificacion_multiplicador':
                try:

                    id = int(request.POST.get('id', '0') or '0')
                    value = float(request.POST['value'])
                    eBalanceCostoCarreraPeriodo = BalanceCostoCarreraPeriodo.objects.get(pk=id)
                    eBalanceCostoCarreraPeriodo.cantidad_modulos_mult_pmodular = value
                    eBalanceCostoCarreraPeriodo.total_certificar_pmodular = (value * float(eBalanceCostoCarreraPeriodo.balancecostocarrera.balancecosto.get_subtotal_certificar_profesor_modulo(eBalanceCostoCarreraPeriodo.balancecostocarrera.carrera_id,eBalanceCostoCarreraPeriodo.periodo_id)))
                    eBalanceCostoCarreraPeriodo.save(request)
                    eBalanceCostoCarreraPeriodo.balancecostocarrera.balancecosto.actualizar_costos_fijos(request)
                    eBalanceCostoCarreraPeriodo.balancecostocarrera.balancecosto.save_total_reporte_profesor_modular(request, eBalanceCostoCarreraPeriodo.balancecostocarrera.balancecosto.get_total_a_certificar_profesor_modulo())
                    log(u'actualizo total reporte profesor modular: %s' % eBalanceCostoCarreraPeriodo, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'addconfigurarflujoefectivo':
                try:
                    import json
                    if not 'configflujo_objs' in request.POST:
                        raise Exception('No ha agregado una cuenta nueva en la configuración de flujo de efectivo')
                    objConfigs = request.POST.get('configflujo_objs', None)
                    if not objConfigs:
                        raise Exception('No ha agregado una cuenta nueva en la configuración de flujo de efectivo')

                    objConfigs = json.loads(objConfigs)
                    if len(objConfigs) < 3:
                        raise Exception('Debe configurar al menos 3 flujos de efectivo')
                    for item in objConfigs:
                        orden = item['orden']
                        tipoflujo = item['tipo_flujo']
                        ids_cuentas = item['cuentas']

                        eConfigFlujoEfectivo = ConfFlujoEfectivo(
                                                    tipoflujo=tipoflujo,
                                                    orden=orden)
                        eConfigFlujoEfectivo.save(request)

                        for id_cuenta in ids_cuentas:
                            eCuenta = CuentaContable.objects.get(pk=id_cuenta)

                            eConfCuentaFlujoEfectivo = ConfCuentaFlujoEfectivo(
                                                        confflujoefectivo=eConfigFlujoEfectivo,
                                                        cuentacontable=eCuenta
                                                       )
                            eConfCuentaFlujoEfectivo.save(request)


                    return JsonResponse({"isSuccess": True, "message": "Se ha guardado correctamente"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"isSuccess": False, "message": f"Error: {ex.__str__()}"})

            elif action == 'editconfigurarflujoefectivo':
                try:
                    import json
                    if not 'configflujo_objs' in request.POST:
                        raise Exception('No se ha enviado el objeto con la configuración de flujo de efectivo')
                    objConfigs = request.POST.get('configflujo_objs', None)
                    if not objConfigs:
                        raise Exception('No se ha enviado el objeto con la configuración de flujo de efectivo')

                    objConfigs = json.loads(objConfigs)
                    for item in objConfigs:
                        eConfFlujoEfectivo = ConfFlujoEfectivo.objects.get(pk=item['id'])
                        ids_cuentas = item['cuentas']
                        for id_cuenta in ids_cuentas:
                            eCuenta = CuentaContable.objects.get(pk=id_cuenta)
                            eConfCuentaFlujoEfectivo = ConfCuentaFlujoEfectivo(
                                                        confflujoefectivo=eConfFlujoEfectivo,
                                                        cuentacontable=eCuenta,
                                                        id=ConfCuentaFlujoEfectivo.objects.all().count()+1)
                            eConfCuentaFlujoEfectivo.save(request)

                    return JsonResponse({"isSuccess": True, "message": "Se ha guardado correctamente"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"isSuccess": False, "message": f"Error: {ex.__str__()}"})

            elif action == 'delete_conf_cuenta_flujo_efectivo':
                try:
                    item = ConfCuentaFlujoEfectivo.objects.get(pk=int(request.POST['id']))
                    item.status = False
                    item.save(request)
                    log(f"Eliminó asociación presupuestaria:{item}", request, 'del')
                    return JsonResponse({"result": True, "error": False})
                except Exception as ex:
                    transaction.rollback()
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'addflujoefectivo':
                try:
                    f = FlujoEfectivoForm(request.POST, request.FILES)
                    if  f.is_valid():
                        with transaction.atomic():
                            eFlujoEfectivoMensual = FlujoEfectivoMensual(
                                mes=f.cleaned_data['mes'],
                                anio=f.cleaned_data['anio'],
                                descripcion=f.cleaned_data['descripcion']
                            )
                            eFlujoEfectivoMensual.save(request)
                            log(u'Agregó nuevo flujo de efectivo de: %s' % eFlujoEfectivoMensual, request, "add")
                            eFlujoEfectivoMensual.generar_estructura_flujo_efectivo_mensual(request)
                    else:
                        return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in f.errors.items()]})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "ok", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'asociarcuentaflujoefectivo':
                try:
                    pk = int(encrypt(request.POST['id']))
                    eConfCuentaFlujoEfectivo = CuentaContable.objects.get(pk=pk)
                    f = AsociarCuentaFlujoEfectivoTotalForm(request.POST, request.FILES)
                    if f.is_valid():
                        with transaction.atomic():
                            eConfCuentaFlujoEfectivo.configuracioncampo = f.cleaned_data['configuracioncampo']
                            eConfCuentaFlujoEfectivo.save(request)
                            log(u'Agregó asociacion flujo efectivo con total: %s' % eConfCuentaFlujoEfectivo, request, "edit")
                    else:
                        return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.",
                                             "form": [{key: value[0]} for key, value in f.errors.items()]})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "ok", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'aprobar_flujo_de_efectivo_mensual':
                try:
                    pk = int(request.POST.get('id', '0') or '0')
                    if pk == 0:
                        raise NameError("Parametro no encontrado")

                    eFlujoEfectivoMensual = FlujoEfectivoMensual.objects.get(pk=pk)
                    eFlujoEfectivoMensual.estado = 1
                    eFlujoEfectivoMensual.save(request)
                    log(u'valido flujo de efectivo: %s' % eFlujoEfectivoMensual, request, "edit")
                    return JsonResponse({'result': True, 'pk': eFlujoEfectivoMensual.pk})

                except Exception as ex:
                    pass

            elif action == 'eliminar_flujo_de_efectivo':
                try:
                    eFlujoEfectivoMensual = FlujoEfectivoMensual.objects.get(pk=int(request.POST['id']))
                    eFlujoEfectivoMensual.status = False
                    eFlujoEfectivoMensual.save(request)
                    log(f"Eliminó flujo de efectivo mensual:{eFlujoEfectivoMensual}", request, 'del')
                    return JsonResponse({"result": True, "error": False})
                except Exception as ex:
                    transaction.rollback()

            elif action == 'guardar_valor_cuenta_flujo':
                try:

                    id = int(request.POST.get('id', '0') or '0')
                    value = request.POST['value']
                    eCuentaFlujoEfectivoMensual = CuentaFlujoEfectivoMensual.objects.get(pk=id)
                    if not eCuentaFlujoEfectivoMensual.cuenta_no_puede_ser_editada():
                        eCuentaFlujoEfectivoMensual.valor = value
                        eCuentaFlujoEfectivoMensual.save(request)
                        eCuentaFlujoEfectivoMensual.recalcular_cuenta_padre_flujo_efectivo(request, eCuentaFlujoEfectivoMensual.cuentacontable)
                        eCuentaFlujoEfectivoMensual.actualizar_total_ingresos_por_actividad_flujoefectivo(request)
                        eCuentaFlujoEfectivoMensual.actualizar_total_egresos_por_actividad_flujoefectivo(request)
                        eCuentaFlujoEfectivoMensual.actualizar_resultado_por_actividad_flujoefectivo(request)
                        eCuentaFlujoEfectivoMensual.actualizar_superavit_flujoefectivo(request)
                        log(u'actualizo valor cuenta flujo efectivo: %s' % eCuentaFlujoEfectivoMensual, request, "edit")

                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'add_cuenta_conf_estado_resultado':
                try:
                    form = CuentaEstadoResultadoIntegralForm(request.POST)
                    form.set_cuentacontable(int(request.POST['cuentacontable']))
                    if form.is_valid():
                        eConfEstadoResultadoIntegral = ConfEstadoResultadoIntegral(
                            cuentacontable=form.cleaned_data['cuentacontable'],
                        )
                        eConfEstadoResultadoIntegral.save(request)
                        log(u'Agregó nueva cuenta a la configuracion del estado de resultado integral %s' % eConfEstadoResultadoIntegral, request, "add")
                    else:
                        return JsonResponse({"result": False, "message": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in form.errors.items()]})
                    res_js = {'result': True}
                except Exception as ex:
                    transaction.set_rollback(True)
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'message': msg_err}
                return JsonResponse(res_js)

            elif action == 'eliminar_cuenta_conf_estado_resultado':
                try:
                    eConfEstadoResultadoIntegral = ConfEstadoResultadoIntegral.objects.get(pk=int(request.POST['id']))
                    eConfEstadoResultadoIntegral.status = False
                    eConfEstadoResultadoIntegral.save(request)
                    log(f"Eliminó cuenta de configuracion de estado de resultado:{eConfEstadoResultadoIntegral}", request, 'del')
                    return JsonResponse({"result": True, "error": False})
                except Exception as ex:
                    transaction.rollback()

            elif action == 'addestadoresultado':
                try:
                    form = EstadoResultadoIntegralFORM(request.POST)

                    mesesseleccion = request.POST.getlist('mes')
                    if len(mesesseleccion) == 0:
                        raise NameError("Debe seleccionar al menos un mes o todos los meses.")
                    if '0' in mesesseleccion:
                        meses = [choice[0] for choice in MESES_CHOICES if choice[0] != '0']
                    else:
                        meses = mesesseleccion
                    if request.POST['anio'] == '' or request.POST['anio'] == '0':
                        raise NameError("Debe seleccionar un año.")
                    anio = int(request.POST['anio'])
                    if anio <= 0:
                        raise NameError("El año seleccionado no es valido.")
                    meses_int = [int(mes) for mes in meses]
                    form.init_meses_x_anio(anio)
                    meseschoices = form.fields['mes'].choices
                    form.set_meses_f(meseschoices)
                    meses = [(id_mes, mes) for id_mes, mes in meseschoices if int(id_mes) in meses_int]
                    if form.is_valid():
                        eEstadoResultadoIntegral = EstadoResultadoIntegral(
                            anio=form.cleaned_data['anio'],
                            fecha=datetime.now().date()
                        )
                        eEstadoResultadoIntegral.set_meses(meses)
                        eEstadoResultadoIntegral.save(request)
                        resp = clonar_flujo_efectivo(eEstadoResultadoIntegral, meses_int, request)
                        result = resp.get('result', False)
                        if not result:
                            raise NameError(resp.get('message'))

                        log(u'Agregó nuevo estado de resultado integral %s' % eEstadoResultadoIntegral, request, "add")
                    else:
                        return JsonResponse({"result": False, "message": f"Error al validar los datos.",
                                             "form": [{key: value[0]} for key, value in form.errors.items()]})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "message": f"Error: {ex.__str__()}"})

            elif action == 'guardar_valor_cuenta_flujo':
                try:

                    id = int(request.POST.get('id', '0') or '0')
                    value = float(request.POST['value'])
                    eDetalleEstadoResultadoIntegral = DetalleEstadoResultadoIntegral.objects.get(pk=id)
                    eDetalleEstadoResultadoIntegral.valor = value
                    eDetalleEstadoResultadoIntegral.save(request)
                    log(u'actualizo valor de detalle de resultado integral: %s' % eDetalleEstadoResultadoIntegral, request, "edit")

                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'del_estadoresultado':
                try:
                    eEstadoResultadoIntegral = EstadoResultadoIntegral.objects.get(pk=int(request.POST['id']))
                    eEstadoResultadoIntegral.status = False
                    eEstadoResultadoIntegral.save(request)
                    log(f"Eliminó estado de resultado:{eEstadoResultadoIntegral}", request, 'del')
                    return JsonResponse({"result": True, "error": False})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "message": f"Error: {ex.__str__()}"})


            elif action == 'add_configuracion_ejecucionpresupuestaria':
                try:
                    form = CuentaEjecucionPresupuestariaFORM(request.POST)
                    form.set_cuentacontable(int(request.POST['cuentacontable']))
                    if form.is_valid():
                        eConfigEjecucionPresupuestaria = ConfigEjecucionPresupuestaria(
                            cuentacontable=form.cleaned_data['cuentacontable'],
                        )
                        eConfigEjecucionPresupuestaria.save(request)
                        log(u'Agregó nueva cuenta a la configuracion de ejecucion presupuestaria %s' % eConfigEjecucionPresupuestaria, request, "add")
                    else:
                        return JsonResponse({"result": False, "message": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in form.errors.items()]})
                    res_js = {'result': True}
                except Exception as ex:
                    transaction.set_rollback(True)
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'message': msg_err}
                return JsonResponse(res_js)

            elif action == 'del_configuracion_ejecucionpresupuestaria':
                try:
                    eConfigEjecucionPresupuestaria = ConfigEjecucionPresupuestaria.objects.get(pk=int(request.POST['id']))
                    eConfigEjecucionPresupuestaria.status = False
                    eConfigEjecucionPresupuestaria.save(request)
                    log(f"Eliminó cuenta de configuracion de ejecucion presupuestaria:{eConfigEjecucionPresupuestaria}", request, 'del')
                    return JsonResponse({"result": True, "error": False})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "message": f"Error: {ex.__str__()}"})


            elif action == 'add_ejecucionpresupuestaria':
                try:
                    form = EjecucionPresupuestariaFORM(request.POST)

                    mesesseleccion = request.POST.getlist('mes')
                    if len(mesesseleccion) == 0:
                        raise NameError("Debe seleccionar al menos un mes o todos los meses.")
                    if '0' in mesesseleccion:
                        meses = [choice[0] for choice in MESES_CHOICES if choice[0] != '0']
                    else:
                        meses = mesesseleccion
                    if request.POST['anio'] == '' or request.POST['anio'] == '0':
                        raise NameError("Debe seleccionar un año.")
                    anio = int(request.POST['anio'])
                    if anio <= 0:
                        raise NameError("El año seleccionado no es valido.")
                    meses_int = [int(mes) for mes in meses]
                    form.init_meses_x_anio(anio)
                    meseschoices = form.fields['mes'].choices
                    form.set_meses_f(meseschoices)
                    meses = [(id_mes, mes) for id_mes, mes in meseschoices if int(id_mes) in meses_int]

                    if form.is_valid():
                        eEjecucionPresupuestaria = EjecucionPresupuestaria(
                            anio=form.cleaned_data['anio'],
                            fecha=datetime.now().date()
                        )
                        eEjecucionPresupuestaria.set_meses(meses)
                        eEjecucionPresupuestaria.save(request)
                        resp = clonar_flujo_efectivo_ejecucion_presupuestaria(eEjecucionPresupuestaria, meses_int,  request)
                        result = resp.get('result', False)
                        if not result:
                            raise NameError(resp.get('message'))

                        log(u'Agregó nuevo ejecucion presupuestaria %s' % eEjecucionPresupuestaria, request, "add")
                    else:
                        return JsonResponse({"result": False, "message": f"Error al validar los datos.",
                                             "form": [{key: value[0]} for key, value in form.errors.items()]})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "message": f"Error: {ex.__str__()}"})

            elif action == 'guardar_codificado_ejecucion_presupuestaria':
                try:
                    id = int(request.POST.get('id', '0') or '0')
                    value = float(request.POST['value'])
                    eDetalleEjecucionPresupuestaria = DetalleEjecucionPresupuestaria.objects.get(pk=id)
                    eDetalleEjecucionPresupuestaria.codificado = value
                    eDetalleEjecucionPresupuestaria.saldo = value - float(eDetalleEjecucionPresupuestaria.devengado)
                    eDetalleEjecucionPresupuestaria.save(request)
                    log(u'actualizo codificado de ejecuion presupuestaria: %s' % eDetalleEjecucionPresupuestaria, request, "edit")

                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'guardar_devengado_ejecucion_presupuestaria':
                try:
                    id = int(request.POST.get('id', '0') or '0')
                    value = float(request.POST['value'])
                    eDetalleEjecucionPresupuestaria = DetalleEjecucionPresupuestaria.objects.get(pk=id)
                    eDetalleEjecucionPresupuestaria.devengado = value
                    eDetalleEjecucionPresupuestaria.saldo = float(eDetalleEjecucionPresupuestaria.codificado) - value
                    eDetalleEjecucionPresupuestaria.save(request)
                    log(u'actualizo devengado de ejecuion presupuestaria: %s' % eDetalleEjecucionPresupuestaria,
                        request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'del_ejecucionpresupuestaria':
                try:
                    eEjecucionPresupuestaria = EjecucionPresupuestaria.objects.get(pk=int(request.POST['id']))
                    eEjecucionPresupuestaria.status = False
                    eEjecucionPresupuestaria.save(request)
                    log(f"Eliminó cuenta de ejecucion presupuestaria:{eEjecucionPresupuestaria}", request, 'del')
                    return JsonResponse({"result": True, "error": False})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "message": f"Error: {ex.__str__()}"})

            elif action == 'actualiza_valores_puntoequilibrio':
                try:
                    id = int(request.POST.get('id', '0') or '0')
                    if id == 0:
                        raise NameError("Sin Id.")
                    tip_id = request.POST.get('tippk', '')
                    if tip_id == '':
                        raise NameError("Sin Tipo pk.")
                    subaction = request.POST.get('subaction', '')
                    if subaction == '':
                        raise NameError("Sin subaccion.")
                    value = request.POST.get('value', None)
                    if value is None:
                        raise NameError("Sin valor.")
                    value = float(value)

                    resp = validar_get_crear_puntoequilibrio(id,tip_id,  request)
                    if not resp.get('isSuccess', False):
                        raise NameError(resp.get('message'))
                    ePuntoEquilibrio = resp.get('ePuntoEquilibrio', None)
                    if ePuntoEquilibrio is None:
                        raise NameError("No se encontro el punto de equilibrio.")

                    if subaction == 'guardar_valor_maestria':
                        ePuntoEquilibrio.valor_maestria = value
                    elif subaction == 'guardar_valor_proyeccion_ventas':
                        ePuntoEquilibrio.proyeccion_ventas = value
                    elif subaction == 'guardar_valor_proyectado':
                        ePuntoEquilibrio.valor_proyectado = value
                    elif subaction == 'guardar_costo_fijo':
                        ePuntoEquilibrio.costo_fijo = value
                    elif subaction == 'guardar_costo_variable':
                        ePuntoEquilibrio.costo_variable = value
                    elif subaction == 'guardar_punto_equilibrio':
                        ePuntoEquilibrio.punto_equilibrio = value
                    elif subaction == 'guardar_valor_punto_equilibrio':
                        ePuntoEquilibrio.valor_punto_equilibrio = value
                    elif subaction == 'guardar_numero_modulos':
                        ePuntoEquilibrio.num_modulos = value

                    ePuntoEquilibrio.calculo_valores_punto_equilibrio()
                    ePuntoEquilibrio.save(request)


                    log(u'actualizo punto de equilibrio: %s' % ePuntoEquilibrio,
                        request, "edit")
                    return JsonResponse({"result": "ok", })
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'viewbalancecosto':
                try:
                    data['title'] = f'Balances de costos'
                    data['menu_principal'] = 2
                    filtro = Q(status=True)
                    url_vars = '&action=viewbalancecosto'

                    if pk := request.GET.get('pk', ''):
                        filtro &= Q(pk=pk)
                        url_vars += "&pk={}".format(pk)

                    eBalanceCostos = BalanceCosto.objects.filter(filtro).order_by('anio','-mes')

                    paging = MiPaginador(eBalanceCostos, 12)
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
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['eBalanceCostos'] = page.object_list
                    data['url_vars'] = url_vars

                    return render(request, "contabilidad/balancecosto/view.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/contabilidadposgrado")

            elif action == 'configuracionesfinanzasposgrado':
                try:
                    data['title'] = f'Configuraciones Balances de costos'
                    data['menu_principal'] = 1
                    data['menu_configuracion'] = 0
                    eGestionPosgrados = GestionPosgrado.objects.filter(status=True)
                    eConfiguracionProgramaProfesorInvitado = ConfiguracionProgramaProfesorInvitado.objects.filter(status=True).first()
                    primera_gestion = None
                    if eGestionPosgrados.exists():
                        primera_gestion = eGestionPosgrados.first()
                    data['primera_gestion'] = primera_gestion
                    data['eGestionPosgrados'] = eGestionPosgrados
                    data['eConfiguracionProgramaProfesorInvitado'] = eConfiguracionProgramaProfesorInvitado

                    return render(request, "contabilidad/configuraciones/balancecosto/view.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/contabilidadposgrado")

            elif action == 'reporteriacontabilidad':
                try:
                    data['title'] = f'Reportería contabilidad posgrado'
                    data['menu_principal'] = 4
                    data['menu_pestana'] = 0
                    return render(request, "contabilidad/reporteria/view.html", data)
                except Exception as ex:
                    messages.error(request,f'Ocurrió un error al abrir reporte cuentas por cobrar año y mes actual y anteriores: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
                    return HttpResponseRedirect(f"/contabilidadposgrado")

            elif action == 'reporteriacontabilidad_cuentasporcobrar':
                try:
                    TIEMPO_ENCACHE = 2 * 24 * 60 * 60  # 2 días en segundos
                    data['title'] = f'Reporte Cuentas por cobrar'
                    data['menu_principal'] = 4
                    data['menu_pestana'] = 1
                    filtro = Q(status=True)
                    url_vars = '&action=reporteriacontabilidad'
                    maestriaadmision_id = CohorteMaestria.objects.filter(periodoacademico__tipo_id=3, status=True).values_list('maestriaadmision_id', flat=True)
                    eMaestriasAdmisions = MaestriasAdmision.objects.filter(status=True, id__in=maestriaadmision_id,carrera__coordinacion__id=7).order_by('id').distinct()
                    ids_carreras_vigentes = []
                    for eMaestriasAdmision in eMaestriasAdmisions:
                        if eMaestriasAdmision.cohortes_maestria_activas():
                            ids_carreras_vigentes.append(eMaestriasAdmision.carrera.pk)
                    data['eCarreras'] = Carrera.objects.filter(pk__in=ids_carreras_vigentes)
                    eCarreras= Carrera.objects.filter(pk__in=ids_carreras_vigentes).filter(filtro)
                    anio = datetime.now().year

                    # Comprobar si se envió el parámetro 'clear_cache'
                    clear_cache = request.GET.get('clear_cache', '0') == '1'

                    # Clave de caché basada en el año y las carreras
                    cache_key = f"estructura_cuentas_por_cobrar_contabilidad_posgrado_todas_las_carreras"
                    # Limpiar la caché si se envió el parámetro 'clear_cache'
                    if clear_cache and cache.has_key(cache_key):
                        cache.delete(cache_key)  # Eliminar la caché existente
                        cache_timestamp = None  # No habrá fecha de caché inicial
                        return redirect("/contabilidadposgrado?action=reporteriacontabilidad_cuentasporcobrar")

                    # Comprobar si ya está en la caché
                    if cache.has_key(cache_key):
                        cache_data = cache.get(cache_key)
                        estructura = cache_data['estructura']
                        cache_timestamp = cache_data['timestamp']
                    else:
                        # Generar la estructura si no está en la caché
                        estructura = MaestriasAdmision.ingresos_cuentas_por_cobrar_por_anio_and_carrera(anio, eCarreras)
                        # Crear un diccionario que incluya la estructura y la fecha y hora de creación
                        cache_data = {
                            'estructura': estructura,
                            'timestamp':  datetime.now()  # Almacenar la fecha y hora de creación de la caché
                        }

                        # Almacenar en caché por 2 días
                        cache.set(cache_key, cache_data, TIEMPO_ENCACHE)

                        # Obtener la fecha y hora de la caché recién creada
                        cache_timestamp = cache_data['timestamp']
                    # Crear un diccionario para almacenar los totales por año y mes
                    diccionario_totales_por_mes = {}

                    carreras_ids = request.GET.getlist('carreras')  # IDs de carreras seleccionadas
                    # Filtrar la estructura por las carreras seleccionadas usando filter(lambda ...)
                    if carreras_ids:
                        estructura_filtrada = list(filter(lambda item: str(item['eCarrera'].id) in carreras_ids, estructura))
                    else:
                        estructura_filtrada = estructura

                    # Leer la estructura y acumular los totales por año y mes
                    for carrera_data in estructura_filtrada:
                        carrera_nombre = carrera_data['eCarrera'].nombre  # Obtener el nombre de la carrera
                        for mes_data in carrera_data['encabezado_meses']:
                            anio = mes_data['anio']
                            mes = mes_data['numero_mes']
                            # Inicializar el diccionario si no existe el año y mes
                            if anio not in diccionario_totales_por_mes:
                                diccionario_totales_por_mes[anio] = {}
                            if mes not in diccionario_totales_por_mes[anio]:
                                diccionario_totales_por_mes[anio][mes] = {
                                    'total_cuentas_por_cobrar_anios_anteriores': 0,
                                    'total_cuentas_por_cobrar_anio_mes_actual': 0,
                                    'total_presupuestado_anio_mes_actual': 0,
                                    'total_presupuestado_anio_mes_actual_sin_este_mes': 0,
                                    'total_presupuestado_anio_mes_actual_acumulado': 0,
                                    'total_pagado': 0,
                                }

                            # Acumular los valores de cada mes
                            diccionario_totales_por_mes[anio][mes]['total_cuentas_por_cobrar_anios_anteriores'] +=mes_data['detalle_mes'][0]['cuentas_por_cobrar_anios_anteriores'] or 0
                            diccionario_totales_por_mes[anio][mes]['total_cuentas_por_cobrar_anio_mes_actual'] +=  mes_data['detalle_mes'][0]['cuentas_por_cobrar_anio_mes_actual'] or 0
                            diccionario_totales_por_mes[anio][mes]['total_presupuestado_anio_mes_actual'] +=mes_data['detalle_mes'][0]['presupuestado_anio_mes_actual'] or 0
                            diccionario_totales_por_mes[anio][mes]['total_presupuestado_anio_mes_actual_sin_este_mes'] +=mes_data['detalle_mes'][0]['presupuestado_anio_mes_sin_mes_actual'] or 0
                            diccionario_totales_por_mes[anio][mes]['total_presupuestado_anio_mes_actual_acumulado'] +=mes_data['detalle_mes'][0]['presupuestado_anio_hasta_mes_actual_acumulado'] or 0
                            diccionario_totales_por_mes[anio][mes]['total_pagado'] += mes_data['detalle_mes'][0][ 'pagado'] or 0

                    if 'option' in request.GET:
                        if request.GET.get('option')== 'downloadexcel':
                            return MaestriasAdmision.generar_reporte_cuentas_por_cobrar_anio_and_excel(anio, estructura_filtrada, diccionario_totales_por_mes, MESES_CHOICES, request)

                    # Ahora el diccionario diccionario_totales_por_mes tiene los totales acumulados por año y mes
                    data['estructura'] = estructura_filtrada
                    data['cache_timestamp'] = cache_timestamp  # Incluir la fecha y hora en el contexto
                    data['diccionario_totales_por_mes'] = diccionario_totales_por_mes
                    data['meses'] = MESES_CHOICES
                    data["url_vars"] = url_vars
                    data["anio"] = anio
                    data['carreras_ids'] = carreras_ids  # Enviar las carreras seleccionadas al template
                    return render(request, "contabilidad/reporteria/cuentasporcobrar/view.html", data)
                except Exception as ex:
                    messages.error(request,f'Ocurrió un error al abrir reporte cuentas por cobrar año y mes actual y anteriores: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
                    return HttpResponseRedirect(f"/contabilidadposgrado")

            elif action == 'reporteria_punto_equilibrio':
                try:
                    data['title'] = f'Punto de Equilibrio'
                    data['menu_principal'] = 4
                    data['menu_pestana'] = 2
                    filtro = Q(status=True)
                    url_vars = '&action=reporteriacontabilidad'
                    maestriaadmision_id = CohorteMaestria.objects.filter(periodoacademico__tipo_id=3,
                                                                         status=True).values_list('maestriaadmision_id',
                                                                                                  flat=True)
                    eMaestriasAdmisions = MaestriasAdmision.objects.filter(status=True, id__in=maestriaadmision_id,
                                                                           carrera__coordinacion__id=7).order_by(
                        'id').distinct()
                    ids_carreras_vigentes = []
                    for eMaestriasAdmision in eMaestriasAdmisions:
                        if eMaestriasAdmision.cohortes_maestria_activas():
                            ids_carreras_vigentes.append(eMaestriasAdmision.carrera.pk)
                    data['eCarreras'] = Carrera.objects.filter(pk__in=ids_carreras_vigentes)
                    eCarreras = Carrera.objects.filter(pk__in=ids_carreras_vigentes).filter(filtro)
                    anio = datetime.now().year

                    ePuntoEquilibrios = PuntoEquilibrio.objects.filter(status=True)
                    costos_fijos_personal_administrativo = GestionPosgrado.objects.filter(status=True).first().get_resumen_carrera_hoja_trabajo()
                    eCarreras = eCarreras.exclude(id__in=ePuntoEquilibrios.values_list('carrera_id', flat=True))
                    def obtener_data_carrera(eCarrera):
                        resumen_carrera = next((item for item in costos_fijos_personal_administrativo if item['eCarrera'] == eCarrera), None)
                        # Verifica si se encontró el resumen de la carrera, si no se encontró, devuelve un total de 0
                        total_costo_fijo = resumen_carrera['total'] if resumen_carrera else 0
                        return{
                            'carrera':eCarrera,
                            'total_costo_fijo': total_costo_fijo
                        }

                    # Obtener la lista de carreras con el total
                    estructura_carrera = list(map(lambda eCarrera: obtener_data_carrera(eCarrera), eCarreras))

                    data['estructura_carrera'] = estructura_carrera
                    data['ePuntoEquilibrios'] = ePuntoEquilibrios
                    data['menu_colapse'] = True
                    return render(request, "contabilidad/reporteria/punto_equilibrio/view.html", data)
                except Exception as ex:
                    messages.error(request,f'Ocurrió un error al abrir reporte: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
                    return HttpResponseRedirect(f"/contabilidadposgrado")

            elif action == 'viewclasificadorpresupuestario':
                try:
                    data['title'] = f"Clasificador presupuestario"
                    data['menu_principal'] = 1
                    data['menu_configuracion'] = 1

                    eCatalogoClasificadorPresupuestario = CatalogoClasificadorPresupuestario.objects.filter(status=True).order_by('descripcion')
                    data['eCatalogoClasificadorPresupuestario'] = eCatalogoClasificadorPresupuestario
                    return render(request, "contabilidad/configuraciones/clasificadorpresupuestario/view.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/contabilidadposgrado")

            elif action == 'add_catalogo_clasificador_presupuestario':
                try:
                    form = CatalogoClasificadorPresupuestarioFORM()
                    data['form'] = form
                    data['action'] = 'add_catalogo_clasificador_presupuestario'
                    template = get_template('contabilidad/modalform.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edit_catalogo_clasificador_presupuestario':
                try:
                    if not 'id' in request.GET:
                        raise NameError("No se ha especificado el id del clasificador presupuestario")
                    id = int(request.GET['id'])
                    eCatalogoClasificadorPresupuestario = CatalogoClasificadorPresupuestario.objects.get(pk=id)
                    form = CatalogoClasificadorPresupuestarioFORM(initial=model_to_dict(eCatalogoClasificadorPresupuestario))
                    data['id'] = id
                    data['form'] = form
                    data['action'] = 'edit_catalogo_clasificador_presupuestario'
                    template = get_template('contabilidad/modalform.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edit_catalogo_cuenta_contable':
                try:
                    if not 'id' in request.GET:
                        raise NameError("No se ha especificado el id del clasificador presupuestario")
                    id = int(request.GET['id'])
                    eCatalogoCuentaContable = CatalogoCuentaContable.objects.get(pk=id)
                    form = CatalogoCuentaContableForm(initial=model_to_dict(eCatalogoCuentaContable))
                    data['id'] = id
                    data['form'] = form
                    data['action'] = 'edit_catalogo_cuenta_contable'
                    template = get_template('contabilidad/modalform.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'list_catalogo_clasificador_presupuestario':
                try:
                    if not 'id' in request.GET:
                        raise NameError("No se ha especificado el id del clasificador presupuestario")
                    data['title'] = f"Clasificador presupuestario"
                    data['menu_principal'] = 1
                    data['menu_configuracion'] = 1
                    data['id_cat'] = id = int(request.GET['id'])
                    filtro = Q(status=True, clasificadorpresupuestario_id=id)
                    url_vars = f'&action=list_catalogo_clasificador_presupuestario&id={id}'
                    codigo = request.GET.get('codigo', '')
                    if codigo:

                        url_vars += "&codigo={}".format(codigo)
                        partes_codigo = codigo.split('.')
                        if len(partes_codigo) > 0 and partes_codigo[0]:  # Validar si la primera parte está presente
                            filtro &= Q(codigo_naturaleza=partes_codigo[0])
                        if len(partes_codigo) > 1 and partes_codigo[1]:  # Validar si la segunda parte está presente
                            filtro &= Q(codigo_grupo=partes_codigo[1])
                        if len(partes_codigo) > 2 and partes_codigo[2]:  # Validar si la tercera parte está presente
                            filtro &= Q(codigo_subgrupo=partes_codigo[2])
                        if len(partes_codigo) > 3 and partes_codigo[3]:  # Validar si la cuarta parte está presente
                            filtro &= Q(codigo_rubro=partes_codigo[3])
                    data['codigo'] = codigo
                    query = ClasificadorPresupuestario.objects.filter(filtro).order_by(
                        Coalesce('codigo_naturaleza', Value('\uffff')),
                        # Asigna un valor alto para que los nulos vayan al final
                        Coalesce('codigo_grupo', Value('\uffff')),
                        Coalesce('codigo_subgrupo', Value('\uffff')),
                        Coalesce('codigo_rubro', Value('\uffff'))
                    )
                    paging = MiPaginador(query, 25)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data["url_vars"] = url_vars
                    data["eClasificadorPresupuestario"] = page.object_list
                    return render(request, "contabilidad/configuraciones/clasificadorpresupuestario/list_clasificarpresupuestario.html", data)
                except Exception as ex:
                    pass

            elif action == 'add_clasificador_presupuestario':
                try:
                    if not 'id' in request.GET:
                        raise NameError("No se ha especificado el id del clasificador presupuestario")
                    data['id_cat'] = id_cat = int(request.GET['id'])

                    form = ClasificadorPresupuestarioFORM()
                    form.set_queryset_catalogo(id_cat)

                    data['form'] = form
                    data['action'] = 'add_clasificador_presupuestario'
                    template = get_template('contabilidad/modalform.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'add_grupo_presupuestario':
                try:
                    if not 'id' in request.GET:
                        raise NameError("No se ha especificado el id del clasificador presupuestario")
                    data['id_cp'] = id = int(request.GET['id'])
                    eClasiPres = ClasificadorPresupuestario.objects.get(id=id, status=True)
                    form = ClasificadorPresupuestarioFORM()
                    cod_grupo = ClasificadorPresupuestario.ultimo_grupo(eClasiPres.clasificadorpresupuestario_id, eClasiPres.codigo_naturaleza)
                    if cod_grupo:
                        cod_grupo = int(cod_grupo) + 1
                    else:
                        cod_grupo = 1
                    form.set_codigos(eClasiPres.codigo_naturaleza, cod_grupo)
                    form.set_queryset_catalogo(eClasiPres.clasificadorpresupuestario_id)

                    data['form'] = form
                    data['action'] = 'add_clasificador_presupuestario'
                    template = get_template('contabilidad/modalform.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'add_subgrupo_presupuestario':
                try:
                    if not 'id' in request.GET:
                        raise NameError("No se ha especificado el id del clasificador presupuestario")
                    data['id_cp'] = id = int(request.GET['id'])
                    eClasiPres = ClasificadorPresupuestario.objects.get(id=id, status=True)
                    form = ClasificadorPresupuestarioFORM()
                    cod_subgrupo = ClasificadorPresupuestario.ultimo_subgrupo(eClasiPres.clasificadorpresupuestario_id,
                                                                        eClasiPres.codigo_naturaleza, eClasiPres.codigo_grupo)
                    if cod_subgrupo:
                        cod_subgrupo = int(cod_subgrupo) + 1
                    else:
                        cod_subgrupo = 1
                    form.set_codigos(eClasiPres.codigo_naturaleza, eClasiPres.codigo_grupo, cod_subgrupo)
                    form.set_queryset_catalogo(eClasiPres.clasificadorpresupuestario_id)

                    data['form'] = form
                    data['action'] = 'add_clasificador_presupuestario'
                    template = get_template('contabilidad/modalform.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'add_rubro_presupuestario':
                try:
                    if not 'id' in request.GET:
                        raise NameError("No se ha especificado el id del clasificador presupuestario")
                    data['id_cp'] = id = int(request.GET['id'])
                    eClasiPres = ClasificadorPresupuestario.objects.get(id=id, status=True)
                    form = ClasificadorPresupuestarioFORM()
                    cod_rubro = ClasificadorPresupuestario.ultimo_rubro(eClasiPres.clasificadorpresupuestario_id,
                                                                        eClasiPres.codigo_naturaleza, eClasiPres.codigo_grupo,
                                                                        eClasiPres.codigo_subgrupo)
                    if cod_rubro:
                        cod_rubro = int(cod_rubro) + 1
                    else:
                        cod_rubro = 1
                    form.set_codigos(eClasiPres.codigo_naturaleza, eClasiPres.codigo_grupo, eClasiPres.codigo_subgrupo, cod_rubro)
                    form.set_queryset_catalogo(eClasiPres.clasificadorpresupuestario_id)

                    data['form'] = form
                    data['action'] = 'add_clasificador_presupuestario'
                    template = get_template('contabilidad/modalform.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edit_clasificador_presupuestario':
                try:
                    if not 'id' in request.GET:
                        raise NameError("No se ha especificado el id del clasificador presupuestario")
                    data['id_cp'] = id = int(request.GET['id'])
                    eClasiPres = ClasificadorPresupuestario.objects.get(id=id, status=True)
                    form = ClasificadorPresupuestarioFORM(initial=model_to_dict(eClasiPres))
                    form.set_queryset_catalogo(eClasiPres.clasificadorpresupuestario_id)
                    data['form'] = form
                    data['id'] = eClasiPres.id
                    data['action'] = 'edit_clasificador_presupuestario'
                    template = get_template('contabilidad/modalform.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'viewcatalogogeneralcuenta':
                try:
                    data['title'] = f"Configuración Catálogo de Cuentas Contables"
                    data['menu_principal'] = 1
                    data['menu_configuracion'] = 2

                    eCatalogoCuentaContable = CatalogoCuentaContable.objects.filter(
                        status=True).order_by('descripcion')
                    data['eCatalogoCuentaContables'] = eCatalogoCuentaContable

                    return render(request, "contabilidad/configuraciones/catalogocuenta/view.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/contabilidadposgrado")

            elif action == 'add_catalogo_cuenta_contable':
                try:
                    form = CatalogoClasificadorPresupuestarioFORM()
                    data['form'] = form
                    data['action'] = 'add_catalogo_cuenta_contable'
                    template = get_template('contabilidad/modalform.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'list_cuenta_contable':
                try:
                    if not 'id' in request.GET:
                        raise NameError("No se ha especificado el id del cuenta contable")
                    data['id_cat'] = id = int(request.GET['id'])
                    data['title'] = f"Cuentas Contables"
                    data['menu_principal'] = 1
                    data['menu_configuracion'] = 2
                    filtro = Q(status=True, catalogocuentacontable_id=id)
                    url_vars = f'&action=list_cuenta_contable&id={id}'
                    codigo = request.GET.get('codigo', '')
                    if codigo:
                        data['codigo'] = codigo
                        url_vars += "&codigo={}".format(codigo)
                        partes_codigo = codigo.split('.')
                        if len(partes_codigo) > 0 and partes_codigo[0]:  # Validar si la primera parte está presente
                            filtro &= Q(codigo_categoria=partes_codigo[0])
                        if len(partes_codigo) > 1 and partes_codigo[1]:  # Validar si la segunda parte está presente
                            filtro &= Q(codigo_grupo=partes_codigo[1])
                        if len(partes_codigo) > 2 and partes_codigo[2]:  # Validar si la tercera parte está presente
                            filtro &= Q(codigo_subgrupo=partes_codigo[2])
                        if len(partes_codigo) > 3 and partes_codigo[3]:  # Validar si la cuarta parte está presente
                            filtro &= Q(codigo_rubro=partes_codigo[3])
                        if len(partes_codigo) > 4 and partes_codigo[4]:  # Validar si la quinta parte está presente
                            filtro &= Q(codigo_subrubro=partes_codigo[4])

                    query = CuentaContable.objects.filter(filtro).order_by(
                        Coalesce('codigo_categoria', Value('\uffff')),
                        # Asigna un valor alto para que los nulos vayan al final
                        Coalesce('codigo_grupo', Value('\uffff')),
                        Coalesce('codigo_subgrupo', Value('\uffff')),
                        Coalesce('codigo_rubro', Value('\uffff')),
                        Coalesce('codigo_subrubro', Value('\uffff'))
                    )
                    paging = MiPaginador(query, 45)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data["url_vars"] = url_vars
                    data["eCuentaContables"] = page.object_list
                    return render(request,"contabilidad/configuraciones/catalogocuenta/list_cuentacontable.html", data)
                except Exception as ex:
                    pass

            elif action == 'add_cuenta_contable_cat':
                try:
                    if not 'id' in request.GET:
                        raise NameError("No se ha especificado el id del clasificador presupuestario")
                    data['id_cat'] = id_cat = int(request.GET['id'])

                    form = CuentaContableFORM()
                    form.set_queryset_catalogo(id_cat)
                    data['form'] = form
                    data['action'] = 'add_cuenta_contable'
                    template = get_template('contabilidad/configuraciones/catalogocuenta/form_cuentacontable.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'add_cuenta_contable':
                try:
                    if not 'id' in request.GET:
                        raise NameError("No se ha especificado el id de cuenta contable")
                    data['id'] = id = int(request.GET['id'])
                    eCuentaContable = CuentaContable.objects.get(id=id)

                    form = CuentaContableFORM()
                    form.set_queryset_catalogo(eCuentaContable.catalogocuentacontable_id)
                    form.set_codigos(eCuentaContable.codigo_categoria,
                                     eCuentaContable.codigo_grupo,
                                     eCuentaContable.codigo_subgrupo,
                                     eCuentaContable.codigo_rubro,
                                     eCuentaContable.codigo_subrubro)
                    data['form'] = form
                    data['action'] = 'add_cuenta_contable'
                    template = get_template('contabilidad/configuraciones/catalogocuenta/form_cuentacontable.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edit_cuenta_contable':
                try:
                    if not 'id' in request.GET:
                        raise NameError("No se ha especificado el id del cuenta contable")
                    data['id'] = id = int(request.GET['id'])
                    eCuentaContable = CuentaContable.objects.get(id=id)
                    form = CuentaContableFORM(initial=model_to_dict(eCuentaContable))
                    form.set_queryset_catalogo(eCuentaContable.catalogocuentacontable_id)
                    form.set_carrera(eCuentaContable.carrera_id)
                    data['asociaciones'] = eCuentaContable.get_asociacion_presupuestaria()
                    data['form'] = form
                    data['action'] = 'edit_cuenta_contable'
                    template = get_template('contabilidad/configuraciones/catalogocuenta/form_cuentacontable.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'buscar_clasificador':
                try:
                    filtro = Q(status=True)

                    q = request.GET['q'].upper().strip()
                    if not '.' in q:
                        s = q.split(" ")
                        if s.__len__() == 1:
                            filtro &= Q(nombre__icontains=q)
                        else:
                            filtro.add(Q(nombre__icontains=q), Q.OR)
                    else:
                        partes_codigo = q.split('.')
                        if len(partes_codigo) > 0 and partes_codigo[0]:  # Validar si la primera parte está presente
                            filtro &= Q(codigo_naturaleza=partes_codigo[0])
                        if len(partes_codigo) > 1 and partes_codigo[1]:  # Validar si la segunda parte está presente
                            filtro &= Q(codigo_grupo=partes_codigo[1])
                        if len(partes_codigo) > 2 and partes_codigo[2]:  # Validar si la tercera parte está presente
                            filtro &= Q(codigo_subgrupo=partes_codigo[2])
                        if len(partes_codigo) > 3 and partes_codigo[3]:  # Validar si la cuarta parte está presente
                            filtro &= Q(codigo_rubro=partes_codigo[3])

                    eClasificador = ClasificadorPresupuestario.objects.filter(filtro)
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.__str__()} for x in eClasificador]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'viewconfigurarflujoefectivo':
                try:
                    data['title'] = f"Configuración flujo de efectivo"
                    data['menu_principal'] = 1
                    data['menu_configuracion'] = 3

                    eConfFlujoEfectivo = ConfFlujoEfectivo.objects.filter(
                        status=True).order_by('orden')
                    data['eConfFlujoEfectivo'] = eConfFlujoEfectivo

                    data['exists'] = False
                    data['ingresado'] = False
                    if eConfFlujoEfectivo.exists():
                        if eConfFlujoEfectivo.count() >= 3:
                            data['exists'] = True
                            data['ingresado'] = True
                            data['action'] = 'editconfigurarflujoefectivo'
                        else:
                            data['action'] = 'addconfigurarflujoefectivo'
                            data['ingresado'] = False
                    else:
                        data['action'] = 'addconfigurarflujoefectivo'

                    return render(request, "contabilidad/configuraciones/flujodeefectivo/view.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/contabilidadposgrado")

            elif action == 'viewconfigurarestadoresultado':
                try:
                    data['title'] = f"Configuración Estado de resultado integral"
                    data['menu_principal'] = 1
                    data['menu_configuracion'] = 4

                    eConfEstadoResultadoIntegralCuentas = ConfEstadoResultadoIntegral.objects.filter(status=True)
                    data['eConfEstadoResultadoIntegralCuentas'] =eConfEstadoResultadoIntegralCuentas
                    return render(request, "contabilidad/configuraciones/estadoderesultado/view.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/contabilidadposgrado")

            elif action == 'addconfigurarflujoefectivo':
                try:
                    template = get_template('contabilidad/configuraciones/flujodeefectivo/form_configflujo.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'data': str(ex)})

            elif action == 'buscar_cuenta_contable':
                try:
                    filtro = Q(status=True)

                    q = request.GET['q'].upper().strip()
                    if not '.' in q:
                        s = q.split(" ")
                        if s.__len__() == 1:
                            filtro &= Q(nombre__icontains=q)
                        else:
                            filtro.add(Q(nombre__icontains=q), Q.OR)
                    else:
                        partes_codigo = q.split('.')
                        if len(partes_codigo) > 0 and partes_codigo[0]:  # Validar si la primera parte está presente
                            filtro &= Q(codigo_categoria=partes_codigo[0])
                        if len(partes_codigo) > 1 and partes_codigo[1]:  # Validar si la segunda parte está presente
                            filtro &= Q(codigo_grupo=partes_codigo[1])
                        if len(partes_codigo) > 2 and partes_codigo[2]:  # Validar si la tercera parte está presente
                            filtro &= Q(codigo_subgrupo=partes_codigo[2])
                        if len(partes_codigo) > 3 and partes_codigo[3]:  # Validar si la cuarta parte está presente
                            filtro &= Q(codigo_rubro=partes_codigo[3])
                        if len(partes_codigo) > 4 and partes_codigo[4]:  # Validar si la quinta parte está presente
                            filtro &= Q(codigo_subrubro=partes_codigo[4])

                    eCuentaContables = CuentaContable.objects.filter(filtro)
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.__str__(), "tipo": x.get_tipo_display()} for x in eCuentaContables]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'viewhojadetrabajoposgradopersonal':
                try:
                    data['title'] = f'Balances de costos - hoja de trabajo'
                    eGestionPosgrados = GestionPosgrado.objects.filter(status=True)
                    primera_gestion=None
                    if eGestionPosgrados.exists():
                        primera_gestion = eGestionPosgrados.first()
                    data['primera_gestion'] = primera_gestion
                    data['menu_principal'] = 1
                    data['menu_configuracion'] = 0
                    data['eGestionPosgrados'] = eGestionPosgrados

                    return render(request, "contabilidad/plantilla/hojadetrabajopersonal/view.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/contabilidadposgrado")

            elif action == 'add_gestion_hoja_trabajo':
                try:
                    form = GestionHojaTrabajoForm()
                    data['form'] = form
                    template = get_template('contabilidad/balancecosto/form.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edit_gestion_hoja_trabajo':
                try:
                    id =int(request.GET.get('id','0')or '0')
                    if id == 0:
                        raise NameError("Parametro no encontrado")
                    eGestionPosgrado = GestionPosgrado.objects.get(pk=id)

                    form = GestionHojaTrabajoForm(initial=model_to_dict(eGestionPosgrado))
                    data['id'] = id
                    data['form'] = form
                    template = get_template('contabilidad/balancecosto/form.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edit_programa_aplica_profesor_invitado':
                try:
                    eConfiguracionProgramaProfesorInvitado = ConfiguracionProgramaProfesorInvitado.objects.filter(status=True)
                    if eConfiguracionProgramaProfesorInvitado.exists():
                        form =ConfigurarCarreraProfesorInvitadoForm(initial=model_to_dict(eConfiguracionProgramaProfesorInvitado.first()))
                    else:
                        form = ConfigurarCarreraProfesorInvitadoForm()

                    data['form'] = form
                    template = get_template('contabilidad/balancecosto/form.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editar_rmu_coordinador_apoyo':
                try:
                    eConfiguracionProgramaProfesorInvitado = ConfiguracionProgramaProfesorInvitado.objects.filter(status=True)
                    if eConfiguracionProgramaProfesorInvitado.exists():
                        form =ConfigurarRmuForm(initial={
                            'rmu':eConfiguracionProgramaProfesorInvitado.first().rmu_coordinador_de_apoyo
                        })
                    else:
                        form = ConfigurarRmuForm()

                    data['form'] = form
                    template = get_template('contabilidad/balancecosto/form.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'add_integrante_gestion_hoja_trabajo':
                try:
                    form = IntegranteGestionHojaTrabajoForm()
                    data['id'] = int(request.GET.get('id','0'))
                    data['form'] = form
                    template = get_template('contabilidad/balancecosto/form.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edit_integrante_gestion_hoja_trabajo':
                try:
                    id =int(request.GET.get('id','0') or '0')
                    if id == 0:
                        raise NameError("Parametro no encontrado")
                    eGestionIntegrantesPosgrado = GestionIntegrantesPosgrado.objects.get(pk=id)

                    form = IntegranteGestionHojaTrabajoForm(initial=model_to_dict(eGestionIntegrantesPosgrado))
                    form.edit(eGestionIntegrantesPosgrado.persona.pk)
                    data['id'] = id
                    data['form'] = form
                    template = get_template('contabilidad/balancecosto/form.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'add_actividad_integrante_gestion_hoja_trabajo':
                try:
                    form = ActividadIntegranteGestionHojaTrabajoForm()
                    data['id'] = int(request.GET.get('id','0'))
                    data['form'] = form
                    template = get_template('contabilidad/balancecosto/form.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edit_actividad_integrante_gestion_hoja_trabajo':
                try:
                    id =int(request.GET.get('id','0') or '0')
                    if id == 0:
                        raise NameError("Parametro no encontrado")

                    eGestionIntegrantesActividadCarreraPosgrado = GestionIntegrantesActividadCarreraPosgrado.objects.get(pk=id)

                    form = ActividadIntegranteGestionHojaTrabajoForm(initial=model_to_dict(eGestionIntegrantesActividadCarreraPosgrado))
                    if eGestionIntegrantesActividadCarreraPosgrado.carrera:
                        form.edit(eGestionIntegrantesActividadCarreraPosgrado.carrera.pk)
                    data['id'] = id
                    data['form'] = form
                    template = get_template('contabilidad/balancecosto/form.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result":False, "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'addbalancecosto':
                try:
                    form = BalanceCostoForm(initial={'anio': anio_actual})
                    data['form'] = form
                    template = get_template('contabilidad/balancecosto/form.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'viewbalancecosto_panel':
                try:
                    data['title'] = f'Balances de costos mensual dashboard'
                    data['menu_principal'] = 2
                    data['balance_de_costo_menu'] = 0
                    pk = int(request.GET.get('pk','0'))
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eBalanceCosto = BalanceCosto.objects.get(pk=pk)
                    data['eBalanceCosto'] = eBalanceCosto
                    return render(request, "contabilidad/balancecosto/reportes/panel/view.html", data)
                except Exception as ex:
                    messages.error(request,f'Ocurrió un error al abrir el reporte: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
                    return HttpResponseRedirect(f"/contabilidadposgrado?action=viewbalancecosto")

            elif action == 'viewbalancecosto_reportes':
                try:
                    data['title'] = f'Balances de costos mensual'
                    data['menu_principal'] = 2
                    data['balance_de_costo_menu'] = 5
                    pk = int(request.GET.get('pk','0'))
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eBalanceCosto = BalanceCosto.objects.get(pk=pk)
                    datos_para_template = eBalanceCosto.get_reporte_mensual()
                    data['eBalanceCosto'] = eBalanceCosto
                    data['eBalanceCostoReporteMensual'] = datos_para_template
                    return render(request, "contabilidad/balancecosto/reportes/reporte/view.html", data)
                except Exception as ex:
                    messages.error(request,f'Ocurrió un error al abrir el reporte: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
                    return HttpResponseRedirect(f"/contabilidadposgrado?action=viewbalancecosto")

            elif action == 'viewbalancecosto_reportes_coordinador':
                try:
                    data['title'] = f'Balances de costos - Reportes coordinador'
                    data['menu_principal'] = 2
                    data['balance_de_costo_menu'] = 1
                    pk = int(request.GET.get('pk', '0'))
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eBalanceCosto = BalanceCosto.objects.get(pk=pk)
                    datos_para_template = eBalanceCosto.get_reporte_coordinadores()
                    data['eBalanceCosto'] = eBalanceCosto
                    data['eBalanceCostoReporteCoordinadores'] = datos_para_template
                    return render(request, "contabilidad/balancecosto/reportes/coordinadorprograma/view.html", data)
                except Exception as ex:
                    messages.error(request,f'Ocurrió un error al abrir el reporte: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
                    return HttpResponseRedirect(f"/contabilidadposgrado?action=viewbalancecosto")

            elif action == 'viewbalancecosto_reportes_coordinadorapoyo':
                try:
                    data['title'] = f'Balances de costos - Reportes coordinador apoyo'
                    data['menu_principal'] = 2
                    data['balance_de_costo_menu'] = 2
                    pk = int(request.GET.get('pk', '0'))
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eBalanceCosto = BalanceCosto.objects.get(pk=pk)
                    datos_para_template = eBalanceCosto.get_reporte_coordinadores_apoyo()

                    data['eBalanceCosto'] = eBalanceCosto
                    data['eBalanceCostoReporteCoordinadoresApoyo'] = datos_para_template
                    return render(request, "contabilidad/balancecosto/reportes/coordinadorapoyo/view.html", data)
                except Exception as ex:
                    messages.error(request,f'Ocurrió un error al abrir el reporte: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
                    return HttpResponseRedirect(f"/contabilidadposgrado?action=viewbalancecosto")

            elif action == 'viewbalancecosto_reportes_profesormodulo':
                try:
                    data['title'] = f'Balances de costos - Reportes profesor módulo'
                    data['menu_principal'] =2
                    data['balance_de_costo_menu'] = 3
                    pk = int(request.GET.get('pk', '0'))
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eBalanceCosto = BalanceCosto.objects.get(pk=pk)
                    datos_para_template = eBalanceCosto.get_reporte_profesor_modular()
                    data['eBalanceCosto'] = eBalanceCosto
                    data['eBalanceCostoReporteProfesorModular'] = datos_para_template
                    return render(request, "contabilidad/balancecosto/reportes/profesormodular/view.html", data)
                except Exception as ex:
                    messages.error(request,f'Ocurrió un error al abrir el reporte: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
                    return HttpResponseRedirect(f"/contabilidadposgrado?action=viewbalancecosto")

            elif action == 'viewbalancecosto_reportes_profesormodulo_invitado':
                try:
                    data['title'] = f'Balances de costos - Reportes profesor módulo posgrado'
                    data['menu_principal'] = 2
                    data['balance_de_costo_menu'] = 6
                    pk = int(request.GET.get('pk', '0'))
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eBalanceCosto = BalanceCosto.objects.get(pk=pk)
                    form =ProfesorInvitadoValoresForm(initial={
                        'medio_tiempo':eBalanceCosto.medio_tiempo,
                        'tiempo_completo':eBalanceCosto.tiempo_completo,
                        'cantidad_tiempo_completo':eBalanceCosto.cantidad_tiempo_completo,
                        'cantidad_medio_tiempo':eBalanceCosto.cantidad_medio_tiempo,
                    })
                    datos_para_template = eBalanceCosto.get_reporte_profesor_modular_invitado()
                    data['form'] = form
                    data['eBalanceCosto'] = eBalanceCosto
                    data['eBalanceCostoReporteProfesorModularInvitado'] = datos_para_template
                    return render(request, "contabilidad/balancecosto/reportes/profesormodularinvitado/view.html", data)
                except Exception as ex:
                    messages.error(request,f'Ocurrió un error al abrir el reporte: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
                    return HttpResponseRedirect(f"/contabilidadposgrado?action=viewbalancecosto")

            elif action == 'viewbalancecosto_reportes_personal_administrativo':
                try:
                    data['title'] = f'Balances de costos - Reportes personal administrativo'
                    data['menu_principal'] = 2
                    data['balance_de_costo_menu'] = 4
                    pk = int(request.GET.get('pk', '0'))
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eBalanceCosto = BalanceCosto.objects.get(pk=pk)
                    datos_para_template = eBalanceCosto.get_reporte_personal_administrativo()
                    data['eBalanceCosto'] = eBalanceCosto
                    eGestionPosgradoHojaTrabajo = GestionPosgradoHojaTrabajo.objects.filter(status=True,balancecosto=eBalanceCosto)
                    primera_gestion = None
                    if eGestionPosgradoHojaTrabajo.exists():
                        primera_gestion = eGestionPosgradoHojaTrabajo.first()
                    data['primera_gestion'] = primera_gestion
                    data['eGestionPosgrados'] = eGestionPosgradoHojaTrabajo
                    data['eBalanceCostoReportePersonalAdministrativo'] = datos_para_template
                    return render(request, "contabilidad/balancecosto/reportes/personaladministrativo/view.html", data)
                except Exception as ex:
                    messages.error(request,f'Ocurrió un error al abrir el reporte: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
                    return HttpResponseRedirect(f"/contabilidadposgrado?action=viewbalancecosto")

            elif action == 'viewbalancecosto_reportes_costo_variable':
                try:
                    data['title'] = f'Balances de costos - Reporte costos variables'
                    data['menu_principal'] = 2
                    data['balance_de_costo_menu'] = 7
                    pk = int(request.GET.get('pk', '0'))
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eBalanceCosto = BalanceCosto.objects.get(pk=pk)

                    form = CostoVariableValoresForm(initial={
                        'costo_por_publicidad': eBalanceCosto.costo_por_publicidad,
                        'evento_promocionales': eBalanceCosto.evento_promocionales,
                        'materiales_de_oficina': eBalanceCosto.materiales_de_oficina,
                    })

                    datos_para_template = eBalanceCosto.get_reporte_costo_variable()
                    data['eBalanceCosto'] = eBalanceCosto
                    data['form'] = form
                    data['eBalanceCostoReporteCostoVariable'] = datos_para_template
                    return render(request, "contabilidad/balancecosto/reportes/costovariable/view.html", data)
                except Exception as ex:
                    messages.error(request, f'Ocurrió un error al abrir el reporte: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
                    return HttpResponseRedirect(f"/contabilidadposgrado?action=viewbalancecosto")

            elif action == 'buscarpersona':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    filtro = Q(usuario__isnull=False,status=True)
                    if len(s) == 1:
                        filtro &= ((Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(cedula__icontains=q) | Q(apellido2__icontains=q) | Q(cedula__contains=q)))
                    elif len(s) == 2:
                        filtro &= ((Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) |
                                   (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1])) |
                                   (Q(nombres__icontains=s[0]) & Q(apellido1__contains=s[1])))
                    else:
                        filtro &= ((Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(apellido2__contains=s[2])) |
                                   (Q(nombres__contains=s[0]) & Q(nombres__contains=s[1]) & Q(apellido1__contains=s[2])))

                    per = Persona.objects.filter(filtro).exclude(cedula='').order_by('apellido1', 'apellido2', 'nombres').distinct()[:15]
                    return JsonResponse({"result": "ok", "results": [{"id": x.id, "name": "%s %s" % (f"<img src='{x.get_foto()}' width='25' height='25' style='border-radius: 20%;' alt='...'>", x.nombre_completo_inverso())} for x in per]})
                except Exception as ex:
                    pass

            elif action == 'buscar_carrera':
                try:
                    maestriaadmision_id = CohorteMaestria.objects.filter(periodoacademico__tipo_id=3, status=True).values_list('maestriaadmision_id', flat=True)
                    # eMaestriasAdmisions = MaestriasAdmision.objects.filter(status=True,   id__in=maestriaadmision_id).order_by('id').distinct()
                    eMaestriasAdmisions = MaestriasAdmision.objects.values_list('carrera_id', flat=True).filter(status=True, id__in=maestriaadmision_id).order_by('id').distinct()
                    # ids_carreras = []
                    # for eMaestriasAdmision in eMaestriasAdmisions:
                    #     if eMaestriasAdmision.cohortes_maestria_activas():
                    #         ids_carreras.append(eMaestriasAdmision.carrera.pk)

                    eCarrera = Carrera.objects.filter(status=True, pk__in=eMaestriasAdmisions)
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if s.__len__() == 1:
                        carreras = eCarrera.filter(Q(nombre__icontains=q) | Q(nombrevisualizar__icontains=s[0]),
                                                          status=True )
                    else:
                        carreras = eCarrera.filter(Q(nombre__icontains=q) | Q(nombrevisualizar__icontains=s[0]),
                                                          status=True ).distinct()[:70]

                    data = {"result": "ok", "results": [{"id": x.id, "name": x.__str__()} for x in carreras]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'dowload_balance_costo_mensual':
                try:
                    pk = int(request.GET.get('id', '0') or '0')
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eBalanceCosto = BalanceCosto.objects.get(pk=pk)
                    return eBalanceCosto.generar_reporte_balance_costo_mensual_excel(request)
                except Exception as ex:
                    pass

            elif action == 'dowload_coordinador_programa':
                try:
                    pk = int(request.GET.get('id', '0') or '0')
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eBalanceCosto = BalanceCosto.objects.get(pk=pk)
                    return eBalanceCosto.generar_reporte_balance_costo_mensual_coordinador_programa_excel(request)
                except Exception as ex:
                    pass

            elif action == 'dowload_coordinador_apoyo':
                try:
                    pk = int(request.GET.get('id', '0') or '0')
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eBalanceCosto = BalanceCosto.objects.get(pk=pk)
                    return eBalanceCosto.generar_reporte_balance_costo_mensual_coordinador_apoyo_excel(request)
                except Exception as ex:
                    pass

            elif action == 'dowload_profesor_posgrado':
                try:
                    pk = int(request.GET.get('id', '0') or '0')
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eBalanceCosto = BalanceCosto.objects.get(pk=pk)
                    return eBalanceCosto.generar_reporte_balance_costo_mensual_profesor_posgrado_excel(request)
                except Exception as ex:
                    pass

            elif action == 'dowload_costos_variables':
                try:
                    pk = int(request.GET.get('id', '0') or '0')
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eBalanceCosto = BalanceCosto.objects.get(pk=pk)
                    return eBalanceCosto.generar_reporte_balance_costo_mensual_costo_variable_excel(request)
                except Exception as ex:
                    pass

            elif action == 'dowload_personal_administrativo':
                try:
                    pk = int(request.GET.get('id', '0') or '0')
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eBalanceCosto = BalanceCosto.objects.get(pk=pk)
                    return eBalanceCosto.generar_reporte_balance_costo_mensual_personal_administrativo_excel(request)
                except Exception as ex:
                    pass

            elif action == 'dowload_profesor_modular':
                try:
                    pk = int(request.GET.get('id', '0') or '0')
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eBalanceCosto = BalanceCosto.objects.get(pk=pk)
                    return eBalanceCosto.generar_reporte_balance_costo_mensual_profesor_modular_excel(request)
                except Exception as ex:
                    pass

            elif action == 'generar_balance_costo_mensual_acumulado':
                try:
                    import json
                    ids = json.loads(request.GET.getlist('ids')[0])
                    eBalanceCosto = BalanceCosto.objects.filter(pk__in = ids)
                    return  eBalanceCosto.first().generar_reporte_mensual_acumulado_excel(request,ids)
                except Exception as ex:
                    pass

            elif action == 'loadasignaturasprofesormodular':
                try:
                    pk = int(request.GET.get('id', '0') or '0')
                    carrera_id = int(request.GET.get('carrera_id', '0') or '0')
                    periodo_id = int(request.GET.get('periodo_id', '0') or '0')
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    if carrera_id == 0:
                        raise NameError("Parametro no encontrado")
                    if periodo_id == 0:
                        raise NameError("Parametro no encontrado")
                    eCarrera = Carrera.objects.get(pk=carrera_id)
                    ePeriodo = Periodo.objects.get(pk=periodo_id)
                    eBalanceCosto = BalanceCosto.objects.get(pk=pk)
                    niveles_y_materias_materias = eBalanceCosto.get_materias_de_niveles_y_materia(ePeriodo, eBalanceCosto.get_mallas(eCarrera))
                    data['niveles_y_materias_materias'] = niveles_y_materias_materias
                    template = get_template('contabilidad/balancecosto/reportes/profesormodular/modal/detalleasignatura.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'loadasignaturasprofesormodularcoordinadorapoyo':
                try:
                    pk = int(request.GET.get('id', '0') or '0')
                    carrera_id = int(request.GET.get('carrera_id', '0') or '0')
                    periodo_id = int(request.GET.get('periodo_id', '0') or '0')
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    if carrera_id == 0:
                        raise NameError("Parametro no encontrado")
                    if periodo_id == 0:
                        raise NameError("Parametro no encontrado")
                    eCarrera = Carrera.objects.get(pk=carrera_id)
                    ePeriodo = Periodo.objects.get(pk=periodo_id)
                    eBalanceCosto = BalanceCosto.objects.get(pk=pk)
                    diccionario_coordinadores_de_apoyos = eBalanceCosto.get_todos_los_profesores_de_niveles_y_materia_coordinadores_de_apoyo()
                    eBalanceCostoReporteCoordinadoresApoyo = eBalanceCosto.get_balancecostoreportecoordinadorapoyo()
                    paralelos_de_niveles_y_materia = eBalanceCosto.get_paralelos_de_niveles_y_materia_coordinador(ePeriodo,eBalanceCosto.get_mallas(eCarrera),diccionario_coordinadores_de_apoyos)
                    data['paralelos_de_niveles_y_materia'] = paralelos_de_niveles_y_materia
                    template = get_template('contabilidad/balancecosto/reportes/coordinadorapoyo/modal/detalleasignatura.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'viewflujodeefectivo':
                try:
                    data['title'] = f'Flujo de efetivo'
                    data['menu_principal'] = 3
                    filtro = Q(status=True)
                    url_vars = '&action=viewbalancecosto'

                    if pk := request.GET.get('pk', ''):
                        filtro &= Q(pk=pk)
                        url_vars += "&pk={}".format(pk)
                    eFlujoEfectivoMensual = FlujoEfectivoMensual.objects.filter(filtro).order_by('anio', '-mes')

                    paging = MiPaginador(eFlujoEfectivoMensual, 12)
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
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['eFlujosEfectivos'] = page.object_list
                    data['url_vars'] = url_vars

                    return render(request, "contabilidad/flujoefectivo/view.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/contabilidadposgrado")

            elif action == 'viewflujoefectivo_panel':
                try:
                    data['title'] = f'Flujo de efectivo'
                    data['menu_principal'] = 3
                    data['flujo_de_efectivo_menu'] = 0
                    pk = int(request.GET.get('pk','0'))
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eFlujoEfectivoMensual = FlujoEfectivoMensual.objects.get(pk=pk)
                    data['eFlujoEfectivoMensual'] = eFlujoEfectivoMensual
                    return render(request, "contabilidad/flujoefectivo/reportes/view.html", data)
                except Exception as ex:
                    messages.error(request,f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
                    return HttpResponseRedirect(f"/contabilidadposgrado?action=viewflujodeefectivo")

            elif action == 'addflujoefectivo':
                try:
                    form = FlujoEfectivoForm(initial={'anio': anio_actual})
                    form.cargar_meses_aprobados(anio_actual)
                    data['form'] = form
                    template = get_template('contabilidad/flujoefectivo/form.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'dowload_flujoefectivo__mensual':
                try:
                    pk = int(request.GET.get('id', '0') or '0')
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eFlujoEfectivoMensual = FlujoEfectivoMensual.objects.get(pk=pk)
                    return eFlujoEfectivoMensual.generar_reporte_flujo_efectivo_mensual_excel(request)
                except Exception as ex:
                    messages.error(request,f'Ocurrió un error al abrir el reporte: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
                    return HttpResponseRedirect(f"/contabilidadposgrado?action=viewflujodeefectivo")

            elif action == 'asociarcuentaflujoefectivo':
                try:
                    pk = int(request.GET.get('id', '0') or '0')
                    eConfCuentaFlujoEfectivo = CuentaContable.objects.get(pk = pk)
                    form = AsociarCuentaFlujoEfectivoTotalForm(initial={'configuracioncampo': eConfCuentaFlujoEfectivo.configuracioncampo})
                    data['id'] = pk
                    data['form'] = form
                    template = get_template('contabilidad/modalform.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'add_cuenta_conf_estado_resultado':
                try:
                    form = CuentaEstadoResultadoIntegralForm()
                    data['form'] = form
                    template = get_template('contabilidad/modalform.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'viewestadoresultado':
                try:
                    data['title'] = f'Estado de Resultado'
                    data['menu_principal'] = 5
                    data['eEstadoResultadoIntegrales'] = EstadoResultadoIntegral.objects.filter(status=True)

                    return render(request, "contabilidad/estadoresultado/view.html", data)
                except Exception as ex:
                    messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
                    return HttpResponseRedirect(f"/contabilidadposgrado?action=viewestadoresultado")

            elif action == 'addestadoresultado':
                try:
                    form = EstadoResultadoIntegralFORM(initial={'anio': anio_actual})
                    form.init_meses_x_anio(anio_actual)
                    data['form'] = form
                    template = get_template('contabilidad/estadoresultado/form.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'actualiza_seleccion_meses':
                try:
                    anio = int(request.GET.get('anio', '0') or '0')
                    query_meses = FlujoEfectivoMensual.objects.filter(status=True, anio=anio).values_list('mes', flat=True).distinct()
                    meses_filter = [(id_mes, mes) for id_mes, mes in MESES_CHOICES if id_mes in query_meses]
                    if meses_filter:
                        meses_filter = [(0, 'Todos')] + meses_filter
                    return JsonResponse({"isSuccess": True, 'meses_filter': meses_filter})

                except Exception as ex:
                    pass

            elif action == 'detalle_estadoresultado':
                try:
                    data['title'] = f'Estado de Resultado'
                    data['menu_principal'] = 5

                    if not 'id' in request.GET:
                        raise NameError("No se envió el id de estado de resultado")
                    id = int(request.GET.get('id', '0') or '0')
                    if id == 0:
                        raise NameError("No se envió el id de estado de resultado")
                    estadoResutlado = EstadoResultadoIntegral.objects.get(pk=id)

                    eDetalles = DetalleEstadoResultadoIntegral.objects.filter(estado_resultado_integral=estadoResutlado).order_by('cuentacontable__tipo',Coalesce('cuentacontable__codigo_categoria', Value('\uffff')), Coalesce('cuentacontable__codigo_grupo', Value('\uffff')),Coalesce('cuentacontable__codigo_subgrupo', Value('\uffff')),Coalesce('cuentacontable__codigo_rubro', Value('\uffff')),Coalesce('cuentacontable__codigo_subrubro', Value('\uffff')))
                    data['eDetalles'] = eDetalles
                    return render(request, "contabilidad/estadoresultado/detalle_resultado.html", data)
                except Exception as ex:
                    messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
                    return HttpResponseRedirect(f"/contabilidadposgrado?action=viewestadoresultado")

            elif action == 'dowload_estadoresultado':
                try:
                    pk = int(request.GET.get('id', '0') or '0')
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eFlujoEfectivoMensual = EstadoResultadoIntegral.objects.get(pk=pk)
                    return eFlujoEfectivoMensual.generar_reporte_estadoresultadointegral_excel(request)
                except Exception as ex:
                    messages.error(request,f'Ocurrió un error al abrir el reporte: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
                    return HttpResponseRedirect(f"/contabilidadposgrado?action=viewestadoresultado")

            elif action == 'view_configurar_ejecucionpresupuestaria':
                try:
                    data['title'] = f'Configuración de ejecución presupuestaria'
                    data['menu_principal'] = 1
                    data['menu_configuracion'] = 5
                    eConfigEjecucionPresupuestarias = ConfigEjecucionPresupuestaria.objects.filter(status=True).order_by('cuentacontable__tipo',Coalesce('cuentacontable__codigo_categoria', Value('\uffff')), Coalesce('cuentacontable__codigo_grupo', Value('\uffff')),Coalesce('cuentacontable__codigo_subgrupo', Value('\uffff')),Coalesce('cuentacontable__codigo_rubro', Value('\uffff')),Coalesce('cuentacontable__codigo_subrubro', Value('\uffff')))
                    data['eConfigEjecucionPresupuestarias'] = eConfigEjecucionPresupuestarias
                    return render(request, "contabilidad/configuraciones/ejecucionpresupuestaria/view.html", data)
                except Exception as ex:
                    pass

            elif action == 'add_configuracion_ejecucionpresupuestaria':
                try:
                    form = CuentaEjecucionPresupuestariaFORM()
                    data['form'] = form
                    template = get_template('contabilidad/modalform.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'view_ejecucionpresupuestaria':
                try:
                    data['title'] = f'Ejecución Presupuestaria'
                    data['menu_principal'] = 6
                    data['eEjecucionPresupuestarias'] = EjecucionPresupuestaria.objects.filter(status=True)

                    return render(request, "contabilidad/ejecucion_presupuestaria/view.html", data)
                except Exception as ex:
                    messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
                    return HttpResponseRedirect(f"/contabilidadposgrado?action=view_ejecucionpresupuestaria")

            elif action == 'add_ejecucionpresupuestaria':
                try:
                    form = EjecucionPresupuestariaFORM(initial={'anio': anio_actual})
                    form.init_meses_x_anio(anio_actual)
                    data['form'] = form
                    template = get_template('contabilidad/ejecucion_presupuestaria/form.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'detalle_ejecucionpresupuestaria':
                try:
                    data['title'] = f'Ejecución Presupuestaria'
                    data['menu_principal'] = 6

                    if not 'id' in request.GET:
                        raise NameError("No se envió el id de ejecución presupuestaria")
                    id = int(request.GET.get('id', '0') or '0')
                    if id == 0:
                        raise NameError("No se envió el id de ejecución presupuestaria")
                    eEjecucionPresupuestaria = EjecucionPresupuestaria.objects.get(pk=id)

                    eDetalles = DetalleEjecucionPresupuestaria.objects.filter(ejecucion_presupuestaria=eEjecucionPresupuestaria)
                    data['eDetalles'] = eDetalles
                    return render(request,
                                  "contabilidad/ejecucion_presupuestaria/detalle_ejecucion_presupuestaria.html", data)
                except Exception as ex:
                    messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
                    return HttpResponseRedirect(f"/contabilidadposgrado?action=view_ejecucionpresupuestaria")

            elif action == 'dowload_ejecucionpresupuestaria':
                try:
                    pk = int(request.GET.get('id', '0') or '0')
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eEjecucionPresupuestaria = EjecucionPresupuestaria.objects.get(pk=pk)
                    return eEjecucionPresupuestaria.generar_reporte_ejecucionpresupuestaria_excel(request)
                except Exception as ex:
                    messages.error(request,
                                   f'Ocurrió un error al abrir el reporte: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
                    return HttpResponseRedirect(f"/contabilidadposgrado?action=view_ejecucionpresupuestaria")

        else:
            try:
                data['title'] = f'Contabilidad posgrado'
                data['menu_principal'] = 0
                return render(request, "contabilidad/view.html", data)
            except Exception as ex:
                pass


def clonar_flujo_efectivo(eEstadoResultadoIntegral, meses, request):
    try:
        meses = meses
        anio = int(eEstadoResultadoIntegral.anio)

        eCuentasEstadoResultado = ConfEstadoResultadoIntegral.objects.filter(status=True).values_list('cuentacontable_id', flat=True).distinct()

        for cuenta in eCuentasEstadoResultado:
            valor_acumulado = CuentaFlujoEfectivoMensual.objects.filter(
                status=True,
                actividadflujoefectivomensual__status=True,
                actividadflujoefectivomensual__flujoefectivomensual__status=True,
                cuentacontable_id=cuenta,
                actividadflujoefectivomensual__flujoefectivomensual__mes__in=meses,
                actividadflujoefectivomensual__flujoefectivomensual__anio=anio,
                actividadflujoefectivomensual__flujoefectivomensual__estado=FlujoEfectivoMensual.TipoEstado.VALIDADO).aggregate(Sum('valor'))['valor__sum']

            eDetalle = DetalleEstadoResultadoIntegral(
                estado_resultado_integral=eEstadoResultadoIntegral,
                cuentacontable_id=cuenta,
                valor=valor_acumulado if valor_acumulado else 0,
            )
            eDetalle.save(request)
        return {'result': True, 'message': ''}
    except Exception as ex:
        return {'result': False, 'message': f'Ocurrió un error al clonar el estado de resultado: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}'}

def clonar_flujo_efectivo_ejecucion_presupuestaria(eEjecucionPresupuestaria, meses, request):
    try:
        meses = meses
        anio = int(eEjecucionPresupuestaria.anio)

        eCuentasEstadoResultado = ConfigEjecucionPresupuestaria.objects.filter(status=True).values_list('cuentacontable_id', flat=True).distinct()

        for cuenta in eCuentasEstadoResultado:

            eCuentaFlujo = CuentaFlujoEfectivoMensual.objects.filter(
                status=True,
                actividadflujoefectivomensual__status=True,
                actividadflujoefectivomensual__flujoefectivomensual__status=True,
                cuentacontable_id=cuenta,
                actividadflujoefectivomensual__flujoefectivomensual__mes__in=meses,
                actividadflujoefectivomensual__flujoefectivomensual__anio=anio,
                actividadflujoefectivomensual__flujoefectivomensual__estado=FlujoEfectivoMensual.TipoEstado.VALIDADO)

            if eCuentaFlujo:
                eDetalle = DetalleEjecucionPresupuestaria(
                    ejecucion_presupuestaria=eEjecucionPresupuestaria,
                    cuentacontable_id=cuenta
                )
                eDetalle.save(request)
        return {'result': True, 'message': ''}
    except Exception as ex:
        return {'result': False, 'message': f'Ocurrió un error al clonar el ejecucion presupuestaria: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}'}

def validar_get_crear_puntoequilibrio(id, tip_id, request):
    try:
        ePuntoEquilibrio = None
        if tip_id == 'carrera':
            eCarrera = Carrera.objects.get(pk=id)
            ePuntoEquilibrio = PuntoEquilibrio.objects.filter(carrera_id=id, status=True).first()
        else:
            ePuntoEquilibrio = PuntoEquilibrio.objects.filter(id=id).first()
        if ePuntoEquilibrio:
            ePuntoEquilibrio = ePuntoEquilibrio
        else:
            ePuntoEquilibrio = PuntoEquilibrio(
                carrera=eCarrera
            )
            ePuntoEquilibrio.save(request)
        return {'isSuccess': True, 'ePuntoEquilibrio': ePuntoEquilibrio}
    except Exception as ex:
        return {'isSuccess': False, 'message': f'Ocurrió un error al validar el punto de equilibrio: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}'}
