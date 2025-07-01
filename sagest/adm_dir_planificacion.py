# -*- coding: UTF-8 -*-
import io
import math
import sys
from datetime import datetime
from datetime import timedelta
from datetime import date
from dateutil.relativedelta import relativedelta
import random
import xlsxwriter
from urllib.request import urlopen
from django.forms import model_to_dict

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template


from decorators import secure_module
from sagest.forms import CabPlanificacionTHForm, PeriodoPlanificacionTHForm, CambiarEstadoDepartamentoForm, \
    CambiarEstadoGestionPlanificacionTHForm, MoverGestionForm, ResponsableGestionForm
from sagest.models import CabPlanificacionTH, SeccionDepartamento, ProductoServicioSeccion, TIPO_ACTIVIDAD_TH, \
    FRECUENCIA_TH, ActividadSecuencialTH, PeriodoPlanificacionTH, ReporteBrechasTH, Departamento, \
    GestionPlanificacionTH, HistorialGestionPlanificacionTH, HistorialCabPlanificacionTH, ReporteBrechasPeriodoTH, \
    DistributivoPersona, GestionProductoServicioTH, ProductoServicioTh
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log
from sga.models import MONTH_NAMES, PersonaDatosFamiliares, Persona


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
#@secure_module



def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data['puede_gestionar_plantilla'] = puede_gestionar_plantilla = request.user.has_perm('sagest.puede_gestionar_plantilla')
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = CabPlanificacionTHForm(request.POST)
                periodo = PeriodoPlanificacionTH.objects.get(pk=request.POST['id'])
                if f.is_valid():
                    if persona.departamentodireccion():
                        departamento = persona.departamentodireccion()
                        if CabPlanificacionTH.objects.filter(periodo=periodo, departamento=departamento,status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"El registro ya existe."})
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
                        return JsonResponse({"result": "bad","mensaje": u"Usted no es responsable de una dirección."})

                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

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

        if action == 'edit':
            try:
                f = CabPlanificacionTHForm(request.POST)
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
                actividad = ActividadSecuencialTH(producto=servicio,servicios=servicio.producto,gestion=gestion)
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
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

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
                cabecera = CabPlanificacionTH.objects.get(pk=request.POST['id'])
                observacion = (request.POST['obser']).upper()
                estado = request.POST['estado']
                cabecera.estado = estado
                historial=HistorialCabPlanificacionTH(cabecera=cabecera,estado=estado,motivo=observacion)
                historial.save()
                cabecera.save()
                # if not cabecera.responsable:
                #     departamento = Departamento.obj


                log(u'Cambió de estado cabecera %s' %cabecera , request, "edit")
                return JsonResponse({"result": "ok"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        # if action == 'aprobaruath':
        #     try:
        #         gestion = GestionPlanificacionTH.objects.get(pk=request.POST['idg'])
        #         observacion = (request.POST['obser']).upper()
        #         estado = request.POST['estado']
        #         gestion.estado = estado
        #         historial=HistorialGestionPlanificacionTH(gestion=gestion,estado=estado,motivo=observacion)
        #         historial.save()
        #         gestion.save()
        #         log(u'Cambió de estado' , request, "edit")
        #         return JsonResponse({"result": "ok"})
        #
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'actualizaresponsables':
            try:
                periodo = PeriodoPlanificacionTH.objects.get(pk=request.POST['idp'])
                direcciones = CabPlanificacionTH.objects.filter(status=True,periodo=periodo)
                for dir in direcciones:
                    gestiones = GestionPlanificacionTH.objects.filter(status=True, cabecera=dir)
                    for gest in gestiones:
                        gest.responsable = gest.gestion.responsable
                        gest.responsablesubrogante = gest.gestion.responsablesubrogante
                        gest.save()
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
                    filtro.responsable_id = f.cleaned_data['responsable']
                    filtro.responsablesubrogante_id = f.cleaned_data['subrogante']
                    filtro.save(request)
                    log(u'Cambio responsable de gestión: %s' % filtro, request, "change")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
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


                    for prod in filtro.actividades():
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




        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Dirección'
                    data['filtro'] = PeriodoPlanificacionTH.objects.get(pk=request.GET['id'])
                    data['form'] = CabPlanificacionTHForm()
                    template = get_template("adm_dir_planificacion/modal/formadireccion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            if action == 'addgestion':
                try:
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
                    data['filtro'] = cabecera = CabPlanificacionTH.objects.get(pk=request.GET['id'])
                    form = CabPlanificacionTHForm(initial={'fecha': cabecera.fecha,
                                                  'nivelterritorial' : cabecera.nivelterritorial,
                                                  'tipoproceso' : cabecera.tipoproceso})
                    data['form'] = form
                    template = get_template("adm_dir_planificacion/modal/formadireccion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            if action == 'delgestion':
                try:
                    data['title'] = u'Eliminar Gestión'
                    data['gestion'] = GestionPlanificacionTH.objects.get(pk=request.GET['id'])
                    return render(request, 'th_dir_planificacion/delgestion.html', data)
                except Exception as ex:
                    pass

            if action == 'deldepa':
                try:
                    data['title'] = u'Eliminar Dirección'
                    data['cabecera'] = CabPlanificacionTH.objects.get(pk=request.GET['id'])
                    return render(request, 'th_dir_planificacion/deldepa.html', data)
                except Exception as ex:
                    pass

            if action == 'gestionar':
                try:
                    data['title'] = u'Plantillas'
                    data['gestion'] = gestion = GestionPlanificacionTH.objects.get(pk=request.GET['id'])
                    gestiones = GestionProductoServicioTH.objects.filter(status=True,gestion=gestion)
                    data['gestiones'] = gestiones
                    data['tipoactividad_list'] = TIPO_ACTIVIDAD_TH
                    data['frecuencia_list'] = FRECUENCIA_TH
                    if gestion.estado == 1 or gestion.estado == 6 or gestion.estado == 7:
                        return render(request, "adm_dir_planificacion/viewgestionar.html", data)
                    else:
                        return render(request, "adm_dir_planificacion/viewgestionarbloq.html", data)

                except Exception as ex:
                    pass

            if action == 'verproceso':
                try:
                    data['title'] = u'Ver Historial'
                    data['filtro'] = filtro = GestionPlanificacionTH.objects.get(pk=int(request.GET['id']))
                    data['detalle'] = HistorialGestionPlanificacionTH.objects.filter(status=True, gestion=filtro).order_by('pk')
                    template = get_template("adm_dir_planificacion/modal/verhistorial.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'midepa':
                try:
                    data['periodo'] =  periodo = PeriodoPlanificacionTH.objects.get(pk=int(request.GET['idp']))
                    data['title'] = u'Departamento'
                    search = None
                    if persona.es_directordepartamental():
                        cab = CabPlanificacionTH.objects.filter(status=True,periodo=periodo,departamento=persona.departamentodireccion()).order_by('id')
                    else:
                        secciones = GestionPlanificacionTH.objects.filter((Q(responsable=persona)|Q(responsablesubrogante=persona)
                                                                          |Q(gestion__responsablesubrogante=persona)),status=True).values_list('cabecera_id', flat=True)
                        cab = CabPlanificacionTH.objects.filter(status=True,periodo=periodo,id__in=secciones).order_by('id')

                    paging = MiPaginador(cab, 50)
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
                    data['cabeceras'] = page.object_list
                    return render(request, "adm_dir_planificacion/viewdepa.html", data)
                except Exception as ex:
                    pass

            if action == 'migestion':
                try:
                    data['cabecera'] =  cabecera = CabPlanificacionTH.objects.get(pk=int(request.GET['idp']))
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
                    return render(request, "adm_dir_planificacion/viewgestion.html", data)
                except Exception as ex:
                    pass

            if action == 'brecha':
                try:
                    brecha = []
                    data['gestion'] =  gestion = GestionPlanificacionTH.objects.get(pk=int(request.GET['id']))
                    data['actividades'] = actividades = ActividadSecuencialTH.objects.filter(gestion=gestion,status=True)
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
                        return render(request, "adm_dir_planificacion/viewbrechas.html", data)
                    else:
                        return render(request, "adm_dir_planificacion/viewbrechasprot.html", data)
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
                    data['title'] = gestion.gestion
                    return render(request, "adm_dir_planificacion/viewbrechasgob.html", data)
                except Exception as ex:
                    pass

            if action == 'brechadepa':
                try:
                    brecha = []
                    data['cabecera'] = cabecera = CabPlanificacionTH.objects.get(pk=int(request.GET['idp']))
                    data['brechas'] =  brechas = ReporteBrechasTH.objects.filter(status=True,gestion__cabecera=cabecera,gestion__status=True).distinct()
                    data['title'] = u'REPORTE DE BRECHAS DE %s' % cabecera.departamento.nombre
                    return render(request, "adm_dir_planificacion/viewbrechasdepa.html", data)
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
                    return render(request, "adm_dir_planificacion/viewmatrizconsolidada.html", data)
                except Exception as ex:
                    pass

            #Reportes
            elif action == 'descargaplantilla':
                try:
                    gestion = GestionPlanificacionTH.objects.get(pk=request.GET['idg'])
                    brecha = ReporteBrechasTH.objects.get(status=True,gestion=gestion)
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

                    productos = ProductoServicioSeccion.objects.filter(status=True, seccion=gestion.gestion)
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
                    data['action'] = 'cambiarEstadoDepartamento'
                    data['filtro'] = filtro = CabPlanificacionTH.objects.get(pk=request.GET['id'])
                    form =CambiarEstadoDepartamentoForm(initial =model_to_dict(filtro))
                    data['form2'] = form

                    template = get_template("adm_dir_planificacion/modal/formestadodepartamento.html")
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
                return render(request, "adm_dir_planificacion/view.html", data)
            except Exception as ex:
                pass
