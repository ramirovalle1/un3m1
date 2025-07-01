# -*- coding: UTF-8 -*-
import json
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template.loader import get_template
from django.shortcuts import render, redirect
from django.contrib import messages
from decorators import secure_module, last_access
from cita.forms import *
from cita.models import *
from sagest.funciones import encrypt_id
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre, remover_caracteres_especiales_unicode
from django.db.models import Q
from settings import EMAIL_DOMAIN
from sga.templatetags.sga_extras import encrypt
from utils.filtros_genericos import filtro_persona_select

from unidecode import unidecode

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
# @transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    user = request.user
    mi_cargo = persona.mi_cargo_administrativo()
    mi_gestion = persona.mi_gestion()
    iddepartamento = persona.mi_departamentopersona()
    es_director, es_director_gestion = False, False
    if iddepartamento:
        mi_departamento = Departamento.objects.get(id=iddepartamento)
        es_director = persona == mi_departamento.responsable

    if mi_gestion:
        es_director_gestion = persona == mi_gestion.responsable
    permiso = request.user.has_perm('sagest.puede_gestionar_servicio')
    if request.method == 'POST':
        action = request.POST['action']

        # Departamento Servicios
        if action == 'addserviciodep':
            with transaction.atomic():
                try:
                    form = DepartamentoServicioForm(request.POST, request.FILES)  # Asegúrate de incluir request.FILES

                    if form.is_valid() and form.validador():
                        # Crear la instancia del servicio
                        instancia = DepartamentoServicio(
                            nombre=form.cleaned_data['nombre'],
                            departamento=form.cleaned_data['departamento'],
                            gestion=form.cleaned_data['gestion'],
                            descripcion=form.cleaned_data['descripcion'],
                            nombresistema=form.cleaned_data['nombresistema'],
                            tiposistema=form.cleaned_data['tiposistema'],
                            url_entrada=form.cleaned_data['url_entrada'],
                        )
                        instancia.save()

                        # Manejar la subida de los logos
                        if 'logonavbar' in request.FILES:
                            logonavbar_file = request.FILES['logonavbar']
                            instancia.logonavbar = logonavbar_file  # Guardar el archivo del navbar
                        if 'logofooter' in request.FILES:
                            logofooter_file = request.FILES['logofooter']
                            instancia.logofooter = logofooter_file  # Guardar el archivo del footer

                        instancia.save()  # Guardar la instancia con los logos

                        log(u'Adiciono Servicio de Citas: %s' % instancia, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)
        # if action == 'addserviciodep':
        #     with transaction.atomic():
        #         try:
        #             form = DepartamentoServicioForm(request.POST)
        #
        #             if form.is_valid() and form.validador():
        #
        #                 instancia = DepartamentoServicio(nombre=form.cleaned_data['nombre'],
        #                                                  departamento=form.cleaned_data['departamento'],
        #
        #                                                  gestion=form.cleaned_data['gestion'],
        #                                                  descripcion=form.cleaned_data['descripcion'],
        #                                                  nombresistema=form.cleaned_data['nombresistema'],
        #                                                  tiposistema=form.cleaned_data['tiposistema'],
        #                                                  url_entrada=form.cleaned_data['url_entrada'],)
        #                 #responsables = [persona]
        #                 #instancia.responsable.set(responsables)
        #                 instancia.save(request)
        #                 # Manejar el logo del navbar
        #                 if 'logonavbar' in request.FILES:
        #                     logonavbar_file = request.FILES['logonavbar']
        #                     logonavbar_file._name = generar_nombre(instancia.nombre_input(), logonavbar_file._name)
        #                     instancia.logonavbar = logonavbar_file
        #                 if 'logofooter' in request.FILES:
        #                     newfile = request.FILES['logofooter']
        #                     newfile._name = generar_nombre(instancia.nombre_input(), newfile._name)
        #                     instancia.logofooter = newfile
        #                     instancia.save(request)
        #                 instancia.save()
        #                 # instancia.responsable.add(persona)
        #                 # instancia.responsable.add(instancia.departamento.reponsable)
        #                 # for responsable in form.cleaned_data['responsable']:
        #                 #     instancia.responsable.add(responsable)
        #             else:
        #                 transaction.set_rollback(True)
        #                 return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
        #                                      "mensaje": "Error en el formulario"})
        #             log(u'Adiciono Servicio de Citas: %s' % instancia, request, "add")
        #             return JsonResponse({"result": False}, safe=False)
        #         except Exception as ex:
        #             transaction.set_rollback(True)
        #             return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)


        if action == 'editserviciodep':
            with transaction.atomic():
                try:
                    filtro = DepartamentoServicio.objects.get(pk=int(encrypt(request.POST['id'])))
                    form = DepartamentoServicioForm(request.POST)
                    if form.is_valid() and form.validador(filtro.id):
                        if 'logonavbar' in request.FILES:
                            newfile = request.FILES['logonavbar']
                            newfile._name = generar_nombre(filtro.nombre_input(), newfile._name)
                            filtro.logonavbar = newfile
                            filtro.save(request)
                        if 'logofooter' in request.FILES:
                            newfile = request.FILES['logofooter']
                            newfile._name = generar_nombre(filtro.nombre_input(), newfile._name)
                            filtro.logofooter = newfile
                            filtro.save(request)
                        filtro.save()
                        filtro.nombre = form.cleaned_data['nombre']
                        filtro.descripcion = form.cleaned_data['descripcion']
                        filtro.departamento = form.cleaned_data['departamento']
                        filtro.gestion = form.cleaned_data['gestion']
                        filtro.nombresistema = form.cleaned_data['nombresistema']
                        filtro.tiposistema = form.cleaned_data['tiposistema']
                        filtro.url_entrada = form.cleaned_data['url_entrada']
                        filtro.save(request)

                        # filtro.responsable.clear()
                        # for responsable in form.cleaned_data['responsable']:
                        #     filtro.responsable.add(responsable)

                        log(u'Edito Departamento Servicio de Citas: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)



        if action == 'delserviciodep':
            with transaction.atomic():
                try:
                    instancia = DepartamentoServicio.objects.get(pk=int(encrypt(request.POST['id'])))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Departamento Servicio de citas: %s' % instancia, request, "del")
                    res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        # Servicios
        if action == 'addservicio':
            with transaction.atomic():
                try:
                    form = ServicioCitaForm(request.POST)
                    idpadre = int(encrypt(request.POST['idpadre']))

                    if form.is_valid() and form.validador():
                        instancia = ServicioCita(departamentoservicio_id=idpadre,
                                                 nombre=form.cleaned_data['nombre'],
                                                 descripcion=form.cleaned_data['descripcion'],
                                                 cuerpodescripcion=form.cleaned_data['cuerpodescripcion'],
                                                 responsable=form.cleaned_data['responsable'],
                                                 link_atencion=form.cleaned_data['link_atencion'],
                                                 tipo_atencion=form.cleaned_data['tipo_atencion'],
                                                 gestion_servicio=form.cleaned_data['gestion_servicio'],
                                                 lugar=form.cleaned_data['lugar'],
                                                 bloque=form.cleaned_data['bloque'],
                                                 mostrar=form.cleaned_data['mostrar'],
                                                 )
                        instancia.save(request)
                        for motivo in form.cleaned_data['motivos']:
                            instancia.motivos.add(motivo)

                        if 'portada' in request.FILES:
                            newfile = request.FILES['portada']
                            newfile._name = generar_nombre(instancia.nombre_input(), newfile._name)
                            instancia.portada = newfile
                            instancia.save(request)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                    log(u'Adiciono Servicio de Citas: %s' % instancia, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'editservicio':
            with transaction.atomic():
                try:
                    filtro = ServicioCita.objects.get(pk=int(encrypt(request.POST['id'])))
                    form = ServicioCitaForm(request.POST)
                    if form.is_valid() and form.validador(filtro.id):
                        if 'portada' in request.FILES:
                            newfile = request.FILES['portada']
                            newfile._name = generar_nombre(filtro.nombre_input(), newfile._name)
                            filtro.portada = newfile
                        filtro.nombre = form.cleaned_data['nombre']
                        filtro.descripcion = form.cleaned_data['descripcion']
                        filtro.cuerpodescripcion = form.cleaned_data['cuerpodescripcion']
                        filtro.responsable = form.cleaned_data['responsable']
                        # filtro.departamento = form.cleaned_data['departamento']
                        filtro.link_atencion = form.cleaned_data['link_atencion']
                        filtro.tipo_atencion = form.cleaned_data['tipo_atencion']
                        filtro.gestion_servicio = form.cleaned_data['gestion_servicio']
                        filtro.lugar = form.cleaned_data['lugar']
                        filtro.bloque = form.cleaned_data['bloque']
                        filtro.mostrar = form.cleaned_data['mostrar']

                        filtro.save(request)
                        filtro.motivos.clear()
                        for motivo in form.cleaned_data['motivos']:
                            filtro.motivos.add(motivo)

                        log(u'Edito Servicio de Citas: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'delservicio':
            with transaction.atomic():
                try:
                    instancia = ServicioCita.objects.get(pk=int(encrypt(request.POST['id'])))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Servicio de citas: %s' % instancia, request, "del")
                    res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        if action == 'mostrarservicio':
            with transaction.atomic():
                try:
                    registro = ServicioCita.objects.get(pk=request.POST['id'])
                    registro.mostrar = eval(request.POST['val'].capitalize())
                    registro.save(request)
                    log(u'Mostrar servicio: %s (%s)' % (registro, registro.mostrar), request, "edit")
                    return JsonResponse({"result": True, 'mensaje': 'Cambios guardados'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False})

        # Configuración de servicios
        if action == 'addservicioconf':
            with transaction.atomic():
                try:
                    form = ServicioConfiguradoForm(request.POST, request.FILES)
                    id = int(encrypt(request.POST['idpadre']))
                    if form.is_valid() and form.validador(0, id):
                        cupo = form.cleaned_data['cupo']
                        numdias = form.cleaned_data['numdias']
                        numdiasinicio = form.cleaned_data['numdiasinicio']
                        prioridad = int(form.cleaned_data['prioridad'])
                        if prioridad == 1:
                            numdias = 365
                            # numdiasinicio = 0
                        instancia = ServicioConfigurado(serviciocita_id=id,
                                                        nombre=form.cleaned_data['nombre'],
                                                        prioridad=prioridad,
                                                        mostrar=form.cleaned_data['mostrar'],
                                                        cupo=cupo,
                                                        numdias=numdias,
                                                        numdiasinicio=numdiasinicio,
                                                        soloadministrativo=form.cleaned_data['soloadministrativo'])
                        instancia.save(request)
                        if instancia.mostrar:
                            configuraciones = ServicioConfigurado.objects.filter(status=True, mostrar=True,
                                                                                 serviciocita_id=id).exclude(
                                pk=instancia.id)
                            for conf in configuraciones:
                                conf.mostrar = False
                                conf.save(request)
                        # if 'portada' in request.FILES:
                        #     newfile = request.FILES['portada']
                        #     newfile._name = generar_nombre(instancia.nombre_input(), newfile._name)
                        #     instancia.portada = newfile
                        #     instancia.save(request)
                        # serviciocita = ServicioCita.objects.get(id=id)
                        # if serviciocita.departamentoservicio.responsable:
                        #     responsable = ResponsableServicioCita(servicio=instancia,
                        #                                           responsable=serviciocita.departamentoservicio.responsable,
                        #                                           activo=True, tipo=1)
                        #     responsable.save(request)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                    log(u'Adiciono Configuración de servicio de Citas: %s' % instancia, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'editservicioconf':
            with transaction.atomic():
                try:
                    filtro = ServicioConfigurado.objects.get(pk=int(encrypt(request.POST['id'])))
                    form = ServicioConfiguradoForm(request.POST, request.FILES)
                    if form.is_valid() and form.validador(filtro.id, filtro.serviciocita.id):
                        # if 'portada' in request.FILES:
                        #     newfile = request.FILES['portada']
                        #     newfile._name = generar_nombre(filtro.nombre_input(), newfile._name)
                        #     filtro.portada = newfile
                        cupo = form.cleaned_data['cupo']
                        numdias = form.cleaned_data['numdias']
                        prioridad = int(form.cleaned_data['prioridad'])
                        if prioridad == 1:
                            numdias = 365

                        filtro.nombre = form.cleaned_data['nombre']
                        filtro.prioridad = prioridad
                        filtro.mostrar = form.cleaned_data['mostrar']
                        filtro.numdiasinicio = form.cleaned_data['numdiasinicio']
                        filtro.soloadministrativo = form.cleaned_data['soloadministrativo']
                        filtro.cupo = cupo
                        filtro.numdias = numdias
                        filtro.save(request)
                        log(u'Edito Configuracion Servicio de Citas: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'delservicioconf':
            with transaction.atomic():
                try:
                    instancia = ServicioConfigurado.objects.get(pk=int(encrypt(request.POST['id'])))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Configuracion de Servicio de citas: %s' % instancia, request, "del")
                    res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        if action == 'mostrarservicioconf':
            with transaction.atomic():
                try:
                    mostrar = eval(request.POST['val'].capitalize())
                    if mostrar:
                        configuraciones = ServicioConfigurado.objects.filter(status=True, mostrar=True,
                                                                             serviciocita_id=int(
                                                                                 request.POST['idex'])).exclude(
                            pk=int(request.POST['id']))
                        for conf in configuraciones:
                            conf.mostrar = False
                            conf.save(request)
                    registro = ServicioConfigurado.objects.get(pk=int(request.POST['id']))
                    registro.mostrar = mostrar
                    registro.save(request)
                    log(u'Mostrar configuracion de servicio : %s (%s)' % (registro, registro.mostrar), request,
                        "edit")
                    return JsonResponse({"result": True, 'mensaje': 'Cambios guardados'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False})

        if action == 'mostrarsoloadministrativo':
            with transaction.atomic():
                try:
                    soloadministrativo = eval(request.POST['val'].capitalize())
                    if soloadministrativo:
                        mostrar = False
                    else:
                        mostrar = True
                    registro = ServicioConfigurado.objects.get(pk=int(request.POST['id']))
                    registro.soloadministrativo = soloadministrativo
                    registro.mostrar = mostrar
                    registro.save(request)
                    log(u'Mostrar configuracion de servicio : %s (%s)' % (registro, registro.soloadministrativo), request,
                        "edit")
                    return JsonResponse({"result": True, 'mensaje': 'Cambios guardados'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False})
        #
        # elif action == 'addcardinformativo':
        #     with transaction.atomic():
        #         try:
        #             form = CardInformativoForm(request.POST, request.FILES)
        #             if form.is_valid():
        #                 departamento = DepartamentoServicio.objects.get(id=int(request.POST['idpadre']))
        #                 instance = CardInformativo(
        #                     departamentoservicio=departamento,
        #                     titulo=form.cleaned_data['titulo'],
        #                     subtitulo=form.cleaned_data['subtitulo'],
        #                     fondo=form.cleaned_data['color'],
        #                     cuerpoinformativa=form.cleaned_data['cuerpoinformativa'],
        #                     orden=int(form.cleaned_data['orden'])
        #                 )
        #
        #                 # Guardar la instancia del modelo primero
        #                 instance.save()
        #
        #                 # Verificar si hay una imagen cargada y guardarla
        #                 if 'imagen' in request.FILES:
        #                     imagen = request.FILES['imagen']
        #                     file_name = generar_nombre(instance.nombre_input(), imagen.name)
        #                     file_path = default_storage.save(f'gestionvinculacion/noticias/{file_name}',
        #                                                      ContentFile(imagen.read()))
        #                     instance.imagen = file_path
        #                     instance.save()
        #
        #                 log(f'Adiciono card informativo {instance}', request, 'add')
        #                 return JsonResponse({'result': False, 'mensaje': u'Guardado con éxito'})
        #         except Exception as ex:
        #             res_json = {'error': True, "message": "Error: {}".format(ex)}
        #             return JsonResponse(res_json, safe=False)

        elif action == 'addcardinformativo':
            with transaction.atomic():
                try:
                    form = CardInformativoForm(request.POST, request.FILES)
                    if form.is_valid():
                        departamento = DepartamentoServicio.objects.get(id = int(request.POST['idpadre']))
                        instance = CardInformativo(departamentoservicio= departamento,
                                                   titulo=form.cleaned_data['titulo'],
                                                   subtitulo=form.cleaned_data['subtitulo'],
                                                   fondo=form.cleaned_data['fondo'],
                                                   cuerpoinformativa=form.cleaned_data['cuerpoinformativa'],
                                                   orden=int(form.cleaned_data['orden']))

                        instance.save(request)
                        if 'imagen' in request.FILES:
                            newfile = request.FILES['imagen']
                            newfile._name = generar_nombre(instance.imagen_input(newfile.name), newfile._name)
                            instance.imagen = newfile
                            instance.save(request)

                        log(f'Adiciono card informativo {instance}', request, 'add')
                        return JsonResponse({'result': False, 'mensaje': u'Guardado con éxito'})
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                    return JsonResponse(res_json, safe=False)

        # Turnos
        if action == 'addturno':
            with transaction.atomic():
                try:
                    form = TurnoCitaForm(request.POST)
                    if form.is_valid() and form.validador():
                        instance = TurnoCita(comienza=form.cleaned_data['comienza'],
                                             termina=form.cleaned_data['termina'],
                                             mostrar=form.cleaned_data['mostrar'])

                        instance.save(request)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                    log(u'Adiciono Turno Cita: %s' % instance, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'editturno':
            with transaction.atomic():
                try:
                    id = int(encrypt(request.POST['id']))
                    filtro = TurnoCita.objects.get(pk=id)
                    form = TurnoCitaForm(request.POST)
                    if form.is_valid() and form.validador(id):
                        filtro.comienza = form.cleaned_data['comienza']
                        filtro.termina = form.cleaned_data['termina']
                        filtro.mostrar = form.cleaned_data['mostrar']
                        filtro.save(request)
                        log(u'Edito turno en Citas: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'delturno':
            with transaction.atomic():
                try:
                    instancia = TurnoCita.objects.get(pk=int(encrypt(request.POST['id'])))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Turno de citas: %s' % instancia, request, "del")
                    res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        if action == 'activaturno':
            with transaction.atomic():
                try:
                    registro = TurnoCita.objects.get(pk=request.POST['id'])
                    registro.mostrar = eval(request.POST['val'].capitalize())
                    registro.save(request)
                    log(u'Turno activo : %s (%s)' % (registro, registro.mostrar), request, "edit")
                    return JsonResponse({"result": True, 'mensaje': 'Cambios guardados'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False})

        # Requisitos
        if action == 'addrequisito':
            with transaction.atomic():
                try:
                    form = RequisitoForm(request.POST)
                    if form.is_valid() and form.validador():
                        instancia = Requisito(nombre=form.cleaned_data['nombre'],
                                              descripcion=form.cleaned_data['descripcion'])
                        instancia.save(request)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse(
                            {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                             "mensaje": "Error en el formulario"})
                    log(u'Adiciono Requisito de Citas: %s' % instancia, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'editrequisito':
            with transaction.atomic():
                try:
                    filtro = Requisito.objects.get(pk=int(encrypt(request.POST['id'])))
                    form = RequisitoForm(request.POST)
                    if form.is_valid() and form.validador(filtro.id):
                        filtro.nombre = form.cleaned_data['nombre']
                        filtro.descripcion = form.cleaned_data['descripcion']
                        filtro.save(request)
                        log(u'Edito Requisito de Citas: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse(
                            {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'delrequisito':
            with transaction.atomic():
                try:
                    instancia = Requisito.objects.get(pk=int(encrypt(request.POST['id'])))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Requisito de citas: %s' % instancia, request, "del")
                    res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        # Motivo cita
        if action == 'addmotivocita':
            with transaction.atomic():
                try:
                    form = MotivoCitaForm(request.POST)
                    idpadre = int(encrypt(request.POST['idpadre']))
                    if form.is_valid() and form.validador(idpadre):
                        instancia = MotivoCita(departamentoservicio_id=idpadre,
                                               descripcion=form.cleaned_data['descripcion'])
                        instancia.save(request)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse(
                            {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                             "mensaje": "Error en el formulario"})
                    log(u'Adiciono Motivo de Citas: %s' % instancia, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'editmotivocita':
            with transaction.atomic():
                try:
                    filtro = MotivoCita.objects.get(pk=int(encrypt(request.POST['id'])))
                    idpadre = int(encrypt(request.POST['idpadre']))
                    form = MotivoCitaForm(request.POST)
                    if form.is_valid() and form.validador(idpadre,filtro.id):
                        filtro.descripcion = form.cleaned_data['descripcion']
                        filtro.save(request)
                        log(u'Edito Motivo de Citas: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse(
                            {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

            #     # Responsables
            # if action == 'addresponsable':
            #     with transaction.atomic():
            #         try:
            #             idservicio = int(encrypt(request.POST['id']))
            #             form = ResponsableServicioForm(request.POST)
            #             if form.is_valid():
            #                 responsable = ResponsableServicioCita(servicio_id=idservicio,
            #                                                       responsable=form.cleaned_data['responsable'],
            #                                                       tipo=form.cleaned_data['tipo'],
            #                                                       activo=True)
            #                 responsable.save(request)
            #                 log(u'Agrego Responsable a Servicio: %s' % responsable, request, "add")
            #                 diccionario = {'id': responsable.id,
            #                                'responsable': str(responsable.responsable),
            #                                'foto': responsable.responsable.get_foto(),
            #                                'tipo': responsable.tipo,
            #                                'activo': responsable.activo,
            #                                }
            #                 return JsonResponse({'result': True, 'data_return': True, 'mensaje': u'Guardado con exito',
            #                                      'data': diccionario, })
            #             else:
            #                 transaction.set_rollback(True)
            #                 return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
            #                                      "mensaje": "Error en el formulario"})
            #         except Exception as ex:
            #             transaction.set_rollback(True)
            #             return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'delmotivocita':
            with transaction.atomic():
                try:
                    instancia = MotivoCita.objects.get(pk=int(encrypt(request.POST['id'])))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino motivo de citas: %s' % instancia, request, "del")
                    res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        # Procesos
        if action == 'addproceso':
            with transaction.atomic():
                try:
                    form = ProcesoForm(request.POST)
                    idpadre = int(encrypt(request.POST['idpadre']))
                    idservicio = int(request.POST['servicio'])
                    if form.is_valid() and form.validador(idservicio):
                        x= ServicioCita.objects.get(id=int(idservicio))
                        # tipoinforme= None
                        # tipo_proceso= None
                        if x.id == 5:
                            tipoinforme = 2
                            tipo_proceso = 2
                        if x.id == 6:
                            tipoinforme = 1
                            tipo_proceso = 1
                        instancia = Proceso(servicio_id=int(idservicio),
                                            descripcion=form.cleaned_data['descripcion'],
                                            tipo_proceso=tipo_proceso,
                                            mostrar=form.cleaned_data['mostrar'],
                                            subtitulo=form.cleaned_data['subtitulo'],
                                            tipoinforme=tipoinforme)
                        instancia.save(request)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse(
                            {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                             "mensaje": "Error en el formulario"})
                    log(u'Adiciono Proceso de Citas: %s' % instancia, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'editproceso':
            with transaction.atomic():
                try:
                    filtro = Proceso.objects.get(pk=int(encrypt(request.POST['id'])))
                    idpadre = int(encrypt(request.POST['idpadre']))
                    idservicio = int(request.POST['servicio'])
                    form = ProcesoForm(request.POST)
                    if form.is_valid() and form.validador(idservicio,filtro.id):
                        filtro.servicio_id = int(idservicio)
                        filtro.descripcion = form.cleaned_data['descripcion']
                        filtro.subtitulo = form.cleaned_data['subtitulo']
                        filtro.tipo_proceso = form.cleaned_data['tipo_proceso']
                        filtro.mostrar = form.cleaned_data['mostrar']
                        filtro.tipoinforme = form.cleaned_data['tipoinforme']
                        filtro.save(request)
                        log(u'Edito Proceso de Citas: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse(
                            {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'delproceso':
            with transaction.atomic():
                try:
                    instancia = Proceso.objects.get(pk=int(encrypt(request.POST['id'])))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino proceso de citas: %s' % instancia, request, "del")
                    res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        if action == 'mostrarserviciopro':
            with transaction.atomic():
                try:
                    registro = Proceso.objects.get(pk=request.POST['id'])
                    registro.mostrar = eval(request.POST['val'].capitalize())
                    registro.save(request)
                    log(u'Mostrar proceso: %s (%s)' % (registro, registro.mostrar), request, "edit")
                    return JsonResponse({"result": True, 'mensaje': 'Cambios guardados'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False})

        # Responsables
        if action == 'addresponsable':
            with transaction.atomic():
                try:
                    idservicio = int(encrypt(request.POST['id']))
                    form = ResponsableServicioForm(request.POST)
                    if form.is_valid():
                        responsable = ResponsableServicioCita(servicio_id=idservicio,
                                                              responsable=form.cleaned_data['responsable'],
                                                              tipo=form.cleaned_data['tipo'],
                                                              activo=True)
                        responsable.save(request)
                        log(u'Agrego Responsable a Servicio: %s' % responsable, request, "add")
                        diccionario = {'id': responsable.id,
                                       'responsable': str(responsable.responsable),
                                       'foto': responsable.responsable.get_foto(),
                                       'tipo': responsable.tipo,
                                       'activo': responsable.activo,
                                       }
                        return JsonResponse({'result': True, 'data_return': True, 'mensaje': u'Guardado con exito',
                                             'data': diccionario, })
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'editresponsable':
            with transaction.atomic():
                try:
                    if 'id' in request.POST:
                        responsable = ResponsableServicioCita.objects.get(pk=int(request.POST['id']))
                        responsable.activo = eval(request.POST['val'].capitalize())
                        responsable.save(request)
                        log(u'Edito estado de responsable : %s (%s)' % (responsable, responsable.activo), request,
                            "edit")

                    if 'ids' in request.POST:
                        responsable = ResponsableServicioCita.objects.get(pk=int(request.POST['ids']))
                        responsable.tipo = int(request.POST['val'])
                        responsable.save(request)
                        log(u'Edito tipo de responsable : %s (%s)' % (responsable, responsable.activo), request,
                            "edit")
                    return JsonResponse({"result": True, 'mensaje': 'Cambios guardados'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': False, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'delresponsable':
            with transaction.atomic():
                try:
                    instancia = ResponsableServicioCita.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino responsable de servicio: %s' % instancia, request, "del")
                    res_json = {"error": False, "mensaje": 'Registro eliminado'}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        # Requisitos Servicio
        if action == 'addrequisitoservicio':
            with transaction.atomic():
                try:
                    idservicio = int(encrypt(request.POST['id']))
                    form = RequisitoServicioForm(request.POST)
                    if form.is_valid() and form.validador(idservicio):
                        requisito = RequisitoServicioCita(servicio_id=idservicio,
                                                          requisito=form.cleaned_data['requisito'],
                                                          # opcional=form.cleaned_data['opcional'],
                                                          # archivo=form.cleaned_data['archivo'],
                                                          mostrar=True)
                        requisito.save(request)
                        diccionario = {'id': requisito.id,
                                       'idservicio': requisito.servicio.id,
                                       'requisito': requisito.requisito.nombre,
                                       'opcional': requisito.opcional,
                                       'archivo': requisito.archivo,
                                       'mostrar': requisito.mostrar,
                                       }
                        log(u'Agrego Requisito a Servicio: %s' % requisito, request, "add")
                        return JsonResponse({'result': True, 'data_return': True, 'mensaje': u'Guardado con exito',
                                             'data': diccionario})
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'editrequisitoservicio':
            with transaction.atomic():
                try:
                    requisito = RequisitoServicioCita.objects.get(pk=int(request.POST['id']))
                    if request.POST['name'] == 'mostrar':
                        requisito.mostrar = eval(request.POST['val'].capitalize())
                        requisito.save(request)
                        log(u'Edito estado mostrar de requisito : %s (%s)' % (requisito, requisito.mostrar), request,
                            "edit")

                    if request.POST['name'] == 'opcional':
                        requisito.opcional = eval(request.POST['val'].capitalize())
                        requisito.save(request)
                        log(u'Edito estado opcional de requisito : %s (%s)' % (requisito, requisito.opcional), request,
                            "edit")

                    if request.POST['name'] == 'archivo':
                        requisito.archivo = eval(request.POST['val'].capitalize())
                        requisito.save(request)
                        log(u'Edito estado archivo de requisito : %s (%s)' % (requisito, requisito.archivo), request,
                            "edit")

                    return JsonResponse({"result": True, 'mensaje': 'Cambios guardados'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': False, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'delrequisitoservicio':
            with transaction.atomic():
                try:
                    instancia = RequisitoServicioCita.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino requisito de servicio: %s' % instancia, request, "del")
                    res_json = {"error": False, "mensaje": 'Registro eliminado'}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        # Estructura de informe

        if action == 'saveEstructurainforme':
            with transaction.atomic():
                try:
                    id = request.POST.get('id', '0')  # Obtener el id del registro o 0 si no existe
                    try:
                        estructura = EstructuraInforme.objects.get(pk=id)
                        estructura.titulo = request.POST['titulo']
                        estructura.tipoinforme = request.POST['tipoinforme']
                        estructura.orden = request.POST['orden']
                        estructura.segmentacion = request.POST['segmentacion']
                        estructura.seccion = request.POST['seccion']
                        mensaje = 'Registro editado con éxito'
                    except EstructuraInforme.DoesNotExist:
                        estructura = EstructuraInforme(
                            servicio_id=int(encrypt(request.POST['servicio_id'])),
                            titulo=request.POST['titulo'],
                            tipoinforme=request.POST['tipoinforme'],
                            orden=request.POST['orden'],
                            segmentacion=request.POST['segmentacion'],
                            seccion=request.POST['seccion'],
                            activo=True if request.POST.get('activo') else False
                        )
                        mensaje = 'Nuevo registro creado con éxito'
                    estructura.save(request)
                    diccionario = {
                        'id': encrypt(estructura.id),  # Encripta el id para devolverlo al frontend
                        'titulo': estructura.titulo,
                        'tipoinforme': estructura.get_tipoinforme_display(),
                        'orden': estructura.orden,
                        'activo': estructura.activo,
                    }

                    return JsonResponse({'result': True, 'mensaje': mensaje, 'data': diccionario})

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': False, 'mensaje': 'Error: {}'.format(ex)}, safe=False)

        if action == 'editestructurainforme':
            with transaction.atomic():
                try:
                    id = int(request.POST['id'])

                    value = False
                    if (request.POST['val'] == 'false'):
                        value = False
                    else:
                        value = True
                    instancia = EstructuraInforme.objects.get(pk=id)
                    if request.POST['name'] == 'activo':
                        instancia.activo = eval(request.POST['val'].capitalize())
                    # instancia.activo = value
                    instancia.save(request)
                    log(u'Actualizo el estado de Estructura Informe: %s' % instancia, request, "edit")
                    return JsonResponse({"result": True, 'mensaje': 'Cambios guardados'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)


        if action == 'delestructurainforme':
            with transaction.atomic():
                try:
                    id = int(encrypt(request.POST['id']))
                    instancia = EstructuraInforme.objects.get(pk=id)
                    instancia.activo = False
                    instancia.save(request)
                    log(u'Elimino la estructura del informe: %s' % instancia, request, "del")
                    return JsonResponse({"result": True, 'mensaje': 'Cambios guardados'})
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                    return JsonResponse(res_json, safe=False)

        # Horarios
        if action == 'addhorario':
            with transaction.atomic():
                try:
                    turno, dia, servicio = int(encrypt(request.POST['idturno'])), \
                                           int(request.POST.get('dia', 0)), \
                                           int(encrypt(request.POST['idservicio']))
                    serviciocita = ServicioConfigurado.objects.get(id=servicio).serviciocita
                    form = HorarioServicioForm(request.POST)
                    if form.is_valid() and form.validador(0, servicio, dia, turno):
                        tipo_atencion = form.cleaned_data['tipo_atencion']
                        if serviciocita.tipo_atencion != 0:
                            tipo_atencion = serviciocita.tipo_atencion
                        instancia = HorarioServicioCita(responsableservicio=form.cleaned_data['responsableservicio'],
                                                        servicio_id=servicio,
                                                        turno_id=turno,
                                                        dia=dia,
                                                        fechainicio=form.cleaned_data['fechainicio'],
                                                        fechafin=form.cleaned_data['fechafin'],
                                                        tipo_atencion=tipo_atencion,
                                                        mostrar=form.cleaned_data['mostrar'])
                        instancia.save(request)
                        log(u'Adiciono horario en Servicio: %s [%s]' % (instancia, instancia.id), request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'edithorario':
            with transaction.atomic():
                try:
                    filtro = HorarioServicioCita.objects.get(pk=int(encrypt(request.POST['id'])))
                    servicio = filtro.servicio.serviciocita
                    f = HorarioServicioForm(request.POST)
                    if f.is_valid() and f.validador(filtro.id, filtro.responsableservicio.servicio.id, filtro.dia,
                                                    filtro.turno.id):

                        tipo_atencion = f.cleaned_data['tipo_atencion']
                        if servicio.tipo_atencion != 0:
                            tipo_atencion = servicio.tipo_atencion
                        filtro.fechainicio = f.cleaned_data['fechainicio']
                        filtro.fechafin = f.cleaned_data['fechafin']
                        filtro.responsableservicio = f.cleaned_data['responsableservicio']
                        filtro.mostrar = f.cleaned_data['mostrar']
                        filtro.tipo_atencion = tipo_atencion
                        filtro.save(request)

                        log(u'Edito horario: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'delhorario':
            with transaction.atomic():
                try:
                    instancia = HorarioServicioCita.objects.get(pk=int(encrypt(request.POST['id'])))

                    if instancia.en_uso():
                        res_json = {'error': True, "message": "Error: en uso"}
                        return JsonResponse(res_json, safe=False)

                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino horario de servicio: %s' % instancia, request, "del")
                    res_json = {"error": False, "mensaje": 'Registro eliminado'}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        if action == 'mostrarhorario':
            with transaction.atomic():
                try:
                    registro = HorarioServicioCita.objects.get(pk=int(request.POST['id']))
                    registro.mostrar = eval(request.POST['val'].capitalize())
                    registro.save(request)
                    log(u'Turno activo : %s (%s)' % (registro, registro.mostrar), request, "edit")
                    return JsonResponse({"result": True, 'mensaje': 'Cambios guardados'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False})

        #  NOTICIAS

        elif action == 'addnoticiavincula':
            with transaction.atomic():
                try:
                    idpadre = encrypt_id(request.POST['idpadre'])
                    form = NoticiaVinculaForm(request.POST, request.FILES, idpadre=idpadre)

                    if not form.is_valid():
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario, revise todos los campos"})

                    instancia = NoticiasVinculacion(departamentoservicio_id=idpadre,
                                                    titulo=form.cleaned_data['titulo'],
                                                    tipopuplicacion=form.cleaned_data['tipopuplicacion'],
                                                    estadowebinar=form.cleaned_data['estadowebinar'],
                                                    subtitulo=form.cleaned_data['subtitulo'],
                                                    descripcion=form.cleaned_data['descripcion'],
                                                    principal=form.cleaned_data['principal'],
                                                    portada=form.cleaned_data['portada'],
                                                    publicado=form.cleaned_data['publicado'],
                                                    )
                    instancia.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        extension = newfile._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if newfile.size > 4194304:
                            transaction.set_rollback(True)
                            return JsonResponse(
                                {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 2 Mb."})
                        if not exte.lower() in ['pdf']:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf"})
                        newfile._name = generar_nombre(
                            "Test_Aplicado_{}_{}".format(instancia.pk,
                                                         random.randint(1, 100000).__str__()),
                            newfile._name)
                        instancia.archivo = newfile
                        instancia.save(request)
                    log(f'Adiciono noticia nueva {instancia}', request, 'add')
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        elif action == 'editnoticiavincula':
            with transaction.atomic():
                try:
                    instancia = NoticiasVinculacion.objects.get(id=encrypt_id(request.POST['id']))
                    idpadre = request.POST['idpadre']
                    form = NoticiaVinculaForm(request.POST, request.FILES, instancia=instancia)
                    if not form.is_valid():
                        # if 'archivo' in request.FILES:
                        #     newfile = request.FILES['archivo']
                        #     newfile._name = generar_nombre(instancia.nombre_input(), newfile._name)
                        #     instancia.archivo = newfile
                        #     instancia.save(request)
                        # instancia.save()

                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "message": "Error en el formulario"})

                    instancia.titulo = form.cleaned_data['titulo']
                    instancia.tipopuplicacion = form.cleaned_data['tipopuplicacion']
                    instancia.estadowebinar= form.cleaned_data['estadowebinar']
                    instancia.subtitulo = form.cleaned_data['subtitulo']
                    instancia.descripcion = form.cleaned_data['descripcion']
                    instancia.principal = form.cleaned_data['principal']
                    instancia.portada = form.cleaned_data['portada']
                    instancia.publicado = form.cleaned_data['publicado']
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre(instancia.nombre_input(), newfile._name)
                        instancia.archivo = newfile

                        # Guardar la instancia después de aplicar los cambios
                    instancia.save()
                    # instancia.save(request)
                    log(f'Edito noticia {instancia}', request, 'edit')
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        elif action == 'delnoticiavincula':
            try:
                with transaction.atomic():
                    instancia = NoticiasVinculacion.objects.get(pk=encrypt_id(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó noticia: %s' % instancia, request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'publicarnoticiavincula':
            with transaction.atomic():
                try:
                    instancia = NoticiasVinculacion.objects.get(id=encrypt_id(request.POST['id']))
                    if not instancia.publicado and not instancia.puede_cambiar_tipo_original_publicacion():
                        raise NameError(
                            'No puede se puede publicar noticia principal por que solo se admiten hasta 3 noticias principales y ya existen 3 noticias principales vigentes')
                    instancia.publicado = not instancia.publicado
                    instancia.save(request)
                    log(f'Edito noticia {instancia}', request, 'edit')
                    return JsonResponse({'result': 'ok', 'mensaje': u'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)
        # CAMBIAR TIPO DE NOTICIAS

        elif action == 'cambiartipovin':
            with transaction.atomic():
                try:
                    instancia = NoticiasVinculacion.objects.get(id=encrypt_id(request.POST['id']))
                    if not instancia.puede_cambiar_tipo():
                        raise NameError(
                            'No puede ser una noticia principal por que solo se admiten hasta 3 noticias principales y ya existen 3 noticias principales vigentes')
                    instancia.principal = not instancia.principal
                    instancia.save(request)
                    log(f'Edito noticia {instancia}', request, 'edit')
                    return JsonResponse({'result': 'ok', 'mensaje': u'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

                # GRUPO RESPONSABLE

        elif action == 'addgruporesponsable':
            try:
                with transaction.atomic():
                    form = ResponsableServicioCitaForm(request.POST)
                    idpadre = encrypt_id(request.POST['idpadre'])
                    if form.is_valid():
                        if ResponsableGrupoServicio.objects.filter(responsable=int(request.POST['responsable']), status=True, activo=True).exists():
                            return JsonResponse({'result': True, "mensaje": 'Registro ya existe.'}, safe=False)
                        persona = Persona.objects.get(id=int(request.POST['responsable']))
                        instance = ResponsableGrupoServicio(departamentoservicio_id=idpadre,
                                                            responsable=persona,
                                                            activo=form.cleaned_data['activo'],
                                                            descripcion=form.cleaned_data['descripcion'],
                                                            cargo= form.cleaned_data['cargo'],
                                                            abreviatura=form.cleaned_data['abreviatura']
                                                            )
                        instance.save(request)
                        log(u'Adiciono grupo responsable: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': 'bad', "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, "mensaje": 'Intentelo más tarde.'}, safe=False)


        elif action == 'editgruporesponsable':
            try:
                with transaction.atomic():
                    id = encrypt_id(request.POST['id'])
                    idpadre = request.POST['idpadre']
                    instance = ResponsableGrupoServicio.objects.get(id=id)
                    form = ResponsableServicioCitaForm(request.POST)
                    if not form.is_valid():
                        return JsonResponse({'result': 'bad', "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                    persona = Persona.objects.get(id=int(request.POST['responsable']))
                    # if ResponsableGrupoServicio.objects.filter(responsable=persona,
                    #                                            departamentoservicio_id=idpadre).exclude(
                    #         id=instance.id).exists():
                    #     return JsonResponse({'result': True, "mensaje": 'Registro ya existe en este grupo.'},
                    #                         safe=False)
                    if ResponsableGrupoServicio.objects.filter(responsable=persona, status=True, activo=True).exclude(id=instance.id).exists():
                        return JsonResponse({'result': True, "mensaje": 'Registro ya existe.'}, safe=False)

                    instance.responsable = persona
                    instance.activo = form.cleaned_data['activo']
                    instance.descripcion = form.cleaned_data['descripcion']
                    instance.cargo = form.cleaned_data['cargo']
                    instance.abreviatura = form.cleaned_data['abreviatura']
                    instance.save(request)
                    log(u'Edito responsable : %s' % instance, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, "mensaje": 'Intentelo más tarde.'}, safe=False)

        elif action == 'delgruporesponsable':
            try:
                with transaction.atomic():
                    instancia = ResponsableGrupoServicio.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Responsable: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'activagruporesponsable':
            try:
                registro = ResponsableGrupoServicio.objects.get(pk=request.POST['id'])
                registro.activo = True if request.POST['val'] == 'y' else False
                registro.save(request)
                log(u'Responsable activo : %s (%s)' % (registro, registro.activo), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

                # SITIO WEB MULTISERVICIO

        elif action == 'editsecciontitulo':
            with transaction.atomic():
                try:
                    id = encrypt_id(request.POST['id'])
                    form = TituloWebSiteServicioForm(request.POST, request.FILES)
                    if not form.is_valid():
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "message": "Error en el formulario"})

                    instancia = TituloWebSiteServicio.objects.get(id=id)
                    newfile = request.FILES.get('fondotitulo', None)
                    if newfile:
                        extension = newfile._name.split('.')
                        exte = extension[len(extension) - 1]
                        if newfile.size > 2194304:
                            raise NameError(u"El tamaño del archivo es mayor a 2 Mb.")
                        if not exte.lower() in ['png', 'jpg', 'jpeg']:
                            raise NameError(u"Solo se permite archivos de formato .png, .jpg, .jpeg")
                        newfile._name = generar_nombre(f'Fondo_', newfile._name)
                        instancia.fondotitulo = newfile
                    instancia.titulo = form.cleaned_data['titulo']
                    instancia.subtitulo = form.cleaned_data['subtitulo']
                    instancia.publicado = form.cleaned_data['publicado']
                    instancia.save(request)
                    log(f'Edito titulo de cabecera {instancia}', request, 'edit')
                    return JsonResponse(
                        {'result': False, 'to': f'{request.path}?action=sitioweb&idp={encrypt(instancia.departamentoservicio_id)}',
                         'mensaje': u'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        elif action == 'addcuerposervicio':
            with transaction.atomic():
                try:
                    idp = encrypt_id(request.POST['idp'])
                    form = CuerpoWebSiteServicioForm(request.POST)
                    if not form.is_valid():
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "message": "Error en el formulario"})

                    instancia = CuerpoWebSiteServicio(titulowebsite_id=idp,
                                                      titulo=form.cleaned_data['titulo'],
                                                      descripcion=form.cleaned_data['descripcion'],
                                                      ubicacion=form.cleaned_data['ubicacion'],
                                                      orden=form.cleaned_data['orden'],
                                                      publicado=form.cleaned_data['publicado'],
                                                      )
                    instancia.save(request)
                    log(f'Adiciono cuerpo de sitio web {instancia}', request, 'add')
                    return JsonResponse({'result': False,
                                         'to': f'{request.path}?action=sitioweb&idp={encrypt(instancia.titulowebsite.departamentoservicio_id)}',
                                         'mensaje': u'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        elif action == 'editcuerposervicio':
            with transaction.atomic():
                try:
                    id = encrypt_id(request.POST['id'])
                    form = CuerpoWebSiteServicioForm(request.POST)
                    if not form.is_valid():
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
                    instancia = CuerpoWebSiteServicio.objects.get(id=id)
                    instancia.titulo = form.cleaned_data['titulo']
                    instancia.descripcion = form.cleaned_data['descripcion']
                    # instancia.ubicacion = form.cleaned_data['ubicacion']
                    instancia.orden = form.cleaned_data['orden']
                    instancia.publicado = form.cleaned_data['publicado']
                    instancia.save(request)
                    log(f'Edito cuerpo de sitio web {instancia}', request, 'edit')
                    return JsonResponse({'result': False,
                                         'to': f'{request.path}?action=sitioweb&idp={encrypt(instancia.titulowebsite.departamentoservicio_id)}',
                                         'mensaje': u'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        elif action == 'delcuerposervicio':
            try:
                with transaction.atomic():
                    instancia = CuerpoWebSiteServicio.objects.get(pk=int(encrypt(request.POST['id'])))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó Cuerpo de sitio web: %s' % instancia, request, "del")
                    res_json = {"error": False,'to': f'{request.path}?action=sitioweb&idp={encrypt(instancia.titulowebsite.departamentoservicio_id)}'}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addterminosvin':
            try:
                with transaction.atomic():
                    form = TerminosCondicionForm(request.POST)
                    if form.is_valid():
                        instance = TerminosCondicion(
                            nombre=form.cleaned_data['nombre'],
                            descripcion=form.cleaned_data['descripcion'],
                            mostrar=form.cleaned_data['mostrar'],
                            general=form.cleaned_data['general'])
                        instance.save(request)
                        for servicio in form.cleaned_data['servicio']:
                            instance.servicio.add(servicio)
                        log(u'Adicionó termino & condiciones agendamiento de cita: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editterminosvin':
            try:
                with transaction.atomic():
                    filtro = TerminosCondicion.objects.get(pk=request.POST['id'])
                    f = TerminosCondicionForm(request.POST)
                    if f.is_valid():
                        filtro.nombre = request.POST['nombre']
                        filtro.descripcion = request.POST['descripcion']
                        if 'mostrar' in request.POST:
                            filtro.mostrar = True
                        else:
                            filtro.mostrar = False
                        if 'general' in request.POST:
                            filtro.general = True
                        else:
                            filtro.general = False
                        filtro.servicio.clear()
                        for servicio in f.cleaned_data['servicio']:
                            filtro.servicio.add(servicio)
                        filtro.save(request)
                        log(u'Edito termino & condición de Agendamiento de cita: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'mostrarterminovic':
            try:
                with transaction.atomic():
                    termino = TerminosCondicion.objects.get(id=request.POST['id'])
                    termino.mostrar = eval(request.POST['val'])
                    termino.save(request)
                    log(u'Edito termino & condición agendamiento de cita: %s' % termino, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deleteterminovic':
            try:
                with transaction.atomic():
                    instancia = TerminosCondicion.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó termino & condición de agendamiento de cita: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addimagenesdepartamento':
            with transaction.atomic():
                try:
                    form = CargaImgvinForm(request.POST)
                    idpadre = int(encrypt(request.POST['idpadre']))
                    if form.is_valid() and form.validador(idpadre):
                        instancia = CargaImgvin(departamentoservicio_id=idpadre,
                                                descripcion=form.cleaned_data['descripcion'])
                        instancia.save(request)

                        if 'imagen' in request.FILES:
                            newfile = request.FILES['imagen']
                            newfile._name = generar_nombre(instancia.imagen_input(newfile.name), newfile._name)
                            instancia.imagen = newfile
                            instancia.save(request)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse(
                            {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                             "mensaje": "Error en el formulario"})
                    log(u'Adiciono la imagen correctamente: %s' % instancia, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'editimagenesdepartamento':
            with transaction.atomic():
                try:
                    filtro = CargaImgvin.objects.get(pk=int(encrypt(request.POST['id'])))
                    idpadre = int(encrypt(request.POST['idpadre']))
                    form = CargaImgvinForm(request.POST)
                    if form.is_valid() and form.validador(idpadre, filtro.id):
                        if 'imagen' in request.FILES:
                            newfile = request.FILES['imagen']
                            newfile._name = generar_nombre(filtro.nombre_input(), newfile._name)
                            filtro.imagen = newfile
                            filtro.save(request)
                        filtro.descripcion = form.cleaned_data['descripcion']
                        # filtro.identificador = form.cleaned_data['identificador']
                        filtro.save(request)
                        log(u'Edito Galeria de imagen: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse(
                            {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'delimagenesdepartamento':
            with transaction.atomic():
                try:
                    instancia = CargaImgvin.objects.get(pk=int(encrypt(request.POST['id'])))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino una imagen de la galeria: %s' % instancia, request, "del")
                    res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            # Departamento Servicios
            if action == 'addserviciodep':
                try:
                    form = DepartamentoServicioForm()
                    # form.fields['responsable'].queryset = Persona.objects.none()
                    form.fields['gestion'].queryset = SeccionDepartamento.objects.none()
                    data['form'] = form
                    template = get_template("adm_agendamientocitas/modal/formdepartamentoservicio.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'listgestiones':
                try:
                    lista = []
                    id = int(request.GET['id'])
                    gestiones = SeccionDepartamento.objects.filter(status=True, departamento=id).distinct()
                    for s in gestiones:
                        text = str(s)
                        lista.append({'value': s.id, 'text': text})
                    return JsonResponse({'result': True, 'data': lista})
                except Exception as e:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'editserviciodep':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = DepartamentoServicio.objects.get(pk=id)
                    form = DepartamentoServicioForm(initial=model_to_dict(filtro))
                    form.fields['gestion'].queryset = SeccionDepartamento.objects.filter(status=True,
                                                                                         departamento=filtro.departamento)
                    # form.fields['responsable'].queryset = Persona.objects.filter(id=filtro.responsable.id)
                    # form.fields['responsable'].queryset = Persona.objects.filter(id__in=filtro.responsable.all().values_list('id', flat=True))

                    data['form'] = form
                    template = get_template("adm_agendamientocitas/modal/formdepartamentoservicio.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            # Servicios
            if action == 'servicios':
                try:
                    data['title'] = u'Servicios'
                    data['idpadre'] = iddpservicio = int(encrypt(request.GET['id']))
                    search, filtro, url_vars = (request.GET.get('s', ''), Q(status=True,
                                                                            departamentoservicio_id=iddpservicio),
                                                f'&action={action}&id={encrypt(iddpservicio)}')

                    if not permiso and not es_director_gestion and not es_director:
                        filtro = filtro & (Q(id__in=ids_servicios_responsable(persona)))

                    if search:
                        filtro = filtro & (Q(nombre__unaccent__icontains=search))
                        url_vars += '&s=' + search
                        data['s'] = search

                    listado = ServicioCita.objects.filter(filtro)
                    paging = MiPaginador(listado, 10)
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
                    data["url_vars"] = url_vars
                    data['listado'] = page.object_list
                    data['listcount'] = len(listado)
                    data['dpservicio'] = DepartamentoServicio.objects.get(id=iddpservicio)
                    request.session['viewactivo'] = 1
                    return render(request, 'adm_agendamientocitas/viewservicios.html', data)
                except Exception as ex:
                    return render({'result': False, 'mensaje': '{}'.format(ex)})

            if action == 'addservicio':
                try:
                    form = ServicioCitaForm()
                    form.fields['responsable'].queryset = Persona.objects.none()
                    data['idpadre'] = request.GET['idp']
                    data['form'] = form
                    template = get_template("adm_agendamientocitas/modal/formservicio.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editservicio':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = ServicioCita.objects.get(pk=id)
                    # Crear una instancia de ServicioCitaForm
                    form = ServicioCitaForm(initial=model_to_dict(filtro))
                    # Verificar si el campo 'responsable' es None y asignar un valor predeterminado si es necesario
                    if filtro.responsable is None:
                        form.fields['responsable'].queryset = Persona.objects.none()
                    else:
                        form.fields['responsable'].queryset = Persona.objects.filter(id=filtro.responsable.id)

                    data['form'] = form
                    template = get_template("adm_agendamientocitas/modal/formservicio.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            # Configuración de servicios
            if action == 'serviciosconfigurados':
                try:
                    data['title'] = u'Servicios | Configuración'
                    data['idpadre'] = idservicio = int(encrypt(request.GET['id']))
                    servicio = ServicioCita.objects.get(id=idservicio)
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True,
                                                                           serviciocita=servicio), f'&action={action}&id={encrypt(servicio.id)}'
                    if search:
                        data['s'] = search
                        filtro = filtro & (Q(nombre__unaccent__icontains=search))
                        url_vars += '&s=' + search

                    listado = ServicioConfigurado.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(listado, 10)
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

                    data["url_vars"] = url_vars
                    data['listado'] = page.object_list
                    data['listcount'] = len(listado)
                    data['filtro'] = servicio
                    request.session['viewactivo'] = 1
                    return render(request, 'adm_agendamientocitas/viewconfservicio.html', data)
                except Exception as ex:
                    return render({'result': False, 'mensaje': '{}'.format(ex)})

            if action == 'addservicioconf':
                try:
                    form = ServicioConfiguradoForm()
                    # form.fields['responsable'].queryset = Persona.objects.none()
                    data['form'] = form
                    data['idpadre'] = id = int(request.GET['idp'])
                    data['cantidad'] = len(ServicioConfigurado.objects.filter(status=True, serviciocita_id=id)) + 1
                    template = get_template("adm_agendamientocitas/modal/formservicioconf.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editservicioconf':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = ServicioConfigurado.objects.get(pk=id)
                    form = ServicioConfiguradoForm(initial=model_to_dict(filtro))
                    # form.fields['responsable'].queryset = Persona.objects.none()
                    data['form'] = form
                    template = get_template("adm_agendamientocitas/modal/formservicioconf.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'buscarpersonas':
                try:
                    resp = filtro_persona_select(request)
                    return HttpResponse(json.dumps({'status': True, 'results': resp}))
                except Exception as ex:
                    pass

            if action == 'buscarpersonaservicio':
                try:
                    resp = consultaPersonaDepartamento(request)
                    return HttpResponse(json.dumps({'status': True, 'results': resp}))
                except Exception as ex:
                    pass

            # Turnos
            if action == 'turnos':
                try:
                    data['title'] = u'Turnos'
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), f'&action={action}'
                    if search:
                        filtro = filtro & (Q(comienza__icontains=search) | Q(termina__icontains=search))
                        url_vars += '&s=' + search
                        data['s'] = search

                    listado = TurnoCita.objects.filter(filtro).order_by('comienza')
                    paging = MiPaginador(listado, 10)
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
                    data["url_vars"] = url_vars
                    data['listado'] = page.object_list
                    data['listcount'] = len(listado)
                    request.session['viewactivo'] = 2
                    return render(request, 'adm_agendamientocitas/viewturno.html', data)
                except Exception as ex:
                    return render({'result': False, 'mensaje': '{}'.format(ex)})

            if action == 'addturno':
                try:
                    form = TurnoCitaForm()
                    data['form'] = form
                    template = get_template("adm_agendamientocitas/modal/formturno.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editturno':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = TurnoCita.objects.get(pk=request.GET['id'])
                    form = TurnoCitaForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("adm_agendamientocitas/modal/formturno.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            # Requisitos
            if action == 'requisitos':
                try:
                    data['title'] = u'Requisitos'
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
                    if search:
                        filtro = filtro & (Q(nombre__unaccent__icontains=search))
                        url_vars += '&s=' + search
                        data['s'] = search

                    listado = Requisito.objects.filter(filtro)
                    paging = MiPaginador(listado, 10)
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
                    data["url_vars"] = url_vars
                    data['listado'] = page.object_list
                    data['listcount'] = len(listado)
                    request.session['viewactivo'] = 3
                    return render(request, 'adm_agendamientocitas/viewrequisitos.html', data)
                except Exception as ex:
                    return render({'result': False, 'mensaje': '{}'.format(ex)})

            if action == 'addrequisito':
                try:
                    form = RequisitoForm()
                    data['form'] = form
                    template = get_template("adm_agendamientocitas/modal/formrequisito.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editrequisito':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    requisito = Requisito.objects.get(pk=id)
                    form = RequisitoForm(initial=model_to_dict(requisito))
                    data['form'] = form
                    template = get_template("adm_agendamientocitas/modal/formrequisito.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            # CARD INFORMATIVO VISTA
            elif action == 'alertainformacion':
                try:
                    data['title'] = 'Configuración de Alertas Informativas'
                    data['idpadre'] = iddpservicio = int(encrypt(request.GET['idp']))
                    data['card'] = card = CardInformativo.objects.filter(departamentoservicio__id=iddpservicio).last() #CardInformativo.objects.last()
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True,
                                                                           departamentoservicio_id=iddpservicio), \
                                               f'&action={action}&idp={encrypt(iddpservicio)}'
                    # search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), f'&action={action}'
                    if search:
                        data['search'] = search.strip()
                        filtro = filtro & Q(titulo__icontains=search) | Q(subtitulo__icontains=search)
                        url_vars += '&s=' + search
                    listado = NoticiasVinculacion.objects.filter(filtro).order_by('-principal', '-fecha_creacion')
                    paging = MiPaginador(listado, 20)
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
                    data["url_vars"] = url_vars
                    data['listado'] = page.object_list
                    request.session['viewactivo'] = 10
                    return render(request, 'adm_agendamientocitas/cardinformativowebsite.html', data)
                except Exception as ex:
                    return render({'result': False, 'mensaje': '{}'.format(ex)})

            elif action == 'imagendepartamento':
                try:
                    data['title'] = u'Galeria de Imagenes'
                    data['idpadre'] = iddpservicio = int(encrypt(request.GET['idp']))
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True,
                                                                           departamentoservicio_id=iddpservicio), f'&action={action}&idp={encrypt(iddpservicio)}'

                    if search:
                        filtro = filtro & (Q(descripcion__unaccent__icontains=search) | Q(identificador__unaccent__icontains=search))
                        url_vars += '&s=' + search
                        data['s'] = search

                    listado = CargaImgvin.objects.filter(filtro)
                    paging = MiPaginador(listado, 10)
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
                    # data['idp'] = iddpservicio
                    data["url_vars"] = url_vars
                    # data['dpservicio'] = DepartamentoServicio.objects.get(idp=iddpservicio)
                    data['listado'] = page.object_list
                    data['listcount'] = len(listado)
                    request.session['viewactivo'] = 5
                    return render(request, 'adm_agendamientocitas/viewimagenes.html', data)
                except Exception as ex:
                    return render({'result': False, 'mensaje': '{}'.format(ex)})


            # Motivo de Cita
            if action == 'motivocita':
                try:
                    data['title'] = u'Motivos de Citas'
                    data['idpadre'] = iddpservicio = int(encrypt(request.GET['idp']))
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True,
                                                                           departamentoservicio_id=iddpservicio), f'&action={action}&idp={encrypt(iddpservicio)}'

                    if search:
                        filtro = filtro & (Q(descripcion__unaccent__icontains=search))
                        url_vars += '&s=' + search
                        data['s'] = search

                    listado = MotivoCita.objects.filter(filtro)
                    paging = MiPaginador(listado, 10)
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
                    # data['idp'] = iddpservicio
                    data["url_vars"] = url_vars
                    # data['dpservicio'] = DepartamentoServicio.objects.get(idp=iddpservicio)
                    data['listado'] = page.object_list
                    data['listcount'] = len(listado)
                    request.session['viewactivo'] = 5
                    return render(request, 'adm_agendamientocitas/viewmotivocita.html', data)
                except Exception as ex:
                    return render({'result': False, 'mensaje': '{}'.format(ex)})

            if action == 'addimagenesdepartamento':
                try:
                    form = CargaImgvinForm()
                    data['idpadre'] = request.GET['idp']
                    data['form'] = form
                    template = get_template("adm_agendamientocitas/modal/formimagenesdepartamento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editimagenesdepartamento':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['idpadre'] = request.GET['idp']
                    carimg = CargaImgvin.objects.get(pk=id)
                    form = CargaImgvinForm(initial=model_to_dict(carimg))
                    data['form'] = form
                    template = get_template("adm_agendamientocitas/modal/formimagenesdepartamento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addmotivocita':
                try:
                    form = MotivoCitaForm()
                    data['idpadre'] = request.GET['idp']
                    data['form'] = form
                    template = get_template("adm_agendamientocitas/modal/formmotivocita.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editmotivocita':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['idpadre']= request.GET['idp']
                    motivo = MotivoCita.objects.get(pk=id)
                    form = MotivoCitaForm(initial=model_to_dict(motivo))
                    data['form'] = form
                    template = get_template("adm_agendamientocitas/modal/formmotivocita.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            # Proceo de Cita
            if action == 'proceso':
                try:
                    data['title'] = u'Proceso de Citas'
                    data['idpadre'] = iddpservicio = int(encrypt(request.GET['idp']))
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True,
                                                                           servicio__departamentoservicio=iddpservicio), f'&action={action}&idp={encrypt(iddpservicio)}'

                    if search:
                        filtro = filtro & (Q(descripcion__unaccent__icontains=search))
                        url_vars += '&s=' + search
                        data['s'] = search

                    listado = Proceso.objects.filter(filtro)
                    paging = MiPaginador(listado, 10)
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
                    # data['idp'] = iddpservicio
                    data["url_vars"] = url_vars
                    # data['dpservicio'] = DepartamentoServicio.objects.get(idp=iddpservicio)
                    data['listado'] = page.object_list
                    data['listcount'] = len(listado)
                    request.session['viewactivo'] = 4
                    return render(request, 'adm_agendamientocitas/viewproceso.html', data)
                except Exception as ex:
                    return render({'result': False, 'mensaje': '{}'.format(ex)})

            if action == 'addproceso':
                try:
                    data['idpadre'] = request.GET['idp']
                    iddep = encrypt(data['idpadre'])
                    form = ProcesoForm(id_padre=iddep)
                    # form.fields['tipo_proceso'].choices = []
                    data['form'] = form
                    template = get_template("adm_agendamientocitas/modal/formproceso.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editproceso':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['idpadre'] = iddep = request.GET['idp']
                    proceso = Proceso.objects.get(pk=id)
                    form = ProcesoForm(initial=model_to_dict(proceso), id_padre=int(encrypt(iddep)))
                    data['form'] = form
                    template = get_template("adm_agendamientocitas/modal/formproceso.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            # # Sub Responsables

            if action == 'responsables':
                try:
                    data['filtro'] = servicio = ServicioConfigurado.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = ResponsableServicioForm()
                    # form.fields['responsable'].queryset = Persona.objects.none()
                    form.fields['responsable'].queryset =ResponsableGrupoServicio.objects.filter(status=True,
                                                                                                 departamentoservicio=servicio.serviciocita.departamentoservicio)
                    data['listado'] = servicio.responsables()
                    data['tipos'] = TIPO_RESPONSABLE[1:]
                    data['form'] = form
                    template = get_template("adm_agendamientocitas/modal/formresponsables.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            # Requisitos
            if action == 'requisitosservicio':
                try:
                    form = RequisitoServicioForm()
                    data['filtro'] = servicio = ServicioConfigurado.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['listado'] = servicio.requisitos()
                    data['form'] = form
                    data['requisitos'] = Requisito.objects.filter(status=True)
                    template = get_template("adm_agendamientocitas/modal/formrequisitoservicio.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'estructurainforme':
                try:
                    # Verificar si se está solicitando la edición de un registro
                    estructura_id = request.GET.get(
                        'estructura_id')  # Obtener el id del registro de EstructuraInforme (si existe)
                    if estructura_id:  # Si se está editando un registro existente
                        try:
                            estructura = EstructuraInforme.objects.get(pk=int(encrypt(estructura_id)))
                            # Preparar los datos para ser enviados al formulario
                            data = {
                                'id': estructura.id,
                                'titulo': estructura.titulo,
                                'orden': estructura.orden,
                                'tipoinforme': estructura.tipoinforme,
                                'activo': estructura.activo,
                                'segmentacion': estructura.segmentacion,
                                'seccion': estructura.seccion,
                            }
                            return JsonResponse({"result": True, 'data': data})
                        except EstructuraInforme.DoesNotExist:
                            return JsonResponse({"result": False, 'mensaje': 'No se encontró el registro.'})

                    else:  # Si es para cargar la lista de registros o crear un nuevo registro
                        form = EstructuraInformeForm()
                        data['filtro'] = servicio = ServicioCita.objects.get(pk=int(encrypt(request.GET['id'])))
                        # Traer todos los registros, sin filtrar por activo
                        data['listado'] = EstructuraInforme.objects.filter(servicio=servicio).order_by('orden')
                        data['form'] = form
                        template = get_template("adm_agendamientocitas/modal/formestructurainforme.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})

                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': 'Ocurrió un error.'})

            if action == 'listadoestructurainforme':
                try:
                    data['servicio'] = servicio = ServicioCita.objects.get(pk=int(encrypt(request.GET['id'])))
                    # Traer todos los registros, sin filtrar por activo
                    data['listado'] = EstructuraInforme.objects.filter(servicio=servicio).order_by('orden')
                    template = get_template("adm_agendamientocitas/modal/listadoestructurainforme.html")
                    return JsonResponse({"result": True, 'html': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': 'Ocurrió un error.'})
            # if action == 'estructurainforme':
            #     try:
            #         form = EstructuraInformeForm()
            #         data['filtro'] = servicio = ServicioCita.objects.get(pk=int(encrypt(request.GET['id'])))
            #         # Trae todos los registros, sin filtrar por activo
            #         data['listado'] = EstructuraInforme.objects.filter(servicio=servicio).order_by('orden')
            #         data['form'] = form
            #         template = get_template("adm_agendamientocitas/modal/formestructurainforme.html")
            #         return JsonResponse({"result": True, 'data': template.render(data)})
            #     except Exception as ex:
            #         pass


            # Horarios
            if action == 'horarios':
                try:
                    data['title'] = u'Servicio | Horarios'
                    servicio = ServicioConfigurado.objects.get(id=int(encrypt(request.GET['id'])))
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True,
                                                                           responsableservicio__servicio=servicio), ''
                    if search:
                        filtro = filtro & (Q(nombre__unaccent__icontains=search))
                        url_vars += '&s=' + search
                        data['s'] = search

                    listado = HorarioServicioCita.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(listado, 10)
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
                    data["url_vars"] = url_vars
                    data['listado'] = page.object_list
                    data['semana'] = DIAS_CHOICES
                    data['turnos'] = TurnoCita.objects.filter(status=True, mostrar=True).order_by('comienza')
                    data['servicio'] = servicio
                    request.session['viewactivo'] = 1
                    return render(request, 'adm_agendamientocitas/viewhorarios.html', data)
                except Exception as ex:
                    return render({'result': False, 'mensaje': '{}'.format(ex)})

            elif action == 'addhorario':
                try:
                    data['title'] = u'Adicionar Horario'
                    form = HorarioServicioForm()
                    data['idservicio'] = id = int(request.GET['idp'])
                    data['servicio'] = ServicioConfigurado.objects.get(id=id).serviciocita
                    data['dia'] = int(request.GET['idex'])
                    data['turno'] = int(request.GET['id'])

                    form.fields['responsableservicio'].queryset = ResponsableServicioCita.objects.filter(status=True, activo=True,
                                                                                                         servicio_id=id)
                    data['form'] = form
                    template = get_template("adm_agendamientocitas/modal/formhorario.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edithorario':
                try:
                    data['filtro'] = filtro = HorarioServicioCita.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['servicio'] = filtro.servicio.serviciocita

                    form = HorarioServicioForm(initial={
                        'responsableservicio': filtro.responsableservicio,
                        'fechainicio': filtro.fechainicio,
                        'fechafin': filtro.fechafin,
                        'mostrar': filtro.mostrar,
                        'tipo_atencion': filtro.tipo_atencion,
                    })
                    form.fields['responsableservicio'].queryset = ResponsableServicioCita.objects.filter(status=True,
                                                                                                         activo=True,
                                                                                                         servicio_id=filtro.servicio.id)
                    data['form'] = form
                    template = get_template("adm_agendamientocitas/modal/formhorario.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            # NOTICIAS
            elif action == 'noticiasvincula':
                try:
                    data['title'] = 'Noticias'
                    data['idpadre'] = iddpservicio = int(encrypt(request.GET['idp']))
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True,
                                                                           departamentoservicio_id=iddpservicio), \
                                               f'&action={action}&idp={encrypt(iddpservicio)}'
                    # search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), f'&action={action}'
                    if search:
                        data['search'] = search.strip()
                        filtro = filtro & Q(titulo__icontains=search) | Q(subtitulo__icontains=search)
                        url_vars += '&s=' + search
                    listado = NoticiasVinculacion.objects.filter(filtro).order_by('-principal', '-fecha_creacion')
                    paging = MiPaginador(listado, 20)
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
                    data["url_vars"] = url_vars
                    data['listado'] = page.object_list
                    request.session['viewactivo'] = 10
                    return render(request, 'adm_agendamientocitas/noticiasvincula.html', data)
                except Exception as ex:
                    return render({'result': False, 'mensaje': '{}'.format(ex)})

            elif action == 'addnoticiavincula':
                try:
                    form = NoticiaVinculaForm()
                    data['idpadre'] = encrypt_id(request.GET['id'])
                    visible_fields = form.visible_fields()
                    total_fields = len(visible_fields)
                    lista = [(1, 'Información Básica', visible_fields[:5]),
                             (2, 'Contenido', visible_fields[5:total_fields])
                             ]
                    data['form'] = lista
                    data['switchery'] = True
                    template = get_template('adm_agendamientocitas/modal/formnoticiavincula.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    messages.error(request, f'{ex}')

            elif action == 'editnoticiavincula':
                try:
                    data['id'] = id = encrypt_id(request.GET['id'])
                    # data['idpadre'] = encrypt_id(request.GET['id'])
                    # noticia = NoticiasVinculacion.objects.get(id=id)
                    noticia = NoticiasVinculacion.objects.get(id=id)
                    form = NoticiaVinculaForm(instancia=noticia, initial=model_to_dict(noticia))
                    visible_fields = form.visible_fields()
                    total_fields = len(visible_fields)
                    lista = [(1, 'Información Básica', visible_fields[:5]),
                             (2, 'Contenido', visible_fields[5:total_fields])
                             ]
                    data['form'] = lista
                    data['switchery'] = True
                    template = get_template('adm_agendamientocitas/modal/formnoticiavincula.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    messages.error(request, f'{ex}')
            # SITIO WEB
            elif action == 'sitioweb':
                try:
                    data['idpadre'] = iddpservicio = int(encrypt(request.GET['idp']))
                    departamento = DepartamentoServicio.objects.get(id=iddpservicio)
                    seccionactiva = request.GET.get('s_activa', 1)
                    titulos = TituloWebSiteServicio.objects.filter(departamentoservicio__id=iddpservicio, status=True)
                    data['title'] = u'Gestion'
                    if len(SECCION) > len(titulos):
                        for s in SECCION:
                            titulo = TituloWebSiteServicio.objects.filter(departamentoservicio__id=iddpservicio,
                                                                          status=True, seccion=s[0])
                            if not titulo.exists():

                                title = ''
                                subtitle = ''
                                if s[0] == 1:
                                    title = 'Acerca de nosotros'
                                    subtitle = '¡Conoce sobre el consultorio!'
                                elif s[0] == 2:
                                    title = 'Nuestros Áreas'
                                    subtitle = '¡Conoce nuestras Áreas!'
                                    if departamento.id == 11:
                                        title = 'Nuestros Proyectos'
                                        subtitle = '¡Conoce nuestros proyectos!'
                                elif s[0] == 3:
                                    title = 'Noticias Informativas'
                                    subtitle = '¡Conoce todas las noticias ocurridas en el consultorio!'
                                elif s[0] == 4:
                                    title = 'Nuestros Eventos'
                                    subtitle = '¡Conoce nuestros eventos!'
                                elif s[0] == 5:
                                    title = 'Nuestro Equipo'
                                    subtitle = '¡Explora Quiénes Somos en Nuestro Equipo de Trabajo!'


                                titulo = TituloWebSiteServicio(departamentoservicio=departamento, seccion=s[0],
                                                               titulo=title, subtitulo=subtitle)
                                titulo.save(request)
                    data['secciones'] = SECCION
                    data['departamento'] = departamento
                    data['s_activa'] = int(seccionactiva)
                    data['titulos'] = TituloWebSiteServicio.objects.filter(departamentoservicio__id=iddpservicio,
                                                                           status=True).order_by('seccion')
                    request.session['viewactivo'] = 9
                    return render(request, 'adm_agendamientocitas/sitioweb.html', data)
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    messages.error(request, f'{ex}')

            elif action == 'editsecciontitulo':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    titulo = TituloWebSiteServicio.objects.get(id=id)
                    data['switchery'] = True
                    form = TituloWebSiteServicioForm(initial=model_to_dict(titulo), instancia=titulo)
                    data['form'] = form
                    template = get_template("ajaxformmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': f'Error: {ex}'})

            elif action == 'addcuerposervicio':
                try:
                    data['idp'] = encrypt_id(request.GET['id'])
                    form = CuerpoWebSiteServicioForm()
                    form.fields['ubicacion'].initial = request.GET['idex']
                    data['form'] = form
                    data['switchery'] = True
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'editcuerposervicio':
                try:
                    data['id'] = id = encrypt_id(request.GET['id'])
                    cuerpo = CuerpoWebSiteServicio.objects.get(id=id)
                    form = CuerpoWebSiteServicioForm(instancia=cuerpo, initial=model_to_dict(cuerpo))
                    data['form'] = form
                    data['switchery'] = True
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'previsualizarnoticiavincula':
                try:
                    data['id'] = id = encrypt_id(request.GET['id'])
                    data['noticia'] = NoticiasVinculacion.objects.get(id=id)
                    template = get_template('adm_agendamientocitas/modal/previsualizarnoticiavincula.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')
            # CARD INFORMATIVO
            elif action == 'addcardinformativo':
                try:
                    ultimo_registro = CardInformativo.objects.last()
                    if ultimo_registro:
                        form_data = {
                            'departamentoservicio': ultimo_registro.departamentoservicio,
                            'titulo': ultimo_registro.titulo,
                            'subtitulo': ultimo_registro.subtitulo,
                            'fondo': ultimo_registro.fondo,
                            'cuerpoinformativa': ultimo_registro.cuerpoinformativa,
                            'orden': ultimo_registro.orden
                        }

                        # Verifica si hay una imagen asociada y pasa la URL al formulario
                        if ultimo_registro.imagen:
                            form_data['imagen'] = ultimo_registro.imagen.url

                        # Pasa también el color al formulario
                        form_data['fondo'] = ultimo_registro.fondo

                        form = CardInformativoForm(initial=form_data)
                    else:
                        form = CardInformativoForm()

                    # Resto del código para generar la respuesta JSON
                    data['idpadre'] = encrypt_id(request.GET['id'])
                    visible_fields = form.visible_fields()
                    total_fields = len(visible_fields)
                    lista = [
                        (1, 'Información Básica', visible_fields[:2]),
                        (2, 'Contenido', visible_fields[2:total_fields])
                    ]
                    data['form'] = lista
                    data['switchery'] = True
                    template = get_template('adm_agendamientocitas/modal/formcardinfo.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    messages.error(request, f'{ex}')



            # GRUPO RESPONSABLES
            elif action == 'gruporesponsable':
                try:
                    data['title'] = u'Gestión de Grupo Responsable'
                    data['idpadre'] = iddpservicio = int(encrypt(request.GET['idp']))
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True,
                                                                           departamentoservicio_id=iddpservicio), \
                                               f'&action={action}&idp={encrypt(iddpservicio)}'
                    # search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), f'&action={action}'
                    if search:
                        filtro = filtro & Q(nombre__icontains=search)
                        url_vars += '&s=' + search
                        data['search'] = search
                        # Filtra por status=True y activo=True
                    #filtro = filtro & Q(status=True, activo=True)
                    listado = ResponsableGrupoServicio.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(listado, 20)
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
                    data["url_vars"] = url_vars
                    data['listado'] = page.object_list
                    data['totcount'] = listado.count()
                    data['email_domain'] = EMAIL_DOMAIN
                    request.session['viewactivo'] = 7
                    return render(request, 'adm_agendamientocitas/viewgruporesponsable.html', data)
                except Exception as ex:
                    pass

            elif action == 'addgruporesponsable':
                try:
                    form = ResponsableServicioCitaForm()
                    form.fields['responsable'].queryset = Persona.objects.none()
                    data['idpadre'] = encrypt_id(request.GET['id'])
                    data['form'] = form
                    template = get_template("adm_agendamientocitas/modal/formgruporesponsable.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editgruporesponsable':
                try:
                    data['filtro']= instance = ResponsableGrupoServicio.objects.get(id=encrypt_id(request.GET['id']))
                    form = ResponsableServicioCitaForm(initial=model_to_dict(instance))
                    form.fields['responsable'].queryset = Persona.objects.filter(id=instance.responsable.id)
                    data['form'] = form
                    template = get_template("adm_agendamientocitas/modal/formgruporesponsable.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            # Terminos & Condiciones

            elif action == 'terminosvin':
                try:
                    data['title'] = 'Gestión de terminos y condiciones'
                    filtro, search, url_vars = Q(status=True), request.GET.get('s', ''), f'&action={action}'
                    if search:
                        data['search'] = search
                        filtro = filtro & (Q(descripcion__icontains=search) | Q(nombre__icontains=search))
                        url_vars += '&s={}'.format(search)
                    terminosvin = TerminosCondicion.objects.filter(filtro).order_by('pk')
                    paging = MiPaginador(terminosvin, 20)
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
                    data['url_vars'] = url_vars
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['listado'] = page.object_list
                    request.session['viewactivo'] = 6
                    return render(request, 'adm_agendamientocitas/viewterminosvin.html', data)
                except Exception as ex:
                    pass

            elif action == 'addterminosvin':
                try:
                    form = TerminosCondicionForm()
                    data['form'] = form
                    template = get_template("adm_agendamientocitas/modal/formterminosvin.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editterminosvin':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = TerminosCondicion.objects.get(pk=request.GET['id'])
                    form = TerminosCondicionForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("adm_agendamientocitas/modal/formterminosvin.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Agendamiento de Citas'
                search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
                # if not request.user.is_superuser or not permiso:
                #     if es_director_gestion or permiso:
                #         filtro = filtro & (Q(gestion=mi_gestion))
                #
                #     elif es_director:
                #         filtro = filtro & (Q(departamento=mi_departamento))
                #
                #     else:
                #         filtro = filtro & (Q(id__in=ids_grupos_servicios(persona)))

                # else:
                #     url_ = f'{request.path}?action=servicios&id={ids_grupos_servicios(persona)}'
                #     return redirect(url_)

                if search:
                    filtro = filtro & (Q(nombre__unaccent__icontains=search))
                    url_vars += '&s=' + search
                    data['s'] = search

                listado = DepartamentoServicio.objects.filter(filtro).order_by('id')
                paging = MiPaginador(listado, 10)
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
                data["url_vars"] = url_vars
                data['listado'] = page.object_list
                data['listcount'] = len(listado)
                request.session['viewactivo'] = 1
                return render(request, 'adm_agendamientocitas/viewdepartamentoservicio.html', data)
            except Exception as ex:
                return render({'result': False, 'mensaje': '{}'.format(ex)})


def ids_grupos_servicios(persona):
    try:
        idsgrupo = ResponsableServicioCita.objects.filter(status=True, responsable=persona).values_list(
            'servicio__serviciocita__departamentoservicio_id', flat=True).distinct()
        idsgrupo_d = ServicioCita.objects.filter(status=True, responsable=persona).values_list('departamentoservicio_id',
                                                                                               flat=True).distinct()
        lista = list(idsgrupo) + list(idsgrupo_d)
        return list(set(lista))
    except Exception as ex:
        raise NameError(f'Error: {ex}')



def ids_servicios_responsable(persona):
    try:
        # Obtenemos los IDs de los servicios que son asignados al responsable
        ids_serviciosr = ResponsableServicioCita.objects.filter(responsable=persona).values_list('servicio__serviciocita_id', flat=True)

        # Obtenemos los IDs de los servicios relacionados con los departamentos de servicio del responsable
        ids_servicios = ServicioCita.objects.filter(responsable=persona,
                                                    status=True).values_list('id', flat=True).distinct()

        lista = list( ids_serviciosr) + list(ids_servicios)
        return list(set(lista))
    except Exception as ex:
        raise NameError(f'Error: {ex}')


def castTituloSubtituloSitioWeb(tipoServicio):
    x = DepartamentoServicio.objects.get(id=tipoServicio)
    return x.nombre

def consultaPersonaDepartamento(request):
    departamentoid = int(encrypt(request.GET.get('args')))
    q = request.GET['q'].upper().strip()
    query = Q(responsable__nombres__icontains=q) | Q(responsable__apellido1__icontains=q) | Q(responsable__apellido2__icontains=q)
    personasresponsables_id = ResponsableGrupoServicio.objects.filter(
        departamentoservicio__id=departamentoid, status=True
    ).filter(query).values_list('responsable__id', flat=True)

    qspersona = Persona.objects.filter(id__in=personasresponsables_id)
    resp = [{'id': qs.pk, 'text': f"{qs.nombre_completo_inverso()}",
             'documento': qs.documento(),
             'departamento': qs.departamentopersona() if qs.departamentopersona() != 'Ninguno' else '',
             'foto': qs.get_foto()} for qs in qspersona]
    return resp

#
# def consultaPersonaDepartamento(request):
#     departamentoid = int(encrypt(request.GET.get('iddepartamento')))
#     q = request.GET['q'].upper().strip()
#     personasresponsables_id = ResponsableGrupoServicio.objects.filter(departamentoservicio_departamento__id = departamentoid, status=True,
#                                                    responsable__nombres__icontains=q,responsable__apellido1__icontains=q,
#                                                    responsable__apellido2__icontains=q).values_list('responsable__id', flat=True)
#     qspersona = Persona.objects.filter(id__in=personasresponsables_id)
#     resp = [{'id': qs.pk, 'text': f"{qs.nombre_completo_inverso()}",
#              'documento': qs.documento(),
#              'departamento': qs.departamentopersona() if not qs.departamentopersona() == 'Ninguno' else '',
#              'foto': qs.get_foto()} for qs in qspersona]
#     return resp
