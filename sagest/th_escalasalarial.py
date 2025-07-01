# -*- coding: UTF-8 -*-
import json
import random
import sys
from datetime import date, datetime

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
from sagest.forms import MantenimientoEscalaForm, EscalaSalarialForm, NivelEscalaSalarialForm, DenominacionPerfilPuestoForm, \
    NivelTituloForm
from sagest.models import NivelOcupacional, RegimenLaboral, EscalaOcupacional, EscalaSalarial, NivelEscalaSalarial, \
    DenominacionPerfilPuesto, Puesto, PuestoDenominacion, DenominacionPuesto
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log
from sga.models import NivelTitulacion


@login_required(redirect_field_name='ret', login_url='/loginsagest')
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    usuario = request.user

    if request.method == 'POST':
        action = request.POST['action']
        #escala salarial
        if action == 'addescalasalarial':
            try:
                f = EscalaSalarialForm(request.POST)
                if f.is_valid():
                    regimen_id = int(f.cleaned_data['regimenlaboral'].pk)
                    escala = EscalaSalarial(regimenlaboral=f.cleaned_data['regimenlaboral'],
                                            rol=f.cleaned_data['rol'], rmu=f.cleaned_data['rmu'])
                    if regimen_id == 1:
                        escala.grupoocupacional=f.cleaned_data['grupoocupacional']
                        escala.nivel = f.cleaned_data['nivel']
                    elif regimen_id == 4:
                        escala.nivel = f.cleaned_data['nivel']
                        escala.subnivel = f.cleaned_data['subnivel']
                    escala.save(request)
                    log(u'Adiciono nueva escala salarial: %s' % escala, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})
        elif action == 'editescalasalarial':
            try:
                id = request.POST['id']
                f = EscalaSalarialForm(request.POST)
                if f.is_valid():
                    escala = EscalaSalarial.objects.get(id=id)
                    escala.rol = f.cleaned_data['rol']
                    escala.rmu = f.cleaned_data['rmu']
                    regimen_id = int(escala.regimenlaboral.pk)
                    if regimen_id == 1:
                        escala.grupoocupacional = f.cleaned_data['grupoocupacional']
                        escala.nivel = f.cleaned_data['nivel']
                    elif regimen_id == 4:
                        escala.nivel = f.cleaned_data['nivel']
                        escala.subnivel = f.cleaned_data['subnivel']
                    escala.save(request)
                    log(u'Edito una escala salarial: %s' % escala, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    # print(f.errors)
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        if action == 'delleliminarperfilmodal':
            try:
                puestoDenominacion = PuestoDenominacion.objects.get(pk=request.POST['id'])
                puestoDenominacion.status = False
                puestoDenominacion.save(request)
                log(u'Elimino : %s' % puestoDenominacion.id, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delescalasalarial':
            escala = EscalaSalarial.objects.get(id=int(request.POST['id']))
            escala.status = False
            escala.save(request)
            log(u'Elimino una escala salarial: %s' % escala, request, "del")
            return JsonResponse({"result": False}, safe=False)
        #nivel
        if action == 'addnivel':
            try:
                f = NivelEscalaSalarialForm(request.POST)
                if f.is_valid():
                    if NivelEscalaSalarial.objects.filter(Q(status=True), Q(nivel=f.cleaned_data['nivel']) | Q(descripcion=f.cleaned_data['descripcion'])).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"ESTE NIVEL YA EXISTE!"})
                    else:
                        nivel = NivelEscalaSalarial(descripcion=f.cleaned_data['descripcion'],
                                                    nivel=f.cleaned_data['nivel'])
                        nivel.save(request)
                        log(u'Adicionó nuevo nivel: %s' % nivel.descripcion, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        if action == 'editnivel':
            try:
                id = request.POST['id']
                f = NivelEscalaSalarialForm(request.POST)
                if f.is_valid():
                    nivel = NivelEscalaSalarial.objects.get(id=id)
                    if NivelEscalaSalarial.objects.filter(Q(status=True), Q(nivel=f.cleaned_data['nivel']) | Q(descripcion=f.cleaned_data['descripcion'])).exclude(id=nivel.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"ESTE NIVEL YA EXISTE!"})
                    else:
                        nivel.descripcion = f.cleaned_data['descripcion']
                        nivel.nivel = f.cleaned_data['nivel']
                        nivel.save(request)
                        log(u'Edito un nivel: %s' % nivel.descripcion, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        elif action == 'delnivel':
            nivel = NivelEscalaSalarial.objects.get(id=int(request.POST['id']))
            nivel.status = False
            nivel.save(request)
            log(u'Elimino un nivel: %s' % nivel, request, "del")
            return JsonResponse({"result": False}, safe=False)

        if action == 'addperfil':
            try:
                f = DenominacionPerfilPuestoForm(request.POST)
                niveles = json.loads(request.POST['lista_items1'])
                if f.is_valid():
                    if not PuestoDenominacion.objects.filter(denominacionpuesto=f.cleaned_data['puesto'], anio=datetime.now().year).exists():
                        puestodenominacion = PuestoDenominacion(denominacionpuesto=f.cleaned_data['puesto'], observacion=f.cleaned_data['observacion'])
                        puestodenominacion.save(request)
                        for a in niveles:
                            if DenominacionPerfilPuesto.objects.filter(status=True, puestodenominacion=puestodenominacion, niveltitulo_id=a['id']).exists():
                                return JsonResponse({"result": "bad", "mensaje": u"Ya existe este perfil o nivel de instruccion"})
                            perfil = DenominacionPerfilPuesto(puestodenominacion=puestodenominacion, niveltitulo_id=a['id'], mesesexperiencia=a['meses'])
                            perfil.save(request)
                            log(u'Adicionó nuevo perfil: %s' % perfil, request, "add")
                        return JsonResponse({"result": "ok"}, safe=False)
                    return JsonResponse({"result": "bad", "mensaje": u"Ya existe este puesto en este año."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})
        if action == 'editperfil':
            try:
                f = DenominacionPerfilPuestoForm(request.POST)
                niveles = json.loads(request.POST['lista_items1'])
                id = int(request.POST['id'])
                anio = int(request.POST['anio'])
                if f.is_valid():
                    if not PuestoDenominacion.objects.filter(Q(denominacionpuesto=f.cleaned_data['puesto']), anio=anio, status=True).exclude(id=id).exists():
                        puestodenominacion = PuestoDenominacion.objects.get(id=id)
                        for d in puestodenominacion.denominacionperfilpuesto_set.all():
                            d.status = False
                            d.save()
                        for a in niveles:
                            puestodenominacion.denominacionpuesto=f.cleaned_data['puesto']
                            puestodenominacion.save(request)
                            perfil = DenominacionPerfilPuesto(puestodenominacion=puestodenominacion, niveltitulo_id=a['id'], mesesexperiencia=a['meses'])
                            perfil.save(request)
                            log(u'Edito perfil de puesto: %s' % perfil, request, "edit")
                        return JsonResponse({"result": "ok"}, safe=False)
                    return JsonResponse({"result": "bad", "mensaje": u"Ya existe este puesto en este año."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})


        #regimen laboral
        elif action == 'addregimen':
            try:
                f = MantenimientoEscalaForm(request.POST)
                if f.is_valid():
                    if RegimenLaboral.objects.filter(Q(status=True), Q(codigo=f.cleaned_data['codigo']) | Q(
                            descripcion=f.cleaned_data['descripcion'])).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"ESTE REGIMEN YA EXISTE!"})
                    else:
                        regimen = RegimenLaboral(descripcion=f.cleaned_data['descripcion'],
                                                    codigo=f.cleaned_data['codigo'])
                        regimen.save(request)
                        log(u'Adicionó nuevo regimen: %s' % regimen, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})
        elif action == 'editregimen':
            try:
                id = int(request.POST['id'])
                f = MantenimientoEscalaForm(request.POST)
                if f.is_valid():
                    regimen = RegimenLaboral.objects.get(id=id)
                    if RegimenLaboral.objects.filter(Q(status=True), Q(codigo=f.cleaned_data['codigo']) | Q(
                            descripcion=f.cleaned_data['descripcion'])).exclude(id=regimen.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"ESTE REGIMEN YA EXISTE!"})
                    else:
                        regimen.descripcion = f.cleaned_data['descripcion']
                        regimen.codigo = f.cleaned_data['codigo']
                        regimen.save(request)
                        log(u'Edito un regimen: %s' % regimen, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
        elif action == 'delregimen':
            regimen = RegimenLaboral.objects.get(id=int(request.POST['id']))
            regimen.status = False
            regimen.save(request)
            log(u'Elimino un nivel: %s' % regimen, request, "del")
            return JsonResponse({"result": False}, safe=False)
        #grupo
        elif action == 'addgrupo':
            try:
                f = MantenimientoEscalaForm(request.POST)
                if f.is_valid():
                    if EscalaOcupacional.objects.filter(Q(status=True), Q(codigo=f.cleaned_data['codigo']) | Q(
                            descripcion=f.cleaned_data['descripcion'])).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"ESTE GRUPO YA EXISTE!"})
                    else:
                        regimen = EscalaOcupacional(descripcion=f.cleaned_data['descripcion'],
                                                    codigo=f.cleaned_data['codigo'])
                        regimen.save(request)
                        log(u'Adicionó nuevo grupo ocupacional: %s' % regimen, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})
        elif action == 'editgrupo':
            try:
                id = int(request.POST['id'])
                f = MantenimientoEscalaForm(request.POST)
                if f.is_valid():
                    grupo = EscalaOcupacional.objects.get(id=id)
                    if EscalaOcupacional.objects.filter(Q(status=True), Q(codigo=f.cleaned_data['codigo']) | Q(
                            descripcion=f.cleaned_data['descripcion'])).exclude(id=grupo.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"ESTE GRUPO OCUPACIONAL YA EXISTE!"})
                    else:
                        grupo.descripcion = f.cleaned_data['descripcion']
                        grupo.codigo = f.cleaned_data['codigo']
                        grupo.save(request)
                        log(u'Edito un grupo ocupacional: %s' % grupo, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
        elif action == 'delgrupo':
            grupo = EscalaOcupacional.objects.get(id=int(request.POST['id']))
            grupo.status = False
            grupo.save(request)
            log(u'Elimino un grupo ocupacional: %s' % grupo, request, "del")
            return JsonResponse({"result": False}, safe=False)

        # rol
        elif action == 'addrol':
            try:
                f = MantenimientoEscalaForm(request.POST)
                if f.is_valid():
                    if NivelOcupacional.objects.filter(Q(status=True), Q(codigo=f.cleaned_data['codigo']) | Q(
                            descripcion=f.cleaned_data['descripcion'])).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"ESTE ROL YA EXISTE!"})
                    else:
                        rol = NivelOcupacional(descripcion=f.cleaned_data['descripcion'],
                                                    codigo=f.cleaned_data['codigo'])
                        rol.save(request)
                        log(u'Adicionó nuevo rol (nivel ocupacional): %s' % rol, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})
        elif action == 'editrol':
            try:
                id = int(request.POST['id'])
                f = MantenimientoEscalaForm(request.POST)
                if f.is_valid():
                    rol = NivelOcupacional.objects.get(id=id)
                    if NivelOcupacional.objects.filter(Q(status=True), Q(codigo=f.cleaned_data['codigo']) | Q(
                            descripcion=f.cleaned_data['descripcion'])).exclude(id=rol.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"ESTE ROL YA EXISTE!"})
                    else:
                        rol.descripcion = f.cleaned_data['descripcion']
                        rol.codigo = f.cleaned_data['codigo']
                        rol.save(request)
                        log(u'Edito un rol (nivel ocupacional): %s' % rol, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
        elif action == 'delrol':
            rol = NivelOcupacional.objects.get(id=int(request.POST['id']))
            rol.status = False
            rol.save(request)
            log(u'Elimino un rol (nivel ocupacional): %s' % rol, request, "del")
            return JsonResponse({"result": False}, safe=False)

        #nivel titulo
        elif action == 'addniveltitulo':
            try:
                f = NivelTituloForm(request.POST)
                if f.is_valid():
                    if NivelTitulacion.objects.filter(status=True, nombre=f.cleaned_data['nombre'],
                                                      rango=f.cleaned_data['rango'],
                                                      codigo_tthh=f.cleaned_data['codigo_tthh'],
                                                      tipo=f.cleaned_data['tipo']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"ESTE NIVEL DE TITULO YA EXISTE!"})
                    else:
                        niveltitulo = NivelTitulacion(nombre=f.cleaned_data['nombre'],
                                                      rango=f.cleaned_data['rango'],
                                                      codigo_tthh=f.cleaned_data['codigo_tthh'],
                                                      tipo=f.cleaned_data['tipo'])
                        niveltitulo.save(request)
                        log(u'Adicionó nuevo nivel de titulo: %s' % niveltitulo, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})
        elif action == 'editniveltitulo':
            try:
                id = int(request.POST['id'])
                f = NivelTituloForm(request.POST)
                if f.is_valid():
                    niveltitulo = NivelTitulacion.objects.get(id=id)
                    if NivelTitulacion.objects.filter(status=True, nombre=f.cleaned_data['nombre'],
                                                      rango=f.cleaned_data['rango'],
                                                      codigo_tthh=f.cleaned_data['codigo_tthh'],
                                                      tipo=f.cleaned_data['tipo']).exclude(id=niveltitulo.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"ESTE NIVEL DE TITULO YA EXISTE!"})
                    else:
                        niveltitulo.nombre=f.cleaned_data['nombre']
                        niveltitulo.rango=f.cleaned_data['rango']
                        niveltitulo.codigo_tthh=f.cleaned_data['codigo_tthh']
                        niveltitulo.tipo=f.cleaned_data['tipo']
                        niveltitulo.save(request)
                        log(u'Edito un nivel de titulo: %s' % niveltitulo, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
        elif action == 'delniveltitulo':
            niveltitulo = NivelTitulacion.objects.get(id=int(request.POST['id']))
            niveltitulo.status = False
            niveltitulo.save(request)
            log(u'Elimino un nivel de titulo: %s' % niveltitulo, request, "del")
            return JsonResponse({"result": False}, safe=False)

        # denominacion de puesto
        # elif action == 'adddenominacion':
        #     try:
        #         f = MantenimientoEscalaForm(request.POST)
        #         if f.is_valid():
        #             if Puesto.objects.filter(status=True, codigo=f.cleaned_data['codigo'],
        #                                               descripcion=f.cleaned_data['descripcion']).exists():
        #                 return JsonResponse({"result": "bad", "mensaje": u"ESTA DENOMINACION YA EXISTE!"})
        #             else:
        #                 denominacion = Puesto(codigo=f.cleaned_data['codigo'],
        #                                               descripcion=f.cleaned_data['descripcion'])
        #                 denominacion.save(request)
        #                 log(u'Adicionó nueva denominacion: %s' % denominacion, request, "add")
        #                 return JsonResponse({"result": False}, safe=False)
        #         else:
        #             raise NameError('Error')
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})
        #
        # elif action == 'editdenominacion':
        #     try:
        #         id = int(request.POST['id'])
        #         f = MantenimientoEscalaForm(request.POST)
        #         if f.is_valid():
        #             denominacion = Puesto.objects.get(id=id)
        #             if Puesto.objects.filter(status=True, codigo=f.cleaned_data['codigo'],
        #                                               descripcion=f.cleaned_data['descripcion']
        #                                                  ).exclude(id=denominacion.id).exists():
        #                 return JsonResponse({"result": "bad", "mensaje": u"ESTA DENOMINACION YA EXISTE!"})
        #             else:
        #                 denominacion.codigo = f.cleaned_data['codigo']
        #                 denominacion.descripcion = f.cleaned_data['descripcion']
        #                 denominacion.save(request)
        #                 log(u'Edito una denominacion: %s' % denominacion, request, "edit")
        #                 return JsonResponse({"result": False}, safe=False)
        #     except Exception as ex:
        #         return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
        #
        # elif action == 'deldenominacion':
        #     denominacion = Puesto.objects.get(id=int(request.POST['id']))
        #     denominacion.status = False
        #     denominacion.save(request)
        #     log(u'Elimino una denominacion: %s' % denominacion, request, "del")
        #     return JsonResponse({"result": False}, safe=False)

        #DENOMINACIÓN PUESTO NUEVO
        elif action == 'adddenominacionpuesto':
            try:
                f = MantenimientoEscalaForm(request.POST)
                if f.is_valid():
                    if DenominacionPuesto.objects.filter(status=True, codigo=f.cleaned_data['codigo'].upper(),
                                                         descripcion=f.cleaned_data['descripcion'].upper()).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"ESTA DENOMINACIÓN PUESTO YA EXISTE!"})
                    else:
                        denominacionpuesto = DenominacionPuesto(codigo=f.cleaned_data['codigo'].upper(),
                                                                descripcion=f.cleaned_data['descripcion'].upper())
                        denominacionpuesto.save(request)
                        log(u'Adicionó nueva denominación puesto: %s' % denominacionpuesto, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        elif action == 'editdenominacionpuesto':
            try:
                id = int(request.POST['id'])
                f = MantenimientoEscalaForm(request.POST)
                if f.is_valid():
                    denominacionpuesto = DenominacionPuesto.objects.get(id=id)
                    if DenominacionPuesto.objects.filter(status=True, codigo=f.cleaned_data['codigo'],
                                                      descripcion=f.cleaned_data['descripcion']
                                                         ).exclude(id=denominacionpuesto.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"ESTA DENOMINACIÓN PUESTO YA EXISTE!"})
                    else:
                        denominacionpuesto.codigo = f.cleaned_data['codigo']
                        denominacionpuesto.descripcion = f.cleaned_data['descripcion']
                        denominacionpuesto.save(request)
                        log(u'Edito una denominación puesto: %s' % denominacionpuesto, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

        elif action == 'deldenominacionpuesto':
            denominacionpuesto = DenominacionPuesto.objects.get(id=int(request.POST['id']))
            denominacionpuesto.status = False
            denominacionpuesto.save(request)
            log(u'Elimino una denominacion: %s' % denominacionpuesto, request, "del")
            return JsonResponse({"result": False}, safe=False)


    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'configuraciones':
                try:
                    data['title'] = u'Configuraciones'
                    data['niveles'] = NivelEscalaSalarial.objects.filter(status=True).order_by('-id')
                    data['nivelocupacional'] = NivelOcupacional.objects.filter(status=True).order_by('-id')
                    data['regimenlaboral'] = RegimenLaboral.objects.filter(status=True).order_by('-pk')
                    data['escalaocupacional'] = EscalaOcupacional.objects.filter(status=True).order_by('-pk')
                    data['niveltitulacion'] = NivelTitulacion.objects.filter(status=True,).order_by('-pk')
                    #data['puestos'] = Puesto.objects.filter(status=True,).order_by('pk')
                    data['denominacionpuesto'] = DenominacionPuesto.objects.filter(status=True,).order_by('-pk')
                    return render(request, "th_escalasalarial/configuraciones.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

            if action == 'perfiles':
                try:
                    data['title'] = u'Denominaciones de Perfil'
                    search = request.GET.get('s', '')
                    url_vars = f"action=perfiles"
                    search = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        data['perfiles'] = PuestoDenominacion.objects.filter((
                            Q(puesto__descripcion__icontains = search)|
                            Q(denominacionpuesto__descripcion__icontains = search)),status=True)
                        data['url_vars'] = url_vars

                    else:
                    # puestos = PuestoDenominacion.objects.filter(status=True).values_list('puesto_id', flat=True).distinct()
                        data['perfiles'] = PuestoDenominacion.objects.filter(status=True)
                    return render(request, "th_escalasalarial/viewperfil.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

            if action == 'delleliminarperfilmodal':
                try:
                    data['title'] = u'Eliminar Firma'
                    data['puestoDenominacion'] = puestoDenominacion = PuestoDenominacion.objects.get(
                        pk=request.GET['id'])
                    data['puestoDenominacion_id'] = puestoDenominacion.id
                    return render(request, "th_escalasalarial/modal/delleliminarperfilmodal.html", data)
                except Exception as ex:
                    pass

            if action == 'addrol':
                try:
                    data['form2'] = MantenimientoEscalaForm()
                    template = get_template("th_escalasalarial/modal/formadicionar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

            if action == 'editrol':
                try:
                    data['id'] = id = int(request.GET['id'])
                    rol = NivelOcupacional.objects.get(id=id)
                    data['form2'] = MantenimientoEscalaForm(initial=model_to_dict(rol))
                    template = get_template("th_escalasalarial/modal/formadicionar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

            if action == 'addgrupo':
                try:
                    data['form2'] = MantenimientoEscalaForm()
                    template = get_template("th_escalasalarial/modal/formadicionar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

            if action == 'editgrupo':
                try:
                    data['id'] = id = int(request.GET['id'])
                    grupo = EscalaOcupacional.objects.get(id=id)
                    data['form2'] = MantenimientoEscalaForm(initial=model_to_dict(grupo))
                    template = get_template("th_escalasalarial/modal/formadicionar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})


            if action == 'addregimen':
                try:
                    data['form2'] = MantenimientoEscalaForm()
                    template = get_template("th_escalasalarial/modal/formadicionar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

            if action == 'editregimen':
                try:
                    data['id'] = id = int(request.GET['id'])
                    regimen = RegimenLaboral.objects.get(id=id)
                    data['form2'] = MantenimientoEscalaForm(initial=model_to_dict(regimen))
                    template = get_template("th_escalasalarial/modal/formadicionar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

            if action == 'addnivel':
                try:
                    data['form2'] = NivelEscalaSalarialForm()
                    template = get_template("th_escalasalarial/modal/formadicionar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

            if action == 'editnivel':
                try:
                    data['id'] = id = int(request.GET['id'])
                    nivel = NivelEscalaSalarial.objects.get(id=id)
                    data['form2'] = NivelEscalaSalarialForm(initial=model_to_dict(nivel))
                    template = get_template("th_escalasalarial/modal/formadicionar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

            if action == 'addescalasalarial':
                try:
                    data['form2'] = EscalaSalarialForm()
                    template = get_template("th_escalasalarial/modal/formadicionarescala.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

            if action == 'addperfil':
                try:
                    data['title'] = u'Adicionar Perfil'
                    data['action'] = action
                    data['form'] = DenominacionPerfilPuestoForm()
                    data['niveles'] = NivelTitulacion.objects.filter(status=True).distinct()
                    # template = get_template("th_escalasalarial/modal/formadicionarperfil.html")
                    return render(request, "th_escalasalarial/addperfil.html", data)
                    # return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

            if action == 'editperfil':
                try:
                    data['title'] = u'Adicionar Perfil'
                    data['action'] = action
                    data['id'] = id = request.GET['id']
                    data['puesto'] = puesto = PuestoDenominacion.objects.get(id=id)
                    data['anio'] = puesto.anio
                    data['form'] = DenominacionPerfilPuestoForm(initial=model_to_dict(puesto))
                    data['nivelespuesto'] = nivelespuesto = puesto.denominacionperfilpuesto_set.filter(status=True)
                    data['niveles'] = NivelTitulacion.objects.filter(status=True).exclude(id__in=nivelespuesto.values_list('niveltitulo_id', flat=True)).distinct()
                    return render(request, "th_escalasalarial/addperfil.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

            if action == 'editescalasalarial':
                try:
                    data['id'] = id = int(request.GET['id'])
                    escala = EscalaSalarial.objects.get(id=id)
                    data['form2'] = EscalaSalarialForm(initial=model_to_dict(escala))
                    template = get_template("th_escalasalarial/modal/formadicionarescala.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

            if action == 'addniveltitulo':
                try:
                    data['form2'] = NivelTituloForm()
                    template = get_template("th_escalasalarial/modal/formadicionarperfil.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

            if action == 'editniveltitulo':
                try:
                    data['id'] = id = int(request.GET['id'])
                    niveltitulo = NivelTitulacion.objects.get(id=id)
                    data['form2'] = NivelTituloForm(initial=model_to_dict(niveltitulo))
                    template = get_template("th_escalasalarial/modal/formadicionarescala.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

            # if action == 'adddenominacion':
            #     try:
            #         data['form2'] = MantenimientoEscalaForm()
            #         template = get_template("th_escalasalarial/modal/formadicionarperfil.html")
            #         return JsonResponse({"result": True, 'data': template.render(data)})
            #     except Exception as ex:
            #         return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})
            #
            # if action == 'editdenominacion':
            #     try:
            #         data['id'] = id = int(request.GET['id'])
            #         denominacion = Puesto.objects.get(id=id)
            #         data['form2'] = MantenimientoEscalaForm(initial=model_to_dict(denominacion))
            #         template = get_template("th_escalasalarial/modal/formadicionarescala.html")
            #         return JsonResponse({"result": True, 'data': template.render(data)})
            #     except Exception as ex:
            #         return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

            # DENOMINACIÓN PUESTO NUEVO
            if action == 'adddenominacionpuesto':
                try:
                    data['form2'] = MantenimientoEscalaForm()
                    template = get_template("th_escalasalarial/modal/formadicionarperfil.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

            if action == 'editdenominacionpuesto':
                try:
                    data['id'] = id = int(request.GET['id'])
                    denominacionpuesto = DenominacionPuesto.objects.get(id=id)
                    data['form2'] = MantenimientoEscalaForm(initial=model_to_dict(denominacionpuesto))
                    template = get_template("th_escalasalarial/modal/formadicionarescala.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

        else:

            data['title'] = u'Escala salarial'

            url_vars = ''
            filtro = Q(status=True)
            search = None
            ids = None
            tipo = None

            if 't' in request.GET:
                if request.GET['t'] != '0':
                    tipo = request.GET['t']
            if 's' in request.GET:
                if request.GET['s'] != '':
                    search = request.GET['s']

            if search:
                filtro = filtro & (Q(descripcion__icontains=search) | (Q(departamento__nombre__icontains=search)))
                url_vars += '&s=' + search

            if tipo:
                filtro = filtro & Q(categoria_id=int(tipo))
                url_vars += '&t=' + tipo

            escala = EscalaSalarial.objects.filter(filtro).order_by('id')

            paging = MiPaginador(escala, 20)
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
            data['t'] = int(tipo) if tipo else ''
            data["url_vars"] = url_vars
            data['ids'] = ids if ids else ""
            data['escalas'] = page.object_list
            data['email_domain'] = EMAIL_DOMAIN
            return render(request, 'th_escalasalarial/view.html', data)
