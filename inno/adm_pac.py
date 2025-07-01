# -*- coding: UTF-8 -*-
import json
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.forms.models import model_to_dict
from django.contrib import messages
from xlwt import *
import sys
import xlwt
import random
from decorators import secure_module, last_access
from inno.forms import CampoAmplioPacForm, CampoEspecificoPacForm, CampoDetalladoPacForm, CarreraPacForm, \
    TitulacionPacForm, CamposPacForm, DatosGeneralForm, FuncionSustantivaDocenciaPacForm, DetalleFuncionSustantivaDocenciaPacForm, \
    FuncionSustantivaInvestigacionPacForm, FuncionSustantivaVinculacionSociedadPacForm, InfraestructuraEquipamientoInformacionPacForm, \
    DetalleLaboratorioInfraestructuraPacForm, DetallePersonalAcademicoInfraestructuraPacForm, DetalleItinerarioProgramaPacForm, \
    DetallePreguntasPerfilegresoDocenciaPacForm, ConvenioPacForm, DetalleBibliotecaInfraestructuraPacForm, DetalleAulaInfraestructuraPacForm, \
    TipoPersonalPacForm, TipoFormacionRedisenoForm, PresupuestoPacColumnaForm, PresupuestoPacFilaForm, AnexoPacForm, DetalleAnexoPacForm, \
    CoordinadorPacForm, TipoProcesoPacForm, TipoProgramaPacForm, PerfilRequeridoPacForm, DetallePerfilIngresoForm, DetalleRequisitoIngresoForm, \
    TituloPerfilIngresoForm, FormaPagoPacForm, TipoFormaPagoPacForm, PlanificacionParaleloForm
from inno.models import CampoAmplioPac, CampoEspecificoPac, CampoDetalladoPac, CarreraPac, TitulacionPac, \
    TituloGradoAcademicoPac, NivelFormacionPac, EtapaProyectoCurricular, ProgramaPac, FuncionSustantivaDocenciaPac, \
    DetalleFuncionSustantivaDocenciaPac, \
    FuncionSustantivaInvestigacionPac, FuncionSustantivaVinculacionSociedadPac, \
    InfraestructuraEquipamientoInformacionPac, \
    DetalleLaboratorioInfraestructuraPac, DetallePersonalAcademicoInfraestructuraPac, DetalleItinerarioProgramaPac, \
    PreguntasPac, \
    DetallePreguntasPerfilegresoDocenciaPac, ConveniosPac, DetalleLaboratorioInfraestructuraPac, \
    DetalleBibliotecaInfraestructuraPac, \
    DetalleAulaInfraestructuraPac, DetalleMicrocurricularPac, TipoPersonalPac, TipoFormacionRediseno, \
    PresupuestoPacColumna, PresupuestoPacFila, \
    InformacionfinancieraPac, AnexosPac, DetalleAnexosPac, ArchivoAnexoPac, InformacionInstitucionalPac, TipoProcesoPac, \
    TipoProgramaPac, PerfilRequeridoPac, PerfilRequeridoDirectorPac, DetallePerfilIngreso, DetalleRequisitoIngreso, TipoFormaPagoPac, \
    AprobacionTrabajoIntegracionCurricular, PlanificacionParalelo

from sagest.forms import ProveedorForm
from postulate.forms import TituloHojaVidaForm
from sagest.models import Proveedor, Departamento
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, puede_realizar_accion, generar_nombre
from sga.models import Materia, Malla, TituloInstitucion, Persona, Profesor, Modalidad, InstitucionEducacionSuperior, Periodo, ConvenioEmpresa, CamposTitulosPostulacion, SubAreaConocimientoTitulacion,\
    SubAreaEspecificaConocimientoTitulacion, Titulo
