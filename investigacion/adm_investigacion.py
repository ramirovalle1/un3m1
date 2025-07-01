# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from investigacion.forms import *
from investigacion.models import *
from sga.forms import ProyectoExternoForm
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import *
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import MiPaginador, log, puede_realizar_accion, generar_nombre
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    data['rutainv'] = '/inv_modulo'
    adduserdata(request, data)
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'registrarrol':
                try:
                    if 'rol' in request.POST:
                        if InvRoles.objects.filter(descripcion=request.POST['rol'].upper().strip(),
                                                   status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe esta descripcion."})

                        if request.POST['unico'] == 'on':
                            unico = True
                        else:
                            unico = False

                        causa = InvRoles(descripcion=request.POST['rol'], unico=unico)
                        causa.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Agrege una descripción."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'registrarcausa':
                try:
                    if 'descripcion' in request.POST:
                        if InvCausa.objects.filter(descripcion=request.POST['descripcion'].upper().strip(),
                                                   status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe esta descripcion."})
                        causa = InvCausa(descripcion=request.POST['descripcion'])
                        causa.save(request)
                        return JsonResponse({"result": "ok", "mensaje": u"Causa Agregada"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Agrege una descripción."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'registrarefecto':
                try:
                    if 'descripcion' in request.POST:
                        if InvEfecto.objects.filter(descripcion=request.POST['descripcion'].upper().strip(),
                                                    status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe esta descripcion."})
                        causa = InvEfecto(descripcion=request.POST['descripcion'])
                        causa.save(request)
                        return JsonResponse({"result": "ok", "mensaje": u"Efecto Agregado"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Agrege una descripción."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            # CAUSAS
            if action == 'addcausa':
                try:
                    f = CausaForm(request.POST)
                    if f.is_valid():
                        if InvCausa.objects.filter(descripcion=f.cleaned_data['descripcion'].strip(),
                                                   status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe esta descripcion."})
                        causa = InvCausa(descripcion=f.cleaned_data['descripcion'])
                        causa.save(request)
                        log(u'Adiciono nueva causa: %s' % causa, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'editcausa':
                try:
                    causa = InvCausa.objects.get(pk=int(encrypt(request.POST['id'])))
                    f = CausaForm(request.POST)
                    if f.is_valid():
                        causa.descripcion = f.cleaned_data['descripcion']
                        causa.save(request)
                        log(u'Modificó causa: %s' % causa, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'deletecausa':
                try:
                    causa = InvCausa.objects.get(pk=int(encrypt(request.POST['id'])))
                    causa.status = False
                    causa.save()
                    log(u'Eliminó causa: %s' % causa, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            # ROLES
            if action == 'addrol':
                try:
                    f = RolesForm(request.POST)
                    if f.is_valid():
                        if InvRoles.objects.filter(descripcion=f.cleaned_data['descripcion'].strip(),
                                                   status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe esta descripcion."})
                        causa = InvRoles(descripcion=f.cleaned_data['descripcion'], unico=f.cleaned_data['unico'])
                        causa.save(request)
                        log(u'Adiciono Rol: %s' % causa, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'editrol':
                try:
                    causa = InvRoles.objects.get(pk=int(encrypt(request.POST['id'])))
                    f = RolesForm(request.POST)
                    if f.is_valid():
                        causa.descripcion = f.cleaned_data['descripcion']
                        causa.unico = f.cleaned_data['unico']
                        causa.save(request)
                        log(u'Modificó Rol: %s' % causa, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'deleterol':
                try:
                    causa = InvRoles.objects.get(pk=int(encrypt(request.POST['id'])))
                    causa.status = False
                    causa.save()
                    log(u'Eliminó Rol: %s' % causa, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            # IMPACTOS
            if action == 'addimpacto':
                try:
                    f = ImpactoForm(request.POST)
                    if f.is_valid():
                        if InvImpacto.objects.filter(descripcion=f.cleaned_data['descripcion'].strip(),
                                                     status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe esta descripcion."})
                        impacto = InvImpacto(descripcion=f.cleaned_data['descripcion'],
                                             rangoinicio=int(request.POST['rangoinicio']),
                                             rangofin=int(request.POST['rangofin']))
                        impacto.save(request)
                        log(u'Adiciono nueva impacto: %s' % impacto, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'editimpacto':
                try:
                    impacto = InvImpacto.objects.get(pk=int(encrypt(request.POST['id'])))
                    f = ImpactoForm(request.POST)
                    if f.is_valid():
                        impacto.descripcion = f.cleaned_data['descripcion']
                        impacto.rangoinicio = int(request.POST['rangoinicio'])
                        impacto.rangofin = int(request.POST['rangofin'])
                        impacto.save(request)
                        log(u'Modificó impacto: %s' % impacto, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'deleteimpacto':
                try:
                    impacto = InvImpacto.objects.get(pk=int(encrypt(request.POST['id'])))
                    impacto.status = False
                    impacto.save()
                    log(u'Eliminó impacto: %s' % impacto, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            # EFECTOS
            if action == 'addefecto':
                try:
                    f = EfectoForm(request.POST)
                    if f.is_valid():
                        if InvEfecto.objects.filter(descripcion=f.cleaned_data['descripcion'].strip(),
                                                    status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe esta descripcion."})
                        efecto = InvEfecto(descripcion=f.cleaned_data['descripcion'])
                        efecto.save(request)
                        log(u'Adiciono nueva efecto: %s' % efecto, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'editefecto':
                try:
                    efecto = InvEfecto.objects.get(pk=int(encrypt(request.POST['id'])))
                    f = EfectoForm(request.POST)
                    if f.is_valid():
                        efecto.descripcion = f.cleaned_data['descripcion']
                        efecto.save(request)
                        log(u'Modificó efecto: %s' % efecto, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'deleteefecto':
                try:
                    efecto = InvEfecto.objects.get(pk=int(encrypt(request.POST['id'])))
                    efecto.status = False
                    efecto.save()
                    log(u'Eliminó efecto: %s' % efecto, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            # COMISIÓN
            if action == 'addcomision':
                try:
                    f = CabComisionForm(request.POST)
                    if f.is_valid():
                        if InvCabComision.objects.filter(nombre=f.cleaned_data['nombre'].strip(), status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe este nombre."})
                        impacto = InvCabComision(nombre=f.cleaned_data['nombre'], estadocomision=1, estadoareas=1)
                        impacto.save(request)
                        persona = Persona.objects.get(usuario_id=int(request.user.id))
                        hist = InvComisionHistorialEstados(cabcom=impacto, descripcion='PENDIENTE DE APROBACIÓN',
                                                           aprobadopor_id=int(persona.pk),
                                                           estado='1')
                        hist.save()
                        log(u'Adiciono Comisión: %s' % impacto, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'editcomision':
                try:
                    impacto = InvCabComision.objects.get(pk=int(encrypt(request.POST['id'])))
                    f = CabComisionForm(request.POST)
                    if f.is_valid():
                        impacto.nombre = f.cleaned_data['nombre']
                        impacto.save(request)
                        log(u'Modificó Comisión: %s' % impacto, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'deletecomision':
                try:
                    impacto = InvCabComision.objects.get(pk=int(encrypt(request.POST['id'])))
                    if impacto.estadocomision == 1 or impacto == 2:
                        impacto.status = False
                        impacto.save()
                        log(u'Eliminó Comisión: %s' % impacto, request, "del")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'aprobarcomision':
                try:
                    estado = request.POST['estado']
                    com = InvCabComision.objects.get(pk=int(encrypt(request.POST['id'])))
                    if com.estadocomision != 3:
                        if InvComisionHistorialEstados.objects.filter(cabcom=com, estado=estado).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Esta comisión ya tiene este estado."})
                        else:
                            com.estadocomision = int(estado)
                            if estado == '3' or estado == '4':
                                if estado == '4':
                                    com.estadoareas = 4
                                if 'archivoaprobado' in request.FILES:
                                    newfile = request.FILES['archivoaprobado']
                                    newfile._name = generar_nombre("informeaprobacion", newfile._name)
                                    com.archivoaprobado = newfile
                            com.save()
                            persona = Persona.objects.get(usuario_id=int(request.user.id))
                            detalle = request.POST['descripcion']
                            if detalle == '':
                                detalle = 'NINGUNA'
                            hist = InvComisionHistorialEstados(cabcom=com, descripcion=detalle,
                                                               aprobadopor_id=int(persona.pk),
                                                               estado=estado)
                            hist.save()
                            log(u'Aprobado: %s' % com, request, "del")
                            return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Esta comisión ya fue aprobada."})

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            # PARTICIPANTE COMISIÓN
            if action == 'addproyectoexterno':
                try:
                    persona = Persona.objects.get(pk=int(encrypt(request.POST['id'])))
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile.size > 2194304:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 2Mb"})
                        else:
                            newfiles = request.FILES['archivo']
                            newfilesd = newfiles._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if not ext.lower() == '.pdf':
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                    form = ProyectoExternoForm(request.POST, request.FILES)
                    if form.is_valid():
                        if persona.proyectoinvestigacionexterno_set.filter(nombre=form.cleaned_data['nombre']).exists():
                            return JsonResponse(
                                {'result': 'bad', 'mensaje': u'El proyecto ya se encuentra registrado.'})
                        proyectoexterno = ProyectoInvestigacionExterno(persona=persona,
                                                                       institucion=form.cleaned_data['institucion'],
                                                                       nombre=form.cleaned_data['nombre'],
                                                                       rol=form.cleaned_data['rol'],
                                                                       financiamiento=form.cleaned_data[
                                                                           'financiamiento'],
                                                                       fechainicio=form.cleaned_data['fechainicio'],
                                                                       fechafin=form.cleaned_data['fechafin'])
                        proyectoexterno.save(request)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("proyinves_", newfile._name)
                            proyectoexterno.archivo = newfile
                            proyectoexterno.save(request)
                        log(u'Adiciono idioma que domina: %s' % proyectoexterno, request, "add")
                        return JsonResponse({'result': 'ok'})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

            if action == 'addparticipante':
                try:
                    f = ComisionAreaForm(request.POST)
                    if int(request.POST['persona']) == 0:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe Agregar una persona."})
                    if f.is_valid():
                        if InvDetComisionParticipantes.objects.filter(cabcom_id=int(encrypt(request.POST['cabid'])),
                                                                      persona_id=int(request.POST['persona']),
                                                                      status=True).exists():
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Ya esta registrado en esta comisión."})

                        rolval = InvRoles.objects.get(pk=int(request.POST['rol']))
                        if rolval.unico:
                            if InvDetComisionParticipantes.objects.filter(cabcom_id=int(encrypt(request.POST['cabid'])),
                                                                          rol_id=int(request.POST['rol']),
                                                                          status=True).exists():
                                return JsonResponse({"result": "bad", "mensaje": u"Rol ya está ocupado."})

                        area = InvDetComisionParticipantes(cabcom_id=int(encrypt(request.POST['cabid'])),
                                                           persona_id=int(request.POST['persona']),
                                                           rol_id=int(request.POST['rol']))
                        area.save(request)

                        log(u'Adiciono: %s' % area, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'addparticipanteexterno':
                try:
                    f = ComisionAreaForm(request.POST)
                    if int(request.POST['persona']) == 0:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe Agregar una persona."})
                    if f.is_valid():
                        if InvDetComisionParticipantes.objects.filter(cabcom_id=int(encrypt(request.POST['cabid'])),
                                                                      persona_id=int(request.POST['persona']),
                                                                      status=True).exists():
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Ya esta registrado en esta comisión."})

                        rolval = InvRoles.objects.get(pk=int(request.POST['rol']))
                        if rolval.unico:
                            if InvDetComisionParticipantes.objects.filter(cabcom_id=int(encrypt(request.POST['cabid'])),
                                                                          rol_id=int(request.POST['rol']),
                                                                          status=True).exists():
                                return JsonResponse({"result": "bad", "mensaje": u"Rol ya está ocupado."})

                        area = InvDetComisionParticipantes(cabcom_id=int(encrypt(request.POST['cabid'])),
                                                           persona_id=int(request.POST['persona']),
                                                           rol_id=int(request.POST['rol']))
                        area.save(request)

                        log(u'Adiciono: %s' % area, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'editparticipante':
                try:
                    area = InvDetComisionParticipantes.objects.get(pk=int(encrypt(request.POST['id'])))
                    f = ComisionAreaForm(request.POST)

                    rolval = InvRoles.objects.get(pk=int(request.POST['rol']))
                    if rolval.unico:
                        if InvDetComisionParticipantes.objects.filter(cabcom_id=int(encrypt(request.POST['cabid'])),
                                                                      rol_id=int(request.POST['rol']),
                                                                      status=True).exclude(
                            pk=int(encrypt(request.POST['id']))).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Rol ya está ocupado."})

                    if f.is_valid():
                        area.rol_id = request.POST['rol']
                        area.save(request)
                        log(u'Modificó: %s' % area, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'editparticipanteexterno':
                try:
                    area = InvDetComisionParticipantes.objects.get(pk=int(encrypt(request.POST['id'])))
                    f = ComisionAreaForm(request.POST)

                    rolval = InvRoles.objects.get(pk=int(request.POST['rol']))
                    if rolval.unico:
                        if InvDetComisionParticipantes.objects.filter(cabcom_id=int(encrypt(request.POST['cabid'])),
                                                                      rol_id=int(request.POST['rol']),
                                                                      status=True).exclude(
                            pk=int(encrypt(request.POST['id']))).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Rol ya está ocupado."})

                    if f.is_valid():
                        area.rol_id = request.POST['rol']
                        area.save(request)
                        experiencia = request.POST.getlist('experiencia[]')
                        counter = 0
                        log(u'Modificó: %s' % area, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'deleteparticipante':
                try:
                    area = InvDetComisionParticipantes.objects.get(pk=int(encrypt(request.POST['id'])))
                    area.status = False
                    area.save()
                    log(u'Eliminó: %s' % area, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'addpersona':
                try:
                    f = PersonalExternoInvForm(request.POST)
                    if f.is_valid():
                        tipopersona = int(f.cleaned_data['tipopersona'])
                        if tipopersona == 1:
                            if not f.cleaned_data['cedula'] and not f.cleaned_data['pasaporte']:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Debe especificar un numero de identificación."})
                            if f.cleaned_data['cedula'] and Persona.objects.filter(
                                    cedula=f.cleaned_data['cedula']).exists():
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"El numero de cedula ya esta registrado."})
                            if f.cleaned_data['pasaporte'] and Persona.objects.filter(
                                    pasaporte=f.cleaned_data['pasaporte']).exists():
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"El numero de pasaporte ya esta registrado."})
                        else:
                            if f.cleaned_data['ruc'] and Persona.objects.filter(ruc=f.cleaned_data['ruc']).exists():
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"El numero de ruc ya esta registrado."})
                        clienteexterno = Persona(
                            nombres=f.cleaned_data['nombres'] if tipopersona == 1 else f.cleaned_data[
                                'nombreempresa'],
                            apellido1=f.cleaned_data['apellido1'] if tipopersona == 1 else '',
                            apellido2=f.cleaned_data['apellido2'] if tipopersona == 1 else '',
                            cedula=f.cleaned_data['cedula'] if tipopersona == 1 else '',
                            ruc=f.cleaned_data['ruc'] if tipopersona == 2 else '',
                            pasaporte=f.cleaned_data['pasaporte'] if tipopersona == 1 else '',
                            nacimiento=f.cleaned_data['nacimiento'],
                            sexo=f.cleaned_data['sexo'],
                            pais=f.cleaned_data['pais'],
                            provincia=f.cleaned_data['provincia'],
                            tipopersona=tipopersona,
                            canton=f.cleaned_data['canton'],
                            parroquia=f.cleaned_data['parroquia'],
                            sector=f.cleaned_data['sector'],
                            direccion=f.cleaned_data['direccion'],
                            direccion2=f.cleaned_data['direccion2'],
                            num_direccion=f.cleaned_data['num_direccion'],
                            telefono=f.cleaned_data['telefono'],
                            telefono_conv=f.cleaned_data['telefono_conv'],
                            email=f.cleaned_data['email'])
                        clienteexterno.save(request)
                        externo = Externo(persona=clienteexterno,
                                          institucionlabora=f.cleaned_data['institucionlabora'],
                                          nombrecomercial=f.cleaned_data[
                                              'nombrecomercial'] if tipopersona == 2 else '',
                                          nombrecontacto=f.cleaned_data[
                                              'nombrecontacto'] if tipopersona == 2 else '',
                                          telefonocontacto=f.cleaned_data[
                                              'telefonocontacto'] if tipopersona == 2 else '')
                        if 'hojadevida' in request.FILES:
                            newfile = request.FILES['hojadevida']
                            newfile._name = generar_nombre("hojadevida_", newfile._name)
                            externo.hojadevida = newfile
                        externo.save(request)
                        clienteexterno.crear_perfil(externo=externo)
                        clienteexterno.mi_perfil()

                        # if not clienteexterno.tiene_perfilusuario():
                        #     if not clienteexterno.usuario:
                        #         persona = Persona.objects.get(pk=clienteexterno.id)
                        #         username = calculate_username(persona)
                        #         generar_usuario(persona, username, variable_valor('INSTRUCTOR_GROUP_ID'))
                        #         if EMAIL_INSTITUCIONAL_AUTOMATICO:
                        #             persona.emailinst = username + '@' + EMAIL_DOMAIN
                        #         persona.save(request)

                        log(u'Adiciono Personal Externo: %s' % clienteexterno, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'verificarcedula':
                try:
                    if Persona.objects.filter(cedula=request.POST["cedula"]).exists():
                        return JsonResponse({"result": "no"})
                    else:
                        return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad"})

            # OBSERVACIÓN COMISIÓN

            if action == 'addobservacioncomision':
                try:
                    f = ComisionObservacionForm(request.POST)
                    if f.is_valid():

                        if InvDetObservacion.objects.filter(cabcom_id=int(encrypt(request.POST['cabid'])),
                                                            descripcion=request.POST['descripcion'],
                                                            status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya esta registrado en esta comisión."})

                        area = InvDetObservacion(cabcom_id=int(encrypt(request.POST['cabid'])),
                                                 descripcion=request.POST['descripcion'])
                        area.save(request)

                        log(u'Adiciono: %s' % area, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'editobservacioncomision':
                try:
                    area = InvDetObservacion.objects.get(pk=encrypt(request.POST['id']))
                    f = ComisionObservacionForm(request.POST)
                    if f.is_valid():
                        area.descripcion = request.POST['descripcion']
                        area.save(request)
                        log(u'Modificó: %s' % area, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'deleteobservacioncomision':
                try:
                    area = InvDetObservacion.objects.get(pk=int(encrypt(request.POST['id'])))
                    area.status = False
                    area.save()
                    log(u'Eliminó: %s' % area, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            # ÁREAS Y SUBÁREAS UNESCO
            if action == 'addareaunesco':
                try:
                    f = AreaUnescoForm(request.POST)
                    if f.is_valid():
                        if AreaUnesco.objects.filter(nombre=f.cleaned_data['nombre'].strip(),
                                                     status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe esta descripcion."})
                        areaunesco = AreaUnesco(nombre=f.cleaned_data['nombre'])
                        areaunesco.save(request)

                        subareas = request.POST.getlist('subareas[]')
                        counter = 0
                        while counter < len(subareas):
                            det = SubAreaUnesco(cabarea=areaunesco, nombre=subareas[counter])
                            det.save()
                            counter += 1

                        log(u'Adiciono nueva Área: %s' % areaunesco, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'editareaunesco':
                try:
                    areaunesco = AreaUnesco.objects.get(pk=int(encrypt(request.POST['id'])))
                    f = AreaUnescoForm(request.POST)
                    if f.is_valid():
                        areaunesco.nombre = f.cleaned_data['nombre']
                        areaunesco.save(request)
                        SubAreaUnesco.objects.filter(cabarea=areaunesco).delete()
                        subareas = request.POST.getlist('subareas[]')
                        counter = 0
                        while counter < len(subareas):
                            det = SubAreaUnesco(cabarea=areaunesco, nombre=subareas[counter])
                            det.save()
                            counter += 1

                        log(u'Modificó Área: %s' % areaunesco, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'deleteareaunesco':
                try:
                    areaunesco = AreaUnesco.objects.get(pk=int(encrypt(request.POST['id'])))
                    areaunesco.status = False
                    areaunesco.save()
                    SubAreaUnesco.objects.filter(cabarea_id=int(encrypt(request.POST['id']))).update(status=True)

                    log(u'Eliminó Área: %s' % areaunesco, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            # CAMPOS DE ACCIÓN

            if action == 'aprobarareacampoaccion':
                try:
                    estado = request.POST['estado']
                    com = InvCabAreas.objects.get(pk=int(encrypt(request.POST['id'])))
                    if com.estadoarea != 3:
                        if InvCabAreasHistorialEstados.objects.filter(cabarea=com, estado=estado).exists():
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Este campo de acción ya tiene este estado."})
                        else:
                            com.estadoarea = int(estado)
                            if 'archivoaprobado' in request.FILES:
                                com.numinforme = request.POST['numinforme']
                                newfile = request.FILES['archivoaprobado']
                                newfile._name = generar_nombre("informeaprobacion", newfile._name)
                                com.archivoinformepdf = newfile
                            com.save()
                            persona = Persona.objects.get(usuario_id=int(request.user.id))
                            detalle = request.POST['descripcion']
                            if detalle == '':
                                detalle = 'NINGUNA'
                            hist = InvCabAreasHistorialEstados(cabarea=com, descripcion=detalle,
                                                               aprobadopor_id=int(persona.pk),
                                                               estado=estado)
                            hist.save()

                            if 'archivoaprobado' in request.FILES:
                                newfile = request.FILES['archivoaprobado']
                                newfile._name = generar_nombre("informeaprobacion", newfile._name)
                                hist2 = InvCabAreasHistorialInforme(cabarea=com,
                                                                   archivoinformepdf=newfile,
                                                                   realizadopor=persona)
                                hist2.save()
                            log(u'Aprobado: %s' % com, request, "del")
                            return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Esta comisión ya fue aprobada."})

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'aprobarareascomisioncampoaccion':
                try:
                    com = InvCabComision.objects.get(pk=int(encrypt(request.POST['id'])))
                    if com.estadoareas != 3:
                        com.estadoareas = 3
                        if 'archivoaprobado' in request.FILES:
                            com.numresolucion = request.POST['numinforme']
                            com.fecha_numresolucion = datetime.now()
                            newfile = request.FILES['archivoaprobado']
                            newfile._name = generar_nombre("resolucionocas", newfile._name)
                            com.archivoresolucionpdf = newfile
                        com.save()
                        log(u'Aprobado: %s' % com, request, "del")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Esta comisión ya fue aprobada."})

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'subirhojadevidaexterno':
                try:
                    com = Externo.objects.get(persona_id=int(encrypt(request.POST['id'])))
                    if 'hojadevida' in request.FILES:
                        newfile = request.FILES['hojadevida']
                        newfile._name = generar_nombre("hojadevida_", newfile._name)
                        com.hojadevida = newfile
                    com.save()
                    log(u'Aprobado: %s' % com, request, "del")
                    return JsonResponse({"result": "ok"})

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'addcampoaccion':
                try:
                    f = CabAreasForm(request.POST)
                    if f.is_valid():
                        if InvCabAreas.objects.filter(nombre=f.cleaned_data['nombre'].strip(),
                                                      cabcom_id=int(encrypt(request.POST['cabcom']))).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe este Campo de Acción."})
                        area = InvCabAreas(cabcom_id=int(encrypt(request.POST['cabcom'])),
                                           nombre=f.cleaned_data['nombre'],
                                           descripcion=f.cleaned_data['descripcion'],
                                           impacto=f.cleaned_data['impacto'],
                                           estadoarea=1)
                        if 'archivoinformepdf' in request.FILES:
                            newfile = request.FILES['archivoinformepdf']
                            newfile._name = generar_nombre("informeaprobacion", newfile._name)
                            area.archivoinformepdf = newfile
                        if 'numinforme' in request.POST:
                            area.numinforme = request.POST['numinforme']
                        area.save(request)

                        if 'archivoinformepdf' in request.FILES:
                            newfile = request.FILES['archivoinformepdf']
                            newfile._name = generar_nombre("informeaprobacion", newfile._name)
                            persona = Persona.objects.get(usuario_id=int(request.user.id))
                            hist = InvCabAreasHistorialInforme(cabarea=area,
                                                               archivoinformepdf=newfile,
                                                               realizadopor=persona)
                            hist.save()

                        persona = Persona.objects.get(usuario_id=int(request.user.id))
                        hist = InvCabAreasHistorialEstados(cabarea=area, descripcion='PENDIENTE DE APROBACIÓN',
                                                           aprobadopor_id=int(persona.pk),
                                                           estado='1')
                        hist.save()

                        log(u'Adiciono: %s' % area, request, "add")
                        return JsonResponse({"result": "ok", "id": encrypt(area.id)})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'editcampoaccion':
                try:
                    area = InvCabAreas.objects.get(pk=int(encrypt(request.POST['id'])))
                    area.nombre = request.POST['nombre']
                    area.descripcion = request.POST['descripcion']
                    area.impacto_id = int(request.POST['impacto'])
                    if 'archivoinformepdf' in request.FILES:
                        newfile = request.FILES['archivoinformepdf']
                        newfile._name = generar_nombre("informeaprobacion", newfile._name)
                        area.archivoinformepdf = newfile
                    if 'numinforme' in request.POST:
                        area.numinforme = request.POST['numinforme']
                    area.save(request)

                    if 'archivoinformepdf' in request.FILES:
                        newfile = request.FILES['archivoinformepdf']
                        newfile._name = generar_nombre("informeaprobacion", newfile._name)
                        persona = Persona.objects.get(usuario_id=int(request.user.id))
                        hist = InvCabAreasHistorialInforme(cabarea=area,
                                                           archivoinformepdf=newfile,
                                                           realizadopor=persona)
                        hist.save()
                    log(u'Modificó: %s' % area, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'deletecampoaccion':
                try:
                    area = InvCabAreas.objects.get(pk=int(encrypt(request.POST['id'])))
                    area.status = False
                    area.save()

                    problemas = InvDetAreasProblemas.objects.filter(cabareas_id=area.pk)
                    if problemas.exists():
                        for p in problemas:
                            p.status = False
                            p.save(request)

                    causas = InvDetAreasCausas.objects.filter(cabproblemas__cabareas_id=area.pk, status=True)
                    if causas.exists():
                        for c in causas:
                            c.status = False
                            c.save(request)

                    efectos = InvDetAreasCausasEfecto.objects.filter(cabareascausa__cabproblemas__cabareas_id=area.pk)
                    if efectos.exists():
                        for e in efectos:
                            e.status = False
                            e.save(request)

                    log(u'Eliminó: %s' % area, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'addproblemacampoaccion':
                try:
                    resultado = InvDetAreasProblemas(cabareas_id=int(encrypt(request.POST['cabid'])),
                                                     descripcion=request.POST['descripcion'])
                    resultado.save(request)
                    log(u'Adicionó Problema: %s %s' % (resultado.descripcion, resultado), request, "edit")
                    return JsonResponse(
                        {"result": "ok", 'idproblema': resultado.id, 'descripcion': resultado.descripcion})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'addcausacampoaccion':
                try:
                    resultado = InvDetAreasCausas(cabproblemas_id=request.POST['idpro'],
                                                  causas_id=int(request.POST['descripcion']))
                    resultado.save(request)
                    log(u'Adicionó Causa: %s %s' % (resultado.causas.descripcion, resultado), request, "edit")
                    return JsonResponse(
                        {"result": "ok", 'descripcion': resultado.causas.descripcion, 'idcausa': resultado.id})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'addefectocampoaccion':
                try:
                    resultado = InvDetAreasCausasEfecto(cabareascausa_id=request.POST['idcaus'],
                                                        efecto_id=int(request.POST['descripcion']))
                    resultado.save(request)
                    log(u'Adicionó Efecto: %s %s' % (resultado.efecto.descripcion, resultado), request, "edit")
                    return JsonResponse(
                        {"result": "ok", 'descripcion': resultado.efecto.descripcion, 'idefecto': resultado.id})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'consultarproblemacampoaccion':
                try:
                    resultado = InvDetAreasProblemas.objects.get(pk=request.POST['id'])
                    return JsonResponse({"result": "ok", 'idproblema': resultado.id, 'nombre': resultado.descripcion})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'consultarcausacampoaccion':
                try:
                    resultado = InvDetAreasCausas.objects.get(pk=request.POST['id'])
                    return JsonResponse(
                        {"result": "ok", 'idcausa': resultado.id, 'nombre': resultado.causas.descripcion})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'consultarefectocampoaccion':
                try:
                    resultado = InvDetAreasCausasEfecto.objects.get(pk=request.POST['id'])
                    return JsonResponse(
                        {"result": "ok", 'idefecto': resultado.id, 'nombre': resultado.efecto.descripcion})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'editproblemacampoaccion':
                try:
                    resultado = InvDetAreasProblemas.objects.get(pk=request.POST['idproblema'])
                    resultado.descripcion = request.POST['descripcion']
                    resultado.save(request)
                    log(u'Editó: %s ' % (resultado.descripcion), request, "edit")
                    return JsonResponse(
                        {"result": "ok", 'idproblema': resultado.id, 'descripcion': resultado.descripcion})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'editcausacampoaccion':
                try:
                    resultado = InvDetAreasCausas.objects.get(pk=request.POST['idcausedit'])
                    resultado.causas_id = int(request.POST['descripcion'])
                    resultado.save(request)
                    log(u'Editó: %s ' % (resultado.causas.descripcion), request, "edit")
                    return JsonResponse({"result": "ok", 'idproblema': resultado.id})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'editefectocampoaccion':
                try:
                    resultado = InvDetAreasCausasEfecto.objects.get(pk=request.POST['idefectedit'])
                    resultado.efecto_id = int(request.POST['descripcion'])
                    resultado.save(request)
                    log(u'Editó: %s ' % (resultado.efecto.descripcion), request, "edit")
                    return JsonResponse({"result": "ok", 'idefecto': resultado.id})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'listaproblemacampoaccion':
                try:
                    resultado = InvDetAreasProblemas.objects.get(pk=request.POST['id'])
                    descripcion = resultado.descripcion
                    codigoproblema = resultado.id
                    return JsonResponse({"result": "ok", 'descripcion': descripcion, 'codigoproblema': codigoproblema})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'listacausacampoaccion':
                try:
                    resultado = InvDetAreasCausas.objects.get(pk=request.POST['id'])
                    descripcion = resultado.causas.descripcion
                    codigoproblema = resultado.id
                    return JsonResponse({"result": "ok", 'descripcion': descripcion, 'codigocausa': codigoproblema})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'listaefectocampoaccion':
                try:
                    resultado = InvDetAreasCausasEfecto.objects.get(pk=request.POST['id'])
                    descripcion = resultado.efecto.descripcion
                    codigoproblema = resultado.id
                    return JsonResponse({"result": "ok", 'descripcion': descripcion, 'codigoefecto': codigoproblema})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'eliminarproblemacampoaccion':
                try:
                    problemaid = request.POST['codigoproblema']
                    unidad = InvDetAreasProblemas.objects.get(pk=problemaid)
                    log(u'Eliminó: %s' % (unidad.descripcion), request, "del")
                    unidad.status = False
                    unidad.save(request)
                    causas = InvDetAreasCausas.objects.filter(cabproblemas_id=problemaid, status=True)
                    if causas.exists():
                        for c in causas:
                            c.status = False
                            c.save(request)

                    efectos = InvDetAreasCausasEfecto.objects.filter(cabareascausa__cabproblemas_id=problemaid)
                    if efectos.exists():
                        for e in efectos:
                            e.status = False
                            e.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'eliminarcausacampoaccion':
                try:
                    problemaid = request.POST['codigocausa']
                    causas = InvDetAreasCausas.objects.filter(pk=int(problemaid), status=True)
                    if causas.exists():
                        for c in causas:
                            c.status = False
                            c.save(request)

                    efectos = InvDetAreasCausasEfecto.objects.filter(cabareascausa_id=problemaid)
                    if efectos.exists():
                        for e in efectos:
                            e.status = False
                            e.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'eliminarefectocampoaccion':
                try:
                    problemaid = request.POST['codigoefecto']
                    efectos = InvDetAreasCausasEfecto.objects.filter(pk=problemaid)
                    if efectos.exists():
                        for e in efectos:
                            e.status = False
                            e.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            #REPORTES

            if action == 'inscritospdf':
                try:
                    data = {}
                    idarea = int(encrypt(request.GET['idarea']))
                    data['fechaactual'] = datetime.now()
                    data['comision'] = comision = InvCabComision.objects.get(id=int(idarea), status=True)
                    data['cab'] = cab = InvDetComisionParticipantes.objects.filter(cabcom_id=int(idarea), status=True)
                    return conviert_html_to_pdf('adm_investigacion/inscritos_pdf.html',
                                                {'pagesize': 'A4', 'data': data})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte. %s" % ex})

            if action == 'areapdfcampoaccion':
                try:
                    data = {}
                    idarea = int(encrypt(request.GET['idarea']))
                    data['fechaactual'] = datetime.now()
                    data['comision'] = comision = InvCabComision.objects.get(id=int(idarea), status=True)
                    data['cab'] = cab = InvCabAreas.objects.filter(cabcom_id=int(idarea), status=True).order_by('pk')
                    return conviert_html_to_pdf('adm_investigacion/area_pdfcampoaccion.html',
                                                {'pagesize': 'A4', 'data': data})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte. %s" % ex})

            if action == 'areaprobadapdfcampoaccion':
                try:
                    data = {}
                    idarea = int(encrypt(request.GET['idarea']))
                    data['fechaactual'] = datetime.now()
                    data['comision'] = comision = InvCabComision.objects.get(id=int(idarea), status=True)
                    data['cab'] = cab = InvCabAreas.objects.filter(cabcom_id=int(idarea), status=True).order_by('pk')
                    return conviert_html_to_pdf('adm_investigacion/areaaprobada_pdfcampoaccion.html',
                                                {'pagesize': 'A4', 'data': data})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte. %s" % ex})

            if action == 'areadetallepdfcampoaccion':
                try:
                    data = {}
                    idarea = int(encrypt(request.GET['idarea']))
                    data['fechaactual'] = datetime.now()
                    data['cab'] = cab = InvCabAreas.objects.get(pk=int(idarea))
                    data['det'] = pro = InvDetAreasProblemas.objects.filter(cabareas_id=int(idarea)).order_by('pk')
                    return conviert_html_to_pdf('adm_investigacion/areadetalle_pdfcampoaccion.html',
                                                {'pagesize': 'A4', 'data': data})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte. %s" % ex})

            # CAUSAS
            if action == 'addcausa':
                try:
                    data['title'] = u'Adicionar Causa'
                    data['form'] = CausaForm()
                    return render(request, "adm_investigacion/addcausa.html", data)
                except Exception as ex:
                    pass

            if action == 'editcausa':
                try:
                    data['title'] = u'Editar Causa'
                    data['causa'] = causa = InvCausa.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = CausaForm(initial={'descripcion': causa.descripcion})
                    data['form'] = form
                    return render(request, "adm_investigacion/editcausa.html", data)
                except Exception as ex:
                    pass

            if action == 'deletecausa':
                try:
                    data['title'] = u'Borrar Causa'
                    data['causa'] = InvCausa.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_investigacion/deletecausa.html", data)
                except Exception as ex:
                    pass

            if action == 'causas':
                data['title'] = u'Gestión de Causas'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s']
                if search:
                    proveedores = InvCausa.objects.filter(Q(descripcion__icontains=search)).filter(
                        status=True).order_by('-pk')
                elif 'id' in request.GET:
                    ids = int(encrypt(request.GET['id']))
                    proveedores = InvCausa.objects.filter(id=ids, status=True).order_by('-pk')
                else:
                    proveedores = InvCausa.objects.filter(status=True).order_by('-pk')
                paging = MiPaginador(proveedores, 20)
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
                data['lista'] = page.object_list
                data['email_domain'] = EMAIL_DOMAIN
                return render(request, "adm_investigacion/viewcausa.html", data)

            # ROLES
            if action == 'addrol':
                try:
                    data['title'] = u'Adicionar Rol'
                    data['form'] = RolesForm()
                    return render(request, "adm_investigacion/addrol.html", data)
                except Exception as ex:
                    pass

            if action == 'editrol':
                try:
                    data['title'] = u'Editar Rol'
                    data['causa'] = causa = InvRoles.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = RolesForm(initial={'descripcion': causa.descripcion, 'unico': causa.unico})
                    data['form'] = form
                    return render(request, "adm_investigacion/editrol.html", data)
                except Exception as ex:
                    pass

            if action == 'deleterol':
                try:
                    data['title'] = u'Borrar Rol'
                    data['causa'] = InvRoles.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_investigacion/deleterol.html", data)
                except Exception as ex:
                    pass

            if action == 'roles':
                data['title'] = u'Gestión de Roles'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s']
                if search:
                    proveedores = InvRoles.objects.filter(Q(descripcion__icontains=search)).filter(
                        status=True).order_by('-pk')
                elif 'id' in request.GET:
                    ids = int(encrypt(request.GET['id']))
                    proveedores = InvRoles.objects.filter(id=ids, status=True).order_by('-pk')
                else:
                    proveedores = InvRoles.objects.filter(status=True).order_by('-pk')
                paging = MiPaginador(proveedores, 20)
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
                data['lista'] = page.object_list
                data['email_domain'] = EMAIL_DOMAIN
                return render(request, "adm_investigacion/viewrol.html", data)

            # IMPACTOS
            if action == 'addimpacto':
                try:
                    data['title'] = u'Adicionar Impacto'
                    data['form'] = ImpactoForm()
                    return render(request, "adm_investigacion/addimpacto.html", data)
                except Exception as ex:
                    pass

            if action == 'editimpacto':
                try:
                    data['title'] = u'Editar Impacto'
                    data['impacto'] = impacto = InvImpacto.objects.get(pk=int(encrypt(request.GET['id'])))
                    initial = model_to_dict(impacto)
                    form = ImpactoForm(initial=initial)
                    data['form'] = form
                    return render(request, "adm_investigacion/editimpacto.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteimpacto':
                try:
                    data['title'] = u'Borrar Impacto'
                    data['impacto'] = InvImpacto.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_investigacion/deleteimpacto.html", data)
                except Exception as ex:
                    pass

            if action == 'impactos':
                data['title'] = u'Gestión de Impactos'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s']
                if search:
                    proveedores = InvImpacto.objects.filter(Q(descripcion__icontains=search)).filter(
                        status=True).order_by('-pk')
                elif 'id' in request.GET:
                    ids = int(encrypt(request.GET['id']))
                    proveedores = InvImpacto.objects.filter(id=ids, status=True).order_by('-pk')
                else:
                    proveedores = InvImpacto.objects.filter(status=True).order_by('-pk')
                paging = MiPaginador(proveedores, 20)
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
                data['lista'] = page.object_list
                data['email_domain'] = EMAIL_DOMAIN
                return render(request, "adm_investigacion/viewimpacto.html", data)

            # EFECTOS
            if action == 'addefecto':
                try:
                    data['title'] = u'Adicionar Efecto'
                    data['form'] = EfectoForm()
                    return render(request, "adm_investigacion/addefecto.html", data)
                except Exception as ex:
                    pass

            if action == 'editefecto':
                try:
                    data['title'] = u'Editar Efecto'
                    data['efecto'] = efecto = InvEfecto.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = EfectoForm(initial={'descripcion': efecto.descripcion})
                    data['form'] = form
                    return render(request, "adm_investigacion/editefecto.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteefecto':
                try:
                    data['title'] = u'Borrar Efecto'
                    data['efecto'] = InvEfecto.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_investigacion/deleteefecto.html", data)
                except Exception as ex:
                    pass

            if action == 'efectos':
                data['title'] = u'Gestión de Efectos'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s']
                if search:
                    proveedores = InvEfecto.objects.filter(Q(descripcion__icontains=search)).filter(
                        status=True).order_by('-pk')
                elif 'id' in request.GET:
                    ids = int(encrypt(request.GET['id']))
                    proveedores = InvEfecto.objects.filter(id=ids, status=True).order_by('-pk')
                else:
                    proveedores = InvEfecto.objects.filter(status=True).order_by('-pk')
                paging = MiPaginador(proveedores, 20)
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
                data['lista'] = page.object_list
                data['email_domain'] = EMAIL_DOMAIN
                return render(request, "adm_investigacion/viewefecto.html", data)

            # COMISIÓN
            if action == 'addcomision':
                try:
                    data['title'] = u'Adicionar Comisión'
                    data['form'] = CabComisionForm()
                    return render(request, "adm_investigacion/addcomision.html", data)
                except Exception as ex:
                    pass

            if action == 'detalleareasaprobacion':
                try:
                    data['title'] = u'Detalle Aprobación Campos de Acción'
                    data['area'] = InvCabComision.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_investigacion/detalle_aprobacion_areas.html", data)
                except Exception as ex:
                    pass

            if action == 'editcomision':
                try:
                    data['title'] = u'Editar Comisión'
                    data['impacto'] = impacto = InvCabComision.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = CabComisionForm(initial={'nombre': impacto.nombre})
                    data['form'] = form
                    return render(request, "adm_investigacion/editcomision.html", data)
                except Exception as ex:
                    pass

            if action == 'deletecomision':
                try:
                    data['title'] = u'Borrar Comisión'
                    data['impacto'] = InvCabComision.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_investigacion/deletecomision.html", data)
                except Exception as ex:
                    pass

            if action == 'aprobarcomision':
                try:
                    data['title'] = u'Aprobar Comisión'
                    data['area'] = area = InvCabComision.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['cabcom'] = area.pk
                    data['det'] = det = InvComisionHistorialEstados.objects.filter(cabcom=area).order_by('pk')
                    data['form'] = EstadoObservacionForm()
                    return render(request, "adm_investigacion/aprobarcomision.html", data)
                except Exception as ex:
                    pass

            if action == 'comision':
                data['title'] = u'Gestión de Comisión'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s']
                if search:
                    proveedores = InvCabComision.objects.filter(Q(nombre__icontains=search)).filter(
                        status=True).order_by('pk')
                elif 'id' in request.GET:
                    ids = int(encrypt(request.GET['id']))
                    proveedores = InvCabComision.objects.filter(id=ids, status=True).order_by('pk')
                else:
                    proveedores = InvCabComision.objects.filter(status=True).order_by('pk')
                paging = MiPaginador(proveedores, 20)
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
                data['lista'] = page.object_list
                data['email_domain'] = EMAIL_DOMAIN
                return render(request, "adm_investigacion/viewcomision.html", data)

            # PARTICIPANTES COMISIÓN
            if action == 'addpersona':
                try:
                    data['title'] = u'Registrar datos del participante'
                    data['cabid'] = int(encrypt(request.GET['cabid']))
                    form = PersonalExternoInvForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, "adm_investigacion/addnuevapersona.html", data)
                except Exception as ex:
                    pass

            if action == 'busquedapersona':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if s.__len__() == 2:
                        persona = Persona.objects.filter(apellido1__icontains=s[0], apellido2__icontains=s[1],
                                                         real=True).distinct()[:15]
                    else:
                        persona = Persona.objects.filter(Q(real=True) & (
                                Q(nombres__contains=s[0]) | Q(apellido1__contains=s[0]) | Q(
                            apellido2__contains=s[0]) | Q(cedula__contains=s[0]))).distinct()[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_repr()} for x in persona if
                                                        x.es_externo() == False]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'busquedapersonaexterna':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if s.__len__() == 2:
                        persona = Persona.objects.filter(apellido1__icontains=s[0], apellido2__icontains=s[1],
                                                         real=True).distinct()[:15]
                    else:
                        persona = Persona.objects.filter(Q(real=True) & (
                                Q(nombres__contains=s[0]) | Q(apellido1__contains=s[0]) | Q(
                            apellido2__contains=s[0]) | Q(cedula__contains=s[0]))).distinct()[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_repr()} for x in persona if
                                                        x.es_externo() == True]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'addproyectoexterno':
                try:
                    data['title'] = u'Adicionar Proyecto Externo'
                    data['cabid'] = int(encrypt(request.GET['cabid']))
                    data['id'] = int(encrypt(request.GET['id']))
                    form = ProyectoExternoForm()
                    data['form'] = form
                    return render(request, "adm_investigacion/addparticipanteexperiencia.html", data)
                except Exception as ex:
                    pass

            if action == 'addparticipante':
                try:
                    data['title'] = u'Adicionar Comisión'
                    data['form'] = ComisionAreaForm()
                    data['cabid'] = int(encrypt(request.GET['cabid']))
                    return render(request, "adm_investigacion/addparticipante.html", data)
                except Exception as ex:
                    pass

            if action == 'addparticipanteexterno':
                try:
                    data['title'] = u'Adicionar Comisión'
                    data['form'] = ComisionAreaForm()
                    data['cabid'] = int(encrypt(request.GET['cabid']))
                    return render(request, "adm_investigacion/addparticipanteexterno.html", data)
                except Exception as ex:
                    pass

            if action == 'editparticipante':
                try:
                    data['title'] = u'Editar Participante'
                    data['cabid'] = int(encrypt(request.GET['cabid']))
                    data['area'] = area = InvDetComisionParticipantes.objects.get(pk=int(encrypt(request.GET['id'])))
                    initial = model_to_dict(area)
                    form = ComisionAreaForm(initial=initial)
                    form.editar(area)
                    data['form'] = form
                    return render(request, "adm_investigacion/editparticipante.html", data)
                except Exception as ex:
                    pass

            if action == 'editparticipanteexterno':
                try:
                    data['title'] = u'Editar Participante'
                    data['cabid'] = int(encrypt(request.GET['cabid']))
                    data['area'] = area = InvDetComisionParticipantes.objects.get(pk=int(encrypt(request.GET['id'])))
                    initial = model_to_dict(area)
                    form = ComisionAreaForm(initial=initial)
                    form.editar(area)
                    data['form'] = form
                    return render(request, "adm_investigacion/editparticipanteexterno.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteparticipante':
                try:
                    data['title'] = u'Borrar Comisión'
                    data['cabid'] = int(encrypt(request.GET['cabid']))
                    data['cabecera'] = cabecera = InvCabComision.objects.get(id=int(encrypt(request.GET['cabid'])))
                    data['area'] = InvDetComisionParticipantes.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_investigacion/deleteparticipante.html", data)
                except Exception as ex:
                    pass

            if action == 'participantes':
                cabecera = None
                cabid = 0
                nombrecomision = ''
                if 'cabid' in request.GET:
                    cabid = int(encrypt(request.GET['cabid']))
                    data['cabecera'] = cabecera = InvCabComision.objects.get(id=int(cabid))
                    nombrecomision = cabecera.nombre
                    if cabecera.estadocomision == 3 or cabecera.estadocomision == 4:
                        cabestado = False
                    else:
                        cabestado = True
                    data['estadocab'] = cabestado
                data['title'] = u'Gestión de Comisión : ' + nombrecomision
                data['cabid'] = cabecera.pk
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s']
                if search:
                    cabarea = InvDetComisionParticipantes.objects.filter(
                        Q(persona__cedula__icontains=search) | Q(persona__apellido1__icontains=search) | Q(
                            rol__descripcion__icontains=search) |
                        Q(persona__nombres__icontains=search)).filter(cabcom_id=int(cabecera.pk), status=True).order_by(
                        'pk')
                elif 'id' in request.GET:
                    ids = int(encrypt(request.GET['id']))
                    cabarea = InvDetComisionParticipantes.objects.filter(cabcom_id=int(cabecera.pk), id=ids,
                                                                         status=True).order_by('pk')
                else:
                    cabarea = InvDetComisionParticipantes.objects.filter(cabcom_id=int(cabecera.pk),
                                                                         status=True).order_by(
                        'pk')
                data['lista'] = cabarea
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['email_domain'] = EMAIL_DOMAIN
                data['reporte_1'] = obtener_reporte('hoja_vida_sagest')
                return render(request, "adm_investigacion/viewparticipante.html", data)

            # OBSERVACIÓN COMISIÓN
            if action == 'addobservacioncomision':
                try:
                    data['title'] = u'Adicionar Observación'
                    data['form'] = ComisionObservacionForm()
                    data['cabid'] = int(encrypt(request.GET['cabid']))
                    return render(request, "adm_investigacion/addobservacioncomision.html", data)
                except Exception as ex:
                    pass

            if action == 'editobservacioncomision':
                try:
                    data['title'] = u'Editar Observación'
                    data['cabid'] = int(encrypt(request.GET['cabid']))
                    data['area'] = area = InvDetObservacion.objects.get(pk=(int(encrypt(request.GET['id']))))
                    initial = model_to_dict(area)
                    form = ComisionObservacionForm(initial=initial)
                    data['form'] = form
                    return render(request, "adm_investigacion/editobservacioncomision.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteobservacioncomision':
                try:
                    data['title'] = u'Borrar Observación'
                    data['cabid'] = int(encrypt(request.GET['cabid']))
                    data['cabecera'] = cabecera = InvCabComision.objects.get(id=int(encrypt(request.GET['cabid'])))
                    data['area'] = InvDetObservacion.objects.get(pk=(int(encrypt(request.GET['id']))))
                    return render(request, "adm_investigacion/deleteobservacioncomision.html", data)
                except Exception as ex:
                    pass

            if action == 'observacioncomision':
                cabecera = None
                cabid = 0
                nombrecomision = ''
                if 'cabid' in request.GET:
                    cabid = int(encrypt(request.GET['cabid']))
                    data['cabecera'] = cabecera = InvCabComision.objects.get(id=int(cabid))
                    nombrecomision = cabecera.nombre
                    if cabecera.estadocomision == 3 or cabecera.estadocomision == 4:
                        cabestado = False
                    else:
                        cabestado = True
                    data['estadocab'] = cabestado
                data['title'] = u'Gestión de Comisión : ' + nombrecomision
                data['cabid'] = cabecera.pk
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s']
                if search:
                    observacionlista = InvDetObservacion.objects.filter(Q(descripcion__icontains=search)).filter(
                        cabcom_id=int(cabecera.pk), status=True).order_by('pk')
                elif 'id' in request.GET:
                    ids = int(encrypt(request.GET['id']))
                    observacionlista = InvDetObservacion.objects.filter(cabcom_id=int(cabecera.pk), id=ids,
                                                                        status=True).order_by('pk')
                else:
                    observacionlista = InvDetObservacion.objects.filter(cabcom_id=int(cabecera.pk),
                                                                        status=True).order_by('pk')
                data['lista'] = observacionlista
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['email_domain'] = EMAIL_DOMAIN
                return render(request, "adm_investigacion/viewobservacioncomision.html", data)

            # ÁREAS Y SUBÁREAS UNESCO

            if action == 'addareaunesco':
                try:
                    data['title'] = u'Adicionar Áreas y Subáreas Unesco'
                    data['form'] = AreaUnescoForm()
                    return render(request, "adm_investigacion/addareaunesco.html", data)
                except Exception as ex:
                    pass

            if action == 'editareaunesco':
                try:
                    data['title'] = u'Editar Áreas y Subáreas Unesco'
                    data['areaunesco'] = areaunesco = AreaUnesco.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = AreaUnescoForm(initial={'nombre': areaunesco.nombre})
                    data['form'] = form
                    data['subareas'] = SubAreaUnesco.objects.filter(cabarea=areaunesco)
                    return render(request, "adm_investigacion/editareaunesco.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteareaunesco':
                try:
                    data['title'] = u'Borrar Áreas y Subáreas Unesco'
                    data['areaunesco'] = AreaUnesco.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_investigacion/deleteareaunesco.html", data)
                except Exception as ex:
                    pass

            if action == 'areaunesco':
                data['title'] = u'Gestión de Áreas y Subáreas Unesco'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s']
                if search:
                    proveedores = AreaUnesco.objects.filter(Q(nombre__icontains=search)).filter(
                        status=True).order_by('pk')
                elif 'id' in request.GET:
                    ids = int(encrypt(request.GET['id']))
                    proveedores = AreaUnesco.objects.filter(id=ids, status=True).order_by('pk')
                else:
                    proveedores = AreaUnesco.objects.filter(status=True).order_by('pk')
                paging = MiPaginador(proveedores, 20)
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
                data['lista'] = page.object_list
                data['email_domain'] = EMAIL_DOMAIN
                return render(request, "adm_investigacion/viewareasunesco.html", data)

            # CAMPOS DE ACCIÓN

            if action == 'busquedacausascampoaccion':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if s.__len__() == 2:
                        causas = InvCausa.objects.filter(Q(descripcion__icontains=s[0])).filter(status=True).distinct()[
                                 :15]
                    else:
                        causas = InvCausa.objects.filter(Q(descripcion__icontains=s[0])).filter(status=True).distinct()[
                                 :15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.descripcion} for x in causas]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'busquedaefectoscampoaccion':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if s.__len__() == 2:
                        efectos = InvEfecto.objects.filter(Q(descripcion__icontains=s[0])).filter(
                            status=True).distinct()[:15]
                    else:
                        efectos = InvEfecto.objects.filter(Q(descripcion__icontains=s[0])).filter(
                            status=True).distinct()[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.descripcion} for x in efectos]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'addcampoaccion':
                try:
                    data['cabcom'] = request.GET['cabcom']
                    data['title'] = u'Adicionar Campo de Acción'
                    data['form'] = CabAreasForm()
                    return render(request,"adm_investigacion/addcampoaccion.html", data)
                except Exception as ex:
                    pass

            if action == 'editcampoaccion':
                try:
                    data['title'] = u'Editar Campo de Acción'
                    data['area'] = area = InvCabAreas.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['cabcom'] = area.cabcom.pk
                    initial = model_to_dict(area)
                    form = CabAreasForm(initial=initial)
                    data['form'] = form
                    data['contenido'] = InvDetAreasProblemas.objects.filter(cabareas_id=int(encrypt(request.GET['id'])),
                                                                            status=True).order_by('pk')
                    return render(request,"adm_investigacion/editcampoaccion.html", data)
                except Exception as ex:
                    pass

            if action == 'deletecampoaccion':
                try:
                    data['title'] = u'Borrar Campo de Acción'
                    data['area'] = area = InvCabAreas.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['cabcom'] = area.cabcom.pk
                    return render(request,"adm_investigacion/deletecampoaccion.html", data)
                except Exception as ex:
                    pass

            if action == 'aprobarcampoaccion':
                try:
                    data['title'] = u'Aprobar Campo de Acción'
                    data['area'] = area = InvCabAreas.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['cabcom'] = area.cabcom.pk
                    data['det'] = det = InvCabAreasHistorialEstados.objects.filter(cabarea=area).order_by('pk')
                    data['form'] = EstadoObservacionAreasForm(initial={'numinforme': area.numinforme,
                                                                       'archivoaprobado': area.archivoinformepdf})
                    return render(request,"adm_investigacion/aprobarareacampoaccion.html", data)
                except Exception as ex:
                    pass

            if action == 'aprobarareascomisioncampoaccion':
                try:
                    data['title'] = u'Aprobar Campos de Acción General'
                    idcomision = int(encrypt(request.GET['id']))
                    data['area'] = InvCabComision.objects.get(pk=idcomision)
                    data['form'] = EstadoObservacionAreasComisionForm()
                    return render(request,"adm_investigacion/aprobarareacomisioncampoaccion.html", data)
                except Exception as ex:
                    pass

            if action == 'subirhojavidaexterno':
                try:
                    data['title'] = u'Subir Hoja de Vida Participante Externo'
                    id = int(encrypt(request.GET['id']))
                    data['cabid'] = int(encrypt(request.GET['cabid']))
                    data['area'] = Persona.objects.get(pk=id)
                    data['form'] = hojadevida()
                    return render(request,"adm_investigacion/subirhojadevidaexterno.html", data)
                except Exception as ex:
                    pass

            if action == 'observacioncampoaccion':
                try:
                    data['area'] = area = InvCabAreas.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = area.nombre
                    data['contenido'] = InvDetAreasProblemas.objects.filter(cabareas_id=int(encrypt(request.GET['id'])),
                                                                            status=True).order_by('pk')
                    return render(request,"adm_investigacion/observacionescampoaccion.html", data)
                except Exception as ex:
                    pass

            if action == 'observacioninformescampoaccion':
                try:
                    data['area'] = area = InvCabAreas.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = area.nombre
                    data['det'] = det = InvCabAreasHistorialInforme.objects.filter(cabarea=area).order_by('pk')
                    return render(request,"adm_investigacion/historialdearchivoscampoaccion.html", data)
                except Exception as ex:
                    pass

            if action == 'campoaccion':
                cabecera = None
                cabcomid = 0
                nombrecomision = ''
                if 'cabcom' in request.GET:
                    data['cabecera'] = cabecera = InvCabComision.objects.get(id=int(encrypt(request.GET['cabcom'])))
                    data['cabcom'] = cabcomid = int(encrypt(request.GET['cabcom']))
                    nombrecomision = cabecera.nombre
                data['title'] = u'Gestión de Campos de Acción: ' + nombrecomision
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s']
                if search:
                    cabarea = InvCabAreas.objects.filter(Q(nombre__icontains=search) |
                                                         Q(impacto__descripcion__icontains=search)).filter(status=True,
                                                                                                           cabcom_id=cabcomid).order_by(
                        'pk')
                elif 'id' in request.GET:
                    ids = int(encrypt(request.GET['id']))
                    cabarea = InvCabAreas.objects.filter(id=ids, status=True, cabcom_id=cabcomid).order_by('pk')
                else:
                    cabarea = InvCabAreas.objects.filter(status=True, cabcom_id=cabcomid).order_by('pk')
                paging = MiPaginador(cabarea, 20)
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
                data['lista'] = page.object_list
                data['email_domain'] = EMAIL_DOMAIN
                data['pdfareasaprobadas'] = False

                if cabarea.exclude(estadoarea=3).exclude(estadoarea=4).exists():
                    data['aprobarareas'] = False
                else:
                    if cabecera.estadoareas == 1:
                        if cabarea.count() > 0:
                            data['aprobarareas'] = True
                        else:
                            data['aprobarareas'] = False
                    else:
                        data['pdfareasaprobadas'] = True

                return render(request,"adm_investigacion/viewcampoaccion.html", data)

            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u'Módulo Investigación'
            return render(request, "adm_investigacion/view_modulo.html", data)
