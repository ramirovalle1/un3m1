# -*- coding: UTF-8 -*-
import io
import json
import random
import math
import sys
from datetime import datetime
from urllib.request import urlopen

import xlsxwriter
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
import xlwt
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import Context
from django.template.loader import get_template
from xlwt import *
from django.shortcuts import render
from decorators import secure_module
from sagest.forms import PeriodoPerfilPuestoForm, MantenimientoNombreForm, CompetenciaLaboralForm, \
    DetalleCompetenciaLaboralForm, PerfilPuestoForm, DuplicarPeriodoPerfilPuestoForm
from sagest.models import PeriodoPerfilPuesto, TipoCompetenciaLaboral, CompetenciaLaboral, DetalleCompetenciaLaboral, \
    Departamento, DireccionPerfilPuesto, PerfilPuestoTh, DenominacionPuesto, DenominacionPerfilPuesto, EscalaSalarial, \
    ActividadesEsencialesPerfilPuesto, AreaConocimientoPerfilPuesto, CompetenciasPerfilPuesto, PuestoDenominacion, \
    SeccionDepartamento
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log


@login_required(redirect_field_name='ret', login_url='/loginsagest')
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addperiodo':
            try:
                f = PeriodoPerfilPuestoForm(request.POST)
                if f.is_valid():
                    if PeriodoPerfilPuesto.objects.filter(status=True, anio=f.cleaned_data['anio']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"ESTE PERIODO YA EXISTE!"})
                    else:
                        periodo = PeriodoPerfilPuesto(descripcion=f.cleaned_data['descripcion'],
                                                      anio=f.cleaned_data['anio'],
                                                      activo=f.cleaned_data['activo'],
                                                      fechafin=f.cleaned_data['fechafin'])
                        periodo.save(request)
                        log(u'Adicionó nuevo periodo en  perfil de puesto: %s' % periodo, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        elif action =='cambiarEstado':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "vacio"})
                if request.POST['dato'] == '':
                    return JsonResponse({"result": "vacio"})
                dato = request.POST['dato']
                periodo = PeriodoPerfilPuesto.objects.get(id=int(request.POST['id']))
                if dato == '1':
                    periodo.activo =True
                if dato == '0':
                    periodo.activo = False
                periodo.save()


                log(u'Cambio el estado al periodo de perfil puesto: %s' % periodo, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. ({})".format(ex)})

        elif action == 'editperiodo':
            try:
                periodo = PeriodoPerfilPuesto.objects.get(id=int(request.POST['id']))
                f = PeriodoPerfilPuestoForm(request.POST)
                if f.is_valid():
                    if PeriodoPerfilPuesto.objects.filter(status=True, anio=f.cleaned_data['anio']).exclude(
                            id=periodo.pk).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"ESTE PERIODO YA EXISTE!"})
                    else:
                        periodo.descripcion = f.cleaned_data['descripcion']
                        periodo.anio = f.cleaned_data['anio']
                        periodo.activo = f.cleaned_data['activo']
                        periodo.fechafin = f.cleaned_data['fechafin']
                        periodo.save(request)
                        log(u'Edito un periodo en  perfil de puesto: %s' % periodo, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})
        # elif action == 'editperiodo':
        #     try:
        #         id = request.POST['id']
        #         f = PeriodoPerfilPuestoForm(request.POST)
        #         if f.is_valid():
        #             nivel = PeriodoPerfilPuesto.objects.get(id=id)
        #             if PeriodoPerfilPuesto.objects.filter(Q(status=True), Q(nivel=f.cleaned_data['nivel']) | Q(descripcion=f.cleaned_data['descripcion'])).exclude(id=nivel.id).exists():
        #                 return JsonResponse({"result": "bad", "mensaje": u"ESTE NIVEL YA EXISTE!"})
        #             else:
        #                 nivel.descripcion = f.cleaned_data['descripcion']
        #                 nivel.nivel = f.cleaned_data['nivel']
        #                 nivel.save(request)
        #                 log(u'Edito un nivel: %s' % nivel.descripcion, request, "edit")
        #                 return JsonResponse({"result": False}, safe=False)
        #         else:
        #             raise NameError('Error')
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})
        elif action == 'delperiodo':
            try:
                data['id'] = id = request.POST['id']
                data['tipo'] = tipo = PeriodoPerfilPuesto.objects.get(id=int(id))
                if tipo.en_uso():
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"No se puede eliminar porque este periodo está en uso"})
                tipo.status = False
                tipo.save(request)
                log(u'Elimino periodo en perfil de puesto : %s' % tipo, request, "del")
                return JsonResponse({"result": 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})
        # elif action == 'delperiodo':
        #     nivel = PeriodoPerfilPuesto.objects.get(id=int(request.POST['id']))
        #     nivel.status = False
        #     nivel.save(request)
        #     log(u'Elimino un nivel: %s' % nivel, request, "del")
        #     return JsonResponse({"result": False}, safe=False)
        elif action == 'addtipo':
            try:
                f = MantenimientoNombreForm(request.POST)
                if f.is_valid():
                    if TipoCompetenciaLaboral.objects.filter(status=True,
                                                             nombre=f.cleaned_data['nombre'].upper().strip()).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"ESTE TIPO YA EXISTE!"})
                    else:
                        tipo = TipoCompetenciaLaboral(nombre=f.cleaned_data['nombre'])
                        tipo.save(request)
                        log(u'Adicionó nuevo tipo : %s' % tipo, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})
        elif action == 'edittipo':
            try:
                data['id'] = id = request.POST['id']
                data['action'] = action
                data['tipo'] = tipo = TipoCompetenciaLaboral.objects.get(id=id)
                f = MantenimientoNombreForm(request.POST)
                if f.is_valid():
                    if TipoCompetenciaLaboral.objects.filter(status=True,
                                                             nombre=f.cleaned_data['nombre'].upper().strip()).exclude(
                            id=id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"ESTE TIPO YA EXISTE!"})
                    else:
                        tipo.nombre = f.cleaned_data['nombre']
                        tipo.save(request)
                        log(u'Edito tipo : %s' % tipo, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})
        elif action == 'eliminartipo':
            try:
                data['id'] = id = request.POST['id']
                data['tipo'] = tipo = TipoCompetenciaLaboral.objects.get(id=int(id))
                if tipo.en_uso():
                    return JsonResponse(
                        {"result": "bad",
                         "mensaje": u"No se puede eliminar porque este tipo de competencia está en uso"})
                tipo.status = False
                tipo.save(request)
                log(u'Elimino competencia : %s' % tipo, request, "add")
                return JsonResponse({"result": 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})
        elif action == 'addcompetencia':
            try:
                f = CompetenciaLaboralForm(request.POST)
                if f.is_valid():
                    if CompetenciaLaboral.objects.filter(status=True, numero=f.cleaned_data['numero'],
                                                         denominacion=f.cleaned_data['denominacion'].upper().strip(),
                                                         definicion=f.cleaned_data['definicion'],
                                                         tipo=f.cleaned_data['tipo']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"ESTA COMPETENCIA YA EXISTE!"})
                    else:
                        competencia = CompetenciaLaboral(
                            numero=f.cleaned_data['numero'],
                            denominacion=f.cleaned_data['denominacion'],
                            definicion=f.cleaned_data['definicion'],
                            tipo=f.cleaned_data['tipo'])
                        competencia.save(request)
                        log(u'Adicionó competencia : %s' % competencia, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})
        elif action == 'editcompetencia':
            try:
                data['id'] = id = request.GET['id']
                data['competencia'] = competencia = CompetenciaLaboral.objects.get(id=int(id))
                if competencia.en_uso():
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"No se puede editar porque esta comptencia esta en uso"})
                f = CompetenciaLaboralForm(request.POST)
                if f.is_valid():
                    if CompetenciaLaboral.objects.filter(status=True, numero=f.cleaned_data['numero'],
                                                         denominacion=f.cleaned_data['denominacion'].upper().strip(),
                                                         definicion=f.cleaned_data['definicion'],
                                                         tipo=f.cleaned_data['tipo']).exclude(
                        id=competencia.pk).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"ESTA COMPETENCIA YA EXISTE!"})
                    else:
                        competencia.numero = f.cleaned_data['numero']
                        competencia.denominacion = f.cleaned_data['denominacion']
                        competencia.definicion = f.cleaned_data['definicion']
                        competencia.tipo = f.cleaned_data['tipo']
                        competencia.save(request)
                        log(u'Edito competencia : %s' % competencia, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})
        elif action == 'eliminarcompetencia':
            try:
                data['id'] = id = request.POST['id']
                data['competencia'] = competencia = CompetenciaLaboral.objects.get(id=int(id))
                if competencia.en_uso():
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"No se puede eliminar porque esta comptencia esta en uso"})
                competencia.status = False
                competencia.save(request)
                log(u'Elimino competencia : %s' % competencia, request, "add")
                return JsonResponse({"result": 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})
        elif action == 'adddetallecompetencia':
            try:
                f = DetalleCompetenciaLaboralForm(request.POST)

                if f.is_valid():
                    if DetalleCompetenciaLaboral.objects.filter(status=True,
                                                                comportamiento=f.cleaned_data[
                                                                    'comportamiento'].upper().strip(),
                                                                competencia_id=request.POST['id'],
                                                                numero=f.cleaned_data['numero'],
                                                                nivel=f.cleaned_data['nivel']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"ESTE DETALLE YA EXISTE!"})
                    else:
                        competencia = DetalleCompetenciaLaboral(
                            competencia_id=request.POST['id'],
                            numero=f.cleaned_data['numero'],
                            comportamiento=f.cleaned_data['comportamiento'],
                            nivel=f.cleaned_data['nivel'])
                        competencia.save(request)
                        log(u'Adicionó detalle competencia : %s' % (competencia,), request, "add")
                        return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})
        elif action == 'editdetallecompetencia':
            try:
                data['id'] = id = request.POST['id']
                data['detalle'] = competencia = DetalleCompetenciaLaboral.objects.get(id=id)
                if competencia.competencia.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": u"Esta detalle esta en uso"})
                f = DetalleCompetenciaLaboralForm(request.POST)

                if f.is_valid():
                    if DetalleCompetenciaLaboral.objects.filter(status=True,
                                                                comportamiento=f.cleaned_data[
                                                                    'comportamiento'].upper().strip(),
                                                                competencia_id=request.POST['id'],
                                                                numero=f.cleaned_data['numero'],
                                                                nivel=f.cleaned_data['nivel']).exclude(id=id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"ESTE DETALLE YA EXISTE!"})
                    else:
                        competencia.numero = f.cleaned_data['numero']
                        competencia.comportamiento = f.cleaned_data['comportamiento']
                        competencia.nivel = f.cleaned_data['nivel']
                        competencia.save(request)
                        log(u'Edito detalle competencia : %s' % (competencia,), request, "add")
                        return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})
        elif action == 'eliminardetallecompetencia':
            try:
                data['id'] = id = request.POST['id']
                data['detalle'] = competencia = DetalleCompetenciaLaboral.objects.get(id=id)
                if competencia.competencia.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": u"Esta detalle esta en uso"})
                competencia.status = False
                competencia.save(request)
                log(u'Elimino detalle competencia : %s' % (competencia,), request, "add")
                return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})
        elif action == 'adddirecion':
            try:
                periodo = request.POST['periodo']
                direccion = int(request.POST['id'])
                if not DireccionPerfilPuesto.objects.filter(status=True, direccion_id=direccion,periodo_id=periodo).exists():
                    dir = DireccionPerfilPuesto(periodo_id=periodo, direccion_id=direccion)
                    dir.save(request)
                    log(u'Adicionó direccion  a perfil puesto : %s' % dir, request, "add")
                    return JsonResponse({"result": True}, safe=False)

            except Exception as e:
                return JsonResponse({"result": False, "message": str(e)}, safe=False)

        elif action == 'eliminarperfil':
            try:
                id = request.POST['id']
                if PerfilPuestoTh.objects.values('id').filter(status=True,pk =id).exists():
                    perfil = PerfilPuestoTh.objects.get(status=True,pk =id)
                    perfil.status = False
                    perfil.save()
                    log(u'Elimno direccion  a perfil puesto : %s' % perfil, request, "del")
                    return JsonResponse({"result": True}, safe=False)
                return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar"})
            except Exception as e:
                transaction.set_rollback(True)
                return JsonResponse({"result": False}, safe=False)
        elif action == 'deletedirecion':
            try:
                periodo = request.POST['periodo']
                direccion = request.POST['id']
                if DireccionPerfilPuesto.objects.filter(status=True, direccion_id=direccion,
                                                        periodo_id=periodo).exists():
                    dir = DireccionPerfilPuesto.objects.get(status=True, direccion_id=direccion, periodo_id=periodo)
                    if dir.en_uso():
                        return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar porque esta en uso"})
                    dir.status = False
                    dir.save(request)
                    log(u'Elimno direccion  a perfil puesto : %s' % dir, request, "del")
                    return JsonResponse({"result": True}, safe=False)

            except Exception as e:
                return JsonResponse({"result": False}, safe=False)
        elif action == 'addperfil':
            try:
                actividadensencial = json.loads(request.POST['lista_items1'])
                competenciatecnica = json.loads(request.POST['lista_items2'])
                competenconductual = json.loads(request.POST['lista_items3'])
                areaconocimiento = json.loads(request.POST['lista_items4'])
                f = PerfilPuestoForm(request.POST)
                if f.is_valid():
                    perfil = PerfilPuestoTh(codigo=f.cleaned_data['codigo'],
                                            #denominacionpuesto=f.cleaned_data['denominacionpuesto'],
                                            denominacionperfil=f.cleaned_data['denominacionperfil'],
                                            secciondepartamento_id=int(request.POST['seccion']),
                                            nivel=f.cleaned_data['nivel'],
                                            direccion=f.cleaned_data['direccion'],
                                            escala=f.cleaned_data['escala'],
                                            mision=f.cleaned_data['mision'],
                                            especificidadexperiencia=f.cleaned_data['especificidadexperiencia'],
                                            interfaz=f.cleaned_data['interfaz'],
                                            capacitacionrequerida=f.cleaned_data['capacitacionrequerida'],
                                            notaextra=f.cleaned_data['notaextra'])
                    perfil.save(request)
                    for a in actividadensencial:
                        actividad = ActividadesEsencialesPerfilPuesto(perfilpuesto=perfil,
                                                                      actividad=a['actividadensencial'],
                                                                      conocimientoadicional=a['conocimientoadicional'])
                        actividad.save(request)
                    for area in areaconocimiento:
                        areac = AreaConocimientoPerfilPuesto(perfil=perfil, areaconocimiento_id=int(area))
                        areac.save(request)
                    for ctec in competenciatecnica:
                        competenciamodel = DetalleCompetenciaLaboral.objects.get(status=True,numero=int(ctec),competencia__tipo__id=1)
                        comp = CompetenciasPerfilPuesto(perfil=perfil, competencia=competenciamodel)
                        comp.save(request)
                    for cct in competenconductual:
                        competenciamodel = DetalleCompetenciaLaboral.objects.get(status=True,numero=int(cct),competencia__tipo__id=2)
                        comp = CompetenciasPerfilPuesto(perfil=perfil, competencia=competenciamodel)
                        comp.save(request)
                    return JsonResponse({"result": 'ok'})
                else:
                    # print(f.errors)
                    transaction.set_rollback(True)
                    return JsonResponse({"result": 'bad', 'mensaje': u'Error al guardar los datos'})
            except Exception as e:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', 'mensaje': u'Error en la transaccion ' + str(e)}, safe=False)
        elif action == 'editperfil':
            try:
                actividadensencial = json.loads(request.POST['lista_items1'])
                competenciatecnica = json.loads(request.POST['lista_items2'])
                competenconductual = json.loads(request.POST['lista_items3'])
                areaconocimiento = json.loads(request.POST['lista_items4'])
                perfil = PerfilPuestoTh.objects.get(id=int(request.POST['id']))
                f = PerfilPuestoForm(request.POST)
                if f.is_valid():
                    if PerfilPuestoTh.objects.filter(Q(status=True), Q(codigo=f.cleaned_data['codigo']), Q(direccion=f.cleaned_data['direccion'])).exclude(id=perfil.pk).exists():
                        return JsonResponse({"result": 'bad', 'mensaje': u'Ya Existe un perfil igual en este periodo y direccion'})
                    #perfil.denominacionpuesto = f.cleaned_data['denominacionpuesto']
                    perfil.codigo = f.cleaned_data['codigo']
                    perfil.denominacionperfil = f.cleaned_data['denominacionperfil']
                    perfil.nivel = f.cleaned_data['nivel']
                    perfil.direccion = f.cleaned_data['direccion']
                    perfil.escala = f.cleaned_data['escala']
                    perfil.mision = f.cleaned_data['mision']
                    perfil.especificidadexperiencia = f.cleaned_data['especificidadexperiencia']
                    perfil.interfaz = f.cleaned_data['interfaz']
                    perfil.capacitacionrequerida = f.cleaned_data['capacitacionrequerida']
                    perfil.notaextra = f.cleaned_data['notaextra']
                    perfil.save(request)
                    perfil.areaconocimientoperfilpuesto_set.all().delete()
                    for a in actividadensencial:
                        if a['id'] !='':
                            actividad = ActividadesEsencialesPerfilPuesto.objects.get(status=True,id =int(a['id']))
                            actividad.actividad = a['actividadensencial']
                            actividad.conocimientoadicional = a['conocimientoadicional']
                        else:
                            actividad = ActividadesEsencialesPerfilPuesto(perfilpuesto=perfil,
                                                                          actividad=a['actividadensencial'],
                                                                          conocimientoadicional=a['conocimientoadicional'])
                        actividad.save(request)
                    for area in areaconocimiento:
                        areac = AreaConocimientoPerfilPuesto(perfil=perfil, areaconocimiento_id=int(area))
                        areac.save(request)
                    for ctec in competenciatecnica:
                        if ctec['id'] !='0':
                            competenciamodel = DetalleCompetenciaLaboral.objects.get(status=True,numero=int(ctec['nombre']),competencia__tipo__id=1)
                            comp = CompetenciasPerfilPuesto.objects.get(status=True,id = int(ctec['id']))
                            comp.competencia = competenciamodel
                        else:
                            competenciamodel = DetalleCompetenciaLaboral.objects.get(status=True,numero=int(ctec['nombre']), competencia__tipo__id=1)
                            comp = CompetenciasPerfilPuesto(perfil=perfil, competencia=competenciamodel)
                        comp.save(request)
                    for cct in competenconductual:
                        if cct['id'] != '0':
                            competenciamodel = DetalleCompetenciaLaboral.objects.get(status=True,numero=int(cct['nombre']),competencia__tipo__id=2)
                            comp = CompetenciasPerfilPuesto.objects.get(status=True,id = int(cct['id']))
                            comp.competencia = competenciamodel
                        else:
                            competenciamodel = DetalleCompetenciaLaboral.objects.get(status=True,numero=int(cct['nombre']), competencia__tipo__id=2)
                            comp = CompetenciasPerfilPuesto( perfil=perfil, competencia=competenciamodel)
                        comp.save(request)
                    return JsonResponse({"result": 'ok'})
                else:
                    print(f.errors)
                    transaction.set_rollback(True)
                    return JsonResponse({"result": 'bad', 'mensaje': u'Error al guardar los datos'})
            except Exception as e:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', 'mensaje': u'Error en la transaccion ' + str(e)}, safe=False)
        elif action == 'duplicar':
            try:
                duplicar = duplicar_periodo(request, request.POST['descripcion'], request.POST['fechafin'],
                                            request.POST['periodopk'])
                if duplicar['resp']:
                    return JsonResponse({"result": 'ok'})
                return JsonResponse({"result": "bad", "mensaje": str(duplicar['mensaje'])})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": str(ex)})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            # PERIODO DE PERFIL DE PUESTO
            if action == 'addperiodo':
                try:
                    data['form2'] = PeriodoPerfilPuestoForm()
                    template = get_template("th_perfilpuesto/modal/formadicionarperiodo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
            if action == 'editperiodo':
                try:
                    periodo = PeriodoPerfilPuesto.objects.get(id=int(request.GET['id']))
                    data['id'] = id = periodo.pk
                    data['action'] = action
                    data['form2'] = form2 = PeriodoPerfilPuestoForm(initial=model_to_dict(periodo))
                    template = get_template("th_perfilpuesto/modal/formadicionarperiodo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
            if action == 'delperiodo':
                try:
                    data['title'] = u'Eliminar Periodo en peefil de puesto'
                    data['action'] = action
                    data['objeto'] = tipo = PeriodoPerfilPuesto.objects.get(pk=int(request.GET['id']))
                    data['descripcion'] = tipo.descripcion
                    data['destino'] = '/th_perfilpuesto'
                    return render(request, "th_perfilpuesto/modal/deletecompetencia.html", data)
                except Exception as ex:
                    pass
            # TIPO
            if action == 'addtipo':
                try:
                    data['form2'] = MantenimientoNombreForm()
                    template = get_template("th_perfilpuesto/modal/formadicionartipo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
            if action == 'edittipo':
                try:
                    data['id'] = id = request.GET['id']
                    data['action'] = action
                    data['tipo'] = tipo = TipoCompetenciaLaboral.objects.get(id=id)
                    data['form2'] = MantenimientoNombreForm(initial=model_to_dict(tipo))
                    template = get_template("th_perfilpuesto/modal/formadicionartipo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
            if action == 'eliminartipo':
                try:
                    data['title'] = u'Eliminar tipo'
                    data['action'] = action
                    data['objeto'] = tipo = TipoCompetenciaLaboral.objects.get(pk=int(request.GET['id']))
                    data['descripcion'] = tipo.nombre
                    data['destino'] = '/th_perfilpuesto?action=tipodiccionario'
                    return render(request, "th_perfilpuesto/modal/deletecompetencia.html", data)
                except Exception as ex:
                    pass
            # COMPTENCIAS
            if action == 'addcompetencia':
                try:
                    data['form2'] = CompetenciaLaboralForm()
                    template = get_template("th_perfilpuesto/modal/formadicionartipo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
            if action == 'editcompetencia':
                try:
                    data['id'] = id = request.GET['id']
                    data['action'] = action
                    data['diccionario'] = diccionario = CompetenciaLaboral.objects.get(id=id)
                    if diccionario.en_uso():
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"No se puede editar porque esta comptencia esta en uso"})
                    data['form2'] = CompetenciaLaboralForm(initial=model_to_dict(diccionario))
                    template = get_template("th_perfilpuesto/modal/formadicionartipo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
            if action == 'eliminarcompetencia':
                try:
                    data['title'] = u'Eliminar comptencia laboral'
                    data['action'] = action
                    data['objeto'] = competencia = CompetenciaLaboral.objects.get(pk=int(request.GET['id']))
                    data['descripcion'] = competencia.denominacion
                    data['destino'] = '/th_perfilpuesto?action=diccionario'
                    return render(request, "th_perfilpuesto/modal/deletecompetencia.html", data)
                except Exception as ex:
                    pass
            if action == 'adddetallecompetencia':
                try:
                    data['id'] = request.GET['id']
                    data['form2'] = DetalleCompetenciaLaboralForm()
                    template = get_template("th_perfilpuesto/modal/formadicionardetalle.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
            if action == 'editdetallecompetencia':
                try:
                    data['id'] = id = request.GET['id']
                    data['detallecomppetencia'] = detallecomppetencia = DetalleCompetenciaLaboral.objects.get(id=id)
                    data['form2'] = DetalleCompetenciaLaboralForm(initial=model_to_dict(detallecomppetencia))
                    template = get_template("th_perfilpuesto/modal/formadicionardetalle.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
            if action == 'eliminardetallecompetencia':
                try:
                    data['title'] = u'Eliminar Detalle Competencia Laboral'
                    data['action'] = action
                    data['objeto'] = detallecompetencia = DetalleCompetenciaLaboral.objects.get(
                        pk=int(request.GET['id']))
                    data['descripcion'] = detallecompetencia.comportamiento
                    data['destino'] = '/th_perfilpuesto?action=detallecompetencia&id=' + str(
                        detallecompetencia.competencia.pk)
                    return render(request, "th_perfilpuesto/modal/deletecompetencia.html", data)
                except Exception as ex:
                    pass
            if action == 'adddetdiccionario':
                try:
                    data['form2'] = MantenimientoNombreForm()
                    template = get_template("th_perfilpuesto/modal/formadicionartipo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
            if action == 'diccionario':
                try:
                    data['title'] = u'Diccionario de competencias laborales'
                    url_vars = ''
                    filtro = Q(status=True)
                    search = None
                    ids = None
                    tipo = None
                    if 's' in request.GET:
                        if request.GET['s'] != '':
                            search = request.GET['s']

                    if search:
                        filtro = filtro & (Q(denominacion__icontains=search) | (Q(numero__icontains=search)) | Q(
                            definicion__icontains=search))
                        url_vars += '&s=' + search

                    competencias = CompetenciaLaboral.objects.filter(filtro).order_by('id')

                    paging = MiPaginador(competencias, 20)
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
                    data['competencias'] = page.object_list
                    data['email_domain'] = EMAIL_DOMAIN
                    return render(request, "th_perfilpuesto/viewdiccionario.html", data)

                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
            if action == 'detallecompetencia':
                try:
                    data['title'] = u'Detalle de competencias'
                    data['competencia'] = competencia = CompetenciaLaboral.objects.get(pk=int(request.GET['id']))
                    url_vars = ''
                    filtro = Q(status=True, competencia=competencia)
                    search = None
                    ids = None
                    tipo = None
                    if 's' in request.GET:
                        if request.GET['s'] != '':
                            search = request.GET['s']

                    if search:
                        filtro = filtro & (Q(descripcion__icontains=search) | (Q(anio__icontains=search)))
                        url_vars += '&s=' + search

                    competencias = DetalleCompetenciaLaboral.objects.filter(filtro).order_by('id')

                    paging = MiPaginador(competencias, 20)
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
                    data['detalles'] = page.object_list
                    data['email_domain'] = EMAIL_DOMAIN
                    return render(request, "th_perfilpuesto/viewdetallecompetencia.html", data)

                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
            if action == 'tipodiccionario':
                try:
                    data['title'] = u'Tipo Diccionario'
                    url_vars = ''
                    filtro = Q(status=True)
                    search = None
                    ids = None

                    if 's' in request.GET:
                        if request.GET['s'] != '':
                            search = request.GET['s']
                    if search:
                        filtro = filtro & (Q(nombre__icontains=search))
                        url_vars += '&s=' + search

                    competencias = TipoCompetenciaLaboral.objects.filter(filtro).order_by('id')

                    paging = MiPaginador(competencias, 20)
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
                    data['tipodiccionarios'] = page.object_list
                    data['email_domain'] = EMAIL_DOMAIN
                    return render(request, "th_perfilpuesto/viewtipodiccionario.html", data)

                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
            if action == 'direcciones':
                try:

                    data['periodoperfil'] = periodoperfil = PeriodoPerfilPuesto.objects.get(id=int(request.GET['idp']))
                    search = None
                    url_vars = ''
                    filtro = Q(status=True, responsable__isnull=False, integrantes__isnull=False)
                    if 's' in request.GET:
                        if request.GET['s'] != '':
                            search = request.GET['s']
                    if search:
                        filtro = filtro & Q(nombre__icontains=search)
                        url_vars += '&s=' + search
                    direcciones = Departamento.objects.filter(filtro).distinct()
                    paging = MiPaginador(direcciones, 20)
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

                    data['direcciones'] = page.object_list

                    return render(request, "th_perfilpuesto/direccionesperfilpuesto.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
            if action == 'perfilesdireccion':
                try:
                    data['periodoperfil'] = periodoperfil = PeriodoPerfilPuesto.objects.get(id=int(request.GET['idp']))
                    data['title'] = u'UNIDADES ORGANIZACIONALES DEL PERIODO ' + str(periodoperfil.descripcion)+' VERSION '+str(periodoperfil.version)
                    search = None
                    url_vars = ''
                    filtro = Q(status=True)
                    if 's' in request.GET:
                        if request.GET['s'] != '':
                            search = request.GET['s']
                    if search:
                        filtro = filtro & Q(direccion__nombre__icontains=search)
                        url_vars += '&s=' + search
                    direcciones = periodoperfil.direccionperfilpuesto_set.filter(filtro)
                    paging = MiPaginador(direcciones, 20)
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

                    data['direcciones'] = page.object_list

                    return render(request, "th_perfilpuesto/direccionesperfiles.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
            if action == 'gestionesperfilesdireccion':
                try:
                    data['periodoperfil'] = periodoperfil = PeriodoPerfilPuesto.objects.get(id=int(request.GET['idp']))
                    data['direccion'] = direccion = Departamento.objects.get(id=int(request.GET['id']))
                    data['title'] = u'SECCIONES DEL DEPARTAMENTO  DEL PERIODO ' + str(periodoperfil.descripcion)
                    search = None
                    url_vars = ''
                    filtro = Q(status=True)
                    if 's' in request.GET:
                        if request.GET['s'] != '':
                            search = request.GET['s']
                    if search:
                        filtro = filtro & Q(descripcion__icontains=search)
                        url_vars += '&s=' + search
                    gestiones = direccion.secciondepartamento_set.filter(filtro)
                    paging = MiPaginador(gestiones, 20)
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

                    data['gestiones']  = page.object_list

                    return render(request, "th_perfilpuesto/seccionesdireccionperfiles.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
            if action == 'perfiles':
                try:
                    data['title'] = u'Perfiles de Puesto'
                    data['seccion'] = seccion = SeccionDepartamento.objects.get(id=int(request.GET['id']))
                    direccion = DireccionPerfilPuesto.objects.get(status=True,direccion_id=seccion.departamento_id,
                                                                  periodo_id=int(request.GET['idp']))
                    url_vars = ''
                    filtro = Q(status=True) & Q(direccion=direccion) & Q(secciondepartamento=seccion)
                    perfiles = PerfilPuestoTh.objects.filter(filtro)
                    data['denominaciones'] = perfiles.values_list('denominacionpuesto',
                                                                  'denominacionpuesto__descripcion')
                    data['dperfiles'] = perfiles.values_list('denominacionperfil',
                                                             'denominacionperfil__puesto__descripcion')
                    data['roles'] = perfiles.values_list('escala__rol_id', 'escala__rol__descripcion')
                    search = None
                    dpuesto = None
                    dperfil = None
                    rol = None
                    nivel = None
                    if 's' in request.GET:
                        if request.GET['s'] != '':
                            search = request.GET['s']
                    if 'dpuesto' in request.GET:
                        if int(request.GET['dpuesto']) > 0:
                            data['dpuestosel'] = dpuesto = int(request.GET['dpuesto'])
                    if 'dperfil' in request.GET:
                        if int(request.GET['dperfil']) > 0:
                            data['dperfilsel'] = dperfil = int(request.GET['dperfil'])
                    if 'nivel' in request.GET:
                        if int(request.GET['nivel']) > 0:
                            data['nivelsel'] = nivel = int(request.GET['nivel'])
                    if 'rol' in request.GET:
                        if int(request.GET['rol']) > 0:
                            data['rolsel'] = rol = int(request.GET['rol'])
                    if dpuesto:
                        filtro = filtro & Q(denominacionpuesto_id=dpuesto)
                        url_vars += '&dpuesto=' + str(dpuesto)
                    if dperfil:
                        filtro = filtro & Q(denominacionperfil_id=dperfil)
                        url_vars += '&dperfil=' + str(dperfil)
                    if nivel:
                        filtro = filtro & Q(nivel=nivel)
                        url_vars += '&nivel=' + str(nivel)
                    if rol:
                        filtro = filtro & Q(escala__rol_id=rol)
                        url_vars += '&rol=' + str(rol)
                    if search:
                        filtro = filtro & Q(codigo__icontains=search)
                        url_vars += '&s=' + search
                    data['periodoperfil'] = periodoperfil = PeriodoPerfilPuesto.objects.get(id=int(request.GET['idp']))
                    perfiles = PerfilPuestoTh.objects.filter(filtro).distinct()

                    paging = MiPaginador(perfiles, 20)
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

                    data['perfiles'] = page.object_list

                    return render(request, "th_perfilpuesto/viewperfil.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
            if action == 'addperfil':
                try:
                    data['title'] = u'Adicionar Perfil'
                    data['periodoperfil'] = periodoperfil = PeriodoPerfilPuesto.objects.get(status=True,id=int(request.GET['idp']))
                    data['seccion'] = seccion = SeccionDepartamento.objects.get(status = True,id=int(request.GET['seccion']))
                    data['direccion'] = direccion = DireccionPerfilPuesto.objects.get(status=True,direccion=seccion.departamento,
                                                                                     periodo=periodoperfil)
                    data['title'] = u'Adicionar Perfil: %s'%(seccion)
                    codigo = calcular_codigo(direccion, seccion, periodoperfil)
                    if codigo['resp'] == False:
                        data['mensajeerrorcodigo'] = codigo['mensaje']
                    else:
                        data['codigo'] = codigo['codigo']
                    data['form_extra'] = PerfilPuestoForm()
                    return render(request, 'th_perfilpuesto/addperfil.html', data)
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
            if action == 'editperfil':
                try:
                    data['title'] = u'Editar Perfil'
                    data['action'] = action
                    data['perfilpuesto'] = perfilpuesto = PerfilPuestoTh.objects.get(status=True,id=int(request.GET['id']))
                    data['id'] = perfilpuesto.pk
                    data['seccion'] = perfilpuesto.secciondepartamento
                    data['periodoperfil'] = periodoperfil = PeriodoPerfilPuesto.objects.get(status=True,id=int(request.GET['idp']))
                    data['direccion'] = perfilpuesto.direccion
                    data['form_extra'] = form_extra = PerfilPuestoForm(initial=model_to_dict(perfilpuesto))
                    data['areasconocimiento'] = perfilpuesto.areas_de_conocimiento()
                    return render(request, 'th_perfilpuesto/editperfil.html', data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
            if action == 'eliminarperfil':
                try:
                    data['title'] = u'Eliminar Perfil de Puesto'
                    data['action'] = action
                    data['objeto'] = perfil = PerfilPuestoTh.objects.get(pk=int(request.GET['id']))
                    data['descripcion'] = perfil.denominacionpuesto
                    data['destino'] = '/th_perfilpuesto?action=perfiles&id=' + str(perfil.direccion.pk) + '&idp=' + str(
                        perfil.direccion.periodo.pk)
                    return render(request, "th_perfilpuesto/modal/deletecompetencia.html", data)
                except Exception as ex:
                    pass
            if action == 'viewdetallesperfil':
                try:
                    data['perfilpuesto'] = perfilpuesto = PerfilPuestoTh.objects.get(id=int(request.GET['id']))
                    data['seccion'] = perfilpuesto.secciondepartamento
                    data['form_extra'] = PerfilPuestoForm(initial=model_to_dict(perfilpuesto))
                    data['title'] = u'Detalles del Perfil'
                    return render(request, 'th_perfilpuesto/viewdetallesperfil.html', data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
            if action == 'searchdenominacionperfil':
                try:
                    id = int(request.GET['id']) if not request.GET['id'] == "" else 0
                    puesto = PuestoDenominacion.objects.get(id=id)
                    array = []
                    instrucciones = puesto.denominacionperfilpuesto_set.filter(status=True)
                    # DenominacionPerfilPuesto.objects.filter(status=True, puestodenominacion=puesto)
                    for i in instrucciones[0:4]:
                        if i.mesesexperiencia >11   :
                            array.append({'meses': str(i.meses_to_anio()), 'instruccion': str(i.niveltitulo.nombre)})
                        else:
                            array.append({'meses': str(i.mesesexperiencia), 'instruccion': str(i.niveltitulo.nombre)})
                    return JsonResponse({"result": "ok", 'data': array}, safe=False)
                except Exception as e:
                    return JsonResponse({"result": "bad", "mensaje": u"Error en la transaccion. %s" % e})
            if action == 'searchescala':
                try:
                    escala = EscalaSalarial.objects.get(id=int(request.GET['id']))
                    array = {'grupo': str(escala.grupoocupacional), 'grado': str(escala.nivel.nivel), 'rmu': str(escala.rmu)}
                    return JsonResponse({"result": "ok", 'data': array}, safe=False)
                except Exception as e:
                    return JsonResponse({"result": "bad", "mensaje": u"Error en la transaccion. %s" % e})
            if action == 'searchcompetencia':
                try:
                    array = {'denominacion': 'N/A', 'nivel': 'N/A', 'comportamiento': 'N/A', 'color': '#ff000024'}
                    if DetalleCompetenciaLaboral.objects.values('id').filter(status = True, numero=int(request.GET['id']), competencia__tipo__id =int(request.GET['tipo']) ).exists():
                        detalle = DetalleCompetenciaLaboral.objects.get(status = True, numero=int(request.GET['id']), competencia__tipo__id =int(request.GET['tipo']) )
                        if 'idpp' in request.GET:

                            if request.GET['idpp'] != '':

                                h = CompetenciasPerfilPuesto.objects.filter(id=int(request.GET['idpp']), status=True).first()
                            else:
                                h = CompetenciasPerfilPuesto.objects.filter(id=int('0'))
                            if h:
                                hid = h.id
                            else:
                                hid= '0'
                            array = {'denominacion': str(detalle.competencia.denominacion),
                                     'nivel': str(detalle.get_nivel_display()),
                                     'comportamiento': str(detalle.comportamiento),
                                     'id':str(hid),
                                     'color': '#00ff3224'}
                        else:
                            array = {'denominacion': str(detalle.competencia.denominacion),
                                     'nivel': str(detalle.get_nivel_display()),
                                     'comportamiento': str(detalle.comportamiento),
                                     'color': '#00ff3224'}
                        return JsonResponse({"result": "ok", 'data': array}, safe=False)
                    return JsonResponse({"result": "bad", 'mensaje':'No existe esa competencia','data': array}, safe=False)
                except Exception as e:
                    return JsonResponse({"result": "bad", "mensaje": u"Error en la transaccion. %s" % e})
            # MATRIZ EXCEL
            if action == 'generarmatriz':
                try:
                    data['perfilpuesto'] = perfilpuesto = PerfilPuestoTh.objects.get(id=int(request.GET['id']))
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('Perfil_de_puesto')
                    ws.fit_to_pages(1,1)
                    ws.set_paper(9)
                    ws.set_landscape()
                    ws.set_margins(left=0.3, right=0.4, top=0.3, bottom=0.5)
                    ws.set_header(margin=0.6)
                    ws.set_footer(margin=0.5)
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

                    formatoceldaleft = workbook.add_format(
                        {'font_size': 14, 'border': 1, 'text_wrap': True, 'align': 'left', 'valign': 'vleft'})

                    formatoceldacenter = workbook.add_format(
                        {'font_size': 14, 'border': 1, 'text_wrap': True, 'align': 'center', 'valign': 'vcenter'})

                    formatoceldacenterleft = workbook.add_format(
                        {'font_size': 14, 'border': 1, 'text_wrap': True, 'align': 'left', 'valign': 'vcenter'})

                    formatotitulo = workbook.add_format(
                        {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 20, 'border': 1,
                         'text_wrap': True, 'font_color': 'black', 'font_name': 'Calibri'})

                    formatosubtitulo = workbook.add_format(
                        {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 14, 'border': 1,
                         'text_wrap': True, 'font_name': 'Calibri', 'fg_color': '#333399', 'font_color': 'white'})

                    formatosubtitulocolumna = workbook.add_format(
                        {'align': 'left', 'valign': 'vcenter', 'bold': 1, 'font_size': 14, 'border': 1,
                         'text_wrap': True, 'font_name': 'Calibri', 'fg_color': '#99CCFF', 'font_color': 'black'})

                    formatosubtitulocolumnacenter = workbook.add_format(
                        {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 14, 'border': 1,
                         'text_wrap': True, 'font_name': 'Calibri', 'fg_color': '#99CCFF', 'font_color': 'black'})

                    formatonotas = workbook.add_format(
                        {'text_wrap': True, 'align': 'left', 'font_color': 'black', 'font_size': 12})

                    formatoceldagrisv = workbook.add_format(
                        {'font_size': 6, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True,
                         'fg_color': '#B6BFC0'})
                    formatoceldagrisv.set_rotation(90)

                    logominurl = 'https://sga.unemi.edu.ec/static/images/logo-ministeriot.png'
                    #
                    logomin = io.BytesIO(urlopen(logominurl).read())

                    for r in range(1, 3):
                        ws.set_row(r, 24)
                    for r in range(6, 11):
                        ws.set_row(r, 55)
                    ws.insert_image('M2', logominurl,
                                    {'x_scale': 0.25, 'y_scale': 0.20, 'image_data': logomin, 'x_offset': 20,
                                     'y_offset': 10, 'object_position': 1})
                    ws.set_column(0, 0, 34.43)
                    ws.set_column(8, 8, 34.86)
                    ws.set_column(9, 9, 36.57)
                    ws.set_column(12, 12, 22.14)
                    #
                    # ####TITULOS
                    ws.merge_range('A2:R4', 'DESCRIPCIÓN Y PERFIL DEL PUESTO', formatotitulo)
                    ws.merge_range('A5:F5', '1. DATOS DE IDENTIFICACIÓN DEL PUESTO', formatosubtitulo)
                    ws.merge_range('G5:I5', '3. RELACIONES INTERNAS Y EXTERNAS', formatosubtitulo)
                    ws.merge_range('J5:R5', '4. INSTRUCCIÓN FORMAL REQUERIDA', formatosubtitulo)
                    ws.merge_range('A14:I15', '2. MISIÓN ', formatosubtitulo)
                    ws.merge_range('J14:R14', '5. EXPERIENCIA LABORAL REQUERIDA', formatosubtitulo)
                    ws.merge_range('J17:R17', '6. CAPACITACIÓN REQUERIDA PARA EL PUESTO', formatosubtitulo)
                    ws.merge_range('J21:R21', '9. COMPETENCIAS TÉCNICAS', formatosubtitulo)
                    ws.merge_range('J28:R28', '10. COMPETENCIAS CONDUCTUALES', formatosubtitulo)
                    ws.merge_range('A21:F22', '7. ACTIVIDADES ESENCIALES', formatosubtitulo)
                    ws.merge_range('G21:I22', '8. CONOCIMIENTOS ADICIONALES RELACIONADOS A LAS ACTIVIDADES ESENCIALES',
                                   formatosubtitulo)

                    # #COLUMNAS SUBTITULO
                    #
                    ws.write('A6', 'Código:', formatosubtitulocolumna)
                    ws.write('A7', 'Denominación del Puesto:', formatosubtitulocolumna)
                    ws.write('A8', 'Nivel:', formatosubtitulocolumna)
                    ws.write('A9', 'Unidad Administrativa:', formatosubtitulocolumna)
                    ws.write('A10', 'Rol:', formatosubtitulocolumna)
                    ws.write('A11', 'Grupo Ocupacional según acuerdo Ministerial #0226:', formatosubtitulocolumna)
                    ws.write('A12', 'Grado:', formatosubtitulocolumna)
                    ws.write('A13', 'RMU:', formatosubtitulocolumna)
                    ws.merge_range('G6:I6', 'INTERFAZ', formatosubtitulocolumnacenter)
                    ws.merge_range('J6:K9', 'Nivel de Instrucción:', formatosubtitulocolumna)
                    ws.merge_range('J10:K13', 'Área de Conocimiento:', formatosubtitulocolumna)
                    ws.write('J15', 'Tiempo de Experiencia:', formatosubtitulocolumna)
                    ws.write('J16', 'Especificidad de la experiencia:', formatosubtitulocolumna)
                    ws.merge_range('J18:R18', 'Temática de la Capacitación', formatosubtitulocolumna)
                    ws.write('J22', 'Denominación de la Competencia', formatosubtitulocolumna)
                    ws.write('K22', 'Nivel', formatosubtitulocolumna)
                    ws.merge_range('L22:R22', 'Temática de la Capacitación', formatosubtitulocolumna)

                    ws.write('J29', 'Denominación de la Competencia', formatosubtitulocolumna)
                    ws.write('K29', 'Nivel', formatosubtitulocolumna)
                    ws.merge_range('L29:R29', 'Temática de la Capacitación', formatosubtitulocolumna)

                    ## contenido
                    ws.merge_range('B6:F6', str(perfilpuesto.codigo), formatoceldacenter)
                    ws.merge_range('B7:F7', str(perfilpuesto.denominacionperfil), formatoceldacenter)
                    ws.merge_range('B8:F8', str(perfilpuesto.nivel), formatoceldacenter)
                    ws.merge_range('B9:F9', str(perfilpuesto.direccion), formatoceldacenter)
                    ws.merge_range('B10:F10', str(perfilpuesto.escala.rol), formatoceldacenter)
                    ws.merge_range('B11:F11', str(perfilpuesto.escala.grupoocupacional), formatoceldacenter)
                    ws.merge_range('B12:F12', str(perfilpuesto.escala.nivel), formatoceldacenter)
                    ws.merge_range('B13:F13', str(perfilpuesto.escala.rmu), formatoceldacenter)
                    ws.merge_range('G7:I13', str(perfilpuesto.interfaz), formatoceldacenter)
                    row = 6
                    niveles = ''
                    for nivel in perfilpuesto.denominacionperfil.nivelesexperiencia():
                        niveles += str(nivel.niveltitulo)+', '+ ' '
                        # colinitial = 'L' + str(row)
                        # colend = 'R' + str(row)
                        # cell = colinitial + ':' + colend
                        # if row == 8:
                        #     ws.merge_range('L8:R8', str(nivel.niveltitulo), formatoceldacenter)
                        # else:
                        #     ws.merge_range(cell, str(nivel.niveltitulo), formatoceldacenter)
                        row += 1
                    ws.merge_range('L6:R9', niveles,formatoceldacenter)
                    areas = ''
                    for a in perfilpuesto.areas_de_conocimiento():
                        areas += str(a.areaconocimiento.nombre) + ', ' + ' '
                    ws.merge_range('L10:R13', str(areas), formatoceldacenter)
                    ws.merge_range('A16:I20', str(perfilpuesto.mision), formatoceldacenter)
                    ws.merge_range('K16:R16', str(perfilpuesto.especificidadexperiencia), formatoceldacenter)

                    LETTERS = ('K', 'L', 'M','N','O','P','Q','R','S','T','U','V')


                    l = 0
                    for nivel in perfilpuesto.denominacionperfil.nivelesexperiencia():
                        ws.write(LETTERS[l] + '15', str(nivel.meses_to_anio()), formatoceldacenter)
                        l += 1

                    ws.merge_range('J19:R20', str(perfilpuesto.capacitacionrequerida), formatoceldacenter)

                    row1 = 23
                    row2 = 24
                    for act in perfilpuesto.actividadesesenciales():
                        ws.set_row(row1 - 1, 60)
                        ws.set_row(row2 - 1, 60)
                        ws.merge_range('A' + str(row1) + ':F' + str(row2), str(act.actividad).capitalize(), formatoceldacenterleft)
                        ws.merge_range('G' + str(row1) + ':I' + str(row2), str(act.conocimientoadicional).capitalize(),
                                       formatoceldacenterleft)
                        row1 += 2
                        row2 += 2

                    row1 = 23
                    for compt in perfilpuesto.competncias_tecnicas():
                        ws.write('J' + str(row1), str(compt.competencia.competencia.denominacion).capitalize(), formatoceldacenterleft)
                        ws.write('K' + str(row1), str(compt.competencia.get_nivel_display()).capitalize(),
                                 formatoceldacenterleft)
                        ws.merge_range('L' + str(row1) + ':R' + str(row1),
                                       str(compt.competencia.comportamiento).capitalize(), formatoceldacenterleft)
                        row1 += 1
                    row1 = 30
                    for compt in perfilpuesto.competncias_conductual():
                        ws.write('J' + str(row1), str(compt.competencia.competencia.denominacion).capitalize(), formatoceldacenterleft)
                        ws.write('K' + str(row1), str(compt.competencia.get_nivel_display()).capitalize(),
                                 formatoceldacenterleft)
                        ws.merge_range('L' + str(row1) + ':R' + str(row1),
                                       str(compt.competencia.comportamiento).capitalize(), formatoceldacenterleft)
                        row1 += 1
                    notavigencia = str(perfilpuesto.notaextra) + ' ' + str(perfilpuesto.direccion.periodo.fechafin.strftime('%Y-%m-%d'))
                    ws.set_row(34, 45)
                    ws.merge_range('A35:F35', notavigencia, formatonotas)
                    workbook.close()
                    output.seek(0)
                    filename = 'Perfil_de_puesto_' + random.randint(1, 10000).__str__() + '.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename

                    return response
                except Exception as ex:
                    pass
            if action == 'reporteperfiles':
                try:
                    seccion = SeccionDepartamento.objects.get(id=int(request.GET['id']))
                    direccion = DireccionPerfilPuesto.objects.get(status=True, direccion_id=seccion.departamento_id,
                                                                  periodo_id=int(request.GET['idp']))
                    url_vars = ''
                    filtro = Q(status=True) & Q(direccion=direccion) & Q(secciondepartamento=seccion)
                    perfiles = PerfilPuestoTh.objects.filter(filtro).order_by('codigo')
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    for perfilpuesto in perfiles:

                        ws = workbook.add_worksheet(str(perfilpuesto.codigo))
                        ws.fit_to_pages(1, 1)
                        ws.set_paper(9)
                        ws.set_landscape()
                        ws.set_margins(left=0.3, right=0.4, top=0.3, bottom=0.5)
                        ws.set_header(margin=0.6)
                        ws.set_footer(margin=0.5)
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

                        formatoceldaleft = workbook.add_format(
                            {'font_size': 14, 'border': 1, 'text_wrap': True, 'align': 'left', 'valign': 'vleft'})

                        formatoceldacenter = workbook.add_format(
                            {'font_size': 14, 'border': 1, 'text_wrap': True, 'align': 'center', 'valign': 'vcenter'})

                        formatoceldacenterleft = workbook.add_format(
                            {'font_size': 14, 'border': 1, 'text_wrap': True, 'align': 'left', 'valign': 'vcenter'})

                        formatotitulo = workbook.add_format(
                            {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 20, 'border': 1,
                             'text_wrap': True, 'font_color': 'black', 'font_name': 'Calibri'})

                        formatosubtitulo = workbook.add_format(
                            {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 14, 'border': 1,
                             'text_wrap': True, 'font_name': 'Calibri', 'fg_color': '#333399', 'font_color': 'white'})

                        formatosubtitulocolumna = workbook.add_format(
                            {'align': 'left', 'valign': 'vcenter', 'bold': 1, 'font_size': 14, 'border': 1,
                             'text_wrap': True, 'font_name': 'Calibri', 'fg_color': '#99CCFF', 'font_color': 'black'})

                        formatosubtitulocolumnacenter = workbook.add_format(
                            {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 14, 'border': 1,
                             'text_wrap': True, 'font_name': 'Calibri', 'fg_color': '#99CCFF', 'font_color': 'black'})

                        formatonotas = workbook.add_format(
                            {'text_wrap': True, 'align': 'left', 'font_color': 'black', 'font_size': 12})

                        formatoceldagrisv = workbook.add_format(
                            {'font_size': 6, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True,
                             'fg_color': '#B6BFC0'})
                        formatoceldagrisv.set_rotation(90)

                        logominurl = 'https://sga.unemi.edu.ec/static/images/logo-ministeriot.png'
                        #
                        logomin = io.BytesIO(urlopen(logominurl).read())

                        for r in range(1, 3):
                            ws.set_row(r, 24)
                        for r in range(6, 11):
                            ws.set_row(r, 55)
                        ws.insert_image('M2', logominurl,
                                        {'x_scale': 0.25, 'y_scale': 0.20, 'image_data': logomin, 'x_offset': 20,
                                         'y_offset': 10, 'object_position': 1})
                        ws.set_column(0, 0, 34.43)
                        ws.set_column(8, 8, 34.86)
                        ws.set_column(9, 9, 36.57)
                        ws.set_column(12, 12, 22.14)
                        #
                        # ####TITULOS
                        ws.merge_range('A2:R4', 'DESCRIPCIÓN Y PERFIL DEL PUESTO', formatotitulo)
                        ws.merge_range('A5:F5', '1. DATOS DE IDENTIFICACIÓN DEL PUESTO', formatosubtitulo)
                        ws.merge_range('G5:I5', '3. RELACIONES INTERNAS Y EXTERNAS', formatosubtitulo)
                        ws.merge_range('J5:R5', '4. INSTRUCCIÓN FORMAL REQUERIDA', formatosubtitulo)
                        ws.merge_range('A14:I15', '2. MISIÓN ', formatosubtitulo)
                        ws.merge_range('J14:R14', '5. EXPERIENCIA LABORAL REQUERIDA', formatosubtitulo)
                        ws.merge_range('J17:R17', '6. CAPACITACIÓN REQUERIDA PARA EL PUESTO', formatosubtitulo)
                        ws.merge_range('J21:R21', '9. COMPETENCIAS TÉCNICAS', formatosubtitulo)
                        ws.merge_range('J28:R28', '10. COMPETENCIAS CONDUCTUALES', formatosubtitulo)
                        ws.merge_range('A21:F22', '7. ACTIVIDADES ESENCIALES', formatosubtitulo)
                        ws.merge_range('G21:I22', '8. CONOCIMIENTOS ADICIONALES RELACIONADOS A LAS ACTIVIDADES ESENCIALES',
                                       formatosubtitulo)

                        # #COLUMNAS SUBTITULO
                        #
                        ws.write('A6', 'Código:', formatosubtitulocolumna)
                        ws.write('A7', 'Denominación del Puesto:', formatosubtitulocolumna)
                        ws.write('A8', 'Nivel:', formatosubtitulocolumna)
                        ws.write('A9', 'Unidad Administrativa:', formatosubtitulocolumna)
                        ws.write('A10', 'Rol:', formatosubtitulocolumna)
                        ws.write('A11', 'Grupo Ocupacional según acuerdo Ministerial #0226:', formatosubtitulocolumna)
                        ws.write('A12', 'Grado:', formatosubtitulocolumna)
                        ws.write('A13', 'RMU:', formatosubtitulocolumna)
                        ws.merge_range('G6:I6', 'INTERFAZ', formatosubtitulocolumnacenter)
                        ws.merge_range('J6:K9', 'Nivel de Instrucción:', formatosubtitulocolumna)
                        ws.merge_range('J10:K13', 'Área de Conocimiento:', formatosubtitulocolumna)
                        ws.write('J15', 'Tiempo de Experiencia:', formatosubtitulocolumna)
                        ws.write('J16', 'Especificidad de la experiencia:', formatosubtitulocolumna)
                        ws.merge_range('J18:R18', 'Temática de la Capacitación', formatosubtitulocolumna)
                        ws.write('J22', 'Denominación de la Competencia', formatosubtitulocolumna)
                        ws.write('K22', 'Nivel', formatosubtitulocolumna)
                        ws.merge_range('L22:R22', 'Temática de la Capacitación', formatosubtitulocolumna)

                        ws.write('J29', 'Denominación de la Competencia', formatosubtitulocolumna)
                        ws.write('K29', 'Nivel', formatosubtitulocolumna)
                        ws.merge_range('L29:R29', 'Temática de la Capacitación', formatosubtitulocolumna)

                        ## contenido
                        ws.merge_range('B6:F6', str(perfilpuesto.codigo), formatoceldacenter)
                        ws.merge_range('B7:F7', str(perfilpuesto.denominacionperfil), formatoceldacenter)
                        ws.merge_range('B8:F8', str(perfilpuesto.nivel), formatoceldacenter)
                        ws.merge_range('B9:F9', str(perfilpuesto.direccion), formatoceldacenter)
                        ws.merge_range('B10:F10', str(perfilpuesto.escala.rol), formatoceldacenter)
                        ws.merge_range('B11:F11', str(perfilpuesto.escala.grupoocupacional), formatoceldacenter)
                        ws.merge_range('B12:F12', str(perfilpuesto.escala.nivel), formatoceldacenter)
                        ws.merge_range('B13:F13', str(perfilpuesto.escala.rmu), formatoceldacenter)
                        ws.merge_range('G7:I13', str(perfilpuesto.interfaz), formatoceldacenter)
                        row = 6
                        niveles = ''
                        for nivel in perfilpuesto.denominacionperfil.nivelesexperiencia():
                            niveles += str(nivel.niveltitulo) + ', ' + ' '
                            # colinitial = 'L' + str(row)
                            # colend = 'R' + str(row)
                            # cell = colinitial + ':' + colend
                            # if row == 8:
                            #     ws.merge_range('L8:R8', str(nivel.niveltitulo), formatoceldacenter)
                            # else:
                            #     ws.merge_range(cell, str(nivel.niveltitulo), formatoceldacenter)
                            row += 1
                        ws.merge_range('L6:R9', niveles, formatoceldacenter)
                        areas = ''
                        for a in perfilpuesto.areas_de_conocimiento():
                            areas += str(a.areaconocimiento.nombre) + ', ' + ' '
                        ws.merge_range('L10:R13', str(areas), formatoceldacenter)
                        ws.merge_range('A16:I20', str(perfilpuesto.mision), formatoceldacenter)
                        ws.merge_range('K16:R16', str(perfilpuesto.especificidadexperiencia), formatoceldacenter)

                        LETTERS = ('K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V')

                        l = 0
                        for nivel in perfilpuesto.denominacionperfil.nivelesexperiencia():
                            ws.write(LETTERS[l] + '15', str(nivel.meses_to_anio()), formatoceldacenter)
                            l += 1

                        ws.merge_range('J19:R20', str(perfilpuesto.capacitacionrequerida), formatoceldacenter)

                        row1 = 23
                        row2 = 24
                        for act in perfilpuesto.actividadesesenciales():
                            ws.set_row(row1 - 1, 60)
                            ws.set_row(row2 - 1, 60)
                            ws.merge_range('A' + str(row1) + ':F' + str(row2), str(act.actividad).capitalize(), formatoceldacenterleft)
                            ws.merge_range('G' + str(row1) + ':I' + str(row2), str(act.conocimientoadicional).capitalize(),
                                           formatoceldacenterleft)
                            row1 += 2
                            row2 += 2

                        row1 = 23
                        for compt in perfilpuesto.competncias_tecnicas():
                            ws.write('J' + str(row1), str(compt.competencia.competencia.denominacion).capitalize(), formatoceldacenterleft)
                            ws.write('K' + str(row1), str(compt.competencia.get_nivel_display()).capitalize(),
                                     formatoceldacenterleft)
                            ws.merge_range('L' + str(row1) + ':R' + str(row1),
                                           str(compt.competencia.comportamiento).capitalize(), formatoceldacenterleft)
                            row1 += 1
                        row1 = 30
                        for compt in perfilpuesto.competncias_conductual():
                            ws.write('J' + str(row1), str(compt.competencia.competencia.denominacion).capitalize(), formatoceldacenterleft)
                            ws.write('K' + str(row1), str(compt.competencia.get_nivel_display()).capitalize(),
                                     formatoceldacenterleft)
                            ws.merge_range('L' + str(row1) + ':R' + str(row1),
                                           str(compt.competencia.comportamiento).capitalize(), formatoceldacenterleft)
                            row1 += 1
                        notavigencia = str(perfilpuesto.notaextra) + ' ' + str(perfilpuesto.direccion.periodo.fechafin.strftime('%Y-%m-%d'))
                        ws.set_row(34, 45)
                        ws.merge_range('A35:F35', notavigencia, formatonotas)
                    workbook.close()
                    output.seek(0)
                    filename = 'Perfil_de_puesto_' + random.randint(1, 10000).__str__() + '.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename

                    return response
                except Exception as ex:
                    pass
            return HttpResponseRedirect(request.path)
        else:

            data['title'] = u'Periodo de perfil de puesto'

            url_vars = ''
            filtro = Q(status=True)
            search = None
            ids = None
            tipo = None

            if 's' in request.GET:
                if request.GET['s'] != '':
                    search = request.GET['s']

            if search:
                filtro = filtro & (Q(descripcion__icontains=search) | (Q(anio__icontains=search)))
                url_vars += '&s=' + search

            perfil = PeriodoPerfilPuesto.objects.filter(filtro).order_by('id')

            paging = MiPaginador(perfil, 20)
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
            data['periodos'] = page.object_list
            data['email_domain'] = EMAIL_DOMAIN
            data['formduplicar'] = DuplicarPeriodoPerfilPuestoForm()
            return render(request, 'th_perfilpuesto/view.html', data)


def calcular_codigo(direccion, gestion, periodoperfil):
    try:
        if not direccion.direccion.codigoindice:
            return {'resp': False,
                    'mensaje': 'Debe configurar el codigo de indice en el departamento {} para poder generar el codigo'.format(
                        direccion.direccion)}
        if not direccion.direccion.tipoindice:
            return {'resp': False,
                    'mensaje': 'Debe configurar el tipo de indice en el departamento {} para poder generar el codigo'.format(
                        direccion.direccion)}
        if not gestion.codigoindice:
            return {'resp': False,
                    'mensaje': 'Debe configurar el codigo de indice en la gestion {} para poder generar el codigo'.format(
                        gestion)}
        ultimo = 0
        if PerfilPuestoTh.objects.filter(status=True, direccion=direccion, secciondepartamento=gestion,
                                         direccion__periodo=periodoperfil).exists():
            ultimo = PerfilPuestoTh.objects.filter(status=True, direccion=direccion, secciondepartamento=gestion,
                                                   direccion__periodo=periodoperfil).count()
        ultimo += 1
        # if ultimo <= 9:
        #     ultimo = '{}'.format(ultimo)
        codigo = '{}.{}.{}.{}'.format(str(int(direccion.direccion.tipoindice)),
                                      direccion.direccion.codigoindice,
                                      gestion.codigoindice, str(ultimo))
        return {'resp': True, 'codigo': codigo}
    except Exception as ex:
        return {'resp': False, 'mensaje': str(ex)}


def duplicar_periodo(request, descripcion, vigencia, periodo):
    try:
        if int(periodo) > 0:
            modelperiodo = PeriodoPerfilPuesto.objects.get(id=periodo)
            anio = datetime.now().year
            version = 1 if not modelperiodo.anio == anio else modelperiodo.version + 1
            periododuplicado = PeriodoPerfilPuesto(anio=anio, descripcion=descripcion, fechafin=vigencia,
                                                   version=version)
            periododuplicado.save(request)
            log(u'Adicionó nuevo periodo en  perfil de puesto: %s' % periododuplicado, request, "add")
            modelperiodo.activo = False
            modelperiodo.save(request)
            for direccion in modelperiodo.direccionperfilpuesto_set.filter(status=True):
                direccionduplicada = DireccionPerfilPuesto(direccion=direccion.direccion, periodo=periododuplicado)
                direccionduplicada.save(request)
                log(u'Adicionó direccion  a perfil puesto : %s' % direccionduplicada, request, "add")
                for gestion in SeccionDepartamento.objects.filter(status=True, departamento=direccion.direccion):
                    if PerfilPuestoTh.objects.filter(status=True, direccion=direccion,
                                                     secciondepartamento=gestion).exists():
                        for perfilactual in PerfilPuestoTh.objects.filter(status=True, direccion=direccion,
                                                                  secciondepartamento=gestion):
                            perfilduplicado = PerfilPuestoTh(codigo=perfilactual.codigo,
                                                             denominacionpuesto=perfilactual.denominacionpuesto,
                                                             denominacionperfil=perfilactual.denominacionperfil,
                                                             nivel=perfilactual.nivel,
                                                             direccion=direccionduplicada,
                                                             secciondepartamento=gestion,
                                                             escala=perfilactual.escala,
                                                             mision=perfilactual.mision,
                                                             especificidadexperiencia=perfilactual.especificidadexperiencia,
                                                             interfaz=perfilactual.interfaz,
                                                             capacitacionrequerida=perfilactual.capacitacionrequerida)
                            perfilduplicado.save(request)
                            for a in perfilactual.actividadesesenciales():
                                actividad = ActividadesEsencialesPerfilPuesto(perfilpuesto=perfilduplicado,
                                                                              actividad=a.actividad,
                                                                              conocimientoadicional=a.conocimientoadicional)
                                actividad.save(request)
                            for area in perfilactual.areas_de_conocimiento():
                                areac = AreaConocimientoPerfilPuesto(perfil=perfilduplicado,
                                                                     areaconocimiento=area.areaconocimiento)
                                areac.save(request)
                            for ctec in perfilactual.competncias_tecnicas():
                                comp = CompetenciasPerfilPuesto(perfil=perfilduplicado, competencia=ctec.competencia)
                                comp.save(request)
                            for cct in perfilactual.competncias_conductual():
                                comp = CompetenciasPerfilPuesto(perfil=perfilduplicado, competencia=cct.competencia)
                                comp.save(request)
                        log(u'Adicionó nuevo perfil de puesto: %s' % periododuplicado, request, "add")
            return {'resp': True, 'mensaje': 'Periodo Duplicado'}
        return {'resp': False, 'mensaje': 'Periodo no valido'}
    except Exception as ex:
        transaction.set_rollback(True)
        return {'resp': False, 'mensaje': str(ex)}
