# -*- coding: UTF-8 -*-
import os
import random

import xlwt
from django.db.models import Avg
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsave
import pyqrcode
import code128
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from xlwt import *
from django.forms import model_to_dict
from decorators import secure_module
from sagest.forms import DatosPersonalesForm, DatosNacimientoForm, DatosDomicilioForm, DatosMedicosForm, \
    ContactoEmergenciaForm, EtniaForm, DiscapacidadForm, FamiliarForm, DeclaracionBienForm, CuentaBancariaPersonaForm, \
    TitulacionPersonaForm, ArchivoTitulacionForm, CapacitacionPersonaForm, ArchivoCapacitacionForm, \
    ExperienciaLaboralForm, DatosPersonaInstitucionForm, ArchivoIdiomaForm, ArchivoExperienciaForm, \
    PersonaContratosForm, PersonaAccionesForm, CertificadoPersonaForm
from sagest.models import ExperienciaLaboral, RolPago, PersonaContratos, PersonaAcciones, SolicitudPublicacion, \
    ActivoFijo, OtroMerito, DistributivoPersona, RegimenLaboral
from settings import PROFESORES_GROUP_ID, EMPLEADORES_GRUPO_ID, ALUMNOS_GROUP_ID, SITE_STORAGE, PUESTO_ACTIVO_ID
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import IdiomaDominaForm, PeriodoSabaticoForm, EvidenciaForm
from sga.funciones import MiPaginador, log, generar_nombre, variable_valor, puede_realizar_accion
from sga.models import PersonaDatosFamiliares, DeclaracionBienes, CuentaBancariaPersona, Titulacion, \
    Capacitacion, IdiomaDomina, Persona, ArticuloInvestigacion, PonenciasInvestigacion, LibroInvestigacion, Evidencia, \
    NivelTitulacion, ParticipantesMatrices, RespuestaEvaluacionAcreditacion, ResumenFinalProcesoEvaluacionIntegral, \
    MigracionEvaluacionDocente, ResumenParcialEvaluacionIntegral, null_to_numeric, ResumenFinalEvaluacionAcreditacion, \
    CapituloLibroInvestigacion, ResponsableEvaluacion, CertificacionPersona
from datetime import datetime, timedelta




