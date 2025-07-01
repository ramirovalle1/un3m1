# -*- coding: UTF-8 -*-
import json
import sys
import os
from itertools import count
import random
import time
import pyqrcode
import xlrd
from decimal import Decimal
import io
import xlsxwriter
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.template.context import Context
from django.db.models.query_utils import Q
from django.forms import model_to_dict
from datetime import datetime, timedelta
from django.db import connections
from django.contrib import messages
from xlwt import *
from xlwt import easyxf
import xlwt

from decorators import secure_module, last_access
from sagest.models import Rubro, TipoOtroRubro, Pago, CuentaContable, CuentaBanco, ComprobanteAlumno
from settings import USA_TIPOS_INSCRIPCIONES, TIPO_INSCRIPCION_INICIAL, SITE_STORAGE
from sga.commonviews import adduserdata, obtener_reporte, actualizar_nota_grupo, traerNotificaciones
from posgrado.commonviews import secuencia_contratopagare, crear_inscripcion
from posgrado.models import InscripcionCohorte, CohorteMaestria, MaestriasAdmision, AsesorMeta,\
    InscripcionAspirante, FormatoCarreraIpec, RolAsesor, AsesorComercial, HistorialAsesor, DetalleAprobacionFormaPago, \
    ClaseRequisito, RequisitosMaestria, DetalleEvidenciaRequisitosAspirante, TipoRespuestaProspecto, HistorialRespuestaProspecto,\
    ConfigFinanciamientoCohorte, HistorialReservacionProspecto,Contrato, TablaAmortizacion, DetalleAprobacionContrato, \
    EvidenciaRequisitosAspirante, GarantePagoMaestria, RequisitosGrupoCohorte, CanalInformacionMaestria, CambioAdmitidoCohorteInscripcion, \
    DetallePreAprobacionPostulante, VentasProgramaMaestria, IntegranteGrupoExamenMsc, IntegranteGrupoEntrevitaMsc, AsesorTerritorio, \
    DetalleAsesorMeta, CuposMaestriaMes
from posgrado.forms import RolForm, AsesorComercialForm, RegistroAdmisionIpecForm, InscripcionCohorteForm, AsesorMetaForm, \
    ConfirmarPreAsignacionForm, TitulacionPersonaPosgradoForm, ActualizarDatosPersonaForm, FinanciamientoForm, \
    HistorialRespuestaProspectoForm, MencionMaestriaForm, AsignarTipoForm, ContratoPagoMaestriaForm, ReservacionProspectoForm, \
    ConfigFinanciamientoCohorteForm, CambioCohorteMaestriaForm, GarantePagoMaestriaForm, ComprobanteArchivoEstudianteForm,\
    RegistroPagoForm, CanalInformacionForm, EditarComprobantePagoForm, RequisitosMaestriaForm, RequisitosMaestriaImgForm, \
    TitulacionPersonaAdmisionPosgradoForm, EvidenciaRequisitoAdmisionForm, ValidarPerfilAdmisionForm, EditarRubroMaestriaForm, \
    AdicionarCuotaTablaAmortizacionForm, ReasignarMasivoForm, AsignarTerritorioForm, VentasMaestriasForm, OficioTerminacionContratoForm
from sga.funciones_templatepdf import contratoformapagoprograma, pagareaspirantemae, oficioterminacioncontrato
from sga.funciones import MiPaginador, log, generar_nombre, convertir_fecha, convertir_hora, variable_valor, \
    resetear_clave, puede_realizar_accion, puede_ver_todoadmision, resetear_clavepostulante, null_to_decimal, \
    calculate_username, generar_usuario_admision, validar_archivo, salvaRubros, numero_a_letras, validarcedula, \
    notificacion3
from sga.models import miinstitucion, Persona, CUENTAS_CORREOS, Carrera, \
    Matricula, PerfilUsuario, SubAreaConocimientoTitulacion, SubAreaEspecificaConocimientoTitulacion, \
    AreaConocimientoTitulacion, Titulo, CamposTitulosPostulacion, Titulacion, Graduado, ItinerarioMallaEspecilidad, \
    VariablesGlobales, Notificacion, Reporte, Canton, PersonaSituacionLaboral, PerfilInscripcion
from inno.models import ProgramaPac, TipoFormaPagoPac, DetallePerfilIngreso
from sga.templatetags.sga_extras import encrypt
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdfsaveqrcertificado
from sga.tasks import send_html_mail, conectar_cuenta
from django.contrib.auth.models import Group, User
from moodle import moodle
from django.db.models import Max
from typing import Any, Hashable, Iterable, Optional
from sga.funciones_templatepdf import certificadoadmtidoprograma
from bd.models import LogEntryLogin
from dateutil.relativedelta import relativedelta
import requests
from sga.reportes import run_report_v1
import shutil
from sga.excelbackground import reporte_estudiantes_unemi
from sagest.forms import DatosPersonalesMaestranteForm
from secretaria.views.adm_secretaria import nombre_carrera_pos
import ast

def buscar_dicc(it: Iterable[dict], clave: Hashable, valor: Any) -> Optional[dict]:
    for dicc in it:
        if dicc[clave] == valor:
            return dicc
    return None

def obtener_primer_ultimo_dia_del_mes(anio, mes):
    primer_dia = datetime(anio, mes, 1)
    if mes == 12:
        siguiente_mes = datetime(anio+1, 1, 1)
    else:
        siguiente_mes = datetime(anio, mes+1, 1)
    ultimo_dia = siguiente_mes - timedelta(days=1)
    return primer_dia, ultimo_dia

@login_required(redirect_field_name='ret', login_url='/loginposgrado')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    hoy = datetime.now().date()
    data['personasesion'] = persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']
#    persona = request.session['persona']
    urlepunemi = 'https://sagest.epunemi.gob.ec/'
    # urlepunemi = 'http://127.0.0.1:8001/'

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addrol':
            try:
                f = RolForm(request.POST)
                if f.is_valid():
                    filtro = RolAsesor(descripcion=f.cleaned_data['descripcion'],)
                    filtro.save(request)
                    log(u'Adicionó rol para asesor comercial: %s' % filtro, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Datos erróneos, intente nuevamente."}, safe=False)

        elif action == 'editrol':
            try:
                f = RolForm(request.POST)
                if f.is_valid():
                    filtro = RolAsesor.objects.get(pk=int(request.POST['id']), status=True)
                    filtro.descripcion = f.cleaned_data['descripcion']
                    filtro.save(request)
                    log(u'Editó rol para asesor comercial: %s' % filtro, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Datos erróneos, intente nuevamente."}, safe=False)

        elif action == 'deleterol':
            try:
                with transaction.atomic():
                    instancia = RolAsesor.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino Rol: %s' % instancia, request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addasesor':
            try:
                f = AsesorComercialForm(request.POST)
                if f.is_valid():
                    if not AsesorComercial.objects.filter(status=True, persona=f.cleaned_data['persona']).exists():
                        if 'activo' in request.POST:
                            activo = True
                        else:
                            activo = False
                        asesor = AsesorComercial(persona=f.cleaned_data['persona'],
                                                 rol=f.cleaned_data['rol'],
                                                 rolgrupo=f.cleaned_data['gruporol'],
                                                 fecha_desde=f.cleaned_data['fechadesdevig'],
                                                 fecha_hasta=f.cleaned_data['fechahastavig'],
                                                 telefono=f.cleaned_data['telefono'],
                                                 activo=activo)
                        asesor.save(request)

                        if asesor.rol.id in [1, 6]:
                            grupo = Group.objects.get(id=368)
                            grupo.user_set.add(asesor.persona.usuario)
                            grupo.save()

                            grupo2 = Group.objects.get(id=365)
                            grupo2.user_set.add(asesor.persona.usuario)
                            grupo2.save()

                        elif asesor.rol.id == 4:
                            grupo = Group.objects.get(name='ASESOR DE FINANCIAMIENTO')
                            grupo.user_set.add(asesor.persona.usuario)
                            grupo.save()

                            grupo2 = Group.objects.get(id=365)
                            grupo2.user_set.add(asesor.persona.usuario)
                            grupo2.save()

                        log(u'Adicionó un Asesor: %s' % asesor, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({"result": True, "mensaje": "Datos erróneos, este asesor ya se encuentra registrado."}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Datos erróneos, intente nuevamente."}, safe=False)

        elif action == 'editasesor':
            try:
                f = AsesorComercialForm(request.POST)
                asesor = AsesorComercial.objects.get(pk=int(request.POST['id']))
                f.sin_persona()
                if f.is_valid():
                    if 'activo' in request.POST:
                        activo = True

                        grupo = Group.objects.get(id=368)
                        grupo.user_set.add(asesor.persona.usuario)
                        grupo.save()

                        grupo2 = Group.objects.get(id=365)
                        grupo2.user_set.add(asesor.persona.usuario)
                        grupo2.save()
                    else:
                        activo = False

                        grupo = Group.objects.get(id=368)
                        grupo.user_set.remove(asesor.persona.usuario)
                        grupo.save()

                        grupo2 = Group.objects.get(id=365)
                        grupo2.user_set.remove(asesor.persona.usuario)
                        grupo2.save()

                    asesor.rol = f.cleaned_data['rol']
                    asesor.rolgrupo = f.cleaned_data['gruporol']
                    asesor.fecha_desde = f.cleaned_data['fechadesdevig']
                    asesor.fecha_hasta = f.cleaned_data['fechahastavig']
                    asesor.telefono = f.cleaned_data['telefono']
                    asesor.activo = activo
                    asesor.save(request)
                    log(u'Editó Asesor Comercial: %s' % asesor, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editventa':
            try:
                f = VentasMaestriasForm(request.POST)
                venta = VentasProgramaMaestria.objects.get(pk=int(request.POST['id']))
                val = False
                fac = False
                if f.is_valid():
                    if 'facturado' in request.POST:
                        fac = True

                    if 'valida' in request.POST:
                        val = True

                    venta.fecha = f.cleaned_data['fecha']
                    venta.facturado = fac
                    venta.valida = val
                    venta.save(request)
                    log(u'Editó venta: %s' % venta, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editmaestria':
            try:
                from posgrado.forms import CambioMaestriaForm
                f = CambioMaestriaForm(request.POST)
                data['id'] = id = int(request.POST['id'])
                inscrito = InscripcionCohorte.objects.get(pk=id)
                if f.is_valid():
                    maestrianueva = f.cleaned_data['maestriacambio']
                    if CohorteMaestria.objects.filter(status=True, maestriaadmision= maestrianueva, descripcion=inscrito.cohortes.descripcion).exists():
                        cohortenueva = CohorteMaestria.objects.get(status=True, maestriaadmision__carrera=maestrianueva.carrera, descripcion=inscrito.cohortes.descripcion)
                        # postulantes = InscripcionCohorte.objects.filter(status=True, cohortes=cohorte,
                        #                                                 cohortes_maestriaadmisioncarrera_id=236,
                        #                                                 itinerario=1).exclude(cohortes_id_in=[192, 206, 207]).order_by('id')
                        # c = 0
                        # for postulante in postulantes:
                        inscrito.cohortes = cohortenueva
                        inscrito.save()

                        requisitos = RequisitosMaestria.objects.filter(status=True, cohorte=cohortenueva)

                        for reqma in requisitos:
                            if EvidenciaRequisitosAspirante.objects.filter(inscripcioncohorte=inscrito, requisitos__requisito=reqma.requisito).exists():
                                evi = EvidenciaRequisitosAspirante.objects.filter(inscripcioncohorte=inscrito, requisitos__requisito=reqma.requisito).first()
                                evi.requisitos = reqma
                                evi.save()

                        if Rubro.objects.filter(status=True, inscripcion=inscrito).exists():
                            rubros = Rubro.objects.filter(status=True, inscripcion=inscrito)
                            for rubro in rubros:
                                rubro.cohortemaestria = cohortenueva
                                rubro.tipo = cohortenueva.tiporubro
                                rubro.save()
                        if inscrito.Configfinanciamientocohorte:
                            if ConfigFinanciamientoCohorte.objects.filter(descripcion=inscrito.Configfinanciamientocohorte.descripcion, cohorte=cohortenueva).exists():
                                finan = ConfigFinanciamientoCohorte.objects.filter(descripcion=inscrito.Configfinanciamientocohorte.descripcion, cohorte=cohortenueva).first()
                                inscrito.Configfinanciamientocohorte = finan
                                inscrito.save()
                        #print(f'{c}/{postulantes.count()} - Cedula: {postulante.inscripcionaspirante.persona.cedula} - {postulante}')
                        return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                             "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteasesor':
            try:
                with transaction.atomic():
                    instancia = AsesorComercial.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)

                    if instancia.rol.id == 1:
                        grupo = Group.objects.get(id=368)
                        grupo.user_set.remove(instancia.persona.usuario)
                        grupo.save()

                        grupo2 = Group.objects.get(id=365)
                        grupo2.user_set.remove(instancia.persona.usuario)
                        grupo2.save()

                    elif instancia.rol.id == 4:
                        grupo = Group.objects.get(name='ASESOR DE FINANCIAMIENTO')
                        grupo.user_set.remove(instancia.persona.usuario)
                        grupo.save()

                        grupo2 = Group.objects.get(id=365)
                        grupo2.user_set.remove(instancia.persona.usuario)
                        grupo2.save()

                    log(u'Elimino Asesor: %s' % instancia, request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        # elif action == 'delcomprobanteunemi':
        #     try:
        #         with transaction.atomic():
        #             instancia = ComprobanteAlumno.objects.get(pk=int(request.POST['id']))
        #             instancia.status = False
        #             instancia.save(request)
        #             log(u'Elimino Comprobante de pago: %s' % instancia, request, "del")
        #             res_json = {"error": False}
        #     except Exception as ex:
        #         res_json = {'error': True, "message": "Error: {}".format(ex)}
        #     return JsonResponse(res_json, safe=False)

        elif action == 'selectcohorte':
            try:
                if 'id' in request.POST:
                    lista = []
                    listaiti = []
                    tieneiti = "no"

                    cohortes = CohorteMaestria.objects.filter(maestriaadmision__carrera__id=int(request.POST['id']), procesoabierto=True)
                    for cohorte in cohortes:
                        lista.append([cohorte.id, cohorte.descripcion])

                    carrera = Carrera.objects.get(status=True, id=int(request.POST['id']))
                    if carrera.malla():
                        if carrera.malla().tiene_itinerario_malla_especialidad():
                            itinerarios = ItinerarioMallaEspecilidad.objects.filter(status=True, malla__id=carrera.malla().id)
                            for itine in itinerarios:
                                listaiti.append([itine.itinerario, itine.nombre])
                            tieneiti = "si"

                    return JsonResponse({"result": "ok", 'lista': lista, 'tieneiti':tieneiti, 'itinerarios':listaiti})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        elif action == 'selectcohorte2':
            try:
                if 'id' in request.POST:
                    lista = []
                    cohortes = CohorteMaestria.objects.filter(maestriaadmision_id=int(request.POST['id']), procesoabierto=True)
                    for cohorte in cohortes:
                        lista.append([cohorte.id, cohorte.descripcion])
                    return JsonResponse({"result": "ok", 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        elif action == 'selectcohorte3':
            try:
                if 'id' in request.POST:
                    lista = []
                    cohortes = CohorteMaestria.objects.filter(maestriaadmision_id=int(request.POST['id']))
                    for cohorte in cohortes:
                        lista.append([cohorte.id, cohorte.descripcion])
                    return JsonResponse({"result": "ok", 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        elif action == 'selectcohorte4':
            try:
                if 'id' in request.POST:
                    lista = []
                    cohortes = CohorteMaestria.objects.filter(maestriaadmision_id=int(request.POST['id']), asesormeta__asesor__persona_id=persona.id).distinct()
                    for cohorte in cohortes:
                        lista.append([cohorte.id, cohorte.descripcion])
                    return JsonResponse({"result": "ok", 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        elif action == 'rangofechas':
            try:
                if 'id' in request.POST:
                    cohorte = CohorteMaestria.objects.get(pk=int(request.POST['id']))
                    inicio = cohorte.fechainicioinsp
                    fin = cohorte.fechafininsp
                    cupo = cohorte.cupodisponible
                    cuposli = cohorte.cuposlibres
                    return JsonResponse({"result": "ok", 'iniinsc': inicio, 'fininsc':fin, 'cupo':cupo, 'cuposli':cuposli})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consulatar los datos."})

        elif action == 'consultacedula':
            try:
                cedula = request.POST['cedula'].strip()
                datospersona = None
                provinciaid = 0
                cantonid = 0
                cantonnom = ''
                lugarestudio = ''
                carrera = ''
                profesion = ''
                institucionlabora = ''
                cargo = ''
                teleoficina = ''
                idgenero = 0
                habilitaemail = 0
                if Persona.objects.filter(cedula=cedula).exists():
                    datospersona = Persona.objects.get(cedula=cedula)
                if Persona.objects.filter(pasaporte=cedula).exists():
                    datospersona = Persona.objects.get(pasaporte=cedula)
                if datospersona:
                    if datospersona.sexo:
                        idgenero = datospersona.sexo_id
                    return JsonResponse({"result": "ok", "idpersona": datospersona.id, "apellido1": datospersona.apellido1,
                                         "apellido2": datospersona.apellido2, "nombres": datospersona.nombres,
                                         "email": datospersona.email, "telefono": datospersona.telefono,
                                         "idgenero":idgenero, "idpais":datospersona.pais.id if datospersona.pais else 0,
                                         "idprovi":datospersona.provincia.id if datospersona.provincia else 0,
                                         "idcanton":datospersona.canton.id if datospersona.canton else 0,
                                         "direccion":datospersona.direccion})
                else:
                    return JsonResponse({"result": "no"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'asignarasesor':
            try:
                f = InscripcionCohorteForm(request.POST)
                lead = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                asesoranti = lead.asesor
                if f.is_valid():
                    lead.asesor = f.cleaned_data['asesor']
                    lead.estado_asesor = 2
                    if lead.tiporespuesta:
                        lead.tiporespuesta = None
                    lead.save(request)

                    if VentasProgramaMaestria.objects.filter(status=True, inscripcioncohorte=lead).exists():
                        venta = VentasProgramaMaestria.objects.get(status=True, inscripcioncohorte=lead)
                        venta.asesor_id = lead.asesor.id
                        venta.save()

                    if not asesoranti:
                        histo = HistorialAsesor(inscripcion_id=lead.id, fecha_inicio=lead.fecha_modificacion,
                                        fecha_fin=None, asesor=lead.asesor, observacion=f.cleaned_data['observacion'])
                        histo.save(request)
                    else:
                        histoanti = HistorialAsesor.objects.get(inscripcion_id=lead.id, fecha_fin=None)
                        histoanti.fecha_fin = lead.fecha_modificacion
                        histoanti.save(request)
                        histo = HistorialAsesor(inscripcion_id=lead.id, fecha_inicio=lead.fecha_modificacion,
                                        fecha_fin=None, asesor=lead.asesor, observacion=f.cleaned_data['observacion'])
                        histo.save(request)
                    log(u'Editó Inscripcion Cohorte(Asigna Asesor Comercial): %s' % lead, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'asignarterritorio':
            try:
                f = AsignarTerritorioForm(request.POST)
                asesor = AsesorComercial.objects.get(status=True, pk=int(request.POST['id']))
                if f.is_valid():
                    if not AsesorTerritorio.objects.filter(status=True, asesor=asesor, canton=f.cleaned_data['canton']).exists():
                        territorio = AsesorTerritorio(asesor=asesor, canton=f.cleaned_data['canton'])
                        territorio.save(request)

                        log(u'Asignó territorio al asesor: %s' % territorio, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({"result": True, "mensaje": u"Este territorio ya ha sido asignado al asesor"}, safe=False)
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'registro_user':
            try:
                browser = request.POST['navegador']
                ops = request.POST['os']
                cookies = request.POST['cookies']
                screensize = request.POST['screensize']
                arregloemail = [23, 24, 25, 26, 27, 28]
                emailaleatorio = random.choice(arregloemail)
                tipoconta = None
                tipobeca = None
                # if int(tipobeca) == 0:
                #     tipobeca = None
                idcarrera = request.POST['idcarrera']
                nomcarrera = Carrera.objects.get(pk=request.POST['idcarrera'])
                # idtitulo = request.POST['titulo']
                # cantexperiencia = request.POST['cantexperiencia']
                itinerario = 0
                if 'itinerario' in request.POST:
                    if request.POST['itinerario'] != '':
                        itinerario = request.POST['itinerario']
                hoy = datetime.now().date()
                f = RegistroAdmisionIpecForm(request.POST)
                if f.is_valid():
                    if (f.cleaned_data['cedula'][:2] == u'VS' or f.cleaned_data['cedula'][:2] == u'vs') and not Persona.objects.filter(pasaporte=f.cleaned_data['cedula'][2:]).exists():
                        # if not Persona.objects.filter(pasaporte=f.cleaned_data['cedula'][2:]).exists():
                            # if not Persona.objects.filter(email=f.cleaned_data['email']).exists():
                                persona = Persona(pasaporte=f.cleaned_data['cedula'][2:],
                                                  nombres=f.cleaned_data['nombres'],
                                                  apellido1=f.cleaned_data['apellido1'],
                                                  apellido2=f.cleaned_data['apellido2'],
                                                  email=f.cleaned_data['email'],
                                                  telefono=f.cleaned_data['telefono'],
                                                  sexo_id=request.POST['genero'],
                                                  nacimiento='1999-01-01',
                                                  pais_id=request.POST['pais'],
                                                  provincia_id=request.POST['provincia'],
                                                  canton_id=request.POST['canton'],
                                                  direccion=request.POST['direccion'],
                                                  direccion2=''
                                                  )
                                persona.save()
                                nomusername = calculate_username(persona)
                                persona.emailinst = nomusername + '@unemi.edu.ec'
                                persona.save()
                                generar_usuario_admision(persona, nomusername, 199)
                                if not InscripcionAspirante.objects.filter(persona=persona, status=True).exists():
                                    aspirante = InscripcionAspirante(persona=persona)
                                    aspirante.save()
                                else:
                                    aspirante = InscripcionAspirante.objects.filter(persona=persona, status=True)[0]
                                if CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True).exists():
                                    cohortemaestria = CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True)[0]
                                    if nomcarrera.malla():
                                        if nomcarrera.malla().tiene_itinerario_malla_especialidad():
                                            if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                        cohortes=cohortemaestria,
                                                                                        tipobeca_id=tipobeca,
                                                                                        contactomaestria=tipoconta,
                                                                                        # tiulacionaspirante_id=idtitulo,
                                                                                        # cantexperiencia=cantexperiencia,
                                                                                        formapagopac_id=1,
                                                                                        itinerario=request.POST['itinerario'],
                                                                                        doblepostulacion=True)
                                                inscripcioncohorte.save(request)
                                        else:
                                            if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                        cohortes=cohortemaestria,
                                                                                        tipobeca_id=tipobeca,
                                                                                        # tiulacionaspirante_id=idtitulo,
                                                                                        # cantexperiencia=cantexperiencia,
                                                                                        formapagopac_id=1,
                                                                                        contactomaestria=tipoconta,
                                                                                        doblepostulacion=True)
                                                inscripcioncohorte.save(request)
                                    else:
                                        if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                            inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                    cohortes=cohortemaestria,
                                                                                    tipobeca_id=tipobeca,
                                                                                    # tiulacionaspirante_id=idtitulo,
                                                                                    # cantexperiencia=cantexperiencia,
                                                                                    formapagopac_id=1,
                                                                                    contactomaestria=tipoconta,
                                                                                    doblepostulacion=True)
                                            inscripcioncohorte.save(request)
                                persona.crear_perfil(inscripcionaspirante=aspirante)
                                persona.mi_perfil()
                                lista = []
                                if persona.emailinst:
                                    lista.append(persona.emailinst)
                                if persona.email:
                                    lista.append(persona.email)
                                # resetear_clavepostulante(persona)
                                if persona.cedula:
                                    clavepostulante = persona.cedula.strip()
                                elif persona.pasaporte:
                                    clavepostulante = persona.pasaporte.strip()
                                validapersonal(aspirante, idcarrera, lista, nomcarrera, persona.usuario.username, clavepostulante)
                                # return HttpResponse(json.dumps({"result": "ok", "mensaje": "Usuario ya pre inscrito, te hemos enviado un email con tu usuario y clave para poder acceder a https://admisionposgrado.unemi.edu.ec/loginposgrado <a class='btn btn-success' href='https://admisionposgrado.unemi.edu.ec/loginposgrado' target='_blank'><i class='fa fa-arrow-right'></i> Ingresar</a> \n usuario:" + persona.usuario.username + " \n clave: " + clavepostulante + ""}), content_type="application/json")
                                return HttpResponse(json.dumps({"result": "ok", "mensaje": "Gracias por su registro, revise el correo electrónico para más información, pronto un asesor/a se contactará."}), content_type="application/json")
                            # else:
                            #     return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Correo ya existe, si no recuerda el usuario y la clave, siga los pasos en la opción, Olvidó su usuario y contraseña?.: "}), content_type="application/json")
                        # else:
                        #     return HttpResponse(json.dumps({"result": "bad", "mensaje": "Persona ya existe.: "}), content_type="application/json")
                    else:
                        if not Persona.objects.filter(Q(cedula=f.cleaned_data['cedula']) | Q(pasaporte=f.cleaned_data['cedula'])).exists():
                            # if not Persona.objects.filter(email=f.cleaned_data['email']).exists():
                            persona = Persona(cedula=f.cleaned_data['cedula'],
                                              nombres=f.cleaned_data['nombres'],
                                              apellido1=f.cleaned_data['apellido1'],
                                              apellido2=f.cleaned_data['apellido2'],
                                              email=f.cleaned_data['email'],
                                              telefono=f.cleaned_data['telefono'],
                                              sexo_id=request.POST['genero'],
                                              nacimiento='1999-01-01',
                                              pais_id=request.POST['pais'],
                                              provincia_id=request.POST['provincia'],
                                              canton_id=request.POST['canton'],
                                              direccion=request.POST['direccion'],
                                              direccion2=''
                                              )
                            persona.save()
                            nomusername = calculate_username(persona)
                            persona.emailinst = nomusername + '@unemi.edu.ec'
                            persona.save()
                            generar_usuario_admision(persona, nomusername, 199)
                            aspirante = InscripcionAspirante(persona=persona)
                            aspirante.save()
                            if CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True).exists():
                                cohortemaestria = CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True)[0]
                                if nomcarrera.malla():
                                    if nomcarrera.malla().tiene_itinerario_malla_especialidad():
                                        if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                            inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                    cohortes=cohortemaestria,
                                                                                    tipobeca_id=tipobeca,
                                                                                    contactomaestria=tipoconta,
                                                                                    # tiulacionaspirante_id=idtitulo,
                                                                                    # cantexperiencia=cantexperiencia,
                                                                                    formapagopac_id=1,
                                                                                    itinerario=request.POST['itinerario'],
                                                                                    doblepostulacion=True)
                                            inscripcioncohorte.save(request)
                                    else:
                                        if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                            inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                    cohortes=cohortemaestria,
                                                                                    tipobeca_id=tipobeca,
                                                                                    # tiulacionaspirante_id=idtitulo,
                                                                                    # cantexperiencia=cantexperiencia,
                                                                                    formapagopac_id=1,
                                                                                    contactomaestria=tipoconta,
                                                                                    doblepostulacion=True)
                                            inscripcioncohorte.save(request)
                                else:
                                    if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                        inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                cohortes=cohortemaestria,
                                                                                tipobeca_id=tipobeca,
                                                                                # tiulacionaspirante_id=idtitulo,
                                                                                # cantexperiencia=cantexperiencia,
                                                                                formapagopac_id=1,
                                                                                contactomaestria=tipoconta,
                                                                                doblepostulacion=True)
                                        inscripcioncohorte.save(request)
                            persona.crear_perfil(inscripcionaspirante=aspirante)
                            persona.mi_perfil()
                            lista = []
                            if persona.emailinst:
                                lista.append(persona.emailinst)
                            if persona.email:
                                lista.append(persona.email)
                            # resetear_clavepostulante(persona)
                            if persona.cedula:
                                clavepostulante = persona.cedula.strip()
                            elif persona.pasaporte:
                                clavepostulante = persona.pasaporte.strip()
                            validapersonal(aspirante, idcarrera, lista, nomcarrera, persona.usuario.username, clavepostulante)
                            # return HttpResponse(json.dumps({"result": "ok", "mensaje": "Usuario ya pre inscrito, te hemos enviado un email con tu usuario y clave para poder acceder a https://admisionposgrado.unemi.edu.ec/loginposgrado <a class='btn btn-success' href='https://admisionposgrado.unemi.edu.ec/loginposgrado' target='_blank'><i class='fa fa-arrow-right'></i> Ingresar</a> \n usuario:" + persona.usuario.username + " \n clave: " + clavepostulante + ""}), content_type="application/json")
                            return HttpResponse(json.dumps({"result": "ok", "mensaje": "Gracias por su registro, revise el correo electrónico para más información, pronto un asesor/a se contactará."}), content_type="application/json")
                        else:
                            postulante = Persona.objects.get(Q(cedula=f.cleaned_data['cedula']) | Q(pasaporte=f.cleaned_data['cedula']), status=True)
                            # valida ya está graduado en la maestria
                            graduado = Graduado.objects.filter(status=True, inscripcion__persona=postulante)
                            if graduado.values('id').filter(inscripcion__carrera=nomcarrera).exists():
                                raise NameError(u"Usted ya se encuentra graduado en la maestría seleccionada, por favor intente con otra")
                            obtenerinscripcion = None
                            # valida ya está registrado en la maestria
                            if InscripcionCohorte.objects.values('id').filter(inscripcionaspirante__persona=postulante,
                                                                              cohortes__maestriaadmision__carrera=nomcarrera,
                                                                              activo=True, status=True).exists():
                                if nomcarrera.id == 215:
                                    if InscripcionCohorte.objects.values('id').filter(inscripcionaspirante__persona=postulante,
                                                                                      cohortes__maestriaadmision__carrera=nomcarrera,
                                                                                      itinerario=itinerario,
                                                                                      activo=True, status=True).exists():
                                        raise NameError(u"Usted ya se encuentra registrado en la maestría seleccionada, por favor intente con otra")
                                else:
                                    raise NameError(u"Usted ya se encuentra registrado en la maestría seleccionada, por favor intente con otra")

                            #     obtenerinscripcion = InscripcionCohorte.objects.filter(inscripcionaspirante__persona=postulante,
                            #                                                            cohortes__maestriaadmision__carrera=nomcarrera,
                            #                                                            activo=True, status=True)[0]
                            #     raise NameError(u"Usted ya se encuentra registrado, en la cohorte %s. Un asesor/a lo contactará en el menor tiempo posible, revise su correo electrónico para más información." % (obtenerinscripcion.cohortes))
                            # valida si no esta registrado en otras maestrias
                            # inscripcionesenotracohortes = InscripcionCohorte.objects.filter(inscripcionaspirante__persona=postulante,
                            #                                                                 activo=True,
                            #                                                                 status=True).exclude(
                            #     cohortes__maestriaadmision__carrera=nomcarrera)
                            # if inscripcionesenotracohortes.values('id').exists():
                            #     for otracohorte in inscripcionesenotracohortes:
                            #         if not graduado.values('id').filter(inscripcion__carrera=otracohorte.cohortes.maestriaadmision.carrera).exists():
                            #             raise NameError(u"Usted ya esta registrado en la maestría %s" % (otracohorte.cohortes.maestriaadmision.carrera))

                            lista = []
                            if postulante.emailinst:
                                lista.append(postulante.emailinst)
                            if postulante.email:
                                lista.append(postulante.email)
                                if not postulante.usuario:
                                    nomusername = calculate_username(postulante)
                                    generar_usuario_admision(postulante, nomusername, 199)
                                else:
                                    nomusername = postulante.usuario.username
                                if not postulante.emailinst:
                                    postulante.emailinst = nomusername + '@unemi.edu.ec'
                                postulante.save()
                                if not InscripcionAspirante.objects.filter(persona=postulante, status=True).exists():
                                    aspirante = InscripcionAspirante(persona=postulante)
                                    aspirante.save(request)
                                else:
                                    aspirante = InscripcionAspirante.objects.filter(persona=postulante, status=True)[0]
                                if not PerfilUsuario.objects.filter(persona=postulante, inscripcionaspirante=aspirante).exists():
                                    postulante.crear_perfil(inscripcionaspirante=aspirante)
                                postulante.mi_perfil()
                                if CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True).exists():
                                    cohortemaestria = CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True)[0]
                                    if nomcarrera.malla():
                                        if nomcarrera.malla().tiene_itinerario_malla_especialidad():
                                            if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante, cohortes=cohortemaestria, tipobeca_id=tipobeca,
                                                                                        # tiulacionaspirante_id=idtitulo,
                                                                                        # cantexperiencia=cantexperiencia,
                                                                                        formapagopac_id=1,
                                                                                        contactomaestria=tipoconta, itinerario=request.POST['itinerario'], doblepostulacion=True)
                                                inscripcioncohorte.save(request)
                                        else:
                                            if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante, cohortes=cohortemaestria, tipobeca_id=tipobeca,
                                                                                        # tiulacionaspirante_id=idtitulo,
                                                                                        # cantexperiencia=cantexperiencia,
                                                                                        formapagopac_id=1, contactomaestria=tipoconta, doblepostulacion=True)
                                                inscripcioncohorte.save(request)
                                    else:
                                        if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                            inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante, cohortes=cohortemaestria, tipobeca_id=tipobeca,
                                                                                    # tiulacionaspirante_id=idtitulo,
                                                                                    #     cantexperiencia=cantexperiencia,
                                                                                    formapagopac_id=1, contactomaestria=tipoconta, doblepostulacion=True)
                                            inscripcioncohorte.save(request)
                                if postulante.cedula:
                                    clavepostulante = postulante.cedula.strip()
                                elif postulante.pasaporte:
                                    clavepostulante = postulante.pasaporte.strip()
                                # resetear_clavepostulante(postulante)

                                if postulante.es_administrativo() and postulante.es_personalactivo():
                                    validapersonalinterno(postulante, idcarrera, hoy, request, lista, nomcarrera, tipobeca, tipoconta, itinerario)
                                    # return HttpResponse(json.dumps({"result": "ok", "mensaje": "Usuario ya pre inscrito, favor acceder con las mismas credenciales del SGA o SAGEST a https://admisionposgrado.unemi.edu.ec/loginposgrado <a class='btn btn-success' href='https://admisionposgrado.unemi.edu.ec/loginposgrado' target='_blank'><i class='fa fa-arrow-right'></i> Ingresar</a> "}), content_type="application/json")
                                    return HttpResponse(json.dumps({"result": "ok", "mensaje": "Gracias por su registro, revise el correo electrónico para más información, pronto un asesor/a se contactará."}), content_type="application/json")
                                if postulante.es_profesor() and postulante.es_personalactivo():
                                    validapersonalinterno(postulante, idcarrera, hoy, request, lista, nomcarrera, tipobeca, tipoconta, itinerario)
                                    return HttpResponse(json.dumps({"result": "ok", "mensaje": "Gracias por su registro, revise el correo electrónico para más información, pronto un asesor/a se contactará."}), content_type="application/json")

                                validapersonal(aspirante, idcarrera, lista, nomcarrera, postulante.usuario.username, clavepostulante)
                                return HttpResponse(json.dumps({"result": "ok", "mensaje": "Gracias por su registro, revise el correo electrónico para más información, pronto un asesor/a se contactará."}), content_type="application/json")
                            if postulante.es_estudiante() and not postulante.es_personalactivo():
                                if not InscripcionAspirante.objects.filter(persona=postulante):
                                    nomusername = postulante.usuario.username
                                    postulante.email = f.cleaned_data['email']
                                    postulante.save()
                                    aspirante = InscripcionAspirante(persona=postulante)
                                    aspirante.save()
                                    if CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True).exists():
                                        cohortemaestria = CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True)[0]
                                        if nomcarrera.malla():
                                            if nomcarrera.malla().tiene_itinerario_malla_especialidad():
                                                if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                    inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                            cohortes=cohortemaestria,
                                                                                            tipobeca_id=tipobeca,
                                                                                            contactomaestria=tipoconta,
                                                                                            # tiulacionaspirante_id=idtitulo,
                                                                                            # cantexperiencia=cantexperiencia,
                                                                                            formapagopac_id=1,
                                                                                            itinerario=request.POST['itinerario'], doblepostulacion=True)
                                                    inscripcioncohorte.save(request)
                                            else:
                                                if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                    inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                            cohortes=cohortemaestria,
                                                                                            tipobeca_id=tipobeca,
                                                                                            # tiulacionaspirante_id=idtitulo,
                                                                                            # cantexperiencia=cantexperiencia,
                                                                                            formapagopac_id=1,
                                                                                            contactomaestria=tipoconta, doblepostulacion=True)
                                                    inscripcioncohorte.save(request)
                                        else:
                                            if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                        cohortes=cohortemaestria,
                                                                                        tipobeca_id=tipobeca,
                                                                                        # tiulacionaspirante_id=idtitulo,
                                                                                        # cantexperiencia=cantexperiencia,
                                                                                        formapagopac_id=1,
                                                                                        contactomaestria=tipoconta, doblepostulacion=True)
                                                inscripcioncohorte.save(request)
                                    postulante.crear_perfil(inscripcionaspirante=aspirante)
                                    postulante.mi_perfil()
                                    usuario = User.objects.get(pk=postulante.usuario.id)
                                    g = Group.objects.get(pk=199)
                                    g.user_set.add(usuario)
                                    g.save()
                                    # resetear_clavepostulante(postulante)
                                    postulante.emailinst = postulante.usuario.username + '@unemi.edu.ec'
                                    postulante.save()
                                    if postulante.cedula:
                                        clavepostulante = postulante.cedula.strip()
                                    elif postulante.pasaporte:
                                        clavepostulante = postulante.pasaporte.strip()
                                    validapersonal(aspirante, idcarrera, lista, nomcarrera, postulante.usuario.username, postulante.identificacion())
                                    # return HttpResponse(json.dumps({"result": "ok", "mensaje": "Usuario ya pre inscrito, te hemos enviado un email con tu usuario y clave para poder acceder a https://admisionposgrado.unemi.edu.ec/loginposgrado <a class='btn btn-success' href='https://admisionposgrado.unemi.edu.ec/loginposgrado' target='_blank'><i class='fa fa-arrow-right'></i> Ingresar</a> \n usuario:"+ postulante.usuario.username +" \n clave: " + clavepostulante + ""}), content_type="application/json")
                                    return HttpResponse(json.dumps({"result": "ok", "mensaje": "Gracias por su registro, revise el correo electrónico para más información, pronto un asesor/a se contactará."}), content_type="application/json")
                                else:
                                    aspirante = InscripcionAspirante.objects.filter(persona=postulante, status=True)[0]
                                    if CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True).exists():
                                        cohortemaestria = CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True)[0]
                                        if nomcarrera.malla():
                                            if nomcarrera.malla().tiene_itinerario_malla_especialidad():
                                                if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                    inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                            cohortes=cohortemaestria,
                                                                                            tipobeca_id=tipobeca,
                                                                                            contactomaestria=tipoconta,
                                                                                            # tiulacionaspirante_id=idtitulo,
                                                                                            # cantexperiencia=cantexperiencia,
                                                                                            formapagopac_id=1,
                                                                                            itinerario=request.POST['itinerario'],
                                                                                            doblepostulacion=True)
                                                    inscripcioncohorte.save(request)
                                            else:
                                                if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                    inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                            cohortes=cohortemaestria,
                                                                                            tipobeca_id=tipobeca,
                                                                                            # tiulacionaspirante_id=idtitulo,
                                                                                            # cantexperiencia=cantexperiencia,
                                                                                            formapagopac_id=1,
                                                                                            contactomaestria=tipoconta,
                                                                                            doblepostulacion=True)
                                                    inscripcioncohorte.save(request)
                                        else:
                                            if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                        cohortes=cohortemaestria,
                                                                                        tipobeca_id=tipobeca,
                                                                                        # tiulacionaspirante_id=idtitulo,
                                                                                        # cantexperiencia=cantexperiencia,
                                                                                        formapagopac_id=1,
                                                                                        contactomaestria=tipoconta,
                                                                                        doblepostulacion=True)
                                                inscripcioncohorte.save(request)
                                    nomusername = postulante.usuario.username
                                    postulante.email = f.cleaned_data['email']
                                    postulante.save()
                                    # resetear_clavepostulante(postulante)
                                    if postulante.cedula:
                                        clavepostulante = postulante.cedula.strip()
                                    elif postulante.pasaporte:
                                        clavepostulante = postulante.pasaporte.strip()
                                    validapersonal(aspirante, idcarrera, lista, nomcarrera, postulante.usuario.username, clavepostulante)
                                    # return HttpResponse(json.dumps({"result": "ok", "mensaje": "Usuario ya pre inscrito, te hemos enviado un email con tu usuario y clave para poder acceder a https://admisionposgrado.unemi.edu.ec/loginposgrado <a class='btn btn-success' href='https://admisionposgrado.unemi.edu.ec/loginposgrado' target='_blank'><i class='fa fa-arrow-right'></i> Ingresar</a> \n usuario:"+ postulante.usuario.username +" \n clave: " + clavepostulante + ""}), content_type="application/json")
                                    return HttpResponse(json.dumps({"result": "ok", "mensaje": "Gracias por su registro, revise el correo electrónico para más información, pronto un asesor/a se contactará."}), content_type="application/json")
                                validapersonal(aspirante, idcarrera, lista, nomcarrera, postulante.usuario.username, postulante.identificacion())
                            if postulante.externo_set.filter(status=True) and not postulante.es_personalactivo():
                                if not InscripcionAspirante.objects.filter(persona=postulante):
                                    if not postulante.usuario:
                                        nomusername = calculate_username(postulante)
                                        generar_usuario_admision(postulante, nomusername, 199)
                                    else:
                                        nomusername = postulante.usuario.username
                                    postulante.email = f.cleaned_data['email']
                                    postulante.emailinst = f.cleaned_data['email']
                                    postulante.save()
                                    aspirante = InscripcionAspirante(persona=postulante)
                                    aspirante.save()
                                    if CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True).exists():
                                        cohortemaestria = CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True)[0]
                                        if nomcarrera.malla():
                                            if nomcarrera.malla().tiene_itinerario_malla_especialidad():
                                                if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                    inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                            cohortes=cohortemaestria,
                                                                                            tipobeca_id=tipobeca,
                                                                                            contactomaestria=tipoconta,
                                                                                            # tiulacionaspirante_id=idtitulo,
                                                                                            # cantexperiencia=cantexperiencia,
                                                                                            formapagopac_id=1,
                                                                                            itinerario=request.POST['itinerario'],
                                                                                            doblepostulacion=True)
                                                    inscripcioncohorte.save(request)
                                            else:
                                                if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                    inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                            cohortes=cohortemaestria,
                                                                                            tipobeca_id=tipobeca,
                                                                                            # tiulacionaspirante_id=idtitulo,
                                                                                            # cantexperiencia=cantexperiencia,
                                                                                            formapagopac_id=1,
                                                                                            contactomaestria=tipoconta,
                                                                                            doblepostulacion=True)
                                                    inscripcioncohorte.save(request)
                                        else:
                                            if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                        cohortes=cohortemaestria,
                                                                                        tipobeca_id=tipobeca,
                                                                                        # tiulacionaspirante_id=idtitulo,
                                                                                        # cantexperiencia=cantexperiencia,
                                                                                        formapagopac_id=1,
                                                                                        contactomaestria=tipoconta,
                                                                                        doblepostulacion=True)
                                                inscripcioncohorte.save(request)
                                    postulante.crear_perfil(inscripcionaspirante=aspirante)
                                    postulante.mi_perfil()
                                    usuario = User.objects.get(pk=postulante.usuario.id)
                                    g = Group.objects.get(pk=199)
                                    g.user_set.add(usuario)
                                    g.save()
                                    # resetear_clavepostulante(postulante)
                                    postulante.emailinst = postulante.usuario.username + '@unemi.edu.ec'
                                    postulante.save()
                                    lista = []
                                    if postulante.emailinst:
                                        lista.append(postulante.emailinst)
                                    if postulante.email:
                                        lista.append(postulante.email)
                                    if postulante.cedula:
                                        clavepostulante = postulante.cedula.strip()
                                    elif postulante.pasaporte:
                                        clavepostulante = postulante.pasaporte.strip()
                                    validapersonal(aspirante, idcarrera, lista, nomcarrera, postulante.usuario.username, clavepostulante)
                                    # send_html_mail("Registro exitoso Admision-UNEMI.", "emails/registroexitoadmisionposgrado.html", {'sistema': u'Admision - UNEMI', 'preinscrito': postulante,'usuario': postulante.usuario.username,'clave': postulante.identificacion(), 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'os': ops, 'cookies': cookies,'screensize': screensize, 't': miinstitucion()}, postulante.emailpersonal(),  [], cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])
                                    return HttpResponse(json.dumps({"result": "ok", "usu": nomusername}), content_type="application/json")
                            if postulante.inscripcionaspirante_set.filter(status=True) and not postulante.es_personalactivo():
                                aspirante = InscripcionAspirante.objects.filter(persona=postulante, status=True)[0]
                                if CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy,  activo=True, status=True).exists():
                                    cohortemaestria = CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True)[0]
                                    if nomcarrera.malla():
                                        if nomcarrera.malla().tiene_itinerario_malla_especialidad():
                                            if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                        cohortes=cohortemaestria,
                                                                                        tipobeca_id=tipobeca,
                                                                                        contactomaestria=tipoconta,
                                                                                        # tiulacionaspirante_id=idtitulo,
                                                                                        # cantexperiencia=cantexperiencia,
                                                                                        formapagopac_id=1,
                                                                                        itinerario=request.POST['itinerario'],
                                                                                        doblepostulacion=True)
                                                inscripcioncohorte.save(request)
                                        else:
                                            if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                        cohortes=cohortemaestria,
                                                                                        tipobeca_id=tipobeca,
                                                                                        # tiulacionaspirante_id=idtitulo,
                                                                                        # cantexperiencia=cantexperiencia,
                                                                                        formapagopac_id=1,
                                                                                        contactomaestria=tipoconta,
                                                                                        doblepostulacion=True)
                                                inscripcioncohorte.save(request)
                                    else:
                                        if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                            inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                    cohortes=cohortemaestria,
                                                                                    tipobeca_id=tipobeca,
                                                                                    # tiulacionaspirante_id=idtitulo,
                                                                                    # cantexperiencia=cantexperiencia,
                                                                                    formapagopac_id=1,
                                                                                    contactomaestria=tipoconta,
                                                                                    doblepostulacion=True)
                                            inscripcioncohorte.save(request)
                                if not postulante.emailinst:
                                    # resetear_clavepostulante(postulante)
                                    postulante.emailinst = postulante.usuario.username + '@unemi.edu.ec'
                                    postulante.save()
                                lista = []
                                if postulante.emailinst:
                                    lista.append(postulante.emailinst)
                                if postulante.email:
                                    lista.append(postulante.email)
                                if postulante.cedula:
                                    clavepostulante = postulante.cedula.strip()
                                elif postulante.pasaporte:
                                    clavepostulante = postulante.pasaporte.strip()
                                # resetear_clavepostulante(postulante)
                                validapersonal(aspirante, idcarrera, lista, nomcarrera, postulante.usuario.username, clavepostulante)
                                # return HttpResponse(json.dumps({"result": "ok", "mensaje": "Usuario ya pre inscrito, te hemos enviado un email con tu usuario y clave para poder acceder a https://admisionposgrado.unemi.edu.ec/loginposgrado <a class='btn btn-success' href='https://admisionposgrado.unemi.edu.ec/loginposgrado' target='_blank'><i class='fa fa-arrow-right'></i> Ingresar</a> \n usuario:"+ postulante.usuario.username +" \n clave: " + clavepostulante + "  "}), content_type="application/json")
                                return HttpResponse(json.dumps({"result": "ok", "mensaje": "Gracias por su registro, revise el correo electrónico para más información, pronto un asesor/a se contactará."}), content_type="application/json")
                                # return HttpResponse(json.dumps({"result": "bad", "mensaje": "Persona ya existe, favor ingresar con su usuario y clave.: "}), content_type="application/json")
                            if postulante.es_administrativo() and postulante.es_personalactivo():
                                validapersonalinterno(postulante,idcarrera,hoy,request, lista, nomcarrera,tipobeca, tipoconta, itinerario)
                                return HttpResponse(json.dumps({"result": "ok", "mensaje": "Gracias por su registro, revise el correo electrónico para más información, pronto un asesor/a se contactará."}), content_type="application/json")
                            if postulante.es_profesor() and postulante.es_personalactivo():
                                validapersonalinterno(postulante,idcarrera,hoy,request, lista, nomcarrera,tipobeca, tipoconta, itinerario)
                                return HttpResponse(json.dumps({"result": "ok", "mensaje": "Gracias por su registro, revise el correo electrónico para más información, pronto un asesor/a se contactará."}), content_type="application/json")
                            return HttpResponse(json.dumps({"result": "bad", "mensaje": "Error al guardar.: "}), content_type="application/json")
                    return HttpResponse(json.dumps({"result": "ok", "mensaje": "Gracias por su registro, revise el correo electrónico para más información, pronto un asesor/a se contactará."}), content_type="application/json")
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addmeta':
            try:
                f = AsesorMetaForm(request.POST)
                if f.is_valid():
                    asesormeta = AsesorMeta(asesor_id=int(request.POST['id']),
                                            cohorte_id=f.cleaned_data['cohorte'].id,
                                            fecha_inicio_meta=f.cleaned_data['fechainiciometa'],
                                            fecha_fin_meta=f.cleaned_data['fechafinmeta'],
                                            meta=f.cleaned_data['meta'])
                                             # maestriaadmision = f.cleaned_data['maestriaadmision'])
                    asesormeta.save(request)
                    cohorte = CohorteMaestria.objects.get(id=f.cleaned_data['cohorte'].id)

                    if asesormeta.meta <= cohorte.cuposlibres:
                        cohorte.cuposlibres = cohorte.cuposlibres - asesormeta.meta
                        cohorte.save(request)
                    else:
                        raise NameError("La meta ingresada excede el numero de cupos libres.")

                    log(u'Adicionó una Meta a un Asesor Comercial: %s' % asesormeta, request, "add")
                    return JsonResponse({"result": 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": "Datos erróneos. %s" % ex.__str__()}, safe=False)

        elif action == 'addmetamasiva':
            try:
                idasesores = request.POST['id'].split(',')
                if not idasesores[0] == '':
                    idcohorte = int(request.POST['idc'])
                    cohorte = CohorteMaestria.objects.get(status=True, pk=idcohorte)
                    meta = 0
                    for idasesor in idasesores:
                        asesor = AsesorComercial.objects.get(status=True, pk=idasesor)

                        if not AsesorMeta.objects.filter(status=True, cohorte=cohorte, asesor=asesor).exists():
                            asesormeta = AsesorMeta(asesor=asesor,
                                                    cohorte=cohorte,
                                                    fecha_inicio_meta=cohorte.fechainicioinsp,
                                                    fecha_fin_meta=cohorte.fechafininsp,
                                                    meta=meta)
                            asesormeta.save(request)

                            log(u'Adicionó una Meta a un Asesor Comercial: %s' % asesormeta, request, "add")

                        if not AsesorMeta.objects.filter(status=True, maestria=cohorte.maestriaadmision, asesor=asesor).exists():
                            asesormeta2 = AsesorMeta(asesor=asesor,
                                                    maestria=cohorte.maestriaadmision,
                                                    meta=0)
                            asesormeta2.save(request)

                            log(u'Adicionó una Meta de maestría a un Asesor Comercial: %s' % asesormeta, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                    return JsonResponse({"result": False, "mensaje": "Por favor, seleccione al menos 1 asesor."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": "Datos erróneos. %s" % ex.__str__()}, safe=False)

        elif action == 'asignarmaestria':
            try:
                maestria = MaestriasAdmision.objects.get(status=True, pk=int(request.POST['idc']))
                asesor = AsesorComercial.objects.get(status=True, pk=int(request.POST['ida']))

                if not AsesorMeta.objects.filter(status=True, maestria=maestria, asesor=asesor).exists():
                    asesormeta = AsesorMeta(asesor=asesor,
                                            maestria=maestria,
                                            meta=0)
                    asesormeta.save(request)

                    log(u'Adicionó una maestria al asesor comercial: %s' % asesormeta, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                    return JsonResponse({"result": False, "mensaje": "Por favor, seleccione al menos 1 asesor."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": "Datos erróneos. %s" % ex.__str__()}, safe=False)

        elif action == 'asignarconvenio':
            try:
                from posgrado.models import Convenio, ConvenioAsesor
                convenio = Convenio.objects.get(status=True, pk=int(request.POST['idc']))
                asesor = AsesorComercial.objects.get(status=True, pk=int(request.POST['ida']))

                if request.POST['fechFin'] == '':
                    raise NameError("Seleccione una fecha.")
                if datetime.strptime(request.POST['fechFin'],'%Y-%m-%d').date() <= convenio.fechaInicio:
                    raise NameError("Seleccione una fecha mayor a la fecha inicio del convenio.")
                if not ConvenioAsesor.objects.filter(status=True, convenio=convenio, asesor=asesor).exists():
                    convenioasesor = ConvenioAsesor(asesor=asesor,
                                            convenio=convenio,
                                            fechaFin=request.POST['fechFin'])
                    convenioasesor.save(request)

                    log(u'Adicionó un convenio al asesor comercial: %s' % convenioasesor, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                    return JsonResponse({"result": False, "mensaje": "Por favor, seleccione al menos 1 asesor."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": "Datos erróneos. %s" % ex.__str__()}, safe=False)

        elif action == 'asignarcohortemaestria':
            try:
                cohorte = CohorteMaestria.objects.get(status=True, pk=int(request.POST['idc']))
                asesor = AsesorComercial.objects.get(status=True, pk=int(request.POST['ida']))

                if not AsesorMeta.objects.filter(status=True, cohorte=cohorte, asesor=asesor).exists():
                    asesormeta = AsesorMeta(asesor=asesor,
                                            cohorte=cohorte,
                                            fecha_inicio_meta=cohorte.fechainicioinsp,
                                            fecha_fin_meta=cohorte.fechafininsp,
                                            meta=0)
                    asesormeta.save(request)

                    log(u'Adicionó una cohorte al asesor comercial: %s' % asesormeta, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                    return JsonResponse({"result": False, "mensaje": "Por favor, seleccione al menos 1 asesor."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": "Datos erróneos. %s" % ex.__str__()}, safe=False)

        elif action == 'retirarmaestria':
            try:
                asesormeta = AsesorMeta.objects.get(status=True, pk=int(request.POST['id']))

                asesormeta.status = False
                asesormeta.save(request)

                log(u'Retiró una maestria al asesor comercial: %s' % asesormeta, request, "del")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": "Datos erróneos. %s" % ex.__str__()}, safe=False)

        elif action == 'retirarconvenio':
            try:
                from posgrado.models import ConvenioAsesor
                convenioasesor = ConvenioAsesor.objects.get(status=True, pk=int(request.POST['id']))

                convenioasesor.status = False
                convenioasesor.save(request)

                log(u'Retiró un convenio al asesor comercial: %s' % convenioasesor, request, "del")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": "Datos erróneos. %s" % ex.__str__()}, safe=False)

        elif action == 'editmeta':
            try:
                f = AsesorMetaForm(request.POST)
                asesormeta = AsesorMeta.objects.get(pk=int(request.POST['id']))
                metaanterior = asesormeta.meta
                # asesormeta = AsesorMeta.objects.get(asesor__id=asesor.id)
                if f.is_valid():
                    asesormeta.fecha_inicio_meta = f.cleaned_data['fechainiciometa']
                    asesormeta.fecha_fin_meta = f.cleaned_data['fechafinmeta']
                    asesormeta.meta = f.cleaned_data['meta']
                    asesormeta.cohorte = f.cleaned_data['cohorte']
                    asesormeta.save(request)

                    cohorte = CohorteMaestria.objects.get(id=f.cleaned_data['cohorte'].id)

                    if asesormeta.meta <= cohorte.cuposlibres:
                        if metaanterior > asesormeta.meta:
                            metaactual = metaanterior - asesormeta.meta
                            cohorte.cuposlibres = cohorte.cuposlibres + metaactual
                            cohorte.save(request)
                        else:
                            metaactual = asesormeta.meta - metaanterior
                            cohorte.cuposlibres = cohorte.cuposlibres - metaactual
                            cohorte.save(request)
                    elif cohorte.cuposlibres == 0 and asesormeta.meta < metaanterior:
                        metaactual = metaanterior - asesormeta.meta
                        cohorte.cuposlibres = cohorte.cuposlibres + metaactual
                        cohorte.save(request)
                    else:
                        raise NameError("La meta ingresada excede el numero de cupos libres.")

                    log(u'Editò una Meta a un Asesor Comercial: %s' % asesormeta, request, "edit")
                    return JsonResponse({"result": 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": "Datos erróneos. %s" % ex.__str__()}, safe=False)

        elif action == 'deletemeta':
            try:
                with transaction.atomic():
                    instancia = AsesorMeta.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino una Meta del asesor: %s' % instancia, request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'confirmar_pre_asignacion':
            try:
                f = ConfirmarPreAsignacionForm(request.POST)
                lead = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                asesoranti = lead.asesor
                if f.is_valid():
                    lead.asesor = f.cleaned_data['asesor']
                    lead.estado_asesor = f.cleaned_data['estado_asesor']
                    lead.save(request)

                    if not asesoranti:
                        histo = HistorialAsesor(inscripcion_id=lead.id, fecha_inicio=lead.fecha_modificacion,
                                        fecha_fin=None, asesor=lead.asesor, observacion=f.cleaned_data['observacion'])
                        histo.save(request)
                    else:
                        histoanti = HistorialAsesor.objects.get(inscripcion_id=lead.id, fecha_fin=None)
                        histoanti.fecha_fin = lead.fecha_modificacion
                        histoanti.save(request)
                        histo = HistorialAsesor(inscripcion_id=lead.id, fecha_inicio=lead.fecha_modificacion,
                                        fecha_fin=None, asesor=lead.asesor, observacion=f.cleaned_data['observacion'])
                        histo.save(request)
                    log(u'Confirmo la pre asignacion de un asesor comercial(Asigna Asesor Comercial): %s' % lead, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'reasignacionmasiva':
            try:
                with transaction.atomic():
                    f = ReasignarMasivoForm(request.POST)
                    if f.is_valid():
                        asesor = AsesorComercial.objects.get(id=int(f.cleaned_data['asesor'].id))
                        leadsselect = request.POST['ids'].split(',')
                        observacion = f.cleaned_data['observacion']
                        for le in leadsselect:
                            if not HistorialReservacionProspecto.objects.filter(status=True, inscripcion__id=le).exists():
                                lead = InscripcionCohorte.objects.get(pk=le)
                                if not lead.asesor:
                                    lead.asesor = asesor
                                    lead.estado_asesor = 2

                                    if lead.tiporespuesta:
                                        lead.tiporespuesta = None

                                    lead.save(request)

                                    histo = HistorialAsesor(inscripcion_id=lead.id, fecha_inicio=lead.fecha_modificacion,
                                                    fecha_fin=None, asesor=lead.asesor, observacion=observacion)
                                    histo.save(request)
                                else:
                                    if not lead.asesor == asesor:
                                        lead.asesor = asesor
                                        lead.estado_asesor = 2

                                        if lead.tiporespuesta:
                                            lead.tiporespuesta = None
                                        lead.save(request)

                                        histoanti = HistorialAsesor.objects.get(inscripcion_id=lead.id, fecha_fin=None)
                                        histoanti.fecha_fin = lead.fecha_modificacion
                                        histoanti.save(request)
                                        histo = HistorialAsesor(inscripcion_id=lead.id, fecha_inicio=lead.fecha_modificacion,
                                                        fecha_fin=None, asesor=lead.asesor, observacion=observacion)
                                        histo.save(request)
                            elif InscripcionCohorte.objects.filter(status=True, asesor__activo=False, pk=le).exists():
                                lead = InscripcionCohorte.objects.get(pk=le)
                                if not lead.asesor:
                                    lead.asesor = asesor
                                    lead.estado_asesor = 2

                                    if lead.tiporespuesta:
                                        lead.tiporespuesta = None

                                    lead.save(request)

                                    histo = HistorialAsesor(inscripcion_id=lead.id, fecha_inicio=lead.fecha_modificacion,
                                                    fecha_fin=None, asesor=lead.asesor, observacion=observacion)
                                    histo.save(request)
                                else:
                                    if not lead.asesor == asesor:
                                        lead.asesor = asesor
                                        lead.estado_asesor = 2

                                        if lead.tiporespuesta:
                                            lead.tiporespuesta = None
                                        lead.save(request)

                                        histoanti = HistorialAsesor.objects.get(inscripcion_id=lead.id, fecha_fin=None)
                                        histoanti.fecha_fin = lead.fecha_modificacion
                                        histoanti.save(request)
                                        histo = HistorialAsesor(inscripcion_id=lead.id, fecha_inicio=lead.fecha_modificacion,
                                                        fecha_fin=None, asesor=lead.asesor, observacion=observacion)
                                        histo.save(request)
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                             "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'reasignacionmasivareserva':
            try:
                with transaction.atomic():
                    f = ReasignarMasivoForm(request.POST)
                    f.no_asesor()
                    if f.is_valid():
                        asesor = AsesorComercial.objects.get(id=int(request.POST['idasesor']))
                        leadsselect = request.POST['ids'].split(',')
                        observacion = f.cleaned_data['observacion']
                        for le in leadsselect:
                            lead = InscripcionCohorte.objects.get(pk=le)
                            histore = HistorialReservacionProspecto.objects.get(inscripcion_id=lead.id, status=True)
                            if not lead.asesor:
                                lead.asesor = asesor
                                lead.estado_asesor = 2

                                if lead.tiporespuesta:
                                    lead.tiporespuesta = None

                                lead.save(request)

                                histore.estado_asesor = 2
                                histore.save(request)

                                histo = HistorialAsesor(inscripcion_id=lead.id, fecha_inicio=lead.fecha_modificacion,
                                                fecha_fin=None, asesor=lead.asesor, observacion=observacion)
                                histo.save(request)
                            else:
                                if not lead.asesor == asesor:
                                    lead.asesor = asesor
                                    lead.estado_asesor = 2
                                    lead.save(request)

                                    histore.estado_asesor = 2
                                    histore.save(request)

                                    histoanti = HistorialAsesor.objects.get(inscripcion_id=lead.id, fecha_fin=None)
                                    histoanti.fecha_fin = lead.fecha_modificacion
                                    histoanti.save(request)
                                    histo = HistorialAsesor(inscripcion_id=lead.id, fecha_inicio=lead.fecha_modificacion,
                                                    fecha_fin=None, asesor=lead.asesor, observacion=observacion)
                                    histo.save(request)
                                else:
                                    histore.estado_asesor = 2
                                    histore.save(request)
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                             "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addpersona':
            try:
                f = RegistroAdmisionIpecForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['cedula'][:2] == u'VS' or f.cleaned_data['cedula'][:2] == u'vs':
                        # if not Persona.objects.filter(pasaporte=f.cleaned_data['cedula'][2:]).exists():
                        if not Persona.objects.filter(pasaporte=f.cleaned_data['cedula']).exists():
                            persona = Persona(pasaporte=f.cleaned_data['cedula'],
                                              nombres=f.cleaned_data['nombres'],
                                              apellido1=f.cleaned_data['apellido1'],
                                              apellido2=f.cleaned_data['apellido2'],
                                              email=f.cleaned_data['email'],
                                              telefono=f.cleaned_data['telefono'],
                                              sexo_id=request.POST['genero'],
                                              nacimiento='1999-01-01',
                                              direccion='',
                                              direccion2=''
                                              )
                            persona.save()
                            log(u'Adiciono persona: %s' % persona, request, "add")
                        else:
                            persona = Persona.objects.filter(pasaporte=f.cleaned_data['cedula']).last()
                            persona.email = f.cleaned_data['email']
                            persona.telefono = f.cleaned_data['telefono']
                            persona.save()
                            log(u'Editó persona: %s' % persona, request, "edit")
                    else:
                        if not Persona.objects.filter(cedula=f.cleaned_data['cedula']).exists():
                            persona = Persona(cedula=f.cleaned_data['cedula'],
                                              nombres=f.cleaned_data['nombres'],
                                              apellido1=f.cleaned_data['apellido1'],
                                              apellido2=f.cleaned_data['apellido2'],
                                              email=f.cleaned_data['email'],
                                              telefono=f.cleaned_data['telefono'],
                                              sexo_id=request.POST['genero'],
                                              nacimiento='1999-01-01',
                                              direccion='',
                                              direccion2=''
                                              )
                            persona.save()
                            log(u'Adiciono persona: %s' % persona, request, "add")
                        else:
                            persona = Persona.objects.filter(cedula=f.cleaned_data['cedula']).first()
                            persona.email = f.cleaned_data['email']
                            persona.telefono = f.cleaned_data['telefono']
                            persona.save()
                            log(u'Editó persona: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok', "idpersona": persona.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        elif action == 'cargarcombo_titulacion':
            try:
                persona = Persona.objects.filter(pk=request.POST['id']).last()
                lista = []
                if persona:
                    for titulo in persona.titulacion_set.filter(status=True, educacionsuperior=True):
                        lista.append([titulo.id, titulo.titulo.__str__()])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'cargar_campoamplio':
            try:
                t = Titulo.objects.filter(pk=request.POST['id']).first()
                lista = []
                campotitulo = CamposTitulosPostulacion.objects.filter(status=True, titulo=t).first()
                if campotitulo:
                    for ca in campotitulo.campoamplio.all():
                        lista.append([ca.id, ca.__str__()])
                else:
                    for ca in AreaConocimientoTitulacion.objects.all():
                        lista.append([ca.id, ca.__str__()])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Seleccione título: mínimo de tercer nivel o superior."})

        elif action == 'cargar_todos':
            try:
                t = Titulo.objects.filter(pk=request.POST['idtitulo']).first()
                listaca = []
                listace = []
                listacd = []
                campotitulo, campoamplio, campoespecifico, campodetallado = None, None, None, None
                if CamposTitulosPostulacion.objects.filter(status=True, titulo=t).exists():
                    campotitulo = CamposTitulosPostulacion.objects.filter(status=True, titulo=t).first()
                    campoamplio = AreaConocimientoTitulacion.objects.filter(status=True, id__in=campotitulo.campoamplio.all().values_list('id', flat=True))
                    if campoamplio:
                        for ca in campoamplio:
                            listaca.append([ca.id, ca.__str__()])
                    campoespecifico = SubAreaConocimientoTitulacion.objects.filter(status=True, id__in=campotitulo.campoespecifico.all().values_list('id', flat=True))
                    if campoespecifico:
                        for ce in campoespecifico:
                            listace.append([ce.id, ce.__str__()])
                    campodetallado = SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, id__in=campotitulo.campodetallado.all().values_list('id', flat=True))
                    if campodetallado:
                        for cd in campodetallado:
                            listacd.append([cd.id, cd.__str__()])
                    return JsonResponse({"result": "ok", "campoamplio": listaca, "campoespecifico": listace,
                                         "campodetallado": listacd})
                else:
                    return JsonResponse({"result": "no"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Seleccione título: mínimo de tercer nivel o superior."})

        elif action == 'retiroasesor':
            try:
                instancia = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                instancia.asesor = None
                instancia.estado_asesor = 1
                instancia.save(request)

                histoanti = HistorialAsesor.objects.get(inscripcion_id=instancia.id, fecha_fin=None)
                histoanti.fecha_fin = instancia.fecha_modificacion
                histoanti.save(request)

                log(u'Ha retirado asesor: %s' % instancia, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": True, "mensaje": "Ha ocurrido un error."}, safe=False)

        # elif action == 'desactivarpostulacion':
        #     try:
        #         hoy = datetime.now().date()
        #         instancia = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
        #         instancia.status = False
        #         instancia.fecha_modificacion = hoy
        #         instancia.save(request)
        #
        #         if Rubro.objects.values('id').filter(status=True, inscripcion=instancia).exists():
        #             rubro = Rubro.objects.filter(status=True, inscripcion=instancia)
        #             rubro[0].status = False
        #             rubro[0].save(request)
        #             log(u'Ha desactivado el rubro: %s' % rubro[0], request, "del")
        #
        #         log(u'Ha desactivado la postulación de: %s' % instancia, request, "del")
        #         return JsonResponse({"result": "ok"})
        #     except Exception as ex:
        #         return JsonResponse({"result": True, "mensaje": "Ha ocurrido un error."}, safe=False)

        elif action == 'desactivarpostulacion':
            try:
                with transaction.atomic():
                    from posgrado.forms import RechazoDesactivaForm
                    f = RechazoDesactivaForm(request.POST)
                    if f.is_valid():
                        hoy = datetime.now().date()
                        instancia = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                        if f.cleaned_data['motivo'] == '1':
                            return JsonResponse({"result": "bad", "mensaje": u"Seleccione un motivo."})
                        instancia.motivo_rechazo_desactiva = f.cleaned_data['motivo']
                        instancia.status = False
                        instancia.fecha_modificacion = hoy
                        instancia.save(request)

                        if Rubro.objects.values('id').filter(status=True, inscripcion=instancia).exists():
                            rubro = Rubro.objects.filter(status=True, inscripcion=instancia)
                            rubro[0].status = False
                            rubro[0].save(request)
                            log(u'Ha desactivado el rubro: %s' % rubro[0], request, "del")

                        log(u'Ha desactivado la postulación de: %s' % instancia, request, "del")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'aperturarmeta':
            try:
                idmes = int(request.POST['mes'])
                idanio = int(request.POST['anio'])
                if 'idas' in request.POST:
                    idas = eval(request.POST['idas'])
                    if idas != None:
                        ase = AsesorMeta.objects.filter(status=True, id__in=idas).first()
                        maes = MaestriasAdmision.objects.get(status=True, pk=ase.maestria.id)

                        if not CuposMaestriaMes.objects.filter(status=True, inicio__month=idmes, inicio__year=idanio, maestria=maes).exists():
                            primer_dia, ultimo_dia = obtener_primer_ultimo_dia_del_mes(idanio, idmes)

                            cupos = CuposMaestriaMes(maestria=maes,
                                                     inicio=primer_dia.strftime("%Y-%m-%d"),
                                                     fin=ultimo_dia.strftime("%Y-%m-%d"),
                                                     cuposlibres=0,
                                                     estado=1)
                            cupos.save(request)
                            log(u'Ha inicializado los cupos del mes dela maestría: %s' % cupos, request, "add")

                        if CohorteMaestria.objects.filter(status=True, procesoabierto=True, maestriaadmision=maes).exists():
                            primer_dia, ultimo_dia = obtener_primer_ultimo_dia_del_mes(idanio, idmes)

                            for id in idas:
                                cab = AsesorMeta.objects.get(status=True, pk=id)
                                if not DetalleAsesorMeta.objects.filter(status=True, asesormeta=cab, inicio=primer_dia.strftime("%Y-%m-%d"), fin=ultimo_dia.strftime("%Y-%m-%d")).exists():
                                    deta = DetalleAsesorMeta(asesormeta=cab,
                                                            inicio=primer_dia.strftime("%Y-%m-%d"),
                                                            fin=ultimo_dia.strftime("%Y-%m-%d"),
                                                            cantidad=0,
                                                            estado=1)
                                    deta.save(request)
                                    log(u'Ha inicializado la meta del asesor: %s' % cab, request, "add")
                        else:
                            return JsonResponse({"result": True, "mensaje": "No puede aperturar metas en esta maestría porque no existen cohortes abiertas."}, safe=False)
                    else:
                        return JsonResponse({"result": True, "mensaje": "Esta maestría no tiene ningún asesor asignado."}, safe=False)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": True, "mensaje": "Ha ocurrido un error."}, safe=False)

        elif action == 'marcarcomocompmatricula':
            try:
                cursor = connections['epunemi'].cursor()
                prospecto = InscripcionCohorte.objects.get(status=True, pk=int(request.POST['idd']))
                sql = """UPDATE sagest_comprobantealumno SET asesor='%s', telefono_asesor='%s' WHERE status=true AND id=%s; """ % (prospecto.asesor.persona.nombre_completo_inverso(), prospecto.asesor.persona.telefono, int(request.POST['id']))
                # sql = "UPDATE sagest_rubro SET nombre='%s' WHERE sagest_rubro.status=true and sagest_rubro.id=" + str(rubro.idrubroepunemi)
                cursor.execute(sql)
                cursor.close()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": True, "mensaje": "Ha ocurrido un error."}, safe=False)

        elif action == 'retiroreservacion':
            try:
                instancia = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                histo = HistorialReservacionProspecto.objects.get(inscripcion_id=instancia.id, status=True)
                histo.status = False
                histo.save(request)

                log(u'Ha retirado su reservación del prospecto: %s' % instancia, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": True, "mensaje": "Ha ocurrido un error."}, safe=False)

        elif action == 'addobservacion':
            try:
                with transaction.atomic():
                    f = HistorialRespuestaProspectoForm(request.POST)
                    filtro = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                    if f.is_valid():
                        filtro.tiporespuesta = f.cleaned_data['tiporespuesta']
                        filtro.save()
                        histo = HistorialRespuestaProspecto(inscripcion_id=filtro.id,
                                                            tiporespuesta=f.cleaned_data['tiporespuesta'],
                                                            observacion=f.cleaned_data['observacion'].upper())
                        histo.save(request)
                        log(u'Adiciono Observación en Comercializacion: %s' % filtro.inscripcionaspirante, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                             "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'addreservacion':
            try:
                f = ReservacionProspectoForm(request.POST)
                inscripcion = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                if f.is_valid():
                    if HistorialReservacionProspecto.objects.filter(inscripcion_id=inscripcion.id, status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Este prospecto ya ha sido reservado."})
                    else:
                        reservacion = HistorialReservacionProspecto(inscripcion_id=inscripcion.id,
                                                                    persona_id=persona.id,
                                                                    observacion = f.cleaned_data['observacion'])
                        reservacion.save(request)

                    asesor = AsesorComercial.objects.filter(status=True, persona=reservacion.persona).order_by('-id').first()
                    asunto = u"RESERVACIÓN DE PROSPECTO"
                    observacion = f'Se le comunica que el asesor {reservacion.persona.nombre_completo_inverso()} ha reservado al prospecto {inscripcion} para su posterior asignación. Por favor, dar seguimiento a la reservación.'

                    supervisores = Persona.objects.filter(status=True, id__in=variable_valor('PERSONAL_SUPERVISION'))

                    for supervisor in supervisores:
                        para = supervisor
                        perfiu = supervisor.perfilusuario_administrativo()

                        notificacion3(asunto, observacion, para, None,
                                      '/comercial?action=leadsregistrados&id=' + str(asesor.id) + '&s=' + str(inscripcion.inscripcionaspirante.persona.cedula) + '&idc=0',
                                      reservacion.pk, 1,
                                      'sga', HistorialReservacionProspecto, perfiu, request)

                    log(u'Reservó el proespecto: %s' % inscripcion.inscripcionaspirante.persona, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editmencion':
            try:
                with transaction.atomic():
                    form = MencionMaestriaForm(request.POST)
                    filtro = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                    if form.is_valid():
                        itine = ItinerarioMallaEspecilidad.objects.get(id=request.POST['mencion'])
                        # filtro.itinerario = request.POST['mencion']
                        filtro.itinerario = itine.itinerario
                        filtro.save()
                        log(u'Actualizó itinerario maestría del prospecto: %s' % filtro.inscripcionaspirante, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
                    # return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                    #                      "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'addcanal':
            try:
                f = CanalInformacionForm(request.POST)
                estado = False
                if f.is_valid():
                    if 'valido' in request.POST:
                        estado = True
                    else:
                        estado = False

                    eCanal = CanalInformacionMaestria(descripcion=f.cleaned_data['canal'],
                                                      valido_form=estado)
                    eCanal.save(request)

                    log(u'Adicionó canales de información: %s' % eCanal, request, "add")
                    return JsonResponse({"result": False, 'mensaje': 'Adición Exitosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addconvenio':
            try:
                from posgrado.models import Convenio
                from posgrado.forms import ConvenioForm
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                f = ConvenioForm(request.POST, request.FILES)
                estado = False
                aplicadescuento = False
                suberequisito = False
                if f.is_valid():
                    if 'valido' in request.POST:
                        estado = True
                    else:
                        estado = False
                    if 'aplicadescuento' in request.POST:
                        aplicadescuento = True
                    else:
                        aplicadescuento = False
                    if 'suberequisito' in request.POST:
                        suberequisito = True
                    else:
                        suberequisito = False
                    eConvenio = Convenio(descripcion=f.cleaned_data['descripcion'],
                                                          valido_form=estado,
                                                         fechaInicio=f.cleaned_data['fechaInicio'],
                                                         aplicadescuento = aplicadescuento,
                                                         porcentajedescuento=f.cleaned_data['porcentajedescuento'],
                                                         suberequisito= suberequisito,
                                                        descripcionrequisito = f.cleaned_data['descripcionrequisito'])
                    eConvenio.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("convenioposgrado_", newfile._name)
                        eConvenio.archivo = newfile
                        eConvenio.save(request)
                    log(u'Adicionó convenio de posgrado: %s' % eConvenio, request, "add")
                    return JsonResponse({"result": False, 'mensaje': 'Adición Exitosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcanal':
            try:
                with transaction.atomic():
                    f = CanalInformacionForm(request.POST)
                    filtro = CanalInformacionMaestria.objects.get(pk=int(request.POST['id']))
                    if f.is_valid():
                        filtro.descripcion = f.cleaned_data['canal']
                        if 'valido' in request.POST:
                            filtro.valido_form = True
                        else:
                            filtro.valido_form = False
                        filtro.save()
                        log(u'Actualizó el canal de información: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editconvenio':
            try:
                with transaction.atomic():
                    from posgrado.forms import ConvenioForm
                    from posgrado.models import Convenio
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile.size > 10485760:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                        else:
                            newfiles = request.FILES['archivo']
                            newfilesd = newfiles._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if not ext.lower() == '.pdf':
                                return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                    f = ConvenioForm(request.POST, request.FILES)
                    filtro = Convenio.objects.get(pk=int(request.POST['id']))
                    # if f.is_valid():
                    filtro.descripcion = request.POST['descripcion']
                    filtro.fechaInicio = request.POST['fechaInicio']
                    filtro.porcentajedescuento = request.POST['porcentajedescuento']
                    filtro.descripcionrequisito = request.POST['descripcionrequisito']
                    if 'valido' in request.POST:
                        filtro.valido_form = True
                    else:
                        filtro.valido_form = False
                    if 'aplicadescuento' in request.POST:
                        filtro.aplicadescuento = True
                    else:
                        filtro.aplicadescuento = False
                    if 'suberequisito' in request.POST:
                        filtro.suberequisito = True
                    else:
                        filtro.suberequisito = False
                    if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("convenioposgrado_", newfile._name)
                            filtro.archivo = newfile
                    filtro.save(request)
                    log(u'Actualizó el convenio de posgrado: %s' % filtro, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                    # else:
                    #     transaction.set_rollback(True)
                    #     return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editarlead':
            try:
                f = ActualizarDatosPersonaForm(request.POST)
                lead = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                personlead = Persona.objects.get(pk=lead.inscripcionaspirante.persona.id)
                if f.is_valid():
                    personlead.nombres = f.cleaned_data['nombres']
                    personlead.apellido1 = f.cleaned_data['apellido1']
                    personlead.apellido2 = f.cleaned_data['apellido2']
                    personlead.telefono = f.cleaned_data['telefono']
                    personlead.email = f.cleaned_data['email']

                    personlead.save(request)

                    cursor = connections['epunemi'].cursor()
                    sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (personlead.cedula, personlead.cedula, personlead.cedula)
                    cursor.execute(sql)
                    idalumno = cursor.fetchone()

                    if idalumno is not None:
                        sql1 = """UPDATE sga_persona SET nombres='%s', apellido1='%s', apellido2='%s', telefono='%s', email='%s' WHERE id=%s;""" % (
                        personlead.nombres, personlead.apellido1, personlead.apellido2, personlead.telefono, personlead.email, idalumno[0])
                        cursor.execute(sql1)

                    log(u'Editó los datos persoanles de: %s' % personlead, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editarinscripcionrubro':
            try:
                rubro = Rubro.objects.get(pk=int(request.POST['id']))
                inscri = InscripcionCohorte.objects.filter(status=True, pk=int(request.POST['idins'])).order_by('id')[0]
                f = EditarRubroMaestriaForm(request.POST)
                if f.is_valid():
                    coho = CohorteMaestria.objects.get(status=True, pk=int(f.cleaned_data['cohorte'].id))
                    rubro.inscripcion = inscri
                    rubro.cohortemaestria = coho
                    rubro.admisionposgradotipo = 3

                    rubro.save(request)
                    log(u'Asignó inscricpcioncohorte y cohorte a rubro: %s' % rubro, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'cambiardeconvenio':
            try:
                from posgrado.forms import CambioConvenioMaestriaForm
                lead = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                f = CambioConvenioMaestriaForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['convenio']:
                        lead.convenio = f.cleaned_data['convenio']
                    else:
                        lead.convenio = None
                    lead.save(request)
                    log(u'Modificó convenio de lead: %s' % lead, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'cambiardehomologacion':
            try:
                from posgrado.forms import CambioHomologacionMaestriaForm
                lead = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                f = CambioHomologacionMaestriaForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['homologado']:
                        lead.homologado = f.cleaned_data['homologado']
                    else:
                        lead.homologado = None
                    lead.save(request)
                    log(u'Modificó convenio de lead: %s' % lead, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'cambiardecohorte':
            try:
                lead = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                log(u'%s - Cambio cohorte: %s a la cohorte numero %s' % (
                    lead.cohortes_id, lead, request.POST['cohorte']), request, "edit")

                listarequisitos = EvidenciaRequisitosAspirante.objects.filter(inscripcioncohorte=lead, requisitos__requisito__claserequisito__clasificacion=1)
                canrequi = RequisitosMaestria.objects.filter(status=True, obligatorio=True, cohorte__id=int(request.POST['cohorte']), requisito__claserequisito__clasificacion=1).distinct().count()
                listarequisitosfinan = EvidenciaRequisitosAspirante.objects.filter(inscripcioncohorte=lead, requisitos__requisito__claserequisito__clasificacion=3)

                if lead.subirrequisitogarante:
                    canrequifi = RequisitosMaestria.objects.filter(status=True, obligatorio=True, cohorte__id=int(request.POST['cohorte']), requisito__claserequisito__clasificacion=3).distinct().count()
                else:
                    canrequifi = RequisitosMaestria.objects.filter(status=True, obligatorio=True, cohorte__id=int(request.POST['cohorte']), requisito__claserequisito__clasificacion=3).exclude(requisito__id__in=[56, 57, 59]).distinct().count()

                # SI TIENE EVIDENCIAS DE ADMISION EN LA COHORTE PASADA
                for lis in listarequisitos:
                    if RequisitosMaestria.objects.filter(requisito=lis.requisitos.requisito, cohorte_id=request.POST['cohorte'], status=True):
                        requi = RequisitosMaestria.objects.filter(requisito=lis.requisitos.requisito,
                                                                  cohorte_id=request.POST['cohorte'], status=True)[0]
                        lis.requisitos = requi
                        if requi.requisito.id in (2, 14, 16, 4, 29, 52, 6, 62, 54):
                            if lis.ultima_evidencia():
                                dera = DetalleEvidenciaRequisitosAspirante.objects.get(pk=lis.ultima_evidencia().id)
                                dera.estado_aprobacion = 1
                                dera.observacion = "Pendiente debido a cambio de Cohorte"
                                dera.save()
                        lis.save()

                canevi = EvidenciaRequisitosAspirante.objects.filter(inscripcioncohorte=lead, requisitos__cohorte__id = request.POST['cohorte'], requisitos__requisito__claserequisito__clasificacion=1, detalleevidenciarequisitosaspirante__estado_aprobacion=2, requisitos__status=True).distinct().count()

                if canevi == canrequi:
                    lead.estado_aprobador = 2
                else:
                    lead.estado_aprobador = 1
                    lead.todosubido = False
                    lead.preaprobado = False

                lead.save(request)

                # SI TIENE EVIDENCIAS DE FINANCIAMIENTO EN LA COHORTE PASADA
                if lead.formapagopac:
                    if lead.formapagopac.id == 2:
                        for listf in listarequisitosfinan:
                            if RequisitosMaestria.objects.filter(requisito=listf.requisitos.requisito,
                                                                 cohorte_id=request.POST['cohorte'], status=True,
                                                                 requisito__claserequisito__clasificacion=3):
                                requifinan = RequisitosMaestria.objects.filter(requisito=listf.requisitos.requisito,
                                                                          cohorte_id=request.POST['cohorte'], status=True,
                                                                               requisito__claserequisito__clasificacion=3)[0]
                                listf.requisitos = requifinan
                                if requifinan.requisito.id in (2, 14, 16, 4, 29, 52, 6, 62, 54):
                                    if listf.ultima_evidencia():
                                        dera = DetalleEvidenciaRequisitosAspirante.objects.get(pk=listf.ultima_evidencia().id)
                                        dera.estado_aprobacion = 1
                                        dera.observacion = "Pendiente debido a cambio de Cohorte"
                                        dera.save()
                                listf.save()

                        canevifi = EvidenciaRequisitosAspirante.objects.filter(inscripcioncohorte=lead, requisitos__cohorte__id = request.POST['cohorte'], requisitos__requisito__claserequisito__clasificacion=3, detalleevidenciarequisitosaspirante__estado_aprobacion=2).count()

                        if canevifi == canrequifi:
                            lead.estadoformapago = 2
                        else:
                            lead.estadoformapago = 1
                            lead.todosubidofi = False

                        lead.save(request)

                # SI TIENE RUBROS GENERADOS
                chorte = CohorteMaestria.objects.get(id=request.POST['cohorte'], status=True)
                if Rubro.objects.filter(inscripcion=lead, status=True).exists():
                    rubros = Rubro.objects.filter(inscripcion=lead, status=True)
                    for rubro in rubros:
                        if rubro.idrubroepunemi != 0:
                            cursor = connections['epunemi'].cursor()
                            sql = """SELECT id FROM sagest_pago WHERE rubro_id=%s; """ % (rubro.idrubroepunemi)
                            cursor.execute(sql)
                            tienerubropagos = cursor.fetchone()

                            if tienerubropagos is None:
                                sql = """DELETE FROM sagest_rubro WHERE sagest_rubro.id=%s AND sagest_rubro.idrubrounemi=%s; """ % (
                                rubro.idrubroepunemi, rubro.id)
                                cursor.execute(sql)
                                cursor.close()

                            rubro.status = False
                            rubro.save()

                if lead.cohortes.tipo == 1:
                    if IntegranteGrupoExamenMsc.objects.filter(status=True, inscripcion=lead).exists():
                        lista = IntegranteGrupoExamenMsc.objects.filter(status=True, inscripcion=lead)
                        for li in lista:
                            li.status = False
                            li.save()

                    if IntegranteGrupoEntrevitaMsc.objects.filter(status=True, inscripcion=lead).exists():
                        lista2 = IntegranteGrupoEntrevitaMsc.objects.filter(status=True, inscripcion=lead)
                        for li2 in lista2:
                            li2.status = False
                            li2.save()

                elif lead.cohortes.tipo == 2:
                    if IntegranteGrupoExamenMsc.objects.filter(status=True, inscripcion=lead).exists():
                        lista = IntegranteGrupoExamenMsc.objects.filter(status=True, inscripcion=lead)
                        for li in lista:
                            li.status = False
                            li.save()

                if Contrato.objects.filter(status=True, inscripcion=lead).exists():
                    contratopos = Contrato.objects.get(status=True, inscripcion=lead)

                    detalleevidencia = DetalleAprobacionContrato(contrato_id=contratopos.id, espagare=False,
                                                                 observacion='Pendiente por cambio de cohorte',
                                                                 persona=persona, estado_aprobacion=1,
                                                                 fecha_aprobacion=datetime.now(),
                                                                 archivocontrato=contratopos.archivocontrato)
                    detalleevidencia.save(request)

                    if contratopos.inscripcion.formapagopac.id == 2:
                        detalleevidencia = DetalleAprobacionContrato(contrato_id=contratopos.id, espagare=True,
                                                                     observacion='Pendiente por cambio de cohorte',
                                                                     persona=persona, estado_aprobacion=1, fecha_aprobacion=datetime.now(),
                                                                     archivocontrato=contratopos.archivopagare)
                        detalleevidencia.save(request)

                    contratopos.estado = 1
                    contratopos.estadopagare = 1
                    contratopos.save(request)

                observacion = f'Cambio de {lead.cohortes} a {chorte}.'
                cambio = CambioAdmitidoCohorteInscripcion(inscripcionCohorte=lead, cohortes=chorte, observacion=observacion)
                cambio.save(request)

                lead.cohortes_id = chorte
                lead.tiporespuesta = None
                lead.save(request)

                asunto = u"POSTULANTE MIGRADO DE COHORTE"
                observacion = f'Se le comunica que el postulante {lead.inscripcionaspirante.persona} con cédula {lead.inscripcionaspirante.persona.cedula} ha sido migrado de cohorte. Por favor, revisar los documentos de admisión para su pre aprobación.'
                para = lead.asesor.persona
                perfiu = lead.asesor.perfil_administrativo()

                notificacion3(asunto, observacion, para, None,
                              '/comercial?s=' + lead.inscripcionaspirante.persona.cedula,
                              lead.pk, 1,
                              'sga', InscripcionCohorte, perfiu, request)
                return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'cambiardecohortemasivo':
            try:
                f = CambioCohorteMaestriaForm(request.POST)
                if f.is_valid():
                    leadsselect = request.POST['ids'].split(',')
                    for le in leadsselect:
                        if not InscripcionCohorte.objects.filter(status=True, id=le, contrato__contratolegalizado=True).exists():
                            lead = InscripcionCohorte.objects.get(pk=le)
                            log(u'%s - Cambio cohorte: %s a la cohorte numero %s' % (
                                lead.cohortes_id, lead, request.POST['cohorte']), request, "edit")

                            listarequisitos = EvidenciaRequisitosAspirante.objects.filter(inscripcioncohorte=lead, requisitos__requisito__claserequisito__clasificacion=1)
                            canrequi = RequisitosMaestria.objects.filter(status=True, obligatorio=True, cohorte__id=int(request.POST['cohorte']), requisito__claserequisito__clasificacion=1).distinct().count()
                            listarequisitosfinan = EvidenciaRequisitosAspirante.objects.filter(inscripcioncohorte=lead, requisitos__requisito__claserequisito__clasificacion=3)

                            if lead.subirrequisitogarante:
                                canrequifi = RequisitosMaestria.objects.filter(status=True, obligatorio=True, cohorte__id=int(request.POST['cohorte']), requisito__claserequisito__clasificacion=3).distinct().count()
                            else:
                                canrequifi = RequisitosMaestria.objects.filter(status=True, obligatorio=True, cohorte__id=int(request.POST['cohorte']), requisito__claserequisito__clasificacion=3).exclude(requisito__id__in=[56, 57, 59]).distinct().count()

                            # SI TIENE EVIDENCIAS DE ADMISION EN LA COHORTE PASADA
                            for lis in listarequisitos:
                                if RequisitosMaestria.objects.filter(requisito=lis.requisitos.requisito, cohorte_id=request.POST['cohorte'], status=True):
                                    requi = RequisitosMaestria.objects.filter(requisito=lis.requisitos.requisito,
                                                                              cohorte_id=request.POST['cohorte'], status=True)[0]
                                    lis.requisitos = requi
                                    if requi.requisito.id in (2,14,16,4,29,52,6,62,54):
                                        if lis.ultima_evidencia():
                                            dera = DetalleEvidenciaRequisitosAspirante.objects.get(pk=lis.ultima_evidencia().id)
                                            dera.estado_aprobacion = 1
                                            dera.observacion = "Pendiente debido a cambio de Cohorte"
                                            dera.save()
                                    lis.save()

                            canevi = EvidenciaRequisitosAspirante.objects.filter(inscripcioncohorte=lead, requisitos__cohorte__id = request.POST['cohorte'], requisitos__requisito__claserequisito__clasificacion=1, detalleevidenciarequisitosaspirante__estado_aprobacion=2, requisitos__status=True).distinct().count()

                            if canevi == canrequi:
                                lead.estado_aprobador = 2
                            else:
                                lead.estado_aprobador = 1
                                lead.todosubido = False
                                lead.preaprobado = False

                            lead.save(request)

                            # SI TIENE EVIDENCIAS DE FINANCIAMIENTO EN LA COHORTE PASADA
                            if lead.formapagopac:
                                if lead.formapagopac.id == 2:
                                    for listf in listarequisitosfinan:
                                        if RequisitosMaestria.objects.filter(requisito=listf.requisitos.requisito,
                                                                             cohorte_id=request.POST['cohorte'], status=True,
                                                                             requisito__claserequisito__clasificacion=3):
                                            requifinan = RequisitosMaestria.objects.filter(requisito=listf.requisitos.requisito,
                                                                                      cohorte_id=request.POST['cohorte'], status=True,
                                                                                           requisito__claserequisito__clasificacion=3)[0]
                                            listf.requisitos = requifinan
                                            if requifinan.requisito.id in (2, 14, 16, 4, 29, 52, 6, 62, 54):
                                                if listf.ultima_evidencia():
                                                    dera = DetalleEvidenciaRequisitosAspirante.objects.get(pk=listf.ultima_evidencia().id)
                                                    dera.estado_aprobacion = 1
                                                    dera.observacion = "Pendiente debido a cambio de Cohorte"
                                                    dera.save()
                                            listf.save()

                                    canevifi = EvidenciaRequisitosAspirante.objects.filter(inscripcioncohorte=lead, requisitos__cohorte__id = request.POST['cohorte'], requisitos__requisito__claserequisito__clasificacion=3, detalleevidenciarequisitosaspirante__estado_aprobacion=2).count()

                                    if canevifi == canrequifi:
                                        lead.estadoformapago = 2
                                    else:
                                        lead.estadoformapago = 1
                                        lead.todosubidofi = False

                                    lead.save(request)

                            # SI TIENE RUBROS GENERADOS
                            chorte = CohorteMaestria.objects.get(id=request.POST['cohorte'], status=True)
                            if Rubro.objects.filter(inscripcion=lead, status=True).exists():
                                rubros = Rubro.objects.filter(inscripcion=lead, status=True)
                                for rubro in rubros:
                                    if rubro.idrubroepunemi != 0:
                                        cursor = connections['epunemi'].cursor()
                                        sql = """SELECT id FROM sagest_pago WHERE rubro_id=%s; """ % (rubro.idrubroepunemi)
                                        cursor.execute(sql)
                                        tienerubropagos = cursor.fetchone()

                                        if tienerubropagos is None:
                                            sql = """DELETE FROM sagest_rubro WHERE sagest_rubro.id=%s AND sagest_rubro.idrubrounemi=%s; """ % (
                                            rubro.idrubroepunemi, rubro.id)
                                            cursor.execute(sql)
                                            cursor.close()

                                        rubro.status = False
                                        rubro.save()

                            if lead.cohortes.tipo == 1:
                                if IntegranteGrupoExamenMsc.objects.filter(status=True, inscripcion=lead).exists():
                                    lista = IntegranteGrupoExamenMsc.objects.filter(status=True, inscripcion=lead)
                                    for li in lista:
                                        li.status = False
                                        li.save()

                                if IntegranteGrupoEntrevitaMsc.objects.filter(status=True, inscripcion=lead).exists():
                                    lista2 = IntegranteGrupoEntrevitaMsc.objects.filter(status=True, inscripcion=lead)
                                    for li2 in lista2:
                                        li2.status = False
                                        li2.save()

                            elif lead.cohortes.tipo == 2:
                                if IntegranteGrupoExamenMsc.objects.filter(status=True, inscripcion=lead).exists():
                                    lista = IntegranteGrupoExamenMsc.objects.filter(status=True, inscripcion=lead)
                                    for li in lista:
                                        li.status = False
                                        li.save()

                            if Contrato.objects.filter(status=True, inscripcion=lead).exists():
                                contratopos = Contrato.objects.get(status=True, inscripcion=lead)

                                detalleevidencia = DetalleAprobacionContrato(contrato_id=contratopos.id, espagare=False,
                                                                             observacion='Pendiente por cambio de cohorte',
                                                                             persona=persona, estado_aprobacion=1,
                                                                             fecha_aprobacion=datetime.now(),
                                                                             archivocontrato=contratopos.archivocontrato)
                                detalleevidencia.save(request)

                                if contratopos.inscripcion.formapagopac.id == 2:
                                    detalleevidencia = DetalleAprobacionContrato(contrato_id=contratopos.id, espagare=True,
                                                                                 observacion='Pendiente  por cambio de cohorte',
                                                                                 persona=persona, estado_aprobacion=1, fecha_aprobacion=datetime.now(),
                                                                                 archivocontrato=contratopos.archivopagare)
                                    detalleevidencia.save(request)

                                contratopos.estado = 1
                                contratopos.estadopagare = 1
                                contratopos.save(request)

                            observacion = f'Cambio de {lead.cohortes} a {chorte}.'
                            cambio = CambioAdmitidoCohorteInscripcion(inscripcionCohorte=lead, cohortes=chorte, observacion=observacion)
                            cambio.save(request)

                            lead.cohortes_id = chorte
                            # lead.tiporespuesta = None
                            lead.save(request)

                            asunto = u"POSTULANTE MIGRADO DE COHORTE"
                            observacion = f'Se le comunica que el postulante {lead.inscripcionaspirante.persona} con cédula {lead.inscripcionaspirante.persona.cedula} ha sido migrado de cohorte. Por favor, revisar los documentos de admisión para su pre aprobación.'
                            para = lead.asesor.persona
                            perfiu = lead.asesor.perfil_administrativo()

                            notificacion3(asunto, observacion, para, None,
                                          '/comercial?s=' + lead.inscripcionaspirante.persona.cedula,
                                          lead.pk, 1,
                                          'sga', InscripcionCohorte, perfiu, request)
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'cambiarformapago':
            try:
                f = FinanciamientoForm(request.POST)
                lead = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                if f.is_valid():
                    lead.formapagopac = f.cleaned_data['tipo']
                    lead.estadoformapago = 1
                    lead.subirrequisitogarante = f.cleaned_data['subirrequisitogarante']
                    lead.puedeeditarmp = False
                    lead.save(request)

                    deta = DetalleAprobacionFormaPago(inscripcion_id=lead.id,
                                                      formapagopac=f.cleaned_data['tipo'],
                                                      estadoformapago=1,
                                                      observacion=f.cleaned_data['observacion'],
                                                      persona=persona)
                    deta.save(request)

                    if Contrato.objects.filter(status=True, inscripcion__id=lead.id).exists():
                        contra = Contrato.objects.get(status=True, inscripcion__id=lead.id)
                        if contra.detalleaprobacioncontrato_set.filter(status=True, espagare=False).exists():
                            evicon = contra.detalleaprobacioncontrato_set.filter(status=True, espagare=False).order_by('-id')[0]
                            evicon.estado_aprobacion = 3
                            evicon.observacion = 'CAMBIO DE FORMA DE PAGO'
                            evicon.save()

                    log(u'Cambio la forma de pago a financiamiento del lead: %s' % lead, request, "edit")

                    if lead.formapagopac.id == 2:
                        #CÉDULA
                        evice = EvidenciaRequisitosAspirante.objects.filter(requisitos__requisito__id__in=[7, 66],
                                                                           inscripcioncohorte=lead,
                                                                           status=True) .first()
                        requisitosmaestria = RequisitosMaestria.objects.filter(status=True, cohorte=lead.cohortes, requisito__id=53).first()
                        if not EvidenciaRequisitosAspirante.objects.filter(requisitos=requisitosmaestria,
                                                                           inscripcioncohorte=lead,
                                                                           status=True).exists():
                            requisitomaestria = EvidenciaRequisitosAspirante(requisitos=requisitosmaestria,
                                                                             inscripcioncohorte=lead)
                            requisitomaestria.save(request)
                            requisitomaestria.archivo = evice.archivo
                            requisitomaestria.save(request)
                            log(u'Adicionó requisito de maestria aspirante: %s' % requisitomaestria.requisitos, request, "add")
                            detalle = DetalleEvidenciaRequisitosAspirante(evidencia=requisitomaestria,
                                                                          estadorevision=1,
                                                                          # persona=inscripcioncohorte.inscripcionaspirante.persona,
                                                                          fecha=datetime.now().date(),
                                                                          observacion='Está cédula fue aprobada por admisión')
                            detalle.save(request)
                        #PAPELETA DE VOTACIÓN
                        evice = EvidenciaRequisitosAspirante.objects.filter(requisitos__requisito__id=2,
                                                                           inscripcioncohorte=lead,
                                                                           status=True).first()
                        requisitosmaestria = RequisitosMaestria.objects.filter(status=True, cohorte=lead.cohortes, requisito__id=54).first()
                        if not EvidenciaRequisitosAspirante.objects.filter(requisitos=requisitosmaestria,
                                                                           inscripcioncohorte=lead,
                                                                           status=True).exists():
                            requisitomaestria = EvidenciaRequisitosAspirante(requisitos=requisitosmaestria,
                                                                             inscripcioncohorte=lead)
                            requisitomaestria.save(request)
                            requisitomaestria.archivo = evice.archivo
                            requisitomaestria.save(request)
                            log(u'Adicionó requisito de maestria aspirante: %s' % requisitomaestria.requisitos, request, "add")
                            detalle = DetalleEvidenciaRequisitosAspirante(evidencia=requisitomaestria,
                                                                          estadorevision=1,
                                                                          # persona=inscripcioncohorte.inscripcionaspirante.persona,
                                                                          fecha=datetime.now().date(),
                                                                          observacion='Está papeleta fue aprobada por admisión')
                            detalle.save(request)
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'asignartipo':
            try:
                f = AsignarTipoForm(request.POST)
                lead = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                if f.is_valid():
                    lead.Configfinanciamientocohorte = f.cleaned_data['tipo']
                    lead.subirrequisitogarante = f.cleaned_data['subirrequisitogarante']
                    lead.save(request)

                    deta = DetalleAprobacionFormaPago(inscripcion_id=lead.id,
                                                      formapagopac=lead.formapagopac,
                                                      estadoformapago=lead.estadoformapago,
                                                      # observacion=f.cleaned_data['observacion'],
                                                      persona=persona,
                                                      tipofinanciamiento = lead.Configfinanciamientocohorte)
                    deta.save(request)

                    log(u'Asgno el tipo de financiamiento al lead: %s' % lead, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'generarrubroformapago':
            try:
                integrante = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                inscripcioncohorte = integrante
                inscripcion=None

                # validar selección de mención
                if integrante.cohortes.maestriaadmision.carrera.malla().tiene_itinerario_malla_especialidad():
                    if integrante.itinerario == 0:
                        raise NameError('%s no tiene registrado el itinerario/mención de la maestría.' % (integrante.inscripcionaspirante))

                # generar rubros
                if integrante.formapagopac:
                    if integrante.formapagopac.id == 1:
                        if not integrante.genero_rubro_programa():
                            if integrante.cohortes.valorprograma:
                                vmatricula = integrante.cohortes.valormatricula if integrante.cohortes.valormatricula else 0
                                valorprograma = integrante.cohortes.valorprograma - vmatricula
                                if not integrante.cohortes.tiporubro:
                                    raise NameError('El programa %s no tiene configurado el Tipo de rubro para generar los rubros.'%(integrante.cohortes))
                                tiporubroarancel = TipoOtroRubro.objects.get(pk=integrante.cohortes.tiporubro.id)
                                rubro = Rubro(tipo=tiporubroarancel,
                                              persona=integrante.inscripcionaspirante.persona,
                                              cohortemaestria=integrante.cohortes,
                                              inscripcion=integrante,
                                              relacionados=None,
                                              nombre=tiporubroarancel.nombre + ' - ' + integrante.cohortes.maestriaadmision.descripcion + ' - ' + integrante.cohortes.descripcion,
                                              cuota=1,
                                              fecha=datetime.now().date(),
                                              fechavence=integrante.cohortes.fechavencerubro,
                                              valor=valorprograma,
                                              iva_id=1,
                                              valoriva=0,
                                              valortotal=valorprograma,
                                              saldo=valorprograma,
                                              epunemi=True,
                                              idrubroepunemi=0,
                                              admisionposgradotipo=3,
                                              cancelado=False)
                                rubro.save(request)
                                integrante.tipocobro = 3
                                integrante.tipo = tiporubroarancel
                                integrante.save(request)
                                log(u'Genero rubro por concepto costo programa posgrado: %s programa de %s' % (integrante, integrante.cohortes.maestriaadmision.descripcion), request, "add")

                            if integrante.cohortes.valormatricula:
                                valormatricula = integrante.cohortes.valormatricula
                                tiporubroarancel = TipoOtroRubro.objects.get(pk=integrante.cohortes.tiporubro.id)
                                # tiporubroarancel = TipoOtroRubro.objects.get(pk=2845)
                                rubro = Rubro(tipo=tiporubroarancel,
                                              persona=integrante.inscripcionaspirante.persona,
                                              cohortemaestria=integrante.cohortes,
                                              inscripcion=integrante,
                                              relacionados=None,
                                              nombre=tiporubroarancel.nombre + ' - ' + integrante.cohortes.maestriaadmision.descripcion + ' - ' + integrante.cohortes.descripcion,
                                              cuota=1,
                                              fecha=datetime.now().date(),
                                              fechavence=integrante.cohortes.fechavencerubro,
                                              valor=valormatricula,
                                              iva_id=1,
                                              valoriva=0,
                                              valortotal=valormatricula,
                                              saldo=valormatricula,
                                              epunemi=True,
                                              idrubroepunemi=0,
                                              admisionposgradotipo=2,
                                              cancelado=False)
                                rubro.save(request)
                                log(u'Genero rubro por concepto matricula posgrado: %s programa de %s' % (integrante, integrante.cohortes.maestriaadmision.descripcion), request, "add")

                            rubrosunemi = Rubro.objects.filter(status=True, inscripcion=integrante, epunemi = True, cancelado=False)

                            # -------CREAR PERSONA EPUNEMI-------
                            cursor = connections['epunemi'].cursor()
                            sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.cedula, integrante.inscripcionaspirante.persona.cedula, integrante.inscripcionaspirante.persona.cedula)
                            cursor.execute(sql)
                            idalumno = cursor.fetchone()

                            if idalumno is None:
                                sql = """ INSERT INTO sga_persona (status, nombres, apellido1, apellido2, cedula, ruc, pasaporte,
                                            nacimiento, tipopersona, sector, direccion,  direccion2,
                                            num_direccion, telefono, telefono_conv, email, contribuyenteespecial,
                                            anioresidencia, nacionalidad, ciudad, referencia, emailinst, identificacioninstitucion,
                                            regitrocertificacion, libretamilitar, servidorcarrera, concursomeritos, telefonoextension,
                                            tipocelular, periodosabatico, real, lgtbi, datosactualizados, confirmarextensiontelefonia,
                                            acumuladecimo, acumulafondoreserva, representantelegal, inscripcioncurso, unemi,
                                            idunemi)
                                                    VALUES(TRUE, '%s', '%s', '%s', '%s', '%s', '%s', '/%s/', %s, '%s', '%s', '%s', '%s', '%s', '%s', '%s', 
                                                    FALSE, 0, '', '', '', '', '', '', '', FALSE, FALSE, '', 0, FALSE, TRUE, FALSE, 0, FALSE, TRUE, FALSE, FALSE, 
                                                    FALSE, FALSE, 0); """ % (
                                    integrante.inscripcionaspirante.persona.nombres, integrante.inscripcionaspirante.persona.apellido1,
                                    integrante.inscripcionaspirante.persona.apellido2, integrante.inscripcionaspirante.persona.cedula,
                                    integrante.inscripcionaspirante.persona.ruc if integrante.inscripcionaspirante.persona.ruc else '',
                                    integrante.inscripcionaspirante.persona.pasaporte if integrante.inscripcionaspirante.persona.pasaporte else '',
                                    integrante.inscripcionaspirante.persona.nacimiento,
                                    integrante.inscripcionaspirante.persona.tipopersona if integrante.inscripcionaspirante.persona.tipopersona else 1,
                                    integrante.inscripcionaspirante.persona.sector if integrante.inscripcionaspirante.persona.sector else '',
                                    integrante.inscripcionaspirante.persona.direccion if integrante.inscripcionaspirante.persona.direccion else '',
                                    integrante.inscripcionaspirante.persona.direccion2 if integrante.inscripcionaspirante.persona.direccion2 else '',
                                    integrante.inscripcionaspirante.persona.num_direccion if integrante.inscripcionaspirante.persona.num_direccion else '',
                                    integrante.inscripcionaspirante.persona.telefono if integrante.inscripcionaspirante.persona.telefono else '',
                                    integrante.inscripcionaspirante.persona.telefono_conv if integrante.inscripcionaspirante.persona.telefono_conv else '',
                                    integrante.inscripcionaspirante.persona.email if integrante.inscripcionaspirante.persona.email else '')
                                cursor.execute(sql)

                                if integrante.inscripcionaspirante.persona.sexo:
                                    sql = """SELECT sexo.id FROM sga_sexo AS sexo WHERE sexo.id='%s'  AND sexo.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.sexo.id)
                                    cursor.execute(sql)
                                    sexo = cursor.fetchone()

                                    if sexo is not None:
                                        sql = """UPDATE sga_persona SET sexo_id='%s' WHERE cedula='%s'; """ % (sexo[0], integrante.inscripcionaspirante.persona.cedula)
                                        cursor.execute(sql)

                                if integrante.inscripcionaspirante.persona.pais:
                                    sql = """SELECT pai.id FROM sga_pais AS pai WHERE pai.id='%s'  AND pai.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.pais.id)
                                    cursor.execute(sql)
                                    pais = cursor.fetchone()

                                    if pais is not None:
                                        sql = """UPDATE sga_persona SET pais_id='%s' WHERE cedula='%s'; """ % (pais[0], integrante.inscripcionaspirante.persona.cedula)
                                        cursor.execute(sql)

                                if integrante.inscripcionaspirante.persona.parroquia:
                                    sql = """SELECT pa.id FROM sga_parroquia AS pa WHERE pa.id='%s'  AND pa.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.parroquia.id)
                                    cursor.execute(sql)
                                    parroquia = cursor.fetchone()

                                    if parroquia is not None:
                                        sql = """UPDATE sga_persona SET parroquia_id='%s' WHERE cedula='%s'; """ % (parroquia[0], integrante.inscripcionaspirante.persona.cedula)
                                        cursor.execute(sql)

                                if integrante.inscripcionaspirante.persona.canton:
                                    sql = """SELECT ca.id FROM sga_canton AS ca WHERE ca.id='%s'  AND ca.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.canton.id)
                                    cursor.execute(sql)
                                    canton = cursor.fetchone()

                                    if canton is not None:
                                        sql = """UPDATE sga_persona SET canton_id='%s' WHERE cedula='%s'; """ % (canton[0], integrante.inscripcionaspirante.persona.cedula)
                                        cursor.execute(sql)

                                if integrante.inscripcionaspirante.persona.provincia:
                                    sql = """SELECT pro.id FROM sga_provincia AS pro WHERE pro.id='%s'  AND pro.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.provincia.id)
                                    cursor.execute(sql)
                                    provincia = cursor.fetchone()

                                    if provincia is not None:
                                        sql = """UPDATE sga_persona SET provincia_id='%s' WHERE cedula='%s'; """ % (provincia[0], integrante.inscripcionaspirante.persona.cedula)
                                        cursor.execute(sql)
                                #ID DE PERSONA EN EPUNEMI
                                sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.cedula, integrante.inscripcionaspirante.persona.cedula, integrante.inscripcionaspirante.persona.cedula)
                                cursor.execute(sql)
                                idalumno = cursor.fetchone()
                                alumnoepu = idalumno[0]
                            else:
                                alumnoepu = idalumno[0]

                            for r in rubrosunemi:
                                # Consulto el tipo otro rubro en epunemi
                                sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (r.tipo.id)
                                cursor.execute(sql)
                                registro = cursor.fetchone()

                                # Si existe
                                if registro is not None:
                                    tipootrorubro = registro[0]
                                else:
                                    # Debo crear ese tipo de rubro
                                    # Consulto centro de costo
                                    sql = """SELECT id FROM sagest_centrocosto WHERE status=True AND unemi=True AND tipo=%s;""" % (r.tipo.tiporubro)
                                    cursor.execute(sql)
                                    centrocosto = cursor.fetchone()
                                    idcentrocosto = centrocosto[0]

                                    # Consulto la cuenta contable
                                    cuentacontable = CuentaContable.objects.get(partida=r.tipo.partida, status=True)

                                    # Creo el tipo de rubro en epunemi
                                    sql = """ Insert Into sagest_tipootrorubro (status, nombre, partida_id, valor, interface, activo, ivaaplicado_id, nofactura, exportabanco, cuentacontable_id, centrocosto_id, tiporubro, idtipootrorubrounemi, unemi, es_especie, es_convalidacionconocimiento)
                                                        VALUES(TRUE, '%s', %s, %s, FALSE, TRUE, %s, FALSE, TRUE, %s, %s, 1, %s, TRUE, FALSE, FALSE); """ % (
                                        r.tipo.nombre, cuentacontable.partida.id, r.tipo.valor,
                                        r.tipo.ivaaplicado.id, cuentacontable.id, idcentrocosto,
                                        r.tipo.id)
                                    cursor.execute(sql)

                                    print(".:: Tipo de Rubro creado en EPUNEMI ::.")

                                    # Obtengo el id recién creado del tipo de rubro
                                    sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (r.tipo.id)
                                    cursor.execute(sql)
                                    registro = cursor.fetchone()
                                    tipootrorubro = registro[0]

                                #pregunto si no existe rubro con ese id de unemi
                                sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE; """ % (r.id)
                                cursor.execute(sql)
                                registrorubro = cursor.fetchone()

                                if registrorubro is None:
                                    # Creo nuevo rubro en epunemi
                                    sql = """ INSERT INTO sagest_rubro (status, persona_id, nombre, cuota, tipocuota, fecha, fechavence,
                                                valor, saldo, iva_id, valoriva, totalunemi, valortotal, cancelado, observacion, 
                                                idrubrounemi, tipo_id, fecha_creacion, usuario_creacion_id, tienenotacredito, valornotacredito, 
                                                valordescuento, anulado, compromisopago, refinanciado, bloqueado, bloqueadopornovedad, 
                                                titularcambiado, coactiva) 
                                              VALUES (TRUE, %s, '%s', %s, %s, '/%s/', '/%s/', %s, %s, %s, %s, %s, %s, %s, '%s', %s, %s, NOW(), 1, FALSE, 0, 0, FALSE, %s, %s, %s, FALSE, FALSE, %s); """ \
                                          % (alumnoepu, r.nombre, r.cuota, r.tipocuota, r.fecha, r.fechavence, r.saldo, r.saldo, r.iva_id, r.valoriva, r.valor,
                                             r.valortotal, r.cancelado, r.observacion, r.id, tipootrorubro, r.compromisopago if r.compromisopago else 0,
                                             r.refinanciado, r.bloqueado, r.coactiva)
                                    cursor.execute(sql)

                                    sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND anulado=FALSE; """ % (r.id)
                                    cursor.execute(sql)
                                    registro = cursor.fetchone()
                                    rubroepunemi = registro[0]

                                    r.idrubroepunemi = rubroepunemi
                                    r.save()

                                    print(".:: Rubro creado en EPUNEMI ::.")
                                else:
                                    sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND cancelado=FALSE; """ % (r.id)
                                    cursor.execute(sql)
                                    rubronoc = cursor.fetchone()

                                    if rubronoc is not None:
                                        sql = """SELECT id FROM sagest_pago WHERE rubro_id=%s; """ % (registrorubro[0])
                                        cursor.execute(sql)
                                        tienerubropagos = cursor.fetchone()

                                        if tienerubropagos is not None:
                                            pass
                                        else:
                                            sql = """UPDATE sagest_rubro SET nombre = '%s', fecha = '/%s/', fechavence = '/%s/',
                                               valor = %s, saldo = %s, iva_id = %s, valoriva = %s, totalunemi = %s,
                                               valortotal = %s, observacion = '%s', tipo_id = %s
                                               WHERE id=%s; """ % (r.nombre, r.fecha, r.fechavence, r.saldo, r.saldo, r.iva_id,
                                                                   r.valoriva, r.valor, r.valortotal, r.observacion, tipootrorubro,
                                                                   registrorubro[0])
                                            cursor.execute(sql)
                                        r.idrubroepunemi = registrorubro[0]
                                        r.save()

                    if integrante.formapagopac.id == 2 or integrante.Configfinanciamientocohorte:
                        # if integrante.cumple_con_requisitos_comercializacion():
                        if integrante.Configfinanciamientocohorte:
                            if integrante.Configfinanciamientocohorte.valormatricula:
                                if not integrante.genero_rubro_matricula():
                                    tablaa = None
                                    if integrante.contrato_set.filter(status=True).values('id').last() and integrante.contrato_set.filter(status=True).last().tablaamortizacion_set.values('id').filter(status=True, cuota=0).last():
                                        tablaa = integrante.contrato_set.filter(status=True).last().tablaamortizacion_set.filter(status=True, cuota=0).last()
                                    valormatricula = integrante.Configfinanciamientocohorte.valormatricula
                                    tiporubroarancel = TipoOtroRubro.objects.get(pk=2845)
                                    rubro = Rubro(tipo=tiporubroarancel,
                                                  persona=integrante.inscripcionaspirante.persona,
                                                  cohortemaestria=integrante.cohortes,
                                                  inscripcion=integrante,
                                                  relacionados=None,
                                                  nombre=tiporubroarancel.nombre + ' - ' + integrante.cohortes.maestriaadmision.descripcion + ' - ' + integrante.cohortes.descripcion,
                                                  cuota=1,
                                                  fecha=datetime.now().date(),
                                                  fechavence=integrante.cohortes.fechavencerubro,
                                                  valor=valormatricula,
                                                  iva_id=1,
                                                  valoriva=0,
                                                  valortotal=valormatricula,
                                                  saldo=valormatricula,
                                                  epunemi=True,
                                                  idrubroepunemi=0,
                                                  admisionposgradotipo=2,
                                                  tablaamortizacionposgrado=tablaa,
                                                  cancelado=False)
                                    rubro.save(request)
                                    log(u'Genero rubro por concepto matricula posgrado: %s programa de %s' % (integrante, integrante.cohortes.maestriaadmision.descripcion), request, "add")

                                if not integrante.genero_rubro_programa2():
                                    if not integrante.cohortes.tiporubro:
                                        raise NameError('El programa %s no tiene configurado el Tipo de rubro para generar los rubros.'%(integrante.cohortes))
                                    tiporubroarancel = TipoOtroRubro.objects.get(pk=integrante.cohortes.tiporubro.id)
                                    tablaamortizacion = integrante.contrato_set.filter(status=True).last().tablaamortizacion_set.filter(status=True)
                                    for cuotarubro in tablaamortizacion:
                                        if not cuotarubro.cuota == 0:
                                            if 'CONVENIOS POSGRADO' in cuotarubro.nombre:
                                                tiporubroconvenio = TipoOtroRubro.objects.get(pk=3634)
                                                rubro = Rubro(tipo=tiporubroconvenio,
                                                              persona=integrante.inscripcionaspirante.persona,
                                                              cohortemaestria=integrante.cohortes,
                                                              inscripcion=integrante,
                                                              relacionados=None,
                                                              nombre= cuotarubro.nombre,
                                                              cuota=cuotarubro.cuota,
                                                              fecha=cuotarubro.fecha,
                                                              fechavence=cuotarubro.fechavence,
                                                              valor=cuotarubro.valor,
                                                              iva_id=1,
                                                              valoriva=0,
                                                              valortotal=cuotarubro.valor,
                                                              saldo=cuotarubro.valor,
                                                              epunemi=True,
                                                              idrubroepunemi=0,
                                                              admisionposgradotipo=3,
                                                              tablaamortizacionposgrado=cuotarubro,
                                                              cancelado=False)
                                                rubro.save(request)
                                            else:
                                                rubro = Rubro(tipo=tiporubroarancel,
                                                              persona=integrante.inscripcionaspirante.persona,
                                                              cohortemaestria=integrante.cohortes,
                                                              inscripcion=integrante,
                                                              relacionados=None,
                                                              nombre=tiporubroarancel.nombre + ' - ' + cuotarubro.nombre,
                                                              cuota=cuotarubro.cuota,
                                                              fecha=cuotarubro.fecha,
                                                              fechavence=cuotarubro.fechavence,
                                                              valor=cuotarubro.valor,
                                                              iva_id=1,
                                                              valoriva=0,
                                                              valortotal=cuotarubro.valor,
                                                              saldo=cuotarubro.valor,
                                                              epunemi=True,
                                                              idrubroepunemi=0,
                                                              admisionposgradotipo=3,
                                                              tablaamortizacionposgrado=cuotarubro,
                                                              cancelado=False)
                                                rubro.save(request)
                                    integrante.tipocobro = 3
                                    integrante.tipo = tiporubroarancel
                                    integrante.save(request)
                                    log(u'Generó rubro por concepto costo programa posgrado: %s programa de %s' % (integrante, integrante.cohortes.maestriaadmision.descripcion), request, "add")

                                rubrosunemi = Rubro.objects.filter(status=True, inscripcion=integrante, epunemi = True, cancelado=False)

                                # -------CREAR PERSONA EPUNEMI-------
                                cursor = connections['epunemi'].cursor()
                                sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.cedula, integrante.inscripcionaspirante.persona.cedula, integrante.inscripcionaspirante.persona.cedula)
                                cursor.execute(sql)
                                idalumno = cursor.fetchone()

                                if idalumno is None:
                                    sql = """ INSERT INTO sga_persona (status, nombres, apellido1, apellido2, cedula, ruc, pasaporte,
                                                nacimiento, tipopersona, sector, direccion,  direccion2,
                                                num_direccion, telefono, telefono_conv, email, contribuyenteespecial,
                                                anioresidencia, nacionalidad, ciudad, referencia, emailinst, identificacioninstitucion,
                                                regitrocertificacion, libretamilitar, servidorcarrera, concursomeritos, telefonoextension,
                                                tipocelular, periodosabatico, real, lgtbi, datosactualizados, confirmarextensiontelefonia,
                                                acumuladecimo, acumulafondoreserva, representantelegal, inscripcioncurso, unemi,
                                                idunemi)
                                                        VALUES(TRUE, '%s', '%s', '%s', '%s', '%s', '%s', '/%s/', %s, '%s', '%s', '%s', '%s', '%s', '%s', '%s', 
                                                        FALSE, 0, '', '', '', '', '', '', '', FALSE, FALSE, '', 0, FALSE, TRUE, FALSE, 0, FALSE, TRUE, FALSE, FALSE, 
                                                        FALSE, FALSE, 0); """ % (
                                        integrante.inscripcionaspirante.persona.nombres, integrante.inscripcionaspirante.persona.apellido1,
                                        integrante.inscripcionaspirante.persona.apellido2, integrante.inscripcionaspirante.persona.cedula,
                                        integrante.inscripcionaspirante.persona.ruc if integrante.inscripcionaspirante.persona.ruc else '',
                                        integrante.inscripcionaspirante.persona.pasaporte if integrante.inscripcionaspirante.persona.pasaporte else '',
                                        integrante.inscripcionaspirante.persona.nacimiento,
                                        integrante.inscripcionaspirante.persona.tipopersona if integrante.inscripcionaspirante.persona.tipopersona else 1,
                                        integrante.inscripcionaspirante.persona.sector if integrante.inscripcionaspirante.persona.sector else '',
                                        integrante.inscripcionaspirante.persona.direccion if integrante.inscripcionaspirante.persona.direccion else '',
                                        integrante.inscripcionaspirante.persona.direccion2 if integrante.inscripcionaspirante.persona.direccion2 else '',
                                        integrante.inscripcionaspirante.persona.num_direccion if integrante.inscripcionaspirante.persona.num_direccion else '',
                                        integrante.inscripcionaspirante.persona.telefono if integrante.inscripcionaspirante.persona.telefono else '',
                                        integrante.inscripcionaspirante.persona.telefono_conv if integrante.inscripcionaspirante.persona.telefono_conv else '',
                                        integrante.inscripcionaspirante.persona.email if integrante.inscripcionaspirante.persona.email else '')
                                    cursor.execute(sql)

                                    if integrante.inscripcionaspirante.persona.sexo:
                                        sql = """SELECT sexo.id FROM sga_sexo AS sexo WHERE sexo.id='%s'  AND sexo.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.sexo.id)
                                        cursor.execute(sql)
                                        sexo = cursor.fetchone()

                                        if sexo is not None:
                                            sql = """UPDATE sga_persona SET sexo_id='%s' WHERE cedula='%s'; """ % (sexo[0], integrante.inscripcionaspirante.persona.cedula)
                                            cursor.execute(sql)

                                    if integrante.inscripcionaspirante.persona.pais:
                                        sql = """SELECT pai.id FROM sga_pais AS pai WHERE pai.id='%s'  AND pai.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.pais.id)
                                        cursor.execute(sql)
                                        pais = cursor.fetchone()

                                        if pais is not None:
                                            sql = """UPDATE sga_persona SET pais_id='%s' WHERE cedula='%s'; """ % (pais[0], integrante.inscripcionaspirante.persona.cedula)
                                            cursor.execute(sql)

                                    if integrante.inscripcionaspirante.persona.parroquia:
                                        sql = """SELECT pa.id FROM sga_parroquia AS pa WHERE pa.id='%s'  AND pa.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.parroquia.id)
                                        cursor.execute(sql)
                                        parroquia = cursor.fetchone()

                                        if parroquia is not None:
                                            sql = """UPDATE sga_persona SET parroquia_id='%s' WHERE cedula='%s'; """ % (parroquia[0], integrante.inscripcionaspirante.persona.cedula)
                                            cursor.execute(sql)

                                    if integrante.inscripcionaspirante.persona.canton:
                                        sql = """SELECT ca.id FROM sga_canton AS ca WHERE ca.id='%s'  AND ca.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.canton.id)
                                        cursor.execute(sql)
                                        canton = cursor.fetchone()

                                        if canton is not None:
                                            sql = """UPDATE sga_persona SET canton_id='%s' WHERE cedula='%s'; """ % (canton[0], integrante.inscripcionaspirante.persona.cedula)
                                            cursor.execute(sql)

                                    if integrante.inscripcionaspirante.persona.provincia:
                                        sql = """SELECT pro.id FROM sga_provincia AS pro WHERE pro.id='%s'  AND pro.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.provincia.id)
                                        cursor.execute(sql)
                                        provincia = cursor.fetchone()

                                        if provincia is not None:
                                            sql = """UPDATE sga_persona SET provincia_id='%s' WHERE cedula='%s'; """ % (provincia[0], integrante.inscripcionaspirante.persona.cedula)
                                            cursor.execute(sql)
                                    #ID DE PERSONA EN EPUNEMI
                                    sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.cedula, integrante.inscripcionaspirante.persona.cedula, integrante.inscripcionaspirante.persona.cedula)
                                    cursor.execute(sql)
                                    idalumno = cursor.fetchone()
                                    alumnoepu = idalumno[0]
                                else:
                                    alumnoepu = idalumno[0]

                                for r in rubrosunemi:
                                    # Consulto el tipo otro rubro en epunemi
                                    sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (r.tipo.id)
                                    cursor.execute(sql)
                                    registro = cursor.fetchone()

                                    # Si existe
                                    if registro is not None:
                                        tipootrorubro = registro[0]
                                    else:
                                        # Debo crear ese tipo de rubro
                                        # Consulto centro de costo
                                        sql = """SELECT id FROM sagest_centrocosto WHERE status=True AND unemi=True AND tipo=%s;""" % (r.tipo.tiporubro)
                                        cursor.execute(sql)
                                        centrocosto = cursor.fetchone()
                                        idcentrocosto = centrocosto[0]

                                        # Consulto la cuenta contable
                                        cuentacontable = CuentaContable.objects.get(partida=r.tipo.partida, status=True)

                                        # Creo el tipo de rubro en epunemi
                                        sql = """ Insert Into sagest_tipootrorubro (status, nombre, partida_id, valor, interface, activo, ivaaplicado_id, nofactura, exportabanco, cuentacontable_id, centrocosto_id, tiporubro, idtipootrorubrounemi, unemi, es_especie, es_convalidacionconocimiento)
                                                            VALUES(TRUE, '%s', %s, %s, FALSE, TRUE, %s, FALSE, TRUE, %s, %s, 1, %s, TRUE, FALSE, FALSE); """ % (
                                            r.tipo.nombre, cuentacontable.partida.id, r.tipo.valor,
                                            r.tipo.ivaaplicado.id, cuentacontable.id, idcentrocosto,
                                            r.tipo.id)
                                        cursor.execute(sql)

                                        print(".:: Tipo de Rubro creado en EPUNEMI ::.")

                                        # Obtengo el id recién creado del tipo de rubro
                                        sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (r.tipo.id)
                                        cursor.execute(sql)
                                        registro = cursor.fetchone()
                                        tipootrorubro = registro[0]

                                    #pregunto si no existe rubro con ese id de unemi
                                    sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE; """ % (r.id)
                                    cursor.execute(sql)
                                    registrorubro = cursor.fetchone()

                                    if registrorubro is None:
                                        # Creo nuevo rubro en epunemi
                                        sql = """ INSERT INTO sagest_rubro (status, persona_id, nombre, cuota, tipocuota, fecha, fechavence,
                                                    valor, saldo, iva_id, valoriva, totalunemi, valortotal, cancelado, observacion, 
                                                    idrubrounemi, tipo_id, fecha_creacion, usuario_creacion_id, tienenotacredito, valornotacredito, 
                                                    valordescuento, anulado, compromisopago, refinanciado, bloqueado, bloqueadopornovedad, 
                                                    titularcambiado, coactiva) 
                                                  VALUES (TRUE, %s, '%s', %s, %s, '/%s/', '/%s/', %s, %s, %s, %s, %s, %s, %s, '%s', %s, %s, NOW(), 1, FALSE, 0, 0, FALSE, %s, %s, %s, FALSE, FALSE, %s); """ \
                                              % (alumnoepu, r.nombre, r.cuota, r.tipocuota, r.fecha, r.fechavence, r.saldo, r.saldo, r.iva_id, r.valoriva, r.valor,
                                                 r.valortotal, r.cancelado, r.observacion, r.id, tipootrorubro, r.compromisopago if r.compromisopago else 0,
                                                 r.refinanciado, r.bloqueado, r.coactiva)
                                        cursor.execute(sql)

                                        sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND anulado=FALSE; """ % (r.id)
                                        cursor.execute(sql)
                                        registro = cursor.fetchone()
                                        rubroepunemi = registro[0]

                                        r.idrubroepunemi = rubroepunemi
                                        r.save()

                                        print(".:: Rubro creado en EPUNEMI ::.")
                                    else:
                                        sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND cancelado=FALSE; """ % (r.id)
                                        cursor.execute(sql)
                                        rubronoc = cursor.fetchone()

                                        if rubronoc is not None:
                                            sql = """SELECT id FROM sagest_pago WHERE rubro_id=%s; """ % (registrorubro[0])
                                            cursor.execute(sql)
                                            tienerubropagos = cursor.fetchone()

                                            if tienerubropagos is not None:
                                                pass
                                            else:
                                                sql = """UPDATE sagest_rubro SET nombre = '%s', fecha = '/%s/', fechavence = '/%s/',
                                                   valor = %s, saldo = %s, iva_id = %s, valoriva = %s, totalunemi = %s,
                                                   valortotal = %s, observacion = '%s', tipo_id = %s
                                                   WHERE id=%s; """ % (r.nombre, r.fecha, r.fechavence, r.saldo, r.saldo, r.iva_id,
                                                                       r.valoriva, r.valor, r.valortotal, r.observacion, tipootrorubro,
                                                                       registrorubro[0])
                                                cursor.execute(sql)
                                            r.idrubroepunemi = registrorubro[0]
                                            r.save()
                        else:
                            raise NameError('%s no tiene configurado el tipo de financiamiento.' % (integrante.inscripcionaspirante))
                        # else:
                        #     raise NameError('%s no tiene aprobados los requisitos de financiamiento.' % (integrante.inscripcionaspirante))
                else:
                    raise NameError('%s no asignado la forma de pago.' % (integrante.inscripcionaspirante))
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar rubros. %s"%ex})

        elif action == 'actualizardocumentos':
            try:
                integrante = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                if CambioAdmitidoCohorteInscripcion.objects.filter(status=True, inscripcionCohorte=integrante).exists():
                    cambio = CambioAdmitidoCohorteInscripcion.objects.filter(status=True, inscripcionCohorte=integrante).order_by('-id')[0]
                    cambio.cohortes = integrante.cohortes
                    cambio.save(request)

                    log(u'Editó la cohorte del lead: %s' % integrante, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'preaprobarrequisitos':
            try:
                integrante = InscripcionCohorte.objects.get(status=True, pk=int(request.POST['id']))
                integrante.preaprobado = True
                integrante.save(request)
                deta = DetallePreAprobacionPostulante(inscripcion=integrante,
                                                      preaprobado=integrante.preaprobado)
                deta.save(request)
                log(u'Pre-aprobó requistos de admisión del lead: %s' % integrante, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'eliminarterritorio':
            try:
                territorio = AsesorTerritorio.objects.get(status=True, pk=int(request.POST['id']))
                territorio.status = False
                territorio.save(request)
                log(u'Pre-Eliminó territorio del asesor: %s' % territorio, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        # elif action == 'rechazarpostulante':
        #     try:
        #         integrante = InscripcionCohorte.objects.get(status=True, pk=int(request.POST['id']))
        #         integrante.estado_aprobador = 3
        #         integrante.status = False
        #         integrante.save(request)
        #         log(u'Rechazó la postulación del lead: %s' % integrante, request, "edit")
        #         return JsonResponse({"result": "ok"})
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'rechazarpostulante':
            try:
                with transaction.atomic():
                    from posgrado.forms import RechazoDesactivaForm
                    f = RechazoDesactivaForm(request.POST)
                    if f.is_valid():
                        hoy = datetime.now().date()
                        instancia = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                        if f.cleaned_data['motivo'] == '1':
                            return JsonResponse({"result": "bad", "mensaje": u"Seleccione un motivo."})
                        instancia.motivo_rechazo_desactiva = f.cleaned_data['motivo']
                        # integrante = InscripcionCohorte.objects.get(status=True, pk=int(request.POST['id']))
                        instancia.estado_aprobador = 3
                        instancia.status = False
                        instancia.save(request)
                        log(u'Rechazó la postulación del lead: %s' % instancia, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'desactivarventa':
            try:
                integrante = VentasProgramaMaestria.objects.get(status=True, pk=int(request.POST['id']))
                integrante.status = False
                integrante.save(request)
                log(u'Desactivó la venta: %s' % integrante.inscripcioncohorte, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'restaurarpostulante':
            try:
                integrante = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                integrante.status = True
                integrante.tiporespuesta = None
                integrante.motivo_rechazo_desactiva = 1
                requistosmaestria = RequisitosMaestria.objects.filter(status=True, cohorte=integrante.cohortes,
                                                                      requisito__claserequisito__clasificacion__id=1,
                                                                      obligatorio=True).values_list('id', flat=True)
                for requisto in requistosmaestria:
                    if EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=integrante,
                                                                   requisitos_id=requisto,
                                                                   requisitos__requisito__claserequisito__clasificacion__id=1).exists():
                        evi = EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=integrante,
                                                                          requisitos_id=requisto,
                                                                          requisitos__requisito__claserequisito__clasificacion__id=1).order_by('-id').first()
                        if evi.ultima_evidencia():
                            deta = DetalleEvidenciaRequisitosAspirante.objects.get(pk=evi.ultima_evidencia().id)
                            deta.estado_aprobacion = 1
                            deta.observacion = "Pendiente debido a restauración de Postulación"
                            deta.save()

                requistosmaestria = RequisitosMaestria.objects.filter(status=True, cohorte=integrante.cohortes,
                                                                      requisito__claserequisito__clasificacion__id=3,
                                                                      obligatorio=True).values_list('id', flat=True)
                for requisto in requistosmaestria:
                    if EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=integrante,
                                                                   requisitos_id=requisto,
                                                                   requisitos__requisito__claserequisito__clasificacion__id=3).exists():
                        evi = EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=integrante,
                                                                          requisitos_id=requisto,
                                                                          requisitos__requisito__claserequisito__clasificacion__id=3).order_by(
                            '-id').first()
                        if evi.ultima_evidencia():
                            deta = DetalleEvidenciaRequisitosAspirante.objects.get(pk=evi.ultima_evidencia().id)
                            deta.estado_aprobacion = 1
                            deta.observacion = "Pendiente debido a restauración de Postulación"
                            deta.save()
                if integrante.total_evidence_lead():
                    integrante.estado_aprobador = 2
                else:
                    integrante.estado_aprobador = 1
                integrante.save(request)

                # SI TIENE RUBROS GENERADOS
                if Rubro.objects.filter(inscripcion=integrante, status=True).exists():
                    rubros = Rubro.objects.filter(inscripcion=integrante, status=True)
                    for rubro in rubros:
                        if rubro.idrubroepunemi != 0:
                            cursor = connections['epunemi'].cursor()
                            sql = """SELECT id FROM sagest_pago WHERE rubro_id=%s; """ % (rubro.idrubroepunemi)
                            cursor.execute(sql)
                            tienerubropagos = cursor.fetchone()

                            if tienerubropagos is None:
                                sql = """DELETE FROM sagest_rubro WHERE sagest_rubro.id=%s AND sagest_rubro.idrubrounemi=%s; """ % (
                                    rubro.idrubroepunemi, rubro.id)
                                cursor.execute(sql)
                                cursor.close()

                            rubro.status = False
                            rubro.save()

                if integrante.cohortes.tipo == 1:
                    if IntegranteGrupoExamenMsc.objects.filter(status=True, inscripcion=integrante).exists():
                        lista = IntegranteGrupoExamenMsc.objects.filter(status=True, inscripcion=integrante)
                        for li in lista:
                            li.status = False
                            li.save()

                    if IntegranteGrupoEntrevitaMsc.objects.filter(status=True, inscripcion=integrante).exists():
                        lista2 = IntegranteGrupoEntrevitaMsc.objects.filter(status=True, inscripcion=integrante)
                        for li2 in lista2:
                            li2.status = False
                            li2.save()

                elif integrante.cohortes.tipo == 2:
                    if IntegranteGrupoExamenMsc.objects.filter(status=True, inscripcion=integrante).exists():
                        lista = IntegranteGrupoExamenMsc.objects.filter(status=True, inscripcion=integrante)
                        for li in lista:
                            li.status = False
                            li.save()

                if Contrato.objects.filter(status=True, inscripcion=integrante).exists():
                    contratopos = Contrato.objects.get(status=True, inscripcion=integrante)

                    detalleevidencia = DetalleAprobacionContrato(contrato_id=contratopos.id, espagare=False,
                                                                 observacion='Pendiente por restauración de postulación',
                                                                 persona=persona, estado_aprobacion=1,
                                                                 fecha_aprobacion=datetime.now(),
                                                                 archivocontrato=contratopos.archivocontrato)
                    detalleevidencia.save(request)

                    if contratopos.inscripcion.formapagopac.id == 2:
                        detalleevidencia = DetalleAprobacionContrato(contrato_id=contratopos.id, espagare=True,
                                                                     observacion='Pendiente por restauración de postulación',
                                                                     persona=persona, estado_aprobacion=1,
                                                                     fecha_aprobacion=datetime.now(),
                                                                     archivocontrato=contratopos.archivopagare)
                        detalleevidencia.save(request)

                    contratopos.estado = 1
                    contratopos.estadopagare = 1
                    contratopos.save(request)

                if integrante.asesor:
                    asunto = u"POSTULANTE RESTAURADO"
                    observacion = f'Se le comunica que el postulante {integrante.inscripcionaspirante.persona} con cédula {integrante.inscripcionaspirante.persona.cedula} ha sido restaurado. Por favor, revisar los documentos de admisión para su pre aprobación.'
                    para = integrante.asesor.persona
                    perfiu = integrante.asesor.perfil_administrativo()

                    notificacion3(asunto, observacion, para, None,
                                  '/comercial?s=' + integrante.inscripcionaspirante.persona.cedula,
                                  integrante.pk, 1,
                                  'sga', InscripcionCohorte, perfiu, request)
                log(u'Restauró la postulación del lead: %s' % integrante, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'habilitaroficio':
            try:
                integrante = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                integrante.puedesubiroficio = True
                integrante.save(request)
                log(u'Habilitó el oficio de terminación de contrato del lead: %s' % integrante, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deshabilitaroficio':
            try:
                integrante = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                integrante.puedesubiroficio = False
                integrante.save(request)
                log(u'Deshabilitó el oficio de terminación de contrato del lead: %s' % integrante, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'habilitarbeca':
            try:
                integrante = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                integrante.es_becado = True
                integrante.save(request)
                log(u'Marcó como beca al lead: %s' % integrante, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deshabilitarbeca':
            try:
                integrante = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                integrante.es_becado = False
                integrante.save(request)
                log(u'Desmarcó como beca al lead: %s' % integrante, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'cancelarsolicitud':
            try:
                contrato = Contrato.objects.get(status=True, pk=int(request.POST['id']))
                contrato.estado = 2
                contrato.archivooficiodescargado = ''
                contrato.archivooficio = ''
                contrato.save(request)

                detalle = DetalleAprobacionContrato(contrato=contrato,
                                                    estado_aprobacion=2,
                                                    fecha_aprobacion=datetime.now(),
                                                    observacion='Su oficio ha sido cancelado',
                                                    archivocontrato=contrato.archivooficio,
                                                    persona=persona,
                                                    esoficio=True)
                detalle.save(request)
                log(u'Canceló el oficio de terminación de contrato del lead: %s' % contrato.inscripcion, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'revertirpreaprobarrequisitos':
            try:
                integrante = InscripcionCohorte.objects.get(status=True, pk=int(request.POST['id']))
                integrante.preaprobado = False
                integrante.save(request)
                deta = DetallePreAprobacionPostulante(inscripcion=integrante,
                                                      preaprobado=integrante.preaprobado)
                deta.save(request)
                log(u'Retirar Pre-aprobación de requistos de admisión del lead: %s' % integrante, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'actualizarventa':
            try:
                venta = VentasProgramaMaestria.objects.get(status=True, pk=int(request.POST['id']))
                venta.fecha = convertir_fecha(request.POST['fec'])
                venta.hora = convertir_hora(request.POST['h'])
                venta.save(request)
                log(u'Actualizó fecha de la venta: %s' % venta, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'restaurar_postulacion':
            try:
                prospecto = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                if InscripcionCohorte.objects.filter(inscripcionaspirante=prospecto.inscripcionaspirante, status=True).exists():
                    prospecto.doblepostulacion = True
                prospecto.status = True
                prospecto.save(request)
                log(u'Restauración de la postulacion: %s' % prospecto, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        elif action == 'cuadrarrubrosepunemi':
            try:
                integrante = InscripcionCohorte.objects.get(pk=int(request.POST['id']))
                # inscripcioncohorte = integrante
                # inscripcion=None

                rubrosunemi = Rubro.objects.filter(status=True, inscripcion=integrante, epunemi = True, cancelado=False)

                # -------CREAR PERSONA EPUNEMI-------
                cursor = connections['epunemi'].cursor()
                sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.cedula, integrante.inscripcionaspirante.persona.cedula, integrante.inscripcionaspirante.persona.cedula)
                cursor.execute(sql)
                idalumno = cursor.fetchone()

                if idalumno is None:
                    sql = """ INSERT INTO sga_persona (status, nombres, apellido1, apellido2, cedula, ruc, pasaporte,
                                nacimiento, tipopersona, sector, direccion,  direccion2,
                                num_direccion, telefono, telefono_conv, email, contribuyenteespecial,
                                anioresidencia, nacionalidad, ciudad, referencia, emailinst, identificacioninstitucion,
                                regitrocertificacion, libretamilitar, servidorcarrera, concursomeritos, telefonoextension,
                                tipocelular, periodosabatico, real, lgtbi, datosactualizados, confirmarextensiontelefonia,
                                acumuladecimo, acumulafondoreserva, representantelegal, inscripcioncurso, unemi,
                                idunemi)
                                        VALUES(TRUE, '%s', '%s', '%s', '%s', '%s', '%s', '/%s/', %s, '%s', '%s', '%s', '%s', '%s', '%s', '%s', 
                                        FALSE, 0, '', '', '', '', '', '', '', FALSE, FALSE, '', 0, FALSE, TRUE, FALSE, 0, FALSE, TRUE, FALSE, FALSE, 
                                        FALSE, FALSE, 0); """ % (
                        integrante.inscripcionaspirante.persona.nombres, integrante.inscripcionaspirante.persona.apellido1,
                        integrante.inscripcionaspirante.persona.apellido2, integrante.inscripcionaspirante.persona.cedula,
                        integrante.inscripcionaspirante.persona.ruc if integrante.inscripcionaspirante.persona.ruc else '',
                        integrante.inscripcionaspirante.persona.pasaporte if integrante.inscripcionaspirante.persona.pasaporte else '',
                        integrante.inscripcionaspirante.persona.nacimiento,
                        integrante.inscripcionaspirante.persona.tipopersona if integrante.inscripcionaspirante.persona.tipopersona else 1,
                        integrante.inscripcionaspirante.persona.sector if integrante.inscripcionaspirante.persona.sector else '',
                        integrante.inscripcionaspirante.persona.direccion if integrante.inscripcionaspirante.persona.direccion else '',
                        integrante.inscripcionaspirante.persona.direccion2 if integrante.inscripcionaspirante.persona.direccion2 else '',
                        integrante.inscripcionaspirante.persona.num_direccion if integrante.inscripcionaspirante.persona.num_direccion else '',
                        integrante.inscripcionaspirante.persona.telefono if integrante.inscripcionaspirante.persona.telefono else '',
                        integrante.inscripcionaspirante.persona.telefono_conv if integrante.inscripcionaspirante.persona.telefono_conv else '',
                        integrante.inscripcionaspirante.persona.email if integrante.inscripcionaspirante.persona.email else '')
                    cursor.execute(sql)

                    if integrante.inscripcionaspirante.persona.sexo:
                        sql = """SELECT sexo.id FROM sga_sexo AS sexo WHERE sexo.id='%s'  AND sexo.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.sexo.id)
                        cursor.execute(sql)
                        sexo = cursor.fetchone()

                        if sexo is not None:
                            sql = """UPDATE sga_persona SET sexo_id='%s' WHERE cedula='%s'; """ % (sexo[0], integrante.inscripcionaspirante.persona.cedula)
                            cursor.execute(sql)

                    if integrante.inscripcionaspirante.persona.pais:
                        sql = """SELECT pai.id FROM sga_pais AS pai WHERE pai.id='%s'  AND pai.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.pais.id)
                        cursor.execute(sql)
                        pais = cursor.fetchone()

                        if pais is not None:
                            sql = """UPDATE sga_persona SET pais_id='%s' WHERE cedula='%s'; """ % (pais[0], integrante.inscripcionaspirante.persona.cedula)
                            cursor.execute(sql)

                    if integrante.inscripcionaspirante.persona.parroquia:
                        sql = """SELECT pa.id FROM sga_parroquia AS pa WHERE pa.id='%s'  AND pa.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.parroquia.id)
                        cursor.execute(sql)
                        parroquia = cursor.fetchone()

                        if parroquia is not None:
                            sql = """UPDATE sga_persona SET parroquia_id='%s' WHERE cedula='%s'; """ % (parroquia[0], integrante.inscripcionaspirante.persona.cedula)
                            cursor.execute(sql)

                    if integrante.inscripcionaspirante.persona.canton:
                        sql = """SELECT ca.id FROM sga_canton AS ca WHERE ca.id='%s'  AND ca.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.canton.id)
                        cursor.execute(sql)
                        canton = cursor.fetchone()

                        if canton is not None:
                            sql = """UPDATE sga_persona SET canton_id='%s' WHERE cedula='%s'; """ % (canton[0], integrante.inscripcionaspirante.persona.cedula)
                            cursor.execute(sql)

                    if integrante.inscripcionaspirante.persona.provincia:
                        sql = """SELECT pro.id FROM sga_provincia AS pro WHERE pro.id='%s'  AND pro.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.provincia.id)
                        cursor.execute(sql)
                        provincia = cursor.fetchone()

                        if provincia is not None:
                            sql = """UPDATE sga_persona SET provincia_id='%s' WHERE cedula='%s'; """ % (provincia[0], integrante.inscripcionaspirante.persona.cedula)
                            cursor.execute(sql)
                    #ID DE PERSONA EN EPUNEMI
                    sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.cedula, integrante.inscripcionaspirante.persona.cedula, integrante.inscripcionaspirante.persona.cedula)
                    cursor.execute(sql)
                    idalumno = cursor.fetchone()
                    alumnoepu = idalumno[0]
                else:
                    alumnoepu = idalumno[0]

                for r in rubrosunemi:
                    # Consulto el tipo otro rubro en epunemi
                    sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (r.tipo.id)
                    cursor.execute(sql)
                    registro = cursor.fetchone()

                    # Si existe
                    if registro is not None:
                        tipootrorubro = registro[0]
                    else:
                        # Debo crear ese tipo de rubro
                        # Consulto centro de costo
                        sql = """SELECT id FROM sagest_centrocosto WHERE status=True AND unemi=True AND tipo=%s;""" % (r.tipo.tiporubro)
                        cursor.execute(sql)
                        centrocosto = cursor.fetchone()
                        idcentrocosto = centrocosto[0]

                        # Consulto la cuenta contable
                        cuentacontable = CuentaContable.objects.get(partida=r.tipo.partida, status=True)

                        # Creo el tipo de rubro en epunemi
                        sql = """ Insert Into sagest_tipootrorubro (status, nombre, partida_id, valor, interface, activo, ivaaplicado_id, nofactura, exportabanco, cuentacontable_id, centrocosto_id, tiporubro, idtipootrorubrounemi, unemi, es_especie, es_convalidacionconocimiento)
                                            VALUES(TRUE, '%s', %s, %s, FALSE, TRUE, %s, FALSE, TRUE, %s, %s, 1, %s, TRUE, FALSE, FALSE); """ % (
                            r.tipo.nombre, cuentacontable.partida.id, r.tipo.valor,
                            r.tipo.ivaaplicado.id, cuentacontable.id, idcentrocosto,
                            r.tipo.id)
                        cursor.execute(sql)

                        print(".:: Tipo de Rubro creado en EPUNEMI ::.")

                        # Obtengo el id recién creado del tipo de rubro
                        sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (r.tipo.id)
                        cursor.execute(sql)
                        registro = cursor.fetchone()
                        tipootrorubro = registro[0]

                    #pregunto si no existe rubro con ese id de unemi
                    sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE; """ % (r.id)
                    cursor.execute(sql)
                    registrorubro = cursor.fetchone()

                    if registrorubro is None:
                        # Creo nuevo rubro en epunemi
                        sql = """ INSERT INTO sagest_rubro (status, persona_id, nombre, cuota, tipocuota, fecha, fechavence,
                                    valor, saldo, iva_id, valoriva, totalunemi, valortotal, cancelado, observacion, 
                                    idrubrounemi, tipo_id, fecha_creacion, usuario_creacion_id, tienenotacredito, valornotacredito, 
                                    valordescuento, anulado, compromisopago, refinanciado, bloqueado, bloqueadopornovedad, 
                                    titularcambiado, coactiva) 
                                  VALUES (TRUE, %s, '%s', %s, %s, '/%s/', '/%s/', %s, %s, %s, %s, %s, %s, %s, '%s', %s, %s, NOW(), 1, FALSE, 0, 0, FALSE, %s, %s, %s, FALSE, FALSE, %s); """ \
                              % (alumnoepu, r.nombre, r.cuota, r.tipocuota, r.fecha, r.fechavence, r.saldo, r.saldo, r.iva_id, r.valoriva, r.valor,
                                 r.valortotal, r.cancelado, r.observacion, r.id, tipootrorubro, r.compromisopago if r.compromisopago else 0,
                                 r.refinanciado, r.bloqueado, r.coactiva)
                        cursor.execute(sql)

                        sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND anulado=FALSE; """ % (r.id)
                        cursor.execute(sql)
                        registro = cursor.fetchone()
                        rubroepunemi = registro[0]

                        r.idrubroepunemi = rubroepunemi
                        r.save()

                        print(".:: Rubro creado en EPUNEMI ::.")
                    else:
                        sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND cancelado=FALSE; """ % (r.id)
                        cursor.execute(sql)
                        rubronoc = cursor.fetchone()

                        if rubronoc is not None:
                            sql = """SELECT id FROM sagest_pago WHERE rubro_id=%s; """ % (registrorubro[0])
                            cursor.execute(sql)
                            tienerubropagos = cursor.fetchone()

                            if tienerubropagos is not None:
                                pass
                            else:
                                sql = """UPDATE sagest_rubro SET nombre = '%s', fecha = '/%s/', fechavence = '/%s/',
                                   valor = %s, saldo = %s, iva_id = %s, valoriva = %s, totalunemi = %s,
                                   valortotal = %s, observacion = '%s', tipo_id = %s
                                   WHERE id=%s; """ % (r.nombre, r.fecha, r.fechavence, r.saldo, r.saldo, r.iva_id,
                                                       r.valoriva, r.valor, r.valortotal, r.observacion, tipootrorubro,
                                                       registrorubro[0])
                                cursor.execute(sql)
                            r.idrubroepunemi = registrorubro[0]
                            r.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar rubros. %s"%ex})

        elif action == 'asignarnuevotipof':
            try:
                lead = InscripcionCohorte.objects.get(pk=int(request.POST['id']))

                f = AsignarTipoForm(request.POST)

                if f.is_valid():
                    if lead.Configfinanciamientocohorte.id != lead.id:
                        financiamiento = ConfigFinanciamientoCohorte.objects.get(pk=int(f.cleaned_data['tipo'].id))
                        lead.Configfinanciamientocohorte = financiamiento
                        lead.save(request)

                        deta = DetalleAprobacionFormaPago(inscripcion_id=lead.id,
                                                          formapagopac=lead.formapagopac,
                                                          estadoformapago=lead.estadoformapago,
                                                          persona=persona,
                                                          tipofinanciamiento = lead.Configfinanciamientocohorte)
                        deta.save(request)

                        rubrosunemi = Rubro.objects.filter(status=True, tablaamortizacionposgrado__contrato__id=lead.contrato_set.filter(status=True).last().id)

                        lista_rubros = []
                        for rub in rubrosunemi:
                            if not Pago.objects.filter(status=True, rubro=rub).exists():
                                lista_rubros.append(rub.id)

                        rubrosaeli = Rubro.objects.filter(status=True, id__in=lista_rubros)

                        cursor = connections['epunemi'].cursor()
                        for ru in rubrosaeli:
                            sql = "SELECT ru.id FROM sagest_rubro ru WHERE ru.idrubrounemi = '%s'" % (ru.id)
                            cursor.execute(sql)
                            idru = cursor.fetchone()

                            if idru is not None:
                                sql = "SELECT ru.rubro_id FROM sagest_logrubros ru WHERE ru.rubro_id = '%s'" % (idru[0])
                                cursor.execute(sql)
                                idlogru = cursor.fetchone()
                                if idlogru is not None:
                                    sql = "DELETE FROM sagest_logrubros WHERE rubro_id = %s" % (idlogru[0])
                                    cursor.execute(sql)

                                    sql = "DELETE FROM sagest_rubro WHERE id = %s" % (idru[0])
                                    cursor.execute(sql)
                                else:
                                    sql = "DELETE FROM sagest_rubro WHERE id = %s" % (idru[0])
                                    cursor.execute(sql)

                        if lead.contrato_set.filter(status=True).last().id and lead.contrato_set.filter(status=True).last().tablaamortizacion_set.all():
                            ct = lead.contrato_set.filter(status=True).last()
                            for t in lead.contrato_set.filter(status=True).last().tablaamortizacion_set.filter(status=True):
                                if Rubro.objects.filter(status=True, tablaamortizacionposgrado=t).exists():
                                    rub = Rubro.objects.filter(status=True, tablaamortizacionposgrado=t).order_by('id')[0]
                                    tab = TablaAmortizacion.objects.get(status=True, id=t.id)
                                    tab.status = False
                                    tab.save()
                                    log(u'Eliminó datos de amortizacion de: %s' % tab, request, "del")
                                    if not Pago.objects.filter(status=True, rubro=rub).exists():
                                        t.delete()
                                        log(u'Eliminó tabla de amortización de: %s' % lead, request, "del")
                                else:
                                    tab = TablaAmortizacion.objects.get(status=True, id=t.id)
                                    tab.status = False
                                    tab.save()
                                    log(u'Eliminó datos de amortizacion de: %s' % tab, request, "del")

                            tablaamortizacion = financiamiento.tablaamortizacioncohortemaestria(lead, datetime.now())
                            des = str(lead.cohortes.maestriaadmision) + ' - ' + str(lead.cohortes.descripcion)
                            desmatricula = 'MATRICULA DE POSTGRADO - %s' % des
                            desconvenio = ''
                            if lead.convenio:
                                if lead.convenio.aplicadescuento:
                                    desconvenio = 'CONVENIOS POSGRADOS - %s' % des
                            for t in tablaamortizacion:
                                cnombre = ''
                                if t[0] != '':
                                    if t[0] > financiamiento.maxnumcuota:
                                        cnombre = desconvenio
                                    else:
                                        cnombre = des
                                else:
                                    cnombre = desmatricula
                                amortizacion = TablaAmortizacion(
                                    contrato=ct,
                                    cuota=t[0] if t[0] != '' else 0,
                                    nombre=cnombre,
                                    valor=t[3],
                                    fecha=t[1] if t[1] != '' else hoy,
                                    fechavence=t[2] if t[2] != '' else lead.cohortes.fechavencerubro)
                                amortizacion.save(request)
                            log(u'registró tabla de amortización de %s' % (ct), request, "add")
                        log(u'Cambió el tipo de financiamiento al lead: %s' % lead, request, "edit")

                        contratopos = Contrato.objects.get(status=True, inscripcion=lead)

                        detalleevidencia = DetalleAprobacionContrato(contrato_id=contratopos.id, espagare=False,
                                                                     observacion='Cambio de tipo de modalidad de pago por diferido',
                                                                     persona=persona, estado_aprobacion=3, fecha_aprobacion=datetime.now(),
                                                                     archivocontrato=contratopos.archivocontrato)
                        detalleevidencia.save(request)

                        detalleevidencia = DetalleAprobacionContrato(contrato_id=contratopos.id, espagare=True,
                                                                     observacion='Cambio de tipo de modalidad de pago por diferido',
                                                                     persona=persona, estado_aprobacion=3, fecha_aprobacion=datetime.now(),
                                                                     archivocontrato=contratopos.archivopagare)
                        detalleevidencia.save(request)

                        contratopos.estado = 3
                        contratopos.estadopagare = 3
                        contratopos.save(request)

                return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editrubro':
            try:
                rubro = Rubro.objects.get(status=True, pk=int(request.POST['id']))
                f = EditarRubroMaestriaForm(request.POST)
                if f.is_valid():
                    rubro.nombre = f.cleaned_data['nombre']
                    rubro.cohortemaestria = f.cleaned_data['cohorte']
                    rubro.valor = int(f.cleaned_data['valor'])
                    rubro.valortotal = int(f.cleaned_data['valor'])
                    rubro.fechavence = f.cleaned_data['fecha']

                    if 'matricula' in request.POST:
                        rubro.admisionposgradotipo = 2
                    else:
                        rubro.admisionposgradotipo = 3
                    rubro.save(request)

                    cursor = connections['epunemi'].cursor()
                    sql = "UPDATE sagest_rubro SET nombre = '%s', fechavence = '%s', valor = '%s', valortotal = '%s', saldo = '%s' , totalunemi = '%s' , bloqueadopornovedad = '%s' WHERE sagest_rubro.status= true and sagest_rubro.id= %s" % (rubro.nombre, rubro.fechavence, rubro.valor, rubro.valor, rubro.valor, rubro.valor, False, rubro.idrubroepunemi)
                    cursor.execute(sql)
                    cursor.close()

                    log(u'Modificó el rubro: %s - %s' % (rubro, rubro.persona), request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delrubro':
            try:
                rubro = Rubro.objects.get(pk=request.POST['id'])

                if rubro.tiene_pagos() or rubro.bloqueado:
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar este rubro."})

                # if rubro.fechavence < datetime.now().date() and persona.id != 2570:
                #     return JsonResponse({"result": "bad", "mensaje": u"La fecha del rubro debe ser mayor o igual a la fecha actual para poder eliminarlo."})

                # qs_anterior = list(Rubro.objects.filter(pk=request.POST['id']).values())

                rubro.status = False
                rubro.save(request)
                #GUARDA AUDITORIA RUBRO
                # qs_nuevo = list(Rubro.objects.filter(pk=rubro.id).values())
                # salvaRubros(request, rubro, action,  qs_nuevo=qs_nuevo, qs_anterior=qs_anterior)
                #GUARDA AUDITORIA RUBRO
                if rubro.epunemi and rubro.idrubroepunemi>0:
                    cursor = connections['epunemi'].cursor()
                    sql = "UPDATE sagest_rubro SET status=false WHERE sagest_rubro.status=true and sagest_rubro.id="+str(rubro.idrubroepunemi)
                    cursor.execute(sql)
                    cursor.close()

                log(u'Elimino rubro: %s - %s' % (rubro, rubro.persona), request, "del")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad'})

        elif action == 'addcuota':
            try:
                f = AdicionarCuotaTablaAmortizacionForm(request.POST)
                if f.is_valid():
                    contrato = Contrato.objects.get(pk=int(request.POST['id']))
                    registros = contrato.tablaamortizacion_set.values_list('cuota', flat=True).filter(status=True)

                    if (int(f.cleaned_data['numerocuota'])) in registros:
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe el número de cuota: %s." % (int(f.cleaned_data['numerocuota']))})

                    cuota = TablaAmortizacion(
                        contrato=contrato,
                        cuota=int(f.cleaned_data['numerocuota']),
                        nombre=f.cleaned_data['nombre'],
                        valor=f.cleaned_data['valor'],
                        fecha=f.cleaned_data['inicio'],
                        fechavence=f.cleaned_data['fin']
                    )
                    cuota.save(request)

                    # Actualiza estado de modificacion de tabla de amortización
                    if not contrato.tablaamortizacionajustada:
                        contrato.tablaamortizacionajustada = True
                        contrato.save(request)

                    log(u'Adicionó una nueva cuota en la Tabla de amortización: %s ).' %(cuota), request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edittablacuota':
            try:
                datos = request.POST.getlist('id[]')
                cuota = TablaAmortizacion.objects.get(pk=int(datos[0]))
                contrato = Contrato.objects.get(pk=cuota.contrato.id)

                # Actualiza estado de modificacion de tabla de amortización
                if cuota.cuota != int(datos[1]) or cuota.nombre != str(datos[2]) or cuota.valor != Decimal(datos[3]) or cuota.fecha != datetime.strptime(datos[4], '%Y-%m-%d').date() or cuota.fechavence != datetime.strptime(datos[5], '%Y-%m-%d').date() and not contrato.tablaamortizacionajustada:
                    contrato.tablaamortizacionajustada = True
                    contrato.save(request)

                cuota.cuota = int(datos[1])
                cuota.nombre = str(datos[2])
                cuota.valor = Decimal(datos[3])
                cuota.fecha = datetime.strptime(datos[4], '%Y-%m-%d').date()
                cuota.fechavence = datetime.strptime(datos[5], '%Y-%m-%d').date()
                cuota.save(request)
                log(u'Modificó datos de la cuota %s - (Tabla de amortización ).' % (cuota), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcuota':
            try:
                cuota = TablaAmortizacion.objects.get(pk=int(request.POST['idcuota']))
                contrato = Contrato.objects.get(pk=cuota.contrato.id)
                f = AdicionarCuotaTablaAmortizacionForm(request.POST)

                if f.is_valid():
                    # Actualiza estado de modificacion de tabla de amortización
                    if cuota.cuota != int(f.cleaned_data['numerocuota']) or cuota.nombre != f.cleaned_data['nombre'] or cuota.valor != Decimal(f.cleaned_data['valor']) or cuota.fecha != f.cleaned_data['inicio'] or cuota.fechavence != f.cleaned_data['fin'] and not contrato.tablaamortizacionajustada:
                        contrato.tablaamortizacionajustada = True
                        contrato.save(request)

                    cuota.cuota = int(f.cleaned_data['numerocuota'])
                    cuota.nombre = f.cleaned_data['nombre']
                    cuota.valor = Decimal(f.cleaned_data['valor'])
                    cuota.fecha = f.cleaned_data['inicio']
                    cuota.fechavence = f.cleaned_data['fin']
                    cuota.save(request)
                    log(u'Modificó datos de la cuota %s - (Tabla de amortización ).' % (cuota), request, "edit")
                    return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delcuotaamortizacion':
            try:
                tabla = TablaAmortizacion.objects.get(pk=request.POST['id'])
                if not tabla.esta_enuso():
                    tabla.status=False
                    tabla.save(request)
                    log(u'Eliminó cuota: %s.' % (tabla), request, "del")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad'})

        elif action == 'addfinanciamientocohorte':
            try:
                with transaction.atomic():
                    form = ConfigFinanciamientoCohorteForm(request.POST)
                    if form.is_valid():
                        instance = ConfigFinanciamientoCohorte(descripcion=form.cleaned_data['descripcion'],
                                                               cohorte_id=request.POST['cohorte'],
                                                               valormatricula=form.cleaned_data['valormatricula'],
                                                               valorarancel =form.cleaned_data['valorarancel'],
                                                               valortotalprograma =form.cleaned_data['valortotalprograma'],
                                                               porcentajeminpagomatricula =form.cleaned_data['porcentajeminpagomatricula'],
                                                               maxnumcuota=form.cleaned_data['maxnumcuota'],
                                                               fecha=form.cleaned_data['fecha'],
                                                               )
                        instance.save(request)
                        log(u'Adicionó Config. Financiamiento Cohorte: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editfinanciamientocohorte':
            try:
                with transaction.atomic():
                    instance = ConfigFinanciamientoCohorte.objects.get(pk=request.POST['id'])
                    f = ConfigFinanciamientoCohorteForm(request.POST)
                    if f.is_valid():
                        instance.descripcion= f.cleaned_data['descripcion']
                        instance.valormatricula= f.cleaned_data['valormatricula']
                        instance.valorarancel= f.cleaned_data['valorarancel']
                        instance.valortotalprograma= f.cleaned_data['valortotalprograma']
                        instance.porcentajeminpagomatricula= f.cleaned_data['porcentajeminpagomatricula']
                        instance.maxnumcuota= f.cleaned_data['maxnumcuota']
                        instance.fecha= f.cleaned_data['fecha']
                        instance.save(request)
                        log(u'Editó Config. Financiamiento Cohorte: %s' % instance, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'delfinanciamientocohorte':
            try:
                info = ConfigFinanciamientoCohorte.objects.get(pk=request.POST['id'])
                info.status = False
                info.save(request)
                log(u'Eliminó Config. Financiamiento Cohorte %s' % info, request, "del")
                return JsonResponse({"result": 'ok', "mensaje": u"Tipo de financiamiento eliminado correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True,"error":True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'aprobarrequisitoevidencia':
            try:
                detalleevidencia_aux = DetalleEvidenciaRequisitosAspirante.objects.filter(evidencia_id=request.POST['idevidencia']).order_by('-id').first()
                detalleevidencia = DetalleEvidenciaRequisitosAspirante(evidencia=detalleevidencia_aux.evidencia,
                                                                       fecha=datetime.now().date(),
                                                                       persona=persona,
                                                                       estadorevision=1,
                                                                       observacion='',
                                                                       estado_aprobacion=request.POST['id_estado'],
                                                                       fecha_aprobacion=datetime.now(),
                                                                       observacion_aprobacion=request.POST[
                                                                           'id_observacion'], )
                #detalleevidencia.observacion_aprobacion = request.POST['id_observacion']
                #detalleevidencia.persona = persona
                #detalleevidencia.estado_aprobacion = request.POST['id_estado']
                #detalleevidencia.fecha_aprobacion = datetime.now()
                detalleevidencia.save(request)

                log(u'Actualizó observacion evidencia: %s' % (detalleevidencia), request, "add")

                cohorte = detalleevidencia.evidencia.inscripcioncohorte.cohortes
                inscripcioncohorte = detalleevidencia.evidencia.inscripcioncohorte

                if request.POST['id_estado'] == '3':
                    inscripcioncohorte.estadoformapago = 1
                    inscripcioncohorte.todosubidofi = False
                    inscripcioncohorte.tienerechazofi = True
                    inscripcioncohorte.save(request)

                bandera = 0
                idrequisitoscomer = ClaseRequisito.objects.filter(clasificacion=3).values_list('requisito__id', flat=True)

                if inscripcioncohorte.subirrequisitogarante:
                    for re in cohorte.requisitosmaestria_set.filter(status=True, requisito__id__in=idrequisitoscomer, obligatorio=True).exclude(requisito__id__in=[56, 57, 59]):
                        ingresoevidencias = re.detalle_requisitosmaestriacohorte(inscripcioncohorte)
                        if ingresoevidencias:
                            if not ingresoevidencias.ultima_evidencia().estado_aprobacion == 2:
                                bandera = 1
                        else:
                            bandera = 1
                    if bandera == 0:
                        # inscripcioncoohorte = InscripcionCohorte.objects.get(pk=request.POST['idinscripcioncohorte'])

                        inscripcioncohorte.estadoformapago = 2
                        inscripcioncohorte.save(request)

                        deta = DetalleAprobacionFormaPago(inscripcion_id=inscripcioncohorte.id,
                                                   estadoformapago=inscripcioncohorte.estadoformapago,
                                                   observacion='TODAS LAS EVIDENCIAS HAN SIDO APROBADAS',
                                                   persona=persona)
                        deta.save(request)

                        asunto = u"REQUISITOS DE FINANCIAMIENTO APROBADOS"
                        observacion = f'Se le comunica que los requisitos de financiamiento del admitido {inscripcioncohorte.inscripcionaspirante.persona} con cédula {inscripcioncohorte.inscripcionaspirante.persona.cedula} han sido aprobados. Por favor, dar seguimiento en la siguiente fase de aprobación de instrumentos legales.'
                        para = inscripcioncohorte.asesor.persona
                        perfiu = inscripcioncohorte.asesor.perfil_administrativo()

                        notificacion3(asunto, observacion, para, None,
                                      '/comercial?s=' + inscripcioncohorte.inscripcionaspirante.persona.cedula,
                                      inscripcioncohorte.pk, 1,
                                      'sga', InscripcionCohorte, perfiu, request)
                else:
                    for re in cohorte.requisitosmaestria_set.filter(status=True, requisito__id__in=idrequisitoscomer, requisito__tipopersona__id=1, obligatorio=True):
                        ingresoevidencias = re.detalle_requisitosmaestriacohorte(inscripcioncohorte)
                        if ingresoevidencias:
                            if not ingresoevidencias.ultima_evidencia().estado_aprobacion == 2:
                                bandera = 1
                        else:
                            bandera = 1
                    if bandera == 0:
                        # inscripcioncoohorte = InscripcionCohorte.objects.get(pk=request.POST['idinscripcioncohorte'])

                        inscripcioncohorte.estadoformapago = 2
                        inscripcioncohorte.save(request)

                        deta = DetalleAprobacionFormaPago(inscripcion_id=inscripcioncohorte.id,
                                                          estadoformapago=inscripcioncohorte.estadoformapago,
                                                          observacion='TODAS LAS EVIDENCIAS HAN SIDO APROBADAS',
                                                          persona=persona)
                        deta.save(request)

                        asunto = u"REQUISITOS DE FINANCIAMIENTO APROBADOS"
                        observacion = f'Se le comunica que los requisitos de financiamiento del admitido {inscripcioncohorte.inscripcionaspirante.persona} con cédula {inscripcioncohorte.inscripcionaspirante.persona.cedula} han sido aprobados. Por favor, dar seguimiento en la siguiente fase de aprobación de instrumentos legales.'
                        para = inscripcioncohorte.asesor.persona
                        perfiu = inscripcioncohorte.asesor.perfil_administrativo()

                        notificacion3(asunto, observacion, para, None,
                                      '/comercial?s=' + inscripcioncohorte.inscripcionaspirante.persona.cedula,
                                      inscripcioncohorte.pk, 1,
                                      'sga', InscripcionCohorte, perfiu, request)

                        log(u'Envio email aprobacion, financiamiento: %s' % (inscripcioncohorte), request, "add")
                        send_html_mail("Aprobado Comercialización - POSGRADO UNEMI.", "emails/registroaprobacionfinanciamiento.html",
                                       {'sistema': u'Comercialización - POSGRADO UNEMI', 'fecha': datetime.now().date(),
                                        'hora': datetime.now().time(), 't': miinstitucion(), 'inscripcioncohorte':inscripcioncohorte},
                                       inscripcioncohorte.inscripcionaspirante.persona.emailpersonal(), [],
                                       cuenta=variable_valor('CUENTAS_CORREOS')[16])
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar."})

        elif action == 'aprobarconvenioevidencia':
            try:
                from posgrado.models import EvidenciaRequisitoConvenio, DetalleEvidenciaRequisitoConvenio
                evidencia = EvidenciaRequisitoConvenio.objects.get(pk=request.POST['idevidencia'])
                detalleevidencia = DetalleEvidenciaRequisitoConvenio(evidenciarequisitoconvenio_id=request.POST['idevidencia'])
                detalleevidencia.save(request)
                detalleevidencia.observacion = request.POST['id_observacion']
                detalleevidencia.persona = persona
                detalleevidencia.estado_aprobacion = request.POST['id_estado']
                detalleevidencia.fecha_aprobacion = datetime.now()
                detalleevidencia.archivo = evidencia.archivo
                detalleevidencia.save(request)
                log(u'Actualizó observacion evidencia: %s' % (detalleevidencia), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar o rechazar evidencia. %s" % (ex)})

        elif action == 'aprobarcontratoevidencia':
            try:
                contra = Contrato.objects.get(pk=request.POST['idevidencia'])

                if request.POST['id_estado'] == '2':
                    if contra.inscripcion.formapagopac.id == 1:
                        if contra.inscripcion.genero_rubro_matricula() or contra.inscripcion.genero_rubro_programa():
                            if not contra.inscripcion.tiene_rubro_cuadrado():
                                return JsonResponse({"result": "no"})

                espagare = True if 'espagare' in request.POST else False
                detalleevidencia = DetalleAprobacionContrato(contrato_id=request.POST['idevidencia'], espagare=espagare)
                detalleevidencia.save(request)
                detalleevidencia.observacion = request.POST['id_observacion']
                detalleevidencia.persona = persona
                detalleevidencia.estado_aprobacion = request.POST['id_estado']
                detalleevidencia.fecha_aprobacion = datetime.now()
                detalleevidencia.archivocontrato = contra.archivocontrato
                detalleevidencia.save(request)

                contrato = Contrato.objects.get(pk=detalleevidencia.contrato.id)
                if espagare:
                    contrato.estadopagare = request.POST['id_estado']
                else:
                    contrato.estado = request.POST['id_estado']
                contrato.save(request)

                log(u'Actualizó observacion evidencia: %s' % (detalleevidencia), request, "add")

                # Para considerarlo como admitido y poder generar rubros y matricular
                if detalleevidencia.contrato.inscripcion.formapagopac.id == 1:
                    if detalleevidencia.estado_aprobacion == '2':
                        insc = InscripcionCohorte.objects.get(pk=detalleevidencia.contrato.inscripcion.id)
                        crear_inscripcion(request, insc)
                        if detalleevidencia.contrato.inscripcion.tipocobro == 1:
                            # insc = InscripcionCohorte.objects.get(pk=detalleevidencia.contrato.inscripcion.id)
                            if insc.genero_rubro_matricula():
                                insc.tipocobro = 2
                            else:
                                insc.tipocobro = 3
                            insc.save(request)
                            log(u'Actualizó tipo de cobro de: %s' % (insc), request, "edit")
                    else: #si estaba los docs aprobados y luego nuevamente lo rechaza
                        if not detalleevidencia.contrato.inscripcion.tipocobro == 1:
                            insc = InscripcionCohorte.objects.get(pk=detalleevidencia.contrato.inscripcion.id)
                            insc.tipocobro = 1
                            insc.save(request)
                            log(u'Actualizó tipo de cobro de: %s' % (insc), request, "edit")

                    if not contra.inscripcion.genero_rubro_matricula() and not contra.inscripcion.genero_rubro_programa():
                        if contrato.inscripcion.cohortes.tienecostomatricula:
                            if contrato.inscripcion.cohortes.valormatricula > 0 and contrato.inscripcion.cohortes.fechavencerubro and contrato.inscripcion.cohortes.fechainiordinaria and contrato.inscripcion.cohortes.fechafinordinaria and contrato.inscripcion.cohortes.fechainiextraordinaria and contrato.inscripcion.cohortes.fechafinextraordinaria and contrato.inscripcion.cohortes.valorprogramacertificado:
                                if not contrato.inscripcion.genero_rubro_matricula():
                                    valormatricula = contrato.inscripcion.cohortes.valormatricula
                                    integrante = InscripcionCohorte.objects.filter(pk=contrato.inscripcion.id, status=True).last()
                                    tiporubroarancel = TipoOtroRubro.objects.get(pk=2845)
                                    rubro = Rubro(tipo=tiporubroarancel,
                                                  persona=integrante.inscripcionaspirante.persona,
                                                  cohortemaestria=integrante.cohortes,
                                                  inscripcion=integrante,
                                                  relacionados=None,
                                                  nombre=tiporubroarancel.nombre + ' - ' + integrante.cohortes.maestriaadmision.descripcion + ' - ' + integrante.cohortes.descripcion,
                                                  cuota=1,
                                                  fecha=datetime.now().date(),
                                                  fechavence=integrante.cohortes.fechavencerubro,
                                                  valor=valormatricula,
                                                  iva_id=1,
                                                  valoriva=0,
                                                  valortotal=valormatricula,
                                                  saldo=valormatricula,
                                                  epunemi=True,
                                                  idrubroepunemi=0,
                                                  admisionposgradotipo=2,
                                                  cancelado=False)
                                    rubro.save(request)
                                    integrante.tipocobro = 2
                                    integrante.tipo_id = 2845
                                    integrante.save(request)
                                    log(u'Genero rubro por concepto matrícula : %s' % (integrante), request, "add")

                                    rubrosunemi = Rubro.objects.filter(status=True, inscripcion=integrante, epunemi = True, cancelado=False)

                                    # -------CREAR PERSONA EPUNEMI-------
                                    cursor = connections['epunemi'].cursor()
                                    sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.cedula, integrante.inscripcionaspirante.persona.cedula, integrante.inscripcionaspirante.persona.cedula)
                                    cursor.execute(sql)
                                    idalumno = cursor.fetchone()

                                    if idalumno is None:
                                        sql = """ INSERT INTO sga_persona (status, nombres, apellido1, apellido2, cedula, ruc, pasaporte,
                                                    nacimiento, tipopersona, sector, direccion,  direccion2,
                                                    num_direccion, telefono, telefono_conv, email, contribuyenteespecial,
                                                    anioresidencia, nacionalidad, ciudad, referencia, emailinst, identificacioninstitucion,
                                                    regitrocertificacion, libretamilitar, servidorcarrera, concursomeritos, telefonoextension,
                                                    tipocelular, periodosabatico, real, lgtbi, datosactualizados, confirmarextensiontelefonia,
                                                    acumuladecimo, acumulafondoreserva, representantelegal, inscripcioncurso, unemi,
                                                    idunemi)
                                                            VALUES(TRUE, '%s', '%s', '%s', '%s', '%s', '%s', '/%s/', %s, '%s', '%s', '%s', '%s', '%s', '%s', '%s', 
                                                            FALSE, 0, '', '', '', '', '', '', '', FALSE, FALSE, '', 0, FALSE, TRUE, FALSE, 0, FALSE, TRUE, FALSE, FALSE, 
                                                            FALSE, FALSE, 0); """ % (
                                            integrante.inscripcionaspirante.persona.nombres, integrante.inscripcionaspirante.persona.apellido1,
                                            integrante.inscripcionaspirante.persona.apellido2, integrante.inscripcionaspirante.persona.cedula,
                                            integrante.inscripcionaspirante.persona.ruc if integrante.inscripcionaspirante.persona.ruc else '',
                                            integrante.inscripcionaspirante.persona.pasaporte if integrante.inscripcionaspirante.persona.pasaporte else '',
                                            integrante.inscripcionaspirante.persona.nacimiento,
                                            integrante.inscripcionaspirante.persona.tipopersona if integrante.inscripcionaspirante.persona.tipopersona else 1,
                                            integrante.inscripcionaspirante.persona.sector if integrante.inscripcionaspirante.persona.sector else '',
                                            integrante.inscripcionaspirante.persona.direccion if integrante.inscripcionaspirante.persona.direccion else '',
                                            integrante.inscripcionaspirante.persona.direccion2 if integrante.inscripcionaspirante.persona.direccion2 else '',
                                            integrante.inscripcionaspirante.persona.num_direccion if integrante.inscripcionaspirante.persona.num_direccion else '',
                                            integrante.inscripcionaspirante.persona.telefono if integrante.inscripcionaspirante.persona.telefono else '',
                                            integrante.inscripcionaspirante.persona.telefono_conv if integrante.inscripcionaspirante.persona.telefono_conv else '',
                                            integrante.inscripcionaspirante.persona.email if integrante.inscripcionaspirante.persona.email else '')
                                        cursor.execute(sql)

                                        if integrante.inscripcionaspirante.persona.sexo:
                                            sql = """SELECT sexo.id FROM sga_sexo AS sexo WHERE sexo.id='%s'  AND sexo.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.sexo.id)
                                            cursor.execute(sql)
                                            sexo = cursor.fetchone()

                                            if sexo is not None:
                                                sql = """UPDATE sga_persona SET sexo_id='%s' WHERE cedula='%s'; """ % (sexo[0], integrante.inscripcionaspirante.persona.cedula)
                                                cursor.execute(sql)

                                        if integrante.inscripcionaspirante.persona.pais:
                                            sql = """SELECT pai.id FROM sga_pais AS pai WHERE pai.id='%s'  AND pai.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.pais.id)
                                            cursor.execute(sql)
                                            pais = cursor.fetchone()

                                            if pais is not None:
                                                sql = """UPDATE sga_persona SET pais_id='%s' WHERE cedula='%s'; """ % (pais[0], integrante.inscripcionaspirante.persona.cedula)
                                                cursor.execute(sql)

                                        if integrante.inscripcionaspirante.persona.parroquia:
                                            sql = """SELECT pa.id FROM sga_parroquia AS pa WHERE pa.id='%s'  AND pa.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.parroquia.id)
                                            cursor.execute(sql)
                                            parroquia = cursor.fetchone()

                                            if parroquia is not None:
                                                sql = """UPDATE sga_persona SET parroquia_id='%s' WHERE cedula='%s'; """ % (parroquia[0], integrante.inscripcionaspirante.persona.cedula)
                                                cursor.execute(sql)

                                        if integrante.inscripcionaspirante.persona.canton:
                                            sql = """SELECT ca.id FROM sga_canton AS ca WHERE ca.id='%s'  AND ca.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.canton.id)
                                            cursor.execute(sql)
                                            canton = cursor.fetchone()

                                            if canton is not None:
                                                sql = """UPDATE sga_persona SET canton_id='%s' WHERE cedula='%s'; """ % (canton[0], integrante.inscripcionaspirante.persona.cedula)
                                                cursor.execute(sql)

                                        if integrante.inscripcionaspirante.persona.provincia:
                                            sql = """SELECT pro.id FROM sga_provincia AS pro WHERE pro.id='%s'  AND pro.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.provincia.id)
                                            cursor.execute(sql)
                                            provincia = cursor.fetchone()

                                            if provincia is not None:
                                                sql = """UPDATE sga_persona SET provincia_id='%s' WHERE cedula='%s'; """ % (provincia[0], integrante.inscripcionaspirante.persona.cedula)
                                                cursor.execute(sql)

                                        #ID DE PERSONA EN EPUNEMI
                                        sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.cedula, integrante.inscripcionaspirante.persona.cedula, integrante.inscripcionaspirante.persona.cedula)
                                        cursor.execute(sql)
                                        idalumno = cursor.fetchone()
                                        alumnoepu = idalumno[0]
                                    else:
                                        alumnoepu = idalumno[0]

                                    for r in rubrosunemi:
                                        # Consulto el tipo otro rubro en epunemi
                                        sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (r.tipo.id)
                                        cursor.execute(sql)
                                        registro = cursor.fetchone()

                                        # Si existe
                                        if registro is not None:
                                            tipootrorubro = registro[0]
                                        else:
                                            # Debo crear ese tipo de rubro
                                            # Consulto centro de costo
                                            sql = """SELECT id FROM sagest_centrocosto WHERE status=True AND unemi=True AND tipo=%s;""" % (r.tipo.tiporubro)
                                            cursor.execute(sql)
                                            centrocosto = cursor.fetchone()
                                            idcentrocosto = centrocosto[0]

                                            # Consulto la cuenta contable
                                            cuentacontable = CuentaContable.objects.get(partida=r.tipo.partida, status=True)

                                            # Creo el tipo de rubro en epunemi
                                            sql = """ Insert Into sagest_tipootrorubro (status, nombre, partida_id, valor, interface, activo, ivaaplicado_id, nofactura, exportabanco, cuentacontable_id, centrocosto_id, tiporubro, idtipootrorubrounemi, unemi, es_especie, es_convalidacionconocimiento)
                                                                VALUES(TRUE, '%s', %s, %s, FALSE, TRUE, %s, FALSE, TRUE, %s, %s, 1, %s, TRUE, FALSE, FALSE); """ % (
                                                r.tipo.nombre, cuentacontable.partida.id, r.tipo.valor,
                                                r.tipo.ivaaplicado.id, cuentacontable.id, idcentrocosto,
                                                r.tipo.id)
                                            cursor.execute(sql)

                                            print(".:: Tipo de Rubro creado en EPUNEMI ::.")

                                            # Obtengo el id recién creado del tipo de rubro
                                            sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (r.tipo.id)
                                            cursor.execute(sql)
                                            registro = cursor.fetchone()
                                            tipootrorubro = registro[0]

                                        #pregunto si no existe rubro con ese id de unemi
                                        sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE; """ % (r.id)
                                        cursor.execute(sql)
                                        registrorubro = cursor.fetchone()

                                        if registrorubro is None:
                                            # Creo nuevo rubro en epunemi
                                            sql = """ INSERT INTO sagest_rubro (status, persona_id, nombre, cuota, tipocuota, fecha, fechavence,
                                                        valor, saldo, iva_id, valoriva, totalunemi, valortotal, cancelado, observacion, 
                                                        idrubrounemi, tipo_id, fecha_creacion, usuario_creacion_id, tienenotacredito, valornotacredito, 
                                                        valordescuento, anulado, compromisopago, refinanciado, bloqueado, bloqueadopornovedad, 
                                                        titularcambiado, coactiva) 
                                                      VALUES (TRUE, %s, '%s', %s, %s, '/%s/', '/%s/', %s, %s, %s, %s, %s, %s, %s, '%s', %s, %s, NOW(), 1, FALSE, 0, 0, FALSE, %s, %s, %s, FALSE, FALSE, %s); """ \
                                                  % (alumnoepu, r.nombre, r.cuota, r.tipocuota, r.fecha, r.fechavence, r.saldo, r.saldo, r.iva_id, r.valoriva, r.valor,
                                                     r.valortotal, r.cancelado, r.observacion, r.id, tipootrorubro, r.compromisopago if r.compromisopago else 0,
                                                     r.refinanciado, r.bloqueado, r.coactiva)
                                            cursor.execute(sql)

                                            sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND anulado=FALSE; """ % (r.id)
                                            cursor.execute(sql)
                                            registro = cursor.fetchone()
                                            rubroepunemi = registro[0]

                                            r.idrubroepunemi = rubroepunemi
                                            r.save()

                                            print(".:: Rubro creado en EPUNEMI ::.")
                                        else:
                                            sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND cancelado=FALSE; """ % (r.id)
                                            cursor.execute(sql)
                                            rubronoc = cursor.fetchone()

                                            if rubronoc is not None:
                                                sql = """SELECT id FROM sagest_pago WHERE rubro_id=%s; """ % (registrorubro[0])
                                                cursor.execute(sql)
                                                tienerubropagos = cursor.fetchone()

                                                if tienerubropagos is not None:
                                                    pass
                                                else:
                                                    sql = """UPDATE sagest_rubro SET nombre = '%s', fecha = '/%s/', fechavence = '/%s/',
                                                           valor = %s, saldo = %s, iva_id = %s, valoriva = %s, totalunemi = %s,
                                                           valortotal = %s, observacion = '%s', tipo_id = %s
                                                           WHERE id=%s; """ % (r.nombre, r.fecha, r.fechavence, r.saldo, r.saldo, r.iva_id,
                                                                               r.valoriva, r.valor, r.valortotal, r.observacion, tipootrorubro,
                                                                               registrorubro[0])
                                                    cursor.execute(sql)
                                                r.idrubroepunemi = registrorubro[0]
                                                r.save()
                                # else:
                                #     if not contrato.inscripcion.tiene_rubro_cuadrado():
                                #         return JsonResponse({"result": "no"})

                        elif contrato.inscripcion.cohortes.tienecostototal:
                            if contrato.inscripcion.cohortes.valorprograma > 0 and contrato.inscripcion.cohortes.tiporubro and contrato.inscripcion.cohortes.fechavencerubro and contrato.inscripcion.cohortes.fechainiordinaria and contrato.inscripcion.cohortes.fechafinordinaria and contrato.inscripcion.cohortes.fechainiextraordinaria and contrato.inscripcion.cohortes.fechafinextraordinaria and contrato.inscripcion.cohortes.valorprogramacertificado:
                                if not contrato.inscripcion.genero_rubro_programa():
                                    valorprograma = contrato.inscripcion.cohortes.valorprograma
                                    integrante = InscripcionCohorte.objects.filter(pk=contrato.inscripcion.id, status=True).last()
                                    tiporubroarancel = TipoOtroRubro.objects.get(pk=integrante.cohortes.tiporubro.id)
                                    valordescuento = None
                                    if integrante.convenio:
                                        if integrante.convenio.aplicadescuento:
                                            valordescuento= ((valorprograma*integrante.convenio.porcentajedescuento)/100)
                                            valorprograma = valorprograma - valordescuento

                                    rubro = Rubro(tipo=tiporubroarancel,
                                                  persona=integrante.inscripcionaspirante.persona,
                                                  cohortemaestria=integrante.cohortes,
                                                  inscripcion=integrante,
                                                  relacionados=None,
                                                  nombre=tiporubroarancel.nombre + ' - ' + integrante.cohortes.maestriaadmision.descripcion + ' - ' + integrante.cohortes.descripcion,
                                                  cuota=1,
                                                  fecha=datetime.now().date(),
                                                  fechavence=integrante.cohortes.fechavencerubro,
                                                  valor=valorprograma,
                                                  iva_id=1,
                                                  valoriva=0,
                                                  valortotal=valorprograma,
                                                  saldo=valorprograma,
                                                  epunemi=True,
                                                  idrubroepunemi=0,
                                                  admisionposgradotipo=3,
                                                  cancelado=False)
                                    rubro.save(request)
                                    integrante.tipocobro = 3
                                    integrante.tipo = tiporubroarancel
                                    integrante.save(request)
                                    log(u'Genero rubro por concepto programa maestría : %s' % (integrante), request, "add")

                                    if integrante.convenio:
                                        if integrante.convenio.aplicadescuento:
                                            tiporubroconvenio = TipoOtroRubro.objects.get(pk=3634) #Tipo Rubro CONVENIOS POSGRADOS
                                            rubro = Rubro(tipo=tiporubroconvenio,
                                                          persona=integrante.inscripcionaspirante.persona,
                                                          cohortemaestria=integrante.cohortes,
                                                          inscripcion=integrante,
                                                          relacionados=None,
                                                          nombre=tiporubroconvenio.nombre + ' - ' + integrante.cohortes.maestriaadmision.descripcion + ' - ' + integrante.cohortes.descripcion,
                                                          cuota=1,
                                                          fecha=datetime.now().date(),
                                                          fechavence=integrante.cohortes.fechavencerubro,
                                                          valor=valordescuento,
                                                          iva_id=1,
                                                          valoriva=0,
                                                          valortotal=valordescuento,
                                                          saldo=valordescuento,
                                                          epunemi=True,
                                                          idrubroepunemi=0,
                                                          admisionposgradotipo=3,
                                                          cancelado=False)
                                            rubro.save(request)
                                            log(u'Genero rubro por concepto convenio programa maestría : %s' % (integrante),
                                                request, "add")


                                    rubrosunemi = Rubro.objects.filter(status=True, inscripcion=integrante, epunemi = True, cancelado=False)

                                    # -------CREAR PERSONA EPUNEMI-------
                                    cursor = connections['epunemi'].cursor()
                                    sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.cedula, integrante.inscripcionaspirante.persona.cedula, integrante.inscripcionaspirante.persona.cedula)
                                    cursor.execute(sql)
                                    idalumno = cursor.fetchone()

                                    if idalumno is None:
                                        sql = """ INSERT INTO sga_persona (status, nombres, apellido1, apellido2, cedula, ruc, pasaporte,
                                                    nacimiento, tipopersona, sector, direccion,  direccion2,
                                                    num_direccion, telefono, telefono_conv, email, contribuyenteespecial,
                                                    anioresidencia, nacionalidad, ciudad, referencia, emailinst, identificacioninstitucion,
                                                    regitrocertificacion, libretamilitar, servidorcarrera, concursomeritos, telefonoextension,
                                                    tipocelular, periodosabatico, real, lgtbi, datosactualizados, confirmarextensiontelefonia,
                                                    acumuladecimo, acumulafondoreserva, representantelegal, inscripcioncurso, unemi,
                                                    idunemi)
                                                            VALUES(TRUE, '%s', '%s', '%s', '%s', '%s', '%s', '/%s/', %s, '%s', '%s', '%s', '%s', '%s', '%s', '%s', 
                                                            FALSE, 0, '', '', '', '', '', '', '', FALSE, FALSE, '', 0, FALSE, TRUE, FALSE, 0, FALSE, TRUE, FALSE, FALSE, 
                                                            FALSE, FALSE, 0); """ % (
                                            integrante.inscripcionaspirante.persona.nombres, integrante.inscripcionaspirante.persona.apellido1,
                                            integrante.inscripcionaspirante.persona.apellido2, integrante.inscripcionaspirante.persona.cedula,
                                            integrante.inscripcionaspirante.persona.ruc if integrante.inscripcionaspirante.persona.ruc else '',
                                            integrante.inscripcionaspirante.persona.pasaporte if integrante.inscripcionaspirante.persona.pasaporte else '',
                                            integrante.inscripcionaspirante.persona.nacimiento,
                                            integrante.inscripcionaspirante.persona.tipopersona if integrante.inscripcionaspirante.persona.tipopersona else 1,
                                            integrante.inscripcionaspirante.persona.sector if integrante.inscripcionaspirante.persona.sector else '',
                                            integrante.inscripcionaspirante.persona.direccion if integrante.inscripcionaspirante.persona.direccion else '',
                                            integrante.inscripcionaspirante.persona.direccion2 if integrante.inscripcionaspirante.persona.direccion2 else '',
                                            integrante.inscripcionaspirante.persona.num_direccion if integrante.inscripcionaspirante.persona.num_direccion else '',
                                            integrante.inscripcionaspirante.persona.telefono if integrante.inscripcionaspirante.persona.telefono else '',
                                            integrante.inscripcionaspirante.persona.telefono_conv if integrante.inscripcionaspirante.persona.telefono_conv else '',
                                            integrante.inscripcionaspirante.persona.email if integrante.inscripcionaspirante.persona.email else '')
                                        cursor.execute(sql)

                                        if integrante.inscripcionaspirante.persona.sexo:
                                            sql = """SELECT sexo.id FROM sga_sexo AS sexo WHERE sexo.id='%s'  AND sexo.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.sexo.id)
                                            cursor.execute(sql)
                                            sexo = cursor.fetchone()

                                            if sexo is not None:
                                                sql = """UPDATE sga_persona SET sexo_id='%s' WHERE cedula='%s'; """ % (sexo[0], integrante.inscripcionaspirante.persona.cedula)
                                                cursor.execute(sql)

                                        if integrante.inscripcionaspirante.persona.pais:
                                            sql = """SELECT pai.id FROM sga_pais AS pai WHERE pai.id='%s'  AND pai.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.pais.id)
                                            cursor.execute(sql)
                                            pais = cursor.fetchone()

                                            if pais is not None:
                                                sql = """UPDATE sga_persona SET pais_id='%s' WHERE cedula='%s'; """ % (pais[0], integrante.inscripcionaspirante.persona.cedula)
                                                cursor.execute(sql)

                                        if integrante.inscripcionaspirante.persona.parroquia:
                                            sql = """SELECT pa.id FROM sga_parroquia AS pa WHERE pa.id='%s'  AND pa.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.parroquia.id)
                                            cursor.execute(sql)
                                            parroquia = cursor.fetchone()

                                            if parroquia is not None:
                                                sql = """UPDATE sga_persona SET parroquia_id='%s' WHERE cedula='%s'; """ % (parroquia[0], integrante.inscripcionaspirante.persona.cedula)
                                                cursor.execute(sql)

                                        if integrante.inscripcionaspirante.persona.canton:
                                            sql = """SELECT ca.id FROM sga_canton AS ca WHERE ca.id='%s'  AND ca.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.canton.id)
                                            cursor.execute(sql)
                                            canton = cursor.fetchone()

                                            if canton is not None:
                                                sql = """UPDATE sga_persona SET canton_id='%s' WHERE cedula='%s'; """ % (canton[0], integrante.inscripcionaspirante.persona.cedula)
                                                cursor.execute(sql)

                                        if integrante.inscripcionaspirante.persona.provincia:
                                            sql = """SELECT pro.id FROM sga_provincia AS pro WHERE pro.id='%s'  AND pro.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.provincia.id)
                                            cursor.execute(sql)
                                            provincia = cursor.fetchone()

                                            if provincia is not None:
                                                sql = """UPDATE sga_persona SET provincia_id='%s' WHERE cedula='%s'; """ % (provincia[0], integrante.inscripcionaspirante.persona.cedula)
                                                cursor.execute(sql)

                                        #ID DE PERSONA EN EPUNEMI
                                        sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (integrante.inscripcionaspirante.persona.cedula, integrante.inscripcionaspirante.persona.cedula, integrante.inscripcionaspirante.persona.cedula)
                                        cursor.execute(sql)
                                        idalumno = cursor.fetchone()
                                        alumnoepu = idalumno[0]
                                    else:
                                        alumnoepu = idalumno[0]

                                    for r in rubrosunemi:
                                        # Consulto el tipo otro rubro en epunemi
                                        sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (r.tipo.id)
                                        cursor.execute(sql)
                                        registro = cursor.fetchone()

                                        # Si existe
                                        if registro is not None:
                                            tipootrorubro = registro[0]
                                        else:
                                            # Debo crear ese tipo de rubro
                                            # Consulto centro de costo
                                            sql = """SELECT id FROM sagest_centrocosto WHERE status=True AND unemi=True AND tipo=%s;""" % (r.tipo.tiporubro)
                                            cursor.execute(sql)
                                            centrocosto = cursor.fetchone()
                                            idcentrocosto = centrocosto[0]

                                            # Consulto la cuenta contable
                                            cuentacontable = CuentaContable.objects.get(partida=r.tipo.partida, status=True)

                                            # Creo el tipo de rubro en epunemi
                                            sql = """ Insert Into sagest_tipootrorubro (status, nombre, partida_id, valor, interface, activo, ivaaplicado_id, nofactura, exportabanco, cuentacontable_id, centrocosto_id, tiporubro, idtipootrorubrounemi, unemi, es_especie, es_convalidacionconocimiento)
                                                                VALUES(TRUE, '%s', %s, %s, FALSE, TRUE, %s, FALSE, TRUE, %s, %s, 1, %s, TRUE, FALSE, FALSE); """ % (
                                                r.tipo.nombre, cuentacontable.partida.id, r.tipo.valor,
                                                r.tipo.ivaaplicado.id, cuentacontable.id, idcentrocosto,
                                                r.tipo.id)
                                            cursor.execute(sql)

                                            print(".:: Tipo de Rubro creado en EPUNEMI ::.")

                                            # Obtengo el id recién creado del tipo de rubro
                                            sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (r.tipo.id)
                                            cursor.execute(sql)
                                            registro = cursor.fetchone()
                                            tipootrorubro = registro[0]

                                        #pregunto si no existe rubro con ese id de unemi
                                        sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE; """ % (r.id)
                                        cursor.execute(sql)
                                        registrorubro = cursor.fetchone()

                                        if registrorubro is None:
                                            # Creo nuevo rubro en epunemi
                                            sql = """ INSERT INTO sagest_rubro (status, persona_id, nombre, cuota, tipocuota, fecha, fechavence,
                                                        valor, saldo, iva_id, valoriva, totalunemi, valortotal, cancelado, observacion, 
                                                        idrubrounemi, tipo_id, fecha_creacion, usuario_creacion_id, tienenotacredito, valornotacredito, 
                                                        valordescuento, anulado, compromisopago, refinanciado, bloqueado, bloqueadopornovedad, 
                                                        titularcambiado, coactiva) 
                                                      VALUES (TRUE, %s, '%s', %s, %s, '/%s/', '/%s/', %s, %s, %s, %s, %s, %s, %s, '%s', %s, %s, NOW(), 1, FALSE, 0, 0, FALSE, %s, %s, %s, FALSE, FALSE, %s); """ \
                                                  % (alumnoepu, r.nombre, r.cuota, r.tipocuota, r.fecha, r.fechavence, r.saldo, r.saldo, r.iva_id, r.valoriva, r.valor,
                                                     r.valortotal, r.cancelado, r.observacion, r.id, tipootrorubro, r.compromisopago if r.compromisopago else 0,
                                                     r.refinanciado, r.bloqueado, r.coactiva)
                                            cursor.execute(sql)

                                            sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND anulado=FALSE; """ % (r.id)
                                            cursor.execute(sql)
                                            registro = cursor.fetchone()
                                            rubroepunemi = registro[0]

                                            r.idrubroepunemi = rubroepunemi
                                            r.save()

                                            print(".:: Rubro creado en EPUNEMI ::.")
                                        else:
                                            sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND cancelado=FALSE; """ % (r.id)
                                            cursor.execute(sql)
                                            rubronoc = cursor.fetchone()

                                            if rubronoc is not None:
                                                sql = """SELECT id FROM sagest_pago WHERE rubro_id=%s; """ % (registrorubro[0])
                                                cursor.execute(sql)
                                                tienerubropagos = cursor.fetchone()

                                                if tienerubropagos is not None:
                                                    pass
                                                else:
                                                    sql = """UPDATE sagest_rubro SET nombre = '%s', fecha = '/%s/', fechavence = '/%s/',
                                                       valor = %s, saldo = %s, iva_id = %s, valoriva = %s, totalunemi = %s,
                                                       valortotal = %s, observacion = '%s', tipo_id = %s
                                                       WHERE id=%s; """ % (r.nombre, r.fecha, r.fechavence, r.saldo, r.saldo, r.iva_id,
                                                                           r.valoriva, r.valor, r.valortotal, r.observacion, tipootrorubro,
                                                                           registrorubro[0])
                                                    cursor.execute(sql)
                                                r.idrubroepunemi = registrorubro[0]
                                                r.save()

                if detalleevidencia.contrato.inscripcion.formapagopac.id == 2:
                    if detalleevidencia.espagare and detalleevidencia.contrato.ultima_evidencia_aspirante() and detalleevidencia.contrato.ultima_evidencia_aspirante().estado_aprobacion == 2 or not detalleevidencia.espagare and detalleevidencia.contrato.ultima_evidencia_aspirantepagare() and detalleevidencia.contrato.ultima_evidencia_aspirantepagare().estado_aprobacion == 2:
                        if detalleevidencia.estado_aprobacion == '2':
                            insc = InscripcionCohorte.objects.get(pk=detalleevidencia.contrato.inscripcion.id)
                            crear_inscripcion(request, insc)
                            if detalleevidencia.contrato.inscripcion.tipocobro == 1:
                                # insc = InscripcionCohorte.objects.get(pk=detalleevidencia.contrato.inscripcion.id)
                                insc.tipocobro = 2
                                insc.save(request)
                                log(u'Actualizó tipo de cobro de: %s' % (insc), request, "edit")
                        else: #si estaba los docs aprobados y luego nuevamente lo rechaza
                            if not detalleevidencia.contrato.inscripcion.tipocobro == 1:
                                insc = InscripcionCohorte.objects.get(pk=detalleevidencia.contrato.inscripcion.id)
                                insc.tipocobro = 1
                                insc.save(request)
                                log(u'Actualizó tipo de cobro de: %s' % (insc), request, "edit")

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar o rechazar evidencia. %s"%(ex)})

        elif action == 'cargarcontratopago':
            try:
                hayarchivos = False
                if 'archivo' in request.FILES:
                    hayarchivos = True
                    descripcionarchivo = 'Contrato de pago'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivo'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar un archivo (Contrato)."})

                f = ContratoPagoMaestriaForm(request.POST, request.FILES)
                if f.is_valid():
                    if hayarchivos:
                        contratopago = request.FILES['archivo']
                        contratopago._name = generar_nombre("contratopago", contratopago._name)
                        insc = InscripcionCohorte.objects.get(pk=int(encrypt(request.POST['id'])))
                        if Contrato.objects.filter(status=True, inscripcion=insc, inscripcion__status=True).exists():
                            contrato = Contrato.objects.get(status=True, inscripcion=insc, inscripcion__status=True)
                            contrato.fechacontrato = hoy
                            contrato.formapago_id = int(request.POST['fpago'])
                            contrato.estado = 1
                            contrato.archivocontrato = contratopago
                            contrato.observacion = request.POST['observacion']
                            if contrato.contratolegalizado:
                               contrato.contratolegalizado = False
                            if contrato.respaldoarchivocontrato:
                               contrato.respaldoarchivocontrato = None
                            contrato.save(request)
                            log(u'Adicionó Contrato de : %s' % (insc), request, "edit")

                            detalle = DetalleAprobacionContrato(contrato=contrato,
                                                                  estado_aprobacion=1,
                                                                  observacion=request.POST['observacion'],
                                                                  archivocontrato=contratopago)
                            detalle.save(request)
                            return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar contrato."})

        elif action == 'cargarcontratopagoase':
            try:
                hayarchivos = False
                if 'archivo' in request.FILES:
                    hayarchivos = True
                    descripcionarchivo = 'Contrato de pago'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivo'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar un archivo (Contrato)."})

                f = ContratoPagoMaestriaForm(request.POST, request.FILES)
                if f.is_valid():
                    if hayarchivos:
                        contratopago = request.FILES['archivo']
                        contratopago._name = generar_nombre("contratopago", contratopago._name)
                        insc = InscripcionCohorte.objects.get(pk=int(encrypt(request.POST['id'])))
                        if Contrato.objects.filter(status=True, inscripcion=insc, inscripcion__status=True).exists():
                            contrato = Contrato.objects.get(status=True, inscripcion=insc, inscripcion__status=True)
                            contrato.fechacontrato = hoy
                            contrato.formapago_id = int(request.POST['fpago'])
                            contrato.estado = 1
                            contrato.archivocontrato = contratopago
                            contrato.observacion = request.POST['observacion']
                            if contrato.contratolegalizado:
                               contrato.contratolegalizado = False
                            if contrato.respaldoarchivocontrato:
                               contrato.respaldoarchivocontrato = None
                            contrato.save(request)
                            log(u'Adicionó Contrato de : %s' % (insc), request, "edit")

                            detalle = DetalleAprobacionContrato(contrato=contrato,
                                                                  estado_aprobacion=1,
                                                                  observacion=request.POST['observacion'],
                                                                  archivocontrato=contratopago)
                            detalle.save(request)
                            return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar contrato."})

        elif action == 'cargarpagareaspirantemaestriaase':
            try:
                hayarchivos = False
                if 'archivo' in request.FILES:
                    hayarchivos = True
                    descripcionarchivo = 'Pagaré del aspirante'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivo'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar un archivo (Pagaré)."})

                f = ContratoPagoMaestriaForm(request.POST, request.FILES)
                if f.is_valid():
                    if hayarchivos:
                        pagare = request.FILES['archivo']
                        pagare._name = generar_nombre("pagareaspirantemaestriafirmado", pagare._name)
                        insc = InscripcionCohorte.objects.get(pk=int(encrypt(request.POST['id'])))
                        if Contrato.objects.filter(status=True, inscripcion=insc).exists():
                            contrato = Contrato.objects.get(status=True, inscripcion=insc)
                            contrato.fechapagare = hoy
                            contrato.estadopagare = 1
                            contrato.archivopagare = pagare
                            contrato.observacionpagare = request.POST['observacion']
                            contrato.save(request)
                            log(u'Adicionó pagaré de : %s' % (insc), request, "edit")

                            detalle = DetalleAprobacionContrato(contrato=contrato,
                                                                  estado_aprobacion=1,
                                                                  observacion='Nuevo archivo pagaré',
                                                                  espagare=True)
                            detalle.save(request)
                            return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar pagaré."})

        elif action == 'cargarrequisitoconvenio':
            try:
                from posgrado.models import EvidenciaRequisitoConvenio, DetalleEvidenciaRequisitoConvenio
                from posgrado.forms import RequisitoConvenioAspiranteForm
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})

                f = RequisitoConvenioAspiranteForm(request.POST, request.FILES)
                if f.is_valid():
                    insc = InscripcionCohorte.objects.get(pk=int(encrypt(request.POST['id'])))
                    archivoconvenio = request.FILES['archivo']
                    archivoconvenio._name = generar_nombre("requisitoconvenio", archivoconvenio._name)
                    if EvidenciaRequisitoConvenio.objects.filter(inscripcion = insc, convenio=insc.convenio, status=True).exists():
                        evidencia = EvidenciaRequisitoConvenio.objects.filter(inscripcion = insc, convenio=insc.convenio, status =True).last()
                        evidencia.archivo = archivoconvenio
                        evidencia.save(request)
                    else:
                        evidencia = EvidenciaRequisitoConvenio(inscripcion = insc, convenio = insc.convenio, archivo = archivoconvenio)
                        evidencia.save(request)
                    detalle = DetalleEvidenciaRequisitoConvenio(evidenciarequisitoconvenio=evidencia,
                                                                  estado_aprobacion=1,
                                                                  archivo=archivoconvenio,
                                                                  observacion='Nuevo archivo requisito convenio')
                    detalle.save(request)
                    log(u'Adicionó requisito convenio de : %s' % (insc), request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error al guardar requisito: {ex.__str__()}"})

        elif action == 'cargarpagareaspirantemaestria':
            try:
                hayarchivos = False
                if 'archivo' in request.FILES:
                    hayarchivos = True
                    descripcionarchivo = 'Pagaré del aspirante'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivo'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar un archivo (Pagaré)."})

                f = ContratoPagoMaestriaForm(request.POST, request.FILES)
                if f.is_valid():
                    if hayarchivos:
                        pagare = request.FILES['archivo']
                        pagare._name = generar_nombre("pagareaspirantemaestriafirmado", pagare._name)
                        insc = InscripcionCohorte.objects.get(pk=int(encrypt(request.POST['id'])))
                        if Contrato.objects.filter(status=True, inscripcion=insc).exists():
                            contrato = Contrato.objects.get(status=True, inscripcion=insc)
                            contrato.fechapagare = hoy
                            contrato.estadopagare = 1
                            contrato.archivopagare = pagare
                            contrato.observacionpagare = request.POST['observacion']
                            contrato.save(request)
                            log(u'Adicionó pagaré de : %s' % (insc), request, "edit")

                            detalle = DetalleAprobacionContrato(contrato=contrato,
                                                                  estado_aprobacion=1,
                                                                  observacion='Nuevo archivo pagaré',
                                                                  espagare=True)
                            detalle.save(request)
                            return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar pagaré."})

        elif action == 'cargaroficio':
            try:
                hayarchivos = False
                if 'archivo' in request.FILES:
                    hayarchivos = True
                    descripcionarchivo = 'Oficio de terminación de contrato'
                    resp = validar_archivo(descripcionarchivo, request.FILES['archivo'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar un archivo (Pagaré)."})

                f = OficioTerminacionContratoForm(request.POST, request.FILES)
                if f.is_valid():
                    if hayarchivos:
                        oficio = request.FILES['archivo']
                        insc = InscripcionCohorte.objects.get(pk=int(encrypt(request.POST['id'])))
                        contrato = Contrato.objects.get(status=True, inscripcion=insc)
                        contrato.archivooficio = oficio
                        contrato.estado = 4
                        contrato.motivo_terminacion = f.cleaned_data['motivo']
                        contrato.save(request)
                        log(u'Subió oficio de intención de terminación de contrato de: %s' % (insc), request, "edit")

                        detalle = DetalleAprobacionContrato(contrato=contrato,
                                                            estado_aprobacion=4,
                                                            fecha_aprobacion=datetime.now(),
                                                            observacion=f'Su oficio ha subido correctamente por {insc.asesor.persona}.',
                                                            archivocontrato=contrato.archivooficio,
                                                            persona=persona,
                                                            esoficio=True,
                                                            motivo_terminacion=contrato.motivo_terminacion)
                        detalle.save(request)
                        return JsonResponse({"result": False}, safe=False)
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar pagaré."})

        elif action == 'pdfpagareprograma':
            try:
                numpagare = 0
                idins = request.POST['idins']
                idconfig = request.POST['idconfig']
                ct = registro = Contrato.objects.filter(status=True, inscripcion__id=idins).first()
                secuenciacp = secuencia_contratopagare(request, datetime.now().year)
                if not registro or not registro.numeropagare:
                    secuenciacp.secuenciapagare += 1
                    secuenciacp.save(request)
                    if Contrato.objects.filter(status=True, numeropagare=secuenciacp.secuenciapagare, fechapagare__year=secuenciacp.anioejercicio.anioejercicio).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Error al generar el pagaré, intente nuevamente"})
                    else:
                        if Contrato.objects.filter(status=True, inscripcion_id=idins).exists():
                            ct = Contrato.objects.filter(inscripcion_id=idins, status=True, ).last()
                            ct.numeropagare = secuenciacp.secuenciapagare
                            ct.save(request)
                            log(u'Editó número pagaré: %s' % (ct), request, "add")
                        else:
                            ct = Contrato(inscripcion_id=idins, numeropagare=secuenciacp.secuenciapagare)
                            ct.save(request)
                            log(u'Adicionó número pagaré: %s' % (ct), request, "add")
                        numpagare = ct.numeropagare
                else:
                    numpagare = Contrato.objects.filter(status=True, inscripcion__id=idins).last().numeropagare

                qrresult = pagareaspirantemae(idins, idconfig, numpagare)
                if qrresult:
                    if not ct.tablaamortizacion_set.values('id').filter(status=True).exists():
                        financiamiento = ConfigFinanciamientoCohorte.objects.get(pk=idconfig)
                        tablaamortizacion = financiamiento.tablaamortizacioncohortemaestria(idins, datetime.now())
                        des = str(ct.inscripcion.cohortes.maestriaadmision) + ' - ' + str(ct.inscripcion.cohortes.descripcion)
                        desmatricula = 'MATRICULA DE POSTGRADO - %s' % des
                        desconvenio = ''
                        if ct.inscripcion.convenio:
                            if ct.inscripcion.convenio.aplicadescuento:
                                desconvenio = 'CONVENIOS POSGRADOS - %s' % des
                        for t in tablaamortizacion:
                            # if t[0] != '':
                            cnombre = ''
                            if t[0] != '':
                                if t[0]>financiamiento.maxnumcuota:
                                    cnombre = desconvenio
                                else:
                                    cnombre = des
                            else:
                                cnombre = desmatricula

                            amortizacion = TablaAmortizacion(
                                contrato=ct,
                                cuota=t[0] if t[0] != '' else 0,
                                nombre=cnombre,
                                valor=t[3],
                                fecha=t[1] if t[1] != '' else hoy,
                                fechavence=t[2] if t[2] != '' else ct.inscripcion.cohortes.fechavencerubro)
                            amortizacion.save(request)

                        # des = str(ct.inscripcion.cohortes)
                        # for t in tablaamortizacion:
                        #     if t[0] != '':
                        #         amortizacion = TablaAmortizacion(
                        #             contrato=ct,
                        #             cuota=t[0],
                        #             nombre=des,
                        #             valor=t[3],
                        #             fecha=t[1],
                        #             fechavence=t[2])
                        #         amortizacion.save(request)
                        log(u'registró tabla de amortización de %s' % (ct), request, "add")
                return JsonResponse({"result": "ok", 'url': qrresult})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al descargar pagaré."})

        elif action == 'resetear':
            try:
                per = Persona.objects.get(pk=request.POST['id'])
                if not per.emailinst:
                    per.emailinst = per.usuario.username+'@unemi.edu.ec'
                    per.save(request)
                resetear_clave(per)
                log(u'Reseteo clave de la persona del modulo de comercialización: %s' % per, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editgarantepagomaestria':
            try:
                insc = InscripcionCohorte.objects.get(pk=request.POST['id'])
                f = GarantePagoMaestriaForm(request.POST)
                if f.is_valid():
                    garante = GarantePagoMaestria.objects.get(pk=request.POST['idg'])
                    garante.cedula = f.cleaned_data['cedula']
                    garante.nombres = f.cleaned_data['nombres']
                    garante.apellido1 = f.cleaned_data['apellido1']
                    garante.apellido2 = f.cleaned_data['apellido2']
                    garante.genero = f.cleaned_data['genero']
                    garante.telefono = f.cleaned_data['telefono']
                    garante.email = f.cleaned_data['email']
                    garante.direccion = f.cleaned_data['direccion']
                    garante.save(request)
                    log(u'Editó garante de pago del aspirante %s' % (insc), request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError("Error en el formulario.")
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Error al editar garante: %s." % (ex)}, safe=False)

        elif action == 'pdfcertificadototalprograma':
            try:
                qrresult = certificadoadmtidoprograma(request.POST['idins'])
                return JsonResponse({"result": "ok", 'url': qrresult})
            except Exception as ex:
                transaction.set_rollback(True)
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                print(f'${ex.__str__()}')
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'pdfcontratopagoprograma':
            try:
                numcontrato = 0
                idins = request.POST['idins']
                admitido = InscripcionCohorte.objects.get(status=True, pk=int(idins))
                registro = Contrato.objects.filter(status=True, inscripcion__id=idins, inscripcion__status=True).last()
                secuenciacp = secuencia_contratopagare(request, datetime.now().year)
                if not registro or not registro.numerocontrato:
                    secuenciacp.secuenciacontrato += 1
                    secuenciacp.save(request)
                    if Contrato.objects.filter(status=True, numerocontrato=secuenciacp.secuenciacontrato, fechacontrato__year=secuenciacp.anioejercicio.anioejercicio).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Error al generar el contrato, intente nuevamente"})
                    else:
                        if Contrato.objects.filter(status=True,inscripcion_id=idins).exists():
                            ct = Contrato.objects.filter(inscripcion_id=idins, status=True,).last()
                            ct.numerocontrato = secuenciacp.secuenciacontrato
                            ct.save(request)
                            log(u'Editó número contrato: %s' % (ct), request, "add")
                        else:
                            ct = Contrato(inscripcion_id=idins, numerocontrato=secuenciacp.secuenciacontrato)
                            ct.save(request)
                            log(u'Adicionó numero contrato: %s' % (ct), request, "add")
                        numcontrato = ct.numerocontrato
                else:
                    if Contrato.objects.get(status=True, inscripcion__id=idins, inscripcion__status=True).numerocontrato:
                        numcontrato = Contrato.objects.get(status=True, inscripcion__id=idins, inscripcion__status=True).numerocontrato

                cont = Contrato.objects.get(status=True, inscripcion__id=idins)

                tipo = 'pdf'
                paRequest = {
                    'idins': admitido.id,
                    'numcontrato': numcontrato
                }

                reporte = None
                if admitido.formapagopac.id == 1:
                    reporte = Reporte.objects.get(id=663)
                elif admitido.formapagopac.id == 2:
                    reporte = Reporte.objects.get(id=664)

                d = run_report_v1(reporte=reporte, tipo=tipo, paRequest=paRequest, request=request)

                if not d['isSuccess']:
                    raise NameError(d['mensaje'])
                else:
                    url_archivo = (SITE_STORAGE + d['data']['reportfile']).replace('\\', '/')
                    url_archivo = (url_archivo).replace('//', '/')
                    _name = generar_nombre(f'contrato_{request.user.username}_{idins}_','descargado')
                    folder = os.path.join(SITE_STORAGE, 'media', 'archivodescargado', '')
                    if not os.path.exists(folder):
                        os.makedirs(folder)
                    folder_save = os.path.join('archivodescargado', '').replace('\\', '/')
                    url_file_generado = f'{folder_save}{_name}.pdf'
                    ruta_creacion = SITE_STORAGE
                    ruta_creacion = ruta_creacion.replace('\\', '/')
                    shutil.copy(url_archivo, ruta_creacion + '/media/' + url_file_generado)

                    cont.archivodescargado = url_file_generado
                    cont.save(request)
                    # return JsonResponse({"result": "ok", 'url': cont.download_descargado()})
                    return JsonResponse({"result": "ok", 'url': d['data']['reportfile']})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al descargar.%s"%(ex)})

        elif action == 'ingresarpago':
            try:
                with transaction.atomic():
                    inscripcioncohorte = InscripcionCohorte.objects.get(pk=int((request.POST['id'])))
                    cuentadeposito = int(request.POST['cuentadeposito'])
                    telefono = str(request.POST['telefono'])
                    email = str(request.POST['email'])
                    fechapago = convertir_fecha(request.POST['fecha'])
                    valor = Decimal(request.POST['valor'])
                    observacion = request.POST['observacion']
                    tipocomprobante = int(request.POST['tipocomprobante'])
                    curso = str(request.POST['curso'])
                    carrera = str(request.POST['carrera'])
                    persona_get = Persona.objects.get(pk=inscripcioncohorte.inscripcionaspirante.persona.id)
                    persona_get.telefono = telefono
                    persona_get.email = email
                    persona_get.save()
                    cuentadepositoget = cuentadeposito
                    if valor <= 0:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "El valor debe ser mayor a cero."}, safe=False)
                    if 'evidencia' in request.FILES:
                        form = ComprobanteArchivoEstudianteForm(request.POST, request.FILES)
                        if form.is_valid():
                            nombrepersona = persona_get.__str__()
                            nombrepersona_str = persona_get.__str__().lower().replace(' ', '_')
                            comprobante = ComprobanteAlumno(persona=persona_get,
                                                            telefono=telefono,
                                                            email=email,
                                                            curso=inscripcioncohorte.cohortes.maestriaadmision.carrera.nombre,
                                                            carrera=inscripcioncohorte.cohortes.maestriaadmision.carrera.nombre,
                                                            cuentadeposito=cuentadepositoget,
                                                            valor=valor,
                                                            fechapago=fechapago,
                                                            observacion=observacion,
                                                            inscripcioncohorte=inscripcioncohorte,
                                                            tipocomprobante=tipocomprobante,
                                                            asesor=inscripcioncohorte.asesor)
                            if 'evidencia' in request.FILES:
                                newfile = request.FILES['evidencia']
                                if newfile.size > 10485760:
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})

                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if not (ext.lower() == '.pdf' or ext.lower() == '.png'):
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf o .png"}, safe=False)

                                nombrefoto = 'comprobante_{}'.format(str(inscripcioncohorte.id))
                                newfile._name = generar_nombre(nombrefoto.strip(), newfile._name)
                                comprobante.comprobantes = newfile
                            comprobante.save()

                            log(u'Adicionó comprobante de pago: %s' % comprobante, request, "add")

                            # -------CREAR COMPROBANTE EPUNEMI-------
                            cursor = connections['epunemi'].cursor()

                            if inscripcioncohorte.inscripcionaspirante.persona.cedula:
                                personacedula = str(inscripcioncohorte.inscripcionaspirante.persona.cedula)

                                sql = """SELECT pe.id FROM sga_persona AS pe WHERE pe.cedula='%s' AND pe.status=TRUE;  """ % (personacedula)
                                cursor.execute(sql)
                                idalumno = cursor.fetchone()

                            elif inscripcioncohorte.inscripcionaspirante.persona.pasaporte:
                                personacedula = str(inscripcioncohorte.inscripcionaspirante.persona.pasaporte)

                                sql = """SELECT pe.id FROM sga_persona AS pe WHERE pe.pasaporte='%s' AND pe.status=TRUE;  """ % (personacedula)
                                cursor.execute(sql)
                                idalumno = cursor.fetchone()

                            elif inscripcioncohorte.inscripcionaspirante.persona.ruc:
                                personacedula = str(inscripcioncohorte.inscripcionaspirante.persona.ruc)

                                sql = """SELECT pe.id FROM sga_persona AS pe WHERE pe.ruc='%s' AND pe.status=TRUE;  """ % (personacedula)
                                cursor.execute(sql)
                                idalumno = cursor.fetchone()


                            sql =  """INSERT INTO sagest_comprobantealumno (status, fecha_creacion, fecha_modificacion, persona_id, cuentadeposito_id, valor, idcomprobanteunemi, fechapago, estados, tiporegistro, tipocomprobante, comprobantes, observacion, curso, carrera, telefono, email, asesor, telefono_asesor) 
                                        VALUES (TRUE, NOW(), NULL, %s, %s, %s, %s,'/%s/', 1, 1, %s, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');""" % (idalumno[0], cuentadeposito, comprobante.valor, comprobante.id, comprobante.fechapago, comprobante.tipocomprobante, comprobante.comprobantes,
                                                                                                                                            comprobante.observacion, curso, carrera, inscripcioncohorte.inscripcionaspirante.persona.telefono, inscripcioncohorte.inscripcionaspirante.persona.email,
                                                                                                                                                          inscripcioncohorte.asesor.persona.nombre_completo_inverso(), inscripcioncohorte.asesor.persona.telefono)
                            cursor.execute(sql)

                            sql = """SELECT ca.id FROM sagest_comprobantealumno AS ca WHERE ca.idcomprobanteunemi='%s' AND ca.status=TRUE;  """ % (comprobante.id)
                            cursor.execute(sql)
                            idcomepu = cursor.fetchone()

                            if idcomepu is not None:
                                comprobante.idcomprobanteepunemi = int(idcomepu[0])
                                comprobante.save()

                            return JsonResponse({"result": False, "mensaje":'Datos guardados correctamente'}, safe=False)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
                            # return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Falta subir evidencia del comprobante de pago."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Error al subir pago: %s." % (ex)}, safe=False)

        elif action == 'editcomprobante':
            try:
                with transaction.atomic():
                    comprobante = ComprobanteAlumno.objects.get(pk=int((request.POST['id'])))
                    cuentadeposito = int(request.POST['cuentadeposito'])
                    valor = Decimal(request.POST['valor'])
                    observacion = request.POST['observacion']
                    tipocomprobante = int(request.POST['tipocomprobante'])
                    if valor <= 0:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "El valor debe ser mayor a cero."}, safe=False)
                    # if 'evidencia' in request.FILES:
                    form = EditarComprobantePagoForm(request.POST, request.FILES)
                    if form.is_valid():
                        if 'evidencia' in request.FILES:
                            newfile = request.FILES['evidencia']
                            if newfile.size > 10485760:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})

                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if not (ext.lower() == '.pdf' or ext.lower() == '.png'):
                                transaction.set_rollback(True)
                                return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf o .png"}, safe=False)

                            nombrefoto = 'comprobante_{}'.format(str(comprobante.persona.id))
                            newfile._name = generar_nombre(nombrefoto.strip(), newfile._name)
                            comprobante.comprobantes = newfile

                        comprobante.valor = valor
                        comprobante.observacion = observacion
                        comprobante.tipocomprobante = tipocomprobante
                        comprobante.cuentadeposito = cuentadeposito
                        comprobante.save()

                        log(u'Editó comprobante de pago: %s' % comprobante, request, "edit")

                        # -------CREAR COMPROBANTE EPUNEMI-------
                        cursor = connections['epunemi'].cursor()
                        sql = """SELECT comp.id FROM sagest_comprobantealumno AS comp WHERE comp.idcomprobanteunemi=%s AND comp.status=TRUE;  """ % (comprobante.id)
                        cursor.execute(sql)

                        idcomp = cursor.fetchone()

                        if idcomp is not None:
                            sql = """UPDATE sagest_comprobantealumno SET valor=%s, observacion='%s', tipocomprobante=%s, cuentadeposito_id=%s, comprobantes='%s' 
                            WHERE status=true AND id=%s; """ % (comprobante.valor, comprobante.observacion, comprobante.tipocomprobante, comprobante.cuentadeposito, comprobante.comprobantes, idcomp[0])

                            cursor.execute(sql)
                        cursor.close()
                        return JsonResponse({"result": False, "mensaje":'Datos guardados correctamente'}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
                            # return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
                    # else:
                    #     transaction.set_rollback(True)
                    #     return JsonResponse({"result": True, "mensaje": "Falta subir evidencia del comprobante de pago."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Error al subir pago: %s." % (ex)}, safe=False)

        elif action == 'existetablaamortizacion':
            try:
                existe = False
                contrato = None
                if 'id' in request.POST and request.POST['id']:
                   contrato = Contrato.objects.filter(pk=request.POST['id']).last()
                if contrato:
                    tablaamortizacion = contrato.tablaamortizacion_set.values('id').filter(status=True)
                    if tablaamortizacion:
                        existe = True
                if existe:
                    return JsonResponse({'result': 'ok'})
                else:
                    return JsonResponse({"result": "bad"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

        elif action == 'addarchivorequi':
            try:
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext.lower() == '.pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})

                f = EvidenciaRequisitoAdmisionForm(request.POST, request.FILES)
                if f.is_valid():
                    inscripcioncohorte = InscripcionCohorte.objects.get(pk=int(encrypt(request.POST['idins'])))
                    requisitosmaestria = RequisitosMaestria.objects.get(pk=int(encrypt(request.POST['id'])))
                    if not EvidenciaRequisitosAspirante.objects.filter(requisitos=requisitosmaestria, inscripcioncohorte=inscripcioncohorte, status=True).exists():
                        requisitomaestria = EvidenciaRequisitosAspirante(requisitos=requisitosmaestria,
                                                                         inscripcioncohorte=inscripcioncohorte)
                        requisitomaestria.save(request)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("requisitopgrado_", newfile._name)
                            requisitomaestria.archivo = newfile
                            requisitomaestria.save(request)
                        log(u'Adicionó requisito de maestria aspirante: %s' % requisitomaestria.requisitos, request, "add")
                        detalle = DetalleEvidenciaRequisitosAspirante(evidencia=requisitomaestria,
                                                                      estadorevision=1,
                                                                      # persona=inscripcioncohorte.inscripcionaspirante.persona,
                                                                      fecha=datetime.now().date(),
                                                                      observacion=f.cleaned_data['observacion'])
                        detalle.save(request)

                        if inscripcioncohorte.total_evidence_lead():
                            inscripcioncohorte.todosubido = True
                            inscripcioncohorte.tienerechazo = False
                            inscripcioncohorte.save()

                        return JsonResponse({"result": False}, safe=False)
                    else:
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            if newfile.size > 10485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                            else:
                                newfiles = request.FILES['archivo']
                                newfilesd = newfiles._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if not ext.lower() == '.pdf':
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        f = RequisitosMaestriaForm(request.POST, request.FILES)
                        requisito = EvidenciaRequisitosAspirante.objects.get(requisitos=requisitosmaestria, inscripcioncohorte=inscripcioncohorte, status=True)
                        if f.is_valid():
                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                newfile._name = generar_nombre("requisitopgrado_", newfile._name)
                                requisito.archivo = newfile
                                requisito.save(request)
                            detalle = DetalleEvidenciaRequisitosAspirante(evidencia=requisito,
                                                                          estadorevision=1,
                                                                          fecha=datetime.now().date(),
                                                                          observacion=f.cleaned_data['observacion'])
                            detalle.save(request)
                            log(u'Editó requisito de maestría aspirante: %s' % requisito, request, "edit")

                            if inscripcioncohorte.total_evidence_lead():
                                inscripcioncohorte.todosubido = True
                                inscripcioncohorte.tienerechazo = False
                                inscripcioncohorte.save()

                            return JsonResponse({"result": False}, safe=False)
                        else:
                            return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                                 "message": "Error en el formulario"})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addtitulacionpos':
            try:
                with transaction.atomic():
                    persona = Persona.objects.get(pk=int(request.POST['idpersona']))
                    f = TitulacionPersonaAdmisionPosgradoForm(request.POST, request.FILES)
                    if 'registroarchivo' in request.FILES:
                        registroarchivo = request.FILES['registroarchivo']
                        extencion1 = registroarchivo._name.split('.')
                        exte1 = extencion1[1]
                        if registroarchivo.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 4 Mb."})
                        if not exte1 == 'pdf' and not exte1 == 'png' and not exte1 == 'jpg' and not exte1 == 'jpeg' and not exte1 == 'jpg':
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Archivo SENESCYT solo en formato .pdf, jpg, jpeg, png"})
                    if f.is_valid():
                        if persona:
                            titulo = None
                            if request.POST['registrartitulo'] == 'true':

                                if Titulo.objects.filter(nombre__unaccent=f.cleaned_data['nombre'].upper()).exists():
                                    return JsonResponse({"result": "bad", "mensaje": u"Imposible guardar registro. El título %s ya se encuentra registrado." % (f.cleaned_data['nombre'])})
                                if Titulo.objects.filter(nombre=f.cleaned_data['nombre'].upper(), nivel=f.cleaned_data['nivel']).exists():
                                    return JsonResponse({"result": "bad", "mensaje": u"Imposible guardar registro. El título %s ya se encuentra registrado." % (f.cleaned_data['nombre'])})
                                if f.cleaned_data['nivel'].id == 4 and not f.cleaned_data['grado']:
                                    return JsonResponse({"result": "bad", "mensaje": u"Por favor seleccione grado."})

                                titulo = Titulo(nombre=f.cleaned_data['nombre'],
                                                abreviatura=f.cleaned_data['abreviatura'],
                                                nivel=f.cleaned_data['nivel'],
                                                grado=f.cleaned_data['grado'],
                                                areaconocimiento=f.cleaned_data['campoamplio'][0],
                                                subareaconocimiento=f.cleaned_data['campoespecifico'][0],
                                                subareaespecificaconocimiento=f.cleaned_data['campodetallado'][0]
                                                )
                                titulo.save(request)
                                titulacion = Titulacion(persona=persona,
                                                        titulo=titulo,
                                                        registro=f.cleaned_data['registro'],
                                                        # pais=f.cleaned_data['pais'],
                                                        # provincia=f.cleaned_data['provincia'],
                                                        # canton=f.cleaned_data['canton'],
                                                        # parroquia=f.cleaned_data['parroquia'],
                                                        educacionsuperior=True,
                                                        institucion=f.cleaned_data['institucion'])
                                titulacion.save(request)
                            else:
                                titulo = f.cleaned_data['titulo']
                                if Titulacion.objects.filter(persona=persona, titulo=titulo).exists():
                                    raise NameError("No se puede guardar título. Usted ya tiene registrado su título %s." % (titulo))
                                titulacion = Titulacion(persona=persona,
                                                        titulo=f.cleaned_data['titulo'],
                                                        registro=f.cleaned_data['registro'],
                                                        # pais=f.cleaned_data['pais'],
                                                        # provincia=f.cleaned_data['provincia'],
                                                        # canton=f.cleaned_data['canton'],
                                                        # parroquia=f.cleaned_data['parroquia'],
                                                        educacionsuperior=True,
                                                        institucion=f.cleaned_data['institucion'])
                                titulacion.save(request)
                        if 'registroarchivo' in request.FILES:
                            newfile2 = request.FILES['registroarchivo']
                            if newfile2:
                                newfile2._name = generar_nombre("archivosenecyt_", newfile2._name)
                                titulacion.registroarchivo = newfile2
                                titulacion.save(request)
                        campotitulo = None
                        if CamposTitulosPostulacion.objects.filter(status=True, titulo=titulo).exists():
                            campotitulo = CamposTitulosPostulacion.objects.filter(status=True, titulo=titulo).first()
                        else:
                            campotitulo = CamposTitulosPostulacion(titulo=titulo)
                            campotitulo.save(request)

                        if not f.cleaned_data['campoamplio']:
                            if titulo.areaconocimiento:
                                if not campotitulo.campoamplio.filter(id=titulo.areaconocimiento.id):
                                    campotitulo.campoamplio.add(titulo.areaconocimiento)
                            else:
                                raise NameError("El título %s no cuenta con campo amplio, específico y detallado. Favor comuníquese con servicios informáticos (servicios.informaticos@unemi.edu.ec) para actualizar los datos del título." % (titulo))
                            if titulo.subareaconocimiento:
                                if not campotitulo.campoespecifico.filter(id=titulo.subareaconocimiento.id):
                                    campotitulo.campoespecifico.add(titulo.subareaconocimiento)
                            if titulo.subareaespecificaconocimiento:
                                if not campotitulo.campodetallado.filter(id=titulo.subareaespecificaconocimiento.id):
                                    campotitulo.campodetallado.add(titulo.subareaespecificaconocimiento)
                        else:
                            for ca in f.cleaned_data['campoamplio']:
                                if not campotitulo.campoamplio.filter(id=ca.id):
                                    campotitulo.campoamplio.add(ca)
                            for ce in f.cleaned_data['campoespecifico']:
                                if not campotitulo.campoespecifico.filter(id=ce.id):
                                    campotitulo.campoespecifico.add(ce)
                            for cd in f.cleaned_data['campodetallado']:
                                if not campotitulo.campodetallado.filter(id=cd.id):
                                    campotitulo.campodetallado.add(cd)
                        campotitulo.save(request)
                        log(u'Adicionó titulación admisión de posgrado: %s' % titulacion, request, "add")
                        return JsonResponse({"result": "ok", "idpersona": persona.id})
                    else:
                        # raise NameError('Error')
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s" % (ex)})

        elif action == 'cargararchivoimagen':
            try:
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if ext.lower() == '.jpg' or ext.lower() == '.png' or ext.lower() == '.jpeg' or ext.lower() == '.JPG' or ext.lower() == '.PNG' or ext.lower() == '.JPEG':
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .jpg, .png."})
                f = RequisitosMaestriaImgForm(request.POST)
                if f.is_valid():
                    inscripcioncohorte = InscripcionCohorte.objects.get(pk=request.POST['id'])
                    requisitosmaestria = RequisitosMaestria.objects.get(pk=request.POST['idevidencia'])
                    if not EvidenciaRequisitosAspirante.objects.filter(requisitos=requisitosmaestria, inscripcioncohorte=inscripcioncohorte, status=True).exists():
                        requisitomaestria = EvidenciaRequisitosAspirante(requisitos=requisitosmaestria,
                                                                         inscripcioncohorte=inscripcioncohorte)
                        requisitomaestria.save(request)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("requisitopgrado_", newfile._name)
                            requisitomaestria.archivo = newfile
                            requisitomaestria.save(request)
                        log(u'Adicionó requisito de maestria aspirante: %s' % requisitomaestria.requisitos, request, "add")
                        detalle = DetalleEvidenciaRequisitosAspirante(evidencia=requisitomaestria,
                                                                      estadorevision=1,
                                                                      # persona=inscripcioncohorte.inscripcionaspirante.persona,
                                                                      fecha=datetime.now().date(),
                                                                      observacion=f.cleaned_data['observacion'])
                        detalle.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            if newfile.size > 10485760:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})
                            else:
                                newfiles = request.FILES['archivo']
                                newfilesd = newfiles._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext.lower() == '.jpg' or ext.lower() == '.png' or ext.lower() == '.jpeg' or ext.lower() == '.JPG' or ext.lower() == '.PNG' or ext.lower() == '.JPEG':
                                    a = 1
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .jpg, .png."})
                        f = RequisitosMaestriaImgForm(request.POST)
                        requisito = EvidenciaRequisitosAspirante.objects.get(requisitos=requisitosmaestria, inscripcioncohorte=inscripcioncohorte, status=True)
                        if f.is_valid():
                            # requisito.observacion = f.cleaned_data['observacion']
                            # requisito.estadorevision = 1
                            # requisito.save(request)
                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                newfile._name = generar_nombre("requisitopgrado_", newfile._name)
                                requisito.archivo = newfile
                                requisito.save(request)
                            detalle = DetalleEvidenciaRequisitosAspirante(evidencia=requisito,
                                                                          estadorevision=1,
                                                                          # persona=inscripcioncohorte.inscripcionaspirante.persona,
                                                                          fecha=datetime.now().date(),
                                                                          observacion=f.cleaned_data['observacion'])
                            detalle.save(request)
                            log(u'Editó requisito de maestría aspirante: %s' % requisito, request, "edit")
                            return JsonResponse({"result": "ok"})
                        else:
                            raise NameError('Error')
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'cargarcombo_titulacion':
            try:
                persona = Persona.objects.filter(pk=request.POST['id']).last()
                lista = []
                if persona:
                    for titulo in persona.titulacion_set.filter(status=True, educacionsuperior=True):
                        lista.append([titulo.id, titulo.titulo.__str__()])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'extraercampos':
            try:
                titulacion = None
                cantexperiencia = 0
                ce = 'Campo Específico: '
                insc = InscripcionCohorte.objects.get(pk=request.POST['insc'])
                if request.POST['id']:
                    titulacion = Titulacion.objects.filter(pk=request.POST['id']).last()
                if titulacion:
                    campotitulos = CamposTitulosPostulacion.objects.filter(status=True, titulo=titulacion.titulo)
                    for campotitulo in campotitulos:
                        for campoe in campotitulo.campoespecifico.all():
                            ce = ce + campoe.__str__() + ' | '
                return JsonResponse({'result': 'ok', 'ce': ce})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

        elif action == 'validarperfilingreso':
            try:
                titulacion = None
                cantexperiencia = 0
                # ce = 'Campo Específico: '
                insc = InscripcionCohorte.objects.get(pk=request.POST['insc'])
                if request.POST['id']:
                    titulacion = Titulacion.objects.filter(pk=request.POST['id']).last()
                # if titulacion:
                #     campotitulos = CamposTitulosPostulacion.objects.filter(status=True, titulo=titulacion.titulo)
                #     for campotitulo in campotitulos:
                #         for campoe in campotitulo.campoespecifico.all():
                #             ce = ce + campoe.__str__() + ' | '
                perfilingreso = None
                if 'idperfil' in request.POST and request.POST['idperfil']:
                    perfilingreso = DetallePerfilIngreso.objects.get(pk=request.POST['idperfil'])
                if perfilingreso:
                    cantexperiencia = request.POST['cantexperiencia'] if 'cantexperiencia' in request.POST and request.POST['cantexperiencia'] else 0
                    if not perfilingreso.alltitulos:
                        # if not insc.tiulacionaspirante:
                        # todos los campos especificos de los titulos de perfil
                        listcetituloperfil = CamposTitulosPostulacion.objects.values_list('campoespecifico__nombre', flat=True).filter(titulo__in=perfilingreso.titulo.all()).distinct()
                        # todos los campos especificos del titulo del postulante
                        listcetitulopos = CamposTitulosPostulacion.objects.values_list('campoespecifico__nombre', flat=True).filter(titulo=titulacion.titulo).distinct()
                        aplicamaestria = False
                        for campoesp in listcetitulopos:
                            if campoesp in listcetituloperfil:
                               aplicamaestria = True
                        if not aplicamaestria:
                            titulosaplica = ''
                            campotitulos = CamposTitulosPostulacion.objects.filter(status=True, titulo__in=perfilingreso.titulo.all()).distinct()
                            for campotitulo in campotitulos:
                                titulosaplica = titulosaplica +'<br> * '+campotitulo.__str__().title()
                                # for campoes in campotitulo.campoespecifico.all():
                                #     titulosaplica = titulosaplica + campoes.__str__().capitalize() + ' | '
                            if not int(cantexperiencia) > 0:
                                return JsonResponse({'result': 'noaplica', 'titulos': titulosaplica})
                    if perfilingreso.experiencia: #si el perfil cuenta con experiencia
                        if int(cantexperiencia) >= 0:
                            experienciamaestria = perfilingreso.cantidadexperiencia
                            if not insc.cantexperiencia >= experienciamaestria:
                                if not float(cantexperiencia) >= float(experienciamaestria):
                                    return JsonResponse({'result': 'noexperiencia', 'cantidad': experienciamaestria})
                    if titulacion:
                        insc.tiulacionaspirante = titulacion
                    if int(cantexperiencia) > 0:
                        insc.cantexperiencia = cantexperiencia
                    insc.save(request)
                    log(u'Actualizó titulación y experiencia de la inscripción: %s' % insc, request, "edit")

                    if insc.tiulacionaspirante and titulacion.registroarchivo:
                        requisitosmaestria = RequisitosMaestria.objects.filter(status=True, cohorte=insc.cohortes, requisito__id__in=[52, 6, 14, 16, 4, 29]).first()
                        if not EvidenciaRequisitosAspirante.objects.filter(requisitos=requisitosmaestria,
                                                                           inscripcioncohorte=insc,
                                                                           status=True).exists():
                            requisitomaestria = EvidenciaRequisitosAspirante(requisitos=requisitosmaestria,
                                                                             inscripcioncohorte=insc)
                            requisitomaestria.save(request)
                            requisitomaestria.archivo = titulacion.registroarchivo
                            requisitomaestria.save(request)
                            log(u'Adicionó requisito de maestria aspirante: %s' % requisitomaestria.requisitos, request, "add")
                            detalle = DetalleEvidenciaRequisitosAspirante(evidencia=requisitomaestria,
                                                                          estadorevision=1,
                                                                          # persona=inscripcioncohorte.inscripcionaspirante.persona,
                                                                          fecha=datetime.now().date(),
                                                                          observacion='Título validado en el perfil de ingreso (afinidad)')
                            detalle.save(request)

                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

        elif action == 'cargamasiva':
            try:
                inscripcioncohorte = InscripcionCohorte.objects.get(pk=request.POST['id'])
                listadorequisitosmaestria = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, status=True)
                for requi in listadorequisitosmaestria:
                    nombrefile = 'requisito' + str(requi.id)
                    if nombrefile in request.FILES:
                        if not EvidenciaRequisitosAspirante.objects.filter(requisitos=requi, inscripcioncohorte=inscripcioncohorte, status=True).exists():
                            requisitomaestria = EvidenciaRequisitosAspirante(requisitos=requi,
                                                                             inscripcioncohorte=inscripcioncohorte)
                            requisitomaestria.save(request)
                            newfile = request.FILES[nombrefile]
                            newfile._name = generar_nombre("requisitopgrado_" + str(requi.id) + "_", newfile._name)
                            requisitomaestria.archivo = newfile
                            requisitomaestria.save(request)
                            log(u'Adicionó requisito de maestria aspirante: %s' % requisitomaestria.requisitos, request, "add")
                            detalle = DetalleEvidenciaRequisitosAspirante(evidencia=requisitomaestria,
                                                                          estadorevision=1,
                                                                          fecha=datetime.now().date(),
                                                                          observacion='')
                            detalle.save(request)

                if inscripcioncohorte.total_evidence_lead():
                    inscripcioncohorte.todosubido = True
                    inscripcioncohorte.tienerechazo = False
                    inscripcioncohorte.save()

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addgarantepagomaestria':
            try:
                insc = InscripcionCohorte.objects.get(pk=request.POST['id'])
                f = GarantePagoMaestriaForm(request.POST)
                resp = validarcedula(request.POST['cedula'].strip())
                if resp != 'Ok':
                    raise NameError(u"Problemas con la cédula: %s." % (resp))
                if f.is_valid():
                    if not GarantePagoMaestria.objects.filter(cedula=f.cleaned_data['cedula'], status=True).exists():
                        garante = GarantePagoMaestria(inscripcioncohorte=insc,
                                                      cedula=f.cleaned_data['cedula'],
                                                      nombres=f.cleaned_data['nombres'],
                                                      apellido1=f.cleaned_data['apellido1'],
                                                      apellido2=f.cleaned_data['apellido2'],
                                                      genero=f.cleaned_data['genero'],
                                                      telefono=f.cleaned_data['telefono'],
                                                      email=f.cleaned_data['email'],
                                                      direccion=f.cleaned_data['direccion'])
                        garante.save(request)
                        log(u'Adicionó garante de pago: %s al aspirante %s' %(garante, insc), request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        raise NameError("La persona ya es garante de otro aspirante a mestría.")
                else:
                    raise NameError("Error en el formulario.")
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Error al registrar. %s"%(ex)}, safe=False)

        elif action == 'delgarantepagomaestria':
            try:
                garante = GarantePagoMaestria.objects.get(pk=request.POST['id'])
                garante.status = False
                garante.save(request)
                log(u'Eliminó garante: %s del aspirante  %s' % (garante, garante.inscripcioncohorte), request, "del")
                return JsonResponse({"result": "ok", "mensaje": u"Garante eliminado correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        elif action == 'ViewedNotification':
            try:
                id = request.POST['id'] if 'id' in request.POST and request.POST['id'] else 0
                notificacion = Notificacion.objects.get(pk=id)
                if not notificacion:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos"})

                notificacion.leido = True
                notificacion.visible = False
                notificacion.fecha_hora_leido = datetime.now()
                notificacion.save(request)
                log(u'Leo el mensaje: %s' % notificacion, request, "edit")
                return JsonResponse({"result": "ok", 'mensaje': u'Notificación vista'})
            except Exception as ex:
                return JsonResponse({"result": "bad","mensaje": u"Error al cargar los datos %s"  % ex.__str__()})

        elif action == 'deletecanal':
            try:
                eCanal = CanalInformacionMaestria.objects.get(pk=int(request.POST['id']))
                eCanal.status = False
                eCanal.save(request)
                log(u'Eliminó el canal de información: %s' % eCanal, request, "del")
                return JsonResponse({"result": 'ok', "mensaje": u"Canal eliminado correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        elif action == 'deleteconvenio':
            try:
                from posgrado.models import Convenio
                eConvenio = Convenio.objects.get(pk=int(request.POST['id']))
                eConvenio.status = False
                eConvenio.save(request)
                log(u'Eliminó el convenio de posgrado: %s' % eConvenio, request, "del")
                return JsonResponse({"result": 'ok', "mensaje": u"Convenio eliminado correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        elif action == 'confirmarmodalidadpago':
            try:
                admitido = InscripcionCohorte.objects.get(status=True, pk=int(request.POST['id']))
                formapago = TipoFormaPagoPac.objects.get(status=True, pk=int(request.POST['fp']))
                admitido.aceptado = True
                admitido.formapagopac = formapago
                admitido.save(request)

                observacion = ''
                if int(request.POST['fp']) == 1:
                    observacion = 'Aceptó modalidad de pago por contado'
                else:
                    observacion = 'Aceptó modalidad de pago diferido'

                deta = DetalleAprobacionFormaPago(inscripcion_id=admitido.id,
                                                  formapagopac=formapago,
                                                  estadoformapago=1,
                                                  observacion=observacion,
                                                  persona=persona)
                deta.save(request)
                log(u'Confirmó la modalidad de pago por contado: %s' % admitido, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'resturacionmasiva':
            try:
                leadsdesactivados = request.POST['id'].split(',')
                if leadsdesactivados[0] != '':
                    for lead in leadsdesactivados:
                        integrante = InscripcionCohorte.objects.get(pk=int(lead))
                        integrante.status = True
                        integrante,motivo_rechazo_desactiva = 1
                        integrante.save(request)

                        requistosmaestria = RequisitosMaestria.objects.filter(status=True, cohorte=integrante.cohortes,
                                                                              requisito__claserequisito__clasificacion__id=1,
                                                                              obligatorio=True).values_list('id',
                                                                                                            flat=True)
                        for requisto in requistosmaestria:
                            if EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=integrante,
                                                                           requisitos_id=requisto,
                                                                           requisitos__requisito__claserequisito__clasificacion__id=1).exists():
                                evi = EvidenciaRequisitosAspirante.objects.filter(status=True,
                                                                                  inscripcioncohorte=integrante,
                                                                                  requisitos_id=requisto,
                                                                                  requisitos__requisito__claserequisito__clasificacion__id=1).order_by(
                                    '-id').first()
                                if evi.ultima_evidencia():
                                    deta = DetalleEvidenciaRequisitosAspirante.objects.get(pk=evi.ultima_evidencia().id)
                                    deta.estado_aprobacion = 1
                                    deta.observacion = "Pendiente debido a restauración de Postulación"
                                    deta.save()

                        requistosmaestria = RequisitosMaestria.objects.filter(status=True, cohorte=integrante.cohortes,
                                                                              requisito__claserequisito__clasificacion__id=3,
                                                                              obligatorio=True).values_list('id',
                                                                                                            flat=True)
                        for requisto in requistosmaestria:
                            if EvidenciaRequisitosAspirante.objects.filter(status=True, inscripcioncohorte=integrante,
                                                                           requisitos_id=requisto,
                                                                           requisitos__requisito__claserequisito__clasificacion__id=3).exists():
                                evi = EvidenciaRequisitosAspirante.objects.filter(status=True,
                                                                                  inscripcioncohorte=integrante,
                                                                                  requisitos_id=requisto,
                                                                                  requisitos__requisito__claserequisito__clasificacion__id=3).order_by(
                                    '-id').first()
                                if evi.ultima_evidencia():
                                    deta = DetalleEvidenciaRequisitosAspirante.objects.get(pk=evi.ultima_evidencia().id)
                                    deta.estado_aprobacion = 1
                                    deta.observacion = "Pendiente debido a restauración de Postulación"
                                    deta.save()
                        if integrante.total_evidence_lead():
                            integrante.estado_aprobador = 2
                        else:
                            integrante.estado_aprobador = 1
                        integrante.save(request)

                        # SI TIENE RUBROS GENERADOS
                        if Rubro.objects.filter(inscripcion=integrante, status=True).exists():
                            rubros = Rubro.objects.filter(inscripcion=integrante, status=True)
                            for rubro in rubros:
                                if rubro.idrubroepunemi != 0:
                                    cursor = connections['epunemi'].cursor()
                                    sql = """SELECT id FROM sagest_pago WHERE rubro_id=%s; """ % (rubro.idrubroepunemi)
                                    cursor.execute(sql)
                                    tienerubropagos = cursor.fetchone()

                                    if tienerubropagos is None:
                                        sql = """DELETE FROM sagest_rubro WHERE sagest_rubro.id=%s AND sagest_rubro.idrubrounemi=%s; """ % (
                                            rubro.idrubroepunemi, rubro.id)
                                        cursor.execute(sql)
                                        cursor.close()

                                    rubro.status = False
                                    rubro.save()

                        if integrante.cohortes.tipo == 1:
                            if IntegranteGrupoExamenMsc.objects.filter(status=True, inscripcion=integrante).exists():
                                lista = IntegranteGrupoExamenMsc.objects.filter(status=True, inscripcion=integrante)
                                for li in lista:
                                    li.status = False
                                    li.save()

                            if IntegranteGrupoEntrevitaMsc.objects.filter(status=True, inscripcion=integrante).exists():
                                lista2 = IntegranteGrupoEntrevitaMsc.objects.filter(status=True, inscripcion=integrante)
                                for li2 in lista2:
                                    li2.status = False
                                    li2.save()

                        elif integrante.cohortes.tipo == 2:
                            if IntegranteGrupoExamenMsc.objects.filter(status=True, inscripcion=integrante).exists():
                                lista = IntegranteGrupoExamenMsc.objects.filter(status=True, inscripcion=integrante)
                                for li in lista:
                                    li.status = False
                                    li.save()

                        if Contrato.objects.filter(status=True, inscripcion=integrante).exists():
                            contratopos = Contrato.objects.get(status=True, inscripcion=integrante)

                            detalleevidencia = DetalleAprobacionContrato(contrato_id=contratopos.id, espagare=False,
                                                                         observacion='Pendiente por restauración de postulación',
                                                                         persona=persona, estado_aprobacion=1,
                                                                         fecha_aprobacion=datetime.now(),
                                                                         archivocontrato=contratopos.archivocontrato)
                            detalleevidencia.save(request)

                            if contratopos.inscripcion.formapagopac.id == 2:
                                detalleevidencia = DetalleAprobacionContrato(contrato_id=contratopos.id, espagare=True,
                                                                             observacion='Pendiente por restauración de postulación',
                                                                             persona=persona, estado_aprobacion=1,
                                                                             fecha_aprobacion=datetime.now(),
                                                                             archivocontrato=contratopos.archivopagare)
                                detalleevidencia.save(request)

                            contratopos.estado = 1
                            contratopos.estadopagare = 1
                            contratopos.save(request)
                        asunto = u"POSTULANTE RESTAURADO"
                        observacion = f'Se le comunica que el postulante {integrante.inscripcionaspirante.persona} con cédula {integrante.inscripcionaspirante.persona.cedula} ha sido restaurado. Por favor, revisar los documentos de admisión para su pre aprobación.'
                        para = integrante.asesor.persona
                        perfiu = integrante.asesor.perfil_administrativo()

                        notificacion3(asunto, observacion, para, None,
                                      '/comercial?s=' + integrante.inscripcionaspirante.persona.cedula,
                                      integrante.pk, 1,
                                      'sga', InscripcionCohorte, perfiu, request)
                        log(u'Restauró la postulación del lead: %s' % integrante, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f"{ex.__str__()}. En la linea {sys.exc_info()[-1].tb_lineno}"})

        elif action == 'updatemetamaestria':
            try:
                meta = DetalleAsesorMeta.objects.get(pk=request.POST['mid'])
                valor = int(request.POST['valor'])
                cuposmes = CuposMaestriaMes.objects.get(status=True, pk=request.POST['cuposmes'])

                if valor > meta.cantidad:
                    di = valor - meta.cantidad
                    tot = meta.asesormeta.maestria.total_metas_mes(meta.inicio.month, meta.inicio.year) + di
                else:
                    di = meta.cantidad - valor
                    tot = meta.asesormeta.maestria.total_metas_mes(meta.inicio.month, meta.inicio.year) - di

                if tot > cuposmes.cuposlibres:
                    return JsonResponse({"result": "bad",
                                         "mensaje": u"No puede asignar esta meta dado que daría un total de " + str(tot) + ", y esto excede el número de cupos libres que es de " + str(cuposmes.cuposlibres) + ". En caso de querer asignar más metas puede incrementa el total de cupos."})

                # cupoanterior = materia.cupo - materia.totalmatriculadocupoadicional
                meta.cantidad = valor
                meta.save(request)
                log(u'Asignó un meta mensual: %s' % meta, request, "edit")
                return JsonResponse({'result': 'ok', 'valor': meta.cantidad, 'totmet':meta.asesormeta.maestria.total_metas_mes(meta.inicio.month, meta.inicio.year), 'so':meta.asesormeta.maestria.sobrante(meta.inicio.month, meta.inicio.year)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        elif action == 'updatecupomaestria':
            try:
                cuposmes = CuposMaestriaMes.objects.get(pk=request.POST['mid'])
                valor = int(request.POST['valor'])

                if valor < cuposmes.maestria.total_metas_mes(cuposmes.inicio.month, cuposmes.inicio.year):
                    return JsonResponse({"result": "bad",
                                         "mensaje": u"No puede reducir la cantidad de cupos ya que existen metas asignadas. Para reducir los cupos reduzca las metas para que se acoplen a su nuevo valor"})

                cuposmes.cuposlibres = valor
                cuposmes.save(request)
                log(u'Actualizó cupos libres: %s' % cuposmes, request, "edit")
                return JsonResponse({'result': 'ok', 'valor': cuposmes.cuposlibres, 'totmet':cuposmes.maestria.total_metas_mes(cuposmes.inicio.month, cuposmes.inicio.year), 'so':cuposmes.maestria.sobrante(cuposmes.inicio.month, cuposmes.inicio.year)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        elif action == 'adddatospersonales':
            try:
                ins = InscripcionCohorte.objects.get(pk=int(request.POST['idins']))
                if PerfilInscripcion.objects.filter(persona=ins.inscripcionaspirante.persona).exists():
                    ePerfilInscripcion = PerfilInscripcion.objects.get(persona=ins.inscripcionaspirante.persona)
                else:
                    ePerfilInscripcion = PerfilInscripcion(persona=ins.inscripcionaspirante.persona,
                                                           tienediscapacidad=False)
                    ePerfilInscripcion.save()

                f = DatosPersonalesMaestranteForm(request.POST, request.FILES)
                if not f.is_valid():
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        raise NameError("Error, el tamaño del archivo de cédula es mayor a 4 Mb.")
                    if not exte.lower() == 'pdf':
                        raise NameError("Solo se permiten archivos .pdf")

                    ins.inscripcionaspirante.persona.mi_perfil().archivo = arch

                ePerfilInscripcion.tienediscapacidad = f.cleaned_data['tienediscapacidad']
                ePerfilInscripcion.tipodiscapacidad = f.cleaned_data['tipodiscapacidad']
                ePerfilInscripcion.porcientodiscapacidad = f.cleaned_data['porcientodiscapacidad'] if f.cleaned_data['porcientodiscapacidad'] is not None else 0
                ePerfilInscripcion.carnetdiscapacidad = f.cleaned_data['carnetdiscapacidad']
                ePerfilInscripcion.raza = f.cleaned_data['raza']
                ePerfilInscripcion.nacionalidadindigena = f.cleaned_data['nacionalidadindigena']
                ePerfilInscripcion.save(request)

                ins.inscripcionaspirante.persona.paisnacimiento = f.cleaned_data['paisori']
                ins.inscripcionaspirante.persona.provincianacimiento = f.cleaned_data['provinciaori']
                ins.inscripcionaspirante.persona.cantonnacimiento = f.cleaned_data['cantonori']
                ins.inscripcionaspirante.persona.pais = f.cleaned_data['paisresi']
                ins.inscripcionaspirante.persona.provincia = f.cleaned_data['provinciaresi']
                ins.inscripcionaspirante.persona.canton = f.cleaned_data['cantonresi']
                ins.inscripcionaspirante.persona.lgtbi = f.cleaned_data['lgtbi']
                ins.inscripcionaspirante.persona.save(request)

                log(u'Modifico datos personales: %s' % ins.inscripcionaspirante.persona, request, "edit")
                return JsonResponse({'result': False, 'mensaje': 'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos: {ex}'})

        if action == 'pdfoficioterminacioncontrato':
            try:
                contrato = Contrato.objects.get(status=True, pk=int(request.POST['idcon']))
                qrresult = oficioterminacioncontrato(request.POST['idcon'])

                url_archivo = (SITE_STORAGE + qrresult[24:]).replace('\\', '/')
                url_archivo = (url_archivo).replace('//', '/')
                _name = generar_nombre(f'oficio_{request.user.username}_{contrato.id}_', 'descargado')
                folder = os.path.join(SITE_STORAGE, 'media', 'archivooficiodescargado', '')
                if not os.path.exists(folder):
                    os.makedirs(folder)
                folder_save = os.path.join('archivooficiodescargado', '').replace('\\', '/')
                url_file_generado = f'{folder_save}{_name}.pdf'
                ruta_creacion = SITE_STORAGE
                ruta_creacion = ruta_creacion.replace('\\', '/')
                shutil.copy(url_archivo, ruta_creacion + '/media/' + url_file_generado)

                contrato.archivooficiodescargado = url_file_generado
                contrato.save(request)
                return JsonResponse({"result": "ok", 'url': qrresult})
            except Exception as ex:
                transaction.set_rollback(True)
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                print(f'${ex.__str__()}')
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'configuracionasesor':
                try:
                    request.session['viewactive'] = 16
                    data['title'] = u'Configuracion Asesor'
                    data['roles'] = RolAsesor.objects.filter(status=True)
                    url_vars = '&action=configuracionasesor'
                    idc = request.GET.get('idc', '0')
                    ide = request.GET.get('ide', '0')
                    search = request.GET.get('s', None)

                    filtro = Q(status=True, rol__id__in=[1, 5, 6])

                    if search:
                        data['search'] = search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(persona__apellido1__icontains=search) |
                                                     Q(persona__apellido2__icontains=search) |
                                                     Q(persona__nombres__icontains=search) |
                                                     Q(persona__cedula__icontains=search))
                            url_vars += "&s={}".format(search)
                        elif len(ss) == 2:
                            filtro = filtro & (Q(persona__apellido1__icontains=ss[0]) &
                                                     Q(persona__apellido2__icontains=ss[1]))
                            url_vars += "&s={}".format(ss)
                        else:
                            filtro = filtro & (Q(persona__apellido1__icontains=ss[0]) &
                                                Q(persona__apellido2__icontains=ss[1]) &
                                               Q(persona__nombres__icontains=ss[2]))
                            url_vars += "&s={}".format(ss)

                    if int(idc):
                        data['idc'] = int(idc)
                        data['cohorte'] = CohorteMaestria.objects.get(status=True, pk=int(idc))
                        url_vars += f"&idc={idc}"

                        data['ide'] = int(ide)
                        url_vars += f"&ide={ide}"

                    if int(ide):
                        if int(ide) == 1:
                            filtro = filtro & (Q(rol__id=1))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 2:
                            filtro = filtro & (Q(rol__id=6))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 3:
                            filtro = filtro & (Q(activo=True))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 4:
                            filtro = filtro & (Q(activo=False))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"

                    query = AsesorComercial.objects.filter(filtro).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    paging = MiPaginador(query, 20)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    # data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["asesores"] = page.object_list
                    data['eCohortes'] = CohorteMaestria.objects.filter(status=True).order_by('-id').distinct()
                    data['eTotal'] = query.count()
                    return render(request, "comercial/configuracionasesor.html", data)
                except Exception as ex:
                    pass

            elif action == 'addrol':
                try:
                    data['form2'] = RolForm
                    data['action'] = 'addrol'
                    template = get_template("comercial/modal/formrol.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editrol':
                try:
                    data['filtro'] = filtro = RolAsesor.objects.get(pk=int(request.GET['id']))
                    data['form2'] = RolForm(initial=model_to_dict(filtro))
                    data['action'] = 'editrol'
                    template = get_template("comercial/modal/formrol.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addasesor':
                try:
                    form = AsesorComercialForm()
                    form.fields['persona'].queryset = Persona.objects.filter(status=True, perfilusuario__administrativo__isnull=False).order_by('apellido1', 'apellido2', 'nombres')
                    form.fields['rol'].queryset = RolAsesor.objects.filter(status=True, id__in=[1, 4, 6]).order_by('descripcion')
                    # form.fields['maestriaadmision'].queryset = MaestriasAdmision.objects.filter(cohortemaestria__procesoabierto=True)
                    data['form2'] = form
                    data['action'] = 'addasesor'
                    template = get_template('comercial/modal/formasesor.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editasesor':
                try:
                    data['filtro'] = asesor = AsesorComercial.objects.get(
                        pk=int(request.GET['id']))
                    form = AsesorComercialForm(initial={'persona': asesor.persona,
                                                        'rol': asesor.rol,
                                                        'gruporol': asesor.rolgrupo,
                                                        'fechadesdevig': asesor.fecha_desde.date(),
                                                        'fechahastavig': asesor.fecha_hasta.date(),
                                                        'telefono':asesor.telefono,
                                                        'activo':asesor.activo})
                    form.sin_persona()
                    data['form2'] = form
                    data['action'] = 'editasesor'
                    template = get_template('comercial/modal/formasesor.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addlead':
                try:
                    puedeinscribirse = False
                    hoy = datetime.now().date()
                    data['puedeinscribirse'] = puedeinscribirse
                    # data['maestrialist'] = Carrera.objects.filter(status=True, coordinacion__id=7)
                    if 'idp' in request.GET:
                        data['person'] = Persona.objects.get(pk=int(request.GET['idp']))
                    else:
                        data['person'] = 0

                    # listacohortes = VariablesGlobales.objects.values_list('valor', flat=True).filter(variable='COHORTES_OFER')
                    data['maestrialist'] = MaestriasAdmision.objects.filter(status=True, carrera__coordinacion__id=7,
                                                                            id__in=variable_valor('MAESTRIAS_OFER'), cohortemaestria__procesoabierto=True).distinct()
                    return render(request, "comercial/addlead.html", data)
                except Exception as ex:
                    pass

            elif action == 'asignarasesor':
                try:
                    data['filtro'] = leads = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    form = InscripcionCohorteForm(initial={'persona': leads.inscripcionaspirante.persona.nombre_completo_inverso,
                                                            'maestria': leads.cohortes.maestriaadmision.descripcion,
                                                            'cohorte': leads.cohortes.descripcion,
                                                            'asesoractual': leads.asesor.persona.nombre_completo_inverso if leads.asesor else 'NINGUNO'
                                                           })
                    form.fields['asesor'].queryset = AsesorComercial.objects.filter(status=True, activo=True, asesormeta__status=True, asesormeta__cohorte__id=leads.cohortes.id).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres').distinct()
                    data['form2'] = form
                    data['action'] = 'asignarasesor'
                    template = get_template('comercial/modal/asignarasesor.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'asignarterritorio':
                try:
                    data['filtro'] = asesor = AsesorComercial.objects.get(pk=int(request.GET['id']))
                    form = AsignarTerritorioForm(initial={'asesor': asesor.persona.nombre_completo_inverso})
                    data['form2'] = form
                    data['action'] = 'asignarterritorio'
                    template = get_template('comercial/modal/addterritorio.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'configuracionmetas':
                try:
                    data['title'] = u'Configuracion Metas'
                    data['asesor'] = asesor = AsesorComercial.objects.get(pk=int(request.GET['id']), status=True)

                    # data['asesormetas'] = AsesorMeta.objects.filter(status=True, asesor_id=asesor.id).order_by('-fecha_creacion')

                    filtro = Q(status=True, asesor_id=asesor.id)

                    search = None
                    url_vars = ' '

                    if 'search' in request.GET:
                        search = request.GET['search']

                    if search:
                        data['search'] = search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(cohorte__descripcion__icontains=search) |
                                               Q(cohorte___maestriaadmision__descripcion__icontains=search))
                            url_vars += "&search={}".format(search)


                    metas = AsesorMeta.objects.filter(status=True, asesor_id=asesor.id).order_by('-fecha_creacion')

                    paging = MiPaginador(metas, 5)
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
                    data['asesormetas'] = page.object_list
                    data['search'] = search if search else ""
                    return render(request, "comercial/configuracionmetas.html", data)
                except Exception as ex:
                    pass

            elif action == 'metasmensuales':
                try:
                    data['title'] = u'Metas mensuales designadas por experta de comercialización'
                    request.session['viewactive'] = 18
                    aa = datetime.now().date().year
                    ma = datetime.now().date().month

                    search = request.GET.get('s', None)
                    ide = request.GET.get('ide', '3')
                    idanio = request.GET.get('idanio', aa)
                    idmes = request.GET.get('idmes', ma)

                    url_vars = '&action=metasmensuales'

                    filtro = Q(status=True)

                    if search:
                        data['search'] = search
                        filtro = filtro & (Q(descripcion__icontains=search))
                        url_vars += "&search={}".format(search)

                    if int(idanio):
                        if int(idanio) > 0:
                            data['idanio'] = int(idanio)
                            url_vars += f"&idanio={idanio}"

                    if int(idmes):
                        if int(idmes) > 0:
                            data['idmes'] = int(idmes)
                            url_vars += f"&idmes={idmes}"


                    if int(ide):
                        if int(ide) == 1:
                            filtro = filtro & (Q(cohortemaestria__procesoabierto=True))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 2:
                            filtro = filtro & (Q(cohortemaestria__procesoabierto=False))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 3:
                            query2 = MaestriasAdmision.objects.filter(filtro).order_by('-id')
                            li = []
                            for que in query2:
                                if que.ofertada():
                                  li.append(que.id)
                            filtro = filtro & (Q(id__in=li))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 4:
                            query2 = MaestriasAdmision.objects.filter(filtro).order_by('-id')
                            li = []
                            for que in query2:
                                if not que.ofertada():
                                  li.append(que.id)
                            filtro = filtro & (Q(id__in=li))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"

                    query = MaestriasAdmision.objects.filter(filtro).order_by('-id')

                    paging = MiPaginador(query, 25)
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
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data['maestrias'] = page.object_list
                    data['eTotal'] = query.count()
                    data['eAbiertas'] = CohorteMaestria.objects.filter(status=True, procesoabierto=True, maestriaadmision__id__in=query.values_list('id', flat=True)).count()
                    data['eCerradas'] = CohorteMaestria.objects.filter(status=True, procesoabierto=False, maestriaadmision__id__in=query.values_list('id', flat=True)).count()
                    data['cAsesores'] = AsesorComercial.objects.filter(status=True, rol__id__in=[1, 6], activo=True).count()
                    data['eAnios'] = InscripcionCohorte.objects.values_list('fecha_creacion__year', flat=True).order_by('fecha_creacion__year').distinct()
                    return render(request, "comercial/metasmensuales.html", data)
                except Exception as ex:
                    pass

            elif action == 'mismetas':
                try:
                    data['title'] = u'Mis metas'
                    request.session['viewactive'] = 7
                    data['asesor'] = asesor = AsesorComercial.objects.get(status=True, persona_id=persona.id)

                    aa = datetime.now().date().year
                    ma = datetime.now().date().month
                    pendientes = porcentaje = 0
                    idanio = request.GET.get('idanio', str(aa))
                    idmes = request.GET.get('idmes', str(ma))
                    ide = request.GET.get('ide', '0')
                    search = request.GET.get('s', None)
                    url_vars = '&action=mismetas'

                    filtro = Q(status=True, asesormeta__asesor__id=asesor.id)

                    if search:
                        data['search'] = search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & Q(asesormeta__maestria__descripcion__icontains=search)
                            url_vars += "&s={}".format(search)

                    if int(idanio):
                        if int(idanio) > 0:
                            data['idanio'] = int(idanio)
                            filtro = filtro & Q(inicio__year=int(idanio))
                            url_vars += f"&idanio={idanio}"

                    if int(idmes):
                        if int(idmes) > 0:
                            data['idmes'] = int(idmes)
                            filtro = filtro & Q(inicio__month=int(idmes))
                            url_vars += f"&idmes={idmes}"

                    if int(ide):
                        if int(ide) == 1:
                            lista =[]
                            metasp = DetalleAsesorMeta.objects.filter(filtro).order_by('-fecha_creacion')

                            for met in metasp:
                                if met.estado_meta():
                                    lista.append(met.id)

                            filtro = filtro & (Q(id__in=lista))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 2:
                            lista = []
                            metasp = DetalleAsesorMeta.objects.filter(filtro).order_by('-fecha_creacion')

                            for met in metasp:
                                if not met.estado_meta():
                                    lista.append(met.id)

                            filtro = filtro & (Q(id__in=lista))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"

                    metas = DetalleAsesorMeta.objects.filter(filtro).order_by('-fecha_creacion')
                    paging = MiPaginador(metas, 25)
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
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["metas"] = page.object_list
                    data['eMetas'] = total = DetalleAsesorMeta.objects.filter(status=True, inicio__month=idmes, inicio__year=idanio, asesormeta__asesor=asesor).aggregate(total=Sum('cantidad'))['total']
                    data['eFacturadas'] = VentasProgramaMaestria.objects.filter(status=True, facturado=True, fecha__month=idmes, fecha__year=idanio, asesor=asesor).count()
                    data['eReportadas'] = VentasProgramaMaestria.objects.filter(status=True, facturado=False, fecha__month=idmes, fecha__year=idanio, asesor=asesor).count()
                    data['eRechazadas'] = VentasProgramaMaestria.objects.filter(status=True, valida=False, fecha__month=idmes, fecha__year=idanio, asesor=asesor).count()
                    data['eValidas'] = validas = VentasProgramaMaestria.objects.filter(status=True, valida=True, fecha__month=idmes, fecha__year=idanio, asesor=asesor).count()
                    if validas > 0 and total > 0:
                        tot = (validas / total) * 100
                        porcentaje = Decimal(null_to_decimal(tot)).quantize(Decimal('.01'))
                    else:
                        porcentaje = 0

                    if validas > total:
                        pendientes = 0
                    else:
                        pendientes = total - validas
                    data['ePendientes'] = pendientes
                    data['ePorcentaje'] = porcentaje
                    data['eAnios'] = InscripcionCohorte.objects.values_list('fecha_creacion__year', flat=True).order_by('fecha_creacion__year').distinct()
                    return render(request, "comercial/mismetas.html", data)
                except Exception as ex:
                    pass

            elif action == 'misnotificaciones':
                try:
                    data['title'] = u'Mis notificaciones'
                    request.session['viewactive'] = 8

                    if persona.es_asesor_financiamiento():
                        data['asesor'] = asesor = AsesorComercial.objects.get(status=True, persona_id=persona.id)
                        filtro = Q(destinatario=persona, titulo__in=['Revisión de documento de Contrato de pago', 'CONTRATO FIRMADO',
                                                                                    'CONTRATO APROBADO Y LEGALIZADO', 'OFICIO DE TERMINACIÓN DE CONTRATO FIRMADO',
                                                                                     'OFICIO DE TERMINACIÓN DE CONTRATO APROBADO', 'OFICIO DE TERMINACIÓN DE CONTRATO RECHAZADO'])
                    elif persona.es_asesor():
                        data['asesor'] = asesor = AsesorComercial.objects.get(status=True, persona_id=persona.id)
                        filtro = Q(destinatario=asesor.persona, titulo__in=['REQUISITO DE ADMISIÓN RECHAZADO', 'VENTA REPORTADA',
                                'VENTA RECHAZADA', 'REQUISITO DE ADMISIÓN SUBIDO', 'COMPROBANTE DE PAGO RECHAZADO', 'SUBIÓ TODOS LOS REQUISITOS DE ADMISIÓN',
                                'POSTULANTE ADMITIDO', 'REQUISITOS DE FINANCIAMIENTO APROBADOS', 'CONTRATO FIRMADO Y APROBADO', 'CONTRATO FIRMADO',
                                                                                            'CONTRATO APROBADO Y LEGALIZADO', 'OFICIO DE TERMINACIÓN DE CONTRATO FIRMADO',
                                                                                            'OFICIO DE TERMINACIÓN DE CONTRATO APROBADO', 'OFICIO DE TERMINACIÓN DE CONTRATO RECHAZADO'])
                    else:
                        filtro = Q(destinatario=persona, titulo__in=['RESERVACIÓN DE PROSPECTO', 'RESERVACIÓN DE PROSPECTO DE TERRITORIO'])

                    search = request.GET.get('s', None)
                    url_vars = '&action=misnotificaciones'

                    if search:
                        data['search'] = search
                        filtro = filtro & (Q(titulo__icontains=search) |
                                           Q(cuerpo__icontains=search))
                        url_vars += "&s={}".format(search)

                    notificaciones = Notificacion.objects.filter(filtro).order_by('-fecha_creacion')

                    paging = MiPaginador(notificaciones, 20)
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
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["notificaciones"] = page.object_list
                    return render(request, "comercial/notificacionesasesor.html", data)
                except Exception as ex:
                    pass

            elif action == 'verasignaciones':
                try:
                    data['title'] = u'Asignaciones de maestrías'
                    data['asesor'] = asesor = AsesorComercial.objects.get(id=int(request.GET['id']))
                    url_vars = '&action=verasignaciones&id=' + str(asesor.id)

                    search = request.GET.get('s', None)

                    filtro1 = Q(asesor=asesor, status=True, maestria__isnull=False)

                    filtro2 = Q(status=True)

                    if search:
                        data['search'] = search
                        filtro1 = filtro1 & (Q(maestria__descripcion__icontains=search))
                        filtro2 = filtro2 & (Q(descripcion__icontains=search))
                        url_vars += "&s={}".format(search)

                    idm = AsesorMeta.objects.filter(asesor=asesor, status=True, maestria__isnull=False).order_by('maestria__id').values_list('maestria__id', flat=True).distinct()
                    data['maestrias'] = AsesorMeta.objects.filter(filtro1).order_by('-maestria__id').distinct()
                    data['nomaestrias'] = MaestriasAdmision.objects.filter(filtro2).exclude(id__in=idm).order_by('-id')
                    data["url_vars"] = url_vars
                    return render(request, "comercial/verasignados.html", data)
                except Exception as ex:
                    pass

            elif action == 'verasignacionesconvenio':
                try:
                    from posgrado.models import ConvenioAsesor, Convenio
                    data['title'] = u'Asignaciones de convenios'
                    data['asesor'] = asesor = AsesorComercial.objects.get(id=int(request.GET['id']))
                    url_vars = '&action=verasignacionesconvenio&id=' + str(asesor.id)

                    search = request.GET.get('s', None)

                    filtro1 = Q(asesor=asesor, status=True, convenio__isnull=False)

                    filtro2 = Q(status=True)

                    if search:
                        data['search'] = search
                        filtro1 = filtro1 & (Q(convenio__descripcion__icontains=search))
                        filtro2 = filtro2 & (Q(descripcion__icontains=search))
                        url_vars += "&s={}".format(search)

                    idc = ConvenioAsesor.objects.filter(asesor=asesor, status=True, convenio__isnull=False).order_by('convenio__id').values_list('convenio__id', flat=True).distinct()
                    data['convenios'] = ConvenioAsesor.objects.filter(filtro1).order_by('-convenio__id').distinct()
                    data['noconvenios'] = Convenio.objects.filter(filtro2).exclude(id__in=idc).order_by('-id')
                    data["url_vars"] = url_vars
                    return render(request, "comercial/verasignadosconvenios.html", data)
                except Exception as ex:
                    pass

            elif action == 'verasignacionescohorte':
                try:
                    data['title'] = u'Asignaciones de cohortes de maestrías'
                    data['asesor'] = asesor = AsesorComercial.objects.get(id=int(request.GET['id']))
                    url_vars = '&action=verasignacionescohorte&id=' + str(asesor.id)

                    search = request.GET.get('s', None)

                    filtro1 = Q(asesor=asesor, status=True, cohorte__isnull=False)

                    filtro2 = Q(status=True)

                    if search:
                        data['search'] = search
                        filtro1 = filtro1 & (Q(cohorte__maestriaadmision__descripcion__icontains=search))
                        filtro2 = filtro2 & (Q(maestriaadmision__descripcion__icontains=search))
                        url_vars += "&s={}".format(search)

                    idm = AsesorMeta.objects.filter(asesor=asesor, status=True, cohorte__isnull=False).order_by('cohorte__id').values_list('cohorte__id', flat=True).distinct()
                    data['cohortes'] = AsesorMeta.objects.filter(filtro1).order_by('-cohorte__id').distinct()
                    data['nocohortes'] = CohorteMaestria.objects.filter(filtro2).exclude(id__in=idm).order_by('-id')
                    data["url_vars"] = url_vars
                    return render(request, "comercial/verasignadoscohortes.html", data)
                except Exception as ex:
                    pass

            elif action == 'editmeta':
                try:
                    # data['asesor'] = asesor = AsesorComercial.objects.get(pk=int(request.GET['id']))
                    data['title'] = u'Editar Meta de Asesor Comercial'
                    data['asesor'] = asesorm = AsesorMeta.objects.get(pk=int(request.GET['id']))
                    data['idase'] = request.GET['idase']
                    form = AsesorMetaForm(initial={'asesor':asesorm.asesor.persona,
                                                   'maestria': asesorm.cohorte.maestriaadmision,
                                                   'cohorte': asesorm.cohorte,
                                                   'fechainicioins': asesorm.cohorte.fechainicioinsp,
                                                   'fechafinins': asesorm.cohorte.fechafininsp,
                                                   'cupo': asesorm.cohorte.cupodisponible,
                                                   'cuposlibres': asesorm.cohorte.cuposlibres,
                                                   'fechainiciometa':asesorm.fecha_inicio_meta,
                                                   'fechafinmeta':asesorm.fecha_fin_meta,
                                                   'meta':asesorm.meta})
                    data['form'] = form
                    return render(request, "comercial/verasignadoscohortes.html", data)
                except Exception as ex:
                    pass

            elif action == 'ventassupervisor':
                try:
                    request.session['viewactive'] = 17
                    data['title'] = u'Ventas obtenidas - general'
                    aa = datetime.now().date().year

                    search = request.GET.get('s', None)
                    idc = request.GET.get('idc', '0')
                    ide = request.GET.get('ide', '0')
                    ida = request.GET.get('ida', '0')
                    idas = request.GET.get('idas', '0')
                    idanio = request.GET.get('idanio', str(aa))
                    desde = request.GET.get('desde', '')
                    hasta = request.GET.get('hasta', '')
                    lista = []

                    url_vars = '&action=ventassupervisor'

                    filtro = Q(status=True)

                    if search:
                        data['search'] = search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(inscripcioncohorte__inscripcionaspirante__persona__apellido1__icontains=search) |
                                                     Q(inscripcioncohorte__inscripcionaspirante__persona__apellido2__icontains=search) |
                                                     Q(inscripcioncohorte__inscripcionaspirante__persona__nombres__icontains=search) |
                                                     Q(inscripcioncohorte__inscripcionaspirante__persona__cedula__icontains=search))
                            url_vars += "&s={}".format(search)
                        elif len(ss) == 2:
                            filtro = filtro & (Q(inscripcioncohorte__inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                              Q(inscripcioncohorte__inscripcionaspirante__persona__apellido2__icontains=ss[1]))
                            url_vars += "&s={}".format(ss)
                        else:
                            filtro = filtro & (Q(inscripcioncohorte__inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                                Q(inscripcioncohorte__inscripcionaspirante__persona__apellido2__icontains=ss[1]) &
                                               Q(inscripcioncohorte__inscripcionaspirante__persona__nombres__icontains=ss[2]))
                            url_vars += "&s={}".format(ss)

                    if int(idc):
                        filtro = filtro & (Q(inscripcioncohorte__cohortes__id=idc))
                        data['idc'] = int(idc)
                        url_vars += f"&idc={idc}"

                    if int(ide):
                        if int(ide) == 1:
                            filtro = filtro & (Q(inscripcioncohorte__formapagopac__id=1))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 2:
                            filtro = filtro & (Q(inscripcioncohorte__formapagopac__id=2))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 3:
                            filtro = filtro & (Q(mediopago='COMPROBANTE SUBIDO POR CONSULTA SALDOS'))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 4:
                            filtro = filtro & (Q(mediopago='PEDIDO ONLINE - TRANSFERENCIA'))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 5:
                            filtro = filtro & (Q(mediopago='PEDIDO ONLINE - TARJETA DE CRÉDITO'))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 6:
                            filtro = filtro & (Q(mediopago='PEDIDO ONLINE - DEPOSITO'))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 7:
                            filtro = filtro & (Q(mediopago='VENTA DIRECTA DE CAJA'))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 8:
                            filtro = filtro & (Q(mediopago='COMPROBANTE SUBIDO POR ASESOR'))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 9:
                            filtro = filtro & (Q(inscripcioncohorte__leaddezona=True))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 10:
                            filtro = filtro & (Q(inscripcioncohorte__es_becado=True))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 11:
                            idquery = CambioAdmitidoCohorteInscripcion.objects.filter(status=True).values_list('inscripcionCohorte__id', flat=True).order_by('inscripcionCohorte__id').distinct()
                            filtro = filtro & (Q(inscripcioncohorte__id__in=idquery))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"

                    if int(ida):
                        if int(ida) == 1:
                            filtro = filtro & (Q(facturado=True))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 2:
                            filtro = filtro & (Q(facturado=False))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 3:
                            filtro = filtro & (Q(valida=False))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"

                    if int(idanio):
                        if int(idanio) > 0:
                            data['idanio'] = int(idanio)
                            filtro = filtro & Q(fecha__year=int(idanio))
                            url_vars += f"&idanio={idanio}"

                    if int(idas):
                        filtro = filtro & (Q(asesor__id=idas))
                        data['idas'] = int(idas)
                        url_vars += f"&idas={idas}"

                    if desde and hasta:
                        data['desde'] = desde
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha__range=(desde, hasta))
                        url_vars += "&desde={}".format(desde)
                        url_vars += "&hasta={}".format(hasta)

                    elif desde:
                        data['desde'] = desde
                        filtro = filtro & Q(fecha__gte=desde)
                        url_vars += "&desde={}".format(hasta)

                    elif hasta:
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha__lte=hasta)
                        url_vars += "&hasta={}".format(hasta)

                    query = VentasProgramaMaestria.objects.filter(filtro).order_by('-fecha')

                    idcohortes = query.values_list('inscripcioncohorte__cohortes__id', flat=True).distinct().order_by('inscripcioncohorte__cohortes__id')

                    # if desde and hasta:
                    #     for idcohorte in idcohortes:
                    #         lista.append(idcohorte)

                    paging = MiPaginador(query, 25)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["listado"] = page.object_list
                    data['eCohortes'] = CohorteMaestria.objects.filter(status=True, id__in=idcohortes).order_by('-id').distinct()
                    data['idcohortes'] = list(idcohortes)
                    # data['idcohortes'] = lista
                    data['eFacturadas'] = query.filter(facturado=True).count()
                    data['eReportadas'] = query.filter(facturado=False).count()
                    data['eRechazadas'] = query.filter(valida=False).count()
                    data['eTotal'] = query.filter(valida=True).count()
                    data['eAnios'] = VentasProgramaMaestria.objects.values_list('fecha__year', flat=True).order_by('fecha__year').distinct()
                    data['eAsesores'] = AsesorComercial.objects.filter(status=True, rol__id__in=[1, 6]).order_by('id')
                    return render(request, "comercial/ventassupervisor.html", data)
                except Exception as ex:
                    pass

            elif action == 'historialasesor':
                try:
                    if 'id' in request.GET:
                        data['historialasesores'] = HistorialAsesor.objects.filter(inscripcion=request.GET['id'],
                                                                                      status=True)
                        template = get_template("comercial/historialasesor.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'historialfinanciamiento':
                try:
                    if 'id' in request.GET:
                        data['inscripcion'] = InscripcionCohorte.objects.get(pk=request.GET['id'], status=True)
                        data['historiales'] = DetalleAprobacionFormaPago.objects.filter(inscripcion=request.GET['id'],
                                                                                        status=True)
                        template = get_template("comercial/modal/historialfinanciamiento.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'historialreservacion':
                try:
                    if 'id' in request.GET:
                        data['inscripcion'] = InscripcionCohorte.objects.get(pk=request.GET['id'], status=True)
                        data['historiales'] = HistorialReservacionProspecto.objects.filter(inscripcion=request.GET['id'],
                                                                                        status=True)
                        template = get_template("comercial/modal/historialreservacion.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addobservacion':
                try:
                    inscripcion = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    data['id'] = id = int(request.GET['id'])
                    data['action'] = 'addobservacion'
                    form = HistorialRespuestaProspectoForm(initial={'prospecto':inscripcion.inscripcionaspirante.persona.nombre_completo_inverso()})
                    form.fields['tiporespuesta'].queryset = TipoRespuestaProspecto.objects.filter(status=True).exclude(id=1).order_by('id')
                    data['form2'] = form
                    template = get_template('comercial/modal/tiporespuesta.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'editventa':
                try:
                    venta = VentasProgramaMaestria.objects.get(pk=int(request.GET['id']))
                    data['id'] = id = int(request.GET['id'])
                    data['action'] = 'editventa'
                    form = VentasMaestriasForm(initial={'persona': venta.inscripcioncohorte.inscripcionaspirante.persona.nombre_completo_inverso(),
                                                        'maestria': venta.inscripcioncohorte.cohortes.maestriaadmision.descripcion,
                                                        'cohorte': venta.inscripcioncohorte.cohortes.descripcion,
                                                        'fecha': venta.fecha,
                                                        'facturado': venta.facturado,
                                                        'valida': venta.valida})
                    data['form2'] = form
                    template = get_template('comercial/modal/tiporespuesta.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'editmaestria':
                try:
                    from posgrado.forms import CambioMaestriaForm
                    data['id'] = id = int(request.GET['id'])
                    inscrito = InscripcionCohorte.objects.get(pk=id)
                    data['action'] = action
                    form = CambioMaestriaForm(initial={
                        'persona': inscrito.inscripcionaspirante.persona.nombre_completo_inverso(),
                        'maestria': inscrito.cohortes.maestriaadmision.descripcion,
                    })
                    form.fields['maestriacambio'].queryset = MaestriasAdmision.objects.filter(status=True, carrera__nombre__icontains=inscrito.cohortes.maestriaadmision.carrera.nombre).exclude(carrera=inscrito.cohortes.maestriaadmision.carrera).order_by('descripcion')
                    data['form2'] = form
                    template = get_template('comercial/modal/tiporespuesta.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result":False, 'message':str(ex)})

            elif action == 'verobservaciones':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = InscripcionCohorte.objects.get(pk=request.GET['id'])
                    data['detalle'] = filtro.historialrespuestaprospecto_set.all().order_by('pk')
                    template = get_template("comercial/modal/observacionatencion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'verhistorialcambio':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = InscripcionCohorte.objects.get(pk=request.GET['id'])
                    data['detalle'] = CambioAdmitidoCohorteInscripcion.objects.filter(status=True, inscripcionCohorte=filtro)
                    template = get_template("comercial/modal/verhistorialcambio.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'verdetalleventas':
                try:
                    data['id'] = ids = eval(request.GET['id'])
                    data['desde'] = desde = request.GET.get('desde', '')
                    data['hasta'] = hasta = request.GET.get('hasta', '')

                    data['cohortes'] = CohorteMaestria.objects.filter(status=True, id__in=ids).order_by('maestriaadmision__carrera__id')

                    data['eFacturadas'] = VentasProgramaMaestria.objects.filter(status=True, inscripcioncohorte__cohortes__id__in=ids, facturado=True, fecha__range=(desde, hasta)).count()
                    data['eReportadas'] = VentasProgramaMaestria.objects.filter(status=True, inscripcioncohorte__cohortes__id__in=ids, facturado=False, fecha__range=(desde, hasta)).count()
                    data['eRechazadas'] = VentasProgramaMaestria.objects.filter(status=True, inscripcioncohorte__cohortes__id__in=ids, valida=False, fecha__range=(desde, hasta)).count()
                    data['eValidas'] = VentasProgramaMaestria.objects.filter(status=True, inscripcioncohorte__cohortes__id__in=ids, valida=True, fecha__range=(desde, hasta)).count()
                    template = get_template("comercial/modal/verdetalleventascohorte.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'verseguimientolead':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = InscripcionCohorte.objects.get(pk=request.GET['id'])
                    template = get_template("comercial/modal/verseguimientolead.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'verdetalleaprobacion':
                try:
                    data['id'] = request.GET['id']
                    evidencia = 0
                    # data['filtro'] = filtro = InscripcionCohorte.objects.get(pk=request.GET['id'])
                    data['detalle'] = DetalleEvidenciaRequisitosAspirante.objects.filter(status=True, evidencia__id=int(request.GET['id']))
                    template = get_template("comercial/modal/verdetallerevision.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'verdetallecontratos':
                try:
                    contra = Contrato.objects.get(pk=int(request.GET['id']))
                    if 'espagare' in request.GET:
                        data['historiales'] = DetalleAprobacionContrato.objects.filter(status=True, contrato=contra, espagare=True).order_by('id')
                    else:
                        data['historiales'] = DetalleAprobacionContrato.objects.filter(status=True, contrato=contra, espagare=False).order_by('id')
                    data['contrato'] =contra
                    template=get_template('comercial/modal/verdetallecontratos.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'verdetalleconvenio':
                try:
                    from posgrado.models import EvidenciaRequisitoConvenio, DetalleEvidenciaRequisitoConvenio
                    econvenio = EvidenciaRequisitoConvenio.objects.get(pk=int(request.GET['id']))
                    data['historiales'] = DetalleEvidenciaRequisitoConvenio.objects.filter(status=True, evidenciarequisitoconvenio=econvenio).order_by('id')
                    data['econvenio'] =econvenio
                    template=get_template('comercial/modal/verdetalleconvenio.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'verobservacionescomprobante':
                try:
                    data['id'] = request.GET['id']
                    cursor = connections['epunemi'].cursor()

                    sql = """SELECT fecha_creacion, observacion, estados FROM sagest_detallecomprobantealumno  
                    WHERE comprobantes_id=%s AND status=TRUE; """ % (int(request.GET['id']))
                    cursor.execute(sql)

                    rows = cursor.fetchall()

                    data['detalles'] = rows
                    template = get_template("comercial/modal/obser_comp.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'vercomprobantespago':
                try:
                    data['inscrito'] = inscrito = InscripcionCohorte.objects.get(pk=request.GET['id'])
                    data['idv'] = int(request.GET['idv'])
                    data['title'] = u'Pedidos Online'
                    data['epunemi'] = inscrito.pedidos_epunemi()
                    return render(request, "comercial/comprobanteslead.html", data)
                except Exception as ex:
                    pass

            elif action == 'editmencion':
                try:
                    data['filtro'] = inscripcion = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    itine = None

                    if inscripcion.itinerario != 0:
                        itine = ItinerarioMallaEspecilidad.objects.get(status=True, itinerario=inscripcion.itinerario,
                                                                        malla__id=inscripcion.cohortes.maestriaadmision.carrera.malla().id)

                    form = MencionMaestriaForm(initial={'prospecto':inscripcion.inscripcionaspirante.persona.nombre_completo_inverso(),
                                                        'maestria':inscripcion.cohortes.maestriaadmision.descripcion,
                                                        'cohorte':inscripcion.cohortes.descripcion,
                                                        'mencion': itine if inscripcion.itinerario else ''})


                    form.fields['mencion'].queryset = ItinerarioMallaEspecilidad.objects.filter(status=True, malla__id=inscripcion.cohortes.maestriaadmision.carrera.malla().id).order_by('id')

                    data['form2'] = form
                    data['action'] = 'editmencion'
                    template = get_template('comercial/modal/mencionmaestria.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addreservacion':
                try:
                    inscripcion = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    data['id'] = id = int(request.GET['id'])
                    data['action'] = 'addreservacion'
                    form = ReservacionProspectoForm(initial={'prospecto': inscripcion.inscripcionaspirante.persona.nombre_completo_inverso()})
                    data['form2'] = form
                    template = get_template('comercial/modal/addreservacion.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'leadsregistrados':
                try:
                    data['title'] = u'Reservaciones de asesor'
                    data['asesor'] = asesor = AsesorComercial.objects.get(id=int(request.GET['id']))

                    url_vars = '&action=leadsregistrados&id=' + str(asesor.id)
                    search = request.GET.get('s', None)
                    ide = request.GET.get('ide', '0')

                    filtro = Q(status=True, persona__id=asesor.persona.id)


                    if search:
                        data['search'] = search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(inscripcion__inscripcionaspirante__persona__apellido1__icontains=search) |
                                                     Q(inscripcion__inscripcionaspirante__persona__apellido2__icontains=search) |
                                                     Q(inscripcion__inscripcionaspirante__persona__nombres__icontains=search) |
                                                     Q(inscripcion__inscripcionaspirante__persona__cedula__icontains=search))
                            url_vars += "&s={}".format(search)
                        elif len(ss) == 2:
                            filtro = filtro & (Q(inscripcion__inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                                     Q(inscripcion__inscripcionaspirante__persona__apellido2__icontains=ss[1]))
                            url_vars += "&s={}".format(ss)
                        else:
                            filtro = filtro & (Q(inscripcion__inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                                Q(inscripcion__inscripcionaspirante__persona__apellido2__icontains=ss[1]) &
                                               Q(inscripcion__inscripcionaspirante__persona__nombres__icontains=ss[2]))
                            url_vars += "&s={}".format(ss)

                    if int(ide):
                        if int(ide) == 1:
                            filtro = filtro & (Q(estado_asesor=1))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 2:
                            filtro = filtro & (Q(estado_asesor=2))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"

                    query = HistorialReservacionProspecto.objects.filter(filtro).order_by('-fecha_creacion')
                    paging = MiPaginador(query, 25)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["listado"] = page.object_list
                    data['eTotal'] = query.count()
                    return render(request, "comercial/leadsregistrados.html", data)
                except Exception as ex:
                    pass

            elif action == 'asignarmetasmensuales':
                try:
                    data['title'] = u'Asignar metas mensuales'
                    data['maestria'] = maestria = MaestriasAdmision.objects.get(status=True, id=int(request.GET['id']))

                    cab = AsesorMeta.objects.filter(status=True, maestria=maestria).values_list('id', flat=True)

                    search = request.GET.get('s', None)
                    idanio = request.GET.get('idanio', '0')
                    idmes = request.GET.get('idmes', '0')
                    ide = request.GET.get('ide', '0')

                    url_vars = '&action=asignarmetasmensuales&id=' + str(maestria.id) + "&idmes=" + str(idmes) + "&idanio=" + str(idanio)

                    filtro = Q(status=True, asesormeta__id__in=cab, inicio__month=int(idmes), inicio__year=int(idanio))

                    primer_dia, ultimo_dia = obtener_primer_ultimo_dia_del_mes(int(idanio), int(idmes))

                    if not CuposMaestriaMes.objects.filter(status=True, inicio__month=idmes, inicio__year=idanio,
                                                           maestria=maestria).exists():
                        cuposmes = CuposMaestriaMes(maestria=maestria,
                                                 inicio=primer_dia.strftime("%Y-%m-%d"),
                                                 fin=ultimo_dia.strftime("%Y-%m-%d"),
                                                 cuposlibres=0,
                                                 estado=1)
                        cuposmes.save(request)
                    else:
                        cuposmes = CuposMaestriaMes.objects.get(status=True, inicio__month=idmes, inicio__year=idanio, maestria=maestria)

                    data['cuposmes'] = cuposmes
                    data['primer_dia'] = primer_dia.strftime("%d-%m-%Y")
                    data['ultimo_dia'] = ultimo_dia.strftime("%d-%m-%Y")

                    if search:
                        data['search'] = search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(asesormeta__asesor__persona__apellido1__icontains=search) |
                                                     Q(asesormeta__asesor__persona__apellido2__icontains=search) |
                                                     Q(asesormeta__asesor__persona__nombres__icontains=search) |
                                                     Q(asesormeta__asesor__persona__cedula__icontains=search))
                            url_vars += "&s={}".format(search)
                        elif len(ss) == 2:
                            filtro = filtro & (Q(asesormeta__asesor__persona__apellido1__icontains=ss[0]) &
                                                     Q(asesormeta__asesor__persona__apellido2__icontains=ss[1]))
                            url_vars += "&s={}".format(ss)
                        else:
                            filtro = filtro & (Q(asesormeta__asesor__persona__apellido1__icontains=ss[0]) &
                                                Q(asesormeta__asesor__persona__apellido2__icontains=ss[1]) &
                                               Q(asesormeta__asesor__persona__nombres__icontains=ss[2]))
                            url_vars += "&s={}".format(ss)

                    if int(ide):
                        if int(ide) == 1:
                            filtro = filtro & (Q(asesormeta__asesor__activo=True))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 2:
                            filtro = filtro & (Q(asesormeta__asesor__activo=False))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 3:
                            filtro = filtro & (Q(cantidad=0))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 4:
                            filtro = filtro & (Q(estado=2))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 5:
                            filtro = filtro & (Q(estado=1))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"

                    query = DetalleAsesorMeta.objects.filter(filtro).order_by('asesormeta__asesor__persona__apellido1',
                                                                              'asesormeta__asesor__persona__apellido2', 'asesormeta__asesor__persona__nombres')
                    paging = MiPaginador(query, query.count() if query.count() > 0 else 1)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["listado"] = page.object_list
                    data['eTotal'] = query.count()
                    data['idmes'] = int(request.GET['idmes'])
                    data['idanio'] = int(request.GET['idanio'])
                    return render(request, "comercial/asignarmetasmensuales.html", data)
                except Exception as ex:
                    pass

            elif action == 'reservacionprospectos':
                try:
                    puede_realizar_accion(request, 'posgrado.puede_reservar_prospectos')
                    request.session['viewactive'] = 5
                    data['title'] = u'Reservación de prospectos'
                    data['asesor'] = asesor = AsesorComercial.objects.get(persona__id=persona.id, status=True, activo=True)
                    idcohortes = AsesorMeta.objects.filter(status=True, asesor__id=asesor.id).values_list('cohorte__id', flat=True)

                    filtro = Q(status=True, persona__id=persona.id)

                    search = request.GET.get('s', None)
                    url_vars = '&action=reservacionprospectos'

                    if search:
                        filtro = Q(status=True, cohortes__maestriaadmision__carrera__coordinacion__id=7, cohortes__id__in=idcohortes)

                        data['search'] = search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=search) |
                                               Q(inscripcionaspirante__persona__apellido2__icontains=search) |
                                               Q(inscripcionaspirante__persona__nombres__icontains=search) |
                                               Q(inscripcionaspirante__persona__cedula__icontains=search))
                            url_vars += "&s={}".format(search)
                        elif len(ss) == 2:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                               Q(inscripcionaspirante__persona__apellido2__icontains=ss[1]))
                            url_vars += "&s={}".format(ss)
                        else:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                               Q(inscripcionaspirante__persona__apellido2__icontains=ss[1]) &
                                               Q(inscripcionaspirante__persona__nombres__icontains=ss[2]))
                            url_vars += "&s={}".format(ss)

                        leads = InscripcionCohorte.objects.filter(filtro).order_by('-fecha_creacion')
                    else:
                        reservaciones = HistorialReservacionProspecto.objects.filter(filtro).values_list('inscripcion__id', flat=True).order_by('-fecha_creacion')

                        leads = InscripcionCohorte.objects.filter(id__in=reservaciones).order_by('-fecha_creacion')

                    paging = MiPaginador(leads, 25)
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
                    data['listado'] = page.object_list
                    data['search'] = search if search else ""
                    data['totalleads'] = leads.count()
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    return render(request, "comercial/reservacionprospectos.html", data)
                except Exception as ex:
                    pass

            elif action == 'prospectosmaestrias':
                try:
                    data['title'] = u'Reservación de prospectos'
                    data['asesor'] = asesor = AsesorComercial.objects.get(persona__id=persona.id, status=True)
                    idcohortes = AsesorMeta.objects.filter(status=True, asesor__id=asesor.id).values_list('cohorte__id', flat=True)
                    filtro = Q(status=True, id__in=idcohortes)

                    search = None
                    url_vars = ' '

                    if 'search' in request.GET:
                        search = request.GET['search']

                    if search:
                        data['search'] = search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(descripcion__icontains=search) |
                                               Q(maestriaadmision__descripcion__icontains=search))
                            url_vars += "&search={}".format(search)

                    # cohortes = CohorteMaestria.objects.filter(filtro).order_by('asesormeta__fecha_creacion')
                    cohortes = CohorteMaestria.objects.filter(filtro)

                    paging = MiPaginador(cohortes, 10)
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
                    data['cohortesasignadas'] = page.object_list
                    data['search'] = search if search else ""
                    return render(request, "comercial/prospectosmaestrias.html", data)
                except Exception as ex:
                    pass

            elif action == 'vermaestrantes':
                try:
                    data['title'] = u'Listado de Maestrantes Obtenidos'
                    data['asesormeta'] = meta = AsesorMeta.objects.get(status=True, pk=int(request.GET['id']))
                    ventas = meta.listado_maestrantes()
                    data['asesor'] = AsesorComercial.objects.get(asesormeta__id=int(request.GET['id']))

                    paging = MiPaginador(ventas, 25)
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
                    data['listadomaestrantes'] = page.object_list
                    return render(request, "comercial/vermaestrantes.html", data)
                except Exception as ex:
                    pass

            elif action == 'ventasobtenidas':
                try:
                    request.session['viewactive'] = 2
                    data['title'] = u'Ventas obtenidas'
                    aa = datetime.now().date().year

                    search = request.GET.get('s', None)
                    idc = request.GET.get('idc', '0')
                    ide = request.GET.get('ide', '0')
                    ida = request.GET.get('ida', '0')
                    idanio = request.GET.get('idanio', str(aa))
                    desde = request.GET.get('desde', '')
                    hasta = request.GET.get('hasta', '')

                    url_vars = '&action=ventasobtenidas'

                    filtro = Q(status=True, asesor__persona=persona)

                    if search:
                        data['search'] = search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(inscripcioncohorte__inscripcionaspirante__persona__apellido1__icontains=search) |
                                                     Q(inscripcioncohorte__inscripcionaspirante__persona__apellido2__icontains=search) |
                                                     Q(inscripcioncohorte__inscripcionaspirante__persona__nombres__icontains=search) |
                                                     Q(inscripcioncohorte__inscripcionaspirante__persona__cedula__icontains=search))
                            url_vars += "&s={}".format(search)
                        elif len(ss) == 2:
                            filtro = filtro & (Q(inscripcioncohorte__inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                              Q(inscripcioncohorte__inscripcionaspirante__persona__apellido2__icontains=ss[1]))
                            url_vars += "&s={}".format(ss)
                        else:
                            filtro = filtro & (Q(inscripcioncohorte__inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                                Q(inscripcioncohorte__inscripcionaspirante__persona__apellido2__icontains=ss[1]) &
                                               Q(inscripcioncohorte__inscripcionaspirante__persona__nombres__icontains=ss[2]))
                            url_vars += "&s={}".format(ss)

                    if int(idc):
                        filtro = filtro & (Q(inscripcioncohorte__cohortes__id=idc))
                        data['idc'] = int(idc)
                        url_vars += f"&idc={idc}"

                    if int(ide):
                        if int(ide) == 1:
                            filtro = filtro & (Q(inscripcioncohorte__formapagopac__id=1))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 2:
                            filtro = filtro & (Q(inscripcioncohorte__formapagopac__id=2))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 3:
                            filtro = filtro & (Q(mediopago='COMPROBANTE SUBIDO POR CONSULTA SALDOS'))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 4:
                            filtro = filtro & (Q(mediopago='PEDIDO ONLINE - TRANSFERENCIA'))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 5:
                            filtro = filtro & (Q(mediopago='PEDIDO ONLINE - TARJETA DE CRÉDITO'))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 6:
                            filtro = filtro & (Q(mediopago='PEDIDO ONLINE - DEPOSITO'))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 7:
                            filtro = filtro & (Q(mediopago='VENTA DIRECTA DE CAJA'))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 8:
                            filtro = filtro & (Q(mediopago='COMPROBANTE SUBIDO POR ASESOR'))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 9:
                            filtro = filtro & (Q(inscripcioncohorte__es_becado=True))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 10:
                            idquery = CambioAdmitidoCohorteInscripcion.objects.filter(status=True).values_list('inscripcionCohorte__id', flat=True).order_by('inscripcionCohorte__id').distinct()
                            filtro = filtro & (Q(inscripcioncohorte__id__in=idquery))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"

                    if int(ida):
                        if int(ida) == 1:
                            filtro = filtro & (Q(facturado=True))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 2:
                            filtro = filtro & (Q(facturado=False))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 3:
                            filtro = filtro & (Q(valida=False))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"

                    if int(idanio):
                        if int(idanio) > 0:
                            data['idanio'] = int(idanio)
                            filtro = filtro & Q(fecha__year=int(idanio))
                            url_vars += f"&idanio={idanio}"

                    if desde and hasta:
                        data['desde'] = desde
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha__range=(desde, hasta))
                        url_vars += "&desde={}".format(desde)
                        url_vars += "&hasta={}".format(hasta)

                    elif desde:
                        data['desde'] = desde
                        filtro = filtro & Q(fecha__gte=desde)
                        url_vars += "&desde={}".format(hasta)

                    elif hasta:
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha__lte=hasta)
                        url_vars += "&hasta={}".format(hasta)

                    query = VentasProgramaMaestria.objects.filter(filtro).order_by('-fecha')

                    paging = MiPaginador(query, 25)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["listado"] = page.object_list
                    data['eCohortes'] = CohorteMaestria.objects.filter(status=True).order_by('-id').distinct()
                    data['eFacturadas'] = query.filter(facturado=True).count()
                    data['eReportadas'] = query.filter(facturado=False).count()
                    data['eRechazadas'] = query.filter(valida=False).count()
                    data['eTotal'] = query.filter(valida=True).count()
                    data['eAnios'] = VentasProgramaMaestria.objects.values_list('fecha__year', flat=True).order_by('fecha__year').distinct()
                    return render(request, "comercial/vermaestrantesase.html", data)
                except Exception as ex:
                    pass

            elif action == 'leadsdesactivados':
                try:
                    request.session['viewactive'] = 3
                    data['title'] = u'Leads desactivados'
                    search = request.GET.get('s', None)
                    idc = request.GET.get('idc', '0')
                    ide = request.GET.get('ide', '0')
                    ida = request.GET.get('ida', '0')
                    desde = request.GET.get('desde', '')
                    hasta = request.GET.get('hasta', '')

                    url_vars = '&action=leadsdesactivados'
                    filtro = Q(status=False, cohortes__maestriaadmision__carrera__coordinacion__id=7, asesor__persona=persona)

                    if search:
                        data['search'] = search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=search) |
                                                     Q(inscripcionaspirante__persona__apellido2__icontains=search) |
                                                     Q(inscripcionaspirante__persona__nombres__icontains=search) |
                                                     Q(inscripcionaspirante__persona__cedula__icontains=search))
                            url_vars += "&s={}".format(search)
                        elif len(ss) == 2:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                                     Q(inscripcionaspirante__persona__apellido2__icontains=ss[1]))
                            url_vars += "&s={}".format(ss)
                        else:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                                Q(inscripcionaspirante__persona__apellido2__icontains=ss[1]) &
                                               Q(inscripcionaspirante__persona__nombres__icontains=ss[2]))
                            url_vars += "&s={}".format(ss)


                    if int(idc):
                        filtro = filtro & (Q(cohortes__id=int(idc)))
                        data['idc'] = int(idc)
                        url_vars += f"&idc={idc}"

                    if int(ide):
                        if int(ide) == 4:
                            filtro = filtro & (Q(formapagopac__id=1))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 5:
                            filtro = filtro & (Q(formapagopac__id=2))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 6:
                            idquery = CambioAdmitidoCohorteInscripcion.objects.filter(status=True).values_list('inscripcionCohorte__id', flat=True).order_by('inscripcionCohorte__id').distinct()
                            filtro = filtro & (Q(id__in=idquery))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        else:
                            filtro = filtro & (Q(estado_aprobador=int(ide)))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"

                    if int(ida):
                        if int(ida) == 1:
                            filtro = filtro & (Q(tiporespuesta__isnull=True))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        else:
                            filtro = filtro & (Q(tiporespuesta__id=int(ida)))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"

                    if desde and hasta:
                        data['desde'] = desde
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha_creacion__date__range=(desde, hasta))
                        url_vars += "&desde={}".format(desde)
                        url_vars += "&hasta={}".format(hasta)

                    elif desde:
                        data['desde'] = desde
                        filtro = filtro & Q(fecha_creacion__date__gte=desde)
                        url_vars += "&desde={}".format(hasta)

                    elif hasta:
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha_creacion__date__lte=hasta)
                        url_vars += "&hasta={}".format(hasta)

                    query = InscripcionCohorte.objects.filter(filtro).order_by('-fecha_creacion')
                    paging = MiPaginador(query, 20)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["listado"] = page.object_list
                    data['eCohortes'] = CohorteMaestria.objects.filter(status=True).order_by('-id').distinct()
                    data['eAsignados'] = query.count()
                    data['eAtendidos'] = query.filter(tiporespuesta__isnull=False).count()
                    data['eNoAtendidos'] = query.filter(tiporespuesta__isnull=True).count()
                    data['eTiposrespuestas'] = TipoRespuestaProspecto.objects.filter(status=True).order_by('id')
                    return render(request, "comercial/leadsdesactivados.html", data)
                except Exception as ex:
                    pass

            elif action == 'leadsporpreaprobar':
                try:
                    request.session['viewactive'] = 4
                    data['title'] = u'Leads pendientes de pre-aprobar'
                    search = request.GET.get('s', None)
                    idc = request.GET.get('idc', '0')
                    ide = request.GET.get('ide', '0')
                    ida = request.GET.get('ida', '1')
                    desde = request.GET.get('desde', '')
                    hasta = request.GET.get('hasta', '')

                    url_vars = '&action=leadsporpreaprobar'
                    filtro = Q(status=True, cohortes__maestriaadmision__carrera__coordinacion__id=7, asesor__persona=persona)

                    if search:
                        data['search'] = search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=search) |
                                                     Q(inscripcionaspirante__persona__apellido2__icontains=search) |
                                                     Q(inscripcionaspirante__persona__nombres__icontains=search) |
                                                     Q(inscripcionaspirante__persona__cedula__icontains=search))
                            url_vars += "&s={}".format(search)
                        elif len(ss) == 2:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                                     Q(inscripcionaspirante__persona__apellido2__icontains=ss[1]))
                            url_vars += "&s={}".format(ss)
                        else:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                                Q(inscripcionaspirante__persona__apellido2__icontains=ss[1]) &
                                               Q(inscripcionaspirante__persona__nombres__icontains=ss[2]))
                            url_vars += "&s={}".format(ss)


                    if int(idc):
                        filtro = filtro & (Q(cohortes__id=int(idc)))
                        data['idc'] = int(idc)
                        url_vars += f"&idc={idc}"

                    if int(ide):
                        if int(ide) == 4:
                            filtro = filtro & (Q(formapagopac__id=1))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 5:
                            filtro = filtro & (Q(formapagopac__id=2))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        else:
                            filtro = filtro & (Q(estado_aprobador=int(ide)))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"

                    if int(ida):
                        if int(ida) == 1:
                            filtro = filtro & (Q(todosubido=True, estado_aprobador=1, preaprobado=False, tienerechazo=False))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 2:
                            filtro = filtro & (Q(todosubido=True, preaprobado=True, tienerechazo=False))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 3:
                            filtro = filtro & (Q(todosubido=False, estado_aprobador=1, preaprobado=False, tienerechazo=True))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"

                    if desde and hasta:
                        data['desde'] = desde
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha_creacion__date__range=(desde, hasta))
                        url_vars += "&desde={}".format(desde)
                        url_vars += "&hasta={}".format(hasta)

                    elif desde:
                        data['desde'] = desde
                        filtro = filtro & Q(fecha_creacion__date__gte=desde)
                        url_vars += "&desde={}".format(hasta)

                    elif hasta:
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha_creacion__date__lte=hasta)
                        url_vars += "&hasta={}".format(hasta)

                    query = InscripcionCohorte.objects.filter(filtro).exclude(tiporespuesta__id=6).order_by('-fecha_creacion')
                    paging = MiPaginador(query, 20)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["listado"] = page.object_list
                    data['eCohortes'] = CohorteMaestria.objects.filter(status=True).order_by('-id').distinct()
                    data['ePorpreaprobar'] = query.count()
                    return render(request, "comercial/leadsporpreaprobar.html", data)
                except Exception as ex:
                    pass

            elif action == 'reportesasesores':
                try:
                    request.session['viewactive'] = 6
                    data['title'] = u'Reportes'
                    data['eTiposrespuestas'] = TipoRespuestaProspecto.objects.filter(status=True).order_by('id')
                    data['eAsesores'] = AsesorComercial.objects.filter(status=True, rol__id__in=[1, 6]).order_by('id')
                    data['eAnios'] = VentasProgramaMaestria.objects.values_list('fecha__year', flat=True).order_by('-fecha__year').distinct()
                    data['eAniosG'] = Graduado.objects.values_list('fechagraduado__year', flat=True).filter(fechagraduado__isnull=False).order_by('-fechagraduado__year').distinct()
                    return render(request, "comercial/reportesasesores.html", data)
                except Exception as ex:
                    pass

            elif action == 'reasignacionmasiva':
                try:
                    ids = None
                    if 'ids' in request.GET:
                        ids = request.GET['ids']
                    data['ids'] = ids
                    if not ids == '':
                        data['cantidad'] = len(ids.split(','))
                        idcohortes = InscripcionCohorte.objects.filter(status=True, id__in=ids.split(',')).values_list('cohortes__id', flat=True).order_by('cohortes__id').distinct()

                        listacoho = []
                        cohortes = CohorteMaestria.objects.filter(status=True, id__in=idcohortes).distinct()
                        for coho in cohortes:
                            ins = InscripcionCohorte.objects.filter(status=True, id__in=ids.split(','), cohortes=coho).distinct().count()
                            a = {'cohorte':coho, 'cant':ins}
                            listacoho.append(a)

                        data['cohortes'] = listacoho

                        data['cancohortes'] = cohortes.count()
                        asesores = AsesorComercial.objects.filter(status=True, activo=True)

                        ases = []
                        for asesor in asesores:
                            can = len(idcohortes)
                            metas = AsesorMeta.objects.filter(status=True, asesor=asesor, cohorte__id__in=idcohortes).distinct().count()
                            if metas == can:
                                ases.append(asesor.id)

                        data['action'] = 'reasignacionmasiva'
                        form = ReasignarMasivoForm()
                        form.fields['asesor'].queryset = AsesorComercial.objects.filter(status=True, id__in=ases).order_by('id')
                        data['form2'] = form
                        template = get_template('comercial/leadsmasivo.html')
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, "mensaje": 'Por favor, seleccione al menos un lead'})
                except Exception as ex:
                    mensaje = 'Intentelo mas tarde'
                    return JsonResponse({"result": False, "mensaje": mensaje})

            elif action == 'reasignacionmasivareserva':
                try:
                    ids = None
                    if 'ids' in request.GET:
                        ids = request.GET['ids']
                    data['ids'] = ids
                    if not ids == '':
                        data['cantidad'] = len(ids.split(','))

                        data['asesor'] = AsesorComercial.objects.get(status=True, id=request.GET['id'])
                        form = ReasignarMasivoForm()
                        form.no_asesor()
                        data['form2'] = form
                        data['action'] = 'reasignacionmasivareserva'
                        template = get_template('comercial/leadsreserva.html')
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, "mensaje": 'Por favor, seleccione al menos un lead'})
                except Exception as ex:
                    mensaje = 'Intentelo mas tarde'
                    return JsonResponse({"result": False, "mensaje": mensaje})

            elif action == 'addtitulacionpos':
                try:
                    data['title'] = u'Adicionar titulación'
                    # data['carrera'] = carrera = Carrera.objects.get(pk=request.GET['idcarrera'])
                    form = TitulacionPersonaAdmisionPosgradoForm()
                    form.adicionar()
                    data['form2'] = form
                    template = get_template("comercial/modal/addtitulacionpos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'listcampoespecifico':
                try:
                    campoamplio = request.GET.get('campoamplio')
                    listcampoamplio = campoamplio
                    if len(campoamplio) > 1:
                        listcampoamplio = campoamplio.split(',')
                    querybase = SubAreaConocimientoTitulacion.objects.filter(status=True, areaconocimiento__in=listcampoamplio).order_by('codigo')
                    if 'q' in request.GET:
                        q = request.GET['q'].upper().strip()
                        if q != 'UNDEFINED':
                            querybase = querybase.filter((Q(nombre__icontains=q) | Q(codigo__icontains=q))).distinct()[:30]
                    data = {"result": "ok", "results": [{"id": x.id, "idca": x.areaconocimiento.id, "name": "{} - {}".format(x.codigo, x.nombre)} for x in querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'listcampodetallado':
                try:
                    campoespecifico = request.GET.get('campoespecifico')
                    listcampoespecifico = campoespecifico
                    if len(campoespecifico) > 1:
                        listcampoespecifico = campoespecifico.split(',')
                    querybase = SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, areaconocimiento__in=listcampoespecifico).order_by('codigo')
                    if 'q' in request.GET:
                        q = request.GET['q'].upper().strip()
                        if q != 'UNDEFINED':
                            querybase = querybase.filter((Q(nombre__icontains=q) | Q(codigo__icontains=q))).distinct()[:30]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {}".format(x.codigo, x.nombre)} for x in querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            # elif action == 'retiroasesor':
            #     try:
            #         data['title'] = u'Confirmar Retiro de Asesor'
            #         # data['responsable'] = int(request.GET['responsable'])
            #         data['prospecto'] = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
            #         return render(request, "comercial/modal/../templates/comercial/leadsdesactivadossup.html", data)
            #     except Exception as ex:
            #         pass

            # elif action == 'desactivarpostulacion':
            #     try:
            #         data['title'] = u'Confirmar eliminación de postulación'
            #         # data['responsable'] = int(request.GET['responsable'])
            #         data['prospecto'] = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
            #         return render(request, "comercial/modal/desactivarpostulacion.html", data)
            #     except Exception as ex:
            #         pass

            elif action == 'marcarcomocompmatricula':
                try:
                    data['title'] = u'Marcar como comprobante de matricula'
                    cursor = connections['epunemi'].cursor()
                    sql = """SELECT comp.id, (per.apellido1||' '||per.apellido2||' '||per.nombres) as persona FROM sagest_comprobantealumno comp INNER JOIN sga_persona per ON comp.persona_id = per.id WHERE comp.status = TRUE AND comp.id = '%s'""" % (int(request.GET['id']))
                    cursor.execute(sql)
                    rows = cursor.fetchone()

                    data['idcom'] = int(rows[0])
                    data['person'] = rows[1]
                    data['prospecto'] = InscripcionCohorte.objects.get(pk=int(request.GET['idd']))
                    return render(request, "comercial/modal/marcarmatricula.html", data)
                except Exception as ex:
                    pass

            elif action == 'leadsdesactivadossup':
                try:
                    request.session['viewactive'] = 15
                    data['title'] = u'Leads desactivados'
                    url_vars = '&action=leadsdesactivadossup'
                    aa = datetime.now().date().year

                    search = request.GET.get('s', None)
                    canti = request.GET.get('cantidad', 25)
                    idc = request.GET.get('idc', '0')
                    ide = request.GET.get('ide', '0')
                    ida = request.GET.get('ida', '0')
                    idcan = request.GET.get('idcan', '0')
                    idanio = request.GET.get('idanio', str(aa))
                    desde = request.GET.get('desde', '')
                    hasta = request.GET.get('hasta', '')

                    filtro = Q(status=False, cohortes__maestriaadmision__carrera__coordinacion__id=7)

                    if search:
                        data['search'] = search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=search) |
                                                     Q(inscripcionaspirante__persona__apellido2__icontains=search) |
                                                     Q(inscripcionaspirante__persona__nombres__icontains=search) |
                                                     Q(inscripcionaspirante__persona__cedula__icontains=search))
                            url_vars += "&s={}".format(search)
                        elif len(ss) == 2:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                                     Q(inscripcionaspirante__persona__apellido2__icontains=ss[1]))
                            url_vars += "&s={}".format(ss)
                        else:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                                Q(inscripcionaspirante__persona__apellido2__icontains=ss[1]) &
                                               Q(inscripcionaspirante__persona__nombres__icontains=ss[2]))
                            url_vars += "&s={}".format(ss)


                    if int(idc):
                        filtro = filtro & (Q(cohortes__id=int(idc)))
                        data['idc'] = int(idc)
                        url_vars += f"&idc={idc}"

                    if int(ide):
                        if int(ide) == 1:
                            filtro = filtro & (Q(estado_asesor=2))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 2:
                            filtro = filtro & (Q(estado_asesor=1))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 3:
                            filtro = filtro & (Q(tiporespuesta__isnull=False))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 4:
                            filtro = filtro & (Q(tiporespuesta__isnull=True))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 5:
                            filtro = filtro & (Q(estado_aprobador=1))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 6:
                            filtro = filtro & (Q(estado_aprobador=2))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 7:
                            filtro = filtro & (Q(estado_aprobador=3))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 8:
                            filtro = filtro & (Q(formapagopac__id=1))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 9:
                            filtro = filtro & (Q(formapagopac__id=2))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 10:
                            filtro = filtro & (Q(contrato__contratolegalizado=True))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 11:
                            filtro = filtro & (Q(todosubido=True, preaprobado=False))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 12:
                            idquery = CambioAdmitidoCohorteInscripcion.objects.filter(status=True).values_list('inscripcionCohorte__id', flat=True).order_by('inscripcionCohorte__id').distinct()
                            filtro = filtro & (Q(id__in=idquery))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"

                    if int(ida):
                            filtro = filtro & (Q(asesor__id=int(ida)))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"

                    if int(idcan):
                            filtro = filtro & (Q(inscripcionaspirante__persona__canton__id=int(idcan)))
                            data['idcan'] = int(idcan)
                            url_vars += f"&idcan={idcan}"

                    if int(idanio):
                        if int(idanio) > 0:
                            data['idanio'] = int(idanio)
                            filtro = filtro & Q(fecha_creacion__year=int(idanio))
                            url_vars += f"&idanio={idanio}"

                    if desde and hasta:
                        data['desde'] = desde
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha_creacion__date__range=(desde, hasta))
                        url_vars += "&desde={}".format(desde)
                        url_vars += "&hasta={}".format(hasta)

                    elif desde:
                        data['desde'] = desde
                        filtro = filtro & Q(fecha_creacion__date__gte=desde)
                        url_vars += "&desde={}".format(hasta)

                    elif hasta:
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha_creacion__date__lte=hasta)
                        url_vars += "&hasta={}".format(hasta)

                    query = InscripcionCohorte.objects.filter(filtro).order_by('-fecha_creacion')
                    paging = MiPaginador(query, canti)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["listado"] = page.object_list
                    data['eCohortes'] = CohorteMaestria.objects.filter(status=True).order_by('-id').distinct()
                    data['eAnios'] = InscripcionCohorte.objects.values_list('fecha_creacion__year', flat=True).order_by('fecha_creacion__year').distinct()
                    data['eTotal'] = query.count()
                    data['eAsignados'] = query.filter(estado_asesor=2).count()
                    data['ePendientes'] = query.filter(estado_asesor=1).count()
                    data['eAtendidos'] = query.filter(tiporespuesta__isnull=False).count()
                    data['eNoAtendidos'] = query.filter(tiporespuesta__isnull=True).count()
                    data['eAsesores'] = AsesorComercial.objects.filter(status=True)
                    data['eCantones'] = Canton.objects.filter(status=True)
                    data['canti'] = canti
                    return render(request, "comercial/leadsdesactivadossup.html", data)
                except Exception as ex:
                    pass

            elif action == 'cargar_maestria':
                try:
                    lista = []
                    maestrias = MaestriasAdmision.objects.filter(status=True, carrera__coordinacion__id=7).distinct()

                    for maestria in maestrias:
                        if not buscar_dicc(lista, 'id', maestria.id):
                            lista.append({'id': maestria.id, 'nombre': maestria.descripcion})
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cargar_maestria2':
                try:
                    lista = []
                    maestrias = MaestriasAdmision.objects.filter(status=True, carrera__coordinacion__id=7,
                                                                 cohortemaestria__asesormeta__asesor__persona_id=persona.id).distinct()

                    for maestria in maestrias:
                        if not buscar_dicc(lista, 'id', maestria.id):
                            lista.append({'id': maestria.id, 'nombre': maestria.descripcion})
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cargar_cohortes_ofer':
                try:
                    lista = []
                    cohortes = CohorteMaestria.objects.filter(status=True).order_by('-id')

                    for cohorte in cohortes:
                        if not buscar_dicc(lista, 'id', cohorte.id):
                            lista.append({'id': cohorte.id, 'nombre': cohorte.descripcion + ' - ' + cohorte.maestriaadmision.descripcion})
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cargar_carreras_ofer':
                try:
                    lista = []
                    idc = Graduado.objects.filter(status=True, inscripcion__carrera__coordinacion__id__in=[1, 2, 3, 4, 5]).values_list('inscripcion__carrera__id', flat=True).order_by('inscripcion__carrera__id').distinct()
                    carreras = Carrera.objects.filter(status=True, id__in=idc ,coordinacion__id__in=[1, 2, 3, 4, 5]).order_by('-id')

                    for carrera in carreras:
                        if not buscar_dicc(lista, 'id', carrera.id):
                            lista.append({'id': carrera.id, 'nombre': carrera.nombre})
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cargar_tiporespuesta':
                try:
                    lista = []
                    tiposres = TipoRespuestaProspecto.objects.filter(status=True).distinct()

                    for tipo in tiposres:
                        if not buscar_dicc(lista, 'id', tipo.id):
                            lista.append({'id': tipo.id, 'nombre': tipo.descripcion})
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cargar_asesor':
                try:
                    lista = []
                    asesores = AsesorComercial.objects.filter(status=True, rol__id__in=[1, 6])

                    for asesor in asesores:
                        if not buscar_dicc(lista, 'id', asesor.id):
                            lista.append({'id': asesor.id, 'nombre': asesor.persona.nombre_completo_inverso(), 'estado': 'ACTIVO' if asesor.activo else 'INACTIVO'})
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editarlead':
                try:
                    lead = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    data['id'] = int(request.GET['id'])
                    form = ActualizarDatosPersonaForm(initial={'cedula': lead.inscripcionaspirante.persona.cedula,
                                                               'nombres': lead.inscripcionaspirante.persona.nombres,
                                                               'apellido1': lead.inscripcionaspirante.persona.apellido1,
                                                               'apellido2': lead.inscripcionaspirante.persona.apellido2,
                                                               'telefono': lead.inscripcionaspirante.persona.telefono,
                                                               'email': lead.inscripcionaspirante.persona.email})

                    data['form2'] = form
                    data['action'] = 'editarlead'
                    template = get_template('comercial/modal/formlead.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'detretiro':
                try:
                    if Matricula.objects.filter(id=int(request.GET['id']), status=True).exists():
                        data['matricula'] = Matricula.objects.get(id=int(request.GET['id']), status=True)
                    template = get_template('comercial/modal/detretiro.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'ingresarpago':
                try:
                    data['filtro'] = lead = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    rubrosinscrito = Rubro.objects.filter(persona=lead.inscripcionaspirante.persona, inscripcion=lead, status=True, cancelado=False).order_by('id').first()

                    form = ComprobanteArchivoEstudianteForm(initial={'telefono': lead.inscripcionaspirante.persona.telefono,
                                                                     'email': lead.inscripcionaspirante.persona.email,
                                                                     'curso': rubrosinscrito.nombre,
                                                                     'carrera': lead.cohortes.maestriaadmision.carrera.nombre})

                    data['form2'] = form
                    data['action'] = 'ingresarpago'
                    url = urlepunemi + "api?a=apicuentas&clavesecreta=unemiepunemi2022"
                    r = requests.get(url)
                    listadocuentas = []
                    for lista in r.json():
                        listadocuentas.append([lista['id'], lista['nombre'], lista['numerocuenta'], lista['tipo']])
                    data['listadocuentas'] = listadocuentas
                    template = get_template('comercial/modal/ingresarpago.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editcomprobante':
                try:
                    data['filtro'] = compro = ComprobanteAlumno.objects.get(pk=int(request.GET['id']))
                    data['cuentade'] = int(compro.cuentadeposito)
                    form = EditarComprobantePagoForm(initial={'valor': compro.valor,
                                                             'observacion': compro.observacion,
                                                             'tipocomprobante': compro.tipocomprobante})
                                                             # 'evidencia': compro.comprobantes})

                    form.fields['evidencia'].initial= compro.comprobantes

                    form.renombrar()
                    data['form2'] = form
                    data['action'] = 'editcomprobante'
                    url = urlepunemi + "api?a=apicuentas&clavesecreta=unemiepunemi2022"
                    r = requests.get(url)
                    listadocuentas = []
                    for lista in r.json():
                        listadocuentas.append([lista['id'], lista['nombre'], lista['numerocuenta'], lista['tipo']])
                    data['listadocuentas'] = listadocuentas
                    template = get_template('comercial/modal/editcompago.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editgarantepagomaestria':
                try:
                    data['action'] = 'editgarantepagomaestria'
                    data['id'] = request.GET['idins']
                    data['idg'] = request.GET['idg']
                    garante = GarantePagoMaestria.objects.get(pk=request.GET['idg'])
                    initial = model_to_dict(garante)
                    form = GarantePagoMaestriaForm(initial=initial)
                    data['form'] = form
                    template = get_template("comercial/modal/editgarante.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content, "nombre": "EDITAR GARANTE"})
                except Exception as ex:
                    pass

            elif action == 'editarinscripcionrubro':
                try:
                    form2 = None
                    data['title'] = u'Editar rubro'
                    data['action'] = 'editarinscripcionrubro'
                    data['id'] = request.GET['id']
                    data['idins'] = request.GET['idins']
                    data['filtro'] = rubro = Rubro.objects.get(pk=int(request.GET['id']))
                    if rubro.cohortemaestria and rubro.inscripcion:
                        form2 = EditarRubroMaestriaForm(initial={'cohorte': rubro.cohortemaestria,
                                                                 'idinscripcion': rubro.inscripcion.id})
                        form2.solo_cohorte()
                    else:
                        form2 = EditarRubroMaestriaForm()
                        form2.solo_cohorte()
                    data['form2'] = form2
                    template = get_template('comercial/modal/editarinscripcionrubro.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'cambiardeconvenio':
                try:
                    from posgrado.forms import CambioConvenioMaestriaForm
                    data['filtro'] = lead = InscripcionCohorte.objects.get(
                        pk=int(request.GET['id']))
                    form = CambioConvenioMaestriaForm()
                    data['form2'] = form
                    data['action'] = 'cambiardeconvenio'
                    template = get_template('comercial/modal/cambiardecohorte.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'cambiardehomologacion':
                try:
                    from posgrado.forms import CambioHomologacionMaestriaForm
                    data['filtro'] = lead = InscripcionCohorte.objects.get(
                        pk=int(request.GET['id']))
                    form = CambioHomologacionMaestriaForm()
                    data['form2'] = form
                    data['action'] = 'cambiardehomologacion'
                    template = get_template('comercial/modal/cambiardecohorte.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'cambiardecohorte':
                try:
                    data['filtro'] = lead = InscripcionCohorte.objects.get(
                        pk=int(request.GET['id']))
                    form = CambioCohorteMaestriaForm(initial={'cohorteactual':lead.cohortes.descripcion})
                    form.fields['cohorte'].queryset = CohorteMaestria.objects.filter(status=True, maestriaadmision__id=lead.cohortes.maestriaadmision.id).exclude(id=lead.cohortes.id).order_by('-id')
                    data['form2'] = form
                    data['action'] = 'cambiardecohorte'
                    template = get_template('comercial/modal/cambiardecohorte.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'cambiardecohortemasivo':
                try:
                    cohorte = CohorteMaestria.objects.get(status=True, pk=int(request.GET['idc']))
                    ids = None
                    if 'ids' in request.GET:
                        ids = request.GET['ids']
                    data['ids'] = ids
                    if not ids == '':
                        data['cantidad'] = len(ids.split(','))
                        form = CambioCohorteMaestriaForm(initial={'cohorteactual':cohorte.descripcion})
                        form.fields['cohorte'].queryset = CohorteMaestria.objects.filter(status=True, maestriaadmision__id=cohorte.maestriaadmision.id).exclude(id=cohorte.id).order_by('-id')
                        data['form2'] = form
                        data['action'] = 'cambiardecohortemasivo'
                        template = get_template('comercial/modal/cambiocohortemasivo.html')
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, "mensaje": 'Por favor, seleccione al menos un lead'})
                except Exception as ex:
                    pass

            elif action == 'desactivarpostulacion':
                try:
                    from posgrado.forms import RechazoDesactivaForm
                    data['filtro'] = lead =  InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    form = RechazoDesactivaForm()
                    data['form2'] = form
                    data['action'] = 'desactivarpostulacion'
                    template = get_template('comercial/modal/rechazaactivapostulacion.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'rechazarpostulante':
                try:
                    from posgrado.forms import RechazoDesactivaForm
                    data['filtro'] = lead =  InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    form = RechazoDesactivaForm()
                    data['form2'] = form
                    data['action'] = 'rechazarpostulante'
                    template = get_template('comercial/modal/rechazaactivapostulacion.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'cambiarformapago':
                try:
                    leads = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    data['id'] = id = int(request.GET['id'])
                    form = FinanciamientoForm(initial={'persona': leads.inscripcionaspirante.persona.nombre_completo_inverso,
                                                           'tipo': leads.formapagopac,
                                                           'subirrequisitogarante': leads.subirrequisitogarante})

                    form.fields['tipo'].queryset = TipoFormaPagoPac.objects.filter(status=True)
                    if persona.es_asesor_financiamiento():
                        form.sin_subirrequisitogarante()
                    data['form2'] = form
                    data['action'] = 'cambiarformapago'
                    template = get_template('comercial/modal/cambiarformapago.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'asignartipo':
                try:
                    data['filtro'] = leads = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    form = AsignarTipoForm(initial={'persona': leads.inscripcionaspirante.persona.nombre_completo_inverso,
                                                    'maestria': leads.cohortes.maestriaadmision.descripcion,
                                                    'cohorte':leads.cohortes.descripcion,
                                                    'tipo': leads.Configfinanciamientocohorte,
                                                    'subirrequisitogarante':leads.subirrequisitogarante})
                    # 'asesor':leads.asesor.persona.nombre_completo_inverso})
                    form.fields['tipo'].queryset = ConfigFinanciamientoCohorte.objects.filter(status=True, cohorte__id=leads.cohortes.id)
                    data['form2'] = form
                    data['action'] = 'asignartipo'
                    template = get_template('comercial/modal/asignartipo.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'detallerequisitos':
                try:
                    tienerequisitos = False
                    data['tipo'] = int(request.GET['tipo'])
                    data['inscripcioncohorte'] = inscripcioncohorte = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    inscripciondescuento = None
                    data['inscripciondescuento'] = inscripciondescuento
                    if inscripcioncohorte.evidenciarequisitosaspirante_set.filter(status=True).exists():
                        tienerequisitos = True
                    data['tienerequisitos'] = tienerequisitos
                    if inscripcioncohorte.cohortes.tienecostoexamen:
                        if inscripcioncohorte.evidenciapagoexamen_set.filter(status=True):
                            tienepagoexamen = True
                            data['pagoexamen'] = evidpagoexamen = inscripcioncohorte.evidenciapagoexamen_set.filter(status=True)[0]
                            if evidpagoexamen.estadorevision == 2:
                                bloqueasubidapago = 2
                    if InscripcionCohorte.objects.filter(pk=int(request.GET['id']), grupo__isnull=True):
                        data['requisitos'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, requisito__claserequisito__clasificacion=1, status=True).order_by("id").distinct()
                        if inscripcioncohorte.subirrequisitogarante:
                            data['requisitosfi'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, requisito__claserequisito__clasificacion=3, status=True).order_by("id")
                        else:
                            data['requisitosfi'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, requisito__claserequisito__clasificacion=3, status=True, requisito__tipopersona__id=1).order_by("id")
                    else:
                        gruporequisitos = RequisitosGrupoCohorte.objects.values_list('requisito_id', flat=True).filter(grupo=inscripcioncohorte.grupo, status=True)
                        data['requisitos'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, requisito_id__in=gruporequisitos, requisito__claserequisito__clasificacion=1, status=True).order_by("id")
                        if inscripcioncohorte.subirrequisitogarante:
                            data['requisitosfi'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, requisito_id__in=gruporequisitos, requisito__claserequisito__clasificacion=3, status=True).order_by("id")
                        else:
                            data['requisitosfi'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, requisito_id__in=gruporequisitos, requisito__claserequisito__clasificacion=3, status=True, requisito__tipopersona__id=1).order_by("id")

                    template = get_template("comercial/modal/detallerequisitos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'asignarnuevotipof':
                try:
                    data['filtro'] = leads = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    form = AsignarTipoForm(initial={'persona': leads.inscripcionaspirante.persona.nombre_completo_inverso,
                                                    'maestria': leads.cohortes.maestriaadmision.descripcion,
                                                    'cohorte':leads.cohortes.descripcion,
                                                    'tipo': leads.Configfinanciamientocohorte})

                    form.fields['tipo'].queryset = ConfigFinanciamientoCohorte.objects.filter(status=True, cohorte__id=leads.cohortes.id)
                    form.sin_subir()
                    data['form2'] = form
                    data['action'] = 'asignarnuevotipof'
                    template = get_template('comercial/modal/asignartipo.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'vertablaamortizacion':
                try:
                    data['id'] = request.GET['id']
                    data['inscripcioncohorte'] = insc = InscripcionCohorte.objects.get(pk=request.GET['id'])
                    if insc.Configfinanciamientocohorte:
                        data['configuracion'] = configuracion = ConfigFinanciamientoCohorte.objects.filter(pk=insc.Configfinanciamientocohorte.id).last()
                        if configuracion:
                            data['contrato'] = contrato = insc.contrato_set.filter(status=True).last()
                            data['tablaamortizacion'] = tablaamortizacion = configuracion.tablaamortizacioncohortemaestria(insc,hoy)
                            total=0
                            for valor in tablaamortizacion:
                                total = total + valor[3]
                            data['total'] = total
                    data['soloVer'] = True
                    template = get_template("alu_requisitosmaestria/modaltablaamortizacionpagare.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'configurarfinanciamientocohorte':
                try:
                    data['title'] = u'Configuración financiamiento'
                    filtros = Q(status=True, cohorte__id=int(request.GET['idcohorte']))
                    s = request.GET.get('s', '')
                    url_vars = '&action=configurarfinanciamientocohorte'

                    if s:
                        filtros = filtros & (Q(descripcion__icontains=s))
                        data['s'] = f"{s}"
                        url_vars += f"&s={s}"

                    eFinanciamientos = ConfigFinanciamientoCohorte.objects.filter(filtros).order_by('-id')
                    paging = MiPaginador(eFinanciamientos, 25)
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
                    data['eFinanciamientos'] = page.object_list
                    data['url_vars'] = url_vars
                    data['cohorte'] = CohorteMaestria.objects.get(status=True, pk=int(request.GET['idcohorte']))
                    data['inscripcion'] = InscripcionCohorte.objects.get(status=True, pk=int(request.GET['idinscripcioncohorte']))
                    data['contratop'] = Contrato.objects.get(status=True, pk=int(request.GET['idcontrato']))
                    data['count'] = eFinanciamientos.count()
                    return render(request, "comercial/tiposfinanciamientocohorte.html", data)
                except Exception as ex:
                    pass

            elif action == 'addfinanciamientocohorte':
                try:
                    data['action'] = 'addfinanciamientocohorte'
                    data['cohorte'] = cohorte = CohorteMaestria.objects.get(pk=request.GET['idc'])
                    carrera = cohorte.maestriaadmision.carrera
                    instauracion = None
                    if carrera:
                        instauracion = carrera.programapac_set.last()
                    if instauracion:
                        infopac = instauracion.infraestructuraequipamientoinformacionpac_set.last()
                        if infopac:
                            form = ConfigFinanciamientoCohorteForm(initial={'valormatricula': infopac.valormatricula,
                                                                            'valorarancel': infopac.valorarancel,
                                                                            'valortotalprograma': infopac.valortotalprograma,
                                                                            'porcentajeminpagomatricula': infopac.porcentajeminpagomatricula,
                                                                            'maxnumcuota': infopac.maxnumcuota})
                        else:
                            form = ConfigFinanciamientoCohorteForm()
                    else:
                        form = ConfigFinanciamientoCohorteForm()
                    data['form2'] = form
                    template = get_template("comercial/modal/modalfinanciamientocohorte.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editfinanciamientocohorte':
                try:
                    data['id'] = request.GET['id']
                    data['action'] = 'editfinanciamientocohorte'
                    data['filtro'] = filtro = ConfigFinanciamientoCohorte.objects.get(pk=request.GET['id'])
                    data['form2'] = ConfigFinanciamientoCohorteForm(model_to_dict(filtro))
                    template = get_template("comercial/modal/modalfinanciamientocohorte.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editrubro':
                try:
                    form2 = None
                    data['title'] = u'Editar rubro'
                    data['action'] = 'editrubro'
                    data['id'] = request.GET['id']
                    data['filtro'] = rubro = Rubro.objects.get(pk=int(request.GET['id']))
                    esmatricula = True if rubro.admisionposgradotipo == 2 else False
                    if rubro.cohortemaestria:
                        form2 = EditarRubroMaestriaForm(initial={'nombre':rubro.nombre,
                                                                 'cohorte': rubro.cohortemaestria,
                                                                 'valor': rubro.valor,
                                                                 'fecha': rubro.fechavence,
                                                                 'matricula': esmatricula})
                        form2.no_id()
                    else:
                        form2 = EditarRubroMaestriaForm(initial={'nombre':rubro.nombre,
                                                                 'valor': rubro.valor,
                                                                 'fecha': rubro.fechavence,
                                                                 'matricula': esmatricula})
                        form2.no_id()
                    data['form2'] = form2
                    template = get_template('comercial/modal/modificacionrubrovalores.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edittablacuota':
                try:
                    data['action'] = 'edittablacuota'
                    data['ta_cuota'] = tablacuota = TablaAmortizacion.objects.get(pk=int(request.GET['id']))
                    data['idcontrato'] = tablacuota.contrato.id
                    template = get_template('comercial/modal/modificaciontablaamortizacion.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editcuota':
                try:
                    data['title'] = u'Editar cuota'
                    data['action'] = 'editcuota'
                    data['tabla'] = tablacuota = TablaAmortizacion.objects.get(pk=int(request.GET['id']))
                    form2 = AdicionarCuotaTablaAmortizacionForm(initial={'numerocuota':tablacuota.cuota,
                                                                         'nombre':tablacuota.nombre,
                                                                         'valor':tablacuota.valor,
                                                                         'inicio':tablacuota.fecha,
                                                                         'fin':tablacuota.fechavence})
                    data['form2'] = form2
                    data['contratop'] = contrato = tablacuota.contrato.id
                    template = get_template('comercial/modal/modificaciontablaamortizacion.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addcuota':
                try:
                    data['title'] = u'Agregar cuota'
                    data['action'] = 'addcuota'
                    form2  = AdicionarCuotaTablaAmortizacionForm()
                    data['form2'] = form2
                    data['contratop'] = contrato = Contrato.objects.get(pk=request.GET['id'])
                    template = get_template('comercial/modal/modificaciontablaamortizacion.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'existerubroajutar':
                try:
                    data['title'] = u'Rubros vs Tabla de amotización'
                    contrato = rubroscohorte = tabla = ins = None
                    if 'sign' in request.GET:
                        data['sign'] = request.GET['sign']

                    if 'idcontrato' in request.GET:
                        if request.GET['idcontrato']:
                            data['contratop'] = contrato = Contrato.objects.get(pk=request.GET['idcontrato'])
                    if 'idinscripcioncohote' in request.GET:
                        if request.GET['idinscripcioncohote']:
                            data['inscripcioncohorte'] = ins = InscripcionCohorte.objects.get(pk=request.GET['idinscripcioncohote'])
                    if contrato:
                        tabla = contrato.tablaamortizacion_set.filter(status=True)
                        if ins:
                            data['rubroscohorte'] = rubroscohorte = Rubro.objects.filter(inscripcion=ins, cohortemaestria=ins.cohortes, status=True).order_by('id')
                            excluirrubros = Rubro.objects.values_list('id').filter(inscripcion=ins, cohortemaestria=ins.cohortes, status=True)
                            data['otrosrubros'] = otrosrubros = Rubro.objects.filter(persona=ins.inscripcionaspirante.persona, status=True).exclude(id__in=excluirrubros).order_by('id')

                            #adicionar automaticamante la cuota de matricula (cuota 0) si no existe.
                            if tabla:
                                registro = contrato.tablaamortizacion_set.values_list('cuota').filter(status=True, cuota=0)
                                if not registro:
                                    des = str(contrato.inscripcion.cohortes.maestriaadmision) + ' - ' + str(contrato.inscripcion.cohortes.descripcion)
                                    desmatricula = 'MATRICULA DE POSTGRADO - %s' % des
                                    amortizacion = TablaAmortizacion(
                                        contrato=contrato,
                                        cuota=0,
                                        nombre=desmatricula,
                                        valor=ins.Configfinanciamientocohorte.valormatricula,
                                        fecha=tabla[0].fecha,
                                        fechavence= contrato.inscripcion.cohortes.fechavencerubro)
                                    amortizacion.save()
                                total = contrato.tablaamortizacion_set.filter(status=True).aggregate(total_amortizado=Sum('valor'))
                                data['totaltabla'] = total['total_amortizado']
                                data['tablaamortizacion'] = contrato.tablaamortizacion_set.filter(status=True)
                            if rubroscohorte:
                                data['contrato'] = tabla[0].contrato
                                total = 0
                                for valor in tabla:
                                    total = total + valor.valor
                                data['total'] = total

                    if contrato.inscripcion.formapagopac.id == 1:
                        if contrato and contrato.archivocontrato:
                            if 'idinscripcioncohote' in request.GET:
                                if request.GET['idinscripcioncohote']:
                                    data['inscripcioncohorte'] = ins = InscripcionCohorte.objects.get(pk=request.GET['idinscripcioncohote'])
                                    data['rubroscohorte'] = rubroscohorte = Rubro.objects.filter(inscripcion=ins, cohortemaestria=ins.cohortes, status=True).order_by('id')
                                    excluirrubros = Rubro.objects.values_list('id').filter(inscripcion=ins, cohortemaestria=ins.cohortes, status=True)
                                    data['otrosrubros'] = otrosrubros = Rubro.objects.filter(persona=ins.inscripcionaspirante.persona, status=True).exclude(id__in=excluirrubros).order_by('id')

                    return render(request, "comercial/rubrosvstablaamortizacion.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'detalleprospecto':
                try:
                    if 'id' in request.GET:
                        data['inscripcion'] = InscripcionCohorte.objects.get(pk=request.GET['id'], status=True)
                        template = get_template("comercial/modal/detalleprospecto.html")
                    return JsonResponse({'result': 'ok', 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'buscarnombrerubros':
                try:
                    inscrito = InscripcionCohorte.objects.get(status=True, pk=int(encrypt(request.GET['idinsc'])))
                    q = request.GET['q'].upper().strip()
                    # per = Rubro.objects.filter(persona=inscrito.inscripcionaspirante.persona, inscripcion=inscrito, status=True, cancelado=False).filter(nombre__icontains=q).distinct('nombre').order_by('id')[0]
                    per = Rubro.objects.filter(persona=inscrito.inscripcionaspirante.persona, inscripcion=inscrito, status=True, cancelado=False).filter(nombre__icontains=q).order_by('id').first()
                    # data = {"result": "ok", "results": [{"id": x.id, "nombre": str(x.nombre)} for x in per]}
                    data = {"result": "ok", "results": [{"id": per.id, "nombre": str(per.nombre)}]}
                    return JsonResponse(data)
                except Exception as ex:
                    messages.error(request, str(ex))

            elif action == 'reporteventasgeneral':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('listado_ventas')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 15)
                    ws.set_column(2, 2, 15)
                    ws.set_column(3, 3, 30)
                    ws.set_column(4, 4, 30)
                    ws.set_column(5, 5, 40)
                    ws.set_column(6, 6, 50)
                    ws.set_column(7, 7, 40)
                    ws.set_column(8, 8, 15)
                    ws.set_column(9, 9, 20)
                    ws.set_column(10, 10, 40)
                    ws.set_column(11, 11, 15)
                    ws.set_column(12, 12, 15)
                    ws.set_column(13, 13, 15)
                    ws.set_column(14, 14, 15)
                    ws.set_column(15, 15, 15)
                    ws.set_column(16, 16, 35)
                    ws.set_column(17, 17, 20)
                    ws.set_column(18, 18, 20)
                    ws.set_column(19, 19, 20)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    decimalformat2 = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    asesor = cohorte = 0
                    desde = hasta = ''

                    if 'cohorte' in request.GET:
                        cohorte = request.GET['cohorte']
                    if 'asesor' in request.GET:
                        asesor = request.GET['asesor']

                    if 'desde' in request.GET:
                        desde = request.GET['desde']
                    if 'hasta' in request.GET:
                        hasta = request.GET['hasta']

                    ws.merge_range('A1:T1', 'Reporte general de ventas', formatotitulo_filtros)
                    if desde and hasta:
                        ws.merge_range('A2:T2', 'Desde el ' + desde + ' Hasta el ' + hasta, formatotitulo_filtros)

                    ws.write(2, 0, 'N°', formatoceldacab)
                    ws.write(2, 1, 'Id', formatoceldacab)
                    ws.write(2, 2, 'Cédula', formatoceldacab)
                    ws.write(2, 3, 'Provincia', formatoceldacab)
                    ws.write(2, 4, 'Cantón', formatoceldacab)
                    ws.write(2, 5, 'Prospecto', formatoceldacab)
                    ws.write(2, 6, 'Cohorte', formatoceldacab)
                    ws.write(2, 7, 'Maestría', formatoceldacab)
                    ws.write(2, 8, 'Fecha de la venta', formatoceldacab)
                    ws.write(2, 9, 'Forma de pago', formatoceldacab)
                    ws.write(2, 10, 'Asesor comercial', formatoceldacab)
                    ws.write(2, 11, 'Valor de la maestría', formatoceldacab)
                    ws.write(2, 12, 'Valor cancelado', formatoceldacab)
                    ws.write(2, 13, 'Por recaudar', formatoceldacab)
                    ws.write(2, 14, 'Medio de pago', formatoceldacab)
                    ws.write(2, 15, '¿Está facturado?', formatoceldacab)
                    ws.write(2, 16, 'Correo', formatoceldacab)
                    ws.write(2, 17, 'Teléfono', formatoceldacab)
                    ws.write(2, 18, 'Canal de información', formatoceldacab)
                    ws.write(2, 19, 'Convenio', formatoceldacab)

                    filtro = Q(status=True)
                    if cohorte != "":
                        if eval(request.GET['cohorte'])[0] != "0":
                            filtro = filtro & Q(inscripcioncohorte__cohortes__id__in=eval(request.GET['cohorte']))

                    if asesor != "":
                        if eval(request.GET['asesor'])[0] != "0":
                            filtro = filtro & Q(asesor__id__in=eval(request.GET['asesor']))

                    if desde and hasta:
                        filtro = filtro & Q(fecha__range=(desde, hasta))
                    elif desde:
                        filtro = filtro & Q(fecha__gte=desde)
                    elif hasta:
                        filtro = filtro & Q(fecha__lte=hasta)

                    ventas = VentasProgramaMaestria.objects.filter(filtro).exclude(valida=False).order_by('fecha')

                    filas_recorridas = 4
                    cont = 1
                    sum_maestria = 0
                    sum_cancelado = 0
                    sum_recaudar = 0
                    for venta in ventas:
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(venta.inscripcioncohorte.id), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(venta.inscripcioncohorte.inscripcionaspirante.persona.identificacion()), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(venta.inscripcioncohorte.inscripcionaspirante.persona.provincia.nombre if venta.inscripcioncohorte.inscripcionaspirante.persona.provincia else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(venta.inscripcioncohorte.inscripcionaspirante.persona.canton.nombre if venta.inscripcioncohorte.inscripcionaspirante.persona.canton else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(venta.inscripcioncohorte.inscripcionaspirante.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(venta.inscripcioncohorte.cohortes.descripcion), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(venta.inscripcioncohorte.cohortes.maestriaadmision.descripcion), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str(venta.fecha), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str(venta.inscripcioncohorte.formapagopac.descripcion), formatoceldaleft)
                        ws.write('K%s' % filas_recorridas, str(venta.inscripcioncohorte.asesor.persona.nombre_completo_inverso() if venta.inscripcioncohorte.asesor else 'POR ASIGNAR'), formatoceldaleft)
                        ws.write('L%s' % filas_recorridas, venta.inscripcioncohorte.cohortes.valorprogramacertificado if venta.inscripcioncohorte.cohortes.valorprogramacertificado else 'NO REGISTRA', decimalformat)
                        ws.write('M%s' % filas_recorridas, venta.inscripcioncohorte.total_pagado_rubro_cohorte(), decimalformat)
                        ws.write('N%s' % filas_recorridas, venta.inscripcioncohorte.total_pendiente(), decimalformat)
                        ws.write('O%s' % filas_recorridas, str(venta.mediopago), formatoceldaleft)
                        ws.write('P%s' % filas_recorridas, str('SI' if venta.inscripcioncohorte.total_pagado_rubro_cohorte() > 0 else 'NO'), formatoceldaleft)
                        ws.write('Q%s' % filas_recorridas, str(venta.inscripcioncohorte.inscripcionaspirante.persona.email if venta.inscripcioncohorte.inscripcionaspirante.persona.email else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('R%s' % filas_recorridas, str(venta.inscripcioncohorte.inscripcionaspirante.persona.telefono if venta.inscripcioncohorte.inscripcionaspirante.persona.telefono else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('S%s' % filas_recorridas, str(venta.inscripcioncohorte.canal.descripcion if venta.inscripcioncohorte.canal else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('T%s' % filas_recorridas, str(venta.inscripcioncohorte.convenio.descripcion if venta.inscripcioncohorte.convenio else 'NO REGISTRA'), formatoceldaleft)

                        filas_recorridas += 1
                        cont += 1
                        sum_maestria += venta.inscripcioncohorte.cohortes.valorprogramacertificado
                        sum_cancelado += venta.inscripcioncohorte.total_pagado_rubro_cohorte()
                        sum_recaudar += venta.inscripcioncohorte.total_pendiente()

                    ws.merge_range('A%s:K%s' % (filas_recorridas, filas_recorridas), 'TOTALES:', formatoceldaleft3)

                    ws.write('L%s' % filas_recorridas, sum_maestria, decimalformat2)
                    ws.write('M%s' % filas_recorridas, sum_cancelado, decimalformat2)
                    ws.write('N%s' % filas_recorridas, sum_recaudar, decimalformat2)

                    workbook.close()
                    output.seek(0)
                    fecha_hora_actual = datetime.now().date()
                    filename = 'Listado_ventas_' + str(fecha_hora_actual) + '.xlsx'
                    response = HttpResponse(output,

                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporteventasasesor':
                try:
                    __author__ = 'Unemi'

                    asesorme = AsesorMeta.objects.get(status=True, id= request.GET['id'])

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('ventas')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 45)
                    ws.set_column(2, 2, 15)
                    ws.set_column(3, 3, 15)
                    ws.set_column(4, 4, 25)
                    ws.set_column(5, 5, 45)
                    ws.set_column(6, 6, 15)
                    ws.set_column(7, 7, 15)
                    ws.set_column(8, 8, 15)
                    ws.set_column(9, 9, 15)
                    ws.set_column(10, 10, 15)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size':14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    ws.merge_range('A1:K1', asesorme.cohorte.maestriaadmision.descripcion + " - " + asesorme.cohorte.descripcion, formatotitulo_filtros)
                    ws.merge_range('A2:K2', 'VENTAS' + asesorme.cohorte.maestriaadmision.descripcion.replace("MAESTRÍA", ""), formatoceldacab)
                    ws.write(2, 0, 'N°', formatoceldacab)
                    ws.write(2, 1, 'NOMBRES', formatoceldacab)
                    ws.write(2, 2, 'FECHA DE CANCELACION', formatoceldacab)
                    ws.write(2, 3, 'CEDULA', formatoceldacab)
                    ws.write(2, 4, 'FORMA DE PAGO', formatoceldacab)
                    ws.write(2, 5, 'ASESOR', formatoceldacab)
                    ws.write(2, 6, 'VALOR DE LA MAESTRIA', formatoceldacab)
                    ws.write(2, 7, 'VALOR CANCELADO', formatoceldacab)
                    ws.write(2, 8, 'POR RECAUDAR', formatoceldacab)
                    ws.write(2, 9, 'FECHA DE REGISTRO', formatoceldacab)
                    ws.write(2, 10, 'CIERRE DE VENTA(DIAS)', formatoceldacab)

                    # estado = request.GET['estado']
                    # desde = request.GET['fdesde']
                    # hasta = request.GET['fhasta']
                    # peri = request.GET['periodo']
                    # cordina = request.GET['coordinacion']

                    listado_pagos = []

                    idadmitidos = InscripcionCohorte.objects.filter(cohortes=asesorme.cohorte,
                                                                    status=True,
                                                                    asesor=asesorme.asesor).values_list('id', flat=True)

                    for idadmitido in idadmitidos:
                        if Rubro.objects.filter(inscripcion__id=idadmitido).exists():
                            admitido = InscripcionCohorte.objects.get(pk=idadmitido)
                            rubrocohorte = Rubro.objects.get(inscripcion=admitido)
                            costomaestria = admitido.cohortes.valorprogramacertificado
                            diezporciento = costomaestria * 0.10

                            if costomaestria == rubrocohorte.valor:
                                valorpagado = admitido.total_pagado_cohorte()
                            else:
                                valorpagado = admitido.inscripcionaspirante.persona.total_pagado_maestria()

                            if valorpagado >= diezporciento:
                                pago = Pago.objects.filter(rubro__inscripcion__id=admitido.id).order_by('id').first()
                                listado_pagos.append(pago.id)

                    ventas = Rubro.objects.filter(status=True, admisionposgradotipo__in=[2, 3], pago__id__in=listado_pagos)

                    filas_recorridas = 4
                    cont = 1
                    formap = ''
                    sum_maestria = 0
                    sum_cancelado = 0
                    sum_recaudar = 0
                    cancelado = 0
                    reacudado = 0
                    for venta in ventas:
                        if venta.inscripcion.cohortes.valorprogramacertificado == venta.valor:
                            formap = 'CONTADO'
                        else:
                            formap = 'FINANCIAMIENTO'

                        if venta.matricula:
                            cancelado = venta.matricula.total_pagado_alumno_rubro_maestria()
                            recaudado = venta.matricula.total_saldo_rubrosinanular_rubro_maestria()
                        else:
                            cancelado = venta.persona.total_pagado_maestria()
                            recaudado = venta.persona.valor_por_recaudar_maestria()
                        registro = venta.inscripcion.fecha_creacion.date()
                        pago = venta.pago_set.first().fecha
                        # dias = pago - registro
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(venta.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(venta.pago_set.first().fecha), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(venta.persona.identificacion()), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(formap), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(venta.inscripcion.asesor.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, '$' + ' ' + str(Decimal(null_to_decimal(venta.inscripcion.cohortes.valorprogramacertificado)).quantize(Decimal('.01'))), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, '$' + ' ' + str(Decimal(null_to_decimal(cancelado,2)).quantize(Decimal('.01'))), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, '$' + ' ' + str(Decimal(null_to_decimal(recaudado,2)).quantize(Decimal('.01'))), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str(venta.inscripcion.fecha_creacion.date()), formatoceldaleft)
                        ws.write('K%s' % filas_recorridas, str(pago - registro), formatoceldaleft)

                        filas_recorridas += 1
                        cont += 1
                        sum_maestria += Decimal(null_to_decimal(venta.inscripcion.cohortes.valorprogramacertificado, 2)).quantize(Decimal('.01'))
                        sum_cancelado += Decimal(null_to_decimal(cancelado, 2)).quantize(Decimal('.01'))
                        sum_recaudar += Decimal(null_to_decimal(recaudado, 2)).quantize(Decimal('.01'))

                    # ws.merge_range('A:F', 'TOTALES:', formatoceldaleft2)
                    ws.merge_range('A%s:F%s' % (filas_recorridas, filas_recorridas), 'TOTALES:', formatoceldaleft3)

                    ws.write('G%s' % filas_recorridas, '$' + ' ' +str(sum_maestria), formatoceldaleft2)
                    ws.write('H%s' % filas_recorridas, '$' + ' ' + str(sum_cancelado), formatoceldaleft2)
                    ws.write('I%s' % filas_recorridas, '$' + ' ' + str(sum_recaudar), formatoceldaleft2)

                    workbook.close()
                    output.seek(0)
                    filename = 'Reporte_Ventas_Asesor.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporteventastotales':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('ventas')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 45)
                    ws.set_column(2, 2, 25)
                    ws.set_column(3, 3, 15)
                    ws.set_column(4, 4, 15)
                    ws.set_column(5, 5, 15)
                    ws.set_column(6, 6, 15)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    cohorte = 0
                    desde = hasta = ''

                    if 'cohorte' in request.GET:
                        cohorte = request.GET['cohorte']

                    if 'desde' in request.GET:
                        desde = request.GET['desde']
                    if 'hasta' in request.GET:
                        hasta = request.GET['hasta']

                    ws.merge_range('A1:G1', 'Cupos vendidos por cohorte', formatotitulo_filtros)
                    if desde and hasta:
                        ws.merge_range('A2:G2', 'Desde el ' + desde + ' hasta el ' + hasta, formatotitulo_filtros)

                    ws.write(2, 0, 'N°', formatoceldacab)
                    ws.write(2, 1, 'Maestría', formatoceldacab)
                    ws.write(2, 2, 'Cohorte', formatoceldacab)
                    ws.write(2, 3, 'Cupos disponibles', formatoceldacab)
                    ws.write(2, 4, 'Ventas reportadas', formatoceldacab)
                    ws.write(2, 5, 'Ventas facturadas', formatoceldacab)
                    ws.write(2, 6, 'Ventas totales', formatoceldacab)

                    filtro = Q(status=True)

                    if cohorte != "":
                        if eval(request.GET['cohorte'])[0] != "0":
                            filtro = filtro & Q(id__in=eval(request.GET['cohorte']))
                        else:
                            if desde and hasta:
                                v = VentasProgramaMaestria.objects.filter(status=True, fecha__range=(desde, hasta)).values_list('inscripcioncohorte__cohortes__id', flat=True).exclude(valida=False).order_by('inscripcioncohorte__cohortes__id').distinct()
                            else:
                                v = VentasProgramaMaestria.objects.filter(status=True).values_list('inscripcioncohorte__cohortes__id', flat=True).exclude(valida=False).order_by('inscripcioncohorte__cohortes__id').distinct()
                            filtro = filtro & Q(id__in=v)

                    cohortes = CohorteMaestria.objects.filter(filtro).order_by('-id','maestriaadmision__carrera__id')

                    filtro2 = Q(status=True)

                    if desde and hasta:
                        filtro2 = filtro2 & Q(fecha__range=(desde, hasta))
                    elif desde:
                        filtro2 = filtro2 & Q(fecha__gte=desde)
                    elif hasta:
                        filtro2 = filtro2 & Q(fecha__lte=hasta)

                    filas_recorridas = 4
                    cont = 1

                    for cohorte in cohortes:

                        ventas = VentasProgramaMaestria.objects.filter(filtro2 & Q(inscripcioncohorte__cohortes=cohorte)).exclude(valida=False)

                        reportadas = ventas.filter(facturado=False).count()
                        facturadas = ventas.filter(facturado=True).count()
                        totales = ventas.count()

                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(cohorte.maestriaadmision.descripcion), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(cohorte.descripcion), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, cohorte.cupodisponible, formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, reportadas, formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, facturadas, formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, totales, formatoceldaleft)

                        filas_recorridas += 1
                        cont += 1


                    workbook.close()
                    output.seek(0)
                    fecha_hora_actual = datetime.now().date()
                    filename = 'Total_cupos_vendidos_' + str(fecha_hora_actual) + '.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporteventastotalesasesor':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('ventas_asesor')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 40)
                    ws.set_column(2, 2, 25)
                    ws.set_column(3, 3, 25)
                    ws.set_column(4, 4, 15)
                    ws.set_column(5, 5, 15)
                    ws.set_column(6, 6, 15)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    asesor = cohorte = 0
                    desde = hasta = ''

                    if 'cohorte' in request.GET:
                        cohorte = request.GET['cohorte']
                    if 'asesor' in request.GET:
                        asesor = request.GET['asesor']

                    if 'desde' in request.GET:
                        desde = request.GET['desde']
                    if 'hasta' in request.GET:
                        hasta = request.GET['hasta']

                    ws.merge_range('A1:G1', 'Ventas de asesores', formatotitulo_filtros)
                    if desde and hasta:
                        ws.merge_range('A2:G2', 'Desde el ' + desde + ' hasta el ' + hasta, formatotitulo_filtros)

                    ws.write(2, 0, 'N°', formatoceldacab)
                    ws.write(2, 1, 'Asesor comercial', formatoceldacab)
                    ws.write(2, 2, 'Maestría', formatoceldacab)
                    ws.write(2, 3, 'Cohorte', formatoceldacab)
                    ws.write(2, 4, 'Ventas reportadas', formatoceldacab)
                    ws.write(2, 5, 'Ventas facturadas', formatoceldacab)
                    ws.write(2, 6, 'Ventas totales', formatoceldacab)

                    filtro = Q(status=True)

                    filtro1 = Q(status=True, rol__id__in=[1, 6])

                    if cohorte != "":
                        if eval(request.GET['cohorte'])[0] != "0":
                            filtro = filtro & Q(id__in=eval(request.GET['cohorte']))
                        else:
                            if desde and hasta:
                                v = VentasProgramaMaestria.objects.filter(status=True, fecha__range=(desde, hasta)).values_list('inscripcioncohorte__cohortes__id', flat=True).exclude(valida=False).order_by('inscripcioncohorte__cohortes__id').distinct()
                            else:
                                v = VentasProgramaMaestria.objects.filter(status=True).values_list('inscripcioncohorte__cohortes__id', flat=True).exclude(valida=False).order_by('inscripcioncohorte__cohortes__id').distinct()
                            filtro = filtro & Q(id__in=v)

                    if asesor != "":
                        if eval(request.GET['asesor'])[0] != "0":
                            filtro1 = filtro1 & Q(id__in=eval(request.GET['asesor']))

                    cohortes = CohorteMaestria.objects.filter(filtro)

                    asesores = AsesorComercial.objects.filter(filtro1).order_by('persona__apellido1',
                                                                                    'persona__apellido2',
                                                                                    'persona__nombres')

                    filtro2 = Q(status=True)

                    if desde and hasta:
                        filtro2 = filtro2 & Q(fecha__range=(desde, hasta))
                    elif desde:
                        filtro2 = filtro2 & Q(fecha__gte=desde)
                    elif hasta:
                        filtro2 = filtro2 & Q(fecha__lte=hasta)

                    filas_recorridas = 4
                    cont = 1

                    for cohorte in cohortes:
                        for asesor in asesores:
                            ventas = VentasProgramaMaestria.objects.filter(filtro2 & Q(inscripcioncohorte__cohortes=cohorte, asesor=asesor)).exclude(valida=False)

                            reportadas = ventas.filter(facturado=False).count()
                            facturadas = ventas.filter(facturado=True).count()
                            totales = ventas.count()

                            ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                            ws.write('B%s' % filas_recorridas, str(asesor.persona.nombre_completo_inverso()), formatoceldaleft)
                            ws.write('C%s' % filas_recorridas, str(cohorte.maestriaadmision.descripcion), formatoceldaleft)
                            ws.write('D%s' % filas_recorridas, str(cohorte.descripcion), formatoceldaleft)
                            ws.write('E%s' % filas_recorridas, reportadas, formatoceldaleft)
                            ws.write('F%s' % filas_recorridas, facturadas, formatoceldaleft)
                            ws.write('G%s' % filas_recorridas, totales, formatoceldaleft)

                            filas_recorridas += 1
                            cont += 1

                    workbook.close()
                    output.seek(0)
                    fecha_hora_actual = datetime.now().date()
                    filename = 'Total_ventas_asesor_' + str(fecha_hora_actual) + '.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'resumen_leads_asesor':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('resumen')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 40)
                    ws.set_column(2, 2, 25)
                    ws.set_column(3, 3, 25)
                    ws.set_column(4, 4, 20)
                    ws.set_column(5, 5, 20)
                    ws.set_column(6, 6, 20)
                    ws.set_column(7, 7, 20)
                    ws.set_column(8, 8, 20)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
                    decimalformat2 = workbook.add_format({'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    asesor = cohorte = 0
                    desde = hasta = ''

                    if 'cohorte' in request.GET:
                        cohorte = request.GET['cohorte']
                    if 'asesor' in request.GET:
                        asesor = request.GET['asesor']

                    if 'desde' in request.GET:
                        desde = request.GET['desde']
                    if 'hasta' in request.GET:
                        hasta = request.GET['hasta']

                    ws.merge_range('A1:H1', 'Resumen de leads por asesor', formatotitulo_filtros)
                    if desde and hasta:
                        ws.merge_range('A2:H2', 'Desde el ' + desde + ' hasta el ' + hasta, formatotitulo_filtros)

                    ws.write(2, 0, 'N°', formatoceldacab)
                    ws.write(2, 1, 'Asesor comercial', formatoceldacab)
                    ws.write(2, 2, '# Leads reservados', formatoceldacab)
                    ws.write(2, 3, '# Leads asignados', formatoceldacab)
                    # ws.write(2, 4, '# de leads', formatoceldacab)
                    ws.write(2, 4, '# de leads en proceso', formatoceldacab)
                    ws.write(2, 5, '# de leads admitidos', formatoceldacab)
                    ws.write(2, 6, '# de contratos aprobados', formatoceldacab)
                    ws.write(2, 7, '# de pagos registrados', formatoceldacab)

                    filtro = Q(status=True, activo=True)
                    filtro_re = Q(status=True)
                    filtro_asi = Q(status=True)
                    filtro_tot = Q(status=True)
                    filtro_admi = Q(status=True, estado_aprobador=2)
                    filtro_cunt = Q(status=True, estado_aprobacion=2)
                    filtro_venta = Q(status=True, valida=True)

                    if cohorte != "":
                        lista_cadenas = ast.literal_eval(request.GET['cohorte'])
                        lista_enteros = list(map(int, lista_cadenas))

                        if len(lista_enteros) > 0 and 0 not in lista_enteros:
                            filtro_re = filtro_re & Q(inscripcion__cohortes__id__in=lista_enteros)
                            filtro_asi = filtro_asi & Q(inscripcion__cohortes__id__in=lista_enteros)
                            filtro_tot = filtro_tot & Q(cohortes__id__in=lista_enteros)
                            filtro_admi = filtro_admi & Q(cohortes__id__in=lista_enteros)
                            filtro_cunt = filtro_cunt & Q(contrato__inscripcion__cohortes__id__in=lista_enteros)
                            filtro_venta = filtro_venta & Q(inscripcioncohorte__cohortes__id__in=lista_enteros)

                    if asesor != "":
                        lista_cadenas_a = ast.literal_eval(request.GET['asesor'])
                        lista_enteros_a = list(map(int, lista_cadenas_a))

                        if len(lista_enteros_a) > 0 and 0 not in lista_enteros_a:
                            filtro = filtro & Q(id__in=lista_enteros_a)

                    asesores = AsesorComercial.objects.filter(filtro).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    if desde and hasta:
                        filtro_re = filtro_re & Q(fecha_creacion__date__range=(desde, hasta))
                        filtro_asi = filtro_asi & Q(fecha_creacion__date__range=(desde, hasta))
                        filtro_tot = filtro_tot & Q(fecha_creacion__date__range=(desde, hasta))
                        filtro_admi = filtro_admi & Q(fecha_aprobador__date__range=(desde, hasta))
                        filtro_cunt = filtro_cunt & Q(fecha_aprobacion__date__range=(desde, hasta))
                        filtro_venta = filtro_venta & Q(fecha__range=(desde, hasta))

                    elif desde:
                        filtro_re = filtro_re & Q(fecha_creacion__date__gte=desde)
                        filtro_asi = filtro_asi & Q(fecha_creacion__date__gte=desde)
                        filtro_tot = filtro_tot & Q(fecha_creacion__date__gte=desde)
                        filtro_admi = filtro_admi & Q(fecha_aprobador__date__gte=desde)
                        filtro_cunt = filtro_cunt & Q(fecha_aprobacion__date__gte=desde)
                        filtro_venta = filtro_venta & Q(fecha__date__gte=desde)

                    elif hasta:
                        filtro_re = filtro_re & Q(fecha_creacion__date__lte=hasta)
                        filtro_asi = filtro_asi & Q(fecha_creacion__date__lte=hasta)
                        filtro_tot = filtro_tot & Q(fecha_creacion__date__lte=hasta)
                        filtro_admi = filtro_admi & Q(fecha_aprobador__date__lte=hasta)
                        filtro_cunt = filtro_cunt & Q(fecha_aprobacion__date__lte=hasta)
                        filtro_venta = filtro_venta & Q(fecha__date__lte=hasta)

                    filas_recorridas = 4
                    cont = 1

                    sumreservados = sumasignados = sumproceso = sumadmitidos = sumaprobadoscon = sumpagos = 0
                    for asesor in asesores:
                        reservados = asignados = leads = proceso = admitidos = aprobadoscon = pagos = 0

                        reservados = HistorialReservacionProspecto.objects.filter(filtro_re, persona=asesor.persona).values_list('inscripcion__id', flat=True).order_by('inscripcion__id').distinct().count()
                        asignados = HistorialAsesor.objects.filter(filtro_asi, asesor=asesor).values_list('inscripcion__id', flat=True).order_by('inscripcion__id').distinct().count()
                        # leads = InscripcionCohorte.objects.filter(filtro_tot, asesor=asesor).values_list('id', flat=True).order_by('id').distinct().count()
                        proceso = InscripcionCohorte.objects.filter(filtro_tot, estado_aprobador=1, asesor=asesor).values_list('id', flat=True).order_by('id').distinct().count()
                        admitidos = InscripcionCohorte.objects.filter(filtro_admi, asesor=asesor).values_list('id', flat=True).order_by('id').distinct().count()
                        aprobadoscon = DetalleAprobacionContrato.objects.filter(filtro_cunt, contrato__inscripcion__asesor=asesor).values_list('contrato__inscripcion__id', flat=True).order_by('contrato__inscripcion__id').distinct().count()
                        pagos = VentasProgramaMaestria.objects.filter(filtro_venta, asesor=asesor).values_list('inscripcioncohorte__id', flat=True).order_by('inscripcioncohorte__id').distinct().count()

                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(asesor.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, reservados, decimalformat)
                        ws.write('D%s' % filas_recorridas, asignados, decimalformat)
                        # ws.write('E%s' % filas_recorridas, leads, decimalformat)
                        ws.write('E%s' % filas_recorridas, proceso, decimalformat)
                        ws.write('F%s' % filas_recorridas, admitidos, decimalformat)
                        ws.write('G%s' % filas_recorridas, aprobadoscon, decimalformat)
                        ws.write('H%s' % filas_recorridas, pagos, decimalformat)

                        filas_recorridas += 1
                        cont += 1

                        sumreservados += reservados
                        sumasignados += asignados
                        sumproceso += proceso
                        sumadmitidos += admitidos
                        sumaprobadoscon += aprobadoscon
                        sumpagos += pagos

                    ws.merge_range('A%s:B%s' % (filas_recorridas, filas_recorridas), 'TOTALES:', formatoceldaleft3)

                    ws.write('C%s' % filas_recorridas, sumreservados, decimalformat2)
                    ws.write('D%s' % filas_recorridas, sumasignados, decimalformat2)
                    ws.write('E%s' % filas_recorridas, sumproceso, decimalformat2)
                    ws.write('F%s' % filas_recorridas, sumadmitidos, decimalformat2)
                    ws.write('G%s' % filas_recorridas, sumaprobadoscon, decimalformat2)
                    ws.write('H%s' % filas_recorridas, sumpagos, decimalformat2)

                    workbook.close()
                    output.seek(0)
                    fecha_hora_actual = datetime.now().date()
                    filename = 'Resumen_asesores_' + str(fecha_hora_actual) + '.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'resumen_leads_asignados':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('resumen')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 40)
                    ws.set_column(2, 2, 25)
                    ws.set_column(3, 3, 25)
                    ws.set_column(4, 4, 20)
                    ws.set_column(5, 5, 20)
                    ws.set_column(6, 6, 20)
                    ws.set_column(7, 7, 20)
                    ws.set_column(8, 8, 20)
                    ws.set_column(9, 9, 20)
                    ws.set_column(10, 10, 20)
                    ws.set_column(11, 11, 20)
                    ws.set_column(12, 12, 20)
                    ws.set_column(13, 13, 20)
                    ws.set_column(14, 14, 20)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
                    decimalformat2 = workbook.add_format({'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    asesor = cohorte = 0
                    desde = hasta = ''

                    if 'cohorte' in request.GET:
                        cohorte = request.GET['cohorte']
                    if 'asesor' in request.GET:
                        asesor = request.GET['asesor']

                    if 'desde' in request.GET:
                        desde = request.GET['desde']
                    if 'hasta' in request.GET:
                        hasta = request.GET['hasta']

                    ws.merge_range('A1:O1', 'Resumen de leads por asesor', formatotitulo_filtros)
                    if desde and hasta:
                        ws.merge_range('A2:O2', 'Desde el ' + desde + ' hasta el ' + hasta, formatotitulo_filtros)

                    ws.write(2, 0, 'N°', formatoceldacab)
                    ws.write(2, 1, 'Asesor comercial', formatoceldacab)
                    ws.write(2, 2, '# Leads reservados', formatoceldacab)
                    ws.write(2, 3, '# Leads asignados', formatoceldacab)
                    ws.write(2, 4, '# de leads activos', formatoceldacab)
                    ws.write(2, 5, '# de leads inactivos', formatoceldacab)
                    ws.write(2, 6, '# de leads en proceso', formatoceldacab)
                    ws.write(2, 7, '# de leads admitidos', formatoceldacab)
                    ws.write(2, 8, '# de leads rechazados', formatoceldacab)
                    ws.write(2, 9, '# de leads sin contrato', formatoceldacab)
                    ws.write(2, 10, '# de contratos en proceso', formatoceldacab)
                    ws.write(2, 11, '# de contratos aprobados', formatoceldacab)
                    ws.write(2, 12, '# de contratos rechazados', formatoceldacab)
                    ws.write(2, 13, '# de pagos registrados', formatoceldacab)
                    ws.write(2, 14, '# de leads no vendidos', formatoceldacab)

                    filtro = Q(status=True, activo=True)
                    filtro_asi = Q(id__gte=0)

                    if cohorte != "":
                        lista_cadenas = ast.literal_eval(request.GET['cohorte'])
                        lista_enteros = list(map(int, lista_cadenas))

                        if len(lista_enteros) > 0 and 0 not in lista_enteros:
                            filtro_asi = filtro_asi & Q(inscripcion__cohortes__id__in=lista_enteros)

                    if asesor != "":
                        lista_cadenas_a = ast.literal_eval(request.GET['asesor'])
                        lista_enteros_a = list(map(int, lista_cadenas_a))

                        if len(lista_enteros_a) > 0 and 0 not in lista_enteros_a:
                            filtro = filtro & Q(id__in=lista_enteros_a)

                    asesores = AsesorComercial.objects.filter(filtro).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    if desde and hasta:
                        filtro_asi = filtro_asi & Q(fecha_creacion__date__range=(desde, hasta))

                    elif desde:
                        filtro_asi = filtro_asi & Q(fecha_creacion__date__gte=desde)

                    elif hasta:
                        filtro_asi = filtro_asi & Q(fecha_creacion__date__lte=hasta)

                    filas_recorridas = 4
                    cont = 1

                    sumreservados = sumasignados = sumproceso = sumadmitidos = sumactivos = suminactivos = sumrechazados = sumprocesocon =sumaprobadoscon = sumrachazadoscon = sumpagos = sumtot = sumtot2  = 0
                    for asesor in asesores:
                        reservados = asignados = proceso = activos = inactivos =  admitidos = rechazados = procesocon = aprobadoscon = rachazadoscon = pagos = 0
                        idasignados = HistorialAsesor.objects.filter(filtro_asi, asesor=asesor).values_list('inscripcion__id', flat=True).order_by('inscripcion__id').distinct()
                        asignados = HistorialAsesor.objects.filter(inscripcion__id__in=idasignados).values_list('inscripcion__id', flat=True).order_by('inscripcion__id').distinct().count()
                        activos = InscripcionCohorte.objects.filter(id__in=idasignados, status=True).values_list('id', flat=True).order_by('id').distinct().count()
                        idactivos = InscripcionCohorte.objects.filter(id__in=idasignados, status=True).values_list('id', flat=True).order_by('id').distinct()
                        inactivos = InscripcionCohorte.objects.filter(id__in=idasignados, status=False).values_list('id', flat=True).order_by('id').distinct().count()
                        reservados = HistorialReservacionProspecto.objects.filter(inscripcion__status=True, persona=asesor.persona, inscripcion__id__in=idactivos).values_list('inscripcion__id', flat=True).order_by('inscripcion__id').distinct().count()
                        proceso = InscripcionCohorte.objects.filter(estado_aprobador=1, id__in=idactivos).values_list('id', flat=True).order_by('id').distinct().count()
                        admitidos = InscripcionCohorte.objects.filter(estado_aprobador=2, id__in=idactivos).values_list('id', flat=True).order_by('id').distinct().count()
                        rechazados = InscripcionCohorte.objects.filter(estado_aprobador=3, id__in=idasignados).values_list('id', flat=True).order_by('id').distinct().count()
                        procesocon = Contrato.objects.filter(estado=1, inscripcion__id__in=idactivos).values_list('inscripcion__id', flat=True).order_by('inscripcion__id').distinct().count()
                        aprobadoscon = Contrato.objects.filter(estado=2, inscripcion__id__in=idactivos).values_list('inscripcion__id', flat=True).order_by('inscripcion__id').distinct().count()
                        rachazadoscon = Contrato.objects.filter(estado=3, inscripcion__id__in=idactivos).values_list('inscripcion__id', flat=True).order_by('inscripcion__id').distinct().count()
                        pagos = VentasProgramaMaestria.objects.filter(asesor=asesor, inscripcioncohorte__id__in=idactivos).values_list('inscripcioncohorte__id', flat=True).order_by('inscripcioncohorte__id').distinct().count()

                        cant1 = procesocon + aprobadoscon + rachazadoscon
                        cant2 = activos
                        tot = 0
                        tot2 = 0
                        if cant1 > cant2:
                            tot = cant1 - cant2
                        else:
                            tot = cant2 - cant1

                        if activos > pagos:
                            tot2 = activos - pagos
                        else:
                            tot2 = pagos - activos

                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(asesor.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, reservados, decimalformat)
                        ws.write('D%s' % filas_recorridas, asignados, decimalformat)
                        ws.write('E%s' % filas_recorridas, activos, decimalformat)
                        ws.write('F%s' % filas_recorridas, inactivos, decimalformat)
                        ws.write('G%s' % filas_recorridas, proceso, decimalformat)
                        ws.write('H%s' % filas_recorridas, admitidos, decimalformat)
                        ws.write('I%s' % filas_recorridas, rechazados, decimalformat)
                        ws.write('J%s' % filas_recorridas, tot, decimalformat)
                        ws.write('K%s' % filas_recorridas, procesocon, decimalformat)
                        ws.write('L%s' % filas_recorridas, aprobadoscon, decimalformat)
                        ws.write('M%s' % filas_recorridas, rachazadoscon, decimalformat)
                        ws.write('N%s' % filas_recorridas, pagos, decimalformat)
                        ws.write('O%s' % filas_recorridas, tot2, decimalformat)

                        filas_recorridas += 1
                        cont += 1

                        sumreservados += reservados
                        sumasignados += asignados
                        sumactivos += activos
                        suminactivos += inactivos
                        sumproceso += proceso
                        sumadmitidos += admitidos
                        sumrechazados += rechazados
                        sumprocesocon += procesocon
                        sumaprobadoscon += aprobadoscon
                        sumrachazadoscon += rachazadoscon
                        sumpagos += pagos
                        sumtot += tot
                        sumtot2 += tot2

                    ws.merge_range('A%s:B%s' % (filas_recorridas, filas_recorridas), 'TOTALES:', formatoceldaleft3)

                    ws.write('C%s' % filas_recorridas, sumreservados, decimalformat2)
                    ws.write('D%s' % filas_recorridas, sumasignados, decimalformat2)
                    ws.write('E%s' % filas_recorridas, sumactivos, decimalformat2)
                    ws.write('F%s' % filas_recorridas, suminactivos, decimalformat2)
                    ws.write('G%s' % filas_recorridas, sumproceso, decimalformat2)
                    ws.write('H%s' % filas_recorridas, sumadmitidos, decimalformat2)
                    ws.write('I%s' % filas_recorridas, sumrechazados, decimalformat2)
                    ws.write('J%s' % filas_recorridas, sumtot, decimalformat2)
                    ws.write('K%s' % filas_recorridas, sumprocesocon, decimalformat2)
                    ws.write('L%s' % filas_recorridas, sumaprobadoscon, decimalformat2)
                    ws.write('M%s' % filas_recorridas, sumrachazadoscon, decimalformat2)
                    ws.write('N%s' % filas_recorridas, sumpagos, decimalformat2)
                    ws.write('O%s' % filas_recorridas, sumtot2, decimalformat2)

                    workbook.close()
                    output.seek(0)
                    fecha_hora_actual = datetime.now().date()
                    filename = 'Resumen_asignados_' + str(fecha_hora_actual) + '.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporteleadsasignados':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('leads_asignados')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 15)
                    ws.set_column(2, 2, 15)
                    ws.set_column(3, 3, 45)
                    ws.set_column(4, 4, 35)
                    ws.set_column(5, 5, 45)
                    ws.set_column(6, 6, 15)
                    ws.set_column(7, 7, 20)
                    ws.set_column(8, 8, 40)
                    ws.set_column(9, 9, 45)
                    ws.set_column(10, 10, 20)
                    ws.set_column(11, 11, 45)
                    ws.set_column(12, 12, 45)
                    ws.set_column(13, 13, 25)
                    ws.set_column(14, 14, 25)
                    ws.set_column(15, 15, 25)
                    ws.set_column(16, 16, 25)
                    ws.set_column(17, 17, 25)
                    ws.set_column(18, 18, 25)
                    ws.set_column(19, 19, 25)
                    ws.set_column(20, 20, 15)
                    ws.set_column(21, 21, 15)
                    ws.set_column(22, 22, 15)
                    ws.set_column(23, 23, 15)
                    ws.set_column(24, 24, 35)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    ws.merge_range('A1:Q1', 'Reporte de leads asignados', formatotitulo_filtros)
                    ws.write(1, 0, 'N°', formatoceldacab)
                    ws.write(1, 1, 'Id', formatoceldacab)
                    ws.write(1, 2, 'Cédula', formatoceldacab)
                    ws.write(1, 3, 'Prospecto', formatoceldacab)
                    ws.write(1, 4, 'Cohorte', formatoceldacab)
                    ws.write(1, 5, 'Maestría', formatoceldacab)
                    ws.write(1, 6, 'Fecha de registro', formatoceldacab)
                    ws.write(1, 7, 'Teléfono', formatoceldacab)
                    ws.write(1, 8, 'Correo', formatoceldacab)
                    ws.write(1, 9, 'Asesor', formatoceldacab)
                    ws.write(1, 10, 'Estado de aprobación', formatoceldacab)
                    ws.write(1, 11, 'Fecha de asignación', formatoceldacab)
                    ws.write(1, 12, 'Estado de atención', formatoceldacab)
                    ws.write(1, 13, 'Ingreso al sistema', formatoceldacab)
                    ws.write(1, 14, 'Forma de pago', formatoceldacab)
                    ws.write(1, 15, 'Cuadrado Unemi', formatoceldacab)
                    ws.write(1, 16, 'Cuadrado Epunemi', formatoceldacab)
                    ws.write(1, 17, 'Canceló cuota inicial', formatoceldacab)
                    ws.write(1, 18, 'Tiene matrícula?', formatoceldacab)
                    ws.write(1, 19, 'Está retirado?', formatoceldacab)
                    ws.write(1, 20, 'Canal de información', formatoceldacab)
                    ws.write(1, 21, '¿Activo?', formatoceldacab)
                    ws.write(1, 22, '¿Migrado?', formatoceldacab)
                    ws.write(1, 23, 'Fecha de migración', formatoceldacab)
                    ws.write(1, 24, 'Obsevación de migración', formatoceldacab)


                    estado = maestria = cohorte = estado_mat = 0
                    desde = hasta = ''

                    if 'maestria' in request.GET:
                        maestria = request.GET['maestria']
                    if 'cohorte' in request.GET:
                        cohorte = request.GET['cohorte']
                    if 'estado' in request.GET:
                        estado = request.GET['estado']
                    if 'estado_mat' in request.GET:
                        estado_mat = request.GET['estado_mat']

                    if 'desde' in request.GET:
                        desde = request.GET['desde']
                    if 'hasta' in request.GET:
                        hasta = request.GET['hasta']

                    filtro = Q(status=True, asesor__persona__id=persona.id, cohortes__maestriaadmision__carrera__coordinacion__id=7)

                    if cohorte != "":
                        if eval(request.GET['cohorte'])[0] != "0":
                            filtro = filtro & Q(cohortes__id__in=eval(request.GET['cohorte']))

                    if estado != "":
                        estado = int(estado)
                        if estado == 1:
                            filtro = filtro & Q(estado_aprobador=1)
                        elif estado == 2:
                            filtro = filtro & Q(estado_aprobador=2)
                        elif estado == 3:
                            filtro = filtro & Q(estado_aprobador=3)
                        elif estado == 4:
                            filtro = filtro & Q(formapagopac_id=1)
                        elif estado == 5:
                            filtro = filtro & Q(formapagopac_id=2)
                        elif estado == 6:
                            filtro = filtro & Q(es_becado=True)
                        elif estado == 7:
                            idquery = CambioAdmitidoCohorteInscripcion.objects.filter(status=True).values_list('inscripcionCohorte__id', flat=True).order_by('inscripcionCohorte__id').distinct()
                            filtro = filtro & Q(id__in=idquery)

                    if estado_mat != "":
                        estado_mat = int(estado_mat)
                        if estado_mat > 0:
                            if estado_mat == 1:
                                filtro = filtro & Q(tiporespuesta__isnull=True)
                            else:
                                filtro = filtro & Q(tiporespuesta__id=estado_mat)


                    if desde and hasta:
                        filtro = filtro & Q(fecha_creacion__date__range=(desde, hasta))

                    elif desde:
                        filtro = filtro & Q(fecha_creacion__date__gte=desde)

                    elif hasta:
                        filtro = filtro & Q(fecha_creacion__date__lte=hasta)


                    leads = InscripcionCohorte.objects.filter(filtro).order_by(
                        'cohortes__maestriaadmision__carrera',
                        'inscripcionaspirante__persona__apellido1',
                        'inscripcionaspirante__persona__apellido2',
                        'inscripcionaspirante__persona__nombres')

                    filas_recorridas = 3
                    cont = 1

                    for lead in leads:
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(lead.id), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.cedula), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(lead.cohortes.descripcion), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(lead.cohortes.maestriaadmision.descripcion), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(lead.fecha_creacion.date()), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.telefono), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.email), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str(lead.asesor.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('K%s' % filas_recorridas, str(lead.get_estado_aprobador_display()), formatoceldaleft)
                        ws.write('L%s' % filas_recorridas, str(lead.fecha_asignacion_asesor().date()), formatoceldaleft)
                        ws.write('M%s' % filas_recorridas, str(lead.tiporespuesta.descripcion if lead.tiporespuesta else 'PENDIENTE'), formatoceldaleft)
                        ws.write('N%s' % filas_recorridas, str(lead.acceso_sistema()), formatoceldaleft)
                        ws.write('O%s' % filas_recorridas, str(lead.formapagopac.descripcion if lead.formapagopac else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('P%s' % filas_recorridas, str('SI' if lead.tiene_rubro_cuadrado() == True else 'NO'), formatoceldaleft)
                        ws.write('Q%s' % filas_recorridas, str('SI' if lead.cuadre_con_epunemi() == True else 'NO'), formatoceldaleft)
                        ws.write('R%s' % filas_recorridas, str('SI' if lead.pago_rubro_matricula() == True else 'NO'), formatoceldaleft)
                        ws.write('S%s' % filas_recorridas, str('SI' if lead.tiene_matricula_cohorte() == True else 'NO'), formatoceldaleft)
                        ws.write('T%s' % filas_recorridas, str('SI' if lead.retirado_matricula() == True else 'NO'), formatoceldaleft)
                        ws.write('U%s' % filas_recorridas, str(lead.canal.descripcion if lead.canal else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('V%s' % filas_recorridas, str('SI' if lead.status else 'NO'), formatoceldaleft)
                        ws.write('W%s' % filas_recorridas, str('SI' if lead.cambioadmitido() else 'NO'), formatoceldaleft)
                        ws.write('X%s' % filas_recorridas, str(lead.cambioadmitido().fecha_creacion.date() if lead.cambioadmitido() else 'NO'), formatoceldaleft)
                        ws.write('Y%s' % filas_recorridas, str(lead.cambioadmitido().observacion if lead.cambioadmitido() and lead.cambioadmitido().observacion else 'NINGUNA'), formatoceldaleft)

                        filas_recorridas += 1
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'Reporte_Leads_Asignados.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporteleadsasignadosdesactivados':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('leads_asignados_desactivados')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 15)
                    ws.set_column(2, 2, 15)
                    ws.set_column(3, 3, 45)
                    ws.set_column(4, 4, 35)
                    ws.set_column(5, 5, 45)
                    ws.set_column(6, 6, 15)
                    ws.set_column(7, 7, 20)
                    ws.set_column(8, 8, 40)
                    ws.set_column(9, 9, 45)
                    ws.set_column(10, 10, 20)
                    ws.set_column(11, 11, 45)
                    ws.set_column(12, 12, 45)
                    ws.set_column(13, 13, 25)
                    ws.set_column(14, 14, 25)
                    ws.set_column(15, 15, 25)
                    ws.set_column(16, 16, 25)
                    ws.set_column(17, 17, 25)
                    ws.set_column(18, 18, 15)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    ws.merge_range('A1:S1', 'Reporte de leads asignados desactivados', formatotitulo_filtros)
                    ws.write(1, 0, 'N°', formatoceldacab)
                    ws.write(1, 1, 'Id', formatoceldacab)
                    ws.write(1, 2, 'Cédula', formatoceldacab)
                    ws.write(1, 3, 'Prospecto', formatoceldacab)
                    ws.write(1, 4, 'Cohorte', formatoceldacab)
                    ws.write(1, 5, 'Maestría', formatoceldacab)
                    ws.write(1, 6, 'Fecha de registro', formatoceldacab)
                    ws.write(1, 7, 'Teléfono', formatoceldacab)
                    ws.write(1, 8, 'Correo', formatoceldacab)
                    ws.write(1, 9, 'Asesor', formatoceldacab)
                    ws.write(1, 10, 'Estado de aprobación', formatoceldacab)
                    ws.write(1, 11, 'Fecha de asignación', formatoceldacab)
                    ws.write(1, 12, 'Estado de atención', formatoceldacab)
                    ws.write(1, 13, 'Ingreso al sistema', formatoceldacab)
                    ws.write(1, 14, 'Forma de pago', formatoceldacab)
                    ws.write(1, 15, 'Canceló cuota inicial', formatoceldacab)
                    ws.write(1, 16, 'Tiene matrícula?', formatoceldacab)
                    ws.write(1, 17, 'Está retirado?', formatoceldacab)
                    ws.write(1, 18, 'Canal de información', formatoceldacab)


                    estado = maestria = cohorte = estado_mat = 0
                    desde = hasta = ''

                    if 'maestria' in request.GET:
                        maestria = request.GET['maestria']
                    if 'cohorte' in request.GET:
                        cohorte = request.GET['cohorte']
                    if 'estado' in request.GET:
                        estado = request.GET['estado']
                    if 'estado_mat' in request.GET:
                        estado_mat = request.GET['estado_mat']

                    if 'desde' in request.GET:
                        desde = request.GET['desde']
                    if 'hasta' in request.GET:
                        hasta = request.GET['hasta']

                    filtro = Q(status=False, asesor__persona__id=persona.id, cohortes__maestriaadmision__carrera__coordinacion__id=7)

                    if cohorte != "":
                        if eval(request.GET['cohorte'])[0] != "0":
                            filtro = filtro & Q(cohortes__id__in=eval(request.GET['cohorte']))

                    if estado != "":
                        estado = int(estado)
                        if estado == 1:
                            filtro = filtro & Q(estado_aprobador=1)
                        elif estado == 2:
                            filtro = filtro & Q(estado_aprobador=2)
                        elif estado == 3:
                            filtro = filtro & Q(estado_aprobador=3)
                        elif estado == 4:
                            filtro = filtro & Q(formapagopac_id=1)
                        elif estado == 5:
                            filtro = filtro & Q(formapagopac_id=2)

                    if estado_mat != "":
                        estado_mat = int(estado_mat)
                        if estado_mat > 0:
                            if estado_mat == 1:
                                filtro = filtro & Q(tiporespuesta__isnull=True)
                            else:
                                filtro = filtro & Q(tiporespuesta__id=estado_mat)


                    if desde and hasta:
                        filtro = filtro & Q(fecha_creacion__range=(desde, hasta))

                    elif desde:
                        filtro = filtro & Q(fecha_creacion__gte=desde)

                    elif hasta:
                        filtro = filtro & Q(fecha_creacion__lte=hasta)


                    leads = InscripcionCohorte.objects.filter(filtro).order_by(
                        'cohortes__maestriaadmision__carrera',
                        'inscripcionaspirante__persona__apellido1',
                        'inscripcionaspirante__persona__apellido2',
                        'inscripcionaspirante__persona__nombres')

                    filas_recorridas = 3
                    cont = 1

                    for lead in leads:
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(lead.id), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.cedula), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(lead.cohortes.descripcion), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(lead.cohortes.maestriaadmision.descripcion), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(lead.fecha_creacion.date()), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.telefono), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.email), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str(lead.asesor.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('K%s' % filas_recorridas, str(lead.get_estado_aprobador_display()), formatoceldaleft)
                        ws.write('L%s' % filas_recorridas, str(lead.fecha_asignacion_asesor().date()), formatoceldaleft)
                        ws.write('M%s' % filas_recorridas, str(lead.tiporespuesta.descripcion if lead.tiporespuesta else 'PENDIENTE'), formatoceldaleft)
                        ws.write('N%s' % filas_recorridas, str(lead.acceso_sistema()), formatoceldaleft)
                        ws.write('O%s' % filas_recorridas, str(lead.formapagopac.descripcion if lead.formapagopac else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('P%s' % filas_recorridas, str('SI' if lead.pago_rubro_matricula() == True else 'NO'), formatoceldaleft)
                        ws.write('Q%s' % filas_recorridas, str('SI' if lead.tiene_matricula_cohorte() == True else 'NO'), formatoceldaleft)
                        ws.write('R%s' % filas_recorridas, str('SI' if lead.retirado_matricula() == True else 'NO'), formatoceldaleft)
                        ws.write('S%s' % filas_recorridas, str(lead.canal.descripcion if lead.canal else 'NO REGISTRA'), formatoceldaleft)

                        filas_recorridas += 1
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'Reporte_Leads_Desactivados.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reportecontratosposgrado':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('contratos')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 15)
                    ws.set_column(2, 2, 15)
                    ws.set_column(3, 3, 20)
                    ws.set_column(4, 4, 35)
                    ws.set_column(5, 5, 40)
                    ws.set_column(6, 6, 45)
                    ws.set_column(7, 7, 30)
                    ws.set_column(8, 8, 50)
                    ws.set_column(9, 9, 25)
                    ws.set_column(10, 10, 20)
                    ws.set_column(11, 11, 45)
                    ws.set_column(12, 12, 40)
                    ws.set_column(13, 13, 45)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    ws.merge_range('A1:L1', 'REPORTE DE CONTRATOS POSGRADO', formatotitulo_filtros)
                    # ws.merge_range('A2:K2', 'VENTAS' + asesorme.cohorte.maestriaadmision.descripcion.replace("MAESTRÍA", ""), formatoceldacab)
                    ws.write(1, 0, 'N°', formatoceldacab)
                    ws.write(1, 1, 'ID CONTRATO', formatoceldacab)
                    ws.write(1, 2, 'ID INS.', formatoceldacab)
                    ws.write(1, 3, 'CÉDULA', formatoceldacab)
                    ws.write(1, 4, 'PROSPECTO', formatoceldacab)
                    ws.write(1, 5, 'MAESTRIA', formatoceldacab)
                    ws.write(1, 6, 'COHORTE', formatoceldacab)
                    ws.write(1, 7, 'FORMA DE PAGO', formatoceldacab)
                    ws.write(1, 8, 'ARCHIVO', formatoceldacab)
                    ws.write(1, 9, 'FECHA DE APROBACION/RECHAZO', formatoceldacab)
                    ws.write(1, 10, 'ESTADO_CONTRATO', formatoceldacab)
                    ws.write(1, 11, 'OBSERVACIÓN', formatoceldacab)
                    ws.write(1, 12, 'ASESOR', formatoceldacab)
                    ws.write(1, 13, 'TIPO DE FINANCIAMIENTO', formatoceldacab)

                    estado = maestria = cohorte = formapago = 0
                    desde = hasta = ''
                    ids_insc = []

                    if 'cohorte' in request.GET:
                        cohorte = request.GET['cohorte']
                    if 'estado' in request.GET:
                        estado = int(request.GET['estado'])
                    if 'formapago' in request.GET:
                        formapago = int(request.GET['formapago'])
                    if 'desde' in request.GET:
                        desde = request.GET['desde']
                    if 'hasta' in request.GET:
                        hasta = request.GET['hasta']

                    filtro = Q(status=True)

                    if cohorte != "":
                        if eval(request.GET['cohorte'])[0] != "0":
                            filtro = filtro & Q(inscripcion__cohortes__id__in=eval(request.GET['cohorte']))
                        else:
                            cohortes_incluidas = []
                            cohortes_ofertadas = CohorteMaestria.objects.filter(status=True).order_by('-fecha_creacion')
                            for chor in cohortes_ofertadas:
                                fecha_aumentada = chor.fechafininsp + relativedelta(months=6)
                                fecha_actual = datetime.now().date()
                                if fecha_aumentada > fecha_actual:
                                    cohortes_incluidas.append(chor.id)
                            filtro = filtro & Q(inscripcion__cohortes__id__in=cohortes_incluidas)

                    if formapago > 0:
                        filtro = filtro & Q(inscripcion__formapagopac__id=formapago)

                    contra_pen = []
                    contra_apro = []
                    contra_rech = []
                    if estado > 0:
                        contratos = Contrato.objects.filter(filtro)
                        if estado == 1:
                            for con in contratos:
                                if con.archivocontrato:
                                    if con.detalleaprobacioncontrato_set.filter(status=True, espagare=False).exists():
                                        evicon = con.detalleaprobacioncontrato_set.filter(status=True, espagare=False).order_by('-id')[0]
                                        if evicon.esta_con_pendiente():
                                            contra_pen.append(con.id)

                            contratos = Contrato.objects.filter(filtro & Q(id__in=contra_pen)).order_by('inscripcion__inscripcionaspirante__persona__apellido1', 'inscripcion__inscripcionaspirante__persona__apellido2', 'inscripcion__inscripcionaspirante__persona__nombres')

                        elif estado == 2:
                            for con in contratos:
                                if con.archivocontrato:
                                    if con.detalleaprobacioncontrato_set.filter(status=True, espagare=False).exists():
                                        evicon = con.detalleaprobacioncontrato_set.filter(status=True, espagare=False).order_by('-id')[0]
                                        if evicon.esta_aprobado():
                                            contra_apro.append(con.id)

                            contratos = Contrato.objects.filter(filtro & Q(id__in=contra_apro)).order_by('inscripcion__inscripcionaspirante__persona__apellido1', 'inscripcion__inscripcionaspirante__persona__apellido2', 'inscripcion__inscripcionaspirante__persona__nombres')

                        elif estado == 3:
                            for con in contratos:
                                if con.archivocontrato:
                                    if con.detalleaprobacioncontrato_set.filter(status=True, espagare=False).exists():
                                        evicon = con.detalleaprobacioncontrato_set.filter(status=True, espagare=False).order_by('-id')[0]
                                        if evicon.esta_con_rechazado():
                                            contra_rech.append(con.id)

                            contratos = Contrato.objects.filter(filtro & Q(id__in=contra_rech)).order_by('inscripcion__inscripcionaspirante__persona__apellido1', 'inscripcion__inscripcionaspirante__persona__apellido2', 'inscripcion__inscripcionaspirante__persona__nombres')

                    else:
                        contratos = Contrato.objects.filter(filtro).order_by(
                            'inscripcion__inscripcionaspirante__persona__apellido1',
                            'inscripcion__inscripcionaspirante__persona__apellido2',
                            'inscripcion__inscripcionaspirante__persona__nombres')


                    if desde and hasta:
                        desde = datetime.strptime(desde, '%Y-%m-%d').date()
                        hasta = datetime.strptime(hasta, '%Y-%m-%d').date()
                        for lead in contratos:
                            if lead.ultima_evidencia() and lead.ultima_evidencia().fecha_creacion.date() >= desde and lead.ultima_evidencia().fecha_creacion.date() <= hasta:
                                ids_insc.append(int(lead.id))
                    elif desde:
                        desde = datetime.strptime(desde, '%Y-%m-%d').date()
                        for lead in contratos:
                            if lead.ultima_evidencia() and lead.ultima_evidencia().fecha_creacion.date() >= desde:
                                ids_insc.append(int(lead.id))
                    elif hasta:
                        hasta = datetime.strptime(hasta, '%Y-%m-%d').date()
                        for lead in contratos:
                            if lead.ultima_evidencia() and lead.ultima_evidencia().fecha_creacion.date() <= hasta:
                                ids_insc.append(int(lead.id))

                    if ids_insc:
                        contratos = contratos.filter(id__in=ids_insc)

                    filas_recorridas = 3
                    cont = 1

                    for contrato in contratos:
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(contrato.id), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(contrato.inscripcion.id), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(contrato.inscripcion.inscripcionaspirante.persona.cedula), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(contrato.inscripcion.inscripcionaspirante.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(contrato.inscripcion.cohortes.maestriaadmision.descripcion), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(contrato.inscripcion.cohortes.descripcion), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(contrato.inscripcion.formapagopac.descripcion), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str(contrato.archivocontrato if contrato.archivocontrato else 'NO HA SUBIDO CONTRATO'), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str(contrato.ultima_evidencia().fecha_creacion.date() if contrato.archivocontrato else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('K%s' % filas_recorridas, str(contrato.ultima_evidencia_estado() if contrato.archivocontrato else 'NO HA SUBIDO CONTRATO'), formatoceldaleft)
                        ws.write('L%s' % filas_recorridas, str(contrato.ultima_evidencia().observacion if contrato.archivocontrato else 'NO HA SUBIDO CONTRATO'), formatoceldaleft)
                        ws.write('M%s' % filas_recorridas, str(contrato.inscripcion.asesor if contrato.inscripcion.asesor else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('N%s' % filas_recorridas, str(contrato.inscripcion.Configfinanciamientocohorte if contrato.inscripcion.Configfinanciamientocohorte else 'NO REGISTRA'), formatoceldaleft)

                        filas_recorridas += 1
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'Reporte_Contratos_Posgrado.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reportepagaresposgrado':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('pagares')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 15)
                    ws.set_column(2, 2, 15)
                    ws.set_column(3, 3, 20)
                    ws.set_column(4, 4, 35)
                    ws.set_column(5, 5, 40)
                    ws.set_column(6, 6, 45)
                    ws.set_column(7, 7, 50)
                    ws.set_column(8, 8, 25)
                    ws.set_column(9, 9, 20)
                    ws.set_column(10, 10, 45)
                    ws.set_column(11, 11, 40)
                    ws.set_column(12, 12, 45)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    ws.merge_range('A1:L1', 'REPORTE DE PAGARES POSGRADO', formatotitulo_filtros)
                    # ws.merge_range('A2:K2', 'VENTAS' + asesorme.cohorte.maestriaadmision.descripcion.replace("MAESTRÍA", ""), formatoceldacab)
                    ws.write(1, 0, 'N°', formatoceldacab)
                    ws.write(1, 1, 'ID CONTRATO', formatoceldacab)
                    ws.write(1, 2, 'ID INS.', formatoceldacab)
                    ws.write(1, 3, 'CÉDULA', formatoceldacab)
                    ws.write(1, 4, 'PROSPECTO', formatoceldacab)
                    ws.write(1, 5, 'MAESTRIA', formatoceldacab)
                    ws.write(1, 6, 'COHORTE', formatoceldacab)
                    ws.write(1, 7, 'ARCHIVO', formatoceldacab)
                    ws.write(1, 8, 'FECHA DE APROBACION/RECHAZO', formatoceldacab)
                    ws.write(1, 9, 'ESTADO_CONTRATO', formatoceldacab)
                    ws.write(1, 10, 'OBSERVACIÓN', formatoceldacab)
                    ws.write(1, 11, 'ASESOR', formatoceldacab)
                    ws.write(1, 12, 'TIPO DE FINANCIAMIENTO', formatoceldacab)

                    estado = maestria = cohorte = 0
                    desde = hasta = ''
                    ids_insc = []
                    # if 'maestria' in request.GET:
                    #     maestria = int(request.GET['maestria'])
                    # if 'cohorte' in request.GET:
                    #     cohorte = int(request.GET['cohorte'])
                    if 'cohorte' in request.GET:
                        cohorte = request.GET['cohorte']
                    if 'estado' in request.GET:
                        estado = int(request.GET['estado'])
                    if 'desde' in request.GET:
                        desde = request.GET['desde']
                    if 'hasta' in request.GET:
                        hasta = request.GET['hasta']

                    idpagares = []
                    idcontratos = Contrato.objects.filter(status=True)
                    for idcon in idcontratos:
                        if idcon.archivopagare:
                            if idcon.detalleaprobacioncontrato_set.filter(status=True, espagare=True).exists():
                                idpagares.append(idcon.id)

                    filtro = Q(status=True, id__in=idpagares)

                    # if maestria > 0:
                    #     filtro = filtro & Q(inscripcion__cohortes__maestriaadmision__id=maestria)

                    # if cohorte > 0:
                    #     filtro = filtro & Q(inscripcion__cohortes__id=cohorte)

                    if cohorte != "":
                        if eval(request.GET['cohorte'])[0] != "0":
                            filtro = filtro & Q(inscripcion__cohortes__id__in=eval(request.GET['cohorte']))
                        else:
                            cohortes_incluidas = []
                            cohortes_ofertadas = CohorteMaestria.objects.filter(status=True).order_by('-fecha_creacion')
                            for chor in cohortes_ofertadas:
                                fecha_aumentada = chor.fechafininsp + relativedelta(months=6)
                                fecha_actual = datetime.now().date()
                                if fecha_aumentada > fecha_actual:
                                    cohortes_incluidas.append(chor.id)
                            filtro = filtro & Q(inscripcion__cohortes__id__in=cohortes_incluidas)

                    paga_pen = []
                    paga_apro = []
                    paga_rech = []
                    if estado > 0:
                        pagares = Contrato.objects.filter(filtro)
                        if estado == 1:
                            for paga in pagares:
                                if paga.archivopagare:
                                    if paga.detalleaprobacioncontrato_set.filter(status=True, espagare=True).exists():
                                        evipaga = paga.detalleaprobacioncontrato_set.filter(status=True, espagare=True).order_by('-id')[0]
                                        if evipaga.esta_con_pendiente():
                                            paga_pen.append(paga.id)

                            contratos = Contrato.objects.filter(filtro & Q(id__in=paga_pen)).order_by('inscripcion__inscripcionaspirante__persona__apellido1', 'inscripcion__inscripcionaspirante__persona__apellido2', 'inscripcion__inscripcionaspirante__persona__nombres')

                        elif estado == 2:
                            for paga in pagares:
                                if paga.archivopagare:
                                    if paga.detalleaprobacioncontrato_set.filter(status=True, espagare=True).exists():
                                        evipaga = paga.detalleaprobacioncontrato_set.filter(status=True, espagare=True).order_by('-id')[0]
                                        if evipaga.esta_aprobado():
                                            paga_apro.append(paga.id)

                            contratos = Contrato.objects.filter(filtro & Q(id__in=paga_apro)).order_by('inscripcion__inscripcionaspirante__persona__apellido1', 'inscripcion__inscripcionaspirante__persona__apellido2', 'inscripcion__inscripcionaspirante__persona__nombres')

                        elif estado == 3:
                            for paga in pagares:
                                if paga.archivopagare:
                                    if paga.detalleaprobacioncontrato_set.filter(status=True, espagare=True).exists():
                                        evipaga = paga.detalleaprobacioncontrato_set.filter(status=True, espagare=True).order_by('-id')[0]
                                        if evipaga.esta_con_rechazado():
                                            paga_rech.append(paga.id)

                            contratos = Contrato.objects.filter(filtro & Q(id__in=paga_rech)).order_by('inscripcion__inscripcionaspirante__persona__apellido1', 'inscripcion__inscripcionaspirante__persona__apellido2', 'inscripcion__inscripcionaspirante__persona__nombres')

                    else:
                        contratos = Contrato.objects.filter(filtro).order_by(
                            'inscripcion__inscripcionaspirante__persona__apellido1',
                            'inscripcion__inscripcionaspirante__persona__apellido2',
                            'inscripcion__inscripcionaspirante__persona__nombres')

                    if desde and hasta:
                        desde = datetime.strptime(desde, '%Y-%m-%d').date()
                        hasta = datetime.strptime(hasta, '%Y-%m-%d').date()
                        for lead in contratos:
                            if lead.ultima_evidenciapagare() and lead.ultima_evidenciapagare().fecha_creacion.date() >= desde and lead.ultima_evidenciapagare().fecha_creacion.date() <= hasta:
                                ids_insc.append(int(lead.id))
                    elif desde:
                        desde = datetime.strptime(desde, '%Y-%m-%d').date()
                        for lead in contratos:
                            if lead.ultima_evidenciapagare() and lead.ultima_evidenciapagare().fecha_creacion.date() >= desde:
                                ids_insc.append(int(lead.id))
                    elif hasta:
                        hasta = datetime.strptime(hasta, '%Y-%m-%d').date()
                        for lead in contratos:
                            if lead.ultima_evidenciapagare() and lead.ultima_evidenciapagare().fecha_creacion.date() <= hasta:
                                ids_insc.append(int(lead.id))

                    if ids_insc:
                        contratos = contratos.filter(id__in=ids_insc)

                    filas_recorridas = 3
                    cont = 1

                    for contrato in contratos:
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(contrato.id), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(contrato.inscripcion.id), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(contrato.inscripcion.inscripcionaspirante.persona.cedula), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(contrato.inscripcion.inscripcionaspirante.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(contrato.inscripcion.cohortes.maestriaadmision.descripcion), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(contrato.inscripcion.cohortes.descripcion), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(contrato.archivopagare if contrato.archivopagare else 'NO HA SUBIDO CONTRATO'), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str(contrato.ultima_evidenciapagare().fecha_creacion.date() if contrato.archivopagare else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str(contrato.ultima_evidenciapagare_estado() if contrato.archivopagare else 'NO HA SUBIDO CONTRATO'), formatoceldaleft)
                        ws.write('K%s' % filas_recorridas, str(contrato.ultima_evidenciapagare().observacion if contrato.archivopagare else 'NO HA SUBIDO CONTRATO'), formatoceldaleft)
                        ws.write('L%s' % filas_recorridas, str(contrato.inscripcion.asesor if contrato.inscripcion.asesor else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('M%s' % filas_recorridas, str(contrato.inscripcion.Configfinanciamientocohorte if contrato.inscripcion.Configfinanciamientocohorte else 'NO REGISTRA'), formatoceldaleft)

                        filas_recorridas += 1
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'Reporte_Pagares_Posgrado.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporterubrosdescuadre':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('rubros')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 15)
                    ws.set_column(2, 2, 15)
                    ws.set_column(3, 3, 45)
                    ws.set_column(4, 4, 35)
                    ws.set_column(5, 5, 45)
                    ws.set_column(6, 6, 15)
                    ws.set_column(7, 7, 20)
                    ws.set_column(8, 8, 20)
                    ws.set_column(9, 9, 20)
                    ws.set_column(10, 10, 20)
                    ws.set_column(11, 11, 20)
                    ws.set_column(12, 12, 20)
                    ws.set_column(13, 13, 20)
                    ws.set_column(14, 14, 45)
                    ws.set_column(15, 15, 40)
                    ws.set_column(16, 16, 15)
                    ws.set_column(17, 17, 15)
                    ws.set_column(18, 18, 25)
                    ws.set_column(19, 19, 25)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    ws.merge_range('A1:T1', 'REPORTE DE RUBROS', formatotitulo_filtros)
                    # ws.merge_range('A2:K2', 'VENTAS' + asesorme.cohorte.maestriaadmision.descripcion.replace("MAESTRÍA", ""), formatoceldacab)
                    ws.write(1, 0, 'N°', formatoceldacab)
                    ws.write(1, 1, 'ID', formatoceldacab)
                    ws.write(1, 2, 'CEDULA', formatoceldacab)
                    ws.write(1, 3, 'PROSPECTO', formatoceldacab)
                    ws.write(1, 4, 'COHORTE', formatoceldacab)
                    ws.write(1, 5, 'MAESTRIA', formatoceldacab)
                    ws.write(1, 6, 'FECHA DE REGISTRO', formatoceldacab)
                    ws.write(1, 7, 'FORMA DE PAGO', formatoceldacab)
                    ws.write(1, 8, 'ESTADO', formatoceldacab)
                    ws.write(1, 9, 'VALOR DE MAESTRÍA', formatoceldacab)
                    ws.write(1, 10, 'TOTAL GENERADO', formatoceldacab)
                    ws.write(1, 11, 'CANTIDAD DE RUBROS', formatoceldacab)
                    ws.write(1, 12, 'TOTAL PAGADO', formatoceldacab)
                    ws.write(1, 13, 'TOTAL PENDIENTE', formatoceldacab)
                    ws.write(1, 14, 'AMORTIZACIÓN', formatoceldacab)
                    ws.write(1, 15, 'ASESOR', formatoceldacab)
                    ws.write(1, 16, 'SUBIÓ CONTRATO', formatoceldacab)
                    ws.write(1, 17, 'SUBIÓ PAGARÉ', formatoceldacab)
                    ws.write(1, 18, 'CUADRADO UNEMI', formatoceldacab)
                    ws.write(1, 19, 'CUADRADO EPUNEMI', formatoceldacab)

                    estado = maestria = cohorte = formapago = 0
                    desde = hasta = ''
                    ids_insc = []
                    # if 'maestria' in request.GET:
                    #     maestria = int(request.GET['maestria'])
                    # if 'cohorte' in request.GET:
                    #     cohorte = int(request.GET['cohorte'])
                    if 'cohorte' in request.GET:
                        cohorte = request.GET['cohorte']
                    if 'estado' in request.GET:
                        estado = int(request.GET['estado'])
                    if 'formapago' in request.GET:
                        formapago = int(request.GET['formapago'])
                    if 'desde' in request.GET:
                        desde = request.GET['desde']
                    if 'hasta' in request.GET:
                        hasta = request.GET['hasta']

                    filtro = Q(status=True, cohortes__maestriaadmision__carrera__coordinacion__id=7, estado_aprobador=2)

                    # if maestria > 0:
                    #     filtro = filtro & Q(cohortes__maestriaadmision__id=maestria)
                    #
                    # if cohorte > 0:
                    #     filtro = filtro & Q(cohortes__id=cohorte)

                    if cohorte != "":
                        if eval(request.GET['cohorte'])[0] != "0":
                            filtro = filtro & Q(cohortes__id__in=eval(request.GET['cohorte']))
                        else:
                            cohortes_incluidas = []
                            cohortes_ofertadas = CohorteMaestria.objects.filter(status=True).order_by('-fecha_creacion')
                            for chor in cohortes_ofertadas:
                                fecha_aumentada = chor.fechafininsp + relativedelta(months=6)
                                fecha_actual = datetime.now().date()
                                if fecha_aumentada > fecha_actual:
                                    cohortes_incluidas.append(chor.id)
                            filtro = filtro & Q(cohortes__id__in=cohortes_incluidas)

                    if formapago > 0:
                        filtro = filtro & Q(formapagopac__id=formapago)

                    rubros_cu = []
                    rubros_descu = []
                    sin_rubro = []
                    if estado > 0:
                        if estado == 1:
                            leads = InscripcionCohorte.objects.filter(filtro)
                            for lead in leads:
                                if lead.cohortes.valorprograma:
                                    valormaestria = lead.cohortes.valorprograma
                                    if lead.total_generado_rubro() == valormaestria:
                                        rubros_cu.append(lead.id)
                                elif lead.cohortes.valorprogramacertificado:
                                    valormaestria = lead.cohortes.valorprogramacertificado
                                    if lead.total_generado_rubro() == valormaestria:
                                        rubros_cu.append(lead.id)

                            leads = InscripcionCohorte.objects.filter(filtro & Q(id__in=rubros_cu)).order_by('cohortes__maestriaadmision__carrera', 'inscripcionaspirante__persona__apellido1', 'inscripcionaspirante__persona__apellido2', 'inscripcionaspirante__persona__nombres')
                        elif estado == 2:
                            leads = InscripcionCohorte.objects.filter(filtro)
                            for lead in leads:
                                if lead.genero_rubro_matricula() or lead.genero_rubro_programa2():
                                    if lead.cohortes.valorprograma:
                                        valormaestria = lead.cohortes.valorprograma
                                        if lead.total_generado_rubro() != valormaestria:
                                            rubros_descu.append(lead.id)
                                    elif lead.cohortes.valorprogramacertificado:
                                        valormaestria = lead.cohortes.valorprogramacertificado
                                        if lead.total_generado_rubro() != valormaestria:
                                            rubros_descu.append(lead.id)

                            leads = InscripcionCohorte.objects.filter(filtro & Q(id__in=rubros_descu)).order_by('cohortes__maestriaadmision__carrera', 'inscripcionaspirante__persona__apellido1', 'inscripcionaspirante__persona__apellido2', 'inscripcionaspirante__persona__nombres')
                        elif estado == 3:
                            leads = InscripcionCohorte.objects.filter(filtro)
                            for lead in leads:
                                if not lead.genero_rubro_matricula() and not lead.genero_rubro_programa2():
                                    sin_rubro.append(lead.id)

                            leads = InscripcionCohorte.objects.filter(filtro & Q(id__in=sin_rubro)).order_by('cohortes__maestriaadmision__carrera', 'inscripcionaspirante__persona__apellido1', 'inscripcionaspirante__persona__apellido2', 'inscripcionaspirante__persona__nombres')
                    else:
                        leads = InscripcionCohorte.objects.filter(filtro).order_by(
                            'cohortes__maestriaadmision__carrera',
                            'inscripcionaspirante__persona__apellido1',
                            'inscripcionaspirante__persona__apellido2',
                            'inscripcionaspirante__persona__nombres')

                    if desde and hasta:
                        desde = datetime.strptime(desde, '%Y-%m-%d').date()
                        hasta = datetime.strptime(hasta, '%Y-%m-%d').date()
                        for lead in leads:
                            if lead.fecha_creacion.date() >= desde and lead.fecha_creacion.date() <= hasta:
                                ids_insc.append(int(lead.id))
                    elif desde:
                        desde = datetime.strptime(desde, '%Y-%m-%d').date()
                        for lead in leads:
                            if lead.fecha_creacion.date() >= desde:
                                ids_insc.append(int(lead.id))
                    elif hasta:
                        hasta = datetime.strptime(hasta, '%Y-%m-%d').date()
                        for lead in leads:
                            if lead.fecha_creacion.date() <= hasta:
                                ids_insc.append(int(lead.id))

                    if ids_insc:
                        leads = leads.filter(id__in=ids_insc)

                    filas_recorridas = 3
                    cont = 1

                    for lead in leads:
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(lead.id), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.cedula), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(lead.cohortes.descripcion), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(lead.cohortes.maestriaadmision.descripcion), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(lead.fecha_creacion.date()), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(lead.formapagopac.descripcion), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str('CUADRADO' if lead.tiene_rubro_cuadrado() else 'DESCUADRADO'), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, lead.cohortes.valorprogramacertificado if lead.cohortes.valorprogramacertificado else 'NO REGISTRA', decimalformat)
                        ws.write('K%s' % filas_recorridas, lead.total_generado_rubro(), decimalformat)
                        ws.write('L%s' % filas_recorridas, str(lead.cantidad_rubros_ins()), formatoceldaleft)
                        ws.write('M%s' % filas_recorridas, lead.total_pagado_rubro_cohorte(), decimalformat)
                        ws.write('N%s' % filas_recorridas, lead.total_pendiente(), decimalformat)
                        ws.write('O%s' % filas_recorridas, str(lead.amortizacion()), formatoceldaleft)
                        ws.write('P%s' % filas_recorridas, str(lead.asesor.persona if lead.asesor else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('Q%s' % filas_recorridas, str('SI' if lead.tiene_contrato_subido() == 2  else 'NO'), formatoceldaleft)
                        ws.write('R%s' % filas_recorridas, str('SI' if lead.tiene_pagare_subido() == 2  else 'NO'), formatoceldaleft)
                        ws.write('S%s' % filas_recorridas, str('SI' if lead.tiene_rubro_cuadrado() == True else 'NO'), formatoceldaleft)
                        ws.write('T%s' % filas_recorridas, str('SI' if lead.cuadre_con_epunemi() == True else 'NO'), formatoceldaleft)

                        filas_recorridas += 1
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'Reporte_Rubros.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporteventasbasica':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('ventas')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 15)
                    ws.set_column(2, 2, 35)
                    ws.set_column(3, 3, 15)
                    ws.set_column(4, 4, 45)
                    ws.set_column(5, 5, 45)
                    ws.set_column(6, 6, 45)
                    ws.set_column(7, 7, 45)
                    ws.set_column(8, 8, 45)
                    ws.set_column(9, 9, 15)
                    ws.set_column(10, 10, 15)
                    ws.set_column(11, 11, 15)
                    ws.set_column(12, 12, 15)
                    ws.set_column(13, 13, 15)
                    ws.set_column(14, 14, 15)
                    ws.set_column(15, 15, 15)
                    ws.set_column(16, 16, 15)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    ws.merge_range('A1:K1', "REPORTE DE GESTIÓN EDUCATIVA", formatotitulo_filtros)
                    ws.write(1, 0, 'N°', formatoceldacab)
                    ws.write(1, 1, 'ID', formatoceldacab)
                    ws.write(1, 2, 'NOMBRES', formatoceldacab)
                    ws.write(1, 3, 'CEDULA', formatoceldacab)
                    ws.write(1, 4, 'MAESTRIA', formatoceldacab)
                    ws.write(1, 5, 'COHORTE', formatoceldacab)
                    ws.write(1, 6, 'ASESOR', formatoceldacab)
                    ws.write(1, 7, 'TOTAL DE EVIDENCIAS', formatoceldacab)
                    ws.write(1, 8, 'TOTAL DE EVIDENCIAS SUBIDAS', formatoceldacab)
                    ws.write(1, 9, 'EVIDENCIAS RECHAZADAS', formatoceldacab)
                    ws.write(1, 10, 'EVIDENCIAS APROBADAS', formatoceldacab)
                    ws.write(1, 11, 'FECHA', formatoceldacab)
                    ws.write(1, 12, 'TODO SUBIDO', formatoceldacab)
                    ws.write(1, 13, 'TIENE RECHAZO', formatoceldacab)
                    ws.write(1, 14, 'PRE APROBADO', formatoceldacab)
                    ws.write(1, 15, 'ESTADO', formatoceldacab)
                    ws.write(1, 16, 'ACTIVO', formatoceldacab)

                    inscritos = InscripcionCohorte.objects.filter(status=True, formapagopac__id=2, estadoformapago=1).order_by('-id')

                    filas_recorridas = 3
                    cont = 1
                    for ins in inscritos:
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(ins.id), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(ins.inscripcionaspirante.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(ins.inscripcionaspirante.persona.identificacion()), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(ins.cohortes.maestriaadmision.descripcion), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(ins.cohortes.descripcion), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(ins.asesor.persona if ins.asesor else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, ins.total_requisitos_financiamiento(), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, ins.total_evidencias_financiamiento(), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, ins.total_evidenciasrechazadas_fi(), formatoceldaleft)
                        ws.write('K%s' % filas_recorridas, ins.total_evidenciasaprobadas_fi(), formatoceldaleft)
                        ws.write('L%s' % filas_recorridas, str(ins.fecha_creacion.date()), formatoceldaleft)
                        ws.write('M%s' % filas_recorridas, str('SI' if ins.todosubidofi else 'NO'), formatoceldaleft)
                        ws.write('N%s' % filas_recorridas, str('SI' if ins.tienerechazofi else 'NO'), formatoceldaleft)
                        ws.write('O%s' % filas_recorridas, str('SI' if ins.preaprobado else 'NO'), formatoceldaleft)
                        ws.write('P%s' % filas_recorridas, str(ins.get_estado_aprobador_display()), formatoceldaleft)
                        ws.write('Q%s' % filas_recorridas, str('SI' if ins.status else 'NO'), formatoceldaleft)

                        filas_recorridas += 1
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'Reporte_preaprobados_descuadre.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporteleadsenproceso':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('proceso')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 15)
                    ws.set_column(2, 2, 35)
                    ws.set_column(3, 3, 15)
                    ws.set_column(4, 4, 45)
                    ws.set_column(5, 5, 45)
                    ws.set_column(6, 6, 45)
                    ws.set_column(7, 7, 45)
                    ws.set_column(8, 8, 45)
                    ws.set_column(9, 9, 15)
                    ws.set_column(10, 10, 15)
                    ws.set_column(11, 11, 15)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    ws.merge_range('A1:K1', "REPORTE DE LEADS CON EVIDENCIAS APROBADAS - EN PROCESO", formatotitulo_filtros)
                    ws.write(1, 0, 'N°', formatoceldacab)
                    ws.write(1, 1, 'ID', formatoceldacab)
                    ws.write(1, 2, 'NOMBRES', formatoceldacab)
                    ws.write(1, 3, 'CEDULA', formatoceldacab)
                    ws.write(1, 4, 'MAESTRIA', formatoceldacab)
                    ws.write(1, 5, 'COHORTE', formatoceldacab)
                    ws.write(1, 6, 'ESTADO APROBADOR', formatoceldacab)

                    listado_leads = []

                    admitidos = InscripcionCohorte.objects.filter(status=True, cohortes__id__in=[120, 123, 122, 113, 121, 86, 124, 107, 125, 126, 127, 128], estado_aprobador=1)
                    # admitidos = [22284, 22678]

                    claserequisitoadmision = ClaseRequisito.objects.values_list('requisito__id').filter(clasificacion=1, status=True)

                    for admiti in admitidos:
                        admitido = InscripcionCohorte.objects.get(id=admiti.id)
                        requisitosadmision = admitido.cohortes.requisitosmaestria_set.filter(requisito__in=claserequisitoadmision, obligatorio=True, status=True).count()

                        if admitido.total_evidencias_obligatorio() == requisitosadmision and admitido.estado_aprobador == 1:
                            listado_leads.append(admitido.id)

                    leads = InscripcionCohorte.objects.filter(status=True, id__in=listado_leads)

                    filas_recorridas = 3
                    cont = 1
                    for lead in leads:
                        # dias = pago - registro
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(lead.id), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.identificacion()), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(lead.cohortes.maestriaadmision), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(lead.cohortes), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(lead.estado_aprobador), formatoceldaleft)

                        filas_recorridas += 1
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'Reporte_Leads_En_Proceso.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporteleadsasignadossupervisor':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('leads_registrados')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 15)
                    ws.set_column(2, 2, 15)
                    ws.set_column(3, 3, 45)
                    ws.set_column(4, 4, 35)
                    ws.set_column(5, 5, 45)
                    ws.set_column(6, 6, 15)
                    ws.set_column(7, 7, 20)
                    ws.set_column(8, 8, 40)
                    ws.set_column(9, 9, 45)
                    ws.set_column(10, 10, 20)
                    ws.set_column(11, 11, 20)
                    ws.set_column(12, 12, 20)
                    ws.set_column(13, 13, 20)
                    ws.set_column(14, 14, 20)
                    ws.set_column(15, 15, 20)
                    ws.set_column(16, 16, 15)
                    ws.set_column(17, 17, 20)
                    ws.set_column(18, 18, 20)
                    ws.set_column(19, 19, 20)
                    ws.set_column(20, 20, 15)
                    ws.set_column(21, 21, 15)
                    ws.set_column(22, 22, 15)
                    ws.set_column(23, 23, 35)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    ws.merge_range('A1:Q1', 'REPORTE DE LEADS REGISTRADOS', formatotitulo_filtros)
                    ws.write(1, 0, 'N°', formatoceldacab)
                    ws.write(1, 1, 'ID', formatoceldacab)
                    ws.write(1, 2, 'CEDULA', formatoceldacab)
                    ws.write(1, 3, 'PROSPECTO', formatoceldacab)
                    ws.write(1, 4, 'COHORTE', formatoceldacab)
                    ws.write(1, 5, 'MAESTRIA', formatoceldacab)
                    ws.write(1, 6, 'FECHA DE REGISTRO', formatoceldacab)
                    ws.write(1, 7, 'TELEFONO', formatoceldacab)
                    ws.write(1, 8, 'CORREO', formatoceldacab)
                    ws.write(1, 9, 'ASESOR', formatoceldacab)
                    ws.write(1, 10, 'FECHA DE ASIGNACIÓN', formatoceldacab)
                    ws.write(1, 11, 'ESTADO DE ATENCIÓN', formatoceldacab)
                    ws.write(1, 12, 'FORMA DE PAGO', formatoceldacab)
                    ws.write(1, 13, 'MATRICULADO', formatoceldacab)
                    ws.write(1, 14, 'CURSO', formatoceldacab)
                    ws.write(1, 15, 'CANAL', formatoceldacab)
                    ws.write(1, 16, 'RESERVA', formatoceldacab)
                    ws.write(1, 17, 'CIUDAD', formatoceldacab)
                    ws.write(1, 18, 'PROVINCIA', formatoceldacab)
                    ws.write(1, 19, 'ZONA', formatoceldacab)
                    ws.write(1, 20, '¿ACTIVO?', formatoceldacab)
                    ws.write(1, 21, '¿MIGRADO?', formatoceldacab)
                    ws.write(1, 22, 'FECHA DE MIGRACIÓN', formatoceldacab)
                    ws.write(1, 23, 'OBSERVACIÓN DE MIGRACIÓN', formatoceldacab)

                    estado = asesor = maestria = cohorte = estado_mat =  0
                    desde = hasta = ''

                    if 'cohorte' in request.GET:
                        cohorte = request.GET['cohorte']
                    if 'asesor' in request.GET:
                        asesor = request.GET['asesor']
                    if 'estado' in request.GET:
                        estado = request.GET['estado']

                    if 'desde' in request.GET:
                        desde = request.GET['desde']
                    if 'hasta' in request.GET:
                        hasta = request.GET['hasta']

                    filtro = Q(cohortes__maestriaadmision__carrera__coordinacion__id=7)

                    if cohorte != "":
                        if eval(request.GET['cohorte'])[0] != "0":
                            filtro = filtro & Q(cohortes__id__in=eval(request.GET['cohorte']))

                    if estado != "":
                        estado = int(estado)
                        if estado == 1:
                            filtro = filtro & Q(estado_asesor=2)
                        elif estado == 2:
                            filtro = filtro & Q(estado_asesor=1)
                        elif estado == 3:
                            filtro = filtro & Q(estado_aprobador=1)
                        elif estado == 4:
                            filtro = filtro & Q(estado_aprobador=2)
                        elif estado == 5:
                            filtro = filtro & Q(estado_aprobador=3)
                        elif estado == 6:
                            filtro = filtro & Q(formapagopac__id=1)
                        elif estado == 7:
                            filtro = filtro & Q(formapagopac__id=2)
                        elif estado == 8:
                            filtro = filtro & Q(contrato__contratolegalizado=True)
                        elif estado == 9:
                            idquery = Matricula.objects.filter(status=True, retiradomatricula=False).values_list('inscripcion__id', flat=True).order_by('inscripcion__id').distinct()
                            filtro = filtro & Q(inscripcion__id__in=idquery)
                        elif estado == 10:
                            filtro = filtro & Q(leaddezona=True)
                        elif estado == 11:
                            filtro = filtro & Q(es_becado=True)
                        elif estado == 12:
                            filtro = filtro & Q(tienerechazo=True)
                        elif estado == 13:
                            idquery = CambioAdmitidoCohorteInscripcion.objects.filter(status=True).values_list('inscripcionCohorte__id', flat=True).order_by('inscripcionCohorte__id').distinct()
                            filtro = filtro & Q(id__in=idquery)

                    if asesor != "":
                        if eval(request.GET['asesor'])[0] != "0":
                            filtro = filtro & Q(asesor__id__in=eval(request.GET['asesor']))

                    if desde and hasta:
                        filtro = filtro & Q(fecha_creacion__date__range=(desde, hasta))

                    elif desde:
                        filtro = filtro & Q(fecha_creacion__date__gte=desde)

                    elif hasta:
                        filtro = filtro & Q(fecha_creacion__date__lte=hasta)

                    leads = InscripcionCohorte.objects.filter(filtro).order_by(
                        'cohortes__maestriaadmision__carrera',
                        'inscripcionaspirante__persona__apellido1',
                        'inscripcionaspirante__persona__apellido2',
                        'inscripcionaspirante__persona__nombres')

                    filas_recorridas = 3
                    cont = 1

                    for lead in leads:
                        curso = ''
                        if lead.tiene_matricula_cohorte():
                            cur = lead.curso_matriculado()
                            if len(cur) > 0:
                                curso = cur[0]
                            else:
                                curso = 'NO REGISTRA'
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(lead.id), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.cedula), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(lead.cohortes.descripcion), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(lead.cohortes.maestriaadmision.descripcion), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(lead.fecha_creacion.date()), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.telefono), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.email), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str(lead.asesor.persona.nombre_completo_inverso() if lead.asesor else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('K%s' % filas_recorridas, str(lead.fecha_asignacion_asesor().date() if lead.asesor else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('L%s' % filas_recorridas, str(lead.tiporespuesta.descripcion if lead.tiporespuesta else 'PENDIENTE'), formatoceldaleft)
                        ws.write('M%s' % filas_recorridas, str(lead.formapagopac.descripcion if lead.formapagopac else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('N%s' % filas_recorridas, str('SI' if lead.tiene_matricula_cohorte() else 'NO'), formatoceldaleft)
                        ws.write('O%s' % filas_recorridas, str(curso), formatoceldaleft)
                        ws.write('P%s' % filas_recorridas, str(lead.canal.descripcion if lead.canal else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('Q%s' % filas_recorridas, str('SI' if lead.leaddezona else 'NO'), formatoceldaleft)
                        ws.write('R%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.canton if lead.inscripcionaspirante.persona.canton else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('S%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.provincia if lead.inscripcionaspirante.persona.provincia else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('T%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.canton.zona if lead.inscripcionaspirante.persona.canton and lead.inscripcionaspirante.persona.canton.zona else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('U%s' % filas_recorridas, str('SI' if lead.status else 'NO'), formatoceldaleft)
                        ws.write('V%s' % filas_recorridas, str('SI' if lead.cambioadmitido() else 'NO'), formatoceldaleft)
                        ws.write('W%s' % filas_recorridas, str(lead.cambioadmitido().fecha_creacion.date() if lead.cambioadmitido() else 'NO'), formatoceldaleft)
                        ws.write('X%s' % filas_recorridas, str(lead.cambioadmitido().observacion if lead.cambioadmitido() and lead.cambioadmitido().observacion else 'NINGUNA'), formatoceldaleft)

                        filas_recorridas += 1
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'Reporte_Leads_Registrados.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporteprospectossinatender':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('leads_sin_atender')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 15)
                    ws.set_column(2, 2, 15)
                    ws.set_column(3, 3, 45)
                    ws.set_column(4, 4, 35)
                    ws.set_column(5, 5, 45)
                    ws.set_column(6, 6, 15)
                    ws.set_column(7, 7, 20)
                    ws.set_column(8, 8, 40)
                    ws.set_column(9, 9, 30)
                    ws.set_column(10, 10, 30)
                    ws.set_column(11, 11, 30)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    ws.merge_range('A1:O1', 'REPORTE DE LEDS SIN ATENDER', formatotitulo_filtros)
                    # ws.merge_range('A2:K2', 'VENTAS' + asesorme.cohorte.maestriaadmision.descripcion.replace("MAESTRÍA", ""), formatoceldacab)
                    ws.write(1, 0, 'N°', formatoceldacab)
                    ws.write(1, 1, 'ID', formatoceldacab)
                    ws.write(1, 2, 'CEDULA', formatoceldacab)
                    ws.write(1, 3, 'PROSPECTO', formatoceldacab)
                    ws.write(1, 4, 'COHORTE', formatoceldacab)
                    ws.write(1, 5, 'MAESTRIA', formatoceldacab)
                    ws.write(1, 6, 'ASESOR', formatoceldacab)
                    ws.write(1, 7, 'FECHA DE INSCRIPCION', formatoceldacab)
                    ws.write(1, 8, 'FECHA DE ASIGNACIÓN', formatoceldacab)
                    ws.write(1, 9, 'DIAS SIN ATENDER DESDE LA INSCRIPCIÓN', formatoceldacab)
                    ws.write(1, 10, 'DIAS SIN ATENDER DESDE LA ASIGNACIÓN', formatoceldacab)
                    ws.write(1, 11, 'ESTADO DE ATENCIÓN', formatoceldacab)
                    ws.write(1, 12, 'LEAD DE ZONA', formatoceldacab)

                    asesor = maestria = cohorte =  0
                    desde = hasta = ''
                    fecha_actual = datetime.now().date()

                    if 'cohorte' in request.GET:
                        cohorte = request.GET['cohorte']
                    if 'asesor' in request.GET:
                        asesor = request.GET['asesor']

                    if 'desde' in request.GET:
                        desde = request.GET['desde']
                    if 'hasta' in request.GET:
                        hasta = request.GET['hasta']

                    filtro = Q(status=True, cohortes__maestriaadmision__carrera__coordinacion__id=7)

                    if cohorte != "":
                        if eval(request.GET['cohorte'])[0] != "0":
                            filtro = filtro & Q(inscripcioncohorte__cohortes__id__in=eval(request.GET['cohorte']))

                    if asesor != "":
                        if eval(request.GET['asesor'])[0] != "0":
                            filtro = filtro & Q(asesor__id__in=eval(request.GET['asesor']))

                    if desde and hasta:
                        filtro = filtro & Q(fecha_creacion__date__range=(desde, hasta))

                    elif desde:
                        filtro = filtro & Q(fecha_creacion__date__gte=desde)

                    elif hasta:
                        filtro = filtro & Q(fecha_creacion__date__lte=hasta)

                    lista_sin = []
                    leads = InscripcionCohorte.objects.filter(filtro).order_by(
                        'cohortes__maestriaadmision__carrera',
                        'inscripcionaspirante__persona__apellido1',
                        'inscripcionaspirante__persona__apellido2',
                        'inscripcionaspirante__persona__nombres')

                    for l in leads:
                        if l.asesor:
                            if l.tiporespuesta == 1 or l.tiporespuesta is None:
                                dias = fecha_actual - l.fecha_asignacion_asesor().date()
                                if dias.days > 2:
                                    lista_sin.append(l.id)

                    leads = InscripcionCohorte.objects.filter(id__in=lista_sin).order_by(
                        'cohortes__maestriaadmision__carrera',
                        'inscripcionaspirante__persona__apellido1',
                        'inscripcionaspirante__persona__apellido2',
                        'inscripcionaspirante__persona__nombres')

                    filas_recorridas = 3
                    cont = 1

                    for lead in leads:
                        dias_a = fecha_actual - lead.fecha_asignacion_asesor().date()
                        dias_a = dias_a.days
                        dias_ins = fecha_actual - lead.fecha_creacion.date()
                        dias_ins = dias_ins.days
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(lead.id), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.cedula), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(lead.cohortes.descripcion), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(lead.cohortes.maestriaadmision.descripcion), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(lead.asesor.persona.nombre_completo_inverso() if lead.asesor else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(lead.fecha_creacion.date()), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str(lead.fecha_asignacion_asesor().date() if lead.asesor else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str(dias_a) + ' ' + 'dias', formatoceldaleft)
                        ws.write('K%s' % filas_recorridas, str(dias_ins) + ' ' + 'dias', formatoceldaleft)
                        ws.write('L%s' % filas_recorridas, str(lead.tiporespuesta.descripcion if lead.tiporespuesta else 'PENDIENTE'), formatoceldaleft)
                        ws.write('M%s' % filas_recorridas, str('SI' if lead.leaddezona else 'NO'), formatoceldaleft)

                        filas_recorridas += 1
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'Reporte_leads_sin_atender.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'listadoadmitidossindatos':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('leads_sin_datos')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 15)
                    ws.set_column(2, 2, 35)
                    ws.set_column(3, 3, 35)
                    ws.set_column(4, 4, 35)
                    ws.set_column(5, 5, 15)
                    ws.set_column(6, 6, 15)
                    ws.set_column(7, 7, 40)
                    ws.set_column(8, 8, 40)
                    ws.set_column(9, 9, 40)
                    ws.set_column(10, 10, 50)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    ws.merge_range('A1:O1', 'REPORTE DE LEDS SIN DATOS PERSONALES ACTUALIZADOS', formatotitulo_filtros)
                    # ws.merge_range('A2:K2', 'VENTAS' + asesorme.cohorte.maestriaadmision.descripcion.replace("MAESTRÍA", ""), formatoceldacab)
                    ws.write(1, 0, 'N°', formatoceldacab)
                    ws.write(1, 1, 'CÉDULA', formatoceldacab)
                    ws.write(1, 2, 'NOMBRES', formatoceldacab)
                    ws.write(1, 3, 'EMAIL', formatoceldacab)
                    ws.write(1, 4, 'EMAIL INSTITUCIONAL', formatoceldacab)
                    ws.write(1, 5, 'TELÉFONO', formatoceldacab)
                    ws.write(1, 6, 'ESTADO', formatoceldacab)
                    ws.write(1, 7, 'MAESTRÍA', formatoceldacab)
                    ws.write(1, 8, 'COHORTE', formatoceldacab)
                    ws.write(1, 9, 'ASESOR COMERCIAL', formatoceldacab)
                    ws.write(1, 10, 'DATOS POR LLENAR', formatoceldacab)

                    asesor = maestria = cohorte =  0
                    desde = hasta = ''
                    fecha_actual = datetime.now().date()

                    if 'cohorte' in request.GET:
                        cohorte = request.GET['cohorte']
                    if 'asesor' in request.GET:
                        asesor = request.GET['asesor']

                    if 'desde' in request.GET:
                        desde = request.GET['desde']
                    if 'hasta' in request.GET:
                        hasta = request.GET['hasta']

                    filtro = Q(status=True, cohortes__maestriaadmision__carrera__coordinacion__id=7, vendido=True)

                    if cohorte != "":
                        if eval(request.GET['cohorte'])[0] != "0":
                            filtro = filtro & Q(cohortes__id__in=eval(request.GET['cohorte']))

                    if asesor != "":
                        if eval(request.GET['asesor'])[0] != "0":
                            filtro = filtro & Q(asesor__id__in=eval(request.GET['asesor']))

                    admitidosge = InscripcionCohorte.objects.filter(filtro).order_by(
                        'cohortes__maestriaadmision__carrera',
                        'inscripcionaspirante__persona__apellido1',
                        'inscripcionaspirante__persona__apellido2',
                        'inscripcionaspirante__persona__nombres')

                    listaad = []
                    for admi in admitidosge:
                        if admi.total_pagado_rubro_cohorte() and admi.completo_datos_matrices() == '1':
                            listaad.append(admi.id)
                    admitidosreales = InscripcionCohorte.objects.filter(status=True, id__in=listaad).order_by('inscripcionaspirante__persona__apellido1','inscripcionaspirante__persona__apellido2', 'inscripcionaspirante__persona__nombres')

                    filas_recorridas = 3
                    cont = 1

                    for admitido in admitidosreales:
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.cedula), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.email if admitido.inscripcionaspirante.persona.email else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.emailinst if admitido.inscripcionaspirante.persona.emailinst else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.telefono if admitido.inscripcionaspirante.persona.telefono else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str('NO MATRICULADO' if admitido.esta_inscrito() == False else 'MATRICULADO'), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(nombre_carrera_pos(admitido.cohortes.maestriaadmision.carrera)), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str(admitido.cohortes.descripcion), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str(admitido.asesor.persona), formatoceldaleft)
                        ws.write('K%s' % filas_recorridas, str(admitido.datos_restantes()), formatoceldaleft)

                        filas_recorridas += 1
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'Listado_admitidos_sin_datos.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'listadoadmitidossindatosasesor':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('leads_sin_datos')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 15)
                    ws.set_column(2, 2, 35)
                    ws.set_column(3, 3, 35)
                    ws.set_column(4, 4, 35)
                    ws.set_column(5, 5, 15)
                    ws.set_column(6, 6, 15)
                    ws.set_column(7, 7, 40)
                    ws.set_column(8, 8, 40)
                    ws.set_column(9, 9, 40)
                    ws.set_column(10, 10, 50)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    ws.merge_range('A1:O1', 'REPORTE DE LEDS SIN DATOS PERSONALES ACTUALIZADOS', formatotitulo_filtros)
                    # ws.merge_range('A2:K2', 'VENTAS' + asesorme.cohorte.maestriaadmision.descripcion.replace("MAESTRÍA", ""), formatoceldacab)
                    ws.write(1, 0, 'N°', formatoceldacab)
                    ws.write(1, 1, 'CÉDULA', formatoceldacab)
                    ws.write(1, 2, 'NOMBRES', formatoceldacab)
                    ws.write(1, 3, 'EMAIL', formatoceldacab)
                    ws.write(1, 4, 'EMAIL INSTITUCIONAL', formatoceldacab)
                    ws.write(1, 5, 'TELÉFONO', formatoceldacab)
                    ws.write(1, 6, 'ESTADO', formatoceldacab)
                    ws.write(1, 7, 'MAESTRÍA', formatoceldacab)
                    ws.write(1, 8, 'COHORTE', formatoceldacab)
                    ws.write(1, 9, 'ASESOR COMERCIAL', formatoceldacab)
                    ws.write(1, 10, 'DATOS POR LLENAR', formatoceldacab)

                    asesor = maestria = cohorte =  0
                    desde = hasta = ''
                    fecha_actual = datetime.now().date()

                    if 'cohorte' in request.GET:
                        cohorte = request.GET['cohorte']

                    filtro = Q(status=True, cohortes__maestriaadmision__carrera__coordinacion__id=7, vendido=True, asesor__persona=persona)

                    if cohorte != "":
                        if eval(request.GET['cohorte'])[0] != "0":
                            filtro = filtro & Q(cohortes__id__in=eval(request.GET['cohorte']))

                    admitidosge = InscripcionCohorte.objects.filter(filtro).order_by(
                        'cohortes__maestriaadmision__carrera',
                        'inscripcionaspirante__persona__apellido1',
                        'inscripcionaspirante__persona__apellido2',
                        'inscripcionaspirante__persona__nombres')

                    listaad = []
                    for admi in admitidosge:
                        if admi.total_pagado_rubro_cohorte() and admi.completo_datos_matrices() == '1':
                            listaad.append(admi.id)
                    admitidosreales = InscripcionCohorte.objects.filter(status=True, id__in=listaad).order_by('inscripcionaspirante__persona__apellido1','inscripcionaspirante__persona__apellido2', 'inscripcionaspirante__persona__nombres')

                    filas_recorridas = 3
                    cont = 1

                    for admitido in admitidosreales:
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.cedula), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.email if admitido.inscripcionaspirante.persona.email else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.emailinst if admitido.inscripcionaspirante.persona.emailinst else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(admitido.inscripcionaspirante.persona.telefono if admitido.inscripcionaspirante.persona.telefono else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str('NO MATRICULADO' if admitido.esta_inscrito() == False else 'MATRICULADO'), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(nombre_carrera_pos(admitido.cohortes.maestriaadmision.carrera)), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str(admitido.cohortes.descripcion), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str(admitido.asesor.persona), formatoceldaleft)
                        ws.write('K%s' % filas_recorridas, str(admitido.datos_restantes()), formatoceldaleft)

                        filas_recorridas += 1
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'Listado_admitidos_sin_datos.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporteprospectosfinanciamiento':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('financiamiento')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 15)
                    ws.set_column(2, 2, 15)
                    ws.set_column(3, 3, 15)
                    ws.set_column(4, 4, 45)
                    ws.set_column(5, 5, 15)
                    ws.set_column(6, 6, 40)
                    ws.set_column(7, 7, 50)
                    ws.set_column(8, 8, 15)
                    ws.set_column(9, 9, 15)
                    ws.set_column(10, 10, 15)
                    ws.set_column(11, 11, 15)
                    ws.set_column(12, 12, 40)
                    ws.set_column(13, 13, 25)
                    ws.set_column(14, 14, 25)
                    ws.set_column(15, 15, 45)
                    ws.set_column(16, 16, 15)
                    ws.set_column(17, 17, 40)
                    ws.set_column(18, 18, 40)
                    ws.set_column(19, 19, 40)
                    ws.set_column(20, 20, 40)
                    ws.set_column(21, 21, 45)
                    ws.set_column(22, 22, 25)
                    ws.set_column(23, 23, 25)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    ws.merge_range('A1:V1', 'REPORTE DE PROSPECTOS DE FINANCIAMIENTO', formatotitulo_filtros)
                    # ws.merge_range('A2:K2', 'VENTAS' + asesorme.cohorte.maestriaadmision.descripcion.replace("MAESTRÍA", ""), formatoceldacab)
                    ws.write(1, 0, 'N°', formatoceldacab)
                    ws.write(1, 1, 'ID', formatoceldacab)
                    ws.write(1, 2, 'FECHA', formatoceldacab)
                    ws.write(1, 3, 'CÉDULA', formatoceldacab)
                    ws.write(1, 4, 'NOMBRES', formatoceldacab)
                    ws.write(1, 5, 'TELÉFONO', formatoceldacab)
                    ws.write(1, 6, 'EMAIL', formatoceldacab)
                    ws.write(1, 7, 'DIRECCIÓN', formatoceldacab)
                    ws.write(1, 8, 'VALOR DE MAESTRÍA', formatoceldacab)
                    ws.write(1, 9, 'TOTAL GENERADO', formatoceldacab)
                    ws.write(1, 10, 'TOTAL PAGADO', formatoceldacab)
                    ws.write(1, 11, 'VALOR PENDIENTE', formatoceldacab)
                    ws.write(1, 12, 'AMORTIZACIÓN', formatoceldacab)
                    ws.write(1, 13, 'SALDO EN LETRAS', formatoceldacab)
                    ws.write(1, 14, 'DOCUMENTOS', formatoceldacab)
                    ws.write(1, 15, 'NOMBRES DEL GARANTE', formatoceldacab)
                    ws.write(1, 16, 'CÉDULA DEL GARANTE', formatoceldacab)
                    ws.write(1, 17, 'MAESTRÍA', formatoceldacab)
                    ws.write(1, 18, 'COHORTE', formatoceldacab)
                    ws.write(1, 19, 'ASESOR', formatoceldacab)
                    ws.write(1, 20, 'OBSERVACIONES', formatoceldacab)
                    ws.write(1, 21, 'TIPO DE FINANCIAMIENTO', formatoceldacab)
                    ws.write(1, 22, 'CUADRADO UNEMI', formatoceldacab)
                    ws.write(1, 23, 'CUADRADO EPUNEMI', formatoceldacab)

                    asesor = maestria = cohorte = 0
                    desde = hasta = ''
                    ids_insc = []

                    if 'cohorte' in request.GET:
                        cohorte = request.GET['cohorte']
                    if 'asesor' in request.GET:
                        asesor = request.GET['asesor']
                    if 'desde' in request.GET:
                        desde = request.GET['desde']
                    if 'hasta' in request.GET:
                        hasta = request.GET['hasta']

                    filtro = Q(status=True, cohortes__maestriaadmision__carrera__coordinacion__id=7, formapagopac__id=2,
                               fecha_creacion__in=InscripcionCohorte.objects.values('inscripcionaspirante__id').annotate(fecha_creacion=Max('fecha_creacion')).values_list('fecha_creacion', flat=True).filter(status=True))

                    if cohorte != "":
                        if eval(request.GET['cohorte'])[0] != "0":
                            filtro = filtro & Q(cohortes__id__in=eval(request.GET['cohorte']))
                        else:
                            cohortes_incluidas = []
                            cohortes_ofertadas = CohorteMaestria.objects.filter(status=True).order_by('-fecha_creacion')
                            for chor in cohortes_ofertadas:
                                fecha_aumentada = chor.fechafininsp + relativedelta(months=6)
                                fecha_actual = datetime.now().date()
                                if fecha_aumentada > fecha_actual:
                                    cohortes_incluidas.append(chor.id)
                            filtro = filtro & Q(cohortes__id__in=cohortes_incluidas)

                    if asesor != "":
                        if eval(request.GET['asesor'])[0] != "0":
                            filtro = filtro & Q(asesor__id__in=eval(request.GET['asesor']))

                    if desde and hasta:
                        desde = datetime.strptime(desde, '%Y-%m-%d').date()
                        hasta = datetime.strptime(hasta, '%Y-%m-%d').date()
                        leads = InscripcionCohorte.objects.filter(filtro).order_by('-fecha_creacion')
                        for lead in leads:
                            if lead.detalle_finan() and lead.detalle_finan().fecha_creacion.date() >= desde and lead.detalle_finan().fecha_creacion.date() <= hasta:
                               ids_insc.append(int(lead.id))
                    elif desde:
                        desde = datetime.strptime(desde, '%Y-%m-%d').date()
                        leads = InscripcionCohorte.objects.filter(filtro).order_by('-fecha_creacion')
                        for lead in leads:
                            if lead.detalle_finan() and lead.detalle_finan().fecha_creacion.date() >= desde:
                               ids_insc.append(lead.id)


                    elif hasta:
                        hasta = datetime.strptime(hasta, '%Y-%m-%d').date()
                        leads = InscripcionCohorte.objects.filter(filtro).order_by('-fecha_creacion')
                        for lead in leads:
                            if lead.detalle_finan() and lead.detalle_finan().fecha_creacion.date() <= hasta:
                               ids_insc.append(lead.id)
                                
                    if ids_insc:
                        leads = leads.filter(id__in=ids_insc)
                    else:
                        leads = InscripcionCohorte.objects.filter(filtro).order_by('-fecha_creacion')


                    filas_recorridas = 3
                    cont = 1

                    for lead in leads:
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(lead.id), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(lead.detalle_finan().fecha_creacion.date()), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.identificacion()), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.telefono if lead.inscripcionaspirante.persona.telefono else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.email), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(lead.inscripcionaspirante.persona.direccion if lead.inscripcionaspirante.persona.direccion else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, lead.cohortes.valorprogramacertificado if lead.cohortes.valorprogramacertificado else 'NO REGISTRA', decimalformat)
                        ws.write('J%s' % filas_recorridas, lead.total_generado_rubro(), decimalformat)
                        ws.write('K%s' % filas_recorridas, lead.total_pagado_rubro_cohorte(), decimalformat)
                        ws.write('L%s' % filas_recorridas, lead.total_pendiente(), decimalformat)
                        ws.write('M%s' % filas_recorridas, str(lead.amortizacion()), formatoceldaleft)
                        ws.write('N%s' % filas_recorridas, str(numero_a_letras(lead.total_pendiente()).upper()), formatoceldaleft)
                        ws.write('O%s' % filas_recorridas, str(lead.tiene_documentos()), formatoceldaleft)
                        ws.write('P%s' % filas_recorridas, str(lead.nombre_garante()), formatoceldaleft)
                        ws.write('Q%s' % filas_recorridas, str(lead.garante_prospecto().cedula if lead.garante_prospecto() else 'SIN GARANTE'), formatoceldaleft)
                        ws.write('R%s' % filas_recorridas, str(lead.cohortes.maestriaadmision.descripcion), formatoceldaleft)
                        ws.write('S%s' % filas_recorridas, str(lead.cohortes.descripcion), formatoceldaleft)
                        ws.write('T%s' % filas_recorridas, str(lead.asesor.persona.nombre_completo_inverso() if lead.asesor else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('U%s' % filas_recorridas, str(lead.detalle_finan().observacion), formatoceldaleft)
                        ws.write('V%s' % filas_recorridas, str(lead.Configfinanciamientocohorte if lead.Configfinanciamientocohorte else 'NO TIENE TIPO DE FINANCIAMIENTO ASIGNADO'), formatoceldaleft)
                        ws.write('W%s' % filas_recorridas, str('SI' if lead.tiene_rubro_cuadrado() == True else 'NO'), formatoceldaleft)
                        ws.write('X%s' % filas_recorridas, str('SI' if lead.cuadre_con_epunemi() == True else 'NO'), formatoceldaleft)

                        filas_recorridas += 1
                        cont += 1


                    workbook.close()
                    output.seek(0)
                    filename = 'Reporte_Leads_Financiamiento.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reportemetasmensuales':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('metas_mensuales')
                    ws.set_column(0, 0, 5)
                    ws.set_column(1, 1, 100)
                    ws.set_column(2, 2, 15)
                    ws.set_column(3, 3, 15)
                    ws.set_column(4, 4, 15)
                    ws.set_column(5, 5, 15)
                    ws.set_column(6, 6, 15)

                    formatotitulo_filtros = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white', 'valign': 'vcenter'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft4 = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#E3651D', 'font_color': 'black', 'valign': 'vcenter'})

                    formatoceldaleft_red = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#E74646', 'font_color': 'black', 'valign': 'vcenter'})

                    formatoceldaleft_red1 = workbook.add_format(
                        {'align': 'right', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#E74646', 'font_color': 'black', 'valign': 'vcenter'})

                    formatoceldaleft_yellow = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#F7D060', 'font_color': 'black', 'valign': 'vcenter'})

                    formatoceldaleft_yellow1 = workbook.add_format(
                        {'align': 'right', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#F7D060', 'font_color': 'black', 'valign': 'vcenter'})

                    formatoceldaleft_green = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#79AC78', 'font_color': 'black', 'valign': 'vcenter'})

                    formatoceldaleft_green1 = workbook.add_format(
                        {'align': 'right', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#79AC78', 'font_color': 'black', 'valign': 'vcenter'})

                    formatoceldaleft_blue = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#3081D0', 'font_color': 'black', 'valign': 'vcenter'})

                    formatoceldaleft_blue1 = workbook.add_format(
                        {'align': 'right', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#3081D0', 'font_color': 'black', 'valign': 'vcenter'})

                    decimalformat = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    decimalformat2 = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat3 = workbook.add_format({'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    anio = mes = asesor = 0
                    nombre_mes = ""

                    if 'asesor' in request.GET:
                        asesor = request.GET['asesor']
                    if 'anio' in request.GET:
                        anio = int(request.GET['anio'])
                    if 'mes' in request.GET:
                        mes = int(request.GET['mes'])

                    ida = DetalleAsesorMeta.objects.filter(status=True, inicio__month=mes, inicio__year=anio, asesormeta__maestria__isnull=False).values_list('asesormeta__asesor__id', flat=True)

                    if asesor != "":
                        if eval(request.GET['asesor'])[0] != "0":
                            asesores = AsesorComercial.objects.filter(status=True, id__in=eval(request.GET['asesor']))
                        else:
                            asesores = AsesorComercial.objects.filter(status=True, id__in=ida)
                    else:
                        asesores = AsesorComercial.objects.filter(status=True, id__in=ida)

                    if mes == 1:
                        nombre_mes = "ENERO"
                    elif mes == 2:
                        nombre_mes = "FEBRERO"
                    elif mes == 3:
                        nombre_mes = "MARZO"
                    elif mes == 4:
                        nombre_mes = "ABRIL"
                    elif mes == 5:
                        nombre_mes = "MAYO"
                    elif mes == 6:
                        nombre_mes = "JUNIO"
                    elif mes == 7:
                        nombre_mes = "JULIO"
                    elif mes == 8:
                        nombre_mes = "AGOSTO"
                    elif mes == 9:
                        nombre_mes = "SEPTIEMBRE"
                    elif mes == 10:
                        nombre_mes = "OCTUBRE"
                    elif mes == 11:
                        nombre_mes = "NOVIEMBRE"
                    elif mes == 12:
                        nombre_mes = "DICIEMBRE"

                    ws.merge_range('A1:G1', 'REPORTE DE METAS MENSUALES', formatotitulo_filtros)
                    ws.merge_range('A2:G2', f'{nombre_mes} {anio}', formatoceldacab)

                    filas_recorridas = 5
                    cab = 3
                    sum_tot = 0
                    sum_ven = 0
                    sum_rec = 0
                    sum_real = 0
                    crmp = 0
                    for asesor in asesores:
                        sum_tot = sum_ven = sum_rec = sum_real = 0
                        ws.merge_range(f'A{cab}:G{cab}', f'{asesor.persona} - {"ACTIVO" if asesor.activo else "INACTIVO"} - {"TERRITORIO" if asesor.rol.id == 6 else "OFICINA"}', formatoceldacab)
                        ws.write(cab, 0, '#', formatoceldacab)
                        ws.write(cab, 1, 'Maestría', formatoceldacab)
                        ws.write(cab, 2, 'Meta', formatoceldacab)
                        ws.write(cab, 3, 'Ventas', formatoceldacab)
                        ws.write(cab, 4, 'Recaudación facturada $', formatoceldacab)
                        ws.write(cab, 5, 'Recaudación real $', formatoceldacab)
                        ws.write(cab, 6, 'Cumplimiento', formatoceldacab)
                        idmetas = DetalleAsesorMeta.objects.filter(status=True, inicio__month=mes, inicio__year=anio,
                                                                 asesormeta__maestria__isnull=False,
                                                                 asesormeta__asesor=asesor).values_list('asesormeta__maestria__id', flat=True).order_by('asesormeta__maestria__id').distinct()

                        idventas = VentasProgramaMaestria.objects.filter(status=True, asesor=asesor,
                                                                       valida=True, fecha__month=mes,
                                                                       fecha__year=anio).exclude(inscripcioncohorte__cohortes__maestriaadmision__id__in=idmetas).values_list('inscripcioncohorte__cohortes__maestriaadmision__id', flat=True).order_by('inscripcioncohorte__cohortes__maestriaadmision__id').distinct()

                        metas = list(idmetas) + list(idventas)
                        crmp = 0
                        cont = 1
                        for meta in metas:
                            if DetalleAsesorMeta.objects.filter(status=True, inicio__month=mes, inicio__year=anio,
                                                                 asesormeta__maestria__isnull=False,
                                                                 asesormeta__maestria__id=meta,
                                                                 asesormeta__asesor=asesor).exists():
                                metav = DetalleAsesorMeta.objects.filter(status=True, inicio__month=mes,
                                                                         asesormeta__maestria__isnull=False,
                                                                         asesormeta__maestria__id=meta,
                                                                         asesormeta__asesor=asesor).order_by('-asesormeta__id').first()

                                valor = metav.asesormeta.maestria.porcentaje_cumplimiento(anio, mes, asesor)

                                if valor >= 0 and valor <= 89:
                                    ws.write('A%s' % filas_recorridas, cont, formatoceldaleft_red)
                                    ws.write('B%s' % filas_recorridas, str(metav.asesormeta.maestria.descripcion), formatoceldaleft_red)
                                    ws.write('C%s' % filas_recorridas, metav.cantidad, formatoceldaleft_red)
                                    ws.write('D%s' % filas_recorridas, metav.asesormeta.maestria.ventas_validas_asesor(anio, mes, asesor), formatoceldaleft_red)
                                    ws.write('E%s' % filas_recorridas, f"$ {metav.asesormeta.maestria.recaudado_asesor(anio, mes, asesor):,.2f}", formatoceldaleft_red)
                                    ws.write('F%s' % filas_recorridas, f"$ {metav.asesormeta.maestria.recaudado_asesor_real(anio, mes, asesor):,.2f}", formatoceldaleft_red)
                                    ws.write('G%s' % filas_recorridas, f"{metav.asesormeta.maestria.porcentaje_cumplimiento(anio, mes, asesor)} %", formatoceldaleft_red)
                                if valor > 89 and valor <= 99:
                                    ws.write('A%s' % filas_recorridas, cont, formatoceldaleft_yellow)
                                    ws.write('B%s' % filas_recorridas, str(metav.asesormeta.maestria.descripcion), formatoceldaleft_yellow)
                                    ws.write('C%s' % filas_recorridas, metav.cantidad, formatoceldaleft_yellow)
                                    ws.write('D%s' % filas_recorridas, metav.asesormeta.maestria.ventas_validas_asesor(anio, mes, asesor), formatoceldaleft_yellow)
                                    ws.write('E%s' % filas_recorridas, f"$ {metav.asesormeta.maestria.recaudado_asesor(anio, mes, asesor):,.2f}", formatoceldaleft_yellow)
                                    ws.write('F%s' % filas_recorridas, f"$ {metav.asesormeta.maestria.recaudado_asesor_real(anio, mes, asesor):,.2f}", formatoceldaleft_yellow)
                                    ws.write('G%s' % filas_recorridas, f"{metav.asesormeta.maestria.porcentaje_cumplimiento(anio, mes, asesor)} %", formatoceldaleft_yellow)
                                if valor > 99 and valor <= 119:
                                    ws.write('A%s' % filas_recorridas, cont, formatoceldaleft_green)
                                    ws.write('B%s' % filas_recorridas, str(metav.asesormeta.maestria.descripcion), formatoceldaleft_green)
                                    ws.write('C%s' % filas_recorridas, metav.cantidad, formatoceldaleft_green)
                                    ws.write('D%s' % filas_recorridas, metav.asesormeta.maestria.ventas_validas_asesor(anio, mes, asesor), formatoceldaleft_green)
                                    ws.write('E%s' % filas_recorridas, f"$ {metav.asesormeta.maestria.recaudado_asesor(anio, mes, asesor):,.2f}", formatoceldaleft_green)
                                    ws.write('F%s' % filas_recorridas, f"$ {metav.asesormeta.maestria.recaudado_asesor_real(anio, mes, asesor):,.2f}", formatoceldaleft_green)
                                    ws.write('G%s' % filas_recorridas, f"{metav.asesormeta.maestria.porcentaje_cumplimiento(anio, mes, asesor)} %", formatoceldaleft_green)
                                if valor > 119:
                                    ws.write('A%s' % filas_recorridas, cont, formatoceldaleft_blue)
                                    ws.write('B%s' % filas_recorridas, str(metav.asesormeta.maestria.descripcion), formatoceldaleft_blue)
                                    ws.write('C%s' % filas_recorridas, metav.cantidad, formatoceldaleft_blue)
                                    ws.write('D%s' % filas_recorridas, metav.asesormeta.maestria.ventas_validas_asesor(anio, mes, asesor), formatoceldaleft_blue)
                                    ws.write('E%s' % filas_recorridas, f"$ {metav.asesormeta.maestria.recaudado_asesor(anio, mes, asesor):,.2f}", formatoceldaleft_blue)
                                    ws.write('F%s' % filas_recorridas, f"$ {metav.asesormeta.maestria.recaudado_asesor_real(anio, mes, asesor):,.2f}", formatoceldaleft_blue)
                                    ws.write('G%s' % filas_recorridas, f"{metav.asesormeta.maestria.porcentaje_cumplimiento(anio, mes, asesor)} %", formatoceldaleft_blue)

                                filas_recorridas += 1
                                crmp += 1
                                sum_tot += metav.cantidad
                                sum_ven += metav.asesormeta.maestria.ventas_validas_asesor(anio, mes, asesor)
                                sum_rec += metav.asesormeta.maestria.recaudado_asesor(anio, mes, asesor)
                                sum_real += metav.asesormeta.maestria.recaudado_asesor_real(anio, mes, asesor)
                                cont += 1
                            elif VentasProgramaMaestria.objects.filter(status=True, asesor=asesor,
                                                              valida=True, fecha__month=mes, inscripcioncohorte__cohortes__maestriaadmision__id=meta,
                                                              fecha__year=anio).exclude(inscripcioncohorte__cohortes__maestriaadmision__id__in=idmetas):
                                maestria = MaestriasAdmision.objects.get(status=True, pk=meta)

                                ws.write('A%s' % filas_recorridas, cont, formatoceldaleft4)
                                ws.write('B%s' % filas_recorridas, str(maestria.descripcion), formatoceldaleft4)
                                ws.write('C%s' % filas_recorridas, 'Sin metas', formatoceldaleft4)
                                ws.write('D%s' % filas_recorridas, maestria.ventas_validas_asesor(anio, mes, asesor), formatoceldaleft4)
                                ws.write('E%s' % filas_recorridas, f"$ {maestria.recaudado_asesor(anio, mes, asesor):,.2f}", formatoceldaleft4)
                                ws.write('F%s' % filas_recorridas, f"$ {maestria.recaudado_asesor_real(anio, mes, asesor):,.2f}", formatoceldaleft4)
                                ws.write('G%s' % filas_recorridas, '100%', formatoceldaleft4)

                                filas_recorridas += 1
                                crmp += 1
                                sum_ven += maestria.ventas_validas_asesor(anio, mes, asesor)
                                sum_rec += maestria.recaudado_asesor(anio, mes, asesor)
                                sum_real += maestria.recaudado_asesor_real(anio, mes, asesor)
                                cont += 1

                        if sum_tot > 0 and sum_ven > 0:
                            tot = (sum_ven / sum_tot) * 100
                            por = Decimal(null_to_decimal(tot)).quantize(Decimal('.01'))
                        else:
                            por = 0

                        if por >= 0 and por <= 89:
                            ws.merge_range('A%s:B%s' % (filas_recorridas, filas_recorridas), 'TOTALES:', formatoceldaleft_red1)
                            ws.write('C%s' % filas_recorridas, sum_tot, formatoceldaleft_red)
                            ws.write('D%s' % filas_recorridas, sum_ven, formatoceldaleft_red)
                            ws.write('E%s' % filas_recorridas, f"$ {sum_rec:,.2f}", formatoceldaleft_red)
                            ws.write('F%s' % filas_recorridas, f"$ {sum_real:,.2f}", formatoceldaleft_red)
                            ws.write('G%s' % filas_recorridas, f"{por} %", formatoceldaleft_red)
                        if por > 89 and por <= 99:
                            ws.merge_range('A%s:B%s' % (filas_recorridas, filas_recorridas), 'TOTALES:', formatoceldaleft_yellow1)
                            ws.write('C%s' % filas_recorridas, sum_tot, formatoceldaleft_yellow)
                            ws.write('D%s' % filas_recorridas, sum_ven, formatoceldaleft_yellow)
                            ws.write('E%s' % filas_recorridas, f"$ {sum_rec:,.2f}", formatoceldaleft_yellow)
                            ws.write('F%s' % filas_recorridas, f"$ {sum_real:,.2f}", formatoceldaleft_yellow)
                            ws.write('G%s' % filas_recorridas, f"{por} %", formatoceldaleft_yellow)
                        if por > 99 and por <= 119:
                            ws.merge_range('A%s:B%s' % (filas_recorridas, filas_recorridas), 'TOTALES:', formatoceldaleft_green1)
                            ws.write('C%s' % filas_recorridas, sum_tot, formatoceldaleft_green)
                            ws.write('D%s' % filas_recorridas, sum_ven, formatoceldaleft_green)
                            ws.write('E%s' % filas_recorridas, f"$ {sum_rec:,.2f}", formatoceldaleft_green)
                            ws.write('F%s' % filas_recorridas, f"$ {sum_real:,.2f}", formatoceldaleft_green)
                            ws.write('G%s' % filas_recorridas, f"{por} %", formatoceldaleft_green)
                        if por > 119:
                            ws.merge_range('A%s:B%s' % (filas_recorridas, filas_recorridas), 'TOTALES:', formatoceldaleft_blue1)
                            ws.write('C%s' % filas_recorridas, sum_tot, formatoceldaleft_blue)
                            ws.write('D%s' % filas_recorridas, sum_ven, formatoceldaleft_blue)
                            ws.write('E%s' % filas_recorridas, f"$ {sum_rec:,.2f}", formatoceldaleft_blue)
                            ws.write('F%s' % filas_recorridas, f"$ {sum_real:,.2f}", formatoceldaleft_blue)
                            ws.write('G%s' % filas_recorridas, f"{por} %", formatoceldaleft_blue)

                        can_regi = 4 + crmp
                        cab = cab + can_regi
                        filas_recorridas += 4

                    workbook.close()
                    output.seek(0)
                    fecha_hora_actual = datetime.now().date()
                    filename = 'Metas_Mensuales_' + str(fecha_hora_actual) + '.xlsx'
                    response = HttpResponse(output,

                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reportemetasmensualesmaestria':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('metas_mensuales_maestria')
                    ws.set_column(0, 0, 5)
                    ws.set_column(1, 1, 100)
                    ws.set_column(2, 2, 15)
                    ws.set_column(3, 3, 15)
                    ws.set_column(4, 4, 15)
                    ws.set_column(5, 5, 15)
                    ws.set_column(6, 6, 15)

                    formatotitulo_filtros = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white', 'valign': 'vcenter'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft4 = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#E3651D', 'font_color': 'black', 'valign': 'vcenter'})

                    formatoceldaleft_red = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#E74646', 'font_color': 'black', 'valign': 'vcenter'})

                    formatoceldaleft_red1 = workbook.add_format(
                        {'align': 'right', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#E74646', 'font_color': 'black', 'valign': 'vcenter'})

                    formatoceldaleft_yellow = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#F7D060', 'font_color': 'black', 'valign': 'vcenter'})

                    formatoceldaleft_yellow1 = workbook.add_format(
                        {'align': 'right', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#F7D060', 'font_color': 'black', 'valign': 'vcenter'})

                    formatoceldaleft_green = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#79AC78', 'font_color': 'black', 'valign': 'vcenter'})

                    formatoceldaleft_green1 = workbook.add_format(
                        {'align': 'right', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#79AC78', 'font_color': 'black', 'valign': 'vcenter'})

                    formatoceldaleft_blue = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#3081D0', 'font_color': 'black', 'valign': 'vcenter'})

                    formatoceldaleft_blue1 = workbook.add_format(
                        {'align': 'right', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#3081D0', 'font_color': 'black', 'valign': 'vcenter'})

                    decimalformat = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    decimalformat2 = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat3 = workbook.add_format({'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    anio = mes = 0
                    nombre_mes = ""

                    if 'anio' in request.GET:
                        anio = int(request.GET['anio'])
                    if 'mes' in request.GET:
                        mes = int(request.GET['mes'])

                    if mes == 1:
                        nombre_mes = "ENERO"
                    elif mes == 2:
                        nombre_mes = "FEBRERO"
                    elif mes == 3:
                        nombre_mes = "MARZO"
                    elif mes == 4:
                        nombre_mes = "ABRIL"
                    elif mes == 5:
                        nombre_mes = "MAYO"
                    elif mes == 6:
                        nombre_mes = "JUNIO"
                    elif mes == 7:
                        nombre_mes = "JULIO"
                    elif mes == 8:
                        nombre_mes = "AGOSTO"
                    elif mes == 9:
                        nombre_mes = "SEPTIEMBRE"
                    elif mes == 10:
                        nombre_mes = "OCTUBRE"
                    elif mes == 11:
                        nombre_mes = "NOVIEMBRE"
                    elif mes == 12:
                        nombre_mes = "DICIEMBRE"

                    ws.merge_range('A1:G1', 'REPORTE DE METAS MENSUALES', formatotitulo_filtros)
                    ws.merge_range('A2:G2', f'{nombre_mes} {anio}', formatoceldacab)

                    filas_recorridas = 5
                    cab = 3
                    idmaestrias = None
                    sum_tot = 0
                    sum_ven = 0
                    sum_rec = 0
                    crmp = 0

                    sum_tot = sum_ven = sum_rec = sum_real = 0
                    ws.merge_range(f'A{cab}:G{cab}', 'PROGRAMAS DE MAESTRÍA', formatoceldacab)
                    ws.write(cab, 0, '#', formatoceldacab)
                    ws.write(cab, 1, 'Maestría', formatoceldacab)
                    ws.write(cab, 2, 'Meta', formatoceldacab)
                    ws.write(cab, 3, 'Ventas', formatoceldacab)
                    ws.write(cab, 4, 'Recaudación facturada $', formatoceldacab)
                    ws.write(cab, 5, 'Recaudación real $', formatoceldacab)
                    ws.write(cab, 6, 'Cumplimiento', formatoceldacab)

                    idm = DetalleAsesorMeta.objects.filter(status=True, inicio__month=mes, inicio__year=anio,
                                                           asesormeta__maestria__isnull=False).values_list('asesormeta__maestria__id', flat=True).order_by('asesormeta__maestria__id').distinct()

                    idv = VentasProgramaMaestria.objects.filter(status=True, valida=True, fecha__month=mes,
                                                                fecha__year=anio).exclude(inscripcioncohorte__cohortes__maestriaadmision__id__in=idm).values_list('inscripcioncohorte__cohortes__maestriaadmision__id', flat=True).order_by('inscripcioncohorte__cohortes__maestriaadmision__id').distinct()

                    idmaestrias = list(idm) + list(idv)
                    crmp = 0
                    cont = 1
                    for idmaestria in idmaestrias:
                        if DetalleAsesorMeta.objects.filter(status=True, inicio__month=mes, inicio__year=anio,
                                                             asesormeta__maestria__isnull=False,
                                                             asesormeta__maestria__id=idmaestria).exists():

                            maestria = MaestriasAdmision.objects.get(status=True, pk=idmaestria)
                            valor = maestria.porcentaje_cumplimiento_maes(anio, mes)

                            if valor >=0 and valor <=89:
                                ws.write('A%s' % filas_recorridas, cont, formatoceldaleft_red)
                                ws.write('B%s' % filas_recorridas, str(maestria.descripcion), formatoceldaleft_red)
                                ws.write('C%s' % filas_recorridas, maestria.total_metas_mes(mes, anio), formatoceldaleft_red)
                                ws.write('D%s' % filas_recorridas, maestria.ventas_maestrias_validas(anio, mes), formatoceldaleft_red)
                                ws.write('E%s' % filas_recorridas, f"$ {maestria.recaudado_maestria(anio, mes):,.2f}", formatoceldaleft_red)
                                ws.write('F%s' % filas_recorridas, f"$ {maestria.recaudado_maestria_real(anio, mes):,.2f}", formatoceldaleft_red)
                                ws.write('G%s' % filas_recorridas, f"{maestria.porcentaje_cumplimiento_maes(anio, mes)} %", formatoceldaleft_red)
                            if valor > 89 and valor <=99:
                                ws.write('A%s' % filas_recorridas, cont, formatoceldaleft_yellow)
                                ws.write('B%s' % filas_recorridas, str(maestria.descripcion), formatoceldaleft_yellow)
                                ws.write('C%s' % filas_recorridas, maestria.total_metas_mes(mes, anio), formatoceldaleft_yellow)
                                ws.write('D%s' % filas_recorridas, maestria.ventas_maestrias_validas(anio, mes), formatoceldaleft_yellow)
                                ws.write('E%s' % filas_recorridas, f"$ {maestria.recaudado_maestria(anio, mes):,.2f}", formatoceldaleft_yellow)
                                ws.write('F%s' % filas_recorridas, f"$ {maestria.recaudado_maestria_real(anio, mes):,.2f}", formatoceldaleft_yellow)
                                ws.write('G%s' % filas_recorridas, f"{maestria.porcentaje_cumplimiento_maes(anio, mes)} %", formatoceldaleft_yellow)
                            if valor > 99 and valor <=119:
                                ws.write('A%s' % filas_recorridas, cont, formatoceldaleft_green)
                                ws.write('B%s' % filas_recorridas, str(maestria.descripcion), formatoceldaleft_green)
                                ws.write('C%s' % filas_recorridas, maestria.total_metas_mes(mes, anio), formatoceldaleft_green)
                                ws.write('D%s' % filas_recorridas, maestria.ventas_maestrias_validas(anio, mes), formatoceldaleft_green)
                                ws.write('E%s' % filas_recorridas, f"$ {maestria.recaudado_maestria(anio, mes):,.2f}", formatoceldaleft_green)
                                ws.write('F%s' % filas_recorridas, f"$ {maestria.recaudado_maestria_real(anio, mes):,.2f}", formatoceldaleft_green)
                                ws.write('G%s' % filas_recorridas, f"{maestria.porcentaje_cumplimiento_maes(anio, mes)} %", formatoceldaleft_green)
                            if valor > 119:
                                ws.write('A%s' % filas_recorridas, cont, formatoceldaleft_blue)
                                ws.write('B%s' % filas_recorridas, str(maestria.descripcion), formatoceldaleft_blue)
                                ws.write('C%s' % filas_recorridas, maestria.total_metas_mes(mes, anio), formatoceldaleft_blue)
                                ws.write('D%s' % filas_recorridas, maestria.ventas_maestrias_validas(anio, mes), formatoceldaleft_blue)
                                ws.write('E%s' % filas_recorridas, f"$ {maestria.recaudado_maestria(anio, mes):,.2f}", formatoceldaleft_blue)
                                ws.write('F%s' % filas_recorridas, f"$ {maestria.recaudado_maestria_real(anio, mes):,.2f}", formatoceldaleft_blue)
                                ws.write('G%s' % filas_recorridas, f"{maestria.porcentaje_cumplimiento_maes(anio, mes)} %", formatoceldaleft_blue)

                            filas_recorridas += 1
                            crmp += 1
                            sum_tot += maestria.total_metas_mes(mes, anio)
                            sum_ven += maestria.ventas_maestrias_validas(anio, mes)
                            sum_rec += maestria.recaudado_maestria(anio, mes)
                            sum_real += maestria.recaudado_maestria_real(anio, mes)
                            cont += 1

                        elif VentasProgramaMaestria.objects.filter(status=True, valida=True, fecha__month=mes,
                                                                  inscripcioncohorte__cohortes__maestriaadmision__id=idmaestria,
                                                                  fecha__year=anio).exclude(inscripcioncohorte__cohortes__maestriaadmision__id__in=idm):

                            maestria = MaestriasAdmision.objects.get(status=True, pk=idmaestria)

                            ws.write('A%s' % filas_recorridas, cont, formatoceldaleft4)
                            ws.write('B%s' % filas_recorridas, str(maestria.descripcion), formatoceldaleft4)
                            ws.write('C%s' % filas_recorridas, 'Sin metas', formatoceldaleft4)
                            ws.write('D%s' % filas_recorridas, maestria.ventas_maestrias_validas(anio, mes), formatoceldaleft4)
                            ws.write('E%s' % filas_recorridas, f"$ {maestria.recaudado_maestria(anio, mes):,.2f}", formatoceldaleft4)
                            ws.write('F%s' % filas_recorridas, f"$ {maestria.recaudado_maestria_real(anio, mes):,.2f}", formatoceldaleft4)
                            ws.write('G%s' % filas_recorridas, '100%', formatoceldaleft4)

                            filas_recorridas += 1
                            crmp += 1
                            sum_ven += maestria.ventas_maestrias_validas(anio, mes)
                            sum_rec += maestria.recaudado_maestria(anio, mes)
                            sum_real += maestria.recaudado_maestria_real(anio, mes)
                            cont += 1

                    if sum_tot > 0 and sum_ven > 0:
                        # if sum_ven > sum_tot:
                        #     por = 100
                        # else:
                        tot = (sum_ven / sum_tot) * 100
                        por = Decimal(null_to_decimal(tot)).quantize(Decimal('.01'))
                    else:
                        por = 0

                    if por >= 0 and por <= 89:
                        ws.merge_range('A%s:B%s' % (filas_recorridas, filas_recorridas), 'TOTALES:', formatoceldaleft_red1)
                        ws.write('C%s' % filas_recorridas, sum_tot, formatoceldaleft_red)
                        ws.write('D%s' % filas_recorridas, sum_ven, formatoceldaleft_red)
                        ws.write('E%s' % filas_recorridas, f"$ {sum_rec:,.2f}", formatoceldaleft_red)
                        ws.write('F%s' % filas_recorridas, f"$ {sum_real:,.2f}", formatoceldaleft_red)
                        ws.write('G%s' % filas_recorridas, f"{por} %", formatoceldaleft_red)
                    if por > 89 and por <= 99:
                        ws.merge_range('A%s:B%s' % (filas_recorridas, filas_recorridas), 'TOTALES:', formatoceldaleft_yellow1)
                        ws.write('C%s' % filas_recorridas, sum_tot, formatoceldaleft_yellow)
                        ws.write('D%s' % filas_recorridas, sum_ven, formatoceldaleft_yellow)
                        ws.write('E%s' % filas_recorridas, f"$ {sum_rec:,.2f}", formatoceldaleft_yellow)
                        ws.write('F%s' % filas_recorridas, f"$ {sum_real:,.2f}", formatoceldaleft_yellow)
                        ws.write('G%s' % filas_recorridas, f"{por} %", formatoceldaleft_yellow)
                    if por > 99 and por <= 119:
                        ws.merge_range('A%s:B%s' % (filas_recorridas, filas_recorridas), 'TOTALES:', formatoceldaleft_green1)
                        ws.write('C%s' % filas_recorridas, sum_tot, formatoceldaleft_green)
                        ws.write('D%s' % filas_recorridas, sum_ven, formatoceldaleft_green)
                        ws.write('E%s' % filas_recorridas, f"$ {sum_rec:,.2f}", formatoceldaleft_green)
                        ws.write('F%s' % filas_recorridas, f"$ {sum_real:,.2f}", formatoceldaleft_green)
                        ws.write('G%s' % filas_recorridas, f"{por} %", formatoceldaleft_green)
                    if por > 119:
                        ws.merge_range('A%s:B%s' % (filas_recorridas, filas_recorridas), 'TOTALES:', formatoceldaleft_blue1)
                        ws.write('C%s' % filas_recorridas, sum_tot, formatoceldaleft_blue)
                        ws.write('D%s' % filas_recorridas, sum_ven, formatoceldaleft_blue)
                        ws.write('E%s' % filas_recorridas, f"$ {sum_rec:,.2f}", formatoceldaleft_blue)
                        ws.write('F%s' % filas_recorridas, f"$ {sum_real:,.2f}", formatoceldaleft_blue)
                        ws.write('G%s' % filas_recorridas, f"{por} %", formatoceldaleft_blue)

                    can_regi = 4 + crmp
                    cab = cab + can_regi
                    filas_recorridas += 4

                    workbook.close()
                    output.seek(0)
                    fecha_hora_actual = datetime.now().date()
                    filename = 'Metas_Mensuales_Maestria_' + str(fecha_hora_actual) + '.xlsx'
                    response = HttpResponse(output,

                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporteestudiantesposgrado':
                try:
                    notifi = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                          titulo='Reporte de graduados unemi', destinatario=persona,
                                          url='',
                                          prioridad=1, app_label='SGA',
                                          fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                          en_proceso=True)
                    notifi.save(request)
                    reporte_estudiantes_unemi(request=request, notiid=notifi.id).start()
                    return JsonResponse({"result": True,
                                         "mensaje": u"El reporte de GRADUADOS UNEMI se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass

            elif action == 'listadocohortes':
                try:
                    maestria = request.GET.get('maestria')
                    listmaestria = maestria
                    if len(maestria) > 1:
                        listmaestria = maestria.split(',')
                    # querybase = SubAreaConocimientoTitulacion.objects.filter(status=True, areaconocimiento__in=listcampoamplio).order_by('codigo')
                    querybase = CohorteMaestria.objects.filter(status=True, maestriaadmision__id__in=listmaestria).order_by('-id').distinct()
                    if 'q' in request.GET:
                        q = request.GET['q'].upper().strip()
                        if q != 'UNDEFINED':
                            querybase = querybase.filter((Q(descripcion__icontains=q))).distinct()[:30]
                    data = {"result": "ok", "results": [{"id": x.id, "idca": x.maestriaadmision.id, "name": "{} - {}".format(x.maestriaadmision.id, x.descripcion)} for x in querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'reporteventasasesorcomercial':
                try:
                    __author__ = 'Unemi'

                    asesorcomercial = AsesorComercial.objects.get(status=True, persona__id=persona.id)

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('ventas')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 15)
                    ws.set_column(2, 2, 15)
                    ws.set_column(3, 3, 30)
                    ws.set_column(4, 4, 30)
                    ws.set_column(5, 5, 40)
                    ws.set_column(6, 6, 60)
                    ws.set_column(7, 7, 40)
                    ws.set_column(8, 8, 15)
                    ws.set_column(9, 9, 20)
                    ws.set_column(10, 10, 40)
                    ws.set_column(11, 11, 15)
                    ws.set_column(12, 12, 15)
                    ws.set_column(13, 13, 15)
                    ws.set_column(14, 14, 15)
                    ws.set_column(15, 15, 30)
                    ws.set_column(16, 16, 15)
                    ws.set_column(17, 17, 15)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size':14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    decimalformat2 = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    cohorte = 0
                    desde = hasta = ''

                    if 'cohorte' in request.GET:
                        cohorte = request.GET['cohorte']

                    if 'desde' in request.GET:
                        desde = request.GET['desde']
                    if 'hasta' in request.GET:
                        hasta = request.GET['hasta']

                    ws.merge_range('A1:O1', "Reporte de ventas del asesor" + ' ' + asesorcomercial.persona.nombre_completo_inverso(), formatotitulo_filtros)
                    if desde and hasta:
                        ws.merge_range('A2:O2', 'Desde el ' + desde + ' Hasta el ' + hasta, formatotitulo_filtros)

                    ws.write(2, 0, 'N°', formatoceldacab)
                    ws.write(2, 1, 'Id', formatoceldacab)
                    ws.write(2, 2, 'Cédula', formatoceldacab)
                    ws.write(2, 3, 'Provincia', formatoceldacab)
                    ws.write(2, 4, 'Cantón', formatoceldacab)
                    ws.write(2, 5, 'Prospecto', formatoceldacab)
                    ws.write(2, 6, 'Cohorte', formatoceldacab)
                    ws.write(2, 7, 'Maestría', formatoceldacab)
                    ws.write(2, 8, 'Fecha de la venta', formatoceldacab)
                    ws.write(2, 9, 'Forma de pago', formatoceldacab)
                    ws.write(2, 10, 'Valor de la maestría', formatoceldacab)
                    ws.write(2, 11, 'Valor cancelado', formatoceldacab)
                    ws.write(2, 12, 'Por recaudar', formatoceldacab)
                    ws.write(2, 13, 'Medio de pago', formatoceldacab)
                    ws.write(2, 14, '¿Está facturado?', formatoceldacab)
                    ws.write(2, 15, 'Correo', formatoceldacab)
                    ws.write(2, 16, 'Teléfono', formatoceldacab)
                    ws.write(2, 17, 'Canal de información', formatoceldacab)


                    filtro = Q(status=True, asesor=asesorcomercial)

                    if cohorte != "":
                        if eval(request.GET['cohorte'])[0] != "0":
                            filtro = filtro & Q(inscripcioncohorte__cohortes__id__in=eval(request.GET['cohorte']))

                    if desde and hasta:
                        filtro = filtro & Q(fecha__range=(desde, hasta))
                    elif desde:
                        filtro = filtro & Q(fecha__gte=desde)
                    elif hasta:
                        filtro = filtro & Q(fecha__lte=hasta)

                    ventas = VentasProgramaMaestria.objects.filter(filtro).exclude(valida=False).order_by('fecha')

                    filas_recorridas = 4
                    cont = 1
                    sum_maestria = 0
                    sum_cancelado = 0
                    sum_recaudar = 0
                    fecha_can = ''
                    sucomp = ''

                    for venta in ventas:
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(venta.inscripcioncohorte.id), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(venta.inscripcioncohorte.inscripcionaspirante.persona.identificacion()), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(venta.inscripcioncohorte.inscripcionaspirante.persona.provincia.nombre if venta.inscripcioncohorte.inscripcionaspirante.persona.provincia else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(venta.inscripcioncohorte.inscripcionaspirante.persona.canton.nombre if venta.inscripcioncohorte.inscripcionaspirante.persona.canton else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(venta.inscripcioncohorte.inscripcionaspirante.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(venta.inscripcioncohorte.cohortes.descripcion), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(venta.inscripcioncohorte.cohortes.maestriaadmision.descripcion), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str(venta.fecha), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str(venta.inscripcioncohorte.formapagopac.descripcion), formatoceldaleft)
                        ws.write('K%s' % filas_recorridas, venta.inscripcioncohorte.cohortes.valorprogramacertificado if venta.inscripcioncohorte.cohortes.valorprogramacertificado else 'NO REGISTRA', decimalformat)
                        ws.write('L%s' % filas_recorridas, venta.inscripcioncohorte.total_pagado_rubro_cohorte(), decimalformat)
                        ws.write('M%s' % filas_recorridas, venta.inscripcioncohorte.total_pendiente(), decimalformat)
                        ws.write('N%s' % filas_recorridas, str(venta.mediopago), formatoceldaleft)
                        ws.write('O%s' % filas_recorridas, str('SI' if venta.inscripcioncohorte.total_pagado_rubro_cohorte() > 0 else 'NO'), formatoceldaleft)
                        ws.write('P%s' % filas_recorridas, str(venta.inscripcioncohorte.inscripcionaspirante.persona.email if venta.inscripcioncohorte.inscripcionaspirante.persona.email else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('Q%s' % filas_recorridas, str(venta.inscripcioncohorte.inscripcionaspirante.persona.telefono if venta.inscripcioncohorte.inscripcionaspirante.persona.telefono else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('R%s' % filas_recorridas, str(venta.inscripcioncohorte.canal.descripcion if venta.inscripcioncohorte.canal else 'NO REGISTRA'), formatoceldaleft)

                        filas_recorridas += 1
                        cont += 1
                        sum_maestria += venta.inscripcioncohorte.cohortes.valorprogramacertificado
                        sum_cancelado += venta.inscripcioncohorte.total_pagado_rubro_cohorte()
                        sum_recaudar += venta.inscripcioncohorte.total_pendiente()

                    ws.merge_range('A%s:J%s' % (filas_recorridas, filas_recorridas), 'TOTALES:', formatoceldaleft3)

                    ws.write('K%s' % filas_recorridas, sum_maestria, decimalformat2)
                    ws.write('L%s' % filas_recorridas, sum_cancelado, decimalformat2)
                    ws.write('M%s' % filas_recorridas, sum_recaudar, decimalformat2)

                    workbook.close()
                    output.seek(0)
                    fecha_hora_actual = datetime.now().date()
                    filename = 'Listado_ventas_asesor_' + str(fecha_hora_actual) + '.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'evidenciasfinanciamiento':
                try:
                    if 'sign' in request.GET:
                        data['sign'] = request.GET['sign']

                    data['title'] = u'Revisión de requisitos de financiamiento'
                    # data['tipoestado'] = request.GET['tipoestado']
                    # data['cant_requisitos'] = request.GET['cant_requisitos']
                    data['cohorte'] = cohorte = CohorteMaestria.objects.get(pk=int(request.GET['idcohorte']))
                    if persona.es_asesor_financiamiento():
                        data['revisaevidencia'] = True
                    else:
                        data['revisaevidencia'] = False
                    data['inscripcioncohorte'] = inscrito = InscripcionCohorte.objects.get(
                        pk=int(request.GET['aspirante']), status=True)

                    # idrequisitoscomer = ClaseRequisito.objects.filter(clasificacion=3).values_list('requisito__id', flat=True)
                    if inscrito.subirrequisitogarante:
                        data['requisitospos'] = cohorte.requisitosmaestria_set.filter(status=True, requisito__claserequisito__clasificacion__id=3, requisito__tipopersona__id=1).order_by('id')
                        data['requisitosgar'] = cohorte.requisitosmaestria_set.filter(status=True, requisito__claserequisito__clasificacion__id=3, requisito__tipopersona__id=2).order_by('id')
                    else:
                        data['requisitospos'] = cohorte.requisitosmaestria_set.filter(status=True, requisito__claserequisito__clasificacion__id=3, requisito__tipopersona__id=1).order_by('id')

                    # if not inscripcioncohorte.grupo:
                    #     data['requisitos'] = cohorte.requisitosmaestria_set.filter(status=True).order_by('id')
                    # else:
                    #     gruporequisitos = inscripcioncohorte.grupo.requisitosgrupocohorte_set.values_list(
                    #         'requisito_id', flat=True).filter(status=True)
                    #     data['requisitos'] = cohorte.requisitosmaestria_set.filter(requisito_id__in=gruporequisitos,
                    #                                                                status=True).order_by('id')
                    return render(request, "comercial/evidenciasfinanciamiento.html", data)
                except Exception as ex:
                    pass

            elif action == 'informeevidencias1':
                try:
                    data['title'] = u'Revisión de evidencias de Financiamiento'
                    requisito = RequisitosMaestria.objects.get(pk=request.GET['idrequisito'])
                    if not requisito.evidenciarequisitosaspirante_set.values("id").filter(
                            inscripcioncohorte_id=request.GET['idinscripcioncohote'], status=True).exists():
                        return JsonResponse({"result": "sin", "mensaje": u"NO EXISTE EVIDENCIA."})
                    data['requisitoinscrito'] = requisito.evidenciarequisitosaspirante_set.get(
                        inscripcioncohorte_id=request.GET['idinscripcioncohote'], status=True)
                    template = get_template("comercial/informeevidenciafinan.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'listadorequisitosfinanciamiento':
                try:
                    data['title'] = u'Requisitos de Financiamiento para programas de Maestría'
                    tienepagoexamen = False
                    ventanaactiva = 1
                    bloqueasubidapago = 1
                    hoy = datetime.now().date()
                    tienerequisitos = False
                    # data['tipoestado'] = request.GET['tipoestado']
                    # data['cant_requisitos'] = request.GET['cant_requisitos']
                    data['inscripcioncohorte'] = inscripcioncohorte = InscripcionCohorte.objects.get(
                        pk=int(encrypt(request.GET['idinscripcioncohorte'])))
                    inscripciondescuento = None
                    tienerequisitosbecas = False
                    data['tienerequisitosbecas'] = tienerequisitosbecas
                    data['inscripciondescuento'] = inscripciondescuento

                    idrequisitoscomer = ClaseRequisito.objects.filter(clasificacion=3).values_list('requisito__id', flat=True)
                    requisitosfinan = RequisitosMaestria.objects.filter(status=True, cohorte=inscripcioncohorte.cohortes, requisito__id__in=idrequisitoscomer).order_by('id')

                    if inscripcioncohorte.evidenciarequisitosaspirante_set.filter(status=True, requisitos__id__in=requisitosfinan.values_list('id', flat=True)).exists():
                        tienerequisitos = True
                    data['tienerequisitos'] = tienerequisitos

                    permisorequisito = False
                    if inscripcioncohorte.cohortes.fechafinrequisito >= hoy:
                        permisorequisito = True
                    data['permisorequisito'] = permisorequisito

                    data['requisitos'] = requisitosfinan

                    # idrequisitoscomer = ClaseRequisito.objects.filter(clasificacion=3).values_list('requisito__id', flat=True)
                    # data['requisitos'] = RequisitosMaestria.objects.filter(status=True, cohorte=inscripcioncohorte.cohortes, requisito__id__in=idrequisitoscomer).order_by('id')

                    return render(request, "comercial/listadorequisitosfinanciamiento.html", data)
                except Exception as ex:
                    pass

            elif action == 'informeevidenciascontrato':
                try:
                    data['title'] = u'Revisión de evidencia de contrato'
                    contrato = None
                    if 'idcontrato' in request.GET:
                        if request.GET['idcontrato']:
                            data['contrato'] = contrato = Contrato.objects.get(pk=request.GET['idcontrato'])
                    if not contrato:
                        return JsonResponse({"result": "sin", "mensaje": u"NO EXISTE EVIDENCIA."})
                    if not contrato.archivocontrato:
                        return JsonResponse({"result": "sin", "mensaje": u"NO EXISTE EVIDENCIA."})
                    template = get_template("comercial/informe_evidencia_contrato.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'informeevidenciaspagare':
                try:
                    data['title'] = u'Revisión de evidencia de pagaré'
                    contrato = None
                    if 'idcontrato' in request.GET:
                        if request.GET['idcontrato']:
                            data['pagare'] = contrato = Contrato.objects.get(pk=request.GET['idcontrato'])
                    if not contrato:
                        return JsonResponse({"result": "sin", "mensaje": u"NO EXISTE EVIDENCIA."})
                    if not contrato.archivopagare:
                        return JsonResponse({"result": "sin", "mensaje": u"NO EXISTE EVIDENCIA."})
                    template = get_template("comercial/informe_evidencia_pagare.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'informeevidenciasconvenio':
                try:
                    from posgrado.models import EvidenciaRequisitoConvenio
                    data['title'] = u'Revisión de evidencia de convenio'
                    econvenio = None
                    if 'idcontrato' in request.GET:
                        if request.GET['idcontrato']:
                            data['econvenio'] = econvenio = EvidenciaRequisitoConvenio.objects.get(pk=request.GET['idcontrato'])
                    if not econvenio:
                        return JsonResponse({"result": "sin", "mensaje": u"NO EXISTE EVIDENCIA."})
                    template = get_template("comercial/informe_evidencia_convenio.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'detallerubros':
                try:
                    data = {}
                    inscrito = InscripcionCohorte.objects.get(pk=request.GET['idi'])
                    rubro1 = Rubro.objects.filter(inscripcion=inscrito, status=True)
                    data['rubros'] = rubro1
                    template = get_template("admitidos/detallepago.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'detallerubrosins':
                try:
                    data = {}
                    inscrito = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    rubro1 = Rubro.objects.filter(inscripcion=inscrito, status=True)
                    data['rubros'] = rubro1
                    template = get_template("admitidos/detallepago.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'tablaamortizacion':
                try:
                    data['title'] = u'Tabla de amortización'
                    data['cohorte'] = cohorte = CohorteMaestria.objects.get(status=True, pk=int(encrypt(request.GET['idcohorte'])))
                    data['aspirante'] = inscripcion = InscripcionCohorte.objects.get(status=True, pk=int(encrypt(request.GET['aspirante'])))
                    # infofinancieramae = InfraestructuraEquipamientoInformacionPac.objects.filter(programapac__carrera=inscripcion.cohortes.maestriaadmision.carrera).last()
                    # if infofinancieramae.valorarancel:
                    #     data['infofinancieramae'] = infofinancieramae
                    data['tablaamortizacion'] = tablaamortizacion = TablaAmortizacion.objects.filter(status=True, contrato=inscripcion.contrato_set.filter(status=True).last())
                    total = 0
                    for valor in tablaamortizacion:
                        total = total + valor.valor
                    data['total'] = total
                    return render(request, "comercial/tablaamortizacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'evidenciacontrato':
                try:
                    from posgrado.models import EvidenciaRequisitoConvenio
                    if 'sign' in request.GET:
                        data['sign'] = request.GET['sign']

                    data['title'] = u'Revisión de contrato de pago'
                    data['cohorte'] = cohorte = CohorteMaestria.objects.get(pk=int(encrypt(request.GET['idcohorte'])))
                    if persona.es_asesor_financiamiento():
                        data['revisaevidencia'] = True
                    else:
                        data['revisaevidencia'] = False
                    data['inscripcioncohorte'] = inscripcioncohorte = InscripcionCohorte.objects.get(
                        pk=int(encrypt(request.GET['aspirante'])), status=True)
                    data['contrato'] = inscripcioncohorte.contrato_set.filter(status=True).last()
                    if inscripcioncohorte.convenio:
                        if inscripcioncohorte.convenio.suberequisito:
                            data['evidenciaconvenio'] = inscripcioncohorte.evidenciarequisitoconvenio_set.filter(status=True,convenio=inscripcioncohorte.convenio).last()
                    return render(request, "comercial/evidenciacontrato.html", data)
                except Exception as ex:
                    pass

            elif action == 'adm_subirevidenciacontrato':
                try:
                    data['title'] = u'Registro de contrato de pago'
                    data['inscripcioncohorte'] = inscripcioncohorte = InscripcionCohorte.objects.get(
                        pk=int(encrypt(request.GET['idinscripcioncohorte'])))
                    permisocontrato = False
                    fechafincontrato = inscripcioncohorte.cohortes.fechafininsp + timedelta(days=30)
                    if fechafincontrato >= hoy:
                        permisocontrato = True
                    data['permisocontrato'] = permisocontrato
                    formapago = 1
                    if inscripcioncohorte.formapagopac:
                        formapago = inscripcioncohorte.formapagopac.id
                    if formapago == 2:
                        data['garante'] = garante = inscripcioncohorte.garantepagomaestria_set.filter(status=True).last()
                    if TipoFormaPagoPac.objects.filter(pk=formapago).exists():
                        data['fpago'] = fpago = TipoFormaPagoPac.objects.filter(pk=formapago).last()
                        data['contrato'] = contrato = Contrato.objects.filter(status=True, inscripcion=inscripcioncohorte, inscripcion__status=True).last()
                    return render(request, "comercial/adm_subircontratopago.html", data)
                except Exception as ex:
                    pass

            elif action == 'cargarcontratopago':
                try:
                    form2 = ContratoPagoMaestriaForm()
                    data['action'] = 'cargarcontratopago'
                    data['filtro'] = filtro = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    data['fpago'] = request.GET['fp']
                    data['form2'] = form2
                    template = get_template("comercial/adm_addcontratopago.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'aceptartablaamortizacionpagaremae':
                try:
                    data['id'] = request.GET['id']
                    data['inscripcioncohorte'] = insc = InscripcionCohorte.objects.get(pk=request.GET['id'])
                    data['contrato'] = contrato = insc.contrato_set.filter(status=True).last()
                    configuracion = None
                    if insc.Configfinanciamientocohorte:
                        data['configuracion'] = configuracion = ConfigFinanciamientoCohorte.objects.filter(pk=insc.Configfinanciamientocohorte.id).last()
                    if insc.contrato_set.filter(status=True).values('id').last() and insc.contrato_set.filter(status=True).last().tablaamortizacion_set.values('id').filter(status=True) and insc.contrato_set.filter(status=True).last().tablaamortizacionajustada:
                        tablaamortizacion = []
                        contrato = contrato
                        montototal = contrato.tablaamortizacion_set.values_list('valor').filter(status=True)
                        total = Decimal(0)
                        valorpendiente = Decimal(0)
                        for valor in montototal:
                            total = total + valor[0]
                        data['total'] = total
                        tablaamortizacionajustada = contrato.tablaamortizacion_set.values_list('cuota', 'fecha', 'fechavence', 'valor').filter(status=True)
                        for tabla in tablaamortizacionajustada:
                            if tabla[0] == 0:
                                valorarancel = total - tabla[3]
                                valorpendiente = valorarancel
                                tablaamortizacion += [('', '', '', tabla[3], valorarancel)]
                            else:
                                valorpendiente = valorpendiente - tabla[3]
                                tablaamortizacion += [(tabla[0], tabla[1], tabla[2], tabla[3], valorpendiente)]

                        data['tablaamortizacion'] = tablaamortizacion
                    else:
                        if configuracion:
                            # data['contrato'] = contrato = insc.contrato_set.last()
                            data['tablaamortizacion'] = tablaamortizacion = configuracion.tablaamortizacioncohortemaestria(insc, hoy)
                            total = 0
                            for valor in tablaamortizacion:
                                total = total + valor[3]
                            data['total'] = total
                    template = get_template("comercial/modal/modaltablaamortizacionpagare.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'cargarpagareaspirantemaestria':
                try:
                    data['action'] = 'cargarpagareaspirantemaestria'
                    form2 = ContratoPagoMaestriaForm()
                    data['filtro'] = filtro = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    data['fpago'] = request.GET['fp']
                    data['form2'] = form2
                    template = get_template("comercial/addcontratopago.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'cargarpagareaspirantemaestriaase':
                try:
                    data['action'] = 'cargarpagareaspirantemaestriaase'
                    form2 = ContratoPagoMaestriaForm()
                    data['filtro'] = filtro = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    data['fpago'] = request.GET['fp']
                    data['form2'] = form2
                    template = get_template("alu_requisitosmaestria/addcontratopago.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'cargarrequisitoconvenio':
                try:
                    from posgrado.forms import RequisitoConvenioAspiranteForm
                    data['action'] = 'cargarrequisitoconvenio'
                    form2 = RequisitoConvenioAspiranteForm()
                    data['filtro'] = filtro = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    data['fpago'] = request.GET['fp']
                    data['form2'] = form2
                    template = get_template("alu_requisitosmaestria/addcontratopago.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'cargaroficio':
                try:
                    data['action'] = 'cargaroficio'
                    form2 = OficioTerminacionContratoForm()
                    data['filtro'] = filtro = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    data['fpago'] = request.GET['fp']
                    data['form2'] = form2
                    template = get_template("alu_requisitosmaestria/addcontratopago.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'resetear':
                try:
                    data['title'] = u'Resetear clave del prospecto'
                    data['p'] = Persona.objects.get(pk=request.GET['id'])
                    # puede_modificar_inscripcion(request, inscripcion)
                    return render(request, "comercial/modal/resetearclave.html", data)
                except Exception as ex:
                    pass

            elif action == 'prospectoscontado':
                try:
                    data['title'] = u'Listado de prospectos de maestrías de contado'
                    request.session['viewactive'] = 10

                    url_vars = '&action=prospectoscontado'
                    aa = datetime.now().date().year
                    # asi = aa + 1

                    search = request.GET.get('s', None)
                    idc = request.GET.get('idc', '0')
                    ide = request.GET.get('ide', '0')
                    ida = request.GET.get('ida', '0')
                    idanio = request.GET.get('idanio', str(aa))
                    desde = request.GET.get('desde', '')
                    hasta = request.GET.get('hasta', '')

                    idmatricula = InscripcionCohorte.objects.filter(status=True, formapagopac__id=1, inscripcion__matricula__isnull=False).values_list('id', flat=True)

                    filtro = Q(status=True, cohortes__maestriaadmision__carrera__coordinacion__id=7, formapagopac__id=1, estado_aprobador=2, aceptado=True)

                    if search:
                        data['search'] = search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=search) |
                                                     Q(inscripcionaspirante__persona__apellido2__icontains=search) |
                                                     Q(inscripcionaspirante__persona__nombres__icontains=search) |
                                                     Q(inscripcionaspirante__persona__cedula__icontains=search))
                            url_vars += "&s={}".format(search)
                        elif len(ss) == 2:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                                     Q(inscripcionaspirante__persona__apellido2__icontains=ss[1]))
                            url_vars += "&s={}".format(ss)
                        else:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                                Q(inscripcionaspirante__persona__apellido2__icontains=ss[1]) &
                                               Q(inscripcionaspirante__persona__nombres__icontains=ss[2]))
                            url_vars += "&s={}".format(ss)


                    if int(idc):
                        filtro = filtro & (Q(cohortes__id=int(idc)))
                        data['idc'] = int(idc)
                        url_vars += f"&idc={idc}"

                    if int(ide):
                        if int(ide) == 1:
                            filtro = filtro & (Q(todosubidofi=True, tienerechazofi=False))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 3:
                            filtro = filtro & (Q(todosubidofi=False, tienerechazofi=True))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 4:
                            filtro = filtro & (Q(subirrequisitogarante=True))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 5:
                            filtro = filtro & (Q(subirrequisitogarante=False))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        else:
                            filtro = filtro & (Q(estadoformapago=int(ide)))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"

                    if int(ida):
                        if int(ida) == 1:
                            filtro = filtro & (~Q(contrato__archivocontrato__exact='')) & (Q(contrato__estado=1))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 2:
                            filtro = filtro & (Q(contrato__estado=2))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 3:
                            filtro = filtro & (Q(contrato__estado=3))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 4:
                            filtro = filtro & (Q(contrato__contratolegalizado=True))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 5:
                            filtro = filtro & (~Q(contrato__archivodescargado__exact='') & (Q(contrato__archivodescargado__isnull=False)))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 6:
                            filtro = filtro & (Q(es_becado=True))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 7:
                            idquery = CambioAdmitidoCohorteInscripcion.objects.filter(status=True).values_list('inscripcionCohorte__id', flat=True).order_by('inscripcionCohorte__id').distinct()
                            filtro = filtro & (Q(id__in=idquery))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"

                    if int(idanio):
                        if int(idanio) > 0:
                            data['idanio'] = int(idanio)
                            filtro = filtro & Q(fecha_creacion__year=int(idanio))
                            url_vars += f"&idanio={idanio}"

                    if desde and hasta:
                        data['desde'] = desde
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha_creacion__range=(desde, hasta))
                        url_vars += "&desde={}".format(desde)
                        url_vars += "&hasta={}".format(hasta)

                    elif desde:
                        data['desde'] = desde
                        filtro = filtro & Q(fecha_creacion__gte=desde)
                        url_vars += "&desde={}".format(hasta)

                    elif hasta:
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha_creacion__lte=hasta)
                        url_vars += "&hasta={}".format(hasta)

                    query = InscripcionCohorte.objects.filter(filtro).exclude(id__in=idmatricula).order_by('-fecha_creacion')
                    paging = MiPaginador(query, 20)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["listado"] = page.object_list
                    data['eCohortes'] = CohorteMaestria.objects.filter(status=True).order_by('-id').distinct()
                    data['eAnios'] = InscripcionCohorte.objects.values_list('fecha_creacion__year', flat=True).order_by('fecha_creacion__year').distinct()
                    data['eTotal'] = query.count()

                    data['eContratosPendientes'] = query.filter((~Q(contrato__archivocontrato__exact='')) & (Q(contrato__estado=1))).count()
                    data['eContratosAprobados'] = query.filter(contrato__estado=2).count()
                    data['eContratosRechazados'] = query.filter(contrato__estado=3).count()
                    return render(request, "comercial/prospectoscontado.html", data)
                except Exception as ex:
                    pass

            elif action == 'oficiosdeposgrado':
                try:
                    data['title'] = u'Listado de oficios de terminación de contrato'
                    request.session['viewactive'] = 12

                    url_vars = '&action=oficiosdeposgrado'
                    aa = datetime.now().date().year
                    # asi = aa + 1

                    search = request.GET.get('s', None)
                    idc = request.GET.get('idc', '0')
                    ide = request.GET.get('ide', '0')
                    ida = request.GET.get('ida', '0')
                    idanio = request.GET.get('idanio', '0')
                    desde = request.GET.get('desde', '')
                    hasta = request.GET.get('hasta', '')

                    filtro = Q(estado__in=[4, 5, 6])

                    if search:
                        data['search'] = search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(inscripcion__inscripcionaspirante__persona__apellido1__icontains=search) |
                                                     Q(inscripcion__inscripcionaspirante__persona__apellido2__icontains=search) |
                                                     Q(inscripcion__inscripcionaspirante__persona__nombres__icontains=search) |
                                                     Q(inscripcion__inscripcionaspirante__persona__cedula__icontains=search))
                            url_vars += "&s={}".format(search)
                        elif len(ss) == 2:
                            filtro = filtro & (Q(inscripcion__inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                                     Q(inscripcion__inscripcionaspirante__persona__apellido2__icontains=ss[1]))
                            url_vars += "&s={}".format(ss)
                        else:
                            filtro = filtro & (Q(inscripcion__inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                                Q(inscripcion__inscripcionaspirante__persona__apellido2__icontains=ss[1]) &
                                               Q(inscripcion__inscripcionaspirante__persona__nombres__icontains=ss[2]))
                            url_vars += "&s={}".format(ss)


                    if int(idc):
                        filtro = filtro & (Q(inscripcion__cohortes__id=int(idc)))
                        data['idc'] = int(idc)
                        url_vars += f"&idc={idc}"

                    if int(ide):
                        if int(ide) == 1:
                            filtro = filtro & (Q(todosubidofi=True, tienerechazofi=False))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 3:
                            filtro = filtro & (Q(todosubidofi=False, tienerechazofi=True))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 4:
                            filtro = filtro & (Q(subirrequisitogarante=True))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 5:
                            filtro = filtro & (Q(subirrequisitogarante=False))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        else:
                            filtro = filtro & (Q(estadoformapago=int(ide)))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"

                    if int(idanio):
                        if int(idanio) > 0:
                            data['idanio'] = int(idanio)
                            filtro = filtro & Q(fecha_creacion__year=int(idanio))
                            url_vars += f"&idanio={idanio}"

                    if desde and hasta:
                        data['desde'] = desde
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha_creacion__range=(desde, hasta))
                        url_vars += "&desde={}".format(desde)
                        url_vars += "&hasta={}".format(hasta)

                    elif desde:
                        data['desde'] = desde
                        filtro = filtro & Q(fecha_creacion__gte=desde)
                        url_vars += "&desde={}".format(hasta)

                    elif hasta:
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha_creacion__lte=hasta)
                        url_vars += "&hasta={}".format(hasta)

                    if int(ida):
                        if int(ida) == 1:
                            filtro = filtro & (Q(estado=4))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 2:
                            lis = []
                            listcontratos = Contrato.objects.filter(filtro).order_by('-fechacontrato', '-contratolegalizado')
                            for contra in listcontratos:
                                if contra.ultima_evidenciaoficio().estado_aprobacion == 2:
                                    lis.append(contra.id)

                            filtro = filtro & Q(id__in=lis)
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 3:
                            lis = []
                            listcontratos = Contrato.objects.filter(filtro).order_by('-fechacontrato', '-contratolegalizado')
                            for contra in listcontratos:
                                if contra.ultima_evidenciaoficio().estado_aprobacion == 3:
                                    lis.append(contra.id)

                            filtro = filtro & Q(id__in=lis)
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"

                    query = Contrato.objects.filter(filtro).order_by('-fecha_creacion')
                    paging = MiPaginador(query, 20)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["listado"] = page.object_list
                    data['eCohortes'] = CohorteMaestria.objects.filter(status=True).order_by('-id').distinct()
                    data['eAnios'] = InscripcionCohorte.objects.values_list('fecha_creacion__year', flat=True).order_by('fecha_creacion__year').distinct()
                    data['eTotal'] = query.count()
                    data['eContratosPendientes'] = query.filter(estado=4).count()
                    data['eContratosAprobados'] = query.filter(estado=5).count()
                    data['eContratosRechazados'] = query.filter(estado=6).count()
                    return render(request, "comercial/listaoficios.html", data)
                except Exception as ex:
                    pass

            elif action == 'leadsmatriculados':
                try:
                    data['title'] = u'Listado de matriculados'
                    request.session['viewactive'] = 11

                    url_vars = '&action=leadsmatriculados'
                    aa = datetime.now().date().year
                    # asi = aa + 1

                    search = request.GET.get('s', None)
                    idc = request.GET.get('idc', '0')
                    ide = request.GET.get('ide', '0')
                    ida = request.GET.get('ida', '0')
                    idanio = request.GET.get('idanio', str(aa))
                    desde = request.GET.get('desde', '')
                    hasta = request.GET.get('hasta', '')

                    filtro = Q(status=True, estado_aprobador=2, cohortes__maestriaadmision__carrera__coordinacion__id=7, inscripcion__matricula__isnull=False, aceptado=True)

                    if search:
                        data['search'] = search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=search) |
                                                     Q(inscripcionaspirante__persona__apellido2__icontains=search) |
                                                     Q(inscripcionaspirante__persona__nombres__icontains=search) |
                                                     Q(inscripcionaspirante__persona__cedula__icontains=search))
                            url_vars += "&s={}".format(search)
                        elif len(ss) == 2:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                                     Q(inscripcionaspirante__persona__apellido2__icontains=ss[1]))
                            url_vars += "&s={}".format(ss)
                        else:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                                Q(inscripcionaspirante__persona__apellido2__icontains=ss[1]) &
                                               Q(inscripcionaspirante__persona__nombres__icontains=ss[2]))
                            url_vars += "&s={}".format(ss)


                    if int(idc):
                        filtro = filtro & (Q(cohortes__id=int(idc)))
                        data['idc'] = int(idc)
                        url_vars += f"&idc={idc}"

                    if int(ide):
                        if int(ide) == 1:
                            filtro = filtro & (Q(formapagopac__id=1))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 2:
                            filtro = filtro & (Q(formapagopac__id=2))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 3:
                            filtro = filtro & (Q(es_becado=True))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 4:
                            idquery = CambioAdmitidoCohorteInscripcion.objects.filter(status=True).values_list('inscripcionCohorte__id', flat=True).order_by('inscripcionCohorte__id').distinct()
                            filtro = filtro & (Q(id__in=idquery))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"

                    if int(ida):
                        if int(ida) == 1:
                            filtro = filtro & (~Q(contrato__archivocontrato__exact='')) & (Q(contrato__estado=1))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 2:
                            filtro = filtro & (Q(contrato__estado=2))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 3:
                            filtro = filtro & (Q(contrato__estado=3))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 4:
                            filtro = filtro & (Q(contrato__contratolegalizado=True))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 5:
                            filtro = filtro & (~Q(contrato__archivopagare__exact='')) & (Q(contrato__estadopagare=1))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 6:
                            filtro = filtro & (Q(contrato__estadopagare=2))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 7:
                            filtro = filtro & (Q(contrato__estadopagare=3))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 8:
                            filtro = filtro & (Q(subirrequisitogarante=True))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 9:
                            filtro = filtro & (Q(subirrequisitogarante=False))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"

                    if int(idanio):
                        if int(idanio) > 0:
                            data['idanio'] = int(idanio)
                            filtro = filtro & Q(fecha_creacion__year=int(idanio))
                            url_vars += f"&idanio={idanio}"

                    if desde and hasta:
                        data['desde'] = desde
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha_creacion__date__range=(desde, hasta))
                        url_vars += "&desde={}".format(desde)
                        url_vars += "&hasta={}".format(hasta)

                    elif desde:
                        data['desde'] = desde
                        filtro = filtro & Q(fecha_creacion__date__gte=desde)
                        url_vars += "&desde={}".format(hasta)

                    elif hasta:
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha_creacion__date__lte=hasta)
                        url_vars += "&hasta={}".format(hasta)

                    query = InscripcionCohorte.objects.filter(filtro).order_by('-fecha_creacion')
                    paging = MiPaginador(query, 20)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["listado"] = page.object_list
                    data['eCohortes'] = CohorteMaestria.objects.filter(status=True).order_by('-id').distinct()
                    data['eAnios'] = InscripcionCohorte.objects.values_list('fecha_creacion__year', flat=True).order_by('fecha_creacion__year').distinct()
                    data['eTotal'] = query.count()

                    data['eContratosPendientes'] = query.filter((~Q(contrato__archivocontrato__exact='')) & (Q(contrato__estado=1))).count()
                    data['eContratosAprobados'] = query.filter(contrato__estado=2).count()
                    data['eContratosRechazados'] = query.filter(contrato__estado=3).count()

                    data['ePagaresPendientes'] = query.filter((~Q(contrato__archivopagare__exact='')) & (Q(contrato__estadopagare=1))).count()
                    data['ePagaresAprobados'] = query.filter(contrato__estadopagare=2).count()
                    data['ePagaresRechazados'] = query.filter(contrato__estadopagare=3).count()
                    return render(request, "comercial/viewleadsmatriculados.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadorequisitosinscripcion':
                try:
                    from posgrado.models import EvidenciaRequisitoConvenio
                    data['title'] = u'Admisión en programas de maestría'
                    vt = False
                    vexpe = False
                    tienepagoexamen = False
                    ventanaactiva = 1
                    bloqueasubidapago = 1
                    tienerequisitos = False
                    integranteexamen = integranteentrevista = garante = contrato = None
                    data['uno'] = 1
                    data['dos'] = 2
                    data['tres'] = 3
                    data['cuatro'] = 4
                    data['cinco'] = 5
                    data['seis'] = 6
                    data['siete'] = 7
                    data['ocho'] = 8
                    data['nueve'] = 9

                    data['sign'] = request.GET['sign']
                    data['inscripcioncohorte'] = inscripcioncohorte = InscripcionCohorte.objects.get(pk=int(encrypt(request.GET['idinscripcioncohorte'])))
                    data['idpersona'] = inscripcioncohorte.inscripcionaspirante.persona.id
                    data['titulaciones'] = Titulacion.objects.filter(status=True, persona=inscripcioncohorte.inscripcionaspirante.persona, titulo__nivel__id__in=[3,4], educacionsuperior=True)
                    if 'idc' in request.GET:
                        data['idc'] = request.GET['idc']
                    if 'ide' in request.GET:
                        data['ide'] = request.GET['ide']
                    if 'ida' in request.GET:
                        data['ida'] = request.GET['ida']
                    if 'desde' in request.GET:
                        data['desde'] = request.GET['desde']
                    if 'hasta' in request.GET:
                        data['hasta'] = request.GET['hasta']
                    data['canales'] = CanalInformacionMaestria.objects.filter(status=True)
                    if str(inscripcioncohorte.id) not in variable_valor('INSCRIPCIONES_NOVALIDA_PERFILINGRESO'):
                        if inscripcioncohorte.cohortes.maestriaadmision.carrera.programapac_set.last() and inscripcioncohorte.cohortes.maestriaadmision.carrera.programapac_set.last().funcionsustantivadocenciapac_set.last() and inscripcioncohorte.cohortes.maestriaadmision.carrera.programapac_set.last().funcionsustantivadocenciapac_set.last().detalleperfilingreso_set.last():
                            data['perfilingreso'] = perfilingreso = inscripcioncohorte.cohortes.maestriaadmision.carrera.programapac_set.last().funcionsustantivadocenciapac_set.last().detalleperfilingreso_set.last()
                            data['idperfilingreso'] = perfilingreso.id
                            if perfilingreso.experiencia > 0: #si el perfil cuenta con experiencia
                                data['validarexperiencia'] = vexpe = True
                                data['experiencia'] = perfilingreso.cantidadexperiencia
                            else:
                                data['validarexperiencia'] = vexpe = False

                            campotitulos = CamposTitulosPostulacion.objects.filter(status=True, titulo__in=perfilingreso.titulo.all()).distinct()
                            data['campotitulos'] = campotitulos

                            if campotitulos:
                                data['validartitulo'] = vt = True
                            else:
                                data['validartitulo'] = vt = False

                    inscripciondescuento = None
                    tienerequisitosbecas = False
                    registrocomprobantepago = None
                    registroanticipo = None

                    if inscripcioncohorte.evidenciarequisitosaspirante_set.filter(status=True).exists():
                        tienerequisitos = True
                    data['tienerequisitos'] = tienerequisitos

                    tienerequisitosfi = False
                    if inscripcioncohorte.evidenciarequisitosaspirante_set.filter(status=True, requisitos__requisito__claserequisito__clasificacion__id=3).exists():
                        tienerequisitosfi = True
                    data['tienerequisitosfi'] = tienerequisitosfi

                    if inscripcioncohorte.cohortes.tienecostoexamen:
                        if inscripcioncohorte.evidenciapagoexamen_set.filter(status=True):
                            tienepagoexamen = True
                            data['pagoexamen'] = evidpagoexamen = inscripcioncohorte.evidenciapagoexamen_set.filter(status=True)[0]
                            if evidpagoexamen.estadorevision == 2:
                                bloqueasubidapago = 2
                    data['bloqueasubidapago'] = bloqueasubidapago
                    data['tienepagoexamen'] = tienepagoexamen
                    permisorequisito = False
                    if hoy >= inscripcioncohorte.cohortes.fechainiciorequisito and hoy <= inscripcioncohorte.cohortes.fechafinrequisito:
                        permisorequisito = True
                    data['permisorequisito'] = permisorequisito
                    if InscripcionCohorte.objects.filter(pk=int(encrypt(request.GET['idinscripcioncohorte'])), grupo__isnull=True):
                        requisitosexcluir = ClaseRequisito.objects.values_list('requisito__id').filter(clasificacion=3, status=True)
                        data['requisitos'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, status=True).exclude(requisito__in=requisitosexcluir).order_by("id")
                    else:
                        gruporequisitos = RequisitosGrupoCohorte.objects.values_list('requisito_id', flat=True).filter(grupo=inscripcioncohorte.grupo, status=True)
                        data['requisitos'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, requisito_id__in=gruporequisitos, status=True).order_by("id")
                    if inscripcioncohorte.integrantegrupoexamenmsc_set.filter(grupoexamen__estado_emailentrevista=2, status=True, inscripcion__status=True).exists():
                        data['integranteexamen'] = integranteexamen = inscripcioncohorte.integrantegrupoexamenmsc_set.get(grupoexamen__estado_emailentrevista=2, status=True)
                    if inscripcioncohorte.integrantegrupoentrevitamsc_set.filter(grupoentrevista__estado_emailentrevista=2, status=True, inscripcion__status=True).exists():
                        data['integranteentrevista'] = integranteentrevista = inscripcioncohorte.integrantegrupoentrevitamsc_set.get(grupoentrevista__estado_emailentrevista=2, status=True)

                    #SI CUMPLE CON LA CONDICIÓN SELECIONA LA PESTAÑA A VIZUALIZAR financiamiento formapagopac_id == 2
                    permisorequisitocomercia = False
                    data['fechafincomercializacion'] = fechafincomercializacion = inscripcioncohorte.cohortes.fechafininsp + timedelta(days=30)
                    if fechafincomercializacion >= hoy:
                        permisorequisitocomercia = True
                    data['permisorequisitocomercia'] = permisorequisitocomercia

                    if inscripcioncohorte.formapagopac:
                        if inscripcioncohorte.formapagopac_id == 2:
                            if inscripcioncohorte.subirrequisitogarante:
                                data['requisitoscomercializacion'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, status=True, requisito__claserequisito__clasificacion__id=3).exclude(requisito__id__in=[56, 57, 59]).order_by("requisito__tipopersona__id")
                            else:
                                data['requisitoscomercializacion'] = RequisitosMaestria.objects.filter(cohorte=inscripcioncohorte.cohortes, status=True, requisito__tipopersona__id=1, requisito__claserequisito__clasificacion__id=3).order_by("id")

                    formapago = 1
                    if inscripcioncohorte.formapagopac:
                        formapago = inscripcioncohorte.formapagopac.id
                    if TipoFormaPagoPac.objects.filter(pk=formapago).exists():
                        data['fpago'] = fpago = TipoFormaPagoPac.objects.filter(pk=formapago).last()
                        data['contrato'] = contrato = Contrato.objects.filter(status=True, inscripcion=inscripcioncohorte, inscripcion__status=True).last()
                    if formapago == 2:
                        data['garante'] = garante = inscripcioncohorte.garantepagomaestria_set.filter(status=True).last()
                    if inscripcioncohorte.integrantegrupoentrevitamsc_set.filter(estado_emailadmitido=2, cohorteadmitidasinproceso__isnull=True, status=True).exists():
                        data['aspiranteadmitido'] = inscripcioncohorte.integrantegrupoentrevitamsc_set.get(estado_emailadmitido=2, cohorteadmitidasinproceso__isnull=True, status=True)
                        data['otracohorte'] = 0
                    if inscripcioncohorte.integrantegrupoentrevitamsc_set.filter(cohorteadmitidasinproceso__isnull=False, status=True, inscripcion__status=True).exists():
                        data['aspiranteadmitido'] = inscripcioncohorte.integrantegrupoentrevitamsc_set.get(cohorteadmitidasinproceso__isnull=False, status=True)
                        data['otracohorte'] = 1
                    if inscripcioncohorte.evidenciarequisitoconvenio_set.filter(status=True, convenio = inscripcioncohorte.convenio).exists():
                        data['requisitoconvenio'] = inscripcioncohorte.evidenciarequisitoconvenio_set.get(status=True, convenio = inscripcioncohorte.convenio)

                    # else:
                    if vexpe or vt:
                        ventanaactiva = 1
                        data['fase1'] = True
                        if inscripcioncohorte.cohortes.tipo == 1:
                            if inscripcioncohorte.tiulacionaspirante:
                                ventanaactiva = 2
                                data['fase2'] = True
                                if inscripcioncohorte.estado_aprobador == 2:
                                    ventanaactiva = 4
                                    data['fase4'] = True
                                    if integranteexamen and integranteexamen.estado == 2:
                                        ventanaactiva = 5
                                        data['fase5'] = True
                                        if integranteentrevista and integranteentrevista.estado == 2:
                                            ventanaactiva = 8
                                            data['fase8'] = True
                                            if inscripcioncohorte.formapagopac.id == 2:
                                                if inscripcioncohorte.aceptado:
                                                    ventanaactiva = 3
                                                    data['fase3'] = True
                                                    if inscripcioncohorte.subirrequisitogarante:
                                                        if garante and inscripcioncohorte.estadoformapago == 2 and inscripcioncohorte.Configfinanciamientocohorte:
                                                            ventanaactiva = 6
                                                            data['fase6'] = True
                                                            if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and contrato.ultima_evidenciapagare() and contrato.ultima_evidenciapagare().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                                                ventanaactiva = 9
                                                                data['fase9'] = True
                                                            if inscripcioncohorte.completo_datos_matrices() == '0':
                                                                ventanaactiva = 7
                                                                data['fase7'] = True
                                                    else:
                                                        if inscripcioncohorte.estadoformapago == 2 and inscripcioncohorte.Configfinanciamientocohorte:
                                                            ventanaactiva = 6
                                                            data['fase6'] = True
                                                            if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and contrato.ultima_evidenciapagare() and contrato.ultima_evidenciapagare().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                                                ventanaactiva = 9
                                                                data['fase9'] = True
                                                            if inscripcioncohorte.completo_datos_matrices() == '0':
                                                                ventanaactiva = 7
                                                                data['fase7'] = True
                                            else:
                                                if inscripcioncohorte.aceptado:
                                                    ventanaactiva = 6
                                                    data['fase6'] = True
                                                    if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                                        ventanaactiva = 9
                                                        data['fase9'] = True
                                                    if inscripcioncohorte.completo_datos_matrices() == '0':
                                                        ventanaactiva = 7
                                                        data['fase7'] = True

                        elif inscripcioncohorte.cohortes.tipo == 2:
                            if inscripcioncohorte.tiulacionaspirante:
                                ventanaactiva = 2
                                data['fase2'] = True
                                if inscripcioncohorte.estado_aprobador == 2:
                                    ventanaactiva = 4
                                    data['fase4'] = True
                                    if integranteexamen and integranteexamen.estado == 2:
                                        ventanaactiva = 8
                                        data['fase8'] = True
                                        if inscripcioncohorte.formapagopac.id == 2:
                                            if inscripcioncohorte.aceptado:
                                                ventanaactiva = 3
                                                data['fase3'] = True
                                                if inscripcioncohorte.subirrequisitogarante:
                                                    if garante and inscripcioncohorte.estadoformapago == 2 and inscripcioncohorte.Configfinanciamientocohorte:
                                                        ventanaactiva = 6
                                                        data['fase6'] = True
                                                        if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and contrato.ultima_evidenciapagare() and contrato.ultima_evidenciapagare().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                                            ventanaactiva = 9
                                                            data['fase9'] = True
                                                        if inscripcioncohorte.completo_datos_matrices() == '0':
                                                            ventanaactiva = 7
                                                            data['fase7'] = True
                                                else:
                                                    if inscripcioncohorte.estadoformapago == 2 and inscripcioncohorte.Configfinanciamientocohorte:
                                                        ventanaactiva = 6
                                                        data['fase6'] = True
                                                        if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and contrato.ultima_evidenciapagare() and contrato.ultima_evidenciapagare().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                                            ventanaactiva = 9
                                                            data['fase9'] = True
                                                        if inscripcioncohorte.completo_datos_matrices() == '0':
                                                            ventanaactiva = 7
                                                            data['fase7'] = True
                                        else:
                                            if inscripcioncohorte.aceptado:
                                                ventanaactiva = 6
                                                data['fase6'] = True
                                                if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                                    ventanaactiva = 9
                                                    data['fase9'] = True
                                                if inscripcioncohorte.completo_datos_matrices() == '0':
                                                    ventanaactiva = 7
                                                    data['fase7'] = True
                        else:
                            if inscripcioncohorte.tiulacionaspirante:
                                ventanaactiva = 2
                                data['fase2'] = True
                                if inscripcioncohorte.estado_aprobador == 2:
                                    ventanaactiva = 8
                                    data['fase8'] = True
                                    if inscripcioncohorte.formapagopac.id == 2:
                                        if inscripcioncohorte.aceptado:
                                            ventanaactiva = 3
                                            data['fase3'] = True
                                            if inscripcioncohorte.subirrequisitogarante:
                                                if garante and inscripcioncohorte.estadoformapago == 2 and inscripcioncohorte.Configfinanciamientocohorte:
                                                    ventanaactiva = 6
                                                    data['fase6'] = True
                                                    if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and contrato.ultima_evidenciapagare() and contrato.ultima_evidenciapagare().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                                        ventanaactiva = 9
                                                        data['fase9'] = True
                                                    if inscripcioncohorte.completo_datos_matrices() == '0':
                                                        ventanaactiva = 7
                                                        data['fase7'] = True
                                            else:
                                                if inscripcioncohorte.estadoformapago == 2 and inscripcioncohorte.Configfinanciamientocohorte:
                                                    ventanaactiva = 6
                                                    data['fase6'] = True
                                                    if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and contrato.ultima_evidenciapagare() and contrato.ultima_evidenciapagare().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                                        ventanaactiva = 9
                                                        data['fase9'] = True
                                                    if inscripcioncohorte.completo_datos_matrices() == '0':
                                                        ventanaactiva = 7
                                                        data['fase7'] = True
                                    else:
                                        if inscripcioncohorte.aceptado:
                                            ventanaactiva = 6
                                            data['fase6'] = True
                                            if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                                ventanaactiva = 9
                                                data['fase9'] = True
                                            if inscripcioncohorte.completo_datos_matrices() == '0':
                                                ventanaactiva = 7
                                                data['fase7'] = True
                    else:
                        ventanaactiva = 2
                        data['fase2'] = True
                        if inscripcioncohorte.estado_aprobador == 2:
                            ventanaactiva = 8
                            data['fase8'] = True
                            if inscripcioncohorte.formapagopac.id == 2:
                                if inscripcioncohorte.aceptado:
                                    ventanaactiva = 3
                                    data['fase3'] = True
                                    if inscripcioncohorte.subirrequisitogarante:
                                        if garante and inscripcioncohorte.estadoformapago == 2 and inscripcioncohorte.Configfinanciamientocohorte:
                                            ventanaactiva = 6
                                            data['fase6'] = True
                                            if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and contrato.ultima_evidenciapagare() and contrato.ultima_evidenciapagare().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                                ventanaactiva = 9
                                                data['fase9'] = True
                                            if inscripcioncohorte.completo_datos_matrices() == '0':
                                                ventanaactiva = 7
                                                data['fase7'] = True
                                    else:
                                        if inscripcioncohorte.estadoformapago == 2 and inscripcioncohorte.Configfinanciamientocohorte:
                                            ventanaactiva = 6
                                            data['fase6'] = True
                                            if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and contrato.ultima_evidenciapagare() and contrato.ultima_evidenciapagare().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                                ventanaactiva = 9
                                                data['fase9'] = True
                                            if inscripcioncohorte.completo_datos_matrices() == '0':
                                                ventanaactiva = 7
                                                data['fase7'] = True
                            else:
                                if inscripcioncohorte.aceptado:
                                    ventanaactiva = 6
                                    data['fase6'] = True
                                    if contrato and contrato.ultima_evidencia() and contrato.ultima_evidencia().estado_aprobacion == 2 and inscripcioncohorte.rubro_generado_ins() and inscripcioncohorte.tipocobro != 1:
                                        ventanaactiva = 9
                                        data['fase9'] = True
                                    if inscripcioncohorte.completo_datos_matrices() == '0':
                                        ventanaactiva = 7
                                        data['fase7'] = True
                    next = 0
                    if 'next' in request.GET:
                        next = request.GET['next']
                        if next:
                            ventanaactiva = int(encrypt(next))
                    data['ventanaactiva'] = ventanaactiva
                    return render(request, "comercial/listadorequisitosasesor.html", data)
                except Exception as ex:
                    pass

            elif action == 'addarchivorequi':
                try:
                    form2 = EvidenciaRequisitoAdmisionForm()
                    data['action'] = 'addarchivorequi'
                    data['filtro'] = filtro = RequisitosMaestria.objects.get(pk=int(request.GET['id']))
                    data['idrequisito'] = request.GET['id']
                    data['idins'] = request.GET['idins']
                    data['form2'] = form2
                    template = get_template("comercial/modal/add_requisitomaestria.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'cargarcontratopagoase':
                try:
                    # data['title'] = u'Contrato de pago'
                    data['action'] = 'cargarcontratopagoase'
                    form2 = ContratoPagoMaestriaForm()
                    data['filtro'] = filtro = InscripcionCohorte.objects.get(pk=int(request.GET['id']))
                    data['fpago'] = request.GET['fp']
                    data['form2'] = form2
                    template = get_template("alu_requisitosmaestria/addcontratopago.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'validarperfil':
                try:
                    experi = None
                    data['title'] = u'Asignar horario de retiro'
                    data['action'] = request.GET['action']
                    data['id'] = id = int(request.GET['id'])
                    data['uno'] = 1
                    data['insc'] = InscripcionCohorte.objects.get(status=True, pk=int(request.GET['insc']))
                    data['idperfilingreso'] = int(request.GET['idperfilingreso'])
                    # data['idperfilingreso'] = DetallePerfilIngreso.objects.get(status=True, pk=int(request.GET['idperfilingreso']))
                    if request.GET['experiencia'] == '':
                        experi = float(0)
                    else:
                        experi = float(request.GET['experiencia'])
                    data['experiencia'] = experi
                    data['validarexperiencia'] = expe = request.GET['vexpe']
                    data['validartitulo'] = titu = request.GET['vtitulo']

                    titulacion = Titulacion.objects.get(status=True, pk=id)
                    form = ValidarPerfilAdmisionForm(initial={'titulo': titulacion.titulo,
                                                              'postulante': titulacion.persona.nombre_completo_inverso()})

                    if expe == 'False':
                        form.sin_cantidad()
                    if titu == 'False':
                        form.sin_titulo()

                    data['form'] = form
                    data['urlaction'] = '/comercial'
                    template = get_template("alu_requisitosmaestria/validarpefil.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'verfacturas':
                try:
                    id= int(request.GET['id'])
                    data['filtro'] = filtro = Rubro.objects.get(pk=int(id))
                    data['listado_facturas'] = filtro.pago_set.filter(status=True).order_by('-pk')
                    template=get_template('alu_requisitosmaestria/verfacturas.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'cargararchivoimagen':
                try:
                    data['title'] = u'Evidencias de requisitos de maestría'
                    data['id'] = request.GET['id']
                    data['inscripcioncohorte'] = InscripcionCohorte.objects.get(status=True, pk=int(request.GET['id']))
                    if 'fp' in request.GET:
                        data['fpago'] = request.GET['fp']
                    data['idevidencia'] = request.GET['idevidencia']
                    requisito = RequisitosMaestria.objects.get(pk=int(request.GET['idevidencia']), status=True)
                    form = RequisitosMaestriaImgForm()
                    data['form'] = form
                    template = get_template("comercial/modal/add_requisitomaestriaimagen.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, "nombre": "SUBIR DOCUMENTO DE REQUISITO " + str(requisito.requisito.nombre)})
                except Exception as ex:
                    pass

            elif action == 'addgarantepagomaestria':
                try:
                    data['action'] = 'addgarantepagomaestria'
                    data['id'] = request.GET['idins']
                    insc = InscripcionCohorte.objects.get(pk=request.GET['idins'])
                    form = GarantePagoMaestriaForm()
                    data['form'] = form
                    template = get_template("comercial/modal/addgarantepagomaestria.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content, "nombre": "REGISTRAR GARANTE"})
                except Exception as ex:
                    pass

            elif action == 'postdesactivadas':
                try:
                    data['title'] = u'Listado de postulaciones de maestrías desactivadas'
                    filtro = Q(status=False, cohortes__maestriaadmision__carrera__coordinacion__id=7)

                    search = None
                    url_vars = f"&action=" + action
                    if 'search' in request.GET:
                        search = request.GET['search']
                    if search:
                        data['search'] = search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=search) |
                                               Q(inscripcionaspirante__persona__apellido2__icontains=search) |
                                               Q(inscripcionaspirante__persona__nombres__icontains=search) |
                                               Q(inscripcionaspirante__persona__cedula__icontains=search))

                            url_vars += "&s={}".format(search)
                        elif len(ss) == 2:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                               Q(inscripcionaspirante__persona__apellido2__icontains=ss[1]))

                            url_vars += "&s={}".format(ss)
                        else:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                               Q(inscripcionaspirante__persona__apellido2__icontains=ss[1]) &
                                               Q(inscripcionaspirante__persona__nombres__icontains=ss[2]))

                            url_vars += "&s={}".format(ss)

                    leads = InscripcionCohorte.objects.filter(filtro).order_by('-fecha_creacion')

                    paging = MiPaginador(leads, 25)
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
                    data['action'] = action
                    data['paging'] = paging
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listadoleads'] = page.object_list
                    data['search'] = search if search else ""
                    data['url_vars'] = url_vars
                    data['totalleads'] = leads.count()

                    return render(request, "comercial/postdesactivadas.html", data)
                except Exception as ex:
                    pass

            elif action == 'verifyrequirments':
                try:
                    id = request.GET['id']
                    filtro = InscripcionCohorte.objects.get(id=int(id))

                    if filtro.contrato_posgrado():
                        contrato = filtro.contrato_posgrado().ultima_evidencia()
                        pagare = filtro.contrato_posgrado().ultima_evidenciapagare()
                        if not contrato:
                            return JsonResponse({'result': False, 'mensaje': "Para realizar esta acción, debe tener el contrato generado!"})
                        if not pagare:
                            return JsonResponse({'result': False, 'mensaje': "Para realizar esta acción, debe tener el pagaré generado!"})
                        # if contrato.estado_aprobacion != 2:
                        #     return JsonResponse({'result':False,'mensaje':"Para realizar esta acción, el contrato debe estar aprobado!"})
                        # if pagare.estado_aprobacion !=2:
                        #     return JsonResponse({'result':False,'mensaje':"Para realizar esta acción, el pagaré debe estar aprobado!"})
                        res_js = {'result':True}
                    else:
                        res_js = {'result':False,'mensaje':"No tiene contrato generado.!"}
                except Exception as ex:
                    lineerr = sys.exc_info()[-1].tb_lineno
                    err_ = f"Ocurrio un error. Detalle: {ex.__str__()}\nError en la linea {lineerr}"
                    res_js = {'result':False,'mensaje':err_}
                return JsonResponse(res_js)

            elif action == 'vercanalesinformacion':
                try:
                    request.session['viewactive'] = 19
                    data['title'] = u'Canales de información'
                    filtros = Q(status=True)
                    s = request.GET.get('s', '')
                    idt = request.GET.get('idt', '0')
                    url_vars = '&action=vercanalesinformacion'

                    if s:
                        filtros = filtros & (Q(descripcion__icontains=s))
                        data['s'] = f"{s}"
                        url_vars += f"&s={s}"

                    if int(idt):
                        if int(idt) == 1:
                            filtros = filtros & (Q(valido_form=True))
                            data['idt'] = f"{idt}"
                            url_vars += f"&idt={idt}"
                        elif int(idt) == 2:
                            filtros = filtros & (Q(valido_form=False))
                            data['idt'] = f"{idt}"
                            url_vars += f"&idt={idt}"

                    eCanales = CanalInformacionMaestria.objects.filter(filtros).order_by('-id')
                    paging = MiPaginador(eCanales, 25)
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
                    data['eCanales'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, "comercial/canalesinfo.html", data)
                except Exception as ex:
                    pass

            elif action == 'verconvenios':
                try:
                    from posgrado.models import Convenio
                    request.session['viewactive'] = 20
                    data['title'] = u'Convenios de Posgrado'
                    filtros = Q(status=True)
                    s = request.GET.get('s', '')
                    idt = request.GET.get('idt', '0')
                    url_vars = '&action=verconvenios'

                    if s:
                        filtros = filtros & (Q(descripcion__icontains=s))
                        data['s'] = f"{s}"
                        url_vars += f"&s={s}"

                    if int(idt):
                        if int(idt) == 1:
                            filtros = filtros & (Q(valido_form=True))
                            data['idt'] = f"{idt}"
                            url_vars += f"&idt={idt}"
                        elif int(idt) == 2:
                            filtros = filtros & (Q(valido_form=False))
                            data['idt'] = f"{idt}"
                            url_vars += f"&idt={idt}"

                    eConvenios = Convenio.objects.filter(filtros).order_by('-id')
                    paging = MiPaginador(eConvenios, 25)
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
                    data['eConvenios'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, "comercial/convenios.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcanal':
                try:
                    data['title'] = u'Adicionar canal de información'
                    data['action'] = request.GET['action']
                    form = CanalInformacionForm()
                    data['form2'] = form
                    template = get_template("comercial/modal/editcanal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'addconvenio':
                try:
                    from posgrado.forms import ConvenioForm
                    data['title'] = u'Adicionar convenio de posgrado'
                    data['action'] = request.GET['action']
                    form = ConvenioForm()
                    data['form2'] = form
                    template = get_template("comercial/modal/editconvenio.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'editcanal':
                try:
                    data['title'] = u'Editar canal de información'
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = CanalInformacionMaestria.objects.get(status=True, pk=int(request.GET['id']))
                    data['action'] = request.GET['action']
                    form = CanalInformacionForm(initial={'canal':filtro.descripcion,
                                                        'valido':filtro.valido_form})
                    data['form2'] = form
                    template = get_template('comercial/modal/editcanal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'editconvenio':
                try:
                    from posgrado.forms import ConvenioForm
                    from posgrado.models import Convenio
                    data['title'] = u'Editar convenio de posgrado'
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = Convenio.objects.get(status=True, pk=int(request.GET['id']))
                    data['action'] = request.GET['action']
                    form = ConvenioForm(initial={'descripcion':filtro.descripcion,
                                                 'fechaInicio':filtro.fechaInicio,
                                                 'valido':filtro.valido_form,
                                                 'aplicadescuento':filtro.aplicadescuento,
                                                 'porcentajedescuento':filtro.porcentajedescuento,
                                                 'suberequisito':filtro.suberequisito,
                                                 'descripcionrequisito':filtro.descripcionrequisito})
                    data['form2'] = form
                    template = get_template('comercial/modal/editconvenio.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'adddatospersonales':
                try:
                    data['title'] = u'Actualizar datos personales'
                    ins = InscripcionCohorte.objects.get(pk=int(request.GET['idp']))
                    form = DatosPersonalesMaestranteForm(initial={'paisori': ins.inscripcionaspirante.persona.paisnacimiento,
                                                                  'provinciaori': ins.inscripcionaspirante.persona.provincianacimiento,
                                                                  'cantonori': ins.inscripcionaspirante.persona.cantonnacimiento,
                                                                  'paisresi': ins.inscripcionaspirante.persona.pais if ins.inscripcionaspirante.persona.pais else '',
                                                                  'provinciaresi': ins.inscripcionaspirante.persona.provincia if ins.inscripcionaspirante.persona.provincia else '',
                                                                  'cantonresi': ins.inscripcionaspirante.persona.canton if ins.inscripcionaspirante.persona.canton else '',
                                                                  'tienediscapacidad': ins.inscripcionaspirante.persona.mi_perfil().tienediscapacidad if ins.inscripcionaspirante.persona.mi_perfil().tienediscapacidad else False,
                                                                  'tipodiscapacidad': ins.inscripcionaspirante.persona.mi_perfil().tipodiscapacidad if ins.inscripcionaspirante.persona.mi_perfil().tipodiscapacidad else '',
                                                                  'porcientodiscapacidad': ins.inscripcionaspirante.persona.mi_perfil().porcientodiscapacidad if ins.inscripcionaspirante.persona.mi_perfil().porcientodiscapacidad else 0,
                                                                  'carnetdiscapacidad': ins.inscripcionaspirante.persona.mi_perfil().carnetdiscapacidad if ins.inscripcionaspirante.persona.mi_perfil().carnetdiscapacidad else '',
                                                                  'archivo': ins.inscripcionaspirante.persona.mi_perfil().archivo if ins.inscripcionaspirante.persona.mi_perfil().archivo else '',
                                                                  'raza': ins.inscripcionaspirante.persona.mi_perfil().raza if ins.inscripcionaspirante.persona.mi_perfil().raza else '',
                                                                  'nacionalidadindigena': ins.inscripcionaspirante.persona.mi_perfil().nacionalidadindigena if ins.inscripcionaspirante.persona.mi_perfil().nacionalidadindigena else '',
                                                                  'lgtbi': ins.inscripcionaspirante.persona.lgtbi})
                    visible_fields = form.visible_fields()
                    total_fields = len(visible_fields)
                    lista = [(1, 'Ubicación demográfica', visible_fields[0:6]),
                             (2, 'Discapacidad', visible_fields[6:11]),
                             (3, 'Etnia/Raza', visible_fields[11:total_fields])
                             ]
                    data['form'] = lista
                    data['switchery'] = True
                    data['clavebi'] = 'foreign'
                    data['action'] = 'adddatospersonales'
                    data['idins'] = ins.id
                    template = get_template('alu_requisitosmaestria/formdatospersonales.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            return HttpResponseRedirect(request.path)
        else:
            try:
                if persona.es_asesor():
                    request.session['viewactive'] = 1
                    data['title'] = u'Leads asignados'
                    url_vars = ''
                    aa = datetime.now().date().year
                    # asi = aa + 1

                    search = request.GET.get('s', None)
                    idc = request.GET.get('idc', '0')
                    ide = request.GET.get('ide', '0')
                    ida = request.GET.get('ida', '0')
                    idanio = request.GET.get('idanio', str(aa))
                    desde = request.GET.get('desde', '')
                    hasta = request.GET.get('hasta', '')


                    idventas = VentasProgramaMaestria.objects.filter(status=True, valida=True, asesor__persona=persona).values_list('inscripcioncohorte__id', flat=True)
                    filtro = Q(status=True, cohortes__maestriaadmision__carrera__coordinacion__id=7, asesor__persona=persona)

                    if search:
                        data['search'] = search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=search) |
                                                     Q(inscripcionaspirante__persona__apellido2__icontains=search) |
                                                     Q(inscripcionaspirante__persona__nombres__icontains=search) |
                                                     Q(inscripcionaspirante__persona__cedula__icontains=search))
                            url_vars += "&s={}".format(search)
                        elif len(ss) == 2:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                                     Q(inscripcionaspirante__persona__apellido2__icontains=ss[1]))
                            url_vars += "&s={}".format(ss)
                        else:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                                Q(inscripcionaspirante__persona__apellido2__icontains=ss[1]) &
                                               Q(inscripcionaspirante__persona__nombres__icontains=ss[2]))
                            url_vars += "&s={}".format(ss)


                    if int(idc):
                        filtro = filtro & (Q(cohortes__id=int(idc)))
                        data['idc'] = int(idc)
                        url_vars += f"&idc={idc}"

                    if int(ide):
                        if int(ide) == 4:
                            filtro = filtro & (Q(formapagopac__id=1))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 5:
                            filtro = filtro & (Q(formapagopac__id=2))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 6:
                            filtro = filtro & (Q(contrato__contratolegalizado=True))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 7:
                            filtro = filtro & (Q(es_becado=True))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 8:
                            idquery = CambioAdmitidoCohorteInscripcion.objects.filter(status=True).values_list('inscripcionCohorte__id', flat=True).order_by('inscripcionCohorte__id').distinct()
                            filtro = filtro & (Q(id__in=idquery))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        else:
                            filtro = filtro & (Q(estado_aprobador=int(ide)))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"

                    if int(ida):
                        if int(ida) == 1:
                            filtro = filtro & (Q(tiporespuesta__isnull=True))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        else:
                            filtro = filtro & (Q(tiporespuesta__id=int(ida)))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"

                    if int(idanio):
                        if int(idanio) > 0:
                            data['idanio'] = int(idanio)
                            filtro = filtro & Q(fecha_creacion__year=int(idanio))
                            url_vars += f"&idanio={idanio}"

                    if desde and hasta:
                        data['desde'] = desde
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha_creacion__range=(desde, hasta))
                        url_vars += "&desde={}".format(desde)
                        url_vars += "&hasta={}".format(hasta)

                    elif desde:
                        data['desde'] = desde
                        filtro = filtro & Q(fecha_creacion__gte=desde)
                        url_vars += "&desde={}".format(hasta)

                    elif hasta:
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha_creacion__lte=hasta)
                        url_vars += "&hasta={}".format(hasta)

                    query = InscripcionCohorte.objects.filter(filtro).exclude(id__in=idventas).order_by('-fecha_creacion')
                    paging = MiPaginador(query, 20)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["listado"] = page.object_list
                    data['eCohortes'] = CohorteMaestria.objects.filter(status=True).order_by('-id').distinct()
                    data['eAnios'] = InscripcionCohorte.objects.values_list('fecha_creacion__year', flat=True).order_by('fecha_creacion__year').distinct()
                    data['eAsignados'] = query.count()
                    data['eAtendidos'] = query.filter(tiporespuesta__isnull=False).count()
                    data['eNoAtendidos'] = query.filter(tiporespuesta__isnull=True).count()
                    data['eTiposrespuestas'] = TipoRespuestaProspecto.objects.filter(status=True).order_by('id')
                    return render(request, "comercial/viewleadsasignados.html", data)
                elif persona.es_asesor_financiamiento():
                    request.session['viewactive'] = 9
                    data['title'] = u'Leads por modalidad de pago diferido'
                    url_vars = ''
                    aa = datetime.now().date().year
                    # asi = aa + 1

                    search = request.GET.get('s', None)
                    idc = request.GET.get('idc', '0')
                    ide = request.GET.get('ide', '0')
                    ida = request.GET.get('ida', '0')
                    idanio = request.GET.get('idanio', str(aa))
                    desde = request.GET.get('desde', '')
                    hasta = request.GET.get('hasta', '')

                    idmatricula = InscripcionCohorte.objects.filter(status=True, formapagopac__id=2, inscripcion__matricula__isnull=False).values_list('id', flat=True)

                    filtro = Q(status=True, cohortes__maestriaadmision__carrera__coordinacion__id=7, formapagopac__id=2, estado_aprobador=2, aceptado=True)

                    if search:
                        data['search'] = search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=search) |
                                                     Q(inscripcionaspirante__persona__apellido2__icontains=search) |
                                                     Q(inscripcionaspirante__persona__nombres__icontains=search) |
                                                     Q(inscripcionaspirante__persona__cedula__icontains=search))
                            url_vars += "&s={}".format(search)
                        elif len(ss) == 2:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                                     Q(inscripcionaspirante__persona__apellido2__icontains=ss[1]))
                            url_vars += "&s={}".format(ss)
                        else:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                                Q(inscripcionaspirante__persona__apellido2__icontains=ss[1]) &
                                               Q(inscripcionaspirante__persona__nombres__icontains=ss[2]))
                            url_vars += "&s={}".format(ss)


                    if int(idc):
                        filtro = filtro & (Q(cohortes__id=int(idc)))
                        data['idc'] = int(idc)
                        url_vars += f"&idc={idc}"

                    if int(ide):
                        if int(ide) == 1:
                            filtro = filtro & (Q(todosubidofi=True, tienerechazofi=False, estadoformapago=1))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 3:
                            filtro = filtro & (Q(todosubidofi=False, tienerechazofi=True, estadoformapago=1))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 4:
                            filtro = filtro & (Q(subirrequisitogarante=True))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 5:
                            filtro = filtro & (Q(subirrequisitogarante=False))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 6:
                            filtro = filtro & (Q(es_becado=True))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 7:
                            idquery = CambioAdmitidoCohorteInscripcion.objects.filter(status=True).values_list('inscripcionCohorte__id', flat=True).order_by('inscripcionCohorte__id').distinct()
                            filtro = filtro & (Q(id__in=idquery))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        else:
                            filtro = filtro & (Q(estadoformapago=int(ide)))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"

                    if int(ida):
                        if int(ida) == 1:
                            filtro = filtro & (~Q(contrato__archivocontrato__exact='')) & (Q(contrato__estado=1))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 2:
                            filtro = filtro & (Q(contrato__estado=2))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 3:
                            filtro = filtro & (Q(contrato__estado=3))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 4:
                            filtro = filtro & (Q(contrato__contratolegalizado=True))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 5:
                            filtro = filtro & (~Q(contrato__archivopagare__exact='')) & (Q(contrato__estadopagare=1))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 6:
                            filtro = filtro & (Q(contrato__estadopagare=2))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 7:
                            filtro = filtro & (Q(contrato__estadopagare=3))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"
                        elif int(ida) == 8:
                            filtro = filtro & (~Q(contrato__archivodescargado__exact='') & (Q(contrato__archivodescargado__isnull=False)))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"

                    if int(idanio):
                        if int(idanio) > 0:
                            data['idanio'] = int(idanio)
                            filtro = filtro & Q(fecha_creacion__year=int(idanio))
                            url_vars += f"&idanio={idanio}"

                    if desde and hasta:
                        data['desde'] = desde
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha_creacion__date__range=(desde, hasta))
                        url_vars += "&desde={}".format(desde)
                        url_vars += "&hasta={}".format(hasta)

                    elif desde:
                        data['desde'] = desde
                        filtro = filtro & Q(fecha_creacion__date__gte=desde)
                        url_vars += "&desde={}".format(hasta)

                    elif hasta:
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha_creacion__date__lte=hasta)
                        url_vars += "&hasta={}".format(hasta)

                    query = InscripcionCohorte.objects.filter(filtro).exclude(id__in=idmatricula).order_by('-fecha_creacion')
                    paging = MiPaginador(query, 20)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["listado"] = page.object_list
                    data['eCohortes'] = CohorteMaestria.objects.filter(status=True).order_by('-id').distinct()
                    data['eAnios'] = InscripcionCohorte.objects.values_list('fecha_creacion__year', flat=True).order_by('fecha_creacion__year').distinct()
                    data['eTotal'] = query.count()
                    data['ePendientes'] = query.filter(todosubidofi=True, tienerechazofi=False, estadoformapago=1).count()
                    data['eAprobados'] = query.filter(estadoformapago=2).count()
                    data['eRechazados'] = query.filter(todosubidofi=False, tienerechazofi=True).count()

                    data['eContratosPendientes'] = query.filter((~Q(contrato__archivocontrato__exact='')) & (Q(contrato__estado=1))).count()
                    data['eContratosAprobados'] = query.filter(contrato__estado=2).count()
                    data['eContratosRechazados'] = query.filter(contrato__estado=3).count()

                    data['ePagaresPendientes'] = query.filter((~Q(contrato__archivopagare__exact='')) & (Q(contrato__estadopagare=1))).count()
                    data['ePagaresAprobados'] = query.filter(contrato__estadopagare=2).count()
                    data['ePagaresRechazados'] = query.filter(contrato__estadopagare=3).count()
                    return render(request, "comercial/viewleadsfinanciamiento.html", data)
                else:
                    request.session['viewactive'] = 14
                    data['title'] = u'Listado de postulaciones a programas de maestría'
                    url_vars = ''
                    aa = datetime.now().date().year

                    search = request.GET.get('s', None)
                    canti = request.GET.get('cantidad', 25)
                    idc = request.GET.get('idc', '0')
                    ide = request.GET.get('ide', '0')
                    ida = request.GET.get('ida', '0')
                    idcan = request.GET.get('idcan', '0')
                    idanio = request.GET.get('idanio', str(aa))
                    desde = request.GET.get('desde', '')
                    hasta = request.GET.get('hasta', '')

                    idventas = VentasProgramaMaestria.objects.filter(status=True, valida=True).values_list('inscripcioncohorte__id', flat=True)
                    filtro = Q(status=True, cohortes__maestriaadmision__carrera__coordinacion__id=7)

                    if search:
                        data['search'] = search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=search) |
                                                     Q(inscripcionaspirante__persona__apellido2__icontains=search) |
                                                     Q(inscripcionaspirante__persona__nombres__icontains=search) |
                                                     Q(inscripcionaspirante__persona__cedula__icontains=search))
                            url_vars += "&s={}".format(search)
                        elif len(ss) == 2:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                                     Q(inscripcionaspirante__persona__apellido2__icontains=ss[1]))
                            url_vars += "&s={}".format(ss)
                        else:
                            filtro = filtro & (Q(inscripcionaspirante__persona__apellido1__icontains=ss[0]) &
                                                Q(inscripcionaspirante__persona__apellido2__icontains=ss[1]) &
                                               Q(inscripcionaspirante__persona__nombres__icontains=ss[2]))
                            url_vars += "&s={}".format(ss)


                    if int(idc):
                        filtro = filtro & (Q(cohortes__id=int(idc)))
                        data['idc'] = int(idc)
                        url_vars += f"&idc={idc}"

                    if int(ide):
                        if int(ide) == 1:
                            filtro = filtro & (Q(estado_asesor=2))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 2:
                            filtro = filtro & (Q(estado_asesor=1))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 3:
                            filtro = filtro & (Q(tiporespuesta__isnull=False))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 4:
                            filtro = filtro & (Q(tiporespuesta__isnull=True))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 5:
                            filtro = filtro & (Q(estado_aprobador=1))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 6:
                            filtro = filtro & (Q(estado_aprobador=2))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 7:
                            filtro = filtro & (Q(estado_aprobador=3))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 8:
                            filtro = filtro & (Q(formapagopac__id=1))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 9:
                            filtro = filtro & (Q(formapagopac__id=2))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 10:
                            filtro = filtro & (Q(contrato__contratolegalizado=True))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 11:
                            filtro = filtro & (Q(todosubido=True, preaprobado=False))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 12:
                            filtro = filtro & (Q(leaddezona=True))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 13:
                            filtro = filtro & (Q(es_becado=True))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 14:
                            idquery = CambioAdmitidoCohorteInscripcion.objects.filter(status=True).values_list('inscripcionCohorte__id', flat=True).order_by('inscripcionCohorte__id').distinct()
                            filtro = filtro & (Q(id__in=idquery))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"

                    if int(ida):
                            filtro = filtro & (Q(asesor__id=int(ida)))
                            data['ida'] = int(ida)
                            url_vars += f"&ida={ida}"

                    if int(idcan):
                            filtro = filtro & (Q(inscripcionaspirante__persona__canton__id=int(idcan)))
                            data['idcan'] = int(idcan)
                            url_vars += f"&idcan={idcan}"

                    if int(idanio):
                        if int(idanio) > 0:
                            data['idanio'] = int(idanio)
                            filtro = filtro & Q(fecha_creacion__year=int(idanio))
                            url_vars += f"&idanio={idanio}"

                    if desde and hasta:
                        data['desde'] = desde
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha_creacion__date__range=(desde, hasta))
                        url_vars += "&desde={}".format(desde)
                        url_vars += "&hasta={}".format(hasta)

                    elif desde:
                        data['desde'] = desde
                        filtro = filtro & Q(fecha_creacion__date__gte=desde)
                        url_vars += "&desde={}".format(hasta)

                    elif hasta:
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha_creacion__date__lte=hasta)
                        url_vars += "&hasta={}".format(hasta)

                    query = InscripcionCohorte.objects.filter(filtro).exclude(id__in=idventas).order_by('-fecha_creacion')
                    paging = MiPaginador(query, canti)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_params"] = url_vars
                    data["url_vars"] = url_vars
                    data["listado"] = page.object_list
                    data['eCohortes'] = CohorteMaestria.objects.filter(status=True).order_by('-id').distinct()
                    data['eAnios'] = InscripcionCohorte.objects.values_list('fecha_creacion__year', flat=True).order_by('fecha_creacion__year').distinct()
                    data['eTotal'] = query.count()
                    data['eAsignados'] = query.filter(estado_asesor=2).count()
                    data['ePendientes'] = query.filter(estado_asesor=1).count()
                    data['eAtendidos'] = query.filter(tiporespuesta__isnull=False).count()
                    data['eNoAtendidos'] = query.filter(tiporespuesta__isnull=True).count()
                    data['eAsesores'] = AsesorComercial.objects.filter(status=True)
                    data['eCantones'] = Canton.objects.filter(status=True)
                    data['canti'] = canti
                    return render(request, "comercial/view.html", data)
            except Exception as ex:
                pass

def validapersonal(aspirante, idcarrera, lista, nomcarrera, userpostulante, clavepostulante):
    archivoadjunto = ''
    banneradjunto = ''
    correo = []
    if FormatoCarreraIpec.objects.filter(carrera_id=idcarrera, status=True):
        formatocorreo = FormatoCarreraIpec.objects.filter(carrera_id=idcarrera, status=True)[0]
        archivoadjunto = formatocorreo.archivo
        banneradjunto = formatocorreo.banner
        if formatocorreo.correomaestria:
            lista.append(formatocorreo.correomaestria)
    lista.append(conectar_cuenta(CUENTAS_CORREOS[18][1]))
    correo.append(aspirante.persona.email)
    correo.append(aspirante.persona.emailinst)
    arregloemail = [23, 24, 25, 26, 27, 28]
    emailaleatorio = random.choice(arregloemail)
    asunto = u"Registro exitoso para admisión de " + nomcarrera.nombre
    if archivoadjunto:
        # send_html_mail(asunto, "emails/registroexitoadmisionposgrado.html", {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante, 'usuario': userpostulante, 'clave': clavepostulante, 'formato': banneradjunto}, lista, [], [archivoadjunto], cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])
        send_html_mail(asunto, "emails/registroexitoadmisionposgrado.html",
                       {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante, 'usuario': userpostulante, 'clave': clavepostulante, 'formato': banneradjunto},
                       correo, [], [archivoadjunto],
                       cuenta=CUENTAS_CORREOS[18][1])
    else:
        send_html_mail(asunto, "emails/registroexitoadmisionposgrado.html",
                       {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante, 'usuario': userpostulante,
                        'clave': clavepostulante, 'formato': banneradjunto},
                       correo, [],
                       cuenta=CUENTAS_CORREOS[18][1])
        # send_html_mail(asunto, "emails/registroexitoadmisionposgrado.html", {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante,  'usuario': userpostulante, 'clave': clavepostulante, 'formato': banneradjunto}, lista, [], cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])
    # send_html_mail(asunto, "emails/registroexitoadmisionposgrado.html", {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante,  'usuario': userpostulante, 'clave': clavepostulante, 'formato': banneradjunto}, lista, [], cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])
    return aspirante

def validapersonalinterno(postulante, idcarrera, hoy, request, lista, nomcarrera,tipobeca, tipoconta):
    arregloemail = [23, 24, 25, 26, 27, 28]
    correo = []
    correo.append(postulante.email)
    correo.append(postulante.emailinst)
    emailaleatorio = random.choice(arregloemail)
    if not InscripcionAspirante.objects.filter(persona=postulante, status=True).exists():
        aspirante = InscripcionAspirante(persona=postulante)
        aspirante.save()
    else:
        aspirante = InscripcionAspirante.objects.filter(persona=postulante, status=True)[0]
    if CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True).exists():
        cohortemaestria = CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True)[0]
        if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
            inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                    cohortes=cohortemaestria,
                                                    tipobeca_id=tipobeca,
                                                    contactomaestria=tipoconta,
                                                    doblepostulacion=True)
            inscripcioncohorte.save(request)
    if not Group.objects.filter(pk=199, user=postulante.usuario):
        usuario = User.objects.get(pk=postulante.usuario.id)
        g = Group.objects.get(pk=199)
        g.user_set.add(usuario)
        g.save()
    archivoadjunto = ''
    banneradjunto = ''
    if FormatoCarreraIpec.objects.filter(carrera_id=idcarrera, status=True):
        formatocorreo = FormatoCarreraIpec.objects.filter(carrera_id=idcarrera, status=True)[0]
        archivoadjunto = formatocorreo.archivo
        banneradjunto = formatocorreo.banner
        if formatocorreo.correomaestria:
            lista.append(formatocorreo.correomaestria)
    asunto = u"Registro exitoso para admisión de " + nomcarrera.nombre
    if archivoadjunto:
        # send_html_mail(asunto, "emails/registroexitoadmisionposgrado.html", {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante, 'formato': banneradjunto}, lista, [], [archivoadjunto], cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])
        send_html_mail(asunto, "emails/registroexitoadmisionposgrado.html",
                       {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante, 'formato': banneradjunto},
                       correo, [], [archivoadjunto],
                       cuenta=CUENTAS_CORREOS[18][1])
    else:
        send_html_mail(asunto, "emails/registroexitoadmisionposgrado.html",
                       {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante, 'formato': banneradjunto},
                       correo, [],
                       cuenta=CUENTAS_CORREOS[18][1])
        # send_html_mail(asunto, "emails/registroexitoadmisionposgrado.html", {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante, 'formato': banneradjunto}, lista, [], cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])
    # send_html_mail(asunto, "emails/registroexitoadmisionposgrado.html", {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante, 'formato': banneradjunto}, lista, [], cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])

    return aspirante
