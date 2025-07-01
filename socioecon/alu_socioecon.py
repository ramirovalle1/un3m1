import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import RequestContext
from decorators import last_access, secure_module
from sagest.forms import DiscapacidadForm, DatosDomicilioForm, FamiliarForm, DatosNacimientoForm, DatosPersonalesForm
from settings import DEBUG
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.commonviews import adduserdata
from sga.funciones import generar_nombre, log
from sga.models import ParentescoPersona, PersonaDatosFamiliares, TIPO_CELULAR, Matricula, InscripcionNivel, Persona, \
    PerfilInscripcion, FotoPersona, PersonaDocumentoPersonal
from socioecon.forms import SustentoHogarForm, PersonaActRecreacionForm, TipoHogarForm, TipoViviendaproForm, \
    PersonaCubreGastoForm, NivelEstudioForm, OcupacionJefeHogarForm, CantidadBannoDuchaForm, TipoServicioHigienicoForm, \
    MaterialPisoForm, MaterialParedForm, TipoViviendaForm, CantidadTVColorHogarForm, CantidadVehiculoHogarForm, \
    CantidadCelularHogarForm, \
    PersonaLugarTareaForm, PersonaSalubridadVidaForm, PersonaEstadoGeneralForm, ProveedorInternetForm, \
    AgregarProveedorInternet
from socioecon.models import FichaSocioeconomicaINEC, PersonaSustentaHogar, FormaTrabajo, TipoHogar, PersonaCubreGasto, \
    NivelEstudio, OcupacionJefeHogar, TipoVivienda, MaterialPared, MaterialPiso, CantidadBannoDucha, \
    TipoServicioHigienico, CantidadTVColorHogar, CantidadCelularHogar, CantidadVehiculoHogar, \
    TipoViviendaPro, ACTIVIDADES_RECREACION, REALIZA_TAREAS, SALUBRIDAD_VIDA, ESTADO_GENERAL, \
    FichaSocioeconomicaReplayINEC, ProveedorServicio


