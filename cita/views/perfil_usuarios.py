# -*- coding: UTF-8 -*-
import random
import sys
import calendar
from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template.loader import get_template
from django.shortcuts import render, redirect
from unidecode import unidecode

from django import forms
from decorators import secure_module
from med.models import PersonaExamenFisico
from poli.forms import PersonaPrimariaForm
from sagest.forms import DatosPersonalesForm, DatosNacimientoForm, DatosDomicilioForm, FamiliarForm, ContactoEmergenciaForm, DatosMedicosForm, PersonaEnfermedadForm, TitulacionPersonaForm
from sagest.models import DistributivoPersona
from settings import EMAIL_DOMAIN
from poli.views.commonviews import adduserdata
from sga.funciones import generar_nombre, log, variable_valor, elimina_tildes
from sga.models import Persona, PersonaDocumentoPersonal, PersonaDatosFamiliares, Externo, PersonaEnfermedad, Titulacion, Titulo, CUENTAS_CORREOS, Graduado
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
from poli.models import *
from poli.acciones import *
from django.db.models import Q


@login_required(redirect_field_name='ret', login_url='/unemideportes?next=login')
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    hoy = datetime.now().date()
    usuario = request.user
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    esestudiante = perfilprincipal.es_estudiante()
    data['puede_modificar_hv'] = variable_valor('PUEDE_MODIFICAR_HV')
    data['solo_perfil_externo'] = solo_perfil_externo = len(persona.mis_perfilesusuarios()) == 1 and persona.tiene_usuario_externo()
    data['es_instructor'] = es_instructor = persona.instructorpolideportivo_set.filter(status=True).exists()
    if request.method == 'POST':
        action = request.POST['action']

        # GESTIONAR PERFIL
        if action == 'editfoto':
            try:
                foto = request.FILES['foto']
                max_tamano = 2 * 1024 * 1024  # 2 MB
                name_ = foto._name
                ext = name_[name_.rfind("."):]
                if not ext.lower() in ['.png', '.jpg', '.jpeg']:
                    raise NameError('Solo se permite archivos de formato .png, .jpg, .jpeg')

                if foto.size > max_tamano:
                    raise NameError('Archivo supera los 2 megas permitidos')
                # Asignar un nombre personalizado al archivo
                foto.name = unidecode(generar_nombre(f"foto_{persona.usuario}", foto._name))
                persona.foto(foto, request)
                persona = Persona.objects.get(id=persona.id)
                request.session['persona'] = persona
                log(u'Edito foto de perfil de ususario: %s' % foto, request, "edit")
                return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error:{ex}'})

        elif action == 'editdatospersonales':
            try:
                persona = request.session['persona']
                persona = Persona.objects.get(id=persona.id)
                f = DatosPersonalesForm(request.POST, request.FILES)
                if esestudiante:
                    f.es_estudiante()
                if not f.is_valid():
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
                if 'archivocedula' in request.FILES:
                    arch = request.FILES['archivocedula']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        raise NameError("Error, el tamaño del archivo de cédula es mayor a 4 Mb.")
                    if not exte.lower() == 'pdf':
                        raise NameError("Solo se permiten archivos .pdf")
                if 'archivoraza' in request.FILES:
                    arch_r = request.FILES['archivoraza']
                    extension = arch_r._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch_r.size > 4194304:
                        raise NameError("Error, el tamaño del archivo de etnia es mayor a 4 Mb.")
                    if not exte.lower() in ['pdf']:
                        raise NameError("Solo se permiten archivos .pdf")
                persona.pasaporte = f.cleaned_data['pasaporte']
                persona.anioresidencia = f.cleaned_data['anioresidencia']
                persona.nacimiento = f.cleaned_data['nacimiento']
                if not esestudiante:
                    persona.telefonoextension = f.cleaned_data['extension']
                persona.sexo = f.cleaned_data['sexo']
                persona.lgtbi = f.cleaned_data['lgtbi']
                persona.email = f.cleaned_data['email']
                persona.libretamilitar = f.cleaned_data['libretamilitar']
                persona.eszurdo = f.cleaned_data['eszurdo']
                persona.save(request)
                personaextension = persona.datos_extension()
                personaextension.estadocivil = f.cleaned_data['estadocivil']
                personaextension.save(request)

                if 'archivocedula' in request.FILES:
                    newfile = request.FILES['archivocedula']
                    newfile._name = generar_nombre("cedula", newfile._name)

                    documento = persona.documentos_personales()
                    if documento is None:
                        documento = PersonaDocumentoPersonal(persona=persona,
                                                             cedula=newfile,
                                                             estadocedula=1
                                                             )
                    else:
                        documento.cedula = newfile
                        documento.estadocedula = 1

                    documento.save(request)

                if 'papeleta' in request.FILES:
                    newfile = request.FILES['papeleta']
                    newfile._name = generar_nombre("papeleta", newfile._name)

                    documento = persona.documentos_personales()
                    if documento is None:
                        documento = PersonaDocumentoPersonal(persona=persona,
                                                             papeleta=newfile,
                                                             estadopapeleta=1
                                                             )
                    else:
                        documento.papeleta = newfile
                        documento.estadopapeleta = 1

                    documento.save(request)

                if 'archivolibretamilitar' in request.FILES:
                    newfile = request.FILES['archivolibretamilitar']
                    newfile._name = generar_nombre("libretamilitar", newfile._name)

                    documento = persona.documentos_personales()
                    if documento is None:
                        documento = PersonaDocumentoPersonal(persona=persona,
                                                             libretamilitar=newfile,
                                                             estadolibretamilitar=1
                                                             )
                    else:
                        documento.libretamilitar = newfile
                        documento.estadolibretamilitar = 1

                    documento.save(request)

                perfil = persona.mi_perfil()
                perfil.raza = f.cleaned_data['raza']
                perfil.nacionalidadindigena = f.cleaned_data['nacionalidadindigena']
                if 'archivoraza' in request.FILES:
                    arch_r._name = generar_nombre("archivoraza", arch_r._name)
                    perfil.archivoraza = arch_r
                    perfil.estadoarchivoraza = 1
                else:
                    if perfil.raza.id != 1:
                        perfil.archivoraza = None
                        perfil.estadoarchivoraza = None
                perfil.save(request)
                log(u'Modifico datos personales: %s' % persona, request, "edit")
                return JsonResponse({'result': False, 'mensaje': 'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos: {ex}'})

        elif action == 'editdatosnacimiento':
            try:
                persona = Persona.objects.get(id=persona.id)
                f = DatosNacimientoForm(request.POST)
                if not f.is_valid():
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
                persona.paisnacimiento = f.cleaned_data['paisnacimiento']
                persona.provincianacimiento = f.cleaned_data['provincianacimiento']
                persona.cantonnacimiento = f.cleaned_data['cantonnacimiento']
                persona.parroquianacimiento = f.cleaned_data['parroquianacimiento']
                persona.paisnacionalidad = f.cleaned_data['paisnacionalidad']
                persona.save(request)
                request.session['persona'] = persona
                log(u'Modifico datos de nacimiento: %s' % persona, request, "edit")
                return JsonResponse({'result': False, 'mensaje': 'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos {ex}'})

        elif action == 'editdatosdomicilio':
            try:
                if 'archivocroquis' in request.FILES:
                    newfile = request.FILES['archivocroquis']
                    if newfile.size > 2194304:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 2Mb"})

                if 'archivoplanillaluz' in request.FILES:
                    newfile = request.FILES['archivoplanillaluz']
                    if newfile.size > 2194304:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 2Mb"})

                if 'serviciosbasico' in request.FILES:
                    newfile2 = request.FILES['serviciosbasico']
                    if newfile2.size > 2194304:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 2Mb"})

                persona = Persona.objects.get(id=persona.id)
                documento_p = persona.documentos_personales()
                f = DatosDomicilioForm(request.POST)
                if 'pais' in request.POST and request.POST['pais'] and int(request.POST['pais']) == 1:
                    if 'provincia' in request.POST and not request.POST['provincia']:
                        raise NameError('Debe ingresa una provincia')
                    if 'canton' in request.POST and not request.POST['canton']:
                        raise NameError('Debe ingresa una canton')
                    if 'parroquia' in request.POST and not request.POST['parroquia']:
                        raise NameError('Debe ingresa una parroquia')
                if not f.is_valid():
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})

                newfile = None
                persona.pais = f.cleaned_data['pais']
                persona.provincia = f.cleaned_data['provincia']
                persona.canton = f.cleaned_data['canton']
                persona.sector = f.cleaned_data['sector']
                persona.parroquia = f.cleaned_data['parroquia']
                persona.direccion = f.cleaned_data['direccion']
                persona.direccion2 = f.cleaned_data['direccion2']
                persona.ciudadela = f.cleaned_data['ciudadela']
                persona.num_direccion = f.cleaned_data['num_direccion']
                persona.telefono_conv = f.cleaned_data['telefono_conv']
                persona.telefono = f.cleaned_data['telefono']
                persona.tipocelular = f.cleaned_data['tipocelular']
                persona.referencia = f.cleaned_data['referencia']
                persona.zona = int(f.cleaned_data['zona'])
                persona.save(request)
                if 'archivocroquis' in request.FILES:
                    newfile = request.FILES['archivocroquis']
                    newfile._name = generar_nombre("croquis_", newfile._name)
                    persona.archivocroquis = newfile
                    persona.save(request)

                if 'archivoplanillaluz' in request.FILES:
                    newfile = request.FILES['archivoplanillaluz']
                    newfile._name = generar_nombre("planilla_luz_", newfile._name)
                    persona.archivoplanillaluz = newfile
                    persona.save(request)

                if 'serviciosbasico' in request.FILES:
                    newfile = request.FILES['serviciosbasico']
                    newfile._name = generar_nombre("serviciobasico_", newfile._name)
                    if documento_p:
                        documento_p.serviciosbasico = newfile
                        documento_p.estadoserviciosbasico = 1
                        documento_p.save(request)
                request.session['persona'] = persona
                log(u'Modifico datos de domicilio: %s' % persona, request, "edit")
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos {ex}'})

        # DATOS FAMILIARES
        elif action == 'addfamiliar':
            try:
                persona = request.session['persona']
                f = FamiliarForm(request.POST)
                if f.is_valid():
                    edit_d = eval(request.POST.get('edit_d', ''))
                    cedula = f.cleaned_data['identificacion'].strip()
                    if persona.personadatosfamiliares_set.filter(identificacion=f.cleaned_data['identificacion'], status=True).exists():
                        raise NameError('El familiar se encuentra registrado.')
                    nombres = f"{f.cleaned_data['apellido1']} {f.cleaned_data['apellido2']} {f.cleaned_data['nombre']}"
                    familiar = PersonaDatosFamiliares(persona=persona,
                                                      identificacion=cedula,
                                                      nombre=nombres,
                                                      fallecido=f.cleaned_data['fallecido'],
                                                      nacimiento=f.cleaned_data['nacimiento'],
                                                      parentesco=f.cleaned_data['parentesco'],
                                                      tienediscapacidad=f.cleaned_data['tienediscapacidad'],
                                                      telefono=f.cleaned_data['telefono'],
                                                      telefono_conv=f.cleaned_data['telefono_conv'],
                                                      niveltitulacion=f.cleaned_data['niveltitulacion'],
                                                      ingresomensual=f.cleaned_data['ingresomensual'],
                                                      formatrabajo=f.cleaned_data['formatrabajo'],
                                                      trabajo=f.cleaned_data['trabajo'],
                                                      convive=f.cleaned_data['convive'],
                                                      sustentohogar=f.cleaned_data['sustentohogar'],
                                                      # rangoedad=f.cleaned_data['rangoedad'],
                                                      essustituto=f.cleaned_data['essustituto'],
                                                      autorizadoministerio=f.cleaned_data['autorizadoministerio'],
                                                      tipodiscapacidad=f.cleaned_data['tipodiscapacidad'],
                                                      porcientodiscapacidad=f.cleaned_data['porcientodiscapacidad'],
                                                      carnetdiscapacidad=f.cleaned_data['carnetdiscapacidad'],
                                                      institucionvalida=f.cleaned_data['institucionvalida'],
                                                      tipoinstitucionlaboral=f.cleaned_data['tipoinstitucionlaboral'],
                                                      negocio=f.cleaned_data['negocio'],
                                                      esservidorpublico=f.cleaned_data['esservidorpublico'],
                                                      bajocustodia=f.cleaned_data['bajocustodia'],
                                                      centrocuidado=f.cleaned_data['centrocuidado'] if f.cleaned_data['centrocuidado'] else 0,
                                                      centrocuidadodesc=f.cleaned_data['centrocuidadodesc'],
                                                      tienenegocio=f.cleaned_data['tienenegocio'])
                    familiar.save(request)
                    if 'cedulaidentidad' in request.FILES:
                        newfile = request.FILES['cedulaidentidad']
                        newfile._name = generar_nombre("cedulaidentidad_", newfile._name)
                        familiar.cedulaidentidad = newfile
                        familiar.save(request)
                    if 'ceduladiscapacidad' in request.FILES:
                        newfile = request.FILES['ceduladiscapacidad']
                        newfile._name = generar_nombre("ceduladiscapacidad_", newfile._name)
                        familiar.ceduladiscapacidad = newfile
                        familiar.save(request)
                    if 'archivoautorizado' in request.FILES:
                        newfile = request.FILES['archivoautorizado']
                        newfile._name = generar_nombre("archivoautorizado_", newfile._name)
                        familiar.archivoautorizado = newfile
                        familiar.save(request)
                    if 'cartaconsentimiento' in request.FILES:
                        newfile = request.FILES['cartaconsentimiento']
                        newfile._name = generar_nombre(f"cartaconsentimiento_{persona.usuario.username}", newfile._name)
                        familiar.cartaconsentimiento = newfile
                        familiar.save(request)
                    if 'archivocustodia' in request.FILES:
                        newfile = request.FILES['archivocustodia']
                        newfile._name = generar_nombre(f"archivocustodia_{persona.usuario.username}", newfile._name)
                        familiar.archivocustodia = newfile
                        familiar.save(request)

                    pers = Persona.objects.filter(Q(pasaporte=cedula) | Q(cedula=cedula) | Q(pasaporte=('VS' + cedula)) | Q(cedula=cedula[2:]), status=True).first()
                    if not pers:
                        pers = Persona(cedula=f.cleaned_data['identificacion'],
                                       nombres=f.cleaned_data['nombre'],
                                       apellido1=f.cleaned_data['apellido1'],
                                       apellido2=f.cleaned_data['apellido2'],
                                       nacimiento=f.cleaned_data['nacimiento'],
                                       telefono=f.cleaned_data['telefono'],
                                       sexo=f.cleaned_data['sexo'],
                                       telefono_conv=f.cleaned_data['telefono_conv'],
                                       )
                        pers.save(request)
                        log(u'Adiciono persona: %s' % persona, request, "add")
                    elif len(pers.mis_perfilesusuarios()) == 1 and pers.tiene_usuario_externo():
                        pers.cedula = f.cleaned_data['identificacion']
                        pers.nombres = f.cleaned_data['nombre']
                        pers.apellido1 = f.cleaned_data['apellido1']
                        pers.apellido2 = f.cleaned_data['apellido2']
                        pers.nacimiento = f.cleaned_data['nacimiento']
                        pers.telefono = f.cleaned_data['telefono']
                        pers.sexo = f.cleaned_data['sexo']
                        pers.telefono_conv = f.cleaned_data['telefono_conv']
                        pers.save(request)
                        log(u'Edito familiar de usuario: %s' % pers, request, "edit")
                    if not pers.tiene_perfil():
                        if not Externo.objects.filter(persona=pers, status=True):
                            externo = Externo(persona=pers)
                            externo.save(request)
                            log(u'Adiciono externo: %s' % pers, request, "add")
                        perfil = PerfilUsuario(persona=pers, externo=externo)
                        perfil.save(request)
                        log(u'Adiciono perfil de usuario: %s' % perfil, request, "add")

                    perfil_i = pers.mi_perfil()
                    if not edit_d and perfil_i.tienediscapacidad:
                        familiar.tienediscapacidad = perfil_i.tienediscapacidad
                        familiar.tipodiscapacidad = perfil_i.tipodiscapacidad
                        familiar.porcientodiscapacidad = perfil_i.porcientodiscapacidad
                        familiar.carnetdiscapacidad = perfil_i.carnetdiscapacidad
                        familiar.institucionvalida = perfil_i.institucionvalida
                        familiar.ceduladiscapacidad = perfil_i.archivo.name if perfil_i.archivo else ''
                        familiar.archivoautorizado = perfil_i.archivovaloracion.name if perfil_i.archivovaloracion else ''
                    elif f.cleaned_data['tienediscapacidad']:
                        perfil_i.tienediscapacidad = f.cleaned_data['tienediscapacidad']
                        perfil_i.tipodiscapacidad = f.cleaned_data['tipodiscapacidad']
                        perfil_i.porcientodiscapacidad = f.cleaned_data['porcientodiscapacidad'] if f.cleaned_data['porcientodiscapacidad'] else 0
                        perfil_i.carnetdiscapacidad = f.cleaned_data['carnetdiscapacidad']
                        perfil_i.institucionvalida = f.cleaned_data['institucionvalida']
                        if 'ceduladiscapacidad' in request.FILES:
                            newfile = request.FILES['ceduladiscapacidad']
                            newfile._name = generar_nombre("archivosdiscapacidad_", newfile._name)
                            perfil_i.archivo = newfile
                            perfil_i.estadoarchivodiscapacidad = 1
                        if 'archivoautorizado' in request.FILES:
                            newfile = request.FILES['archivoautorizado']
                            newfile._name = generar_nombre("archivovaloracionmedica_", newfile._name)
                            perfil_i.archivovaloracion = newfile
                        perfil_i.save(request)
                    if f.cleaned_data['parentesco'].id in [14, 11] and not persona.apellido1 in [pers.apellido1, pers.apellido2]:
                        familiar.aprobado = False
                    if f.cleaned_data['parentesco'].id == 13 and not pers.personadatosfamiliares_set.filter(personafamiliar=persona, status=True).exists():
                        fam_ = PersonaDatosFamiliares(persona=pers,
                                                      personafamiliar=persona,
                                                      identificacion=persona.cedula,
                                                      nombre=persona.nombre_completo_inverso(),
                                                      nacimiento=persona.nacimiento,
                                                      parentesco=f.cleaned_data['parentesco'],
                                                      telefono=persona.telefono,
                                                      telefono_conv=persona.telefono_conv,
                                                      convive=f.cleaned_data['convive'])
                        fam_.save(request)
                        perfil_fam = persona.mi_perfil()
                        if perfil_fam.tienediscapacidad:
                            fam_.tienediscapacidad = perfil_fam.tienediscapacidad
                            fam_.tipodiscapacidad = perfil_fam.tipodiscapacidad
                            fam_.porcientodiscapacidad = perfil_fam.porcientodiscapacidad
                            fam_.carnetdiscapacidad = perfil_fam.carnetdiscapacidad
                            fam_.institucionvalida = perfil_fam.institucionvalida
                            fam_.ceduladiscapacidad = perfil_fam.archivo.name if perfil_i.archivo else ''
                            fam_.archivoautorizado = perfil_fam.archivovaloracion.name if perfil_i.archivovaloracion else ''
                        fam_.save(request)
                    familiar.personafamiliar = pers
                    familiar.save(request)
                    if familiar.parentesco.id in [11, 14] or familiar.bajocustodia:
                        per_extension = persona.personaextension_set.filter(status=True).first()
                        hijos = per_extension.hijos if per_extension.hijos else 0
                        per_extension.hijos = hijos + 1
                        per_extension.save(request)
                    log(u'Adiciono familiar: %s' % familiar, request, "add")
                    return JsonResponse({'result': False, 'mensaje': 'Guardado con exito'})
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': f'{ex}'})

        elif action == 'editfamiliar':
            try:
                persona = request.session['persona']
                f = FamiliarForm(request.POST)
                f.edit()
                if f.is_valid():
                    familiar = PersonaDatosFamiliares.objects.get(pk=encrypt_id(request.POST['id']))
                    edit_d = eval(request.POST.get('edit_d', ''))
                    cedula = f.cleaned_data['identificacion'].strip()
                    if persona.personadatosfamiliares_set.filter(identificacion=cedula, status=True).exclude(id=familiar.id).exists():
                        raise NameError(u'El familiar se encuentra registrado.')
                    nombres = f"{f.cleaned_data['apellido1']} {f.cleaned_data['apellido2']} {f.cleaned_data['nombre']}"
                    pers = Persona.objects.filter(Q(pasaporte=cedula) | Q(cedula=cedula) | Q(pasaporte=('VS' + cedula)) | Q(cedula=cedula[2:]), status=True).first()
                    familiar.fallecido = f.cleaned_data['fallecido']
                    familiar.parentesco = f.cleaned_data['parentesco']
                    familiar.tienediscapacidad = f.cleaned_data['tienediscapacidad']
                    familiar.trabajo = f.cleaned_data['trabajo']
                    familiar.niveltitulacion = f.cleaned_data['niveltitulacion']
                    familiar.ingresomensual = f.cleaned_data['ingresomensual']
                    familiar.formatrabajo = f.cleaned_data['formatrabajo']
                    familiar.convive = f.cleaned_data['convive']
                    familiar.sustentohogar = f.cleaned_data['sustentohogar']
                    # familiar.rangoedad = f.cleaned_data['rangoedad']
                    familiar.tienenegocio = f.cleaned_data['tienenegocio']
                    familiar.esservidorpublico = f.cleaned_data['esservidorpublico']
                    familiar.bajocustodia = f.cleaned_data['bajocustodia']
                    familiar.centrocuidado = f.cleaned_data['centrocuidado'] if f.cleaned_data['centrocuidado'] else 0
                    familiar.centrocuidadodesc = f.cleaned_data['centrocuidadodesc']
                    familiar.negocio = ''
                    familiar.tipoinstitucionlaboral = f.cleaned_data['tipoinstitucionlaboral']
                    if familiar.tienenegocio:
                        familiar.negocio = f.cleaned_data['negocio']
                    familiar.save(request)
                    if 'cedulaidentidad' in request.FILES:
                        newfile = request.FILES['cedulaidentidad']
                        newfile._name = generar_nombre("cedulaidentidad_", newfile._name)
                        familiar.cedulaidentidad = newfile
                        familiar.save(request)
                    if 'ceduladiscapacidad' in request.FILES:
                        newfile = request.FILES['ceduladiscapacidad']
                        newfile._name = generar_nombre("ceduladiscapacidad_", newfile._name)
                        familiar.ceduladiscapacidad = newfile
                        familiar.save(request)
                    if 'cartaconsentimiento' in request.FILES:
                        newfile = request.FILES['cartaconsentimiento']
                        newfile._name = generar_nombre(f"cartaconsentimiento_{persona.usuario.username}", newfile._name)
                        familiar.cartaconsentimiento = newfile
                        familiar.save(request)
                    if 'archivocustodia' in request.FILES:
                        newfile = request.FILES['archivocustodia']
                        newfile._name = generar_nombre(f"archivocustodia_{persona.usuario.username}", newfile._name)
                        familiar.archivocustodia = newfile
                        familiar.save(request)

                    if f.cleaned_data['tienediscapacidad']:
                        if 'archivoautorizado' in request.FILES:
                            newfile = request.FILES['archivoautorizado']
                            newfile._name = generar_nombre("archivoautorizado_", newfile._name)
                            familiar.archivoautorizado = newfile
                            familiar.save(request)
                    else:
                        familiar.archivoautorizado = None
                        familiar.save(request)
                    if not pers:
                        pers = Persona(cedula=f.cleaned_data['identificacion'],
                                       nombres=f.cleaned_data['nombre'],
                                       apellido1=f.cleaned_data['apellido1'],
                                       apellido2=f.cleaned_data['apellido2'],
                                       nacimiento=f.cleaned_data['nacimiento'],
                                       telefono=f.cleaned_data['telefono'],
                                       sexo=f.cleaned_data['sexo'],
                                       telefono_conv=f.cleaned_data['telefono_conv'],
                                       )
                        pers.save(request)
                        log(u'Adiciono persona: %s' % persona, request, "add")
                    elif len(pers.mis_perfilesusuarios()) == 1 and pers.tiene_usuario_externo():
                        pers.cedula = cedula
                        pers.nombres = f.cleaned_data['nombre']
                        pers.apellido1 = f.cleaned_data['apellido1']
                        pers.apellido2 = f.cleaned_data['apellido2']
                        pers.nacimiento = f.cleaned_data['nacimiento']
                        pers.telefono = f.cleaned_data['telefono']
                        pers.sexo = f.cleaned_data['sexo']
                        pers.telefono_conv = f.cleaned_data['telefono_conv']
                        pers.save(request)
                        log(u'Edito familiar de usuario: %s' % pers, request, "edit")
                    if not pers.tiene_perfil():
                        if not Externo.objects.filter(persona=pers, status=True):
                            externo = Externo(persona=pers)
                            externo.save(request)
                            log(u'Adiciono externo: %s' % pers, request, "add")
                        perfil = PerfilUsuario(persona=pers, externo=externo)
                        perfil.save(request)
                        log(u'Adiciono perfil de usuario: %s' % perfil, request, "add")
                    if len(pers.mis_perfilesusuarios()) == 1 and pers.tiene_usuario_externo():
                        familiar.identificacion = cedula
                        familiar.nombre = nombres
                        familiar.nacimiento = f.cleaned_data['nacimiento']
                        familiar.telefono = f.cleaned_data['telefono']
                        familiar.telefono_conv = f.cleaned_data['telefono_conv']
                    else:
                        familiar.identificacion = pers.cedula
                        familiar.nombre = pers.nombre_completo_inverso()
                        familiar.nacimiento = pers.nacimiento
                        familiar.telefono = pers.telefono
                        familiar.telefono_conv = pers.telefono_conv
                    perfil_i = pers.mi_perfil()
                    if edit_d:
                        if f.cleaned_data['tienediscapacidad']:
                            familiar.essustituto = f.cleaned_data['essustituto']
                            familiar.autorizadoministerio = f.cleaned_data['autorizadoministerio']
                            familiar.tipodiscapacidad = f.cleaned_data['tipodiscapacidad']
                            familiar.porcientodiscapacidad = f.cleaned_data['porcientodiscapacidad']
                            familiar.carnetdiscapacidad = f.cleaned_data['carnetdiscapacidad']
                            familiar.institucionvalida = f.cleaned_data['institucionvalida']
                            perfil_i.tienediscapacidad = f.cleaned_data['tienediscapacidad']
                            perfil_i.tipodiscapacidad = f.cleaned_data['tipodiscapacidad']
                            perfil_i.porcientodiscapacidad = f.cleaned_data['porcientodiscapacidad'] if f.cleaned_data['porcientodiscapacidad'] else 0
                            perfil_i.carnetdiscapacidad = f.cleaned_data['carnetdiscapacidad']
                            perfil_i.institucionvalida = f.cleaned_data['institucionvalida']
                            if 'ceduladiscapacidad' in request.FILES:
                                newfile = request.FILES['ceduladiscapacidad']
                                newfile._name = generar_nombre("archivosdiscapacidad_", newfile._name)
                                perfil_i.archivo = newfile
                                perfil_i.estadoarchivodiscapacidad = 1
                            if 'archivoautorizado' in request.FILES:
                                newfile = request.FILES['archivoautorizado']
                                newfile._name = generar_nombre("archivovaloracionmedica_", newfile._name)
                                perfil_i.archivovaloracion = newfile
                            perfil_i.save(request)
                        else:
                            familiar.essustituto = False
                            familiar.autorizadoministerio = False
                            familiar.tipodiscapacidad = None
                            familiar.porcientodiscapacidad = None
                            familiar.carnetdiscapacidad = ''
                            familiar.institucionvalida = None
                            perfil_i.tienediscapacidad = False
                            perfil_i.tipodiscapacidad = None
                            perfil_i.porcientodiscapacidad = None
                            perfil_i.carnetdiscapacidad = ''
                            perfil_i.institucionvalida = None
                            perfil_i.save(request)
                    elif perfil_i.tienediscapacidad:
                        familiar.essustituto = f.cleaned_data['essustituto']
                        familiar.autorizadoministerio = f.cleaned_data['autorizadoministerio']
                        familiar.tienediscapacidad = perfil_i.tienediscapacidad
                        familiar.tipodiscapacidad = perfil_i.tipodiscapacidad
                        familiar.porcientodiscapacidad = perfil_i.porcientodiscapacidad
                        familiar.carnetdiscapacidad = perfil_i.carnetdiscapacidad
                        familiar.institucionvalida = perfil_i.institucionvalida
                        familiar.ceduladiscapacidad = perfil_i.archivo.name if perfil_i.archivo else ''
                        familiar.archivoautorizado = perfil_i.archivovaloracion.name if perfil_i.archivovaloracion else ''
                        perfil_i.save(request)
                    if f.cleaned_data['parentesco'].id in [14, 11] and not persona.apellido1 in [pers.apellido1, pers.apellido2]:
                        familiar.aprobado = False
                    if f.cleaned_data['parentesco'].id == 13 and not pers.personadatosfamiliares_set.filter(personafamiliar=persona, status=True).exists():
                        fam_ = PersonaDatosFamiliares(persona=pers,
                                                      personafamiliar=persona,
                                                      identificacion=persona.cedula,
                                                      nombre=persona.nombre_completo_inverso(),
                                                      nacimiento=persona.nacimiento,
                                                      parentesco=f.cleaned_data['parentesco'],
                                                      telefono=persona.telefono,
                                                      telefono_conv=persona.telefono_conv,
                                                      convive=f.cleaned_data['convive'])
                        fam_.save(request)
                        perfil_fam = persona.mi_perfil()
                        if perfil_fam.tienediscapacidad:
                            fam_.tienediscapacidad = perfil_fam.tienediscapacidad
                            fam_.tipodiscapacidad = perfil_fam.tipodiscapacidad
                            fam_.porcientodiscapacidad = perfil_fam.porcientodiscapacidad
                            fam_.carnetdiscapacidad = perfil_fam.carnetdiscapacidad
                            fam_.institucionvalida = perfil_fam.institucionvalida
                            fam_.ceduladiscapacidad = perfil_fam.archivo.name if perfil_i.archivo else ''
                            fam_.archivoautorizado = perfil_fam.archivovaloracion.name if perfil_i.archivovaloracion else ''
                        fam_.save(request)
                    familiar.personafamiliar = pers
                    familiar.save(request)
                    log(u'Modifico familiar: %s' % persona, request, "edit")
                    return JsonResponse({'result': False, 'mensaje': 'Guardado con exito'})
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': str(ex)})

        elif action == 'delfamiliar':
            try:
                persona = request.session['persona']
                familiar = PersonaDatosFamiliares.objects.get(pk=encrypt_id(request.POST['id']))
                familiar.status = False
                familiar.save(request)
                log(u'Elimino familiar: %s' % persona, request, "del")
                res_js = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        # DATOS MEDICOS
        elif action == 'editdatosmedicos':
            try:
                persona = request.session['persona']
                f = DatosMedicosForm(request.POST)
                if f.is_valid():
                    datosextension = persona.datos_extension()
                    examenfisico = persona.datos_examen_fisico()
                    datosextension.carnetiess = f.cleaned_data['carnetiess']
                    personaexamenfisico = PersonaExamenFisico.objects.filter(personafichamedica__personaextension=datosextension)[0]
                    personaexamenfisico.peso = f.cleaned_data['peso']
                    personaexamenfisico.talla = f.cleaned_data['talla']
                    personaexamenfisico.save(request)
                    persona.sangre = f.cleaned_data['sangre']
                    persona.save(request)
                    datosextension.save(request)

                    if 'archivotiposangre' in request.FILES:
                        newfile = request.FILES['archivotiposangre']
                        newfile._name = generar_nombre("tiposangre", newfile._name)

                        documento = persona.documentos_personales()
                        if documento is None:
                            documento = PersonaDocumentoPersonal(persona=persona,
                                                                 tiposangre=newfile,
                                                                 estadotiposangre=1
                                                                 )
                        else:
                            documento.tiposangre = newfile
                            documento.estadotiposangre = 1

                        documento.save(request)

                    log(u'Modifico datos de medicos basicos: %s' % persona, request, "edit")
                    return JsonResponse({'result': False, 'mensaje': 'Guardado con exito'})
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': f'{ex}'})

        elif action == 'editcontactoemergencia':
            try:
                f = ContactoEmergenciaForm(request.POST)
                if f.is_valid():
                    datosextension = persona.datos_extension()
                    datosextension.contactoemergencia = f.cleaned_data['contactoemergencia']
                    datosextension.parentescoemergencia = f.cleaned_data['parentescoemergencia']
                    datosextension.telefonoemergencia = f.cleaned_data['telefonoemergencia']
                    datosextension.correoemergencia = f.cleaned_data['correoemergencia']
                    datosextension.telefonoconvemergencia = f.cleaned_data['telefonoconvemergencia']
                    datosextension.save(request)
                    log(u'editó contacto de emergencia: %s' % datosextension, request, "edit")
                    return JsonResponse({'result': False, 'mensaje': 'Guardado con exito'})
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': f'{ex}'})

        # ENFERMEDADES
        elif action == 'addenfermedad':
            with transaction.atomic():
                try:
                    form = PersonaEnfermedadForm(request.POST, request.FILES)
                    if not form.is_valid():
                        for k, v in form.errors.items():
                            raise NameError(v[0])
                        # raise NameError(u"Complete todos los campos vacios.")
                    if PersonaEnfermedad.objects.filter(persona=persona, enfermedad=form.cleaned_data['enfermedad'],
                                                        status=True).exists():
                        raise NameError(u"Enfermedad seleccionada ya se encuentra registrada.")
                    personaenfermedad = PersonaEnfermedad(persona=persona, enfermedad=form.cleaned_data['enfermedad'])
                    personaenfermedad.save(request)
                    if 'archivomedico' in request.FILES:
                        newfile = request.FILES['archivomedico']
                        extension = newfile._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if newfile.size > 2194304:
                            raise NameError(u"El tamaño del archivo es mayor a 2 Mb.")
                        if not exte.lower() in ['pdf']:
                            raise NameError(u"Solo archivos .pdf,.jpg, .jpeg")
                        newfile._name = generar_nombre(str(elimina_tildes(personaenfermedad.enfermedad)), newfile._name)
                        personaenfermedad.archivomedico = newfile
                        personaenfermedad.save(request)
                    log(u'Adiciono enfermedad: %s' % personaenfermedad, request, "addenfermedad")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": f"Intentelo más tarde. {ex.__str__()}"}, safe=False)

        elif action == 'editenfermedad':
            try:
                with transaction.atomic():
                    personaenfermedad = PersonaEnfermedad.objects.get(pk=int(encrypt(request.POST['id'])))
                    form = PersonaEnfermedadForm(request.POST, request.FILES, instancia=personaenfermedad)
                    if form.is_valid():
                        if PersonaEnfermedad.objects.filter(persona=persona, enfermedad=form.cleaned_data['enfermedad'],
                                                            status=True).exclude(id=personaenfermedad.id).exists():
                            transaction.set_rollback(True)
                            return JsonResponse(
                                {"result": True, "mensaje": "Enfermedad seleccionada ya se encuentra registrada."},
                                safe=False)
                        personaenfermedad.enfermedad = form.cleaned_data['enfermedad']
                        personaenfermedad.save(request)
                        if 'archivomedico' in request.FILES:
                            newfile = request.FILES['archivomedico']
                            extension = newfile._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if newfile.size > 2194304:
                                transaction.set_rollback(True)
                                return JsonResponse(
                                    {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 2 Mb."})
                            if not exte.lower() in ['pdf']:
                                transaction.set_rollback(True)
                                return JsonResponse(
                                    {"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                            newfile._name = generar_nombre(str(personaenfermedad.enfermedad), newfile._name)
                            personaenfermedad.archivomedico = newfile
                            personaenfermedad.save(request)
                        log(u'Edicion de enfermedad de persona: %s' % personaenfermedad, request, "editenfermedad")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete todos los campos vacios."},
                                            safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'delenfermedad':
            try:
                with transaction.atomic():
                    enfermedad = PersonaEnfermedad.objects.get(pk=int(encrypt(request.POST['id'])))
                    enfermedad.status = False
                    enfermedad.save(request)
                    log(u'Elimino registro de enfermedad : %s - %s - %s', request, "del")
                    res_json = {"result": True}
            except Exception as ex:
                res_json = {'result': False, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        # ESTUDIOS
        elif action == 'addtitulacion':
            try:
                persona = request.session['persona']
                f = TitulacionPersonaForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extencion = arch._name.split('.')
                    exte = extencion[1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                    if not exte == 'pdf' and not exte == 'png' and not exte == 'jpg' and not exte == 'jpeg' and not exte == 'jpg':
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Archivo Título solo en formato .pdf, jpg, jpeg, png"})
                if 'registroarchivo' in request.FILES:
                    registroarchivo = request.FILES['registroarchivo']
                    extencion1 = registroarchivo._name.split('.')
                    exte1 = extencion1[1]
                    if registroarchivo.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                    if not exte1 == 'pdf' and not exte1 == 'png' and not exte1 == 'jpg' and not exte1 == 'jpeg' and not exte1 == 'jpg':
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Archivo SENESCYT solo en formato .pdf, jpg, jpeg, png"})
                if not f.is_valid():
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
                titulacion = Titulacion(persona=persona,
                                        titulo=f.cleaned_data['titulo'],
                                        areatitulo=f.cleaned_data['areatitulo'],
                                        fechainicio=f.cleaned_data['fechainicio'],
                                        fechaobtencion=f.cleaned_data['fechaobtencion'],
                                        fechaegresado=f.cleaned_data['fechaegresado'],
                                        registro=f.cleaned_data['registro'],
                                        # areaconocimiento=f.cleaned_data['areaconocimiento'],
                                        # subareaconocimiento=f.cleaned_data['subareaconocimiento'],
                                        # subareaespecificaconocimiento=f.cleaned_data['subareaespecificaconocimiento'],
                                        pais=f.cleaned_data['pais'],
                                        provincia=f.cleaned_data['provincia'],
                                        canton=f.cleaned_data['canton'],
                                        parroquia=f.cleaned_data['parroquia'],
                                        educacionsuperior=f.cleaned_data['educacionsuperior'],
                                        institucion=f.cleaned_data['institucion'],
                                        colegio=f.cleaned_data['colegio'],
                                        anios=f.cleaned_data['anios'],
                                        semestres=f.cleaned_data['semestres'],
                                        cursando=f.cleaned_data['cursando'],
                                        aplicobeca=f.cleaned_data['aplicobeca'],
                                        tipobeca=f.cleaned_data['tipobeca'] if f.cleaned_data[
                                            'aplicobeca'] else None,
                                        financiamientobeca=f.cleaned_data['financiamientobeca'] if f.cleaned_data[
                                            'aplicobeca'] else None,
                                        valorbeca=f.cleaned_data['valorbeca'] if f.cleaned_data[
                                            'aplicobeca'] else 0)
                titulacion.save(request)
                if not titulacion.cursando:
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            newfile._name = generar_nombre("titulacion_", newfile._name)
                            titulacion.archivo = newfile
                            titulacion.save(request)
                        if DistributivoPersona.objects.filter(status=True, persona=persona):
                            lista = ['talento_humano@unemi.edu.ec', 'portizg@unemi.edu.ec']
                            asunto = "Ingresaron título académico (archivo)"
                            send_html_mail(asunto, "emails/ingreso_archivos_tthh.html",
                                           {'asunto': asunto, 'd': titulacion.persona.nombre_completo_inverso(),
                                            'fecha': datetime.now().date(), 'escenario': 'titulación - SENECYT'},
                                           lista, [], cuenta=CUENTAS_CORREOS[1][1])

                    if 'registroarchivo' in request.FILES:
                        newfile2 = request.FILES['registroarchivo']
                        if newfile2:
                            newfile2._name = generar_nombre("archivosenecyt_", newfile2._name)
                            titulacion.registroarchivo = newfile2
                            titulacion.save(request)
                        if DistributivoPersona.objects.filter(status=True, persona=persona):
                            lista = ['talento_humano@unemi.edu.ec', 'portizg@unemi.edu.ec']
                            asunto = "Ingresaron título académico (archivo SENESCYT)"
                            send_html_mail(asunto, "emails/ingreso_archivos_tthh.html",
                                           {'asunto': asunto, 'd': titulacion.persona.nombre_completo_inverso(),
                                            'fecha': datetime.now().date(),
                                            'escenario': 'titulación - título academico'}, lista, [],
                                           cuenta=CUENTAS_CORREOS[1][1])
                log(u'Adiciono titulacion: %s' % persona, request, "add")
                return JsonResponse({'result': False, 'mensaje': 'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos {ex}'})

        elif action == 'edittitulacion':
            try:
                persona = request.session['persona']
                f = TitulacionPersonaForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extencion = arch._name.split('.')
                    exte = extencion[1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                    if not exte == 'pdf' and not exte == 'png' and not exte == 'jpg' and not exte == 'jpeg' and not exte == 'jpg':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf, jpg, jpeg, png"})

                if 'registroarchivo' in request.FILES:
                    registroarchivo = request.FILES['registroarchivo']
                    extencion1 = registroarchivo._name.split('.')
                    exte1 = extencion1[1]
                    if registroarchivo.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                    if not exte1 == 'pdf' and not exte1 == 'png' and not exte1 == 'jpg' and not exte1 == 'jpeg' and not exte1 == 'jpg':
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Archivo SENESCYT solo en formato .pdf, jpg, jpeg, png"})
                if not f.is_valid():
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
                titulacion = Titulacion.objects.get(pk=encrypt_id(request.POST['id']))
                titulacion.areatitulo = f.cleaned_data['areatitulo']
                titulacion.fechainicio = f.cleaned_data['fechainicio']
                titulacion.fechaobtencion = f.cleaned_data['fechaobtencion']
                titulacion.fechaegresado = f.cleaned_data['fechaegresado']
                # titulacion.areaconocimiento = f.cleaned_data['areaconocimiento']
                # titulacion.subareaconocimiento = f.cleaned_data['subareaconocimiento']
                # titulacion.subareaespecificaconocimiento = f.cleaned_data['subareaespecificaconocimiento']
                titulacion.pais = f.cleaned_data['pais']
                titulacion.provincia = f.cleaned_data['provincia']
                titulacion.canton = f.cleaned_data['canton']
                titulacion.parroquia = f.cleaned_data['parroquia']
                titulacion.colegio = f.cleaned_data['colegio']
                titulacion.anios = f.cleaned_data['anios']
                titulacion.semestres = f.cleaned_data['semestres']
                titulacion.aplicobeca = f.cleaned_data['aplicobeca']
                titulacion.tipobeca = f.cleaned_data['tipobeca'] if f.cleaned_data['aplicobeca'] else None
                titulacion.financiamientobeca = f.cleaned_data['financiamientobeca'] if f.cleaned_data[
                    'aplicobeca'] else None
                titulacion.valorbeca = f.cleaned_data['valorbeca'] if f.cleaned_data['aplicobeca'] else 0
                if not titulacion.verificadosenescyt:
                    titulacion.titulo = f.cleaned_data['titulo']
                    titulacion.educacionsuperior = f.cleaned_data['educacionsuperior']
                    titulacion.institucion = f.cleaned_data['institucion']
                    titulacion.registro = f.cleaned_data['registro']
                    titulacion.cursando = f.cleaned_data['cursando']
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("titulacion_", newfile._name)
                    titulacion.archivo = newfile
                if 'registroarchivo' in request.FILES:
                    newfile2 = request.FILES['registroarchivo']
                    if newfile2:
                        newfile2._name = generar_nombre("archivosenecyt_", newfile2._name)
                        titulacion.registroarchivo = newfile2
                titulacion.save(request)
                request.session['instruccion'] = 1
                if Graduado.objects.filter(status=True, inscripcion__persona__id=persona.id).exists():
                    datos = Persona.objects.get(status=True, id=persona.id)
                    if 'personales' in request.session and 'nacimiento' in request.session and 'domicilio' in request.session and 'etnia' in request.session and 'instruccion' in request.session and datos.datosactualizados == 0:
                        if request.session['personales'] == 1 and request.session['nacimiento'] == 1 and \
                                request.session['domicilio'] == 1 and request.session['etnia'] == 1 and \
                                request.session['instruccion'] == 1 and datos.datosactualizados == 0:
                            datos.datosactualizados = 1
                            datos.save(request)
                log(u'Modifico titulacion: %s' % persona, request, "edit")
                return JsonResponse({'result': False, 'mensaje': 'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos {ex}'})

        elif action == 'deltitulacion':
            try:
                persona = request.session['persona']
                titulacion = Titulacion.objects.get(pk=encrypt_id(request.POST['id']))
                if titulacion.verificado:
                    return JsonResponse({'result': 'bad', 'mensaje': u'No puede eliminar el titulo.'})
                log(u'Elimino titulacion: %s' % titulacion, request, "del")
                titulacion.status = False
                titulacion.save()
                res_js = {'result': True}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'result': False, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'tituloprincipal':
            try:
                titulacion = Titulacion.objects.get(pk=encrypt_id(request.POST['id']))
                val = eval(request.POST['val'].capitalize())
                if val:
                    # if not titulacion.verificado:
                    #     return JsonResponse({'result': 'bad', 'mensaje': u'No se ha verificado su titulo'})
                    titulacion.persona.titulacion_set.update(principal=False)
                    titulacion.principal = val
                else:
                    titulacion.principal = val
                titulacion.save(request)
                log(u"Selecciono titulo principal: %s" % titulacion, request, "edit")
                return JsonResponse({'result': True, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': False, 'mensaje': f'{ex}'})

        elif action == 'addprimaria':
            try:
                f = PersonaPrimariaForm(request.POST)
                if not f.is_valid():
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
                primaria = PersonaPrimaria(persona=persona,
                                           escuela=f.cleaned_data['escuela'],
                                           inicio=f.cleaned_data['inicio'],
                                           fin=f.cleaned_data['fin'],
                                           cursando=f.cleaned_data['cursando'],
                                           anios=f.cleaned_data['anios'])
                primaria.save(request)
                log(u'Adiciono primaria: %s' % persona, request, "add")
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos {ex}'})

        elif action == 'editprimaria':
            try:
                primaria = PersonaPrimaria.objects.get(id=encrypt_id(request.POST['id']))
                f = PersonaPrimariaForm(request.POST, instancia=primaria)
                if not f.is_valid():
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
                primaria.escuela = f.cleaned_data['escuela']
                primaria.inicio = f.cleaned_data['inicio']
                primaria.fin = f.cleaned_data['fin']
                primaria.cursando = f.cleaned_data['cursando']
                primaria.anios = f.cleaned_data['anios']
                primaria.save(request)
                log(u'Edito primaria: %s' % persona, request, "edit")
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos {ex}'})

        elif action == 'delprimaria':
            try:
                with transaction.atomic():
                    primaria = PersonaPrimaria.objects.get(id=encrypt_id(request.POST['id']))
                    primaria.status = False
                    primaria.save(request)
                    log(u'Elimino registro de primaria : %s - %s - %s', request, "del")
                    res_json = {"result": True}
            except Exception as ex:
                res_json = {'result': False, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        # MIS INSCRICIONES
        elif action == 'anularinscripcion':
            try:
                with transaction.atomic():
                    instancia = ReservacionPersonaPoli.objects.get(id=encrypt_id(request.POST['id']))
                    instancia.estado = 3
                    instancia.save(request)
                    log(f'Anulo inscripción a actividad : {instancia}', request, "edit")
                    res_json = {"result": True}
            except Exception as ex:
                res_json = {'result': False, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            # GESTIONAR PERFIL
            if action == 'editfoto':
                try:
                    template = get_template("core/modal/editfoto.html")
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, })
                    messages.error(request, str(ex))

            elif action == 'editdatospersonales':
                try:
                    persona = Persona.objects.get(id=persona.id)
                    perfil = persona.mi_perfil()
                    form = DatosPersonalesForm(initial={'nombres': persona.nombres,
                                                        'apellido1': persona.apellido1,
                                                        'apellido2': persona.apellido2,
                                                        'cedula': persona.cedula,
                                                        'pasaporte': persona.pasaporte,
                                                        'extension': persona.telefonoextension,
                                                        'sexo': persona.sexo,
                                                        'lgtbi': persona.lgtbi,
                                                        'anioresidencia': persona.anioresidencia,
                                                        'nacimiento': persona.nacimiento,
                                                        'email': persona.email,
                                                        'estadocivil': persona.estado_civil(),
                                                        'libretamilitar': persona.libretamilitar,
                                                        'eszurdo': persona.eszurdo,
                                                        'estadogestacion': persona.estadogestacion,
                                                        'archivocedula': persona.documentos_personales().cedula if persona.documentos_personales() else '',
                                                        'papeleta': persona.archivo_papeleta() if persona.documentos_personales() else '',
                                                        'archivolibretamilitar': persona.archivo_libreta_militar() if persona.documentos_personales() else '',
                                                        'raza': perfil.raza,
                                                        'nacionalidadindigena': perfil.nacionalidadindigena,
                                                        'archivoraza': perfil.archivoraza
                                                        })
                    form.editar()
                    if esestudiante:
                        form.es_estudiante()
                    data['form'] = form
                    data['persona'] = persona
                    banderalibreta = 0
                    banderapapeleta = 0
                    banderacedula = 0
                    documentos = PersonaDocumentoPersonal.objects.filter(persona=persona)
                    if documentos:
                        if documentos[0].libretamilitar:
                            banderalibreta = 1
                        if documentos[0].papeleta:
                            banderapapeleta = 1
                        if documentos[0].cedula:
                            banderacedula = 1
                    data['banderacedula'] = banderacedula
                    data['banderalibreta'] = banderalibreta
                    data['banderapapeleta'] = banderapapeleta
                    data['switchery'] = True
                    template = get_template('th_hojavida/informacionpersonal/modal/formdatospersonales.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'editdatosnacimiento':
                try:
                    data['nacionalidad'] = persona.paisnacimiento.nacionalidad
                    form = DatosNacimientoForm(initial={'paisnacimiento': persona.paisnacimiento,
                                                        'provincianacimiento': persona.provincianacimiento,
                                                        'cantonnacimiento': persona.cantonnacimiento,
                                                        'parroquianacimiento': persona.parroquianacimiento,
                                                        'paisnacionalidad': persona.paisnacionalidad
                                                        })
                    form.editar(persona)
                    data['form'] = form
                    template = get_template('th_hojavida/informacionpersonal/modal/formnacimiento.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'editdatosdomicilio':
                try:
                    persona = Persona.objects.get(id=persona.id)
                    documento_p = persona.documentos_personales()
                    form = DatosDomicilioForm(initial={'pais': persona.pais,
                                                       'provincia': persona.provincia,
                                                       'canton': persona.canton,
                                                       'ciudadela': persona.ciudadela,
                                                       'parroquia': persona.parroquia,
                                                       'direccion': persona.direccion,
                                                       'direccion2': persona.direccion2,
                                                       'sector': persona.sector,
                                                       'num_direccion': persona.num_direccion,
                                                       'referencia': persona.referencia,
                                                       'telefono': persona.telefono,
                                                       'telefono_conv': persona.telefono_conv,
                                                       'tipocelular': persona.tipocelular,
                                                       'archivoplanillaluz': persona.archivoplanillaluz,
                                                       'archivocroquis': persona.archivocroquis,
                                                       'serviciosbasico': documento_p.serviciosbasico if documento_p else None,
                                                       'zona': persona.zona})
                    form.editar(persona)
                    if not documento_p:
                        form.fields['serviciosbasico'].widget = forms.HiddenInput()
                    data['form'] = form
                    template = get_template('th_hojavida/informacionpersonal/modal/formdomicilio.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            # FAMILIARES
            elif action == 'datosfamiliares':
                try:
                    data['title'] = u'Datos familiares'
                    url_vars = f'&action={action}'
                    familiares = persona.familiares().order_by('-id')
                    paging = MiPaginador(familiares, 20)
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
                    data['url_vars'] = url_vars
                    data['listado'] = page.object_list
                    data['viewactivo'] = action
                    return render(request, "unemideporte/gestionarperfil/familiares.html", data)
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'addfamiliar':
                try:
                    form = FamiliarForm()
                    visible_fields = form.visible_fields()
                    total_fields = len(visible_fields)
                    lista = [(1, 'Informació Básica', visible_fields[:19]),
                             (2, 'Información Laboral', visible_fields[19:27]),
                             (3, 'Discapacidad', visible_fields[27:total_fields])
                             ]
                    data['form'] = lista
                    data['switchery'] = True
                    template = get_template('th_hojavida/informacionpersonal/modal/formfamiliar.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'editfamiliar':
                try:
                    data['title'] = u'Editar familiar'
                    data['id'] = id = encrypt_id(request.GET['id'])
                    data['familiar'] = familiar = PersonaDatosFamiliares.objects.get(pk=id)
                    apellido1, apellido2, nombres, editdiscapacidad, sexo = '', '', familiar.nombre, False, None
                    if familiar.personafamiliar:
                        apellido1 = familiar.personafamiliar.apellido1
                        apellido2 = familiar.personafamiliar.apellido2
                        nombres = familiar.personafamiliar.nombres
                        sexo = familiar.personafamiliar.sexo
                        perfil_f = familiar.personafamiliar.perfilinscripcion_set.filter(status=True).first()
                        estado = True if perfil_f and perfil_f.estadoarchivodiscapacidad == 2 else False
                        if len(familiar.personafamiliar.mis_perfilesusuarios()) == 1 and familiar.personafamiliar.tiene_usuario_externo():
                            editdiscapacidad = True
                        elif not estado:
                            editdiscapacidad = True
                    else:
                        editdiscapacidad = True
                    banderacedula = 0
                    if familiar.cedulaidentidad:
                        banderacedula = 1
                    data['banderacedula'] = banderacedula
                    data['edit_d'] = editdiscapacidad
                    form = FamiliarForm(initial={'identificacion': familiar.identificacion,
                                                 'parentesco': familiar.parentesco,
                                                 'nombre': nombres,
                                                 'apellido1': apellido1,
                                                 'apellido2': apellido2,
                                                 'sexo': sexo,
                                                 'nacimiento': familiar.nacimiento,
                                                 'fallecido': familiar.fallecido,
                                                 'tienediscapacidad': familiar.tienediscapacidad,
                                                 'telefono': familiar.telefono,
                                                 'niveltitulacion': familiar.niveltitulacion,
                                                 'ingresomensual': familiar.ingresomensual,
                                                 'formatrabajo': familiar.formatrabajo,
                                                 'telefono_conv': familiar.telefono_conv,
                                                 'trabajo': familiar.trabajo,
                                                 'convive': familiar.convive,
                                                 'sustentohogar': familiar.sustentohogar,
                                                 'essustituto': familiar.essustituto,
                                                 'autorizadoministerio': familiar.autorizadoministerio,
                                                 'tipodiscapacidad': familiar.tipodiscapacidad,
                                                 'porcientodiscapacidad': familiar.porcientodiscapacidad,
                                                 'carnetdiscapacidad': familiar.carnetdiscapacidad,
                                                 'institucionvalida': familiar.institucionvalida,
                                                 'tipoinstitucionlaboral': familiar.tipoinstitucionlaboral,
                                                 'tienenegocio': familiar.tienenegocio,
                                                 'esservidorpublico': familiar.esservidorpublico,
                                                 'bajocustodia': familiar.bajocustodia,
                                                 'tienenegocio': familiar.tienenegocio,
                                                 'cedulaidentidad': familiar.cedulaidentidad,
                                                 'ceduladiscapacidad': familiar.ceduladiscapacidad,
                                                 'archivoautorizado': familiar.archivoautorizado,
                                                 'cartaconsentimiento': familiar.cartaconsentimiento,
                                                 'archivocustodia': familiar.archivocustodia,
                                                 'centrocuidado': familiar.centrocuidado,
                                                 'centrocuidadodesc': familiar.centrocuidadodesc,
                                                 'negocio': familiar.negocio, })
                    visible_fields = form.visible_fields()
                    total_fields = len(visible_fields)
                    lista = [(1, 'Informació Básica', visible_fields[:19]),
                             (2, 'Información Laboral', visible_fields[19:27]),
                             (3, 'Discapacidad', visible_fields[27:total_fields])
                             ]
                    form.edit()
                    data['form'] = lista
                    data['switchery'] = True
                    template = get_template('th_hojavida/informacionpersonal/modal/formfamiliar.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            # DATOS MEDICOS
            elif action == 'datosmedicos':
                try:
                    data['title'] = u'Datos médicos'
                    data['subtitle'] = u'Información registrada'
                    data['url_vars'] = f'&action={action}'
                    data['persona'] = persona = Persona.objects.get(id=persona.id)
                    data['perfil'] = persona.mi_perfil()
                    data['datosextension'] = datosextension = persona.datos_extension()
                    data['examenfisico'] = examenfisico = persona.datos_examen_fisico()
                    data['viewactivo'] = action
                    return render(request, "unemideporte/gestionarperfil/datosmedicos.html", data)
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'editdatosmedicos':
                try:
                    datosextension = persona.datos_extension()
                    examenfisico = persona.datos_examen_fisico()
                    form = DatosMedicosForm(initial={
                        'carnetiess': datosextension.carnetiess,
                        'sangre': persona.sangre,
                        'archivotiposangre': persona.archivo_tiposangre,
                        'peso': examenfisico.peso,
                        'talla': examenfisico.talla
                    })
                    data['form'] = form
                    template = get_template('th_hojavida/informacionmedica/modal/formbasico.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'editcontactoemergencia':
                try:
                    datosextension = persona.datos_extension()
                    form = ContactoEmergenciaForm(initial={
                        'contactoemergencia': datosextension.contactoemergencia,
                        'parentescoemergencia': datosextension.parentescoemergencia,
                        'telefonoemergencia': datosextension.telefonoemergencia,
                        'telefonoconvemergencia': datosextension.telefonoconvemergencia,
                        'correoemergencia': datosextension.correoemergencia
                    })
                    data['form'] = form
                    template = get_template('th_hojavida/informacionmedica/modal/formbasico.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            # ENFERMEDADES
            elif action == 'enfermedades':
                try:
                    data['title'] = u'Enfermedades'
                    url_vars = f'&action={action}'
                    artistas = persona.mis_enfermedades().order_by('-id')
                    paging = MiPaginador(artistas, 20)
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
                    data['url_vars'] = url_vars
                    data['listado'] = page.object_list
                    data['viewactivo'] = action
                    return render(request, "unemideporte/gestionarperfil/enfermedades.html", data)
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'addenfermedad':
                try:
                    form = PersonaEnfermedadForm()
                    data['form'] = form
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editenfermedad':
                try:
                    data['enfermedad'] = enfermedad = PersonaEnfermedad.objects.get(id=int(encrypt(request.GET['id'])))
                    data['id'] = enfermedad.id
                    form = PersonaEnfermedadForm(initial=model_to_dict(enfermedad), instancia=enfermedad)
                    data['form'] = form
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            # FORMACIÓN ACADEMICA

            elif action == 'estudios':
                try:
                    data['title'] = u'Estudios'
                    url_vars = f'&action={action}'
                    titulaciones = persona.mis_titulaciones().order_by('-titulo__niveltitulacion')
                    paging = MiPaginador(titulaciones, 20)
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
                    data['url_vars'] = url_vars
                    data['listado'] = page.object_list
                    data['listado1'] = persona.personaprimaria_set.filter(status=True)
                    data['viewactivo'] = action
                    return render(request, "unemideporte/gestionarperfil/formacionacademica.html", data)
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'addprimaria':
                try:
                    form = PersonaPrimariaForm()
                    data['form'] = form
                    data['switchery'] = True
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'editprimaria':
                try:
                    data['id'] = id = encrypt_id(request.GET['id'])
                    instancia = PersonaPrimaria.objects.get(id=id)
                    form = PersonaPrimariaForm(instancia=instancia, initial=model_to_dict(instancia))
                    data['form'] = form
                    data['switchery'] = True
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'addtitulacion':
                try:
                    data['title'] = u'Adicionar primaria'
                    form = TitulacionPersonaForm()
                    form.adicionar()
                    visible_fields = form.visible_fields()
                    total_fields = len(visible_fields)
                    lista = [(1, 'Información de título', visible_fields[:14]),
                             (2, 'Ubicación de institución', visible_fields[14:18]),
                             (3, 'Beca', visible_fields[18:total_fields])
                             ]
                    data['form'] = lista
                    data['switchery'] = True
                    template = get_template('th_hojavida/informacionacademica/modal/formtitulacion.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'edittitulacion':
                try:
                    data['titulacion'] = titulacion = Titulacion.objects.get(pk=encrypt_id(request.GET['id']))
                    # campotitulo, campoamplio, campoespecifico, campodetallado = None, None, None, None
                    # if CamposTitulosPostulacion.objects.filter(status=True, titulo=titulacion.titulo).exists():
                    #     campotitulo = CamposTitulosPostulacion.objects.filter(status=True,
                    #                                                           titulo=titulacion.titulo).first()
                    #     campoamplio = AreaConocimientoTitulacion.objects.filter(status=True,
                    #                                                             id__in=campotitulo.campoamplio.all().values_list(
                    #                                                                 'id', flat=True))
                    #     campoespecifico = SubAreaConocimientoTitulacion.objects.filter(status=True,
                    #                                                                    id__in=campotitulo.campoespecifico.all().values_list(
                    #                                                                        'id', flat=True))
                    #     campodetallado = SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True,
                    #                                                                             id__in=campotitulo.campodetallado.all().values_list(
                    #                                                                                 'id', flat=True))
                    form = TitulacionPersonaForm(initial={'titulo': titulacion.titulo,
                                                          'areatitulo': titulacion.areatitulo,
                                                          'fechainicio': titulacion.fechainicio,
                                                          'educacionsuperior': titulacion.educacionsuperior,
                                                          'institucion': titulacion.institucion,
                                                          'colegio': titulacion.colegio,
                                                          'cursando': titulacion.cursando,
                                                          'fechaobtencion': titulacion.fechaobtencion if not titulacion.cursando else datetime.now().date(),
                                                          'fechaegresado': titulacion.fechaegresado if not titulacion.cursando else datetime.now().date(),
                                                          'registro': titulacion.registro,
                                                          # 'areaconocimiento': titulacion.areaconocimiento,
                                                          # 'subareaconocimiento': titulacion.subareaconocimiento,
                                                          # 'subareaespecificaconocimiento': titulacion.subareaespecificaconocimiento,
                                                          'pais': titulacion.pais,
                                                          'provincia': titulacion.provincia,
                                                          'canton': titulacion.canton,
                                                          'parroquia': titulacion.parroquia,
                                                          # 'campoamplio': campoamplio,
                                                          # 'campoespecifico': campoespecifico,
                                                          # 'campodetallado': campodetallado,
                                                          'anios': titulacion.anios,
                                                          'semestres': titulacion.semestres,
                                                          'aplicobeca': titulacion.aplicobeca,
                                                          'tipobeca': titulacion.tipobeca,
                                                          'archivo': titulacion.archivo,
                                                          'registroarchivo': titulacion.registroarchivo,
                                                          'financiamientobeca': titulacion.financiamientobeca,
                                                          'valorbeca': titulacion.valorbeca})
                    form.editar(titulacion)
                    visible_fields = form.visible_fields()
                    total_fields = len(visible_fields)
                    lista = [(1, 'Información de título', visible_fields[:14]),
                             (2, 'Ubicación de institución', visible_fields[14:18]),
                             (3, 'Beca', visible_fields[18:total_fields])
                             ]
                    data['form'] = lista
                    data['id'] = titulacion.id
                    data['switchery'] = True
                    template = get_template('th_hojavida/informacionacademica/modal/formtitulacion.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'buscartitulo':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    filtro = Q(status=True, nombre__icontains=q)
                    titulos = Titulo.objects.filter(filtro).distinct()[:15]
                    resp = [{'id': t.pk, 'text': f"{t.nombre}"} for t in titulos]
                    return JsonResponse(resp, safe=False)
                except Exception as ex:
                    pass

            elif action == 'detalletitulo':
                try:
                    data['titulacion'] = titulacion = Titulacion.objects.get(pk=encrypt_id(request.GET['args']))
                    dettitu = titulacion.detalletitulacionbachiller_set.filter(status=True)
                    data['detalletitulacionbachiller'] = dettitu.last()
                    if titulacion.usuario_creacion:
                        data['personacreacion'] = Persona.objects.get(
                            usuario=titulacion.usuario_creacion) if titulacion.usuario_creacion.id > 1 else ""
                    template = get_template("th_hojavida/detalletitulo.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            # INSCRIPCIONES O RESERVAS
            elif action == 'misinscripciones':
                try:
                    data['title'] = u'Mis Inscripciones'
                    url_vars = f'&action={action}'
                    eInscripciones = ReservacionPersonaPoli.objects.filter(actividad__tipoactividad__in=[2,3], persona=persona, status=True)
                    paging = MiPaginador(eInscripciones, 20)
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
                    data['url_vars'] = url_vars
                    data['listado'] = page.object_list
                    data['viewactivo'] = action
                    return render(request, "unemideporte/gestionarperfil/mis_inscripciones.html", data)
                except Exception as ex:
                    messages.error(request, f'{ex}')

            #         # MIS CITAS
            # elif action == 'misinscripciones':
            #     try:
            #         data['title'] = u'Mis Citas'
            #         url_vars = f'&action={action}'
            #         eInscripciones = ReservacionPersonaPoli.objects.filter(actividad__tipoactividad__in=[2, 3],
            #                                                                persona=persona, status=True)
            #         paging = MiPaginador(eInscripciones, 20)
            #         p = 1
            #         try:
            #             paginasesion = 1
            #             if 'paginador' in request.session:
            #                 paginasesion = int(request.session['paginador'])
            #             if 'page' in request.GET:
            #                 p = int(request.GET['page'])
            #             else:
            #                 p = paginasesion
            #             try:
            #                 page = paging.page(p)
            #             except:
            #                 p = 1
            #             page = paging.page(p)
            #         except:
            #             page = paging.page(p)
            #         request.session['paginador'] = p
            #         data['paging'] = paging
            #         data['rangospaging'] = paging.rangos_paginado(p)
            #         data['page'] = page
            #         data['url_vars'] = url_vars
            #         data['listado'] = page.object_list
            #         data['viewactivo'] = action
            #         return render(request, "serviciosvinculacion/gestionarperfilvin/miscitas.html", data)
            #     except Exception as ex:
            #         messages.error(request, f'{ex}')

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['viewactivo'] ='gestionarperfil'
                data['title'] = u'Gestionar mi perfil'
                data['subtitle'] = u'Tiene control total para administrar la configuración de su propia cuenta.'
                return render(request, "unemideporte/gestionarperfil/gestionarperfil.html", data)
            except Exception as ex:
                messages.error(request, str(ex))
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                pass