from django.template.loader import get_template
from django.template.context import Context
from sga.templatetags.sga_extras import encrypt

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    data['persona']=persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    data['url_'] = request.path
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'addcampos':
            try:
                # nivelformacion = NivelFormacionPac.objects.get(pk=request.POST['idnivelformacion'])
                f = CamposPacForm(request.POST)
                if f.is_valid():
                    campoamplio= None
                    campoespecifico= None
                    campodetallado= None
                    carrera= None
                    titulacion= None
                    if not CampoAmplioPac.objects.filter(status=True,descripcion=f.cleaned_data['descripcionamplio'].upper()).exists():
                        campoamplio = CampoAmplioPac(codigo=f.cleaned_data['codigoamplio'],
                                                  descripcion=f.cleaned_data['descripcionamplio'],
                                                  nivelformacion=f.cleaned_data['nivelformacion'])
                        campoamplio.save(request)
                        log(u'Adiciono nuevo campo amplio: %s' % campoamplio, request, "add")
                    else:
                        campoamplio= CampoAmplioPac.objects.filter(status=True, descripcion=f.cleaned_data['descripcionamplio'].upper())[0]


                    if not CampoEspecificoPac.objects.filter(status=True,campoampliopac_id=campoamplio.id, descripcion=f.cleaned_data['descripcionespecifico'].upper()).exists():
                        campoespecifico = CampoEspecificoPac(campoampliopac_id=campoamplio.id,
                                                            codigo=f.cleaned_data['codigoespecifico'],
                                                            descripcion=f.cleaned_data['descripcionespecifico'],
                                                            nivelformacion=f.cleaned_data['nivelformacion'])
                        campoespecifico.save(request)
                        log(u'Adiciono nuevo campo especifico: %s' % campoamplio, request, "add")
                    else:
                        campoespecifico = CampoEspecificoPac.objects.filter(status=True, descripcion=f.cleaned_data['descripcionespecifico'].upper())[0]


                    if not CampoDetalladoPac.objects.filter(status=True,campoespecificopac_id=campoespecifico.id,descripcion=f.cleaned_data['descripciondetallado'].upper()).exists():
                        campodetallado = CampoDetalladoPac(campoespecificopac_id=campoespecifico.id,
                                                        codigo=f.cleaned_data['codigodetallado'],
                                                        descripcion=f.cleaned_data['descripciondetallado'],
                                                        nivelformacion=f.cleaned_data['nivelformacion'])
                        campodetallado.save(request)
                        log(u'Adiciono nuevo campo detallado: %s' % campoamplio, request, "add")
                    else:
                        campodetallado = CampoDetalladoPac.objects.filter(status=True, descripcion=f.cleaned_data['descripciondetallado'].upper())[0]
                    # else:
                    #     return JsonResponse({"result": "bad", "mensaje": "Campo Detallado Repetido."})

                    if not CarreraPac.objects.filter(status=True,campodetalladopac_id=campodetallado.id, descripcion=f.cleaned_data['descripcioncarrera'].upper()).exists():
                        carrera = CarreraPac(campodetalladopac_id=campodetallado.id,
                                                        codigo=f.cleaned_data['codigocarrera'],
                                                        descripcion=f.cleaned_data['descripcioncarrera'],
                                                        abreviaturacarrera=f.cleaned_data['abreviaturacarrera'],
                                                        nivelformacion=f.cleaned_data['nivelformacion'])
                        carrera.save(request)
                        log(u'Adiciono nueva carrera: %s' % campoamplio, request, "add")
                    else:
                        carrera = CarreraPac.objects.filter(status=True, descripcion=f.cleaned_data['descripcioncarrera'].upper())[0]
                    # else:
                    #     return JsonResponse({"result": "bad", "mensaje": "Carrera Repetida."})

                    if not TitulacionPac.objects.filter(status=True,carrerapac_id=carrera.id, tituloobtenidohombre=f.cleaned_data['tituloobtenidohombre'].upper(), tituloobtenidomujer=f.cleaned_data['tituloobtenidomujer'].upper()).exists():
                        titulacion = TitulacionPac(carrerapac_id=carrera.id,
                                                        codigo=f.cleaned_data['codigotitulacion'],
                                                        tituloobtenidohombre=f.cleaned_data['tituloobtenidohombre'],
                                                        tituloobtenidomujer=f.cleaned_data['tituloobtenidomujer'],
                                                        nivelformacion=f.cleaned_data['nivelformacion'])
                        titulacion.save(request)
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})

                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addcampoamplio':
            try:
                nivelformacion = NivelFormacionPac.objects.get(pk=request.POST['idnivelformacion'])
                f = CampoAmplioPacForm(request.POST)
                if f.is_valid():
                    if not CampoAmplioPac.objects.filter(status=True,descripcion=f.cleaned_data['descripcion'].upper()).exists():
                        campoamplio = CampoAmplioPac(codigo=f.cleaned_data['codigo'],
                                                  descripcion=f.cleaned_data['descripcion'],
                                                  nivelformacion_id=nivelformacion)
                        campoamplio.save(request)
                        log(u'Adiciono nuevo campo amplio: %s' % campoamplio, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcampoamplio':
            try:
                campoamplio = CampoAmplioPac.objects.get(pk=request.POST['id'])
                f = CampoAmplioPacForm(request.POST)
                if f.is_valid():
                    if not CampoAmplioPac.objects.filter(status=True,descripcion=f.cleaned_data['descripcion'].upper()).exclude(pk=request.POST['id']).exists():
                        campoamplio.codigo = f.cleaned_data['codigo']
                        campoamplio.descripcion = f.cleaned_data['descripcion']
                        campoamplio.save(request)
                        log(u'Modificó Campo Amplio: %s' % campoamplio, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletecampoamplio':
            try:
                campoamplio = CampoAmplioPac.objects.get(pk=request.POST['id'])
                if campoamplio.enuso():
                    return JsonResponse({"result": "bad", "mensaje": u"Campo Amplio en uso."})
                campoamplio.status = False
                campoamplio.save(request)
                log(u'Editó el estado de Campo Amplio: %s' % campoamplio, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'deltipo':
            try:
                tipo = TipoFormacionRediseno.objects.get(pk=request.POST['id'])
                if tipo.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": u"Tipo de formación en uso."})
                tipo.status = False
                tipo.save(request)
                messages.success(request, 'Registro eliminado correctamente.')
                log(u'eliminó tipo de formación %s' % tipo, request, "edit")
                return JsonResponse({"result": False,"error":False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True,"error":True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'addcampoespecifico':
            try:
                f = CampoEspecificoPacForm(request.POST)
                if f.is_valid():
                    if not CampoEspecificoPac.objects.filter(status=True,descripcion=f.cleaned_data['descripcion'].upper()).exists():
                        campoespecifico = CampoEspecificoPac(campoampliopac=f.cleaned_data['campoampliopac'],
                                                            codigo=f.cleaned_data['codigo'],
                                                            descripcion=f.cleaned_data['descripcion'])
                        campoespecifico.save(request)
                        log(u'Adiciono nuevo campo específico: %s' % campoespecifico, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcampoespecifico':
            try:
                campoespecifico = CampoEspecificoPac.objects.get(pk=request.POST['id'])
                f = CampoEspecificoPacForm(request.POST)
                if f.is_valid():
                    if not CampoEspecificoPac.objects.filter(status=True,descripcion=f.cleaned_data['descripcion'].upper()).exclude(pk=request.POST['id']).exists():
                        campoespecifico.campoampliopac = f.cleaned_data['campoampliopac']
                        campoespecifico.codigo = f.cleaned_data['codigo']
                        campoespecifico.descripcion = f.cleaned_data['descripcion']
                        campoespecifico.save(request)
                        log(u'Modificó Campo Específico: %s' % campoespecifico, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletecampoespecifico':
            try:
                campoespecifico = CampoEspecificoPac.objects.get(pk=request.POST['id'])
                if campoespecifico.enuso():
                    return JsonResponse({"result": "bad", "mensaje": u"Campo Específico en uso."})
                campoespecifico.status = False
                campoespecifico.save(request)
                log(u'Editó el estado de Campo Especifico: %s' % campoespecifico, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addcampodetallado':
            try:
                f = CampoDetalladoPacForm(request.POST)
                if f.is_valid():
                    if not CampoDetalladoPac.objects.filter(status=True,descripcion=f.cleaned_data['descripcion'].upper()).exists():
                        campodetallado = CampoDetalladoPac(campoespecificopac=f.cleaned_data['campoespecificopac'],
                                                        codigo=f.cleaned_data['codigo'],
                                                        descripcion=f.cleaned_data['descripcion'])
                        campodetallado.save(request)
                        log(u'Adiciono nuevo campo detallado: %s' % campodetallado, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcampodetallado':
            try:
                campodetallado = CampoDetalladoPac.objects.get(pk=request.POST['id'])
                f = CampoDetalladoPacForm(request.POST)
                if f.is_valid():
                    if not CampoDetalladoPac.objects.filter(status=True,descripcion=f.cleaned_data['descripcion'].upper()).exclude(pk=request.POST['id']).exists():
                        campodetallado.campoespecificopac = f.cleaned_data['campoespecificopac']
                        campodetallado.codigo = f.cleaned_data['codigo']
                        campodetallado.descripcion = f.cleaned_data['descripcion']
                        campodetallado.save(request)
                        log(u'Modificó Campo Detallado: %s' % campodetallado, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletecampodetallado':
            try:
                campodetallado = CampoDetalladoPac.objects.get(pk=request.POST['id'])
                if campodetallado.enuso():
                    return JsonResponse({"result": "bad", "mensaje": u"Campo Detallado en uso."})
                campodetallado.status = False
                campodetallado.save(request)
                log(u'Editó el estado de Campo Detallado: %s' % campodetallado, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addcarrera':
            try:
                f = CarreraPacForm(request.POST)
                if f.is_valid():
                    if not CarreraPac.objects.filter(status=True,descripcion=f.cleaned_data['descripcion'].upper()).exists():
                        carrera = CarreraPac(campodetalladopac=f.cleaned_data['campodetalladopac'],
                                                        codigo=f.cleaned_data['codigo'],
                                                        descripcion=f.cleaned_data['descripcion'],
                                                        abreviaturacarrera = f.cleaned_data['abreviaturacarrera'])
                        carrera.save(request)
                        log(u'Adiciono nueva Carrera: %s' % carrera, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcarrera':
            try:
                carrera = CarreraPac.objects.get(pk=request.POST['id'])
                f = CarreraPacForm(request.POST)
                if f.is_valid():
                    if not CarreraPac.objects.filter(status=True,descripcion=f.cleaned_data['descripcion'].upper()).exclude(pk=request.POST['id']).exists():
                        carrera.campodetalladopac = f.cleaned_data['campodetalladopac']
                        carrera.codigo = f.cleaned_data['codigo']
                        carrera.descripcion = f.cleaned_data['descripcion']
                        carrera.abreviaturacarrera = f.cleaned_data['abreviaturacarrera']
                        carrera.save(request)
                        log(u'Modificó Carrera: %s' % carrera, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletecarrera':
            try:
                carrera = CarreraPac.objects.get(pk=request.POST['id'])
                if carrera.enuso():
                    return JsonResponse({"result": "bad", "mensaje": u"Carrera en uso."})
                carrera.status = False
                carrera.save(request)
                log(u'Edito el estado de Carrera: %s' % carrera, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addtitulacion':
            try:
                f = TitulacionPacForm(request.POST)
                if f.is_valid():
                    if not TitulacionPac.objects.filter(status=True,descripcion=f.cleaned_data['descripcion'].upper()).exists():
                        titulacion = TitulacionPac(carrerapac=f.cleaned_data['carrerapac'],
                                                        codigo=f.cleaned_data['codigo'],
                                                        descripcion=f.cleaned_data['descripcion'])
                        titulacion.save(request)
                        log(u'Adiciono nueva Titulacion: %s' % titulacion, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edittitulacion':
            try:
                titulacion = TitulacionPac.objects.get(pk=request.POST['id'])
                f = TitulacionPacForm(request.POST)
                if f.is_valid():
                    if not TitulacionPac.objects.filter(status=True,tituloobtenidohombre=f.cleaned_data['tituloobtenidohombre'].upper(), tituloobtenidomujer=f.cleaned_data['tituloobtenidomujer'].upper()).exclude(pk=request.POST['id']).exists():
                        titulacion.carrerapac = f.cleaned_data['carrerapac']
                        titulacion.codigo = f.cleaned_data['codigo']
                        titulacion.tituloobtenidohombre = f.cleaned_data['tituloobtenidohombre']
                        titulacion.tituloobtenidomujer = f.cleaned_data['tituloobtenidomujer']
                        titulacion.save(request)
                        log(u'Modificó Titulación: %s' % titulacion, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                else:
                     raise NameError('Error')
            except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletetitulacion':
            try:
                titulacion = TitulacionPac.objects.get(pk=request.POST['id'])
                titulacion.status = False
                titulacion.save(request)
                log(u'Edito el estado de Titulación: %s' % titulacion, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addcarrerarant':
            try:
                if not TituloGradoAcademicoPac.objects.filter(campoampliopac_id=int(request.POST['idamplio']),campoespecificopac_id=int(request.POST['idespecifico']), campodetalladopac_id=int(request.POST['iddetallado']), carrerapac_id=int(request.POST['idcarrera']), titulacionpac_id=int(request.POST['idtitulacion']), status=True ).exists():
                    tgradoacademico = TituloGradoAcademicoPac(campoampliopac_id=int(request.POST['idamplio']),
                                                    campoespecificopac_id=int(request.POST['idespecifico']),
                                                    campodetalladopac_id=int(request.POST['iddetallado']),
                                                    carrerapac_id=int(request.POST['idcarrera']),
                                                    titulacionpac_id=int(request.POST['idtitulacion']))
                    tgradoacademico.save(request)
                    log(u'Adiciono Titulo Grado Académico:%s' % tgradoacademico, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletetitulogradoacademico':
            try:
                tgradoacademico = TituloGradoAcademicoPac.objects.get(pk=request.POST['id'])
                tgradoacademico.status = False
                tgradoacademico.save(request)
                log(u'Edito el estado de Titulo Grado Académico: %s' % tgradoacademico, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'campoespecifico':
            try:
                amplio = CampoAmplioPac.objects.get(pk=request.POST['id'])
                lista = []
                for especifico in CampoEspecificoPac.objects.filter(campoampliopac=amplio, status=True):
                    lista.append([especifico.id, especifico.descripcion])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'campodetallado':
            try:
                especifico = CampoEspecificoPac.objects.get(pk=request.POST['id'])
                lista = []
                for detallado in CampoDetalladoPac.objects.filter(campoespecificopac=especifico, status=True):
                    lista.append([detallado.id, detallado.descripcion])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'carrera':
            try:
                detallado = CampoDetalladoPac.objects.get(pk=request.POST['id'])
                lista = []
                for carrera in CarreraPac.objects.filter(campodetalladopac=detallado, status=True):
                    lista.append([carrera.id, carrera.descripcion])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'titulacion':
            try:
                carrera = CarreraPac.objects.get(pk=request.POST['id'])
                lista = []
                for titulacion in TitulacionPac.objects.filter(carrerapac=carrera, status=True):
                    lista.append([titulacion.id, titulacion.descripcion])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'datosdocente':
            try:
                datosdocente = Profesor.objects.get(pk=request.POST['id_nombres'])
                correo = datosdocente.persona.emailinst
                correo2 = datosdocente.persona.email
                telfinst = datosdocente.persona.telefono_conv
                ext = datosdocente.persona.telefonoextension
                celular = datosdocente.persona.telefono
                return JsonResponse({'result': 'ok', 'correo': correo, 'correo2': correo2, 'telfinst': telfinst ,'ext': ext, 'celular': celular })
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'extraercampostitulacion':
            try:
                titulacion = CamposTitulosPostulacion.objects.get(pk=request.POST['id'])
                lista = []
                ca, ce, cd = '','',''
                if titulacion:
                    if titulacion.campoamplio.all():
                        ca = titulacion.campoamplio.all()[0]
                    if titulacion.campoespecifico.all():
                        ce = titulacion.campoespecifico.all()[0]
                    if titulacion.campodetallado.all():
                        cd = titulacion.campodetallado.all()[0]
                lista.append(['%s ' % (ca),'%s ' % (ce),'%s ' % (cd)])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'listar_campoespecifico':
            try:
                campoamplio = CampoAmplioPac.objects.get(pk=request.POST['id'])
                lista = []
                for campoespecifico in campoamplio.campoespecificopac_set.filter(status=True):
                    lista.append([campoespecifico.id, campoespecifico.descripcion])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'listar_campodetallado':
            try:
                campoespecifico = CampoEspecificoPac.objects.get(pk=request.POST['id'])
                lista = []
                for campodetallado in campoespecifico.campodetalladopac_set.filter(status=True):
                    lista.append([campodetallado.id, campodetallado.descripcion])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'listar_carrera':
            try:
                campodetallado = CampoDetalladoPac.objects.get(pk=request.POST['id'])
                lista = []
                for carrera in campodetallado.carrerapac_set.filter(status=True):
                    lista.append([carrera.id, carrera.descripcion])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'listar_titulacion':
            try:
                carerrapac = CarreraPac.objects.get(pk=request.POST['id'])
                lista = []
                for titulacion in carerrapac.titulacionpac_set.filter(status=True):
                    if persona.sexo.id == 2:
                        lista.append([titulacion.id, titulacion.tituloobtenidohombre])
                    else:
                        lista.append([titulacion.id, titulacion.tituloobtenidomujer])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'datosgenerales':
            try:
                f = DatosGeneralForm(request.POST)
                if f.is_valid():
                    caltotalhoras = 0
                    caltotalcreditos = 0

                    # newfile = None
                    # if 'anexoresolucion' in request.FILES:
                    #     newfile = request.FILES['anexoresolucion']
                    #     newfile._name = generar_nombre("anexoresolucion_ocs_", newfile._name)
                    #
                    # newfile2 = None
                    # if 'anexoresolucioncaces' in request.FILES:
                    #     newfile2 = request.FILES['anexoresolucioncaces']
                    #     newfile2._name = generar_nombre("anexoresolucion_caces_", newfile2._name)

                    datosgeneral = ProgramaPac( tipotramite=f.cleaned_data['tipotramite'],

                                                tipoproceso=f.cleaned_data['tipoproceso'],
                                                tipoprograma=f.cleaned_data['tipoprograma'],

                                                codigosniese=f.cleaned_data['codigosniese'],
                                                proyectoinnovador=f.cleaned_data['proyectoinnovador'],
                                                tipoformacion=f.cleaned_data['tipoformacion'],
                                                modalidad=f.cleaned_data['modalidad'],
                                                ejecucionmodalidad=f.cleaned_data['ejecucionmodalidad'],
                                                proyectoenred=f.cleaned_data['proyectoenred'],
                                                campostitulacion=f.cleaned_data['campostitulacion'],
                                                # campoampliopac=f.cleaned_data['campoampliopac'],
                                                # campoespecificopac=f.cleaned_data['campoespecificopac'],
                                                # campodetalladopac=f.cleaned_data['campodetalladopac'],
                                                carrera=f.cleaned_data['carrera'],
                                                numeroperiodosordinario=f.cleaned_data['numeroperiodosordinario'],
                                                numerosemanaordinario=f.cleaned_data['numerosemanaordinario'],

                                                periodoextraordinario=f.cleaned_data['periodoextraordinario'],

                                                indicehoraplanificacion=f.cleaned_data['indicehoraplanificacion'],

                                                totalhoras=f.cleaned_data['totalhoras'],# caltotalhoras,
                                                totalcreditos=caltotalcreditos,

                                                totalhorasaprendizajecontactodocente= f.cleaned_data['totalhorasaprendizajecontactodocente'],
                                                totalhorasaprendizajepracticoexperimental= f.cleaned_data['totalhorasaprendizajepracticoexperimental'],
                                                totalhorasaprendizajeautonomo= f.cleaned_data['totalhorasaprendizajeautonomo'],
                                                totalhoraspracticasprofesionales= f.cleaned_data['totalhoraspracticasprofesionales'],
                                                totalhorasunidadtitulacion= f.cleaned_data['totalhorasunidadtitulacion'],

                                                numerocohorte=f.cleaned_data['numerocohorte'],
                                                numeroparalelocohorte=f.cleaned_data['numeroparalelocohorte'],
                                                numerototalasignatura=f.cleaned_data['numerototalasignatura'],
                                                numeroestudiantecohorte=f.cleaned_data['numeroestudiantecohorte'],

                                                fechaaprobacion=f.cleaned_data['fechaaprobacion'],
                                                fechaaprobacioncaces=f.cleaned_data.get('fechaaprobacioncaces'),
                                                numeroresolucion=f.cleaned_data['numeroresolucion'],

                                                numeroresolucioncaces=f.cleaned_data['numeroresolucioncaces'],

                                                estructurainstitucional=f.cleaned_data['estructurainstitucional'],
                                                provincia=f.cleaned_data['provincia'],
                                                canton=f.cleaned_data['canton'],
                                                parroquia=f.cleaned_data['parroquia'],
                                                )
                    datosgeneral.save(request)

                    if request.POST['infor']:
                        inf = InformacionInstitucionalPac.objects.get(pk=int(request.POST['infor']))
                        inf.programapac = datosgeneral
                        inf.save(request)

                    # if newfile:
                    #     datosgeneral.anexoresolucion = newfile
                        # # Guardar anexos en tabla ArchivoAnexos
                        # a = AnexosPac.objects.filter(status=True, descripcion='ANEXOS DATOS GENERALES')
                        # if not a:
                        #     anexo = AnexosPac(descripcion='ANEXOS DATOS GENERALES')
                        #     anexo.save()
                        #     det = DetalleAnexosPac.objects.filter(anexo_id=anexo.id, descripcion='RESOLUCIÓN OCS')
                        #     if not a:
                            #     detanexo = DetalleAnexosPac(anexo_id=anexo.id, descripcion='RESOLUCIÓN OCS')
                            #     detanexo.save()
                            #     archivo = ArchivoAnexoPac(programapac_id=datosgeneral.id,anexo_id=detanexo.id,archivo=newfile)
                            #     archivo.save()

                    # if newfile2:
                    #     datosgeneral.anexoresolucioncaces = newfile2
                    if f.cleaned_data['mencionitinerario']:
                        datosgeneral.mencionitinerario = f.cleaned_data['mencionitinerario']
                    else:
                        datosgeneral.mencionitinerario = 1
                    datosgeneral.save(request)

                    if f.cleaned_data['proyectoenred'] == '1':
                        for integrante in f.cleaned_data['integrantesred']:
                            datosgeneral.integrantesred.add(integrante)
                        datosgeneral.save(request)

                    if f.cleaned_data['periodoextraordinario'] == '1':
                        datosgeneral.numeroperiodosextraordinario = f.cleaned_data['numeroperiodosextraordinario']
                        datosgeneral.numerosemanaextraordinario = f.cleaned_data['numerosemanaextraordinario']
                        datosgeneral.save(request)

                    if 'detalle' in request.POST:
                        if request.POST['detalle']:
                            listadetalle = json.loads(request.POST['detalle'])
                            if listadetalle:
                                for list in listadetalle:
                                    ingresodetalledatos = DetalleItinerarioProgramaPac(programaPac=datosgeneral, nombreitinerario=list['listanombreitinerario'],codigo=list['codigoitinerario'])
                                    ingresodetalledatos.nivelitinerario_id = list['listanivelitinerario']
                                    ingresodetalledatos.save(request)
                    messages.success(request, 'Se guardó exitosamente.')
                    log(u'Adiciono nuevo Datos Generales: %s' % datosgeneral, request, "add")
                    return JsonResponse({"result": "ok", "id": encrypt(datosgeneral.id)})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editdatosgenerales':
            try:
                datosgenerales = ProgramaPac.objects.get(pk=int(encrypt(request.POST['id'])))
                f = DatosGeneralForm(request.POST)
                if f.is_valid():

                    # newfile = None
                    # if 'anexoresolucion' in request.FILES:
                    #     newfile = request.FILES['anexoresolucion']
                    #     newfile._name = generar_nombre("anexoresolucion_", newfile._name)
                    #
                    # newfile2 = None
                    # if 'anexoresolucioncaces' in request.FILES:
                    #     newfile2 = request.FILES['anexoresolucioncaces']
                    #     newfile2._name = generar_nombre("anexoresolucion_caces_", newfile2._name)

                    caltotalhoras = 0
                    caltotalcreditos = 0
                    datosgenerales.tipotramite = f.cleaned_data['tipotramite']

                    datosgenerales.tipoproceso = f.cleaned_data['tipoproceso']
                    datosgenerales.tipoprograma = f.cleaned_data['tipoprograma']

                    datosgenerales.codigosniese = request.POST['codigosniese']
                    datosgenerales.proyectoinnovador = f.cleaned_data['proyectoinnovador']
                    datosgenerales.tipoformacion = f.cleaned_data['tipoformacion']
                    datosgenerales.modalidad = f.cleaned_data['modalidad']
                    datosgenerales.ejecucionmodalidad = f.cleaned_data['ejecucionmodalidad']
                    datosgenerales.proyectoenred = f.cleaned_data['proyectoenred']
                    datosgenerales.campostitulacion = f.cleaned_data['campostitulacion']
                    # datosgenerales.campoampliopac = f.cleaned_data['campoampliopac']
                    # datosgenerales.campoespecificopac = f.cleaned_data['campoespecificopac']
                    # datosgenerales.campodetalladopac = f.cleaned_data['campodetalladopac']
                    datosgenerales.carrera = f.cleaned_data['carrera']
                    datosgenerales.indicehoraplanificacion = f.cleaned_data['indicehoraplanificacion']
                    datosgenerales.numeroperiodosordinario = f.cleaned_data['numeroperiodosordinario']
                    datosgenerales.numerosemanaordinario = f.cleaned_data['numerosemanaordinario']

                    datosgenerales.periodoextraordinario = f.cleaned_data['periodoextraordinario']

                    if f.cleaned_data['periodoextraordinario'] == '1':
                        datosgenerales.numeroperiodosextraordinario = f.cleaned_data['numeroperiodosextraordinario']
                        datosgenerales.numerosemanaextraordinario = f.cleaned_data['numerosemanaextraordinario']
                    else:
                        datosgenerales.numeroperiodosextraordinario = 0
                        datosgenerales.numerosemanaextraordinario = 0

                    datosgenerales.totalhoras = f.cleaned_data['totalhoras'] #= caltotalhoras
                    datosgenerales.totalcreditos = caltotalcreditos

                    datosgenerales.totalhorasaprendizajecontactodocente = f.cleaned_data['totalhorasaprendizajecontactodocente']
                    datosgenerales.totalhorasaprendizajepracticoexperimental = f.cleaned_data['totalhorasaprendizajepracticoexperimental']
                    datosgenerales.totalhorasaprendizajeautonomo = f.cleaned_data['totalhorasaprendizajeautonomo']
                    datosgenerales.totalhoraspracticasprofesionales = f.cleaned_data['totalhoraspracticasprofesionales']
                    datosgenerales.totalhorasunidadtitulacion = f.cleaned_data['totalhorasunidadtitulacion']
                    datosgenerales.numerocohorte = f.cleaned_data['numerocohorte']
                    datosgenerales.numeroparalelocohorte = f.cleaned_data['numeroparalelocohorte']
                    datosgenerales.numeroestudiantecohorte = f.cleaned_data['numeroestudiantecohorte']
                    datosgenerales.numerototalasignatura = f.cleaned_data['numerototalasignatura']
                    if f.cleaned_data['mencionitinerario']:
                        datosgenerales.mencionitinerario = f.cleaned_data['mencionitinerario']
                    else:
                        datosgenerales.mencionitinerario = 1
                    datosgenerales.fechaaprobacion = f.cleaned_data['fechaaprobacion']
                    datosgenerales.fechaaprobacioncaces = f.cleaned_data.get('fechaaprobacioncaces')
                    datosgenerales.numeroresolucion = f.cleaned_data['numeroresolucion']
                    datosgenerales.sesion = f.cleaned_data['sesionocs']
                    datosgenerales.numeroresolucioncaces = f.cleaned_data['numeroresolucioncaces']
                    # if newfile:
                    #     datosgenerales.anexoresolucion = newfile
                    # if newfile2:
                    #     datosgenerales.anexoresolucioncaces = newfile2

                    datosgenerales.estructurainstitucional = f.cleaned_data['estructurainstitucional']
                    datosgenerales.provincia = f.cleaned_data['provincia']
                    datosgenerales.canton = f.cleaned_data['canton']
                    datosgenerales.parroquia = f.cleaned_data['parroquia']
                    datosgenerales.integrantesred.clear()
                    datosgenerales.save(request)

                    if f.cleaned_data['proyectoenred'] == '1':
                        for integrante in f.cleaned_data['integrantesred']:
                            datosgenerales.integrantesred.add(integrante)
                        datosgenerales.save(request)

                    messages.success(request, 'Se editó exitosamente.')
                    log(u'Modifico Datos Generales Programa Pac: %s' % datosgenerales, request, "editdatosgenerales")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletedatosgenerales':
            try:
                programapac = ProgramaPac.objects.get(pk=request.POST['id'])
                info = InformacionInstitucionalPac.objects.filter(programapac=programapac).last()
                info.status = False
                info.save(request)
                programapac.status = False
                programapac.save(request)
                log(u'Eliminó ProgramaPac: %s' % programapac, request, "edit")
                messages.success(request, 'Se eliminó exitosamente.')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'additemdetalleitinerarioprogramapac':
            try:
                detalle = DetalleItinerarioProgramaPac(programaPac_id=request.POST['idprogramapac'],
                                                                 nombreitinerario=request.POST['nombreitinerario'],
                                                       codigo=request.POST['codigoitinerario'])
                detalle.nivelitinerario_id = request.POST['nivelitinerario']
                detalle.save(request)
                log(u'Adicinó detalle de itinerario - ProgramaPac: %s' % detalle, request, "add")
                # messages.success(request, 'Se Adicinó Itinerario exitosamente.')
                return JsonResponse({"result": "ok", 'codigoinformedet': detalle.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'itemdetalleitinerarioprogramapac':
            try:
                detalle = DetalleItinerarioProgramaPac.objects.get(pk=request.POST['id'])
                descripcion = detalle.nombreitinerario
                idobjetivo = detalle.id
                return JsonResponse({"result": "ok", 'descripcion': descripcion, 'codigorai': idobjetivo})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'eliminaritemdetalleitinerarioprogramapac':
            try:
                itemdetalle = DetalleItinerarioProgramaPac.objects.get(pk=request.POST['idcodigodet'])
                log(u'Eliminó item detalle Itinerario ProgramaPac: %s' % itemdetalle, request, "del")
                # messages.success(request, 'Se eliminó Itinerario exitosamente.')
                itemdetalle.status=False
                itemdetalle.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addconveniopac':
            try:
                convenio = ConveniosPac(
                             programapac_id=int(encrypt(request.POST['idprograma'])),
                             convenioinstitucional_id=request.POST['convenioinstitucional'])
                convenio.save(request)
                messages.success(request, 'Se adicionó convenio exitosamente.')
                log(u'Adicionó Convenio PAC: %s' % convenio, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'listar_convenioinstitucional':
            try:
                conveniospac = ConveniosPac.objects.filter(programapac=request.POST['id'],status=True)
                listx = []
                for x in conveniospac:
                    listx.append(x.convenioinstitucional.id)
                convenioempresa = ConvenioEmpresa.objects.filter(status=True).exclude(pk__in=listx)
                lista = []
                for conv in convenioempresa:
                    lista.append([conv.id, str(conv)])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        # elif action == 'editconveniopac':
        #     try:
        #         conveniopac = ConveniosPac.objects.get(pk=request.POST['id'])
        #         f = ConvenioPacForm(request.POST)
        #         if f.is_valid():
        #             conveniopac.convenioinstitucional = f.cleaned_data['convenioinstitucional']
        #             conveniopac.save(request)
        #             messages.success(request, 'Se editó exitosamente')
        #             log(u'Modifico Convenio Pac: %s' % conveniopac, request, "editconveniopac")
        #             return JsonResponse({"result": "ok"})
        #         else:
        #             pass
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteconveniopac':
            try:
                conveniopac = ConveniosPac.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Elimino Convenio Pac: %s' % conveniopac, request, "del")
                conveniopac.delete()
                messages.success(request, 'Se eliminó exitosamente')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addfuncionsustantiva':
            try:
                f = FuncionSustantivaDocenciaPacForm(request.POST)
                if f.is_valid():
                    funcionsustantiva = FuncionSustantivaDocenciaPac(
                                        programapac_id=int(encrypt(request.POST['pro'])),
                                        objetivogeneral=f.cleaned_data['objetivogeneral'],
                                        objetivoespecifico=f.cleaned_data['objetivoespecifico'],
                                        # perfilingreso=f.cleaned_data['perfilingreso'],
                                        # requisitoingreso=f.cleaned_data['requisitoingreso'],
                                        perfilprofesional=f.cleaned_data['perfilprofesional'],
                                        requisitotitulacion=f.cleaned_data['requisitotitulacion'],
                                        descripcionintegracioncurricular=f.cleaned_data['descripcionintegracioncurricular'],
                                        pertinencia=f.cleaned_data['pertinencia'],
                                        objetoestudio=f.cleaned_data['objetoestudio'],
                                        metodologiaambiente=f.cleaned_data['metodologiaambiente'],
                                        justificacion=f.cleaned_data['justificacion']
                    )
                    funcionsustantiva.save(request)
                    for aprobacion in f.cleaned_data['aprobaciontrabajo']:
                        funcionsustantiva.aprobaciontrabajo.add(aprobacion)
                    funcionsustantiva.save(request)

                    messages.success(request, 'Se guardó exitosamente.')
                    log(u'Adicionó ProgramaPac: %s' % funcionsustantiva, request, "add")
                    return JsonResponse({"result": "ok","id": encrypt(funcionsustantiva.id)})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editfuncionsustantiva':
            try:
                funcionsustantiva = FuncionSustantivaDocenciaPac.objects.get(pk=int(encrypt(request.POST['id'])))
                f = FuncionSustantivaDocenciaPacForm(request.POST)
                if f.is_valid():
                    funcionsustantiva.objetivogeneral = f.cleaned_data['objetivogeneral']
                    funcionsustantiva.objetivoespecifico = f.cleaned_data['objetivoespecifico']
                    # funcionsustantiva.perfilingreso = f.cleaned_data['perfilingreso']
                    # funcionsustantiva.requisitoingreso = f.cleaned_data['requisitoingreso']
                    funcionsustantiva.perfilprofesional = f.cleaned_data['perfilprofesional']
                    funcionsustantiva.requisitotitulacion = f.cleaned_data['requisitotitulacion']
                    funcionsustantiva.descripcionintegracioncurricular = f.cleaned_data['descripcionintegracioncurricular']
                    funcionsustantiva.pertinencia = f.cleaned_data['pertinencia']
                    funcionsustantiva.objetoestudio = f.cleaned_data['objetoestudio']
                    funcionsustantiva.metodologiaambiente = f.cleaned_data['metodologiaambiente']
                    funcionsustantiva.justificacion = f.cleaned_data['justificacion']
                    funcionsustantiva.aprobaciontrabajo.clear()
                    funcionsustantiva.save(request)
                    for aprobacion in f.cleaned_data['aprobaciontrabajo']:
                        funcionsustantiva.aprobaciontrabajo.add(aprobacion)
                    funcionsustantiva.save(request)

                    messages.success(request, 'Se editó exitosamente.')
                    log(u'Modifico Función Sustantiva: %s' % funcionsustantiva, request, "editfuncionsustantiva")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletefuncionsustantiva':
            try:
                funcionsustantiva = FuncionSustantivaDocenciaPac.objects.get(pk=int(encrypt(request.POST['id'])))
                detfuncionsustantiva = DetalleFuncionSustantivaDocenciaPac.objects.filter(funcionsustantivadocenciapac=funcionsustantiva.id)
                preguntarespuestapac = DetallePreguntasPerfilegresoDocenciaPac.objects.filter(funcionsustantivadocenciapac=funcionsustantiva.id)
                for detfun in detfuncionsustantiva:
                    detfun.delete()
                for pregunta in preguntarespuestapac:
                    p = PreguntasPac.objects.get(pk=pregunta.preguntaspac.id)
                    p.delete()
                log(u'Eliminó FunciónSustantivaDocenciaPac: %s' % funcionsustantiva, request, "del")
                funcionsustantiva.delete()
                messages.success(request, 'Se eliminó exitosamente.')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addperfilingreso':
            try:
                f = DetallePerfilIngresoForm(request.POST)
                if f.is_valid():
                    perfil = DetallePerfilIngreso(
                                 funcionsustantiva_id=int(encrypt(request.POST['funciondocencia'])),
                                 alltitulos=f.cleaned_data['alltitulos'],
                                 experiencia=f.cleaned_data['experiencia'])
                    perfil.save(request)
                    for t in f.cleaned_data['titulo']:
                        perfil.titulo.add(t)
                        #actualiza la tabla campotitulospostulacion
                        campotitulo = None
                        if CamposTitulosPostulacion.objects.filter(status=True, titulo=t).exists():
                            campotitulo = CamposTitulosPostulacion.objects.filter(status=True, titulo=t).first()
                        else:
                            campotitulo = CamposTitulosPostulacion(titulo=t)
                            campotitulo.save(request)
                        if t.areaconocimiento:
                            if not campotitulo.campoamplio.filter(id=t.areaconocimiento.id):
                                campotitulo.campoamplio.add(t.areaconocimiento)
                        if t.subareaconocimiento:
                            if not campotitulo.campoespecifico.filter(id=t.subareaconocimiento.id):
                                campotitulo.campoespecifico.add(t.subareaconocimiento)
                        if t.subareaespecificaconocimiento:
                            if not campotitulo.campodetallado.filter(id=t.subareaespecificaconocimiento.id):
                                campotitulo.campodetallado.add(t.subareaespecificaconocimiento)
                        campotitulo.save()

                    if f.cleaned_data['experiencia']:
                        perfil.cantidadexperiencia = f.cleaned_data['cantidadexperiencia']
                    perfil.save(request)

                    messages.success(request, 'Se adicionó exitosamente.')
                    log(u'Adicionó Detalle Perfil Ingreso: %s' % perfil, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addtitulo':
            try:
                f = TituloPerfilIngresoForm(request.POST)
                if f.is_valid():
                    if Titulo.objects.filter(nombre__unaccent=f.cleaned_data['nombre'].upper()).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El título ya existe."})
                    if Titulo.objects.filter(nombre=f.cleaned_data['nombre'].upper(), nivel=f.cleaned_data['nivel']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El título ya existe."})
                    if f.cleaned_data['nivel'].id ==4 and not f.cleaned_data['grado']:
                        return JsonResponse({"result": "bad", "mensaje": u"Por favor seleccione grado."})

                    titulo = Titulo(nombre=f.cleaned_data['nombre'],
                                    abreviatura=f.cleaned_data['abreviatura'],
                                    areaconocimiento=f.cleaned_data['areaconocimiento'],
                                    subareaconocimiento=f.cleaned_data['subareaconocimiento'],
                                    subareaespecificaconocimiento=f.cleaned_data['subareaespecificaconocimiento'],
                                    nivel=f.cleaned_data['nivel'],
                                    grado=f.cleaned_data['grado'])
                    titulo.save(request)
                    log(u'Adiciono nuevo titulo desde postulacion: %s' % titulo, request, "add")
                    # messages.success(request, 'Se guado exitosamente')
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editperfilingreso':
            try:
                perfil = DetallePerfilIngreso.objects.get(pk=int(encrypt(request.POST['id'])))
                f = DetallePerfilIngresoForm(request.POST)
                if f.is_valid():
                    perfil.alltitulos = f.cleaned_data['alltitulos']
                    perfil.experiencia = f.cleaned_data['experiencia']
                    perfil.titulo.clear()
                    perfil.save(request)

                    for t in f.cleaned_data['titulo']:
                        perfil.titulo.add(t)
                        #actualiza la tabla campotitulospostulacion
                        campotitulo = None
                        if CamposTitulosPostulacion.objects.filter(status=True, titulo=t).exists():
                            campotitulo = CamposTitulosPostulacion.objects.filter(status=True, titulo=t).first()
                        else:
                            campotitulo = CamposTitulosPostulacion(titulo=t)
                            campotitulo.save(request)
                        if t.areaconocimiento:
                            if not campotitulo.campoamplio.filter(id=t.areaconocimiento.id):
                                campotitulo.campoamplio.add(t.areaconocimiento)
                        if t.subareaconocimiento:
                            if not campotitulo.campoespecifico.filter(id=t.subareaconocimiento.id):
                                campotitulo.campoespecifico.add(t.subareaconocimiento)
                        if t.subareaespecificaconocimiento:
                            if not campotitulo.campodetallado.filter(id=t.subareaespecificaconocimiento.id):
                                campotitulo.campodetallado.add(t.subareaespecificaconocimiento)
                        campotitulo.save()

                    if f.cleaned_data['experiencia']:
                        perfil.cantidadexperiencia = f.cleaned_data['cantidadexperiencia']
                    else:
                        perfil.cantidadexperiencia = 0
                    perfil.save(request)
                    messages.success(request, 'Se editó exitosamente')
                    log(u'Modifico Detalle Perfil Ingreso: %s' % perfil, request, "editpreguntasfuncionsustantiva")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteperfilingreso':
            try:
                perfil = DetallePerfilIngreso.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Elimino Detalle Perfil ingreso: %s' % perfil, request, "del")
                perfil.delete()
                messages.success(request, 'Se eliminó exitosamente')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addrequisitoingreso':
            try:
                f = DetalleRequisitoIngresoForm(request.POST)
                if f.is_valid():
                    requi = DetalleRequisitoIngreso(
                                 funcionsustantiva_id=int(encrypt(request.POST['funciondocencia'])),
                                 firmaelectronica=f.cleaned_data['firmaelectronica'])
                    requi.save(request)
                    for r in f.cleaned_data['requisito']:
                        requi.requisito.add(r)
                    requi.save(request)
                    messages.success(request, 'Se adicionó exitosamente.')
                    log(u'Adicionó Detalle Perfil Ingreso: %s' % requi, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editrequisitoingreso':
            try:
                requi = DetalleRequisitoIngreso.objects.get(pk=int(encrypt(request.POST['id'])))
                f = DetalleRequisitoIngresoForm(request.POST)
                if f.is_valid():
                    requi.firmaelectronica = f.cleaned_data['firmaelectronica']
                    requi.requisito.clear()
                    requi.save(request)
                    for r in f.cleaned_data['requisito']:
                        requi.requisito.add(r)
                    requi.save(request)
                    messages.success(request, 'Se editó exitosamente')
                    log(u'Modifico Detalle Requisito Ingreso: %s' % requi, request, "editrequisitoingreso")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleterequisitoingreso':
            try:
                requi = DetalleRequisitoIngreso.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Elimino Detalle Requisito ingreso: %s' % requi, request, "del")
                requi.delete()
                messages.success(request, 'Se eliminó exitosamente')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addpreguntasfuncionsustantiva':
            try:
                preguntapac = PreguntasPac(descripcion=request.POST['preguntaspac'])
                preguntapac.save(request)
                detallepreg = DetallePreguntasPerfilegresoDocenciaPac(
                             funcionsustantivadocenciapac_id=int(encrypt(request.POST['funciondocencia'])),
                             preguntaspac=preguntapac,
                             respuestapac=request.POST['respuestapac'])
                detallepreg.save(request)
                messages.success(request, 'Se adicionó pregunta exitosamente.')
                log(u'Adicionó Pregunta en Función Sustantiva Docencia: %s' % detallepreg, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editpreguntasfuncionsustantiva':
            try:
                detallepreguntapac = DetallePreguntasPerfilegresoDocenciaPac.objects.get(pk=int(encrypt(request.POST['id'])))
                pregunta = PreguntasPac.objects.get(pk=detallepreguntapac.preguntaspac.id)
                f = DetallePreguntasPerfilegresoDocenciaPacForm(request.POST)
                if f.is_valid():
                    pregunta.descripcion = f.cleaned_data['preguntaspac']
                    pregunta.save(request)
                    detallepreguntapac.respuestapac = f.cleaned_data['respuestapac']
                    detallepreguntapac.save(request)
                    messages.success(request, 'Se editó exitosamente')
                    log(u'Modifico Detalle Preguntas Perfil egreso DocenciaPac: %s' % detallepreguntapac, request, "editpreguntasfuncionsustantiva")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletepreguntasfuncionsustantiva':
            try:
                detallepregunta = DetallePreguntasPerfilegresoDocenciaPac.objects.get(pk=int(encrypt(request.POST['id'])))
                pregunta = PreguntasPac.objects.get(pk=detallepregunta.preguntaspac.id)
                log(u'Elimino Detalle Preguntas Perfil egreso DocenciaPac: %s' % detallepregunta.preguntaspac, request, "del")
                pregunta.delete()
                detallepregunta.delete()
                messages.success(request, 'Se eliminó exitosamente')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        # elif action == 'additemdetallefuncionsustantiva':
        #     try:
        #         detalleinf = DetalleFuncionSustantivaDocenciaPac(funcionsustantivadocenciapac_id=request.POST['idfuncion'],
        #                                                          asignatura_id=request.POST['asignatura'],
        #                                                          itinerariomencion=request.POST['itinerario'],
        #                                                          unidadorganizacioncurricular=request.POST['unidad'])
        #         detalleinf.save(request)
        #         listaperiodo = request.POST['periodoacademico'].split(',')
        #         for periodo in listaperiodo:
        #             p = Periodo.objects.get(pk=periodo)
        #             detalleinf.periodoacademico.add(p)
        #             detalleinf.save(request)
        #         log(u'Adicinó detalle de funcion sustantiva: %s' % detalleinf, request, "add")
        #         return JsonResponse({"result": "ok", 'codigoinformedet': detalleinf.id})
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addmicrocurricularfuncionsustantiva':
            try:
                f = DetalleFuncionSustantivaDocenciaPacForm(request.POST)
                if f.is_valid():
                    registros = DetalleFuncionSustantivaDocenciaPac.objects.filter(status=True, funcionsustantivadocenciapac_id=int(encrypt(request.POST['funciondocencia'])))
                    if registros:
                        totalprograma = registros.last().funcionsustantivadocenciapac.programapac.totalhoras
                        total = sum(registros.values_list('horas', flat=True))+int(request.POST['horas'])
                        # if int(total) > int(totalprograma):
                        #     return JsonResponse({"result": "bad", "mensaje": u"No es posible adicionar. Se excede el límite de horas del Programa. Horas restantes: %s"%(int(totalprograma)-int(total))})

                    if DetalleFuncionSustantivaDocenciaPac.objects.values('id').filter(status=True, funcionsustantivadocenciapac_id=int(encrypt(request.POST['funciondocencia'])), asignatura=f.cleaned_data['asignatura']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe Descripción Microcurricular con la asignatura seleccionada."})

                    if f.cleaned_data['horas'] <= 0:
                        return JsonResponse({"result": "bad", "mensaje": u"El total de Horas debe ser mayor que 0"})

                    microcurricularpac = DetalleFuncionSustantivaDocenciaPac(
                            funcionsustantivadocenciapac_id=int(encrypt(request.POST['funciondocencia'])),
                            asignatura=f.cleaned_data['asignatura'],
                            nivelperiodoacademico=f.cleaned_data['nivelperiodoacademico'],
                            # itinerariomencion=f.cleaned_data['itinerariomencion'],
                            unidadorganizacioncurricular=f.cleaned_data['unidadorganizacioncurricular'],

                            horas=f.cleaned_data['horas'],
                            creditos=f.cleaned_data['creditos'],
                            horasacdtotal=f.cleaned_data['horasacdtotal'],
                            horasacdsemanal=f.cleaned_data['horasacdsemanal'],
                            horaspresenciales=f.cleaned_data['horaspresenciales'],
                            horaspresencialessemanales=f.cleaned_data['horaspresencialessemanales'],
                            horasvirtualtotal=f.cleaned_data['horasvirtualtotal'],
                            horasvirtualsemanal=f.cleaned_data['horasvirtualsemanal'],
                            horasapetotal=f.cleaned_data['horasapetotal'],
                            horasapesemanal=f.cleaned_data['horasapesemanal'],
                            horasapeasistotal=f.cleaned_data['horasapeasistotal'],
                            horasapeasissemanal=f.cleaned_data['horasapeasissemanal'],
                            horasapeautototal=f.cleaned_data['horasapeautototal'],
                            horasapeautosemanal=f.cleaned_data['horasapeautosemanal'],
                            horasautonomas=f.cleaned_data['horasautonomas'],
                            horasautonomassemanales=f.cleaned_data['horasautonomassemanales'],
                            horasvinculaciontotal=f.cleaned_data['horasvinculaciontotal'],
                            horasvinculacionsemanal=f.cleaned_data['horasvinculacionsemanal'],
                            horaspppsemanal = f.cleaned_data['horaspppsemanal'],
                            horasppptotal=f.cleaned_data['horasppptotal'],
                            horascolaborativototal=f.cleaned_data['horascolaborativototal'],
                            valorhoramodulo=f.cleaned_data['valorhoramodulo']
                    )
                    microcurricularpac.save(request)
                    #GENERAR CODIGO
                    fun = FuncionSustantivaDocenciaPac.objects.get(pk=int(encrypt(request.POST['funciondocencia'])))
                    pro = ProgramaPac.objects.get(pk=fun.programapac.id)
                    abreviatura = pro.carrera.alias
                    nivel = 0
                    if microcurricularpac.nivelperiodoacademico:
                        nivel = microcurricularpac.nivelperiodoacademico.orden
                    cantidadnivel = DetalleFuncionSustantivaDocenciaPac.objects.filter(funcionsustantivadocenciapac_id=fun.id, nivelperiodoacademico=microcurricularpac.nivelperiodoacademico)
                    codigogenerado = '%s_%s_%s'%(abreviatura,nivel,cantidadnivel.count())
                    microcurricularpac.codigo = codigogenerado
                    microcurricularpac.save(request)
                    #GUARDAR DETALLE CONTENIDOMICRO
                    contenidomicro = request.POST.getlist('contenidomicro[]')
                    if contenidomicro:
                        count = 0
                        while count < len(contenidomicro):
                            contenidominimo = contenidomicro[count]
                            resultadoaprendizaje = contenidomicro[count + 1]
                            if contenidominimo or resultadoaprendizaje:
                                detmicrocurricular = DetalleMicrocurricularPac(
                                                                            detallefuncionsustantivadocenciapac=microcurricularpac,
                                                                            contenidominimo=contenidominimo,
                                                                            resultadoaprendizaje=resultadoaprendizaje)
                                detmicrocurricular.save(request)
                            count += 2
                    log(u'Adicionó detalle Microcurricular en Función Sustantiva Docencia: %s' % microcurricularpac, request, "add")

                # #ACTUALIZAR TOTAL DE HORAS Y CREDITOS DE LA CARRERA
                # microcuriculares =DetalleFuncionSustantivaDocenciaPac.objects.filter(status=True, funcionsustantivadocenciapac_id=int(encrypt(request.POST['funciondocencia'])))
                # totalhorascarrera = 0.00
                # totalcreditoscarrera = 0.0000
                # for total in microcuriculares:
                #     totalhorascarrera = totalhorascarrera + total.horas
                #     totalcreditoscarrera = totalcreditoscarrera +total.creditos
                # pro = ProgramaPac.objects.get(pk=microcuriculares.last().funcionsustantivadocenciapac.programapac.id)
                # pro.totalhoras = totalhorascarrera
                # pro.totalcreditos = totalcreditoscarrera.__round__(4)
                # pro.save(request)
                # log(u'Editó Programa PAC: %s' % pro, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editmicrocurricularfuncionsustantiva':
            try:
                microcurricularpac = DetalleFuncionSustantivaDocenciaPac.objects.get(pk=int(encrypt(request.POST['id'])))
                f = DetalleFuncionSustantivaDocenciaPacForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['horas'] <= 0:
                        return JsonResponse({"result": "bad", "mensaje": u"El total de Horas debe ser mayor que 0"})

                    microcurricularpac.asignatura = f.cleaned_data['asignatura']
                    microcurricularpac.nivelperiodoacademico = f.cleaned_data['nivelperiodoacademico']
                    # microcurricularpac.itinerariomencion = f.cleaned_data['itinerariomencion']
                    microcurricularpac.unidadorganizacioncurricular = f.cleaned_data['unidadorganizacioncurricular']

                    microcurricularpac.horas = f.cleaned_data['horas']
                    microcurricularpac.creditos = f.cleaned_data['creditos']
                    microcurricularpac.horasacdtotal = f.cleaned_data['horasacdtotal']
                    microcurricularpac.horasacdsemanal = f.cleaned_data['horasacdsemanal']
                    microcurricularpac.horaspresenciales = f.cleaned_data['horaspresenciales']
                    microcurricularpac.horaspresencialessemanales = f.cleaned_data['horaspresencialessemanales']
                    microcurricularpac.horasvirtualtotal = f.cleaned_data['horasvirtualtotal']
                    microcurricularpac.horasvirtualsemanal = f.cleaned_data['horasvirtualsemanal']
                    microcurricularpac.horasapetotal = f.cleaned_data['horasapetotal']
                    microcurricularpac.horasapesemanal = f.cleaned_data['horasapesemanal']
                    microcurricularpac.horasapeasistotal = f.cleaned_data['horasapeasistotal']
                    microcurricularpac.horasapeasissemanal = f.cleaned_data['horasapeasissemanal']
                    microcurricularpac.horasapeautototal = f.cleaned_data['horasapeautototal']
                    microcurricularpac.horasapeautosemanal = f.cleaned_data['horasapeautosemanal']
                    microcurricularpac.horasautonomas = f.cleaned_data['horasautonomas']
                    microcurricularpac.horasautonomassemanales = f.cleaned_data['horasautonomassemanales']
                    microcurricularpac.horasvinculaciontotal = f.cleaned_data['horasvinculaciontotal']
                    microcurricularpac.horasvinculacionsemanal = f.cleaned_data['horasvinculacionsemanal']
                    microcurricularpac.horaspppsemanal = f.cleaned_data['horaspppsemanal']
                    microcurricularpac.horasppptotal = f.cleaned_data['horasppptotal']
                    microcurricularpac.horascolaborativototal = f.cleaned_data['horascolaborativototal']
                    microcurricularpac.valorhoramodulo = f.cleaned_data['valorhoramodulo']

                    microcurricularpac.save(request)
                    # #GENERAR CODIGO
                    # fun = FuncionSustantivaDocenciaPac.objects.get(pk=microcurricularpac.funcionsustantivadocenciapac.id)
                    # pro = ProgramaPac.objects.get(pk=fun.programapac.id)
                    # abreviatura = pro.carrera.alias
                    # nivel = microcurricularpac.nivelperiodoacademico.orden
                    # cantidadnivel = DetalleFuncionSustantivaDocenciaPac.objects.filter(funcionsustantivadocenciapac_id=fun.id, nivelperiodoacademico=microcurricularpac.nivelperiodoacademico)
                    # codigogenerado = '%s_%s_%s' % (abreviatura, nivel, cantidadnivel.count())
                    # microcurricularpac.codigo = codigogenerado
                    # microcurricularpac.save(request)

                    #EDITAR DETALLE CONTENIDO MICRO
                    contenidomicroedit = request.POST.getlist('contenidomicroedit[]')
                    idsevaluados = []
                    if contenidomicroedit:
                        countedit = 0
                        while countedit < len(contenidomicroedit):
                            id = contenidomicroedit[countedit]
                            contenidominimo = contenidomicroedit[countedit + 1]
                            resultadoaprendizaje = contenidomicroedit[countedit + 2]
                            detmicro = DetalleMicrocurricularPac.objects.get(pk=id)
                            detmicro.contenidominimo = contenidominimo
                            detmicro.resultadoaprendizaje = resultadoaprendizaje
                            detmicro.save(request)
                            countedit += 3
                            if contenidominimo or resultadoaprendizaje:
                                idsevaluados.append(id)
                    detmicroborrar = DetalleMicrocurricularPac.objects.filter(detallefuncionsustantivadocenciapac=microcurricularpac, status=True).exclude(pk__in=idsevaluados)
                    for detb in detmicroborrar:
                        detb.status = False
                        detb.save(request)
                    contenidomicro = request.POST.getlist('contenidomicro[]')
                    if contenidomicro:
                        count = 0
                        while count < len(contenidomicro):
                            contenidominimo = contenidomicro[count]
                            resultadoaprendizaje = contenidomicro[count + 1]
                            if contenidominimo or resultadoaprendizaje:
                                detmicrocurricular = DetalleMicrocurricularPac(
                                    detallefuncionsustantivadocenciapac=microcurricularpac,
                                    contenidominimo=contenidominimo,
                                    resultadoaprendizaje=resultadoaprendizaje)
                                detmicrocurricular.save(request)
                            count += 2

                    messages.success(request, 'Se editó exitosamente')
                    log(u'Modifico Detalle Función Sustantiva DocenciaPac: %s' % microcurricularpac, request, "editmicrocurricularfuncionsustantiva")

                    # ACTUALIZAR TOTAL DE HORAS Y CREDITOS DE LA CARRERA
                    # allmicrocuriculares = DetalleFuncionSustantivaDocenciaPac.objects.filter(status=True, funcionsustantivadocenciapac_id=microcurricularpac.funcionsustantivadocenciapac.id)
                    # totalhorascarrera = 0.00
                    # totalcreditoscarrera = 0.0000
                    # for total in allmicrocuriculares:
                    #     totalhorascarrera = totalhorascarrera + total.horas
                    #     totalcreditoscarrera = totalcreditoscarrera + total.creditos
                    # pro = ProgramaPac.objects.get(pk=allmicrocuriculares.last().funcionsustantivadocenciapac.programapac.id)
                    # pro.totalhoras = totalhorascarrera
                    # pro.totalcreditos = totalcreditoscarrera.__round__(4)
                    # pro.save(request)
                    # log(u'Editó Programa PAC: %s' % pro, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletemicrocurricularfuncionsustantiva':
            try:
                microcurricularpac = DetalleFuncionSustantivaDocenciaPac.objects.get(pk=int(encrypt(request.POST['id'])))
                detmicro = DetalleMicrocurricularPac.objects.filter(detallefuncionsustantivadocenciapac=microcurricularpac.id, status=True)
                for det in detmicro:
                    det.status = False
                    det.save(request)
                microcurricularpac.status = False
                microcurricularpac.save(request)
                log(u'Elimino Detalle Microcurricular Funcion Sustantiva DocenciaPac: %s' % microcurricularpac, request, "del")

                # ACTUALIZAR TOTAL DE HORAS Y CREDITOS DE LA CARRERA
                # allmicrocuriculares = DetalleFuncionSustantivaDocenciaPac.objects.filter(status=True, funcionsustantivadocenciapac_id=microcurricularpac.funcionsustantivadocenciapac.id)
                # totalhorascarrera = 0.00
                # totalcreditoscarrera = 0.0000
                # if allmicrocuriculares:
                #     for total in allmicrocuriculares:
                #         totalhorascarrera = totalhorascarrera + total.horas
                #         totalcreditoscarrera = totalcreditoscarrera + total.creditos
                #
                #     pro = ProgramaPac.objects.get(pk=allmicrocuriculares.last().funcionsustantivadocenciapac.programapac.id)
                #     pro.totalhoras = totalhorascarrera
                #     pro.totalcreditos = totalcreditoscarrera.__round__(4)
                #     pro.save(request)
                #     log(u'Editó Programa PAC: %s' % pro, request, "edit")
                messages.success(request, 'Se eliminó exitosamente')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'verdetallemicrocurricular':
            try:
                data['detallefuncion'] = detallefuncion = DetalleFuncionSustantivaDocenciaPac.objects.get(pk=int(request.POST['id']))
                data['detallemicro'] = detallemicro = DetalleMicrocurricularPac.objects.filter(status=True, detallefuncionsustantivadocenciapac_id=int(request.POST['id']))
                template = get_template("adm_pac/detallemicrocurricular.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'verresumenmicrocurricular':
            try:
                data['detallefuncion'] = detallefuncion = DetalleFuncionSustantivaDocenciaPac.objects.filter(funcionsustantivadocenciapac_id=int(encrypt(request.POST['id'])))
                data['tasignatura'] = detallefuncion.count()
                thcontactodocente = 0
                thaprendizajeautonomo = 0
                thaprendizajeexperimental = 0
                thpracticasprofesionales = 0
                thcolaborativototal = 0
                duracion = 0
                for det in detallefuncion:
                    thcontactodocente += det.horasacdtotal
                    thaprendizajeautonomo += det.horasautonomas
                    thaprendizajeexperimental += det.horasapetotal
                    # data['unidadtitulacion']= unidadtitulacion
                    thpracticasprofesionales += det.horasppptotal
                    thcolaborativototal += det.horascolaborativototal
                    duracion += det.horas

                data['thcontactodocente']= thcontactodocente
                data['thaprendizajeautonomo']= thaprendizajeautonomo
                data['thaprendizajeexperimental']= thaprendizajeexperimental
                # data['unidadtitulacion']= unidadtitulacion
                data['thpracticasprofesionales']= thpracticasprofesionales
                data['thcolaborativototal']= thcolaborativototal
                data['duracion']= duracion

                template = get_template("adm_pac/resumendescripcionmicrocurricular.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


        # elif action == 'itemdetallefuncionsustantiva':
        #     try:
        #         detallefuncion = DetalleFuncionSustantivaDocenciaPac.objects.get(pk=request.POST['id'])
        #         descripcion = detallefuncion.asignatura.nombre
        #         idobjetivo = detallefuncion.id
        #         return JsonResponse({"result": "ok", 'descripcion': descripcion, 'codigorai': idobjetivo})
        #     except Exception as ex:
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        # elif action == 'eliminaritemdetallefuncionsustantiva':
        #     try:
        #         itemdetalle = DetalleFuncionSustantivaDocenciaPac.objects.get(pk=request.POST['idcodigodet'])
        #         log(u'Eliminó item detalle informe baja: %s' % itemdetalle, request, "del")
        #         itemdetalle.delete()
        #         return JsonResponse({"result": "ok"})
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addfuncioninvestigacion':
            try:
                f = FuncionSustantivaInvestigacionPacForm(request.POST)
                if f.is_valid():
                    funcioninvestigacion = FuncionSustantivaInvestigacionPac(
                                            programapac_id=int(encrypt(request.POST['pro'])),
                                            investigacion=f.cleaned_data['investigacion'])
                    funcioninvestigacion.save(request)
                    messages.success(request, 'Se guardó exitosamente.')
                    log(u'Adiciono FuncionSustantivaInvestigacionPac: %s' % funcioninvestigacion, request, "add")
                    return JsonResponse({"result": "ok", "id": encrypt(funcioninvestigacion.id)})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editfuncioninvestigacion':
            try:
                funcioninvestigacion = FuncionSustantivaInvestigacionPac.objects.get(pk=int(encrypt(request.POST['id'])))
                f = FuncionSustantivaInvestigacionPacForm(request.POST)
                if f.is_valid():
                    funcioninvestigacion.investigacion = f.cleaned_data['investigacion']
                    funcioninvestigacion.save(request)
                    messages.success(request, 'Se editó exitosamente.')
                    log(u'Modifico Función Investigación: %s' % funcioninvestigacion, request, "editfuncioninvestigacion")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletefuncioninvestigacion':
            try:
                funcioninvestigacion = FuncionSustantivaInvestigacionPac.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Eliminó FuncionSustantivaInvestigacionPac: %s' % funcioninvestigacion, request, "del")
                funcioninvestigacion.delete()
                messages.success(request, 'Se eliminó exitosamente.')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addfuncionvinculacion':
            try:
                f = FuncionSustantivaVinculacionSociedadPacForm(request.POST)
                if f.is_valid():
                    funcionvinculacion = FuncionSustantivaVinculacionSociedadPac(
                                        programapac_id=int(encrypt(request.POST['pro'])),
                                        componentevinculacion=f.cleaned_data['componentevinculacion'],
                                        modelopractica=f.cleaned_data['modelopractica'])
                    funcionvinculacion.save(request)
                    messages.success(request, 'Se guardó exitosamente.')
                    log(u'Adiciono FuncionSustantivaVinculacionSociedadPac: %s' % funcionvinculacion, request, "add")
                    return JsonResponse({"result": "ok", "id": encrypt(funcionvinculacion.id)})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editfuncionvinculacion':
            try:
                funcionvinculacion = FuncionSustantivaVinculacionSociedadPac.objects.get(pk=int(encrypt(request.POST['id'])))
                f = FuncionSustantivaVinculacionSociedadPacForm(request.POST)
                if f.is_valid():
                    funcionvinculacion.componentevinculacion = f.cleaned_data['componentevinculacion']
                    funcionvinculacion.modelopractica = f.cleaned_data['modelopractica']
                    funcionvinculacion.save(request)
                    messages.success(request, 'Se editó exitosamente.')
                    log(u'Modifico Funcion Sustantiva Vinculación SociedadPac: %s' % funcionvinculacion, request, "editfuncionvinculacion")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletefuncionvinculacion':
            try:
                funcionvinculacion = FuncionSustantivaVinculacionSociedadPac.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Eliminó FuncionSustantivaVinculacionSociedadPac: %s' % funcionvinculacion, request, "del")
                funcionvinculacion.delete()
                messages.success(request, 'Se eliminó exitosamente.')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addinfraestructuraequipamiento':
            try:
                f = InfraestructuraEquipamientoInformacionPacForm(request.POST)
                if f.is_valid():
                    infraestructurapac = InfraestructuraEquipamientoInformacionPac(
                                        programapac_id=int(encrypt(request.POST['pro'])),
                                        descripcion=f.cleaned_data['descripcion'],

                                        aniosexperiencia=f.cleaned_data['aniosexperiencia'],
                                        numeropublicacion=f.cleaned_data['numeropublicacion'],
                                        dominiotics=f.cleaned_data['dominiotics'],

                                        cargofunciondirector=f.cleaned_data['cargofunciondirector'],
                                        ciudaddirector=f.cleaned_data['ciudaddirector'],
                                        horassemanaies=f.cleaned_data['horassemanaies'],
                                        tiporelacionlaboralies=f.cleaned_data['tiporelacionlaboralies']

                    )
                    infraestructurapac.save(request)

                    messages.success(request, 'Se guardó exitosamente.')
                    log(u'Adicionó InfraestructuraEquipamientoInformacionPac: %s' % infraestructurapac, request, "add")
                    return JsonResponse({"result": "ok","id": encrypt(infraestructurapac.id)})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editinfraestructuraequipamiento':
            try:
                infraestructurapac = InfraestructuraEquipamientoInformacionPac.objects.get(pk=int(encrypt(request.POST['id'])))
                f = InfraestructuraEquipamientoInformacionPacForm(request.POST)
                if f.is_valid():
                    infraestructurapac.descripcion = f.cleaned_data['descripcion']
                    infraestructurapac.aniosexperiencia = f.cleaned_data['aniosexperiencia']
                    infraestructurapac.numeropublicacion = f.cleaned_data['numeropublicacion']
                    infraestructurapac.dominiotics = f.cleaned_data['dominiotics']
                    infraestructurapac.cargofunciondirector = f.cleaned_data['cargofunciondirector']
                    infraestructurapac.ciudaddirector = f.cleaned_data['ciudaddirector']
                    infraestructurapac.horassemanaies = f.cleaned_data['horassemanaies']
                    infraestructurapac.tiporelacionlaboralies = f.cleaned_data['tiporelacionlaboralies']

                    infraestructurapac.save(request)

                    messages.success(request, 'Se editó exitosamente.')
                    log(u'Modifico infraestructura equipamiento e información: %s' % infraestructurapac, request, "editinfraestructuraequipamiento")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteinfraestructuraequipamiento':
            try:
                infraestructurapac = InfraestructuraEquipamientoInformacionPac.objects.get(pk=int(encrypt(request.POST['id'])))
                detinfralaboratorio = DetalleLaboratorioInfraestructuraPac.objects.filter(infraestructuraequipamientopac=infraestructurapac.id)
                detinfrapersonal = DetallePersonalAcademicoInfraestructuraPac.objects.filter(infraestructuraequipamientopac=infraestructurapac.id)
                if detinfralaboratorio:
                    for detalle in detinfralaboratorio:
                        detalle.delete()
                if detinfrapersonal:
                    for detalle in detinfrapersonal:
                        detalle.delete()
                log(u'Eliminó InfraestructuraEquipamientoInformacionPac: %s' % infraestructurapac, request, "del")
                infraestructurapac.delete()
                messages.success(request, 'Se eliminó exitosamente.')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addlaboratorioinfraestructura':
            try:
                f = DetalleLaboratorioInfraestructuraPacForm(request.POST)
                if f.is_valid():
                    detalle = DetalleLaboratorioInfraestructuraPac(infraestructuraequipamientopac_id=int(encrypt(request.POST['infraestructura'])),
                                                                     estructurainstitucional=request.POST['estructurainstitucional'],
                                                                     aulalaboratorio_id=request.POST['aulalaboratorio'],
                                                                     descripcion=request.POST['descripcion'],
                                                                     equipamiento=request.POST['equipamiento'],
                                                                     metroscuadrado=request.POST['metroscuadrado'],
                                                                     puestotrabajo=request.POST['puestotrabajo']
                                                                   )
                    detalle.save(request)
                    messages.success(request, 'Se adicionó Laboratorio y/o taller exitosamente.')
                    log(u'Adicinó detalle laboratorio infraestructuraPac: %s' % detalle, request, "add")
                    return JsonResponse({"result": "ok", 'codigoinformedet': encrypt(detalle.id)})
                else:
                    raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editlaboratorioinfraestructura':
            try:
                laboratoriopac = DetalleLaboratorioInfraestructuraPac.objects.get(pk=int(encrypt(request.POST['id'])))
                f = DetalleLaboratorioInfraestructuraPacForm(request.POST)
                if f.is_valid():
                    laboratoriopac.estructurainstitucional = f.cleaned_data['estructurainstitucional']
                    laboratoriopac.aulalaboratorio = f.cleaned_data['aulalaboratorio']
                    laboratoriopac.descripcion = f.cleaned_data['descripcion']
                    laboratoriopac.equipamiento = f.cleaned_data['equipamiento']
                    laboratoriopac.metroscuadrado = f.cleaned_data['metroscuadrado']
                    laboratoriopac.puestotrabajo = f.cleaned_data['puestotrabajo']
                    laboratoriopac.save(request)
                    messages.success(request, 'Se editó exitosamente')
                    log(u'Modificó Detalle Laboratorio Infraestructura Pac: %s' % laboratoriopac, request, "editlaboratorioinfraestructura")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletelaboratorioinfraestructura':
            try:
                laboratorio = DetalleLaboratorioInfraestructuraPac.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Eliminó detalle laboratorio infraestructuraPac: %s' % laboratorio, request, "del")
                laboratorio.delete()
                messages.success(request, 'Se eliminó exitosamente')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addbibliotecainfraestructura':
            try:
                detalle = DetalleBibliotecaInfraestructuraPac(infraestructuraequipamientopac_id=int(encrypt(request.POST['infraestructura'])),
                                                                 estructurainstitucional=request.POST['estructurainstitucional'],
                                                                 numerotitulo=request.POST['numerotitulo'],
                                                                 titulo=request.POST['titulo'],
                                                                 numerovolumen=request.POST['numerovolumen'],
                                                                 volumen=request.POST['volumen'],
                                                                 numerobasedatos=request.POST['numerobasedatos'],
                                                                 basedatos=request.POST['basedatos'],
                                                                 numerosuscripcion=request.POST['numerosuscripcion'],
                                                                 suscripcionrevista=request.POST['suscripcionrevista']
                                                               )
                detalle.save(request)
                messages.success(request, 'Se adicionó Biblioteca PAC exitosamente.')
                log(u'Adicinó detalle Biblioteca infraestructuraPac: %s' % detalle, request, "add")
                return JsonResponse({"result": "ok", 'codigoinformedet': encrypt(detalle.id)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editbibliotecainfraestructura':
            try:
                bibliotecapac = DetalleBibliotecaInfraestructuraPac.objects.get(pk=int(encrypt(request.POST['id'])))
                f = DetalleBibliotecaInfraestructuraPacForm(request.POST)
                if f.is_valid():
                    bibliotecapac.estructurainstitucional = f.cleaned_data['estructurainstitucional']
                    bibliotecapac.numerotitulo = f.cleaned_data['numerotitulo']
                    bibliotecapac.titulo = f.cleaned_data['titulo']
                    bibliotecapac.numerovolumen = f.cleaned_data['numerovolumen']
                    bibliotecapac.volumen = f.cleaned_data['volumen']
                    bibliotecapac.numerobasedatos = f.cleaned_data['numerobasedatos']
                    bibliotecapac.basedatos = f.cleaned_data['basedatos']
                    bibliotecapac.numerosuscripcion = f.cleaned_data['numerosuscripcion']
                    bibliotecapac.suscripcionrevista = f.cleaned_data['suscripcionrevista']
                    bibliotecapac.save(request)
                    messages.success(request, 'Se editó exitosamente')
                    log(u'Modificó Detalle Biblioteca Infraestructura Pac: %s' % bibliotecapac, request, "editbibliotecainfraestructura")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletebibliotecainfraestructura':
            try:
                bibliotecapac = DetalleBibliotecaInfraestructuraPac.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Eliminó detalle biblioteca infraestructuraPac: %s' % bibliotecapac, request, "del")
                bibliotecapac.delete()
                messages.success(request, 'Se eliminó exitosamente')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addaulainfraestructura':
            try:
                detalle = DetalleAulaInfraestructuraPac( infraestructuraequipamientopac_id=int(encrypt(request.POST['infraestructura'])),
                                                         estructurainstitucional=request.POST['estructurainstitucional'],
                                                         numeroaula=request.POST['numeroaula'],
                                                         numeropuestotrabajoaula=request.POST['numeropuestotrabajoaula']
                                                       )
                detalle.save(request)
                messages.success(request, 'Se adicionó Aula PAC exitosamente.')
                log(u'Adicinó detalle aula infraestructuraPac: %s' % detalle, request, "add")
                return JsonResponse({"result": "ok", 'codigoinformedet': encrypt(detalle.id)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editaulainfraestructura':
            try:
                aulapac = DetalleAulaInfraestructuraPac.objects.get(pk=int(encrypt(request.POST['id'])))
                f = DetalleAulaInfraestructuraPacForm(request.POST)
                if f.is_valid():
                    aulapac.estructurainstitucional = f.cleaned_data['estructurainstitucional']
                    aulapac.numeroaula = f.cleaned_data['numeroaula']
                    aulapac.numeropuestotrabajoaula = f.cleaned_data['numeropuestotrabajoaula']
                    aulapac.save(request)
                    messages.success(request, 'Se editó exitosamente')
                    log(u'Modificó Detalle Aula Infraestructura Pac: %s' % aulapac, request, "editaulainfraestructura")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteaulainfraestructura':
            try:
                aulapac = DetalleAulaInfraestructuraPac.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Eliminó detalle aula infraestructuraPac: %s' % aulapac, request, "del")
                aulapac.delete()
                messages.success(request, 'Se eliminó exitosamente')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addpersonalacademicoinfraestructura':
            try:
                f = DetallePersonalAcademicoInfraestructuraPacForm(request.POST)
                if f.is_valid():
                    detalle = DetallePersonalAcademicoInfraestructuraPac(infraestructuraequipamientopac_id=int(encrypt(request.POST['infraestructura'])),

                                                                         aniosexperiencia=f.cleaned_data['aniosexperiencia'],
                                                                         numeropublicacion=f.cleaned_data['numeropublicacion'],
                                                                         dominiotics=f.cleaned_data['dominiotics'],

                                                                         asignaturaimpartir=f.cleaned_data['asignaturaimpartir'],
                                                                         ciudadpersonalacademico=f.cleaned_data['ciudadpersonalacademico'],
                                                                         horadedicacionies=f.cleaned_data['horadedicacionies'],
                                                                         horadedicacionsemanal=f.cleaned_data['horadedicacionsemanal'],
                                                                         tiempodedicacioncarrera=f.cleaned_data['tiempodedicacioncarrera'],
                                                                         tipopersonalcategoria=f.cleaned_data['tipopersonalcategoria']
                                                                       )
                    detalle.save(request)
                    messages.success(request, 'Se adicionó Personal Académico exitosamente.')
                    log(u'Adicinó Detalle Personal Académico Infraestructura PAC: %s' % detalle, request, "add")
                    return JsonResponse({"result": "ok", 'codigoinformedet': encrypt(detalle.id)})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addperfilacademico':
            try:
                with transaction.atomic():
                    if PerfilRequeridoPac.objects.filter(personalacademico_id=request.POST['id'], titulacion=request.POST['titulacion'],status=True).exists():
                        transaction.set_rollback(True)
                        messages.error(request, 'Ya se encuentra registrado.')
                        return JsonResponse({'error': True, "message": 'Titulación ya se encuentra registrada.'}, safe=False)
                    f = PerfilRequeridoPacForm(request.POST)
                    if f.is_valid():
                        perfil = PerfilRequeridoPac(personalacademico_id=request.POST['id'],
                                                    titulacion=f.cleaned_data['titulacion'])
                        perfil.save(request)
                        messages.success(request, 'Se adicionó exitosamente.')
                        log(u'Adicinó Perfil Requerido PAC: %s' % perfil, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                    #     return JsonResponse({"result": False}, safe=False)
                    # else:
                    #     return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addperfildirector':
            try:
                with transaction.atomic():
                    if PerfilRequeridoDirectorPac.objects.filter(infraestructuradirector_id=request.POST['id'], titulacion=request.POST['titulacion'],status=True).exists():
                        transaction.set_rollback(True)
                        messages.error(request, 'Ya se encuentra registrado.')
                        return JsonResponse({'error': True, "message": 'Titulación ya se encuentra registrada.'}, safe=False)
                    f = PerfilRequeridoPacForm(request.POST)
                    if f.is_valid():
                        perfil = PerfilRequeridoDirectorPac(infraestructuradirector_id=request.POST['id'],
                                                    titulacion=f.cleaned_data['titulacion'])
                        perfil.save(request)
                        messages.success(request, 'Se adicionó exitosamente.')
                        log(u'Adicinó Perfil Requerido Director PAC: %s' % perfil, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteperfilacademico':
            try:
                detalle = PerfilRequeridoPac.objects.get(pk=request.POST['id'])
                log(u'Eliminó Perfil Requerido Pac: %s' % detalle, request, "del")
                detalle.delete()
                messages.success(request, 'Se eliminó exitosamente')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'deleteperfildirector':
            try:
                detalle = PerfilRequeridoDirectorPac.objects.get(pk=request.POST['id'])
                log(u'Eliminó Perfil Requerido Director Pac: %s' % detalle, request, "del")
                detalle.delete()
                messages.success(request, 'Se eliminó exitosamente')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'editpersonalacademicoinfraestructura':
            try:
                personalpac = DetallePersonalAcademicoInfraestructuraPac.objects.get(pk=int(encrypt(request.POST['id'])))
                f = DetallePersonalAcademicoInfraestructuraPacForm(request.POST)
                if f.is_valid():
                    # personalpac.perfildocente = f.cleaned_data['perfildocente']
                    personalpac.aniosexperiencia = f.cleaned_data['aniosexperiencia']
                    personalpac.numeropublicacion = f.cleaned_data['numeropublicacion']
                    personalpac.dominiotics = f.cleaned_data['dominiotics']

                    personalpac.asignaturaimpartir = f.cleaned_data['asignaturaimpartir']
                    personalpac.ciudadpersonalacademico = f.cleaned_data['ciudadpersonalacademico']
                    personalpac.horadedicacionies = f.cleaned_data['horadedicacionies']
                    personalpac.horadedicacionsemanal = f.cleaned_data['horadedicacionsemanal']
                    personalpac.tiempodedicacioncarrera = f.cleaned_data['tiempodedicacioncarrera']
                    personalpac.tipopersonalcategoria = f.cleaned_data['tipopersonalcategoria']
                    personalpac.save(request)
                    messages.success(request, 'Se editó exitosamente')
                    log(u'Modificó Personal Académico Infraestructura Pac: %s' % personalpac, request, "editpersonalacademicoinfraestructura")
                    return JsonResponse({"result": "ok"})
                else:
                    pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletepersonalacademicoinfraestructura':
            try:
                personalpac = DetallePersonalAcademicoInfraestructuraPac.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Eliminó detalle personal infraestructuraPac: %s' % personalpac, request, "del")
                personalpac.delete()
                messages.success(request, 'Se eliminó exitosamente')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'cargaradicionartipopersonal':
            try:
                data['form'] = TipoPersonalPacForm()
                template = get_template('adm_pac/infraestructura/addtipopersonal.html')
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

        elif action == 'addTipoPersonal':
            try:
                f = TipoPersonalPacForm(request.POST)
                if f.is_valid():
                    if TipoPersonalPac.objects.filter(descripcion__unaccent=f.cleaned_data['descripcion']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El registro ya existe."})
                    tipop = TipoPersonalPac(descripcion=f.cleaned_data['descripcion'])
                    tipop.save(request)
                    log(u'Adiciono nuevo Tipo personal Pac: %s' % tipop, request, "add")
                    messages.success(request, 'Se guardó nuevo Tipo de personal exitosamente')
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'listar_asignaturapersonalacademicoinfraestructura':
            try:
                listaeditar =[]
                if request.POST['idasignaturaeditar']:
                    listaeditar.append(request.POST['idasignaturaeditar'])
                detallepersonalinfra = DetallePersonalAcademicoInfraestructuraPac.objects.filter(infraestructuraequipamientopac=request.POST['infraestructura'], status=True).exclude(pk__in=listaeditar)
                listx = []
                for x in detallepersonalinfra:
                    listx.append(x.asignaturaimpartir.id)
                detallefuncion = DetalleFuncionSustantivaDocenciaPac.objects.filter(funcionsustantivadocenciapac=request.POST['funcion'], status=True).exclude(pk__in=listx)
                lista = []
                for asig in detallefuncion:
                    lista.append([asig.id, str(asig)])

                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'addinformacionfianciera':
            try:
                mensajeaccion = 'Adiciono'
                costo = request.POST.getlist('costos[]')
                gastos = request.POST.getlist('gastos[]')
                inversion = request.POST.getlist('inversion[]')
                if gastos or inversion or costo:

                    countc = 0
                    while countc < len(costo):
                        valormatricula = costo[countc]
                        porcentajeminpagomatricula = costo[countc + 1]
                        valorarancel = costo[countc + 2]
                        maxnumcuota = costo[countc + 3]
                        valortotalprograma = costo[countc + 4]
                        if valorarancel and valormatricula and porcentajeminpagomatricula and maxnumcuota:
                            if InfraestructuraEquipamientoInformacionPac.objects.filter(pk=int(encrypt(request.POST['infraestructura']))).exists():
                                infra = InfraestructuraEquipamientoInformacionPac.objects.filter(pk=int(encrypt(request.POST['infraestructura']))).last()
                                infra.valormatricula = float(valormatricula)
                                infra.valorarancel = float(valorarancel)
                                infra.porcentajeminpagomatricula = int(porcentajeminpagomatricula)
                                infra.maxnumcuota = int(maxnumcuota)
                                infra.valortotalprograma = float(valortotalprograma)
                                infra.save(request)
                                log(u'Editó Infraestructura Equipamiento Informacion Pac: %s' % (infra), request, "edit")
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, ingrese todos los campos."})
                        countc += 5

                    countg = 0
                    while countg < len(gastos):
                        idcolumnafila = gastos[countg]
                        valor = gastos[countg + 1]
                        if valor:
                            separarid = idcolumnafila.split(sep='_')
                            if InformacionfinancieraPac.objects.filter(infraestructurapac_id=int(encrypt(request.POST['infraestructura'])),presupuestoColumna_id=separarid[0], presupuestoFila_id=separarid[1]).exists():
                                info = InformacionfinancieraPac.objects.filter(infraestructurapac_id=int(encrypt(request.POST['infraestructura'])),presupuestoColumna_id=separarid[0], presupuestoFila_id=separarid[1]).last()
                                info.valorpresupuesto=float(valor)
                                info.save(request)
                                mensajeaccion = 'editó'
                            else:
                                info = InformacionfinancieraPac(
                                                                infraestructurapac_id= int(encrypt(request.POST['infraestructura'])),
                                                                presupuestoColumna_id=separarid[0],
                                                                presupuestoFila_id=separarid[1],
                                                                valorpresupuesto=float(valor)
                                                                )
                                info.save(request)
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, ingrese todos los campos."})
                        countg += 2

                    counti = 0
                    while counti < len(inversion):
                        idcolumnafila = inversion[counti]
                        valor = inversion[counti + 1]
                        if valor:
                            separarid = idcolumnafila.split(sep='_')
                            if InformacionfinancieraPac.objects.filter(infraestructurapac_id=int(encrypt(request.POST['infraestructura'])),presupuestoColumna_id=separarid[0], presupuestoFila_id=separarid[1]).exists():
                                info = InformacionfinancieraPac.objects.filter(infraestructurapac_id=int(encrypt(request.POST['infraestructura'])),presupuestoColumna_id=separarid[0], presupuestoFila_id=separarid[1]).last()
                                info.valorpresupuesto=float(valor)
                                info.save(request)
                                mensajeaccion = 'editó'
                            else:
                                info = InformacionfinancieraPac(
                                    infraestructurapac_id=int(encrypt(request.POST['infraestructura'])),
                                    presupuestoColumna_id=separarid[0],
                                    presupuestoFila_id=separarid[1],
                                    valorpresupuesto=float(valor)
                                )
                                info.save(request)
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, ingrese todos los campos."})
                        counti += 2
                    log(u'%s Informacion Financiera Pac: %s' % (mensajeaccion,info), request, "add")
                    messages.success(request, 'Se %s Información financiera exitosamente.'%mensajeaccion)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteinformacionfinaciera':
            try:
                infraestructurapac = InfraestructuraEquipamientoInformacionPac.objects.get(pk=int(encrypt(request.POST['id'])))
                infraestructurapac.valormatricula = 0
                infraestructurapac.valorarancel = 0
                infraestructurapac.porcentajeminpagomatricula = 0
                infraestructurapac.maxnumcuota = 0
                infraestructurapac.formapagopac.clear()
                infraestructurapac.save(request)
                log(u'Editó Infraestructura Equipamiento Información Pac: %s' % infraestructurapac, request, "edit")
                infofinaciera = InformacionfinancieraPac.objects.filter(infraestructurapac_id=infraestructurapac.id)
                if infofinaciera:
                    for info in infofinaciera:
                        info.delete()
                log(u'Eliminó Informacion financiera Pac: %s' % infofinaciera, request, "del")
                messages.success(request, 'Se eliminó exitosamente.')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'addtipo':
            try:
                with transaction.atomic():
                    if TipoFormacionRediseno.objects.filter(descripcion=(request.POST['descripcion']).upper(),tipo= request.POST['tipo'],status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'Tipo ya se encuentra registrado.'}, safe=False)
                    form = TipoFormacionRedisenoForm(request.POST)
                    if form.is_valid():
                        instance = TipoFormacionRediseno(descripcion=form.cleaned_data['descripcion'],
                                                         tipo = form.cleaned_data['tipo'])
                        instance.save(request)
                        messages.success(request, 'Registro adicionado correctamente.')
                        log(u'Adicionó tipo de formación: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'edittipo':
            try:
                with transaction.atomic():
                    instance = TipoFormacionRediseno.objects.get(pk=request.POST['id'])
                    f = TipoFormacionRedisenoForm(request.POST)
                    if f.is_valid():
                        instance.descripcion = f.cleaned_data['descripcion']
                        instance.tipo = f.cleaned_data['tipo']
                        instance.save(request)
                        messages.success(request, 'Registro editado correctamente.')
                        log(u'Editó tipo de formación: %s' % instance, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'addcolumnainformacionfinanciera':
            try:
                with transaction.atomic():
                    if PresupuestoPacColumna.objects.filter(tipo=(request.POST['tipo']).upper(),descripcioncol= request.POST['descripcioncol'],status=True).exists():
                        transaction.set_rollback(True)
                        messages.error(request, 'Ya se encuentra registrado.')
                        return JsonResponse({'error': True, "message": 'Tipo ya se encuentra registrado.'}, safe=False)
                    form = PresupuestoPacColumnaForm(request.POST)
                    if form.is_valid():
                        columnapac = PresupuestoPacColumna(tipo=form.cleaned_data['tipo'],
                                                           descripcioncol=form.cleaned_data['descripcioncol'],
                                                           orden=form.cleaned_data['orden'])
                        columnapac.save(request)
                        log(u'Adiciono Presupuesto Pac Columna: %s' % columnapac, request, "add")
                        messages.success(request, 'Registro adicionado correctamente.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcolumnainformacionfinanciera':
            try:
                with transaction.atomic():
                    instance = PresupuestoPacColumna.objects.get(pk=request.POST['id'])
                    f = PresupuestoPacColumnaForm(request.POST)
                    if f.is_valid():
                        instance.descripcioncol = f.cleaned_data['descripcioncol']
                        instance.tipo = f.cleaned_data['tipo']
                        instance.orden = f.cleaned_data['orden']
                        instance.save(request)
                        log(u'Editó Presupuesto Pac Columna: %s' % instance, request, "edit")
                        messages.success(request, 'Registro modificado correctamente.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'delcolumnainformacionfinanciera':
            try:
                col = PresupuestoPacColumna.objects.get(pk=request.POST['id'])
                if col.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": u"Presupuesto Pac Columna en uso."})
                col.delete()
                log(u'Eliminó PresupuestoPac Columna: %s' % col, request, "del")
                messages.success(request, 'Se eliminó correctamente.')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addfilainformacionfinanciera':
            try:
                with transaction.atomic():
                    if PresupuestoPacFila.objects.filter(descripcionfila=request.POST['descripcionfila'], status=True).exists():
                        transaction.set_rollback(True)
                        messages.error(request, 'Ya se encuentra registrado.')
                        return JsonResponse({'error': True, "message": 'Tipo ya se encuentra registrado.'}, safe=False)
                    form = PresupuestoPacFilaForm(request.POST)
                    if form.is_valid():
                        filapac = PresupuestoPacFila(descripcionfila=form.cleaned_data['descripcionfila'],
                                                           orden=form.cleaned_data['orden'])
                        filapac.save(request)
                        log(u'Adiciono Presupuesto Pac Fila: %s' % filapac, request, "add")
                        messages.success(request, 'Registro adicionado correctamente.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editfilainformacionfinanciera':
            try:
                with transaction.atomic():
                    instance = PresupuestoPacFila.objects.get(pk=request.POST['id'])
                    f = PresupuestoPacFilaForm(request.POST)
                    if f.is_valid():
                        instance.descripcionfila = f.cleaned_data['descripcionfila']
                        instance.orden = f.cleaned_data['orden']
                        instance.save(request)
                        log(u'Editó Presupuesto Pac Fila: %s' % instance, request, "edit")
                        messages.success(request, 'Registro modificado correctamente.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'delfilainformacionfinanciera':
            try:
                fila = PresupuestoPacFila.objects.get(pk=request.POST['id'])
                if fila.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": u"Presupuesto Pac fila en uso."})
                fila.delete()
                log(u'Eliminó PresupuestoPac Fila: %s' % fila, request, "del")
                messages.success(request, 'Se eliminó correctamente.')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addtipoformapago':
            try:
                f = TipoFormaPagoPacForm(request.POST)
                if f.is_valid():
                    if TipoFormaPagoPac.objects.filter(descripcion=request.POST['descripcion'], status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra registrado."})
                    tformap = TipoFormaPagoPac(descripcion=f.cleaned_data['descripcion'])
                    tformap.save(request)
                    log(u'Adicinó Tipo Forma de Pago: %s' % tformap, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        elif action == 'addformapagopac':
            try:
                f = FormaPagoPacForm(request.POST)
                if f.is_valid():
                    if InfraestructuraEquipamientoInformacionPac.objects.filter(pk=int(encrypt(request.POST['infraestructura']))).exists():
                        infra = InfraestructuraEquipamientoInformacionPac.objects.filter(pk=int(encrypt(request.POST['infraestructura']))).last()
                        infra.formapagopac.clear()
                        for fp in f.cleaned_data['formapago']:
                            infra.formapagopac.add(fp)
                        infra.save(request)
                        log(u'Editó Infraestructura Equipamiento Informacion Pac: %s' % (infra), request, "edit")
                        messages.success(request, 'Forma de pago registrado exitosamente.')
                        return JsonResponse({"result": "ok"})
                    else:
                        pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'imprimir_campos_pac':
            try:

                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('gestion_titulacion_pac')
                response = HttpResponse(content_type="application/ms-excel")
                columns = [
                    (u"N.", 1500),
                    (u"NIVEL DE FORMACIÓN", 10000),
                    (u"CÓDIGO CAMPO AMPLIO", 7000),
                    (u"DESCRIPCIÓN CAMPO AMPLIO", 10000),
                    (u"CÓDIGO CAMPO ESPECÍFICO", 8000),
                    (u"DESCRIPCION CAMPO ESPECÍFICO", 10000),
                    (u"CÓDIGO CAMPO DETALLADO", 8000),
                    (u"DESCRIPCIÓN CAMPO DETALLADO", 16000),
                    (u"CÓDIGO CARRERA", 6000),
                    (u"DESCRIPCIÓN CARRERA", 16000),
                    (u"CÓDIGO TITULACIÓN", 6000),
                    (u"TÍTULO OBTENIDO HOMBRE ", 26000),
                    (u"TÍTULO OBTENIDO MUJER", 26000),
                ]

                response['Content-Disposition'] = 'attachment; filename=gestion_titulacion_pac' + random.randint(1, 10000).__str__() + '.xls'
                style_title = xlwt.easyxf(
                    'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                style_title_2 = xlwt.easyxf(
                    'font: height 250, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                ws.write_merge(0, 0, 0, len(columns), 'UNIVERSIDAD ESTATAL DE MILAGRO', style_title)
                ws.write_merge(1, 1, 0, len(columns),
                               'LISTADO DE MATRIZ DE TITULACIÓN',
                               style_title_2)
                row_num = 3
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                    ws.col(col_num).width = columns[col_num][1]
                date_format = xlwt.XFStyle()
                date_format.num_format_str = 'yyyy/mm/dd'
                titulaciones = TitulacionPac.objects.filter(status=True)
                row_num = 4

                for i, titulacion in enumerate(titulaciones):

                    campo1 = titulacion.nivelformacion.descripcion

                    campo2 = titulacion.carrerapac.campodetalladopac.campoespecificopac.campoampliopac.codigo
                    campo3 = titulacion.carrerapac.campodetalladopac.campoespecificopac.campoampliopac.descripcion

                    campo4 = titulacion.carrerapac.campodetalladopac.campoespecificopac.codigo
                    campo5 = titulacion.carrerapac.campodetalladopac.campoespecificopac.descripcion

                    campo6 = titulacion.carrerapac.campodetalladopac.codigo
                    campo7 = titulacion.carrerapac.campodetalladopac.descripcion

                    campo8 = titulacion.carrerapac.codigo
                    campo9 = titulacion.carrerapac.descripcion

                    campo10 = titulacion.codigo
                    campo11 = titulacion.tituloobtenidohombre
                    campo12 = titulacion.tituloobtenidomujer

                    ws.write(row_num, 0, i+1, font_style2)
                    ws.write(row_num, 1, campo1, font_style2)
                    ws.write(row_num, 2, campo2, font_style2)
                    ws.write(row_num, 3, campo3, font_style2)
                    ws.write(row_num, 4, campo4, font_style2)
                    ws.write(row_num, 5, campo5, font_style2)
                    ws.write(row_num, 6, campo6, font_style2)
                    ws.write(row_num, 7, campo7, font_style2)
                    ws.write(row_num, 8, campo8, font_style2)
                    ws.write(row_num, 9, campo9, font_style2)
                    ws.write(row_num, 10, campo10, font_style2)
                    ws.write(row_num, 11, campo11, font_style2)
                    ws.write(row_num, 12, campo12, font_style2)

                    row_num += 1
                wb.save(response)
                return response
            except Exception as ex:
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg = ex.__str__()
                msg = f'{msg} {err}'

                return JsonResponse({"result": "bad", "mensaje": u"Error: %s"%msg})

        elif action == 'imprimir_perfilingresopac':
            try:

                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('perfil_ingreso_pac')
                response = HttpResponse(content_type="application/ms-excel")
                columns = [
                    (u"N.", 1500),
                    (u"PROGRAMA O MAESTRÍA", 19000),
                    (u"TÍTULO", 23000),
                    (u"CAMPO AMPLIO", 16000),
                    (u"CAMPO ESPECÍFICO", 16000),
                    (u"CAMPO DETALLADO", 18000),
                    (u"AÑOS DE EXPERIENCIA", 6600),
                ]
                response['Content-Disposition'] = 'attachment; filename=perfil_ingreso_pac' + random.randint(1, 10000).__str__() + '.xls'
                style_title = xlwt.easyxf(
                    'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                style_title_2 = xlwt.easyxf(
                    'font: height 250, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                ws.write_merge(0, 0, 0, len(columns), 'UNIVERSIDAD ESTATAL DE MILAGRO', style_title)
                ws.write_merge(1, 1, 0, len(columns),
                               'REPORTE DE PERFIL DE INGRESO DE PROGRAMA',
                               style_title_2)
                row_num = 3
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                    ws.col(col_num).width = columns[col_num][1]
                date_format = xlwt.XFStyle()
                date_format.num_format_str = 'yyyy/mm/dd'
                # perfil = DetallePerfilIngreso.objects.filter(status=True)
                perfil = ProgramaPac.objects.filter(status=True)
                row_num = 4

                for i, p in enumerate(perfil):
                    sinregistro = False
                    x = p.funcionsustantivadocenciapac_set.last()
                    if x:
                        if x.detalleperfilingreso_set.last():
                            if x.detalleperfilingreso_set.last().alltitulos:
                                ws.write(row_num, 0, i + 1, font_style2)
                                ws.write(row_num, 1, p.carrera.nombre, font_style2)
                                ws.write(row_num, 2, 'TODO TÍTULO DE TERCER NIVEL O SUPERIOR', font_style2)
                                ws.write(row_num, 3, 'NINGUNO', font_style2)
                                ws.write(row_num, 4, 'NINGUNO', font_style2)
                                ws.write(row_num, 5, 'NINGUNO', font_style2)
                                if x.detalleperfilingreso_set.last().experiencia:
                                    cantidad = x.detalleperfilingreso_set.last().cantidadexperiencia
                                else:
                                    cantidad = 'NO REQUIERE EXPERIENCIA'
                                ws.write(row_num, 6, cantidad, font_style2)
                                row_num += 1
                            else:
                                for t in x.detalleperfilingreso_set.last().titulo.all():
                                    ws.write(row_num, 0, i + 1, font_style2)
                                    ws.write(row_num, 1, p.carrera.nombre, font_style2)
                                    ws.write(row_num, 2, str(t) if t else '', font_style2)
                                    ws.write(row_num, 3, str(t.areaconocimiento), font_style2)
                                    ws.write(row_num, 4, str(t.subareaconocimiento) if t.subareaconocimiento else '', font_style2)
                                    ws.write(row_num, 5, str(t.subareaespecificaconocimiento) if t.subareaespecificaconocimiento else '', font_style2)
                                    if x.detalleperfilingreso_set.last().experiencia:
                                        cantidad = x.detalleperfilingreso_set.last().cantidadexperiencia
                                    else:
                                        cantidad = 'NO REQUIERE EXPERIENCIA'
                                    ws.write(row_num, 6, cantidad, font_style2)
                                    row_num += 1
                        else:
                            sinregistro=True
                    else:
                        sinregistro=True

                    if sinregistro:
                        ws.write(row_num, 0, i + 1, font_style2)
                        ws.write(row_num, 1, p.carrera.nombre, font_style2)
                        ws.write(row_num, 2, 'SIN REGISTRO', font_style2)
                        ws.write(row_num, 3, 'SIN REGISTRO', font_style2)
                        ws.write(row_num, 4, 'SIN REGISTRO', font_style2)
                        ws.write(row_num, 5, 'SIN REGISTRO', font_style2)
                        ws.write(row_num, 6, 'SIN REGISTRO', font_style2)
                        row_num += 1

                wb.save(response)
                return response
            except Exception as ex:
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg = ex.__str__()
                msg = f'{msg} {err}'

                return JsonResponse({"result": "bad", "mensaje": u"Error: %s"%msg})

        elif action == 'imprimir_perfildocentepac':
            try:
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('perfil_docente_pac')
                response = HttpResponse(content_type="application/ms-excel")
                columns = [
                    (u"N.", 1500),
                    (u"PROGRAMA O MAESTRÍA", 19000),
                    (u"ASIGNATURA", 18000),
                    (u"TÍTULO", 23000),
                    (u"CAMPO AMPLIO", 16000),
                    (u"CAMPO ESPECÍFICO", 16000),
                    (u"CAMPO DETALLADO", 18000),
                ]
                response['Content-Disposition'] = 'attachment; filename=perfil_docente_pac' + random.randint(1, 10000).__str__() + '.xls'
                style_title = xlwt.easyxf(
                    'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                style_title_2 = xlwt.easyxf(
                    'font: height 250, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                ws.write_merge(0, 0, 0, len(columns), 'UNIVERSIDAD ESTATAL DE MILAGRO', style_title)
                ws.write_merge(1, 1, 0, len(columns),
                               'REPORTE DE PERFIL DE DOCENTES POR PROGRAMA',
                               style_title_2)
                row_num = 3
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                    ws.col(col_num).width = columns[col_num][1]
                date_format = xlwt.XFStyle()
                date_format.num_format_str = 'yyyy/mm/dd'
                perfil = ProgramaPac.objects.filter(status=True)
                row_num = 4

                for i, p in enumerate(perfil):
                    sinregistro = False
                    estructura = p.infraestructuraequipamientoinformacionpac_set.last()
                    if estructura:
                        if estructura.detallepersonalacademicoinfraestructurapac_set.all():
                            for personal in estructura.detallepersonalacademicoinfraestructurapac_set.all():
                                if personal.perfilrequeridopac_set.all():
                                    for perfil in personal.perfilrequeridopac_set.all():
                                        ws.write(row_num, 0, i + 1, font_style2)
                                        ws.write(row_num, 1, p.carrera.nombre, font_style2)
                                        ws.write(row_num, 2, str(perfil.personalacademico.asignaturaimpartir.asignatura) if perfil.personalacademico.asignaturaimpartir.asignatura else '', font_style2)
                                        ws.write(row_num, 3, str(perfil.titulacion) if perfil.titulacion else ' --- ', font_style2)
                                        campoamplio = 'NINGUNO'
                                        if perfil.titulacion.campoamplio.all():
                                            campoamplio = ''
                                            for ca in perfil.titulacion.campoamplio.all():
                                                campoamplio = campoamplio + ' * ' + str(ca) + '\n'
                                        ws.write(row_num, 4, campoamplio, font_style2)
                                        campoespecifico = 'NINGUNO'
                                        if perfil.titulacion.campoespecifico.all():
                                            campoespecifico = ''
                                            for ce in perfil.titulacion.campoespecifico.all():
                                                campoespecifico = campoespecifico + ' * ' + str(ce) + '\n'
                                        ws.write(row_num, 5, campoespecifico, font_style2)
                                        campodetallado = 'NINGUNO'
                                        if perfil.titulacion.campodetallado.all():
                                            campodetallado = ''
                                            for cd in perfil.titulacion.campodetallado.all():
                                                campodetallado = campodetallado + ' * ' + str(cd) + '\n'
                                        ws.write(row_num, 6, campodetallado, font_style2)
                                        row_num += 1
                                else:
                                    sinregistro=True
                        else:
                            sinregistro=True
                    else:
                        sinregistro=True

                    if sinregistro:
                        ws.write(row_num, 0, i + 1, font_style2)
                        ws.write(row_num, 1, p.carrera.nombre, font_style2)
                        ws.write(row_num, 2, 'SIN REGISTRO', font_style2)
                        ws.write(row_num, 3, 'SIN REGISTRO', font_style2)
                        ws.write(row_num, 4, 'SIN REGISTRO', font_style2)
                        ws.write(row_num, 5, 'SIN REGISTRO', font_style2)
                        ws.write(row_num, 6, 'SIN REGISTRO', font_style2)
                        row_num += 1

                wb.save(response)
                return response
            except Exception as ex:
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg = ex.__str__()
                msg = f'{msg} {err}'

                return JsonResponse({"result": "bad", "mensaje": u"Error: %s"%msg})

        elif action == 'imprimir_financiamientopac':
            try:
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('registro_financiamiento_pac')
                response = HttpResponse(content_type="application/ms-excel")
                columns = [
                    (u"N.", 1500),
                    (u"PROGRAMA O MAESTRÍA", 19000),

                    (u"VALOR DE MATRÍCULA", 5500),
                    (u"% MÍNIMO DE PAGO", 5050),
                    (u"VALOR DE ARANCEL", 5050),
                    (u"NÚMERO MÁX. DE CUOTAS", 6350),

                    (u"TOTAL GASTOS CORRIENTES", 7000),
                    (u"TOTAL INVERSIÓN", 4800),
                    (u"TOTAL PRESUPUESTO", 5450),
                    (u"FORMAS DE PAGO", 10000),
                ]
                response['Content-Disposition'] = 'attachment; filename=registro_financiamiento_pac' + random.randint(1, 10000).__str__() + '.xls'
                style_title = xlwt.easyxf(
                    'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                style_title_2 = xlwt.easyxf(
                    'font: height 250, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                ws.write_merge(0, 0, 0, len(columns), 'UNIVERSIDAD ESTATAL DE MILAGRO', style_title)
                ws.write_merge(1, 1, 0, len(columns),
                               'REPORTE DE FINANCIAMIENTO POR PROGRAMA',
                               style_title_2)
                row_num = 3
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                    ws.col(col_num).width = columns[col_num][1]
                date_format = xlwt.XFStyle()
                date_format.num_format_str = 'yyyy/mm/dd'
                perfil = ProgramaPac.objects.filter(status=True)
                row_num = 4

                for i, p in enumerate(perfil):
                    sinregistro = False
                    estructura = p.infraestructuraequipamientoinformacionpac_set.last()
                    if estructura:
                        if estructura.informacionfinancierapac_set.all():
                            subtotalgasto = estructura.informacionfinancierapac_set.filter(status=True, presupuestoColumna__tipo=1).order_by('-id')
                            subtotalinversion = estructura.informacionfinancierapac_set.filter(status=True, presupuestoColumna__tipo=2).order_by('-id')
                            if subtotalgasto or subtotalinversion:
                                subtg = 0.00
                                subti = 0.00
                                totalpresupuesto = 0.00
                                for sub in subtotalgasto:
                                    subtg = sub.valorpresupuesto.__round__(2) + subtg.__round__(2)
                                for sub in subtotalinversion:
                                    subti = sub.valorpresupuesto.__round__(2) + subti.__round__(2)
                                totalpresupuesto = subtg + subti

                                ws.write(row_num, 0, i + 1, font_style2)
                                ws.write(row_num, 1, p.carrera.nombre, font_style2)

                                ws.write(row_num, 2, estructura.valormatricula if estructura.valormatricula else 0, font_style2)
                                ws.write(row_num, 3, estructura.porcentajeminpagomatricula if estructura.porcentajeminpagomatricula else 0, font_style2)
                                ws.write(row_num, 4, estructura.valorarancel if estructura.valorarancel else 0, font_style2)
                                ws.write(row_num, 5, estructura.maxnumcuota if estructura.maxnumcuota else 0, font_style2)

                                ws.write(row_num, 6, subtg if subtg else 0, font_style2)
                                ws.write(row_num, 7, subti if subti else 0, font_style2)
                                ws.write(row_num, 8, totalpresupuesto.__round__(2) if totalpresupuesto else 0, font_style2)
                                fp = ''
                                if estructura.formapagopac:
                                    fp = ''
                                    for f in estructura.formapagopac.all():
                                        fp = fp + ' * ' + str(f) + '\n'
                                ws.write(row_num, 9, fp if fp else 'SIN REGISTRO', font_style2)

                                row_num += 1
                            else:
                                sinregistro=True
                        else:
                            sinregistro=True
                    else:
                        sinregistro=True

                    if sinregistro:
                        ws.write(row_num, 0, i + 1, font_style2)
                        ws.write(row_num, 1, p.carrera.nombre, font_style2)
                        ws.write(row_num, 2, 'SIN REGISTRO', font_style2)
                        ws.write(row_num, 3, 'SIN REGISTRO', font_style2)
                        ws.write(row_num, 4, 'SIN REGISTRO', font_style2)
                        ws.write(row_num, 5, 'SIN REGISTRO', font_style2)
                        ws.write(row_num, 6, 'SIN REGISTRO', font_style2)
                        ws.write(row_num, 7, 'SIN REGISTRO', font_style2)
                        ws.write(row_num, 8, 'SIN REGISTRO', font_style2)
                        ws.write(row_num, 9, 'SIN REGISTRO', font_style2)
                        row_num += 1

                wb.save(response)
                return response
            except Exception as ex:
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg = ex.__str__()
                msg = f'{msg} {err}'

                return JsonResponse({"result": "bad", "mensaje": u"Error: %s"%msg})

        elif action == 'imprimir_requisitospac':
            try:
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('requisitos_ingreso_pac')
                response = HttpResponse(content_type="application/ms-excel")
                columns = [
                    (u"N.", 1500),
                    (u"PROGRAMA O MAESTRÍA", 19000),
                    (u"REQUISITOS", 23000),
                    (u"¿FIRMA ELECTRÓNICA?", 5500),
                ]
                response['Content-Disposition'] = 'attachment; filename=requisitos_ingreso_pac' + random.randint(1, 10000).__str__() + '.xls'
                style_title = xlwt.easyxf(
                    'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                style_title_2 = xlwt.easyxf(
                    'font: height 250, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                ws.write_merge(0, 0, 0, len(columns), 'UNIVERSIDAD ESTATAL DE MILAGRO', style_title)
                ws.write_merge(1, 1, 0, len(columns),
                               'REPORTE DE PERFIL DE INGRESO DE PROGRAMA',
                               style_title_2)
                row_num = 3
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                    ws.col(col_num).width = columns[col_num][1]
                date_format = xlwt.XFStyle()
                date_format.num_format_str = 'yyyy/mm/dd'
                perfil = ProgramaPac.objects.filter(status=True)
                row_num = 4

                for i, p in enumerate(perfil):
                    sinregistro = False
                    x = p.funcionsustantivadocenciapac_set.last()
                    if x:
                        if x.detallerequisitoingreso_set.last():
                            if x.detallerequisitoingreso_set.last().requisito:
                                for r in x.detallerequisitoingreso_set.last().requisito.all():
                                    ws.write(row_num, 0, i + 1, font_style2)
                                    ws.write(row_num, 1, p.carrera.nombre, font_style2)
                                    ws.write(row_num, 2, str(r) if r else '', font_style2)
                                    ws.write(row_num, 3, 'SI' if x.detallerequisitoingreso_set.last().firmaelectronica else 'NO', font_style2)
                                    row_num += 1
                            else:
                                sinregistro = True
                        else:
                            sinregistro = True
                    else:
                        sinregistro = True

                    if sinregistro:
                        ws.write(row_num, 0, i + 1, font_style2)
                        ws.write(row_num, 1, p.carrera.nombre, font_style2)
                        ws.write(row_num, 2, 'SIN REGISTRO', font_style2)
                        ws.write(row_num, 3, 'SIN REGISTRO', font_style2)
                        row_num += 1

                wb.save(response)
                return response
            except Exception as ex:
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg = ex.__str__()
                msg = f'{msg} {err}'

                return JsonResponse({"result": "bad", "mensaje": u"Error: %s"%msg})

        elif action == 'finalizarsubidadatos':
            try:
                programapac = ProgramaPac.objects.get(pk=int(encrypt(request.POST['id'])))
                programapac.finalizado = True
                programapac.save(request)
                log(u'Editó Programa Pac: %s' % programapac, request, "edit")
                messages.success(request, 'Se finalizó el registro de datos correctamente.')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al finalizar registro."})

        elif action == 'habilitarsubidadatos':
            try:
                programapac = ProgramaPac.objects.get(pk=int(encrypt(request.POST['id'])))
                programapac.finalizado = False
                programapac.save(request)
                log(u'Editó Programa Pac: %s' % programapac, request, "edit")
                messages.success(request, 'Se habilitó el registro de datos correctamente.')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al finalizar registro."})

        elif action == 'addanexopac':
            try:
                with transaction.atomic():
                    if AnexosPac.objects.filter(descripcion=request.POST['descripcion'],
                                                         status=True).exists():
                        transaction.set_rollback(True)
                        messages.error(request, 'Ya se encuentra registrado.')
                        return JsonResponse({'error': True, "message": 'Anexo ya se encuentra registrado.'}, safe=False)
                    form = AnexoPacForm(request.POST)
                    if form.is_valid():
                        anexo = AnexosPac(descripcion=request.POST['descripcion'])
                        anexo.save(request)
                        log(u'Adiciono Anexo Pac: %s' % anexo, request, "add")
                        messages.success(request, 'Anexo adicionado correctamente.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editanexopac':
            try:
                with transaction.atomic():
                    instance = AnexosPac.objects.get(pk=request.POST['id'])
                    f = AnexoPacForm(request.POST)
                    if f.is_valid():
                        instance.descripcion = f.cleaned_data['descripcion']
                        instance.save(request)
                        log(u'Editó Anexos Pac: %s' % instance, request, "edit")
                        messages.success(request, 'Anexo modificado correctamente.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'delanexopac':
            try:
                a = AnexosPac.objects.get(pk=request.POST['id'])
                if a.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": u"Anexo en uso."})
                deta = DetalleAnexosPac.objects.filter(anexo_id=a.id)
                for d in deta:
                    d.delete()
                a.delete()
                log(u'Eliminó Anexo Pac: %s' % a, request, "del")
                messages.success(request, 'Se eliminó correctamente.')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'adddetalleanexopac':
            try:
                with transaction.atomic():
                    if DetalleAnexosPac.objects.filter(anexo_id=request.POST['id'], descripcion=request.POST['descripcion'],
                                                         status=True).exists():
                        transaction.set_rollback(True)
                        messages.error(request, 'Ya se encuentra registrado.')
                        return JsonResponse({'error': True, "message": 'Soporte ya se encuentra registrado.'}, safe=False)
                    form = DetalleAnexoPacForm(request.POST)
                    if form.is_valid():
                        detanexo = DetalleAnexosPac(anexo_id=request.POST['id'], descripcion=request.POST['descripcion'])
                        detanexo.save(request)
                        log(u'Adiciono Detalle Anexo Pac: %s' % detanexo, request, "add")
                        messages.success(request, 'Soporte adicionado correctamente.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deldetalleanexopac':
            try:
                a = DetalleAnexosPac.objects.get(pk=request.POST['id'])
                if a.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": u"Detalle Anexo en uso."})
                a.delete()
                log(u'Eliminó Detalle Anexos Pac: %s' % a, request, "del")
                messages.success(request, 'Se eliminó correctamente.')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'subirarchivoanexo':
            try:
                with transaction.atomic():
                    detalleanexo = DetalleAnexosPac.objects.filter(anexo_id=request.POST['id'])
                    newfile = None
                    indi = False
                    for det in detalleanexo:
                        if 'archivo_%s'%det.id in request.FILES:
                            newfile = request.FILES['archivo_%s'%det.id]
                            if newfile:
                                indi = True
                                if not ArchivoAnexoPac.objects.filter(programapac_id=request.POST['pro'], anexo_id=det.id, status=True).exists():
                                    newfile._name = generar_nombre("documentoanexopac_", newfile._name)
                                    anexoarchivo = ArchivoAnexoPac(programapac_id=request.POST['pro'],
                                                                   anexo_id=det.id,
                                                                   archivo=newfile)
                                    anexoarchivo.save(request)
                                else:
                                    anexoarchivo = ArchivoAnexoPac.objects.filter(programapac_id=request.POST['pro'], anexo_id=det.id, status=True).last()
                                    newfile._name = generar_nombre("documentoanexopac_", newfile._name)
                                    anexoarchivo.archivo = newfile
                                    anexoarchivo.save(request)
                    if indi:
                        log(u'Adicionó Archivo Anexos Pac: %s' % anexoarchivo, request, "add")
                        messages.success(request, 'Archivo Anexo guardado correctamente.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        messages.error(request, 'Ningún Archivo Anexo cargado.')
                        return JsonResponse({'error': True,
                                             "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        # elif action == 'actualizarconvenio':
        #     try:
        #         with transaction.atomic():
        #             convenios = ConveniosPac.objects.filter(programapac_id=request.POST['id'], status=True)
        #             if not AnexosPac.objects.filter(descripcion=request.POST['des'], status=True).exists():
        #                 anexo = AnexosPac(descripcion=request.POST['des'])
        #                 anexo.save(request)
        #                 log(u'Adicionó Anexo Pac: %s' % anexo, request, "add")
        #             a = AnexosPac.objects.filter(descripcion=request.POST['des'], status=True).last()
        #             limpiar = DetalleAnexosPac.objects.filter(anexo_id=a.id, status=True)
        #             for d in limpiar:
        #                 d.delete()
        #             for con in convenios:
        #                 if not DetalleAnexosPac.objects.filter(anexo_id=a.id, descripcion=con.convenioinstitucional.empresaempleadora.nombre, status=True).exists():
        #                     det = DetalleAnexosPac(anexo_id=a.id,
        #                                            descripcion=con.convenioinstitucional.empresaempleadora.nombre)
        #                     det.save(request)
        #                     log(u'Adicionó Detalle Anexo Pac: %s' % det, request, "add")
        #                     if not ArchivoAnexoPac.objects.filter(programapac_id=request.POST['pro'], anexo_id=det.id).exists():
        #                         anexconvenio = ArchivoAnexoPac(programapac_id=request.POST['pro'], anexo_id=det.id)
        #                         if con.convenioinstitucional.archivosconvenio:
        #                             anexconvenio.archivo = con.convenioinstitucional.archivoconvenio_set.filter(status=True).last().archivo
        #                         anexconvenio.save(request)
        #
        #             messages.success(request, 'Convenios actualizados correctamente.')
        #             return JsonResponse({"result": "ok"})
        #
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar los datos."})

        elif action == 'addcoordinador':
            try:
                with transaction.atomic():
                    form = CoordinadorPacForm(request.POST)
                    if form.is_valid():
                        info = InformacionInstitucionalPac(coordinador_id=request.POST['registro'])
                        pro = ProgramaPac.objects.filter(pk=request.POST['pro']).last()
                        if pro:
                            info.programapac = pro
                        info.save(request)
                        log(u'Editó Informacion Institucional Pac Pac: %s' % info, request, "edit")
                        messages.success(request, 'Coordinador guardado correctamente.')
                        return JsonResponse({"result": "ok","id": encrypt(info.id)})
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcoordinador':
            try:
                with transaction.atomic():
                    informacion = InformacionInstitucionalPac.objects.get(pk=request.POST['id'])
                    f = CoordinadorPacForm(request.POST)
                    if f.is_valid():
                        informacion.coordinador = Profesor.objects.get(pk=request.POST['registro'])
                        informacion.save(request)
                        messages.success(request, 'Se editó exitosamente')
                        log(u'Modifico Informacion Institucional Pac', request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        pass
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delcoordinadorpac':
            try:
                with transaction.atomic():
                    info = InformacionInstitucionalPac.objects.filter(pk=request.POST['id']).last()
                    info.delete()
                    log(u'Eliminó Informacion Institucional Pac: %s' % info, request, "del")
                    messages.success(request, 'Se eliminó exitosamente.')
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addtipoproceso':
            try:
                with transaction.atomic():
                    if TipoProcesoPac.objects.filter(descripcion=(request.POST['descripcion']).upper(), status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'Tipo ya se encuentra registrado.'}, safe=False)
                    form = TipoProcesoPacForm(request.POST)
                    if form.is_valid():
                        instance = TipoProcesoPac(descripcion=form.cleaned_data['descripcion'])
                        instance.save(request)
                        messages.success(request, 'Se adicionó exitosamente.')
                        log(u'Adicionó tipo de proceso: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'edittipoproceso':
            try:
                with transaction.atomic():
                    instance = TipoProcesoPac.objects.get(pk=request.POST['id'])
                    f = TipoProcesoPacForm(request.POST)
                    if f.is_valid():
                        instance.descripcion = f.cleaned_data['descripcion']
                        instance.save(request)
                        messages.success(request, 'Se editó exitosamente.')
                        log(u'Editó tipo de proceso: %s' % instance, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deltipoproceso':
            try:
                tipo = TipoProcesoPac.objects.get(pk=request.POST['id'])
                if tipo.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": u"Tipo de proceso en uso."})
                tipo.status = False
                tipo.save(request)
                log(u'Eliminó tipo de proceso %s' % tipo, request, "edit")
                messages.success(request, 'Se eliminó exitosamente.')
                return JsonResponse({"result": False,"error":False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True,"error":True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'addtipoprograma':
            try:
                with transaction.atomic():
                    if TipoProgramaPac.objects.filter(descripcion=(request.POST['descripcion']).upper(), status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'Tipo ya se encuentra registrado.'}, safe=False)
                    form = TipoProgramaPacForm(request.POST)
                    if form.is_valid():
                        instance = TipoProgramaPac(descripcion=form.cleaned_data['descripcion'])
                        instance.save(request)
                        messages.success(request, 'Se adicionó exitosamente.')
                        log(u'Adicionó tipo de programa Pac: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'edittipoprograma':
            try:
                with transaction.atomic():
                    instance = TipoProgramaPac.objects.get(pk=request.POST['id'])
                    f = TipoProgramaPacForm(request.POST)
                    if f.is_valid():
                        instance.descripcion = f.cleaned_data['descripcion']
                        instance.save(request)
                        messages.success(request, 'Se editó exitosamente.')
                        log(u'Editó tipo de programa: %s' % instance, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deltipoprograma':
            try:
                tipo = TipoProgramaPac.objects.get(pk=request.POST['id'])
                if tipo.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": u"Tipo de programa en uso."})
                tipo.status = False
                tipo.save(request)
                messages.success(request, 'Se eliminó exitosamente.')
                log(u'Eliminó tipo de programa %s' % tipo, request, "edit")
                return JsonResponse({"result": False,"error":False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True,"error":True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'addaprobaciontrabajotitulacion':
            try:
                with transaction.atomic():
                    if AprobacionTrabajoIntegracionCurricular.objects.filter(descripcion=(request.POST['descripcion']).upper(), status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'Ya se encuentra registrado.'}, safe=False)
                    form = TipoProgramaPacForm(request.POST)
                    if form.is_valid():
                        instance = AprobacionTrabajoIntegracionCurricular(descripcion=form.cleaned_data['descripcion'])
                        instance.save(request)
                        messages.success(request, 'Se adicionó exitosamente.')
                        log(u'Adicionó opción de aprobación Pac: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editaprobaciontrabajotitulacion':
            try:
                with transaction.atomic():
                    instance = AprobacionTrabajoIntegracionCurricular.objects.get(pk=request.POST['id'])
                    f = TipoProgramaPacForm(request.POST)
                    if f.is_valid():
                        instance.descripcion = f.cleaned_data['descripcion']
                        instance.save(request)
                        messages.success(request, 'Se editó exitosamente.')
                        log(u'Editó opción de aprobación: %s' % instance, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'delaprobaciontrabajotitulacion':
            try:
                tipo = AprobacionTrabajoIntegracionCurricular.objects.get(pk=request.POST['id'])
                if tipo.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": u"Opción de aprobación está en uso."})
                tipo.status = False
                tipo.save(request)
                messages.success(request, 'Se eliminó exitosamente.')
                log(u'Eliminó opción de aprobación %s' % tipo, request, "edit")
                return JsonResponse({"result": False,"error":False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True,"error":True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'delplanificacionparalelo':
            try:
                plan = PlanificacionParalelo.objects.get(pk=request.POST.get('id'))
                plan.status = False
                plan.save(request)
                return JsonResponse({"error":False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True,"error":True, "message": f"Intentelo más tarde. {ex.__str__()}"}, safe=False)

        elif action == 'addplanificacionparalelo':
            try:
                f = PlanificacionParaleloForm(request.POST)
                det = DetalleFuncionSustantivaDocenciaPac.objects.get(pk=request.POST['ids'])
                if f.is_valid():
                    if not PlanificacionParalelo.objects.values('id').filter(detallefuncionsustantivadocencia=det, periodo=f.cleaned_data.get('periodo'), status=True).exists():
                        carrera = det.funcionsustantivadocenciapac.programapac.carrera if det.funcionsustantivadocenciapac.programapac else None
                        plan = PlanificacionParalelo(
                            detallefuncionsustantivadocencia=det,
                            carrera=carrera,
                            periodo=f.cleaned_data.get('periodo'),
                            paralelos=f.cleaned_data.get('paralelos'),
                            fechalimiteplanificacion = f.cleaned_data.get('fechalimiteplanificacion')
                        )
                        plan.save(request)
                        return JsonResponse({'result':True})
                    return JsonResponse({'result':False,  "mensaje": f"Los paralelos de esta asignatura y periodo ya se encuentran registrados"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "error": True, "mensaje": f"Intentelo más tarde. {ex.__str__()}"}, safe=False)

        elif action == 'editplanificacionparalelo':
            try:
                plan = PlanificacionParalelo.objects.get(pk=request.POST['id'])
                det = DetalleFuncionSustantivaDocenciaPac.objects.get(pk=request.POST['ids'])
                f = PlanificacionParaleloForm(request.POST)
                if f.is_valid():
                    plan.detallefuncionsustantivadocencia = det
                    plan.carrera = det.funcionsustantivadocenciapac.programapac.carrera if det.funcionsustantivadocenciapac.programapac else None
                    plan.periodo = f.cleaned_data.get('periodo')
                    plan.paralelos = f.cleaned_data.get('paralelos')
                    plan.fechalimiteplanificacion = f.cleaned_data.get('fechalimiteplanificacion')
                    plan.save(request)
                    return JsonResponse({'result':True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "error": True, "mensaje": f"Intentelo más tarde. {ex.__str__()}"}, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})


    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addcampos':
                try:
                    data['title'] = u'Adicionar Campos'
                    form = CamposPacForm()
                    data['form'] = form
                    # data['nivelformacion'] = NivelFormacionPac.objects.get(pk=request.GET['idnivelformacion'])
                    return render(request, 'adm_pac/addcampos.html', data)
                except Exception as ex:
                    pass

            elif action == 'addcampoamplio':
                try:
                    data['title'] = u'Adicionar Campo Amplio'
                    form = CampoAmplioPacForm()
                    data['form'] = form
                    data['nivelformacion'] = NivelFormacionPac.objects.get(pk=request.GET['idnivelformacion'])
                    return render(request, 'adm_pac/addcampoamplio.html', data)
                except Exception as ex:
                    pass

            elif action == 'editcampoamplio':
                try:
                    data['title'] = u'Editar Campo Amplio'
                    data['campoamplio'] = campoamplio = CampoAmplioPac.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(campoamplio)
                    form = CampoAmplioPacForm(initial=initial)
                    data['form'] = form
                    return render(request, 'adm_pac/editcampoamplio.html', data)
                except Exception as ex:
                    pass

            elif action == 'addcampoespecifico':
                try:
                    data['title'] = u'Adicionar Campo Específico'
                    form = CampoEspecificoPacForm()
                    data['form'] = form
                    return render(request, 'adm_pac/addcampoespecifico.html', data)
                except Exception as ex:
                    pass

            elif action == 'editcampoespecifico':
                try:
                    data['title'] = u'Editar Campo Específico'
                    data['campoespecifico'] = campoespecifico = CampoEspecificoPac.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(campoespecifico)
                    form = CampoEspecificoPacForm(initial=initial)
                    data['form'] = form
                    return render(request, 'adm_pac/editcampoespecifico.html', data)
                except Exception as ex:
                    pass

            elif action == 'addcampodetallado':
                try:
                    data['title'] = u'Adicionar Campo Detallado'
                    form = CampoDetalladoPacForm()
                    data['form'] = form
                    return render(request, 'adm_pac/addcampodetallado.html', data)
                except Exception as ex:
                    pass

            elif action == 'editcampodetallado':
                try:
                    data['title'] = u'Editar Campo Detallado'
                    data['campodetallado'] = campodetallado = CampoDetalladoPac.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(campodetallado)
                    form = CampoDetalladoPacForm(initial=initial)
                    data['form'] = form
                    return render(request, 'adm_pac/editcampodetallado.html', data)
                except Exception as ex:
                    pass

            elif action == 'addcarrera':
                try:
                    data['title'] = u'Adicionar Carrera'
                    form = CarreraPacForm()
                    data['form'] = form
                    return render(request, 'adm_pac/addcarrera.html', data)
                except Exception as ex:
                    pass

            elif action == 'editcarrera':
                try:
                    data['title'] = u'Editar Carrera'
                    data['carrera'] = carrera = CarreraPac.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(carrera)
                    form = CarreraPacForm(initial=initial)
                    data['form'] = form
                    return render(request, 'adm_pac/editcarrera.html', data)
                except Exception as ex:
                    pass

            elif action == 'addtitulacion':
                try:
                    data['title'] = u'Adicionar Titulación'
                    form = TitulacionPacForm()
                    data['form'] = form
                    return render(request, 'adm_pac/addtitulacion.html', data)
                except Exception as ex:
                    pass

            elif action == 'edittitulacion':
                try:
                    data['title'] = u'Editar Titulación'
                    data['titulacion'] = titulacion = TitulacionPac.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(titulacion)
                    form = TitulacionPacForm(initial=initial)
                    data['form'] = form
                    return render(request, 'adm_pac/edittitulacion.html', data)
                except Exception as ex:
                    pass

            elif action == 'addcarrerarant':
                try:
                    data['title'] = u'Adicionar Titulo Grado Académico'
                    data['amplios'] = CampoAmplioPac.objects.filter(status=True)
                    data['especificos'] = CampoEspecificoPac.objects.filter(status=True)
                    data['detallados'] = CampoDetalladoPac.objects.filter(status=True)
                    data['carreras'] = CarreraPac.objects.filter(status=True)
                    data['titulaciones'] = TitulacionPac.objects.filter(status=True)
                    data['gradosacademicos'] = TituloGradoAcademicoPac.objects.filter(status=True)
                    return render(request, 'adm_pac/addcarrerarant.html', data)
                except Exception as ex:
                    pass

            elif action == 'campos':
                try:
                    data['title'] = u'Configuración de Campos'
                    campoamplio = CampoAmplioPac.objects.filter(status=True)
                    campoespecifico = CampoEspecificoPac.objects.filter(status=True)
                    campodetallado = CampoDetalladoPac.objects.filter(status=True)
                    carrera = CarreraPac.objects.filter(status=True)
                    titulacion = TitulacionPac.objects.filter(status=True)
                    data['nivelformacion'] = NivelFormacionPac.objects.filter(status=True)

                #paginación
                    # campoamplio
                    pagingcama = MiPaginador(campoamplio, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'pagecama' in request.GET:
                            p = int(request.GET['pagecama'])
                        else:
                            p = paginasesion
                        try:
                            page = pagingcama.page(p)
                        except:
                            p = 1
                        page = pagingcama.page(p)
                    except:
                        page = pagingcama.page(p)
                    request.session['paginador'] = p
                    data['pagingcama'] = pagingcama
                    data['rangospagincama'] = pagingcama.rangos_paginado(p)
                    data['pagecama'] = page
                    data['campoamplio'] = page.object_list

                    # campoespecifico
                    pagingcame = MiPaginador(campoespecifico, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'pagecame' in request.GET:
                            p = int(request.GET['pagecame'])
                        else:
                            p = paginasesion
                        try:
                            page = pagingcame.page(p)
                        except:
                            p = 1
                        page = pagingcame.page(p)
                    except:
                        page = pagingcame.page(p)
                    request.session['paginador'] = p
                    data['pagingcame'] = pagingcame
                    data['rangospagincame'] = pagingcame.rangos_paginado(p)
                    data['pagecame'] = page
                    data['campoespecifico'] = page.object_list

                    #campodetallado
                    pagingcamd = MiPaginador(campodetallado, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'pagecamd' in request.GET:
                            p = int(request.GET['pagecamd'])
                        else:
                            p = paginasesion
                        try:
                            page = pagingcamd.page(p)
                        except:
                            p = 1
                        page = pagingcamd.page(p)
                    except:
                        page = pagingcamd.page(p)
                    request.session['paginador'] = p
                    data['pagingcamd'] = pagingcamd
                    data['rangospagincamd'] = pagingcamd.rangos_paginado(p)
                    data['pagecamd'] = page
                    data['campodetallado'] = page.object_list

                    # #titulacion
                    paging = MiPaginador(titulacion, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'paget' in request.GET:
                            p = int(request.GET['paget'])
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
                    data['rangospagint'] = paging.rangos_paginado(p)
                    data['paget'] = page
                    data['titulacion'] = page.object_list

                    # carrera
                    pagingcarr = MiPaginador(carrera, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'pagecarr' in request.GET:
                            p = int(request.GET['pagecarr'])
                        else:
                            p = paginasesion
                        try:
                            pagecarr = pagingcarr.page(p)
                        except:
                            p = 1
                        pagecarr = pagingcarr.page(p)
                    except:
                        pagecarr = pagingcarr.page(p)
                    request.session['paginador'] = p
                    data['pagingcarr'] = pagingcarr
                    data['rangospagingcarr'] = pagingcarr.rangos_paginado(p)
                    data['pagecarr'] = pagecarr
                    data['carrera'] = pagecarr.object_list

                    return render(request, 'adm_pac/confcampos.html', data)
                except Exception as ex:
                    pass

            elif action == 'formacion':
                try:
                    data['title'] = u'Tipo de formación'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        tipos = TipoFormacionRediseno.objects.filter(descripcion__icontains=search,status=True).distinct()
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        tipos = TipoFormacionRediseno.objects.filter(id=ids)
                    else:
                        tipos = TipoFormacionRediseno.objects.filter(status=True).order_by('id')
                    paging = MiPaginador(tipos, 20)
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
                    data['proveedores'] = page.object_list
                    data['email_domain'] = EMAIL_DOMAIN
                    data['tipos'] = page.object_list
                    return render(request, "adm_pac/tipoformacion.html", data)
                except Exception as ex:
                    pass

            if action == 'data':
                try:
                    m = request.GET['model']
                    if 'q' in request.GET:
                        q = request.GET['q'].upper().strip()
                        if ':' in m:
                            sp = m.split(':')
                            model = eval(sp[0])
                            if len(sp) > 1:
                                query = model.flexbox_query(q, extra=sp[1])
                            else:
                                query = model.flexbox_query(q)
                        else:
                            model = eval(request.GET['model'])
                            query = model.flexbox_query(q)
                    else:
                        m = request.GET['model']
                        if ':' in m:
                            sp = m.split(':')
                            model = eval(sp[0])
                            resultquery = model.flexbox_query('')
                            try:
                                query = eval('resultquery.filter(%s, status=True).distinct()' % (sp[1]))
                            except Exception as ex:
                                query = resultquery
                        else:
                            model = eval(request.GET['model'])
                            query = model.flexbox_query('')
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_repr(), 'alias': x.flexbox_alias() if hasattr(x, 'flexbox_alias') else []} for x in query]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", 'mensaje': u'Error al obtener los datos.'})

            elif action == 'addpac':
                try:
                    data['title'] = u'Proyecto Académico Curricular'
                    data['etapas']=EtapaProyectoCurricular.objects.filter(status=True).order_by('id')
                    data['institucion'] = TituloInstitucion.objects.filter(status=True)[0]
                    data['departamento'] = Departamento.objects.filter(status=True, id=11)[0]

                    idprogramaPac = None
                    programapac = None
                    # funcionsustantiva = None
                    # funcioninvestigacion = None
                    # funcionvinculacio = None
                    # infraestructurapac = None

                    if 'idprograma' in request.GET:
                        if request.GET['idprograma']:
                            programapac = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['idprograma']))).last()
                            idprogramaPac = programapac.id if programapac else idprogramaPac
                    if 'idfuncion' in request.GET:
                        if request.GET['idfuncion']:
                            funcionsustantiva = FuncionSustantivaDocenciaPac.objects.filter(status=True, pk=int(encrypt(request.GET['idfuncion']))).last()
                            idprogramaPac = funcionsustantiva.programapac.id if funcionsustantiva else idprogramaPac
                    if 'idinvestigacion' in request.GET:
                        if request.GET['idinvestigacion']:
                            funcioninvestigacion = FuncionSustantivaInvestigacionPac.objects.filter(status=True, pk=int(encrypt(request.GET['idinvestigacion']))).last()
                            idprogramaPac = funcioninvestigacion.programapac.id if funcioninvestigacion else idprogramaPac
                    if 'idvinculacion' in request.GET:
                        if request.GET['idvinculacion']:
                            funcionvinculacio = FuncionSustantivaVinculacionSociedadPac.objects.filter(status=True, pk=int(encrypt(request.GET['idvinculacion']))).last()
                            idprogramaPac = funcionvinculacio.programapac.id if funcionvinculacio else idprogramaPac
                    if 'idinfraestructura' in request.GET:
                        if request.GET['idinfraestructura']:
                            infraestructurapac = InfraestructuraEquipamientoInformacionPac.objects.filter(status=True, pk=int(encrypt(request.GET['idinfraestructura']))).last()
                            idprogramaPac = infraestructurapac.programapac.id if infraestructurapac else idprogramaPac
                    if 'idinformacion' in request.GET:
                        if request.GET['idinformacion']:
                            data['informacioninstitucional'] = informacion = InformacionInstitucionalPac.objects.filter(status=True,pk=int(encrypt(request.GET['idinformacion']))).last()
                            if programapac:
                                idprogramaPac = informacion.programapac.id if informacion else idprogramaPac

                    if idprogramaPac:
                        data['programa'] = pr = ProgramaPac.objects.filter(status=True, pk=idprogramaPac).last()
                        informacion = InformacionInstitucionalPac.objects.filter(status=True,programapac_id=idprogramaPac).last()
                        if informacion:
                            data['informacioninstitucional'] = informacion
                        if pr:
                            data['detprogramaitinerario'] = DetalleItinerarioProgramaPac.objects.filter(status=True, programaPac=pr.id).order_by('id')
                            data['conveniopac'] = ConveniosPac.objects.filter(status=True, programapac=pr.id).order_by('-id')
                        data['funcion'] = fs = FuncionSustantivaDocenciaPac.objects.filter(status=True, programapac_id=idprogramaPac).last()
                        if fs:
                            data['detperfilingreso'] = DetallePerfilIngreso.objects.filter(status=True, funcionsustantiva=fs.id).last()
                            data['detrequisitoingreso'] = DetalleRequisitoIngreso.objects.filter(status=True, funcionsustantiva=fs.id).last()
                            data['detfuncion'] = DetalleFuncionSustantivaDocenciaPac.objects.filter(status=True, funcionsustantivadocenciapac=fs.id).order_by('-id')
                            data['detpreguntarespuestapac'] = DetallePreguntasPerfilegresoDocenciaPac.objects.filter(status=True, funcionsustantivadocenciapac=fs.id).order_by('-id')
                        data['investigacion'] = FuncionSustantivaInvestigacionPac.objects.filter(status=True, programapac_id=idprogramaPac).last()
                        data['vinculacion'] = FuncionSustantivaVinculacionSociedadPac.objects.filter(status=True, programapac_id=idprogramaPac).last()
                        data['infraestructura'] = inf = InfraestructuraEquipamientoInformacionPac.objects.filter(status=True, programapac_id=idprogramaPac).last()
                        if inf:
                            data['detallelaboratoriopac'] = DetalleLaboratorioInfraestructuraPac.objects.filter(status=True, infraestructuraequipamientopac=inf.id).order_by('-id')
                            data['detallebibliotecapac'] = DetalleBibliotecaInfraestructuraPac.objects.filter(status=True, infraestructuraequipamientopac=inf.id).order_by('-id')
                            data['detalleaulapac'] = DetalleAulaInfraestructuraPac.objects.filter(status=True, infraestructuraequipamientopac=inf.id).order_by('-id')
                            data['detallepersonalpac'] = detallepersonalpac= DetallePersonalAcademicoInfraestructuraPac.objects.filter(status=True, infraestructuraequipamientopac=inf.id).order_by('-id')
                            # if detallepersonalpac:
                            #    data['perfilrequerido'] = PerfilRequeridoPac.objects.filter(status=True).order_by('-id')
                            subtotalgasto = InformacionfinancieraPac.objects.filter(status=True, infraestructurapac=inf.id, presupuestoColumna__tipo=1).order_by('-id')
                            subtotalinversion = InformacionfinancieraPac.objects.filter(status=True, infraestructurapac=inf.id, presupuestoColumna__tipo=2).order_by('-id')
                            if subtotalgasto or subtotalinversion:
                                subtg = 0.00
                                subti = 0.00
                                totalpresupuesto = 0.00
                                for sub in subtotalgasto:
                                    subtg = sub.valorpresupuesto.__round__(2) + subtg.__round__(2)
                                for sub in subtotalinversion:
                                    subti = sub.valorpresupuesto.__round__(2) + subti.__round__(2)
                                totalpresupuesto = subtg+subti
                                data['informacionfinaciera'] = ['TOTAL GASTOS CORRIENTES:   %s $'%subtg,'TOTAL INVERSIÓN:   %s $'%subti,'TOTAL PRESUPUESTO:   %s $'%totalpresupuesto.__round__(2)]

                    data['idinformacion'] = request.GET.get('idinformacion')
                    return render(request, 'adm_pac/addpac.html', data)
                except Exception as ex:
                    pass

            elif action == 'addplanificacionparalelo':
                try:
                    f = PlanificacionParaleloForm()
                    f._init(periodo=request.session.get('periodo').pk)
                    data['form2'] = f
                    data['ids'] = request.GET['id']
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editplanificacionparalelo':
                try:
                    plan = PlanificacionParalelo.objects.get(pk=request.GET['id'])
                    f = PlanificacionParaleloForm(initial=model_to_dict(plan))
                    data['form2'] = f
                    data['id'] = plan.pk
                    data['ids'] = request.GET['detalle_id']
                    template = get_template('adm_postulacion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'listadocohortes':
                try:
                    data['title'] = u'Listado de Cohortes de la Carrera'
                    data['detalle'] = det = DetalleFuncionSustantivaDocenciaPac.objects.get(pk=request.GET['pk_detallefsd'])
                    data['planificacion'] = PlanificacionParalelo.objects.filter(detallefuncionsustantivadocencia=det, status=True)
                    data['pk_info'] = request.GET['pk_info']
                    data['pk_prog'] = det.funcionsustantivadocenciapac.programapac.pk
                    return render(request, "adm_pac/listadocohortes.html", data)
                except Exception as ex:
                    pass

            elif action == 'datosgenerales':
                try:
                    if request.GET['informacion']:
                        data['informacion'] = request.GET['informacion']
                    data['title'] = u'Datos generales'
                    form =  DatosGeneralForm()
                    form.bloquearcampos()
                    data['form'] = form

                    data['formdetalle'] = DetalleItinerarioProgramaPacForm()

                    return render(request, "adm_pac/datosgeneral.html", data)
                except Exception as ex:
                    pass

            elif action == 'editdatosgenerales':
                try:
                    data['title'] = u'Editar Datos generales'
                    data['programapac'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    data['detprogramaitinerario'] = DetalleItinerarioProgramaPac.objects.filter(programaPac=programa.id)
                    initial = model_to_dict(programa)
                    form = DatosGeneralForm(initial=initial)
                    form.bloquearcampos()
                    data['form'] = form
                    data['formdetalle'] = DetalleItinerarioProgramaPacForm()

                    return render(request, "adm_pac/editdatosgenerales.html", data)
                except Exception as ex:
                    pass

            elif action == 'addconveniopac':
                try:
                    data['title'] = u'Adicionar Convenio'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    data['form'] = ConvenioPacForm()
                    return render(request, "adm_pac/addconveniopac.html", data)
                except Exception as ex:
                    pass

            # elif action == 'editconveniopac':
            #     try:
            #         data['title'] = u'Editar Convenio'
            #         if 'pro' in request.GET:
            #             data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=request.GET['pro']).last()
            #         data['conveniopac'] = convenio = ConveniosPac.objects.filter(status=True, pk=request.GET['id']).last()
            #         initial = model_to_dict(convenio)
            #         form = ConvenioPacForm(initial=initial)
            #         data['form'] = form
            #
            #         return render(request, "adm_pac/editconveniopac.html", data)
            #     except Exception as ex:
            #         pass

            elif action == 'deleteconveniopac':
                try:
                    data['title'] = u'Eliminar Convenio'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    data['conveniopac'] = convenio = ConveniosPac.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    return render(request, "adm_pac/deleteconveniopac.html", data)
                except Exception as ex:
                    pass

            elif action == 'addfuncionsustantiva':
                try:
                    data['title'] = u'Funcion Sustantiva: Docencia'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    data['form'] = FuncionSustantivaDocenciaPacForm()
                    data['formdetalle'] = DetalleFuncionSustantivaDocenciaPacForm()

                    return render(request, "adm_pac/addfuncionsustantiva.html", data)
                except Exception as ex:
                    pass

            elif action == 'editfuncionsustantiva':
                try:
                    data['title'] = u'Editar Función Sustantiva: Docencia'
                    data['funcionpac'] = funcion = FuncionSustantivaDocenciaPac.objects.filter(status=True,
                                                                                pk=int(encrypt(request.GET['id']))).last()
                    initial = model_to_dict(funcion)
                    form = FuncionSustantivaDocenciaPacForm(initial=initial)
                    data['form'] = form
                    return render(request, "adm_pac/editfuncionsustantiva.html", data)
                except Exception as ex:
                    pass

            elif action == 'addperfilingreso':
                try:
                    data['title'] = u'Adicionar Perfil de ingreso'
                    data['action'] = action
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                        data['funciondocencia'] = funcion = FuncionSustantivaDocenciaPac.objects.filter(status=True, programapac_id=programa.id).last()
                    data['form'] = DetallePerfilIngresoForm()
                    return render(request, "adm_pac/addperfilingreso.html", data)
                except Exception as ex:
                    pass

            elif action == 'cargaradicionartitulo':
                try:
                    form = TituloPerfilIngresoForm()
                    form.adicionar()
                    data['form2'] = form
                    template = get_template('adm_pac/modal/addtituloperfil.html')
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

            elif action == 'editperfilingreso':
                try:
                    data['title'] = u'Editar Perfil de ingreso'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    data['detperfilingreso'] = perfil = DetallePerfilIngreso.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    initial = model_to_dict(perfil)
                    form = DetallePerfilIngresoForm(initial=initial)
                    data['form'] = form
                    return render(request, "adm_pac/editperfilingreso.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteperfilingreso':
                try:
                    data['title'] = u'Eliminar Perfil de ingreso'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    data['detperfilingreso'] = perfil = DetallePerfilIngreso.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    return render(request, "adm_pac/deleteperfilingreso.html", data)
                except Exception as ex:
                    pass

            elif action == 'addrequisitoingreso':
                try:
                    data['title'] = u'Adicionar Requisito de ingreso'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                        data['funciondocencia'] = funcion = FuncionSustantivaDocenciaPac.objects.filter(status=True, programapac_id=programa.id).last()
                    form = DetalleRequisitoIngresoForm()
                    form.iniciar()
                    data['form'] = form
                    return render(request, "adm_pac/addrequisitoingreso.html", data)
                except Exception as ex:
                    pass

            elif action == 'editrequisitoingreso':
                try:
                    data['title'] = u'Editar Requisito de ingreso'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    data['detrequisitoingreso'] = requi = DetalleRequisitoIngreso.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    initial = model_to_dict(requi)
                    form = DetalleRequisitoIngresoForm(initial=initial)
                    form.iniciar()
                    data['form'] = form
                    return render(request, "adm_pac/editrequisitoingreso.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleterequisitoingreso':
                try:
                    data['title'] = u'Eliminar Requisito de ingreso'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    data['detrequisitoingreso'] = requi = DetalleRequisitoIngreso.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    return render(request, "adm_pac/deleterequisitoingreso.html", data)
                except Exception as ex:
                    pass


            elif action == 'addpreguntasfuncionsustantiva':
                try:
                    data['title'] = u'Adicionar Preguntas de Perfil de egreso'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    if 'funcion' in request.GET:
                        data['funciondocencia'] = funcion = FuncionSustantivaDocenciaPac.objects.filter(status=True, pk=int(encrypt(request.GET['funcion']))).last()
                    data['form'] = DetallePreguntasPerfilegresoDocenciaPacForm()
                    return render(request, "adm_pac/addpreguntafunciondocencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'editpreguntasfuncionsustantiva':
                try:
                    data['title'] = u'Editar Preguntas de Perfil de egreso'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    data['detpreguntarespuestapac'] = preguntas = DetallePreguntasPerfilegresoDocenciaPac.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    form = DetallePreguntasPerfilegresoDocenciaPacForm(initial={'preguntaspac': preguntas.preguntaspac.descripcion, 'respuestapac': preguntas.respuestapac})
                    data['form'] = form

                    return render(request, "adm_pac/editPreguntaFuncionDocencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletepreguntasfuncionsustantiva':
                try:
                    data['title'] = u'Eliminar Pregunta de Perfil de egreso'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    data['detpreguntarespuestapac'] = preguntas = DetallePreguntasPerfilegresoDocenciaPac.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    return render(request, "adm_pac/deletepreguntafunciondocencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'addmicrocurricularfuncionsustantiva':
                try:
                    data['title'] = u'Adicionar Descripción Microcurricular'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    if 'funcion' in request.GET:
                        data['funciondocencia'] = funcion = FuncionSustantivaDocenciaPac.objects.filter(status=True, pk=int(encrypt(request.GET['funcion']))).last()
                    form = DetalleFuncionSustantivaDocenciaPacForm()
                    form.bloquearcampocomponentehoracredito()
                    form.editar(programa.numeroperiodosordinario)
                    form.masignatura(programa.carrera_id)
                    data['form'] = form
                    return render(request, "adm_pac/addmicrocurricularfuncionsustantiva.html", data)
                except Exception as ex:
                    pass

            elif action == 'editmicrocurricularfuncionsustantiva':
                try:
                    data['title'] = u'Editar Descripción Microcurricular'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    data['detmicrocurricular'] = microcurricular =DetalleFuncionSustantivaDocenciaPac.objects.get(pk=int(encrypt(request.GET['id'])))
                    initial = model_to_dict(microcurricular)
                    form = DetalleFuncionSustantivaDocenciaPacForm(initial=initial)
                    form.bloquearcampocomponentehoracredito()
                    form.editar(programa.numeroperiodosordinario)
                    form.masignatura(programa.carrera_id)
                    data['form'] = form
                    return render(request, "adm_pac/editmicrocurricularfunciondocencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletemicrocurricularfuncionsustantiva':
                try:
                    data['title'] = u'Eliminar Descripción Microcurricular'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    data['microcurricularpac'] = microcurricularpac = DetalleFuncionSustantivaDocenciaPac.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    return render(request, "adm_pac/deletemicrocurricularfuncionsustantiva.html", data)
                except Exception as ex:
                    pass

            elif action == 'addfuncioninvestigacion':
                try:
                    data['title'] = u'Funcion Sustantiva: Investigación'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    data['form'] = FuncionSustantivaInvestigacionPacForm()
                    return render(request, "adm_pac/addfuncioninvestigacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'editfuncioninvestigacion':
                try:
                    data['title'] = u'Editar Función Sustantiva: Investigación'
                    data['investigacionpac'] = investigacionpac = FuncionSustantivaInvestigacionPac.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    initial = model_to_dict(investigacionpac)
                    form = FuncionSustantivaInvestigacionPacForm(initial=initial)
                    data['form'] = form
                    return render(request, "adm_pac/editfuncioninvestigacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addfuncionvinculacion':
                try:
                    data['title'] = u'Funcion Sustantiva: Vinculación con la sociedad'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    data['form'] = FuncionSustantivaVinculacionSociedadPacForm()
                    return render(request, "adm_pac/addfuncionvinculacionsociedad.html", data)
                except Exception as ex:
                    pass

            elif action == 'editfuncionvinculacion':
                try:
                    data['title'] = u'Editar Función Sustantiva: Vinculación con la sociedad'
                    data['vinculacionpac'] = vinculacionpac = FuncionSustantivaVinculacionSociedadPac.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    initial = model_to_dict(vinculacionpac)
                    form = FuncionSustantivaVinculacionSociedadPacForm(initial=initial)
                    data['form'] = form
                    return render(request, "adm_pac/editfuncionvinculacionsociedad.html", data)
                except Exception as ex:
                    pass

            elif action == 'addinfraestructuraequipamiento':
                try:
                    data['title'] = u'Infraestructura, equipamiento e información financiera'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    data['form'] = InfraestructuraEquipamientoInformacionPacForm()
                    return render(request, "adm_pac/addinfraestructuraequipamiento.html", data)
                except Exception as ex:
                    pass

            elif action == 'editinfraestructuraequipamiento':
                try:
                    data['title'] = u'Editar Infraestructura, equipamiento e informacion financiera'
                    data['infraestructurapac'] = infraestructura = InfraestructuraEquipamientoInformacionPac.objects.filter(status=True,
                                                                                pk=int(encrypt(request.GET['id']))).last()
                    initial = model_to_dict(infraestructura)
                    form = InfraestructuraEquipamientoInformacionPacForm(initial=initial)
                    data['form'] = form
                    return render(request, "adm_pac/editinfraestructuraequipamiento.html", data)
                except Exception as ex:
                    pass

            elif action == 'addlaboratorioinfraestructura':
                try:
                    data['title'] = u'Adicionar Laboratorios y/o talleres'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    if 'infraestructura' in request.GET:
                        data['infraestructura'] = infraestructura = InfraestructuraEquipamientoInformacionPac.objects.filter(status=True, pk=int(encrypt(request.GET['infraestructura']))).last()
                    form = DetalleLaboratorioInfraestructuraPacForm()
                    # form.iniciar()
                    data['form'] = form
                    return render(request, "adm_pac/infraestructura/addlaboratorioinfraestructura.html", data)
                except Exception as ex:
                    pass

            elif action == 'editlaboratorioinfraestructura':
                try:
                    data['title'] = u'Editar Laboratorios y/o talleres'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    data['detlaboratoriopac'] = laboratorio = DetalleLaboratorioInfraestructuraPac.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    initial = model_to_dict(laboratorio)
                    form = DetalleLaboratorioInfraestructuraPacForm(initial=initial)
                    data['form'] = form
                    return render(request, "adm_pac/infraestructura/editlaboratorioinfraestructura.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletelaboratorioinfraestructura':
                try:
                    data['title'] = u'Eliminar Laboratorio y/o taller'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    data['detlaboratoriopac'] = laboratorio = DetalleLaboratorioInfraestructuraPac.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    return render(request, "adm_pac/infraestructura/deletelaboratorioinfraestructura.html", data)
                except Exception as ex:
                    pass

            elif action == 'addbibliotecainfraestructura':
                try:
                    data['title'] = u'Adicionar Bibliotecas Específicas PAC'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    if 'infraestructura' in request.GET:
                        data['infraestructura'] = infraestructura = InfraestructuraEquipamientoInformacionPac.objects.filter(status=True, pk=int(encrypt(request.GET['infraestructura']))).last()
                    data['form'] = DetalleBibliotecaInfraestructuraPacForm()
                    return render(request, "adm_pac/infraestructura/addbibliotecainfraestructura.html", data)
                except Exception as ex:
                    pass

            elif action == 'editbibliotecainfraestructura':
                try:
                    data['title'] = u'Editar Bibliotecas Específicas PAC'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    data['detbibliotecapac'] = biblioteca = DetalleBibliotecaInfraestructuraPac.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    initial = model_to_dict(biblioteca)
                    form = DetalleBibliotecaInfraestructuraPacForm(initial=initial)
                    data['form'] = form

                    return render(request, "adm_pac/infraestructura/editbibliotecainfraestructura.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletebibliotecainfraestructura':
                try:
                    data['title'] = u'Eliminar Bibliotecas Específicas PAC'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    data['detbibliotecapac'] = biblioteca = DetalleBibliotecaInfraestructuraPac.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    return render(request, "adm_pac/infraestructura/deletebibliotecainfraestructura.html", data)
                except Exception as ex:
                    pass

            elif action == 'addaulainfraestructura':
                try:
                    data['title'] = u'Adicionar Aulas por estructura institucional'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    if 'infraestructura' in request.GET:
                        data['infraestructura'] = infraestructura = InfraestructuraEquipamientoInformacionPac.objects.filter(status=True, pk=int(encrypt(request.GET['infraestructura']))).last()
                    form = DetalleAulaInfraestructuraPacForm()
                    form.numeroaulas()
                    data['form'] = form
                    return render(request, "adm_pac/infraestructura/addaulainfraestructura.html", data)
                except Exception as ex:
                    pass

            elif action == 'editaulainfraestructura':
                try:
                    data['title'] = u'Editar Aulas por estructura institucional'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    data['detaulapac'] = aula = DetalleAulaInfraestructuraPac.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    initial = model_to_dict(aula)
                    form = DetalleAulaInfraestructuraPacForm(initial=initial)
                    data['form'] = form
                    return render(request, "adm_pac/infraestructura/editaulainfraestructura.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteaulainfraestructura':
                try:
                    data['title'] = u'Eliminar Aulas por estructura institucional'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    data['detaulapac'] = aula = DetalleAulaInfraestructuraPac.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    return render(request, "adm_pac/infraestructura/deleteaulainfraestructura.html", data)
                except Exception as ex:
                    pass

            elif action == 'addpersonalacademicoinfraestructura':
                try:
                    data['title'] = u'Adicionar Personal Académico'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                        if programa:
                            data['funcion'] = funcion = FuncionSustantivaDocenciaPac.objects.filter(status=True, programapac_id=programa.id).last()
                    if 'infraestructura' in request.GET:
                        data['infraestructura'] = infraestructura = InfraestructuraEquipamientoInformacionPac.objects.filter(status=True, pk=int(encrypt(request.GET['infraestructura']))).last()
                    form = DetallePersonalAcademicoInfraestructuraPacForm()
                    form.editar(funcion)
                    data['form'] = form
                    return render(request, "adm_pac/infraestructura/addpersonalacademicoinfraestructura.html", data)
                except Exception as ex:
                    pass

            elif action == 'gestionarperfilacademico':
                try:
                    data['title'] = u'Gestionar Perfil Académico'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    if 'id' in request.GET:
                        data['personal'] = DetallePersonalAcademicoInfraestructuraPac.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    return render(request, "adm_pac/infraestructura/gestionarperfilacademico.html", data)
                except Exception as ex:
                    pass

            elif action == 'gestionarperfildirector':
                try:
                    data['title'] = u'Gestionar Perfil Director'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    if 'id' in request.GET:
                        data['director'] = InfraestructuraEquipamientoInformacionPac.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    return render(request, "adm_pac/infraestructura/gestionarperfildirector.html", data)
                except Exception as ex:
                    pass

            elif action == 'addperfilacademico':
                try:
                    data['title'] = u'Adicionar Titulación'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    if 'id' in request.GET:
                        data['personal'] = DetallePersonalAcademicoInfraestructuraPac.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    form = PerfilRequeridoPacForm()
                    form.bloquearcampos()
                    # data['form2'] = form
                    # template = get_template("adm_pac/modal/formperfilrequerido.html")
                    # return JsonResponse({"result": True, 'data': template.render(data)})
                    data['form'] = form
                    return render(request, "adm_pac/infraestructura/addperfilacademico.html", data)
                except Exception as ex:
                    pass

            elif action == 'addperfildirector':
                try:
                    data['title'] = u'Adicionar Titulación'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    if 'id' in request.GET:
                        data['director'] = InfraestructuraEquipamientoInformacionPac.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    form = PerfilRequeridoPacForm()
                    form.bloquearcampos()
                    data['form'] = form
                    return render(request, "adm_pac/infraestructura/addperfildirector.html", data)
                except Exception as ex:
                    pass

            elif action == 'editpersonalacademicoinfraestructura':
                try:
                    data['title'] = u'Editar Personal Académico'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                        if programa:
                            data['funcion'] = funcion = FuncionSustantivaDocenciaPac.objects.filter(status=True, programapac_id=programa.id).last()
                    data['detallepersonalpac'] = personal = DetallePersonalAcademicoInfraestructuraPac.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    initial = model_to_dict(personal)
                    form = DetallePersonalAcademicoInfraestructuraPacForm(initial=initial)
                    form.editar(funcion)
                    data['form'] = form
                    return render(request, "adm_pac/infraestructura/editpersonalacademicoinfraestructura.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletepersonalacademicoinfraestructura':
                try:
                    data['title'] = u'Eliminar Personal Académico'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    data['detallepersonalpac'] = personal = DetallePersonalAcademicoInfraestructuraPac.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    return render(request, "adm_pac/infraestructura/deletepersonalacademicoinfraestructura.html", data)
                except Exception as ex:
                    pass

            elif action == 'addinformacionfianciera':
                try:
                    data['title'] = u'Adicionar Información Financiera'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                        if programa:
                            data['funcion'] = funcion = FuncionSustantivaDocenciaPac.objects.filter(status=True, programapac_id=programa.id).last()
                    if 'infraestructura' in request.GET:
                        data['infraestructura'] = infraestructura = InfraestructuraEquipamientoInformacionPac.objects.filter(status=True, pk=int(encrypt(request.GET['infraestructura']))).last()
                    if infraestructura:
                        data['presupuestofila'] = presupuestofila = PresupuestoPacFila.objects.filter(status=True).order_by('orden')
                        data['presupuestocolumna'] = presupuestocolumna = PresupuestoPacColumna.objects.filter(status=True).order_by('orden')
                        data['presupuestocolumnagasto'] = presupuestocolumnagasto = PresupuestoPacColumna.objects.filter(status=True, tipo=1).order_by('orden')
                        data['presupuestocolumnainversion'] = presupuestocolumnainversion = PresupuestoPacColumna.objects.filter(status=True, tipo=2).order_by('orden')

                    return render(request, "adm_pac/infraestructura/addinformacionfinancierainfraestructura.html", data)
                except Exception as ex:
                    pass

            elif action == 'cargaradicionartipoformapago':
                try:
                    form = TipoFormaPagoPacForm()
                    data['form2'] = form
                    template = get_template('adm_pac/modal/addtipoformapagopac.html')
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos."})

            elif action == 'formapagopac':
                try:
                    data['title'] = u'Adicionar forma de pago del programa'
                    data['action'] = action
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    if 'infraestructura' in request.GET:
                        data['infraestructura'] = infraestructura = InfraestructuraEquipamientoInformacionPac.objects.filter(status=True, pk=int(encrypt(request.GET['infraestructura']))).last()
                    if infraestructura.formapagopac.all():
                        form = FormaPagoPacForm(initial={'formapago':infraestructura.formapagopac.all()})
                    else:
                        form = FormaPagoPacForm()
                    data['form'] = form
                    return render(request, "adm_pac/infraestructura/addformapagopac.html", data)
                except Exception as ex:
                    pass

            elif action == 'editinformacionfianciera':
                try:
                    data['title'] = u'Editar Información Financiera'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                        if programa:
                            data['funcion'] = funcion = FuncionSustantivaDocenciaPac.objects.filter(status=True, programapac_id=programa.id).last()
                    if 'infraestructura' in request.GET:
                        data['infraestructura'] = infraestructura = InfraestructuraEquipamientoInformacionPac.objects.filter(status=True, pk=int(encrypt(request.GET['infraestructura']))).last()

                    if infraestructura:

                        data['informacionfinacieragasto'] = informacionfinacieragasto = InformacionfinancieraPac.objects.filter(infraestructurapac_id=infraestructura.id, presupuestoColumna__tipo=1).order_by('presupuestoColumna__orden')
                        data['informacionfinacierainversion'] = informacionfinacierainversion = InformacionfinancieraPac.objects.filter(infraestructurapac_id=infraestructura.id, presupuestoColumna__tipo=2).order_by('presupuestoColumna__orden')
                        # data['informacionfinaciera'] = informacionfinaciera = InformacionfinancieraPac.objects.filter(status=True, infraestructurapac_id=infraestructura.id).order_by('id')
                        filtrocolumna = InformacionfinancieraPac.objects.filter(status=True, infraestructurapac_id=infraestructura.id).values('presupuestoColumna').distinct().order_by('id')
                        filtrofila = InformacionfinancieraPac.objects.filter(status=True, infraestructurapac_id=infraestructura.id).values('presupuestoFila').distinct().order_by('id')

                        data['presupuestofila'] = presupuestofila = PresupuestoPacFila.objects.filter(status=True, pk__in=filtrofila).order_by('orden')
                        data['presupuestocolumna'] = PresupuestoPacColumna.objects.filter(status=True, pk__in=filtrocolumna).order_by('orden')
                        data['presupuestocolumnagasto'] = presupuestocolumnagasto = PresupuestoPacColumna.objects.filter(status=True, tipo=1, pk__in=filtrocolumna).order_by('orden')
                        data['presupuestocolumnainversion'] = presupuestocolumnainversion = PresupuestoPacColumna.objects.filter(status=True, tipo=2, pk__in=filtrocolumna).order_by('orden')

                    return render(request, "adm_pac/infraestructura/editinformacionfinancierainfraestructura.html", data)
                except Exception as ex:
                    pass

            elif action == 'addtipo':
                try:
                    data['form2'] = TipoFormacionRedisenoForm()
                    template = get_template("adm_pac/modal/formtipoformacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edittipo':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = TipoFormacionRediseno.objects.get(pk= request.GET['id'])
                    data['form2'] = TipoFormacionRedisenoForm(model_to_dict(filtro))
                    template = get_template("adm_pac/modal/formtipoformacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

        # nuevos 18/4/2022
            elif action == 'configuraranexo':
                try:
                    data['title'] = u'Configuración Anexos'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                        data['anexos'] = anexos = AnexosPac.objects.filter(status=True).order_by('descripcion')
                        data['detalleanexo'] = detalleanexo = DetalleAnexosPac.objects.filter(status=True)
                    return render(request, "adm_pac/configuraranexopac.html", data)
                except Exception as ex:
                    pass

            elif action == 'cargaranexos':
                try:
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                        data['title'] = u'Cargar Anexos: %s'%programa.carrera
                        data['anexos'] = anexos = AnexosPac.objects.filter(status=True).order_by('descripcion')
                        data['detalleanexo'] = detalleanexo = DetalleAnexosPac.objects.filter(status=True)
                        data['archivoanexo'] = archivoanexo = ArchivoAnexoPac.objects.filter(programapac_id=int(encrypt(request.GET['pro'])), status=True)

                        # ACTUALIZAR CONVENIOS DEL PROGRAMA
                        convenios = ConveniosPac.objects.filter(programapac_id=programa.id, status=True)
                        if not AnexosPac.objects.filter(descripcion='CONVENIOS', status=True).exists():
                            anexo = AnexosPac(descripcion='CONVENIOS')
                            anexo.save(request)
                            log(u'Adicionó Anexo Pac: %s' % anexo, request, "add")
                        a = AnexosPac.objects.filter(descripcion='CONVENIOS', status=True).last()
                        for con in convenios:
                            if not DetalleAnexosPac.objects.filter(anexo_id=a.id, descripcion=con.convenioinstitucional.empresaempleadora.nombre, status=True).exists():
                                det = DetalleAnexosPac(anexo_id=a.id,
                                                       descripcion=con.convenioinstitucional.empresaempleadora.nombre)
                                det.save(request)
                                log(u'Adicionó Detalle Anexo Pac: %s' % det, request, "add")
                                if not ArchivoAnexoPac.objects.filter(programapac_id=programa.id, anexo_id=det.id).exists():
                                    anexconvenio = ArchivoAnexoPac(programapac_id=programa.id, anexo_id=det.id)
                                    if con.convenioinstitucional.archivosconvenio:
                                        anexconvenio.archivo = con.convenioinstitucional.archivoconvenio_set.filter(status=True).last().archivo
                                    anexconvenio.save(request)

                    return render(request, "adm_pac/cargaranexospac.html", data)
                except Exception as ex:
                    pass

            elif action == 'subirarchivoanexo':
                try:
                    data['id'] = request.GET['id']
                    data['pro'] = request.GET['pro']
                    data['detanexo'] = detanexo = DetalleAnexosPac.objects.filter(anexo_id=request.GET['id'])
                    data['form2'] = DetalleAnexoPacForm()

                    template = get_template("adm_pac/modal/formsubirarchivoanexos.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addanexopac':
                try:
                    data['form2'] = AnexoPacForm()
                    template = get_template("adm_pac/modal/formanexospac.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editanexopac':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = AnexosPac.objects.get(pk=request.GET['id'])
                    data['form2'] = AnexoPacForm(initial=model_to_dict(filtro))
                    template = get_template("adm_pac/modal/formanexospac.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'adddetalleanexopac':
                try:
                    data['id'] = request.GET['id']
                    data['form2'] = DetalleAnexoPacForm()
                    template = get_template("adm_pac/modal/formanexospac.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'configinformacionfianciera':
                try:
                    data['title'] = u'Configuración de Información Financiera'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(
                            encrypt(request.GET['pro']))).last()
                        if programa:
                            data['funcion'] = funcion = FuncionSustantivaDocenciaPac.objects.filter(status=True,
                                                                                                    programapac_id=programa.id).last()
                    if 'infraestructura' in request.GET:
                        data['infraestructura'] = infraestructura = InfraestructuraEquipamientoInformacionPac.objects.filter(
                            status=True, pk=int(encrypt(request.GET['infraestructura']))).last()
                    if infraestructura:
                        data['presupuestofila'] = presupuestofila = PresupuestoPacFila.objects.filter(status=True).order_by('orden')
                        data['presupuestocolumna'] = presupuestocolumna = PresupuestoPacColumna.objects.filter(status=True).order_by('orden')
                        # data['presupuestocolumnagasto'] = presupuestocolumnagasto = PresupuestoPacColumna.objects.filter(infraestructuraequipamientopac_id=infraestructura.id, tipo=1).order_by('orden')
                        # data['presupuestocolumnainversion'] = presupuestocolumnainversion = PresupuestoPacColumna.objects.filter(infraestructuraequipamientopac_id=infraestructura.id, tipo=2).order_by('orden')
                    return render(request, "adm_pac/infraestructura/configuracioninformacionfianciera.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcolumnainformacionfinanciera':
                try:
                    if 'infraestructura' in request.GET:
                        data['infraestructura'] = request.GET['infraestructura']
                    data['form2'] = PresupuestoPacColumnaForm()
                    template = get_template("adm_pac/modal/formconfiginformacionfinanciera.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editcolumnainformacionfinanciera':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = PresupuestoPacColumna.objects.get(pk=request.GET['id'])
                    data['form2'] = PresupuestoPacColumnaForm(initial=model_to_dict(filtro))
                    template = get_template("adm_pac/modal/formconfiginformacionfinanciera.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addfilainformacionfinanciera':
                try:
                    if 'infraestructura' in request.GET:
                        data['infraestructura'] = request.GET['infraestructura']
                    data['form2'] = PresupuestoPacFilaForm()
                    template = get_template("adm_pac/modal/formconfiginformacionfinanciera.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editfilainformacionfinanciera':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = PresupuestoPacFila.objects.get(pk=request.GET['id'])
                    data['form2'] = PresupuestoPacFilaForm(initial=model_to_dict(filtro))
                    template = get_template("adm_pac/modal/formconfiginformacionfinanciera.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addcoordinador':
                try:
                    if request.GET['pro']:
                        data['pro'] = int(encrypt(request.GET['pro']))
                    data['title'] = u'Registrar Director/a o Coordinador/a'
                    data['form'] = CoordinadorPacForm()
                    return render(request, "adm_pac/addcoordinador.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcoordinador':
                try:
                    data['title'] = u'Editar Director/a o Coordinador/a'
                    if 'pro' in request.GET:
                        data['programa'] = programa = ProgramaPac.objects.filter(status=True, pk=int(encrypt(request.GET['pro']))).last()
                    data['informacioninstitucional'] = infor = InformacionInstitucionalPac.objects.filter(status=True, pk=int(encrypt(request.GET['id']))).last()
                    data['form'] = CoordinadorPacForm()
                    return render(request, "adm_pac/editcoordinador.html", data)
                except Exception as ex:
                    pass

            elif action == 'proceso':
                try:
                    data['title'] = u'Tipo de proceso'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        tipos = TipoProcesoPac.objects.filter(descripcion__icontains=search,status=True).distinct()
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        tipos = TipoProcesoPac.objects.filter(id=ids)
                    else:
                        tipos = TipoProcesoPac.objects.filter(status=True).order_by('id')
                    paging = MiPaginador(tipos, 20)
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
                    data['proveedores'] = page.object_list
                    data['email_domain'] = EMAIL_DOMAIN
                    data['tipos'] = page.object_list
                    return render(request, "adm_pac/tipoproceso.html", data)
                except Exception as ex:
                    pass

            elif action == 'addtipoproceso':
                try:
                    data['form2'] = TipoProcesoPacForm()
                    template = get_template("adm_pac/modal/formtipoformacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edittipoproceso':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = TipoProcesoPac.objects.get(pk= request.GET['id'])
                    data['form2'] = TipoProcesoPacForm(model_to_dict(filtro))
                    template = get_template("adm_pac/modal/formtipoformacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'tipoprograma':
                try:
                    data['title'] = u'Tipo de programa'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        tipos = TipoProgramaPac.objects.filter(descripcion__icontains=search,status=True).distinct()
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        tipos = TipoProgramaPac.objects.filter(id=ids)
                    else:
                        tipos = TipoProgramaPac.objects.filter(status=True).order_by('id')
                    paging = MiPaginador(tipos, 20)
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
                    data['proveedores'] = page.object_list
                    data['email_domain'] = EMAIL_DOMAIN
                    data['tipos'] = page.object_list
                    return render(request, "adm_pac/tipoprogramapac.html", data)
                except Exception as ex:
                    pass

            elif action == 'addtipoprograma':
                try:
                    data['form2'] = TipoProgramaPacForm()
                    template = get_template("adm_pac/modal/formtipoformacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edittipoprograma':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = TipoProgramaPac.objects.get(pk= request.GET['id'])
                    data['form2'] = TipoProgramaPacForm(model_to_dict(filtro))
                    template = get_template("adm_pac/modal/formtipoformacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'aprobaciontrabajotitulacion':
                try:
                    data['title'] = u'Opciones de aprobación del trabajo de la unidad de integración curricular / unidad de titulación'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        tipos = AprobacionTrabajoIntegracionCurricular.objects.filter(descripcion__icontains=search,status=True).distinct()
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        tipos = AprobacionTrabajoIntegracionCurricular.objects.filter(id=ids).order_by('-id')
                    else:
                        tipos = AprobacionTrabajoIntegracionCurricular.objects.filter(status=True).order_by('-id')
                    paging = MiPaginador(tipos, 12)
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
                    data['proveedores'] = page.object_list
                    data['email_domain'] = EMAIL_DOMAIN
                    data['tipos'] = page.object_list
                    return render(request, "adm_pac/opcionesaprobacionpac.html", data)
                except Exception as ex:
                    pass

            elif action == 'addaprobaciontrabajotitulacion':
                try:
                    data['form2'] = TipoProgramaPacForm()
                    template = get_template("adm_pac/modal/formtipoformacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editaprobaciontrabajotitulacion':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = AprobacionTrabajoIntegracionCurricular.objects.get(pk=request.GET['id'])
                    data['form2'] = TipoProgramaPacForm(model_to_dict(filtro))
                    template = get_template("adm_pac/modal/formtipoformacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u'Proyecto Académico Curricular'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s']
                if search:
                    informacion = InformacionInstitucionalPac.objects.filter(Q(coordinador__persona__nombres__icontains=search) |
                                                            Q(programapac__carrera__nombre__icontains=search) |
                                                            Q(programapac__modalidad__nombre__icontains=search) |
                                                            Q(programapac__tipotramite__descripcion__icontains=search), status=True).distinct()
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    informacion = InformacionInstitucionalPac.objects.filter(status=True, id=ids)
                else:
                    informacion = InformacionInstitucionalPac.objects.filter(status=True).order_by('id')
                paging = MiPaginador(informacion, 20)
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
                data['email_domain'] = EMAIL_DOMAIN
                data['informacionprograma'] = page.object_list
                return render(request, "adm_pac/view.html", data)
            except Exception as ex:
                pass