@login_required(redirect_field_name='ret', login_url='/loginsga')
@last_access
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if persona.es_estudiante() or persona.es_inscripcionaspirante():
        # if not persona.es_estudiante():
        #     return HttpResponseRedirect("/?info=Usted no pertenece al grupo de estudiantes.")
        perfilprincipal = request.session['perfilprincipal']
        inscripcion = perfilprincipal.inscripcion
        if request.method == 'POST':
            action = request.POST['action']

            if action == 'changeescabezafamilia':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.escabezafamilia:
                        ficha.escabezafamilia = False
                    else:
                        ficha.escabezafamilia = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.escabezafamilia}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            if action == 'changeescabezafamiliareplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.escabezafamilia:
                        ficha.escabezafamilia = False
                    else:
                        ficha.escabezafamilia = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.escabezafamilia}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")


            elif action == 'changeesdependiente':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.esdependiente:
                        ficha.esdependiente = False
                    else:
                        ficha.esdependiente = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.esdependiente}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changeesdependientereplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.esdependiente:
                        ficha.esdependiente = False
                    else:
                        ficha.esdependiente = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.esdependiente}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")


            elif action == 'confirmarficha':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.confirmar = True
                    ficha.save()
                    log(u'Confirmo ficha socioeconomica: %s %s %s' % (ficha, ficha.puntajetotal, ficha.grupoeconomico.nombre), request, "edit")
                    return HttpResponse(json.dumps({'result': 'ok'}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'confirmarfichareplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.confirmar = True
                    ficha.save()
                    log(u'Confirmo ficha socioeconomica replica: %s %s %s' % (ficha, ficha.puntajetotal, ficha.grupoeconomico.nombre), request, "edit")
                    return HttpResponse(json.dumps({'result': 'ok'}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'tipohogar':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    th = TipoHogar.objects.get(pk=request.POST['th'])
                    ficha.tipohogar = th
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tipohogar.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'tipohogarreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    th = TipoHogar.objects.get(pk=request.POST['th'])
                    ficha.tipohogar = th
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tipohogar.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'tiporecreacion':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    otrosg = request.POST['otrosg']
                    ficha.tipoactividad = request.POST['codigoact']
                    ficha.otrosactividad = request.POST['otrosg']
                    ficha.save()
                    valor = ACTIVIDADES_RECREACION[int(ficha.tipoactividad) - 1][1]
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': valor }), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'tiporecreacionreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    otrosg = request.POST['otrosg']
                    ficha.tipoactividad = request.POST['codigoact']
                    ficha.otrosactividad = request.POST['otrosg']
                    ficha.save()
                    valor = ACTIVIDADES_RECREACION[int(ficha.tipoactividad) - 1][1]
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': valor }), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'datospersonales':
                try:
                    persona = request.session['persona']
                    f = DatosPersonalesForm(request.POST)
                    if not f.is_valid():
                        transaction.set_rollback(True)
                        return JsonResponse({'result': 'bad', "form": [{k: v[0]} for k, v in f.errors.items()],
                                             "mensaje": "Error en el formulario"})

                    if 'archivocedula' in request.FILES:
                        arch = request.FILES['archivocedula']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 4194304:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                    if f.is_valid():
                        persona.pasaporte = f.cleaned_data['pasaporte']
                        persona.sexo = f.cleaned_data['sexo']
                        persona.lgtbi = f.cleaned_data['lgtbi']
                        persona.nacimiento = f.cleaned_data['nacimiento']
                        # persona.nacionalidad = f.cleaned_data['nacionalidad']
                        persona.anioresidencia = f.cleaned_data['anioresidencia']
                        persona.email = f.cleaned_data['email']
                        persona.eszurdo = f.cleaned_data['eszurdo']
                        persona.libretamilitar = f.cleaned_data['libretamilitar']
                        persona.telefonoextension = f.cleaned_data['extension']
                        persona.save()
                        personaextension = persona.datos_extension()
                        personaextension.estadocivil = f.cleaned_data['estadocivil']
                        personaextension.save()

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
                        log(u'Modifico datos personales: %s' % persona, request, "edit")
                        return HttpResponse(json.dumps({'result': 'ok'}), content_type="application/json")

                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({'result': 'bad', 'mensaje': f'Error al guardar los datos: {ex}'}), content_type="application/json")

            elif action == 'tipolugartareas':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    otrosg = request.POST['otroslugartarea']
                    ficha.tipotarea = request.POST['codigolugtarea']
                    ficha.otrostarea = request.POST['otroslugartarea']
                    ficha.save()
                    valor = REALIZA_TAREAS[int(ficha.tipotarea) - 1][1]
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': valor }), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'tipolugartareasreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    otrosg = request.POST['otroslugartarea']
                    ficha.tipotarea = request.POST['codigolugtarea']
                    ficha.otrostarea = request.POST['otroslugartarea']
                    ficha.save()
                    valor = REALIZA_TAREAS[int(ficha.tipotarea) - 1][1]
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': valor }), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'salubridad':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.salubridadvida = request.POST['codigosalubridad']
                    ficha.save()
                    valor = SALUBRIDAD_VIDA[int(ficha.salubridadvida) - 1][1]
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': valor }), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'salubridadreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.salubridadvida = request.POST['codigosalubridad']
                    ficha.save()
                    valor = SALUBRIDAD_VIDA[int(ficha.salubridadvida) - 1][1]
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': valor }), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'estadogeneral':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.estadogeneral = request.POST['codigoestadogeneral']
                    ficha.save()
                    valor = ESTADO_GENERAL[int(ficha.estadogeneral) - 1][1]
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': valor }), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'estadogeneralreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.estadogeneral = request.POST['codigoestadogeneral']
                    ficha.save()
                    valor = ESTADO_GENERAL[int(ficha.estadogeneral) - 1][1]
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': valor }), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'personacubregasto':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    pcg = PersonaCubreGasto.objects.get(pk=request.POST['pcg'])
                    otrosg = request.POST['otrosg']
                    ficha.personacubregasto = pcg
                    ficha.otroscubregasto = otrosg
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.personacubregasto.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'personacubregastoreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    pcg = PersonaCubreGasto.objects.get(pk=request.POST['pcg'])
                    otrosg = request.POST['otrosg']
                    ficha.personacubregasto = pcg
                    ficha.otroscubregasto = otrosg
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.personacubregasto.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")


            elif action == 'addsustentohogar':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    personasustenta = request.POST['persona']
                    formatrabajo = FormaTrabajo.objects.get(pk=int(request.POST['ft']))
                    parentesco = ParentescoPersona.objects.get(pk=int(request.POST['parentesco']))
                    ingresomensual = float(request.POST['im'])
                    sustento = PersonaSustentaHogar(persona=personasustenta,
                                                    parentesco=parentesco,
                                                    formatrabajo=formatrabajo,
                                                    ingresomensual=ingresomensual)
                    sustento.save()
                    ficha.sustentahogar.add(sustento)
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok'}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changealguienafiliado':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.alguienafiliado:
                        ficha.alguienafiliado = False
                        ficha.val_alguienafiliado = 0
                    else:
                        ficha.alguienafiliado = True
                        ficha.val_alguienafiliado = 39
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.alguienafiliado}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changealguienafiliadoreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.alguienafiliado:
                        ficha.alguienafiliado = False
                        ficha.val_alguienafiliado = 0
                    else:
                        ficha.alguienafiliado = True
                        ficha.val_alguienafiliado = 39
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.alguienafiliado}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")


            elif action == 'changealguienseguro':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.alguienseguro:
                        ficha.alguienseguro = False
                        ficha.val_alguienseguro = 0
                    else:
                        ficha.alguienseguro = True
                        ficha.val_alguienseguro = 55
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.alguienseguro}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changealguienseguroreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.alguienseguro:
                        ficha.alguienseguro = False
                        ficha.val_alguienseguro = 0
                    else:
                        ficha.alguienseguro = True
                        ficha.val_alguienseguro = 55
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.alguienseguro}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changecompravestcc':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.compravestcc:
                        ficha.compravestcc = False
                        ficha.val_compravestcc = 0
                    else:
                        ficha.compravestcc = True
                        ficha.val_compravestcc = 6
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.compravestcc}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changecompravestccreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.compravestcc:
                        ficha.compravestcc = False
                        ficha.val_compravestcc = 0
                    else:
                        ficha.compravestcc = True
                        ficha.val_compravestcc = 6
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.compravestcc}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changeusainternetseism':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.usainternetseism:
                        ficha.usainternetseism = False
                        ficha.val_usainternetseism = 0
                    else:
                        ficha.usainternetseism = True
                        ficha.val_usainternetseism = 26
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.usainternetseism}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changeusainternetseismreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.usainternetseism:
                        ficha.usainternetseism = False
                        ficha.val_usainternetseism = 0
                    else:
                        ficha.usainternetseism = True
                        ficha.val_usainternetseism = 26
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.usainternetseism}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changeusacorreonotrab':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.usacorreonotrab:
                        ficha.usacorreonotrab = False
                        ficha.val_usacorreonotrab = 0
                    else:
                        ficha.usacorreonotrab = True
                        ficha.val_usacorreonotrab = 27
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.usacorreonotrab}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changeusacorreonotrabreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.usacorreonotrab:
                        ficha.usacorreonotrab = False
                        ficha.val_usacorreonotrab = 0
                    else:
                        ficha.usacorreonotrab = True
                        ficha.val_usacorreonotrab = 27
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.usacorreonotrab}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changeregistroredsocial':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.registroredsocial:
                        ficha.registroredsocial = False
                        ficha.val_registroredsocial = 0
                    else:
                        ficha.registroredsocial = True
                        ficha.val_registroredsocial = 28
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.registroredsocial}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changeregistroredsocialreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.registroredsocial:
                        ficha.registroredsocial = False
                        ficha.val_registroredsocial = 0
                    else:
                        ficha.registroredsocial = True
                        ficha.val_registroredsocial = 28
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.registroredsocial}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changeleidolibrotresm':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.leidolibrotresm:
                        ficha.leidolibrotresm = False
                        ficha.val_leidolibrotresm = 0
                    else:
                        ficha.leidolibrotresm = True
                        ficha.val_leidolibrotresm = 12
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.leidolibrotresm}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changeleidolibrotresmreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.leidolibrotresm:
                        ficha.leidolibrotresm = False
                        ficha.val_leidolibrotresm = 0
                    else:
                        ficha.leidolibrotresm = True
                        ficha.val_leidolibrotresm = 12
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.leidolibrotresm}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienetelefconv':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienetelefconv:
                        ficha.tienetelefconv = False
                        ficha.val_tienetelefconv = 0
                    else:
                        ficha.tienetelefconv = True
                        ficha.val_tienetelefconv = 19
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienetelefconv}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienetelefconvreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienetelefconv:
                        ficha.tienetelefconv = False
                        ficha.val_tienetelefconv = 0
                    else:
                        ficha.tienetelefconv = True
                        ficha.val_tienetelefconv = 19
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienetelefconv}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienecocinahorno':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienecocinahorno:
                        ficha.tienecocinahorno = False
                        ficha.val_tienecocinahorno = 0
                    else:
                        ficha.tienecocinahorno = True
                        ficha.val_tienecocinahorno = 29
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienecocinahorno}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienecocinahornoreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienecocinahorno:
                        ficha.tienecocinahorno = False
                        ficha.val_tienecocinahorno = 0
                    else:
                        ficha.tienecocinahorno = True
                        ficha.val_tienecocinahorno = 29
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienecocinahorno}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienerefrig':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienerefrig:
                        ficha.tienerefrig = False
                        ficha.val_tienerefrig = 0
                    else:
                        ficha.tienerefrig = True
                        ficha.val_tienerefrig = 30
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienerefrig}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienerefrigreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienerefrig:
                        ficha.tienerefrig = False
                        ficha.val_tienerefrig = 0
                    else:
                        ficha.tienerefrig = True
                        ficha.val_tienerefrig = 30
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienerefrig}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienelavadora':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienelavadora:
                        ficha.tienelavadora = False
                        ficha.val_tienelavadora = 0
                    else:
                        ficha.tienelavadora = True
                        ficha.val_tienelavadora = 18
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienelavadora}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienelavadorareplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienelavadora:
                        ficha.tienelavadora = False
                        ficha.val_tienelavadora = 0
                    else:
                        ficha.tienelavadora = True
                        ficha.val_tienelavadora = 18
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienelavadora}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienemusica':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienemusica:
                        ficha.tienemusica = False
                        ficha.val_tienemusica = 0
                    else:
                        ficha.tienemusica = True
                        ficha.val_tienemusica = 18
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienemusica}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienemusicareplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienemusica:
                        ficha.tienemusica = False
                        ficha.val_tienemusica = 0
                    else:
                        ficha.tienemusica = True
                        ficha.val_tienemusica = 18
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienemusica}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetieneinternet':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tieneinternet:
                        ficha.tieneinternet = False
                        ficha.val_tieneinternet = 0
                    else:
                        ficha.tieneinternet = True
                        ficha.val_tieneinternet = 45

                    ficha.proveedorinternet = None
                    ficha.internetpanf = False

                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tieneinternet}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetieneinternetreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tieneinternet:
                        ficha.tieneinternet = False
                        ficha.val_tieneinternet = 0
                    else:
                        ficha.tieneinternet = True
                        ficha.val_tieneinternet = 45
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tieneinternet}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienesala':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienesala:
                        ficha.tienesala = False
                    else:
                        ficha.tienesala = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienesala}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienesalareplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienesala:
                        ficha.tienesala = False
                    else:
                        ficha.tienesala = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienesala}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienecomedor':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienecomedor:
                        ficha.tienecomedor = False
                    else:
                        ficha.tienecomedor = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienecomedor}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienecomedorreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienecomedor:
                        ficha.tienecomedor = False
                    else:
                        ficha.tienecomedor = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienecomedor}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienecocina':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienecocina:
                        ficha.tienecocina = False
                    else:
                        ficha.tienecocina = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienecocina}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienecocinareplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienecocina:
                        ficha.tienecocina = False
                    else:
                        ficha.tienecocina = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienecocina}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienebanio':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienebanio:
                        ficha.tienebanio = False
                    else:
                        ficha.tienebanio = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienebanio}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienebanioreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienebanio:
                        ficha.tienebanio = False
                    else:
                        ficha.tienebanio = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienebanio}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetieneluz':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tieneluz:
                        ficha.tieneluz = False
                    else:
                        ficha.tieneluz = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tieneluz}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetieneluzreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tieneluz:
                        ficha.tieneluz = False
                    else:
                        ficha.tieneluz = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tieneluz}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetieneagua':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tieneagua:
                        ficha.tieneagua = False
                    else:
                        ficha.tieneagua = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tieneagua}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetieneaguareplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tieneagua:
                        ficha.tieneagua = False
                    else:
                        ficha.tieneagua = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tieneagua}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienetelefono':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienetelefono:
                        ficha.tienetelefono = False
                    else:
                        ficha.tienetelefono = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienetelefono}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienetelefonoreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienetelefono:
                        ficha.tienetelefono = False
                    else:
                        ficha.tienetelefono = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienetelefono}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienealcantarilla':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienealcantarilla:
                        ficha.tienealcantarilla = False
                    else:
                        ficha.tienealcantarilla = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienealcantarilla}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienealcantarillareplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienealcantarilla:
                        ficha.tienealcantarilla = False
                    else:
                        ficha.tienealcantarilla = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienealcantarilla}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changedisponibilidadrecursos':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.disponibilidadrecursos:
                        ficha.disponibilidadrecursos = False
                        ficha.tienefolleto = False
                        ficha.tienecomputador = False
                        ficha.tieneenciclopedia = False
                    else:
                        ficha.disponibilidadrecursos = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.disponibilidadrecursos}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changedisponibilidadrecursosreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.disponibilidadrecursos:
                        ficha.disponibilidadrecursos = False
                        ficha.tienefolleto = False
                        ficha.tienecomputador = False
                        ficha.tieneenciclopedia = False
                    else:
                        ficha.disponibilidadrecursos = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.disponibilidadrecursos}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienefolleto':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienefolleto:
                        ficha.tienefolleto = False
                    else:
                        ficha.tienefolleto = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienefolleto}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienefolletoreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienefolleto:
                        ficha.tienefolleto = False
                    else:
                        ficha.tienefolleto = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienefolleto}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienecomputador':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienecomputador:
                        ficha.tienecomputador = False
                    else:
                        ficha.tienecomputador = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienecomputador}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienecomputadorreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienecomputador:
                        ficha.tienecomputador = False
                    else:
                        ficha.tienecomputador = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienecomputador}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetieneenciclopedia':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tieneenciclopedia:
                        ficha.tieneenciclopedia = False
                    else:
                        ficha.tieneenciclopedia = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tieneenciclopedia}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetieneenciclopediareplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tieneenciclopedia:
                        ficha.tieneenciclopedia = False
                    else:
                        ficha.tieneenciclopedia = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tieneenciclopedia}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienecyber':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienecyber:
                        ficha.tienecyber = False
                    else:
                        ficha.tienecyber = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienecyber}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienecyberreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienecyber:
                        ficha.tienecyber = False
                    else:
                        ficha.tienecyber = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienecyber}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienebiblioteca':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienebiblioteca:
                        ficha.tienebiblioteca = False
                    else:
                        ficha.tienebiblioteca = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienebiblioteca}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienebibliotecareplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienebiblioteca:
                        ficha.tienebiblioteca = False
                    else:
                        ficha.tienebiblioteca = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienebiblioteca}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienemuseo':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienemuseo:
                        ficha.tienemuseo = False
                    else:
                        ficha.tienemuseo = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienemuseo}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienemuseoreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienemuseo:
                        ficha.tienemuseo = False
                    else:
                        ficha.tienemuseo = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienemuseo}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienearearecreacion':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienearearecreacion:
                        ficha.tienearearecreacion = False
                    else:
                        ficha.tienearearecreacion = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienearearecreacion}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienearearecreacionreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienearearecreacion:
                        ficha.tienearearecreacion = False
                    else:
                        ficha.tienearearecreacion = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienearearecreacion}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienediabetes':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienediabetes:
                        ficha.tienediabetes = False
                    else:
                        ficha.tienediabetes = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienediabetes}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienediabetesreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienediabetes:
                        ficha.tienediabetes = False
                    else:
                        ficha.tienediabetes = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienediabetes}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienehipertencion':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienehipertencion:
                        ficha.tienehipertencion = False
                    else:
                        ficha.tienehipertencion = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienehipertencion}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienehipertencionreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienehipertencion:
                        ficha.tienehipertencion = False
                    else:
                        ficha.tienehipertencion = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienehipertencion}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetieneparkinson':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tieneparkinson:
                        ficha.tieneparkinson = False
                    else:
                        ficha.tieneparkinson = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tieneparkinson}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetieneparkinsonreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tieneparkinson:
                        ficha.tieneparkinson = False
                    else:
                        ficha.tieneparkinson = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tieneparkinson}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienecancer':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienecancer:
                        ficha.tienecancer = False
                    else:
                        ficha.tienecancer = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienecancer}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienecancerreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienecancer:
                        ficha.tienecancer = False
                    else:
                        ficha.tienecancer = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienecancer}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienealzheimer':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienealzheimer:
                        ficha.tienealzheimer = False
                    else:
                        ficha.tienealzheimer = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienealzheimer}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienealzheimerreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienealzheimer:
                        ficha.tienealzheimer = False
                    else:
                        ficha.tienealzheimer = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienealzheimer}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienevitiligo':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienevitiligo:
                        ficha.tienevitiligo = False
                    else:
                        ficha.tienevitiligo = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienevitiligo}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienevitiligoreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienevitiligo:
                        ficha.tienevitiligo = False
                    else:
                        ficha.tienevitiligo = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienevitiligo}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienedesgastamiento':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienedesgastamiento:
                        ficha.tienedesgastamiento = False
                    else:
                        ficha.tienedesgastamiento = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienedesgastamiento}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienedesgastamientoreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienedesgastamiento:
                        ficha.tienedesgastamiento = False
                    else:
                        ficha.tienedesgastamiento = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienedesgastamiento}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienepielblanca':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienepielblanca:
                        ficha.tienepielblanca = False
                    else:
                        ficha.tienepielblanca = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienepielblanca}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienepielblancareplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienepielblanca:
                        ficha.tienepielblanca = False
                    else:
                        ficha.tienepielblanca = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienepielblanca}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienesida':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienesida:
                        ficha.tienesida = False
                    else:
                        ficha.tienesida = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienesida}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienesidareplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienesida:
                        ficha.tienesida = False
                    else:
                        ficha.tienesida = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienesida}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienedesktop':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienedesktop:
                        ficha.tienedesktop = False
                        ficha.val_tienedesktop = 0
                    else:
                        ficha.tienedesktop = True
                        ficha.val_tienedesktop = 35

                    ficha.save()

                    if ficha.tienedesktop is False and ficha.tienedesktop is False:
                        ficha.equipotienecamara = False
                        ficha.save()

                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienedesktop, 'valor2': ficha.tienelaptop}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienedesktopreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienedesktop:
                        ficha.tienedesktop = False
                        ficha.val_tienedesktop = 0
                    else:
                        ficha.tienedesktop = True
                        ficha.val_tienedesktop = 35
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienedesktop}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienelaptop':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienelaptop:
                        ficha.tienelaptop = False
                        ficha.val_tienelaptop = 0
                    else:
                        ficha.tienelaptop = True
                        ficha.val_tienelaptop = 39
                    ficha.save()

                    if ficha.tienedesktop is False and ficha.tienedesktop is False:
                        ficha.equipotienecamara = False
                        ficha.save()

                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienelaptop, 'valor2': ficha.tienedesktop}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changetienelaptopreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.tienelaptop:
                        ficha.tienelaptop = False
                        ficha.val_tienelaptop = 0
                    else:
                        ficha.tienelaptop = True
                        ficha.val_tienelaptop = 39
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tienelaptop}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changeinternetajeno':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.internetpanf:
                        ficha.internetpanf = False
                    else:
                        ficha.internetpanf = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.internetpanf}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'changeequipotienecamara':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    if ficha.equipotienecamara:
                        ficha.equipotienecamara = False
                    else:
                        ficha.equipotienecamara = True
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.equipotienecamara}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'addproveedorinternet':
                try:
                    f = AgregarProveedorInternet(request.POST)
                    if f.is_valid():
                        if not ProveedorServicio.objects.filter(nombre=f.cleaned_data['nombreproveedor'], tiposervicio=1, status=True).exists():
                            proveedorinternet = ProveedorServicio(nombre=f.cleaned_data['nombreproveedor'],
                                                                  tiposervicio=1
                                                                  )
                            proveedorinternet.save(request)
                            log(u'Adiciono proveedor de internet: %s [%s]' % (proveedorinternet, proveedorinternet.id), request, "add")
                            return JsonResponse({"result": "ok", "id": proveedorinternet.id})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"El proveedor de internet ya existe."})
                    else:
                        errorformulario = f._errors
                        raise NameError('Error')
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

            elif action == 'niveljefehogar':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    niveleducacion = NivelEstudio.objects.get(pk=request.POST['niveledu'])
                    ficha.niveljefehogar = niveleducacion
                    ficha.val_niveljefehogar = niveleducacion.puntaje
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.niveljefehogar.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'niveljefehogarreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    niveleducacion = NivelEstudio.objects.get(pk=request.POST['niveledu'])
                    ficha.niveljefehogar = niveleducacion
                    ficha.val_niveljefehogar = niveleducacion.puntaje
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.niveljefehogar.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'ocupacionjefehogar':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    ocupacion = OcupacionJefeHogar.objects.get(pk=request.POST['ocupacion'])
                    ficha.ocupacionjefehogar = ocupacion
                    ficha.val_ocupacionjefehogar = ocupacion.puntaje
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.ocupacionjefehogar.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'ocupacionjefehogarreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    ocupacion = OcupacionJefeHogar.objects.get(pk=request.POST['ocupacion'])
                    ficha.ocupacionjefehogar = ocupacion
                    ficha.val_ocupacionjefehogar = ocupacion.puntaje
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.ocupacionjefehogar.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'tipovivienda':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    tipovivienda = TipoVivienda.objects.get(pk=request.POST['tipovivienda'])
                    ficha.tipovivienda = tipovivienda
                    ficha.val_tipovivienda = tipovivienda.puntaje
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tipovivienda.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'tipoviviendareplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    tipovivienda = TipoVivienda.objects.get(pk=request.POST['tipovivienda'])
                    ficha.tipovivienda = tipovivienda
                    ficha.val_tipovivienda = tipovivienda.puntaje
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tipovivienda.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'tipoviviendapropia':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    tipoviviendapropia = TipoViviendaPro.objects.get(pk=request.POST['tipoviviendapropia'])
                    ficha.tipoviviendapro = tipoviviendapropia
                    #ficha.val_tipoviviendapropia = tipoviviendapropia.puntaje
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tipoviviendapro.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'tipoviviendapropiareplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    tipoviviendapropia = TipoViviendaPro.objects.get(pk=request.POST['tipoviviendapropia'])
                    ficha.tipoviviendapro = tipoviviendapropia
                    #ficha.val_tipoviviendapropia = tipoviviendapropia.puntaje
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tipoviviendapro.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'materialpared':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    materialpared = MaterialPared.objects.get(pk=request.POST['materialpared'])
                    ficha.materialpared = materialpared
                    ficha.val_materialpared = materialpared.puntaje
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.materialpared.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'materialparedreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    materialpared = MaterialPared.objects.get(pk=request.POST['materialpared'])
                    ficha.materialpared = materialpared
                    ficha.val_materialpared = materialpared.puntaje
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.materialpared.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'materialpiso':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    materialpiso = MaterialPiso.objects.get(pk=request.POST['materialpiso'])
                    ficha.materialpiso = materialpiso
                    ficha.val_materialpiso = materialpiso.puntaje
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.materialpiso.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'materialpisoreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    materialpiso = MaterialPiso.objects.get(pk=request.POST['materialpiso'])
                    ficha.materialpiso = materialpiso
                    ficha.val_materialpiso = materialpiso.puntaje
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.materialpiso.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'cantbannoducha':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    cantbannoducha = CantidadBannoDucha.objects.get(pk=request.POST['cantduchas'])
                    ficha.cantbannoducha = cantbannoducha
                    ficha.val_cantbannoducha = cantbannoducha.puntaje
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.cantbannoducha.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'cantbannoduchareplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    cantbannoducha = CantidadBannoDucha.objects.get(pk=request.POST['cantduchas'])
                    ficha.cantbannoducha = cantbannoducha
                    ficha.val_cantbannoducha = cantbannoducha.puntaje
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.cantbannoducha.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'tiposervhig':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    tiposervhig = TipoServicioHigienico.objects.get(pk=request.POST['tiposervh'])
                    ficha.tiposervhig = tiposervhig
                    ficha.val_tiposervhig = tiposervhig.puntaje
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tiposervhig.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'tiposervhigreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    tiposervhig = TipoServicioHigienico.objects.get(pk=request.POST['tiposervh'])
                    ficha.tiposervhig = tiposervhig
                    ficha.val_tiposervhig = tiposervhig.puntaje
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tiposervhig.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'canttvcolor':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    canttv = CantidadTVColorHogar.objects.get(pk=request.POST['canttv'])
                    ficha.canttvcolor = canttv
                    ficha.val_canttvcolor = canttv.puntaje
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.canttvcolor.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'canttvcolorreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    canttv = CantidadTVColorHogar.objects.get(pk=request.POST['canttv'])
                    ficha.canttvcolor = canttv
                    ficha.val_canttvcolor = canttv.puntaje
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.canttvcolor.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'cantvehiculos':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    cantveh = CantidadVehiculoHogar.objects.get(pk=request.POST['cantveh'])
                    ficha.cantvehiculos = cantveh
                    ficha.val_cantvehiculos = cantveh.puntaje
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.cantvehiculos.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'cantvehiculosreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    cantveh = CantidadVehiculoHogar.objects.get(pk=request.POST['cantveh'])
                    ficha.cantvehiculos = cantveh
                    ficha.val_cantvehiculos = cantveh.puntaje
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.cantvehiculos.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'cantcelulares':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    cantcel = CantidadCelularHogar.objects.get(pk=request.POST['cantcel'])
                    ficha.cantcelulares = cantcel
                    ficha.val_cantcelulares = cantcel.puntaje
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.cantcelulares.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'cantcelularesreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    cantcel = CantidadCelularHogar.objects.get(pk=request.POST['cantcel'])
                    ficha.cantcelulares = cantcel
                    ficha.val_cantcelulares = cantcel.puntaje
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.cantcelulares.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'proveedorinternet':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.proveedorinternet_id = request.POST['proveedorinternetid']
                    ficha.save()

                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.proveedorinternet.nombre}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'cantacthorashogar':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.horastareahogar = request.POST['canthogar']
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.horastareahogar}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'cantacthorashogarreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.horastareahogar = request.POST['canthogar']
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.horastareahogar}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'saveotrosrecursos':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.otrosrecursos = request.POST['otrorecurso']
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.otrosrecursos}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'saveotrosrecursosreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.otrosrecursos = request.POST['otrorecurso']
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.otrosrecursos}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'saveotrossector':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.otrossector = request.POST['otrosector']
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.otrossector}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'saveotrossectorreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.otrossector = request.POST['otrosector']
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.otrossector}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'saveotrasenfermedades':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.otrasenfermedades = request.POST['otraenfermedad']
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.otrasenfermedades}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'saveotrasenfermedadesreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.otrasenfermedades = request.POST['otraenfermedad']
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.otrasenfermedades}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'saveenfermedadescomunes':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.enfermedadescomunes = request.POST['enfermedadescomunes']
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.enfermedadescomunes}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'saveenfermedadescomunesreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.enfermedadescomunes = request.POST['enfermedadescomunes']
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.enfermedadescomunes}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'savetratamientomedico':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.tratamientomedico = request.POST['tratamientomedico']
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tratamientomedico}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'savetratamientomedicoreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.tratamientomedico = request.POST['tratamientomedico']
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.tratamientomedico}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'cantacthorasdomesticas':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.horastrabajodomestico = request.POST['cantdomesticas']
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.horastrabajodomestico}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'cantacthorasdomesticasreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.horastrabajodomestico = request.POST['cantdomesticas']
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.horastrabajodomestico}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'cantacthorastrabajofuera':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.horastrabajofuera = request.POST['canttrabajofuera']
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.horastrabajofuera}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'cantacthorastrabajofuerareplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.horastrabajofuera = request.POST['canttrabajofuera']
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.horastrabajofuera}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'datosdomicilio':
                try:
                    if 'archivocroquis' in request.FILES:
                        newfile = request.FILES['archivocroquis']
                        if newfile.size > 2194304:
                            return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")
                    persona = request.session['persona']
                    f = DatosDomicilioForm(request.POST)
                    if f.is_valid():
                        newfile = None
                        persona.pais = f.cleaned_data['pais']
                        persona.provincia = f.cleaned_data['provincia']
                        persona.canton = f.cleaned_data['canton']
                        persona.parroquia = f.cleaned_data['parroquia']
                        persona.direccion = f.cleaned_data['direccion']
                        persona.direccion2 = f.cleaned_data['direccion2']
                        persona.num_direccion = f.cleaned_data['num_direccion']
                        persona.telefono = f.cleaned_data['telefono']
                        persona.telefono_conv = f.cleaned_data['telefono_conv']
                        persona.referencia = f.cleaned_data['referencia']
                        persona.tipocelular = f.cleaned_data['tipocelular']
                        persona.save()
                        if 'archivocroquis' in request.FILES:
                            newfile = request.FILES['archivocroquis']
                            newfile._name = generar_nombre("croquis_", newfile._name)
                            persona.archivocroquis = newfile
                            persona.save()
                        log(u'Modifico datos de domicilio: %s' % persona, request, "edit")
                        return HttpResponse(json.dumps({'result': 'ok'}), content_type="application/json")
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

            elif action == 'editfamiliar':
                try:
                    persona = request.session['persona']
                    f = FamiliarForm(request.POST)
                    if f.is_valid():
                        familiar = PersonaDatosFamiliares.objects.get(pk=int(request.POST['id']))
                        if persona.personadatosfamiliares_set.filter(identificacion=f.cleaned_data['identificacion']).exclude(id=familiar.id).exists():
                            return HttpResponse(json.dumps({'result': 'bad', 'mensaje': u'El familiar se encuentra registrado.'}), content_type="application/json")
                        familiar.identificacion = f.cleaned_data['identificacion']
                        familiar.nombre = f.cleaned_data['nombre']
                        familiar.fallecido = f.cleaned_data['fallecido']
                        familiar.nacimiento = f.cleaned_data['nacimiento']
                        familiar.parentesco = f.cleaned_data['parentesco']
                        familiar.tienediscapacidad = f.cleaned_data['tienediscapacidad']
                        familiar.telefono = f.cleaned_data['telefono']
                        familiar.telefono_conv = f.cleaned_data['telefono_conv']
                        familiar.trabajo = f.cleaned_data['trabajo']
                        familiar.convive = f.cleaned_data['convive']
                        familiar.sustentohogar = f.cleaned_data['sustentohogar']
                        familiar.niveltitulacion = f.cleaned_data['niveltitulacion']
                        familiar.formatrabajo = f.cleaned_data['formatrabajo']
                        familiar.ingresomensual = f.cleaned_data['ingresomensual']
                        familiar.save()
                        log(u'Modifico familiar: %s' % persona, request, "edit")
                        return HttpResponse(json.dumps({'result': 'ok'}), content_type="application/json")
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({'result': 'bad', 'mensaje': u'Error al guardar los datos'}), content_type="application/json")

            elif action == 'addfamiliar':
                try:
                    persona = request.session['persona']
                    f = FamiliarForm(request.POST)
                    if f.is_valid():
                        if persona.personadatosfamiliares_set.filter(identificacion=f.cleaned_data['identificacion']).exists():
                            return HttpResponse(json.dumps({'result': 'bad', 'mensaje': u'El familiar se encuentra registrado.'}), content_type="application/json")
                        familiar = PersonaDatosFamiliares(persona=persona,
                                                          identificacion=f.cleaned_data['identificacion'],
                                                          nombre=f.cleaned_data['nombre'],
                                                          fallecido=f.cleaned_data['fallecido'],
                                                          nacimiento=f.cleaned_data['nacimiento'],
                                                          parentesco=f.cleaned_data['parentesco'],
                                                          tienediscapacidad=f.cleaned_data['tienediscapacidad'],
                                                          telefono=f.cleaned_data['telefono'],
                                                          telefono_conv=f.cleaned_data['telefono_conv'],
                                                          trabajo=f.cleaned_data['trabajo'],
                                                          convive=f.cleaned_data['convive'],
                                                          sustentohogar=f.cleaned_data['sustentohogar'],
                                                          niveltitulacion=f.cleaned_data['niveltitulacion'],
                                                          formatrabajo=f.cleaned_data['formatrabajo'],
                                                          ingresomensual=f.cleaned_data['ingresomensual'])
                        familiar.save()
                        log(u'Adiciono familiar: %s' % persona, request, "add")
                        return HttpResponse(json.dumps({'result': 'ok'}), content_type="application/json")
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({'result': 'bad', 'mensaje': u'Error al guardar los datos'}), content_type="application/json")

            elif action == 'delfamiliar':
                try:
                    persona = request.session['persona']
                    familiar = PersonaDatosFamiliares.objects.get(pk=int(request.POST['id']))
                    familiar.delete()
                    log(u'Elimino familiar: %s' % persona, request, "del")
                    return HttpResponse(json.dumps({'result': 'ok'}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({'result': 'bad', 'mensaje': u'Error al eliminar los datos'}), content_type="application/json")

            elif action == 'datosnacimiento':
                try:
                    persona = request.session['persona']
                    f = DatosNacimientoForm(request.POST)
                    if f.is_valid():
                        persona.paisnacimiento = f.cleaned_data['paisnacimiento']
                        persona.provincianacimiento = f.cleaned_data['provincianacimiento']
                        persona.cantonnacimiento = f.cleaned_data['cantonnacimiento']
                        persona.parroquianacimiento = f.cleaned_data['parroquianacimiento']
                        persona.save()
                        log(u'Modifico datos de nacimiento: %s' % persona, request, "edit")
                        return HttpResponse(json.dumps({'result': 'ok'}), content_type="application/json")
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({'result': 'bad', 'mensaje': u'Error al guardar los datos'}), content_type="application/json")

            elif action == 'discapacidad':
                try:
                    if 'archivocroquis' in request.FILES:
                        newfile = request.FILES['archivocroquis']
                        if newfile.size > 2194304:
                            return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")
                    persona = request.session['persona']
                    f = DiscapacidadForm(request.POST)
                    if f.is_valid():
                        newfile = None
                        perfil = persona.mi_perfil()
                        perfil.tienediscapacidad = f.cleaned_data['tienediscapacidad']
                        perfil.tipodiscapacidad = f.cleaned_data['tipodiscapacidad']
                        perfil.porcientodiscapacidad = f.cleaned_data['porcientodiscapacidad'] if f.cleaned_data['porcientodiscapacidad'] else 0
                        perfil.carnetdiscapacidad = f.cleaned_data['carnetdiscapacidad']
                        perfil.save()
                        if not f.cleaned_data['tienediscapacidad']:
                            perfil.archivo = None
                            perfil.save()
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("archivosdiscapacidad_", newfile._name)
                            perfil.archivo = newfile
                            perfil.save()
                        log(u'Modifico tipo de discapacidad: %s' % persona, request, "edit")
                        return HttpResponse(json.dumps({'result': 'ok'}), content_type="application/json")
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({'result': 'bad', 'mensaje': u'Error al guardar los datos'}), content_type="application/json")

            elif action == 'cantacthorashacertareas':
                try:
                    ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.horashacertareas = request.POST['canthacertareas']
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.horashacertareas}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            elif action == 'cantacthorashacertareasreplay':
                try:
                    ficha = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['fichaid'])
                    ficha.horashacertareas = request.POST['canthacertareas']
                    ficha.save()
                    return HttpResponse(json.dumps({'result': 'ok', 'valor': ficha.horashacertareas}), content_type="application/json")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

            return HttpResponseRedirect('/alu_socioecon')
        else:
            if 'action' in request.GET:
                action = request.GET['action']
                if action == 'datosdomicilio':
                    try:
                        data['title'] = u'Datos de domicilio'
                        form = DatosDomicilioForm(initial={'pais': persona.pais,
                                                           'provincia': persona.provincia,
                                                           'canton': persona.canton,
                                                           'parroquia': persona.parroquia,
                                                           'direccion': persona.direccion,
                                                           'direccion2': persona.direccion2,
                                                           'num_direccion': persona.num_direccion,
                                                           'referencia': persona.referencia,
                                                           'telefono': persona.telefono,
                                                           'telefono_conv': persona.telefono_conv,
                                                           'tipocelular': persona.tipocelular})
                        form.editar(persona)
                        data['form'] = form
                        return render(request, "alu_socioecon/datosdomicilio.html", data)
                    except:
                        pass

                if action == 'addfamiliar':
                    try:
                        data['title'] = u'Adicionar familiar'
                        data['form'] = FamiliarForm()
                        return render(request, "alu_socioecon/addfamiliar.html", data)
                    except:
                        pass

                if action == 'discapacidad':
                    try:
                        data['title'] = u'Discapacidad'
                        perfil = persona.mi_perfil()
                        form = DiscapacidadForm(initial={'tienediscapacidad': perfil.tienediscapacidad,
                                                         'tipodiscapacidad': perfil.tipodiscapacidad,
                                                         'porcientodiscapacidad': perfil.porcientodiscapacidad,
                                                         'carnetdiscapacidad': perfil.carnetdiscapacidad})
                        data['form'] = form
                        return render(request, "alu_socioecon/discapacidad.html", data)
                    except:
                        pass

                if action == 'delfamiliar':
                    try:
                        data['title'] = u'Eliminar familiar'
                        data['familiar'] = familiar = PersonaDatosFamiliares.objects.get(pk=int(request.GET['id']))
                        return render(request, "alu_socioecon/delfamiliar.html", data)
                    except:
                        pass

                if action == 'datospersonales':
                    try:
                        data['title'] = u'Datos personales'
                        personabd=Persona.objects.get(id=persona.id)
                        form = DatosPersonalesForm(initial={'nombres': personabd.nombres,
                                                            'apellido1': personabd.apellido1,
                                                            'apellido2': personabd.apellido2,
                                                            'cedula': personabd.cedula,
                                                            'pasaporte': personabd.pasaporte,
                                                            'sexo': personabd.sexo,
                                                            'lgtbi': personabd.lgtbi,
                                                            'anioresidencia': personabd.anioresidencia,
                                                            'nacimiento': personabd.nacimiento,
                                                            'nacionalidad': personabd.nacionalidad,
                                                            'email': personabd.email,
                                                            'estadocivil': personabd.estado_civil(),
                                                            'libretamilitar': personabd.libretamilitar})
                        form.editar()
                        data['form'] = form
                        return render(request, "alu_socioecon/datospersonales.html", data)
                    except:
                        pass

                elif action == 'pdf':
                    data = {}
                    adduserdata(request, data)
                    data['personaficha'] = persona = Persona.objects.get(pk=request.GET['id'])
                    data['ficha'] = persona.mi_ficha()
                    data['perfilinscripcion'] = PerfilInscripcion.objects.get(persona=persona)
                    if FotoPersona.objects.filter(persona=request.GET['id']).exists():
                        data['fotopersona'] = FotoPersona.objects.get(persona=request.GET['id'])
                    data['form_sustento'] = SustentoHogarForm(initial={'ingresomensual': 0.00})
                    data['form_tipohogar'] = TipoHogarForm()
                    data['form_personacubregasto'] = PersonaCubreGastoForm()
                    data['form_tipoactividad'] = PersonaActRecreacionForm()
                    data['form_lugartarea'] = PersonaLugarTareaForm()
                    data['form_salubridadvida'] = PersonaSalubridadVidaForm()
                    data['form_estadogeneral'] = PersonaEstadoGeneralForm()
                    data['personacubregasto_otros_id'] = 7
                    data['tipoactividad_otros_id'] = 7
                    data['tipotarea_otros_id'] = 8
                    data['form_niveljefehogar'] = NivelEstudioForm()
                    data['form_ocupacionjefehogar'] = OcupacionJefeHogarForm()
                    data['form_tipovivienda'] = TipoViviendaForm()
                    data['form_tipoviviendapro'] = TipoViviendaproForm()
                    data['form_materialpared'] = MaterialParedForm()
                    data['form_materialpiso'] = MaterialPisoForm()
                    data['form_cantbannoducha'] = CantidadBannoDuchaForm()
                    data['form_tiposervhig'] = TipoServicioHigienicoForm()
                    data['form_canttvcolor'] = CantidadTVColorHogarForm()
                    data['form_cantvehiculos'] = CantidadVehiculoHogarForm()
                    data['form_cantcelulares'] = CantidadCelularHogarForm()
                    periodo = request.session['periodo']
                    matricula = Matricula.objects.filter(inscripcion_id=request.GET['idins'], nivel__periodo=periodo)
                    validamaterias = 0
                    if matricula.exists():
                        validamaterias = 1
                        data['idmatricula'] = matricula[0]
                        data['materias'] = materias = matricula[0].materiaasignada_set.all()
                        data['nivelacademico'] = InscripcionNivel.objects.get(inscripcion_id=request.GET['idins'])
                    data['validamaterias'] = validamaterias
                    return conviert_html_to_pdf(
                        'alu_socioecon/ficha_pdf.html',
                        {
                            'pagesize': 'A4',
                            'listadoficha': data,
                        }
                    )


                if action == 'editfamiliar':
                    try:
                        data['title'] = u'Editar familiar'
                        data['familiar'] = familiar = PersonaDatosFamiliares.objects.get(pk=int(request.GET['id']))
                        data['form'] = FamiliarForm(initial={'identificacion': familiar.identificacion,
                                                             'parentesco': familiar.parentesco,
                                                             'nombre': familiar.nombre,
                                                             'nacimiento': familiar.nacimiento,
                                                             'fallecido': familiar.fallecido,
                                                             'tienediscapacidad': familiar.tienediscapacidad,
                                                             'telefono': familiar.telefono,
                                                             'telefono_conv': familiar.telefono_conv,
                                                             'trabajo': familiar.trabajo,
                                                             'convive': familiar.convive,
                                                             'sustentohogar': familiar.sustentohogar,
                                                             'niveltitulacion': familiar.niveltitulacion,
                                                             'formatrabajo': familiar.formatrabajo,
                                                             'ingresomensual': familiar.ingresomensual})
                        return render(request, "alu_socioecon/editfamiliar.html", data)
                    except:
                        pass

                if action == 'datosnacimiento':
                    try:
                        data['title'] = u'Datos de nacimiento'
                        form = DatosNacimientoForm(initial={'paisnacimiento': persona.paisnacimiento,
                                                            'provincianacimiento': persona.provincianacimiento,
                                                            'cantonnacimiento': persona.cantonnacimiento,
                                                            'parroquianacimiento': persona.parroquianacimiento})
                        form.editar(persona)
                        data['form'] = form
                        return render(request, "alu_socioecon/datosnacimiento.html", data)
                    except:
                        pass

                if action == 'delsustento':
                    try:
                        sustento = PersonaSustentaHogar.objects.get(pk=request.GET['id'])
                        sustento.delete()
                    except Exception as ex:
                        transaction.set_rollback(True)
                    return HttpResponseRedirect("/alu_socioecon")

                return HttpResponseRedirect(request.path)
            else:
                if persona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1,status=True):
                    if not persona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1,status=True)[0].confirmar:
                        data['title'] = u'Ficha socioeconomica del estudiante'
                        data['inscripcion'] = inscripcion
                        data['ficha'] = persona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1,status=True)[0]
                        data['perfil'] = persona.mi_perfil()
                        if persona.tipocelular == 0:
                            data['tipocelular'] = '-'
                        else:
                            data['tipocelular'] = TIPO_CELULAR[int(persona.tipocelular) - 1][1]
                        data['form_sustento'] = SustentoHogarForm(initial={'ingresomensual': 0.00})
                        data['form_tipohogar'] = TipoHogarForm()
                        data['form_personacubregasto'] = PersonaCubreGastoForm()
                        data['form_tipoactividad'] = PersonaActRecreacionForm()
                        data['form_lugartarea'] = PersonaLugarTareaForm()
                        data['form_salubridadvida'] = PersonaSalubridadVidaForm()
                        data['form_estadogeneral'] = PersonaEstadoGeneralForm()
                        data['personacubregasto_otros_id'] = 7
                        data['tipoactividad_otros_id'] = 7
                        data['tipotarea_otros_id'] = 8
                        data['form_niveljefehogar'] = NivelEstudioForm()
                        data['form_ocupacionjefehogar'] = OcupacionJefeHogarForm()
                        data['form_tipovivienda'] = TipoViviendaForm()
                        data['form_tipoviviendapro'] = TipoViviendaproForm()
                        data['form_materialpared'] = MaterialParedForm()
                        data['form_materialpiso'] = MaterialPisoForm()
                        data['form_cantbannoducha'] = CantidadBannoDuchaForm()
                        data['form_tiposervhig'] = TipoServicioHigienicoForm()
                        data['form_canttvcolor'] = CantidadTVColorHogarForm()
                        data['form_cantvehiculos'] = CantidadVehiculoHogarForm()
                        data['form_cantcelulares'] = CantidadCelularHogarForm()
                        return render(request, "alu_socioecon/fichareplay.html", data)

                if not persona.fichasocioeconomicainec_set.filter(status=True)[0].confirmar: # produccion

                # if persona.fichasocioeconomicainec_set.filter(status=True): # pruebas
                    data['title'] = u'Ficha socioeconomica del estudiante'
                    data['inscripcion'] = inscripcion
                    data['ficha'] = persona.mi_ficha()
                    data['perfil'] = persona.mi_perfil()
                    if persona.tipocelular == 0:
                        data['tipocelular'] = '-'
                    else:
                        data['tipocelular'] =  TIPO_CELULAR[int(persona.tipocelular) - 1][1]
                    data['form_sustento'] = SustentoHogarForm(initial={'ingresomensual': 0.00})
                    data['form_tipohogar'] = TipoHogarForm()
                    data['form_personacubregasto'] = PersonaCubreGastoForm()
                    data['form_tipoactividad'] = PersonaActRecreacionForm()
                    data['form_lugartarea'] = PersonaLugarTareaForm()
                    data['form_salubridadvida'] = PersonaSalubridadVidaForm()
                    data['form_estadogeneral'] = PersonaEstadoGeneralForm()
                    data['personacubregasto_otros_id'] = 7
                    data['tipoactividad_otros_id'] = 7
                    data['tipotarea_otros_id'] = 8
                    data['form_niveljefehogar'] = NivelEstudioForm()
                    data['form_ocupacionjefehogar'] = OcupacionJefeHogarForm()
                    data['form_tipovivienda'] = TipoViviendaForm()
                    data['form_tipoviviendapro'] = TipoViviendaproForm()
                    data['form_materialpared'] = MaterialParedForm()
                    data['form_materialpiso'] = MaterialPisoForm()
                    data['form_cantbannoducha'] = CantidadBannoDuchaForm()
                    data['form_tiposervhig'] = TipoServicioHigienicoForm()
                    data['form_canttvcolor'] = CantidadTVColorHogarForm()
                    data['form_cantvehiculos'] = CantidadVehiculoHogarForm()
                    data['form_cantcelulares'] = CantidadCelularHogarForm()
                    data['form_proveedorinternet'] = ProveedorInternetForm()
                    data['form_nuevoproveedor'] = AgregarProveedorInternet()

                    return render(request, "alu_socioecon/ficha.html", data)
                else:
                    return HttpResponseRedirect(u"/?info=Usted ya ha confirmado sus datos en la ficha Socia Económica.")
    else:
        return HttpResponseRedirect("/?info=Usted no pertenece al grupo de estudiantes.")