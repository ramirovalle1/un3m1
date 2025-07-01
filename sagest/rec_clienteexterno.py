# -*- coding: UTF-8 -*-

from django.contrib.auth.models import Group, User
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sagest.forms import ClienteExternoForm, CuentaBancariaPersonaForm
from sagest.models import datetime
from settings import PROFESORES_GROUP_ID, CLAVE_USUARIO_CEDULA, DEFAULT_PASSWORD, ALUMNOS_GROUP_ID, EMPLEADORES_GRUPO_ID
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, puede_realizar_accion, calculate_username, generar_usuario, variable_valor, resetear_clave
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
from sga.models import Persona, Externo, CuentaBancariaPersona, Administrativo, Coordinacion, TiempoDedicacionDocente, \
    Profesor, PerfilUsuario, CUENTAS_CORREOS, miinstitucion
from django.template import Context
from django.template.loader import get_template


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@last_access
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = ClienteExternoForm(request.POST)
                if f.is_valid():
                    tipopersona = int(f.cleaned_data['tipopersona'])
                    if tipopersona == 1:
                        if not f.cleaned_data['cedula'] and not f.cleaned_data['pasaporte']:
                            return JsonResponse({"result": "bad", "mensaje": u"Debe especificar un numero de identificación."})
                        if f.cleaned_data['cedula'] and Persona.objects.filter(cedula=f.cleaned_data['cedula']).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"El numero de cedula ya esta registrado."})
                        if f.cleaned_data['pasaporte'] and Persona.objects.filter(pasaporte=f.cleaned_data['pasaporte']).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"El numero de pasaporte ya esta registrado."})
                    else:
                        if f.cleaned_data['ruc'] and Persona.objects.filter(ruc=f.cleaned_data['ruc']).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"El numero de ruc ya esta registrado."})
                    clienteexterno = Persona(nombres=f.cleaned_data['nombres'] if tipopersona == 1 else f.cleaned_data['nombreempresa'],
                                             apellido1=f.cleaned_data['apellido1'] if tipopersona == 1 else '',
                                             apellido2=f.cleaned_data['apellido2'] if tipopersona == 1 else '',
                                             cedula=f.cleaned_data['cedula'] if tipopersona == 1 else '',
                                             ruc=f.cleaned_data['ruc'] if tipopersona == 2 else '',
                                             pasaporte=f.cleaned_data['pasaporte'] if tipopersona == 1 else '',
                                             nacimiento=f.cleaned_data['nacimiento'],
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
                                      nombrecomercial=f.cleaned_data['nombrecomercial'] if tipopersona == 2 else '',
                                      nombrecontacto=f.cleaned_data['nombrecontacto'] if tipopersona == 2 else '',
                                      telefonocontacto=f.cleaned_data['telefonocontacto'] if tipopersona == 2 else '')
                    externo.save(request)
                    if f.cleaned_data['sexo']:
                        clienteexterno.sexo=f.cleaned_data['sexo']
                        clienteexterno.save()
                    clienteexterno.crear_perfil(externo=externo)
                    clienteexterno.mi_perfil()
                    log(u'Adiciono cliente externo: %s' % clienteexterno, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                f = ClienteExternoForm(request.POST)
                if f.is_valid():
                    clientexter = Persona.objects.get(pk=request.POST['id'])
                    if clientexter.tipopersona == 1:
                        if not f.cleaned_data['cedula'] and not f.cleaned_data['pasaporte']:
                            return JsonResponse({"result": "bad", "mensaje": u"Debe especificar un numero de identificación."})
                        if f.cleaned_data['cedula'] and Persona.objects.filter(cedula=f.cleaned_data['cedula']).exclude(id=clientexter.id).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"El numero de cedula ya esta registrado."})
                        if f.cleaned_data['pasaporte'] and Persona.objects.filter(pasaporte=f.cleaned_data['pasaporte']).exclude(id=clientexter.id).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"El numero de pasaporte ya esta registrado."})
                    else:
                        if not f.cleaned_data['ruc']:
                            return JsonResponse({"result": "bad", "mensaje": u"Debe especificar un numero de ruc."})
                        if f.cleaned_data['ruc'] and Persona.objects.filter(ruc=f.cleaned_data['ruc']).exclude(id=clientexter.id).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"El numero de ruc ya esta registrado."})
                    if clientexter.tipopersona == 1:
                        clientexter.nombres = f.cleaned_data['nombres']
                        clientexter.apellido1 = f.cleaned_data['apellido1']
                        clientexter.apellido2 = f.cleaned_data['apellido2']
                        clientexter.cedula = f.cleaned_data['cedula']
                        clientexter.pasaporte = f.cleaned_data['pasaporte']
                    else:
                        clientexter.nombres = f.cleaned_data['nombreempresa']
                        clientexter.ruc = f.cleaned_data['ruc']
                        clientexter.contribuyenteespecial = f.cleaned_data['contribuyenteespecial']
                        if clientexter.externo_set.exists():
                            externo = clientexter.externo_set.all()[0]
                            externo.nombrecomercial = f.cleaned_data['nombrecomercial']
                            externo.nombrecontacto = f.cleaned_data['nombrecontacto']
                            externo.telefonocontacto = f.cleaned_data['telefonocontacto']
                            externo.save(request)
                    clientexter.nacimiento = f.cleaned_data['nacimiento']
                    clientexter.sexo = f.cleaned_data['sexo']
                    clientexter.pais = f.cleaned_data['pais']
                    clientexter.provincia = f.cleaned_data['provincia']
                    clientexter.canton = f.cleaned_data['canton']
                    clientexter.parroquia = f.cleaned_data['parroquia']
                    clientexter.sector = f.cleaned_data['sector']
                    clientexter.direccion = f.cleaned_data['direccion']
                    clientexter.direccion2 = f.cleaned_data['direccion2']
                    clientexter.num_direccion = f.cleaned_data['num_direccion']
                    clientexter.telefono = f.cleaned_data['telefono']
                    clientexter.telefono_conv = f.cleaned_data['telefono_conv']
                    clientexter.email = f.cleaned_data['email']
                    clientexter.save(request)
                    log(u'Modifico cliente externo: %s' % clientexter, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'detalle_cliente':
            try:
                data['persona'] = cliente = Persona.objects.get(pk=int(request.POST['id']))
                template = get_template("rec_clienteexterno/detalle.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'delete':
            try:
                externo = Externo.objects.get(pk=request.POST['id'])
                log(u'Elimino cliente externo: %s' % externo, request, "del")
                externo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addcuentabancaria':
            try:
                persona = Persona.objects.get(pk=int(request.POST['persona']))
                f = CuentaBancariaPersonaForm(request.POST)
                if f.is_valid():
                    cuentabancaria = CuentaBancariaPersona(persona=persona,
                                                           numero=f.cleaned_data['numero'],
                                                           banco=f.cleaned_data['banco'],
                                                           tipocuentabanco=f.cleaned_data['tipocuentabanco'],)
                    cuentabancaria.save(request)
                    log(u'Adiciono cuenta bancaria: %s' % persona, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'editcuentabancaria':
            try:
                persona = Persona.objects.get(pk=int(request.POST['persona']))
                f = CuentaBancariaPersonaForm(request.POST)
                if f.is_valid():
                    cuentabancaria = CuentaBancariaPersona.objects.get(pk=int(request.POST['id']))
                    if persona.cuentabancariapersona_set.filter(numero=f.cleaned_data['numero']).exclude(id=cuentabancaria.id).exists():
                        return JsonResponse({'result': 'bad', 'mensaje': u'La cuenta bancaria se encuentra registrada.'})
                    if cuentabancaria.verificado:
                        return JsonResponse({'result': 'bad', 'mensaje': u'No puede modificar la cuenta bancaria.'})
                    cuentabancaria.numero = f.cleaned_data['numero']
                    cuentabancaria.banco = f.cleaned_data['banco']
                    cuentabancaria.tipocuentabanco = f.cleaned_data['tipocuentabanco']
                    cuentabancaria.save(request)
                    log(u'Modifico cuenta bancaria: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'delcuentabancaria':
            try:
                cuentabancaria = CuentaBancariaPersona.objects.get(pk=int(request.POST['id']))
                if cuentabancaria.verificado or cuentabancaria.activapago or cuentabancaria.archivoesigef or cuentabancaria.estadorevision==1:
                    return JsonResponse({'result': 'bad', 'mensaje': u'No puede eliminar la cuenta bancaria.'})
                cuentabancaria.status=False
                cuentabancaria.save()
                log(u'Elimino cuenta bancaria: %s' % cuentabancaria, request, "del")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al eliminar los datos'})

        elif action == 'addadministrativo':
            try:
                persona = Persona.objects.get(pk=request.POST['id'])
                if persona.es_administrativo():
                    return JsonResponse({"result": "bad", "mensaje": u"Ya existe un perfil administrativo para este usuario."})
                administrativo = Administrativo(persona=persona,
                                                contrato='',
                                                fechaingreso=datetime.now().date())
                administrativo.save(request)
                g = Group.objects.get(pk=variable_valor('ADMINISTRATIVOS_GROUP_ID'))
                usuarionuevo = False
                if not persona.usuario:
                    username = calculate_username(persona)
                    generar_usuario(persona, username, g.id)
                    usuarionuevo = True

                g.user_set.add(persona.usuario)
                g.save()
                persona.crear_perfil(administrativo=administrativo)
                if not persona.emailinst:
                    persona.emailinst=u"%s@unemi.edu.ec"%persona.usuario.username
                    persona.save(request)

                resetear = request.POST.get('resetear', '') == 'on'
                if resetear:
                    resetear_clave(persona)

                enviar_correo_credenciales(request, persona, usuarionuevo, resetear, 'ADMINISTRATIVO', CUENTAS_CORREOS[4][1])

                log(u'Adiciono personal administrativo: %s' % administrativo, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'adddocente':
            try:
                persona = Persona.objects.get(pk=request.POST['id'])
                if persona.es_profesor():
                    return JsonResponse({"result": "bad", "mensaje": u"Ya existe un perfil de docente para este usuario."})
                profesor = Profesor(persona=persona,
                                    activo=True,
                                    fechaingreso=datetime.now().date(),
                                    coordinacion=Coordinacion.objects.all()[0],
                                    dedicacion=TiempoDedicacionDocente.objects.all()[0])
                profesor.save(request)
                grupo = Group.objects.get(pk=PROFESORES_GROUP_ID)
                usuarionuevo = False
                if not persona.usuario:
                    username = calculate_username(persona)
                    generar_usuario(persona, username, PROFESORES_GROUP_ID)
                    usuarionuevo = True

                grupo.user_set.add(persona.usuario)
                grupo.save()
                persona.crear_perfil(profesor=profesor)
                if not persona.emailinst:
                    persona.emailinst=u"%s@unemi.edu.ec"%persona.usuario.username
                    persona.save(request)

                resetear = request.POST.get('resetear', '') == 'on'
                if resetear:
                    resetear_clave(persona)

                enviar_correo_credenciales(request, persona, usuarionuevo, resetear, 'DOCENTE', CUENTAS_CORREOS[4][1])

                log(u'Adiciono profesor: %s' % profesor, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addexterno':
            try:
                persona = Persona.objects.get(pk=request.POST['id'])
                if persona.es_externo():
                    return JsonResponse({"result": "bad", "mensaje": u"Ya existe un perfil externo para este usuario."})

                # Guardo externo
                externo = Externo(
                    persona=persona,
                    nombrecomercial='',
                    institucionlabora='',
                    cargodesempena=''
                )
                externo.save(request)

                # Guardo perfil externo
                persona.crear_perfil(externo=externo)
                persona.mi_perfil()

                log(u'Adiciono perfil externo: %s' % externo, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'resetear':
            try:
                per = Persona.objects.get(pk=request.POST['id'])
                if not per.emailinst:
                    per.emailinst = per.usuario.username+'@unemi.edu.ec'
                    per.save(request)
                resetear_clave(per)
                log(u'Reseteo clave de la persona del modulo de cliente externo: %s' % per, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addusuario':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                # Consulto la persona externa
                personaexterna = Persona.objects.get(pk=int(encrypt(request.POST['id'])))

                # Crear el usuario para el SGA/SAGEST, etc
                nombreusuario = calculate_username(personaexterna)
                anio = "*" + str(personaexterna.nacimiento)[0:4] if personaexterna.nacimiento else ''
                password = personaexterna.identificacion() + anio
                try:
                    emailinst_ = '{}@unemi.edu.ec'.format(nombreusuario)
                    user = User.objects.create_user(nombreusuario, emailinst_, password)
                except Exception as ex:
                    raise NameError(f'La persona con usuario "{nombreusuario}" ya se encuentra registrada.')

                user.emailinst = '{}@unemi.edu.ec'.format(nombreusuario)
                user.save()
                personaexterna.usuario = user
                personaexterna.email = user.emailinst
                personaexterna.save()
                personaexterna.cambiar_clave()

                log(u'%s creó usuario para la persona %s:' % (request.session['persona'], personaexterna), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar el registro. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addgrupo':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                # Consulto la persona externa
                persona = Externo.objects.get(pk=int(encrypt(request.POST['id']))).persona

                # Consulto el grupo
                grupo = Group.objects.get(pk=request.POST['grupo'])

                # Asigno el grupo al usuario
                grupo.user_set.add(persona.usuario)
                grupo.save()

                log(u'%s asignó grupo %s al usuario: %s' % (request.session['persona'], grupo, persona.usuario.username), request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True, "personaid": persona.id})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'delgrupo':
            try:
                personagrupo = Persona.objects.get(pk=request.POST['id'])
                grupo = Group.objects.get(pk=request.POST['idg'])
                if grupo.id in [PROFESORES_GROUP_ID, ALUMNOS_GROUP_ID, EMPLEADORES_GRUPO_ID]:
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar del grupo seleccionado."})

                grupo.user_set.remove(personagrupo.usuario)
                grupo.save()

                log(u'Elimino de grupo de usuarios: %s - %s' % (grupo, personagrupo), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'actualizarperfilprincipal':
                try:
                    if request.GET['idp']:
                        pu = PerfilUsuario.objects.get(pk=int(encrypt(request.GET['idp'])))
                        pu.inscripcionprincipal = False if pu.inscripcionprincipal else True
                        pu.save(request)
                        log(u'Modificó la inscripción principal en el modulo de cliente externo: %s' % pu, request, "edit")
                        return JsonResponse({"result": True})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": "%s" % ex.__str__()})

            if action == 'add':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_administrativos')
                    data['title'] = u'Adicionar Clientes Externos'
                    form = ClienteExternoForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, "rec_clienteexterno/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_administrativos')
                    data['title'] = u'Editar cliente'
                    data['persona'] = clientexter = Persona.objects.get(pk=request.GET['id'])
                    nombrecomercial = clientexter.nombre_completo()
                    nombrecontacto = ''
                    telefonocontacto = ''
                    if clientexter.externo_set.exists():
                        externo = clientexter.externo_set.all()[0]
                        nombrecomercial = externo.nombrecomercial
                        nombrecontacto = externo.nombrecontacto
                        telefonocontacto = externo.telefonocontacto
                    form = ClienteExternoForm(initial={'nombres': clientexter.nombres if clientexter.tipopersona == 1 else '',
                                                       'nombreempresa': clientexter.nombres if clientexter.tipopersona == 2 else '',
                                                       'nombrecomercial': nombrecomercial,
                                                       'nombrecontacto': nombrecontacto,
                                                       'telefonocontacto': telefonocontacto,
                                                       'apellido1': clientexter.apellido1,
                                                       'apellido2': clientexter.apellido2,
                                                       'cedula': clientexter.cedula,
                                                       'ruc': clientexter.ruc,
                                                       'tipopersona': clientexter.tipopersona,
                                                       'contribuyenteespecial': clientexter.contribuyenteespecial,
                                                       'sexo': clientexter.sexo,
                                                       'pasaporte': clientexter.pasaporte,
                                                       'nacimiento': clientexter.nacimiento,
                                                       'pais': clientexter.pais,
                                                       'provincia': clientexter.provincia,
                                                       'canton': clientexter.canton,
                                                       'parroquia': clientexter.parroquia,
                                                       'sector': clientexter.sector,
                                                       'direccion': clientexter.direccion,
                                                       'direccion2': clientexter.direccion2,
                                                       'num_direccion': clientexter.num_direccion,
                                                       'telefono': clientexter.telefono,
                                                       'telefono_conv': clientexter.telefono_conv,
                                                       'email': clientexter.email})
                    form.editar(clientexter)
                    data['form'] = form
                    return render(request, "rec_clienteexterno/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    # puede_realizar_accion(request, 'sagest.puede_modificar_catalogo')
                    data['title'] = u'Eliminar Cliente'
                    data['externo'] = Externo.objects.get(pk=request.GET['id'])
                    return render(request, 'rec_clienteexterno/delete.html', data)
                except Exception as ex:
                    pass

            if action == 'cuentas':
                try:
                    data['title'] = u'Cuentas Bancarias'
                    data['persona'] = persona = Persona.objects.get(pk=int(request.GET['id']))
                    return render(request, "rec_clienteexterno/cuentas.html", data)
                except:
                    pass

            if action == 'addcuentabancaria':
                try:
                    data['title'] = u'Adicionar cuenta bancaria'
                    data['form'] = CuentaBancariaPersonaForm()
                    data['persona'] = persona = Persona.objects.get(pk=int(request.GET['persona']))
                    return render(request, "rec_clienteexterno/addcuentabancaria.html", data)
                except:
                    pass

            if action == 'editcuentabancaria':
                try:
                    data['title'] = u'Editar cuenta bancaria'
                    data['persona'] = persona = Persona.objects.get(pk=int(request.GET['persona']))
                    data['cuentabancaria'] = cuentabancaria = CuentaBancariaPersona.objects.get(pk=int(request.GET['id']))
                    data['form'] = CuentaBancariaPersonaForm(initial={'numero': cuentabancaria.numero,
                                                                      'banco': cuentabancaria.banco,
                                                                      'tipocuentabanco': cuentabancaria.tipocuentabanco})
                    return render(request, "rec_clienteexterno/editcuentabancaria.html", data)
                except:
                    pass

            if action == 'delcuentabancaria':
                try:
                    data['title'] = u'Eliminar cuenta bancaria'
                    data['cuentabancaria'] = cuentabancaria = CuentaBancariaPersona.objects.get(pk=int(request.GET['id']))
                    return render(request, "rec_clienteexterno/delcuentabancaria.html", data)
                except:
                    pass

            if action == 'addadministrativo':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_administrativos')
                    data['title'] = u'Crear perfil de administrativo'
                    data['persona'] = persona = Persona.objects.get(pk=request.GET['id'])
                    data['tieneusuario'] = persona.usuario
                    return render(request, 'rec_clienteexterno/addadministrativo.html', data)
                except Exception as ex:
                    pass

            if action == 'adddocente':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_profesores')
                    data['title'] = u'Crear perfil de profesor'
                    data['persona'] = persona = Persona.objects.get(pk=request.GET['id'])
                    data['tieneusuario'] = persona.usuario
                    return render(request, "rec_clienteexterno/adddocente.html", data)
                except Exception as ex:
                    pass

            if action == 'addexterno':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_administrativos')
                    data['title'] = u'Crear perfil de externo'
                    data['persona'] = persona = Persona.objects.get(pk=request.GET['id'])
                    return render(request, 'rec_clienteexterno/addexterno.html', data)
                except Exception as ex:
                    pass

            if action == 'resetear':
                try:
                    data['title'] = u'Resetear clave del usuario'
                    data['p'] = Persona.objects.get(pk=request.GET['id'])
                    # puede_modificar_inscripcion(request, inscripcion)
                    return render(request, "rec_clienteexterno/resetear.html", data)
                except Exception as ex:
                    pass

            elif action == 'addgrupo':
                try:
                    data['title'] = u'Adicionar Grupo'
                    data['personaexterna'] = Externo.objects.get(persona_id=int(encrypt(request.GET['id'])))
                    data['grupos'] = Group.objects.all().order_by('name')
                    template = get_template("rec_clienteexterno/addgrupo.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'delgrupo':
                try:
                    data['title'] = u'Eliminar de grupo'
                    data['personagrupo'] = Persona.objects.get(pk=request.GET['id'])
                    data['grupo'] = Group.objects.get(pk=request.GET['idg'])
                    return render(request, "rec_clienteexterno/delgrupo.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Listado de Clientes'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        cliente = Persona.objects.filter(Q(nombres__icontains=search) |
                                                         Q(apellido1__icontains=search) |
                                                         Q(apellido2__icontains=search) |
                                                         Q(cedula__icontains=search) |
                                                         Q(ruc__icontains=search) |
                                                         Q(externo__nombrecomercial__icontains=search) |
                                                         Q(pasaporte__icontains=search)).distinct()
                    else:
                        cliente = Persona.objects.filter(Q(apellido1__icontains=ss[0]) &
                                                         Q(apellido2__icontains=ss[1])).distinct()
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    cliente = Persona.objects.filter(id=ids).distinct()
                else:
                    cliente = Persona.objects.all()
                paging = MiPaginador(cliente, 25)
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
                data['clientes'] = page.object_list
                data['app'] = request.session['tiposistema']

                data['grupo_administrativos'] = variable_valor('ADMINISTRATIVOS_GROUP_ID')
                data['grupo_docentes'] = PROFESORES_GROUP_ID
                data['grupo_estudiantes'] = ALUMNOS_GROUP_ID
                data['grupo_aspirantes'] = 199
                data['grupo_empleadores'] = EMPLEADORES_GRUPO_ID

                return render(request, "rec_clienteexterno/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect(f"/?info={ex.__str__()}")


def enviar_correo_credenciales(request, persona, usuarionuevo, resetear, tipousuario, cuentascorreos):
    correo = persona.lista_emails()
    anio = "*" + str(persona.nacimiento)[0:4] if persona.nacimiento else ''
    if persona.cedula:
        password = persona.cedula.strip() + anio
    elif persona.pasaporte:
        password = persona.pasaporte.strip() + anio
    else:
        password = persona.ruc.strip() + anio
    send_html_mail("Creación de cuenta institucional", "emails/nuevacuentacorreo_v2.html",
                   {'sistema': request.session['nombresistema'], 'persona': persona, 'nuevo': usuarionuevo,
                    'resetear': resetear, 'pass': password,
                    't': miinstitucion(), 'tipo_usuario': tipousuario,
                    'usuario': persona.usuario.username, 'tiposistema_': 2}, correo, [],
                   cuenta=cuentascorreos)