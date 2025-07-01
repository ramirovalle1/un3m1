# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import DatosInstitucionForm, DatosGeneralForm, ComponentesForm, ItinerariosForm, ConvenioForm, \
    DatosSustantivaForm, RequisitoIngresoForm, MicrocurricularForm, ContenidoForm, ComponenteForm, \
    DatosInvestigacionForm, DatosComponenteForm, DatosInfraestructuraForm, LaboratoriosForm, PersonalForm
from sga.funciones import MiPaginador, log
from sga.models import RedisenoCarrera, TituloInstitucion, Profesor, CarreraRedisenoCarrera, IntegarntesRedisenoCarrera, \
    CarrerasRediseno, InstitucionEducacionSuperior, ComponentesRedisenoCarrera, ItinerariosRedisenoCarrera, \
    ConveniosRedisenoCarrera, OpcionesAprobacionRedisenoCarrera, RequisitoIngresoRedisenoCarrera, \
    MicrocurricularRedisenoCarrera, ContenidoMicrocurricularRedisenoCarrera, ComponenteMicrocurricularRedisenoCarrera, \
    LaboratoriosRedisenoCarrera, PersonalAcademicoRedisenoCarrera


@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'datosinstitucion':
            try:
                f = DatosInstitucionForm(request.POST)
                if f.is_valid():
                    t = TituloInstitucion.objects.filter(status=True)[0]
                    if int(request.POST['id']) == 0:
                        r = RedisenoCarrera(nombreinstitucion = t.nombre,
                                            codigoiess = t.codigo,
                                            categoriaies = f.cleaned_data['categoriaies'],
                                            tipofinanciamiento = f.cleaned_data['tipofinanciamiento'],
                                            siglas = t.nombrecomercial,
                                            mision = f.cleaned_data['mision'],
                                            vision = f.cleaned_data['vision'],
                                            direccion = t.direccion,
                                            rector = f.cleaned_data['rector'],
                                            extrector = f.cleaned_data['extrector'],
                                            decano = f.cleaned_data['decano'],
                                            telefonoinstitucional = t.telefono,
                                            extdecano = f.cleaned_data['extdecano'])
                        r.save(request)
                        log(u'Insert datos institución: %s' % r, request, "add")
                    else:
                        r = RedisenoCarrera.objects.get(pk=int(request.POST['id']))
                        r.nombreinstitucion = t.nombre
                        r.codigoiess = t.codigo
                        r.categoriaies = f.cleaned_data['categoriaies']
                        r.tipofinanciamiento = f.cleaned_data['tipofinanciamiento']
                        r.siglas = t.nombrecomercial
                        r.mision = f.cleaned_data['mision']
                        r.vision = f.cleaned_data['vision']
                        r.direccion = f.cleaned_data['direccion']
                        r.rector = f.cleaned_data['rector']
                        r.extrector = f.cleaned_data['extrector']
                        r.decano = f.cleaned_data['decano']
                        r.extdecano = f.cleaned_data['extdecano']
                        r.telefonoinstitucional = t.telefono
                        r.save(request)
                        log(u'Modifico datos institución: %s' % r, request, "edit")
                    return JsonResponse({"result": "ok", "id": r.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})


        if action == 'datosgenerales':
            try:
                f = DatosGeneralForm(request.POST)
                if f.is_valid():
                    r = RedisenoCarrera.objects.get(pk=int(request.POST['id']))
                    r.tipotramite = f.cleaned_data['tipotramite']
                    r.codigosniese = f.cleaned_data['codigosniese']
                    r.proyectoinnovador = f.cleaned_data['proyectoinnovador']
                    r.tipoformacion = f.cleaned_data['tipoformacion']
                    r.modalidad = f.cleaned_data['modalidad']
                    r.descripcionmodalidad = f.cleaned_data['descripcionmodalidad']
                    r.proyectored = f.cleaned_data['proyectored']
                    r.campoamplio = f.cleaned_data['campoamplio']
                    r.campoespecifico = f.cleaned_data['campoespecifico']
                    r.campodetallado = f.cleaned_data['campodetallado']
                    r.carreraprogramama = f.cleaned_data['carreraprogramama']
                    r.titulacion = f.cleaned_data['titulacion']
                    r.numeroperiodosordinario = f.cleaned_data['numeroperiodosordinario']
                    r.numerosemanaordinario = f.cleaned_data['numerosemanaordinario']
                    r.numeroperiodosextraordinario = f.cleaned_data['numeroperiodosextraordinario']
                    r.numerosemanaextraordinario = f.cleaned_data['numerosemanaextraordinario']
                    r.numeroestudiante = f.cleaned_data['numeroestudiante']
                    r.mencionitinerario = f.cleaned_data['mencionitinerario']
                    r.estructurainstitucional = f.cleaned_data['estructurainstitucional']
                    r.numeroresolucion = f.cleaned_data['numeroresolucion']
                    r.nombredirector = f.cleaned_data['nombredirector']
                    r.provincia_id=10
                    r.canton_id=2
                    r.parroquia_id=4
                    r.emailinstitucional=f.cleaned_data['emailinstitucional']
                    r.emailreferencia=f.cleaned_data['emailreferencia']
                    r.telefonoinstitucional=f.cleaned_data['telefonoinstitucional']
                    r.save(request)
                    r.carreraredisenocarrera_set.all().delete()
                    for c in f.cleaned_data['carrera']:
                        ca = CarreraRedisenoCarrera(redisenocarrera=r,
                                                    carrerasrediseno_id=c.id)
                        ca.save(request)
                    r.integarntesredisenocarrera_set.all().delete()
                    for i in f.cleaned_data['integrantes']:
                        inte = IntegarntesRedisenoCarrera(redisenocarrera=r,
                                                          institucioneducacionsuperior_id=i.id)
                        inte.save(request)
                    log(u'Modifico datos generales: %s' % r, request, "edit")
                    return JsonResponse({"result": "ok", "id": r.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'datossustantiva':
            try:
                f = DatosSustantivaForm(request.POST)
                if f.is_valid():
                    r = RedisenoCarrera.objects.get(pk=int(request.POST['id']))
                    r.objetivogeneral = f.cleaned_data['objetivogeneral']
                    r.objetivoespecifico = f.cleaned_data['objetivoespecifico']
                    r.perfilingreso = f.cleaned_data['perfilingreso']
                    r.aprendizajecompetencia = f.cleaned_data['aprendizajecompetencia']
                    r.aprendizajemetodo = f.cleaned_data['aprendizajemetodo']
                    r.mejoramientocalidad = f.cleaned_data['mejoramientocalidad']
                    r.valoresprincipios = f.cleaned_data['valoresprincipios']
                    r.perfilprofesional = f.cleaned_data['perfilprofesional']
                    r.requisitotitulacion = f.cleaned_data['requisitotitulacion']
                    r.descripcionopciones = f.cleaned_data['descripcionopciones']
                    r.pertinencias = f.cleaned_data['pertinencias']
                    r.objetoestudio = f.cleaned_data['objetoestudio']
                    r.metodologia = f.cleaned_data['metodologia']
                    r.save(request)
                    r.opcionesaprobacionredisenocarrera_set.all().delete()
                    for c in f.cleaned_data['opcionesaprobacion']:
                        ca = OpcionesAprobacionRedisenoCarrera(redisenocarrera=r,
                                                               opcionesaprobacion_id=c.id)
                        ca.save(request)
                    log(u'Modifico datos sustantiva docencia: %s' % r, request, "edit")
                    return JsonResponse({"result": "ok", "id": r.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'datosinfraestructura':
            try:
                f = DatosInfraestructuraForm(request.POST)
                if f.is_valid():
                    r = RedisenoCarrera.objects.get(pk=int(request.POST['id']))
                    r.plataformatecnologica = f.cleaned_data['plataformatecnologica']
                    r.estructurainstitucionallaboratorio = f.cleaned_data['estructurainstitucionallaboratorio']
                    r.numerotitulos = f.cleaned_data['numerotitulos']
                    r.titulos = f.cleaned_data['titulos']
                    r.numerovolumen = f.cleaned_data['numerovolumen']
                    r.volumen = f.cleaned_data['volumen']
                    r.numerobasedatos = f.cleaned_data['numerobasedatos']
                    r.basedatos = f.cleaned_data['basedatos']
                    r.numerosuscripcion = f.cleaned_data['numerosuscripcion']
                    r.suscripcion = f.cleaned_data['suscripcion']
                    r.estructurainstitucionalaula = f.cleaned_data['estructurainstitucionalaula']
                    r.numeroaula = f.cleaned_data['numeroaula']
                    r.numeropuesto = f.cleaned_data['numeropuesto']
                    r.perfilprofesionaldirector = f.cleaned_data['perfilprofesionaldirector']
                    r.cargo = f.cleaned_data['cargo']
                    r.horasdedicacion = f.cleaned_data['horasdedicacion']
                    r.tiporelacion = f.cleaned_data['tiporelacion']
                    r.save(request)
                    log(u'Modifico datos infraestructura: %s' % r, request, "edit")
                    return JsonResponse({"result": "ok", "id": r.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'datosinvestigacion':
            try:
                f = DatosInvestigacionForm(request.POST)
                if f.is_valid():
                    r = RedisenoCarrera.objects.get(pk=int(request.POST['id']))
                    r.investigacion = f.cleaned_data['investigacion']
                    r.save(request)
                    log(u'Modifico datos sustantiva investigacion: %s' % r, request, "edit")
                    return JsonResponse({"result": "ok", "id": r.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'datoscomponente':
            try:
                f = DatosComponenteForm(request.POST)
                if f.is_valid():
                    r = RedisenoCarrera.objects.get(pk=int(request.POST['id']))
                    r.componentevinculacion = f.cleaned_data['componentevinculacion']
                    r.modelopracticas = f.cleaned_data['modelopracticas']
                    r.save(request)
                    log(u'Modifico datos sustantiva investigacion: %s' % r, request, "edit")
                    return JsonResponse({"result": "ok", "id": r.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'addcomponentes':
            try:
                f = ComponentesForm(request.POST)
                if f.is_valid():
                    r = RedisenoCarrera.objects.get(pk=int(request.POST['id']))
                    c = ComponentesRedisenoCarrera(redisenocarrera=r,
                                                   componentesrediseno = f.cleaned_data['componentesrediseno'],
                                                   horas = f.cleaned_data['horas'],
                                                   creditos = f.cleaned_data['creditos'])
                    c.save(request)
                    log(u'Modifico componentes rediseño: %s' % r, request, "edit")
                    return JsonResponse({"result": "ok", "id": r.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'addpersonal':
            try:
                f = PersonalForm(request.POST)
                if f.is_valid():
                    r = RedisenoCarrera.objects.get(pk=int(request.POST['id']))
                    c = PersonalAcademicoRedisenoCarrera(redisenocarrera=r,
                                                        perfildocente = f.cleaned_data['perfildocente'],
                                                        asignatura = f.cleaned_data['asignatura'],
                                                        ciudad = 'MILAGRO',
                                                        horadedicacion = f.cleaned_data['horadedicacion'],
                                                        horadedicacionsemanal = f.cleaned_data['horadedicacionsemanal'],
                                                        tiempodedicacion = f.cleaned_data['tiempodedicacion'],
                                                        tipopersonal = f.cleaned_data['tipopersonal'])
                    c.save(request)
                    log(u'Modifico personal rediseño: %s' % r, request, "edit")
                    return JsonResponse({"result": "ok", "id": r.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'addlaboratorio':
            try:
                f = LaboratoriosForm(request.POST)
                if f.is_valid():
                    r = RedisenoCarrera.objects.get(pk=int(request.POST['id']))
                    c = LaboratoriosRedisenoCarrera(redisenocarrera=r,
                                                    estructura = f.cleaned_data['estructura'],
                                                    nombrelaboratorio = f.cleaned_data['nombrelaboratorio'],
                                                    equipamientolaboratorio = f.cleaned_data['equipamientolaboratorio'],
                                                    metroscuadrado = f.cleaned_data['metroscuadrado'],
                                                    puestotrabajo = f.cleaned_data['puestotrabajo'])
                    c.save(request)
                    log(u'Modifico laboratorios rediseño: %s' % r, request, "edit")
                    return JsonResponse({"result": "ok", "id": r.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'addrequisito':
            try:
                f = RequisitoIngresoForm(request.POST)
                if f.is_valid():
                    r = RedisenoCarrera.objects.get(pk=int(request.POST['id']))
                    c = RequisitoIngresoRedisenoCarrera(redisenocarrera=r,
                                                        requisitoingreso = f.cleaned_data['requisitoingreso'])
                    c.save(request)
                    log(u'Modifico requisito ingreso rediseño: %s' % r, request, "edit")
                    return JsonResponse({"result": "ok", "id": r.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'addcontenido':
            try:
                f = ContenidoForm(request.POST)
                if f.is_valid():
                    r = MicrocurricularRedisenoCarrera.objects.get(pk=int(request.POST['id']))
                    c = ContenidoMicrocurricularRedisenoCarrera(microcurricularredisenocarrera=r,
                                                                numero = f.cleaned_data['numero'],
                                                                contenido = f.cleaned_data['contenido'],
                                                                resultado = f.cleaned_data['resultado'])
                    c.save(request)
                    log(u'Modifico contenido ingreso rediseño: %s' % r, request, "edit")
                    return JsonResponse({"result": "ok", "id": r.redisenocarrera.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'addcomponente':
            try:
                f = ComponenteForm(request.POST)
                if f.is_valid():
                    r = MicrocurricularRedisenoCarrera.objects.get(pk=int(request.POST['id']))
                    c = ComponenteMicrocurricularRedisenoCarrera(microcurricularredisenocarrera=r,
                                                                 componente = f.cleaned_data['componente'],
                                                                 horas = f.cleaned_data['horas'],
                                                                 creditos = f.cleaned_data['creditos'])
                    c.save(request)
                    log(u'Modifico componente ingreso rediseño: %s' % r, request, "edit")
                    return JsonResponse({"result": "ok", "id": r.redisenocarrera.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'addmicrocurricular':
            try:
                f = MicrocurricularForm(request.POST)
                if f.is_valid():
                    r = RedisenoCarrera.objects.get(pk=int(request.POST['id']))
                    c = MicrocurricularRedisenoCarrera(redisenocarrera=r,
                                                       numero = f.cleaned_data['numero'],
                                                       asignatura = f.cleaned_data['asignatura'],
                                                       periodo = f.cleaned_data['periodo'],
                                                       unidadorganizacion = f.cleaned_data['unidadorganizacion'],
                                                       itinerario = f.cleaned_data['itinerario'])
                    c.save(request)
                    log(u'Modifico microcurricular ingreso rediseño: %s' % r, request, "edit")
                    return JsonResponse({"result": "ok", "id": r.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'additinerarios':
            try:
                f = ItinerariosForm(request.POST)
                if f.is_valid():
                    r = RedisenoCarrera.objects.get(pk=int(request.POST['id']))
                    c = ItinerariosRedisenoCarrera(redisenocarrera=r,
                                                   itinerario = f.cleaned_data['itinerario'],
                                                   nivelmalla = f.cleaned_data['nivelmalla'])
                    c.save(request)
                    log(u'Modifico itinerarios rediseño: %s' % r, request, "edit")
                    return JsonResponse({"result": "ok", "id": r.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'addconvenios':
            try:
                f = ConvenioForm(request.POST)
                if f.is_valid():
                    r = RedisenoCarrera.objects.get(pk=int(request.POST['id']))
                    c = ConveniosRedisenoCarrera(redisenocarrera=r,
                                                 convenio = f.cleaned_data['convenio'])
                    c.save(request)
                    log(u'Modifico convenio rediseño: %s' % r, request, "edit")
                    return JsonResponse({"result": "ok", "id": r.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'deleterequisito':
            try:
                requisito = RequisitoIngresoRedisenoCarrera.objects.get(pk=int(request.POST['id']), status=True)
                log(u'Eliminó requisito rediseño: %s' % requisito, request, "del")
                requisito.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletelaboratorio':
            try:
                requisito = LaboratoriosRedisenoCarrera.objects.get(pk=int(request.POST['id']), status=True)
                log(u'Eliminó laboratorio rediseño: %s' % requisito, request, "del")
                requisito.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletepersonalacademico':
            try:
                requisito = PersonalAcademicoRedisenoCarrera.objects.get(pk=int(request.POST['id']), status=True)
                log(u'Eliminó Personal Academico rediseño: %s' % requisito, request, "del")
                requisito.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletecomponentes':
            try:
                requisito = ComponenteMicrocurricularRedisenoCarrera.objects.get(pk=int(request.POST['id']), status=True)
                log(u'Eliminó ComponenteMicrocurricular rediseño: %s' % requisito, request, "del")
                requisito.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletecontenido':
            try:
                requisito = ContenidoMicrocurricularRedisenoCarrera.objects.get(pk=int(request.POST['id']), status=True)
                log(u'Eliminó contenido rediseño: %s' % requisito, request, "del")
                requisito.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletemicrocurricular':
            try:
                requisito = MicrocurricularRedisenoCarrera.objects.get(pk=int(request.POST['id']), status=True)
                log(u'Eliminó microcurricular rediseño: %s' % requisito, request, "del")
                requisito.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteitinerarios':
            try:
                requisito = ItinerariosRedisenoCarrera.objects.get(pk=int(request.POST['id']), status=True)
                log(u'Eliminó Itinerarios rediseño: %s' % requisito, request, "del")
                requisito.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteconvenio':
            try:
                requisito = ConveniosRedisenoCarrera.objects.get(pk=int(request.POST['id']), status=True)
                log(u'Eliminó Convenio rediseño: %s' % requisito, request, "del")
                requisito.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletecomponente':
            try:
                requisito = ComponentesRedisenoCarrera.objects.get(pk=int(request.POST['id']), status=True)
                log(u'Eliminó componentes rediseño: %s' % requisito, request, "del")
                requisito.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'duplicar':
            try:
                rediseno = RedisenoCarrera.objects.get(pk=request.POST['id'])
                rediseno1 = RedisenoCarrera(nombreinstitucion = rediseno.nombreinstitucion,
                                            codigoiess = rediseno.codigoiess,
                                            categoriaies = rediseno.categoriaies,
                                            tipofinanciamiento = rediseno.tipofinanciamiento,
                                            siglas = rediseno.siglas,
                                            mision = rediseno.mision,
                                            vision = rediseno.vision,
                                            direccion = rediseno.direccion,
                                            rector = rediseno.rector,
                                            extrector = rediseno.extrector,
                                            decano = rediseno.decano,
                                            extdecano = rediseno.extdecano,
                                            #fase 2
                                            tipotramite = rediseno.tipotramite,
                                            codigosniese = rediseno.codigosniese,
                                            carrera = rediseno.carrera,
                                            proyectoinnovador = rediseno.proyectoinnovador,
                                            tipoformacion = rediseno.tipoformacion,
                                            modalidad = rediseno.modalidad,
                                            descripcionmodalidad = rediseno.descripcionmodalidad,
                                            proyectored = rediseno.proyectored,
                                            campoamplio = rediseno.campoamplio,
                                            campoespecifico = rediseno.campoespecifico,
                                            campodetallado = rediseno.campodetallado,
                                            carreraprogramama = rediseno.carreraprogramama,
                                            titulacion = rediseno.titulacion,
                                            numeroperiodosordinario = rediseno.numeroperiodosordinario,
                                            numerosemanaordinario = rediseno.numerosemanaordinario,
                                            numeroperiodosextraordinario = rediseno.numeroperiodosextraordinario,
                                            numerosemanaextraordinario = rediseno.numerosemanaextraordinario,
                                            indicehoraplanificacion = rediseno.indicehoraplanificacion,
                                            numeroestudiante = rediseno.numeroestudiante,
                                            mencionitinerario = rediseno.mencionitinerario,
                                            estructurainstitucional = rediseno.estructurainstitucional,
                                            provincia = rediseno.provincia,
                                            canton = rediseno.canton,
                                            parroquia = rediseno.parroquia,
                                            numeroresolucion = rediseno.numeroresolucion,
                                            nombredirector = rediseno.nombredirector,
                                            emailinstitucional = rediseno.emailinstitucional,
                                            emailreferencia = rediseno.emailreferencia,
                                            telefonoinstitucional = rediseno.telefonoinstitucional,
                                            #fase 3
                                            objetivogeneral = rediseno.objetivogeneral,
                                            objetivoespecifico = rediseno.objetivoespecifico,
                                            perfilingreso = rediseno.perfilingreso,
                                            aprendizajecompetencia = rediseno.aprendizajecompetencia,
                                            aprendizajemetodo = rediseno.aprendizajemetodo,
                                            mejoramientocalidad = rediseno.mejoramientocalidad,
                                            valoresprincipios = rediseno.valoresprincipios,
                                            perfilprofesional = rediseno.perfilprofesional,
                                            requisitotitulacion = rediseno.requisitotitulacion,
                                            descripcionopciones = rediseno.descripcionopciones,
                                            pertinencias = rediseno.pertinencias,
                                            objetoestudio = rediseno.objetoestudio,
                                            metodologia = rediseno.metodologia,
                                            # fase 4
                                            investigacion = rediseno.investigacion,
                                            # fase 5
                                            componentevinculacion = rediseno.componentevinculacion,
                                            modelopracticas = rediseno.modelopracticas,
                                            # fase 6
                                            plataformatecnologica = rediseno.plataformatecnologica,
                                            estructurainstitucionallaboratorio = rediseno.estructurainstitucionallaboratorio,
                                            numerotitulos = rediseno.numerotitulos,
                                            titulos = rediseno.titulos,
                                            numerovolumen = rediseno.numerovolumen,
                                            volumen = rediseno.volumen,
                                            numerobasedatos = rediseno.numerobasedatos,
                                            basedatos = rediseno.basedatos,
                                            numerosuscripcion = rediseno.numerosuscripcion,
                                            suscripcion = rediseno.suscripcion,
                                            estructurainstitucionalaula = rediseno.estructurainstitucionalaula,
                                            numeroaula = rediseno.numeroaula,
                                            numeropuesto = rediseno.numeropuesto,
                                            perfilprofesionaldirector = rediseno.perfilprofesionaldirector,
                                            cargo = rediseno.cargo,
                                            ciudad = rediseno.ciudad,
                                            horasdedicacion = rediseno.horasdedicacion,
                                            tiporelacion = rediseno.tiporelacion)
                rediseno1.save(request)
                for c in rediseno.carreraredisenocarrera_set.filter(status=True):
                    ca = CarreraRedisenoCarrera(redisenocarrera=rediseno1,
                                                carrerasrediseno=c.carrerasrediseno)
                    ca.save(request)
                for i in rediseno.integarntesredisenocarrera_set.filter(status=True):
                    inte = IntegarntesRedisenoCarrera(redisenocarrera=rediseno1,
                                                      institucioneducacionsuperior=i.institucioneducacionsuperior)
                    inte.save(request)
                for com in rediseno.componentesredisenocarrera_set.filter(status=True):
                    c = ComponentesRedisenoCarrera(redisenocarrera=rediseno1,
                                                   componentesrediseno=com.componentesrediseno,
                                                   horas=com.horas,
                                                   creditos=com.creditos)
                    c.save(request)
                for con in rediseno.conveniosredisenocarrera_set.filter(status=True):
                    c = ConveniosRedisenoCarrera(redisenocarrera=rediseno1,
                                                 convenio=con.convenio)
                    c.save(request)
                for requi in rediseno.requisitoingresoredisenocarrera_set.filter(status=True):
                    c = RequisitoIngresoRedisenoCarrera(redisenocarrera=rediseno1,
                                                        requisitoingreso=requi.requisitoingreso)
                    c.save(request)
                for opc in rediseno.opcionesaprobacionredisenocarrera_set.filter(status=True):
                    ca = OpcionesAprobacionRedisenoCarrera(redisenocarrera=rediseno1,
                                                           opcionesaprobacion=opc.opcionesaprobacion)
                    ca.save(request)
                for micro in rediseno.microcurricularredisenocarrera_set.filter(status=True):
                    m = MicrocurricularRedisenoCarrera(redisenocarrera=rediseno1,
                                                       numero=micro.numero,
                                                       asignatura=micro.asignatura,
                                                       periodo=micro.periodo,
                                                       unidadorganizacion=micro.unidadorganizacion,
                                                       itinerario=micro.itinerario)
                    m.save(request)
                    for cont in m.contenidomicrocurricularredisenocarrera_set.filter(status=True):
                        c = ContenidoMicrocurricularRedisenoCarrera(microcurricularredisenocarrera=m,
                                                                    numero=cont.numero,
                                                                    contenido=cont.contenido,
                                                                    resultado=cont.resultado)
                        c.save(request)
                    for compo in m.componentemicrocurricularredisenocarrera_set.filter(status=True):
                        c = ComponenteMicrocurricularRedisenoCarrera(microcurricularredisenocarrera=m,
                                                                     componente=compo.componente,
                                                                     horas=compo.horas,
                                                                     creditos=compo.creditos)
                        c.save(request)
                for labo in rediseno.laboratoriosredisenocarrera_set.filter(status=True):
                    c = LaboratoriosRedisenoCarrera(redisenocarrera=rediseno1,
                                                    estructura=labo.estructura,
                                                    nombrelaboratorio=labo.nombrelaboratorio,
                                                    equipamientolaboratorio=labo.equipamientolaboratorio,
                                                    metroscuadrado=labo.metroscuadrado,
                                                    puestotrabajo=labo.puestotrabajo)
                    c.save(request)
                for perso in rediseno.personalacademicoredisenocarrera_set.filter(status=True):
                    c = PersonalAcademicoRedisenoCarrera(redisenocarrera=rediseno1,
                                                         perfildocente=perso.perfildocente,
                                                         asignatura=perso.asignatura,
                                                         ciudad=perso.ciudad,
                                                         horadedicacion=perso.horadedicacion,
                                                         horadedicacionsemanal=perso.horadedicacionsemanal,
                                                         tiempodedicacion=perso.tiempodedicacion,
                                                         tipopersonal=perso.tipopersonal)
                    c.save(request)
                log(u'duplico rediseño carrera: %s' % rediseno1, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al procesar el traspaso."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Rediseño Carreras'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Rediseño Carrera'
                    # data['form'] = AsignaturaForm(initial={'creditos': 0})
                    codigo = 0
                    r = None
                    if 'id' in request.GET:
                        codigo = int(request.GET['id'])
                        if codigo > 0:
                            r = RedisenoCarrera.objects.get(pk=codigo)
                    data['rediseño'] = r
                    data['codigo'] = codigo
                    return render(request, "adm_rediseno/add.html", data)
                except Exception as ex:
                    pass

            if action == 'cargaranexo':
                try:
                    data['title'] = u'Cargar Anexo'
                    codigo = 0
                    r = None
                    if 'id' in request.GET:
                        codigo = int(request.GET['id'])
                        if codigo > 0:
                            r = RedisenoCarrera.objects.get(pk=codigo)
                    data['rediseño'] = r
                    data['codigo'] = codigo
                    return render(request, "adm_rediseno/add.html", data)
                except Exception as ex:
                    pass

            if action == 'addcomponentes':
                try:
                    data['title'] = u'Rediseño Carrera'
                    # data['form'] = AsignaturaForm(initial={'creditos': 0})
                    codigo = 0
                    codigo = request.GET['id']
                    r = RedisenoCarrera.objects.get(pk=codigo)
                    data['rediseño'] = r
                    data['codigo'] = codigo
                    ids = r.componentesredisenocarrera_set.values_list('componentesrediseno_id', flat=True).filter(status=True)
                    form = ComponentesForm()
                    form.add(ids)
                    data['form'] = form
                    return render(request, "adm_rediseno/addcomponentes.html", data)
                except Exception as ex:
                    pass

            if action == 'addlaboratorio':
                try:
                    data['title'] = u'Rediseño Carrera'
                    # data['form'] = AsignaturaForm(initial={'creditos': 0})
                    codigo = 0
                    codigo = request.GET['id']
                    r = RedisenoCarrera.objects.get(pk=codigo)
                    data['rediseño'] = r
                    data['codigo'] = codigo
                    form = LaboratoriosForm()
                    data['form'] = form
                    return render(request, "adm_rediseno/addlaboratorio.html", data)
                except Exception as ex:
                    pass

            if action == 'addpersonal':
                try:
                    data['title'] = u'Rediseño Carrera'
                    # data['form'] = AsignaturaForm(initial={'creditos': 0})
                    codigo = 0
                    codigo = request.GET['id']
                    r = RedisenoCarrera.objects.get(pk=codigo)
                    data['rediseño'] = r
                    data['codigo'] = codigo
                    ids = r.personalacademicoredisenocarrera_set.values_list('asignatura_id', flat=True).filter(status=True)
                    form = PersonalForm()
                    form.add(r,ids)
                    data['form'] = form
                    return render(request, "adm_rediseno/addpersonal.html", data)
                except Exception as ex:
                    pass

            if action == 'addrequisito':
                try:
                    data['title'] = u'Rediseño Carrera'
                    # data['form'] = AsignaturaForm(initial={'creditos': 0})
                    codigo = 0
                    codigo = request.GET['id']
                    r = RedisenoCarrera.objects.get(pk=codigo)
                    data['rediseño'] = r
                    data['codigo'] = codigo
                    form = RequisitoIngresoForm()
                    data['form'] = form
                    return render(request, "adm_rediseno/addrequisito.html", data)
                except Exception as ex:
                    pass

            if action == 'addcontenido':
                try:
                    data['title'] = u'Rediseño Carrera'
                    # data['form'] = AsignaturaForm(initial={'creditos': 0})
                    codigo = 0
                    codigo = request.GET['id']
                    r = MicrocurricularRedisenoCarrera.objects.get(pk=codigo)
                    data['rediseño'] = r
                    data['codigo'] = codigo
                    form = ContenidoForm()
                    data['form'] = form
                    return render(request, "adm_rediseno/addcontenido.html", data)
                except Exception as ex:
                    pass

            if action == 'addcomponente':
                try:
                    data['title'] = u'Rediseño Carrera'
                    # data['form'] = AsignaturaForm(initial={'creditos': 0})
                    codigo = 0
                    codigo = request.GET['id']
                    r = MicrocurricularRedisenoCarrera.objects.get(pk=codigo)
                    data['rediseño'] = r
                    data['codigo'] = codigo
                    ids = r.componentemicrocurricularredisenocarrera_set.values_list('componente_id', flat=True).filter(status=True)
                    form = ComponenteForm()
                    form.add(ids)
                    data['form'] = form
                    return render(request, "adm_rediseno/addcomponente.html", data)
                except Exception as ex:
                    pass

            if action == 'addmicrocurricular':
                try:
                    data['title'] = u'Rediseño Carrera'
                    # data['form'] = AsignaturaForm(initial={'creditos': 0})
                    codigo = 0
                    codigo = request.GET['id']
                    r = RedisenoCarrera.objects.get(pk=codigo)
                    data['rediseño'] = r
                    data['codigo'] = codigo
                    form = MicrocurricularForm()
                    data['form'] = form
                    return render(request, "adm_rediseno/addmicrocurricular.html", data)
                except Exception as ex:
                    pass

            if action == 'additinerarios':
                try:
                    data['title'] = u'Rediseño Carrera'
                    # data['form'] = AsignaturaForm(initial={'creditos': 0})
                    codigo = 0
                    codigo = request.GET['id']
                    r = RedisenoCarrera.objects.get(pk=codigo)
                    data['rediseño'] = r
                    data['codigo'] = codigo
                    ids = r.itinerariosredisenocarrera_set.values_list('nivelmalla_id', flat=True).filter(status=True)
                    form = ItinerariosForm()
                    form.add(ids)
                    data['form'] = form
                    return render(request, "adm_rediseno/additinerarios.html", data)
                except Exception as ex:
                    pass

            if action == 'addconvenios':
                try:
                    data['title'] = u'Rediseño Carrera'
                    # data['form'] = AsignaturaForm(initial={'creditos': 0})
                    codigo = 0
                    codigo = request.GET['id']
                    r = RedisenoCarrera.objects.get(pk=codigo)
                    data['rediseño'] = r
                    data['codigo'] = codigo
                    ids = r.conveniosredisenocarrera_set.values_list('convenio_id', flat=True).filter(status=True)
                    form = ConvenioForm()
                    form.add(ids)
                    data['form'] = form
                    return render(request, "adm_rediseno/addconvenios.html", data)
                except Exception as ex:
                    pass

            if action == 'datosinstitucion':
                try:
                    data['title'] = u'Datos Institución'
                    r = None
                    t = TituloInstitucion.objects.filter(status=True)[0]
                    mision = t.mision
                    vision = t.vision
                    codigo = 0
                    if int(request.GET['id']) > 0:
                        codigo = int(request.GET['id'])
                        r = RedisenoCarrera.objects.get(pk=int(request.GET['id']))
                        mision = r.mision
                        vision = r.vision
                        form = DatosInstitucionForm(initial={'nombreinstitucion': t.nombre,
                                                             'codigoiess': t.codigo,
                                                             'categoriaies': r.categoriaies,
                                                             'tipofinanciamiento': r.tipofinanciamiento,
                                                             'siglas': t.nombrecomercial,
                                                             'mision': mision,
                                                             'vision': vision,
                                                             'direccion': t.direccion,
                                                             'rector': r.rector,
                                                             'extrector': r.extrector,
                                                             'extdecano': r.extdecano,
                                                             'decano': r.decano})
                    else:
                        form = DatosInstitucionForm(initial={'nombreinstitucion': t.nombre,
                                                             'codigoiess': t.codigo,
                                                             'siglas': t.nombrecomercial,
                                                             'mision': mision,
                                                             'vision': vision,
                                                             'direccion': t.direccion})
                    data['datos'] = r
                    data['codigo'] = codigo
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_rediseno/datosinstitucion.html", data)
                except:
                    pass

            if action == 'datosgenerales':
                try:
                    data['title'] = u'Datos Generales'
                    r = None
                    codigo = 0
                    if int(request.GET['id']) > 0:
                        codigo = int(request.GET['id'])
                        r = RedisenoCarrera.objects.get(pk=int(request.GET['id']))
                        id_carreras = r.carreraredisenocarrera_set.values_list('carrerasrediseno_id', flat=True).filter(status=True).order_by('carrerasrediseno')
                        carreras = CarrerasRediseno.objects.filter(pk__in=id_carreras)
                        id_integrantes = r.integarntesredisenocarrera_set.values_list('institucioneducacionsuperior_id', flat=True).filter(status=True).order_by('institucioneducacionsuperior')
                        integrantes = InstitucionEducacionSuperior.objects.filter(pk__in=id_integrantes)
                        if r.nombredirector:
                            emailinstitucional = r.emailinstitucional
                            emailreferencia = r.emailreferencia
                            telefonoinstitucional = r.telefonoinstitucional
                        else:
                            t = TituloInstitucion.objects.filter(status=True)[0]
                            emailinstitucional = t.correo
                            emailreferencia = t.correo
                            telefonoinstitucional = t.telefono

                        form = DatosGeneralForm(initial={'tipotramite': r.tipotramite,
                                                         'codigosniese': r.codigosniese,
                                                         'carrera': carreras,
                                                         'proyectoinnovador': r.proyectoinnovador,
                                                         'tipoformacion': r.tipoformacion,
                                                         'rector': r.rector,
                                                         'modalidad': r.modalidad,
                                                         'descripcionmodalidad': r.descripcionmodalidad,
                                                         'proyectored': r.proyectored,
                                                         'integrantes': integrantes,
                                                         'campoamplio': r.campoamplio,
                                                         'campoespecifico': r.campoespecifico,
                                                         'campodetallado': r.campodetallado,
                                                         'carreraprogramama': r.carreraprogramama,
                                                         'titulacion': r.titulacion,
                                                         'numeroperiodosordinario': r.numeroperiodosordinario,
                                                         'numerosemanaordinario': r.numerosemanaordinario,
                                                         'numeroperiodosextraordinario': r.numeroperiodosextraordinario,
                                                         'numeroestudiante': r.numeroestudiante,
                                                         'mencionitinerario': r.mencionitinerario,
                                                         'estructurainstitucional': r.estructurainstitucional,
                                                         'numeroresolucion': r.numeroresolucion,
                                                         'nombredirector': r.nombredirector,
                                                         'emailinstitucional': emailinstitucional,
                                                         'emailreferencia': emailreferencia,
                                                         'telefonoinstitucional': telefonoinstitucional,
                                                         'numerosemanaextraordinario': r.numerosemanaextraordinario})
                    data['datos'] = r
                    data['codigo'] = codigo
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_rediseno/datosgenerales.html", data)
                except:
                    pass

            if action == 'datossustantiva':
                try:
                    data['title'] = u'Función Sustantiva: Docencia'
                    r = None
                    codigo = 0
                    if int(request.GET['id']) > 0:
                        codigo = int(request.GET['id'])
                        r = RedisenoCarrera.objects.get(pk=int(request.GET['id']))
                        opcionesaprobacion = r.opcionesaprobacionredisenocarrera_set.filter(status=True)
                        form = DatosSustantivaForm(initial={'objetivogeneral': r.objetivogeneral,
                                                            'objetivoespecifico': r.objetivoespecifico,
                                                            'perfilingreso': r.perfilingreso,
                                                            'aprendizajecompetencia': r.aprendizajecompetencia,
                                                            'aprendizajemetodo': r.aprendizajemetodo,
                                                            'mejoramientocalidad': r.mejoramientocalidad,
                                                            'valoresprincipios': r.valoresprincipios,
                                                            'perfilprofesional': r.perfilprofesional,
                                                            'requisitotitulacion': r.requisitotitulacion,
                                                            'opcionesaprobacion': opcionesaprobacion,
                                                            'descripcionopciones': r.descripcionopciones,
                                                            'pertinencias': r.pertinencias,
                                                            'objetoestudio': r.objetoestudio,
                                                            'metodologia': r.metodologia})
                    data['datos'] = r
                    data['codigo'] = codigo
                    data['form'] = form
                    return render(request, "adm_rediseno/datossustantiva.html", data)
                except:
                    pass

            if action == 'datosinfraestructura':
                try:
                    data['title'] = u'Infraestructura, equipamiento e información financiera'
                    r = None
                    codigo = 0
                    if int(request.GET['id']) > 0:
                        codigo = int(request.GET['id'])
                        r = RedisenoCarrera.objects.get(pk=int(request.GET['id']))
                        form = DatosInfraestructuraForm(initial={'plataformatecnologica': r.plataformatecnologica,
                                                                 'estructurainstitucionallaboratorio': r.estructurainstitucionallaboratorio,
                                                                 'numerotitulos': r.numerotitulos,
                                                                 'titulos': r.titulos,
                                                                 'numerovolumen': r.numerovolumen,
                                                                 'volumen': r.volumen,
                                                                 'numerobasedatos': r.numerobasedatos,
                                                                 'basedatos': r.basedatos,
                                                                 'numerosuscripcion': r.numerosuscripcion,
                                                                 'suscripcion': r.suscripcion,
                                                                 'estructurainstitucionalaula': r.estructurainstitucionalaula,
                                                                 'numeroaula': r.numeroaula,
                                                                 'numeropuesto': r.numeropuesto,
                                                                 'perfilprofesionaldirector': r.perfilprofesionaldirector,
                                                                 'cargo': r.cargo,
                                                                 'horasdedicacion': r.horasdedicacion,
                                                                 'tiporelacion': r.tiporelacion})
                    data['datos'] = r
                    data['codigo'] = codigo
                    data['form'] = form
                    return render(request, "adm_rediseno/datosinfraestructura.html", data)
                except:
                    pass

            if action == 'datosinvestigacion':
                try:
                    data['title'] = u'Función Sustantiva: Investigación'
                    r = None
                    codigo = 0
                    if int(request.GET['id']) > 0:
                        codigo = int(request.GET['id'])
                        r = RedisenoCarrera.objects.get(pk=int(request.GET['id']))
                        form = DatosInvestigacionForm(initial={'investigacion': r.investigacion})
                    data['datos'] = r
                    data['codigo'] = codigo
                    data['form'] = form
                    return render(request, "adm_rediseno/datosinvestigacion.html", data)
                except:
                    pass

            if action == 'datoscomponente':
                try:
                    data['title'] = u'Función sustantiva: Vinculación con la sociedad'
                    r = None
                    codigo = 0
                    if int(request.GET['id']) > 0:
                        codigo = int(request.GET['id'])
                        r = RedisenoCarrera.objects.get(pk=int(request.GET['id']))
                        form = DatosComponenteForm(initial={'componentevinculacion': r.componentevinculacion,
                                                            'modelopracticas': r.modelopracticas})
                    data['datos'] = r
                    data['codigo'] = codigo
                    data['form'] = form
                    return render(request, "adm_rediseno/datoscomponente.html", data)
                except:
                    pass

            if action == 'extension':
                try:
                    profesor = Profesor.objects.get(pk=int(request.GET['id_profesor']))
                    extension = profesor.persona.telefonoextension
                    return JsonResponse({"result": "ok", "extension": extension})
                except Exception as ex:
                    pass

            if action == 'deleterequisito':
                try:
                    data['title'] = u'Eliminar Requisito Ingreso'
                    data['requisito'] = RequisitoIngresoRedisenoCarrera.objects.get(pk=request.GET['id'])
                    return render(request, 'adm_rediseno/deleterequisito.html', data)
                except Exception as ex:
                    pass

            if action == 'deletelaboratorio':
                try:
                    data['title'] = u'Eliminar Laboratorio'
                    data['requisito'] = LaboratoriosRedisenoCarrera.objects.get(pk=request.GET['id'])
                    return render(request, 'adm_rediseno/deletelaboratorio.html', data)
                except Exception as ex:
                    pass

            if action == 'deletepersonalacademico':
                try:
                    data['title'] = u'Eliminar Personal Académico'
                    data['requisito'] = PersonalAcademicoRedisenoCarrera.objects.get(pk=request.GET['id'])
                    return render(request, 'adm_rediseno/deletepersonalacademico.html', data)
                except Exception as ex:
                    pass

            if action == 'deletecomponentes':
                try:
                    data['title'] = u'Eliminar Componente'
                    data['requisito'] = ComponenteMicrocurricularRedisenoCarrera.objects.get(pk=request.GET['id'])
                    return render(request, 'adm_rediseno/deletecomponentes.html', data)
                except Exception as ex:
                    pass

            if action == 'deletecontenido':
                try:
                    data['title'] = u'Eliminar Contenido'
                    data['requisito'] = ContenidoMicrocurricularRedisenoCarrera.objects.get(pk=request.GET['id'])
                    return render(request, 'adm_rediseno/deletecontenido.html', data)
                except Exception as ex:
                    pass

            if action == 'deletemicrocurricular':
                try:
                    data['title'] = u'Eliminar Microcurricular'
                    data['requisito'] = MicrocurricularRedisenoCarrera.objects.get(pk=request.GET['id'])
                    return render(request, 'adm_rediseno/deletemicrocurricular.html', data)
                except Exception as ex:
                    pass

            if action == 'deleteconvenio':
                try:
                    data['title'] = u'Eliminar Convenio'
                    data['requisito'] = ConveniosRedisenoCarrera.objects.get(pk=request.GET['id'])
                    return render(request, 'adm_rediseno/deleteconvenio.html', data)
                except Exception as ex:
                    pass

            if action == 'deletecomponente':
                try:
                    data['title'] = u'Eliminar Componente'
                    data['requisito'] = ComponentesRedisenoCarrera.objects.get(pk=request.GET['id'])
                    return render(request, 'adm_rediseno/deletecomponente.html', data)
                except Exception as ex:
                    pass

            if action == 'deleteitinerarios':
                try:
                    data['title'] = u'Eliminar Itinerarios'
                    data['requisito'] = ItinerariosRedisenoCarrera.objects.get(pk=request.GET['id'])
                    return render(request, 'adm_rediseno/deleteitinerarios.html', data)
                except Exception as ex:
                    pass

            if action == 'duplicar':
                try:
                    data['title'] = u'Duplicar Rediseño Carrera'
                    data['rediseno'] = RedisenoCarrera.objects.get(pk=int(request.GET['id']))
                    return render(request, 'adm_rediseno/duplicar.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                ss = search.split(' ')
                if len(ss) == 2:
                    rediseño = RedisenoCarrera.objects.filter(Q(carrera__descripcion__icontains=ss[0]) & Q(carrera__descripcion__icontains=ss[1])).order_by('carrera__descripcion')
                if len(ss) == 3:
                    rediseño = RedisenoCarrera.objects.filter(Q(carrera__descripcion__icontains=ss[0]) & Q(carrera__descripcion__icontains=ss[1]) & Q(carrera__descripcion__icontains=ss[2])).order_by('carrera__descripcion')
                if len(ss) == 4:
                    rediseño = RedisenoCarrera.objects.filter(Q(carrera__descripcion__icontains=ss[0]) & Q(carrera__descripcion__icontains=ss[1]) & Q(carrera__descripcion__icontains=ss[2]) & Q(carrera__descripcion__icontains=ss[3])).order_by('carrera__descripcion')
                else:
                    rediseño = RedisenoCarrera.objects.filter(carrera__descripcion__icontains=search).order_by('carrera__descripcion')
            elif 'id' in request.GET:
                ids = request.GET['id']
                rediseño = RedisenoCarrera.objects.filter(id=ids)
            else:
                rediseño = RedisenoCarrera.objects.filter(status=True).order_by('carrera__descripcion')
            paging = MiPaginador(rediseño, 25)
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
            data['rediseño'] = page.object_list
            return render(request, "adm_rediseno/view.html", data)
