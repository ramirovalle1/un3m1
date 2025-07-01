# -*- coding: UTF-8 -*-
import io
import json
import math
import sys
from datetime import datetime
from datetime import timedelta
from datetime import date
from dateutil.relativedelta import relativedelta
import random
import xlsxwriter
from urllib.request import urlopen

from django import forms
from django.forms import model_to_dict

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template


from decorators import secure_module
from sagest.forms import CabPlanificacionTHForm, PeriodoPlanificacionTHForm, CambiarEstadoDepartamentoForm, \
    CambiarEstadoGestionPlanificacionTHForm, MoverGestionForm, ResponsableGestionForm, CambiarAprobarUathForm, \
    CambiarProductoForm, CopiarUnidadForm, ImportarActividadesForm
from sagest.funciones import encrypt_id
from sagest.models import CabPlanificacionTH, SeccionDepartamento, ProductoServicioSeccion, TIPO_ACTIVIDAD_TH, \
    FRECUENCIA_TH, ActividadSecuencialTH, PeriodoPlanificacionTH, ReporteBrechasTH, Departamento, \
    GestionPlanificacionTH, HistorialGestionPlanificacionTH, HistorialCabPlanificacionTH, ReporteBrechasPeriodoTH, \
    DistributivoPersona, GestionProductoServicioTH, ProductoServicioTh, ActividadPresupuestoObra
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log
from sga.models import MONTH_NAMES, PersonaDatosFamiliares, Persona
from sga.templatetags.sga_extras import encrypt
from utils.filtros_genericos import filtro_persona_select


def calculabrecha(primero,segundo):
    resultado = primero-segundo
    letras='SERVIDORES EXCEDENTES'
    if resultado < 0:
        resultado = resultado*(-1)
        letras = 'SERVIDORES REQUERIDOS'
    elif resultado == 0:
        letras = ''
    respuesta = {'valor':  resultado,'letras':letras}
    return respuesta


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module