@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'detalledato':
            try:
                data = {}
                personaladministrativo = Persona.objects.filter(cedula__in=['0909979015',
                                                                            '0910438985',
                                                                            '0912531829',
                                                                            '0909100307',
                                                                            '0912312402',
                                                                            '0911444032',
                                                                            '1200934105',
                                                                            '0914202627',
                                                                            '0919995779',
                                                                            '0922980883',
                                                                            '1201599402',
                                                                            '0914386040',
                                                                            '1714770623',
                                                                            '0912851698',
                                                                            '0921284501',
                                                                            '0919872010',
                                                                            '0915684112',
                                                                            '0918223876',
                                                                            '0913962833',
                                                                            '0906276217',
                                                                            '0907194195',
                                                                            '1707198808',
                                                                            '0920733318',
                                                                            '0917039000',
                                                                            '1202374789',
                                                                            '1203525132',
                                                                            '0924887714',
                                                                            '0701612251',
                                                                            '0909408031',
                                                                            '0911447480',
                                                                            '0923603690',
                                                                            '0912554151',
                                                                            '0919875542',
                                                                            '0920198439',
                                                                            '0921691010',
                                                                            '0917885063',
                                                                            '0915184501',
                                                                            '1202292080',
                                                                            '0917923021',
                                                                            '0927425066',
                                                                            '0917219313',
                                                                            '0916305790',
                                                                            '0927990937',
                                                                            '0104392014',
                                                                            '0927981308',
                                                                            '0925229635',
                                                                            '0922333844',
                                                                            '1202043996',
                                                                            '0917118374',
                                                                            '0918306952',
                                                                            '0914201496',
                                                                            '0915580443',
                                                                            '0919142778',
                                                                            '0921230439',
                                                                            '1201339692',
                                                                            '0912011178',
                                                                            '0922576376',
                                                                            '1203091358',
                                                                            '0703680207',
                                                                            '1708436702',
                                                                            '1203351745',
                                                                            '0914607007',
                                                                            '0908258916',
                                                                            '0909549669',
                                                                            '0954221842',
                                                                            '0919509653',
                                                                            '0918475633']).distinct()
                data['listaadministrativos'] = personaladministrativo.filter(Q(titulacion__verificado=False, titulacion__cursando=False) |
                                                                             Q(capacitacion__verificado=False) |
                                                                             Q(declaracionbienes__verificado=False) |
                                                                             Q(cuentabancariapersona__verificado=False) |
                                                                             Q(experiencialaboral__verificado=False)).distinct()
                template = get_template("th_personaltrabajador/detalle.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'datospersonales':
            try:
                f = DatosPersonalesForm(request.POST)
                if f.is_valid():
                    personaadmin = Persona.objects.get(pk=int(request.POST['id']))
                    personaadmin.nombres = f.cleaned_data['nombres']
                    personaadmin.apellido1 = f.cleaned_data['apellido1']
                    personaadmin.apellido2 = f.cleaned_data['apellido2']
                    personaadmin.anioresidencia = f.cleaned_data['anioresidencia']
                    personaadmin.nacimiento = f.cleaned_data['nacimiento']
                    personaadmin.sexo = f.cleaned_data['sexo']
                    personaadmin.nacionalidad = f.cleaned_data['nacionalidad']
                    personaadmin.email = f.cleaned_data['email']
                    personaadmin.libretamilitar = f.cleaned_data['libretamilitar']
                    personaadmin.save(request)
                    personaextension = personaadmin.datos_extension()
                    personaextension.estadocivil = f.cleaned_data['estadocivil']
                    personaextension.save(request)
                    log(u'Modifico datos personales: %s' % personaadmin, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'datosnacimiento':
            try:
                f = DatosNacimientoForm(request.POST)
                if f.is_valid():
                    personaadmin = Persona.objects.get(pk=int(request.POST['id']))
                    personaadmin.paisnacimiento = f.cleaned_data['paisnacimiento']
                    personaadmin.provincianacimiento = f.cleaned_data['provincianacimiento']
                    personaadmin.cantonnacimiento = f.cleaned_data['cantonnacimiento']
                    personaadmin.parroquianacimiento = f.cleaned_data['parroquianacimiento']
                    personaadmin.save(request)
                    log(u'Modifico datos de nacimiento: %s' % personaadmin, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'datosdomicilio':
            try:
                f = DatosDomicilioForm(request.POST)
                if f.is_valid():
                    personaadmin = Persona.objects.get(pk=int(request.POST['id']))
                    personaadmin.pais = f.cleaned_data['pais']
                    personaadmin.provincia = f.cleaned_data['provincia']
                    personaadmin.canton = f.cleaned_data['canton']
                    personaadmin.parroquia = f.cleaned_data['parroquia']
                    personaadmin.direccion = f.cleaned_data['direccion']
                    personaadmin.direccion2 = f.cleaned_data['direccion2']
                    personaadmin.num_direccion = f.cleaned_data['num_direccion']
                    personaadmin.telefono = f.cleaned_data['telefono']
                    personaadmin.telefono_conv = f.cleaned_data['telefono_conv']
                    personaadmin.referencia = f.cleaned_data['referencia']
                    personaadmin.save(request)
                    log(u'Modifico datos de domicilio: %s' % personaadmin, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'consul_contrato':
            try:
                personacontrato = PersonaContratos.objects.get(pk=request.POST['idcontra'], status=True)
                numero = personacontrato.numerodocumento
                relacionada = personacontrato.contratacionrelacionada
                return JsonResponse({"result": "ok","numero": numero,"relacionada": relacionada })
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'consul_accion':
            try:
                personaaccion = PersonaAcciones.objects.get(pk=request.POST['idaccion'], status=True)
                numero = personaaccion.numerodocumento
                tipo = personaaccion.tipo.nombre
                return JsonResponse({"result": "ok","numero": numero,"tipo": tipo })
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'datosmedicos':
            try:
                f = DatosMedicosForm(request.POST)
                if f.is_valid():
                    personaadmin = Persona.objects.get(pk=int(request.POST['id']))
                    datosextension = personaadmin.datos_extension()
                    examenfisico = personaadmin.datos_examen_fisico()
                    datosextension.carnetiess = f.cleaned_data['carnetiess']
                    datosextension.save(request)
                    examenfisico.peso = f.cleaned_data['peso']
                    examenfisico.talla = f.cleaned_data['talla']
                    examenfisico.save(request)
                    personaadmin.sangre = f.cleaned_data['sangre']
                    personaadmin.save(request)
                    log(u'Modifico datos de medicos basicos: %s' % personaadmin, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'contactoemergencia':
            try:
                f = ContactoEmergenciaForm(request.POST)
                if f.is_valid():
                    personaadmin = Persona.objects.get(pk=int(request.POST['id']))
                    datosextension = personaadmin.datos_extension()
                    datosextension.contactoemergencia = f.cleaned_data['contactoemergencia']
                    datosextension.telefonoemergencia = f.cleaned_data['telefonoemergencia']
                    datosextension.parentescoemergencia = f.cleaned_data['parentescoemergencia']
                    datosextension.save(request)
                    log(u'Modifico datos de contacto de emergencia: %s' % personaadmin, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'detalletitulo':
            try:
                data['titulacion'] = titulacion = Titulacion.objects.get(pk=int(request.POST['id']))
                if titulacion.usuario_creacion:
                    data['personacreacion'] = Persona.objects.get(usuario=titulacion.usuario_creacion) if titulacion.usuario_creacion.id > 1 else ""
                template = get_template("th_personal/detalletitulo.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


        if action == 'detallecapacitacion':
            try:
                data['capacitacion'] = capacitacion = Capacitacion.objects.get(pk=int(request.POST['id']))
                if capacitacion.usuario_creacion:
                    data['personacreacion'] = Persona.objects.get(usuario=capacitacion.usuario_creacion) if capacitacion.usuario_creacion.id > 1 else ""
                template = get_template("th_personal/detallecapacitacion.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


        if action == 'detallerol':
            try:
                data['detallerol'] = registro = RolPago.objects.get(pk=int(request.POST['id']), status=True)
                data['detalleinformativo'] = registro.detallerolinformativo()
                data['detalleingreso'] = registro.detallerolingreso()
                data['detalleegreso'] = registro.detallerolegreso()
                template = get_template("th_personal/detallerol.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'detallearticulo':
            try:
                data['articulo'] = articulos = ArticuloInvestigacion.objects.get(pk=request.POST['id'])
                data['evidencias'] = Evidencia.objects.filter(status=True, matrizevidencia_id=3)
                data['formevidencias'] = EvidenciaForm()
                # data['evidenciasarticulo'] = evidencias = DetalleEvidencias.objects.filter(articulo=articulos)
                template = get_template("th_hojavida/detallearticulo.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'detalleponencia':
            try:
                data['ponencias'] = ponencias = PonenciasInvestigacion.objects.get(pk=request.POST['id'])

                data['evidencias'] = Evidencia.objects.filter(status=True, matrizevidencia_id=4)
                data['formevidencias'] = EvidenciaForm()
                template = get_template("th_hojavida/detalleponencia.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'detalleexplicacion':
            try:
                if 'id' in request.POST:
                    data['accion'] = PersonaAcciones.objects.get(pk=int(request.POST['id']))
                    template = get_template("th_personal/detalleaccionpersonalexplicacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'detallecontrato':
            try:
                if 'id' in request.POST:
                    data['contrato'] = PersonaContratos.objects.get(pk=int(request.POST['id']))
                    template = get_template("th_personal/detallecontrato.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


        elif action == 'detallecertificacion':
            try:
                data['certificacion'] = certificacion = CertificacionPersona.objects.get(pk=int(request.POST['id']))
                if certificacion.usuario_creacion:
                    data['personacreacion'] = Persona.objects.get(usuario=certificacion.usuario_creacion) if certificacion.usuario_creacion.id > 1 else ""
                template = get_template("th_hojavida/detallecertificacion.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'datospersonales':
                try:
                    data['title'] = u'Datos personales'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['id']))
                    form = DatosPersonalesForm(initial={'nombres': personaadmin.nombres,
                                                        'apellido1': personaadmin.apellido1,
                                                        'apellido2': personaadmin.apellido2,
                                                        'cedula': personaadmin.cedula,
                                                        'pasaporte': personaadmin.pasaporte,
                                                        'sexo': personaadmin.sexo,
                                                        'anioresidencia': personaadmin.anioresidencia,
                                                        'nacimiento': personaadmin.nacimiento,
                                                        'nacionalidad': personaadmin.nacionalidad,
                                                        'email': personaadmin.email,
                                                        'estadocivil': personaadmin.estado_civil(),
                                                        'libretamilitar': personaadmin.libretamilitar})
                    form.editar(sinnombres=False)
                    data['form'] = form
                    return render(request, "th_personal/datospersonales.html", data)
                except:
                    pass

            if action == 'datosnacimiento':
                try:
                    data['title'] = u'Datos de nacimiento'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['id']))
                    form = DatosNacimientoForm(initial={'paisnacimiento': personaadmin.paisnacimiento,
                                                        'provincianacimiento': personaadmin.provincianacimiento,
                                                        'cantonnacimiento': personaadmin.cantonnacimiento,
                                                        'parroquianacimiento': personaadmin.parroquianacimiento})
                    form.editar(personaadmin)
                    data['form'] = form
                    return render(request, "th_personal/datosnacimiento.html", data)
                except Exception as ex:
                    pass

            if action == 'datosmedicos':
                try:
                    data['title'] = u'Datos medicos basicos'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['id']))
                    datosextension = personaadmin.datos_extension()
                    examenfisico = personaadmin.datos_examen_fisico()
                    form = DatosMedicosForm(initial={'carnetiess': datosextension.carnetiess,
                                                     'sangre': personaadmin.sangre,
                                                     'peso': examenfisico.peso,
                                                     'talla': examenfisico.talla})
                    data['form'] = form
                    return render(request, "th_personal/datosmedicos.html", data)
                except:
                    pass

            if action == 'datosdomicilio':
                try:
                    data['title'] = u'Datos de domicilio'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['id']))
                    form = DatosDomicilioForm(initial={'pais': personaadmin.pais,
                                                       'provincia': personaadmin.provincia,
                                                       'canton': personaadmin.canton,
                                                       'parroquia': personaadmin.parroquia,
                                                       'direccion': personaadmin.direccion,
                                                       'direccion2': personaadmin.direccion2,
                                                       'num_direccion': personaadmin.num_direccion,
                                                       'referencia': personaadmin.referencia,
                                                       'telefono': personaadmin.telefono,
                                                       'telefono_conv': personaadmin.telefono_conv})
                    form.editar(persona)
                    data['form'] = form
                    return render(request, "th_personal/datosdomicilio.html", data)
                except:
                    pass

            if action == 'contactoemergencia':
                try:
                    data['title'] = u'Contacto de emergencia'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['id']))
                    datosextension = personaadmin.datos_extension()
                    form = ContactoEmergenciaForm(initial={'contactoemergencia': datosextension.contactoemergencia,
                                                           'parentescoemergencia': datosextension.parentescoemergencia,
                                                           'telefonoemergencia': datosextension.telefonoemergencia})
                    data['form'] = form
                    return render(request, "th_personal/contactoemergencia.html", data)
                except:
                    pass

            if action == 'etnia':
                try:
                    data['title'] = u'Etnia'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['id']))
                    perfil = personaadmin.mi_perfil()
                    form = EtniaForm(initial={'raza': perfil.raza,
                                              'nacionalidadindigena': perfil.nacionalidadindigena})
                    data['form'] = form
                    return render(request, "th_personal/etnia.html", data)
                except:
                    pass

            if action == 'discapacidad':
                try:
                    data['title'] = u'Discapacidad'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['id']))
                    perfil = personaadmin.mi_perfil()
                    form = DiscapacidadForm(initial={'tienediscapacidad': perfil.tienediscapacidad,
                                                     'tipodiscapacidad': perfil.tipodiscapacidad,
                                                     'porcientodiscapacidad': perfil.porcientodiscapacidad,
                                                     'carnetdiscapacidad': perfil.carnetdiscapacidad})
                    data['form'] = form
                    return render(request, "th_personal/discapacidad.html", data)
                except:
                    pass

            if action == 'addfamiliar':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_hoja_vida')
                    data['title'] = u'Adicionar familiar'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['id']))
                    data['form'] = FamiliarForm()
                    return render(request, "th_personal/addfamiliar.html", data)
                except:
                    pass

            if action == 'editfamiliar':
                try:
                    data['title'] = u'Editar familiar'
                    puede_realizar_accion(request, 'sagest.puede_modificar_hoja_vida')
                    data['familiar'] = familiar = PersonaDatosFamiliares.objects.get(pk=int(request.GET['id']))
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['ida']))
                    data['form'] = FamiliarForm(initial={'identificacion': familiar.identificacion,
                                                         'parentesco': familiar.parentesco,
                                                         'nombre': familiar.nombre,
                                                         'nacimiento': familiar.nacimiento,
                                                         'fallecido': familiar.fallecido,
                                                         'tienediscapacidad': familiar.tienediscapacidad,
                                                         'telefono': familiar.telefono,
                                                         'telefono_conv': familiar.telefono_conv,
                                                         'niveltitulacion': familiar.niveltitulacion,
                                                         'formatrabajo': familiar.formatrabajo,
                                                         'ingresomensual': familiar.ingresomensual,
                                                         'trabajo': familiar.trabajo,
                                                         'convive': familiar.convive,
                                                         'sustentohogar': familiar.sustentohogar})
                    return render(request, 'th_personal/editfamiliar.html', data)
                except:
                    pass

            if action == 'delfamiliar':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_hoja_vida')
                    data['title'] = u'Eliminar familiar'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['ida']))
                    data['familiar'] = familiar = PersonaDatosFamiliares.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_personal/delfamiliar.html", data)
                except:
                    pass

            if action == 'adddeclaracion':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_hoja_vida')
                    data['title'] = u'Adicionar declaración'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['id']))
                    form = DeclaracionBienForm()
                    form.ocultarcampos()
                    data['form'] = form
                    return render(request, "th_personal/adddeclaracion.html", data)
                except:
                    pass

            if action == 'deldeclaracion':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_hoja_vida')
                    data['title'] = u'Eliminar declaración'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['ida']))
                    data['declaracion'] = declaracion = DeclaracionBienes.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_personal/deldeclaracion.html", data)
                except:
                    pass

            if action == 'addcuentabancaria':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_hoja_vida')
                    data['title'] = u'Adicionar cuenta bancaria'
                    data['form'] = CuentaBancariaPersonaForm()
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_personal/addcuentabancaria.html", data)
                except:
                    pass

            if action == 'editcuentabancaria':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_hoja_vida')
                    data['title'] = u'Editar cuenta bancaria'
                    data['cuentabancaria'] = cuentabancaria = CuentaBancariaPersona.objects.get(pk=int(request.GET['id']))
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['ida']))
                    data['form'] = CuentaBancariaPersonaForm(initial={'numero': cuentabancaria.numero,
                                                                      'banco': cuentabancaria.banco,
                                                                      'tipocuentabanco': cuentabancaria.tipocuentabanco})
                    return render(request, "th_personal/editcuentabancaria.html", data)
                except:
                    pass

            if action == 'delcuentabancaria':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_hoja_vida')
                    data['title'] = u'Eliminar cuenta bancaria'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['ida']))
                    data['cuentabancaria'] = cuentabancaria = CuentaBancariaPersona.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_personal/delcuentabancaria.html", data)
                except:
                    pass

            if action == 'addtitulacion':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_hoja_vida')
                    data['title'] = u'Adicionar titulación'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['id']))
                    form = TitulacionPersonaForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, "th_personal/addtitulacion.html", data)
                except:
                    pass

            if action == 'edittitulacion':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_hoja_vida')
                    data['title'] = u'Editar titulación'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['ida']))
                    data['titulacion'] = titulacion = Titulacion.objects.get(pk=int(request.GET['id']))
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
                                                          'anios': titulacion.anios,
                                                          'semestres': titulacion.semestres,
                                                          'aplicobeca': titulacion.aplicobeca,
                                                          'tipobeca': titulacion.tipobeca,
                                                          'financiamientobeca': titulacion.financiamientobeca,
                                                          'valorbeca': titulacion.valorbeca})
                    form.editar(titulacion)
                    data['form'] = form
                    return render(request, "th_personal/edittitulacion.html", data)
                except:
                    pass

            if action == 'deltitulacion':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_hoja_vida')
                    data['title'] = u'Eliminar titulación'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['ida']))
                    data['titulacion'] = titulacion = Titulacion.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_personal/deltitulacion.html", data)
                except:
                    pass

            if action == 'addarchivotitulacion':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_hoja_vida')
                    data['title'] = u'Adicionar archivo de titulación'
                    data['titulacion'] = titulacion = Titulacion.objects.get(pk=int(request.GET['id']))
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['ida']))
                    data['form'] = ArchivoTitulacionForm()
                    return render(request, "th_personal/addarchivotitulacion.html", data)
                except:
                    pass

            if action == 'addarchivoexperiencia':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_hoja_vida')
                    data['title'] = u'Adicionar archivo de referencia laboral'
                    data['experiencia'] = experiencia = ExperienciaLaboral.objects.get(pk=int(request.GET['id']))
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['ida']))
                    data['form'] = ArchivoExperienciaForm()
                    return render(request, "th_personal/addarchivoexperiencia.html", data)
                except:
                    pass

            if action == 'addarchivoidioma':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_hoja_vida')
                    data['title'] = u'Adicionar archivo de idioma'
                    data['idioma'] = IdiomaDomina.objects.get(pk=int(request.GET['id']))
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['ida']))
                    data['form'] = ArchivoIdiomaForm()
                    return render(request, "th_personal/addarchivoidioma.html", data)
                except:
                    pass

            if action == 'addcapacitacion':
                try:
                    data['title'] = u'Adicionar capacitación'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['id']))
                    form = CapacitacionPersonaForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, "th_personal/addcapacitacion.html", data)
                except:
                    pass

            if action == 'editcapacitacion':
                try:
                    data['title'] = u'Editar capacitación'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['ida']))
                    data['capacitacion'] = capacitacion = Capacitacion.objects.get(pk=int(request.GET['id']))
                    data['form'] = CapacitacionPersonaForm(initial={'institucion': capacitacion.institucion,
                                                                    'nombre': capacitacion.nombre,
                                                                    'descripcion': capacitacion.descripcion,
                                                                    'tipocurso': capacitacion.tipocurso,
                                                                    'tipocertificacion': capacitacion.tipocertificacion,
                                                                    'tipocapacitacion': capacitacion.tipocapacitacion,
                                                                    'tipoparticipacion': capacitacion.tipoparticipacion,
                                                                    'anio': capacitacion.anio,
                                                                    'contexto': capacitacion.contextocapacitacion,
                                                                    'detallecontexto': capacitacion.detallecontextocapacitacion,
                                                                    'auspiciante': capacitacion.auspiciante,
                                                                    'expositor': capacitacion.expositor,
                                                                    'areaconocimiento': capacitacion.areaconocimiento,
                                                                    'subareaconocimiento': capacitacion.subareaconocimiento,
                                                                    'subareaespecificaconocimiento': capacitacion.subareaespecificaconocimiento,
                                                                    'pais': capacitacion.pais,
                                                                    'provincia': capacitacion.provincia,
                                                                    'canton': capacitacion.canton,
                                                                    'parroquia': capacitacion.parroquia,
                                                                    'fechainicio': capacitacion.fechainicio,
                                                                    'fechafin': capacitacion.fechafin,
                                                                    'horas': capacitacion.horas})
                    #                                                 'tiempo': capacitacion.tiempo
                    return render(request, "th_personal/editcapacitacion.html", data)
                except:
                    pass

            if action == 'delcapacitacion':
                try:
                    data['title'] = u'Eliminar capacitación'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['ida']))
                    data['capacitacion'] = capacitacion = Capacitacion.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_personal/delcapacitacion.html", data)
                except:
                    pass

            if action == 'addarchivocapacitacion':
                try:
                    data['title'] = u'Adicionar archivo de capacitación'
                    data['capacitacion'] = capacitacion = Capacitacion.objects.get(pk=int(request.GET['id']))
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['ida']))
                    data['form'] = ArchivoCapacitacionForm()
                    return render(request, "th_personal/addarchivocapacitacion.html", data)
                except:
                    pass

            if action == 'addexperiencia':
                try:
                    data['title'] = u'Adicionar experiencia'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['id']))
                    form = ExperienciaLaboralForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, "th_personal/addexperiencia.html", data)
                except:
                    pass

            if action == 'editexperiencia':
                try:
                    data['title'] = u'Editar experiencia'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['ida']))
                    data['experiencia'] = experiencia = ExperienciaLaboral.objects.get(pk=int(request.GET['id']))
                    data['form'] = ExperienciaLaboralForm(initial={'tipoinstitucion': experiencia.tipoinstitucion,
                                                                   'institucion': experiencia.institucion,
                                                                   'cargo': experiencia.cargo,
                                                                   'departamento': experiencia.departamento,
                                                                   'pais': experiencia.pais,
                                                                   'provincia': experiencia.provincia,
                                                                   'canton': experiencia.canton,
                                                                   'parroquia': experiencia.parroquia,
                                                                   'fechainicio': experiencia.fechainicio,
                                                                   'fechafin': experiencia.fechafin,
                                                                   'motivosalida': experiencia.motivosalida,
                                                                   'regimenlaboral': experiencia.regimenlaboral,
                                                                   'horassemanales': experiencia.horassemanales,
                                                                   'dedicacionlaboral': experiencia.dedicacionlaboral,
                                                                   'actividadlaboral': experiencia.actividadlaboral,
                                                                   'observaciones': experiencia.observaciones})
                    return render(request, "th_personal/editexperiencia.html", data)
                except:
                    pass

            if action == 'delexperiencia':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_hoja_vida')
                    data['title'] = u'Eliminar experiencia'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['ida']))
                    data['experiencia'] = experiencia = ExperienciaLaboral.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_personal/delexperiencia.html", data)
                except:
                    pass

            if action == 'addidioma':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_hoja_vida')
                    data['title'] = u'Adicionar idioma'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['id']))
                    data['form'] = IdiomaDominaForm()
                    return render(request, "th_personal/addidioma.html", data)
                except:
                    pass

            if action == 'editidioma':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_hoja_vida')
                    data['title'] = u'Editar Idioma'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['ida']))
                    data['idioma'] = idioma = IdiomaDomina.objects.get(pk=request.GET['id'])
                    data['form'] = IdiomaDominaForm(initial={'idioma': idioma.idioma,
                                                             'escritura': idioma.escritura,
                                                             'lectura': idioma.lectura,
                                                             'oral': idioma.oral})
                    return render(request, "th_personal/editidioma.html", data)
                except Exception as ex:
                    pass

            if action == 'editperiodosabatico':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_hoja_vida')
                    data['title'] = u'Editar periodo sabatico'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['ida']))
                    data['form'] = PeriodoSabaticoForm(initial={'periodosabatico': personaadmin.periodosabatico,
                                                                'fechainicioperiodosabatico': personaadmin.fechainicioperiodosabatico if personaadmin.fechainicioperiodosabatico else datetime.now().date(),
                                                                'fechafinperiodosabatico': personaadmin.fechafinperiodosabatico if personaadmin.fechafinperiodosabatico else (datetime.now() + timedelta(days=365)).date()})
                    return render(request, "th_personal/editperiodosabatico.html", data)
                except Exception as ex:
                    pass

            if action == 'editdatointitucion':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_hoja_vida')
                    data['title'] = u'Editar parametros del trabajador'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['id']))
                    data['form'] = DatosPersonaInstitucionForm(initial={'indicebiometrico': personaadmin.identificacioninstitucion,
                                                                        'registro': personaadmin.regitrocertificacion,
                                                                        'servidorcarrera': personaadmin.servidorcarrera,
                                                                        'extension': personaadmin.telefonoextension,
                                                                        'correoinstitucional': personaadmin.emailinst,
                                                                        'fechaingresoies': personaadmin.fechaingresoies if personaadmin.fechaingresoies else datetime.now().date(),
                                                                        'fechasalidaies': personaadmin.fechasalidaies if personaadmin.fechasalidaies else datetime.now().date(),
                                                                        'labora': True if not personaadmin.fechasalidaies else False,
                                                                        'concursomeritos': personaadmin.concursomeritos})
                    return render(request, "th_personal/editdatointitucion.html", data)
                except Exception as ex:
                    pass

            if action == 'delidioma':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_hoja_vida')
                    data['title'] = u'Eliminar idioma'
                    data['personaadmin'] = personaadmin = Persona.objects.get(pk=int(request.GET['ida']))
                    data['idioma'] = idioma = IdiomaDomina.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_personal/delidioma.html", data)
                except:
                    pass

            if action == 'pdf':
                try:
                    data['title'] = u'Adicionar Programa'
                    adduserdata(request, data)
                    persona = Persona.objects.get(pk=int(request.GET['id']))
                    # persona = request.session['persona']
                    profesor = persona.profesor().id
                    data['datospersona'] = persona
                    data['profesor'] = profesor
                    if ResponsableEvaluacion.objects.filter(status=True, activo=True).exists():
                        data['responsable'] = ResponsableEvaluacion.objects.filter(status=True, activo=True)[0]
                    data['periodoslect'] = MigracionEvaluacionDocente.objects.values('idperiodo','tipoeval').filter(idprofesor=profesor,idperiodo=request.GET['idperiodo']).distinct()
                    data['detalleevaluacion'] = migra = MigracionEvaluacionDocente.objects.filter(idprofesor=profesor,idperiodo=request.GET['idperiodo']).order_by('tipoeval','idperiodo','carrera','semestre','materia')
                    data['detalleevalconmodulo'] = migra.filter(modulo=1)
                    data['moduloevalcuatro'] = migra.filter(modulo=1,tipoeval=4)[0] if migra.filter(modulo=1,tipoeval=4).exists() else {}
                    data['detalleevalsinmodulo'] = migra.filter(modulo=0)
                    data['sinmoduloevalcuatro'] = migra.filter(modulo=0,tipoeval=4)[0] if migra.filter(modulo=0,tipoeval=4).exists() else {}
                    data['promperiodosinmodulo'] = promfinalc = round(null_to_numeric(migra.filter(modulo=0).aggregate(prom=Avg('promedioasignatura'))['prom']), 2)
                    data['promperiodoconmodulo'] = promfinal = round(null_to_numeric(migra.filter(modulo=1).aggregate(prom=Avg('promedioasignatura'))['prom']), 2)
                    if promfinal:
                        notaf = str(request.GET['idperiodo']) + "-" + persona.cedula + "-" + str(promfinal)
                    else:
                        notaf = str(request.GET['idperiodo']) + "-" + persona.cedula + "-" + str(promfinalc)
                    data['nomperiodo'] = request.GET['nomperiodo']
                    data['tipoev'] = request.GET['tipoev']
                    qrname = 'qrce_evam_' + request.GET['idperiodo'] + persona.cedula
                    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente', 'qr'))
                    # folder = '/mnt/nfs/home/storage/media/qrcode/evaluaciondocente/'
                    rutapdf = folder + qrname + '.pdf'
                    rutaimg = folder + qrname + '.png'
                    if os.path.isfile(rutapdf):
                        os.remove(rutaimg)
                        os.remove(rutapdf)
                    url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/evaluaciondocente/' + qrname + '.pdf')
                    imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                    imagebarcode = code128.image(notaf).save(folder + qrname + "_bar.png")
                    data['qrname'] = 'qr' + qrname
                    data['fechactual'] = datetime.now().strftime("%d")  + '/' + datetime.now().strftime("%m") + '/' + datetime.now().strftime("%y")+ ' ' + datetime.now().strftime("%H:%M")
                    return conviert_html_to_pdfsave('pro_certificados/certificado_porperiodo.html',
                                                    {
                                                        'pagesize': 'A4',
                                                        'listadoevaluacion': data,
                                                    },qrname + '.pdf'
                                                    )
                except Exception as ex:
                    pass

            if action == 'pdfmodelo2015':
                try:
                    data['title'] = u'Adicionar Programa'
                    adduserdata(request, data)
                    persona = Persona.objects.get(pk=int(request.GET['id']))
                    profesor = persona.profesor().id
                    data['datospersona'] = persona
                    data['profesor'] = profesor
                    if ResponsableEvaluacion.objects.filter(status=True, activo=True).exists():
                        data['responsable'] = ResponsableEvaluacion.objects.filter(status=True, activo=True)[0]
                    data['nomperiodo'] = request.GET['nomperiodo']
                    data['resultados'] = notaporcentaje = ResumenParcialEvaluacionIntegral.objects.filter(profesor=profesor,proceso=request.GET['idperiodo']).order_by('materia__asignaturamalla__malla__carrera__id', 'materia__asignaturamalla__nivelmalla__id')
                    data['porcentaje'] = round(null_to_numeric(notaporcentaje.aggregate(prom=Avg('totalmateriadocencia'))['prom']), 2)
                    data['fechactual'] = datetime.now().strftime("%d") + '/' + datetime.now().strftime("%m") + '/' + datetime.now().strftime("%y")+ ' ' + datetime.now().strftime("%H:%M")
                    notaporcen = "0"+ str(request.GET['idperiodo']) + "-" + persona.cedula + "-" + str(data['porcentaje'])
                    qrname = 'qrce_2015_0' + request.GET['idperiodo'] + persona.cedula
                    # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente', 'qr'))
                    rutapdf = folder + qrname + '.pdf'
                    rutaimg = folder + qrname + '.png'
                    if os.path.isfile(rutapdf):
                        os.remove(rutaimg)
                        os.remove(rutapdf)
                    url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/evaluaciondocente/' + qrname + '.pdf')
                    imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                    imagebarcode = code128.image(notaporcen).save(folder + qrname + "_bar.png")
                    data['qrname'] = 'qr' + qrname
                    return conviert_html_to_pdfsave(
                        'pro_certificados/pdfqrce_2015.html',
                        {
                            'pagesize': 'A4',
                            'listadoevaluacion': data,
                        },qrname + '.pdf'
                    )
                except Exception as ex:
                    pass

            if action == 'pdfmodeloactual':
                try:
                    data['title'] = u'Adicionar Programa'
                    adduserdata(request, data)
                    persona = Persona.objects.get(pk=int(request.GET['ida']))
                    profesor = persona.profesor().id
                    data['datospersona'] = persona
                    data['profesor'] = profesor
                    if ResponsableEvaluacion.objects.filter(status=True, activo=True).exists():
                        data['responsable'] = ResponsableEvaluacion.objects.filter(status=True, activo=True)[0]
                    data['nomperiodo'] = request.GET['nomperiodo']
                    data['resultados'] = porcentaje = ResumenFinalEvaluacionAcreditacion.objects.get(distributivo__profesor=profesor,distributivo__periodo=request.GET['idperiodo'])
                    data['porcentaje'] = notaporcentaje = round(((porcentaje.resultado_total * 100) / 5), 2)
                    data['fechactual'] = datetime.now().strftime("%d") + '/' + datetime.now().strftime("%m") + '/' + datetime.now().strftime("%y")+ ' ' + datetime.now().strftime("%H:%M")
                    notaporcen = str(request.GET['idperiodo']) + "-" + persona.cedula + "-" + str(notaporcentaje)
                    qrname = 'qrce_mied_' + request.GET['idperiodo'] + persona.cedula
                    # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente', 'qr'))
                    # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
                    rutapdf = folder + qrname + '.pdf'
                    rutaimg = folder + qrname + '.png'
                    if os.path.isfile(rutapdf):
                        os.remove(rutaimg)
                        os.remove(rutapdf)
                    url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/evaluaciondocente/' + qrname + '.pdf')
                    imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                    imagebarcode = code128.image(notaporcen).save(folder + qrname + "_bar.png")
                    data['qrname'] = 'qr' + qrname
                    return conviert_html_to_pdfsave(
                        'pro_certificados/pdfqrce_modeloactual.html',
                        {
                            'pagesize': 'A4',
                            'listadoevaluacion': data,
                        },qrname + '.pdf'
                    )
                except Exception as ex:
                    pass

            if action == 'detallepersonal':
                try:
                    data['administrativo'] = personaadmin = Persona.objects.get(pk=int(request.GET['ida']))
                    data['title'] = u'Hoja de vida'
                    data['datosextension'] = personaadmin.datos_extension()
                    data['perfil'] = personaadmin.mi_perfil()
                    data['examenfisico'] = personaadmin.datos_examen_fisico()
                    data['articulos'] = ArticuloInvestigacion.objects.select_related().filter(participantesarticulos__profesor__persona=personaadmin, status=True,participantesarticulos__status=True).order_by('revista__nombre', 'numero', 'nombre')
                    data['ponencias'] = PonenciasInvestigacion.objects.select_related().filter(participanteponencias__profesor__persona=personaadmin, status=True,participanteponencias__status=True)
                    data['capitulolibro'] = CapituloLibroInvestigacion.objects.select_related().filter(participantecapitulolibros__profesor__persona=personaadmin, status=True,participantecapitulolibros__status=True)
                    data['libros'] = LibroInvestigacion.objects.select_related().filter(participantelibros__profesor__persona=personaadmin, status=True, participantelibros__status=True)
                    data['solicitudes'] = SolicitudPublicacion.objects.filter(persona=personaadmin, aprobado=False,status=True)
                    roles = RolPago.objects.filter(periodo__estado=5, persona=personaadmin, status=True)
                    data['reporte_0'] = obtener_reporte('rol_pago')
                    paging = MiPaginador(roles, 25)
                    p = 1
                    try:
                        if 'pagerol' in request.GET:
                            p = int(request.GET['pagerol'])
                        page = paging.page(p)
                    except Exception as ex:
                        page = paging.page(p)
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['roles'] = page.object_list
                    data['niveltitulo'] = NivelTitulacion.objects.filter(status=True).order_by('-rango')
                    activos = ActivoFijo.objects.filter(responsable=personaadmin, statusactivo=1).order_by('ubicacion','descripcion')
                    pagingactivo = MiPaginador(activos, 10)
                    pactivo = 1
                    try:
                        if 'page_activo' in request.GET:
                            pactivo = int(request.GET['page_activo'])
                        pageactivo = pagingactivo.page(pactivo)
                    except Exception as ex:
                        pageactivo = pagingactivo.page(pactivo)
                    data['paging_activo'] = pagingactivo
                    data['rangospaging_activo'] = pagingactivo.rangos_paginado(pactivo)
                    data['page_activo'] = pageactivo
                    data['activos'] = pageactivo.object_list

                    # data['admin'] = personaadmin
                    data['gastospersonales'] = personaadmin.gastospersonales_set.all().order_by('-periodogastospersonales__anio', '-mes')
                    data['pod'] = personaadmin.podevaluaciondet_set.filter(status=True,podperiodo__publicacion__lte=datetime.now().date()).order_by("podperiodo", "departamento")
                    # if personaadmin.es_administrativo() or personaadmin.es_profesor():
                    data['articulos'] = ArticuloInvestigacion.objects.select_related().filter((Q(participantesarticulos__profesor__persona=personaadmin) | Q(participantesarticulos__administrativo__persona=personaadmin)), status=True,participantesarticulos__status=True).order_by('-fechapublicacion')
                    data['ponencias'] = PonenciasInvestigacion.objects.select_related().filter((Q(participanteponencias__profesor__persona=personaadmin) | Q(participanteponencias__administrativo__persona=personaadmin)), status=True,participanteponencias__status=True)
                    data['capitulolibro'] = CapituloLibroInvestigacion.objects.select_related().filter((Q(participantecapitulolibros__profesor__persona=personaadmin) | Q(participantecapitulolibros__profesor__persona=personaadmin)), status=True,participantecapitulolibros__status=True)
                    data['libros'] = LibroInvestigacion.objects.select_related().filter((Q(participantelibros__profesor__persona=personaadmin) | Q(participantelibros__profesor__persona=personaadmin)), status=True, participantelibros__status=True)
                    data['solicitudes'] = SolicitudPublicacion.objects.filter(persona=personaadmin, aprobado=False,status=True)
                    distributivos = personaadmin.distributivopersona_set.all()
                    data['anios'] = personaadmin.lista_anios_trabajados_log()
                    data['jornadas'] = personaadmin.historialjornadatrabajador_set.all()
                    if distributivos:
                        data['distributivo'] = distributivo = distributivos[0]
                    else:
                        data['distributivo'] = None
                    # else:
                    #     data['distributivo'] = None
                    #     data['anios'] = None
                    #     data['jornadas'] = None
                    listadocentes = ParticipantesMatrices.objects.values('proyecto__programa__nombre', 'proyecto__nombre', 'proyecto__tipo', 'horas', 'tipoparticipante__nombre').filter( matrizevidencia_id=2, status=True, proyecto__status=True, profesor__persona=personaadmin)
                    listaadministrativo = ParticipantesMatrices.objects.values('proyecto__programa__nombre','proyecto__nombre', 'proyecto__tipo','horas','tipoparticipante__nombre').filter(matrizevidencia_id=2, status=True, proyecto__status=True, administrativo__persona=personaadmin)
                    data['proyectos'] = listadocentes | listaadministrativo
                    data['reporte_1'] = obtener_reporte('hoja_vida_sagest')
                    data['reporte_activos_persona'] = obtener_reporte('activos_persona')
                    data['reporte_capacitaciones_persona'] = obtener_reporte('capacitaciones_persona')
                    data['reporte_certificaciones_persona'] = obtener_reporte('certificaciones_persona')
                    data['reporte_experiencias_persona'] = obtener_reporte('experiencias_persona')
                    data['perfilprincipal'] = perfilprincipal = request.session['perfilprincipal']
                    if personaadmin.profesor_set.filter(status=True).exists():
                        data['es_profesor'] = True
                        profesor = personaadmin.profesor().id
                        data['profesor'] = profesor
                        data['existeactual'] = RespuestaEvaluacionAcreditacion.objects.values('profesor', 'proceso','proceso__mostrarresultados','proceso__periodo','proceso__periodo__nombre').filter(profesor=profesor).distinct().order_by('proceso')
                        data['existe'] = RespuestaEvaluacionAcreditacion.objects.filter(profesor=profesor,tipoinstrumento=1).exists()
                        data['existeanterior'] = ResumenFinalProcesoEvaluacionIntegral.objects.filter(profesor=profesor).exists()
                        data['periodoslect'] = MigracionEvaluacionDocente.objects.values('idperiodo', 'descperiodo','tipoeval').filter(idprofesor=profesor).distinct().order_by('idperiodo')
                        data['periodoslect'] = MigracionEvaluacionDocente.objects.values('idperiodo', 'descperiodo','tipoeval').filter( idprofesor=profesor).distinct().order_by('idperiodo')
                    else:
                        data['es_profesor']=False
                    data['otromeritos'] = OtroMerito.objects.filter(status=True, persona=personaadmin)
                    data['certificaciones'] = CertificacionPersona.objects.filter(status=True, persona=personaadmin)
                    data['reporte_2'] = obtener_reporte('certificado_laboral')
                    data['informesmensuales'] = personaadmin.informemensual_set.filter(status=True).order_by('-fechainicio')
                    return render(request, "th_personaltrabajador/detallepersonaltrabajador.html", data)
                except Exception as ex:
                    pass

            if action == 'datos':
                try:
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    # ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=datos' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"CEDULA", 4000),
                        (u"EMPLEADO", 8000),
                        (u"CARGO", 4000),
                        (u"DEPARTAMENTO", 4000),
                        (u"REGIMEN", 4000),
                        (u"FECHA DE NACIMIENTO", 5000),
                        (u"FECHA DE INGRESO", 2500),
                    ]

                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    personals = DistributivoPersona.objects.filter(status=True, estadopuesto__id=PUESTO_ACTIVO_ID).order_by('unidadorganica','persona__apellido1')
                    row_num = 1
                    i = 0
                    for personal in personals:
                        i += 1
                        # ws.write(row_num, 0, i, font_style2)
                        ws.write(row_num, 0, personal.persona.cedula, font_style2)
                        ws.write(row_num, 1, personal.persona.apellido1 + ' ' + personal.persona.apellido2 + ' ' + personal.persona.nombres, font_style2)
                        ws.write(row_num, 2, personal.denominacionpuesto.descripcion, font_style2)
                        ws.write(row_num, 3, personal.unidadorganica.nombre, date_format)
                        ws.write(row_num, 4, personal.regimenlaboral.descripcion, font_style2)
                        ws.write(row_num, 5, personal.persona.nacimiento, style1)
                        ws.write(row_num, 6, personal.persona.ingreso_personal_fecha(personal.regimenlaboral), style1)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Personal de la institución trabajador.'
            search = None
            ids = None
            personaladministrativo = Persona.objects.filter(cedula__in=['0909979015',
                                                                        '0910438985',
                                                                        '0912531829',
                                                                        '0909100307',
                                                                        '0912312402',
                                                                        '0911444032',
                                                                        '1200934105',
                                                                        '0914202627',
                                                                        '0919995779',
                                                                        '0922980883',
                                                                        '1201599402',
                                                                        '0914386040',
                                                                        '1714770623',
                                                                        '0912851698',
                                                                        '0921284501',
                                                                        '0919872010',
                                                                        '0915684112',
                                                                        '0918223876',
                                                                        '0913962833',
                                                                        '0906276217',
                                                                        '0907194195',
                                                                        '1707198808',
                                                                        '0920733318',
                                                                        '0917039000',
                                                                        '1202374789',
                                                                        '1203525132',
                                                                        '0924887714',
                                                                        '0701612251',
                                                                        '0909408031',
                                                                        '0911447480',
                                                                        '0923603690',
                                                                        '0912554151',
                                                                        '0919875542',
                                                                        '0920198439',
                                                                        '0921691010',
                                                                        '0917885063',
                                                                        '0915184501',
                                                                        '1202292080',
                                                                        '0917923021',
                                                                        '0927425066',
                                                                        '0917219313',
                                                                        '0916305790',
                                                                        '0927990937',
                                                                        '0104392014',
                                                                        '0927981308',
                                                                        '0925229635',
                                                                        '0922333844',
                                                                        '1202043996',
                                                                        '0917118374',
                                                                        '0918306952',
                                                                        '0914201496',
                                                                        '0915580443',
                                                                        '0919142778',
                                                                        '0921230439',
                                                                        '1201339692',
                                                                        '0912011178',
                                                                        '0922576376',
                                                                        '1203091358',
                                                                        '0703680207',
                                                                        '1708436702',
                                                                        '1203351745',
                                                                        '0914607007',
                                                                        '0908258916',
                                                                        '0909549669',
                                                                        '0954221842',
                                                                        '0919509653',
                                                                        '0918475633']).distinct()
            if 's' in request.GET:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                if len(ss) == 1:
                    administrativos = personaladministrativo.filter(Q(nombres__icontains=search) |
                                                                    Q(apellido1__icontains=search) |
                                                                    Q(apellido2__icontains=search) |
                                                                    Q(cedula__icontains=search) |
                                                                    Q(pasaporte__icontains=search)).distinct()
                else:
                    administrativos = personaladministrativo.filter(Q(apellido1__icontains=ss[0]) & Q(apellido2__icontains=ss[1])).distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                administrativos = personaladministrativo.filter(id=ids).distinct()
            else:
                administrativos = personaladministrativo
            paging = MiPaginador(administrativos, 25)
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
            data['administrativos'] = page.object_list
            data['grupo_docentes'] = PROFESORES_GROUP_ID
            data['grupo_empleadores'] = EMPLEADORES_GRUPO_ID
            data['grupo_estudiantes'] = ALUMNOS_GROUP_ID
            data['grupo_administrativos'] = variable_valor('ADMINISTRATIVOS_GROUP_ID')
            data['titulos_nuevos'] = personaladministrativo.filter(titulacion__verificado=False, titulacion__cursando=False).distinct().count()
            data['cursos_nuevos'] = personaladministrativo.filter(capacitacion__verificado=False).distinct().count()
            data['declaraciones_nuevos'] = personaladministrativo.filter(declaracionbienes__verificado=False).distinct().count()
            data['cbancarias_nuevos'] = personaladministrativo.filter(cuentabancariapersona__verificado=False).distinct().count()
            data['experiencia_nuevos'] = personaladministrativo.filter(experiencialaboral__verificado=False).distinct().count()
            data['total_nuevos'] = 0
            return render(request, 'th_personaltrabajador/view.html', data)