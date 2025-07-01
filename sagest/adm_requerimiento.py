# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Max
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sagest.forms import ProveedorForm, ModuloForm, PrioridadForm, ReqHistoriaForm, ReqHistoriaActividadForm, \
    ResponsableForm, TipoAccionForm, SecuenciaCapacitacionForm, OpcionSistemaForm, \
    CabCapacitacionForm, DetObservacionForm, DetResponsableForm, DetParticipanteForm, DetOpcionForm, VerificadoForm, \
    ElaboradoForm, ReqActividadForm, InformeForm, ArchivoCapacitacionForm, AnexoInformeForm
from sagest.models import Proveedor, ReqHistoria, ReqActividad, ReqPrioridad, \
    DistributivoPersona, ReqHistoriaActividad, SecuenciaCapacitacion, TipoAccion, OpcionSistema, CabCapacitacion, \
    DetObservacion, DetResponsable, DetParticipante, DetOpcion, Informes, BitacoraActividadDiaria, TIPO_CAPACITACION, \
    DenominacionPuesto, AnexoInforme
from settings import EMAIL_DOMAIN, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT, REDIS_BD
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, puede_realizar_accion, generar_nombre, convertir_fecha
from django.forms import model_to_dict
from datetime import datetime
from sga.templatetags.sga_extras import encrypt
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import Modulo, Persona
from sagest.celery_task import demo_task
import xlwt
from xlwt import *
import random

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    data['personaadmin']= persona = request.session['persona']
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        # elif action == 'addtipoaccion':
        #     try:
        #         f = TipoAccionForm(request.POST)
        #         if f.is_valid():
        #             tipoaccion = TipoAccion(nombre=f.cleaned_data['nombre'])
        #             tipoaccion.save(request)
        #             log(u'Adiciono tipo accion: %s' % tipoaccion, request, "add")
        #             return JsonResponse({"result": "ok"})
        #         else:
        #             raise NameError('Error')
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        #
        # elif action == 'edittipoaccion':
        #     try:
        #         tipo = TipoAccion.objects.get(pk=request.POST['id'])
        #         f = TipoAccionForm(request.POST)
        #         if f.is_valid():
        #             tipo.nombre = f.cleaned_data['nombre']
        #             tipo.save(request)
        #             log(u'Modificó Tipo Acción: %s' % tipo, request, "edit")
        #             return JsonResponse({"result": "ok"})
        #         else:
        #             raise NameError('Error')
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        #
        # elif action == 'deletetipoaccion':
        #     try:
        #         tipo = TipoAccion.objects.get(pk=request.POST['id'])
        #         # if tipo.en_uso():
        #         #     return JsonResponse({"result": "bad", "mensaje": u"El sistema esta en uso no puede eliminar"})
        #         tipo.status = False
        #         tipo.save(request)
        #         log(u'Eliminó Tipo Acción: %s' % tipo, request, "del")
        #         return JsonResponse({"result": "ok"})
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})
        #
        if action == 'addsecuenciacapacitacion':
            try:
                f = SecuenciaCapacitacionForm(request.POST)
                if f.is_valid():
                    secuencia = SecuenciaCapacitacion(secuencia=f.cleaned_data['secuencia'],
                                                      descripcion=f.cleaned_data['descripcion'],
                                                      anio=f.cleaned_data['anio'],
                                                      vigente=f.cleaned_data['vigente'],
                                                      )
                    secuencia.save(request)
                    log(u'Adiciono Secuencia: %s' % secuencia, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editsecuenciacapacitacion':
            try:
                secuencia = SecuenciaCapacitacion.objects.get(pk=request.POST['id'])
                f = SecuenciaCapacitacionForm(request.POST)
                if f.is_valid():
                    secuencia.secuencia = f.cleaned_data['secuencia']
                    secuencia.descripcion = f.cleaned_data['descripcion']
                    secuencia.anio = f.cleaned_data['anio']
                    secuencia.secuencia = f.cleaned_data['secuencia']
                    secuencia.vigente = f.cleaned_data['vigente']
                    secuencia.save(request)
                    log(u'Modificó Secuencia Capacitación: %s' % secuencia, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletesecuenciacapacitacion':
            try:
                secuencia = SecuenciaCapacitacion.objects.get(pk=request.POST['id'])
                # if tipo.en_uso():
                #     return JsonResponse({"result": "bad", "mensaje": u"El sistema esta en uso no puede eliminar"})
                secuencia.status = False
                secuencia.save(request)
                log(u'Eliminó Secuencia Capacitación: %s' % secuencia, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addopcionsistema':
            try:
                f = OpcionSistemaForm(request.POST)
                if f.is_valid():
                    opcion = OpcionSistema(descripcion=f.cleaned_data['descripcion'],
                                           modulo=Modulo.objects.get(pk=int(f.cleaned_data['modulo'])),
                                           visible=f.cleaned_data['visible']

                                           )
                    opcion.save(request)
                    log(u'Adiciono Opción Sistema: %s' % opcion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editopcionsistema':
            try:
                opcion = OpcionSistema.objects.get(pk=request.POST['id'])
                f = OpcionSistemaForm(request.POST)
                if f.is_valid():
                    opcion.descripcion = f.cleaned_data['descripcion'],
                    opcion.modulo = Modulo.objects.get(pk=int(f.cleaned_data['modulo']))

                    opcion.save(request)
                    log(u'Modificó Opción Sistema: %s' % opcion, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        # elif action == 'deleteopcionsistema':
        #     try:
        #         opcion = OpcionSistema.objects.get(pk=request.POST['id'])
        #         # if tipo.en_uso():
        #         #     return JsonResponse({"result": "bad", "mensaje": u"El sistema esta en uso no puede eliminar"})
        #         opcion.status = False
        #         opcion.save(request)
        #         log(u'Eliminó Opción Sistema: %s' % opcion, request, "del")
        #         return JsonResponse({"result": "ok"})
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})
        #
        if action == 'addcab':
            try:
                f = CabCapacitacionForm(request.POST)
                if f.is_valid():
                    if SecuenciaCapacitacion.objects.filter(status=True, vigente=True).exists():
                        sec = SecuenciaCapacitacion.objects.get(status=True, vigente=True).pk
                    else :
                        sec=None
                    secuencias = secuencia_capacitacion(sec)

                    capacitacion = CabCapacitacion(
                        secuencia=int(secuencias),
                        confsecuencia=SecuenciaCapacitacion.objects.get(status=True, vigente=True),
                        antecedente=f.cleaned_data['antecedente'],
                        horainicio=f.cleaned_data['horainicio'],
                        departamento=f.cleaned_data['departamento'],
                        fecha=f.cleaned_data['fecha'],
                        seccion=f.cleaned_data['seccion'],
                        horafin=f.cleaned_data['horafin'],
                        tiposistema = f.cleaned_data['tiposistema'],
                        tipocapacitacion = f.cleaned_data['tipocapacitacion'],
                        #sistema=ReqSistema.objects.get(pk=int(f.cleaned_data['sistema'])),
                        #tipoaccion=TipoAccion.objects.get(pk=int(f.cleaned_data['tipoaccion'])),
                        elaborado_id=f.cleaned_data['elaborado'].persona_id,
                        # elaborado=f.cleaned_data['elaborado'],
                        verificado=f.cleaned_data['verificado'],
                        aprobado=f.cleaned_data['aprobado'],

                    )

                    capacitacion.save(request)
                    log(u'Adiciono Capacitación: %s' % capacitacion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcab':
            try:
                cab = CabCapacitacion.objects.get(pk=request.POST['id'])
                f = CabCapacitacionForm(request.POST)
                if f.is_valid():
                    cab.departamento = f.cleaned_data['departamento']
                    cab.seccion = f.cleaned_data['seccion']
                    #cab.secuencia = f.cleaned_data['secuencia']
                    cab.fecha = f.cleaned_data['fecha']
                    cab.horainicio = f.cleaned_data['horainicio']
                    cab.horafin = f.cleaned_data['horafin']
                    cab.antecedente = f.cleaned_data['antecedente']
                    cab.tiposistema = f.cleaned_data['tiposistema']
                    cab.tipocapacitacion = f.cleaned_data['tipocapacitacion']
                    # cab.sistema = ReqSistema.objects.get(pk=int(f.cleaned_data['sistema']))
                    #cab.tipoaccion = TipoAccion.objects.get(pk=int(f.cleaned_data['tipoaccion']))
                    cab.elaborado_id = f.cleaned_data['elaborado'].persona_id
                    cab.verificado = f.cleaned_data['verificado']
                    cab.aprobado = f.cleaned_data['aprobado']
                    cab.save(request)
                    log(u'Modificó Opción Sistema: %s' % cab, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editelaborado':
            try:
                cab = CabCapacitacion.objects.get(pk=request.POST['id'])
                f = ElaboradoForm(request.POST)
                if f.is_valid():

                    cab.elaborado = Persona.objects.get(pk=int(f.cleaned_data['elaborado']))

                    cab.save(request)
                    log(u'Modificó El Campo Elaborado: %s' % cab, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editverificado':
            try:
                cab = CabCapacitacion.objects.get(pk=request.POST['id'])
                f = VerificadoForm(request.POST)
                if f.is_valid():
                    cab.verificado = Persona.objects.get(pk=int(f.cleaned_data['verificado']))
                    cab.save(request)
                    log(u'Modificó El Campo Verificado: %s' % cab, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletecab':
            try:
                cab = CabCapacitacion.objects.get(pk=request.POST['id'])
                # if tipo.en_uso():
                #     return JsonResponse({"result": "bad", "mensaje": u"El sistema esta en uso no puede eliminar"})
                cab.status = False
                cab.save(request)
                log(u'Eliminó Capacitación: %s' % cab, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addobservacion':
            try:
                f = DetObservacionForm(request.POST)
                if f.is_valid():
                    detobservacion = DetObservacion(
                        capacitacion=CabCapacitacion.objects.get(pk=int(request.POST['idobservacion'])),
                        observacion=f.cleaned_data['observacion'],
                        estado=f.cleaned_data['estado'],
                        responsable_id=f.cleaned_data['responsable'].persona_id,
                        fecha=f.cleaned_data['fecha']

                    )
                    detobservacion.save(request)
                    log(u'Adiciono Observación: %s' % detobservacion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editobservacion':
            try:
                detobservacion = DetObservacion.objects.get(pk=request.POST['id'])
                f = DetObservacionForm(request.POST)
                if f.is_valid():
                    detobservacion.observacion = f.cleaned_data['observacion']
                    detobservacion.estado = f.cleaned_data['estado']
                    detobservacion.responsable_id = f.cleaned_data['responsable'].persona_id
                    detobservacion.fecha = f.cleaned_data['fecha']
                    detobservacion.save(request)
                    log(u'Modificó  Observación: %s' % detobservacion, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteobservacion':
            try:
                detobservacion = DetObservacion.objects.get(pk=request.POST['id'])
                # if tipo.en_uso():
                #     return JsonResponse({"result": "bad", "mensaje": u"El sistema esta en uso no puede eliminar"})
                detobservacion.status = False
                detobservacion.save(request)
                log(u'Eliminó Observación: %s' % detobservacion, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addresponsables':
            try:
                f = DetResponsableForm(request.POST)
                if f.is_valid():
                    detobservacion = DetResponsable(
                        capacitacion=CabCapacitacion.objects.get(pk=int(request.POST['idrespon'])),
                        responsable_id=f.cleaned_data['responsable'].persona_id,
                    )
                    detobservacion.save(request)
                    log(u'Adiciono Responsable: %s' % detobservacion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editresponsable':
            try:
                detresponsable = DetResponsable.objects.get(pk=request.POST['id'])
                f = DetResponsableForm(request.POST)
                if f.is_valid():
                    detresponsable.responsable_id = f.cleaned_data['responsable'].persona_id
                    detresponsable.save(request)
                    log(u'Modificó  Responsable: %s' % detresponsable, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteresponsable':
            try:
                detresponsable = DetResponsable.objects.get(pk=request.POST['id'])
                # if tipo.en_uso():
                #     return JsonResponse({"result": "bad", "mensaje": u"El sistema esta en uso no puede eliminar"})
                detresponsable.status = False
                detresponsable.save(request)
                log(u'Eliminó Responsable: %s' % detresponsable, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'subirarchivo':
            try:
                cab = CabCapacitacion.objects.get(pk=request.POST['id'])
                f = ArchivoCapacitacionForm(request.POST, request.FILES)
                newfile = None
                if f.is_valid():
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                    cab.archivo = newfile
                    cab.save(request)
                    log(u'Agregó archivo capacitacion: %s' % cab, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        elif action == 'addparticipante':
            try:
                f = DetParticipanteForm(request.POST)
                if f.is_valid():
                    detparticipante = DetParticipante(
                        capacitacion=CabCapacitacion.objects.get(pk=int(request.POST['idpartici'])),
                        participante=Persona.objects.get(pk=f.cleaned_data['participante']),
                        cargo= f.cleaned_data['cargo'],
                    )
                    detparticipante.save(request)
                    log(u'Adiciono Participante: %s' % detparticipante, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editparticipante':
            try:
                detparticipante = DetParticipante.objects.get(pk=request.POST['id'])
                f = DetParticipanteForm(request.POST)
                if f.is_valid():
                    detparticipante.participante = Persona.objects.get(pk=f.cleaned_data['participante'])
                    detparticipante.cargo = f.cleaned_data['cargo']
                    detparticipante.save(request)
                    log(u'Modificó  Participantes: %s' % detparticipante, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteparticipante':
            try:
                detparticipantes = DetParticipante.objects.get(pk=request.POST['id'])
                # if tipo.en_uso():
                #     return JsonResponse({"result": "bad", "mensaje": u"El sistema esta en uso no puede eliminar"})
                detparticipantes.status = False
                detparticipantes.save(request)
                log(u'Eliminó Participantes: %s' % detparticipantes, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addopcion':
            try:
                f = DetOpcionForm(request.POST)
                if f.is_valid():
                    detopcion = DetOpcion(
                        capacitacion=CabCapacitacion.objects.get(pk=int(request.POST['idopcion'])),
                        # opcion=OpcionSistema.objects.get(pk=f.cleaned_data['opcion']),
                        responsable_id=f.cleaned_data['responsable'].persona_id,
                        modulo=f.cleaned_data['modulo'],
                        observacion=f.cleaned_data['observacion'],
                    )
                    detopcion.save(request)
                    log(u'Adiciono Opciones: %s' % detopcion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editopcion':
            try:
                detopcion = DetOpcion.objects.get(pk=request.POST['id'])
                f = DetOpcionForm(request.POST)
                if f.is_valid():
                    # detopcion.opcion = OpcionSistema.objects.get(pk=f.cleaned_data['opcion'])
                    detopcion.responsable_id = f.cleaned_data['responsable'].persona_id
                    detopcion.modulo= f.cleaned_data['modulo']
                    detopcion.observacion= f.cleaned_data['observacion']
                    detopcion.save(request)
                    log(u'Modificó  Opciones: %s' % detopcion, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteopcion':
            try:
                detopcion = DetOpcion.objects.get(pk=request.POST['id'])
                # if tipo.en_uso():
                #     return JsonResponse({"result": "bad", "mensaje": u"El sistema esta en uso no puede eliminar"})
                detopcion.status = False
                detopcion.save(request)
                log(u'Eliminó Opciones: %s' % detopcion, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addmodulo':
            try:
                f = ModuloForm(request.POST)
                if f.is_valid():
                    modulo = OpcionSistema(modulo=f.cleaned_data['sistema'],
                                       nombre=f.cleaned_data['nombre'],
                                       descripcion=f.cleaned_data['descripcion'],
                                       estado=1)
                    modulo.save(request)
                    log(u'Adiciono modulo: %s' % modulo.nombre, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deldetalle':
            try:
                if ReqHistoriaActividad.objects.filter(pk=request.POST['id'], status=True):
                    actividad = ReqHistoriaActividad.objects.get(pk=request.POST['id'], status=True)
                    if actividad.estado == 1:
                        actividad.delete()
                        log(u'Elimino una actividad: %s' % actividad, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        # --- MANTENIMIENTO DE MODULOS
        # --- GUARDAR AGREGAR MODULO
        elif action == 'SaveAddModulo':
            try:
                f = ModuloForm(request.POST)
                if f.is_valid():
                    modulo = Modulo(url=f.cleaned_data['url'],
                                    nombre=f.cleaned_data['nombre'],
                                    icono=f.cleaned_data['icono'],
                                    descripcion=f.cleaned_data['descripcion'],
                                    activo=f.cleaned_data['activo'],
                                    sga=f.cleaned_data['sga'],
                                    sagest=f.cleaned_data['sagest'],
                                    posgrado=f.cleaned_data['posgrado']
                                    )
                    modulo.save(request)
                    log(u'Adiciono modulo: %s' % modulo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # --- GUARDAR EDITAR MODULO
        elif action == 'SaveEditModulo':
            try:
                modulo = Modulo.objects.get(pk=request.POST['id'])
                f = ModuloForm(request.POST)
                if f.is_valid():
                    modulo.url = f.cleaned_data['url']
                    modulo.nombre = f.cleaned_data['nombre']
                    modulo.icono = f.cleaned_data['icono']
                    modulo.descripcion = f.cleaned_data['descripcion']
                    modulo.activo = f.cleaned_data['activo']
                    modulo.sga = f.cleaned_data['sga']
                    modulo.sagest = f.cleaned_data['sagest']
                    modulo.posgrado = f.cleaned_data['posgrado']
                    modulo.save(request)
                    log(u'Modificó modulo: %s' % modulo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # --- GUARDAR INACTIVAR MODULO
        elif action == 'SaveInactiveModulo':
            try:
                modulo = Modulo.objects.get(pk=int(request.POST['id']))
                log(u'Inactivo modulo: %s' % modulo, request, "edit")
                modulo.status = False
                modulo.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # --- GUARDAR ACTIVAR MODULO
        elif action == 'SaveActiveModulo':
            try:
                modulo = Modulo.objects.get(pk=int(request.POST['id']))
                log(u'Activo modulo: %s' % modulo, request, "edit")
                modulo.status = True
                modulo.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # --- GUARDAR AGREGAR HISTORIA
        elif action == 'SaveAddHistoria':
            try:
                form = ReqHistoriaForm(request.POST, request.FILES)
                newfile = None
                if form.is_valid():
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("historiarequerimiento_", newfile._name)
                    distributivo = DistributivoPersona.objects.filter(status=True, id=form.cleaned_data['solicita'])[0]
                    historia = ReqHistoria(modulo=form.cleaned_data['modulo'],
                                           solicita=distributivo.persona,
                                           fecha=datetime.now().date(),
                                           denominacionpuesto=distributivo.denominacionpuesto if distributivo.denominacionpuesto else None,
                                           departamento=distributivo.unidadorganica if distributivo.unidadorganica else None,
                                           asunto=form.cleaned_data['asunto'],
                                           cuerpo=form.cleaned_data['cuerpo'],
                                           prioridad=form.cleaned_data['prioridad'],
                                           estado=1,
                                           archivo=newfile)
                    historia.save(request)
                    # for x in ReqActividad.objects.filter(status=True, vigente=True):
                    #     historiaactividad = ReqHistoriaActividad(historia=historia,
                    #                                              actividad=x,
                    #                                              )
                    #     historiaactividad.save()
                    log(u'Agrego una nueva historia: %s' % historia, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # --- GUARDAR EDITAR HISTORIA
        elif action == 'SaveEditHistoria':
            try:
                historia = ReqHistoria.objects.get(id=request.POST['id'])
                form = ReqHistoriaForm(request.POST, request.FILES)
                newfile = None
                if form.is_valid():
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("historiarequerimiento_", newfile._name)
                    distributivo = DistributivoPersona.objects.filter(status=True, id=form.cleaned_data['solicita'])[0]
                    historia.modulo = form.cleaned_data['modulo']
                    historia.solicita = distributivo.persona
                    historia.denominacionpuesto = distributivo.denominacionpuesto if distributivo.denominacionpuesto else None
                    historia.departamento = distributivo.unidadorganica if distributivo.unidadorganica else None
                    historia.asunto = form.cleaned_data['asunto']
                    historia.cuerpo = form.cleaned_data['cuerpo']
                    historia.prioridad = form.cleaned_data['prioridad']
                    historia.archivo = newfile
                    historia.save(request)
                    log(u'Modifico historia: %s' % historia, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # --- GUARDAR INACTIVAR HISTORIA
        elif action == 'SaveInactiveHistoria':
            try:
                historia = ReqHistoria.objects.get(pk=int(request.POST['id']))
                log(u'Inactivo requerimiento: %s' % historia, request, "edit")
                historia.status = False
                historia.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # --- GUARDAR ACTIVAR HISTORIA
        elif action == 'SaveActiveHistoria':
            try:
                historia = ReqHistoria.objects.get(pk=int(request.POST['id']))
                log(u'Activo requerimiento: %s' % historia, request, "edit")
                historia.status = True
                historia.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # --- GUARDAR AGREGAR RESPONSABLE
        elif action == 'SaveAddResponsable':
            try:
                historia = ReqHistoria.objects.get(id=request.POST['id_historia'])
                distributivo = DistributivoPersona.objects.get(id=request.POST['id_distributivo'])
                historia.responsable = distributivo.persona
                if not historia.estado == 3 or not historia.estado == 4:
                    historia.estado = 2
                historia.save(request)
                log(u'Asigno responsable de requerimiento: %s %s' % (historia, historia.responsable), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # --- GUARDAR INACTIVAR ACTIVIDAD
        elif action == 'SaveInactiveActividad':
            try:
                actividad = ReqActividad.objects.get(pk=request.POST['id'])
                # if actividad.en_uso():
                #    return JsonResponse({"result": "bad", "mensaje": u"La actividad esta en uso no puede inactivar"})
                log(u'Modifico actividad: %s' % actividad, request, "edit")
                actividad.status = False
                actividad.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # --- GUARDAR ACTIVAR ACTIVIDAD
        elif action == 'SaveActiveActividad':
            try:
                actividad = ReqActividad.objects.get(pk=request.POST['id'])
                log(u'Modifico actividad: %s' % actividad, request, "edit")
                actividad.status = True
                actividad.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # --- GUARDAR AGREGAR ACTIVIDAD
        elif action == 'SaveAddActividad':
            try:
                f = ReqActividadForm(request.POST)
                if f.is_valid():
                    actividad = ReqActividad(nombre=f.cleaned_data['nombre'],
                                             vigente=f.cleaned_data['vigente'])
                    actividad.save(request)
                    log(u'Adiciono actividad: %s' % actividad, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addanexoinforme':
            try:
                f = AnexoInformeForm(request.POST, request.FILES)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if newfile.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                        if newfile:
                            newfile._name = generar_nombre("anexoinforme", newfile._name)
                if f.is_valid():
                    anexoinforme = AnexoInforme(tipoanexo=f.cleaned_data['tipoanexo'],
                                                informe_id=request.POST['id'],
                                                descripcion=f.cleaned_data['descripcion'])
                    anexoinforme.archivo = newfile
                    anexoinforme.save(request)
                    log(u'Adiciono anexo informe: %s' % anexoinforme, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editanexoinforme':
            try:
                f = AnexoInformeForm(request.POST)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if newfile.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                        if newfile:
                            newfile._name = generar_nombre("informetic", newfile._name)
                anexo = AnexoInforme.objects.get(pk=request.POST['id'])
                if f.is_valid():
                    anexo.tipoanexo = f.cleaned_data['tipoanexo']
                    anexo.descripcion = f.cleaned_data['descripcion']
                    if newfile:
                        anexo.archivo = newfile
                    anexo.save(request)
                    log(u'Modificó anexo informe: %s' % anexo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delanexoinforme':
            try:
                anexo = AnexoInforme.objects.get(pk=request.POST['id'])
                anexo.status = False
                anexo.save(request)
                log(u'Eliminó anexo informe: %s' % anexo, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})


        # --- GUARDAR EDITAR ACTIVIDAD
        elif action == 'SaveEditActividad':
            try:
                actividad = ReqActividad.objects.get(pk=request.POST['id'])
                f = ReqActividadForm(request.POST)
                if f.is_valid():
                    actividad.nombre = f.cleaned_data['nombre']
                    actividad.vigente = f.cleaned_data['vigente']
                    actividad.save(request)
                    log(u'Modificó actividad: %s' % actividad, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # --- GUARDAR AGREGAR PRIORIDAD
        elif action == 'SaveAddPrioridad':
            try:
                form = PrioridadForm(request.POST, request.FILES)
                newfile = None
                if form.is_valid():
                    if not ReqPrioridad.objects.filter(status=True,
                                                       nombre=form.cleaned_data['nombre'].upper()).exists():
                        if 'imagen' in request.FILES:
                            newfile = request.FILES['imagen']
                            newfile._name = generar_nombre("prioridadrequerimiento_", newfile._name)
                        prioridad = ReqPrioridad(nombre=form.cleaned_data['nombre'],
                                                 codigo=form.cleaned_data['codigo'],
                                                 horamax=form.cleaned_data['hora'] if len(
                                                     form.cleaned_data['hora']) > 1 else '0' + form.cleaned_data[
                                                     'hora'],
                                                 minutomax=form.cleaned_data['minuto'] if len(
                                                     form.cleaned_data['minuto']) > 1 else '0' + form.cleaned_data[
                                                     'minuto'],
                                                 segundomax=form.cleaned_data['segundo'] if len(
                                                     form.cleaned_data['segundo']) > 1 else '0' + form.cleaned_data[
                                                     'segundo'],
                                                 imagen=newfile
                                                 )
                        prioridad.save(request)
                        log(u'Agrego una nueva prioridad: %s' % prioridad, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"El registro ya existe."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # --- GUARDAR EDITAR PRIORIDAD
        elif action == 'SaveEditPrioridad':
            try:
                prioridad = ReqPrioridad.objects.get(pk=int(request.POST['id']))
                form = PrioridadForm(request.POST, request.FILES)
                newfile = None
                if form.is_valid():
                    if 'imagen' in request.FILES:
                        newfile = request.FILES['imagen']
                        newfile._name = generar_nombre("historiaprioridad_", newfile._name)
                    prioridad.nombre = form.cleaned_data['nombre']
                    prioridad.codigo = form.cleaned_data['codigo']
                    prioridad.horamax = form.cleaned_data['hora'] if len(form.cleaned_data['hora']) > 1 else '0' + \
                                                                                                             form.cleaned_data[
                                                                                                                 'hora']
                    prioridad.minutomax = form.cleaned_data['minuto'] if len(form.cleaned_data['minuto']) > 1 else '0' + \
                                                                                                                   form.cleaned_data[
                                                                                                                       'minuto']
                    prioridad.segundomax = form.cleaned_data['segundo'] if len(
                        form.cleaned_data['segundo']) > 1 else '0' + form.cleaned_data['segundo']
                    prioridad.imagen = newfile
                    prioridad.save(request)
                    log(u'Actualizo Prioridad: %s' % prioridad, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # --- GUARDAR INACTIVAR PRIORIDAD
        elif action == 'SaveInactivePrioridad':
            try:
                prioridad = ReqPrioridad.objects.get(pk=int(request.POST['id']))
                log(u'Modifico prioridad: %s' % prioridad, request, "edit")
                prioridad.status = False
                prioridad.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # --- GUARDAR ACTIVAR PRIORIDAD
        elif action == 'SaveActivePrioridad':
            try:
                prioridad = ReqPrioridad.objects.get(pk=int(request.POST['id']))
                log(u'Modifico prioridad: %s' % prioridad, request, "edit")
                prioridad.status = True
                prioridad.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # --- LOAD DETALLE DEL REQUERIMIENTO
        elif action == 'LoadDetalleActividad':
            try:
                id = int(request.POST['idd'])
                actividaddet = ReqHistoriaActividad.objects.get(id=id)
                distributivo = actividaddet.responsable.distributivopersona_set.filter(status=True)[0]

                data = {"result": "ok",
                        "responsable": {
                            "id": actividaddet.responsable.mis_plantillas_actuales()[
                                0].id if actividaddet.responsable else None,
                            "name": u"%s" % (actividaddet.responsable),
                        },
                        "actividad": actividaddet.actividad.id if actividaddet.actividad else None,
                        "estado": actividaddet.estado if actividaddet.estado else None,
                        "fechainicio": actividaddet.fechainicio.date().strftime(
                            '%d-%m-%Y') if actividaddet.fechainicio else None,
                        "fechafin": actividaddet.fechafin.date().strftime(
                            '%d-%m-%Y') if actividaddet.fechafin else None,
                        "descripcion": actividaddet.descripcion if actividaddet.descripcion else None}

                return JsonResponse(data)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # --- GUARDAR DETALLE DEL REQUERIMIENTO
        elif action == 'SaveDetalleActividad':
            try:
                distributivo = None
                actividad = None
                historia = ReqHistoria.objects.get(id=int(request.POST['idc']))
                if 'responsable' in request.POST:
                    if not request.POST['responsable'] and int(request.POST['idd']) != 0:
                        hactividadd = ReqHistoriaActividad.objects.get(id=int(request.POST['idd']))
                        distributivo = hactividadd.responsable.distributivopersona_set.filter(status=True)[0]
                    elif int(request.POST['responsable']) != 0:
                        distributivo = DistributivoPersona.objects.get(id=int(request.POST['responsable']))
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error de datos del representante."})

                if request.POST['actividad'] and int(request.POST['actividad']) != 0:
                    actividad = ReqActividad.objects.get(id=int(request.POST['actividad']))
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error de datos de la actividad."})
                form2 = ReqHistoriaActividadForm(request.POST)
                if form2.is_valid():
                    if request.POST['idd'] and int(request.POST['idd']) == 0:
                        actividaddet = ReqHistoriaActividad(historia=historia,
                                                            descripcion=form2.cleaned_data['descripcion'],
                                                            actividad=actividad,
                                                            fechainicio=form2.cleaned_data['fechainicio'],
                                                            fechafin=form2.cleaned_data['fechafin'],
                                                            responsable=distributivo.persona,
                                                            estado=form2.cleaned_data['estado'])
                        actividaddet.save(request)
                        actividaddet.actualizar_estado()
                        log(u'Agrego una nueva detalle a la historia: %s' % actividaddet, request, "add")
                        return JsonResponse({"result": "ok", "estado": actividaddet.historia.estado})
                    else:
                        actividaddet = ReqHistoriaActividad.objects.get(id=int(request.POST['idd']))
                        actividaddet.descripcion = form2.cleaned_data['descripcion']
                        actividaddet.actividad = actividad
                        actividaddet.fechainicio = form2.cleaned_data['fechainicio']
                        actividaddet.fechafin = form2.cleaned_data['fechafin']
                        actividaddet.responsable = distributivo.persona
                        actividaddet.estado = form2.cleaned_data['estado']
                        actividaddet.save(request)
                        actividaddet.actualizar_estado()
                        log(u'Modifico un detalle a la historia: %s' % actividaddet, request, "edit")
                        return JsonResponse({"result": "ok", "estado": actividaddet.historia.estado})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error de datos del formulario."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # --- GUARDAR INACTIVAR DETALLE DE LA ACTIVIDAD
        elif action == 'SaveInactiveHistoriaDetalle':
            try:
                historia = ReqHistoria.objects.get(id=int(request.POST['idc']))
                actividaddet = ReqHistoriaActividad.objects.get(id=int(request.POST['idd']))
                log(u'Inactivo detalle de historia: %s' % actividaddet, request, "edit")
                actividaddet.status = False
                actividaddet.save()
                actividaddet.actualizar_estado()
                return JsonResponse({"result": "ok", "estado": actividaddet.historia.estado})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # --- GUARDAR ACTIVAR DETALLE DE LA ACTIVIDAD
        elif action == 'SaveActiveHistoriaDetalle':
            try:
                historia = ReqHistoria.objects.get(id=int(request.POST['idc']))
                actividaddet = ReqHistoriaActividad.objects.get(id=int(request.POST['idd']))
                log(u'Activo detalle de historia: %s' % actividaddet, request, "edit")
                actividaddet.status = True
                actividaddet.save()
                actividaddet.actualizar_estado()
                return JsonResponse({"result": "ok", "estado": actividaddet.historia.estado})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'loadDemoProceso':
            # https://django-q.readthedocs.io/en/latest/brokers.html
            # from tasks.queues import my_queue
            # import redis as Redis
            from django_q.tasks import async_task
            # from tasks.demo import mi_tarea
            try:
                # task_id = demo_task.delay()
                # "task_id": task_id.id
                task = "Tarea de ejemplo"
                # my_queue.put(task)
                # redis_conn = Redis.StrictRedis(host=REDIS_HOST, password=REDIS_PASSWORD, port=REDIS_PORT, db=REDIS_BD + 1)
                # redis_conn.publish('cola_redis', task)
                id = async_task('tasks.demo.demo', 1, 2, group='grupo_demo', task_name='demo_manejar_tarea')
                print(f"id: ", id)
                return JsonResponse({"result": "ok", "task_id": task})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al al cargar el proceso."})

        elif action == 'addinforme':
            try:
                f = InformeForm(request.POST)
                newfile=None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if newfile.size > 50485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 50 Mb."})
                        if newfile:
                            newfile._name = generar_nombre("informetic", newfile._name)
                if f.is_valid():
                    informe = Informes(codigo=f.cleaned_data['codigo'],
                                       departamento=f.cleaned_data['departamento'],
                                       fecha=f.cleaned_data['fecha'],
                                       objetivo=f.cleaned_data['objetivo'],
                                       experto=f.cleaned_data['experto'],
                                       director=f.cleaned_data['director'],
                                       archivo=newfile)
                    informe.save(request)

                    for responsable in f.cleaned_data['responsables']:
                        res = informe.responsables
                        res.add(responsable.persona_id)

                    log(u'Ingreso informe tic: %s' % informe, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editinforme':
            try:
                f = InformeForm(request.POST)
                newfile = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if newfile.size > 50485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                        if newfile:
                            newfile._name = generar_nombre("informetic", newfile._name)
                informe = Informes.objects.get(pk=request.POST['id'])
                if f.is_valid():
                    informe.codigo = f.cleaned_data['codigo']
                    informe.departamento = f.cleaned_data['departamento']
                    informe.fecha = f.cleaned_data['fecha']
                    informe.objetivo = f.cleaned_data['objetivo']
                    informe.experto = f.cleaned_data['experto']
                    informe.director = f.cleaned_data['director']
                    if newfile:
                        informe.archivo = newfile
                    informe.save(request)

                    for responsable in informe.responsables.all():
                        informe.responsables.remove(responsable)

                    for responsable in f.cleaned_data['responsables']:
                        res = informe.responsables
                        res.add(responsable.persona_id)

                    # informe.responsables=f.cleaned_data['responsables']
                    log(u'Modificó informe tic: %s' % informe, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delinforme':
            try:
                informe = Informes.objects.get(pk=request.POST['id'])
                informe.status = False
                informe.save(request)
                log(u'Eliminó Informe tic: %s' % informe, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Registro de Requerimientos'
        if 'action' in request.GET:
            action = request.GET['action']
            # if action == 'sistema':
            #     try:
            #         data['title'] = 'SISTEMAS'
            #         search = None
            #         ids = None
            #         if 's' in request.GET:
            #             search = request.GET['s'].strip()
            #             sistema = ReqSistema.objects.filter(status=True, nombre__icontains=search)
            #         else:
            #             sistema = ReqSistema.objects.filter(status=True)
            #         paging = MiPaginador(sistema, 25)
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
            #         data['page'] = page
            #         data['rangospaging'] = paging.rangos_paginado(p)
            #         data['sistemas'] = page.object_list
            #         data['search'] = search if search else ""
            #         data['ids'] = ids if ids else ""
            #         return render(request, "adm_requerimiento/sistema.html", data)
            #     except Exception as ex:
            #         pass
            #
            # elif action == 'addsistema':
            #     try:
            #         data['title'] = u'Adicionar sistema'
            #         form = SistemaForm()
            #         form.adicionar()
            #         data['form'] = form
            #         return render(request, "adm_requerimiento/addsistema.html", data)
            #     except Exception as ex:
            #         pass
            #
            # elif action == 'editsistema':
            #     try:
            #         data['title'] = u'Editar Sistema'
            #         data['sistema'] = sistema = ReqSistema.objects.get(pk=request.GET['id'])
            #         initial = model_to_dict(sistema)
            #         form = SistemaForm(initial=initial)
            #         data['form'] = form
            #         return render(request, "adm_requerimiento/editsistema.html", data)
            #     except Exception as ex:
            #         pass
            #
            # elif action == 'deletesistema':
            #     try:
            #         data['title'] = u'Eliminar Sistema'
            #         data['sistema'] = ReqSistema.objects.get(pk=request.GET['id'])
            #         return render(request, "adm_requerimiento/deletesistema.html", data)
            #     except Exception as ex:
            #         pass
            #
            # elif action == 'tipoaccion':
            #     try:
            #         data['title'] = 'Tipo Acción'
            #         search = None
            #         ids = None
            #         if 's' in request.GET:
            #             search = request.GET['s'].strip()
            #             sistema = TipoAccion.objects.filter(status=True, nombre__icontains=search)
            #         else:
            #             sistema = TipoAccion.objects.filter(status=True)
            #         paging = MiPaginador(sistema, 25)
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
            #         data['page'] = page
            #         data['rangospaging'] = paging.rangos_paginado(p)
            #         data['tipoaccion'] = page.object_list
            #         data['search'] = search if search else ""
            #         data['ids'] = ids if ids else ""
            #         return render(request, "adm_requerimiento/tipoaccion.html", data)
            #     except Exception as ex:
            #         pass
            #
            # elif action == 'addtipoaccion':
            #     try:
            #         data['title'] = u'Adicionar Tipo Acción'
            #         form = TipoAccionForm()
            #         data['form'] = form
            #         return render(request, "adm_requerimiento/addtipoaccion.html", data)
            #     except Exception as ex:
            #         pass
            #
            # elif action == 'edittipoaccion':
            #     try:
            #         data['title'] = u'Editar Tipo Acción'
            #         data['tipoaccion'] = sistema = TipoAccion.objects.get(pk=request.GET['id'])
            #         form = TipoAccionForm(initial={
            #             'nombre': sistema.nombre,
            #         })
            #         data['form'] = form
            #         return render(request, "adm_requerimiento/edittipoaccion.html", data)
            #     except Exception as ex:
            #         pass
            #
            # elif action == 'deletetipoaccion':
            #     try:
            #         data['title'] = u'Eliminar Tipo Acción'
            #         data['tipoaccion'] = TipoAccion.objects.get(pk=request.GET['id'])
            #         return render(request, "adm_requerimiento/deletetipoaccion.html", data)
            #     except Exception as ex:
            #         pass

            if action == 'secuenciacapacitacion':
                try:
                    data['title'] = 'Secuencia Capacitación'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        sistema = SecuenciaCapacitacion.objects.filter(status=True, descripcion__icontains=search,
                                                                       secuencia__icontains=search,
                                                                       anio__icontains=search)
                    else:
                        sistema = SecuenciaCapacitacion.objects.filter(status=True)
                    paging = MiPaginador(sistema, 25)
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
                    data['secuenciacapacitacion'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_requerimiento/secuenciacapacitacion.html", data)
                except Exception as ex:
                    pass

            if action == 'addsecuenciacapacitacion':
                try:
                    data['title'] = u'Adicionar Secuencia Capacitación'
                    form = SecuenciaCapacitacionForm()
                    data['form'] = form
                    return render(request, "adm_requerimiento/addsecuenciacapacitacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'editanexoinforme':
                try:
                    data['title'] = u'Editar Anexo Informe'
                    data['anexo'] = anexo = AnexoInforme.objects.get(pk=int(request.GET['id']))
                    initial = model_to_dict(anexo)
                    form = AnexoInformeForm(initial=initial)
                    data['form'] = form
                    return render(request, "adm_requerimiento/editanexoinforme.html", data)
                except Exception as ex:
                    pass

            elif action == 'delanexoinforme':
                try:
                    data['title'] = u'Eliminar anexo informe'
                    data['anexo'] = AnexoInforme.objects.get(pk=request.GET['id'])
                    return render(request, "adm_requerimiento/delanexoinforme.html", data)
                except Exception as ex:
                    pass

            if action == 'editsecuenciacapacitacion':
                try:
                    data['title'] = u'Editar Secuencia Capacitación'
                    data['secuenciacapacitacion'] = secuencia = SecuenciaCapacitacion.objects.get(pk=request.GET['id'])
                    form = SecuenciaCapacitacionForm(initial={
                        'descripcion': secuencia.descripcion,
                        'anio': secuencia.anio,
                        'secuencia': secuencia.secuencia,
                        'vigente': secuencia.vigente,
                    })
                    data['form'] = form
                    return render(request, "adm_requerimiento/editsecuenciacapacitacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletesecuenciacapacitacion':
                try:
                    data['title'] = u'Eliminar Secuencia Capacitación'
                    data['secuenciacapacitacion'] = SecuenciaCapacitacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_requerimiento/deletesecuenciacapacitacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'opcionsistema':
                try:
                    data['title'] = 'Opciones Sistemas'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        opcion = OpcionSistema.objects.filter(status=True, descripcion__icontains=search,
                                                              modulo__nombre__icontains=search)
                    else:
                        opcion = OpcionSistema.objects.filter(status=True)
                    paging = MiPaginador(opcion, 25)
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
                    data['opcionsistema'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_requerimiento/opcionsistema.html", data)
                except Exception as ex:
                    pass
            #
            elif action == 'addopcionsistema':
                try:
                    data['title'] = u'Adicionar Opcion Sistema'
                    form = OpcionSistemaForm()
                    data['form'] = form
                    return render(request, "adm_requerimiento/addopcionsistema.html", data)
                except Exception as ex:
                    pass

            elif action == 'addanexoinforme':
                try:
                    data['title'] = u'Adicionar Anexo Informe'
                    data['id_informe'] = int(request.GET['id'])
                    form = AnexoInformeForm()
                    data['form'] = form
                    return render(request, "adm_requerimiento/addanexoinforme.html", data)
                except Exception as ex:
                    pass

            elif action == 'editopcionsistema':
                try:
                    data['title'] = u'Editar Opción Sistema'
                    data['opcionsistema'] = opcion = OpcionSistema.objects.get(pk=request.GET['id'])
                    form = OpcionSistemaForm(initial={
                        'descripcion': opcion.descripcion,

                    })
                    form.editar(opcion.modulo)
                    data['form'] = form
                    return render(request, "adm_requerimiento/editopcionsistema.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteopcionsistema':
                try:
                    data['title'] = u'Eliminar Opción Sistema'
                    data['opcionsistema'] = OpcionSistema.objects.get(pk=request.GET['id'])
                    return render(request, "adm_requerimiento/deleteopcionsistema.html", data)
                except Exception as ex:
                    pass

            elif action == 'buscarmodulo':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if s.__len__() == 1:
                        modulo = Modulo.objects.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=s[0]),
                                                       status=True).distinct()[:20]
                    else:
                        modulo = Modulo.objects.filter(Q(nombre__icontains=q) | Q(descripcion__icontains=s[0])).filter(
                            status=True).distinct()[:20]
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_reprhd()} for x in modulo]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass
            #
            # elif action == 'buscarsistema':
            #     try:
            #         q = request.GET['q'].upper().strip()
            #         s = q.split(" ")
            #
            #         if s.__len__() == 1:
            #             # activo = ActivoFijo.objects.filter(Q(codigogobierno__icontains=q) | Q(codigointerno__icontains=s[0]) | Q(serie__icontains=q),status=True, catalogo__equipoelectronico=True if tipo == 2 else False).distinct()[:20]
            #             sistema = ReqSistema.objects.filter(Q(nombre__icontains=q), status=True).distinct()[:20]
            #         else:
            #             sistema = ReqSistema.objects.filter(Q(nombre__icontains=q)).filter(status=True).distinct()[:20]
            #         data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_reprhd()} for x in sistema]}
            #         return JsonResponse(data)
            #     except Exception as ex:
            #         pass
            #
            # elif action == 'buscartipo':
            #     try:
            #         q = request.GET['q'].upper().strip()
            #         s = q.split(" ")
            #
            #         if s.__len__() == 1:
            #             # activo = ActivoFijo.objects.filter(Q(codigogobierno__icontains=q) | Q(codigointerno__icontains=s[0]) | Q(serie__icontains=q),status=True, catalogo__equipoelectronico=True if tipo == 2 else False).distinct()[:20]
            #             tipo = TipoAccion.objects.filter(Q(nombre__icontains=q), status=True).distinct()[:20]
            #         else:
            #             tipo = TipoAccion.objects.filter(Q(nombre__icontains=q)).filter(status=True).distinct()[:20]
            #         data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_reprhd()} for x in tipo]}
            #         return JsonResponse(data)
            #     except Exception as ex:
            #         pass
            #
            elif action == 'buscarelaborado':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if s.__len__() == 1:
                        # activo = ActivoFijo.objects.filter(Q(codigogobierno__icontains=q) | Q(codigointerno__icontains=s[0]) | Q(serie__icontains=q),status=True, catalogo__equipoelectronico=True if tipo == 2 else False).distinct()[:20]
                        persona = Persona.objects.filter(
                            Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(cedula__icontains=q) | Q(
                                apellido2__icontains=q), status=True).distinct()[:20]
                    else:
                        persona = Persona.objects.filter(Q(status=True),
                                                               (Q(cedula__icontains=s[0]) | ((Q(
                                                                   nombres__icontains=s[0]) & Q(
                                                                   nombres__icontains=s[0])) |
                                                                                             (Q(apellido1__icontains=s[
                                                                                                 0]) & Q(
                                                                                                 apellido2__icontains=s[
                                                                                                     1]))) | (
                                                                        (Q(nombres__icontains=s[0]) & Q(
                                                                            nombres__icontains=s[
                                                                                1])) |
                                                                        (Q(apellido1__icontains=s[0]) & Q(
                                                                            apellido2__icontains=s[1]))))).distinct()[
                                  :20]
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_repr()} for x in persona]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'buscaropcion':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if s.__len__() == 1:
                        tipo = OpcionSistema.objects.filter(
                            Q(descripcion__icontains=q) | Q(modulo__nombre__icontains=q), status=True).distinct()[:20]
                    else:
                        tipo = OpcionSistema.objects.filter(
                            Q(descripcion__icontains=q) | Q(modulo__nombre__icontains=q)).filter(
                            status=True).distinct()[:20]
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_reprhd()} for x in tipo]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass
            #
            elif action == 'addcab':
                try:
                    data['title'] = u'Adicionar Capacitación'
                    form = CabCapacitacionForm()
                    data['form'] = form
                    return render(request, "adm_requerimiento/addcab.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcab':
                try:
                    data['title'] = u'Editar Capacitación'
                    data['capacitacion'] = opcion = CabCapacitacion.objects.get(pk=request.GET['id'])
                    form = CabCapacitacionForm(initial={
                        'departamento': opcion.departamento,
                        'seccion': opcion.seccion,
                        'fecha': opcion.fecha,
                        'antecedente': opcion.antecedente,
                        'tiposistema': opcion.tiposistema,
                        'tipocapacitacion': opcion.tipocapacitacion,
                        'horainicio': opcion.horainicio,
                        'horafin': opcion.horafin,
                        'elaborado': opcion.elaborado,
                        'verificado': opcion.verificado,
                        'aprobado': opcion.aprobado,

                    })
                    # form.editarelaborado(opcion.elaborado.persona_id)
                    # form.editarverificado(opcion.verificado)
                    data['form'] = form
                    return render(request, "adm_requerimiento/editcab.html", data)
                except Exception as ex:
                    pass

            elif action == 'subirarchivo':
                try:
                    data['title'] = u'Cargar Archivo Capacitación'
                    data['capacitacion'] = opcion = CabCapacitacion.objects.get(pk=request.GET['id'])
                    form = ArchivoCapacitacionForm()
                    data['form'] = form
                    return render(request, "adm_requerimiento/addarchivo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editelaborado':
                try:
                    data['title'] = u'Editar Elaborado'
                    data['capacitacion'] = opcion = CabCapacitacion.objects.get(pk=request.GET['id'])
                    form = ElaboradoForm(initial={})
                    form.editarelaborado(opcion.elaborado)
                    data['form'] = form
                    return render(request, "adm_requerimiento/editelaborado.html", data)
                except Exception as ex:
                    pass

            elif action == 'editverificado':
                try:
                    data['title'] = u'Editar Verificado'
                    data['capacitacion'] = opcion = CabCapacitacion.objects.get(pk=request.GET['id'])
                    form = VerificadoForm(initial={})
                    form.editarverificado(opcion.verificado)
                    data['form'] = form
                    return render(request, "adm_requerimiento/editarverificado.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletecab':
                try:
                    data['title'] = u'Eliminar Capacitación'
                    data['capacitacion'] = OpcionSistema.objects.get(pk=request.GET['id'])
                    return render(request, "adm_requerimiento/deletecab.html", data)
                except Exception as ex:
                    pass
            #
            elif action == 'viewcapacitacion':
                try:
                    data['title'] = 'Formularios de Capacitación'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(" ")

                        if len(ss) == 1:
                            sistema = CabCapacitacion.objects.filter(Q(elaborado__apellido1__icontains=search)|
                                                                     Q(elaborado__apellido2__icontains=search),
                                                                     status=True
                                                                     ).order_by('-id')
                        else:
                            sistema = CabCapacitacion.objects.filter(elaborado__apellido1__icontains=ss[0],
                                                                     elaborado__apellido2__icontains=ss[1],
                                                                     status=True
                                                                     ).order_by('-id')
                    else:
                        sistema = CabCapacitacion.objects.filter(status=True).order_by('-id')
                    paging = MiPaginador(sistema, 25)
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
                    data['capacitacion'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_requerimiento/viewcapacitacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'viewobservacion':
                try:
                    data['title'] = 'Observación'

                    search = None
                    ids = None
                    observa = None
                    observacion = DetObservacion.objects.filter(status=True, capacitacion=int(request.GET['id']))
                    if 'id' in request.GET:
                        data['observa'] = observa = CabCapacitacion.objects.get(pk=int(request.GET['id'])).pk
                    if 'observacion' in request.GET:
                        data['observa'] = observa = CabCapacitacion.objects.get(pk=int(request.GET['observacion'])).pk

                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        opcion = observacion.filter(Q(responsable__nombres__icontains=search) |
                                                    Q(responsable__apellido1__icontains=search) |
                                                    Q(responsable__apellido2__icontains=search) |
                                                    Q(observacion__icontains=search)
                                                    )
                    else:
                        if 'id' in request.GET:
                            opcion = DetObservacion.objects.filter(status=True,
                                                                   capacitacion=int(request.GET['id'])).order_by('-id')
                        if 'observacion' in request.GET:
                            opcion = DetObservacion.objects.filter(status=True,
                                                                   capacitacion=int(request.GET['observacion'])).order_by('-id')
                    paging = MiPaginador(opcion, 25)
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
                    data['observacion'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_requerimiento/viewobservacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addobservacion':
                try:
                    data['title'] = u'Adicionar Observación'
                    form = DetObservacionForm()
                    data['observaci'] = observaci = CabCapacitacion.objects.get(pk=int(request.GET['observacion']))
                    data['form'] = form
                    return render(request, "adm_requerimiento/addobservacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'editobservacion':
                try:
                    data['title'] = u'Editar Observación'
                    data['observacion'] = observacion = DetObservacion.objects.get(pk=request.GET['id'])
                    form = DetObservacionForm(initial={
                        'observacion': observacion.observacion,
                        'estado': observacion.estado,
                        'fecha': observacion.fecha,
                        'responsable': observacion.responsable,


                    })
                    # form.editarresponsable(observacion.responsable)
                    data['form'] = form
                    return render(request, "adm_requerimiento/editobservacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteobservacion':
                try:
                    data['title'] = u'Eliminar Observación'
                    data['observacion'] = DetObservacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_requerimiento/deleteobservacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'viewresponsable':
                try:
                    data['title'] = 'Responsable'

                    search = None
                    ids = None
                    observa = None
                    responsable = DetResponsable.objects.filter(status=True,capacitacion=int(request.GET['id']))
                    if 'id' in request.GET:
                        data['respon'] = observa = CabCapacitacion.objects.get(pk=int(request.GET['id'])).pk
                    if 'responsable' in request.GET:
                        data['respon'] = observa = CabCapacitacion.objects.get(pk=int(request.GET['responsable'])).pk

                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        opcion = responsable.filter(Q(responsable__nombres__icontains=search) |
                                                    Q(responsable__apellido1__icontains=search) |
                                                    Q(responsable__apellido2__icontains=search)
                                                    )
                    else:

                        if 'id' in request.GET:
                            opcion = DetResponsable.objects.filter(status=True, capacitacion=int(request.GET['id'])).order_by('-id')
                        if 'responsable' in request.GET:
                            opcion = DetResponsable.objects.filter(status=True,
                                                                   capacitacion=int(request.GET['responsable'])).order_by('-id')

                    paging = MiPaginador(opcion, 25)
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
                    data['responsable'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_requerimiento/viewresponsable.html", data)
                except Exception as ex:
                    pass

            elif action == 'addresponsable':
                try:
                    data['title'] = u'Adicionar Responsables'
                    data['respon'] = respon = CabCapacitacion.objects.get(pk=int(request.GET['responsable']))
                    form = DetResponsableForm()
                    data['form'] = form
                    return render(request, "adm_requerimiento/addresponsable.html", data)
                except Exception as ex:
                    pass

            elif action == 'editresponsable':
                try:
                    data['title'] = u'Editar Responsable'
                    data['responsable'] = responsable = DetResponsable.objects.get(pk=request.GET['id'])
                    form = DetResponsableForm(initial={
                        'responsable': responsable.responsable,
                    })
                    # form.editarresponsable(responsable.responsable)
                    data['form'] = form
                    return render(request, "adm_requerimiento/editresponsable.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteresponsable':
                try:
                    data['title'] = u'Eliminar Responsable'
                    data['responsable'] = DetResponsable.objects.get(pk=request.GET['id'])
                    return render(request, "adm_requerimiento/deleteresponsable.html", data)
                except Exception as ex:
                    pass

            elif action == 'viewparticipante':
                try:
                    data['title'] = 'Participante'

                    search = None
                    ids = None
                    observa = None
                    participante = DetParticipante.objects.filter(status=True, capacitacion=int(request.GET['id']) )
                    if 'id' in request.GET:
                        data['partici'] = observa = CabCapacitacion.objects.get(pk=int(request.GET['id'])).pk
                    if 'participante' in request.GET:
                        data['partici'] = observa = CabCapacitacion.objects.get(pk=int(request.GET['participante'])).pk

                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        opcion = participante.filter(Q(participante__nombres__icontains=search) |
                                                    Q(participante__apellido1__icontains=search) |
                                                    Q(participante__apellido2__icontains=search)
                                                    )
                    else:

                        if 'id' in request.GET:
                            opcion = DetParticipante.objects.filter(status=True,
                                                                    capacitacion=int(request.GET['id'])).order_by('-id')
                        if 'participante' in request.GET:
                            opcion = DetParticipante.objects.filter(status=True,
                                                                    capacitacion=int(request.GET['participante'])).order_by('-id')

                        # opcion = DetParticipante.objects.filter(status=True,capacitacion=int(request.GET['participante']))
                    paging = MiPaginador(opcion, 25)
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
                    data['participante'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_requerimiento/viewparticipante.html", data)
                except Exception as ex:
                    pass

            elif action == 'addparticipante':
                try:
                    data['title'] = u'Adicionar Participante'
                    data['partici'] = respon = CabCapacitacion.objects.get(pk=int(request.GET['participante']))
                    form = DetParticipanteForm()
                    data['form'] = form
                    return render(request, "adm_requerimiento/addparticipante.html", data)
                except Exception as ex:
                    pass

            elif action == 'editparticipante':
                try:
                    data['title'] = u'Editar Participante'
                    data['participante'] = participante = DetParticipante.objects.get(pk=request.GET['id'])
                    form = DetParticipanteForm(initial={

                    })
                    form.editarparticipante(participante.participante)
                    data['form'] = form
                    return render(request, "adm_requerimiento/editparticipante.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteparticipante':
                try:
                    data['title'] = u'Eliminar Participante'
                    data['participante'] = DetParticipante.objects.get(pk=request.GET['id'])
                    return render(request, "adm_requerimiento/deleteparticipante.html", data)
                except Exception as ex:
                    pass

            elif action == 'reportepdf':
                try:
                    data['fechahoy'] = datetime.now().date()
                    data['solicitud'] = solicitud = CabCapacitacion.objects.get(status=True, pk=int(request.GET['id']))
                    data['participante'] = participante = DetParticipante.objects.filter(status=True,
                                                                                         capacitacion=int(solicitud.pk))
                    data['responsable'] = responsable = DetResponsable.objects.filter(status=True,
                                                                                      capacitacion=int(solicitud.pk))
                    data['observacion'] = observacion = DetObservacion.objects.filter(status=True,
                                                                                      capacitacion=int(solicitud.pk))
                    data['opcion'] = opcion = DetOpcion.objects.filter(status=True, capacitacion=int(solicitud.pk))
                    # data['tipocapacitacion'] = TIPO_CAPACITACION
                    return conviert_html_to_pdf(
                        'adm_requerimiento/reportepdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'viewopciones':
                try:
                    data['title'] = 'Opciones'

                    search = None
                    ids = None
                    observa = None
                    opciones = DetOpcion.objects.filter(status=True, capacitacion=int(request.GET['id']))
                    if 'id' in request.GET:
                        data['opcion'] = observa = CabCapacitacion.objects.get(pk=int(request.GET['id'])).pk
                    if 'opciones' in request.GET:
                        data['opcion'] = observa = CabCapacitacion.objects.get(pk=int(request.GET['opciones'])).pk

                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        opcion = opciones.filter(Q(responsable__nombres__icontains=search) |
                                                    Q(responsable__apellido1__icontains=search) |
                                                    Q(responsable__apellido2__icontains=search) |
                                                    Q(modulo__nombre__icontains=search)|
                                                    Q(observacion__icontains=search)
                                                    )
                    else:

                        if 'id' in request.GET:
                            opcion = DetOpcion.objects.filter(status=True, capacitacion=int(request.GET['id'])).order_by('-id')
                        if 'opciones' in request.GET:
                            opcion = DetOpcion.objects.filter(status=True, capacitacion=int(request.GET['opciones'])).order_by('-id')

                    paging = MiPaginador(opcion, 25)
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
                    data['opciones'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_requerimiento/viewopciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'addopcion':
                try:
                    data['title'] = u'Adicionar Opciones'
                    data['opcion'] = respon = CabCapacitacion.objects.get(pk=int(request.GET['opciones']))
                    form = DetOpcionForm()
                    data['form'] = form
                    return render(request, "adm_requerimiento/addopciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'editopcion':
                try:
                    data['title'] = u'Editar Opciones'
                    data['opcion'] = opciones = DetOpcion.objects.get(pk=request.GET['id'])
                    form = DetOpcionForm(initial={
                        'responsable':opciones.responsable,
                        'modulo': opciones.modulo,
                        'observacion':opciones.observacion,
                    })
                    # form.editaropcion(opciones.opcion)
                    # form.editarresponsable(opciones.responsable)
                    # form.editarmodulo(opciones.modulo)
                    data['form'] = form
                    return render(request, "adm_requerimiento/editopciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteopcion':
                try:
                    data['title'] = u'Eliminar Opciones'
                    data['opcion'] = DetOpcion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_requerimiento/deleteopciones.html", data)
                except Exception as ex:
                    pass

            # --- MANTENIMIENTO DE MODULOS
            # --- VISTA DE TABLA DE MODULOS
            # -- VISTA LISTA MODULOS
            elif action == 'modulos':
                try:
                    data['title'] = 'Módulos'
                    search = None
                    ids = None
                    modulo = Modulo.objects.filter()
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        modulo = modulo.filter(nombre__icontains=search)
                    if not persona.usuario.is_staff:
                        modulo = modulo.filter(status=True)
                    paging = MiPaginador(modulo, 25)
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
                    data['modulos'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_requerimiento/modulos.html", data)
                except Exception as ex:
                    pass
            # --- VISTA NUEVO MODULO
            elif action == 'addmodulo':
                try:
                    data['title'] = u'Adicionar Módulo'
                    form = ModuloForm()
                    # form.adicionar()
                    data['form'] = form
                    return render(request, "adm_requerimiento/addmodulo.html", data)
                except Exception as ex:
                    pass
            # --- VISTA EDITAR MODULO
            elif action == 'editmodulo':
                try:
                    data['title'] = u'Editar Módulo'
                    data['modulo'] = modulo = Modulo.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(modulo)
                    form = ModuloForm(initial=initial)
                    data['form'] = form
                    return render(request, "adm_requerimiento/editmodulo.html", data)
                except Exception as ex:
                    pass
            # --- VISTA INACTIVAR MODULO
            elif action == 'inactivemodulo':
                try:
                    data['title'] = u'Inactivar Módulo'
                    data['modulo'] = Modulo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_requerimiento/inactivatemodulo.html", data)
                except Exception as ex:
                    pass
            # --- VISTA ACTIVAR MODULO
            elif action == 'activemodulo':
                try:
                    data['title'] = u'Activar Módulo'
                    data['modulo'] = Modulo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_requerimiento/activemodulo.html", data)
                except Exception as ex:
                    pass
            # --- VISTA INACTIVAR REQUERIMIENTO
            elif action == 'inactivehistoria':
                try:
                    data['title'] = u'Inactivar Requerimiento'
                    data['historia'] = ReqHistoria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_requerimiento/inactivatehistoria.html", data)
                except Exception as ex:
                    pass
            # --- VISTA ACTIVAR REQUERIMIENTO
            elif action == 'activehistoria':
                try:
                    data['title'] = u'Activar Requerimiento'
                    data['historia'] = ReqHistoria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_requerimiento/activatehistoria.html", data)
                except Exception as ex:
                    pass
            # --- VISTA AGREGAR REQUERIMIENTO
            elif action == 'addhistoria':
                try:
                    data['title'] = u'Adicionar Requerimiento'
                    form = ReqHistoriaForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, "adm_requerimiento/addhistoria.html", data)
                except Exception as ex:
                    pass
            # --- VISTA EDITAR REQUERIMIENTO
            elif action == 'edithistoria':
                try:
                    return_to = None
                    if 'return' in request.GET:
                        return_to = request.GET['return']
                    data['return'] = return_to
                    data['title'] = u'Editar Requerimiento'
                    data['historia'] = historia = ReqHistoria.objects.get(pk=request.GET['id'])
                    distributivo = historia.solicita.distributivopersona_set.filter(status=True)[0]
                    form = ReqHistoriaForm(
                        initial={'modulo': historia.modulo,
                                 'prioridad': historia.prioridad,
                                 'asunto': historia.asunto,
                                 'cuerpo': historia.cuerpo,
                                 })
                    form.editar(distributivo)
                    data['form'] = form
                    return render(request, "adm_requerimiento/edithistoria.html", data)
                except Exception as ex:
                    pass
            # --- VISTA LISTA ACTIVIDAD
            elif action == 'actividades':
                try:
                    data['title'] = 'Actividades'
                    search = None
                    ids = None
                    actividad = ReqActividad.objects.filter()
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        actividad = actividad.filter(nombre__icontains=search)
                    if not persona.usuario.is_staff:
                        actividad = actividad.filter(status=True)
                    paging = MiPaginador(actividad, 25)
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
                    data['actividades'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_requerimiento/actividades.html", data)
                except Exception as ex:
                    pass
            # --- VISTA INACTIVAR ACTIVIDAD
            elif action == 'inactiveactividad':
                try:
                    data['title'] = u'Inactivar Actividad'
                    data['actividad'] = ReqActividad.objects.get(pk=request.GET['id'])
                    return render(request, "adm_requerimiento/inactivateactividad.html", data)
                except Exception as ex:
                    pass
            # --- VISTA ACTIVAR ACTIVIDAD
            elif action == 'activeactividad':
                try:
                    data['title'] = u'Activar Actividad'
                    data['actividad'] = ReqActividad.objects.get(pk=request.GET['id'])
                    return render(request, "adm_requerimiento/activateactividad.html", data)
                except Exception as ex:
                    pass
            # --- VISTA AGREGAR ACTIVIDAD
            elif action == 'addactividad':
                try:
                    data['title'] = u'Adicionar Actividad'
                    form = ReqActividadForm()
                    # form.adicionar()
                    data['form'] = form
                    return render(request, "adm_requerimiento/addactividad.html", data)
                except Exception as ex:
                    pass
            # --- VISTA EDITAR ACTIVIDAD
            elif action == 'editactividad':
                try:
                    data['title'] = u'Editar Actividad'
                    data['actividad'] = actividad = ReqActividad.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(actividad)
                    form = ReqActividadForm(initial=initial)
                    data['form'] = form
                    return render(request, "adm_requerimiento/editactividad.html", data)
                except Exception as ex:
                    pass
            # --- VISTA LISTA PRIORIDAD
            elif action == 'prioridades':
                try:
                    data['title'] = 'Prioridades'
                    search = None
                    ids = None
                    prioridad = ReqPrioridad.objects.filter().order_by('codigo')
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        prioridad = prioridad.filter(nombre__icontains=search)
                    if not persona.usuario.is_staff:
                        prioridad = prioridad.filter(status=True)
                    paging = MiPaginador(prioridad, 25)
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
                    data['listamateriales'] = page.object_list
                    return render(request, "adm_hdincidente/view_departamento.html", data)
                except Exception as ex:
                    pass
            # --- VISTA AGREGAR PRIORIDAD
            elif action == 'addprioridad':
                try:
                    data['title'] = u'Adicionar Prioridad'
                    form = PrioridadForm()
                    data['form'] = form
                    return render(request, "adm_requerimiento/addprioridad.html", data)
                except Exception as ex:
                    pass
            # --- VISTA EDITAR PRIORIDAD
            elif action == 'editprioridad':
                try:
                    data['title'] = u'Editar Prioridad'
                    data['prioridad'] = prioridad = ReqPrioridad.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(prioridad)
                    form = PrioridadForm(initial=initial)
                    data['form'] = form
                    return render(request, "adm_requerimiento/editprioridad.html", data)
                except Exception as ex:
                    pass
            # --- VISTA INACTIVAR PRIORIDAD
            elif action == 'inactiveprioridad':
                try:
                    data['title'] = u'Inactivar Prioridad'
                    data['prioridad'] = ReqPrioridad.objects.get(pk=request.GET['id'])
                    return render(request, "adm_requerimiento/inactivateprioridad.html", data)
                except Exception as ex:
                    pass
            # --- VISTA ACTIVAR PRIORIDAD
            elif action == 'activeprioridad':
                try:
                    data['title'] = u'Activar Prioridad'
                    data['prioridad'] = ReqPrioridad.objects.get(pk=request.GET['id'])
                    return render(request, "adm_requerimiento/activateprioridad.html", data)
                except Exception as ex:
                    pass
            # --- VISTA CABECERA Y DETALLE DEL REQUERIMIENTO
            elif action == 'detalle':
                try:
                    data['title'] = u'Registro de Actividades'
                    data['historia'] = historia = ReqHistoria.objects.get(pk=request.GET['id'])
                    detalles = ReqHistoriaActividad.objects.filter(historia=historia).order_by('actividad', 'fechainicio')
                    if not persona.usuario.is_staff:
                        detalles = detalles.filter(status=True)
                    data['detalles'] = detalles
                    data['form2'] = ReqHistoriaActividadForm()
                    return render(request, "adm_requerimiento/detalle.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
            # --- AJAX CARGA EL DATATABLE DEL DETALLE DE LAS ACTIVIDADES
            elif action == 'load_data_detalle':
                try:
                    idc = int(request.GET['idc']) if request.GET['idc'] else 0
                    txt_filter = request.GET['sSearch'] if request.GET['sSearch'] else ''
                    limit = int(request.GET['iDisplayLength']) if request.GET['iDisplayLength'] else 25
                    offset = int(request.GET['iDisplayStart']) if request.GET['iDisplayStart'] else 0

                    if idc == 0:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

                    historia = ReqHistoria.objects.get(pk=idc)
                    actividaddet = ReqHistoriaActividad.objects.filter(historia=historia)
                    isView = 1
                    if not persona.usuario.is_staff:
                        actividaddet = actividaddet.filter(status=True)
                        isView = 0
                    if txt_filter:
                        actividaddet = actividaddet.filter(Q(responsable__nombres__icontains=txt_filter) |
                                                           Q(responsable__apellido1__icontains=txt_filter) |
                                                           Q(responsable__apellido2__icontains=txt_filter) |
                                                           Q(responsable__cedula__icontains=txt_filter) |
                                                           Q(responsable__pasaporte__icontains=txt_filter)
                                                           )
                    tCount = actividaddet.count()
                    if offset == 0:
                        actividaddetRows = actividaddet[offset:limit]
                    elif offset == limit:
                        actividaddetRows = actividaddet[offset:tCount]
                    else:
                        actividaddetRows = actividaddet[offset:offset+limit]
                    aaData = []
                    for dataRow in actividaddetRows:
                        persona = u'%s %s %s' % (dataRow.responsable.apellido1, dataRow.responsable.apellido2, dataRow.responsable.nombres)

                        aaData.append([persona,
                                       dataRow.actividad.nombre,
                                       dataRow.descripcion,
                                       dataRow.fechainicio.strftime("%d-%m-%Y"),
                                       dataRow.fechafin.strftime("%d-%m-%Y"),
                                       dataRow.estado,
                                       dataRow.status,
                                       {
                                           'idc': historia.id,
                                           'idd': dataRow.id,
                                           'state': dataRow.estado,
                                           'responsable': persona,
                                           'status': dataRow.status,
                                       }])
                    return JsonResponse(
                        {"result": "ok", "mensaje": u"Cargo los datos.", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
            # --- VISTA DE SEGUIMIENTO DE REQUERIMIENTOS
            elif action == 'seguimientohistoria':
                try:
                    data['title'] = 'Seguimiento de Requerimientos'
                    search = None
                    ids = None
                    historia = ReqHistoria.objects.filter(status=True)
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        historia = historia.filter(Q(responsable__nombres__icontains=search) |
                                                   Q(responsable__apellido1__icontains=search) |
                                                   Q(responsable__apellido2__icontains=search) |
                                                   Q(responsable__cedula__icontains=search) |
                                                   Q(responsable__pasaporte__icontains=search) |
                                                   Q(modulo__nombre__icontains=search) |
                                                   Q(solicita__nombres__icontains=search) |
                                                   Q(solicita__apellido1__icontains=search) |
                                                   Q(solicita__apellido2__icontains=search) |
                                                   Q(solicita__cedula__icontains=search) |
                                                   Q(solicita__pasaporte__icontains=search) |
                                                   Q(asunto__icontains=search))
                    paging = MiPaginador(historia, 25)
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
                    data['historias'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_requerimiento/seguimientohistoria.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
            # --- VISTA DE SEGUIMIENTO DE ACTIVIDADES DEL REQUERIMIENTO
            elif action == 'seguimientoactividad':
                try:
                    data['title'] = 'Seguimiento de Actividad'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        actividad = ReqHistoriaActividad.objects.filter(status=True, nombre__icontains=search).order_by('historia')
                    else:
                        actividad = ReqHistoriaActividad.objects.filter(status=True).order_by('historia')
                    paging = MiPaginador(actividad, 25)
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
                    data['actividades'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_requerimiento/seguimientoactividades.html", data)
                except Exception as ex:
                    pass

            elif action == 'informes':
                try:
                    data['title'] = 'INFORMES TICS'
                    departamento = responsable = 0
                    fechadesde = fechahasta = ''
                    filtros, search, url_vars = Q(status=True), request.GET.get('s', ''), ''
                    ids = None
                    if search:
                        filtros = filtros & (Q(objetivo__icontains=search)|
                                           Q(codigo__icontains=search)|
                                           Q(departamento__nombre__icontains=search)|
                                           Q(responsables__apellido1__icontains=search)|
                                           Q(responsables__apellido2__icontains=search)|
                                           Q(responsables__nombres__icontains=search)
                                           )
                        data['s'] = f"{search}"
                        url_vars += f"&s={search}"

                    if 'dep' in request.GET:
                        departamento = int(request.GET['dep'])
                    if 'resp' in request.GET:
                        responsable = int(request.GET['resp'])
                    if 'fd' in request.GET:
                        fechadesde = convertir_fecha(request.GET['fd'])
                    if 'fh' in request.GET:
                        fechahasta = convertir_fecha(request.GET['fh'])

                    if departamento > 0:
                        data['dep'] = departamento
                        filtros = filtros & Q(departamento__id=departamento)
                        url_vars += "&dep={}".format(departamento)

                    if responsable > 0:
                        data['resp'] = responsable
                        filtros = filtros & Q(responsables__id=responsable)
                        url_vars += "&resp={}".format(responsable)

                    if fechadesde and fechahasta:
                        data['fd'] = request.GET['fd']
                        data['fh'] = request.GET['fh']
                        filtros = filtros & Q(fecha__gte=fechadesde, fecha__lt=fechahasta )
                        url_vars += "&fd={}".format(fechadesde)
                        url_vars += "&fh={}".format(fechahasta)

                    informes = Informes.objects.filter(filtros).order_by('-fecha').distinct()

                    paging = MiPaginador(informes, 25)
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
                    data['informes'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['url_vars'] = url_vars
                    data['list_departamentos'] = list_departamentos = Informes.objects.values_list('departamento_id', 'departamento__nombre').filter(status=True).distinct().exclude(departamento=None).order_by('departamento_id')
                    data['list_responsables'] = list_responsables = Informes.objects.values_list('responsables__id', 'responsables__nombres', 'responsables__apellido1', 'responsables__apellido2').filter(status=True).distinct().exclude(responsables=None).order_by('responsables__apellido1')
                    return render(request, "adm_requerimiento/informes.html", data)
                except Exception as ex:
                    pass

            elif action == 'anexos':
                try:
                    data['title'] = 'ANEXOS INFORMES'
                    data['informe'] = informe = Informes.objects.get(pk=int(encrypt(request.GET['id'])))
                    search = None
                    anexos = AnexoInforme.objects.filter(status=True, informe= informe)
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        anexos = anexos.filter(Q(descripcion__icontains=search))
                    paging = MiPaginador(anexos, 25)
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
                    data['anexos'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_requerimiento/anexos.html", data)
                except Exception as ex:
                    pass

            elif action == 'addinforme':
                try:
                    data['title'] = u'Adicionar Prioridad'
                    form = InformeForm()
                    data['form'] = form
                    return render(request, "adm_requerimiento/addinforme.html", data)
                except Exception as ex:
                    pass

            elif action == 'editinforme':
                try:
                    data['title'] = u'Editar Informe'
                    data['informe'] = informe = Informes.objects.get(pk=int(encrypt(request.GET['id'])))
                    initial = model_to_dict(informe)
                    form = InformeForm(initial=initial)
                    data['form'] = form
                    return render(request, "adm_requerimiento/editinforme.html", data)
                except Exception as ex:
                    pass

            elif action == 'delinforme':
                try:
                    data['title'] = u'Eliminar informe'
                    data['informe'] = Informes.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_requerimiento/delinforme.html", data)
                except Exception as ex:
                    pass

            elif action == 'buscarpersona':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if len(s) == 1:
                        per = Persona.objects.filter((Q(distributivopersona__isnull=False) | Q(profesor__isnull=False)),
                                                     (Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(cedula__icontains=q) | Q(
                                                         apellido2__icontains=q) | Q(cedula__contains=q)),
                                                     Q(status=True)).distinct()[:15]
                    elif len(s) == 2:
                        per = Persona.objects.filter((Q(distributivopersona__isnull=False) | Q(profesor__isnull=False)),
                                                     (Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) | (
                                                             Q(nombres__icontains=s[0]) & Q(
                                                         nombres__icontains=s[1])) | (
                                                             Q(nombres__icontains=s[0]) & Q(
                                                         apellido1__contains=s[1]))).filter(status=True).distinct()[
                              :15]
                    else:
                        per = Persona.objects.filter((Q(distributivopersona__isnull=False) | Q(profesor__isnull=False)),
                                                     (Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(
                                                         apellido2__contains=s[2])) | (Q(nombres__contains=s[0]) & Q(
                                                         nombres__contains=s[1]) & Q(apellido1__contains=s[2]))).filter(
                            status=True).distinct()[:15]

                    data = {"result": "ok",
                            "results": [{"id": x.id, "name": "{} - {}".format(x.cedula, x.nombre_completo())}
                                        for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'reporte_bitacora_excel':
                try:
                    fechadesde = convertir_fecha(request.GET['fecha_desde'])
                    fechahasta = convertir_fecha(request.GET['fecha_hasta'])
                    tipo_actividad = int(request.GET['tipo_actividad'])
                    __author__ = 'Unemi'
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Hoja1')
                    ws.write_merge(0, 0, 0, 12, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=bitacora' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"TITULO", 0),
                        (u"DEPARTAMENTO", 6000),
                        (u"FECHA", 6000),
                        (u"PERSONA", 6000),
                        (u"DESCRIPCIÓN", 6000),
                        (u"LINK", 6000),
                        (u"TIPO SISTEMA", 6000),
                        (u"DEPARTAMENTO SOLICITA", 6500),
                        (u"TIPO ACTIVIDAD", 6000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    bitacoras = BitacoraActividadDiaria.objects.filter(status=True,fecha__date__gte=fechadesde,fecha__date__lte=fechahasta)
                    if tipo_actividad > 0:
                        bitacoras = bitacoras.filter(tipoactividad=tipo_actividad)
                    row_num = 4
                    for r in bitacoras:
                        campo1 = u"%s"% r.titulo
                        campo2 = u"%s"% r.departamento.nombre if r.departamento else 'SIN DEPARTAMENTO'
                        campo3 = u"%s"% r.fecha
                        campo4 = u"%s"% r.persona
                        campo5 = u"%s"% r.descripcion
                        campo6 = u"%s"% r.link
                        campo7 = u"%s"% r.get_tiposistema_display()
                        campo8 = u"%s"% r.departamento_requiriente.nombre if r.departamento_requiriente else 'SIN DEPARTAMENTO REQUIRIENTE'
                        campo9 = u"%s"% r.get_tipoactividad_display() if r.tipoactividad else 'SIN TIPO'
                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        ws.write(row_num, 6, campo7, font_style2)
                        ws.write(row_num, 7, campo8, font_style2)
                        ws.write(row_num, 8, campo9, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporte_bitacora_pdf':
                try:
                    data['fechadesde']= fechadesde = convertir_fecha(request.GET['fecha_desde'])
                    data['fechahasta']= fechahasta = convertir_fecha(request.GET['fecha_hasta'])
                    tipo_actividad = int(request.GET['tipo_actividad'])
                    bitacoras = BitacoraActividadDiaria.objects.filter(status=True, fecha__date__gte=fechadesde, fecha__date__lte=fechahasta)
                    if tipo_actividad > 0:
                        bitacoras = bitacoras.filter(tipoactividad=tipo_actividad)
                    data['bitacoras'] = bitacoras
                    return conviert_html_to_pdf(
                        'adm_requerimiento/reporte_bitacora_pdf.html',
                        {
                            'pagesize': 'a4 landscape',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'reporte_informes':
                try:
                    fechadesde = request.GET['inicio']
                    fechahasta = request.GET['fin']
                    __author__ = 'Unemi'
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Hoja1')
                    ws.write_merge(0, 0, 0, 12, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=informes' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"Fecha", 3000),
                        (u"Código", 5000),
                        (u"Departamento", 6000),
                        (u"Responsables", 6000),
                        (u"Objetivo", 6000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    informes = Informes.objects.filter(status=True,fecha__gte=fechadesde, fecha__lte=fechahasta)
                    row_num = 4
                    for r in informes:
                        responsables = ''
                        for idx, res in enumerate(r.responsables.all(), start=1):
                            if idx > 1 and idx < len(responsables):
                                responsables+=', '
                            responsables += f'{res}'
                        ws.write(row_num, 0, r.fecha.strftime('%d-%m-%Y'), font_style2)
                        ws.write(row_num, 1, r.codigo, font_style2)
                        ws.write(row_num, 2, str(r.departamento), font_style2)
                        ws.write(row_num, 3, responsables, font_style2)
                        ws.write(row_num, 4, r.objetivo, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        # --- VISTA HISTORIA DE REQUERIMIENTOS
        else:
            try:
                search = None
                ids = None
                historias = ReqHistoria.objects.filter(status=True)
                if not persona.usuario.is_staff:
                    historias = historias.filter(status=True)
                if 's' in request.GET:
                    search = request.GET['s']
                    ss = search.split(' ')
                    while '' in ss:
                        ss.remove('')
                    if len(ss) == 1:
                        historias = historias.filter(Q(responsable__nombres__icontains=search) |
                                                     Q(responsable__apellido1__icontains=search) |
                                                     Q(responsable__apellido2__icontains=search) |
                                                     Q(responsable__cedula__icontains=search) |
                                                     Q(responsable__pasaporte__icontains=search) |
                                                     Q(solicita__nombres__icontains=search) |
                                                     Q(solicita__apellido1__icontains=search) |
                                                     Q(solicita__apellido2__icontains=search) |
                                                     Q(solicita__cedula__icontains=search) |
                                                     Q(solicita__pasaporte__icontains=search) |
                                                     Q(asunto__icontains=search)
                                                     )
                    else:
                        historias = historias.filter(Q(responsable__apellido1__icontains=ss[0]) |
                                                     Q(responsable__apellido2__icontains=ss[1]) |
                                                     Q(responsable__cedula__icontains=ss[0]) |
                                                     Q(responsable__cedula__icontains=ss[1]) |
                                                     Q(responsable__pasaporte__icontains=ss[0]) |
                                                     Q(responsable__pasaporte__icontains=ss[1]) |
                                                     Q(solicita__apellido1__icontains=ss[0]) |
                                                     Q(solicita__apellido2__icontains=ss[1]) |
                                                     Q(solicita__cedula__icontains=ss[0]) |
                                                     Q(solicita__cedula__icontains=ss[1]) |
                                                     Q(solicita__pasaporte__icontains=ss[0]) |
                                                     Q(solicita__pasaporte__icontains=ss[1]) |
                                                     Q(asunto__icontains=ss[0]) |
                                                     Q(asunto__icontains=ss[1]))

                elif 'id' in request.GET:
                    ids = request.GET['id']
                    historias = historias.filter(id=ids)
                paging = MiPaginador(historias, 20)
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
                data['historias'] = page.object_list
                data['form2'] = ResponsableForm()
                return render(request, "adm_requerimiento/view.html", data)
            except Exception as ex:
                pass

            #
            #
            #
            # elif action == 'deldetalle':
            #     try:
            #         data['title'] = u'Eliminar Actividad'
            #         data['actividaddet'] = ReqHistoriaActividad.objects.get(id=int(request.GET['idd']))
            #         return render(request, "adm_requerimiento/deldetalle.html", data)
            #     except Exception as ex:
            #         pass

            return HttpResponseRedirect(request.path)


def secuencia_capacitacion(conf):
    reg = CabCapacitacion.objects.filter(status=True, confsecuencia=conf).aggregate(secue=Max('secuencia') + 1)
    if reg['secue'] is None:
        secuencia = SecuenciaCapacitacion.objects.get(status=True, vigente=True).secuencia
    else:
        secuencia = reg['secue']
    return secuencia