def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    hoy = datetime.now()
    data['puede_gestionar_plantilla'] = puede_gestionar_plantilla = request.user.has_perm('sagest.puede_gestionar_plantilla')
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addperiodo':
            try:
                f = PeriodoPlanificacionTHForm(request.POST)
                if f.is_valid():
                    if PeriodoPlanificacionTH.objects.filter(anio = f.cleaned_data['anio'],status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El registro ya existe."})
                    periodo = PeriodoPlanificacionTH(anio=f.cleaned_data['anio'],
                                            activo=f.cleaned_data['activo'],
                                            valorcalculo=f.cleaned_data['valorcalculo'],
                                            institucion_id=1,
                                            descripcion=f.cleaned_data['descripcion'])
                    periodo.save(request)
                    log(u'Adicionó nuevo periodo de plantilla: %s' % periodo, request, "add")
                    return JsonResponse({"result": False,"mensaje":"Se ha guardado correctamente"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'add':
            try:
                f = CabPlanificacionTHForm(request.POST)
                periodo = PeriodoPlanificacionTH.objects.get(pk=encrypt_id(request.POST['id']))
                if not puede_gestionar_plantilla:
                    f.fields['departamento'].required = False
                if f.is_valid():
                    if puede_gestionar_plantilla:
                        departamento = f.cleaned_data['departamento']
                    else:
                        departamento = persona.departamentodireccion()
                    if departamento:
                        if CabPlanificacionTH.objects.filter(periodo=periodo, departamento=departamento, status=True).exists():
                            raise NameError(u"El registro que intenta adicionar ya existe.")
                        if not departamento.responsable:
                            raise NameError('Departamento que intenta adicionar no cuenta con responsable configurado')
                        if not departamento.gestiones():
                            raise NameError('Departamento que intenta adicionar no cuenta con gestiones configuradas')
                        cabecera = CabPlanificacionTH(
                                                periodo=periodo,
                                                departamento=departamento,
                                                fecha=f.cleaned_data['fecha'],
                                                nivelterritorial=f.cleaned_data['nivelterritorial'],
                                                tipoproceso=f.cleaned_data['tipoproceso'],
                                                estado = 1,
                                                responsable=departamento.responsable,
                                                cargo=departamento.responsable.mi_cargo(),
                                            )
                        cabecera.save(request)
                        gestiones = SeccionDepartamento.objects.filter(status=True,departamento=departamento)
                        for gestion in gestiones:
                            gestionth = GestionPlanificacionTH(
                                cabecera=cabecera,
                                gestion=gestion,
                                estado=1,
                                responsable=gestion.responsable,
                                responsablesubrogante=gestion.responsablesubrogante)
                            gestionth.save()
                            productos = ProductoServicioSeccion.objects.filter(status=True,seccion=gestion,activo=True)
                            for p in productos:
                                producto = GestionProductoServicioTH(producto=p.producto,gestion=gestionth)
                                producto.save()

                            brecha = ReporteBrechasTH(
                                gestion = gestionth,
                            )
                            brecha.save()
                        log(u'Adicionó nueva cabecera de plantilla: %s' % cabecera.departamento, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({"result": True, "mensaje": u"Usted no es responsable de una dirección."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"Error: {ex}"})

        if action == 'importargestion':
            try:
                cabecera = CabPlanificacionTH.objects.get(pk=int(request.POST['idg']))
                excluir = GestionPlanificacionTH.objects.values_list('gestion_id').filter(cabecera=cabecera,status=True)
                gestiones = SeccionDepartamento.objects.filter(status=True, departamento=cabecera.departamento).exclude(
                    id__in=excluir)
                for gestion in gestiones:
                    gestionth = GestionPlanificacionTH(
                        cabecera=cabecera,
                        gestion=gestion,
                        estado=1,
                        responsable=gestion.responsable,
                        responsablesubrogante=gestion.responsablesubrogante
                    )
                    gestionth.save()

                    brecha = ReporteBrechasTH(
                        gestion=gestionth,
                    )
                    brecha.save()

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                pass

        if action == 'editperiodo':
            try:
                f = PeriodoPlanificacionTHForm(request.POST)
                if f.is_valid():
                    periodo = PeriodoPlanificacionTH.objects.get(pk=request.POST['id'])
                    periodo.anio=f.cleaned_data['anio']
                    periodo.activo=f.cleaned_data['activo']
                    periodo.valorcalculo=f.cleaned_data['valorcalculo']
                    periodo.descripcion=f.cleaned_data['descripcion']
                    periodo.save(request)
                    log(u'Modifico periodo: %s' % periodo, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                f = CabPlanificacionTHForm(request.POST)
                f.fields['departamento'].required = False
                if f.is_valid():
                    cabecera = CabPlanificacionTH.objects.get(pk=request.POST['id'])
                    cabecera.fecha=f.cleaned_data['fecha']
                    cabecera.nivelterritorial=f.cleaned_data['nivelterritorial']
                    cabecera.tipoproceso=f.cleaned_data['tipoproceso']
                    cabecera.save(request)
                    log(u'Modifico cabecera: %s' % cabecera.departamento, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        if action == 'addactividad':
            try:
                servicio = GestionProductoServicioTH.objects.get(pk=request.POST['servicio'])
                gestion = GestionPlanificacionTH.objects.get(pk=request.POST['gestion'])
                actividad = ActividadSecuencialTH(producto=servicio)
                actividad.save(request)
                return JsonResponse({"result": "ok", "id": actividad.id })
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al crear la fila."})

        if action == 'deleteactividad':
            try:
                actividad = ActividadSecuencialTH.objects.get(pk=request.POST['id'])
                actividad.delete()
                log(u'Elimino actividad', request, "del")
                return JsonResponse({"result": "ok", "actividad": actividad.actividad})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'delproductogestion':
            try:
                servicio = GestionProductoServicioTH.objects.get(pk=request.POST['id'])
                actividades = servicio.actividadsecuencialth_set.filter(status=True)
                actividades.update(status=False)
                servicio.status=False
                servicio.save(request, update_fields=['status'])
                log(u'Eliminó producto de plantilla', request, "del")
                res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)


        if action == 'delgestion':
            try:
                gestion = GestionPlanificacionTH.objects.get(pk=request.POST['id'])
                gestion.status=False
                gestion.save()
                productos = GestionProductoServicioTH.objects.filter(status=True,gestion=gestion)
                for pro in productos:
                    pro.status=False
                    pro.save()
                if ReporteBrechasTH.objects.filter(gestion=gestion,status=True).exists():
                    brechas = ReporteBrechasTH.objects.filter(gestion=gestion,status=True)
                    for brecha in brechas:
                        brecha.status=False
                        brecha.save()
                log(u'Elimino gestión %s' % gestion , request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'deldepa':
            try:
                cabecera = CabPlanificacionTH.objects.get(pk=request.POST['id'])
                cabecera.status=False
                cabecera.save()
                log(u'Elimino dirección %s' % cabecera , request, "del")
                res_js = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        if action == 'guardaactividad':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "vacio"})
                if request.POST['dato'] == '':
                    return JsonResponse({"result": "vacio"})
                actividad = ActividadSecuencialTH.objects.get(pk=request.POST['id'])
                tipo = int(request.POST['tipo'])
                dato = request.POST['dato']
                if tipo == 1:
                    actividad.actividad = dato
                    actividad.actividad=actividad.actividad.strip().replace('  ',' ')
                elif tipo == 2:
                    actividad.tipoactividad = dato
                elif tipo ==3:
                    actividad.productointermedio = dato
                    actividad.productointermedio=actividad.productointermedio.strip().replace('  ',' ')
                elif tipo == 4:
                    actividad.frecuencia = dato
                elif tipo == 5:
                    actividad.volumen = dato
                elif tipo == 6:
                    actividad.tiempomin = dato
                elif tipo == 7:
                    actividad.tiempomax = dato
                elif tipo == 8:
                    actividad.pdireccion = dato
                elif tipo == 9:
                    actividad.pejecucioncoord = dato
                elif tipo == 10:
                    actividad.pejecucionsupervision = dato
                elif tipo == 11:
                    actividad.pejecucion = dato
                elif tipo == 12:
                    actividad.pejecucionapoyo = dato
                elif tipo == 13:
                    actividad.ptecnico = dato
                actividad.save(request)
                #log(u'Editó actividad: %s' % actividad.actividad, request, "del")
                return JsonResponse({"result": "ok", "actividad": actividad.actividad})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. ({})".format(ex)})

        if action == 'guardabrecha':
            try:
                #cabecera = CabPlanificacionTH.objects.get(pk=request.POST['cab'])
                gestion = GestionPlanificacionTH.objects.get(pk=request.POST['id'])
                actividad = ReporteBrechasTH.objects.get(gestion=gestion,status=True)
                nombre = (request.POST['nombre'])
                dato = (request.POST['dato'])
                if nombre == 'direccion':
                    actividad.direccion = dato

                if nombre == 'pdireccion':
                    actividad.pdireccion = dato

                elif nombre == 'coordinacion':
                    actividad.ejecucioncoord = dato

                elif nombre == 'pcoordinacion':
                    actividad.pejecucioncoord = dato

                elif nombre == 'supervision':
                    actividad.ejecucionsupervision = dato

                elif nombre == 'psupervision':
                    actividad.pejecucionsupervision = dato

                elif nombre == 'ejecucion':
                    actividad.ejecucion = dato

                elif nombre == 'pejecucion':
                    actividad.pejecucion = dato

                elif nombre == 'apoyo':
                    actividad.ejecucionapoyo = dato

                elif nombre == 'papoyo':
                    actividad.pejecucionapoyo = dato

                elif nombre == 'tecnico':
                    actividad.tecnico = dato

                elif nombre == 'ptecnico':
                    actividad.ptecnico = dato

                elif nombre == 'admin':
                    actividad.administrativo = dato

                elif nombre == 'padmin':
                    actividad.padministrativo = dato

                elif nombre == 'serv':
                    actividad.servicios = dato

                elif nombre == 'pserv':
                    actividad.pservicios = dato

                elif nombre == 'contrato':
                    actividad.contrato = dato

                elif nombre == 'provisional':
                    actividad.provisional = dato

                elif nombre == 'permanente':
                    actividad.permanente = dato

                elif nombre == 'njs':
                    actividad.njs = dato

                elif nombre == 'trabajo':
                    actividad.trabajo = dato

                elif nombre == 'otros':
                    actividad.otros = dato

                elif nombre == 'vacantes':
                    actividad.vacantes = dato


                elif nombre == 'anominadora':
                    actividad.anominadora = dato

                elif nombre == 'viceministros':
                    actividad.viceministros = dato

                elif nombre == 'subsecretarios':
                    actividad.subsecretarios = dato

                elif nombre == 'coordinadores':
                    actividad.coordinadores = dato

                elif nombre == 'asesor':
                    actividad.asesor = dato

                elif nombre == 'coorddespacho':
                    actividad.coorddespacho = dato

                elif nombre == 'panominadora':
                    actividad.panominadora = dato

                elif nombre == 'pviceministros':
                    actividad.pviceministros = dato

                elif nombre == 'psubsecretarios':
                    actividad.psubsecretarios = dato

                elif nombre == 'pcoordinadores':
                    actividad.pcoordinadores = dato

                elif nombre == 'pasesor':
                    actividad.pasesor = dato

                elif nombre == 'pcoorddespacho':
                    actividad.pcoorddespacho = dato



                actividad.save(request)
                #log(u'Editó actividad: %s' % actividad.actividad, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'guardabrechaconsolidada':
            try:
                periodo = PeriodoPlanificacionTH.objects.get(pk=request.POST['id'])
                if not ReporteBrechasPeriodoTH.objects.filter(periodo=periodo,status=True).exists():
                    brecha = ReporteBrechasPeriodoTH(periodo=periodo)
                    brecha.save(request)
                else:
                    brecha = ReporteBrechasPeriodoTH.objects.get(periodo=periodo,status=True)

                nombre = (request.POST['nombre'])
                dato = (request.POST['dato'])
                if nombre == 'totalcodtrabajo':
                    brecha.totalcodtrabajo = dato

                if nombre == 'totalregespecial':
                    brecha.totalregespecial = dato

                elif nombre == 'ptotalcodtrabajo':
                    brecha.ptotalcodtrabajo = dato

                elif nombre == 'ptotalregespecial':
                    brecha.ptotalregespecial = dato

                elif nombre == 'jerarquico':
                    brecha.jerarquico = dato

                elif nombre == 'pjerarquico':
                    brecha.pjerarquico = dato

                elif nombre == 'ejecucioncoord':
                    brecha.ejecucioncoord = dato

                elif nombre == 'pejecucioncoord':
                    brecha.pejecucioncoord = dato

                elif nombre == 'ejecucionsupervision':
                    brecha.ejecucionsupervision = dato

                elif nombre == 'pejecucionsupervision':
                    brecha.pejecucionsupervision = dato

                elif nombre == 'ejecucion':
                    brecha.ejecucion = dato

                elif nombre == 'pejecucion':
                    brecha.pejecucion = dato

                elif nombre == 'ejecucionapoyo':
                    brecha.ejecucionapoyo = dato

                elif nombre == 'pejecucionapoyo':
                    brecha.pejecucionapoyo = dato

                elif nombre == 'apoyo':
                    brecha.apoyo = dato

                elif nombre == 'papoyo':
                    brecha.papoyo = dato

                elif nombre == 'gobernante':
                    brecha.gobernante = dato

                elif nombre == 'pgobernante':
                    brecha.pgobernante = dato

                elif nombre == 'sustantivo':
                    brecha.sustantivo = dato

                elif nombre == 'psustantivo':
                    brecha.psustantivo = dato

                elif nombre == 'adjetivo':
                    brecha.adjetivo = dato

                elif nombre == 'padjetivo':
                    brecha.padjetivo = dato



                brecha.save(request)
                #log(u'Editó actividad: %s' % actividad.actividad, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'enviardir':
            try:
                gestion = GestionPlanificacionTH.objects.get(pk=request.POST['idg'])
                gestion.estado = 2
                gestion.save()
                log(u'Enviado a revisión: %s' % gestion.gestion, request, "edit")
                return JsonResponse({"result": "ok"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'enviaruath':
            try:
                cab = CabPlanificacionTH.objects.get(pk=request.POST['id'])
                cab.estado = 3
                cab.save()
                log(u'Enviado a revisión: %s' % cab, request, "edit")
                return JsonResponse({"result": "ok"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'aprobardir':
            try:
                gestion = GestionPlanificacionTH.objects.get(pk=request.POST['idg'])
                observacion = (request.POST['obser']).upper()
                estado = request.POST['estado']
                gestion.estado = estado
                historial=HistorialGestionPlanificacionTH(gestion=gestion,estado=estado,motivo=observacion)
                historial.save()
                gestion.save()
                log(u'Cambió de estado' , request, "edit")
                return JsonResponse({"result": "ok"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'aprobaruath':
            try:
                f = CambiarAprobarUathForm(request.POST)
                if f.is_valid():
                    cabecera = CabPlanificacionTH.objects.get(pk=request.POST['id'])
                    cabecera.estado=f.cleaned_data['estado']
                    cabecera.save(request, update_fields=['estado'])
                    historial = HistorialCabPlanificacionTH(cabecera=cabecera,
                                                            estado=cabecera.estado,
                                                            motivo=f.cleaned_data['observacion'])
                    historial.save()
                    log(u'Cambió estado a: %s en planificación %s' %(cabecera.estado,cabecera) , request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        if action == 'actualizaresponsables':
            try:
                periodo = PeriodoPlanificacionTH.objects.get(pk=request.POST['idp'])
                direcciones = CabPlanificacionTH.objects.filter(status=True,periodo=periodo)
                for dir in direcciones:
                    dir.responsable = dir.departamento.responsable
                    gestiones = GestionPlanificacionTH.objects.filter(status=True, cabecera=dir)
                    for gest in gestiones:
                        gest.responsable = gest.gestion.responsable
                        gest.responsablesubrogante = gest.gestion.responsablesubrogante
                        gest.save(request)
                    dir.save(request)
                    log(u'Actualizó responsables' , request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cambiarEstadoDepartamento':
            try:
                f = CambiarEstadoDepartamentoForm(request.POST)
                if f.is_valid():
                    filtro = CabPlanificacionTH.objects.get(pk=int(request.POST['id']))
                    filtro.estado = f.cleaned_data['estado']
                    filtro.save(request)
                    log(u'Cambio el estado del departamento: %s' % filtro, request, "change")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Datos erróneos, intente nuevamente."}, safe=False)

        if action == 'cambiarResponsableGestion':
            try:
                f = ResponsableGestionForm(request.POST)
                if f.is_valid():
                    filtro = GestionPlanificacionTH.objects.get(pk=int(request.POST['id']))
                    if 'responsable' in f.fields:
                        filtro.responsable_id = f.cleaned_data['responsable']
                    if 'subrogante' in f.fields:
                        filtro.responsablesubrogante_id = f.cleaned_data['subrogante']
                    filtro.save(request)
                    log(u'Cambio responsable de gestión: %s' % filtro, request, "change")
                    return JsonResponse({"result": False}, safe=False)
                # else:
                #     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Datos erróneos, intente nuevamente."}, safe=False)

        if action == 'deleteperiodo':
            try:
                periodo = PeriodoPlanificacionTH.objects.get(pk=request.GET['id'])
                periodo.status = False
                periodo.save()
                cab = CabPlanificacionTH.objects.filter(status=True, periodo=periodo).order_by('id')
                if cab:
                    for i in cab:
                        i.status = False
                        i.save()
                        ges = GestionPlanificacionTH.objects.filter(cabecera=i, status=True)
                        if ges:
                            for gestion in ges:
                                gestion.status = False
                                gestion.save()
                                prod = ProductoServicioSeccion.objects.filter(status=True,seccion=gestion)
                                if prod:
                                    for p in prod:
                                        p.status = False
                                        p.save()
                                        acti = ActividadSecuencialTH.objects.filter(status=True, gestion=gestion,servicio=p)
                                        if acti:
                                            for ac in acti:
                                                ac.status=False
                                                ac.save()
                                if ReporteBrechasTH.objects.filter(gestion=gestion, status=True).exists():
                                    brecha = ReporteBrechasTH.objects.get(gestion=gestion, status=True)
                                    brecha.status = False
                                    brecha.save()
                res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'cambiarEstadoGestionPlanificacionTH':
            try:
                f = CambiarEstadoGestionPlanificacionTHForm(request.POST)
                if f.is_valid():
                    filtro = GestionPlanificacionTH.objects.get(pk=int(request.POST['id']))
                    filtro.estado = f.cleaned_data['estado']
                    filtro.save(request)
                    log(u'Cambio el estado de la gestion de planificacion: %s' % filtro, request, "change")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Datos erróneos, intente nuevamente."}, safe=False)

        if action == 'cambiarproducto':
            try:
                f = CambiarProductoForm(request.POST)
                if f.is_valid():
                    filtro = GestionProductoServicioTH.objects.get(pk=int(request.POST['id']))
                    gestion = GestionProductoServicioTH.objects.filter(status=True, productoseccion=f.cleaned_data['producto'],
                                                                       producto=f.cleaned_data['producto'].producto,
                                                                       gestion__cabecera_id=int(request.POST['idp']))
                    if not gestion:
                        filtro.producto = f.cleaned_data['producto'].producto
                        filtro.productoseccion = f.cleaned_data['producto']
                        filtro.save(request)
                    else:
                        actividades = filtro.actividades()
                        actividades.update(producto=gestion[0])
                    log(u'Cambió el producto de la gestion de planificacion: %s' % filtro, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Datos erróneos, intente nuevamente."}, safe=False)

        if action == 'movergestion':
            try:
                f = MoverGestionForm(request.POST)
                if f.is_valid():
                    seccionact = f.cleaned_data['seccion']
                    filtro = GestionPlanificacionTH.objects.get(pk=int(request.POST['id']))
                    if  CabPlanificacionTH.objects.filter(periodo=filtro.cabecera.periodo,departamento=seccionact.departamento,status=True).exists():
                        cabeceraact = CabPlanificacionTH.objects.filter(periodo=filtro.cabecera.periodo,departamento=seccionact.departamento,status=True)[0]
                    else:
                        cabeceraact = CabPlanificacionTH(periodo=filtro.cabecera.periodo,
                                                          departamento=seccionact.departamento,
                                                         nivelterritorial=filtro.cabecera.nivelterritorial,
                                                         tipoproceso=filtro.cabecera.tipoproceso,
                                                         estado=1,
                                                         responsable=seccionact.departamento.responsable,
                                                         )
                        cabeceraact.save()

                    if GestionPlanificacionTH.objects.filter(cabecera=cabeceraact,status=True,gestion=seccionact).exists():
                        gestion = GestionPlanificacionTH.objects.filter(cabecera=cabeceraact, status=True,
                                                                        gestion=seccionact)[0]
                    else:
                        gestion = GestionPlanificacionTH(cabecera=cabeceraact, status=True,
                                                              gestion=seccionact,estado=1,responsable=filtro.responsable,responsablesubrogante=filtro.responsablesubrogante)
                        gestion.save()


                    for prod in filtro.gestionproductoservicioth_set.actividades():
                        if ProductoServicioSeccion.objects.filter(status=True,seccion=gestion.gestion,producto = prod.servicios).exists():
                            prodsecc = ProductoServicioSeccion.objects.filter(status=True,seccion=gestion.gestion,producto = prod.servicios)[0]
                        else:
                            prodsecc = ProductoServicioSeccion(status=True, seccion=gestion.gestion,
                                                                   producto = prod.servicios)
                            prodsecc.save()

                        if GestionProductoServicioTH.objects.filter(status=True,gestion=gestion,producto=prodsecc.producto).exists():
                            gestprod = GestionProductoServicioTH.objects.filter(status=True,gestion=gestion,producto=prodsecc.producto)[0]
                        else:
                            gestprod = GestionProductoServicioTH(status=True, gestion=gestion,
                                                                                producto=prodsecc.producto)
                            gestprod.save()

                        acts = ActividadSecuencialTH(gestion=gestion, servicios=prodsecc.producto,actividad=prod.actividad,
                                              tipoactividad=prod.tipoactividad, productointermedio=prod.productointermedio,
                                              frecuencia=prod.frecuencia, volumen=prod.volumen, tiempomin = prod.tiempomin,
                                              tiempomax = prod.tiempomax,pdireccion = prod.pdireccion,pejecucioncoord=prod.pejecucioncoord,
                                              pejecucionsupervision = prod.pejecucionsupervision,pejecucion = prod.pejecucion,
                                              pejecucionapoyo = prod.pejecucionapoyo, ptecnico=prod.ptecnico,producto = gestprod
                                              )
                        acts.save()
                        prod.delete()

                    log(u'movió productos de la gestion de planificacion: %s' % filtro, request, "change")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Datos erróneos, intente nuevamente."}, safe=False)

        if action == 'delperiodo':
            try:
                periodo = PeriodoPlanificacionTH.objects.get(pk=encrypt_id(request.POST['id']))
                periodo.status=False
                periodo.save()
                log(u'Elimino dirección %s' % periodo , request, "del")
                res_js = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        if action == 'duplicar':
            try:
                periodo = PeriodoPlanificacionTH.objects.get(pk=encrypt_id(request.POST['id']))
                periodo.descripcion = periodo.descripcion + '_Duplicado'
                du_periodo = PeriodoPlanificacionTH(anio=periodo.anio,
                                                    activo=periodo.activo,
                                                    valorcalculo=periodo.valorcalculo,
                                                    institucion_id=1,
                                                    descripcion=periodo.descripcion)
                du_periodo.save()

                tipo = int(request.POST['unidad'])
                if tipo == 1:
                    cab = CabPlanificacionTH.objects.filter(status=True, periodo=periodo).order_by('id')
                    for i in cab:

                        cabecera = CabPlanificacionTH(
                            periodo=du_periodo,
                            departamento_id=i.departamento_id,
                            fecha=i.fecha,
                            nivelterritorial=i.nivelterritorial,
                            tipoproceso=i.tipoproceso,
                            estado=1,
                            responsable=i.departamento.responsable,
                            cargo=i.cargo,
                        )
                        cabecera.save()

                        gestiones = GestionPlanificacionTH.objects.filter(cabecera=i, status=True)
                        for gestion in gestiones:
                            gestionth = GestionPlanificacionTH(
                                cabecera=cabecera,
                                gestion=gestion.gestion,
                                estado=1,
                                responsable=gestion.gestion.responsable,
                                responsablesubrogante=gestion.gestion.responsablesubrogante)
                            gestionth.save()

                            productos = GestionProductoServicioTH.objects.filter(status=True, gestion=gestion)
                            id_excluir = GestionProductoServicioTH.objects.values_list('producto_id').filter(status=True, gestion=gestion)
                            id_productosactuales = ProductoServicioSeccion.objects.values_list('producto_id', flat=True).filter(activo=True, status=True, seccion=gestionth.gestion)
                            productos_actuales = ProductoServicioSeccion.objects.filter(status=True, seccion=gestion.gestion, activo=True).exclude(producto_id__in=id_excluir)

                            # Diccionario para mapear los productos originales a sus duplicados
                            producto_map = {}

                            for produ in productos:
                                productogestion = GestionProductoServicioTH(gestion=gestionth, producto=produ.producto)
                                productogestion.save()
                                producto_map[produ.id] = productogestion
                                if productogestion.producto_id in id_productosactuales:
                                    productogestion.activoseccion = True
                                    productogestion.save()
                            for produ in productos_actuales:
                                productogestion = GestionProductoServicioTH(gestion=gestionth, producto=produ.producto, activoseccion=True)
                                productogestion.save()
                                producto_map[produ.id] = productogestion

                            actividades = ActividadSecuencialTH.objects.filter(status=True, producto__gestion=gestion)
                            for ac in actividades:
                                # Asociar la actividad al producto duplicado correspondiente
                                producto_duplicado = producto_map.get(ac.producto.id)
                                acti = ActividadSecuencialTH(
                                    actividad=ac.actividad,
                                    producto=producto_duplicado,
                                    tipoactividad=ac.tipoactividad,
                                    productointermedio=ac.productointermedio,
                                    frecuencia=ac.frecuencia,
                                    volumen=ac.volumen,
                                    tiempomin=ac.tiempomin,
                                    tiempomax=ac.tiempomax,
                                    pdireccion=ac.pdireccion,
                                    pejecucioncoord=ac.pejecucioncoord,
                                    pejecucionsupervision=ac.pejecucionsupervision,
                                    pejecucion=ac.pejecucion,
                                    pejecucionapoyo=ac.pejecucionapoyo,
                                    ptecnico=ac.ptecnico
                                )
                                acti.save()

                            if ReporteBrechasTH.objects.filter(gestion=gestion, status=True).exists():
                                brecha = ReporteBrechasTH.objects.get(gestion=gestion, status=True)
                                actividad = ReporteBrechasTH(
                                    gestion=gestionth,
                                    direccion=brecha.direccion,
                                    pdireccion=brecha.pdireccion,
                                    ejecucioncoord=brecha.ejecucioncoord,
                                    pejecucioncoord=brecha.pejecucioncoord,
                                    ejecucionsupervision=brecha.ejecucionsupervision,
                                    pejecucionsupervision=brecha.pejecucionsupervision,
                                    ejecucion=brecha.ejecucion,
                                    pejecucion=brecha.pejecucion,
                                    ejecucionapoyo=brecha.ejecucionapoyo,
                                    pejecucionapoyo=brecha.pejecucionapoyo,
                                    tecnico=brecha.tecnico,
                                    ptecnico=brecha.ptecnico,
                                    administrativo=brecha.administrativo,
                                    padministrativo=brecha.padministrativo,
                                    servicios=brecha.servicios,
                                    pservicios=brecha.pservicios,
                                    contrato=brecha.contrato,
                                    provisional=brecha.provisional,
                                    permanente=brecha.permanente,
                                    njs=brecha.njs,
                                    trabajo=brecha.trabajo,
                                    otros=brecha.otros,
                                    vacantes=brecha.vacantes,
                                    anominadora=brecha.anominadora,
                                    viceministros=brecha.viceministros,
                                    subsecretarios=brecha.subsecretarios,
                                    coordinadores=brecha.coordinadores,
                                    asesor=brecha.asesor,
                                    coorddespacho=brecha.coorddespacho,
                                    panominadora=brecha.panominadora,
                                    pviceministros=brecha.pviceministros,
                                    psubsecretarios=brecha.psubsecretarios,
                                    pcoordinadores=brecha.pcoordinadores,
                                    pasesor=brecha.pasesor,
                                    pcoorddespacho=brecha.pcoorddespacho
                                )
                                actividad.save()
                return JsonResponse({"error": False})
            except Exception as ex:
                print(ex)
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                transaction.set_rollback(True)
                return JsonResponse({"error": True, 'mensaje':f'Error: {ex}'})

        elif action == 'copiarunidad':
            try:
                periodo_recepta = PeriodoPlanificacionTH.objects.get(pk=encrypt_id(request.POST['id']))
                form = CopiarUnidadForm(request.POST)
                if not form.is_valid():
                    return JsonResponse({'result': 'bad', "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})

                cab = form.cleaned_data['unidad']
                cabecera = CabPlanificacionTH(
                    periodo=periodo_recepta,
                    departamento_id=cab.departamento_id,
                    fecha=cab.fecha,
                    nivelterritorial=cab.nivelterritorial,
                    tipoproceso=cab.tipoproceso,
                    estado=1,
                    responsable=cab.departamento.responsable,
                    cargo=cab.cargo,
                )
                cabecera.save()

                gestiones = GestionPlanificacionTH.objects.filter(cabecera=cab, status=True)
                for gestion in gestiones:
                    gestionth = GestionPlanificacionTH(
                        cabecera=cabecera,
                        gestion=gestion.gestion,
                        estado=1,
                        responsable=gestion.gestion.responsable,
                        responsablesubrogante=gestion.gestion.responsablesubrogante)
                    gestionth.save()

                    productos = GestionProductoServicioTH.objects.filter(status=True, gestion=gestion)
                    id_excluir = GestionProductoServicioTH.objects.values_list('producto_id').filter(status=True, gestion=gestion)
                    id_productosactuales = ProductoServicioSeccion.objects.values_list('producto_id', flat=True).filter(activo=True, status=True, seccion=gestionth.gestion)
                    productos_actuales = ProductoServicioSeccion.objects.filter(status=True, seccion=gestion.gestion, activo=True).exclude(producto_id__in=id_excluir)

                    # Diccionario para mapear los productos originales a sus duplicados
                    producto_map = {}

                    for produ in productos:
                        productogestion = GestionProductoServicioTH(gestion=gestionth, producto=produ.producto)
                        productogestion.save()
                        producto_map[produ.id] = productogestion
                        if productogestion.producto_id in id_productosactuales:
                            productogestion.activoseccion = True
                            productogestion.save()
                    for produ in productos_actuales:
                        productogestion = GestionProductoServicioTH(gestion=gestionth, producto=produ.producto, activoseccion=True)
                        productogestion.save()
                        producto_map[produ.id] = productogestion

                    actividades = ActividadSecuencialTH.objects.filter(status=True, producto__gestion=gestion)
                    for ac in actividades:
                        # Asociar la actividad al producto duplicado correspondiente
                        producto_duplicado = producto_map.get(ac.producto.id)
                        acti = ActividadSecuencialTH(
                            actividad=ac.actividad,
                            producto=producto_duplicado,
                            tipoactividad=ac.tipoactividad,
                            productointermedio=ac.productointermedio,
                            frecuencia=ac.frecuencia,
                            volumen=ac.volumen,
                            tiempomin=ac.tiempomin,
                            tiempomax=ac.tiempomax,
                            pdireccion=ac.pdireccion,
                            pejecucioncoord=ac.pejecucioncoord,
                            pejecucionsupervision=ac.pejecucionsupervision,
                            pejecucion=ac.pejecucion,
                            pejecucionapoyo=ac.pejecucionapoyo,
                            ptecnico=ac.ptecnico
                        )
                        acti.save()

                    if ReporteBrechasTH.objects.filter(gestion=gestion, status=True).exists():
                        brecha = ReporteBrechasTH.objects.get(gestion=gestion, status=True)
                        actividad = ReporteBrechasTH(
                            gestion=gestionth,
                            direccion=brecha.direccion,
                            pdireccion=brecha.pdireccion,
                            ejecucioncoord=brecha.ejecucioncoord,
                            pejecucioncoord=brecha.pejecucioncoord,
                            ejecucionsupervision=brecha.ejecucionsupervision,
                            pejecucionsupervision=brecha.pejecucionsupervision,
                            ejecucion=brecha.ejecucion,
                            pejecucion=brecha.pejecucion,
                            ejecucionapoyo=brecha.ejecucionapoyo,
                            pejecucionapoyo=brecha.pejecucionapoyo,
                            tecnico=brecha.tecnico,
                            ptecnico=brecha.ptecnico,
                            administrativo=brecha.administrativo,
                            padministrativo=brecha.padministrativo,
                            servicios=brecha.servicios,
                            pservicios=brecha.pservicios,
                            contrato=brecha.contrato,
                            provisional=brecha.provisional,
                            permanente=brecha.permanente,
                            njs=brecha.njs,
                            trabajo=brecha.trabajo,
                            otros=brecha.otros,
                            vacantes=brecha.vacantes,
                            anominadora=brecha.anominadora,
                            viceministros=brecha.viceministros,
                            subsecretarios=brecha.subsecretarios,
                            coordinadores=brecha.coordinadores,
                            asesor=brecha.asesor,
                            coorddespacho=brecha.coorddespacho,
                            panominadora=brecha.panominadora,
                            pviceministros=brecha.pviceministros,
                            psubsecretarios=brecha.psubsecretarios,
                            pcoordinadores=brecha.pcoordinadores,
                            pasesor=brecha.pasesor,
                            pcoorddespacho=brecha.pcoorddespacho
                        )
                        actividad.save()
                return JsonResponse({"result": False})
            except Exception as ex:
                print(ex)
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                transaction.set_rollback(True)
                return JsonResponse({"result": True, 'mensaje':f'Error: {ex}'})

        elif action == 'movergestiones':
            try:
                ids_gestiones = list(request.POST.getlist('gestiones'))
                unidad_recibe = CabPlanificacionTH.objects.get(pk=encrypt_id(request.POST['unidad_recepta']))
                GestionPlanificacionTH.objects.filter(id__in=ids_gestiones).update(cabecera=unidad_recibe)
                log(u'Se mueven gestiones a nueva unidad organizacional: %s' % unidad_recibe, request, "edit")
                return JsonResponse({"result": False})
            except Exception as ex:
                print(ex)
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                transaction.set_rollback(True)
                return JsonResponse({"result": True, 'mensaje':f'Error: {ex}'})

        elif action == 'addproducto':
            try:
                productoservicio =ProductoServicioSeccion.objects.get(id=encrypt_id(request.POST['producto']))
                gestionp = GestionPlanificacionTH.objects.get(id=encrypt_id(request.POST['id']))
                gestionproducto = GestionProductoServicioTH(producto=productoservicio.producto,
                                                            productoseccion=productoservicio,
                                                            gestion=gestionp,
                                                            activoseccion=productoservicio.activo)
                gestionproducto.save(request)
                log(u'Se crear producto nuevo: %s' % gestionproducto, request, "add")
                return JsonResponse({"result": False})
            except Exception as ex:
                print(ex)
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                transaction.set_rollback(True)
                return JsonResponse({"result": True, 'mensaje':f'Error: {ex}'})

        elif action == 'importaractividades':
            try:
                if not 'actividades' in request.POST:
                    raise NameError('Seleccione al menos una actividad.')
                ids_actividades = list(request.POST.getlist('actividades'))
                gestionproducto = GestionProductoServicioTH.objects.get(id=encrypt_id(request.POST['id']))
                actividades = ActividadSecuencialTH.objects.filter(id__in=ids_actividades)
                for a in actividades:
                    actividad = ActividadSecuencialTH(producto=gestionproducto,
                                                    actividad=a.actividad,
                                                    tipoactividad=a.tipoactividad,
                                                    productointermedio=a.productointermedio,
                                                    frecuencia=a.frecuencia,
                                                    volumen=a.volumen,
                                                    tiempomin=a.tiempomin,
                                                    tiempomax=a.tiempomax,
                                                    pdireccion=a.pdireccion,
                                                    pejecucioncoord=a.pejecucioncoord,
                                                    pejecucionsupervision=a.pejecucionsupervision,
                                                    pejecucion=a.pejecucion,
                                                    pejecucionapoyo=a.pejecucionapoyo,
                                                    ptecnico=a.ptecnico)
                    actividad.save(request)
                log(u'Se importa actividades: %s' % gestionproducto, request, "add")
                return JsonResponse({"result": False})
            except Exception as ex:
                print(ex)
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                transaction.set_rollback(True)
                return JsonResponse({"result": True, 'mensaje':f'Error: {ex}'})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addperiodo':
                try:
                    data['form'] = PeriodoPlanificacionTHForm()
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'add':
                try:
                    data['title'] = u'Planificación'
                    data['id'] = id = encrypt_id(request.GET['id'])
                    plan = PeriodoPlanificacionTH.objects.get(pk=id)
                    ids_excluidos = list(CabPlanificacionTH.objects.filter(periodo=plan, status=True).values_list('departamento_id', flat=True))
                    form = CabPlanificacionTHForm()
                    if puede_gestionar_plantilla:
                        form.fields['departamento'].queryset = Departamento.objects.filter(status=True, integrantes__isnull=False).exclude(id__in=ids_excluidos).order_by('id').distinct()
                        data['header_info'] = f'Si el departamento no se encuentra en la lista, o no se puede crear, ' \
                                              f'puede gestionarlo para su configuración del nuevo departamento con sus gestiones y productos ' \
                                              f'en el módulo <a href="/adm_departamentos" target="_blank"><i class="bi bi-diagram-3 fs-4"></i> Direcciones.</a>'
                    else:
                        form.fields['departamento'].queryset = Departamento.objects.none()
                        form.fields['departamento'].required = False
                        form.fields['departamento'].widget = forms.HiddenInput()
                    data['form'] = form
                    data['unidad'] = request.GET['idex']
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addgestion':
                try:
                    data['unidad'] = request.GET['unidad']
                    cabecera = CabPlanificacionTH.objects.get(pk = int(request.GET['idg']))
                    excluir = GestionPlanificacionTH.objects.values_list('gestion_id').filter(cabecera=cabecera,status=True)
                    gestiones = SeccionDepartamento.objects.filter(status=True,departamento=cabecera.departamento,activo=True).exclude(id__in=excluir)
                    data = {"result": "ok", "gestiones": [x.descripcion for x in gestiones]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Modificar Dirección'
                    data['unidad'] = request.GET['idex']
                    data['id'] = request.GET['id']
                    data['cabecera'] = cabecera = CabPlanificacionTH.objects.get(pk=encrypt(request.GET['id']))
                    form = CabPlanificacionTHForm(initial={'fecha': cabecera.fecha.date(),
                                                  'nivelterritorial' : cabecera.nivelterritorial,
                                                  'tipoproceso' : cabecera.tipoproceso})
                    form.fields['departamento'].queryset = Departamento.objects.none()
                    form.fields['departamento'].required = False
                    form.fields['departamento'].widget = forms.HiddenInput()
                    data['form'] = form
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editperiodo':
                try:
                    data['periodo'] = periodo = PeriodoPlanificacionTH.objects.get(pk=request.GET['id'])
                    data['id'] = encrypt(request.GET['id'])
                    initial = model_to_dict(periodo)
                    data['form'] = PeriodoPlanificacionTHForm(initial=initial)
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'delgestion':
                try:
                    data['unidad'] = request.GET['unidad']
                    data['title'] = u'Eliminar Gestión'
                    data['gestion'] = GestionPlanificacionTH.objects.get(pk=request.GET['id'])
                    data['unidad'] = request.GET['unidad']
                    return render(request, 'th_dir_planificacion/delgestion.html', data)
                except Exception as ex:
                    pass

            if action == 'gestionar':
                try:
                    data['title'] = u'Plantillas'
                    data['unidad'] =  request.GET['unidad']
                    data['gestiond'] = gestion = GestionPlanificacionTH.objects.get(pk=request.GET['id'])
                    data['gestiones'] = GestionProductoServicioTH.objects.filter(status=True,gestion=gestion).order_by('-id')
                    data['tipoactividad_list'] = TIPO_ACTIVIDAD_TH
                    data['frecuencia_list'] = FRECUENCIA_TH
                    if gestion.estado == 1 or gestion.estado == 6 or gestion.estado == 7:
                        return render(request, "th_dir_planificacion/viewgestionar.html", data)
                    else:
                        return render(request, "th_dir_planificacion/viewgestionarbloq.html", data)

                except Exception as ex:
                    pass

            if action == 'verproceso':
                try:
                    data['title'] = u'Ver Historial'
                    data['filtro'] = filtro = GestionPlanificacionTH.objects.get(pk=int(request.GET['id']))
                    data['detalle'] = HistorialGestionPlanificacionTH.objects.filter(status=True, gestion=filtro).order_by('pk')
                    template = get_template("th_dir_planificacion/verhistorial.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'midepa':
                try:
                    data['periodo'] = periodo = PeriodoPlanificacionTH.objects.get(pk=int(request.GET['idp']))
                    data['title'] = u'Unidades Organizacionales'
                    search = None
                    tipo = int(request.GET['unidad'])
                    if tipo==0:
                        secciones = GestionPlanificacionTH.objects.filter((Q(responsable=persona)|Q(responsablesubrogante=persona)|Q(cabecera__responsable=persona)),status=True).values_list('cabecera_id', flat=True)
                        cab = CabPlanificacionTH.objects.filter(status=True,periodo=periodo,id__in=secciones).distinct().order_by('id')
                    elif tipo==1:
                        if 's' in request.GET:
                            search = request.GET['s']
                        if search:
                            cab = CabPlanificacionTH.objects.filter(Q(departamento__nombre__icontains=search),
                                status=True, periodo=periodo)
                        else:
                            cab = CabPlanificacionTH.objects.filter(status=True, periodo=periodo).order_by('id')

                    paging = MiPaginador(cab.order_by('departamento__nombre'), 100)
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
                    data['unidad'] = tipo
                    data['cabeceras'] = page.object_list
                    return render(request, "th_dir_planificacion/viewdepa.html", data)
                except Exception as ex:
                    pass

            if action == 'migestion':
                try:
                    data['cabecera'] =  cabecera = CabPlanificacionTH.objects.get(pk=int(request.GET['idp']))
                    data['unidad'] =  request.GET['unidad']
                    data['title'] = u'Gestiones'
                    search = None
                    tipo = None
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        gestiones = GestionPlanificacionTH.objects.filter(Q(responsable=persona)|Q(responsablesubrogante=persona)|Q(cabecera__departamento__responsable=persona),cabecera=cabecera,status=True).order_by('id')
                    else:
                        if puede_gestionar_plantilla:
                            gestiones = GestionPlanificacionTH.objects.filter(cabecera=cabecera,status=True).order_by('id')
                        else:
                            gestiones = GestionPlanificacionTH.objects.filter(Q(responsable=persona)|Q(responsablesubrogante=persona)|Q(cabecera__departamento__responsable=persona),cabecera=cabecera,status=True).order_by('id')
                    paging = MiPaginador(gestiones, 25)
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
                    data['gestiones'] = page.object_list
                    #data['persona'] = persona
                    return render(request, "th_dir_planificacion/viewgestion.html", data)
                except Exception as ex:
                    pass

            if action == 'brecha':
                try:
                    brecha = []
                    data['unidad'] = request.GET['unidad']
                    data['gestion'] =  gestion = GestionPlanificacionTH.objects.get(pk=int(request.GET['id']))
                    data['actividades'] = actividades = ActividadSecuencialTH.objects.filter(producto__gestion=gestion,status=True)
                    if ReporteBrechasTH.objects.filter(gestion=gestion,status=True).exists():
                        brecha = ReporteBrechasTH.objects.get(gestion=gestion,status=True)
                    else:
                        brecha = ReporteBrechasTH(gestion=gestion)
                        brecha.save()
                    data['brecha'] = brecha
                    direccion = 0
                    coordinacion = 0
                    supervision = 0
                    ejecucion = 0
                    apoyo = 0
                    tecnico = 0
                    for a in actividades:
                        direccion += a.resuldireccion()
                        coordinacion += a.resulejecucioncoord()
                        supervision += a.resulejecucionsupervision()
                        ejecucion += a.resulejecucion()
                        apoyo += a.resulejecucionapoyo()
                        tecnico += a.resultecnico()
                    valorcalculo = gestion.cabecera.periodo.valorcalculo if gestion.cabecera.periodo.valorcalculo else 9225.84096
                    direccion =direccion/valorcalculo
                    coordinacion =coordinacion/valorcalculo
                    supervision =supervision/valorcalculo
                    ejecucion = ejecucion / valorcalculo
                    apoyo = apoyo/valorcalculo
                    tecnico =tecnico/valorcalculo

                    direccion =  1 if direccion > 0 else 0
                    coordinacion =  int(coordinacion)
                    supervision =  int(supervision)
                    ejecucion =  int(ejecucion)
                    apoyo =  int(apoyo)
                    tecnico =  int(tecnico)

                    brecha.pdireccion = direccion
                    brecha.pejecucioncoord = coordinacion
                    brecha.pejecucionsupervision = supervision
                    brecha.pejecucion = ejecucion
                    brecha.pejecucionapoyo = apoyo
                    brecha.ptecnico = tecnico
                    brecha.save()

                    data['title'] = gestion.gestion
                    if gestion.estado == 1 or gestion.estado == 6 or gestion.estado == 7:
                        return render(request, "th_dir_planificacion/viewbrechas.html", data)
                    else:
                        return render(request, "th_dir_planificacion/viewbrechasprot.html", data)
                except Exception as ex:
                    pass

            if action == 'brechagob':
                try:
                    brecha = []
                    data['gestion'] =  gestion = GestionPlanificacionTH.objects.get(pk=int(request.GET['id']))
                    if ReporteBrechasTH.objects.filter(gestion=gestion,status=True).exists():
                        brecha = ReporteBrechasTH.objects.get(gestion=gestion,status=True)
                    else:
                        brecha = ReporteBrechasTH(gestion=gestion)
                        brecha.save()
                    data['brecha'] = brecha
                    data['unidad'] = request.GET['unidad']
                    data['title'] = gestion.gestion
                    return render(request, "th_dir_planificacion/viewbrechasgob.html", data)
                except Exception as ex:
                    pass

            if action == 'brechadepa':
                try:
                    brecha = []
                    data['cabecera'] = cabecera = CabPlanificacionTH.objects.get(pk=int(request.GET['idp']))
                    data['unidad'] = request.GET['unidad']
                    data['brechas'] =  brechas = ReporteBrechasTH.objects.filter(status=True,gestion__cabecera=cabecera,gestion__status=True).distinct()
                    data['title'] = u'REPORTE DE BRECHAS DE %s' % cabecera.departamento.nombre
                    return render(request, "th_dir_planificacion/viewbrechasdepa.html", data)
                except Exception as ex:
                    pass

            if action == 'brechatotal':
                try:
                    brecha = []
                    data['periodo'] = periodo = PeriodoPlanificacionTH.objects.get(pk=int(request.GET['idp']))
                    if not ReporteBrechasPeriodoTH.objects.filter(periodo=periodo, status=True).exists():
                        brecha = ReporteBrechasPeriodoTH(periodo=periodo)
                        brecha.save(request)
                    else:
                        brecha = ReporteBrechasPeriodoTH.objects.get(periodo=periodo, status=True)

                    data['direcciones'] = periodo.direccionesaprobadas()
                    data['brecha'] = brecha
                    data['total'] = total = periodo.totaldireccionesaprobadas()
                    data['totalactual'] = totalactual = total['anominadora']+total['viceministros']+total['subsecretarios']+total['coordinadores']+total['asesor']+total['coorddesp']+\
                                             total['direccion']+total['ejeccord']+total['ejesuper']+total['ejecucion']+total['tecnologico']+total['apoyo']
                    data['totalpropuesto'] = totalpropuesto = total['anominadora']+total['pviceministros']+total['psubsecretarios']+total['pcoordinadores']+total['pasesor']+total['pcoorddesp']+\
                                             total['pdireccion']+total['pejeccord']+total['pejesuper']+total['pejecucion']+total['ptecnologico']+total['papoyo']
                    data['totalservactual'] = totalactual + brecha.totalcodtrabajo+brecha.totalregespecial
                    data['totalservpropuesto'] = totalpropuesto + brecha.ptotalcodtrabajo+brecha.ptotalregespecial
                    data['totalgobernante'] = totalgobernante = periodo.totalbrecharol(1)
                    data['totalsustantivo'] = totalsustantivo = periodo.totalbrecharol(2)
                    data['totaladjetivo'] = totaladjetivo = periodo.totalbrecharol(3)
                    data['totalprocesoactual'] = totalprocesoactual= totalgobernante['actual']+totalsustantivo['actual']+totaladjetivo['actual']
                    data['totalprocesopro'] = totalprocesopro = totalgobernante['propuesto']+totalsustantivo['propuesto']+totaladjetivo['propuesto']
                    data['totalproceso'] = calculabrecha(totalprocesoactual,totalprocesopro)
                    data['totaljerarquico'] = totaljerarquico = total['anominadora']+total['viceministros']+total['subsecretarios']+total['coordinadores']+total['asesor']+total['coorddesp']+total['direccion']
                    data['ptotaljerarquico'] = ptotaljerarquico = total['panominadora']+total['pviceministros']+total['psubsecretarios']+total['pcoordinadores']+total['pasesor']+total['pcoorddesp']+total['pdireccion']
                    data['btotaljerarquico'] = calculabrecha(totaljerarquico,ptotaljerarquico)
                    data['totalrol'] = calculabrecha(totalactual,totalpropuesto)

                    data['brechaejecoord'] = calculabrecha(total['ejeccord'],total['pejeccord'])
                    data['brechaejesuper'] = calculabrecha(total['ejesuper'],total['pejesuper'])
                    data['brechaejepro'] = calculabrecha(total['ejecucion'],total['pejecucion'])
                    data['brechaejeapoyo'] = calculabrecha(total['tecnologico'],total['ptecnologico'])
                    data['brechaapoyo'] = calculabrecha(total['apoyo'],total['papoyo'])

                    brecha.jerarquico = totaljerarquico
                    brecha.pjerarquico = ptotaljerarquico

                    brecha.ejecucioncoord = total['ejeccord']
                    brecha.pejecucioncoord = total['pejeccord']

                    brecha.ejecucionsupervision = total['ejesuper']
                    brecha.pejecucionsupervision = total['pejesuper']

                    brecha.ejecucion = total['ejecucion']
                    brecha.pejecucion = total['pejecucion']

                    brecha.ejecucionapoyo = total['tecnologico']
                    brecha.pejecucionapoyo = total['ptecnologico']

                    brecha.apoyo = total['apoyo']
                    brecha.papoyo = total['papoyo']

                    brecha.gobernante = totalgobernante['actual']
                    brecha.pgobernante = totalgobernante['propuesto']

                    brecha.sustantivo = totalsustantivo['actual']
                    brecha.psustantivo = totalsustantivo['propuesto']

                    brecha.adjetivo = totaladjetivo['actual']
                    brecha.padjetivo = totaladjetivo['propuesto']

                    brecha.save()

                    data['title'] = u'MATRIZ CONSOLIDADA'
                    return render(request, "th_dir_planificacion/viewmatrizconsolidada.html", data)
                except Exception as ex:
                    pass
            #Reportes
            elif action == 'descargadiagnostico':
                try:
                    # periodo = PeriodoPlanificacionTH.objects.get(pk=request.GET['id'])
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('diagnostico')

                    ws.set_column(0, 36, 30)

                    formatoceldaleft = workbook.add_format({'text_wrap': True, 'align': 'left'})

                    formatoceldacenter = workbook.add_format(
                        {'border': 1, 'text_wrap': True, 'align': 'center', 'valign': 'vcenter'})

                    formatoceldagris = workbook.add_format( {'align': 'center', 'border': 1, 'text_wrap': True, 'fg_color': '#B6BFC0'})

                    ws.write('A1', 'REPORTE DE DIAGNÓSTICO INSTITUCIONAL',formatoceldaleft)
                    ws.write('A2', 'FECHA CON CORTE A: %s'%(datetime.today().date()),formatoceldaleft)
                    ws.write('A4', '1. Nombre de la institución',formatoceldagris)
                    ws.write('B4', '2. Nivel de desconcentración (planta Central o desconcentrado)',formatoceldagris)
                    ws.write('C4', '3. Tipología institucional',formatoceldagris)
                    ws.write('D4', '4. Partida general',formatoceldagris)
                    ws.write('E4', '5. Partida individual',formatoceldagris)
                    ws.write('F4', '6. Nivel o tipo de proceso (gobernante, agregador de valor, apoyo, etc.)',formatoceldagris)
                    ws.write('G4', '7. Unidad administrativa (unidad a la que pertenece el servidor)',formatoceldagris)
                    ws.write('H4', '8. Lugar de trabajo (Ciudad)',formatoceldagris)
                    ws.write('I4', '9. Apellidos y nombres del servidor',formatoceldagris)
                    ws.write('J4', '10. No. de documento (Cédula: 10 dígitos, en caso de iniciar con cero “0”, debe aparecer)',formatoceldagris)
                    ws.write('K4', '11. Puesto institucional (denominación del puesto)',formatoceldagris)
                    ws.write('L4', '12. Grupo ocupacional (servidor público 1,  servidor público 2, jerárquico superior 1, etc.)',formatoceldagris)
                    ws.write('M4', '13. Rol (Ejecución de procesos, Ejecución y supervisión de procesos, Ejecución y coordinación de procesos, etc)',formatoceldagris)
                    ws.write('N4', '14. Ámbito del puesto (nacional, zonal, regional, distrital, circuital, provincial, cantonal, parroquial)',formatoceldagris)
                    ws.write('O4', '15. Grado (1,2,3,4, etc)',formatoceldagris)
                    ws.write('P4', '16. Remuneración mensual unificada (Remuneración del puesto)',formatoceldagris)
                    ws.write('Q4', '17.1 Fecha de nacimiento Día',formatoceldagris)
                    ws.write('R4', '17.2 Fecha de nacimiento Mes',formatoceldagris)
                    ws.write('S4', '17.3 Fecha de nacimiento Año',formatoceldagris)
                    ws.write('T4', '18. Edad (años)',formatoceldagris)
                    ws.write('U4', '19. Género (masculino y femenino)',formatoceldagris)
                    ws.write('V4', '20. Etnia (indígena, montubio, etc)',formatoceldagris)
                    ws.write('W4', '21. Instrucción formal (técnico superior, tercer nivel, cuarto nivel, etc)',formatoceldagris)
                    ws.write('X4', '22. Régimen laboral (LOSEP, Código de trabajo, etc)',formatoceldagris)
                    ws.write('Y4', '23. Modalidad de prestación de servicios (nombramiento permanente, nombramiento provisional o contrato de servicios ocasionales)',formatoceldagris)
                    ws.write('Z4', '24. Fecha de ingreso a la institución (dd/mm/aaaa)',formatoceldagris)
                    ws.write('AA4', '25. Tiempo de servicio en la institución (años, meses)',formatoceldagris)
                    ws.write('AB4', '26. Tiempo de servicio en el sector público (años)',formatoceldagris)
                    ws.write('AC4', '27. Nro de imposiciones solo sector público',formatoceldagris)
                    ws.write('AD4', '28. Discapacidad',formatoceldagris)
                    ws.write('AE4', '29. Tipo de discapacidad (auditiva, física, visual, etc.)',formatoceldagris)
                    ws.write('AF4', '30. Sustitutos ',formatoceldagris)
                    ws.write('AG4', '31. Nombre completo del familiar',formatoceldagris)
                    ws.write('AH4', '32. Enfermedades catastróficas ',formatoceldagris)
                    ws.write('AI4', '33. Nombre de la enfermedad',formatoceldagris)
                    ws.write('AJ4', '34. Modalidad de la partida',formatoceldagris)
                    ws.write('AK4', '35. Observaciones',formatoceldagris)

                    plantillas = DistributivoPersona.objects.all()
                    i = 5

                    fecha_actual = datetime.now().date()#.strftime("%Y-%m-%d")


                    for  plantilla in plantillas:
                        perfil = plantilla.persona.mi_perfil()

                        ws.write('A%s'%i, 'UNIVERSIDAD ESTATAL DE MILAGRO',formatoceldaleft)
                        ws.write('B%s'%i, '',formatoceldaleft)
                        ws.write('C%s'%i, '',formatoceldaleft)
                        ws.write('D%s'%i, '',formatoceldaleft)
                        ws.write('E%s'%i, plantilla.partidaindividual,formatoceldaleft)
                        ws.write('F%s'%i, '',formatoceldaleft)
                        ws.write('G%s'%i, str(plantilla.unidadorganica),formatoceldaleft)
                        ws.write('H%s'%i, 'MILAGRO',formatoceldaleft)
                        ws.write('I%s'%i, str(plantilla.persona),formatoceldaleft)
                        ws.write('J%s'%i, plantilla.persona.identificacion(),formatoceldaleft)
                        ws.write('K%s'%i, str(plantilla.denominacionpuesto),formatoceldaleft)
                        ws.write('L%s'%i, str(plantilla.escalaocupacional),formatoceldaleft)
                        ws.write('M%s'%i, '')
                        ws.write('N%s'%i, 'CANTONAL',formatoceldaleft)
                        ws.write('O%s'%i, str(plantilla.grado),formatoceldaleft)
                        ws.write('P%s'%i, plantilla.rmupuesto,formatoceldaleft)
                        ws.write('Q%s'%i, plantilla.persona.nacimiento.day,formatoceldaleft)
                        ws.write('R%s'%i, str(MONTH_NAMES[(plantilla.persona.nacimiento.month) - 1]),formatoceldaleft)
                        ws.write('S%s'%i, plantilla.persona.nacimiento.year,formatoceldaleft)
                        ws.write('T%s'%i, str(plantilla.persona.edad()),formatoceldaleft)
                        ws.write('U%s'%i, str(plantilla.persona.sexo),formatoceldaleft)
                        ws.write('V%s'%i, str(perfil.raza if perfil.raza else ''))
                        ws.write('W%s'%i, str(plantilla.persona.titulacionmaxima() if plantilla.persona.titulacionmaxima() else '' ),formatoceldaleft)
                        ws.write('X%s'%i, str(plantilla.regimenlaboral),formatoceldaleft)
                        ws.write('Y%s'%i, str(plantilla.modalidadlaboral),formatoceldaleft)

                        #FECHA DE INGRESO OBTENIDA DEL MODELO INGRESOPERSONAL
                        ingreso = plantilla.persona.ingresopersonal_set.filter(status=True)
                        tiempo_trabajado = ""
                        if ingreso:
                            fechain_cadena = datetime.strftime(ingreso[0].fechaingreso, "%d-%m-%Y")

                            fechain_date = datetime.strptime(fechain_cadena, "%d-%m-%Y").date()
                            mes_actual = fechain_date.today().month
                            mes_ingreso = fechain_date.month
                            meses_trabajados = mes_actual - mes_ingreso

                            if mes_ingreso < mes_actual:
                                 meses_trabajados = mes_actual - mes_ingreso
                            elif mes_ingreso >= mes_actual:
                                 meses_trabajados = fechain_date.today().month

                            calculo_fecha = fecha_actual - fechain_date
                            mes, anios_trabajados = math.modf(calculo_fecha.days/365)



                        ws.write('Z%s' % i, fechain_cadena,formatoceldaleft)
                        ws.write('AA%s' % i, f'{round(anios_trabajados)} AÑOS Y {meses_trabajados} MESES', formatoceldaleft)
                        ws.write('AB%s'%i, '',formatoceldaleft) #--tiempo de servicio en el sector publico
                        ws.write('AC%s'%i, '',formatoceldaleft) #-- Nro de imposiciones solo sector público

                        #AGG LAS VARIABLES PARA SUSTITUTO Y EVALUE EL OBJECTS TRAYENDO EL REGISTRO DE PERSONA DATOS FAMILIARES
                        tienesustituto = 'NO'
                        nombresustituto = ''
                        discapacidad ='NO'
                        tipodiscapacidad = ''

                        if perfil.tienediscapacidad:
                            discapacidad = 'SI'
                            tipodiscapacidad = str(perfil.tipodiscapacidad)

                            familiar = plantilla.persona.personadatosfamiliares_set.filter(status=True, essustituto=True)
                            if familiar:
                                tienesustituto = 'SI'
                                nombresustituto = familiar[0].nombre

                        ws.write('AD%s'%i, discapacidad,formatoceldaleft) #--discapacidad
                        ws.write('AE%s'%i, tipodiscapacidad,formatoceldaleft) #--tipodiscapacidad
                        ws.write('AF%s'%i, tienesustituto,formatoceldaleft) #--sustitutos
                        ws.write('AG%s'%i, nombresustituto,formatoceldaleft)#--nombre del sustituto
                        # ws.write('AH%s'%i, '32. Enfermedades catastróficas ',formatoceldaleft)
                        # ws.write('AI%s'%i, '33. Nombre de la enfermedad',formatoceldaleft)
                        i+=1

                    workbook.close()
                    output.seek(0)
                    filename = 'diagnostico_institucional.xlsx'
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'descargaplantilla':
                try:
                    gestion = GestionPlanificacionTH.objects.get(pk=request.GET['idg'])
                    brecha = ReporteBrechasTH.objects.get(status=True,gestion=gestion)
                    productos = GestionProductoServicioTH.objects.filter(status=True,gestion=gestion)

                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('plantilla_')
                    ws.set_landscape()
                    ws.set_paper(9)
                    ws.set_column(0, 0, 11)
                    ws.set_column(1, 2, 16)
                    ws.set_column(3, 3, 7)
                    ws.set_column(4, 4, 12)
                    ws.set_column(5, 5, 8)
                    ws.set_column(6, 6, 7)
                    ws.set_column(7, 8, 6)
                    ws.set_column(9, 14, 5)
                    ws.set_row(5, 40)
                    ws.set_row(6, 40)
                    ws.set_row(7, 40)


                    title = workbook.add_format({
                        'bold': 1,
                        'border': 1,
                        'align': 'center',
                        'valign': 'vcenter',
                        'bg_color': 'silver',
                        'text_wrap': 1,
                        'font_size': 10})

                    formatoceldaleft = workbook.add_format({'border': 1,'text_wrap': True,'align': 'center', 'font_size': 5,'valign': 'vcenter','font_name':'Century Gothic'})

                    formatoceldacenter = workbook.add_format({'border': 1,'text_wrap': True,'align': 'center','valign': 'vcenter','font_size': 5,'font_name':'Century Gothic'})


                    formatotitulo = workbook.add_format(
                        {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 10,'border': 1,'text_wrap': True,'font_color': 'blue','font_name':'Century Gothic'})

                    formatosubtitulo = workbook.add_format(
                        {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 7,'border': 1,'text_wrap': True,'font_name':'Century Gothic'})

                    formatotitulo1 = workbook.add_format({'text_wrap': True,'align': 'right','font_size': 7,'font_color': 'blue','font_name':'Century Gothic'})

                    formatotitulo2 = workbook.add_format({'text_wrap': True,'font_size': 7,'align': 'left','font_name':'Century Gothic'})

                    formatoceldatitulo = workbook.add_format({'align': 'center', 'valign': 'vcenter','border': 1,'text_wrap': True,
                                                              'bold':1,'font_size': 5,'fg_color': '#A9BCD6','font_name':'Century Gothic'})
                    formatoceldatitulo3 = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True,
                                                               'bold':1,'font_size': 4, 'fg_color': '#A9BCD6', 'font_name': 'Century Gothic'})
                    formatoceldatitulo2 = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True,
                                                               'font_size': 4, 'fg_color': '#A9BCD6', 'font_name': 'Century Gothic'})
                    formatoceldatotal = workbook.add_format({'bold': 1,'align': 'center', 'valign': 'vcenter' ,'border': 1,'text_wrap': True,'fg_color': '#A9D3D6','font_size': 5,'font_name':'Century Gothic'})

                    formatoceldagris = workbook.add_format({'align': 'center', 'valign': 'vcenter','border': 1,'text_wrap': True,'fg_color': '#B6BFC0','font_size': 5,'font_name':'Century Gothic'})

                    formatoceldagrisv = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1,
                                                             'text_wrap': True, 'fg_color': '#A9BCD6','font_size': 4,'font_name':'Century Gothic'})
                    formatoceldagrisv.set_rotation(90)

                    estilo7 = workbook.add_format(
                        {'align': 'center', 'valign': 'top', 'bold': 1, 'font_size': 5,'text_wrap': True,'font_name':'Century Gothic'})

                    estilo9= workbook.add_format(
                        {'align': 'center', 'valign': 'bottom', 'bold': 1, 'font_size': 5, 'text_wrap': True, 'font_name': 'Century Gothic'})


                    estilo1 = workbook.add_format(
                        {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 5,'border': 1,'text_wrap': True,'font_name':'Century Gothic'})

                    estilo6 = workbook.add_format(
                        {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 5,'border': 1,'text_wrap': True,'font_name':'Century Gothic'})


                    logominurl =  'https://sga.unemi.edu.ec/static/images/logo-ministeriot.png'
                    logunemiurl = 'https://sga.unemi.edu.ec/static/images/LOGO-UNEMI-2020.png'

                    logomin = io.BytesIO(urlopen(logominurl).read())
                    logunemi = io.BytesIO(urlopen(logunemiurl).read())

                    ws.merge_range('A1:B2', '', formatotitulo)
                    ws.merge_range('J1:O2', '', formatotitulo)

                    ws.insert_image('J1',logunemiurl, {'x_scale': 0.16, 'y_scale': 0.10,'image_data': logunemi})
                    ws.insert_image('A1',logominurl, {'x_scale': 0.16, 'y_scale': 0.11,'y_offset':1,'image_data':logomin})
                    ws.merge_range('C1:I1', 'PLANIFICACION DEL TALENTO HUMANO', formatotitulo)
                    ws.merge_range('C2:I2', str(gestion.cabecera.periodo),formatosubtitulo)
                    ws.merge_range('A3:B3', 'NOMBRE DE LA INSTITUCIÓN:',formatotitulo1)
                    ws.merge_range('C3:G3', 'UNIVERSIDAD ESTATAL DE MILAGRO',formatotitulo2)
                    ws.merge_range('H3:J3', 'NIVEL TERRITORIAL:',formatotitulo1)
                    ws.merge_range('K3:L3', str(gestion.cabecera.tterritorial()),formatotitulo2)
                    ws.merge_range('A4:B4', 'MACROPROCESO AL QUE PERTENECE:',formatotitulo1)
                    ws.merge_range('C4:G4', str(gestion.cabecera.departamento),formatotitulo2)
                    ws.merge_range('H4:J4', 'TIPO DE PROCESO:',formatotitulo1)
                    ws.merge_range('K4:L4', str(gestion.cabecera.proceso()),formatotitulo2)
                    ws.merge_range('A5:B5','UNIDAD, PROCESO O PROYECTO:',formatotitulo1)
                    ws.merge_range('C5:G5', str(gestion.gestion),formatotitulo2)
                    ws.merge_range('H5:J5','FECHA:',formatotitulo1)
                    ws.merge_range('K5:L5', str(datetime.now().date()),formatotitulo2)

                    ws.merge_range('A6:A8', 'PORTAFOLIO DE PRODUCTOS O SERVICIOS', formatoceldatitulo)
                    ws.merge_range('B6:C8','ACTIVIDADES SECUENCIALES', formatoceldatitulo)
                    ws.merge_range('D6:D8', 'TIPO DE ACTIVIDAD', formatoceldatitulo)
                    ws.merge_range('E6:E8', 'PRODUCTO O SERVICIOS INTERMEDIO OBTENIDO DE LA ACTIVIDAD', formatoceldatitulo)
                    ws.merge_range('F6:F8', 'FRECUENCIA', formatoceldatitulo3)
                    ws.write('G6', 'VOLUMEN', formatoceldatitulo3)
                    ws.merge_range('G7:G8', 'N° DE PRODUCTOS O SERVICIOS INTERMEDIOS', formatoceldatitulo2)
                    ws.merge_range('H6:I6', 'TIEMPO DE EJECUCIÓN EN MINUTOS POR PRODUCTO O SERVICIO INTERMEDIO',formatoceldatitulo3)
                    ws.merge_range('H7:H8', 'TIEMPO MÍNIMO', formatoceldatitulo2)
                    ws.merge_range('I7:I8', 'TIEMPO MÁXIMO', formatoceldatitulo2)
                    ws.merge_range('J6:O6', 'PORCENTAJE DE PARTICIPACIÓN DEL ROL EN LA ACTIVIDAD', formatoceldatitulo3)
                    ws.merge_range('J7:J8', 'DIRECCIÓN', formatoceldagrisv)
                    ws.merge_range('K7:K8', 'EJECUCIÓN Y COORDINACION DE PROCESOS', formatoceldagrisv)
                    ws.merge_range('L7:L8', 'EJECUCIÓN Y SUPERVISIÓN DE PROCESOS', formatoceldagrisv)
                    ws.merge_range('M7:M8', 'EJECUCIÓN DE PROCESOS', formatoceldagrisv)
                    ws.merge_range('N7:N8', u'EJECUCIÓN DE PROCESOS DE APOYO', formatoceldagrisv)
                    ws.merge_range('O7:O8', u'TÉCNICO', formatoceldagrisv)
                    a = 8
                    val = 0

                    # productos = ProductoServicioSeccion.objects.filter(status=True, seccion=gestion)
                    for producto in productos:
                        actividades = producto.actividades()
                        if actividades.count() > 0:
                            val = actividades.count() - 1
                            ws.merge_range('A%s:A%s'%(a+1,a+1+val), producto.producto.nombre, formatoceldacenter)

                            for act in actividades:
                                ws.merge_range(a, 1,a,2, act.actividad, formatoceldacenter)
                                ws.write(a, 3, str(act.ttipoactividad()), formatoceldaleft)
                                ws.write(a, 4, str(act.productointermedio), formatoceldacenter)
                                ws.write(a, 5, str(act.tfrecuencia()), formatoceldaleft)
                                ws.write(a, 6, str(act.volumen), formatoceldaleft)
                                ws.write(a, 7, str(act.tiempomin), formatoceldaleft)
                                ws.write(a, 8, str(act.tiempomax), formatoceldaleft)
                                ws.write(a, 9, str(act.pdireccion), formatoceldaleft)
                                ws.write(a, 10, str(act.pejecucioncoord), formatoceldaleft)
                                ws.write(a, 11, str(act.pejecucionsupervision), formatoceldaleft)
                                ws.write(a, 12, str(act.pejecucion), formatoceldaleft)
                                ws.write(a, 13, str(act.pejecucionapoyo), formatoceldaleft)
                                ws.write(a, 14, str(act.ptecnico), formatoceldaleft)
                                a += 1

                    a += 4
                    ws.merge_range('B%s:F%s'%(a,a), 'REPORTE DE BRECHAS', formatoceldatitulo)
                    a+=1
                    ws.write('B%s'%(a), 'ROLES', formatoceldatitulo)
                    ws.write('C%s'%(a), 'SITUACIÓN ACTUAL', formatoceldatitulo)
                    ws.write('D%s'%(a), 'SITUACIÓN PROPUESTA', formatoceldatitulo)
                    ws.write('E%s'%(a), 'BRECHA', formatoceldatitulo)
                    ws.write('F%s'%(a), '', formatoceldatitulo)
                    a+=1
                    ws.write('B%s'%(a), 'DIRECCIÓN', estilo6)
                    ws.write('C%s'%(a), brecha.direccion,estilo1)
                    ws.write('D%s'%(a), brecha.pdireccion, estilo1)
                    ws.write('E%s'%(a), brecha.totaldireccion(), estilo1)
                    ws.write('F%s'%(a), brecha.paldireccion(), estilo1)
                    a+=1
                    ws.write('B%s'%(a), 'EJECUCIÓN Y COORDINACIÓN DE PROCESOS', estilo6)
                    ws.write('C%s'%(a), brecha.ejecucioncoord,estilo1)
                    ws.write('D%s'%(a), brecha.pejecucioncoord, estilo1)
                    ws.write('E%s'%(a), brecha.totalejecucioncoord(), estilo1)
                    ws.write('F%s'%(a), brecha.palejecucioncoord(), estilo1)
                    a += 1
                    ws.write('B%s' % (a), 'EJECUCIÓN Y SUPERVISIÓN DE PROCESOS', estilo6)
                    ws.write('C%s' % (a), brecha.ejecucionsupervision,estilo1)
                    ws.write('D%s' % (a), brecha.pejecucionsupervision, estilo1)
                    ws.write('E%s'%(a), brecha.totalejecucionsupervision(), estilo1)
                    ws.write('F%s' % (a), brecha.palpejecucionsupervision(), estilo1)
                    a+=1
                    ws.write('B%s' % (a), 'EJECUCIÓN DE PROCESOS', estilo6)
                    ws.write('C%s' % (a), brecha.ejecucion,estilo1)
                    ws.write('D%s' % (a), brecha.pejecucion, estilo1)
                    ws.write('E%s' % (a), brecha.totalejecucion(), estilo1)
                    ws.write('F%s' % (a), brecha.palejecucion(), estilo1)
                    a+=1
                    ws.write('B%s' % (a), 'EJECUCIÓN DE PROCESOS DE APOYO', estilo6)
                    ws.write('C%s' % (a), brecha.ejecucionapoyo,estilo1)
                    ws.write('D%s' % (a), brecha.pejecucionapoyo, estilo1)
                    ws.write('E%s' % (a), brecha.totalejecucionapoyo(), estilo1)
                    ws.write('F%s' % (a), brecha.palpejecucionapoyo(), estilo1)
                    a+=1
                    ws.write('B%s' % (a), 'TÉCNICO', estilo6)
                    ws.write('C%s' % (a), brecha.tecnico,estilo1)
                    ws.write('D%s' % (a), brecha.ptecnico, estilo1)
                    ws.write('E%s' % (a), brecha.totaltecnico(), estilo1)
                    ws.write('F%s' % (a), brecha.paltecnico(), estilo1)
                    a+=1
                    ws.write('B%s' % (a), 'ADMINISTRATIVO', estilo6)
                    ws.write('C%s' % (a), brecha.administrativo,estilo1)
                    ws.write('D%s' % (a), brecha.padministrativo, estilo1)
                    ws.write('E%s' % (a), brecha.totaladministrativo(), estilo1)
                    ws.write('F%s' % (a), brecha.palpadministrativo(), estilo1)
                    a += 1
                    ws.write('B%s' % (a), 'SERVICIOS', estilo6)
                    ws.write('C%s' % (a), brecha.servicios,estilo1)
                    ws.write('D%s' % (a), brecha.pservicios, estilo1)
                    ws.write('E%s' % (a), brecha.totalservicios(), estilo1)
                    ws.write('F%s' % (a), brecha.palservicios(), estilo1)
                    a += 1
                    ws.write('B%s' % (a), 'BRECHA GENERAL DE LA UNIDAD O PROCESOS INTERNO', formatoceldatotal)
                    ws.write('C%s' % (a), str(brecha.totalactual()), formatoceldatotal)
                    ws.write('D%s' % (a), str(brecha.totalpropuesto()), formatoceldatotal)
                    ws.write('E%s' % (a), str(brecha.totalbrecha()), formatoceldatotal)
                    ws.write('F%s' % (a), str(brecha.totpalabras()), formatoceldatotal)
                    a += 1
                    ws.merge_range('B%s:F%s' % (a,a),'La situación actual presentada esta conformada por el siguiente número de servidores bajo la modalidad de:',formatoceldagris)
                    a += 2
                    #
                    ws.write('B%s' % (a), 'CONTRATO DE SERVICIOS OCASIONALES ESCALA DE 20 GRADOS', formatoceldagris)
                    ws.write('C%s' % (a), brecha.contrato, formatoceldacenter)
                    ws.write('B%s' % (a+1), 'NOMBRAMIENTOS PROVISIONALES', formatoceldagris)
                    ws.write('C%s' % (a+1), brecha.provisional, formatoceldacenter)
                    ws.write('B%s' % (a+2), 'NOMBRAMIENTOS PERMANENTES', formatoceldagris)
                    ws.write('C%s' % (a+2), brecha.permanente, formatoceldacenter)
                    ws.write('B%s' % (a+3), 'NJS', formatoceldagris)
                    ws.write('C%s' % (a+3), brecha.njs, formatoceldacenter)
                    ws.write('B%s' % (a+4), 'CÓDIGO DE TRABAJO', formatoceldagris)
                    ws.write('C%s' % (a+4), brecha.trabajo, formatoceldacenter)
                    ws.write('B%s' % (a+5), 'OTROS REGÍMENES', formatoceldagris)
                    ws.write('C%s' % (a+5), brecha.otros, formatoceldacenter)
                    ws.write('B%s' % (a+6), 'VACANTES', formatoceldagris)
                    ws.write('C%s' % (a+6), brecha.vacantes, formatoceldacenter)
                    ws.write('B%s' % (a+7), 'TOTAL', formatoceldatotal)
                    ws.write('C%s' % (a+7), brecha.totalloes(),formatoceldacenter)
                    mensaje = ''
                    if brecha.totalactual() < brecha.totalpropuesto():
                        mensaje = 'REALIZAR AUDITORÍA, la unidad o proceso interno deberá presentar respaldos físicos y/o digitales de los datos empleados en su plantilla, para validar y justificar la brecha resultante. Realizar optimización del talento humano por cada rol.'
                    elif brecha.totalactual() == brecha.totalpropuesto():
                        mensaje = 'NO HAY INCREMENTO DE SERVIDORES de acuerdo a la brecha general de la unidad o proceso interno, sin embargo, revisar si se debe realizar optimización del talento humano por cada rol, de ser el caso.'
                    if brecha.totalactual() > brecha.totalpropuesto():
                        mensaje = 'EL NÚMERO DE SERVIDORES ACTUAL de la unidad o proceso interno es SUPERIOR AL NÚMERO PROPUESTO, según a la brecha general obtenida. Se deberá realizar la optimización del talento humano por cada rol, considerando movimientos de personal antes de optar por desvinculaciones.'

                    ws.merge_range('B%s:F%s' % (a+10,a+10), 'CONCLUSIÓN PARA LA UATH INSTITUCIONAL', formatoceldatitulo)
                    ws.merge_range('B%s:F%s' % (a+11,a+13), mensaje, formatoceldagris)

                    ws.merge_range('B%s:C%s' % (a+20,a+20), '__________________________________', estilo7)
                    ws.merge_range('B%s:C%s' % (a+21,a+21), 'FIRMA', estilo7)
                    ws.merge_range('B%s:C%s' % (a+22,a+22), 'RESPONSABLE DE LA UNIDAD O PROCESO INTERNO', estilo9)
                    ws.merge_range('B%s:C%s' % (a+23,a+23), str(gestion.cabecera.departamento.responsable), estilo7)

                    ws.merge_range('E%s:F%s' % (a+20,a+20), '__________________________________', estilo7)
                    ws.merge_range('E%s:F%s' % (a+21,a+21), 'FIRMA', estilo7)
                    ws.merge_range('E%s:F%s' % (a+22,a+22), 'RESPONSABLE DE LA UATH INSTITUCIONAL', estilo7)
                    ws.merge_range('E%s:F%s' % (a+23,a+23), str(gestion.cabecera.periodo.responsable), estilo7)

                    ws.merge_range('B%s:C%s' % (a+24,a+24), 'RESPONSABLE',estilo9)
                    ws.merge_range('B%s:C%s' % (a+25,a+25), 'NOMBRE: %s' % gestion.responsable,estilo7)
                    ws.merge_range('B%s:C%s' % (a+26,a+26), 'RESPONSABLE SUBROGANTE',estilo9)
                    ws.merge_range('B%s:C%s' % (a+27,a+27), 'NOMBRE: %s' % gestion.responsablesubrogante,estilo7)

                    workbook.close()
                    output.seek(0)
                    filename = 'plantilla' + random.randint(1,10000).__str__() + '.xlsx'
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename

                    return response
                except Exception as ex:
                    pass

            elif action == 'cambiarEstadoDepartamento':
                try:
                    data['filtro'] = filtro = CabPlanificacionTH.objects.get(pk=encrypt(request.GET['id']))
                    data['id'] = request.GET['id']
                    data['form'] = CambiarEstadoDepartamentoForm(initial =model_to_dict(filtro))
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})

                except Exception as ex:
                    pass

            elif action == 'aprobaruath':
                try:
                    data['id'] = request.GET['id']
                    data['form'] = CambiarAprobarUathForm()
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})

                except Exception as ex:
                    pass

            elif action == 'cambiarResponsableGestion':
                try:
                    data['id'] = filtro = request.GET['id']
                    form =ResponsableGestionForm()
                    form.fields['responsable'].queryset = Persona.objects.none()
                    form.fields['subrogante'].queryset = Persona.objects.none()
                    data['form'] = form
                    template = get_template('th_dir_planificacion/modal/formresponsablegestion.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})

                except Exception as ex:
                    pass

            elif action == 'buscarpersonas':
                try:
                    resp = filtro_persona_select(request)
                    return HttpResponse(json.dumps({'status': True, 'results': resp}))
                except Exception as ex:
                    pass

            elif action == 'cambiarEstadoGestionPlanificacionTH':
                try:
                    data['id'] = request.GET['id']
                    form =CambiarEstadoGestionPlanificacionTHForm()
                    data['form'] = form
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})

                except Exception as ex:
                    pass

            elif action == 'buscarpersona':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    query = Persona.objects.filter(status=True)
                    if len(s) == 1:
                        per = query.filter((Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(apellido2__icontains=q) | Q(cedula__contains=q))).distinct()[:15]
                    elif len(s) == 2:
                        per = query.filter((Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) |
                                           (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1])) |
                                           (Q(nombres__icontains=s[0]) & Q(apellido1__contains=s[1]))).distinct()[:15]
                    else:
                        per = query.filter((Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) &
                                            Q(apellido2__contains=s[2])) | (Q(nombres__contains=s[0]) &
                                            Q(nombres__contains=s[1]) & Q(apellido1__contains=s[2]))).distinct()[:15]
                    data = {"result": "ok",
                            "results": [{"id": x.id, "name": str(x.nombre_completo())}
                                        for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'movergestion':
                try:
                    data['filtro'] = filtro = GestionPlanificacionTH.objects.get(pk=encrypt(request.GET['id']))
                    data['id'] = request.GET['id']
                    form =MoverGestionForm(initial =model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("ajaxformmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})

                except Exception as ex:
                    pass

            elif action == 'cambiarproducto':
                try:
                    data['id'] = request.GET['id']
                    form =CambiarProductoForm()
                    producto = GestionProductoServicioTH.objects.get(id=encrypt(request.GET['id']))
                    gestionplan = producto.gestion
                    data['idp']=encrypt(producto.gestion.cabecera.pk)
                    form.cambiar(gestionplan)
                    data['form'] = form
                    data['header_info'] = f'Si no encuentra el producto que desea, puede crearlo en el siguiente enlace:' \
                                          f'<a target="_blank" href="/adm_departamentos?action=viewproductos&id={gestionplan.gestion.id}"' \
                                          f'class="btn btn-primary-old btn-sm">' \
                                          f' <i class="bi bi-link-45deg fs-5"></i> Gestionar productos</a><br>' \
                                          f'Una vez creado el producto, vuelva a esta ventana y recargue la página para poder visualizar el nuevo producto a adicionar.'
                    template = get_template("ajaxformmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})

                except Exception as ex:
                    pass

            elif action == 'descargamatrizconsolidada':
                try:
                    periodo = PeriodoPlanificacionTH.objects.get(pk=request.GET['idp'])
                    direcciones = periodo.direccionesaprobadas()
                    brecha = ReporteBrechasPeriodoTH.objects.get(status=True,periodo=periodo)
                    total = periodo.totaldireccionesaprobadas()
                    totalactual = total['anominadora'] + total['viceministros'] + total[
                        'subsecretarios'] + total['coordinadores'] + total['asesor'] + total['coorddesp'] + \
                                                        total['direccion'] + total['ejeccord'] + total['ejesuper'] + \
                                                        total['ejecucion'] + total['tecnologico'] + total['apoyo']
                    totalpropuesto = total['anominadora'] + total['pviceministros'] + total[
                        'psubsecretarios'] + total['pcoordinadores'] + total['pasesor'] + total['pcoorddesp'] + \
                                                              total['pdireccion'] + total['pejeccord'] + total[
                                                                  'pejesuper'] + total['pejecucion'] + total[
                                                                  'ptecnologico'] + total['papoyo']
                    totalservactual= totalactual + brecha.totalcodtrabajo + brecha.totalregespecial
                    totalservpropuesto= totalpropuesto + brecha.ptotalcodtrabajo + brecha.ptotalregespecial

                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('plantilla_')
                    ws.set_column(1, 60)
                    ws.set_row(13, 20)


                    title = workbook.add_format({
                        'bold': 1,
                        'border': 1,
                        'align': 'center',
                        'valign': 'vcenter',
                        'bg_color': 'silver',
                        'text_wrap': 1,
                        'font_size': 10})

                    formatoceldaleft = workbook.add_format({'font_size': 6,'border': 1,'text_wrap': True,'align': 'left'})

                    formatoceldacenter = workbook.add_format({'font_size': 6,'border': 1,'text_wrap': True,'align': 'center','valign': 'vcenter'})


                    formatotitulo = workbook.add_format(
                        {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 12,'border': 1,'text_wrap': True,'font_color': 'blue'})

                    formatosubtitulo = workbook.add_format(
                        {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 10,'border': 1,'text_wrap': True})

                    formatotitulo1 = workbook.add_format({'text_wrap': True,'align': 'right','font_color': 'blue','font_size': 12})

                    formatotitulo2 = workbook.add_format({'text_wrap': True,'align': 'left','font_size': 12})

                    formatoceldasinborde = workbook.add_format({'text_wrap': True,'bold':True,'align': 'center','font_size': 6})

                    formatoceldatitulo = workbook.add_format({'align': 'center','border': 1,'text_wrap': True,'fg_color': '#A9BCD6'})

                    formatoceldatotal = workbook.add_format({'bold': 1,'align': 'center','border': 1,'text_wrap': True,'fg_color': '#A9D3D6'})

                    formatoceldagrist = workbook.add_format({'font_size': 10,'align': 'center','valign': 'vcenter','border': 1,'text_wrap': True,'fg_color': '#B6BFC0'})

                    formatoceldagris = workbook.add_format({'font_size': 6,'align': 'center','valign': 'vcenter','border': 1,'text_wrap': True,'fg_color': '#B6BFC0'})

                    formatoceldagrisv = workbook.add_format({'font_size': 6,'align': 'center','valign': 'vcenter','border': 1,'text_wrap': True,'fg_color': '#B6BFC0'})
                    formatoceldagrisv.set_rotation(90)


                    estilo7 = workbook.add_format(
                        {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 14,'text_wrap': True})

                    estilo1 = workbook.add_format(
                        {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 12,'border': 1,'text_wrap': True})

                    estilo6 = workbook.add_format(
                        {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 12,'border': 1,'text_wrap': True})


                    logominurl =  'https://sga.unemi.edu.ec/static/images/logo-ministeriot.png'
                    logunemiurl = 'https://sga.unemi.edu.ec/static/images/LOGO-UNEMI-2020.png'

                    logomin = io.BytesIO(urlopen(logominurl).read())
                    logunemi = io.BytesIO(urlopen(logunemiurl).read())

                    ws.merge_range('A1:F6', '', formatotitulo)
                    ws.merge_range('V1:AA6', '', formatotitulo)

                    ws.insert_image('V1',logunemiurl, {'x_scale': 0.30, 'y_scale': 0.30,'image_data': logunemi})
                    ws.insert_image('A1',logominurl, {'x_scale': 0.31, 'y_scale': 0.31,'image_data':logomin})
                    ws.merge_range('G1:U3', 'PLANIFICACION DEL TALENTO HUMANO', formatotitulo)
                    ws.merge_range('G4:U6', 'MATRIZ DE PLANIFICACION DEL TALENTO HUMANO POR NIVELES TERRITORIALES AÑO-%s'%(periodo.anio),formatosubtitulo)
                    ws.merge_range('A8:C8', 'INSTITUCIÓN:',formatotitulo1)
                    ws.merge_range('D8:G8', 'UNIVERSIDAD ESTATAL DE MILAGRO',formatotitulo2)
                    ws.merge_range('A9:C9', 'DETALLE(Zonal/Distrito/Ciruito/ o sus equivalentes)',formatotitulo1)
                    ws.merge_range('D9:G9', 'MILAGRO-GUAYAS',formatotitulo2)
                    ws.merge_range('P8:U8', 'NIVEL TERRITORIAL:',formatotitulo1)
                    ws.merge_range('V8:AA8', 'CENTRAL:',formatotitulo2)
                    ws.merge_range('P9:U9', 'FECHA:',formatotitulo1)
                    ws.merge_range('V9:AA9', str(datetime.now().date()),formatotitulo2)

                    ws.merge_range('A11:B12', 'ESTRUCTURA ORGÁNICA INSTITUCIONAL', formatoceldatitulo)
                    ws.write('A13','Proceso', formatoceldatitulo)
                    ws.write('B13','Unidad administrativa', formatoceldatitulo)
                    ws.merge_range('C11:N11', 'SITUACIÓN ACTUAL', formatoceldatitulo)

                    ws.merge_range('C12:I12', 'N° De Puestos de Nivel Jerárquico Superior',formatoceldagrist)
                    ws.write( 'C13','Autoridad nominadora',formatoceldagrisv)
                    ws.write( 'D13', 'Viceministros',formatoceldagrisv)
                    ws.write( 'E13','Subsecretarios',formatoceldagrisv)
                    ws.write( 'F13', 'Coordinadores',formatoceldagrisv)
                    ws.write( 'G13','Asesor',formatoceldagrisv)
                    ws.write( 'H13','Coordinador de despacho',formatoceldagrisv)
                    ws.write( 'I13','Dirección',formatoceldagrisv)

                    ws.merge_range('J12:N12', 'N° De Puestos Bajo el Rol de:',formatoceldagrist)
                    ws.write( 'J13','Ejecución y coordinación de procesos', formatoceldagrisv)
                    ws.write( 'K13','Ejecución y supervisión de procesos', formatoceldagrisv)
                    ws.write( 'L13','Ejecución de procesos', formatoceldagrisv)
                    ws.write( 'M13','Ejecución de procesos de apoyo y tecnológico ', formatoceldagrisv)
                    ws.write( 'N13','Apoyo administrativo', formatoceldagrisv)

                    ws.merge_range('P11:AA11', 'SITUACIÓN PROPUESTA', formatoceldatitulo)

                    ws.merge_range('P12:V12', 'N° De Puestos de Nivel Jerárquico Superior',formatoceldagrist)
                    ws.write('P13', 'Autoridad nominadora',formatoceldagrisv)
                    ws.write('Q13', 'Viceministros',formatoceldagrisv)
                    ws.write('R13', 'Subsecretarios',formatoceldagrisv)
                    ws.write('S13', 'Coordinadores',formatoceldagrisv)
                    ws.write('T13', 'Asesor',formatoceldagrisv)
                    ws.write('U13', 'Coordinador de despacho',formatoceldagrisv)
                    ws.write('V13', 'Dirección',formatoceldagrisv)

                    ws.merge_range('W12:AA12', 'N° De Puestos Bajo el Rol de:',formatoceldagrist)
                    ws.write('W13', 'Ejecución y coordinación de procesos', formatoceldagrisv)
                    ws.write('X13', 'Ejecución y supervisión de procesos', formatoceldagrisv)
                    ws.write('Y13', 'Ejecución de procesos', formatoceldagrisv)
                    ws.write('Z13', 'Ejecución de procesos de apoyo y tecnológico ', formatoceldagrisv)
                    ws.write('AA13', 'Apoyo administrativo', formatoceldagrisv)

                    ws.merge_range('AC11:AM11', 'REPORTE DE BRECHAS POR UNIDAD, PROCESO O PROYECTO',formatoceldatitulo)
                    ws.write('AC12', '',formatoceldagrisv)
                    ws.write('AC13', 'DIRECCIÓN',formatoceldagrisv)

                    ws.merge_range('AD12:AE12', 'Ejecución y coordinación de procesos',formatoceldagrist)
                    ws.write('AD13','Brecha',formatoceldagrisv)
                    ws.write('AE13', 'Observaciones',formatoceldagrisv)

                    ws.merge_range('AF12:AG12', 'Ejecución y supervisión de procesos',formatoceldagrist)
                    ws.write('AF13', 'Brecha',formatoceldagrisv)
                    ws.write('AG13', 'Observaciones',formatoceldagrisv)

                    ws.merge_range('AH12:AI12', 'Ejecución de procesos',formatoceldagrist)
                    ws.write('AH13', 'Brecha',formatoceldagrisv)
                    ws.write('AI13', 'Observaciones',formatoceldagrisv)

                    ws.merge_range('AJ12:AK12', 'Ejecución de procesos de apoyo y tecnológico',formatoceldagrist)
                    ws.write('AJ13', 'Brecha',formatoceldagrisv)
                    ws.write('AK13', 'Observaciones',formatoceldagrisv)

                    ws.merge_range('AL12:AM12', 'Apoyo administrativo',formatoceldagrist)
                    ws.write('AL13', 'Brecha',formatoceldagrisv)
                    ws.write('AM13', 'Observaciones',formatoceldagrisv)

                    i=13
                    a = 12
                    val = 0


                    for direccion in direcciones:

                        ws.write(i, 0, direccion.proceso() ,formatoceldaleft)
                        ws.write(i, 1, str(direccion.departamento) ,formatoceldaleft)
                        ws.write(i, 2, direccion.totalanominadora()['valor'] ,formatoceldagris)
                        ws.write(i, 3, direccion.totalviceministros()['valor'] ,formatoceldagris)
                        ws.write(i, 4, direccion.totalsubsecretarios()['valor'] ,formatoceldagris)
                        ws.write(i, 5, direccion.totalcoordinadores()['valor'] ,formatoceldagris)
                        ws.write(i, 6, direccion.totalasesor()['valor'] ,formatoceldagris)
                        ws.write(i, 7, direccion.totalcoorddespacho()['valor'] ,formatoceldagris)

                        ws.write(i, 8, direccion.totaldireccion()['valor'],formatoceldacenter)
                        ws.write(i, 9, direccion.totalejecucioncoord()['valor'],formatoceldacenter)
                        ws.write(i, 10, direccion.totalejecucionsupervision()['valor'],formatoceldacenter)
                        ws.write(i, 11, direccion.totalejecucion()['valor'],formatoceldacenter)
                        ws.write(i, 12, direccion.totalejecucionapoyo()['valor'],formatoceldacenter)
                        ws.write(i, 13, direccion.totaltecnico()['valor'],formatoceldacenter)

                        ws.write(i, 15, direccion.totalpanominadora()['valor'] ,formatoceldagris)
                        ws.write(i, 16, direccion.totalpviceministros()['valor'] ,formatoceldagris)
                        ws.write(i, 17, direccion.totalpsubsecretarios()['valor'] ,formatoceldagris)
                        ws.write(i, 18, direccion.totalpcoordinadores()['valor'] ,formatoceldagris)
                        ws.write(i, 19, direccion.totalpasesor()['valor'] ,formatoceldagris)
                        ws.write(i, 20, direccion.totalpcoorddespacho()['valor'] ,formatoceldagris)

                        ws.write(i, 21, direccion.totalpdireccion()['valor'],formatoceldacenter)
                        ws.write(i, 22, direccion.totalpejecucioncoord()['valor'],formatoceldacenter)
                        ws.write(i, 23, direccion.totalpejecucionsupervision()['valor'],formatoceldacenter)
                        ws.write(i, 24, direccion.totalpejecucion()['valor'],formatoceldacenter)
                        ws.write(i, 25, direccion.totalpejecucionapoyo()['valor'],formatoceldacenter)
                        ws.write(i, 26, direccion.totalptecnico()['valor'],formatoceldacenter)

                        # if direccion.brechaejecucioncoord()>0:


                        ws.write(i, 28, '',formatoceldacenter)
                        ws.write(i, 29, '{} {}'.format(direccion.brechaejecucioncoord()['valor'],direccion.brechaejecucioncoord()['letras']),formatoceldacenter)
                        ws.write(i, 30, '',formatoceldacenter)
                        ws.write(i, 31, '{} {}'.format(direccion.brechaejecucionsupervision()['valor'],direccion.brechaejecucionsupervision()['letras']),formatoceldacenter)
                        ws.write(i, 32, '',formatoceldacenter)
                        ws.write(i, 33, '{} {}'.format(direccion.brechaejecucion()['valor'],direccion.brechaejecucion()['letras']),formatoceldacenter)
                        ws.write(i, 34, '',formatoceldacenter)
                        ws.write(i, 35, '{} {}'.format(direccion.brechaejecucionapoyo()['valor'],direccion.brechaejecucionapoyo()['letras']),formatoceldacenter)
                        ws.write(i, 36, '',formatoceldacenter)
                        ws.write(i, 37, '{} {}'.format(direccion.brechatecnico()['valor'],direccion.brechatecnico()['letras']),formatoceldacenter)
                        ws.write(i, 38, '',formatoceldacenter)

                        i += 1

                    ws.write(i, 1, 'NÚMERO DE SERVIDORES:', formatoceldacenter)
                    ws.write(i, 2, total['anominadora'], formatoceldacenter)
                    ws.write(i, 3, total['viceministros'], formatoceldacenter)
                    ws.write(i, 4, total['subsecretarios'], formatoceldacenter)
                    ws.write(i, 5, total['coordinadores'], formatoceldacenter)
                    ws.write(i, 6, total['asesor'], formatoceldacenter)
                    ws.write(i, 7, total['coorddesp'], formatoceldacenter)
                    ws.write(i, 8, total['direccion'], formatoceldacenter)
                    ws.write(i, 9, total['ejeccord'], formatoceldacenter)
                    ws.write(i, 10, total['ejesuper'], formatoceldacenter)
                    ws.write(i, 11, total['ejecucion'], formatoceldacenter)
                    ws.write(i, 12, total['tecnologico'], formatoceldacenter)
                    ws.write(i, 13, total['apoyo'], formatoceldacenter)

                    ws.write(i, 15, total['panominadora'], formatoceldacenter)
                    ws.write(i, 16, total['pviceministros'], formatoceldacenter)
                    ws.write(i, 17, total['psubsecretarios'], formatoceldacenter)
                    ws.write(i, 18, total['pcoordinadores'], formatoceldacenter)
                    ws.write(i, 19, total['pasesor'], formatoceldacenter)
                    ws.write(i, 20, total['pcoorddesp'], formatoceldacenter)
                    ws.write(i, 21, total['pdireccion'], formatoceldacenter)
                    ws.write(i, 22, total['pejeccord'], formatoceldacenter)
                    ws.write(i, 23, total['pejesuper'], formatoceldacenter)
                    ws.write(i, 24, total['pejecucion'], formatoceldacenter)
                    ws.write(i, 25, total['ptecnologico'], formatoceldacenter)
                    ws.write(i, 26, total['papoyo'], formatoceldacenter)
                    i+=2

                    ws.merge_range(i,6,i,8, 'SITUACIÓN ACTUAL', formatoceldatitulo)
                    ws.merge_range(i+1,6,i+1,8,totalactual, formatoceldacenter)
                    ws.merge_range(i+2,6,i+2,8, brecha.totalcodtrabajo, formatoceldacenter)
                    ws.merge_range(i+3,6,i+3,8, brecha.totalregespecial, formatoceldacenter)
                    ws.merge_range(i+4,6,i+4,8, totalservactual, formatoceldatitulo)

                    ws.merge_range(i,10,i,12, 'SITUACIÓN PROPUESTA', formatoceldatitulo)
                    ws.merge_range(i+1,10,i+1,12, totalpropuesto, formatoceldacenter)
                    ws.merge_range(i+2,10,i+2,12, brecha.ptotalcodtrabajo, formatoceldacenter)
                    ws.merge_range(i+3,10,i+3,12, brecha.ptotalregespecial, formatoceldacenter)
                    ws.merge_range(i+4,10,i+4,12, totalservpropuesto, formatoceldatitulo)

                    i+=7
                    ws.merge_range(i,2,i,6, 'RESPONSABLE DE LA UATH',formatoceldasinborde)
                    ws.merge_range(i+1,2,i+1,6, str(periodo.responsable),formatoceldasinborde)
                    ws.merge_range(i+2,2,i+2,6, periodo.cargo,formatoceldasinborde)


                    ws.merge_range(i,20,i,24, 'AUTORIDAD RESPONSABLE' ,formatoceldasinborde)
                    ws.merge_range(i+1,20,i+1,24, str(periodo.autoridadresponsable),formatoceldasinborde)
                    ws.merge_range(i+2,20,i+2,24, 'RECTOR UNIVERSIDAD ESTATAL DE MILAGRO',formatoceldasinborde)

                    i+=5


                    ws.merge_range(i,2,i,13, 'ANÁLISIS DE BRECHAS POR ROL', formatoceldatitulo)
                    ws.merge_range(i+1,2,i+1,5, 'ROL', formatoceldacenter)
                    ws.merge_range(i+2,2,i+2,5, 'Nivel Jerárquico Superior', formatoceldacenter)
                    ws.merge_range(i+3,2,i+3,5, 'Ejecución y coordinación de procesos', formatoceldacenter)
                    ws.merge_range(i+4,2,i+4,5, 'Ejecución y supervisión de procesos', formatoceldacenter)
                    ws.merge_range(i+5,2,i+5,5, 'Ejecución de procesos', formatoceldacenter)
                    ws.merge_range(i+6,2,i+6,5, 'Ejecución de procesos de apoyo y tecnológico ', formatoceldacenter)
                    ws.merge_range(i+7,2,i+7,5, 'Apoyo administrativo', formatoceldacenter)
                    ws.merge_range(i+8,2,i+8,5, 'BRECHA INSTITUCIONAL GENERAL', formatoceldatitulo)

                    ws.merge_range(i+1,6,i+1,7, 'SITUACIÓN ACTUAL', formatoceldatitulo)
                    ws.merge_range(i+2,6,i+2,7, brecha.jerarquico, formatoceldacenter)
                    ws.merge_range(i+3,6,i+3,7, brecha.ejecucioncoord, formatoceldacenter)
                    ws.merge_range(i+4,6,i+4,7, brecha.ejecucionsupervision, formatoceldacenter)
                    ws.merge_range(i+5,6,i+5,7, brecha.ejecucion, formatoceldacenter)
                    ws.merge_range(i+6,6,i+6,7, brecha.ejecucionapoyo, formatoceldacenter)
                    ws.merge_range(i+7,6,i+7,7, brecha.apoyo, formatoceldacenter)
                    ws.merge_range(i+8,6,i+8,7, brecha.totalrol()['actual'], formatoceldatitulo)

                    ws.merge_range(i+1,8,i+1,9, 'SITUACIÓN PROPUESTA', formatoceldatitulo)
                    ws.merge_range(i+2,8,i+2,9, brecha.pjerarquico, formatoceldacenter)
                    ws.merge_range(i+3,8,i+3,9, brecha.pejecucioncoord, formatoceldacenter)
                    ws.merge_range(i+4,8,i+4,9, brecha.pejecucionsupervision, formatoceldacenter)
                    ws.merge_range(i+5,8,i+5,9, brecha.pejecucion, formatoceldacenter)
                    ws.merge_range(i+6,8,i+6,9, brecha.pejecucionapoyo, formatoceldacenter)
                    ws.merge_range(i+7,8,i+7,9, brecha.papoyo, formatoceldacenter)
                    ws.merge_range(i+8,8,i+8,9, brecha.totalrol()['propuesto'], formatoceldatitulo)

                    ws.merge_range(i+1,10,i+1,13, 'BRECHA', formatoceldatitulo)
                    ws.merge_range(i+2,10,i+2,11, calculabrecha(brecha.jerarquico,brecha.pjerarquico)['valor'], formatoceldacenter)
                    ws.merge_range(i+2,12,i+2,13, calculabrecha(brecha.jerarquico,brecha.pjerarquico)['letras'], formatoceldacenter)
                    ws.merge_range(i+3,10,i+3,11, calculabrecha(brecha.ejecucioncoord,brecha.pejecucioncoord)['valor'], formatoceldacenter)
                    ws.merge_range(i+3,12,i+3,13, calculabrecha(brecha.ejecucioncoord,brecha.pejecucioncoord)['letras'], formatoceldacenter)
                    ws.merge_range(i+4,10,i+4,11, calculabrecha(brecha.ejecucionsupervision,brecha.pejecucionsupervision)['valor'], formatoceldacenter)
                    ws.merge_range(i+4,12,i+4,13, calculabrecha(brecha.ejecucionsupervision,brecha.pejecucionsupervision)['letras'], formatoceldacenter)
                    ws.merge_range(i+5,10,i+5,11, calculabrecha(brecha.ejecucion,brecha.pejecucion)['valor'], formatoceldacenter)
                    ws.merge_range(i+5,12,i+5,13, calculabrecha(brecha.ejecucion,brecha.pejecucion)['letras'], formatoceldacenter)
                    ws.merge_range(i+6,10,i+6,11, calculabrecha(brecha.ejecucionapoyo,brecha.pejecucionapoyo)['valor'], formatoceldacenter)
                    ws.merge_range(i+6,12,i+6,13, calculabrecha(brecha.ejecucionapoyo,brecha.pejecucionapoyo)['letras'], formatoceldacenter)
                    ws.merge_range(i+7,10,i+7,11, calculabrecha(brecha.apoyo,brecha.papoyo)['valor'], formatoceldacenter)
                    ws.merge_range(i+7,12,i+7,13, calculabrecha(brecha.apoyo,brecha.papoyo)['letras'], formatoceldacenter)
                    ws.merge_range(i+8,10,i+8,11, brecha.totalrol()['brecha'], formatoceldatitulo)
                    ws.merge_range(i+8,12,i+8,13, brecha.totalrol()['palabras'], formatoceldatitulo)

                    ws.merge_range(i,15,i,26, 'ANÁLISIS DE BRECHAS POR PROCESO', formatoceldatitulo)
                    ws.merge_range(i+1,15,i+1,18, 'PROCESO', formatoceldatitulo)
                    ws.merge_range(i+2,15,i+2,18, 'Gobernante', formatoceldacenter)
                    ws.merge_range(i+3,15,i+3,18, 'Sustantivo', formatoceldacenter)
                    ws.merge_range(i+4,15,i+4,18, 'Adjetivo', formatoceldacenter)
                    ws.merge_range(i+5,15,i+5,18, 'BRECHA INSTITUCIONAL', formatoceldatitulo)

                    ws.merge_range(i+1,19,i+1,20, 'SITUACIÓN ACTUAL', formatoceldatitulo)
                    ws.merge_range(i+2,19,i+2,20, brecha.gobernante, formatoceldacenter)
                    ws.merge_range(i+3,19,i+3,20, brecha.sustantivo, formatoceldacenter)
                    ws.merge_range(i+4,19,i+4,20, brecha.adjetivo, formatoceldacenter)
                    ws.merge_range(i+5,19,i+5,20, brecha.totalproceso()['actual'], formatoceldatitulo)
                    ws.merge_range(i+1,21,i+1,22, 'SITUACIÓN PROPUESTA', formatoceldatitulo)
                    ws.merge_range(i+2,21,i+2,22, brecha.pgobernante, formatoceldacenter)
                    ws.merge_range(i+3,21,i+3,22, brecha.psustantivo, formatoceldacenter)
                    ws.merge_range(i+4,21,i+4,22, brecha.padjetivo, formatoceldacenter)
                    ws.merge_range(i+5,21,i+5,22, brecha.totalproceso()['propuesto'], formatoceldatitulo)


                    ws.merge_range(i+1,23,i+1,26, 'BRECHA', formatoceldatitulo)
                    ws.merge_range(i+2,23,i+2,24, calculabrecha(brecha.gobernante,brecha.pgobernante)['valor'], formatoceldacenter)
                    ws.merge_range(i+2,25,i+2,26, calculabrecha(brecha.gobernante,brecha.pgobernante)['letras'], formatoceldacenter)
                    ws.merge_range(i+3,23,i+3,24, calculabrecha(brecha.sustantivo,brecha.psustantivo)['valor'], formatoceldacenter)
                    ws.merge_range(i+3,25,i+3,26, calculabrecha(brecha.sustantivo,brecha.psustantivo)['letras'], formatoceldacenter)
                    ws.merge_range(i+4,23,i+4,24, calculabrecha(brecha.adjetivo,brecha.padjetivo)['valor'], formatoceldacenter)
                    ws.merge_range(i+4,25,i+4,26, calculabrecha(brecha.adjetivo,brecha.padjetivo)['letras'], formatoceldacenter)
                    ws.merge_range(i+5,23,i+5,24,brecha.totalproceso()['brecha'] , formatoceldatitulo)
                    ws.merge_range(i+5,25,i+5,26,brecha.totalproceso()['palabras'] , formatoceldatitulo)



                    workbook.close()
                    output.seek(0)
                    filename = 'plantilla' + random.randint(1,10000).__str__() + '.xlsx'
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename


                    return response
                except Exception as ex:
                    pass

            elif action == 'copiarunidad':
                try:
                    data['periodo'] = periodo = PeriodoPlanificacionTH.objects.get(pk=encrypt_id(request.GET['id']))
                    form = CopiarUnidadForm()
                    form.fields['periodo'].queryset = PeriodoPlanificacionTH.objects.filter(status=True).exclude(pk=periodo.id)
                    form.fields['unidad'].queryset = CabPlanificacionTH.objects.none()
                    data['form'] = form
                    data['id'] = periodo.id
                    template = get_template("th_dir_planificacion/modal/formcopiarunidad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': f'Error: {ex}'})

            elif action == 'cargarunidades':
                try:
                    lista = []
                    p_recepta = PeriodoPlanificacionTH.objects.get(pk=int(request.GET['args']))
                    p_envia = PeriodoPlanificacionTH.objects.get(pk=int(request.GET['id']))
                    departamentos = list(CabPlanificacionTH.objects.filter(periodo=p_recepta, status=True).values_list('departamento_id', flat=True))
                    unidades = CabPlanificacionTH.objects.filter(status=True, periodo=p_envia).exclude(departamento_id__in=departamentos)
                    for u in unidades:
                        text = str(u.departamento) + ' | ' + str(len(u.gestiones_producto())) + ' Gestiones'
                        lista.append({'value': u.id, 'text': text})
                    return JsonResponse({'result': True, 'data': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'movergestiones':
                try:
                    data['unidad_envia'] = unidad = CabPlanificacionTH.objects.get(id=encrypt_id(request.GET['id']))
                    data['unidades'] = CabPlanificacionTH.objects.filter(status=True, periodo=unidad.periodo).exclude(id=unidad.id)
                    data['id'] = unidad.id
                    template = get_template("th_dir_planificacion/modal/formmovergestiones.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': f'Error: {ex}'})

            elif action == 'addproducto':
                try:
                    data['gestion_planificacion'] = gestionplanificacion = GestionPlanificacionTH.objects.get(id=encrypt_id(request.GET['id']))
                    ids_excluir = list(gestionplanificacion.gestion_productos().values_list('producto_id', flat=True))
                    data['productos'] = ProductoServicioSeccion.objects.filter(seccion=gestionplanificacion.gestion).exclude(producto_id__in=ids_excluir)
                    data['id'] = gestionplanificacion.id
                    template = get_template("th_dir_planificacion/modal/formproducto.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': f'Error: {ex}'})

            elif action == 'importaractividades':
                try:
                    form = ImportarActividadesForm()
                    form.fields['unidad'].queryset = CabPlanificacionTH.objects.none()
                    form.fields['gestion'].queryset = GestionPlanificacionTH.objects.none()
                    form.fields['producto'].queryset = GestionProductoServicioTH.objects.none()
                    data['form'] = form
                    data['gestionproducto'] = GestionProductoServicioTH.objects.get(id=encrypt_id(request.GET['id']))
                    data['id'] = encrypt_id(request.GET['id'])
                    data['seccionado'] = True
                    template = get_template("th_dir_planificacion/modal/formimportaractividades.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': f'Error: {ex}'})

            elif action == 'cargarunidades_all':
                try:
                    lista = []
                    p_envia = PeriodoPlanificacionTH.objects.get(pk=int(request.GET['id']))
                    unidades = CabPlanificacionTH.objects.filter(status=True, periodo=p_envia)
                    for u in unidades:
                        text = str(u.departamento)
                        lista.append({'value': u.id, 'text': text})
                    return JsonResponse({'result': True, 'data': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cargargestiones':
                try:
                    lista = []
                    cabecera = CabPlanificacionTH.objects.get(pk=int(request.GET['id']))
                    gestiones = GestionPlanificacionTH.objects.filter(status=True, cabecera=cabecera)
                    for g in gestiones:
                        text = str(g.gestion)
                        lista.append({'value': g.id, 'text': text})
                    return JsonResponse({'result': True, 'data': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cargarproductos':
                try:
                    lista = []
                    gestion = GestionPlanificacionTH.objects.get(pk=int(request.GET['id']))
                    productos = GestionProductoServicioTH.objects.filter(status=True, gestion=gestion)
                    for p in productos:
                        text = str(p.producto)
                        lista.append({'value': p.id, 'text': text})
                    return JsonResponse({'result': True, 'data': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cargaractividades':
                try:
                    lista = []
                    gestion = GestionProductoServicioTH.objects.get(pk=int(request.GET['value']))
                    actividades = gestion.actividades()
                    for a in actividades:
                        text = str(a.actividad)
                        lista.append({'value': a.id, 'text': text})
                    return JsonResponse({'result': True, 'data': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Plantillas de Talento Humano'
                search = None
                tipo = None
                if 's' in request.GET:
                    search = request.GET['s']
                if search:
                    periodos = PeriodoPlanificacionTH.objects.filter(status=True)
                else:
                    periodos = PeriodoPlanificacionTH.objects.filter(status=True)
                paging = MiPaginador(periodos, 21)
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
                data['periodos'] = page.object_list
                return render(request, "th_dir_planificacion/view.html", data)
            except Exception as ex:
                pass
