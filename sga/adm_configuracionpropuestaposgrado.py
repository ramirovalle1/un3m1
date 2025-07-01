# -*- coding: latin-1 -*-
import ast
import io
import json
import os
import random
import sys
import time
import zipfile
from datetime import datetime, timedelta
from decimal import Decimal

import pandas as pd
from django.core.files.base import ContentFile
from django.db import transaction, connections
import xlsxwriter
from django.db.models import Avg, F, Value, Count
from django.db.models.functions import Concat
from django.forms import model_to_dict
import xlwt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template
from xlwt import *
from django.core.files import File as DjangoFile
from core.firmar_documentos import obtener_posicion_y, obtener_posicion_x_y_saltolinea
from core.firmar_documentos_ec import JavaFirmaEc
from decorators import secure_module, last_access
from moodle import moodle
from posgrado.forms import FormSolicitudProrrogaIngresoTemaMatricula, FormInforme, FormSeccionInforme, \
    FormPreguntaInforme, FormSeccionInformePregunta, FormConfiguracionInforme, SeleccionSedeForm, \
    JornadaEncuestaSedeForm, SeleleccionSedeJornadaForm, CronogramaEncuestaForm, FormObservacion
from posgrado.models import SolicitudProrrogaIngresoTemaMatricula, HistorialSolicitudProrrogaIngresoTemaMatricula, \
    Informe, SeccionInforme, Pregunta, SeccionInformePregunta, Revision, ConfiguraInformePrograma, InscripcionCohorte, \
    MecanismoDocumentosTutoriaPosgrado, EncuestaTitulacionPosgrado, SedeEncuestaTitulacionPosgrado, \
    JornadaSedeEncuestaTitulacionPosgrado, \
    InscripcionEncuestaTitulacionPosgrado, RespuestaSedeInscripcionEncuesta
from sagest.models import PersonaDepartamentoFirmas
from settings import SITE_STORAGE
from sga.commonviews import adduserdata
from sga.forms import ConfiguracionTitulacionPosgradoForm, ConfiguracionTitulacionPosgradoSublineaForm, ArchivoPdfForm, \
    ModificacionTutorForm, ComplexivoTribunalCalificadorPosgradoForm, ConfiguracionRubricaPosgradoForm, \
    RubricaPosgradoForm, \
    PonderacionRubricaForm, GraduadoPosgradoForm, ConfiguracionConvocatoriaMecanismoForm, GrupoTitulacionPostgradoForm, \
    ModeloEvaluativoPosgradoForm, DetalleModeloEvaluativoPosgradoForm, AsignarRubricaForm, \
    ComplexivoCalificarPropuestaEnsayoForm, AsignarModalidadSustentacionForm, ActualizarFechaSolicitudForm, \
    EtapaTutoriaTitulacionPosgradoForm, FirmarActaAprobacionCoordinacionForm, \
    ProgramaEtapaTutoriaTitulacionPosgradoForm, TipoDocumentoTutoriaPosgradoTitulacionForm, \
    EncuestaTitulacionPosgradoForm, EncuestaTitulacionPosgradoGeneralForm
from sga.funciones import log, MiPaginador, variable_valor, generar_nombre, null_to_numeric, null_to_decimal, \
    remover_caracteres_especiales_unicode, remover_caracteres_tildes_unicode
from sga.funciones_templatepdf import actagradoposgrado, actagradoposgradocomplexivo, \
    actagradoposgradocomplexivoconintegantesfirma, \
    rubricatribunalcalificacionposgrado, actadefensaposgrado, actagradoposgradoconintegrantesfirma, \
    actagradoposgradocomplexivoconintegantesfirmamasivo, \
    actadefensaposgradonotas, certificaciondefensa, acompanamientoposgrado, acompanamientoposgradopareja, \
    actaaprobacionexamencomplexivoposgrado, informe_posgrado, actagradoposgradocomplexivocontent, \
    certificaciondefensaposgradoconintegrantesfirma, actasustentacionnotaposgradoconintegrantesfirma
from sga.models import ConfiguracionTitulacionPosgrado, PropuestaSubLineaInvestigacion, \
    ConfiguracionTitulacionPosgradoSublinea, TemaTitulacionPosgradoMatricula, \
    TemaTitulacionPosgradoMatriculaHistorial, TemaTitulacionPosgradoProfesor, CARGOS_JURADO_SUSTENTACION, \
    TribunalTemaTitulacionPosgradoMatricula, RubricaTitulacionPosgrado, DetalleRubricaTitulacionPosgrado, TIPO_RUBRICA, \
    Graduado, ModeloRubricaTitulacionPosgrado, PonderacionRubricaPosgrado, RubricaTitulacionCabPonderacion, \
    RubricaTitulacionCabPonderacionPosgrado, RubricaTitulacionPonderacion, RubricaTitulacionPonderacionPosgrado, \
    RevisionTutoriasTemaTitulacionPosgradoProfesor, MecanismoTitulacionPosgrado, DetalleTitulacionPosgrado, \
    GrupoTitulacionPostgrado, DetalleGrupoTitulacionPostgrado, TemaTitulacionPosgradoMatriculaCabecera, Persona, \
    NivelTitulacion, Profesor, ModeloEvaluativoPosgrado, ModeloEvualativoDetallePosgrado, \
    RevisionPropuestaComplexivoPosgrado, ArchivoRevisionPropuestaComplexivoPosgrado, Periodo, \
    SolicitudTutorTemaHistorial, NotaDetalleGrupoTitulacionPostgrado, EtapaTemaTitulacionPosgrado, \
    HistorialFirmaActaAprobacionComplexivo, ProgramaEtapaTutoriaPosgrado, Carrera, \
    TutoriasTemaTitulacionPosgradoProfesor, Inscripcion, MateriaAsignada, ItinerarioMallaEspecilidad, Malla, \
    CoordinadorCarrera, Provincia, Canton, Notificacion
from sga.templatetags.sga_extras import encrypt


def nombre_mencion(tema):
    from sga.models import ItinerarioMallaEspecilidad
    try:
        eInscripcionCohorte = InscripcionCohorte.objects.filter(status=True, inscripcion=tema.matricula.inscripcion).first()
        iti = ItinerarioMallaEspecilidad.objects.filter(status=True, malla=tema.matricula.inscripcion.carrera.malla(),itinerario=eInscripcionCohorte.itinerario).order_by('-id').first()
        return iti.nombre
    except Exception as ex:
        return '-'

def paralelo_matricula(matricula):
    from sga.models import MateriaAsignada
    try:
        paralelo=''
        if MateriaAsignada.objects.filter(status=True, matricula=matricula).exists():
            eMateriaAsignada = MateriaAsignada.objects.filter(status=True, matricula=matricula).first()
            paralelo = eMateriaAsignada.materia.paralelo
        return paralelo
    except Exception as ex:
        pass

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    # periodo = request.session['periodo']
    carreras = persona.mis_carreras()
    escoordinadoraposgrado = PersonaDepartamentoFirmas.objects.filter(tipopersonadepartamento_id=2, departamentofirma_id=1, status=True, actualidad=True)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = ConfiguracionTitulacionPosgradoForm(request.POST)
                if f.is_valid():
                    configuracion = ConfiguracionTitulacionPosgrado(periodo=f.cleaned_data['periodo'],
                                                                    carrera=f.cleaned_data['carrera'],
                                                                    publicado=f.cleaned_data['publicado'],
                                                                    fechainiciotutoria=f.cleaned_data['fechainiciotutoria'],
                                                                    fechafintutoria=f.cleaned_data['fechafintutoria'],
                                                                    fechainiciopostulacion=f.cleaned_data['fechainiciopostulacion'],
                                                                    fechafinpostulacion=f.cleaned_data['fechafinpostulacion'],
                                                                    fechainimaestrante=f.cleaned_data['fechainimaestrante'],
                                                                    fechafinmaestrante=f.cleaned_data['fechafinmaestrante'])
                    configuracion.save(request)
                    log(u'Adiciono configuracion Titulacion posgrado: %s' % configuracion, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'agregarencuestatitulacion':
            try:
                f = EncuestaTitulacionPosgradoForm(request.POST)
                if f.is_valid():
                    eEncuestaTitulacionPosgrado = EncuestaTitulacionPosgrado(periodo=f.cleaned_data['periodo'],
                                                                    inicio=f.cleaned_data['inicio'],
                                                                    fin=f.cleaned_data['fin'],
                                                                    activo=f.cleaned_data['activo'],
                                                                   )
                    eEncuestaTitulacionPosgrado.save(request)
                    eEncuestaTitulacionPosgrado.configuraciontitulacionposgrados.set(f.cleaned_data['convocatoria'])
                    log(u'Adiciono encuesta: %s' % eEncuestaTitulacionPosgrado, request, "add")
                    return JsonResponse({"result": False}, safe=False)

                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addencuestagraduaciongeneral':
            try:
                f = EncuestaTitulacionPosgradoGeneralForm(request.POST, request.FILES)
                if f.is_valid():
                    eEncuestaTitulacionPosgrado = EncuestaTitulacionPosgrado(descripcion=f.cleaned_data['descripcion'],
                                                                             inicio=f.cleaned_data['inicio'],
                                                                             fin=f.cleaned_data['fin'],
                                                                             activo=f.cleaned_data['activo'],
                                                                             )
                    eEncuestaTitulacionPosgrado.save(request)
                    log(u'Adiciono encuesta general: %s' % eEncuestaTitulacionPosgrado, request, "add")
                else:
                    return JsonResponse({"result": False, "mensaje": f"Error al validar los datos.",
                                         "form": [{key: value[0]} for key, value in f.errors.items()]})
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})


        elif action == 'addrubrica':
            try:
                f = ConfiguracionRubricaPosgradoForm(request.POST)
                if f.is_valid():
                    rubrica = RubricaTitulacionPosgrado(nombre=f.cleaned_data['nombre'],
                                                        activo=f.cleaned_data['activo'])
                    rubrica.save(request)
                    log(u'Adiciono configuracion rubrica posgrado: %s' % rubrica, request, "add")
                    return JsonResponse({"result": False}, safe=True)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addrubricas':
            try:
                f = RubricaPosgradoForm(request.POST)
                rubrica = RubricaTitulacionPosgrado.objects.get(pk=request.POST['idrubrica'])
                if f.is_valid():
                    detalle = DetalleRubricaTitulacionPosgrado(rubricatitulacionposgrado=rubrica,
                                                               tiporubrica=f.cleaned_data['tiporubrica'],
                                                               rubrica=f.cleaned_data['rubrica'],
                                                               equivalencia=f.cleaned_data['equivalencia'])
                    detalle.save(request)
                    #se verifica que no pase de 100
                    valor = detalle.rubricatitulacionposgrado.puntaje()
                    if valor > 100:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Total de rubricas mayor a 100."})

                    log(u'Adiciono detalle rubrica posgrado: %s' % detalle, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'asignar_rubrica':
            try:
                f = AsignarRubricaForm(request.POST)
                if f.is_valid():
                    tema = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['id'])
                    if not tema.rubrica:
                        tema.rubrica = f.cleaned_data['rubrica']
                        tema.save(request)
                        log(u'Adicionó rubrica al temade titulación posgrado: %s' % tema, request, "edit")
                    return JsonResponse({"result": False})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Datos erróneos, intente nuevamente."}, safe=False)

        elif action == 'asignar_rubrica_pareja':
            try:
                f = AsignarRubricaForm(request.POST)
                if f.is_valid():
                    pareja = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=request.POST['id'])
                    if not pareja.rubrica_pareja():
                        for tema in pareja.obtener_parejas():
                            tema.rubrica = f.cleaned_data['rubrica']
                            tema.save(request)
                            log(u'Adicionó rubrica al tema de titulación posgrado: %s' % tema, request, "edit")
                    return JsonResponse({"result": False})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Datos erróneos, intente nuevamente."}, safe=False)

        elif action == 'firmar_acta_de_aprobacion':
            try:
                f = FirmarActaAprobacionCoordinacionForm(request.POST)
                if f.is_valid():
                    tema_titulacion = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['id'])
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre(str(tema_titulacion.id), newfile._name)

                        id = request.POST['id']
                        if newfile:
                            extension = newfile._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if newfile.size > 4194304:
                                return JsonResponse(
                                    {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                            if exte in ['pdf', 'PDF','.zip','.rar','.docx','docx','rar','zip']:
                                newfile._name = generar_nombre("acta_firmada", newfile._name)
                            else:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf"})

                            if f.cleaned_data['tipo'] == '1': #firmado por secretaria
                                firmado = 3
                            if f.cleaned_data['tipo'] == '2': #firmado por coordinacion
                                firmado = 4

                            tema_titulacion.actaaprobacionexamen = newfile
                            tema_titulacion.estado_acta_firma = firmado
                            tema_titulacion.save(request)
                            log(u"Firma de acta de aprobación complexivo, por: %s de %s" % (tema_titulacion.get_estado_acta_firma_display(),tema_titulacion), request,
                                "change")
                            historial = HistorialFirmaActaAprobacionComplexivo(
                                tema=tema_titulacion,
                                persona=persona,
                                actaaprobacionfirmada=newfile,
                                estado_acta_firma=firmado
                            )
                            historial.save(request)

                            return JsonResponse({"result": False}, safe=False)
                    else:
                        raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'asignar_modalidad_sustentacion':
            try:
                f = AsignarModalidadSustentacionForm(request.POST)
                if f.is_valid():
                    tema = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['id'])
                    tema.modalidadSustentacion = f.cleaned_data['modalidad']
                    tema.save(request)
                    log(u'Adicionó rubrica al temade titulación posgrado: %s' % tema, request, "edit")
                    return JsonResponse({"result": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Datos erróneos, intente nuevamente."}, safe=False)

        elif action == 'asignar_modalidad_sustentacion_pareja':
            try:
                f = AsignarModalidadSustentacionForm(request.POST)
                if f.is_valid():
                    pareja = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=request.POST['id'])
                    for tema in pareja.obtener_parejas():
                        tema.modalidadSustentacion = f.cleaned_data['modalidad']
                        tema.save(request)
                        log(u'Adicionó rubrica al tema de titulación posgrado: %s' % tema, request, "edit")
                    return JsonResponse({"result": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Datos erróneos, intente nuevamente."}, safe=False)

        elif action == 'actualizar_fecha_solicitud_propuesta':
            try:
                f = ActualizarFechaSolicitudForm(request.POST)
                if f.is_valid():
                    tema = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['id'])
                    tema.fecha_creacion = f.cleaned_data['fecha_solicitud']
                    tema.save(request)
                    log(u'Actualizó la fecha de solicitud de creación de la propuesta de titulación posgrado: %s' % tema, request, "edit")
                    return JsonResponse({"result": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Datos erróneos, intente nuevamente."}, safe=False)

        elif action == 'edit':
            try:
                configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=int(encrypt(request.POST['id'])))
                f = ConfiguracionTitulacionPosgradoForm(request.POST)
                if f.is_valid():
                    # configuracion.periodo = f.cleaned_data['periodo']
                    # configuracion.carrera = f.cleaned_data['carrera']
                    configuracion.publicado = f.cleaned_data['publicado']
                    configuracion.fechainiciotutoria = f.cleaned_data['fechainiciotutoria']
                    configuracion.fechafintutoria = f.cleaned_data['fechafintutoria']
                    configuracion.fechainiciopostulacion = f.cleaned_data['fechainiciopostulacion']
                    configuracion.fechafinpostulacion = f.cleaned_data['fechafinpostulacion']
                    configuracion.fechainimaestrante = f.cleaned_data['fechainimaestrante']
                    configuracion.fechafinmaestrante = f.cleaned_data['fechafinmaestrante']
                    configuracion.tipocomponente = f.cleaned_data['tipocomponente']
                    configuracion.save(request)
                    log(u'Modifico configuracion Titulacion posgrado: %s' % configuracion, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editrubrica':
            try:
                rubrica = RubricaTitulacionPosgrado.objects.get(pk=request.POST['id'])
                f = ConfiguracionRubricaPosgradoForm(request.POST)
                if f.is_valid():
                    rubrica.nombre = f.cleaned_data['nombre']
                    rubrica.activo = f.cleaned_data['activo']
                    rubrica.save(request)
                    log(u'Modifico configuracion Rubrica posgrado: %s' % rubrica, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editrubricas':
            try:
                detalle = DetalleRubricaTitulacionPosgrado.objects.get(pk=request.POST['id'])
                f = RubricaPosgradoForm(request.POST)
                if f.is_valid():
                    detalle.tiporubrica = f.cleaned_data['tiporubrica']
                    detalle.rubrica = f.cleaned_data['rubrica']
                    detalle.equivalencia = f.cleaned_data['equivalencia']
                    detalle.save(request)
                    log(u'Modifico detalle Rubrica posgrado: %s' % detalle, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editetapatutoriaposgrado':
            try:
                with transaction.atomic():
                    filtro = EtapaTemaTitulacionPosgrado.objects.get(pk=request.POST['id'])
                    f = EtapaTutoriaTitulacionPosgradoForm(request.POST)
                    if f.is_valid():
                        filtro.descripcion = f.cleaned_data['descripcion']
                        filtro.clasificacion = f.cleaned_data['clasificacion']
                        filtro.save(request)
                        log(u'Edito etapa tutoria posgrado %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                             "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'edit_programa_etapa_tutoria_posgrado':
            try:
                with transaction.atomic():
                    filtro = ProgramaEtapaTutoriaPosgrado.objects.get(pk=request.POST['id'])
                    f = ProgramaEtapaTutoriaTitulacionPosgradoForm(request.POST)
                    if f.is_valid():
                        filtro.orden = f.cleaned_data['orden']
                        filtro.mecanismotitulacionposgrado_id = int(request.POST['idmecanismo'])
                        filtro.convocatoria_id = int(request.POST['idconfiguracion'])
                        filtro.etapatutoria = f.cleaned_data['etapatutoria']
                        filtro.save(request)
                        log(u'Edito etapa tutoria posgrado %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                             "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'addmodelorubrica':
            try:
                rubrica = int(encrypt(request.POST['id']))
                numeroorden=0
                if ModeloRubricaTitulacionPosgrado.objects.filter(rubrica_id=rubrica, status=True):
                    ordenmodelorubrica = ModeloRubricaTitulacionPosgrado.objects.filter(rubrica_id=rubrica, status=True).order_by('-orden')[0]
                    numeroorden = ordenmodelorubrica.orden + 1
                else:
                    numeroorden=1
                modelorubrica=ModeloRubricaTitulacionPosgrado(rubrica_id=rubrica, orden=numeroorden)
                modelorubrica.save(request)
                log(u'Agrego modelo rubrica titulación: %s' % modelorubrica, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'actualizamodelorubrica':
            try:
                modelorubrica = ModeloRubricaTitulacionPosgrado.objects.get(pk=request.POST['iddetalle'])
                opc=int(request.POST['opc'])
                if opc==1:
                    valortexto=request.POST['valortexto']
                    modelorubrica.nombre=valortexto
                if opc==2:
                    valortexto=request.POST['valortexto']
                    modelorubrica.puntaje=valortexto
                if opc == 3:
                    valortexto = request.POST['valortexto']
                    modelorubrica.orden = valortexto
                if opc == 4:
                    valortexto = (request.POST['valortexto']).replace('#','')
                    modelorubrica.color = valortexto
                modelorubrica.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar."})

        elif action == 'actualizadetallerubrica':
            try:
                detallerubrica = DetalleRubricaTitulacionPosgrado.objects.get(pk=request.POST['iddetalle'])
                tipo=int(request.POST['tipo'])
                valortexto=request.POST['valortexto']
                if tipo == 1:
                    detallerubrica.puntaje=valortexto
                if tipo == 2:
                    detallerubrica.rubrica = valortexto
                if tipo == 3:
                    detallerubrica.letra = valortexto
                if tipo == 4:
                    detallerubrica.modelorubrica_id = int(valortexto)
                if tipo == 5:
                    detallerubrica.orden = int(valortexto)
                detallerubrica.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar."})

        elif action == 'actualizadetallerubricamodelo':
            try:
                detallerubrica = RubricaTitulacionPonderacionPosgrado.objects.get(pk=request.POST['iddetalle'])
                tipo=int(request.POST['tipo'])
                valortexto=request.POST['valortexto']
                if tipo == 1:
                    detallerubrica.descripción=valortexto
                if tipo == 2:
                    detallerubrica.leyenda = valortexto
                detallerubrica.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar."})

        elif action == 'deletedetallerubrica':
            try:
                detallerubrica = DetalleRubricaTitulacionPosgrado.objects.get(pk=request.POST['iddetalle'])
                detallerubrica.delete()
                log(u'Eliminó detalle rubrica titulación posgrado: %s - %s' % (detallerubrica, detallerubrica.id), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar."})

        elif action == 'deleteetapatutoriaposgrado':
            try:
                with transaction.atomic():
                    instancia = EtapaTemaTitulacionPosgrado.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino etapa tema tutoria posgrado: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'deleteprogramaetapatutoriaposgrado':
            try:
                with transaction.atomic():
                    instancia = ProgramaEtapaTutoriaPosgrado.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino etapa del programa tutoria posgrado: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'adddetallerubrica':
            try:
                id_modelorubrica = request.POST['id_modelorubrica']
                rubrica = RubricaTitulacionPosgrado.objects.get(pk=int(encrypt(request.POST['id'])))
                numeroorden = 0
                if DetalleRubricaTitulacionPosgrado.objects.filter(rubricatitulacionposgrado=rubrica, status=True):
                    ordenrubicatitulacion = DetalleRubricaTitulacionPosgrado.objects.filter(rubricatitulacionposgrado=rubrica, status=True).order_by('-orden')[0]
                    numeroorden = ordenrubicatitulacion.orden + 1
                else:
                    numeroorden = 1
                listadoabecedario = [
                    [0, '-'],[1, 'A'], [2, 'B'], [3, 'C'], [4, 'D'], [5, 'E'], [6, 'F'],
                    [7, 'G'], [8, 'H'], [9, 'I'], [10, 'J'], [11, 'K'], [12, 'L'], [13, 'M'], [14, 'N'],
                    [15, 'O'], [16, 'P'], [17, 'Q'], [18, 'R'], [19, 'S'], [20, 'T'], [21, 'U'], [22, 'V']
                ]
                detallerubrica=DetalleRubricaTitulacionPosgrado(rubricatitulacionposgrado=rubrica,modelorubrica_id=id_modelorubrica,orden=numeroorden)
                detallerubrica.save(request)
                listadorubricaponderacion = rubrica.rubricatitulacioncabponderacionposgrado_set.filter(activa=True, status=True)
                for idponde in listadorubricaponderacion:
                    rubricaponderacion = RubricaTitulacionPonderacionPosgrado(detallerubrica=detallerubrica,
                                                                              ponderacionrubrica=idponde)
                    rubricaponderacion.save()
                log(u'Agrego detalle rubrica titulación posgrado: %s' % detallerubrica, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'actualizamoddetallerubrica':
            try:
                rubrica = RubricaTitulacionPosgrado.objects.get(pk=request.POST['idrubrica'])
                id_modrubrica = request.POST['id_modrubrica']
                numeroorden = 0
                if RubricaTitulacionCabPonderacionPosgrado.objects.filter(rubrica=rubrica,status=True):
                    ordenponderacion = RubricaTitulacionCabPonderacionPosgrado.objects.filter(rubrica=rubrica, status=True).order_by('-orden')[0]
                    numeroorden = ordenponderacion.orden + 1
                else:
                    numeroorden = 1
                rubricaponderacion = RubricaTitulacionCabPonderacionPosgrado(rubrica=rubrica, orden=numeroorden, ponderacion_id=id_modrubrica)
                rubricaponderacion.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar."})

        elif action == 'configurar_convocatoria_mecanismo':
            try:
                f = ConfiguracionConvocatoriaMecanismoForm(request.POST)
                if f.is_valid():
                    configuracion = DetalleTitulacionPosgrado(configuracion_id=int(request.POST['configuracionTitulacion']),
                                                              mecanismotitulacionposgrado=f.cleaned_data['mecanismo'],
                                                              rubricatitulacionposgrado=f.cleaned_data['rubrica'])
                    configuracion.save(request)
                    log(u'Adiciono la configuracion de convocatoria mecanismo, Titulacion posgrado: %s' % configuracion,
                        request, "add")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'configurar_convocatoria_mecanismo_editar':
            try:
                f = ConfiguracionConvocatoriaMecanismoForm(request.POST)
                if f.is_valid():
                    filtro = DetalleTitulacionPosgrado.objects.get(pk=int(request.POST['id']), status=True)
                    filtro.mecanismotitulacionposgrado = f.cleaned_data['mecanismo']
                    filtro.rubricatitulacionposgrado = f.cleaned_data['rubrica']
                    filtro.save(request)
                    log(u'Edito la configuracion de convocatoria mecanismo, Titulacion posgrado: %s' % filtro, request,
                        "edit")
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'addgrupotitulacionpostgrado':
            try:
                f = GrupoTitulacionPostgradoForm(request.POST)
                if f.is_valid():
                    grupo = GrupoTitulacionPostgrado(configuracion_id=int(request.POST['id']),
                                                     fecha=f.cleaned_data['fecha'],
                                                     hora=f.cleaned_data['hora'],
                                                     link_zoom=f.cleaned_data['link_zoom'],
                                                     link_grabacion=f.cleaned_data['link_grabacion'],
                                                     cupo=f.cleaned_data['cupo'],
                                                     tutor=f.cleaned_data['tutor'],
                                                     modeloevaluativo=f.cleaned_data['modeloevaluativo'],
                                                     paralelo=f.cleaned_data['paralelo'],
                                                     itinerariomallaespecilidad=f.cleaned_data['mencion']
                                                     )
                    grupo.save(request)
                    log(u'Adiciono nuevo grupo, titulacion posgrado: %s' % grupo, request, "add")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'editgrupotitulacionpostgrado':
            try:
                f = GrupoTitulacionPostgradoForm(request.POST)
                if f.is_valid():
                    grupo = GrupoTitulacionPostgrado.objects.get(pk=request.POST['id'], status=True)
                    grupo.fecha = f.cleaned_data['fecha']
                    grupo.hora = f.cleaned_data['hora']
                    grupo.link_zoom = f.cleaned_data['link_zoom']
                    grupo.link_grabacion = f.cleaned_data['link_grabacion']
                    grupo.cupo = f.cleaned_data['cupo']
                    grupo.tutor = f.cleaned_data['tutor']
                    grupo.modeloevaluativo = f.cleaned_data['modeloevaluativo']
                    grupo.paralelo = f.cleaned_data['paralelo']
                    grupo.itinerariomallaespecilidad = f.cleaned_data['mencion']
                    grupo.save(request)
                    log(u'Edito  grupo titulacion posgrado: %s' % grupo, request, "edit")
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'delete_grupo_titulacion_postgrado':
            try:
                with transaction.atomic():
                    instancia = GrupoTitulacionPostgrado.objects.get(pk=request.POST['id'], status = True)
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó grupotitulación posgrado: %s' % instancia, request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'formargrupotitulacionposgradomatricula':
            try:
                tutor1 = None
                tutor2 = None
                lista = json.loads(request.POST['lista_items1'])
                if len(lista)>0:

                    if len(lista) == 1:
                        return JsonResponse({"result": True, "mensaje": "No se puede guardar una pareja con 1 registro seleccionado."}, safe=False)

                    contador = 1

                    for elemento in json.loads(request.POST['lista_items1']):
                        tema = TemaTitulacionPosgradoMatricula.objects.get(pk=int(elemento['id']))
                        if tema.cabeceratitulacionposgrado == None:
                            if contador == 1:
                                cabecera = TemaTitulacionPosgradoMatriculaCabecera(sublinea=tema.sublinea,
                                                                                 mecanismotitulacionposgrado=tema.mecanismotitulacionposgrado,
                                                                                 convocatoria=tema.convocatoria,
                                                                                 propuestatema=tema.propuestatema,
                                                                                 tutor=None,
                                                                                 variabledependiente= tema.variabledependiente,
                                                                                 variableindependiente = tema.variableindependiente
                                                                                 )
                                tutor1=tema.tutor
                                cabecera.save(request)
                                log(u'Adiciono la cabecera al grupo tema titulacion posgrado matricula: %s' % cabecera, request, "add")
                                contador=contador+1
                            tutor2= tema.tutor
                            tema.cabeceratitulacionposgrado = cabecera
                            tema.save(request)
                            log(u'Adiciono la cabecera de tema titulacion posgrado al maestrante: %s' % tema, request, "change")
                        else:
                            return JsonResponse({"result": True, "mensaje": "El o los maestrantes ya se encuentran en pareja."}, safe=False)

                    if tutor1 != tutor2:
                        cabecera.tutor = None
                        cabecera.poner_null_tutores()
                    else:
                        cabecera.tutor = tutor1
                    cabecera.save(request)
                    return JsonResponse({"result": "ok"}, safe=False)
                else:
                    return JsonResponse({"result": True, "mensaje": "No ha seleccionado datos   ."}, safe=False)

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Datos erróneos, intente nuevamente."}, safe=False)

        elif action == 'delmodelorubrica':
            try:
                modelorubrica=ModeloRubricaTitulacionPosgrado.objects.get(pk=request.POST['id'])
                log(u'Eliminó modelo rubrica titulación posgrado: %s' % modelorubrica, request, "del")
                modelorubrica.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delponderacionrubrica':
            try:
                prubonderacion=RubricaTitulacionCabPonderacionPosgrado.objects.get(pk=request.POST['id'])
                log(u'Eliminó ponderacion rubrica titulación posgrado: %s' % prubonderacion, request, "del")
                prubonderacion.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addponderacionmodal':
            try:
                with transaction.atomic():
                    form = PonderacionRubricaForm(request.POST)
                    if form.is_valid():
                        categoria = PonderacionRubricaPosgrado(nombre=form.cleaned_data['nombre'].upper())
                        categoria.save(request)
                        log(u'Adiciono Ponderación de Rubricas: %s' % categoria, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editponderacionmodal':
            try:
                with transaction.atomic():
                    filtro = PonderacionRubricaPosgrado.objects.get(pk=request.POST['id'])
                    f = PonderacionRubricaForm(request.POST)
                    if f.is_valid():
                        filtro.nombre = f.cleaned_data['nombre'].upper()
                        filtro.save(request)
                        log(u'Modificó Ponderación de Rubricas: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deleteponderacion':
            try:
                with transaction.atomic():
                    id = request.POST['id']
                    filtro = PonderacionRubricaPosgrado.objects.get(pk=id)
                    filtro.status = False
                    filtro.save(request)
                    log(u'Eliminar registro de evidencia: %s' % filtro, request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": str(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'modificartutor':
            try:
                temamatricula = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['id'], status = True)
                f = ModificacionTutorForm(request.POST)
                if f.is_valid():
                    temamatricula.tutor_id = f.cleaned_data['tutor']
                    temamatricula.save(request)
                    # temamatricula.tematitulacionposgradoprofesor_set.filter(aprobado=True, status = True).update(aprobado=False)
                    log(u'Modifico tutor del tema de titulacion: %s, y se desaprobo al profesor que estaba en ese tema' % temamatricula, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'modificartutorgruposol':
            try:
                temamatricula = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=request.POST['id'], status = True)
                f = ModificacionTutorForm(request.POST)
                if f.is_valid():
                    temamatricula.tutor_id = f.cleaned_data['tutor']
                    temamatricula.save(request)
                    # temamatricula.tematitulacionposgradoprofesor_set.filter(aprobado=True, status = True).update(aprobado=False)
                    log(u'Modifico tutor del tema de titulacion: %s, y se desaprobo al profesor que estaba en ese tema' % temamatricula, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'modificartutor1':
            try:
                temamatricula = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['id'], status = True)
                f = ModificacionTutorForm(request.POST)
                if f.is_valid():
                    temamatricula.tutor_id = f.cleaned_data['tutor']
                    temamatricula.save(request)
                    # temamatricula.tematitulacionposgradoprofesor_set.filter(aprobado=True, status = True).update(aprobado=False)
                    log(u'Modifico tutor del tema de titulacion: %s, y se desaprobo al profesor que estaba en ese tema' % temamatricula, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'modificartutorGrupo':
            try:
                temamatricula = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=request.POST['id'], status = True)
                f = ModificacionTutorForm(request.POST)
                if f.is_valid():
                    temamatricula.tutor_id = f.cleaned_data['tutor']
                    temamatricula.save(request)
                    temamatricula.tematitulacionposgradoprofesor_set.filter(aprobado=True, status = True).update(aprobado=False)
                    TemaTitulacionPosgradoMatricula.objects.filter(cabeceratitulacionposgrado= temamatricula, status = True).update(tutor=temamatricula.tutor)
                    log(u'Modifico tutor del tema de titulacion: %s, y se desaprobo al profesor que estaba en ese tema' % temamatricula, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'sublineas':
            try:
                configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=request.POST['id'])
                configuracion.configuraciontitulacionposgradosublinea_set.all().delete()
                datos = json.loads(request.POST['lista_items1'])
                for elemento in datos:
                    configuraciontitulacionposgradosublinea = ConfiguracionTitulacionPosgradoSublinea(configuraciontitulacionposgrado=configuracion,
                                                                                                      sublinea_id=int(elemento['id']))
                    configuraciontitulacionposgradosublinea.save(request)

                log(u'Modifico Sublinea configuracion Titulacion posgrado: %s' % configuracion, request, "edit")
                return JsonResponse({"result": "ok"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delete':
            try:
                configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=int(request.POST['id']), status=True)
                if not configuracion.en_uso():
                    log(u'Eliminó la carrera: %s' % configuracion, request, "del")
                    configuracion.delete()
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar ya se encuentra en uso."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteconfiguraciontitulacionpostgrado':
            try:
                with transaction.atomic():
                    detalle = DetalleTitulacionPosgrado.objects.get(pk=int(request.POST['id']), status=True)
                    detalle.status = False
                    detalle.save()
                    log(u'Eliminó grupotitulación posgrado: %s' % detalle, request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'aprobar_tema':
            try:
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 10485760:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                if 'id' in request.POST and 'st' in request.POST and 'obs' in request.POST:
                    tema = TemaTitulacionPosgradoMatricula.objects.get(pk=int(request.POST['id']),status = True)

                    if tema.cabeceratitulacionposgrado:#aprobar en pareja
                        cabecera = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk= tema.cabeceratitulacionposgrado.pk,status = True)
                        for foo in cabecera.obtener_parejas():
                            historia = TemaTitulacionPosgradoMatriculaHistorial(tematitulacionposgradomatricula=foo,
                                                                             observacion=request.POST['obs'],
                                                                             estado=request.POST['st'])
                            historia.save(request)
                            if variable_valor('APROBAR_SILABO') == int(request.POST['st']):
                                foo.aprobado = True
                                foo.save(request)
                                log(u'Aprobó el tema titulacion en pareja %s' % (foo), request, "add")
                                # silabo.materia.crear_actualizar_silabo_curso()
                            else:
                                log(u'Rechazó el tema titulacion en pareja %s' % (foo), request, "add")

                    else:#aprobar individual
                        historial = TemaTitulacionPosgradoMatriculaHistorial(tematitulacionposgradomatricula=tema,
                                                                             observacion=request.POST['obs'],
                                                                             estado=request.POST['st'])
                        historial.save(request)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("archivorevisionsolicitudtemapropuesto_", newfile._name)
                            historial.archivo = newfile
                            historial.save(request)

                        if variable_valor('APROBAR_SILABO') == int(request.POST['st']):
                            tema.aprobado = True
                            tema.save(request)
                            log(u'Aprobó el tema titulacion %s' % (tema), request, "add")
                            # silabo.materia.crear_actualizar_silabo_curso()
                        else:
                            log(u'Rechazó el tema titulacion %s' % (tema), request, "add")
                    return JsonResponse({"result": "ok", "idm": tema.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'detalleaprobacion':
            try:
                data['tema'] = tema = TemaTitulacionPosgradoMatricula.objects.get(pk=int(request.POST['id']),status = True)
                data['historialaprobacion'] = tema.tematitulacionposgradomatriculahistorial_set.filter(
                    status=True).order_by('-id')
                data['aprobar'] = variable_valor('APROBAR_SILABO')
                data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                template = get_template("adm_configuracionpropuesta/detalleaprobacion.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        elif action == 'cerrar_acta_y_graduar_masivo':
            try:
                eConfiguracionTitulacionPosgrado = request.POST.get('id',0)
                if eConfiguracionTitulacionPosgrado == 0:
                    raise NameError("Parametro no encontrado")

                eTemasTitulacionPosgradoMatriculas =TemaTitulacionPosgradoMatricula.objects.filter(status=True, convocatoria_id = eConfiguracionTitulacionPosgrado,actacerrada =False, estado_acta_firma = 4,mecanismotitulacionposgrado__id__in=[15,21] )
                for eTemaTitulacionPosgradoMatricula in eTemasTitulacionPosgradoMatriculas:
                    eTemaTitulacionPosgradoMatricula.calificacion = eTemaTitulacionPosgradoMatricula.obtener_calificacion_total_complexivo()
                    eTemaTitulacionPosgradoMatricula.califico = True
                    log(u"Calificación de acta complexivoposgrado masivo %s posgrado" % eTemaTitulacionPosgradoMatricula, request, "change")
                    eTemaTitulacionPosgradoMatricula.save(request)
                    eTemaTitulacionPosgradoMatricula.cerraracta_posgrado()
                    log(u"Acta cerrada masiva  %s posgrado masivo" % eTemaTitulacionPosgradoMatricula, request, "change")

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        elif action == 'cerrar_actas_y_graduar_masivo_seleccionados':
            try:
                id_string = request.POST.get('ids_tema', 0)
                id_list = ast.literal_eval(id_string)
                # Si id_list no es una lista, conviértelo en una lista con un solo elemento
                if not isinstance(id_list, tuple):
                    id_list = (id_list,)

                eTemaTitulacionPosgradoMatriculas = TemaTitulacionPosgradoMatricula.objects.filter(pk__in=id_list)
                for eTemaTitulacionPosgradoMatricula in eTemaTitulacionPosgradoMatriculas:
                    eTemaTitulacionPosgradoMatricula.calificacion = eTemaTitulacionPosgradoMatricula.obtener_calificacion_total_complexivo()
                    eTemaTitulacionPosgradoMatricula.califico = True
                    log(u"Calificación de acta complexivoposgrado masivo %s posgrado" % eTemaTitulacionPosgradoMatricula, request, "change")
                    eTemaTitulacionPosgradoMatricula.save(request)
                    eTemaTitulacionPosgradoMatricula.cerraracta_posgrado()
                    log(u"Acta cerrada masiva  %s posgrado masivo" % eTemaTitulacionPosgradoMatricula, request, "change")

                return JsonResponse({"result": False})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                pass

        elif action == 'aprobarprofesor':
            try:
                temaprofesor = TemaTitulacionPosgradoProfesor.objects.get(pk=request.POST['id'])
                # profesor = temaprofesor.profesor
                temaprofesor.aprobado=True
                temaprofesor.rechazado=False
                temaprofesor.save(request)

                if temaprofesor.aprobado:
                    valor_aprobado = 2
                    observacion= 'Aprobó solicitud de profesor para ser posible tutor del tema de titulación.'
                else:
                    valor_aprobado = 3
                    observacion = 'Rechazó solicitud de profesor para ser posible tutor del tema de titulación.'

                historial = SolicitudTutorTemaHistorial(
                tematitulacionposgradoprofesor=temaprofesor,
                persona = persona,
                estado = valor_aprobado,
                observacion = observacion

                )
                historial.save(request)
                #guardar el historial de aprobacion


                #aqui cambiar para que solo se apruebe y luego el estudiante elija su tutor
                # if temaprofesor.tematitulacionposgradomatricula:
                #     temamatricula = temaprofesor.tematitulacionposgradomatricula
                #     temamatricula.tutor = profesor
                #     temamatricula.save(request)
                # else:
                #     temamatricula = temaprofesor.tematitulacionposgradomatriculacabecera
                #     temamatricula.tutor = profesor
                #     temamatricula.save(request)
                ##############

                log(u'Aprobo solicitud de ser tutor: %s' % temaprofesor, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar los datos."})

        elif action == 'asignartribunal':
            try:
                f = ComplexivoTribunalCalificadorPosgradoForm(request.POST)
                if f.is_valid():
                    grupo = TribunalTemaTitulacionPosgradoMatricula.objects.get(pk=int(request.POST['id']))
                    if int(f.cleaned_data['presidente']) == 0 and int(f.cleaned_data['presidente']) == 0 and int(
                            f.cleaned_data['presidente']) == 0:
                        return JsonResponse({'result': 'bad', 'mensaje': u'Todos los campos son obligatorios'})
                    grupo.presidentepropuesta_id = f.cleaned_data['presidente']
                    grupo.secretariopropuesta_id = f.cleaned_data['secretario']
                    grupo.delegadopropuesta_id = f.cleaned_data['delegado']
                    grupo.fechadefensa = f.cleaned_data['fecha']
                    grupo.fechainiciocalificaciontrabajotitulacion = f.cleaned_data['fechainiciocalificaciontrabajotitulacion']
                    grupo.fechafincalificaciontrabajotitulacion = f.cleaned_data['fechafincalificaciontrabajotitulacion']
                    grupo.lugardefensa = f.cleaned_data['lugar'].upper()
                    grupo.horadefensa = f.cleaned_data['hora']
                    grupo.horafindefensa = f.cleaned_data['horafin']
                    grupo.save(request)
                    log(u"Adiciono Tribunal posgrado[%s]" % grupo.id, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u"Error al guardar los datos"})

        elif action == 'cambiartribunal':
            try:
                grupo = TribunalTemaTitulacionPosgradoMatricula.objects.get(pk=int(request.POST['id']), status=True)
                tema = TemaTitulacionPosgradoMatricula.objects.get(pk=grupo.tematitulacionposgradomatricula_id, status=True)
                elimino_calificacion = request.POST.get('calificacion', False)
                calificacion_titulacion = None
                detalle_puntaje = None
                id_trib_ant = None
                id_reemplazo_trib = str(request.POST['reemplazo_tribunal'])
                if grupo.presidentepropuesta_id == int(request.POST['ant_tribunal']):
                    if tema.calificaciontitulacionposgrado_set.filter(status=True, juradocalificador=grupo.presidentepropuesta_id).exists():
                        calificacion_titulacion = tema.calificaciontitulacionposgrado_set.get(status=True, juradocalificador=grupo.presidentepropuesta_id)
                        detalle_puntaje = calificacion_titulacion.calificaciondetallemodelorubricatitulacionposgrado_set.filter(
                            status=True).order_by('modelorubrica__orden')
                        calificacion_titulacion.juradocalificador_id = int(request.POST['reemplazo_tribunal'])
                        calificacion_titulacion.save(request)
                    id_trib_ant = str(grupo.presidentepropuesta_id)
                    grupo.presidentepropuesta_id = int(request.POST['reemplazo_tribunal'])

                if grupo.secretariopropuesta_id == int(request.POST['ant_tribunal']):
                    if tema.calificaciontitulacionposgrado_set.filter(status=True, juradocalificador=grupo.secretariopropuesta_id).exists():
                        calificacion_titulacion = tema.calificaciontitulacionposgrado_set.get(status=True, juradocalificador=grupo.secretariopropuesta_id)
                        detalle_puntaje = calificacion_titulacion.calificaciondetallemodelorubricatitulacionposgrado_set.filter(status=True).order_by('modelorubrica__orden')
                        calificacion_titulacion.juradocalificador_id = int(request.POST['reemplazo_tribunal'])
                        calificacion_titulacion.save(request)
                    id_trib_ant = str(grupo.secretariopropuesta_id)
                    grupo.secretariopropuesta_id = int(request.POST['reemplazo_tribunal'])

                if grupo.delegadopropuesta_id == int(request.POST['ant_tribunal']):
                    if tema.calificaciontitulacionposgrado_set.filter(status=True, juradocalificador=grupo.delegadopropuesta_id).exists():
                        calificacion_titulacion = tema.calificaciontitulacionposgrado_set.get(status=True, juradocalificador=grupo.delegadopropuesta_id)
                        detalle_puntaje = calificacion_titulacion.calificaciondetallemodelorubricatitulacionposgrado_set.filter(status=True).order_by('modelorubrica__orden')
                        calificacion_titulacion.juradocalificador_id = int(request.POST['reemplazo_tribunal'])
                        calificacion_titulacion.save(request)
                    id_trib_ant = str(grupo.delegadopropuesta_id)
                    grupo.delegadopropuesta_id = int(request.POST['reemplazo_tribunal'])

                if elimino_calificacion and calificacion_titulacion:
                    for calificacion_puntaje in detalle_puntaje:
                        calificacion_puntaje.puntaje = 0
                        calificacion_puntaje.save(request)
                    calificacion_titulacion.puntajerubricas = 0
                    calificacion_titulacion.puntajetrabajointegral = 0
                    calificacion_titulacion.puntajedefensaoral = 0
                    calificacion_titulacion.save(request)
                grupo.fechainiciocalificaciontrabajotitulacion = datetime.strptime(request.POST['fechai'], "%d-%m-%Y")
                grupo.fechafincalificaciontrabajotitulacion = datetime.strptime(request.POST['fechaf'], "%d-%m-%Y")
                grupo.save(request)
                log(u"Reemplazo Tribunal Individual posgrado: [%s] por: [%s] en grupo [%s]" % (id_trib_ant, id_reemplazo_trib, grupo.id), request, "edit")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u"Error al guardar los datos"})

        elif action == 'cambiartribunalpareja':
            try:
                grupo = TribunalTemaTitulacionPosgradoMatricula.objects.get(pk=int(request.POST['id']), status=True)
                cabecera = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=grupo.tematitulacionposgradomatriculacabecera_id, status=True)
                temas = TemaTitulacionPosgradoMatricula.objects.filter(cabeceratitulacionposgrado = cabecera, status = True)
                elimino_calificacion = request.POST.get('calificacion', False)
                calificacion_titulacion = None
                detalle_puntaje = None
                id_trib_ant = None
                id_reemplazo_trib = str(request.POST['reemplazo_tribunal'])
                if grupo.presidentepropuesta_id == int(request.POST['ant_tribunal']):
                    for tema in temas:
                        if tema.calificaciontitulacionposgrado_set.filter(status=True, juradocalificador=grupo.presidentepropuesta_id).exists():
                            calificacion_titulacion = tema.calificaciontitulacionposgrado_set.get(status=True, juradocalificador=grupo.presidentepropuesta_id)
                            detalle_puntaje = calificacion_titulacion.calificaciondetallemodelorubricatitulacionposgrado_set.filter(
                                status=True).order_by('modelorubrica__orden')
                            calificacion_titulacion.juradocalificador_id = int(request.POST['reemplazo_tribunal'])
                            calificacion_titulacion.save(request)
                            if elimino_calificacion:
                                for calificacion_puntaje in detalle_puntaje:
                                    calificacion_puntaje.puntaje = 0
                                    calificacion_puntaje.save(request)
                                calificacion_titulacion.puntajerubricas = 0
                                calificacion_titulacion.puntajetrabajointegral = 0
                                calificacion_titulacion.puntajedefensaoral = 0
                                calificacion_titulacion.save(request)
                    id_trib_ant = str(grupo.presidentepropuesta_id)
                    grupo.presidentepropuesta_id = int(request.POST['reemplazo_tribunal'])

                if grupo.secretariopropuesta_id == int(request.POST['ant_tribunal']):
                    for tema in temas:
                        if tema.calificaciontitulacionposgrado_set.filter(status=True, juradocalificador=grupo.secretariopropuesta_id).exists():
                            calificacion_titulacion = tema.calificaciontitulacionposgrado_set.get(status=True, juradocalificador=grupo.secretariopropuesta_id)
                            detalle_puntaje = calificacion_titulacion.calificaciondetallemodelorubricatitulacionposgrado_set.filter(status=True).order_by('modelorubrica__orden')
                            calificacion_titulacion.juradocalificador_id = int(request.POST['reemplazo_tribunal'])
                            calificacion_titulacion.save(request)
                            if elimino_calificacion:
                                for calificacion_puntaje in detalle_puntaje:
                                    calificacion_puntaje.puntaje = 0
                                    calificacion_puntaje.save(request)
                                calificacion_titulacion.puntajerubricas = 0
                                calificacion_titulacion.puntajetrabajointegral = 0
                                calificacion_titulacion.puntajedefensaoral = 0
                                calificacion_titulacion.save(request)
                    id_trib_ant = str(grupo.secretariopropuesta_id)
                    grupo.secretariopropuesta_id = int(request.POST['reemplazo_tribunal'])

                if grupo.delegadopropuesta_id == int(request.POST['ant_tribunal']):
                    for tema in temas:
                        if tema.calificaciontitulacionposgrado_set.filter(status=True, juradocalificador=grupo.delegadopropuesta_id).exists():
                            calificacion_titulacion = tema.calificaciontitulacionposgrado_set.get(status=True, juradocalificador=grupo.delegadopropuesta_id)
                            detalle_puntaje = calificacion_titulacion.calificaciondetallemodelorubricatitulacionposgrado_set.filter(status=True).order_by('modelorubrica__orden')
                            calificacion_titulacion.juradocalificador_id = int(request.POST['reemplazo_tribunal'])
                            calificacion_titulacion.save(request)
                            if elimino_calificacion:
                                for calificacion_puntaje in detalle_puntaje:
                                    calificacion_puntaje.puntaje = 0
                                    calificacion_puntaje.save(request)
                                calificacion_titulacion.puntajerubricas = 0
                                calificacion_titulacion.puntajetrabajointegral = 0
                                calificacion_titulacion.puntajedefensaoral = 0
                                calificacion_titulacion.save(request)
                    id_trib_ant = str(grupo.delegadopropuesta_id)
                    grupo.delegadopropuesta_id = int(request.POST['reemplazo_tribunal'])
                grupo.fechainiciocalificaciontrabajotitulacion = datetime.strptime(request.POST['fechai'], "%d-%m-%Y")
                grupo.fechafincalificaciontrabajotitulacion = datetime.strptime(request.POST['fechaf'], "%d-%m-%Y")
                grupo.save(request)
                log(u"Reemplazo Tribunal Pareja posgrado: [%s] por: [%s] en grupo [%s]" % (id_trib_ant, id_reemplazo_trib, grupo.id), request, "edit")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u"Error al guardar los datos"})

        elif action == 'asignartribunalpareja':
            try:
                f = ComplexivoTribunalCalificadorPosgradoForm(request.POST)
                if f.is_valid():
                    grupo = TribunalTemaTitulacionPosgradoMatricula.objects.get(pk=int(request.POST['id']))
                    if int(f.cleaned_data['presidente']) == 0 and int(f.cleaned_data['presidente']) == 0 and int(
                            f.cleaned_data['presidente']) == 0:
                        return JsonResponse({'result': 'bad', 'mensaje': u'Todos los campos son obligatorios'})
                    grupo.presidentepropuesta_id = f.cleaned_data['presidente']
                    grupo.secretariopropuesta_id = f.cleaned_data['secretario']
                    grupo.delegadopropuesta_id = f.cleaned_data['delegado']
                    grupo.fechadefensa = f.cleaned_data['fecha']
                    grupo.fechainiciocalificaciontrabajotitulacion = f.cleaned_data['fechainiciocalificaciontrabajotitulacion']
                    grupo.fechafincalificaciontrabajotitulacion = f.cleaned_data['fechafincalificaciontrabajotitulacion']
                    grupo.lugardefensa = f.cleaned_data['lugar'].upper()
                    grupo.horadefensa = f.cleaned_data['hora']
                    grupo.horafindefensa = f.cleaned_data['horafin']
                    grupo.save(request)
                    log(u"Adiciono Tribunal en pareja posgrado[%s]" % grupo.id, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u"Error al guardar los datos"})

        elif action == 'editarnumeroacta':
            try:
                f = GraduadoPosgradoForm(request.POST)
                if f.is_valid():
                    graduado = Graduado.objects.get(pk=int(request.POST['id']))
                    graduado.numeroactagrado = f.cleaned_data['numeroactagrado']
                    graduado.save(request)
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u"Error al guardar los datos"})

        elif action == 'detalle_tribunal':
            try:
                data = {}
                data['tema'] = tema = TemaTitulacionPosgradoMatricula.objects.get(pk=int(request.POST['id']))
                detalle = tema.tribunaltematitulacionposgradomatricula_set.filter(status=True)
                data['presidente'] = ''
                data['secretario'] = ''
                data['delegado'] = ''
                data['lugar'] = ''
                data['fechadefensa'] = ''
                data['horadefensa'] = ''
                data['horafindefensa'] = ''
                if detalle:
                    d = detalle[0]
                    data['presidente'] = d.presidentepropuesta
                    data['secretario'] = d.secretariopropuesta
                    data['delegado'] = d.delegadopropuesta
                    data['lugar'] = d.lugardefensa
                    data['fechadefensa'] = d.fechadefensa
                    data['horadefensa'] = d.horadefensa
                    data['horafindefensa'] = d.horafindefensa

                template = get_template('adm_configuracionpropuesta/detalle_tribunal.html')
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'graduar_estudiante':
            try:
                if 'id' in request.POST:
                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=request.POST['id'], status=True)
                    periodo = configuracion.periodo
                    carrera = configuracion.carrera
                    # for detalle in grupo.complexivodetallegrupo_set.filter(Q(status=True), (Q(matricula__estado=1)| Q(matricula__estado=10))).exclude(matricula__complexivoexamendetalle__estado=2):
                    for detalle in TemaTitulacionPosgradoMatricula.objects.filter(aprobado=True, tutor__isnull=False, tribunaltematitulacionposgradomatricula__isnull=False ,status=True, actacerrada=False, matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera):
                        if detalle.matricula.inscripcion.completo_malla():
                            if not detalle.matricula.inscripcion.graduado_set.filter(status=True):
                                graduado = Graduado(inscripcion=detalle.matricula.inscripcion,
                                                    decano=None,
                                                    notafinal=0,
                                                    nombretitulo='',
                                                    horastitulacion=0,
                                                    creditotitulacion=0,
                                                    creditovinculacion=0,
                                                    creditopracticas=0,
                                                    fechagraduado=None,
                                                    horagraduacion=None,
                                                    fechaactagrado=None,
                                                    profesor=None,
                                                    integrantetribunal=None,
                                                    docentesecretario=None,
                                                    secretariageneral=None,
                                                    representanteestudiantil=None,
                                                    representantedocente=None,
                                                    representantesuplentedocente=None,
                                                    representanteservidores=None,
                                                    matriculatitulacion=None,
                                                    codigomecanismotitulacion=None,
                                                    asistentefacultad=None,
                                                    estadograduado=False,
                                                    docenteevaluador1=None,
                                                    docenteevaluador2=None,
                                                    directorcarrera=None,
                                                    tematesis='')
                                graduado.save()
                            if Graduado.objects.filter(Q(status=True), (Q(inscripcion=detalle.matricula.inscripcion))).exists():
                                graduado = Graduado.objects.get(Q(status=True),Q(inscripcion=detalle.matricula.inscripcion))
                                notapropuesta = float(detalle.calificacion)
                                notafinal = null_to_numeric((notapropuesta), 2)
                                graduado.promediotitulacion = notafinal
                                graduado.estadograduado = True
                                graduado.save(request)
                                log(u'Graduo al estudiante: %s con nota final de: %s' % (graduado.inscripcion, str(graduado.promediotitulacion)), request,"edit")
                                detalle.actacerrada = True
                                detalle.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cerrar acta y graduar."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'quitartutor1':
            try:
                temamatricula = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['id'], status = True)
                temamatricula.tutor = None
                temamatricula.save(request)
                log(u'Quito tutor en titulacion: %s' % temamatricula, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        elif action == 'quitartutorGrupo':
            try:
                temamatricula = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=request.POST['id'], status = True)
                temamatricula.tutor = None
                temamatricula.save(request)
                TemaTitulacionPosgradoMatricula.objects.filter(cabeceratitulacionposgrado=temamatricula, status = True).update(tutor=temamatricula.tutor )
                log(u'Quito tutor en titulacion: %s' % temamatricula, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        elif action == 'quitartutor2':
            try:
                temamatricula = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['id'], status = True)
                temamatricula.tutor = None
                temamatricula.save(request)
                # solicitudprofesor = TemaTitulacionPosgradoProfesor.objects.get(tematitulacionposgradomatricula=temamatricula, status = True)
                # solicitudprofesor.aprobado = False
                # solicitudprofesor.save()
                log(u'Quito tutor en titulacion posgrado: %s' % temamatricula, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        elif action == 'quitartutorgruposol':
            try:
                temamatricula = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=request.POST['id'], status = True)
                temamatricula.tutor = None
                temamatricula.save(request)
                # solicitudprofesor = TemaTitulacionPosgradoProfesor.objects.get(tematitulacionposgradomatriculacabecera=temamatricula, status = True)
                # solicitudprofesor.aprobado = False
                # solicitudprofesor.save()
                log(u'Quito tutor en titulacion posgrado: %s' % temamatricula, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        elif action == 'addmodeloevaluativoposgrado':
            try:
                f = ModeloEvaluativoPosgradoForm(request.POST)
                if f.is_valid():
                    modelo = ModeloEvaluativoPosgrado(nombre=f.cleaned_data['nombre'],
                                                      fecha=datetime.now().date(),
                                                      notaaprobar=f.cleaned_data['notaaprobar'])
                    modelo.save(request)
                    log(u'Adicionado modelo evaluativo posgrado: %s' % modelo, request, "add")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'add_etapa_tutoria_posgrado':
            try:
                f = EtapaTutoriaTitulacionPosgradoForm(request.POST)
                if f.is_valid():
                    etapa = EtapaTemaTitulacionPosgrado(descripcion=f.cleaned_data['descripcion'],
                                                      clasificacion=f.cleaned_data['clasificacion'])
                    etapa.save(request)
                    log(u'Adicionado etapa tutoria posgrado: %s' % etapa, request, "add")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'add_programa_etapa_tutoria_posgrado':
            try:
                f = ProgramaEtapaTutoriaTitulacionPosgradoForm(request.POST)
                if f.is_valid():
                    programa_etapa = ProgramaEtapaTutoriaPosgrado(mecanismotitulacionposgrado_id=request.POST['idmecanismo'],
                                                                  convocatoria_id=request.POST['idconfiguracion'],
                                                                  etapatutoria=f.cleaned_data['etapatutoria'],
                                                                  orden=f.cleaned_data['orden'])
                    programa_etapa.save(request)
                    log(u'Adicionado una etapa al programa tutoria posgrado: %s' % programa_etapa, request, "add")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                             "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'add_documento_tutoria_titulacion_posgrado':
            try:
                f = TipoDocumentoTutoriaPosgradoTitulacionForm(request.POST)
                if f.is_valid():
                    eMecanismoDocumentosTutoriaPosgrado = MecanismoDocumentosTutoriaPosgrado(mecanismotitulacionposgrado_id=request.POST['idmecanismo'],
                                                                  convocatoria_id=request.POST['idconfiguracion'],
                                                                  tipo=f.cleaned_data['tipo'],
                                                                  orden=f.cleaned_data['orden'])
                    eMecanismoDocumentosTutoriaPosgrado.save(request)
                    log(u'Adicionado documento tutoria posgrado: %s' % eMecanismoDocumentosTutoriaPosgrado, request, "add")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                             "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'editmodeloevaluativoposgrado':
            try:
                f = ModeloEvaluativoPosgradoForm(request.POST)
                if f.is_valid():
                    modelo = ModeloEvaluativoPosgrado.objects.get(pk=request.POST['id'], status=True)
                    modelo.nombre = f.cleaned_data['nombre']
                    modelo.fecha = datetime.now().date()
                    modelo.notaaprobar = f.cleaned_data['notaaprobar']
                    modelo.save(request)
                    log(u'Modifico modelo evaluativo posgrado: %s' % modelo, request, "edit")
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'delmodeloevaluativoposgrado':
            try:
                with transaction.atomic():
                    modelo = ModeloEvaluativoPosgrado.objects.get(pk=request.POST['id'], status=True)
                    log(u"Elimino modelo evaluativo posgrado: %s" % modelo, request, "del")
                    modelo.status = False
                    modelo.save(request)
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'deldetallemodeloevaluativoposgrado':
            try:
                with transaction.atomic():
                    instancia = ModeloEvualativoDetallePosgrado.objects.get(pk=request.POST['id'], status=True)
                    instancia.status = False
                    instancia.save(request)
                    log(u"Elimino campo de modelo evaluativo posgrado: %s" % instancia, request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'adddetallemodeloevaluativoposgrado':
            try:
                f = DetalleModeloEvaluativoPosgradoForm(request.POST)
                if f.is_valid():
                    modelo = ModeloEvaluativoPosgrado.objects.get(pk=request.POST['modelo'], status=True)
                    if modelo.modeloevualativodetalleposgrado_set.filter(nombre=f.cleaned_data['nombre'],
                                                                         status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un campo con este nombre."})

                    detalle = ModeloEvualativoDetallePosgrado(modelo=modelo,
                                                              nombre=f.cleaned_data['nombre'],
                                                              alternativa=f.cleaned_data['alternativa'],
                                                              notamaxima=f.cleaned_data['notamaxima'])
                    detalle.save(request)
                    log(u'Adiciono detalle de modelo evaluativo posgrado: %s' % detalle, request, "edit")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'editdetallemodeloevaluativoposgrado':
            try:
                f = DetalleModeloEvaluativoPosgradoForm(request.POST)
                if f.is_valid():
                    detalle = ModeloEvualativoDetallePosgrado.objects.get(pk=request.POST['id'])
                    if ModeloEvualativoDetallePosgrado.objects.filter(modelo=detalle.modelo, nombre=detalle.nombre,
                                                                      alternativa=f.cleaned_data[
                                                                          'alternativa']).exclude(
                            id=detalle.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un campo con esa alternativa."})
                    detalle.alternativa = f.cleaned_data['alternativa']
                    detalle.notamaxima = f.cleaned_data['notamaxima']
                    detalle.save(request)
                    log(u'Modifico detalle de modelo evaluativo posgrado: %s' % detalle, request, "edit")
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'clasificar_tema':
            try:
                temamatricula = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['idt'])
                temamatricula.convocatoria_id=int(request.POST['id'])
                temamatricula.save(request)
                log(u'Clasifica convocatoria al tema : %s' % temamatricula, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        elif action == 'pdfactagradoposgrado':
            try:
                from settings import DEBUG
                url_path = 'http://127.0.0.1:8000'
                if not DEBUG:
                    url_path = 'https://sga.unemi.edu.ec'
                actaposgrado = actagradoposgradoconintegrantesfirma(request)
                if not actaposgrado:
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"El Acta de Grado debe estar calificada y cerrada"})
                res = actaposgrado
                qrresult = url_path + res.url
                return JsonResponse({"result": "ok", 'url': qrresult})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar documento."})

        elif action == 'pdfcertificaciondefensaposgrado':
            try:
                from settings import DEBUG
                url_path = 'http://127.0.0.1:8000'
                if not DEBUG:
                    url_path = 'https://sga.unemi.edu.ec'
                actaposgrado = certificaciondefensaposgradoconintegrantesfirma(request)
                if not actaposgrado:
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"El Acta de Grado debe estar calificada y cerrada"})
                res = actaposgrado
                qrresult = url_path + res.url
                return JsonResponse({"result": "ok", 'url': qrresult})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar documento."})

        elif action == 'pdfactasustentacionnotaposgrado':
            try:
                from settings import DEBUG
                url_path = 'http://127.0.0.1:8000'
                if not DEBUG:
                    url_path = 'https://sga.unemi.edu.ec'
                actaposgrado = actasustentacionnotaposgradoconintegrantesfirma(request)
                if not actaposgrado:
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"El Acta de Grado debe estar calificada y cerrada"})
                res = actaposgrado
                qrresult = url_path + res.url
                return JsonResponse({"result": "ok", 'url': qrresult})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar documento."})

        elif action == 'pdfactagradoposgradocomplexivo':
            try:
                from settings import DEBUG
                url_path = 'http://127.0.0.1:8000'
                if not DEBUG:
                    url_path = 'https://sga.unemi.edu.ec'
                actaposgrado = actagradoposgradocomplexivoconintegantesfirma(request)
                res = actaposgrado
                qrresult = url_path + res.url
                return JsonResponse({"result": "ok", 'url': qrresult})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar documento."})

        elif action == 'pdfactagradoposgradocomplexivomasivo':
            try:
                from sga.proccess_background_sga import generar_actas_de_grado_masivo
                a = generar_actas_de_grado_masivo(request)
                a.start()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar documento."})

        elif action == 'pdfcertificaciondefensa':
            try:
                actaposgrado = certificaciondefensa(request.POST['id'])
                return actaposgrado
            except Exception as ex:
                pass

        elif action == 'actaacompanamiento_pdf':
            try:
                actaposgrado = acompanamientoposgrado(request.POST['id'])
                return actaposgrado
            except Exception as ex:
                pass

        elif action == 'actaacompanamientopareja_pdf':
            try:
                actaposgrado = acompanamientoposgradopareja(request.POST['id'])
                return actaposgrado
            except Exception as ex:
                pass

        elif action == 'pdfactadefensaposgrado':
            try:
                actdefensaposgrado = actadefensaposgrado(request.POST['id'])
                return actdefensaposgrado
            except Exception as ex:
                pass

        elif action == 'pdfactaaprobacionexamencomplexivo':
            try:
                actaaprobacionexamencomplexivo = actaaprobacionexamencomplexivoposgrado(request.POST['id'])
                return actaaprobacionexamencomplexivo
            except Exception as ex:
                pass

        elif action == 'pdfactadefensaposgradonotas':
            try:
                actdefensaposgrado = actadefensaposgradonotas(request.POST['id'])
                return actdefensaposgrado
            except Exception as ex:
                pass

        elif action == 'pdfrubricacalificacionesposgrado':
            try:
                iddetallegrupo = request.POST['id']
                rubricatribunal = rubricatribunalcalificacionposgrado(iddetallegrupo)
                return rubricatribunal
            except Exception as ex:
                pass

        elif action == 'cerraactaposgrado':
            try:
                idmaestrantegrupo = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['id'])
                idmaestrantegrupo.califico =True
                idmaestrantegrupo.save(request)
                if idmaestrantegrupo.estadotribunal == 2:
                    idmaestrantegrupo.cerraracta_posgrado()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                pass

        elif action == 'calificaractaycerrarposgradocomplexivo':
            try:
                idmaestrantegrupo = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['id'])
                idmaestrantegrupo.calificacion = idmaestrantegrupo.obtener_calificacion_total_complexivo()
                idmaestrantegrupo.califico = True
                idmaestrantegrupo.save(request)
                log(u"Calificación de acta complexivo  %s posgrado" % idmaestrantegrupo, request,"change")

                idmaestrantegrupo.cerraracta_posgrado()
                log(u"Acta cerrada  %s posgrado" % idmaestrantegrupo, request, "change")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                pass

        elif action == 'abriractaposgrado':
            try:
                idmaestrantegrupo = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['id'])
                idmaestrantegrupo.califico = False
                idmaestrantegrupo.actacerrada = False
                idmaestrantegrupo.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                pass

        elif action == 'habilitartesiscorrejida':
            try:
                idmaestrantegrupo = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['id'])
                idmaestrantegrupo.puedesubirtrabajofinal = True
                idmaestrantegrupo.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                pass

        elif action == 'habilitartesiscorrejidapareja':
            try:
                cabecera = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=request.POST['id'])
                cabecera.puedesubirtrabajofinal = True
                cabecera.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                pass

        elif action == 'aprobarensayo':
            try:
                f = ComplexivoCalificarPropuestaEnsayoForm(request.POST, request.FILES)
                newfile = None
                newfilec = None

                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        if newfile.size > 52428800:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                        elif newfile.size <= 0:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Error, el archivo Propuesta Práctica esta vacío."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf' or ext == '.PDF':
                                newfile._name = generar_nombre("urkund_", newfile._name)
                            else:
                                return JsonResponse({"result": "bad",
                                                     "mensaje": u"Error, archivo de Propuesta Práctica solo en .doc, docx."})
                if 'correccion' in request.FILES:
                    newfilec = request.FILES['correccion']
                    if newfilec:
                        if newfilec.size > 52428800:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                        elif newfilec.size <= 0:
                            return JsonResponse({"result": "bad",
                                                 "mensaje": u"Error, el archivo Propuesta Práctica (Desde introducción hasta conclusión) esta vacío."})
                        else:
                            newfilesd = newfilec._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.doc' or ext == '.docx' or ext == '.pdf' or ext == '.PDF':
                                newfilec._name = generar_nombre("correccion_", newfilec._name)
                            else:
                                return JsonResponse({"result": "bad",
                                                     "mensaje": u"Error, archivo Propuesta Práctica Antiplagio solo en .doc, docx."})

                if f.is_valid():
                    propuesta = RevisionPropuestaComplexivoPosgrado.objects.get(pk=request.POST['id'])
                    if f.cleaned_data['aprobar']:
                        archivo = ArchivoRevisionPropuestaComplexivoPosgrado(
                            revisionpropuestacomplexivoposgrado=propuesta, archivo=newfile, tipo=3,
                            fecha=datetime.now())
                        archivo.save(request)
                        log(u"Calificación de ensayo  %s a revision[%s], posgrado" % (archivo, propuesta.id), request,
                            "add")
                    else:
                        if newfilec:
                            archivo = ArchivoRevisionPropuestaComplexivoPosgrado(
                                revisionpropuestacomplexivoposgrado=propuesta, archivo=newfilec, tipo=4,
                                fecha=datetime.now())
                            archivo.save(request)
                            log(u"Rechazo el ensayo %s a revision[%s], posgrado" % (archivo, propuesta.id),
                                request, "add")
                    propuesta.fecharevision = datetime.now()
                    propuesta.observacion = f.cleaned_data['observaciones']
                    propuesta.observacion = propuesta.observacion.upper()
                    if f.cleaned_data['rechazar']:
                        propuesta.estado = 3
                    if f.cleaned_data['aprobar']:
                        if f.cleaned_data['plagio']:
                            porcentaje_plagio =  f.cleaned_data['plagio']
                        else:
                            porcentaje_plagio= 0

                        propuesta.porcentajeurkund = porcentaje_plagio
                        if f.cleaned_data['plagio']:
                            if float(f.cleaned_data['plagio']) <= 15:
                                propuesta.estado = 2
                            else:
                                propuesta.estado = 3
                        propuesta.calificacion = f.cleaned_data['calificacion']
                    if f.cleaned_data['calificacion']:
                        propuesta.estado = 2

                    if not f.cleaned_data['rechazar'] and not f.cleaned_data['aprobar']:
                        propuesta.estado = 4
                    propuesta.save(request)
                    if propuesta.tematitulacionposgradomatricula:
                        propuesta_maestrante = propuesta.tematitulacionposgradomatricula.propuestatema
                    else:
                        propuesta_maestrante = propuesta.tematitulacionposgradomatriculacabecera.propuestatema

                    log(u"Aprobo/Reprobo  el ensayo [%s] con línea de investigación: %s" % (
                    propuesta.id,propuesta_maestrante), request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error, ar guardar los datos.'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrio un problema al subir archivo.'})

        elif action == 'editdocensayo':
            try:
                f = ComplexivoCalificarPropuestaEnsayoForm(request.POST, request.FILES)
                newfile = None
                newfilec = None

                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        if newfile.size > 52428800:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                        elif newfile.size <= 0:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, el archivo Urkund esta vacío."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf':
                                newfile._name = generar_nombre("urkund_", newfile._name)
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo Urkund solo en pdf."})
                if 'correccion' in request.FILES:
                    newfilec = request.FILES['correccion']
                    if newfilec:
                        if newfilec.size > 52428800:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                        elif newfilec.size <= 0:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Error, el archivo correcciones esta vacío."})
                        else:
                            newfilesd = newfilec._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.doc' or ext == '.docx' or ext == '.pdf':
                                newfilec._name = generar_nombre("correccion_", newfilec._name)
                            else:
                                return JsonResponse({"result": "bad",
                                                     "mensaje": u"Error, archivo correcciones solo en .doc, docx, pdf."})

                if f.is_valid():
                    propuesta = RevisionPropuestaComplexivoPosgrado.objects.get(pk=request.POST['id'])

                    if newfile:
                        if propuesta.get_urkund():
                            archivo = propuesta.get_urkund()
                            archivo.archivo = newfile
                        else:
                            archivo = ArchivoRevisionPropuestaComplexivoPosgrado(
                                revisionpropuestacomplexivoposgrado=propuesta, archivo=newfile, tipo=3,
                                fecha=datetime.now())
                        archivo.save(request)
                        log(u"Añade archivo de correccion %s a revision[%s]" % (archivo, propuesta.id), request, "edit")
                    if newfilec:
                        if propuesta.get_correccion():
                            archivo = propuesta.get_correccion()
                            archivo.archivo = newfilec
                        else:
                            archivo = ArchivoRevisionPropuestaComplexivoPosgrado(
                                revisionpropuestacomplexivoposgrado=propuesta, archivo=newfilec, tipo=4,
                                fecha=datetime.now())
                        archivo.save(request)
                        log(u"Añade archivo de correccion %s a revision[%s]" % (archivo, propuesta.id), request, "edit")


                    propuesta.observacion = f.cleaned_data['observaciones']
                    propuesta.observacion = propuesta.observacion.upper()

                    if f.cleaned_data['rechazar']:
                        propuesta.estado = 3
                    if f.cleaned_data['aprobar']:
                        propuesta.calificacion = f.cleaned_data['calificacion']
                        propuesta.porcentajeurkund = f.cleaned_data['plagio']
                        propuesta.observacion = propuesta.observacion.upper()
                        propuesta.estado = 2
                    if not f.cleaned_data['rechazar'] and not f.cleaned_data['aprobar']:
                        propuesta.estado = 4
                    propuesta.save(request)
                    if propuesta.tematitulacionposgradomatricula:
                        propuesta_maestrante =propuesta.tematitulacionposgradomatricula.propuestatema
                    else:
                        propuesta_maestrante =propuesta.tematitulacionposgradomatriculacabecera.propuestatema

                    log(u"Aprobo/Reprobo a propuesta examen complexivo [%s] con línea de investigación: %s" % (
                    propuesta.id, propuesta_maestrante), request, "add")
                    return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrio un problema al subir archivo.'})

        elif action == 'delete_configuracion_informe':
            try:
                id= int(request.POST['id'])
                configuracion_informe = ConfiguraInformePrograma.objects.get(pk=id)
                configuracion_informe.status = False
                configuracion_informe.save(request)
                log(u'Elimino configuracion por programa mecanismo informe posgrado: %s' % configuracion_informe, request, "delete")
                res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'deletecaltribunal':
            try:
                idmaestrantegrupo = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['idtematitulacion'])
                idmaestrantegrupo.rubrica_id = None
                idmaestrantegrupo.save()
                listadocalificacionestribunales = idmaestrantegrupo.calificaciontitulacionposgrado_set.filter(status=True)
                listadocalificacionestribunales.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                pass

        elif action == 'deletecaltribunalpareja':
            try:
                idmaestrantegrupo = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=request.POST['idtematitulacion'])

                for participante in idmaestrantegrupo.obtener_parejas():
                    participante.rubrica_id = None
                    participante.save()
                    listadocalificacionestribunales = participante.calificaciontitulacionposgrado_set.filter(status=True)
                    listadocalificacionestribunales.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                pass

        elif action == 'importar_nota_moodle':
            try:
                grupo = GrupoTitulacionPostgrado.objects.get(pk=request.POST['id'])
                suma=0
                contador=0
                if grupo.maestrantes_inscritos():
                    for detallegrupotitulacion in grupo.maestrantes_inscritos():
                        suma = 0
                        contador = 0
                        persona = detallegrupotitulacion.inscrito.matricula.inscripcion.persona
                        if grupo.notas_de_moodle_posgrado(persona):
                            for notasmooc in grupo.notas_de_moodle_posgrado(persona):
                                nombre_campo_moodle = notasmooc[1] if notasmooc[1] else ''
                                suma+= float(notasmooc[0]) if notasmooc[0] else 0
                                contador+=1
                                if ModeloEvualativoDetallePosgrado.objects.filter(status=True,  modelo=grupo.modeloevaluativo,nombre=nombre_campo_moodle):
                                    detallemodelo=ModeloEvualativoDetallePosgrado.objects.filter(status=True,  modelo=grupo.modeloevaluativo,nombre=nombre_campo_moodle)[0]
                                    if NotaDetalleGrupoTitulacionPostgrado.objects.values('id').filter(status=True,
                                                                                                       detallegrupotitulacion=detallegrupotitulacion,
                                                                                                       modeloevaluativodetalle=detallemodelo,
                                                                                                       modeloevaluativodetalle__nombre=nombre_campo_moodle).exists():
                                        notaguardada=NotaDetalleGrupoTitulacionPostgrado.objects.filter(status=True,
                                                                                                       detallegrupotitulacion=detallegrupotitulacion,
                                                                                                       modeloevaluativodetalle=detallemodelo,
                                                                                                       modeloevaluativodetalle__nombre=nombre_campo_moodle)[0]
                                        notaguardada.nota= float(notasmooc[0]) if notasmooc[0] else 0
                                        notaguardada.save(request)
                                    else:
                                        notaguardada = NotaDetalleGrupoTitulacionPostgrado(
                                            detallegrupotitulacion=detallegrupotitulacion,
                                            modeloevaluativodetalle=detallemodelo,
                                            nota=float(notasmooc[0]) if notasmooc[0] else 0
                                        )
                                        notaguardada.save(request)
                                else:
                                    raise NameError(u"El nombre de la categoria del modelo evaluativo no concide con lo configurado, moode (%s)" % (nombre_campo_moodle))

                            detallegrupotitulacion.nota = null_to_decimal(suma/contador,0)
                            detallegrupotitulacion.save(request)
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"No existen inscritos registrados."})
                return JsonResponse({"result": True, "mensaje": u"Notas importadas correctamente."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error %s" %ex })

        elif action == 'revisarsolicitudprorrogatitulacion':
            try:
                f = FormSolicitudProrrogaIngresoTemaMatricula(request.POST)
                if f.is_valid():
                    solicitud = SolicitudProrrogaIngresoTemaMatricula.objects.get(pk=request.POST['id'])
                    if int(f.cleaned_data['estado']) == 3:
                        solicitud.estado = 3  # rechazo
                        solicitud.fechainicioprorroga = None
                        solicitud.fechafinprorroga = None
                    else:
                        solicitud.estado = 2  # apruebo
                        solicitud.fechainicioprorroga = f.cleaned_data['fechainicioprorroga']
                        solicitud.fechafinprorroga = f.cleaned_data['fechafinprorroga']
                    solicitud.save(request)
                    historial = HistorialSolicitudProrrogaIngresoTemaMatricula(
                        solicitud=solicitud,
                        persona=persona,
                        estado=solicitud.estado,
                    )
                    historial.save(request)

                    log(u'Reviso solicitud prorroga de propuesta titulacion: %s - estado: %s' % (solicitud,solicitud.get_estado_display()), request, "edit")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'add_informe_tribunal':
            try:
                f = FormInforme(request.POST)
                if f.is_valid():
                    informe = Informe(
                        descripcion = request.POST['descripcion'],
                        tipo = request.POST['tipo'],
                    )
                    informe.save(request)
                    log(u'Adiciono informe posgrado: %s' % informe, request, "add")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'edit_informe_tribunal':
            try:
                f = FormInforme(request.POST)
                if f.is_valid():
                    informe = Informe.objects.get(pk=request.POST['id'])
                    informe.descripcion = request.POST['descripcion']
                    informe.tipo = request.POST['tipo']
                    informe.save(request)
                    log(u'Editó informe posgrado: %s' % informe, request, "edit")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'delete_informe_tribunal':
            try:
                with transaction.atomic():
                    instancia = Informe.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino informe posgrado: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'add_seccion_informe_tribunal':
            try:
                f = FormSeccionInforme(request.POST)
                if f.is_valid():
                    seccion_informe = SeccionInforme(
                        informe_id = request.POST['id_informe'],
                        seccion_id = request.POST['seccion'],
                        orden = request.POST['orden']
                    )
                    seccion_informe.save(request)
                    log(u'Adiciono seccion informe posgrado: %s' % seccion_informe, request, "add")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'edit_seccion_informe_tribunal':
            try:
                f = FormSeccionInforme(request.POST)
                if f.is_valid():
                    seccion_informe = SeccionInforme.objects.get(pk=request.POST['id'])
                    seccion_informe.seccion.id = request.POST['seccion']
                    seccion_informe.orden = request.POST['orden']
                    seccion_informe.save(request)
                    log(u'Modificó sección informe posgrado: %s' % seccion_informe, request, "add")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'delete_seccion_informe_tribunal':
            try:
                with transaction.atomic():
                    instancia = SeccionInforme.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino seccion informe posgrado: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'add_pregunta_informe':
            try:
                f = FormPreguntaInforme(request.POST)
                if f.is_valid():
                    pregunta = Pregunta(
                        descripcion=request.POST['descripcion']
                    )
                    pregunta.save(request)
                    log(u'Adiciono pregunta informe posgrado: %s' % pregunta, request, "add")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'edit_pregunta_informe':
            try:
                f = FormPreguntaInforme(request.POST)
                if f.is_valid():
                    pregunta = Pregunta.objects.get(pk=request.POST['id'])
                    pregunta.descripcion = request.POST['descripcion']
                    pregunta.save(request)
                    log(u'Modificó pregunta posgrado: %s' % pregunta, request, "add")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'delete_pregunta_informe':
            try:
                with transaction.atomic():
                    instancia = Pregunta.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino pregunta informe posgrado: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'add_pregunta_seccion_informe':
            try:
                f = FormSeccionInformePregunta(request.POST)
                if f.is_valid():
                    seccion_informe_pregunta = SeccionInformePregunta(
                        seccion_informe_id = request.POST['id_seccion_informe'],
                        pregunta_id= request.POST['pregunta'],
                        tipo_pregunta=request.POST['tipo_pregunta']
                    )
                    seccion_informe_pregunta.save(request)
                    log(u'Adiciono pregunta a la seccion del informe posgrado: %s' % seccion_informe_pregunta, request, "add")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'edit_pregunta_seccion_informe':
            try:
                f = FormSeccionInformePregunta(request.POST)
                if f.is_valid():
                    seccion_informe_pregunta = SeccionInformePregunta.objects.get(pk=request.POST['id'])
                    seccion_informe_pregunta.pregunta = request.POST['pregunta']
                    seccion_informe_pregunta.tipo_pregunta = request.POST['tipo_pregunta']
                    seccion_informe_pregunta.save(request)
                    log(u'Modificó pregunta de la seccion del informe posgrado: %s' % seccion_informe_pregunta, request, "add")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'delete_pregunta_seccion_informe':
            try:
                with transaction.atomic():
                    instancia = SeccionInformePregunta.objects.get(pk=int(request.POST['id']))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino pregunta de la seccion del informe posgrado: %s' % instancia, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'add_configuracion_informe_tribunal':
            try:
                f = FormConfiguracionInforme(request.POST)
                if f.is_valid():

                    informe = ConfiguraInformePrograma(
                        informe_id = request.POST['informe'],
                        mecanismotitulacionposgrado_id = request.POST['mecanismotitulacionposgrado'],
                        programa_id = request.POST['programa'],
                        estado = True if 'estado' in request.POST else False
                    )
                    informe.save(request)
                    log(u'Adiciono configuracion informe posgrado: %s' % informe, request, "add")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'edit_configuracion_informe_tribunal':
            try:
                f = FormConfiguracionInforme(request.POST)
                if f.is_valid():
                    configuracion = ConfiguraInformePrograma.objects.get(pk=request.POST['id'])
                    configuracion.informe = request.POST['informe']
                    configuracion.mecanismotitulacionposgrado = request.POST['mecanismotitulacionposgrado']
                    configuracion.programa = request.POST['programa']
                    configuracion.estado = request.POST['estado']
                    configuracion.save(request)
                    log(u'Editó configuracion informe posgrado: %s' % configuracion, request, "edit")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'deletesolicitud':
            try:
                solicitud = TemaTitulacionPosgradoProfesor.objects.get(pk=request.POST['id'])
                solicitud.status = False
                solicitud.save()
                log(u'Eliminó solicitud tema titulacion posgrado: %s' % solicitud, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'actualizar_estado_configuracion_informe':
            try:
                configuracion_informe= ConfiguraInformePrograma.objects.get(pk=request.POST['id'])

                existe_informe_ya_configurado = ConfiguraInformePrograma.objects.filter(
                    status=True,
                    mecanismotitulacionposgrado =configuracion_informe.mecanismotitulacionposgrado,
                    programa = configuracion_informe.programa,
                    estado =True
                ).exclude(pk=configuracion_informe.pk).exists()

                if not existe_informe_ya_configurado:
                    configuracion_informe.estado = False if configuracion_informe.estado else True
                    configuracion_informe.save(request)
                    mensaje="Estado actualizado correctamente!"
                    log(u'Actualizó estado informe  posgrado: %s' % configuracion_informe, request, "edit")
                else:
                    mensaje = "No puede teneder dos informes activos en un mismo mecanismo"


                return JsonResponse({"result": "ok","mensaje":mensaje})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action =='importar_numero_acta':
            try:
                if 'archivo_excel' in request.FILES:
                    archivo = request.FILES['archivo_excel']
                    # Utiliza pandas para leer el archivo Excel
                    df = pd.read_excel(archivo)
                    # Itera sobre cada fila del DataFrame
                    for fila in df.itertuples(index=False):
                        cedula = fila.CEDULA
                        id_registro = fila.ID_PROPUESTA
                        numero_de_acta = fila.NUMERO_DE_ACTA

                        try:
                            eTemaTitulacionPosgradoMatricula = TemaTitulacionPosgradoMatricula.objects.get(status=True,pk=int(id_registro),matricula__inscripcion__persona__cedula__contains =cedula)
                            eTemaTitulacionPosgradoMatricula.asignar_numero_acta_graduado(request, numero_de_acta)
                        except TemaTitulacionPosgradoMatricula.DoesNotExist:
                            return JsonResponse({"result":True ,"mensaje": f"No se encontró registro: Cédula {cedula}, ID {id_registro}"})

                    return JsonResponse({"result":False,"mensaje": u"Importación correcta"})

                else:
                    return JsonResponse({"result":True, "mensaje": u"Seleccione una archivo"})
            except Exception as ex:
                transaction.set_rollback(True)

        elif action == 'firma_masiva_complexivo_posgrado':
            try:
                firma = request.FILES["firma"]
                contrasenaCertificado = request.POST['palabraclave']
                firmado_por = int(request.POST.get('firmado_por', '0'))
                id_string = request.POST.get('ids_tema', 0)
                id_list = ast.literal_eval(id_string)
                # Si id_list no es una lista, conviértelo en una lista con un solo elemento
                if not isinstance(id_list, tuple):
                    id_list = (id_list,)

                eTemaTitulacionPosgradoMatriculas = TemaTitulacionPosgradoMatricula.objects.filter(pk__in = id_list)

                bytes_certificado = firma.read()
                extension_certificado = os.path.splitext(firma.name)[1][1:]

                if firmado_por == 0:
                    return JsonResponse({"result": "bad", "mensaje":"No se identifica quien firma"})
                elif firmado_por == 3:
                    palabras = 'Secretaría técnica de posgrado'
                elif firmado_por == 4:
                    palabras = 'Coordinación del programa'
                else:
                    return JsonResponse({"result": "bad", "mensaje": "No se identifica quien firma"})

                tiempos_firma = []

                for tema in eTemaTitulacionPosgradoMatriculas:
                    archivo_a_firmar = tema.actaaprobacionexamen
                    x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(archivo_a_firmar.url, palabras)
                    if firmado_por == 3:
                        if x == None or y == None:
                            palabras = 'Gestión de titulación'
                            x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(archivo_a_firmar.url, palabras)

                    if palabras == 'Secretaría técnica de posgrado' or palabras == 'Gestión de titulación':
                        if x <= 270:
                            x = 300
                    datau = JavaFirmaEc(
                        archivo_a_firmar=archivo_a_firmar, archivo_certificado=bytes_certificado,
                        extension_certificado=extension_certificado,
                        password_certificado=contrasenaCertificado,
                        page=int(numpaginafirma), reason='', lx=x + 50, ly=y + 20
                    ).sign_and_get_content_bytes()

                    documento_a_firmar = io.BytesIO()
                    documento_a_firmar.write(datau)
                    documento_a_firmar.seek(0)
                    tema.estado_acta_firma = firmado_por
                    tema.save(request)
                    tema.actaaprobacionexamen.save(f'{tema.actaaprobacionexamen.name.split("/")[-1].replace(".pdf", "")}_firmado.pdf', ContentFile(documento_a_firmar.read()))
                    log(u"Firma de acta de aprobación complexivo, por: %s de %s" % (tema.get_estado_acta_firma_display(), tema), request,  "change")
                    historial = HistorialFirmaActaAprobacionComplexivo(
                        tema=tema,
                        persona=persona,
                        actaaprobacionfirmada= tema.actaaprobacionexamen,
                        estado_acta_firma=firmado_por
                    )
                    historial.save(request)


                return JsonResponse({"result":False,"mensaje": u"firma correcta"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s" % ex})

        elif action == 'add_sede_titulacion':
            try:
                pk = request.POST.get('id', None)
                eEncuestaTitulacionPosgrado = EncuestaTitulacionPosgrado.objects.get(pk=pk)
                f = SeleccionSedeForm(request.POST)
                id_canton =request.POST['canton']
                eCanton = Canton.objects.get(pk=id_canton)
                eSedeEncuestaTitulacionPosgrado = SedeEncuestaTitulacionPosgrado(
                    encuestatitulacionposgrado = eEncuestaTitulacionPosgrado,
                    canton = eCanton
                )
                eSedeEncuestaTitulacionPosgrado.save(request)
                log(u'Agrego sede  %s' % eSedeEncuestaTitulacionPosgrado, request, "add")
                return JsonResponse({"result": True, 'mensaje': 'registro Exitos0'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos."})

        elif action == 'editarjornadagraduacion':
            try:
                pk = request.POST.get('id', None)
                eInscripcionEncuestaTitulacionPosgrado = InscripcionEncuestaTitulacionPosgrado.objects.get(pk=pk)
                form = SeleleccionSedeJornadaForm(request.POST)
                if request.POST['jornadasedeencuestatitulacionposgrado'] == '':
                    raise NameError("Seleccione la jornada")

                RespuestaSedeInscripcionEncuestaPk = int(request.POST.get('RespuestaSedeInscripcionEncuestaPk', None))
                if RespuestaSedeInscripcionEncuestaPk== 0:
                    eRespuestaSedeInscripcionEncuesta = RespuestaSedeInscripcionEncuesta(
                        inscripcionencuestatitulacionposgrado_id = pk,
                        jornadasedeencuestatitulacionposgrado_id =  request.POST['jornadasedeencuestatitulacionposgrado']
                    )
                    eRespuestaSedeInscripcionEncuesta.save(request)
                else:
                    eRespuestaSedeInscripcionEncuesta = RespuestaSedeInscripcionEncuesta.objects.get(pk=RespuestaSedeInscripcionEncuestaPk)
                    eRespuestaSedeInscripcionEncuesta.jornadasedeencuestatitulacionposgrado_id = request.POST['jornadasedeencuestatitulacionposgrado']
                    eRespuestaSedeInscripcionEncuesta.save(request)
                eInscripcionEncuestaTitulacionPosgrado.respondio = True
                eInscripcionEncuestaTitulacionPosgrado.participa = True
                eInscripcionEncuestaTitulacionPosgrado.save(request)
                log(u'Agrego /edito jornada  %s' % eRespuestaSedeInscripcionEncuesta, request, "add")
                return JsonResponse({"result": True, 'mensaje': 'registro Exitoso'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos."})

        elif action == 'edit_inicio_fin_encuesta':
            try:
                pk = request.POST.get('id', None)
                eEncuestaTitulacionPosgrado = EncuestaTitulacionPosgrado.objects.get(pk=pk)
                f = CronogramaEncuestaForm(request.POST)
                if f.is_valid():
                    eEncuestaTitulacionPosgrado.inicio =  f.cleaned_data['inicio']
                    eEncuestaTitulacionPosgrado.fin =  f.cleaned_data['fin']
                    eEncuestaTitulacionPosgrado.activo =  f.cleaned_data['activo']
                    eEncuestaTitulacionPosgrado.save(request)

                    if eEncuestaTitulacionPosgrado.activo:
                        eEncuestaTitulacionPosgrado.notificar_encuesta(request)


                log(u'Edito inicio fin y activo de encuesta sede %s' % eEncuestaTitulacionPosgrado, request, "add")
                return JsonResponse({"result": True, 'mensaje': 'registro Exitoso'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos."})

        elif action == 'addhorarioporsede':
            try:
                pk = request.POST.get('id', None)
                eSedeEncuestaTitulacionPosgrado = SedeEncuestaTitulacionPosgrado.objects.get(pk=pk)
                f = JornadaEncuestaSedeForm(request.POST)
                if f.is_valid():
                    eJornadaSedeEncuestaTitulacionPosgrado = JornadaSedeEncuestaTitulacionPosgrado(
                        sedeencuestatitulacionposgrado = eSedeEncuestaTitulacionPosgrado,
                        fecha = f.cleaned_data['fecha'],
                        hora_inicio = f.cleaned_data['hora_inicio'],
                        hora_fin = f.cleaned_data['hora_fin'],
                        cupo = f.cleaned_data['cupo']
                    )
                    eJornadaSedeEncuestaTitulacionPosgrado.save(request)
                    log(u'Agrego jornada sede  %s' % eJornadaSedeEncuestaTitulacionPosgrado, request, "add")
                else:
                        return JsonResponse({'error': False, "form": [{k: v[0]} for k, v in f.errors.items()],
                                             "message": "Error en el formulario"})

                return JsonResponse({"result": True, 'mensaje': f'registro Exitos0'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": f"Error al guardar los datos. {ex.__str__()}"})

        elif action == 'editjornada':
            try:
                pk = request.POST.get('id', None)
                eJornadaSedeEncuestaTitulacionPosgrado = JornadaSedeEncuestaTitulacionPosgrado.objects.get(pk=pk)
                f = JornadaEncuestaSedeForm(request.POST)
                if f.is_valid():
                    eJornadaSedeEncuestaTitulacionPosgrado.fecha = f.cleaned_data['fecha']
                    eJornadaSedeEncuestaTitulacionPosgrado.hora_inicio = f.cleaned_data['hora_inicio']
                    eJornadaSedeEncuestaTitulacionPosgrado.hora_fin = f.cleaned_data['hora_fin']
                    eJornadaSedeEncuestaTitulacionPosgrado.cupo = f.cleaned_data['cupo']
                    eJornadaSedeEncuestaTitulacionPosgrado.save(request)
                    log(u'edito jornada sede  %s' % eJornadaSedeEncuestaTitulacionPosgrado, request, "edit")
                else:
                    return JsonResponse({'error': False, "form": [{k: v[0]} for k, v in f.errors.items()],"message": "Error en el formulario"})

                return JsonResponse({"result": True, 'mensaje': f'registro Exitos0'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": f"Error al guardar los datos. {ex.__str__()}"})

        elif action == 'deletejornada':
            try:
                eJornadaSedeEncuestaTitulacionPosgrado = JornadaSedeEncuestaTitulacionPosgrado.objects.get(
                    pk=int(request.POST['id']))
                eJornadaSedeEncuestaTitulacionPosgrado.status = False
                eJornadaSedeEncuestaTitulacionPosgrado.save(request)
                log(f"Eliminó jornada de sede:{eJornadaSedeEncuestaTitulacionPosgrado}", request, 'del')
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()

        elif action == 'deletesede':
            try:
                eSedeEncuestaTitulacionPosgrado = SedeEncuestaTitulacionPosgrado.objects.get(pk=int(request.POST['id']))
                eSedeEncuestaTitulacionPosgrado.status = False
                eSedeEncuestaTitulacionPosgrado.save(request)
                log(f"Eliminó sede:{eSedeEncuestaTitulacionPosgrado}", request, 'del')
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()

        elif action == 'delencuestaperiodo':
            try:
                eEncuestaTitulacionPosgrado = EncuestaTitulacionPosgrado.objects.get(pk=int(request.POST['id']))
                eEncuestaTitulacionPosgrado.status = False
                eEncuestaTitulacionPosgrado.save(request)
                log(f"Eliminó encuesta titulacion:{eEncuestaTitulacionPosgrado}", request, 'del')
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()

        elif action == 'delinscripcionencuestatitulacionposgrado':
            try:
                eInscripcionEncuestaTitulacionPosgrado = InscripcionEncuestaTitulacionPosgrado.objects.get(pk=int(request.POST['id']))
                eInscripcionEncuestaTitulacionPosgrado.status = False
                eInscripcionEncuestaTitulacionPosgrado.save(request)
                log(f"Eliminó eInscripcionEncuestaTitulacionPosgrado titulacion:{eInscripcionEncuestaTitulacionPosgrado}", request, 'del')
                return JsonResponse({"result": True, "error": False})
            except Exception as ex:
                transaction.rollback()

        elif action == 'exportar_poblacion':
            try:
                id_string = request.POST.get('ids', 0)

                idencuesta = int(request.POST.get('idencuesta', 0))
                id_list = ast.literal_eval(id_string)
                eTemaTitulacionPosgradoMatriculas = TemaTitulacionPosgradoMatricula.objects.filter(status=True, pk__in=id_list)
                eEncuestaTitulacionPosgrado = EncuestaTitulacionPosgrado.objects.get(pk=idencuesta)
                for eTemaTitulacionPosgradoMatricula in eTemaTitulacionPosgradoMatriculas:
                    eInscripcionEncuestaTitulacionPosgrado = InscripcionEncuestaTitulacionPosgrado(
                        encuestatitulacionposgrado=eEncuestaTitulacionPosgrado,
                        inscripcion=eTemaTitulacionPosgradoMatricula.matricula.inscripcion,
                        respondio=False
                    )
                    eInscripcionEncuestaTitulacionPosgrado.save(request)

                return JsonResponse({"result": False, 'mensaje': 'Guardado correcto','rt': f"/adm_configuracionpropuesta?action=configurarencuesta_resultados&id={eEncuestaTitulacionPosgrado.pk}"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"{ex.__str__()}"})

        elif action == 'exportar_poblacion_graduacion_ceremonia_excel':
            try:
                file = request.FILES['file']
                idencuesta = int(request.POST.get('idencuesta', 0))
                df =pd.read_excel(file, dtype={'cedula': str}, engine='openpyxl')
                # Asumiendo que el archivo tiene una columna llamada 'cedula'
                cedulas = df['cedula'].tolist()
                # Filtrar en la base de datos las cédulas que coinciden
                eTemaTitulacionPosgradoMatriculaPk = TemaTitulacionPosgradoMatricula.objects.filter(status=True,matricula__inscripcion__graduado__isnull=False,aprobado = True,actacerrada =True,
                    matricula__inscripcion__persona__cedula__in=cedulas).values_list('id',flat=True)

                eTemaTitulacionPosgradoMatriculas = TemaTitulacionPosgradoMatricula.objects.filter(status=True, pk__in=eTemaTitulacionPosgradoMatriculaPk)
                eEncuestaTitulacionPosgrado = EncuestaTitulacionPosgrado.objects.get(pk=idencuesta)
                for eTemaTitulacionPosgradoMatricula in eTemaTitulacionPosgradoMatriculas:
                    eInscripcionEncuestaTitulacionPosgrado = InscripcionEncuestaTitulacionPosgrado(
                        encuestatitulacionposgrado=eEncuestaTitulacionPosgrado,
                        inscripcion=eTemaTitulacionPosgradoMatricula.matricula.inscripcion,
                        respondio=False
                    )
                    eInscripcionEncuestaTitulacionPosgrado.save(request)

                return JsonResponse({"result": "ok", 'mensaje': 'Guardado correcto','rt': f"/adm_configuracionpropuesta?action=configurarencuesta_resultados&id={eEncuestaTitulacionPosgrado.pk}"})
            except Exception as ex:
                pass

        elif action == 'importar_poblacion_graduacion_ceremonia':
            try:
                file = request.FILES['file']
                df =pd.read_excel(file, dtype={'cedula': str}, engine='openpyxl')
                # Asumiendo que el archivo tiene una columna llamada 'cedula'
                cedulas = df['cedula'].tolist()
                # Filtrar en la base de datos las cédulas que coinciden
                graduados = TemaTitulacionPosgradoMatricula.objects.filter(status=True,matricula__inscripcion__graduado__isnull=False,aprobado = True,actacerrada =True,
                    matricula__inscripcion__persona__cedula__in=cedulas
                )

                # Obtener las cédulas que se encontraron en la base de datos
                cedulas_encontradas = list(graduados.values_list('matricula__inscripcion__persona__cedula', flat=True))

                # Identificar las cédulas que no se encontraron
                cedulas_no_encontradas = list(set(cedulas) - set(cedulas_encontradas))

                temas_no_encontrados = TemaTitulacionPosgradoMatricula.objects.filter(status=True,matricula__inscripcion__persona__cedula__in=cedulas_no_encontradas)
                data = {
                    'graduados': graduados,
                    "cedulas_no_encontradas": cedulas_no_encontradas,
                    "temas_no_encontrados": temas_no_encontrados,
                }
                template = get_template('adm_configuracionpropuesta/encuestas/configuracion/snipper_graduados_seleccionados.html')
                json_content = template.render(data, request)
                return JsonResponse({"result": "ok", "html": json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "message":  f'Ocurrió un error al visualizar la población: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}'})

        elif action == 'importar_ubicacion_masiva_sede_graduacion':
            try:
                file = request.FILES['archivo_excel']
                df =pd.read_excel(file, usecols=['ID','BLOQUE', 'FILA', 'ASIENTO'], dtype={'ID': int}, engine='openpyxl')
                # Iterar sobre las filas del DataFrame
                for index, row in df.iterrows():
                    # Obtener los datos de cada fila
                    id = row['ID']  # Obtener el ID
                    bloque = row['BLOQUE']  # Obtener el bloque
                    fila = row['FILA']  # Obtener la fila
                    asiento = row['ASIENTO']  # Obtener el asiento

                    # Filtrar el registro en la base de datos por ID
                    eInscripcionEncuestaTitulacionPosgrado = InscripcionEncuestaTitulacionPosgrado.objects.filter(status=True, pk=id).first()

                    if eInscripcionEncuestaTitulacionPosgrado:
                        # Actualizar los campos correspondientes
                        eInscripcionEncuestaTitulacionPosgrado.bloque = bloque
                        eInscripcionEncuestaTitulacionPosgrado.fila = fila
                        eInscripcionEncuestaTitulacionPosgrado.asiento = asiento

                        # Guardar los cambios en la base de datos
                        eInscripcionEncuestaTitulacionPosgrado.save(request)

                return JsonResponse({"result": "ok", "mensaje": "Datos actualizados correctamente."})
            except Exception as ex:
                pass

        elif action == 'rechazar_profesor_solicitudtema':
            try:
                f = FormObservacion(request.POST)
                if f.is_valid():
                    eTemaTitulacionPosgradoProfesor = TemaTitulacionPosgradoProfesor.objects.get(pk=request.POST['id'])
                    eTemaTitulacionPosgradoProfesor.rechazado = True
                    eTemaTitulacionPosgradoProfesor.aprobado = False
                    eTemaTitulacionPosgradoProfesor.observacion = f.cleaned_data['observacion']
                    eTemaTitulacionPosgradoProfesor.save(request)

                    if eTemaTitulacionPosgradoProfesor.rechazado:
                        valor_aprobado = 3
                        observacion = 'Rechazó solicitud de profesor para ser posible tutor del tema de titulación.'
                        historial = SolicitudTutorTemaHistorial(
                            tematitulacionposgradoprofesor=eTemaTitulacionPosgradoProfesor,
                            persona=persona,
                            estado=valor_aprobado,
                            observacion=observacion

                        )
                        historial.save(request)
                        para = eTemaTitulacionPosgradoProfesor.profesor.persona
                        asunto = u"SOLICITUD TUTOR PROPUESTA POSGRADO"
                        noti = Notificacion(cuerpo=eTemaTitulacionPosgradoProfesor.observacion, titulo=asunto,
                                            destinatario=para,
                                            url='/pro_tutoriaposgrado?action=solicitudes', prioridad=1, app_label='SGA',
                                            fecha_hora_visible=datetime.now() + timedelta(days=3),
                                            tipo=2, en_proceso=False)
                        noti.save()

                    log(u'Rechazo solicitud profesor: %s' % eTemaTitulacionPosgradoProfesor, request, "edit")
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        elif action == 'guardar_ubicacion_bloque':
            try:

                id = int(request.POST.get('id', '0') or '0')
                value = request.POST['value']
                eInscripcionEncuestaTitulacionPosgrado = InscripcionEncuestaTitulacionPosgrado.objects.get(pk=id)
                eInscripcionEncuestaTitulacionPosgrado.bloque= value
                eInscripcionEncuestaTitulacionPosgrado.save(request)
                log(u'actualizo bloque: %s' % eInscripcionEncuestaTitulacionPosgrado, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

        elif action == 'guardar_ubicacion_fila':
            try:

                id = int(request.POST.get('id', '0') or '0')
                value = request.POST['value']
                eInscripcionEncuestaTitulacionPosgrado = InscripcionEncuestaTitulacionPosgrado.objects.get(pk=id)
                eInscripcionEncuestaTitulacionPosgrado.fila = value
                eInscripcionEncuestaTitulacionPosgrado.save(request)
                log(u'actualizo fila: %s' % eInscripcionEncuestaTitulacionPosgrado, request, "edit")


                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

        elif action == 'guardar_ubicacion_asiento':
            try:

                id = int(request.POST.get('id', '0') or '0')
                value = request.POST['value']
                eInscripcionEncuestaTitulacionPosgrado = InscripcionEncuestaTitulacionPosgrado.objects.get(pk=id)
                eInscripcionEncuestaTitulacionPosgrado.asiento = value
                eInscripcionEncuestaTitulacionPosgrado.save(request)
                log(u'actualizo asiento: %s' % eInscripcionEncuestaTitulacionPosgrado, request, "edit")

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

        elif action == 'generar_qr_pdf_sede_graduacion':
            try:

                id = int(request.POST.get('id', '0') or '0')
                eInscripcionEncuestaTitulacionPosgrado = InscripcionEncuestaTitulacionPosgrado.objects.get(pk=id)
                eInscripcionEncuestaTitulacionPosgrado.generar_qr_pdf_sede_graduacion(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

        elif action == 'generar_masiva_qr_pdf_sede_graduacion':
            try:
                from sga.proccess_background_sga import generar_qr_graduaciones_posgrado_masivo
                a = generar_qr_graduaciones_posgrado_masivo(request)
                a.start()

                return JsonResponse({"result": "ok",'mensaje':"Se está ejecutando la generación masiva, espere la notificación"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

        elif action == 'marcar_asistencia_sede_graduacion':
            try:

                id = int(request.POST.get('id', '0') or '0')
                eInscripcionEncuestaTitulacionPosgrado = InscripcionEncuestaTitulacionPosgrado.objects.get(pk=id)
                eInscripcionEncuestaTitulacionPosgrado.asistio = True
                eInscripcionEncuestaTitulacionPosgrado.save(request)
                log(u'marco asistencia sede graduacion : %s' % eInscripcionEncuestaTitulacionPosgrado, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Configuración y presentación de maestrías'
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'descargar_actas_aprobacion_masiva':
                try:
                    id = request.GET.get('id', 0)
                    if id == 0: raise NameError("Parametro no encontrado")
                    eConfiguracionTitulacionPosgrado = ConfiguracionTitulacionPosgrado.objects.get(pk=id)

                    rutas_certificados = []
                    dominiosistema = request.build_absolute_uri('/')[:-1].strip("/")
                    directory = os.path.join(SITE_STORAGE, 'media/zip')
                    try:
                        os.stat(directory)
                    except:
                        os.mkdir(directory)
                    url = os.path.join(SITE_STORAGE, 'media', 'zip','actascomplexivofirmadas.zip')
                    url_zip = url
                    fantasy_zip = zipfile.ZipFile(url, 'w')
                    if eConfiguracionTitulacionPosgrado.propuestas_complexivo_firmas():
                        for tema in eConfiguracionTitulacionPosgrado.propuestas_complexivo_firmas():
                            if tema.actaaprobacionexamen.path:
                                eParalelo = eConfiguracionTitulacionPosgrado.se_encuentra_en_el_paralelo_complexivo(tema)
                                carpeta_inscripcion = f"{eParalelo}/"
                                # Agregar el archivo PDF a la carpeta de la inscripción dentro del ZIP
                                fantasy_zip.write(tema.actaaprobacionexamen.path, carpeta_inscripcion + os.path.basename(tema.actaaprobacionexamen.path))
                                # fantasy_zip.write(ins.rutapdf.path)
                    else:
                        raise NameError('Erro al generar')
                    fantasy_zip.close()
                    response = HttpResponse(open(url_zip, 'rb'), content_type='application/zip')
                    response['Content-Disposition'] = 'attachment; filename=actascomplexivofirmadas.zip'
                    return response


                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            elif action == 'add':
                try:
                    data['title'] = u'Nueva configuración y presentar propuesta maestrante'
                    form = ConfiguracionTitulacionPosgradoForm()
                    data['form'] = form
                    data['persona'] = persona
                    template = get_template("adm_configuracionpropuesta/add.html")
                    return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'agregarencuestatitulacion':
                try:
                    data['title'] = u'Nueva encuesta selección de sedes'
                    id = int(request.GET.get('id','0'))
                    if id == 0:
                        raise NameError("Parametro no encontrado")
                    form = EncuestaTitulacionPosgradoForm()
                    form.cargar_periodo(id)
                    form.cargar_convocatorias(id)
                    data['form'] = form
                    template = get_template("adm_configuracionpropuesta/modal/formmodal.html")
                    return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addencuestagraduaciongeneral':
                try:
                    form = EncuestaTitulacionPosgradoGeneralForm()
                    data['form'] = form
                    template = get_template('adm_configuracionpropuesta/encuestas/graduacion/form.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addrubrica':
                try:
                    form = ConfiguracionRubricaPosgradoForm()
                    data['form'] = form
                    template = get_template("adm_configuracionpropuesta/addrubrica.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addrubricas':
                try:
                    data['title'] = u'Nueva rubrica'
                    form = RubricaPosgradoForm()
                    data['form'] = form
                    data['idrubrica'] = request.GET['idrubrica']
                    return render(request, "adm_configuracionpropuesta/addrubricas.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = ConfiguracionTitulacionPosgradoForm(initial={'periodo': configuracion.periodo,
                                                                        'carrera': configuracion.carrera,
                                                                        'fechainiciotutoria': configuracion.fechainiciotutoria,
                                                                        'fechafintutoria': configuracion.fechafintutoria,
                                                                        'fechainiciopostulacion': configuracion.fechainiciopostulacion,
                                                                        'fechafinpostulacion' : configuracion.fechafinpostulacion,
                                                                        'fechainimaestrante' : configuracion.fechainimaestrante,
                                                                        'fechafinmaestrante' : configuracion.fechafinmaestrante,
                                                                        'publicado' : configuracion.publicado,
                                                                        'tipocomponente': configuracion.tipocomponente})
                    data['configuracion'] = configuracion
                    form.editar()
                    data['form2'] = form
                    template = get_template("adm_configuracionpropuesta/edit.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editrubrica':
                try:
                    data['title'] = u'Editar configuración rubrica posgrado'
                    rubrica = RubricaTitulacionPosgrado.objects.get(pk=int(request.GET['id']))
                    form = ConfiguracionRubricaPosgradoForm(initial={'nombre': rubrica.nombre, 'activo': rubrica.activo})
                    data['rubrica'] = rubrica
                    data['form'] = form
                    data['detallemodelorubrica'] = rubrica.modelorubricatitulacionposgrado_set.filter(status=True).order_by('orden')
                    data['ponderacionesrubrica'] = ponderacionesrubrica = rubrica.rubricatitulacioncabponderacionposgrado_set.filter(status=True).order_by('orden')
                    data['comboponderaciones'] = PonderacionRubricaPosgrado.objects.filter(status=True).exclude(pk__in=ponderacionesrubrica.values_list('ponderacion_id',flat=True))
                    return render(request, "adm_configuracionpropuesta/editrubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'editrubricas':
                try:
                    data['title'] = u'Editar detalle rubrica posgrado'
                    detalle = DetalleRubricaTitulacionPosgrado.objects.get(pk=int(request.GET['id']))
                    form = RubricaPosgradoForm(initial={'tiporubrica': detalle.tiporubrica,
                                                        'rubrica': detalle.rubrica,
                                                        'equivalencia': detalle.equivalencia })
                    data['detalle'] = detalle
                    data['form'] = form
                    return render(request, "adm_configuracionpropuesta/editrubricas.html", data)
                except Exception as ex:
                    pass

            elif action == 'modificartutor':
                try:
                    data['title'] = u'Modificar Tutor de tesis'
                    temamatricula = TemaTitulacionPosgradoMatricula.objects.get(pk=int(request.GET['idtema']))
                    form = ModificacionTutorForm(initial={'tutor': temamatricula.tutor})
                    # form.modificar(temamatricula.tutor)
                    data['temamatricula'] = temamatricula
                    data['idconfiguracion'] = request.GET['idconfiguracion']
                    data['form'] = form
                    return render(request, "adm_configuracionpropuesta/modificartutor.html", data)
                except Exception as ex:
                    pass

            elif action == 'modificartutorgruposol':
                try:
                    data['title'] = u'Modificar Tutor de tesis'
                    temamatricula = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=int(request.GET['idtema']))
                    form = ModificacionTutorForm(initial={'tutor': temamatricula.tutor})
                    # form.modificar(temamatricula.tutor)
                    data['temamatricula'] = temamatricula
                    data['idconfiguracion'] = request.GET['idconfiguracion']
                    data['form'] = form
                    return render(request, "adm_configuracionpropuesta/modificartutorgruposol.html", data)
                except Exception as ex:
                    pass

            elif action == 'modificartutor1':
                try:
                    data['title'] = u'Asignar Tutor de tesis'
                    temamatricula = TemaTitulacionPosgradoMatricula.objects.get(pk=int(request.GET['idtema']))
                    form = ModificacionTutorForm(initial={'tutor': temamatricula.tutor})
                    # form.modificar(temamatricula.tutor)
                    data['temamatricula'] = temamatricula
                    data['idconfiguracion'] = request.GET['idconfiguracion']
                    data['form'] = form
                    return render(request, "adm_configuracionpropuesta/modificartutor1.html", data)
                except Exception as ex:
                    pass

            elif action == 'modificartutorGrupo':
                try:
                    data['title'] = u'Asignar Tutor de tesis en pareja'
                    temamatricula = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=int(request.GET['idtema']))
                    form = ModificacionTutorForm(initial={'tutor': temamatricula.tutor})
                    # form.modificar(temamatricula.tutor)
                    data['temamatricula'] = temamatricula
                    data['idconfiguracion'] = request.GET['idconfiguracion']
                    data['form'] = form
                    return render(request, "adm_configuracionpropuesta/modificartutorgrupo.html", data)
                except Exception as ex:
                    pass

            elif action == 'sublineas':
                try:
                    data['title'] = u'Configuración y presentación propuesta - sublineas '
                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=int(request.GET['id']))
                    form = ConfiguracionTitulacionPosgradoSublineaForm(initial={'periodo': configuracion.periodo,
                                                                                'carrera': configuracion.carrera})
                    form.editar()
                    data['configuracion'] = configuracion
                    data['sublineas'] = PropuestaSubLineaInvestigacion.objects.filter(status=True, propuestasublineainvestigacioncarrera__carrera=configuracion.carrera, activo=True, linea__activo=True)
                    data['form'] = form
                    return render(request, "adm_configuracionpropuesta/sublineas.html", data)
                except Exception as ex:
                    pass

            elif action == 'propuestastemas':
                try:
                    data['title'] = u'Propuestas de titulación'
                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    data['idconfiguracion'] = request.GET['idconfiguracion']
                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=int(request.GET['idconfiguracion']),status = True)

                    periodo = configuracion.periodo
                    carrera = configuracion.carrera
                    if not periodo.visible:
                        return HttpResponseRedirect("/?info=Periodo Inactivo.")
                    search = None
                    alternativa = None
                    mallaid = None
                    nivelmallaid = None
                    ids = None
                    data['alternativa_form'] = MecanismoTitulacionPosgrado.objects.filter(status= True, activo = True)
                    data['convocatorias_similares']=ConfiguracionTitulacionPosgrado.objects.filter(status=True,periodo=periodo,carrera=carrera )
                    temas = configuracion.tematitulacionposgradomatricula_set.filter(status=True,cabeceratitulacionposgrado__isnull=True ).order_by('-id')

                    # temas1 = TemaTitulacionPosgradoMatricula.objects.filter(status=True,matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera).order_by('-id').exclude(convocatoria=configuracion)
                    # temas2 = TemaTitulacionPosgradoMatricula.objects.filter(status=True,convocatoria=configuracion,matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera).order_by('-id')
                    # temas=temas1|temas2
                    if 'id' in request.GET:
                        ids = int(request.GET['id'])
                        temas = temas.filter(id=int(request.GET['id']))
                    if 'alternativa' in request.GET:
                        if  int(request.GET['alternativa']) !=0:
                            alternativa =int(request.GET['alternativa'])
                            temas = temas.filter(mecanismotitulacionposgrado__id=alternativa)
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search:
                            temas = temas.filter(Q(propuestatema__icontains=search) |
                                                 Q(matricula__inscripcion__persona__nombres__icontains=search) |
                                                 Q(matricula__inscripcion__persona__apellido1__icontains=search) |
                                                 Q(matricula__inscripcion__persona__apellido2__icontains=search) |
                                                 Q(matricula__inscripcion__persona__cedula__icontains=search))

                    paging = MiPaginador(temas, 25)
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
                    data['temas'] = page.object_list
                    data['search'] = search if search else ""
                    data['alternativa'] = alternativa if alternativa else ""
                    data['periodo'] = periodo
                    data['configuracion'] = configuracion

                    # paginador en pareja
                    searchPareja = None
                    alternativaPareja = None
                    temapareja = configuracion.tematitulacionposgradomatriculacabecera_set.filter(status=True)
                    if 'idPareja' in request.GET:
                        idsPareja = int(request.GET['idPareja'])
                        temapareja = temapareja.filter(id=int(request.GET['idPareja']))
                    if 'alternativaPareja' in request.GET:
                        if int(request.GET['alternativaPareja']) != 0:
                            alternativaPareja = int(request.GET['alternativaPareja'])
                            temapareja = temapareja.filter(mecanismotitulacionposgrado__id=alternativaPareja)
                    if 'sPareja' in request.GET:
                        searchPareja = request.GET['sPareja']
                        if searchPareja:
                            cabecera =configuracion.tematitulacionposgradomatricula_set.values_list('cabeceratitulacionposgrado').filter(status=True,cabeceratitulacionposgrado__isnull=False, matricula__inscripcion__persona__cedula__icontains = searchPareja).distinct()
                            temapareja = temapareja.filter(Q(propuestatema__icontains=searchPareja)|
                                                           Q(pk__in = cabecera)
                                                           )

                    paging2 = MiPaginador(temapareja, 25)
                    p2 = 1
                    try:
                        paginasesion2 = 1
                        if 'paginador2' in request.session:
                            paginasesion2 = int(request.session['paginador2'])
                        if 'page2' in request.GET:
                            p2 = int(request.GET['page2'])
                        else:
                            p2 = paginasesion2
                        try:
                            page2 = paging2.page(p2)
                        except:
                            p2 = 1
                        page2 = paging2.page(p2)
                    except:
                        page2 = paging2.page(p2)
                    request.session['paginador2'] = p2
                    data['paging2'] = paging2
                    data['rangospaging2'] = paging2.rangos_paginado(p2)
                    data['page2'] = page2
                    data['searchPareja'] = searchPareja if searchPareja else ""
                    data['alternativaPareja'] = alternativaPareja if alternativaPareja else ""
                    data['temaspareja'] = page2.object_list
                    return render(request, "adm_configuracionpropuesta/propuestastemas.html", data)
                except Exception as ex:
                    pass

            elif action == 'revisarensayo':
                try:
                    data['tema'] = tema =TemaTitulacionPosgradoMatricula.objects.get(pk=request.GET['id'])
                    data['propuestas'] =  propuesta = RevisionPropuestaComplexivoPosgrado.objects.filter(tematitulacionposgradomatricula=tema,
                                                                                  status=True).order_by('id')

                    return render(request, "adm_configuracionpropuesta/revisarensayo.html", data)
                except Exception as ex:
                    pass

            elif action == 'revisarensayocomplexivo':
                try:
                    data['tema'] = tema =TemaTitulacionPosgradoMatricula.objects.get(pk=request.GET['id'])
                    data['propuestas'] =  propuesta = RevisionPropuestaComplexivoPosgrado.objects.filter(tematitulacionposgradomatricula=tema,
                                                                                  status=True).order_by('id')

                    return render(request, "adm_configuracionpropuesta/revisarensayocomplexivo.html", data)
                except Exception as ex:
                    pass

            elif action == 'revisarensayopareja':
                try:
                    data['tema'] = tema =TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=request.GET['id'])
                    data['propuestas'] =  propuesta = RevisionPropuestaComplexivoPosgrado.objects.filter(tematitulacionposgradomatriculacabecera=tema,
                                                                                  status=True).order_by('id')

                    return render(request, "adm_configuracionpropuesta/revisarensayopareja.html", data)
                except Exception as ex:
                    pass

            elif action == 'revisarensayocomplexivopareja':
                try:
                    data['tema'] = tema =TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=request.GET['id'])
                    data['propuestas'] =  propuesta = RevisionPropuestaComplexivoPosgrado.objects.filter(tematitulacionposgradomatriculacabecera=tema,
                                                                                  status=True).order_by('id')

                    return render(request, "adm_configuracionpropuesta/revisarensayocomplexivopareja.html", data)
                except Exception as ex:
                    pass


            elif action == 'aprobarensayo':
                try:
                    data['title'] = u"Calificar Ensayo"
                    data['propuesta'] = propuesta = RevisionPropuestaComplexivoPosgrado.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['grupo'] = propuesta.tematitulacionposgradomatricula
                    form = ComplexivoCalificarPropuestaEnsayoForm()
                    data['form'] = form
                    return render(request, 'adm_configuracionpropuesta/aprobarensayo.html', data)
                except Exception as ex:
                    pass

            elif action == 'aprobarensayocomplexivo':
                try:
                    data['title'] = u"Calificar Ensayo"
                    data['propuesta'] = propuesta = RevisionPropuestaComplexivoPosgrado.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['grupo'] = propuesta.tematitulacionposgradomatricula
                    form = ComplexivoCalificarPropuestaEnsayoForm()
                    data['form'] = form
                    return render(request, 'adm_configuracionpropuesta/aprobarensayocomplexivo.html', data)
                except Exception as ex:
                    pass


            elif action == 'aprobarensayopareja':
                try:
                    data['title'] = u"Calificar Ensayo"
                    data['propuesta'] = propuesta = RevisionPropuestaComplexivoPosgrado.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    data['grupo'] = propuesta.tematitulacionposgradomatriculacabecera
                    form = ComplexivoCalificarPropuestaEnsayoForm()
                    data['form'] = form
                    return render(request, 'adm_configuracionpropuesta/aprobarensayopareja.html', data)
                except Exception as ex:
                    pass


            elif action == 'aprobarensayocomplexivopareja':
                try:
                    data['title'] = u"Calificar Ensayo"
                    data['propuesta'] = propuesta = RevisionPropuestaComplexivoPosgrado.objects.get(
                        pk=int(encrypt(request.GET['id'])))
                    data['grupo'] = propuesta.tematitulacionposgradomatriculacabecera
                    form = ComplexivoCalificarPropuestaEnsayoForm()
                    data['form'] = form
                    return render(request, 'adm_configuracionpropuesta/aprobarensayocomplexivopareja.html', data)
                except Exception as ex:
                    pass

            elif action == 'editdocensayo':
                try:
                    data['title'] = u"Editar Calificación Ensayo"
                    data['propuesta'] = propuesta = RevisionPropuestaComplexivoPosgrado.objects.get(pk=int(encrypt(request.GET['id'])))
                    if propuesta.tematitulacionposgradomatricula:
                        data['grupo'] = propuesta.tematitulacionposgradomatricula
                    else:
                        data['grupo'] = propuesta.tematitulacionposgradomatriculacabecera

                    data['form'] = ComplexivoCalificarPropuestaEnsayoForm(initial={'calificacion': propuesta.calificacion,
                                                                             'observaciones': propuesta.observacion,
                                                                             'plagio': propuesta.porcentajeurkund,
                                                                             'aprobar': True if propuesta.estado==2 else False,
                                                                             'rechazar': True if propuesta.estado==3 else False})
                    return render(request, 'adm_configuracionpropuesta/editaprobarensayo.html', data)
                except Exception as ex:
                    pass

            elif action == 'editdocensayocomplexivo':
                try:
                    data['title'] = u"Editar Calificación Ensayo"
                    data['propuesta'] = propuesta = RevisionPropuestaComplexivoPosgrado.objects.get(pk=int(encrypt(request.GET['id'])))
                    if propuesta.tematitulacionposgradomatricula:
                        data['grupo'] = propuesta.tematitulacionposgradomatricula
                    else:
                        data['grupo'] = propuesta.tematitulacionposgradomatriculacabecera

                    data['form'] = ComplexivoCalificarPropuestaEnsayoForm(initial={'calificacion': propuesta.calificacion,
                                                                             'observaciones': propuesta.observacion,
                                                                             'plagio': propuesta.porcentajeurkund,
                                                                             'aprobar': True if propuesta.estado==2 else False,
                                                                             'rechazar': True if propuesta.estado==3 else False})
                    return render(request, 'adm_configuracionpropuesta/editaprobarensayocomplexivo.html', data)
                except Exception as ex:
                    pass

            elif action == 'editdocensayopareja':
                try:
                    data['title'] = u"Editar Calificación Ensayo"
                    data['propuesta'] = propuesta = RevisionPropuestaComplexivoPosgrado.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['grupo'] = propuesta.tematitulacionposgradomatriculacabecera

                    data['form'] = ComplexivoCalificarPropuestaEnsayoForm(initial={'calificacion': propuesta.calificacion,
                                                                             'observaciones': propuesta.observacion,
                                                                             'plagio': propuesta.porcentajeurkund,
                                                                             'aprobar': True if propuesta.estado==2 else False,
                                                                             'rechazar': True if propuesta.estado==3 else False})
                    return render(request, 'adm_configuracionpropuesta/editaprobarensayopareja.html', data)
                except Exception as ex:
                    pass

            elif action == 'editdocensayocomplexivopareja':
                try:
                    data['title'] = u"Editar Calificación Ensayo"
                    data['propuesta'] = propuesta = RevisionPropuestaComplexivoPosgrado.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['grupo'] = propuesta.tematitulacionposgradomatriculacabecera

                    data['form'] = ComplexivoCalificarPropuestaEnsayoForm(initial={'calificacion': propuesta.calificacion,
                                                                             'observaciones': propuesta.observacion,
                                                                             'plagio': propuesta.porcentajeurkund,
                                                                             'aprobar': True if propuesta.estado==2 else False,
                                                                             'rechazar': True if propuesta.estado==3 else False})
                    return render(request, 'adm_configuracionpropuesta/editaprobarensayocomplexivopareja.html', data)
                except Exception as ex:
                    pass

            elif action == 'reporteDocenteConTutorias':
                try:
                    cursor = connections['default'].cursor()
                    sql = """ 
                    SELECT 
                    (per.apellido1||' '||per.apellido2 ||' '||per.nombres ) AS profesor,
                    per.cedula cedula,
                    (
                    -- QUERY PARA OBTENER LA CANTIDAD DE TUTORIAS QUE UN DOCENTE TIENE QUE DAR
                    -- EN DONDE LA ACTA NO ESTE CERRADA - ES DECIR ES DE UN PERIODO ACTIVO
                    SELECT 
                    COUNT(a.id)
                    FROM sga_tematitulacionposgradomatricula a 
                    INNER JOIN sga_configuraciontitulacionposgrado confs ON confs.id  = a.convocatoria_id 
                    WHERE a.tutor_id = tema.tutor_id  AND  a.status = TRUE  AND a.actacerrada = False
                    ) AS CANTIDAD_TUTORIAS 
                    
                    FROM sga_tematitulacionposgradomatricula tema
                    INNER JOIN sga_profesor prof ON prof.id = tema.tutor_id
                    INNER JOIN sga_persona per ON per.id = prof.persona_id
                    INNER JOIN sga_configuraciontitulacionposgrado conf ON conf.id  = tema.convocatoria_id
                    WHERE 
                    tema.status=TRUE AND 
                    tema.tutor_id IS NOT NULL AND 
                    tema.aprobado = TRUE AND 
                    tema.actacerrada = FALSE AND 
                    tema.cabeceratitulacionposgrado_id IS  NULL 
                    GROUP BY  tema.tutor_id,per.apellido1,per.apellido2,per.nombres , per.cedula
                    ORDER BY  per.apellido1, per.apellido2,per.nombres
                    """

                    cursor.execute(sql)
                    results = cursor.fetchall()

                    __author__ = 'Unemi'
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws_cantidad_tutoria = workbook.add_worksheet('resumen')

                    formatoceldagris = workbook.add_format(
                        {'align': 'center', 'border': 1, 'text_wrap': True})
                    formatoceldaleft = workbook.add_format({'text_wrap': True, 'align': 'left'})


                    #hoja 1
                    ws_cantidad_tutoria.set_column(0, 0, 50)
                    ws_cantidad_tutoria.set_column(1, 1, 12)
                    ws_cantidad_tutoria.set_column(1, 1, 12)
                    # Text with formatting.
                    ws_cantidad_tutoria.write('A1', 'DOCENTE')
                    ws_cantidad_tutoria.write('B1', 'CÉDULA')
                    ws_cantidad_tutoria.write('C1', 'CANTIDAD TUTORIAS')
                    row_num = 1
                    for dato in results:
                        docente = dato[0]
                        ced = dato[1]
                        cantidad = dato[2]
                        ws_cantidad_tutoria.write(row_num, 0, docente)
                        ws_cantidad_tutoria.write(row_num, 1, ced)
                        ws_cantidad_tutoria.write(row_num, 2, cantidad)
                        row_num += 1

                    #hoja 2
                    sql2 = """
                        SELECT 
                        conf.id  id_convocatoria,
                        car.nombre maestria,
                        peri.nombre AS cohorte, 
                        (per.apellido1||' '||per.apellido2 ||' '||per.nombres ) AS profesor,
                        per.cedula cedula,
                        (
                        SELECT 
                        COUNT(a.id)
                        FROM sga_tematitulacionposgradomatricula a 
                        INNER JOIN sga_configuraciontitulacionposgrado confs ON confs.id  = a.convocatoria_id
                        INNER JOIN sga_carrera cars ON cars.id = confs.carrera_id
                        INNER JOIN sga_periodo peris ON peris.id = confs.periodo_id
                        WHERE a.tutor_id = tema.tutor_id  AND  a.status = TRUE AND cars.id = car.id AND peris.id = conf.periodo_id AND a.actacerrada = False
                        ) AS CANTIDAD_TUTORIAS 
                        
                        FROM sga_tematitulacionposgradomatricula tema
                        INNER JOIN sga_profesor prof ON prof.id = tema.tutor_id
                        INNER JOIN sga_persona per ON per.id = prof.persona_id
                        INNER JOIN sga_configuraciontitulacionposgrado conf ON conf.id  = tema.convocatoria_id
                        INNER JOIN sga_carrera car ON car.id = conf.carrera_id
                        INNER JOIN sga_periodo peri ON peri.id = conf.periodo_id
                        WHERE 
                        tema.status=TRUE AND 
                        tema.tutor_id IS NOT NULL AND 
                        tema.cabeceratitulacionposgrado_id IS  NULL AND 
                        tema.aprobado = TRUE AND 
                        tema.actacerrada = FALSE 
                        GROUP BY car.id ,per.apellido1,per.apellido2,per.nombres , tema.tutor_id, peri.nombre,conf.periodo_id, per.cedula, conf.id
                        ORDER BY  per.apellido1, per.apellido2,per.nombres, conf.id
                    """
                    cursor.execute(sql2)
                    results2 = cursor.fetchall()
                    ws_tutorias_detalle = workbook.add_worksheet('cant_tutoria_x_maestria')
                    ws_tutorias_detalle.set_column(0, 0, 60)
                    ws_tutorias_detalle.set_column(1, 1, 12)
                    ws_tutorias_detalle.set_column(2, 2, 50)
                    ws_tutorias_detalle.set_column(3, 3, 60)
                    ws_tutorias_detalle.set_column(4, 4, 42)
                    ws_tutorias_detalle.set_column(5, 5, 12)
                    # Text with formatting.
                    ws_tutorias_detalle.write('A1', 'PROFESOR')
                    ws_tutorias_detalle.write('B1', 'CÉDULA')
                    ws_tutorias_detalle.write('C1', 'CANTIDAD DE TUTORIAS ')
                    ws_tutorias_detalle.write('D1', 'MAESTRÍA ')
                    ws_tutorias_detalle.write('E1', 'COHORTE')
                    ws_tutorias_detalle.write('F1', 'N° CONVOCATORIA')
                    row_num = 1
                    for dato in results2:
                        conv = dato[0]
                        maesria = dato[1]
                        cohorte = dato[2]
                        docente = dato[3]
                        cedula = dato[4]
                        cantidad =dato[5]
                        ws_tutorias_detalle.write(row_num, 0, docente)
                        ws_tutorias_detalle.write(row_num, 1, cedula)
                        ws_tutorias_detalle.write(row_num, 2, cantidad)
                        ws_tutorias_detalle.write(row_num, 3, maesria)
                        ws_tutorias_detalle.write(row_num, 4, cohorte)
                        ws_tutorias_detalle.write(row_num, 5, conv)
                        row_num += 1

                    # hoja 3
                    sql3 = """
                    
                    SELECT 
                    configuracion.id  id_convocatoria,
                    carreraa.nombre  maestria,
                    periodo.nombre  cohorte, 
                    mecanismo.nombre mecanismo,
                    tema.propuestatema tema,
                    tema.variabledependiente var_dependiente,
                    tema.variableindependiente var_independiente,
                    tema.moduloreferencia mod_referencia,
                    (persona.apellido1||' '||persona.apellido2 ||' '||persona.nombres )  profesor,
                    persona.cedula,
                    tema.aprobado  aprobado,
                    tema.actacerrada acta_cerrada
                    
                    FROM 
                    sga_tematitulacionposgradomatricula tema 
                    INNER jOIN sga_mecanismotitulacionposgrado mecanismo  ON mecanismo.id = tema.mecanismotitulacionposgrado_id
                    INNER JOIN sga_profesor profesor ON profesor.id = tema.tutor_id
                    INNER JOIN sga_persona persona ON persona.id = profesor.persona_id
                    INNER JOIN sga_configuraciontitulacionposgrado configuracion ON configuracion.id  = tema.convocatoria_id
                    INNER JOIN sga_periodo periodo ON periodo.id = configuracion.periodo_id
                    INNER JOIN sga_carrera carreraa ON carreraa.id = configuracion.carrera_id
                    WHERE 
                    tema.cabeceratitulacionposgrado_id IS NULL AND
                    tema.status = TRUE AND	
                    tema.aprobado = TRUE AND
                    tema.actacerrada = FALSE 
                    ORDER BY	carreraa.id, periodo.id,configuracion.id, mecanismo.id, persona.apellido1, persona.apellido2, persona.nombres
                    """

                    cursor.execute(sql3)
                    results3 = cursor.fetchall()

                    ws_tutorias_x_tema = workbook.add_worksheet('tutores_x_tema')

                    ws_tutorias_x_tema.set_column(0, 0, 50)
                    ws_tutorias_x_tema.set_column(1, 1, 60)
                    ws_tutorias_x_tema.set_column(2, 2, 50)
                    ws_tutorias_x_tema.set_column(3, 3, 50)
                    ws_tutorias_x_tema.set_column(4, 4, 50)
                    ws_tutorias_x_tema.set_column(5, 5, 50)
                    ws_tutorias_x_tema.set_column(6, 6, 50)
                    ws_tutorias_x_tema.set_column(7, 7, 50)
                    ws_tutorias_x_tema.set_column(8, 8, 60)
                    ws_tutorias_x_tema.set_column(9, 9, 13)
                    # Text with formatting.
                    ws_tutorias_x_tema.write('A1', 'ID_CONVOCATORIA')
                    ws_tutorias_x_tema.write('B1', 'MAESTRIA')
                    ws_tutorias_x_tema.write('C1', 'COHORTE')
                    ws_tutorias_x_tema.write('D1', 'MECANISMO ')
                    ws_tutorias_x_tema.write('E1', 'TEMA')
                    ws_tutorias_x_tema.write('F1', 'VAR_DEPENDIENTE')
                    ws_tutorias_x_tema.write('G1', 'VAR_INDEPENDIENTE')
                    ws_tutorias_x_tema.write('H1', 'MOD_REFERENCIA')
                    ws_tutorias_x_tema.write('I1', 'DOCENTE')
                    ws_tutorias_x_tema.write('J1', 'CÉDULA')
                    row_num = 1
                    for dato in results3:
                        conv = dato[0]
                        maestria = dato[1]
                        cohorte = dato[2]
                        mecanismo = dato[3]
                        tema = dato[4]
                        var_dep =dato[5]
                        var_inde =dato[6]
                        mod =dato[7]
                        docente =dato[8]
                        ced =dato[9]
                        ws_tutorias_x_tema.write(row_num, 0, conv)
                        ws_tutorias_x_tema.write(row_num, 1, maestria)
                        ws_tutorias_x_tema.write(row_num, 2, cohorte)
                        ws_tutorias_x_tema.write(row_num, 3, mecanismo)
                        ws_tutorias_x_tema.write(row_num, 4, tema)
                        ws_tutorias_x_tema.write(row_num, 5, var_dep)
                        ws_tutorias_x_tema.write(row_num, 6, var_inde)
                        ws_tutorias_x_tema.write(row_num, 7, mod)
                        ws_tutorias_x_tema.write(row_num, 8, docente)
                        ws_tutorias_x_tema.write(row_num, 9, ced)

                        row_num += 1


                    workbook.close()
                    output.seek(0)

                    filename = 'reporte_tutorias_docentes_posgrado' + random.randint(1, 10000).__str__() + '.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporteDocenteConTutoriasPareja':
                try:
                    cursor = connections['default'].cursor()
                    sql = """
                    SELECT 
                    (persona.apellido1||' '||persona.apellido2 ||' '||persona.nombres) tutor,
                    persona.cedula cedula,
                    (
                    SELECT 
                    COUNT(tema.id) /2 AS Cantidad_tutorias
                    FROM 
                    sga_tematitulacionposgradomatricula tema 
                    WHERE 
                    tema.status=TRUE AND 
                    cabecera.id = tema.cabeceratitulacionposgrado_id AND 
                    tema.actacerrada = FALSE AND 
                    tema.aprobado = TRUE	
                    )
                    FROM 
                    sga_tematitulacionposgradomatriculacabecera cabecera
                    INNER JOIN sga_profesor profesor ON profesor.id = cabecera.tutor_id
                    INNER JOIN sga_persona persona ON persona.id = profesor.persona_id
                    WHERE cabecera.tutor_id IS NOT NULL AND cabecera.status= TRUE
                    """
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    __author__ = 'Unemi'
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws_cantidad_tutoria = workbook.add_worksheet('resumen')
                    formatoceldagris = workbook.add_format(
                        {'align': 'center', 'border': 1, 'text_wrap': True})
                    formatoceldaleft = workbook.add_format({'text_wrap': True, 'align': 'left'})

                    # hoja 1
                    ws_cantidad_tutoria.set_column(0, 0, 50)
                    ws_cantidad_tutoria.set_column(1, 1, 12)
                    ws_cantidad_tutoria.set_column(1, 1, 12)
                    # Text with formatting.
                    ws_cantidad_tutoria.write('A1', 'DOCENTE')
                    ws_cantidad_tutoria.write('B1', 'CÉDULA')
                    ws_cantidad_tutoria.write('C1', 'CANTIDAD TUTORIAS')
                    row_num = 1
                    for dato in results:
                        docente = dato[0]
                        ced = dato[1]
                        cantidad = dato[2]
                        ws_cantidad_tutoria.write(row_num, 0, docente)
                        ws_cantidad_tutoria.write(row_num, 1, ced)
                        ws_cantidad_tutoria.write(row_num, 2, cantidad)
                        row_num += 1
                    # hoja 2
                    sql2 = """
                                                                SELECT 
                                                                car.nombre AS maestria,
                                                                peri.nombre AS cohorte, 
                                                                conf.id AS id_convocatoria,
                                                                (per.apellido1||' '||per.apellido2 ||' '||per.nombres) AS profesor, 
                                                                per.cedula cedula,
                                                                mec.nombre AS alternativa_titulacion,
                                                                tema.cabeceratitulacionposgrado_id,
                                                                tema.propuestatema AS tema,
                                                                (
                                                                SELECT (perso.cedula)
                                                                FROM sga_matricula ma
                                                                INNER JOIN sga_tematitulacionposgradomatricula tem ON ma.id = tem.matricula_id
                                                                INNER JOIN sga_inscripcion inscri ON inscri.id = ma.inscripcion_id
                                                                INNER JOIN sga_persona perso ON perso.id = inscri.persona_id
                                                                WHERE tem.id = tema.id
                                                                ) AS cedula_Estudiante,
                                                                (
                                                                SELECT (perso.apellido1||' '||perso.apellido2 ||' '||perso.nombres)
                                                                FROM sga_matricula ma
                                                                INNER JOIN sga_tematitulacionposgradomatricula tem ON ma.id = tem.matricula_id
                                                                INNER JOIN sga_inscripcion inscri ON inscri.id = ma.inscripcion_id
                                                                INNER JOIN sga_persona perso ON perso.id = inscri.persona_id
                                                                WHERE tem.id = tema.id
                                                                ) AS estudiante,
                                                                (
                                                                SELECT COUNT(gr.id) FROM sga_graduado gr WHERE gr.inscripcion_id = matr.inscripcion_id AND status = True
                                                                ) AS registro_graduado,
                                                                tema.aprobado AS aprobado,
                                                                tema.actacerrada
                                                                FROM sga_tematitulacionposgradomatriculacabecera cab
                                                                INNER JOIN sga_tematitulacionposgradomatricula tema ON tema.cabeceratitulacionposgrado_id = cab.id
                                                                INNER JOIN sga_matricula matr ON matr.id = tema.matricula_id
                                                                INNER JOIN sga_profesor prof ON prof.id = cab.tutor_id
                                                                INNER JOIN sga_persona per ON per.id = prof.persona_id
                                                                INNER JOIN sga_configuraciontitulacionposgrado conf ON conf.id = cab.convocatoria_id
                                                                INNER JOIN sga_periodo peri ON peri.id = conf.periodo_id
                                                                INNER JOIN sga_carrera car ON car.id = conf.carrera_id
                                                                INNER JOIN sga_mecanismotitulacionposgrado mec ON mec.id = cab.mecanismotitulacionposgrado_id
                                                                INNER JOIN sga_propuestasublineainvestigacion sub ON sub.id = cab.sublinea_id
                                                                INNER JOIN sga_propuestalineainvestigacion lin ON lin.id = sub.linea_id
                                                                WHERE tema.actacerrada = FALSE AND
                                                                tema.aprobado = True
                                                                ORDER BY car.nombre, peri.nombre, conf.id, per.apellido1, per.apellido2, per.nombres, lin.nombre, sub.nombre,tema.propuestatema;
                                                                """
                    cursor.execute(sql2)
                    results2 = cursor.fetchall()
                    ws_tema_pareja = workbook.add_worksheet('temas_en_pareja')
                    ws_tema_pareja.set_column(0, 0, 60)
                    ws_tema_pareja.set_column(1, 1, 50)
                    ws_tema_pareja.set_column(2, 2, 15)
                    ws_tema_pareja.set_column(3, 3, 50)
                    ws_tema_pareja.set_column(4, 4, 13)
                    ws_tema_pareja.set_column(5, 5, 45)
                    ws_tema_pareja.set_column(6, 6, 12)
                    ws_tema_pareja.set_column(7, 7, 60)
                    ws_tema_pareja.set_column(8, 8, 12)
                    ws_tema_pareja.set_column(9, 9, 60)
                    # Text with formatting.
                    ws_tema_pareja.write('A1', 'MAESTRÍA')
                    ws_tema_pareja.write('B1', 'COHORTE')
                    ws_tema_pareja.write('C1', 'ID_CONVOCATORIA')
                    ws_tema_pareja.write('D1', 'DOCENTE')
                    ws_tema_pareja.write('E1', 'CÉDULA DOCENTE')
                    ws_tema_pareja.write('F1', 'ALTERNATIVA')
                    ws_tema_pareja.write('G1', 'N° PAREJA')
                    ws_tema_pareja.write('H1', 'TEMA')
                    ws_tema_pareja.write('I1', 'CÉDULA ESTUDIANTE')
                    ws_tema_pareja.write('J1', 'ESTUDIANTE')
                    row_num = 1
                    for dato in results2:
                        maestria = dato[0]
                        cohorte = dato[1]
                        convocatoria = dato[2]
                        docente = dato[3]
                        ced_docente = dato[4]
                        alernativa = dato[5]
                        cabecera = dato[6]
                        tema = dato[7]
                        ced_estudiante = dato[8]
                        estudiante = dato[9]
                        ws_tema_pareja.write(row_num, 0, maestria)
                        ws_tema_pareja.write(row_num, 1, cohorte)
                        ws_tema_pareja.write(row_num, 2, convocatoria)
                        ws_tema_pareja.write(row_num, 3, docente)
                        ws_tema_pareja.write(row_num, 4, ced_docente)
                        ws_tema_pareja.write(row_num, 5, alernativa)
                        ws_tema_pareja.write(row_num, 6, cabecera)
                        ws_tema_pareja.write(row_num, 7, tema)
                        ws_tema_pareja.write(row_num, 8, ced_estudiante)
                        ws_tema_pareja.write(row_num, 9, estudiante)
                        row_num += 1

                    workbook.close()
                    output.seek(0)

                    filename = 'tutorias_docentes_posgrado_pareja' + random.randint(1, 10000).__str__() + '.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'formargrupotitulacionposgradomatricula':
                data['title'] = u'Formulario para conformar grupos de titulación posgrado'

                data['configuracion'] = configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=int(request.GET['id']))
                data['maestrantes'] = TemaTitulacionPosgradoMatriculaHistorial.objects.annotate(dato_id=F("tematitulacionposgradomatricula__id"), dato_propuestatema=F("tematitulacionposgradomatricula__propuestatema"),dato_mecanismo=F("tematitulacionposgradomatricula__mecanismotitulacionposgrado__nombre"),dato_matricula=Concat(F("tematitulacionposgradomatricula__matricula__inscripcion__persona__apellido1"), Value(" "), F("tematitulacionposgradomatricula__matricula__inscripcion__persona__apellido2"), Value(" "), F("tematitulacionposgradomatricula__matricula__inscripcion__persona__nombres"), Value("-"), F("tematitulacionposgradomatricula__matricula__inscripcion__persona__cedula"), Value(" "), F("tematitulacionposgradomatricula__convocatoria__carrera__nombre")))\
                    .values("dato_id", "dato_matricula","dato_propuestatema","dato_mecanismo")\
                    .filter(status=True,estado=2,tematitulacionposgradomatricula__convocatoria=configuracion).exclude(tematitulacionposgradomatricula__cabeceratitulacionposgrado__isnull=False).order_by("dato_mecanismo").distinct()
                return render(request, "adm_configuracionpropuesta/formgrupotitulacionposgradomatricula.html", data)


            elif action == 'configurar_convocatoria_mecanismo':
                try:
                    data['form'] = ConfiguracionConvocatoriaMecanismoForm()
                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(id=int(request.GET['id']))
                    data['configuracionTitulacion'] = configuracion
                    template = get_template("adm_configuracionpropuesta/modal/formconfigurarconvocatoria.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action =='configurar_convocatoria_mecanismo_editar':
                try:
                    filtro =DetalleTitulacionPosgrado.objects.get(pk = int(request.GET['id']))
                    data['form'] = ConfiguracionConvocatoriaMecanismoForm(initial={
                        'mecanismo': filtro.mecanismotitulacionposgrado,
                        'rubrica': filtro.rubricatitulacionposgrado
                    })
                    data['configuracionTitulacion'] = filtro.configuracion
                    data['id'] = filtro.pk
                    template = get_template("adm_configuracionpropuesta/modal/formconfigurarconvocatoria.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addgrupotitulacionpostgrado':
                try:
                    data['title'] = u'Adicionar grupo'
                    form = GrupoTitulacionPostgradoForm()
                    form.fields['tutor'].queryset = Profesor.objects.none()
                    data['id'] = request.GET["id"]
                    eConfiguracionTitulacionPosgrado = ConfiguracionTitulacionPosgrado.objects.get(pk=int(request.GET["id"]))
                    eItinerarioMallaEspecilidad = ItinerarioMallaEspecilidad.objects.filter(status=True, malla__id=eConfiguracionTitulacionPosgrado.carrera.malla().id).order_by('id')
                    if eItinerarioMallaEspecilidad.exists():
                        form.fields['mencion'].queryset = form.fields['mencion'].queryset = eItinerarioMallaEspecilidad
                    else:
                        del form.fields['mencion']

                    data['form'] = form
                    template = get_template("adm_configuracionpropuesta/modal/formGrupotitulacionposgrado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'ver_grupo_posgrado_inscritos':
                try:
                    data['title'] = u'Maestrantes inscritos'
                    search = None
                    search = request.GET.get('s', '')
                    url_vars = ""
                    filtros = Q(status=True)

                    if search:
                        data['search'] = search
                        url_vars += "&s={}".format(search)
                        filtros = filtros & (
                                Q(inscrito__matricula__inscripcion__persona__nombres__icontains=search) |
                                Q(inscrito__matricula__inscripcion__persona__apellido1__icontains=search) |
                                Q(inscrito__matricula__inscripcion__persona__apellido2__icontains=search) |
                                Q(inscrito__matricula__inscripcion__persona__cedula__icontains=search)|
                                Q(inscrito__propuestatema__icontains=search)
                        )

                    data["url_vars"] = url_vars
                    data['grupo'] = grupo = GrupoTitulacionPostgrado.objects.get(pk=int(request.GET['id']))
                    inscritos = DetalleGrupoTitulacionPostgrado.objects.filter(filtros,grupoTitulacionPostgrado = grupo)
                    total=inscritos.count()
                    paging = MiPaginador(inscritos, 20)
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
                    data['inscritos'] = page.object_list
                    data['total'] = total
                    return render(request, "adm_configuracionpropuesta/ver_grupo_posgrado_inscrito.html", data)
                except Exception as ex:
                    pass

            elif action == 'editgrupotitulacionpostgrado':
                try:
                    data['grupo'] = grupo = GrupoTitulacionPostgrado.objects.get(status=True, pk=int(request.GET['id']))
                    data['id'] = grupo.pk
                    data['title'] = u'Editar grupo titulación posgrado'
                    data['tutor'] = grupo.tutor
                    form = GrupoTitulacionPostgradoForm(initial={
                        'fecha': grupo.fecha,
                        'hora': grupo.hora.strftime('%H:%m'),
                        'link_zoom': grupo.link_zoom,
                        'link_grabacion': grupo.link_grabacion,
                        'cupo': grupo.cupo,
                        'tutor': grupo.tutor,
                        'modeloevaluativo': grupo.modeloevaluativo,
                        'paralelo': grupo.paralelo,
                        'mencion': grupo.itinerariomallaespecilidad
                    })

                    if grupo.tutor:
                        form.fields['tutor'].queryset = Profesor.objects.filter(id=grupo.tutor.id)
                    else:
                        form.fields['tutor'].queryset = Profesor.objects.none()
                    eItinerarioMallaEspecilidad = ItinerarioMallaEspecilidad.objects.filter(status=True,malla__id=grupo.configuracion.carrera.malla().id).order_by('id')
                    if eItinerarioMallaEspecilidad.exists():
                        form.fields['mencion'].queryset = form.fields['mencion'].queryset = eItinerarioMallaEspecilidad
                    else:
                        del form.fields['mencion']

                    data['form'] = form
                    template = get_template("adm_configuracionpropuesta/modal/formGrupotitulacionposgrado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'reporte_temas_individuales_pareja_titulacion_posgrado':
                try:
                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=int(request.GET['idconfiguracion']))
                    temas_individual = configuracion.tematitulacionposgradomatricula_set.filter(status=True,matricula__nivel__periodo=configuracion.periodo,matricula__inscripcion__carrera=configuracion.carrera,cabeceratitulacionposgrado__isnull=True).order_by('-id')
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf( 'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    fuentecabecera = easyxf('font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('INDIVIDUAL')
                    ws2 = wb.add_sheet('PAREJA')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[ 'Content-Disposition'] = 'attachment; filename= reporte_temas_individuales_pareja_titulacion_posgrado' + random.randint( 1, 10000).__str__() + '.xls'
                    columns = [
                        (u"MECANISMO DE TITULACIÓN", 16000),
                        (u"MAESTRANTE", 12000),
                        (u"CÉDULA", 6000),
                        (u"CARRERA", 12000),
                        (u"PARALELO", 12000),
                        (u"MENCION", 12000),
                        (u"TEMA", 20000),
                        (u"TEMA CORRECTO TUTOR", 20000),
                        (u"TUTOR", 20000),
                        (u"CANT TUTORIAS", 20000),
                        (u"VARIABLE DEPENDIENTE", 15000),
                        (u"VARIABLE INDEPENDIENTE", 15000),
                        (u"LINEA", 12000),
                        (u"SUBLINEA", 12000),
                        (u"ESTADO", 4500),
                        (u"APROBADO POR DIRECTOR TFM", 4500),
                        (u"DOCUMENTO TRABAJO TITULACIÓN", 4500),
                        (u"PRESIDENTE", 16000),
                        (u"SECRETARIO", 16000),
                        (u"VOCAL", 16000),
                    ]

                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    row_num = 2
                    for tema in temas_individual:
                        aprobadotutor = 'NO APROBADO'
                        if tema.revisiontutoriastematitulacionposgradoprofesor_set.filter(estado=2, status=True):
                            aprobadotutor = 'APROBADO'
                        campo0 = tema.matricula.inscripcion.persona.nombre_completo_inverso()
                        campo1 = tema.matricula.inscripcion.carrera.nombre
                        cedula = tema.matricula.inscripcion.persona.cedula
                        if tema.tutor != None:
                            tutor = tema.tutor.persona.nombre_completo_inverso()
                        else:
                            tutor = "No tiene aún tutor"
                        temacorrejidotutor = ''
                        if tema.tribunaltematitulacionposgradomatricula_set.filter(status=True).exists():
                            tribunal = TribunalTemaTitulacionPosgradoMatricula.objects.get(
                                tematitulacionposgradomatricula=tema)
                            temacorrejidotutor = tribunal.subtema
                        campo2 = tema.propuestatema
                        campo3 = tutor
                        campo4 = tema.variabledependiente
                        campo5 = tema.variableindependiente
                        campo6 = tema.sublinea.linea.nombre if tema.sublinea else ''
                        campo7 = tema.sublinea.nombre if tema.sublinea else ''
                        if tema.tiene_aprobaciones():
                            if tema.estado_aprobacion().estado == 1:
                                estado = 'SOLICITADO'
                            elif tema.estado_aprobacion().estado == 2:
                                estado = 'APROBADO'
                            elif tema.estado_aprobacion().estado == 3:
                                estado = 'RECHAZADO'
                        campo8 = estado
                        campo9 = 'NO'
                        if tema.mecanismotitulacionposgrado.id in [15, 21]:
                            if tema.cargo_documento_ensayo():
                                campo9 = 'SI'
                        else:
                            if tema.revisiontutoriastematitulacionposgradoprofesor_set.filter(status=True).exists():
                                campo9 = 'SI'
                        campo10 = tema.mecanismotitulacionposgrado.__str__()
                        campo11 = 'N/A'
                        campo12 = 'N/A'
                        campo13 = 'N/A'
                        if tema.detalletribunal():
                            campo11 = tema.detalletribunal().first().presidentepropuesta.__str__() if tema.detalletribunal().first().presidentepropuesta else 'N/A'
                            campo12 = tema.detalletribunal().first().secretariopropuesta.__str__() if tema.detalletribunal().first().secretariopropuesta else 'N/A'
                            campo13 = tema.detalletribunal().first().delegadopropuesta.__str__() if tema.detalletribunal().first().delegadopropuesta else 'N/A'

                        cantidad_tutorias = tema.tutoriastematitulacionposgradoprofesor_set.filter(status=True).count()
                        ws.write(row_num, 0, campo10, font_style2)
                        ws.write(row_num, 1, campo0, font_style2)
                        ws.write(row_num, 2, cedula, font_style2)
                        ws.write(row_num, 3, campo1, font_style2)
                        ws.write(row_num, 4, tema.get_paralelo_maestrante().__str__(), font_style2)
                        ws.write(row_num, 5, tema.get_mencion_maestrante().__str__(), font_style2)
                        ws.write(row_num, 6, campo2, font_style2)
                        ws.write(row_num, 7, temacorrejidotutor, font_style2)
                        ws.write(row_num, 8, campo3, font_style2)
                        ws.write(row_num, 9, cantidad_tutorias, font_style2)
                        ws.write(row_num, 10, campo4, font_style2)
                        ws.write(row_num, 11, campo5, font_style2)
                        ws.write(row_num, 12, campo6, font_style2)
                        ws.write(row_num, 13, campo7, font_style2)
                        ws.write(row_num, 14, campo8, font_style2)
                        ws.write(row_num, 15, aprobadotutor, font_style2)
                        ws.write(row_num, 16, campo9, font_style2)
                        ws.write(row_num, 17, campo11, font_style2)
                        ws.write(row_num, 18, campo12, font_style2)
                        ws.write(row_num, 19, campo13, font_style2)

                        row_num += 1

                    # pareja------------------------------+
                    temas_pareja = configuracion.tematitulacionposgradomatricula_set.filter(status=True,matricula__nivel__periodo=configuracion.periodo,matricula__inscripcion__carrera=configuracion.carrera,cabeceratitulacionposgrado__isnull=False).order_by('cabeceratitulacionposgrado')

                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    fuentecabecera = easyxf( 'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    ws2.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    columns = [
                        (u"MECANISMO TITULACIÓN", 12000),
                        (u"CÓDIGO PAREJA", 3000),
                        (u"MAESTRANTE", 12000),
                        (u"CÉDULA", 6000),
                        (u"CARRERA", 12000),
                        (u"PARALELO", 12000),
                        (u"MENCION", 12000),
                        (u"TEMA", 12000),
                        (u"TEMA CORRECTO TUTOR", 12000),
                        (u"TUTOR", 10000),
                        (u"CANT TUTORIA", 10000),
                        (u"VARIABLE DEPENDIENTE", 10000),
                        (u"VARIABLE INDEPENDIENTE", 10000),
                        (u"LINEA", 12000),
                        (u"SUBLINEA", 12000),
                        (u"ESTADO", 4500),
                        (u"APROBADO POR DIRECTOR TFM", 4500),
                        (u"DOCUMENTO TRABAJO TITULACIÓN", 4500),
                        (u"PRESIDENTE", 20000),
                        (u"SECRETARIO", 20000),
                        (u"VOCAL", 20000),
                    ]

                    row_num = 1
                    for col_num in range(len(columns)):
                        ws2.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws2.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    row_num = 2
                    for tema in temas_pareja:
                        aprobadotutor = 'NO APROBADO'
                        if tema.cabeceratitulacionposgrado:
                            if tema.cabeceratitulacionposgrado.revisiontutoriastematitulacionposgradoprofesor_set.filter(estado=2, status=True):
                                aprobadotutor = 'APROBADO'
                        campo0 = tema.matricula.inscripcion.persona.nombre_completo_inverso()
                        cedula = tema.matricula.inscripcion.persona.cedula
                        campo1 = tema.matricula.inscripcion.carrera.nombre
                        if tema.cabeceratitulacionposgrado.tutor != None:
                            tutor = tema.cabeceratitulacionposgrado.tutor.persona.nombre_completo_inverso()
                        else:
                            tutor = "No tiene aún tutor"
                        temacorrejidotutor = ''
                        if tema.tribunaltematitulacionposgradomatricula_set.filter(status=True).exists():
                            tribunal = TribunalTemaTitulacionPosgradoMatricula.objects.get(tematitulacionposgradomatricula=tema)
                            temacorrejidotutor = tribunal.subtema
                        campo2 = tema.propuestatema
                        campo3 = tutor
                        campo4 = tema.variabledependiente
                        campo5 = tema.variableindependiente
                        campo6 = tema.sublinea.linea.nombre if tema.sublinea else ''
                        campo7 = tema.sublinea.nombre if tema.sublinea else ''
                        if tema.tiene_aprobaciones():
                            if tema.estado_aprobacion().estado == 1:
                                estado = 'SOLICITADO'
                            elif tema.estado_aprobacion().estado == 2:
                                estado = 'APROBADO'
                            elif tema.estado_aprobacion().estado == 3:
                                estado = 'RECHAZADO'
                        campo8 = estado
                        campo9 = 'NO'
                        if tema.mecanismotitulacionposgrado.id in [15, 21]:
                            if tema.cabeceratitulacionposgrado.cargo_documento_ensayo():
                                campo9 = 'SI'
                        else:
                            if tema.revisiontutoriastematitulacionposgradoprofesor_set.filter(status=True).exists():
                                campo9 = 'SI'

                        campo10 = tema.cabeceratitulacionposgrado.id
                        campo11 = tema.mecanismotitulacionposgrado.__str__()
                        campo12 = 'N/A'
                        campo13 = 'N/A'
                        campo14 = 'N/A'
                        if tema.detalletribunal():
                            campo12 = tema.detalletribunal().first().presidentepropuesta.__str__() if tema.detalletribunal().first().presidentepropuesta else 'N/A'
                            campo13 = tema.detalletribunal().first().secretariopropuesta.__str__() if tema.detalletribunal().first().secretariopropuesta else 'N/A'
                            campo14 = tema.detalletribunal().first().delegadopropuesta.__str__() if tema.detalletribunal().first().delegadopropuesta else 'N/A'

                        cantidad_tutorias = tema.tutoriastematitulacionposgradoprofesor_set.filter(status=True).count()
                        ws2.write(row_num, 0, campo11, font_style2)
                        ws2.write(row_num, 1, campo10, font_style2)
                        ws2.write(row_num, 2, campo0, font_style2)
                        ws2.write(row_num, 3, cedula, font_style2)
                        ws2.write(row_num, 4, campo1, font_style2)
                        ws2.write(row_num, 5, tema.get_paralelo_maestrante().__str__(), font_style2)
                        ws2.write(row_num, 6, tema.get_mencion_maestrante().__str__(), font_style2)
                        ws2.write(row_num, 7, campo2, font_style2)
                        ws2.write(row_num, 8, temacorrejidotutor, font_style2)
                        ws2.write(row_num, 9, campo3, font_style2)
                        ws2.write(row_num, 10, cantidad_tutorias, font_style2)
                        ws2.write(row_num, 11, campo4, font_style2)
                        ws2.write(row_num, 12, campo5, font_style2)
                        ws2.write(row_num, 13, campo6, font_style2)
                        ws2.write(row_num, 14, campo7, font_style2)
                        ws2.write(row_num, 15, campo8, font_style2)
                        ws2.write(row_num, 16, aprobadotutor, font_style2)
                        ws2.write(row_num, 17, campo9, font_style2)
                        ws2.write(row_num, 18, campo12, font_style2)
                        ws2.write(row_num, 19, campo13, font_style2)
                        ws2.write(row_num, 20, campo14, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporte_tutoria_individuales_pareja_titulacion_posgrado':
                try:
                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=int(request.GET['idconfiguracion']))
                    temas_individual = configuracion.tematitulacionposgradomatricula_set.filter(status=True,matricula__nivel__periodo=configuracion.periodo,matricula__inscripcion__carrera=configuracion.carrera,cabeceratitulacionposgrado__isnull=True).exclude(mecanismotitulacionposgrado_id__in = [21,15]).order_by('-id')
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf( 'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    fuentecabecera = easyxf('font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('INDIVIDUAL')
                    ws2 = wb.add_sheet('PAREJA')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[ 'Content-Disposition'] = 'attachment; filename=reporte_tutoria_individuales_pareja_titulacion_posgrado' + random.randint( 1, 10000).__str__() + '.xls'
                    columns = [
                        (u"MECANISMO DE TITULACIÓN", 16000),
                        (u"MAESTRANTE", 12000),
                        (u"CÉDULA", 6000),
                        (u"CARRERA", 12000),
                        (u"PARALELO", 12000),
                        (u"MENCIÓN", 12000),
                        (u"TEMA CORRECTO TUTOR", 20000),
                        (u"TUTOR", 20000),
                        (u"CANT TUTORIAS", 20000),
                        (u"ESTADO", 4500),
                        (u"APROBADO POR DIRECTOR TFM", 4500),
                        (u"PRESIDENTE", 16000),
                        (u"SECRETARIO", 16000),
                        (u"VOCAL", 16000),
                    ]

                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    row_num = 2
                    for tema in temas_individual:
                        aprobadotutor = 'EN PROCESO DE TUTORIAS'
                        ACEPTADO = 2
                        PENDIENTE = 1
                        RECHAZADO= 3
                        POR_REVISIÓN_DE_PLAGIO = 4
                        if tema.revisiontutoriastematitulacionposgradoprofesor_set.filter(estado=ACEPTADO, status=True):
                            aprobadotutor = 'ACEPTADO'

                        maestrante = tema.matricula.inscripcion.persona.nombre_completo_inverso()
                        carrera = tema.matricula.inscripcion.carrera.nombre
                        cedula = tema.matricula.inscripcion.persona.cedula
                        if tema.tutor != None:
                            tutor = tema.tutor.persona.nombre_completo_inverso()
                        else:
                            tutor = "No tiene aún tutor"
                        temacorrejidotutor = '-'
                        if tema.tribunaltematitulacionposgradomatricula_set.filter(status=True).exists():
                            tribunal = TribunalTemaTitulacionPosgradoMatricula.objects.get( tematitulacionposgradomatricula=tema)
                            temacorrejidotutor = tribunal.subtema if tribunal.subtema else  'el tutor no ha definido tema correcto'

                        mecanismo = tema.mecanismotitulacionposgrado.__str__()
                        presidentepropuesta = 'N/A'
                        secretariopropuesta = 'N/A'
                        delegadopropuesta = 'N/A'
                        if tema.detalletribunal():
                            presidentepropuesta = tema.detalletribunal().first().presidentepropuesta.__str__() if tema.detalletribunal().first().presidentepropuesta else 'N/A'
                            secretariopropuesta = tema.detalletribunal().first().secretariopropuesta.__str__() if tema.detalletribunal().first().secretariopropuesta else 'N/A'
                            delegadopropuesta = tema.detalletribunal().first().delegadopropuesta.__str__() if tema.detalletribunal().first().delegadopropuesta else 'N/A'

                        cantidad_tutorias = tema.tutoriastematitulacionposgradoprofesor_set.filter(status=True).count()

                        estado = ''
                        if tema.tiene_aprobaciones():
                            if tema.estado_aprobacion().estado == 1:
                                estado = 'SOLICITADO'
                            elif tema.estado_aprobacion().estado == 2:
                                estado = 'APROBADO'
                            elif tema.estado_aprobacion().estado == 3:
                                estado = 'RECHAZADO'

                        ws.write(row_num, 0, mecanismo, font_style2)
                        ws.write(row_num, 1, maestrante, font_style2)
                        ws.write(row_num, 2, cedula, font_style2)
                        ws.write(row_num, 3, carrera, font_style2)
                        ws.write(row_num, 4, tema.get_paralelo_maestrante().__str__(), font_style2)
                        ws.write(row_num, 5, tema.get_mencion_maestrante().__str__(), font_style2)
                        ws.write(row_num, 6, temacorrejidotutor, font_style2)
                        ws.write(row_num, 7, tutor, font_style2)
                        ws.write(row_num, 8, cantidad_tutorias, font_style2)
                        ws.write(row_num, 9, estado, font_style2)
                        ws.write(row_num, 10, aprobadotutor, font_style2)
                        ws.write(row_num, 11, presidentepropuesta, font_style2)
                        ws.write(row_num, 12, secretariopropuesta, font_style2)
                        ws.write(row_num, 13, delegadopropuesta, font_style2)

                        row_num += 1

                    # pareja------------------------------+
                    temas_pareja = configuracion.tematitulacionposgradomatricula_set.filter(status=True,matricula__nivel__periodo=configuracion.periodo,matricula__inscripcion__carrera=configuracion.carrera,cabeceratitulacionposgrado__isnull=False).exclude( mecanismotitulacionposgrado_id__in=[21, 15]).order_by('-cabeceratitulacionposgrado')
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    fuentecabecera = easyxf( 'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    ws2.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)

                    columns = [
                        (u"MECANISMO DE TITULACIÓN", 16000),
                        (u"CÓDIGO PAREJA", 16000),
                        (u"MAESTRANTE", 12000),
                        (u"CÉDULA", 6000),
                        (u"CARRERA", 12000),
                        (u"PARALELO", 12000),
                        (u"MENCIÓN", 12000),
                        (u"TEMA CORRECTO TUTOR", 20000),
                        (u"TUTOR", 20000),
                        (u"CANT TUTORIAS", 20000),
                        (u"ESTADO", 4500),
                        (u"APROBADO POR DIRECTOR TFM", 4500),
                        (u"PRESIDENTE", 16000),
                        (u"SECRETARIO", 16000),
                        (u"VOCAL", 16000),
                    ]

                    row_num = 1
                    for col_num in range(len(columns)):
                        ws2.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws2.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    row_num = 2
                    for tema in temas_pareja:
                        aprobadotutor = 'EN PROCESO DE TUTORIAS'
                        ACEPTADO = 2
                        PENDIENTE = 1
                        RECHAZADO = 3
                        POR_REVISIÓN_DE_PLAGIO = 4
                        if tema.cabeceratitulacionposgrado.revisiontutoriastematitulacionposgradoprofesor_set.filter(estado=ACEPTADO, status=True):
                            aprobadotutor = 'ACEPTADO'

                        maestrante = tema.matricula.inscripcion.persona.nombre_completo_inverso()
                        carrera = tema.matricula.inscripcion.carrera.nombre
                        cedula = tema.matricula.inscripcion.persona.cedula
                        if tema.cabeceratitulacionposgrado.tutor != None:
                            tutor = tema.cabeceratitulacionposgrado.tutor.persona.nombre_completo_inverso()
                        else:
                            tutor = "No tiene aún tutor"
                        temacorrejidotutor = '-'
                        if tema.cabeceratitulacionposgrado.tribunaltematitulacionposgradomatricula_set.filter(status=True).exists():
                            tribunal = TribunalTemaTitulacionPosgradoMatricula.objects.get(tematitulacionposgradomatriculacabecera=tema.cabeceratitulacionposgrado)
                            temacorrejidotutor = tribunal.subtema if tribunal.subtema else 'el tutor no ha definido tema correcto'

                        mecanismo = tema.mecanismotitulacionposgrado.__str__()
                        cod_pareja = tema.cabeceratitulacionposgrado_id
                        presidentepropuesta = 'N/A'
                        secretariopropuesta = 'N/A'
                        delegadopropuesta = 'N/A'
                        if tema.cabeceratitulacionposgrado.detalletribunal():
                            presidentepropuesta = tema.cabeceratitulacionposgrado.detalletribunal().first().presidentepropuesta.__str__() if tema.cabeceratitulacionposgrado.detalletribunal().first().presidentepropuesta else 'N/A'
                            secretariopropuesta = tema.cabeceratitulacionposgrado.detalletribunal().first().secretariopropuesta.__str__() if tema.cabeceratitulacionposgrado.detalletribunal().first().secretariopropuesta else 'N/A'
                            delegadopropuesta = tema.cabeceratitulacionposgrado.detalletribunal().first().delegadopropuesta.__str__() if tema.cabeceratitulacionposgrado.detalletribunal().first().delegadopropuesta else 'N/A'

                        estado = ''
                        if tema.tiene_aprobaciones():
                            if tema.estado_aprobacion().estado == 1:
                                estado = 'SOLICITADO'
                            elif tema.estado_aprobacion().estado == 2:
                                estado = 'APROBADO'
                            elif tema.estado_aprobacion().estado == 3:
                                estado = 'RECHAZADO'

                        cantidad_tutorias = tema.cabeceratitulacionposgrado.tutoriastematitulacionposgradoprofesor_set.filter(status=True).count()
                        ws2.write(row_num, 0, mecanismo, font_style2)
                        ws2.write(row_num, 1, cod_pareja, font_style2)
                        ws2.write(row_num, 2, maestrante, font_style2)
                        ws2.write(row_num, 3, cedula, font_style2)
                        ws2.write(row_num, 4, carrera, font_style2)
                        ws2.write(row_num, 5, tema.get_paralelo_maestrante().__str__(), font_style2)
                        ws2.write(row_num, 6, tema.get_mencion_maestrante().__str__(), font_style2)
                        ws2.write(row_num, 7, temacorrejidotutor, font_style2)
                        ws2.write(row_num, 8, tutor, font_style2)
                        ws2.write(row_num, 9, cantidad_tutorias, font_style2)
                        ws2.write(row_num, 10, estado, font_style2)
                        ws2.write(row_num, 11, aprobadotutor, font_style2)
                        ws2.write(row_num, 12, presidentepropuesta, font_style2)
                        ws2.write(row_num, 13, secretariopropuesta, font_style2)
                        ws2.write(row_num, 14, delegadopropuesta, font_style2)

                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'detalledatoimp':
                try:
                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=int(request.GET['idconfiguracion']))
                    temas = configuracion.tematitulacionposgradomatricula_set.filter(status=True,matricula__nivel__periodo=configuracion.periodo, matricula__inscripcion__carrera=configuracion.carrera, cabeceratitulacionposgrado__isnull = True ).order_by('-id')
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Listado')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Lista de propuestas a temas de titulacion ' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"MECANISMO DE TITULACIÓN", 16000),
                        (u"MAESTRANTE", 12000),
                        (u"CÉDULA", 6000),
                        (u"CARRERA", 12000),
                        (u"PARALELO", 12000),
                        (u"MENCION", 12000),
                        (u"TEMA", 20000),
                        (u"TEMA CORRECTO TUTOR", 20000),
                        (u"TUTOR", 20000),
                        (u"CANT TUTORIAS", 20000),
                        (u"VARIABLE DEPENDIENTE", 15000),
                        (u"VARIABLE INDEPENDIENTE", 15000),
                        (u"LINEA", 12000),
                        (u"SUBLINEA", 12000),
                        (u"ESTADO", 4500),
                        (u"APROBADO POR DIRECTOR TFM", 4500),
                        (u"DOCUMENTO TRABAJO TITULACIÓN", 4500),
                        (u"PRESIDENTE", 16000),
                        (u"SECRETARIO", 16000),
                        (u"VOCAL", 16000),
                    ]

                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    row_num = 2
                    for tema in temas:
                        aprobadotutor = 'NO APROBADO'
                        if  tema.revisiontutoriastematitulacionposgradoprofesor_set.filter(estado=2, status=True):
                            aprobadotutor = 'APROBADO'
                        campo0 = tema.matricula.inscripcion.persona.nombre_completo_inverso()
                        campo1 = tema.matricula.inscripcion.carrera.nombre
                        cedula = tema.matricula.inscripcion.persona.cedula
                        if tema.tutor != None:
                            tutor = tema.tutor.persona.nombre_completo_inverso()
                        else:
                            tutor = "No tiene aún tutor"
                        temacorrejidotutor = ''
                        if tema.tribunaltematitulacionposgradomatricula_set.filter(status=True).exists():
                            tribunal = TribunalTemaTitulacionPosgradoMatricula.objects.get(tematitulacionposgradomatricula=tema)
                            temacorrejidotutor = tribunal.subtema
                        campo2 = tema.propuestatema
                        campo3 = tutor
                        campo4 = tema.variabledependiente
                        campo5 = tema.variableindependiente
                        campo6 = tema.sublinea.linea.nombre if  tema.sublinea else ''
                        campo7 = tema.sublinea.nombre  if tema.sublinea else ''
                        if tema.tiene_aprobaciones():
                            if tema.estado_aprobacion().estado == 1:
                                estado = 'SOLICITADO'
                            elif tema.estado_aprobacion().estado == 2:
                                estado = 'APROBADO'
                            elif tema.estado_aprobacion().estado == 3:
                                estado = 'RECHAZADO'
                        campo8 = estado
                        campo9 = 'NO'
                        if tema.mecanismotitulacionposgrado.id in [15,21]:
                            if tema.cargo_documento_ensayo():
                                campo9 = 'SI'
                        else:
                            if tema.revisiontutoriastematitulacionposgradoprofesor_set.filter(status=True).exists():
                                campo9 = 'SI'
                        campo10 = tema.mecanismotitulacionposgrado.__str__()
                        campo11 = 'N/A'
                        campo12 = 'N/A'
                        campo13 = 'N/A'
                        if  tema.detalletribunal():
                            campo11 = tema.detalletribunal().first().presidentepropuesta.__str__() if tema.detalletribunal().first().presidentepropuesta else 'N/A'
                            campo12 =  tema.detalletribunal().first().secretariopropuesta.__str__() if tema.detalletribunal().first().secretariopropuesta else 'N/A'
                            campo13 =  tema.detalletribunal().first().delegadopropuesta.__str__() if tema.detalletribunal().first().delegadopropuesta else 'N/A'

                        cantidad_tutorias = tema.tutoriastematitulacionposgradoprofesor_set.filter(status=True).count()
                        ws.write(row_num, 0, campo10, font_style2)
                        ws.write(row_num, 1, campo0, font_style2)
                        ws.write(row_num, 2, cedula, font_style2)
                        ws.write(row_num, 3, campo1, font_style2)
                        ws.write(row_num, 4, tema.get_paralelo_maestrante().__str__(), font_style2)
                        ws.write(row_num, 5, tema.get_mencion_maestrante().__str__(), font_style2)
                        ws.write(row_num, 6, campo2, font_style2)
                        ws.write(row_num, 7, temacorrejidotutor, font_style2)
                        ws.write(row_num, 8, campo3, font_style2)
                        ws.write(row_num, 9, cantidad_tutorias, font_style2)
                        ws.write(row_num, 10, campo4, font_style2)
                        ws.write(row_num, 11, campo5, font_style2)
                        ws.write(row_num, 12, campo6, font_style2)
                        ws.write(row_num, 13, campo7, font_style2)
                        ws.write(row_num, 14, campo8, font_style2)
                        ws.write(row_num, 15, aprobadotutor, font_style2)
                        ws.write(row_num, 16, campo9, font_style2)
                        ws.write(row_num, 17, campo11, font_style2)
                        ws.write(row_num, 18, campo12, font_style2)
                        ws.write(row_num, 19, campo13, font_style2)

                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'reportes_inscritos':
                try:
                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=int(request.GET['idconfiguracion']))
                    temas = configuracion.tematitulacionposgradomatricula_set.filter(status=True,matricula__nivel__periodo=configuracion.periodo, matricula__inscripcion__carrera=configuracion.carrera ).order_by('-id')
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Listado')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Lista de propuestas a temas de titulacion ' + random.randint(1,
                                                                                                                                         10000).__str__() + '.xls'
                    columns = [
                        (u"N°", 3000),
                        (u"MAESTRANTE", 12000),
                        (u"CÉDULA", 6000),
                        (u"CARRERA", 22000),
                        (u"MENCION", 12000),
                        (u"PARALELO", 12000),
                        (u"TEMA", 22000),
                        (u"TEMA CORRECTO TUTOR", 22000),
                        (u"TUTOR", 12000),
                        (u"VARIABLE DEPENDIENTE", 10000),
                        (u"VARIABLE INDEPENDIENTE", 10000),
                        (u"LINEA", 12000),
                        (u"SUBLINEA", 12000),
                        (u"ESTADO", 4500),
                        (u"APROBADO POR DIRECTOR TFM", 12000),
                        (u"DOCUMENTO TRABAJO TITULACIÓN", 12000),
                        (u"MECANISMO DE TITULACIÓN", 12000),
                    ]

                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    row_num = 2
                    contador = 1
                    for tema in temas:
                        aprobadotutor = 'NO APROBADO'
                        if  tema.revisiontutoriastematitulacionposgradoprofesor_set.filter(estado=2, status=True):
                            aprobadotutor = 'APROBADO'
                        campo0 = tema.matricula.inscripcion.persona.nombre_completo_inverso()
                        campo1 = tema.matricula.inscripcion.carrera.nombre
                        if tema.matricula.inscripcion.malla_inscripcion().malla.tiene_itinerario_malla_especialidad():

                            mencion = nombre_mencion(tema)
                        else:
                            mencion = tema.matricula.inscripcion.carrera.mencion

                        paralelo = paralelo_matricula(tema.matricula)

                        cedula = tema.matricula.inscripcion.persona.cedula
                        if tema.tutor != None:
                            tutor = tema.tutor.persona.nombre_completo_inverso()
                        else:
                            tutor = "No tiene aún tutor"
                        temacorrejidotutor = ''
                        if tema.tribunaltematitulacionposgradomatricula_set.filter(status=True).exists():
                            tribunal = TribunalTemaTitulacionPosgradoMatricula.objects.get(tematitulacionposgradomatricula=tema)
                            temacorrejidotutor = tribunal.subtema
                        campo2 = tema.propuestatema
                        campo3 = tutor
                        campo4 = tema.variabledependiente
                        campo5 = tema.variableindependiente
                        campo6 = tema.sublinea.linea.nombre if  tema.sublinea else ''
                        campo7 = tema.sublinea.nombre  if tema.sublinea else ''
                        if tema.tiene_aprobaciones():
                            if tema.estado_aprobacion().estado == 1:
                                estado = 'SOLICITADO'
                            elif tema.estado_aprobacion().estado == 2:
                                estado = 'APROBADO'
                            elif tema.estado_aprobacion().estado == 3:
                                estado = 'RECHAZADO'
                        campo8 = estado
                        campo9 = 'NO'
                        if tema.mecanismotitulacionposgrado.id in [15,21]:
                            if tema.cargo_documento_ensayo():
                                campo9 = 'SI'
                        else:
                            if tema.revisiontutoriastematitulacionposgradoprofesor_set.filter(status=True).exists():
                                campo9 = 'SI'
                        campo10 = tema.mecanismotitulacionposgrado.__str__()
                        ws.write(row_num, 0, contador, font_style2)
                        ws.write(row_num, 1, campo0, font_style2)
                        ws.write(row_num, 2, cedula, font_style2)
                        ws.write(row_num, 3, campo1, font_style2)
                        ws.write(row_num, 4, mencion, font_style2)
                        ws.write(row_num, 5, paralelo, font_style2)
                        ws.write(row_num, 6, campo2, font_style2)
                        ws.write(row_num, 7, temacorrejidotutor, font_style2)
                        ws.write(row_num, 8, campo3, font_style2)
                        ws.write(row_num, 9, campo4, font_style2)
                        ws.write(row_num, 10, campo5, font_style2)
                        ws.write(row_num, 11, campo6, font_style2)
                        ws.write(row_num, 12, campo7, font_style2)
                        ws.write(row_num, 13, campo8, font_style2)
                        ws.write(row_num, 14, aprobadotutor, font_style2)
                        ws.write(row_num, 15, campo9, font_style2)
                        ws.write(row_num, 16, campo10, font_style2)
                        row_num += 1
                        contador += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'detalledatoimpPareja':
                try:
                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=int(request.GET['idconfiguracion']))
                    temas = configuracion.tematitulacionposgradomatricula_set.filter(status=True,
                                                                                     matricula__nivel__periodo=configuracion.periodo,
                                                                                     matricula__inscripcion__carrera=configuracion.carrera,
                                                                                     cabeceratitulacionposgrado__isnull=False).order_by('cabeceratitulacionposgrado')
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Listado')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Lista de propuestas a temas de titulacion ' + random.randint(
                        1,
                        10000).__str__() + '.xls'
                    columns = [
                        (u"MECANISMO TITULACIÓN", 12000),
                        (u"CÓDIGO PAREJA", 3000),
                        (u"MAESTRANTE", 12000),
                        (u"CÉDULA", 6000),
                        (u"CARRERA", 12000),
                        (u"PARALELO", 12000),
                        (u"MENCION", 12000),
                        (u"TEMA", 12000),
                        (u"TEMA CORRECTO TUTOR", 12000),
                        (u"TUTOR", 10000),
                        (u"CANT TUTORIA", 10000),
                        (u"VARIABLE DEPENDIENTE", 10000),
                        (u"VARIABLE INDEPENDIENTE", 10000),
                        (u"LINEA", 12000),
                        (u"SUBLINEA", 12000),
                        (u"ESTADO", 4500),
                        (u"APROBADO POR DIRECTOR TFM", 4500),
                        (u"DOCUMENTO TRABAJO TITULACIÓN", 4500),
                        (u"PRESIDENTE", 20000),
                        (u"SECRETARIO", 20000),
                        (u"VOCAL", 20000),
                    ]

                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    row_num = 2
                    for tema in temas:
                        aprobadotutor = 'NO APROBADO'
                        if tema.cabeceratitulacionposgrado:
                            if tema.cabeceratitulacionposgrado.revisiontutoriastematitulacionposgradoprofesor_set.filter(estado=2, status=True):
                                aprobadotutor = 'APROBADO'
                        campo0 = tema.matricula.inscripcion.persona.nombre_completo_inverso()
                        cedula = tema.matricula.inscripcion.persona.cedula
                        campo1 = tema.matricula.inscripcion.carrera.nombre
                        if tema.cabeceratitulacionposgrado.tutor != None:
                            tutor = tema.cabeceratitulacionposgrado.tutor.persona.nombre_completo_inverso()
                        else:
                            tutor = "No tiene aún tutor"
                        temacorrejidotutor = ''
                        if tema.tribunaltematitulacionposgradomatricula_set.filter(status=True).exists():
                            tribunal = TribunalTemaTitulacionPosgradoMatricula.objects.get(
                                tematitulacionposgradomatricula=tema)
                            temacorrejidotutor = tribunal.subtema
                        campo2 = tema.propuestatema
                        campo3 = tutor
                        campo4 = tema.variabledependiente
                        campo5 = tema.variableindependiente
                        campo6 = tema.sublinea.linea.nombre if  tema.sublinea else ''
                        campo7 = tema.sublinea.nombre if  tema.sublinea else ''
                        if tema.tiene_aprobaciones():
                            if tema.estado_aprobacion().estado == 1:
                                estado = 'SOLICITADO'
                            elif tema.estado_aprobacion().estado == 2:
                                estado = 'APROBADO'
                            elif tema.estado_aprobacion().estado == 3:
                                estado = 'RECHAZADO'
                        campo8 = estado
                        campo9 = 'NO'
                        if tema.mecanismotitulacionposgrado.id in [15,21]:
                            if tema.cabeceratitulacionposgrado.cargo_documento_ensayo():
                                campo9 = 'SI'
                        else:
                            if tema.revisiontutoriastematitulacionposgradoprofesor_set.filter(status=True).exists():
                                campo9 = 'SI'

                        campo10 = tema.cabeceratitulacionposgrado.id
                        campo11 = tema.mecanismotitulacionposgrado.__str__()
                        campo12 = 'N/A'
                        campo13 = 'N/A'
                        campo14 = 'N/A'
                        if  tema.detalletribunal():
                            campo12 = tema.detalletribunal().first().presidentepropuesta.__str__() if tema.detalletribunal().first().presidentepropuesta else 'N/A'
                            campo13 =  tema.detalletribunal().first().secretariopropuesta.__str__() if tema.detalletribunal().first().secretariopropuesta else 'N/A'
                            campo14 =  tema.detalletribunal().first().delegadopropuesta.__str__() if tema.detalletribunal().first().delegadopropuesta else 'N/A'

                        cantidad_tutorias = tema.tutoriastematitulacionposgradoprofesor_set.filter(status=True).count()
                        ws.write(row_num, 0, campo11, font_style2)
                        ws.write(row_num, 1, campo10, font_style2)
                        ws.write(row_num, 2, campo0, font_style2)
                        ws.write(row_num, 3, cedula, font_style2)
                        ws.write(row_num, 4, campo1, font_style2)
                        ws.write(row_num, 5, tema.get_paralelo_maestrante().__str__(), font_style2)
                        ws.write(row_num, 6, tema.get_mencion_maestrante().__str__(), font_style2)
                        ws.write(row_num, 7, campo2, font_style2)
                        ws.write(row_num, 8, temacorrejidotutor, font_style2)
                        ws.write(row_num, 9, campo3, font_style2)
                        ws.write(row_num, 10, cantidad_tutorias, font_style2)
                        ws.write(row_num, 11, campo4, font_style2)
                        ws.write(row_num, 12, campo5, font_style2)
                        ws.write(row_num, 13, campo6, font_style2)
                        ws.write(row_num, 14, campo7, font_style2)
                        ws.write(row_num, 15, campo8, font_style2)
                        ws.write(row_num, 16, aprobadotutor, font_style2)
                        ws.write(row_num, 17, campo9, font_style2)
                        ws.write(row_num, 18, campo12, font_style2)
                        ws.write(row_num, 19, campo13, font_style2)
                        ws.write(row_num, 20, campo14, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporte_temas_complexivo_individuales':
                try:
                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=int(request.GET['idconfiguracion']))
                    temas = configuracion.tematitulacionposgradomatricula_set.filter(status=True,matricula__nivel__periodo=configuracion.periodo, matricula__inscripcion__carrera=configuracion.carrera, cabeceratitulacionposgrado__isnull = True ,mecanismotitulacionposgrado__id__in=[15,21]).order_by('-id')
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Listado')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Lista de propuestas a temas de titulacion ' + random.randint(1,
                                                                                                                                         10000).__str__() + '.xls'
                    columns = [
                        (u"MAESTRANTE", 12000),
                        (u"CÉDULA", 12000),
                        (u"CARRERA", 12000),
                        (u"TEMA", 12000),
                        (u"LINEA", 12000),
                        (u"SUBLINEA", 12000),
                        (u"ESTADO", 4500),
                        (u"DOCUMENTO TRABAJO TITULACIÓN", 4500),
                        (u"MECANISMO DE TITULACIÓN", 4500),
                        (u"ESTADO DEL ENSAYO", 4500),
                    ]

                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    row_num = 2
                    for tema in temas:
                        if tema.tiene_aprobaciones():
                            if tema.estado_aprobacion().estado == 2:
                                campo0 = tema.matricula.inscripcion.persona.nombre_completo_inverso()
                                cedula = tema.matricula.inscripcion.persona.cedula
                                campo1 = tema.matricula.inscripcion.carrera.nombre
                                campo2 = tema.propuestatema
                                campo6 = tema.sublinea.linea.nombre if  tema.sublinea else ''
                                campo7 = tema.sublinea.nombre if  tema.sublinea else ''
                                if tema.tiene_aprobaciones():
                                    if tema.estado_aprobacion().estado == 1:
                                        estado = 'SOLICITADO'
                                    elif tema.estado_aprobacion().estado == 2:
                                        estado = 'APROBADO'
                                    elif tema.estado_aprobacion().estado == 3:
                                        estado = 'RECHAZADO'
                                campo8 = estado
                                campo9 = 'NO'
                                if tema.mecanismotitulacionposgrado.id in [15,21]:
                                    if tema.cargo_documento_ensayo():
                                        campo9 = 'SI'
                                else:
                                    if tema.revisiontutoriastematitulacionposgradoprofesor_set.filter(status=True).exists():
                                        campo9 = 'SI'
                                campo10 = tema.mecanismotitulacionposgrado.__str__()
                                campo11 = tema.estado_documento_ensayo()
                                ws.write(row_num, 0, campo0, font_style2)
                                ws.write(row_num, 1, cedula, font_style2)
                                ws.write(row_num, 2, campo1, font_style2)
                                ws.write(row_num, 3, campo2, font_style2)
                                ws.write(row_num, 4, campo6, font_style2)
                                ws.write(row_num, 5, campo7, font_style2)
                                ws.write(row_num, 6, campo8, font_style2)
                                ws.write(row_num, 7, campo9, font_style2)
                                ws.write(row_num, 8, campo10, font_style2)
                                ws.write(row_num, 9, campo11, font_style2)
                                row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporte_temas_complexivo_pareja':
                try:
                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=int(request.GET['idconfiguracion']))
                    temas = configuracion.tematitulacionposgradomatricula_set.filter(status=True,
                                                                                     matricula__nivel__periodo=configuracion.periodo,
                                                                                     matricula__inscripcion__carrera=configuracion.carrera,
                                                                                     cabeceratitulacionposgrado__isnull=False,
                                                                                     mecanismotitulacionposgrado__id__in=[15,21]).order_by('cabeceratitulacionposgrado')
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Listado')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Lista de propuestas a temas de titulacion ' + random.randint(
                        1,
                        10000).__str__() + '.xls'
                    columns = [
                        (u"MAESTRANTE", 12000),
                        (u"CÉDULA", 12000),
                        (u"CARRERA", 12000),
                        (u"TEMA", 12000),
                        (u"LINEA", 12000),
                        (u"SUBLINEA", 12000),
                        (u"ESTADO", 4500),
                        (u"DOCUMENTO TRABAJO TITULACIÓN", 4500),
                        (u"CÓDIGO PAREJA", 3000),
                        (u"MECANISMO TITULACIÓN", 12000),
                        (u"ESTADO DEL ENSAYO", 4500),
                    ]

                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    row_num = 2
                    for tema in temas:
                        if tema.tiene_aprobaciones():
                            if tema.estado_aprobacion().estado == 2:
                                campo0 = tema.matricula.inscripcion.persona.nombre_completo_inverso()
                                cedula = tema.matricula.inscripcion.persona.cedula
                                campo1 = tema.matricula.inscripcion.carrera.nombre
                                campo2 = tema.propuestatema
                                campo6 = tema.sublinea.linea.nombre if  tema.sublinea else ''
                                campo7 = tema.sublinea.nombre if  tema.sublinea else ''
                                if tema.tiene_aprobaciones():
                                    if tema.estado_aprobacion().estado == 1:
                                        estado = 'SOLICITADO'
                                    elif tema.estado_aprobacion().estado == 2:
                                        estado = 'APROBADO'
                                    elif tema.estado_aprobacion().estado == 3:
                                        estado = 'RECHAZADO'
                                campo8 = estado
                                campo9 = 'NO'
                                if tema.mecanismotitulacionposgrado.id in [15,21]:
                                    if tema.cabeceratitulacionposgrado.cargo_documento_ensayo():
                                        campo9 = 'SI'
                                else:
                                    if tema.revisiontutoriastematitulacionposgradoprofesor_set.filter(status=True).exists():
                                        campo9 = 'SI'

                                campo10 = tema.cabeceratitulacionposgrado.id
                                campo11 = tema.mecanismotitulacionposgrado.__str__()
                                campo12 = tema.estado_documento_ensayo_pareja()
                                ws.write(row_num, 0, campo0, font_style2)
                                ws.write(row_num, 1, cedula, font_style2)
                                ws.write(row_num, 2, campo1, font_style2)
                                ws.write(row_num, 3, campo2, font_style2)
                                ws.write(row_num, 4, campo6, font_style2)
                                ws.write(row_num, 5, campo7, font_style2)
                                ws.write(row_num, 6, campo8, font_style2)
                                ws.write(row_num, 7, campo9, font_style2)
                                ws.write(row_num, 8, campo10, font_style2)
                                ws.write(row_num, 9, campo11, font_style2)
                                ws.write(row_num, 10, campo12, font_style2)
                                row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporte_inscritos_grupos_complexivos':
                try:
                    inscritos = DetalleGrupoTitulacionPostgrado.objects.filter(grupoTitulacionPostgrado_id=request.GET['id'],status=True)
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Listado')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=inscritos_complexivo' + random.randint( 1, 10000).__str__() + '.xls'
                    columns = [
                        (u"MAESTRANTE", 12000),
                        (u"CARRERA", 12000),
                        (u"CÉDULA", 12000),
                        (u"EMAIL", 12000),
                        (u"MOVIL", 12000),
                        (u"MECANISMO TITULACIÓN", 12000),
                    ]
                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    row_num = 2
                    for fila in inscritos:
                        ws.write(row_num, 0, fila.inscrito.matricula.inscripcion.persona.nombre_completo_inverso().__str__(), font_style2)
                        ws.write(row_num, 1, fila.inscrito.matricula.inscripcion.carrera.nombre.__str__(), font_style2)
                        ws.write(row_num, 2, fila.inscrito.matricula.inscripcion.persona.cedula.__str__(), font_style2)
                        ws.write(row_num, 3, fila.inscrito.matricula.inscripcion.persona.email.__str__(), font_style2)
                        ws.write(row_num, 4, fila.inscrito.matricula.inscripcion.persona.telefono.__str__(), font_style2)
                        ws.write(row_num, 5, fila.inscrito.mecanismotitulacionposgrado.__str__(), font_style2)
                        row_num += 1

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporte_inscritos_nota':
                try:
                    inscritos = DetalleGrupoTitulacionPostgrado.objects.filter(grupoTitulacionPostgrado_id=request.GET['id'],status=True)
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Listado')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=notas_inscritos' + random.randint( 1, 10000).__str__() + '.xls'
                    columns = [
                        (u"MAESTRANTE", 12000),
                        (u"CARRERA", 12000),
                        (u"CÉDULA", 12000),
                        (u"MECANISMO TITULACIÓN", 12000),
                        (u"NOTA EXÁMEN", 12000),
                    ]
                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    row_num = 2
                    for fila in inscritos:
                        ws.write(row_num, 0, fila.inscrito.matricula.inscripcion.persona.nombre_completo_inverso().__str__(), font_style2)
                        ws.write(row_num, 1, fila.inscrito.matricula.inscripcion.carrera.nombre.__str__(), font_style2)
                        ws.write(row_num, 2, fila.inscrito.matricula.inscripcion.persona.cedula.__str__(), font_style2)
                        ws.write(row_num, 3, fila.inscrito.mecanismotitulacionposgrado.__str__(), font_style2)
                        ws.write(row_num, 4, fila.nota.__str__(), font_style2)
                        row_num += 1

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporte_nota_complexivo_ensayo_examen':
                try:
                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=int(request.GET['id']),status=True)
                    temas_complexivo = configuracion.tematitulacionposgradomatricula_set.filter(status=True,mecanismotitulacionposgrado__id__in=[15,21]).order_by('-id')
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Listado')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=notas_complexivo_ensayo_maestrantes' + random.randint(1,
                                                                                                              10000).__str__() + '.xls'
                    columns = [
                        (u"MAESTRANTE", 12000),
                        (u"CARRERA", 12000),
                        (u"PARALELO", 12000),
                        (u"MENCION", 12000),
                        (u"CÉDULA", 12000),
                        (u"MECANISMO TITULACIÓN", 12000),
                        (u"SUBIÓ EL ENSAYO", 12000),
                        (u"NOTA  DEL ENSAYO", 12000),
                        (u"NOTA  DEL EXÁMEN", 12000),

                    ]
                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    row_num = 2

                    for tema in temas_complexivo:
                        if tema.tiene_aprobaciones():
                            if tema.estado_aprobacion().estado == 2:

                                if tema.cabeceratitulacionposgrado:
                                    cargo_ensayo = 'SI' if tema.cabeceratitulacionposgrado.cargo_documento_ensayo() else 'NO'

                                else:
                                    cargo_ensayo = 'SI' if tema.cargo_documento_ensayo() else 'NO'

                                if tema.obtener_nota_examen_complexivo() is None:
                                    nota_examen = ''
                                else:
                                    nota_examen = tema.obtener_nota_examen_complexivo().nota


                                if not tema.obtener_calificacion_ensayo() == None:
                                    nota_ensayo = tema.obtener_calificacion_ensayo()
                                else:
                                    nota_ensayo = ''

                                ws.write(row_num, 0,tema.matricula.inscripcion.persona.nombre_completo_inverso().__str__(),font_style2)
                                ws.write(row_num, 1, tema.matricula.inscripcion.carrera.nombre.__str__(), font_style2)
                                ws.write(row_num, 2, tema.get_paralelo_maestrante().__str__(), font_style2)
                                ws.write(row_num, 3, tema.get_mencion_maestrante().__str__(), font_style2)
                                ws.write(row_num, 4, tema.matricula.inscripcion.persona.cedula.__str__(),font_style2)
                                ws.write(row_num, 5, tema.mecanismotitulacionposgrado.__str__(), font_style2)
                                ws.write(row_num, 6, cargo_ensayo, font_style2)
                                ws.write(row_num, 7, nota_ensayo, font_style2)
                                ws.write(row_num, 8, nota_examen, font_style2)

                                row_num += 1

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'reportenoculminaronprogramaposgrado':
                try:
                    #temas  aprobados
                    if 'id' in request.GET:
                        configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=request.GET['id'])
                        temas_titulacion = configuracion.tematitulacionposgradomatricula_set.filter(status=True,actacerrada =False, aprobado = True)
                    else:
                        temas_titulacion = TemaTitulacionPosgradoMatricula.objects.filter(status=True,actacerrada =False, aprobado = True)

                    nomina_no_culminar_programa_proyectos = temas_titulacion.exclude(mecanismotitulacionposgrado__id__in= [15,21])
                    nomina_no_culminar_programa_complexivo = temas_titulacion.filter(mecanismotitulacionposgrado__id__in=[15,21])
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('no_culminaron_proyectos')
                    ws2 = wb.add_sheet('no_culminaron_complexivo')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=reporte_no_culminaron_programa_posgrado' + random.randint(
                        1,
                        10000).__str__() + '.xls'
                    columns = [
                        (u"COD. CONVOCATORIA", 12000),
                        (u"COHORTE", 12000),
                        (u"CARRERA", 12000),
                        (u"PARALELO", 12000),
                        (u"MENCION", 12000),
                        (u"MAESTRANTE", 12000),
                        (u"CÉDULA", 12000),
                        (u"MÉCANISMO", 12000),
                        (u"TIPO", 12000),
                        (u"COD. PAREJA", 12000),
                        (u"TUTOR", 12000),
                        (u"CÉDULA TUTOR", 12000),
                        (u"# TUTORIAS", 12000),
                        (u"CALIFICACIÓN TRABAJO TITULACIÓN", 12000),
                        (u"CALIFICACIÓN DEFENSA ORAL TITULACIÓN", 12000),
                        (u"CALIFICACIÓN TOTAL TITULACIÓN", 12000),


                    ]
                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    row_num = 2
                    for tema in nomina_no_culminar_programa_proyectos:
                        cantidad_acompanamiento= 'N/A'
                        if tema.tutor:
                            if tema.cabeceratitulacionposgrado:
                                cantidad_acompanamiento  = tema.cabeceratitulacionposgrado.cantidad_acompanamientos()
                            else:
                                cantidad_acompanamiento  = tema.cantidad_acompanamientos()
                        calificacion_trabajo_titulacion = 'N/A'
                        promediopuntajetrabajointegral ='N/A'
                        promediodefensaoral ='N/A'
                        promediofinal ='N/A'

                        if tema.rubrica:
                            detallecalificacion = tema.calificaciontitulacionposgrado_set.filter(status=True).order_by('tipojuradocalificador')
                            try:
                                promediofinal = detallecalificacion.values_list('puntajerubricas').aggregate(promedio=Avg('puntajerubricas'))['promedio']
                            except Exception as ex:
                                promediofinal = 'N/A'
                            listadomodelorubrica = tema.rubrica.modelorubricatitulacionposgrado_set.filter(status=True).order_by('id')
                            try:
                                promediopuntajetrabajointegral = tema.puntajemodelorubrica(listadomodelorubrica[0]) if tema.puntajemodelorubrica(listadomodelorubrica[0]) else  'N/A'
                            except Exception as ex:
                                promediopuntajetrabajointegral =  'N/A'
                            try:
                                promediodefensaoral= tema.puntajemodelorubrica(listadomodelorubrica[1])
                            except Exception as ex:
                                promediodefensaoral = 'N/A'



                        try:
                            ws.write(row_num, 0, tema.convocatoria.id.__str__(), font_style2)
                            ws.write(row_num, 1, tema.matricula.nivel.periodo.__str__(), font_style2)
                            ws.write(row_num, 2, tema.matricula.inscripcion.carrera.__str__(), font_style2)
                            ws.write(row_num, 3, tema.get_paralelo_maestrante().__str__(), font_style2)
                            ws.write(row_num, 4, tema.get_mencion_maestrante().__str__(), font_style2)
                            ws.write(row_num, 5,tema.matricula.inscripcion.persona.nombre_completo_inverso().__str__(),font_style2)
                            ws.write(row_num, 6, tema.matricula.inscripcion.persona.cedula.__str__(),font_style2)
                            ws.write(row_num, 7, tema.mecanismotitulacionposgrado.__str__(), font_style2)
                            ws.write(row_num, 8, 'pareja' if tema.cabeceratitulacionposgrado else 'individual', font_style2)
                            ws.write(row_num, 9, tema.cabeceratitulacionposgrado.id if tema.cabeceratitulacionposgrado else 'N/A', font_style2)
                            ws.write(row_num, 10, tema.tutor.__str__() if tema.tutor else 'N/A', font_style2)
                            ws.write(row_num, 11, tema.tutor.persona.cedula.__str__() if tema.tutor else 'N/A', font_style2)
                            ws.write(row_num, 12, cantidad_acompanamiento, font_style2)
                            ws.write(row_num, 13, promediopuntajetrabajointegral, font_style2)
                            ws.write(row_num, 14, promediodefensaoral, font_style2)
                            ws.write(row_num, 15, promediofinal if promediofinal else 'N/A', font_style2)
                            row_num += 1
                        except Exception as ex:
                            pass


                    #complexivo
                    ws2.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)

                    columns2 = [
                        (u"COD. CONVOCATORIA", 12000),
                        (u"COHORTE", 12000),
                        (u"CARRERA", 12000),
                        (u"MAESTRANTE", 12000),
                        (u"CÉDULA", 12000),
                        (u"MÉCANISMO", 12000),
                        (u"TIPO", 12000),
                        (u"COD. PAREJA", 12000),
                        (u"COD. GRUPO EXAMEN", 12000),
                        (u"NOTA. EXAMEN", 12000),
                        (u"SUBIO EL ENSAYO", 12000),
                        (u"NOTA. ENSAYO", 12000),
                    ]
                    row_num = 1
                    for col_num in range(len(columns2)):
                        ws2.write(row_num, col_num, columns2[col_num][0], fuentecabecera)
                        ws2.col(col_num).width = columns2[col_num][1]

                    row_num = 2
                    for tema in nomina_no_culminar_programa_complexivo:
                        id_grupo_examen = 'N/A'
                        if not tema.tiene_nota_de_examen_and_ensayo_complexivo():
                            if tema.obtener_nota_examen_complexivo():#el detalle del grupo en donde esta inscrito
                                id_grupo_examen = tema.obtener_nota_examen_complexivo().grupoTitulacionPostgrado.pk
                                nota_examen = tema.obtener_nota_examen_complexivo().nota if tema.obtener_nota_examen_complexivo().nota else 'N/A'
                            else:
                                nota_examen = 'N/A'

                            nota_ensayo = tema.obtener_calificacion_ensayo() if tema.obtener_calificacion_ensayo() else 'N/A'

                            ws2.write(row_num, 0, tema.convocatoria.id.__str__(), font_style2)
                            ws2.write(row_num, 1, tema.matricula.nivel.periodo.__str__(), font_style2)
                            ws2.write(row_num, 2, tema.matricula.inscripcion.carrera.__str__(), font_style2)
                            ws2.write(row_num, 3,tema.matricula.inscripcion.persona.nombre_completo_inverso().__str__(),font_style2)
                            ws2.write(row_num, 4, tema.matricula.inscripcion.persona.cedula.__str__(),font_style2)
                            ws2.write(row_num, 5, tema.mecanismotitulacionposgrado.__str__(), font_style2)
                            ws2.write(row_num, 6, 'pareja' if tema.cabeceratitulacionposgrado else 'individual', font_style2)
                            ws2.write(row_num, 7, tema.cabeceratitulacionposgrado.id if tema.cabeceratitulacionposgrado else 'N/A', font_style2)
                            ws2.write(row_num, 8, id_grupo_examen, font_style2)
                            ws2.write(row_num, 9, nota_examen, font_style2)
                            ws2.write(row_num, 10, 'SI' if tema.cargo_documento_ensayo() else 'NO', font_style2)
                            ws2.write(row_num, 11, nota_ensayo, font_style2)

                        row_num += 1


                    wb.save(response)
                    return response
                except Exception as ex:
                    print('Error en: {}'.format(sys.exc_info()[-1].tb_lineno))

            elif action == 'reporte_culminaron_malla_sin_solicitud_titulacion':
                try:
                    #
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('no_culminaron_proyectos')
                    ws2 = wb.add_sheet('no_culminaron_complexivo')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=reporte_culminaron_malla_sin_solicitud_de_tema_titulacion' + random.randint(
                        1,
                        10000).__str__() + '.xls'
                    columns = [
                        (u"Nª", 7000),
                        (u"COHORTE", 12000),
                        (u"CARRERA", 12000),
                        (u"MAESTRANTE", 12000),
                        (u"CÉDULA", 12000),
                        (u"CORREO", 12000),
                        (u"TELEFONO", 12000),
                        (u"CANTIDAD MATERIAS MALLA", 12000),
                        (u"CANTIDAD MATERIAS APROBADAS", 12000),


                    ]
                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    row_num = 2

                    maestrantes = Inscripcion.objects.annotate(
                        id_malla=F('inscripcionmalla__malla_id'),
                        cantidad_materias_mallas=Count('inscripcionmalla__malla__asignaturamalla__asignatura_id',
                                                       distinct=True, filter=Q(
                                inscripcionmalla__malla__id=F('inscripcionmalla__malla_id'))),
                        materias_aprobadas=Count('matricula__materiaasignada', distinct=True,
                                                 filter=Q(matricula__materiaasignada__estado_id=1, status=True))
                    ).values(
                        'persona__nombres', 'persona__apellido1', 'persona__apellido2', 'persona__cedula',
                        'carrera__nombre',
                        'modalidad__nombre', 'materias_aprobadas', 'cantidad_materias_mallas', 'id_malla', 'matricula',
                        'coordinacion_id', 'matricula__nivel__periodo__nombre','persona__email','persona__telefono'
                    ).filter(status=True,
                             coordinacion_id=7,
                             cantidad_materias_mallas=F('materias_aprobadas'),
                             matricula__isnull=False,
                             inscripcionmalla__malla__isnull=False,

                             ).exclude(
                        matricula__tematitulacionposgradomatricula__isnull=False,

                    )
                    i = 1
                    for maestrante in maestrantes:
                        nombre_maestrante = maestrante['persona__apellido1'] + ' '+maestrante['persona__apellido2']+' '+maestrante['persona__nombres']
                        ws.write(row_num, 0, i, font_style2)
                        ws.write(row_num, 1, maestrante['matricula__nivel__periodo__nombre'], font_style2)
                        ws.write(row_num, 2, maestrante['carrera__nombre'], font_style2)
                        ws.write(row_num, 3, nombre_maestrante, font_style2)
                        ws.write(row_num, 4, maestrante['persona__cedula'], font_style2)
                        ws.write(row_num, 5, maestrante['persona__email'], font_style2)
                        ws.write(row_num, 6, maestrante['persona__telefono'], font_style2)
                        ws.write(row_num, 7, maestrante['cantidad_materias_mallas'], font_style2)
                        ws.write(row_num, 8, maestrante['materias_aprobadas'], font_style2)

                        row_num += 1
                        i+=1




                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporteFirmaActaSustentacionComplexivo':
                try:
                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=int(request.GET['id']),status=True)
                    temas_complexivo = configuracion.tematitulacionposgradomatricula_set.filter(status=True,mecanismotitulacionposgrado__id__in=[15,21]).order_by('-id')
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Listado')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=firmas_acta_aprobacion' + random.randint(1,
                                                                                                              10000).__str__() + '.xls'
                    columns = [
                        (u"MAESTRANTE", 12000),
                        (u"CARRERA", 12000),
                        (u"CÉDULA", 12000),
                        (u"MECANISMO TITULACIÓN", 12000),
                        (u"SUBIÓ EL ENSAYO", 12000),
                        (u"NOTA  DEL ENSAYO", 12000),
                        (u"NOTA  DEL EXÁMEN", 12000),
                        (u"FIRMA MAESTRANTE", 12000),
                        (u"FIRMA SECRETARÍA", 12000),
                        (u"FIRMA COORDINADOR", 12000),
                        (u"ABREVIATURA", 12000),
                        (u"TITULO TERCER NIVEL", 2200),

                    ]
                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    row_num = 2

                    for tema in temas_complexivo:
                        if tema.tiene_aprobaciones():
                            if tema.estado_aprobacion().estado == 2:

                                if tema.cabeceratitulacionposgrado:
                                    cargo_ensayo = 'SI' if tema.cabeceratitulacionposgrado.cargo_documento_ensayo() else 'NO'

                                else:
                                    cargo_ensayo = 'SI' if tema.cargo_documento_ensayo() else 'NO'

                                if tema.obtener_nota_examen_complexivo() is None:
                                    nota_examen = ''
                                else:
                                    nota_examen = tema.obtener_nota_examen_complexivo().nota


                                if not tema.obtener_calificacion_ensayo() == None:
                                    nota_ensayo = tema.obtener_calificacion_ensayo()
                                else:
                                    nota_ensayo = ''


                                firma_maestrante = 'NO'
                                firma_secretaria = 'NO'
                                firma_coordinador = 'NO'

                                if tema.obtener_historial_firma_acta_aprobacion_complexivo().filter(estado_acta_firma=2).exists():
                                    firma_maestrante = 'SI'
                                if tema.obtener_historial_firma_acta_aprobacion_complexivo().filter(estado_acta_firma=3).exists():
                                    firma_secretaria = 'SI'
                                if tema.obtener_historial_firma_acta_aprobacion_complexivo().filter(estado_acta_firma=4).exists():
                                    firma_coordinador = 'SI'

                                if tema.matricula.inscripcion.persona.titulacion_solo3nivelparapogrado():
                                    abreviatura_maestrante = tema.matricula.inscripcion.persona.titulacion_solo3nivelparapogrado().titulo.abreviatura.__str__()
                                    titulo_maestrante = tema.matricula.inscripcion.persona.titulacion_solo3nivelparapogrado().titulo.__str__()
                                else:
                                    abreviatura_maestrante="--"
                                    titulo_maestrante="--"

                                ws.write(row_num, 0,tema.matricula.inscripcion.persona.nombre_completo_inverso().__str__(),font_style2)
                                ws.write(row_num, 1, tema.matricula.inscripcion.carrera.nombre.__str__(), font_style2)
                                ws.write(row_num, 2, tema.matricula.inscripcion.persona.cedula.__str__(),font_style2)
                                ws.write(row_num, 3, tema.mecanismotitulacionposgrado.__str__(), font_style2)
                                ws.write(row_num, 4, cargo_ensayo, font_style2)
                                ws.write(row_num, 5, nota_ensayo, font_style2)
                                ws.write(row_num, 6, nota_examen, font_style2)
                                ws.write(row_num, 7, firma_maestrante, font_style2)
                                ws.write(row_num, 8, firma_secretaria, font_style2)
                                ws.write(row_num, 9, firma_coordinador, font_style2)
                                ws.write(row_num, 10, abreviatura_maestrante, font_style2)
                                ws.write(row_num, 11, titulo_maestrante, font_style2)


                                row_num += 1

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'descargarpropuestatemas':
                try:
                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=int(encrypt(request.GET['idconfiguracion'])))
                    temas = TemaTitulacionPosgradoProfesor.objects.filter(status=True,tematitulacionposgradomatricula__matricula__nivel__periodo=configuracion.periodo,
                                                                          tematitulacionposgradomatricula__matricula__inscripcion__carrera=configuracion.carrera,tematitulacionposgradomatriculacabecera__isnull=True ).order_by('tematitulacionposgradomatricula')
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Listado')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Lista de docentes postulantes ' + random.randint(1,
                                                                                                                             10000).__str__() + '.xls'
                    columns = [
                        (u"MAESTRANTE", 12000),
                        (u"CÉDULA", 4000),
                        (u"CARRERA", 12000),
                        (u"TEMA", 12000),
                        (u"MÓDULO REFERENCIA", 12000),
                        (u"VARIABLE DEPENDIENTE", 10000),
                        (u"VARIABLE INDEPENDIENTE", 10000),
                        (u"PROFESOR POSTULANTE", 12000),
                        (u"TITULOS  TERCER NIVEL PROFESOR POSTULANTE", 40500),
                        (u"TITULOS  CUARTO NIVEL PROFESOR POSTULANTE", 40500),
                        (u"ESTADO PROFESOR POSTULANTE", 4500),

                    ]

                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    row_num = 2
                    for tema in temas:
                        cmaes = tema.tematitulacionposgradomatricula.matricula.inscripcion.persona.nombre_completo_inverso()
                        cmaesced = tema.tematitulacionposgradomatricula.matricula.inscripcion.persona.cedula
                        ccarrera = tema.tematitulacionposgradomatricula.matricula.inscripcion.carrera.nombre
                        ctema = tema.tematitulacionposgradomatricula.propuestatema
                        ctemamod = tema.tematitulacionposgradomatricula.moduloreferencia
                        cvdepen = tema.tematitulacionposgradomatricula.variabledependiente
                        cvindep = tema.tematitulacionposgradomatricula.variableindependiente
                        cpostula = tema.profesor.persona.nombre_completo_inverso()
                        titulotercerNivel =tema.profesor.persona.titulacion_set.filter(status=True,titulo__nivel = 3)
                        titulocuartonivel =tema.profesor.persona.titulacion_set.filter(status=True,titulo__nivel = 4)
                        tercer_nivel =  ""
                        cuarto_nivel =  ""
                        for titulo  in titulotercerNivel:
                            tercer_nivel= tercer_nivel +" [' "+ str(titulo.titulo.nombre) +" '] "

                        for titulo in titulocuartonivel:
                            cuarto_nivel = cuarto_nivel +" [' "+ str(titulo.titulo.nombre)+" '] "

                        if tema.aprobado:
                            estado = 'APROBADO'
                        else:
                            estado = 'PENDIENTE'

                        cestadopos = estado
                        ws.write(row_num, 0, cmaes, font_style2)
                        ws.write(row_num, 1, cmaesced, font_style2)
                        ws.write(row_num, 2, ccarrera, font_style2)
                        ws.write(row_num, 3, ctema, font_style2)
                        ws.write(row_num, 4, ctema, font_style2)
                        ws.write(row_num, 5, cvdepen, font_style2)
                        ws.write(row_num, 6, cvindep, font_style2)
                        ws.write(row_num, 7, cpostula, font_style2)
                        ws.write(row_num, 8, tercer_nivel, font_style2)
                        ws.write(row_num, 9, cuarto_nivel, font_style2)
                        ws.write(row_num, 10, cestadopos, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'descargarpropuestatemaspareja':
                try:
                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=int(encrypt(request.GET['idconfiguracion'])))
                    cursor = connections['default'].cursor()
                    sql = """
                    SELECT
                    periodo.nombre cohorte,
                    carrer.nombre carrera,
                    mecanismo.nombre Mecanismo,
                    (
                    SELECT
                    coalesce(json_agg(maestrante), '[]')
                    FROM (
                    SELECT
                            (per.apellido1||' '||per.apellido2 ||' '||per.nombres ||'- CI:'|| per.cedula) AS maestrante
                    FROM sga_tematitulacionposgradomatricula mat
                    INNER JOIN sga_matricula ma ON ma.id = mat.matricula_id
                    INNER JOIN sga_inscripcion ins ON ins.id = ma.inscripcion_id
                    INNER JOIN sga_persona per ON per.id = ins.persona_id
                    WHERE mat.cabeceratitulacionposgrado_id = cab.id AND mat.status = TRUE 
                            ) maestrante
                    ) maestrantes,
                    cab.propuestatema tema,
                    (persona.apellido1||' '||persona.apellido2 ||' '||persona.nombres) AS profesor,
                    solicitud.aprobado,
                    profesor.id 
                    FROM sga_tematitulacionposgradoprofesor solicitud
                    INNER JOIN sga_profesor profesor ON profesor.id = solicitud.profesor_id
                    INNER JOIN sga_persona persona ON persona.id = profesor.persona_id
                    INNER JOIN sga_tematitulacionposgradomatriculacabecera cab ON cab.id = solicitud.tematitulacionposgradomatriculacabecera_id
                    INNER JOIN sga_mecanismotitulacionposgrado mecanismo ON mecanismo.id = cab.mecanismotitulacionposgrado_id
                    INNER JOIN sga_configuraciontitulacionposgrado conf ON conf.id = cab.convocatoria_id
                    INNER JOIN sga_periodo periodo ON periodo.id = conf.periodo_id
                    INNER JOIN sga_carrera carrer ON carrer.id = conf.carrera_id
                    WHERE solicitud.status = TRUE AND periodo.id = '%s' AND conf.carrera_id = '%s'
                    """ % (configuracion.periodo.id,configuracion.carrera.id)


                    cursor.execute(sql)
                    results = cursor.fetchall()

                    __author__ = 'Unemi'
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('solicitudes_pareja')
                    formatoceldagris = workbook.add_format(
                        {'align': 'center', 'border': 1, 'text_wrap': True})
                    formatoceldaleft = workbook.add_format({'text_wrap': True, 'align': 'left'})

                    ws.set_column(0, 0, 50)
                    ws.set_column(1, 3, 50)
                    ws.set_column(4, 4, 80)
                    ws.set_column(5, 8, 50)
                    ws.set_column(9, 10, 50)
                    ws.set_column(11, 13, 50)
                    ws.set_column(14, 14, 120)
                    ws.set_column(15, 15, 120)
                    ws.set_column(16, 16, 50)


                    # Text with formatting.
                    ws.write('A1', 'COHORTE',formatoceldagris)
                    ws.write('B1', 'CARRERA',formatoceldagris)
                    ws.write('C1', 'MECANISMO',formatoceldagris)
                    ws.write('D1', 'MAESTRANTES',formatoceldagris)
                    ws.write('E1', 'TEMA',formatoceldagris)
                    ws.write('F1', 'PROFESOR POSTULANTE',formatoceldagris)
                    ws.write('G1', 'TITULOS TERCER NIVEL PROFESOR POSTULANTE',formatoceldagris)
                    ws.write('H1', 'TITULOS CUARTO NIVEL PROFESOR POSTULANTE',formatoceldagris)
                    ws.write('I1', 'ESTADO POSTULANTE',formatoceldagris)

                    row_num = 1

                    for dato in results:
                        cohorte = dato[0]
                        carrera = dato[1]
                        mecanismo = dato[2]
                        maestrante = 'M1: '+dato[3][0] +'  M2: '+dato[3][1]
                        tema = dato[4]
                        cpostula = dato[5]
                        if dato[6]:
                            estado = 'APROBADO'
                        else:
                            estado = 'PENDIENTE'
                        profesor_id = dato[7]
                        obtener_profesor = Profesor.objects.get(id=profesor_id)
                        titulotercerNivel = obtener_profesor.persona.titulacion_set.filter(status=True, titulo__nivel=3)
                        titulocuartonivel = obtener_profesor.persona.titulacion_set.filter(status=True, titulo__nivel=4)
                        tercer_nivel = ""
                        cuarto_nivel = ""

                        for titulo in titulotercerNivel:
                            tercer_nivel = tercer_nivel + " [' "+str(titulo.titulo.nombre)+" '] "

                        for titulo in titulocuartonivel:
                            cuarto_nivel = cuarto_nivel + " [' "+str(titulo.titulo.nombre)+" '] "

                        cestadopos = estado
                        ws.write(row_num, 0, cohorte,formatoceldagris)
                        ws.write(row_num, 1, carrera,formatoceldagris)
                        ws.write(row_num, 2, mecanismo,formatoceldagris)
                        ws.write(row_num, 3, maestrante,formatoceldagris)
                        ws.write(row_num, 4, tema,formatoceldagris)
                        ws.write(row_num, 5, cpostula,formatoceldagris)
                        ws.write(row_num, 6, tercer_nivel,formatoceldagris)
                        ws.write(row_num, 7, cuarto_nivel,formatoceldagris)
                        ws.write(row_num, 8, cestadopos,formatoceldagris)

                        row_num += 1
                    workbook.close()
                    output.seek(0)
                    filename = 'reporte_solicitudes_pareja' + random.randint(1,10000).__str__() + '.xlsx'
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'configuraciones':
                try:
                    data['title'] = u'Configuración'
                    data['ponderaciones'] = PonderacionRubricaPosgrado.objects.filter(status=True)
                    return render(request, "adm_configuracionpropuesta/configuraciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'asignar_rubrica':
                try:
                    data['tema'] = tema = TemaTitulacionPosgradoMatricula.objects.get(pk=request.GET['id'])
                    form = AsignarRubricaForm()
                    programa_rubricas_id = DetalleTitulacionPosgrado.objects.values_list('rubricatitulacionposgrado', flat=True).filter(status = True ,mecanismotitulacionposgrado = tema.mecanismotitulacionposgrado,configuracion =tema.convocatoria )
                    if programa_rubricas_id:
                        form.fields['rubrica'].queryset = RubricaTitulacionPosgrado.objects.filter(status=True, id__in = programa_rubricas_id)
                    data['form2'] = form
                    template = get_template("adm_configuracionpropuesta/modal/formAsignarRubrica.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'asignar_rubrica_pareja':
                try:
                    data['tema'] = tema = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=request.GET['id'])
                    form = AsignarRubricaForm()
                    programa_rubricas_id = DetalleTitulacionPosgrado.objects.values_list('rubricatitulacionposgrado', flat=True).filter(status = True ,mecanismotitulacionposgrado = tema.mecanismotitulacionposgrado,configuracion =tema.convocatoria )
                    if programa_rubricas_id:
                        form.fields['rubrica'].queryset = RubricaTitulacionPosgrado.objects.filter(status=True, id__in = programa_rubricas_id)
                    data['form2'] = form
                    template = get_template("adm_configuracionpropuesta/modal/formAsignarRubrica.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'asignar_modalidad_sustentacion':
                try:
                    data['form2'] = AsignarModalidadSustentacionForm()
                    data['tema']= tema =TemaTitulacionPosgradoMatricula.objects.get(pk=request.GET['id'])
                    template = get_template("adm_configuracionpropuesta/modal/formAsignarmodalidadsustentacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'asignar_modalidad_sustentacion_pareja':
                try:
                    data['form2'] = AsignarModalidadSustentacionForm()
                    data['tema']= tema =TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=request.GET['id'])
                    template = get_template("adm_configuracionpropuesta/modal/formAsignarmodalidadsustentacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'firmar_acta_de_aprobacion':
                try:
                    data['title'] = u'Firmar acta de aprobación'
                    data['id'] = request.GET['id']
                    eTemaTitulacionPosgradoMatricula = TemaTitulacionPosgradoMatricula.objects.get(pk= int(request.GET['id']))
                    eecarrera = eTemaTitulacionPosgradoMatricula.convocatoria.carrera
                    eeperiodo = eTemaTitulacionPosgradoMatricula.convocatoria.periodo

                    form = FirmarActaAprobacionCoordinacionForm()

                    eCoordinadorCarrera = CoordinadorCarrera.objects.filter(periodo=eeperiodo, carrera=eecarrera,persona = persona)
                    if eCoordinadorCarrera.exists():
                        TIPO_COORDINADOR = (
                            (2, u'COORDINADOR DEL PROGRAMA'),
                        )
                        form.fields['tipo'].choices = TIPO_COORDINADOR  # es coordinador
                    else:
                        TIPO_FIRMA_SECRETARIA = (
                            (1, u'SECRETARÍA TÉCNICA DE POSGRADO '),
                        )
                        form.fields['tipo'].choices = TIPO_FIRMA_SECRETARIA  # es secretaría



                    data['form'] = form
                    template = get_template("adm_configuracionpropuesta/modal/form_firmar_acta.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'historial_firmar_acta_de_aprobacion':
                try:
                    data['title'] = u'Historial firmar acta de aprobación'
                    data['tema'] = tema =  TemaTitulacionPosgradoMatricula.objects.get(pk = request.GET['id'])
                    data['historial_firma'] = tema.obtener_historial_firma_acta_aprobacion_complexivo()
                    template = get_template("adm_configuracionpropuesta/modal/historial_firmar_acta.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'historial_firma_actas_de_grado':
                try:
                    data['title'] = u'Historial firmar acta de aprobación'
                    data['tema'] = tema =  TemaTitulacionPosgradoMatricula.objects.get(pk = request.GET['id'])
                    data['historial_firma'] = tema.obtener_historial_firma_acta_de_grado_complexivo_firma()
                    template = get_template("adm_configuracionpropuesta/modal/historial_firma_actas_de_grado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
            elif action == 'historial_firma_acta_sustentacion_nota':
                try:
                    data['title'] = u'Historial firmar acta de sustentación con notas'
                    data['tema'] = tema =  TemaTitulacionPosgradoMatricula.objects.get(pk = request.GET['id'])
                    data['historial_firma'] = tema.get_historial_firma_acta_sustentacion_con_nota()

                    template = get_template("adm_configuracionpropuesta/modal/historial_firma_actas_de_grado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'historial_firma_certificacion_defensa':
                try:
                    data['title'] = u'Historial firmar acta de sustentación con notas'
                    data['tema'] = tema =  TemaTitulacionPosgradoMatricula.objects.get(pk = request.GET['id'])
                    data['historial_firma'] = tema.get_historial_firma_por_certificacion_defensa()
                    template = get_template("adm_configuracionpropuesta/modal/historial_firma_actas_de_grado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'actualizar_fecha_solicitud_propuesta':
                try:
                    tema = TemaTitulacionPosgradoMatricula.objects.get(pk=request.GET['id'])
                    data['form2'] = ActualizarFechaSolicitudForm(
                        initial={
                            'fecha_solicitud': tema.fecha_creacion
                        }
                    )
                    data['tema']= tema
                    template = get_template("adm_configuracionpropuesta/modal/formActualizarfechasolicitud.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addponderacionmodal':
                try:
                    data['form2'] = PonderacionRubricaForm()
                    template = get_template("adm_configuracionpropuesta/modal/formponderacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editponderacionmodal':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = PonderacionRubricaPosgrado.objects.get(pk=request.GET['id'])
                    data['form2'] = PonderacionRubricaForm(initial=model_to_dict(filtro))
                    template = get_template("adm_configuracionpropuesta/modal/formponderacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'rubrica':
                try:
                    search = None
                    data['title'] = u'Rubricas'
                    rubricas = RubricaTitulacionPosgrado.objects.filter(status=True).order_by('-id')
                    if 'id' in request.GET:
                        ids = int(request.GET['id'])
                        rubricas = rubricas.filter(status=True,id=int(request.GET['id']))

                    if 's' in request.GET:
                        search = request.GET['s']
                        # s = search.split(" ")
                        rubricas = rubricas.filter(status=True,nombre__icontains=search)

                    paging = MiPaginador(rubricas, 25)
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
                    data['temas'] = page.object_list
                    data['search'] = search if search else ""
                    data['rubricas'] = rubricas
                    data['tiporubrica'] = TIPO_RUBRICA
                    return render(request, "adm_configuracionpropuesta/rubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadodetallerubricas':
                try:
                    data['rubrica'] = rubrica = RubricaTitulacionPosgrado.objects.get(pk=request.GET['id'], status=True)
                    data['title'] = u'Detalle de rúbricas'
                    data['listadodetallerubricas'] = rubrica.detallerubricatitulacionposgrado_set.filter(status=True).order_by('modelorubrica__orden','orden')
                    data['ponderacionesrubrica'] = rubrica.rubricatitulacioncabponderacionposgrado_set.filter(status=True).order_by('orden')
                    mostrar = True
                    llenarescala = True
                    llenarpondercion = True
                    if rubrica.en_usoalternativa():
                        mostrar = False
                    if rubrica.rubricatitulacioncabponderacionposgrado_set.filter(status=True):
                        llenarescala = False
                    if rubrica.modelorubricatitulacionposgrado_set.filter(status=True):
                        llenarpondercion = False
                    data['mostrar'] = mostrar
                    data['llenarescala'] = llenarescala
                    data['llenarpondercion'] = llenarpondercion
                    data['listadomodelorubrica'] = rubrica.modelorubricatitulacionposgrado_set.filter(status=True).order_by('id')
                    return render(request, "adm_configuracionpropuesta/rubricas.html", data)
                except Exception as ex:
                    pass

            elif action == 'tribunaltemas':
                try:
                    data['title'] = u'Tribunal tema titulación'
                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=int(request.GET['idconfiguracion']))
                    periodo = configuracion.periodo
                    carrera = configuracion.carrera
                    if not periodo.visible:
                        return HttpResponseRedirect("/?info=Periodo Inactivo.")
                    search = None
                    mallaid = None
                    nivelmallaid = None
                    ids = None
                    hoy = datetime.now().date()
                    if 'id' in request.GET:
                        ids = int(request.GET['id'])
                        temas = configuracion.tematitulacionposgradomatricula_set.filter(matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera, status=True,id=int(request.GET['id']),  revisiontutoriastematitulacionposgradoprofesor__estado=2).distinct().order_by('-tribunaltematitulacionposgradomatricula__fechadefensa')

                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            temas = configuracion.tematitulacionposgradomatricula_set.filter(Q(matricula__inscripcion__persona__nombres__icontains=search) |
                                                                                             Q(matricula__inscripcion__persona__apellido1__icontains=search) |
                                                                                             Q(matricula__inscripcion__persona__apellido2__icontains=search) |
                                                                                             Q(matricula__inscripcion__persona__cedula__icontains=search) |
                                                                                             Q(matricula__inscripcion__persona__pasaporte__icontains=search) |
                                                                                             Q(matricula__inscripcion__persona__usuario__username__icontains=search),matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera, status=True, revisiontutoriastematitulacionposgradoprofesor__estado=2).distinct().order_by('-tribunaltematitulacionposgradomatricula__fechadefensa')
                        else:
                            temas = configuracion.tematitulacionposgradomatricula_set.filter(Q(matricula__inscripcion__persona__apellido1__icontains=ss[0]) &
                                                                                             Q(matricula__inscripcion__persona__apellido2__icontains=ss[1]),matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera, status=True, revisiontutoriastematitulacionposgradoprofesor__estado=2).distinct().order_by('-tribunaltematitulacionposgradomatricula__fechadefensa')
                    else:
                        temas = configuracion.tematitulacionposgradomatricula_set.filter(status=True,matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera, revisiontutoriastematitulacionposgradoprofesor__estado=2).distinct().order_by('-tribunaltematitulacionposgradomatricula__fechadefensa')
                    # data['sustentanhoy'] = configuracion.tematitulacionposgradomatricula_set.filter(status=True,matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera, revisiontutoriastematitulacionposgradoprofesor__estado=2, tribunaltematitulacionposgradomatricula__fechadefensa=hoy).distinct().order_by('-tribunaltematitulacionposgradomatricula__fechadefensa')
                    paging = MiPaginador(temas, 25)
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
                    data['temas'] = page.object_list
                    data['search'] = search if search else ""
                    data['periodo'] = periodo
                    data['configuracion'] = configuracion
                    data['escoordinadoraposgrado'] = escoordinadoraposgrado

                    # ingreso tribunal pareja
                    temas_pareja = configuracion.tematitulacionposgradomatriculacabecera_set.filter(status=True, revisiontutoriastematitulacionposgradoprofesor__estado=2).distinct()
                    data['temas_pareja'] = temas_pareja

                    return render(request, "adm_configuracionpropuesta/tribunaltemas.html", data)
                except Exception as ex:
                    pass

            elif action == 'graduarExamenComplexivo':
                try:
                    data['title'] = "Listado de maestrantes aptos para graduar"
                    search = None
                    firmado = 0
                    if ((request.user.has_perm("sga.puede_calificar_ensayos_titulacion_posgrado") and request.user.has_perm(
                            "sga.puede_gestionar_configuraciones_titulacion_posgrado")) or request.user.has_perm(
                            "sga.puede_gestionar_configuraciones_titulacion_posgrado")):
                        firmado = 3  # firmado por secretaria
                    else:
                        if request.user.has_perm("sga.puede_calificar_ensayos_titulacion_posgrado") and not request.user.has_perm(
                                "sga.puede_gestionar_configuraciones_titulacion_posgrado"):
                            firmado = 4  # firmado por coordinador

                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=int(request.GET['idconfiguracion']))
                    temas_complexivo = configuracion.tematitulacionposgradomatricula_set.filter(status=True, mecanismotitulacionposgrado__id__in=[15,21]).order_by('-id')
                    if 's' in request.GET:
                        search = request.GET['s']
                        temas_complexivo = temas_complexivo.filter(
                                                 Q(propuestatema__icontains=search) |
                                                 Q(matricula__inscripcion__persona__nombres__icontains=search) |
                                                 Q(matricula__inscripcion__persona__apellido1__icontains=search) |
                                                 Q(matricula__inscripcion__persona__apellido2__icontains=search) |
                                                 Q(matricula__inscripcion__persona__cedula__icontains=search))

                    temas_unidos  = []
                    data['existen_actas_sin_cerrar']= existen_actas_sin_cerrar =  True if temas_complexivo.filter(actacerrada=False,estado_acta_firma=4).count() > 0 else False
                    for tema in temas_complexivo:
                        if tema.tiene_aprobaciones():
                            if tema.estado_aprobacion().estado == 2:#si la solicitud del tema de examen complexivo esta aprobado
                                if configuracion.tipocomponente == 1:  # practico y teorico
                                    if tema.tiene_nota_de_examen_and_ensayo_complexivo():
                                        nota_examen = tema.obtener_nota_examen_complexivo().nota
                                        nota_ensayo = tema.obtener_calificacion_ensayo()
                                        temas_unidos.append([tema, nota_examen, nota_ensayo])

                                if configuracion.tipocomponente == 2:  # practico
                                        nota_ensayo = tema.obtener_calificacion_ensayo()
                                        temas_unidos.append([tema, 0,nota_ensayo])

                                if configuracion.tipocomponente == 3:  # teorico
                                    if tema.tiene_calificacion_examen_complexivoposgrado():
                                        nota_examen = tema.obtener_nota_examen_complexivo().nota
                                        temas_unidos.append([tema, nota_examen,0])

                    paging = MiPaginador(temas_unidos, 15)
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
                    data['temas_examen_complexivo'] = page.object_list
                    data['search'] = search if search else ""
                    data['configuracion'] = configuracion
                    data['firmado'] = firmado
                    return render(request, "adm_configuracionpropuesta/graduar_examen_complexivo.html", data)
                except Exception as ex:
                    pass

            elif action == 'importar_numero_acta':
                try:
                    id = int(request.GET.get('id',0))
                    if id == 0:
                        raise NameError(f"Parametro no encontrado")
                    eConfiguracionTitulacionPosgrado = ConfiguracionTitulacionPosgrado.objects.get(pk=id)
                    data['eConfiguracionTitulacionPosgrado'] = eConfiguracionTitulacionPosgrado
                    data['action'] = action
                    template = get_template("adm_configuracionpropuesta/modal/importar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'cerrar_actas_y_graduar_masivo_seleccionados':
                try:
                    data['ids_tema'] = id_string = request.GET.get('ids_tema', 0)
                    id_list = ast.literal_eval(id_string)

                    # Si id_list no es una lista, conviértelo en una lista con un solo elemento
                    if not isinstance(id_list, tuple):
                        id_list = (id_list,)
                    eTemaTitulacionPosgradoMatriculas = TemaTitulacionPosgradoMatricula.objects.filter(pk__in=id_list)

                    data['action'] = action

                    data['eTemaTitulacionPosgradoMatriculas'] = eTemaTitulacionPosgradoMatriculas
                    template = get_template("adm_configuracionpropuesta/modal/Formcerrargraduarmasivo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})


            elif action == 'firma_masiva_complexivo_posgrado':
                try:
                    id = int(request.GET.get('id',0))
                    data['ids_tema'] = id_string = request.GET.get('ids_tema', 0)
                    id_list = ast.literal_eval(id_string)
                    # Si id_list no es una lista, conviértelo en una lista con un solo elemento
                    if not isinstance(id_list, tuple):
                        id_list = (id_list,)

                    data['eTemaTitulacionPosgradoMatricula'] = eTemaTitulacionPosgradoMatricula = TemaTitulacionPosgradoMatricula.objects.filter(pk__in=id_list)
                    if not id_list:
                        raise NameError(f"Favor seleccionar almenos una acta de aceptaciòn")

                    if id == 0:
                        raise NameError(f"Parametro no encontrado")

                    firmado = 0
                    if ((request.user.has_perm("sga.puede_calificar_ensayos_titulacion_posgrado") and request.user.has_perm(
                            "sga.puede_gestionar_configuraciones_titulacion_posgrado")) or request.user.has_perm(
                            "sga.puede_gestionar_configuraciones_titulacion_posgrado")):
                        firmado = 3  # firmado por secretaria
                    else:
                        if request.user.has_perm("sga.puede_calificar_ensayos_titulacion_posgrado") and not request.user.has_perm(
                                "sga.puede_gestionar_configuraciones_titulacion_posgrado"):
                            firmado = 4  # firmado por coordinador

                    eConfiguracionTitulacionPosgrado = ConfiguracionTitulacionPosgrado.objects.get(pk=id)
                    data['eConfiguracionTitulacionPosgrado'] = eConfiguracionTitulacionPosgrado
                    data['action'] = action
                    data['firmado'] = firmado
                    template = get_template("adm_configuracionpropuesta/modal/formFirmaMasiva.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})


            elif action == 'acta_grado_masiva_complexivo_posgrado':
                try:
                    id = request.GET.get('id', 0)
                    if id == 0: raise NameError("Parametro no encontrado")
                    eConfiguracionTitulacionPosgrado = ConfiguracionTitulacionPosgrado.objects.get(pk=id)

                    rutas_certificados = []
                    dominiosistema = request.build_absolute_uri('/')[:-1].strip("/")
                    directory = os.path.join(SITE_STORAGE, 'media/zip')
                    try:
                        os.stat(directory)
                    except:
                        os.mkdir(directory)

                    directory = os.path.join(SITE_STORAGE, 'media/actasgradocomplexivo')
                    try:
                        os.stat(directory)
                    except:
                        os.mkdir(directory)

                    url = os.path.join(SITE_STORAGE, 'media', 'zip','actasgradocomplexivo.zip')
                    url_zip = url
                    fantasy_zip = zipfile.ZipFile(url, 'w')
                    if eConfiguracionTitulacionPosgrado.temas_complexivo_acta_grado():
                        for tema in eConfiguracionTitulacionPosgrado.temas_complexivo_acta_grado():
                            try:
                                pdf_content = actagradoposgradocomplexivocontent(tema.pk)
                                temp_pdf_path = os.path.join(SITE_STORAGE, 'media/actasgradocomplexivo', f'{remover_caracteres_especiales_unicode(tema.matricula.inscripcion.persona.__str__())}.pdf')
                                url_archivo = (temp_pdf_path).replace('\\', '/')
                                ruta_archivo = (url_archivo).replace('//', '/')
                                with open(ruta_archivo, 'wb') as temp_pdf:
                                    temp_pdf.write(pdf_content)

                                eParalelo = tema.get_paralelo_maestrante()
                                carpeta_paralelo = f"{eParalelo}/"
                                # Agregar el archivo PDF a la carpeta de la inscripción dentro del ZIP
                                fantasy_zip.write(ruta_archivo, carpeta_paralelo + os.path.basename(ruta_archivo))
                            except Exception as ex:
                                pass
                    else:
                        raise NameError('Erro al generar')
                    fantasy_zip.close()
                    response = HttpResponse(open(url_zip, 'rb'), content_type='application/zip')
                    response['Content-Disposition'] = 'attachment; filename=actasgradocomplexivo.zip'
                    return response


                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)


            elif action == 'dowload_formato_numero_de_acta':
                try:
                    id = int(request.GET.get('id', 0))
                    if id == 0:
                        raise NameError(f"Parametro no encontrado")
                    eConfiguracionTitulacionPosgrado = ConfiguracionTitulacionPosgrado.objects.get(pk=id)
                    eTemaTitulacionPosgradoMatricula = eConfiguracionTitulacionPosgrado.tematitulacionposgradomatricula_set.filter(status=True, mecanismotitulacionposgrado__id__in=[15,21],actacerrada=True,estado_acta_firma=4,calificacion__gte=70).order_by('-id')

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
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=importar_numeroacta' + random.randint(1, 10000).__str__() + '.xls'

                    columns = [
                        (u"N", 2000),
                        (u"ID_PROPUESTA", 2000),
                        (u"APELLIDOS", 4000),
                        (u"NOMBRES", 15000),
                        (u"CEDULA", 15000),
                        (u"NUMERO_DE_ACTA", 15000),
                    ]
                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'

                    row_num = 1
                    i = 0
                    for tema in eTemaTitulacionPosgradoMatricula:
                        i += 1
                        ws.write(row_num, 0, i, font_style2)
                        ws.write(row_num, 1, tema.pk, font_style2)
                        ws.write(row_num, 2, tema.matricula.inscripcion.persona.apellido1.__str__() + ' '+ tema.matricula.inscripcion.persona.apellido2.__str__(), font_style2)
                        ws.write(row_num, 3, tema.matricula.inscripcion.persona.nombres.__str__(), font_style2)
                        ws.write(row_num, 4, tema.matricula.inscripcion.persona.cedula.__str__(), font_style2)
                        ws.write(row_num, 5, tema.get_numero_acta_graduado().__str__(), font_style2)
                        row_num += 1

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'propuestastemasprofesor':
                try:
                    data['title'] = u'Solicitudes de profesores para ser tutor de temas de titulación'
                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=int(request.GET['idconfiguracion']))
                    periodo = configuracion.periodo
                    carrera = configuracion.carrera
                    if not periodo.visible:
                        return HttpResponseRedirect("/?info=Periodo Inactivo.")
                    search = None
                    mallaid = None
                    nivelmallaid = None
                    ids = None

                    temas = configuracion.tematitulacionposgradomatricula_set.filter(status=True,matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera, tematitulacionposgradoprofesor__isnull=False, cabeceratitulacionposgrado__isnull = True).exclude(mecanismotitulacionposgrado_id__in = [15,21]).distinct().order_by('-id')
                    if 'id' in request.GET:
                        ids = int(request.GET['id'])
                        temas = configuracion.tematitulacionposgradomatricula_set.filter(matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera, status=True,id=int(request.GET['id']), tematitulacionposgradoprofesor__isnull=False).distinct()

                    if 's' in request.GET:
                        search = request.GET['s']
                        # s = search.split(" ")
                        temas = configuracion.tematitulacionposgradomatricula_set.filter(Q(matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera, status=True,propuestatema__icontains=search, tematitulacionposgradoprofesor__isnull=False)|
                                                                                         Q( status=True,matricula__inscripcion__persona__cedula__icontains=search)).distinct()

                    paging = MiPaginador(temas, 25)
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
                    data['temas'] = page.object_list
                    data['search'] = search if search else ""
                    data['periodo'] = periodo

                    data['configuracion'] = configuracion
                    # temas solocitados en pareja
                    searchPareja = None
                    temaspareja = configuracion.tematitulacionposgradomatriculacabecera_set.filter(status=True, tematitulacionposgradoprofesor__isnull=False).exclude(mecanismotitulacionposgrado_id__in = [15,21]).distinct().order_by('-id')

                    if 'sPareja' in request.GET:
                        searchPareja = request.GET['sPareja']

                        cabecera = configuracion.tematitulacionposgradomatricula_set.values_list(
                            'cabeceratitulacionposgrado').filter(status=True, cabeceratitulacionposgrado__isnull=False,
                                                                 matricula__inscripcion__persona__cedula__icontains=searchPareja).distinct()

                        temaspareja = temaspareja.filter(
                                                       Q(propuestatema__icontains=searchPareja) |
                                                       Q(pk__in=cabecera)|
                                                       Q(tutor=searchPareja)
                                                       )


                    paging2 = MiPaginador(temaspareja, 25)
                    p2 = 1
                    try:
                        paginasesion2 = 1
                        if 'paginador2' in request.session:
                            paginasesion2 = int(request.session['paginador2'])
                        if 'page2' in request.GET:
                            p2 = int(request.GET['page2'])
                        else:
                            p2 = paginasesion2
                        try:
                            page2 = paging2.page(p2)
                        except:
                            p2 = 1
                        page2 = paging2.page(p2)
                    except:
                        page2 = paging2.page(p2)
                    request.session['paginador2'] = p2
                    data['paging2'] = paging2
                    data['rangospaging2'] = paging2.rangos_paginado(p)
                    data['page2'] = page2
                    data['searchPareja'] = searchPareja if searchPareja else ""
                    data['temasparejas'] = page2.object_list



                    return render(request, "adm_configuracionpropuesta/propuestastemasprofesor.html", data)
                except Exception as ex:
                    pass

            elif action == 'exceltribunalconvocatoria':
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
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Graduados' + random.randint(1, 10000).__str__() + '.xls'
                    idtodos = int(request.GET['idtodos'])
                    fech_ini = request.GET['fechainicio']
                    fech_fin = request.GET['fechafin']
                    columns = [
                        (u"N.", 2000),
                        (u"CEDULA", 4000),
                        (u"APELLIDOS Y NOMBRES", 15000),
                        (u"CARRERA", 15000),
                        (u"COHORTE", 15000),
                        (u"FECHA SUSTENTACIÓN", 4000),
                        (u"PRESIDENTE(A)", 15000),
                        (u"SECRETARIO(A)", 15000),
                        (u"DIRECTOR(A) TFM", 15000),
                        (u"TEMA PROPUESTO", 15000),
                        (u"TEMA VÁLIDO CORREJIDO POR TUTOR", 15000),
                        (u"TRABAJO DE TITULACION", 2500),
                        (u"DEFENSA ORAL", 2500),
                        (u"NOTA FINAL(SUMA)", 2500),
                        (u"NOTA FINAL(PROMEDIO)", 2500),
                    ]
                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=int(request.GET['idconfiguracion']))
                    if idtodos == 1:
                        listadotribunal = configuracion.tematitulacionposgradomatricula_set.filter(revisiontutoriastematitulacionposgradoprofesor__estado=2, status=True).distinct().order_by('-tribunaltematitulacionposgradomatricula__fechadefensa')
                    else:
                        listadotribunal = configuracion.tematitulacionposgradomatricula_set.filter(tribunaltematitulacionposgradomatricula__fechadefensa__range=(fech_ini, fech_fin), status=True).distinct()
                    row_num = 1
                    i = 0
                    for listado in listadotribunal:
                        textoidentidad = ''
                        if listado.matricula.inscripcion.persona.cedula:
                            textoidentidad = listado.matricula.inscripcion.persona.cedula
                        else:
                            if listado.matricula.inscripcion.persona.pasaporte:
                                textoidentidad = listado.matricula.inscripcion.persona.pasaporte
                        campo1 = textoidentidad
                        campo2 = listado.matricula.inscripcion.persona.apellido1 + ' ' + listado.matricula.inscripcion.persona.apellido2 + ' ' + listado.matricula.inscripcion.persona.nombres
                        campo3 = listado.matricula.inscripcion.carrera.nombre + (" MENCION " + listado.matricula.inscripcion.carrera.mencion if listado.matricula.inscripcion.carrera.mencion else "")
                        campo4 = listado.matricula.nivel.periodo.nombre

                        campo6 = None
                        campo7 = None
                        campo8 = None
                        campo9 = None
                        campo5 = ''
                        campo10 = listado.propuestatema
                        if listado.tribunaltematitulacionposgradomatricula_set.filter(status=True).exists():
                            tribunal = TribunalTemaTitulacionPosgradoMatricula.objects.get(tematitulacionposgradomatricula=listado)
                            campo6 = tribunal.fechadefensa
                            campo5 = tribunal.subtema
                            if tribunal.presidentepropuesta:
                                campo7 = tribunal.presidentepropuesta.persona.apellido1 + ' ' + tribunal.presidentepropuesta.persona.apellido2 + ' ' + tribunal.presidentepropuesta.persona.nombres
                            if tribunal.secretariopropuesta:
                                campo8 = tribunal.secretariopropuesta.persona.apellido1 + ' ' + tribunal.secretariopropuesta.persona.apellido2 + ' ' + tribunal.secretariopropuesta.persona.nombres
                            if tribunal.delegadopropuesta:
                                campo9 = tribunal.delegadopropuesta.persona.apellido1 + ' ' + tribunal.delegadopropuesta.persona.apellido2 + ' ' + tribunal.delegadopropuesta.persona.nombres

                        i += 1
                        ws.write(row_num, 0, i, font_style2)
                        ws.write(row_num, 1, campo1, font_style2)
                        ws.write(row_num, 2, campo2, font_style2)
                        ws.write(row_num, 3, campo3, font_style2)
                        ws.write(row_num, 4, campo4, font_style2)
                        ws.write(row_num, 5, campo6, date_format)
                        ws.write(row_num, 6, campo7, font_style2)
                        ws.write(row_num, 7, campo8, font_style2)
                        ws.write(row_num, 8, campo9, font_style2)
                        ws.write(row_num, 9, campo10, font_style2)
                        ws.write(row_num, 10, campo5, font_style2)
                        if listado.rubrica:
                            agregar = 10
                            listadomodelorubrica = listado.rubrica.modelorubricatitulacionposgrado_set.filter(status=True).order_by('orden')
                            detallecalificacion = listado.calificaciontitulacionposgrado_set.filter(status=True).order_by('tipojuradocalificador')
                            promediofinal = detallecalificacion.values_list('puntajerubricas').aggregate(promedio=Avg('puntajerubricas'))['promedio']
                            sumatotal = 0
                            for lmodelo in listadomodelorubrica:
                                agregar += 1
                                puntajemodelo = listado.puntajemodelorubrica(lmodelo)
                                sumatotal += puntajemodelo
                                ws.write(row_num, agregar, round(puntajemodelo,4), font_style2)
                            agregar += 1
                            ws.write(row_num, agregar, round(sumatotal,2), font_style2)
                            agregar += 1
                            ws.write(row_num, agregar, round(promediofinal,2), font_style2)
                        else:
                            ws.write(row_num, 11, '-', font_style2)
                            ws.write(row_num, 12, '-', font_style2)
                            ws.write(row_num, 13, '-', font_style2)
                            ws.write(row_num, 14, '-', font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'verprofesor':
                try:
                    data['title'] = u'Aprobar solicitudes tema titulación profesores'
                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    tema = TemaTitulacionPosgradoMatricula.objects.get(pk=int(request.GET['idtema']))
                    # bandera = tema.tematitulacionposgradoprofesor_set.filter(aprobado=True).count()
                    # data['bandera'] = bandera
                    search = None
                    mallaid = None
                    nivelmallaid = None
                    ids = None

                    solicitudes = tema.tematitulacionposgradoprofesor_set.filter(status=True).order_by('-id')
                    if 'id' in request.GET:
                        ids = int(request.GET['id'])
                        solicitudes = tema.tematitulacionposgradoprofesor_set.filter(status=True, id=request.GET['id']).order_by('-id')

                    if 's' in request.GET:
                        search = request.GET['s']
                        # s = search.split(" ")
                        solicitudes = tema.tematitulacionposgradoprofesor_set.filter(status=True, tematitulacionposgradomatricula__propuestatema__icontains=search).order_by('-id')

                    paging = MiPaginador(solicitudes, 25)
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
                    data['solicitudes'] = page.object_list
                    data['search'] = search if search else ""
                    data['tema'] = tema
                    data['idconfiguracion'] = request.GET['idconfiguracion']
                    return render(request, "adm_configuracionpropuesta/verprofesor.html", data)
                except Exception as ex:
                    pass

            elif action == 'instruccionformaldocente':
                try:
                    if 'id' in request.GET:
                        data['title'] = u'Instrucción formal del profesor'
                        data['personadocente'] =  profesor = Profesor.objects.get(pk=request.GET['id'],status =True)
                        template = get_template("adm_configuracionpropuesta/instruccionformaldocente.html")
                        return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'historial_aprobacion_tutor':
                try:
                    if 'id' in request.GET:
                        data['title'] = u'Historial de solicitud de tutor'
                        temaProfesor = TemaTitulacionPosgradoProfesor.objects.get(pk=request.GET['id'])
                        data['historial'] = historial = temaProfesor.solicitudtutortemahistorial_set.filter(status=True).order_by("-id")
                        template = get_template("adm_configuracionpropuesta/historial_aprobacion_tutor.html")
                        return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'verprofesorgrupo':
                try:
                    data['title'] = u'Aprobar solicitudes tema titulación profesores'
                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    tema = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=int(request.GET['idtema']))
                    bandera = tema.tematitulacionposgradoprofesor_set.filter(aprobado=True).count()
                    data['bandera'] = bandera
                    search = None
                    mallaid = None
                    nivelmallaid = None
                    ids = None

                    solicitudes = tema.tematitulacionposgradoprofesor_set.filter(status=True).order_by('-id')
                    if 'id' in request.GET:
                        ids = int(request.GET['id'])
                        solicitudes = tema.tematitulacionposgradoprofesor_set.filter(status=True, id=request.GET['id']).order_by('-id')

                    if 's' in request.GET:
                        search = request.GET['s']
                        # s = search.split(" ")
                        solicitudes = tema.tematitulacionposgradoprofesor_set.filter(status=True, tematitulacionposgradomatriculacabecera__propuestatema__icontains=search).order_by('-id')

                    paging = MiPaginador(solicitudes, 25)
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
                    data['solicitudes'] = page.object_list
                    data['search'] = search if search else ""
                    data['tema'] = tema
                    data['idconfiguracion'] = request.GET['idconfiguracion']
                    return render(request, "adm_configuracionpropuesta/verprofesorgrupo.html", data)
                except Exception as ex:
                    pass

            elif action == 'delete':
                try:
                    data['title'] = u'Eliminar configuración  y presentar propuesta maestrante'
                    data['configuracion'] = ConfiguracionTitulacionPosgrado.objects.get(pk=int(request.GET['id']), status=True)
                    return render(request, "adm_configuracionpropuesta/delete.html", data)
                except Exception as ex:
                    pass

            elif action == 'listar_temas':
                try:
                    # data['materia'] = materia = Materia.objects.get(pk=pm.materia.id)
                    data['temas'] = tema = TemaTitulacionPosgradoMatricula.objects.filter(pk=int(request.GET['id']),status=True)
                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    form = ArchivoPdfForm()
                    if not tema.first().es_examen_complaxivo():
                        data['form'] = form
                    else:
                        data['form'] = None
                    data['es_complexivo'] = tema.first().es_examen_complaxivo()
                    template = get_template("adm_configuracionpropuesta/listatema.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'listar_temas_profesor':
                try:
                    # data['materia'] = materia = Materia.objects.get(pk=pm.materia.id)
                    data['temas'] = tema = TemaTitulacionPosgradoProfesor.objects.filter(status = True,pk=int(request.GET['id']))
                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    form = ArchivoPdfForm()
                    data['form'] = form
                    template = get_template("adm_configuracionpropuesta/listatemaprofesor.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'aprobarprofesor':
                try:
                    data['title'] = u'Aprobar Profesor'
                    data['tema'] = TemaTitulacionPosgradoProfesor.objects.get(pk=request.GET['id'],status = True)
                    data['idtema'] = request.GET['idtema']
                    data['idconfiguracion'] = request.GET['idconfiguracion']
                    return render(request, "adm_configuracionpropuesta/aprobarprofesor.html", data)
                except Exception as ex:
                    pass

            elif action == 'aprobarprofesorgrupotit':
                try:
                    data['title'] = u'Aprobar Profesor'
                    data['tema'] = TemaTitulacionPosgradoProfesor.objects.get(pk=request.GET['id'],status = True)
                    data['idtema'] = request.GET['idtema']
                    data['idconfiguracion'] = request.GET['idconfiguracion']
                    return render(request, "adm_configuracionpropuesta/aprobarprofesorgrupo.html", data)
                except Exception as ex:
                    pass

            elif action == 'asignartribunal':
                try:
                    # puede_realizar_accion(request, 'sga.puede_editar_cupotematica')
                    data['title']=u"Asignar Tribunal"
                    # if 'c' in request.GET:
                    #     data['c'] = request.GET['c']
                    data['roles'] = CARGOS_JURADO_SUSTENTACION
                    tema = TemaTitulacionPosgradoMatricula.objects.get(pk=int(request.GET['id']))
                    if tema.tribunaltematitulacionposgradomatricula_set.filter(status=True):
                        grupo = tema.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]
                    else:
                        grupo = TribunalTemaTitulacionPosgradoMatricula(tematitulacionposgradomatricula=tema)
                        grupo.save(request)
                    data['grupo'] = grupo
                    form = ComplexivoTribunalCalificadorPosgradoForm(initial={'presidente': grupo.presidentepropuesta.id if grupo.presidentepropuesta else 0,
                                                                              'secretario': grupo.secretariopropuesta.id if grupo.secretariopropuesta else 0,
                                                                              'delegado': grupo.delegadopropuesta.id if grupo.delegadopropuesta else 0,
                                                                              'fecha': grupo.fechadefensa if grupo.fechadefensa else datetime.now().date(),
                                                                              'fechainiciocalificaciontrabajotitulacion': grupo.fechainiciocalificaciontrabajotitulacion if grupo.fechainiciocalificaciontrabajotitulacion else datetime.now().date(),
                                                                              'fechafincalificaciontrabajotitulacion': grupo.fechafincalificaciontrabajotitulacion if grupo.fechafincalificaciontrabajotitulacion else datetime.now().date(),
                                                                              'hora': str(grupo.horadefensa) if grupo.horadefensa else datetime.now().time().strftime('%H:%M'),
                                                                              'horafin': str(grupo.horafindefensa) if grupo.horafindefensa else datetime.now().time().strftime('%H:%M'),
                                                                              'lugar': grupo.lugardefensa if grupo.lugardefensa else ''})
                    if grupo.presidentepropuesta:
                        form.fields['presidente'].widget.attrs['descripcion'] = grupo.presidentepropuesta
                        form.fields['presidente'].widget.attrs['value'] = grupo.presidentepropuesta.id
                    else:
                        form.fields['presidente'].widget.attrs['descripcion'] = '----------------'
                        form.fields['presidente'].widget.attrs['value'] = 0
                    if grupo.secretariopropuesta:
                        form.fields['secretario'].widget.attrs['descripcion'] = grupo.secretariopropuesta
                        form.fields['secretario'].widget.attrs['value'] = grupo.secretariopropuesta.id
                    else:
                        form.fields['secretario'].widget.attrs['descripcion'] = '----------------'
                        form.fields['secretario'].widget.attrs['value'] = 0
                    if grupo.delegadopropuesta:
                        form.fields['delegado'].widget.attrs['descripcion'] = grupo.delegadopropuesta
                        form.fields['delegado'].widget.attrs['value'] = grupo.delegadopropuesta.id
                    else:
                        form.fields['delegado'].widget.attrs['descripcion'] = '----------------'
                        form.fields['delegado'].widget.attrs['value'] = 0
                    data['form'] = form
                    data['idconfiguracion'] = request.GET['idconfiguracion']
                    return render(request, "adm_configuracionpropuesta/asignartribunal.html", data)
                except Exception as ex:
                    pass

            elif action == 'buscarreemplazo':
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
                    excep = [val[0] for val in eval(request.GET['excep'])]
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_repr(),
                                                         'alias': x.flexbox_alias()  if hasattr(x,
                                                                                               'flexbox_alias') else []}
                                                        for x in query if x.id not in excep ]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", 'mensaje': u'Error al obtener los datos.'})

            elif action == 'cambiartribunal':
                try:
                    # puede_realizar_accion(request, 'sga.puede_editar_cupotematica')
                    data['title'] = u"Cambiar Tribunal"
                    # if 'c' in request.GET:
                    #     data['c'] = request.GET['c']
                    tema = TemaTitulacionPosgradoMatricula.objects.get(pk=int(request.GET['id']), status=True)
                    if tema.tribunaltematitulacionposgradomatricula_set.filter(status=True):
                        grupo = tema.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]
                    else:
                        grupo = TribunalTemaTitulacionPosgradoMatricula(tematitulacionposgradomatricula=tema)
                        grupo.save(request)
                    data['grupo'] = grupo

                    list_tribunal = []
                    if grupo.presidentepropuesta:
                        list_tribunal.append((grupo.presidentepropuesta.id, 'PRESIDENTE: ' + str(grupo.presidentepropuesta)))
                    if grupo.secretariopropuesta:
                        list_tribunal.append((grupo.secretariopropuesta.id, 'SECRETARIO: ' + str(grupo.secretariopropuesta)))
                    if grupo.delegadopropuesta:
                        list_tribunal.append((grupo.delegadopropuesta.id, 'VOCAL: ' + str(grupo.delegadopropuesta)))

                    data['list_tribunal'] = list_tribunal
                    data['fecha_actual'] = datetime.now().date()
                    data['idconfiguracion'] = request.GET['idconfiguracion']
                    data['action'] = 'cambiartribunal'
                    return render(request, "adm_configuracionpropuesta/cambiartribunal.html", data)
                except Exception as ex:
                    pass

            elif action == 'cambiartribunalpareja':
                try:
                    # puede_realizar_accion(request, 'sga.puede_editar_cupotematica')
                    data['title'] = u"Cambiar Tribunal"
                    # if 'c' in request.GET:
                    #     data['c'] = request.GET['c']
                    tema = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=int(request.GET['id']))
                    if tema.tribunaltematitulacionposgradomatricula_set.filter(status=True):
                        grupo = tema.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]
                    else:
                        grupo = TribunalTemaTitulacionPosgradoMatricula(tematitulacionposgradomatriculacabecera=tema)
                        grupo.save(request)
                    data['grupo'] = grupo

                    list_tribunal = []
                    if grupo.presidentepropuesta:
                        list_tribunal.append(
                            (grupo.presidentepropuesta.id, 'PRESIDENTE: ' + str(grupo.presidentepropuesta)))
                    if grupo.secretariopropuesta:
                        list_tribunal.append(
                            (grupo.secretariopropuesta.id, 'SECRETARIO: ' + str(grupo.secretariopropuesta)))
                    if grupo.delegadopropuesta:
                        list_tribunal.append((grupo.delegadopropuesta.id, 'VOCAL: ' + str(grupo.delegadopropuesta)))

                    data['list_tribunal'] = list_tribunal
                    data['fecha_actual'] = datetime.now().date()
                    data['idconfiguracion'] = request.GET['idconfiguracion']
                    data['action'] = 'cambiartribunalpareja'
                    data['idconfiguracion'] = request.GET['idconfiguracion']
                    return render(request, "adm_configuracionpropuesta/cambiartribunal.html", data)
                except Exception as ex:
                    pass

            elif action == 'asignartribunalpareja':
                try:
                    # puede_realizar_accion(request, 'sga.puede_editar_cupotematica')
                    data['title']=u"Asignar Tribunal"
                    # if 'c' in request.GET:
                    #     data['c'] = request.GET['c']
                    data['roles'] = CARGOS_JURADO_SUSTENTACION
                    tema = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=int(request.GET['id']))
                    data['primer_participante'] = primer_participante = tema.obtener_parejas()[0]
                    if tema.tribunaltematitulacionposgradomatricula_set.filter(status=True):
                        grupo = tema.tribunaltematitulacionposgradomatricula_set.filter(status=True)[0]
                    else:
                        grupo = TribunalTemaTitulacionPosgradoMatricula(tematitulacionposgradomatriculacabecera=tema)
                        grupo.save(request)
                    data['grupo'] = grupo
                    form = ComplexivoTribunalCalificadorPosgradoForm(initial={'presidente': grupo.presidentepropuesta.id if grupo.presidentepropuesta else 0,
                                                                              'secretario': grupo.secretariopropuesta.id if grupo.secretariopropuesta else 0,
                                                                              'delegado': grupo.delegadopropuesta.id if grupo.delegadopropuesta else 0,
                                                                              'fecha': grupo.fechadefensa if grupo.fechadefensa else datetime.now().date(),
                                                                              'fechainiciocalificaciontrabajotitulacion': grupo.fechainiciocalificaciontrabajotitulacion if grupo.fechainiciocalificaciontrabajotitulacion else datetime.now().date(),
                                                                              'fechafincalificaciontrabajotitulacion': grupo.fechafincalificaciontrabajotitulacion if grupo.fechafincalificaciontrabajotitulacion else datetime.now().date(),
                                                                              'hora': str(grupo.horadefensa) if grupo.horadefensa else datetime.now().time().strftime('%H:%M'),
                                                                              'horafin': str(grupo.horafindefensa) if grupo.horafindefensa else datetime.now().time().strftime('%H:%M'),
                                                                              'lugar': grupo.lugardefensa if grupo.lugardefensa else ''})
                    if grupo.presidentepropuesta:
                        form.fields['presidente'].widget.attrs['descripcion'] = grupo.presidentepropuesta
                        form.fields['presidente'].widget.attrs['value'] = grupo.presidentepropuesta.id
                    else:
                        form.fields['presidente'].widget.attrs['descripcion'] = '----------------'
                        form.fields['presidente'].widget.attrs['value'] = 0
                    if grupo.secretariopropuesta:
                        form.fields['secretario'].widget.attrs['descripcion'] = grupo.secretariopropuesta
                        form.fields['secretario'].widget.attrs['value'] = grupo.secretariopropuesta.id
                    else:
                        form.fields['secretario'].widget.attrs['descripcion'] = '----------------'
                        form.fields['secretario'].widget.attrs['value'] = 0
                    if grupo.delegadopropuesta:
                        form.fields['delegado'].widget.attrs['descripcion'] = grupo.delegadopropuesta
                        form.fields['delegado'].widget.attrs['value'] = grupo.delegadopropuesta.id
                    else:
                        form.fields['delegado'].widget.attrs['descripcion'] = '----------------'
                        form.fields['delegado'].widget.attrs['value'] = 0
                    data['form'] = form
                    data['idconfiguracion'] = request.GET['idconfiguracion']
                    return render(request, "adm_configuracionpropuesta/asignartribunalpareja.html", data)
                except Exception as ex:
                    pass

            elif action == 'editarnumeroacta':
                try:
                    data['title']=u"Editar número acta"
                    data['participante'] = tema = TemaTitulacionPosgradoMatricula.objects.get(pk=int(request.GET['id']))
                    data['graduado'] = graduado = Graduado.objects.get(inscripcion_id=tema.matricula.inscripcion, status=True)
                    form = GraduadoPosgradoForm(initial={'numeroactagrado': graduado.numeroactagrado})
                    data['form'] = form
                    return render(request, "adm_configuracionpropuesta/editarnumeroacta.html", data)
                except Exception as ex:
                    pass

            elif action == 'editarnumeroactacomplexivo':
                try:
                    data['title']=u"Editar número acta"
                    data['participante'] = tema = TemaTitulacionPosgradoMatricula.objects.get(pk=int(request.GET['id']))
                    data['graduado'] = graduado = Graduado.objects.get(inscripcion_id=tema.matricula.inscripcion, status=True)
                    form = GraduadoPosgradoForm(initial={'numeroactagrado': graduado.numeroactagrado})
                    data['form'] = form
                    return render(request, "adm_configuracionpropuesta/editarnumeroactacomplexivo.html", data)
                except Exception as ex:
                    pass

            elif action == 'cerraracta':
                try:
                    data['title'] = u'Cerrar acta y graduar estudiantes'
                    data['configuracion'] = ConfiguracionTitulacionPosgrado.objects.get(pk=request.GET['id'])
                    return render(request, "adm_configuracionpropuesta/cerrar_acta.html", data)
                except Exception as ex:
                    pass

            elif action == 'quitartutor1':
                try:
                    data['title'] = u'Quitar tutor'
                    temamatricula = TemaTitulacionPosgradoMatricula.objects.get(status = True,pk=int(request.GET['idtema']))
                    data['temamatricula'] = temamatricula
                    data['idconfiguracion'] = request.GET['idconfiguracion']
                    return render(request, "adm_configuracionpropuesta/quitartutor1.html", data)
                except Exception as ex:
                    pass

            elif action == 'quitartutorGrupo':
                try:
                    data['title'] = u'Quitar tutor de tesis'
                    temamatricula = TemaTitulacionPosgradoMatriculaCabecera.objects.get(status = True,pk=int(request.GET['idtema']))
                    data['temamatricula'] = temamatricula
                    data['idconfiguracion'] = request.GET['idconfiguracion']
                    return render(request, "adm_configuracionpropuesta/quitartutorgrupo.html", data)
                except Exception as ex:
                    pass

            elif action == 'quitartutor2':
                try:
                    data['title'] = u'Quitar tutor de tesis'
                    temamatricula = TemaTitulacionPosgradoMatricula.objects.get(status = True,pk=int(request.GET['idtema']))
                    data['temamatricula'] = temamatricula
                    data['idconfiguracion'] = request.GET['idconfiguracion']
                    return render(request, "adm_configuracionpropuesta/quitartutor2.html", data)
                except Exception as ex:
                    pass

            elif action == 'quitartutorgruposol':
                try:
                    data['title'] = u'Quitar tutor de tesis'
                    temamatricula = TemaTitulacionPosgradoMatriculaCabecera.objects.get(status = True,pk=int(request.GET['idtema']))
                    data['temamatricula'] = temamatricula
                    data['idconfiguracion'] = request.GET['idconfiguracion']
                    return render(request, "adm_configuracionpropuesta/quitartutorgruposol.html", data)
                except Exception as ex:
                    pass

            elif action == 'detallecalificaciontribunal':
                try:
                    data['participante'] = participante = TemaTitulacionPosgradoMatricula.objects.get(pk=request.GET['id'])
                    data['detallecalificacion'] = detallecalificacion = participante.calificaciontitulacionposgrado_set.filter(status=True).order_by('tipojuradocalificador')
                    data['promediopuntajetrabajointegral'] = detallecalificacion.values_list('puntajetrabajointegral').aggregate(promedio=Avg('puntajetrabajointegral'))['promedio']
                    data['promediodefensaoral'] = detallecalificacion.values_list('puntajedefensaoral').aggregate(promedio=Avg('puntajedefensaoral'))['promedio']
                    data['promediofinal'] = detallecalificacion.values_list('puntajerubricas').aggregate(promedio=Avg('puntajerubricas'))['promedio']
                    if participante.rubrica:
                        data['listadomodelorubrica'] = participante.rubrica.modelorubricatitulacionposgrado_set.filter(status=True).order_by('orden')
                        template = get_template("adm_configuracionpropuesta/detallecalificaciontribunalmodrubrica.html")
                        json_content = template.render(data)
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"No existen notas de tribunal calificador."})
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'seguimiento_maestrante':
                try:
                    es_pareja = int(request.GET['pareja'])
                    id = request.GET['id']
                    if es_pareja == 1:
                        tema = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=id)
                    else:
                        tema = TemaTitulacionPosgradoMatricula.objects.get(pk=id)
                    configuracion = tema.convocatoria

                    bandera = False
                    hoy = datetime.now().date()
                    if hoy >= configuracion.fechainiciotutoria and hoy <= configuracion.fechafintutoria:
                        bandera = True
                    data['bandera'] = bandera

                    data['grupo'] = tema
                    data['es_pareja'] = es_pareja
                    data['cronograma'] = configuracion
                    data['detalles'] = tema.tutoriastematitulacionposgradoprofesor_set.filter(status=True).order_by( 'id')
                    data['resumen_tutoria'] =tema.tutoriastematitulacionposgradoprofesor_set.values('programaetapatutoria__etapatutoria__id',).filter(status=True).annotate(cantidad =Count('id'))
                    if variable_valor('HABILITAR_TUTORIA_POR_MECANISMO'):
                        etapas =configuracion.obtener_etapas_de_tutorias(tema.mecanismotitulacionposgrado_id)
                    else:
                        etapas =etapas =configuracion.obtener_etapas_de_tutorias_antiguo()
                    data['configuracion_programa_etapa'] = etapas

                    return render(request, "adm_configuracionpropuesta/seguimiento_maestrante.html", data)

                except Exception as ex:
                    pass

            elif action == 'detalletutoriaposgrado':
                try:
                    data['tutoria'] = TutoriasTemaTitulacionPosgradoProfesor.objects.get(pk=request.GET['id'])
                    template = get_template("pro_tutoriaposgrado/modal/detalletutoriaposgrado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'grupotitulacionpostgrado':
                try:
                    data['title'] = u'Grupos para la toma de examen de cáracter complexivo'

                    search = None
                    search = request.GET.get('s', '')
                    url_vars = ""
                    filtros = Q(status=True)

                    if search:
                        data['search'] = search
                        url_vars += "&s={}".format(search)
                        filtros = filtros & (Q(tutor__persona__apellido1__icontains=search) | Q(tutor__persona__apellido2__icontains=search) | Q(tutor__persona__nombres__icontains=search))

                    data["url_vars"] = url_vars
                    grupos =GrupoTitulacionPostgrado.objects.filter(filtros,configuracion_id=request.GET['id'] )
                    paging = MiPaginador(grupos, 20)
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
                    data['grupos'] = page.object_list
                    data['id_configuracion'] = ConfiguracionTitulacionPosgrado.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_configuracionpropuesta/grupotitulacionpostgrado.html", data)
                except Exception as ex:
                    pass

            elif action == 'calificar_ensayos_posgrado':
                try:
                    data['title'] = u'Revisión de Ensayos'
                    data['idconfiguracion'] = request.GET['idconfiguracion']
                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk=int(request.GET['idconfiguracion']),status=True)
                    periodo = configuracion.periodo
                    carrera = configuracion.carrera
                    if not periodo.visible:
                        return HttpResponseRedirect("/?info=Periodo Inactivo.")
                    search = None
                    mallaid = None
                    nivelmallaid = None
                    ids = None
                    temas  = configuracion.tematitulacionposgradomatricula_set.filter(status=True,cabeceratitulacionposgrado__isnull=True , mecanismotitulacionposgrado__id__in=[15,21]).order_by('-id')
                    if 'id' in request.GET:
                        ids = int(request.GET['id'])
                        temas = temas.filter(id=int(request.GET['id']))

                    if 's' in request.GET:
                        search = request.GET['s']
                        if search:
                            temas = temas.filter(Q(propuestatema__icontains=search) |
                                                 Q(matricula__inscripcion__persona__nombres__icontains=search) |
                                                 Q(matricula__inscripcion__persona__apellido1__icontains=search) |
                                                 Q(matricula__inscripcion__persona__apellido2__icontains=search) |
                                                 Q(matricula__inscripcion__persona__cedula__icontains=search))

                    paging = MiPaginador(temas, 25)
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
                    data['temas'] = page.object_list
                    data['search'] = search if search else ""
                    data['periodo'] = periodo
                    data['configuracion'] = configuracion

                    # paginador en pareja
                    searchPareja = None
                    temapareja = configuracion.tematitulacionposgradomatriculacabecera_set.filter(status=True,mecanismotitulacionposgrado__id__in=[15,21])
                    if 'idPareja' in request.GET:
                        idsPareja = int(request.GET['idPareja'])
                        temapareja = temapareja.filter(id=int(request.GET['idPareja']))

                    if 'sPareja' in request.GET:
                        searchPareja = request.GET['sPareja']
                        if searchPareja:
                            cabecera = configuracion.tematitulacionposgradomatricula_set.values_list(
                                'cabeceratitulacionposgrado').filter(status=True,
                                                                     cabeceratitulacionposgrado__isnull=False,
                                                                     matricula__inscripcion__persona__cedula__icontains=searchPareja).distinct()
                            temapareja = temapareja.filter(Q(propuestatema__icontains=searchPareja) |
                                                           Q(pk__in=cabecera)
                                                           )

                    paging2 = MiPaginador(temapareja, 25)
                    p2 = 1
                    try:
                        paginasesion2 = 1
                        if 'paginador2' in request.session:
                            paginasesion2 = int(request.session['paginador2'])
                        if 'page2' in request.GET:
                            p2 = int(request.GET['page2'])
                        else:
                            p2 = paginasesion2
                        try:
                            page2 = paging2.page(p2)
                        except:
                            p2 = 1
                        page2 = paging2.page(p2)
                    except:
                        page2 = paging2.page(p2)
                    request.session['paginador2'] = p2
                    data['paging2'] = paging2
                    data['rangospaging2'] = paging2.rangos_paginado(p2)
                    data['page2'] = page2
                    data['searchPareja'] = searchPareja if searchPareja else ""
                    data['temaspareja'] = page2.object_list
                    return render(request, "adm_configuracionpropuesta/propuestasensayocomplexivo.html", data)
                except Exception as ex:
                    pass

            elif action == 'configuraciontitulacionpostgrado':
                try:
                    data['title'] = u'Configuración Titulación Posgrado'

                    search = None
                    search = request.GET.get('s', '')
                    url_vars = ""
                    filtros = Q(status=True)
                    if search:
                        data['search'] = search
                        url_vars += "&s={}".format(search)
                        filtros = filtros & (Q(mecanismotitulacionposgrado__nombre__icontains=search)|Q(rubricatitulacionposgrado__nombre__icontains=search))

                    data["url_vars"] = url_vars
                    detalle=DetalleTitulacionPosgrado.objects.filter(filtros, configuracion=request.GET['id'])
                    paging = MiPaginador(detalle, 20)
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
                    data['DetalleTitulacionPosgrado'] = page.object_list
                    data['configuracionTitulacion'] =  ConfiguracionTitulacionPosgrado.objects.get(id=int(request.GET['id']))

                    return render(request, "adm_configuracionpropuesta/configuraciontitulacionpostgrado.html", data)
                except Exception as ex:
                    pass

            elif action  == 'modeloevaluativoposgrado':
                try:
                    data['title'] = u'Modelos evaluativos posgrado'
                    search = None
                    search = request.GET.get('s', '')
                    url_vars = ""
                    filtros = Q(status=True)
                    if search:
                        data['search'] = search
                        url_vars += "&s={}".format(search)
                        filtros = filtros & (Q(nombre__icontains=search))

                    data["url_vars"] = url_vars
                    modeloevaluativo =ModeloEvaluativoPosgrado.objects.filter(filtros)
                    paging = MiPaginador(modeloevaluativo, 25)
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
                    data['modelos'] = page.object_list
                    return render(request, "adm_configuracionpropuesta/modeloevaluativoposgrado.html", data)
                except Exception as ex:
                    pass

            elif action  == 'etapasTutoriasPosgrado':
                try:
                    data['title'] = u'Etapas tutorías posgrado'
                    search = None
                    search = request.GET.get('s', '')
                    url_vars = ""
                    filtros = Q(status=True)
                    if search:
                        data['search'] = search
                        url_vars += "&s={}".format(search)
                        filtros = filtros & (Q(descripcion__icontains=search))

                    data["url_vars"] = url_vars
                    etapas_tutorias =EtapaTemaTitulacionPosgrado.objects.filter(filtros).order_by('id')

                    paging = MiPaginador(etapas_tutorias, 25)
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
                    data['etapas_tutorias'] = page.object_list
                    return render(request, "adm_configuracionpropuesta/etapastutoriasposgrado.html", data)
                except Exception as ex:
                    pass

            elif action == 'editmodeloevaluativoposgrado':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_modelos_evaluativos')
                    data['title'] = u'Editar modelo evaluativo posgrado'
                    data['modelo'] = modelo = ModeloEvaluativoPosgrado.objects.get(pk=request.GET['id'], status=True)
                    form = ModeloEvaluativoPosgradoForm(initial={'nombre': modelo.nombre,
                                                                                'notaaprobar': modelo.notaaprobar})
                    data['form'] = form
                    template = get_template("adm_configuracionpropuesta/modal/formModeloevaluativoposgrado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'editetapatutoriaposgrado':
                try:
                    data['id'] = id =  request.GET['id']
                    data['filtro'] = filtro = EtapaTemaTitulacionPosgrado.objects.get(pk=id)
                    form = EtapaTutoriaTitulacionPosgradoForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("adm_configuracionpropuesta/modal/formetapatutoriaposgrado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action  == 'configuracionprogramaetapatutoria':
                try:
                    configuracion = ConfiguracionTitulacionPosgrado.objects.get(pk = int(request.GET["id"]))
                    data['title'] = u'Configuración de etapas de tutorias'
                    data['eConfiguracionTitulacionPosgrado'] = configuracion

                    search = None
                    search = request.GET.get('s', '')
                    url_vars = ""
                    filtros = Q(status=True)
                    if search:
                        data['search'] = search
                        url_vars += "&s={}".format(search)
                        filtros = filtros & (Q(etapatutoria__descripcion__icontains=search))

                    data["url_vars"] = url_vars
                    programa_etapas_tutorias =ProgramaEtapaTutoriaPosgrado.objects.filter(filtros).order_by('orden').filter(mecanismotitulacionposgrado_id =request.GET['mecanismo_id'],convocatoria__id = request.GET['id'])

                    paging = MiPaginador(programa_etapas_tutorias, 25)
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
                    data['configuracion'] = configuracion
                    data['search'] = search if search else ""
                    data['programa_etapas_tutorias'] = page.object_list
                    data['eMecanismoTitulacionPosgrado'] = MecanismoTitulacionPosgrado.objects.get(pk=request.GET['mecanismo_id'])
                    return render(request, "adm_configuracionpropuesta/programaetapastutoriasposgrado.html", data)
                except Exception as ex:
                    pass

            elif action  == 'encuestasconvocatoria':
                try:
                    request.session['viewencuestatitulacionposgrado'] = 1
                    ePeriodo = Periodo.objects.get(pk=int(request.GET["id"]))
                    eEncuestaTitulacionPosgrado =  EncuestaTitulacionPosgrado .objects.filter(status=True,periodo =ePeriodo)
                    data['eEncuestaTitulacionPosgrados'] = eEncuestaTitulacionPosgrado
                    data['title'] = u'Encuestas de sede de graduación'
                    return render(request, "adm_configuracionpropuesta/encuestas/view.html", data)
                except Exception as ex:
                    pass

            elif action  == 'tutoriasposgrado':
                try:
                    url_vars = '&action=tutoriasposgrado'
                    filtro = Q(status=True)
                    search = None
                    search = request.GET.get('searchinput', '')

                    if search:
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro &= (Q(persona__nombres__icontains=search) |
                                       Q(persona__apellido1__icontains=search) |
                                       Q(persona__apellido2__icontains=search) |
                                       Q(persona__cedula__icontains=search))
                        else:
                            filtro &= ((Q(persona__nombres__icontains=ss[0]) & Q(persona__nombres__icontains=ss[1])) |
                                       (Q(persona__apellido1__icontains=ss[0]) & Q( persona__apellido2__icontains=ss[1])) |(Q(persona__cedula__icontains=ss[0]) & Q(persona__cedula__icontains=ss[1])))

                    profesor_individual_id = TemaTitulacionPosgradoMatricula.objects.filter(cabeceratitulacionposgrado__isnull=True,status=True).values_list('tutor_id',flat=True).distinct()
                    profesor_pareja_id = TemaTitulacionPosgradoMatriculaCabecera.objects.filter(status=True).values_list('tutor_id',flat=True).distinct()
                    profesor_id  = list(profesor_individual_id.union(profesor_pareja_id))

                    eProfesores = Profesor.objects.filter(id__in=profesor_id).filter(filtro)

                    def temas_como_tutor_individual(profesor_id):
                        eTemaTitulacionPosgradoMatricula = TemaTitulacionPosgradoMatricula.objects.filter(status=True, tutor_id=profesor_id, cabeceratitulacionposgrado__isnull=True).values_list('pk',flat=True)
                        return eTemaTitulacionPosgradoMatricula

                    def temas_como_tutor_pareja(profesor_id):
                        eTemaTitulacionPosgradoMatriculaCabecera = TemaTitulacionPosgradoMatriculaCabecera.objects.filter(status=True, tutor_id=profesor_id).values_list('pk',flat=True)
                        return eTemaTitulacionPosgradoMatriculaCabecera

                    def cantidad_de_temas_como_tutor_individual_culminadas(profesor_id):
                        tematitulacionposgradomatricula_ids= temas_como_tutor_individual(profesor_id)
                        ACEPTADO = 2
                        eRevisionTutoriasTemaTitulacionPosgradoProfesor = RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.filter(estado = ACEPTADO,porcentajeurkund__isnull=False,
                                                                    tematitulacionposgradomatricula_id__in=tematitulacionposgradomatricula_ids,status=True,tematitulacionposgradomatriculacabecera__isnull=True).values_list('tematitulacionposgradomatricula_id',flat=True).distinct().order_by('tematitulacionposgradomatricula_id')
                        return eRevisionTutoriasTemaTitulacionPosgradoProfesor.count()

                    def cantidad_de_temas_como_tutor_pareja_culminadas(profesor_id):
                        tematitulacionposgradomatriculacabecera_ids = temas_como_tutor_pareja(profesor_id)
                        ACEPTADO = 2
                        eRevisionTutoriasTemaTitulacionPosgradoProfesor = RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.filter(estado = ACEPTADO,porcentajeurkund__isnull=False,
                        tematitulacionposgradomatriculacabecera_id__in =tematitulacionposgradomatriculacabecera_ids,status=True,tematitulacionposgradomatricula__isnull=True).values_list('tematitulacionposgradomatriculacabecera_id',flat=True).distinct().order_by('tematitulacionposgradomatriculacabecera_id')
                        return eRevisionTutoriasTemaTitulacionPosgradoProfesor.count()

                    def total_tutorias(profesor_id):
                            return temas_como_tutor_individual(profesor_id).count() + temas_como_tutor_pareja(profesor_id).count()

                    def total_tutorias_culminadas(profesor_id):
                            return cantidad_de_temas_como_tutor_individual_culminadas(profesor_id) + cantidad_de_temas_como_tutor_pareja_culminadas(profesor_id)

                    def total_tutorias_no_culminadas(profesor_id):
                        return (total_tutorias(profesor_id) - total_tutorias_culminadas(profesor_id))


                    def obtener_datos(eProfesor):
                        return {
                            'eProfesor': eProfesor,
                            'cantidad_temas_individual': temas_como_tutor_individual(eProfesor.pk).count(),
                            'cantidad_temas_en_pareja': temas_como_tutor_pareja(eProfesor.pk).count(),
                            'total_tutorias': total_tutorias(eProfesor.pk),
                            'cantidad_temas_individual_culminadas': cantidad_de_temas_como_tutor_individual_culminadas(eProfesor.pk) ,
                            'cantidad_temas_en_pareja_culminadas': cantidad_de_temas_como_tutor_pareja_culminadas(eProfesor.pk),
                            'total_tutorias_culminadas': total_tutorias_culminadas(eProfesor.pk),
                            'total_tutorias_no_culminadas': total_tutorias_no_culminadas(eProfesor.pk)

                        }


                    listado = list(map(lambda eProfesor: obtener_datos(eProfesor),eProfesores))
                    if 'dowloadexcel' in request.GET:
                        __author__ = 'Unemi'
                        style0 = easyxf('font: name Times New Roman, color-index blue, bold off',num_format_str='#,##0.00')
                        style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                        style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                        title = easyxf( 'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                        style1 = easyxf(num_format_str='D-MMM-YY')
                        fuentecabecera = easyxf( 'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                        font_style = XFStyle()
                        font_style.font.bold = True
                        font_style2 = XFStyle()
                        font_style2.font.bold = False
                        wb = Workbook(encoding='utf-8')
                        ws = wb.add_sheet('reporte_tutorias')
                        ws.write_merge(0, 0, 0, 4, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                        response = HttpResponse(content_type="application/ms-excel")
                        response['Content-Disposition'] = 'attachment; filename= reporte_tutorias' + random.randint( 1, 10000).__str__() + '.xls'
                        columns = [
                            (u"PROFESOR", 10000),
                            (u"CEDULA", 4000),
                            (u"CANT TUTORIAS", 4000),
                            (u"CANT TUTORIAS CULMINADAS", 4000),
                            (u"CANT TUTORIAS NO CULMINADAS", 4000),
                        ]

                        row_num = 1
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                            ws.col(col_num).width = columns[col_num][1]
                        date_format = xlwt.XFStyle()
                        date_format.num_format_str = 'yyyy-mm-dd'
                        date_formatreverse = xlwt.XFStyle()
                        date_formatreverse.num_format_str = 'dd/mm/yyyy'
                        row_num = 2
                        for item in listado:
                            ws.write(row_num, 0, item['eProfesor'].persona.nombre_completo_minus().__str__(), font_style2)
                            ws.write(row_num, 1, item['eProfesor'].persona.cedula.__str__(), font_style2)
                            ws.write(row_num, 2, item['total_tutorias'], font_style2)
                            ws.write(row_num, 3, item['total_tutorias_culminadas'], font_style2)
                            ws.write(row_num, 4, item['total_tutorias_no_culminadas'], font_style2)
                            row_num += 1

                        wb.save(response)
                        return response

                    paging = MiPaginador(listado, 25)
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
                    data['searchinput'] = search if search else ""
                    data['url_vars'] = url_vars
                    data['total'] = len(listado)

                    return render(request, "adm_configuracionpropuesta/tutoriasposgrado/view.html", data)
                except Exception as ex:
                    pass


            elif action  == 'graduacionposgrado':
                try:
                    url_vars = '&action=graduacionposgrado'
                    data['menu_principal'] = 0
                    filtro = Q(status=True)
                    eEncuestaTitulacionPosgrado = EncuestaTitulacionPosgrado.objects.filter(filtro).order_by('-id')
                    data['eEncuestaTitulacionPosgrados'] = eEncuestaTitulacionPosgrado
                    return render(request, "adm_configuracionpropuesta/encuestas/graduacion/view.html", data)
                except Exception as ex:
                    pass

            elif action == 'viewpropuestasporprofesor':
                try:
                    pk = int(request.GET.get('id', '0'))
                    if pk == 0:
                        raise NameError("Parametro no encontrado")

                    eProfesor = Profesor.objects.get(pk=pk)

                    def temas_como_tutor_individual(profesor_id):
                        eTemaTitulacionPosgradoMatricula = TemaTitulacionPosgradoMatricula.objects.filter(status=True, tutor_id=profesor_id, cabeceratitulacionposgrado__isnull=True)
                        return eTemaTitulacionPosgradoMatricula

                    def temas_como_tutor_pareja(profesor_id):
                        eTemaTitulacionPosgradoMatriculaCabecera = TemaTitulacionPosgradoMatriculaCabecera.objects.filter(status=True, tutor_id=profesor_id)
                        return eTemaTitulacionPosgradoMatriculaCabecera

                    temas_individuales = temas_como_tutor_individual(eProfesor.id)
                    temas_pareja = temas_como_tutor_pareja(eProfesor.id)

                    data['eProfesor'] = eProfesor
                    data['temas_individuales'] = temas_individuales
                    data['temas_pareja'] = temas_pareja

                    template = get_template('adm_configuracionpropuesta/tutoriasposgrado/propuestatitulacion/view.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": f"{ex.__str__()}"})

            elif action == 'configurarencuestatitulacion':
                try:
                    request.session['view_encuesta_configuracion'] = 'datos_generales'
                    data['title'] = u'Configurar encuesta'
                    pk = int(request.GET.get('id'))
                    eEncuestaTitulacionPosgrado = EncuestaTitulacionPosgrado.objects.get(pk=pk)
                    data['eEncuestaTitulacionPosgrado'] = eEncuestaTitulacionPosgrado
                    return render(request, "adm_configuracionpropuesta/encuestas/configuracion/view.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/adm_configuracionpropuesta?action=encuestasconvocatoria&id={eEncuestaTitulacionPosgrado.periodo_id}&info=%s" % ex.__str__())


            elif action == 'configurarencuesta_sedes':
                try:
                    request.session['view_encuesta_configuracion'] = 'sedes'
                    data['title'] = u'Configurar encuesta Sedes'
                    pk = int(request.GET.get('id'))
                    eEncuestaTitulacionPosgrado = EncuestaTitulacionPosgrado.objects.get(pk=pk)
                    data['eEncuestaTitulacionPosgrado'] = eEncuestaTitulacionPosgrado
                    return render(request, "adm_configuracionpropuesta/encuestas/configuracion/encuesta_sede.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(
                        f"/adm_configuracionpropuesta?action=encuestasconvocatoria&id={eEncuestaTitulacionPosgrado.periodo_id}&info=%s" % ex.__str__())


            elif action == 'add_sede_titulacion':
                try:
                    pk = request.GET.get('id', None)
                    eEncuestaTitulacionPosgrado = EncuestaTitulacionPosgrado.objects.get(pk=pk)
                    data['id'] = eEncuestaTitulacionPosgrado.pk
                    form =SeleccionSedeForm()
                    data['form2'] = form
                    template = get_template('adm_configuracionpropuesta/encuestas/configuracion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editarjornadagraduacion':
                try:
                    pk = request.GET.get('id', None)
                    eInscripcionEncuestaTitulacionPosgrado = InscripcionEncuestaTitulacionPosgrado.objects.get(pk=pk)
                    form =SeleleccionSedeJornadaForm()
                    RespuestaSedeInscripcionEncuestaPk = 0
                    sedes = SedeEncuestaTitulacionPosgrado.objects.filter(status=True,encuestatitulacionposgrado =eInscripcionEncuestaTitulacionPosgrado.encuestatitulacionposgrado)
                    data['sedes'] = sedes
                    eRespuestaSedeInscripcionEncuesta = RespuestaSedeInscripcionEncuesta.objects.filter(status=True, inscripcionencuestatitulacionposgrado=eInscripcionEncuestaTitulacionPosgrado)
                    form.cargar_sedes(eInscripcionEncuestaTitulacionPosgrado.encuestatitulacionposgrado)
                    if eRespuestaSedeInscripcionEncuesta.exists():
                        RespuestaSedeInscripcionEncuestaPk =eRespuestaSedeInscripcionEncuesta.first().pk
                        form.inicializar_campos_sede(eRespuestaSedeInscripcionEncuesta.first().jornadasedeencuestatitulacionposgrado.sedeencuestatitulacionposgrado)
                        form.inicializar_campos_jornada(eRespuestaSedeInscripcionEncuesta.first().jornadasedeencuestatitulacionposgrado)



                    data['RespuestaSedeInscripcionEncuestaPk'] = RespuestaSedeInscripcionEncuestaPk
                    data['id'] = pk
                    data['form2'] = form
                    template = get_template('adm_configuracionpropuesta/encuestas/configuracion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edit_inicio_fin_encuesta':
                try:
                    pk = request.GET.get('id', None)
                    eEncuestaTitulacionPosgrado = EncuestaTitulacionPosgrado.objects.get(pk=pk)
                    data['id'] = eEncuestaTitulacionPosgrado.pk
                    form = CronogramaEncuestaForm(initial=model_to_dict(eEncuestaTitulacionPosgrado))
                    data['form2'] = form
                    template = get_template('adm_configuracionpropuesta/encuestas/configuracion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addhorarioporsede':
                try:
                    pk = int(request.GET['id'])
                    eSedeEncuestaTitulacionPosgrado = SedeEncuestaTitulacionPosgrado.objects.get(pk=pk)
                    form = JornadaEncuestaSedeForm()
                    data['id']= eSedeEncuestaTitulacionPosgrado.pk
                    data['form2']= form
                    template = get_template('adm_configuracionpropuesta/encuestas/configuracion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editjornada':
                try:
                    pk = int(request.GET['id'])
                    eJornadaSedeEncuestaTitulacionPosgrado = JornadaSedeEncuestaTitulacionPosgrado.objects.get(pk=pk)
                    form = JornadaEncuestaSedeForm(initial=model_to_dict(eJornadaSedeEncuestaTitulacionPosgrado))
                    data['id']= eJornadaSedeEncuestaTitulacionPosgrado.pk
                    data['form2']= form
                    template = get_template('adm_configuracionpropuesta/encuestas/configuracion/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            elif action == 'listprovincia':
                try:
                    pais_id = int(request.GET.get('pais_id'))

                    querybase = Provincia.objects.filter(status=True, pais_id =  pais_id).order_by('id')

                    if 'q' in request.GET:
                        q = request.GET['q'].upper().strip()
                        if q != 'UNDEFINED':
                            querybase = querybase.filter((Q(nombre__icontains=q) | Q(codigo__icontains=q))).distinct()[:30]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {}".format(x.codigo, x.nombre)} for x in querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'listjornadas':
                try:
                    id_sede = int(request.GET.get('id_sede'))

                    querybase = JornadaSedeEncuestaTitulacionPosgrado.objects.filter(status=True, sedeencuestatitulacionposgrado_id =  id_sede).order_by('id')

                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {}".format(x.pk, x)} for x in querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass


            elif action == 'listcanton':
                try:
                    provincia_id = int(request.GET.get('provincia_id'))
                    querybase = Canton.objects.filter(status=True, provincia_id =provincia_id).order_by('id')

                    if 'q' in request.GET:
                        q = request.GET['q'].upper().strip()
                        if q != 'UNDEFINED':
                            querybase = querybase.filter((Q(nombre__icontains=q) | Q(codigo__icontains=q))).distinct()[
                                        :30]
                    data = {"result": "ok",
                            "results": [{"id": x.id, "name": "{} - {}".format(x.codigo, x.nombre)} for x in querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'configurarencuesta_poblacion':
                try:
                    request.session['view_encuesta_configuracion'] = 'poblacion'
                    data['title'] = u'Configurar encuesta Población'
                    pk = int(request.GET.get('id'))
                    eEncuestaTitulacionPosgrado = EncuestaTitulacionPosgrado.objects.get(pk=pk)
                    data['eEncuestaTitulacionPosgrado'] = eEncuestaTitulacionPosgrado
                    return render(request, "adm_configuracionpropuesta/encuestas/configuracion/encuesta_poblacion.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(
                        f"/adm_configuracionpropuesta?action=encuestasconvocatoria&id={eEncuestaTitulacionPosgrado.periodo_id}&info=%s" % ex.__str__())

            elif action == 'configurarencuesta_resultados':
                try:
                    pk = int(request.GET.get('id'))
                    request.session['view_encuesta_configuracion'] = 'resultados'
                    data['title'] = u'Configurar encuesta Población'
                    eEncuestaTitulacionPosgrado = EncuestaTitulacionPosgrado.objects.get(pk=pk)
                    url_vars = f'&action=configurarencuesta_resultados&id={eEncuestaTitulacionPosgrado.pk}'
                    filtro = Q(status=True)
                    search = None
                    search = request.GET.get('searchinput', '')
                    sede_id = int(request.GET.get('sede_id', '0') or '0')



                    if search:
                        url_vars += "&searchinput={}".format(search)
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro &= (Q(inscripcion__persona__nombres__icontains=search) |
                                       Q(inscripcion__persona__apellido1__icontains=search) |
                                       Q(inscripcion__persona__apellido2__icontains=search) |
                                       Q(inscripcion__persona__cedula__icontains=search))
                        else:
                            filtro &= ((Q(inscripcion__persona__nombres__icontains=ss[0]) & Q(inscripcion__persona__nombres__icontains=ss[1])) |
                                       (Q(inscripcion__persona__apellido1__icontains=ss[0]) & Q(
                                           inscripcion__persona__apellido2__icontains=ss[1])) | (
                                                   Q(inscripcion__persona__cedula__icontains=ss[0]) & Q(
                                               inscripcion__persona__cedula__icontains=ss[1])))


                    eInscripcionEncuestaTitulacionPosgrado = eEncuestaTitulacionPosgrado.get_encuestados().filter(filtro)
                    if sede_id != 0:
                        url_vars += "&sede_id={}".format(sede_id)
                        inscripcionencuestatitulacionposgrado_id = RespuestaSedeInscripcionEncuesta.objects.values_list('inscripcionencuestatitulacionposgrado_id',flat=True).filter(status=True,jornadasedeencuestatitulacionposgrado__sedeencuestatitulacionposgrado_id =sede_id)
                        eInscripcionEncuestaTitulacionPosgrado = eEncuestaTitulacionPosgrado.get_encuestados().filter(id__in=inscripcionencuestatitulacionposgrado_id)
                    total = eInscripcionEncuestaTitulacionPosgrado.count()
                    paging = MiPaginador(eInscripcionEncuestaTitulacionPosgrado, 25)
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
                    data['eInscripcionEncuestaTitulacionPosgrado'] = page.object_list
                    data['eEncuestaTitulacionPosgrado'] = eEncuestaTitulacionPosgrado
                    data['url_vars'] = url_vars
                    data['total'] = total
                    return render(request, "adm_configuracionpropuesta/encuestas/configuracion/encuesta_resultados.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/adm_configuracionpropuesta?action=encuestasconvocatoria&id={eEncuestaTitulacionPosgrado.periodo_id}&info=%s" % ex.__str__())


            elif action == 'verificar_asistencia_sede_graduacion':
                try:
                    request.session['view_encuesta_configuracion'] = 'resultados'
                    data['title'] = u'Registrar asistencias'
                    pk =  int(request.GET.get('id', '0') or '0')
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    eInscripcionEncuestaTitulacionPosgrado = InscripcionEncuestaTitulacionPosgrado.objects.get(pk=pk)
                    data['eInscripcionEncuestaTitulacionPosgrado'] = eInscripcionEncuestaTitulacionPosgrado
                    data['eEncuestaTitulacionPosgrado'] = eInscripcionEncuestaTitulacionPosgrado.encuestatitulacionposgrado
                    return render(request, "adm_configuracionpropuesta/encuestas/asistencia/view.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/adm_configuracionpropuesta?action=encuestasconvocatoria&id={eInscripcionEncuestaTitulacionPosgrado.encuestatitulacionposgrado.periodo_id}&info=%s" % ex.__str__())

            elif action == 'addencuestasede':
                try:
                    data['pk'] = pk = request.GET.get('id', 0)
                    template = get_template('adm_configuracionpropuesta/encuestas/modal/formmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action  == 'configuraciondocumentossubidamaestrantetitulacion':
                try:
                    eConfiguracionTitulacionPosgrado = ConfiguracionTitulacionPosgrado.objects.get(pk = int(request.GET["id"]))
                    eMecanismoTitulacionPosgrado = MecanismoTitulacionPosgrado.objects.get(pk = int(request.GET["mecanismo_id"]))
                    data['title'] = u'Configuración de documentos a subir'
                    search = None
                    search = request.GET.get('s', '')
                    url_vars = ""
                    filtros = Q(status=True)

                    data["url_vars"] = url_vars
                    eMecanismoDocumentosTutoriaPosgrado =MecanismoDocumentosTutoriaPosgrado.objects.filter(filtros).filter(mecanismotitulacionposgrado = eMecanismoTitulacionPosgrado,convocatoria = eConfiguracionTitulacionPosgrado).order_by('orden')

                    paging = MiPaginador(eMecanismoDocumentosTutoriaPosgrado, 25)
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
                    data['eConfiguracionTitulacionPosgrado'] = eConfiguracionTitulacionPosgrado
                    data['eMecanismoTitulacionPosgrado'] = eMecanismoTitulacionPosgrado
                    data['search'] = search if search else ""
                    data['eMecanismoDocumentosTutoriaPosgrados'] = page.object_list
                    return render(request, "adm_configuracionpropuesta/administrador/documentossubidatutoria.html", data)
                except Exception as ex:
                    pass

            elif action  == 'configuracionprogramamecanismotutoria':
                try:
                    eConfiguracionTitulacionPosgrado = ConfiguracionTitulacionPosgrado.objects.get(pk = int(request.GET["idconfiguracion"]))
                    eMecanismoTitulacionPosgrado = eConfiguracionTitulacionPosgrado.carrera.get_mecanismo_configurados()
                    data['title'] = u'Configuración etapas de tutorias por mecanismo de titulación'
                    search = None
                    search = request.GET.get('s', '')
                    url_vars = ""
                    filtros = Q(status=True)

                    data["url_vars"] = url_vars

                    paging = MiPaginador(eMecanismoTitulacionPosgrado, 25)
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
                    data['eConfiguracionTitulacionPosgrado'] = eConfiguracionTitulacionPosgrado
                    data['search'] = search if search else ""
                    data['eMecanismoTitulacionPosgrados'] = page.object_list
                    return render(request, "adm_configuracionpropuesta/administrador/programamecanismotutoriasposgrado.html", data)
                except Exception as ex:
                    pass

            elif action == 'addmodeloevaluativoposgrado':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_modelos_evaluativos')
                    data['title'] = u'Adicionar modelo evaluativo posgrado'
                    data['form'] = ModeloEvaluativoPosgradoForm()
                    template = get_template("adm_configuracionpropuesta/modal/formModeloevaluativoposgrado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'add_etapa_tutoria_posgrado':
                try:
                    data['title'] = u'Adicionar etapa tutoria posgrado'
                    data['form'] = EtapaTutoriaTitulacionPosgradoForm()
                    template = get_template("adm_configuracionpropuesta/modal/formetapatutoriaposgrado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'add_programa_etapa_tutoria_posgrado':
                try:
                    data['title'] = u'Adicionar etapa tutoria posgrado'
                    form = ProgramaEtapaTutoriaTitulacionPosgradoForm()
                    data['idconfiguracion'] = idconfiguracion = request.GET['idconfiguracion']
                    data['idmecanismo'] = idmecanismo = request.GET['idmecanismo']
                    form.add(int(idconfiguracion),int(idmecanismo))
                    data['form'] = form
                    template = get_template("adm_configuracionpropuesta/modal/formprogramaetapatutoriaposgrado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'add_documento_tutoria_titulacion_posgrado':
                try:
                    data['title'] = u'Adicionar documento tutoria tiulación posgrado'
                    form = TipoDocumentoTutoriaPosgradoTitulacionForm()
                    data['idconfiguracion'] = idconfiguracion = request.GET['idconfiguracion']
                    data['idmecanismo'] = idmecanismo = request.GET['idmecanismo']
                    data['form'] = form
                    template = get_template("adm_configuracionpropuesta/modal/formprogramaetapatutoriaposgrado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'edit_programa_etapa_tutoria_posgrado':
                try:
                    data['id'] = id =  request.GET['id']
                    data['filtro'] = filtro = ProgramaEtapaTutoriaPosgrado.objects.get(pk=id)
                    form = ProgramaEtapaTutoriaTitulacionPosgradoForm(initial=model_to_dict(filtro))
                    data['idconfiguracion'] = idconfiguracion = request.GET['idconfiguracion']
                    data['idmecanismo'] = idmecanismo = request.GET['idmecanismo']
                    form.edit(int(idconfiguracion),filtro.etapatutoria.pk, int(idmecanismo))
                    data['form'] = form
                    template = get_template("adm_configuracionpropuesta/modal/formprogramaetapatutoriaposgrado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'detallemodeloevaluativoposgrado':
                try:
                    data['title'] = u'Detalle modelo evaluativo posgrado'
                    data['modelo'] = modelo = ModeloEvaluativoPosgrado.objects.get(pk=request.GET['id'], status = True)
                    data['campos'] = modelo.modeloevualativodetalleposgrado_set.filter(status=True)

                    return render(request, "adm_configuracionpropuesta/detallemodeloevaluativoposgrado.html", data)
                except Exception as ex:
                    pass

            elif action == 'adddetallemodeloevaluativoposgrado':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_modelos_evaluativos')
                    data['title'] = u'Nuevo campo del modelo evaluativo posgrado'
                    data['modelo'] = modelo = ModeloEvaluativoPosgrado.objects.get(pk=request.GET['id'], status=True)
                    data['form'] = DetalleModeloEvaluativoPosgradoForm()
                    template = get_template("adm_configuracionpropuesta/modal/formDetalleModeloevaluativoposgrado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'editdetallemodeloevaluativoposgrado':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_modelos_evaluativos')
                    data['title'] = u'Editar campo'
                    data['detalle'] = detalle = ModeloEvualativoDetallePosgrado.objects.get(pk=request.GET['id'])
                    form = DetalleModeloEvaluativoPosgradoForm(initial={'nombre': detalle.nombre,
                                                                        'alternativa': detalle.alternativa,
                                                                        'notamaxima': detalle.notamaxima})
                    form.editar()
                    data['form'] = form
                    template = get_template("adm_configuracionpropuesta/modal/formDetalleModeloevaluativoposgrado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'crear_cursos_moodle_complexivo_posgrado':
                try:
                    grupo_titulacion_posgrado = GrupoTitulacionPostgrado.objects.get(pk=request.GET['id'])
                    grupo_titulacion_posgrado.crear_actualizar_curso_grupo_titulacion_posgrado()
                    return JsonResponse({"result": True, 'mensaje':'El curso se creo correctamente.'})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje':'Ha ocurrido un error al crear el curso.'})

            elif action == 'enrolar_actualizar_estudiantes_grupos_posgrado':
                try:
                    grupo_titulacion_posgrado = GrupoTitulacionPostgrado.objects.get(pk=request.GET['id'])
                    from moodle import moodle
                    tipourl=1
                    grupo_titulacion_posgrado.crear_actualizar_estudiantes_curso_grupo_posgrado(moodle, tipourl)
                    return JsonResponse({"result": True, 'mensaje':'Los maestrantes se enrolaron al curso de  moodle correctamente.'})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje':'Ha ocurrido un error al enrolar a los maestrantes al curso de moodle.'})

            elif action == 'enrolar_actualizar_tutor_grupos_posgrado':
                try:
                    grupo_titulacion_posgrado = GrupoTitulacionPostgrado.objects.get(pk=request.GET['id'])
                    from moodle import moodle
                    tipourl=1
                    grupo_titulacion_posgrado.crear_actualizar_tutor_curso_grupo_titulacion_posgrado(moodle, tipourl)
                    return JsonResponse({"result": True, 'mensaje':'El tutor se enrolo al curso de  moodle correctamente.'})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje':'Ha ocurrido un error al enrolar al tutor al curso de moodle.'})

            elif action == 'enrolar_actualizar_un_estudiantes_grupos_posgrado':
                try:
                    from moodle import moodle
                    tipourl = 1
                    estudiante = DetalleGrupoTitulacionPostgrado.objects.get(pk=request.GET['id'])
                    estudiante.crear_actualizar_un_estudiante_curso_grupo_posgrado( moodle, tipourl)
                    return JsonResponse({"result": True, 'mensaje':'Los maestrantes se enrolaron al curso de  moodle correctamente.'})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje':'Ha ocurrido un error al enrolar a los maestrantes al curso de moodle.'})

            elif action == 'verificar_enrolado_un_inscrito_grupo_posgrado':
                try:
                    estudiante = DetalleGrupoTitulacionPostgrado.objects.get(pk=request.GET['id'])
                    idusermoodle = estudiante.inscrito.matricula.inscripcion.persona.idusermoodleposgrado
                    idcursomoodle = estudiante.grupoTitulacionPostgrado.idgrupomoodle
                    cursor = None
                    cursor = connections['moodle_pos'].cursor()

                    if idusermoodle > 0:
                        queryest = """
                                        SELECT DISTINCT asi.userid, asi.roleid
                                        FROM  mooc_role_assignments asi
                                        INNER JOIN MOOC_CONTEXT CON ON asi.CONTEXTID=CON.ID AND ASI.ROLEID=%s 
                                        AND CON.INSTANCEID=%s AND asi.userid =%s
                                            """ % (estudiante.grupoTitulacionPostgrado.configuracion.periodo.rolestudiante, idcursomoodle, idusermoodle)
                        cursor.execute(queryest)
                        rowest = cursor.fetchall()
                        return JsonResponse({"result": "ok", "rowest": rowest})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"El usuario no se encuentra enrolado"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

            elif action  == 'solicitudesprorrogapropuesta':
                try:

                    data['title'] = u'Solicitudes de prórroga de registro de propuesta de titulación'

                    periodos_id = SolicitudProrrogaIngresoTemaMatricula.objects.filter(status = True).order_by('matricula__nivel__periodo').values_list('matricula__nivel__periodo',flat = True).distinct()
                    carreras_id = SolicitudProrrogaIngresoTemaMatricula.objects.filter(status = True).order_by('matricula__inscripcion__carrera').values_list('matricula__inscripcion__carrera',flat = True).distinct()

                    search = None
                    search = request.GET.get('s', '')
                    carrera_id =int(request.GET.get('carrera_id','0'))
                    periodo_id =int(request.GET.get('periodo_id','0'))
                    estado_id =int(request.GET.get('estado_id','0'))
                    url_vars = ""
                    filtros = Q(status=True)
                    if search:
                        data['search'] = search
                        url_vars += "&s={}".format(search)
                        filtros = filtros & (
                                Q(matricula__inscripcion__persona__nombres__icontains=search) |
                                Q(matricula__inscripcion__persona__apellido1__icontains=search) |
                                Q(matricula__inscripcion__persona__apellido2__icontains=search) |
                                Q(matricula__inscripcion__persona__cedula__icontains=search)
                        )
                    if carrera_id != 0:
                        url_vars += "&carrera_id={}".format(carrera_id)
                        filtros = filtros & (Q(matricula__inscripcion__carrera__id=carrera_id))

                    if periodo_id != 0:
                        url_vars += "&periodo_id={}".format(periodo_id)
                        filtros = filtros & (Q(matricula__nivel__periodo__id=periodo_id))

                    if estado_id != 0:
                        url_vars += "&estado_id={}".format(estado_id)
                        filtros = filtros & (Q(estado=estado_id))

                    solicitudes =SolicitudProrrogaIngresoTemaMatricula.objects.filter(filtros).order_by('-id')


                    paging = MiPaginador(solicitudes, 25)
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
                    data['periodos'] = Periodo.objects.filter(id__in=periodos_id)
                    data['carreras'] = Carrera.objects.filter(id__in = carreras_id)
                    data['page'] = page
                    data['url_vars'] = url_vars
                    data['search'] = search if search else ""
                    data['estado_id'] = estado_id
                    data['carrera_id'] = carrera_id
                    data['periodo_id'] = periodo_id
                    data['solicitudes'] = page.object_list
                    return render(request, "adm_configuracionpropuesta/solicitudesprorrogapropuestatitulacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'revisarsolicitudprorrogatitulacion':
                try:
                    data['title'] = u'Revisar solicitud prórroga propuesta titulación'
                    solicitud = SolicitudProrrogaIngresoTemaMatricula.objects.get(pk=request.GET['id'])
                    form = FormSolicitudProrrogaIngresoTemaMatricula(initial={
                        'fechainicioprorroga':solicitud.fechainicioprorroga,
                        'fechafinprorroga':solicitud.fechafinprorroga,
                        'estado':solicitud.estado,
                    })

                    form.revisar(solicitud)
                    data['form'] = form
                    data['action'] = 'revisarsolicitudprorrogatitulacion'
                    data['solicitud'] = solicitud
                    template = get_template("adm_configuracionpropuesta/modal/formrevisarsolicitudprorrogapropuestatitulacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'historialsolicitudprorroga':
                try:
                    data['title'] = u'Historial solicitud prórroga propuesta titulación'
                    solicitud = SolicitudProrrogaIngresoTemaMatricula.objects.get(pk=request.GET['id'])
                    data['historiales'] = solicitud.historial_solicitud()
                    template = get_template("adm_configuracionpropuesta/modal/historialsolicitudprorrogapropuestatitulacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'configuracion_informe_tribunal':
                try:
                    data['title'] = u'Configuración informe tribunal por programa'
                    search = None
                    search = request.GET.get('s', '')
                    url_vars = ""
                    filtros = Q(status=True)
                    if search:
                        data['search'] = search
                        url_vars += "&s={}".format(search)
                        filtros = filtros & (Q(programa__nombre__icontains=search))

                    data["url_vars"] = url_vars
                    configuracion_informe_tribunal = ConfiguraInformePrograma.objects.filter(filtros).order_by('programa_id','mecanismotitulacionposgrado_id')

                    paging = MiPaginador(configuracion_informe_tribunal, 25)
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
                    data['configuracion_informe'] = page.object_list
                    return render(request, "adm_configuracionpropuesta/configuracioninformetribunal.html", data)
                except Exception as ex:
                    pass

            elif action == 'add_configuracion_informe_tribunal':
                try:
                    data['title'] = u'Adicionar informe'
                    form = FormConfiguracionInforme()
                    data['form'] = form
                    template = get_template("adm_configuracionpropuesta/modal/forminforme.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'edit_configuracion_informe_tribunal':
                try:
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = ConfiguraInformePrograma.objects.get(pk=id)
                    form = FormConfiguracionInforme(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("adm_configuracionpropuesta/modal/forminforme.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            elif action == 'informe_tribunal':
                try:
                    data['title'] = u'Configuración informe tribunal'
                    search = None
                    search = request.GET.get('s', '')
                    url_vars = ""
                    filtros = Q(status=True)
                    if search:
                        data['search'] = search
                        url_vars += "&s={}".format(search)
                        filtros = filtros & (Q(descripcion__icontains=search))

                    data["url_vars"] = url_vars
                    informe_tribunal = Informe.objects.filter(filtros).order_by('id')

                    paging = MiPaginador(informe_tribunal, 25)
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
                    data['informes'] = page.object_list
                    return render(request, "adm_configuracionpropuesta/informetribunal.html", data)
                except Exception as ex:
                    pass

            elif action == 'add_informe_tribunal':
                try:
                    data['title'] = u'Adicionar informe'
                    form = FormInforme()
                    data['form'] = form
                    template = get_template("adm_configuracionpropuesta/modal/forminforme.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'edit_informe_tribunal':
                try:
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = Informe.objects.get(pk=id)
                    form = FormInforme(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("adm_configuracionpropuesta/modal/forminforme.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'seccion_informe_tribunal':
                try:
                    id_informe= request.GET['id']
                    data['title'] = u'Configuración de secciones de informe tribunal'
                    search = None
                    search = request.GET.get('s', '')
                    url_vars = ""
                    filtros = Q(status=True)
                    if search:
                        data['search'] = search
                        url_vars += "&s={}".format(search)
                        filtros = filtros & (Q(etapa__descripcion__icontains=search))

                    data["url_vars"] = url_vars
                    seccione_informe_tribunal = SeccionInforme.objects.filter(filtros).filter(informe__id=id_informe).order_by('id')

                    paging = MiPaginador(seccione_informe_tribunal, 25)
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
                    data['secciones_informe'] = page.object_list
                    data['id_informe'] = id_informe
                    return render(request, "adm_configuracionpropuesta/seccioninformetribunal.html", data)
                except Exception as ex:
                    pass

            elif action == 'add_seccion_informe_tribunal':
                try:
                    data['title'] = u'Adicionar sección de informe'
                    form = FormSeccionInforme()
                    id_informe =request.GET['id']
                    form.add(id_informe)
                    data['form'] = form
                    data['id_informe'] = id_informe
                    template = get_template("adm_configuracionpropuesta/modal/formseccioninforme.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'edit_seccion_informe_tribunal':
                try:
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = SeccionInforme.objects.get(pk=id)
                    form = FormSeccionInforme(initial=model_to_dict(filtro))
                    form.edit(filtro.informe.id,filtro.seccion.id)
                    data['form'] = form
                    template = get_template("adm_configuracionpropuesta/modal/formseccioninforme.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'preguntas_informe':
                try:
                    data['title'] = u'Configuración de preguntas para informes'
                    search = None
                    search = request.GET.get('s', '')
                    url_vars = ""
                    filtros = Q(status=True)
                    if search:
                        data['search'] = search
                        url_vars += "&s={}".format(search)
                        filtros = filtros & (Q(descripcion__icontains=search))

                    data["url_vars"] = url_vars
                    preguntas = Pregunta.objects.filter(filtros).order_by('id')

                    paging = MiPaginador(preguntas, 25)
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
                    data['preguntas'] = page.object_list
                    return render(request, "adm_configuracionpropuesta/preguntas.html", data)
                except Exception as ex:
                    pass

            elif action == 'add_pregunta_informe':
                try:
                    data['title'] = u'Adicionar pregunta'
                    form = FormPreguntaInforme()
                    data['form'] = form
                    template = get_template("adm_configuracionpropuesta/modal/formpregunta.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'edit_pregunta_informe':
                try:
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = Pregunta.objects.get(pk=id)
                    form = FormPreguntaInforme(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("adm_configuracionpropuesta/modal/formpregunta.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'add_pregunta_seccion_informe':
                try:
                    data['title'] = u'Adicionar pregunta a la sección del informe'
                    form = FormSeccionInformePregunta()
                    id_seccion_informe = request.GET['id']
                    seccion_informe = SeccionInforme.objects.get(pk= id_seccion_informe)
                    form.add(seccion_informe.informe.id)
                    data['form'] = form
                    data['id_seccion_informe'] = id_seccion_informe
                    template = get_template("adm_configuracionpropuesta/modal/formpreguntaseccioninforme.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'edit_pregunta_seccion_informe':
                try:
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = SeccionInformePregunta.objects.get(pk=id)
                    form = FormSeccionInformePregunta(initial=model_to_dict(filtro))
                    form.edit(filtro.seccion_informe.informe.id,filtro.pregunta.id)
                    data['form'] = form
                    template = get_template("adm_configuracionpropuesta/modal/formpreguntaseccioninforme.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'deletesolicitud':
                try:
                    data['title'] = u'Eliminar solicitud de tema titulación'
                    data['solicitud'] = TemaTitulacionPosgradoProfesor.objects.get(pk=request.GET['id'], status=True)
                    data['idtema'] = request.GET['idtema']
                    data['idconfiguracion'] = request.GET['idconfiguracion']
                    return render(request, 'adm_configuracionpropuesta/deletesolicitud.html', data)
                except Exception as ex:
                    pass

            elif action == 'seguimiento_tribunal':
                try:
                    id= int(request.GET['id'])
                    es_pareja = json.loads(request.GET['es_pareja'])
                    if es_pareja:
                        tema =TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=id)
                    else:
                        tema =TemaTitulacionPosgradoMatricula.objects.get(pk=id)

                    tribunal = tema.obtener_tribunal()
                    revisiones = Revision.objects.filter(status=True, tribunal =tribunal)

                    data['revisiones'] = revisiones
                    template = get_template('adm_configuracionpropuesta/modal/formseguimientotribunal.html')
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'tutorias_configuradas_mecanismo':
                try:
                    id_configuracion= int(request.GET['id_configuracion'])
                    id_mecanismo= int(request.GET['id_mecanismo'])
                    eProgramaEtapaTutoriaPosgrado = ProgramaEtapaTutoriaPosgrado.objects.filter(status=True,mecanismotitulacionposgrado_id =id_mecanismo, convocatoria_id =id_configuracion).order_by('orden')
                    data['eProgramaEtapaTutoriaPosgrado'] =eProgramaEtapaTutoriaPosgrado
                    template = get_template('adm_configuracionpropuesta/modal/formetapasconfiguradas.html')
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'informe_configuradas_mecanismo':
                try:
                    id_carrera= int(request.GET['id_carrera'])
                    id_mecanismo= int(request.GET['id_mecanismo'])
                    eConfiguraInformePrograma = ConfiguraInformePrograma.objects.filter(mecanismotitulacionposgrado_id=id_mecanismo, programa=id_carrera, estado=True, status=True)
                    data['eConfiguraInformePrograma'] = eConfiguraInformePrograma
                    template = get_template('adm_configuracionpropuesta/modal/forminformeconfigurado.html')
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'verificar_cantidad_actas_seleccionadas':
                try:
                    id = int(request.GET['id'])
                    actas = TemaTitulacionPosgradoMatricula.objects.filter(califico=True, actacerrada=True, status=True,
                                                                           estado_acta_firma=4,
                                                                           mecanismotitulacionposgrado__in=(15, 21),
                                                                           convocatoria_id=id).filter(Q(archivo_acta_grado__isnull=True) | Q(archivo_acta_grado = ''))
                    if actas.count() > 0:
                        return JsonResponse({"result": "ok", "cantidad": actas.count()})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"No existen actas con criterios requeridos para ser generadas."})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'informe_pdf':
                try:
                    informe = informe_posgrado(request.GET['id'])
                    return informe
                except Exception as ex:
                    pass

            elif action == 'exportar_poblacion':
                try:
                    ids = request.GET.getlist('ids[]')
                    idencuesta = request.GET['idencuesta']
                    eTemaTitulacionPosgradoMatriculas = TemaTitulacionPosgradoMatricula.objects.filter(status=True, pk__in=ids)
                    data['eTemaTitulacionPosgradoMatriculas'] = eTemaTitulacionPosgradoMatriculas
                    data['ids'] = ids
                    data['idencuesta'] = idencuesta
                    template = get_template('adm_configuracionpropuesta/encuestas/configuracion/modal/formmodalimportarpoblacion.html')
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'importar_ubicacion_masiva_sede_graduacion':
                try:
                    id = int(request.GET['id'])
                    eEncuestaTitulacionPosgrado = EncuestaTitulacionPosgrado.objects.get(pk=id)
                    data['eEncuestaTitulacionPosgrado'] = eEncuestaTitulacionPosgrado
                    template = get_template('adm_configuracionpropuesta/encuestas/configuracion/modal/formmodalimportarubicacion.html')
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'dowloadreporteencuesta':
                try:
                    eEncuestaTitulacionPosgrado = EncuestaTitulacionPosgrado.objects.get(pk=int(request.GET['pk']))
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
                    ws = workbook.add_worksheet()

                    formatoceldagris = workbook.add_format({'bold': True, 'bg_color': 'gray', 'font_color': 'white'})

                    ws.set_column(2, 12, 50)  # Adjust column width for columns A to M

                    # Text with formatting.
                    headers = ['CARRERA','MAESTRANTE', 'CEDULA', 'EMAIL',
                               'EMAILINST', 'TELEFONO', 'RESPONDIO','PARTICIPA', 'SEDE', 'HORAIO', 'BLOQUE', 'FILA', 'ASIENTO', 'ASISTIO']
                    for col_num, header in enumerate(headers):
                        ws.write(0, col_num, header, formatoceldagris)

                    row_num = 1
                    for eInscripcionEncuestaTitulacionPosgrado in  eEncuestaTitulacionPosgrado.get_encuestados():
                        ws.write(row_num, 0, eInscripcionEncuestaTitulacionPosgrado.inscripcion.carrera.__str__())
                        ws.write(row_num, 1, eInscripcionEncuestaTitulacionPosgrado.inscripcion.persona.__str__())
                        ws.write(row_num, 2, eInscripcionEncuestaTitulacionPosgrado.inscripcion.persona.cedula.__str__())
                        ws.write(row_num, 3, eInscripcionEncuestaTitulacionPosgrado.inscripcion.persona.email.__str__())
                        ws.write(row_num, 4, eInscripcionEncuestaTitulacionPosgrado.inscripcion.persona.emailinst.__str__())
                        ws.write(row_num, 5, eInscripcionEncuestaTitulacionPosgrado.inscripcion.persona.telefono.__str__())
                        ws.write(row_num, 6, 'Si' if eInscripcionEncuestaTitulacionPosgrado.respondio else 'No')
                        ws.write(row_num, 7, 'Si' if eInscripcionEncuestaTitulacionPosgrado.participa else 'No')

                        fecha_ceremonia = ''
                        if eInscripcionEncuestaTitulacionPosgrado.get_resultado_encuestado():
                            fecha_ceremonia =f'{eInscripcionEncuestaTitulacionPosgrado.get_resultado_encuestado().jornadasedeencuestatitulacionposgrado.fecha.__str__() }-  {eInscripcionEncuestaTitulacionPosgrado.get_resultado_encuestado().jornadasedeencuestatitulacionposgrado.hora_inicio.__str__()} - { eInscripcionEncuestaTitulacionPosgrado.get_resultado_encuestado().jornadasedeencuestatitulacionposgrado.hora_fin.__str__()}'
                            ws.write(row_num, 8,  eInscripcionEncuestaTitulacionPosgrado.get_resultado_encuestado().jornadasedeencuestatitulacionposgrado.sedeencuestatitulacionposgrado.__str__())
                            ws.write(row_num, 9,fecha_ceremonia )
                            ws.write(row_num, 10, eInscripcionEncuestaTitulacionPosgrado.bloque.__str__())
                            ws.write(row_num, 11, eInscripcionEncuestaTitulacionPosgrado.fila.__str__())
                            ws.write(row_num, 12, eInscripcionEncuestaTitulacionPosgrado.asiento.__str__())
                            ws.write(row_num, 13, 'Si' if eInscripcionEncuestaTitulacionPosgrado.asistio else 'No')
                        else:
                            ws.write(row_num, 8, '')
                            ws.write(row_num, 9, fecha_ceremonia)
                            ws.write(row_num, 10, '')
                            ws.write(row_num, 11, '')
                            ws.write(row_num, 12, '')
                            ws.write(row_num, 13, '')


                        row_num += 1

                    # Close workbook and prepare the response
                    workbook.close()
                    output.seek(0)
                    filename = f"sede_graduacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = f'attachment; filename={filename}'
                    return response

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": f"Error al descargar reporte:  {sys.exc_info()[-1].tb_lineno}"})

            elif action == 'dowloadreporteencuestaasistieron':
                try:
                    eEncuestaTitulacionPosgrado = EncuestaTitulacionPosgrado.objects.get(pk=int(request.GET['pk']))
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
                    ws = workbook.add_worksheet()

                    formatoceldagris = workbook.add_format({'bold': True, 'bg_color': 'gray', 'font_color': 'white'})

                    ws.set_column(2, 12, 50)  # Adjust column width for columns A to M

                    # Text with formatting.
                    headers = ['CARRERA','MAESTRANTE', 'CEDULA', 'EMAIL',
                               'EMAILINST', 'TELEFONO', 'RESPONDIO','PARTICIPA', 'SEDE', 'FECHA', 'BLOQUE', 'FILA', 'ASIENTO', 'ASISTIO']
                    for col_num, header in enumerate(headers):
                        ws.write(0, col_num, header, formatoceldagris)

                    row_num = 1
                    for eInscripcionEncuestaTitulacionPosgrado in  eEncuestaTitulacionPosgrado.get_encuestados().filter(asistio=True):
                        ws.write(row_num, 0, eInscripcionEncuestaTitulacionPosgrado.inscripcion.carrera.__str__())
                        ws.write(row_num, 1, eInscripcionEncuestaTitulacionPosgrado.inscripcion.persona.__str__())
                        ws.write(row_num, 2, eInscripcionEncuestaTitulacionPosgrado.inscripcion.persona.cedula.__str__())
                        ws.write(row_num, 3, eInscripcionEncuestaTitulacionPosgrado.inscripcion.persona.email.__str__())
                        ws.write(row_num, 4, eInscripcionEncuestaTitulacionPosgrado.inscripcion.persona.emailinst.__str__())
                        ws.write(row_num, 5, eInscripcionEncuestaTitulacionPosgrado.inscripcion.persona.telefono.__str__())
                        ws.write(row_num, 6, 'Si' if eInscripcionEncuestaTitulacionPosgrado.respondio else 'No')
                        ws.write(row_num, 7, 'Si' if eInscripcionEncuestaTitulacionPosgrado.participa else 'No')
                        fecha_ceremonia=''
                        if  eInscripcionEncuestaTitulacionPosgrado.get_resultado_encuestado():
                            fecha_ceremonia = f'{eInscripcionEncuestaTitulacionPosgrado.get_resultado_encuestado().jornadasedeencuestatitulacionposgrado.fecha.__str__() } - {eInscripcionEncuestaTitulacionPosgrado.get_resultado_encuestado().jornadasedeencuestatitulacionposgrado.hora_inicio.__str__()} - {eInscripcionEncuestaTitulacionPosgrado.get_resultado_encuestado().jornadasedeencuestatitulacionposgrado.hora_fin.__str__()}'

                            ws.write(row_num, 8, eInscripcionEncuestaTitulacionPosgrado.get_resultado_encuestado().jornadasedeencuestatitulacionposgrado.sedeencuestatitulacionposgrado.__str__())
                            ws.write(row_num, 9, fecha_ceremonia)

                            ws.write(row_num, 10, eInscripcionEncuestaTitulacionPosgrado.bloque.__str__())
                            ws.write(row_num, 11, eInscripcionEncuestaTitulacionPosgrado.fila.__str__())
                            ws.write(row_num, 12, eInscripcionEncuestaTitulacionPosgrado.asiento.__str__())
                            ws.write(row_num, 13, 'Si' if eInscripcionEncuestaTitulacionPosgrado.asistio else 'No')
                        else:
                            ws.write(row_num, 8, '')
                            ws.write(row_num, 9,fecha_ceremonia)
                            ws.write(row_num, 10, '')
                            ws.write(row_num, 11, '')
                            ws.write(row_num, 12, '')
                            ws.write(row_num, 13, '')

                        row_num += 1

                    # Close workbook and prepare the response
                    workbook.close()
                    output.seek(0)
                    filename = f"sede_graduacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = f'attachment; filename={filename}'
                    return response

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": f"Error al descargar pagaré {sys.exc_info()[-1].tb_lineno}"})

            elif action == 'dowloadreporteencuestanoasistieron':
                try:
                    eEncuestaTitulacionPosgrado = EncuestaTitulacionPosgrado.objects.get(pk=int(request.GET['pk']))
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
                    ws = workbook.add_worksheet()

                    formatoceldagris = workbook.add_format({'bold': True, 'bg_color': 'gray', 'font_color': 'white'})

                    ws.set_column(2, 12, 50)  # Adjust column width for columns A to M

                    # Text with formatting.
                    headers = ['CARRERA','MAESTRANTE', 'CEDULA', 'EMAIL',
                               'EMAILINST', 'TELEFONO', 'RESPONDIO','PARTICIPA', 'SEDE', 'FECHA', 'BLOQUE', 'FILA', 'ASIENTO', 'ASISTIO']
                    for col_num, header in enumerate(headers):
                        ws.write(0, col_num, header, formatoceldagris)

                    row_num = 1
                    for eInscripcionEncuestaTitulacionPosgrado in  eEncuestaTitulacionPosgrado.get_encuestados().filter(asistio=False,participa=True,respondio=True):
                        ws.write(row_num, 0, eInscripcionEncuestaTitulacionPosgrado.inscripcion.carrera.__str__())
                        ws.write(row_num, 1, eInscripcionEncuestaTitulacionPosgrado.inscripcion.persona.__str__())
                        ws.write(row_num, 2, eInscripcionEncuestaTitulacionPosgrado.inscripcion.persona.cedula.__str__())
                        ws.write(row_num, 3, eInscripcionEncuestaTitulacionPosgrado.inscripcion.persona.email.__str__())
                        ws.write(row_num, 4, eInscripcionEncuestaTitulacionPosgrado.inscripcion.persona.emailinst.__str__())
                        ws.write(row_num, 5, eInscripcionEncuestaTitulacionPosgrado.inscripcion.persona.telefono.__str__())
                        ws.write(row_num, 6, 'Si' if eInscripcionEncuestaTitulacionPosgrado.respondio else 'No')
                        ws.write(row_num, 7, 'Si' if eInscripcionEncuestaTitulacionPosgrado.participa else 'No')
                        fecha_ceremonia=''
                        if  eInscripcionEncuestaTitulacionPosgrado.get_resultado_encuestado():
                            fecha_ceremonia = f'{eInscripcionEncuestaTitulacionPosgrado.get_resultado_encuestado().jornadasedeencuestatitulacionposgrado.fecha.__str__() }- {eInscripcionEncuestaTitulacionPosgrado.get_resultado_encuestado().jornadasedeencuestatitulacionposgrado.hora_inicio.__str__()} - {eInscripcionEncuestaTitulacionPosgrado.get_resultado_encuestado().jornadasedeencuestatitulacionposgrado.hora_fin.__str__()}'
                            ws.write(row_num, 8,  eInscripcionEncuestaTitulacionPosgrado.get_resultado_encuestado().jornadasedeencuestatitulacionposgrado.sedeencuestatitulacionposgrado.__str__())
                            ws.write(row_num, 9, fecha_ceremonia)
                            ws.write(row_num, 10, eInscripcionEncuestaTitulacionPosgrado.bloque.__str__())
                            ws.write(row_num, 11, eInscripcionEncuestaTitulacionPosgrado.fila.__str__())
                            ws.write(row_num, 12, eInscripcionEncuestaTitulacionPosgrado.asiento.__str__())
                            ws.write(row_num, 13, 'Si' if eInscripcionEncuestaTitulacionPosgrado.asistio else 'No')
                        else:
                            ws.write(row_num, 8, '')
                            ws.write(row_num, 9, fecha_ceremonia)
                            ws.write(row_num, 10, '')
                            ws.write(row_num, 11, '')
                            ws.write(row_num, 12, '')
                            ws.write(row_num, 13, '')

                        row_num += 1

                    # Close workbook and prepare the response
                    workbook.close()
                    output.seek(0)
                    filename = f"sede_graduacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = f'attachment; filename={filename}'
                    return response

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": f"Error al descargar {sys.exc_info()[-1].tb_lineno}"})

            elif action == 'dowload_formato_resultados_sede_graduacion_posgrado':
                try:
                    eEncuestaTitulacionPosgrado = EncuestaTitulacionPosgrado.objects.get(pk=int(request.GET['id']))
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
                    ws = workbook.add_worksheet()

                    formatoceldagris = workbook.add_format({'bold': True, 'bg_color': 'gray', 'font_color': 'white'})

                    ws.set_column(2, 12, 50)  # Adjust column width for columns A to M

                    # Text with formatting.
                    headers = ['ID','CARRERA','MAESTRANTE', 'CEDULA', 'EMAIL', 'EMAILINST', 'TELEFONO', 'RESPONDIO','PARTICIPA', 'SEDE', 'FECHA', 'BLOQUE', 'FILA', 'ASIENTO']
                    for col_num, header in enumerate(headers):
                        ws.write(0, col_num, header, formatoceldagris)

                    row_num = 1
                    for eInscripcionEncuestaTitulacionPosgrado in  eEncuestaTitulacionPosgrado.get_encuestados().filter(respondio=True,participa=True):
                        ws.write(row_num, 0, eInscripcionEncuestaTitulacionPosgrado.id)
                        ws.write(row_num, 1, eInscripcionEncuestaTitulacionPosgrado.inscripcion.carrera.__str__())
                        ws.write(row_num, 2, eInscripcionEncuestaTitulacionPosgrado.inscripcion.persona.__str__())
                        ws.write(row_num, 3, eInscripcionEncuestaTitulacionPosgrado.inscripcion.persona.cedula.__str__())
                        ws.write(row_num, 4, eInscripcionEncuestaTitulacionPosgrado.inscripcion.persona.email.__str__())
                        ws.write(row_num, 5, eInscripcionEncuestaTitulacionPosgrado.inscripcion.persona.emailinst.__str__())
                        ws.write(row_num, 6, eInscripcionEncuestaTitulacionPosgrado.inscripcion.persona.telefono.__str__())
                        ws.write(row_num, 7, 'Si' if eInscripcionEncuestaTitulacionPosgrado.respondio else 'No')
                        ws.write(row_num, 8, 'Si' if eInscripcionEncuestaTitulacionPosgrado.participa else 'No')
                        fecha_ceremonia=''
                        if  eInscripcionEncuestaTitulacionPosgrado.get_resultado_encuestado():
                            fecha_ceremonia = f'{eInscripcionEncuestaTitulacionPosgrado.get_resultado_encuestado().jornadasedeencuestatitulacionposgrado.fecha.__str__() }- {eInscripcionEncuestaTitulacionPosgrado.get_resultado_encuestado().jornadasedeencuestatitulacionposgrado.hora_inicio.__str__()} - {eInscripcionEncuestaTitulacionPosgrado.get_resultado_encuestado().jornadasedeencuestatitulacionposgrado.hora_fin.__str__()}'
                            ws.write(row_num, 9,  eInscripcionEncuestaTitulacionPosgrado.get_resultado_encuestado().jornadasedeencuestatitulacionposgrado.sedeencuestatitulacionposgrado.__str__())
                            ws.write(row_num, 10, fecha_ceremonia)
                            ws.write(row_num, 11, eInscripcionEncuestaTitulacionPosgrado.bloque.__str__())
                            ws.write(row_num, 12, eInscripcionEncuestaTitulacionPosgrado.fila.__str__())
                            ws.write(row_num, 13, eInscripcionEncuestaTitulacionPosgrado.asiento.__str__())
                        else:
                            ws.write(row_num, 9, '')
                            ws.write(row_num, 10, '')
                            ws.write(row_num, 11, '')
                            ws.write(row_num, 12, '')
                            ws.write(row_num, 13, '')



                        row_num += 1

                    # Close workbook and prepare the response
                    workbook.close()
                    output.seek(0)
                    filename = f"sede_graduacion_participantes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = f'attachment; filename={filename}'
                    return response

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": f"Error {sys.exc_info()[-1].tb_lineno}."})

            elif action == 'rechazar_profesor_solicitudtema':
                try:
                    id = request.GET['id']
                    form =FormObservacion()
                    data['form'] = form
                    data['id'] = id
                    template = get_template("adm_configuracionpropuesta/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['escoordinadoraposgrado'] = escoordinadoraposgrado
                search = None
                ids = None
                if 'id' in request.GET:
                    ids = request.GET['id']
                    configuraciones = ConfiguracionTitulacionPosgrado.objects.filter(id=int(ids)).order_by('-id')
                elif 's' in request.GET:
                    search = request.GET['s']
                    configuraciones = ConfiguracionTitulacionPosgrado.objects.filter(Q(periodo__nombre__icontains=search) | Q(carrera__nombre__icontains=search), carrera__in=carreras).distinct().order_by('-id')
                else:
                    configuraciones = ConfiguracionTitulacionPosgrado.objects.filter(status=True, carrera__in=carreras).order_by('periodo_id','carrera_id')
                paging = MiPaginador(configuraciones, 12)
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
                data['configuraciones'] = page.object_list
                return render(request, "adm_configuracionpropuesta/view.html", data)
            except Exception as ex:
                pass
