# -*- coding: UTF-8 -*-
import random
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
import xlwt
from xlwt import *

from decorators import secure_module, last_access
from sagest.forms import FamiliarForm, DiscapacidadForm, DatosNacimientoForm, DatosDomicilioForm
from settings import ALUMNOS_GROUP_ID
from sga.commonviews import adduserdata
from sga.forms import DobeInscripcionForm
from sga.funciones import MiPaginador, log, generar_nombre
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import Inscripcion, PerfilInscripcion, Persona, ParentescoPersona, Matricula, InscripcionNivel, \
    FotoPersona, TIPO_CELULAR, PersonaDatosFamiliares
from socioecon.forms import SustentoHogarForm, TipoHogarForm, PersonaCubreGastoForm, NivelEstudioForm, \
    OcupacionJefeHogarForm, TipoViviendaForm, MaterialParedForm, MaterialPisoForm, CantidadBannoDuchaForm, \
    TipoServicioHigienicoForm, CantidadTVColorHogarForm, CantidadVehiculoHogarForm, CantidadCelularHogarForm, \
    PersonaLugarTareaForm, PersonaSalubridadVidaForm, PersonaEstadoGeneralForm, PersonaActRecreacionForm, \
    TipoViviendaproForm
from socioecon.models import FichaSocioeconomicaINEC, CantidadCelularHogar, CantidadVehiculoHogar, CantidadTVColorHogar, \
    TipoServicioHigienico, CantidadBannoDucha, MaterialPiso, MaterialPared, TipoVivienda, OcupacionJefeHogar, \
    NivelEstudio, PersonaSustentaHogar, FormaTrabajo, PersonaCubreGasto, TipoHogar, TipoViviendaPro, \
    ACTIVIDADES_RECREACION, REALIZA_TAREAS, SALUBRIDAD_VIDA, ESTADO_GENERAL, FichaSocioeconomicaReplayINEC


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                f = DobeInscripcionForm(request.POST)
                if f.is_valid():
                    perfil = PerfilInscripcion(persona=inscripcion.persona,
                                               raza=f.cleaned_data['raza'],
                                               estrato=f.cleaned_data['estrato'],
                                               tienediscapacidad=f.cleaned_data['tienediscapacidad'],
                                               porcientodiscapacidad=f.cleaned_data['porcientodiscapacidad'],
                                               carnetdiscapacidad=f.cleaned_data['carnetdiscapacidad'])
                    perfil.save(request)
                    log(u'Adiciono perfil de inscripcion: %s' % perfil, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                perfil = PerfilInscripcion.objects.get(pk=request.POST['id'])
                f = DobeInscripcionForm(request.POST)
                if f.is_valid():
                    perfil.raza = f.cleaned_data['raza']
                    perfil.tienediscapacidad = f.cleaned_data['tienediscapacidad']
                    if f.cleaned_data['tienediscapacidad']:
                        perfil.tipodiscapacidad = f.cleaned_data['tipodiscapacidad']
                        perfil.porcientodiscapacidad = f.cleaned_data['porcientodiscapacidad']
                        perfil.carnetdiscapacidad = f.cleaned_data['carnetdiscapacidad']
                    else:
                        perfil.tipodiscapacidad = None
                        perfil.porcientodiscapacidad = 0
                        perfil.carnetdiscapacidad = ''
                    perfil.save(request)
                    log(u'Edito perfil de inscripcion: %s' % perfil, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'copypasteficha':
            try:
                if not FichaSocioeconomicaReplayINEC.objects.filter(persona_id=request.POST['idficha']).exists():
                    mificha = FichaSocioeconomicaINEC.objects.get(persona_id=request.POST['idficha'])
                    mifichareply = FichaSocioeconomicaReplayINEC(persona=mificha.persona,
                                                                 puntajetotal=mificha.puntajetotal,
                                                                 grupoeconomico=mificha.grupoeconomico,
                                                                 tipohogar=mificha.tipohogar,
                                                                 escabezafamilia=mificha.escabezafamilia,
                                                                 esdependiente=mificha.esdependiente,
                                                                 personacubregasto=mificha.personacubregasto,
                                                                 otroscubregasto=mificha.otroscubregasto,
                                                                 tipovivienda=mificha.tipovivienda,
                                                                 val_tipovivienda =mificha.val_tipovivienda ,
                                                                 materialpared =mificha.materialpared ,
                                                                 val_materialpared =mificha.val_materialpared ,
                                                                 materialpiso =mificha.materialpiso ,
                                                                 val_materialpiso=mificha.val_materialpiso,
                                                                 cantbannoducha=mificha.cantbannoducha,
                                                                 val_cantbannoducha=mificha.val_cantbannoducha,
                                                                 tiposervhig =mificha.tiposervhig ,
                                                                 val_tiposervhig =mificha.val_tiposervhig ,
                                                                 tieneinternet =mificha.tieneinternet ,
                                                                 val_tieneinternet =mificha.val_tieneinternet ,
                                                                 tienedesktop =mificha.tienedesktop ,
                                                                 val_tienedesktop =mificha.val_tienedesktop ,
                                                                 tienelaptop =mificha.tienelaptop ,
                                                                 val_tienelaptop=mificha.val_tienelaptop,
                                                                 cantcelulares =mificha.cantcelulares ,
                                                                 val_cantcelulares =mificha.val_cantcelulares ,
                                                                 tienetelefconv =mificha.tienetelefconv ,
                                                                 val_tienetelefconv =mificha.val_tienetelefconv ,
                                                                 tienecocinahorno =mificha.tienecocinahorno ,
                                                                 val_tienecocinahorno =mificha.val_tienecocinahorno ,
                                                                 tienerefrig=mificha.tienerefrig,
                                                                 val_tienerefrig =mificha.val_tienerefrig ,
                                                                 tienelavadora =mificha.tienelavadora ,
                                                                 val_tienelavadora =mificha.val_tienelavadora ,
                                                                 tienemusica =mificha.tienemusica ,
                                                                 val_tienemusica =mificha.val_tienemusica ,
                                                                 canttvcolor =mificha.canttvcolor ,
                                                                 val_canttvcolor =mificha.val_canttvcolor ,
                                                                 cantvehiculos =mificha.cantvehiculos ,
                                                                 val_cantvehiculos =mificha.val_cantvehiculos ,
                                                                 compravestcc=mificha.compravestcc,
                                                                 val_compravestcc =mificha.val_compravestcc ,
                                                                 usainternetseism =mificha.usainternetseism ,
                                                                 val_usainternetseism=mificha.val_usainternetseism,
                                                                 usacorreonotrab =mificha.usacorreonotrab ,
                                                                 val_usacorreonotrab =mificha.val_usacorreonotrab ,
                                                                 registroredsocial =mificha.registroredsocial ,
                                                                 val_registroredsocial =mificha.val_registroredsocial ,
                                                                 leidolibrotresm =mificha.leidolibrotresm ,
                                                                 val_leidolibrotresm=mificha.val_leidolibrotresm,
                                                                 niveljefehogar =mificha.niveljefehogar ,
                                                                 val_niveljefehogar=mificha.val_niveljefehogar,
                                                                 alguienafiliado=mificha.alguienafiliado,
                                                                 val_alguienafiliado =mificha.val_alguienafiliado ,
                                                                 alguienseguro =mificha.alguienseguro ,
                                                                 val_alguienseguro=mificha.val_alguienseguro,
                                                                 ocupacionjefehogar=mificha.ocupacionjefehogar,
                                                                 val_ocupacionjefehogar =mificha.val_ocupacionjefehogar ,
                                                                 tipoviviendapro =mificha.tipoviviendapro ,
                                                                 tienesala =mificha.tienesala ,
                                                                 tienecomedor =mificha.tienecomedor ,
                                                                 tienecocina =mificha.tienecocina ,
                                                                 tienebanio =mificha.tienebanio ,
                                                                 tieneluz=mificha.tieneluz,
                                                                 tieneagua=mificha.tieneagua,
                                                                 tienetelefono =mificha.tienetelefono ,
                                                                 tienealcantarilla=mificha.tienealcantarilla,
                                                                 horastareahogar=mificha.horastareahogar,
                                                                 horastrabajodomestico=mificha.horastrabajodomestico,
                                                                 horastrabajofuera =mificha.horastrabajofuera ,
                                                                 tipoactividad=mificha.tipoactividad,
                                                                 otrosactividad =mificha.otrosactividad ,
                                                                 horashacertareas =mificha.horashacertareas ,
                                                                 tipotarea =mificha.tipotarea ,
                                                                 otrostarea =mificha.otrostarea ,
                                                                 tienefolleto =mificha.tienefolleto ,
                                                                 tienecomputador =mificha.tienecomputador ,
                                                                 tieneenciclopedia =mificha.tieneenciclopedia ,
                                                                 tienecyber =mificha.tienecyber ,
                                                                 tienebiblioteca =mificha.tienebiblioteca ,
                                                                 tienemuseo =mificha.tienemuseo ,
                                                                 tienearearecreacion=mificha.tienearearecreacion,
                                                                 otrosrecursos =mificha.otrosrecursos ,
                                                                 otrossector =mificha.otrossector ,
                                                                 tienediabetes =mificha.tienediabetes ,
                                                                 tienehipertencion =mificha.tienehipertencion ,
                                                                 tieneparkinson =mificha.tieneparkinson ,
                                                                 tienecancer =mificha.tienecancer ,
                                                                 tienealzheimer =mificha.tienealzheimer ,
                                                                 tienevitiligo =mificha.tienevitiligo ,
                                                                 tienedesgastamiento =mificha.tienedesgastamiento ,
                                                                 tienepielblanca=mificha.tienepielblanca,
                                                                 otrasenfermedades=mificha.otrasenfermedades,
                                                                 tienesida =mificha.tienesida ,
                                                                 enfermedadescomunes=mificha.enfermedadescomunes,
                                                                 salubridadvida =mificha.salubridadvida ,
                                                                 estadogeneral =mificha.estadogeneral ,
                                                                 tratamientomedico =mificha.tratamientomedico ,
                                                                 confirmar=False)
                    mifichareply.save(request)
                    mificha.confirmar=False
                    mificha.save(request)
                    log(u'Adicionó copia ficha: %s' % mifichareply, request,"add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Ya ficha socioeconomia esta ingresado."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'apruebasolicitudficha':
            try:
                mifichareply = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['idficha'])
                mifichareply.personaaprueba = request.session['persona']
                mifichareply.obseaprueba = request.POST['observacion']
                mifichareply.estadosolicitud = 2
                mifichareply.save(request)
                mificha = FichaSocioeconomicaINEC.objects.get(persona=mifichareply.persona, status=True)
                mificha.puntajetotal = mifichareply.puntajetotal
                mificha.grupoeconomico_id = mifichareply.grupoeconomico_id
                mificha.tipohogar = mifichareply.tipohogar
                mificha.escabezafamilia = mifichareply.escabezafamilia
                mificha.esdependiente = mifichareply.esdependiente
                mificha.personacubregasto_id = mifichareply.personacubregasto_id
                mificha.otroscubregasto = mifichareply.otroscubregasto.upper() if mifichareply.otroscubregasto else ''
                mificha.tipovivienda_id = mifichareply.tipovivienda_id
                mificha.val_tipovivienda = mifichareply.val_tipovivienda
                mificha.materialpared_id = mifichareply.materialpared_id
                mificha.val_materialpared = mifichareply.val_materialpared
                mificha.materialpiso_id = mifichareply.materialpiso_id
                mificha.val_materialpiso = mifichareply.val_materialpiso
                mificha.cantbannoducha_id = mifichareply.cantbannoducha_id
                mificha.val_cantbannoducha = mifichareply.val_cantbannoducha
                mificha.tiposervhig_id = mifichareply.tiposervhig_id
                mificha.val_tiposervhig = mifichareply.val_tiposervhig
                mificha.tieneinternet = mifichareply.tieneinternet
                mificha.val_tieneinternet = mifichareply.val_tieneinternet
                mificha.tienedesktop = mifichareply.tienedesktop
                mificha.val_tienedesktop = mifichareply.val_tienedesktop
                mificha.tienelaptop = mifichareply.tienelaptop
                mificha.val_tienelaptop = mifichareply.val_tienelaptop
                mificha.cantcelulares_id = mifichareply.cantcelulares_id
                mificha.val_cantcelulares = mifichareply.val_cantcelulares
                mificha.tienetelefconv = mifichareply.tienetelefconv
                mificha.val_tienetelefconv = mifichareply.val_tienetelefconv
                mificha.tienecocinahorno = mifichareply.tienecocinahorno
                mificha.val_tienecocinahorno = mifichareply.val_tienecocinahorno
                mificha.tienerefrig = mifichareply.tienerefrig
                mificha.val_tienerefrig = mifichareply.val_tienerefrig
                mificha.tienelavadora = mifichareply.tienelavadora
                mificha.val_tienelavadora = mifichareply.val_tienelavadora
                mificha.tienemusica = mifichareply.tienemusica
                mificha.val_tienemusica = mifichareply.val_tienemusica
                mificha.canttvcolor_id = mifichareply.canttvcolor_id
                mificha.val_canttvcolor = mifichareply.val_canttvcolor
                mificha.cantvehiculos_id = mifichareply.cantvehiculos_id
                mificha.val_cantvehiculos = mifichareply.val_cantvehiculos
                mificha.compravestcc = mifichareply.compravestcc
                mificha.val_compravestcc = mifichareply.val_compravestcc
                mificha.usainternetseism = mifichareply.usainternetseism
                mificha.val_usainternetseism = mifichareply.val_usainternetseism
                mificha.usacorreonotrab = mifichareply.usacorreonotrab
                mificha.val_usacorreonotrab = mifichareply.val_usacorreonotrab
                mificha.registroredsocial = mifichareply.registroredsocial
                mificha.val_registroredsocial = mifichareply.val_registroredsocial
                mificha.leidolibrotresm = mifichareply.leidolibrotresm
                mificha.val_leidolibrotresm = mifichareply.val_leidolibrotresm
                mificha.niveljefehogar_id = mifichareply.niveljefehogar_id
                mificha.val_niveljefehogar = mifichareply.val_niveljefehogar
                mificha.alguienafiliado = mifichareply.alguienafiliado
                mificha.val_alguienafiliado = mifichareply.val_alguienafiliado
                mificha.alguienseguro = mifichareply.alguienseguro
                mificha.val_alguienseguro = mifichareply.val_alguienseguro
                mificha.ocupacionjefehogar_id = mifichareply.ocupacionjefehogar_id
                mificha.val_ocupacionjefehogar = mifichareply.val_ocupacionjefehogar
                mificha.tipoviviendapro_id = mifichareply.tipoviviendapro_id
                mificha.tienesala = mifichareply.tienesala
                mificha.tienecomedor = mifichareply.tienecomedor
                mificha.tienecocina = mifichareply.tienecocina
                mificha.tienebanio = mifichareply.tienebanio
                mificha.tieneluz = mifichareply.tieneluz
                mificha.tieneagua = mifichareply.tieneagua
                mificha.tienetelefono = mifichareply.tienetelefono
                mificha.tienealcantarilla = mifichareply.tienealcantarilla
                mificha.horastareahogar = mifichareply.horastareahogar
                mificha.horastrabajodomestico = mifichareply.horastrabajodomestico
                mificha.horastrabajofuera = mifichareply.horastrabajofuera
                mificha.tipoactividad = mifichareply.tipoactividad
                mificha.otrosactividad = mifichareply.otrosactividad
                mificha.horashacertareas = mifichareply.horashacertareas
                mificha.tipotarea = mifichareply.tipotarea
                mificha.otrostarea = mifichareply.otrostarea
                mificha.tienefolleto = mifichareply.tienefolleto
                mificha.tienecomputador = mifichareply.tienecomputador
                mificha.tieneenciclopedia = mifichareply.tieneenciclopedia
                mificha.tienecyber = mifichareply.tienecyber
                mificha.tienebiblioteca = mifichareply.tienebiblioteca
                mificha.tienemuseo = mifichareply.tienemuseo
                mificha.tienearearecreacion = mifichareply.tienearearecreacion
                mificha.otrosrecursos = mifichareply.otrosrecursos
                mificha.otrossector = mifichareply.otrossector
                mificha.tienediabetes = mifichareply.tienediabetes
                mificha.tienehipertencion = mifichareply.tienehipertencion
                mificha.tieneparkinson = mifichareply.tieneparkinson
                mificha.tienecancer = mifichareply.tienecancer
                mificha.tienealzheimer = mifichareply.tienealzheimer
                mificha.tienevitiligo = mifichareply.tienevitiligo
                mificha.tienedesgastamiento = mifichareply.tienedesgastamiento
                mificha.tienepielblanca = mifichareply.tienepielblanca
                mificha.otrasenfermedades = mifichareply.otrasenfermedades
                mificha.tienesida = mifichareply.tienesida
                mificha.enfermedadescomunes = mifichareply.enfermedadescomunes
                mificha.salubridadvida = mifichareply.salubridadvida
                mificha.estadogeneral = mifichareply.estadogeneral
                mificha.tratamientomedico = mifichareply.tratamientomedico
                mificha.confirmar = True
                mificha.save(request)
                log(u'Aprobo solicitud ficha: %s' % mifichareply, request,"add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'rechazasolicitudficha':
            try:
                mifichareply = FichaSocioeconomicaReplayINEC.objects.get(pk=request.POST['idficha'])
                mifichareply.personaaprueba = request.session['persona']
                mifichareply.obseaprueba = request.POST['observacion']
                mifichareply.estadosolicitud = 3
                mifichareply.save(request)
                log(u'Rechazo solicitud ficha: %s' % mifichareply, request,"add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'changeescabezafamilia':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.escabezafamilia:
                    ficha.escabezafamilia = False
                else:
                    ficha.escabezafamilia = True
                ficha.save(request)
                log(u'Cambio cabeza familia en ficha socioeconomica INEC: %s - %s' % (ficha,ficha.escabezafamilia), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.escabezafamilia})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changeesdependiente':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.esdependiente:
                    ficha.esdependiente = False
                else:
                    ficha.esdependiente = True
                ficha.save(request)
                log(u'Cambio de dependencia en ficha socioeconomica INEC: %s - %s' % (ficha,ficha.esdependiente), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.esdependiente})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'tipohogar':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                th = TipoHogar.objects.get(pk=request.POST['th'])
                ficha.tipohogar = th
                ficha.save(request)
                log(u'Edito tipo de hogar en ficha socioeconomica INEC: %s - %s' % (ficha,ficha.tipohogar), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tipohogar.nombre})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'tiporecreacion':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                otrosg = request.POST['otrosg']
                ficha.tipoactividad = request.POST['codigoact']
                ficha.otrosactividad = request.POST['otrosg']
                ficha.save(request)
                valor = ACTIVIDADES_RECREACION[int(ficha.tipoactividad) - 1][1]
                log(u'Edito tipo de recreacion en ficha socioeconomica INEC: %s - %s' % (ficha,ficha.tipoactividad), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'tipolugartareas':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                otrosg = request.POST['otroslugartarea']
                ficha.tipotarea = request.POST['codigolugtarea']
                ficha.otrostarea = request.POST['otroslugartarea']
                ficha.save(request)
                valor = REALIZA_TAREAS[int(ficha.tipotarea) - 1][1]
                log(u'Edito tipo de lugares tareas en ficha socioeconomica INEC: %s - %s' % (ficha,ficha.tipotarea), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'salubridad':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                ficha.salubridadvida = request.POST['codigosalubridad']
                ficha.save(request)
                valor = SALUBRIDAD_VIDA[int(ficha.salubridadvida) - 1][1]
                log(u'Edito saludbrida de vida en ficha socioeconomica INEC: %s - %s' % (ficha,ficha.salubridadvida), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'estadogeneral':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                ficha.estadogeneral = request.POST['codigoestadogeneral']
                ficha.save(request)
                valor = ESTADO_GENERAL[int(ficha.estadogeneral) - 1][1]
                log(u'Edito estado general en ficha socioeconomica INEC: %s - %s' % (ficha,ficha.estadogeneral), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'personacubregasto':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                pcg = PersonaCubreGasto.objects.get(pk=request.POST['pcg'])
                otrosg = request.POST['otrosg']
                ficha.personacubregasto = pcg
                ficha.otroscubregasto = otrosg
                ficha.save(request)
                log(u'Edito persona cubre gastos en ficha socioeconomica INEC: %s - %s' % (ficha,ficha.personacubregasto), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.personacubregasto.nombre})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addsustentohogar':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                persona = request.POST['persona']
                formatrabajo = FormaTrabajo.objects.get(pk=int(request.POST['ft']))
                parentesco = ParentescoPersona.objects.get(pk=int(request.POST['parentesco']))
                ingresomensual = float(request.POST['im'])
                sustento = PersonaSustentaHogar(persona=persona,
                                                parentesco=parentesco,
                                                formatrabajo=formatrabajo,
                                                ingresomensual=ingresomensual)
                sustento.save(request)
                ficha.sustentahogar.add(sustento)
                ficha.save(request)
                log(u'Edito sustento de hogar en ficha socioeconomica INEC: %s - %s' % (ficha,ficha.sustentahogar), request, "edit")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changealguienafiliado':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.alguienafiliado:
                    ficha.alguienafiliado = False
                    ficha.val_alguienafiliado = 0
                else:
                    ficha.alguienafiliado = True
                    ficha.val_alguienafiliado = 39
                ficha.save(request)
                log(u'Cambio alguien afiliado en ficha socioeconomica INEC: %s - %s' % (ficha,ficha.val_alguienafiliado), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.alguienafiliado})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changealguienseguro':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.alguienseguro:
                    ficha.alguienseguro = False
                    ficha.val_alguienseguro = 0
                else:
                    ficha.alguienseguro = True
                    ficha.val_alguienseguro = 55
                ficha.save(request)
                log(u'Cambio alguien seguro en ficha socioeconomica INEC: %s - %s' % (ficha,ficha.val_alguienseguro), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.alguienseguro})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changecompravestcc':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.compravestcc:
                    ficha.compravestcc = False
                    ficha.val_compravestcc = 0
                else:
                    ficha.compravestcc = True
                    ficha.val_compravestcc = 6
                ficha.save(request)
                log(u'Cambio de compra de vestuario en ficha socioeconomica INEC: %s - %s' % (ficha,ficha.val_compravestcc), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.compravestcc})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changeusainternetseism':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.usainternetseism:
                    ficha.usainternetseism = False
                    ficha.val_usainternetseism = 0
                else:
                    ficha.usainternetseism = True
                    ficha.val_usainternetseism = 26
                ficha.save(request)
                log(u'Cambio en usa internet en ficha socioeconomica INEC: %s - %s' % (ficha,ficha.val_usainternetseism), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.usainternetseism})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changeusacorreonotrab':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.usacorreonotrab:
                    ficha.usacorreonotrab = False
                    ficha.val_usacorreonotrab = 0
                else:
                    ficha.usacorreonotrab = True
                    ficha.val_usacorreonotrab = 27
                ficha.save(request)
                log(u'Cambio en usa correo no trabajo en ficha socioeconomica INEC: %s - %s' % (ficha,ficha.val_usacorreonotrab), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.usacorreonotrab})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changeregistroredsocial':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.registroredsocial:
                    ficha.registroredsocial = False
                    ficha.val_registroredsocial = 0
                else:
                    ficha.registroredsocial = True
                    ficha.val_registroredsocial = 28
                ficha.save(request)
                log(u'Cambio en registro red social en ficha socioeconomica INEC: %s - %s' % (ficha,ficha.val_registroredsocial), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.registroredsocial})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changeleidolibrotresm':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.leidolibrotresm:
                    ficha.leidolibrotresm = False
                    ficha.val_leidolibrotresm = 0
                else:
                    ficha.leidolibrotresm = True
                    ficha.val_leidolibrotresm = 12
                ficha.save(request)
                log(u'Cambio en leido libro en ficha socioeconomica INEC: %s - %s' % (ficha,ficha.val_leidolibrotresm), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.leidolibrotresm})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienetelefconv':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienetelefconv:
                    ficha.tienetelefconv = False
                    ficha.val_tienetelefconv = 0
                else:
                    ficha.tienetelefconv = True
                    ficha.val_tienetelefconv = 19
                ficha.save(request)
                log(u'Cambio en tiene telefono convencional en ficha socioeconomica INEC: %s - %s' % (ficha,ficha.val_tienetelefconv), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienetelefconv})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienecocinahorno':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienecocinahorno:
                    ficha.tienecocinahorno = False
                    ficha.val_tienecocinahorno = 0
                else:
                    ficha.tienecocinahorno = True
                    ficha.val_tienecocinahorno = 29
                ficha.save(request)
                log(u'Edito tiene cocina con horno en ficha socioeconomica INEC: %s - %s' % (ficha,ficha.val_tienecocinahorno), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienecocinahorno})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienerefrig':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienerefrig:
                    ficha.tienerefrig = False
                    ficha.val_tienerefrig = 0
                else:
                    ficha.tienerefrig = True
                    ficha.val_tienerefrig = 30
                ficha.save(request)
                log(u'Edito tiene refrigeradora en ficha socioeconomica INEC: %s - %s' % (ficha,ficha.val_tienerefrig), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienerefrig})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienelavadora':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienelavadora:
                    ficha.tienelavadora = False
                    ficha.val_tienelavadora = 0
                else:
                    ficha.tienelavadora = True
                    ficha.val_tienelavadora = 18
                ficha.save(request)
                log(u'Edito tiene labadora en ficha socioeconomica INEC: %s - %s' % (ficha,ficha.val_tienelavadora), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienelavadora})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienemusica':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienemusica:
                    ficha.tienemusica = False
                    ficha.val_tienemusica = 0
                else:
                    ficha.tienemusica = True
                    ficha.val_tienemusica = 18
                ficha.save(request)
                log(u'Edito tiene musica en ficha socioeconomica INEC: %s - %s' % (ficha,ficha.val_tienemusica), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienemusica})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetieneinternet':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tieneinternet:
                    ficha.tieneinternet = False
                    ficha.val_tieneinternet = 0
                else:
                    ficha.tieneinternet = True
                    ficha.val_tieneinternet = 45
                ficha.save(request)
                log(u'Edito tiene internet en ficha socioeconomica INEC: %s - %s' % (ficha,ficha.val_tieneinternet), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tieneinternet})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienesala':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienesala:
                    ficha.tienesala = False
                else:
                    ficha.tienesala = True
                ficha.save(request)
                log(u'Edito tiene sala en ficha socioeconomica INEC: %s - %s' % (ficha,ficha.tienesala), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienesala})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienecomedor':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienecomedor:
                    ficha.tienecomedor = False
                else:
                    ficha.tienecomedor = True
                ficha.save(request)
                log(u'Edito tiene comedor en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tienecomedor), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienecomedor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienecocina':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienecocina:
                    ficha.tienecocina = False
                else:
                    ficha.tienecocina = True
                ficha.save(request)
                log(u'Edito tiene cocina en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tienecocina), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienecocina})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienebanio':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienebanio:
                    ficha.tienebanio = False
                else:
                    ficha.tienebanio = True
                ficha.save(request)
                log(u'Edito tiene baño en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tienebanio), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienebanio})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetieneluz':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tieneluz:
                    ficha.tieneluz = False
                else:
                    ficha.tieneluz = True
                ficha.save(request)
                log(u'Edito tiene luz en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tieneluz), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tieneluz})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetieneagua':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tieneagua:
                    ficha.tieneagua = False
                else:
                    ficha.tieneagua = True
                ficha.save(request)
                log(u'Edito tiene agua en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tieneagua), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tieneagua})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienetelefono':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienetelefono:
                    ficha.tienetelefono = False
                else:
                    ficha.tienetelefono = True
                ficha.save(request)
                log(u'Edito tiene telefono en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tienetelefono), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienetelefono})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienealcantarilla':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienealcantarilla:
                    ficha.tienealcantarilla = False
                else:
                    ficha.tienealcantarilla = True
                ficha.save(request)
                log(u'Edito tiene alcantarilla en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tienealcantarilla), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienealcantarilla})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

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
                ficha.save(request)
                log(u'Edito tiene disponibilidad de recursos en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.disponibilidadrecursos), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.disponibilidadrecursos})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienefolleto':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienefolleto:
                    ficha.tienefolleto = False
                else:
                    ficha.tienefolleto = True
                ficha.save(request)
                log(u'Edito tiene folleto en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tienefolleto), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienefolleto})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienecomputador':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienecomputador:
                    ficha.tienecomputador = False
                else:
                    ficha.tienecomputador = True
                ficha.save(request)
                log(u'Edito tiene computador en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tienecomputador), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienecomputador})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetieneenciclopedia':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tieneenciclopedia:
                    ficha.tieneenciclopedia = False
                else:
                    ficha.tieneenciclopedia = True
                ficha.save(request)
                log(u'Edito tiene enciclopedia en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tieneenciclopedia), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tieneenciclopedia})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienecyber':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienecyber:
                    ficha.tienecyber = False
                else:
                    ficha.tienecyber = True
                ficha.save(request)
                log(u'Edito tiene cyber en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tienecyber), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienecyber})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienebiblioteca':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienebiblioteca:
                    ficha.tienebiblioteca = False
                else:
                    ficha.tienebiblioteca = True
                ficha.save(request)
                log(u'Edito tiene biblioteca en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tienebiblioteca), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienebiblioteca})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienemuseo':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienemuseo:
                    ficha.tienemuseo = False
                else:
                    ficha.tienemuseo = True
                ficha.save(request)
                log(u'Edito tiene museo en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tienemuseo), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienemuseo})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienearearecreacion':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienearearecreacion:
                    ficha.tienearearecreacion = False
                else:
                    ficha.tienearearecreacion = True
                ficha.save(request)
                log(u'Edito tiene area de recreacion en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tienearearecreacion), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienearearecreacion})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienediabetes':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienediabetes:
                    ficha.tienediabetes = False
                else:
                    ficha.tienediabetes = True
                ficha.save(request)
                log(u'Edito tiene diabetes en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tienediabetes), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienediabetes})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienehipertencion':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienehipertencion:
                    ficha.tienehipertencion = False
                else:
                    ficha.tienehipertencion = True
                ficha.save(request)
                log(u'Edito tiene hipertencion en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tienehipertencion), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienehipertencion})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetieneparkinson':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tieneparkinson:
                    ficha.tieneparkinson = False
                else:
                    ficha.tieneparkinson = True
                ficha.save(request)
                log(u'Edito tiene parkinson en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tieneparkinson), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tieneparkinson})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienecancer':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienecancer:
                    ficha.tienecancer = False
                else:
                    ficha.tienecancer = True
                ficha.save(request)
                log(u'Edito tiene cancer en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tienecancer), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienecancer})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienealzheimer':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienealzheimer:
                    ficha.tienealzheimer = False
                else:
                    ficha.tienealzheimer = True
                ficha.save(request)
                log(u'Edito tiene alzheimer en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tienealzheimer), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienealzheimer})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienevitiligo':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienevitiligo:
                    ficha.tienevitiligo = False
                else:
                    ficha.tienevitiligo = True
                ficha.save(request)
                log(u'Edito tiene vitiligo en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tienevitiligo), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienevitiligo})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienedesgastamiento':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienedesgastamiento:
                    ficha.tienedesgastamiento = False
                else:
                    ficha.tienedesgastamiento = True
                ficha.save(request)
                log(u'Edito tiene desgatamiento en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tienedesgastamiento), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienedesgastamiento})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienepielblanca':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienepielblanca:
                    ficha.tienepielblanca = False
                else:
                    ficha.tienepielblanca = True
                ficha.save(request)
                log(u'Edito tiene piel blanca en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tienepielblanca), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienepielblanca})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienesida':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienesida:
                    ficha.tienesida = False
                else:
                    ficha.tienesida = True
                ficha.save(request)
                log(u'Edito tiene sida en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tienesida), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienesida})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienedesktop':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienedesktop:
                    ficha.tienedesktop = False
                    ficha.val_tienedesktop = 0
                else:
                    ficha.tienedesktop = True
                    ficha.val_tienedesktop = 35
                ficha.save(request)
                log(u'Edito tiene desktop en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.val_tienedesktop), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienedesktop})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetienelaptop':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                if ficha.tienelaptop:
                    ficha.tienelaptop = False
                    ficha.val_tienelaptop = 0
                else:
                    ficha.tienelaptop = True
                    ficha.val_tienelaptop = 39
                ficha.save(request)
                log(u'Edito tiene lapto en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tienelaptop), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tienelaptop})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'niveljefehogar':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                niveleducacion = NivelEstudio.objects.get(pk=request.POST['niveledu'])
                ficha.niveljefehogar = niveleducacion
                ficha.val_niveljefehogar = niveleducacion.puntaje
                ficha.save(request)
                log(u'Edito nivel jefe de hogar en ficha socioeconomica INEC: %s - %s' % (ficha, niveleducacion), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.niveljefehogar.nombre})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'ocupacionjefehogar':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                ocupacion = OcupacionJefeHogar.objects.get(pk=request.POST['ocupacion'])
                ficha.ocupacionjefehogar = ocupacion
                ficha.val_ocupacionjefehogar = ocupacion.puntaje
                ficha.save(request)
                log(u'Edito ocupacion del jefe de hogar en ficha socioeconomica INEC: %s - %s' % (ficha, ocupacion), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.ocupacionjefehogar.nombre})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'tipovivienda':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                tipovivienda = TipoVivienda.objects.get(pk=request.POST['tipovivienda'])
                ficha.tipovivienda = tipovivienda
                ficha.val_tipovivienda = tipovivienda.puntaje
                ficha.save(request)
                log(u'Edito tipo de vivienda en ficha socioeconomica INEC: %s - tipo de vivienda: %s' % (ficha, tipovivienda), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tipovivienda.nombre})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'tipoviviendapropia':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                tipoviviendapropia = TipoViviendaPro.objects.get(pk=request.POST['tipoviviendapropia'])
                ficha.tipoviviendapro = tipoviviendapropia
                # ficha.val_tipoviviendapropia = tipoviviendapropia.puntaje
                ficha.save(request)
                log(u'Edito tipo de vivienda propia en ficha socioeconomica INEC: %s -  tipo de vivienda: %s' % (ficha, tipoviviendapropia),request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tipoviviendapro.nombre})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'materialpared':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                materialpared = MaterialPared.objects.get(pk=request.POST['materialpared'])
                ficha.materialpared = materialpared
                ficha.val_materialpared = materialpared.puntaje
                ficha.save(request)
                log(u'Edito material pared en ficha socioeconomica INEC: %s - material pared: %s' % (ficha, materialpared), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.materialpared.nombre})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'materialpiso':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                materialpiso = MaterialPiso.objects.get(pk=request.POST['materialpiso'])
                ficha.materialpiso = materialpiso
                ficha.val_materialpiso = materialpiso.puntaje
                ficha.save(request)
                log(u'Edito material de piso en ficha socioeconomica INEC: %s - material piso: %s' % (ficha, materialpiso), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.materialpiso.nombre})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'cantbannoducha':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                cantbannoducha = CantidadBannoDucha.objects.get(pk=request.POST['cantduchas'])
                ficha.cantbannoducha = cantbannoducha
                ficha.val_cantbannoducha = cantbannoducha.puntaje
                ficha.save(request)
                log(u'Edito catidad de baño de ducha en ficha socioeconomica INEC: %s -  cattidad de ducha: %s' % (ficha, cantbannoducha), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.cantbannoducha.nombre})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'tiposervhig':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                tiposervhig = TipoServicioHigienico.objects.get(pk=request.POST['tiposervh'])
                ficha.tiposervhig = tiposervhig
                ficha.val_tiposervhig = tiposervhig.puntaje
                ficha.save(request)
                log(u'Edito tipo de servicio higiene en ficha socioeconomica INEC: %s - tipo de servicio: %s' % (ficha, tiposervhig), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tiposervhig.nombre})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'canttvcolor':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                canttv = CantidadTVColorHogar.objects.get(pk=request.POST['canttv'])
                ficha.canttvcolor = canttv
                ficha.val_canttvcolor = canttv.puntaje
                ficha.save(request)
                log(u'Edito cantidad de tv color en ficha socioeconomica INEC: %s - cantidad de tv: %s' % (ficha, canttv), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.canttvcolor.nombre})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'cantvehiculos':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                cantveh = CantidadVehiculoHogar.objects.get(pk=request.POST['cantveh'])
                ficha.cantvehiculos = cantveh
                ficha.val_cantvehiculos = cantveh.puntaje
                ficha.save(request)
                log(u'Edito cantidad de vehiculos en ficha socioeconomica INEC: %s - cantidad de vehiculo: %s' % (ficha, cantveh), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.cantvehiculos.nombre})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'cantcelulares':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                cantcel = CantidadCelularHogar.objects.get(pk=request.POST['cantcel'])
                ficha.cantcelulares = cantcel
                ficha.val_cantcelulares = cantcel.puntaje
                ficha.save(request)
                log(u'Edito cantidad de celulares en ficha socioeconomica INEC: %s - cantidad de celular: %s' % (ficha, cantcel), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.cantcelulares.nombre})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'cantacthorashogar':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                ficha.horastareahogar = request.POST['canthogar']
                ficha.save(request)
                log(u'Edito contacto de horas de hogar en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.horastareahogar), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.horastareahogar})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'saveotrosrecursos':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                ficha.otrosrecursos = request.POST['otrorecurso']
                ficha.save(request)
                log(u'Adiciono otros recursos en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.otrosrecursos), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.otrosrecursos})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'saveotrossector':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                ficha.otrossector = request.POST['otrosector']
                ficha.save(request)
                log(u'Adiciono otros sectores en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.otrossector), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.otrossector})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'saveotrasenfermedades':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                ficha.otrasenfermedades = request.POST['otraenfermedad']
                ficha.save(request)
                log(u'Adiciono otras enfermedades en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.otrasenfermedades), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.otrasenfermedades})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'saveenfermedadescomunes':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                ficha.enfermedadescomunes = request.POST['enfermedadescomunes']
                ficha.save(request)
                log(u'Adiciono otros enfermedades comunes en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.enfermedadescomunes), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.enfermedadescomunes})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'savetratamientomedico':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                ficha.tratamientomedico = request.POST['tratamientomedico']
                ficha.save(request)
                log(u'Adiciono tratamiento medico en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.tratamientomedico), request, "edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.tratamientomedico})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'cantacthorasdomesticas':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                ficha.horastrabajodomestico = request.POST['cantdomesticas']
                ficha.save(request)
                log(u'Edito contacto de horas domestica en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.horastrabajodomestico), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.horastrabajodomestico})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'cantacthorastrabajofuera':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                ficha.horastrabajofuera = request.POST['canttrabajofuera']
                ficha.save(request)
                log(u'Edito contacto de horas trabajo fuera en ficha socioeconomica INEC: %s - %s' % (ficha, ficha.horastrabajofuera), request,"edit")
                return JsonResponse({'result': 'ok', 'valor': ficha.horastrabajofuera})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editfamiliar':
            try:
                persona = Persona.objects.get(pk=request.GET['id'])
                f = FamiliarForm(request.POST)
                if f.is_valid():
                    familiar = PersonaDatosFamiliares.objects.get(pk=int(request.POST['idfamiliar']))
                    if persona.personadatosfamiliares_set.filter(identificacion=f.cleaned_data['identificacion']).exclude(id=familiar.id).exists():
                        return JsonResponse({'result': 'bad', 'mensaje': u'El familiar se encuentra registrado.'})
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
                    familiar.save(request)
                    log(u'Modifico familiar: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'datosnacimiento':
            try:
                persona = Persona.objects.get(pk=request.GET['id'])
                f = DatosNacimientoForm(request.POST)
                if f.is_valid():
                    persona.paisnacimiento = f.cleaned_data['paisnacimiento']
                    persona.provincianacimiento = f.cleaned_data['provincianacimiento']
                    persona.cantonnacimiento = f.cleaned_data['cantonnacimiento']
                    persona.parroquianacimiento = f.cleaned_data['parroquianacimiento']
                    persona.save(request)
                    log(u'Modifico datos de nacimiento: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'datosdomicilio':
            try:
                if 'archivocroquis' in request.FILES:
                    newfile = request.FILES['archivocroquis']
                    if newfile.size > 2194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 2Mb"})
                persona = Persona.objects.get(pk=request.GET['id'])
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
                    persona.save(request)
                    if 'archivocroquis' in request.FILES:
                        newfile = request.FILES['archivocroquis']
                        newfile._name = generar_nombre("croquis_", newfile._name)
                        persona.archivocroquis = newfile
                        persona.save(request)
                    log(u'Modifico datos de domicilio: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'discapacidad':
            try:
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 2194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 2Mb"})
                persona = Persona.objects.get(pk=request.GET['id'])
                f = DiscapacidadForm(request.POST)
                if f.is_valid():
                    newfile = None
                    perfil = persona.mi_perfil()
                    perfil.tienediscapacidad = f.cleaned_data['tienediscapacidad']
                    perfil.tipodiscapacidad = f.cleaned_data['tipodiscapacidad']
                    perfil.porcientodiscapacidad = f.cleaned_data['porcientodiscapacidad'] if f.cleaned_data['porcientodiscapacidad'] else 0
                    perfil.carnetdiscapacidad = f.cleaned_data['carnetdiscapacidad']
                    perfil.save(request)
                    if not f.cleaned_data['tienediscapacidad']:
                        perfil.archivo = None
                        perfil.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivosdiscapacidad_", newfile._name)
                        perfil.archivo = newfile
                        perfil.save(request)
                    log(u'Modifico tipo de discapacidad: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'delfamiliar':
            try:
                data = {'title': 'Ficha Socio-Economica'}
                #persona = Persona.objects.get(pk=request.GET['personaid'])
                #familiar = PersonaDatosFamiliares.objects.get(pk=int(request.POST['id']))
                #familiar.delete()
                data['personaficha'] = persona = Persona.objects.get(pk=request.GET['personaid'])
                data['ficha'] = persona.mi_ficha()
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
                return render(request, "dobe/ficha.html", data)
            except Exception as ex:
                pass

        elif action == 'addfamiliar':
            try:
                persona = Persona.objects.get(pk=request.GET['id'])
                f = FamiliarForm(request.POST)
                if f.is_valid():
                    if persona.personadatosfamiliares_set.filter(identificacion=f.cleaned_data['identificacion']).exists():
                        return JsonResponse({'result': 'bad', 'mensaje': u'El familiar se encuentra registrado.'})
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
                    familiar.save(request)
                    log(u'Adiciono familiar: %s' % persona, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'cantacthorashacertareas':
            try:
                ficha = FichaSocioeconomicaINEC.objects.get(pk=request.POST['fichaid'])
                ficha.horashacertareas = request.POST['canthacertareas']
                ficha.save(request)
                return JsonResponse({'result': 'ok', 'valor': ficha.horashacertareas})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data = {'title': 'Listado de Perfiles de Alumnos'}
        adduserdata(request, data)
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar perfil de alumno'
                    inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = inscripcion
                    data['form'] = DobeInscripcionForm()
                    return render(request, "dobe/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'editfamiliar':
                try:
                    data['title'] = u'Editar familiar'
                    data['personaid'] = request.GET['idpersona']
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
                    return render(request, "dobe/editfamiliar.html", data)
                except:
                    pass

            if action == 'delfamiliar':
                try:
                    data['personaid'] = request.GET['idpersona']
                    data['title'] = u'Eliminar familiar'
                    data['familiar'] = familiar = PersonaDatosFamiliares.objects.get(pk=int(request.GET['id']))
                    return render(request, "dobe/delfamiliar.html", data)
                except:
                    pass

            elif action == 'addfamiliar':
                try:
                    data['title'] = u'Adicionar familiar'
                    data['form'] = FamiliarForm()
                    data['personaid'] = request.GET['id']
                    return render(request, "dobe/addfamiliar.html", data)
                except:
                    pass

            elif action == 'datosnacimiento':
                try:
                    data['personaid'] = persona = Persona.objects.get(pk=request.GET['id'])
                    data['title'] = u'Datos de nacimiento'
                    form = DatosNacimientoForm(initial={'paisnacimiento': persona.paisnacimiento,
                                                        'provincianacimiento': persona.provincianacimiento,
                                                        'cantonnacimiento': persona.cantonnacimiento,
                                                        'parroquianacimiento': persona.parroquianacimiento})
                    form.editar(persona)
                    data['form'] = form
                    return render(request, "dobe/datosnacimiento.html", data)
                except:
                    pass

            elif action == 'datosdomicilio':
                try:
                    data['personaid'] = persona = Persona.objects.get(pk=request.GET['id'])
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
                    return render(request, "dobe/datosdomicilio.html", data)
                except:
                    pass

            elif action == 'discapacidad':
                try:

                    data['title'] = u'Discapacidad'
                    data['personaid'] = persona = Persona.objects.get(pk=request.GET['id'])
                    perfil = persona.mi_perfil()
                    form = DiscapacidadForm(initial={'tienediscapacidad': perfil.tienediscapacidad,
                                                     'tipodiscapacidad': perfil.tipodiscapacidad,
                                                     'porcientodiscapacidad': perfil.porcientodiscapacidad,
                                                     'carnetdiscapacidad': perfil.carnetdiscapacidad})
                    data['form'] = form
                    return render(request, 'dobe/discapacidad.html', data)
                except:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Editar perfil del alumno'
                    persona = Persona.objects.get(pk=request.GET['id'])
                    data['perfil'] = perfil = persona.mi_perfil()
                    data['form'] = DobeInscripcionForm(initial={"raza": perfil.raza,
                                                                "tienediscapacidad": perfil.tienediscapacidad,
                                                                "tipodiscapacidad": perfil.tipodiscapacidad,
                                                                "porcientodiscapacidad": perfil.porcientodiscapacidad,
                                                                "carnetdiscapacidad": perfil.carnetdiscapacidad})
                    return render(request, "dobe/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'listadosolicitudes':
                try:
                    data['title'] = u'Listado de solicitudes ficha estudiantil'
                    search = None
                    ids = None
                    tipobus = None
                    inscripcionid = None
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            listadosolicitudes = FichaSocioeconomicaReplayINEC.objects.filter(Q(persona__nombres__icontains=search) |
                                                                   Q(persona__apellido1__icontains=search) |
                                                                   Q(persona__apellido2__icontains=search) |
                                                                   Q(persona__cedula__icontains=search) |
                                                                   Q(persona__pasaporte__icontains=search) |
                                                                   Q(persona__usuario__username__icontains=search),status=True)
                        else:
                            listadosolicitudes = FichaSocioeconomicaReplayINEC.objects.filter(Q(persona__apellido1__icontains=ss[0]) &
                                                                   Q(persona__apellido2__icontains=ss[1]),status=True)
                    else:
                        listadosolicitudes = FichaSocioeconomicaReplayINEC.objects.select_related().filter(status=True)
                    paging = MiPaginador(listadosolicitudes, 25)
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
                    data['listadosolicitudes'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "dobe/listadosolicitudes.html", data)
                except Exception as ex:
                    pass

            elif action == 'delsustento':
                try:
                    sustento = PersonaSustentaHogar.objects.get(pk=request.GET['id'])
                    ficha = sustento.fichasocioeconomicainec_set.all()[0]
                    sustento.delete()
                    return HttpResponseRedirect("/dobe?action=ficha&id=" + str(ficha.persona.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponseRedirect(request.path)

            elif action == 'pdf':
                try:
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
                    data['inscripcionpersona'] = Inscripcion.objects.get(pk=request.GET['idins'])
                    matricula = Matricula.objects.filter(inscripcion_id=request.GET['idins'], nivel__periodo=periodo)
                    validamaterias = 0
                    if matricula.exists():
                        validamaterias = 1
                        data['idmatricula'] = matricula[0]
                        data['materias'] = materias = matricula[0].materiaasignada_set.all()
                        data['nivelacademico'] = InscripcionNivel.objects.get(inscripcion_id=request.GET['idins'])
                    data['validamaterias'] = validamaterias
                    return conviert_html_to_pdf(
                        'dobe/ficha_pdf.html',
                        {
                            'pagesize': 'A4',
                            'listadoficha': data,
                        }
                    )
                except Exception as e:
                    import sys
                    print(e)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass

            elif action == 'pdfresultados':
                data = {}
                adduserdata(request, data)
                data['personaficha'] = persona = Persona.objects.get(pk=request.GET['id'])
                data['ficha_grupo'] = persona.mi_ficha_matricula(periodo)
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
                data['periodo'] = periodo
                data['inscripcionpersona'] = Inscripcion.objects.get(pk=request.GET['idins'])
                matricula = Matricula.objects.filter(inscripcion_id=request.GET['idins'], nivel__periodo=periodo)
                validamaterias = 0
                if matricula.exists():
                    validamaterias = 1
                    data['idmatricula'] = matricula[0]
                    data['materias'] = materias = matricula[0].materiaasignada_set.all()
                    data['nivelacademico'] = InscripcionNivel.objects.get(inscripcion_id=request.GET['idins'])
                data['validamaterias'] = validamaterias
                return conviert_html_to_pdf(
                    'dobe/ficha_pdfresultado.html',
                    {
                        'pagesize': 'A4',
                        'listadoficha': data,
                    }
                )

            elif action == 'pdfresultadosreplay':
                data = {}
                adduserdata(request, data)
                data['personaficha'] = persona = Persona.objects.get(pk=request.GET['id'])
                data['ficha_grupo'] = persona.mi_ficha_matricula(periodo)
                data['ficha'] = persona.mi_fichareply()
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
                data['periodo'] = periodo
                data['inscripcionpersona'] = Inscripcion.objects.get(pk=request.GET['idins'])
                matricula = Matricula.objects.filter(inscripcion_id=request.GET['idins'], nivel__periodo=periodo)
                validamaterias = 0
                if matricula.exists():
                    validamaterias = 1
                    data['idmatricula'] = matricula[0]
                    data['materias'] = materias = matricula[0].materiaasignada_set.all()
                    data['nivelacademico'] = InscripcionNivel.objects.get(inscripcion_id=request.GET['idins'])
                data['validamaterias'] = validamaterias
                return conviert_html_to_pdf(
                    'dobe/ficha_pdfresultadoreplay.html',
                    {
                        'pagesize': 'A4',
                        'listadoficha': data,
                    }
                )

            elif action == 'ficha':
                try:
                    data['title'] = u'Ficha Socio-Economica'
                    data['personaficha'] = persona = Persona.objects.get(pk=request.GET['id'])
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
                    return render(request, "dobe/ficha.html", data)
                except Exception as ex:
                    pass

            # elif action == 'excelprograma':
            #     try:
            #         __author__ = 'Unemi'
            #         style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
            #         style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
            #         style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
            #         title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
            #         style1 = easyxf(num_format_str='D-MMM-YY')
            #         font_style = XFStyle()
            #         font_style.font.bold = True
            #         font_style2 = XFStyle()
            #         font_style2.font.bold = False
            #         wb = Workbook(encoding='utf-8')
            #         ws = wb.add_sheet('exp_xls_post_part')
            #         ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
            #         response = HttpResponse(content_type="application/ms-excel")
            #         response[
            #             'Content-Disposition'] = 'attachment; filename=Ficha Socio Economica' + random.randint(1, 10000).__str__() + '.xls'
            #
            #         columns = [
            #             (u"Nombre", 2000),
            #             (u"IDENTIFICACIÓN", 10000),
            #             (u"EMAIL/TELÉFONO", 10000),
            #             (u"RAZA", 3000),
            #             (u"EST. SOCIOECON.", 3000),
            #             (u"DISCAP.", 3000),
            #             (u"TIPO DISCAPACIDAD", 10000),
            #             (u"PERIODO ACADÉMICO", 10000),
            #             (u"FACULTAD", 10000),
            #             (u"CARRERA", 10000),
            #             (u"MODALIDAD", 10000),
            #             (u"NIVEL", 10000),
            #         ]
            #         row_num = 3
            #         for col_num in range(len(columns)):
            #             ws.write(row_num, col_num, columns[col_num][0], font_style)
            #             ws.col(col_num).width = columns[col_num][1]
            #         date_format = xlwt.XFStyle()
            #         date_format.num_format_str = 'yyyy/mm/dd'
            #         personal = Persona.objects.filter(inscripcion__matricula__nivel__periodo=periodo, usuario__groups__id__in=[ALUMNOS_GROUP_ID]).distinct()
            #         row_num = 4
            #         for personadobe in personal:
            #             perfil = personadobe.mi_perfil()
            #             ficha = personadobe.mi_ficha()
            #
            #             i = 0
            #             campo1 = personadobe.nombre_completo()
            #             if personadobe.mi_perfil().tienediscapacidad:
            #                 campo1 = campo1 + ' DISCAPACIDAD'
            #             campo2 = ""
            #             if personadobe.identificacion:
            #                 campo2 = personadobe.identificacion()
            #
            #             campo3 = ""
            #
            #             if personadobe.lista_emails():
            #                 for email in personadobe.lista_emails():
            #                     campo3 = email + ' '
            #
            #             if personadobe.lista_telefonos():
            #                 for telefono in personadobe.lista_telefonos():
            #                     campo3 = telefono + ', '
            #
            #             campo4 = ""
            #             if perfil.raza:
            #                 campo4 = perfil.raza.nombre
            #
            #             campo5 = ficha.grupoeconomico.nombre_corto()
            #
            #             campo6 = ""
            #             if perfil.tienediscapacidad:
            #                 campo6 = "SI"
            #             campo7 = ''
            #             campo8 = ''
            #             campo9 = ''
            #             campo10 = ''
            #             if Matricula.objects.filter(inscripcion__persona=personadobe, nivel__periodo=periodo, retiradomatricula=False, status=True):
            #                 matricula = Matricula.objects.filter(inscripcion__persona=personadobe, nivel__periodo=periodo, retiradomatricula=False, status=True)[0]
            #                 campo7 = matricula.inscripcion.coordinacion.nombre
            #                 campo8 = matricula.inscripcion.carrera.nombre
            #                 campo9 = matricula.inscripcion.modalidad.nombre
            #                 campo10 = matricula.nivelmalla.nombre
            #
            #             ws.write(row_num, 0, campo1, font_style2)
            #             ws.write(row_num, 1, campo2, font_style2)
            #             ws.write(row_num, 2, campo3, font_style2)
            #             ws.write(row_num, 3, campo4, date_format)
            #             ws.write(row_num, 4, campo5, date_format)
            #             ws.write(row_num, 5, campo6, date_format)
            #             ws.write(row_num, 6, periodo.nombre, font_style2)
            #             ws.write(row_num, 7, campo7, font_style2)
            #             ws.write(row_num, 8, campo8, font_style2)
            #             ws.write(row_num, 9, campo9, font_style2)
            #             ws.write(row_num, 10, campo10, font_style2)
            #             row_num += 1
            #         wb.save(response)
            #         return response
            #     except Exception as ex:
            #         pass

            elif action == 'excelprograma':
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
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Ficha Socio Economica' + random.randint(1, 10000).__str__() + '.xls'

                    columns = [
                        (u"Nombre", 2000),
                        (u"IDENTIFICACIÓN", 10000),
                        (u"EMAIL/TELÉFONO", 10000),
                        (u"RAZA", 3000),
                        (u"EST. SOCIOECON.", 3000),
                        (u"DISCAP.", 3000),
                        (u"TIPO DISCAPACIDAD", 10000),
                        (u"PERIODO ACADÉMICO", 10000),
                        (u"FACULTAD", 10000),
                        (u"CARRERA", 10000),
                        (u"MODALIDAD", 10000),
                        (u"NIVEL", 10000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    # personal = Persona.objects.filter(inscripcion__matricula__nivel__periodo=periodo, usuario__groups__id__in=[ALUMNOS_GROUP_ID]).distinct()
                    personal = Inscripcion.objects.filter(matricula__nivel__periodo=periodo, persona__usuario__groups__id__in=[ALUMNOS_GROUP_ID]).distinct()
                    row_num = 4
                    for personadobe in personal:
                        perfil = personadobe.persona.mi_perfil()
                        ficha = personadobe.persona.mi_ficha()

                        i = 0
                        campo1 = personadobe.persona.nombre_completo()
                        if personadobe.persona.mi_perfil().tienediscapacidad:
                            campo1 = campo1 + ' DISCAPACIDAD'
                        campo2 = ""
                        if personadobe.persona.identificacion:
                            campo2 = personadobe.persona.identificacion()

                        campo3 = ""

                        if personadobe.persona.lista_emails():
                            for email in personadobe.persona.lista_emails():
                                campo3 = email + ' '

                        if personadobe.persona.lista_telefonos():
                            for telefono in personadobe.persona.lista_telefonos():
                                campo3 = telefono + ', '

                        campo4 = ""
                        if perfil.raza:
                            campo4 = perfil.raza.nombre

                        campo5 = ficha.grupoeconomico.nombre_corto()

                        campo6 = ""
                        if perfil.tienediscapacidad:
                            campo6 = "SI"
                        campo7 = ''
                        campo8 = ''
                        campo9 = ''
                        campo10 = ''
                        # if Matricula.objects.filter(inscripcion__persona=personadobe, nivel__periodo=periodo, retiradomatricula=False, status=True):
                        #     matricula = Matricula.objects.filter(inscripcion__persona=personadobe, nivel__periodo=periodo, retiradomatricula=False, status=True)[0]
                        campo7 = personadobe.coordinacion.nombre
                        campo8 = personadobe.carrera.nombre
                        campo9 = personadobe.modalidad.nombre
                        matri = personadobe.matricula_periodo(periodo)
                        campo10 = matri.nivelmalla.nombre
                        campo11 = ''
                        if perfil.tipodiscapacidad:
                            campo11 = perfil.tipodiscapacidad.nombre

                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, date_format)
                        ws.write(row_num, 4, campo5, date_format)
                        ws.write(row_num, 5, campo6, date_format)
                        ws.write(row_num, 6, campo11, font_style2)
                        ws.write(row_num, 7, periodo.nombre, font_style2)
                        ws.write(row_num, 8, campo7, font_style2)
                        ws.write(row_num, 9, campo8, font_style2)
                        ws.write(row_num, 10, campo9, font_style2)
                        ws.write(row_num, 11, campo10, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                ss = search.split(' ')
                while '' in ss:
                    ss.remove('')
                if len(ss) == 1:
                    personal = Persona.objects.filter(Q(nombres__icontains=search) |
                                                      Q(apellido1__icontains=search) |
                                                      Q(apellido2__icontains=search) |
                                                      Q(cedula__icontains=search) |
                                                      Q(pasaporte__icontains=search) |
                                                      Q(inscripcion__identificador__icontains=search) |
                                                      Q(inscripcion__inscripciongrupo__grupo__nombre__icontains=search) |
                                                      Q(inscripcion__carrera__nombre__icontains=search),inscripcion__matricula__nivel__periodo=periodo, usuario__groups__id__in=[ALUMNOS_GROUP_ID]).distinct()
                else:
                    personal = Persona.objects.filter(Q(apellido1__icontains=ss[0]) &
                                                      Q(apellido2__icontains=ss[1]),inscripcion__matricula__nivel__periodo=periodo, usuario__groups__id__in=[ALUMNOS_GROUP_ID]).distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                personal = Persona.objects.filter(id=ids, inscripcion__matricula__nivel__periodo=periodo,usuario__groups__id__in=[ALUMNOS_GROUP_ID]).distinct()
            else:
                personal = Persona.objects.filter(inscripcion__matricula__nivel__periodo=periodo,usuario__groups__id__in=[ALUMNOS_GROUP_ID]).distinct()
            paging = MiPaginador(personal, 25)
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
            data['personal'] = page.object_list
            return render(request, "dobe/view.html", data)